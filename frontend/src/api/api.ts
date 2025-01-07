import { createClient } from '@supabase/supabase-js'
import { Database } from '@/types/database.types'
import { OptionsStrategyTrade as UtilsOptionsStrategyTrade } from '@/utils/types'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

const supabase = supabaseUrl && supabaseAnonKey
  ? createClient<Database>(supabaseUrl, supabaseAnonKey)
  : null

type Trade = Database['public']['Tables']['trades']['Row'] & {
  trade_configurations: Database['public']['Tables']['trade_configurations']['Row'] | null
}

type DatabaseOptionsStrategyTrade = Database['public']['Tables']['options_strategy_trades']['Row'] & {
  trade_configurations: Database['public']['Tables']['trade_configurations']['Row'] | null
}

type Transaction = Database['public']['Tables']['transactions']['Row']
type OptionsStrategyTransaction = Database['public']['Tables']['options_strategy_transactions']['Row']
type TradeConfiguration = Database['public']['Tables']['trade_configurations']['Row']

interface TradeFilters {
  configName: string
  skip?: number
  limit?: number
  status?: string
  symbol?: string
  tradeType?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  weekFilter?: string
  monthFilter?: string
  yearFilter?: string
  optionType?: string
  maxEntryPrice?: number
  minEntryPrice?: number
  tradeGroup?: string
  showAllTrades?: boolean
}

interface StrategyFilters {
  skip?: number
  limit?: number
  status?: 'OPEN' | 'CLOSED'
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  configName?: string
  weekFilter?: string
}

interface PortfolioFilters {
  skip?: number
  limit?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  configName?: string
  weekFilter?: string
}

export interface MonthlyPL {
  month: string
  profit_loss: number
}

interface PortfolioStats {
  totalTrades: number
  winRate: number
  averageWin: number
  averageLoss: number
  profitFactor: number
  totalProfitLoss: number
  averageRiskRewardRatio: number
}

interface PortfolioStatsFilters {
  configName: string
  status: string
  weekFilter?: string
  optionType?: string
}

// Helper functions
export const getTradesByConfiguration = async (filters: TradeFilters): Promise<Trade[]> => {
  if (!supabase) return []
  return api.trades.getByFilters(filters)
}

export const getOptionsStrategyTradesByConfiguration = async (filters: StrategyFilters): Promise<UtilsOptionsStrategyTrade[]> => {
  if (!supabase) return []
  const data = await api.optionsStrategyTrades.getByFilters(filters)
  return data.map(trade => ({
    trade_id: trade.id.toString(),
    name: trade.name,
    underlying_symbol: trade.underlying_symbol,
    status: trade.status as 'OPEN' | 'CLOSED',
    net_cost: trade.net_cost,
    average_net_cost: trade.average_net_cost,
    size: trade.size,
    current_size: trade.current_size,
    created_at: trade.created_at,
    closed_at: trade.closed_at || undefined,
    legs: trade.legs
  }))
}

export const getPortfolio = async (filters: PortfolioFilters) => {
  if (!supabase) return { regular_trades: [], strategy_trades: [] }
  return api.portfolio.getTrades(filters)
}

export const getMonthlyPL = async (configName: string) => {
  if (!supabase) return []
  return api.portfolio.getMonthlyPL(configName)
}

