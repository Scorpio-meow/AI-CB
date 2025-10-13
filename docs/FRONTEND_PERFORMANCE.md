"""
前端效能優化建議

這個文件包含了前端組件的效能優化最佳實踐
"""

# ============================================
# React 組件效能優化指南
# ============================================

## 1. 使用 React.memo 避免不必要的重渲染

```javascript
// Before
function MessageItem({ message }) {
  return <div>{message.content}</div>;
}

// After
const MessageItem = React.memo(function MessageItem({ message }) {
  return <div>{message.content}</div>;
});
```

## 2. 使用 useMemo 和 useCallback 優化計算和回調

```javascript
import React, { useMemo, useCallback } from 'react';

function ChatList({ messages, onMessageClick }) {
  // 優化昂貴計算
  const sortedMessages = useMemo(() => {
    return messages.sort((a, b) => b.created_at - a.created_at);
  }, [messages]);
  
  // 優化回調函數
  const handleClick = useCallback((id) => {
    onMessageClick(id);
  }, [onMessageClick]);
  
  return (
    <div>
      {sortedMessages.map(msg => (
        <MessageItem key={msg.id} message={msg} onClick={handleClick} />
      ))}
    </div>
  );
}
```

## 3. 虛擬滾動 - 處理大列表

```javascript
import { FixedSizeList } from 'react-window';

function VirtualMessageList({ messages }) {
  const Row = ({ index, style }) => (
    <div style={style}>
      <MessageItem message={messages[index]} />
    </div>
  );
  
  return (
    <FixedSizeList
      height={600}
      itemCount={messages.length}
      itemSize={80}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
}

// 安裝: npm install react-window
```

## 4. 延遲載入和程式碼分割

```javascript
import React, { lazy, Suspense } from 'react';

// 延遲載入大型組件
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const Documents = lazy(() => import('./pages/Documents'));

function App() {
  return (
    <Suspense fallback={<CircularProgress />}>
      <Routes>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/documents" element={<Documents />} />
      </Routes>
    </Suspense>
  );
}
```

## 5. 防抖和節流

```javascript
import { debounce } from 'lodash';

function SearchBox() {
  const [query, setQuery] = useState('');
  
  // 防抖搜尋，避免每次按鍵都發送請求
  const debouncedSearch = useMemo(
    () => debounce(async (searchTerm) => {
      const results = await api.get(`/search?q=${searchTerm}`);
      setResults(results.data);
    }, 300),
    []
  );
  
  const handleChange = (e) => {
    const value = e.target.value;
    setQuery(value);
    debouncedSearch(value);
  };
  
  return <input value={query} onChange={handleChange} />;
}
```

## 6. 優化圖片載入

```javascript
function OptimizedImage({ src, alt }) {
  return (
    <img 
      src={src} 
      alt={alt}
      loading="lazy"  // 瀏覽器原生懶載入
      decoding="async"  // 異步解碼
    />
  );
}
```

## 7. 減少 API 請求 - 合併狀態更新

```javascript
// Before - 多次 setState 觸發多次渲染
setUsers(usersData);
setDocuments(docsData);
setStatistics(statsData);

// After - 使用 useReducer 或合併更新
const [state, dispatch] = useReducer(reducer, initialState);

dispatch({
  type: 'SET_ALL_DATA',
  payload: { users, documents, statistics }
});
```

## 8. Service Worker 和離線支援

```javascript
// src/serviceWorkerRegistration.js
export function register() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js')
        .then(registration => {
          console.log('SW registered:', registration);
        })
        .catch(error => {
          console.log('SW registration failed:', error);
        });
    });
  }
}
```

## 9. Web Workers 處理重計算

```javascript
// worker.js
self.addEventListener('message', (e) => {
  const { data, type } = e.data;
  
  if (type === 'PROCESS_LARGE_DATA') {
    const result = processLargeData(data);
    self.postMessage({ result });
  }
});

// Component
const worker = new Worker('worker.js');

useEffect(() => {
  worker.postMessage({ type: 'PROCESS_LARGE_DATA', data: largeData });
  
  worker.addEventListener('message', (e) => {
    setProcessedData(e.data.result);
  });
}, [largeData]);
```

## 10. 批次 DOM 更新

