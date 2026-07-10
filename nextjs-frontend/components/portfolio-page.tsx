'use client'

import {
  PieChart, Pie, Cell, ResponsiveContainer,
  AreaChart, Area, Line, XAxis, YAxis, Tooltip, Legend,
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Filter,
  RefreshCw,
  DollarSign,
  BarChart3,
  CalendarDays,
} from 'lucide-react'
import {
  MetricCard,
  SectionHeader,
  DataRow,
  formatCurrency,
} from '@/components/ui-components'
import {
  portfolioData as mockSummary,
  holdings      as mockHoldings,
} from '@/lib/mock-data'
import { type PortfolioApiData, type PortfolioPerformanceData, type DecisionSignal, type DividendEntry, fetchPortfolio, fetchPortfolioPerformance, fetchDecisions, fetchDividends } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useState, useEffect } from 'react'

// ── Sector colour palette ─────────────────────────────────────────────────────
const SECTOR_COLOURS: Record<string, string> = {
  'ETF':                    'var(--chart-1)',
  'Communication Services': 'var(--chart-3)',
  'Technology':             'var(--chart-2)',
  'Consumer Staples':       'var(--chart-4)',
  'Cash':                   'var(--muted-foreground)',
  'Financials':             'var(--chart-5)',
  'Consumer Discretionary': 'var(--chart-1)',
  'Real Estate':            'var(--chart-2)',
  'Healthcare':             'var(--chart-3)',
  'Materials':              'var(--chart-4)',
  'Energy':                 'var(--chart-5)',
  'Industrials':            'var(--chart-1)',
  'Utilities':              'var(--chart-2)',
}
function sectorColour(name: string) {
  return SECTOR_COLOURS[name] ?? 'var(--chart-1)'
}

// ── Internal holding shape used throughout the component ──────────────────────
interface Holding {
  symbol:            string
  name:              string
  sector:            string
  shares:            number
  avgCost:           number
  currentPrice:      number
  value:             number
  costBasis:         number
  unrealisedPnl:     number
  unrealisedPct:     number
  change:            number   // daily change %
  dailyChangeDollars: number  // daily change $
  weight:            number
}

// ── Normalise API data into internal shape ────────────────────────────────────
function fromApi(apiData: PortfolioApiData): {
  holdings: Holding[]
  totalValue: number
  totalGain: number
  totalGainPct: number
  dailyChangePct: number
  dailyChangeDollars: number
  cash: number
  invested: number
  sectorChart: { name: string; value: number; color: string }[]
} {
  const holdings: Holding[] = apiData.holdings.map((h) => ({
    symbol:             h.ticker,
    name:               h.name,
    sector:             h.sector,
    shares:             h.shares,
    avgCost:            h.avg_cost,
    currentPrice:       h.current_price,
    value:              h.market_value,
    costBasis:          h.cost_basis,
    unrealisedPnl:      h.unrealised_pnl,
    unrealisedPct:      h.unrealised_pct,
    change:             h.daily_change_pct,
    dailyChangeDollars: h.daily_change_dollars,
    weight:             h.weight,
  }))

  const sectorWeights = apiData.sector_weights
  const totalValue    = apiData.summary.total_value
  const cashPct       = apiData.summary.cash_pct

  const sectorChart = [
    ...Object.entries(sectorWeights).map(([name, value]) => ({
      name, value, color: sectorColour(name),
    })),
    { name: 'Cash', value: cashPct, color: sectorColour('Cash') },
  ].filter((s) => s.value > 0.1)

  return {
    holdings,
    totalValue,
    totalGain:          apiData.summary.total_gain,
    totalGainPct:       apiData.summary.total_gain_pct,
    dailyChangePct:     apiData.summary.daily_change_pct,
    dailyChangeDollars: apiData.summary.daily_change_dollars,
    cash:               apiData.summary.cash,
    invested:           apiData.summary.invested,
    sectorChart,
  }
}

