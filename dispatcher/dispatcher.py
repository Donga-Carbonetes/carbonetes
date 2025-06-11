from kubernetes import client, config
from flask import Flask, request
import os
import mysql.connector
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)

db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": "carbonetes"
}

class MLTask():
    def __init__(self, cluster, task_name):
        self.cluster = cluster
        self.task_name = task_name

    def print(self):
        print(f"\tcluster: {self.cluster}")
        print(f"\ttask name: {self.task_name}")

def get_kube_api_from_config(config_path):
    config.load_kube_config(config_file=config_path)
    conf = client.Configuration().get_default_copy()
    return client.BatchV1Api(client.ApiClient(conf))

def get_cr_api_incluster():
    config.load_incluster_config()
    conf = client.Configuration().get_default_copy()
    return client.CustomObjectsApi(client.ApiClient(conf))

def deploy_to_cluster(cluster_name, task_name):
    config_path = f"/app/configs/{cluster_name}/config"
    api = get_kube_api_from_config(config_path)

    job_manifest = generate_job_manifest(task_name)
    api.create_namespaced_job(namespace="default", body=job_manifest)
    print(f"✅ Cluster {cluster_name}에 Job {task_name}-job 생성 완료")

    # DB 업데이트
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    query = """
        UPDATE task_info
        SET status = 'running', cluster_name = %s, dispatched_at = %s
        WHERE task_name = %s
    """
    cursor.execute(query, (cluster_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), task_name,))
    conn.commit()
    cursor.close()
    conn.close()

def update_k8s_mltask_status(name, namespace, phase):
    api = get_cr_api_incluster()
    group = "ml.carbonetes.io"
    version = "v1"
    plural = "mltasks"

    body = {
        "status": {
            "phase": phase
        }
    }

    try:
        api.patch_namespaced_custom_object_status(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
            body=body
        )
        print(f"✅ mltask '{name}' 상태를 '{phase}'로 업데이트 했습니다.")
    except Exception as e:
        print(f"❌ mltask 상태 '{phase}' 업데이트 실패: {e}")

def update_k8s_mltask_status_running(name, namespace):
    update_k8s_mltask_status(name, namespace, "running")

def update_k8s_mltask_status_terminated(name, namespace):
    update_k8s_mltask_status(name, namespace, "terminated")

def fetch_terminated_mltasks():
    result = []
    try:
        # 1. 클러스터에서 mltask 목록 조회
        config.load_incluster_config()
        cr_api = client.CustomObjectsApi()
        group = "ml.carbonetes.io"
        version = "v1"
        namespace = "default"
        plural = "mltasks"

        cr_list = cr_api.list_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural
        )

        cluster_task_names = [item["metadata"]["name"] for item in cr_list.get("items", [])]

        if not cluster_task_names:
            return []

        # 2. DB에서 terminated 상태인 task 조회 (클러스터에 존재하는 것만)
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        format_strings = ','.join(['%s'] * len(cluster_task_names))
        query = f"""
            SELECT task_name
            FROM task_info
            WHERE status = 'terminated'
            AND task_name IN ({format_strings})
        """

        cursor.execute(query, tuple(cluster_task_names))
        db_results = cursor.fetchall()
        cursor.close()
        conn.close()

        # 3. 결과 정리
        for row in db_results:
            result.append({
                "task_name": row["task_name"],
                "namespace": namespace
            })

    except Exception as e:
        print(f"❌ mltask 조회 실패: {e}")

    return result


def delete_k8s_mltask(name, namespace):
    api = get_cr_api_incluster()
    group = "ml.carbonetes.io"
    version = "v1"
    plural = "mltasks"

    try:
        api.delete_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
            body=client.V1DeleteOptions()
        )
        print(f"🗑️ mltask '{name}' 리소스를 삭제했습니다.")
    except Exception as e:
        print(f"❌ mltask 삭제 실패: {e}")

def loop_terminated_updater():
    while True:
        try:
            tasks = fetch_terminated_mltasks()
            if tasks:
                for task in tasks:
                    try:
                        task_name = task.get("task_name")
                        namespace = task.get("namespace", "default")
                        if not task_name:
                            print("⚠️ 잘못된 task 레코드: 'task_name' 없음")
                            continue

                        update_k8s_mltask_status_terminated(task_name, namespace)
                        time.sleep(5)  # 상태 업데이트 후 약간 대기
                        delete_k8s_mltask(task_name, namespace)

                    except Exception as e:
                        print(f"❌ task '{task.get('task_name')}' 처리 중 오류: {e}")
        except Exception as e:
            print(f"❌ 전체 루프에서 오류 발생: {e}")

        time.sleep(300)  # 5분마다 반복


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
                                {"name": "MYSQL_HOST", "value": os.getenv("MYSQL_HOST")},
                                {"name": "MYSQL_PORT", "value": os.getenv("MYSQL_PORT")},
                                {"name": "MYSQL_USER", "value": "root"},
                                {"name": "MYSQL_PASSWORD", "value": os.getenv("MYSQL_PASSWORD")},
                                {"name": "MYSQL_DATABASE", "value": "carbonetes"},
                                {"name": "TASK_NAME", "value": task_name},
                                {"name": "MINIO_HOST", "value": os.getenv("MINIO_HOST")},
                                {"name": "MINIO_PORT", "value": os.getenv("MINIO_PORT")}
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
    mlTask.print()

    deploy_to_cluster(mlTask.cluster, mlTask.task_name)
    update_k8s_mltask_status_running(mlTask.task_name, "default")
    return {"status": "success", "message": f"{mlTask.task_name} 작업이 생성되었습니다."}, 200

if __name__ == "__main__":
    threading.Thread(target=loop_terminated_updater, daemon=True).start()
    app.run(debug=True, host="0.0.0.0", port=5000)
