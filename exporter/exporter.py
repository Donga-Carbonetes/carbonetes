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
import uuid

def load_user_module(path="/mnt/main.py"):
    spec = importlib.util.spec_from_file_location("user_module", path)
    user_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(user_module)
    return user_module

def make_task_name_with_UUID(model_name: str) -> str:
    unique_id = uuid.uuid4().hex
    return f"task-{model_name}-{unique_id}"

def extract_training_profile(model, optimizer, loss_fn, batch_size, epochs, device):
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
        "dataset_size": 50000,
        "data_shape": [3, 32, 32],
        "label_count": 10
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


if __name__ == "__main__":
    load_dotenv()
    user_module = load_user_module("E:\carbonetes\exporter\sample_resnet.py")

    # 추출
    profile = extract_training_profile(
        model=user_module.network,
        optimizer=user_module.optimizer,
        loss_fn=user_module.loss_function,
        batch_size=user_module.batch_size,
        epochs=user_module.training_epochs,
        device=user_module.device if hasattr(user_module, "device") else ("cuda" if torch.cuda.is_available() else "cpu")
    )

    pprint.pprint(profile)

    # 시간 측정
    times = []
    for i in range(10):
        t = profiling(profile, user_module.network, user_module.optimizer, user_module.loss_function)
        print(f"[{i+1}/10] Time = {t:.2f} sec")
        times.append(t)

    standard_time = times[5]

    # DB 연결
    db_config = {
        "host": os.getenv("MYSQL_HOST"),
        "port": int(os.getenv("MYSQL_PORT")),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE")
    }

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO task_info (task_name, data_shape, dataset_size, label_count, estimated_time)
    VALUES (%s, %s, %s, %s, %s)
    """

    task_name = make_task_name_with_UUID(profile['model']['model_name'])
    data_shape = str(profile['dataset']['data_shape'])
    dataset_size = profile['dataset']['dataset_size']
    label_count = profile['dataset']['label_count']
    estimated_time = standard_time * profile['hyperparameters']['epochs']

    cursor.execute(insert_query, (task_name, data_shape, dataset_size, label_count, estimated_time))
    conn.commit()

    print(f"✅ DB에 task 등록 완료! ID: {cursor.lastrowid}")

    cursor.close()
    conn.close()
