# 1️⃣ Epic 列表（功能群組）  
| Epic 編號 | 名稱 | 主要目標 | 主要模組 |
|-----------|------|----------|----------|
| **E‑CM** | Customer Management | 讓使用者能夠註冊、查詢、更新個人資料 | `backend/customer-service` |
| **E‑QS** | Queue Service | 服務排隊、叫號、同步顯示 | `backend/queue-service` |
| **E‑NT** | Notification Service | 實時推送與 WebSocket 同步 | `backend/notification-service` |
| **E‑OT** | OTP Service | 產生／驗證一次性驗證碼 | `backend/otp-service` |
| **E‑AD** | Admin Dashboard | 管理服務、統計、審計 | `backend/admin-service` |
| **E‑OP** | Ops & Infrastructure | Helm、CI/CD、監控、日誌 | `infra/helm`, `.github/workflows` |

> 每個 Epic 代表一個可交付的業務能力；所有 Story 皆可獨立開發、測試、Review，並不會相互影響。

---

## 2️⃣ Epic E‑CM (Customer Management)

### 2.1 Story CM‑001A – 進行客戶註冊（前端流程）  
- **As a** 新客戶  
- **I want** 在前端填寫電話與姓名並送出註冊表單  
- **So that** 系統能為我產生 OTP 並返回註冊成功資訊  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 前端必須驗證電話格式、避免空值、使用 OAuth2‑PSK 方式呼叫 `/api/customers/register`。 |
| **技術規格** | - React/TypeScript + Formik/Yup。<br>- POST `/api/customers/register`，payload `{ phone, name }`。<br>- 回傳 201 ⇒ `{ customerId, otpExpireAt }`。<br>- 顯示 OTP 輸入頁面。 |
| **資料模型** | N/A（前端） |
| **檔案位置** | `frontend/src/pages/CustomerRegister.tsx`、`hooks/useCustomer.ts` |
| **關聯/依賴** | 依賴後端 API (`/api/customers/register`)。 |
| **測試要求** | - 單元測試表單驗證。<br>- E2E 以 Cypress 送出有效/無效電話。 |
| **驗收條件（GWT）** | **Given** 客戶輸入有效電話與姓名，**When** 提交表單，**Then** 回傳 201 且顯示 OTP 輸入頁。 |
| **DoR** | - UI 設計稿完成。<br>- API 路徑與參數已在 Swagger 內定義。 |
| **DoD** | - 100% 覆蓋率單元測試。<br>- Cypress E2E 通过。<br>- PR 合併至 `develop`。 |
| **PO 任務映射** | CM‑001 (任務 2.2) |

---

### 2.2 Story CM‑001B – 建立 CustomerController (後端)  
- **As a** Backend 開發人員  
- **I want** 在 Spring‑Boot 中定義 `CustomerController`，接收註冊請求  
- **So that** 可以驗證電話、創建客戶、發送 OTP  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 後端必須處理電話驗證、重複註冊、OTP 產生。 |
| **技術規格** | - `POST /api/customers/register`。<br>- 呼叫 `CustomerService.register(phone, name)`。<br>- 回傳 201 以及 `customerId`, `otpExpireAt`。 |
| **資料模型** | `Customer` – `id (UUID)`, `phone (VARCHAR)`, `name (VARCHAR)`, `created_at (TIMESTAMP)`。<br>`OtpCode` – `id`, `phone`, `code`, `expire_at`, `used_at`。 |
| **檔案位置** | `backend/customer-service/src/main/java/com/example/customer/CustomerController.java`<br>`CustomerService.java`、`OtpService.java` |
| **關聯/依賴** | 依賴 `OtpService`, `PhoneValidator`, `TwilioClient`. |
| **測試要求** | - 單元測試：電話驗證、重複註冊、OTP 儲存。<br>- Integration 測試：Mock Twilio、Mock Redis。 |
| **驗收條件（GWT）** | **Given** 未註冊電話，**When** 送出 POST，**Then** 返回 201、OTP 存於資料庫、SMS 已發送。 |
| **DoR** | - Swagger API 需求已完成。<br>- 資料庫表 `customers`, `otp_codes` 已建立。 |
| **DoD** | - 單元測試 80%+ 覆蓋。<br>- 100% CI 通过。<br>- 文檔更新 (`docs/api.md`)。 |
| **PO 任務映射** | CM‑001 (任務 2.3) |

