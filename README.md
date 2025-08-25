# AI-CB — 企業內部 HR 專家知識 ChatBot

這是一個前後端分離、可容器化部署的 HR 知識型聊天機器人範例（MVP）。提供本機開發與 Docker Compose 一鍵啟動方式，並內建 LLM 服務代理、健康檢查、與基本串流/非串流回覆 API。

## 目錄
- 快速開始
- 部署流程總覽（Checklist）
- 專案結構
- 本機開發（Windows PowerShell）
- 使用 Docker Compose 啟動（開發/本機容器）
- 生產部署（Production）
- 環境變數設定（backend/.env）
- 資料庫遷移（Alembic）
- RAG 資料初始化（/rag/ingest）
- API 速覽與測試
- Lint / Format / 測試
- 疑難排解

## 快速開始
- 需要的工具：
  - Node.js 20+
  - Python 3.11+
  - Docker / Docker Desktop（可選）
- 後端先在 `backend/.env` 設定必要環境變數（見「環境變數設定」）。
- 開兩個終端（或分頁）：前端在 3000 連接，後端在 8000 提供 API。

## 部署流程總覽（Checklist）
1) 安裝必要工具（Node 20+ / Python 3.11+ / Docker 可選）。
2) 建立並填好 `backend/.env`（LLM_BASE_URL、DATABASE_URL、REDIS_URL...）。
3) 啟動服務：本機直跑或使用 Docker Compose。
4) 執行資料庫遷移（Alembic：`alembic upgrade head`）。
5) 初始化/匯入 RAG 資料（呼叫 `/rag/ingest` 或放入 `backend/data/rag_store`）。
6) 健康檢查與 API 驗收（/health、/llm/ping）。
7) 生產部署：關閉熱更新、設定 workers、持久化資料與監控。

## 專案結構
```
AI-CB/
├─ docker-compose.yml
├─ README.md
├─ backend/
│  ├─ Dockerfile
│  ├─ pyproject.toml
│  ├─ requirements.txt
│  ├─ alembic.ini
│  ├─ migrations/
│  └─ src/
│     ├─ main.py                # FastAPI 入口，/health 與 LLM 路由註冊
│     ├─ _health_check.py       # 本地 smoke 測試輔助
│     ├─ smoke_test.py          # 內部 ASGI smoke 測試
│     ├─ llm/
│     │  ├─ config.py           # LLM_* 環境變數讀取
│     │  ├─ routes.py           # /llm/generate /llm/generate_stream /llm/ping
│     │  └─ services.py         # OpenAI 相容 API 呼叫（含 SSE 串流）
│     ├─ rag/
│     │  ├─ config.py           # EMBEDDING_*, RAG_* 設定
│     │  ├─ embeddings.py       # FastEmbed/ONNX E5 向量化
│     │  ├─ routes.py           # /rag/ingest /rag/query /rag/ask
│     │  └─ store.py            # 檔案型簡單向量庫（npy+json）
│     └─ database/
│        ├─ connection.py       # SQLAlchemy/Redis 設定（可選）
│        └─ models.py           # 範例資料表模型
└─ frontend/
   ├─ Dockerfile
   ├─ package.json
   ├─ vite.config.ts            # 代理 /api → http://127.0.0.1:8000
   └─ src/
```

## 本機開發（Windows PowerShell）
建議開兩個終端分別跑前端與後端。

1) 後端（FastAPI + Uvicorn，埠 8000）
- 建立與啟用虛擬環境（可選）：
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
- 安裝相依：
```powershell
pip install -r backend/requirements.txt
```
- 設定環境（可在 backend/.env，見下一節）。
- 以專案根目錄啟動（避免 import 問題）：
```powershell
python -m uvicorn --app-dir backend src.main:app --reload --port 8000
```
（或切到 backend 目錄後執行）
```powershell
cd backend
python -m uvicorn src.main:app --reload --port 8000
```
若遇到模組匯入問題，可臨時設定：
```powershell
$env:PYTHONPATH = "backend"
python -m uvicorn src.main:app --reload --port 8000
```

2) 前端（Vite 開發伺服器，埠 3000）
```powershell
cd frontend
npm install
npm run dev
```
瀏覽器打開：http://localhost:3000

後端健康檢查：http://127.0.0.1:8000/health
```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## 使用 Docker Compose 啟動（開發/本機容器）
於專案根目錄：
```powershell
docker compose up --build
```
- 前端：http://localhost:3000（Vite dev server）
- 後端：http://localhost:8000（FastAPI）
- Postgres：localhost:5432（帳密與 DB 名見 compose）
- Redis：localhost:6379

提示：Compose 以掛載 volume 進行熱更新，開發時很方便；若要純生產模式，建議調整 Dockerfile 與 compose（使用 build 輸出而非 dev server）。

## 生產部署（Production）
以下提供以 Docker Compose 的建議作法：

1) 準備環境變數
   - 將生產值填入 `backend/.env`。
   - 在容器網路中，資料庫/快取主機名稱請使用服務名（`postgres`、`redis`）。

2) 建立生產覆蓋檔（選擇性）：`docker-compose.prod.yml`
```yaml
services:
  backend:
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 2
    environment:
      PYTHONUNBUFFERED: "1"
      DATABASE_URL: postgresql+psycopg2://app:app@postgres:5432/hrchatbot
      REDIS_URL: redis://redis:6379/0
      LLM_BASE_URL: ${LLM_BASE_URL:-http://your-llm-host:8001}
  frontend:
    command: npm run preview -- --host 0.0.0.0 --port 3000
```

3) 以生產參數啟動
```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

4) 執行 Alembic 遷移（確保 DB schema 就緒）
```powershell
docker compose exec backend alembic upgrade head
```

