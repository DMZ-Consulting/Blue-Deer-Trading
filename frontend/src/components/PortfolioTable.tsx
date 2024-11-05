'use client'

import React, { useState } from 'react'
import { PortfolioEndpoint, PortfolioTrade } from '../utils/types'
import { ChevronDown, ChevronUp, ArrowUpDown } from 'lucide-react'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

type SortField = 'oneliner' | 'expiration' | 'type' | 'avg_price' | 'size' | 'avg_exit'
type SortOrder = 'asc' | 'desc'

const HighlightedNumber = ({ value, decimals = 2, highlight = false }: { value: number, decimals?: number, highlight?: boolean }) => {
  const formattedValue = value.toFixed(decimals);
  if (highlight) {
    const className = value >= 0 ? "text-green-500" : "text-red-500";
    return <span className={className}>{formattedValue}</span>;
  }
  return <span>{formattedValue}</span>;
}

const formatOneliner = (oneliner: string) => {
    return oneliner.replace(/^###\s*/, '');
}

const TradeTable = ({ trades }: { trades: PortfolioTrade[] }) => {
  const [sortField, setSortField] = useState<SortField>('oneliner')
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }

  const sortedTrades = [...trades].sort((a, b) => {
    let aValue, bValue;

    switch (sortField) {
      case 'oneliner':
        aValue = a.oneliner;
        bValue = b.oneliner;
        break;
      case 'type':
        aValue = 'trade' in a && typeof a.trade === 'object' && a.trade && 'trade_type' in a.trade ? (a.trade.trade_type as string) || 'Unknown' : 'Strategy';
        bValue = 'trade' in b && typeof b.trade === 'object' && b.trade && 'trade_type' in b.trade ? (b.trade.trade_type as string) || 'Unknown' : 'Strategy';
        break;
      default:
        aValue = a[sortField as keyof PortfolioTrade] ?? '';
        bValue = b[sortField as keyof PortfolioTrade] ?? '';
    }
    
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
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="text-center whitespace-nowrap">
            <Button variant="ghost" onClick={() => handleSort('oneliner')}>
              Trade {renderSortIcon('oneliner')}
            </Button>
          </TableHead>
          <TableHead className="text-center whitespace-nowrap">
            <Button variant="ghost">Type</Button>
          </TableHead>
          <TableHead className="text-center whitespace-nowrap">
            <Button variant="ghost">Avg Price</Button>
          </TableHead>
          <TableHead className="text-center whitespace-nowrap">
            <Button variant="ghost">Size</Button>
          </TableHead>
          <TableHead className="text-center whitespace-nowrap">
            <Button variant="ghost">Avg Exit</Button>
          </TableHead>
          <TableHead className="text-center whitespace-nowrap">
            <Button variant="ghost">Pct Change</Button>
          </TableHead>
          <TableHead className="text-center whitespace-nowrap">
            <Button variant="ghost">Unit P/L</Button>
          </TableHead>
          <TableHead className="text-center whitespace-nowrap">
            <Button variant="ghost">Realized P/L</Button>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sortedTrades.map((item, index) => {
          let tradeType = 'Strategy';
          if ('trade' in item && item.trade && typeof item.trade === 'object' && 'trade_type' in item.trade) {
            tradeType = (item.trade.trade_type as string) || 'Unknown';
          }

          return (
            <TableRow key={index} className={tradeType === 'strategy' ? 'bg-slate-50' : ''}>
              <TableCell className="text-center whitespace-nowrap">{formatOneliner(item.oneliner)}</TableCell>
              <TableCell className="text-center whitespace-nowrap">{tradeType}</TableCell>
              <TableCell className="text-center whitespace-nowrap">$<HighlightedNumber value={item.avg_entry_price} /></TableCell>
              <TableCell className="text-center whitespace-nowrap">{item.realized_size}</TableCell>
              <TableCell className="text-center whitespace-nowrap">$<HighlightedNumber value={item.avg_exit_price} /></TableCell>
              <TableCell className="text-center whitespace-nowrap"><HighlightedNumber value={item.pct_change} highlight={true} />%</TableCell>
              <TableCell className="text-center whitespace-nowrap">$<HighlightedNumber value={item.realized_pl / item.realized_size} highlight={true} /></TableCell>
              <TableCell className="text-center whitespace-nowrap">$<HighlightedNumber value={item.realized_pl} highlight={true} /></TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  )
}

export function PortfolioTableComponent({ portfolio }: { portfolio: PortfolioEndpoint }) {
  const allTrades = [...portfolio.regular_trades, ...portfolio.strategy_trades];
  
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Portfolio</h2>
      <Card>
        <CardContent>
          <TradeTable trades={allTrades} />
        </CardContent>
      </Card>
    </div>
  )
}
