import { apiBase } from '@/lib/config';
import type { LoginInput, SignupInput, User } from '@/types/auth';

const API_BASE = apiBase();

/** Thrown for non-2xx auth responses; carries the API's `detail` message. */
export class AuthRequestError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'AuthRequestError';
  }
}

async function authFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
}

async function parseError(res: Response): Promise<never> {
  let detail = res.statusText;
  try {
    const body = await res.json();
    if (typeof body?.detail === 'string') detail = body.detail;
  } catch {
    // non-JSON body; keep statusText
  }
  throw new AuthRequestError(res.status, detail);
}

export async function signup(input: SignupInput): Promise<User> {
  const res = await authFetch('/auth/signup', { method: 'POST', body: JSON.stringify(input) });
  if (!res.ok) return parseError(res);
  return res.json();
}

export async function login(input: LoginInput): Promise<User> {
  const res = await authFetch('/auth/login', { method: 'POST', body: JSON.stringify(input) });
  if (!res.ok) return parseError(res);
  return res.json();
}

export async function logout(): Promise<void> {
  await authFetch('/auth/logout', { method: 'POST' });
}

/** Returns the current user, or null when there is no valid session. */
export async function fetchMe(): Promise<User | null> {
  const res = await authFetch('/auth/me');
  if (res.status === 401) return null;
  if (!res.ok) return parseError(res);
  return res.json();
}
