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
from whoosh.analysis import StandardAnalyzer, Analyzer, Tokenizer, Token
from whoosh.filedb.filestore import FileStorage
from whoosh.writing import AsyncWriter
try:
    import jieba
    _HAS_JIEBA = True
except Exception:
    _HAS_JIEBA = False

# Define Jieba-based analyzer at module level to ensure picklability in Whoosh schema
if _HAS_JIEBA:
    class JiebaTokenizer(Tokenizer):
        def __call__(self, value, positions=False, chars=False, keeporiginal=False,
                     removestops=False, start_pos=0, start_char=0, tokenize=True,
                     mode="default", **kwargs):
            t = Token(positions, chars, removestops=removestops)
            if not tokenize:
                return
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", "ignore")
                except Exception:
                    value = value.decode(errors="ignore")
            pos = start_pos
            char_pos = start_char
            for w in jieba.cut(value, cut_all=False):
                w = w.strip()
                if not w:
                    continue
                t.original = w
                t.text = w
                t.boost = 1.0
                if positions:
                    t.pos = pos
                    pos += 1
                if chars:
                    # best-effort char positions
                    idx = value.find(w, char_pos)
                    if idx < 0:
                        idx = char_pos
                    t.startchar = idx
                    t.endchar = idx + len(w)
                    char_pos = t.endchar
                yield t

    class JiebaAnalyzer(Analyzer):
        def __init__(self):
            self._tokenizer = JiebaTokenizer()

        def __call__(self, value, **kwargs):
            return self._tokenizer(value, **kwargs)

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
            # Fail-fast: require MODEL_NAME and LLM_API_BASE to be provided via environment
            try:
                self.model_name = os.environ["MODEL_NAME"]
            except KeyError:
                raise RuntimeError("Environment variable MODEL_NAME is required but not set. Please set it in .env or the environment.")

            try:
                self.api_base = os.environ["LLM_API_BASE"]
            except KeyError:
                raise RuntimeError("Environment variable LLM_API_BASE is required but not set. Please set it in .env or the environment.")
            
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
            # how many candidates to retrieve before reranking
            self.top_k = int(os.getenv("TOP_K", "50"))
            # default larger candidate pool for reranking
            self.rerank_top_k = int(os.getenv("RERANK_TOP_K", "80"))
            # final docs used downstream
            self.final_k = int(os.getenv("FINAL_K", "10"))
            # reranker weighting and acceptance threshold
            self.rerank_weight = float(os.getenv("RERANK_WEIGHT", "0.8"))  # 0..1 weight for cross-encoder
            self.final_threshold = float(os.getenv("FINAL_THRESHOLD", "0.1"))  # threshold on normalized combined score
            # hybrid fusion controls
            self.hybrid_alpha = float(os.getenv("HYBRID_ALPHA", "0.7"))
            self.normalization = os.getenv("NORMALIZATION", "max").lower()  # 'max' or 'softmax'
            # chunking
            self.chunk_size = int(os.getenv("CHUNK_SIZE", "300"))
            self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "100"))
            self.reindex_threshold_hours = int(os.getenv("REINDEX_HOURS", "24"))
            
            # LLM timeout configuration
            self.llm_timeout = int(os.getenv("LLM_TIMEOUT", "120"))
            
            # Storage paths
            self.data_dir = os.getenv("DATA_DIR", "data")
            self.faiss_index_path = os.getenv("FAISS_INDEX_PATH", os.path.join(self.data_dir, "faiss_index.bin"))
            self.documents_path = os.getenv("DOCUMENTS_PATH", os.path.join(self.data_dir, "documents.pkl"))
            self.bm25_index_dir = os.getenv("BM25_INDEX_DIR", os.path.join(self.data_dir, "bm25_index"))
            self.metadata_path = os.getenv("METADATA_PATH", os.path.join(self.data_dir, "index_metadata.pkl"))
            
            # Initialize storage
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Vector store
            self.index = faiss.IndexFlatIP(self.embedding_dimension)
            self.documents = []
            self.context_memory = {}
            
            # BM25 index
            self.bm25_index = None
            self.bm25_searcher = None
            
            # Text splitter (optimize for Chinese punctuation-aware splitting)
            self.text_splitter = self._create_text_splitter()
            # Inject domain words into jieba to improve BM25 tokenization
            if _HAS_JIEBA:
                try:
                    domain_words = [
                        "補休", "到期", "遞延", "產檢", "育嬰留停", "免刷卡", "時刻維護", "集體異動", "調班",
                        "外勤", "PAKKA", "MES", "薪資條", "在職證明", "眷屬", "健保", "勞保", "資遣",
                        "特休", "颱風", "防災假", "逾期補登", "刷卡", "忘刷", "排班", "輪班", "四週彈性工時",
                        "調班申請", "人事調閱", "加班", "請假", "同意書", "證明"
                    ]
                    for w in domain_words:
                        try:
                            jieba.add_word(w)
                        except Exception:
                            pass
                except Exception:
                    pass
            
            # Load existing indices
            self._load_indices()

            # Auto-reindex check: disabled by default to avoid reindex during
            # FastAPI/uvicorn reload or when multiple processes start.
            # Enable explicitly in a single indexer process by setting
            # environment variable ENABLE_AUTO_REINDEX=1, or call
            # `force_reindex()` / `_rebuild_indices()` from a startup hook.
            if os.getenv("ENABLE_AUTO_REINDEX", "0") == "1":
                self._check_auto_reindex()
            else:
                logger.info("Auto-reindex skipped in init; set ENABLE_AUTO_REINDEX=1 or run reindex in a dedicated indexer/startup hook")
            
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
        # Prefer jieba analyzer for Chinese text if available
        analyzer = self._get_chinese_analyzer()
        return fields.Schema(
            doc_id=fields.ID(stored=True, unique=True),
            content=fields.TEXT(stored=True, analyzer=analyzer),
            title=fields.TEXT(stored=True),
            source=fields.TEXT(stored=True),
            chunk_index=fields.NUMERIC(stored=True)
        )

    def _get_chinese_analyzer(self) -> Analyzer:
        """Return a Whoosh analyzer optimized for Chinese using jieba when available."""
        if _HAS_JIEBA:
            return JiebaAnalyzer()
        # Fallback to StandardAnalyzer when jieba is not available
        return StandardAnalyzer()

    def _create_text_splitter(self) -> RecursiveCharacterTextSplitter:
        """Create a text splitter tuned for Chinese punctuation and sentence breaks."""
        # Prioritize splitting on Chinese punctuation, then on sentences/newlines, then characters
        separators = [
            "\n\n", "。", "！", "？", "；", "：", "，", ", ", ". ", "! ", "? ",
            "\n", "。\n", "；\n", "，\n", "。 ", "； ", "， ", " ", ""
        ]
        return RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=separators,
        )
    
    def _load_bm25_index(self):
        """Load existing BM25 index"""
        try:
            storage = FileStorage(self.bm25_index_dir)
            self.bm25_index = storage.open_index()
            # Use BM25 weighting explicitly
            self.bm25_searcher = self.bm25_index.searcher(weighting=scoring.BM25F())
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
                "total_vectors": self.index.ntotal,
                "tokenizer": "jieba" if _HAS_JIEBA else "standard"
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
                # If tokenizer changed to jieba, rebuild BM25 to ensure compatibility
                tokenizer_used = metadata.get("tokenizer", "standard")
                if _HAS_JIEBA and tokenizer_used != "jieba":
                    logger.info("Detected non-jieba BM25 index metadata. Rebuilding BM25 index with jieba analyzer...")
                    self._rebuild_bm25_index()
                    # update metadata immediately
                    metadata["tokenizer"] = "jieba"
                    metadata["last_reindex"] = datetime.now()
                    with open(self.metadata_path, 'wb') as f:
                        pickle.dump(metadata, f)
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
            # Ensure previous searcher is closed to avoid file locks (Windows)
            if self.bm25_searcher:
                try:
                    self.bm25_searcher.close()
                except Exception:
                    pass
                self.bm25_searcher = None
            # Remove old index
            if os.path.exists(self.bm25_index_dir):
                shutil.rmtree(self.bm25_index_dir)
            
            # Create new index
            os.makedirs(self.bm25_index_dir, exist_ok=True)
            storage = FileStorage(self.bm25_index_dir)
            self.bm25_index = storage.create_index(self._create_bm25_schema())

            # Add documents using AsyncWriter and optional external file lock.
            # Close existing searcher first to avoid Windows file handle locks.
            if self.bm25_searcher:
                try:
                    self.bm25_searcher.close()
                except Exception:
                    pass
                self.bm25_searcher = None

            # Try to use a file lock if available to serialize cross-process writes.
            lock_path = os.path.join(self.bm25_index_dir, "bm25_write.lock")
            use_filelock = False
            try:
                from filelock import FileLock, Timeout
                use_filelock = True
            except Exception:
                FileLock = None
                Timeout = None

            write_attempts = 3
            for attempt in range(write_attempts):
                try:
                    if use_filelock:
                        with FileLock(lock_path, timeout=5):
                            with AsyncWriter(self.bm25_index) as writer:
                                for i, doc in enumerate(self.documents):
                                    writer.add_document(
                                        doc_id=f"doc_{i}",
                                        content=doc.page_content,
                                        title=doc.metadata.get('source', ''),
                                        source=doc.metadata.get('source', ''),
                                        chunk_index=doc.metadata.get('chunk_index', 0)
                                    )
                    else:
                        with AsyncWriter(self.bm25_index) as writer:
                            for i, doc in enumerate(self.documents):
                                writer.add_document(
                                    doc_id=f"doc_{i}",
                                    content=doc.page_content,
                                    title=doc.metadata.get('source', ''),
                                    source=doc.metadata.get('source', ''),
                                    chunk_index=doc.metadata.get('chunk_index', 0)
                                )
                    # success, break out
                    break
                except Exception as e:
                    logger.warning(f"BM25 write attempt {attempt+1} failed: {e}")
                    time.sleep(0.5)

            # Update searcher with BM25 weighting
            if self.bm25_searcher:
                try:
                    self.bm25_searcher.close()
                except Exception:
                    pass
            try:
                self.bm25_searcher = self.bm25_index.searcher(weighting=scoring.BM25F())
            except Exception as e:
                logger.warning(f"Failed to open BM25 searcher after rebuild: {e}")
            
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
        preserved_count = 0
        preserved_sources = set()
        for doc in documents:
            # If metadata requests preserving the whole content, skip splitting
            preserve = bool(doc.metadata.get('preserve_whole')) if doc.metadata and isinstance(doc.metadata, dict) else False
            if preserve:
                preserved_count += 1
                try:
                    preserved_sources.add(doc.metadata.get('source', 'unknown'))
                except Exception:
                    pass
                chunk_doc = Document(
                    page_content=doc.page_content,
                    metadata={
                        **doc.metadata,
                        "chunk_id": f"{doc.metadata.get('source', 'unknown')}_0",
                        "chunk_index": 0,
                        "original_doc_id": doc.metadata.get('document_id'),
                        "added_timestamp": datetime.now().isoformat()
                    }
                )
                all_chunks.append(chunk_doc)
            else:
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
        
        # log debug info if any preserve_whole was used
        if preserved_count > 0:
            try:
                logger.debug(f"preserve_whole used for {preserved_count} document(s); sources={list(preserved_sources)}")
            except Exception:
                logger.debug(f"preserve_whole used for {preserved_count} document(s)")

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
                self.bm25_searcher = self.bm25_index.searcher(weighting=scoring.BM25F())
            
            # Add documents using AsyncWriter; close existing searcher first to avoid file locks on Windows
            if self.bm25_searcher:
                try:
                    self.bm25_searcher.close()
                except Exception:
                    pass
                self.bm25_searcher = None

            start_id = len(self.documents)

            # Optional external file lock to serialize multi-process writes
            lock_path = os.path.join(self.bm25_index_dir, "bm25_write.lock")
            use_filelock = False
            try:
                from filelock import FileLock, Timeout
                use_filelock = True
            except Exception:
                FileLock = None
                Timeout = None

            write_attempts = 3
            for attempt in range(write_attempts):
                try:
                    if use_filelock:
                        with FileLock(lock_path, timeout=5):
                            with AsyncWriter(self.bm25_index) as writer:
                                for i, chunk in enumerate(chunks):
                                    writer.add_document(
                                        doc_id=f"doc_{start_id + i}",
                                        content=chunk.page_content,
                                        title=chunk.metadata.get('source', ''),
                                        source=chunk.metadata.get('source', ''),
                                        chunk_index=chunk.metadata.get('chunk_index', 0)
                                    )
                    else:
                        with AsyncWriter(self.bm25_index) as writer:
                            for i, chunk in enumerate(chunks):
                                writer.add_document(
                                    doc_id=f"doc_{start_id + i}",
                                    content=chunk.page_content,
                                    title=chunk.metadata.get('source', ''),
                                    source=chunk.metadata.get('source', ''),
                                    chunk_index=chunk.metadata.get('chunk_index', 0)
                                )
                    # success
                    break
                except Exception as e:
                    logger.warning(f"BM25 add attempt {attempt+1} failed: {e}")
                    time.sleep(0.3)

            # Update searcher with BM25 weighting
            try:
                if self.bm25_searcher:
                    try:
                        self.bm25_searcher.close()
                    except Exception:
                        pass
                self.bm25_searcher = self.bm25_index.searcher(weighting=scoring.BM25F())
            except Exception as e:
                logger.warning(f"Failed to open BM25 searcher after add: {e}")
            
        except Exception as e:
            logger.error(f"Failed to add to BM25 index: {e}")
    
    def vector_search(self, query: str, top_k: int = None, apply_threshold: bool = True) -> List[Tuple[Document, float]]:
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
            if (not apply_threshold or similarity > self.similarity_threshold) and idx < len(self.documents):
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
    
    def _normalize_scores(self, scores: List[float], method: str = "max") -> List[float]:
        """Normalize a list of scores into 0..1 using max or softmax."""
        if not scores:
            return []
        if method == "softmax":
            a = np.array(scores, dtype=np.float32)
            a = a - np.max(a)
            exp = np.exp(a)
            denom = np.sum(exp)
            if denom <= 0:
                return [0.0 for _ in scores]
            prob = exp / denom
            # re-scale to 0..1 while preserving order (softmax already 0..1)
            return prob.tolist()
        # default: max-normalization
        max_v = max(scores)
        return [(s / max_v) if max_v > 0 else 0.0 for s in scores]

    def hybrid_search(self, query: str, alpha: float = None) -> List[Tuple[Document, float]]:
        """
        Hybrid search combining vector and BM25
        alpha: weight for vector search (1-alpha for BM25)
        """
        alpha = self.hybrid_alpha if alpha is None else alpha
        # Get results from both methods
        vector_results = self.vector_search(query, self.rerank_top_k, apply_threshold=False)
        bm25_results = self.bm25_search(query, self.rerank_top_k)

        # Create score mapping per document
        doc_scores: Dict[int, Dict[str, Any]] = {}

        # Normalize and record vector scores
        if vector_results:
            vec_scores = [score for _, score in vector_results]
            vec_norms = self._normalize_scores(vec_scores, method=self.normalization)
            for (doc, _), norm in zip(vector_results, vec_norms):
                did = id(doc)
                doc_scores[did] = {"doc": doc, "vector_score": float(norm), "bm25_score": 0.0}

        # Normalize and record BM25 scores
        if bm25_results:
            bm_scores = [score for _, score in bm25_results]
            bm_norms = self._normalize_scores(bm_scores, method=self.normalization)
            for (doc, _), norm in zip(bm25_results, bm_norms):
                did = id(doc)
                if did in doc_scores:
                    doc_scores[did]["bm25_score"] = float(norm)
                else:
                    doc_scores[did] = {"doc": doc, "vector_score": 0.0, "bm25_score": float(norm)}

        # Compute hybrid score
        combined: List[Tuple[Document, float]] = []
        for rec in doc_scores.values():
            score = alpha * rec["vector_score"] + (1 - alpha) * rec["bm25_score"]
            if score > 0:
                combined.append((rec["doc"], score))

        combined.sort(key=lambda x: x[1], reverse=True)
        return combined[: self.rerank_top_k]

    def rerank_with_cross_encoder(self, query: str, doc_score_pairs: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        """Rerank candidates using a cross-encoder when available.
        Combines normalized cross-encoder scores with original scores using self.rerank_weight.
        Applies final thresholding and caps to self.final_k.
        """
        if not self.has_reranker or not doc_score_pairs:
            return doc_score_pairs

        try:
            pairs = [(query, d.page_content) for d, _ in doc_score_pairs]
            cross_scores = self.cross_encoder.predict(pairs)
            orig_scores = [s for _, s in doc_score_pairs]

            def _minmax(arr):
                mn, mx = float(np.min(arr)), float(np.max(arr))
                if mx - mn <= 1e-8:
                    return [0.0 for _ in arr]
                return [float((x - mn) / (mx - mn)) for x in arr]

            cs_norm = _minmax(cross_scores)
            os_norm = _minmax(orig_scores)
            w = min(max(self.rerank_weight, 0.0), 1.0)

            combined = [
                (doc, float(w * cs + (1 - w) * os))
                for (doc, _), cs, os in zip(doc_score_pairs, cs_norm, os_norm)
            ]
            # threshold and sort
            combined = [x for x in combined if x[1] >= self.final_threshold]
            combined.sort(key=lambda x: x[1], reverse=True)
            return combined[: self.final_k]
        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}")
            doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
            return doc_score_pairs[: self.final_k]
    
    def smart_search(self, query: str) -> List[Tuple[Document, float]]:
        """
        Smart search that chooses the best strategy:
        1. Hybrid search for general queries
        2. Pure vector for semantic queries  
        3. Pure BM25 for exact term queries
        4. Cross-encoder reranking when available
        """
        # Analyze query to choose strategy
        has_quotes = '"' in query
        has_chinese = bool(re.search(r"[\u4e00-\u9fff]", query))
        has_exact_terms = bool(has_quotes or re.search(r'\b(exactly|precisely|具體|確切)\b', query, re.I))
        faq_keywords = r'(填寫說明|申請|到期|調班|補登|證明|薪資條|特休|補休|育嬰留停|產檢|免刷卡|時刻維護|集體異動|輪班|排班)'
        is_short = len(re.sub(r'\s+', '', query)) <= 25
        contains_faq_kw = bool(re.search(faq_keywords, query))

        # Choose search strategy
        strategy = ""
        if has_exact_terms and not has_chinese:
            # Prefer BM25 for exact searches
            results = self.bm25_search(query, self.rerank_top_k)
            strategy = "bm25"
            logger.info(f"Retrieval strategy=BM25 query='{query}' candidates={len(results)}")
        elif has_chinese and (is_short or contains_faq_kw):
            # Prefer hybrid for FAQ-like short Chinese queries
            results = self.hybrid_search(query, alpha=self.hybrid_alpha)
            strategy = "hybrid"
            logger.info(f"Retrieval strategy=HYBRID(FAQ-like) query='{query}' candidates={len(results)}")
        elif has_chinese and not has_exact_terms:
            # Prefer vector for general semantic Chinese queries
            results = self.vector_search(query, self.rerank_top_k, apply_threshold=False)
            strategy = "vector"
            logger.info(f"Retrieval strategy=VECTOR query='{query}' candidates={len(results)}")
        else:
            # Use hybrid for balanced queries
            results = self.hybrid_search(query, alpha=self.hybrid_alpha)
            strategy = "hybrid"
            logger.info(f"Retrieval strategy=HYBRID(alpha={self.hybrid_alpha}) query='{query}' candidates={len(results)}")

        # Apply cross-encoder reranking
        if results:
            # keep some debug info before rerank
            try:
                preview = [
                    {
                        "source": d.metadata.get('source', '未知'),
                        "chunk": d.metadata.get('chunk_index', 0),
                        "score": round(float(s), 4)
                    }
                    for d, s in results[:5]
                ]
                logger.info(f"Retrieval pre-rerank top5: {preview}")
            except Exception:
                pass
            results = self.rerank_with_cross_encoder(query, results)
            # after rerank
            try:
                preview = [
                    {
                        "source": d.metadata.get('source', '未知'),
                        "chunk": d.metadata.get('chunk_index', 0),
                        "score": round(float(s), 4)
                    }
                    for d, s in results[:5]
                ]
                logger.info(f"Retrieval post-rerank top5: {preview}")
            except Exception:
                pass

        # expose last strategy for external inspection
        try:
            self._last_retrieval_strategy = strategy or "unknown"
        except Exception:
            pass

        return results if results else []
    
    def build_context_prompt(self, query: str, relevant_docs: List[Document], 
                           conversation_id: Optional[int] = None,
                           user_id: Optional[int] = None) -> Tuple[str, List[Dict[str, str]]]:
        """Build enhanced context-aware prompt with System/User separation
        
        Returns:
            Tuple of (user_prompt, conversation_history)
            - user_prompt: The current user message with document context
            - conversation_history: List of previous messages for multi-turn conversation
        """
        # Get conversation history (scoped by user and conversation)
        conversation_history = []
        if conversation_id is not None:
            key = f"{user_id}:{conversation_id}" if user_id is not None else f"{conversation_id}"
            if key in self.context_memory:
                # 只保留最近3輪對話 (6條訊息: user + assistant)
                recent_context = self.context_memory[key][-3:]
                for exchange in recent_context:
                    conversation_history.append({
                        "role": "user",
                        "content": exchange['user']
                    })
                    conversation_history.append({
                        "role": "assistant", 
                        "content": exchange['assistant']
                    })
        
        # Build document context with improved citations (only include top-N to control prompt size)
        document_context = ""
        max_docs = min(len(relevant_docs), 5)
        for i, doc in enumerate(relevant_docs[:max_docs]):
            source = doc.metadata.get('source', '未知來源')
            chunk_id = doc.metadata.get('chunk_index', 0)
            document_context += f"文檔 [{i+1}] (來源: {source}, 段落: {chunk_id}):\n{doc.page_content}\n\n"
        
        # 構建當前用戶訊息 (User role)
        user_prompt = f"""用戶問題: {query}

檔案片段:
{document_context}"""
        
        return user_prompt, conversation_history
    
    async def call_llm_api(self, prompt: str, model_name: str = None, 
                          conversation_history: List[Dict[str, str]] = None) -> str:
        """Enhanced LLM API call with multi-turn conversation support
        
        Args:
            prompt: The current user message
            model_name: Optional model override
            conversation_history: List of previous messages with 'role' and 'content'
        
        Returns:
            The model's response text
        """
        try:
            # Use provided model or fall back to default
            model_to_use = model_name or self.model_name
            
            # Use Ollama chat API for multi-turn conversations
            url = f"{self.api_base}/api/chat"
            
            # Construct messages list
            messages = [
                {
                    "role": "system",
                    "content": """你是神通資訊科技內部的知識型助理，綽號為「通哥」，負責根據用戶問題、對話上下文與檔案片段，產出準確、可追溯的中文回答。

規則：
1) 以中文回答問題。
2) 在回答末尾列出使用到的來源，格式為："[n] 來源名稱 (段落: m)"。若來源未知請標示為「無來源」。
3) 避免編造事實；若資料不足或為推論，請在回覆中明確標註「推論」或回報「無法確定」，並建議下一步可查詢的關鍵字或資料位置。
4) 回應中不得包含任何系統內部實作細節、索引 id 或未經驗證的 URL。"""
                }
            ]
            
            # Add conversation history (if provided, already limited to last 3 turns = 6 messages)
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            payload = {
                "model": model_to_use,
                "messages": messages,
                "stream": False  # Get complete response at once
            }
            
            headers = {
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"  # Required for ngrok tunnels
            }
            
            logger.info(f"Calling LLM API: model={model_to_use}, messages={len(messages)}, url={url}, timeout={self.llm_timeout}s")
            resp = self.requests.post(url, json=payload, headers=headers, timeout=self.llm_timeout)
            resp.raise_for_status()
            
            data = resp.json()
            # Ollama chat API returns message.content
            response_text = data.get("message", {}).get("content", "").strip()
            
            if response_text:
                logger.info(f"LLM response received: {len(response_text)} chars")
                return response_text
            else:
                logger.warning("LLM returned empty response")
                return "抱歉，模型沒有返回有效回應。"
                
        except self.requests.exceptions.Timeout:
            logger.error(f"LLM API timeout after {self.llm_timeout}s for model {model_to_use}")
            return f"抱歉，請求超時 ({self.llm_timeout}秒)。請嘗試使用較小的模型或稍後再試。"
        except self.requests.exceptions.ConnectionError as e:
            logger.error(f"LLM API connection error: {e}")
            return "抱歉，無法連接到語言模型服務。請檢查網路連接或 ngrok 隧道狀態。"
        except self.requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "unknown"
            error_detail = ""
            try:
                error_detail = e.response.text if e.response else ""
            except:
                pass
            logger.error(f"LLM API HTTP error {status_code}: {e}, detail: {error_detail[:200]}")
            if status_code == 500:
                return f"抱歉，模型服務器錯誤 (500)。可能是模型 '{model_to_use}' 負載過重或通過 ngrok 超時，建議切換到較小的模型 (如 gpt-oss:20b)。"
            return f"抱歉，模型 API 返回錯誤 ({status_code}): {str(e)}"
        except Exception as e:
            logger.error(f"LLM API unexpected error: {type(e).__name__}: {e}")
            return f"抱歉，生成回應時出現錯誤: {str(e)}"
    
    async def generate_response(self, query: str, conversation_id: Optional[int] = None, model_name: str = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Generate response using enhanced RAG pipeline with multi-turn conversation support
        
        Args:
            query: The user's question
            conversation_id: Optional conversation ID for context tracking
            model_name: Optional model override
            user_id: Optional user ID for context isolation
            
        Returns:
            Dict containing answer, sources, timing info, and retrieval metadata
        """
        start_time = time.time()
        
        # Smart retrieval (with scores)
        doc_score_pairs = self.smart_search(query)
        retrieval_strategy = getattr(self, "_last_retrieval_strategy", None)
        relevant_docs = [doc for doc, _ in doc_score_pairs]
        retrieval_time = time.time() - start_time
        
        # Build context prompt (returns user_prompt and conversation_history)
        user_prompt, conversation_history = self.build_context_prompt(
            query, relevant_docs, conversation_id, user_id
        )
        
        # Generate response with multi-turn conversation
        generation_start = time.time()
        answer = await self.call_llm_api(user_prompt, model_name, conversation_history)
        generation_time = time.time() - generation_start
        
        # Update conversation memory (scoped by user and conversation)
        if conversation_id is not None:
            key = f"{user_id}:{conversation_id}" if user_id is not None else f"{conversation_id}"
            if key not in self.context_memory:
                self.context_memory[key] = []

            self.context_memory[key].append({
                "user": query,
                "assistant": answer,
                "timestamp": time.time(),
                "context_used": len(relevant_docs),
                "sources": [doc.metadata.get('source', '未知') for doc in relevant_docs],
                "retrieval_time": retrieval_time,
                "generation_time": generation_time
            })

            # Keep only recent exchanges
            if len(self.context_memory[key]) > 10:
                self.context_memory[key] = self.context_memory[key][-10:]
        
        # Prepare sources info
        sources_info = []
        for i, doc in enumerate(relevant_docs[:3]):  # Top 3 sources
            score = doc_score_pairs[i][1] if i < len(doc_score_pairs) else None
            sources_info.append({
                "source": doc.metadata.get('source', '未知'),
                "chunk": doc.metadata.get('chunk_index', 0),
                "score": round(float(score), 4) if score is not None else None,
                "snippet": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            })
        
        return {
            "answer": answer,
            "context_used": len(relevant_docs),
            "sources": [doc.metadata.get('source', '未知') for doc in relevant_docs[:3]],
            "sources_detail": sources_info,
            "retrieval_time": retrieval_time,
            "generation_time": generation_time,
            "total_time": time.time() - start_time,
            "retrieval_strategy": retrieval_strategy
        }
    
    def remove_document_by_id(self, document_id: int, rebuild_bm25: bool = True):
        """Enhanced document removal with optional BM25 rebuild.

        Parameters:
        - document_id: id of the original document to remove
        - rebuild_bm25: whether to rebuild the BM25 index immediately. On Windows
          rebuilding BM25 may fail due to file locks; set to False to skip BM25
          rebuild and only rebuild the FAISS/vector index and persist documents.
        """
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

        # Rebuild FAISS (vector) index and persist documents.
        try:
            if not self.documents:
                # Nothing left: clear store
                self.clear_vector_store()
            else:
                # Recompute embeddings and rebuild FAISS index
                all_texts = [doc.page_content for doc in self.documents]
                embeddings = self.local_embeddings.encode(all_texts, show_progress_bar=False)
                embeddings = embeddings.astype('float32')
                faiss.normalize_L2(embeddings)

                self.index = faiss.IndexFlatIP(self.embedding_dimension)
                self.index.add(embeddings)

                # Optionally rebuild BM25 (may be skipped by callers)
                if rebuild_bm25:
                    try:
                        self._rebuild_bm25_index()
                    except Exception as e:
                        logger.warning(f"BM25 rebuild skipped/failed during remove: {e}")

                # Persist FAISS and documents/metadata (safe even if BM25 skipped)
                try:
                    self._save_indices()
                except Exception as e:
                    logger.error(f"Failed to save indices after removal: {e}")

        except Exception as e:
            logger.error(f"Failed to rebuild indices after removal: {e}")

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
            doc_score_pairs = self.hybrid_search(query, alpha=self.hybrid_alpha)
            # apply reranking if available
            doc_score_pairs = self.rerank_with_cross_encoder(query, doc_score_pairs)
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

    def auto_tune_alpha(self, test_queries: List[str], gold_doc_ids: List[List[int]], 
                         alphas: List[float] = None) -> Dict[str, Any]:
        """Grid search alpha to maximize avg_mrr. Returns best alpha and metrics."""
        if alphas is None:
            alphas = [round(x, 2) for x in np.linspace(0.3, 0.9, 13)]  # 0.3..0.9 step 0.05
        best = {"alpha": None, "avg_mrr": -1, "metrics": None}
        for a in alphas:
            self.hybrid_alpha = a
            metrics = self.evaluate_retrieval(test_queries, gold_doc_ids)
            if metrics.get("avg_mrr", 0) > best["avg_mrr"]:
                best = {"alpha": a, "avg_mrr": metrics.get("avg_mrr", 0), "metrics": metrics}
        return best
    
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