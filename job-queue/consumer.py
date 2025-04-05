# consumer.py
import requests
import subprocess
import time

def run_job(job):
    try:
        cmd = ["python", job["script"]] + job["args"]
        subprocess.run(cmd, check=True)
        requests.post(f"http://localhost:5000/jobs/{job['id']}/status", json={"status": "DONE"})
        print(f"✅ 작업 완료: {job['id']}")
    except subprocess.CalledProcessError:
        requests.post(f"http://localhost:5000/jobs/{job['id']}/status", json={"status": "FAILED"})
        print(f"❌ 작업 실패: {job['id']}")

while True:
    res = requests.get("http://localhost:5000/jobs/next")
    if res.status_code == 200:
        job = res.json()
        print(f"🚀 실행 중: {job['id']}")
        run_job(job)
    else:
        time.sleep(1)
