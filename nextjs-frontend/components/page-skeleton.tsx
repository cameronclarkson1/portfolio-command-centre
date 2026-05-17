import { cn } from '@/lib/utils'

function Bone({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-muted', className)} />
}

function SkeletonCard({ rows = 3, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn('rounded-xl border border-border bg-card p-4 shadow-sm', className)}>
      <Bone className="h-4 w-32 mb-4" />
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <Bone key={i} className="h-8 w-full" />
        ))}
      </div>
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6 max-w-[1600px] mx-auto">
      <Bone className="h-8 w-48" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} rows={2} />)}
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <SkeletonCard rows={6} className="lg:col-span-2" />
        <div className="space-y-4">
          <SkeletonCard rows={4} />
          <SkeletonCard rows={3} />
        </div>
      </div>
    </div>
  )
}

export function MarketsSkeleton() {
  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6">
      <Bone className="h-8 w-32" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} rows={2} />)}
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <SkeletonCard rows={4} />
          <SkeletonCard rows={5} />
        </div>
        <div className="space-y-4">
          <SkeletonCard rows={4} />
          <SkeletonCard rows={3} />
        </div>
      </div>
    </div>
  )
}

export function IntelligenceSkeleton() {
  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6">
      <Bone className="h-8 w-40" />
      <SkeletonCard rows={4} />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <SkeletonCard rows={3} />
          <SkeletonCard rows={6} />
        </div>
        <div className="space-y-4">
          <SkeletonCard rows={3} />
          <SkeletonCard rows={4} />
        </div>
      </div>
    </div>
  )
}

export function PortfolioSkeleton() {
  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6">
      <Bone className="h-8 w-36" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} rows={2} />)}
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <SkeletonCard rows={8} className="lg:col-span-2" />
        <div className="space-y-4">
          <SkeletonCard rows={4} />
          <SkeletonCard rows={3} />
        </div>
      </div>
    </div>
  )
}

export function WatchlistSkeleton() {
  return (
    <div className="px-4 py-6 lg:px-8 lg:py-8 space-y-6">
      <div className="flex justify-between">
        <Bone className="h-8 w-36" />
        <Bone className="h-9 w-32" />
      </div>
      <Bone className="h-12 w-full rounded-lg" />
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} rows={4} />)}
      </div>
    </div>
  )
}
