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

export default function Home() {
  const [tradeView, setTradeView] = useState<TradeViewType>('regular')
  const [configName, setConfigName] = useState('swing_trader')
  const [statusFilter, setStatusFilter] = useState<'OPEN' | 'CLOSED'>('OPEN')

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

          <Select value={statusFilter} onValueChange={(value: 'OPEN' | 'CLOSED') => setStatusFilter(value)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="OPEN">Open</SelectItem>
              <SelectItem value="CLOSED">Closed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {tradeView === 'regular' && (
        <TradesTableComponent 
          configName={configName}
          filterOptions={{
            status: statusFilter,
            optionType: 'common'
          }}
        />
      )}

      {tradeView === 'options' && (
        <TradesTableComponent 
          configName={configName}
          filterOptions={{
            status: statusFilter,
            optionType: 'options'
          }}
        />
      )}

      {tradeView === 'strategy' && (
        <OptionsStrategyTableComponent 
          configName={configName}
          statusFilter={statusFilter}
        />
      )}
    </main>
  )
}
