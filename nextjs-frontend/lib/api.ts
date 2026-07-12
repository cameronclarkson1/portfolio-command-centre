/**
 * api.ts — fetches live data from the FastAPI backend (localhost:8000).
 *
 * Each function returns the correctly shaped object the dashboard already
 * expects, or null if the API is offline / returns an error.
 * The dashboard falls back to mock data when it receives null.
 */

import {
  marketRegime      as mockRegime,
  marketIndices     as mockIndices,
  newsEvents        as mockNews,
  sectorPerformance as mockSectors,
  bondYields        as mockYields,
} from '@/lib/mock-data'

// ── Config ─────────────────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ── Types (mirror what the dashboard uses) ────────────────────────────────────

export type MarketRegimeData   = typeof mockRegime
export type MarketIndexData    = (typeof mockIndices)[number]
export type NewsEventData      = (typeof mockNews)[number]
export type SectorPerfData     = (typeof mockSectors)[number]
export type BondYieldData      = (typeof mockYields)[number]
export type MacroIndicatorData = { name: string; value: string; trend: 'up' | 'down' | 'flat' }

export interface DashboardDecision {
  ticker:  string
  action:  'BUY' | 'ADD' | 'HOLD' | 'MONITOR' | 'TRIM'
  reason:  string
  urgency: 'high' | 'medium' | 'low'
}

export interface DashboardOpportunity {
  ticker:    string
  company:   string
  price:     number
  fairValue: number
  upside:    number
  score:     number
  tag:       string
}

export interface DashboardHolding {
  symbol:        string
  name:          string
  weight:        number
  value:         number
  change:        number         // daily %
  unrealisedPnl: number
}

export interface DashboardSectorEntry {
  name:  string
  value: number   // %
  color: string
}

export interface LiveDashboardData {
  marketRegime:     MarketRegimeData        | null
  marketIndices:    MarketIndexData[]       | null
  newsEvents:       NewsEventData[]         | null
  decisions:        DashboardDecision[]     | null
  opportunities:    DashboardOpportunity[]  | null
  riskAlerts:       RiskAlert[]             | null
  portfolioSummary: PortfolioSummary        | null
  portfolioRisk:    PortfolioRiskData       | null
  topHoldings:      DashboardHolding[]      | null
  sectorAlloc:      DashboardSectorEntry[]  | null
}

// Forward-declared subset so LiveDashboardData can reference it before PortfolioApiData
export interface PortfolioSummary {
  total_value:          number
  invested:             number
  cash:                 number
  cash_pct:             number
  daily_change_dollars: number
  daily_change_pct:     number
  total_gain:           number
  total_gain_pct:       number
  num_holdings:         number
  health_score:         number
  prices_live:          boolean
}

export interface CommodityData {
  symbol: string
  name:   string
  unit:   string
  price:  number | null
  change: number | null
}

export interface CryptoData {
  symbol: string
  name:   string
  price:  number | null
  change: number | null
}

export interface EarningsItem {
  ticker:       string
  name:         string
  date:         string        // ISO: "2026-05-20"
  hour:         string        // "amc" | "bmo"
  eps_estimate: number | null
}

export interface MacroEvent {
  date:        string          // ISO: "2026-07-15"
  event:       string
  time:        string
  importance:  'high' | 'medium'
}

export interface LiveMarketsData {
  marketIndices:    MarketIndexData[]    | null
  sectorPerformance: SectorPerfData[]   | null
  newsEvents:       NewsEventData[]      | null
  bondYields:       BondYieldData[]      | null
  macroIndicators:  MacroIndicatorData[] | null
  commodities:      CommodityData[]      | null
  crypto:           CryptoData[]         | null
}

export interface LiveIntelligenceData {
  marketRegime: MarketRegimeData | null
  newsEvents:   NewsEventData[]  | null
  earnings:     EarningsItem[]   | null
}

export type LivePriceData = Record<string, { price: number; change_pct: number } | null>

// ── Internal helpers ──────────────────────────────────────────────────────────

/** Fetch with a configurable timeout so a cold/offline API doesn't block the page. */
async function apiFetch(path: string, timeoutMs = 15000, init?: RequestInit): Promise<unknown> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      cache: 'no-store',
    })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  } finally {
    clearTimeout(timer)
  }
}

