export const dynamic = 'force-dynamic'

import { AppLayout }      from '@/components/app-layout'
import { DashboardPage }  from '@/components/dashboard-page'
import { fetchDashboardData } from '@/lib/api'

// This is a Next.js Server Component — it runs on the server at request time,
// fetches live data from the FastAPI backend, and passes it to the dashboard.
// If the API is offline the dashboard automatically falls back to mock data.
export default async function Home() {
  const liveData = await fetchDashboardData()

  return (
    <AppLayout>
      <DashboardPage liveData={liveData} />
    </AppLayout>
  )
}
