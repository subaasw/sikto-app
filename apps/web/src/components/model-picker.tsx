'use client';

import { Check, Sparkles } from 'lucide-react';
import { useModelPreference } from '@/lib/model-preference';
import { cn } from '@/lib/utils';
import type { Provider } from '@/types/api';

export function ModelPicker({ providers }: { providers: Provider[] }) {
  const { model, setModel } = useModelPreference();

  if (providers.length === 0) {
    return (
      <div className="border-2 border-border bg-surface p-6">
        <p className="text-sm font-medium">No providers configured</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Set one of <code className="font-mono">NVIDIA_API_KEY</code>,{' '}
          <code className="font-mono">DEEPSEEK_API_KEY</code>, or{' '}
          <code className="font-mono">OPENAI_API_KEY</code> in the API environment, then reload.
        </p>
      </div>
    );
  }

  const options: { value: string | null; label: string; hint: string }[] = [
    { value: null, label: 'Automatic', hint: 'Best available, with fallback' },
    ...providers.flatMap((provider) =>
      provider.models.map((name) => ({
        value: `${provider.id}:${name}`,
        label: name,
        hint: provider.label,
      })),
    ),
  ];

  return (
    <div className="flex flex-col gap-2">
      {options.map((option) => {
        const selected = model === option.value;
        return (
          <button
            key={option.value ?? 'auto'}
            type="button"
            onClick={() => setModel(option.value)}
            aria-pressed={selected}
            className={cn(
              'flex items-center gap-3 border-2 px-4 py-3 text-left transition-colors',
              selected
                ? 'border-border bg-muted shadow-pixel-sm'
                : 'border-border-soft hover:border-border hover:bg-muted',
            )}
          >
            <span
              className={cn(
                'flex size-5 shrink-0 items-center justify-center border-2',
                selected ? 'border-border bg-primary text-primary-foreground' : 'border-border-soft',
              )}
            >
              {selected ? <Check className="size-3" /> : null}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-mono text-sm">{option.label}</span>
              <span className="block text-xs text-muted-foreground">{option.hint}</span>
            </span>
            {option.value === null ? <Sparkles className="size-4 text-muted-foreground" /> : null}
          </button>
        );
      })}
    </div>
  );
}
