'use client'

import React from 'react'
import { TradesTableComponent } from './TradesTable'
import { calculateUnitPrice, calculatePositionMetrics } from '@/utils/position-sizing'
import { TimeframeConfig } from '@/types/position-sizing'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn } from "@/utils/cn"

interface PositionSizingTableProps {
  configName: string;
  filterOptions: {
    status: 'ALL' | 'OPEN' | 'CLOSED';
    startDate?: string;
    optionType?: 'options' | 'common';
    symbol?: string;
    minEntryPrice?: number;
    maxEntryPrice?: number;
  };
  positionSizingConfig: TimeframeConfig;
}

interface Transaction {
  id: string;
  trade_id: string;
  transaction_type: string;
  amount: number;
  size: string;
  created_at: string;
}

interface Trade {
  trade_id: string;
  symbol: string;
  trade_type: string;
  status: string;
  entry_price: number;
  current_size: string;
  size?: string;
  expiration_date: string | null;
  created_at: string;
  closed_at: string | null;
  average_price: number | null;
  average_exit_price: number | null;
  profit_loss: number | null;
  option_type?: string;
  strike?: number;
  is_contract?: boolean;
  transactions?: Transaction[];
}

export function PositionSizingTable({ configName, filterOptions, positionSizingConfig }: PositionSizingTableProps) {
  const calculateRiskPositions = (size: number, availableUnits: number) => {
    // Prevent division by zero or very small numbers
    if (availableUnits <= 0 || !isFinite(availableUnits)) {
      return 0;
    }
    return Math.floor(size / availableUnits);
  };

  const calculateUnitsPerRisk = (trade: Trade) => {
    const unitPrice = calculateUnitPrice({
      symbol: trade.symbol,
      entry_price: trade.entry_price,
      is_contract: trade.is_contract || false
    });

    // Calculate one risk unit
    const riskUnit = positionSizingConfig.portfolioSize * (positionSizingConfig.riskTolerancePercent / 100);
    
    // Calculate how many units we can buy with one risk unit
    return Math.floor(riskUnit / unitPrice);
  };

  const renderPositionSizingColumns = (trade: Trade) => {
    const unitPrice = calculateUnitPrice({
      symbol: trade.symbol,
      entry_price: trade.entry_price,
      is_contract: trade.is_contract || false
    });

    // Calculate one risk unit
    const riskUnit = positionSizingConfig.portfolioSize * (positionSizingConfig.riskTolerancePercent / 100);
    
    // Calculate how many units we can buy with one risk unit
    const unitsPerRisk = Math.floor(riskUnit / unitPrice);
    
    // Calculate total closed positions
    const closedTransactions = trade.transactions?.filter(t => 
      t.transaction_type === 'CLOSE' || t.transaction_type === 'TRIM'
    ) || [];
    
    // Only calculate realized values if there are closed transactions and profit/loss exists
    if (closedTransactions.length === 0 || trade.profit_loss === null) {
      return (
        <>
          <TableCell className="text-right">
            ${unitPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </TableCell>
          <TableCell className="text-right">
            {unitsPerRisk > 0 ? unitsPerRisk.toLocaleString() : '-'}
          </TableCell>
          <TableCell className="text-right">-</TableCell>
        </>
      );
    }

    // Calculate risk positions for each closed transaction
    const totalRiskPositions = closedTransactions.reduce((sum, t) => {
      const transactionSize = parseFloat(t.size || '0');
      const transactionRiskPositions = transactionSize > 0 && unitsPerRisk > 0 
        ? Math.ceil(transactionSize / unitsPerRisk) 
        : 0;
      return sum + transactionRiskPositions;
    }, 0);
    
    // Calculate realized value by multiplying profit/loss by total risk positions from closed transactions
    const realizedValue = totalRiskPositions > 0 ? trade.profit_loss * totalRiskPositions : undefined;

    console.log('Realized Value Debug:', {
      symbol: trade.symbol,
      profitLoss: trade.profit_loss,
      closedTransactions: closedTransactions.map(t => ({
        type: t.transaction_type,
        size: t.size,
        riskPositions: Math.ceil(parseFloat(t.size || '0') / unitsPerRisk)
      })),
      unitsPerRisk,
      totalRiskPositions,
      realizedValue
    });

    return (
      <>
        <TableCell className="text-right">
          ${unitPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </TableCell>
        <TableCell className="text-right">
          {unitsPerRisk > 0 ? unitsPerRisk.toLocaleString() : '-'}
        </TableCell>
        <TableCell className="text-right">
          {realizedValue !== undefined
            ? `$${realizedValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : '-'
          }
        </TableCell>
      </>
    );
  };

  const renderTransactionSizing = (transaction: Transaction, trade: Trade) => {
    const unitPrice = calculateUnitPrice({
      symbol: trade.symbol,
      entry_price: trade.entry_price,
      is_contract: trade.is_contract || false
    });

    // Calculate one risk unit
    const riskUnit = positionSizingConfig.portfolioSize * (positionSizingConfig.riskTolerancePercent / 100);
    
    // Calculate how many units we can buy with one risk unit
    const unitsPerRisk = Math.floor(riskUnit / unitPrice);
    
    // Calculate risk positions for this transaction by dividing transaction size by units per risk
    const transactionSize = parseFloat(transaction.size || '0');
    const riskPositions = transactionSize > 0 && unitsPerRisk > 0 ? Math.ceil(transactionSize * unitsPerRisk) : 0;

    console.log('Transaction Sizing Debug:', {
      transactionType: transaction.transaction_type,
      transactionSize,
      unitPrice,
      riskUnit,
      unitsPerRisk,
      riskPositions,
      amount: transaction.amount,
      isContract: trade.is_contract
    });
    
    // Calculate position value based on transaction type
    let positionValue: number | undefined;
    if (riskPositions > 0) {
      // For any transaction type, multiply the amount by number of risk positions
      positionValue = transaction.amount * riskPositions;
      
      // If this is a contract trade, multiply the position value by 100
      if (trade.is_contract) {
        positionValue *= 100;
      }
    }

    return (
      <>
        <TableCell className="text-center">
          {riskPositions > 0 ? `${riskPositions}x` : '-'}
        </TableCell>
        <TableCell className="text-center">
          {positionValue !== undefined
            ? `$${positionValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : '-'
          }
        </TableCell>
      </>
    );
  };

  return (
    <div className="space-y-4">
      <TradesTableComponent
        configName={configName}
        filterOptions={filterOptions}
        renderAdditionalColumns={renderPositionSizingColumns}
        renderTransactionColumns={renderTransactionSizing}
      />
    </div>
  );
} 