from kubernetes import client, config
from datetime import datetime
import uuid
import mysql.connector
import time

config.load_kube_config()

def main():
    unique_id = uuid.uuid4().hex
    task_name = f"mltask-{unique_id}"

    def create_mltask_from_file(script_path, datashape, dataset_size, label_count, namespace="default"):
        script_content = None
        with open(script_path, 'r') as f:
            script_content = f.read()
        
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


    db_config = {
        "host": '211.253.31.134',
        "port": '30529',
        "user": 'root',
        "password": '12341234',
        "database": 'carbonetes'
    }

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    insert_query = """
        INSERT INTO task_info (id,task_name, data_shape, dataset_size, label_count)
        VALUES (%s, %s, %s, %s, %s)
    """

    cursor.execute(insert_query, (unique_id, task_name, "[1,28,28]", 60000, 10))
    conn.commit()
    cursor.close()
    conn.close()

    create_mltask_from_file(
        script_path="/carbonetes/tester/learn.py",
        datashape=[1,28,28],
        dataset_size=60000,
        label_count=10
    )


for i in range(10):
    main()
    time.sleep(30) # 2초의 시간을 두고 보내기




