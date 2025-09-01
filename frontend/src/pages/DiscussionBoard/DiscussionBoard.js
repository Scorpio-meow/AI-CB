// src/components/DiscussionBoard/DiscussionBoard.js

import React, { useState, useCallback, useRef, useEffect, useMemo, useImperativeHandle } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  applyEdgeChanges,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Box, Paper, Typography, Menu, MenuItem, Chip, Button, Alert, CircularProgress } from '@mui/material';
import { DoneAll } from '@mui/icons-material';
import AgentNode from './AgentNode';
import Sidebar from './Sidebar'; // Corrected typo from Siderbar

let idCounter = 0;
const getUniqueId = () => `dndnode_${idCounter++}`;

const DiscussionBoard = React.forwardRef(({ initialPrompt, onWorkflowComplete }, ref) => { 
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [workflowProcess, setWorkflowProcess] = useState([]);
  const [entryPointId, setEntryPointId] = useState(null);
  const [contextMenu, setContextMenu] = useState({ anchorEl: null, node: null });
  const socketRef = useRef(null);
  const reactFlowWrapper = useRef(null); 
  const [wsStatus, setWsStatus] = useState('disconnected');
  
  const [isFinished, setIsFinished] = useState(false);
  const [finalConversationId, setFinalConversationId] = useState(null);
  const [infoMessage, setInfoMessage] = useState(''); // State for info messages

  const nodeTypes = useMemo(() => ({ agent: AgentNode }), []);

  const logCurrentProcess = (action) => {
    setWorkflowProcess(currentProcess => {
      console.log(`--- 🔄 狀態更新後 (${action}) ---`);
      console.log(JSON.stringify(currentProcess, null, 2));
      console.log('---------------------------------');
      return currentProcess;
    });
  };
  
  const onDrop = useCallback( (event) => {
    event.preventDefault();
    const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
    const { nodeType, label, profession } = JSON.parse(event.dataTransfer.getData('application/reactflow'));
    if (typeof nodeType === 'undefined' || !nodeType) return;
    
    const position = reactFlowInstance.project({ x: event.clientX - reactFlowBounds.left, y: event.clientY - reactFlowBounds.top });
    const newNodeId = getUniqueId();
    const newNode = { 
      id: newNodeId, 
      type: 'agent', 
      position, 
      data: { originalLabel: label, label: label, profession: profession }, 
    };
    setNodes((nds) => nds.concat(newNode));

    const newAgentData = {
      ID: newNodeId,
      profession: profession,
      gate: false,
      input: [],
      output: [],
    };
    setWorkflowProcess(current => [...current, newAgentData]);
    logCurrentProcess("Agent 加入");

  }, [reactFlowInstance, setNodes]);

  const onConnect = useCallback((params) => {
    setEdges((eds) => addEdge(params, eds));
    setWorkflowProcess(currentProcess => {
      const sourceAgent = currentProcess.find(a => a.ID === params.source);
      const targetAgent = currentProcess.find(a => a.ID === params.target);
      if (!sourceAgent || !targetAgent) return currentProcess;
      const outputString = `${targetAgent.ID}_${targetAgent.profession}`;
      const inputString = `${sourceAgent.ID}_${sourceAgent.profession}`;
      return currentProcess.map(agent => {
        if (agent.ID === params.source) {
          if (agent.output.includes(outputString)) return agent;
          return { ...agent, output: [...agent.output, outputString] };
        }
        if (agent.ID === params.target) {
          if (agent.input.includes(inputString)) return agent;
          return { ...agent, input: [...agent.input, inputString] };
        }
        return agent;
      });
    });
    logCurrentProcess("連接 Agent");
  }, [setEdges]);

  const onNodeClick = useCallback((event, node) => {
    setEntryPointId(node.id);
    setWorkflowProcess(currentProcess => 
      currentProcess.map(agent => ({ ...agent, gate: agent.ID === node.id }))
    );
    logCurrentProcess("設定入口");
  }, []);
  
  const handleEdgesChange = useCallback((changes) => {
    setEdges((eds) => applyEdgeChanges(changes, eds));
    changes.forEach(change => {
      if (change.type === 'remove') {
        const edgeToRemove = edges.find(edge => edge.id === change.id);
        if (!edgeToRemove) return;
        setWorkflowProcess(currentProcess => {
          const sourceAgent = currentProcess.find(a => a.ID === edgeToRemove.source);
          const targetAgent = currentProcess.find(a => a.ID === edgeToRemove.target);
          if (!sourceAgent || !targetAgent) return currentProcess;
          const outputStringToRemove = `${targetAgent.ID}_${targetAgent.profession}`;
          const inputStringToRemove = `${sourceAgent.ID}_${sourceAgent.profession}`;
          return currentProcess.map(agent => {
            if (agent.ID === sourceAgent.ID) {
              return { ...agent, output: agent.output.filter(o => o !== outputStringToRemove) };
            }
            if (agent.ID === targetAgent.ID) {
              return { ...agent, input: agent.input.filter(i => i !== inputStringToRemove) };
            }
            return agent;
          });
        });
        logCurrentProcess("刪除連線");
      }
    });
  }, [edges, setEdges]);

  const handleDeleteNode = () => { 
    if (!contextMenu.node) return;
    const nodeIdToDelete = contextMenu.node.id;
    const professionToDelete = nodes.find(n => n.id === nodeIdToDelete)?.data.profession;
    setNodes((nds) => nds.filter((node) => node.id !== nodeIdToDelete));
    setWorkflowProcess(currentProcess => {
      const remainingAgents = currentProcess.filter(agent => agent.ID !== nodeIdToDelete);
      return remainingAgents.map(agent => {
        const stringToRemoveFromInput = `${nodeIdToDelete}_${professionToDelete}`;
        return {
          ...agent,
          input: agent.input.filter(i => !i.startsWith(stringToRemoveFromInput)),
          output: agent.output.filter(o => !o.startsWith(stringToRemoveFromInput)),
        };
      });
    });
    if(entryPointId === nodeIdToDelete) setEntryPointId(null);
    handleCloseContextMenu();
    logCurrentProcess("刪除 Agent");
  };

  useEffect(() => {
    // build ws url based on current location to support different hosts and wss in production
    // If frontend runs on localhost:3000 (dev), prefer backend default port 8001
    let isMounted = true;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 6;
    let reconnectTimer = null;

    const connect = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // when frontend is served from localhost:3000 during development, connect to backend at 8001
        let host;
        try {
          const hostname = window.location.hostname;
          const port = window.location.port;
          if (hostname === 'localhost' && port === '3000') {
            host = `${hostname}:8001`;
          } else {
            host = window.location.host || `${hostname}:8001`;
          }
        } catch (e) {
          host = 'localhost:8001';
        }
        const websocketURL = `${protocol}//${host}/api/workflow/ws`;
        console.log('建立 WebSocket，URL:', websocketURL);

        // close existing socket if any
        if (socketRef.current) {
          try { socketRef.current.onopen = null; socketRef.current.onclose = null; socketRef.current.onerror = null; socketRef.current.onmessage = null; socketRef.current.close(); } catch (e) {}
        }

        socketRef.current = new WebSocket(websocketURL);

        socketRef.current.onopen = () => {
          console.log('WebSocket 連線已建立');
          reconnectAttempts = 0;
          setWsStatus('connected');
        };

        socketRef.current.onclose = (ev) => {
          console.log('WebSocket 連線已關閉', ev);
          setWsStatus('disconnected');
          if (!isMounted) return;
          if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts += 1;
            const backoff = 1000 * Math.min(5, reconnectAttempts); // linear backoff up to 5s
            console.log(`嘗試重連 WebSocket (#${reconnectAttempts})，${backoff}ms 後重試`);
            reconnectTimer = setTimeout(connect, backoff);
          } else {
            console.warn('已達到最大重連次數，停止重連');
          }
        };

        socketRef.current.onerror = (error) => {
          console.error('WebSocket 錯誤:', error);
          setWsStatus('error');
          // onerror may be followed by onclose which triggers reconnect
        };

        socketRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('收到後端更新:', data);
            if (data.status === 'finished') {
              setInfoMessage('');
              setIsFinished(true);
              setFinalConversationId(data.conversation_id);
              // 暫存最終下載連結於 socket 物件，避免全域狀態污染
              if (socketRef.current) {
                socketRef.current.lastFinalDownloadUrl = data.final_download_url || null;
              }
            } else if (data.status === 'error') {
              setInfoMessage('工作流執行出錯');
              setIsFinished(true);
            } else if (data.status === 'info') {
              setInfoMessage(data.message);
            } else if (data.nodeId) {
              setNodes((nds) =>
                nds.map((node) => {
                  if (node.id === data.nodeId) {
                    return { 
                      ...node, 
                      data: { 
                        ...node.data, 
                        status: data.status, 
                        response: data.response || node.data.response,
                        fileName: data.file_name || node.data.fileName,
                        downloadUrl: data.download_url || node.data.downloadUrl,
                      } 
                    };
                  }
                  return node;
                })
              );
            }
          } catch (e) {
            console.error('解析 WebSocket 訊息失敗', e);
          }
        };

      } catch (err) {
        console.error('建立 WebSocket 時發生錯誤', err);
        setWsStatus('error');
        socketRef.current = null;
      }
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (socketRef.current) {
        try { socketRef.current.close(); } catch (e) {}
      }
    };
  }, [setNodes]);

  const handleStartWorkflow = () => {
    if (!entryPointId) { 
      alert("請先左鍵點擊一個 AI 角色，將其設定為主要進入端口！"); 
      return; 
    }
    if (!initialPrompt || initialPrompt.trim() === '') { 
      alert("請在下方的對話框輸入您的初始指令！"); 
      return; 
    }
    
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        setInfoMessage('');
        setIsFinished(false);
        setFinalConversationId(null);
        setNodes(nds => nds.map(node => ({...node, data: {...node.data, response: null, status: undefined}})));
        
        const payload = {
          agents: workflowProcess,
          initialPrompt: initialPrompt
        };
        
        socketRef.current.send(JSON.stringify({ type: "start_workflow", payload: payload }));
    } else {
        alert("WebSocket 尚未連接，請稍後再試。");
    }
  };

  const handleFinalize = () => {
    if (onWorkflowComplete && finalConversationId) {
      onWorkflowComplete(finalConversationId);
    }
  };
  
  useImperativeHandle(ref, () => ({ startWorkflow: handleStartWorkflow }));
  const onDragOver = useCallback((event) => { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; }, []);
  const onNodeContextMenu = useCallback((event, node) => { event.preventDefault(); setContextMenu({ anchorEl: event.currentTarget, node: node }); }, []);
  const handleCloseContextMenu = () => setContextMenu({ anchorEl: null, node: null });
  useEffect(() => { setNodes((nds) => nds.map((node) => ({ ...node, data: { ...node.data, isEntryPoint: node.id === entryPointId } }))); }, [entryPointId, setNodes]);
  
  return (
    <Box sx={{ height: '100%', display: 'flex' }}>
      <Sidebar />
      <Box sx={{ flex: 1, height: '100%', position: 'relative' }} ref={reactFlowWrapper}>
        <Box sx={{position: 'absolute', top: 10, right: 10, zIndex: 10, display: 'flex', gap: 1, alignItems: 'center' }}>
             {infoMessage && (
                <Alert severity="info" icon={<CircularProgress size={20} />} sx={{ p: '0px 16px' }}>
                    {infoMessage}
                </Alert>
             )}
             <Chip 
               label={wsStatus === 'connected' ? '連線成功' : '連線中...'} 
               color={wsStatus === 'connected' ? 'success' : 'warning'}
               size="small"
             />
        </Box>
        <ReactFlow
          nodes={nodes} 
          edges={edges} 
          onNodesChange={onNodesChange} 
          onEdgesChange={handleEdgesChange}
          onConnect={onConnect} 
          onInit={setReactFlowInstance} 
          onDrop={onDrop}
          onDragOver={onDragOver} 
          fitView 
          onNodeClick={onNodeClick}
          onNodeContextMenu={onNodeContextMenu} 
          onPaneClick={handleCloseContextMenu}
          nodeTypes={nodeTypes}
        >
          <Controls />
          <Background variant="dots" gap={12} size={1} />
          <Box sx={{position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center', color: 'grey.400', zIndex: 0}}>
            {nodes.length === 0 && (
                <Paper sx={{ p: 4, backgroundColor:'rgba(240, 240, 240, 0.8)' }}>
                  <Typography variant="h4">討論會議</Typography>
                  <Typography>從左側拖拉 AI 角色至此處開始</Typography>
                </Paper>
            )}
          </Box>
        </ReactFlow>
        {isFinished && (
          <Paper sx={{ position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)', p: 2, zIndex: 10}} elevation={4}>
            <Button
              variant="contained"
              color="success"
              onClick={handleFinalize}
              startIcon={<DoneAll />}
            >
              看最終結果
            </Button>
            {infoMessage === '' && (
              <Button 
                variant="outlined" 
                sx={{ ml: 1 }}
                href={socketRef.current?.lastFinalDownloadUrl}
                onClick={(e) => { if (!socketRef.current?.lastFinalDownloadUrl) e.preventDefault(); }}
              >
                下載最終總結
              </Button>
            )}
          </Paper>
        )}
        <Menu open={Boolean(contextMenu.anchorEl)} onClose={handleCloseContextMenu} anchorEl={contextMenu.anchorEl} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }} transformOrigin={{ vertical: 'top', horizontal: 'center' }}>
            <MenuItem onClick={handleDeleteNode} sx={{ color: 'error.main' }}>刪除代理人</MenuItem>
        </Menu>
      </Box>
    </Box>
  );
});



const DiscussionBoardWrapper = React.forwardRef((props, ref) => (
  <ReactFlowProvider>
    <DiscussionBoard {...props} ref={ref} />
  </ReactFlowProvider>
));

export default DiscussionBoardWrapper;