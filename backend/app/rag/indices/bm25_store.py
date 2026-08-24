from typing import List, Tuple, Optional
import os
import time
import shutil
import logging
from ..types import Document
from ..tokenizers import get_chinese_analyzer, HAS_WHOOSH

logger = logging.getLogger(__name__)

if HAS_WHOOSH:
    from whoosh import fields, qparser, scoring
    from whoosh.filedb.filestore import FileStorage
    from whoosh.writing import AsyncWriter
else:
    fields = None  # type: ignore
    qparser = None  # type: ignore
    scoring = None  # type: ignore
    FileStorage = None  # type: ignore
    AsyncWriter = None  # type: ignore


class BM25StoreManager:
    def __init__(self, data_dir: str = "data", bm25_index_dir: Optional[str] = None):
        self.data_dir = data_dir
        self.bm25_index_dir = bm25_index_dir or os.path.join(self.data_dir, "bm25_index")
        self.bm25_index = None
        self.bm25_searcher = None
        if HAS_WHOOSH:
            self.load_index()

    def _create_bm25_schema(self):
        if not HAS_WHOOSH:
            return None
        analyzer = get_chinese_analyzer()
        return fields.Schema(
            doc_id=fields.ID(stored=True, unique=True),
            content=fields.TEXT(stored=True, analyzer=analyzer),
            title=fields.TEXT(stored=True),
            source=fields.TEXT(stored=True),
            chunk_index=fields.NUMERIC(stored=True)
        )

    def load_index(self) -> None:
        if not HAS_WHOOSH or not os.path.exists(self.bm25_index_dir):
            if HAS_WHOOSH:
                logger.info("No BM25 index found, will create on first add")
            self.bm25_index = None
            self.bm25_searcher = None
            return

        try:
            storage = FileStorage(self.bm25_index_dir)
            self.bm25_index = storage.open_index()
            self.bm25_searcher = self.bm25_index.searcher(weighting=scoring.BM25F())
            logger.info("Loaded BM25 index")
        except Exception as e:
            logger.error(f"Failed to load BM25 index: {e}")
            self.bm25_index = None
            self.bm25_searcher = None

    def add_documents(self, chunks: List[Document], start_id: int = 0) -> None:
        if not HAS_WHOOSH or not chunks:
            return

        try:
            if self.bm25_index is None:
                os.makedirs(self.bm25_index_dir, exist_ok=True)
                storage = FileStorage(self.bm25_index_dir)
                self.bm25_index = storage.create_index(self._create_bm25_schema())
                if self.bm25_searcher:
                    try:
                        self.bm25_searcher.close()
                    except Exception:
                        pass
                self.bm25_searcher = self.bm25_index.searcher(weighting=scoring.BM25F())

            if self.bm25_searcher:
                try:
                    self.bm25_searcher.close()
                except Exception:
                    pass
                self.bm25_searcher = None

            lock_path = os.path.join(self.bm25_index_dir, "bm25_write.lock")
            use_filelock = False
            try:
                from filelock import FileLock
                use_filelock = True
            except Exception:
                FileLock = None

            for attempt in range(3):
                try:
                    if use_filelock:
                        with FileLock(lock_path, timeout=5):
                            with AsyncWriter(self.bm25_index) as writer:
                                for i, chunk in enumerate(chunks):
                                    writer.add_document(
                                        doc_id=f"doc_{start_id + i}",
                                        content=chunk.page_content,
                                        title=chunk.metadata.get("source", ""),
                                        source=chunk.metadata.get("source", ""),
                                        chunk_index=chunk.metadata.get("chunk_index", 0)
                                    )
                    else:
                        with AsyncWriter(self.bm25_index) as writer:
                            for i, chunk in enumerate(chunks):
                                writer.add_document(
                                    doc_id=f"doc_{start_id + i}",
                                    content=chunk.page_content,
                                    title=chunk.metadata.get("source", ""),
                                    source=chunk.metadata.get("source", ""),
                                    chunk_index=chunk.metadata.get("chunk_index", 0)
                                )
                    break
                except Exception as e:
                    logger.warning(f"BM25 add attempt {attempt + 1} failed: {e}")
                    time.sleep(0.3)

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

    def search(self, query: str, documents: List[Document], top_k: int = 50) -> List[Tuple[Document, float]]:
        if not HAS_WHOOSH or not self.bm25_searcher or not self.bm25_index:
            return []

        try:
            parser = qparser.QueryParser("content", self.bm25_index.schema)
            query_obj = parser.parse(query)
            results = self.bm25_searcher.search(query_obj, limit=top_k)

            bm25_results = []
            for hit in results:
                try:
                    doc_id = int(hit["doc_id"].split("_")[1])
                    if doc_id < len(documents):
                        bm25_results.append((documents[doc_id], float(hit.score)))
                except Exception:
                    continue

            return bm25_results
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    def rebuild(self, documents: List[Document]) -> None:
        self.clear()
        if documents and HAS_WHOOSH:
            self.add_documents(documents, start_id=0)

    def clear(self) -> None:
        if self.bm25_searcher:
            try:
                self.bm25_searcher.close()
            except Exception:
                pass
            self.bm25_searcher = None

        if os.path.exists(self.bm25_index_dir):
            try:
                shutil.rmtree(self.bm25_index_dir)
            except Exception as e:
                logger.warning(f"Failed to remove BM25 index dir: {e}")

        self.bm25_index = None
        logger.info("BM25 store cleared")
