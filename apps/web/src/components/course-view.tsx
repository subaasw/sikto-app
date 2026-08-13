'use client';

import Link from 'next/link';
import { CheckCircle2, GraduationCap, Loader2, Lock, Play, Sparkles } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getCourseByJob, generateModule, type ApiCourse, type ApiCourseModule } from '@/lib/api';

const GENERATING = new Set(['queued', 'loading', 'embedding', 'planning', 'narrating', 'rendering']);

export function CourseView({ course: initial }: { course: ApiCourse }) {
  const [course, setCourse] = useState(initial);
  const [busy, setBusy] = useState<number | null>(null);
  const polling = course.modules.some((m) => GENERATING.has(m.status));

  const refresh = useCallback(async () => {
    try {
      setCourse(await getCourseByJob(initial.job_id));
    } catch {
      // transient — keep the last good state and try again on the next tick
    }
  }, [initial.job_id]);

  // Poll only while something is generating; stop once every module settles.
  useEffect(() => {
    if (!polling) return;
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, [polling, refresh]);

  async function onGenerate(order: number) {
    setBusy(order);
    try {
      await generateModule(course.id, order);
      await refresh();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3">
        <Badge tone="active" className="self-start">
          <GraduationCap className="size-3" /> Course
        </Badge>
        <h1 className="text-2xl font-semibold tracking-tight">{course.title}</h1>
        <p className="text-muted-foreground">{course.summary}</p>
      </div>

      <ol className="flex flex-col gap-3">
        {course.modules.map((module) => (
          <ModuleRow
            key={module.order}
            module={module}
            busy={busy === module.order}
            onGenerate={() => onGenerate(module.order)}
          />
        ))}
      </ol>
    </div>
  );
}

function ModuleRow({
  module,
  busy,
  onGenerate,
}: {
  module: ApiCourseModule;
  busy: boolean;
  onGenerate: () => void;
}) {
  const generating = GENERATING.has(module.status);
  return (
    <li className="flex items-center gap-4 border-2 border-border bg-surface px-4 py-3 shadow-pixel-sm">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
        {module.status === 'done' ? <CheckCircle2 className="size-4" /> : module.order + 1}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{module.title}</p>
        <p className="truncate text-xs text-muted-foreground">{module.summary}</p>
      </div>
      <ModuleAction module={module} busy={busy} generating={generating} onGenerate={onGenerate} />
    </li>
  );
}

function ModuleAction({
  module,
  busy,
  generating,
  onGenerate,
}: {
  module: ApiCourseModule;
  busy: boolean;
  generating: boolean;
  onGenerate: () => void;
}) {
  if (module.status === 'done' && module.job_id) {
    return (
      <Link href={`/lessons/${module.job_id}`}>
        <Button size="sm" variant="secondary">
          <Play className="size-4" /> View lesson
        </Button>
      </Link>
    );
  }
  if (generating) {
    return (
      <span className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Generating…
      </span>
    );
  }
  if (module.status === 'failed' && module.job_id) {
    // ponytail: no reset endpoint — open the failed lesson to see why.
    return (
      <Link href={`/lessons/${module.job_id}`}>
        <Button size="sm" variant="ghost">
          Failed — open
        </Button>
      </Link>
    );
  }
  if (module.locked) {
    return (
      <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <Lock className="size-3.5" /> Locked
      </span>
    );
  }
  return (
    <Button size="sm" onClick={onGenerate} disabled={busy}>
      {busy ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
      Generate
    </Button>
  );
}
