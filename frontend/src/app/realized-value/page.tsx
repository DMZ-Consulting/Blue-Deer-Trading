'use client';

import { useState, useEffect } from 'react';
import { RealizedValueTable } from '@/components/RealizedValueTable';
import { PositionSizingConfig } from '@/types/position-sizing';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/utils/cn";

// Update the type to include 'all' as a possible value
type TimeframeSelection = keyof PositionSizingConfig | 'all';

const TIMEFRAME_TO_CONFIG: Record<keyof PositionSizingConfig, string> = {
  dayTrading: 'day_trader',
  swingTrading: 'swing_trader',
  longTermInvesting: 'long_term_trader'
};

interface RealizedPL {
  dayTrading: number;
  swingTrading: number;
  longTermInvesting: number;
  all: number;
}

export default function RealizedValuePage() {
  const [config, setConfig] = useState<PositionSizingConfig>({
    dayTrading: {
      portfolioSize: 250000,
      riskTolerancePercent: 5
    },
    swingTrading: {
      portfolioSize: 500000,
      riskTolerancePercent: 5
    },
    longTermInvesting: {
      portfolioSize: 250000,
      riskTolerancePercent: 5
    }
  });
  const [realizedPL, setRealizedPL] = useState<RealizedPL>({
    dayTrading: 0,
    swingTrading: 0,
    longTermInvesting: 0,
    all: 0
  });
  const [selectedTimeframe, setSelectedTimeframe] = useState<TimeframeSelection>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Simulate loading state for demo purposes
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  // Helper function to get the configuration for the table
  const getTableConfig = (timeframe: TimeframeSelection) => {
    if (timeframe === 'all') {
      // For 'all', use the total portfolio size and average risk tolerance
      const totalSize = Object.values(config).reduce((total, timeframe) => total + timeframe.portfolioSize, 0);
      const avgRiskTolerance = Object.values(config).reduce(
        (sum, tf) => sum + tf.riskTolerancePercent,
        0
      ) / Object.values(config).length;

      return {
        portfolioSize: totalSize,
        riskTolerancePercent: avgRiskTolerance
      };
    }
    return config[timeframe];
  };

  const handleRealizedPLUpdate = (timeframe: TimeframeSelection, value: number) => {
    setRealizedPL(prev => ({
      ...prev,
      [timeframe]: value
    }));
  };

  if (isLoading) {
    return (
      <main className="container mx-auto p-4">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="container mx-auto p-4">
        <div className="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error}</span>
        </div>
      </main>
    );
  }

  return (
    <main className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Realized Value Calculator</h1>
      
      <div className="mt-6">
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-3">Realized Value Summary</h2>
          
          {/* Total Portfolio Summary */}
          <div className="bg-blue-50 p-6 rounded-lg max-w-md mx-auto">
            <h3 className="text-lg font-semibold text-blue-800 mb-4">Total Portfolio</h3>
            <div className="space-y-3">
              <div>
                <p className="text-sm text-gray-600">Day Trading P/L</p>
                <p className={cn(
                  "text-lg font-semibold",
                  realizedPL.dayTrading > 0 ? "text-green-600" : 
                  realizedPL.dayTrading < 0 ? "text-red-600" : "text-gray-600"
                )}>
                  ${realizedPL.dayTrading.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Swing Trading P/L</p>
                <p className={cn(
                  "text-lg font-semibold",
                  realizedPL.swingTrading > 0 ? "text-green-600" : 
                  realizedPL.swingTrading < 0 ? "text-red-600" : "text-gray-600"
                )}>
                  ${realizedPL.swingTrading.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Long Term P/L</p>
                <p className={cn(
                  "text-lg font-semibold",
                  realizedPL.longTermInvesting > 0 ? "text-green-600" : 
                  realizedPL.longTermInvesting < 0 ? "text-red-600" : "text-gray-600"
                )}>
                  ${realizedPL.longTermInvesting.toLocaleString()}
                </p>
              </div>
              <div className="pt-3 border-t border-blue-200">
                <p className="text-sm font-medium text-gray-600">Total P/L</p>
                <p className={cn(
                  "text-xl font-bold",
                  realizedPL.all > 0 ? "text-green-600" : 
                  realizedPL.all < 0 ? "text-red-600" : "text-gray-600"
                )}>
                  ${realizedPL.all.toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Realized Value Details</h2>
            <div className="w-[200px]">
              <Select
                value={selectedTimeframe}
                onValueChange={(value: TimeframeSelection) => setSelectedTimeframe(value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select timeframe" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Trades</SelectItem>
                  <SelectItem value="dayTrading">Day Trading (1-5 Days)</SelectItem>
                  <SelectItem value="swingTrading">Swing Trading (6-90 Days)</SelectItem>
                  <SelectItem value="longTermInvesting">Long Term Investing ({'>'}90 Days)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <RealizedValueTable
            configName={selectedTimeframe === 'all' ? '' : TIMEFRAME_TO_CONFIG[selectedTimeframe]}
            filterOptions={{
              status: 'ALL',
              startDate: undefined,
              optionType: undefined,
              symbol: undefined,
              minEntryPrice: undefined,
              maxEntryPrice: undefined
            }}
            positionSizingConfig={getTableConfig(selectedTimeframe)}
            allConfigs={config}
            onRealizedPLUpdate={handleRealizedPLUpdate}
          />
        </div>
      </div>
    </main>
  );
} 