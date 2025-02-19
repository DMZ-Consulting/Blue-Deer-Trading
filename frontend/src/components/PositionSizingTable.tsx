'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { TradesTableComponent } from './TradesTable'
import { calculateUnitPrice } from '@/utils/position-sizing'
import { TimeframeConfig, PositionSizingConfig } from '@/types/position-sizing'
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

export function PositionSizingTable({ 
  configName, 
  filterOptions, 
  positionSizingConfig, 
  allConfigs,
  onRealizedPLUpdate 
}: PositionSizingTableProps) {
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

  const calculateRiskPercentage = useCallback((maxRiskPercent: number): number => {
    const perLevelRisk = maxRiskPercent / 6;
    return perLevelRisk;
  }, []);

  const calculateUnitsPerRisk = useCallback((trade: Trade) => {
    const tradeConfig = getConfigForTrade(trade);
    const unitPrice = calculateUnitPrice({
      symbol: trade.symbol,
      entry_price: trade.entry_price,
      is_contract: trade.is_contract || false
    });

    const riskPercentage = calculateRiskPercentage(tradeConfig.riskTolerancePercent);
    const riskUnit = tradeConfig.portfolioSize * (riskPercentage / 100);
    
    return Math.floor(riskUnit / unitPrice);
  }, [getConfigForTrade, calculateRiskPercentage]);

  const calculateRiskPercentageForLevel = (maxRiskPercent: number, riskLevel: number = 6): number => {
    const perLevelRisk = maxRiskPercent / 6;
    return perLevelRisk * riskLevel;
  };

  const calculateTradeRealizedValue = useCallback((trade: Trade) => {
    if (!trade.average_exit_price || !trade.average_price || !trade.transactions) return 0;

    const tradeConfig = getConfigForTrade(trade);
    const unitPrice = calculateUnitPrice({
      symbol: trade.symbol,
      entry_price: trade.entry_price,
      is_contract: trade.is_contract || false
    });

    const riskPercentage = calculateRiskPercentage(tradeConfig.riskTolerancePercent);
    const riskUnit = tradeConfig.portfolioSize * (riskPercentage / 100);
    const unitsPerRisk = Math.floor(riskUnit / unitPrice);

    // Track open positions as we process transactions chronologically
    let openRiskPositions = 0;
    const totalRiskPositions = trade.transactions.reduce((sum, t) => {
      const transactionSize = parseFloat(t.size || '0');
      const transactionRiskPositions = transactionSize > 0 && unitsPerRisk > 0 
        ? Math.ceil(transactionSize * unitsPerRisk) 
        : 0;

      if (t.transaction_type === 'OPEN' || t.transaction_type === 'ADD') {
        openRiskPositions += transactionRiskPositions;
        return sum;
      } else if (t.transaction_type === 'TRIM' || t.transaction_type === 'CLOSE') {
        // Can only close up to the number of positions currently open
        const closablePositions = Math.min(transactionRiskPositions, openRiskPositions);
        openRiskPositions -= closablePositions;
        return sum + closablePositions;
      }
      return sum;
    }, 0);

    let realizedValue = totalRiskPositions > 0 ? (trade.average_exit_price - trade.average_price) * totalRiskPositions : 0;
    if (trade.is_contract) {
      realizedValue *= 100;
    }
    
    return realizedValue;
  }, [getConfigForTrade, calculateRiskPercentage]);

  const calculateTotalRealizedPL = useCallback((trades: Trade[]) => {
    return trades.reduce((total, trade) => total + calculateTradeRealizedValue(trade), 0);
  }, [calculateTradeRealizedValue]);

  const handleTradesUpdate = (updatedTrades: Trade[]) => {
    setTrades(updatedTrades);
  };

  const renderPositionSizingColumns = useCallback((trade: Trade) => {
    const tradeConfig = getConfigForTrade(trade);
    const unitPrice = calculateUnitPrice({
      symbol: trade.symbol,
      entry_price: trade.entry_price,
      is_contract: trade.is_contract || false
    });

    const riskPercentage = calculateRiskPercentage(tradeConfig.riskTolerancePercent);
    const riskUnit = tradeConfig.portfolioSize * (riskPercentage / 100);
    const unitsPerRisk = Math.floor(riskUnit / unitPrice);
    
    const realizedValue = calculateTradeRealizedValue(trade);

    return (
      <>
        <TableCell className="text-right">
          ${unitPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </TableCell>
        <TableCell className="text-right">
          {unitsPerRisk > 0 ? unitsPerRisk.toLocaleString() : '-'}
        </TableCell>
        <TableCell className="text-right">
          {realizedValue !== 0
            ? `$${realizedValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : '-'
          }
        </TableCell>
        <TableCell className="text-right">
          {trade.trade_configurations?.name || '-'}
        </TableCell>
      </>
    );
  }, [getConfigForTrade, calculateRiskPercentage, calculateTradeRealizedValue]);

  const renderTransactionSizing = useCallback((transaction: Transaction, trade: Trade) => {
    const tradeConfig = getConfigForTrade(trade);
    const unitPrice = calculateUnitPrice({
      symbol: trade.symbol,
      entry_price: trade.entry_price,
      is_contract: trade.is_contract || false
    });

    const riskPercentage = calculateRiskPercentage(tradeConfig.riskTolerancePercent);
    const riskUnit = tradeConfig.portfolioSize * (riskPercentage / 100);
    const unitsPerRisk = Math.floor(riskUnit / unitPrice);
    
    const transactionSize = parseFloat(transaction.size || '0');
    let riskPositions = 0;

    if (transaction.transaction_type === 'CLOSE') {
      // For CLOSE, calculate remaining open risk positions
      const openPositions = trade.transactions
        ?.filter(t => t.transaction_type === 'OPEN' || t.transaction_type === 'ADD')
        .reduce((sum, t) => {
          const size = parseFloat(t.size || '0');
          return sum + (size > 0 && unitsPerRisk > 0 ? Math.ceil(size * unitsPerRisk) : 0);
        }, 0);

      const trimPositions = trade.transactions
        ?.filter(t => t.transaction_type === 'TRIM')
        .reduce((sum, t) => {
          const size = parseFloat(t.size || '0');
          return sum + (size > 0 && unitsPerRisk > 0 ? Math.ceil(size * unitsPerRisk) : 0);
        }, 0);

      const remainingOpen = openPositions ? openPositions - (trimPositions || 0) : 0;
      riskPositions = Math.min(
        transactionSize > 0 && unitsPerRisk > 0 ? Math.ceil(transactionSize * unitsPerRisk) : 0,
        remainingOpen
      );
    } else {
      riskPositions = transactionSize > 0 && unitsPerRisk > 0 ? Math.ceil(transactionSize * unitsPerRisk) : 0;
    }
    
    let positionValue: number | undefined;
    if (riskPositions > 0) {
      positionValue = transaction.amount * riskPositions;
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
  }, [getConfigForTrade, calculateRiskPercentage]);

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
        renderAdditionalColumns={renderPositionSizingColumns}
        renderTransactionColumns={renderTransactionSizing}
        onTradesUpdate={handleTradesUpdate}
      />
    </div>
  );
} 