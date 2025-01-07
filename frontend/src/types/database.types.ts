export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      trades: {
        Row: {
          trade_id: string
          symbol: string
          trade_type: string
          status: string
          entry_price: number
          average_price: number | null
          current_size: string | null
          size: string
          created_at: string
          closed_at: string | null
          exit_price: number | null
          average_exit_price: number | null
          profit_loss: number | null
          risk_reward_ratio: number | null
          win_loss: string | null
          configuration_id: number | null
          is_contract: boolean
          is_day_trade: boolean
          strike: number | null
          expiration_date: string | null
          option_type: string | null
        }
        Insert: {
          trade_id: string
          symbol: string
          trade_type: string
          status: string
          entry_price: number
          average_price?: number | null
          current_size?: string | null
          size: string
          created_at?: string
          closed_at?: string | null
          exit_price?: number | null
          average_exit_price?: number | null
          profit_loss?: number | null
          risk_reward_ratio?: number | null
          win_loss?: string | null
          configuration_id?: number | null
          is_contract?: boolean
          is_day_trade?: boolean
          strike?: number | null
          expiration_date?: string | null
          option_type?: string | null
        }
        Update: {
          trade_id?: string
          symbol?: string
          trade_type?: string
          status?: string
          entry_price?: number
          average_price?: number | null
          current_size?: string | null
          size?: string
          created_at?: string
          closed_at?: string | null
          exit_price?: number | null
          average_exit_price?: number | null
          profit_loss?: number | null
          risk_reward_ratio?: number | null
          win_loss?: string | null
          configuration_id?: number | null
          is_contract?: boolean
          is_day_trade?: boolean
          strike?: number | null
          expiration_date?: string | null
          option_type?: string | null
        }
      }
      options_strategy_trades: {
        Row: {
          id: number
          trade_id: string
          name: string
          underlying_symbol: string
          status: string
          created_at: string
          closed_at: string | null
          configuration_id: number | null
          trade_group: string | null
          legs: string
          net_cost: number
          average_net_cost: number
          size: string
          current_size: string
        }
        Insert: {
          id?: number
          trade_id: string
          name: string
          underlying_symbol: string
          status: string
          created_at?: string
          closed_at?: string | null
          configuration_id?: number | null
          trade_group?: string | null
          legs: string
          net_cost: number
          average_net_cost: number
          size: string
          current_size: string
        }
        Update: {
          id?: number
          trade_id?: string
          name?: string
          underlying_symbol?: string
          status?: string
          created_at?: string
          closed_at?: string | null
          configuration_id?: number | null
          trade_group?: string | null
          legs?: string
          net_cost?: number
          average_net_cost?: number
          size?: string
          current_size?: string
        }
      }
      transactions: {
        Row: {
          id: string
          trade_id: string
          transaction_type: string
          amount: number
          size: string
          created_at: string
        }
        Insert: {
          id: string
          trade_id: string
          transaction_type: string
          amount: number
          size: string
          created_at?: string
        }
        Update: {
          id?: string
          trade_id?: string
          transaction_type?: string
          amount?: number
          size?: string
          created_at?: string
        }
      }
      options_strategy_transactions: {
        Row: {
          id: number
          strategy_id: number
          transaction_type: string
          net_cost: number
          size: string
          created_at: string
        }
        Insert: {
          id?: number
          strategy_id: number
          transaction_type: string
          net_cost: number
          size: string
          created_at?: string
        }
        Update: {
          id?: number
          strategy_id?: number
          transaction_type?: string
          net_cost?: number
          size?: string
          created_at?: string
        }
      }
      trade_configurations: {
        Row: {
          id: number
          name: string
          channel_id: string
          role_id: string
          roadmap_channel_id: string
          update_channel_id: string
          portfolio_channel_id: string
          log_channel_id: string
        }
        Insert: {
          id?: number
          name: string
          channel_id: string
          role_id: string
          roadmap_channel_id: string
          update_channel_id: string
          portfolio_channel_id: string
          log_channel_id: string
        }
        Update: {
          id?: number
          name?: string
          channel_id?: string
          role_id?: string
          roadmap_channel_id?: string
          update_channel_id?: string
          portfolio_channel_id?: string
          log_channel_id?: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
  }
}
