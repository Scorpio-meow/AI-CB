#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild RAG index from uploads with FAQ Q/A splitting (one QA per chunk)."""
import os
import sys
import re
import asyncio
import argparse
from pathlib import Path

# Ensure backend imports
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Prefer large chunk size to keep one QA per chunk
os.environ.setdefault("CHUNK_SIZE", "2000")
os.environ.setdefault("CHUNK_OVERLAP", "0")

from app.services.document_processor import DocumentProcessor
from app.rag.contextual_rag import ContextualRAG
from langchain.schema import Document as LangDoc

EXT_TO_MIME = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

QA_PATTERN = re.compile(r"(?:^|\n)\s*[QＱ]\s*[：:]\s*(.*?)\s*[\r\n]+\s*[AＡ]\s*[：:]\s*(.*?)(?=(?:\n\s*[QＱ]\s*[：:]|\Z))",
                        re.DOTALL)

def infer_mime(path: Path):
    return EXT_TO_MIME.get(path.suffix.lower())


def split_faq(text: str):
    """Return list of (question, answer) pairs found in text."""
    pairs = []
    for m in QA_PATTERN.finditer(text):
        q = m.group(1).strip()
        a = m.group(2).strip()
        if q and a:
            pairs.append((q, a))
    return pairs


async def main():
    uploads = Path('backend/data/uploads')
    if not uploads.exists() or not uploads.is_dir():
        print('Uploads directory not found:', uploads.resolve())
        return

    parser = argparse.ArgumentParser(
        description='Reindex uploads into RAG. By default it will add documents incrementally without clearing the existing vector store. Use --rebuild to clear the vector store first.'
    )
    parser.add_argument('--rebuild', action='store_true', help='Clear vector store before adding documents')
    args = parser.parse_args()

    rag = ContextualRAG()

    # Clear existing vector store only when explicitly requested
    if args.rebuild:
        print('[1] Clearing existing vector store...')
        rag.clear_vector_store()
    else:
        print('[1] Skipping clear of vector store (incremental add). Use --rebuild to clear before indexing.')

    docs = []
    total_pairs = 0
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

        pairs = split_faq(text)
        if pairs:
            print(f"Parsed {len(pairs)} QA pairs from {f.name}")
            for i, (q, a) in enumerate(pairs):
                content = f"Q：{q}\nA：{a}"
                md = {
                    "source": f.name,
                    "qa_index": i,
                    "question": q[:2000],
                }
                docs.append(LangDoc(page_content=content, metadata=md))
            total_pairs += len(pairs)
        else:
            # Fallback: add whole document
            md = {"source": f.name}
            docs.append(LangDoc(page_content=text, metadata=md))

    if not docs:
        print('No documents to index.')
        return

    print(f"[2] Adding {len(docs)} documents to RAG... (total QA pairs: {total_pairs})")
    added = await rag.add_documents(docs)
    print(f'Added {added} chunks. Vector count now: {rag.index.ntotal}')


if __name__ == '__main__':
    asyncio.run(main())
