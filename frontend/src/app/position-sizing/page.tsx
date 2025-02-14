'use client';

import { useState, useEffect } from 'react';
import { PositionSizingInputs } from '@/components/PositionSizingInputs';
import { PositionSizingTable } from '@/components/PositionSizingTable';
import { PositionSizingConfig } from '@/types/position-sizing';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

// Update the type to include 'all' as a possible value
type TimeframeSelection = keyof PositionSizingConfig | 'all';

const TIMEFRAME_TO_CONFIG: Record<keyof PositionSizingConfig, string> = {
  dayTrading: 'day_trader',
  swingTrading: 'swing_trader',
  longTermInvesting: 'long_term_trader'
};

export default function PositionSizingPage() {
  const [config, setConfig] = useState<PositionSizingConfig>({
    dayTrading: {
      portfolioSize: 25000,
      riskTolerancePercent: 1
    },
    swingTrading: {
      portfolioSize: 50000,
      riskTolerancePercent: 2
    },
    longTermInvesting: {
      portfolioSize: 100000,
      riskTolerancePercent: 5
    }
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

  const handleConfigChange = (newConfig: PositionSizingConfig) => {
    try {
      setError(null);
      setConfig(newConfig);
    } catch (err) {
      setError('An error occurred while updating the configuration');
      console.error(err);
    }
  };

  const calculateTotalPortfolioSize = () => {
    return Object.values(config).reduce((total, timeframe) => total + timeframe.portfolioSize, 0);
  };

  const calculateMaxPositionSize = (timeframe: keyof PositionSizingConfig) => {
    const { portfolioSize, riskTolerancePercent } = config[timeframe];
    return portfolioSize * (riskTolerancePercent / 100);
  };

  // Helper function to get the configuration for the table
  const getTableConfig = (timeframe: TimeframeSelection) => {
    if (timeframe === 'all') {
      // For 'all', use the total portfolio size and average risk tolerance
      const totalSize = calculateTotalPortfolioSize();
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

  const totalPortfolioSize = calculateTotalPortfolioSize();

  return (
    <main className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Position Sizing Calculator</h1>
      
      <PositionSizingInputs 
        config={config}
        onChange={handleConfigChange}
      />
      
      <div className="mt-6">
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-3">Position Sizing Summary</h2>
          
          {/* Total Portfolio Summary */}
          <div className="bg-blue-50 p-4 rounded-lg mb-4">
            <h3 className="text-lg font-semibold text-blue-800 mb-2">Total Portfolio</h3>
            <p className="text-2xl font-bold text-blue-900">${totalPortfolioSize.toLocaleString()}</p>
          </div>

          {/* Individual Timeframe Summaries */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Day Trading Summary */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="text-lg font-semibold mb-2">Day Trading</h3>
              <div className="space-y-2">
                <div>
                  <p className="text-sm text-gray-600">Portfolio Size</p>
                  <p className="text-xl font-bold">${config.dayTrading.portfolioSize.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Risk Tolerance</p>
                  <p className="text-lg font-semibold">{config.dayTrading.riskTolerancePercent}%</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Max Position Size</p>
                  <p className="text-lg font-semibold text-blue-700">
                    ${calculateMaxPositionSize('dayTrading').toLocaleString()}
                  </p>
                </div>
              </div>
            </div>

            {/* Swing Trading Summary */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="text-lg font-semibold mb-2">Swing Trading</h3>
              <div className="space-y-2">
                <div>
                  <p className="text-sm text-gray-600">Portfolio Size</p>
                  <p className="text-xl font-bold">${config.swingTrading.portfolioSize.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Risk Tolerance</p>
                  <p className="text-lg font-semibold">{config.swingTrading.riskTolerancePercent}%</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Max Position Size</p>
                  <p className="text-lg font-semibold text-blue-700">
                    ${calculateMaxPositionSize('swingTrading').toLocaleString()}
                  </p>
                </div>
              </div>
            </div>

            {/* Long Term Investing Summary */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="text-lg font-semibold mb-2">Long Term Investing</h3>
              <div className="space-y-2">
                <div>
                  <p className="text-sm text-gray-600">Portfolio Size</p>
                  <p className="text-xl font-bold">${config.longTermInvesting.portfolioSize.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Risk Tolerance</p>
                  <p className="text-lg font-semibold">{config.longTermInvesting.riskTolerancePercent}%</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Max Position Size</p>
                  <p className="text-lg font-semibold text-blue-700">
                    ${calculateMaxPositionSize('longTermInvesting').toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Position Sizing Details</h2>
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

          <PositionSizingTable
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
          />
        </div>
      </div>
    </main>
  );
} 