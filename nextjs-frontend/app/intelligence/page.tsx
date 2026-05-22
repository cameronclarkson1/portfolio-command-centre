export const dynamic = 'force-dynamic'

import { AppLayout }           from '@/components/app-layout'
import { IntelligencePage }   from '@/components/intelligence-page'
import { fetchIntelligenceData } from '@/lib/api'

export default async function Intelligence() {
  const liveData = await fetchIntelligenceData()
  return (
    <AppLayout>
      <IntelligencePage liveData={liveData} />
    </AppLayout>
  )
}
