# Python 3.11 환경 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 라이브러리 설치 (psycopg2 등을 위한 빌드 도구)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 종속성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 소스 코드 복사
COPY . .

# 실행 권한 부여 및 서버 실행
# backend 폴더 내에서 실행되므로 경로 주의 (uvicorn app.main:app)
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
