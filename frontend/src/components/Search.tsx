'use client'

import React, { useState } from 'react'
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TradesTableComponent } from './TradesTable'

// Define configuration options
const TRADE_CONFIGS = [
  { value: "day_trader", label: "Day Trader" },
  { value: "swing_trader", label: "Swing Trader" },
  { value: "long_term_trader", label: "Long Term Trader" }
] as const;

// Define trade type options
const TRADE_TYPES = [
  { value: "all", label: "All" },
  { value: "options", label: "Options" },
  { value: "common", label: "Common" }
] as const;

export function SearchComponent() {
  type StatusType = 'all' | 'open' | 'closed'
  
  const [filters, setFilters] = useState({
    symbol: '',
    status: 'all' as StatusType,
    configName: 'all',
    minEntryPrice: '',
    maxEntryPrice: '',
    startDate: new Date().toISOString().split('T')[0],
    tradeType: 'all'
  })

  const handleFilterChange = (field: string, value: string) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleReset = () => {
    setFilters({
      symbol: '',
      status: 'all' as StatusType,
      configName: 'all',
      minEntryPrice: '',
      maxEntryPrice: '',
      startDate: new Date().toISOString().split('T')[0],
      tradeType: 'all'
    })
  }

  // Helper function to determine optionType
  const getOptionType = (tradeType: string): string | undefined => {
    switch (tradeType) {
      case 'options':
        return 'options';
      case 'common':
        return 'common';
      case 'all':
      default:
        return undefined;
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Search Trades</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label>Symbol</label>
              <Input
                placeholder="Enter symbol"
                value={filters.symbol}
                onChange={(e) => handleFilterChange('symbol', e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <label>Status</label>
              <Select
                value={filters.status}
                onValueChange={(value) => handleFilterChange('status', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="closed">Closed</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label>Trade Type</label>
              <Select
                value={filters.tradeType}
                onValueChange={(value) => handleFilterChange('tradeType', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select trade type" />
                </SelectTrigger>
                <SelectContent>
                  {TRADE_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label>Configuration</label>
              <Select
                value={filters.configName}
                onValueChange={(value) => handleFilterChange('configName', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select configuration" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Configurations</SelectItem>
                  {TRADE_CONFIGS.map((config) => (
                    <SelectItem key={config.value} value={config.value}>
                      {config.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label>Min Entry Price</label>
              <Input
                type="number"
                placeholder="Min price"
                value={filters.minEntryPrice}
                onChange={(e) => handleFilterChange('minEntryPrice', e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <label>Max Entry Price</label>
              <Input
                type="number"
                placeholder="Max price"
                value={filters.maxEntryPrice}
                onChange={(e) => handleFilterChange('maxEntryPrice', e.target.value)}
              />
            </div>
          </div>

          <div className="mt-4 flex justify-end space-x-2">
            <Button variant="outline" onClick={handleReset}>
              Reset Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      <TradesTableComponent
        configName={filters.configName}
        filterOptions={{
          status: filters.status === 'all' ? 'open' : filters.status,
          startDate: filters.startDate,
          optionType: getOptionType(filters.tradeType),
          symbol: filters.symbol || undefined,
          minEntryPrice: filters.minEntryPrice ? parseFloat(filters.minEntryPrice) : undefined,
          maxEntryPrice: filters.maxEntryPrice ? parseFloat(filters.maxEntryPrice) : undefined,
        }}
        showAllTrades={true}
      />
    </div>
  )
} 