/**
 * Converts an ISO timestamp ("2026-05-16T10:32:00Z") into a relative label
 * ("4m ago", "2h ago", "1d ago").
 */
function toRelativeTime(iso: string): string {
  const diffMs   = Date.now() - new Date(iso).getTime()
  const diffMins = Math.floor(diffMs / 60_000)
  if (diffMins < 60)  return `${diffMins}m ago`
  const diffHrs = Math.floor(diffMins / 60)
  if (diffHrs  < 24)  return `${diffHrs}h ago`
  return `${Math.floor(diffHrs / 24)}d ago`
}

// ── Market Regime ─────────────────────────────────────────────────────────────
//
// API returns:  { regime, vix, sp500_trend, buying_rule, summary, confidence }
// Dashboard expects: { regime, label, vix, sp500Trend, nasdaqStatus,
//                      rateMacroNote, aiConviction, summary }

const REGIME_LABELS: Record<string, string> = {
  'risk-on':  'Risk-On',
  'neutral':  'Neutral',
  'risk-off': 'Risk-Off',
  'crisis':   'Crisis',
}

async function fetchMarketRegime(): Promise<MarketRegimeData | null> {
  const raw = await apiFetch('/api/market/regime') as Record<string, unknown> | null
  if (!raw) return null

  const regime = (String(raw.regime ?? '').toLowerCase()) as MarketRegimeData['regime']
  return {
    regime,
    label:         REGIME_LABELS[regime]            ?? String(raw.regime),
    vix:           Number(raw.vix)                  ?? 0,
    sp500Trend:    String(raw.sp500_trend            ?? 'Unknown'),
    nasdaqStatus:  String(raw.sp500_trend            ?? 'Unknown'),  // API doesn't expose Nasdaq separately
    dowStatus:     String(raw.sp500_trend            ?? 'Unknown'),
    rateMacroNote: String(raw.buying_rule            ?? ''),
    aiConviction:  Math.round(Number(raw.confidence) ?? 70),
    summary:       String(raw.summary                ?? ''),
  }
}

// ── Market Indices ────────────────────────────────────────────────────────────
//
// API returns:  [{ name, value, change_pct, source, fetched_at }, ...]
// Dashboard expects: [{ name, symbol, value, change, ytd }, ...]

const SYMBOL_MAP: Record<string, string> = {
  'S&P 500':   'SPX',
  'NASDAQ':    'IXIC',
  'Dow Jones': 'DJI',
  'VIX':       'VIX',
}

async function fetchMarketIndices(): Promise<MarketIndexData[] | null> {
  const raw = await apiFetch('/api/market/indices') as Record<string, unknown>[] | null
  if (!Array.isArray(raw) || raw.length === 0) return null

  return raw.map((idx) => ({
    name:   String(idx.name),
    symbol: SYMBOL_MAP[String(idx.name)] ?? String(idx.name),
    value:  Number(idx.value),
    change: Number(idx.change_pct) * 100,
    ytd:    null,   // API doesn't provide YTD — shown as "—" in the table
  }))
}

// ── News Events ───────────────────────────────────────────────────────────────
//
// API returns:  [{ headline, source, published_at, ticker, provider }, ...]
// Dashboard expects: [{ time, title, source, sentiment, ticker, aiScore }, ...]

async function fetchMarketNews(): Promise<NewsEventData[] | null> {
  const raw = await apiFetch('/api/news/market') as Record<string, unknown>[] | null
  if (!Array.isArray(raw) || raw.length === 0) return null

  return raw.map((item) => ({
    time:      toRelativeTime(String(item.published_at ?? '')),
    title:     String(item.headline ?? ''),
    source:    String(item.source   ?? ''),
    sentiment: 'neutral' as const,
    ticker:    item.ticker ? String(item.ticker) : null,
    aiScore:   65,
    url:       item.url ? String(item.url) : null,
  })) as NewsEventData[]
}

// ── Sector Performance ────────────────────────────────────────────────────────
//
// API returns:  { "Technology": 0.82, "Healthcare": -0.34, ... }
// Page expects: [{ sector, daily, weekly, monthly }]
// weekly/monthly are kept from mock since the API only provides daily (via ETFs)

const SECTOR_NAME_MAP: Record<string, string> = {
  'Communication Services': 'Communication',
  'Consumer Discretionary': 'Consumer Disc.',
}

