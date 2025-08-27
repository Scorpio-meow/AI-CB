import sys
import traceback
import pprint
print('Python executable:', sys.executable)
print('sys.path:')
pp = pprint.PrettyPrinter(indent=2)
pp.pprint(sys.path)

try:
    from app.rag.contextual_rag import HybridContextualRAG
    print('Imported HybridContextualRAG OK')
    rag = HybridContextualRAG()
    print('RAG init OK')
except Exception:
    print('Full traceback:')
    traceback.print_exc()
