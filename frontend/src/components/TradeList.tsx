import { useState, useEffect } from 'react'
import { api } from '@/api/api'
import { Trade } from '@/utils/types'

interface TradeListProps {
  configName: string
  status: 'OPEN' | 'CLOSED'
  weekFilter?: string
}

export default function TradeList({ configName, status, weekFilter }: TradeListProps) {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTrades = async () => {
      try {
        setLoading(true)
        const data = await api.trades.getByFilters({
          status,
          configName,
          weekFilter
        })
        setTrades(data as Trade[])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch trades')
      } finally {
        setLoading(false)
      }
    }

    fetchTrades()
  }, [configName, status, weekFilter])

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>
  if (trades.length === 0) return <div>No trades found</div>

  return (
    <div>
      {trades.map(trade => (
        <div key={trade.trade_id} className="mb-4">
          <h3>{trade.symbol}</h3>
          <p>Status: {trade.status}</p>
          <p>Entry Price: ${trade.entry_price}</p>
          {trade.exit_price && <p>Exit Price: ${trade.exit_price}</p>}
          {trade.profit_loss && <p>P/L: ${trade.profit_loss}</p>}
        </div>
      ))}
    </div>
  )
} 