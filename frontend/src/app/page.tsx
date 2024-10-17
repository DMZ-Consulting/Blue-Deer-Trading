'use client'

import React, { useState } from 'react'
import { PortfolioTableComponent } from '../components/PortfolioTable'
import { ReportAreaComponent } from '../components/ReportArea'
import { Button } from "@/components/ui/button"
import { PanelRightOpen, PanelRightClose } from 'lucide-react'
import { TradesTableComponent } from '@/components/TradesTable'

export default function Page() {
  const [isReportsVisible, setIsReportsVisible] = useState(true)

  const toggleReportsVisibility = () => {
    setIsReportsVisible(prev => !prev)
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm lg:flex">
        <div className={`flex-grow ${isReportsVisible ? 'w-3/4' : 'w-full'}`}>
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-3xl font-bold">Portfolio Dashboard</h1>
            <Button onClick={toggleReportsVisibility} variant="outline">
              {isReportsVisible ? <PanelRightClose className="w-4 h-4 mr-2" /> : <PanelRightOpen className="w-4 h-4 mr-2" />}
              {isReportsVisible ? "Hide Reports" : "Show Reports"}
            </Button>
          </div>
          <TradesTableComponent 
            configName="your_config_name"
          />
        </div>
      </div>
    </main>
  )
}
