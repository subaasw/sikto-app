'use client';

import { useRouter } from 'next/navigation';
import { FileText, Link2, Loader2, Youtube } from 'lucide-react';
import { type FormEvent, useState } from 'react';
import { Button } from '@/components/ui/button';
import { SegmentedControl, type SegmentOption } from '@/components/ui/segmented-control';
import { createSource, type SourceType } from '@/lib/api';

const typeOptions: SegmentOption<SourceType>[] = [
  { value: 'text', label: 'Paste text', icon: FileText },
  { value: 'url', label: 'Article URL', icon: Link2 },
  { value: 'youtube', label: 'YouTube', icon: Youtube },
];

const placeholders: Record<SourceType, string> = {
  text: 'Paste the text or notes you want to turn into a lesson…',
  url: 'https://example.com/article',
  youtube: 'https://www.youtube.com/watch?v=…',
};

export function SourceInput() {
  const router = useRouter();
  const [type, setType] = useState<SourceType>('text');
  const [value, setValue] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = value.trim();
    if (!input || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const { job_id } = await createSource({ type, input });
      router.push(`/jobs/${job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setSubmitting(false);
    }
  }

  const fieldClass =
    'w-full border-2 border-border bg-surface px-4 py-3 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring';

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <SegmentedControl
        options={typeOptions}
        value={type}
        onChange={(next) => {
          setType(next);
          setValue('');
        }}
      />

      {type === 'text' ? (
        <textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={placeholders[type]}
          rows={8}
          className={`${fieldClass} resize-y`}
        />
      ) : (
        <input
          type="url"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={placeholders[type]}
          className={fieldClass}
        />
      )}

      {error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null}

      <div className="flex items-center justify-between gap-4">
        <p className="text-xs text-muted-foreground">One source → one narrated microlearning lesson.</p>
        <Button type="submit" size="lg" disabled={!value.trim() || submitting}>
          {submitting ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Generating…
            </>
          ) : (
            'Generate lesson'
          )}
        </Button>
      </div>
    </form>
  );
}
