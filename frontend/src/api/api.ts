import { createClient } from '@supabase/supabase-js'
import { Database } from '../../lib/database.types'

const supabase = createClient<Database>(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

type Trade = Database['public']['Tables']['trades']['Row'] & {
  trade_configurations: Database['public']['Tables']['trade_configurations']['Row'] | null
}

type OptionsStrategyTrade = Database['public']['Tables']['options_strategy_trades']['Row'] & {
  trade_configurations: Database['public']['Tables']['trade_configurations']['Row'] | null
}

type Transaction = Database['public']['Tables']['transactions']['Row']
type OptionsStrategyTransaction = Database['public']['Tables']['options_strategy_transactions']['Row']
type TradeConfiguration = Database['public']['Tables']['trade_configurations']['Row']

interface TradeFilters {
  skip?: number
  limit?: number
  status?: string
  symbol?: string
  tradeType?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  configName?: string
  weekFilter?: string
  monthFilter?: string
  yearFilter?: string
  optionType?: string
  maxEntryPrice?: number
  minEntryPrice?: number
}

interface StrategyFilters {
  skip?: number
  limit?: number
  status?: string
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

export const api = {
  trades: {
    getAll: async (): Promise<Trade[]> => {
      const { data, error } = await supabase.functions.invoke('trades', {
        body: { action: 'getAll' }
      })
      if (error) throw error
      return data
    },

    getByFilters: async (filters: TradeFilters): Promise<Trade[]> => {
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
      const { data, error } = await supabase.functions.invoke('trades', {
        body: { action: 'createTrade', input }
      })
      if (error) throw error
      return data
    },

    addToTrade: async (trade_id: string, price: number, size: string): Promise<Trade> => {
      const { data, error } = await supabase.functions.invoke('trades', {
        body: { action: 'addToTrade', trade_id, price, size }
      })
      if (error) throw error
      return data
    },

    trimTrade: async (trade_id: string, price: number, size: string): Promise<Trade> => {
      const { data, error } = await supabase.functions.invoke('trades', {
        body: { action: 'trimTrade', trade_id, price, size }
      })
      if (error) throw error
      return data
    },

    exitTrade: async (trade_id: string, price: number): Promise<Trade> => {
      const { data, error } = await supabase.functions.invoke('trades', {
        body: { action: 'exitTrade', trade_id, price }
      })
      if (error) throw error
      return data
    }
  },

  optionsStrategyTrades: {
    getAll: async (): Promise<OptionsStrategyTrade[]> => {
      const { data, error } = await supabase.functions.invoke('options-strategies', {
        body: { action: 'getAll' }
      })
      if (error) throw error
      return data
    },

    getByFilters: async (filters: StrategyFilters): Promise<OptionsStrategyTrade[]> => {
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
    }): Promise<OptionsStrategyTrade> => {
      const { data, error } = await supabase.functions.invoke('options-strategies', {
        body: { action: 'createOptionsStrategy', input }
      })
      if (error) throw error
      return data
    },

    addToStrategy: async (strategy_id: number, net_cost: number, size: string): Promise<OptionsStrategyTrade> => {
      const { data, error } = await supabase.functions.invoke('options-strategies', {
        body: { action: 'addToStrategy', strategy_id, net_cost, size }
      })
      if (error) throw error
      return data
    },

    trimStrategy: async (strategy_id: number, net_cost: number, size: string): Promise<OptionsStrategyTrade> => {
      const { data, error } = await supabase.functions.invoke('options-strategies', {
        body: { action: 'trimStrategy', strategy_id, net_cost, size }
      })
      if (error) throw error
      return data
    },

    exitStrategy: async (strategy_id: number, net_cost: number): Promise<OptionsStrategyTrade> => {
      const { data, error } = await supabase.functions.invoke('options-strategies', {
        body: { action: 'exitStrategy', strategy_id, net_cost }
      })
      if (error) throw error
      return data
    }
  },

  portfolio: {
    getTrades: async (filters: PortfolioFilters) => {
      const { data, error } = await supabase.functions.invoke('portfolio', {
        body: { action: 'getPortfolioTrades', filters }
      })
      if (error) throw error
      return data
    },

    getMonthlyPL: async (configName?: string) => {
      const { data, error } = await supabase.functions.invoke('portfolio', {
        body: { action: 'getMonthlyPL', configName }
      })
      if (error) throw error
      return data
    }
  },

  tradeConfigurations: {
    getAll: async (): Promise<TradeConfiguration[]> => {
      const { data, error } = await supabase
        .from('trade_configurations')
        .select('*')
        .order('name', { ascending: true })
      if (error) throw error
      return data
    }
  }
}
