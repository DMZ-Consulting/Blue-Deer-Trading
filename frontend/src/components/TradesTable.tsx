'use client'

import { useState, useEffect } from 'react'
import { Trade, Transaction } from '../utils/types'
import { ChevronDown, ChevronUp } from 'lucide-react'
import React from 'react'
import { getTradesByConfiguration } from '../api/api'

interface TradesTableProps {
  dateFilter: string
  statusFilter: string
  configName: string
}

export function TradesTableComponent({ dateFilter, statusFilter, configName }: TradesTableProps) {
  const [trades, setTrades] = useState<Trade[]>([])
  const [expandedTrades, setExpandedTrades] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchTrades = async () => {
      setLoading(true)
      try {
        const fetchedTrades = await getTradesByConfiguration(configName, statusFilter)
        setTrades(fetchedTrades)
      } catch (error) {
        console.error('Error fetching trades:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchTrades()
  }, [configName, statusFilter])

  const filteredTrades = trades.filter(trade => {
    const dateMatch = !dateFilter || new Date(trade.created_at) >= new Date(dateFilter)
    return dateMatch
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
                        {/* Transactions for this trade */}
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
