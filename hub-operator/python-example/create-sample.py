# create_mltask.py
from kubernetes import client, config
from datetime import datetime

config.load_kube_config()  # 클러스터 외부에서 실행 시
# config.load_incluster_config()  # 클러스터 내부에서 실행 시

def create_mltask(script: str, datashape: list, dataset_size: int, label_count: int, namespace="default"):
    task_name = f"mltask-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    body = {
        "apiVersion": "ml.carbonetes.io/v1",
        "kind": "MLTask",
        "metadata": {
            "name": task_name,
        },
        "spec": {
            "datashape": datashape,
            "dataset_size": dataset_size,
            "label_count": label_count,
            "script": script
        }
    }

    api = client.CustomObjectsApi()
    api.create_namespaced_custom_object(
        group="ml.carbonetes.io",
        version="v1",
        namespace=namespace,
        plural="mltasks",
        body=body
    )
    print(f"✅ MLTask {task_name} 생성 완료")
    return task_name
