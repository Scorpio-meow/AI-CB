
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  CircularProgress,
  Card,
  CardContent,
  Alert,
  Autocomplete,
  Chip
} from '@mui/material';
import { PlayArrow, DoneAll } from '@mui/icons-material';
import { getCustomAgents } from '../services/customAgentService';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001';

// --- Helper function to get available professions ---
const getProfessions = async () => {
  const response = await axios.get(`${API_URL}/api/workflow/professions`);
  return response.data;
};

// --- NodeCard Component ---
const NodeCard = ({ nodeState }) => (
  <Card sx={{ mt: 2, mb: 2, boxShadow: 3, borderRadius: 2 }}>
    <CardContent>
      <Typography variant="h6" component="div" sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        {nodeState.label}
      </Typography>
      
      {nodeState.status === 'thinking' && <CircularProgress size={20} />}
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        狀態: {nodeState.status || 'pending'}
      </Typography>

      {nodeState.error && <Alert severity="error" sx={{ mb: 1 }}>{nodeState.error}</Alert>}

      {nodeState.response && (
        <Paper variant="outlined" sx={{ p: 2, mt: 1, whiteSpace: 'pre-wrap', maxHeight: '400px', overflowY: 'auto' }}>
          {nodeState.response}
        </Paper>
      )}
    </CardContent>
  </Card>
);