async function fetchSectorPerformance(): Promise<SectorPerfData[] | null> {
  const raw = await apiFetch('/api/market/sectors') as Record<string, number> | null
  if (!raw || typeof raw !== 'object') return null

  return mockSectors.map((s) => {
    const apiKey = Object.keys(SECTOR_NAME_MAP).find(k => SECTOR_NAME_MAP[k] === s.sector) ?? s.sector
    const daily  = raw[apiKey] ?? s.daily
    return { ...s, daily }
  })
}

// ── Macro Snapshot ────────────────────────────────────────────────────────────
//
// API returns:  { fed_funds_rate: {value}, treasury_10y: {value}, cpi_yoy: {value}, ... }
// Used for: macro indicator cards + bond yields

type RawMacro = Record<string, { value: number } | unknown>

async function fetchMacroSnapshot(): Promise<RawMacro | null> {
  return await apiFetch('/api/market/macro') as RawMacro | null
}

function macroValue(raw: RawMacro, key: string): number | null {
  const entry = raw[key]
  if (entry && typeof entry === 'object' && 'value' in entry) return Number((entry as { value: number }).value)
  return null
}

function normalizeMacroIndicators(raw: RawMacro): MacroIndicatorData[] | null {
  const gdp  = macroValue(raw, 'gdp_growth')
  const cpi  = macroValue(raw, 'cpi_yoy')
  const unem = macroValue(raw, 'unemployment')
  const fed  = macroValue(raw, 'fed_funds_rate')
  if (gdp === null && cpi === null) return null

  return [
    { name: 'GDP Growth (QoQ)',    value: gdp  != null ? `${gdp.toFixed(1)}%`  : '—', trend: 'flat' },
    { name: 'Inflation (CPI YoY)', value: cpi  != null ? `${cpi.toFixed(1)}%`  : '—', trend: 'flat' },
    { name: 'Unemployment',        value: unem != null ? `${unem.toFixed(1)}%` : '—', trend: 'flat' },
    { name: 'Fed Funds Rate',      value: fed  != null ? `${fed.toFixed(2)}%`  : '—', trend: 'flat' },
  ]
}

function normalizeBondYields(raw: RawMacro): BondYieldData[] | null {
  const y2  = macroValue(raw, 'treasury_2y')
  const y10 = macroValue(raw, 'treasury_10y')
  if (y2 === null && y10 === null) return null

  return [
    { name: '2Y Treasury',  yield: y2  ?? 0,                     change: 0 },
    { name: '10Y Treasury', yield: y10 ?? 0,                     change: 0 },
    { name: '30Y Treasury', yield: mockYields[2]?.yield ?? 4.45, change: 0 },
  ]
}

// ── Main exports ──────────────────────────────────────────────────────────────

async function fetchDashboardDecisions(): Promise<DashboardDecision[] | null> {
  const raw = await apiFetch('/api/portfolio/decisions') as { decisions: Record<string, unknown>[] } | null
  if (!raw || !Array.isArray(raw.decisions)) return null
  return raw.decisions.map((d) => ({
    ticker:  String(d.ticker  ?? ''),
    action:  (String(d.action  ?? 'HOLD')) as DashboardDecision['action'],
    reason:  String(d.reason  ?? ''),
    urgency: (String(d.urgency ?? 'low')) as DashboardDecision['urgency'],
  }))
}

async function fetchDashboardOpportunities(): Promise<DashboardOpportunity[] | null> {
  const raw = await apiFetch('/api/portfolio/opportunities') as { opportunities: Record<string, unknown>[] } | null
  if (!raw || !Array.isArray(raw.opportunities)) return null
  return raw.opportunities.map((o) => ({
    ticker:    String(o.ticker    ?? ''),
    company:   String(o.company   ?? ''),
    price:     Number(o.price     ?? 0),
    fairValue: Number(o.fair_value ?? 0),
    upside:    Number(o.upside    ?? 0),
    score:     Number(o.score     ?? 0),
    tag:       String(o.tag       ?? ''),
  }))
}


