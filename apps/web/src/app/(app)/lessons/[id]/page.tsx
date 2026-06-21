import Link from 'next/link';
import type { ReactNode } from 'react';
import { LessonProgress } from '@/components/lesson-progress';
import { LessonView, type LessonData } from '@/components/lesson-view';
import { LessonStage } from '@/components/player/lesson-stage';
import { Button } from '@/components/ui/button';
import {
  getJob,
  getLesson,
  getLessonAudio,
  getSceneDocument,
  type Job,
  type SceneAudioTrack,
} from '@/lib/api';
import type { SceneDocument } from '@/lib/scene/types';

export default async function LessonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  // One URL for the whole lifecycle: poll the job, show live progress while it
  // generates, then the finished lesson. LessonProgress refreshes this route
  // when the job completes.
  let job: Job | null = null;
  try {
    job = await getJob(id);
  } catch {
    job = null;
  }

  if (!job) {
    return (
      <Shell>
        <NotReady />
      </Shell>
    );
  }

  if (job.status !== 'done') {
    return (
      <Shell title="Your lesson" subtitle="Hang tight while we put it together.">
        <LessonProgress jobId={id} initialJob={job} />
      </Shell>
    );
  }

  const lesson = await loadLesson(id);
  if (!lesson) {
    return (
      <Shell>
        <NotReady />
      </Shell>
    );
  }

  let document: SceneDocument | null = null;
  try {
    document = await getSceneDocument(id);
  } catch {
    document = null;
  }

  let audio: SceneAudioTrack[] = [];
  try {
    audio = await getLessonAudio(id);
  } catch {
    audio = [];
  }

  return (
    <Shell>
      <LessonView
        lesson={lesson}
        player={document ? <LessonStage document={document} audio={audio} /> : undefined}
      />
    </Shell>
  );
}

async function loadLesson(id: string): Promise<LessonData | null> {
  try {
    const data = await getLesson(id);
    return {
      title: data.title,
      summary: data.summary,
      keyPoints: data.key_points,
      videoUrl: data.video_url,
      transcriptUrl: data.transcript_url,
      scriptUrl: data.script_url,
      quiz: data.quiz.map((item) => ({
        question: item.question,
        choices: item.choices ?? undefined,
        answer: item.answer,
        explanation: item.explanation,
      })),
    };
  } catch {
    return null;
  }
}

function Shell({
  children,
  title,
  subtitle,
}: {
  children: ReactNode;
  title?: string;
  subtitle?: string;
}) {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10 sm:px-8 sm:py-14">
      {title ? (
        <div className="mb-8 flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {subtitle ? <p className="text-muted-foreground">{subtitle}</p> : null}
        </div>
      ) : null}
      {children}
    </div>
  );
}

function NotReady() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 border-2 border-dashed border-border bg-surface py-16 text-center">
      <p className="font-medium">This lesson isn’t available</p>
      <p className="text-sm text-muted-foreground">
        It may have been removed, or the API isn’t running.
      </p>
      <Link href="/">
        <Button>Back to create</Button>
      </Link>
    </div>
  );
}
