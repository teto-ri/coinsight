from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from sqlalchemy.orm import Session
from src.service.coin_ohlcv import get_ohlcv_data_by_coin
from src.service.coin_ohlcv import get_ohlcv_data_by_interval
from src.database.connection import get_db

router = APIRouter(prefix="/ohlcv", tags=["Coin OHLCV"])

@router.get("/{symbol}")
def retrieve_ohlcv_data(symbol: str, db: Session = Depends(get_db)):
    ohlcv_data = get_ohlcv_data_by_coin(db, symbol)
    if not ohlcv_data:
        raise HTTPException(status_code=404, detail="No OHLCV data found for this coin")
    return ohlcv_data

@router.get("/1h/{symbol}")
def retrieve_1h_ohlcv_data(
    symbol: str,
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    db: Session = Depends(get_db)
):
    return get_ohlcv_data_by_interval(db, symbol, start_date, end_date, 1)

# 4시간 간격
@router.get("/4h/{symbol}")
def retrieve_4h_ohlcv_data(
    symbol: str,
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    db: Session = Depends(get_db)
):
    return get_ohlcv_data_by_interval(db, symbol, start_date, end_date, 4)

# 24시간 간격
@router.get("/24h/{symbol}")
def retrieve_24h_ohlcv_data(
    symbol: str,
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    db: Session = Depends(get_db)
):
    return get_ohlcv_data_by_interval(db, symbol, start_date, end_date, 24)