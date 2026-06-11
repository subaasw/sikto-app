'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import type { ReactNode } from 'react';
import { PixelLogo } from '@/components/pixel-logo';
import { useAuth } from '@/components/auth/auth-provider';

export default function AuthLayout({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === 'authenticated') router.replace('/');
  }, [status, router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 py-12">
      <Link href="/" className="mb-8 flex items-center gap-2.5">
        <span className="flex size-9 items-center justify-center border-2 border-border bg-primary text-foreground shadow-pixel-sm">
          <PixelLogo size={22} />
        </span>
        <span className="font-pixel text-xl tracking-tight">Sikto</span>
      </Link>
      <div className="w-full max-w-sm">{children}</div>
    </div>
  );
}