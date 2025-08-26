import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Checkbox,
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
  Cancel as CancelIcon
} from '@mui/icons-material';
import axios from 'axios';

function Documents() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadItems, setUploadItems] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uploadDialog, setUploadDialog] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [bulkDeleteConfirmOpen, setBulkDeleteConfirmOpen] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [deletingStatus, setDeletingStatus] = useState({});
  const [confirmRemoveOpen, setConfirmRemoveOpen] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/documents/');
  // Ensure documents is always an array to avoid runtime errors when mapping
  const docs = Array.isArray(response.data) ? response.data : (response.data ? [response.data] : []);
  setDocuments(docs);
      setError('');
    } catch (err) {
      setError('載入文檔失敗');
      console.error('Load documents error:', err);
    } finally {
      setLoading(false);
    }
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
      const response = await axios.post('/api/documents/upload', formData, {
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
      // eslint-disable-next-line no-await-in-loop
      await uploadSingle(i);
    }

    setUploadLoading(false);
    // refresh document list after uploads finish
    loadDocuments();
  };

  const cancelUpload = (index) => {
    const it = uploadItems[index];
    if (!it || !it.controller) return;
    try {
      it.controller.abort();
    } catch (e) {
      console.error('Cancel error', e);
    }
    // controller abort will trigger catch and set status
  };

  const cancelAllUploads = () => {
    // abort any active controllers
    setUploadItems((prev) => {
      for (const it of prev) {
        if (it && it.controller && it.status === 'uploading') {
          try {
            it.controller.abort();
          } catch (e) {
            console.error('Cancel all error', e);
          }
        }
      }
      return [];
    });

    // clear selection and UI
    setSelectedFiles([]);
    setUploadLoading(false);
    setError('');
    setUploadDialog(false);
    setSuccess('上傳已取消');
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
    try {
      setDeletingStatus((prev) => ({ ...prev, [documentId]: 'deleting' }));
      await axios.delete(`/api/documents/${documentId}`);
      setDeletingStatus((prev) => ({ ...prev, [documentId]: 'deleted' }));
      // remove from list immediately for fast UX
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
      setSelectedDocIds((prev) => prev.filter((id) => id !== documentId));
      setSuccess('文檔刪除成功');
    } catch (err) {
      console.error('刪除文檔錯誤:', err);
      setDeletingStatus((prev) => ({ ...prev, [documentId]: 'failed' }));
      setError('刪除文檔失敗: ' + (err.response?.data?.detail || err.message));
    }
  };

  const toggleSelectDoc = (documentId) => {
    setSelectedDocIds((prev) => {
      if (prev.includes(documentId)) return prev.filter((id) => id !== documentId);
      return [...prev, documentId];
    });
  };

  const openBulkDeleteConfirm = () => {
    if (!selectedDocIds || selectedDocIds.length === 0) return;
    setBulkDeleteConfirmOpen(true);
  };

  const cancelBulkDelete = () => setBulkDeleteConfirmOpen(false);

  const bulkDeleteSelected = async () => {
    if (!selectedDocIds || selectedDocIds.length === 0) return;
    setBulkDeleting(true);
    // mark all as deleting
    setDeletingStatus((prev) => {
      const next = { ...prev };
      for (const id of selectedDocIds) next[id] = 'deleting';
      return next;
    });

    const failed = [];
    for (const id of selectedDocIds) {
      try {
        await axios.delete(`/api/documents/${id}`);
        // mark deleted and remove from UI
        setDeletingStatus((prev) => ({ ...prev, [id]: 'deleted' }));
        setDocuments((prev) => prev.filter((d) => d.id !== id));
      } catch (err) {
        console.error('Bulk delete error for', id, err);
        failed.push(id);
        setDeletingStatus((prev) => ({ ...prev, [id]: 'failed' }));
      }
    }

    setBulkDeleting(false);
    setBulkDeleteConfirmOpen(false);
    if (failed.length === 0) {
      setSuccess('已刪除選取的文檔');
    } else {
      setError(`部分刪除失敗: ${failed.join(',')}`);
    }
    // remove deleted ids from selection
    setSelectedDocIds((prev) => prev.filter((id) => !(deletingStatus[id] === 'deleted')));
    // finally refresh list to sync with server
    loadDocuments();
    if (!selectedDocIds || selectedDocIds.length === 0) return;
    setBulkDeleting(true);
    // mark all as deleting
    setDeletingStatus((prev) => {
      const next = { ...prev };
      for (const id of selectedDocIds) next[id] = 'deleting';
      return next;
    });

    try {
      const response = await axios.post('/api/documents/bulk_delete', { ids: selectedDocIds });
      const results = response.data?.results || [];
      const failed = [];

      for (const r of results) {
        if (r.status === 'deleted') {
          setDeletingStatus((prev) => ({ ...prev, [r.id]: 'deleted' }));
          setDocuments((prev) => prev.filter((d) => d.id !== r.id));
        } else {
          failed.push(r.id);
          setDeletingStatus((prev) => ({ ...prev, [r.id]: 'failed' }));
        }
      }

      if (failed.length === 0) {
        setSuccess('已刪除選取的文檔');
      } else {
        setError(`部分刪除失敗: ${failed.join(',')}`);
      }
    } catch (err) {
      console.error('Bulk delete request failed', err);
      // mark all as failed
      setDeletingStatus((prev) => {
        const next = { ...prev };
        for (const id of selectedDocIds) next[id] = 'failed';
        return next;
      });
      setError('批次刪除失敗: ' + (err.response?.data?.detail || err.message));
    } finally {
      setBulkDeleting(false);
      setBulkDeleteConfirmOpen(false);
      // clear selection of those that were deleted
      setSelectedDocIds((prev) => prev.filter((id) => deletingStatus[id] !== 'deleted'));
      // sync with server for any unexpected differences
      loadDocuments();
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
        <Button
          variant="contained"
          startIcon={<UploadIcon />}
          onClick={() => setUploadDialog(true)}
        >
          上傳文檔
        </Button>
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
            已上傳的文檔 ({Array.isArray(documents) ? documents.length : 0})
          </Typography>
          <Box>
            <Button variant="outlined" color="error" onClick={openBulkDeleteConfirm} disabled={!selectedDocIds.length} sx={{ mr: 1 }}>
              刪除選取
            </Button>
          </Box>
        </Box>
        
  {(Array.isArray(documents) ? documents.length : 0) === 0 ? (
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
            {(Array.isArray(documents) ? documents : []).map((doc, index) => (
              <React.Fragment key={doc.id}>
                <ListItem>
                  <Checkbox checked={selectedDocIds.includes(doc.id)} onChange={() => toggleSelectDoc(doc.id)} />
                  <ListItemText
                    primaryTypographyProps={{ component: 'div' }}
                    secondaryTypographyProps={{ component: 'div' }}
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
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          上傳時間: {new Date(doc.created_at).toLocaleString('zh-TW')}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          文件類型: {doc.file_type}
                        </Typography>
                      </Box>
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
      >
        <DialogTitle>上傳文檔到知識庫</DialogTitle>
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
      <Dialog open={confirmRemoveOpen} onClose={cancelRemove}>
        <DialogTitle>確認移除所選檔案？</DialogTitle>
        <DialogContent>
          <Typography>此操作將清除目前選取的檔案。確定要移除嗎？</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelRemove}>取消</Button>
          <Button onClick={confirmRemoveSelectedFiles} variant="contained" color="error">確定移除</Button>
        </DialogActions>
      </Dialog>
      {/* 批量刪除確認 */}
      <Dialog open={bulkDeleteConfirmOpen} onClose={cancelBulkDelete}>
        <DialogTitle>確認刪除選取的文檔？</DialogTitle>
        <DialogContent>
          <Typography>將刪除 {selectedDocIds.length} 個檔案，操作不可逆，確定要刪除嗎？</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelBulkDelete}>取消</Button>
          <Button onClick={bulkDeleteSelected} variant="contained" color="error" disabled={bulkDeleting}>
            {bulkDeleting ? '刪除中...' : '確認刪除'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Documents;
