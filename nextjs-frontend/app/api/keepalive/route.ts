// Vercel cron pings the Railway backend every hour to keep it warm.
// Without this, Railway sleeps after ~5 min of inactivity causing 20-30s cold starts.
export const dynamic = 'force-dynamic'

export async function GET() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  if (!apiUrl) {
    return Response.json({ ok: false, reason: 'No API URL configured' }, { status: 500 })
  }

  try {
    const res = await fetch(`${apiUrl}/api/health`, {
      signal: AbortSignal.timeout(8000),
    })
    const data = await res.json()
    return Response.json({ ok: true, backend: data, pinged: new Date().toISOString() })
  } catch (err) {
    return Response.json({ ok: false, error: String(err) }, { status: 503 })
  }
}
