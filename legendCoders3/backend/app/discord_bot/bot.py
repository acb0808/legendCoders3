import discord
from discord.ext import tasks
import os
import json
import asyncio
import anyio
import time
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy.orm import Session, joinedload
from ..database import SessionLocal
from .. import models, crud

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'bot_config.json')
last_known_date = None

def load_config():
    if not os.path.exists(CONFIG_FILE): return {}
    try:
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    except: return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)

@client.event
async def on_ready():
    print(f'Discord Bot logged in as {client.user}')
    if not check_for_updates.is_running(): check_for_updates.start()
    if not check_for_solves.is_running(): check_for_solves.start()

def sync_check_solves():
    db = SessionLocal()
    results = []
    try:
        config = load_config()
        announced_ids = config.get('announced_submission_ids', [])
        today = date.today()
        
        daily_problem = db.query(models.DailyProblem).filter(
            models.DailyProblem.problem_date >= datetime.combine(today, datetime.min.time()),
            models.DailyProblem.problem_date <= datetime.combine(today, datetime.max.time())
        ).first()
        
        if not daily_problem: return None

        submissions = db.query(models.Submission).filter(
            models.Submission.daily_problem_id == daily_problem.id
        ).order_by(models.Submission.submitted_at.asc()).all()

        for idx, sub in enumerate(submissions):
            sub_id = str(sub.id)
            if sub_id not in announced_ids:
                # 칭호 정보를 포함하여 사용자 조회
                user = db.query(models.User).options(joinedload(models.User.equipped_title)).filter(models.User.id == sub.user_id).first()
                if user:
                    title_prefix = f"[`{user.equipped_title.name}`] " if user.equipped_title else ""
                    results.append({
                        "id": sub_id,
                        "nickname": f"{title_prefix}{user.nickname}",
                        "is_first": (idx == 0)
                    })
        return results, config
    finally:
        db.close()

def sync_get_leaderboard_data():
    db = SessionLocal()
    try:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        users = db.query(models.User).options(joinedload(models.User.equipped_title)).all()
        
        leaderboard_rows = []
        for user in users:
            # 칭호가 있으면 닉네임 앞에 붙임
            if user.equipped_title:
                name_display = f"[{user.equipped_title.name[:2]}] {user.nickname[:6]}"
            else:
                name_display = user.nickname[:10]
            
            row = [name_display]
            for i in range(7):
                target_date = start_of_week + timedelta(days=i)
                prob = db.query(models.DailyProblem).filter(
                    models.DailyProblem.problem_date >= datetime.combine(target_date, datetime.min.time()),
                    models.DailyProblem.problem_date <= datetime.combine(target_date, datetime.max.time())
                ).first()
                if prob:
                    solved = db.query(models.Submission).filter(
                        models.Submission.user_id == user.id,
                        models.Submission.daily_problem_id == prob.id
                    ).first()
                    row.append("O" if solved else "X")
                else:
                    row.append("-")
            leaderboard_rows.append(row)
        return leaderboard_rows, start_of_week
    finally:
        db.close()

@tasks.loop(seconds=15)
async def check_for_solves():
    try:
        res = await anyio.to_thread.run_sync(sync_check_solves)
        if not res: return
        new_solves, config = res
        if not new_solves: return

        channel_id = config.get('channel_2')
        if not channel_id: return
        channel = client.get_channel(channel_id)
        if not channel: return

        for solve in new_solves:
            if solve["is_first"]:
                await channel.send(f'🎉 **{solve["nickname"]}**님이 오늘의 문제 첫 클리어! **(FIRST BLOOD!)**')
            else:
                await channel.send(f'👍 **{solve["nickname"]}**님이 문제를 해결했습니다!')
            config.setdefault('announced_submission_ids', []).append(solve["id"])
        
        config['announced_submission_ids'] = config['announced_submission_ids'][-100:]
        await anyio.to_thread.run_sync(save_config, config)
        await update_leaderboard()
    except Exception as e:
        print(f"Error in check_for_solves: {e}")