5) 初始化 RAG（可選）
- 透過 `/rag/ingest` 導入文件；或將檔案放入 `backend/data/rag_store` 並重啟。

6) 驗收與監控
```powershell
curl http://localhost:8000/health
docker compose logs -f backend
```

## 環境變數設定（backend/.env）
在 `backend/.env` 建議設定：
```
# LLM 設定（OpenAI 相容 /v1/chat/completions）
LLM_BASE_URL=http://localhost:8001
LLM_TIMEOUT=60
LLM_MODEL=gpt-oss:20b

# 嵌入/RAG
EMBEDDING_MODEL=intfloat/e5-base-v2
EMBEDDING_CACHE_DIR=./backend/src/models
RAG_STORE_DIR=./backend/data/rag_store
RAG_TOP_K=5

# 資料庫/快取（本機直跑）
DATABASE_URL=postgresql+psycopg2://app:app@localhost:5432/hrchatbot
REDIS_URL=redis://localhost:6379/0

# 容器/Compose 內建議（重點：服務名作為主機名稱）
# DATABASE_URL=postgresql+psycopg2://app:app@postgres:5432/hrchatbot
# REDIS_URL=redis://redis:6379/0
```
- `src/main.py` 會在啟動時讀取 `backend/.env`。
- `frontend/vite.config.ts` 已將 `/api` 代理到 `http://127.0.0.1:8000`，前端呼叫以 `/api/...` 即可。

## 資料庫遷移（Alembic）
- 第一次建立遷移（會根據 models 自動偵測差異）：
```powershell
alembic revision --autogenerate -m "init"
```
- 升級到最新：
```powershell
alembic upgrade head
```
- 以 Docker Compose 執行：
```powershell
docker compose exec backend alembic upgrade head
```
提示：`alembic.ini` 內已設定 `script_location = backend/migrations`，連線字串可用環境變數 `DATABASE_URL` 覆蓋。

## RAG 資料初始化（/rag/ingest）
- 以 API 導入文本（會寫入 `RAG_STORE_DIR` 的 `vectors.npy` 與 `meta.json`）：
```powershell
$items = @{ items = @(
  @{ text = "公司試用期為 3 個月，表現合格者轉正。"; metadata = @{ topic = "policy" } },
  @{ text = "加班需事前申請，並依勞基法計薪。"; metadata = @{ topic = "policy" } }
) } | ConvertTo-Json -Depth 6
Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/ingest" -Method Post -ContentType "application/json" -Body $items
```
- 查詢/問答：
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/query" -Method Post -ContentType "application/json" -Body '{"query":"試用期多久?","top_k":3}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/ask" -Method Post -ContentType "application/json" -Body '{"query":"請問試用期多久?"}'
```

## API 速覽與測試
- 健康檢查：`GET /health`
- LLM（非串流）：`POST /llm/generate`
- LLM（SSE 串流）：`POST /llm/generate_stream`
- LLM Ping：`GET /llm/ping`

請求模型（非串流）
```json
{
  "messages": [
    {"role": "system", "content": "You are an HR expert."},
    {"role": "user",   "content": "請說明試用期轉正的標準流程。"}
  ],
  "context": null
}
```
PowerShell 測試（非串流）：
```powershell
$body = @{ messages = @(
    @{ role = "system"; content = "You are an HR expert." },
    @{ role = "user";   content = "請說明試用期轉正的標準流程。" }
  )} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://127.0.0.1:8000/llm/generate" -Method Post -ContentType "application/json" -Body $body
```
或使用 curl（Windows 10+ 內建）：
```powershell
curl -X POST http://127.0.0.1:8000/llm/generate ^
  -H "Content-Type: application/json" ^
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

串流（SSE）回應會以 `text/event-stream` 傳回，前端可用 `EventSource` 或 `fetch` + 讀取串流處理。

## Lint / Format / 測試
- 前端：
```powershell
cd frontend
npm run lint
npm run format
```
- 後端：
```powershell
ruff check backend/src
black --check backend/src
# 自動格式化
black backend/src
```
- Smoke 測試（ASGI in-memory）：
```powershell
python backend/src/smoke_test.py
```

## 疑難排解
- Uvicorn 無法匯入 `src.main:app`
  - 優先使用：`python -m uvicorn --app-dir backend src.main:app --reload --port 8000`
  - 或 `cd backend; python -m uvicorn src.main:app --reload --port 8000`
  - 仍有問題可暫設：`$env:PYTHONPATH = "backend"`
- 前端打 API 404
  - 請確認前端呼叫路徑以 `/api` 開頭；Vite 代理會將 `/api` 重寫為後端根路徑。
- LLM 未回應或 502
  - 檢查 `LLM_BASE_URL` 是否可連線、對應 OpenAI 相容的 `/v1/chat/completions` 端點（services.py 以此為預設）。
- 資料庫/Redis 未啟用
  - 預設程式會連向 `localhost`，若尚未啟動 Postgres/Redis，請調整 `.env` 或使用 Docker Compose。

—
如需補充文件或自動化腳本（如 Alembic migration、pre-commit），可以在 Issue 提出或直接提交 PR。
