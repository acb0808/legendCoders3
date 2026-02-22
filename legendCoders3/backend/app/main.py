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

app = FastAPI(title="Legend Coder Platform API")

# CORS 설정
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost",
    "http://127.0.0.1",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(daily_problems.router)
app.include_router(submissions.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(stats.router)
app.include_router(admin.router)
app.include_router(titles.router)
app.include_router(arena.router)

@app.on_event("startup")
async def startup_event():
    print("Starting up application...")
    
    token = os.getenv('DISCORD_TOKEN')
    if token:
        asyncio.create_task(discord_client.start(token))
        print("Discord bot task started in background.")
    
    asyncio.create_task(pro_sync_loop())
    print("Pro Auto-Sync task started in background (5min interval).")

@app.get("/")
async def root():
    return {"message": "Welcome to Legend Coder Platform API"}
