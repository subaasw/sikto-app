'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LibraryBig, MessagesSquare, Sparkles, type LucideIcon } from 'lucide-react';
import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { PixelLogo } from '@/components/pixel-logo';

const nav: { href: string; label: string; icon: LucideIcon }[] = [
  { href: '/', label: 'Create', icon: Sparkles },
  { href: '/library', label: 'Library', icon: LibraryBig },
  { href: '/chat', label: 'Chat', icon: MessagesSquare },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col border-r-2 border-border bg-surface px-3 py-4 sm:flex">
        <Link href="/" className="mb-8 flex items-center gap-2.5 px-2">
          <span className="flex size-8 items-center justify-center border-2 border-border bg-primary text-foreground shadow-pixel-sm">
            <PixelLogo size={20} />
          </span>
          <span className="font-pixel text-lg tracking-tight">Sikto</span>
        </Link>

        <nav className="flex flex-col gap-1.5">
          {nav.map((item) => {
            const active = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 border-2 px-3 py-2 text-sm font-medium transition-colors',
                  active
                    ? 'border-border bg-primary text-foreground shadow-pixel-sm'
                    : 'border-transparent text-muted-foreground hover:border-border hover:bg-muted hover:text-foreground',
                )}
              >
                <Icon className="size-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <p className="mt-auto px-3 font-pixel text-[0.65rem] uppercase tracking-wide text-muted-foreground">
          Microlearning studio
        </p>
      </aside>

      <main className="flex-1">{children}</main>
    </div>
  );
}
