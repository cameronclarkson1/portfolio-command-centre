'use client'

import { useState, useEffect, useCallback } from 'react'
import { 
  Settings, 
  User,
  Bell,
  Moon,
  Sun,
  Shield,
  Key,
  Plug,
  Star,
  ChevronRight,
  Check,
  Smartphone,
  Mail,
  Globe,
} from 'lucide-react'
import { SectionHeader, StatusBadge } from '@/components/ui-components'
import { useTheme } from 'next-themes'
import { cn } from '@/lib/utils'

const profileSettings = {
  name: 'John Doe',
  email: 'john.doe@hedgefund.com',
  phone: '+1 (555) 123-4567',
  timezone: 'America/New_York',
  currency: 'USD',
}

const notificationSettings = [
  { id: 'price_alerts', label: 'Price Alerts', description: 'Get notified when stocks hit target prices', enabled: true },
  { id: 'portfolio_updates', label: 'Portfolio Updates', description: 'Daily summary of portfolio performance', enabled: true },
  { id: 'ai_insights', label: 'AI Insights', description: 'AI-generated market and portfolio insights', enabled: true },
  { id: 'earnings', label: 'Earnings Alerts', description: 'Notifications for upcoming earnings', enabled: false },
  { id: 'risk_alerts', label: 'Risk Alerts', description: 'Alerts when risk thresholds are breached', enabled: true },
  { id: 'news', label: 'Breaking News', description: 'Real-time market news notifications', enabled: false },
]

interface ProviderStatus {
  id:          string
  name:        string
  description: string
  status:      'connected' | 'no_key' | 'error'
  latency_ms:  number | null
}

