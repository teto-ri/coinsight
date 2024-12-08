select * from partman.show_partitions('public.coin_ohlcv');

SELECT cron.schedule('auto partitioning', '0 23 * * *', $$CALL partman.run_maintenance_proc()$$);


SELECT cron.schedule('auto partitioning', '* * * * *', 
     $$CALL partman.run_maintenance_proc()$$);

SELECT cron.schedule('Refresh DailyOHLCV every minute', '* * * * *', 
    'REFRESH MATERIALIZED VIEW public.DailyOHLCV');
    
DELETE FROM cron.job WHERE jobid = 11;


DELETE FROM public.recommendations;



SELECT c.coin_name,
       SUM(CASE 
               WHEN r.reason ILIKE '%Increase%' THEN CAST(REGEXP_REPLACE(r.reason, '[^0-9]', '', 'g') AS INTEGER) 
               ELSE 0 
           END) AS increase_mentions,  -- 증가량
       SUM(CASE 
               WHEN r.reason ILIKE '%Decrease%' THEN CAST(REGEXP_REPLACE(r.reason, '[^0-9]', '', 'g') AS INTEGER) 
               ELSE 0 
           END) AS decrease_mentions,  -- 감소량
       SUM(CASE 
               WHEN r.reason ILIKE '%Increase%' THEN CAST(REGEXP_REPLACE(r.reason, '[^0-9]', '', 'g') AS INTEGER) 
               ELSE 0 
           END) - 
       SUM(CASE 
               WHEN r.reason ILIKE '%Decrease%' THEN CAST(REGEXP_REPLACE(r.reason, '[^0-9]', '', 'g') AS INTEGER) 
               ELSE 0 
           END) AS net_mentions,  -- 증가량과 감소량의 차이
       MIN(r."timestamp") AS start_date,
       MAX(r."timestamp") AS end_date,
       CONCAT(MIN(r."timestamp"), ' to ', MAX(r."timestamp")) AS mention_period,
       ROW_NUMBER() OVER (ORDER BY 
           SUM(CASE 
                   WHEN r.reason ILIKE '%Increase%' THEN CAST(REGEXP_REPLACE(r.reason, '[^0-9]', '', 'g') AS INTEGER) 
                   ELSE 0 
               END) - 
           SUM(CASE 
                   WHEN r.reason ILIKE '%Decrease%' THEN CAST(REGEXP_REPLACE(r.reason, '[^0-9]', '', 'g') AS INTEGER) 
                   ELSE 0 
               END) DESC,  -- 첫 번째 정렬 기준: net_mentions (증가량 - 감소량)
           SUM(CASE 
                   WHEN r.reason ILIKE '%Increase%' THEN CAST(REGEXP_REPLACE(r.reason, '[^0-9]', '', 'g') AS INTEGER) 
                   ELSE 0 
               END) DESC,  -- 두 번째 정렬 기준: increase_mentions
           c.market_cap DESC) AS recommend_ranking  -- 세 번째 정렬 기준: market_cap
FROM recommendations r
JOIN Coins c ON r.coin_id = c.coin_id
GROUP BY c.coin_name, c.market_cap
ORDER BY net_mentions DESC, increase_mentions DESC, c.market_cap DESC;



