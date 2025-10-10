FROM python:3.11-slim

WORKDIR /app

# run-main.py 복사
COPY run-main.py .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates tzdata gcc && \
    rm -rf /var/lib/apt/lists/*

# run-main.py 복사
COPY run-main.py .

# 파이썬 패키지 설치
# kubernetes 클라이언트 + 기존 의존성
# (버전 고정 권장: 클러스터와의 호환성 안정)
RUN pip install --no-cache-dir \
        kubernetes==29.0.0 \
        mysql-connector-python \
        minio \
        torch \
        torchvision \
        numpy

# 실행에 필요한 디렉토리 미리 생성
RUN mkdir -p ./tmp/myapp

CMD ["python", "run-main.py"] 