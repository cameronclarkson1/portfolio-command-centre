'use client'

import { 
  Brain, 
  Sparkles, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle,
  Calendar,
  Activity,
  Zap,
  Bell,
  BarChart3,
  Eye,
  Target,
  Building,
  ChevronRight,
} from 'lucide-react'
import { 
  SectionHeader, 
  StatusBadge,
  AlertCard,
  ProgressRing,
  formatCurrency,
} from '@/components/ui-components'
import {
  aiInsights,
  newsEvents as mockNews,
  earningsCalendar as mockEarnings,
  watchlist,
  portfolioData,
} from '@/lib/mock-data'
import { type LiveIntelligenceData, type EarningsItem } from '@/lib/api'
import { cn } from '@/lib/utils'

const defaultCommentary = {
  summary: "Markets showing resilience despite mixed economic data. Technology leading with AI-driven momentum while defensive sectors lag. Bond yields stabilizing after recent volatility.",
  regime: "Risk-On",
  confidence: 78,
  keyThemes: [
    "AI capex cycle accelerating",
    "Inflation trending toward target",
    "Fed likely to cut in September",
    "Earnings revisions positive",
  ],
}

const portfolioInsights = [
  { type: 'positive', title: 'Strong momentum in NVDA', description: 'Position up 42% YTD, consider taking partial profits above $900', priority: 'medium' },
  { type: 'warning', title: 'Concentration alert', description: 'Tech sector now 35% of portfolio, above your 30% limit', priority: 'high' },
  { type: 'opportunity', title: 'Dividend reinvestment', description: '$2,847 in dividends received this quarter available for reinvestment', priority: 'low' },
]

const watchlistAlerts = [
  { symbol: 'AMD', alert: 'Breaking above 200-day MA', type: 'bullish' },
  { symbol: 'TSLA', alert: 'Approaching support at $240', type: 'neutral' },
  { symbol: 'CRM', alert: 'RSI oversold, potential bounce', type: 'bullish' },
]

const institutionalActivity = [
  { symbol: 'NVDA', action: 'Accumulation', change: '+2.4%', institution: 'Vanguard' },
  { symbol: 'META', action: 'Distribution', change: '-1.2%', institution: 'BlackRock' },
  { symbol: 'GOOGL', action: 'Accumulation', change: '+1.8%', institution: 'State Street' },
]

const suggestedActions = [
  { action: 'Rebalance', description: 'Reduce tech exposure by 5%', urgency: 'high', icon: Target },
  { action: 'Review', description: 'UNH approaching stop-loss level', urgency: 'medium', icon: Eye },
  { action: 'Opportunity', description: 'Add AMD on pullback to $155', urgency: 'low', icon: Zap },
]

function fmtEarningsDate(iso: string): string {
  const d = new Date(iso + 'T12:00:00Z')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
}

function fmtHour(hour: string): string {
  if (hour === 'amc') return 'After Close'
  if (hour === 'bmo') return 'Before Open'
  return hour.toUpperCase()
}

