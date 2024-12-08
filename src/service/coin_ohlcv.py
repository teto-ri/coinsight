from sqlalchemy.orm import Session
from src.model.models import CoinOHLCV, Coin
from fastapi import HTTPException
from datetime import datetime, timedelta

def get_ohlcv_data_by_coin(db: Session, symbol: str):
    coin = db.query(Coin).filter(Coin.symbol == symbol.upper()).first()
    return db.query(CoinOHLCV).filter(CoinOHLCV.coin_id == coin.coin_id).all()

def get_ohlcv_data_by_interval(db: Session, symbol: str, start_date: datetime, end_date: datetime, interval: int):
    # 지원하는 간격 확인
    if interval not in [1, 4, 24]:
        raise HTTPException(status_code=400, detail="Invalid interval. Supported values: 1, 4, 24")

    # 심볼로 코인 정보 가져오기
    coin = db.query(Coin).filter(Coin.symbol == symbol.upper()).first()
    if not coin:
        raise HTTPException(status_code=404, detail="Coin not found")

    # 시작일과 종료일 기본값 설정
    if not end_date:
        end_date = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    if not start_date:
        start_date = (end_date - timedelta(days=7)).replace(minute=0, second=0, microsecond=0)  # 기본적으로 최근 7일 데이터를 가져옴

    # 기본 데이터 가져오기
    raw_data = (
        db.query(
            CoinOHLCV.timestamp,
            CoinOHLCV.open,
            CoinOHLCV.high,
            CoinOHLCV.low,
            CoinOHLCV.close,
            CoinOHLCV.volume
        )
        .filter(
            CoinOHLCV.coin_id == coin.coin_id,
            CoinOHLCV.timestamp >= start_date,
            CoinOHLCV.timestamp <= end_date,
        )
        .order_by(CoinOHLCV.timestamp)
        .all()
    )

    if not raw_data:
        raise HTTPException(status_code=404, detail="No OHLCV data found for this coin")

    # 데이터를 간격별로 정제
    grouped_data = []
    interval_seconds = interval * 3600  # 간격(시간)을 초 단위로 변환
    current_group = {
        "open": None,
        "high": float('-inf'),
        "low": float('inf'),
        "close": None,
        "volume": 0,
        "timestamp": None,
    }

    start_of_interval = None

    for row in raw_data:
        timestamp = row.timestamp 
        print(timestamp)
        
        if not start_of_interval:
            start_of_interval = timestamp

        # 새 그룹을 시작해야 할 경우
        if (timestamp - start_of_interval).total_seconds() >= interval_seconds:
            # 이전 그룹 저장
            if current_group["open"] is not None:  # 그룹 데이터가 유효할 경우만 추가
                grouped_data.append(current_group)

            # 새 그룹 초기화
            start_of_interval = timestamp
            current_group = {
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
                "timestamp": start_of_interval,
            }
        else:
            # 기존 그룹 데이터 업데이트
            if current_group["open"] is None:
                current_group["open"] = row.open
            current_group["high"] = max(current_group["high"], row.high)
            current_group["low"] = min(current_group["low"], row.low)
            current_group["close"] = row.close
            current_group["volume"] += row.volume

    # 마지막 그룹 저장
    if current_group["open"] is not None:
        grouped_data.append(current_group)
    
    grouped_data = [group for group in grouped_data if group["timestamp"] is not None]
    
    return grouped_data