```javascript
import { unstable_batchedUpdates } from 'react-dom';

function handleMultipleUpdates() {
  unstable_batchedUpdates(() => {
    setCount(count + 1);
    setFlag(true);
    setName('New Name');
  });
}
```

---

# 具體實施建議

## Documents.js 優化

```javascript
// 1. 添加虛擬滾動
import { FixedSizeList } from 'react-window';

// 2. 使用 React.memo 優化列表項
const DocumentItem = React.memo(({ document, onDelete }) => {
  return (
    <ListItem>
      <ListItemText primary={document.filename} />
      <IconButton onClick={() => onDelete(document.id)}>
        <DeleteIcon />
      </IconButton>
    </ListItem>
  );
});

// 3. 優化刪除操作 - 批次更新
const handleBulkDelete = useCallback(async (ids) => {
  try {
    await api.post('/documents/bulk_delete', { ids });
    
    // 批次更新狀態
    setDocuments(prev => prev.filter(doc => !ids.includes(doc.id)));
  } catch (error) {
    setError(error.message);
  }
}, []);
```

## AdminDashboard.js 優化

```javascript
// 1. 使用 SWR 或 React Query 管理快取
import useSWR from 'swr';

function AdminDashboard() {
  const { data: statistics, error } = useSWR(
    '/api/admin/statistics',
    fetcher,
    { refreshInterval: 180000 } // 3 分鐘自動刷新
  );
  
  // 不需要手動管理快取和載入狀態
}

// 安裝: npm install swr
```

## Chat.js 優化

```javascript
// 1. 使用 IntersectionObserver 實現無限滾動
const loadMoreRef = useRef();

useEffect(() => {
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && hasMore) {
        loadMoreMessages();
      }
    },
    { threshold: 0.1 }
  );
  
  if (loadMoreRef.current) {
    observer.observe(loadMoreRef.current);
  }
  
  return () => observer.disconnect();
}, [hasMore]);

// 2. 優化消息發送 - 樂觀更新
const sendMessage = async (content) => {
  const tempMessage = {
    id: `temp-${Date.now()}`,
    content,
    is_user: true,
    created_at: new Date().toISOString()
  };
  
  // 立即顯示訊息
  setMessages(prev => [...prev, tempMessage]);
  
  try {
    const response = await api.post('/chat/send', { content });
    // 替換臨時訊息
    setMessages(prev => 
      prev.map(m => m.id === tempMessage.id ? response.data : m)
    );
  } catch (error) {
    // 移除失敗的訊息
    setMessages(prev => prev.filter(m => m.id !== tempMessage.id));
    setError(error.message);
  }
};
```

---

# 效能監控

## 使用 React DevTools Profiler

```javascript
import { Profiler } from 'react';

function onRenderCallback(
  id, // 組件的 "id"
  phase, // "mount" 或 "update"
  actualDuration, // 本次更新花費的時間
  baseDuration, // 理想情況下的渲染時間
  startTime, // React 開始渲染的時間
  commitTime, // React 提交更新的時間
) {
  console.log(`${id} (${phase}) took ${actualDuration}ms`);
}

function App() {
  return (
    <Profiler id="App" onRender={onRenderCallback}>
      <MainContent />
    </Profiler>
  );
}
```

## 使用 Web Vitals 監控

```javascript
// src/reportWebVitals.js
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

function sendToAnalytics({ name, value, id }) {
  console.log({ name, value, id });
  // 發送到分析服務
}

getCLS(sendToAnalytics);
getFID(sendToAnalytics);
getFCP(sendToAnalytics);
getLCP(sendToAnalytics);
getTTFB(sendToAnalytics);

// 安裝: npm install web-vitals
```

---

# 優先順序建議

## 高優先級 (立即實施)
1. ✅ 記憶體快取 (已實施)
2. ⭐ React.memo 優化常用組件
3. ⭐ 防抖搜尋和輸入

## 中優先級 (1-2週)
4. 虛擬滾動 (Documents 和 AdminDashboard)
5. 程式碼分割和懶載入
6. 使用 SWR/React Query 管理狀態

## 低優先級 (按需實施)
7. Web Workers (處理大量數據時)
8. Service Worker (PWA 功能)
9. 圖片優化

---

**文件版本**: 1.0  
**建立日期**: 2025年10月13日  
**適用範圍**: React 前端應用
