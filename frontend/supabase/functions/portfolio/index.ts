import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface PortfolioFilters {
  skip?: number
  limit?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  configName?: string
  weekFilter?: string
}

interface Transaction {
  transaction_type: 'OPEN' | 'ADD' | 'TRIM' | 'CLOSE'
  amount: number
  size: string
  net_cost?: number
}

interface Trade {
  trade_id: string
  symbol: string
  trade_type: string
  status: string
  entry_price: number
  average_price: number
  size: string
  current_size: string
  created_at: string
  closed_at?: string
  is_contract: boolean
  strike?: number
  option_type?: string
  expiration_date?: string
  average_exit_price?: number
  profit_loss?: number
  trade_configurations?: {
    name: string
  }
  transactions: Transaction[]
}

interface Strategy {
  id: number
  name: string
  underlying_symbol: string
  status: string
  net_cost: number
  average_net_cost: number
  size: string
  current_size: string
  created_at: string
  closed_at?: string
  profit_loss?: number
  trade_configurations?: {
    name: string
  }
  options_strategy_transactions: Transaction[]
}

interface RequestPayload {
  action: string
  filters?: PortfolioFilters
  configName?: string
}

serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const payload = await req.json() as RequestPayload
    const { action, filters, configName } = payload

    let data

    switch (action) {
      case 'getPortfolioTrades':
        const regularTrades = []
        const strategyTrades = []

        // Get regular trades
        let tradeQuery = supabase
          .from('trades')
          .select(`
            *,
            trade_configurations (*),
            transactions (*)
          `)
          .eq('status', 'CLOSED')

        // Handle date filters
        if (filters?.weekFilter) {
          const day = new Date(filters.weekFilter)
          const monday = new Date(day.setDate(day.getDate() - day.getDay()))
          const friday = new Date(day.setDate(day.getDate() + 4))
          tradeQuery = tradeQuery
            .gte('closed_at', monday.toISOString())
            .lte('closed_at', friday.toISOString())
        }

        const { data: trades, error: tradeError } = await tradeQuery

        if (tradeError) throw tradeError

        // Process regular trades
        for (const trade of trades as Trade[]) {
          if (!trade.transactions) continue

          const closeTransactions = trade.transactions.filter((t: Transaction) =>
            t.transaction_type === 'CLOSE' || t.transaction_type === 'TRIM'
          )
          const openTransactions = trade.transactions.filter((t: Transaction) =>
            t.transaction_type === 'OPEN' || t.transaction_type === 'ADD'
          )

          let closedSize = 0
          for (const transaction of closeTransactions) {
            closedSize += parseFloat(transaction.size)
          }

          let totalRealizedPL = 0
          if (trade.average_exit_price) {
            totalRealizedPL = (trade.average_exit_price - trade.average_price) * closedSize
          } else {
            totalRealizedPL = openTransactions.reduce((sum: number, t: Transaction) => 
              sum + ((parseFloat(t.amount.toString()) - trade.average_price) * parseFloat(t.size)), 0
            ) * -1
          }

          // Apply contract multiplier
          if (trade.symbol === 'ES') {
            totalRealizedPL *= 50
          } else {
            totalRealizedPL *= 100
          }

          const pctChange = ((trade.average_exit_price || 0) - trade.average_price) / trade.average_price * 100

          // Reverse P/L for short trades
          if (trade.trade_type === 'STO' || trade.trade_type === 'Sell to Open') {
            totalRealizedPL = -totalRealizedPL
          }

          regularTrades.push({
            trade,
            oneliner: createTradeOneliner(trade),
            realized_pl: totalRealizedPL,
            realized_size: closedSize,
            avg_entry_price: trade.average_price,
            avg_exit_price: trade.average_exit_price || 0,
            pct_change: pctChange,
            trade_type: 'regular'
          })
        }

        // Get strategy trades
        let strategyQuery = supabase
          .from('options_strategy_trades')
          .select(`
            *,
            trade_configurations (*),
            options_strategy_transactions (*)
          `)
          .eq('status', 'CLOSED')

        if (filters?.weekFilter) {
          const day = new Date(filters.weekFilter)
          const monday = new Date(day.setDate(day.getDate() - day.getDay()))
          const friday = new Date(day.setDate(day.getDate() + 4))
          strategyQuery = strategyQuery
            .gte('closed_at', monday.toISOString())
            .lte('closed_at', friday.toISOString())
        }

        const { data: strategies, error: strategyError } = await strategyQuery

        if (strategyError) throw strategyError

        // Process strategy trades
        for (const strategy of strategies as Strategy[]) {
          if (!strategy.options_strategy_transactions) continue

          const [realizedPL, avgExitPrice] = calculateStrategyPL(strategy)
          const pctChange = (avgExitPrice - strategy.average_net_cost) / strategy.average_net_cost * 100

          strategyTrades.push({
            trade: strategy,
            oneliner: createStrategyOneliner(strategy),
            realized_pl: realizedPL,
            realized_size: parseFloat(strategy.size),
            avg_entry_price: strategy.average_net_cost,
            avg_exit_price: avgExitPrice,
            pct_change: pctChange,
            trade_type: 'strategy'
          })
        }

        // Filter by configuration name
        if (filters?.configName) {
          data = {
            regular_trades: regularTrades.filter(t => 
              t.trade.trade_configurations?.name === filters.configName || filters.configName === 'all'
            ),
            strategy_trades: strategyTrades.filter(t => 
              t.trade.trade_configurations?.name === filters.configName || filters.configName === 'all'
            )
          }
        } else {
          data = {
            regular_trades: regularTrades,
            strategy_trades: strategyTrades
          }
        }
        break

      case 'getMonthlyPL':
        // Get trades
        const { data: monthlyTrades, error: monthlyTradeError } = await supabase
          .from('trades')
          .select(`
            profit_loss,
            created_at,
            trade_configurations (name)
          `)
          .order('created_at', { ascending: true })

        if (monthlyTradeError) throw monthlyTradeError

        // Get strategy trades
        const { data: monthlyStrategies, error: monthlyStrategyError } = await supabase
          .from('options_strategy_trades')
          .select(`
            profit_loss,
            created_at,
            trade_configurations (name)
          `)
          .order('created_at', { ascending: true })

        if (monthlyStrategyError) throw monthlyStrategyError

        // Filter trades by configuration
        const filteredTrades = monthlyTrades?.filter((trade: Trade) => 
          !configName || trade.trade_configurations?.name === configName || configName === 'all'
        ) || []

        const filteredStrategies = monthlyStrategies?.filter((strategy: Strategy) => 
          !configName || strategy.trade_configurations?.name === configName || configName === 'all'
        ) || []

        // Combine and group by month
        const monthlyPL: { [key: string]: number } = {}

        // Process trades
        filteredTrades.forEach(trade => {
          if (!trade.profit_loss) return
          const month = new Date(trade.created_at).toLocaleString('default', {
            month: 'long',
            year: 'numeric'
          })
          monthlyPL[month] = (monthlyPL[month] || 0) + trade.profit_loss
        })

        // Process strategies
        filteredStrategies.forEach(strategy => {
          if (!strategy.profit_loss) return
          const month = new Date(strategy.created_at).toLocaleString('default', {
            month: 'long',
            year: 'numeric'
          })
          monthlyPL[month] = (monthlyPL[month] || 0) + strategy.profit_loss
        })

        // Convert to array and sort
        data = Object.entries(monthlyPL)
          .map(([month, profit_loss]) => ({ month, profit_loss }))
          .sort((a, b) => new Date(b.month).getTime() - new Date(a.month).getTime())
        break

      default:
        throw new Error(`Unknown action: ${action}`)
    }

    return new Response(
      JSON.stringify(data),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    const message = error instanceof Error ? error.message : 'An unknown error occurred'
    return new Response(
      JSON.stringify({ error: message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
    )
  }
})

