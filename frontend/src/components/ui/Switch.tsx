import React from 'react';
import styles from './Switch.module.css';
export interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: React.ReactNode;
}
export const Switch: React.FC<SwitchProps> = ({
  checked,
  onChange,
  disabled,
  label,
  className = '',
  ...props
}) => {
  return (
    <label className={`${styles.switchLabel} ${disabled ? styles.disabled : ''} ${className}`}>
      <input
        type="checkbox"
        className={styles.input}
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        role="switch"
        aria-checked={checked}
        {...props}
      />
      <span className={styles.track}>
        <span className={styles.thumb} />
      </span>
      {label && <span>{label}</span>}
    </label>
  );
};