# ChatBot 生產環境部署指南 (RTX 4090 + i9-13900KF 優化版)

## 🖥️ 硬體配置

- **CPU**: Intel Core i9-13900KF (24核心32執行緒)
- **GPU**: NVIDIA GeForce RTX 4090 (24GB GDDR6X)
- **記憶體**: 32GB DDR4/DDR5
- **作業系統**: Windows 11 Pro

## 🚀 關鍵優化成果

### 1. GPU 加速 (30-100x 性能提升)
✅ PyTorch 已升級至 **2.5.1+cu121** (支援 CUDA 12.1)  
✅ RTX 4090 成功啟用，24GB 顯存可用  
✅ 嵌入模型批次大小優化至 **128** (RTX 4090 最佳配置)  
✅ 所有向量運算已遷移至 GPU

**預期性能提升**:
- 嵌入生成: 20 tokens/s → **3,000-7,000 tokens/s** (150倍)
- 向量檢索延遲: 數百毫秒 → **10-50ms**
- 批次索引重建: 數分鐘 → **數秒**

### 2. 多 Worker 部署 (24-49 Workers)
✅ Uvicorn 多進程模式已配置  
✅ Waitress Windows 原生支援已安裝  
✅ 推薦配置: **32 Workers** (核心數 × 2 + 1 = 49 為理論最大值)

**執行命令**:
```powershell
# Uvicorn 多 Worker (推薦)
.\backend\start_production.ps1 -Workers 32

# Waitress Windows 穩定版
.\backend\start_waitress.ps1 -Threads 32
```

### 3. Redis 快取層 (10-100x 響應加速)
✅ Redis 快取服務已實現  
✅ 自動快取查詢結果 (TTL: 300秒)  
✅ 快取命中率監控  
✅ 批次快取清理

**啟用方式**:
```bash
# 設定環境變數
ENABLE_REDIS_CACHE=true

# 啟動 Redis (需要另外安裝)
# Windows: 使用 Memurai 或 WSL2 運行 Redis
```

## 📋 快速開始

### 步驟 1: 驗證 GPU 支援
```powershell
# 檢查 CUDA 狀態
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0))"

# 預期輸出:
# CUDA: True
# GPU: NVIDIA GeForce RTX 4090
```

### 步驟 2: 啟動生產環境服務器

**方案 A: Uvicorn 多 Worker (推薦)**
```powershell
cd backend
.\start_production.ps1 -Workers 32 -Port 8001
```

**方案 B: Waitress Windows 原生**
```powershell
cd backend
.\start_waitress.ps1 -Threads 32 -Port 8001
```

**方案 C: VS Code 任務**
- 按 `Ctrl+Shift+P` → "Run Task"
- 選擇 "🚀 生產環境啟動 (32 Workers)"

### 步驟 3: 測試 GPU 性能
```powershell
cd backend
python scripts/gpu_benchmark.py
```

## 🔧 配置文件

### backend/.env.production
```bash
# GPU 配置
GPU_BATCH_SIZE=128          # RTX 4090 最佳批次大小
CUDA_VISIBLE_DEVICES=0      # 使用第一張 GPU

# Redis 快取
ENABLE_REDIS_CACHE=true     # 啟用快取
CACHE_TTL_SECONDS=300       # 快取 5 分鐘

# Workers 配置
UVICORN_WORKERS=32          # 推薦: 24 | 32 | 49

# RAG 系統
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
```

## 📊 性能基準測試

### GPU 加速測試
```powershell
# 完整 GPU 基準測試
python scripts/gpu_benchmark.py

# 測試項目:
# 1. CPU vs GPU 對比
# 2. 不同批次大小吞吐量測試
# 3. Cross-Encoder 重排序性能
# 4. FAISS 向量檢索性能
```

### 並發測試
```powershell
# 安裝依賴
pip install aiohttp

# 執行並發測試 (50 個請求, 10 個並發)
python scripts/performance_test.py --requests 50 --workers 10

# 快取效果測試
python scripts/performance_test.py --mode cache

# 壓力測試 (60 秒持續負載)
python scripts/performance_test.py --mode stress --duration 60
```

## 🎯 最佳實踐

