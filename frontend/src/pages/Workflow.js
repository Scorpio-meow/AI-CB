
import React, { useState, useEffect, useRef } from 'react';
import { Box, TextField, Button, Paper, Typography, CircularProgress, Card, CardContent, CardActions, IconButton, Collapse, Alert } from '@mui/material';
import { PlayArrow, Replay, AccountTree, Send } from '@mui/icons-material';

// A simple, hardcoded workflow definition for demonstration
const hardcodedWorkflow = {
  initialPrompt: '',
  entryPointId: 'node-pm',
  nodes: [
    { id: 'node-pm', data: { originalLabel: 'PM' } },
    { id: 'node-engineer', data: { originalLabel: '工程師' } },
    { id: 'node-sales', data: { originalLabel: '業務分析師' } },
    { id: 'node-aggregator', data: { originalLabel: 'Aggregator' } },
  ],
  edges: [
    { source: 'node-pm', target: 'node-engineer' },
    { source: 'node-pm', target: 'node-sales' },
    { source: 'node-engineer', target: 'node-aggregator' },
    { source: 'node-sales', target: 'node-aggregator' },
  ],
};

const NodeCard = ({ nodeId, nodeState, onRollback }) => {
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);

  const handleRollbackClick = () => {
    if (feedback) {
      onRollback(nodeId, feedback);
      setShowFeedback(false);
      setFeedback('');
    }
  };

  return (
    <Card sx={{ mt: 2, mb: 2, boxShadow: 3, borderRadius: 2 }}>
      <CardContent>
        <Typography variant="h6" component="div" sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <AccountTree sx={{ mr: 1, color: 'primary.main' }} />
          {nodeState.label}
        </Typography>
        
        {nodeState.status === 'thinking' && <CircularProgress size={20} />}
        {nodeState.status === 'revising' && <CircularProgress size={20} color="secondary" />}
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          狀態: {nodeState.status || 'pending'}
        </Typography>

        {nodeState.message && <Alert severity="info" sx={{ mb: 1 }}>{nodeState.message}</Alert>}
        {nodeState.error && <Alert severity="error" sx={{ mb: 1 }}>{nodeState.error}</Alert>}

        {nodeState.response && (
          <Paper variant="outlined" sx={{ p: 2, mt: 1, whiteSpace: 'pre-wrap', maxHeight: '300px', overflowY: 'auto' }}>
            {nodeState.response}
          </Paper>
        )}
      </CardContent>
      {nodeState.can_rollback && (
        <CardActions sx={{ justifyContent: 'flex-end' }}>
          <Button 
            variant="outlined"
            size="small" 
            startIcon={<Replay />} 
            onClick={() => setShowFeedback(!showFeedback)}
          >
            請求修改
          </Button>
        </CardActions>
      )}
      <Collapse in={showFeedback}>
        <Box sx={{ p: 2, borderTop: '1px solid #eee' }}>
          <TextField
            fullWidth
            label="請提供修改建議..."
            variant="outlined"
            size="small"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            multiline
          />
          <Button 
            variant="contained"
            size="small"
            sx={{ mt: 1 }}
            onClick={handleRollbackClick}
            endIcon={<Send />}
            disabled={!feedback}
          >
            發送建議
          </Button>
        </Box>
      </Collapse>
    </Card>
  );
};

const Workflow = () => {
  const [prompt, setPrompt] = useState('');
  const [workflowState, setWorkflowState] = useState({});
  const [isStarted, setIsStarted] = useState(false);
  const [finalResult, setFinalResult] = useState('');
  const ws = useRef(null);

  useEffect(() => {
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    // Ensure you are using the correct WebSocket protocol (ws or wss)
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/workflow/ws`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received from WS:', data);

      setWorkflowState(prevState => {
        const newState = { ...prevState };
        if (data.nodeId) {
          const node = hardcodedWorkflow.nodes.find(n => n.id === data.nodeId);
          newState[data.nodeId] = {
            ...prevState[data.nodeId],
            label: node?.data.originalLabel || data.nodeId,
            status: data.status,
            response: data.response || prevState[data.nodeId]?.response,
            message: data.message,
            error: data.status === 'error' ? data.response : null,
            can_rollback: data.can_rollback,
          };
        } else if (data.status === 'finished') {
            setIsStarted(false);
            setFinalResult(data.final_artical);
        } else if (data.status === 'error') {
            setIsStarted(false);
            // Handle global errors
            setFinalResult(`工作流出錯: ${data.response}`);
        }
        return newState;
      });
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
      setIsStarted(false);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsStarted(false);
    };
  };

  const startWorkflow = () => {
    if (!prompt.trim()) {
      alert('請輸入初始指令');
      return;
    }
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
        connectWebSocket();
        // Wait for connection to be established
        setTimeout(() => {
            sendStartMessage();
        }, 1000);
    } else {
        sendStartMessage();
    }
  };

  const sendStartMessage = () => {
    setWorkflowState({});
    setFinalResult('');
    setIsStarted(true);

    const payload = { ...hardcodedWorkflow, initialPrompt: prompt };
    ws.current.send(JSON.stringify({ type: 'start_workflow', payload }));
  }

  const handleRollback = (nodeId, feedback) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'request_rollback', payload: { nodeId, feedback } }));
    }
  };

  return (
    <Box sx={{ maxWidth: 800, margin: 'auto', p: 2 }}>
      <Typography variant="h4" gutterBottom>多 Agent 工作流</Typography>
      <Paper sx={{ p: 2, mb: 3 }} elevation={2}>
        <TextField
          fullWidth
          label="請輸入初始專案指令"
          variant="outlined"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          multiline
          rows={3}
          disabled={isStarted}
        />
        <Button
          variant="contained"
          onClick={startWorkflow}
          disabled={isStarted}
          startIcon={isStarted ? <CircularProgress size={20} /> : <PlayArrow />}
          sx={{ mt: 2 }}
        >
          {isStarted ? '執行中...' : '啟動工作流'}
        </Button>
      </Paper>

      {isStarted && (
        <Box>
          {hardcodedWorkflow.nodes.map(node => (
            workflowState[node.id] && (
              <NodeCard 
                key={node.id} 
                nodeId={node.id} 
                nodeState={workflowState[node.id]} 
                onRollback={handleRollback}
              />
            )
          ))}
        </Box>
      )}

      {finalResult && (
        <Paper sx={{ p: 3, mt: 3, backgroundColor: '#e8f5e9' }} elevation={3}>
            <Typography variant="h5" gutterBottom>最終結果</Typography>
            <Typography sx={{whiteSpace: 'pre-wrap'}}>{finalResult}</Typography>
        </Paper>
      )}
    </Box>
  );
};

export default Workflow;
