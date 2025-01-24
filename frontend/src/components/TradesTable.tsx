'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Trade } from '../utils/types'
import { ChevronDown, ChevronUp, ArrowUpDown, Settings2, X } from 'lucide-react'
import { getTradesByConfiguration, deleteTransaction, updateTransaction } from '../api/api'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

import 'react-datepicker/dist/react-datepicker.css'

interface FilterOptions {
  status: 'ALL' | 'OPEN' | 'CLOSED';
  startDate?: string;
  optionType?: 'options' | 'common';
  symbol?: string;
  minEntryPrice?: number;
  maxEntryPrice?: number;
}

interface TradesTableProps {
  configName: string;
  filterOptions: FilterOptions;
  showAllTrades?: boolean;
  allowTransactionActions?: boolean;
}

// Add these type definitions at the top of the file
type SortField = keyof Trade
type SortOrder = 'asc' | 'desc'

interface TransactionFormData {
  amount: number;
  size: string;
  transaction_type: string;  // Keep this for the API but don't show it in the UI
}

interface Transaction {
  id: string;
  trade_id: string;
  transaction_type: string;
  amount: number;
  size: string;
  created_at: string;
}

interface FormError {
  size?: string | undefined;
  amount?: string | undefined;
}

export function TradesTableComponent({ configName, filterOptions, showAllTrades = false, allowTransactionActions = false }: TradesTableProps) {
  const [trades, setTrades] = useState<Trade[]>([])
  const [expandedTrades, setExpandedTrades] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [debugMode, setDebugMode] = useState(false)
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [editingTransaction, setEditingTransaction] = useState<{ id: string; trade_id: string } | null>(null)
  const [columnVisibility, setColumnVisibility] = useState({
    symbol: true,
    type: true,
    status: true,
    entryPrice: true,
    size: true,
    expirationDate: true,
    openedAt: true,
    closedAt: true,
  })
  const [editFormData, setEditFormData] = useState<TransactionFormData>({
    amount: 0,
    size: '',
    transaction_type: '',  // Initialize with an empty string
  });
  const [editFormError, setEditFormError] = useState<FormError>({});

  const fetchTrades = useCallback(async () => {
    setLoading(true)
    try {
      const requestParams = {
        configName: configName === '' ? 'all' : configName,
        status: filterOptions.status,
        weekFilter: filterOptions.startDate,
        optionType: filterOptions.optionType,
        symbol: filterOptions.symbol,
        minEntryPrice: filterOptions.minEntryPrice,
        maxEntryPrice: filterOptions.maxEntryPrice,
        showAllTrades
      };

      // console.log("Fetching trades with request:", {
      //   action: 'getTrades',
      //   filters: requestParams
      // });

      const fetchedTrades = await getTradesByConfiguration(requestParams)
      //console.log("Received trades response:", fetchedTrades);
      setTrades(fetchedTrades as Trade[])
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
    if (!filterOptions.startDate) {
      if (filterOptions.status === 'OPEN') {
        return `Trades Remaining Open`
      } else if (filterOptions.status === 'CLOSED') {
        return `Closed Trades`
      } else {
        return 'All Trades'
      }
    }

    const date = new Date(filterOptions.startDate + 'T00:00:00Z');
    const friday = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() + (5 - date.getUTCDay() + 7) % 7));
    if (filterOptions.status === 'OPEN') {
      return `Trades Remaining Open`
    } else if (filterOptions.status === 'CLOSED') {
      return `Trades Realized for the week of ${friday.toLocaleDateString(undefined, { timeZone: 'UTC' })}`
    } else {
      return 'All Trades'
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

    // date may come in this format "2025-01-22T20:48:08.699+00:00"
    // we need to convert it to "2025-01-22 20:48:08"
    // +00:00 is timezone for UTC
    // we need to remove the timezone and the milliseconds, but apply the timezone to the date
    const formattedDate = dateString.replace('T', ' ').replace('.699+00:00', '')
    
    // Parse the UTC date string
    const utcDate = new Date(formattedDate + 'Z');
    
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

  const getStatusColor = (status: string) => {
    switch (status.toUpperCase()) {
      case 'OPEN':
        return 'bg-green-200 text-green-800';
      case 'CLOSED':
        return 'bg-red-200 text-red-800';
      default:
        return 'bg-gray-200 text-gray-800';
    }
  };

  const getTransactionTypeColor = (type: string) => {
    switch (type.toUpperCase()) {
      case 'OPEN':
        return 'bg-green-200 text-green-800';
      case 'ADD':
        return 'bg-blue-200 text-blue-800';
      case 'TRIM':
        return 'bg-yellow-200 text-yellow-800';
      case 'CLOSE':
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

  const getTradeStatus = (trade: Trade) => {
    return trade.status.toUpperCase() as 'OPEN' | 'CLOSED'
  }

  // Add handlers for edit and delete
  const handleEditTransaction = async (transactionId: string, tradeId: string) => {
    const trade = trades.find(t => t.trade_id === tradeId);
    const transaction = trade?.transactions?.find(t => String(t.id) === transactionId);
    
    if (transaction) {
      setEditFormData({
        amount: transaction.amount,
        size: transaction.size,
        transaction_type: transaction.transaction_type,  // Keep the original type
      });
      setEditingTransaction({ id: transactionId, trade_id: tradeId });
    }
  };

  const validateSize = (newSize: string, trade: Trade, editedTransaction: Transaction) => {
    const oldSize = parseFloat(editedTransaction.size);
    const proposedSize = parseFloat(newSize);
    
    if (isNaN(proposedSize)) return undefined;

    const sizeDiff = editedTransaction.transaction_type === 'OPEN' || editedTransaction.transaction_type === 'ADD'
      ? proposedSize - oldSize
      : oldSize - proposedSize;

    const currentTradeSize = trade.current_size ? parseFloat(trade.current_size) : 0;
    const newTotalSize = currentTradeSize + sizeDiff;

    return newTotalSize < 0 ? `This size would result in a negative total size (${newTotalSize})` : undefined;
  };

  const validateAmount = (amount: number) => {
    if (amount < 0) {
      return 'Amount cannot be negative';
    }
    return undefined;
  };

  const handleAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newAmount = parseFloat(e.target.value);
    setEditFormData(prev => ({ ...prev, amount: newAmount }));

    const error = validateAmount(newAmount);
    setEditFormError(prev => ({
      ...prev,
      amount: error
    }));
  };

  const handleSizeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newSize = e.target.value;
    setEditFormData(prev => ({ ...prev, size: newSize }));

    if (!editingTransaction) return;

    const trade = trades.find(t => t.trade_id === editingTransaction.trade_id);
    const editedTransaction = trade?.transactions?.find(t => String(t.id) === editingTransaction.id);
    
    if (!trade || !editedTransaction) return;

    const error = validateSize(newSize, trade, editedTransaction);
    setEditFormError(prev => ({
      ...prev,
      size: error
    }));
  };

  const handleSaveEdit = async () => {
    if (!editingTransaction || Object.values(editFormError).some(error => error)) return;

    try {
      await updateTransaction(editingTransaction.id, editFormData);
      setEditingTransaction(null);
      setEditFormError({});
      fetchTrades();
    } catch (error) {
      console.error('Error updating transaction:', error);
      alert('Failed to update transaction');
    }
  };

  const handleDeleteTransaction = async (transactionId: string, tradeId: string) => {
    if (!window.confirm('Are you sure you want to delete this transaction?')) {
      return;
    }

    try {
      // TODO: Implement delete API call
      await deleteTransaction(transactionId);
      // Refresh trades after deletion
      fetchTrades();
    } catch (error) {
      console.error('Error deleting transaction:', error);
      alert('Failed to delete transaction');
    }
  };

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
      
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">{getHeaderText()}</h2>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="ml-auto">
              <Settings2 className="h-4 w-4" />
              <span className="ml-2">Columns</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuCheckboxItem
              checked={columnVisibility.symbol}
              onCheckedChange={(checked) => 
                setColumnVisibility(prev => ({ ...prev, symbol: checked }))
              }
            >
              Symbol
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem
              checked={columnVisibility.type}
              onCheckedChange={(checked) => 
                setColumnVisibility(prev => ({ ...prev, type: checked }))
              }
            >
              Type
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem
              checked={columnVisibility.status}
              onCheckedChange={(checked) => 
                setColumnVisibility(prev => ({ ...prev, status: checked }))
              }
            >
              Status
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem
              checked={columnVisibility.entryPrice}
              onCheckedChange={(checked) => 
                setColumnVisibility(prev => ({ ...prev, entryPrice: checked }))
              }
            >
              Entry Price
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem
              checked={columnVisibility.size}
              onCheckedChange={(checked) => 
                setColumnVisibility(prev => ({ ...prev, size: checked }))
              }
            >
              Size
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem
              checked={columnVisibility.expirationDate}
              onCheckedChange={(checked) => 
                setColumnVisibility(prev => ({ ...prev, expirationDate: checked }))
              }
            >
              Expiration Date
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem
              checked={columnVisibility.openedAt}
              onCheckedChange={(checked) => 
                setColumnVisibility(prev => ({ ...prev, openedAt: checked }))
              }
            >
              Opened At
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem
              checked={columnVisibility.closedAt}
              onCheckedChange={(checked) => 
                setColumnVisibility(prev => ({ ...prev, closedAt: checked }))
              }
            >
              Closed At
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {loading ? (
        <p>Loading trades...</p>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="max-h-[800px] overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-center whitespace-nowrap w-[50px] sticky top-0 bg-white">
                      <Button variant="ghost" size="sm">
                        {/* Expand/Collapse column */}
                      </Button>
                    </TableHead>
                    {isDevelopment && debugMode && (
                      <TableHead className="text-center whitespace-nowrap sticky top-0 bg-white">Trade ID</TableHead>
                    )}
                    {columnVisibility.symbol && (
                      <TableHead className="text-center whitespace-nowrap sticky top-0 bg-white">
                        <Button variant="ghost" onClick={() => handleSort('symbol')}>
                          Symbol {renderSortIcon('symbol')}
                        </Button>
                      </TableHead>
                    )}
                    {columnVisibility.type && (
                      <TableHead className="text-center whitespace-nowrap sticky top-0 bg-white">
                        <Button variant="ghost" onClick={() => handleSort('trade_type')}>
                          Type {renderSortIcon('trade_type')}
                        </Button>
                      </TableHead>
                    )}
                    {columnVisibility.status && (
                      <TableHead className="text-center whitespace-nowrap sticky top-0 bg-white">
                        <Button variant="ghost" onClick={() => handleSort('status')}>
                          Status {renderSortIcon('status')}
                        </Button>
                      </TableHead>
                    )}
                    {columnVisibility.entryPrice && (
                      <TableHead className="text-center whitespace-nowrap sticky top-0 bg-white">
                        <Button variant="ghost" onClick={() => handleSort('entry_price')}>
                          Entry Price {renderSortIcon('entry_price')}
                        </Button>
                      </TableHead>
                    )}
                    {columnVisibility.size && (
                      <TableHead className="text-center whitespace-nowrap sticky top-0 bg-white">
                        <Button variant="ghost" onClick={() => handleSort('current_size')}>
                          Size {renderSortIcon('current_size')}
                        </Button>
                      </TableHead>
                    )}
                    {columnVisibility.expirationDate && (
                      <TableHead className="text-center whitespace-nowrap sticky top-0 bg-white">
                        <Button variant="ghost" onClick={() => handleSort('expiration_date')}>
                          Expiration Date {renderSortIcon('expiration_date')}
                        </Button>
                      </TableHead>
                    )}
                    {columnVisibility.openedAt && (
                      <TableHead className="text-center whitespace-nowrap sticky top-0 bg-white">
                        <Button variant="ghost" onClick={() => handleSort('created_at')}>
                          Opened At {renderSortIcon('created_at')}
                        </Button>
                      </TableHead>
                    )}
                    {filterOptions.status !== 'OPEN' && columnVisibility.closedAt && (
                      <TableHead className="text-center whitespace-nowrap sticky top-0 bg-white">
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
                        {columnVisibility.symbol && (
                          <TableCell className="text-center whitespace-nowrap">{createTradeOneliner(trade)}</TableCell>
                        )}
                        {columnVisibility.type && (
                          <TableCell className="text-center whitespace-nowrap">{getTradeType(trade)}</TableCell>
                        )}
                        {columnVisibility.status && (
                          <TableCell className="text-center whitespace-nowrap">
                            <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(getTradeStatus(trade))}`}>
                              {getTradeStatus(trade)}
                            </span>
                          </TableCell>
                        )}
                        {columnVisibility.entryPrice && (
                          <TableCell className="text-center whitespace-nowrap">${trade.average_price?.toFixed(2) ?? 'N/A'}</TableCell>
                        )}
                        {columnVisibility.size && (
                          <TableCell className="text-center whitespace-nowrap">{trade.current_size}</TableCell>
                        )}
                        {columnVisibility.expirationDate && (
                          <TableCell className="text-center whitespace-nowrap">{trade.expiration_date ? formatDateTime(trade.expiration_date) : ''}</TableCell>
                        )}
                        {columnVisibility.openedAt && (
                          <TableCell className="text-center whitespace-nowrap">{formatDateTime(trade.created_at)}</TableCell>
                        )}
                        {filterOptions.status !== 'OPEN' && columnVisibility.closedAt && (
                          <TableCell className="text-center whitespace-nowrap">{trade.closed_at ? formatDateTime(trade.closed_at) : '-'}</TableCell>
                        )}
                      </TableRow>
                      {expandedTrades.has(trade.trade_id) && (
                        <TableRow>
                          <TableCell colSpan={Object.values(columnVisibility).filter(Boolean).length + (isDevelopment && debugMode ? 2 : 1)}>
                            <Card>
                              <CardHeader>
                                <CardTitle>Transactions</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <Table>
                                  <TableHeader>
                                    <TableRow>
                                      {isDevelopment && debugMode && <TableHead className="text-center">Transaction ID</TableHead>}
                                      <TableHead className="text-center w-24">Type</TableHead>
                                      <TableHead className="text-center w-24">Price</TableHead>
                                      <TableHead className="text-center w-16">Size</TableHead>
                                      <TableHead className="text-center w-40">Date</TableHead>
                                      {allowTransactionActions && (
                                        <TableHead className="text-center w-32">Actions</TableHead>
                                      )}
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {trade.transactions?.sort((a, b) => 
                                      new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
                                    ).map((transaction, index, array) => (
                                      <TableRow key={String(transaction.id)}>
                                        {isDevelopment && debugMode && <TableCell className="text-center">{String(transaction.id)}</TableCell>}
                                        <TableCell className="text-center">
                                          <span className={`px-2 py-1 rounded-full text-xs ${getTransactionTypeColor(transaction.transaction_type)}`}>
                                            {transaction.transaction_type}
                                          </span>
                                        </TableCell>
                                        <TableCell className="text-center">${transaction.amount.toFixed(2)}</TableCell>
                                        <TableCell className="text-center">{transaction.size}</TableCell>
                                        <TableCell className="text-center whitespace-nowrap">{new Date(transaction.created_at).toLocaleString()}</TableCell>
                                        {allowTransactionActions && (
                                          <TableCell>
                                            <div className="flex justify-center space-x-2">
                                              <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleEditTransaction(String(transaction.id), trade.trade_id)}
                                              >
                                                Edit
                                              </Button>
                                              {index === array.length - 1 && transaction.transaction_type !== 'OPEN' && (
                                                <Button
                                                  variant="ghost"
                                                  size="sm"
                                                  className="text-red-600 hover:text-red-800"
                                                  onClick={() => handleDeleteTransaction(String(transaction.id), trade.trade_id)}
                                                >
                                                  Delete
                                                </Button>
                                              )}
                                            </div>
                                          </TableCell>
                                        )}
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
          </CardContent>
        </Card>
      )}

      <Dialog open={editingTransaction !== null} onOpenChange={() => {
        setEditingTransaction(null);
        setEditFormError({});
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Transaction</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label htmlFor="amount">Amount</label>
              <Input
                id="amount"
                type="number"
                step="0.01"
                value={editFormData.amount}
                onChange={handleAmountChange}
                className={editFormError.amount ? 'border-red-500' : ''}
              />
              {editFormError.amount && (
                <p className="text-sm text-red-500">{editFormError.amount}</p>
              )}
            </div>
            <div className="grid gap-2">
              <label htmlFor="size">Size</label>
              <Input
                id="size"
                value={editFormData.size}
                onChange={handleSizeChange}
                className={editFormError.size ? 'border-red-500' : ''}
              />
              {editFormError.size && (
                <p className="text-sm text-red-500">{editFormError.size}</p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setEditingTransaction(null);
              setEditFormError({});
            }}>
              Cancel
            </Button>
            <Button 
              onClick={handleSaveEdit} 
              disabled={Object.values(editFormError).some(error => error)}
            >
              Save changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
