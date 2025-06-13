# --- 1단계: 빌드 ---
FROM node:22.15
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# 환경변수 ARG로 받기
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL
COPY . .

# build 시점에 환경변수 사용
RUN REACT_APP_API_URL=$REACT_APP_API_URL npm run build

# serve 패키지 전역 설치
RUN npm install -g serve

EXPOSE 3000     

CMD ["serve", "-s", "build", "-l", "3000"] 