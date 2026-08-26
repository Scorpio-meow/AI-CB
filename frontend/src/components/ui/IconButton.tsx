import React, { forwardRef } from 'react';
import styles from './IconButton.module.css';
export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: 'sm' | 'md' | 'lg' | 'small' | 'medium' | 'large';
  variant?: 'default' | 'filled' | 'outline';
  rounded?: boolean;
  color?: string;
}
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  (
    {
      children,
      size = 'md',
      variant = 'default',
      rounded = true,
      className = '',
      color,
      style,
      ...props
    },
    ref
  ) => {
    const normalizedSize =
      size === 'small' ? 'sm' : size === 'medium' ? 'md' : size === 'large' ? 'lg' : size;
    const sizeClass =
      normalizedSize === 'sm'
        ? styles.sizeSm
        : normalizedSize === 'lg'
          ? styles.sizeLg
          : styles.sizeMd;
    const variantClass =
      variant === 'filled'
        ? styles.filled
        : variant === 'outline'
          ? styles.outline
          : '';
    const classes = [
      styles.iconButton,
      sizeClass,
      variantClass,
      rounded ? styles.rounded : '',
      className,
    ]
      .filter(Boolean)
      .join(' ');
    const customStyle: React.CSSProperties = {
      ...style,
      ...(color ? { color } : {}),
    };
    return (
      <button ref={ref} type="button" className={classes} style={customStyle} {...props}>
        {children}
      </button>
    );
  }
);
IconButton.displayName = 'IconButton';