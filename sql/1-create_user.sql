CREATE ROLE data_collector WITH LOGIN PASSWORD 'data_collector!';
CREATE ROLE data_scheduler WITH LOGIN PASSWORD 'data_scheduler!';
CREATE ROLE end_user WITH LOGIN PASSWORD 'end_user!';

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO db2024;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO db2024;
GRANT CONNECT ON DATABASE coinsight TO db2024;

-- 데이터베이스 접근 권한 부여
GRANT CONNECT ON DATABASE coinsight TO data_collector;
GRANT USAGE ON SCHEMA public TO data_collector;
GRANT SELECT, INSERT ON TABLE coins, Coin_OHLCV, Community_Reactions TO data_collector;

GRANT CONNECT ON DATABASE coinsight TO data_scheduler;
GRANT USAGE ON SCHEMA public TO data_scheduler;
GRANT SELECT ON TABLE Coin_OHLCV, Community_Reactions TO data_scheduler;

GRANT CONNECT ON DATABASE coinsight TO end_user;
GRANT USAGE ON SCHEMA public TO end_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO end_user;


-- public 스키마 내에서 테이블을 생성할 수 있는 권한을 부여
GRANT CREATE ON SCHEMA public TO data_collector;