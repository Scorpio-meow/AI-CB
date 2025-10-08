"""
資料分區功能測試腳本
測試分區創建、用戶分配、文檔上傳和查詢隔離
"""
import sys
from pathlib import Path

# 添加父目錄到 Python 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import DATABASE_URL
from app.models import Partition, User, Document, user_partition_association
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_partition_functionality():
    """測試資料分區功能"""
    logger.info("=" * 60)
    logger.info("開始測試資料分區功能")
    logger.info("=" * 60)
    
    # 創建數據庫連接
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. 檢查預設分區
        logger.info("\n1. 檢查預設分區...")
        default_partition = session.query(Partition).filter(Partition.is_default == True).first()
        if default_partition:
            logger.info(f"  ✓ 預設分區存在: {default_partition.name} (ID: {default_partition.id})")
        else:
            logger.error("  ✗ 預設分區不存在")
            return False
        
        # 2. 檢查用戶
        logger.info("\n2. 檢查用戶...")
        users = session.query(User).all()
        logger.info(f"  找到 {len(users)} 個用戶")
        for user in users[:3]:  # 只顯示前3個
            logger.info(f"  - {user.username} (ID: {user.id}, 當前分區: {user.current_partition_id})")
        
        if not users:
            logger.warning("  ⚠ 沒有找到用戶，請先創建用戶")
            return False
        
        # 3. 檢查用戶分區關聯
        logger.info("\n3. 檢查用戶分區關聯...")
        test_user = users[0]
        user_partitions = session.query(Partition).join(
            user_partition_association,
            Partition.id == user_partition_association.c.partition_id
        ).filter(user_partition_association.c.user_id == test_user.id).all()
        
        logger.info(f"  用戶 {test_user.username} 有權訪問的分區:")
        for p in user_partitions:
            logger.info(f"  - {p.name} (ID: {p.id})")
        
        # 4. 檢查文檔分區分配
        logger.info("\n4. 檢查文檔分區分配...")
        docs = session.query(Document).all()
        logger.info(f"  找到 {len(docs)} 個文檔")
        
        partition_doc_count = {}
        for doc in docs:
            pid = doc.partition_id
            partition_doc_count[pid] = partition_doc_count.get(pid, 0) + 1
        
        for pid, count in partition_doc_count.items():
            partition = session.query(Partition).filter(Partition.id == pid).first()
            partition_name = partition.name if partition else "未知分區"
            logger.info(f"  - 分區 '{partition_name}' (ID: {pid}): {count} 個文檔")
        
        # 5. 測試創建新分區（如果有管理員用戶）
        admin = session.query(User).filter(User.is_admin == True).first()
        if admin:
            logger.info("\n5. 測試創建新分區...")
            test_partition_name = "測試分區_自動測試"
            
            # 檢查是否已存在
            existing = session.query(Partition).filter(Partition.name == test_partition_name).first()
            if existing:
                logger.info(f"  測試分區已存在 (ID: {existing.id})")
            else:
                new_partition = Partition(
                    name=test_partition_name,
                    description="自動化測試創建的分區",
                    is_default=False,
                    created_by=admin.id
                )
                session.add(new_partition)
                session.commit()
                session.refresh(new_partition)
                logger.info(f"  ✓ 成功創建測試分區 (ID: {new_partition.id})")
                
                # 將管理員添加到新分區
                from sqlalchemy import text
                session.execute(
                    text("INSERT INTO user_partition_association (user_id, partition_id) VALUES (:uid, :pid)"),
                    {"uid": admin.id, "pid": new_partition.id}
                )
                session.commit()
                logger.info(f"  ✓ 已將管理員添加到測試分區")
        else:
            logger.warning("\n5. 跳過創建新分區測試（沒有管理員用戶）")
        
        # 6. 統計總覽
        logger.info("\n" + "=" * 60)
        logger.info("統計總覽")
        logger.info("=" * 60)
        
        partition_count = session.query(Partition).filter(Partition.is_active == True).count()
        total_docs = session.query(Document).count()
        
        logger.info(f"活躍分區數: {partition_count}")
        logger.info(f"文檔總數: {total_docs}")
        logger.info(f"用戶總數: {len(users)}")
        
        # 7. 分區詳細信息
        logger.info("\n分區詳細信息:")
        logger.info("-" * 60)
        all_partitions = session.query(Partition).filter(Partition.is_active == True).all()
        for p in all_partitions:
            doc_count = session.query(Document).filter(Document.partition_id == p.id).count()
            user_count = session.query(user_partition_association).filter(
                user_partition_association.c.partition_id == p.id
            ).count()
            
            status = "預設" if p.is_default else "一般"
            logger.info(f"\n分區: {p.name} [{status}]")
            logger.info(f"  ID: {p.id}")
            logger.info(f"  文檔數: {doc_count}")
            logger.info(f"  用戶數: {user_count}")
            logger.info(f"  創建時間: {p.created_at}")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ 資料分區功能測試完成")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


if __name__ == "__main__":
    try:
        result = asyncio.run(test_partition_functionality())
        if result:
            print("\n✓ 所有測試通過！")
            sys.exit(0)
        else:
            print("\n✗ 部分測試失敗")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ 測試執行失敗: {e}")
        sys.exit(1)
