import React, { useState, useMemo } from 'react';
import { Box, Chip, Typography, Popover, Paper, Link } from '@mui/material';
import {
  DescriptionOutlined,
  ScoreOutlined,
  LanguageOutlined,
  OpenInNew,
} from '@mui/icons-material';
import { SourceBadgesProps, SourceDetail } from './types';

export const SourceBadges: React.FC<SourceBadgesProps> = ({
  sources,
  sourcesDetail,
}) => {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [activeDetail, setActiveDetail] = useState<SourceDetail | null>(null);

  // 安全正規化 sourcesDetail 為陣列
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

  // 安全正規化 sources 為字串陣列
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
        } catch {
          // ignore
        }
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
    <Box sx={{ mt: 1.5, pt: 1, borderTop: '1px dashed rgba(0, 0, 0, 0.08)' }}>
      <Typography
        variant="caption"
        sx={{
          display: 'block',
          fontWeight: 600,
          color: '#64748B',
          mb: 0.8,
        }}
      >
        參考來源：
      </Typography>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.8 }}>
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
                      <LanguageOutlined sx={{ fontSize: 16, color: '#0891B2' }} />
                    ) : (
                      <DescriptionOutlined sx={{ fontSize: 16 }} />
                    )
                  }
                  deleteIcon={isWeb ? <OpenInNew sx={{ fontSize: '13px !important' }} /> : undefined}
                  onDelete={isWeb ? (e) => handleOpenDetail(e, detail) : undefined}
                  label={label}
                  size="small"
                  variant="outlined"
                  onClick={(e) => handleOpenDetail(e, detail)}
                  sx={{
                    borderRadius: 1.5,
                    fontSize: '0.75rem',
                    borderColor: isWeb ? '#A5F3FC' : '#CBD5E1',
                    backgroundColor: isWeb ? '#F0FDFA' : '#F8FAFC',
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: isWeb ? '#CCFBF1' : '#EFF6FF',
                      borderColor: isWeb ? '#5EEAD4' : '#93C5FD',
                    },
                  }}
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
                      <LanguageOutlined sx={{ fontSize: 16, color: '#0891B2' }} />
                    ) : (
                      <DescriptionOutlined sx={{ fontSize: 16 }} />
                    )
                  }
                  label={src}
                  size="small"
                  variant="outlined"
                  onClick={isWeb ? () => window.open(src, '_blank', 'noopener,noreferrer') : undefined}
                  sx={{
                    borderRadius: 1.5,
                    fontSize: '0.75rem',
                    borderColor: isWeb ? '#A5F3FC' : '#CBD5E1',
                    backgroundColor: isWeb ? '#F0FDFA' : '#F8FAFC',
                    cursor: isWeb ? 'pointer' : 'default',
                  }}
                />
              );
            })}
      </Box>

      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={handleCloseDetail}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'left',
        }}
      >
        {activeDetail && (
          <Paper sx={{ p: 2, maxWidth: 360, borderRadius: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <DescriptionOutlined sx={{ color: '#2563EB', fontSize: 20 }} />
              <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#1E293B' }}>
                {activeDetail.source}
              </Typography>
            </Box>

            {activeDetail.score !== undefined && activeDetail.score !== null && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                <ScoreOutlined sx={{ fontSize: 16, color: '#059669' }} />
                <Typography variant="caption" sx={{ color: '#059669', fontWeight: 600 }}>
                  匹配分數: {activeDetail.score}
                </Typography>
              </Box>
            )}

            {activeDetail.snippet && (
              <Typography
                variant="body2"
                sx={{
                  color: '#475569',
                  backgroundColor: '#F8FAFC',
                  p: 1,
                  borderRadius: 1,
                  fontSize: '0.8rem',
                  lineHeight: 1.5,
                  border: '1px solid #E2E8F0',
                }}
              >
                {activeDetail.snippet}
              </Typography>
            )}
          </Paper>
        )}
      </Popover>
    </Box>
  );
};

export default SourceBadges;
