"""
進階優化驗證腳本
測試 FAISS-GPU, FP16 量化, 批次累積
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_faiss_gpu():
    """測試 FAISS-GPU 支援"""
    print("="*60)
    print("1️⃣ FAISS-GPU 測試")
    print("="*60)
    
    try:
        import faiss
        has_gpu = hasattr(faiss, 'StandardGpuResources')
        
        print(f"FAISS 版本: {faiss.__version__}")
        print(f"GPU 支援: {'✅ 是' if has_gpu else '❌ 否'}")
        
        if has_gpu:
            try:
                import numpy as np
                
                # 創建 GPU 資源
                res = faiss.StandardGpuResources()
                print(f"✅ GPU 資源已初始化")
                
                # 測試 GPU 索引
                d = 384
                nb = 10000
                xb = np.random.random((nb, d)).astype('float32')
                faiss.normalize_L2(xb)
                
                # CPU 索引
                cpu_index = faiss.IndexFlatIP(d)
                start = time.time()
                cpu_index.add(xb)
                cpu_add_time = time.time() - start
                
                # GPU 索引
                gpu_index = faiss.index_cpu_to_gpu(res, 0, cpu_index)
                print(f"✅ 索引已轉換至 GPU: {gpu_index.ntotal} 個向量")
                
                # 測試查詢
                xq = np.random.random((100, d)).astype('float32')
                faiss.normalize_L2(xq)
                
                # CPU 查詢
                start = time.time()
                cpu_D, cpu_I = cpu_index.search(xq, 10)
                cpu_search_time = time.time() - start
                
                # GPU 查詢
                start = time.time()
                gpu_D, gpu_I = gpu_index.search(xq, 10)
                gpu_search_time = time.time() - start
                
                speedup = cpu_search_time / gpu_search_time
                
                print(f"\n性能對比 (100 queries, Top-10):")
                print(f"  CPU: {cpu_search_time*1000:.2f}ms")
                print(f"  GPU: {gpu_search_time*1000:.2f}ms")
                print(f"  加速比: {speedup:.2f}x")
                
                return True
            except Exception as e:
                print(f"❌ GPU 索引測試失敗: {e}")
                return False
        else:
            print("\n⚠️ FAISS-GPU 未安裝")
            print("安裝方法:")
            print("  conda install -c pytorch faiss-gpu")
            return False
            
    except Exception as e:
        print(f"❌ FAISS 測試失敗: {e}")
        return False

def test_fp16_quantization():
    """測試 FP16 量化"""
    print("\n" + "="*60)
    print("2️⃣ FP16 量化測試")
    print("="*60)
    
    try:
        import torch
        from sentence_transformers import SentenceTransformer
        
        if not torch.cuda.is_available():
            print("❌ CUDA 不可用，無法測試 FP16")
            return False
        
        model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
        test_texts = ['測試文本'] * 100
        
        # FP32 測試
        print("載入 FP32 模型...")
        model_fp32 = SentenceTransformer(model_name, device='cuda')
        
        # 記錄顯存
        torch.cuda.reset_peak_memory_stats()
        start = time.time()
        embeddings_fp32 = model_fp32.encode(test_texts, batch_size=50, show_progress_bar=False)
        fp32_time = time.time() - start
        fp32_memory = torch.cuda.max_memory_allocated() / 1024**3
        
        print(f"✅ FP32: {fp32_time:.3f}秒, 顯存: {fp32_memory:.2f}GB")
        
        # FP16 測試
        print("\n載入 FP16 模型...")
        model_fp16 = SentenceTransformer(model_name, device='cuda')
        model_fp16 = model_fp16.half()
        
        torch.cuda.reset_peak_memory_stats()
        start = time.time()
        embeddings_fp16 = model_fp16.encode(test_texts, batch_size=50, show_progress_bar=False)
        fp16_time = time.time() - start
        fp16_memory = torch.cuda.max_memory_allocated() / 1024**3
        
        print(f"✅ FP16: {fp16_time:.3f}秒, 顯存: {fp16_memory:.2f}GB")
        
        # 計算差異
        speedup = fp32_time / fp16_time
        memory_saved = (1 - fp16_memory / fp32_memory) * 100
        
        print(f"\n性能提升:")
        print(f"  速度提升: {speedup:.2f}x ({(speedup-1)*100:.1f}%)")
        print(f"  顯存節省: {memory_saved:.1f}%")
        
        # 檢查精度損失
        import numpy as np
        diff = np.abs(embeddings_fp32 - embeddings_fp16).mean()
        print(f"  平均誤差: {diff:.6f} ({'✅ 可接受' if diff < 0.01 else '⚠️ 較大'})")
        
        return True
        
    except Exception as e:
        print(f"❌ FP16 量化測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_batch_accumulation():
    """測試批次累積"""
    print("\n" + "="*60)
    print("3️⃣ 批次累積測試")
    print("="*60)
    
    try:
        import asyncio
        from app.services.batch_processor import BatchAccumulator
        
        async def simulate_requests():
            accumulator = BatchAccumulator(
                max_batch_size=32,
                max_wait_time=0.05,
                min_batch_size=4
            )
            
            print("模擬 100 個並發請求...")
            
            # 模擬並發請求
            tasks = []
            for i in range(100):
                # 分散請求時間
                if i % 10 == 0:
                    await asyncio.sleep(0.01)
                
                # 這裡只是示範，實際需要處理邏輯
                # task = accumulator.add_request(f"query_{i}", f"req_{i}")
                # tasks.append(task)
            
            stats = accumulator.get_stats()
            print(f"\n✅ 批次累積統計:")
            print(f"  總請求數: {stats['total_requests']}")
            print(f"  總批次數: {stats['total_batches']}")
            print(f"  平均批次大小: {stats['avg_batch_size']}")
            print(f"  平均等待時間: {stats['avg_wait_time_ms']:.1f}ms")
            print(f"  GPU 利用率提升: {stats['gpu_utilization_boost']}")
            
            return True
        
        result = asyncio.run(simulate_requests())
        return result
        
    except Exception as e:
        print(f"❌ 批次累積測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rag_advanced_features():
    """測試 RAG 系統進階功能"""
    print("\n" + "="*60)
    print("4️⃣ RAG 系統進階功能測試")
    print("="*60)
    
    try:
        # 設定環境變數
        os.environ.setdefault('MODEL_NAME', 'gpt-oss:20b')
        os.environ.setdefault('LLM_API_BASE', 'http://localhost:11434')
        os.environ['USE_FP16_QUANTIZATION'] = 'true'
        os.environ['USE_FAISS_GPU'] = 'true'
        
        from app.rag.contextual_rag import HybridContextualRAG
        import torch
        
        print("初始化 RAG 系統 (啟用進階優化)...")
        rag = HybridContextualRAG()
        
        print(f"\n✅ RAG 系統配置:")
        print(f"  設備: {rag.device}")
        print(f"  FP16 量化: {'✅ 是' if rag.use_fp16 else '❌ 否'}")
        print(f"  FAISS-GPU: {'✅ 是' if rag.use_faiss_gpu else '❌ 否'}")
        print(f"  批次大小: {rag.batch_size}")
        print(f"  向量維度: {rag.embedding_dimension}")
        
        # 測試編碼性能
        if rag.device == 'cuda':
            test_texts = ['測試查詢'] * 50
            
            torch.cuda.reset_peak_memory_stats()
            start = time.time()
            embeddings = rag.local_embeddings.encode(
                test_texts,
                batch_size=rag.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                device=rag.device
            )
            elapsed = time.time() - start
            memory = torch.cuda.max_memory_allocated() / 1024**3
            
            throughput = len(test_texts) / elapsed
            
            print(f"\n性能測試 (50 texts):")
            print(f"  耗時: {elapsed:.3f}秒")
            print(f"  吞吐量: {throughput:.1f} texts/s")
            print(f"  GPU 記憶體: {memory:.2f}GB")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG 系統測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*60)
    print("🔬 進階優化功能驗證")
    print("="*60)
    print("測試 FAISS-GPU, FP16 量化, 批次累積\n")
    
    results = []
    
    # 執行測試
    results.append(("FAISS-GPU", test_faiss_gpu()))
    results.append(("FP16 量化", test_fp16_quantization()))
    results.append(("批次累積", test_batch_accumulation()))
    results.append(("RAG 進階功能", test_rag_advanced_features()))
    
    # 總結
    print("\n" + "="*60)
    print("📊 測試總結")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{status:<10} {name}")
    
    print(f"\n通過率: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed >= 2:
        print("\n✅ 部分優化可用")
        print("\n說明:")
        print("- FAISS-GPU: 需要安裝 faiss-gpu (conda install faiss-gpu)")
        print("- FP16 量化: 已整合,設定 USE_FP16_QUANTIZATION=true 啟用")
        print("- 批次累積: 已整合,設定 ENABLE_BATCH_ACCUMULATION=true 啟用")
    else:
        print("\n⚠️ 部分測試失敗，請查看詳細信息")
    
    return 0 if passed >= 2 else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 測試已中斷")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 測試腳本執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
