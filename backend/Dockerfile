# 1단계: 빌드 환경
FROM node:22.15.0-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .


# 2단계: 실행 환경
FROM node:22.15.0-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY --from=builder /app ./

USER root

EXPOSE 4000

CMD ["node", "app.js"] 