# backend/app/main.py
from fastapi import FastAPI
import uvicorn
import os
from dotenv import load_dotenv

from .routers import users, daily_problems
from .tasks.scheduler import start_scheduler # 스케줄러 임포트

load_dotenv()

app = FastAPI(title="Legend Coder Platform API")

app.include_router(users.router)
app.include_router(daily_problems.router)

@app.on_event("startup")
async def startup_event():
    print("Starting up application...")
    start_scheduler() # 애플리케이션 시작 시 스케줄러 시작

@app.get("/")
async def root():
    return {"message": "Welcome to Legend Coder Platform API"}