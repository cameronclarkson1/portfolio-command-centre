import { AppLayout } from '@/components/app-layout'
import { MarketsSkeleton } from '@/components/page-skeleton'

export default function Loading() {
  return (
    <AppLayout>
      <MarketsSkeleton />
    </AppLayout>
  )
}
