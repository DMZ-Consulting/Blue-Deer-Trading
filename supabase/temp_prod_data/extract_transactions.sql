\copy (
    SELECT t.* FROM public.transactions t
    JOIN public.trades tr ON t.trade_id = tr.trade_id
    WHERE tr.created_at >= NOW() - INTERVAL '30 days'
    ORDER BY t.created_at DESC 
    LIMIT 200
) TO 'transactions_sample.csv' WITH CSV HEADER;
