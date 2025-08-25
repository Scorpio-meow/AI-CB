from __future__ import annotations

from typing import Iterable, List
from pathlib import Path
import os
import json
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from fastembed import TextEmbedding

from .config import EMBEDDING_MODEL, EMBEDDING_CACHE_DIR


class EmbeddingService:
    """Embedding service with FastEmbed first, ONNX fallback for E5 models.

    Default model id via env EMBEDDING_MODEL (e.g., "intfloat/e5-base-v2").
    If FastEmbed doesn't support it, we load ONNX from cache_dir/<model_name>/onnx.
    """

    def __init__(self, model_id: str | None = None):
        self._mode = "fastembed"
        self._onnx = None  # type: ignore

        # Resolve model id or local path
        raw_model_id = model_id or EMBEDDING_MODEL
        try:
            mp = Path(raw_model_id)
            if mp.exists():
                model_name = mp.resolve().as_posix()
            else:
                model_name = raw_model_id
        except Exception:
            model_name = raw_model_id

        try:
            cache_dir = Path(EMBEDDING_CACHE_DIR).resolve()
        except Exception:
            cache_dir = Path(EMBEDDING_CACHE_DIR)

        # Try FastEmbed first
        try:
            self.model_id = model_name
            self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir.as_posix())
            self._mode = "fastembed"
            return
        except ValueError:
            # Not supported by FastEmbed -> fall back to ONNX loader
            pass

        # ONNX fallback: expect local layout: <cache_dir>/<short_name>/onnx/{model.onnx, tokenizer.json, config.json}
        short = Path(model_name).name if "/" in model_name or "\\" in model_name else model_name
        local_root = None
        # If model_name is a local path with onnx folder
        p = Path(model_name)
        if p.exists():
            local_root = p
        else:
            candidate = cache_dir / short
            if candidate.exists():
                local_root = candidate

        if local_root is None:
            raise ValueError(
                f"Model '{model_name}' not supported by FastEmbed and local files not found under cache_dir '{cache_dir}'."
            )

        onnx_dir = local_root / "onnx"
        model_path = onnx_dir / "model.onnx"
        tok_path = onnx_dir / "tokenizer.json"
        cfg_path = onnx_dir / "config.json"
        if not (model_path.exists() and tok_path.exists() and cfg_path.exists()):
            raise ValueError(f"ONNX assets missing under {onnx_dir} (need model.onnx, tokenizer.json, config.json)")

        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        max_len = int(cfg.get("max_position_embeddings", 512))
        pad_id = int(cfg.get("pad_token_id", 0))

        tokenizer = Tokenizer.from_file(tok_path.as_posix())
        # Enable truncation/padding (fixed length for batching simplicity)
        tokenizer.enable_truncation(max_length=max_len)
        tokenizer.enable_padding(length=max_len, pad_id=pad_id, pad_token="[PAD]")

        # Prepare ONNX session
        sess = ort.InferenceSession(model_path.as_posix(), providers=["CPUExecutionProvider"])  # CPU by default
        input_names = [i.name for i in sess.get_inputs()]
        output_names = [o.name for o in sess.get_outputs()]
        if not output_names:
            raise ValueError("ONNX model has no outputs")
        out_name = output_names[0]

        class _ONNXWrapper:
            def __init__(self, session, tokenizer, input_names, out_name):
                self.session = session
                self.tokenizer = tokenizer
                self.input_names = input_names
                self.out_name = out_name

            def embed(self, texts: Iterable[str]):
                encs = self.tokenizer.encode_batch(list(texts))
                ids = np.array([e.ids for e in encs], dtype=np.int64)
                attn = np.array([e.attention_mask for e in encs], dtype=np.int64)
                feeds = {"input_ids": ids, "attention_mask": attn}
                if "token_type_ids" in self.input_names:
                    feeds["token_type_ids"] = np.zeros_like(ids, dtype=np.int64)
                outputs = self.session.run([self.out_name], feeds)[0]  # [B, L, H] or [B, H]
                if outputs.ndim == 3:
                    # mean pooling with attention mask
                    mask = attn.astype(np.float32)
                    mask = np.expand_dims(mask, axis=-1)  # [B, L, 1]
                    summed = (outputs * mask).sum(axis=1)
                    counts = np.clip(mask.sum(axis=1), 1e-6, None)
                    embs = summed / counts
                else:
                    embs = outputs.astype(np.float32)
                return [v.astype(np.float32) for v in embs]

        self._onnx = _ONNXWrapper(sess, tokenizer, input_names, out_name)
        self._mode = "onnx"
        self.model_id = model_name

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        if self._mode == "fastembed":
            return [vec.tolist() if hasattr(vec, "tolist") else list(vec) for vec in self._model.embed(texts)]
        # ONNX path
        vecs = self._onnx.embed(texts)  # type: ignore
        return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vecs]

    def embed_query(self, query: str) -> List[float]:
        return self.embed([f"query: {query}"])[0]

    def embed_passages(self, passages: Iterable[str]) -> List[List[float]]:
        prefixed = [f"passage: {p}" for p in passages]
        return self.embed(prefixed)
