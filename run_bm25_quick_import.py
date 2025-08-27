import sys, traceback, os
sys.path.insert(0, r'C:\Users\MITAC\Documents\AI-CB')
try:
    from backend.app.rag.contextual_rag import HybridContextualRAG
    print('Imported via backend.app.rag')
    rag = HybridContextualRAG()
    print('RAG initialized')
    print('bm25_index:', type(rag.bm25_index))
    print('bm25_searcher:', type(rag.bm25_searcher))
    print('bm25_index_dir exists:', os.path.exists(rag.bm25_index_dir))
    print('bm25_index_dir listing:', os.listdir(rag.bm25_index_dir) if os.path.exists(rag.bm25_index_dir) else None)
except Exception:
    traceback.print_exc()
