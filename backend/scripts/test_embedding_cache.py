#!/usr/bin/env python3
"""
Embedding Cache 性能測試腳本

測試新的 embedding cache 和批次處理系統的性能改進。
"""

import asyncio
import sys
import os
import time
import shutil
import tempfile
from typing import List, Dict, Any
import logging
import numpy as np

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.contextual_rag import HybridContextualRAG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmbeddingCacheTestSuite:
    def __init__(self):
        self.test_texts = [
            "人工智能是計算機科學的一個分支，它致力於創建能夠執行通常需要人類智能的任務的系統。",
            "機器學習是人工智能的一個子集，它使用統計技術讓計算機能夠從數據中'學習'而無需明確編程。",
            "深度學習是機器學習的一個分支，它基於人工神經網絡，特別是深度神經網絡。",
            "自然語言處理（NLP）是人工智能的一個分支，專注於計算機與人類語言之間的交互。",
            "計算機視覺是人工智能的一個領域，致力於讓計算機能夠理解和解釋視覺信息。",
            "大數據分析是從大量數據中提取有價值信息和洞察的過程。",
            "雲計算是通過互聯網提供計算服務，包括服務器、存儲、數據庫、網絡、軟件等。",
            "區塊鏈是一種分布式賬本技術，能夠維護一個持續增長的記錄列表。",
            "物聯網（IoT）是指將日常物品連接到互聯網，讓它們能夠發送和接收數據。",
            "網絡安全是保護計算機系統和網絡免受數字攻擊的實踐。"
        ]
        
        # 生成更多測試文本（重複和變化）
        self.large_test_set = []
        for i in range(100):
            base_text = self.test_texts[i % len(self.test_texts)]
            # 添加一些變化使文本稍有不同
            variation = f"第{i+1}條：{base_text}"
            self.large_test_set.append(variation)

    def test_cache_functionality(self):
        """測試緩存基本功能"""
        logger.info("=== 測試 Embedding Cache 基本功能 ===")
        
        # 創建臨時緩存目錄
        temp_dir = tempfile.mkdtemp()
        try:
            # 初始化 RAG 系統，啟用緩存
            rag = HybridContextualRAG()
            rag.use_embedding_cache = True
            rag.embedding_cache_dir = temp_dir
            os.makedirs(temp_dir, exist_ok=True)
            
            test_text = "這是一個測試文本用於驗證緩存功能。"
            
            # 第一次生成 embedding（應該沒有緩存）
            logger.info("第一次生成 embedding（無緩存）...")
            start_time = time.time()
            embeddings1 = rag._get_embeddings_batch([test_text])
            first_time = time.time() - start_time
            logger.info(f"第一次耗時: {first_time:.3f}秒")
            
            # 檢查緩存文件是否被創建
            cache_files = os.listdir(temp_dir)
            logger.info(f"緩存文件數量: {len(cache_files)}")
            
            # 第二次生成同樣的 embedding（應該使用緩存）
            logger.info("第二次生成 embedding（使用緩存）...")
            start_time = time.time()
            embeddings2 = rag._get_embeddings_batch([test_text])
            second_time = time.time() - start_time
            logger.info(f"第二次耗時: {second_time:.3f}秒")
            
            # 驗證結果一致性
            if np.allclose(embeddings1, embeddings2, rtol=1e-6):
                logger.info("✅ 緩存結果與原始結果一致")
            else:
                logger.error("❌ 緩存結果與原始結果不一致")
            
            # 性能提升
            if second_time > 0 and second_time < first_time:
                speedup = first_time / second_time
                logger.info(f"✅ 緩存帶來 {speedup:.2f}x 速度提升")
            elif second_time == 0:
                logger.info("✅ 緩存帶來極大速度提升（第二次幾乎瞬間完成）")
            else:
                logger.warning("⚠️ 緩存未能帶來性能提升")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ 緩存功能測試失敗: {e}")
            return False
        finally:
            # 清理臨時目錄
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def test_batch_processing_performance(self):
        """測試批次處理性能"""
        logger.info("=== 測試批次處理性能 ===")
        
        temp_dir = tempfile.mkdtemp()
        try:
            # 測試不同批次大小的性能
            batch_sizes = [1, 8, 16, 32, 64]
            results = {}
            
            for batch_size in batch_sizes:
                logger.info(f"測試批次大小: {batch_size}")
                
                rag = HybridContextualRAG()
                rag.use_embedding_cache = False  # 禁用緩存以測試純批次處理
                rag.embedding_batch_size = batch_size
                
                # 測試50個文本的處理時間
                test_subset = self.large_test_set[:50]
                
                start_time = time.time()
                embeddings = rag._get_embeddings_batch(test_subset)
                processing_time = time.time() - start_time
                
                results[batch_size] = {
                    'time': processing_time,
                    'texts_per_second': len(test_subset) / processing_time,
                    'shape': embeddings.shape
                }
                
                logger.info(f"批次大小 {batch_size}: {processing_time:.3f}秒, "
                          f"{results[batch_size]['texts_per_second']:.2f} texts/sec")
            
            # 找出最佳批次大小
            best_batch_size = max(results.keys(), key=lambda k: results[k]['texts_per_second'])
            logger.info(f"✅ 最佳批次大小: {best_batch_size} "
                       f"({results[best_batch_size]['texts_per_second']:.2f} texts/sec)")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 批次處理測試失敗: {e}")
            return {}
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def test_cache_with_batch_performance(self):
        """測試緩存 + 批次處理組合性能"""
        logger.info("=== 測試緩存 + 批次處理組合性能 ===")
        
        temp_dir = tempfile.mkdtemp()
        try:
            rag = HybridContextualRAG()
            rag.use_embedding_cache = True
            rag.embedding_cache_dir = temp_dir
            rag.embedding_batch_size = 32
            os.makedirs(temp_dir, exist_ok=True)
            
            # 第一輪：生成所有 embeddings（建立緩存）
            logger.info("第一輪：建立緩存...")
            start_time = time.time()
            embeddings1 = rag._get_embeddings_batch(self.large_test_set)
            first_round_time = time.time() - start_time
            logger.info(f"第一輪耗時: {first_round_time:.3f}秒")
            
            cache_files = len(os.listdir(temp_dir))
            logger.info(f"創建緩存文件: {cache_files} 個")
            
            # 第二輪：使用緩存（應該大幅提速）
            logger.info("第二輪：使用緩存...")
            start_time = time.time()
            embeddings2 = rag._get_embeddings_batch(self.large_test_set)
            second_round_time = time.time() - start_time
            logger.info(f"第二輪耗時: {second_round_time:.3f}秒")
            
            # 驗證結果一致性
            if np.allclose(embeddings1, embeddings2, rtol=1e-6):
                logger.info("✅ 批次處理 + 緩存結果一致")
            else:
                logger.error("❌ 批次處理 + 緩存結果不一致")
            
            # 性能提升
            if second_round_time < first_round_time:
                speedup = first_round_time / second_round_time
                logger.info(f"✅ 緩存帶來 {speedup:.2f}x 整體速度提升")
                
                # 測試混合場景（部分緩存，部分新文本）
                logger.info("測試混合場景（50% 緩存 + 50% 新文本）...")
                mixed_texts = self.large_test_set[:50] + [f"新文本 {i}" for i in range(50)]
                
                start_time = time.time()
                mixed_embeddings = rag._get_embeddings_batch(mixed_texts)
                mixed_time = time.time() - start_time
                logger.info(f"混合場景耗時: {mixed_time:.3f}秒")
                
                # 預期時間應該介於第一輪和第二輪之間
                expected_time = (first_round_time + second_round_time) / 2
                if mixed_time <= expected_time * 1.2:  # 允許20%誤差
                    logger.info("✅ 混合場景性能符合預期")
                else:
                    logger.warning("⚠️ 混合場景性能低於預期")
                    
            return {
                'first_round_time': first_round_time,
                'second_round_time': second_round_time,
                'speedup': first_round_time / second_round_time if second_round_time > 0 else 0,
                'cache_files': cache_files
            }
            
        except Exception as e:
            logger.error(f"❌ 緩存 + 批次處理測試失敗: {e}")
            return {}
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def test_memory_usage(self):
        """測試記憶體使用情況"""
        logger.info("=== 測試記憶體使用情況 ===")
        
        try:
            import psutil
            process = psutil.Process()
            
            # 記錄初始記憶體使用
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            logger.info(f"初始記憶體使用: {initial_memory:.2f} MB")
            
            # 創建大量 embeddings
            rag = HybridContextualRAG()
            rag.use_embedding_cache = False  # 先測試不使用緩存
            
            large_test_set = self.large_test_set * 5  # 500個文本
            logger.info(f"處理 {len(large_test_set)} 個文本...")
            
            embeddings = rag._get_embeddings_batch(large_test_set)
            
            # 記錄處理後記憶體使用
            after_processing_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = after_processing_memory - initial_memory
            
            logger.info(f"處理後記憶體使用: {after_processing_memory:.2f} MB")
            logger.info(f"記憶體增長: {memory_increase:.2f} MB")
            logger.info(f"每個 embedding 平均記憶體: {memory_increase * 1024 / len(large_test_set):.2f} KB")
            
            # 檢查 embeddings 大小
            embedding_size = embeddings.nbytes / 1024 / 1024  # MB
            logger.info(f"Embeddings 數據大小: {embedding_size:.2f} MB")
            logger.info(f"Embeddings 形狀: {embeddings.shape}")
            
            return {
                'initial_memory_mb': initial_memory,
                'final_memory_mb': after_processing_memory,
                'memory_increase_mb': memory_increase,
                'embeddings_size_mb': embedding_size,
                'embeddings_shape': embeddings.shape
            }
            
        except ImportError:
            logger.warning("⚠️ psutil 未安裝，跳過記憶體測試")
            return {}
        except Exception as e:
            logger.error(f"❌ 記憶體測試失敗: {e}")
            return {}

    def run_all_tests(self):
        """運行所有測試"""
        logger.info("🚀 開始 Embedding Cache 完整測試套件")
        
        results = {}
        
        # 1. 基本功能測試
        results['cache_functionality'] = self.test_cache_functionality()
        
        # 2. 批次處理性能測試
        results['batch_performance'] = self.test_batch_processing_performance()
        
        # 3. 緩存 + 批次處理組合測試
        results['cache_batch_performance'] = self.test_cache_with_batch_performance()
        
        # 4. 記憶體使用測試
        results['memory_usage'] = self.test_memory_usage()
        
        # 總結報告
        logger.info("=" * 60)
        logger.info("📊 測試總結報告")
        logger.info("=" * 60)
        
        if results['cache_functionality']:
            logger.info("✅ 緩存基本功能正常")
        else:
            logger.info("❌ 緩存基本功能有問題")
        
        if results['batch_performance']:
            best_batch = max(results['batch_performance'].keys(), 
                           key=lambda k: results['batch_performance'][k]['texts_per_second'])
            logger.info(f"✅ 最佳批次大小: {best_batch}")
        
        if results['cache_batch_performance'] and 'speedup' in results['cache_batch_performance']:
            speedup = results['cache_batch_performance']['speedup']
            logger.info(f"✅ 緩存速度提升: {speedup:.2f}x")
        
        if results['memory_usage']:
            memory_per_text = results['memory_usage'].get('memory_increase_mb', 0) * 1024 / 500
            logger.info(f"📈 每個文本記憶體使用: {memory_per_text:.2f} KB")
        
        return results

def main():
    """主函數"""
    test_suite = EmbeddingCacheTestSuite()
    results = test_suite.run_all_tests()
    
    # 保存測試結果
    import json
    output_file = "embedding_cache_test_results.json"
    try:
        # 轉換 numpy 數組為列表以便 JSON 序列化
        json_results = {}
        for key, value in results.items():
            if isinstance(value, dict):
                json_results[key] = {}
                for k, v in value.items():
                    if hasattr(v, 'tolist'):  # numpy array
                        json_results[key][k] = v.tolist()
                    else:
                        json_results[key][k] = v
            else:
                json_results[key] = value
                
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, indent=2, ensure_ascii=False)
        logger.info(f"測試結果已保存到: {output_file}")
    except Exception as e:
        logger.warning(f"無法保存測試結果: {e}")

if __name__ == "__main__":
    main()
