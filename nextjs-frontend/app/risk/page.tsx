import { AppLayout }       from '@/components/app-layout'
import { RiskPage }        from '@/components/risk-page'
import { fetchPortfolioRisk } from '@/lib/api'

export default async function Risk() {
  const apiData = await fetchPortfolioRisk()
  return (
    <AppLayout>
      <RiskPage apiData={apiData} />
    </AppLayout>
  )
}
