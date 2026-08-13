'use client';

import { Check, FileText, Play, ScrollText, Sparkles, X } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { VideoPlayer } from '@/components/player/video-player';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export interface QuizItem {
  question: string;
  choices?: string[];
  answer: string;
  explanation: string;
}

export interface LessonData {
  title: string;
  summary: string;
  keyPoints: string[];
  videoUrl: string | null;
  transcriptUrl?: string | null;
  scriptUrl?: string | null;
  quiz: QuizItem[];
}

export function LessonView({ lesson, player }: { lesson: LessonData; player?: ReactNode }) {
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <Badge tone="active" className="self-start">
          <Sparkles className="size-3" /> Microlearning lesson
        </Badge>
        <h1 className="text-2xl font-semibold tracking-tight">{lesson.title}</h1>
        <p className="text-muted-foreground">{lesson.summary}</p>
      </header>

      {player ?? (lesson.videoUrl ? <VideoPlayer src={lesson.videoUrl} /> : <VideoPlaceholder />)}

      {player && lesson.videoUrl ? (
        <section className="flex flex-col gap-2">
          <h2 className="text-lg font-semibold tracking-tight">Rendered video</h2>
          <p className="text-sm text-muted-foreground">
            The narrated MP4 with baked-in voice-over.
          </p>
          <VideoPlayer src={lesson.videoUrl} />
        </section>
      ) : null}

      {lesson.transcriptUrl || lesson.scriptUrl ? (
        <div className="flex flex-wrap gap-2">
          {lesson.transcriptUrl ? (
            <DownloadLink href={lesson.transcriptUrl} icon={<FileText className="size-4" />}>
              Source transcript (.md)
            </DownloadLink>
          ) : null}
          {lesson.scriptUrl ? (
            <DownloadLink href={lesson.scriptUrl} icon={<ScrollText className="size-4" />}>
              Narration script (.md)
            </DownloadLink>
          ) : null}
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Key points</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="flex flex-col gap-3">
            {lesson.keyPoints.map((point, index) => (
              <li key={index} className="flex items-start gap-3">
                <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Check className="size-3" />
                </span>
                <span className="text-sm">{point}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold tracking-tight">Quiz</h2>
        {lesson.quiz.map((item, index) => (
          <QuizCard key={index} item={item} index={index} />
        ))}
      </section>
    </div>
  );
}

function DownloadLink({
  href,
  icon,
  children,
}: {
  href: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      download
      className="inline-flex items-center gap-2 border-2 border-border bg-surface px-3 py-2 text-sm font-medium shadow-pixel-sm transition-transform hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-pixel"
    >
      {icon}
      {children}
    </a>
  );
}

function VideoPlaceholder() {
  return (
    <div className="flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-muted text-muted-foreground">
      <Play className="size-8" />
      <p className="text-sm">The narrated video will appear here once rendering finishes.</p>
    </div>
  );
}

function QuizCard({ item, index }: { item: QuizItem; index: number }) {
  // Per-question self-check: pick a choice → instant right/wrong + explanation.
  const [selected, setSelected] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false); // choices-less fallback
  const answered = selected !== null;
  const correct = selected === item.answer;

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-5">
        <p className="text-sm font-medium">
          {index + 1}. {item.question}
        </p>

        {item.choices ? (
          <ul className="flex flex-col gap-2">
            {item.choices.map((choice) => {
              const isAnswer = choice === item.answer;
              const isChosen = choice === selected;
              let cls = 'border-border hover:bg-muted';
              if (answered && isAnswer)
                cls =
                  'border-emerald-500/50 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300';
              else if (answered && isChosen)
                cls = 'border-red-500/50 bg-red-500/10 text-red-700 dark:text-red-300';
              else if (answered) cls = 'border-border opacity-60';
              return (
                <li key={choice}>
                  <button
                    type="button"
                    disabled={answered}
                    onClick={() => setSelected(choice)}
                    className={`flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors disabled:cursor-default ${cls}`}
                  >
                    <span>{choice}</span>
                    {answered && isAnswer ? <Check className="size-4 shrink-0" /> : null}
                    {answered && isChosen && !isAnswer ? <X className="size-4 shrink-0" /> : null}
                  </button>
                </li>
              );
            })}
          </ul>
        ) : null}

        {item.choices && answered ? (
          <div className="rounded-lg bg-muted px-3 py-2 text-sm">
            <span className="font-medium">{correct ? 'Correct!' : 'Not quite.'} </span>
            {item.explanation}
          </div>
        ) : null}

        {!item.choices ? (
          revealed ? (
            <div className="rounded-lg bg-muted px-3 py-2 text-sm">
              <span className="font-medium">Answer: </span>
              {item.answer}
              <p className="mt-1 text-muted-foreground">{item.explanation}</p>
            </div>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              className="self-start"
              onClick={() => setRevealed(true)}
            >
              Reveal answer
            </Button>
          )
        ) : null}
      </CardContent>
    </Card>
  );
}
