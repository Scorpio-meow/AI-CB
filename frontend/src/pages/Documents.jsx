import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
  Chip,
  LinearProgress,
  Divider
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Delete as DeleteIcon,
  Description as DocumentIcon,
  Cancel as CancelIcon,
  Build as RebuildIcon
} from '@mui/icons-material';
import axios from 'axios';
import api from '../services/api';

// 記憶體快取（3分鐘 TTL）
const documentsCache = {
  data: null,
  timestamp: 0
};
const CACHE_TTL = 3 * 60 * 1000; // 3 分鐘

// 請求去重標記
let loadingPromise = null;

function Documents() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadItems, setUploadItems] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uploadDialog, setUploadDialog] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [deletingStatus, setDeletingStatus] = useState({});
  const [confirmRemoveOpen, setConfirmRemoveOpen] = useState(false);
  const [rebuildLoading, setRebuildLoading] = useState(false);
  const [rebuildDialog, setRebuildDialog] = useState(false);

  // AbortController ref
  const loadAbortControllerRef = useRef(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    loadDocuments();

    // Cleanup on unmount
    return () => {
      isMountedRef.current = false;
      // 不要在組件卸載時取消請求，讓請求自然完成
      // if (loadAbortControllerRef.current) {
      //   loadAbortControllerRef.current.abort();
      // }
    };
  }, []);

  const loadDocuments = async (force = false) => {
    // 請求去重：如果已有進行中的請求，直接返回該 Promise
    if (loadingPromise && !force) {
      return loadingPromise;
    }

    // 檢查快取（僅在非強制刷新時）
    const now = Date.now();
    if (!force && documentsCache.data && (now - documentsCache.timestamp) < CACHE_TTL) {
      setDocuments(documentsCache.data);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError('');

    // 取消之前的請求
    if (loadAbortControllerRef.current) {
      loadAbortControllerRef.current.abort();
    }

    // 創建新的 AbortController
    loadAbortControllerRef.current = new AbortController();
    const timeoutId = setTimeout(() => {
      if (loadAbortControllerRef.current) {
        loadAbortControllerRef.current.abort();
      }
    }, 120000); // 120 秒超時，給 DevTunnels + token refresh + CORS preflight 充足時間

    loadingPromise = (async () => {
      try {
        const response = await api.get('/documents/', {  // 修正：加上 trailing slash 避免 307 redirect
          signal: loadAbortControllerRef.current.signal
        });

        // 只有當組件還在時才更新狀態
        if (!isMountedRef.current) return;

        // 更新快取
        documentsCache.data = response.data;
        documentsCache.timestamp = Date.now();

        setDocuments(response.data);
        setError('');
      } catch (err) {
        if (!isMountedRef.current) return;

        // 只有真正的超時才顯示超時錯誤
        if (err.name === 'AbortError' || err.name === 'CanceledError') {
          // 不顯示錯誤，讓使用者可以重試
          if (import.meta.env.DEV) console.debug('Documents loading was cancelled', err);
          setError('載入文檔超時，請重新整理頁面或檢查網路連線');
        } else if (err.response?.status === 400) {
          setError('載入文檔失敗：請求格式錯誤或授權無效，請嘗試重新登入');
          console.error('Load documents 400 error:', err.response?.data);
        } else {
          setError('載入文檔失敗：' + (err.response?.data?.detail || err.message || '未知錯誤'));
          console.error('Load documents error:', err);
        }
      } finally {
        clearTimeout(timeoutId);
        if (isMountedRef.current) {
          setLoading(false);
        }
        loadingPromise = null;
      }
    })();

    return loadingPromise;
  };

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    const allowedTypes = ['text/plain', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const maxSize = 50 * 1024 * 1024; // 50MB

    const accepted = [];
    for (const file of files) {
      if (!allowedTypes.includes(file.type)) {
        setError('不支援的文件類型。請上傳 .txt, .pdf 或 .docx 文件');
        return;
      }
      if (file.size > maxSize) {
        setError('文件大小不能超過 50MB');
        return;
      }
      accepted.push(file);
    }

    setSelectedFiles(accepted);
    // prepare upload items
    const items = accepted.map((f) => ({ file: f, progress: 0, status: 'ready', controller: null, detail: null }));
    setUploadItems(items);
    setError('');
  };

  const uploadSingle = async (index) => {
    const item = uploadItems[index];
    if (!item) return;

    const controller = new AbortController();

    // mark uploading and attach controller
    setUploadItems((prev) => {
      const next = prev.slice();
      next[index] = { ...next[index], status: 'uploading', controller, progress: 0, detail: null };
      return next;
    });

    const formData = new FormData();
    formData.append('file', item.file);

    try {
      const response = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        signal: controller.signal,
        onUploadProgress: (e) => {
          if (e.lengthComputable) {
            const p = Math.round((e.loaded * 100) / e.total);
            setUploadItems((prev) => {
              const next = prev.slice();
              next[index] = { ...next[index], progress: p };
              return next;
            });
          }
        }
      });

      // backend returns results array
      const res = response.data?.results?.[0];
      if (res && res.status === 'success') {
        setUploadItems((prev) => {
          const next = prev.slice();
          next[index] = { ...next[index], status: 'success', progress: 100, detail: null };
          return next;
        });
      } else {
        setUploadItems((prev) => {
          const next = prev.slice();
          next[index] = { ...next[index], status: 'failed', detail: res?.detail || '上傳失敗' };
          return next;
        });
      }

    } catch (err) {
      if (axios.isCancel && axios.isCancel(err)) {
        setUploadItems((prev) => {
          const next = prev.slice();
          next[index] = { ...next[index], status: 'canceled', detail: '已取消' };
          return next;
        });
      } else if (err.name === 'CanceledError') {
        setUploadItems((prev) => {
          const next = prev.slice();
          next[index] = { ...next[index], status: 'canceled', detail: '已取消' };
          return next;
        });
      } else {
        setUploadItems((prev) => {
          const next = prev.slice();
          next[index] = { ...next[index], status: 'failed', detail: err.response?.data?.detail || err.message };
          return next;
        });
      }
      console.error('Upload error:', err);
    }
  };

  const startUpload = async () => {
    if (!selectedFiles || selectedFiles.length === 0) {
      setError('請選擇文件');
      return;
    }
    setUploadLoading(true);
    // sequential upload; could be parallelized if desired
    for (let i = 0; i < uploadItems.length; i++) {
      // skip already successful
      const it = uploadItems[i];
      if (!it) continue;
      if (it.status === 'success') continue;
      // await uploadSingle for sequential behavior
      await uploadSingle(i);
    }

    setUploadLoading(false);
    // refresh document list after uploads finish
    loadDocuments();
  };

  const cancelAllUploads = () => {
    // Abort any active per-file controllers
    setUploadItems((prev) => {
      for (const it of prev) {
        if (it && it.controller) {
          try {
            it.controller.abort();
          } catch (e) {
            console.error('Cancel error', e);
          }
        }
      }
      return prev.map((it) => (it ? { ...it, status: it.status === 'uploading' ? 'canceled' : it.status } : it));
    });
    setUploadLoading(false);
    setSuccess('已取消全部上傳');
    setSelectedFiles([]);
    setUploadItems([]);
    setUploadDialog(false);
  };

  const cancelUpload = (index) => {
    const it = uploadItems[index];
    if (!it || !it.controller) return;
    try {
      it.controller.abort();
    } catch (err) {
      if (err.name === 'AbortError' || err.name === 'CanceledError') {
        if (import.meta.env.DEV) console.debug('Upload was cancelled', err);
      } else {
        setError('取消上傳失敗');
      }
    }
    setUploadItems((prev) => {
      const next = prev.slice();
      next[index] = { ...next[index], status: 'canceled', detail: '已取消' };
      return next;
    });
  };

  const removeSelectedFiles = () => {
    if (uploadLoading) {
      setError('正在上傳中，請先取消上傳後再移除檔案');
      return;
    }
    setConfirmRemoveOpen(true);
  };

  const confirmRemoveSelectedFiles = () => {
    setSelectedFiles([]);
    setUploadItems([]);
    setError('');
    setConfirmRemoveOpen(false);
  };

  const cancelRemove = () => {
    setConfirmRemoveOpen(false);
  };

  const removeFileAt = (index) => {
    const it = uploadItems[index];
    if (it && it.status === 'uploading') {
      setError('該檔案正在上傳，請先取消上傳後再移除');
      return;
    }
    if (!window.confirm('確定要從選取清單移除此檔案嗎？')) return;
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setUploadItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDelete = async (documentId, filename) => {
    if (!window.confirm(`確定要刪除文檔 "${filename}" 嗎？此操作不可逆！`)) return;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000); // 45 秒超時

    try {
      setDeletingStatus((prev) => ({ ...prev, [documentId]: 'deleting' }));
      await api.delete(`/documents/${documentId}`, { signal: controller.signal });
      setDeletingStatus((prev) => ({ ...prev, [documentId]: 'deleted' }));

      // 從列表中移除以提供快速 UX
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));

      // 清除快取
      documentsCache.data = null;
      documentsCache.timestamp = 0;

      setSuccess('文檔刪除成功');
    } catch (err) {
      console.error('刪除文檔錯誤:', err);
      setDeletingStatus((prev) => ({ ...prev, [documentId]: 'failed' }));

      if (err.name === 'AbortError' || err.name === 'CanceledError') {
        setError('刪除文檔超時，請稍後再試');
      } else {
        setError('刪除文檔失敗: ' + (err.response?.data?.detail || err.message));
      }
    } finally {
      clearTimeout(timeoutId);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileTypeLabel = (contentType) => {
    switch (contentType) {
      case 'text/plain':
        return 'TXT';
      case 'application/pdf':
        return 'PDF';
      case 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        return 'DOCX';
      default:
        return '未知';
    }
  };

  const handleRebuildIndex = async () => {
    setRebuildDialog(false);
    setRebuildLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await api.post('/documents/rebuild-index');
      const data = response.data;

      // 顯示詳細的重建結果
      const messageParts = [
        `索引重建成功！`,
        `文檔: ${data.document_count || 0}`,
        `向量塊: ${data.chunk_count || 0}`,
        `配置: ${data.chunk_size || '?'}/${data.chunk_overlap || '?'}`
      ];

      // 如果檢測到 QA 對，添加到訊息中
      if (data.qa_pairs_detected && data.qa_pairs_detected > 0) {
        messageParts.push(`Q&A對: ${data.qa_pairs_detected}`);
      }

      setSuccess(messageParts.join(' | '));

      // 重建後重新載入文檔列表
      await loadDocuments(true);
    } catch (err) {
      console.error('重建索引錯誤:', err);
      setError('重建索引失敗: ' + (err.response?.data?.detail || err.message || '未知錯誤'));
    } finally {
      setRebuildLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="50vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          知識庫管理
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<RebuildIcon />}
            onClick={() => setRebuildDialog(true)}
            disabled={rebuildLoading}
          >
            {rebuildLoading ? '重建中...' : '重建索引'}
          </Button>
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={() => setUploadDialog(true)}
          >
            上傳文檔
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      <Paper>
        <Box display="flex" alignItems="center" justifyContent="space-between" sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6">
            已上傳的文檔 ({documents.length})
          </Typography>
          <Box>
            {/* Bulk delete removed - users should delete individually */}
          </Box>
        </Box>

        {documents.length === 0 ? (
          <Box p={4} textAlign="center">
            <DocumentIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              還沒有上傳任何文檔
            </Typography>
            <Typography variant="body2" color="text.secondary">
              開始上傳文檔來建立您的知識庫
            </Typography>
          </Box>
        ) : (
          <List>
            {documents.map((doc, index) => (
              <React.Fragment key={doc.id}>
                <ListItem>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <DocumentIcon color="primary" />
                        <Typography variant="subtitle1">{doc.filename}</Typography>
                        <Chip
                          label={getFileTypeLabel(doc.file_type)}
                          size="small"
                          variant="outlined"
                        />
                        {doc.is_processed && (
                          <Chip
                            label="已處理"
                            size="small"
                            color="success"
                            variant="outlined"
                          />
                        )}
                      </Box>
                    }
                    secondary={
                      <React.Fragment>
                        <Typography variant="body2" color="text.secondary" component="span" display="block">
                          上傳時間: {new Date(doc.created_at).toLocaleString('zh-TW')}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" component="span" display="block">
                          文件類型: {doc.file_type}
                        </Typography>
                      </React.Fragment>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Box display="flex" alignItems="center" gap={1}>
                      {deletingStatus[doc.id] === 'deleting' && (
                        <Chip label="刪除中" size="small" color="warning" />
                      )}
                      {deletingStatus[doc.id] === 'deleted' && (
                        <Chip label="已刪除" size="small" color="success" />
                      )}
                      {deletingStatus[doc.id] === 'failed' && (
                        <Chip label="刪除失敗" size="small" color="error" />
                      )}
                      <IconButton
                        edge="end"
                        onClick={() => handleDelete(doc.id, doc.filename)}
                        color="error"
                        disabled={deletingStatus[doc.id] === 'deleting'}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                  </ListItemSecondaryAction>
                </ListItem>
                {index < documents.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        )}
      </Paper>

      {/* 上傳對話框 */}
      <Dialog
        open={uploadDialog}
        onClose={() => setUploadDialog(false)}
        maxWidth="sm"
        fullWidth
        disableRestoreFocus
        aria-labelledby="upload-dialog-title"
      >
        <DialogTitle id="upload-dialog-title">上傳文檔到知識庫</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <input
              accept=".txt,.pdf,.docx"
              style={{ display: 'none' }}
              id="file-upload"
              type="file"
              multiple
              onChange={handleFileSelect}
            />
            <Box display="flex" gap={1}>
              <label htmlFor="file-upload" style={{ flex: 1 }}>
                <Button
                  variant="outlined"
                  component="span"
                  startIcon={<UploadIcon />}
                  fullWidth
                  sx={{ mb: 2 }}
                >
                  選擇文件
                </Button>
              </label>
              <Button variant="outlined" color="inherit" onClick={removeSelectedFiles} sx={{ mb: 2 }}>
                移除檔案
              </Button>
            </Box>

            {selectedFiles && selectedFiles.length > 0 && (
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <Typography variant="subtitle2" gutterBottom>
                  已選擇的文件 ({selectedFiles.length}):
                </Typography>
                {selectedFiles.map((f, idx) => {
                  const item = uploadItems[idx] || { progress: 0, status: 'ready', detail: null };
                  return (
                    <Box key={idx} sx={{ mb: 1 }}>
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Box>
                          <Typography variant="body2">
                            <strong>文件名:</strong> {f.name}
                          </Typography>
                          <Typography variant="body2">
                            <strong>大小:</strong> {formatFileSize(f.size)}
                          </Typography>
                          <Typography variant="body2">
                            <strong>類型:</strong> {getFileTypeLabel(f.type)}
                          </Typography>
                        </Box>
                        <Box display="flex" alignItems="center" gap={1}>
                          <Chip label={item.status} size="small" />
                          <IconButton size="small" onClick={() => removeFileAt(idx)}>
                            <DeleteIcon />
                          </IconButton>
                        </Box>
                      </Box>
                      <Box sx={{ mt: 1 }}>
                        <LinearProgress variant={item.status === 'uploading' ? 'determinate' : 'determinate'} value={item.progress} />
                        <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mt: 0.5 }}>
                          <Typography variant="caption">{item.progress}%</Typography>
                          <Box>
                            {item.status === 'uploading' && (
                              <IconButton size="small" onClick={() => cancelUpload(idx)}>
                                <CancelIcon />
                              </IconButton>
                            )}
                          </Box>
                        </Box>
                      </Box>
                      {idx < selectedFiles.length - 1 && <Divider sx={{ my: 1 }} />}
                    </Box>
                  );
                })}
              </Paper>
            )}

            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              支援的文件格式: .txt, .pdf, .docx
              <br />
              最大文件大小: 50MB
            </Typography>

            {/* per-file progress is shown above; no global progress required */}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setUploadDialog(false)}
            disabled={uploadLoading}
          >
            取消
          </Button>
          <Button onClick={cancelAllUploads} disabled={!uploadLoading}>
            取消全部上傳
          </Button>
          <Button
            onClick={startUpload}
            variant="contained"
            disabled={(!selectedFiles || selectedFiles.length === 0) || uploadLoading}
          >
            {uploadLoading ? '上傳中...' : '上傳'}
          </Button>
        </DialogActions>
      </Dialog>
      {/* 移除檔案確認對話框 */}
      <Dialog
        open={confirmRemoveOpen}
        onClose={cancelRemove}
        disableRestoreFocus
        aria-labelledby="confirm-remove-dialog-title"
      >
        <DialogTitle id="confirm-remove-dialog-title">確認移除所選檔案？</DialogTitle>
        <DialogContent>
          <Typography>此操作將清除目前選取的檔案。確定要移除嗎？</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelRemove}>取消</Button>
          <Button onClick={confirmRemoveSelectedFiles} variant="contained" color="error">確定移除</Button>
        </DialogActions>
      </Dialog>

      {/* 重建索引確認對話框 */}
      <Dialog
        open={rebuildDialog}
        onClose={() => !rebuildLoading && setRebuildDialog(false)}
        disableRestoreFocus
        aria-labelledby="rebuild-dialog-title"
      >
        <DialogTitle id="rebuild-dialog-title">確認重建知識庫索引？</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>
            此操作將重新建立所有文檔的向量索引和 BM25 索引。
          </Typography>
          <Typography variant="body2" color="text.secondary">
            • 適用於索引損壞或不一致時
          </Typography>
          <Typography variant="body2" color="text.secondary">
            • 處理時間取決於文檔數量
          </Typography>
          <Typography variant="body2" color="text.secondary">
            • 重建期間可能影響查詢性能
          </Typography>
          {rebuildLoading && (
            <Box sx={{ mt: 2 }}>
              <LinearProgress />
              <Typography variant="body2" sx={{ mt: 1 }} align="center">
                正在重建索引，請稍候...
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRebuildDialog(false)} disabled={rebuildLoading}>
            取消
          </Button>
          <Button
            onClick={handleRebuildIndex}
            variant="contained"
            color="primary"
            disabled={rebuildLoading}
          >
            確認重建
          </Button>
        </DialogActions>
      </Dialog>
      {/* Bulk delete UI removed */}
    </Box>
  );
}

export default Documents;