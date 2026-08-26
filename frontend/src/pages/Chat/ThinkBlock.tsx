import React from 'react';
import { ThinkBlockProps } from './types';
import { Icon, Collapse, IconButton } from '../../components/ui';
import styles from './ThinkBlock.module.css';
export const ThinkBlock: React.FC<ThinkBlockProps> = ({
  thinkContent,
  isOpen,
  onToggle,
}) => {
  if (!thinkContent) return null;
  return (
    <div className={styles.container}>
      <div
        className={styles.header}
        onClick={onToggle}
        role="button"
        tabIndex={0}
        aria-expanded={isOpen}
      >
        <div className={styles.titleArea}>
          <Icon name="lightbulb" size={18} color="#2563EB" />
          <span>思考與推論過程</span>
        </div>
        <IconButton size="sm" aria-label={isOpen ? '收合思考過程' : '展開思考過程'}>
          <Icon name={isOpen ? 'expand-less' : 'expand-more'} size={16} />
        </IconButton>
      </div>
      <Collapse in={isOpen}>
        <div className={styles.body}>
          <pre className={styles.text}>{thinkContent}</pre>
        </div>
      </Collapse>
    </div>
  );
};
export default ThinkBlock;