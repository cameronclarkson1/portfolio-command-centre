import { AppLayout } from '@/components/app-layout'
import { PortfolioSkeleton } from '@/components/page-skeleton'

export default function Loading() {
  return (
    <AppLayout>
      <PortfolioSkeleton />
    </AppLayout>
  )
}
