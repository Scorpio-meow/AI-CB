
import sys
import os
import shutil
from pathlib import Path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
def reset_indexes():
    print("=" * 60)
    print("🔧 開始重置 RAG 索引...")
    print("=" * 60)
    
    data_dir = backend_dir / "data"
    
    index_files = [
        data_dir / "faiss_index.bin",
        data_dir / "documents.pkl",
    ]
    bm25_dir = data_dir / "bm25_index"
    
    print("\n⚠️  這將刪除以下索引檔案:")
    for f in index_files:
        status = "存在" if f.exists() else "不存在"
        print(f"   - {f.name}: {status}")
    print(f"   - bm25_index/: {'存在' if bm25_dir.exists() else '不存在'}")
    
    response = input("\n是否繼續? (y/n): ")
    if response.lower() != 'y':
        print("❌ 操作已取消")
        return
    
    print("\n🗑️  刪除索引檔案...")
    for f in index_files:
        if f.exists():
            f.unlink()
            print(f"   ✓ 已刪除 {f.name}")
    
    if bm25_dir.exists():
        shutil.rmtree(bm25_dir)
        print("   ✓ 已刪除 bm25_index/")
    
    print("\n🔄 重新初始化 RAG 系統...")
    try:
        from app.core.rag_manager import get_rag_system
        rag = get_rag_system()
        
        print("\n📊 新的索引狀態:")
        if hasattr(rag, 'get_index_status'):
            status = rag.get_index_status()
            for key, value in status.items():
                print(f"  {key}: {value}")
        else:
            print(f"  嵌入維度: {rag.embedding_dimension}")
            print(f"  索引中的向量數: {rag.index.ntotal if hasattr(rag, 'index') else 0}")
            print(f"  文檔數: {len(rag.documents) if hasattr(rag, 'documents') else 0}")
        
        print("\n✅ 索引重置成功!")
        print("   下次上傳文檔時將自動建立新索引")
        
    except Exception as e:
        print(f"\n⚠️  RAG 初始化警告 (索引已清空，重啟服務後將重建): {e}")
    
    print("\n" + "=" * 60)
    print("🏁 重置流程完成")
    print("=" * 60)
if __name__ == "__main__":
    reset_indexes()
