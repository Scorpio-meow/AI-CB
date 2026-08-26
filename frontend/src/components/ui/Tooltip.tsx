import React, { useState, useRef } from 'react';
import styles from './Tooltip.module.css';
export interface TooltipProps {
  title: React.ReactNode;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  children: React.ReactElement;
  className?: string;
  arrow?: boolean;
}
export const Tooltip: React.FC<TooltipProps> = ({
  title,
  placement = 'top',
  children,
  className = '',
}) => {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  if (!title) return children;
  const show = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setVisible(true), 100);
  };
  const hide = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setVisible(false);
  };
  const placementClass =
    placement === 'bottom'
      ? styles.placementBottom
      : placement === 'left'
        ? styles.placementLeft
        : placement === 'right'
          ? styles.placementRight
          : styles.placementTop;
  return (
    <div
      className={`${styles.wrapper} ${className}`}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      <div
        className={`${styles.tooltip} ${placementClass} ${visible ? styles.visible : ''}`}
        role="tooltip"
        aria-hidden={!visible}
      >
        {title}
      </div>
    </div>
  );
};