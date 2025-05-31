# 기본 이미지
FROM python:3.10-slim

# 작업 디렉토리 생성
WORKDIR /app

# 앱 파일 복사
COPY . /app

# 필요한 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# Flask 실행
CMD ["python", "carbon_collector.py"]