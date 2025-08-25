from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from .config import RAG_STORE_DIR


@dataclass
class DocChunk:
    id: str
    text: str
    metadata: dict


class SimpleVectorStore:
    """A tiny, file-based vector store with cosine similarity.

    Persists two files under RAG_STORE_DIR:
    - vectors.npy (shape: [N, D])
    - meta.json (list of {id, text, metadata})
    """

    def __init__(self, root: str | None = None):
        self.root = os.path.abspath(root or RAG_STORE_DIR)
        os.makedirs(self.root, exist_ok=True)
        self.vec_path = os.path.join(self.root, "vectors.npy")
        self.meta_path = os.path.join(self.root, "meta.json")
        self._vectors: np.ndarray | None = None
        self._metas: List[DocChunk] = []
        self._load()

    def _load(self):
        if os.path.exists(self.vec_path):
            self._vectors = np.load(self.vec_path)
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._metas = [DocChunk(**m) for m in raw]

    def _save(self):
        if self._vectors is not None:
            np.save(self.vec_path, self._vectors)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump([m.__dict__ for m in self._metas], f, ensure_ascii=False, indent=2)

    @staticmethod
    def _cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        # a: [N, D], b: [D]
        an = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-10)
        bn = b / (np.linalg.norm(b) + 1e-10)
        return an @ bn

    def add(self, vectors: List[List[float]], metas: List[DocChunk]):
        v = np.array(vectors, dtype=np.float32)
        if self._vectors is None:
            self._vectors = v
        else:
            self._vectors = np.concatenate([self._vectors, v], axis=0)
        self._metas.extend(metas)
        self._save()

    def topk(self, query_vec: List[float], k: int = 5) -> List[Tuple[DocChunk, float]]:
        if self._vectors is None or len(self._metas) == 0:
            return []
        q = np.array(query_vec, dtype=np.float32)
        sims = self._cosine_sim(self._vectors, q)
        idx = np.argsort(-sims)[:k]
        return [(self._metas[i], float(sims[i])) for i in idx]
