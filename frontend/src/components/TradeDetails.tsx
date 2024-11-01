'use client'

import { useState } from 'react'
import { Trade, Transaction } from '../utils/types'

interface TradeDetailsProps {
  trade: Trade
  transactions: Transaction[]
}

export function TradeDetailsComponent({ trade, transactions }: TradeDetailsProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="mt-4 bg-white border border-gray-300 p-4 rounded shadow-sm">
      <div className="flex justify-between items-center mb-2">
        <h2 className="text-xl font-bold">Trade Details: {trade.symbol}</h2>
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
        >
          {isExpanded ? 'Hide Details' : 'Show Details'}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p><span className="font-semibold">Status:</span> 
            <span className={`ml-2 px-2 py-1 rounded-full text-xs ${trade.status === 'open' ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'}`}>
              {trade.status}
            </span>
          </p>
          <p><span className="font-semibold">Avg Entry Price:</span> ${trade.entry_price.toFixed(2)}</p>
          <p><span className="font-semibold">Current Size:</span> {trade.current_size}</p>
        </div>
        <div>
          <p><span className="font-semibold">Created At:</span> {new Date(trade.created_at).toLocaleString()}</p>
          {trade.closed_at && <p><span className="font-semibold">Closed At:</span> {new Date(trade.closed_at).toLocaleString()}</p>}
          {trade.exit_price && <p><span className="font-semibold">Exit Price:</span> ${trade.exit_price.toFixed(2)}</p>}
          {trade.profit_loss && (
            <p>
              <span className="font-semibold">Profit/Loss:</span> 
              <span className={trade.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}>
                ${trade.profit_loss.toFixed(2)}
              </span>
            </p>
          )}
        </div>
      </div>
      
      {isExpanded && (
        <>
          <h3 className="text-lg font-bold mt-4 mb-2">Transactions</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white border border-gray-300">
              <thead>
                <tr className="bg-gray-100">
                  <th className="py-2 px-4 border-b">Type</th>
                  <th className="py-2 px-4 border-b">Amount</th>
                  <th className="py-2 px-4 border-b">Size</th>
                  <th className="py-2 px-4 border-b">Date</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map(transaction => (
                  <tr key={transaction.id}>
                    <td className="py-2 px-4 border-b">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        transaction.transaction_type === 'open' ? 'bg-blue-200 text-blue-800' :
                        transaction.transaction_type === 'close' ? 'bg-red-200 text-red-800' :
                        transaction.transaction_type === 'add' ? 'bg-green-200 text-green-800' :
                        'bg-yellow-200 text-yellow-800'
                      }`}>
                        {transaction.transaction_type}
                      </span>
                    </td>
                    <td className="py-2 px-4 border-b">${transaction.amount.toFixed(2)}</td>
                    <td className="py-2 px-4 border-b">{transaction.size}</td>
                    <td className="py-2 px-4 border-b">{new Date(transaction.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
