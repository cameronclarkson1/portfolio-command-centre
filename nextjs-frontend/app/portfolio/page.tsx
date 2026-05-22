export const dynamic = 'force-dynamic'

import { AppLayout }    from '@/components/app-layout'
import { PortfolioPage } from '@/components/portfolio-page'
import { fetchPortfolio } from '@/lib/api'

export default async function Portfolio() {
  const apiData = await fetchPortfolio()
  return (
    <AppLayout>
      <PortfolioPage apiData={apiData} />
    </AppLayout>
  )
}
