'use client';

import { useRouter } from 'next/navigation';
import {
  FileText,
  GraduationCap,
  Link2,
  Loader2,
  Megaphone,
  Mic,
  PenLine,
  Presentation,
  Sparkles,
  Video,
  Youtube,
} from 'lucide-react';
import { type FormEvent, useState } from 'react';
import { Button } from '@/components/ui/button';
import { SegmentedControl, type SegmentOption } from '@/components/ui/segmented-control';
import { createSource, type SourceType } from '@/lib/api';

const typeOptions: SegmentOption<SourceType>[] = [
  { value: 'text', label: 'Paste text', icon: FileText },
  { value: 'url', label: 'Article URL', icon: Link2 },
  { value: 'youtube', label: 'YouTube', icon: Youtube },
];

const templateOptions: SegmentOption<string>[] = [
  { value: 'explainer', label: 'Explainer', icon: Presentation },
  { value: 'marketing', label: 'Marketing', icon: Megaphone },
  { value: 'whiteboard', label: 'Whiteboard', icon: PenLine },
];

const modeOptions: SegmentOption<string>[] = [
  { value: 'auto', label: 'Auto', icon: Sparkles },
  { value: 'course', label: 'Course', icon: GraduationCap },
  { value: 'video', label: 'Video', icon: Video },
];

const voiceOptions: SegmentOption<string>[] = [
  { value: 'male', label: 'Male', icon: Mic },
  { value: 'female', label: 'Female', icon: Mic },
];

const placeholders: Record<SourceType, string> = {
  text: 'Paste the text or notes you want to turn into a lesson…',
  url: 'https://example.com/article',
  youtube: 'https://www.youtube.com/watch?v=…',
};

export function SourceInput() {
  const router = useRouter();
  const [type, setType] = useState<SourceType>('text');
  const [template, setTemplate] = useState('explainer');
  const [mode, setMode] = useState('auto');
  const [voice, setVoice] = useState('male');
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
      const { job_id } = await createSource({ type, input, template, mode, voice });
      router.push(`/lessons/${job_id}`);
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

      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Format
        </span>
        <SegmentedControl options={modeOptions} value={mode} onChange={setMode} />
        <p className="text-xs text-muted-foreground">
          Auto lets the AI choose a structured course or a short informative video based on the
          source.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Voice
        </span>
        <SegmentedControl options={voiceOptions} value={voice} onChange={setVoice} />
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Template
        </span>
        <SegmentedControl options={templateOptions} value={template} onChange={setTemplate} />
      </div>

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
