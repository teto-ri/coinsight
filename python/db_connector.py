import psycopg2
from dotenv import load_dotenv
import os 

# .env 파일 로드
load_dotenv()

# 환경 변수에서 DB 접속 정보와 포트를 읽어옴
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", 5432)  # 기본 포트 5432
DB_NAME = os.getenv("DB_NAME")

# 데이터 수집기 역할에 맞는 DB 사용자 정보
DB_USER_COLLECTOR = os.getenv("DB_USER_COLLECTOR")
DB_PASSWORD_COLLECTOR = os.getenv("DB_PASSWORD_COLLECTOR")

# 데이터 스케줄러 역할에 맞는 DB 사용자 정보
DB_USER_SCHEDULER = os.getenv("DB_USER_SCHEDULER")
DB_PASSWORD_SCHEDULER = os.getenv("DB_PASSWORD_SCHEDULER")

# 데이터베이스 연결 함수 (역할별 사용자 정보 처리)
def get_db_connection(role):
    if role == "data_collector":
        # 데이터 수집기 권한으로 DB 연결
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER_COLLECTOR,
            password=DB_PASSWORD_COLLECTOR
        )
    elif role == "data_scheduler":
        # 데이터 스케줄러 권한으로 DB 연결
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER_SCHEDULER,
            password=DB_PASSWORD_SCHEDULER
        )
    else:
        raise ValueError("Invalid role specified")
    
    return connection


import asyncpg

# 비동기 데이터베이스 연결 함수
async def asycn_get_db_connection(role):
    if role == "data_collector":
        return await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER_COLLECTOR,
            password=DB_PASSWORD_COLLECTOR
        )
    elif role == "data_scheduler":
        return await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER_SCHEDULER,
            password=DB_PASSWORD_SCHEDULER
        )
    else:
        raise ValueError("Invalid role specified")