"""
GPU 加速性能基準測試
測試 RTX 4090 在不同批次大小下的嵌入生成性能
"""
import torch
from sentence_transformers import SentenceTransformer, CrossEncoder
import time
import numpy as np
from typing import Dict, List

def benchmark_embedding_model(batch_sizes: List[int] = [1, 8, 16, 32, 64, 128, 256]):
    """測試嵌入模型在不同批次大小下的性能"""
    print("="*60)
    print("🚀 GPU 嵌入模型性能測試")
    print("="*60)
    
    # 檢查 GPU
    if not torch.cuda.is_available():
        print("❌ CUDA 不可用，無法執行 GPU 測試")
        return
    
    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
    print(f"GPU: {gpu_name}")
    print(f"顯存: {gpu_memory} GB\n")
    
    # 載入模型
    print("載入嵌入模型...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device='cuda')
    print(f"✅ 模型已載入至 GPU\n")
    
    # 測試文本
    test_texts = [
        "這是一個測試文本，用於評估嵌入模型的性能。",
        "特休假如何申請？需要什麼條件？",
        "補休到期後會怎樣？是否會累積到下年度？",
        "外勤人員的刷卡規定是什麼？",
        "育嬰留停如何申請？需要準備哪些文件？"
    ] * 100  # 500 個文本
    
    print(f"測試文本數量: {len(test_texts)}\n")
    print("="*60)
    print(f"{'批次大小':<10} {'耗時(秒)':<12} {'吞吐量(text/s)':<18} {'GPU記憶體(GB)':<15}")
    print("="*60)
    
    results = []
    
    for batch_size in batch_sizes:
        try:
            # 清空 GPU 快取
            torch.cuda.empty_cache()
            
            # 熱身
            _ = model.encode(test_texts[:batch_size], batch_size=batch_size, convert_to_numpy=True)
            
            # 正式測試
            start_time = time.time()
            embeddings = model.encode(
                test_texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                device='cuda'
            )
            elapsed = time.time() - start_time
            
            # GPU 記憶體使用
            gpu_mem = torch.cuda.max_memory_allocated() / 1024**3
            
            throughput = len(test_texts) / elapsed
            
            print(f"{batch_size:<10} {elapsed:<12.3f} {throughput:<18.1f} {gpu_mem:<15.2f}")
            
            results.append({
                "batch_size": batch_size,
                "elapsed": elapsed,
                "throughput": throughput,
                "gpu_memory": gpu_mem
            })
            
        except RuntimeError as e:
            if "out of memory" in str(e):
                print(f"{batch_size:<10} ❌ GPU 記憶體不足")
                break
            else:
                raise
    
    print("="*60)
    
    # 找出最佳批次大小
    if results:
        best = max(results, key=lambda x: x["throughput"])
        print(f"\n✨ 最佳配置:")
        print(f"   批次大小: {best['batch_size']}")
        print(f"   吞吐量: {best['throughput']:.1f} text/s")
        print(f"   GPU 記憶體: {best['gpu_memory']:.2f} GB")
    
    return results

def benchmark_cross_encoder():
    """測試 Cross-Encoder 重排序性能"""
    print("\n" + "="*60)
    print("🎯 Cross-Encoder 重排序性能測試")
    print("="*60)
    
    if not torch.cuda.is_available():
        print("❌ CUDA 不可用")
        return
    
    print("載入 Cross-Encoder...")
    reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device='cuda')
    print(f"✅ 模型已載入至 GPU\n")
    
    query = "如何申請特休假？"
    candidates = [
        "特休假申請需要在系統中填寫表單，並經主管核准。",
        "補休假期限為三個月，逾期自動失效。",
        "外勤人員可免刷卡，但需填寫外勤單。",
        "薪資條可在人事系統中查詢下載。",
        "產檢假每次最多給假一天，全年最多七天。"
    ] * 20  # 100 個候選
    
    pairs = [(query, doc) for doc in candidates]
    
    print(f"查詢: {query}")
    print(f"候選數量: {len(candidates)}\n")
    
    # 熱身
    _ = reranker.predict(pairs[:10])
    
    # 測試
    start_time = time.time()
    scores = reranker.predict(pairs)
    elapsed = time.time() - start_time
    
    throughput = len(pairs) / elapsed
    
    print(f"總耗時: {elapsed:.3f}秒")
    print(f"吞吐量: {throughput:.1f} pairs/s")
    print(f"平均延遲: {elapsed/len(pairs)*1000:.2f}ms per pair")
    
    print("="*60)

