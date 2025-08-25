import React, { useState, useEffect, useRef } from 'react';
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
import {
  Send as SendIcon,
  Delete as DeleteIcon,
  Add as AddIcon
} from '@mui/icons-material';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function Chat() {
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  loadConversations();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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

      const escapePipe = (s) => String(s).replace(/\|/g, '\\|');

      function tableToMarkdown(table) {
  const rows = Array.from(table.querySelectorAll('tr'));
  if (rows.length === 0) return '';
        const headerCells = Array.from(rows[0].querySelectorAll('th'));
        let md = '';

        // If first row has th use as header, otherwise use first row as header
        const headerRow = headerCells.length ? rows[0] : rows[0];
        const headerTexts = Array.from(headerRow.querySelectorAll('th,td')).map(td => escapePipe(nodeText(td).trim() || ''));
        md += `| ${headerTexts.join(' | ')} |\n`;
        md += `| ${Array(headerTexts.length).fill('---').join(' | ')} |\n`;

        const dataRows = headerCells.length ? rows.slice(1) : rows.slice(1);
        for (const r of dataRows) {
          const cells = Array.from(r.querySelectorAll('td,th')).map(td => escapePipe(nodeText(td).trim() || ''));
          // pad cells if less than header
          while (cells.length < headerTexts.length) cells.push('');
          md += `| ${cells.join(' | ')} |\n`;
        }
        return md + '\n';
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

  const loadConversations = async () => {
    try {
      const response = await axios.get('/api/chat/conversations');
      setConversations(response.data);
      
      if (response.data.length > 0 && !currentConversation) {
        setCurrentConversation(response.data[0]);
        setMessages(response.data[0].messages || []);
      }
    } catch (error) {
      setError('載入對話失敗');
    }
  };

  const loadConversation = async (conversation) => {
    try {
      const response = await axios.get(`/api/chat/conversations/${conversation.id}`);
      setCurrentConversation(response.data);
      setMessages(response.data.messages || []);
    } catch (error) {
      setError('載入對話詳情失敗');
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim()) return;

    const userMessage = {
      content: newMessage,
      is_user: true,
      created_at: new Date().toISOString()
    };

    // 立即顯示用戶消息
    setMessages(prev => [...prev, userMessage]);
    setNewMessage('');
    setLoading(true);

    try {
      const response = await axios.post('/api/chat/send', {
        content: newMessage,
        conversation_id: currentConversation?.id
      });

      // 添加機器人回應
      setMessages(prev => [...prev, response.data.message]);

      // 如果是新對話，更新對話列表
      if (!currentConversation || response.data.conversation_id !== currentConversation.id) {
        await loadConversations();
        const newConv = conversations.find(c => c.id === response.data.conversation_id);
        if (newConv) {
          setCurrentConversation(newConv);
        }
      }

    } catch (error) {
      setError('發送消息失敗');
      // 移除失敗的用戶消息
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
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
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex' }}>
      {/* 側邊欄 - 對話列表 */}
      <Box sx={{ width: 300, borderRight: 1, borderColor: 'divider' }}>
        <Paper sx={{ height: '100%', borderRadius: 0 }}>
          <Box sx={{ p: 2 }}>
            <Button
              fullWidth
              variant="contained"
              startIcon={<AddIcon />}
              onClick={startNewConversation}
            >
              新對話
            </Button>
          </Box>
          
          <Divider />
          
          <List sx={{ height: 'calc(100% - 80px)', overflow: 'auto' }}>
            {conversations.map((conv) => (
              <ListItem
                key={conv.id}
                button
                selected={currentConversation?.id === conv.id}
                onClick={() => loadConversation(conv)}
                sx={{
                  borderLeft: currentConversation?.id === conv.id ? 3 : 0,
                  borderColor: 'primary.main'
                }}
              >
                <ListItemText
                  primary={conv.title}
                  secondary={new Date(conv.updated_at).toLocaleDateString()}
                  primaryTypographyProps={{
                    noWrap: true,
                    fontSize: '0.9rem'
                  }}
                />
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteConversation(conv.id);
                  }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </ListItem>
            ))}
          </List>
        </Paper>
      </Box>

      {/* 主聊天區域 */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* 聊天標題 */}
        <Paper sx={{ p: 2, borderRadius: 0 }} elevation={1}>
          <Typography variant="h6">
            {currentConversation?.title || '新對話'}
          </Typography>
        </Paper>

        {/* 錯誤提示 */}
        {error && (
          <Alert severity="error" onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {/* 消息列表 */}
        <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
          {messages.map((message, index) => (
            <Box
              key={index}
              sx={{
                display: 'flex',
                justifyContent: message.is_user ? 'flex-end' : 'flex-start',
                mb: 2
              }}
            >
              <Paper
                sx={{
                  p: 2,
                  maxWidth: '70%',
                  backgroundColor: message.is_user ? 'primary.main' : 'grey.100',
                  color: message.is_user ? 'white' : 'text.primary'
                }}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{preprocessContent(message.content)}</ReactMarkdown>
                
                {!message.is_user && message.context_used && (
                  <Box sx={{ mt: 1 }}>
                    <Chip 
                      label="使用了知識庫" 
                      size="small" 
                      variant="outlined" 
                      sx={{ fontSize: '0.7rem' }}
                    />
                  </Box>
                )}
              </Paper>
            </Box>
          ))}
          
          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
              <Paper sx={{ p: 2, backgroundColor: 'grey.100' }}>
                <CircularProgress size={20} />
                <Typography variant="body2" sx={{ ml: 1, display: 'inline' }}>
                  正在思考...
                </Typography>
              </Paper>
            </Box>
          )}
          
          <div ref={messagesEndRef} />
        </Box>

        {/* 輸入區域 */}
        <Paper sx={{ p: 2, borderRadius: 0 }} elevation={1}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="輸入你的問題..."
              disabled={loading}
            />
            <Button
              variant="contained"
              onClick={sendMessage}
              disabled={loading || !newMessage.trim()}
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
