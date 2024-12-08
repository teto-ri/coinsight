-- data_collector가 Coin_OHLCV에 INSERT 할 수 있는지 테스트
SET ROLE data_collector;

INSERT INTO Coins (coin_name, symbol, market_cap, launch_date)
VALUES ('Bitcoin', 'BTC', 1000000000, '2009-01-03');

INSERT INTO Coin_OHLCV (coin_id, timestamp, open, high, low, close, volume)
VALUES (1, '2024-12-08 00:00:00', 50000, 52000, 49000, 51000, 1000);

SET ROLE db2024;
-- 삽입 후 삭제해서 원상복구
DELETE FROM Coins where coin_id = 1;
DELETE FROM Coin_OHLCV WHERE coin_id = 1 AND timestamp = '2024-12-08 00:00:00';

SET ROLE data_collector;

-- 1. Community_Reactions 테이블에 데이터 삽입
INSERT INTO public.Community_Reactions (timestamp, reaction_text, chat_name, sender, source)
VALUES 
    (CURRENT_TIMESTAMP, 'Great project!', 'Crypto Chat', 'User123', 'Telegram');

-- 2. 삽입된 데이터 조회
SELECT * 
FROM public.Community_Reactions;

-- 3. 삽입된 데이터 삭제
SET ROLE db2024;

DELETE FROM public.Community_Reactions 
WHERE reaction_text = 'Great project!' AND sender = 'User123';

-- 1. Community_Reactions에 데이터가 있어야 테스트 가능하므로, 우선 반응 데이터 생성
SET ROLE data_collector;

INSERT INTO public.Community_Reactions (timestamp, reaction_text, chat_name, sender, source)
VALUES 
    (CURRENT_TIMESTAMP, 'Good insights', 'Crypto Analysis', 'User456', 'Reddit');

-- data_scheduler로 역할 변경   
SET ROLE data_scheduler;

-- 2. Community_Analysis 테이블에 데이터 삽입
INSERT INTO public.Community_Analysis (timestamp, reaction_id, analysis_text, sentiment)
SELECT 
    timestamp, reaction_id, 'This is positive feedback', 'positive'
FROM 
    public.Community_Reactions
WHERE 
    reaction_text = 'Good insights';

-- 3. 삽입된 데이터 조회
SELECT * 
FROM public.Community_Analysis;


SET ROLE db2024;

-- 4. 삽입된 데이터 삭제
DELETE FROM public.Community_Analysis 
WHERE analysis_text = 'This is positive feedback';

-- 외래 키 테스트를 위해 반응 데이터 삭제
DELETE FROM public.Community_Reactions 
WHERE reaction_text = 'Good insights';


-- end_user가 Coin_OHLCV 테이블에서 조회할 수 있는지 테스트
SET ROLE end_user;
SELECT * FROM Coin_OHLCV WHERE coin_id = 1;

-- end_user가 Coin_OHLCV 테이블에 데이터를 삽입할 수 없는지 테스트
INSERT INTO Coin_OHLCV (coin_id, timestamp, open, high, low, close, volume)
VALUES (1, CURRENT_TIMESTAMP, 50000.0, 51000.0, 49000.0, 50500.0, 1000);  -- 오류 발생

-- end_user가 Community_Reactions 테이블에서 조회할 수 있는지 테스트
SELECT * FROM Community_Reactions;
