export const dynamic = 'force-dynamic'

import { AppLayout }         from '@/components/app-layout'
import { OpportunitiesPage } from '@/components/opportunities-page'
import { fetchScannerResults, fetchScannerStatus } from '@/lib/api'

export const metadata = { title: 'Best Opportunities | AI HedgeFund' }

export default async function Page() {
  const [results, status] = await Promise.all([
    fetchScannerResults(),
    fetchScannerStatus(),
  ])

  return (
    <AppLayout>
      <OpportunitiesPage initialResults={results} initialStatus={status} />
    </AppLayout>
  )
}
