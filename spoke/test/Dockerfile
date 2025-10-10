FROM python:3.10-slim
RUN pip install kubernetes
COPY test_cpu_sampler.py /app/test_cpu_sampler.py
CMD ["python", "-u", "/app/test_cpu_sampler.py"]
