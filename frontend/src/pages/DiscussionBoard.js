import React, { useState, useCallback, useRef, useEffect, useMemo, useImperativeHandle } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Box, Paper, Typography, List, ListItem, ListItemText, Menu, MenuItem, Button, Chip } from '@mui/material';
import AgentNode from './AgentNode';

const agentTypes = [
  { type: 'pm', label: 'PM', description: '有事找我嗎~~' },
  { type: 'engineer', label: '工程師', description: '有事找我嗎~~' },
  { type: 'ba', label: '業務分析師', description: '有事找我嗎~~' },
];

const Sidebar = () => {
  const onDragStart = (event, nodeType, label) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({ nodeType, label }));
    event.dataTransfer.effectAllowed = 'move';
  };
  
  return (
    <Box sx={{ width: 250, borderRight: 1, borderColor: 'divider', p: 1, backgroundColor: '#f9f9f9' }}>
        <Typography variant="h6" sx={{p:1}}>AI 角色</Typography>
      <List>
        {agentTypes.map((agent) => (
          <ListItem key={agent.type} onDragStart={(event) => onDragStart(event, agent.type, agent.label)} draggable
            sx={{ cursor: 'grab', backgroundColor: 'white', border: '1px solid #ddd', borderRadius: 2, mb: 1, '&:hover': { backgroundColor: 'grey.100', borderColor: 'primary.main' } }}
          >
            <ListItemText primary={agent.label} secondary={agent.description} />
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

let id = 0;
const getId = () => `dndnode_${id++}`;

// userId prop 已經不是建立連線所必需的了，可以考慮移除
const DiscussionBoard = React.forwardRef(({ initialPrompt, onWorkflowComplete }, ref) => { 
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [entryPointId, setEntryPointId] = useState(null);
  const [contextMenu, setContextMenu] = useState({ anchorEl: null, node: null });

  // === WebSocket 相關狀態 ===
  const socketRef = useRef(null);
  const reactFlowWrapper = useRef(null); 
  const [wsStatus, setWsStatus] = useState('disconnected');
  const [runStatus, setRunStatus] = useState('idle');
  
  const nodeTypes = useMemo(() => ({ agent: AgentNode }), []);

  // === WebSocket 連線與事件處理 ===
  useEffect(() => {
    const websocketURL = 'ws://localhost:8001/api/workflow/ws';
    socketRef.current = new WebSocket(websocketURL);

    socketRef.current.onopen = () => {
      console.log("WebSocket 連線已建立");
      setWsStatus('connected');
    };

    socketRef.current.onclose = () => {
      console.log("WebSocket 連線已關閉");
      setWsStatus('disconnected');
    };

    socketRef.current.onerror = (error) => {
      console.error("WebSocket 錯誤:", error);
      setWsStatus('error');
    };

    // 監聽從後端來的訊息
    socketRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("收到後端更新:", data);

      if (data.status === 'started') {
        setRunStatus('running');
      } else if (data.status === 'finished' || data.status === 'error') {
        setRunStatus(data.status);
        if (data.status === 'finished' && data.final_artical && onWorkflowComplete) {
          onWorkflowComplete(data.final_artical);
        }
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
                },
              };
            }
            return node;
          })
        );
      }
    };

    // 組件卸載時的清理函數
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [setNodes, onWorkflowComplete]);

  // === 觸發工作流的函數 ===
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
        setNodes(nds => nds.map(node => ({...node, data: {...node.data, response: null, status: undefined}})));
        
        const workflowPayload = {
            nodes,
            edges,
            entryPointId,
            initialPrompt,
        };

        socketRef.current.send(JSON.stringify({
            type: "start_workflow",
            payload: workflowPayload
        }));
        setRunStatus('running');
    } else {
        alert("WebSocket 尚未連接，請稍後再試。");
    }
  };

  useImperativeHandle(ref, () => ({
    startWorkflow: handleStartWorkflow,
  }));

  const onConnect = useCallback((params) => setEdges((eds) => addEdge(params, eds)), [setEdges]);
  const onNodeContextMenu = useCallback((event, node) => { event.preventDefault(); setContextMenu({ anchorEl: event.currentTarget, node: node }); }, [setContextMenu]);
  const handleCloseContextMenu = () => setContextMenu({ anchorEl: null, node: null });
  const handleDeleteNode = () => { if (contextMenu.node) { const nodeIdToDelete = contextMenu.node.id; setNodes((nds) => nds.filter((node) => node.id !== nodeIdToDelete)); setEdges((eds) => eds.filter((edge) => edge.source !== nodeIdToDelete && edge.target !== nodeIdToDelete)); if(entryPointId === nodeIdToDelete) setEntryPointId(null); handleCloseContextMenu(); } };
  const onNodeClick = useCallback((event, node) => { setEntryPointId(node.id); }, []);
  const onDrop = useCallback( (event) => { event.preventDefault(); const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect(); const { nodeType, label } = JSON.parse(event.dataTransfer.getData('application/reactflow')); if (typeof nodeType === 'undefined' || !nodeType) return; const position = reactFlowInstance.project({ x: event.clientX - reactFlowBounds.left, y: event.clientY - reactFlowBounds.top, }); const newNode = { id: getId(), type: 'agent', position, data: { originalLabel: label, label: label, response: null, isEntryPoint: false, }, }; setNodes((nds) => nds.concat(newNode)); }, [reactFlowInstance, setNodes] );
  const onDragOver = useCallback((event) => { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; }, []);
  useEffect(() => { setNodes((nds) => nds.map((node) => { const isEntryPoint = node.id === entryPointId; const label = isEntryPoint ? `${node.data.originalLabel} (入口)` : node.data.originalLabel; return { ...node, data: { ...node.data, label: label, isEntryPoint: isEntryPoint, }, }; })); }, [entryPointId, setNodes]);

  return (
    <Box sx={{ height: '100%', display: 'flex' }}>
      <Sidebar />
      <Box sx={{ flex: 1, height: '100%', position: 'relative' }} ref={reactFlowWrapper}>
        <Box sx={{position: 'absolute', top: 10, right: 10, zIndex: 10}}>
             <Chip 
               label={wsStatus === 'connected' ? '連線成功' : '連線中...'} 
               color={wsStatus === 'connected' ? 'success' : 'warning'}
               size="small"
            />
        </Box>
        <ReactFlow
          nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          onConnect={onConnect} onInit={setReactFlowInstance} onDrop={onDrop}
          onDragOver={onDragOver} fitView onNodeClick={onNodeClick}
          onNodeContextMenu={onNodeContextMenu} onPaneClick={handleCloseContextMenu}
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
        <Menu open={Boolean(contextMenu.anchorEl)} onClose={handleCloseContextMenu} anchorEl={contextMenu.anchorEl} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }} transformOrigin={{ vertical: 'top', horizontal: 'center' }}>
            <MenuItem onClick={handleDeleteNode} sx={{ color: 'error.main' }}>刪除代理人</MenuItem>
        </Menu>
      </Box>
    </Box>
  );
});

// Wrapper 不變
const DiscussionBoardWrapper = React.forwardRef((props, ref) => (
    <ReactFlowProvider>
        <DiscussionBoard {...props} ref={ref} />
    </ReactFlowProvider>
));

export default DiscussionBoardWrapper;