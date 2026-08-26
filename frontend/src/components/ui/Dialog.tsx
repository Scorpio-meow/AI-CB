import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import styles from './Dialog.module.css';
export interface DialogProps {
  open: boolean;
  onClose?: () => void;
  maxWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  fullWidth?: boolean;
  children: React.ReactNode;
  className?: string;
}
export const Dialog: React.FC<DialogProps> = ({
  open,
  onClose,
  maxWidth = 'sm',
  fullWidth = true,
  children,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);
  if (!open) return null;
  const maxWidthClass =
    maxWidth === 'xs'
      ? styles.maxWidthXs
      : maxWidth === 'md'
        ? styles.maxWidthMd
        : maxWidth === 'lg'
          ? styles.maxWidthLg
          : maxWidth === 'xl'
            ? styles.maxWidthXl
            : styles.maxWidthSm;
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose?.();
    }
  };
  return createPortal(
    <div className={styles.backdrop} onClick={handleBackdropClick} role="dialog" aria-modal="true">
      <div
        ref={containerRef}
        className={`${styles.container} ${maxWidthClass} ${fullWidth ? styles.fullWidth : ''} ${className}`}
      >
        {children}
      </div>
    </div>,
    document.body
  );
};
export const DialogTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  children,
  className = '',
  ...props
}) => {
  return (
    <h3 className={`${styles.title} ${className}`} {...props}>
      {children}
    </h3>
  );
};
export const DialogContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = '',
  ...props
}) => {
  return (
    <div className={`${styles.content} ${className}`} {...props}>
      {children}
    </div>
  );
};
export const DialogActions: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = '',
  ...props
}) => {
  return (
    <div className={`${styles.actions} ${className}`} {...props}>
      {children}
    </div>
  );
};
export const Modal = Dialog;