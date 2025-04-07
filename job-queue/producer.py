# producer.py
import requests
import uuid

job_id = f"job-{uuid.uuid4().hex[:6]}"
job = {
    "id": job_id,
    "type": "kubectl_cmd",
    "script": "kubectl",  
    "args": ["get", "nodes"], 
    "resources": {
        "cpu": "1",
        "memory": "1Gi",
        "gpu": "0"
    }
}

res = requests.post("http://localhost:5000/jobs", json=job)
print(f"📥 작업 등록됨: {job_id}")
