import { serve } from 'https://deno.land/std@0.177.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'
import { SupabaseClient } from 'https://esm.sh/@supabase/supabase-js@2'

// Set up logging
const logger = {
  info: (message: string, ...args: any[]) => {
    console.log(`[INFO] ${message}`, ...args)
  },
  error: (message: string, ...args: any[]) => {
    console.error(`[ERROR] ${message}`, ...args) 
  },
  debug: (message: string, ...args: any[]) => {
    console.debug(`[DEBUG] ${message}`, ...args)
  }
}

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
  logger.info('Received request:', req.method, req.url)

  logger.info('Received request:', req.method, req.url)

  if (req.method === 'OPTIONS') {
    logger.debug('Handling OPTIONS request')
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    logger.debug('Initializing Supabase client')
    logger.debug('Initializing Supabase client')
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const payload = await req.json() as RequestPayload
    logger.info('Request payload:', payload)
    const { action, filters, input, trade_id, price, size } = payload

    let data

    switch (action) {
      case 'getAll':
        logger.debug('Handling getAll action')
        const { data: allTrades, error: allError } = await supabaseClient
          .from('trades')
          .select(`
            *,
            trade_configurations (*)
          `)
          .order('created_at', { ascending: false })
        if (allError) throw allError
        data = allTrades
        logger.debug('Retrieved all trades:', data)
        break

      case 'getTrades':
        logger.debug('Handling getTrades action')
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
          logger.debug('Applying filters:', filters)
          if (filters.status && filters.status !== 'ALL') {
            query = query.eq('status', filters.status.toUpperCase())
          }
          
          if (filters.configName && filters.configName !== 'all') {
            logger.debug('Fetching config data for:', filters.configName)
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
        logger.debug('Retrieved filtered trades:', data)
        break

      case 'createTrade':
        logger.debug('Handling createTrade action')
        if (!input) throw new Error('Input is required for creating a trade')

        // Handle expiration date timezone
        if (input.expiration_date) {
          const [month, day, yearShort] = input.expiration_date.split('/')
          const year = `20${yearShort}`
          const dateString = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`
          const expirationDate = new Date(`${dateString}T16:30:00-04:00`)
          input.expiration_date = expirationDate.toISOString()
          logger.debug('Processed expiration date:', input.expiration_date)
        }

        // Generate trade ID
        logger.debug('Generating trade ID');
        const tradeId = await generateTradeId(supabaseClient);
        logger.debug('Generated trade ID:', tradeId);

        // Log the full trade object before insert
        const tradeData = {
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
        };
        logger.debug('Trade data to insert:', tradeData);

        // Create trade with explicit columns
        logger.debug('Creating trade with ID:', tradeId);
        const { data: trade, error: tradeError } = await supabaseClient
          .from('trades')
          .insert(tradeData)
          .select(`
            trade_id,
            symbol,
            trade_type,
            status,
            entry_price,
            size,
            created_at,
            configuration_id,
            is_contract,
            is_day_trade,
            strike,
            expiration_date,
            option_type
          `)
          .single();

        if (tradeError) {
          logger.error('Trade creation error:', tradeError);
          logger.error('Full error details:', JSON.stringify(tradeError, null, 2));
          logger.error('Supabase client config:', {
            url: Deno.env.get('SUPABASE_URL'),
            // Don't log the full key
            hasServiceRoleKey: !!Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
          });
          throw tradeError;
        }
        logger.debug('Successfully created trade:', trade);

        // Create initial transaction
        logger.debug('Creating initial transaction');
        const transactionId = await generateTransactionId(supabaseClient);
        logger.debug('Generated transaction ID:', transactionId);

        // Log the full transaction object before insert
        const transactionData = {
          id: transactionId,
          trade_id: tradeId,
          transaction_type: TransactionType.OPEN,
          amount: input.entry_price,
          size: input.size,
          created_at: new Date().toISOString()
        };
        logger.debug('Transaction data to insert:', transactionData);

        const { error: transactionError } = await supabaseClient
          .from('transactions')
          .insert(transactionData);

        if (transactionError) {
          logger.error('Transaction creation error:', transactionError);
          logger.error('Full error details:', JSON.stringify(transactionError, null, 2));
          throw transactionError;
        }
        logger.debug('Created initial transaction')

        // Fetch updated trade after trigger has run
        const { data: updatedTrade, error: fetchError } = await supabaseClient
          .from('trades')
          .select('*')
          .eq('trade_id', tradeId)
          .single()

        if (fetchError) throw fetchError
        data = updatedTrade
        logger.debug('Retrieved updated trade:', data)
        break

      case 'addToTrade':
        logger.debug('Handling addToTrade action')
        if (!trade_id || !price || !size) {
          throw new Error('Missing required parameters: trade_id, price, and size are required for adding to a trade')
        }

        // Create ADD transaction
        const { error: addTransactionError } = await supabaseClient
          .from('transactions')
          .insert({
            id: await generateTransactionId(supabaseClient),
            trade_id: trade_id,
            transaction_type: TransactionType.ADD,
            amount: price,
            size,
            created_at: new Date().toISOString()
          })

        if (addTransactionError) throw addTransactionError
        logger.debug('Created ADD transaction')

        // Fetch updated trade after trigger has run
        const { data: addedTrade, error: addFetchError } = await supabaseClient
          .from('trades')
          .select('*')
          .eq('trade_id', trade_id)
          .single()

        if (addFetchError) throw addFetchError
        data = addedTrade
        logger.debug('Retrieved updated trade:', data)
        break

      case 'trimTrade':
        logger.debug('Handling trimTrade action')
        if (!trade_id || !price || !size) {
          throw new Error('Missing required parameters: trade_id, price, and size are required for trimming a trade')
        }

        // Create TRIM transaction
        const { error: trimTransactionError } = await supabaseClient
          .from('transactions')
          .insert({
            id: await generateTransactionId(supabaseClient),
            trade_id: trade_id,
            transaction_type: TransactionType.TRIM,
            amount: price,
            size: size,
            created_at: new Date().toISOString()
          })

        if (trimTransactionError) throw trimTransactionError
        logger.debug('Created TRIM transaction')

        // Fetch updated trade after trigger has run
        const { data: trimmedTrade, error: trimFetchError } = await supabaseClient
          .from('trades')
          .select('*')
          .eq('trade_id', trade_id)
          .single()

        if (trimFetchError) throw trimFetchError
        data = trimmedTrade
        logger.debug('Retrieved updated trade:', data)
        break

      case 'exitTrade':
        logger.debug('Handling exitTrade action')
        if (!trade_id || price === undefined) {
          throw new Error('Missing required parameters: trade_id and price are required for exiting a trade')
        }

        // Get current trade for size
        const { data: exitTrade, error: exitTradeError } = await supabaseClient
          .from('trades')
          .select('*')
          .eq('trade_id', trade_id)
          .single()

        if (exitTradeError) throw exitTradeError
        logger.debug('Retrieved trade for exit:', exitTrade)

        // Create CLOSE transaction
        const { error: exitTransactionError } = await supabaseClient
          .from('transactions')
          .insert({
            id: await generateTransactionId(supabaseClient),
            trade_id: trade_id,
            transaction_type: TransactionType.CLOSE,
            amount: price,
            size: exitTrade.current_size,
            created_at: new Date().toISOString()
          })

        if (exitTransactionError) throw exitTransactionError
        logger.debug('Created CLOSE transaction')

        // Normalize exit transaction sizes for proportional calculations
        await normalizeExitTransactionSizes(supabaseClient, trade_id)

        // Fetch updated trade after trigger has run
        const { data: closedTrade, error: closeFetchError } = await supabaseClient
          .from('trades')
          .select('*')
          .eq('trade_id', trade_id)
          .single()

        if (closeFetchError) throw closeFetchError
        logger.debug('Retrieved closed trade:', closedTrade)

        // Add unit_profit_loss and exit_size to the response
        const responseData = {
          ...closedTrade,
          exit_size: exitTrade.current_size,
          unit_profit_loss: closedTrade.average_exit_price - closedTrade.average_price
        }
        data = responseData
        logger.debug('Final response data:', data)
        break

      default:
        logger.error('Unknown action:', action)
        throw new Error(`Unknown action: ${action}`)
    }

    logger.info('Successfully processed request')
    return new Response(
      JSON.stringify(data),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    logger.error('Error processing request:', error)
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : 'Unknown error' }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
    )
  }
})

// Helper function to check if an ID exists in the database
async function isIdUnique(supabase: SupabaseClient, table: 'trades' | 'transactions', id: string): Promise<boolean> {
  const { data } = await supabase
    .from(table)
    .select('id')
    .eq('id', id)
    .single();
  
  return !data;
}

// Helper function to generate a trade ID with uniqueness check
async function generateTradeId(supabase: SupabaseClient, maxAttempts = 10): Promise<string> {
  const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const alphanumeric = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    // First character must be a letter
    let id = letters.charAt(Math.floor(Math.random() * letters.length));
    
    // Generate 7 more random characters (must include both letters and numbers)
    let hasLetter = false;
    let hasNumber = false;
    let remainingChars = '';
    
    while (remainingChars.length < 7 || !hasLetter || !hasNumber) {
      const char = alphanumeric.charAt(Math.floor(Math.random() * alphanumeric.length));
      if (/[A-Z]/.test(char)) hasLetter = true;
      if (/[0-9]/.test(char)) hasNumber = true;
      remainingChars += char;
    }
    
    id += remainingChars.slice(0, 7);
    
    // Check if ID is unique
    if (await isIdUnique(supabase, 'trades', id)) {
      return id;
    }
  }
  
  throw new Error('Failed to generate unique trade ID after maximum attempts');
}

// Helper function to generate a transaction ID with uniqueness check
async function generateTransactionId(supabase: SupabaseClient, maxAttempts = 10): Promise<string> {
  const alphanumeric = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    // First character is always 'T'
    let id = 'T';
    
    // Generate 7 more random characters (must include both letters and numbers)
    let hasLetter = false;
    let hasNumber = false;
    let remainingChars = '';
    
    while (remainingChars.length < 7 || !hasLetter || !hasNumber) {
      const char = alphanumeric.charAt(Math.floor(Math.random() * alphanumeric.length));
      if (/[A-Z]/.test(char)) hasLetter = true;
      if (/[0-9]/.test(char)) hasNumber = true;
      remainingChars += char;
    }
    
    id += remainingChars.slice(0, 7);
    
    // Check if ID is unique
    if (await isIdUnique(supabase, 'transactions', id)) {
      return id;
    }
  }
  
  throw new Error('Failed to generate unique transaction ID after maximum attempts');
}

// Helper function to normalize exit transaction sizes for proportional calculations
async function normalizeExitTransactionSizes(supabase: SupabaseClient, trade_id: string): Promise<void> {
  logger.debug('Normalizing exit transaction sizes for trade:', trade_id)
  
  // Get all exit transactions (TRIM and CLOSE) for this trade
  const { data: exitTransactions, error: exitTransactionError } = await supabase
    .from('transactions')
    .select('id, transaction_type, size')
    .eq('trade_id', trade_id)
    .in('transaction_type', [TransactionType.TRIM, TransactionType.CLOSE])

  if (exitTransactionError) throw exitTransactionError
  
  if (!exitTransactions || exitTransactions.length === 0) {
    logger.debug('No exit transactions found to normalize')
    return
  }

  logger.debug('Found exit transactions to normalize:', exitTransactions)

  // Calculate total exit size
  const totalExitSize = exitTransactions.reduce((total: number, transaction: any) => 
    total + parseFloat(transaction.size), 0
  )

  // Calculate proportional size for each exit transaction
  const proportionalSize = totalExitSize / exitTransactions.length

  logger.debug('Normalizing sizes:', {
    totalExitSize,
    transactionCount: exitTransactions.length,
    proportionalSize
  })

  // Update each exit transaction with the proportional size
  for (const transaction of exitTransactions) {
    const { error: updateError } = await supabase
      .from('transactions')
      .update({
        size: proportionalSize.toString()
      })
      .eq('id', transaction.id)

    if (updateError) {
      logger.error('Error updating transaction size:', updateError)
      throw updateError
    }
  }

  logger.debug('Successfully normalized exit transaction sizes')
}