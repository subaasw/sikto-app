import { NextResponse, type NextRequest } from 'next/server';
import { AUTH_COOKIE } from '@/lib/config';

const PUBLIC_PATHS = ['/login', '/signup'];

/**
 * Primary route guard (Next.js "proxy", formerly "middleware"): redirect
 * unauthenticated navigation to `/login` when no access-token cookie is present.
 * Signature verification stays in the API.
 *
 * We deliberately do NOT redirect cookie-bearing users away from /login: the
 * cookie may be stale (e.g. signed with a rotated JWT secret), and the real
 * check happens in AuthProvider via /auth/me. Sending them to "/" here would
 * bounce them straight back and create a loop. The (auth) layout redirects
 * genuinely-authenticated users away from /login based on real session status.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = request.cookies.has(AUTH_COOKIE);
  const isPublic = PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));

  if (!hasSession && !isPublic) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  // Run on everything except Next internals, the API routes, and static assets.
  matcher: ['/((?!_next/static|_next/image|api|favicon.ico|icon.svg).*)'],
};
