# ADR-0001: 增強型混合 RAG 檢索架構與雙 Token 安全防護決策

[繁體中文](0001-hybrid-rag-and-security.md) | [English](0001-hybrid-rag-and-security_en.md)

## 狀態

已通過 (Accepted) - 2026-08-01

---

## 背景與問題陳述

AskMiao 作為智慧對話與多 Agent 協作系統，在知識庫檢索與安全認證方面面臨兩大核心挑戰：

1. **單一檢索機制的限制**：
   - 純向量搜尋（Dense Retrieval）擅長捕捉語意相似度，但在處理專業術語、專有名詞、型號或精確關鍵字比對時容易遺漏或產生幻覺。
   - 純關鍵字搜尋（Sparse Retrieval，如 BM25）精準比對能力強，但缺乏語意理解與同義詞擴展能力。
2. **認證安全性與敏感資料洩漏防範**：
   - 單一長壽命 JWT Token 若遭側錄會有永久風險；而純 Session 機制在分散式與非同步 API 架構下擴充性較差。
   - 系統運作產生的日誌容易在無意間記錄使用者密碼與 API 金鑰，導致 CodeQL 安全檢測警報。

---

## 架構決策內容

經團隊評估後，決定採用以下架構技術方案：

### 1. 增強型混合 RAG 管道 (Hybrid RAG Pipeline)

- 結合 **FAISS 向量檢索**（使用 `BAAI/bge-small-zh-v1.5` 模型）與 **Whoosh BM25 關鍵字檢索**（配合 `Jieba` 分詞）。
- 採用分數歸一化融合演算法，並引入 **Cross-Encoder 模型 (`bge-reranker-base`)** 進行 Top-K 文本片段重排序。

### 2. RSA-2048 雙 Token 認證與 Redis 黑名單

- **Access Token**：使用 RSA-2048 私鑰簽署，有效期限設定為 30 分鐘，經由 HTTP Header 傳輸。
- **Refresh Token**：設定為 HttpOnly / Secure / SameSite 之 Cookie，有效期限為 7 天。
- **即時撤銷機制**：登出時將 Access Token 之 JTI 寫入 Redis 黑名單，有效防範權限殘留。

### 3. 雙層敏感資料遞迴脫敏機制 (`security_logging.py`)

- 實現物件層級 `sanitize_sensitive_data` 遞迴替換機制。
- 在日誌輸出與 JSON 序列化前進行正則表達式二次遮罩，將所有敏感欄位統一轉換為 `[REDACTED]`。

---

## 決定產生的影響與權衡

### 正面影響 (Benefits)

- **檢索精準度顯著提升**：混合檢索重排序大幅降低了幻覺問題，對於中文領域名詞與精確單字檢索成功率大幅提高。
- **安全性顯著增強**：無感刷新機制兼顧了使用者體驗與短壽命 Token 安全性；雙層脫敏徹底解除日誌資料洩漏隱患並通過 CodeQL 安全評估。

### 負面影響與挑戰 (Trade-offs & Risks)

- **系統複雜度增加**：後端需同時維護 FAISS 向量索引檔案與 Whoosh 關鍵字索引。
- **算力與延遲開銷**：Cross-Encoder 重排序步驟增加了數十毫秒的回應延遲，需透過 Redis 快取熱門查詢進行最佳化。