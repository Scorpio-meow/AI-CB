import React from 'react';
import styles from './Spinner.module.css';
export interface SpinnerProps extends React.SVGProps<SVGSVGElement> {
  size?: number | 'sm' | 'md' | 'lg' | 'small' | 'medium' | 'large';
  color?: string;
  thickness?: number;
}
export const Spinner: React.FC<SpinnerProps> = ({
  size = 24,
  color = 'currentColor',
  thickness = 3.6,
  className = '',
  style,
  ...props
}) => {
  const pixelSize =
    typeof size === 'number'
      ? size
      : size === 'sm' || size === 'small'
        ? 16
        : size === 'lg' || size === 'large'
          ? 36
          : 24;
  const center = 22;
  const radius = (44 - thickness) / 2;
  const circumference = 2 * Math.PI * radius;
  return (
    <svg
      className={`${styles.spinner} ${className}`}
      width={pixelSize}
      height={pixelSize}
      viewBox="0 0 44 44"
      style={{ color, ...style }}
      aria-label="Loading"
      role="status"
      {...props}
    >
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={thickness}
        strokeOpacity="0.2"
      />
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={thickness}
        strokeDasharray={circumference}
        strokeDashoffset={circumference * 0.7}
        strokeLinecap="round"
      />
    </svg>
  );
};
export const CircularProgress = Spinner;