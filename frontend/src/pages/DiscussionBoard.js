import React, { useState, useCallback, useRef } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
} from 'reactflow';
import 'reactflow/dist/style.css'; // 引入 React Flow 樣式
import { Box, Paper, Typography, List, ListItem, ListItemText } from '@mui/material';

// 側邊欄提供的 AI 角色
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
    <Box sx={{ width: 250, borderRight: 1, borderColor: 'divider', p: 1 }}>
        <Typography variant="h6" sx={{p:1}}>AI 角色</Typography>
      <List>
        {agentTypes.map((agent) => (
          <ListItem
            key={agent.type}
            onDragStart={(event) => onDragStart(event, agent.type, agent.label)}
            draggable
            sx={{
              cursor: 'grab',
              backgroundColor: 'grey.200',
              borderRadius: 1,
              mb: 1,
              '&:hover': {
                backgroundColor: 'grey.300',
              },
            }}
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

const DiscussionBoard = () => {
  const reactFlowWrapper = useRef(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);

  const onConnect = useCallback((params) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const { nodeType, label } = JSON.parse(event.dataTransfer.getData('application/reactflow'));
      
      // 檢查是否為有效的 nodeType
      if (typeof nodeType === 'undefined' || !nodeType) {
        return;
      }

      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const newNode = {
        id: getId(),
        type: 'default', // 你可以建立自定義節點
        position,
        data: { label: `${label}` },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes]
  );

  return (
    <Box sx={{ height: '100%', display: 'flex' }}>
      <Sidebar />
      <Box sx={{ flex: 1, height: '100%' }} ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          fitView
        >
          <Controls />
          <Background variant="dots" gap={12} size={1} />
           <Box
                sx={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    textAlign: 'center',
                    color: 'grey.400',
                    zIndex: 0,
                }}
            >
                {nodes.length === 0 && (
                    <Paper sx={{ p: 4, backgroundColor:'rgba(240, 240, 240, 0.8)' }}>
                        <Typography variant="h4">討論會議</Typography>
                        <Typography>從左側拖拉 AI 角色至此處開始</Typography>
                    </Paper>
                )}
            </Box>
        </ReactFlow>
      </Box>
    </Box>
  );
};


// 你需要將 DiscussionBoard 包在 ReactFlowProvider 中
function DiscussionBoardWrapper() {
    return (
        <ReactFlowProvider>
            <DiscussionBoard />
        </ReactFlowProvider>
    )
}

export default DiscussionBoardWrapper;