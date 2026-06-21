export const AUTH_COOKIE = 'access_token';

const SERVER_API_BASE = process.env.API_INTERNAL_URL ?? 'http://localhost:8000';
const BROWSER_API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? '/api';

export function apiBase(): string {
  return typeof window === 'undefined' ? SERVER_API_BASE : BROWSER_API_BASE;
}
