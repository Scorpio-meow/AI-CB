# ChatBot 生產環境快速參考卡

## 🚀 快速啟動

### 驗證環境
```powershell
python backend\scripts\verify_production.py
```

### 啟動服務器 (三選一)
```powershell
# 1. Uvicorn 多 Worker (推薦)
.\backend\start_production.ps1 -Workers 32

# 2. Waitress Windows 穩定版
.\backend\start_waitress.ps1 -Threads 32

# 3. VS Code 任務
Ctrl+Shift+P → Run Task → "🚀 生產環境啟動"
```

## 🔧 關鍵配置

### GPU 優化
```bash
GPU_BATCH_SIZE=128          # RTX 4090 最佳批次
CUDA_VISIBLE_DEVICES=0      # 使用第一張 GPU
```

### Worker 配置
| 場景 | Workers | 說明 |
|------|---------|------|
| 開發 | 24 | 保守配置 |
| 生產 | 32 | **推薦** |
| 高負載 | 49 | 最大值 |

### Redis 快取
```bash
ENABLE_REDIS_CACHE=true
CACHE_TTL_SECONDS=300       # 5 分鐘過期
```

## 📊 性能指標

```
✅ GPU 加速: 30-150x 提升
✅ 嵌入吞吐量: 140+ texts/s
✅ 並發處理: 16-24 請求/秒
✅ 快取加速: 10-100x
```

## 🧪 測試命令

```powershell
# GPU 基準測試
python backend\scripts\gpu_benchmark.py

# 並發測試
python backend\scripts\performance_test.py --requests 50

# 快取測試
python backend\scripts\performance_test.py --mode cache

# 壓力測試
python backend\scripts\performance_test.py --mode stress --duration 60
```

## 🐛 常見問題

### GPU 未啟用
```powershell
# 檢查 PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# 若為 False，重新安裝
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### Redis 連線失敗
```bash
# 禁用快取
ENABLE_REDIS_CACHE=false

# 或安裝 Redis for Windows
# https://github.com/tporadowski/redis/releases
```

### 性能不佳
1. 檢查 GPU 利用率: `nvidia-smi -l 1`
2. 調整 Worker 數量: `-Workers 24` 或 `-Workers 49`
3. 增加批次大小: `GPU_BATCH_SIZE=256`

## 📈 監控

```powershell
# 即時日誌
Get-Content backend\logs\chatbot.log -Wait -Tail 50

# GPU 監控
nvidia-smi -l 1

# 快取統計
Invoke-RestMethod http://localhost:8001/api/cache/stats
```

## 📚 文檔

- `PRODUCTION_DEPLOYMENT.md` - 完整部署指南
- `OPTIMIZATION_SUMMARY.md` - 優化總結報告
- `TROUBLESHOOTING.md` - 疑難排解

## 🎯 優化檢查清單

- [x] ✅ PyTorch CUDA 版本 (2.5.1+cu121)
- [x] ✅ RTX 4090 識別 (24GB)
- [x] ✅ 嵌入模型 GPU 模式 (140+ texts/s)
- [x] ✅ RAG 系統 GPU 加速
- [x] ✅ Redis 連線正常
- [x] ✅ 多 Worker 啟動腳本
- [x] ✅ 自動化驗證腳本

**部署狀態**: 🟢 就緒

---
**硬體**: i9-13900KF (24核) + RTX 4090 (24GB)  
**驗證**: 6/6 通過 (100%)  
**更新**: 2025-10-13