export function IntelligencePage({ liveData }: { liveData?: LiveIntelligenceData }) {
  const newsEvents = liveData?.newsEvents ?? mockNews
  const liveEarnings: EarningsItem[] | null = liveData?.earnings ?? null

  const marketCommentary = liveData?.marketRegime
    ? {
        ...defaultCommentary,
        regime:     liveData.marketRegime.label,
        confidence: liveData.marketRegime.aiConviction,
        summary:    liveData.marketRegime.summary || defaultCommentary.summary,
      }
    : defaultCommentary

  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary">
            <Brain className="h-6 w-6 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Intelligence</h1>
            <p className="text-sm text-muted-foreground">AI-powered market insights</p>
          </div>
        </div>
        <StatusBadge status="neutral">
          <Sparkles className="h-3 w-3 mr-1" /> Updated 5 min ago
        </StatusBadge>
      </div>

      {/* AI Market Commentary */}
      <div className="rounded-xl border border-border bg-gradient-to-br from-primary/5 to-transparent p-5 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-3">
              <Brain className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold text-foreground">AI Market Commentary</h2>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">{marketCommentary.summary}</p>
            
            <div className="mt-4 flex flex-wrap gap-2">
              {marketCommentary.keyThemes.map((theme, i) => (
                <span key={i} className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                  {theme}
                </span>
              ))}
            </div>
          </div>
          <div className="hidden lg:block">
            <div className="text-center">
              <ProgressRing value={marketCommentary.confidence} size={72} strokeWidth={5} />
              <p className="text-xs text-muted-foreground mt-2">Confidence</p>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-border/50 flex items-center gap-6">
          <div>
            <p className="text-xs text-muted-foreground">Market Regime</p>
            <p className="text-sm font-semibold text-success">{marketCommentary.regime}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Sentiment</p>
            <p className="text-sm font-semibold text-foreground">Cautiously Bullish</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Volatility</p>
            <p className="text-sm font-semibold text-foreground">Low</p>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Portfolio Insights */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader 
              title="Portfolio Insights"
              action={
                <span className="flex items-center gap-1 text-xs text-primary hover:underline cursor-pointer">
                  View all <ChevronRight className="h-3 w-3" />
                </span>
              }
            />
            <div className="mt-3 space-y-3">
              {portfolioInsights.map((insight, index) => (
                <div
                  key={index}
                  className={cn(
                    'rounded-lg border p-4 transition-colors hover:bg-accent/30',
                    insight.type === 'positive' && 'border-success/30 bg-success/5',
                    insight.type === 'warning' && 'border-gold/30 bg-gold/5',
                    insight.type === 'opportunity' && 'border-primary/30 bg-primary/5'
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      'mt-0.5 flex h-7 w-7 items-center justify-center rounded-lg',
                      insight.type === 'positive' && 'bg-success/20',
                      insight.type === 'warning' && 'bg-gold/20',
                      insight.type === 'opportunity' && 'bg-primary/20'
                    )}>
                      {insight.type === 'positive' && <TrendingUp className="h-4 w-4 text-success" />}
                      {insight.type === 'warning' && <AlertTriangle className="h-4 w-4 text-gold" />}
                      {insight.type === 'opportunity' && <Zap className="h-4 w-4 text-primary" />}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-foreground">{insight.title}</p>
                        <StatusBadge 
                          status={insight.priority === 'high' ? 'negative' : insight.priority === 'medium' ? 'warning' : 'neutral'}
                        >
                          {insight.priority}
                        </StatusBadge>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{insight.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Suggested Actions */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Suggested Actions" />
            <div className="mt-3 grid gap-3 lg:grid-cols-3">
              {suggestedActions.map((action, index) => (
                <div 
                  key={index}
                  className={cn(
                    'rounded-lg border p-4 cursor-pointer transition-all hover:shadow-md',
                    action.urgency === 'high' && 'border-destructive/30 hover:border-destructive/50',
                    action.urgency === 'medium' && 'border-gold/30 hover:border-gold/50',
                    action.urgency === 'low' && 'border-border hover:border-primary/50'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      'flex h-9 w-9 items-center justify-center rounded-lg',
                      action.urgency === 'high' && 'bg-destructive/10',
                      action.urgency === 'medium' && 'bg-gold/10',
                      action.urgency === 'low' && 'bg-primary/10'
                    )}>
                      <action.icon className={cn(
                        'h-4 w-4',
                        action.urgency === 'high' && 'text-destructive',
                        action.urgency === 'medium' && 'text-gold',
                        action.urgency === 'low' && 'text-primary'
                      )} />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{action.action}</p>
                      <p className="text-xs text-muted-foreground">{action.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* News Sentiment */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader 
              title="News Sentiment Analysis"
              action={<Activity className="h-4 w-4 text-muted-foreground" />}
            />
            <div className="mt-3 divide-y divide-border">
              {newsEvents.map((news, index) => (
                <div key={index} className="py-3 first:pt-0 last:pb-0">
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      'mt-1 flex h-6 w-6 items-center justify-center rounded-full',
                      news.sentiment === 'positive' && 'bg-success/10',
                      news.sentiment === 'negative' && 'bg-destructive/10',
                      news.sentiment === 'neutral' && 'bg-muted'
                    )}>
                      {news.sentiment === 'positive' && <TrendingUp className="h-3 w-3 text-success" />}
                      {news.sentiment === 'negative' && <TrendingDown className="h-3 w-3 text-destructive" />}
                      {news.sentiment === 'neutral' && <Activity className="h-3 w-3 text-muted-foreground" />}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm text-foreground leading-tight">{news.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-muted-foreground">{news.source}</span>
                        <span className="text-xs text-muted-foreground">{news.time}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Watchlist Alerts */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader 
              title="Watchlist Alerts"
              action={<Bell className="h-4 w-4 text-muted-foreground" />}
            />
            <div className="mt-3 space-y-2">
              {watchlistAlerts.map((alert, index) => (
                <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-accent/30">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-xs font-bold text-foreground">
                      {alert.symbol.slice(0, 2)}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{alert.symbol}</p>
                      <p className="text-xs text-muted-foreground">{alert.alert}</p>
                    </div>
                  </div>
                  <div className={cn(
                    'h-2 w-2 rounded-full',
                    alert.type === 'bullish' && 'bg-success',
                    alert.type === 'bearish' && 'bg-destructive',
                    alert.type === 'neutral' && 'bg-gold'
                  )} />
                </div>
              ))}
            </div>
          </div>

          {/* Earnings Calendar */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader
              title="Upcoming Earnings"
              action={<Calendar className="h-4 w-4 text-muted-foreground" />}
            />
            <div className="mt-3 space-y-2">
              {liveEarnings !== null ? (
                liveEarnings.length === 0
                  ? <p className="text-xs text-muted-foreground py-2">No upcoming earnings found.</p>
                  : liveEarnings.slice(0, 6).map((e, i) => (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-xs font-bold text-foreground">
                          {e.ticker.slice(0, 2)}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-foreground">{e.ticker}</p>
                          <p className="text-xs text-muted-foreground">{fmtEarningsDate(e.date)} · {fmtHour(e.hour)}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">Est. EPS</p>
                        <p className="text-sm font-medium text-foreground">
                          {e.eps_estimate != null ? `$${e.eps_estimate.toFixed(2)}` : '—'}
                        </p>
                      </div>
                    </div>
                  ))
              ) : (
                mockEarnings.map((earning, index) => (
                  <div key={index} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-xs font-bold text-foreground">
                        {earning.symbol.slice(0, 2)}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-foreground">{earning.symbol}</p>
                        <p className="text-xs text-muted-foreground">{earning.date} · {earning.time}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-muted-foreground">Est. EPS</p>
                      <p className="text-sm font-medium text-foreground">{earning.estimate}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Institutional Activity */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader 
              title="Institutional Activity"
              action={<Building className="h-4 w-4 text-muted-foreground" />}
            />
            <div className="mt-3 space-y-2">
              {institutionalActivity.map((activity, index) => (
                <div key={index} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-lg text-xs font-bold',
                      activity.action === 'Accumulation' ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'
                    )}>
                      {activity.symbol.slice(0, 2)}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{activity.symbol}</p>
                      <p className="text-xs text-muted-foreground">{activity.institution}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={cn(
                      'text-sm font-medium',
                      activity.action === 'Accumulation' ? 'text-success' : 'text-destructive'
                    )}>
                      {activity.change}
                    </p>
                    <p className="text-xs text-muted-foreground">{activity.action}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Risk Warnings */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Risk Warnings" />
            <div className="mt-3 space-y-2">
              <AlertCard
                severity="high"
                title="Sector Concentration"
                description="Technology at 35.2% exceeds your 30% limit"
              />
              <AlertCard
                severity="medium"
                title="Elevated Volatility"
                description="VIX approaching 18, consider hedges"
              />
              <AlertCard
                severity="low"
                title="Currency Exposure"
                description="23% international exposure unhedged"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
