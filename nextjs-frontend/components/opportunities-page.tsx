'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import {
  TrendingUp, RefreshCw, Clock, AlertCircle, Loader2,
  BarChart3, ChevronUp, ChevronDown, Zap, CheckCircle2, Info,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  fetchScannerResults, fetchScannerStatus, triggerScan,
  type ScannerOpportunity, type ScannerResults, type ScannerStatus,
} from '@/lib/api'

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, decimals = 1, suffix = ''): string {
  if (n == null) return '—'
  return `${n.toFixed(decimals)}${suffix}`
}

function fmtMarketCap(n: number | null): string {
  if (!n) return '—'
  if (n >= 1e12) return `$${(n / 1e12).toFixed(1)}T`
  if (n >= 1e9)  return `$${(n / 1e9).toFixed(1)}B`
  return `$${(n / 1e6).toFixed(0)}M`
}

function toRelative(iso: string | null): string {
  if (!iso) return 'Never'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 2)  return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24)  return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

type SortKey = 'score' | 'ev_ebitda' | 'roic' | 'rev_growth' | 'market_cap'

// ── Opportunity card ──────────────────────────────────────────────────────────

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? 'bg-success' : score >= 55 ? 'bg-primary' : score >= 40 ? 'bg-gold' : 'bg-destructive'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-bold text-foreground w-6 text-right">{score}</span>
    </div>
  )
}

function MetricCell({ label, value, highlight }: { label: string; value: string; highlight?: 'good' | 'bad' | null }) {
  return (
    <div>
      <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-0.5">{label}</p>
      <p className={cn(
        'text-xs font-semibold',
        highlight === 'good' ? 'text-success' : highlight === 'bad' ? 'text-destructive' : 'text-foreground'
      )}>{value}</p>
    </div>
  )
}

