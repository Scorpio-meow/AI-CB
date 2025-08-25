from typing import List, Dict, Any, Optional
import os
import time
import numpy as np
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from openai import OpenAI

class ContextualRAG:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.model_name = os.getenv("MODEL_NAME", "openai/gpt-5-chat")
        self.api_base = os.getenv("GITHUB_API_BASE", "https://models.github.ai/inference")
        
        # Initialize OpenAI client for external models
        import requests
        self.requests = requests
        
        # Initialize local embeddings for semantic search
        embedding_model = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
        self.local_embeddings = SentenceTransformer(embedding_model)
        self.embedding_dimension = 384  # paraphrase-multilingual-MiniLM-L12-v2 dimension
        
        # Configuration from environment
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))
        
        # FAISS vector store setup
        self.index = faiss.IndexFlatIP(self.embedding_dimension)  # Inner Product (cosine similarity)
        self.documents = []
        self.faiss_index_path = "data/faiss_index.bin"
        self.documents_path = "data/documents.pkl"
        self.context_memory = {}  # Store conversation context
        
        # Load existing index if available
        self._load_vector_store()
        
        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(os.getenv("CHUNK_SIZE", 1000)),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 200)),
            length_function=len,
        )
        
    def _load_vector_store(self):
        """Load existing FAISS index and documents"""
        try:
            if os.path.exists(self.faiss_index_path) and os.path.exists(self.documents_path):
                # Load FAISS index
                self.index = faiss.read_index(self.faiss_index_path)
                
                # Load documents
                with open(self.documents_path, 'rb') as f:
                    self.documents = pickle.load(f)
                    
                print(f"Loaded FAISS index with {self.index.ntotal} vectors and {len(self.documents)} documents")
            else:
                print("No existing FAISS index found, starting with empty index")
        except Exception as e:
            print(f"Error loading FAISS index: {e}")
            # Initialize empty index if loading fails
            self.index = faiss.IndexFlatIP(self.embedding_dimension)
            self.documents = []
    
    def _save_vector_store(self):
        """Save FAISS index and documents to disk"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.faiss_index_path), exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, self.faiss_index_path)
            
            # Save documents
            with open(self.documents_path, 'wb') as f:
                pickle.dump(self.documents, f)
                
            print(f"Saved FAISS index with {self.index.ntotal} vectors")
        except Exception as e:
            print(f"Error saving FAISS index: {e}")
        
    async def initialize_vector_store(self, documents: List[Document] = None):
        """Initialize or load the vector store"""
        if documents:
            await self.add_documents(documents)
            
    async def add_documents(self, documents: List[Document]):
        """Add documents to the FAISS vector store"""
        # Chunk documents
        all_chunks = []
        for doc in documents:
            chunks = self.text_splitter.split_text(doc.page_content)
            for i, chunk in enumerate(chunks):
                chunk_doc = Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        "chunk_id": f"{doc.metadata.get('source', 'unknown')}_{i}",
                        "chunk_index": i
                    }
                )
                all_chunks.append(chunk_doc)
        
        if not all_chunks:
            return
            
        # Generate embeddings for chunks
        chunk_texts = [chunk.page_content for chunk in all_chunks]
        embeddings = self.local_embeddings.encode(chunk_texts)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to FAISS index
        self.index.add(embeddings)
        
        # Store documents
        self.documents.extend(all_chunks)
        
        # Save to disk
        self._save_vector_store()
        
        print(f"Added {len(all_chunks)} chunks to FAISS index. Total: {self.index.ntotal} vectors")
        
    def semantic_search(self, query: str, top_k: int = 5) -> List[Document]:
        """Perform semantic search using FAISS"""
        if self.index.ntotal == 0:
            return []
            
        # Generate query embedding
        query_embedding = self.local_embeddings.encode([query])
        
        # Normalize query embedding for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Search FAISS index
        similarities, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
        
        # Filter results by similarity threshold and return documents
        relevant_docs = []
        for similarity, idx in zip(similarities[0], indices[0]):
            if similarity > self.similarity_threshold and idx < len(self.documents):  # Use configurable threshold
                relevant_docs.append(self.documents[idx])
                
        return relevant_docs
    
    def rerank_documents(self, query: str, documents: List[Document]) -> List[Document]:
        """Re-rank documents based on relevance for Traditional Chinese"""
        if not documents:
            return documents
            
        # Enhanced keyword-based re-ranking for Traditional Chinese
        import re
        
        # Extract keywords from query (including Chinese characters)
        query_terms = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', query.lower()))
        scored_docs = []
        
        for doc in documents:
            # Extract terms from document content
            doc_terms = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', doc.page_content.lower()))
            
            # Calculate overlap score
            overlap = len(query_terms.intersection(doc_terms))
            
            # Bonus for exact phrase matches
            phrase_bonus = 0
            for term in query_terms:
                if len(term) > 1 and term in doc.page_content.lower():
                    phrase_bonus += len(term)
            
            total_score = overlap + phrase_bonus * 0.5
            scored_docs.append((total_score, doc))
        
        # Sort by score
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        return [doc for _, doc in scored_docs]
    
    def build_context_prompt(self, query: str, relevant_docs: List[Document], 
                           conversation_id: Optional[int] = None) -> str:
        """Build the context-aware prompt"""
        # Get conversation history
        conversation_context = ""
        if conversation_id and conversation_id in self.context_memory:
            recent_context = self.context_memory[conversation_id][-3:]  # Last 3 exchanges
            for exchange in recent_context:
                conversation_context += f"用戶: {exchange['user']}\nAI: {exchange['assistant']}\n\n"
        
        # Build document context
        document_context = ""
        for i, doc in enumerate(relevant_docs):
            source = doc.metadata.get('source', '未知來源')
            document_context += f"文檔 {i+1} (來源: {source}):\n{doc.page_content}\n\n"
        
        # Build final prompt
        prompt = f"""你是一個專業的繁體中文智能助手，請根據提供的上下文信息回答用戶問題。

