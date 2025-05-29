FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir \
    requests \
    python-dotenv \
    prometheus_client \
    mysql-connector-python

CMD ["python", "monitoring.py"] 