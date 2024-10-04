'use client'

export interface Trade {
  trade_id: string
  symbol: string
  trade_type: string
  status: string
  entry_price: number
  current_size: string
  created_at: string
  closed_at?: string
  exit_price?: number
  profit_loss?: number
  risk_reward_ratio?: number
  win_loss?: string
}

export interface Transaction {
  id: string
  trade_id: string
  transaction_type: string
  amount: number
  size: string
  created_at: string
}