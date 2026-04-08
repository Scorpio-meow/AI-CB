#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from app.models.database import Base, engine

# Import all models to register them with Base.metadata
from app.models import User, Conversation, Message, Document, DocumentChunk
from app.models.custom_agent import CustomAgent


def ensure_schema_compatibility():
    """補齊既有資料庫的相容欄位與索引（可重複執行）。"""
    with engine.begin() as conn:
        # 舊版 SQLite 可能有 messages.model_name 欄位，PostgreSQL 需補齊以便遷移舊資料
        conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS model_name VARCHAR"))

        # 常用查詢索引（若已存在則略過）
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations (user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages (conversation_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_uploaded_by ON documents (uploaded_by)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id ON document_chunks (document_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_custom_agents_created_by ON custom_agents (created_by)"))

async def main():
    print("Available tables in metadata:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    print("Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(main())
