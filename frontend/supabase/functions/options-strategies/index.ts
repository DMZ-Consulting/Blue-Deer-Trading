import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface Transaction {
  transaction_type: 'OPEN' | 'ADD' | 'TRIM' | 'CLOSE'
  amount: number
  size: string
  net_cost?: number
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

interface StrategyFilters {
  skip?: number
  limit?: number
  status?: 'ALL' | 'OPEN' | 'CLOSED'
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  configName?: string
  weekFilter?: string
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
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const payload = await req.json() as RequestPayload
    const { action, filters, input, strategy_id, net_cost, size } = payload

    console.log('Received request payload:', JSON.stringify(payload, null, 2))

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
        if (allError) throw allError
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

        const { data: filteredStrategies, error: filterError } = await query
        if (filterError) {
          console.error('Error fetching strategy trades:', filterError)
          throw filterError
        }
        console.log(`Found ${filteredStrategies?.length ?? 0} strategy trades`)
        data = filteredStrategies
        break

      case 'createOptionsStrategy':
        if (!input) throw new Error('Input is required')
        const { data: strategy, error: strategyError } = await supabase
          .from('options_strategy_trades')
          .insert({
            name: input.name,
            underlying_symbol: input.underlying_symbol,
            status: 'open',
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

        if (strategyError) throw strategyError

        // Create initial transaction
        const { error: transactionError } = await supabase
          .from('options_strategy_transactions')
          .insert({
            strategy_id: strategy.id,
            transaction_type: 'OPEN',
            net_cost: input.net_cost,
            size: input.size,
            created_at: new Date().toISOString()
          })

        if (transactionError) throw transactionError
        data = strategy
        break

      case 'addToStrategy':
        if (!strategy_id || !net_cost || !size) throw new Error('strategy_id, net_cost, and size are required')
        // Get current strategy
        const { data: currentStrategy, error: currentStrategyError } = await supabase
          .from('options_strategy_trades')
          .select('*')
          .eq('id', strategy_id)
          .single()

        if (currentStrategyError) throw currentStrategyError

        // Calculate new average net cost and size
        const currentSize = parseFloat(currentStrategy.current_size)
        const addSize = parseFloat(size)
        const newSize = currentSize + addSize
        const newAverageNetCost = ((currentSize * currentStrategy.average_net_cost) + (addSize * net_cost)) / newSize

        // Create transaction
        const { error: addTransactionError } = await supabase
          .from('options_strategy_transactions')
          .insert({
            strategy_id,
            transaction_type: 'ADD',
            net_cost,
            size,
            created_at: new Date().toISOString()
          })

        if (addTransactionError) throw addTransactionError

        // Update strategy
        const { data: updatedStrategy, error: updateError } = await supabase
          .from('options_strategy_trades')
          .update({
            average_net_cost: newAverageNetCost,
            current_size: newSize.toString()
          })
          .eq('id', strategy_id)
          .select()
          .single()

        if (updateError) throw updateError
        data = updatedStrategy
        break

      case 'trimStrategy':
        if (!strategy_id || !net_cost || !size) throw new Error('strategy_id, net_cost, and size are required')
        // Get current strategy
        const { data: trimStrategy, error: trimStrategyError } = await supabase
          .from('options_strategy_trades')
          .select('*')
          .eq('id', strategy_id)
          .single()

        if (trimStrategyError) throw trimStrategyError

        const trimCurrentSize = parseFloat(trimStrategy.current_size)
        const trimSize = parseFloat(size)

        if (trimSize > trimCurrentSize) {
          throw new Error('Trim size is greater than current strategy size')
        }

        // Create transaction
        const { error: trimTransactionError } = await supabase
          .from('options_strategy_transactions')
          .insert({
            strategy_id,
            transaction_type: 'TRIM',
            net_cost,
            size,
            created_at: new Date().toISOString()
          })

        if (trimTransactionError) throw trimTransactionError

        // Update strategy
        const { data: trimmedStrategy, error: trimUpdateError } = await supabase
          .from('options_strategy_trades')
          .update({
            current_size: (trimCurrentSize - trimSize).toString()
          })
          .eq('id', strategy_id)
          .select()
          .single()

        if (trimUpdateError) throw trimUpdateError
        data = trimmedStrategy
        break

      case 'exitStrategy':
        if (!strategy_id || !net_cost) throw new Error('strategy_id and net_cost are required')
        // Get current strategy and all its transactions
        const { data: exitStrategy, error: exitStrategyError } = await supabase
          .from('options_strategy_trades')
          .select(`
            *,
            options_strategy_transactions (*)
          `)
          .eq('id', strategy_id)
          .single()

        if (exitStrategyError) throw exitStrategyError

        // Create exit transaction
        const { error: exitTransactionError } = await supabase
          .from('options_strategy_transactions')
          .insert({
            strategy_id,
            transaction_type: 'CLOSE',
            net_cost,
            size: exitStrategy.current_size,
            created_at: new Date().toISOString()
          })

        if (exitTransactionError) throw exitTransactionError

        // Calculate profit/loss
        const transactions = exitStrategy.options_strategy_transactions
        const openTransactions = transactions.filter((t: any) => 
          t.transaction_type === 'OPEN' || t.transaction_type === 'ADD'
        )
        const trimTransactions = transactions.filter((t: any) => 
          t.transaction_type === 'TRIM'
        )

        const totalCost = openTransactions.reduce((sum: number, t: any) => 
          sum + (parseFloat(t.net_cost.toString()) * parseFloat(t.size)), 0
        )
        const totalSize = openTransactions.reduce((sum: number, t: any) => 
          sum + parseFloat(t.size), 0
        )
        const avgEntryCost = totalCost / totalSize

        const totalExitCost = trimTransactions.reduce((sum: number, t: any) => 
          sum + (parseFloat(t.net_cost.toString()) * parseFloat(t.size)), 0
        ) + (net_cost * parseFloat(exitStrategy.current_size))
        const totalExitSize = trimTransactions.reduce((sum: number, t: any) => 
          sum + parseFloat(t.size), 0
        ) + parseFloat(exitStrategy.current_size)
        const avgExitCost = totalExitCost / totalExitSize

        const profitLoss = (avgExitCost - avgEntryCost) * parseFloat(exitStrategy.size) * 100

        // Update strategy
        const { data: closedStrategy, error: closeUpdateError } = await supabase
          .from('options_strategy_trades')
          .update({
            status: 'closed',
            closed_at: new Date().toISOString(),
            profit_loss: profitLoss
          })
          .eq('id', strategy_id)
          .select()
          .single()

        if (closeUpdateError) throw closeUpdateError
        data = closedStrategy
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