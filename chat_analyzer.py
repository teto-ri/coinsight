from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import pandas as pd
import psycopg2
from konlpy.tag import Okt
from psycopg2.extras import execute_values
import time
from apscheduler.schedulers.background import BackgroundScheduler
from db_connector import get_db_connection
import re

import logging
from logging.handlers import RotatingFileHandler

#Rotating File Handler 설정
log_file_handler = RotatingFileHandler(
    "log/coin_analyzer.log",  # 로그 파일 이름
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

# 모델 로드 및 설정
device = torch.device('cpu')  # CPU에서 실행

# KR-FinBert-SC 모델과 토크나이저 로드
logging.info("Loading model and tokenizer...")
tokenizer = AutoTokenizer.from_pretrained('snunlp/KR-FinBert-SC')
model = AutoModelForSequenceClassification.from_pretrained('snunlp/KR-FinBert-SC').to(device)

# 모델을 'half-precision' (float16)으로 변환하여 메모리 최적화
model = model.half()  # 모델을 float16으로 변환 (가능한 경우)
logging.info("Model loaded and converted to half-precision.")

# 형태소 분석 함수 (Okt 사용)
def analyze_text(reaction_text):
    okt = Okt()
    
    # 명사 추출
    nouns = okt.nouns(reaction_text)
    
    # 형태소 분석 후 명사, 형용사, 동사 추출
    pos_tags = okt.pos(reaction_text)
    adjectives = [word for word, tag in pos_tags if tag == 'Adjective']
    verbs = [word for word, tag in pos_tags if tag == 'Verb']
    interjections = [word for word, tag in pos_tags if tag == 'Exclamation']
    
    return nouns, adjectives, verbs, interjections

# 감정 분석 함수
def analyze_sentiment(texts):
    labels = ['positive', 'neutral', 'negative']
    inputs = tokenizer(texts, return_tensors='pt', truncation=True, padding=True, max_length=512).to(device)
    
    with torch.no_grad():
        outputs = model(**inputs)
        
    logits = outputs.logits
    predicted_classes = torch.argmax(logits, dim=-1).cpu().numpy()
    predicted_sentiments = [labels[predicted_class] for predicted_class in predicted_classes]
    return predicted_sentiments

def analyze_and_store_morphological_data():
    logging.info("Starting morphological analysis and data storage...")
    
    # DB 연결
    conn = get_db_connection("data_scheduler")
    cur = conn.cursor()
    logging.info("Database connection established.")

    # 최근 커뮤니티 반응 조회
    cur.execute(""" 
        SELECT reaction_id, timestamp, reaction_text, chat_name 
        FROM public.Community_Reactions
        WHERE timestamp > NOW() - INTERVAL '1 month'
        AND reaction_id NOT IN (
            SELECT DISTINCT reaction_id FROM public.Community_Analysis
        );  -- 이미 분석된 데이터를 제외
    """)
    reactions = cur.fetchall()
    logging.info(f"Fetched {len(reactions)} reactions for morphological analysis.")

    # 분석 결과를 저장할 데이터 준비
    analysis_data = []
    batch_size = 1000

    for idx, reaction in enumerate(reactions):
        reaction_id, timestamp, reaction_text, chat_name = reaction
        nouns, adjectives, verbs, interjections = analyze_text(reaction_text)
        
        # 형태소 분석 결과 저장 준비
        analysis_data.append((timestamp, reaction_id, nouns, adjectives, verbs, interjections))

        # 배치 크기에 도달하면 삽입
        if (idx + 1) % batch_size == 0 or (idx + 1) == len(reactions):
            logging.info(f"Inserting morphological data for batch {idx + 1}...")
            execute_values(cur, """
                INSERT INTO public.Community_Analysis (timestamp, reaction_id, nouns, adjectives, verbs, interjections)
                VALUES %s
                ON CONFLICT (reaction_id, timestamp) DO NOTHING;
            """, analysis_data)

            conn.commit()
            analysis_data.clear()
            logging.info(f"Batch {idx + 1} inserted and committed.")

    cur.close()
    conn.close()
    logging.info("Morphological data storage complete.")

def analyze_and_store_sentiments():
    logging.info("Starting sentiment analysis and data storage...")
    
    # DB 연결
    conn = get_db_connection("data_scheduler")
    cur = conn.cursor()
    logging.info("Database connection established.")

    # 아직 감정 분석이 수행되지 않은 데이터를 조회
    cur.execute("""
        SELECT reaction_id, timestamp, reaction_text 
        FROM public.Community_Reactions
        WHERE reaction_id NOT IN (
            SELECT DISTINCT reaction_id 
            FROM public.Community_Analysis
            WHERE sentiment IS NOT NULL
        );
    """)
    reactions = cur.fetchall()
    logging.info(f"Fetched {len(reactions)} reactions for sentiment analysis.")

    batch_size = 100
    texts = []
    sentiment_data = []

    for idx, reaction in enumerate(reactions):
        reaction_id, timestamp, reaction_text = reaction
        texts.append(reaction_text)

        # 배치 크기에 도달하거나 마지막 데이터일 경우 처리
        if (idx + 1) % batch_size == 0 or (idx + 1) == len(reactions):
            sentiments = analyze_sentiment(texts)
            sentiment_data.extend(
                (timestamp, reaction_id, sentiment) for sentiment, (_, timestamp, reaction_id) in zip(sentiments, reactions[idx - len(texts) + 1: idx + 1])
            )
            texts.clear()

            # 감정 분석 결과 저장
            logging.info(f"Inserting sentiment data for batch {idx + 1}...")
            execute_values(cur, """
                INSERT INTO public.Community_Analysis (timestamp, reaction_id, sentiment)
                VALUES %s
                ON CONFLICT (reaction_id, timestamp) DO UPDATE
                SET sentiment = EXCLUDED.sentiment;
            """, sentiment_data)

            conn.commit()
            sentiment_data.clear()
            logging.info(f"Batch {idx + 1} inserted and committed.")

    cur.close()
    conn.close()
    logging.info("Sentiment analysis storage complete.")

# 코인 이름과 별칭 가져오기
def fetch_coin_aliases(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT coin_id, coin_name FROM Coins;")
        return cur.fetchall()  # [(coin_id, coin_name), ...]

# 분석할 커뮤니티 반응 가져오기
def fetch_unprocessed_reactions(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT reaction_id, timestamp, reaction_text
            FROM Community_Reactions
            WHERE reaction_id NOT IN (
                SELECT DISTINCT reaction_id FROM Community_Analysis_Coins
            );
        """)
        return cur.fetchall()  # [(reaction_id, timestamp, reaction_text), ...]

# 코인 이름 매칭 로직
def match_coins_in_text(reaction_text, coin_aliases):
    detected_coins = set()  # 중복 제거를 위해 set 사용
    for coin_id, alias in coin_aliases:
        if re.search(rf'\b{re.escape(alias)}', reaction_text, re.IGNORECASE):
            detected_coins.add(coin_id)
    return list(detected_coins)

# 분석 결과 저장
def save_analysis_results(conn, analysis_results):
    with conn.cursor() as cur:
        # INSERT를 위한 데이터 형식 준비
        data_to_insert = []
        for reaction_id, (timestamp, coin_ids) in analysis_results.items():
            # 1. Community_Analysis 테이블에서 해당 reaction_id와 timestamp로 analysis_id 조회
            cur.execute("""
                SELECT analysis_id FROM Community_Analysis
                WHERE reaction_id = %s AND timestamp = %s;
            """, (reaction_id, timestamp))
            
            # 2. 해당 analysis_id를 가져옴
            result = cur.fetchone()
            if result:
                analysis_id = result[0]
                
                # 3. Community_Analysis_Coins에 연결된 데이터 삽입
                for coin_id in coin_ids:
                    data_to_insert.append((analysis_id, timestamp, coin_id))
        if data_to_insert:
            execute_values(
                cur,
                """
                INSERT INTO Community_Analysis_Coins (analysis_id, timestamp, coin_id)
                VALUES %s
                ON CONFLICT DO NOTHING;
                """,
                data_to_insert
            )
    conn.commit()

# 배치 처리 메인 함수
def process_reactions(batch_size=1000):
    try:
        # PostgreSQL 연결
        conn = get_db_connection("data_scheduler")
        
        # 1. 코인 이름과 별칭 가져오기
        coin_aliases = fetch_coin_aliases(conn)
        logging.info(f"Fetched {len(coin_aliases)} coin aliases.")
        
        # 2. 분석되지 않은 커뮤니티 반응 가져오기
        reactions = fetch_unprocessed_reactions(conn)
        logging.info(f"Fetched {len(reactions)} unprocessed reactions.")
        
        # 3. 매칭 로직 실행
        analysis_results = {}
        for reaction_id, timestamp, reaction_text in reactions:
            matched_coins = match_coins_in_text(reaction_text, coin_aliases)
            if matched_coins:
                analysis_results[reaction_id] = (timestamp, matched_coins)
            
            # 일정량의 데이터를 처리할 때마다 중간 저장
            if len(analysis_results) >= batch_size:
                save_analysis_results(conn, analysis_results)
                logging.info(f"Processed {len(analysis_results)} reactions and saved results.")
                analysis_results.clear()  # 저장 후 리스트 초기화
        
        # 남은 데이터 저장
        if analysis_results:
            save_analysis_results(conn, analysis_results)
            logging.info(f"Processed remaining {len(analysis_results)} reactions and saved results.")
        
    except Exception as e:
        logging.error(f"Error during processing: {e}")
    finally:
        if conn:
            conn.close()


#주기적으로 실행되는 스케줄러
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(analyze_and_store_morphological_data, 'interval', hours=1)  # 1시간마다 실행
    scheduler.add_job(analyze_and_store_sentiments, 'interval', hours=12)  # 12시간마다 실행
    scheduler.add_job(process_reactions, 'interval', hours=1)  # 1시간마다 실행
    scheduler.start()

    # 계속 실행
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == '__main__':
    #analyze_and_store_morphological_data()
    #analyze_and_store_sentiments()
    #process_reactions()
    start_scheduler()
