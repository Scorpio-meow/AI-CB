import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import styles from './Snackbar.module.css';
export interface SnackbarProps {
  open: boolean;
  autoHideDuration?: number;
  onClose?: (event?: React.SyntheticEvent | Event, reason?: string) => void;
  message?: React.ReactNode;
  children?: React.ReactNode;
  anchorOrigin?: {
    vertical: 'top' | 'bottom';
    horizontal: 'left' | 'center' | 'right';
  };
  className?: string;
}
export const Snackbar: React.FC<SnackbarProps> = ({
  open,
  autoHideDuration = 4000,
  onClose,
  message,
  children,
  anchorOrigin = { vertical: 'bottom', horizontal: 'center' },
  className = '',
}) => {
  useEffect(() => {
    if (!open || !autoHideDuration) return;
    const timer = setTimeout(() => {
      onClose?.(undefined, 'timeout');
    }, autoHideDuration);
    return () => clearTimeout(timer);
  }, [open, autoHideDuration, onClose]);
  if (!open) return null;
  const { vertical, horizontal } = anchorOrigin;
  const positionClass =
    vertical === 'top'
      ? horizontal === 'left'
        ? styles.topLeft
        : horizontal === 'right'
          ? styles.topRight
          : styles.topCenter
      : horizontal === 'left'
        ? styles.bottomLeft
        : horizontal === 'right'
          ? styles.bottomRight
          : styles.bottomCenter;
  return createPortal(
    <div className={`${styles.snackbar} ${positionClass} ${className}`}>
      {children || <div className={styles.defaultMessage}>{message}</div>}
    </div>,
    document.body
  );
};