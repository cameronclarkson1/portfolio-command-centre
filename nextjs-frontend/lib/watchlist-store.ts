/**
 * Shared watchlist type + localStorage helpers.
 * Used by both watchlist-page.tsx (reads/writes) and research-page.tsx (writes).
 */

export type WatchlistItem = {
  symbol:        string
  name:          string
  price:         number
  change:        number
  changePercent: number
  fairValue:     number
  rating:        string    // 7-level: Strong Buy | Buy | Accumulate | Hold / Watchlist | Reduce | Sell | Strong Sell
  upside:        number
  safetyScore:   number    // 0-100, higher = safer (business/financial risk)
  sparkline:     number[]

  buyBelow?:       number | null   // manual target or fair_value_low from valuation

  // Optional score fields populated by /api/watchlist/refresh
  finalScore?:     number | null
  qualityScore?:   number | null
  growthScore?:    number | null
  valuationScore?: number | null
  confidence?:     number | null
  valuationStatus?: string | null
  lastUpdated?:    string | null   // ISO timestamp
  dataError?:      string | null
}

const STORAGE_KEY = 'ai_hedgefund_watchlist'
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://portfolio-command-centre-production.up.railway.app'

export function getStoredWatchlist(): WatchlistItem[] | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as WatchlistItem[]) : null
  } catch {
    return null
  }
}

export function saveWatchlist(items: WatchlistItem[]): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  } catch {}
  // Sync to server (fire and forget)
  fetch(`${API_BASE}/api/watchlist/items`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  }).catch(() => {})
}

/** Load watchlist from server, falling back to localStorage. */
export async function loadWatchlist(): Promise<WatchlistItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/watchlist/items`, { cache: 'no-store' })
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data.items) && data.items.length > 0) {
        // Sync to localStorage only — do NOT POST back to server (circular write).
        try { localStorage.setItem('ai_hedgefund_watchlist', JSON.stringify(data.items)) } catch {}
        return data.items as WatchlistItem[]
      }
    }
  } catch {}
  return getStoredWatchlist() ?? []
}

/** Returns false if the ticker is already in the stored list. */
export function addToWatchlist(item: WatchlistItem): boolean {
  const current = getStoredWatchlist() ?? []
  if (current.some((s) => s.symbol === item.symbol)) return false
  saveWatchlist([item, ...current])
  return true
}
