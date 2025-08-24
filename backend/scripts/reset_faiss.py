#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reset FAISS vector store by calling ContextualRAG.clear_vector_store()
"""
from app.rag.contextual_rag import ContextualRAG

def main():
    rag = ContextualRAG()
    print('Vector store info before reset:')
    print(rag.get_vector_store_info())

    rag.clear_vector_store()

    print('\nVector store info after reset:')
    print(rag.get_vector_store_info())

if __name__ == '__main__':
    main()
