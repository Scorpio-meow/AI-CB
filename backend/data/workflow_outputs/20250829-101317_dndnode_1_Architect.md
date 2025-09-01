## 1. 目標與限制  
| 目標 | 具體數值 | 重要性 |
|------|----------|--------|
| **即時叫號同步** | ≤ 2 s（從「叫號」→「手機端收到通知」） | ★★★★★ |
| **資料一致性** | 99.9 %（寫入 → 讀取 → 服務完成） | ★★★★★ |
| **可用率** | 99.5 % SLA（24/7 服務） | ★★★★ |
| **可擴展性** | 10 k 同時連線、每日 > 10 萬筆排隊記錄 | ★★★★ |
| **安全合規** | TLS 1.2+、GDPR/個資保護、敏感欄位加密 | ★★★★ |
| **成本效益** | 離線可作緩存、無硬體依賴、雲端成本 ≤ 20 % 現有系統 | ★★★ |

> **限制**  
> - 取號機只能提供 QR 讀取；  
> - 移動端僅支援 Android/iOS；  
> - 系統必須能在 3 個月內交付 MVP，且不需要第三方 API（僅內部短信、FCM/APNs）。  

---

## 2. 技術選型表（語言/框架/關鍵套件與取捨理由）  

| 層級 | 技術 | 為什麼選擇 | 取捨 |
|------|------|-------------|------|
| **API / Web** | **Spring Boot (Java 21)** | 穩定、企業級，支援 Spring Cloud Sleuth、Actuator、WebFlux（非同步） | 可選 Kotlin + Spring Boot (若團隊更偏 Kotlin) |
| **即時通訊** | **Spring WebSocket (STOMP over SockJS)** + **Redis Pub/Sub** | 低延遲、水平可擴展、與 Spring 生態集成 | 不採用 Socket.io，因 Java 團隊更熟悉 |
| **資料庫** | **PostgreSQL 15** (主表)、**Redis 7** (快取/佇列) | ACID、行鎖、全文檢索；Redis 供 Pub/Sub、緩存、排程 | 若資料量激增可加行分區、Postgres‑XTP |
| **推送通知** | **Firebase Cloud Messaging (Android)**, **APNs (iOS)** | 兩路通知、成熟 SDK、可靠投遞 | 不使用 Apple Push Notification Service (APNS) 自行實作 |
| **身份驗證** | **JWT** (RS256) + **OAuth2 Resource Server** | 無狀態、跨域、支持多租戶 | 不採用 Session / Cookie |
| **OTP 驗證** | **Twilio / 阿里雲短信** | 可靠短信、可自定義語言、已合規 | 不採用自建短信閘道 |
| **CI/CD** | **GitHub Actions** + **Docker + Helm** | 直觀、容器化、K8s 原生 | 不使用 Jenkins |
| **監控** | **Prometheus + Grafana** + **OpenTelemetry** | 直觀度量、分佈式追蹤、易告警 | 不採用 Datadog、NewRelic |
| **日誌** | **Elastic Stack (ELK)** | 索引全文、可視化、易搜索 | 不使用 Loki |
| **基礎架構** | **Kubernetes (EKS/GKE/AKS)** | 自動水平擴展、滾動更新、灰度部署 | 不使用 Serverless (Lambda/Fargate) 以避免冷啟動 |

---

## 3. 系統拓撲 / 模組分層與邊界  

```
┌───────────────────────────────────────┐
│               Load Balancer / Nginx   │
│  (TLS termination, rate limiting)     │
└───────────────┬───────────────────────┘
                │
┌───────────────────────────────────────┐
│             API Gateway (Spring Boot) │
│  - Auth & Rate Limit (JWT)             │
│  - HTTP ↔ gRPC/WebSocket bridge        │
└───────────────┬───────────────────────┘
                │
┌───────────────────────────────────────┐
│          Application Layer            │
│  • Queue Service (business logic)      │
│  • Notification Service (push + WS)    │
│  • OTP Service (SMS)                   │
│  • QR/QR‑Code Service (validation)     │
│  • Staff / Admin Service (CRUD)        │
└───────────────┬───────────────────────┘
                │
┌───────────────────────────────────────┐
│          Infrastructure Layer          │
│  • PostgreSQL (ACID)                   │
│  • Redis (Pub/Sub, Cache, Queue)       │
│  • Vault / K8s Secrets (secret mgmt)   │
│  • FCM/APNs (push clients)             │
└───────────────┬───────────────────────┘
                │
┌───────────────────────────────────────┐
│        Client Layer (Web/Mobile)       │
│  • Web UI (React / Vue)                │
│  • Mobile (Android/iOS)                │
│  • QR Reader / Offline Mode            │
└───────────────────────────────────────┘
```