export const api = {
  trades: {
    getAll: async (): Promise<Trade[]> => {
      if (!supabase) return []
      const { data, error } = await supabase.functions.invoke('trades', {
        body: { action: 'getAll' }
      })
      if (error) throw error
      return data
    },

    getByFilters: async (filters: TradeFilters): Promise<Trade[]> => {
      if (!supabase) return []
      const { data, error } = await supabase.functions.invoke('trades', {
        body: { action: 'getTrades', filters }
      })
      if (error) throw error
      return data
    },

    create: async (input: {
      symbol: string
      trade_type: string
      entry_price: number
      size: string
      expiration_date?: string
      strike?: number
      configuration_id?: number
      is_contract?: boolean
      is_day_trade?: boolean
      option_type?: string
    }): Promise<Trade> => {
      if (!supabase) throw new Error('Supabase client not initialized')
      const { data, error } = await supabase.functions.invoke('trades', {
        body: { action: 'createTrade', input }
      })
      if (error) throw error
      return data
    },

    addToTrade: async (trade_id: string, price: number, size: string): Promise<Trade> => {
      if (!supabase) throw new Error('Supabase client not initialized')
      const { data, error } = await supabase.functions.invoke('trades', {
        body: { action: 'addToTrade', trade_id, price, size }
      })
      if (error) throw error
      return data
    },

    trimTrade: async (trade_id: string, price: number, size: string): Promise<Trade> => {
      if (!supabase) throw new Error('Supabase client not initialized')
      const { data, error } = await supabase.functions.invoke('trades', {
        body: { action: 'trimTrade', trade_id, price, size }
      })
      if (error) throw error
      return data
    },

    exitTrade: async (trade_id: string, price: number): Promise<Trade> => {
      if (!supabase) throw new Error('Supabase client not initialized')
      const { data, error } = await supabase.functions.invoke('trades', {
        body: { action: 'exitTrade', trade_id, price }
      })
      if (error) throw error
      return data
    }
  },

  optionsStrategyTrades: {
    getAll: async (): Promise<DatabaseOptionsStrategyTrade[]> => {
      if (!supabase) return []
      const { data, error } = await supabase.functions.invoke('options-strategies', {
        body: { action: 'getAll' }
      })
      if (error) throw error
      return data
    },

    getByFilters: async (filters: StrategyFilters): Promise<DatabaseOptionsStrategyTrade[]> => {
      if (!supabase) return []
      const { data, error } = await supabase.functions.invoke('options-strategies', {
        body: { action: 'getStrategyTrades', filters }
      })
      if (error) throw error
      return data
    },

    create: async (input: {
      name: string
      underlying_symbol: string
      legs: string
      net_cost: number
      size: string
      trade_group?: string
      configuration_id?: number
    }): Promise<DatabaseOptionsStrategyTrade> => {
      if (!supabase) throw new Error('Supabase client not initialized')
      const { data, error } = await supabase.functions.invoke('options-strategies', {
        body: { action: 'createOptionsStrategy', input }
      })
      if (error) throw error
      return data
    },

    addToStrategy: async (strategy_id: number, net_cost: number, size: string): Promise<DatabaseOptionsStrategyTrade> => {
      if (!supabase) throw new Error('Supabase client not initialized')
      const { data, error } = await supabase.functions.invoke('options-strategies', {
        body: { action: 'addToStrategy', strategy_id, net_cost, size }
      })
      if (error) throw error
      return data
    },

    trimStrategy: async (strategy_id: number, net_cost: number, size: string): Promise<DatabaseOptionsStrategyTrade> => {
      if (!supabase) throw new Error('Supabase client not initialized')
      const { data, error } = await supabase.functions.invoke('options-strategies', {
        body: { action: 'trimStrategy', strategy_id, net_cost, size }
      })
      if (error) throw error
      return data
    },

    exitStrategy: async (strategy_id: number, net_cost: number): Promise<DatabaseOptionsStrategyTrade> => {
      if (!supabase) throw new Error('Supabase client not initialized')
      const { data, error } = await supabase.functions.invoke('options-strategies', {
        body: { action: 'exitStrategy', strategy_id, net_cost }
      })
      if (error) throw error
      return data
    }
  },

  portfolio: {
    getTrades: async (filters: PortfolioFilters) => {
      if (!supabase) return { regular_trades: [], strategy_trades: [] }
      const { data, error } = await supabase.functions.invoke('portfolio', {
        body: { action: 'getPortfolioTrades', filters }
      })
      if (error) throw error
      return data
    },

    getMonthlyPL: async (configName?: string) => {
      if (!supabase) return []
      const { data, error } = await supabase.functions.invoke('portfolio', {
        body: { action: 'getMonthlyPL', configName }
      })
      if (error) throw error
      return data
    },

    getStats: async (filters: PortfolioStatsFilters): Promise<PortfolioStats> => {
      if (!supabase) return {
        totalTrades: 0,
        winRate: 0,
        averageWin: 0,
        averageLoss: 0,
        profitFactor: 0,
        totalProfitLoss: 0,
        averageRiskRewardRatio: 0
      }
      const { data, error } = await supabase.functions.invoke('portfolio', {
        body: { action: 'getStats', filters }
      })
      if (error) throw error
      return data
    }
  },

  tradeConfigurations: {
    getAll: async (): Promise<TradeConfiguration[]> => {
      if (!supabase) return []
      const { data, error } = await supabase
        .from('trade_configurations')
        .select('*')
        .order('name', { ascending: true })
      if (error) throw error
      return data
    }
  }
}