// ── Fallback using mock data (when API is offline) ───────────────────────────
function fromMock(): ReturnType<typeof fromApi> {
  const holdings: Holding[] = mockHoldings.map((h) => ({
    symbol:        h.symbol,
    name:          h.name,
    sector:        h.sector,
    shares:        h.shares,
    avgCost:       h.avgCost,
    currentPrice:  h.currentPrice,
    value:         h.value,
    costBasis:     h.avgCost * h.shares,
    unrealisedPnl: h.unrealisedPnl,
    unrealisedPct:      h.shares > 0 ? (h.unrealisedPnl / (h.avgCost * h.shares)) * 100 : 0,
    change:             h.change,
    dailyChangeDollars: h.value * h.change / 100,
    weight:             h.weight,
  }))

  const totalValue  = holdings.reduce((s, h) => s + h.value, 0) + mockSummary.cashBalance
  const totalGain   = holdings.reduce((s, h) => s + h.unrealisedPnl, 0)
  const totalCost   = holdings.reduce((s, h) => s + h.costBasis, 0)
  const totalGainPct = totalCost > 0 ? (totalGain / totalCost) * 100 : 0

  // Build sector weights from holdings
  const sw: Record<string, number> = {}
  for (const h of holdings) {
    sw[h.sector] = (sw[h.sector] ?? 0) + h.weight
  }
  const sectorChart = Object.entries(sw).map(([name, value]) => ({
    name, value: +value.toFixed(2), color: sectorColour(name),
  }))

  return {
    holdings,
    totalValue,
    totalGain,
    totalGainPct,
    dailyChangePct:     mockSummary.dailyChangePercent,
    dailyChangeDollars: mockSummary.dailyChange,
    cash:               mockSummary.cashBalance,
    invested:           mockSummary.investedCapital,
    sectorChart,
  }
}

// ── Component ─────────────────────────────────────────────────────────────────

