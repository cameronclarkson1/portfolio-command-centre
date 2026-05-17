import { AppLayout } from '@/components/app-layout'
import { IntelligenceSkeleton } from '@/components/page-skeleton'

export default function Loading() {
  return (
    <AppLayout>
      <IntelligenceSkeleton />
    </AppLayout>
  )
}
