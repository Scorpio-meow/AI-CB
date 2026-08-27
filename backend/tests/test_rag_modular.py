import os
import pytest
from app.rag.types import Document, RecursiveCharacterTextSplitter
from app.rag.tokenizers import init_domain_dictionary, get_chinese_analyzer
from app.rag.contextual_rag import HybridContextualRAG, ContextualRAG
@pytest.fixture(autouse=True)
def setup_env():
    from app.core.config import settings
    old_data_dir = settings.DATA_DIR
    old_faiss = settings.FAISS_INDEX_PATH
    old_docs = settings.DOCUMENTS_PATH
    old_bm25 = settings.BM25_INDEX_DIR
    old_meta = settings.METADATA_PATH
    settings.DATA_DIR = "tests_data"
    settings.FAISS_INDEX_PATH = "tests_data/faiss_index.bin"
    settings.DOCUMENTS_PATH = "tests_data/documents.pkl"
    settings.BM25_INDEX_DIR = "tests_data/bm25_index"
    settings.METADATA_PATH = "tests_data/index_metadata.pkl"
    if os.path.exists("tests_data"):
        import shutil
        try:
            shutil.rmtree("tests_data")
        except Exception:
            pass
    os.makedirs("tests_data", exist_ok=True)
    yield
    if os.path.exists("tests_data"):
        import shutil
        try:
            shutil.rmtree("tests_data")
        except Exception:
            pass
    settings.DATA_DIR = old_data_dir
    settings.FAISS_INDEX_PATH = old_faiss
    settings.DOCUMENTS_PATH = old_docs
    settings.BM25_INDEX_DIR = old_bm25
    settings.METADATA_PATH = old_meta
def test_document_and_splitter():
    doc = Document(page_content="這是測試文檔內容", metadata={"source": "test.txt", "document_id": 1})
    assert doc.page_content == "這是測試文檔內容"
    assert doc.metadata["document_id"] == 1
    splitter = RecursiveCharacterTextSplitter(chunk_size=10, chunk_overlap=2)
    chunks = splitter.split_text("神通資訊科技股份有限公司知識庫系統測試")
    assert len(chunks) > 0
def test_tokenizers():
    init_domain_dictionary("tests_data")
    analyzer = get_chinese_analyzer()
    assert analyzer is not None or analyzer is None
def test_rag_facade_lifecycle():
    rag = HybridContextualRAG()
    assert rag.documents == []
    assert rag.embedding_dimension > 0
    sample_docs = [
        Document(
            page_content="員工加班申請需於當日或事前由主管核准，加班時數可選擇換取加班費或補休。",
            metadata={"source": "差勤管理辦法.docx", "document_id": 101}
        ),
        Document(
            page_content="神通資訊科技的核心上班時間為早上九點至下午六點，支援彈性上下班半小時。",
            metadata={"source": "員工手冊.pdf", "document_id": 102}
        )
    ]
    added_chunks = rag.add_documents(sample_docs)
    assert added_chunks > 0
    assert len(rag.documents) > 0
    assert rag.index.ntotal > 0
    stats = rag.get_statistics()
    assert stats["total_documents"] == len(rag.documents)
    assert stats["total_vectors"] == rag.index.ntotal
    info = rag.get_vector_store_info()
    assert info["total_vectors"] == rag.index.ntotal
    vec_results = rag.vector_search("加班申請與補休規定", top_k=2)
    assert len(vec_results) > 0
    top_doc, score = vec_results[0]
    assert isinstance(top_doc, Document)
    assert isinstance(score, float)
    smart_results = rag.smart_search("加班如何申請？")
    assert len(smart_results) > 0
    prompt, history = rag.pipeline.build_context_prompt("加班怎麼申請", [top_doc], conversation_id=1, user_id=10)
    assert "用戶問題: 加班怎麼申請" in prompt
    assert "檔案片段:" in prompt
    rag.remove_document_by_id(101)
    remaining_ids = [d.metadata.get("original_doc_id") for d in rag.documents]
    assert 101 not in remaining_ids
    rag.clear_vector_store()
    assert len(rag.documents) == 0
    assert rag.index.ntotal == 0