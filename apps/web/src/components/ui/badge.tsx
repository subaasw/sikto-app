import { type HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

const tones = {
  neutral: 'border-border-soft bg-muted text-muted-foreground',
  active: 'border-border bg-primary text-primary-foreground',
  success: 'border-lime-600/40 bg-lime-500/15 text-lime-700 dark:text-lime-400',
  error: 'border-red-500/40 bg-red-500/15 text-red-600 dark:text-red-400',
} as const;

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: keyof typeof tones;
}

export function Badge({ className, tone = 'neutral', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 border-2 px-2 py-0.5 text-xs font-medium',
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}
