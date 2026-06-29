// ── REAL PORTFOLIO DATA ───────────────────────────────────────────────────────
// Source: repo/utils/sample_data.py  (shares, avg_cost are ground truth)
// Live prices are overlaid on each page load via market_data_service.
// Performance chart and some market-page figures remain placeholder.
// ─────────────────────────────────────────────────────────────────────────────

// ── Portfolio summary ────────────────────────────────────────────────────────

export const portfolioData = {
  totalValue:              14_833.63,
  dailyChange:                  0.00,   // computed live
  dailyChangePercent:           0.00,
  weeklyChange:                 0.00,
  weeklyChangePercent:          0.00,
  monthlyChange:                0.00,
  monthlyChangePercent:         0.00,
  yearlyChange:                 0.00,
  yearlyChangePercent:          0.00,
  cashBalance:              2_757.08,
  investedCapital:         12_076.55,
  buyingPower:              2_757.08,
  portfolioHealthScore:            70,
  beta:                          1.0,
  sharpeRatio:                   0.0,   // placeholder
  volatility:                    0.0,
}

// ── Market status ────────────────────────────────────────────────────────────

export const marketStatus = {
  isOpen:            true,
  nextOpen:          '09:30 AM ET',
  nextClose:         '04:00 PM ET',
  regime:            'Neutral',
  regimeConfidence:  60,
}

// ── Market regime (detailed) ─────────────────────────────────────────────────

export const marketRegime = {
  regime:         'neutral' as 'risk-on' | 'neutral' | 'risk-off' | 'crisis',
  label:          'Neutral',
  vix:            21.4,
  sp500Trend:     'Sideways',
  nasdaqStatus:   'Sideways',
  dowStatus:      'Sideways',
  rateMacroNote:  'Fed on hold. VIX at 21 — cautious buying only. Prefer adds over new initiations.',
  aiConviction:   60,
  summary:
    'VIX at 21 signals moderate uncertainty. S&P 500 near its 50-day MA with mixed breadth. ' +
    'Prefer adding to existing quality positions over initiating large new positions.',
}

// ── Portfolio health detail ───────────────────────────────────────────────────

export const portfolioHealthDetail = {
  score: 70,
  indicators: [
    { label: 'Diversification',    status: 'good'    as const, detail: '9 sectors, 18 positions' },
    { label: 'Cash Position',      status: 'warning' as const, detail: '18.6% cash (deploy into quality dips)' },
    { label: 'Beta / Risk',        status: 'good'    as const, detail: 'Beta ~1.0 — market-neutral' },
    { label: 'Rebalance Status',   status: 'good'    as const, detail: 'All positions at target weight' },
    { label: 'ETF Concentration',  status: 'warning' as const, detail: '22.1% in ETFs (SCHD + VOO)' },
  ],
}

// ── Daily decisions ───────────────────────────────────────────────────────────

export const dailyDecisions: {
  ticker: string; action: 'BUY' | 'ADD' | 'HOLD' | 'MONITOR' | 'TRIM'; reason: string; urgency: 'high' | 'medium' | 'low'
}[] = []

// ── Best opportunities ────────────────────────────────────────────────────────

export const opportunities: {
  ticker: string; company: string; price: number; fairValue: number; upside: number; score: number; tag: string
}[] = []

// ── Upcoming events ───────────────────────────────────────────────────────────

export const upcomingEvents = [
  { date: 'May 20', type: 'earnings' as const, ticker: 'NVDA', description: 'Q1 FY2026 Earnings',     timing: 'After Close', inPortfolio: true  },
  { date: 'May 21', type: 'macro'    as const, ticker: null,   description: 'FOMC Minutes Released',   timing: '2:00 PM ET',  inPortfolio: false },
  { date: 'May 22', type: 'macro'    as const, ticker: null,   description: 'US CPI Data Release',     timing: '8:30 AM ET',  inPortfolio: false },
  { date: 'May 30', type: 'macro'    as const, ticker: null,   description: 'US PCE Inflation Report', timing: '8:30 AM ET',  inPortfolio: false },
]

