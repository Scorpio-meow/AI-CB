import React from 'react';
import styles from './Avatar.module.css';
export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string;
  alt?: string;
  size?: number | 'sm' | 'md' | 'lg' | 'small' | 'medium' | 'large';
}
export const Avatar: React.FC<AvatarProps> = ({
  src,
  alt = 'Avatar',
  size = 'md',
  children,
  className = '',
  style,
  ...props
}) => {
  const isCustomSize = typeof size === 'number';
  const normalizedSize =
    size === 'sm' || size === 'small'
      ? styles.sizeSm
      : size === 'lg' || size === 'large'
        ? styles.sizeLg
        : styles.sizeMd;
  const customStyle: React.CSSProperties = {
    ...(isCustomSize ? { width: `${size}px`, height: `${size}px` } : {}),
    ...style,
  };
  return (
    <div
      className={`${styles.avatar} ${!isCustomSize ? normalizedSize : ''} ${className}`}
      style={customStyle}
      {...props}
    >
      {src ? (
        <img src={src} alt={alt} className={styles.img} />
      ) : (
        children
      )}
    </div>
  );
};