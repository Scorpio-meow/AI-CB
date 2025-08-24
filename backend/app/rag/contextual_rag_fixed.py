from typing import List, Dict, Any, Optional
import os
import time
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from openai import OpenAI

class ContextualRAG:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.model_name = os.getenv("MODEL_NAME", "openai/gpt-5-chat")
        self.api_base = os.getenv("GITHUB_API_BASE", "https://models.github.ai/inference")
        
        # Initialize OpenAI client for GitHub Models
        self.client = None
        if self.github_token:
            self.client = OpenAI(
                base_url=self.api_base,
                api_key=self.github_token,
            )
        
        # Initialize local embeddings for semantic search
        self.local_embeddings = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Simple in-memory vector store
        self.documents = []
        self.embeddings_cache = []
        self.context_memory = {}  # Store conversation context
        
        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(os.getenv("CHUNK_SIZE", 1000)),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 200)),
            length_function=len,
        )
        
    async def initialize_vector_store(self, documents: List[Document] = None):
        """Initialize or load the vector store"""
        if documents:
            await self.add_documents(documents)
            
    async def add_documents(self, documents: List[Document]):
        """Add documents to the vector store"""
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
        
        # Generate embeddings for chunks
        chunk_texts = [chunk.page_content for chunk in all_chunks]
        embeddings = self.local_embeddings.encode(chunk_texts)
        
        # Store documents and embeddings
        self.documents.extend(all_chunks)
        self.embeddings_cache.extend(embeddings.tolist())
        
    def semantic_search(self, query: str, top_k: int = 5) -> List[Document]:
        """Perform semantic search using local embeddings"""
        if not self.documents:
            return []
            
        # Generate query embedding
        query_embedding = self.local_embeddings.encode([query])
        
        # Calculate similarities
        similarities = []
        for i, doc_embedding in enumerate(self.embeddings_cache):
            similarity = np.dot(query_embedding[0], doc_embedding) / (
                np.linalg.norm(query_embedding[0]) * np.linalg.norm(doc_embedding)
            )
            similarities.append((similarity, i))
        
        # Sort by similarity and return top-k
        similarities.sort(reverse=True)
        
        relevant_docs = []
        for similarity, idx in similarities[:top_k]:
            if similarity > 0.3:  # Threshold for relevance
                relevant_docs.append(self.documents[idx])
                
        return relevant_docs
    
    def rerank_documents(self, query: str, documents: List[Document]) -> List[Document]:
        """Re-rank documents based on relevance"""
        if not documents:
            return documents
            
        # Simple keyword-based re-ranking
        query_terms = set(query.lower().split())
        scored_docs = []
        
        for doc in documents:
            doc_terms = set(doc.page_content.lower().split())
            overlap = len(query_terms.intersection(doc_terms))
            scored_docs.append((overlap, doc))
        
        # Sort by overlap score
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
        prompt = f"""你是一個智能助手，請根據提供的上下文信息回答用戶問題。

對話歷史:
{conversation_context}

相關文檔:
{document_context}

用戶問題: {query}

請基於上述上下文信息提供準確、有用的回答。如果上下文中沒有相關信息，請誠實地說明並提供一般性的幫助。"""
        
        return prompt
    
    async def call_github_models_api(self, prompt: str) -> str:
        """Call GitHub Models API using OpenAI SDK"""
        if not self.client:
            return "抱歉，GitHub Models API 未配置。"
            
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一個智能助手，請用繁體中文回答問題。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model_name,
                temperature=0.7,
                max_tokens=1000,
                top_p=1.0
            )
            
            return response.choices[0].message.content
                
        except Exception as e:
            print(f"Error calling GitHub Models API: {e}")
            return f"抱歉，生成回應時出現錯誤: {str(e)}"
    
    async def generate_response(self, query: str, conversation_id: Optional[int] = None) -> Dict[str, Any]:
        """Generate response using RAG"""
        # Retrieve relevant documents
        relevant_docs = self.semantic_search(query, top_k=5)
        
        # Re-rank documents
        reranked_docs = self.rerank_documents(query, relevant_docs)
        
        # Build context prompt
        context_prompt = self.build_context_prompt(query, reranked_docs, conversation_id)
        
        # Generate response using GitHub Models
        answer = await self.call_github_models_api(context_prompt)
        
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
            "total_embeddings": len(self.embeddings_cache)
        }