// ── Allocation drift / rebalance ──────────────────────────────────────────────

export const allocationDrift: Array<{ sector: string; current: number; target: number; drift: number; action: string; actionType: 'hold' | 'buy' | 'sell' }> = [
  { sector: 'ETF',                    current: 22.1, target: 22.1, drift:  0.0, action: 'Hold',   actionType: 'hold' as const },
  { sector: 'Communication Services', current: 14.5, target: 14.5, drift:  0.0, action: 'Hold',   actionType: 'hold' as const },
  { sector: 'Technology',             current: 14.1, target: 14.1, drift:  0.0, action: 'Hold',   actionType: 'hold' as const },
  { sector: 'Consumer Staples',       current: 12.6, target: 12.6, drift:  0.0, action: 'Hold',   actionType: 'hold' as const },
  { sector: 'Cash',                   current: 18.6, target: 10.0, drift:  8.6, action: 'Deploy', actionType: 'buy'  as const },
  { sector: 'Financials',             current:  6.2, target:  6.2, drift:  0.0, action: 'Hold',   actionType: 'hold' as const },
]

// ── Holdings ──────────────────────────────────────────────────────────────────
// Shares and avgCost are ground truth. currentPrice/value/change are snapshot
// values from sample_data.py — live prices will override them on page load.

export const holdings = [
  { symbol: 'AVGO', name: 'Broadcom',               shares:  1.57, avgCost: 190.10, currentPrice: 438.41, value:   688.30, change: 0, unrealisedPnl:   389.85, sector: 'Technology',             weight:  4.64 },
  { symbol: 'BABA', name: 'Alibaba',                shares:  0.85, avgCost: 115.63, currentPrice: 140.91, value:   119.77, change: 0, unrealisedPnl:    21.49, sector: 'Consumer Discretionary', weight:  0.81 },
  { symbol: 'BAC',  name: 'Bank of America',        shares:  9.31, avgCost:  42.91, currentPrice:  49.93, value:   464.88, change: 0, unrealisedPnl:    65.36, sector: 'Financials',             weight:  3.13 },
  { symbol: 'GOOG', name: 'Alphabet',               shares:  5.75, avgCost: 172.38, currentPrice: 297.30, value: 1_709.50, change: 0, unrealisedPnl:   718.29, sector: 'Communication Services', weight: 11.52 },
  { symbol: 'JNJ',  name: 'Johnson & Johnson',      shares:  2.83, avgCost: 189.40, currentPrice: 170.63, value:   482.88, change: 0, unrealisedPnl:   -53.12, sector: 'Healthcare',             weight:  3.28 },
  { symbol: 'KO',   name: 'Coca-Cola',              shares:  9.87, avgCost:  64.58, currentPrice:  80.44, value:   793.93, change: 0, unrealisedPnl:   156.54, sector: 'Consumer Staples',       weight:  5.35 },
  { symbol: 'MCD',  name: "McDonald's",             shares:  1.88, avgCost: 271.40, currentPrice: 274.65, value:   516.34, change: 0, unrealisedPnl:     6.11, sector: 'Consumer Discretionary', weight:  3.48 },
  { symbol: 'META', name: 'Meta Platforms',         shares:  0.61, avgCost: 601.41, currentPrice: 667.03, value:   406.89, change: 0, unrealisedPnl:    40.03, sector: 'Communication Services', weight:  2.74 },
  { symbol: 'MO',   name: 'Altria Group',           shares: 14.85, avgCost:  53.24, currentPrice:  72.14, value: 1_071.24, change: 0, unrealisedPnl:   280.67, sector: 'Consumer Staples',       weight:  7.22 },
  { symbol: 'MU',   name: 'Micron Technology',      shares:  0.85, avgCost: 119.02, currentPrice: 109.00, value:    92.65, change: 0, unrealisedPnl:    -8.52, sector: 'Technology',             weight:  0.62 },
  { symbol: 'NEM',  name: 'Newmont',                shares:  0.39, avgCost: 125.16, currentPrice: 116.95, value:    45.61, change: 0, unrealisedPnl:    -3.20, sector: 'Materials',              weight:  0.31 },
  { symbol: 'NVDA', name: 'NVIDIA',                 shares:  3.16, avgCost: 111.42, currentPrice: 235.80, value:   745.13, change: 0, unrealisedPnl:   393.04, sector: 'Technology',             weight:  5.02 },
  { symbol: 'O',    name: 'Realty Income',          shares:  9.90, avgCost:  52.70, currentPrice:  62.00, value:   613.72, change: 0, unrealisedPnl:    92.07, sector: 'Real Estate',            weight:  4.14 },
  { symbol: 'SCHD', name: 'Schwab US Dividend ETF', shares: 89.00, avgCost:  27.11, currentPrice:  31.87, value: 2_836.09, change: 0, unrealisedPnl:   423.64, sector: 'ETF',                    weight: 19.12 },
  { symbol: 'V',    name: 'Visa',                   shares:  1.10, avgCost: 276.18, currentPrice: 323.12, value:   355.43, change: 0, unrealisedPnl:    51.63, sector: 'Financials',             weight:  2.40 },
  { symbol: 'VOO',  name: 'Vanguard S&P 500 ETF',   shares:  0.72, avgCost: 535.54, currentPrice: 610.92, value:   439.86, change: 0, unrealisedPnl:    54.27, sector: 'ETF',                    weight:  2.96 },
  { symbol: 'VZ',   name: 'Verizon',                shares:  0.72, avgCost:  39.75, currentPrice:  48.13, value:    34.65, change: 0, unrealisedPnl:     6.03, sector: 'Communication Services', weight:  0.23 },
  { symbol: 'WFC',  name: 'Wells Fargo',            shares:  1.25, avgCost:  78.90, currentPrice:  73.98, value:    92.48, change: 0, unrealisedPnl:    -6.15, sector: 'Financials',             weight:  0.62 },
]