const _SECTOR_COLORS: Record<string, string> = {
  'ETF':                    'var(--chart-1)',
  'Communication Services': 'var(--chart-3)',
  'Technology':             'var(--chart-2)',
  'Consumer Staples':       'var(--chart-4)',
  'Financials':             'var(--chart-5)',
  'Consumer Discretionary': 'var(--chart-1)',
  'Real Estate':            'var(--chart-2)',
  'Healthcare':             'var(--chart-3)',
  'Materials':              'var(--chart-4)',
  'Energy':                 'var(--chart-5)',
  'Industrials':            'var(--chart-1)',
  'Utilities':              'var(--chart-2)',
  'Cash':                   'var(--muted-foreground)',
}

/**
 * Fetches all live data for the Dashboard in parallel.
 * Any section that fails returns null — falls back to mock data.
 */
export async function fetchDashboardData(): Promise<LiveDashboardData> {
  const [regime, indices, news, decisions, opportunities, portfolio, portfolioRisk] = await Promise.all([
    fetchMarketRegime(),
    fetchMarketIndices(),
    fetchMarketNews(),
    fetchDashboardDecisions(),
    fetchDashboardOpportunities(),
    fetchPortfolio(),
    fetchPortfolioRisk(),
  ])

  const topHoldings: DashboardHolding[] | null = portfolio
    ? [...portfolio.holdings]
        .sort((a, b) => b.weight - a.weight)
        .slice(0, 6)
        .map((h) => ({
          symbol:        h.ticker,
          name:          h.name,
          weight:        h.weight,
          value:         h.market_value,
          change:        h.daily_change_pct,
          unrealisedPnl: h.unrealised_pnl,
        }))
    : null

  const sectorAlloc: DashboardSectorEntry[] | null = portfolio
    ? [
        ...Object.entries(portfolio.sector_weights).map(([name, value]) => ({
          name,
          value,
          color: _SECTOR_COLORS[name] ?? 'var(--chart-1)',
        })),
        {
          name:  'Cash',
          value: portfolio.summary.cash_pct,
          color: _SECTOR_COLORS['Cash'],
        },
      ].filter((s) => s.value > 0.1).sort((a, b) => b.value - a.value)
    : null

  return {
    marketRegime:     regime,
    marketIndices:    indices,
    newsEvents:       news,
    decisions,
    opportunities,
    riskAlerts:       portfolioRisk?.alerts     ?? null,
    portfolioSummary: portfolio?.summary        ?? null,
    portfolioRisk:    portfolioRisk             ?? null,
    topHoldings,
    sectorAlloc,
  }
}

/**
 * Fetches live news + regime for the Intelligence page.
 */
async function fetchPortfolioEarnings(): Promise<EarningsItem[] | null> {
  const raw = await apiFetch('/api/news/earnings', 20_000) as EarningsItem[] | null
  if (!Array.isArray(raw)) return null
  return raw
}

export async function fetchIntelligenceData(): Promise<LiveIntelligenceData> {
  const [regime, news, earnings] = await Promise.all([
    fetchMarketRegime(),
    fetchMarketNews(),
    fetchPortfolioEarnings(),
  ])
  return { marketRegime: regime, newsEvents: news, earnings }
}

export { fetchPortfolioEarnings }

export async function fetchMacroEvents(): Promise<MacroEvent[] | null> {
  const raw = await apiFetch('/api/events/macro') as { events: MacroEvent[] } | null
  if (!raw || !Array.isArray(raw.events)) return null
  return raw.events
}

/**
 * Fetches live prices for a set of tickers (used by Watchlist).
 * Returns a map of symbol → { price, change_pct } or null if all fail.
 */
export async function fetchWatchlistPrices(tickers: string[]): Promise<LivePriceData | null> {
  if (tickers.length === 0) return null
  const raw = await apiFetch(`/api/market/prices?tickers=${tickers.join(',')}`) as LivePriceData | null
  if (!raw || typeof raw !== 'object') return null
  return raw
}

// ── Portfolio ─────────────────────────────────────────────────────────────────
//
// Calls /api/portfolio which builds live-enriched holdings server-side,
// so the frontend never has to merge prices into mock data itself.

export interface PortfolioHolding {
  ticker:               string
  name:                 string
  sector:               string
  shares:               number
  avg_cost:             number
  current_price:        number
  market_value:         number
  cost_basis:           number
  unrealised_pnl:       number
  unrealised_pct:       number
  daily_change_pct:     number
  daily_change_dollars: number
  weight:               number
}

