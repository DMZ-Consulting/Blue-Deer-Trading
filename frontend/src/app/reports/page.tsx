'use client'

import { useState, useEffect } from 'react'
import { Card, Title, LineChart, BarChart, Metric, Text, Flex, Grid } from '@tremor/react'
import { getMonthlyPL } from '@/api/api'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { api } from '@/api/api'

const TRADE_GROUPS = [
  { value: "day_trader", label: "Day Trader" },
  { value: "swing_trader", label: "Swing Trader" },
  { value: "long_term_trader", label: "Long Term Trader" },
  { value: "full_access", label: "Full Access" }
] as const

interface MonthlyPL {
  month: string
  profit_loss: number
}

interface PortfolioStats {
  totalTrades: number
  winRate: number
  averageWin: number
  averageLoss: number
  profitFactor: number
  totalProfitLoss: number
  averageRiskRewardRatio: number
}

export default function ReportsPage() {
  const [selectedGroup, setSelectedGroup] = useState<string>('day_trader')
  const [monthlyData, setMonthlyData] = useState<MonthlyPL[]>([])
  const [stats, setStats] = useState<PortfolioStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [monthlyPLData, statsData] = await Promise.all([
          getMonthlyPL(selectedGroup === 'full_access' ? undefined : selectedGroup),
          api.portfolio.getStats({
            configName: selectedGroup === 'full_access' ? 'all' : selectedGroup,
            status: 'CLOSED'
          })
        ])
        setMonthlyData(monthlyPLData)
        setStats(statsData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [selectedGroup])

  const chartData = monthlyData.map(item => ({
    month: item.month,
    "Profit/Loss": item.profit_loss
  }))

  return (
    <main className="container mx-auto p-4 space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Trading Performance Reports</h1>
        <Select value={selectedGroup} onValueChange={setSelectedGroup}>
          <SelectTrigger className="w-[180px]">
            <SelectValue>
              {TRADE_GROUPS.find(group => group.value === selectedGroup)?.label}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {TRADE_GROUPS.map((group) => (
              <SelectItem key={group.value} value={group.value}>
                {group.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="h-96 flex items-center justify-center">Loading...</div>
      ) : error ? (
        <div className="h-96 flex items-center justify-center text-red-500">{error}</div>
      ) : (
        <>
          <Grid numItems={1} numItemsSm={2} numItemsLg={4} className="gap-6">
            <Card>
              <Text>Total Trades</Text>
              <Metric>{stats?.totalTrades || 0}</Metric>
            </Card>
            <Card>
              <Text>Win Rate</Text>
              <Metric>{((stats?.winRate || 0) * 100).toFixed(1)}%</Metric>
            </Card>
            <Card>
              <Text>Profit Factor</Text>
              <Metric>{(stats?.profitFactor || 0).toFixed(2)}</Metric>
            </Card>
            <Card>
              <Text>Total P/L</Text>
              <Metric className={stats?.totalProfitLoss && stats.totalProfitLoss >= 0 ? 'text-emerald-500' : 'text-red-500'}>
                ${(stats?.totalProfitLoss || 0).toFixed(2)}
              </Metric>
            </Card>
          </Grid>

          <Card>
            <Title>Monthly Performance</Title>
            {monthlyData.length === 0 ? (
              <div className="h-72 flex items-center justify-center">No data available</div>
            ) : (
              <LineChart
                className="h-72 mt-4"
                data={chartData}
                index="month"
                categories={["Profit/Loss"]}
                colors={["emerald"]}
                valueFormatter={(value) => `$${value.toFixed(2)}`}
                yAxisWidth={60}
              />
            )}
          </Card>

          <Grid numItems={1} numItemsSm={2} className="gap-6">
            <Card>
              <Title>Average Win/Loss</Title>
              <BarChart
                className="h-40 mt-4"
                data={[
                  {
                    name: "Average",
                    "Win": stats?.averageWin || 0,
                    "Loss": Math.abs(stats?.averageLoss || 0)
                  }
                ]}
                index="name"
                categories={["Win", "Loss"]}
                colors={["emerald", "red"]}
                valueFormatter={(value) => `$${value.toFixed(2)}`}
                stack={false}
              />
            </Card>
            <Card>
              <Title>Risk/Reward Metrics</Title>
              <div className="mt-4">
                <Flex>
                  <Text>Average R:R Ratio</Text>
                  <Text>{(stats?.averageRiskRewardRatio || 0).toFixed(2)}</Text>
                </Flex>
                <Flex className="mt-2">
                  <Text>Win Rate</Text>
                  <Text>{((stats?.winRate || 0) * 100).toFixed(1)}%</Text>
                </Flex>
                <Flex className="mt-2">
                  <Text>Profit Factor</Text>
                  <Text>{(stats?.profitFactor || 0).toFixed(2)}</Text>
                </Flex>
              </div>
            </Card>
          </Grid>
        </>
      )}
    </main>
  )
} 
