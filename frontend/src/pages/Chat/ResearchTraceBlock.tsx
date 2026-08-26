import React, { useState, useEffect, useRef } from 'react';
import { ResearchTraceStep } from './types';
import { Collapse, Chip, Spinner, Icon } from '../../components/ui';
import styles from './ResearchTraceBlock.module.css';

export interface ResearchTraceBlockProps {
  trace: ResearchTraceStep[];
  hasContent?: boolean;
  isStreaming?: boolean;
}

const getToolDisplayInfo = (toolName: string) => {
  switch (toolName) {
    case 'search_knowledge_base':
      return {
        label: '檢索內部知識庫',
        color: '#2563EB',
        bgColor: 'rgba(37, 99, 235, 0.12)',
        icon: <Icon name="menu-book" size={16} color="#2563EB" />,
      };
    case 'web_search':
      return {
        label: '外部聯網搜尋',
        color: '#0891B2',
        bgColor: 'rgba(8, 145, 178, 0.12)',
        icon: <Icon name="language" size={16} color="#0891B2" />,
      };
    case 'web_fetch':
      return {
        label: '深度閱讀網頁',
        color: '#7C3AED',
        bgColor: 'rgba(124, 58, 237, 0.12)',
        icon: <Icon name="article" size={16} color="#7C3AED" />,
      };
    default:
      return {
        label: toolName,
        color: '#64748B',
        bgColor: 'rgba(100, 116, 139, 0.12)',
        icon: <Icon name="code" size={16} color="#64748B" />,
      };
  }
};

export const ResearchTraceBlock: React.FC<ResearchTraceBlockProps> = ({
  trace,
  hasContent = false,
  isStreaming = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const userInteractedRef = useRef(false);
  const prevHasContentRef = useRef(hasContent);

  const hasRunningStep = trace.some(s => s.status === 'running');
  const isResearching = isStreaming && !hasContent;

  // 檢索期間自動展開；文字串流開始時自動收合
  useEffect(() => {
    if (userInteractedRef.current) return;

    if (isResearching || hasRunningStep) {
      setIsOpen(true);
    } else if (hasContent && !prevHasContentRef.current) {
      setIsOpen(false);
    }
    prevHasContentRef.current = hasContent;
  }, [isResearching, hasRunningStep, hasContent]);

  if (!trace || trace.length === 0) return null;

  const handleHeaderClick = () => {
    userInteractedRef.current = true;
    setIsOpen(prev => !prev);
  };

  const activeStep = trace.find(s => s.status === 'running') || trace[trace.length - 1];
  const activeToolInfo = activeStep ? getToolDisplayInfo(activeStep.tool) : null;

  return (
    <div className={`${styles.container} ${hasRunningStep ? styles.containerActive : ''}`}>
      <div
        className={styles.header}
        onClick={handleHeaderClick}
        role="button"
        tabIndex={0}
        aria-expanded={isOpen}
      >
        <div className={styles.titleArea}>
          {hasRunningStep ? (
            <Spinner size={16} color="var(--color-primary)" />
          ) : (
            <Icon name="search" size={18} color="var(--color-primary)" />
          )}
          <span className={styles.titleText}>
            {hasRunningStep
              ? `AI 自主研究中：${activeToolInfo?.label || '執行中'} (步驟 ${activeStep.step})`
              : `AI 自主研究歷程 (${trace.length} 個步驟)`}
          </span>
        </div>

        <div className={styles.metaArea}>
          <div className={styles.stepsChipRow}>
            {trace.map((step, idx) => {
              const info = getToolDisplayInfo(step.tool);
              const isStepRunning = step.status === 'running';
              return (
                <Chip
                  key={idx}
                  label={`S${step.step}${isStepRunning ? '...' : ''}`}
                  size="sm"
                  style={{
                    color: isStepRunning ? '#FFFFFF' : info.color,
                    backgroundColor: isStepRunning ? 'var(--color-primary)' : info.bgColor,
                    borderColor: `${info.color}33`,
                    height: '20px',
                    fontSize: '0.68rem',
                    fontWeight: 600,
                    animation: isStepRunning ? 'var(--anim-pulse)' : undefined
                  }}
                />
              );
            })}
          </div>
          <span className={`${styles.chevron} ${isOpen ? styles.chevronOpen : ''}`}>
            <Icon name="expand-more" size={16} />
          </span>
        </div>
      </div>

      <Collapse in={isOpen}>
        <div className={styles.divider} />
        <div className={styles.stepList}>
          {trace.map((step: ResearchTraceStep, index: number) => {
            const toolInfo = getToolDisplayInfo(step.tool);
            const queryParam = step.arguments?.query || step.arguments?.url || '';
            const isStepRunning = step.status === 'running';

            return (
              <div
                key={index}
                className={`${styles.stepItem} ${isStepRunning ? styles.stepItemRunning : ''}`}
              >
                <div className={styles.stepHeader}>
                  <div className={styles.stepTitle}>
                    {toolInfo.icon}
                    <span>
                      步驟 {step.step}：{toolInfo.label}
                      {isStepRunning && <span className={styles.runningBadge}>進行中</span>}
                    </span>
                  </div>
                  <div className={styles.stepMeta}>
                    {step.duration_seconds !== undefined && !isStepRunning && (
                      <span className={styles.duration}>{step.duration_seconds}s</span>
                    )}
                    {isStepRunning ? (
                      <Spinner size={14} color="var(--color-primary)" />
                    ) : step.status === 'error' ? (
                      <Icon name="error" size={14} color="#EF4444" />
                    ) : (
                      <Icon name="check-circle" size={14} color="#10B981" />
                    )}
                  </div>
                </div>

                {queryParam && (
                  <div className={styles.queryBox}>
                    <span className={styles.queryText}>
                      關鍵字/目標: {queryParam}
                    </span>
                  </div>
                )}

                {step.output_preview && (
                  <pre className={styles.outputPreview}>
                    {step.output_preview}
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      </Collapse>
    </div>
  );
};

export default ResearchTraceBlock;