@tasks.loop(seconds=60)
async def check_for_updates():
    global last_known_date
    today = date.today()
    if last_known_date != today:
        try:
            db = SessionLocal()
            problem = await anyio.to_thread.run_sync(lambda: db.query(models.DailyProblem).filter(
                models.DailyProblem.problem_date >= datetime.combine(today, datetime.min.time()),
                models.DailyProblem.problem_date <= datetime.combine(today, datetime.max.time())
            ).first())
            db.close()
            if problem:
                await update_daily_problem_embed(problem)
                await update_leaderboard()
                if last_known_date is not None:
                    config = load_config()
                    channel_id = config.get('channel_2')
                    if channel_id:
                        channel = client.get_channel(channel_id)
                        if channel:
                            msg = f'😆 오늘의 문제가 업데이트되었습니다! : **{problem.title}**\nhttp://localhost:3000/problems/today'
                            await channel.send(msg)
                last_known_date = today
        except Exception as e:
            print(f"Error in check_for_updates: {e}")

async def update_leaderboard():
    try:
        data, start_date = await anyio.to_thread.run_sync(sync_get_leaderboard_data)
        config = load_config()
        channel_id = config.get('channel_1')
        if not channel_id: return
        channel = client.get_channel(channel_id)
        if not channel: return

        header = "| 사용자 | 월 | 화 | 수 | 목 | 금 | 토 | 일 |\n"
        separator = "|---|---|---|---|---|---|---|---|\n"
        body = ""
        for row in data:
            body += f"| {row[0]:<10} | " + " | ".join(row[1:]) + " |\n"
        content = f"**주간 리더보드 ({start_date} ~)**\n```md\n{header}{separator}{body}```"
        
        message_id = config.get('leaderboard_message_id')
        try:
            if message_id:
                message = await channel.fetch_message(message_id)
                await message.edit(content=content)
            else:
                message = await channel.send(content=content)
                config['leaderboard_message_id'] = message.id
                save_config(config)
        except:
            message = await channel.send(content=content)
            config['leaderboard_message_id'] = message.id
            save_config(config)
    except Exception as e:
        print(f"Leaderboard update error: {e}")

async def update_daily_problem_embed(problem):
    config = load_config()
    channel_id = config.get('channel_1')
    if not channel_id: return
    channel = client.get_channel(channel_id)
    if not channel: return
    embed = discord.Embed(
        title=f"오늘의 문제: {problem.title}",
        description=f"난이도: {problem.difficulty_level}\n문제 번호: {problem.baekjoon_problem_id}",
        url=f"https://www.acmicpc.net/problem/{problem.baekjoon_problem_id}",
        color=discord.Color.blue()
    )
    embed.add_field(name="상세 정보", value="[웹사이트에서 보기](http://localhost:3000/problems/today)")
    message_id = config.get('daily_problem_message_id')
    try:
        if message_id:
            message = await channel.fetch_message(message_id)
            await message.edit(embed=embed)
        else:
            message = await channel.send(embed=embed)
            config['daily_problem_message_id'] = message.id
            save_config(config)
    except:
        message = await channel.send(embed=embed)
        config['daily_problem_message_id'] = message.id
        save_config(config)

async def notify_new_arena(arena):
    try:
        config = load_config()
        channel_id = config.get('channel_2')
        if not channel_id: return
        channel = client.get_channel(channel_id)
        if not channel: return

        # 호스트 닉네임 가져오기 (DB 세션을 새로 열어야 할 수도 있음, 또는 arena 객체에 이미 로딩되어 있어야 함)
        # 여기서는 arena 객체가 이미 joinedload 되어 있다고 가정하거나, ID만 있으면 DB 조회
        
        # 간단하게 메시지 구성
        msg = (
            f"⚔️ **새로운 아레나 대결이 열렸습니다!**\n"
            f"- 난이도: **{arena.difficulty}**\n"
            f"- 모드: **공개 대전**\n"
            f"- [참가하기](http://localhost:3000/arena/{arena.id})"
        )
        await channel.send(msg)
    except Exception as e:
        print(f"Failed to send arena notification: {e}")

@client.event
async def on_message(message):
    if message.author == client.user: return
    if message.content.startswith('!지정'):
        parts = message.content.split()
        if len(parts) == 2 and parts[1] in ['1', '2']:
            config = load_config()
            config[f'channel_{parts[1]}'] = message.channel.id
            save_config(config)
            await message.channel.send(f'✅ 이 채널이 **유형 {parts[1]}** 공지 채널로 지정되었습니다.')
