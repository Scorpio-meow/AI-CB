import { useState } from 'react';
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
  IconButton,
  FormControlLabel,
  Switch,
  Chip
} from '@mui/material';
import { Add, Edit, Delete, Public, Lock } from '@mui/icons-material';
import { useCustomAgents } from '../hooks/useCustomAgents';
import { useAgents } from '../contexts/useAgents';
const initialFormState = {
  id: null,
  name: '',
  role: '',
  expertise: '',
  prompt: '',
  tools: '',
  is_public: true
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
  const { createAgent, updateAgent: apiUpdateAgent, deleteAgent: apiDeleteAgent } = useCustomAgents();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState(initialFormState);
  const [formError, setFormError] = useState(null);
  const handleOpenDialog = (agent = null) => {
    setFormError(null);
    if (agent) {
      setFormData({
        ...agent,
        tools: agent.tools ? agent.tools.join(', ') : '',
        is_public: agent.is_public !== undefined ? agent.is_public : true
      });
    } else {
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
  const handleSwitchChange = (event) => {
    setFormData(prev => ({ ...prev, is_public: event.target.checked }));
  };
  const handleFormSubmit = async () => {
    try {
      setFormError(null);
      const submissionData = {
        ...formData,
        tools: formData.tools.split(',').map(t => t.trim()).filter(t => t),
        is_public: formData.is_public
      };
      if (formData.id) {
        const updatedAgentData = await apiUpdateAgent(formData.id, submissionData);
        if (updatedAgentData) {
          updateAgent(updatedAgentData);
        } else {
          throw new Error('更新失敗');
        }
      } else {
        const newAgentData = await createAgent(submissionData);
        if (newAgentData) {
          addAgent(newAgentData);
        } else {
          throw new Error('新增失敗');
        }
      }
      handleCloseDialog();
    } catch (err) {
      setFormError('儲存失敗：' + (err.response?.data?.detail || err.message || '請檢查資料是否正確'));
      console.error(err);
    }
  };
  const handleDelete = async (id) => {
    if (window.confirm('確定要刪除這個 Agent 嗎？')) {
      try {
        const success = await apiDeleteAgent(id);
        if (success) {
          removeAgent(id);
        } else {
          throw new Error('刪除失敗');
        }
      } catch (err) {
        alert('刪除失敗：' + (err.response?.data?.detail || err.message));
        console.error('刪除失敗。', err);
      }
    }
  };
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
              <TableCell>可見性</TableCell>
              <TableCell>創建者</TableCell>
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
                <TableCell>
                  {agent.is_public !== false ? (
                    <Chip
                      icon={<Public />}
                      label="公開"
                      color="success"
                      size="small"
                    />
                  ) : (
                    <Chip
                      icon={<Lock />}
                      label="私人"
                      color="default"
                      size="small"
                    />
                  )}
                </TableCell>
                <TableCell>
                  {agent.creator_username || '未知'}
                </TableCell>
                <TableCell align="right">
                  <IconButton onClick={() => handleOpenDialog(agent)}><Edit /></IconButton>
                  <IconButton onClick={() => handleDelete(agent.id)}><Delete /></IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      { }
      <Dialog
        open={isDialogOpen}
        onClose={handleCloseDialog}
        fullWidth
        maxWidth="md"
        disableRestoreFocus
        aria-labelledby="agent-dialog-title"
      >
        <DialogTitle id="agent-dialog-title">{formData.id ? '編輯 Agent' : '新增 Agent'}</DialogTitle>
        <DialogContent>
          {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
          <TextField
            name="name"
            label="名稱 (例如: 產品經理)"
            value={formData.name}
            onChange={handleFormChange}
            fullWidth
            margin="normal"
          />
          <TextField
            name="role"
            label="角色 (英文，例如: Product Manager)"
            value={formData.role}
            onChange={handleFormChange}
            fullWidth
            margin="normal"
          />
          <TextField
            name="expertise"
            label="專業領域"
            value={formData.expertise}
            onChange={handleFormChange}
            fullWidth
            margin="normal"
            multiline
            rows={3}
          />
          <TextField
            name="prompt"
            label="系統提示 (Prompt)"
            value={formData.prompt}
            onChange={handleFormChange}
            fullWidth
            margin="normal"
            multiline
            rows={6}
          />
          <TextField
            name="tools"
            label="工具 (用逗號分隔，例如: File, Search)"
            value={formData.tools}
            onChange={handleFormChange}
            fullWidth
            margin="normal"
            helperText="請以逗號分隔多個工具。"
          />
          <FormControlLabel
            control={
              <Switch
                checked={formData.is_public}
                onChange={handleSwitchChange}
                color="primary"
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {formData.is_public ? <Public /> : <Lock />}
                <Typography>
                  {formData.is_public ? '公開 Agent (所有用戶可見)' : '私人 Agent (僅自己可見)'}
                </Typography>
              </Box>
            }
            sx={{ mt: 2 }}
          />
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