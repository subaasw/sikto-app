'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import * as authApi from '@/lib/auth/api';
import type { LoginInput, SignupInput, User } from '@/types/auth';

type Status = 'loading' | 'authenticated' | 'unauthenticated';

interface AuthContextValue {
  user: User | null;
  status: Status;
  login: (input: LoginInput) => Promise<void>;
  signup: (input: SignupInput) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({
  children,
  initialUser = null,
}: {
  children: ReactNode;
  initialUser?: User | null;
}) {
  const [user, setUser] = useState<User | null>(initialUser);
  const [status, setStatus] = useState<Status>(initialUser ? 'authenticated' : 'loading');

  // Hydrate the session from the cookie on first mount.
  useEffect(() => {
    let active = true;
    if (initialUser) return;
    authApi
      .fetchMe()
      .then((me) => {
        if (!active) return;
        setUser(me);
        setStatus(me ? 'authenticated' : 'unauthenticated');
      })
      .catch(() => {
        if (!active) return;
        setUser(null);
        setStatus('unauthenticated');
      });
    return () => {
      active = false;
    };
  }, [initialUser]);

  const login = useCallback(async (input: LoginInput) => {
    const me = await authApi.login(input);
    setUser(me);
    setStatus('authenticated');
  }, []);

  const signup = useCallback(async (input: SignupInput) => {
    const me = await authApi.signup(input);
    setUser(me);
    setStatus('authenticated');
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, login, signup, logout }),
    [user, status, login, signup, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an <AuthProvider>');
  return ctx;
}