**分層說明**  

| 層級 | 角色 | 主責任 | 主要技術 |
|------|------|--------|----------|
| **Presentation** | 前端 / 取號機 | UI、客戶互動、QR 掃描、WebSocket 連線 | React / Vue + WebSocket |
| **Application** | 服務邏輯 | 排隊計算、叫號順序、狀態轉移、重試、交易一致性 | Spring Service, Saga pattern |
| **Domain** | 實體模型 | QueueItem, CallRecord, OTP, Staff | Domain‑Driven Design |
| **Infrastructure** | 資料存取、外部服務 | PostgreSQL, Redis, SMS API, FCM/APNs, Vault | Spring Data, RedisTemplate, RestTemplate |

---

## 4. 資料庫設計  

### 4.1 主表與關聯  

| 表 | 主鍵 | 主要欄位 | 索引 | 備註 |
|----|------|----------|------|------|
| **services** | service_id | name, description | PK | 服務類型 |
| **customers** | customer_id | phone, name, encrypted_ssn | PK | 電話作為 OTP 觸發鍵 |
| **otp_codes** | otp_id | phone, code, expire_at, used_at | PK, idx_phone_expire | 5 min 有效 |
| **queue_items** | queue_id | service_id, customer_id, created_at, status, seq_no, staff_id, updated_at | PK, idx_service_status, idx_status | status: WAITING, CALLED, SERVING, DONE |
| **call_records** | call_id | queue_id, staff_id, called_at, served_at, finished_at | PK | 用於審計、報表 |
| **staff** | staff_id | name, role, department | PK | 角色: STAFF, ADMIN |
| **audit_logs** | audit_id | queue_id, field_changed, old_value, new_value, changed_at, changed_by | PK, idx_queue_changed | 所有狀態改變 |
| **config** | key | value | PK | 動態參數 (如速率限制) |

### 4.2 索引（重點）  

- `queue_items(service_id, status, seq_no)` – 叫號順序查詢  
- `queue_items(customer_id)` – 客戶最近排隊記錄  
- `call_records(queue_id)` – 查詢歷史服務  
- `audit_logs(queue_id, changed_at)` – 審計查詢  

### 4.3 事務一致性  

- 取號: `BEGIN; INSERT queue_item; INSERT otp_codes; COMMIT;`  
- 叫號: 先 `SELECT ... FOR UPDATE` 取下一筆，更新 `status='CALLED'`，再 `COMMIT`  
- 使用 **Saga** 模式：  
  - 步驟 1: 取號 → 事件 `queue.created`  
  - 步驟 2: 叫號 → 事件 `queue.called`  
  - 步驟 3: 完成 → 事件 `queue.completed`  
  - 若任何步驟失敗，觸發補償（回退）  

---

## 5. API / 事件合約 & 錯誤處理  

### 5.1 REST API 範例  

| 方法 | 路徑 | 說明 | 請求 Body | 回應 | 錯誤碼 |
|------|------|------|-----------|------|--------|
| POST | /api/queue/take | 取號 | `{serviceId, phone}` | `201 Created`, `{queueId, seqNo}` | 400 (invalid), 401 (unauth), 503 (service busy) |
| GET | /api/queue/status/{queueId} | 查詢排隊位置 | - | `200 OK`, `{status, position, eta}` | 404 (not found) |
| POST | /api/staff/next | 櫃員叫號 | `{staffId}` | `200 OK`, `{queueId, seqNo}` | 400, 401, 409 (already called) |
| POST | /api/notification/subscribe | WebSocket 連線（透過 STOMP header） | - | `200 OK` | 401 |
| POST | /api/qr/scan | QR 碼驗證 | `{qrToken}` | `200 OK`, `{queueId}` | 400, 410 (expired) |

### 5.2 WebSocket 事件  

| 事件 | Payload | 用途 |
|------|---------|------|
| `queue.created` | `{queueId, serviceId, seqNo}` | 客戶端即時更新排隊號 |
| `queue.status_changed` | `{queueId, status, eta}` | 同步叫號與服務進度 |
| `call.notified` | `{queueId, staffId}` | 櫃員成功推送通知 |

### 5.3 事件合約（Kafka/Redis Pub/Sub）  

| Channel | Payload | 訂閱者 |
|---------|---------|--------|
| `queue_events` | `queue.created/called/served` | 所有微服務、監控 |
| `notification_events` | `push_sent/success/failure` | Notification Service, Auditing |

### 5.4 錯誤處理  
- 所有 API 回傳 `errorCode`、`errorMsg`、`retryAfter`（若適用）。  
- WebSocket 失敗時自動重連（10 s 後重試 3 次）。  
- 推送失敗持續 3 次後標記 `push_failed` 並發送 FCM 退訂事件。  
- 交易失敗 (deadlock) 會觸發自動重試 2 次，仍失敗則 rollback 並回報 `503 Service Unavailable`。  

