import { serve } from 'https://deno.land/std@0.177.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

enum TransactionType {
  OPEN = 'OPEN',
  ADD = 'ADD',
  TRIM = 'TRIM',
  CLOSE = 'CLOSE'
}

enum TradeStatus {
  OPEN = 'OPEN',
  CLOSED = 'CLOSED'
}

interface Transaction {
  transaction_type: TransactionType
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
  status: TradeStatus
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

interface TradeData {
  symbol: string;
  trade_type: string;
  entry_price: number;
  size: string;
  configuration_id?: number;
  is_contract?: boolean;
  strike?: number;
  expiration_date?: string;
  option_type?: string;
}

interface RequestPayload {
  action: string
  filters?: TradeFilters
  trade_id?: string
  price?: number
  size?: string
  input?: TradeInput
}

serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const payload = await req.json() as RequestPayload
    const { action, filters, input, trade_id, price, size } = payload

    let data

    switch (action) {
      case 'getAll':
        const { data: allTrades, error: allError } = await supabaseClient
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
        let query = supabaseClient
          .from('trades')
          .select(`
            *,
            trade_configurations (
              id,
              name
            ),
            transactions (
              id,
              amount,
              size,
              transaction_type,
              created_at
            )
          `)

        if (filters) {
          if (filters.status && filters.status !== 'ALL') {
            query = query.eq('status', filters.status.toUpperCase())
          }
          
          if (filters.configName && filters.configName !== 'all') {
            const { data: configData, error: configError } = await supabaseClient
              .from('trade_configurations')
              .select('id')
              .eq('name', filters.configName)
              .single()

            if (configError) throw configError
            if (configData) {
              query = query.eq('configuration_id', configData.id)
            }
          }

          if (filters.symbol) {
            query = query.ilike('symbol', `%${filters.symbol.toUpperCase()}%`)
          }

          if (filters.tradeType) {
            query = query.eq('trade_type', filters.tradeType)
          }

          if (filters.optionType === 'options') {
            query = query.eq('is_contract', true)
          } else if (filters.optionType === 'common') {
            query = query.eq('is_contract', false)
          }

          if (filters.maxEntryPrice) {
            query = query.lte('average_price', filters.maxEntryPrice)
          }

          if (filters.minEntryPrice) {
            query = query.gte('average_price', filters.minEntryPrice)
          }

          if (filters.weekFilter && filters.status?.toUpperCase() === TradeStatus.CLOSED) {
            const day = new Date(filters.weekFilter)
            const monday = new Date(day.setDate(day.getDate() - day.getDay()))
            const friday = new Date(day.setDate(day.getDate() + 4))
            query = query
              .gte('closed_at', monday.toISOString())
              .lte('closed_at', friday.toISOString())
          }
          
          if (filters.sortBy) {
            query = query.order(filters.sortBy, { ascending: filters.sortOrder === 'asc' })
          } else {
            query = query.order('created_at', { ascending: false })
          }

          if (filters.skip) {
            query = query.range(filters.skip, (filters.skip + (filters.limit || 100)) - 1)
          }
        }

        const { data: filteredTrades, error: filterError } = await query
        if (filterError) throw filterError
        data = filteredTrades
        break

      case 'createTrade':
        if (!input) throw new Error('Input is required for creating a trade')

        // Handle expiration date timezone
        if (input.expiration_date) {
          const [month, day, yearShort] = input.expiration_date.split('/')
          const year = `20${yearShort}`
          const dateString = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`
          const expirationDate = new Date(`${dateString}T16:30:00-04:00`)
          input.expiration_date = expirationDate.toISOString()
        }

        // Create trade
        const tradeId = generateTradeId()
        const { data: trade, error: tradeError } = await supabaseClient
          .from('trades')
          .insert({
            trade_id: tradeId,
            symbol: input.symbol,
            trade_type: input.trade_type,
            status: TradeStatus.OPEN,
            entry_price: input.entry_price,
            size: input.size,
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
        const { error: transactionError } = await supabaseClient
          .from('transactions')
          .insert({
            id: generateTransactionId(),
            trade_id: tradeId,
            transaction_type: TransactionType.OPEN,
            amount: input.entry_price,
            size: input.size,
            created_at: new Date().toISOString()
          })

        if (transactionError) throw transactionError

        // Fetch updated trade after trigger has run
        const { data: updatedTrade, error: fetchError } = await supabaseClient
          .from('trades')
          .select('*')
          .eq('trade_id', tradeId)
          .single()

        if (fetchError) throw fetchError
        data = updatedTrade
        break

      case 'addToTrade':
        if (!trade_id || !price || !size) {
          throw new Error('Missing required parameters: trade_id, price, and size are required for adding to a trade')
        }

        // Create ADD transaction
        const { error: addTransactionError } = await supabaseClient
          .from('transactions')
          .insert({
            id: generateTransactionId(),
            trade_id,
            transaction_type: TransactionType.ADD,
            amount: price,
            size,
            created_at: new Date().toISOString()
          })

        if (addTransactionError) throw addTransactionError

        // Fetch updated trade after trigger has run
        const { data: addedTrade, error: addFetchError } = await supabaseClient
          .from('trades')
          .select('*')
          .eq('trade_id', trade_id)
          .single()

        if (addFetchError) throw addFetchError
        data = addedTrade
        break

      case 'trimTrade':
        if (!trade_id || !price || !size) {
          throw new Error('Missing required parameters: trade_id, price, and size are required for trimming a trade')
        }

        // Create TRIM transaction
        const { error: trimTransactionError } = await supabaseClient
          .from('transactions')
          .insert({
            id: generateTransactionId(),
            trade_id,
            transaction_type: TransactionType.TRIM,
            amount: price,
            size,
            created_at: new Date().toISOString()
          })

        if (trimTransactionError) throw trimTransactionError

        // Fetch updated trade after trigger has run
        const { data: trimmedTrade, error: trimFetchError } = await supabaseClient
          .from('trades')
          .select('*')
          .eq('trade_id', trade_id)
          .single()

        if (trimFetchError) throw trimFetchError
        data = trimmedTrade
        break

      case 'exitTrade':
        if (!trade_id || !price) {
          throw new Error('Missing required parameters: trade_id and price are required for exiting a trade')
        }

        // Get current trade for size
        const { data: exitTrade, error: exitTradeError } = await supabaseClient
          .from('trades')
          .select('*')
          .eq('trade_id', trade_id)
          .single()

        if (exitTradeError) throw exitTradeError

        // Create CLOSE transaction
        const { error: exitTransactionError } = await supabaseClient
          .from('transactions')
          .insert({
            id: generateTransactionId(),
            trade_id,
            transaction_type: TransactionType.CLOSE,
            amount: price,
            size: exitTrade.current_size,
            created_at: new Date().toISOString()
          })

        if (exitTransactionError) throw exitTransactionError

        // Fetch updated trade after trigger has run
        const { data: closedTrade, error: closeFetchError } = await supabaseClient
          .from('trades')
          .select('*')
          .eq('trade_id', trade_id)
          .single()

        if (closeFetchError) throw closeFetchError

        // Add unit_profit_loss and exit_size to the response
        const responseData = {
          ...closedTrade,
          exit_size: exitTrade.current_size,
          unit_profit_loss: closedTrade.average_exit_price - closedTrade.average_price
        }
        data = responseData
        break

      default:
        throw new Error(`Unknown action: ${action}`)
    }

    return new Response(
      JSON.stringify(data),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    console.error('Error processing request:', error)
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : 'Unknown error' }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
    )
  }
})

// Helper function to generate a trade ID
function generateTradeId(): string {
  const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const alphanumeric = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  
  // First character must be a letter
  let id = letters.charAt(Math.floor(Math.random() * letters.length));
  
  // Generate 7 more random characters (can be letters or numbers)
  for (let i = 0; i < 7; i++) {
    id += alphanumeric.charAt(Math.floor(Math.random() * alphanumeric.length));
  }
  
  return id;
}

// Helper function to generate a transaction ID (similar format but always starts with 'T')
function generateTransactionId(): string {
  const alphanumeric = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  
  // First character is always 'T'
  let id = 'T';
  
  // Generate 7 more random characters (can be letters or numbers)
  for (let i = 0; i < 7; i++) {
    id += alphanumeric.charAt(Math.floor(Math.random() * alphanumeric.length));
  }
  
  return id;
} 