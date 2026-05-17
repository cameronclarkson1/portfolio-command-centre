'use client'

import { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight, Minus, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react'

// ── MetricCard ───────────────────────────────────────────────────────────────

interface MetricCardProps {
  title: string
  value: string | number
  change?: number
  changeLabel?: string
  icon?: ReactNode
  className?: string
  compact?: boolean
}

export function MetricCard({ title, value, change, changeLabel, icon, className, compact }: MetricCardProps) {
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

interface RatingBadgeProps {
  rating: 'Buy' | 'Hold' | 'Sell'
  className?: string
}

export function RatingBadge({ rating, className }: RatingBadgeProps) {
  return (
    <span className={cn(
      'inline-flex items-center rounded-md px-2 py-1 text-xs font-semibold',
      rating === 'Buy'  && 'bg-success/10 text-success',
      rating === 'Hold' && 'bg-gold/10 text-gold',
      rating === 'Sell' && 'bg-destructive/10 text-destructive',
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
  const styles = {
    'risk-on':  { bg: '#f0fdf4', border: '#bbf7d0', text: '#166534', pill: 'bg-green-100 text-green-800'  },
    'neutral':  { bg: '#fefce8', border: '#fef08a', text: '#854d0e', pill: 'bg-yellow-100 text-yellow-800' },
    'risk-off': { bg: '#fff7ed', border: '#fed7aa', text: '#9a3412', pill: 'bg-orange-100 text-orange-800' },
    'crisis':   { bg: '#fef2f2', border: '#fecaca', text: '#991b1b', pill: 'bg-red-100 text-red-800'       },
  }
  const s = styles[regime]

  return (
    <div
      className="rounded-xl border p-4"
      style={{ background: s.bg, borderColor: s.border }}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        {/* Left: regime label + summary */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Market Regime</span>
            <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-bold', s.pill)}>{label}</span>
          </div>
          <p className="text-sm text-foreground/80 leading-relaxed">{summary}</p>
        </div>

        {/* Middle: key stats */}
        <div className="flex flex-wrap gap-4 lg:gap-6">
          {[
            { label: 'VIX',       value: vix.toFixed(1)    },
            { label: 'S&P 500',   value: sp500Trend        },
            { label: 'Nasdaq',    value: nasdaqStatus       },
            { label: 'Rate Note', value: rateMacroNote, wide: true },
          ].map(({ label: l, value: v, wide }) => (
            <div key={l} className={cn('flex-shrink-0', wide && 'hidden xl:block max-w-[220px]')}>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">{l}</p>
              <p className="text-sm font-medium text-foreground truncate" style={{ color: s.text }}>{v}</p>
            </div>
          ))}
        </div>

        {/* Right: conviction ring */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">AI Conviction</p>
            <p className="text-sm font-semibold" style={{ color: s.text }}>{aiConviction}%</p>
          </div>
          <ProgressRing value={aiConviction} size={52} strokeWidth={4} />
        </div>
      </div>
    </div>
  )
}

// ── Format helpers ────────────────────────────────────────────────────────────

export function formatCurrency(value: number, compact?: boolean): string {
  if (compact && Math.abs(value) >= 1_000_000) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1,
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
