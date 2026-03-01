# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import asyncio
from dotenv import load_dotenv

from .routers import users, daily_problems, submissions, posts, comments, stats, admin, titles, arena
from .tasks.scheduler import start_scheduler
from .discord_bot.bot import client as discord_client
from .tasks.pro_sync import pro_sync_loop

load_dotenv()

from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .limiter import limiter # 분리된 limiter 가져오기

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup 로직
    print("Starting up application with security patches...")
    tasks = []
    
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot_task = asyncio.create_task(discord_client.start(token))
        tasks.append(bot_task)
        print("Discord bot task started in background.")
    
    sync_task = asyncio.create_task(pro_sync_loop())
    tasks.append(sync_task)
    print("Pro Auto-Sync task started in background (5min interval).")
    
    yield
    
    # Shutdown 로직
    print("Shutting down application...")
    if token:
        try:
            await discord_client.close()
        except Exception as e:
            print(f"Error while closing Discord bot: {e}")
            
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    print("Security-aware shutdown complete.")

app = FastAPI(title="Legend Coder Platform API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS 설정
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost,http://127.0.0.1").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(users.router)
app.include_router(daily_problems.router)
app.include_router(submissions.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(stats.router)
app.include_router(admin.router)
app.include_router(titles.router)
app.include_router(arena.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Legend Coder Platform API (Secured)"}
