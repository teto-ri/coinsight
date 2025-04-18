import requests
import asyncio
import aiohttp
from db_connector import asycn_get_db_connection
from psycopg2.extras import execute_batch
import time
from datetime import datetime

import logging
from logging.handlers import RotatingFileHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

#Rotating File Handler 설정
log_file_handler = RotatingFileHandler(
    "log/coin_ohlcv_collector.log",  # 로그 파일 이름
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

scheduler = AsyncIOScheduler()


# Upbit API에서 KRW 마켓만 필터링
def get_krw_pairs():
    url = "https://api.upbit.com/v1/market/all"
    response = requests.get(url)
    data = response.json()

    krw_pairs = [(coin['market'], coin['korean_name']) for coin in data if coin['market'].startswith('KRW-')]
    return krw_pairs

async def get_candles(market, count=200, to=None):
    url = "https://api.upbit.com/v1/candles/minutes/60"
    params = {
        'market': market,
        'count': count
    }
    if to:
        params['to'] = to
    headers = {"accept": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as response:
            return await response.json()

async def get_data_from_range(market, start_date, end_date):
    all_data = []
    current_to = start_date
    while True:
        # 200개의 캔들을 가져옴
        candles = await get_candles(market, count=200, to=current_to)
        
        if not candles:
            break  # 더 이상 데이터가 없으면 종료

        # 최신 데이터의 timestamp (다음 요청에 사용될 'to')
        current_to = candles[-1]['candle_date_time_kst']
        all_data.extend(candles)

        start_date = candles[0]['candle_date_time_kst']
        logging.info(f"Fetching data from {current_to} to {start_date}")
                
        if current_to <= end_date or len(candles) < 200:
            logging.info("Reached the end of available data or end date.")
            break

        await asyncio.sleep(0.5)
    return all_data

# Asynchronous Database Insert Function (with asyncpg)
async def insert_ohlcv_data(conn, coin_id, candles):
    query = """
        INSERT INTO public.Coin_OHLCV (coin_id, timestamp, open, high, low, close, volume)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (coin_id, timestamp) DO NOTHING;
    """
    ohlcv_data = []
    for candle in candles:
        try:
            volume = round(candle['candle_acc_trade_volume'], 8)
            
            # 크기 조정 (필요 시)
            if volume > 1e12:  # 10^12 이상인 경우
                volume /= 1_000_000
            
            rounded_data = (
                coin_id,
                datetime.strptime(candle['candle_date_time_kst'].replace("T", " "), "%Y-%m-%d %H:%M:%S"),
                round(candle['opening_price'], 8),
                round(candle['high_price'], 8),
                round(candle['low_price'], 8),
                round(candle['trade_price'], 8),
                volume
            )
            ohlcv_data.append(rounded_data)
        except Exception as e:
            logging.error(f"Error processing candle: {candle}, Error: {e}")
    # Batch insert in asyncpg
    await conn.executemany(query, ohlcv_data)

# Asynchronous Function to Update Latest Data
async def update_latest_data():
    conn = await asycn_get_db_connection("data_collector")
    
    krw_pairs = get_krw_pairs()

    for market, coin_name in krw_pairs:
        symbol = market.split('-')[1]
        logging.info(f"Updating data for {coin_name} ({market})")
        candles = await get_candles(market, count=10)
    
        # Get coin_id (adjust accordingly for asyncpg or other async query method)
        coin_id = await conn.fetchval("SELECT coin_id FROM public.Coins WHERE symbol = $1", symbol)

        if coin_id:
            await insert_ohlcv_data(conn, coin_id, candles)
        await asyncio.sleep(0.5)
    await conn.close()

async def init_ohlcv():
    conn = await asycn_get_db_connection("data_collector")

    krw_pairs = get_krw_pairs()

    for market, coin_name in krw_pairs:
        symbol = market.split('-')[1]
        coin_id = await conn.fetchval("SELECT coin_id FROM public.Coins WHERE symbol = $1", symbol)
        
        if not coin_id:
            logging.info(f"Skipping {coin_name} ({market})")
            continue
        
        logging.info(f"Inserting data for {coin_name} ({market})")
        
        end_date = "2024-10-01T00:00:00"
        start_date = "2024-12-08T00:00:00"
        
        candles = await get_data_from_range(market, start_date, end_date)
        logging.info(len(candles))
        await insert_ohlcv_data(conn, coin_id, candles)

        # Optional sleep if necessary, but it's better to use a small delay for rate-limiting.
        await asyncio.sleep(0.5)

    await conn.close()
    
if __name__ == "__main__":
    #asyncio.run(init_ohlcv())
    asyncio.run(update_latest_data())
    # scheduler.add_job(update_latest_data, 'cron', minute='1')
    # scheduler.start()
    # try:
    #     asyncio.get_event_loop().run_forever()
    # except (KeyboardInterrupt, SystemExit):
    #     logging.info("Shutting down scheduler.")
    #     scheduler.shutdown()