---

### 2.3 Story CM‑001C – OtpService 產生 & 寄送 (後端)  
- **As a** 認證服務開發人員  
- **I want** 在註冊時產生 6 位數 OTP，並寄送 SMS  
- **So that** 用戶能即時收到驗證碼  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 需確保 OTP 唯一、失效時間、重複請求不產生多筆。 |
| **技術規格** | - `OtpService.generateAndSend(phone)`。<br>- 產生隨機 6 位數，存入 `otp_codes`。<br>- `expire_at = now + 5min`。<br>- 呼叫 Twilio REST API。 |
| **資料模型** | `OtpCode` (phone, code, expire_at, used_at=NULL)。 |
| **檔案位置** | `backend/otp-service/src/main/java/com/example/otp/OtpService.java` |
| **關聯/依賴** | `TwilioClient`, `OtpRepository`. |
| **測試要求** | - 單元測試：OTP 6 位、expire_at 正確、相同電話無重複未過期。<br>- Mock Twilio。 |
| **驗收條件（GWT）** | **Given** 電話號碼，**When** 呼叫 `generateAndSend`，**Then** 資料庫有新紀錄，`expire_at` 正確，Twilio 回傳 200。 |
| **DoR** | - Twilio mock 已配置。<br>- 資料庫表已建立。 |
| **DoD** | - 單元測試 80%+ 覆蓋。<br>- CI 通过。<br>- 文檔更新 (`docs/otp.md`)。 |
| **PO 任務映射** | OT‑001 (任務 4.1) |

---

### 2.4 Story CM‑002 – 客戶資料查詢  
- **As a** 客戶  
- **I want** 查詢自己的個人資訊與排隊紀錄  
- **So that** 可以隨時掌握自己的狀態  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 需授權 JWT，保護個人資料。 |
| **技術規格** | - `GET /api/customers/me`。<br>- 回傳 `{ customerId, name, phone, queueHistory: [{queueId, serviceName, status, timestamp}] }`。 |
| **資料模型** | `QueueItem` (service_id, customer_id, status, seq_no, created_at)。 |
| **檔案位置** | `CustomerController.getMe()` in `backend/customer-service`。 |
| **關聯/依賴** | 依賴 `QueueService`。 |
| **測試要求** | - Auth 401/200 測試。<br>- 返回資料完整性測試。 |
| **驗收條件（GWT）** | **Given** 已授權 token，**When** GET /api/customers/me，**Then** 回傳 200 且資料正確。 |
| **DoR** | - JWT 驗證已完成。<br>- Swagger 文檔已更新。 |
| **DoD** | - 單元/集成測試 100% 覆蓋。<br>- PR merge。 |
| **PO 任務映射** | CM‑002 (任務 2.2) |

---

### 2.5 Story CM‑003 – 客戶資訊更新  
- **As a** 客戶  
- **I want** 更新姓名、電話或偏好設定  
- **So that** 資料保持最新  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 需要驗證電話重複性、姓名長度。 |
| **技術規格** | - `PUT /api/customers/me`。<br>- Payload `{ name?, phone?, preferences? }`。<br>- 若更換電話，需重新發送 OTP。 |
| **資料模型** | 同 `Customer`。 |
| **檔案位置** | `CustomerController.updateMe()` |
| **關聯/依賴** | `OtpService`（電話變更時）。 |
| **測試要求** | - 名稱、電話合法性測試。<br>- 電話變更觸發 OTP。 |
| **驗收條件（GWT）** | **Given** 已授權且輸入合法，**When** PUT，**Then** 200 且資料更新。 |
| **DoR** | - 需求文檔已完成。 |
| **DoD** | - 測試覆蓋 80%+。<br>- PR merge。 |
| **PO 任務映射** | CM‑003 (任務 2.3) |

