'use client'

import { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight, Minus, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react'

// ── MetricCard ───────────────────────────────────────────────────────────────

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  change?: number
  changeLabel?: string
  icon?: ReactNode
  className?: string
  compact?: boolean
}

export function MetricCard({ title, value, subtitle, change, changeLabel, icon, className, compact }: MetricCardProps) {
  const isPositive = change !== undefined && change > 0
  const isNegative = change !== undefined && change < 0

  return (
    <div className={cn(
      'rounded-xl border border-border bg-card p-4 shadow-sm transition-shadow hover:shadow-md',
      compact && 'p-3',
      className
    )}>
      <div className="flex items-center justify-between">
        <span className={cn('text-xs font-medium text-muted-foreground uppercase tracking-wide', compact && 'text-[10px]')}>
          {title}
        </span>
        {icon && <span className="text-muted-foreground">{icon}</span>}
      </div>
      <div className={cn('mt-2 text-2xl font-semibold tracking-tight text-foreground', compact && 'mt-1 text-xl')}>
        {value}
      </div>
      {subtitle && (
        <div className="text-xs text-muted-foreground mt-0.5">{subtitle}</div>
      )}
      {change !== undefined && (
        <div className="mt-1 flex items-center gap-1">
          {isPositive && <ArrowUpRight className="h-3.5 w-3.5 text-success" />}
          {isNegative && <ArrowDownRight className="h-3.5 w-3.5 text-destructive" />}
          {!isPositive && !isNegative && <Minus className="h-3.5 w-3.5 text-muted-foreground" />}
          <span className={cn(
            'text-xs font-medium',
            isPositive && 'text-success',
            isNegative && 'text-destructive',
            !isPositive && !isNegative && 'text-muted-foreground'
          )}>
            {isPositive ? '+' : ''}{change.toFixed(2)}%
          </span>
          {changeLabel && <span className="text-xs text-muted-foreground">{changeLabel}</span>}
        </div>
      )}
    </div>
  )
}

// ── StatusBadge ───────────────────────────────────────────────────────────────

interface StatusBadgeProps {
  status: 'positive' | 'negative' | 'neutral' | 'warning'
  children: ReactNode
  className?: string
}

export function StatusBadge({ status, children, className }: StatusBadgeProps) {
  return (
    <span className={cn(
      'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
      status === 'positive' && 'bg-success/10 text-success',
      status === 'negative' && 'bg-destructive/10 text-destructive',
      status === 'neutral'  && 'bg-muted text-muted-foreground',
      status === 'warning'  && 'bg-gold/10 text-gold',
      className
    )}>
      {children}
    </span>
  )
}

// ── SectionHeader ─────────────────────────────────────────────────────────────

interface SectionHeaderProps {
  title: string
  action?: ReactNode
  className?: string
}

export function SectionHeader({ title, action, className }: SectionHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between', className)}>
      <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      {action}
    </div>
  )
}

// ── DataRow ───────────────────────────────────────────────────────────────────

interface DataRowProps {
  label: string
  value: string | number
  change?: number
  className?: string
}

export function DataRow({ label, value, change, className }: DataRowProps) {
  const isPositive = change !== undefined && change > 0
  const isNegative = change !== undefined && change < 0

  return (
    <div className={cn('flex items-center justify-between py-2', className)}>
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-foreground">{value}</span>
        {change !== undefined && (
          <span className={cn(
            'text-xs font-medium',
            isPositive && 'text-success',
            isNegative && 'text-destructive',
            !isPositive && !isNegative && 'text-muted-foreground'
          )}>
            {isPositive ? '+' : ''}{change.toFixed(2)}%
          </span>
        )}
      </div>
    </div>
  )
}

// ── Sparkline ─────────────────────────────────────────────────────────────────

interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  className?: string
  positive?: boolean
}

export function Sparkline({ data, width = 60, height = 20, className, positive }: SparklineProps) {
  if (!data || data.length < 2) return null
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width
    const y = height - ((v - min) / range) * height
    return `${x},${y}`
  }).join(' ')
  const trend = data[data.length - 1] > data[0]
  const color = positive !== undefined
    ? (positive ? 'var(--success)' : 'var(--destructive)')
    : (trend ? 'var(--success)' : 'var(--destructive)')
  return (
    <svg width={width} height={height} className={className}>
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={points} />
    </svg>
  )
}

// ── RatingBadge ───────────────────────────────────────────────────────────────
// Handles both the 3-level valuation labels (Buy/Hold/Sell) and the
// 7-level composite score labels used by the watchlist and scoring engine.

interface RatingBadgeProps {
  rating: string
  className?: string
}

