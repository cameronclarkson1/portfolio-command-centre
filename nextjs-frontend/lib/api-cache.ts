// Lightweight in-browser cache for API responses.
// Prevents re-fetching the same data when navigating between pages.
// Uses a simple Map with TTLs — lost on page refresh, which is fine.

type Entry = { data: unknown; expiresAt: number }

const store = new Map<string, Entry>()

// TTLs in milliseconds
const TTL = {
  price:        60_000,   // 1 min  — prices change
  research:    300_000,   // 5 min  — fundamentals are stable
  market:       60_000,   // 1 min
  news:        300_000,   // 5 min
  portfolio:   300_000,   // 5 min
  watchlist:   120_000,   // 2 min
  events:      600_000,   // 10 min
  default:     120_000,   // 2 min
}

export type CacheCategory = keyof typeof TTL

export function getCached(key: string): unknown | null {
  const entry = store.get(key)
  if (!entry) return null
  if (Date.now() > entry.expiresAt) {
    store.delete(key)
    return null
  }
  return entry.data
}

export function setCached(key: string, data: unknown, category: CacheCategory = 'default') {
  store.set(key, {
    data,
    expiresAt: Date.now() + TTL[category],
  })
}

export function invalidate(prefix: string) {
  for (const key of store.keys()) {
    if (key.startsWith(prefix)) store.delete(key)
  }
}

// Wrapper: fetch with cache. Drop-in replacement for fetch() on GET requests.
// Usage: cachedFetch('/api/research?ticker=AAPL', 'research')
export async function cachedFetch(
  url: string,
  category: CacheCategory = 'default'
): Promise<unknown> {
  const cached = getCached(url)
  if (cached !== null) return cached

  const res = await fetch(url)
  if (!res.ok) throw new Error(`API error ${res.status}: ${url}`)

  const data = await res.json()
  setCached(url, data, category)
  return data
}