---

## 3️⃣ Epic E‑QS (Queue Service)

### 3.1 Story QS‑001A – 取號（Create Queue Item）  
- **As a** 客戶  
- **I want** 在前端掃描 QR 或輸入服務編號後取號  
- **So that** 系統能為我產生順序號並推算 ETA  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 需避免同一服務同時取號 seqNo 重複。 |
| **技術規格** | - `POST /api/queue/take`。<br>- Payload `{ serviceId, phone }`。<br>- Redis INCR 產生 `seq_no`。<br>- 估算 ETA = (queueLength * avgServeTime)。 |
| **資料模型** | `QueueItem` (id, service_id, customer_id, status, seq_no, eta, created_at)。 |
| **檔案位置** | `QueueController.java`, `QueueService.java` in `backend/queue-service` |
| **關聯/依賴** | `ServiceRepository`, `CustomerRepository`, Redis. |
| **測試要求** | - 單元測試 seq_no 正確。<br>- Integration 測試 Redis INCR。 |
| **驗收條件（GWT）** | **Given** 服務存在且未滿員，**When** POST /api/queue/take，**Then** 201 且 seqNo 連續遞增。 |
| **DoR** | - Redis 已啟動。<br>- Swagger 已定義。 |
| **DoD** | - 100% 覆蓋單元測試。<br>- CI 通过。 |
| **PO 任務映射** | QS‑001 (任務 3.2) |

---

### 3.2 Story QS‑002 – 叫號（Next Queue Item）  
- **As a** 櫃員  
- **I want** 呼叫「叫號」API 讓系統決定下一位客戶  
- **So that** 能有效召喚客戶並推送通知  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 需確保順序、狀態轉換、通知成功。 |
| **技術規格** | - `POST /api/queue/next`。<br>- 服務 ID 需作為參數。<br>- 選取 `status=WAITING` 的最低 `seq_no`。<br>- 更新為 `CALLED`。<br>- 觸發 `NotificationService.sendPush(queueItem)`。 |
| **資料模型** | 同 `QueueItem`。 |
| **檔案位置** | `QueueController.java` (next) |
| **關聯/依賴** | `NotificationService`. |
| **測試要求** | - 單元測試選取正確。<br>- 集成測試通知成功。 |
| **驗收條件（GWT）** | **Given** 有等待客戶，**When** POST /api/queue/next，**Then** 回傳 200 且狀態轉為 CALLED。 |
| **DoR** | - NotificationService 已實作。 |
| **DoD** | - 單元測試 80%+ 覆蓋。<br>- CI 通过。 |
| **PO 任務映射** | QS‑002 (任務 3.2) |

---

### 3.3 Story QS‑003 – WebSocket 同步  
- **As a** 前端開發人員  
- **I want** 透過 WebSocket 接收排隊位置與叫號狀態  
- **So that** 前端能即時更新 UI  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 必須支持多端同步。 |
| **技術規格** | - `GET /ws/queue?queueId=` 端點。<br>- 使用 Spring WebSocket + STOMP。<br>- 每 5 秒推送 `queueStatus`。 |
| **資料模型** | `QueueEvent` (queueId, seqNo, status, eta)。 |
| **檔案位置** | `WebSocketConfig.java`, `QueueWebSocketHandler.java` |
| **關聯/依賴** | `QueueService`. |
| **測試要求** | - Unit test handler logic。<br>- Integration test WebSocket handshake。 |
| **驗收條件（GWT）** | **Given** 前端連線成功，**When** queue 變更，**Then** 立即收到 `queueStatus`。 |
| **DoR** | - WebSocket config 已完成。 |
| **DoD** | - WebSocket unit test。<br>- E2E 测试。 |
| **PO 任務映射** | QS‑003 (任務 3.2) |

