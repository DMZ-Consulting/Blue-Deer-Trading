'use client';

import { useState, useEffect } from 'react';
import { PositionSizingInputs } from '@/components/PositionSizingInputs';
import { PositionSizingTable } from '@/components/PositionSizingTable';
import { PositionSizingConfig } from '@/types/position-sizing';

export default function PositionSizingPage() {
  const [config, setConfig] = useState<PositionSizingConfig>({
    portfolioSize: 100000,
    riskTolerancePercent: 1
  });
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
      <h1 className="text-2xl font-bold mb-6">Position Sizing Calculator</h1>
      
      <PositionSizingInputs 
        config={config}
        onChange={handleConfigChange}
      />
      
      <div className="mt-6">
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-3">Position Sizing Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">Portfolio Size</p>
              <p className="text-2xl font-bold">${config.portfolioSize.toLocaleString()}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">Risk Tolerance</p>
              <p className="text-2xl font-bold">{config.riskTolerancePercent}%</p>
            </div>
            <div className="p-4 bg-blue-50 rounded-lg md:col-span-2">
              <p className="text-sm text-blue-600">Maximum Position Size</p>
              <p className="text-2xl font-bold text-blue-700">
                ${(config.portfolioSize * (config.riskTolerancePercent / 100)).toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <PositionSizingTable
          configName=""
          filterOptions={{
            status: 'ALL',
            startDate: undefined,
            optionType: undefined,
            symbol: undefined,
            minEntryPrice: undefined,
            maxEntryPrice: undefined
          }}
          positionSizingConfig={config}
        />
      </div>
    </main>
  );
} 