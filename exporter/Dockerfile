FROM python:3.11-slim

WORKDIR /app

# exporter 코드만 복사
COPY exporter.py .

# PyTorch 설치를 위한 기본 의존성
RUN apt-get update && \
    apt-get install -y gcc && \
    pip install --no-cache-dir \
        torch torchvision \
        numpy \
        python-dotenv \
        mysql-connector-python \
        minio \
        kubernetes

# 환경변수는 .env 대신 Kubernetes Job에서 주입
CMD ["python", "exporter.py"]