export interface PortfolioApiData {
  summary:        PortfolioSummary
  holdings:       PortfolioHolding[]
  sector_weights: Record<string, number>
  nzd_rate?:      number
}

export async function fetchPortfolio(): Promise<PortfolioApiData | null> {
  const raw = await apiFetch('/api/portfolio') as PortfolioApiData | null
  if (!raw || typeof raw !== 'object' || !('holdings' in raw)) return null
  return raw
}

export async function updateCash(usdAmount: number): Promise<boolean> {
  const raw = await apiFetch('/api/portfolio/cash', 10_000, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ amount: usdAmount }),
  })
  return raw != null
}

// ── Portfolio Risk ────────────────────────────────────────────────────────────

export interface RiskCategory {
  name:        string
  severity:    'info' | 'warning' | 'critical'
  score:       number
  metric:      string
  description: string
  limit:       string
  action:      string
}

export interface PerformancePoint {
  date:       string   // "YYYY-MM-DD"
  value:      number
  benchmark?: number | null   // SPY normalised to portfolio start value
}

export interface PortfolioPerformanceData {
  series:                PerformancePoint[]
  period:                string
  start_value:           number
  end_value:             number
  change_pct:            number
  change_dollars:        number
  benchmark_change_pct?: number | null   // SPY % change over same period
  volatility?:           number | null   // annualised daily vol as %
  sharpe?:               number | null   // annualised Sharpe ratio
  hypothetical?:         boolean         // true when showing current holdings applied retroactively
}

export async function fetchPortfolioPerformance(period: string): Promise<PortfolioPerformanceData | null> {
  const raw = await apiFetch(`/api/portfolio/performance?period=${period}`, 60_000) as PortfolioPerformanceData | null
  if (!raw || !Array.isArray(raw.series)) return null
  return raw
}

export interface RiskAlert {
  severity:    'high' | 'medium' | 'low'
  title:       string
  description: string
}

export interface PortfolioRiskData {
  health_score:   number
  categories:     RiskCategory[]
  alerts:         RiskAlert[]
  sector_weights: Record<string, number>
  metrics: {
    cash_pct:         number
    num_holdings:     number
    num_sectors:      number
    top_position:     string
    top_position_pct: number
    portfolio_beta:   number
    volatility?:      number | null
    sharpe_ratio?:    number | null
    max_drawdown?:    number | null
  }
  prices_live: boolean
}

export async function fetchPortfolioRisk(): Promise<PortfolioRiskData | null> {
  const raw = await apiFetch('/api/portfolio/risk') as PortfolioRiskData | null
  if (!raw || typeof raw !== 'object' || !('categories' in raw)) return null
  return raw
}

// ── Portfolio Decisions ───────────────────────────────────────────────────────

export interface DecisionSignal {
  ticker:  string
  action:  'ADD' | 'HOLD' | 'MONITOR' | 'TRIM'
  reason:  string
  urgency: 'high' | 'medium' | 'low'
}

export async function fetchDecisions(): Promise<{ decisions: DecisionSignal[]; prices_live: boolean } | null> {
  const raw = await apiFetch('/api/portfolio/decisions') as { decisions: DecisionSignal[]; prices_live: boolean } | null
  if (!raw || !Array.isArray(raw.decisions)) return null
  return raw
}

// ── Dividend Calendar ─────────────────────────────────────────────────────────

export interface DividendEntry {
  ticker:        string
  name:          string
  ex_div_date:   string | null   // "YYYY-MM-DD"
  pay_date:      string | null
  annual_div:    number
  quarterly_div: number
  yield_pct:     number | null
  in_portfolio:  boolean
}

export async function fetchDividends(): Promise<{ upcoming: DividendEntry[]; recent: DividendEntry[] } | null> {
  const raw = await apiFetch('/api/portfolio/dividends', 55_000) as { upcoming: DividendEntry[]; recent: DividendEntry[] } | null
  if (!raw || !Array.isArray(raw.upcoming)) return null
  return raw
}

// ── Research ──────────────────────────────────────────────────────────────────
//
// Calls /api/research/{ticker} which runs valuation + ratios + statements +
// analyst + news + earnings in parallel (45 s timeout for first call).