---

## 4️⃣ Epic E‑NT (Notification Service)

### 4.1 Story NT‑001 – FCM / APNs 推送  
- **As a** QueueService  
- **I want** 在 queue 變為 CALLED 時推送通知  
- **So that** 客戶手機即時收到「已叫號」訊息  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 必須支持多平台、重試機制。 |
| **技術規格** | - `PushService.sendPush(queueItem)`。<br>- 取得 `device_token`, `platform`。<br>- 使用 `fcm-java` / `apns-client`。<br>- 成功寫入 `notification_logs (status=SUCCESS)`。<br>- 失敗寫入 `FAILURE` 並觸發重試（最大 3 次）。 |
| **資料模型** | `NotificationLog` (id, queue_id, device_token, status, attempt, error_msg, created_at)。 |
| **檔案位置** | `PushService.java` in `backend/notification-service` |
| **關聯/依賴** | `DeviceTokenRepository`, `QueueRepository`. |
| **測試要求** | - 單元測試成功/失敗路徑。<br>- Mock FCM/APNs。 |
| **驗收條件（GWT）** | **Given** queue 變為 CALLED，**When** sendPush，**Then** 200 且日誌成功。 |
| **DoR** | - FCM/APNs credential 已配置。 |
| **DoD** | - 單元測試 80%+ 覆蓋。<br>- CI 通过。 |
| **PO 任務映射** | NT‑001 (任務 5.1) |

---

### 4.2 Story NT‑002 – WebSocket 事件推送  
- **As a** 前端  
- **I want** 透過 WebSocket 即時收到排隊位置、叫號狀態  
- **So that** UI 不需要輪詢。  

（已在 Epic E‑QS 的 QS‑003 覆蓋，這裡重申為獨立 Story，確保獨立交付）  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 前端使用 SockJS + STOMP。 |
| **技術規格** | - Server 端發送 `queueEvent`。<br>- 前端 subscribe `/topic/queue.{queueId}`。 |
| **資料模型** | `QueueEvent` (queueId, status, eta)。 |
| **檔案位置** | `frontend/src/services/queueSocket.ts` |
| **關聯/依賴** | 依賴 QS‑003 WebSocket。 |
| **測試要求** | - E2E 前端接收事件。 |
| **驗收條件（GWT）** | **Given** queue 變更，**When** 事件發送，**Then** 前端立即收到。 |
| **DoR** | - WebSocket 已配置。 |
| **DoD** | - E2E 通过。 |
| **PO 任務映射** | NT‑002 (任務 5.2) |

---

### 4.3 Story NT‑003 – NotificationLog 文檔  
- **As a** DevOps / Technical Writer  
- **I want** 編寫 NotificationLog 的 Swagger/Doc  
- **So that** 前端和其他開發者能正確解讀推送日誌  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 需對外公開 Notification API、日誌查詢。 |
| **技術規格** | - `GET /api/notifications/logs?queueId=`。<br>- Swagger schema。 |
| **資料模型** | `NotificationLog`. |
| **檔案位置** | `NotificationController.java` |
| **關聯/依賴** | `NotificationLogRepository`. |
| **測試要求** | - Auth 測試。 |
| **驗收條件（GWT）** | **Given** 有通知日誌，**When** GET，**Then** 200 返回正確。 |
| **DoR** | - Swagger 已完成。 |
| **DoD** | - CI 通过。 |
| **PO 任務映射** | NT‑003 (任務 5.2) |

---

## 5️⃣ Epic E‑OT (OTP Service)

（上面已提供 CM‑001C、OT‑001C，以下 Story 確保 OTP 服務能被後續驗證使用）

