import React from 'react';
import { createPortal } from 'react-dom';
import { ChatSidebarProps } from './types';
import { Button, IconButton, Tooltip, Spinner, Icon } from '../../components/ui';
import styles from './ChatSidebar.module.css';
export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  open,
  onClose,
  conversations,
  currentConversation,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  loading,
}) => {
  const sidebarContent = (
    <div className={styles.sidebarInner}>
      <div className={styles.newButtonArea}>
        <Button
          fullWidth
          variant="primary"
          startIcon={<Icon name="add" size={18} />}
          onClick={onNewConversation}
        >
          開啟新對話
        </Button>
      </div>
      <div className={styles.divider} />
      <div className={styles.listArea}>
        <span className={styles.sectionTitle}>歷史對話記錄</span>
        {loading && conversations.length === 0 ? (
          <div className={styles.loadingCenter}>
            <Spinner size={24} color="var(--color-primary)" />
          </div>
        ) : conversations.length === 0 ? (
          <div className={styles.emptyText}>尚無歷史對話</div>
        ) : (
          <div>
            {conversations.map((conv, idx) => {
              const isSelected = currentConversation?.id === conv.id;
              return (
                <div
                  key={conv.id ? `conv-${conv.id}` : `conv-${idx}`}
                  className={styles.conversationItem}
                >
                  <button
                    type="button"
                    className={`${styles.conversationButton} ${isSelected ? styles.conversationSelected : ''}`}
                    onClick={() => {
                      onSelectConversation(conv.id);
                      if (onClose) onClose();
                    }}
                  >
                    <Icon
                      name="chat"
                      size={18}
                      color={isSelected ? 'var(--color-primary)' : 'var(--text-secondary)'}
                    />
                    <span className={styles.conversationTitle}>{conv.title || '對話'}</span>
                  </button>
                  <Tooltip title="刪除此對話">
                    <IconButton
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conv.id);
                      }}
                      className={styles.deleteButton}
                      aria-label="刪除對話"
                    >
                      <Icon name="delete" size={16} />
                    </IconButton>
                  </Tooltip>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
  return (
    <>
      <aside className={styles.desktopSidebar}>
        {sidebarContent}
      </aside>
      {open &&
        createPortal(
          <>
            <div className={styles.mobileBackdrop} onClick={onClose} />
            <div className={styles.mobileDrawer}>{sidebarContent}</div>
          </>,
          document.body
        )}
    </>
  );
};
export default ChatSidebar;