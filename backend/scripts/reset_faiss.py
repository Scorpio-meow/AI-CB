"""
重置 FAISS 和 BM25 索引的腳本
用於修復索引損壞或重建完整的 RAG 索引
"""
import sys
import os
from pathlib import Path

# 添加 backend 目錄到 Python 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.rag_manager import get_rag_instance
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, Document


def reset_indexes():
    """重置所有索引"""
    print("=" * 60)
    print("🔧 開始重置 RAG 索引...")
    print("=" * 60)
    
    # 獲取 RAG 實例
    rag = get_rag_instance()
    
    # 檢查現有索引狀態
    print("\n📊 當前索引狀態:")
    status = rag.get_index_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 獲取資料庫中的文檔
    db: Session = SessionLocal()
    try:
        documents = db.query(Document).all()
        doc_count = len(documents)
        print(f"\n📚 資料庫中共有 {doc_count} 個文檔")
        
        if doc_count == 0:
            print("\n⚠️  警告: 資料庫中沒有文檔,無需重建索引")
            return
        
        # 確認重建
        print("\n⚠️  這將刪除並重建所有索引 (FAISS + BM25)")
        print("   包括:")
        print("   - data/faiss_index.bin")
        print("   - data/documents.pkl")
        print("   - data/bm25_index/")
        
        response = input("\n是否繼續? (y/n): ")
        if response.lower() != 'y':
            print("❌ 操作已取消")
            return
        
        # 執行重建
        print("\n🔨 開始重建索引...")
        print("   這可能需要幾分鐘時間,請耐心等待...")
        
        success = rag.force_reindex()
        
        if success:
            print("\n✅ 索引重建成功!")
            
            # 顯示新的索引狀態
            print("\n📊 新的索引狀態:")
            new_status = rag.get_index_status()
            for key, value in new_status.items():
                print(f"  {key}: {value}")
        else:
            print("\n❌ 索引重建失敗,請檢查日誌")
            
    except Exception as e:
        print(f"\n❌ 發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("🏁 重置流程完成")
    print("=" * 60)


if __name__ == "__main__":
    reset_indexes()
