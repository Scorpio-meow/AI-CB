#!/usr/bin/env python3
import asyncio
from app.models.database import Base, engine

# Import all models to register them with Base.metadata
from app.models import User, Conversation, Message, Document, DocumentChunk

async def main():
    print("Available tables in metadata:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(main())
