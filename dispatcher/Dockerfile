FROM python:3.11-slim

WORKDIR /app

# dispatcher.py 복사
COPY dispatcher.py .

# mysql-connector-python, flask, kubernetes 등 필요한 패키지 설치
RUN apt-get update && \
    apt-get install -y gcc && \
    pip install --no-cache-dir \
        flask \
        kubernetes \
        mysql-connector-python

CMD ["python", "dispatcher.py"] 