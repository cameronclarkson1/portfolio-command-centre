import { AppLayout } from '@/components/app-layout'
import { WatchlistSkeleton } from '@/components/page-skeleton'

export default function Loading() {
  return (
    <AppLayout>
      <WatchlistSkeleton />
    </AppLayout>
  )
}
