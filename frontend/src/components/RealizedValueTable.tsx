'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { TradesTableComponent } from './TradesTable'
import { calculateUnitPrice } from '@/utils/position-sizing'
import { TimeframeConfig, PositionSizingConfig } from '@/types/position-sizing'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn } from "@/utils/cn"

interface RealizedValueTableProps {
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
  allConfigs: PositionSizingConfig;
  onRealizedPLUpdate: (timeframe: keyof PositionSizingConfig | 'all', value: number) => void;
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
  trade_configurations?: {
    name: string;
  };
}

export function RealizedValueTable({ 
  configName, 
  filterOptions, 
  positionSizingConfig, 
  allConfigs,
  onRealizedPLUpdate 
}: RealizedValueTableProps) {
  const [trades, setTrades] = useState<Trade[]>([]);
  const lastUpdateRef = React.useRef<string>('');

  const getConfigForTrade = useCallback((trade: Trade): TimeframeConfig => {
    if (!trade.trade_configurations?.name) {
      return positionSizingConfig;
    }

    const configMap: Record<string, TimeframeConfig> = {
      'day_trader': allConfigs.dayTrading,
      'swing_trader': allConfigs.swingTrading,
      'long_term_trader': allConfigs.longTermInvesting
    };

    return configMap[trade.trade_configurations.name] || positionSizingConfig;
  }, [positionSizingConfig, allConfigs]);

  // Calculate realized value based on the trade type
  const calculateRealizedValue = useCallback((trade: Trade): number => {
    // If the trade doesn't have average prices, try to calculate from transactions
    if ((!trade.average_exit_price || !trade.average_price) && trade.transactions && trade.transactions.length > 0) {
      const openTransactions = trade.transactions.filter(t => 
        t.transaction_type === 'OPEN' || t.transaction_type === 'ADD'
      );
      
      const closeTransactions = trade.transactions.filter(t => 
        t.transaction_type === 'CLOSE' || t.transaction_type === 'TRIM'
      );
      
      if (openTransactions.length > 0 && closeTransactions.length > 0) {
        const avgEntryPrice = openTransactions.reduce((sum, t) => sum + t.amount, 0) / openTransactions.length;
        const avgExitPrice = closeTransactions.reduce((sum, t) => sum + t.amount, 0) / closeTransactions.length;
        
        return calculateValueForPrices(trade, avgExitPrice - avgEntryPrice);
      }
      
      return 0;
    }
    
    // If we have average prices, use them
    if (trade.average_exit_price !== null && trade.average_price !== null) {
      const priceDifference = trade.average_exit_price - trade.average_price;
      return calculateValueForPrices(trade, priceDifference);
    }
    
    return 0;
  }, []);
  
  // Helper function to calculate value based on price difference and trade type
  const calculateValueForPrices = useCallback((trade: Trade, priceDifference: number): number => {
    // For ES trades: 1 contract per risk, 5x multiplier
    if (trade.symbol === 'ES') {
      return priceDifference * 50;
    }
    
    // For options contracts: (avg exit - avg entry) * 100 shares per contract * 100 contracts
    if (trade.is_contract || trade.option_type) {
      return priceDifference * 100 * 100;
    }
    
    // For non-options contracts: (avg exit - avg entry) * 1000 shares
    return priceDifference * 1000;
  }, []);

  const calculateTotalRealizedPL = useCallback((trades: Trade[]) => {
    return trades.reduce((total, trade) => {
      const realizedValue = calculateRealizedValue(trade);
      return total + realizedValue;
    }, 0);
  }, [calculateRealizedValue]);

  const handleTradesUpdate = (updatedTrades: Trade[]) => {
    setTrades(updatedTrades);
  };

  const renderRealizedValueColumns = useCallback((trade: Trade) => {
    const unitPrice = calculateUnitPrice({
      symbol: trade.symbol,
      entry_price: trade.entry_price,
      is_contract: trade.is_contract || false
    });

    // Calculate realized value for all trades, even if they don't have average prices
    const realizedValue = calculateRealizedValue(trade);
    let multiplier = '';

    // Determine the multiplier based on trade type
    if (trade.symbol === 'ES') {
      multiplier = '5x';
    } else if (trade.is_contract || trade.option_type) {
      multiplier = '100 contracts × 100 shares';
    } else {
      multiplier = '1000 shares';
    }

    return (
      <>
        <TableCell className="text-right">
          ${unitPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </TableCell>
        <TableCell className="text-right">
          {multiplier}
        </TableCell>
        <TableCell className="text-right">
          <span className={cn(
            realizedValue > 0 ? "text-green-600" : 
            realizedValue < 0 ? "text-red-600" : "text-gray-600"
          )}>
            ${realizedValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </TableCell>
        <TableCell className="text-right">
          {trade.trade_configurations?.name || '-'}
        </TableCell>
      </>
    );
  }, [calculateRealizedValue]);

  const renderTransactionSizing = useCallback((transaction: Transaction, trade: Trade) => {
    // Always calculate position value for all transaction types
    const transactionSize = parseFloat(transaction.size || '0');
    let multiplier = '';
    let positionValue = 0;

    // For ES trades: 1 contract per risk, 5x multiplier
    if (trade.symbol === 'ES') {
      multiplier = '5x';
      positionValue = transaction.amount * 5 * transactionSize;
    }
    // For options contracts: (avg exit - avg entry) * 100 shares per contract * 100 contracts
    else if (trade.is_contract || trade.option_type) {
      multiplier = '100 contracts × 100 shares';
      positionValue = transaction.amount * 100 * 100 * transactionSize;
    }
    // For non-options contracts: (avg exit - avg entry) * 1000 shares
    else {
      multiplier = '1000 shares';
      positionValue = transaction.amount * 1000 * transactionSize;
    }

    return (
      <>
        <TableCell className="text-center">
          {multiplier}
        </TableCell>
        <TableCell className="text-center">
          ${Math.abs(positionValue).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </TableCell>
      </>
    );
  }, []);

  useEffect(() => {
    if (onRealizedPLUpdate && trades.length > 0) {
      // Calculate total realized P/L for all trades
      const totalPL = calculateTotalRealizedPL(trades);
      
      // Calculate realized P/L for each timeframe
      const dayTradingPL = calculateTotalRealizedPL(
        trades.filter((t: Trade) => t.trade_configurations?.name === 'day_trader')
      );
      
      const swingTradingPL = calculateTotalRealizedPL(
        trades.filter((t: Trade) => t.trade_configurations?.name === 'swing_trader')
      );
      
      const longTermPL = calculateTotalRealizedPL(
        trades.filter((t: Trade) => t.trade_configurations?.name === 'long_term_trader')
      );

      // Only update if values have changed
      const newValues = {
        all: totalPL,
        dayTrading: dayTradingPL,
        swingTrading: swingTradingPL,
        longTermInvesting: longTermPL
      };

      // Store previous values in a ref to compare
      const prevValues = JSON.stringify(newValues);
      if (prevValues !== lastUpdateRef.current) {
        Object.entries(newValues).forEach(([timeframe, value]) => {
          onRealizedPLUpdate(timeframe as keyof PositionSizingConfig | 'all', value);
        });
        lastUpdateRef.current = prevValues;
      }
    }
  }, [trades, onRealizedPLUpdate, calculateTotalRealizedPL]);

  return (
    <div className="space-y-4">
      <TradesTableComponent
        configName={configName}
        filterOptions={filterOptions}
        renderAdditionalColumns={renderRealizedValueColumns}
        renderTransactionColumns={renderTransactionSizing}
        onTradesUpdate={handleTradesUpdate}
      />
    </div>
  );
} 