from typing import List, Dict, Any, Optional, Tuple
import os
import time
import logging
import re
import shutil
from datetime import datetime, timedelta
import numpy as np
import faiss
import pickle
from sentence_transformers import SentenceTransformer, CrossEncoder
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from sklearn.metrics.pairwise import cosine_similarity
from whoosh import index, fields, qparser, scoring
from whoosh.analysis import StandardAnalyzer
from whoosh.filedb.filestore import FileStorage
import tempfile

logger = logging.getLogger(__name__)

class HybridContextualRAG:
    """
    Enhanced RAG system with:
    1. Hybrid retrieval (Vector + BM25)
    2. Cross-encoder reranking
    3. Auto reindexing
    4. Evaluation metrics
    """
    def __init__(self):
        try:
            self.github_token = os.getenv("GITHUB_TOKEN")
            self.model_name = os.getenv("MODEL_NAME", "gpt-oss:20b")
            self.api_base = os.getenv("GITHUB_API_BASE", "https://fc5d1d0fc900.ngrok-free.app")
            
            # Import requests for API calls
            import requests
            self.requests = requests
            
            # Embedding models
            embedding_model = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
            self.local_embeddings = SentenceTransformer(embedding_model)
            self.embedding_dimension = self.local_embeddings.get_sentence_embedding_dimension()
            
            # Cross-encoder for reranking
            reranker_model = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
            try:
                self.cross_encoder = CrossEncoder(reranker_model)
                self.has_reranker = True
                logger.info(f"Loaded cross-encoder: {reranker_model}")
            except Exception as e:
                logger.warning(f"Failed to load cross-encoder {reranker_model}: {e}")
                self.cross_encoder = None
                self.has_reranker = False
            
            # Configuration
            self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.25"))
            self.top_k = int(os.getenv("TOP_K", "50"))  # Retrieve more for reranking
            self.final_k = int(os.getenv("FINAL_K", "5"))  # Final documents to use
            self.chunk_size = int(os.getenv("CHUNK_SIZE", "600"))
            self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "150"))
            self.reindex_threshold_hours = int(os.getenv("REINDEX_HOURS", "24"))
            
            # Storage paths
            self.data_dir = "data"
            self.faiss_index_path = os.path.join(self.data_dir, "faiss_index.bin")
            self.documents_path = os.path.join(self.data_dir, "documents.pkl")
            self.bm25_index_dir = os.path.join(self.data_dir, "bm25_index")
            self.metadata_path = os.path.join(self.data_dir, "index_metadata.pkl")
            
            # Initialize storage
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Vector store
            self.index = faiss.IndexFlatIP(self.embedding_dimension)
            self.documents = []
            self.context_memory = {}
            
            # BM25 index
            self.bm25_index = None
            self.bm25_searcher = None
            
            # Text splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
            )
            
            # Load existing indices
            self._load_indices()
            
            # Auto-reindex check
            self._check_auto_reindex()
            
        except Exception as e:
            logger.error(f"Failed to initialize HybridContextualRAG: {e}")
            # Set minimal defaults to prevent AttributeError
            self.has_reranker = False
            self.cross_encoder = None
            self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=150)
            self.embedding_dimension = 384
            self.index = faiss.IndexFlatIP(384)
            self.documents = []
            self.context_memory = {}
            raise
        
    def _load_indices(self):
        """Load both FAISS and BM25 indices"""
        try:
            # Load FAISS
            if os.path.exists(self.faiss_index_path) and os.path.exists(self.documents_path):
                self.index = faiss.read_index(self.faiss_index_path)
                with open(self.documents_path, 'rb') as f:
                    self.documents = pickle.load(f)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            
            # Load BM25
            if os.path.exists(self.bm25_index_dir):
                self._load_bm25_index()
                logger.info("Loaded BM25 index")
            else:
                logger.info("No BM25 index found, will create on first add")
                
        except Exception as e:
            logger.error(f"Error loading indices: {e}")
            self._initialize_empty_indices()
    
    def _initialize_empty_indices(self):
        """Initialize empty indices"""
        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        self.documents = []
        self.bm25_index = None
        self.bm25_searcher = None
    
    def _create_bm25_schema(self):
        """Create Whoosh schema for BM25"""
        return fields.Schema(
            doc_id=fields.ID(stored=True, unique=True),
            content=fields.TEXT(stored=True, analyzer=StandardAnalyzer()),
            title=fields.TEXT(stored=True),
            source=fields.TEXT(stored=True),
            chunk_index=fields.NUMERIC(stored=True)
        )
    
    def _load_bm25_index(self):
        """Load existing BM25 index"""
        try:
            storage = FileStorage(self.bm25_index_dir)
            self.bm25_index = storage.open_index()
            self.bm25_searcher = self.bm25_index.searcher()
        except Exception as e:
            logger.error(f"Failed to load BM25 index: {e}")
            self.bm25_index = None
            self.bm25_searcher = None
    
    def _save_indices(self):
        """Save both FAISS and BM25 indices"""
        try:
            # Save FAISS
            faiss.write_index(self.index, self.faiss_index_path)
            with open(self.documents_path, 'wb') as f:
                pickle.dump(self.documents, f)
            
            # Save metadata
            metadata = {
                "last_reindex": datetime.now(),
                "total_documents": len(self.documents),
                "total_vectors": self.index.ntotal
            }
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
                
            logger.info(f"Saved indices with {self.index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Error saving indices: {e}")
    
    def _check_auto_reindex(self):
        """Check if auto-reindex is needed"""
        try:
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                last_reindex = metadata.get("last_reindex")
                if last_reindex and isinstance(last_reindex, datetime):
                    hours_since = (datetime.now() - last_reindex).total_seconds() / 3600
                    if hours_since > self.reindex_threshold_hours:
                        logger.info(f"Auto-reindex triggered after {hours_since:.1f} hours")
                        self._rebuild_indices()
        except Exception as e:
            logger.warning(f"Auto-reindex check failed: {e}")
    
    def _rebuild_indices(self):
        """Rebuild both indices from documents"""
        if not self.documents:
            return
            
        logger.info("Rebuilding indices...")
        
        # Rebuild FAISS
        all_texts = [doc.page_content for doc in self.documents]
        embeddings = self.local_embeddings.encode(all_texts, show_progress_bar=True)
        embeddings = embeddings.astype('float32')
        faiss.normalize_L2(embeddings)
        
        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        self.index.add(embeddings)
        
        # Rebuild BM25
        self._rebuild_bm25_index()
        
        # Save
        self._save_indices()
        logger.info("Indices rebuilt successfully")
    
    def _rebuild_bm25_index(self):
        """Rebuild BM25 index"""
        try:
            # Remove old index
            if os.path.exists(self.bm25_index_dir):
                shutil.rmtree(self.bm25_index_dir)
            
            # Create new index
            os.makedirs(self.bm25_index_dir, exist_ok=True)
            storage = FileStorage(self.bm25_index_dir)
            self.bm25_index = storage.create_index(self._create_bm25_schema())
            
            # Add documents
            writer = self.bm25_index.writer()
            for i, doc in enumerate(self.documents):
                writer.add_document(
                    doc_id=f"doc_{i}",
                    content=doc.page_content,
                    title=doc.metadata.get('source', ''),
                    source=doc.metadata.get('source', ''),
                    chunk_index=doc.metadata.get('chunk_index', 0)
                )
            writer.commit()
            
            # Update searcher
            if self.bm25_searcher:
                self.bm25_searcher.close()
            self.bm25_searcher = self.bm25_index.searcher()
            
        except Exception as e:
            logger.error(f"Failed to rebuild BM25 index: {e}")
            self.bm25_index = None
            self.bm25_searcher = None
    
    async def add_documents(self, documents: List[Document]):
        """Add documents with hybrid indexing"""
        if not documents:
            return
            
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
                        "chunk_index": i,
                        "original_doc_id": doc.metadata.get('document_id'),
                        "added_timestamp": datetime.now().isoformat()
                    }
                )
                all_chunks.append(chunk_doc)
        
        if not all_chunks:
            return
        
        # Add to vector index
        chunk_texts = [chunk.page_content for chunk in all_chunks]
        embeddings = self.local_embeddings.encode(chunk_texts, show_progress_bar=True)
        embeddings = embeddings.astype('float32')
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        
        # Add to BM25 index
        self._add_to_bm25(all_chunks)
        
        # Store documents
        self.documents.extend(all_chunks)
        
        # Save indices
        self._save_indices()
        
        logger.info(f"Added {len(all_chunks)} chunks. Total: {self.index.ntotal} vectors")
        return len(all_chunks)
    
    def _add_to_bm25(self, chunks: List[Document]):
        """Add chunks to BM25 index"""
        try:
            # Create index if it doesn't exist
            if self.bm25_index is None:
                os.makedirs(self.bm25_index_dir, exist_ok=True)
                storage = FileStorage(self.bm25_index_dir)
                self.bm25_index = storage.create_index(self._create_bm25_schema())
                if self.bm25_searcher:
                    self.bm25_searcher.close()
                self.bm25_searcher = self.bm25_index.searcher()
            
            # Add documents
            writer = self.bm25_index.writer()
            start_id = len(self.documents)
            
            for i, chunk in enumerate(chunks):
                writer.add_document(
                    doc_id=f"doc_{start_id + i}",
                    content=chunk.page_content,
                    title=chunk.metadata.get('source', ''),
                    source=chunk.metadata.get('source', ''),
                    chunk_index=chunk.metadata.get('chunk_index', 0)
                )
            writer.commit()
            
            # Update searcher
            if self.bm25_searcher:
                self.bm25_searcher.close()
            self.bm25_searcher = self.bm25_index.searcher()
            
        except Exception as e:
            logger.error(f"Failed to add to BM25 index: {e}")
    
    def vector_search(self, query: str, top_k: int = None) -> List[Tuple[Document, float]]:
        """Pure vector search"""
        if self.index.ntotal == 0:
            return []
            
        top_k = top_k or self.top_k
        
        # Generate and normalize query embedding
        query_embedding = self.local_embeddings.encode([query])
        query_embedding = query_embedding.astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Search
        similarities, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
        
        # Filter and return
        results = []
        for similarity, idx in zip(similarities[0], indices[0]):
            if similarity > self.similarity_threshold and idx < len(self.documents):
                results.append((self.documents[idx], float(similarity)))
        
        return results
    
    def bm25_search(self, query: str, top_k: int = None) -> List[Tuple[Document, float]]:
        """Pure BM25 search"""
        if not self.bm25_searcher:
            return []
            
        top_k = top_k or self.top_k
        
        try:
            # Parse query
            parser = qparser.QueryParser("content", self.bm25_index.schema)
            query_obj = parser.parse(query)
            
            # Search
            results = self.bm25_searcher.search(query_obj, limit=top_k)
            
            # Convert to our format
            bm25_results = []
            for hit in results:
                doc_id = int(hit['doc_id'].split('_')[1])
                if doc_id < len(self.documents):
                    doc = self.documents[doc_id]
                    score = hit.score
                    bm25_results.append((doc, score))
            
            return bm25_results
            
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []
    
    def hybrid_search(self, query: str, alpha: float = 0.7) -> List[Tuple[Document, float]]:
        """
        Hybrid search combining vector and BM25
        alpha: weight for vector search (1-alpha for BM25)
        """
        # Get results from both methods
        vector_results = self.vector_search(query, self.top_k)
        bm25_results = self.bm25_search(query, self.top_k)
        
        # Create score mapping
        doc_scores = {}
        
        # Normalize and combine vector scores
        if vector_results:
            max_vec_score = max(score for _, score in vector_results)
            for doc, score in vector_results:
                doc_id = id(doc)
                normalized_score = score / max_vec_score if max_vec_score > 0 else 0
                doc_scores[doc_id] = {
                    'doc': doc,
                    'vector_score': normalized_score,
                    'bm25_score': 0.0
                }
        
        # Normalize and combine BM25 scores
        if bm25_results:
            max_bm25_score = max(score for _, score in bm25_results)
            for doc, score in bm25_results:
                doc_id = id(doc)
                normalized_score = score / max_bm25_score if max_bm25_score > 0 else 0
                if doc_id in doc_scores:
                    doc_scores[doc_id]['bm25_score'] = normalized_score
                else:
                    doc_scores[doc_id] = {
                        'doc': doc,
                        'vector_score': 0.0,
                        'bm25_score': normalized_score
                    }
        
        # Calculate hybrid scores
        hybrid_results = []
        for doc_id, scores in doc_scores.items():
            hybrid_score = (alpha * scores['vector_score'] + 
                          (1 - alpha) * scores['bm25_score'])
            if hybrid_score > 0:  # Only include docs with some relevance
                hybrid_results.append((scores['doc'], hybrid_score))
        
        # Sort by hybrid score
        hybrid_results.sort(key=lambda x: x[1], reverse=True)
        
        return hybrid_results[:self.top_k]
    
    def rerank_with_cross_encoder(self, query: str, doc_score_pairs: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        """Rerank using cross-encoder"""
        if not self.has_reranker or not doc_score_pairs:
            return doc_score_pairs
        
        try:
            # Prepare inputs for cross-encoder
            pairs = [(query, doc.page_content) for doc, _ in doc_score_pairs]
            
            # Get cross-encoder scores
            cross_scores = self.cross_encoder.predict(pairs)
            
            # Combine with original scores
            reranked = []
            for i, (doc, original_score) in enumerate(doc_score_pairs):
                # Weighted combination: 70% cross-encoder, 30% original
                combined_score = 0.7 * cross_scores[i] + 0.3 * original_score
                reranked.append((doc, combined_score))
            
            # Sort by combined score
            reranked.sort(key=lambda x: x[1], reverse=True)
            
            return reranked[:self.final_k]
            
        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}")
            return doc_score_pairs[:self.final_k]
    
    def smart_search(self, query: str) -> List[Document]:
        """
        Smart search that chooses the best strategy:
        1. Hybrid search for general queries
        2. Pure vector for semantic queries  
        3. Pure BM25 for exact term queries
        4. Cross-encoder reranking when available
        """
        # Analyze query to choose strategy
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', query))
        has_quotes = '"' in query
        has_exact_terms = has_quotes or re.search(r'\b(exactly|precisely|具體|確切)\b', query, re.I)
        
        # Choose search strategy
        if has_exact_terms and not has_chinese:
            # Prefer BM25 for exact searches
            results = self.bm25_search(query, self.top_k)
            logger.debug(f"Using BM25 search for exact query: {query}")
        elif has_chinese and not has_exact_terms:
            # Prefer vector for semantic Chinese queries
            results = self.vector_search(query, self.top_k)
            logger.debug(f"Using vector search for semantic query: {query}")
        else:
            # Use hybrid for balanced queries
            results = self.hybrid_search(query)
            logger.debug(f"Using hybrid search for query: {query}")
        
        # Apply cross-encoder reranking
        if results:
            results = self.rerank_with_cross_encoder(query, results)
        
        # Return only documents (extract from tuples)
        return [doc for doc, score in results] if results else []
    
    def build_context_prompt(self, query: str, relevant_docs: List[Document], 
                           conversation_id: Optional[int] = None) -> str:
        """Build enhanced context-aware prompt with citations"""
        # Get conversation history
        conversation_context = ""
        if conversation_id and conversation_id in self.context_memory:
            recent_context = self.context_memory[conversation_id][-3:]
            for exchange in recent_context:
                conversation_context += f"用戶: {exchange['user']}\nAI: {exchange['assistant']}\n\n"
        
        # Build document context with improved citations
        document_context = ""
        sources = []
        for i, doc in enumerate(relevant_docs):
            source = doc.metadata.get('source', '未知來源')
            sources.append(source)
            chunk_id = doc.metadata.get('chunk_index', 0)
            document_context += f"文檔 [{i+1}] (來源: {source}, 段落: {chunk_id}):\n{doc.page_content}\n\n"
        
        # Enhanced prompt with citation requirements
        prompt = f"""你是一個專業的繁體中文智能助手。請根據提供的文檔內容回答用戶問題，並嚴格遵循以下要求：

對話歷史:
{conversation_context}

相關文檔內容:
{document_context}

用戶問題: {query}

回答要求：
1. 使用繁體中文回答
2. 僅基於上述文檔內容回答，不要添加文檔外的信息
3. 回答時必須引用來源，格式：[來源：文檔名稱]
4. 如果文檔中沒有相關信息，請明確說明「根據提供的文檔，找不到相關信息」
5. 回答要條理清晰、結構化呈現
6. 對於數據、日期、專有名詞等關鍵信息，務必準確引用

請提供回答："""
        
        return prompt
    
    async def call_llm_api(self, prompt: str) -> str:
        """Enhanced LLM API call with Ollama format"""
        try:
            # Use Ollama format directly
            url = f"{self.api_base}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False  # Get complete response at once
            }
            
            headers = {"Content-Type": "application/json"}
            
            resp = self.requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            
            data = resp.json()
            response_text = data.get("response", "").strip()
            
            if response_text:
                return response_text
            else:
                return "抱歉，模型沒有返回有效回應。"
                
        except self.requests.exceptions.Timeout:
            return "抱歉，請求超時。請稍後再試。"
        except self.requests.exceptions.ConnectionError:
            return "抱歉，無法連接到語言模型服務。請檢查網路連接。"
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return f"抱歉，生成回應時出現錯誤: {str(e)}"
    
    async def generate_response(self, query: str, conversation_id: Optional[int] = None) -> Dict[str, Any]:
        """Generate response using enhanced RAG pipeline"""
        start_time = time.time()
        
        # Smart retrieval
        relevant_docs = self.smart_search(query)
        retrieval_time = time.time() - start_time
        
        # Build context prompt
        context_prompt = self.build_context_prompt(query, relevant_docs, conversation_id)
        
        # Generate response
        generation_start = time.time()
        answer = await self.call_llm_api(context_prompt)
        generation_time = time.time() - generation_start
        
        # Update conversation memory
        if conversation_id:
            if conversation_id not in self.context_memory:
                self.context_memory[conversation_id] = []
            
            self.context_memory[conversation_id].append({
                "user": query,
                "assistant": answer,
                "timestamp": time.time(),
                "context_used": len(relevant_docs),
                "sources": [doc.metadata.get('source', '未知') for doc in relevant_docs],
                "retrieval_time": retrieval_time,
                "generation_time": generation_time
            })
            
            # Keep only recent exchanges
            if len(self.context_memory[conversation_id]) > 10:
                self.context_memory[conversation_id] = self.context_memory[conversation_id][-10:]
        
        # Prepare sources info
        sources_info = []
        for doc in relevant_docs[:3]:  # Top 3 sources
            sources_info.append({
                "source": doc.metadata.get('source', '未知'),
                "chunk": doc.metadata.get('chunk_index', 0),
                "snippet": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            })
        
        return {
            "answer": answer,
            "context_used": len(relevant_docs),
            "sources": [doc.metadata.get('source', '未知') for doc in relevant_docs[:3]],
            "sources_detail": sources_info,
            "retrieval_time": retrieval_time,
            "generation_time": generation_time,
            "total_time": time.time() - start_time
        }
    
    def remove_document_by_id(self, document_id: int):
        """Enhanced document removal with proper index rebuilding"""
        # Find documents to remove
        docs_to_remove_indices = []
        for i, doc in enumerate(self.documents):
            if doc.metadata.get('document_id') == document_id or doc.metadata.get('original_doc_id') == document_id:
                docs_to_remove_indices.append(i)
        
        if not docs_to_remove_indices:
            logger.warning(f"No documents found with document_id: {document_id}")
            return
        
        # Remove documents (reverse order to maintain indices)
        for i in sorted(docs_to_remove_indices, reverse=True):
            del self.documents[i]
        
        # Rebuild indices
        self._rebuild_indices()
        
        logger.info(f"Removed {len(docs_to_remove_indices)} chunks for document_id {document_id}")
    
    def clear_vector_store(self):
        """Clear all data"""
        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        self.documents = []
        self.context_memory = {}
        
        # Close BM25 searcher
        if self.bm25_searcher:
            self.bm25_searcher.close()
            self.bm25_searcher = None
        
        # Remove files
        for path in [self.faiss_index_path, self.documents_path, self.metadata_path]:
            if os.path.exists(path):
                os.remove(path)
        
        if os.path.exists(self.bm25_index_dir):
            shutil.rmtree(self.bm25_index_dir)
        
        self.bm25_index = None
        logger.info("Vector store cleared completely")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Enhanced statistics"""
        bm25_status = "Available" if self.bm25_index else "Not Available"
        reranker_status = "Available" if self.has_reranker else "Not Available"
        
        return {
            "total_documents": len(self.documents),
            "total_conversations": len(self.context_memory),
            "total_vectors": self.index.ntotal,
            "embedding_dimension": self.embedding_dimension,
            "bm25_status": bm25_status,
            "reranker_status": reranker_status,
            "similarity_threshold": self.similarity_threshold,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "last_reindex": self._get_last_reindex_time()
        }
    
    def _get_last_reindex_time(self) -> Optional[str]:
        """Get last reindex time"""
        try:
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                last_reindex = metadata.get("last_reindex")
                if last_reindex and isinstance(last_reindex, datetime):
                    return last_reindex.isoformat()
        except Exception:
            pass
        return None
    
    def evaluate_retrieval(self, test_queries: List[str], gold_doc_ids: List[List[int]], k_values: List[int] = [1, 3, 5, 10]) -> Dict[str, Any]:
        """
        Evaluate retrieval performance
        test_queries: List of test queries
        gold_doc_ids: List of lists containing relevant document IDs for each query
        k_values: Values of k for recall@k and precision@k
        """
        if len(test_queries) != len(gold_doc_ids):
            raise ValueError("Number of queries must match number of gold standard lists")
        
        results = {f"recall@{k}": [] for k in k_values}
        results.update({f"precision@{k}": [] for k in k_values})
        results["mrr"] = []
        
        for query, gold_ids in zip(test_queries, gold_doc_ids):
            # Get retrieval results
            doc_score_pairs = self.hybrid_search(query, alpha=0.7)
            retrieved_doc_ids = [doc.metadata.get('document_id', doc.metadata.get('original_doc_id', -1)) 
                               for doc, _ in doc_score_pairs]
            
            # Calculate metrics for each k
            for k in k_values:
                top_k_retrieved = retrieved_doc_ids[:k]
                
                # Recall@k
                relevant_retrieved = len(set(top_k_retrieved) & set(gold_ids))
                recall = relevant_retrieved / len(gold_ids) if gold_ids else 0
                results[f"recall@{k}"].append(recall)
                
                # Precision@k
                precision = relevant_retrieved / k if k > 0 else 0
                results[f"precision@{k}"].append(precision)
            
            # MRR (Mean Reciprocal Rank)
            mrr = 0
            for i, doc_id in enumerate(retrieved_doc_ids):
                if doc_id in gold_ids:
                    mrr = 1 / (i + 1)
                    break
            results["mrr"].append(mrr)
        
        # Calculate averages
        avg_results = {}
        for metric, values in results.items():
            avg_results[f"avg_{metric}"] = sum(values) / len(values) if values else 0
            avg_results[f"{metric}_std"] = np.std(values) if values else 0
        
        avg_results["num_queries"] = len(test_queries)
        avg_results["evaluation_timestamp"] = datetime.now().isoformat()
        
        return avg_results
    
    def force_reindex(self):
        """Force immediate reindexing"""
        logger.info("Forcing reindex...")
        self._rebuild_indices()
        return True
    
    def get_vector_store_info(self) -> Dict[str, Any]:
        """Enhanced vector store information"""
        return {
            "total_vectors": self.index.ntotal,
            "total_documents": len(self.documents),
            "embedding_dimension": self.embedding_dimension,
            "index_type": "FAISS IndexFlatIP + Whoosh BM25",
            "vector_index_exists": os.path.exists(self.faiss_index_path),
            "bm25_index_exists": os.path.exists(self.bm25_index_dir),
            "documents_file_exists": os.path.exists(self.documents_path),
            "reranker_available": self.has_reranker,
            "last_reindex": self._get_last_reindex_time(),
            "auto_reindex_hours": self.reindex_threshold_hours
        }
    
    def clear_conversation_context(self, conversation_id: int):
        """Clear conversation context"""
        if conversation_id in self.context_memory:
            del self.context_memory[conversation_id]
            logger.info(f"Cleared context for conversation {conversation_id}")

# For backward compatibility
ContextualRAG = HybridContextualRAG