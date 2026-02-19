# backend/app/main.py
from fastapi import FastAPI
import uvicorn
import os
from dotenv import load_dotenv

from .routers import users, daily_problems, submissions
from .tasks.scheduler import start_scheduler

load_dotenv()

app = FastAPI(title="Legend Coder Platform API")

app.include_router(users.router)
app.include_router(daily_problems.router)
app.include_router(submissions.router)

@app.on_event("startup")
async def startup_event():
    print("Starting up application...")
    # start_scheduler() # 임시 비활성화 (무한 로딩 방지)

@app.get("/")
async def root():
    return {"message": "Welcome to Legend Coder Platform API"}
