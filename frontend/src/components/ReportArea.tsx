'use client'

import { useState, useEffect, Suspense } from 'react'
import { PortfolioEndpoint } from '../utils/types'
import { getMonthlyPL, MonthlyPL } from '@/api/api'

interface ReportAreaProps {
  portfolio: PortfolioEndpoint;
  configName: string;
}

// Separate the data fetching and display logic
function MonthlyBreakdown({ configName, totalPL }: { configName: string; totalPL: number }) {
  const [monthlyPLData, setMonthlyPLData] = useState<MonthlyPL[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMonthlyPL = async () => {
      try {
        setLoading(true);
        const data = await getMonthlyPL(configName);
        setMonthlyPLData(data);
      } catch (error) {
        console.error('Error fetching monthly P/L:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchMonthlyPL();
  }, [configName]);

  if (loading) {
    return <p>Loading monthly data...</p>;
  }

  return (
    <div className="space-y-2">
      {monthlyPLData.map((item) => (
        <div key={item.month} className="flex justify-between items-center">
          <span className="text-sm">{item.month}</span>
          <span className={`font-semibold ${item.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            ${item.profit_loss.toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function ReportAreaComponent({ portfolio, configName }: ReportAreaProps) {
  const allTrades = [
    ...(portfolio.regular_trades || []),
    ...(portfolio.strategy_trades || [])
  ];

  const weeklyPL = allTrades.reduce((sum, trade) => sum + trade.realized_pl, 0);
  const totalPL = allTrades.reduce((sum, trade) => sum + trade.realized_pl, 0);

  return (
    <div className="bg-white border border-gray-300 p-4 rounded shadow-sm">
      <h2 className="text-xl font-bold mb-4">Reports</h2>
      <div className="space-y-4">
        <div className="p-4 bg-gray-100 rounded">
          <h3 className="font-semibold mb-2">Weekly Profit/Loss</h3>
          <p className={`text-2xl font-bold ${weeklyPL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            ${weeklyPL.toFixed(2)}
          </p>
        </div>
        
        <div className="p-4 bg-gray-100 rounded">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold">Monthly Breakdown</h3>
            <div className="text-right">
              <div className="text-sm text-gray-600">Total P/L</div>
              <div className={`font-bold ${totalPL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                ${totalPL.toFixed(2)}
              </div>
            </div>
          </div>
          <Suspense fallback={<p>Loading monthly data...</p>}>
            <MonthlyBreakdown configName={configName} totalPL={totalPL} />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
