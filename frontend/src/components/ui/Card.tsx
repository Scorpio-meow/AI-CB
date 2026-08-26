import React, { forwardRef } from 'react';
import styles from './Card.module.css';
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  elevation?: number;
  variant?: 'elevation' | 'outlined';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  square?: boolean;
}
export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      elevation = 1,
      variant = 'elevation',
      padding = 'none',
      square = false,
      className = '',
      style,
      ...props
    },
    ref
  ) => {
    const elevationClass =
      elevation === 0
        ? styles.elevation0
        : elevation === 2
          ? styles.elevation2
          : elevation === 3
            ? styles.elevation3
            : elevation >= 4
              ? styles.elevation4
              : styles.elevation1;
    const paddingClass =
      padding === 'sm'
        ? styles.paddingSm
        : padding === 'md'
          ? styles.paddingMd
          : padding === 'lg'
            ? styles.paddingLg
            : styles.paddingNone;
    const classes = [
      styles.card,
      elevationClass,
      variant === 'outlined' ? styles.outlined : '',
      paddingClass,
      className,
    ]
      .filter(Boolean)
      .join(' ');
    const customStyle: React.CSSProperties = {
      ...(square ? { borderRadius: 0 } : {}),
      ...style,
    };
    return (
      <div ref={ref} className={classes} style={customStyle} {...props}>
        {children}
      </div>
    );
  }
);
Card.displayName = 'Card';
export const Paper = Card;