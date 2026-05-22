'use client'

import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

type Status = 'live' | 'mock' | 'checking'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export function APIStatus() {
  const [status, setStatus] = useState<Status>('checking')

  useEffect(() => {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 10000)

    fetch(`${API_BASE}/api/health`, { signal: controller.signal, cache: 'no-store' })
      .then((r) => setStatus(r.ok ? 'live' : 'mock'))
      .catch(() => setStatus('mock'))
      .finally(() => clearTimeout(timer))
  }, [])

  if (status === 'checking') return null

  return (
    <div className={cn(
      'flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium',
      status === 'live'
        ? 'bg-emerald-500/15 text-emerald-400'
        : 'bg-white/8 text-white/50'
    )}>
      <span className={cn(
        'h-1.5 w-1.5 rounded-full',
        status === 'live' ? 'bg-emerald-400 animate-pulse' : 'bg-white/40'
      )} />
      {status === 'live' ? 'Live Data' : 'Mock Data'}
    </div>
  )
}
