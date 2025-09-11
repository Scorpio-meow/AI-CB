import React, { useState } from 'react';
import {
  Container,
  Typography,
  Button,
  Box,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton
} from '@mui/material';
import { Add, Edit, Delete } from '@mui/icons-material';
import * as customAgentService from '../services/customAgentService';
import { useAgents } from '../contexts/AgentContext';

// Agent 表單的初始狀態
const initialFormState = {
  id: null,
  name: '',
  role: '',
  expertise: '',
  prompt: '',
  tools: ''
};

function CustomAgents() {
  const { 
    agents, 
    loading, 
    error: contextError, 
    addAgent, 
    updateAgent, 
    removeAgent 
  } = useAgents();
  
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState(initialFormState);
  const [formError, setFormError] = useState(null);

  // --- Dialog and Form Handlers ---
  const handleOpenDialog = (agent = null) => {
    setFormError(null);
    if (agent) {
      // 編輯模式：載入 agent 資料，確保 tools 是字串
      setFormData({ ...agent, tools: agent.tools ? agent.tools.join(', ') : '' });
    } else {
      // 新增模式：重設為初始表單
      setFormData(initialFormState);
    }
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
  };

  const handleFormChange = (event) => {
    const { name, value } = event.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFormSubmit = async () => {
    try {
      setFormError(null);
      const submissionData = {
        ...formData,
        tools: formData.tools.split(',').map(t => t.trim()).filter(t => t)
      };

      if (formData.id) {
        // 更新模式
        const { data: updatedAgentData } = await customAgentService.updateCustomAgent(formData.id, submissionData);
        updateAgent(updatedAgentData);
      } else {
        // 新增模式
        const { data: newAgentData } = await customAgentService.createCustomAgent(submissionData);
        addAgent(newAgentData);
      }
      
      handleCloseDialog();
    } catch (err) {
      setFormError('儲存失敗，請檢查資料是否正確。');
      console.error(err);
    }
  };

  // --- CRUD Handlers ---
  const handleDelete = async (id) => {
    if (window.confirm('確定要刪除這個 Agent 嗎？')) {
      try {
        await customAgentService.deleteCustomAgent(id);
        removeAgent(id);
      } catch (err) {
        // 這裡可以選擇性地顯示一個錯誤提示
        console.error('刪除失敗。', err);
      }
    }
  };

  // --- Rendering ---
  if (loading) {
    return <CircularProgress />;
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">Agent 管理</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => handleOpenDialog()}>
          新增 Agent
        </Button>
      </Box>

      {contextError && <Alert severity="error" sx={{ mb: 2 }}>{contextError}</Alert>}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>名稱</TableCell>
              <TableCell>角色 (Role)</TableCell>
              <TableCell>專業領域</TableCell>
              <TableCell>工具</TableCell>
              <TableCell align="right">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {agents.map((agent) => (
              <TableRow key={agent.id}>
                <TableCell>{agent.name}</TableCell>
                <TableCell>{agent.role}</TableCell>
                <TableCell>{agent.expertise}</TableCell>
                <TableCell>{Array.isArray(agent.tools) ? agent.tools.join(', ') : ''}</TableCell>
                <TableCell align="right">
                  <IconButton onClick={() => handleOpenDialog(agent)}><Edit /></IconButton>
                  <IconButton onClick={() => handleDelete(agent.id)}><Delete /></IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* 新增/編輯用的 Dialog */}
      <Dialog open={isDialogOpen} onClose={handleCloseDialog} fullWidth maxWidth="md">
        <DialogTitle>{formData.id ? '編輯 Agent' : '新增 Agent'}</DialogTitle>
        <DialogContent>
          {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
          <TextField name="name" label="名稱 (例如: 產品經理)" value={formData.name} onChange={handleFormChange} fullWidth margin="normal" />
          <TextField name="role" label="角色 (英文，例如: Product Manager)" value={formData.role} onChange={handleFormChange} fullWidth margin="normal" />
          <TextField name="expertise" label="專業領域" value={formData.expertise} onChange={handleFormChange} fullWidth margin="normal" multiline rows={3} />
          <TextField name="prompt" label="系統提示 (Prompt)" value={formData.prompt} onChange={handleFormChange} fullWidth margin="normal" multiline rows={6} />
          <TextField name="tools" label="工具 (用逗號分隔，例如: File, Search)" value={formData.tools} onChange={handleFormChange} fullWidth margin="normal" helperText="請以逗號分隔多個工具。" />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>取消</Button>
          <Button onClick={handleFormSubmit} variant="contained">儲存</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default CustomAgents;
