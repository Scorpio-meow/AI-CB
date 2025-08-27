import logging
import os
import traceback
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
	from app.rag.contextual_rag import HybridContextualRAG

	print('Initializing RAG...')
	rag = HybridContextualRAG()
	print('RAG initialized')
	print('bm25_index:', type(rag.bm25_index))
	print('bm25_searcher:', type(rag.bm25_searcher))
	print('bm25_index_dir exists:', os.path.exists(rag.bm25_index_dir))
	print('bm25_index_dir listing:', os.listdir(rag.bm25_index_dir) if os.path.exists(rag.bm25_index_dir) else None)
except Exception as e:
	print('Exception during test:')
	traceback.print_exc()
