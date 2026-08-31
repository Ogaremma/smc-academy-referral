import type { HTMLAttributes, ReactNode } from 'react';

interface GlassCardProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
  as?: 'article' | 'section' | 'div';
}

export function GlassCard({ children, className = '', as: Element = 'article', ...props }: GlassCardProps) {
  return <Element className={`glass-card ${className}`} {...props}>{children}</Element>;
}
