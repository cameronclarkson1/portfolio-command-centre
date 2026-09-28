// AI HedgeFund — Service Worker
// Caches the app shell so it loads instantly on repeat visits.
// API calls always go to the network (never cached — data must be live).

const CACHE_NAME = 'ai-hedgefund-v1'

// Pages to pre-cache so they open instantly even on a slow connection
const PRECACHE_URLS = [
  '/',
  '/research',
  '/watchlist',
  '/portfolio',
  '/markets',
  '/opportunities',
  '/events',
  '/intelligence',
  '/risk',
  '/settings',
]

// ── Install: pre-cache the app shell ────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // addAll silently skips any URLs that fail (e.g. server not running locally)
      return Promise.allSettled(PRECACHE_URLS.map((url) => cache.add(url).catch(() => {})))
    })
  )
  // Activate immediately — don't wait for old tabs to close
  self.skipWaiting()
})

// ── Activate: clean up old cache versions ───────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  )
  self.clients.claim()
})

// ── Fetch: network-first for API, cache-first for everything else ────────────
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)

  // Always hit the network for:
  //  • backend API calls (Railway URL or /api/ paths)
  //  • POST/PUT/DELETE requests
  //  • Chrome extension requests
  const isApiCall =
    url.hostname.includes('railway.app') ||
    url.pathname.startsWith('/api/') ||
    event.request.method !== 'GET' ||
    url.protocol === 'chrome-extension:'

  if (isApiCall) {
    // Pure network — don't intercept
    return
  }

  // For everything else (pages, fonts, icons, JS bundles):
  // Try cache first, fall back to network, update cache in background
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const networkFetch = fetch(event.request)
        .then((response) => {
          // Only cache valid responses
          if (response && response.status === 200 && response.type === 'basic') {
            const cloned = response.clone()
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, cloned))
          }
          return response
        })
        .catch(() => cached) // If network fails and we have cache, use it

      // Return cache immediately if available, otherwise wait for network
      return cached || networkFetch
    })
  )
})
