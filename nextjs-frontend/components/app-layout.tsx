'use client'

import { ReactNode, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { APIStatus } from '@/components/api-status'
import {
  TrendingUp,
  Search,
  RefreshCw,
  Menu,
  X,
  LayoutDashboard,
  Star,
  FlaskConical,
  Brain,
  BarChart3,
  Calendar,
  Briefcase,
  Shield,
  Settings,
  Zap,
} from 'lucide-react'

// ── Navigation definition ────────────────────────────────────────────────────

const NAV_GROUPS = [
  {
    label: undefined as string | undefined,
    items: [{ href: '/', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    label: 'Research',
    items: [
      { href: '/watchlist',      label: 'Watchlist',      icon: Star },
      { href: '/research',       label: 'Stock Research',  icon: FlaskConical },
      { href: '/intelligence',   label: 'Intelligence',    icon: Brain },
      { href: '/opportunities',  label: 'Opportunities',   icon: Zap },
    ],
  },
  {
    label: 'Market',
    items: [
      { href: '/markets', label: 'Markets', icon: BarChart3 },
      { href: '/events',  label: 'Events',  icon: Calendar },
    ],
  },
  {
    label: 'Portfolio',
    items: [
      { href: '/portfolio', label: 'Portfolio',   icon: Briefcase },
      { href: '/risk',      label: 'Risk Centre', icon: Shield },
    ],
  },
  {
    label: 'System',
    items: [{ href: '/settings', label: 'Settings', icon: Settings }],
  },
]

// ── Helpers ──────────────────────────────────────────────────────────────────

function useMarketStatus() {
  // Always compare against Eastern Time — US markets are 9:30–16:00 ET
  const etDate     = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }))
  const day        = etDate.getDay()
  const h          = etDate.getHours()
  const m          = etDate.getMinutes()
  const isWeekday   = day >= 1 && day <= 5
  const afterOpen   = h > 9  || (h === 9  && m >= 30)
  const beforeClose = h < 16
  return { isOpen: isWeekday && afterOpen && beforeClose }
}

function formatNow() {
  return new Date().toLocaleString('en-GB', {
    weekday: 'short', day: '2-digit', month: 'short',
    year: 'numeric',  hour: '2-digit', minute: '2-digit',
    hour12: false,
  })
}

// ── Component ────────────────────────────────────────────────────────────────

export function AppLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)
  const { isOpen: marketOpen } = useMarketStatus()

  return (
    <div className="min-h-screen bg-background">

      {/* Top navigation */}
      <header className="sticky top-0 z-50 bg-[#0B1628] shadow-lg">

        {/* Brand row */}
        <div className="flex items-center justify-between px-4 py-2.5 lg:px-6">

          {/* Logo + name */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/10">
              <TrendingUp className="h-5 w-5 text-white" />
            </div>
            <div className="leading-tight">
              <p className="text-[15px] font-semibold text-white tracking-tight">AI HedgeFund</p>
              <p className="text-[10px] text-white/50 font-medium tracking-widest uppercase">Private Market Intelligence</p>
            </div>
          </div>

          {/* Search */}
          <div className="hidden md:flex items-center gap-2 bg-white/8 border border-white/10 rounded-lg px-3 py-1.5 w-72 hover:bg-white/12 transition-colors">
            <Search className="h-3.5 w-3.5 text-white/40 flex-shrink-0" />
            <input
              type="text"
              placeholder="Search ticker or company…"
              className="bg-transparent text-sm text-white/80 placeholder:text-white/35 outline-none flex-1 min-w-0"
            />
          </div>

          {/* Date · market status · refresh */}
          <div className="flex items-center gap-3">
            <span className="hidden lg:block text-xs text-white/45">{formatNow()}</span>

            <div className={cn(
              'flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium',
              marketOpen
                ? 'bg-emerald-500/15 text-emerald-400'
                : 'bg-white/8 text-white/50'
            )}>
              <span className={cn(
                'h-1.5 w-1.5 rounded-full',
                marketOpen ? 'bg-emerald-400 animate-pulse' : 'bg-white/40'
              )} />
              {marketOpen ? 'Market Open' : 'Market Closed'}
            </div>

            <APIStatus />

            <button
              onClick={() => window.location.reload()}
              className="hidden md:flex h-7 w-7 items-center justify-center rounded-md text-white/50 hover:bg-white/10 hover:text-white transition-colors"
              title="Refresh"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>

            <button
              onClick={() => setMobileOpen(true)}
              className="md:hidden flex h-7 w-7 items-center justify-center rounded-md text-white/60 hover:bg-white/10"
            >
              <Menu className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Nav row (desktop) */}
        <nav className="hidden md:flex items-center gap-0.5 px-4 lg:px-6 pb-1.5 overflow-x-auto hide-scrollbar border-t border-white/8 pt-1">
          {NAV_GROUPS.map((group, gi) => (
            <div key={gi} className="flex items-center">
              {gi > 0 && (
                <div className="h-3.5 w-px bg-white/15 mx-2 flex-shrink-0" />
              )}
              {group.label && (
                <span className="mr-1 text-[9px] font-bold uppercase tracking-widest text-white/30 flex-shrink-0 select-none">
                  {group.label}
                </span>
              )}
              {group.items.map((item) => {
                const active = pathname === item.href
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[12.5px] font-medium transition-all duration-150 whitespace-nowrap',
                      active
                        ? 'text-white bg-white/12'
                        : 'text-white/55 hover:text-white/85 hover:bg-white/8'
                    )}
                  >
                    <item.icon className="h-3.5 w-3.5 flex-shrink-0" />
                    {item.label}
                  </Link>
                )
              })}
            </div>
          ))}
        </nav>
      </header>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="absolute top-0 right-0 bottom-0 w-72 bg-[#0B1628] shadow-2xl overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <span className="text-sm font-semibold text-white">Navigation</span>
              <button
                onClick={() => setMobileOpen(false)}
                className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-white/10 text-white/60"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <nav className="p-3 space-y-0.5">
              {NAV_GROUPS.map((group, gi) => (
                <div key={gi} className={gi > 0 ? 'mt-3' : ''}>
                  {group.label && (
                    <p className="px-2 py-1 text-[9px] font-bold uppercase tracking-widest text-white/30">
                      {group.label}
                    </p>
                  )}
                  {group.items.map((item) => {
                    const active = pathname === item.href
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={() => setMobileOpen(false)}
                        className={cn(
                          'flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                          active ? 'bg-white/12 text-white' : 'text-white/60 hover:bg-white/8 hover:text-white/85'
                        )}
                      >
                        <item.icon className="h-4 w-4 flex-shrink-0" />
                        {item.label}
                      </Link>
                    )
                  })}
                </div>
              ))}
            </nav>
          </aside>
        </div>
      )}

      {/* Main content */}
      <main className="min-h-screen">
        {children}
      </main>
    </div>
  )
}