---

## 6. 安全性清單  

| 層級 | 措施 | 工具/實作 | 備註 |
|------|------|-----------|------|
| **傳輸** | TLS 1.2+ | Let’s Encrypt + Nginx termination | 所有內外流量 |
| **身份驗證** | JWT (RS256) | Spring Security OAuth2 Resource Server | 失效時間 30 min |
| **授權** | RBAC (ROLE_CUSTOMER, ROLE_STAFF, ROLE_ADMIN) | Spring Security annotations | 角色分隔 |
| **數據保護** | 加密欄位 (customer.phone, SSN) | Jasypt + Postgres pgcrypto | AES‑256 |
| **OTP 安全** | 單次使用、5 min 有效 | DB + 失敗記錄 | 防止重放 |
| **速率限制** | 每號碼 5 次/分鐘 | Bucket4j | 防止刷號 |
| **祕密管理** | HashiCorp Vault / K8s Secrets | 只對授權 POD 可見 | 避免硬編碼 |
| **審計** | 所有狀態變更寫 audit_logs | PostgreSQL | 可追溯 |
| **DDOS 防禦** | Cloudflare + WAF | 速率限制 + IP 黑名單 | 內部部署可選 |
| **CORS** | 只允許前端域名 | Spring CORS config | 防止 CSRF |

---

## 7. Observability  

### 7.1 日誌  
- **ELK**：Filebeat → Logstash → Elasticsearch → Kibana  
- 標準格式：JSON (timestamp, level, service, requestId, traceId, spanId, message)  
- 重要事件：queue.created, queue.called, push.sent, push.failed, error.stack

### 7.2 追蹤  
- **OpenTelemetry** SDK (Java) → Jaeger/Zipkin collector → Grafana dashboards  
- 追蹤 ID 透過 HTTP header `traceparent`

### 7.3 指標  
- **Prometheus** 內嵌 `micrometer-registry-prometheus`  
- 主要指標：  
  - `http_request_duration_seconds`  
  - `queue_wait_time_seconds`  
  - `push_success_total`, `push_failure_total`  
  - `db_query_latency_seconds`  
  - `redis_cache_hit_ratio`  
- **Grafana**：即時儀表板、異常告警  
- **告警**：Alertmanager → Slack/Teams

---

## 8. DevOps 與部署策略  

| 步驟 | 內容 | 工具 |
|------|------|------|
| **Container** | 所有服務打包為 Docker Image | Dockerfile, BuildKit |
| **CI** | GitHub Actions → lint, unit, integration, k6 load test, image build | GitHub Actions |
| **Repository** | Helm Chart（主 chart + sub‑chart for each service） | Helm 3 |
| **CD** | Argo CD / Flux CD → GitOps, auto‑deploy to K8s | Argo CD |
| **環境** | dev → staging → production | 3‑tier K8s clusters (EKS/GKE) |
| **Autoscaling** | HPA (CPU/Memory) + KEDA (Redis queue length) | K8s |
| **Rolling Update** | maxUnavailable: 1, maxSurge: 1 | K8s Deployments |
| **Blue‑Green / Canary** | `canary=true` label, traffic split via Istio/NGINX Ingress | Istio |
| **Rollback** | Helm rollback or Argo CD rollback | Helm / Argo CD |
| **Secrets** | K8s Secrets + Vault CSI | HashiCorp Vault |
| **Observability** | Prometheus ServiceMonitors, Loki, Jaeger | Prometheus, Loki, Jaeger |
| **Backup** | PostgreSQL WAL archiving + pgBackRest | pgBackRest |
| **Failover** | Multi‑AZ PostgreSQL, Redis Sentinel | RDS Multi‑AZ, Redis Cluster |

---

## 9. 專案目錄結構建議  

```
/
├── backend/
│   ├── queue-service/          # 主業務服務
│   ├── notification-service/
│   ├── otp-service/
│   ├── staff-service/
│   ├── config/                 # ConfigServer / Spring Cloud Config
│   ├── shared/                 # 公共依賴、DTO、Model
│   ├── Dockerfile
│   └── pom.xml
├── frontend/
│   ├── web/                    # React/Vue SPA
│   ├── mobile/
│   │   ├── android/
│   │   └── ios/
│   ├── Dockerfile
│   └── package.json
├── infra/
│   ├── helm/
│   │   ├── queue-service/
│   │   ├── notification-service/
│   │   ├── redis/
│   │   ├── postgres/
│   │   └── ingress/
│   ├── scripts/
│   └── kustomize/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── security.md
│   └── ops.md
├── .github/
│   └── workflows/
├── .gitignore
└── README.md
```