### 5.1 Story OT‑002 – 驗證 OTP (驗證一次性碼)  
- **As a** 客戶  
- **I want** 在前端輸入 OTP 並驗證  
- **So that** 註冊流程完成  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 需檢查 `code`、`expire_at`、`used_at`。 |
| **技術規格** | - `POST /api/otp/verify`。<br>- Payload `{ phone, code }`。<br>- 若有效，`used_at = now`，回傳 200。 |
| **資料模型** | `OtpCode`。 |
| **檔案位置** | `OtpController.java` in `backend/otp-service` |
| **關聯/依賴** | `OtpRepository`. |
| **測試要求** | - 單元測試合法/非法。 |
| **驗收條件（GWT）** | **Given** 正確 OTP，**When** POST /api/otp/verify，**Then** 200 且 `used_at` 設置。 |
| **DoR** | - Swagger 已定義。 |
| **DoD** | - 單元測試 80%+ 覆蓋。<br>- CI 通过。 |
| **PO 任務映射** | OT‑002 (任務 4.2) |

---

## 6️⃣ Epic E‑AD (Admin Dashboard)

### 6.1 Story AD‑001 – 管理服務（新增/刪除）  
- **As a** Admin  
- **I want** 新增或刪除服務（`serviceId`）  
- **So that** 我能控制可排隊的服務項目  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 需驗證 `serviceName` 唯一、權限 `ADMIN`。 |
| **技術規格** | - `POST /api/admin/services`（新增）。<br>- `DELETE /api/admin/services/{id}`（刪除）。 |
| **資料模型** | `Service` (id, name, avgServeTime, capacity, created_at)。 |
| **檔案位置** | `AdminServiceController.java` in `backend/admin-service` |
| **關聯/依賴** | `ServiceRepository`. |
| **測試要求** | - 角色 403/200 測試。 |
| **驗收條件（GWT）** | **Given** 有 ADMIN token，**When** POST/DELETE，**Then** 200 且資料變更。 |
| **DoR** | - Swagger 已定義。 |
| **DoD** | - 單元測試覆蓋 80%+。 |
| **PO 任務映射** | AD‑001 (任務 6.1) |

---

### 6.2 Story AD‑002 – 排隊統計（GET）  
- **As a** Admin  
- **I want** 查看服務排隊統計（平均等待時間、呼叫頻次）  
- **So that** 可以評估業務表現  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 需聚合 `QueueItem`、`NotificationLog`。 |
| **技術規格** | - `GET /api/admin/queues?serviceId=`。<br>- 回傳 `{ serviceId, totalCalls, avgWaitTime, lastCalled }`。 |
| **資料模型** | 同 `QueueItem`, `NotificationLog`. |
| **檔案位置** | `AdminController.getQueueStats()` |
| **關聯/依賴** | `QueueService`. |
| **測試要求** | - SQL 聚合測試。 |
| **驗收條件（GWT）** | **Given** 已存在排隊資料，**When** GET，**Then** 200 且統計正確。 |
| **DoR** | - 需求已寫入 JIRA。 |
| **DoD** | - 單元/集成測試 100%。 |
| **PO 任務映射** | AD‑002 (任務 6.1) |

---

### 6.3 Story AD‑003 – 審計日誌（Audit Trail）  
- **As a** Compliance Officer  
- **I want** 查看所有管理操作的審計日誌  
- **So that** 可以確保符合規範  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 需追蹤使用者、操作時間、操作類型。 |
| **技術規格** | - `GET /api/admin/audit?resource=service`。<br>- 回傳 `{ auditId, adminId, action, resourceId, created_at }`。 |
| **資料模型** | `AuditLog` (id, admin_id, action, resource_type, resource_id, created_at)。 |
| **檔案位置** | `AuditController.java` in `backend/admin-service` |
| **關聯/依賴** | `AuditRepository`. |
| **測試要求** | - Auth 403/200。<br>- 日誌正確。 |
| **驗收條件（GWT）** | **Given** 管理員 token，**When** GET，**Then** 200 且包含最近 100 筆。 |
| **DoR** | - 合規需求已確定。 |
| **DoD** | - 單元覆蓋 80%+。<br>- PR merge。 |
| **PO 任務映射** | AD‑003 (任務 6.2) |

