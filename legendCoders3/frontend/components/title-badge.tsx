'use client';

import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface TitleBadgeProps {
  title: {
    name: string;
    color_code: string;
    has_glow?: boolean;
    animation_type?: string | null;
    icon?: string | null;
  } | null;
  size?: 'xs' | 'sm' | 'md';
  className?: string;
}

export default function TitleBadge({ title, size = 'sm', className }: TitleBadgeProps) {
  if (!title) return null;

  const sizeClasses = {
    xs: 'px-1.5 py-0.5 text-[9px]',
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-3 py-1 text-xs',
  };

  // 칭호 애니메이션 효과
  const animationClass = title.animation_type === 'pulse' 
    ? 'animate-pulse' 
    : title.animation_type === 'shimmer'
    ? 'bg-shimmer' // 커스텀 CSS 필요
    : '';

  // 글로우 효과
  const glowStyle = title.has_glow 
    ? { boxShadow: `0 0 10px var(--tw-shadow-color)`, shadowColor: title.color_code }
    : {};

  return (
    <span 
      className={cn(
        "inline-flex items-center gap-1 font-black uppercase tracking-tighter rounded-md border transition-all",
        `bg-${title.color_code.split('-')[0]}-50 text-${title.color_code} border-${title.color_code.split('-')[0]}-100`,
        sizeClasses[size],
        animationClass,
        className
      )}
      style={title.has_glow ? { boxShadow: `0 0 8px currentColor` } : {}}
    >
      {title.icon && <span className="text-[1.2em]">{title.icon}</span>}
      {title.name}
    </span>
  );
}
