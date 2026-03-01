from app.database import engine, Base
from app.models import User, Title, UserTitle, DailyProblem, Submission, Post, Comment, Achievement, UserAchievement, Arena, InvitationCode

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Done!")
