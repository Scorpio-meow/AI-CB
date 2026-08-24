from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np
from .retrievers.hybrid import HybridRetriever


class RAGEvaluator:
    def __init__(self, retriever: HybridRetriever):
        self.retriever = retriever

    def evaluate_retrieval(
        self,
        test_queries: List[str],
        gold_doc_ids: List[List[int]],
        k_values: List[int] = [1, 3, 5, 10]
    ) -> Dict[str, Any]:
        if len(test_queries) != len(gold_doc_ids):
            raise ValueError("Number of queries must match number of gold standard lists")

        results: Dict[str, List[float]] = {f"recall@{k}": [] for k in k_values}
        results.update({f"precision@{k}": [] for k in k_values})
        results["mrr"] = []

        for query, gold_ids in zip(test_queries, gold_doc_ids):
            doc_score_pairs = self.retriever.hybrid_search(query, alpha=self.retriever.hybrid_alpha)
            doc_score_pairs = self.retriever.rerank_with_cross_encoder(query, doc_score_pairs)
            retrieved_doc_ids = [
                doc.metadata.get("document_id", doc.metadata.get("original_doc_id", -1))
                for doc, _ in doc_score_pairs
            ]

            for k in k_values:
                top_k_retrieved = retrieved_doc_ids[:k]
                relevant_retrieved = len(set(top_k_retrieved) & set(gold_ids))
                recall = relevant_retrieved / len(gold_ids) if gold_ids else 0
                results[f"recall@{k}"].append(recall)

                precision = relevant_retrieved / k if k > 0 else 0
                results[f"precision@{k}"].append(precision)

            mrr = 0
            for i, doc_id in enumerate(retrieved_doc_ids):
                if doc_id in gold_ids:
                    mrr = 1 / (i + 1)
                    break
            results["mrr"].append(mrr)

        avg_results: Dict[str, Any] = {}
        for metric, values in results.items():
            avg_results[f"avg_{metric}"] = float(sum(values) / len(values)) if values else 0.0
            avg_results[f"{metric}_std"] = float(np.std(values)) if values else 0.0

        avg_results["num_queries"] = len(test_queries)
        avg_results["evaluation_timestamp"] = datetime.now().isoformat()
        return avg_results

    def auto_tune_alpha(
        self,
        test_queries: List[str],
        gold_doc_ids: List[List[int]],
        alphas: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        if alphas is None:
            alphas = [round(x, 2) for x in np.linspace(0.3, 0.9, 13)]

        best: Dict[str, Any] = {"alpha": None, "avg_mrr": -1.0, "metrics": None}
        for a in alphas:
            self.retriever.hybrid_alpha = a
            metrics = self.evaluate_retrieval(test_queries, gold_doc_ids)
            if metrics.get("avg_mrr", 0) > best["avg_mrr"]:
                best = {"alpha": a, "avg_mrr": metrics.get("avg_mrr", 0), "metrics": metrics}

        return best
