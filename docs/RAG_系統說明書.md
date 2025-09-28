# 混合型增強RAG系統說明書

## 目錄
- [1. 系統概述](#1-系統概述)
- [2. 系統架構](#2-系統架構)
- [3. 核心組件](#3-核心組件)
- [4. 檢索策略](#4-檢索策略)
- [5. 文檔處理](#5-文檔處理)
- [6. 配置參數](#6-配置參數)
- [7. API使用說明](#7-api使用說明)
- [8. 性能優化](#8-性能優化)
- [9. 評估指標](#9-評估指標)
- [10. 故障排除](#10-故障排除)

---

## 1. 系統概述

### 1.1 什麼是RAG？
RAG（Retrieval-Augmented Generation，檢索增強生成）是一種結合了檢索系統和生成式AI的技術，通過以下步驟工作：

1. **檢索階段**：從知識庫中找出與用戶問題相關的文檔片段
2. **增強階段**：將檢索到的內容作為上下文提供給語言模型
3. **生成階段**：語言模型基於檢索到的上下文生成準確的回答

### 1.2 系統特色

本系統實現了**混合型增強RAG（HybridContextualRAG）**，具有以下特色：

- **混合檢索**：結合向量檢索（FAISS）和關鍵詞檢索（BM25）
- **智能重排序**：使用Cross-Encoder模型重新排序檢索結果
- **中文優化**：針對繁體中文進行特殊優化
- **自動索引重建**：支持定期自動重建索引
- **多格式支持**：支持TXT、PDF、DOCX格式文檔
- **對話記憶**：維護對話上下文以提供更好的連續對話體驗

### 1.3 技術優勢

- **高精度檢索**：混合檢索策略提供更全面的文檔匹配
- **語義理解**：向量檢索捕捉語義相似性
- **精確匹配**：BM25檢索處理關鍵詞精確匹配
- **可擴展性**：支持大規模文檔庫
- **實時性**：支持實時文檔添加和檢索

---

## 2. 系統架構

### 2.1 整體架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                    HybridContextualRAG                     │
├─────────────────────────────────────────────────────────────┤
│                      文檔處理層                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  TXT處理    │  │  PDF處理    │  │  DOCX處理   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                         │                                   │
│                    文檔分塊器                                │
│              (RecursiveCharacterTextSplitter)               │
├─────────────────────────────────────────────────────────────┤
│                      檢索層                                  │
│  ┌─────────────────┐              ┌─────────────────┐       │
│  │   向量檢索      │              │   BM25檢索      │       │
│  │  (FAISS Index)  │              │ (Whoosh Index)  │       │
│  │                 │              │                 │       │
│  │ • IndexFlatIP   │              │ • 中文分詞支持  │       │
│  │ • 384維向量     │              │ • BM25F評分     │       │
│  │ • 內積相似度    │              │ • 精確匹配      │       │
│  └─────────────────┘              └─────────────────┘       │
│                         │                                   │
│                    混合融合策略                              │
│              (可配置權重 α = 0.7)                           │
├─────────────────────────────────────────────────────────────┤
│                      重排序層                                │
│                 Cross-Encoder重排序                         │
│           (ms-marco-MiniLM-L-6-v2)                         │
├─────────────────────────────────────────────────────────────┤
│                      生成層                                  │
│                   LLM API調用                               │
│              (支持Ollama格式)                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心模塊說明

#### 2.2.1 文檔處理模塊
- **功能**：處理多種格式文檔，進行清理和分塊
- **編碼支持**：UTF-8、GBK、Big5自動檢測
- **分塊策略**：基於中文標點符號的智能分塊

#### 2.2.2 向量檢索模塊
- **嵌入模型**：paraphrase-multilingual-MiniLM-L12-v2
- **索引類型**：FAISS IndexFlatIP（內積相似度）
- **維度**：384維向量空間

#### 2.2.3 BM25檢索模塊
- **分詞器**：Jieba中文分詞（如可用）
- **評分方式**：BM25F演算法
- **索引引擎**：Whoosh全文檢索引擎

#### 2.2.4 重排序模塊
- **模型**：Cross-Encoder ms-marco-MiniLM-L-6-v2
- **功能**：對檢索候選進行二次精準排序
- **權重配置**：可調整重排序權重（預設0.8）

---

## 3. 核心組件

### 3.1 HybridContextualRAG類

主要的RAG系統實現類，包含以下核心方法：

#### 3.1.1 初始化方法
```python
def __init__(self)
```
- 載入嵌入模型和重排序模型
- 初始化FAISS和BM25索引
- 設置配置參數
- 載入已存在的索引文件

#### 3.1.2 文檔添加方法
```python
async def add_documents(self, documents: List[Document]) -> int
```
- 對文檔進行分塊處理
- 生成向量嵌入
- 同時更新FAISS和BM25索引
- 持久化保存索引

#### 3.1.3 檢索方法

##### 向量檢索
```python
def vector_search(self, query: str, top_k: int = None, apply_threshold: bool = True) -> List[Tuple[Document, float]]
```

##### BM25檢索
```python
def bm25_search(self, query: str, top_k: int = None) -> List[Tuple[Document, float]]
```

##### 混合檢索
```python
def hybrid_search(self, query: str, alpha: float = None) -> List[Tuple[Document, float]]
```

##### 智能檢索
```python
def smart_search(self, query: str) -> List[Tuple[Document, float]]
```

#### 3.1.4 生成回答方法
```python
async def generate_response(self, query: str, conversation_id: Optional[int] = None) -> Dict[str, Any]
```

### 3.2 文檔分塊器

#### 3.2.1 分塊策略
使用`RecursiveCharacterTextSplitter`，優化中文分塊：

```python
separators = [
    "\n\n", "。", "！", "？", "；", "：", "，", 
    ", ", ". ", "! ", "? ", "\n", "。\n", 
    "；\n", "，\n", "。 ", "； ", "， ", " ", ""
]
```

#### 3.2.2 分塊參數
- **chunk_size**：預設300字符
- **chunk_overlap**：預設100字符重疊
- **length_function**：使用`len()`計算長度

### 3.3 向量嵌入模型

#### 3.3.1 模型選擇
- **模型名稱**：paraphrase-multilingual-MiniLM-L12-v2
- **特點**：多語言支持，對中文友好
- **向量維度**：384維
- **模型大小**：相對輕量，推理速度快

#### 3.3.2 正規化處理
所有向量都經過L2正規化處理，確保使用內積相似度時的一致性。

---

## 4. 檢索策略

### 4.1 智能檢索策略選擇

系統根據查詢特徵自動選擇最適合的檢索策略：

#### 4.1.1 BM25檢索（關鍵詞檢索）
**適用場景**：
- 查詢包含引號（精確匹配需求）
- 查詢包含"exactly"、"precisely"、"具體"、"確切"等詞
- 需要精確術語匹配的查詢

**特點**：
- 基於詞彙匹配
- 適合處理專業術語查詢
- 對拼字和關鍵詞敏感

#### 4.1.2 向量檢索（語義檢索）
**適用場景**：
- 包含中文且非精確匹配查詢
- 語義理解需求較高的查詢
- 概念性問題

**特點**：
- 基於語義相似度
- 能理解同義詞和相關概念
- 對拼字錯誤有一定容忍度

#### 4.1.3 混合檢索
**適用場景**：
- 包含FAQ關鍵詞的短查詢
- 平衡語義和關鍵詞需求的查詢
- 預設策略

**特點**：
- 結合兩種檢索方式的優點
- 可調整權重平衡（α參數）
- 提供最全面的檢索覆蓋

### 4.2 混合檢索融合算法

#### 4.2.1 分數正規化
```python
def _normalize_scores(self, scores: List[float], method: str = "max") -> List[float]
```

支持兩種正規化方法：
- **max正規化**：除以最大分數
- **softmax正規化**：使用softmax函數

#### 4.2.2 分數融合公式
```
混合分數 = α × 正規化向量分數 + (1-α) × 正規化BM25分數
```
其中α預設為0.7，可通過環境變數`HYBRID_ALPHA`調整。

### 4.3 Cross-Encoder重排序

#### 4.3.1 重排序流程
1. 從混合檢索獲得候選文檔
2. 使用Cross-Encoder對查詢-文檔對評分
3. 結合原始檢索分數和Cross-Encoder分數
4. 重新排序並篩選最終結果

#### 4.3.2 分數融合
```
最終分數 = rerank_weight × 正規化Cross-Encoder分數 + (1-rerank_weight) × 正規化原始分數
```
其中`rerank_weight`預設為0.8。

---

## 5. 文檔處理

### 5.1 支持格式

#### 5.1.1 TXT文件
- **編碼檢測**：自動檢測UTF-8、GBK、Big5編碼
- **預處理**：移除多餘空白字符
- **分塊**：按照中文標點符號分塊

#### 5.1.2 PDF文件
- **解析引擎**：PyPDF2
- **頁面提取**：逐頁提取文本內容
- **格式清理**：處理PDF特有的格式問題

#### 5.1.3 DOCX文件
- **解析引擎**：python-docx
- **段落提取**：提取段落和表格內容
- **格式保留**：保留基本的文檔結構

### 5.2 文檔元數據

每個文檔塊包含以下元數據：
```python
{
    "chunk_id": "文檔名_塊索引",
    "chunk_index": 塊索引,
    "original_doc_id": 原始文檔ID,
    "source": "文檔來源",
    "added_timestamp": "添加時間戳",
    "preserve_whole": False  # 是否保留整個文檔不分塊
}
```

### 5.3 特殊處理選項

#### 5.3.1 保留完整文檔
通過設置`preserve_whole=True`元數據，可以跳過分塊處理：
```python
document.metadata["preserve_whole"] = True
```

#### 5.3.2 領域詞彙優化
系統預置了HR領域的專業詞彙，提升中文分詞準確度：
```python
domain_words = [
    "補休", "到期", "遞延", "產檢", "育嬰留停", 
    "免刷卡", "時刻維護", "集體異動", "調班",
    # ... 更多詞彙
]
```

---

## 6. 配置參數

### 6.1 環境變數配置

在`.env`文件中設置以下參數：

#### 6.1.1 必需參數
```env
# LLM配置
MODEL_NAME=llama3.1:8b              # 語言模型名稱
LLM_API_BASE=http://your-llm-host:port # API基礎URL，請以實際部署位址或環境變數設定為準

# 嵌入模型（可選）
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
```

#### 6.1.2 檢索參數
```env
# 相似度閾值
SIMILARITY_THRESHOLD=0.25

# 檢索數量配置
TOP_K=50                    # 初始檢索候選數
RERANK_TOP_K=80            # 重排序前候選數
FINAL_K=10                 # 最終返回文檔數

# 混合檢索權重
HYBRID_ALPHA=0.7           # 向量檢索權重
RERANK_WEIGHT=0.8          # 重排序權重
FINAL_THRESHOLD=0.1        # 最終分數閾值

# 分數正規化方法
NORMALIZATION=max          # max 或 softmax
```

#### 6.1.3 分塊參數
```env
# 文檔分塊配置
CHUNK_SIZE=300             # 分塊大小（字符）
CHUNK_OVERLAP=100          # 分塊重疊（字符）
```

#### 6.1.4 索引管理
```env
# 自動重建索引
REINDEX_HOURS=24           # 重建索引間隔（小時）
ENABLE_AUTO_REINDEX=0      # 啟用自動重建（1啟用，0禁用）
```

### 6.2 預設值說明

| 參數 | 預設值 | 說明 |
|------|--------|------|
| SIMILARITY_THRESHOLD | 0.25 | 向量相似度閾值 |
| TOP_K | 50 | 初始檢索數量 |
| RERANK_TOP_K | 80 | 重排序候選數 |
| FINAL_K | 10 | 最終返回數量 |
| HYBRID_ALPHA | 0.7 | 向量檢索權重 |
| RERANK_WEIGHT | 0.8 | 重排序權重 |
| CHUNK_SIZE | 300 | 分塊大小 |
| CHUNK_OVERLAP | 100 | 分塊重疊 |

---

## 7. API使用說明

### 7.1 核心API方法

#### 7.1.1 添加文檔
```python
# 添加文檔到知識庫
documents = [Document(page_content="文檔內容", metadata={"source": "文檔名"})]
chunks_added = await rag.add_documents(documents)
```

#### 7.1.2 生成回答
```python
# 生成基於知識庫的回答
response = await rag.generate_response(
    query="用戶問題",
    conversation_id=123  # 可選，用於對話上下文
)
```

響應格式：
```python
{
    "answer": "生成的回答",
    "context_used": 5,  # 使用的上下文文檔數
    "sources": ["文檔1", "文檔2"],  # 來源文檔
    "sources_detail": [  # 詳細來源信息
        {
            "source": "文檔名",
            "chunk": 0,
            "score": 0.8542,
            "snippet": "文檔片段..."
        }
    ],
    "retrieval_time": 0.15,  # 檢索耗時
    "generation_time": 1.23,  # 生成耗時
    "total_time": 1.38,      # 總耗時
    "retrieval_strategy": "hybrid"  # 使用的檢索策略
}
```

#### 7.1.3 檢索文檔
```python
# 純檢索，不生成回答
results = rag.smart_search("查詢問題")
for doc, score in results:
    print(f"分數: {score}, 來源: {doc.metadata['source']}")
```

#### 7.1.4 文檔管理
```python
# 刪除文檔
rag.remove_document_by_id(document_id=123)

# 清空所有文檔
rag.clear_vector_store()

# 強制重建索引
rag.force_reindex()
```

### 7.2 統計信息API

#### 7.2.1 獲取系統統計
```python
stats = rag.get_statistics()
```

返回信息：
```python
{
    "total_documents": 1250,
    "total_conversations": 45,
    "total_vectors": 1250,
    "embedding_dimension": 384,
    "bm25_status": "Available",
    "reranker_status": "Available",
    "similarity_threshold": 0.25,
    "chunk_size": 300,
    "chunk_overlap": 100,
    "last_reindex": "2023-12-01T10:30:00"
}
```

#### 7.2.2 獲取向量庫信息
```python
info = rag.get_vector_store_info()
```

### 7.3 評估API

#### 7.3.1 檢索評估
```python
# 評估檢索性能
test_queries = ["問題1", "問題2"]
gold_doc_ids = [[1, 3], [2, 5]]  # 相關文檔ID

metrics = rag.evaluate_retrieval(test_queries, gold_doc_ids)
```

#### 7.3.2 自動調優
```python
# 自動調優混合檢索權重
best_config = rag.auto_tune_alpha(test_queries, gold_doc_ids)
print(f"最佳alpha: {best_config['alpha']}")
```

---

## 8. 性能優化

### 8.1 檢索性能優化

#### 8.1.1 索引優化
- **FAISS索引**：使用IndexFlatIP實現精確檢索
- **BM25索引**：使用Whoosh實現高效全文檢索
- **索引壓縮**：向量L2正規化減少存儲空間

#### 8.1.2 批量處理
- **批量嵌入**：一次處理多個文檔的向量化
- **異步寫入**：使用AsyncWriter進行BM25索引更新
- **文件鎖**：防止多進程同時寫入衝突

#### 8.1.3 內存管理
- **惰性載入**：僅在需要時載入大型模型
- **分塊處理**：大文檔分塊處理避免內存溢出
- **垃圾回收**：及時釋放不用的資源

### 8.2 查詢優化

#### 8.2.1 智能策略選擇
根據查詢特徵自動選擇最優檢索策略，避免不必要的計算。

#### 8.2.2 閾值過濾
通過相似度閾值過濾低質量結果，減少後續處理負擔。

#### 8.2.3 早期停止
在重排序階段，若候選文檔數量不足，跳過複雜的重排序計算。

### 8.3 存儲優化

#### 8.3.1 索引持久化
- **增量更新**：支持增量添加文檔而無需重建整個索引
- **檢查點**：定期保存索引檢查點
- **壓縮存儲**：使用pickle序列化減少文件大小

#### 8.3.2 文件管理
- **目錄結構**：合理的目錄結構便於管理
- **臨時文件**：及時清理臨時文件
- **備份恢復**：支持索引備份和恢復

---

## 9. 評估指標

### 9.1 檢索評估指標

#### 9.1.1 Recall@K（召回率）
衡量在前K個結果中包含相關文檔的比例：
```
Recall@K = |檢索到的相關文檔| / |所有相關文檔|
```

#### 9.1.2 Precision@K（精確率）
衡量前K個結果中相關文檔的比例：
```
Precision@K = |檢索到的相關文檔| / K
```

#### 9.1.3 MRR（平均倒數排名）
衡量第一個相關文檔的排名：
```
MRR = 1/N × Σ(1/rank_i)
```

### 9.2 生成評估指標

#### 9.2.1 回答質量
- **相關性**：回答與問題的相關程度
- **準確性**：回答內容的事實準確性
- **完整性**：回答是否完整覆蓋問題要點

#### 9.2.2 來源可追溯性
- **來源標註**：是否正確標註信息來源
- **引用準確性**：引用內容是否準確
- **來源多樣性**：是否使用多個來源的信息

### 9.3 性能指標

#### 9.3.1 響應時間
- **檢索時間**：從查詢到檢索完成的時間
- **生成時間**：LLM生成回答的時間
- **總處理時間**：端到端處理時間

#### 9.3.2 資源使用
- **內存使用**：系統內存佔用
- **CPU使用**：處理器使用率
- **存儲空間**：索引文件大小

---

## 10. 故障排除

### 10.1 常見問題

#### 10.1.1 模型載入失敗
**錯誤信息**：
```
Failed to load cross-encoder model
```

**解決方案**：
1. 檢查網絡連接
2. 確認模型名稱正確
3. 檢查磁盤空間是否充足
4. 清除模型緩存後重試

#### 10.1.2 索引文件損壞
**錯誤信息**：
```
Error loading indices
```

**解決方案**：
1. 刪除損壞的索引文件
2. 重新建立索引：
```python
rag.clear_vector_store()
# 重新添加文檔
await rag.add_documents(documents)
```

#### 10.1.3 BM25檢索失敗
**錯誤信息**：
```
BM25 search failed
```

**解決方案**：
1. 檢查Whoosh索引完整性
2. 重建BM25索引：
```python
rag._rebuild_bm25_index()
```

#### 10.1.4 LLM API連接失敗
**錯誤信息**：
```
Failed to connect to LLM API
```

**解決方案**：
1. 檢查`LLM_API_BASE`設置
2. 確認LLM服務正在運行
3. 檢查網絡連接和防火牆設置

### 10.2 性能問題

#### 10.2.1 檢索速度慢
**可能原因**：
- 文檔數量過多
- 向量維度過高
- 硬件資源不足

**優化方案**：
1. 調整`TOP_K`和`RERANK_TOP_K`參數
2. 使用更小的嵌入模型
3. 增加硬件資源
4. 實施分塊檢索策略

#### 10.2.2 內存使用過高
**可能原因**：
- 一次載入過多文檔
- 模型緩存過大
- 內存洩漏

**解決方案**：
1. 分批處理大量文檔
2. 定期清理緩存
3. 重啟系統釋放內存

#### 10.2.3 響應時間過長
**可能原因**：
- LLM模型過大
- 上下文長度過長
- 網絡延遲

**優化方案**：
1. 使用更小的LLM模型
2. 限制上下文長度
3. 使用本地LLM服務

### 10.3 調試工具

#### 10.3.1 日誌系統
系統提供詳細的日誌信息，可通過以下方式啟用詳細日誌：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 10.3.2 性能監控
使用內建的性能監控功能：
```python
response = await rag.generate_response(query)
print(f"檢索時間: {response['retrieval_time']}")
print(f"生成時間: {response['generation_time']}")
print(f"使用策略: {response['retrieval_strategy']}")
```

#### 10.3.3 檢索調試
查看檢索過程的詳細信息：
```python
# 查看檢索策略和結果
results = rag.smart_search(query)
for i, (doc, score) in enumerate(results[:5]):
    print(f"結果{i+1}: {score:.4f} - {doc.metadata['source']}")
```

---

## 附錄

### A. 環境變數完整列表

```env
# 必需參數
MODEL_NAME=llama3.1:8b
LLM_API_BASE=http://your-llm-host:port

# 模型配置
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# 檢索參數
SIMILARITY_THRESHOLD=0.25
TOP_K=50
RERANK_TOP_K=80
FINAL_K=10
HYBRID_ALPHA=0.7
RERANK_WEIGHT=0.8
FINAL_THRESHOLD=0.1
NORMALIZATION=max

# 文檔處理
CHUNK_SIZE=300
CHUNK_OVERLAP=100

# 索引管理
REINDEX_HOURS=24
ENABLE_AUTO_REINDEX=0
```

### B. 系統要求

#### B.1 硬件要求
- **內存**：最低8GB，推薦16GB以上
- **存儲**：至少10GB可用空間
- **CPU**：多核心處理器，支持AVX指令集

#### B.2 軟件要求
- **Python**：3.8或以上版本
- **操作系統**：Windows 10/11、Linux、macOS
- **依賴庫**：見requirements.txt

### C. 參考資料

1. [FAISS官方文檔](https://faiss.ai/)
2. [Whoosh檢索引擎](https://whoosh.readthedocs.io/)
3. [Sentence Transformers](https://www.sbert.net/)
4. [LangChain文檔分割器](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
5. [BM25演算法](https://en.wikipedia.org/wiki/Okapi_BM25)

---

*文檔版本：v1.0*  
*最後更新：2024年12月*  
*維護者：RAG系統開發團隊*
