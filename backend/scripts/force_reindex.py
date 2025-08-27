#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Force rebuild of FAISS and BM25 indices from persisted documents."""
import os
import sys

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

try:
    from app.rag.contextual_rag import ContextualRAG
except ModuleNotFoundError:
    PROJECT_ROOT = os.path.dirname(BACKEND_ROOT)
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from backend.app.rag.contextual_rag import ContextualRAG


def main():
    rag = ContextualRAG()
    print("[Before] Vector store info:")
    print(rag.get_vector_store_info())

    ok = rag.force_reindex()
    print(f"\nReindex triggered: {ok}")

    print("\n[After] Vector store info:")
    print(rag.get_vector_store_info())


if __name__ == "__main__":
    main()