export function PortfolioPage({ apiData }: { apiData?: PortfolioApiData | null }) {
  const [liveData,    setLiveData]    = useState<PortfolioApiData | null | undefined>(apiData)
  const [refreshing,  setRefreshing]  = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(apiData ? new Date() : null)
  const [sortBy,      setSortBy]      = useState<'value' | 'change' | 'weight'>('value')
  const [sortDir,     setSortDir]     = useState<'asc' | 'desc'>('desc')
  const [period,      setPeriod]      = useState<'1m' | '3m' | '6m' | '1y'>('3m')
  const [perfData,      setPerfData]      = useState<PortfolioPerformanceData | null>(null)
  const [perfLoading,   setPerfLoading]   = useState(true)
  const [perfError,     setPerfError]     = useState(false)
  const [decisions,     setDecisions]     = useState<DecisionSignal[]>([])
  const [decisionsLive, setDecisionsLive] = useState(false)
  const [dividends,     setDividends]     = useState<DividendEntry[]>([])
  const [divLoading,    setDivLoading]    = useState(true)

  // Auto-refresh prices on mount — SSR data can be seconds old by the time
  // the browser renders, so fetch fresh numbers immediately in the background.
  useEffect(() => {
    fetchPortfolio().then((fresh) => {
      if (fresh) {
        setLiveData(fresh)
        setLastUpdated(new Date())
      }
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const loadPerf = (p: string) => {
    setPerfLoading(true)
    setPerfError(false)
    fetchPortfolioPerformance(p).then((d) => {
      if (d && d.series.length > 0) {
        setPerfData(d)
        setPerfError(false)
      } else {
        setPerfError(true)
      }
      setPerfLoading(false)
    })
  }

  useEffect(() => { loadPerf(period) }, [period]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchDecisions().then((d) => {
      if (d) {
        setDecisions(d.decisions)
        setDecisionsLive(d.prices_live)
      }
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchDividends().then((d) => {
      if (d) setDividends(d.upcoming)
      setDivLoading(false)
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleRefresh() {
    setRefreshing(true)
    const fresh = await fetchPortfolio()
    if (fresh) {
      setLiveData(fresh)
      setLastUpdated(new Date())
    }
    setRefreshing(false)
  }

  const data    = liveData ? fromApi(liveData) : fromMock()
  const isLive  = liveData?.summary.prices_live ?? false
  const nzdRate = liveData?.nzd_rate ?? 1.69

  // Format a USD value as NZD (primary display)
  const fmtNZD = (usd: number) => {
    const nzd = usd * nzdRate
    const abs = Math.abs(nzd)
    const sign = nzd < 0 ? '-' : ''
    return `${sign}NZ$${abs.toLocaleString('en-NZ', { maximumFractionDigits: 0 })}`
  }

  const { holdings, totalValue, totalGain, totalGainPct,
          dailyChangePct, dailyChangeDollars, cash, invested, sectorChart } = data

  const sorted = [...holdings].sort((a, b) => {
    const m = sortDir === 'desc' ? -1 : 1
    if (sortBy === 'value')  return (a.value  - b.value)  * m
    if (sortBy === 'change') return (a.change - b.change) * m
    return (a.weight - b.weight) * m
  })

  const topGainers = [...holdings].sort((a, b) => b.change - a.change).slice(0, 3)
  const topLosers  = [...holdings].sort((a, b) => a.change - b.change).filter(h => h.change < 0).slice(0, 3)

  function toggleSort(col: 'value' | 'change' | 'weight') {
    if (sortBy === col) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortBy(col); setSortDir('desc') }
  }

  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Portfolio</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {holdings.length} positions
            {isLive
              ? <span className="ml-2 text-success text-xs font-medium">● Live</span>
              : <span className="ml-2 text-muted-foreground text-xs">● Snapshot prices</span>
            }
            {lastUpdated && (
              <span className="ml-3 text-xs text-muted-foreground">
                Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors">
            <Filter className="h-4 w-4" />Filter
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn('h-4 w-4', refreshing && 'animate-spin')} />
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <MetricCard
          title="Total Value"
          value={fmtNZD(totalValue)}
          subtitle={`${formatCurrency(totalValue, true)} USD`}
          change={dailyChangePct}
          changeLabel="today"
          icon={<DollarSign className="h-4 w-4" />}
        />
        <MetricCard
          title="Total Gain / Loss"
          value={fmtNZD(totalGain)}
          subtitle={`${formatCurrency(totalGain, true)} USD`}
          change={totalGainPct}
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <MetricCard
          title="Invested"
          value={fmtNZD(invested)}
          subtitle={`${formatCurrency(invested, true)} USD`}
          icon={<BarChart3 className="h-4 w-4" />}
        />
        <MetricCard
          title="Cash"
          value={fmtNZD(cash)}
          subtitle={`${formatCurrency(cash, true)} USD`}
          icon={<DollarSign className="h-4 w-4" />}
        />
      </div>

      {/* Daily P&L banner — only meaningful when live prices are loaded */}
      {isLive && dailyChangeDollars !== 0 && (
        <div className={cn(
          'rounded-xl border px-4 py-3 flex items-center gap-3',
          dailyChangeDollars >= 0
            ? 'border-success/30 bg-success/5'
            : 'border-destructive/30 bg-destructive/5'
        )}>
          {dailyChangeDollars >= 0
            ? <ArrowUpRight   className="h-4 w-4 text-success shrink-0" />
            : <ArrowDownRight className="h-4 w-4 text-destructive shrink-0" />
          }
          <p className="text-sm font-medium text-foreground">
            Today&apos;s P&amp;L:{' '}
            <span className={dailyChangeDollars >= 0 ? 'text-success' : 'text-destructive'}>
              {dailyChangeDollars >= 0 ? '+' : ''}{formatCurrency(dailyChangeDollars)}
              {' '}({dailyChangePct >= 0 ? '+' : ''}{(dailyChangePct).toFixed(2)}%)
            </span>
          </p>
        </div>
      )}

      {/* Performance Chart */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-sm font-semibold text-foreground">Portfolio Performance</p>
            {perfData && (
              <div className="flex items-center gap-3 mt-0.5 flex-wrap">
                <p className={cn(
                  'text-xs font-medium',
                  perfData.change_pct >= 0 ? 'text-success' : 'text-destructive'
                )}>
                  Portfolio: {perfData.change_pct >= 0 ? '+' : ''}{perfData.change_pct.toFixed(2)}%
                  {' '}({perfData.change_dollars >= 0 ? '+' : ''}{formatCurrency(perfData.change_dollars)})
                </p>
                {perfData.benchmark_change_pct != null && (
                  <p className={cn(
                    'text-xs font-medium',
                    perfData.benchmark_change_pct >= 0 ? 'text-muted-foreground' : 'text-destructive/70'
                  )}>
                    S&amp;P 500: {perfData.benchmark_change_pct >= 0 ? '+' : ''}{perfData.benchmark_change_pct.toFixed(2)}%
                  </p>
                )}
                {perfData.benchmark_change_pct != null && (() => {
                  const alpha = perfData.change_pct - perfData.benchmark_change_pct
                  return (
                    <p className={cn('text-xs font-semibold', alpha >= 0 ? 'text-success' : 'text-destructive')}>
                      {alpha >= 0 ? '▲' : '▼'} {Math.abs(alpha).toFixed(2)}% vs market
                    </p>
                  )
                })()}
              </div>
            )}
          </div>
          <div className="flex items-center gap-1">
            {(['1m', '3m', '6m', '1y'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={cn(
                  'px-2.5 py-1 text-xs font-medium rounded-md transition-colors',
                  period === p
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent'
                )}
              >
                {p.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {perfLoading ? (
          <div className="h-48 flex items-center justify-center">
            <div className="h-1.5 w-32 rounded-full bg-muted overflow-hidden">
              <div className="h-full w-1/2 bg-primary/40 rounded-full animate-pulse" />
            </div>
          </div>
        ) : perfData && perfData.series.length > 0 ? (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={perfData.series} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="perfGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="var(--primary)" stopOpacity={0.20} />
                  <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}    />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }}
                tickFormatter={(d: string) => {
                  const dt = new Date(d)
                  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                }}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[(min: number) => min * 0.97, (max: number) => max * 1.02]}
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }}
                tickFormatter={(v: number) => `NZ$${((v * nzdRate) / 1000).toFixed(1)}k`}
                width={56}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--card)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  fontSize: '12px',
                  color: 'var(--foreground)',
                }}
                formatter={(v: number, name: string) => [
                  `${fmtNZD(v)} (${formatCurrency(v)} USD)`,
                  name === 'value' ? 'Portfolio' : 'S&P 500 (scaled)',
                ]}
                labelFormatter={(d: string) => new Date(d).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
              />
              {/* Portfolio area */}
              <Area
                type="monotone"
                dataKey="value"
                stroke="var(--primary)"
                strokeWidth={2}
                fill="url(#perfGrad)"
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
                connectNulls
              />
              {/* S&P 500 benchmark line */}
              {perfData.series.some((pt) => pt.benchmark != null) && (
                <Line
                  type="monotone"
                  dataKey="benchmark"
                  stroke="var(--muted-foreground)"
                  strokeWidth={1.5}
                  strokeDasharray="4 3"
                  dot={false}
                  activeDot={{ r: 3, strokeWidth: 0 }}
                  connectNulls
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-48 flex flex-col items-center justify-center gap-3">
            <p className="text-sm text-muted-foreground">
              {perfError
                ? 'Performance data unavailable — the server may still be warming up.'
                : 'No performance data for this period.'}
            </p>
            {perfError && (
              <button
                onClick={() => loadPerf(period)}
                className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-accent transition-colors"
              >
                <RefreshCw className="h-3 w-3" /> Retry
              </button>
            )}
          </div>
        )}

        {/* Legend */}
        {perfData && perfData.series.some((pt) => pt.benchmark != null) && (
          <div className="flex items-center gap-4 mt-2 px-1">
            <div className="flex items-center gap-1.5">
              <div className="h-0.5 w-6 bg-primary rounded-full" />
              <span className="text-[10px] text-muted-foreground">Your portfolio</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-0.5 w-6 rounded-full border-t-2 border-dashed border-muted-foreground" />
              <span className="text-[10px] text-muted-foreground">S&amp;P 500 (SPY)</span>
            </div>
          </div>
        )}
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Holdings Table */}
        <div className="lg:col-span-2 rounded-xl border border-border bg-card shadow-sm overflow-hidden">
          <div className="p-4 border-b border-border">
            <SectionHeader title="Holdings" />
          </div>

          {/* Table header with sort controls */}
          <div className="hidden lg:grid grid-cols-12 gap-2 px-4 py-2 border-b border-border bg-muted/30">
            <div className="col-span-4 text-xs font-medium text-muted-foreground">Asset</div>
            <div className="col-span-2 text-xs font-medium text-muted-foreground text-right">Price</div>
            <button
              onClick={() => toggleSort('value')}
              className="col-span-2 text-xs font-medium text-muted-foreground text-right hover:text-foreground transition-colors"
            >
              Value {sortBy === 'value' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
            </button>
            <button
              onClick={() => toggleSort('change')}
              className="col-span-2 text-xs font-medium text-muted-foreground text-right hover:text-foreground transition-colors"
            >
              Day {sortBy === 'change' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
            </button>
            <button
              onClick={() => toggleSort('weight')}
              className="col-span-2 text-xs font-medium text-muted-foreground text-right hover:text-foreground transition-colors"
            >
              Weight {sortBy === 'weight' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
            </button>
          </div>

          <div className="divide-y divide-border">
            {sorted.map((h) => (
              <div key={h.symbol} className="px-4 py-3 hover:bg-accent/30 transition-colors">
                {/* Mobile */}
                <div className="lg:hidden">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-sm font-semibold text-foreground">
                        {h.symbol.slice(0, 2)}
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <p className="text-sm font-medium text-foreground">{h.symbol}</p>
                          {h.sector === 'ETF' && (
                            <span className="rounded px-1 py-0.5 text-[9px] font-bold uppercase tracking-wide bg-primary/10 text-primary">ETF</span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">{h.shares.toFixed(2)} sh</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-foreground">{formatCurrency(h.value, true)}</p>
                      <p className={cn('text-xs', h.change >= 0 ? 'text-success' : 'text-destructive')}>
                        {h.change >= 0 ? '+' : ''}{h.change.toFixed(2)}%
                      </p>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                    <span>{formatCurrency(h.currentPrice)}</span>
                    <span>{h.sector}</span>
                    <span>{h.weight}%</span>
                  </div>
                </div>

                {/* Desktop */}
                <div className="hidden lg:grid grid-cols-12 gap-2 items-center">
                  <div className="col-span-4 flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-xs font-semibold text-foreground">
                      {h.symbol.slice(0, 2)}
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <p className="text-sm font-medium text-foreground">{h.symbol}</p>
                        {h.sector === 'ETF' && (
                          <span className="rounded px-1 py-0.5 text-[9px] font-bold uppercase tracking-wide bg-primary/10 text-primary">ETF</span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{h.name}</p>
                    </div>
                  </div>
                  <div className="col-span-2 text-right">
                    <p className="text-sm font-medium text-foreground">{formatCurrency(h.currentPrice)}</p>
                    <p className="text-xs text-muted-foreground">{h.shares.toFixed(2)} sh</p>
                  </div>
                  <div className="col-span-2 text-right">
                    <p className="text-sm font-medium text-foreground">{formatCurrency(h.value)}</p>
                    <p className={cn(
                      'text-xs',
                      h.unrealisedPnl >= 0 ? 'text-success' : 'text-destructive'
                    )}>
                      {h.unrealisedPnl >= 0 ? '+' : ''}{formatCurrency(h.unrealisedPnl)}
                      {' '}({h.unrealisedPct >= 0 ? '+' : ''}{h.unrealisedPct.toFixed(2)}%)
                    </p>
                  </div>
                  <div className="col-span-2 text-right">
                    <p className={cn(
                      'text-sm font-medium flex items-center justify-end gap-1',
                      h.change >= 0 ? 'text-success' : 'text-destructive'
                    )}>
                      {h.change >= 0
                        ? <ArrowUpRight   className="h-3 w-3" />
                        : <ArrowDownRight className="h-3 w-3" />
                      }
                      {h.change >= 0 ? '+' : ''}{h.change.toFixed(2)}%
                    </p>
                    <p className={cn('text-xs', h.change >= 0 ? 'text-success/70' : 'text-destructive/70')}>
                      {h.dailyChangeDollars >= 0 ? '+' : ''}{formatCurrency(h.dailyChangeDollars)}
                    </p>
                  </div>
                  <div className="col-span-2 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${Math.min((h.weight / 20) * 100, 100)}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-foreground">{h.weight}%</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Sector Allocation */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Sector Allocation" />
            <div className="mt-4 h-40">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sectorChart}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {sectorChart.map((entry, i) => (
                      <Cell key={`cell-${i}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 space-y-1.5">
              {sectorChart
                .sort((a, b) => b.value - a.value)
                .map((s) => (
                  <div key={s.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: s.color }} />
                      <span className="text-xs text-muted-foreground">{s.name}</span>
                    </div>
                    <span className="text-xs font-medium text-foreground">{s.value.toFixed(2)}%</span>
                  </div>
                ))}
            </div>
          </div>

          {/* Top Performers */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Today&apos;s Movers" />
            <div className="mt-3 space-y-4">
              {topGainers.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                    <TrendingUp className="h-3 w-3 text-success" /> Gainers
                  </p>
                  <div className="space-y-2">
                    {topGainers.map((h) => (
                      <div key={h.symbol} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-success/10 text-[10px] font-semibold text-success">
                            {h.symbol.slice(0, 2)}
                          </div>
                          <span className="text-sm font-medium text-foreground">{h.symbol}</span>
                        </div>
                        <span className="text-sm font-medium text-success">
                          +{h.change.toFixed(2)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {topLosers.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                    <TrendingDown className="h-3 w-3 text-destructive" /> Losers
                  </p>
                  <div className="space-y-2">
                    {topLosers.map((h) => (
                      <div key={h.symbol} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-destructive/10 text-[10px] font-semibold text-destructive">
                            {h.symbol.slice(0, 2)}
                          </div>
                          <span className="text-sm font-medium text-foreground">{h.symbol}</span>
                        </div>
                        <span className="text-sm font-medium text-destructive">
                          {h.change.toFixed(2)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {topGainers.length === 0 && topLosers.length === 0 && (
                <p className="text-xs text-muted-foreground">Live price data required for daily movers.</p>
              )}
            </div>
          </div>

          {/* Summary Metrics */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Portfolio Metrics" />
            <div className="mt-3 divide-y divide-border">
              <DataRow label="Positions"      value={String(holdings.length)} />
              <DataRow label="Sectors"        value={String(sectorChart.filter(s => s.name !== 'Cash').length)} />
              <DataRow label="Total Cost"     value={formatCurrency(holdings.reduce((s, h) => s + h.costBasis, 0))} />
              <DataRow label="Unrealised G/L" value={formatCurrency(totalGain)} change={totalGainPct} />
              <DataRow label="Cash"           value={formatCurrency(cash)} />
            </div>
          </div>
        </div>
      </div>
      {/* Dividend Calendar */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <CalendarDays className="h-4 w-4 text-muted-foreground" />
          <p className="text-sm font-semibold text-foreground">Dividend Calendar</p>
          <span className="text-xs text-muted-foreground">— upcoming ex-dividend dates</span>
        </div>

        {divLoading ? (
          <div className="flex items-center gap-2 py-4">
            <div className="h-1.5 w-32 rounded-full bg-muted overflow-hidden">
              <div className="h-full w-1/2 bg-primary/40 rounded-full animate-pulse" />
            </div>
            <span className="text-xs text-muted-foreground">Loading dividend data…</span>
          </div>
        ) : dividends.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4">
            No upcoming ex-dividend dates found — API may need a moment to load.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="pb-2 text-left text-xs font-medium text-muted-foreground">Stock</th>
                  <th className="pb-2 text-center text-xs font-medium text-muted-foreground">Ex-Div Date</th>
                  <th className="pb-2 text-center text-xs font-medium text-muted-foreground">Pay Date</th>
                  <th className="pb-2 text-right text-xs font-medium text-muted-foreground">Per Share</th>
                  <th className="pb-2 text-right text-xs font-medium text-muted-foreground">Yield</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {dividends.map((d) => {
                  const daysUntil = d.ex_div_date
                    ? Math.ceil((new Date(d.ex_div_date).getTime() - Date.now()) / 86_400_000)
                    : null
                  const isClose = daysUntil != null && daysUntil <= 7
                  return (
                    <tr key={d.ticker} className="hover:bg-accent/30 transition-colors">
                      <td className="py-2.5 pr-4">
                        <div className="flex items-center gap-2">
                          <div className={cn(
                            'flex h-7 w-7 items-center justify-center rounded-md text-[10px] font-bold',
                            d.in_portfolio ? 'bg-primary/10 text-primary' : 'bg-accent text-foreground'
                          )}>
                            {d.ticker.slice(0, 2)}
                          </div>
                          <div>
                            <p className="text-xs font-semibold text-foreground">{d.ticker}</p>
                            <p className="text-[10px] text-muted-foreground truncate max-w-[120px]">{d.name}</p>
                          </div>
                          {d.in_portfolio && (
                            <span className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                              held
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 text-center">
                        <div>
                          <p className={cn('text-xs font-medium', isClose ? 'text-gold-foreground' : 'text-foreground')}>
                            {d.ex_div_date
                              ? new Date(d.ex_div_date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                              : '—'
                            }
                          </p>
                          {daysUntil != null && (
                            <p className={cn('text-[10px]', isClose ? 'text-gold-foreground font-medium' : 'text-muted-foreground')}>
                              {daysUntil === 0 ? 'Today' : daysUntil === 1 ? 'Tomorrow' : `${daysUntil}d`}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 text-center text-xs text-muted-foreground">
                        {d.pay_date
                          ? new Date(d.pay_date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                          : '—'
                        }
                      </td>
                      <td className="py-2.5 text-right">
                        <p className="text-xs font-medium text-foreground">${d.quarterly_div.toFixed(4)}</p>
                        <p className="text-[10px] text-muted-foreground">${d.annual_div.toFixed(2)}/yr</p>
                      </td>
                      <td className="py-2.5 text-right">
                        <p className={cn('text-xs font-medium', (d.yield_pct ?? 0) >= 3 ? 'text-success' : 'text-foreground')}>
                          {d.yield_pct != null ? `${d.yield_pct.toFixed(2)}%` : '—'}
                        </p>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Daily Decisions Feed */}
      {decisions.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm font-semibold text-foreground">Daily Decisions</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Rule-based signals from live portfolio metrics
                {decisionsLive
                  ? <span className="ml-2 text-success font-medium">● Live</span>
                  : <span className="ml-2 text-muted-foreground">● Snapshot</span>
                }
              </p>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {decisions.map((d, i) => {
              const actionStyles: Record<string, string> = {
                ADD:     'bg-success/10 text-success border-success/30',
                TRIM:    'bg-destructive/10 text-destructive border-destructive/30',
                MONITOR: 'bg-gold/10 text-gold-foreground border-gold/30',
                HOLD:    'bg-muted/60 text-muted-foreground border-border',
              }
              const urgencyDot: Record<string, string> = {
                high:   'bg-destructive',
                medium: 'bg-gold',
                low:    'bg-muted-foreground',
              }
              const style = actionStyles[d.action] ?? actionStyles.HOLD
              return (
                <div key={i} className="rounded-lg border border-border bg-card/50 p-3 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-foreground">{d.ticker}</span>
                      <span className={cn('text-[10px] font-bold px-2 py-0.5 rounded-md border uppercase tracking-wide', style)}>
                        {d.action}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div className={cn('h-1.5 w-1.5 rounded-full', urgencyDot[d.urgency] ?? 'bg-muted-foreground')} />
                      <span className="text-[10px] text-muted-foreground capitalize">{d.urgency}</span>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">{d.reason}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
