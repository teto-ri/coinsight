from sqlalchemy import (
    Column, Integer, String, BigInteger, Float, Date, Text, Numeric, ForeignKey, ARRAY, TIMESTAMP, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

# 1. 코인 정보 테이블
class Coin(Base):
    __tablename__ = 'coins'
    
    coin_id = Column(Integer, primary_key=True, autoincrement=True)
    coin_name = Column(String(100), nullable=False)
    symbol = Column(String(10), nullable=False, unique=True)
    market_cap = Column(BigInteger)
    total_supply = Column(BigInteger)
    circulating_supply = Column(BigInteger)
    ranking = Column(Integer)
    market_cap_change_24h = Column(Float)
    launch_date = Column(Date)
    description = Column(Text)

# 2. OHLCV 데이터 테이블
class CoinOHLCV(Base):
    __tablename__ = 'coin_ohlcv'
    
    coin_id = Column(Integer, ForeignKey('coins.coin_id', ondelete='CASCADE'), primary_key=True)
    timestamp = Column(TIMESTAMP, primary_key=True)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)

# 3. 커뮤니티 반응 테이블
class CommunityReaction(Base):
    __tablename__ = 'community_reactions'
    
    reaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(TIMESTAMP, primary_key=True)
    reaction_text = Column(Text, nullable=False)
    chat_name = Column(String(255), nullable=False)
    sender = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)

# # 4-1. 커뮤니티 분석 테이블
class CommunityAnalysis(Base):
    __tablename__ = 'community_analysis'
    
    analysis_id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP, nullable=False)
    reaction_id = Column(UUID(as_uuid=True), nullable=False)
    nouns = Column(Text)
    adjectives = Column(Text)
    verbs = Column(Text)
    interjections = Column(Text)
    sentiment = Column(String(10))

    __table_args__ = (
        ForeignKeyConstraint(
            ['reaction_id', 'timestamp'],
            ['community_reactions.reaction_id', 'community_reactions.timestamp'],
            ondelete='CASCADE'
        ),
    )

# # 4-2. 커뮤니티 분석과 코인 관계를 연결하는 교차 테이블
# class CommunityAnalysisCoins(Base):
#     __tablename__ = 'Community_Analysis_Coins'
    
#     analysis_id = Column(Integer, primary_key=True)
#     timestamp = Column(TIMESTAMP, primary_key=True)
#     coin_id = Column(Integer, ForeignKey('Coins.coin_id', ondelete='CASCADE'), nullable=False)

# # 5. 추천 및 알림 테이블
# class Recommendation(Base):
#     __tablename__ = 'Recommendations'
    
#     recommendation_id = Column(Integer, primary_key=True, autoincrement=True)
#     coin_id = Column(Integer, ForeignKey('Coins.coin_id', ondelete='CASCADE'), nullable=False)
#     timestamp = Column(TIMESTAMP, nullable=False)
#     reason = Column(Text, nullable=False)
