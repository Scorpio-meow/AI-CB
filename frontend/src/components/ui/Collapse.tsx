import React from 'react';
import styles from './Collapse.module.css';
export interface CollapseProps {
  in: boolean;
  children: React.ReactNode;
  className?: string;
}
export const Collapse: React.FC<CollapseProps> = ({ in: isOpen, children, className = '' }) => {
  return (
    <div
      className={`${styles.collapseContainer} ${isOpen ? styles.collapseExpanded : ''} ${className}`}
      aria-expanded={isOpen}
    >
      <div className={styles.collapseInner}>{children}</div>
    </div>
  );
};