#!/usr/bin/env python3
"""
RAG性能測試和評估腳本

使用方法：
python scripts/test_rag_improvements.py --mode benchmark
python scripts/test_rag_improvements.py --mode compare
python scripts/test_rag_improvements.py --mode evaluate
"""

import asyncio
import sys
import os
import time
import json
import argparse
from typing import List, Dict, Any
import logging

# Add backend root to sys.path (to import app.*)
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

try:
    from app.rag.contextual_rag import HybridContextualRAG
except ModuleNotFoundError:
    PROJECT_ROOT = os.path.dirname(BACKEND_ROOT)
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from backend.app.rag.contextual_rag import HybridContextualRAG
from langchain.schema import Document

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RAGEvaluator:
    def __init__(self):
        self.rag = HybridContextualRAG()
        
        # 測試查詢集（你可以根據實際文檔調整）
        self.test_queries = [
            "什麼是人工智能？",
            "如何實現機器學習？", 
            "深度學習的基本原理",
            "神經網絡如何工作？",
            "自然語言處理的應用",
            "計算機視覺技術",
            "數據科學方法論",
            "Python程式設計基礎",
            "軟體開發流程",
            "資料庫設計原則"
        ]
        
        # 對應的相關文檔ID（需要根據你的實際數據調整）
        self.gold_standards = [
            [1, 2],      # AI相關文檔
            [1, 3],      # ML相關文檔  
            [2, 3],      # 深度學習文檔
            [2, 4],      # 神經網絡文檔
            [5, 6],      # NLP文檔
            [7, 8],      # CV文檔
            [9, 10],     # 數據科學文檔
            [11, 12],    # Python文檔
            [13, 14],    # 軟體開發文檔
            [15, 16]     # 資料庫文檔
        ]
    
    async def benchmark_search_methods(self):
        """對比不同搜尋方法的性能"""
        logger.info("開始搜尋方法基準測試...")
        
        methods = [
            ("Vector Search", lambda q: self.rag.vector_search(q, 5)),
            ("BM25 Search", lambda q: self.rag.bm25_search(q, 5)),
            ("Hybrid Search", lambda q: self.rag.hybrid_search(q, alpha=0.7)),
            ("Smart Search", lambda q: self.rag.smart_search(q))
        ]
        
        results = {}
        
        for method_name, method_func in methods:
            logger.info(f"測試 {method_name}...")
            times = []
            result_counts = []
            
            for query in self.test_queries:
                start_time = time.time()
                try:
                    search_results = method_func(query)
                    elapsed = time.time() - start_time
                    times.append(elapsed)
                    result_counts.append(len(search_results))
                except Exception as e:
                    logger.error(f"{method_name} 失敗於查詢 '{query}': {e}")
                    times.append(float('inf'))
                    result_counts.append(0)
            
            avg_time = sum(t for t in times if t != float('inf')) / len([t for t in times if t != float('inf')])
            avg_results = sum(result_counts) / len(result_counts)
            
            results[method_name] = {
                "avg_time_ms": avg_time * 1000,
                "avg_results": avg_results,
                "success_rate": len([t for t in times if t != float('inf')]) / len(times)
            }
        
        return results
    
    async def compare_configurations(self):
        """比較不同配置的效果"""
        logger.info("開始配置比較測試...")
        
        configs = [
            {"alpha": 0.5, "similarity_threshold": 0.2, "name": "平衡配置"},
            {"alpha": 0.7, "similarity_threshold": 0.25, "name": "語義偏向"},
            {"alpha": 0.3, "similarity_threshold": 0.3, "name": "關鍵詞偏向"},
            {"alpha": 0.8, "similarity_threshold": 0.15, "name": "高召回配置"}
        ]
        
        results = {}
        original_threshold = self.rag.similarity_threshold
        
        for config in configs:
            logger.info(f"測試配置: {config['name']}")
            
            # 設置配置
            self.rag.similarity_threshold = config["similarity_threshold"]
            
            times = []
            result_counts = []
            
            for query in self.test_queries:
                start_time = time.time()
                search_results = self.rag.hybrid_search(query, alpha=config["alpha"])
                elapsed = time.time() - start_time
                
                times.append(elapsed)
                result_counts.append(len(search_results))
            
            results[config["name"]] = {
                "avg_time_ms": sum(times) / len(times) * 1000,
                "avg_results": sum(result_counts) / len(result_counts),
                "config": config
            }
        
        # 恢復原始設置
        self.rag.similarity_threshold = original_threshold
        
        return results
    
    async def evaluate_retrieval_quality(self):
        """評估檢索質量"""
        logger.info("開始檢索質量評估...")
        
        if len(self.test_queries) != len(self.gold_standards):
            logger.warning("測試查詢數量與金標準不匹配，使用前幾個查詢")
            min_len = min(len(self.test_queries), len(self.gold_standards))
            queries = self.test_queries[:min_len]
            gold_ids = self.gold_standards[:min_len]
        else:
            queries = self.test_queries
            gold_ids = self.gold_standards
        
        try:
            results = self.rag.evaluate_retrieval(queries, gold_ids)
            return results
        except Exception as e:
            logger.error(f"評估失敗: {e}")
            return {"error": str(e)}
    
    async def test_reranker_impact(self):
        """測試reranker的影響"""
        logger.info("測試Cross-Encoder Reranker的影響...")
        
        results = {"with_reranker": [], "without_reranker": []}
        original_reranker = self.rag.has_reranker
        
        for use_reranker in [True, False]:
            self.rag.has_reranker = use_reranker and self.rag.cross_encoder is not None
            key = "with_reranker" if use_reranker else "without_reranker"
            
            for query in self.test_queries[:5]:  # 測試前5個查詢
                start_time = time.time()
                docs = self.rag.smart_search(query)
                elapsed = time.time() - start_time
                
                # smart_search returns list of (doc, score)
                top = docs[:3]
                results[key].append({
                    "query": query,
                    "time_ms": elapsed * 1000,
                    "num_results": len(docs),
                    "top_sources": [doc.metadata.get('source', 'unknown') for doc, _ in top]
                })
        
        # 恢復原始設置
        self.rag.has_reranker = original_reranker
        
        return results
    
    def generate_test_documents(self, num_docs: int = 20):
        """生成測試文檔（如果沒有真實文檔）"""
        logger.info(f"生成 {num_docs} 個測試文檔...")
        
        test_docs = [
            Document(
                page_content=f"""
                人工智能（AI）是計算機科學的一個分支，致力於創造能夠執行通常需要人類智能的任務的機器。
                AI包括機器學習、深度學習、自然語言處理等多個子領域。
                機器學習是AI的核心技術之一，通過訓練算法來識別數據中的模式。
                深度學習使用神經網絡來處理複雜的數據結構。
                文檔編號：{i}，主題：人工智能基礎
                """,
                metadata={"source": f"AI_doc_{i}.txt", "document_id": i, "topic": "AI"}
            )
            for i in range(1, num_docs + 1)
        ]
        
        return test_docs
    
    async def run_full_evaluation(self):
        """運行完整評估"""
        logger.info("=== RAG系統性能評估開始 ===")
        
        # 檢查是否有文檔
        if self.rag.index.ntotal == 0:
            logger.info("沒有文檔，生成測試文檔...")
            test_docs = self.generate_test_documents()
            await self.rag.add_documents(test_docs)
        
        results = {}
        
        # 1. 基準測試
        try:
            results["benchmark"] = await self.benchmark_search_methods()
        except Exception as e:
            results["benchmark"] = {"error": str(e)}
        
        # 2. 配置比較
        try:
            results["configuration_comparison"] = await self.compare_configurations()
        except Exception as e:
            results["configuration_comparison"] = {"error": str(e)}
        
        # 3. 檢索質量評估
        try:
            results["retrieval_quality"] = await self.evaluate_retrieval_quality()
        except Exception as e:
            results["retrieval_quality"] = {"error": str(e)}
        
        # 4. Reranker影響
        try:
            results["reranker_impact"] = await self.test_reranker_impact()
        except Exception as e:
            results["reranker_impact"] = {"error": str(e)}
        
        # 5. 系統統計
        results["system_stats"] = self.rag.get_statistics()
        results["vector_store_info"] = self.rag.get_vector_store_info()
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """格式化輸出結果"""
        print("\n" + "="*60)
        print("RAG系統性能評估報告")
        print("="*60)
        
        # 基準測試結果
        if "benchmark" in results and "error" not in results["benchmark"]:
            print("\n📊 搜尋方法基準測試:")
            for method, stats in results["benchmark"].items():
                print(f"  {method:15} | 平均時間: {stats['avg_time_ms']:.2f}ms | 平均結果數: {stats['avg_results']:.1f} | 成功率: {stats['success_rate']:.1%}")
        
        # 配置比較
        if "configuration_comparison" in results and "error" not in results["configuration_comparison"]:
            print("\n⚙️  配置比較測試:")
            for config_name, stats in results["configuration_comparison"].items():
                print(f"  {config_name:12} | 平均時間: {stats['avg_time_ms']:.2f}ms | 平均結果數: {stats['avg_results']:.1f}")
        
        # 檢索質量
        if "retrieval_quality" in results and "error" not in results["retrieval_quality"]:
            print("\n🎯 檢索質量評估:")
            quality = results["retrieval_quality"]
            for metric, value in quality.items():
                if metric.startswith("avg_"):
                    print(f"  {metric:20} | {value:.3f}")
        
        # Reranker影響
        if "reranker_impact" in results and "error" not in results["reranker_impact"]:
            print("\n🔄 Reranker影響測試:")
            impact = results["reranker_impact"]
            if "with_reranker" in impact:
                avg_time_with = sum(r["time_ms"] for r in impact["with_reranker"]) / len(impact["with_reranker"])
                avg_time_without = sum(r["time_ms"] for r in impact["without_reranker"]) / len(impact["without_reranker"])
                print(f"  有Reranker平均時間:    {avg_time_with:.2f}ms")
                print(f"  無Reranker平均時間:    {avg_time_without:.2f}ms")
                print(f"  時間差異:             {avg_time_with - avg_time_without:+.2f}ms")
        
        # 系統統計
        if "system_stats" in results:
            print("\n📈 系統統計:")
            stats = results["system_stats"]
            print(f"  總文檔數:             {stats.get('total_documents', 0)}")
            print(f"  總向量數:             {stats.get('total_vectors', 0)}")
            print(f"  BM25狀態:             {stats.get('bm25_status', 'Unknown')}")
            print(f"  Reranker狀態:         {stats.get('reranker_status', 'Unknown')}")
        
        print("\n" + "="*60)

async def main():
    parser = argparse.ArgumentParser(description="RAG性能測試工具")
    parser.add_argument("--mode", choices=["benchmark", "compare", "evaluate", "full"], 
                       default="full", help="測試模式")
    parser.add_argument("--output", help="保存結果到JSON文件")
    parser.add_argument("--add-test-docs", action="store_true", help="添加測試文檔")
    
    args = parser.parse_args()
    
    evaluator = RAGEvaluator()
    
    # 添加測試文檔
    if args.add_test_docs:
        test_docs = evaluator.generate_test_documents(20)
        await evaluator.rag.add_documents(test_docs)
        logger.info("已添加測試文檔")
    
    # 運行測試
    if args.mode == "benchmark":
        results = await evaluator.benchmark_search_methods()
    elif args.mode == "compare":
        results = await evaluator.compare_configurations()
    elif args.mode == "evaluate":
        results = await evaluator.evaluate_retrieval_quality()
    else:  # full
        results = await evaluator.run_full_evaluation()
    
    # 輸出結果
    evaluator.print_results({"benchmark" if args.mode == "benchmark" else args.mode: results} if args.mode != "full" else results)
    
    # 保存結果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"結果已保存到 {args.output}")

if __name__ == "__main__":
    asyncio.run(main())
