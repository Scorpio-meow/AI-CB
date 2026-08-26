import React from 'react';
import styles from './Chip.module.css';
import { Icon } from './Icon';
export interface ChipProps extends React.HTMLAttributes<HTMLDivElement> {
  label?: React.ReactNode;
  icon?: React.ReactNode;
  onDelete?: () => void;
  onClick?: (e: React.MouseEvent<HTMLDivElement>) => void;
  variant?: 'filled' | 'outlined';
  color?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info' | 'secondary';
  size?: 'sm' | 'md' | 'small' | 'medium';
}
export const Chip: React.FC<ChipProps> = ({
  label,
  icon,
  onDelete,
  onClick,
  variant = 'filled',
  color = 'default',
  size = 'md',
  children,
  className = '',
  ...props
}) => {
  const normalizedSize = size === 'small' || size === 'sm' ? styles.sizeSm : styles.sizeMd;
  const colorClass =
    color === 'primary' || color === 'secondary'
      ? styles.primary
      : color === 'success'
        ? styles.success
        : color === 'warning'
          ? styles.warning
          : color === 'error'
            ? styles.error
            : color === 'info'
              ? styles.info
              : '';
  const classes = [
    styles.chip,
    normalizedSize,
    colorClass,
    variant === 'outlined' ? styles.outlined : '',
    onClick ? styles.clickable : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');
  return (
    <div className={classes} onClick={onClick} {...props}>
      {icon && <span style={{ display: 'inline-flex', flexShrink: 0 }}>{icon}</span>}
      <span>{label || children}</span>
      {onDelete && (
        <button
          type="button"
          className={styles.deleteButton}
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          aria-label="Delete"
        >
          <Icon name="close" size={12} />
        </button>
      )}
    </div>
  );
};
export const Badge = Chip;