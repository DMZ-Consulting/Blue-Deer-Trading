'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Trade } from '../utils/types'
import { ChevronDown, ChevronUp, ArrowUpDown } from 'lucide-react'
import { getTradesByConfiguration } from '../api/api'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

import 'react-datepicker/dist/react-datepicker.css'

interface FilterOptions {
  status: string;
  startDate: string;
  optionType?: string;
  symbol?: string;
  tradeGroup?: string;
  minEntryPrice?: number;
  maxEntryPrice?: number;
}

interface TradesTableProps {
  configName: string;
  filterOptions: FilterOptions;
  showAllTrades?: boolean;
}

// Add these type definitions at the top of the file
type SortField = keyof Trade
type SortOrder = 'asc' | 'desc'

export function TradesTableComponent({ configName, filterOptions, showAllTrades = false }: TradesTableProps) {
  const [trades, setTrades] = useState<Trade[]>([])
  const [expandedTrades, setExpandedTrades] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [debugMode, setDebugMode] = useState(false)
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  const fetchTrades = useCallback(async () => {
    setLoading(true)
    try {
      console.log("Fetching trades with options:", {
        status: filterOptions.status,
        weekFilter: filterOptions.startDate,
        optionType: filterOptions.optionType,
        symbol: filterOptions.symbol,
        tradeGroup: filterOptions.tradeGroup,
        minEntryPrice: filterOptions.minEntryPrice,
        maxEntryPrice: filterOptions.maxEntryPrice,
        showAllTrades
      });

      const fetchedTrades = await getTradesByConfiguration(configName, {
        status: filterOptions.status,
        weekFilter: filterOptions.startDate,
        optionType: filterOptions.optionType,
        symbol: filterOptions.symbol,
        tradeGroup: filterOptions.tradeGroup,
        minEntryPrice: filterOptions.minEntryPrice,
        maxEntryPrice: filterOptions.maxEntryPrice,
        showAllTrades
      })
      setTrades(fetchedTrades)
    } catch (error) {
      console.error('Error fetching trades:', error)
    } finally {
      setLoading(false)
    }
  }, [configName, filterOptions, showAllTrades])

  useEffect(() => {
    fetchTrades()
  }, [fetchTrades])

  const getHeaderText = () => {
    const date = new Date(filterOptions.startDate + 'T00:00:00Z');
    const friday = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() + (5 - date.getUTCDay() + 7) % 7));
    if (filterOptions.status === 'open') {
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

  const formatDateTime = (dateString: string | null): string => {
    if (!dateString) return 'N/A';
    
    // Parse the UTC date string
    const utcDate = new Date(dateString + 'Z');
    
    // Create options for EST time formatting
    const options: Intl.DateTimeFormatOptions = {
      year: '2-digit',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
      timeZone: 'America/New_York'
    };

    return utcDate.toLocaleString('en-US', options);
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
    let aValue = a[sortField];
    let bValue = b[sortField];
    
    // Convert ID fields to strings if they're numbers
    if (sortField.includes('id')) {
      aValue = String(aValue);
      bValue = String(bValue);
    }
    if (aValue == null || bValue == null) return 0; // Handle undefined values
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

  // Add a function to create the oneliner
  const createTradeOneliner = (trade: Trade): string => {
    const upperSymbol = trade.symbol.toUpperCase();
    if (trade.option_type) {
      const optionType = trade.option_type.startsWith("C") ? "CALL" : "PUT";
      const expiration = trade.expiration_date ? 
        trade.expiration_date ? new Date(trade.expiration_date).toLocaleDateString('en-US', { 
          year: '2-digit', 
          month: '2-digit', 
          day: '2-digit',
          timeZone: 'America/New_York'
        }) : "No Exp" : "";
      const strike = trade.strike ? `$${trade.strike.toFixed(2)}` : "";
      return `${expiration} ${upperSymbol} ${strike} ${optionType}`;
    } else {
      return `${upperSymbol} @ $${trade.entry_price.toFixed(2)} ${trade.current_size} Size`;
    }
  };

  const getTradeType = (trade: Trade) => {
    return trade.trade_type === 'Buy to Open' ? 'BTO' : trade.trade_type === 'Sell to Open' ? 'STO' : trade.trade_type === 'BTO' ? 'BTO' : trade.trade_type === 'STO' ? 'STO' : '';
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
          </CardContent>
        </Card>
      )}
      
      <h2 className="text-2xl font-bold">{getHeaderText()}</h2>

      {loading ? (
        <p>Loading trades...</p>
      ) : (
        <Card>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-center whitespace-nowrap w-[50px]">
                    <Button variant="ghost" size="sm">
                      {/* Expand/Collapse column */}
                    </Button>
                  </TableHead>
                  {isDevelopment && debugMode && (
                    <TableHead className="text-center whitespace-nowrap">Trade ID</TableHead>
                  )}
                  <TableHead className="text-center whitespace-nowrap">
                    <Button variant="ghost" onClick={() => handleSort('symbol')}>
                      Symbol {renderSortIcon('symbol')}
                    </Button>
                  </TableHead>
                  <TableHead className="text-center whitespace-nowrap">
                    <Button variant="ghost" onClick={() => handleSort('trade_type')}>
                      Type {renderSortIcon('trade_type')}
                    </Button>
                  </TableHead>
                  <TableHead className="text-center whitespace-nowrap">
                    <Button variant="ghost" onClick={() => handleSort('status')}>
                      Status {renderSortIcon('status')}
                    </Button>
                  </TableHead>
                  <TableHead className="text-center whitespace-nowrap">
                    <Button variant="ghost" onClick={() => handleSort('entry_price')}>
                      Entry Price {renderSortIcon('entry_price')}
                    </Button>
                  </TableHead>
                  <TableHead className="text-center whitespace-nowrap">
                    <Button variant="ghost" onClick={() => handleSort('current_size')}>
                      Size {renderSortIcon('current_size')}
                    </Button>
                  </TableHead>
                  <TableHead className="text-center whitespace-nowrap">
                    <Button variant="ghost" onClick={() => handleSort('expiration_date')}>
                      Expiration Date {renderSortIcon('expiration_date')}
                    </Button>
                  </TableHead>
                  <TableHead className="text-center whitespace-nowrap">
                    <Button variant="ghost" onClick={() => handleSort('created_at')}>
                      Opened At {renderSortIcon('created_at')}
                    </Button>
                  </TableHead>
                  {filterOptions.status !== 'open' && (
                    <TableHead className="text-center whitespace-nowrap">
                      <Button variant="ghost" onClick={() => handleSort('closed_at')}>
                        Closed At {renderSortIcon('closed_at')}
                      </Button>
                    </TableHead>
                  )}
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedTrades.map(trade => (
                  <React.Fragment key={trade.trade_id}>
                    <TableRow>
                      <TableCell className="text-center whitespace-nowrap">
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
                      {isDevelopment && debugMode && <TableCell className="text-center whitespace-nowrap">{trade.trade_id}</TableCell>}
                      <TableCell className="text-center whitespace-nowrap">{createTradeOneliner(trade)}</TableCell>
                      <TableCell className="text-center whitespace-nowrap">{getTradeType(trade)}</TableCell>
                      <TableCell className="text-center whitespace-nowrap">
                        <span className={`px-2 py-1 rounded-full text-xs ${trade.status === 'open' ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'}`}>
                          {trade.status}
                        </span>
                      </TableCell>
                      <TableCell className="text-center whitespace-nowrap">${trade.average_price.toFixed(2)}</TableCell>
                      <TableCell className="text-center whitespace-nowrap">{trade.current_size}</TableCell>
                      <TableCell className="text-center whitespace-nowrap">{trade.expiration_date ? formatDateTime(trade.expiration_date) : ''}</TableCell>
                      <TableCell className="text-center whitespace-nowrap">{formatDateTime(trade.created_at)}</TableCell>
                      {filterOptions.status !== 'open' && (
                        <TableCell className="text-center whitespace-nowrap">{trade.closed_at ? formatDateTime(trade.closed_at) : '-'}</TableCell>
                      )}
                    </TableRow>
                    {expandedTrades.has(trade.trade_id) && (
                      <TableRow>
                        <TableCell colSpan={isDevelopment && debugMode ? 9 : 8}>
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
                                    <TableRow key={String(transaction.id)}>
                                      {isDevelopment && debugMode && <TableCell>{String(transaction.id)}</TableCell>}
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
          </CardContent>
        </Card>
      )}
    </div>
  )
}
