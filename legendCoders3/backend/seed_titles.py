import os
import sys
import uuid

# Add backend dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Title

def seed_titles():
    db = SessionLocal()
    
    titles = [
        {
            "name": "퍼스트 블러드",
            "description": "오늘의 문제를 가장 먼저 해결한 자에게 주어지는 영광",
            "color_code": "red-500",
            "icon": "🩸",
            "is_pro_only": False,
            "has_glow": True,
            "animation_type": "pulse"
        },
        {
            "name": "얼리버드",
            "description": "아침 일찍(06:00~09:00) 문제를 해결하는 부지런한 코더",
            "color_code": "blue-400",
            "icon": "🐦",
            "is_pro_only": False,
            "has_glow": False,
            "animation_type": None
        },
        {
            "name": "레전드 프로",
            "description": "Legend Pro 프리미엄 멤버십 회원 전용",
            "color_code": "amber-500",
            "icon": "👑",
            "is_pro_only": True,
            "has_glow": True,
            "animation_type": "shimmer"
        },
        {
            "name": "브론즈 마스터",
            "description": "기초가 탄탄한 자, 브론즈 문제를 정복하다",
            "color_code": "orange-700",
            "icon": "🥉",
            "is_pro_only": False,
            "has_glow": False,
            "animation_type": None
        },
        {
            "name": "플래티넘 헌터",
            "description": "일요일의 고난도 문제를 해결한 진정한 실력자",
            "color_code": "indigo-400",
            "icon": "💎",
            "is_pro_only": False,
            "has_glow": True,
            "animation_type": "shimmer"
        }
    ]

    print("--- Seeding Titles ---")
    for t_data in titles:
        existing = db.query(Title).filter(Title.name == t_data["name"]).first()
        if not existing:
            new_title = Title(**t_data)
            db.add(new_title)
            print(f"Added Title: {t_data['name']}")
        else:
            print(f"Title exists: {t_data['name']}")
            # 업데이트 (필요한 경우)
            for key, value in t_data.items():
                setattr(existing, key, value)
    
    db.commit()
    db.close()
    print("--- Done ---")

if __name__ == "__main__":
    seed_titles()
