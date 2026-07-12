'use client'

import { 
  TrendingUp, 
  TrendingDown, 
  Clock,
  Newspaper,
  Globe,
  BarChart3,
  Activity,
} from 'lucide-react'
import { 
  SectionHeader, 
  StatusBadge,
  Sparkline,
  formatCurrency,
  formatNumber,
} from '@/components/ui-components'
import {
  marketIndices    as mockIndices,
  sectorPerformance as mockSectors,
  commodities      as mockCommodities,
  bondYields       as mockYields,
  crypto           as mockCrypto,
  newsEvents       as mockNews,
} from '@/lib/mock-data'
import { type LiveMarketsData } from '@/lib/api'

// Market open/closed based on US Eastern Time (9:30–16:00 ET, Mon–Fri)
function getMarketOpen(): boolean {
  const etDate     = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }))
  const day        = etDate.getDay()
  const h          = etDate.getHours()
  const m          = etDate.getMinutes()
  const isWeekday   = day >= 1 && day <= 5
  const afterOpen   = h > 9  || (h === 9  && m >= 30)
  const beforeClose = h < 16
  return isWeekday && afterOpen && beforeClose
}
import { cn } from '@/lib/utils'

const breadthIndicators = [
  { name: 'Advance/Decline', value: 1.42, status: 'positive' },
  { name: 'New Highs/Lows', value: 2.8, status: 'positive' },
  { name: '% Above 200 DMA', value: 68, status: 'positive' },
  { name: '% Above 50 DMA', value: 52, status: 'neutral' },
]

const fallbackMacro = [
  { name: 'GDP Growth (QoQ)', value: '2.8%', trend: 'up'   as const },
  { name: 'Inflation (CPI YoY)', value: '3.2%', trend: 'down' as const },
  { name: 'Unemployment', value: '3.9%', trend: 'flat' as const },
  { name: 'Fed Funds Rate', value: '5.25%', trend: 'flat' as const },
]

