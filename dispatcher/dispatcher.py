from kubernetes import client, config, utils
from kubernetes.client import configuration
from flask import Flask, request, jsonify
from queue import Queue

app = Flask(__name__)
queue = Queue()

class MLTask():
    def __init__(self,cluster, task, task_url):
        self.cluster = cluster
        self.task = task
        self.task_url = task_url
    
    def print(self):
        print(f"\tcluster: {self.cluster}")
        print(f"\ttask name: {self.task}")
        print(f"\ttask url: {self.task_url}")


@app.route("/new-task", methods=["POST"])
def new_task():
    # 스케줄러로부터 새로운 작업을 받아서 큐에 넣기
    task = request.json
    mlTask = MLTask(task['cluster'], task['task'], task['task_url'])
    queue.put(mlTask)
    if not queue.empty():
        will_deploy = queue.get()
        will_deploy.print()
    
    return {"status": "success", "message": f"{will_deploy.task}작업이 생성되었습니다."}, 200
   

if __name__ == "__main__":
    app.run(debug=True, port=5000)

