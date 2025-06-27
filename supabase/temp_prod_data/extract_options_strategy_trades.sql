\copy (
    SELECT * FROM public.options_strategy_trades 
    WHERE legs IS NOT NULL AND legs != ''
    ORDER BY created_at DESC 
    LIMIT 20
) TO 'options_strategy_trades_sample.csv' WITH CSV HEADER;
