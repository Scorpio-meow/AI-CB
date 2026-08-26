from typing import List, Tuple, Dict, Any, Optional
import os
import pickle
import logging
from datetime import datetime
import numpy as np
import faiss
from ..types import Document

logger = logging.getLogger(__name__)

SentenceTransformer = None


class VectorStoreManager:
    def __init__(
        self,
        data_dir: str = "data",
        faiss_index_path: Optional[str] = None,
        documents_path: Optional[str] = None,
        metadata_path: Optional[str] = None,
        embedding_model: Optional[str] = None,
        force_cpu: bool = False,
        use_fp16: bool = False,
        use_faiss_gpu: bool = False,
        faiss_gpu_device: int = 0,
        batch_size: Optional[int] = None,
        similarity_threshold: float = 0.25,
        top_k: int = 50,
    ):
        self.data_dir = data_dir
        self.faiss_index_path = faiss_index_path or os.path.join(self.data_dir, "faiss_index.bin")
        self.documents_path = documents_path or os.path.join(self.data_dir, "documents.pkl")
        self.metadata_path = metadata_path or os.path.join(self.data_dir, "index_metadata.pkl")
        os.makedirs(self.data_dir, exist_ok=True)

        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.documents: List[Document] = []

        import torch
        from app.core.config import settings

        if force_cpu or not torch.cuda.is_available():
            self.device = "cpu"
            try:
                # 針對 Intel i7-1360P (12 核 16 線程) 配置最佳 PyTorch 執行緒數
                cpu_threads = min(16, os.cpu_count() or 8)
                torch.set_num_threads(cpu_threads)
                torch.set_num_interop_threads(min(4, os.cpu_count() or 4))
                logger.info(f"Intel Core i7-1360P CPU 多執行緒加速啟用: PyTorch 執行緒數 = {cpu_threads}")
            except Exception as e:
                logger.debug(f"設定 PyTorch 執行緒失敗: {e}")
            self.batch_size = batch_size or settings.CPU_BATCH_SIZE or 128
        else:
            self.device = "cuda"
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
            logger.info(f"GPU加速已啟用: {gpu_name} ({gpu_mem}GB 顯存)")
            self.batch_size = batch_size or settings.GPU_BATCH_SIZE or 128

        model_name = embedding_model or os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
        fallback_model = "paraphrase-multilingual-MiniLM-L12-v2"
        self.local_embeddings = self._load_embedding_model(model_name, fallback_model)
        if self.local_embeddings is None:
            raise RuntimeError("No embedding model available. Please check EMBEDDING_MODEL environment variable or install sentence-transformers.")

        self.use_fp16 = use_fp16
        if self.use_fp16 and self.device == "cuda":
            try:
                self.local_embeddings = self.local_embeddings.half()
                logger.info("嵌入模型已量化為 FP16 (顯存減少 50%)")
            except Exception as e:
                logger.warning(f"FP16 量化失敗，使用 FP32: {e}")
                self.use_fp16 = False

        if hasattr(self.local_embeddings, "get_embedding_dimension"):
            self.embedding_dimension = self.local_embeddings.get_embedding_dimension()
        elif hasattr(self.local_embeddings, "get_sentence_embedding_dimension"):
            self.embedding_dimension = self.local_embeddings.get_sentence_embedding_dimension()
        else:
            self.embedding_dimension = 384
        logger.info(f"嵌入模型已載入至 {self.device.upper()}: {model_name} (維度: {self.embedding_dimension}, 精度: {'FP16' if self.use_fp16 else 'FP32'})")

        self.use_faiss_gpu = use_faiss_gpu
        self.faiss_gpu_device = faiss_gpu_device
        self.gpu_resources = None
        if self.use_faiss_gpu and hasattr(faiss, "StandardGpuResources"):
            try:
                self.gpu_resources = faiss.StandardGpuResources()
                gpu_temp_memory = int(os.getenv("FAISS_GPU_TEMP_MEMORY", str(2 * 1024 * 1024 * 1024)))
                self.gpu_resources.setTempMemory(gpu_temp_memory)
                logger.info(f"FAISS-GPU 資源已初始化 (設備 {self.faiss_gpu_device}, 臨時記憶體: {gpu_temp_memory / 1024**3:.1f}GB)")
            except Exception as e:
                logger.warning(f"FAISS-GPU 初始化失敗，回退到 CPU: {e}")
                self.use_faiss_gpu = False
                self.gpu_resources = None
        elif self.use_faiss_gpu:
            logger.warning("FAISS-GPU 已啟用但庫不支援 GPU，請安裝 faiss-gpu。回退到 CPU 模式。")
            self.use_faiss_gpu = False

        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        self.load_indices()

    def _load_embedding_model(self, model_name: str, fallback_model: str):
        global SentenceTransformer
        try:
            if SentenceTransformer is None:
                from sentence_transformers import SentenceTransformer as _ST
                SentenceTransformer = _ST
            return SentenceTransformer(model_name, device=self.device)
        except Exception as e:
            logger.warning(f"Failed to load SentenceTransformer ({model_name}): {e}")
            if model_name != fallback_model:
                logger.info(f"嘗試載入備用模型: {fallback_model}")
                try:
                    return SentenceTransformer(fallback_model, device=self.device)
                except Exception as e2:
                    logger.error(f"Fallback model also failed: {e2}")
                    return None
            return None

    def load_indices(self) -> None:
        try:
            index_mismatch = False
            if os.path.exists(self.faiss_index_path) and os.path.exists(self.documents_path):
                cpu_index = faiss.read_index(self.faiss_index_path)
                try:
                    index_dim = getattr(cpu_index, "d", None)
                except Exception:
                    index_dim = None

                if index_dim is not None and index_dim != self.embedding_dimension:
                    index_mismatch = True
                    logger.warning(
                        f"Loaded FAISS index dimension ({index_dim}) does not match current embedding dimension ({self.embedding_dimension})."
                        " Initializing empty index to avoid add() assertion failure."
                    )
                    cpu_index = faiss.IndexFlatIP(self.embedding_dimension)
                    try:
                        if os.path.exists(self.faiss_index_path):
                            os.replace(self.faiss_index_path, self.faiss_index_path + ".mismatch.bak")
                        if os.path.exists(self.documents_path):
                            os.replace(self.documents_path, self.documents_path + ".mismatch.bak")
                        logger.info("Backed up mismatched FAISS index and documents.pkl as *.mismatch.bak")
                    except Exception as e:
                        logger.warning(f"Failed to back up mismatched indices: {e}")

                if self.use_faiss_gpu and self.gpu_resources:
                    try:
                        self.index = faiss.index_cpu_to_gpu(
                            self.gpu_resources,
                            self.faiss_gpu_device,
                            cpu_index
                        )
                        logger.info(f"FAISS 索引已轉換至 GPU (設備 {self.faiss_gpu_device})")
                    except Exception as e:
                        logger.warning(f"FAISS 索引 GPU 轉換失敗，使用 CPU: {e}")
                        self.index = cpu_index
                        self.use_faiss_gpu = False
                else:
                    self.index = cpu_index

                if index_mismatch:
                    self.documents = []
                else:
                    try:
                        with open(self.documents_path, "rb") as f:
                            self.documents = pickle.load(f)
                    except Exception as e:
                        logger.warning(f"Failed to load documents pickle: {e}. Clearing documents.")
                        self.documents = []

                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Error loading FAISS indices: {e}")
            self.clear()

    def save_indices(self) -> None:
        try:
            if self.use_faiss_gpu and self.gpu_resources:
                try:
                    cpu_index = faiss.index_gpu_to_cpu(self.index)
                    faiss.write_index(cpu_index, self.faiss_index_path)
                    logger.info("FAISS-GPU 索引已轉回 CPU 並儲存")
                except Exception as e:
                    logger.warning(f"GPU 索引轉換失敗，嘗試直接儲存: {e}")
                    faiss.write_index(self.index, self.faiss_index_path)
            else:
                faiss.write_index(self.index, self.faiss_index_path)

            with open(self.documents_path, "wb") as f:
                pickle.dump(self.documents, f)

            from ..tokenizers import HAS_JIEBA
            metadata = {
                "last_reindex": datetime.now(),
                "total_documents": len(self.documents),
                "total_vectors": self.index.ntotal,
                "tokenizer": "jieba" if HAS_JIEBA else "standard",
                "faiss_gpu_enabled": self.use_faiss_gpu
            }
            with open(self.metadata_path, "wb") as f:
                pickle.dump(metadata, f)

            logger.info(f"Saved FAISS indices with {self.index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Error saving FAISS indices: {e}")

    def add_documents(self, chunks: List[Document]) -> int:
        if not chunks:
            return 0
        total_chunks = len(chunks)
        chunk_texts = [chunk.page_content for chunk in chunks]
        logger.info(f"正在對 {total_chunks} 個文本塊計算向量嵌入 (Batch Size: {self.batch_size}, Device: {self.device})...")
        
        # 若文字塊數量龐大，分批編碼並輸出進度百分比
        if total_chunks > 500:
            step = max(500, self.batch_size * 4)
            all_embeddings = []
            for start_idx in range(0, total_chunks, step):
                end_idx = min(start_idx + step, total_chunks)
                sub_texts = chunk_texts[start_idx:end_idx]
                sub_emb = self.local_embeddings.encode(
                    sub_texts,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    device=self.device
                )
                all_embeddings.append(sub_emb)
                pct = int((end_idx / total_chunks) * 100)
                logger.info(f"向量編碼進度: {pct}% ({end_idx}/{total_chunks} 塊)")
            import numpy as np
            embeddings = np.vstack(all_embeddings).astype("float32")
        else:
            embeddings = self.local_embeddings.encode(
                chunk_texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                device=self.device
            )
            embeddings = embeddings.astype("float32")

        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        self.documents.extend(chunks)
        self.save_indices()
        logger.info(f"成功將 {total_chunks} 個文本塊寫入 FAISS 向量庫 (現有總向量數: {self.index.ntotal})")
        return total_chunks

    def search(self, query: str, top_k: Optional[int] = None, apply_threshold: bool = True) -> List[Tuple[Document, float]]:
        if self.index.ntotal == 0:
            return []

        limit = top_k or self.top_k
        query_embedding = self.local_embeddings.encode(
            [query],
            batch_size=1,
            convert_to_numpy=True,
            device=self.device
        )
        query_embedding = query_embedding.astype("float32")
        faiss.normalize_L2(query_embedding)

        similarities, indices = self.index.search(query_embedding, min(limit, self.index.ntotal))

        results = []
        for similarity, idx in zip(similarities[0], indices[0]):
            if (not apply_threshold or similarity > self.similarity_threshold) and idx < len(self.documents):
                results.append((self.documents[idx], float(similarity)))

        return results

    def remove_document_by_id(self, document_id: int) -> int:
        docs_to_remove = []
        for i, doc in enumerate(self.documents):
            if doc.metadata.get("document_id") == document_id or doc.metadata.get("original_doc_id") == document_id:
                docs_to_remove.append(i)

        if not docs_to_remove:
            return 0

        for i in sorted(docs_to_remove, reverse=True):
            del self.documents[i]

        if not self.documents:
            self.clear()
        else:
            all_texts = [doc.page_content for doc in self.documents]
            embeddings = self.local_embeddings.encode(
                all_texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                device=self.device
            )
            embeddings = embeddings.astype("float32")
            faiss.normalize_L2(embeddings)
            self.index = faiss.IndexFlatIP(self.embedding_dimension)
            self.index.add(embeddings)
            self.save_indices()

        logger.info(f"Removed {len(docs_to_remove)} chunks for document_id {document_id}")
        return len(docs_to_remove)

    def clear(self) -> None:
        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        self.documents = []
        for path in [self.faiss_index_path, self.documents_path, self.metadata_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        logger.info("Vector store cleared completely")
