'use client'

import React, { useState } from 'react'
import { Button } from "@/components/ui/button"
import { PanelRightOpen, PanelRightClose } from 'lucide-react'
import { TradesTableComponent } from '@/components/TradesTable'

export default function Page() {
  const [isReportsVisible, setIsReportsVisible] = useState(true)
  const [configName, setConfigName] = useState('day_trader')

  const toggleReportsVisibility = () => {
    setIsReportsVisible(prev => !prev)
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm lg:flex">
        <div className={`flex-grow ${isReportsVisible ? 'w-3/4' : 'w-full'}`}>
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-3xl font-bold">Trades</h1>
            <Button onClick={toggleReportsVisibility} variant="outline">
              {isReportsVisible ? <PanelRightClose className="w-4 h-4 mr-2" /> : <PanelRightOpen className="w-4 h-4 mr-2" />}
              {isReportsVisible ? "Hide Reports" : "Show Reports"}
            </Button>
          </div>
          <select
            value={configName}
            onChange={(e) => setConfigName(e.target.value)}
            className="mb-4 border p-2 rounded"
          >
            <option value="day_trader">Day Trader</option>
            <option value="swing_trader">Swing Trader</option>
            <option value="long_term_trader">Long Term Trader</option>
          </select>
          <TradesTableComponent 
            configName={configName}
          />
        </div>
      </div>
    </main>
  )
}
