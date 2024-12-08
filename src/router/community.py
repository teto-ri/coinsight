from fastapi import APIRouter, Depends, HTTPException
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from sqlalchemy.orm import Session
from src.service.community import get_community_data_by_interval
from src.database.connection import get_db

router = APIRouter(prefix="/community", tags=["community"])

@router.get("/")
def get_community_data(
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    db: Session = Depends(get_db)
):
    return get_community_data_by_interval(db, start_date, end_date)