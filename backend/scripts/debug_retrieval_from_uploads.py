import sys
import os

# Ensure backend package is importable when running script from repository root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.rag.contextual_rag import HybridContextualRAG


def run_tests():
    rag = HybridContextualRAG()
    print("Vector store info:")
    print(rag.get_vector_store_info())
    queries = [
        "申請或取消免刷卡申請單填寫說明",
        "人事調閱申請單填寫說明",
        "集體異動清冊填寫說明",
        "時刻維護申請表填寫說明",
        "調班申請(調整例假日/休息日/工作日)填寫說明",
    ]

    for q in queries:
        print("\n---\nQuery:", q)
        results = rag.smart_search(q)
        if not results:
            print("No results returned")
            continue
        for i, (doc, score) in enumerate(results[:5]):
            src = doc.metadata.get('source', 'unknown')
            chunk_idx = doc.metadata.get('chunk_index', -1)
            doc_id = doc.metadata.get('document_id', doc.metadata.get('original_doc_id', 'n/a'))
            snippet = doc.page_content[:300].replace('\n', ' ')
            print(f"{i+1}. score={score:.4f} source={src} chunk={chunk_idx} doc_id={doc_id}")
            print("   ", snippet)

if __name__ == '__main__':
    run_tests()
