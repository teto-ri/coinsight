import requests
import schedule
import time
import os
from dotenv import load_dotenv
from db_connector import get_db_connection
from util import translate_text
import logging
from logging.handlers import RotatingFileHandler

#Rotating File Handler 설정
log_file_handler = RotatingFileHandler(
    "log/coin_metadata_collector.log",  # 로그 파일 이름
    maxBytes=5 * 1024 * 1024,  # 파일 최대 크기 (5MB)
    backupCount=5  # 최대 보관 파일 수 (최대 5개)
)
log_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log_file_handler.setLevel(logging.INFO)

# Logging 설정
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        log_file_handler
    ]
)
load_dotenv()

# Upbit API에서 KRW 마켓만 필터링
def get_krw_pairs():
    url = "https://api.upbit.com/v1/market/all"
    response = requests.get(url)
    data = response.json()

    krw_pairs = [(coin['market'], coin['korean_name']) for coin in data if coin['market'].startswith('KRW-')]
    return krw_pairs

def get_all_coins_from_paprika():
    url = "https://api.coinpaprika.com/v1/tickers?quotes=KRW"
    response = requests.get(url)
    data = response.json()
    return data

# PostgreSQL에서 코인 정보 확인 (이미 DB에 존재하는지 확인)
def check_coin_in_db(cursor, coin_symbol):
    query = "SELECT 1 FROM Coins WHERE symbol = %s LIMIT 1;"
    cursor.execute(query, (coin_symbol,))
    return cursor.fetchone() is not None

# CoinMarketCap API에서 코인 정보 조회
def get_coin_info(coin_symbol, api_key):
    url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/info"
    params = {'symbol': coin_symbol}
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }
    response = requests.get(url, params=params, headers=headers)
    data = response.json()

    if "data" in data:
        coin_data = data["data"].get(coin_symbol, {})
        coin_info = {
            'name': coin_data.get('name', ''),
            'symbol': coin_symbol,
            'market_cap': coin_data.get('market_cap', 0),
            'launch_date': coin_data.get('date_added', '1900-01-01'),
            'description': coin_data.get('description', '')
        }
        return coin_info
    return None

# PostgreSQL에 데이터 저장 (갱신 가능)
def insert_or_update_coin_info(cursor, coin_info, korean_name):
    try:
        insert_query = """
        INSERT INTO Coins (coin_name, symbol, market_cap, launch_date, description)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (symbol) DO UPDATE
        SET
            coin_name = EXCLUDED.coin_name,
            symbol = EXCLUDED.symbol,
            market_cap = EXCLUDED.market_cap,
            launch_date = EXCLUDED.launch_date,
            description = EXCLUDED.description;
        """
        cursor.execute(insert_query, (
            korean_name, coin_info['symbol'], coin_info['market_cap'],
            coin_info['launch_date'], translate_text(coin_info['description'])
        ))
        logging.info(f"Inserted or updated {coin_info['name']} ({coin_info['symbol']})")
    except Exception as e:
        logging.error(f"Error inserting/updating coin: {e}")

# PostgreSQL에 데이터 업데이트 (필요한 필드만)
def update_coin_info(cursor, coin_info):
    try:
        # 필요한 필드만 업데이트
        update_query = """
        UPDATE Coins
        SET 
            market_cap = %s,
            total_supply = %s,
            circulating_supply = %s,
            ranking = %s,
            market_cap_change_24h = %s
        WHERE symbol = %s;
        """
        cursor.execute(update_query, (
            coin_info['market_cap'], coin_info['total_supply'], coin_info['circulating_supply'],
            coin_info['ranking'], coin_info['market_cap_change_24h'], coin_info['symbol']
        ))
        logging.info(f"Updated {coin_info['symbol']} details.")
    except Exception as e:
        logging.error(f"Error updating coin details: {e}")

# 코인 정보만 갱신하는 함수
def update_coin_details():
    conn = get_db_connection("data_collector") 
    cursor = conn.cursor()

    krw_pairs = get_krw_pairs()
    logging.info(f"Found {len(krw_pairs)} KRW pairs.")
    coin_details = get_all_coins_from_paprika()
    logging.info(f"Found {len(coin_details)} coins from CoinPaprika.")

    for pair in krw_pairs:
        coin_symbol = pair[0].split('-')[1]  # KRW-BTC에서 BTC를 추출

        if check_coin_in_db(cursor, coin_symbol):
            logging.info(f"{coin_symbol} already exists in the database, updating details...")
            for coin_detail in coin_details:
                if coin_detail['symbol'] == coin_symbol:
                    coin_info = {
                        'symbol': coin_symbol,
                        'market_cap': coin_detail['quotes']['KRW']['market_cap'],
                        'total_supply': coin_detail['max_supply'],
                        'circulating_supply': coin_detail['total_supply'],
                        'ranking': coin_detail['rank'],
                        'market_cap_change_24h': coin_detail['quotes']['KRW']['market_cap_change_24h']
                    }
                    update_coin_info(cursor, coin_info)
                    break
        else:
            logging.info(f"{coin_symbol} does not exist in the database, skipping...")

        time.sleep(0.1)  # 딜레이 추가
    conn.commit()
    cursor.close()
    conn.close()

# 초기 데이터 수집 함수
def init_coin():
    conn = get_db_connection("data_collector") 
    cursor = conn.cursor()
    krw_pairs = get_krw_pairs()
    logging.info(f"Found {len(krw_pairs)} KRW pairs.")
    coin_details = get_all_coins_from_paprika()
    logging.info(f"Found {len(coin_details)} coins from CoinPaprika.")
    
    api_key = os.getenv("CMC_API_KEY_COLLECTOR")

    for pair in krw_pairs:
        coin_symbol = pair[0].split('-')[1]  # KRW-BTC에서 BTC를 추출

        if check_coin_in_db(cursor, coin_symbol):
            logging.info(f"{coin_symbol} already exists in the database, skipping CoinMarketCap API call.")
        else:
            logging.info(f"Getting info for {coin_symbol} from CoinMarketCap...")
            coin_info = get_coin_info(coin_symbol, api_key)

            if coin_info:
                insert_or_update_coin_info(cursor, coin_info, pair[1])
        time.sleep(2)  # 딜레이 추가
    conn.commit()
    cursor.close()
    conn.close()

# 스케줄링: 매일 자정에 실행
def schedule_jobs():
    schedule.every().day.at("00:00").do(init_coin)  # init_coin() 함수는 자정에 실행
    schedule.every().hour.do(update_coin_details)  # update_coin_details() 함수는 시간마다 실행

    while True:
        schedule.run_pending()  # 스케줄된 작업 실행
        time.sleep(1)  # 1초 대기

if __name__ == "__main__":
    # # init_coin()  # 메인 함수 실행
    update_coin_details()  # 코인 정보 갱신 함수 실행
    # schedule_jobs()  # 스케줄링 실행