// Helper functions
function calculateStrategyPL(strategy: Strategy): [number, number] {
  const transactions = strategy.options_strategy_transactions
  const openTransactions = transactions.filter((t: Transaction) => 
    t.transaction_type === 'OPEN' || t.transaction_type === 'ADD'
  )
  const closeTransactions = transactions.filter((t: Transaction) => 
    t.transaction_type === 'CLOSE' || t.transaction_type === 'TRIM'
  )

  const totalCost = openTransactions.reduce((sum: number, t: Transaction) => 
    sum + ((t.net_cost || 0) * parseFloat(t.size)), 0
  )
  const totalSize = openTransactions.reduce((sum: number, t: Transaction) => 
    sum + parseFloat(t.size), 0
  )
  const avgEntryCost = totalCost / totalSize

  const totalExitValue = closeTransactions.reduce((sum: number, t: Transaction) => 
    sum + ((t.net_cost || 0) * parseFloat(t.size)), 0
  )
  const totalExitSize = closeTransactions.reduce((sum: number, t: Transaction) => 
    sum + parseFloat(t.size), 0
  )
  const avgExitCost = totalExitValue / totalExitSize

  const realizedPL = (avgExitCost - avgEntryCost) * parseFloat(strategy.size) * 100

  return [realizedPL, avgExitCost]
}

function createTradeOneliner(trade: Trade): string {
  const parts = []
  parts.push(trade.trade_type)
  parts.push(trade.symbol)
  
  if (trade.is_contract) {
    if (trade.strike) parts.push(trade.strike.toString())
    if (trade.option_type) parts.push(trade.option_type)
    if (trade.expiration_date) {
      const date = new Date(trade.expiration_date)
      parts.push(date.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: '2-digit' }))
    }
  }

  parts.push(trade.size)
  parts.push(`@${trade.entry_price}`)

  return parts.join(' ')
}

function createStrategyOneliner(strategy: Strategy): string {
  return `${strategy.name} ${strategy.underlying_symbol} ${strategy.size} @${strategy.net_cost}`
} 