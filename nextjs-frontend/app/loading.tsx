import { AppLayout } from '@/components/app-layout'
import { DashboardSkeleton } from '@/components/page-skeleton'

export default function Loading() {
  return (
    <AppLayout>
      <DashboardSkeleton />
    </AppLayout>
  )
}
