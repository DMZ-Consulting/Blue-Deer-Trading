'use client'

import { useState } from 'react'
import { TradesTableComponent } from '../components/TradesTable'
import { OptionsStrategyTableComponent } from '../components/OptionsStrategyTable'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'

// Import shadcn components
import { Button } from "../components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select"

export default function Home() {
  const [configName, setConfigName] = useState('swing_trader');
  const [statusFilter, setStatusFilter] = useState<'OPEN' | 'CLOSED'>('OPEN');

  return (
    <main className="container mx-auto p-4">
      <Tabs defaultValue="trades" className="w-full">
        <div className="flex justify-between items-center mb-4">
          <TabsList className="grid grid-cols-2 w-[300px]">
            <TabsTrigger value="trades">Trades</TabsTrigger>
            <TabsTrigger value="options">Options Strategies</TabsTrigger>
          </TabsList>
          
          <div className="flex gap-4">
            <Select value={configName} onValueChange={setConfigName}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Select trade group" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="day_trader">Day Trader</SelectItem>
                <SelectItem value="swing_trader">Swing Trader</SelectItem>
                <SelectItem value="long_term_trader">Long Term Trader</SelectItem>
                <SelectItem value="all">All Groups</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={(value: 'OPEN' | 'CLOSED') => setStatusFilter(value)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="OPEN">Open Trades</SelectItem>
                <SelectItem value="CLOSED">Closed Trades</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <TabsContent value="trades">
          <TradesTableComponent 
            configName={configName}
            filterOptions={{
              status: statusFilter
            }}
          />
        </TabsContent>
        <TabsContent value="options">
          <OptionsStrategyTableComponent 
            configName={configName}
            statusFilter={statusFilter}
          />
        </TabsContent>
      </Tabs>
    </main>
  );
}
