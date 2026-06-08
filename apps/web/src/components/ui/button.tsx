import { type ButtonHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

const base =
  'pixel-press inline-flex items-center justify-center gap-2 border-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50';

const variants = {
  primary: 'border-border bg-primary text-primary-foreground shadow-pixel-sm hover:brightness-95',
  secondary: 'border-border bg-surface text-foreground shadow-pixel-sm hover:bg-muted',
  ghost: 'border-transparent text-foreground hover:bg-muted',
} as const;

const sizes = {
  sm: 'h-8 px-3',
  md: 'h-10 px-4',
  lg: 'h-11 px-5 text-[0.95rem]',
} as const;

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => (
    <button ref={ref} className={cn(base, variants[variant], sizes[size], className)} {...props} />
  ),
);

Button.displayName = 'Button';
