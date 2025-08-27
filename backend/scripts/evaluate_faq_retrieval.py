#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evaluate retrieval quality for all FAQ Q/A pairs.
For each QA (metadata contains 'question'), query with the question text and
measure whether the exact QA chunk is retrieved in top-k.
"""
import os
import sys
from collections import Counter

# Ensure backend import
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.rag.contextual_rag import HybridContextualRAG


def main():
    rag = HybridContextualRAG()
    qa_docs = [(i, d) for i, d in enumerate(rag.documents) if d.metadata.get('question')]
    if not qa_docs:
        print('No QA documents found in vector store. Make sure to run reindex_faq_split.py first.')
        return

    total = len(qa_docs)
    k_values = [1, 3, 5]
    hits = {k: 0 for k in k_values}
    mrr_sum = 0.0
    failures = []
    strategy_counter = Counter()

    for idx, (doc_idx, doc) in enumerate(qa_docs, start=1):
        q = doc.metadata['question']
        results = rag.smart_search(q)
        strategy = getattr(rag, '_last_retrieval_strategy', 'unknown')
        strategy_counter[strategy] += 1

        # find rank of the exact doc object
        rank = None
        for i, (cand_doc, _score) in enumerate(results):
            if cand_doc is doc:
                rank = i + 1
                break

        if rank is None:
            failures.append({
                'question': q,
                'source': doc.metadata.get('source', '未知'),
                'top3': [
                    {
                        'source': d.metadata.get('source', '未知'),
                        'preview': d.page_content[:80].replace('\n', ' ')
                    }
                    for d, _ in results[:3]
                ]
            })
        else:
            for k in k_values:
                if rank <= k:
                    hits[k] += 1
            mrr_sum += 1.0 / rank

        if idx % 20 == 0 or idx == total:
            print(f"Progress: {idx}/{total}")

    # summary
    print("\n=== Retrieval Summary ===")
    print(f"QA count: {total}")
    for k in k_values:
        rate = hits[k] / total if total else 0.0
        print(f"Hit@{k}: {hits[k]} ({rate:.1%})")
    mrr = mrr_sum / total if total else 0.0
    print(f"MRR: {mrr:.4f}")
    print(f"Strategies used: {dict(strategy_counter)}")

    if failures:
        print("\nSample failures (up to 10):")
        for item in failures[:10]:
            print("- Q:", item['question'])
            print("  source:", item['source'])
            for j, t in enumerate(item['top3'], start=1):
                print(f"  top{j} -> src={t['source']} preview={t['preview']}")


if __name__ == '__main__':
    main()
