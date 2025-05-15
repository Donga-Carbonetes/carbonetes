import importlib.util
import torch
import pprint
import torch.nn as nn
import torch.optim as optim
import torch.profiler
import time
import os
from dotenv import load_dotenv
import mysql.connector
import ast
from minio import Minio
from minio.error import S3Error
from kubernetes import client, config


def load_user_module(path="/mnt/main.py"):
    spec = importlib.util.spec_from_file_location("user_module", path)
    user_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(user_module)
    return user_module

def export_data(result):
    if result:
        raw_shape, dataset_size, label_count = result
        data_shape = ast.literal_eval(raw_shape)
        return (dataset_size, data_shape, label_count)
    return None


def extract_training_profile(model, optimizer, loss_fn, batch_size, epochs, device, dataset_size, data_shape, label_count):
    model_info = {
        "model_name": model.__class__.__name__
    }

    hyperparams = {
        "batch_size": batch_size,
        "epochs": epochs,
        "learning_rate": optimizer.param_groups[0].get('lr', None),
        "optimizer": optimizer.__class__.__name__,
        "loss_function": loss_fn.__class__.__name__,
        "device": device,
    }

    dataset_info = {
        "dataset_size": dataset_size,
        "data_shape": data_shape,
        "label_count": label_count
    }

    profile = {
        "model": model_info,
        "hyperparameters": hyperparams,
        "dataset": dataset_info
    }

    return profile

def profiling(profile, model, optimizer, loss_function):
    model = model.to(profile['hyperparameters']['device'])
    model.train()

    shape = profile['dataset']['data_shape']
    batch = profile['hyperparameters']['batch_size']
    labels = profile['dataset']['label_count']

    dummy_input = torch.randn(batch, shape[0], shape[1], shape[2]).to(profile['hyperparameters']['device'])
    dummy_target = torch.randint(0, labels, (batch,)).to(profile['hyperparameters']['device'])

    with torch.profiler.profile(
        activities=[
            torch.profiler.ProfilerActivity.CPU,
            torch.profiler.ProfilerActivity.CUDA
        ],
        record_shapes=True,
        profile_memory=True,
        with_stack=True,
        with_flops=True,
    ) as prof:
        start_time = time.time()
        optimizer.zero_grad()
        output = model(dummy_input)
        loss = loss_function(output, dummy_target)
        loss.backward()
        optimizer.step()
        end_time = time.time()

    steps = profile['dataset']['dataset_size'] // batch
    return (end_time - start_time) * steps

def upload_file_minio(local_file_path, task_name):
    minio_host = os.getenv("MINIO_HOST")
    minio_port = os.getenv("MINIO_PORT")
    minio_user = os.getenv("MINIO_USER")
    minio_password = os.getenv("MINIO_PASSWORD")

    host = f"{minio_host}:{minio_port}"
    client = Minio(
    host,
    access_key=minio_user,
    secret_key=minio_password,
    secure=False
    )

    bucket_name = "mybucket"
    object_name = f"{task_name}.py"
    
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
    
    try:
        client.fput_object(bucket_name, object_name, local_file_path)
        print(f"✅ '{object_name}' 업로드 성공")
    except S3Error as e:
        print(f"❌ 업로드 실패: {e}")


def update_k8s_mltask_status(name, namespace):
    config.load_incluster_config()
    api = client.CustomObjectsApi()

    group="ml.carbonetes.io",
    version="v1",
    namespace='default',
    plural="mltasks",
    body = {
        "status": {
            "phase": 'ready'
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
        print(f"✅ mltask '{name}' 상태를 'ready'로 업데이트 했습니다.")
    except Exception as e:
        print(f"❌ mltask 상태 업데이트 실패: {e}")
                



if __name__ == "__main__":
    load_dotenv()
    task_name = os.getenv("TASK_NAME")

    local_path = f"/mnt/{task_name}.py" # for docker 
    # local_path = "E:\carbonetes\exporter\sample_resnet.py" # for local test

    user_module = load_user_module(local_path) 
    

        # DB 연결
    db_config = {
        "host": os.getenv("MYSQL_HOST"),
        "port": int(os.getenv("MYSQL_PORT")),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE")
    }

    dataset_size = None
    data_shape = None
    label_count = None


    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    query = """
    SELECT data_shape, dataset_size, label_count
    FROM task_info
    WHERE task_name = %s
    """
    cursor.execute(query, (task_name,))
    result = cursor.fetchone()
    dataset_size, data_shape, label_count = export_data(result)
    
    # 추출
    profile = extract_training_profile(
        model=user_module.network,
        optimizer=user_module.optimizer,
        loss_fn=user_module.loss_function,
        batch_size=user_module.batch_size,
        epochs=user_module.training_epochs,
        device=user_module.device if hasattr(user_module, "device") else ("cuda" if torch.cuda.is_available() else "cpu"),
        dataset_size=dataset_size,
        data_shape=data_shape,
        label_count=label_count
    )

    pprint.pprint(profile)

    # 시간 측정
    times = []
    for i in range(10):
        t = profiling(profile, user_module.network, user_module.optimizer, user_module.loss_function)
        print(f"[{i+1}/10] Time = {t:.2f} sec")
        times.append(t)

    standard_time = times[5]

    update_query = """
    UPDATE task_info SET estimated_time=%s, status='ready' WHERE task_name=%s
    """

    estimated_time = standard_time * profile['hyperparameters']['epochs']

    cursor.execute(update_query, (estimated_time, task_name))
    conn.commit()

    print(f"✅ DB에 task 업데이트 완료!")

    update_k8s_mltask_status(task_name, 'default')

    cursor.close()
    conn.close()

    # minio에 파일 업로드하기
    upload_file_minio(local_path, task_name)

    # 끝나고 스케줄러에 새로운 작업이 생겼다고 알려주기