---

## 7️⃣ Epic E‑AD (Admin Dashboard)

### 7.1 Story AD‑004 – Admin Login（JWT + RBAC）  
- **As a** Admin  
- **I want** 用 JWT 登入管理後台  
- **So that** 只能看到自己權限內的頁面  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 使用 Keycloak 或自建 JWT。 |
| **技術規格** | - `/auth/admin/login`。<br>- JWT `ROLE_ADMIN`。 |
| **資料模型** | `Admin` (id, username, password_hash)。 |
| **檔案位置** | `AdminController.login()`. |
| **關聯/依賴** | `AdminRepository`. |
| **測試要求** | - Auth 401/200。 |
| **驗收條件（GWT）** | **Given** 正確憑證，**When** POST `/auth/admin/login`，**Then** 200 且 token。 |
| **DoR** | - Keycloak 設定完成。 |
| **DoD** | - 測試通過。 |
| **PO 任務映射** | AD‑004 (任務 6.1) |

---

### 7.2 Story AD‑005 – 前端 Admin Dashboard  
- **As a** Admin  
- **I want** 查看服務表、統計圖表、審計日誌  
- **So that** 能即時掌握業務數據  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 前端使用 `react‑admin` + `recharts`。 |
| **技術規格** | - `GET /api/admin/services`、`GET /api/admin/queues`、`GET /api/admin/audit`。 |
| **資料模型** | N/A |
| **檔案位置** | `frontend/src/admin/` |
| **關聯/依賴** | 依賴後端 API。 |
| **測試要求** | - Unit 測試每個頁面。<br>- E2E 測試。 |
| **驗收條件（GWT）** | **Given** 已授權 token，**When** 進入 /admin，**Then** 顯示服務列表與統計圖。 |
| **DoR** | - UI 設計稿完成。 |
| **DoD** | - 測試覆蓋 80%+。 |
| **PO 任務映射** | AD‑004 (任務 6.3) |

---

## 8️⃣ Epic E‑OP (Ops & Infrastructure)

### 8.1 Story OP‑01 – Helm Chart 構建  
- **As a** DevOps 工程師  
- **I want** 將每個微服務打包為 Helm Chart  
- **So that** CI/CD 能自動部署到 Kubernetes  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 需要支援多環境（dev, prod）、自動版本化。 |
| **技術規格** | - Chart `values.yaml` 包含 `image.tag`, `replicaCount`, `env`. <br>- `helm lint`, `helm template`。 |
| **檔案位置** | `infra/helm/<service>/Chart.yaml`、`templates/deployment.yaml` |
| **關聯/依賴** | Dockerfile 於 `./build`. |
| **測試要求** | - `helm template` 成功。 |
| **驗收條件（GWT）** | **Given** Chart 完成，**When** `helm install`，**Then** Pod 正常啟動。 |
| **DoR** | - Dockerfile 已可構建。 |
| **DoD** | - Helm lint 通過。<br>- Helm template 通过。 |
| **PO 任務映射** | OP‑01 (任務 7.1) |

---

### 8.2 Story OP‑02 – GitHub Actions CI/CD  
- **As a** CI/CD 工程師  
- **I want** 在 Push `develop` 時自動執行單元、整合、Docker Build、Helm Deploy  
- **So that** 我們能快速回饋功能變更  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 必須同時支援後端與前端。 |
| **技術規格** | - `.github/workflows/ci-cd.yml`。<br>- Jobs: `build-backend`, `test-backend`, `build-frontend`, `docker-build`, `helm-deploy`。 |
| **檔案位置** | `.github/workflows/ci-cd.yml` |
| **關聯/依賴** | 上述所有微服務。 |
| **測試要求** | - Workflow 通过。 |
| **驗收條件（GWT）** | **Given** 有 PR merge 至 `develop`，**When** CI run，**Then** 所有 job 完成並推送 Docker image。 |
| **DoR** | - Workflow YAML 已撰寫。 |
| **DoD** | - Workflow CI 通过。 |
| **PO 任務映射** | OP‑02 (任務 7.2) |

