import { serve } from 'https://deno.land/std@0.177.0/http/server.ts'
import { createClient, SupabaseClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface Transaction {
  id: string;
  trade_id: string;
  transaction_type: string;
  amount: number;
  size: string;
}

interface TransactionData {
  amount: number;
  size: string;
  transaction_type: string;
}

interface RequestBody {
  action: 'updateTransaction' | 'deleteTransaction';
  transactionId: string;
  data?: TransactionData;
}

const updateTransaction = async (client: SupabaseClient, id: string, data: TransactionData) => {
  const { error: updateError } = await client
    .from('transactions')
    .update({
      amount: data.amount,
      size: data.size,
      transaction_type: data.transaction_type
    })
    .eq('id', id);

  if (updateError) throw updateError;

  // Fetch the updated trade data
  const { data: transactionData, error: transactionError } = await client
    .from('transactions')
    .select('trade_id')
    .eq('id', id)
    .single();

  if (transactionError) throw transactionError;

  // Get the updated trade data
  const { data: tradeData, error: tradeError } = await client
    .from('trades')
    .select('*')
    .eq('trade_id', transactionData.trade_id)
    .single();

  if (tradeError) throw tradeError;

  return { transaction: data, trade: tradeData };
};

const deleteTransaction = async (client: SupabaseClient, id: string) => {
  // First get the trade_id before deleting
  const { data: transactionData, error: fetchError } = await client
    .from('transactions')
    .select('trade_id')
    .eq('id', id)
    .single();

  if (fetchError) throw fetchError;

  const { error: deleteError } = await client
    .from('transactions')
    .delete()
    .eq('id', id);

  if (deleteError) throw deleteError;

  // Get the updated trade data
  const { data: tradeData, error: tradeError } = await client
    .from('trades')
    .select('*')
    .eq('trade_id', transactionData.trade_id)
    .single();

  if (tradeError) throw tradeError;

  return { success: true, trade: tradeData };
};

serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    console.log('Creating Supabase client...')
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    console.log('Parsing request body...')
    const body = await req.json() as RequestBody

    // Validate request body
    if (!body.action) {
      throw new Error('Missing action in request body')
    }
    if (!body.transactionId) {
      throw new Error('Missing transactionId in request body')
    }
    if (body.action === 'updateTransaction' && !body.data) {
      throw new Error('Missing data in request body for update action')
    }

    console.log('Request:', { action: body.action, transactionId: body.transactionId, data: body.data })

    switch (body.action) {
      case 'updateTransaction': {
        if (!body.data) {
          throw new Error('Missing transaction data')
        }
        console.log('Updating transaction:', body.transactionId)
        const { transaction, trade } = await updateTransaction(supabaseClient, body.transactionId, body.data)
        console.log('Transaction updated successfully:', transaction)
        return new Response(
          JSON.stringify({
            transaction,
            trade
          }),
          {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
            status: 200,
          }
        )
      }

      case 'deleteTransaction': {
        console.log('Deleting transaction:', body.transactionId)
        const { success, trade } = await deleteTransaction(supabaseClient, body.transactionId)
        console.log('Transaction deleted, fetching updated trade data...')
        console.log('Successfully fetched updated trade:', trade)
        return new Response(
          JSON.stringify({
            success,
            trade
          }),
          {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
            status: 200,
          }
        )
      }

      default:
        console.error('Invalid action:', body.action)
        throw new Error('Invalid action')
    }
  } catch (error) {
    console.error('Error processing request:', error)
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : 'Unknown error' }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 400,
      }
    )
  }
}) 