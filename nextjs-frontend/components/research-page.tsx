'use client'

import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line,
} from 'recharts'
import {
  Search,
  TrendingUp,
  TrendingDown,
  Shield,
  BarChart3,
  Building2,
  Globe,
  Brain,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Newspaper,
  CalendarDays,
} from 'lucide-react'
import {
  SectionHeader,
  StatusBadge,
  RatingBadge,
  ProgressRing,
  DataRow,
  formatCurrency,
} from '@/components/ui-components'
import { fetchResearch, type ResearchData, type ValuationResult, type ScoreData, type InvestmentThesis } from '@/lib/api'
import { addToWatchlist } from '@/lib/watchlist-store'
import { cn } from '@/lib/utils'

// ── Helpers ───────────────────────────────────────────────────────────────────

const MODEL_LABELS: Record<string, string> = {
  dcf:       'DCF (Discounted Cash Flow)',
  pe:        'P/E Relative',
  ev_ebitda: 'EV/EBITDA',
  ev_sales:  'EV/Sales',
  pb:        'Price / Book',
  pcf:       'Price / Cash Flow',
  ddm:       'Dividend Discount (DDM)',
  pffo:      'Price / FFO (REIT)',
  paffo:     'Price / AFFO (REIT)',
}

function ratingFromValuation(rating: string): 'Hold' | 'Buy' | 'Sell' {
  const r = rating.toLowerCase()
  if (r.includes('under')) return 'Buy'
  if (r.includes('over'))  return 'Sell'
  return 'Hold'
}

function fmt(v: number | null | undefined, decimals = 2, suffix = ''): string {
  if (v == null) return '—'
  return `${v.toFixed(decimals)}${suffix}`
}

function relativeTime(iso: string): string {
  if (!iso) return ''
  const diffMs   = Date.now() - new Date(iso).getTime()
  const diffMins = Math.floor(diffMs / 60_000)
  if (diffMins < 60)  return `${diffMins}m ago`
  const diffHrs  = Math.floor(diffMins / 60)
  if (diffHrs  < 24)  return `${diffHrs}h ago`
  return `${Math.floor(diffHrs / 24)}d ago`
}

// ── Component ─────────────────────────────────────────────────────────────────

type Tab = 'valuation' | 'scores' | 'financials' | 'analyst' | 'news'

