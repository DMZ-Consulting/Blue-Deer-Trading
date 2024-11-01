'use client'

export interface Trade {
  trade_id: string
  symbol: string
  trade_type: string
  status: string
  entry_price: number
  average_price: number
  current_size: number
  is_contract: boolean
  created_at: string
  closed_at?: string
  exit_price?: number
  profit_loss?: number
  risk_reward_ratio?: number
  win_loss?: string
  transactions?: Transaction[]
  expiration_date?: string
  option_type?: string
  strike?: number
}

export interface StrategyTransaction {
  id: string
  strategy_id: string
  transaction_type: string
  net_cost: number
  size: string
  created_at: string
}

export interface StrategyTrade {
  id: string
  name: string
  underlying_symbol: string
  status: string
  created_at: string
  closed_at?: string
  configuration_id?: string
  transactions: StrategyTransaction[]
  trade_group?: string
  trade_id: string
  legs: string
  net_cost: number
  average_net_cost: number
  size: string
  current_size: string
}

export interface PortfolioEndpoint{
  regular_trades: RegularPortfolioTrade[]
  strategy_trades: PortfolioStrategyTrade[]
}

export interface Transaction {
  id: string
  trade_id: string
  transaction_type: string
  amount: number
  size: string
  created_at: string
}



export interface PortfolioTrade {
  trade: unknown
  oneliner: string
  realized_pl: number
  realized_size: number
  avg_entry_price: number
  avg_exit_price: number
  pct_change: number
}

export interface RegularPortfolioTrade extends PortfolioTrade {
  trade: Trade
}

export interface PortfolioStrategyTrade extends PortfolioTrade {
  trade: StrategyTrade
}
