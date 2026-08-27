import os
import sys
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
from app.models.database import SessionLocal
from app.models import Document as DBDocument
from app.services.document_processor import DocumentProcessor
from app.core.rag_manager import get_rag_system
from app.api.documents import process_document_for_rag
import asyncio
async def reprocess_all():
    db = SessionLocal()
    rag_system = get_rag_system()
    
    print("=== 開始重新處理現有文件庫 ===")
    docs = db.query(DBDocument).all()
    if not docs:
        print("資料庫中無任何文件記錄。")
        db.close()
        return
    print("清空現有 RAG 向量與 BM25 索引...")
    from app.core.config import settings
    rag_system.clear_vector_store()
    upload_dir = settings.UPLOAD_DIR
    total_chunks = 0
    for doc in docs:
        file_path = os.path.join(upload_dir, doc.filename)
        print(f"\n--- 處理文檔: {doc.filename} (ID: {doc.id}) ---")
        
        content = doc.content
        if os.path.exists(file_path):
            try:
                print(f"正在從實體檔案重新提取文字 (含 OCR)...")
                fresh_content = DocumentProcessor.extract_text_from_file(file_path, doc.file_type or "text/plain")
                if fresh_content and fresh_content.strip():
                    content = fresh_content.strip()
                    doc.content = content
            except Exception as e:
                print(f"提取失敗，使用現有內容: {e}")
        
        summary = await DocumentProcessor.generate_document_summary_async(doc.filename, content, doc.file_type or "text/plain")
        doc.description = summary
        db.add(doc)
        db.commit()
        print(f"新 AI 大綱摘要: {summary}")
        print(f"提取字數: {len(content)} 字元")
        base_metadata = {
            "source": doc.filename,
            "document_id": doc.id,
            "uploaded_by": doc.uploaded_by,
            "content_type": doc.file_type,
            "original_filename": doc.filename
        }
        langchain_docs, qa_count = process_document_for_rag(content, base_metadata, rag_system)
        chunks_added = rag_system.add_documents(langchain_docs)
        total_chunks += (chunks_added or 0)
        print(f"已建立向量分塊: {chunks_added} 塊")
    db.close()
    print(f"\n=== 重建完成！共處理 {len(docs)} 份文檔，建立 {total_chunks} 個向量塊 ===")
if __name__ == "__main__":
    asyncio.run(reprocess_all())