def benchmark_faiss_search():
    """測試 FAISS 向量檢索性能"""
    print("\n" + "="*60)
    print("🔍 FAISS 向量檢索性能測試")
    print("="*60)
    
    import faiss
    from sentence_transformers import SentenceTransformer
    
    # 載入模型
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device='cuda')
    embedding_dim = model.get_sentence_embedding_dimension()
    
    # 創建測試向量庫
    num_vectors = 10000
    print(f"創建 {num_vectors} 個測試向量...")
    
    # 生成隨機文本
    test_texts = [f"測試文檔 {i}" for i in range(num_vectors)]
    embeddings = model.encode(test_texts, batch_size=128, show_progress_bar=True, convert_to_numpy=True)
    embeddings = embeddings.astype('float32')
    faiss.normalize_L2(embeddings)
    
    # 創建 FAISS 索引
    index = faiss.IndexFlatIP(embedding_dim)
    index.add(embeddings)
    
    print(f"✅ 索引已創建: {index.ntotal} 個向量\n")
    
    # 測試查詢
    query_text = "如何申請特休假？"
    query_embedding = model.encode([query_text], convert_to_numpy=True).astype('float32')
    faiss.normalize_L2(query_embedding)
    
    # 熱身
    _ = index.search(query_embedding, 10)
    
    # 測試不同的 k 值
    k_values = [1, 5, 10, 20, 50, 100]
    print(f"{'Top-K':<10} {'耗時(ms)':<15} {'QPS':<10}")
    print("="*40)
    
    for k in k_values:
        iterations = 1000
        start_time = time.time()
        for _ in range(iterations):
            _ = index.search(query_embedding, k)
        elapsed = time.time() - start_time
        
        avg_time_ms = (elapsed / iterations) * 1000
        qps = iterations / elapsed
        
        print(f"{k:<10} {avg_time_ms:<15.3f} {qps:<10.1f}")
    
    print("="*60)

def compare_cpu_vs_gpu():
    """比較 CPU vs GPU 性能"""
    print("\n" + "="*60)
    print("⚡ CPU vs GPU 性能對比")
    print("="*60)
    
    test_texts = ["測試文本 " * 50] * 100  # 100 個長文本
    
    print(f"測試文本數量: {len(test_texts)}")
    print(f"批次大小: 32\n")
    
    # CPU 測試
    print("🖥️ CPU 測試...")
    model_cpu = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device='cpu')
    start_time = time.time()
    _ = model_cpu.encode(test_texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True)
    cpu_time = time.time() - start_time
    cpu_throughput = len(test_texts) / cpu_time
    
    print(f"   耗時: {cpu_time:.3f}秒")
    print(f"   吞吐量: {cpu_throughput:.1f} text/s\n")
    
    # GPU 測試
    if torch.cuda.is_available():
        print("🚀 GPU 測試...")
        model_gpu = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device='cuda')
        # 熱身
        _ = model_gpu.encode(test_texts[:10], batch_size=32, convert_to_numpy=True)
        
        start_time = time.time()
        _ = model_gpu.encode(test_texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True, device='cuda')
        gpu_time = time.time() - start_time
        gpu_throughput = len(test_texts) / gpu_time
        
        print(f"   耗時: {gpu_time:.3f}秒")
        print(f"   吞吐量: {gpu_throughput:.1f} text/s\n")
        
        speedup = cpu_time / gpu_time
        print(f"🎯 加速比: {speedup:.2f}x")
        print(f"   GPU 比 CPU 快 {speedup:.2f} 倍")
    
    print("="*60)

if __name__ == "__main__":
    print("\n🎮 ChatBot GPU 性能基準測試工具\n")
    
    try:
        # 1. CPU vs GPU 對比
        compare_cpu_vs_gpu()
        
        # 2. 嵌入模型批次大小優化
        benchmark_embedding_model()
        
        # 3. Cross-Encoder 性能
        benchmark_cross_encoder()
        
        # 4. FAISS 檢索性能
        benchmark_faiss_search()
        
        print("\n✅ 所有測試完成！")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 測試已中斷")
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
