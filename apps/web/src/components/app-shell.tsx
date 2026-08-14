'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  ChevronUp,
  Images,
  LayoutTemplate,
  LibraryBig,
  LogOut,
  MessagesSquare,
  Settings2,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { PixelLogo } from '@/components/pixel-logo';
import { useAuth } from '@/components/auth/auth-provider';
import { ThemeToggle } from '@/components/theme-toggle';
import { JobEventsProvider } from '@/components/job-events-provider';

const nav: { href: string; label: string; icon: LucideIcon }[] = [
  { href: '/', label: 'Create', icon: Sparkles },
  { href: '/library', label: 'My Lessons', icon: LibraryBig },
  { href: '/templates', label: 'Templates', icon: LayoutTemplate },
  { href: '/media', label: 'Media', icon: Images },
  { href: '/chat', label: 'Chat', icon: MessagesSquare },
  { href: '/settings', label: 'Settings', icon: Settings2 },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  async function handleLogout() {
    await logout();
    router.replace('/login');
  }

  return (
    <JobEventsProvider>
      <div className="flex min-h-screen">
        <aside className="border-border bg-surface sticky top-0 hidden h-screen w-60 shrink-0 flex-col self-start overflow-y-auto border-r-2 px-3 py-4 sm:flex">
          <div className="mb-8 flex items-center justify-between gap-2 px-2">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="border-border bg-primary text-primary-foreground shadow-pixel-sm flex size-8 items-center justify-center border-2">
                <PixelLogo size={20} />
              </span>
              <span className="font-pixel text-lg tracking-tight">Sikto</span>
            </Link>
            <ThemeToggle />
          </div>

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
                      ? 'border-border bg-primary text-primary-foreground shadow-pixel-sm'
                      : 'text-muted-foreground hover:border-border hover:bg-muted hover:text-foreground border-transparent',
                  )}
                >
                  <Icon className="size-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {user ? <ProfileMenu user={user} onLogout={handleLogout} /> : null}
        </aside>

        <main className="flex-1">{children}</main>
      </div>
    </JobEventsProvider>
  );
}

/** Clickable profile card that opens a small popover menu (logout for now). */
function ProfileMenu({
  user,
  onLogout,
}: {
  user: { name: string; email: string };
  onLogout: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative mt-auto">
      {open ? (
        <div
          role="menu"
          className="border-border bg-surface shadow-pixel-sm absolute inset-x-0 bottom-full mb-2 border-2"
        >
          <button
            type="button"
            role="menuitem"
            onClick={onLogout}
            className="text-muted-foreground hover:bg-muted hover:text-foreground flex w-full items-center gap-3 px-3 py-2 text-sm font-medium transition-colors"
          >
            <LogOut className="size-4" />
            Log out
          </button>
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        className={cn(
          'flex w-full items-center gap-2 border-2 px-3 py-2 text-left transition-colors',
          open ? 'border-border bg-muted' : 'border-border-soft hover:border-border hover:bg-muted',
        )}
      >
        <span className="border-border bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center border-2 text-xs font-semibold">
          {user.name.charAt(0).toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{user.name}</p>
          <p className="text-muted-foreground truncate text-xs">{user.email}</p>
        </div>
        <ChevronUp
          className={cn(
            'text-muted-foreground size-4 shrink-0 transition-transform',
            !open && 'rotate-180',
          )}
        />
      </button>
    </div>
  );
}
