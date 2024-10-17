'use client'

import { PortfolioTrade } from '../utils/types'

interface ReportAreaProps {
  portfolio: PortfolioTrade[]
}

export function ReportAreaComponent({ portfolio }: ReportAreaProps) {
  const totalPL = portfolio.reduce((sum, trade) => sum + trade.realized_pl, 0)
  const closedTrades = portfolio.length
  const winningTrades = portfolio.filter(trade => trade.realized_pl > 0).length
  const winRate = closedTrades > 0 ? (winningTrades / closedTrades) * 100 : 0

  return (
    <div className="bg-white border border-gray-300 p-4 rounded shadow-sm">
      <h2 className="text-xl font-bold mb-4">Reports</h2>
      <div className="space-y-4">
        <div className="p-4 bg-gray-100 rounded">
          <h3 className="font-semibold mb-2">Total Profit/Loss</h3>
          <p className={`text-2xl font-bold ${totalPL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            ${totalPL.toFixed(2)}
          </p>
        </div>
        <div className="p-4 bg-gray-100 rounded">
          <h3 className="font-semibold mb-2">Closed Trades</h3>
          <p className="text-2xl font-bold">{closedTrades}</p>
        </div>
        <div className="p-4 bg-gray-100 rounded">
          <h3 className="font-semibold mb-2">Win Rate</h3>
          <p className="text-2xl font-bold">{winRate.toFixed(2)}%</p>
        </div>
        <div className="mt-4">
          <p className="text-sm text-gray-600">
            This area will contain more detailed graphs and reports based on the trading data.
          </p>
        </div>
      </div>
    </div>
  )
}
