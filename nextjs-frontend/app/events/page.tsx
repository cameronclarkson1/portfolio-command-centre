export const dynamic = 'force-dynamic'

import { AppLayout }          from '@/components/app-layout'
import { EventsPage }         from '@/components/events-page'
import { fetchPortfolioEarnings } from '@/lib/api'

export default async function Events() {
  const apiEarnings = await fetchPortfolioEarnings()
  return (
    <AppLayout>
      <EventsPage apiEarnings={apiEarnings} />
    </AppLayout>
  )
}
