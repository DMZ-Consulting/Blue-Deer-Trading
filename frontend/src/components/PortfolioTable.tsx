'use client'

import React, { useState } from 'react'
import { PortfolioTrade } from '../utils/types'
import { ChevronDown, ChevronUp, ArrowUpDown } from 'lucide-react'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

type SortField = 'symbol' | 'expiration' | 'type' | 'avg_price' | 'size' | 'avg_exit'
type SortOrder = 'asc' | 'desc'

const HighlightedNumber = ({ value, decimals = 2 }: { value: number, decimals?: number }) => {
  const formattedValue = value.toFixed(decimals);
  const className = value >= 0 ? "text-green-500" : "text-red-500";
  return <span className={className}>{formattedValue}</span>;
};

export function PortfolioTableComponent({ portfolio }: { portfolio: PortfolioTrade[] }) {
  const [sortField, setSortField] = useState<SortField>('symbol')
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }

  const sortedPortfolio = [...portfolio].sort((a, b) => {
    const aValue = a.trade[sortField as keyof PortfolioTrade['trade']] ?? '';
    const bValue = b.trade[sortField as keyof PortfolioTrade['trade']] ?? '';
    
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
      <h2 className="text-2xl font-bold">Portfolio</h2>
      <Card>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-center">
                  <Button variant="ghost" onClick={() => handleSort('symbol')}>
                    Symbol {renderSortIcon('symbol')}
                  </Button>
                </TableHead>
                <TableHead className="text-center">
                  <Button variant="ghost">
                    Expiration
                  </Button>
                </TableHead>
                <TableHead className="text-center">
                  <Button variant="ghost">
                    Type
                  </Button>
                </TableHead>
                <TableHead className="text-center">
                  <Button variant="ghost">
                    Avg Price
                  </Button>
                </TableHead>
                <TableHead className="text-center">
                  <Button variant="ghost">
                    Size
                  </Button>
                </TableHead>
                <TableHead className="text-center">
                  <Button variant="ghost">
                    Avg Exit
                  </Button>
                </TableHead>
                <TableHead className="text-center">
                  <Button variant="ghost">
                    Pct Change
                  </Button>
                </TableHead>
                <TableHead className="text-center">
                  <Button variant="ghost">
                    Unit P/L
                  </Button>
                </TableHead>
                <TableHead className="text-center">
                  <Button variant="ghost">
                    Realized P/L
                  </Button>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedPortfolio.map((item, index) => (
                <TableRow key={index}>
                  <TableCell className="text-center">{item.trade.symbol}</TableCell>
                  <TableCell className="text-center">{item.trade.expiration_date ? new Date(item.trade.expiration_date).toLocaleDateString() : 'N/A'}</TableCell>
                  <TableCell className="text-center">{item.trade.trade_type}</TableCell>
                  <TableCell className="text-center">$<HighlightedNumber value={item.avg_entry_price} /></TableCell>
                  <TableCell className="text-center">{item.realized_size}</TableCell>
                  <TableCell className="text-center">$<HighlightedNumber value={item.avg_exit_price} /></TableCell>
                  <TableCell className="text-center"><HighlightedNumber value={item.pct_change} />%</TableCell>
                  <TableCell className="text-center">$<HighlightedNumber value={item.realized_pl / item.realized_size} /></TableCell>
                  <TableCell className="text-center">$<HighlightedNumber value={item.realized_pl} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
