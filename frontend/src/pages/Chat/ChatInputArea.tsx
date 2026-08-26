import React, { useRef, useEffect, useState, useCallback } from 'react';
import { ChatInputAreaProps, ChatAttachment } from './types';
import { Tooltip, Spinner, Icon } from '../../components/ui';
import styles from './ChatInputArea.module.css';

const formatFileSize = (bytes?: number): string => {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const getBadgeClass = (filename: string): { className: string; label: string } => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  if (ext === 'pdf') return { className: styles.badgePdf, label: 'PDF' };
  if (['doc', 'docx'].includes(ext)) return { className: styles.badgeDocx, label: 'DOC' };
  if (['xls', 'xlsx', 'csv'].includes(ext)) return { className: styles.badgeXlsx, label: ext.toUpperCase() };
  if (['ppt', 'pptx'].includes(ext)) return { className: styles.badgePptx, label: 'PPT' };
  if (['js', 'ts', 'jsx', 'tsx', 'py', 'json', 'html', 'css', 'sql'].includes(ext)) {
    return { className: styles.badgeCode, label: ext.toUpperCase() };
  }
  return { className: '', label: ext ? ext.toUpperCase() : 'FILE' };
};

export const ChatInputArea: React.FC<ChatInputAreaProps> = ({
  value,
  onChange,
  onSend,
  loading,
  disabled = false,
  attachments = [],
  onAddAttachments,
  onRemoveAttachment,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const processFiles = useCallback((files: FileList | File[]) => {
    const newAttachments: ChatAttachment[] = [];
    const fileList = Array.from(files);

    let processedCount = 0;
    fileList.forEach((file) => {
      const isImg = file.type.startsWith('image/');
      const reader = new FileReader();

      reader.onload = (e) => {
        const dataUrl = e.target?.result as string;
        newAttachments.push({
          id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          filename: file.name,
          file_type: file.type || 'application/octet-stream',
          file_size: file.size,
          data_url: dataUrl,
          file,
        });
        processedCount++;
        if (processedCount === fileList.length && onAddAttachments) {
          onAddAttachments(newAttachments);
        }
      };

      if (isImg || file.size < 15 * 1024 * 1024) {
        reader.readAsDataURL(file);
      } else {
        newAttachments.push({
          id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          filename: file.name,
          file_type: file.type || 'application/octet-stream',
          file_size: file.size,
          file,
        });
        processedCount++;
        if (processedCount === fileList.length && onAddAttachments) {
          onAddAttachments(newAttachments);
        }
      }
    });
  }, [onAddAttachments]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!loading && !disabled && (value.trim() || attachments.length > 0)) {
        onSend();
      }
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    const pastedFiles: File[] = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.indexOf('image') !== -1 || item.kind === 'file') {
        const file = item.getAsFile();
        if (file) {
          pastedFiles.push(file);
        }
      }
    }

    if (pastedFiles.length > 0) {
      e.preventDefault();
      processFiles(pastedFiles);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(e.dataTransfer.files);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(e.target.files);
      e.target.value = '';
    }
  };

  useEffect(() => {
    if (!loading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [loading]);

  const hasContent = Boolean(value.trim()) || attachments.length > 0;

  return (
    <div className={styles.container}>
      <div
        className={`${styles.inputCard} ${isDragging ? styles.dropActive : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* 附件預覽列 */}
        {attachments.length > 0 && (
          <div className={styles.attachmentPreviewBar}>
            {attachments.map((att, idx) => {
              const isImg = att.file_type.startsWith('image/') || Boolean(att.data_url?.startsWith('data:image/'));
              const badge = getBadgeClass(att.filename);

              if (isImg && att.data_url) {
                return (
                  <div key={att.id || idx} className={styles.imagePreviewCard}>
                    <img src={att.data_url} alt={att.filename} className={styles.imagePreviewThumb} />
                    <button
                      type="button"
                      className={styles.removeAttachmentBtn}
                      onClick={() => onRemoveAttachment && onRemoveAttachment(idx)}
                      title="移除圖片"
                    >
                      <Icon name="close" size={12} />
                    </button>
                  </div>
                );
              }

              return (
                <div key={att.id || idx} className={styles.filePreviewCard}>
                  <span className={`${styles.fileFormatBadge} ${badge.className}`}>
                    {badge.label}
                  </span>
                  <div className={styles.fileInfo}>
                    <span className={styles.fileName} title={att.filename}>{att.filename}</span>
                    {att.file_size && <span className={styles.fileSize}>{formatFileSize(att.file_size)}</span>}
                  </div>
                  <button
                    type="button"
                    className={styles.removeFileBtn}
                    onClick={() => onRemoveAttachment && onRemoveAttachment(idx)}
                    title="移除檔案"
                  >
                    <Icon name="close" size={14} />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        <div className={styles.inputRow}>
          {/* 上傳檔案/圖片按鈕 */}
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            multiple
            accept=".png,.jpg,.jpeg,.webp,.gif,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.csv,.txt,.md,.json,.js,.ts,.py,.html,.css"
            onChange={handleFileInputChange}
          />
          <Tooltip title="上傳檔案或圖片 (亦支援截圖貼上 Ctrl+V / 拖曳)">
            <button
              type="button"
              className={styles.attachButton}
              onClick={() => fileInputRef.current?.click()}
              disabled={loading || disabled}
              aria-label="上傳檔案或圖片"
            >
              <Icon name="upload" size={18} />
            </button>
          </Tooltip>

          <textarea
            ref={textareaRef}
            rows={1}
            className={styles.textarea}
            placeholder="請輸入您的問題... (支援多行、貼上圖片或拖曳檔案)"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            disabled={loading || disabled}
          />

          <Tooltip title="發送訊息 (Enter)">
            <button
              type="button"
              className={`${styles.sendButton} ${hasContent && !loading ? styles.sendButtonActive : ''}`}
              onClick={onSend}
              disabled={loading || disabled || !hasContent}
              aria-label="發送訊息"
            >
              {loading ? (
                <Spinner size={18} color="var(--color-primary)" />
              ) : (
                <Icon name="send" size={18} />
              )}
            </button>
          </Tooltip>
        </div>
      </div>

      <div className={styles.hintRow}>
        <span className={styles.dragHint}>
          <Icon name="image" size={13} /> 支援圖片貼上與各類文件解析
        </span>
        <span className={styles.hint}>按 Enter 發送，Shift + Enter 換行</span>
      </div>
    </div>
  );
};

export default ChatInputArea;