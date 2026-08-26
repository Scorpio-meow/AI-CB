import React, { useState, useMemo } from 'react';
import { SourceBadgesProps, SourceDetail } from './types';
import { Chip, Popover, Icon } from '../../components/ui';
import styles from './SourceBadges.module.css';
export const SourceBadges: React.FC<SourceBadgesProps> = ({
  sources,
  sourcesDetail,
}) => {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [activeDetail, setActiveDetail] = useState<SourceDetail | null>(null);
  const normalizedDetails: SourceDetail[] = useMemo(() => {
    if (!sourcesDetail) return [];
    if (Array.isArray(sourcesDetail)) return sourcesDetail;
    if (typeof sourcesDetail === 'string') {
      try {
        const parsed = JSON.parse(sourcesDetail);
        if (Array.isArray(parsed)) return parsed;
      } catch {
        return [];
      }
    }
    return [];
  }, [sourcesDetail]);
  const normalizedSources: string[] = useMemo(() => {
    if (!sources) return [];
    if (Array.isArray(sources)) {
      return sources.map((s) => (typeof s === 'string' ? s : (s as any)?.source || JSON.stringify(s)));
    }
    if (typeof sources === 'string') {
      const trimmed = (sources as string).trim();
      if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
        try {
          const parsed = JSON.parse(trimmed);
          if (Array.isArray(parsed)) {
            return parsed.map((s) => (typeof s === 'string' ? s : (s as any)?.source || JSON.stringify(s)));
          }
        } catch { }
      }
      return trimmed.split(/[,;\n]+/).map((s) => s.trim()).filter(Boolean);
    }
    return [];
  }, [sources]);
  const handleOpenDetail = (
    event: React.MouseEvent<HTMLElement>,
    detail: SourceDetail
  ) => {
    if (detail.url) {
      window.open(detail.url, '_blank', 'noopener,noreferrer');
      return;
    }
    setAnchorEl(event.currentTarget);
    setActiveDetail(detail);
  };
  const handleCloseDetail = () => {
    setAnchorEl(null);
    setActiveDetail(null);
  };
  const hasDetails = normalizedDetails.length > 0;
  const hasSources = normalizedSources.length > 0;
  if (!hasDetails && !hasSources) return null;
  return (
    <div className={styles.container}>
      <span className={styles.heading}>參考來源：</span>
      <div className={styles.badgesList}>
        {hasDetails
          ? normalizedDetails.map((detail, idx) => {
            const isWeb = Boolean(detail.url);
            const label = isWeb
              ? detail.source
              : `${detail.source}${detail.chunk !== undefined ? ` (段落 ${detail.chunk})` : ''}`;
            return (
              <Chip
                key={idx}
                icon={
                  isWeb ? (
                    <Icon name="language" size={14} color="#0891B2" />
                  ) : (
                    <Icon name="description" size={14} />
                  )
                }
                label={label}
                size="sm"
                variant="outlined"
                onClick={(e) => handleOpenDetail(e, detail)}
                className={isWeb ? styles.badgeWeb : ''}
              />
            );
          })
          : normalizedSources.map((src, idx) => {
            const isWeb = src.startsWith('http://') || src.startsWith('https://');
            return (
              <Chip
                key={idx}
                icon={
                  isWeb ? (
                    <Icon name="language" size={14} color="#0891B2" />
                  ) : (
                    <Icon name="description" size={14} />
                  )
                }
                label={src}
                size="sm"
                variant="outlined"
                onClick={isWeb ? () => window.open(src, '_blank', 'noopener,noreferrer') : undefined}
                className={isWeb ? styles.badgeWeb : ''}
              />
            );
          })}
      </div>
      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={handleCloseDetail}
      >
        {activeDetail && (
          <div className={styles.popoverCard}>
            <div className={styles.popoverHeader}>
              <Icon name="description" size={18} color="#2563EB" />
              <span>{activeDetail.source}</span>
            </div>
            {activeDetail.score !== undefined && activeDetail.score !== null && (
              <div className={styles.scoreRow}>
                <Icon name="analytics" size={14} color="#059669" />
                <span>匹配分數: {activeDetail.score}</span>
              </div>
            )}
            {activeDetail.snippet && (
              <div className={styles.snippet}>
                {activeDetail.snippet}
              </div>
            )}
          </div>
        )}
      </Popover>
    </div>
  );
};
export default SourceBadges;