export function RatingBadge({ rating, className }: RatingBadgeProps) {
  const r = rating.toLowerCase()
  const style =
    r === 'strong buy'
      ? 'bg-success/15 text-success border border-success/30'
    : r === 'buy'
      ? 'bg-success/10 text-success border border-success/20'
    : r === 'accumulate'
      ? 'bg-primary/10 text-primary border border-primary/30'
    : r === 'hold / watchlist' || r === 'hold'
      ? 'bg-gold/10 text-gold-foreground border border-gold/30'
    : r === 'reduce'
      ? 'bg-orange-500/10 text-orange-400 border border-orange-500/30'
    : r === 'sell'
      ? 'bg-destructive/10 text-destructive border border-destructive/30'
    : r === 'strong sell'
      ? 'bg-destructive/15 text-destructive border border-destructive/40'
    : 'bg-muted text-muted-foreground border border-border'

  return (
    <span className={cn(
      'inline-flex items-center rounded-md px-2 py-1 text-xs font-semibold',
      style,
      className
    )}>
      {rating}
    </span>
  )
}

// ── ProgressRing ──────────────────────────────────────────────────────────────

interface ProgressRingProps {
  value: number
  size?: number
  strokeWidth?: number
  className?: string
}

export function ProgressRing({ value, size = 48, strokeWidth = 4, className }: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (value / 100) * circumference
  const getColor = (v: number) =>
    v >= 80 ? 'var(--success)' : v >= 60 ? 'var(--gold)' : v >= 40 ? 'var(--chart-4)' : 'var(--destructive)'

  return (
    <div className={cn('relative', className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--muted)" strokeWidth={strokeWidth} />
        <circle
          cx={size / 2} cy={size / 2} r={radius} fill="none"
          stroke={getColor(value)} strokeWidth={strokeWidth}
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round" className="transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs font-semibold text-foreground">{value}</span>
      </div>
    </div>
  )
}

// ── AlertCard ─────────────────────────────────────────────────────────────────

interface AlertCardProps {
  severity: 'high' | 'medium' | 'low'
  title: string
  description: string
  className?: string
}

export function AlertCard({ severity, title, description, className }: AlertCardProps) {
  return (
    <div className={cn(
      'rounded-lg border p-3',
      severity === 'high'   && 'border-destructive/30 bg-destructive/5',
      severity === 'medium' && 'border-gold/30 bg-gold/5',
      severity === 'low'    && 'border-muted bg-muted/30',
      className
    )}>
      <div className="flex items-start gap-3">
        <div className={cn(
          'mt-0.5 h-2 w-2 flex-shrink-0 rounded-full',
          severity === 'high'   && 'bg-destructive',
          severity === 'medium' && 'bg-gold',
          severity === 'low'    && 'bg-muted-foreground'
        )} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground">{title}</p>
          <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">{description}</p>
        </div>
      </div>
    </div>
  )
}

// ── EmptyState ────────────────────────────────────────────────────────────────

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 text-center', className)}>
      {icon && <div className="mb-4 text-muted-foreground">{icon}</div>}
      <h3 className="text-sm font-medium text-foreground">{title}</h3>
      {description && <p className="mt-1 text-xs text-muted-foreground max-w-xs">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

// ── ActionBadge (BUY / SELL / HOLD / TRIM / ADD / MONITOR) ───────────────────

type ActionType = 'BUY' | 'ADD' | 'HOLD' | 'TRIM' | 'SELL' | 'MONITOR'

interface ActionBadgeProps {
  action: ActionType
  className?: string
}

export function ActionBadge({ action, className }: ActionBadgeProps) {
  return (
    <span className={cn(
      'inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide',
      (action === 'BUY'  || action === 'ADD')     && 'bg-success/10 text-success',
      (action === 'HOLD' || action === 'MONITOR')  && 'bg-muted text-muted-foreground',
      (action === 'TRIM' || action === 'SELL')     && 'bg-destructive/10 text-destructive',
      className
    )}>
      {action}
    </span>
  )
}

// ── UrgencyDot ────────────────────────────────────────────────────────────────

interface UrgencyDotProps {
  urgency: 'high' | 'medium' | 'low'
}

export function UrgencyDot({ urgency }: UrgencyDotProps) {
  return (
    <span className={cn(
      'h-1.5 w-1.5 rounded-full flex-shrink-0',
      urgency === 'high'   && 'bg-destructive',
      urgency === 'medium' && 'bg-gold',
      urgency === 'low'    && 'bg-muted-foreground'
    )} />
  )
}

// ── ScoreBadge ────────────────────────────────────────────────────────────────

interface ScoreBadgeProps {
  score: number
  className?: string
}

export function ScoreBadge({ score, className }: ScoreBadgeProps) {
  return (
    <span className={cn(
      'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold',
      score >= 80 && 'bg-success/10 text-success',
      score >= 60 && score < 80 && 'bg-gold/10 text-gold',
      score < 60  && 'bg-muted text-muted-foreground',
      className
    )}>
      {score}
    </span>
  )
}

// ── EventTypeBadge ────────────────────────────────────────────────────────────

type EventType = 'earnings' | 'macro' | 'dividend' | 'rate'

interface EventTypeBadgeProps {
  type: EventType
}

export function EventTypeBadge({ type }: EventTypeBadgeProps) {
  const map: Record<EventType, { label: string; cls: string }> = {
    earnings: { label: 'Earnings', cls: 'bg-[#2563EB]/10 text-[#2563EB]' },
    macro:    { label: 'Macro',    cls: 'bg-[#7C3AED]/10 text-[#7C3AED]' },
    dividend: { label: 'Dividend', cls: 'bg-success/10 text-success'      },
    rate:     { label: 'Rate',     cls: 'bg-gold/10 text-gold'            },
  }
  const { label, cls } = map[type] ?? { label: type, cls: 'bg-muted text-muted-foreground' }
  return (
    <span className={cn('inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-semibold', cls)}>
      {label}
    </span>
  )
}

// ── HealthStatusRow ───────────────────────────────────────────────────────────

type HealthStatus = 'good' | 'warning' | 'danger'

interface HealthStatusRowProps {
  label: string
  status: HealthStatus
  detail: string
}

export function HealthStatusRow({ label, status, detail }: HealthStatusRowProps) {
  const Icon =
    status === 'good'    ? CheckCircle2 :
    status === 'warning' ? AlertTriangle :
    XCircle

  return (
    <div className="flex items-center gap-3 py-1.5 border-b border-border last:border-0">
      <Icon className={cn(
        'h-4 w-4 flex-shrink-0',
        status === 'good'    && 'text-success',
        status === 'warning' && 'text-gold',
        status === 'danger'  && 'text-destructive'
      )} />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-foreground">{label}</p>
        <p className="text-[11px] text-muted-foreground truncate">{detail}</p>
      </div>
    </div>
  )
}

// ── MarketRegimeBanner ────────────────────────────────────────────────────────

interface MarketRegimeBannerProps {
  regime:        'risk-on' | 'neutral' | 'risk-off' | 'crisis'
  label:         string
  vix:           number
  sp500Trend:    string
  nasdaqStatus:  string
  rateMacroNote: string
  aiConviction:  number
  summary:       string
}

export function MarketRegimeBanner({
  regime, label, vix, sp500Trend, nasdaqStatus, rateMacroNote, aiConviction, summary,
}: MarketRegimeBannerProps) {
  const pill = {
    'risk-on':  'bg-success/15 text-success border-success/30',
    'neutral':  'bg-gold/15 text-gold-foreground border-gold/30',
    'risk-off': 'bg-orange-500/15 text-orange-400 border-orange-500/30',
    'crisis':   'bg-destructive/15 text-destructive border-destructive/30',
  }[regime]

  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
      {/* Top row: regime badge + stats */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">Market Regime</span>
          <span className={cn('rounded-full border px-2.5 py-0.5 text-xs font-bold', pill)}>{label}</span>
        </div>

        <div className="flex flex-wrap gap-5 ml-auto">
          {([
            { label: 'VIX',     value: vix.toFixed(2) },
            { label: 'S&P 500', value: sp500Trend      },
            { label: 'Nasdaq',  value: nasdaqStatus    },
          ] as { label: string; value: string }[]).map(({ label: l, value: v }) => (
            <div key={l} className="text-center">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">{l}</p>
              <p className="text-sm font-semibold text-foreground mt-0.5">{v}</p>
            </div>
          ))}
          <div className="flex items-center gap-2.5">
            <div className="text-center">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">AI Conviction</p>
              <p className="text-sm font-semibold text-foreground mt-0.5">{aiConviction}%</p>
            </div>
            <ProgressRing value={aiConviction} size={40} strokeWidth={3} />
          </div>
        </div>
      </div>

      {/* Bottom row: summary + rate note */}
      <div className="mt-3 pt-3 border-t border-border flex flex-col gap-1 lg:flex-row lg:gap-6">
        <p className="text-sm text-muted-foreground leading-relaxed flex-1">{summary}</p>
        {rateMacroNote && (
          <p className="text-sm text-muted-foreground leading-relaxed lg:text-right lg:max-w-xs">{rateMacroNote}</p>
        )}
      </div>
    </div>
  )
}

// ── Format helpers ────────────────────────────────────────────────────────────

export function formatCurrency(value: number, compact?: boolean): string {
  if (compact && Math.abs(value) >= 1_000_000) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2,
    }).format(value)
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).format(value)
}

export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals, maximumFractionDigits: decimals,
  }).format(value)
}

export function formatPercent(value: number, showSign = false): string {
  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).format(Math.abs(value))
  const sign = showSign && value > 0 ? '+' : (value < 0 ? '-' : '')
  return `${sign}${formatted}%`
}