### Workers 數量建議
根據 i9-13900KF (24核心) 的規格:

| 配置 | Workers | 適用場景 |
|------|---------|----------|
| 保守 | 24 | 開發/測試環境 |
| 推薦 | 32 | 生產環境 (平衡性能與穩定性) |
| 激進 | 49 | 高負載場景 (核心數×2+1) |

### GPU 記憶體管理
RTX 4090 24GB 顯存分配建議:
- **嵌入模型**: ~2GB (paraphrase-multilingual-MiniLM-L12-v2)
- **Cross-Encoder**: ~1GB (ms-marco-MiniLM-L-6-v2)
- **批次運算緩衝**: ~10-15GB (batch_size=128)
- **系統預留**: ~5GB

### Redis 快取策略
```python
# 高頻查詢: 5 分鐘快取
CACHE_TTL_SECONDS=300

# 靜態內容: 1 小時快取
CACHE_TTL_SECONDS=3600

# 即時數據: 30 秒快取
CACHE_TTL_SECONDS=30
```

## 🐛 常見問題排查

### 問題 1: GPU 未被識別
```powershell
# 檢查 PyTorch CUDA 版本
python -c "import torch; print(torch.__version__)"

# 若輸出為 2.x.x+cpu，需重新安裝 CUDA 版本:
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 問題 2: Gunicorn 無法在 Windows 運行
**解決方案**: Gunicorn 僅支援 Unix/Linux，Windows 請使用:
- ✅ Uvicorn 多 Worker 模式
- ✅ Waitress (Windows 原生)
- ✅ Docker 容器化部署

### 問題 3: Redis 連線失敗
```bash
# Windows 安裝 Redis 選項:
# 1. Memurai (官方推薦): https://www.memurai.com/
# 2. WSL2 + Redis: wsl --install && wsl apt install redis-server
# 3. 禁用快取: ENABLE_REDIS_CACHE=false
```

### 問題 4: GPU 記憶體不足
```python
# 降低批次大小
GPU_BATCH_SIZE=64  # 從 128 降至 64

# 或使用梯度累積
GPU_BATCH_SIZE=32
```

## 📈 監控與日誌

### GPU 利用率監控
```powershell
# Windows 工作管理員 → 效能 → GPU
# 或使用 nvidia-smi
nvidia-smi -l 1  # 每秒更新
```

### 應用日誌
```powershell
# 即時日誌
Get-Content backend/logs/chatbot.log -Wait -Tail 50

# 性能日誌 (慢查詢)
Select-String -Path backend/logs/chatbot.log -Pattern "SLOW QUERY" -Context 2
```

### Redis 快取統計
```python
# API 端點: GET /api/cache/stats
# 返回: 快取命中率、總鍵數、記憶體使用
```

## 🔒 安全配置

生產環境部署前**必須修改**:
```bash
# backend/.env.production
SECRET_KEY=<使用 openssl rand -hex 32 生成>
REDIS_PASSWORD=<強密碼>
DATABASE_URL=<PostgreSQL 連線字串>
ALLOWED_ORIGINS=<僅允許信任的域名>
```

## 🚢 Docker 部署 (可選)

如需容器化部署:
```powershell
# 構建映像
docker-compose build

# 啟動服務
docker-compose up -d

# 查看日誌
docker-compose logs -f backend
```

## 📞 技術支援

遇到問題請查看:
1. `TROUBLESHOOTING.md` - 疑難排解指南
2. `PERFORMANCE_OPTIMIZATION.md` - 性能調優建議
3. GitHub Issues - 社群支援

## 📝 更新日誌

### v2.0.0 (2025-10-13)
- ✅ GPU 加速全面啟用 (RTX 4090)
- ✅ 多 Worker 生產環境配置 (32 Workers)
- ✅ Redis 快取層實現
- ✅ Windows 原生 Waitress 支援
- ✅ 完整性能測試工具集

---

**部署完成後預期指標**:
- 並發處理: **10-20+ 請求/秒**
- 平均響應時間: **< 2 秒** (包含 LLM 生成)
- GPU 利用率: **70-90%** (峰值負載)
- 快取命中率: **> 40%** (穩定運行後)
