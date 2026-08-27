from typing import List, Tuple, Dict, Any, Optional
import os
import re
import logging
import numpy as np
from ..types import Document
from ..indices.vector_store import VectorStoreManager
from ..indices.bm25_store import BM25StoreManager

logger = logging.getLogger(__name__)

CrossEncoder = None


class HybridRetriever:
    def __init__(
        self,
        vector_store: VectorStoreManager,
        bm25_store: BM25StoreManager,
        reranker_model: Optional[str] = None,
        hybrid_alpha: float = 0.7,
        rerank_top_k: int = 80,
        final_k: int = 10,
        rerank_weight: float = 0.8,
        final_threshold: float = 0.1,
        normalization: str = "max",
        use_fp16: bool = False,
    ):
        self.vector_store = vector_store
        self.bm25_store = bm25_store
        self.hybrid_alpha = hybrid_alpha
        self.rerank_top_k = rerank_top_k
        self.final_k = final_k
        self.rerank_weight = rerank_weight
        self.final_threshold = final_threshold
        self.normalization = normalization.lower()
        self.last_retrieval_strategy = "unknown"

        global CrossEncoder
        from app.core.config import settings
        model_name = reranker_model or settings.RERANKER_MODEL
        self.has_reranker = False
        self.cross_encoder = None
        try:
            if CrossEncoder is None:
                from sentence_transformers import CrossEncoder as _CE
                CrossEncoder = _CE
            self.cross_encoder = CrossEncoder(model_name, device=self.vector_store.device)

            if use_fp16 and self.vector_store.device == "cuda":
                try:
                    self.cross_encoder.model = self.cross_encoder.model.half()
                    logger.info("Cross-Encoder 已量化為 FP16")
                except Exception as e:
                    logger.warning(f"Cross-Encoder FP16 量化失敗: {e}")

            self.has_reranker = True
            logger.info(f"Cross-Encoder 已載入至 {self.vector_store.device.upper()}: {model_name} (精度: {'FP16' if use_fp16 else 'FP32'})")
        except Exception as e:
            logger.warning(f"Failed to load cross-encoder {model_name}: {e}")
            self.cross_encoder = None
            self.has_reranker = False

    def normalize_scores(self, scores: List[float], method: Optional[str] = None) -> List[float]:
        if not scores:
            return []
        m = (method or self.normalization).lower()
        if m == "softmax":
            a = np.array(scores, dtype=np.float32)
            a = a - np.max(a)
            exp = np.exp(a)
            denom = np.sum(exp)
            if denom <= 0:
                return [0.0 for _ in scores]
            return (exp / denom).tolist()

        max_v = max(scores)
        return [(s / max_v) if max_v > 0 else 0.0 for s in scores]

    def hybrid_search(self, query: str, alpha: Optional[float] = None) -> List[Tuple[Document, float]]:
        alpha_val = self.hybrid_alpha if alpha is None else alpha
        vector_results = self.vector_store.search(query, self.rerank_top_k, apply_threshold=False)
        bm25_results = self.bm25_store.search(query, self.vector_store.documents, self.rerank_top_k)

        doc_scores: Dict[int, Dict[str, Any]] = {}
        if vector_results:
            vec_scores = [score for _, score in vector_results]
            vec_norms = self.normalize_scores(vec_scores, method=self.normalization)
            for (doc, _), norm in zip(vector_results, vec_norms):
                did = id(doc)
                doc_scores[did] = {"doc": doc, "vector_score": float(norm), "bm25_score": 0.0}

        if bm25_results:
            bm_scores = [score for _, score in bm25_results]
            bm_norms = self.normalize_scores(bm_scores, method=self.normalization)
            for (doc, _), norm in zip(bm25_results, bm_norms):
                did = id(doc)
                if did in doc_scores:
                    doc_scores[did]["bm25_score"] = float(norm)
                else:
                    doc_scores[did] = {"doc": doc, "vector_score": 0.0, "bm25_score": float(norm)}

        combined: List[Tuple[Document, float]] = []
        for rec in doc_scores.values():
            score = alpha_val * rec["vector_score"] + (1 - alpha_val) * rec["bm25_score"]
            if score > 0:
                combined.append((rec["doc"], score))

        combined.sort(key=lambda x: x[1], reverse=True)
        return combined[: self.rerank_top_k]

    def rerank_with_cross_encoder(self, query: str, doc_score_pairs: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        if not self.has_reranker or not doc_score_pairs:
            return doc_score_pairs

        try:
            pairs = [(query, d.page_content) for d, _ in doc_score_pairs]
            cross_scores = self.cross_encoder.predict(pairs)
            orig_scores = [s for _, s in doc_score_pairs]


            cs_arr = np.array(cross_scores, dtype=float)
            cs_norm = 1.0 / (1.0 + np.exp(-np.clip(cs_arr, -20.0, 20.0)))

            def _normalize_orig(arr):
                arr = np.array(arr, dtype=float)
                mn, mx = float(np.min(arr)), float(np.max(arr))
                if mx - mn <= 1e-8:
                    return [max(0.5, float(x)) for x in arr]
                return [float((x - mn) / (mx - mn)) for x in arr]

            os_norm = _normalize_orig(orig_scores)
            w = min(max(self.rerank_weight, 0.0), 1.0)
            combined = [
                (doc, float(w * cs + (1 - w) * os))
                for (doc, _), cs, os in zip(doc_score_pairs, cs_norm, os_norm)
            ]
            combined = [x for x in combined if x[1] >= self.final_threshold]
            combined.sort(key=lambda x: x[1], reverse=True)
            return combined[: self.final_k]
        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}")
            doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
            return doc_score_pairs[: self.final_k]

    def smart_search(self, query: str) -> List[Tuple[Document, float]]:
        has_quotes = '"' in query
        has_chinese = bool(re.search(r"[\u4e00-\u9fff]", query))
        has_exact_terms = bool(has_quotes or re.search(r"\b(exactly|precisely|具體|確切)\b", query, re.I))
        faq_keywords = r"(填寫說明|申請|到期|調班|補登|證明|薪資條|特休|補休|育嬰留停|產檢|免刷卡|時刻維護|集體異動|輪班|排班)"
        is_short = len(re.sub(r"\s+", "", query)) <= 25
        contains_faq_kw = bool(re.search(faq_keywords, query))


        url_match = re.search(r'https?://[^\s"\'<>]+', query)
        id_match = re.search(r'/post/([A-Za-z0-9_-]+)', query)
        user_match = re.search(r'@[A-Za-z0-9_.-]+', query)


        target_dates = []
        for m in re.finditer(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', query):
            y, mth, d = m.group(1), int(m.group(2)), int(m.group(3))
            target_dates.extend([f"{y}-{mth:02d}-{d:02d}", f"{y}年{mth}月{d}日", f"{y}年{mth:02d}月{d:02d}日"])
        for m in re.finditer(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日', query):
            y, mth, d = m.group(1), int(m.group(2)), int(m.group(3))
            target_dates.extend([f"{y}-{mth:02d}-{d:02d}", f"{y}年{mth}月{d}日", f"{y}年{mth:02d}月{d:02d}日"])
        target_dates = list(set(target_dates))

        target_url = url_match.group(0).rstrip('/>"\'') if url_match else None
        target_id = id_match.group(1) if id_match else None
        target_user = user_match.group(0) if user_match else None

        exact_candidates: List[Tuple[Document, float]] = []
        if target_url or target_id or target_user or target_dates:
            seen_ids = set()
            for doc in self.vector_store.documents:
                c = doc.page_content
                c_lower = c.lower()
                did = id(doc)
                if did in seen_ids:
                    continue
                if target_url and target_url.lower() in c_lower:
                    exact_candidates.append((doc, 1.0))
                    seen_ids.add(did)
                elif target_id and target_id in c:
                    exact_candidates.append((doc, 0.98))
                    seen_ids.add(did)
                elif target_dates and any(td in c for td in target_dates):
                    exact_candidates.append((doc, 0.98))
                    seen_ids.add(did)
                elif target_user and target_user.lower() in c_lower:
                    exact_candidates.append((doc, 0.90))
                    seen_ids.add(did)

        strategy = ""
        if has_exact_terms and not has_chinese:
            results = self.bm25_store.search(query, self.vector_store.documents, self.rerank_top_k)
            strategy = "bm25"
            logger.info(f"Retrieval strategy=BM25 query='{query}' candidates={len(results)}")
        elif has_chinese and (is_short or contains_faq_kw):
            results = self.hybrid_search(query, alpha=self.hybrid_alpha)
            strategy = "hybrid"
            logger.info(f"Retrieval strategy=HYBRID(FAQ-like) query='{query}' candidates={len(results)}")
        elif has_chinese and not has_exact_terms:
            results = self.vector_store.search(query, self.rerank_top_k, apply_threshold=False)
            strategy = "vector"
            logger.info(f"Retrieval strategy=VECTOR query='{query}' candidates={len(results)}")
        else:
            results = self.hybrid_search(query, alpha=self.hybrid_alpha)
            strategy = "hybrid"
            logger.info(f"Retrieval strategy=HYBRID(alpha={self.hybrid_alpha}) query='{query}' candidates={len(results)}")


        if exact_candidates:
            combined_candidates = []
            seen_cand_ids = set()
            for doc, score in exact_candidates:
                combined_candidates.append((doc, score))
                seen_cand_ids.add(id(doc))
            for doc, score in results:
                if id(doc) not in seen_cand_ids:
                    combined_candidates.append((doc, score))
                    seen_cand_ids.add(id(doc))
            results = combined_candidates

        if results:
            results = self.rerank_with_cross_encoder(query, results)


            if exact_candidates:
                top_hits = [c[0] for c in exact_candidates if c[1] >= 0.95]
                top_hit_ids = {id(d) for d in top_hits}
                exact_ranked = [r for r in results if id(r[0]) in top_hit_ids]
                other_ranked = [r for r in results if id(r[0]) not in top_hit_ids]
                results = exact_ranked + other_ranked

        self.last_retrieval_strategy = strategy or "unknown"
        return results if results else []
