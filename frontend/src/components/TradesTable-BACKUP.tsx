'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Trade, Transaction } from '../utils/types'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { getTradesByConfiguration } from '../api/api'

import 'react-datepicker/dist/react-datepicker.css'

interface TradesTableProps {
  configName: string
}

export function TradesTableComponent({ configName }: TradesTableProps) {
  const [trades, setTrades] = useState<Trade[]>([])
  const [expandedTrades, setExpandedTrades] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [debugMode, setDebugMode] = useState(false)
  const [dateFilter, setDateFilter] = useState(() => {
    const now = new Date();
    return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())).toISOString().split('T')[0];
  });
  //const [timeFrame, setTimeFrame] = useState('daily')
  const [statusFilter, setStatusFilter] = useState('closed')
  const [weekFilter, setWeekFilter] = useState(new Date().toISOString().split('T')[0])
  const [monthFilter, setMonthFilter] = useState('')
  const [yearFilter, setYearFilter] = useState('')

  const fetchTrades = useCallback(async () => {
    setLoading(true)
    try {
      const fetchedTrades = await getTradesByConfiguration(configName, {
        status: statusFilter,
        //timeFrame: timeFrame,
        weekFilter: weekFilter,
        monthFilter: monthFilter,
        yearFilter: yearFilter
      })
      setTrades(fetchedTrades)
    } catch (error) {
      console.error('Error fetching trades:', error)
    } finally {
      setLoading(false)
    }
  }, [configName, statusFilter, weekFilter, monthFilter, yearFilter])

  useEffect(() => {
    fetchTrades()
  }, [fetchTrades])

  const getHeaderText = () => {
    const date = new Date(dateFilter + 'T00:00:00Z'); // Ensure UTC interpretation
    const friday = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() + (5 - date.getUTCDay() + 7) % 7));
    if (statusFilter === 'open') {
      return `Trades Remaining Open`
    } else {
      return `Trades Realized for the week of ${friday.toLocaleDateString(undefined, { timeZone: 'UTC' })}`
    }
    /*switch (timeFrame) {
      case 'daily':
        return `Trades on ${date.toLocaleDateString(undefined, { timeZone: 'UTC' })}`
      case 'weekly':
        const friday = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() + (5 - date.getUTCDay() + 7) % 7));
        return `Trades for the week of ${friday.toLocaleDateString(undefined, { timeZone: 'UTC' })}`
      case 'monthly':
        return `Trades for ${date.toLocaleString('default', { month: 'long', year: 'numeric', timeZone: 'UTC' })}`
      default:
        return 'Trades'
    }*/
  }

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

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newDate = e.target.value
    setDateFilter(newDate)
    setWeekFilter(newDate)
  }

  const formatDateTime = (dateString: string | null): string => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString + 'Z');
    return date.toLocaleString('en-US', {
      year: '2-digit',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
      timeZone: 'UTC'
    });
  }

  const isDevelopment = process.env.NODE_ENV === 'development'

  const getTransactionTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'open':
        return 'bg-green-200 text-green-800';
      case 'add':
        return 'bg-blue-200 text-blue-800';
      case 'trim':
        return 'bg-yellow-200 text-yellow-800';
      case 'close':
        return 'bg-red-200 text-red-800';
      default:
        return 'bg-gray-200 text-gray-800';
    }
  };

  return (
    <div>
      {isDevelopment && (
        <div className="mb-4 flex items-center space-x-4">
          <label className="inline-flex items-center">
            <input
              type="checkbox"
              className="form-checkbox h-5 w-5 text-blue-600"
              checked={debugMode}
              onChange={(e) => setDebugMode(e.target.checked)}
            />
            <span className="ml-2 text-gray-700">Debug Mode</span>
          </label>
          <input
            type="date"
            value={dateFilter}
            onChange={handleDateChange}
            className="border p-2 rounded"
          />
          {/* 
          <select
            value={timeFrame}
            onChange={(e) => setTimeFrame(e.target.value)}
            className="form-select mt-1 block"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
          */} 
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="form-select mt-1 block"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      )}
      
      <h2 className="text-xl font-bold mb-4">{getHeaderText()}</h2>

      {loading ? (
        <p>Loading trades...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-300">
            <thead>
              <tr className="bg-gray-100">
                <th className="py-2 px-4 border-b text-center"></th>
                {isDevelopment && debugMode && <th className="py-2 px-4 border-b text-center">Trade ID</th>}
                <th className="py-2 px-4 border-b text-center">Symbol</th>
                <th className="py-2 px-4 border-b text-center">Type</th>
                <th className="py-2 px-4 border-b text-center">Status</th>
                <th className="py-2 px-4 border-b text-center">Entry Price</th>
                <th className="py-2 px-4 border-b text-center">Size</th>
                <th className="py-2 px-4 border-b text-center">Opened At</th>
                <th className="py-2 px-4 border-b text-center">Closed At</th>
                <th className="py-2 px-4 border-b text-center">Realized P/L</th>
              </tr>
            </thead>
            <tbody>
              {trades.map(trade => (
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
                    {isDevelopment && debugMode && <td className="py-2 px-4 border-b text-center">{trade.trade_id}</td>}
                    <td className="py-2 px-4 border-b text-center">{trade.symbol}</td>
                    <td className="py-2 px-4 border-b text-center">{trade.trade_type}</td>
                    <td className="py-2 px-4 border-b text-center">
                      <span className={`px-2 py-1 rounded-full text-xs ${trade.status === 'open' ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'}`}>
                        {trade.status}
                      </span>
                    </td>
                    <td className="py-2 px-4 border-b text-center">${trade.entry_price.toFixed(2)}</td>
                    <td className="py-2 px-4 border-b text-center">{trade.current_size}</td>
                    <td className="py-2 px-4 border-b text-center">
                      {formatDateTime(trade.created_at)}
                    </td>
                    <td className="py-2 px-4 border-b text-center">
                      {trade.closed_at ? formatDateTime(trade.closed_at) : '-'}
                    </td>
                    <td className="py-2 px-4 border-b text-center">${trade.realized_pl !== undefined ? trade.realized_pl.toFixed(2) : 'N/A'}</td>
                  </tr>
                  {expandedTrades.has(trade.trade_id) && (
                    <tr>
                      <td colSpan={isDevelopment && debugMode ? 9 : 8} className="py-4 px-4 border-b bg-gray-50">
                        <h4 className="text-lg font-semibold mb-2 text-center">Transactions</h4>
                        <table className="min-w-full bg-white border border-gray-300">
                          <thead>
                            <tr className="bg-gray-100">
                              {isDevelopment && debugMode && <th className="py-2 px-4 border-b text-center">Transaction ID</th>}
                              <th className="py-2 px-4 border-b text-center">Type</th>
                              <th className="py-2 px-4 border-b text-center">Price</th>
                              <th className="py-2 px-4 border-b text-center">Size</th>
                              <th className="py-2 px-4 border-b text-center">Date</th>
                            </tr>
                          </thead>
                          <tbody>
                            {trade.transactions?.map(transaction => (
                              <tr key={transaction.id}>
                                {isDevelopment && debugMode && <td className="py-2 px-4 border-b text-center">{transaction.id}</td>}
                                <td className="py-2 px-4 border-b text-center">
                                  <span className={`px-2 py-1 rounded-full text-xs ${getTransactionTypeColor(transaction.transaction_type)}`}>
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
      )}
    </div>
  )
}
