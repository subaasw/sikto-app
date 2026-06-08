'use client';

import { Check, Play, Sparkles } from 'lucide-react';
import { useState } from 'react';
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
  quiz: QuizItem[];
}

export function LessonView({ lesson }: { lesson: LessonData }) {
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <Badge tone="active" className="self-start">
          <Sparkles className="size-3" /> Microlearning lesson
        </Badge>
        <h1 className="text-2xl font-semibold tracking-tight">{lesson.title}</h1>
        <p className="text-muted-foreground">{lesson.summary}</p>
      </header>

      <VideoPlayer url={lesson.videoUrl} />

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

function VideoPlayer({ url }: { url: string | null }) {
  if (url) {
    return (
      <video controls className="w-full rounded-xl border border-border bg-black shadow-sm">
        <source src={url} type="video/mp4" />
      </video>
    );
  }
  return (
    <div className="flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-muted text-muted-foreground">
      <Play className="size-8" />
      <p className="text-sm">The narrated video will appear here once rendering finishes.</p>
    </div>
  );
}

function QuizCard({ item, index }: { item: QuizItem; index: number }) {
  const [revealed, setRevealed] = useState(false);

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-5">
        <p className="text-sm font-medium">
          {index + 1}. {item.question}
        </p>

        {item.choices ? (
          <ul className="flex flex-col gap-2">
            {item.choices.map((choice) => {
              const isAnswer = revealed && choice === item.answer;
              return (
                <li
                  key={choice}
                  className={
                    isAnswer
                      ? 'rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300'
                      : 'rounded-lg border border-border px-3 py-2 text-sm'
                  }
                >
                  {choice}
                </li>
              );
            })}
          </ul>
        ) : null}

        {revealed ? (
          <div className="rounded-lg bg-muted px-3 py-2 text-sm">
            <span className="font-medium">Answer: </span>
            {item.answer}
            <p className="mt-1 text-muted-foreground">{item.explanation}</p>
          </div>
        ) : (
          <Button variant="secondary" size="sm" className="self-start" onClick={() => setRevealed(true)}>
            Reveal answer
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
