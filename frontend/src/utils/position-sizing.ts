import { Trade, StrategyTrade, PortfolioTrade, PositionSizingConfig, PositionSizingCalculations } from '../types/position-sizing';

export function calculateUnitPrice(trade: Trade | StrategyTrade): number {
  if ('symbol' in trade) {
    // Regular trade
    if (trade.symbol === 'ES') return 2500;
    if (trade.is_contract) return trade.entry_price * 100;
    return trade.entry_price;
  }
  // Strategy trade
  return trade.net_cost * 100;
}

export function calculateMaxPosition(
  portfolioSize: number,
  riskTolerancePercent: number
): number {
  return portfolioSize * (riskTolerancePercent / 100);
}

export function calculateAvailableUnits(
  maxPosition: number,
  unitPrice: number
): number {
  return Math.floor(maxPosition / unitPrice);
}

export function calculatePositionMetrics(
  trade: PortfolioTrade,
  config: PositionSizingConfig
): PositionSizingCalculations {
  const unitPrice = calculateUnitPrice(trade.trade);
  const maxPosition = calculateMaxPosition(
    config.portfolioSize,
    config.riskTolerancePercent
  );
  const availableUnits = calculateAvailableUnits(maxPosition, unitPrice);
  
  return {
    unitPrice,
    maxPositionSize: maxPosition,
    availableUnits,
    realizedValue: trade.realized_pl ? trade.realized_pl * availableUnits : undefined
  };
} 