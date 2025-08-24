from typing import List, Dict, Any, Optional
import os
import openai
import time
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import json
import numpy as np
from sentence_transformers import SentenceTransformer

class ContextualRAG:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        # configure openai key if available
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        
        # Initialize embeddings (OpenAIEmbeddings only if key present)
        self.embeddings = None
        if self.openai_api_key:
            try:
                self.embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)
            except Exception:
                # If creation fails, keep embeddings None and allow service to start
                self.embeddings = None
        self.local_embeddings = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Vector store
        self.vector_store = None
        self.context_memory = {}  # Store conversation context
        
        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(os.getenv("CHUNK_SIZE", 1000)),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 200)),
            length_function=len,
        )
        
    async def initialize_vector_store(self, documents: List[Document] = None):
        """Initialize or load the vector store"""
        vector_db_path = os.getenv("VECTOR_DB_PATH", "./data/vector_db")
        
        if os.path.exists(vector_db_path) and documents is None:
            # Load existing vector store (only if embeddings available)
            if self.embeddings is not None:
                self.vector_store = FAISS.load_local(vector_db_path, self.embeddings)
            else:
                self.vector_store = None
        elif documents:
            # Create new vector store with documents
            texts = []
            metadatas = []
            
            for doc in documents:
                chunks = self.text_splitter.split_text(doc.page_content)
                for i, chunk in enumerate(chunks):
                    texts.append(chunk)
                    metadatas.append({
                        **doc.metadata,
                        "chunk_id": i,
                        "total_chunks": len(chunks)
                    })
            
            if self.embeddings is not None:
                self.vector_store = FAISS.from_texts(
                    texts, self.embeddings, metadatas=metadatas
                )
            else:
                # Can't create vector store without embeddings (OpenAI key missing)
                self.vector_store = None
            
            # Save vector store
            os.makedirs(os.path.dirname(vector_db_path), exist_ok=True)
            self.vector_store.save_local(vector_db_path)
        else:
            # Create empty vector store
            self.vector_store = FAISS.from_texts(
                [""], self.embeddings, metadatas=[{}]
            )
    
    def add_documents(self, documents: List[Document]):
        """Add new documents to the vector store"""
        if not self.vector_store:
            # If embeddings not configured, skip adding and return
            if self.embeddings is None:
                return
            return self.initialize_vector_store(documents)
        
        texts = []
        metadatas = []
        
        for doc in documents:
            chunks = self.text_splitter.split_text(doc.page_content)
            for i, chunk in enumerate(chunks):
                texts.append(chunk)
                metadatas.append({
                    **doc.metadata,
                    "chunk_id": i,
                    "total_chunks": len(chunks)
                })
        
        self.vector_store.add_texts(texts, metadatas=metadatas)
        
        # Save updated vector store
        vector_db_path = os.getenv("VECTOR_DB_PATH", "./data/vector_db")
        self.vector_store.save_local(vector_db_path)
    
    def get_contextual_chunks(self, query: str, conversation_id: int, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve contextually relevant chunks using conversation history"""
        if not self.vector_store:
            return []
        
        # Get conversation context
        conversation_context = self.context_memory.get(conversation_id, [])
        
        # Enhanced query with conversation context
        enhanced_query = query
        if conversation_context:
            # Take last 3 exchanges for context
            recent_context = conversation_context[-6:]  # 3 user + 3 bot messages
            context_text = " ".join([msg["content"] for msg in recent_context])
            enhanced_query = f"Context: {context_text}\n\nCurrent question: {query}"
        
        # Retrieve relevant documents
        docs = self.vector_store.similarity_search_with_score(enhanced_query, k=k)
        
        # Re-rank based on conversation context
        if conversation_context:
            docs = self._rerank_with_context(docs, conversation_context, query)
        
        # Format results
        results = []
        for doc, score in docs:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": float(score),
                "contextual_relevance": self._calculate_contextual_relevance(
                    doc.page_content, conversation_context, query
                )
            })
        
        return results
    
    def _rerank_with_context(self, docs, conversation_context, query):
        """Re-rank documents based on conversation context"""
        if not conversation_context:
            return docs
        
        # Calculate context similarity for each document
        context_text = " ".join([msg["content"] for msg in conversation_context[-4:]])
        
        reranked_docs = []
        for doc, score in docs:
            # Calculate semantic similarity with context
            context_sim = self._calculate_semantic_similarity(doc.page_content, context_text)
            query_sim = self._calculate_semantic_similarity(doc.page_content, query)
            
            # Combined score: original similarity + context boost
            combined_score = score + (context_sim * 0.3) + (query_sim * 0.7)
            reranked_docs.append((doc, combined_score))
        
        # Sort by combined score
        reranked_docs.sort(key=lambda x: x[1])
        return reranked_docs
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        try:
            embeddings1 = self.local_embeddings.encode([text1])
            embeddings2 = self.local_embeddings.encode([text2])
            
            # Cosine similarity
            similarity = np.dot(embeddings1[0], embeddings2[0]) / (
                np.linalg.norm(embeddings1[0]) * np.linalg.norm(embeddings2[0])
            )
            return float(similarity)
        except:
            return 0.0
    
    def _calculate_contextual_relevance(self, content: str, conversation_context: List[Dict], query: str) -> float:
        """Calculate how relevant the content is given the conversation context"""
        if not conversation_context:
            return 0.0
        
        # Extract keywords from recent conversation
        recent_messages = [msg["content"] for msg in conversation_context[-4:]]
        context_keywords = self._extract_keywords(" ".join(recent_messages))
        query_keywords = self._extract_keywords(query)
        content_keywords = self._extract_keywords(content)
        
        # Calculate keyword overlap
        context_overlap = len(set(context_keywords) & set(content_keywords))
        query_overlap = len(set(query_keywords) & set(content_keywords))
        
        # Normalize by content length
        total_keywords = len(content_keywords) if content_keywords else 1
        relevance = (context_overlap * 0.3 + query_overlap * 0.7) / total_keywords
        
        return min(relevance, 1.0)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Simple keyword extraction (can be enhanced with NLP libraries)"""
        # Remove common words and split
        stop_words = {"the", "is", "at", "which", "on", "and", "or", "but", "in", "with", "to", "for", "of", "as", "by"}
        words = text.lower().split()
        keywords = [word.strip(".,!?;:") for word in words if word.strip(".,!?;:") not in stop_words and len(word) > 2]
        return list(set(keywords))
    
    def update_conversation_context(self, conversation_id: int, message: str, is_user: bool):
        """Update conversation context memory"""
        if conversation_id not in self.context_memory:
            self.context_memory[conversation_id] = []
        
        self.context_memory[conversation_id].append({
            "content": message,
            "is_user": is_user,
            "timestamp": time.time()
        })
        
        # Keep only last 20 messages to prevent memory bloat
        if len(self.context_memory[conversation_id]) > 20:
            self.context_memory[conversation_id] = self.context_memory[conversation_id][-20:]
    
    async def generate_response(self, query: str, conversation_id: int, max_tokens: int = None) -> Dict[str, Any]:
        """Generate response using contextual RAG"""
        # Get relevant context
        relevant_chunks = self.get_contextual_chunks(query, conversation_id)
        
        # Prepare context for LLM
        context_text = ""
        if relevant_chunks:
            context_text = "\n\n".join([
                f"Source {i+1} (Relevance: {chunk['relevance_score']:.2f}):\n{chunk['content']}"
                for i, chunk in enumerate(relevant_chunks[:3])  # Top 3 chunks
            ])
        
        # Get conversation history for context
        conversation_context = self.context_memory.get(conversation_id, [])
        recent_history = ""
        if conversation_context:
            recent_messages = conversation_context[-6:]  # Last 3 exchanges
            for msg in recent_messages:
                role = "User" if msg["is_user"] else "Assistant"
                recent_history += f"{role}: {msg['content']}\n"
        
        # Construct prompt
        prompt = self._build_contextual_prompt(query, context_text, recent_history)
        
        try:
            # Generate response using OpenAI
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant. Use the provided context to answer questions accurately and helpfully. If the context doesn't contain relevant information, say so clearly."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens or int(os.getenv("MAX_TOKENS", 4000)),
                temperature=float(os.getenv("TEMPERATURE", 0.7))
            )
            
            answer = response.choices[0].message.content
            
            # Update conversation context
            self.update_conversation_context(conversation_id, query, True)
            self.update_conversation_context(conversation_id, answer, False)
            
            return {
                "answer": answer,
                "context_used": context_text,
                "sources": relevant_chunks,
                "conversation_id": conversation_id
            }
            
        except Exception as e:
            return {
                "answer": f"抱歉，生成回應時發生錯誤: {str(e)}",
                "context_used": "",
                "sources": [],
                "conversation_id": conversation_id
            }
    
    def _build_contextual_prompt(self, query: str, context: str, history: str) -> str:
        """Build a contextual prompt for the LLM"""
        prompt_parts = []
        
        if history:
            prompt_parts.append(f"對話歷史:\n{history}")
        
        if context:
            prompt_parts.append(f"相關文件內容:\n{context}")
        
        prompt_parts.append(f"用戶問題: {query}")
        prompt_parts.append("請根據上述對話歷史和文件內容回答用戶問題。如果文件內容不足以回答問題，請明確說明。")
        
        return "\n\n".join(prompt_parts)
