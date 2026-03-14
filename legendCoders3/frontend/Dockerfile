# 빌드 단계
FROM node:20-alpine AS builder
WORKDIR /app

# 패키지 매니저 파일 복사 및 설치
COPY package*.json ./
RUN npm install

# 소스 코드 복사 및 빌드
COPY . .
RUN npm run build

# 실행 단계 (최종 이미지 용량을 위해 빌드 결과물만 복사)
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# 빌드 결과물 및 node_modules 복사
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
CMD ["npm", "start"]
