import requests
import uuid



def make_task():
    task_name = f"mltask-{uuid.uuid4().hex[:6]}"
    task = {
        "cluster": "default",
        "task": task_name
        }
    return task

for i in range(5):
    task = make_task()
    res = requests.post("http://localhost:5000/new-task", json=task)
    json = res.json()
    print(f"📥 작업 등록됨: {json['message']}")