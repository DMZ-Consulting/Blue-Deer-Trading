import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
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
        if (allError) {
          console.error('Error fetching all trades:', allError)
          throw new Error(`Failed to fetch all trades: ${allError.message}`)
        }
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
          // TODO: Make these all uppercase when the backend is updated.
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
              throw new Error(`Failed to fetch trade configuration '${filters.configName}': ${configError.message}`)
            }

            if (configData) {
              console.log('Found configuration ID:', configData.id)
              query = query.eq('configuration_id', configData.id)
            } else {
              console.warn('No configuration found for name:', filters.configName)
              throw new Error(`No trade configuration found with name '${filters.configName}'`)
            }
          }

          if (filters.symbol) {
            console.log('Applying symbol filter:', filters.symbol.toUpperCase())
            query = query.ilike('symbol', `%${filters.symbol.toUpperCase()}%`)
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
          throw new Error(`Failed to fetch filtered trades: ${filterError.message}`)
        }
        console.log(`Found ${filteredTrades?.length ?? 0} trades`)
        data = filteredTrades
        break

      case 'createTrade':
        if (!input) {
          console.error('Input is required for createTrade action')
          throw new Error('Input is required for creating a trade')
        }
        console.log('Creating new trade with input:', input)

        try {
          const tradeId = generateTradeId()
          console.log('Generated trade ID:', tradeId)

          // if expiration date is provided, make sure the time is set to 4:30PM EST, even if the request is from a different timezone
          if (input.expiration_date) {
            // Parse the MM/DD/YY format explicitly
            const [month, day, yearShort] = input.expiration_date.split('/');
            const year = `20${yearShort}`; // Convert 2-digit year to 4-digit
            
            // Create the date string with the exact date at 16:30 ET
            const dateString = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
            const expirationDate = new Date(`${dateString}T16:30:00-04:00`);
            input.expiration_date = expirationDate.toISOString();
          }

          const tradeData = {
            trade_id: tradeId,
            symbol: input.symbol,
            trade_type: input.trade_type,
            status: TradeStatus.OPEN,
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
          }
          console.log('Prepared trade data:', tradeData)

          const { data: trade, error: tradeError } = await supabase
            .from('trades')
            .insert(tradeData)
            .select()
            .single()

          if (tradeError) {
            console.error('Error creating trade:', tradeError)
            throw tradeError
          }
          console.log('Successfully created trade:', trade)

          // Create initial transaction
          const transactionData = {
            id: generateTransactionId(),
            trade_id: trade.trade_id,
            transaction_type: TransactionType.OPEN,
            amount: input.entry_price,
            size: input.size,
            created_at: new Date().toISOString()
          }
          console.log('Creating initial transaction:', transactionData)

          const { error: transactionError } = await supabase
            .from('transactions')
            .insert(transactionData)

          if (transactionError) {
            console.error('Error creating transaction:', transactionError)
            // If transaction creation fails, we should delete the trade
            await supabase
              .from('trades')
              .delete()
              .eq('trade_id', trade.trade_id)
            throw transactionError
          }
          console.log('Successfully created transaction')

          data = { trade, transaction: transactionData }
          console.log('Returning data:', data)
        } catch (error) {
          console.error('Error in createTrade:', error)
          throw new Error(`Error creating new trade: ${error instanceof Error ? error.message : 'Unknown error'}`)
        }
        break

      case 'addToTrade':
        if (!trade_id || !price || !size) {
          throw new Error('Missing required parameters: trade_id, price, and size are required for adding to a trade')
        }

        try {
          // Get current trade
          const { data: currentTrade, error: currentTradeError } = await supabase
            .from('trades')
            .select('*')
            .eq('trade_id', trade_id)
            .single()

          if (currentTradeError) {
            console.error('Error fetching trade for add:', currentTradeError)
            throw new Error(`Failed to fetch trade ${trade_id} for adding: ${currentTradeError.message}`)
          }

          // Calculate new average price and size
          const currentSize = parseFloat(currentTrade.current_size)
          const addSize = parseFloat(size)
          const newSize = currentSize + addSize
          // TODO: Make sure this calculation is correct.
          const newAveragePrice = ((currentSize * currentTrade.average_price) + (addSize * price)) / newSize

          // Create transaction
          const { error: addTransactionError } = await supabase
            .from('transactions')
            .insert({
              id: generateTransactionId(),
              trade_id,
              transaction_type: 'ADD',
              amount: price,
              size,
              created_at: new Date().toISOString()
            })

          if (addTransactionError) {
            console.error('Error creating add transaction:', addTransactionError)
            throw new Error(`Failed to create add transaction: ${addTransactionError.message}`)
          }

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

          if (updateError) {
            console.error('Error updating trade for add:', updateError)
            throw new Error(`Failed to update trade ${trade_id} after adding: ${updateError.message}`)
          }
          data = updatedTrade
        } catch (error) {
          console.error('Error in addToTrade:', error)
          throw new Error(`Error adding to trade ${trade_id}: ${error instanceof Error ? error.message : 'Unknown error'}`)
        }
        break

      case 'trimTrade':
        if (!trade_id || !price || !size) {
          throw new Error('Missing required parameters: trade_id, price, and size are required for trimming a trade')
        }
        try {
          // Get current trade
          const { data: trimTrade, error: trimTradeError } = await supabase
            .from('trades')
          .select('*')
          .eq('trade_id', trade_id)
          .single()

        if (trimTradeError) {
          console.error('Error fetching trade for trim:', trimTradeError)
          throw new Error(`Failed to fetch trade ${trade_id} for trimming: ${trimTradeError.message}`)
        }

        const trimCurrentSize = parseFloat(trimTrade.current_size)
        const trimSize = parseFloat(size)

        if (trimSize > trimCurrentSize) {
          throw new Error(`Cannot trim ${trimSize} shares/contracts - current position size is only ${trimCurrentSize}`)
        }

        // Create transaction
        const { error: trimTransactionError } = await supabase
          .from('transactions')
          .insert({
            id: generateTransactionId(),
            trade_id,
            transaction_type: TransactionType.TRIM,
            amount: price,
            size,
            created_at: new Date().toISOString()
          })

        if (trimTransactionError) {
          console.error('Error creating trim transaction:', trimTransactionError)
          throw new Error(`Failed to create trim transaction: ${trimTransactionError.message}`)
        }

        // Update trade
        const { data: trimmedTrade, error: trimUpdateError } = await supabase
          .from('trades')
          .update({
            current_size: (trimCurrentSize - trimSize).toString()
          })
          .eq('trade_id', trade_id)
          .select()
          .single()

          if (trimUpdateError) {
            console.error('Error updating trade for trim:', trimUpdateError)
            throw new Error(`Failed to update trade ${trade_id} after trimming: ${trimUpdateError.message}`)
          }
          data = trimmedTrade
        } catch (error) {
          console.error('Error in trimTrade:', error)
          throw new Error(`Error trimming trade ${trade_id}: ${error instanceof Error ? error.message : 'Unknown error'}`)
        }
        break

      case 'exitTrade':
        if (!trade_id || !price) {
          throw new Error('Missing required parameters: trade_id and price are required for exiting a trade')
        }
        try {
          // Get current trade and all its transactions
          const { data: exitTradeData, error: exitTradeError } = await supabase
            .from('trades')
            .select(`
              *,
              transactions (*)
            `)
            .eq('trade_id', trade_id)
            .single()

          if (exitTradeError) {
            console.error('Error fetching trade for exit:', exitTradeError)
            throw new Error(`Failed to fetch trade ${trade_id} for exiting: ${exitTradeError.message}`)
          }

          // Create exit transaction
          const { error: exitTransactionError } = await supabase
            .from('transactions')
            .insert({
              id: generateTransactionId(),
              trade_id,
              transaction_type: TransactionType.CLOSE,
              amount: price,
              size: exitTradeData.current_size,
              created_at: new Date().toISOString()
            })

          if (exitTransactionError) {
            console.error('Error creating exit transaction:', exitTransactionError)
            throw new Error(`Failed to create exit transaction: ${exitTransactionError.message}`)
          }

          // Calculate profit/loss
          const exitTradeWithTransactions = exitTradeData as ExitTrade
          console.log('Exit trade data:', exitTradeWithTransactions)

          const openTransactions = exitTradeWithTransactions.transactions.filter((t: Transaction) => 
            t.transaction_type === TransactionType.OPEN || t.transaction_type === TransactionType.ADD
          )
          console.log('Open/Add transactions:', openTransactions)

          const trimTransactions = exitTradeWithTransactions.transactions.filter((t: Transaction) => 
            t.transaction_type === TransactionType.TRIM
          )
          console.log('Trim transactions:', trimTransactions)

          const totalCost = openTransactions.reduce((sum: number, t: Transaction) => {
            const amount = parseFloat(t.amount.toString())
            const size = parseFloat(t.size)
            const cost = amount * size
            console.log(`Transaction cost calculation: amount ${amount} * size ${size} = ${cost}`)
            return sum + cost
          }, 0)
          console.log('Total cost:', totalCost)

          const totalOpenSize = openTransactions.reduce((sum: number, t: Transaction) => {
            const size = parseFloat(t.size)
            console.log(`Adding size ${size} to total open size ${sum}`)
            return sum + size
          }, 0)
          console.log('Total open size:', totalOpenSize)

          const averageCost = totalCost / totalOpenSize
          console.log('Average cost:', averageCost)

          const trimProfitLoss = trimTransactions.reduce((sum: number, t: Transaction) => {
            const amount = parseFloat(t.amount.toString())
            const size = parseFloat(t.size)
            const profitLoss = (amount - averageCost) * size
            console.log(`Trim P/L calculation: (amount ${amount} - avg cost ${averageCost}) * size ${size} = ${profitLoss}`)
            return sum + profitLoss
          }, 0)
          console.log('Total trim P/L:', trimProfitLoss)

          const currentSize = parseFloat(exitTradeData.current_size)
          const exitProfitLoss = (price - averageCost) * currentSize
          console.log(`Exit P/L calculation: (price ${price} - avg cost ${averageCost}) * current size ${currentSize} = ${exitProfitLoss}`)

          const totalProfitLoss = trimProfitLoss + exitProfitLoss
          console.log('Total P/L:', totalProfitLoss)

          // Calculate average exit price
          const totalExitValue = trimTransactions.reduce((sum: number, t: Transaction) => {
            const amount = parseFloat(t.amount.toString())
            const size = parseFloat(t.size)
            const value = amount * size
            console.log(`Trim exit value: amount ${amount} * size ${size} = ${value}`)
            return sum + value
          }, 0) + (price * currentSize)
          console.log('Total exit value:', totalExitValue)

          const totalExitSize = trimTransactions.reduce((sum: number, t: Transaction) => {
            const size = parseFloat(t.size)
            console.log(`Adding size ${size} to total exit size ${sum}`)
            return sum + size
          }, 0) + currentSize
          console.log('Total exit size:', totalExitSize)

          const averageExitPrice = totalExitValue / totalExitSize
          console.log('Average exit price:', averageExitPrice)

          // Update trade
          const { data: closedTrade, error: closeUpdateError } = await supabase
            .from('trades')
            .update({
              status: TradeStatus.CLOSED,
              exit_price: price,
              average_exit_price: averageExitPrice,
              profit_loss: totalProfitLoss,
              win_loss: totalProfitLoss > 0 ? 'WIN' : totalProfitLoss < 0 ? 'LOSS' : 'BREAKEVEN',
              closed_at: new Date().toISOString(),
              current_size: '0'
            })
            .eq('trade_id', trade_id)
            .select()
            .single()

          closedTrade.exit_size = exitTradeData.current_size
          closedTrade.unit_profit_loss = averageExitPrice - averageCost

          if (closeUpdateError) {
            console.error('Error updating trade for exit:', closeUpdateError)
            throw new Error(`Failed to update trade ${trade_id} after exiting: ${closeUpdateError.message}`)
          }
          data = closedTrade
        } catch (error) {
          console.error('Error in exitTrade:', error)
          throw new Error(`Error exiting trade ${trade_id}: ${error instanceof Error ? error.message : 'Unknown error'}`)
        }
        break

      default:
        throw new Error(`Unknown action: ${action}. Supported actions are: getAll, getTrades, createTrade, addToTrade, trimTrade, exitTrade`)
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