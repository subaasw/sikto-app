'use client';

import { useRouter } from 'next/navigation';
import {
  FileText,
  GraduationCap,
  Link2,
  Loader2,
  Megaphone,
  Mic,
  Paperclip,
  PenLine,
  Plus,
  Presentation,
  Sparkles,
  Video,
  X,
} from 'lucide-react';
import { type ChangeEvent, type FormEvent, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { SegmentedControl, type SegmentOption } from '@/components/ui/segmented-control';
import { createSource, uploadSourceDocuments } from '@/lib/api';
import { readModel } from '@/lib/model-preference';

// Mirrors DOCUMENT_EXTENSIONS in api.ingestion.documents (MarkItDown-backed).
const DOCUMENT_ACCEPT = '.pdf,.epub,.docx,.pptx,.xlsx';

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
  const [showText, setShowText] = useState(false);
  const [docs, setDocs] = useState<{ path: string; name: string }[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [template, setTemplate] = useState('explainer');
  const [mode, setMode] = useState('auto');
  const [voice, setVoice] = useState('male');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inputs = [...links.map((l) => l.trim()), text.trim(), ...docs.map((d) => d.path)].filter(
    Boolean,
  );
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

  async function handleFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = ''; // allow re-selecting the same file
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const uploaded = await uploadSourceDocuments(files);
      setDocs((prev) => [...prev, ...uploaded]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }
  function removeDoc(i: number) {
    setDocs((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inputs.length === 0 || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const { job_id } = await createSource({
        type: 'mixed',
        inputs,
        template,
        mode,
        voice,
        model: readModel(),
      });
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
          Documents
        </span>
        {docs.map((doc, i) => (
          <div key={doc.path} className="flex items-center gap-2">
            <FileText className="size-4 shrink-0 text-muted-foreground" />
            <span className="flex-1 truncate border-2 border-border bg-surface px-4 py-3 text-sm">
              {doc.name}
            </span>
            <button
              type="button"
              onClick={() => removeDoc(i)}
              aria-label="Remove document"
              className="flex size-9 shrink-0 items-center justify-center border-2 border-border text-muted-foreground transition-colors hover:bg-muted"
            >
              <X className="size-4" />
            </button>
          </div>
        ))}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={DOCUMENT_ACCEPT}
          onChange={handleFiles}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="flex w-fit items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
        >
          {uploading ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <Paperclip className="size-3.5" />
          )}
          {uploading ? 'Uploading…' : 'Upload PDF, slides, or docs'}
        </button>
      </div>

      {showText ? (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Pasted text
            </span>
            <button
              type="button"
              onClick={() => {
                setShowText(false);
                setText('');
              }}
              className="flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              <X className="size-3.5" />
              Remove
            </button>
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste notes or an article to include…"
            rows={5}
            autoFocus
            className={`${fieldClass} resize-y`}
          />
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setShowText(true)}
          className="flex w-fit items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <Plus className="size-3.5" />
          Or paste text instead
        </button>
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
