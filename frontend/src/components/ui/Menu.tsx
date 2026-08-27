import React, { useEffect, useRef, useState, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import styles from './Menu.module.css';
export interface MenuProps {
  open: boolean;
  anchorEl: HTMLElement | null;
  onClose?: () => void;
  children: React.ReactNode;
  className?: string;
  placement?: 'bottom-start' | 'bottom-end' | 'top-start' | 'top-end';
}
export const Menu: React.FC<MenuProps> = ({
  open,
  anchorEl,
  onClose,
  children,
  className = '',
  placement = 'bottom-start',
}) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  useLayoutEffect(() => {
    if (!open || !anchorEl) return;
    const rect = anchorEl.getBoundingClientRect();
    const menuEl = menuRef.current;
    const menuWidth = menuEl ? menuEl.offsetWidth : 180;
    const menuHeight = menuEl ? menuEl.offsetHeight : 150;
    let top = rect.bottom + 6;
    let left = rect.left;
    if (placement === 'bottom-end') {
      left = rect.right - menuWidth;
    } else if (placement === 'top-start') {
      top = rect.top - menuHeight - 6;
    } else if (placement === 'top-end') {
      top = rect.top - menuHeight - 6;
      left = rect.right - menuWidth;
    }
    const padding = 8;
    if (left + menuWidth > window.innerWidth - padding) {
      left = window.innerWidth - menuWidth - padding;
    }
    if (left < padding) {
      left = padding;
    }
    if (top + menuHeight > window.innerHeight - padding) {
      top = rect.top - menuHeight - 6;
    }
    if (top < padding) {
      top = padding;
    }
    setCoords({ top, left });
  }, [open, anchorEl, placement]);
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);
  if (!open || !anchorEl) return null;
  return createPortal(
    <>
      <div className={styles.menuBackdrop} onClick={onClose} />
      <div
        ref={menuRef}
        className={`${styles.menuContainer} ${className}`}
        style={{ top: `${coords.top}px`, left: `${coords.left}px` }}
        tabIndex={-1}
      >
        {children}
      </div>
    </>,
    document.body
  );
};
export interface MenuItemProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: React.ReactNode;
  danger?: boolean;
}
export const MenuItem: React.FC<MenuItemProps> = ({
  children,
  icon,
  danger = false,
  className = '',
  onClick,
  ...props
}) => {
  return (
    <button
      className={`${styles.menuItem} ${danger ? styles.menuItemDanger : ''} ${className}`}
      onClick={onClick}
      {...props}
    >
      {icon && <span style={{ display: 'inline-flex', flexShrink: 0 }}>{icon}</span>}
      <span>{children}</span>
    </button>
  );
};
export const MenuDivider: React.FC = () => <div className={styles.divider} />;
export const Popover = Menu;