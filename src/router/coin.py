from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.service.coin import get_all_coins, get_coin_by_id
from src.database.connection import get_db

router = APIRouter(prefix="/coins", tags=["Coins"])

@router.get("/")
def list_coins(db: Session = Depends(get_db)):
    return get_all_coins(db)

@router.get("/{symbol}")
def retrieve_coin(symbol: str, db: Session = Depends(get_db)):
    coin = get_coin_by_id(db, symbol)
    if not coin:
        raise HTTPException(status_code=404, detail="Coin not found")
    return coin
