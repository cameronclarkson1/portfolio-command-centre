'use client'

import {
  Shield,
  AlertTriangle,
  TrendingDown,
  Activity,
  Target,
  BarChart3,
  Zap,
  CheckCircle2,
  Info,
} from 'lucide-react'
import {
  SectionHeader,
  StatusBadge,
  AlertCard,
  ProgressRing,
  DataRow,
  formatCurrency,
} from '@/components/ui-components'
import { riskMetrics, stressTests, portfolioData } from '@/lib/mock-data'
import { type PortfolioRiskData } from '@/lib/api'
import { cn } from '@/lib/utils'

const correlationData = [
  { asset: 'SPY', correlation: 0.89 },
  { asset: 'QQQ', correlation: 0.92 },
  { asset: 'IWM', correlation: 0.72 },
  { asset: 'AGG', correlation: -0.12 },
  { asset: 'GLD', correlation: 0.08 },
]

function severityTextColour(s: 'info' | 'warning' | 'critical') {
  if (s === 'critical') return 'text-destructive'
  if (s === 'warning')  return 'text-gold-foreground'
  return 'text-muted-foreground'
}

function severityCardClass(s: 'info' | 'warning' | 'critical') {
  if (s === 'critical') return 'border-destructive/20 bg-destructive/5'
  if (s === 'warning')  return 'border-gold/20 bg-gold/5'
  return 'border-border bg-muted/30'
}

function scoreLabel(score: number) {
  if (score >= 80) return 'Low Risk'
  if (score >= 60) return 'Moderate'
  if (score >= 40) return 'Moderate-High'
  return 'High Risk'
}

