'use client'

import { useState, useEffect } from 'react'
import {
  PieChart, Pie, Cell, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, Line,
} from 'recharts'
import {
  Wallet, TrendingUp, TrendingDown, DollarSign, Activity, ShieldCheck,
  BarChart2, ChevronRight, Newspaper, Zap,
} from 'lucide-react'
import {
  MetricCard, SectionHeader, ProgressRing, AlertCard,
  ActionBadge, UrgencyDot, ScoreBadge, EventTypeBadge, HealthStatusRow,
  MarketRegimeBanner, formatCurrency,
} from '@/components/ui-components'
import {
  portfolioData, marketRegime as mockRegime, portfolioHealthDetail, performanceData,
  dailyDecisions, opportunities, riskAlerts, sectorAllocation, holdings,
  marketIndices as mockIndices, newsEvents as mockNews, upcomingEvents, topMovers, allocationDrift,
} from '@/lib/mock-data'
import type { LiveDashboardData, DashboardDecision, DashboardOpportunity, DashboardHolding, DashboardSectorEntry, ScannerOpportunity, EarningsItem } from '@/lib/api'
import { fetchPortfolioPerformance, triggerScan, fetchScannerStatus, fetchScannerResults, fetchPortfolioEarnings } from '@/lib/api'
import { cn } from '@/lib/utils'
import Link from 'next/link'

interface DashboardPageProps {
  liveData?: LiveDashboardData
}

// Map UI period labels → API param + optional client-side slice
const PERIOD_MAP: Record<string, { apiParam: string; sliceDays?: number }> = {
  '1W': { apiParam: '1m', sliceDays: 7 },
  '1M': { apiParam: '1m' },
  '3M': { apiParam: '3m' },
  '1Y': { apiParam: '1y' },
  'ALL': { apiParam: '1y' },
}

// Format ISO date → readable label based on zoom level
function fmtDate(iso: string, sliceDays?: number): string {
  const d = new Date(iso + 'T00:00:00')
  if (sliceDays && sliceDays <= 7) return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  if (sliceDays && sliceDays <= 35) return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
}

