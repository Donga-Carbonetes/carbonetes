FROM python:3.11-slim

WORKDIR /app

# run-main.py 복사
COPY run-main.py .

# mysql-connector-python 빌드에 gcc 필요
RUN apt-get update && \
    apt-get install -y gcc && \
    pip install --no-cache-dir \
        mysql-connector-python \
        minio \
        torch \
        torchvision \
        numpy 

# 실행에 필요한 디렉토리 미리 생성
RUN mkdir -p ./tmp/myapp

CMD ["python", "run-main.py"] 