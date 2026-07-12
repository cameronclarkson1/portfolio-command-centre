'use client'

import { useState } from 'react'
import { Clock, Star } from 'lucide-react'
import { SectionHeader, EventTypeBadge } from '@/components/ui-components'
import { upcomingEvents as mockUpcoming, earningsCalendar as mockEarnings } from '@/lib/mock-data'
import { type EarningsItem, type MacroEvent, type DividendEntry } from '@/lib/api'
import { cn } from '@/lib/utils'

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string): string {
  const d = new Date(iso + 'T12:00:00Z')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
}

// ── Portfolio tickers — used to flag events as "In Portfolio" ─────────────────

const PORTFOLIO_TICKERS = new Set([
  'AVGO', 'BABA', 'BAC', 'GOOG', 'JNJ', 'KO', 'MCD', 'META',
  'MO',   'MU',   'NEM', 'NVDA', 'O',   'SCHD', 'V', 'VOO', 'VZ', 'WFC',
])

// ── Types ─────────────────────────────────────────────────────────────────────

type FilterType = 'all' | 'earnings' | 'macro' | 'dividend'

interface EventRow {
  date:        string        // display: "Jul 15"
  isoDate:     string        // for sorting: "2026-07-15"
  type:        'earnings' | 'macro'
  ticker:      string | null
  description: string
  timing:      string
  inPortfolio: boolean
}

// ── Page component ─────────────────────────────────────────────────────────────

