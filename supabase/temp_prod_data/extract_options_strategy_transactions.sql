\copy (
    SELECT ost.* FROM public.options_strategy_transactions ost
    JOIN public.options_strategy_trades ostrades ON ost.strategy_id = ostrades.strategy_id
    WHERE ostrades.legs IS NOT NULL AND ostrades.legs != ''
    ORDER BY ost.created_at DESC 
    LIMIT 100
) TO 'options_strategy_transactions_sample.csv' WITH CSV HEADER;
