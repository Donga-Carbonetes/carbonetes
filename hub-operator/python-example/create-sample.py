from kubernetes import client, config
from datetime import datetime

config.load_kube_config()

def create_mltask_from_file(script_path, datashape, dataset_size, label_count, namespace="default"):
    script_content = None
    with open(script_path, 'r') as f:
        script_content = f.read()

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
            "script": script_content  
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


create_mltask_from_file(
    script_path="/carbonetes/exporter/sample_resnet.py",
    datashape=[3, 32, 32],
    dataset_size=50000,
    label_count=10
)
