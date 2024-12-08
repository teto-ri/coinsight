from fastapi import FastAPI
from cors import app
from src.router import coin, coin_ohlcv, community
import uvicorn

app.include_router(coin.router)
app.include_router(coin_ohlcv.router)
app.include_router(community.router)
# print(coin.get_all_coins())
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5455)
    
#  uvicorn main:app --host 0.0.0.0 --port 5455