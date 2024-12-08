from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.model.models import CommunityReaction, CommunityAnalysis

def get_community_data_by_interval(db: Session, start_date: datetime, end_date: datetime):
    """
    주어진 시간 범위에 따라 CommunityReaction 데이터를 조회하고
    각 reaction에 맞는 CommunityAnalysis 데이터를 찾아서 응답합니다.
    
    Args:
        db (Session): SQLAlchemy 세션
        start_date (datetime): 조회 시작 시간
        end_date (datetime): 조회 끝나는 시간

    Returns:
        list[dict]: 조회된 데이터의 리스트
    """
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=7)
    
    # 날짜 검증
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="시작 날짜는 끝나는 날짜보다 이전이어야 합니다.")
    
    # CommunityReaction 데이터 조회
    reactions = (
        db.query(CommunityReaction)
        .filter(CommunityReaction.timestamp.between(start_date, end_date))
        .all()
    )
    
    if not reactions:
        return []  # 조회된 데이터가 없을 경우 빈 리스트 반환
    
    response_data = []
    for reaction in reactions:
        # 해당 reaction_id 및 timestamp에 맞는 CommunityAnalysis 조회
        analysis = (
            db.query(CommunityAnalysis)
            .filter(
                CommunityAnalysis.reaction_id == reaction.reaction_id,
                CommunityAnalysis.timestamp == reaction.timestamp
            )
            .first()
        )
        
        # 결과 데이터 구성
        response_data.append({
            "reaction_id": reaction.reaction_id,
            "timestamp": reaction.timestamp,
            "reaction_text": reaction.reaction_text,
            "chat_name": reaction.chat_name,
            "sender": reaction.sender,
            "source": reaction.source,
            "analysis": {
                "nouns": analysis.nouns if analysis else None,
                "adjectives": analysis.adjectives if analysis else None,
                "verbs": analysis.verbs if analysis else None,
                "interjections": analysis.interjections if analysis else None,
                "sentiment": analysis.sentiment if analysis else None
            } if analysis else None
        })
    
    return response_data