// ── Watchlist ─────────────────────────────────────────────────────────────────
// Mirrors sample_data.py WATCHLIST — keeps frontend initial state in sync with backend defaults.
// PG + HD have real scores; all others show live data after "Refresh Scores".

const _w = { price: 0, change: 0, changePercent: 0, fairValue: 0, rating: 'Watch', upside: 0, safetyScore: 0, sparkline: [] as number[] }

export const watchlist = [
  // ── Researched ────────────────────────────────────────────────────────────
  { symbol: 'PG',    name: 'Procter & Gamble',       price: 158.90, change: 0, changePercent: 0, fairValue: 175.00, buyBelow: 140.00, rating: 'Watch', upside: 10.1, safetyScore: 86, sparkline: [] as number[] },
  { symbol: 'HD',    name: 'Home Depot',              price: 342.10, change: 0, changePercent: 0, fairValue: 360.00, buyBelow: 288.00, rating: 'Watch', upside:  5.2, safetyScore: 76, sparkline: [] as number[] },
  // ── Technology ───────────────────────────────────────────────────────────
  { ..._w, symbol: 'AAPL',  name: 'Apple'                  },
  { ..._w, symbol: 'MSFT',  name: 'Microsoft'              },
  { ..._w, symbol: 'NVDA',  name: 'NVIDIA'                 },
  { ..._w, symbol: 'AVGO',  name: 'Broadcom'               },
  { ..._w, symbol: 'AMD',   name: 'Advanced Micro Devices' },
  { ..._w, symbol: 'TSM',   name: 'Taiwan Semiconductor'   },
  { ..._w, symbol: 'ASML',  name: 'ASML Holding'           },
  { ..._w, symbol: 'AMAT',  name: 'Applied Materials'      },
  { ..._w, symbol: 'MU',    name: 'Micron Technology'      },
  // ── Consumer ─────────────────────────────────────────────────────────────
  { ..._w, symbol: 'AMZN',  name: 'Amazon'                 },
  { ..._w, symbol: 'MCD',   name: "McDonald's"             },
  { ..._w, symbol: 'NKE',   name: 'Nike'                   },
  { ..._w, symbol: 'LOW',   name: "Lowe's"                 },
  { ..._w, symbol: 'BABA',  name: 'Alibaba'                },
  { ..._w, symbol: 'COST',  name: 'Costco'                 },
  { ..._w, symbol: 'PEP',   name: 'PepsiCo'                },
  { ..._w, symbol: 'WMT',   name: 'Walmart'                },
  { ..._w, symbol: 'KO',    name: 'Coca-Cola'              },
  // ── Financials ───────────────────────────────────────────────────────────
  { ..._w, symbol: 'MA',    name: 'Mastercard'             },
  { ..._w, symbol: 'V',     name: 'Visa'                   },
  { ..._w, symbol: 'JPM',   name: 'JPMorgan Chase'         },
  { ..._w, symbol: 'BRK.B', name: 'Berkshire Hathaway'     },
  { ..._w, symbol: 'BAC',   name: 'Bank of America'        },
  { ..._w, symbol: 'WFC',   name: 'Wells Fargo'            },
  // ── Healthcare ───────────────────────────────────────────────────────────
  { ..._w, symbol: 'JNJ',   name: 'Johnson & Johnson'      },
  // ── Real Estate ──────────────────────────────────────────────────────────
  { ..._w, symbol: 'O',     name: 'Realty Income'          },
  { ..._w, symbol: 'VICI',  name: 'VICI Properties'        },
  { ..._w, symbol: 'PLD',   name: 'Prologis'               },
  { ..._w, symbol: 'AMT',   name: 'American Tower'         },
  // ── Communication Services ────────────────────────────────────────────────
  { ..._w, symbol: 'DIS',   name: 'Walt Disney'            },
  { ..._w, symbol: 'VZ',    name: 'Verizon'                },
]

