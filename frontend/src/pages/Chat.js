import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Divider,
  CircularProgress,
  Alert,
  Chip
} from '@mui/material';
import { FaRobot } from "react-icons/fa";
import { Send as SendIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import DiscussionBoard from './DiscussionBoard';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

function Chat() {
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);
  const initialLoadDoneRef = useRef(false);

  const loadConversations = useCallback(async () => {
    try {
      const response = await axios.get('/api/chat/conversations');
      // Ensure conversations is always an array to avoid map errors
      const convs = Array.isArray(response.data) ? response.data : (response.data ? [response.data] : []);
      setConversations(convs);
      // auto-select first conversation only on first load
      if (convs.length > 0 && !initialLoadDoneRef.current) {
        setCurrentConversation(convs[0]);
        setMessages(convs[0].messages || []);
        initialLoadDoneRef.current = true;
      }
    } catch (error) {
      setError('載入對話失敗');
    }
  }, []);
  const [viewMode, setViewMode] = useState('chat');
  const discussionBoardRef = useRef(null);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    if (viewMode === 'chat') {
      scrollToBottom();
    }
  }, [messages, viewMode]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Simple preprocessing: convert HTML <br> tags to Markdown newlines
  const preprocessContent = (content) => {
    if (!content || typeof content !== 'string') return '';
    // If no HTML tags, return as-is
    if (content.indexOf('<') === -1) return content;

    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(content, 'text/html');

  // escapePipe removed (unused)

      function tableToMarkdown(table) {
  // Convert an HTML table DOM node into an HTML string (not markdown)
  const rows = Array.from(table.querySelectorAll('tr'));
  if (rows.length === 0) return '';

  // build header
  let thead = '';
  const firstRow = rows[0];
  const headerCells = Array.from(firstRow.querySelectorAll('th'));
  const headerCols = headerCells.length ? headerCells : Array.from(firstRow.querySelectorAll('td'));
  if (headerCols.length) {
    thead = '<thead><tr>' + headerCols.map(h => `<th>${nodeText(h).trim()}</th>`).join('') + '</tr></thead>';
  }

  // build body
  const bodyRows = headerCells.length ? rows.slice(1) : rows.slice(1);
  const tbody = '<tbody>' + bodyRows.map(r => {
    const cells = Array.from(r.querySelectorAll('td,th'));
    return '<tr>' + cells.map(c => `<td>${nodeText(c).trim()}</td>`).join('') + '</tr>';
  }).join('') + '</tbody>';

  return `<table class="converted-table">${thead}${tbody}</table>`;
      }

      function nodeText(node) {
        if (!node) return '';
        if (node.nodeType === Node.TEXT_NODE) return node.textContent || '';
        if (node.nodeType !== Node.ELEMENT_NODE) return '';
        const tag = node.tagName.toLowerCase();
        if (tag === 'br') return '\n\n';
        if (tag === 'p' || tag === 'div' || tag === 'section' || tag === 'header' || tag === 'footer') {
          return Array.from(node.childNodes).map(nodeText).join('') + '\n\n';
        }
        if (tag === 'strong' || tag === 'b') return `**${Array.from(node.childNodes).map(nodeText).join('').trim()}**`;
        if (tag === 'em' || tag === 'i') return `*${Array.from(node.childNodes).map(nodeText).join('').trim()}*`;
        if (tag === 'a') {
          const href = node.getAttribute('href') || '';
          const text = Array.from(node.childNodes).map(nodeText).join('').trim();
          return href ? `[${text}](${href})` : text;
        }
        if (tag === 'ul') {
          return Array.from(node.querySelectorAll(':scope > li')).map(li => `- ${Array.from(li.childNodes).map(nodeText).join('').trim()}`).join('\n') + '\n\n';
        }
        if (tag === 'ol') {
          return Array.from(node.querySelectorAll(':scope > li')).map((li, idx) => `${idx+1}. ${Array.from(li.childNodes).map(nodeText).join('').trim()}`).join('\n') + '\n\n';
        }
        if (tag === 'li') return `- ${Array.from(node.childNodes).map(nodeText).join('').trim()}\n`;
        if (tag === 'pre' || tag === 'code') return '```\n' + (node.textContent || '') + '\n```\n\n';
        if (tag === 'table') return tableToMarkdown(node);

        // default: concatenate children
        return Array.from(node.childNodes).map(nodeText).join('');
      }

      const body = doc.body || doc;
      const out = Array.from(body.childNodes).map(nodeText).join('').trim();
      // Post-process: convert pipe-like blocks to proper Markdown tables
      function convertPipeBlocksToTables(text) {
        const lines = text.split(/\r?\n/);
        const result = [];
        let i = 0;
        while (i < lines.length) {
          // detect start of a pipe block (line contains at least one | and not a code fence)
          if (lines[i].includes('|') && !lines[i].trim().startsWith('```')) {
            // collect contiguous pipe lines
            const block = [];
            let j = i;
            while (j < lines.length && lines[j].includes('|') && !lines[j].trim().startsWith('```')) {
              block.push(lines[j]);
              j++;
            }

            // analyze block: must have at least 1 pipe and at least 1 row
            if (block.length > 0) {
              // check if any line is a separator like | --- | --- |
              const hasSeparator = block.some(l => /^\s*\|?\s*[:-]+/.test(l.replace(/\s+/g, '')) || /-\s*\|\s*-/.test(l));
              if (!hasSeparator && block.length >= 2) {
                // create separator based on first row's column count
                const headerCells = block[0].split('|').map(s => s.trim()).filter(s => s.length > 0);
                const cols = headerCells.length || Math.max(1, block[0].split('|').length - 1);
                const sep = '| ' + Array(cols).fill('---').join(' | ') + ' |';
                // insert separator after first line
                const newBlock = [block[0], sep, ...block.slice(1)];
                result.push(...newBlock);
              } else {
                result.push(...block);
              }
            }

            i = j;
            continue;
          }

          result.push(lines[i]);
          i++;
        }

        return result.join('\n');
      }

      return convertPipeBlocksToTables(out);
    } catch (e) {
      // fallback: simple br replacement and strip tags
      return content.replace(/<br\s*\/?>(?=>)?/gi, '\n\n').replace(/<[^>]+>/g, '');
    }
  };


  const loadConversation = async (conversation) => {
    setViewMode('chat');
    try {
      const response = await axios.get(`/api/chat/conversations/${conversation.id}`);
      setCurrentConversation(response.data);
      setMessages(response.data.messages || []);
    } catch (error) {
      setError('載入對話詳情失敗');
    }
  };

  const sendChatMessage = async () => {
    if (!newMessage.trim() || viewMode !== 'chat') return;

    const userMessage = {
      content: newMessage,
      is_user: true,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);
    setNewMessage('');
    setLoading(true);

    try {
      const response = await axios.post('/api/chat/send', {
        content: newMessage,
        conversation_id: currentConversation?.id
      });
      setMessages(prev => [...prev, response.data.message]);

      // 如果是新對話，直接載入該對話的詳細內容，並在背景刷新對話列表，避免使用舊的 conversations state 覆寫剛建立的對話
      if (!currentConversation || response.data.conversation_id !== currentConversation.id) {
        try {
          // 使用現有的 loadConversation helper（接受一個含 id 屬性的參數）來載入完整對話
          await loadConversation({ id: response.data.conversation_id });
          // 非同步在背景刷新對話列表，但不要等待它完成以免覆寫目前選取
          loadConversations().catch(() => {});
        } catch (e) {
          // 若載入失敗，嘗試退而求其次地刷新整個對話列表
          await loadConversations();
        }
      }
    } catch (error) {
      setError('發送消息失敗');
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const handleStartWorkflow = () => {
    if (discussionBoardRef.current) {
      discussionBoardRef.current.startWorkflow();
    }
  };

  const handleSendMessage = () => {
    if (viewMode === 'discussion') {
      handleStartWorkflow();
    } else {
      sendChatMessage();
    }
  };

  const handleWorkflowComplete = (result) => {
    const systemMessage = {
      content: `**工作流執行完畢**\n\n---\n\n${result}`,
      is_user: false,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, systemMessage]);
    setViewMode('chat'); // Switch back to chat view to see the result
  };

  const deleteConversation = async (conversationId) => {
    try {
      await axios.delete(`/api/chat/conversations/${conversationId}`);
      await loadConversations();
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
        setMessages([]);
      }
    } catch (error) {
      setError('刪除對話失敗');
    }
  };

  const startNewConversation = () => {
    setCurrentConversation(null);
    setMessages([]);
    setViewMode('chat');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex' }}>
      {/* 側邊欄 - 這部分不變 */}
      <Box sx={{ width: 300, borderRight: 1, borderColor: 'divider', display: 'flex', flexDirection: 'column' }}>
        <Paper sx={{ height: '100%', borderRadius: 0 }}>
          <Box sx={{ p: 2, display: "flex", columnGap: 1 }}>
            <Button
              fullWidth
              variant={viewMode === 'chat' ? 'contained' : 'outlined'}
              startIcon={<AddIcon />}
              onClick={startNewConversation}
            >
              新對話
            </Button>
            <Button
              fullWidth
              variant={viewMode === 'discussion' ? 'contained' : 'outlined'}
              startIcon={<FaRobot />}
              onClick={() => setViewMode('discussion')}
            >
              AI討論
            </Button>
          </Box>
          <Divider />
          <List sx={{ height: 'calc(100% - 80px)', overflow: 'auto' }}>
            {(Array.isArray(conversations) ? conversations : []).map((conv) => (
              <ListItem
                key={conv.id}
                button
                selected={currentConversation?.id === conv.id && viewMode === 'chat'}
                onClick={() => loadConversation(conv)}
                sx={{
                  borderLeft: currentConversation?.id === conv.id && viewMode === 'chat' ? 3 : 0,
                  borderColor: 'primary.main'
                }}
              >
                <ListItemText
                  primary={conv.title}
                  secondary={new Date(conv.updated_at).toLocaleDateString()}
                  primaryTypographyProps={{
                    component: 'div',
                    noWrap: true,
                    fontSize: '0.9rem'
                  }}
                  secondaryTypographyProps={{ component: 'div' }}
                />
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id); }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </ListItem>
            ))}
          </List>
        </Paper>
      </Box>

      {/* 主區域 */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        
        {/* 主要內容區域 (會變動) */}
        <Box sx={{ flex: 1, overflow: 'hidden' }}>
            {viewMode === 'chat' ? (
            <>
                <Paper sx={{ p: 2, borderRadius: 0 }} elevation={1}>
                    <Typography variant="h6">{currentConversation?.title || '新對話'}</Typography>
                </Paper>
                {error && (<Alert severity="error" onClose={() => setError('')}>{error}</Alert>)}
                <Box sx={{ height: 'calc(100% - 68px)', overflow: 'auto', p: 2 }}>
                    {(Array.isArray(messages) ? messages : []).map((message, index) => {
            const msg = message || {};
            const isUser = !!msg.is_user;
            const content = msg.content || '';
            return (
                        <Box key={index} sx={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', mb: 2 }}>
                            <Paper sx={{ p: 2, maxWidth: '70%', backgroundColor: isUser ? 'primary.main' : 'grey.100', color: isUser ? 'white' : 'text.primary' }}>
                                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} children={preprocessContent(content)} components={{
                  // keep default rendering but allow table elements from raw HTML
                  table: ({node, ...props}) => <table className="converted-table" {...props} />
                }} />
                                {!isUser && msg.context_used && (
                                <Box sx={{ mt: 1 }}><Chip label="使用了知識庫" size="small" variant="outlined" sx={{ fontSize: '0.7rem' }}/></Box>
                                )}
                            </Paper>
                        </Box>
                      );
          })}
                    {loading && (
                        <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
                            <Paper sx={{ p: 2, backgroundColor: 'grey.100' }}>
                                <CircularProgress size={20} />
                                <Typography variant="body2" sx={{ ml: 1, display: 'inline' }}>正在思考...</Typography>
                            </Paper>
                        </Box>
                    )}
                    <div ref={messagesEndRef} />
                </Box>
            </>
            ) : (
                <DiscussionBoard 
                    ref={discussionBoardRef}
                    initialPrompt={newMessage} 
                    onWorkflowComplete={handleWorkflowComplete}
                />
            )}
        </Box>

        {/* 輸入區域 (固定在底部) */}
        <Paper sx={{ p: 2, borderRadius: 0, borderTop: 1, borderColor: 'divider' }} elevation={2}>
            <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
                fullWidth
                multiline
                maxRows={4}
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={loading}
                placeholder={
                    viewMode === 'discussion' 
                      ? '在此輸入工作流的初始指令...' 
                      : '輸入你的問題...'
                }
            />
            <Button
                variant="contained"
                onClick={handleSendMessage}
                sx={{ minWidth: 60 }}
            >
              <SendIcon />
            </Button>
            </Box>
        </Paper>
      </Box>
    </Box>
  );
}


export default Chat;