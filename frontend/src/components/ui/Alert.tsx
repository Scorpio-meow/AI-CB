import React from 'react';
import styles from './Alert.module.css';
import { Icon } from './Icon';
export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  severity?: 'success' | 'info' | 'warning' | 'error';
  icon?: React.ReactNode;
  action?: React.ReactNode;
  onClose?: () => void;
}
export const Alert: React.FC<AlertProps> = ({
  severity = 'info',
  icon,
  action,
  onClose,
  children,
  className = '',
  ...props
}) => {
  const severityClass =
    severity === 'success'
      ? styles.success
      : severity === 'warning'
        ? styles.warning
        : severity === 'error'
          ? styles.error
          : styles.info;
  const defaultIcon =
    severity === 'success' ? (
      <Icon name="check-circle" size={18} />
    ) : severity === 'warning' ? (
      <Icon name="warning" size={18} />
    ) : severity === 'error' ? (
      <Icon name="error" size={18} />
    ) : (
      <Icon name="info" size={18} />
    );
  return (
    <div className={`${styles.alert} ${severityClass} ${className}`} role="alert" {...props}>
      <div className={styles.icon}>{icon !== undefined ? icon : defaultIcon}</div>
      <div className={styles.message}>{children}</div>
      {(action || onClose) && (
        <div className={styles.action}>
          {action}
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                padding: '2px',
                color: 'currentColor',
                display: 'inline-flex',
              }}
              aria-label="Close"
            >
              <Icon name="close" size={16} />
            </button>
          )}
        </div>
      )}
    </div>
  );
};