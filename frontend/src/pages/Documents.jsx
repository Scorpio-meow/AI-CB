import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import api from '../services/api';
import { useDocuments } from '../hooks/useDocuments';
import {
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Spinner,
  Alert,
  Chip,
  Icon
} from '../components/ui';
import styles from './Documents.module.css';
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
  const [isDragging, setIsDragging] = useState(false);
  const isMountedRef = useRef(true);
  const fileInputRef = useRef(null);

  useEffect(() => {
    isMountedRef.current = true;
    fetchDocuments();
    return () => {
      isMountedRef.current = false;
    };
  }, [fetchDocuments]);

  const processFiles = (files) => {
    if (!files || !files.length) return;
    const allowedExtensions = [
      '.txt', '.md', '.markdown', '.pdf', '.docx', '.pptx', '.xlsx',
      '.csv', '.json', '.yaml', '.yml', '.xml', '.html', '.htm', '.log',
      '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.sql',
      '.sh', '.ini', '.env'
    ];
    const allowedTypes = [
      'text/plain',
      'text/markdown',
      'text/x-markdown',
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/csv',
      'application/csv',
      'application/json',
      'text/json',
      'text/html',
      'text/xml',
      'application/xml',
      'text/yaml',
      'application/x-yaml'
    ];
    const maxSize = 50 * 1024 * 1024;
    const accepted = [];
    for (const file of files) {
      const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
      const isAllowed = allowedTypes.includes(file.type) || allowedExtensions.includes(ext) || file.type.startsWith('text/');
      if (!isAllowed) {
        setLocalError(`不支援的文件類型（${file.name}）。支援 PDF, Word, PPT, Excel, Markdown, CSV, JSON, HTML, 程式碼等文件`);
        return;
      }
      if (file.size > maxSize) {
        setLocalError(`文件大小不能超過 50MB（${file.name}）`);
        return;
      }
      // 避免在同一次選擇中加入重複檔案
      if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
        accepted.push(file);
      }
    }
    if (!accepted.length) return;
    setSelectedFiles((prev) => [...prev, ...accepted]);
    const items = accepted.map(createUploadItem);
    setUploadItems((prev) => [...prev, ...items]);
    setLocalError('');
  };

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files || []);
    processFiles(files);
    if (event.target) event.target.value = '';
  };

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(Array.from(e.dataTransfer.files));
    }
  };

  const getStatusChipProps = (status, detail) => {
    switch (status) {
      case 'uploading':
        return { label: '處理中', variant: 'primary', icon: <Spinner size={12} color="currentColor" /> };
      case 'success':
        return { label: '已入庫', variant: 'success', icon: <Icon name="check" size={12} /> };
      case 'failed':
        return { label: detail || '失敗', variant: 'error', icon: <Icon name="error" size={12} /> };
      case 'duplicate':
        return { label: '已存在', variant: 'warning', icon: <Icon name="warning" size={12} /> };
      case 'canceled':
        return { label: '已取消', variant: 'default' };
      case 'ready':
      default:
        return { label: '待上傳', variant: 'outline' };
    }
  };

  const getFileBadgeClass = (ext) => {
    const e = ext.toLowerCase();
    if (e === 'pdf') return styles.fileBadgePdf;
    if (e === 'docx' || e === 'doc') return styles.fileBadgeDocx;
    if (e === 'pptx' || e === 'ppt') return styles.fileBadgePptx;
    if (e === 'xlsx' || e === 'xls' || e === 'csv') return styles.fileBadgeXlsx;
    if (['py', 'js', 'ts', 'tsx', 'jsx', 'json', 'html', 'sql', 'sh', 'css'].includes(e)) return styles.fileBadgeCode;
    return styles.fileBadgeText;
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
  const getFileTypeLabel = (contentType, filename = '') => {
    const ext = filename ? ('.' + (filename.split('.').pop() || '').toLowerCase()) : '';
    if (ext === '.pdf' || contentType === 'application/pdf') return 'PDF';
    if (ext === '.docx' || contentType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') return 'DOCX';
    if (ext === '.pptx' || contentType === 'application/vnd.openxmlformats-officedocument.presentationml.presentation') return 'PPTX';
    if (ext === '.xlsx' || contentType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') return 'XLSX';
    if (ext === '.md' || ext === '.markdown' || contentType?.includes('markdown')) return 'MD';
    if (ext === '.csv' || contentType?.includes('csv')) return 'CSV';
    if (ext === '.json' || contentType?.includes('json')) return 'JSON';
    if (ext === '.html' || ext === '.htm' || contentType?.includes('html')) return 'HTML';
    if (['.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.sql', '.sh'].includes(ext)) return ext.slice(1).toUpperCase();
    if (ext === '.txt' || contentType === 'text/plain') return 'TXT';
    if (ext) return ext.slice(1).toUpperCase();
    return 'TXT';
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
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <Spinner size={36} color="var(--color-primary)" />
      </div>
    );
  }
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>知識庫管理</h1>
        <div className={styles.actions}>
          <Button
            variant="outline"
            startIcon={<Icon name="tune" size={16} />}
            onClick={() => setRebuildDialog(true)}
            disabled={rebuildLoading}
          >
            {rebuildLoading ? '重建中...' : '重建索引'}
          </Button>
          <Button
            variant="primary"
            startIcon={<Icon name="upload" size={16} />}
            onClick={() => setUploadDialog(true)}
          >
            上傳文檔
          </Button>
        </div>
      </div>
      {error && (
        <Alert severity="error" style={{ marginBottom: '16px' }} onClose={() => setLocalError('')}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" style={{ marginBottom: '16px' }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}
      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <h2 className={styles.cardTitle}>
            已上傳的文檔 ({documents.length})
          </h2>
        </div>
        {documents.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>
              <Icon name="description" size={64} />
            </div>
            <h3 className={styles.emptyTitle}>還沒有上傳任何文檔</h3>
            <p className={styles.emptySubtitle}>開始上傳文檔來建立您的知識庫</p>
          </div>
        ) : (
          <div className={styles.docList}>
            {documents.map((doc) => (
              <div key={doc.id} className={styles.docItem}>
                <div className={styles.docMain}>
                  <div className={styles.docTitleRow}>
                    <Icon name="description" size={20} color="var(--color-primary)" />
                    <span className={styles.docFilename}>{doc.filename}</span>
                    <Chip label={getFileTypeLabel(doc.file_type, doc.filename)} size="sm" variant="outlined" />
                    {doc.is_processed && (
                      <Chip label="已處理" size="sm" color="success" variant="outlined" />
                    )}
                  </div>
                  {doc.description && (
                    <div className={styles.docDescriptionBox}>
                      <span className={styles.docDescriptionIcon}>
                        <Icon name="lightbulb" size={15} />
                      </span>
                      <span className={styles.docDescriptionText}>
                        {doc.description}
                      </span>
                    </div>
                  )}
                  <div className={styles.docMeta}>
                    <span>上傳時間: {new Date(doc.created_at).toLocaleString('zh-TW')}</span>
                    <span>文件類型: {doc.file_type}</span>
                  </div>
                </div>
                <div className={styles.docActions}>
                  {deletingStatus[doc.id] === 'deleting' && (
                    <Chip label="刪除中" size="sm" color="warning" />
                  )}
                  {deletingStatus[doc.id] === 'deleted' && (
                    <Chip label="已刪除" size="sm" color="success" />
                  )}
                  {deletingStatus[doc.id] === 'failed' && (
                    <Chip label="刪除失敗" size="sm" color="error" />
                  )}
                  <IconButton
                    size="sm"
                    onClick={() => handleDelete(doc.id, doc.filename)}
                    disabled={deletingStatus[doc.id] === 'deleting'}
                    aria-label="刪除文檔"
                  >
                    <Icon name="delete" size={18} color="var(--color-error)" />
                  </IconButton>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      {/* 上傳文檔 Dialog */}
      <Dialog
        open={uploadDialog}
        onClose={() => !uploadLoading && setUploadDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <div className={styles.dialogHeaderFlex}>
            <div className={styles.dialogTitleWithIcon}>
              <div className={styles.dialogIconBadge}>
                <Icon name="upload" size={20} />
              </div>
              <div>
                <div>上傳文檔到知識庫</div>
                <div style={{ fontSize: '12px', fontWeight: 'normal', color: 'var(--text-secondary)' }}>
                  支援將多種格式檔案分塊、向量化並存入 RAG 檢索庫
                </div>
              </div>
            </div>
            <IconButton
              size="sm"
              onClick={() => !uploadLoading && setUploadDialog(false)}
              disabled={uploadLoading}
              aria-label="關閉對話框"
            >
              <Icon name="close" size={18} />
            </IconButton>
          </div>
        </DialogTitle>

        <DialogContent>
          <div style={{ marginTop: '8px' }}>
            <input
              ref={fileInputRef}
              accept=".txt,.md,.markdown,.pdf,.docx,.pptx,.xlsx,.csv,.json,.yaml,.yml,.xml,.html,.htm,.log,.py,.js,.ts,.tsx,.jsx,.java,.cpp,.c,.sql,.sh,.ini,.env"
              style={{ display: 'none' }}
              id="file-upload"
              type="file"
              multiple
              onChange={handleFileSelect}
            />

            {/* 拖曳上傳放置區 */}
            <div
              className={`${styles.dropZone} ${isDragging ? styles.dropZoneActive : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragEnter={handleDragEnter}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className={styles.dropZoneIconWrap}>
                <Icon name="upload" size={28} />
              </div>
              <div className={styles.dropZoneTitle}>
                {isDragging ? '放開以新增檔案' : '拖曳檔案至此處，或點擊瀏覽檔案'}
              </div>
              <div className={styles.dropZoneSubtitle}>
                支援多檔案批次選取，單一檔案上限 50MB
              </div>
              <div className={styles.formatTagsWrap}>
                <span className={styles.formatTag}>PDF</span>
                <span className={styles.formatTag}>Word (DOCX)</span>
                <span className={styles.formatTag}>PPT (PPTX)</span>
                <span className={styles.formatTag}>Excel (XLSX/CSV)</span>
                <span className={styles.formatTag}>Markdown</span>
                <span className={styles.formatTag}>JSON</span>
                <span className={styles.formatTag}>HTML</span>
                <span className={styles.formatTag}>Code (.py, .js, .ts...)</span>
              </div>
            </div>

            {/* 已選擇檔案佇列 */}
            {selectedFiles && selectedFiles.length > 0 && (
              <div className={styles.selectedFilesBox}>
                <div className={styles.fileQueueHeader}>
                  <div className={styles.fileQueueTitle}>
                    待處理清單 ({selectedFiles.length} 個檔案，共 {formatFileSize(selectedFiles.reduce((acc, f) => acc + f.size, 0))})
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={removeSelectedFiles}
                    disabled={uploadLoading}
                    startIcon={<Icon name="delete" size={14} color="var(--color-error)" />}
                  >
                    清空清單
                  </Button>
                </div>

                <div className={styles.fileQueueList}>
                  {selectedFiles.map((f, idx) => {
                    const item = uploadItems[idx] || { progress: 0, status: 'ready', detail: null };
                    const extLabel = getFileTypeLabel(f.type, f.name);
                    const chipProps = getStatusChipProps(item.status, item.detail);

                    return (
                      <div key={idx} className={styles.fileCard}>
                        <div className={styles.fileCardTop}>
                          <div className={styles.fileCardLeft}>
                            <span className={`${styles.fileBadge} ${getFileBadgeClass(extLabel)}`}>
                              {extLabel}
                            </span>
                            <div className={styles.fileInfoText}>
                              <div className={styles.fileName} title={f.name}>{f.name}</div>
                              <div className={styles.fileSize}>{formatFileSize(f.size)}</div>
                            </div>
                          </div>

                          <div className={styles.fileCardRight}>
                            <Chip
                              label={chipProps.label}
                              variant={chipProps.variant}
                              icon={chipProps.icon}
                              size="sm"
                            />
                            {item.status === 'uploading' ? (
                              <IconButton
                                size="sm"
                                onClick={() => cancelUpload(idx)}
                                title="取消此檔案上傳"
                              >
                                <Icon name="close" size={14} />
                              </IconButton>
                            ) : (
                              <IconButton
                                size="sm"
                                onClick={() => removeFileAt(idx)}
                                disabled={uploadLoading}
                                title="從清單移除"
                              >
                                <Icon name="delete" size={14} color="var(--text-tertiary)" />
                              </IconButton>
                            )}
                          </div>
                        </div>

                        {/* 進度條 */}
                        {(item.status === 'uploading' || item.progress > 0) && (
                          <div>
                            <div className={styles.progressBar}>
                              <div className={styles.progressFill} style={{ width: `${item.progress}%` }} />
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-tertiary)' }}>
                              <span>{item.status === 'uploading' ? '正在分塊與建立向量索引...' : ''}</span>
                              <span>{item.progress}%</span>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </DialogContent>

        <DialogActions>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <div>
              {uploadLoading && (
                <Button variant="outline" size="sm" onClick={cancelAllUploads}>
                  取消全部上傳
                </Button>
              )}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <Button
                variant="secondary"
                onClick={() => setUploadDialog(false)}
                disabled={uploadLoading}
              >
                關閉
              </Button>
              <Button
                variant="primary"
                startIcon={<Icon name="upload" size={16} />}
                onClick={startUpload}
                disabled={(!selectedFiles || selectedFiles.length === 0) || uploadLoading}
                loading={uploadLoading}
              >
                {uploadLoading ? '正在入庫處理中...' : `開始上傳 (${selectedFiles.length})`}
              </Button>
            </div>
          </div>
        </DialogActions>
      </Dialog>

      {/* 清除確認 Dialog */}
      <Dialog
        open={confirmRemoveOpen}
        onClose={cancelRemove}
        maxWidth="xs"
      >
        <DialogTitle>
          <div className={styles.dialogTitleWithIcon}>
            <div className={`${styles.dialogIconBadge} ${styles.dialogIconBadgeDanger}`}>
              <Icon name="warning" size={18} />
            </div>
            <span>確認清空待上傳清單？</span>
          </div>
        </DialogTitle>
        <DialogContent>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.5, marginTop: '8px' }}>
            此操作將清空目前已選取的 {selectedFiles.length} 個檔案。已入庫的文檔不受影響。
          </p>
        </DialogContent>
        <DialogActions>
          <Button variant="secondary" onClick={cancelRemove}>取消</Button>
          <Button variant="danger" onClick={confirmRemoveSelectedFiles}>確定清空</Button>
        </DialogActions>
      </Dialog>

      {/* 重建索引 Dialog */}
      <Dialog
        open={rebuildDialog}
        onClose={() => !rebuildLoading && setRebuildDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <div className={styles.dialogTitleWithIcon}>
            <div className={`${styles.dialogIconBadge} ${styles.dialogIconBadgeWarning}`}>
              <Icon name="tune" size={18} />
            </div>
            <span>確認重建知識庫索引？</span>
          </div>
        </DialogTitle>
        <DialogContent>
          <div style={{ marginTop: '8px' }}>
            <p style={{ fontSize: '14px', color: 'var(--text-primary)', marginBottom: '10px' }}>
              此操作將依據最新切塊配置（800字/塊）重新建立所有文檔的 FAISS 向量索引和 BM25 關鍵字索引。
            </p>
            <div style={{ background: 'var(--bg-surface-secondary)', padding: '12px 16px', borderRadius: 'var(--radius-md)', marginBottom: '12px' }}>
              <ul style={{ fontSize: '13px', color: 'var(--text-secondary)', paddingLeft: '16px', lineHeight: 1.7, margin: 0 }}>
                <li>適用於切塊參數調整、索引毀損或檢索異常時</li>
                <li>採用 Intel 多執行緒加速，重構速度極快</li>
                <li>重建過程中背景自動執行，完成後即時生效</li>
              </ul>
            </div>
            {rebuildLoading && (
              <div style={{ marginTop: '16px', textAlign: 'center', padding: '12px' }}>
                <Spinner size={28} color="var(--color-primary)" />
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '8px', fontWeight: 500 }}>
                  正在重建向量庫與全文檢索索引，請稍候...
                </p>
              </div>
            )}
          </div>
        </DialogContent>
        <DialogActions>
          <Button variant="secondary" onClick={() => setRebuildDialog(false)} disabled={rebuildLoading}>
            取消
          </Button>
          <Button
            variant="primary"
            onClick={handleRebuildIndex}
            disabled={rebuildLoading}
            loading={rebuildLoading}
            startIcon={<Icon name="refresh" size={16} />}
          >
            確認重建
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}
export default Documents;