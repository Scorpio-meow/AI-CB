import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DOMPurify from 'dompurify';
import { ChatMessageItemProps } from './types';
import ThinkBlock from './ThinkBlock';
import SourceBadges from './SourceBadges';
import ResearchTraceBlock from './ResearchTraceBlock';
import { Avatar, Tooltip, IconButton, Spinner, Icon } from '../../components/ui';
import styles from './ChatMessageItem.module.css';

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  message,
  isThinkingOpen,
  onToggleThinking,
  onCopyMessage,
}) => {
  const isUser = message.is_user;

  const { thinkContent, mainContent } = useMemo(() => {
    const rawContent = message.content || '';
    const thinkMatch = rawContent.match(/<think>([\s\S]*?)<\/think>/);

    if (thinkMatch) {
      const think = thinkMatch[1].trim();
      const content = rawContent.replace(/<think>[\s\S]*?<\/think>/, '').trim();
      return { thinkContent: think, mainContent: content };
    }

    return {
      thinkContent: null,
      mainContent: rawContent,
    };
  }, [message.content]);

  const sanitizedContent = useMemo(() => {
    return DOMPurify.sanitize(mainContent);
  }, [mainContent]);

  const traceFromContext = useMemo(() => {
    if (message.research_trace && message.research_trace.length > 0) {
      return message.research_trace;
    }
    if (message.context_used) {
      try {
        const parsed = typeof message.context_used === 'string' ? JSON.parse(message.context_used) : message.context_used;
        if (parsed && typeof parsed === 'object' && Array.isArray(parsed.research_trace)) {
          return parsed.research_trace;
        }
      } catch {}
    }
    return [];
  }, [message.research_trace, message.context_used]);

  const sourcesFromContext = useMemo(() => {
    if (message.sources && message.sources.length > 0) {
      return message.sources;
    }
    if (message.context_used) {
      try {
        const parsed = typeof message.context_used === 'string' ? JSON.parse(message.context_used) : message.context_used;
        if (Array.isArray(parsed)) {
          return parsed;
        }
        if (parsed && typeof parsed === 'object' && Array.isArray(parsed.sources)) {
          return parsed.sources;
        }
      } catch {}
    }
    return [];
  }, [message.sources, message.context_used]);

  const sourcesDetailFromContext = useMemo(() => {
    if (message.sources_detail && message.sources_detail.length > 0) {
      return message.sources_detail;
    }
    if (message.context_used) {
      try {
        const parsed = typeof message.context_used === 'string' ? JSON.parse(message.context_used) : message.context_used;
        if (parsed && typeof parsed === 'object' && Array.isArray(parsed.sources_detail)) {
          return parsed.sources_detail;
        }
      } catch {}
    }
    return [];
  }, [message.sources_detail, message.context_used]);

  const attachmentsFromContext = useMemo(() => {
    if (message.attachments && message.attachments.length > 0) {
      return message.attachments;
    }
    if (message.context_used) {
      try {
        const parsed = typeof message.context_used === 'string' ? JSON.parse(message.context_used) : message.context_used;
        if (parsed && typeof parsed === 'object' && Array.isArray(parsed.attachments)) {
          return parsed.attachments;
        }
      } catch {}
    }
    return [];
  }, [message.attachments, message.context_used]);

  const [lightboxImg, setLightboxImg] = React.useState<string | null>(null);

  const hasTrace = traceFromContext.length > 0;
  const hasText = Boolean(mainContent.trim());
  const hasAttachments = attachmentsFromContext.length > 0;

  return (
    <div className={`${styles.container} ${isUser ? styles.userContainer : ''}`}>
      <Avatar
        size={36}
        className={isUser ? styles.avatarUser : styles.avatarBot}
      >
        <Icon name={isUser ? 'person' : 'bot'} size={18} />
      </Avatar>

      <div
        className={`${styles.contentWrapper} ${isUser ? styles.alignEnd : styles.alignStart}`}
      >
        <div
          className={`${styles.bubble} ${isUser ? styles.bubbleUser : styles.bubbleBot}`}
        >
          {/* 訊息附件展示 */}
          {hasAttachments && (
            <div className={styles.attachmentGallery}>
              {attachmentsFromContext.map((att: any, idx: number) => {
                const isImg = att.file_type?.startsWith('image/') || Boolean(att.data_url?.startsWith('data:image/'));
                if (isImg && att.data_url) {
                  return (
                    <img
                      key={idx}
                      src={att.data_url}
                      alt={att.filename || '圖片'}
                      className={styles.messageImage}
                      onClick={() => setLightboxImg(att.data_url)}
                      title="點擊放大圖片"
                    />
                  );
                }
                const ext = (att.filename || '').split('.').pop()?.toUpperCase() || 'FILE';
                return (
                  <div key={idx} className={styles.messageFileCard}>
                    <span className={styles.fileBadge}>{ext}</span>
                    <span>{att.filename}</span>
                  </div>
                );
              })}
            </div>
          )}

          {!isUser && hasTrace && (
            <ResearchTraceBlock
              trace={traceFromContext}
              hasContent={hasText}
              isStreaming={!message.id || Number(message.id) > 1000000000}
            />
          )}

          {!isUser && thinkContent && (
            <ThinkBlock
              thinkContent={thinkContent}
              isOpen={isThinkingOpen}
              onToggle={onToggleThinking}
            />
          )}

          {isUser ? (
            <div className={styles.userText}>{mainContent}</div>
          ) : !hasText && !hasTrace ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0', color: 'var(--text-secondary)', fontSize: '13px' }}>
              <Spinner size={16} color="var(--color-primary)" />
              <span>AI 正在分析您的問題...</span>
            </div>
          ) : hasText ? (
            <div className={styles.markdownBody}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{sanitizedContent}</ReactMarkdown>
            </div>
          ) : null}

          {!isUser && (
            <SourceBadges
              sources={sourcesFromContext}
              sourcesDetail={sourcesDetailFromContext}
            />
          )}
        </div>

        {/* 圖片全螢幕燈箱 */}
        {lightboxImg && (
          <div className={styles.lightboxOverlay} onClick={() => setLightboxImg(null)}>
            <img src={lightboxImg} alt="預覽" className={styles.lightboxImage} />
          </div>
        )}

        <div className={styles.footer}>
          {message.created_at && (
            <span className={styles.timestamp}>
              {new Date(message.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          )}

          {hasText && (
            <Tooltip title="複製訊息內容">
              <IconButton
                size="sm"
                onClick={() => onCopyMessage(mainContent)}
                className={styles.copyButton}
                aria-label="複製訊息內容"
              >
                <Icon name="copy" size={14} />
              </IconButton>
            </Tooltip>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatMessageItem;