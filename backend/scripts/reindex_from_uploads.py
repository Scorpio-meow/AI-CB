#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild RAG index from files in data/uploads by extracting text and adding to RAG."""
import os
import sys
from pathlib import Path
import asyncio

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.services.document_processor import DocumentProcessor
from app.rag.contextual_rag import ContextualRAG
from langchain.schema import Document as LangDoc


EXT_TO_MIME = {
    '.txt': 'text/plain',
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}


def infer_mime(path: Path):
    return EXT_TO_MIME.get(path.suffix.lower())


async def main():
    uploads = Path('backend/data/uploads')
    if not uploads.exists() or not uploads.is_dir():
        print('Uploads directory not found:', uploads.resolve())
        return

    rag = ContextualRAG()

    # Clear existing vector store to rebuild from uploads
    print('[1] Clearing existing vector store...')
    rag.clear_vector_store()

    docs = []
    for f in sorted(uploads.iterdir()):
        if not f.is_file():
            continue
        mime = infer_mime(f)
        if not mime:
            print(f'Skipping unsupported extension: {f.name}')
            continue
        try:
            text = DocumentProcessor.extract_text_from_file(str(f), mime)
        except Exception as e:
            print(f'Failed to extract from {f.name}: {e}')
            continue
        if not text or not text.strip():
            print(f'No text extracted from {f.name}, skipping')
            continue

        md = {"source": f.name}
        docs.append(LangDoc(page_content=text, metadata=md))

    if not docs:
        print('No documents to index.')
        return

    print(f'[2] Adding {len(docs)} documents to RAG...')
    added = await rag.add_documents(docs)
    print(f'Added {added} chunks. Vector count now: {rag.index.ntotal}')


if __name__ == '__main__':
    asyncio.run(main())
