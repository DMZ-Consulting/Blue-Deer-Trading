'use client'

export interface Trade {
  trade_id: string
  symbol: string
  trade_type: string
  status: string
  entry_price: number
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

export interface Transaction {
  id: string
  trade_id: string
  transaction_type: string
  amount: number
  size: string
  created_at: string
}

export interface PortfolioTrade {
  trade: Trade
  oneliner: string
  realized_pl: number
  realized_size: number
  avg_entry_price: number
  avg_exit_price: number
  pct_change: number
}
