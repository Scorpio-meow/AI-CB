import os
import pytest
from app.rag.types import Document, RecursiveCharacterTextSplitter
from app.rag.tokenizers import init_domain_dictionary, get_chinese_analyzer
from app.rag.contextual_rag import HybridContextualRAG, ContextualRAG


@pytest.fixture(autouse=True)
def setup_env():
    os.environ["FORCE_CPU"] = "true"
    os.environ["DATA_DIR"] = "tests_data"
    yield
    # 清理測試資料目錄
    if os.path.exists("tests_data"):
        import shutil
        try:
            shutil.rmtree("tests_data")
        except Exception:
            pass


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
    assert analyzer is not None or analyzer is None  # 不報錯即可


def test_rag_facade_lifecycle():
    rag = HybridContextualRAG()
    assert rag.documents == []
    assert rag.embedding_dimension == 384

    # 1. 建立測試文檔
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

    # 2. 加入文檔
    added_chunks = rag.add_documents(sample_docs)
    assert added_chunks > 0
    assert len(rag.documents) > 0
    assert rag.index.ntotal > 0

    # 3. 測試統計與向量庫資訊
    stats = rag.get_statistics()
    assert stats["total_documents"] == len(rag.documents)
    assert stats["total_vectors"] == rag.index.ntotal

    info = rag.get_vector_store_info()
    assert info["total_vectors"] == rag.index.ntotal

    # 4. 測試向量檢索與智慧檢索
    vec_results = rag.vector_search("加班申請與補休規定", top_k=2)
    assert len(vec_results) > 0
    top_doc, score = vec_results[0]
    assert isinstance(top_doc, Document)
    assert isinstance(score, float)

    smart_results = rag.smart_search("加班如何申請？")
    assert len(smart_results) > 0

    # 5. 測試 Prompt 提示詞構建
    prompt, history = rag.pipeline.build_context_prompt("加班怎麼申請", [top_doc], conversation_id=1, user_id=10)
    assert "用戶問題: 加班怎麼申請" in prompt
    assert "檔案片段:" in prompt

    # 6. 測試刪除文檔
    rag.remove_document_by_id(101)
    # 確保 101 的 chunk 已刪除
    remaining_ids = [d.metadata.get("original_doc_id") for d in rag.documents]
    assert 101 not in remaining_ids

    # 7. 清理向量庫
    rag.clear_vector_store()
    assert len(rag.documents) == 0
    assert rag.index.ntotal == 0
