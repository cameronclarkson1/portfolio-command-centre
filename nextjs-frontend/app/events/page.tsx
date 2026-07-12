export const dynamic = 'force-dynamic'

import { AppLayout }                                        from '@/components/app-layout'
import { EventsPage }                                       from '@/components/events-page'
import { fetchPortfolioEarnings, fetchMacroEvents, fetchDividends } from '@/lib/api'

export default async function Events() {
  const [apiEarnings, apiMacro, dividendsData] = await Promise.all([
    fetchPortfolioEarnings(),
    fetchMacroEvents(),
    fetchDividends(),
  ])

  return (
    <AppLayout>
      <EventsPage
        apiEarnings={apiEarnings}
        apiMacro={apiMacro}
        apiDividends={dividendsData?.upcoming ?? null}
      />
    </AppLayout>
  )
}