export function DashboardPage({ liveData }: DashboardPageProps) {
  const [activePeriod, setActivePeriod] = useState<string>('1Y')
  const [livePerf, setLivePerf] = useState<{ date: string; portfolio: number; benchmark?: number | null }[] | null>(null)
  const [perfStats, setPerfStats] = useState<{ volatility: number | null; sharpe: number | null }>({ volatility: null, sharpe: null })
  const [perfLoading, setPerfLoading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [scannerOpps, setScannerOpps] = useState<ScannerOpportunity[] | null>(null)
  const [earnings, setEarnings] = useState<EarningsItem[] | null>(null)

  useEffect(() => {
    const { apiParam, sliceDays } = PERIOD_MAP[activePeriod] ?? { apiParam: '1y' }
    setPerfLoading(true)
    fetchPortfolioPerformance(apiParam).then((d) => {
      if (d && d.series.length > 0) {
        let pts = d.series.map((s: { date: string; value: number; benchmark?: number | null }) => ({
          date:      fmtDate(s.date, sliceDays),
          portfolio: s.value,
          benchmark: s.benchmark ?? null,
        }))
        if (sliceDays) pts = pts.slice(-sliceDays)
        setLivePerf(pts)
        setPerfStats({ volatility: d.volatility ?? null, sharpe: d.sharpe ?? null })
      } else {
        setLivePerf(null)
      }
    }).finally(() => setPerfLoading(false))
  }, [activePeriod])

  useEffect(() => {
    fetchScannerStatus().then((s) => { if (s?.running) setScanning(true) })
    fetchScannerResults().then((r) => {
      if (r?.opportunities?.length) setScannerOpps(r.opportunities.slice(0, 5))
    })
    fetchPortfolioEarnings().then((e) => { if (e?.length) setEarnings(e) })
  }, [])

  const handleRunScan = async () => {
    setScanning(true)
    await triggerScan()
  }

  // Use live data from FastAPI where available, fall back to mock data
  const marketRegime  = liveData?.marketRegime  ?? mockRegime
  const marketIndices = liveData?.marketIndices ?? mockIndices
  const newsEvents    = liveData?.newsEvents    ?? mockNews
  const liveDecisions     = liveData?.decisions     ?? null
  const liveOpportunities = liveData?.opportunities ?? null
  const liveRiskAlerts    = liveData?.riskAlerts    ?? null

  // Live portfolio widgets (fall back to mock)
  const displayHoldings: DashboardHolding[] = liveData?.topHoldings ?? holdings.slice(0, 6).map(h => ({
    symbol: h.symbol, name: h.name, weight: h.weight,
    value: h.value, change: h.change, unrealisedPnl: h.unrealisedPnl,
  }))
  const displaySectors: DashboardSectorEntry[] = liveData?.sectorAlloc ?? sectorAllocation

  // Portfolio live values (fall back to mock when API is offline)
  const ps = liveData?.portfolioSummary ?? null
  const pr = liveData?.portfolioRisk    ?? null

  const totalValue         = ps?.total_value          ?? portfolioData.totalValue
  const dailyChangeDollars = ps?.daily_change_dollars ?? portfolioData.dailyChange
  const dailyChangePct     = ps?.daily_change_pct     ?? portfolioData.dailyChangePercent
  const cashBalance        = ps?.cash                 ?? portfolioData.cashBalance
  const investedCapital    = ps?.invested             ?? portfolioData.investedCapital
  const healthScore        = pr?.health_score ?? ps?.health_score ?? portfolioData.portfolioHealthScore
  const portfolioBeta      = pr?.metrics.portfolio_beta ?? portfolioData.beta
  // Weekly P&L derived from last 5 trading days of performance series
  const weeklyChange = (() => {
    if (!livePerf || livePerf.length < 2) return portfolioData.weeklyChange
    const end   = livePerf[livePerf.length - 1].portfolio
    const start = livePerf[Math.max(0, livePerf.length - 6)].portfolio
    return Math.round((end - start) * 100) / 100
  })()
  const weeklyChangePct = (() => {
    if (!livePerf || livePerf.length < 2) return portfolioData.weeklyChangePercent
    const end   = livePerf[livePerf.length - 1].portfolio
    const start = livePerf[Math.max(0, livePerf.length - 6)].portfolio
    return start ? Math.round((end - start) / start * 10000) / 100 : 0
  })()
  const buyingPower = portfolioData.buyingPower

  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6 max-w-[1600px] mx-auto">

      {/* ── Row 1: 8 Metric Cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:gap-4">
        <MetricCard
          title="Portfolio Value"
          value={formatCurrency(totalValue, true)}
          change={dailyChangePct}
          changeLabel="today"
          icon={<Wallet className="h-4 w-4" />}
        />
        <MetricCard
          title="Daily P&L"
          value={formatCurrency(dailyChangeDollars)}
          change={dailyChangePct}
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <MetricCard
          title="Weekly P&L"
          value={formatCurrency(weeklyChange)}
          change={weeklyChangePct}
          icon={<BarChart2 className="h-4 w-4" />}
        />
        <MetricCard
          title="Cash Balance"
          value={formatCurrency(cashBalance, true)}
          icon={<DollarSign className="h-4 w-4" />}
        />
        <MetricCard
          title="Invested Capital"
          value={formatCurrency(investedCapital, true)}
          change={portfolioData.monthlyChangePercent}
          changeLabel="this month"
          icon={<Activity className="h-4 w-4" />}
        />
        <MetricCard
          title="Health Score"
          value={`${Math.round(healthScore)}/100`}
          icon={<ShieldCheck className="h-4 w-4" />}
        />
        <MetricCard
          title="Portfolio Beta"
          value={portfolioBeta.toFixed(2)}
          icon={<Activity className="h-4 w-4" />}
        />
        <MetricCard
          title="Buying Power"
          value={formatCurrency(buyingPower, true)}
          icon={<Wallet className="h-4 w-4" />}
        />
      </div>

      {/* ── Row 2: Market Regime Banner ──────────────────────────────────────── */}
      <MarketRegimeBanner {...marketRegime} />

      {/* ── Row 3: Performance Chart + Portfolio Health ───────────────────────── */}
      <div className="grid gap-6 lg:grid-cols-3">

        {/* Performance Chart — 2/3 width */}
        <div className="lg:col-span-2 rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader
            title="Portfolio Performance"
            action={
              <div className="flex gap-1">
                {['1W', '1M', '3M', '1Y', 'ALL'].map((p) => (
                  <button
                    key={p}
                    onClick={() => setActivePeriod(p)}
                    className={cn(
                      'px-2 py-1 text-xs font-medium rounded-md transition-colors',
                      p === activePeriod
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent'
                    )}
                  >
                    {p}
                  </button>
                ))}
              </div>
            }
          />
          <div className="mt-4 h-52 lg:h-64 relative">
            {perfLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-card/60 rounded-lg z-10">
                <span className="text-xs text-muted-foreground animate-pulse">Loading…</span>
              </div>
            )}
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={livePerf ?? performanceData} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                <defs>
                  <linearGradient id="pgGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.2} />
                    <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }}
                  interval="preserveStartEnd"
                />
                <YAxis
                  hide
                  domain={[(min: number) => min * 0.98, (max: number) => max * 1.02]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--card)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                  formatter={(v: number) => [formatCurrency(v), '']}
                />
                <Area
                  type="monotone"
                  dataKey="portfolio"
                  stroke="var(--primary)"
                  strokeWidth={2}
                  fill="url(#pgGrad)"
                  name="Portfolio"
                />
                <Line
                  type="monotone"
                  dataKey="benchmark"
                  stroke="var(--muted-foreground)"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  dot={false}
                  name="S&P 500"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-5 text-xs">
            <div className="flex items-center gap-2">
              <div className="h-2 w-4 rounded-sm bg-primary" />
              <span className="text-muted-foreground">Portfolio</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-0.5 w-4 border-t border-dashed border-muted-foreground" />
              <span className="text-muted-foreground">S&P 500</span>
            </div>
            <div className="ml-auto flex gap-4 text-muted-foreground">
              <span>YTD: <span className="text-success font-medium">+{portfolioData.yearlyChangePercent.toFixed(2)}%</span></span>
              <span>Sharpe: <span className="text-foreground font-medium">{portfolioData.sharpeRatio}</span></span>
            </div>
          </div>
        </div>

        {/* Portfolio Health — 1/3 width */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader title="Portfolio Health" />
          <div className="mt-4 flex items-center gap-4">
            <ProgressRing value={Math.round(healthScore)} size={64} strokeWidth={5} />
            <div>
              <p className="text-2xl font-semibold text-foreground">
                {Math.round(healthScore)}
                <span className="text-sm font-normal text-muted-foreground">/100</span>
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">Overall Score</p>
            </div>
          </div>
          <div className="mt-4">
            {portfolioHealthDetail.indicators.map((ind) => (
              <HealthStatusRow
                key={ind.label}
                label={ind.label}
                status={ind.status}
                detail={ind.detail}
              />
            ))}
          </div>
        </div>
      </div>

      {/* ── Row 4: Decisions | Opportunities | Risk Alerts ───────────────────── */}
      <div className="grid gap-6 lg:grid-cols-3">

        {/* Today's Decisions */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader
            title="Today's Decisions"
            action={
              <span className="text-xs text-muted-foreground">
                {new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
              </span>
            }
          />
          <div className="mt-3 divide-y divide-border">
            {(liveDecisions ?? dailyDecisions).length === 0 ? (
              <p className="py-4 text-center text-xs text-muted-foreground">No signals today — portfolio on track.</p>
            ) : (
              (liveDecisions ?? dailyDecisions).map((d: DashboardDecision) => (
                <div key={d.ticker} className="flex items-start gap-3 py-2.5">
                  <UrgencyDot urgency={d.urgency} />
                  <div className="flex-1 min-w-0 mt-[-1px]">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-semibold text-foreground">{d.ticker}</span>
                      <ActionBadge action={d.action} />
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">{d.reason}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Best Opportunities */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader
            title="Best Opportunities"
            action={
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRunScan}
                  disabled={scanning}
                  className={cn(
                    'flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition-colors',
                    scanning
                      ? 'text-muted-foreground cursor-not-allowed'
                      : 'bg-amber-500/15 text-amber-400 hover:bg-amber-500/25'
                  )}
                >
                  <Zap className={cn('h-3 w-3', scanning && 'animate-pulse')} />
                  {scanning ? 'Scanning…' : 'Run Scan'}
                </button>
                <Link href="/opportunities" className="text-xs text-primary hover:underline flex items-center gap-0.5">
                  View all <ChevronRight className="h-3 w-3" />
                </Link>
              </div>
            }
          />
          <div className="mt-3 divide-y divide-border">
            {scannerOpps ? (
              scannerOpps.map((o) => {
                const changeUp = (o.change_pct ?? 0) >= 0
                return (
                  <div key={o.ticker} className="flex items-center gap-3 py-2.5">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-[11px] font-bold text-foreground flex-shrink-0">
                      {o.ticker.slice(0, 3)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-foreground">{o.ticker}</span>
                        <span className={cn('text-xs font-semibold', changeUp ? 'text-success' : 'text-destructive')}>
                          {changeUp ? '+' : ''}{((o.change_pct ?? 0) * 100).toFixed(2)}%
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground truncate">{o.name}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-muted-foreground">{o.price != null ? formatCurrency(o.price) : '—'}</span>
                        {o.sector && <span className="text-[10px] px-1.5 py-0.5 bg-muted rounded-md text-muted-foreground font-medium">{o.sector}</span>}
                      </div>
                    </div>
                    <ScoreBadge score={o.score} />
                  </div>
                )
              })
            ) : (liveOpportunities ?? opportunities).length === 0 ? (
              <p className="py-4 text-center text-xs text-muted-foreground">No scan results yet — click Run Scan to generate opportunities.</p>
            ) : (
              (liveOpportunities ?? opportunities).map((o: DashboardOpportunity) => (
                <div key={o.ticker} className="flex items-center gap-3 py-2.5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-[11px] font-bold text-foreground flex-shrink-0">
                    {o.ticker.slice(0, 3)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-foreground">{o.ticker}</span>
                      <span className={cn('text-xs font-semibold', o.upside >= 0 ? 'text-success' : 'text-destructive')}>
                        {o.upside >= 0 ? '+' : ''}{o.upside.toFixed(2)}% upside
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground">{o.company}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] text-muted-foreground">{formatCurrency(o.price)}</span>
                      <span className="text-[10px] px-1.5 py-0.5 bg-muted rounded-md text-muted-foreground font-medium">{o.tag}</span>
                    </div>
                  </div>
                  <ScoreBadge score={o.score} />
                </div>
              ))
            )}
          </div>
        </div>

        {/* Risk Alerts */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader
            title="Risk Alerts"
            action={
              <Link href="/risk" className="text-xs text-primary hover:underline flex items-center gap-0.5">
                View all <ChevronRight className="h-3 w-3" />
              </Link>
            }
          />
          <div className="mt-3 space-y-2">
            {(liveRiskAlerts ?? riskAlerts).map((alert, i) => (
              <AlertCard
                key={i}
                severity={alert.severity}
                title={alert.title}
                description={alert.description}
              />
            ))}
          </div>
          <div className="mt-4 pt-3 border-t border-border grid grid-cols-3 gap-2">
            <div className="rounded-lg bg-accent/50 p-2 text-center">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Beta</p>
              <p className="text-sm font-semibold text-foreground mt-0.5">{portfolioBeta.toFixed(2)}</p>
            </div>
            <div className="rounded-lg bg-accent/50 p-2 text-center">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Vol</p>
              <p className="text-sm font-semibold text-foreground mt-0.5">
                {perfStats.volatility != null ? `${perfStats.volatility}%` : '—'}
              </p>
            </div>
            <div className="rounded-lg bg-accent/50 p-2 text-center">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Sharpe</p>
              <p className="text-sm font-semibold text-foreground mt-0.5">
                {perfStats.sharpe != null ? perfStats.sharpe : '—'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Row 5: Sector Exposure | Top Holdings | Market Overview ──────────── */}
      <div className="grid gap-6 lg:grid-cols-3">

        {/* Sector Exposure — donut + legend */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader title="Sector Exposure" />
          <div className="mt-3 flex items-center gap-4">
            <div className="h-36 w-36 flex-shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={displaySectors}
                    cx="50%"
                    cy="50%"
                    innerRadius={38}
                    outerRadius={62}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {displaySectors.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex-1 space-y-2">
              {displaySectors.map((s) => (
                <div key={s.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: s.color }} />
                    <span className="text-xs text-muted-foreground truncate max-w-[90px]">{s.name}</span>
                  </div>
                  <span className="text-xs font-medium text-foreground">{Number(s.value).toFixed(2)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Top Holdings */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader
            title="Top Holdings"
            action={
              <Link href="/portfolio" className="text-xs text-primary hover:underline flex items-center gap-0.5">
                All <ChevronRight className="h-3 w-3" />
              </Link>
            }
          />
          <div className="mt-3 divide-y divide-border">
            {displayHoldings.map((h) => (
              <div key={h.symbol} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-7 w-7 items-center justify-center rounded-md bg-accent text-[10px] font-bold text-foreground flex-shrink-0">
                    {h.symbol.slice(0, 2)}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-foreground">{h.symbol}</p>
                    <p className="text-[10px] text-muted-foreground">{h.weight.toFixed(2)}% weight</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs font-medium text-foreground">{formatCurrency(h.value, true)}</p>
                  <p className={cn('text-[10px]', h.change >= 0 ? 'text-success' : 'text-destructive')}>
                    {h.change >= 0 ? '+' : ''}{h.change.toFixed(2)}%
                    {' · '}
                    {h.unrealisedPnl >= 0 ? '+' : ''}{formatCurrency(h.unrealisedPnl, true)} PnL
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Market Overview */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader title="Market Overview" />
          <div className="mt-3 divide-y divide-border">
            {marketIndices.map((idx) => (
              <div key={idx.symbol} className="flex items-center justify-between py-2">
                <div>
                  <p className="text-xs font-medium text-foreground">{idx.name}</p>
                  <p className="text-[10px] text-muted-foreground">{idx.symbol}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs font-semibold text-foreground">
                    {idx.value >= 1000
                      ? idx.value.toLocaleString('en-US', { maximumFractionDigits: 2 })
                      : idx.value.toFixed(2)}
                  </p>
                  <p className={cn('text-[10px] font-medium', idx.change >= 0 ? 'text-success' : 'text-destructive')}>
                    {idx.change >= 0 ? '+' : ''}{idx.change.toFixed(2)}%
                    {idx.ytd !== null && (
                      <span className="text-muted-foreground">
                        {' · YTD '}
                        {idx.ytd > 0 ? '+' : ''}{idx.ytd}%
                      </span>
                    )}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Row 6: Intelligence Feed | Upcoming Events | Watchlist Movers ────── */}
      <div className="grid gap-6 lg:grid-cols-3">

        {/* Intelligence Feed */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader
            title="Intelligence Feed"
            action={
              <Link href="/intelligence" className="text-xs text-primary hover:underline flex items-center gap-0.5">
                More <ChevronRight className="h-3 w-3" />
              </Link>
            }
          />
          <div className="mt-3 divide-y divide-border">
            {newsEvents.map((n, i) => (
              <a
                key={i}
                href={n.url ?? undefined}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                  'flex items-start gap-3 py-3 first:pt-0 last:pb-0',
                  n.url && 'hover:bg-accent/40 -mx-1 px-1 rounded-lg transition-colors cursor-pointer'
                )}
              >
                <Newspaper className="h-3.5 w-3.5 flex-shrink-0 mt-0.5 text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-foreground leading-relaxed">{n.title}</p>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <span className="text-[10px] text-muted-foreground">{n.source}</span>
                    <span className="text-[10px] text-muted-foreground">·</span>
                    <span className="text-[10px] text-muted-foreground">{n.time}</span>
                    {n.ticker && (
                      <span className="text-[10px] font-semibold text-primary">{n.ticker}</span>
                    )}
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>

        {/* Upcoming Events */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader
            title="Upcoming Events"
            action={
              <Link href="/events" className="text-xs text-primary hover:underline flex items-center gap-0.5">
                Calendar <ChevronRight className="h-3 w-3" />
              </Link>
            }
          />
          <div className="mt-3 divide-y divide-border">
            {(earnings ?? upcomingEvents).map((e, i) => {
              // Live earnings from API
              if (earnings) {
                const item = e as EarningsItem
                const d = new Date(item.date + 'T00:00:00')
                const month = d.toLocaleString('en-US', { month: 'short' })
                const day   = String(d.getDate())
                const timing = item.hour === 'amc' ? 'After Close' : item.hour === 'bmo' ? 'Before Open' : 'TBD'
                return (
                  <div key={i} className="flex items-start gap-3 py-2.5 first:pt-0">
                    <div className="flex flex-col items-center justify-center rounded-md bg-accent px-2 py-1.5 min-w-[40px] text-center flex-shrink-0">
                      <span className="text-[11px] font-bold text-foreground leading-tight">{day}</span>
                      <span className="text-[9px] text-muted-foreground">{month}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <EventTypeBadge type="earnings" />
                        <span className="text-[10px] font-semibold text-primary">In Portfolio</span>
                      </div>
                      <p className="text-xs font-medium text-foreground">
                        <span className="font-bold">{item.ticker}</span> — Earnings
                      </p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {timing}{item.eps_estimate != null ? ` · EPS est. $${item.eps_estimate.toFixed(2)}` : ''}
                      </p>
                    </div>
                  </div>
                )
              }
              // Mock data fallback
              const mock = e as typeof upcomingEvents[number]
              return (
                <div key={i} className="flex items-start gap-3 py-2.5 first:pt-0">
                  <div className="flex flex-col items-center justify-center rounded-md bg-accent px-2 py-1.5 min-w-[40px] text-center flex-shrink-0">
                    <span className="text-[11px] font-bold text-foreground leading-tight">{mock.date.split(' ')[1]}</span>
                    <span className="text-[9px] text-muted-foreground">{mock.date.split(' ')[0]}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                      <EventTypeBadge type={mock.type} />
                      {mock.inPortfolio && <span className="text-[10px] font-semibold text-primary">In Portfolio</span>}
                    </div>
                    <p className="text-xs font-medium text-foreground">
                      {mock.ticker && <span className="font-bold">{mock.ticker} — </span>}
                      {mock.description}
                    </p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{mock.timing}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Watchlist Movers */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader
            title="Watchlist Movers"
            action={
              <Link href="/watchlist" className="text-xs text-primary hover:underline flex items-center gap-0.5">
                View all <ChevronRight className="h-3 w-3" />
              </Link>
            }
          />
          <div className="mt-3 space-y-4">

            {/* Gainers */}
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2 flex items-center gap-1.5">
                <TrendingUp className="h-3 w-3 text-success" /> Gainers
              </p>
              <div className="space-y-2">
                {topMovers.gainers.map((s) => (
                  <div key={s.symbol} className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-semibold text-foreground">{s.symbol}</span>
                      <span className="text-[10px] text-muted-foreground ml-2">{formatCurrency(s.price)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <ScoreBadge score={s.score} />
                      <span className="text-xs font-semibold text-success min-w-[42px] text-right">+{s.change}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Losers */}
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2 flex items-center gap-1.5">
                <TrendingDown className="h-3 w-3 text-destructive" /> Losers
              </p>
              <div className="space-y-2">
                {topMovers.losers.map((s) => (
                  <div key={s.symbol} className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-semibold text-foreground">{s.symbol}</span>
                      <span className="text-[10px] text-muted-foreground ml-2">{formatCurrency(s.price)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <ScoreBadge score={s.score} />
                      <span className="text-xs font-semibold text-destructive min-w-[42px] text-right">{s.change}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Near Buy Range */}
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2">
                Near Buy Range
              </p>
              <div className="space-y-2">
                {topMovers.nearBuyRange.map((s) => (
                  <div key={s.symbol} className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <span className="text-xs font-semibold text-foreground">{s.symbol}</span>
                      <p className="text-[10px] text-muted-foreground">
                        {formatCurrency(s.price)} · buy below {formatCurrency(s.buyBelow)}
                      </p>
                    </div>
                    <span className="text-xs font-semibold text-success flex-shrink-0">+{s.upside}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Row 7: Allocation Drift / Rebalance ──────────────────────────────── */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <SectionHeader
          title="Allocation Drift & Rebalance"
          action={
            <Link href="/portfolio" className="text-xs text-primary hover:underline flex items-center gap-0.5">
              Full report <ChevronRight className="h-3 w-3" />
            </Link>
          }
        />
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-2 text-left font-semibold text-muted-foreground uppercase tracking-wide">Sector</th>
                <th className="pb-2 text-right font-semibold text-muted-foreground uppercase tracking-wide">Current</th>
                <th className="pb-2 text-right font-semibold text-muted-foreground uppercase tracking-wide">Target</th>
                <th className="pb-2 text-right font-semibold text-muted-foreground uppercase tracking-wide">Drift</th>
                <th className="hidden sm:table-cell pb-2 text-center font-semibold text-muted-foreground uppercase tracking-wide">Visual</th>
                <th className="pb-2 text-right font-semibold text-muted-foreground uppercase tracking-wide">Action</th>
              </tr>
            </thead>
            <tbody>
              {allocationDrift.map((row) => {
                const maxDrift = 6
                const halfBarPct = Math.min(Math.abs(row.drift) / maxDrift * 50, 50)
                return (
                  <tr key={row.sector} className="border-b border-border last:border-0">
                    <td className="py-3 font-medium text-foreground">{row.sector}</td>
                    <td className="py-3 text-right text-foreground">{row.current.toFixed(2)}%</td>
                    <td className="py-3 text-right text-muted-foreground">{row.target.toFixed(2)}%</td>
                    <td className={cn(
                      'py-3 text-right font-semibold',
                      row.drift >  1  && 'text-destructive',
                      row.drift < -1  && 'text-gold',
                      Math.abs(row.drift) <= 1 && 'text-success',
                    )}>
                      {row.drift > 0 ? '+' : ''}{row.drift.toFixed(2)}%
                    </td>
                    <td className="hidden sm:table-cell py-3 px-6">
                      <div className="flex items-center justify-center">
                        <div className="relative h-2 w-28 rounded-full bg-muted overflow-hidden">
                          <div className="absolute left-1/2 top-0 h-full w-px bg-border" />
                          <div
                            className={cn(
                              'absolute top-0 h-full rounded-full',
                              row.actionType === 'sell' ? 'right-1/2 bg-destructive/60' :
                              row.actionType === 'buy'  ? 'left-1/2 bg-success/60' :
                              'left-1/2 bg-muted-foreground/30'
                            )}
                            style={{ width: `${halfBarPct}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-3 text-right">
                      <span className={cn(
                        'inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide',
                        row.actionType === 'sell' && 'bg-destructive/10 text-destructive',
                        row.actionType === 'buy'  && 'bg-success/10 text-success',
                        row.actionType === 'hold' && 'bg-muted text-muted-foreground',
                      )}>
                        {row.action}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  )
}
