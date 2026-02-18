# backend/main.py
from fastapi import FastAPI
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv() # .env 파일에서 환경 변수 로드

app = FastAPI(title="Legend Coder Platform API")

@app.get("/")
async def root():
    return {"message": "Welcome to Legend Coder Platform API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))