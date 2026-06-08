import Link from 'next/link';
import { LessonView, type LessonData } from '@/components/lesson-view';
import { Button } from '@/components/ui/button';
import { getLesson } from '@/lib/api';

export default async function LessonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let lesson: LessonData | null = null;
  try {
    const data = await getLesson(id);
    lesson = {
      title: data.title,
      summary: data.summary,
      keyPoints: data.key_points,
      videoUrl: data.video_url,
      quiz: data.quiz.map((item) => ({
        question: item.question,
        choices: item.choices ?? undefined,
        answer: item.answer,
        explanation: item.explanation,
      })),
    };
  } catch {
    lesson = null;
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10 sm:px-8 sm:py-14">
      {lesson ? <LessonView lesson={lesson} /> : <NotReady />}
    </div>
  );
}

function NotReady() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-border bg-surface py-16 text-center">
      <p className="font-medium">This lesson isn’t ready yet</p>
      <p className="text-sm text-muted-foreground">
        It may still be generating, or the API isn’t running.
      </p>
      <Link href="/">
        <Button>Back to create</Button>
      </Link>
    </div>
  );
}
