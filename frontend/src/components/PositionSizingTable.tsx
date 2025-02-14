'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { TradesTableComponent } from './TradesTable'
import { calculateUnitPrice, calculatePositionMetrics } from '@/utils/position-sizing'
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

  const calculateTotalRealizedPL = useCallback((trades: Trade[]) => {
    return trades.reduce((total, trade) => {
      if (!trade.profit_loss || !trade.transactions) return total;
      
      const tradeConfig = getConfigForTrade(trade);
      const unitsPerRisk = calculateUnitsPerRisk(trade);
      
      const closedTransactions = trade.transactions.filter(t => 
        t.transaction_type === 'CLOSE' || t.transaction_type === 'TRIM'
      );
      
      const totalRiskPositions = closedTransactions.reduce((sum, t) => {
        const transactionSize = parseFloat(t.size || '0');
        const transactionRiskPositions = transactionSize > 0 && unitsPerRisk > 0 
          ? Math.ceil(transactionSize * unitsPerRisk) 
          : 0;
        return sum + transactionRiskPositions;
      }, 0);
      
      const realizedValue = totalRiskPositions > 0 ? trade.profit_loss * totalRiskPositions : 0;
      return total + realizedValue;
    }, 0);
  }, [getConfigForTrade, calculateUnitsPerRisk]);

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
    
    const closedTransactions = trade.transactions?.filter(t => 
      t.transaction_type === 'CLOSE' || t.transaction_type === 'TRIM'
    ) || [];
    
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
          <TableCell className="text-right">
            {trade.trade_configurations?.name || '-'}
          </TableCell>
        </>
      );
    }

    const totalRiskPositions = closedTransactions.reduce((sum, t) => {
      const transactionSize = parseFloat(t.size || '0');
      const transactionRiskPositions = transactionSize > 0 && unitsPerRisk > 0 
        ? Math.ceil(transactionSize * unitsPerRisk) 
        : 0;
      return sum + transactionRiskPositions;
    }, 0);
    
    const realizedValue = totalRiskPositions > 0 ? trade.profit_loss * totalRiskPositions : undefined;

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
        <TableCell className="text-right">
          {trade.trade_configurations?.name || '-'}
        </TableCell>
      </>
    );
  }, [getConfigForTrade, calculateRiskPercentage]);

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
    const riskPositions = transactionSize > 0 && unitsPerRisk > 0 ? Math.ceil(transactionSize * unitsPerRisk) : 0;
    
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