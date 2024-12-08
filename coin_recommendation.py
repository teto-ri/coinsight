import logging
from datetime import datetime, timedelta
from psycopg2.extras import execute_values

from db_connector import get_db_connection

import logging
from logging.handlers import RotatingFileHandler

# Rotating File Handler 설정
log_file_handler = RotatingFileHandler(
    "log/coin_recommendation.log",  # 로그 파일 이름
    maxBytes=5 * 1024 * 1024,  # 파일 최대 크기 (5MB)
    backupCount=5  # 최대 보관 파일 수 (최대 5개)
)
log_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log_file_handler.setLevel(logging.INFO)

# Logging 설정
logging.basicConfig(
    level=logging.INFO,
    handlers=[log_file_handler]
)

# 코인 언급량을 날짜별로 계산
def calculate_coin_mentions(conn, start_date, end_date):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT coin_id, COUNT(*) 
            FROM Community_Analysis_Coins
            WHERE timestamp BETWEEN %s AND %s
            GROUP BY coin_id;
        """, (start_date, end_date))
        
        return cur.fetchall()  # [(coin_id, mention_count), ...]

# 슬라이딩 윈도우로 언급량 증가를 찾는 함수
def calculate_increase_in_mentions_with_sliding_window(conn, start_date, end_date):
    increased_mentions = {}

    current_date = start_date
    while current_date < end_date:
        # 슬라이딩 윈도우: 3일 간격으로 언급량을 비교
        previous_date = current_date - timedelta(days=3)
        next_date = current_date + timedelta(days=3)

        current_mentions = {coin_id: count for coin_id, count in calculate_coin_mentions(conn, current_date, next_date)}
        previous_mentions = {coin_id: count for coin_id, count in calculate_coin_mentions(conn, previous_date, current_date)}

        # 언급량 증가 계산
        for coin_id, current_count in current_mentions.items():
            previous_count = previous_mentions.get(coin_id, 0)
            if current_count > previous_count:  # 증가량이 있을 때만
                increase = current_count - previous_count
                if coin_id in increased_mentions:
                    increased_mentions[coin_id].append((current_date, increase))
                else:
                    increased_mentions[coin_id] = [(current_date, increase)]

        current_date += timedelta(days=1)  # 하루씩 슬라이딩

    return increased_mentions  # {coin_id: [(date, increase), ...]}

def calculate_decrease_in_mentions_with_sliding_window(conn, start_date, end_date):
    decreased_mentions = {}

    current_date = start_date
    while current_date < end_date:
        # 슬라이딩 윈도우: 3일 간격으로 언급량을 비교
        previous_date = current_date - timedelta(days=3)
        next_date = current_date + timedelta(days=3)

        current_mentions = {coin_id: count for coin_id, count in calculate_coin_mentions(conn, current_date, next_date)}
        previous_mentions = {coin_id: count for coin_id, count in calculate_coin_mentions(conn, previous_date, current_date)}

        # 언급량 감소 계산
        for coin_id, current_count in current_mentions.items():
            previous_count = previous_mentions.get(coin_id, 0)
            if current_count < previous_count:  # 감소량이 있을 때만
                decrease = previous_count - current_count
                if coin_id in decreased_mentions:
                    decreased_mentions[coin_id].append((current_date, decrease))
                else:
                    decreased_mentions[coin_id] = [(current_date, decrease)]

        current_date += timedelta(days=1)  # 하루씩 슬라이딩

    return decreased_mentions  # {coin_id: [(date, decrease), ...]}


# 추천 테이블에 저장
def save_recommendations(conn, increased_mentions, decreased_mentions):
    with conn.cursor() as cur:
        data_to_insert = []
        
        # 증가한 언급량에 대한 추천 저장
        for coin_id, increase_data in increased_mentions.items():
            for date, increase in increase_data:
                data_to_insert.append((coin_id, date, f"Increase {increase} in mentions"))

        # 감소한 언급량에 대한 패널티 저장
        for coin_id, decrease_data in decreased_mentions.items():
            for date, decrease in decrease_data:
                data_to_insert.append((coin_id, date, f"Decrease {decrease} in mentions"))

        if data_to_insert:
            execute_values(
                cur,
                """
                INSERT INTO Recommendations (coin_id, timestamp, reason)
                VALUES %s;
                """,
                data_to_insert
            )
            conn.commit()

# 배치 처리 메인 함수
def process_recommendations():
    try:
        # PostgreSQL 연결
        conn = get_db_connection("data_scheduler")

        # 오늘 날짜 및 계산할 마지막 날짜 설정
        today = datetime.now()
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)

        # 슬라이딩 윈도우로 언급량 증가를 계산
        increased_mentions = calculate_increase_in_mentions_with_sliding_window(conn, start_date - timedelta(days=90), today)
        decreased_mentions = calculate_decrease_in_mentions_with_sliding_window(conn, start_date - timedelta(days=90), today)

        # 증가량이 있는 코인에 대해 추천 저장
        if increased_mentions or decreased_mentions:
            save_recommendations(conn, increased_mentions, decreased_mentions)
            logging.info(f"Processed {len(increased_mentions)} coin recommendations and {len(decreased_mentions)} coin penalties.")
        else:
            logging.info("No significant changes in coin mentions.")
        
    except Exception as e:
        logging.error(f"Error during recommendation processing: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    process_recommendations()