function OpportunityCard({ stock, rank }: { stock: ScannerOpportunity; rank: number }) {
  const changeUp = (stock.change_pct ?? 0) >= 0
  const pctFromLow = (stock.year_high && stock.year_low && stock.price && stock.year_high > stock.year_low)
    ? ((stock.price - stock.year_low) / (stock.year_high - stock.year_low)) * 100
    : null

  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-accent text-[11px] font-bold text-muted-foreground flex-shrink-0">
            {rank}
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-bold text-foreground">{stock.ticker}</span>
              {stock.roic && stock.roic > 20 && (
                <CheckCircle2 className="h-3 w-3 text-success" aria-label="High ROIC" />
              )}
            </div>
            <p className="text-[11px] text-muted-foreground truncate max-w-[130px]">{stock.name || '—'}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-base font-semibold text-foreground">${fmt(stock.price, 2, '')}</p>
          <span className={cn('text-[11px] font-medium flex items-center justify-end gap-0.5', changeUp ? 'text-success' : 'text-destructive')}>
            {changeUp ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {fmt(Math.abs((stock.change_pct ?? 0) * 100), 2, '%')}
          </span>
        </div>
      </div>

      {/* Sector */}
      {stock.sector && (
        <div className="mb-3">
          <span className="inline-block rounded-md bg-accent px-2 py-0.5 text-[10px] font-medium text-accent-foreground">
            {stock.sector}
          </span>
        </div>
      )}

      {/* Score bar */}
      <div className="mb-3">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Composite Score</p>
        <ScoreBar score={stock.score} />
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 mb-3 pt-3 border-t border-border">
        <MetricCell
          label="ROIC"
          value={fmt(stock.roic, 1, '%')}
          highlight={stock.roic ? (stock.roic > 15 ? 'good' : stock.roic < 0 ? 'bad' : null) : null}
        />
        <MetricCell
          label="EV/EBITDA"
          value={fmt(stock.ev_ebitda, 1, 'x')}
          highlight={stock.ev_ebitda ? (stock.ev_ebitda < 12 ? 'good' : stock.ev_ebitda > 28 ? 'bad' : null) : null}
        />
        <MetricCell
          label="P/E Ratio"
          value={fmt(stock.pe_ratio, 1, 'x')}
          highlight={stock.pe_ratio ? (stock.pe_ratio < 18 ? 'good' : stock.pe_ratio > 40 ? 'bad' : null) : null}
        />
        <MetricCell
          label="Net Margin"
          value={fmt(stock.net_margin, 1, '%')}
          highlight={stock.net_margin ? (stock.net_margin > 12 ? 'good' : stock.net_margin < 0 ? 'bad' : null) : null}
        />
        <MetricCell
          label="Rev Growth"
          value={stock.rev_growth != null ? `${stock.rev_growth > 0 ? '+' : ''}${fmt(stock.rev_growth, 1, '%')}` : '—'}
          highlight={stock.rev_growth ? (stock.rev_growth > 8 ? 'good' : stock.rev_growth < -5 ? 'bad' : null) : null}
        />
        <MetricCell
          label="Current Ratio"
          value={fmt(stock.current_ratio, 2, 'x')}
          highlight={stock.current_ratio ? (stock.current_ratio >= 1.5 ? 'good' : stock.current_ratio < 1.0 ? 'bad' : null) : null}
        />
      </div>

      {/* 52W range bar */}
      {pctFromLow != null && (
        <div>
          <div className="h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary/60"
              style={{ width: `${Math.min(100, Math.max(2, pctFromLow))}%` }}
            />
          </div>
          <div className="flex justify-between text-[9px] text-muted-foreground mt-1">
            <span>${fmt(stock.year_low, 2, '')}</span>
            <span>${fmt(stock.year_high, 2, '')}</span>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

interface OpportunitiesPageProps {
  initialResults?: ScannerResults | null
  initialStatus?:  ScannerStatus  | null
}

export function OpportunitiesPage({ initialResults, initialStatus }: OpportunitiesPageProps) {
  const [results, setResults]       = useState<ScannerResults | null>(initialResults ?? null)
  const [status, setStatus]         = useState<ScannerStatus | null>(initialStatus ?? null)
  const [loading, setLoading]       = useState(!initialResults)
  const [triggering, setTriggering] = useState(false)
  const [triggerError, setTriggerError] = useState(false)
  const [sortKey, setSortKey]       = useState<SortKey>('score')
  const [sectorFilter, setSectorFilter] = useState('All')

  const pollStatus = useCallback(async () => {
    const stat = await fetchScannerStatus()
    if (!stat) return
    setStatus(stat)
    if (!stat.running) {
      setTriggering(false)
      const res = await fetchScannerResults()
      if (res) setResults(res)
    }
  }, [])

  const load = useCallback(async () => {
    const [res, stat] = await Promise.all([fetchScannerResults(), fetchScannerStatus()])
    if (res)  setResults(res)
    if (stat) {
      setStatus(stat)
      if (!stat.running) setTriggering(false)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    if (!initialResults) load()
    const interval = setInterval(pollStatus, 8_000)
    return () => clearInterval(interval)
  }, [load, pollStatus, initialResults])

  const handleTrigger = async () => {
    setTriggering(true)
    setTriggerError(false)
    const result = await triggerScan()
    if (!result) {
      setTriggering(false)
      setTriggerError(true)
      return
    }
    // Poll quickly a few times to catch the backend's running:true before the regular interval does
    for (const delay of [800, 2000, 4000]) {
      await new Promise(r => setTimeout(r, delay))
      const stat = await fetchScannerStatus()
      if (stat) {
        setStatus(stat)
        if (stat.running) break          // backend confirmed — normal polling takes over
        if (delay === 4000) setTriggering(false)  // backend never went running, give up
      }
    }
  }

  const opportunities = results?.opportunities ?? []
  const sectors = ['All', ...Array.from(new Set(opportunities.map(o => o.sector).filter(Boolean)))]
  const isRunning = status?.running || triggering

  const filtered = opportunities
    .filter(o => sectorFilter === 'All' || o.sector === sectorFilter)
    .slice()
    .sort((a, b) => {
      if (sortKey === 'score')      return b.score - a.score
      if (sortKey === 'ev_ebitda')  return (a.ev_ebitda ?? 999) - (b.ev_ebitda ?? 999)
      if (sortKey === 'roic')       return (b.roic ?? -999) - (a.roic ?? -999)
      if (sortKey === 'rev_growth') return (b.rev_growth ?? -999) - (a.rev_growth ?? -999)
      if (sortKey === 'market_cap') return (b.market_cap ?? 0) - (a.market_cap ?? 0)
      return 0
    })

  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6 max-w-[1600px] mx-auto">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Zap className="h-5 w-5 text-gold" />
            Best Opportunities
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Daily scan of S&amp;P 500 · Dow Jones · NASDAQ-100 — ranked by composite score
          </p>
        </div>
        <button
          onClick={handleTrigger}
          disabled={isRunning}
          className={cn(
            'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors border',
            isRunning
              ? 'bg-muted text-muted-foreground border-border cursor-not-allowed'
              : 'bg-accent text-accent-foreground border-border hover:bg-accent/80'
          )}
        >
          {isRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          {isRunning ? 'Scanning…' : 'Run Scan Now'}
        </button>
      </div>

      {/* How the score works */}
      <div className="flex items-start gap-3 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-xs text-muted-foreground">
        <Info className="h-4 w-4 mt-0.5 flex-shrink-0 text-primary" />
        <p>
          <span className="font-semibold text-foreground">How to use this page:</span>{' '}
          The composite score reflects <span className="font-medium text-foreground">quality + sector-relative valuation + growth + safety</span>.
          It ranks which stocks in the universe are most compelling <em>right now</em> — not a buy signal by itself.
          Use the <Link href="/research" className="font-medium text-primary underline underline-offset-2">Stock Research</Link> tab
          to run a full 9-model fair value analysis on any stock that catches your eye.
        </p>
      </div>

      {/* Status bar */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-border bg-card px-4 py-3 text-xs shadow-sm">
        <div className="flex items-center gap-2">
          <span className={cn('h-2 w-2 rounded-full', isRunning ? 'bg-gold animate-pulse' : status?.results_available ? 'bg-success' : 'bg-muted-foreground')} />
          <span className="text-muted-foreground">{isRunning ? 'Scan in progress…' : status?.results_available ? 'Results ready' : 'No results yet'}</span>
        </div>
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          Last scan: <span className="font-medium text-foreground">{toRelative(status?.last_run ?? null)}</span>
        </div>
        {status?.last_run_duration_s != null && (
          <span className="text-muted-foreground">{status.last_run_duration_s}s to complete</span>
        )}
        {results?.universe_size && (
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <BarChart3 className="h-3.5 w-3.5" />
            <span className="font-medium text-foreground">{results.universe_size}</span> scanned ·{' '}
            <span className="font-medium text-foreground">{opportunities.length}</span> opportunities
          </div>
        )}
        <span className="ml-auto text-muted-foreground hidden sm:block">Auto-scans Mon–Fri at 4:15 PM ET</span>
      </div>

      {/* Trigger error */}
      {triggerError && (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <p>Could not reach the API at <strong>localhost:8000</strong>. Make sure the backend is running: <code className="font-mono text-xs">uvicorn main:app --reload --port 8000</code></p>
        </div>
      )}

      {/* Error */}
      {status?.error && (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <p>{status.error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center gap-3 py-20 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="text-sm">Loading results…</p>
        </div>
      )}

      {/* Scanning placeholder */}
      {!loading && isRunning && opportunities.length === 0 && (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <div>
            <p className="font-medium text-foreground">Scanning exchanges…</p>
            <p className="text-sm text-muted-foreground mt-1">Analysing ~140 large-cap stocks. Takes 2–3 minutes.</p>
          </div>
        </div>
      )}

      {/* No results */}
      {!loading && !isRunning && opportunities.length === 0 && (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-accent">
            <TrendingUp className="h-8 w-8 text-muted-foreground" />
          </div>
          <div>
            <p className="font-medium text-foreground">No scan results yet</p>
            <p className="text-sm text-muted-foreground mt-1">{results?.message ?? 'Click "Run Scan Now" to scan all major exchange stocks.'}</p>
          </div>
          <button
            onClick={handleTrigger}
            className="flex items-center gap-2 rounded-lg bg-primary text-primary-foreground px-5 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            <Zap className="h-4 w-4" />
            Run First Scan
          </button>
        </div>
      )}

      {/* Filters + sort */}
      {!loading && filtered.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-1">
            {sectors.map(s => (
              <button
                key={s}
                onClick={() => setSectorFilter(s)}
                className={cn(
                  'rounded-full px-2.5 py-1 text-xs font-medium transition-colors border',
                  sectorFilter === s
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-card text-muted-foreground border-border hover:bg-accent'
                )}
              >
                {s}
              </button>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Sort:</span>
            {([
              ['score',      'Score'],
              ['ev_ebitda',  'EV/EBITDA'],
              ['roic',       'ROIC'],
              ['rev_growth', 'Growth'],
              ['market_cap', 'Mkt Cap'],
            ] as [SortKey, string][]).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setSortKey(key)}
                className={cn(
                  'rounded px-2 py-1 text-xs font-medium transition-colors',
                  sortKey === key ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Results grid */}
      {!loading && filtered.length > 0 && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filtered.map((stock, i) => (
              <OpportunityCard key={stock.ticker} stock={stock} rank={i + 1} />
            ))}
          </div>
          <p className="text-center text-xs text-muted-foreground pb-2">
            Scores are algorithmic — not financial advice. Always do your own research.
          </p>
        </>
      )}
    </div>
  )
}
