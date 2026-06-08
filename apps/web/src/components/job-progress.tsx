'use client';

import { useRouter } from 'next/navigation';
import { AlertCircle, Check, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { getJob, type Job, type JobStatus } from '@/lib/api';
import { cn } from '@/lib/utils';

const STEPS: { key: JobStatus; label: string }[] = [
  { key: 'loading', label: 'Loading source' },
  { key: 'embedding', label: 'Indexing knowledge' },
  { key: 'planning', label: 'Planning the lesson' },
  { key: 'narrating', label: 'Synthesizing narration' },
  { key: 'rendering', label: 'Rendering video' },
];

type StepState = 'done' | 'active' | 'error' | 'pending';

export function JobProgress({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const next = await getJob(jobId);
        if (!active) return;
        setJob(next);
        if (next.status !== 'done' && next.status !== 'failed') {
          timer = setTimeout(poll, 1500);
        }
      } catch {
        if (!active) return;
        timer = setTimeout(poll, 3000);
      }
    }

    poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [jobId]);

  const status = job?.status;
  const currentIndex = status ? STEPS.findIndex((step) => step.key === status) : -1;
  const failed = status === 'failed';
  const done = status === 'done';

  function stepState(index: number, key: JobStatus): StepState {
    if (failed) return job?.step === key ? 'error' : index < currentIndex ? 'done' : 'pending';
    if (done || index < currentIndex) return 'done';
    if (index === currentIndex) return 'active';
    return 'pending';
  }

  return (
    <div className="flex flex-col gap-6">
      <ol className="flex flex-col">
        {STEPS.map((step, index) => {
          const state = stepState(index, step.key);
          return (
            <li key={step.key} className="flex items-center gap-3 px-1 py-2">
              <StepIcon state={state} />
              <span
                className={cn(
                  'text-sm',
                  state === 'pending' ? 'text-muted-foreground' : 'text-foreground',
                  state === 'active' && 'font-medium',
                )}
              >
                {step.label}
              </span>
            </li>
          );
        })}
      </ol>

      {!job ? <p className="px-1 text-sm text-muted-foreground">Connecting…</p> : null}

      {failed ? (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-600 dark:text-red-400">
          {job?.error ?? 'Generation failed.'}
        </div>
      ) : null}

      {done ? (
        <Button size="lg" className="self-start" onClick={() => router.push(`/lessons/${jobId}`)}>
          View lesson
        </Button>
      ) : null}
    </div>
  );
}

function StepIcon({ state }: { state: StepState }) {
  const wrap = 'flex size-6 shrink-0 items-center justify-center rounded-full';
  if (state === 'done') {
    return (
      <span className={cn(wrap, 'bg-primary text-primary-foreground')}>
        <Check className="size-3.5" />
      </span>
    );
  }
  if (state === 'active') {
    return (
      <span className={cn(wrap, 'bg-primary/10 text-primary')}>
        <Loader2 className="size-3.5 animate-spin" />
      </span>
    );
  }
  if (state === 'error') {
    return (
      <span className={cn(wrap, 'bg-red-500/10 text-red-500')}>
        <AlertCircle className="size-3.5" />
      </span>
    );
  }
  return (
    <span className={cn(wrap, 'border border-border text-muted-foreground')}>
      <span className="size-1.5 rounded-full bg-current" />
    </span>
  );
}
