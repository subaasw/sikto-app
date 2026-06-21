import { LibraryBig, Play, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { listLessons, type LessonSummary } from '@/lib/api';

export const dynamic = 'force-dynamic';

export default async function LibraryPage() {
  let lessons: LessonSummary[] = [];
  try {
    lessons = await listLessons();
  } catch {
    lessons = [];
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10 sm:px-8 sm:py-14">
      <div className="mb-8 flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">My Lessons</h1>
        <p className="text-muted-foreground">Every lesson you’ve generated — rewatch anytime.</p>
      </div>

      {lessons.length === 0 ? (
        <EmptyState />
      ) : (
        <ul className="flex flex-col gap-3">
          {lessons.map((lesson) => (
            <li key={lesson.job_id}>
              <LessonCard lesson={lesson} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function LessonCard({ lesson }: { lesson: LessonSummary }) {
  return (
    <Link
      href={`/lessons/${lesson.job_id}`}
      className="group flex items-start gap-4 border-2 border-border bg-surface p-4 shadow-pixel-sm transition-transform hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-pixel"
    >
      <span className="flex size-11 shrink-0 items-center justify-center border-2 border-border bg-primary text-primary-foreground">
        <Play className="size-5" />
      </span>
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex items-center gap-2">
          <h2 className="truncate text-sm font-semibold">{lesson.title}</h2>
          {lesson.has_video ? (
            <Badge tone="active" className="shrink-0">
              Video
            </Badge>
          ) : null}
        </div>
        <p className="line-clamp-2 text-sm text-muted-foreground">{lesson.summary}</p>
        {lesson.created_at ? (
          <span className="font-pixel text-[10px] uppercase tracking-wide text-muted-foreground">
            {formatDate(lesson.created_at)}
          </span>
        ) : null}
      </div>
    </Link>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 border-2 border-dashed border-border bg-surface py-16 text-center">
      <span className="flex size-12 items-center justify-center border-2 border-border bg-muted text-muted-foreground">
        <LibraryBig className="size-6" />
      </span>
      <div>
        <p className="font-medium">No lessons yet</p>
        <p className="text-sm text-muted-foreground">Generate your first lesson to see it here.</p>
      </div>
      <Link href="/">
        <Button>
          <Sparkles className="size-4" /> Create a lesson
        </Button>
      </Link>
    </div>
  );
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}
