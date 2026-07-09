'use client'

import { useState, useRef, useEffect } from 'react'
import {
  Search,
  Plus,
  X,
  Star,
  StarOff,
  TrendingUp,
  TrendingDown,
  ChevronDown,
  Loader2,
  RefreshCw,
  LayoutGrid,
  List,
  Bell,
  ChevronUp,
} from 'lucide-react'
import {
  SectionHeader,
  Sparkline,
  formatCurrency,
} from '@/components/ui-components'
import { watchlist as mockWatchlist } from '@/lib/mock-data'
import { fetchWatchlistPrices, fetchValuation, fetchWatchlistRefresh, fetchSparklines, type LivePriceData } from '@/lib/api'
import {
  type WatchlistItem,
  getStoredWatchlist,
  saveWatchlist,
  loadWatchlist,
} from '@/lib/watchlist-store'
import { cn } from '@/lib/utils'

// ── Helpers ───────────────────────────────────────────────────────────────────

function mergeWithLive(stock: WatchlistItem, live: LivePriceData[string]): WatchlistItem {
  if (!live?.price) return stock
  const changePercent = live.change_pct ?? stock.changePercent
  const price         = live.price
  const change        = +(price - price / (1 + changePercent / 100)).toFixed(2)
  return { ...stock, price, change, changePercent }
}

function buildInitialList(livePrices?: LivePriceData | null): WatchlistItem[] {
  return mockWatchlist.map((s) => mergeWithLive(s as WatchlistItem, livePrices?.[s.symbol] ?? null))
}

// Map 5-level score to colour class
function scoreColor(score: number | null | undefined): string {
  if (score == null) return 'text-muted-foreground'
  if (score >= 75)  return 'text-success'
  if (score >= 55)  return 'text-gold-foreground'
  if (score >= 40)  return 'text-orange-400'
  return 'text-destructive'
}

// Map 7-level rating to badge style
function ratingStyle(rating: string): string {
  if (rating === 'Strong Buy')       return 'bg-success/10 text-success border-success/30'
  if (rating === 'Buy')              return 'bg-success/5 text-success border-success/20'
  if (rating === 'Accumulate')       return 'bg-primary/10 text-primary border-primary/30'
  if (rating === 'Hold / Watchlist') return 'bg-gold/10 text-gold-foreground border-gold/30'
  if (rating === 'Hold')             return 'bg-gold/10 text-gold-foreground border-gold/30'
  if (rating === 'Reduce')           return 'bg-orange-500/10 text-orange-400 border-orange-500/30'
  if (rating === 'Sell')             return 'bg-destructive/10 text-destructive border-destructive/30'
  if (rating === 'Strong Sell')      return 'bg-destructive/15 text-destructive border-destructive/40'
  return 'bg-muted text-muted-foreground border-border'
}

// ── Constants ─────────────────────────────────────────────────────────────────

const POPULAR = ['TSLA', 'AAPL', 'GOOGL', 'AMZN', 'META', 'MSFT', 'NVDA', 'AMD']

const SECTOR_ORDER = [
  'Technology',
  'Communication Services',
  'Consumer Discretionary',
  'Consumer Staples',
  'Financials',
  'Healthcare',
  'Real Estate',
]

const sortOptions = [
  { value: 'change',      label: 'Price Change' },
  { value: 'upside',      label: 'Upside Potential' },
  { value: 'risk',        label: 'Safety Score' },
  { value: 'final_score', label: 'Final Score' },
  { value: 'confidence',  label: 'Confidence' },
  { value: 'alpha',       label: 'Alphabetical' },
]

const filterOptions = [
  { value: 'all',              label: 'All' },
  { value: 'Strong Buy',       label: 'Strong Buy' },
  { value: 'Buy',              label: 'Buy' },
  { value: 'Accumulate',       label: 'Accumulate' },
  { value: 'Hold / Watchlist', label: 'Hold' },
  { value: 'Reduce',           label: 'Reduce' },
  { value: 'Sell',             label: 'Sell' },
]

// ── Component ─────────────────────────────────────────────────────────────────

