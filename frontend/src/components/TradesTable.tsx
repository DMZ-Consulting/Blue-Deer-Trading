'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Trade, Transaction } from '../utils/types'
import { ChevronDown, ChevronUp, ArrowUpDown } from 'lucide-react'
import { getTradesByConfiguration } from '../api/api'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

import 'react-datepicker/dist/react-datepicker.css'

interface TradesTableProps {
  configName: string
}

type SortField = 'symbol' | 'trade_type' | 'status' | 'entry_price' | 'current_size' | 'created_at' | 'closed_at' | 'realized_pl'
type SortOrder = 'asc' | 'desc'

export function TradesTableComponent({ configName }: TradesTableProps) {
  const [trades, setTrades] = useState<Trade[]>([])
  const [expandedTrades, setExpandedTrades] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [debugMode, setDebugMode] = useState(false)
  const [dateFilter, setDateFilter] = useState(() => {
    const now = new Date();
    return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())).toISOString().split('T')[0];
  });
  const [statusFilter, setStatusFilter] = useState('closed')
  const [weekFilter, setWeekFilter] = useState(new Date().toISOString().split('T')[0])
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  const fetchTrades = useCallback(async () => {
    setLoading(true)
    try {
      const fetchedTrades = await getTradesByConfiguration(configName, {
        status: statusFilter,
        weekFilter: weekFilter,
      })
      setTrades(fetchedTrades)
    } catch (error) {
      console.error('Error fetching trades:', error)
    } finally {
      setLoading(false)
    }
  }, [configName, statusFilter, weekFilter]) // Removed monthFilter and yearFilter as they are not defined

  useEffect(() => {
    fetchTrades()
  }, [fetchTrades])

  const getHeaderText = () => {
    const date = new Date(dateFilter + 'T00:00:00Z');
    const friday = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() + (5 - date.getUTCDay() + 7) % 7));
    if (statusFilter === 'open') {
      return `Trades Remaining Open`
    } else {
      return `Trades Realized for the week of ${friday.toLocaleDateString(undefined, { timeZone: 'UTC' })}`
    }
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

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }
  const sortedTrades = [...trades].sort((a, b) => {
    const aValue = a[sortField] ?? '';
    const bValue = b[sortField] ?? '';
    
    if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  const renderSortIcon = (field: SortField) => {
    if (sortField === field) {
      return sortOrder === 'asc' ? <ChevronUp className="w-4 h-4 ml-1" /> : <ChevronDown className="w-4 h-4 ml-1" />
    }
    return <ArrowUpDown className="w-4 h-4 ml-1" />
  }

  return (
    <div className="space-y-4">
      {isDevelopment && (
        <Card>
          <CardHeader>
            <CardTitle>Debug Options</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center space-x-4">
            <label className="flex items-center space-x-2">
              <Input
                type="checkbox"
                checked={debugMode}
                onChange={(e) => setDebugMode(e.target.checked)}
              />
              <span>Debug Mode</span>
            </label>
            <Input
              type="date"
              value={dateFilter}
              onChange={handleDateChange}
            />
            <Select value={statusFilter} onValueChange={setStatusFilter}> {/* Updated Select component */}
              <SelectTrigger>
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem> {/* Updated SelectItem value */}
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      )}
      
      <h2 className="text-2xl font-bold">{getHeaderText()}</h2>

      {loading ? (
        <p>Loading trades...</p>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[50px]"></TableHead>
                {isDevelopment && debugMode && <TableHead>Trade ID</TableHead>}
                <TableHead>
                  <Button variant="ghost" onClick={() => handleSort('symbol')}>
                    Symbol {renderSortIcon('symbol')}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button variant="ghost" onClick={() => handleSort('trade_type')}>
                    Type {renderSortIcon('trade_type')}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button variant="ghost" onClick={() => handleSort('status')}>
                    Status {renderSortIcon('status')}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button variant="ghost" onClick={() => handleSort('entry_price')}>
                    Entry Price {renderSortIcon('entry_price')}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button variant="ghost" onClick={() => handleSort('current_size')}>
                    Size {renderSortIcon('current_size')}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button variant="ghost" onClick={() => handleSort('created_at')}>
                    Opened At {renderSortIcon('created_at')}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button variant="ghost" onClick={() => handleSort('closed_at')}>
                    Closed At {renderSortIcon('closed_at')}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button variant="ghost" onClick={() => handleSort('realized_pl')}>
                    Realized P/L {renderSortIcon('realized_pl')}
                  </Button>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedTrades.map(trade => (
                <React.Fragment key={trade.trade_id}>
                  <TableRow>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleTradeExpansion(trade.trade_id)}
                      >
                        {expandedTrades.has(trade.trade_id) ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </Button>
                    </TableCell>
                    {isDevelopment && debugMode && <TableCell>{trade.trade_id}</TableCell>}
                    <TableCell>{trade.symbol}</TableCell>
                    <TableCell>{trade.trade_type}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded-full text-xs ${trade.status === 'open' ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'}`}>
                        {trade.status}
                      </span>
                    </TableCell>
                    <TableCell>${trade.entry_price.toFixed(2)}</TableCell>
                    <TableCell>{trade.current_size}</TableCell>
                    <TableCell>{formatDateTime(trade.created_at)}</TableCell>
                    <TableCell>{trade.closed_at ? formatDateTime(trade.closed_at) : '-'}</TableCell>
                    <TableCell>${trade.realized_pl !== undefined ? trade.realized_pl.toFixed(2) : 'N/A'}</TableCell>
                  </TableRow>
                  {expandedTrades.has(trade.trade_id) && (
                    <TableRow>
                      <TableCell colSpan={isDevelopment && debugMode ? 10 : 9}>
                        <Card>
                          <CardHeader>
                            <CardTitle>Transactions</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  {isDevelopment && debugMode && <TableHead>Transaction ID</TableHead>}
                                  <TableHead>Type</TableHead>
                                  <TableHead>Price</TableHead>
                                  <TableHead>Size</TableHead>
                                  <TableHead>Date</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {trade.transactions?.map(transaction => (
                                  <TableRow key={transaction.id}>
                                    {isDevelopment && debugMode && <TableCell>{transaction.id}</TableCell>}
                                    <TableCell>
                                      <span className={`px-2 py-1 rounded-full text-xs ${getTransactionTypeColor(transaction.transaction_type)}`}>
                                        {transaction.transaction_type}
                                      </span>
                                    </TableCell>
                                    <TableCell>${transaction.amount.toFixed(2)}</TableCell>
                                    <TableCell>{transaction.size}</TableCell>
                                    <TableCell>{new Date(transaction.created_at).toLocaleString()}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </CardContent>
                        </Card>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}