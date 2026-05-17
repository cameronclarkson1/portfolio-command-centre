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
}

/** Returns false if the ticker is already in the stored list. */
export function addToWatchlist(item: WatchlistItem): boolean {
  const current = getStoredWatchlist() ?? []
  if (current.some((s) => s.symbol === item.symbol)) return false
  saveWatchlist([item, ...current])
  return true
}
