import React, { useState, useEffect } from 'react';
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
  Description as DocumentIcon
} from '@mui/icons-material';
import axios from 'axios';

function Documents() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uploadDialog, setUploadDialog] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/documents/');
      setDocuments(response.data);
      setError('');
    } catch (err) {
      setError('載入文檔失敗');
      console.error('Load documents error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      // 檢查文件類型
      const allowedTypes = ['text/plain', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      if (!allowedTypes.includes(file.type)) {
        setError('不支援的文件類型。請上傳 .txt, .pdf 或 .docx 文件');
        return;
      }
      
      // 檢查文件大小 (最大 50MB)
      if (file.size > 50 * 1024 * 1024) {
        setError('文件大小不能超過 50MB');
        return;
      }
      
      setSelectedFile(file);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('請選擇文件');
      return;
    }

    setUploadLoading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      await axios.post('/api/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      setSuccess('文檔上傳成功！');
      setUploadDialog(false);
      setSelectedFile(null);
      loadDocuments(); // 重新載入文檔列表
    } catch (err) {
      setError(err.response?.data?.detail || '文檔上傳失敗');
      console.error('Upload error:', err);
    } finally {
      setUploadLoading(false);
    }
  };

  const handleDelete = async (documentId, filename) => {
    if (window.confirm(`確定要刪除文檔 "${filename}" 嗎？此操作不可逆！`)) {
      try {
        console.log(`正在刪除文檔 ID: ${documentId}, 文件名: ${filename}`);
        const response = await axios.delete(`/api/documents/${documentId}`);
        console.log('刪除響應:', response.data);
        setSuccess('文檔刪除成功');
        loadDocuments();
      } catch (err) {
        console.error('刪除文檔錯誤:', err);
        setError('刪除文檔失敗: ' + (err.response?.data?.detail || err.message));
      }
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
        <Typography variant="h6" sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          已上傳的文檔 ({documents.length})
        </Typography>
        
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
                    <IconButton
                      edge="end"
                      onClick={() => handleDelete(doc.id, doc.filename)}
                      color="error"
                    >
                      <DeleteIcon />
                    </IconButton>
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
              onChange={handleFileSelect}
            />
            <label htmlFor="file-upload">
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
            
            {selectedFile && (
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <Typography variant="subtitle2" gutterBottom>
                  已選擇的文件:
                </Typography>
                <Typography variant="body2">
                  <strong>文件名:</strong> {selectedFile.name}
                </Typography>
                <Typography variant="body2">
                  <strong>大小:</strong> {formatFileSize(selectedFile.size)}
                </Typography>
                <Typography variant="body2">
                  <strong>類型:</strong> {getFileTypeLabel(selectedFile.type)}
                </Typography>
              </Paper>
            )}
            
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              支援的文件格式: .txt, .pdf, .docx
              <br />
              最大文件大小: 50MB
            </Typography>
            
            {uploadLoading && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" gutterBottom>
                  正在上傳文檔...
                </Typography>
                <LinearProgress />
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setUploadDialog(false)}
            disabled={uploadLoading}
          >
            取消
          </Button>
          <Button 
            onClick={handleUpload}
            variant="contained"
            disabled={!selectedFile || uploadLoading}
          >
            {uploadLoading ? '上傳中...' : '上傳'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Documents;
