import React from 'react';
import { ChatMessageListProps } from './types';
import ChatMessageItem from './ChatMessageItem';
import { Button, Spinner, Chip, Icon } from '../../components/ui';
import styles from './ChatMessageList.module.css';
export const ChatMessageList: React.FC<ChatMessageListProps> = ({
  messages,
  loading,
  loadingMore,
  hasMoreMessages,
  onLoadMore,
  thinkOpenArr,
  onToggleThinking,
  onCopyMessage,
  onSelectPrompt,
  messagesEndRef,
  messagesTopRef,
}) => {
  const isEmpty = messages.length === 0;
  return (
    <div className={styles.container}>
      <div ref={messagesTopRef} />
      {hasMoreMessages && (
        <div className={styles.loadMoreContainer}>
          <Button
            size="sm"
            variant="outline"
            onClick={onLoadMore}
            disabled={loadingMore}
            startIcon={loadingMore ? <Spinner size={14} /> : undefined}
          >
            {loadingMore ? '正在載入更早訊息...' : '載入更早訊息'}
          </Button>
        </div>
      )}
      {isEmpty && !loading ? (
        <div className={styles.emptyContainer}>
          <div className={styles.emptyCard}>
            <div className={styles.emptyIcon}>
              <Icon name="bot" size={48} color="var(--color-primary)" />
            </div>
            <h3 className={styles.emptyTitle}>歡迎使用智慧知識庫對話</h3>
            <p className={styles.emptyDesc}>
              我是您的智慧知識助理。您可以詢問知識庫文檔、技術指引、專案流程或任何即時資訊問題。
            </p>
            <div className={styles.suggestPrompts}>
              <span className={styles.suggestTitle}>常見問題提示：</span>
              <div className={styles.suggestList}>
                {[
                  '請幫我分析並總結文檔的核心重點',
                  '如何結合知識庫與網路搜尋進行自主研究？',
                  '請解釋大型語言模型與 RAG 技術的運作原理',
                  '幫我撰寫一份專案規劃與技術選型建議',
                ].map((prompt, idx) => (
                  <Chip
                    key={idx}
                    icon={<Icon name="chat" size={14} />}
                    label={prompt}
                    size="sm"
                    variant="outlined"
                    onClick={() => {
                      if (onSelectPrompt) {
                        onSelectPrompt(prompt);
                      } else {
                        onCopyMessage(prompt);
                      }
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        messages.map((msg, index) => {
          const itemKey = `${msg.is_user ? 'user' : 'assistant'}-${msg.id ?? 'idx'}-${index}`;
          const thinkId = msg.id ?? index;
          return (
            <ChatMessageItem
              key={itemKey}
              message={msg}
              isThinkingOpen={Boolean(thinkOpenArr[thinkId])}
              onToggleThinking={() => onToggleThinking(thinkId)}
              onCopyMessage={onCopyMessage}
            />
          );
        })
      )}
      {loading && (messages.length === 0 || messages[messages.length - 1].is_user) && (
        <div className={styles.loadingRow}>
          <Icon name="bot" size={24} color="var(--color-primary)" />
          <div className={styles.loadingBubble}>
            <Spinner size={18} color="var(--color-primary)" />
            <span className={styles.loadingText}>正在檢索知識庫並生成回答...</span>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};
export default ChatMessageList;