import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const isLoginPage = request.nextUrl.pathname === '/';
  const hasSessionCookie =
    request.cookies.has('bakery_session') ||
    request.cookies.has('session') ||
    request.cookies.has('auth_token');

  // Redirect authenticated users away from login
  if (isLoginPage && hasSessionCookie) {
    return NextResponse.redirect(new URL('/helpdesk', request.url));
  }

  // Allow all other requests (API will handle auth)
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
