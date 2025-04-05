# producer.py
import requests
import uuid

job_id = f"job-{uuid.uuid4().hex[:6]}"
job = {
    "id": job_id,
    "type": "python_script",
    "script": "train_model.py",
    "args": ["--epochs", "5"],
    "resources": {
        "cpu": "2",
        "memory": "4Gi",
        "gpu": "0"
    }
}

res = requests.post("http://localhost:5000/jobs", json=job)
print(f"📥 작업 등록됨: {job_id}")
