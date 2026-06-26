'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AlertCircle, Check, Loader2, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { getJob, type Job, type JobStatus } from '@/lib/api';
import { cn } from '@/lib/utils';

const STEPS: { key: JobStatus; label: string; hint: string }[] = [
  { key: 'loading', label: 'Loading source', hint: 'Fetching the transcript and cleaning your content' },
  { key: 'planning', label: 'Designing the lesson', hint: 'The agent drafts the script, slides, and visuals' },
  { key: 'narrating', label: 'Synthesizing narration', hint: 'Generating the voiceover for each scene' },
  { key: 'rendering', label: 'Rendering video', hint: 'Animating slides and exporting the video' },
];

type StepState = 'done' | 'active' | 'error' | 'pending';

function fmtElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  return `${m}:${String(seconds % 60).padStart(2, '0')}`;
}

/**
 * Live progress for a generating lesson. Polls the job; when it finishes it
 * refreshes the route so the server component swaps in the finished lesson —
 * no manual "view lesson" hop. Renders the failure state inline too.
 *
 * ponytail: polls instead of SSE — the browser reaches the API through the
 * Next.js /api rewrite, which buffers a long-lived text/event-stream so events
 * never arrive. Discrete GETs proxy fine. Switch to SSE only if the browser
 * talks to the API origin directly.
 */
export function LessonProgress({ jobId, initialJob }: { jobId: string; initialJob?: Job | null }) {
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(initialJob ?? null);
  const [elapsed, setElapsed] = useState(0);

  // Poll the job until it's done or failed.
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const next = await getJob(jobId);
        if (!active) return;
        setJob(next);
        if (next.status === 'done') {
          // Small beat on "Ready", then re-render the route into the lesson.
          timer = setTimeout(() => active && router.refresh(), 650);
          return;
        }
        if (next.status === 'failed') return;
        timer = setTimeout(poll, 1200);
      } catch {
        if (!active) return;
        timer = setTimeout(poll, 2500);
      }
    }

    poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [jobId, router]);

  // Tick an elapsed timer while work is in flight.
  useEffect(() => {
    if (job?.status === 'done' || job?.status === 'failed') return;
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, [job?.status]);

  const status = job?.status;
  const failed = status === 'failed';
  const done = status === 'done';
  // 'queued' (and the initial null) sit before the first visible step.
  const currentIndex =
    status === 'queued' || !status ? 0 : STEPS.findIndex((step) => step.key === status);
  const completedCount = done ? STEPS.length : Math.max(currentIndex, 0);
  const pct = done ? 100 : (completedCount / STEPS.length) * 100;

  function stepState(index: number): StepState {
    if (failed) return index === currentIndex ? 'error' : index < currentIndex ? 'done' : 'pending';
    if (done || index < currentIndex) return 'done';
    if (index === currentIndex) return 'active';
    return 'pending';
  }

  return (
    <div className="flex flex-col gap-6">
      {/* header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'flex size-8 items-center justify-center border-2 border-border shadow-pixel-sm',
              done ? 'bg-primary text-primary-foreground' : failed ? 'bg-red-500 text-white' : 'bg-primary text-primary-foreground',
            )}
          >
            {done ? (
              <Check className="size-4" />
            ) : failed ? (
              <AlertCircle className="size-4" />
            ) : (
              <Sparkles className="size-4 animate-pulse" />
            )}
          </span>
          <span className="font-pixel text-sm uppercase tracking-wide">
            {done ? 'Lesson ready' : failed ? 'Generation failed' : 'Generating lesson'}
          </span>
        </div>
        <span className="font-pixel text-xs text-muted-foreground tabular-nums">
          {fmtElapsed(elapsed)}
        </span>
      </div>

      {/* progress bar */}
      <div className="h-3 w-full overflow-hidden border-2 border-border bg-muted">
        <div
          className={cn(
            'h-full transition-[width] duration-700 ease-out',
            failed ? 'bg-red-500' : 'bg-primary',
            !done && !failed && 'animate-pulse',
          )}
          style={{ width: `${Math.max(pct, failed ? pct : 6)}%` }}
        />
      </div>

      {/* steps */}
      <ol className="flex flex-col gap-1.5">
        {STEPS.map((step, index) => {
          const state = stepState(index);
          return (
            <li
              key={step.key}
              className={cn(
                'flex items-start gap-3 border-2 px-3 py-2.5 transition-colors',
                state === 'active'
                  ? 'border-border bg-primary/10'
                  : state === 'error'
                    ? 'border-red-500/40 bg-red-500/5'
                    : 'border-transparent',
              )}
            >
              <StepIcon state={state} />
              <div className="flex min-w-0 flex-col">
                <span
                  className={cn(
                    'text-sm',
                    state === 'pending' ? 'text-muted-foreground' : 'text-foreground',
                    state === 'active' && 'font-medium',
                  )}
                >
                  {step.label}
                </span>
                {state === 'active' ? (
                  <span className="text-xs text-muted-foreground">{job?.step || step.hint}</span>
                ) : null}
              </div>
              {state === 'done' ? (
                <span className="ml-auto font-pixel text-[10px] uppercase text-primary">done</span>
              ) : null}
            </li>
          );
        })}
      </ol>

      {failed ? (
        <div className="flex flex-col gap-3">
          <div className="border-2 border-red-500/40 bg-red-500/5 px-4 py-3 text-sm text-red-600 dark:text-red-400">
            {job?.error ?? 'Something went wrong while generating this lesson.'}
          </div>
          <Link href="/">
            <Button>Try another source</Button>
          </Link>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          {done
            ? 'Opening your lesson…'
            : 'This may take a while — you can keep this tab open.'}
        </p>
      )}
    </div>
  );
}

function StepIcon({ state }: { state: StepState }) {
  const wrap = 'mt-0.5 flex size-6 shrink-0 items-center justify-center border-2';
  if (state === 'done') {
    return (
      <span className={cn(wrap, 'border-border bg-primary text-primary-foreground')}>
        <Check className="size-3.5" />
      </span>
    );
  }
  if (state === 'active') {
    return (
      <span className={cn(wrap, 'border-border bg-primary/20 text-primary')}>
        <Loader2 className="size-3.5 animate-spin" />
      </span>
    );
  }
  if (state === 'error') {
    return (
      <span className={cn(wrap, 'border-red-500/50 bg-red-500/10 text-red-500')}>
        <AlertCircle className="size-3.5" />
      </span>
    );
  }
  return (
    <span className={cn(wrap, 'border-border-soft text-muted-foreground')}>
      <span className="size-1.5 bg-current" />
    </span>
  );
}