// ── Sector allocation ─────────────────────────────────────────────────────────
// Source: sample_data.py SECTOR_EXPOSURE

export const sectorAllocation = [
  { name: 'ETF',                    value: 22.08, target: 22.08, color: 'var(--chart-1)' },
  { name: 'Communication Services', value: 14.49, target: 14.49, color: 'var(--chart-3)' },
  { name: 'Technology',             value: 14.11, target: 14.11, color: 'var(--chart-2)' },
  { name: 'Cash',                   value: 18.59, target: 10.00, color: 'var(--muted-foreground)' },
  { name: 'Consumer Staples',       value: 12.57, target: 12.57, color: 'var(--chart-4)' },
  { name: 'Financials',             value:  6.15, target:  6.15, color: 'var(--chart-5)' },
  { name: 'Consumer Disc.',         value:  4.29, target:  4.29, color: 'var(--chart-1)' },
  { name: 'Real Estate',            value:  4.14, target:  4.14, color: 'var(--chart-2)' },
  { name: 'Healthcare',             value:  3.28, target:  3.28, color: 'var(--chart-3)' },
  { name: 'Materials',              value:  0.31, target:  0.31, color: 'var(--chart-4)' },
]

// ── Performance chart data ────────────────────────────────────────────────────
// Placeholder — no historical data available yet.

export const performanceData = [
  { date: 'Jan', portfolio: 12_000, benchmark: 12_000 },
  { date: 'Feb', portfolio: 12_200, benchmark: 12_100 },
  { date: 'Mar', portfolio: 12_400, benchmark: 12_200 },
  { date: 'Apr', portfolio: 13_100, benchmark: 12_500 },
  { date: 'May', portfolio: 14_833, benchmark: 13_000 },
]

// ── Market indices ────────────────────────────────────────────────────────────

export const marketIndices = [
  { name: "S&P 500",      symbol: 'SPX',  value:  5_234.82, change:  0.82, ytd: null },
  { name: 'Nasdaq',       symbol: 'IXIC', value: 16_428.34, change:  1.24, ytd: null },
  { name: 'Dow Jones',    symbol: 'DJI',  value: 39_245.67, change:  0.45, ytd: null },
  { name: 'Russell 2000', symbol: 'RUT',  value:  2_048.92, change: -0.32, ytd: null },
  { name: 'VIX',          symbol: 'VIX',  value:      21.4, change: -3.10, ytd: null },
]

