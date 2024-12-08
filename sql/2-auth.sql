-- 권한 설정 (Authorization)

-- Coins: 관리자만 수정 가능, 모든 사용자가 조회 가능, 수집기는 삽입 가능
REVOKE ALL ON TABLE Coins FROM PUBLIC;
GRANT SELECT ON TABLE Coins TO PUBLIC;
GRANT INSERT ON TABLE Coins TO data_collector;
GRANT UPDATE ON TABLE Coins TO data_collector;

GRANT USAGE, SELECT ON SEQUENCE coins_coin_id_seq TO data_collector;

-- Coin_OHLCV: 모든 사용자가 조회 가능, 관리자만 수정 가능; 수집기는 삽입 가능
REVOKE ALL ON TABLE Coin_OHLCV FROM PUBLIC;
GRANT SELECT ON TABLE Coin_OHLCV TO PUBLIC;
GRANT INSERT ON TABLE Coin_OHLCV TO data_collector;

-- Community_Reactions: 모든 사용자가 조회 가능, 관리자만 수정 가능; 수집기는 삽입 가능
REVOKE ALL ON TABLE Community_Reactions FROM PUBLIC;
GRANT SELECT ON TABLE Community_Reactions TO PUBLIC;
GRANT INSERT ON TABLE Community_Reactions TO data_collector;

-- Community_Analysis: 관리자만 수정 가능, 모든 사용자가 조회 가능; 수집기는 조회 가능, 스케줄러 삽입 가능
REVOKE ALL ON TABLE Community_Analysis FROM PUBLIC;
GRANT SELECT ON TABLE Community_Analysis TO PUBLIC;
GRANT SELECT ON TABLE Community_Analysis TO data_collector;

GRANT INSERT ON TABLE Community_Analysis TO data_scheduler;
GRANT UPDATE ON TABLE Community_Analysis TO data_scheduler;

GRANT USAGE, SELECT ON SEQUENCE community_analysis_analysis_id_seq TO data_scheduler;

-- `Community_Analysis_Coins` 테이블에 대한 권한 설정
REVOKE ALL ON TABLE Community_Analysis_Coins FROM PUBLIC;
-- `data_collector`에게 조회 권한 부여
GRANT SELECT ON TABLE Community_Analysis_Coins TO data_collector;
-- `data_scheduler`에게 삽입 및 조회 권한 부여
GRANT SELECT, INSERT ON TABLE Community_Analysis_Coins TO data_scheduler;
GRANT UPDATE ON TABLE Community_Analysis_Coins TO data_scheduler;

-- Recommendations: 모든 사용자가 조회 가능, 관리자만 수정 가능; 수집기와 스케줄러는 조회 가능
REVOKE ALL ON TABLE Recommendations FROM PUBLIC;
GRANT SELECT ON TABLE Recommendations TO PUBLIC;
GRANT SELECT, INSERT ON TABLE Recommendations TO data_scheduler;

GRANT USAGE, SELECT ON SEQUENCE recommendations_recommendation_id_seq TO data_scheduler;


-- 데이터베이스 접근 권한 부여
GRANT CONNECT ON DATABASE coinsight TO data_collector;
GRANT USAGE ON SCHEMA public TO data_collector;
GRANT SELECT, INSERT ON TABLE Coin_OHLCV, Community_Reactions TO data_collector;

GRANT CONNECT ON DATABASE coinsight TO data_scheduler;
GRANT USAGE ON SCHEMA public TO data_scheduler;
GRANT SELECT ON TABLE Coin_OHLCV, Community_Reactions TO data_scheduler;

GRANT CONNECT ON DATABASE coinsight TO end_user;
GRANT USAGE ON SCHEMA public TO end_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO end_user;

-- 기본 권한 설정
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO PUBLIC;
