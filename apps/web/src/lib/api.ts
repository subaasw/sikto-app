const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

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
  type: SourceType;
  input: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${detail || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function createSource(body: CreateSourceInput): Promise<{ job_id: string }> {
  return request('/sources', { method: 'POST', body: JSON.stringify(body) });
}

export function getJob(id: string): Promise<Job> {
  return request(`/jobs/${id}`);
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
  quiz: ApiQuizItem[];
}

export function getLesson(jobId: string): Promise<ApiLesson> {
  return request(`/lessons/${jobId}`, { cache: 'no-store' });
}
