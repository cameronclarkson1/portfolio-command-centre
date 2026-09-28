import { NextRequest, NextResponse } from 'next/server'

// POST /api/auth/login
// Validates the password and sets a session cookie.
export async function POST(req: NextRequest) {
  const { password } = await req.json()

  const correct = process.env.APP_PASSWORD
  if (!correct) {
    return NextResponse.json({ error: 'APP_PASSWORD not set on server' }, { status: 500 })
  }

  if (password !== correct) {
    // Wrong password — return 401 so the login page can show an error
    return NextResponse.json({ error: 'Incorrect password' }, { status: 401 })
  }

  // Password correct — set a session cookie
  const secret = process.env.SESSION_SECRET || 'changeme'
  const res = NextResponse.json({ ok: true })

  res.cookies.set('hf_session', secret, {
    httpOnly: true,     // Not accessible from JavaScript (safer)
    secure: true,       // Only sent over HTTPS
    sameSite: 'strict', // Not sent on cross-site requests
    maxAge: 60 * 60 * 24 * 30, // Stay logged in for 30 days
    path: '/',
  })

  return res
}