export function RiskPage({ apiData }: { apiData: PortfolioRiskData | null }) {
  const healthScore = apiData?.health_score ?? portfolioData.portfolioHealthScore
  const beta        = apiData?.metrics.portfolio_beta ?? riskMetrics.portfolioBeta
  const alerts      = apiData?.alerts ?? []
  const categories  = apiData?.categories ?? []
  const sectorMap   = apiData?.sector_weights ?? {}
  const isLive      = apiData?.prices_live ?? false

  const sectors = Object.entries(sectorMap).sort((a, b) => b[1] - a[1])

  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-destructive/10">
            <Shield className="h-6 w-6 text-destructive" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Risk Centre</h1>
            <p className="text-sm text-muted-foreground">Portfolio risk analysis and monitoring</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {alerts.length > 0
            ? <StatusBadge status="warning">
                <AlertTriangle className="h-3 w-3 mr-1" />
                {alerts.length} Alert{alerts.length !== 1 ? 's' : ''}
              </StatusBadge>
            : <StatusBadge status="positive">
                <CheckCircle2 className="h-3 w-3 mr-1" /> All Clear
              </StatusBadge>
          }
          {isLive && (
            <span className="text-xs text-success bg-success/10 px-2 py-1 rounded-full font-medium">Live</span>
          )}
        </div>
      </div>

      {/* Banners */}
      {apiData && !isLive && (
        <div className="flex items-center gap-2 rounded-lg border border-gold/30 bg-gold/5 px-4 py-2.5 text-sm text-gold-foreground">
          <Info className="h-4 w-4 shrink-0" />
          Market is closed — risk metrics based on last known prices.
        </div>
      )}
      {!apiData && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-2.5 text-sm text-destructive">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          Could not reach the API — showing snapshot data.
        </div>
      )}

      {/* 4 stat cards */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Beta</span>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className="mt-2 text-2xl font-semibold text-foreground">{beta.toFixed(2)}</p>
          <p className={cn('mt-1 text-xs', beta > 1 ? 'text-gold-foreground' : 'text-success')}>
            {beta > 1 ? 'Above market' : 'Below market'}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Volatility</span>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className="mt-2 text-2xl font-semibold text-foreground">
            {apiData?.metrics.volatility != null ? `${apiData.metrics.volatility}%` : '—'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">Annualized · 3M</p>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Sharpe</span>
            <Target className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className={cn(
            'mt-2 text-2xl font-semibold',
            apiData?.metrics.sharpe_ratio != null
              ? apiData.metrics.sharpe_ratio >= 1 ? 'text-success' : apiData.metrics.sharpe_ratio >= 0 ? 'text-foreground' : 'text-destructive'
              : 'text-foreground'
          )}>
            {apiData?.metrics.sharpe_ratio != null ? apiData.metrics.sharpe_ratio.toFixed(2) : '—'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">Risk-adjusted · 3M</p>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Max Drawdown</span>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className={cn(
            'mt-2 text-2xl font-semibold',
            apiData?.metrics.max_drawdown != null && apiData.metrics.max_drawdown < 0 ? 'text-destructive' : 'text-foreground'
          )}>
            {apiData?.metrics.max_drawdown != null ? `${apiData.metrics.max_drawdown}%` : '—'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">3M peak-to-trough</p>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-6">

          {/* Risk Categories */}
          {categories.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
              <SectionHeader title="Risk Categories" />
              <div className="mt-4 space-y-3">
                {categories.map((cat) => (
                  <div key={cat.name} className={cn('rounded-lg border p-3', severityCardClass(cat.severity))}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium text-foreground">{cat.name}</span>
                          <span className={cn(
                            'text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded-full border',
                            cat.severity === 'critical' && 'border-destructive/30 bg-destructive/10 text-destructive',
                            cat.severity === 'warning'  && 'border-gold/30 bg-gold/10 text-gold-foreground',
                            cat.severity === 'info'     && 'border-border bg-muted text-muted-foreground',
                          )}>
                            {cat.severity}
                          </span>
                        </div>
                        <p className="mt-0.5 text-xs text-muted-foreground">{cat.metric}</p>
                        {cat.description && (
                          <p className="mt-1 text-xs text-muted-foreground">{cat.description}</p>
                        )}
                        {cat.action && cat.action !== 'OK' && (
                          <p className="mt-1.5 text-xs font-medium text-foreground">→ {cat.action}</p>
                        )}
                      </div>
                      <div className="text-right shrink-0">
                        <p className={cn('text-xl font-semibold', severityTextColour(cat.severity))}>
                          {cat.score}
                        </p>
                        <p className="text-[10px] text-muted-foreground">score</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sector Concentration */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Sector Concentration" />
            <div className="mt-4 space-y-3">
              {(sectors.length > 0 ? sectors : []).slice(0, 8).map(([name, pct]) => {
                const isRisky = pct > 30
                return (
                  <div key={name}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-foreground">{name}</span>
                      <div className="flex items-center gap-2">
                        <span className={cn('text-sm font-medium', isRisky ? 'text-destructive' : 'text-foreground')}>
                          {pct.toFixed(2)}%
                        </span>
                        {isRisky && <AlertTriangle className="h-3 w-3 text-destructive" />}
                      </div>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={cn('h-full rounded-full', isRisky ? 'bg-destructive' : 'bg-primary')}
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Stress Tests */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader
              title="Stress Test Scenarios"
              action={<Zap className="h-4 w-4 text-muted-foreground" />}
            />
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              {stressTests.map((test) => (
                <div key={test.scenario} className="rounded-lg border border-border bg-accent/20 p-4">
                  <p className="text-sm font-medium text-foreground">{test.scenario}</p>
                  <div className="mt-2 flex items-end justify-between">
                    <div>
                      <p className="text-2xl font-semibold text-destructive">{test.impact}%</p>
                      <p className="text-xs text-muted-foreground">Projected loss</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-foreground">
                        {formatCurrency(portfolioData.totalValue * (Math.abs(test.impact) / 100) * -1, true)}
                      </p>
                      <p className="text-xs text-muted-foreground">Recovery: {test.recovery}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-muted-foreground text-right">Historical scenario estimates only</p>
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Health Score ring */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Portfolio Health Score" />
            <div className="mt-4 flex flex-col items-center">
              <ProgressRing value={healthScore} size={100} strokeWidth={8} />
              <p className="mt-3 text-lg font-semibold text-foreground">{scoreLabel(healthScore)}</p>
              <p className="text-xs text-muted-foreground">
                Based on {isLive ? 'live' : 'snapshot'} data
              </p>
            </div>
            <div className="mt-4 pt-4 border-t border-border grid grid-cols-3 gap-2 text-center">
              <div>
                <p className="text-xs text-muted-foreground">Low</p>
                <div className="mt-1 h-1.5 bg-success rounded-full" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Medium</p>
                <div className="mt-1 h-1.5 bg-gold rounded-full" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">High</p>
                <div className="mt-1 h-1.5 bg-destructive rounded-full" />
              </div>
            </div>
          </div>

          {/* Active Alerts */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Active Alerts" />
            <div className="mt-3 space-y-2">
              {alerts.length > 0
                ? alerts.map((alert, i) => (
                    <AlertCard
                      key={i}
                      severity={alert.severity}
                      title={alert.title}
                      description={alert.description}
                    />
                  ))
                : (
                  <div className="flex items-center gap-2 py-3 text-sm text-success">
                    <CheckCircle2 className="h-4 w-4" />
                    No active risk alerts
                  </div>
                )
              }
            </div>
          </div>

          {/* Risk Metrics */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Risk Metrics" />
            <div className="mt-3 divide-y divide-border">
              <DataRow label="Portfolio Beta"    value={beta.toFixed(2)} />
              <DataRow label="Sortino Ratio"     value={riskMetrics.sortinoRatio > 0 ? riskMetrics.sortinoRatio.toFixed(2) : '—'} />
              <DataRow label="VaR (95%)"         value={riskMetrics.var95 !== 0 ? formatCurrency(riskMetrics.var95) : '—'} />
              <DataRow label="Corr. to SPY"      value={riskMetrics.correlationToSPY > 0 ? riskMetrics.correlationToSPY.toFixed(2) : '—'} />
              <DataRow label="Cash"              value={apiData ? `${apiData.metrics.cash_pct.toFixed(2)}%` : '—'} />
              <DataRow label="Holdings"          value={apiData ? `${apiData.metrics.num_holdings}` : '—'} />
            </div>
          </div>

          {/* Correlation (estimates) */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Portfolio Correlation" />
            <div className="mt-3 space-y-2">
              {correlationData.map((item) => (
                <div key={item.asset} className="flex items-center justify-between py-1.5">
                  <span className="text-sm text-muted-foreground">{item.asset}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={cn(
                          'h-full rounded-full',
                          item.correlation > 0.5 ? 'bg-primary' : item.correlation < 0 ? 'bg-success' : 'bg-gold'
                        )}
                        style={{ width: `${Math.abs(item.correlation) * 100}%` }}
                      />
                    </div>
                    <span className={cn(
                      'text-xs font-medium w-10 text-right',
                      item.correlation > 0.7 ? 'text-destructive' : item.correlation < 0 ? 'text-success' : 'text-foreground'
                    )}>
                      {item.correlation.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-muted-foreground text-right">Estimates only</p>
          </div>
        </div>
      </div>
    </div>
  )
}