---

### 8.3 Story OP‑03 – 監控 & 日誌（Prometheus / Grafana / Loki）  
- **As a** Sys‑Ops  
- **I want** 監控每個微服務的健康狀態、CPU/Memory、HTTP latency、日誌聚合  
- **So that** 我可以即時發現問題並排查  

| 項目 | 內容 |
|------|------|
| **背景與範圍** | 必須支援多 namespace。 |
| **技術規格** | - Prometheus scrape `/actuator/prometheus`。<br>- Grafana Dashboard：CPU, Memory, HTTP latency。<br>- Loki 與 Fluent‑Bit 收集 Pod 日誌。 |
| **檔案位置** | `infra/monitoring/`（Helm chart for Prometheus/Grafana/Loki）。 |
| **關聯/依賴** | 微服務需導出 `PrometheusMeterRegistry`。 |
| **測試要求** | - 集成測試：metrics endpoint。 |
| **驗收條件（GWT）** | **Given** 系統啟動，**When** 訪問 `/actuator/prometheus`，**Then** 返回 metrics。 |
| **DoR** | - Helm chart 已構建。 |
| **DoD** | - Grafana dashboard 可視化。 |
| **PO 任務映射** | OP‑03 (任務 7.3) |

---

## 9️⃣ 整體交付流程

| 步驟 | 目的 | 參與角色 |
|------|------|-----------|
| 1. **需求確定** | 所有 Story 必須在 JIRA / Confluence 有完整需求、畫圖、API 文檔 | PO、Business Analyst |
| 2. **設計審查** | 需求、接口、資料模型、測試計畫 | Lead Engineer |
| 3. **實作** | 編碼、單元測試、Review | 開發人員 |
| 4. **CI** | `mvn -B test`, `npm run test`, `docker build` | CI Bot |
| 5. **交付測試** | E2E / Integration / Acceptance | QA、QA Lead |
| 6. **部署** | 佈署至 `staging`/`prod` | Ops |
| 7. **發布** | 文檔更新、版本號、Slack/Teams 通知 | Release Manager |

> **DoR** 只在「需求 + 接口 + 環境」完全確定後才可拉取 Sprint Backlog。  
> **DoD** 需包含：代碼合併、測試通過、CI 通過、部署檔案推送、文檔同步。  

---

## 10️⃣ 小結  

| Epic | Story 數量 | 交付物 | 里程碑 |
|------|------------|--------|--------|
| E‑CM | 5 | `/api/customers/...`, `/api/queue/take`, `/api/queue/next`, `/ws/queue` | `v1.0.0` |
| E‑QS | 3 | QueueItem CRUD, WebSocket, 叫號 | `v1.0.0` |
| E‑NT | 2 | FCM/APNs, WebSocket | `v1.0.0` |
| E‑OT | 2 | OTP 生成/驗證 | `v1.0.0` |
| E‑AD | 3 | Admin CRUD, 監控, 審計 | `v1.0.0` |
| E‑OP | 3 | Helm, CI/CD, 監控 | `v1.0.0` |

> 以上構成 **六大業務能力** 的完整交付框架。  
> 每個 Story 都可在獨立 Sprint（或 Kanban 列）中完成，且都有明確的 **DoR / DoD**、**檔案位置**、**資料模型**、**驗收條件**，讓 **PO**、**Dev**、**QA**、**Ops** 之間能以文件、API spec、CI pipeline 為契約，確保「開發到交付」無痛滑動。  

祝你開發順利，產品一路向前 🚀