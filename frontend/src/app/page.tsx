'use client'

import { useState } from 'react'
import { TradesTableComponent } from '@/components/TradesTable'
import { OptionsStrategyTableComponent } from '@/components/OptionsStrategyTable'

// Import shadcn components
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

type TradeViewType = 'regular' | 'options' | 'strategy'
type StatusType = 'OPEN' | 'CLOSED'

export default function Home() {
  const [tradeView, setTradeView] = useState<TradeViewType>('regular')
  const [configName, setConfigName] = useState('swing_trader')
  const [statusFilter, setStatusFilter] = useState<StatusType>('OPEN')
  const [dateFilter, setDateFilter] = useState(() => {
    const now = new Date()
    return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())).toISOString().split('T')[0]
  })

  return (
    <main className="container mx-auto p-4 space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          <Button 
            variant={tradeView === 'regular' ? "default" : "outline"}
            onClick={() => setTradeView('regular')}
          >
            Regular Trades
          </Button>
          <Button 
            variant={tradeView === 'options' ? "default" : "outline"}
            onClick={() => setTradeView('options')}
          >
            Options Trades
          </Button>
          <Button 
            variant={tradeView === 'strategy' ? "default" : "outline"}
            onClick={() => setTradeView('strategy')}
          >
            Options Strategies
          </Button>
        </div>

        <div className="flex gap-4">
          <Select value={configName} onValueChange={setConfigName}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select trader type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="day_trader">Day Trader</SelectItem>
              <SelectItem value="swing_trader">Swing Trader</SelectItem>
              <SelectItem value="long_term_trader">Long Term Trader</SelectItem>
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={(value: StatusType) => setStatusFilter(value)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="OPEN">Open</SelectItem>
              <SelectItem value="CLOSED">Closed</SelectItem>
            </SelectContent>
          </Select>

          <input
            type="date"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="px-3 py-2 border rounded-md"
          />
        </div>
      </div>

      {tradeView === 'regular' && (
        <TradesTableComponent 
          configName={configName}
          filterOptions={{
            status: statusFilter.toLowerCase(),
            startDate: dateFilter,
            optionType: 'common'
          }}
        />
      )}

      {tradeView === 'options' && (
        <TradesTableComponent 
          configName={configName}
          filterOptions={{
            status: statusFilter.toLowerCase(),
            startDate: dateFilter,
            optionType: 'options'
          }}
        />
      )}

      {tradeView === 'strategy' && (
        <OptionsStrategyTableComponent 
          configName={configName}
          statusFilter={statusFilter}
          dateFilter={dateFilter}
        />
      )}
    </main>
  )
}
