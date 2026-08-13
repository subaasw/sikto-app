import { apiBase } from '@/lib/config';
import type {
  ApiCourse,
  ApiLesson,
  ChatMessage,
  CreateSourceInput,
  Job,
  LessonSummary,
  MediaAsset,
  MediaSearchResult,
  SceneAudioTrack,
  Template,
} from '@/types/api';

// Re-exported so `@/lib/api` stays a one-stop surface; definitions live in @/types.
export * from '@/types/api';

const API_BASE = apiBase();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (res.status === 401 && typeof window !== 'undefined') {
    // Session expired or missing — bounce to login.
    window.location.href = '/login';
    throw new Error('API 401: not authenticated');
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${detail || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function createSource(body: CreateSourceInput): Promise<{ job_id: string }> {
  return request('/sources', { method: 'POST', body: JSON.stringify(body) });
}

/** Uploads PDF/DOCX/PPTX/XLSX/EPUB files; the API converts them to markdown via
 * MarkItDown once the lesson job runs. Returns each file's server-side path,
 * which slots straight into `inputs` on createSource. */
export async function uploadSourceDocuments(
  files: File[],
): Promise<{ path: string; name: string }[]> {
  const form = new FormData();
  for (const file of files) form.append('files', file);
  const res = await fetch(`${API_BASE}/sources/upload`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`Upload failed (${res.status}): ${detail || res.statusText}`);
  }
  return res.json();
}

export function getJob(id: string): Promise<Job> {
  return request(`/jobs/${id}`);
}

export function getLesson(jobId: string): Promise<ApiLesson> {
  return request(`/lessons/${jobId}`, { cache: 'no-store' });
}

export function getCourseByJob(jobId: string): Promise<ApiCourse> {
  return request(`/courses/by-job/${jobId}`, { cache: 'no-store' });
}

export function generateModule(courseId: string, order: number): Promise<{ job_id: string }> {
  return request(`/courses/${courseId}/modules/${order}/generate`, { method: 'POST' });
}

export function listLessons(): Promise<LessonSummary[]> {
  return request('/lessons', { cache: 'no-store' });
}

export function listTemplates(): Promise<Template[]> {
  return request('/templates');
}

export function listAssets(): Promise<MediaAsset[]> {
  return request('/assets', { cache: 'no-store' });
}

export function addAsset(body: {
  kind: string;
  title: string;
  url: string;
  tags?: string[];
}): Promise<MediaAsset> {
  return request('/assets', { method: 'POST', body: JSON.stringify(body) });
}

export async function uploadAssets(
  files: File[],
  fields: { kind: string; tags: string },
): Promise<MediaAsset[]> {
  const form = new FormData();
  for (const file of files) form.append('files', file);
  form.append('kind', fields.kind);
  form.append('tags', fields.tags);
  const res = await fetch(`${API_BASE}/assets/upload`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed (${res.status})`);
  return res.json() as Promise<MediaAsset[]>;
}

export async function deleteAsset(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/assets/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!res.ok && res.status !== 204) throw new Error(`Delete failed (${res.status})`);
}

export function searchMedia(q: string, kind: string): Promise<MediaSearchResult[]> {
  return request(`/assets/search?q=${encodeURIComponent(q)}&kind=${encodeURIComponent(kind)}`);
}

export function getSceneDocument(jobId: string): Promise<import('@/lib/scene/types').SceneDocument> {
  return request(`/lessons/${jobId}/scene-document`, { cache: 'no-store' });
}

export function getLessonAudio(jobId: string): Promise<SceneAudioTrack[]> {
  return request(`/lessons/${jobId}/audio`, { cache: 'no-store' });
}

export function getLessonManim(jobId: string): Promise<{ scene_id: string; url: string }[]> {
  return request(`/lessons/${jobId}/manim`, { cache: 'no-store' });
}

// Streams the assistant reply as plain-text token deltas for incremental render.
export async function* streamChat(
  messages: ChatMessage[],
  signal?: AbortSignal,
): AsyncGenerator<string> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
    signal,
  });
  if (!res.ok || !res.body) {
    const detail = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${detail || res.statusText}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    const text = decoder.decode(value, { stream: true });
    if (text) yield text;
  }
}