export function EventsPage({
  apiEarnings,
  apiMacro,
  apiDividends,
}: {
  apiEarnings?:  EarningsItem[]  | null
  apiMacro?:     MacroEvent[]    | null
  apiDividends?: DividendEntry[] | null
}) {
  const [filter, setFilter] = useState<FilterType>('all')

  // ── Earnings calendar detail table ────────────────────────────────────────
  const earningsCalendar = apiEarnings ?? mockEarnings.map(e => ({
    ticker:       e.symbol,
    name:         e.name,
    date:         e.date,
    hour:         e.time === 'AMC' ? 'amc' : 'bmo',
    eps_estimate: parseFloat(e.estimate.replace('$', '')) || null,
  }))

  // ── Unified events timeline (earnings + macro, sorted by date) ────────────
  const eventTimeline: EventRow[] = []

  if (apiEarnings && apiEarnings.length > 0) {
    apiEarnings.forEach(e => {
      eventTimeline.push({
        date:        fmtDate(e.date),
        isoDate:     e.date,
        type:        'earnings',
        ticker:      e.ticker,
        description: `${e.name} Earnings`,
        timing:      e.hour === 'amc' ? 'After Close' : 'Before Open',
        inPortfolio: PORTFOLIO_TICKERS.has(e.ticker),
      })
    })
  }

  if (apiMacro && apiMacro.length > 0) {
    apiMacro.forEach(m => {
      eventTimeline.push({
        date:        fmtDate(m.date),
        isoDate:     m.date,
        type:        'macro',
        ticker:      null,
        description: m.event,
        timing:      m.time,
        inPortfolio: false,
      })
    })
  }

  eventTimeline.sort((a, b) => a.isoDate.localeCompare(b.isoDate))

  // Fall back to mock data if the API returned nothing for both sources
  const displayTimeline: EventRow[] = eventTimeline.length > 0
    ? eventTimeline
    : mockUpcoming.map(e => ({ ...e, isoDate: '' }))

  // ── Macro sidebar list (first 8 macro events) ─────────────────────────────
  const macroSidebar = apiMacro
    ? apiMacro.slice(0, 8).map(m => ({
        date:       fmtDate(m.date),
        event:      m.event,
        time:       m.time,
        importance: m.importance,
      }))
    : []

  // ── Dividend table rows ───────────────────────────────────────────────────
  const dividendRows = apiDividends
    ? apiDividends.map(d => ({
        ticker:      d.ticker,
        name:        d.name,
        exDate:      d.ex_div_date ? fmtDate(d.ex_div_date) : '—',
        payDate:     d.pay_date    ? fmtDate(d.pay_date)    : '—',
        amount:      d.quarterly_div,
        yieldPct:    d.yield_pct ?? 0,
        inPortfolio: d.in_portfolio,
      }))
    : []

  // ── Summary counts for sidebar ────────────────────────────────────────────
  const portfolioEarnings  = displayTimeline.filter(e => e.type === 'earnings' && e.inPortfolio)
  const portfolioDividends = dividendRows.filter(d => d.inPortfolio)

  const filterTabs: { key: FilterType; label: string; count: number }[] = [
    { key: 'all',      label: 'All Events', count: displayTimeline.length + dividendRows.length },
    { key: 'earnings', label: 'Earnings',   count: earningsCalendar.length },
    { key: 'macro',    label: 'Macro',      count: macroSidebar.length },
    { key: 'dividend', label: 'Dividends',  count: dividendRows.length },
  ]

  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6 max-w-[1600px] mx-auto">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Events Calendar</h1>
        <p className="mt-1 text-sm text-muted-foreground">Earnings, macro events, and dividend dates</p>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        {filterTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              filter === tab.key
                ? 'bg-primary text-primary-foreground'
                : 'bg-card border border-border text-muted-foreground hover:text-foreground hover:bg-accent'
            )}
          >
            {tab.label}
            <span className={cn(
              'text-[10px] font-bold rounded-full px-1.5 py-0.5',
              filter === tab.key ? 'bg-white/20 text-white' : 'bg-muted text-muted-foreground'
            )}>
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Main grid */}
      <div className="grid gap-6 lg:grid-cols-3">

        {/* ── Left column: main content ── */}
        <div className="lg:col-span-2 space-y-6">

          {/* Upcoming events timeline */}
          {(filter === 'all' || filter === 'earnings' || filter === 'macro') && (
            <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
              <SectionHeader title="Upcoming Events" />
              <div className="mt-4 divide-y divide-border">
                {displayTimeline
                  .filter(e => filter === 'all' || e.type === filter)
                  .slice(0, 15)
                  .map((event, i) => (
                    <div key={i} className="flex items-center gap-4 py-3">
                      <div className="w-14 flex-shrink-0 text-center">
                        <p className="text-sm font-bold text-foreground">{event.date.split(' ')[1]}</p>
                        <p className="text-[10px] text-muted-foreground">{event.date.split(' ')[0]}</p>
                      </div>
                      <EventTypeBadge type={event.type} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground">
                          {event.ticker && <span className="font-bold">{event.ticker} — </span>}
                          {event.description}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <Clock className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                          <span className="text-xs text-muted-foreground">{event.timing}</span>
                          {event.inPortfolio && (
                            <span className="text-xs font-semibold text-primary">· In Portfolio</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                {displayTimeline.filter(e => filter === 'all' || e.type === filter).length === 0 && (
                  <p className="py-6 text-sm text-center text-muted-foreground">No upcoming events</p>
                )}
              </div>
            </div>
          )}

          {/* Earnings calendar table */}
          {(filter === 'all' || filter === 'earnings') && (
            <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
              <SectionHeader title="Earnings Detail" />
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="pb-2 text-left font-semibold text-muted-foreground uppercase tracking-wide">Company</th>
                      <th className="pb-2 text-left font-semibold text-muted-foreground uppercase tracking-wide">Date</th>
                      <th className="pb-2 text-left font-semibold text-muted-foreground uppercase tracking-wide">Timing</th>
                      <th className="pb-2 text-right font-semibold text-muted-foreground uppercase tracking-wide">EPS Est.</th>
                      <th className="pb-2 text-center font-semibold text-muted-foreground uppercase tracking-wide">Portfolio</th>
                    </tr>
                  </thead>
                  <tbody>
                    {earningsCalendar.map((e, i) => {
                      const isAmc     = e.hour === 'amc'
                      const dateLabel = e.date.includes('-') ? fmtDate(e.date) : e.date
                      const epsLabel  = e.eps_estimate != null ? `$${e.eps_estimate.toFixed(2)}` : '—'
                      return (
                        <tr key={i} className="border-b border-border last:border-0">
                          <td className="py-3">
                            <div className="flex items-center gap-2.5">
                              <div className="h-7 w-7 rounded-md bg-accent flex items-center justify-center text-[10px] font-bold text-foreground flex-shrink-0">
                                {e.ticker.slice(0, 2)}
                              </div>
                              <div>
                                <p className="font-semibold text-foreground">{e.ticker}</p>
                                <p className="text-muted-foreground">{e.name}</p>
                              </div>
                            </div>
                          </td>
                          <td className="py-3 font-medium text-foreground">{dateLabel}</td>
                          <td className="py-3">
                            <span className={cn(
                              'rounded-md px-1.5 py-0.5 text-[10px] font-semibold',
                              isAmc ? 'bg-[#7C3AED]/10 text-[#7C3AED]' : 'bg-[#2563EB]/10 text-[#2563EB]'
                            )}>
                              {isAmc ? 'After Close' : 'Before Open'}
                            </span>
                          </td>
                          <td className="py-3 text-right font-semibold text-foreground">{epsLabel}</td>
                          <td className="py-3 text-center">
                            {PORTFOLIO_TICKERS.has(e.ticker) && (
                              <Star className="h-3.5 w-3.5 text-primary fill-primary inline" />
                            )}
                          </td>
                        </tr>
                      )
                    })}
                    {earningsCalendar.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-6 text-center text-muted-foreground">No upcoming earnings</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Dividends table */}
          {(filter === 'all' || filter === 'dividend') && (
            <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
              <SectionHeader title="Upcoming Dividends" />
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="pb-2 text-left font-semibold text-muted-foreground uppercase tracking-wide">Company</th>
                      <th className="pb-2 text-right font-semibold text-muted-foreground uppercase tracking-wide">Amount</th>
                      <th className="pb-2 text-right font-semibold text-muted-foreground uppercase tracking-wide">Yield</th>
                      <th className="pb-2 text-right font-semibold text-muted-foreground uppercase tracking-wide">Ex-Date</th>
                      <th className="pb-2 text-right font-semibold text-muted-foreground uppercase tracking-wide">Pay Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dividendRows.map((d, i) => (
                      <tr key={i} className="border-b border-border last:border-0">
                        <td className="py-3">
                          <div className="flex items-center gap-2.5">
                            <div className="h-7 w-7 rounded-md bg-accent flex items-center justify-center text-[10px] font-bold text-foreground flex-shrink-0">
                              {d.ticker.slice(0, 2)}
                            </div>
                            <div>
                              <div className="flex items-center gap-1.5">
                                <p className="font-semibold text-foreground">{d.ticker}</p>
                                {d.inPortfolio && <Star className="h-3 w-3 text-primary fill-primary" />}
                              </div>
                              <p className="text-muted-foreground truncate max-w-[100px]">{d.name}</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 text-right font-semibold text-success">${d.amount.toFixed(2)}</td>
                        <td className="py-3 text-right text-muted-foreground">{d.yieldPct.toFixed(2)}%</td>
                        <td className="py-3 text-right font-medium text-foreground">{d.exDate}</td>
                        <td className="py-3 text-right text-muted-foreground">{d.payDate}</td>
                      </tr>
                    ))}
                    {dividendRows.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-6 text-center text-muted-foreground">
                          Loading dividends...
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* ── Right column: sidebar ── */}
        <div className="space-y-6">

          {/* This week snapshot */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="This Week" />
            <div className="mt-3 divide-y divide-border">
              {displayTimeline.slice(0, 4).map((e, i) => (
                <div key={i} className="flex items-start gap-2.5 py-2.5">
                  <EventTypeBadge type={e.type} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-foreground">
                      {e.ticker ? `${e.ticker} — ` : ''}{e.description}
                    </p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{e.date} · {e.timing}</p>
                  </div>
                </div>
              ))}
              {displayTimeline.length === 0 && (
                <p className="py-3 text-xs text-center text-muted-foreground">No upcoming events</p>
              )}
            </div>
          </div>

          {/* Key macro dates */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Key Macro Dates" />
            <div className="mt-3 divide-y divide-border">
              {macroSidebar.map((m, i) => (
                <div key={i} className="flex items-center justify-between py-2.5">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-foreground truncate">{m.event}</p>
                    <p className="text-[10px] text-muted-foreground">{m.time}</p>
                  </div>
                  <div className="text-right flex-shrink-0 ml-3">
                    <p className="text-xs font-semibold text-foreground">{m.date}</p>
                    <span className={cn(
                      'text-[9px] font-bold uppercase rounded px-1.5 py-0.5',
                      m.importance === 'high'
                        ? 'bg-destructive/10 text-destructive'
                        : 'bg-gold/10 text-gold'
                    )}>
                      {m.importance}
                    </span>
                  </div>
                </div>
              ))}
              {macroSidebar.length === 0 && (
                <p className="py-3 text-xs text-center text-muted-foreground">Loading macro calendar...</p>
              )}
            </div>
          </div>

          {/* Your portfolio summary */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Your Portfolio" />
            <div className="mt-3 space-y-2.5">
              <div className="rounded-lg bg-accent/50 p-3">
                <p className="text-xs font-medium text-muted-foreground">Earnings this month</p>
                <p className="mt-0.5">
                  <span className="text-2xl font-bold text-foreground">{portfolioEarnings.length}</span>
                  <span className="text-sm text-muted-foreground ml-1">positions reporting</span>
                </p>
              </div>
              <div className="rounded-lg bg-accent/50 p-3">
                <p className="text-xs font-medium text-muted-foreground">Dividends due</p>
                <p className="mt-0.5">
                  <span className="text-2xl font-bold text-foreground">{portfolioDividends.length}</span>
                  <span className="text-sm text-muted-foreground ml-1">payments coming</span>
                </p>
              </div>
              {portfolioEarnings.length > 0 && (
                <div className="rounded-lg bg-destructive/5 border border-destructive/20 p-3">
                  <p className="text-xs font-semibold text-destructive mb-1">Watch closely</p>
                  <p className="text-xs text-foreground">
                    {portfolioEarnings.map(e => e.ticker).join(', ')} reporting — expect elevated volatility
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