- **monorepo** 方便跨語言整合。  
- **backend** 使用 Maven 多模組，統一版本管理。  
- **infra** 版本化 Helm charts，與 CI pipeline 一起部署。  

---

## 10. 擴展性與效能考量  

| 场景 | 需求 | 實作方式 |
|------|------|----------|
| **10k 連線** | WebSocket | NGINX + Spring WebSocket, HPA + NGINX replica |
| **高併發寫入** | 取號寫入 | PostgreSQL row‑level lock + WAL, Redis cache double‑write, async DB write |
| **多地域** | 跨國服務 | 多 AZ PostgreSQL read replicas, Global Redis Cloud, CDNs for static assets |
| **事件流** | 大量事件 | Kafka（可替代 Redis Pub/Sub）作長期記錄，Kafka Connect 走審計表 |
| **資料保留** | 歷史 1 年 | PostgreSQL partition by range (month), TTL 在 Redis |
| **多租戶** | 不同分機 | PostgreSQL schema per tenant, Redis namespace, JWT audience claim |
| **測試壓力** | 5k 併發 | k6 + Docker compose + JMeter, 模擬 2 s 延遲 |

> **性能優化順序**  
> 1. 快取常用資料（queue status, staff availability）至 Redis。  
> 2. 使用 PostgreSQL **pg_stat_statements** 監控慢查詢。  
> 3. 采用 **Connection Pooling**（HikariCP）+ KeepAlive。  
> 4. 測試 WebSocket 換成 **gRPC‑Web** 若發現瓶頸。  

---

## 11. 風險與替代方案  

| 風險 | 影響 | 重要性 | 緩解措施 | 替代方案 |
|------|------|--------|----------|----------|
| **網路斷線** | 取號失敗、叫號延遲 | ★★★★ | 本地緩存、離線取號、WebSocket 重連 | 使用 CDN + Cloudflare Workers 做緩存 |
| **推送失敗** | 客戶未收到叫號 | ★★★★ | 兩路通知、重試 3 次、監控失敗率 | 先行透過 SMS + FCM |
| **資料一致性** | 叫號順序錯亂 | ★★★★ | 事務 + Saga + Redis lock | 使用 **PostgreSQL Row‑Level Lock** + `SELECT ... FOR UPDATE` |
| **DB 壞掉** | 整個排程系統癱瘓 | ★★★★ | RDS Multi‑AZ + read replica, 备份 & 灾备 | 引入 **CockroachDB** 取代 Postgres |
| **Redis 輕量失效** | 快取失效、Pub/Sub 失效 | ★★★ | Sentinel + Cluster | 直接使用 **RabbitMQ** |
| **高併發死鎖** | 交易重試多次 | ★★★ | Deadlock detection, exponential backoff, 監控 lock 時間 | 使用 **Hazelcast** 分布式鎖 |
| **安全漏洞** | 數據洩露 | ★★★★ | 祕密管理、審計、速率限制 | 使用 **AWS Secrets Manager** 或 **Google Cloud KMS** |
| **團隊技能曲線** | 延長開發週期 | ★★★ | 先做小型實驗、技術分享、外包部分模組 | 采用 **Node.js + NestJS** 以降低門檻 |

> **備註**  
> 替代方案往往是**增量實作**（如先用 Redis Pub/Sub → 後續改成 Kafka），不會改變整體架構，只是外部服務的選擇。  

---

### 最終交付：MVP 功能清單  

| 功能 | 是否必備 | 開發週期 |
|------|----------|----------|
| 取號（含 OTP） | ✅ | 1‑2 週 |
| 排隊位置查詢 | ✅ | 1 週 |
| 櫃員叫號、順序推送 | ✅ | 1 週 |
| WebSocket 同步客戶端 | ✅ | 1 週 |
| FCM/APNs 兩路推送 | ✅ | 1 週 |
| 取號與叫號兩路通知失敗重試 | ✅ | 1 週 |
| 監控日誌追蹤（ELK, Prometheus） | ✅ | 2 週 |
| CI/CD Pipeline (GitHub Actions + Helm) | ✅ | 2 週 |
| 3‑Tier Kubernetes 部署 | ✅ | 1 週 |
| 3 個月內交付 MVP | ✅ | **依賴**：團隊內部 3‑4 名工程師 + 1 名 DevOps |

---

**結論**：上述設計在保持高效能、可擴展、強一致性、可靠推送的同時，符合團隊技術棧、項目時程與安全合規需求。若在實施過程中發現特定瓶頸，可在同一架構下快速替換 Redis → Kafka，或將 WebSocket 轉為 gRPC‑Web。祝開發順利！