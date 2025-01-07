import { useEffect, useState } from 'react'
import { api } from '../api/api'
import { Database } from '../../lib/database.types'

type Trade = Database['public']['Tables']['trades']['Row'] & {
  trade_configurations: Database['public']['Tables']['trade_configurations']['Row'] | null
}

interface TradeListProps {
  configName: string
  status: string
  weekFilter?: string
  optionType?: string
}

export default function TradeList({ configName, status, weekFilter, optionType }: TradeListProps) {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTrades = async () => {
      try {
        setLoading(true)
        const data = await api.trades.getByStatus(status)
        // Filter trades based on configuration name
        const filteredTrades = data.filter(trade => 
          trade.trade_configurations?.name === configName || configName === 'all'
        )
        setTrades(filteredTrades)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch trades')
      } finally {
        setLoading(false)
      }
    }

    fetchTrades()
  }, [configName, status, weekFilter, optionType])

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>
  if (trades.length === 0) return <div>No trades found</div>

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Symbol
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Entry Price
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Exit Price
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              P/L
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {trades.map((trade) => (
            <tr key={trade.trade_id}>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {trade.symbol}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {trade.trade_type}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                ${trade.entry_price.toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : '-'}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {trade.profit_loss ? `$${trade.profit_loss.toFixed(2)}` : '-'}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {trade.status}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
} 