export interface ScoreData {
  quality_score:     number | null
  growth_score:      number | null
  valuation_score:   number | null
  safety_score:      number | null   // higher = safer (business/financial risk only)
  confidence:        number | null
  final_score:       number | null
  rating:            string          // 7-level: Strong Buy → Strong Sell
  valuation_status:  string          // Deeply Undervalued → Severely Overvalued
  rating_explanation: string | null  // one or two plain-English sentences
  score_qualifiers:  {
    quality:   string
    growth:    string
    valuation: string
    safety:    string
  } | null
}

export interface InvestmentThesis {
  bull:  string[]
  bear:  string[]
  base:  string[]
  watch: string[]
}

export interface CompanyProfile {
  description: string | null
  ceo:         string | null
  employees:   number | string | null
  exchange:    string | null
  country:     string | null
  ipo_year:    string | null
  website:     string | null
}

export interface ResearchData {
  ticker:               string
  company_name:         string | null
  company_profile:      CompanyProfile | null
  price:                number | null
  change_pct:           number
  price_source?:        string | null
  price_fallback_used?: boolean

  // Valuation engine (9-model sector-aware)
  valuation: ValuationResult | null

  // Key ratios from FMP / Finnhub
  ratios: {
    pe_ratio?:           number | null
    ev_ebitda?:          number | null
    ps_ratio?:           number | null
    pb_ratio?:           number | null
    roic?:               number | null
    roe?:                number | null
    debt_equity?:        number | null
    dividend_yield?:     number | null
    beta?:               number | null
    fcf_per_share?:      number | null
    revenue_growth_yoy?: number | null
    '52_week_high'?:     number | null
    '52_week_low'?:      number | null
  } | null

  // Revenue + EPS series for charts
  income_series: { year: string; revenue_b: number; eps: number }[]

  // Margin percentages from latest income statement
  margins: { gross: number | null; operating: number | null; net: number | null; note?: string | null } | null

  // Composite scoring (Quality / Growth / Valuation / Safety)
  scores: ScoreData | null

  // Data-driven investment thesis
  investment_thesis: InvestmentThesis | null

  // Analyst ratings counts + raw list
  analyst_summary: { buy: number; hold: number; sell: number; total: number; avg_target: number | null }
  analyst_actions: {
    analyst_firm:        string
    action:              string
    rating:              string
    rating_prior?:       string | null
    price_target?:       number | null
    price_target_prior?: number | null
    published_at:        string
    bucket:              'buy' | 'hold' | 'sell'
  }[]

  // Recent news
  recent_news: { headline: string; source: string; published_at: string; summary?: string | null; url?: string | null }[]

  // Upcoming earnings
  earnings: { date: string; hour: string; eps_estimate?: number | null; revenue_est?: number | null }[]
}

export async function fetchResearch(ticker: string, price?: number): Promise<ResearchData | null> {
  const params = price != null ? `?price=${price}` : ''
  const raw = await apiFetch(`/api/research/${ticker.toUpperCase()}${params}`, 45_000) as ResearchData | null
  if (!raw || typeof raw !== 'object' || !('ticker' in raw)) return null
  return raw
}

// ── Valuation Engine ──────────────────────────────────────────────────────────
//
// Calls /api/valuation/{ticker} which runs the 9-model sector-aware engine.
// Uses a 30-second timeout — first call for a ticker may take 5-15 seconds.

export interface ValuationResult {
  ticker:             string
  sector:             string
  bucket:             string
  models_run:         Record<string, {
    fair_value:   number | null
    confidence:   number
    name?:        string
    warnings?:    string[]
    inputs_used?: Record<string, number | string | null | boolean>
  }>
  fair_value_low:     number
  fair_value_base:    number
  fair_value_high:    number
  upside_pct:         number
  valuation_rating:   string
  overall_confidence:      number
  confidence_explanation?: string
  analyst_consensus?: {
    target_median:    number | null
    target_consensus: number | null
    target_high:      number | null
    target_low:       number | null
    analyst_count:    number
    has_data:         boolean
    pt_upside_pct:    number | null
  }
  warnings:                string[]
  blend_notes?:            string[]   // outlier/down-weight explanations from P2.3
  why_these_models?:       string     // updated dynamically when characteristic models added
}

