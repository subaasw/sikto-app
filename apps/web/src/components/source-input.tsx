'use client';

import { useRouter } from 'next/navigation';
import {
  GraduationCap,
  Link2,
  Loader2,
  Megaphone,
  Mic,
  PenLine,
  Plus,
  Presentation,
  Sparkles,
  Video,
  X,
} from 'lucide-react';
import { type FormEvent, useState } from 'react';
import { Button } from '@/components/ui/button';
import { SegmentedControl, type SegmentOption } from '@/components/ui/segmented-control';
import { createSource } from '@/lib/api';

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

export function SourceInput() {
  const router = useRouter();
  const [links, setLinks] = useState<string[]>(['']);
  const [text, setText] = useState('');
  const [template, setTemplate] = useState('explainer');
  const [mode, setMode] = useState('auto');
  const [voice, setVoice] = useState('male');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inputs = [...links.map((l) => l.trim()), text.trim()].filter(Boolean);
  const multi = inputs.length > 1;

  function setLink(i: number, value: string) {
    setLinks((prev) => prev.map((l, idx) => (idx === i ? value : l)));
  }
  function addLink() {
    setLinks((prev) => [...prev, '']);
  }
  function removeLink(i: number) {
    setLinks((prev) => (prev.length === 1 ? [''] : prev.filter((_, idx) => idx !== i)));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inputs.length === 0 || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const { job_id } = await createSource({ type: 'mixed', inputs, template, mode, voice });
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
      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Links &amp; videos
        </span>
        {links.map((link, i) => (
          <div key={i} className="flex items-center gap-2">
            <Link2 className="size-4 shrink-0 text-muted-foreground" />
            <input
              type="url"
              value={link}
              onChange={(e) => setLink(i, e.target.value)}
              placeholder="https://example.com/article or https://youtu.be/…"
              className={fieldClass}
            />
            <button
              type="button"
              onClick={() => removeLink(i)}
              aria-label="Remove link"
              className="flex size-9 shrink-0 items-center justify-center border-2 border-border text-muted-foreground transition-colors hover:bg-muted disabled:opacity-40"
              disabled={links.length === 1 && !link}
            >
              <X className="size-4" />
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={addLink}
          className="flex w-fit items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <Plus className="size-3.5" />
          Add another link
        </button>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Or paste text
        </span>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste notes or an article to include…"
          rows={5}
          className={`${fieldClass} resize-y`}
        />
      </div>

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
        <p className="text-xs text-muted-foreground">
          {multi
            ? `${inputs.length} sources → one combined lesson.`
            : 'Add links, videos, or text → one narrated lesson.'}
        </p>
        <Button type="submit" size="lg" disabled={inputs.length === 0 || submitting}>
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
