import { AppLayout }          from '@/components/app-layout'
import { WatchlistPage }     from '@/components/watchlist-page'
import { fetchWatchlistPrices } from '@/lib/api'
import { watchlist }         from '@/lib/mock-data'

export default async function Watchlist() {
  const tickers   = watchlist.map((s) => s.symbol)
  const livePrices = await fetchWatchlistPrices(tickers)
  return (
    <AppLayout>
      <WatchlistPage livePrices={livePrices} />
    </AppLayout>
  )
}
