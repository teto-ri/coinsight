from sqlalchemy.orm import Session
from src.model.models import Coin

def get_all_coins(db: Session):
    return db.query(Coin).all()

def get_coin_by_id(db: Session, symbol: str):
    symbol = symbol.upper()
    return db.query(Coin).filter(Coin.symbol == symbol).first()