export function WatchlistPage({ livePrices }: { livePrices?: LivePriceData | null }) {
  // Always start with the full 33-stock list from mock-data so it's visible immediately.
  // The server load below will overlay saved scores and any user-added stocks on top.
  const [items, setItems]           = useState<WatchlistItem[]>(() => buildInitialList(livePrices))

  const [serverLoaded, setServerLoaded] = useState(false)

  // On mount: load from server (cross-device persistence)
  useEffect(() => {
    loadWatchlist().then((serverItems) => {
      if (serverItems.length > 0) setItems(serverItems)
      setServerLoaded(true)
    })
  }, [])
  const [searchQuery,    setSearchQuery]    = useState('')
  const [activeFilter,   setActiveFilter]   = useState('all')
  const [sortBy,         setSortBy]         = useState('change')
  const [groupBySector,  setGroupBySector]  = useState(true)
  const [favorites,      setFavorites]      = useState<string[]>(['AMD', 'COST'])
  const [showAdd,      setShowAdd]      = useState(false)
  const [addInput,     setAddInput]     = useState('')
  const [isAdding,          setIsAdding]          = useState(false)
  const [isRefreshing,      setIsRefreshing]      = useState(false)
  const [refreshingSymbols, setRefreshingSymbols] = useState<Set<string>>(new Set())
  const [refreshedCount,    setRefreshedCount]    = useState(0)
  const [addError,          setAddError]          = useState('')
  const [alertsOpen,        setAlertsOpen]        = useState(true)
  const inputRef = useRef<HTMLInputElement>(null)

  // Persist to localStorage/server whenever the list changes — but only after server has loaded,
  // so we don't overwrite the server's defaults with stale localStorage data on first render.
  useEffect(() => {
    if (!serverLoaded) return
    saveWatchlist(items)
  }, [items, serverLoaded])

  // On mount: refresh live prices for all items
  useEffect(() => {
    const symbols = items.map((s) => s.symbol)
    if (!symbols.length) return
    fetchWatchlistPrices(symbols).then((prices) => {
      if (!prices) return
      setItems((prev) => prev.map((s) => mergeWithLive(s, prices[s.symbol])))
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // On mount: load 7-day sparklines for all items
  useEffect(() => {
    const symbols = items.map((s) => s.symbol)
    if (!symbols.length) return
    fetchSparklines(symbols).then((sparklines) => {
      if (!sparklines) return
      setItems((prev) => prev.map((s) => {
        const data = sparklines[s.symbol]
        return data && data.length >= 2 ? { ...s, sparkline: data } : s
      }))
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Refresh all scores (progressive — each card updates as it finishes) ──────

  async function refreshAllScores() {
    if (isRefreshing || items.length === 0) return
    setIsRefreshing(true)
    setRefreshedCount(0)

    const symbols = items.map((s) => s.symbol)
    setRefreshingSymbols(new Set(symbols))

    const now   = new Date().toISOString()
    const queue = [...symbols]

    async function processOne(symbol: string) {
      try {
        const result    = await fetchWatchlistRefresh([symbol])
        const refreshed = result?.[0]

        setItems((prev) => prev.map((stock) => {
          if (stock.symbol !== symbol) return stock
          if (!refreshed || refreshed.error) {
            return { ...stock, dataError: refreshed?.error ?? 'timeout', lastUpdated: now }
          }
          const scores    = refreshed.scores
          const fairValue = refreshed.fair_value ?? stock.fairValue
          const buyBelow  = refreshed.buy_below  ?? stock.buyBelow ?? null
          const price     = refreshed.price      ?? stock.price
          const upsidePct = refreshed.upside_pct
          const upside    = upsidePct != null ? Math.round(upsidePct * 100) : stock.upside
          return {
            ...stock,
            price,
            changePercent:  refreshed.change_pct ?? stock.changePercent,
            change:         refreshed.price != null
              ? +(refreshed.price - refreshed.price / (1 + (refreshed.change_pct ?? 0) / 100)).toFixed(2)
              : stock.change,
            fairValue,
            buyBelow,
            upside,
            rating:         scores?.rating         ?? stock.rating,
            finalScore:     scores?.final_score     ?? null,
            qualityScore:   scores?.quality_score   ?? null,
            growthScore:    scores?.growth_score    ?? null,
            valuationScore: scores?.valuation_score ?? null,
            safetyScore:    scores?.safety_score    ?? null,
            confidence:     scores?.confidence      ?? null,
            dataError:      null,
            lastUpdated:    now,
          }
        }))
      } catch {
        setItems((prev) => prev.map((s) =>
          s.symbol === symbol ? { ...s, dataError: 'timeout', lastUpdated: now } : s
        ))
      } finally {
        setRefreshingSymbols((prev) => { const n = new Set(prev); n.delete(symbol); return n })
        setRefreshedCount((c) => c + 1)
      }
    }

    // Run up to 8 stocks in parallel — each worker picks the next from the queue
    async function worker() {
      while (queue.length > 0) {
        const symbol = queue.shift()
        if (symbol) await processOne(symbol)
      }
    }
    await Promise.allSettled(
      Array.from({ length: Math.min(8, symbols.length) }, worker)
    )

    setIsRefreshing(false)
    setRefreshingSymbols(new Set())
  }

  // ── Add security ──────────────────────────────────────────────────────────────

  async function addSecurity(rawSymbol: string) {
    const symbol = rawSymbol.trim().toUpperCase()
    if (!symbol) return
    if (items.some((s) => s.symbol === symbol)) {
      setAddError(`${symbol} is already on your watchlist`)
      return
    }

    setIsAdding(true)
    setAddError('')

    let price = 0, change = 0, changePercent = 0
    let fairValue = 0, rating = 'Hold / Watchlist', upside = 0, safetyScore = 50
    let name = symbol

    const [prices, valuation] = await Promise.allSettled([
      fetchWatchlistPrices([symbol]),
      fetchValuation(symbol),
    ])

    if (prices.status === 'fulfilled' && prices.value?.[symbol]) {
      const live = prices.value[symbol]
      price         = live.price
      changePercent = live.change_pct ?? 0
      change        = +(price - price / (1 + changePercent / 100)).toFixed(2)
    }

    if (valuation.status === 'fulfilled' && valuation.value) {
      const val = valuation.value
      fairValue   = val.fair_value_base
      upside      = Math.round(val.upside_pct * 100)
      safetyScore = Math.round(val.overall_confidence ?? 50)   // confidence as safety proxy until scores refresh
      const r = val.valuation_rating.toLowerCase()
      if (r.includes('under'))     rating = 'Buy'
      else if (r.includes('over')) rating = 'Hold / Watchlist'
      else                         rating = 'Hold / Watchlist'
    }

    setItems((prev) => [{
      symbol, name, price, change, changePercent, fairValue, rating, upside, safetyScore,
      sparkline: Array(7).fill(price || 0),
    }, ...prev])
    setAddInput('')
    setShowAdd(false)
    setIsAdding(false)
  }

  function removeSecurity(symbol: string) {
    setItems((prev) => prev.filter((s) => s.symbol !== symbol))
  }

  function toggleFavorite(symbol: string) {
    setFavorites((prev) =>
      prev.includes(symbol) ? prev.filter((s) => s !== symbol) : [...prev, symbol]
    )
  }

  function openAdd() {
    setShowAdd(true)
    setAddError('')
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  // ── Filter + sort ─────────────────────────────────────────────────────────────

  const filtered = items
    .filter((s) => {
      if (activeFilter === 'all') return true
      return s.rating === activeFilter
    })
    .filter((s) =>
      s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => {
      if (sortBy === 'change')      return b.changePercent - a.changePercent
      if (sortBy === 'upside')      return b.upside - a.upside
      if (sortBy === 'risk')        return (b.safetyScore ?? -1) - (a.safetyScore ?? -1)   // highest safety first
      if (sortBy === 'final_score') return (b.finalScore ?? -1) - (a.finalScore ?? -1)
      if (sortBy === 'confidence')  return (b.confidence ?? -1) - (a.confidence ?? -1)
      if (sortBy === 'alpha')       return a.symbol.localeCompare(b.symbol)
      return 0
    })

  const alreadyAdded = (symbol: string) => items.some((s) => s.symbol === symbol)

  // ── Card renderer ─────────────────────────────────────────────────────────────

  function renderCard(stock: WatchlistItem) {
    const hasScores = stock.finalScore != null
    const isLoading = refreshingSymbols.has(stock.symbol)
    return (
      <div
        key={stock.symbol}
        className={cn(
          'rounded-xl border border-border bg-card p-4 shadow-sm hover:shadow-md transition-all group',
          isLoading && 'opacity-60'
        )}
      >
        {/* Card header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-accent text-sm font-semibold text-foreground">
              {isLoading
                ? <Loader2 className="h-4 w-4 animate-spin text-primary" />
                : stock.symbol.slice(0, 2)
              }
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">{stock.symbol}</p>
              <p className="text-xs text-muted-foreground truncate max-w-[140px]">{stock.name}</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {stock.rating && (
              <span className={cn('text-[10px] font-semibold px-2 py-0.5 rounded-md border', ratingStyle(stock.rating))}>
                {stock.rating}
              </span>
            )}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button onClick={() => toggleFavorite(stock.symbol)}>
                {favorites.includes(stock.symbol)
                  ? <Star    className="h-4 w-4 text-gold fill-gold" />
                  : <StarOff className="h-4 w-4 text-muted-foreground hover:text-gold" />
                }
              </button>
              <button onClick={() => removeSecurity(stock.symbol)} title="Remove">
                <X className="h-4 w-4 text-muted-foreground hover:text-destructive" />
              </button>
            </div>
          </div>
        </div>

        {/* Price & change */}
        <div className="mt-4 flex items-end justify-between">
          <div>
            <p className="text-xl font-semibold text-foreground">
              {stock.price > 0 ? formatCurrency(stock.price) : '—'}
            </p>
            <div className="flex items-center gap-1 mt-0.5">
              {stock.change >= 0
                ? <TrendingUp   className="h-3 w-3 text-success" />
                : <TrendingDown className="h-3 w-3 text-destructive" />
              }
              <span className={cn('text-xs font-medium', stock.change >= 0 ? 'text-success' : 'text-destructive')}>
                {stock.price > 0
                  ? `${stock.change >= 0 ? '+' : ''}${formatCurrency(stock.change)} (${stock.changePercent.toFixed(2)}%)`
                  : 'Price unavailable'
                }
              </span>
            </div>
          </div>
          <Sparkline data={stock.sparkline} width={70} height={28} positive={stock.change >= 0} />
        </div>

        <div className="my-3 border-t border-border" />

        {/* Fair value + upside */}
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center">
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Fair Value</p>
            <p className="text-sm font-medium text-foreground mt-0.5">
              {stock.fairValue > 0 ? formatCurrency(stock.fairValue) : '—'}
            </p>
          </div>
          <div className="text-center">
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Upside</p>
            <p className={cn('text-sm font-medium mt-0.5', stock.upside >= 0 ? 'text-success' : 'text-destructive')}>
              {stock.fairValue > 0 ? `${stock.upside >= 0 ? '+' : ''}${stock.upside}%` : '—'}
            </p>
          </div>
          <div className="text-center">
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Safety</p>
            <p className={cn(
              'text-sm font-medium mt-0.5',
              (stock.safetyScore ?? 0) >= 75 ? 'text-success' :
              (stock.safetyScore ?? 0) >= 55 ? 'text-gold-foreground' :
              (stock.safetyScore ?? 0) >= 40 ? 'text-orange-400' : 'text-destructive'
            )}>
              {stock.safetyScore != null ? stock.safetyScore : '—'}
            </p>
          </div>
        </div>

        {/* Buy Below row */}
        {(stock.buyBelow ?? 0) > 0 && (() => {
          const atTarget = stock.price > 0 && stock.price <= (stock.buyBelow ?? 0)
          return (
            <div className={cn(
              'mt-2 flex items-center justify-between rounded-lg px-3 py-1.5',
              atTarget ? 'bg-success/10' : 'bg-muted/40'
            )}>
              <span className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">Buy Below</span>
              <div className="flex items-center gap-1.5">
                <span className={cn('text-xs font-semibold', atTarget ? 'text-success' : 'text-foreground')}>
                  {formatCurrency(stock.buyBelow!)}
                </span>
                {atTarget && (
                  <span className="text-[10px] font-semibold text-success">✓ At Target</span>
                )}
              </div>
            </div>
          )
        })()}

        {/* Score bars */}
        {hasScores && (
          <>
            <div className="my-3 border-t border-border" />
            <div className="space-y-2">
              {[
                { label: 'Quality',   score: stock.qualityScore },
                { label: 'Valuation', score: stock.valuationScore },
                { label: 'Growth',    score: stock.growthScore },
              ].map(({ label, score }) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="text-[10px] text-muted-foreground w-14 shrink-0">{label}</span>
                  <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full',
                        score != null && score >= 75 ? 'bg-success' :
                        score != null && score >= 55 ? 'bg-gold' :
                        score != null && score >= 40 ? 'bg-orange-400' : 'bg-destructive'
                      )}
                      style={{ width: `${score ?? 0}%` }}
                    />
                  </div>
                  <span className={cn('text-[10px] font-medium w-6 text-right', scoreColor(score))}>
                    {score != null ? Math.round(score) : '—'}
                  </span>
                </div>
              ))}

              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-muted-foreground">Final</span>
                  <span className={cn('text-sm font-bold', scoreColor(stock.finalScore))}>
                    {stock.finalScore != null ? Math.round(stock.finalScore) : '—'}
                  </span>
                  <span className="text-[10px] text-muted-foreground">/100</span>
                </div>
                {stock.confidence != null && (
                  <span className="text-[10px] text-muted-foreground">
                    {Math.round(stock.confidence)}% confidence
                  </span>
                )}
              </div>
            </div>
          </>
        )}

        {/* Data error */}
        {stock.dataError && (
          <p className="mt-2 text-[10px] text-destructive">
            Score data unavailable — {stock.dataError === 'timeout' ? 'request timed out' : 'refresh failed'}
          </p>
        )}

        {/* Last updated */}
        {stock.lastUpdated && !stock.dataError && (
          <p className="mt-2 text-[10px] text-muted-foreground">
            Updated {new Date(stock.lastUpdated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        )}
      </div>
    )
  }

  // ── Render ─────────────────────────────────────────────────────────────────────

  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6">

      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Watchlist</h1>
          <p className="mt-1 text-sm text-muted-foreground">{items.length} securities tracked</p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Refresh Scores button */}
          <button
            onClick={refreshAllScores}
            disabled={isRefreshing || items.length === 0}
            className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground hover:bg-accent disabled:opacity-40 transition-colors"
          >
            <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
            {isRefreshing
              ? `${refreshedCount} / ${items.length} done…`
              : 'Refresh Scores'
            }
          </button>

          {/* Add security control */}
          {showAdd ? (
            <>
              <input
                ref={inputRef}
                type="text"
                value={addInput}
                onChange={(e) => { setAddInput(e.target.value.toUpperCase()); setAddError('') }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter')  addSecurity(addInput)
                  if (e.key === 'Escape') setShowAdd(false)
                }}
                placeholder="Ticker symbol…"
                className="rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary w-36 transition-all"
              />
              <button
                onClick={() => addSecurity(addInput)}
                disabled={isAdding || !addInput}
                className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {isAdding ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                Add
              </button>
              <button onClick={() => { setShowAdd(false); setAddError('') }}>
                <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
              </button>
            </>
          ) : (
            <button
              onClick={openAdd}
              className="flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Plus className="h-4 w-4" />
              Add Security
            </button>
          )}
        </div>
      </div>

      {/* Inline error */}
      {addError && <p className="text-xs text-destructive">{addError}</p>}

      {/* Buy Zone Alerts */}
      {(() => {
        const alerts = items.filter(
          (s) => (s.buyBelow ?? 0) > 0 && s.price > 0 && s.price <= (s.buyBelow ?? 0)
        )
        if (alerts.length === 0) return null
        return (
          <div className="rounded-xl border border-success/30 bg-success/5 overflow-hidden">
            <button
              onClick={() => setAlertsOpen((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-3 text-left"
            >
              <div className="flex items-center gap-2">
                <Bell className="h-4 w-4 text-success" />
                <span className="text-sm font-semibold text-success">
                  {alerts.length} stock{alerts.length > 1 ? 's' : ''} in buy zone
                </span>
                <span className="text-xs text-success/70">— at or below buy-below price</span>
              </div>
              {alertsOpen
                ? <ChevronUp   className="h-4 w-4 text-success/60" />
                : <ChevronDown className="h-4 w-4 text-success/60" />
              }
            </button>
            {alertsOpen && (
              <div className="px-4 pb-4 flex flex-wrap gap-2">
                {alerts.map((s) => {
                  const discount = s.buyBelow! > 0
                    ? Math.round((s.buyBelow! - s.price) / s.buyBelow! * 100)
                    : 0
                  return (
                    <div
                      key={s.symbol}
                      className="flex items-center gap-2 rounded-lg bg-success/10 border border-success/25 px-3 py-2"
                    >
                      <div className="flex h-7 w-7 items-center justify-center rounded-md bg-success/20 text-[10px] font-bold text-success">
                        {s.symbol.slice(0, 2)}
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-foreground">{s.symbol}</p>
                        <p className="text-[10px] text-success">
                          {formatCurrency(s.price)} / target {formatCurrency(s.buyBelow!)}
                          {discount > 0 && <span className="ml-1 font-medium">{discount}% below</span>}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })()}

      {/* Search & Filters */}
      <div className="space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search securities..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-border bg-card pl-10 pr-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2">
              <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-3 overflow-x-auto pb-1">
          {/* Rating filter (5-level) */}
          <div className="flex items-center gap-1.5">
            {filterOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setActiveFilter(opt.value)}
                className={cn(
                  'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap',
                  activeFilter === opt.value
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground hover:bg-accent'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="h-4 w-px bg-border shrink-0" />

          {/* Sort */}
          <div className="relative shrink-0">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="appearance-none rounded-lg border border-border bg-card px-3 py-1.5 pr-8 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              {sortOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>Sort: {opt.label}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground pointer-events-none" />
          </div>

          {/* Sector grouping toggle */}
          <button
            onClick={() => setGroupBySector((v) => !v)}
            title={groupBySector ? 'Show flat list' : 'Group by sector'}
            className={cn(
              'flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors shrink-0',
              groupBySector
                ? 'border-primary/40 bg-primary/10 text-primary'
                : 'border-border bg-card text-muted-foreground hover:bg-accent'
            )}
          >
            {groupBySector ? <List className="h-3.5 w-3.5" /> : <LayoutGrid className="h-3.5 w-3.5" />}
            {groupBySector ? 'Flat' : 'By Sector'}
          </button>
        </div>
      </div>

      {/* Watchlist Grid */}
      {groupBySector ? (
        <div className="space-y-8">
          {SECTOR_ORDER.map((sector) => {
            const sectorStocks = filtered.filter((s) => (s.sector ?? 'Other') === sector)
            if (sectorStocks.length === 0) return null
            return (
              <div key={sector}>
                <div className="flex items-center gap-3 mb-3">
                  <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{sector}</h2>
                  <div className="flex-1 h-px bg-border" />
                  <span className="text-xs text-muted-foreground">{sectorStocks.length}</span>
                </div>
                <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
                  {sectorStocks.map(renderCard)}
                </div>
              </div>
            )
          })}
          {/* Uncategorised stocks (user-added without a sector) */}
          {(() => {
            const other = filtered.filter((s) => !s.sector || !SECTOR_ORDER.includes(s.sector))
            if (other.length === 0) return null
            return (
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Other</h2>
                  <div className="flex-1 h-px bg-border" />
                  <span className="text-xs text-muted-foreground">{other.length}</span>
                </div>
                <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
                  {other.map(renderCard)}
                </div>
              </div>
            )
          })()}
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {filtered.map(renderCard)}
        </div>
      )}

      {/* Empty state */}
      {filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Search className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-sm font-medium text-foreground">No securities found</h3>
          <p className="mt-1 text-xs text-muted-foreground max-w-xs">
            Try adjusting your search or filters.
          </p>
          <button
            onClick={() => { setSearchQuery(''); setActiveFilter('all') }}
            className="mt-4 text-sm text-primary font-medium hover:underline"
          >
            Clear filters
          </button>
        </div>
      )}

      {/* Popular Securities quick-add */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <SectionHeader title="Popular Securities" />
        <div className="mt-3 flex flex-wrap gap-2">
          {POPULAR.map((symbol) => {
            const added = alreadyAdded(symbol)
            return (
              <button
                key={symbol}
                onClick={() => !added && addSecurity(symbol)}
                disabled={added || isAdding}
                className={cn(
                  'flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
                  added
                    ? 'border-border bg-muted text-muted-foreground cursor-default'
                    : 'border-border bg-card text-foreground hover:bg-accent cursor-pointer'
                )}
              >
                {added ? <span className="h-3 w-3 text-success">✓</span> : <Plus className="h-3 w-3" />}
                {symbol}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