const riskProfileOptions = [
  { id: 'conservative', label: 'Conservative', description: 'Low risk tolerance, focus on capital preservation' },
  { id: 'moderate', label: 'Moderate', description: 'Balanced approach to risk and return' },
  { id: 'aggressive', label: 'Aggressive', description: 'High risk tolerance, growth-focused' },
]

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function apiSave(body: object) {
  try {
    await fetch(`${API}/api/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch { /* API offline — silently ignore */ }
}

export function SettingsPage() {
  const [notifications, setNotifications]   = useState(notificationSettings)
  const [riskProfile, setRiskProfile]       = useState('moderate')
  const [saved, setSaved]                   = useState(false)
  const [providers, setProviders]           = useState<ProviderStatus[]>([])
  const [providersLoading, setProvidersLoading] = useState(true)
  const { theme, setTheme } = useTheme()
  const darkMode = theme === 'dark'

  // Load persisted settings on mount
  useEffect(() => {
    fetch(`${API}/api/settings`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data) return
        if (data.risk_profile)  setRiskProfile(data.risk_profile)
        if (data.notifications) {
          setNotifications(prev => prev.map(n => ({
            ...n,
            enabled: data.notifications[n.id] ?? n.enabled,
          })))
        }
      })
      .catch(() => {})

    fetch(`${API}/api/health/providers`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (Array.isArray(data)) setProviders(data)
      })
      .catch(() => {})
      .finally(() => setProvidersLoading(false))
  }, [])

  const flashSaved = useCallback(() => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }, [])

  const toggleNotification = (id: string) => {
    setNotifications(prev => {
      const next = prev.map(n => n.id === id ? { ...n, enabled: !n.enabled } : n)
      const notifMap = Object.fromEntries(next.map(n => [n.id, n.enabled]))
      apiSave({ notifications: notifMap })
      return next
    })
  }

  const selectRiskProfile = (id: string) => {
    setRiskProfile(id)
    apiSave({ risk_profile: id })
    flashSaved()
  }

  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-muted">
          <Settings className="h-6 w-6 text-foreground" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Settings</h1>
          <p className="text-sm text-muted-foreground">Manage your account and preferences</p>
        </div>
        {saved && (
          <span className="ml-auto text-xs text-success font-medium flex items-center gap-1">
            <Check className="h-3 w-3" /> Saved
          </span>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Profile Settings */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader 
              title="Profile"
              action={
                <button className="text-xs text-primary font-medium hover:underline">
                  Edit Profile
                </button>
              }
            />
            <div className="mt-4 flex items-start gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-xl font-semibold text-primary-foreground">
                JD
              </div>
              <div className="flex-1 space-y-3">
                <div>
                  <p className="text-lg font-semibold text-foreground">{profileSettings.name}</p>
                  <p className="text-sm text-muted-foreground">Pro Account</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center gap-2">
                    <Mail className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">{profileSettings.email}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Smartphone className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">{profileSettings.phone}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">{profileSettings.timezone}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Notification Settings */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader 
              title="Notifications"
              action={<Bell className="h-4 w-4 text-muted-foreground" />}
            />
            <div className="mt-4 space-y-1">
              {notifications.map((notification) => (
                <div 
                  key={notification.id}
                  className="flex items-center justify-between py-3 border-b border-border last:border-0"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">{notification.label}</p>
                    <p className="text-xs text-muted-foreground">{notification.description}</p>
                  </div>
                  <button
                    onClick={() => toggleNotification(notification.id)}
                    className={cn(
                      'relative h-6 w-11 rounded-full transition-colors',
                      notification.enabled ? 'bg-primary' : 'bg-muted'
                    )}
                  >
                    <span
                      className={cn(
                        'absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform',
                        notification.enabled && 'translate-x-5'
                      )}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Risk Profile */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader 
              title="Risk Profile"
              action={<Shield className="h-4 w-4 text-muted-foreground" />}
            />
            <div className="mt-4 space-y-2">
              {riskProfileOptions.map((option) => (
                <button
                  key={option.id}
                  onClick={() => selectRiskProfile(option.id)}
                  className={cn(
                    'w-full flex items-center justify-between p-4 rounded-lg border transition-all text-left',
                    riskProfile === option.id 
                      ? 'border-primary bg-primary/5' 
                      : 'border-border hover:border-primary/50'
                  )}
                >
                  <div>
                    <p className="text-sm font-medium text-foreground">{option.label}</p>
                    <p className="text-xs text-muted-foreground">{option.description}</p>
                  </div>
                  {riskProfile === option.id && (
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary">
                      <Check className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Portfolio Preferences */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Portfolio Preferences" />
            <div className="mt-4 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Maximum Sector Allocation</p>
                  <p className="text-xs text-muted-foreground">Alert when sector exceeds this threshold</p>
                </div>
                <select className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20">
                  <option>25%</option>
                  <option>30%</option>
                  <option>35%</option>
                  <option>40%</option>
                </select>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Cash Buffer Target</p>
                  <p className="text-xs text-muted-foreground">Minimum cash allocation</p>
                </div>
                <select className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20">
                  <option>3%</option>
                  <option>5%</option>
                  <option>10%</option>
                  <option>15%</option>
                </select>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Rebalancing Frequency</p>
                  <p className="text-xs text-muted-foreground">How often to suggest rebalancing</p>
                </div>
                <select className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20">
                  <option>Weekly</option>
                  <option>Monthly</option>
                  <option>Quarterly</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Theme Toggle */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader title="Appearance" />
            <div className="mt-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {darkMode ? <Moon className="h-5 w-5 text-foreground" /> : <Sun className="h-5 w-5 text-foreground" />}
                  <span className="text-sm font-medium text-foreground">{darkMode ? 'Dark Mode' : 'Light Mode'}</span>
                </div>
                <button
                  onClick={() => setTheme(darkMode ? 'light' : 'dark')}
                  className={cn(
                    'relative h-6 w-11 rounded-full transition-colors',
                    darkMode ? 'bg-primary' : 'bg-muted'
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform',
                      darkMode && 'translate-x-5'
                    )}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* Integrations — live provider health */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader
              title="Data Providers"
              action={<Plug className="h-4 w-4 text-muted-foreground" />}
            />
            <div className="mt-3 space-y-2">
              {providersLoading ? (
                <div className="space-y-2">
                  {[1,2,3,4].map(i => (
                    <div key={i} className="h-14 rounded-lg bg-accent/30 animate-pulse" />
                  ))}
                </div>
              ) : providers.length === 0 ? (
                <p className="py-4 text-center text-xs text-muted-foreground">API offline — provider status unavailable</p>
              ) : (
                providers.map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-accent/30"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent flex-shrink-0">
                        <Plug className="h-4 w-4 text-foreground" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{p.name}</p>
                        <p className="text-[10px] text-muted-foreground truncate">{p.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                      {p.latency_ms != null && (
                        <span className="text-[10px] text-muted-foreground">{p.latency_ms}ms</span>
                      )}
                      <StatusBadge status={
                        p.status === 'connected' ? 'positive'
                        : p.status === 'no_key'  ? 'neutral'
                        : 'negative'
                      }>
                        {p.status === 'connected' ? 'Live'
                         : p.status === 'no_key'  ? 'No Key'
                         : 'Error'}
                      </StatusBadge>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Security */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader 
              title="Security"
              action={<Key className="h-4 w-4 text-muted-foreground" />}
            />
            <div className="mt-3 space-y-2">
              <button className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-accent transition-colors">
                <div className="flex items-center gap-3">
                  <Key className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-foreground">Change Password</span>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>
              <button className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-accent transition-colors">
                <div className="flex items-center gap-3">
                  <Shield className="h-4 w-4 text-muted-foreground" />
                  <div className="text-left">
                    <span className="text-sm text-foreground block">Two-Factor Auth</span>
                    <span className="text-xs text-success">Enabled</span>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>
              <button className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-accent transition-colors">
                <div className="flex items-center gap-3">
                  <Smartphone className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-foreground">Active Sessions</span>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>
            </div>
          </div>

          {/* Watchlist Management */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <SectionHeader 
              title="Watchlists"
              action={<Star className="h-4 w-4 text-muted-foreground" />}
            />
            <div className="mt-3 space-y-2">
              <div className="flex items-center justify-between p-3 rounded-lg bg-accent/30">
                <span className="text-sm text-foreground">Main Watchlist</span>
                <span className="text-xs text-muted-foreground">5 securities</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-accent/30">
                <span className="text-sm text-foreground">Tech Stocks</span>
                <span className="text-xs text-muted-foreground">12 securities</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-accent/30">
                <span className="text-sm text-foreground">Dividend Plays</span>
                <span className="text-xs text-muted-foreground">8 securities</span>
              </div>
            </div>
            <button className="mt-3 w-full rounded-lg border border-dashed border-border py-2.5 text-sm font-medium text-muted-foreground hover:border-primary hover:text-primary transition-colors">
              + Create Watchlist
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
