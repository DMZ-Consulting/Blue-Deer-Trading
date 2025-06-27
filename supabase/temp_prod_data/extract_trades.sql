\copy (
    SELECT * FROM public.trades 
    WHERE created_at >= NOW() - INTERVAL '30 days'
    ORDER BY created_at DESC 
    LIMIT 50
) TO 'trades_sample.csv' WITH CSV HEADER;
