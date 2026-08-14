'use client';

import { useCallback, useSyncExternalStore } from 'react';

const STORAGE_KEY = 'sikto.model';

const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  window.addEventListener('storage', listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener('storage', listener);
  };
}

export function readModel(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function useModelPreference() {
  const model = useSyncExternalStore(subscribe, readModel, () => null);

  const setModel = useCallback((next: string | null) => {
    try {
      if (next) localStorage.setItem(STORAGE_KEY, next);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* private mode — selection cannot persist */
    }
    for (const listener of listeners) listener();
  }, []);

  return { model, setModel };
}
