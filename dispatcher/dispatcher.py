from kubernetes import client, config, utils
from kubernetes.client import configuration
from flask import Flask, request, jsonify
import os
import mysql.connector

db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": "carbonetes"
}

app = Flask(__name__)

class MLTask():
    def __init__(self,cluster, task_name):
        self.cluster = cluster
        self.task_name = task_name
        
    
    def print(self):
        print(f"\tcluster: {self.cluster}")
        print(f"\ttask name: {self.task_name}")


def get_kubeconfig_context(cluster_name):
    # cluster_name이 "k3s-1" 또는 "k3s-2"일 때 context 이름 반환
    if cluster_name == "k3s-1":
        return "k3s-1"
    elif cluster_name == "k3s-2":
        return "k3s-2"
    else:
        raise ValueError("지원하지 않는 클러스터입니다.")

def deploy_to_cluster(cluster_name, task_name ):
    # 클러스터 설정
    context = get_kubeconfig_context(cluster_name)
    config_path = f"/app/configs/{cluster_name}/config"
    config.load_kube_config(config_file=config_path)
    
    # Job 생성
    batch = client.BatchV1Api()
    job_manifest = generate_job_manifest(task_name)
    batch.create_namespaced_job(namespace="default", body=job_manifest)
    print(f"Cluster {cluster_name}에 Job {task_name}-job 생성 완료")

    # DB 업데이트
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    query = """
        UPDATE task_info
        SET status = 'running'
        WHERE task_name = %s
    """
    cursor.execute(query, (task_name,))
    cursor.close()
    conn.commit()


def generate_job_manifest(task_name):
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": f"{task_name}-job"
        },
        "spec": {
            "backoffLimit": 3,
            "ttlSecondsAfterFinished": 600,
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "main",
                            "image": "twkji/run-main",
                            "command": ["python", "run-main.py"],
                            "env": [
                                {"name": "MYSQL_HOST", "valueFrom": {"configMapKeyRef": {"name": "mysql-cm", "key": "MYSQL_HOST"}}},
                                {"name": "MYSQL_PORT", "valueFrom": {"configMapKeyRef": {"name": "mysql-cm", "key": "MYSQL_PORT"}}},
                                {"name": "MYSQL_USER", "value": "root"},
                                {"name": "MYSQL_PASSWORD", "valueFrom": {"secretKeyRef": {"name": "mysql-secret", "key": "mysql-password"}}},
                                {"name": "MYSQL_DATABASE", "value": "carbonetes"},
                                {"name": "TASK_NAME", "value": task_name},
                                {"name": "MINIO_HOST", "valueFrom": {"configMapKeyRef": {"name": "minio-cm", "key": "MINIO_HOST"}}},
                                {"name": "MINIO_PORT", "valueFrom": {"configMapKeyRef": {"name": "minio-cm", "key": "MINIO_PORT"}}}
                            ]
                        }
                    ],
                    "restartPolicy": "Never",
                }
            }
        }
    }

@app.route("/new-task", methods=["POST"])
def new_task():
    
    task = request.json
    mlTask = MLTask(task['cluster'], task['task_name'])

    # 클러스터에 배포 및 DB 업데이트
    deploy_to_cluster(mlTask.cluster, mlTask.task_name)
    return {"status": "success", "message": f"{mlTask.task_name}작업이 생성되었습니다."}, 200
   

if __name__ == "__main__":
    app.run(debug=True, port=5000)