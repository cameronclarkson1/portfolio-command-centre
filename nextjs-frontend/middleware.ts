import { NextRequest, NextResponse } from 'next/server'

// ── Private app protection ───────────────────────────────────────────────────
// Every page requires a valid session cookie.
// The login page and the auth API route are the only public routes.

const PUBLIC_PATHS = ['/login', '/api/auth']

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  // Allow login page and auth API through without a session
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  // Check for a valid session cookie set by /api/auth/login
  const session = req.cookies.get('hf_session')?.value
  const secret  = process.env.SESSION_SECRET || 'changeme'

  if (session !== secret) {
    // Not logged in — redirect to the login page
    const loginUrl = req.nextUrl.clone()
    loginUrl.pathname = '/login'
    loginUrl.searchParams.set('from', pathname) // remember where they were going
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

// Apply to all routes except Next.js internals and static files
export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|icon|apple-icon|manifest|sw\\.js).*)'],
}