// ── Intelligence / news ───────────────────────────────────────────────────────

export const aiInsights = [
  { type: 'opportunity' as const, title: 'GOOG at a strong entry point',      description: 'Cloud revenue beating estimates. Trades below fair value with a strong moat.',  confidence: 80, urgency: 'medium' as const },
  { type: 'risk'        as const, title: 'VZ dividend sustainability in focus', description: 'Three consecutive quarters of subscriber misses. FCF guidance trimmed. Monitor.',    confidence: 70, urgency: 'medium' as const },
  { type: 'alert'       as const, title: 'NVDA earnings this week',            description: 'NVDA reports Q1 FY2026. In portfolio. Expect elevated vol around the event.',       confidence: 95, urgency: 'high'   as const },
]

export const newsEvents = [
  { time: '1h ago',  title: 'Fed holds rates steady — NIM pressure eases for banks',           source: 'WSJ',       sentiment: 'neutral'  as const, ticker: null,   aiScore: 62 },
  { time: '2h ago',  title: 'Alphabet Q1: Cloud revenue beats estimates by 8%',                source: 'Bloomberg', sentiment: 'positive' as const, ticker: 'GOOG', aiScore: 83 },
  { time: '4h ago',  title: 'Verizon misses subscriber targets for third consecutive quarter', source: 'FT',        sentiment: 'negative' as const, ticker: 'VZ',   aiScore: 42 },
  { time: '1d ago',  title: 'NVIDIA data centre revenue surges 400% YoY — valuation stretched', source: 'CNBC',    sentiment: 'neutral'  as const, ticker: 'NVDA', aiScore: 55 },
]

// ── Risk alerts ───────────────────────────────────────────────────────────────

export const riskAlerts = [
  { severity: 'medium' as const, title: 'High Cash Position',  description: '18.6% in cash — above 10% target. Deploy into quality dips.' },
  { severity: 'low'    as const, title: 'ETF Concentration',   description: 'SCHD + VOO = 22.1% of portfolio. Intended for broad diversification.' },
  { severity: 'low'    as const, title: 'VZ Thesis Weakening', description: 'FCF guidance trimmed. Review dividend sustainability over next 2 quarters.' },
]

// ── Watchlist top movers ──────────────────────────────────────────────────────

export const topMovers = {
  gainers: [
    { symbol: 'GOOG', change: 2.10, price: 297.30, score: 0 },
    { symbol: 'MO',   change: 1.20, price:  72.14, score: 0 },
  ],
  losers: [
    { symbol: 'VZ',  change: -0.80, price: 48.13, score: 0 },
    { symbol: 'JNJ', change: -0.40, price: 170.63, score: 0 },
  ],
  nearBuyRange: [
    { symbol: 'PG', price: 158.90, buyBelow: 140.00, upside: 10.1 },
    { symbol: 'HD', price: 342.10, buyBelow: 288.00, upside:  5.2 },
  ],
}

// ── Risk metrics ──────────────────────────────────────────────────────────────

export const riskMetrics = {
  portfolioBeta:      1.0,
  volatility:          0.0,
  sharpeRatio:         0.0,
  sortinoRatio:        0.0,
  maxDrawdown:         0.0,
  var95:               0,
  concentrationRisk: 'Low',
  correlationToSPY:    0.0,
}

export const stressTests = [
  { scenario: '2008 Financial Crisis',  impact: -32.0, recovery: '18 months' },
  { scenario: 'COVID Crash (Mar 2020)', impact: -28.0, recovery: '5 months'  },
  { scenario: '10% Market Correction',  impact: -10.0, recovery: '3 months'  },
  { scenario: 'Rate Hike (+100bps)',     impact:  -6.0, recovery: '4 months'  },
]

// ── Markets page data ─────────────────────────────────────────────────────────

