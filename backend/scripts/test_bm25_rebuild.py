import os
import sys
from datetime import datetime

# Ensure backend root on path
CURR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.rag.contextual_rag import HybridContextualRAG

if __name__ == "__main__":
    rag = HybridContextualRAG()
    print("Before:", rag.get_vector_store_info())
    ok = rag.force_reindex()
    print("force_reindex returned:", ok)
    print("After:", rag.get_vector_store_info())
    print("Done at:", datetime.now().isoformat())
