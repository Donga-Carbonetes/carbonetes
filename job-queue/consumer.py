# consumer.py
import requests
import subprocess
import time

SERVER_URL = "http://localhost:5000"
contexts = ['default', 'docker-desktop']
def run_job(job):
    try:
        if job["type"] == "python_script":
            cmd = ["python", job["script"]] + job["args"]
        elif job["type"] == "kubectl_cmd":
            cmd = job["script"]  # 예: ["kubectl", "get", "nodes"]
        else:
            print(f"⚠️ 알 수 없는 작업 타입: {job['type']}")
            requests.post(f"{SERVER_URL}/jobs/{job['id']}/status", json={"status": "FAILED"})
            return

        for context in contexts:
            print(f"▶️ 실행 명령어: {' '.join(cmd)}")
            subprocess.run(f'kubectl config use-context {context}', check=True)
            subprocess.run(cmd, check=True)

        requests.post(f"{SERVER_URL}/jobs/{job['id']}/status", json={"status": "DONE"})
        print(f"✅ 작업 완료: {job['id']}")

    except subprocess.CalledProcessError as e:
        print(f"❌ 작업 실패: {job['id']}\n에러: {e}")
        requests.post(f"{SERVER_URL}/jobs/{job['id']}/status", json={"status": "FAILED"})

while True:
    res = requests.get(f"{SERVER_URL}/jobs/next")
    if res.status_code == 200:
        job = res.json()
        print(f"\n🚀 작업 수신됨: {job['id']} ({job['type']})")
        run_job(job)
    else:
        time.sleep(1)
