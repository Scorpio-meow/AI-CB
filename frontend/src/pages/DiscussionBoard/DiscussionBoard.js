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
    const websocketURL = 'ws://localhost:8000/api/workflow/ws';
    socketRef.current = new WebSocket(websocketURL);
    socketRef.current.onopen = () => { console.log("WebSocket 連線已建立"); setWsStatus('connected'); };
    socketRef.current.onclose = () => { console.log("WebSocket 連線已關閉"); setWsStatus('disconnected'); };
    socketRef.current.onerror = (error) => { console.error("WebSocket 錯誤:", error); setWsStatus('error'); };

    socketRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("收到後端更新:", data);
      
      if (data.status === 'finished') {
        setInfoMessage('');
        setIsFinished(true);
        setFinalConversationId(data.conversation_id);
      } else if (data.status === 'error') {
        setInfoMessage('工作流執行出錯');
        setIsFinished(true);
      } else if (data.status === 'info') {
        setInfoMessage(data.message);
      } else if (data.nodeId) {
        setNodes((nds) =>
          nds.map((node) => {
            if (node.id === data.nodeId) {
              return { ...node, data: { ...node.data, status: data.status, response: data.response || node.data.response } };
            }
            return node;
          })
        );
      }
    };

    return () => { if (socketRef.current) socketRef.current.close(); };
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