export function ResearchPage() {
  const [searchQuery,    setSearchQuery]    = useState('')
  const [activeTab,      setActiveTab]      = useState<Tab>('valuation')
  const [searching,      setSearching]      = useState(false)
  const [searchedTicker, setSearchedTicker] = useState<string | null>(null)
  const [research,       setResearch]       = useState<ResearchData | null>(null)
  const [addedMsg,       setAddedMsg]       = useState<string | null>(null)

  async function runSearch(query: string) {
    const ticker = query.trim().toUpperCase()
    if (!ticker) return

    setSearching(true)
    setSearchedTicker(ticker)
    setResearch(null)
    setActiveTab('valuation')

    try {
      const data = await fetchResearch(ticker)
      setResearch(data)
    } catch {
      setResearch(null)
    } finally {
      setSearching(false)
    }
  }

  function addCurrentToWatchlist() {
    if (!searchedTicker) return
    const price  = research?.price  ?? 0
    const pct    = research?.change_pct ?? 0
    const val    = research?.valuation
    const scores = research?.scores
    const fv     = val?.fair_value_base ?? 0
    const upside = fv > 0 && price > 0 ? Math.round((fv - price) / price * 100) : 0
    const rating = scores?.rating ?? (val ? ratingFromValuation(val.valuation_rating) : 'Hold / Watchlist')

    const added = addToWatchlist({
      symbol:         searchedTicker,
      name:           research?.company_name ?? searchedTicker,
      sector:         val?.sector ?? null,
      price,
      change:         +(price - price / (1 + pct / 100)).toFixed(2),
      changePercent:  pct,
      fairValue:      fv,
      buyBelow:       val?.fair_value_low ?? null,
      rating,
      upside,
      safetyScore:    scores?.safety_score ?? Math.round(val?.overall_confidence ?? 50),
      sparkline:      Array(7).fill(price),
      finalScore:     scores?.final_score     ?? null,
      qualityScore:   scores?.quality_score   ?? null,
      growthScore:    scores?.growth_score    ?? null,
      valuationScore: scores?.valuation_score ?? null,
      confidence:     scores?.confidence      ?? null,
    })

    setAddedMsg(added ? `${searchedTicker} added to watchlist` : `${searchedTicker} already on watchlist`)
    setTimeout(() => setAddedMsg(null), 3000)
  }

  const price     = research?.price      ?? null
  const changePct = research?.change_pct ?? 0

  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Research</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Search any ticker to run a full valuation analysis
        </p>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        <input
          type="text"
          placeholder="Enter ticker (e.g. AAPL, MSFT, KO) and press Enter…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
          onKeyDown={(e) => { if (e.key === 'Enter') runSearch(searchQuery) }}
          className="w-full rounded-xl border border-border bg-card pl-12 pr-28 py-4 text-base text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
        />
        <button
          onClick={() => runSearch(searchQuery)}
          disabled={searching || !searchQuery}
          className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg bg-primary px-4 py-1.5 text-xs font-medium text-primary-foreground disabled:opacity-40 transition-colors"
        >
          {searching ? 'Loading…' : 'Analyse'}
        </button>
      </div>

      {/* Empty state */}
      {!searchedTicker && (
        <div className="rounded-xl border border-dashed border-border bg-card/50 p-12 text-center">
          <BarChart3 className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm font-medium text-foreground">No ticker selected</p>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
            Enter any ticker above to run a live valuation using the full 9-model engine —
            DCF, P/E, EV/EBITDA, DDM, and sector-specific models.
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {['AAPL', 'MSFT', 'KO', 'O', 'GOOG', 'JNJ'].map((t) => (
              <button
                key={t}
                onClick={() => { setSearchQuery(t); runSearch(t) }}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-accent hover:bg-accent/70 text-foreground transition-colors"
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading state */}
      {searching && (
        <div className="rounded-xl border border-border bg-card p-10 shadow-sm flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm font-medium text-foreground">
            Analysing {searchedTicker}…
          </p>
          <p className="text-xs text-muted-foreground">
            Running valuation engine + fetching fundamentals, analyst ratings, and news.
            First run may take up to 30 s — data is cached afterward.
          </p>
        </div>
      )}

      {/* Results */}
      {!searching && searchedTicker && (
        <>
          {/* Company Header */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-accent text-lg font-bold text-foreground">
                  {searchedTicker.slice(0, 2)}
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-xl font-semibold text-foreground">{searchedTicker}</h2>
                    {research?.valuation && (
                      <RatingBadge rating={ratingFromValuation(research.valuation.valuation_rating)} />
                    )}
                  </div>
                  {research?.company_name && (
                    <p className="text-sm font-medium text-foreground/70">{research.company_name}</p>
                  )}
                  <p className="text-sm text-muted-foreground">
                    {research?.valuation
                      ? `${research.valuation.sector} · ${research.valuation.valuation_rating}`
                      : research
                        ? 'Valuation data unavailable'
                        : 'Analysis failed — check API connection'
                    }
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-6">
                {/* Fair value */}
                {research?.valuation && (
                  <div className="text-right hidden lg:block">
                    <p className="text-xs text-muted-foreground">Fair Value</p>
                    <p className="text-sm font-semibold text-foreground">
                      {formatCurrency(research.valuation.fair_value_base)}
                    </p>
                    <p className={cn(
                      'text-xs font-medium',
                      research.valuation.upside_pct >= 0 ? 'text-success' : 'text-destructive'
                    )}>
                      {research.valuation.upside_pct >= 0 ? '+' : ''}
                      {(research.valuation.upside_pct * 100).toFixed(2)}% upside
                    </p>
                  </div>
                )}

                {/* Live price */}
                {price != null && (
                  <div>
                    <p className="text-2xl font-semibold text-foreground">{formatCurrency(price)}</p>
                    <div className="flex items-center gap-1">
                      {changePct >= 0
                        ? <TrendingUp   className="h-3 w-3 text-success" />
                        : <TrendingDown className="h-3 w-3 text-destructive" />
                      }
                      <span className={cn('text-xs font-medium', changePct >= 0 ? 'text-success' : 'text-destructive')}>
                        {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}% today
                      </span>
                    </div>
                  </div>
                )}

                <div className="hidden lg:flex flex-col items-end gap-1">
                  <button
                    onClick={addCurrentToWatchlist}
                    disabled={!price}
                    className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-40 transition-colors"
                  >
                    Add to Watchlist
                  </button>
                  {addedMsg && <p className="text-xs text-muted-foreground">{addedMsg}</p>}
                </div>
              </div>
            </div>

            {/* Mobile Add to Watchlist — shown below price on small screens */}
            <div className="flex items-center gap-2 mt-3 lg:hidden">
              <button
                onClick={addCurrentToWatchlist}
                disabled={!price}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-40 transition-colors"
              >
                Add to Watchlist
              </button>
              {addedMsg && <p className="text-xs text-muted-foreground">{addedMsg}</p>}
            </div>

            {/* Tab navigation */}
            {research && (
              <div className="mt-4 flex gap-1 overflow-x-auto hide-scrollbar border-t border-border pt-4">
                {([
                  ['valuation', 'Valuation'],
                  ['scores',    'Scores'],
                  ['financials', 'Financials'],
                  ['analyst',   'Analyst'],
                  ['news',      'News'],
                ] as [Tab, string][]).map(([tab, label]) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={cn(
                      'px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap',
                      activeTab === tab
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent'
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* No data state */}
          {!research && !searching && (
            <div className="rounded-xl border border-border bg-card p-8 shadow-sm text-center">
              <AlertTriangle className="h-10 w-10 text-gold-foreground mx-auto mb-3" />
              <p className="text-sm font-medium text-foreground">
                Analysis unavailable for {searchedTicker}
              </p>
              <p className="text-xs text-muted-foreground mt-1 max-w-xs mx-auto">
                The API may be offline or insufficient data exists for this ticker.
                Ensure the backend is running at localhost:8000.
              </p>
            </div>
          )}

          {/* Tab content */}
          {research && activeTab === 'valuation' && (
            <ValuationTab research={research} />
          )}
          {research && activeTab === 'scores' && (
            <ScoresTab research={research} />
          )}
          {research && activeTab === 'financials' && (
            <FinancialsTab research={research} />
          )}
          {research && activeTab === 'analyst' && (
            <AnalystTab research={research} />
          )}
          {research && activeTab === 'news' && (
            <NewsTab research={research} />
          )}
        </>
      )}
    </div>
  )
}

// ── Valuation Tab ─────────────────────────────────────────────────────────────

function ValuationTab({ research }: { research: ResearchData }) {
  const val = research.valuation
  if (!val) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
        <p className="text-sm text-muted-foreground">
          Valuation engine returned no result for {research.ticker}.
          This can happen if fundamental data is unavailable.
        </p>
      </div>
    )
  }

  const upside      = val.upside_pct * 100
  const isUp        = upside >= 0
  const ratingColor = val.valuation_rating.toLowerCase().includes('under')
    ? 'text-success border-success/30 bg-success/10'
    : val.valuation_rating.toLowerCase().includes('over')
      ? 'text-destructive border-destructive/30 bg-destructive/10'
      : 'text-gold-foreground border-gold/30 bg-gold/10'

  const modelEntries = Object.entries(val.models_run).filter(([, m]) => m.fair_value != null)
  const price        = research.price ?? 0

  return (
    <div className="space-y-4">
      {/* Fair value range */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <SectionHeader
          title="Blended Fair Value"
          action={
            <span className={cn('text-xs font-medium px-2 py-1 rounded-md border', ratingColor)}>
              {val.valuation_rating}
            </span>
          }
        />
        <div className="mt-4 grid grid-cols-3 gap-3 text-center">
          <div className="rounded-lg bg-destructive/5 border border-destructive/20 p-3">
            <p className="text-xs text-muted-foreground">Bear / Low</p>
            <p className="text-lg font-semibold text-foreground">{formatCurrency(val.fair_value_low)}</p>
          </div>
          <div className="rounded-lg bg-primary/5 border border-primary/30 p-4">
            <p className="text-xs text-muted-foreground">Base (Blended)</p>
            <p className="text-xl font-bold text-foreground">{formatCurrency(val.fair_value_base)}</p>
            <p className={cn('text-xs font-medium mt-1', isUp ? 'text-success' : 'text-destructive')}>
              {isUp ? '+' : ''}{upside.toFixed(2)}% from current
            </p>
          </div>
          <div className="rounded-lg bg-success/5 border border-success/20 p-3">
            <p className="text-xs text-muted-foreground">Bull / High</p>
            <p className="text-lg font-semibold text-foreground">{formatCurrency(val.fair_value_high)}</p>
          </div>
        </div>

        {price > 0 && (
          <div className="mt-4">
            <div className="flex justify-between text-xs text-muted-foreground mb-1">
              <span>Current: {formatCurrency(price)}</span>
              <span>Fair Value: {formatCurrency(val.fair_value_base)}</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full', isUp ? 'bg-success' : 'bg-destructive')}
                style={{ width: `${Math.min((price / val.fair_value_base) * 100, 110)}%` }}
              />
            </div>
          </div>
        )}

        <div className="mt-4 pt-4 border-t border-border grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-muted-foreground">Sector</p>
            <p className="text-sm font-medium text-foreground mt-0.5">{val.sector || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Model Confidence</p>
            <div className="flex items-center gap-2 mt-0.5">
              <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full" style={{ width: `${val.overall_confidence}%` }} />
              </div>
              <span className="text-sm font-medium text-foreground">{val.overall_confidence.toFixed(0)}%</span>
            </div>
          </div>
        </div>
        {val.confidence_explanation && (
          <p className="mt-3 pt-3 border-t border-border text-xs text-muted-foreground leading-relaxed">
            {val.confidence_explanation}
          </p>
        )}
      </div>

      {/* Models breakdown */}
      {modelEntries.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader title="Models Used" />
          <p className="mt-1 text-xs text-muted-foreground">{val.bucket} bucket</p>
          <div className="mt-3 divide-y divide-border">
            {modelEntries.map(([key, model]) => (
              <div key={key} className="flex items-center justify-between py-2.5">
                <div>
                  <p className="text-sm font-medium text-foreground">{MODEL_LABELS[key] ?? key.toUpperCase()}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <div className="w-16 h-1 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-primary rounded-full" style={{ width: `${model.confidence}%` }} />
                    </div>
                    <p className="text-xs text-muted-foreground">{model.confidence.toFixed(0)}% confidence</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-foreground">{formatCurrency(model.fair_value!)}</p>
                  {price > 0 && (
                    <p className={cn('text-xs font-medium', model.fair_value! > price ? 'text-success' : 'text-destructive')}>
                      {model.fair_value! > price ? '+' : ''}
                      {((model.fair_value! - price) / price * 100).toFixed(2)}%
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Market Consensus — analyst price targets shown separately, not blended */}
      {val.analyst_consensus?.has_data && (
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <SectionHeader title="Market Consensus" />
            {(val.analyst_consensus.analyst_count ?? 0) > 0 && (
              <span className="text-xs text-muted-foreground">
                {val.analyst_consensus.analyst_count} analysts
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Analyst price targets — reference only, not blended into the fair value above
          </p>

          {/* PT range: low / median / high */}
          <div className="mt-3 grid grid-cols-3 gap-2">
            <div className="rounded-lg bg-muted/30 p-3 text-center">
              <p className="text-xs text-muted-foreground mb-1">Low Target</p>
              <p className="text-sm font-semibold text-foreground">
                {val.analyst_consensus.target_low != null
                  ? formatCurrency(val.analyst_consensus.target_low)
                  : '—'}
              </p>
            </div>
            <div className="rounded-lg bg-primary/10 border border-primary/20 p-3 text-center">
              <p className="text-xs text-muted-foreground mb-1">Median Target</p>
              <p className="text-base font-bold text-foreground">
                {formatCurrency(
                  (val.analyst_consensus.target_median ?? val.analyst_consensus.target_consensus) ?? 0
                )}
              </p>
            </div>
            <div className="rounded-lg bg-muted/30 p-3 text-center">
              <p className="text-xs text-muted-foreground mb-1">High Target</p>
              <p className="text-sm font-semibold text-foreground">
                {val.analyst_consensus.target_high != null
                  ? formatCurrency(val.analyst_consensus.target_high)
                  : '—'}
              </p>
            </div>
          </div>

          {/* Street vs our models comparison */}
          <div className="mt-3 flex items-center justify-between rounded-lg bg-muted/20 px-3 py-2">
            <div className="text-sm">
              <span className="text-muted-foreground">Street implies </span>
              <span className={cn(
                'font-semibold',
                (val.analyst_consensus.pt_upside_pct ?? 0) > 0 ? 'text-success' : 'text-destructive'
              )}>
                {val.analyst_consensus.pt_upside_pct != null
                  ? `${val.analyst_consensus.pt_upside_pct > 0 ? '+' : ''}${(val.analyst_consensus.pt_upside_pct * 100).toFixed(1)}%`
                  : '—'}
              </span>
              <span className="text-muted-foreground"> from current</span>
            </div>
            <div className="text-xs text-muted-foreground">
              Our models:{' '}
              <span className={cn(
                'font-medium',
                (val.upside_pct ?? 0) > 0 ? 'text-success' : 'text-destructive'
              )}>
                {val.upside_pct != null
                  ? `${val.upside_pct > 0 ? '+' : ''}${(val.upside_pct * 100).toFixed(1)}%`
                  : '—'}
              </span>
            </div>
          </div>

          {/* Buy / Hold / Sell from analyst_summary if available */}
          {research.analyst_summary && research.analyst_summary.total > 0 && (
            <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
              <span className="text-success font-medium">
                Buy {research.analyst_summary.buy}
              </span>
              <span>·</span>
              <span className="text-gold-foreground font-medium">
                Hold {research.analyst_summary.hold}
              </span>
              <span>·</span>
              <span className="text-destructive font-medium">
                Sell {research.analyst_summary.sell}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Warnings */}
      {val.warnings.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader title="Warnings & Caveats" />
          <div className="mt-3 space-y-2">
            {val.warnings.map((w, i) => (
              <div key={i} className="flex items-start gap-2 rounded-lg bg-gold/5 border border-gold/20 p-3">
                <AlertTriangle className="h-4 w-4 text-gold-foreground mt-0.5 shrink-0" />
                <p className="text-sm text-foreground">{w}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {val.warnings.length === 0 && (
        <div className="flex items-center gap-2 rounded-xl border border-success/20 bg-success/5 px-4 py-3">
          <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
          <p className="text-sm text-foreground">
            All {modelEntries.length} model{modelEntries.length !== 1 ? 's' : ''} completed without warnings.
          </p>
        </div>
      )}

      {/* Key ratios alongside valuation */}
      {research.ratios && (
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader title="Key Ratios" />
          <div className="mt-3 divide-y divide-border">
            <DataRow label="P/E Ratio"       value={fmt(research.ratios.pe_ratio,      1, 'x')} />
            <DataRow label="EV/EBITDA"        value={fmt(research.ratios.ev_ebitda,     1, 'x')} />
            <DataRow label="P/S Ratio"        value={fmt(research.ratios.ps_ratio,      1, 'x')} />
            <DataRow label="P/B Ratio"        value={fmt(research.ratios.pb_ratio,      1, 'x')} />
            <DataRow label="Dividend Yield"   value={fmt(research.ratios.dividend_yield,2, '%')} />
            <DataRow label="Beta"             value={fmt(research.ratios.beta,          2)} />
            <DataRow label="FCF / Share"      value={research.ratios.fcf_per_share != null ? formatCurrency(research.ratios.fcf_per_share) : '—'} />
          </div>
        </div>
      )}
    </div>
  )
}

// ── Scores Tab ────────────────────────────────────────────────────────────────

// All four sub-scores use the same direction: higher = better
function scoreColor(score: number | null): string {
  if (score == null) return 'text-muted-foreground'
  if (score >= 75)  return 'text-success'
  if (score >= 55)  return 'text-gold-foreground'
  if (score >= 40)  return 'text-orange-400'
  return 'text-destructive'
}

function scoreBg(score: number | null): string {
  if (score == null) return 'bg-muted/30 border-border'
  if (score >= 75)  return 'bg-success/5 border-success/20'
  if (score >= 55)  return 'bg-gold/5 border-gold/20'
  if (score >= 40)  return 'bg-orange-500/5 border-orange-500/20'
  return 'bg-destructive/5 border-destructive/20'
}

function scoreLabel(score: number | null): string {
  if (score == null) return 'No data'
  if (score >= 80)  return 'Excellent'
  if (score >= 65)  return 'Good'
  if (score >= 50)  return 'Average'
  if (score >= 35)  return 'Below average'
  return 'Weak'
}

// Safety-specific labels (same colour direction but distinct wording)
function safetyLabel(score: number | null): string {
  if (score == null) return 'No data'
  if (score >= 80)  return 'Low Risk / High Safety'
  if (score >= 60)  return 'Moderate Safety'
  if (score >= 40)  return 'Elevated Risk'
  return 'High Risk'
}

function ratingBadgeStyle(rating: string): string {
  if (rating === 'Strong Buy')      return 'bg-success/10 text-success border-success/30'
  if (rating === 'Buy')             return 'bg-success/5 text-success border-success/20'
  if (rating === 'Accumulate')      return 'bg-primary/10 text-primary border-primary/30'
  if (rating === 'Hold / Watchlist') return 'bg-gold/10 text-gold-foreground border-gold/30'
  if (rating === 'Reduce')          return 'bg-orange-500/10 text-orange-400 border-orange-500/30'
  if (rating === 'Sell')            return 'bg-destructive/10 text-destructive border-destructive/30'
  if (rating === 'Strong Sell')     return 'bg-destructive/15 text-destructive border-destructive/40'
  return 'bg-muted text-muted-foreground border-border'
}

function valuationStatusStyle(status: string): string {
  if (status === 'Deeply Undervalued') return 'bg-success/10 text-success border-success/30'
  if (status === 'Undervalued')        return 'bg-success/5 text-success border-success/20'
  if (status === 'Fairly Valued')      return 'bg-gold/10 text-gold-foreground border-gold/30'
  if (status === 'Overvalued')         return 'bg-orange-500/10 text-orange-400 border-orange-500/30'
  if (status === 'Severely Overvalued') return 'bg-destructive/10 text-destructive border-destructive/30'
  return 'bg-muted text-muted-foreground border-border'
}

const SCORE_CARD_META = [
  {
    key:         'quality_score'   as keyof ScoreData,
    label:       'Quality',
    description: 'ROIC, ROE, operating margin, net margin, FCF generation',
    isSafety:    false,
  },
  {
    key:         'valuation_score' as keyof ScoreData,
    label:       'Valuation',
    description: 'P/E, EV/EBITDA, P/S, P/B, upside to fair value',
    isSafety:    false,
  },
  {
    key:         'growth_score'    as keyof ScoreData,
    label:       'Growth',
    description: 'Revenue growth, EPS growth, free cash flow CAGR',
    isSafety:    false,
  },
  {
    key:         'safety_score'    as keyof ScoreData,
    label:       'Safety',
    description: 'Business/financial risk: leverage, beta, drawdown, FCF',
    isSafety:    true,
  },
]

function ScoresTab({ research }: { research: ResearchData }) {
  const scores = research.scores
  const thesis = research.investment_thesis

  if (!scores) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
        <Brain className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">
          Scoring data unavailable for {research.ticker}.
          This can happen if fundamental data is missing or the API is slow.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 4 Score Cards — all use same colour direction (higher = better) */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {SCORE_CARD_META.map(({ key, label, description, isSafety }) => {
          const raw   = scores[key] as number | null
          const color = scoreColor(raw)
          const bg    = scoreBg(raw)
          const interp = isSafety ? safetyLabel(raw) : scoreLabel(raw)

          return (
            <div key={String(key)} className={cn('rounded-xl border p-4 shadow-sm', bg)}>
              <p className="text-xs text-muted-foreground font-medium">{label}</p>
              <p className={cn('text-3xl font-bold mt-1', color)}>
                {raw != null ? Math.round(raw) : '—'}
              </p>
              <p className={cn('text-xs font-medium mt-0.5', color)}>{interp}</p>
              <p className="text-xs text-muted-foreground mt-2 leading-snug">{description}</p>
            </div>
          )
        })}
      </div>

      {/* Final Score + Rating + Valuation Status */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <p className="text-xs text-muted-foreground">Final Composite Score</p>
            <div className="flex items-baseline gap-3 mt-1">
              <p className={cn('text-5xl font-bold', scoreColor(scores.final_score))}>
                {scores.final_score != null ? Math.round(scores.final_score) : '—'}
              </p>
              <p className="text-lg text-muted-foreground">/100</p>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Quality 30% · Valuation 30% · Growth 20% · Safety 15% · Confidence 5%
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <span className={cn('px-4 py-2 rounded-xl border text-sm font-semibold', ratingBadgeStyle(scores.rating))}>
              {scores.rating}
            </span>
            {scores.valuation_status && scores.valuation_status !== 'Unknown' && (
              <span className={cn('px-3 py-1 rounded-lg border text-xs font-medium', valuationStatusStyle(scores.valuation_status))}>
                {scores.valuation_status}
              </span>
            )}
            {scores.confidence != null && (
              <div className="flex items-center gap-2">
                <div className="w-24 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full" style={{ width: `${scores.confidence}%` }} />
                </div>
                <span className="text-xs text-muted-foreground">{Math.round(scores.confidence)}% confidence</span>
              </div>
            )}
          </div>
        </div>

        {/* Explanation sentence */}
        {scores.rating_explanation && (
          <p className="mt-4 text-sm text-muted-foreground leading-relaxed border-t border-border pt-4">
            {scores.rating_explanation}
          </p>
        )}

        {/* Score bar breakdown + qualitative labels */}
        <div className="mt-4 pt-4 border-t border-border space-y-2.5">
          {[
            { label: 'Quality',   score: scores.quality_score,   weight: 30, qualifier: scores.score_qualifiers?.quality },
            { label: 'Valuation', score: scores.valuation_score, weight: 30, qualifier: scores.score_qualifiers?.valuation },
            { label: 'Growth',    score: scores.growth_score,    weight: 20, qualifier: scores.score_qualifiers?.growth },
            { label: 'Safety',    score: scores.safety_score,    weight: 15, qualifier: scores.score_qualifiers?.safety },
          ].map(({ label, score, weight, qualifier }) => (
            <div key={label}>
              <div className="flex justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">{label} <span className="opacity-50">({weight}%)</span></span>
                  {qualifier && (
                    <span className={cn('text-[10px] font-medium', scoreColor(score))}>{qualifier}</span>
                  )}
                </div>
                <span className={cn('text-xs font-medium', scoreColor(score))}>
                  {score != null ? Math.round(score) : '—'}
                </span>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all',
                    score == null            ? 'bg-muted-foreground/30' :
                    score >= 75              ? 'bg-success' :
                    score >= 55              ? 'bg-gold' :
                    score >= 40              ? 'bg-orange-400' :
                                               'bg-destructive'
                  )}
                  style={{ width: score != null ? `${score}%` : '100%' }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Investment Thesis */}
      {thesis && (
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader title="Investment Thesis" />
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div className="rounded-lg bg-success/5 border border-success/20 p-4">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="h-4 w-4 text-success shrink-0" />
                <p className="text-sm font-semibold text-success">Bull Case</p>
              </div>
              <ul className="space-y-2">
                {thesis.bull.map((pt, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-foreground leading-snug">
                    <span className="text-success mt-0.5 shrink-0">+</span>{pt}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-lg bg-destructive/5 border border-destructive/20 p-4">
              <div className="flex items-center gap-2 mb-3">
                <TrendingDown className="h-4 w-4 text-destructive shrink-0" />
                <p className="text-sm font-semibold text-destructive">Bear Case</p>
              </div>
              <ul className="space-y-2">
                {thesis.bear.map((pt, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-foreground leading-snug">
                    <span className="text-destructive mt-0.5 shrink-0">−</span>{pt}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-lg bg-primary/5 border border-primary/20 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="h-4 w-4 text-primary shrink-0" />
                <p className="text-sm font-semibold text-foreground">Base Case</p>
              </div>
              <ul className="space-y-2">
                {thesis.base.map((pt, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-foreground leading-snug">
                    <span className="text-primary mt-0.5 shrink-0">→</span>{pt}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-lg bg-gold/5 border border-gold/20 p-4">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-4 w-4 text-gold-foreground shrink-0" />
                <p className="text-sm font-semibold text-gold-foreground">Key Watch Items</p>
              </div>
              <ul className="space-y-2">
                {thesis.watch.map((pt, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-foreground leading-snug">
                    <span className="text-gold-foreground mt-0.5 shrink-0">!</span>{pt}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Financials Tab ────────────────────────────────────────────────────────────

function FinancialsTab({ research }: { research: ResearchData }) {
  const series = research.income_series ?? []

  if (series.length === 0 && !research.margins) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
        <p className="text-sm text-muted-foreground">
          Financial statement data unavailable for {research.ticker}.
          FMP API key may be required for this ticker.
        </p>
      </div>
    )
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Revenue chart */}
      {series.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader title="Revenue (USD Billions)" />
          <div className="mt-4 h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={series}>
                <XAxis dataKey="year" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }} />
                <YAxis hide />
                <Tooltip
                  contentStyle={{ backgroundColor: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }}
                  formatter={(v: number) => [`$${v}B`, 'Revenue']}
                />
                <Bar dataKey="revenue_b" fill="var(--primary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* EPS chart */}
      {series.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader title="Earnings Per Share ($)" />
          <div className="mt-4 h-44">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series}>
                <XAxis dataKey="year" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }} />
                <YAxis hide />
                <Tooltip
                  contentStyle={{ backgroundColor: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }}
                  formatter={(v: number) => [`$${v}`, 'EPS']}
                />
                <Line type="monotone" dataKey="eps" stroke="var(--success)" strokeWidth={2} dot={{ fill: 'var(--success)', strokeWidth: 0, r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Margins */}
      {research.margins && (
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader title="Margin Analysis (Latest Year)" />
          <div className="mt-4 space-y-4">
            {(Object.entries(research.margins) as [string, number | null][]).map(([key, value]) => (
              value != null && (
                <div key={key}>
                  <div className="flex justify-between mb-1">
                    <span className="text-xs text-muted-foreground capitalize">{key} Margin</span>
                    <span className="text-xs font-medium text-foreground">{value.toFixed(2)}%</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-primary rounded-full" style={{ width: `${Math.max(value, 0)}%` }} />
                  </div>
                </div>
              )
            ))}
          </div>
        </div>
      )}

      {/* Key ratios */}
      {research.ratios && (
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader title="Quality & Balance Sheet" />
          <div className="mt-3 divide-y divide-border">
            <DataRow label="ROIC"           value={fmt(research.ratios.roic,        1, '%')} />
            <DataRow label="ROE"            value={fmt(research.ratios.roe,         1, '%')} />
            <DataRow label="Debt / Equity"  value={fmt(research.ratios.debt_equity, 2, 'x')} />
            <DataRow label="FCF / Share"    value={research.ratios.fcf_per_share != null ? formatCurrency(research.ratios.fcf_per_share) : '—'} />
            <DataRow label="Dividend Yield" value={fmt(research.ratios.dividend_yield, 2, '%')} />
          </div>
        </div>
      )}
    </div>
  )
}

// ── Analyst Tab ───────────────────────────────────────────────────────────────

function AnalystTab({ research }: { research: ResearchData }) {
  const summary = research.analyst_summary
  const actions = research.analyst_actions ?? []
  const total   = summary.total

  if (total === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
        <p className="text-sm text-muted-foreground">
          No analyst ratings available for {research.ticker}. Benzinga coverage may be limited for this ticker.
        </p>
      </div>
    )
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Rating summary */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <SectionHeader title="Analyst Consensus" />
        <div className="mt-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="flex-1 h-3 rounded-full bg-muted overflow-hidden flex">
              <div className="bg-success transition-all" style={{ width: `${(summary.buy  / total) * 100}%` }} />
              <div className="bg-gold   transition-all" style={{ width: `${(summary.hold / total) * 100}%` }} />
              <div className="bg-destructive transition-all" style={{ width: `${(summary.sell / total) * 100}%` }} />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-2xl font-bold text-success">{summary.buy}</p>
              <p className="text-xs text-muted-foreground">Buy</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gold-foreground">{summary.hold}</p>
              <p className="text-xs text-muted-foreground">Hold</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-destructive">{summary.sell}</p>
              <p className="text-xs text-muted-foreground">Sell</p>
            </div>
          </div>
          {summary.avg_target != null && (
            <div className="mt-4 pt-4 border-t border-border">
              <DataRow label="Avg. Price Target" value={formatCurrency(summary.avg_target)} />
              {research.price != null && (
                <DataRow
                  label="Implied Upside"
                  value={`${((summary.avg_target - research.price) / research.price * 100).toFixed(2)}%`}
                  change={(summary.avg_target - research.price) / research.price * 100}
                />
              )}
            </div>
          )}
        </div>
      </div>

      {/* Recent actions list */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <SectionHeader title="Recent Actions" />
        <div className="mt-3 divide-y divide-border">
          {actions.slice(0, 8).map((a, i) => (
            <div key={i} className="py-2.5 flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-foreground truncate">{a.analyst_firm}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {a.action} → <span className={cn(
                    'font-medium',
                    a.bucket === 'buy'  ? 'text-success' :
                    a.bucket === 'sell' ? 'text-destructive' : 'text-gold-foreground'
                  )}>{a.rating}</span>
                  {a.rating_prior && ` (was ${a.rating_prior})`}
                </p>
              </div>
              <div className="text-right shrink-0">
                {a.price_target != null && (
                  <p className="text-xs font-medium text-foreground">{formatCurrency(a.price_target)}</p>
                )}
                <p className="text-xs text-muted-foreground">{relativeTime(a.published_at)}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Earnings upcoming */}
      {research.earnings.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm lg:col-span-2">
          <SectionHeader
            title="Upcoming Earnings"
            action={<CalendarDays className="h-4 w-4 text-muted-foreground" />}
          />
          <div className="mt-3 divide-y divide-border">
            {research.earnings.map((e, i) => (
              <div key={i} className="py-2.5 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">{e.date}</p>
                  <p className="text-xs text-muted-foreground capitalize">
                    {e.hour === 'amc' ? 'After Close' : e.hour === 'bmo' ? 'Before Open' : e.hour}
                  </p>
                </div>
                <div className="text-right text-xs text-muted-foreground space-y-0.5">
                  {e.eps_estimate != null && <p>EPS est. ${e.eps_estimate.toFixed(2)}</p>}
                  {e.revenue_est  != null && <p>Rev est. ${(e.revenue_est / 1e9).toFixed(2)}B</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── News Tab ──────────────────────────────────────────────────────────────────

function NewsTab({ research }: { research: ResearchData }) {
  const news = research.recent_news ?? []

  if (news.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
        <Newspaper className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">No recent news available for {research.ticker}.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {news.map((item, i) => (
        <div key={i} className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground leading-snug">{item.headline}</p>
              {item.summary && (
                <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed line-clamp-3">
                  {item.summary}
                </p>
              )}
            </div>
            <div className="text-right shrink-0">
              <p className="text-xs font-medium text-foreground">{item.source}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{relativeTime(item.published_at)}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
