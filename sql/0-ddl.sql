-- Drop existing tables if they exist
DROP TABLE IF EXISTS Recommendations CASCADE;
DROP TABLE IF EXISTS Community_Analysis CASCADE;
DROP TABLE IF EXISTS Community_Reactions CASCADE;
DROP TABLE IF EXISTS Community_Analysis_Coins CASCADE;
DROP TABLE IF EXISTS Coin_OHLCV CASCADE;
DROP TABLE IF EXISTS Coins CASCADE;

CREATE SCHEMA partman;
CREATE EXTENSION pg_partman WITH SCHEMA partman;

-- 1. 코인 정보 테이블
CREATE TABLE public.Coins (
    coin_id SERIAL PRIMARY KEY,
    coin_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    market_cap BIGINT, -- 시가총액
    total_supply BIGINT, -- 총 유통량
    circulating_supply BIGINT, -- 현재 유통량
    ranking INT, -- 랭킹
    market_cap_change_24h FLOAT, -- 24시간 시가총액 변화 (%)
    launch_date DATE,
    description TEXT -- 코인 설명
);

-- 2. OHLCV 데이터 테이블
CREATE TABLE public.Coin_OHLCV (
    coin_id INT REFERENCES Coins(coin_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(20, 8) NOT NULL,
    PRIMARY KEY (coin_id, timestamp)  -- PRIMARY KEY에 파티션 키 포함
) PARTITION BY RANGE (timestamp);

-- 3. 커뮤니티 반응 테이블
CREATE TABLE public.Community_Reactions (
    reaction_id UUID DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP NOT NULL,
    reaction_text TEXT NOT NULL,
    chat_name VARCHAR(255) NOT NULL,
    sender VARCHAR(255) NOT NULL,
    source VARCHAR(255) NOT NULL,
    PRIMARY KEY (reaction_id, timestamp),
    CONSTRAINT unique_reactions UNIQUE (timestamp, chat_name, sender)
) PARTITION BY RANGE (timestamp);


-- 4-1. 커뮤니티 분석 테이블
CREATE TABLE public.Community_Analysis (
    analysis_id SERIAL NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    reaction_id UUID NOT NULL,
    nouns TEXT[],           -- 명사를 배열로 저장
    adjectives TEXT[],      -- 형용사를 배열로 저장
    verbs TEXT[],           -- 동사를 배열로 저장
    interjections TEXT[],   -- 감탄사를 배열로 저장
    sentiment VARCHAR(10) CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    
    CONSTRAINT unique_reaction_timestamp UNIQUE (reaction_id, timestamp),
    FOREIGN KEY (reaction_id, timestamp) REFERENCES Community_Reactions(reaction_id, timestamp) ON DELETE CASCADE,
    PRIMARY KEY (analysis_id, timestamp) -- PRIMARY KEY에 timestamp 추가
) PARTITION BY RANGE (timestamp);

-- 4-2. 커뮤니티 분석과 코인 관계를 연결하는 교차 테이블
CREATE TABLE public.Community_Analysis_Coins (
    analysis_id INT,
    timestamp TIMESTAMP, -- timestamp 추가
    coin_id INT REFERENCES Coins(coin_id) ON DELETE CASCADE,
    PRIMARY KEY (analysis_id, coin_id),
    FOREIGN KEY (analysis_id, timestamp) REFERENCES Community_Analysis(analysis_id, timestamp) ON DELETE CASCADE
);


-- 5. 추천 및 알림 테이블
CREATE TABLE public.Recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    coin_id INT REFERENCES Coins(coin_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    reason TEXT NOT NULL
);

-- coin_id와 timestamp에 대한 복합 인덱스
CREATE INDEX idx_coin_ohlcv_coin_id_timestamp ON public.Coin_OHLCV (coin_id, timestamp);

-- timestamp에 대한 단일 인덱스
CREATE INDEX idx_coin_ohlcv_timestamp ON public.Coin_OHLCV (timestamp);

-- timestamp와 chat_name에 대한 복합 인덱스
CREATE INDEX idx_community_reactions_timestamp_chat_name ON public.Community_Reactions (timestamp, chat_name);

-- sender와 source에 대한 복합 인덱스
CREATE INDEX idx_community_reactions_sender_source ON public.Community_Reactions (sender, source);

-- MD5 해시값으로 인덱스 생성
CREATE INDEX idx_reaction_text_md5 ON public.Community_Reactions (md5(reaction_text));

-- reaction_id에 대한 인덱스
CREATE INDEX idx_community_analysis_reaction_id ON public.Community_Analysis (reaction_id);

-- coin_id와 timestamp에 대한 복합 인덱스
CREATE INDEX idx_recommendations_coin_id_timestamp ON public.Recommendations (coin_id, timestamp);

-- analysis_id와 coin_id에 대한 복합 인덱스
CREATE INDEX idx_community_analysis_coins_analysis_id_coin_id ON public.Community_Analysis_Coins (analysis_id, coin_id);

SELECT partman.create_parent(
	p_parent_table := 'public.coin_ohlcv',
	p_control := 'timestamp',
	p_type := 'range',
	p_interval := '1 day',
	p_premake := 1, 
	p_start_partition := (CURRENT_TIMESTAMP - '30 days'::interval)::text
);

SELECT partman.create_parent(
    p_parent_table := 'public.community_reactions',
    p_control := 'timestamp',
    p_type := 'range',
    p_interval := '1 day',  -- 하루 단위로 파티셔닝
    p_premake := 1,       -- 기본적으로 1개의 파티션 미리 생성
    p_start_partition := (CURRENT_TIMESTAMP - '30 days'::interval)::text  -- 30일 전부터 시작
);

SELECT partman.create_parent(
    p_parent_table := 'public.community_analysis',
    p_control := 'timestamp',
    p_type := 'range',
    p_interval := '1 day',  -- 하루 단위로 파티션 생성
    p_premake := 1,        -- 기본적으로 1개의 파티션 미리 생성
    p_start_partition := (CURRENT_TIMESTAMP - '30 days'::interval)::text -- 30일 전부터 시작
);

update partman.part_config
   set infinite_time_partitions = true,
       retention = '3 months',
       retention_keep_table = false
 where parent_table = 'public.coin_ohlcv'; 

update partman.part_config
   set infinite_time_partitions = true,
       retention = '3 months',
       retention_keep_table = false
 where parent_table = 'public.community_reactions'; 

UPDATE partman.part_config
SET infinite_time_partitions = true,
    retention = '3 months',
    retention_keep_table = false
WHERE parent_table = 'public.community_analysis';

SELECT cron.schedule('auto partitioning', '0 23 * * *', $$CALL partman.run_maintenance_proc()$$);

