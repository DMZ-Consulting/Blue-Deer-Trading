'use client'

import { useState } from 'react'
import { Trade, Transaction } from '../utils/types'
import { ChevronDown, ChevronUp } from 'lucide-react'
import React from 'react'

interface TradesTableProps {
  dateFilter: string
  statusFilter: string
}

const dummyTrades: Trade[] = [
  {
    trade_id: "T001",
    symbol: "AAPL",
    trade_type: "Long",
    status: "open",
    entry_price: 150.25,
    current_size: "100",
    created_at: "2023-06-01T10:00:00Z",
  },
  {
    trade_id: "T002",
    symbol: "GOOGL",
    trade_type: "Short",
    status: "closed",
    entry_price: 2750.50,
    current_size: "50",
    created_at: "2023-05-28T14:30:00Z",
    closed_at: "2023-06-02T11:15:00Z",
    exit_price: 2780.75,
    profit_loss: 1512.50,
  },
  {
    trade_id: "T003",
    symbol: "TSLA",
    trade_type: "Long",
    status: "open",
    entry_price: 620.75,
    current_size: "75",
    created_at: "2023-06-03T09:45:00Z",
  },
  {
    trade_id: "T004",
    symbol: "AMZN",
    trade_type: "Long",
    status: "closed",
    entry_price: 3300.00,
    current_size: "25",
    created_at: "2023-05-25T13:20:00Z",
    closed_at: "2023-06-01T15:45:00Z",
    exit_price: 3350.25,
    profit_loss: 1256.25,
  },
  {
    trade_id: "T005",
    symbol: "MSFT",
    trade_type: "Short",
    status: "open",
    entry_price: 280.50,
    current_size: "100",
    created_at: "2023-06-04T11:30:00Z",
  },
]

const dummyTransactions: { [key: string]: Transaction[] } = {
  "T001": [
    { id: "TR001", trade_id: "T001", transaction_type: "open", amount: 15025.00, size: "100", created_at: "2023-06-01T10:00:00Z" },
    { id: "TR002", trade_id: "T001", transaction_type: "add", amount: 7650.00, size: "50", created_at: "2023-06-02T11:30:00Z" },
    { id: "TR003", trade_id: "T001", transaction_type: "trim", amount: 4635.00, size: "30", created_at: "2023-06-03T14:15:00Z" },
  ],
  "T002": [
    { id: "TR004", trade_id: "T002", transaction_type: "open", amount: 137525.00, size: "50", created_at: "2023-05-28T14:30:00Z" },
    { id: "TR005", trade_id: "T002", transaction_type: "close", amount: 139037.50, size: "50", created_at: "2023-06-02T11:15:00Z" },
  ],
  "T003": [
    { id: "TR006", trade_id: "T003", transaction_type: "open", amount: 46556.25, size: "75", created_at: "2023-06-03T09:45:00Z" },
  ],
  "T004": [
    { id: "TR007", trade_id: "T004", transaction_type: "open", amount: 82500.00, size: "25", created_at: "2023-05-25T13:20:00Z" },
    { id: "TR008", trade_id: "T004", transaction_type: "close", amount: 83756.25, size: "25", created_at: "2023-06-01T15:45:00Z" },
  ],
  "T005": [
    { id: "TR009", trade_id: "T005", transaction_type: "open", amount: 28050.00, size: "100", created_at: "2023-06-04T11:30:00Z" },
  ],
}

