-- 6. 하루 전체의 시고저총을 계산하여 제공하는 뷰
CREATE MATERIALIZED VIEW public.DailyOHLCV AS
WITH RankedOHLCV AS (
    SELECT 
        o.coin_id,
        o.open,
        o.close,
        o.high,
        o.low,
        o.volume,
        DATE(o.timestamp) AS date,
        ROW_NUMBER() OVER (PARTITION BY o.coin_id, DATE(o.timestamp) ORDER BY o.timestamp ASC) AS row_asc,
        ROW_NUMBER() OVER (PARTITION BY o.coin_id, DATE(o.timestamp) ORDER BY o.timestamp DESC) AS row_desc
    FROM 
        public.Coin_OHLCV o
)
SELECT 
    c.coin_id,
    c.coin_name,
    c.symbol,
    -- 하루의 시가: 해당 날짜의 첫 번째 OHLCV의 open 값
    (SELECT r.open 
     FROM RankedOHLCV r 
     WHERE r.coin_id = c.coin_id 
       AND r.date = DATE(MAX(o.timestamp)) 
       AND r.row_asc = 1) AS open,
    -- 하루의 고가: 해당 날짜의 최고 high 값
    MAX(o.high) AS high,
    -- 하루의 저가: 해당 날짜의 최저 low 값
    MIN(o.low) AS low,
    -- 하루의 종가: 해당 날짜의 마지막 OHLCV의 close 값
    (SELECT r.close 
     FROM RankedOHLCV r 
     WHERE r.coin_id = c.coin_id 
       AND r.date = DATE(MAX(o.timestamp)) 
       AND r.row_desc = 1) AS close,
    -- 하루의 총 거래량: 해당 날짜의 거래량 합산
    SUM(o.volume) AS volume,
    -- 해당 날짜의 timestamp (최신 OHLCV 데이터의 timestamp)
    DATE(MAX(o.timestamp)) AS date
FROM 
    public.Coins c
JOIN 
    public.Coin_OHLCV o ON c.coin_id = o.coin_id
WHERE 
    DATE(o.timestamp) = CURRENT_DATE  -- 최근 하루 데이터만 필터링
GROUP BY 
    c.coin_id, c.coin_name, c.symbol, DATE(o.timestamp)
ORDER BY 
    DATE(MAX(o.timestamp)) DESC;

SELECT cron.schedule('Refresh DailyOHLCV every hour', '0 * * * *', 
    'REFRESH MATERIALIZED VIEW public.DailyOHLCV');

CREATE VIEW recommendation_view AS
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