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
import { useDocuments } from '../hooks/useDocuments';

// 記憶體快取（3分鐘 TTL）
const documentsCache = {
  data: null,
  timestamp: 0
};

const createUploadItem = (file) => ({
  file,
  progress: 0,
  status: 'ready',
  controller: null,
  detail: null
});

function Documents() {
  const {
    documents,
    loading,
    error: docError,
    fetchDocuments,
    deleteDocument
  } = useDocuments();

  const [localError, setLocalError] = useState('');
  const [success, setSuccess] = useState('');
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadItems, setUploadItems] = useState([]);
  const [uploadDialog, setUploadDialog] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [deletingStatus, setDeletingStatus] = useState({});
  const [confirmRemoveOpen, setConfirmRemoveOpen] = useState(false);
  const [rebuildLoading, setRebuildLoading] = useState(false);
  const [rebuildDialog, setRebuildDialog] = useState(false);

  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    fetchDocuments();

    return () => {
      isMountedRef.current = false;
    };
  }, [fetchDocuments]);

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    const allowedTypes = ['text/plain', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const maxSize = 50 * 1024 * 1024; // 50MB

    const accepted = [];
    for (const file of files) {
      if (!allowedTypes.includes(file.type)) {
        setLocalError('不支援的文件類型。請上傳 .txt, .pdf 或 .docx 文件');
        return;
      }
      if (file.size > maxSize) {
        setLocalError('文件大小不能超過 50MB');
        return;
      }
      accepted.push(file);
    }

    setSelectedFiles(accepted);
    const items = accepted.map(createUploadItem);
    setUploadItems(items);
    setLocalError('');
  };

  const uploadSingle = async (item, index) => {
    if (!item) return 'skipped';

    const controller = new AbortController();

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
          if (e.lengthComputable && e.total) {
            const p = Math.round((e.loaded * 100) / e.total);
            setUploadItems((prev) => {
              const next = prev.slice();
              next[index] = { ...next[index], progress: p };
              return next;
            });
          }
        }
      });

      const res = response.data?.results?.[0];
      if (res && res.status === 'success') {
        setUploadItems((prev) => {
          const next = prev.slice();
          next[index] = { ...next[index], status: 'success', progress: 100, detail: null };
          return next;
        });
        return 'success';
      } else {
        setUploadItems((prev) => {
          const next = prev.slice();
          next[index] = { ...next[index], status: 'failed', detail: res?.detail || '上傳失敗' };
          return next;
        });
        return 'failed';
      }

    } catch (err) {
      console.error('Upload error:', err);
      if (axios.isCancel && axios.isCancel(err)) {
        setUploadItems((prev) => {
          const next = prev.slice();
          next[index] = { ...next[index], status: 'canceled', detail: '已取消' };
          return next;
        });
        return 'canceled';
      } else if (err.name === 'CanceledError') {
        setUploadItems((prev) => {
          const next = prev.slice();
          next[index] = { ...next[index], status: 'canceled', detail: '已取消' };
          return next;
        });
        return 'canceled';
      } else {
        setUploadItems((prev) => {
          const next = prev.slice();
          next[index] = { ...next[index], status: 'failed', detail: err.response?.data?.detail || err.message };
          return next;
        });
        return 'failed';
      }
    }
  };

  const startUpload = async () => {
    if (!selectedFiles || selectedFiles.length === 0) {
      setLocalError('請選擇文件');
      return;
    }
    setUploadLoading(true);
    setLocalError('');
    setSuccess('');

    const itemsToUpload = uploadItems.slice();
    let successCount = 0;
    let failedCount = 0;
    let canceledCount = 0;

    for (let i = 0; i < itemsToUpload.length; i++) {
      const it = itemsToUpload[i];
      if (!it) continue;
      if (it.status === 'success') continue;
      const result = await uploadSingle(it, i);
      if (result === 'success') successCount += 1;
      if (result === 'failed') failedCount += 1;
      if (result === 'canceled') canceledCount += 1;
    }

    setUploadLoading(false);
    documentsCache.data = null;
    documentsCache.timestamp = 0;
    await fetchDocuments();

    setSelectedFiles([]);
    setUploadItems([]);
    setUploadDialog(false);

    if (successCount > 0) {
      const summary = [`成功 ${successCount} 個`];
      if (failedCount > 0) summary.push(`失敗 ${failedCount} 個`);
      if (canceledCount > 0) summary.push(`取消 ${canceledCount} 個`);
      setSuccess(`文件上傳完成：${summary.join('，')}`);
    } else if (failedCount > 0 || canceledCount > 0) {
      const summary = [];
      if (failedCount > 0) summary.push(`失敗 ${failedCount} 個`);
      if (canceledCount > 0) summary.push(`取消 ${canceledCount} 個`);
      setLocalError(`文件未成功上傳：${summary.join('，')}`);
    }
  };

  const cancelAllUploads = () => {
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
      if (err.name !== 'AbortError' && err.name !== 'CanceledError') {
        setLocalError('取消上傳失敗');
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
      setLocalError('正在上傳中，請先取消上傳後再移除檔案');
      return;
    }
    setConfirmRemoveOpen(true);
  };

  const confirmRemoveSelectedFiles = () => {
    setSelectedFiles([]);
    setUploadItems([]);
    setLocalError('');
    setConfirmRemoveOpen(false);
  };

  const cancelRemove = () => {
    setConfirmRemoveOpen(false);
  };

  const removeFileAt = (index) => {
    const it = uploadItems[index];
    if (it && it.status === 'uploading') {
      setLocalError('該檔案正在上傳，請先取消上傳後再移除');
      return;
    }
    if (!window.confirm('確定要從選取清單移除此檔案嗎？')) return;
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setUploadItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDelete = async (documentId, filename) => {
    if (!window.confirm(`確定要刪除文檔 "${filename}" 嗎？此操作不可逆！`)) return;

    try {
      setDeletingStatus((prev) => ({ ...prev, [documentId]: 'deleting' }));
      await deleteDocument(documentId);
      setDeletingStatus((prev) => ({ ...prev, [documentId]: 'deleted' }));
      setSuccess('文檔刪除成功');
    } catch (err) {
      console.error('刪除文檔錯誤:', err);
      setDeletingStatus((prev) => ({ ...prev, [documentId]: 'failed' }));
      setLocalError('刪除文檔失敗: ' + (err.message || '未知錯誤'));
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
    setLocalError('');
    setSuccess('');

    try {
      const response = await api.post('/documents/rebuild-index');
      const data = response.data;

      const messageParts = [
        `索引重建成功！`,
        `文檔: ${data.document_count || 0}`,
        `向量塊: ${data.chunk_count || 0}`,
        `配置: ${data.chunk_size || '?'}/${data.chunk_overlap || '?'}`
      ];

      if (data.qa_pairs_detected && data.qa_pairs_detected > 0) {
        messageParts.push(`Q&A對: ${data.qa_pairs_detected}`);
      }

      setSuccess(messageParts.join(' | '));
      await fetchDocuments();
    } catch (err) {
      console.error('重建索引錯誤:', err);
      setLocalError('重建索引失敗: ' + (err.response?.data?.detail || err.message || '未知錯誤'));
    } finally {
      setRebuildLoading(false);
    }
  };

  const error = localError || docError;

  if (loading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "50vh"
        }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{
      p: 3
    }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3
        }}>
        <Typography variant="h4" component="h1">
          知識庫管理
        </Typography>
        <Box
          sx={{
            display: "flex",
            gap: 2
          }}>
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
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setLocalError('')}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}
      <Paper>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            p: 2,
            borderBottom: 1,
            borderColor: 'divider'
          }}>
          <Typography variant="h6">
            已上傳的文檔 ({documents.length})
          </Typography>
        </Box>

        {documents.length === 0 ? (
          <Box
            sx={{
              p: 4,
              textAlign: "center"
            }}>
            <DocumentIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom sx={{
              color: "text.secondary"
            }}>
              還沒有上傳任何文檔
            </Typography>
            <Typography variant="body2" sx={{
              color: "text.secondary"
            }}>
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
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 1
                        }}>
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
                        <Typography
                          variant="body2"
                          component="span"
                          sx={{
                            color: "text.secondary",
                            display: "block"
                          }}>
                          上傳時間: {new Date(doc.created_at).toLocaleString('zh-TW')}
                        </Typography>
                        <Typography
                          variant="body2"
                          component="span"
                          sx={{
                            color: "text.secondary",
                            display: "block"
                          }}>
                          文件類型: {doc.file_type}
                        </Typography>
                      </React.Fragment>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1
                      }}>
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
            <Box
              sx={{
                display: "flex",
                gap: 1
              }}>
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
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center"
                        }}>
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
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 1
                          }}>
                          <Chip label={item.status} size="small" />
                          <IconButton size="small" onClick={() => removeFileAt(idx)}>
                            <DeleteIcon />
                          </IconButton>
                        </Box>
                      </Box>
                      <Box sx={{ mt: 1 }}>
                        <LinearProgress variant="determinate" value={item.progress} />
                        <Box
                          sx={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            mt: 0.5
                          }}>
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

            <Typography
              variant="body2"
              sx={{
                color: "text.secondary",
                mt: 2
              }}>
              支援的文件格式: .txt, .pdf, .docx
              <br />
              最大文件大小: 50MB
            </Typography>
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
          <Typography variant="body2" sx={{
            color: "text.secondary"
          }}>
            • 適用於索引損壞或不一致時
          </Typography>
          <Typography variant="body2" sx={{
            color: "text.secondary"
          }}>
            • 處理時間取決於文檔數量
          </Typography>
          <Typography variant="body2" sx={{
            color: "text.secondary"
          }}>
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
    </Box>
  );
}

export default Documents;