// --- Main Workflow Component ---
const Workflow = () => {
  // --- State Hooks ---
  const [prompt, setPrompt] = useState('');
  const [availableAgents, setAvailableAgents] = useState([]);
  const [selectedAgents, setSelectedAgents] = useState([]);
  const [workflowState, setWorkflowState] = useState({});
  const [isStarted, setIsStarted] = useState(false);
  const [isFinished, setIsFinished] = useState(false);
  const [finalResult, setFinalResult] = useState('');
  const [finalConversationId, setFinalConversationId] = useState(null);
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [error, setError] = useState(null); // <-- 新增錯誤狀態
  const ws = useRef(null);
  const navigate = useNavigate();

  // --- Fetch all available agents (built-in + custom) ---
  useEffect(() => {
    const fetchAllAgents = async () => {
      try {
        setLoadingAgents(true);
        setError(null);
        
        const professions = await getProfessions();
        const customAgentsResponse = await getCustomAgents();
        const customAgents = customAgentsResponse.data.map(agent => agent.name);
        
        const allAgentNames = [...new Set([...professions, ...customAgents])];
        setAvailableAgents(allAgentNames);

      } catch (err) {
        console.error("Failed to fetch agents:", err);
        setError("無法載入 Agent 列表，請確保後端服務正在運行且資料庫已連接。");
      } finally {
        setLoadingAgents(false);
      }
    };
    fetchAllAgents();
  }, []);

  // --- WebSocket Management ---
  const connectWebSocket = useCallback(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host.replace(/\d+$/, '8001')}/api/workflow/ws`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => console.log('WebSocket connected');
    ws.current.onclose = () => console.log('WebSocket disconnected');
    ws.current.onerror = (error) => console.error('WebSocket error:', error);

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received from WS:', data);

      if (data.nodeId) {
        setWorkflowState(prevState => ({
          ...prevState,
          [data.nodeId]: {
            ...prevState[data.nodeId],
            ...data,
            label: prevState[data.nodeId]?.label || data.nodeId,
          }
        }));
      }

      if (data.status === 'finished') {
        setIsStarted(false);
        setIsFinished(true);
        setFinalResult(data.final_artical);
        setFinalConversationId(data.conversation_id);
      } else if (data.status === 'error') {
        setIsStarted(false);
        setFinalResult(`工作流出錯: ${data.response}`);
      }
    };
  }, []);

  useEffect(() => {
    connectWebSocket();
    return () => ws.current?.close();
  }, [connectWebSocket]);

  // --- Workflow Logic ---
  const startWorkflow = () => {
    if (!prompt.trim()) return alert('請輸入初始指令');
    if (selectedAgents.length === 0) return alert('請至少選擇一個 Agent');

    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
        alert("WebSocket 尚未連接，請稍後再試。");
        return;
    }

    setWorkflowState({});
    setFinalResult('');
    setIsStarted(true);
    setIsFinished(false);
    setFinalConversationId(null);

    const nodes = selectedAgents.map((agentName, index) => ({
      ID: `node-${index}`,
      profession: agentName,
      gate: index === 0,
      input: index === 0 ? [] : [`node-${index - 1}_output`],
      output: index === selectedAgents.length - 1 ? [] : [`node-${index + 1}_input`]
    }));

    const payload = {
      initialPrompt: prompt,
      agents: nodes
    };
    
    const initialState = {};
    nodes.forEach(node => {
        initialState[node.ID] = { label: node.profession, status: 'pending' };
    });
    setWorkflowState(initialState);

    ws.current.send(JSON.stringify({ type: 'start_workflow', payload }));
  };

  const handleFinalize = () => {
    if (finalConversationId) {
      navigate('/chat', { state: { conversationId: finalConversationId } });
    }
  };

  // --- Rendering ---
  return (
    <Box sx={{ maxWidth: 800, margin: 'auto', p: 2 }}>
      <Typography variant="h4" gutterBottom>多 Agent 工作流</Typography>
      
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper sx={{ p: 2, mb: 3 }} elevation={2}>
        <TextField
          fullWidth
          label="請輸入初始專案指令"
          variant="outlined"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          multiline
          rows={3}
          disabled={isStarted || isFinished}
        />

        <Autocomplete
          multiple
          sx={{ mt: 2 }}
          options={availableAgents}
          getOptionLabel={(option) => option}
          value={selectedAgents}
          onChange={(event, newValue) => {
            setSelectedAgents(newValue);
          }}
          loading={loadingAgents}
          disabled={loadingAgents || !!error} // 如果正在載入或發生錯誤，則禁用
          renderInput={(params) => (
            <TextField
              {...params}
              variant="outlined"
              label="選擇 Agents (按順序執行)"
              placeholder="選擇 Agents"
              InputProps={{
                ...params.InputProps,
                endAdornment: (
                  <React.Fragment>
                    {loadingAgents ? <CircularProgress color="inherit" size={20} /> : null}
                    {params.InputProps.endAdornment}
                  </React.Fragment>
                ),
              }}
            />
          )}
          renderTags={(value, getTagProps) =>
            value.map((option, index) => (
              <Chip variant="outlined" label={`${index + 1}. ${option}`} {...getTagProps({ index })} />
            ))
          }
        />

        <Button
          variant="contained"
          onClick={startWorkflow}
          disabled={isStarted || isFinished || loadingAgents || !!error}
          startIcon={isStarted ? <CircularProgress size={20} /> : <PlayArrow />}
          sx={{ mt: 2 }}
        >
          {isStarted ? '執行中...' : '啟動工作流'}
        </Button>
      </Paper>

      {(isStarted || isFinished) && (
        <Box>
          {Object.keys(workflowState).map(nodeId => (
            workflowState[nodeId] && <NodeCard key={nodeId} nodeState={workflowState[nodeId]} />
          ))}
        </Box>
      )}

      {isFinished && (
        <Paper sx={{ p: 3, mt: 3, backgroundColor: '#e8f5e9' }} elevation={3}>
            <Typography variant="h5" gutterBottom>最終結論</Typography>
            <Typography sx={{whiteSpace: 'pre-wrap'}}>{finalResult}</Typography>
            <Button
              variant="contained"
              color="success"
              onClick={handleFinalize}
              startIcon={<DoneAll />}
              sx={{ mt: 2 }}
            >
              將此結論存入對話紀錄
            </Button>
        </Paper>
      )}
    </Box>
  );
};

export default Workflow;