對話歷史:
{conversation_context}

相關文檔內容:
{document_context}

用戶問題: {query}

回答要求：
1. 請用繁體中文回答
2. 基於上述文檔內容提供準確、詳細的回答
3. 如果文檔中沒有相關信息，請誠實說明並提供一般性建議
4. 回答要條理清晰、易於理解
5. 可以適當引用文檔來源以增加可信度

請提供回答："""
        
        return prompt
    
    async def call_llm_api(self, prompt: str) -> str:
        """Call GPT-oss-20b API with custom payload"""
        try:
            url = f"{self.api_base}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
            headers = {"Content-Type": "application/json"}
            resp = self.requests.post(url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            # Ollama 回傳格式為 {"response": "..."}
            return data.get("response", "抱歉，模型未回應。").strip()
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return f"抱歉，生成回應時出現錯誤: {str(e)}"
    
    async def generate_response(self, query: str, conversation_id: Optional[int] = None) -> Dict[str, Any]:
        """Generate response using RAG"""
        # Retrieve relevant documents
        relevant_docs = self.semantic_search(query, top_k=5)
        
        # Re-rank documents
        reranked_docs = self.rerank_documents(query, relevant_docs)
        
        # Build context prompt
        context_prompt = self.build_context_prompt(query, reranked_docs, conversation_id)
        
        # Generate response using LLM
        answer = await self.call_llm_api(context_prompt)
        
        # Update conversation memory
        if conversation_id:
            if conversation_id not in self.context_memory:
                self.context_memory[conversation_id] = []
            
            self.context_memory[conversation_id].append({
                "user": query,
                "assistant": answer,
                "timestamp": time.time(),
                "context_used": len(reranked_docs)
            })
            
            # Keep only recent exchanges (max 10)
            if len(self.context_memory[conversation_id]) > 10:
                self.context_memory[conversation_id] = self.context_memory[conversation_id][-10:]
        
        return {
            "answer": answer,
            "context_used": len(reranked_docs),
            "sources": [doc.metadata.get('source', '未知') for doc in reranked_docs[:3]]
        }
    
    def clear_conversation_context(self, conversation_id: int):
        """Clear conversation context"""
        if conversation_id in self.context_memory:
            del self.context_memory[conversation_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        return {
            "total_documents": len(self.documents),
            "total_conversations": len(self.context_memory),
            "total_vectors": self.index.ntotal,
            "embedding_dimension": self.embedding_dimension
        }
    
    def get_vector_store_info(self) -> Dict[str, Any]:
        """Get information about the current vector store"""
        return {
            "total_vectors": self.index.ntotal,
            "total_documents": len(self.documents),
            "embedding_dimension": self.embedding_dimension,
            "index_type": "FAISS IndexFlatIP",
            "index_file_exists": os.path.exists(self.faiss_index_path),
            "documents_file_exists": os.path.exists(self.documents_path)
        }
    
    def remove_document_by_id(self, document_id: int):
        """Remove a document from the vector store by document_id"""
        # Find documents to remove
        docs_to_remove = []
        indices_to_remove = []
        
        for i, doc in enumerate(self.documents):
            if doc.metadata.get('document_id') == document_id:
                docs_to_remove.append(doc)
                indices_to_remove.append(i)
        
        if not docs_to_remove:
            print(f"No documents found with document_id: {document_id}")
            return
        
        # Remove documents from list (in reverse order to maintain indices)
        for i in sorted(indices_to_remove, reverse=True):
            del self.documents[i]
        
        # Rebuild FAISS index (since FAISS doesn't support efficient deletion)
        if self.documents:
            # Re-encode all remaining documents
            all_texts = [doc.page_content for doc in self.documents]
            embeddings = self.local_embeddings.encode(all_texts)
            faiss.normalize_L2(embeddings)
            
            # Create new index
            self.index = faiss.IndexFlatIP(self.embedding_dimension)
            self.index.add(embeddings)
        else:
            # If no documents left, create empty index
            self.index = faiss.IndexFlatIP(self.embedding_dimension)
        
        # Save updated index
        self._save_vector_store()
        
        print(f"Removed {len(docs_to_remove)} documents with ID {document_id}. Index rebuilt with {self.index.ntotal} vectors.")
    
    def clear_vector_store(self):
        """Clear all vectors and documents from the store"""
        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        self.documents = []
        
        # Remove saved files
        try:
            if os.path.exists(self.faiss_index_path):
                os.remove(self.faiss_index_path)
            if os.path.exists(self.documents_path):
                os.remove(self.documents_path)
            print("Vector store cleared successfully")
        except Exception as e:
            print(f"Error clearing vector store files: {e}")
