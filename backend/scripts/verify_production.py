"""
生產環境優化驗證腳本
檢查所有關鍵配置是否正確設置
"""
import sys
import os

# 添加 backend 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def check_gpu():
    """檢查 GPU 支援"""
    print("="*60)
    print("1️⃣ GPU 支援檢查")
    print("="*60)
    
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
            print(f"✅ CUDA 可用")
            print(f"   GPU: {gpu_name}")
            print(f"   顯存: {gpu_memory} GB")
            print(f"   CUDA 版本: {torch.version.cuda}")
            print(f"   PyTorch 版本: {torch.__version__}")
            return True
        else:
            print("❌ CUDA 不可用")
            print("   請確認:")
            print("   1. 安裝了 NVIDIA 驅動程式")
            print("   2. PyTorch 是 CUDA 版本 (pip install torch --index-url https://download.pytorch.org/whl/cu121)")
            return False
    except Exception as e:
        print(f"❌ GPU 檢查失敗: {e}")
        return False

def check_embedding_model():
    """檢查嵌入模型 GPU 加速"""
    print("\n" + "="*60)
    print("2️⃣ 嵌入模型 GPU 加速檢查")
    print("="*60)
    
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        import time
        
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"載入模型到 {device.upper()}...")
        
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        model = model.to(device)
        
        print(f"✅ 模型已載入")
        print(f"   設備: {model.device}")
        
        # 測試編碼
        test_texts = ["測試文本"] * 100
        start = time.time()
        embeddings = model.encode(test_texts, batch_size=128, device=device, show_progress_bar=False)
        elapsed = time.time() - start
        throughput = len(test_texts) / elapsed
        
        print(f"   測試: 100 個文本")
        print(f"   耗時: {elapsed:.3f}秒")
        print(f"   吞吐量: {throughput:.1f} texts/s")
        
        if device == 'cuda' and throughput > 100:
            print(f"✅ GPU 加速正常 (吞吐量 > 100 texts/s)")
            return True
        elif device == 'cpu':
            print(f"⚠️ 使用 CPU 模式，性能受限")
            return False
        else:
            print(f"⚠️ GPU 吞吐量較低，請檢查批次大小配置")
            return False
            
    except Exception as e:
        print(f"❌ 嵌入模型測試失敗: {e}")
        return False

def check_dependencies():
    """檢查關鍵依賴"""
    print("\n" + "="*60)
    print("3️⃣ 依賴套件檢查")
    print("="*60)
    
    required_packages = {
        'fastapi': '後端框架',
        'uvicorn': 'ASGI 伺服器',
        'waitress': 'Windows 生產伺服器',
        'redis': 'Redis 客戶端',
        'sentence_transformers': '嵌入模型',
        'faiss': 'FAISS 向量庫',
        'whoosh': 'BM25 全文檢索'
    }
    
    all_ok = True
    for package, description in required_packages.items():
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package:<25} ({description})")
        except ImportError:
            print(f"❌ {package:<25} 未安裝")
            all_ok = False
    
    return all_ok

def check_rag_system():
    """檢查 RAG 系統配置"""
    print("\n" + "="*60)
    print("4️⃣ RAG 系統配置檢查")
    print("="*60)
    
    try:
        # 設定環境變數 (測試用)
        os.environ.setdefault('MODEL_NAME', 'gpt-oss:20b')
        os.environ.setdefault('LLM_API_BASE', 'http://localhost:11434')
        os.environ.setdefault('GPU_BATCH_SIZE', '128')
        
        from app.rag.contextual_rag import HybridContextualRAG
        import torch
        
        print("初始化 RAG 系統...")
        rag = HybridContextualRAG()
        
        print(f"✅ RAG 系統已初始化")
        print(f"   設備: {rag.device if hasattr(rag, 'device') else 'N/A'}")
        print(f"   批次大小: {rag.batch_size if hasattr(rag, 'batch_size') else 'N/A'}")
        print(f"   向量維度: {rag.embedding_dimension}")
        print(f"   總向量數: {rag.index.ntotal}")
        print(f"   Reranker: {'已啟用' if rag.has_reranker else '未啟用'}")
        
        if hasattr(rag, 'device') and rag.device == 'cuda':
            print(f"✅ GPU 加速已啟用")
            return True
        else:
            print(f"⚠️ GPU 加速未啟用，請檢查 contextual_rag.py")
            return False
            
    except Exception as e:
        print(f"❌ RAG 系統初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_redis():
    """檢查 Redis 連線"""
    print("\n" + "="*60)
    print("5️⃣ Redis 快取檢查")
    print("="*60)
    
    try:
        import redis
        
        # 測試連線
        client = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=2)
        client.ping()
        
        info = client.info('server')
        print(f"✅ Redis 已連線")
        print(f"   版本: {info.get('redis_version', 'N/A')}")
        print(f"   模式: {info.get('redis_mode', 'N/A')}")
        return True
        
    except redis.ConnectionError:
        print(f"⚠️ Redis 未運行")
        print(f"   快取功能將被禁用")
        print(f"   啟動 Redis: 安裝 Memurai 或使用 WSL2")
        return False
    except Exception as e:
        print(f"❌ Redis 檢查失敗: {e}")
        return False

def check_env_config():
    """檢查環境變數配置"""
    print("\n" + "="*60)
    print("6️⃣ 環境變數配置檢查")
    print("="*60)
    
    critical_vars = {
        'MODEL_NAME': 'LLM 模型名稱',
        'LLM_API_BASE': 'LLM API 端點',
        'GPU_BATCH_SIZE': 'GPU 批次大小',
    }
    
    optional_vars = {
        'ENABLE_REDIS_CACHE': 'Redis 快取開關',
        'UVICORN_WORKERS': 'Worker 數量',
        'CUDA_VISIBLE_DEVICES': 'GPU 設備 ID'
    }
    
    print("必要配置:")
    for var, desc in critical_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var:<20} = {value} ({desc})")
        else:
            print(f"⚠️ {var:<20} 未設定 ({desc})")
    
    print("\n可選配置:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        status = "✅" if value else "  "
        print(f"{status} {var:<25} = {value or '(未設定)'} ({desc})")
    
    return True

def main():
    print("\n" + "="*60)
    print("🔧 ChatBot 生產環境優化驗證")
    print("="*60)
    print("檢查 RTX 4090 GPU 加速、多 Worker、Redis 快取配置\n")
    
    results = []
    
    # 執行所有檢查
    results.append(("GPU 支援", check_gpu()))
    results.append(("嵌入模型 GPU", check_embedding_model()))
    results.append(("依賴套件", check_dependencies()))
    results.append(("RAG 系統", check_rag_system()))
    results.append(("Redis 快取", check_redis()))
    results.append(("環境變數", check_env_config()))
    
    # 總結
    print("\n" + "="*60)
    print("📊 驗證總結")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通過" if result else "❌ 失敗" if "GPU" in name or "RAG" in name else "⚠️ 警告"
        print(f"{status:<10} {name}")
    
    print(f"\n通過率: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 所有檢查通過！系統已準備好部署。")
        print("\n下一步:")
        print("1. 啟動生產環境: .\\backend\\start_production.ps1 -Workers 32")
        print("2. 運行性能測試: python backend\\scripts\\gpu_benchmark.py")
        print("3. 查看部署文檔: PRODUCTION_DEPLOYMENT.md")
    elif passed >= 4:
        print("\n✅ 核心功能正常，可以啟動測試。")
        print("⚠️ 部分功能未啟用，請查看上方警告。")
    else:
        print("\n❌ 檢查失敗過多，請修復問題後重試。")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 檢查已中斷")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 驗證腳本執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
