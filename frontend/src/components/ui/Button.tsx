import React, { forwardRef } from 'react';
import styles from './Button.module.css';
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'text' | 'danger' | 'contained' | 'outlined';
  size?: 'sm' | 'md' | 'lg' | 'small' | 'medium' | 'large';
  fullWidth?: boolean;
  loading?: boolean;
  startIcon?: React.ReactNode;
  endIcon?: React.ReactNode;
  iconOnly?: boolean;
  color?: 'primary' | 'secondary' | 'error' | 'inherit' | string;
}
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      fullWidth = false,
      loading = false,
      startIcon,
      endIcon,
      iconOnly = false,
      className = '',
      disabled,
      color,
      ...props
    },
    ref
  ) => {
    const normalizedVariant =
      variant === 'contained' ? 'primary' : variant === 'outlined' ? 'outline' : variant;
    const normalizedSize =
      size === 'small' ? 'sm' : size === 'medium' ? 'md' : size === 'large' ? 'lg' : size;
    const variantClass =
      normalizedVariant === 'secondary'
        ? styles.variantSecondary
        : normalizedVariant === 'outline'
          ? styles.variantOutline
          : normalizedVariant === 'text'
            ? styles.variantText
            : normalizedVariant === 'danger'
              ? styles.variantDanger
              : styles.variantPrimary;
    const sizeClass =
      normalizedSize === 'sm'
        ? styles.sizeSm
        : normalizedSize === 'lg'
          ? styles.sizeLg
          : styles.sizeMd;
    const classes = [
      styles.button,
      variantClass,
      sizeClass,
      fullWidth ? styles.fullWidth : '',
      iconOnly ? styles.iconOnly : '',
      className,
    ]
      .filter(Boolean)
      .join(' ');
    return (
      <button ref={ref} className={classes} disabled={disabled || loading} {...props}>
        {loading ? (
          <span style={{ display: 'inline-flex', animation: 'spin 1s linear infinite' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="12" />
            </svg>
          </span>
        ) : (
          startIcon && <span style={{ display: 'inline-flex', flexShrink: 0 }}>{startIcon}</span>
        )}
        {children}
        {!loading && endIcon && (
          <span style={{ display: 'inline-flex', flexShrink: 0 }}>{endIcon}</span>
        )}
      </button>
    );
  }
);
Button.displayName = 'Button';