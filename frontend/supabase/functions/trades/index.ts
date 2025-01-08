import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface Transaction {
  transaction_type: 'OPEN' | 'ADD' | 'TRIM' | 'CLOSE'
  amount: number
  size: string
  net_cost?: number
}

interface ExitTrade {
  transactions: Transaction[]
  current_size: string
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

interface TradeFilters {
  configName: string
  status?: 'ALL' | 'OPEN' | 'CLOSED'
  skip?: number
  limit?: number
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
  showAllTrades?: boolean
}

interface TradeInput {
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
}

interface RequestPayload {
  action: string
  filters?: TradeFilters
  input?: TradeInput
  trade_id?: string
  price?: number
  size?: string
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
    const { action, filters, input, trade_id, price, size } = payload

    console.log('Received request payload:', JSON.stringify(payload, null, 2))

    let data

    switch (action) {
      case 'getAll':
        console.log('Fetching all trades')
        const { data: allTrades, error: allError } = await supabase
          .from('trades')
          .select(`
            *,
            trade_configurations (*)
          `)
          .order('created_at', { ascending: false })
        if (allError) throw allError
        data = allTrades
        break

      case 'getTrades':
        console.log('Fetching trades with filters:', JSON.stringify(filters, null, 2))
        let query = supabase
          .from('trades')
          .select(`
            *,
            trade_configurations (
              id,
              name
            )
          `)

        if (filters) {
          if (filters.status && filters.status !== 'ALL') {
            console.log('Applying status filter:', filters.status.toLowerCase())
            query = query.eq('status', filters.status.toLowerCase())
          }
          
          if (filters.configName && filters.configName !== 'all') {
            console.log('Applying configuration filter:', filters.configName)
            const { data: configData, error: configError } = await supabase
              .from('trade_configurations')
              .select('id')
              .eq('name', filters.configName)
              .single()

            if (configError) {
              console.error('Error fetching configuration:', configError)
              throw configError
            }

            if (configData) {
              console.log('Found configuration ID:', configData.id)
              query = query.eq('configuration_id', configData.id)
            } else {
              console.warn('No configuration found for name:', filters.configName)
              return []
            }
          }

          if (filters.symbol) {
            console.log('Applying symbol filter:', filters.symbol)
            query = query.eq('symbol', filters.symbol)
          }

          if (filters.tradeType) {
            console.log('Applying trade type filter:', filters.tradeType)
            query = query.eq('trade_type', filters.tradeType)
          }

          if (filters.optionType === 'options') {
            console.log('Filtering for options trades')
            query = query.eq('is_contract', true)
          } else if (filters.optionType === 'common') {
            console.log('Filtering for common stock trades')
            query = query.eq('is_contract', false)
          }

          if (filters.maxEntryPrice) {
            console.log('Applying max entry price filter:', filters.maxEntryPrice)
            query = query.lte('average_price', filters.maxEntryPrice)
          }

          if (filters.minEntryPrice) {
            console.log('Applying min entry price filter:', filters.minEntryPrice)
            query = query.gte('average_price', filters.minEntryPrice)
          }

          // Handle date filters
          if (filters.weekFilter && filters.status?.toLowerCase() === 'closed') {
            console.log('Applying week filter for closed trades:', filters.weekFilter)
            const day = new Date(filters.weekFilter)
            const monday = new Date(day.setDate(day.getDate() - day.getDay()))
            const friday = new Date(day.setDate(day.getDate() + 4))
            query = query
              .gte('closed_at', monday.toISOString())
              .lte('closed_at', friday.toISOString())
          }

          // Handle sorting
          if (filters.sortBy) {
            console.log('Applying sort:', filters.sortBy, filters.sortOrder)
            query = query.order(filters.sortBy, { ascending: filters.sortOrder === 'asc' })
          } else {
            query = query.order('created_at', { ascending: false })
          }

          // Handle pagination
          if (filters.skip) {
            console.log('Applying pagination:', filters.skip, filters.limit)
            query = query.range(filters.skip, (filters.skip + (filters.limit || 100)) - 1)
          }
        }

        const { data: filteredTrades, error: filterError } = await query
        if (filterError) {
          console.error('Error fetching trades:', filterError)
          throw filterError
        }
        console.log(`Found ${filteredTrades?.length ?? 0} trades`)
        data = filteredTrades
        break

      case 'createTrade':
        if (!input) throw new Error('Input is required')
        const { data: trade, error: tradeError } = await supabase
          .from('trades')
          .insert({
            trade_id: generateTradeId(),
            symbol: input.symbol,
            trade_type: input.trade_type,
            status: 'open',
            entry_price: input.entry_price,
            average_price: input.entry_price,
            size: input.size,
            current_size: input.size,
            created_at: new Date().toISOString(),
            configuration_id: input.configuration_id,
            is_contract: input.is_contract || false,
            is_day_trade: input.is_day_trade || false,
            strike: input.strike,
            expiration_date: input.expiration_date,
            option_type: input.option_type
          })
          .select()
          .single()

        if (tradeError) throw tradeError

        // Create initial transaction
        const { error: transactionError } = await supabase
          .from('transactions')
          .insert({
            trade_id: trade.trade_id,
            transaction_type: 'OPEN',
            amount: input.entry_price,
            size: input.size,
            created_at: new Date().toISOString()
          })

        if (transactionError) throw transactionError
        data = trade
        break

      case 'addToTrade':
        if (!trade_id || !price || !size) throw new Error('trade_id, price, and size are required')
        // Get current trade
        const { data: currentTrade, error: currentTradeError } = await supabase
          .from('trades')
          .select('*')
          .eq('trade_id', trade_id)
          .single()

        if (currentTradeError) throw currentTradeError

        // Calculate new average price and size
        const currentSize = parseFloat(currentTrade.current_size)
        const addSize = parseFloat(size)
        const newSize = currentSize + addSize
        const newAveragePrice = ((currentSize * currentTrade.average_price) + (addSize * price)) / newSize

        // Create transaction
        const { error: addTransactionError } = await supabase
          .from('transactions')
          .insert({
            trade_id,
            transaction_type: 'ADD',
            amount: price,
            size,
            created_at: new Date().toISOString()
          })

        if (addTransactionError) throw addTransactionError

        // Update trade
        const { data: updatedTrade, error: updateError } = await supabase
          .from('trades')
          .update({
            average_price: newAveragePrice,
            current_size: newSize.toString()
          })
          .eq('trade_id', trade_id)
          .select()
          .single()

        if (updateError) throw updateError
        data = updatedTrade
        break

      case 'trimTrade':
        if (!trade_id || !price || !size) throw new Error('trade_id, price, and size are required')
        // Get current trade
        const { data: trimTrade, error: trimTradeError } = await supabase
          .from('trades')
          .select('*')
          .eq('trade_id', trade_id)
          .single()

        if (trimTradeError) throw trimTradeError

        const trimCurrentSize = parseFloat(trimTrade.current_size)
        const trimSize = parseFloat(size)

        if (trimSize > trimCurrentSize) {
          throw new Error('Trim size is greater than current trade size')
        }

        // Create transaction
        const { error: trimTransactionError } = await supabase
          .from('transactions')
          .insert({
            trade_id,
            transaction_type: 'TRIM',
            amount: price,
            size,
            created_at: new Date().toISOString()
          })

        if (trimTransactionError) throw trimTransactionError

        // Update trade
        const { data: trimmedTrade, error: trimUpdateError } = await supabase
          .from('trades')
          .update({
            current_size: (trimCurrentSize - trimSize).toString()
          })
          .eq('trade_id', trade_id)
          .select()
          .single()

        if (trimUpdateError) throw trimUpdateError
        data = trimmedTrade
        break

      case 'exitTrade':
        if (!trade_id || !price) throw new Error('trade_id and price are required')
        // Get current trade and all its transactions
        const { data: exitTradeData, error: exitTradeError } = await supabase
          .from('trades')
          .select(`
            *,
            transactions (*)
          `)
          .eq('trade_id', trade_id)
          .single()

        if (exitTradeError) throw exitTradeError

        // Create exit transaction
        const { error: exitTransactionError } = await supabase
          .from('transactions')
          .insert({
            trade_id,
            transaction_type: 'CLOSE',
            amount: price,
            size: exitTradeData.current_size,
            created_at: new Date().toISOString()
          })

        if (exitTransactionError) throw exitTransactionError

        // Calculate profit/loss
        const exitTradeWithTransactions = exitTradeData as ExitTrade
        const openTransactions = exitTradeWithTransactions.transactions.filter((t: Transaction) => 
          t.transaction_type === 'OPEN' || t.transaction_type === 'ADD'
        )
        const trimTransactions = exitTradeWithTransactions.transactions.filter((t: Transaction) => 
          t.transaction_type === 'TRIM'
        )

        const totalCost = openTransactions.reduce((sum: number, t: Transaction) => 
          sum + (parseFloat(t.amount.toString()) * parseFloat(t.size)), 0
        )
        const totalOpenSize = openTransactions.reduce((sum: number, t: Transaction) => 
          sum + parseFloat(t.size), 0
        )
        const averageCost = totalCost / totalOpenSize

        const trimProfitLoss = trimTransactions.reduce((sum: number, t: Transaction) => 
          sum + ((parseFloat(t.amount.toString()) - averageCost) * parseFloat(t.size)), 0
        )
        const exitProfitLoss = (price - averageCost) * parseFloat(exitTradeData.current_size)
        const totalProfitLoss = trimProfitLoss + exitProfitLoss

        // Calculate average exit price
        const totalExitValue = trimTransactions.reduce((sum: number, t: Transaction) => 
          sum + (parseFloat(t.amount.toString()) * parseFloat(t.size)), 0
        ) + (price * parseFloat(exitTradeData.current_size))
        const totalExitSize = trimTransactions.reduce((sum: number, t: Transaction) => 
          sum + parseFloat(t.size), 0
        ) + parseFloat(exitTradeData.current_size)
        const averageExitPrice = totalExitValue / totalExitSize

        // Update trade
        const { data: closedTrade, error: closeUpdateError } = await supabase
          .from('trades')
          .update({
            status: 'closed',
            exit_price: price,
            average_exit_price: averageExitPrice,
            profit_loss: totalProfitLoss,
            win_loss: totalProfitLoss > 0 ? 'WIN' : totalProfitLoss < 0 ? 'LOSS' : 'BREAKEVEN',
            closed_at: new Date().toISOString()
          })
          .eq('trade_id', trade_id)
          .select()
          .single()

        if (closeUpdateError) throw closeUpdateError
        data = closedTrade
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

// Helper function to generate a trade ID
function generateTradeId(): string {
  return Math.random().toString(36).substring(2, 10)
} 