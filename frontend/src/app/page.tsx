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
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="trades">Trades</TabsTrigger>
          <TabsTrigger value="options">Options Strategies</TabsTrigger>
        </TabsList>
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
