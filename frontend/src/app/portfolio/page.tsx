'use client'

import { useState, useEffect } from 'react'
import { PortfolioTableComponent } from '@/components/PortfolioTable'
import { ReportAreaComponent } from '@/components/ReportArea'
import { Button } from "@/components/ui/button"
import { PanelRightOpen, PanelRightClose } from 'lucide-react'
import { getPortfolio } from '@/api/api'
import { PortfolioTrade } from '@/utils/types'
import { Input } from '@/components/ui/input'

export default function PortfolioPage() {
  const [configName, setConfigName] = useState('day_trader')
  const [isReportsVisible, setIsReportsVisible] = useState(true)
  const [portfolio, setPortfolio] = useState<PortfolioTrade[]>([])
  const [loading, setLoading] = useState(true)
  const [dateFilter, setDateFilter] = useState(() => {
    const now = new Date();
    return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())).toISOString().split('T')[0];
  });

  const toggleReportsVisibility = () => {
    setIsReportsVisible(prev => !prev)
  }

  useEffect(() => {
    const fetchPortfolio = async () => {
      setLoading(true)
      const filterOptions = {
        weekFilter: dateFilter,
      }
      try {
        const fetchedPortfolio = await getPortfolio(configName, filterOptions)
        setPortfolio(fetchedPortfolio)
      } catch (error) {
        console.error('Error fetching portfolio:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchPortfolio()
  }, [configName, dateFilter])

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDateFilter(e.target.value)
  }

  return (
    <div id="portfolio-page" className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Blue Deer Trading Dashboard</h1>
        <Button onClick={toggleReportsVisibility} variant="outline">
          {isReportsVisible ? <PanelRightClose className="w-4 h-4 mr-2" /> : <PanelRightOpen className="w-4 h-4 mr-2" />}
          {isReportsVisible ? "Hide Reports" : "Show Reports"}
        </Button>
      </div>
      <div className="flex flex-col lg:flex-row gap-8">
        <div className={`lg:${isReportsVisible ? 'w-2/3' : 'w-full'}`}>
          <div className="mb-4 flex flex-wrap gap-4 items-center">
            <label className="block text-sm font-medium text-gray-700" htmlFor="trade-group">
              Select Trade Group
            </label>
            <select
              id="trade-group-selector"
              value={configName}
              onChange={(e) => setConfigName(e.target.value)}
              className="border p-2 rounded"
            >
              <option value="day_trader">Day Trader</option>
              <option value="swing_trader">Swing Trader</option>
              <option value="long_term_trader">Long Term Trader</option>
            </select>
            <Input
              type="date"
              value={dateFilter}
              onChange={handleDateChange}
              className="ml-4"
            />
          </div>
          {loading ? (
            <p>Loading portfolio...</p>
          ) : (
            <PortfolioTableComponent portfolio={portfolio} />
          )}
        </div>
        {isReportsVisible && (
          <div className="lg:w-1/3">
            <ReportAreaComponent portfolio={portfolio} />
          </div>
        )}
      </div>
    </div>
  )
}
