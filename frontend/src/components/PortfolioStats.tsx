import { useEffect, useState } from 'react'
import { calculatePortfolioStats } from '../../lib/portfolio'

interface PortfolioStats {
  totalTrades: number
  winRate: number
  averageWin: number
  averageLoss: number
  profitFactor: number
  totalProfitLoss: number
  averageRiskRewardRatio: number
}

interface PortfolioStatsProps {
  configName: string
  status: string
  weekFilter?: string
  optionType?: string
}

export default function PortfolioStats({ configName, status, weekFilter, optionType }: PortfolioStatsProps) {
  const [stats, setStats] = useState<PortfolioStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true)
        const data = await calculatePortfolioStats(configName, status, weekFilter, optionType)
        setStats(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch portfolio stats')
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [configName, status, weekFilter, optionType])

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>
  if (!stats) return <div>No stats available</div>

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Total Trades</h3>
        <p className="mt-2 text-3xl font-semibold text-gray-700">{stats.totalTrades}</p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Win Rate</h3>
        <p className="mt-2 text-3xl font-semibold text-gray-700">
          {(stats.winRate * 100).toFixed(1)}%
        </p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Average Win</h3>
        <p className="mt-2 text-3xl font-semibold text-green-600">
          ${stats.averageWin.toFixed(2)}
        </p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Average Loss</h3>
        <p className="mt-2 text-3xl font-semibold text-red-600">
          ${stats.averageLoss.toFixed(2)}
        </p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Profit Factor</h3>
        <p className="mt-2 text-3xl font-semibold text-gray-700">
          {stats.profitFactor.toFixed(2)}
        </p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Total P/L</h3>
        <p className={`mt-2 text-3xl font-semibold ${
          stats.totalProfitLoss >= 0 ? 'text-green-600' : 'text-red-600'
        }`}>
          ${stats.totalProfitLoss.toFixed(2)}
        </p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Avg R:R Ratio</h3>
        <p className="mt-2 text-3xl font-semibold text-gray-700">
          {stats.averageRiskRewardRatio.toFixed(2)}
        </p>
      </div>
    </div>
  )
} 