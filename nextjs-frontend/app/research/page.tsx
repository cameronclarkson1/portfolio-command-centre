export const dynamic = 'force-dynamic'

import { AppLayout } from '@/components/app-layout'
import { ResearchPage } from '@/components/research-page'

export default function Research({ searchParams }: { searchParams: { ticker?: string } }) {
  return (
    <AppLayout>
      <ResearchPage initialTicker={searchParams.ticker} />
    </AppLayout>
  )
}
