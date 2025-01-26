import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface Transaction {
  transaction_type: 'OPEN' | 'ADD' | 'TRIM' | 'CLOSE'
  amount: number
  size: string
  net_cost?: number
}

enum StrategyStatus {
  OPEN = 'OPEN',
  CLOSED = 'CLOSED'
}

enum StrategyTransactionType {
  OPEN = 'OPEN',
  ADD = 'ADD',
  TRIM = 'TRIM',
  CLOSE = 'CLOSE'
}

interface Strategy {
  id: number
  name: string
  underlying_symbol: string
  status: StrategyStatus
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

interface StrategyFilters {
  skip?: number
  limit?: number
  status?: 'ALL' | 'OPEN' | 'CLOSED'
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  configName?: string
  weekFilter?: string
  symbol?: string
}

interface StrategyInput {
  name: string
  underlying_symbol: string
  legs: string
  net_cost: number
  size: string
  trade_group?: string
  configuration_id?: number
}

interface RequestPayload {
  action: string
  filters?: StrategyFilters
  input?: StrategyInput
  strategy_id?: string
  net_cost?: number
  size?: string
}

declare global {
  const Deno: {
    env: {
      get(key: string): string | undefined
    }
  }
}

serve(async (req: Request) => {
  console.log('Received request:', req.method, req.url)
  
  if (req.method === 'OPTIONS') {
    console.log('Handling OPTIONS request')
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    console.log('Initializing Supabase client')
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const payload = await req.json() as RequestPayload
    const { action, filters, input, strategy_id, net_cost, size } = payload

    console.log('Received request payload:', JSON.stringify(payload, null, 2))
    console.log(`Processing action: ${action}`)

    let data

    switch (action) {
      case 'getAll':
        console.log('Fetching all strategy trades')
        const { data: allStrategies, error: allError } = await supabase
          .from('options_strategy_trades')
          .select(`
            *,
            trade_configurations (*)
          `)
          .order('created_at', { ascending: false })
        if (allError) {
          console.error('Error fetching all strategies:', allError)
          throw allError
        }
        console.log(`Retrieved ${allStrategies?.length ?? 0} strategies`)
        data = allStrategies
        break

      case 'getStrategyTrades':
        console.log('Fetching strategy trades with filters:', JSON.stringify(filters, null, 2))
        let query = supabase
          .from('options_strategy_trades')
          .select(`
            *,
            trade_configurations (
              id,
              name
            )
          `)

        if (filters) {
          if (filters.status && filters.status !== 'ALL') {
            console.log('Applying status filter:', filters.status.toUpperCase())
            query = query.eq('status', filters.status.toUpperCase())
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
            console.log('Applying symbol filter:', filters.symbol.toUpperCase())
            query = query.ilike('underlying_symbol', `%${filters.symbol.toUpperCase()}%`)
          }

          // Handle date filters
          if (filters.weekFilter && filters.status?.toUpperCase() === 'CLOSED') {
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

        const { data: filteredStrategies, error: filterError } = await query
        if (filterError) {
          console.error('Error fetching strategy trades:', filterError)
          throw filterError
        }
        console.log(`Found ${filteredStrategies?.length ?? 0} strategy trades`)
        data = filteredStrategies
        break

      case 'createOptionsStrategy':
        console.log('Creating new options strategy:', input)
        if (!input) throw new Error('Input is required')
        const { data: strategy, error: strategyError } = await supabase
          .from('options_strategy_trades')
          .insert({
            name: input.name,
            underlying_symbol: input.underlying_symbol,
            status: StrategyStatus.OPEN,
            legs: input.legs,
            net_cost: input.net_cost,
            average_net_cost: input.net_cost,
            size: input.size,
            current_size: input.size,
            trade_group: input.trade_group,
            configuration_id: input.configuration_id,
            created_at: new Date().toISOString()
          })
          .select()
          .single()

        if (strategyError) {
          console.error('Error creating strategy:', strategyError)
          throw strategyError
        }
        console.log('Created strategy:', strategy)

        // Create initial transaction
        console.log('Creating initial transaction for strategy:', strategy.strategy_id)
        const { error: transactionError } = await supabase
          .from('options_strategy_transactions')
          .insert({
            strategy_id: strategy.strategy_id,
            transaction_type: StrategyTransactionType.OPEN,
            net_cost: input.net_cost,
            size: input.size,
            created_at: new Date().toISOString()
          })

        if (transactionError) {
          console.error('Error creating initial transaction:', transactionError)
          throw transactionError
        }
        console.log('Successfully created initial transaction')
        data = strategy
        break

      case 'addToStrategy':
        console.log('Adding to strategy:', { strategy_id, net_cost, size })
        if (!strategy_id || !net_cost || !size) throw new Error('strategy_id, net_cost, and size are required')
          
        // Create transaction
        console.log('Creating ADD transaction')
        const { error: addTransactionError } = await supabase
          .from('options_strategy_transactions')
          .insert({
            strategy_id,
            transaction_type: StrategyTransactionType.ADD,
            net_cost,
            size,
            created_at: new Date().toISOString()
          })

        if (addTransactionError) {
          console.error('Error creating ADD transaction:', addTransactionError)
          throw addTransactionError
        }
        // get updated strategy
        const { data: addUpdatedStrategy, error: addUpdateError } = await supabase
          .from('options_strategy_trades')
          .select('*')
          .eq('strategy_id', strategy_id)
          .single()

        if (addUpdateError) {
          console.error('Error updating strategy:', addUpdateError)
          throw addUpdateError
        }
        console.log('Successfully updated strategy:', addUpdatedStrategy)
        data = addUpdatedStrategy
        break

      case 'trimStrategy':
        console.log('Trimming strategy:', { strategy_id, net_cost, size })
        if (!strategy_id || !net_cost || !size) throw new Error('strategy_id, net_cost, and size are required')
        // Get current strategy
        const { data: trimStrategy, error: trimStrategyError } = await supabase
          .from('options_strategy_trades')
          .select('*')
          .eq('strategy_id', strategy_id)
          .single()

        if (trimStrategyError) {
          console.error('Error fetching strategy to trim:', trimStrategyError)
          throw trimStrategyError
        }
        console.log('Current strategy:', trimStrategy)

        const trimCurrentSize = parseFloat(trimStrategy.current_size)
        const trimSize = parseFloat(size)
        console.log('Sizes:', { trimCurrentSize, trimSize })

        if (trimSize > trimCurrentSize) {
          console.error('Invalid trim size:', { trimSize, trimCurrentSize })
          throw new Error('Trim size is greater than current strategy size')
        }

        // Create transaction
        console.log('Creating TRIM transaction')
        const { error: trimTransactionError } = await supabase
          .from('options_strategy_transactions')
          .insert({
            strategy_id,
            transaction_type: StrategyTransactionType.TRIM,
            net_cost,
            size,
            created_at: new Date().toISOString()
          })

        if (trimTransactionError) {
          console.error('Error creating TRIM transaction:', trimTransactionError)
          throw trimTransactionError
        }
        // get updated strategy
        const { data: trimUpdatedStrategy, error: trimUpdateError } = await supabase
          .from('options_strategy_trades')
          .select('*')
          .eq('strategy_id', strategy_id)
          .single()

        if (trimUpdateError) {
          console.error('Error updating strategy:', trimUpdateError)
          throw trimUpdateError
        }
        console.log('Successfully updated strategy:', trimUpdatedStrategy)
        data = trimUpdatedStrategy
        break

      case 'exitStrategy':
        console.log('Exiting strategy:', { strategy_id, net_cost })
        if (!strategy_id || !net_cost) throw new Error('strategy_id and net_cost are required')
        // Get current strategy and all its transactions
        const { data: exitStrategy, error: exitStrategyError } = await supabase
          .from('options_strategy_trades')
          .select(`
            *,
            options_strategy_transactions (*)
          `)
          .eq('strategy_id', strategy_id)
          .single()

        if (exitStrategyError) {
          console.error('Error fetching strategy to exit:', exitStrategyError)
          throw exitStrategyError
        }
        console.log('Current strategy and transactions:', exitStrategy)

        // Create exit transaction
        console.log('Creating CLOSE transaction')
        const { error: exitTransactionError } = await supabase
          .from('options_strategy_transactions')
          .insert({
            strategy_id,
            transaction_type: StrategyTransactionType.CLOSE,
            net_cost,
            size: exitStrategy.current_size,
            created_at: new Date().toISOString()
          })

        if (exitTransactionError) {
          console.error('Error creating CLOSE transaction:', exitTransactionError)
          throw exitTransactionError
        }

        console.log('Successfully closed strategy:', exitStrategy)
        data = exitStrategy
        break

      default:
        console.error('Unknown action:', action)
        throw new Error(`Unknown action: ${action}`)
    }

    console.log('Sending successful response')
    return new Response(
      JSON.stringify(data),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    console.error('Error processing request:', error)
    const message = error instanceof Error ? error.message : 'An unknown error occurred'
    return new Response(
      JSON.stringify({ error: message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
    )
  }
}) 