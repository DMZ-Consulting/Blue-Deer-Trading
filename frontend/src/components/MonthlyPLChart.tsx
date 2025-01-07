import { useEffect, useState } from 'react'
import { getMonthlyPL } from '@/api/api'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

interface MonthlyPL {
  month: string
  profit_loss: number
}

interface MonthlyPLChartProps {
  configName: string
}

export default function MonthlyPLChart({ configName }: MonthlyPLChartProps) {
  const [monthlyPL, setMonthlyPL] = useState<MonthlyPL[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMonthlyPL = async () => {
      try {
        setLoading(true)
        const data = await getMonthlyPL(configName)
        setMonthlyPL(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch monthly P/L')
      } finally {
        setLoading(false)
      }
    }

    fetchMonthlyPL()
  }, [configName])

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>
  if (monthlyPL.length === 0) return <div>No data available</div>

  return (
    <div className="h-96 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={monthlyPL}
          margin={{
            top: 20,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="month" />
          <YAxis />
          <Tooltip
            formatter={(value: number) => [`$${value.toFixed(2)}`, 'P/L']}
          />
          <Bar dataKey="profit_loss">
            {monthlyPL.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.profit_loss >= 0 ? '#34D399' : '#EF4444'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
} 