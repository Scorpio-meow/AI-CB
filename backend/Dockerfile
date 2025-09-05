FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 安裝系統依賴（包含 curl 與 PostgreSQL build 需要的套件）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       g++ \
       build-essential \
       libpq-dev \
       curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install dependencies first to leverage Docker layer cache
COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 建立資料目錄並使用非 root 使用者運行
RUN mkdir -p /app/data/uploads /app/data/vector_db \
    && addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app

USER appuser

# 暴露端口
EXPOSE 8001

# 啟動命令（保留 exec 形式，讓 PID 1 接收信號）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--log-level", "info"]
