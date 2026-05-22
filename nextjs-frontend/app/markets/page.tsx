export const dynamic = 'force-dynamic'

import { AppLayout }       from '@/components/app-layout'
import { MarketsPage }     from '@/components/markets-page'
import { fetchMarketsData } from '@/lib/api'

export default async function Markets() {
  const liveData = await fetchMarketsData()
  return (
    <AppLayout>
      <MarketsPage liveData={liveData} />
    </AppLayout>
  )
}
