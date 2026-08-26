import React from 'react';
import styles from './Tabs.module.css';
export interface TabsProps {
  value: number | string;
  onChange: (event: React.SyntheticEvent, newValue: any) => void;
  children: React.ReactNode;
  className?: string;
}
export const Tabs: React.FC<TabsProps> = ({ value, onChange, children, className = '' }) => {
  return (
    <div className={`${styles.tabsContainer} ${className}`} role="tablist">
      {React.Children.map(children, (child, index) => {
        if (!React.isValidElement(child)) return null;
        const tabChild = child as React.ReactElement<any>;
        const tabValue = tabChild.props.value !== undefined ? tabChild.props.value : index;
        const isActive = tabValue === value;
        return React.cloneElement(tabChild, {
          active: isActive,
          onClick: (e: React.MouseEvent) => {
            tabChild.props.onClick?.(e);
            onChange(e, tabValue);
          },
        });
      })}
    </div>
  );
};
export interface TabProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  label: React.ReactNode;
  icon?: React.ReactNode;
  value?: number | string;
  active?: boolean;
}
export const Tab: React.FC<TabProps> = ({
  label,
  icon,
  active = false,
  className = '',
  ...props
}) => {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      className={`${styles.tab} ${active ? styles.tabActive : ''} ${className}`}
      {...props}
    >
      {icon && <span style={{ display: 'inline-flex', flexShrink: 0 }}>{icon}</span>}
      <span>{label}</span>
    </button>
  );
};