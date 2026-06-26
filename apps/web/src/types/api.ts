import type { SceneTheme } from '@/lib/scene/types';

export type SourceType = 'text' | 'url' | 'youtube';

export type JobStatus =
  | 'queued'
  | 'loading'
  | 'embedding'
  | 'planning'
  | 'narrating'
  | 'rendering'
  | 'done'
  | 'failed';

export interface Job {
  id: string;
  status: JobStatus;
  step: string | null;
  error: string | null;
}

export interface CreateSourceInput {
  type: SourceType | 'mixed';
  /** Several sources (links / videos / pasted text) combined into one lesson. */
  inputs: string[];
  template?: string;
  mode?: string;
  voice?: string;
}

export interface ApiQuizItem {
  question: string;
  choices: string[] | null;
  answer: string;
  explanation: string;
}

export interface ApiLesson {
  id: string;
  title: string;
  summary: string;
  key_points: string[];
  video_url: string | null;
  transcript_url: string | null;
  script_url: string | null;
  quiz: ApiQuizItem[];
}

export interface LessonSummary {
  job_id: string;
  title: string;
  summary: string;
  has_video: boolean;
  created_at: string | null;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  theme: SceneTheme;
}

export interface MediaAsset {
  id: string;
  kind: string;
  title: string;
  url: string;
  tags: string[];
  source: string | null;
  license: string | null;
}

export interface MediaSearchResult {
  title: string;
  url: string;
  thumbnail: string;
  source: string;
  kind: string;
  license: string | null;
  tags: string[];
}

export interface WordTiming {
  text: string;
  start_ms: number;
  end_ms: number;
}

export interface SceneAudioTrack {
  scene_id: string;
  url: string;
  duration_ms: number;
  words: WordTiming[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}
