export interface TimeframeConfig {
  portfolioSize: number;
  riskTolerancePercent: number;
}

export interface PositionSizingConfig {
  dayTrading: TimeframeConfig;  // 1-5 Days
  swingTrading: TimeframeConfig;  // 6-90 Days
  longTermInvesting: TimeframeConfig;  // >90 Days
}

export interface PositionSizingCalculations {
  unitPrice: number;
  maxPositionSize: number;
  availableUnits: number;
  realizedValue?: number;
}

export interface Trade {
  symbol: string;
  entry_price: number;
  is_contract: boolean;
}

export interface StrategyTrade {
  net_cost: number;
}

export interface PortfolioTrade {
  trade: Trade | StrategyTrade;
  realized_pl?: number;
  positionSizing?: PositionSizingCalculations;
} 