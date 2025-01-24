'use client'

import React, { useState } from 'react'
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TradesTableComponent } from './TradesTable'
import { cn } from "@/utils/cn"

type TradeConfig = {
  value: "day_trader" | "swing_trader" | "long_term_trader";
  label: string;
}

type TradeType = {
  value: "all" | "options" | "common";
  label: string;
}

// Define configuration options
const TRADE_CONFIGS: TradeConfig[] = [
  { value: "day_trader", label: "Day Trader" },
  { value: "swing_trader", label: "Swing Trader" },
  { value: "long_term_trader", label: "Long Term Trader" }
];

// Define trade type options
const TRADE_TYPES: TradeType[] = [
  { value: "all", label: "All" },
  { value: "options", label: "Options" },
  { value: "common", label: "Common" }
];

interface SearchComponentProps {
  allowTransactionActions?: boolean;
}

export function SearchComponent({ allowTransactionActions = false }: SearchComponentProps) {
  type StatusType = 'ALL' | 'OPEN' | 'CLOSED'
  type ConfigNameType = 'all' | TradeConfig['value']
  type TradeTypeValue = TradeType['value']
  
  interface FilterState {
    symbol: string;
    status: StatusType;
    configName: ConfigNameType;
    minEntryPrice: string;
    maxEntryPrice: string;
    startDate: string;
    tradeType: TradeTypeValue;
  }

  const [filters, setFilters] = useState<FilterState>({
    symbol: '',
    status: 'ALL',
    configName: 'all',
    minEntryPrice: '',
    maxEntryPrice: '',
    startDate: new Date().toISOString().split('T')[0],
    tradeType: 'all'
  })

  // Add date validation helper
  const isValidDate = (dateString: string) => {
    const date = new Date(dateString);
    return date instanceof Date && !isNaN(date.getTime());
  }

  // Modify handleFilterChange to include date validation
  const handleFilterChange = (field: keyof FilterState, value: string) => {
    if (field === 'startDate') {
      // Only update if it's a valid date or empty
      if (value === '' || isValidDate(value)) {
        setFilters(prev => ({
          ...prev,
          [field]: value
        }));
      }
      return;
    }

    setFilters(prev => ({
      ...prev,
      [field]: value
    }));
  }

  const handleReset = () => {
    setFilters({
      symbol: '',
      status: 'ALL',
      configName: 'all',
      minEntryPrice: '',
      maxEntryPrice: '',
      startDate: new Date().toISOString().split('T')[0],
      tradeType: 'all'
    })
  }

  // Helper function to determine optionType
  const getOptionType = (tradeType: TradeTypeValue): 'options' | 'common' | undefined => {
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
    <div className="space-y-4 max-w-[1200px] mx-auto px-4 py-6">
      <Card className="shadow-lg">
        <CardHeader className="border-b">
          <CardTitle>Search Trades</CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-medium">Symbol</label>
              <Input
                placeholder="Enter symbol"
                value={filters.symbol}
                onChange={(e) => handleFilterChange('symbol', e.target.value)}
                className="shadow-sm"
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">Status</label>
              <Select
                value={filters.status}
                onValueChange={(value: StatusType) => handleFilterChange('status', value)}
              >
                <SelectTrigger className="shadow-sm">
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All</SelectItem>
                  <SelectItem value="OPEN">Open</SelectItem>
                  <SelectItem value="CLOSED">Closed</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Trade Type</label>
              <Select
                value={filters.tradeType}
                onValueChange={(value: TradeTypeValue) => handleFilterChange('tradeType', value)}
              >
                <SelectTrigger className="shadow-sm">
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
              <label className="text-sm font-medium">Configuration</label>
              <Select
                value={filters.configName}
                onValueChange={(value: ConfigNameType) => handleFilterChange('configName', value)}
              >
                <SelectTrigger className="shadow-sm">
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
              <label className="text-sm font-medium">Min Entry Price</label>
              <Input
                type="number"
                placeholder="Min price"
                value={filters.minEntryPrice}
                onChange={(e) => handleFilterChange('minEntryPrice', e.target.value)}
                className={cn(
                  "shadow-sm",
                  parseFloat(filters.minEntryPrice) < 0 && "border-red-500"
                )}
                min="0"
                step="0.01"
              />
              {parseFloat(filters.minEntryPrice) < 0 && (
                <p className="text-xs text-red-500">Price cannot be negative</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Max Entry Price</label>
              <Input
                type="number"
                placeholder="Max price"
                value={filters.maxEntryPrice}
                onChange={(e) => handleFilterChange('maxEntryPrice', e.target.value)}
                className={cn(
                  "shadow-sm",
                  parseFloat(filters.maxEntryPrice) < 0 && "border-red-500"
                )}
                min="0"
                step="0.01"
              />
              {parseFloat(filters.maxEntryPrice) < 0 && (
                <p className="text-xs text-red-500">Price cannot be negative</p>
              )}
            </div>
          </div>

          <div className="mt-6 flex justify-end space-x-2">
            <Button 
              variant="outline" 
              onClick={handleReset}
              className="shadow-sm hover:bg-gray-100"
            >
              Reset Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="bg-white rounded-lg shadow-lg p-4">
        <TradesTableComponent
          configName={filters.configName === 'all' ? '' : filters.configName}
          filterOptions={{
            status: filters.status,
            startDate: isValidDate(filters.startDate) ? filters.startDate : undefined,
            optionType: getOptionType(filters.tradeType),
            symbol: filters.symbol === '' ? undefined : filters.symbol,
            minEntryPrice: filters.minEntryPrice && !isNaN(parseFloat(filters.minEntryPrice)) 
              ? parseFloat(filters.minEntryPrice) 
              : undefined,
            maxEntryPrice: filters.maxEntryPrice && !isNaN(parseFloat(filters.maxEntryPrice)) 
              ? parseFloat(filters.maxEntryPrice) 
              : undefined,
          }}
          showAllTrades={filters.configName === 'all'}
          allowTransactionActions={allowTransactionActions}
        />
      </div>
    </div>
  )
} 