"""
資料分區功能數據庫遷移腳本
執行此腳本將現有數據庫升級以支援資料分區功能

使用方式：
    python backend/scripts/migrate_add_partitions.py
"""
import sys
import os
from pathlib import Path

# 添加父目錄到 Python 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.models.database import Base, DATABASE_URL
from app.models import Partition, User, Document, DocumentChunk, user_partition_association
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_table_exists(inspector, table_name):
    """檢查表是否存在"""
    return table_name in inspector.get_table_names()


def check_column_exists(inspector, table_name, column_name):
    """檢查列是否存在"""
    if not check_table_exists(inspector, table_name):
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_database():
    """執行資料庫遷移"""
    logger.info("開始資料分區功能遷移...")
    logger.info(f"數據庫 URL: {DATABASE_URL}")
    
    # 創建引擎和會話
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. 創建 partitions 表
        if not check_table_exists(inspector, 'partitions'):
            logger.info("創建 partitions 表...")
            Partition.__table__.create(engine)
            logger.info("✓ partitions 表創建成功")
        else:
            logger.info("partitions 表已存在，跳過創建")
        
        # 2. 創建 user_partition_association 關聯表
        if not check_table_exists(inspector, 'user_partition_association'):
            logger.info("創建 user_partition_association 關聯表...")
            user_partition_association.create(engine)
            logger.info("✓ user_partition_association 表創建成功")
        else:
            logger.info("user_partition_association 表已存在，跳過創建")
        
        # 3. 為 users 表添加 current_partition_id 欄位
        if not check_column_exists(inspector, 'users', 'current_partition_id'):
            logger.info("為 users 表添加 current_partition_id 欄位...")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN current_partition_id INTEGER"))
                conn.commit()
            logger.info("✓ current_partition_id 欄位添加成功")
        else:
            logger.info("users.current_partition_id 欄位已存在，跳過添加")
        
        # 4. 為 documents 表添加 partition_id 欄位
        if not check_column_exists(inspector, 'documents', 'partition_id'):
            logger.info("為 documents 表添加 partition_id 欄位...")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE documents ADD COLUMN partition_id INTEGER"))
                conn.commit()
            logger.info("✓ partition_id 欄位添加成功")
        else:
            logger.info("documents.partition_id 欄位已存在，跳過添加")
        
        # 5. 為 document_chunks 表添加 partition_id 欄位
        if not check_column_exists(inspector, 'document_chunks', 'partition_id'):
            logger.info("為 document_chunks 表添加 partition_id 欄位...")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE document_chunks ADD COLUMN partition_id INTEGER"))
                conn.commit()
            logger.info("✓ partition_id 欄位添加成功")
        else:
            logger.info("document_chunks.partition_id 欄位已存在，跳過添加")
        
        # 6. 創建預設分區
        default_partition = session.query(Partition).filter(Partition.is_default == True).first()
        
        if not default_partition:
            logger.info("創建預設分區...")
            
            # 獲取管理員用戶（如果存在）
            admin_user = session.query(User).filter(User.is_admin == True).first()
            admin_id = admin_user.id if admin_user else 1
            
            default_partition = Partition(
                name="預設分區",
                description="系統預設知識庫分區",
                is_default=True,
                is_active=True,
                created_by=admin_id,
                document_count=0,
                chunk_count=0
            )
            session.add(default_partition)
            session.commit()
            session.refresh(default_partition)
            logger.info(f"✓ 預設分區創建成功 (ID: {default_partition.id})")
        else:
            logger.info(f"預設分區已存在 (ID: {default_partition.id})")
        
        # 7. 將所有現有文檔關聯到預設分區
        with engine.connect() as conn:
            # 更新沒有 partition_id 的文檔
            result = conn.execute(text(
                f"UPDATE documents SET partition_id = {default_partition.id} WHERE partition_id IS NULL"
            ))
            updated_docs = result.rowcount
            
            # 更新沒有 partition_id 的文檔分塊
            result = conn.execute(text(
                f"UPDATE document_chunks SET partition_id = {default_partition.id} WHERE partition_id IS NULL"
            ))
            updated_chunks = result.rowcount
            
            conn.commit()
            
            logger.info(f"✓ 已將 {updated_docs} 個文檔關聯到預設分區")
            logger.info(f"✓ 已將 {updated_chunks} 個文檔分塊關聯到預設分區")
        
        # 8. 更新預設分區的統計資訊
        doc_count = session.query(Document).filter(Document.partition_id == default_partition.id).count()
        chunk_count = session.query(DocumentChunk).filter(DocumentChunk.partition_id == default_partition.id).count()
        
        default_partition.document_count = doc_count
        default_partition.chunk_count = chunk_count
        session.commit()
        
        logger.info(f"✓ 預設分區統計更新：{doc_count} 個文檔, {chunk_count} 個分塊")
        
        # 9. 將所有用戶添加到預設分區
        all_users = session.query(User).all()
        for user in all_users:
            # 檢查是否已經在預設分區中
            existing = session.execute(
                text("SELECT * FROM user_partition_association WHERE user_id = :uid AND partition_id = :pid"),
                {"uid": user.id, "pid": default_partition.id}
            ).fetchone()
            
            if not existing:
                session.execute(
                    text("INSERT INTO user_partition_association (user_id, partition_id) VALUES (:uid, :pid)"),
                    {"uid": user.id, "pid": default_partition.id}
                )
                logger.info(f"  - 用戶 {user.username} 已添加到預設分區")
            
            # 設置當前分區（如果尚未設置）
            if user.current_partition_id is None:
                user.current_partition_id = default_partition.id
        
        session.commit()
        logger.info(f"✓ 所有用戶已添加到預設分區")
        
        # 10. 創建索引以提升查詢性能
        logger.info("創建索引以提升查詢性能...")
        with engine.connect() as conn:
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_partition_id ON documents(partition_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_document_chunks_partition_id ON document_chunks(partition_id)"))
                conn.commit()
                logger.info("✓ 索引創建成功")
            except Exception as e:
                logger.warning(f"索引創建警告: {e}")
        
        logger.info("\n" + "="*60)
        logger.info("✓ 資料分區功能遷移完成！")
        logger.info("="*60)
        logger.info(f"預設分區 ID: {default_partition.id}")
        logger.info(f"文檔總數: {doc_count}")
        logger.info(f"分塊總數: {chunk_count}")
        logger.info(f"用戶總數: {len(all_users)}")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"遷移過程中發生錯誤: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    try:
        migrate_database()
        print("\n✓ 遷移成功完成！")
        print("您現在可以使用資料分區功能了。")
        print("\n下一步：")
        print("1. 重啟後端服務")
        print("2. 訪問 /api/partitions 查看分區管理 API")
        print("3. 使用管理員帳號創建新的分區")
    except Exception as e:
        print(f"\n✗ 遷移失敗: {e}")
        sys.exit(1)
