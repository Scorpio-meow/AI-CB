import sys, os, pickle, traceback
sys.path.insert(0, r'C:\Users\MITAC\Documents\AI-CB')
from backend.app.rag.contextual_rag import HybridContextualRAG

print('Working dir:', os.getcwd())
print('Data dir listing:', os.listdir(os.path.join(os.getcwd(), '..', 'data')) if os.path.exists(os.path.join(os.getcwd(), '..', 'data')) else None)

# documents.pkl
docs_path = os.path.join(os.getcwd(), '..', 'data', 'documents.pkl')
if os.path.exists(docs_path):
    try:
        with open(docs_path, 'rb') as f:
            docs = pickle.load(f)
        print('documents.pkl loaded, num chunks =', len(docs))
        if len(docs) > 0:
            print('sample metadata[0]:', docs[0].metadata)
    except Exception:
        print('Failed to load documents.pkl:')
        traceback.print_exc()
else:
    print('documents.pkl not found')

# BM25 index dir
bm25_dir = os.path.join(os.getcwd(), '..', 'data', 'bm25_index')
print('bm25_index_dir exists:', os.path.exists(bm25_dir))
if os.path.exists(bm25_dir):
    print('bm25_index contents:', os.listdir(bm25_dir))

# Instantiate RAG and run a BM25 search
try:
    rag = HybridContextualRAG()
    print('RAG loaded. bm25_index:', type(rag.bm25_index), 'bm25_searcher:', type(rag.bm25_searcher))
    sample_query = '測試'
    results = rag.bm25_search(sample_query, top_k=5)
    print(f'BM25 search for "{sample_query}" returned {len(results)} results')
    for doc, score in results:
        print(' -', doc.metadata.get('source', 'unknown'), 'score=', score, 'snippet=', doc.page_content[:60])
except Exception:
    print('Failed to init RAG or search:')
    traceback.print_exc()
