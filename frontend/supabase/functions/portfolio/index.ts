import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'


enum TransactionType {
  OPEN = 'OPEN',
  ADD = 'ADD',
  TRIM = 'TRIM',
  CLOSE = 'CLOSE'
}

interface PortfolioFilters {
  skip?: number
  limit?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  configName?: string
  weekFilter?: string
}

interface Transaction {
  transaction_id: string
  transaction_type: TransactionType
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
  strategy_id: number
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

interface MonthlyPLRecord {
  month: string;
  regular_trades_pl: number;
  strategy_trades_pl: number;
  total_pl: number;
  trade_configurations: {
    name: string;
  } | null;
}

interface MonthlyPLResponse {
  month: string;
  profit_loss: number;
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
    console.log('Initializing portfolio edge function')
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const payload = await req.json() as RequestPayload
    const { action, filters, configName } = payload
    console.log('Received request payload:', JSON.stringify(payload, null, 2))

    let data

    switch (action) {
      case 'getPortfolioTrades':
        console.log('Processing getPortfolioTrades action')
        const regularTrades = []
        const strategyTrades = []

        // Get regular trades
        console.log('Building regular trades query with filters:', JSON.stringify(filters, null, 2))
        let tradeQuery = supabase
          .from('trades')
          .select(`
            *,
            trade_configurations (*),
            transactions!inner (*)
          `)

        // Handle date filters
        if (filters?.weekFilter) {
          console.log('Applying week filter for regular trades:', filters.weekFilter)
          const day = new Date(filters.weekFilter)
          console.log('Initial day:', {
            raw: day,
            getDay: day.getDay(),
            getDate: day.getDate(),
            getMonth: day.getMonth(),
            getFullYear: day.getFullYear(),
            toISOString: day.toISOString()
          })

          // Set to midnight UTC
          day.setUTCHours(0, 0, 0, 0)
          
          // Calculate Monday (start of week)
          const monday = new Date(day)
          monday.setUTCDate(monday.getUTCDate() - monday.getUTCDay())
          
          // Calculate Friday (end of week)
          const friday = new Date(monday)
          friday.setUTCDate(friday.getUTCDate() + 4)
          friday.setUTCHours(23, 59, 59, 999)

          console.log('Date range:', { 
            input: filters.weekFilter,
            day: day.toISOString(),
            monday: monday.toISOString(), 
            friday: friday.toISOString()
          })
          
          // Filter trades that have TRIM or CLOSE transactions within the date range
          tradeQuery = tradeQuery
            .in('transactions.transaction_type', [TransactionType.TRIM, TransactionType.CLOSE])
            .gte('transactions.created_at', monday.toISOString())
            .lte('transactions.created_at', friday.toISOString())

          console.log('Query parameters:', {
            transaction_types: [TransactionType.TRIM, TransactionType.CLOSE],
            created_at_gte: monday.toISOString(),
            created_at_lte: friday.toISOString()
          })
        }

        console.log('Executing regular trades query')
        const { data: trades, error: tradeError } = await tradeQuery

        if (tradeError) {
          console.error('Error fetching regular trades:', tradeError)
          throw tradeError
        }
        console.log(`Found ${trades?.length ?? 0} regular trades`)
        if (trades && trades.length > 0) {
          console.log('Sample trade dates:', trades.map((t: Trade) => ({
            trade_id: t.trade_id,
            closed_at: t.closed_at,
            status: t.status
          })))
        }

        // Process regular trades
        console.log('Processing regular trades')
        for (const trade of trades as Trade[]) {
          if (!trade.transactions) {
            console.log(`Skipping trade ${trade.trade_id} - no transactions found`)
            continue
          }

          console.log(`Processing trade ${trade.trade_id}:`, {
            symbol: trade.symbol,
            status: trade.status,
            trade_type: trade.trade_type
          })

          const closeTransactions = trade.transactions.filter((t: Transaction) =>
            t.transaction_type === TransactionType.CLOSE || t.transaction_type === TransactionType.TRIM
          )
          const openTransactions = trade.transactions.filter((t: Transaction) =>
            t.transaction_type === TransactionType.OPEN || t.transaction_type === TransactionType.ADD
          )

          console.log('Transaction counts:', {
            close: closeTransactions.length,
            open: openTransactions.length
          })

          let closedSize = 0
          for (const transaction of closeTransactions) {
            closedSize += parseFloat(transaction.size)
          }

          let totalRealizedPL = 0
          if (trade.average_exit_price !== null && trade.average_exit_price !== undefined) {
            totalRealizedPL = (trade.average_exit_price - trade.average_price) * closedSize
          } else {
            totalRealizedPL = openTransactions.reduce((sum: number, t: Transaction) => 
              sum + ((parseFloat(t.amount.toString()) - trade.average_price) * parseFloat(t.size)), 0
            ) * -1
          }

          // Apply contract multiplier
          if (trade.symbol === 'ES') {
            console.log('Applying ES contract multiplier (50x)')
            totalRealizedPL *= 50
          } else {
            console.log('Applying standard contract multiplier (100x)')
            totalRealizedPL *= 100
          }
          let difference = 0
          if (trade.trade_type === 'BTO') {
            difference = (trade.average_exit_price || 0) - trade.average_price
          } else if (trade.trade_type === 'STO') {
            difference = trade.average_price - (trade.average_exit_price || 0)
          }
          const pctChange = difference / trade.average_price * 100

          // Reverse P/L for short trades
          if (trade.trade_type === 'STO' || trade.trade_type === 'Sell to Open') {
            console.log('Reversing P/L for short trade')
            totalRealizedPL = -totalRealizedPL
          }

          console.log('Final trade calculations:', {
            realized_pl: totalRealizedPL,
            pct_change: pctChange,
            closed_size: closedSize
          })

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
        console.log('Building strategy trades query with filters:', JSON.stringify(filters, null, 2))
        let strategyQuery = supabase
          .from('options_strategy_trades')
          .select(`
            *,
            trade_configurations (*),
            options_strategy_transactions!inner (*)
          `)

        // Handle date filters for strategy trades
        if (filters?.weekFilter) {
          console.log('Applying week filter for strategy trades:', filters.weekFilter)
          const day = new Date(filters.weekFilter)
          // Set to midnight UTC
          day.setUTCHours(0, 0, 0, 0)
          
          // Calculate Monday (start of week)
          const monday = new Date(day)
          monday.setUTCDate(monday.getUTCDate() - monday.getUTCDay())
          
          // Calculate Friday (end of week)
          const friday = new Date(monday)
          friday.setUTCDate(friday.getUTCDate() + 4)
          friday.setUTCHours(23, 59, 59, 999)

          console.log('Date range:', { 
            input: filters.weekFilter,
            day: day.toISOString(),
            monday: monday.toISOString(), 
            friday: friday.toISOString() 
          })
          
          // Filter strategies that have TRIM or CLOSE transactions within the date range
          strategyQuery = strategyQuery
            .in('options_strategy_transactions.transaction_type', [TransactionType.TRIM, TransactionType.CLOSE])
            .gte('options_strategy_transactions.created_at', monday.toISOString())
            .lte('options_strategy_transactions.created_at', friday.toISOString())
        }

        console.log('Executing strategy trades query')
        const { data: strategies, error: strategyError } = await strategyQuery

        if (strategyError) {
          console.error('Error fetching strategy trades:', strategyError)
          throw strategyError
        }
        console.log(`Found ${strategies?.length ?? 0} strategy trades`)

        // Process strategy trades
        console.log('Processing strategy trades')
        for (const strategy of strategies as Strategy[]) {
          if (!strategy.options_strategy_transactions) {
            console.log(`Skipping strategy ${strategy.strategy_id} - no transactions found`)
            continue
          }

          console.log(`Processing strategy ${strategy.strategy_id}:`, {
            name: strategy.name,
            symbol: strategy.underlying_symbol,
            status: strategy.status
          })

          // query the open transactions for the strategy
          const { data: openTransactions } = await supabase
            .from('options_strategy_transactions')
            .select('*')
            .eq('strategy_id', strategy.strategy_id)
            .in('transaction_type', [TransactionType.OPEN, TransactionType.ADD])

          console.log('Open transactions:', openTransactions)

          const [realizedPL, avgExitPrice] = calculateStrategyPL(strategy, openTransactions)
          const pctChange = (avgExitPrice - strategy.average_net_cost) / strategy.average_net_cost * 100

          console.log('Strategy calculations:', {
            realized_pl: realizedPL,
            avg_exit_price: avgExitPrice,
            avg_entry_price: strategy.average_net_cost,
            pct_change: pctChange
          })

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
          console.log('Filtering trades by configuration:', filters.configName)
          data = {
            regular_trades: regularTrades.filter(t => {
              const matches = t.trade.trade_configurations?.name === filters.configName || filters.configName === 'all'
              console.log(`Regular trade ${t.trade.trade_id} config match:`, {
                trade_config: t.trade.trade_configurations?.name,
                filter_config: filters.configName,
                matches
              })
              return matches
            }),
            strategy_trades: strategyTrades.filter(t => {
              const matches = t.trade.trade_configurations?.name === filters.configName || filters.configName === 'all'
              console.log(`Strategy trade ${t.trade.strategy_id} config match:`, {
                trade_config: t.trade.trade_configurations?.name,
                filter_config: filters.configName,
                matches 
              })
              return matches
            })
          }
        } else {
          console.log('No configuration filter applied')
          data = {
            regular_trades: regularTrades,
            strategy_trades: strategyTrades
          }
        }

        console.log('Final portfolio data:', {
          regular_trades: data.regular_trades.length,
          strategy_trades: data.strategy_trades.length
        })
        break

      case 'getMonthlyPL':
        console.log('Processing getMonthlyPL action with configName:', configName)
        
        let query = supabase
          .from('monthly_pl')
          .select(`
            month,
            regular_trades_pl,
            strategy_trades_pl,
            total_pl,
            trade_configurations:configuration_id (
              name
            )
          `)
          .order('month', { ascending: true })

        if (configName && configName !== 'all') {
          console.log('Filtering by configuration:', configName)
          const { data: configData, error: configError } = await supabase
            .from('trade_configurations')
            .select('id')
            .eq('name', configName)
            .single()

          if (configError) {
            console.error('Error fetching configuration:', configError)
            throw configError
          }

          if (configData) {
            console.log('Found configuration ID:', configData.id)
            query = query.eq('configuration_id', configData.id)
          }
        }

        const { data: monthlyData, error: monthlyError } = await query
        if (monthlyError) {
          console.error('Error fetching monthly P/L:', monthlyError)
          throw monthlyError
        }
        console.log(`Found ${monthlyData?.length ?? 0} monthly P/L records`)
        
        // Log raw data to check for invalid dates
        console.log('Raw monthly P/L data:', monthlyData.map((record: MonthlyPLRecord) => ({
          month: record.month,
          total_pl: record.total_pl
        })))

        // Transform data into expected format
        data = monthlyData.map((record: MonthlyPLRecord) => {
          // The month field comes from Postgres as a DATE type (YYYY-MM-DD)
          // We need to parse it and format it as "Month Year"
          const date = new Date(record.month);
          
          if (isNaN(date.getTime())) {
            console.error('Invalid date encountered:', record.month);
            return {
              month: 'Invalid Date',
              profit_loss: record.total_pl
            };
          }

          const formattedMonth = date.toLocaleString('en-US', {
            month: 'long',
            year: 'numeric',
            timeZone: 'UTC'
          });

          return {
            month: formattedMonth,
            profit_loss: record.total_pl
          };
        }).sort((a: MonthlyPLResponse, b: MonthlyPLResponse) => {
          // Sort by date, putting invalid dates at the end
          if (a.month === 'Invalid Date') return 1;
          if (b.month === 'Invalid Date') return -1;

          // Parse the formatted dates back for comparison
          const [aMonth, aYear] = a.month.split(' ');
          const [bMonth, bYear] = b.month.split(' ');
          
          // Compare years first
          const yearDiff = parseInt(aYear) - parseInt(bYear);
          if (yearDiff !== 0) return yearDiff;
          
          // If years are equal, compare months
          const months = ['January', 'February', 'March', 'April', 'May', 'June', 
                         'July', 'August', 'September', 'October', 'November', 'December'];
          return months.indexOf(aMonth) - months.indexOf(bMonth);
        });

        console.log('Transformed monthly P/L data:', data)
        break

      default:
        console.error('Unknown action:', action)
        throw new Error(`Unknown action: ${action}`)
    }

    return new Response(
      JSON.stringify(data),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    console.error('Portfolio edge function error:', error)
    const message = error instanceof Error ? error.message : 'An unknown error occurred'
    return new Response(
      JSON.stringify({ error: message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
    )
  }
})

// Helper functions
function calculateStrategyPL(strategy: Strategy, openTransactions: Transaction[]): [number, number] {
  console.log('Calculating strategy P/L for strategy:', strategy)
  const transactions = strategy.options_strategy_transactions

  console.log('Transactions:', transactions)

  const closeTransactions = transactions.filter((t: Transaction) => 
    t.transaction_type === TransactionType.CLOSE || t.transaction_type === TransactionType.TRIM
  )

  console.log('Open transactions:', openTransactions)

  const totalCost = openTransactions.reduce((sum: number, t: Transaction) => {
    return sum + ((t.net_cost || 0) * parseFloat(t.size || '0'));
  }, 0);
  //const totalSize = openTransactions.reduce((sum: number, t: Transaction) => 
  //  sum + parseFloat(t.size), 0
  //)
  //const avgEntryCost = totalCost / totalSize

  const totalExitValue = closeTransactions.reduce((sum: number, t: Transaction) => 
    sum + ((t.net_cost || 0) * parseFloat(t.size)), 0
  )
  const totalExitSize = closeTransactions.reduce((sum: number, t: Transaction) => 
    sum + parseFloat(t.size), 0
  )
  const avgExitCost = totalExitValue / totalExitSize

  console.log('Strategy P/L calculations:', {
    totalCost,
    totalExitValue,
    avgExitCost,
  })

  //const realizedPL = (avgExitCost - avgEntryCost) * parseFloat(strategy.size) * 100
  const realizedPL = totalExitValue - totalCost
  return [realizedPL, avgExitCost]
}

function createTradeOneliner(trade: Trade): string {
  return [
    trade.expiration_date ? new Date(trade.expiration_date).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: '2-digit' }) : null,
    trade.symbol,
    trade.is_contract && trade.strike ? `${Number.isInteger(trade.strike) ? trade.strike : trade.strike.toFixed(2)}${trade.option_type || ''}` : null,
    trade.size,
    `@${trade.average_price.toFixed(2)}`
  ].filter(Boolean).join(' ')
}

function createStrategyOneliner(strategy: Strategy): string {
  return `${strategy.name} ${strategy.underlying_symbol} ${strategy.size} @${strategy.net_cost}`
} 