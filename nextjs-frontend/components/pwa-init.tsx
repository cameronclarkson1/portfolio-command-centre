'use client'

// Registers the service worker once when the app first loads.
// This is a client component so it can use browser APIs (navigator).
import { useEffect } from 'react'

export function PWAInit() {
  useEffect(() => {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/sw.js')
        .then((reg) => {
          console.log('[PWA] Service worker registered:', reg.scope)
        })
        .catch((err) => {
          // Non-fatal — app works fine without it
          console.warn('[PWA] Service worker registration failed:', err)
        })
    }
  }, []) // Only runs once on mount

  // Renders nothing — purely a side-effect component
  return null
}