export function TradesTableComponent({ dateFilter, statusFilter }: TradesTableProps) {
  const [trades, setTrades] = useState<Trade[]>(dummyTrades)
  const [expandedTrades, setExpandedTrades] = useState<Set<string>>(new Set())

  const filteredTrades = trades.filter(trade => {
    const dateMatch = !dateFilter || new Date(trade.created_at) >= new Date(dateFilter)
    const statusMatch = !statusFilter || trade.status === statusFilter
    return dateMatch && statusMatch
  })

  const toggleTradeExpansion = (tradeId: string) => {
    setExpandedTrades(prevExpanded => {
      const newExpanded = new Set(prevExpanded)
      if (newExpanded.has(tradeId)) {
        newExpanded.delete(tradeId)
      } else {
        newExpanded.add(tradeId)
      }
      return newExpanded
    })
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white border border-gray-300">
        <thead>
          <tr className="bg-gray-100">
            <th className="py-2 px-4 border-b text-center"></th>
            <th className="py-2 px-4 border-b text-center">Trade ID</th>
            <th className="py-2 px-4 border-b text-center">Symbol</th>
            <th className="py-2 px-4 border-b text-center">Type</th>
            <th className="py-2 px-4 border-b text-center">Status</th>
            <th className="py-2 px-4 border-b text-center">Entry Price</th>
            <th className="py-2 px-4 border-b text-center">Current Size</th>
            <th className="py-2 px-4 border-b text-center">Created At</th>
          </tr>
        </thead>
        <tbody>
          {filteredTrades.map(trade => (
            <React.Fragment key={trade.trade_id}>
              <tr className="hover:bg-gray-50">
                <td className="py-2 px-4 border-b text-center">
                  <button onClick={() => toggleTradeExpansion(trade.trade_id)} className="focus:outline-none">
                    {expandedTrades.has(trade.trade_id) ? (
                      <ChevronUp className="w-5 h-5 text-gray-500 mx-auto" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-500 mx-auto" />
                    )}
                  </button>
                </td>
                <td className="py-2 px-4 border-b text-center">{trade.trade_id}</td>
                <td className="py-2 px-4 border-b text-center">{trade.symbol}</td>
                <td className="py-2 px-4 border-b text-center">{trade.trade_type}</td>
                <td className="py-2 px-4 border-b text-center">
                  <span className={`px-2 py-1 rounded-full text-xs ${trade.status === 'open' ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'}`}>
                    {trade.status}
                  </span>
                </td>
                <td className="py-2 px-4 border-b text-center">${trade.entry_price.toFixed(2)}</td>
                <td className="py-2 px-4 border-b text-center">{trade.current_size}</td>
                <td className="py-2 px-4 border-b text-center">{new Date(trade.created_at).toLocaleString()}</td>
              </tr>
              {expandedTrades.has(trade.trade_id) && (
                <tr>
                  <td colSpan={8} className="py-4 px-4 border-b bg-gray-50">
                    <h4 className="text-lg font-semibold mb-2 text-center">Transactions</h4>
                    <table className="min-w-full bg-white border border-gray-300">
                      <thead>
                        <tr className="bg-gray-100">
                          <th className="py-2 px-4 border-b text-center">Transaction ID</th>
                          <th className="py-2 px-4 border-b text-center">Type</th>
                          <th className="py-2 px-4 border-b text-center">Amount</th>
                          <th className="py-2 px-4 border-b text-center">Size</th>
                          <th className="py-2 px-4 border-b text-center">Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dummyTransactions[trade.trade_id].map(transaction => (
                          <tr key={transaction.id}>
                            <td className="py-2 px-4 border-b text-center">{transaction.id}</td>
                            <td className="py-2 px-4 border-b text-center">
                              <span className={`px-2 py-1 rounded-full text-xs ${
                                transaction.transaction_type === 'open' ? 'bg-blue-200 text-blue-800' :
                                transaction.transaction_type === 'close' ? 'bg-red-200 text-red-800' :
                                transaction.transaction_type === 'add' ? 'bg-green-200 text-green-800' :
                                'bg-yellow-200 text-yellow-800'
                              }`}>
                                {transaction.transaction_type}
                              </span>
                            </td>
                            <td className="py-2 px-4 border-b text-center">${transaction.amount.toFixed(2)}</td>
                            <td className="py-2 px-4 border-b text-center">{transaction.size}</td>
                            <td className="py-2 px-4 border-b text-center">{new Date(transaction.created_at).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}