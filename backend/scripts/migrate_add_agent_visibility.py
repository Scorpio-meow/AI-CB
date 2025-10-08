"""
數據庫遷移腳本：為 custom_agents 表添加 is_public 和 created_by 欄位

執行此腳本以升級現有數據庫結構：
python scripts/migrate_add_agent_visibility.py
"""

import sys
import os
from pathlib import Path

# 添加後端目錄到 Python 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, inspect
from app.models.database import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """執行數據庫遷移"""
    logger.info(f"連接到數據庫: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        
        # 檢查 custom_agents 表是否存在
        if 'custom_agents' not in inspector.get_table_names():
            logger.error("custom_agents 表不存在！請先運行初始化腳本。")
            return False
        
        # 獲取現有欄位
        existing_columns = [col['name'] for col in inspector.get_columns('custom_agents')]
        logger.info(f"現有欄位: {existing_columns}")
        
        # 添加 is_public 欄位
        if 'is_public' not in existing_columns:
            logger.info("添加 is_public 欄位...")
            try:
                if DATABASE_URL.startswith("sqlite"):
                    # SQLite 語法
                    conn.execute(text(
                        "ALTER TABLE custom_agents ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT 1"
                    ))
                else:
                    # PostgreSQL 語法
                    conn.execute(text(
                        "ALTER TABLE custom_agents ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT TRUE"
                    ))
                conn.commit()
                logger.info("✅ is_public 欄位添加成功")
            except Exception as e:
                logger.error(f"❌ 添加 is_public 欄位失敗: {e}")
                conn.rollback()
                return False
        else:
            logger.info("is_public 欄位已存在，跳過")
        
        # 添加 created_by 欄位
        if 'created_by' not in existing_columns:
            logger.info("添加 created_by 欄位...")
            try:
                if DATABASE_URL.startswith("sqlite"):
                    # SQLite 語法
                    conn.execute(text(
                        "ALTER TABLE custom_agents ADD COLUMN created_by INTEGER"
                    ))
                else:
                    # PostgreSQL 語法
                    conn.execute(text(
                        "ALTER TABLE custom_agents ADD COLUMN created_by INTEGER REFERENCES users(id)"
                    ))
                conn.commit()
                logger.info("✅ created_by 欄位添加成功")
            except Exception as e:
                logger.error(f"❌ 添加 created_by 欄位失敗: {e}")
                conn.rollback()
                return False
        else:
            logger.info("created_by 欄位已存在，跳過")
        
        # 更新現有數據：將所有現有 Agent 設置為公開
        logger.info("更新現有 Agent 為公開狀態...")
        try:
            result = conn.execute(text(
                "UPDATE custom_agents SET is_public = :is_public WHERE is_public IS NULL"
            ), {"is_public": True})
            conn.commit()
            logger.info(f"✅ 更新了 {result.rowcount} 個 Agent 為公開狀態")
        except Exception as e:
            logger.error(f"❌ 更新現有數據失敗: {e}")
            conn.rollback()
            return False
        
        logger.info("🎉 數據庫遷移完成！")
        return True

if __name__ == "__main__":
    try:
        success = migrate_database()
        if success:
            print("\n✅ 遷移成功完成！")
            print("現在可以重新啟動應用程式。")
            sys.exit(0)
        else:
            print("\n❌ 遷移失敗，請檢查日誌。")
            sys.exit(1)
    except Exception as e:
        logger.error(f"遷移過程中發生錯誤: {e}")
        sys.exit(1)