export const sectorPerformance = [
  { sector: 'Technology',       daily:  0.82, weekly:  2.10, monthly:  5.40 },
  { sector: 'Healthcare',       daily: -0.34, weekly: -0.80, monthly: -1.20 },
  { sector: 'Financials',       daily:  0.55, weekly:  1.20, monthly:  3.80 },
  { sector: 'Energy',           daily:  1.24, weekly:  2.80, monthly:  6.20 },
  { sector: 'Consumer Staples', daily: -0.12, weekly:  0.30, monthly:  1.10 },
  { sector: 'Industrials',      daily:  0.19, weekly:  0.90, monthly:  2.60 },
  { sector: 'Utilities',        daily: -0.58, weekly: -1.10, monthly: -2.40 },
  { sector: 'Real Estate',      daily: -0.89, weekly: -1.80, monthly: -3.20 },
  { sector: 'Materials',        daily:  0.33, weekly:  0.80, monthly:  2.10 },
  { sector: 'Communication',    daily:  0.63, weekly:  1.50, monthly:  4.20 },
  { sector: 'Consumer Disc.',   daily:  0.41, weekly:  1.00, monthly:  3.50 },
]

export const bondYields = [
  { name: '2Y Treasury',  yield: 4.72, change: -0.02 },
  { name: '10Y Treasury', yield: 4.28, change:  0.03 },
  { name: '30Y Treasury', yield: 4.45, change:  0.01 },
]

// ── Research / valuation default (shown before a search) ─────────────────────

export const valuationData = {
  symbol:        'AAPL',
  name:          'Apple Inc.',
  price:         189.84,
  dcfValue:      175.50,
  peRatio:        28.4,
  forwardPE:      25.2,
  pegRatio:        2.1,
  pbRatio:        42.8,
  evEbitda:       22.4,
  industryPE:     32.5,
  historicalPE:   26.8,
  analystTarget:  195.00,
  upside:           2.7,
}

export const geographicAllocation = [
  { name: 'United States',    value: 72.4 },
  { name: 'Europe',           value: 12.8 },
  { name: 'Asia Pacific',     value:  9.6 },
  { name: 'Emerging Markets', value:  5.2 },
]

export const earningsCalendar = [
  { date: 'May 20', symbol: 'NVDA', name: 'NVIDIA',           estimate: '$5.65', time: 'AMC' },
  { date: 'May 21', symbol: 'TGT',  name: 'Target',           estimate: '$2.12', time: 'BMO' },
  { date: 'May 22', symbol: 'COST', name: 'Costco',           estimate: '$3.75', time: 'AMC' },
  { date: 'May 23', symbol: 'DELL', name: 'Dell Technologies', estimate: '$1.42', time: 'AMC' },
]

export const commodities = [
  { name: 'Gold',        symbol: 'GC', price: 2342.50, change:  0.82, unit: '/oz'    },
  { name: 'Silver',      symbol: 'SI', price:   28.45, change:  1.24, unit: '/oz'    },
  { name: 'Crude Oil',   symbol: 'CL', price:   78.92, change: -0.56, unit: '/bbl'   },
  { name: 'Natural Gas', symbol: 'NG', price:    2.34, change: -2.12, unit: '/MMBtu' },
]

export const crypto = [
  { name: 'Bitcoin',  symbol: 'BTC', price: 67_842.34, change: 2.45 },
  { name: 'Ethereum', symbol: 'ETH', price:  3_524.82, change: 1.82 },
]

export const companyFinancials = {
  revenue: [
    { year: '2020', value: 274.5 },
    { year: '2021', value: 365.8 },
    { year: '2022', value: 394.3 },
    { year: '2023', value: 383.3 },
    { year: '2024E', value: 395.2 },
  ],
  eps: [
    { year: '2020', value: 3.28 },
    { year: '2021', value: 5.61 },
    { year: '2022', value: 6.11 },
    { year: '2023', value: 6.13 },
    { year: '2024E', value: 6.58 },
  ],
  margins: {
    gross:     45.8,
    operating: 30.2,
    net:       25.3,
  },
}
