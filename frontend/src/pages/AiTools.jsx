import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { chatService, apiToolService, mcpService } from '../services/api';
import { Button, Icon, Spinner, Switch, Snackbar } from '../components/ui';
import styles from './AiTools.module.css';
const DEFAULT_TOOLS_METADATA = [
  {
    name: 'search_knowledge_base',
    displayName: '知識庫智能檢索',
    category: 'knowledge',
    categoryName: '內部知識庫',
    icon: 'search',
    summary: '基於 FAISS 向量語意與 BM25 關鍵字混合檢索演算法，深入內部專業文件庫進行高精度段落匹配與置信度評分。',
    executionMode: '自主調用 / Function Calling',
    priority: '內部專業提問第一優先級',
    triggerTiming: '當使用者詢問公司制度、專案架構、技術文件、內部貼文細節或特定檔案內容時自動觸發。',
    examples: [
      '請查詢知識庫中關於專案架構的相關文件',
      '知識庫中有提到系統的佈署流程與注意事項嗎？',
      '查詢關於 API 規格說明的檔案內容'
    ],
    parameters: [
      { name: 'query', type: 'string', required: true, desc: '要檢索的繁體中文、英文關鍵字、作者帳號或特定網址' },
      { name: 'target_document', type: 'string', required: false, desc: '可選：限定搜尋的特定文件檔案名稱（如特定 .md 或 .js 檔）' },
      { name: 'top_k', type: 'integer', required: false, desc: '返回的最相關片段數量（預設 3，最大 5）' }
    ]
  },
  {
    name: 'filter_and_count_records',
    displayName: '記錄精準統計與篩選',
    category: 'knowledge',
    categoryName: '內部知識庫',
    icon: 'analytics',
    summary: '針對知識庫中的結構化記錄、貼文與文檔進行條件過濾與計數（精確 count），支援精確發布時間、作者帳號與全文關鍵字篩選。',
    executionMode: '自主調用 / Function Calling',
    priority: '統計與清單查詢最高優先級',
    triggerTiming: '當使用者提問「總共有幾則」、「統計某年某月貼文數量」、「列出某作者的所有記錄」時強制調用。',
    examples: [
      '統計知識庫中 2026年8月 的全部貼文數量與內容',
      '查詢某作者的所有記錄總共有幾則？',
      '篩選包含特定關鍵字的結構化記錄清單'
    ],
    parameters: [
      { name: 'date_range', type: 'string', required: false, desc: '篩選發布日期或月份（如 2026-08、2026年8月、2025-10-22）' },
      { name: 'author', type: 'string', required: false, desc: '篩選特定作者帳號（如 @username）' },
      { name: 'keyword', type: 'string', required: false, desc: '篩選內容中包含的關鍵字' },
      { name: 'target_document', type: 'string', required: false, desc: '限定的文件名稱' },
      { name: 'limit', type: 'integer', required: false, desc: '返回清單筆數上限（預設 50，最大 200）' }
    ]
  },
  {
    name: 'web_search',
    displayName: '即時聯網搜尋',
    category: 'web',
    categoryName: '聯網與外部',
    icon: 'language',
    summary: '當內部知識庫未收錄相關資料時，調用外部搜尋引擎（優先使用官方 Search API，自動容錯切換 DuckDuckGo 備援）獲取最新即時公開資訊。',
    executionMode: '自主調用 / 備援引擎容錯',
    priority: '即時外部資訊優先',
    triggerTiming: '當詢問外部時事新聞、最新科技動態、或內部知識庫無收錄的外部公開資訊時自動調用。',
    examples: [
      '搜尋目前最新的 AI 技術發展動態',
      '查詢今日最新科技產業時事新聞',
      '搜尋外部開源專案的最新版本與更新紀錄'
    ],
    parameters: [
      { name: 'query', type: 'string', required: true, desc: '搜尋引擎關鍵字' },
      { name: 'max_results', type: 'integer', required: false, desc: '最大搜尋結果筆數（預設 5）' }
    ]
  },
  {
    name: 'web_fetch',
    displayName: '網頁全文深入閱讀',
    category: 'web',
    categoryName: '聯網與外部',
    icon: 'description',
    summary: '針對指定的公開網址進行全文抓取與 HTML 結構清洗，擷取核心文章本文供 AI 深度閱讀、交叉驗證與摘要總結。',
    executionMode: '自主調用 / 內容解析',
    priority: '網址深入探討專用',
    triggerTiming: '當使用者在問題中提供特定網址連結，或搜尋摘要需要進一步深入探討閱讀全文時調用。',
    examples: [
      '請深入閱讀這個網頁並整理出重點摘要：https://example.com/article',
      '分析指定網址的技術架構與特點說明'
    ],
    parameters: [
      { name: 'url', type: 'string', required: true, desc: '要讀取的完整網址（http:// 或 https://）' }
    ]
  }
];
const SAMPLE_OAS_SPECS = {
  oas2: `swagger: '2.0'
info:
  title: 即時天氣查詢 API (Swagger 2.0)
  version: 1.0.0
host: httpbin.org
basePath: /
schemes:
  - https
paths:
  /get:
    get:
      summary: 查詢指定城市之即時天氣與氣溫
      operationId: get_weather_by_city
      parameters:
        - name: city
          in: query
          required: true
          type: string
          description: 城市名稱（例如 Taipei, Tokyo, New York）`,
  oas30: `openapi: 3.0.3
info:
  title: 匯率即時轉換服務 (OpenAPI 3.0)
  version: 1.0.0
servers:
  - url: https://httpbin.org
paths:
  /anything/rates:
    get:
      summary: 查詢法幣與加密貨幣即時匯率換算
      operationId: get_exchange_rate
      parameters:
        - name: from_currency
          in: query
          required: true
          schema:
            type: string
          description: 來源貨幣代碼（例如 USD, TWD, EUR）
        - name: to_currency
          in: query
          required: true
          schema:
            type: string
          description: 目標貨幣代碼（例如 TWD, JPY, USD）`,
  oas31: `openapi: 3.1.0
info:
  title: 工單通知派遣服務 (OpenAPI 3.1)
  version: 2.0.0
servers:
  - url: https://httpbin.org
paths:
  /post:
    post:
      summary: 發送緊急工單派遣通知
      operationId: send_dispatch_ticket
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                ticket_id:
                  type:
                    - string
                    - integer
                  description: 工單編號
                title:
                  type: string
                  description: 工單標題
                priority:
                  type: string
                  enum: [low, medium, high, urgent]
                  description: 優先等級
              required: [ticket_id, title]`
};
export default function AiTools() {
  const navigate = useNavigate();
  const [defaultTools, setDefaultTools] = useState(DEFAULT_TOOLS_METADATA);
  const [customTools, setCustomTools] = useState([]);
  const [mcpServers, setMcpServers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  // 提示訊息
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  // OpenAPI 匯入 Modal 狀態
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [specInput, setSpecInput] = useState('');
  const [defaultBaseUrl, setDefaultBaseUrl] = useState('');
  const [parsing, setParsing] = useState(false);
  const [parseResult, setParseResult] = useState(null);
  const [selectedEndpoints, setSelectedEndpoints] = useState({});
  const [globalAuthToken, setGlobalAuthToken] = useState('');
  const [importing, setImporting] = useState(false);
  // 手動自訂 API 工具 Modal 狀態
  const [toolModalOpen, setToolModalOpen] = useState(false);
  const [editingTool, setEditingTool] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    method: 'GET',
    url: '',
    auth_type: 'none',
    auth_token: '',
    timeout: 15,
    parameters_json: '{\n  "type": "object",\n  "properties": {}\n}'
  });
  // 自訂 API 工具線上測試 Modal 狀態
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [testingTool, setTestingTool] = useState(null);
  const [testArgs, setTestArgs] = useState({});
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  // MCP 伺服器 Modal 狀態
  const [mcpModalOpen, setMcpModalOpen] = useState(false);
  const [mcpPresets, setMcpPresets] = useState([]);
  const [editingMcpServer, setEditingMcpServer] = useState(null);
  const [mcpFormData, setMcpFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    transport_type: 'stdio',
    command: 'python',
    args_json: '[]',
    env_vars_json: '{}',
    url: '',
    headers_json: '{}',
    timeout: 30
  });
  // MCP 工具線上測試 Modal 狀態
  const [mcpTestModalOpen, setMcpTestModalOpen] = useState(false);
  const [testingMcpServer, setTestingMcpServer] = useState(null);
  const [testingMcpTool, setTestingMcpTool] = useState(null);
  const [mcpTestArgs, setMcpTestArgs] = useState({});
  const [mcpTesting, setMcpTesting] = useState(false);
  const [mcpTestResult, setMcpTestResult] = useState(null);
  const [discoveringId, setDiscoveringId] = useState(null);
  // 載入後端工具清單與 MCP 伺服器
  const fetchAllTools = useCallback(async () => {
    try {
      setLoading(true);
      const [resDefault, resCustom, resMcp, resPresets] = await Promise.allSettled([
        chatService.getTools(),
        apiToolService.getTools(),
        mcpService.getServers(),
        mcpService.getPresets()
      ]);
      if (resDefault.status === 'fulfilled' && resDefault.value?.tools) {
        const updated = DEFAULT_TOOLS_METADATA.map((meta) => {
          const matched = resDefault.value.tools.find(
            (t) => (t.function ? t.function.name : t.name) === meta.name
          );
          if (matched) {
            const func = matched.function || matched;
            return { ...meta, backendDescription: func.description };
          }
          return meta;
        });
        setDefaultTools(updated);
      }
      if (resCustom.status === 'fulfilled' && resCustom.value?.tools) {
        setCustomTools(resCustom.value.tools);
      }
      if (resMcp.status === 'fulfilled' && resMcp.value?.servers) {
        setMcpServers(resMcp.value.servers);
      }
      if (resPresets.status === 'fulfilled' && resPresets.value?.presets) {
        setMcpPresets(resPresets.value.presets);
      }
    } catch (err) {
      console.warn('載入工具清單失敗:', err);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    queueMicrotask(() => {
      fetchAllTools();
    });
  }, [fetchAllTools]);
  const handleTestExample = (exampleText) => {
    navigate('/chat', { state: { prefillPrompt: exampleText } });
  };
  // 切換自訂 API 工具啟用狀態
  const handleToggleCustomTool = async (toolId) => {
    try {
      const res = await apiToolService.toggleTool(toolId);
      setCustomTools((prev) =>
        prev.map((t) => (t.id === toolId ? { ...t, is_enabled: res.is_enabled } : t))
      );
      setSnackbar({ open: true, message: res.message, severity: 'success' });
    } catch (err) {
      console.warn('切換工具狀態失敗:', err);
      setSnackbar({ open: true, message: '切換狀態失敗', severity: 'error' });
    }
  };
  // 刪除自訂 API 工具
  const handleDeleteCustomTool = async (toolId) => {
    if (!window.confirm('確定要刪除此自訂 API 工具嗎？')) return;
    try {
      await apiToolService.deleteTool(toolId);
      setCustomTools((prev) => prev.filter((t) => t.id !== toolId));
      setSnackbar({ open: true, message: '工具已成功刪除', severity: 'success' });
    } catch (err) {
      console.warn('刪除工具失敗:', err);
      setSnackbar({ open: true, message: '刪除失敗', severity: 'error' });
    }
  };
  // 解析 OpenAPI 規格
  const handleParseSpec = async () => {
    if (!specInput.trim()) {
      setSnackbar({ open: true, message: '請輸入 OpenAPI 規格內容或網址', severity: 'warning' });
      return;
    }
    try {
      setParsing(true);
      const res = await apiToolService.parseOpenApiSpec(specInput, defaultBaseUrl);
      if (res?.data) {
        setParseResult(res.data);
        const sel = {};
        res.data.endpoints.forEach((ep) => {
          sel[ep.name] = true;
        });
        setSelectedEndpoints(sel);
      }
    } catch (err) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || '解析 OpenAPI 規格失敗，請檢查格式',
        severity: 'error'
      });
    } finally {
      setParsing(false);
    }
  };
  // 執行批次匯入
  const handleExecuteImport = async () => {
    if (!parseResult) return;
    const toImport = parseResult.endpoints.filter((ep) => selectedEndpoints[ep.name]);
    if (toImport.length === 0) {
      setSnackbar({ open: true, message: '請至少勾選一個要匯入的 API 端點', severity: 'warning' });
      return;
    }
    try {
      setImporting(true);
      const authConfig = globalAuthToken ? { token: globalAuthToken } : {};
      const authType = globalAuthToken ? 'bearer' : 'none';
      const res = await apiToolService.importTools({
        tools: toImport,
        global_base_url: parseResult.base_url || defaultBaseUrl,
        global_auth_type: authType,
        global_auth_config: authConfig
      });
      setSnackbar({ open: true, message: res.message, severity: 'success' });
      setImportModalOpen(false);
      setParseResult(null);
      setSpecInput('');
      fetchAllTools();
    } catch (err) {
      console.warn('匯入工具失敗:', err);
      setSnackbar({ open: true, message: '匯入工具失敗', severity: 'error' });
    } finally {
      setImporting(false);
    }
  };
  // 開啟手動新增/編輯自訂 API Modal
  const handleOpenToolModal = (tool = null) => {
    if (tool) {
      setEditingTool(tool);
      setFormData({
        name: tool.name,
        display_name: tool.display_name,
        description: tool.description,
        method: tool.method,
        url: tool.url,
        auth_type: tool.auth_type || 'none',
        auth_token: tool.auth_config?.token || '',
        timeout: tool.timeout || 15,
        parameters_json: JSON.stringify(tool.parameters_schema || { type: 'object', properties: {} }, null, 2)
      });
    } else {
      setEditingTool(null);
      setFormData({
        name: '',
        display_name: '',
        description: '',
        method: 'GET',
        url: '',
        auth_type: 'none',
        auth_token: '',
        timeout: 15,
        parameters_json: '{\n  "type": "object",\n  "properties": {\n    "query": {\n      "type": "string",\n      "description": "參數說明"\n    }\n  },\n  "required": ["query"]\n}'
      });
    }
    setToolModalOpen(true);
  };
  // 儲存自訂 API 工具
  const handleSaveTool = async (e) => {
    e.preventDefault();
    try {
      let parsedSchema = {};
      if (formData.parameters_json) {
        parsedSchema = JSON.parse(formData.parameters_json);
      }
      const payload = {
        name: formData.name,
        display_name: formData.display_name,
        description: formData.description,
        method: formData.method,
        url: formData.url,
        auth_type: formData.auth_type,
        auth_config: formData.auth_token ? { token: formData.auth_token } : {},
        timeout: Number(formData.timeout) || 15,
        parameters_schema: parsedSchema
      };
      if (editingTool) {
        await apiToolService.updateTool(editingTool.id, payload);
        setSnackbar({ open: true, message: '工具更新成功', severity: 'success' });
      } else {
        await apiToolService.createTool(payload);
        setSnackbar({ open: true, message: '自訂 API 工具建立成功', severity: 'success' });
      }
      setToolModalOpen(false);
      fetchAllTools();
    } catch (err) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || '儲存失敗，請檢查參數格式與必填欄位',
        severity: 'error'
      });
    }
  };
  // 開啟自訂 API 線上測試 Modal
  const handleOpenTestModal = (tool) => {
    setTestingTool(tool);
    setTestResult(null);
    const initialArgs = {};
    if (tool.parameters_schema?.properties) {
      Object.keys(tool.parameters_schema.properties).forEach((k) => {
        initialArgs[k] = '';
      });
    }
    setTestArgs(initialArgs);
    setTestModalOpen(true);
  };
  // 執行自訂 API 線上測試
  const handleRunTest = async () => {
    if (!testingTool) return;
    try {
      setTesting(true);
      const res = await apiToolService.testTool(testingTool.id, testArgs);
      setTestResult(res.result);
    } catch (err) {
      setTestResult({
        status_code: 500,
        is_success: false,
        error: err.response?.data?.detail || '測試請求發送失敗'
      });
    } finally {
      setTesting(false);
    }
  };
  // --- MCP 相關操作 ---
  // 切換 MCP 伺服器啟用狀態
  const handleToggleMcpServer = async (serverId) => {
    try {
      const res = await mcpService.toggleServer(serverId);
      setMcpServers((prev) =>
        prev.map((s) => (s.id === serverId ? { ...s, is_enabled: res.is_enabled } : s))
      );
      setSnackbar({ open: true, message: res.message, severity: 'success' });
    } catch (err) {
      console.warn('切換 MCP 狀態失敗:', err);
      setSnackbar({ open: true, message: '切換狀態失敗', severity: 'error' });
    }
  };
  // 刪除 MCP 伺服器
  const handleDeleteMcpServer = async (serverId) => {
    if (!window.confirm('確定要刪除此 MCP 伺服器嗎？')) return;
    try {
      await mcpService.deleteServer(serverId);
      setMcpServers((prev) => prev.filter((s) => s.id !== serverId));
      setSnackbar({ open: true, message: 'MCP 伺服器已成功刪除', severity: 'success' });
    } catch (err) {
      console.warn('刪除 MCP 伺服器失敗:', err);
      setSnackbar({ open: true, message: '刪除失敗', severity: 'error' });
    }
  };
  // 探索 MCP 工具清單
  const handleDiscoverMcpServer = async (serverId) => {
    try {
      setDiscoveringId(serverId);
      const res = await mcpService.discoverServer(serverId);
      setMcpServers((prev) =>
        prev.map((s) => (s.id === serverId ? res.server : s))
      );
      setSnackbar({ open: true, message: res.message, severity: 'success' });
    } catch (err) {
      console.warn('探索 MCP 伺服器失敗:', err);
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || '連線與探索 MCP 工具失敗',
        severity: 'error'
      });
      // 重新整理取得更新後的 error status
      fetchAllTools();
    } finally {
      setDiscoveringId(null);
    }
  };
  // 開啟 MCP 新增/編輯 Modal
  const handleOpenMcpModal = (server = null) => {
    if (server) {
      setEditingMcpServer(server);
      setMcpFormData({
        name: server.name,
        display_name: server.display_name,
        description: server.description || '',
        transport_type: server.transport_type || 'stdio',
        command: server.command || 'python',
        args_json: JSON.stringify(server.args || [], null, 2),
        env_vars_json: JSON.stringify(server.env_vars || {}, null, 2),
        url: server.url || '',
        headers_json: JSON.stringify(server.headers || {}, null, 2),
        timeout: server.timeout || 30
      });
    } else {
      setEditingMcpServer(null);
      setMcpFormData({
        name: 'mcp_custom',
        display_name: '自訂 MCP 伺服器',
        description: '提供客製化本地或遠端 MCP 工具服務',
        transport_type: 'stdio',
        command: 'python',
        args_json: '[]',
        env_vars_json: '{}',
        url: '',
        headers_json: '{}',
        timeout: 30
      });
    }
    setMcpModalOpen(true);
  };
  // 套用 MCP 官方範本
  const handleApplyMcpPreset = (preset) => {
    setMcpFormData({
      name: preset.name,
      display_name: preset.display_name,
      description: preset.description || '',
      transport_type: preset.transport_type || 'stdio',
      command: preset.command || '',
      args_json: JSON.stringify(preset.args || [], null, 2),
      env_vars_json: JSON.stringify(preset.env_vars || {}, null, 2),
      url: preset.url || '',
      headers_json: JSON.stringify(preset.headers || {}, null, 2),
      timeout: preset.timeout || 30
    });
  };
  // 儲存 MCP 伺服器
  const handleSaveMcpServer = async (e) => {
    e.preventDefault();
    try {
      let parsedArgs = [];
      let parsedEnv = {};
      let parsedHeaders = {};
      if (mcpFormData.args_json) parsedArgs = JSON.parse(mcpFormData.args_json);
      if (mcpFormData.env_vars_json) parsedEnv = JSON.parse(mcpFormData.env_vars_json);
      if (mcpFormData.headers_json) parsedHeaders = JSON.parse(mcpFormData.headers_json);
      const payload = {
        name: mcpFormData.name,
        display_name: mcpFormData.display_name,
        description: mcpFormData.description,
        transport_type: mcpFormData.transport_type,
        command: mcpFormData.command,
        args: parsedArgs,
        env_vars: parsedEnv,
        url: mcpFormData.url,
        headers: parsedHeaders,
        timeout: Number(mcpFormData.timeout) || 30
      };
      if (editingMcpServer) {
        await mcpService.updateServer(editingMcpServer.id, payload);
        setSnackbar({ open: true, message: 'MCP 伺服器配置更新成功', severity: 'success' });
      } else {
        await mcpService.createServer(payload);
        setSnackbar({ open: true, message: 'MCP 伺服器建立成功並已嘗試自動連線', severity: 'success' });
      }
      setMcpModalOpen(false);
      fetchAllTools();
    } catch (err) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || '儲存失敗，請檢查 JSON 欄位格式',
        severity: 'error'
      });
    }
  };
  // 開啟 MCP 工具測試 Modal
  const handleOpenMcpTestModal = (server, tool) => {
    setTestingMcpServer(server);
    setTestingMcpTool(tool);
    setMcpTestResult(null);
    const initialArgs = {};
    if (tool.inputSchema?.properties) {
      Object.keys(tool.inputSchema.properties).forEach((k) => {
        initialArgs[k] = '';
      });
    }
    setMcpTestArgs(initialArgs);
    setMcpTestModalOpen(true);
  };
  // 執行 MCP 工具線上測試
  const handleRunMcpTest = async () => {
    if (!testingMcpServer || !testingMcpTool) return;
    try {
      setMcpTesting(true);
      const res = await mcpService.testTool(testingMcpServer.id, testingMcpTool.name, mcpTestArgs);
      setMcpTestResult(res.result);
    } catch (err) {
      setMcpTestResult({
        is_success: false,
        error: err.response?.data?.detail || 'MCP 工具調用失敗'
      });
    } finally {
      setMcpTesting(false);
    }
  };
  // 計算 MCP 工具總數
  const totalMcpToolsCount = mcpServers.reduce((acc, s) => {
    return acc + (s.discovered_tools?.length || 0);
  }, 0);
  // 整理所有工具以供呈現
  const allUnifiedTools = [
    ...defaultTools.map((t) => ({ ...t, isCustom: false, isMcp: false, is_enabled: true })),
    ...customTools.map((t) => ({
      ...t,
      isCustom: true,
      isMcp: false,
      categoryName: '自訂 API',
      icon: 'code',
      executionMode: '外部 RESTful API',
      priority: '自主按需調用',
      triggerTiming: `當使用者提問與「${t.display_name}」相關之業務或資料時自主調用。`,
      summary: t.description || '外部自訂 API 服務端點。',
      examples: [`請調用 ${t.display_name} 查詢相關資料`, `查詢 ${t.name} 的即時結果`]
    }))
  ];
  const filteredTools = allUnifiedTools.filter((tool) => {
    let matchesCategory = true;
    if (activeCategory === 'knowledge') matchesCategory = tool.category === 'knowledge';
    else if (activeCategory === 'web') matchesCategory = tool.category === 'web';
    else if (activeCategory === 'custom_api') matchesCategory = tool.isCustom;
    const query = searchQuery.trim().toLowerCase();
    const matchesQuery =
      !query ||
      tool.displayName?.toLowerCase().includes(query) ||
      tool.display_name?.toLowerCase().includes(query) ||
      tool.name.toLowerCase().includes(query) ||
      tool.summary?.toLowerCase().includes(query) ||
      tool.description?.toLowerCase().includes(query);
    return matchesCategory && matchesQuery;
  });
  const getMethodClass = (method) => {
    switch (method?.toUpperCase()) {
      case 'GET': return styles.methodGet;
      case 'POST': return styles.methodPost;
      case 'PUT': return styles.methodPut;
      case 'DELETE': return styles.methodDelete;
      case 'PATCH': return styles.methodPatch;
      default: return styles.methodGet;
    }
  };
  return (
    <div className={styles.container}>
      {/* 頂部 Hero 區塊 */}
      <section className={styles.heroSection}>
        <div className={styles.heroContent}>
          <div className={styles.heroBadge}>
            <Icon name="tune" size={14} />
            <span>AI 工具與 MCP 協定核心中心</span>
          </div>
          <h1 className={styles.heroTitle}>AI 可用工具與 MCP 全景總覽</h1>
          <p className={styles.heroSubtitle}>
            本系統內建自主研究調度引擎（Agentic Research Engine），支援內部知識庫混合檢索、結構化記錄篩選統計、即時聯網搜尋與深入閱讀，並全面原生支援 Model Context Protocol (MCP) 開放標準與全版本 OpenAPI Specification（Swagger 2.0、OpenAPI 3.0 / 3.1）。
          </p>
          <div className={styles.heroActions}>
            <Button
              variant="primary"
              onClick={() => navigate('/chat')}
              startIcon={<Icon name="chat" size={18} />}
            >
              前往對話體驗工具
            </Button>
            <Button
              variant="secondary"
              onClick={() => handleOpenMcpModal()}
              startIcon={<Icon name="build" size={18} />}
            >
              新增 MCP 伺服器
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setSpecInput(SAMPLE_OAS_SPECS.oas30);
                setImportModalOpen(true);
              }}
              startIcon={<Icon name="upload" size={18} />}
            >
              匯入 OpenAPI 規格
            </Button>
            <Button
              variant="secondary"
              onClick={() => handleOpenToolModal()}
              startIcon={<Icon name="add" size={18} />}
            >
              手動新增 API 工具
            </Button>
            <Button
              variant="secondary"
              onClick={fetchAllTools}
              disabled={loading}
              startIcon={loading ? <Spinner size="sm" /> : <Icon name="refresh" size={18} />}
            >
              重新整理狀態
            </Button>
          </div>
        </div>
      </section>
      {/* 指標概覽 */}
      <div className={styles.metricsGrid}>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>內建核心工具</span>
          <div className={styles.metricValue}>
            <Icon name="tools" size={24} color="var(--color-primary)" />
            <span>{defaultTools.length} 項</span>
          </div>
          <span className={styles.metricDesc}>知識庫檢索、統計、聯網與閱讀</span>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>MCP 協定伺服器</span>
          <div className={styles.metricValue}>
            <Icon name="build" size={24} color="var(--color-warning)" />
            <span>{mcpServers.length} 台 ({totalMcpToolsCount} 工具)</span>
          </div>
          <span className={styles.metricDesc}>已連線啟用：{mcpServers.filter((s) => s.is_enabled && s.status === 'connected').length} 台</span>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>自訂 API 工具</span>
          <div className={styles.metricValue}>
            <Icon name="code" size={24} color="var(--color-info)" />
            <span>{customTools.length} 項</span>
          </div>
          <span className={styles.metricDesc}>已啟用：{customTools.filter((t) => t.is_enabled).length} 項</span>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>標準相容性</span>
          <div className={styles.metricValue}>
            <Icon name="check-circle" size={24} color="var(--color-success)" />
            <span>MCP & OAS 全版本</span>
          </div>
          <span className={styles.metricDesc}>Model Context Protocol + Swagger 2.0 / 3.0 / 3.1</span>
        </div>
      </div>
      {/* 篩選與搜尋列 */}
      <div className={styles.filterBar}>
        <div className={styles.tabGroup}>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeCategory === 'all' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveCategory('all')}
          >
            全部工具 ({allUnifiedTools.length + totalMcpToolsCount})
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeCategory === 'mcp' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveCategory('mcp')}
          >
            MCP 協定伺服器 ({mcpServers.length})
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeCategory === 'knowledge' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveCategory('knowledge')}
          >
            知識庫與數據 ({defaultTools.filter((t) => t.category === 'knowledge').length})
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeCategory === 'web' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveCategory('web')}
          >
            聯網與閱讀 ({defaultTools.filter((t) => t.category === 'web').length})
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${activeCategory === 'custom_api' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveCategory('custom_api')}
          >
            自訂 API 工具 ({customTools.length})
          </button>
        </div>
        <div className={styles.searchBox}>
          <Icon name="search" size={16} color="var(--text-tertiary)" />
          <input
            type="text"
            className={styles.searchInput}
            placeholder="搜尋工具名稱、路徑、MCP 或關鍵字..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>
      {/* 1. MCP 伺服器列表區塊 (當 activeCategory === 'mcp' 或 'all' 時展示) */}
      {(activeCategory === 'all' || activeCategory === 'mcp') && (
        <div style={{ marginBottom: 'var(--space-8)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Icon name="build" size={20} color="var(--color-primary)" />
              <span>Model Context Protocol (MCP) 伺服器</span>
            </h2>
            <Button
              variant="secondary"
              onClick={() => handleOpenMcpModal()}
              startIcon={<Icon name="add" size={16} />}
            >
              新增 MCP 伺服器
            </Button>
          </div>
          {mcpServers.length === 0 ? (
            <div className={styles.emptyNotice}>
              尚未配置任何 MCP 伺服器，點擊「新增 MCP 伺服器」即可套用 Time、Filesystem 等預設範本或自訂指令。
            </div>
          ) : (
            <div className={styles.toolsList}>
              {mcpServers.map((server) => {
                const isEnabled = server.is_enabled;
                const isConnected = server.status === 'connected';
                const isError = server.status === 'error';
                const tools = server.discovered_tools || [];
                return (
                  <div key={server.id} className={styles.toolOuterShell}>
                    <div className={styles.toolInnerCore}>
                      <div className={styles.toolHeader}>
                        <div className={styles.toolIdentity}>
                          <div className={styles.toolIconBox} style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#d97706' }}>
                            <Icon name="build" size={22} />
                          </div>
                          <div className={styles.toolTitleWrap}>
                            <div className={styles.toolTitle}>
                              <span className={`${styles.methodBadge} ${styles.methodPost}`}>
                                {server.transport_type}
                              </span>
                              <span>{server.display_name}</span>
                            </div>
                            <div className={styles.toolIdentifier}>{server.name}</div>
                          </div>
                        </div>
                        <div className={styles.toolStatusWrap}>
                          <span className={styles.categoryTag}>MCP Server</span>
                          <span className={`${styles.statusPill} ${isConnected ? styles.statusActive : isError ? styles.methodDelete : styles.statusDisabled
                            }`}>
                            <span className={styles.statusDot} />
                            <span>
                              {isConnected ? '已連線 (Connected)' : isError ? '連線錯誤 (Error)' : '未連線'}
                            </span>
                          </span>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: 'var(--font-size-xs)', color: isEnabled ? 'var(--color-success)' : 'var(--text-tertiary)' }}>
                              {isEnabled ? '已啟用' : '已停用'}
                            </span>
                            <Switch
                              checked={isEnabled}
                              onChange={() => handleToggleMcpServer(server.id)}
                            />
                          </div>
                        </div>
                      </div>
                      <p className={styles.toolDescription}>{server.description || 'MCP 協定外部工具伺服器。'}</p>
                      {/* 連線執行配置 */}
                      <div className={styles.specBlock} style={{ marginBottom: 'var(--space-4)' }}>
                        <div className={styles.specLabel}>
                          <Icon name="terminal" size={14} color="var(--color-primary)" />
                          <span>
                            {server.transport_type === 'stdio' ? 'Stdio 啟動指令與參數' : 'HTTP / SSE 連線網址'}
                          </span>
                        </div>
                        <div className={styles.specContent} style={{ fontFamily: 'var(--font-mono)' }}>
                          {server.transport_type === 'stdio'
                            ? `${server.command || ''} ${(server.args || []).join(' ')}`
                            : server.url}
                        </div>
                      </div>
                      {/* 錯誤資訊 */}
                      {server.last_error && (
                        <div className={styles.specBlock} style={{ marginBottom: 'var(--space-4)', borderColor: 'var(--color-error)' }}>
                          <div className={styles.specLabel} style={{ color: 'var(--color-error)' }}>
                            <Icon name="warning" size={14} color="var(--color-error)" />
                            <span>最近一次連線/探索異常紀錄</span>
                          </div>
                          <div className={styles.specContent} style={{ color: 'var(--color-error)' }}>
                            {server.last_error}
                          </div>
                        </div>
                      )}
                      {/* 探索到的 MCP Tools 清單 */}
                      <div className={styles.specBlock} style={{ marginBottom: 'var(--space-4)' }}>
                        <div className={styles.specLabel} style={{ justifyContent: 'space-between' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Icon name="code" size={14} color="var(--color-primary)" />
                            <span>提供之 MCP 工具 ({tools.length} 項)</span>
                          </div>
                          <Button
                            variant="secondary"
                            onClick={() => handleDiscoverMcpServer(server.id)}
                            disabled={discoveringId === server.id}
                            startIcon={discoveringId === server.id ? <Spinner size="sm" /> : <Icon name="refresh" size={14} />}
                          >
                            {discoveringId === server.id ? '正在連線探索...' : '重新探索工具 (tools/list)'}
                          </Button>
                        </div>
                        {tools.length === 0 ? (
                          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', padding: '8px 0' }}>
                            尚未探索到工具，請點擊上方按鈕執行工具探索。
                          </div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                            {tools.map((t) => (
                              <div
                                key={t.name}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                  padding: '8px 12px',
                                  background: 'var(--bg-surface)',
                                  borderRadius: 'var(--radius-md)',
                                  border: '1px solid var(--border-default)'
                                }}
                              >
                                <div>
                                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold', fontSize: 'var(--font-size-xs)' }}>
                                    {t.name}
                                  </div>
                                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
                                    {t.description || '無詳細說明'}
                                  </div>
                                </div>
                                <Button
                                  variant="secondary"
                                  onClick={() => handleOpenMcpTestModal(server, t)}
                                  startIcon={<Icon name="speed" size={14} />}
                                >
                                  線上測試
                                </Button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      {/* 伺服器操作按鈕 */}
                      <div className={styles.toolActionsFooter}>
                        <div className={styles.toolActionGroup}>
                          <Button
                            variant="secondary"
                            onClick={() => handleOpenMcpModal(server)}
                            startIcon={<Icon name="edit" size={16} />}
                          >
                            編輯伺服器配置
                          </Button>
                        </div>
                        <Button
                          variant="danger"
                          onClick={() => handleDeleteMcpServer(server.id)}
                          startIcon={<Icon name="delete" size={16} />}
                        >
                          刪除伺服器
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
      {/* 2. 內部工具與自訂 API 工具列表區塊 */}
      {activeCategory !== 'mcp' && (
        <div className={styles.toolsList}>
          {filteredTools.length === 0 ? (
            <div className={styles.emptyNotice}>
              查無符合「{searchQuery}」的相關工具
            </div>
          ) : (
            filteredTools.map((tool) => {
              const title = tool.display_name || tool.displayName;
              const isEnabled = tool.is_enabled !== false;
              const parametersList = tool.isCustom
                ? Object.entries(tool.parameters_schema?.properties || {}).map(([pName, pObj]) => ({
                  name: pName,
                  type: pObj.type || 'string',
                  required: tool.parameters_schema?.required?.includes(pName),
                  desc: pObj.description || ''
                }))
                : tool.parameters || [];
              return (
                <div key={tool.isCustom ? `custom_${tool.id}` : tool.name} className={styles.toolOuterShell}>
                  <div className={styles.toolInnerCore}>
                    {/* 工具頭部資訊 */}
                    <div className={styles.toolHeader}>
                      <div className={styles.toolIdentity}>
                        <div className={styles.toolIconBox}>
                          <Icon name={tool.icon || 'code'} size={22} />
                        </div>
                        <div className={styles.toolTitleWrap}>
                          <div className={styles.toolTitle}>
                            {tool.isCustom && tool.method && (
                              <span className={`${styles.methodBadge} ${getMethodClass(tool.method)}`}>
                                {tool.method}
                              </span>
                            )}
                            <span>{title}</span>
                          </div>
                          <div className={styles.toolIdentifier}>{tool.name}</div>
                        </div>
                      </div>
                      <div className={styles.toolStatusWrap}>
                        <span className={styles.categoryTag}>{tool.categoryName || '工具'}</span>
                        {tool.spec_version && (
                          <span className={styles.versionTag}>{tool.spec_version}</span>
                        )}
                        {tool.isCustom ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span className={`${styles.statusPill} ${isEnabled ? styles.statusActive : styles.statusDisabled}`}>
                              <span className={styles.statusDot} />
                              <span>{isEnabled ? '已啟用' : '已停用'}</span>
                            </span>
                            <Switch
                              checked={isEnabled}
                              onChange={() => handleToggleCustomTool(tool.id)}
                            />
                          </div>
                        ) : (
                          <span className={`${styles.statusPill} ${styles.statusActive}`}>
                            <span className={styles.statusDot} />
                            <span>內建線上</span>
                          </span>
                        )}
                      </div>
                    </div>
                    {/* 功能簡介 */}
                    <p className={styles.toolDescription}>{tool.summary}</p>
                    {/* URL 與路徑 (自訂工具) */}
                    {tool.isCustom && tool.url && (
                      <div className={styles.specBlock} style={{ marginBottom: 'var(--space-4)' }}>
                        <div className={styles.specLabel}>
                          <Icon name="link" size={14} color="var(--color-primary)" />
                          <span>目標 API 請求網址 (Endpoint URL)</span>
                        </div>
                        <div className={styles.specContent} style={{ fontFamily: 'var(--font-mono)' }}>
                          {tool.url}
                        </div>
                      </div>
                    )}
                    {/* 核心規格與時機 */}
                    <div className={styles.specsGrid}>
                      <div className={styles.specBlock}>
                        <div className={styles.specLabel}>
                          <Icon name="timeline" size={14} color="var(--color-primary)" />
                          <span>觸發調用時機</span>
                        </div>
                        <div className={styles.specContent}>{tool.triggerTiming}</div>
                      </div>
                      <div className={styles.specBlock}>
                        <div className={styles.specLabel}>
                          <Icon name="tune" size={14} color="var(--color-primary)" />
                          <span>調度機制與特性</span>
                        </div>
                        <div className={styles.specContent}>
                          <div>模式：{tool.executionMode}</div>
                          <div>優先級：{tool.priority}</div>
                        </div>
                      </div>
                    </div>
                    {/* 參數規格說明 */}
                    {parametersList.length > 0 && (
                      <div className={styles.specBlock} style={{ marginBottom: 'var(--space-4)' }}>
                        <div className={styles.specLabel}>
                          <Icon name="code" size={14} color="var(--color-primary)" />
                          <span>支援參數規格 (Parameters Schema)</span>
                        </div>
                        <table className={styles.paramsTable}>
                          <thead>
                            <tr>
                              <th style={{ width: '25%' }}>參數名稱</th>
                              <th style={{ width: '15%' }}>資料型態</th>
                              <th style={{ width: '60%' }}>說明</th>
                            </tr>
                          </thead>
                          <tbody>
                            {parametersList.map((param) => (
                              <tr key={param.name}>
                                <td>
                                  <span className={styles.paramName}>{param.name}</span>
                                  {param.required && <span className={styles.paramRequired}>*</span>}
                                </td>
                                <td>
                                  <span className={styles.paramType}>{param.type}</span>
                                </td>
                                <td>{param.desc || '無特定說明'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                    {/* 自訂工具專屬操作按鈕 */}
                    {tool.isCustom && (
                      <div className={styles.toolActionsFooter}>
                        <div className={styles.toolActionGroup}>
                          <Button
                            variant="secondary"
                            onClick={() => handleOpenTestModal(tool)}
                            startIcon={<Icon name="speed" size={16} />}
                          >
                            即時線上測試
                          </Button>
                          <Button
                            variant="secondary"
                            onClick={() => handleOpenToolModal(tool)}
                            startIcon={<Icon name="edit" size={16} />}
                          >
                            編輯配置
                          </Button>
                        </div>
                        <Button
                          variant="danger"
                          onClick={() => handleDeleteCustomTool(tool.id)}
                          startIcon={<Icon name="delete" size={16} />}
                        >
                          刪除工具
                        </Button>
                      </div>
                    )}
                    {/* 推薦提問測試 (內建工具) */}
                    {!tool.isCustom && tool.examples && (
                      <div className={styles.examplesSection}>
                        <div className={styles.examplesTitle}>
                          <Icon name="lightbulb" size={14} color="var(--color-warning)" />
                          <span>測試提問範例（點擊可直接帶入聊天提問）</span>
                        </div>
                        <div className={styles.examplePillsWrap}>
                          {tool.examples.map((ex, idx) => (
                            <button
                              key={idx}
                              type="button"
                              className={styles.examplePill}
                              onClick={() => handleTestExample(ex)}
                            >
                              <Icon name="send" size={12} color="var(--color-primary)" />
                              <span>{ex}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
      {/* 3. MCP 伺服器新增 / 編輯 Modal */}
      {mcpModalOpen && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalCard}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>
                {editingMcpServer ? '編輯 MCP 伺服器' : '新增 Model Context Protocol (MCP) 伺服器'}
              </div>
              <button
                type="button"
                style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
                onClick={() => setMcpModalOpen(false)}
              >
                <Icon name="close" size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveMcpServer}>
              <div className={styles.modalBody}>
                {!editingMcpServer && mcpPresets.length > 0 && (
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>快速套用官方與社群範本：</label>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {mcpPresets.map((p) => (
                        <Button
                          key={p.name}
                          variant="secondary"
                          type="button"
                          onClick={() => handleApplyMcpPreset(p)}
                        >
                          {p.display_name}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>伺服器識別名稱 (英文小寫與底線)*：</label>
                    <input
                      type="text"
                      className={styles.formInput}
                      placeholder="例如 mcp_time"
                      value={mcpFormData.name}
                      onChange={(e) => setMcpFormData({ ...mcpFormData, name: e.target.value })}
                      disabled={!!editingMcpServer}
                      required
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>顯示名稱 (繁體中文)*：</label>
                    <input
                      type="text"
                      className={styles.formInput}
                      placeholder="例如 時間查詢服務"
                      value={mcpFormData.display_name}
                      onChange={(e) => setMcpFormData({ ...mcpFormData, display_name: e.target.value })}
                      required
                    />
                  </div>
                </div>
                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>說明描述：</label>
                  <input
                    type="text"
                    className={styles.formInput}
                    placeholder="說明此 MCP 伺服器的功能與用途"
                    value={mcpFormData.description}
                    onChange={(e) => setMcpFormData({ ...mcpFormData, description: e.target.value })}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: '16px' }}>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>傳輸模式：</label>
                    <select
                      className={styles.formSelect}
                      value={mcpFormData.transport_type}
                      onChange={(e) => setMcpFormData({ ...mcpFormData, transport_type: e.target.value })}
                    >
                      <option value="stdio">Stdio (子進程)</option>
                      <option value="sse">SSE (Server-Sent Events)</option>
                      <option value="http">HTTP (POST Stream)</option>
                    </select>
                  </div>
                  {mcpFormData.transport_type === 'stdio' ? (
                    <div className={styles.formGroup}>
                      <label className={styles.formLabel}>啟動指令 (Command)*：</label>
                      <input
                        type="text"
                        className={styles.formInput}
                        placeholder="例如 npx, uvx, python"
                        value={mcpFormData.command}
                        onChange={(e) => setMcpFormData({ ...mcpFormData, command: e.target.value })}
                        required
                      />
                    </div>
                  ) : (
                    <div className={styles.formGroup}>
                      <label className={styles.formLabel}>連線網址 (URL)*：</label>
                      <input
                        type="text"
                        className={styles.formInput}
                        placeholder="例如 http://localhost:8080/sse"
                        value={mcpFormData.url}
                        onChange={(e) => setMcpFormData({ ...mcpFormData, url: e.target.value })}
                        required
                      />
                    </div>
                  )}
                </div>
                {mcpFormData.transport_type === 'stdio' && (
                  <>
                    <div className={styles.formGroup}>
                      <label className={styles.formLabel}>指令參數清單 (JSON 陣列格式)：</label>
                      <textarea
                        className={styles.formTextarea}
                        style={{ minHeight: '80px' }}
                        value={mcpFormData.args_json}
                        onChange={(e) => setMcpFormData({ ...mcpFormData, args_json: e.target.value })}
                        placeholder='["-y", "@modelcontextprotocol/server-filesystem", "./data"]'
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.formLabel}>環境變數配置 (JSON 物件格式)：</label>
                      <textarea
                        className={styles.formTextarea}
                        style={{ minHeight: '60px' }}
                        value={mcpFormData.env_vars_json}
                        onChange={(e) => setMcpFormData({ ...mcpFormData, env_vars_json: e.target.value })}
                        placeholder='{"API_KEY": "secret"}'
                      />
                    </div>
                  </>
                )}
                {mcpFormData.transport_type !== 'stdio' && (
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>自訂 HTTP Headers (JSON 物件格式)：</label>
                    <textarea
                      className={styles.formTextarea}
                      style={{ minHeight: '60px' }}
                      value={mcpFormData.headers_json}
                      onChange={(e) => setMcpFormData({ ...mcpFormData, headers_json: e.target.value })}
                      placeholder='{"Authorization": "Bearer ..."}'
                    />
                  </div>
                )}
              </div>
              <div className={styles.modalFooter}>
                <Button variant="secondary" type="button" onClick={() => setMcpModalOpen(false)}>
                  取消
                </Button>
                <Button variant="primary" type="submit" startIcon={<Icon name="save" size={16} />}>
                  {editingMcpServer ? '儲存變更' : '建立並連線探索'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* 4. MCP 工具線上測試 Modal */}
      {mcpTestModalOpen && testingMcpServer && testingMcpTool && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalCard}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>
                即時測試 MCP 工具：{testingMcpTool.name}
              </div>
              <button
                type="button"
                style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
                onClick={() => setMcpTestModalOpen(false)}
              >
                <Icon name="close" size={20} />
              </button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.specBlock}>
                <div className={styles.specLabel}>
                  <span className={`${styles.methodBadge} ${styles.methodPost}`}>{testingMcpServer.display_name}</span>
                  <span>{testingMcpTool.description || '無詳細說明'}</span>
                </div>
              </div>
              <div className={styles.formGroup}>
                <label className={styles.formLabel}>輸入參數 (Arguments)：</label>
                {Object.keys(testingMcpTool.inputSchema?.properties || {}).length === 0 ? (
                  <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>此 MCP 工具無須輸入額外參數</p>
                ) : (
                  Object.entries(testingMcpTool.inputSchema?.properties || {}).map(([pName, pObj]) => (
                    <div key={pName} style={{ marginBottom: '8px' }}>
                      <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-medium)' }}>
                        {pName} {testingMcpTool.inputSchema?.required?.includes(pName) && <span style={{ color: 'var(--color-error)' }}>*</span>}:
                        <span style={{ color: 'var(--text-tertiary)', marginLeft: '6px' }}>({pObj.description || pObj.type})</span>
                      </label>
                      <input
                        type="text"
                        className={styles.formInput}
                        placeholder={`請輸入 ${pName}`}
                        value={mcpTestArgs[pName] || ''}
                        onChange={(e) => setMcpTestArgs({ ...mcpTestArgs, [pName]: e.target.value })}
                      />
                    </div>
                  ))
                )}
              </div>
              {mcpTestResult && (
                <div className={styles.formGroup}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <label className={styles.formLabel}>MCP 回傳結果 (tools/call)：</label>
                    <span style={{ fontSize: 'var(--font-size-xs)', color: mcpTestResult.is_success ? 'var(--color-success)' : 'var(--color-error)' }}>
                      耗時: {mcpTestResult.duration_seconds}s
                    </span>
                  </div>
                  <pre className={styles.jsonViewer}>
                    {JSON.stringify(mcpTestResult.content || mcpTestResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>
            <div className={styles.modalFooter}>
              <Button variant="secondary" onClick={() => setMcpTestModalOpen(false)}>
                關閉
              </Button>
              <Button
                variant="primary"
                onClick={handleRunMcpTest}
                disabled={mcpTesting}
                startIcon={mcpTesting ? <Spinner size="sm" /> : <Icon name="send" size={16} />}
              >
                {mcpTesting ? '正在調用 MCP...' : '發送 MCP 測試請求'}
              </Button>
            </div>
          </div>
        </div>
      )}
      {/* 5. OpenAPI 匯入 Modal */}
      {importModalOpen && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalCard}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>匯入 OpenAPI / Swagger 規格</div>
              <button
                type="button"
                style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
                onClick={() => setImportModalOpen(false)}
              >
                <Icon name="close" size={20} />
              </button>
            </div>
            <div className={styles.modalBody}>
              {!parseResult ? (
                <>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>快速載入官方測試範例：</label>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <Button
                        variant="secondary"
                        onClick={() => setSpecInput(SAMPLE_OAS_SPECS.oas2)}
                      >
                        Swagger 2.0 (即時天氣)
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => setSpecInput(SAMPLE_OAS_SPECS.oas30)}
                      >
                        OpenAPI 3.0 (匯率轉換)
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => setSpecInput(SAMPLE_OAS_SPECS.oas31)}
                      >
                        OpenAPI 3.1 (工單派遣)
                      </Button>
                    </div>
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>OpenAPI 規格內容 (JSON / YAML) 或 遠端 URL：</label>
                    <textarea
                      className={styles.formTextarea}
                      style={{ minHeight: '220px' }}
                      placeholder="貼上 OpenAPI / Swagger 規範 YAML/JSON，或輸入 https://.../openapi.json 網址"
                      value={specInput}
                      onChange={(e) => setSpecInput(e.target.value)}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>預設 Base URL (可選，覆蓋規格中的伺服器位址)：</label>
                    <input
                      type="text"
                      className={styles.formInput}
                      placeholder="例如 https://api.example.com"
                      value={defaultBaseUrl}
                      onChange={(e) => setDefaultBaseUrl(e.target.value)}
                    />
                  </div>
                </>
              ) : (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <span className={styles.versionTag}>{parseResult.version}</span>
                      <strong style={{ marginLeft: '8px', fontSize: 'var(--font-size-base)' }}>{parseResult.title}</strong>
                    </div>
                    <Button variant="secondary" onClick={() => setParseResult(null)}>
                      重新解析
                    </Button>
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>全域 Bearer Token (可選，將自動注入 Authorization Header)：</label>
                    <input
                      type="password"
                      className={styles.formInput}
                      placeholder="若 API 需要認證請填寫 Bearer Token 或 API Key"
                      value={globalAuthToken}
                      onChange={(e) => setGlobalAuthToken(e.target.value)}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <label className={styles.formLabel}>
                        選擇要匯入的 API 端點 ({Object.values(selectedEndpoints).filter(Boolean).length} / {parseResult.endpoints.length})：
                      </label>
                      <button
                        type="button"
                        style={{ background: 'transparent', border: 'none', color: 'var(--color-primary)', cursor: 'pointer', fontSize: 'var(--font-size-xs)' }}
                        onClick={() => {
                          const allChecked = Object.values(selectedEndpoints).every(Boolean);
                          const updated = {};
                          parseResult.endpoints.forEach((ep) => {
                            updated[ep.name] = !allChecked;
                          });
                          setSelectedEndpoints(updated);
                        }}
                      >
                        全選 / 全不選
                      </button>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
                      {parseResult.endpoints.map((ep) => {
                        const isChecked = Boolean(selectedEndpoints[ep.name]);
                        return (
                          <div
                            key={ep.name}
                            className={`${styles.endpointItem} ${isChecked ? styles.endpointSelected : ''}`}
                            onClick={() => setSelectedEndpoints((prev) => ({ ...prev, [ep.name]: !prev[ep.name] }))}
                          >
                            <div className={styles.endpointInfo}>
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={() => { }}
                              />
                              <span className={`${styles.methodBadge} ${getMethodClass(ep.method)}`}>
                                {ep.method}
                              </span>
                              <div>
                                <div className={styles.endpointPath}>{ep.path}</div>
                                <div className={styles.endpointSummary}>{ep.display_name}</div>
                              </div>
                            </div>
                            <span className={styles.versionTag}>
                              {Object.keys(ep.parameters_schema?.properties || {}).length} 參數
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </>
              )}
            </div>
            <div className={styles.modalFooter}>
              <Button variant="secondary" onClick={() => setImportModalOpen(false)}>
                取消
              </Button>
              {!parseResult ? (
                <Button
                  variant="primary"
                  onClick={handleParseSpec}
                  disabled={parsing}
                  startIcon={parsing ? <Spinner size="sm" /> : <Icon name="search" size={16} />}
                >
                  {parsing ? '正在解析規格...' : '解析規格'}
                </Button>
              ) : (
                <Button
                  variant="primary"
                  onClick={handleExecuteImport}
                  disabled={importing}
                  startIcon={importing ? <Spinner size="sm" /> : <Icon name="check" size={16} />}
                >
                  {importing ? '正在匯入中...' : `確認匯入 (${Object.values(selectedEndpoints).filter(Boolean).length})`}
                </Button>
              )}
            </div>
          </div>
        </div>
      )}
      {/* 6. 手動新增 / 編輯自訂 API Modal */}
      {toolModalOpen && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalCard}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>
                {editingTool ? '編輯自訂 API 工具' : '手動建立自訂 API 工具'}
              </div>
              <button
                type="button"
                style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
                onClick={() => setToolModalOpen(false)}
              >
                <Icon name="close" size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveTool}>
              <div className={styles.modalBody}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>工具識別碼 (英文小寫與底線，供 LLM 調用)*：</label>
                    <input
                      type="text"
                      className={styles.formInput}
                      placeholder="例如 get_user_profile"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>顯示名稱 (繁體中文)*：</label>
                    <input
                      type="text"
                      className={styles.formInput}
                      placeholder="例如 查詢使用者個人檔案"
                      value={formData.display_name}
                      onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                      required
                    />
                  </div>
                </div>
                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>工具用途描述 (詳細說明工具功能與調用時機，供 AI 意圖匹配)*：</label>
                  <textarea
                    className={styles.formInput}
                    style={{ minHeight: '60px' }}
                    placeholder="例如：當使用者需要查詢特定 ID 的用戶基本資料時調用。"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    required
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '16px' }}>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>HTTP 方法：</label>
                    <select
                      className={styles.formSelect}
                      value={formData.method}
                      onChange={(e) => setFormData({ ...formData, method: e.target.value })}
                    >
                      <option value="GET">GET</option>
                      <option value="POST">POST</option>
                      <option value="PUT">PUT</option>
                      <option value="DELETE">DELETE</option>
                      <option value="PATCH">PATCH</option>
                    </select>
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>請求完整 URL (支援 &#123;param&#125; 路徑變數)*：</label>
                    <input
                      type="text"
                      className={styles.formInput}
                      placeholder="例如 https://api.example.com/users/{userId}"
                      value={formData.url}
                      onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                      required
                    />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>認證方式：</label>
                    <select
                      className={styles.formSelect}
                      value={formData.auth_type}
                      onChange={(e) => setFormData({ ...formData, auth_type: e.target.value })}
                    >
                      <option value="none">無認證 (None)</option>
                      <option value="bearer">Bearer Token</option>
                      <option value="api_key">API Key (Header)</option>
                    </select>
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>認證金鑰 / Token：</label>
                    <input
                      type="password"
                      className={styles.formInput}
                      placeholder="例如 token_abc123"
                      value={formData.auth_token}
                      onChange={(e) => setFormData({ ...formData, auth_token: e.target.value })}
                    />
                  </div>
                </div>
                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>參數 JSON Schema 定義 (Parameters Schema)：</label>
                  <textarea
                    className={styles.formTextarea}
                    style={{ minHeight: '140px' }}
                    value={formData.parameters_json}
                    onChange={(e) => setFormData({ ...formData, parameters_json: e.target.value })}
                  />
                </div>
              </div>
              <div className={styles.modalFooter}>
                <Button variant="secondary" type="button" onClick={() => setToolModalOpen(false)}>
                  取消
                </Button>
                <Button variant="primary" type="submit" startIcon={<Icon name="save" size={16} />}>
                  {editingTool ? '儲存變更' : '建立工具'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* 7. 自訂 API 線上即時測試 Modal */}
      {testModalOpen && testingTool && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalCard}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>
                即時線上測試：{testingTool.display_name} ({testingTool.name})
              </div>
              <button
                type="button"
                style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
                onClick={() => setTestModalOpen(false)}
              >
                <Icon name="close" size={20} />
              </button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.specBlock}>
                <div className={styles.specLabel}>
                  <span className={`${styles.methodBadge} ${getMethodClass(testingTool.method)}`}>
                    {testingTool.method}
                  </span>
                  <span>{testingTool.url}</span>
                </div>
              </div>
              <div className={styles.formGroup}>
                <label className={styles.formLabel}>測試輸入參數 (Arguments)：</label>
                {Object.keys(testingTool.parameters_schema?.properties || {}).length === 0 ? (
                  <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>此 API 無須輸入額外參數</p>
                ) : (
                  Object.entries(testingTool.parameters_schema?.properties || {}).map(([pName, pObj]) => (
                    <div key={pName} style={{ marginBottom: '8px' }}>
                      <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-medium)' }}>
                        {pName} {testingTool.parameters_schema?.required?.includes(pName) && <span style={{ color: 'var(--color-error)' }}>*</span>}:
                        <span style={{ color: 'var(--text-tertiary)', marginLeft: '6px' }}>({pObj.description || pObj.type})</span>
                      </label>
                      <input
                        type="text"
                        className={styles.formInput}
                        placeholder={`請輸入 ${pName}`}
                        value={testArgs[pName] || ''}
                        onChange={(e) => setTestArgs({ ...testArgs, [pName]: e.target.value })}
                      />
                    </div>
                  ))
                )}
              </div>
              {testResult && (
                <div className={styles.formGroup}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <label className={styles.formLabel}>API 回應結果 (Response)：</label>
                    <span style={{ fontSize: 'var(--font-size-xs)', color: testResult.is_success ? 'var(--color-success)' : 'var(--color-error)' }}>
                      狀態碼: {testResult.status_code} | 耗時: {testResult.duration_seconds}s
                    </span>
                  </div>
                  <pre className={styles.jsonViewer}>
                    {typeof testResult.data === 'object'
                      ? JSON.stringify(testResult.data, null, 2)
                      : String(testResult.data || testResult.error || '')}
                  </pre>
                </div>
              )}
            </div>
            <div className={styles.modalFooter}>
              <Button variant="secondary" onClick={() => setTestModalOpen(false)}>
                關閉
              </Button>
              <Button
                variant="primary"
                onClick={handleRunTest}
                disabled={testing}
                startIcon={testing ? <Spinner size="sm" /> : <Icon name="send" size={16} />}
              >
                {testing ? '正在發送請求...' : '發送測試請求'}
              </Button>
            </div>
          </div>
        </div>
      )}
      {/* 通知提示 */}
      <Snackbar
        open={snackbar.open}
        message={snackbar.message}
        severity={snackbar.severity}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      />
    </div>
  );
}