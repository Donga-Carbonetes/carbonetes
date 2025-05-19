FROM python:3.11-slim

WORKDIR /app

COPY operator.py .

RUN pip install --no-cache-dir \
    kopf \
    kubernetes

CMD ["kopf", "run", "--standalone", "operator.py"]
