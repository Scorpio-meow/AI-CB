#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from app.models.database import Base, engine
from app.models import User, Conversation, Message, Document


def ensure_schema_compatibility():
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS document_chunks"))
        conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS model_name VARCHAR"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations (user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages (conversation_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_uploaded_by ON documents (uploaded_by)"))


async def main():
    print("Available tables in metadata:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")
    
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    print("Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(main())