export function MarketsPage({ liveData }: { liveData?: LiveMarketsData }) {
  const marketIndices     = liveData?.marketIndices     ?? mockIndices
  const sectorPerformance = liveData?.sectorPerformance ?? mockSectors
  const newsEvents        = liveData?.newsEvents        ?? mockNews
  const bondYields        = liveData?.bondYields        ?? mockYields
  const macroIndicators   = liveData?.macroIndicators   ?? fallbackMacro
  const commodities       = liveData?.commodities       ?? mockCommodities
  const crypto            = liveData?.crypto            ?? mockCrypto
  const fx                = liveData?.fx                ?? null
  const marketOpen        = getMarketOpen()
  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Markets</h1>
          <p className="mt-1 text-sm text-muted-foreground">Global market overview and analysis</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={cn(
            'flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium',
            marketOpen
              ? 'bg-success/10 text-success'
              : 'bg-muted text-muted-foreground'
          )}>
            <span className={cn(
              'h-2 w-2 rounded-full animate-pulse',
              marketOpen ? 'bg-success' : 'bg-muted-foreground'
            )} />
            {marketOpen ? 'Market Open' : 'Market Closed'}
          </div>
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {marketOpen ? 'Closes at 04:00 PM ET' : 'Opens 09:30 AM ET weekdays'}
          </span>
        </div>
      </div>

      {/* Major Indices */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <SectionHeader title="Major Indices" />
        <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-5">
          {marketIndices.map((index) => (
            <div 
              key={index.symbol}
              className="rounded-lg border border-border bg-accent/20 p-3 hover:bg-accent/40 transition-colors"
            >
              <p className="text-xs text-muted-foreground">{index.name}</p>
              <p className="text-lg font-semibold text-foreground mt-1">{formatNumber(index.value, 2)}</p>
              <div className="flex items-center gap-2 mt-1">
                {index.change >= 0 
                  ? <TrendingUp className="h-3 w-3 text-success" />
                  : <TrendingDown className="h-3 w-3 text-destructive" />
                }
                <span className={cn(
                  'text-xs font-medium',
                  index.change >= 0 ? 'text-success' : 'text-destructive'
                )}>
                  {index.change >= 0 ? '+' : ''}{index.change.toFixed(2)}%
                </span>
                <span className="text-xs text-muted-foreground">
                  YTD: {index.ytd != null ? `${index.ytd > 0 ? '+' : ''}${index.ytd}%` : '—'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Sector Heatmap */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader 
              title="Sector Performance"
              action={
                <div className="flex gap-1">
                  {['1D', '1W', '1M'].map((period, i) => (
                    <button
                      key={period}
                      className={cn(
                        'px-2 py-1 text-xs font-medium rounded-md transition-colors',
                        i === 0 ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-accent'
                      )}
                    >
                      {period}
                    </button>
                  ))}
                </div>
              }
            />
            <div className="mt-4 grid grid-cols-3 lg:grid-cols-4 gap-2">
              {sectorPerformance.map((sector) => {
                const isPositive = sector.daily >= 0
                return (
                  <div
                    key={sector.sector}
                    className={cn(
                      'rounded-lg p-3 text-center transition-all hover:scale-105',
                      isPositive ? 'bg-success/10' : 'bg-destructive/10'
                    )}
                  >
                    <p className="text-xs text-muted-foreground truncate">{sector.sector}</p>
                    <p className={cn(
                      'text-sm font-semibold mt-1',
                      isPositive ? 'text-success' : 'text-destructive'
                    )}>
                      {isPositive ? '+' : ''}{sector.daily.toFixed(2)}%
                    </p>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Market Breadth */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader
              title="Market Breadth"
              action={<span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground bg-muted px-2 py-0.5 rounded">Sample data</span>}
            />
            <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
              {breadthIndicators.map((indicator) => (
                <div key={indicator.name} className="text-center">
                  <div className={cn(
                    'mx-auto flex h-12 w-12 items-center justify-center rounded-full',
                    indicator.status === 'positive' && 'bg-success/10',
                    indicator.status === 'negative' && 'bg-destructive/10',
                    indicator.status === 'neutral' && 'bg-gold/10'
                  )}>
                    <Activity className={cn(
                      'h-5 w-5',
                      indicator.status === 'positive' && 'text-success',
                      indicator.status === 'negative' && 'text-destructive',
                      indicator.status === 'neutral' && 'text-gold'
                    )} />
                  </div>
                  <p className="mt-2 text-lg font-semibold text-foreground">
                    {typeof indicator.value === 'number' && indicator.value < 10 
                      ? indicator.value.toFixed(2)
                      : `${indicator.value}%`
                    }
                  </p>
                  <p className="text-xs text-muted-foreground">{indicator.name}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Macro Indicators */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Macro Indicators" />
            <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
              {macroIndicators.map((indicator) => (
                <div key={indicator.name} className="rounded-lg bg-accent/30 p-3">
                  <p className="text-xs text-muted-foreground">{indicator.name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <p className="text-lg font-semibold text-foreground">{indicator.value}</p>
                    {indicator.trend === 'up' && <TrendingUp className="h-3 w-3 text-success" />}
                    {indicator.trend === 'down' && <TrendingDown className="h-3 w-3 text-destructive" />}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* News Feed */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader 
              title="Market News"
              action={<Newspaper className="h-4 w-4 text-muted-foreground" />}
            />
            <div className="mt-3 divide-y divide-border">
              {newsEvents.map((news, index) => (
                <div key={index} className="py-3 first:pt-0 last:pb-0">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-foreground leading-tight hover:text-primary cursor-pointer transition-colors">
                        {news.title}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-muted-foreground">{news.source}</span>
                        <span className="text-xs text-muted-foreground">{news.time}</span>
                      </div>
                    </div>
                    <StatusBadge 
                      status={news.sentiment === 'positive' ? 'positive' : news.sentiment === 'negative' ? 'negative' : 'neutral'}
                    >
                      {news.sentiment}
                    </StatusBadge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Bond Yields */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Treasury Yields" />
            <div className="mt-3 space-y-3">
              {bondYields.map((bond) => (
                <div key={bond.name} className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">{bond.name}</span>
                  <span className="text-sm font-semibold text-foreground">{bond.yield.toFixed(2)}%</span>
                </div>
              ))}
            </div>
            {bondYields.length >= 2 && (
              <div className="mt-4 pt-4 border-t border-border">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">2s/10s Spread</span>
                  <span className={cn(
                    'text-xs font-medium',
                    bondYields[1].yield - bondYields[0].yield < 0 ? 'text-destructive' : 'text-foreground'
                  )}>
                    {(bondYields[1].yield - bondYields[0].yield).toFixed(2)}%
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Commodities */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Commodities" />
            <div className="mt-3 space-y-3">
              {commodities.map((commodity) => (
                <div key={commodity.symbol} className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-foreground">{commodity.name}</span>
                    <span className="text-xs text-muted-foreground ml-1">{commodity.unit}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-foreground">
                      {commodity.price != null ? `$${commodity.price.toFixed(2)}` : '—'}
                    </span>
                    {commodity.change != null && (
                      <span className={cn('text-xs', commodity.change >= 0 ? 'text-success' : 'text-destructive')}>
                        {commodity.change >= 0 ? '+' : ''}{commodity.change.toFixed(2)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Crypto */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Crypto" />
            <div className="mt-3 space-y-3">
              {crypto.map((coin) => (
                <div key={coin.symbol} className="flex items-center justify-between p-3 rounded-lg bg-accent/30">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-xs font-bold text-foreground">
                      {coin.symbol}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{coin.name}</p>
                      <p className="text-xs text-muted-foreground">{coin.symbol}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-foreground">
                      {coin.price != null ? formatCurrency(coin.price) : '—'}
                    </p>
                    {coin.change != null ? (
                      <p className={cn('text-xs', coin.change >= 0 ? 'text-success' : 'text-destructive')}>
                        {coin.change >= 0 ? '+' : ''}{coin.change.toFixed(2)}%
                      </p>
                    ) : (
                      <p className="text-xs text-muted-foreground">—</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Currency */}
          {fx && fx.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
              <SectionHeader title="Currency" action={<Globe className="h-4 w-4 text-muted-foreground" />} />
              <div className="mt-3 space-y-3">
                {fx.map((pair) => (
                  <div key={pair.label} className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">{pair.label}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-foreground">
                        {pair.price != null ? pair.price.toString() : '—'}
                      </span>
                      {pair.change_pct != null && (
                        <span className={cn('text-xs', pair.change_pct >= 0 ? 'text-success' : 'text-destructive')}>
                          {pair.change_pct >= 0 ? '+' : ''}{pair.change_pct.toFixed(2)}%
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
