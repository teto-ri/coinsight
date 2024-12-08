from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "*",  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 허용할 출처 리스트
    allow_credentials=True,  # 인증 정보 포함 여부
    allow_methods=["*"],  # 허용할 HTTP 메서드
    allow_headers=["*"],  # 허용할 HTTP 헤더
)