import React, { forwardRef, useState } from 'react';
import styles from './TextField.module.css';
export interface TextFieldProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement | HTMLTextAreaElement>, 'size'> {
  label?: React.ReactNode;
  helperText?: React.ReactNode;
  error?: boolean;
  fullWidth?: boolean;
  multiline?: boolean;
  rows?: number;
  maxRows?: number;
  startAdornment?: React.ReactNode;
  endAdornment?: React.ReactNode;
  InputProps?: {
    startAdornment?: React.ReactNode;
    endAdornment?: React.ReactNode;
    readOnly?: boolean;
  };
  variant?: 'outlined' | 'filled' | 'standard';
  size?: 'small' | 'medium';
}
export const TextField = forwardRef<HTMLInputElement & HTMLTextAreaElement, TextFieldProps>(
  (
    {
      label,
      helperText,
      error = false,
      fullWidth = false,
      multiline = false,
      rows = 3,
      startAdornment,
      endAdornment,
      InputProps,
      className = '',
      style,
      disabled,
      onFocus,
      onBlur,
      ...props
    },
    ref
  ) => {
    const [focused, setFocused] = useState(false);
    const actualStartAdornment = startAdornment || InputProps?.startAdornment;
    const actualEndAdornment = endAdornment || InputProps?.endAdornment;
    const handleFocus = (e: React.FocusEvent<HTMLInputElement & HTMLTextAreaElement>) => {
      setFocused(true);
      onFocus?.(e);
    };
    const handleBlur = (e: React.FocusEvent<HTMLInputElement & HTMLTextAreaElement>) => {
      setFocused(false);
      onBlur?.(e);
    };
    const wrapperClasses = [
      styles.inputWrapper,
      focused ? styles.focused : '',
      error ? styles.hasError : '',
      disabled ? styles.disabled : '',
    ]
      .filter(Boolean)
      .join(' ');
    return (
      <div
        className={`${styles.container} ${fullWidth ? styles.fullWidth : ''} ${className}`}
        style={style}
      >
        {label && (
          <label className={`${styles.label} ${error ? styles.labelError : ''}`}>
            {label}
          </label>
        )}
        <div className={wrapperClasses}>
          {actualStartAdornment && (
            <div className={styles.adornment}>{actualStartAdornment}</div>
          )}
          {multiline ? (
            <textarea
              ref={ref as unknown as React.Ref<HTMLTextAreaElement>}
              className={`${styles.input} ${styles.textarea}`}
              rows={rows}
              disabled={disabled}
              readOnly={InputProps?.readOnly}
              onFocus={handleFocus}
              onBlur={handleBlur}
              {...(props as React.TextareaHTMLAttributes<HTMLTextAreaElement>)}
            />
          ) : (
            <input
              ref={ref as unknown as React.Ref<HTMLInputElement>}
              className={styles.input}
              disabled={disabled}
              readOnly={InputProps?.readOnly}
              onFocus={handleFocus}
              onBlur={handleBlur}
              {...(props as React.InputHTMLAttributes<HTMLInputElement>)}
            />
          )}
          {actualEndAdornment && (
            <div className={styles.adornment}>{actualEndAdornment}</div>
          )}
        </div>
        {helperText && (
          <div className={`${styles.helperText} ${error ? styles.helperTextError : ''}`}>
            {helperText}
          </div>
        )}
      </div>
    );
  }
);
TextField.displayName = 'TextField';
export const Input = TextField;