export async function fetchValuation(ticker: string, price?: number): Promise<ValuationResult | null> {
  const params = price != null ? `?price=${price}` : ''
  const raw = await apiFetch(`/api/valuation/${ticker.toUpperCase()}${params}`, 30_000) as ValuationResult | null
  if (!raw || typeof raw !== 'object' || !('fair_value_base' in raw)) return null
  return raw as ValuationResult
}

// ── Watchlist Refresh ─────────────────────────────────────────────────────────

export interface WatchlistRefreshItem {
  ticker:     string
  price:      number | null
  change_pct: number | null
  fair_value: number | null
  buy_below:  number | null
  upside_pct: number | null
  scores:     ScoreData | null
  error:      string | null
}

export async function fetchWatchlistRefresh(tickers: string[]): Promise<WatchlistRefreshItem[] | null> {
  if (tickers.length === 0) return null
  const raw = await apiFetch('/api/watchlist/refresh', 90_000, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ tickers }),
  }) as { items: WatchlistRefreshItem[] } | null
  if (!raw || !Array.isArray(raw.items)) return null
  return raw.items
}

// ── Scanner (Daily Opportunities) ────────────────────────────────────────────

export interface ScannerOpportunity {
  ticker:        string
  name:          string
  sector:        string
  price:         number | null
  change_pct:    number | null
  market_cap:    number | null
  pe_ratio:      number | null
  ev_ebitda:     number | null
  roic:          number | null      // percent, e.g. 18.5 means 18.5%
  net_margin:    number | null      // percent
  rev_growth:    number | null      // percent
  current_ratio: number | null
  year_high:     number | null
  year_low:      number | null
  score:         number             // 0–100 composite score
}

export interface ScannerResults {
  scanned_at:       string | null
  duration_seconds: number | null
  universe_size:    number | null
  stocks_quoted:    number | null
  opportunities:    ScannerOpportunity[]
  message?:         string
}

export interface ScannerStatus {
  running:             boolean
  last_run:            string | null
  last_run_duration_s: number | null
  stocks_scanned:      number
  error:               string | null
  results_available:   boolean
}

export async function fetchScannerResults(): Promise<ScannerResults | null> {
  const raw = await apiFetch('/api/scanner/results', 15_000) as ScannerResults | null
  if (!raw || typeof raw !== 'object') return null
  return raw
}

export async function fetchScannerStatus(): Promise<ScannerStatus | null> {
  const raw = await apiFetch('/api/scanner/status', 5_000) as ScannerStatus | null
  if (!raw || typeof raw !== 'object') return null
  return raw
}

export async function triggerScan(): Promise<{ message: string; running: boolean } | null> {
  const raw = await apiFetch('/api/scanner/trigger', 10_000) as { message: string; running: boolean } | null
  return raw
}

/** Fetch 7-day daily close prices for sparkline charts. Returns { AAPL: [182, 183, ...], ... } */
export async function fetchSparklines(tickers: string[]): Promise<Record<string, number[]> | null> {
  if (tickers.length === 0) return null
  const raw = await apiFetch('/api/watchlist/sparklines', 35_000, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ tickers }),
  }) as { sparklines: Record<string, number[]> } | null
  return raw?.sparklines ?? null
}

async function fetchAlternatives(): Promise<{ commodities: CommodityData[]; crypto: CryptoData[] } | null> {
  const raw = await apiFetch('/api/market/alternatives') as { commodities: CommodityData[]; crypto: CryptoData[] } | null
  if (!raw || !Array.isArray(raw.commodities)) return null
  return raw
}

/**
 * Fetches all live data for the Markets page in parallel.
 * Any section that fails returns null — falls back to mock data.
 */
export async function fetchMarketsData(): Promise<LiveMarketsData> {
  const [indices, sectors, news, macro, alternatives] = await Promise.all([
    fetchMarketIndices(),
    fetchSectorPerformance(),
    fetchMarketNews(),
    fetchMacroSnapshot(),
    fetchAlternatives(),
  ])

  return {
    marketIndices:     indices,
    sectorPerformance: sectors,
    newsEvents:        news,
    bondYields:        macro ? normalizeBondYields(macro)      : null,
    macroIndicators:   macro ? normalizeMacroIndicators(macro) : null,
    commodities:       alternatives?.commodities ?? null,
    crypto:            alternatives?.crypto      ?? null,
  }
}
