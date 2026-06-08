'use client';

import { type ComponentType } from 'react';
import { cn } from '@/lib/utils';

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
  icon?: ComponentType<{ className?: string }>;
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  className,
}: {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}) {
  return (
    <div className={cn('inline-flex border-2 border-border bg-muted p-1', className)}>
      {options.map((option) => {
        const Icon = option.icon;
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={cn(
              'inline-flex items-center gap-1.5 border-2 px-3 py-1.5 text-sm font-medium transition-colors',
              active
                ? 'border-border bg-primary text-primary-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground',
            )}
          >
            {Icon ? <Icon className="size-4" /> : null}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
