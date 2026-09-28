'use client'

import { useState, FormEvent } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { TrendingUp, Lock, Eye, EyeOff, Loader2 } from 'lucide-react'

export default function LoginPage() {
  const router       = useRouter()
  const searchParams = useSearchParams()
  const from         = searchParams.get('from') || '/'

  const [password, setPassword]   = useState('')
  const [showPw,   setShowPw]     = useState(false)
  const [error,    setError]      = useState('')
  const [loading,  setLoading]    = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })

      if (res.ok) {
        // Logged in — go to the page they originally wanted
        router.push(from)
        router.refresh()
      } else {
        const data = await res.json()
        setError(data.error || 'Incorrect password')
        setPassword('')
      }
    } catch {
      setError('Connection error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0B1628] flex flex-col items-center justify-center px-4">

      {/* Background texture */}
      <div
        className="absolute inset-0 opacity-5"
        style={{
          backgroundImage: `radial-gradient(circle at 25% 25%, #3b82f6 0%, transparent 50%),
                            radial-gradient(circle at 75% 75%, #1d4ed8 0%, transparent 50%)`,
        }}
      />

      <div className="relative w-full max-w-sm">

        {/* Logo */}
        <div className="flex flex-col items-center mb-10">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 mb-4 shadow-xl">
            <TrendingUp className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">AI HedgeFund</h1>
          <p className="text-sm text-white/45 mt-1 tracking-widest uppercase font-medium">
            Private Market Intelligence
          </p>
        </div>

        {/* Card */}
        <div className="bg-white/6 border border-white/10 rounded-2xl p-8 shadow-2xl backdrop-blur-xl">
          <div className="flex items-center gap-2 mb-6">
            <Lock className="h-4 w-4 text-white/50" />
            <p className="text-sm text-white/50">Private access only</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Password field */}
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
                autoFocus
                className={`
                  w-full bg-white/8 border rounded-xl px-4 py-3.5 pr-11
                  text-white placeholder:text-white/30
                  outline-none focus:ring-2 transition-all
                  ${error
                    ? 'border-red-500/60 focus:ring-red-500/30'
                    : 'border-white/15 focus:border-white/30 focus:ring-white/10'
                  }
                `}
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/35 hover:text-white/60 transition-colors"
              >
                {showPw
                  ? <EyeOff className="h-4 w-4" />
                  : <Eye    className="h-4 w-4" />
                }
              </button>
            </div>

            {/* Error message */}
            {error && (
              <p className="text-sm text-red-400 flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-red-400 flex-shrink-0" />
                {error}
              </p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !password}
              className={`
                w-full flex items-center justify-center gap-2
                rounded-xl py-3.5 text-sm font-semibold
                transition-all duration-150
                ${loading || !password
                  ? 'bg-white/10 text-white/30 cursor-not-allowed'
                  : 'bg-blue-500 hover:bg-blue-400 text-white active:scale-[0.98] shadow-lg shadow-blue-500/25'
                }
              `}
            >
              {loading
                ? <><Loader2 className="h-4 w-4 animate-spin" /> Verifying…</>
                : 'Access Dashboard'
              }
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-white/20 mt-8">
          Your data. Your rules. Fully private.
        </p>
      </div>
    </div>
  )
}
