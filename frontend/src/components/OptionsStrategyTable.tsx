'use client'

import { useState, useEffect } from 'react'
import { OptionsStrategyTrade } from '../utils/types'
import { ChevronDown, ChevronUp, ArrowUpDown } from 'lucide-react'
import { getOptionsStrategyTradesByConfiguration } from '../api/api'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

import 'react-datepicker/dist/react-datepicker.css'

interface OptionsStrategyTableProps {
  configName: string
  statusFilter: string
  dateFilter: string
}

type SortField = keyof OptionsStrategyTrade
type SortOrder = 'asc' | 'desc'

interface Leg {
  symbol: string;
  expiration_date: string;
  strike: number;
  option_type: string;
  trade_type: string;
}

export function OptionsStrategyTableComponent({ configName, statusFilter, dateFilter }: OptionsStrategyTableProps) {
  const [trades, setTrades] = useState<OptionsStrategyTrade[]>([])
  const [expandedTrades, setExpandedTrades] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  useEffect(() => {
    const fetchTrades = async () => {
      setLoading(true)
      try {
        const fetchedTrades = await getOptionsStrategyTradesByConfiguration(
          configName,
          statusFilter,
          dateFilter
        )
        setTrades(fetchedTrades)
      } catch (error) {
        console.error('Error fetching trades:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchTrades()
  }, [configName, statusFilter, dateFilter])

  const toggleExpand = (tradeId: string) => {
    setExpandedTrades(prev => {
      const newSet = new Set(prev)
      if (newSet.has(tradeId)) {
        newSet.delete(tradeId)
      } else {
        newSet.add(tradeId)
      }
      return newSet
    })
  }

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }

  const sortedTrades = [...trades].sort((a, b) => {
    const aValue = a[sortField]
    const bValue = b[sortField]
    const modifier = sortOrder === 'asc' ? 1 : -1

    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return aValue.localeCompare(bValue) * modifier
    }
    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return (aValue - bValue) * modifier
    }
    return 0
  })

  const SortButton = ({ field, label }: { field: SortField; label: string }) => (
    <Button
      variant="ghost"
      onClick={() => handleSort(field)}
      className="h-8 flex items-center gap-1"
    >
      {label}
      <ArrowUpDown className="h-4 w-4" />
    </Button>
  )

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'open':
        return 'bg-green-200 text-green-800';
      case 'closed':
        return 'bg-red-200 text-red-800';
      default:
        return 'bg-gray-200 text-gray-800';
    }
  };

  const createTradeOneliner = (trade: OptionsStrategyTrade): string => {
    try {
      const legs: Leg[] = JSON.parse(trade.legs);
      let oneliner = `${trade.underlying_symbol} - ${trade.name} `;
      
      // Add date from first leg
      const exp_date = legs[0].expiration_date;
      let multiple_exp_dates = false;
      for (const leg of legs) {
        if (leg.expiration_date !== exp_date) {
          multiple_exp_dates = true;
          break;
        }
      }
    
      if (legs.length > 0 && !multiple_exp_dates) {
        const date = new Date(legs[0].expiration_date);
        oneliner += `(${date.toLocaleDateString('en-US', { 
          month: '2-digit', 
          day: '2-digit', 
          year: '2-digit',
          timeZone: 'UTC'
        })}) `;
      } else {
        let oneliner_exp_date = '(';
        for (const leg of legs) {
          if (oneliner_exp_date !== '(') {
            oneliner_exp_date += leg.trade_type.startsWith('BTO') ? '+' : '-';
          }
          oneliner_exp_date += `${new Date(leg.expiration_date).toLocaleDateString('en-US', { 
            month: '2-digit', 
            day: '2-digit', 
            year: '2-digit',
            timeZone: 'UTC'
          })}`;
        }
        oneliner += oneliner_exp_date + ') ';
      }

      // Add each leg
      legs.forEach((leg, index) => {
        if (index > 0) {
          // Add + for calls, - for puts after the first leg
          oneliner += leg.trade_type.startsWith('BTO') ? '+' : '-';
        }
        oneliner += `${leg.strike}${leg.option_type[0]}`;
      });

      return oneliner;
    } catch (error) {
      console.error('Error parsing legs:', error);
      return `${trade.underlying_symbol} - ${trade.name}`;
    }
  };

  if (loading) {
    return <div>Loading...</div>
  }

  return (
    <Card>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead></TableHead>
              <TableHead className="text-center">
                <div className="flex justify-center">
                  <SortButton field="name" label="Strategy" />
                </div>
              </TableHead>
              <TableHead className="text-center">
                <div className="flex justify-center">
                  <SortButton field="status" label="Status" />
                </div>
              </TableHead>
              <TableHead className="text-center">
                <div className="flex justify-center">
                  <SortButton field="net_cost" label="Net Cost" />
                </div>
              </TableHead>
              <TableHead className="text-center">
                <div className="flex justify-center">
                  <SortButton field="average_net_cost" label="Avg Cost" />
                </div>
              </TableHead>
              <TableHead className="text-center">
                <div className="flex justify-center">
                  <SortButton field="current_size" label="Size" />
                </div>
              </TableHead>
              <TableHead className="text-center">
                <div className="flex justify-center">
                  <SortButton field="created_at" label="Date" />
                </div>
              </TableHead>
              {statusFilter === 'closed' && (
                <TableHead><SortButton field="closed_at" label="Closed Date" /></TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedTrades.map((trade) => (
              <TableRow key={trade.trade_id}>
                <TableCell>
                  <Button
                    variant="ghost"
                    onClick={() => toggleExpand(trade.trade_id)}
                    className="h-8 w-8 p-0"
                  >
                    {expandedTrades.has(trade.trade_id) ? 
                      <ChevronUp className="h-4 w-4" /> : 
                      <ChevronDown className="h-4 w-4" />
                    }
                  </Button>
                </TableCell>
                <TableCell className="whitespace-nowrap text-center">
                  {createTradeOneliner(trade)}
                </TableCell>
                <TableCell className="text-center">
                  <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(trade.status)}`}>
                    {trade.status}
                  </span>
                </TableCell>
                <TableCell className="text-center">${trade.net_cost.toFixed(2)}</TableCell>
                <TableCell className="text-center">${trade.average_net_cost.toFixed(2)}</TableCell>
                <TableCell className="text-center">{trade.current_size}</TableCell>
                <TableCell className="text-center">{new Date(trade.created_at).toLocaleDateString()}</TableCell>
                {statusFilter === 'closed' && trade.closed_at && (
                  <TableCell className="text-center">{new Date(trade.closed_at).toLocaleDateString()}</TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
} 