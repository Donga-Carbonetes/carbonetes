import torch
import pprint
import sample_resnet as target  # sample_resnet.py의 내용을 가져옴
import torch
import torch.nn as nn
import torch.optim as optim
import torch.profiler
import time

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
        "train_size": 50000,
        "input_shape": [3,32,32],
        "label_count" : 10
    }

    profile = {
        "model": model_info,
        "hyperparameters": hyperparams,
        "dataset": dataset_info
    }

    return profile

def profiling(profile):
    model = target.network
    model = model.to(profile['hyperparameters']['device'])
    model.train()

    dummy_shape = profile['dataset']['input_shape']
    dummy_input = torch.randn(profile['hyperparameters']['batch_size'],dummy_shape[0], dummy_shape[1],dummy_shape[2]).cuda()
    dummy_target = torch.randint(0,profile['dataset']['label_count'], (profile['hyperparameters']['batch_size'],)).cuda()


    loss_function = target.loss_function
    optimizer = target.optimizer


    with torch.profiler.profile(
        activities=[
            torch.profiler.ProfilerActivity.CPU,
            torch.profiler.ProfilerActivity.CUDA],
        record_shapes=True,
        profile_memory=True,
        with_stack=True,
        with_flops=True,   # (선택) FLOPS도 계산
    ) as prof:
        # 학습 루프 한 번
        start_time = time.time()
        optimizer.zero_grad()
        output = model(dummy_input)
        loss = loss_function(output, dummy_target)
        loss.backward()
        optimizer.step()
        end_time = time.time()

    steps = profile['dataset']['train_size'] // profile['hyperparameters']['batch_size']
    t = (end_time - start_time) * steps
    return t

if __name__ == "__main__":
    profile = extract_training_profile(
        model=target.network,
        optimizer=target.optimizer,
        loss_fn=target.loss_function,
        batch_size=target.batch_size,
        epochs=target.training_epochs,
        device=target.device if hasattr(target, "device") else ("cuda" if torch.cuda.is_available() else "cpu")
    )

    pprint.pprint(profile)

    for i in range(10):
        t = profiling(profile)
        print(f'Time = {t:.2f} sec')
        
    # 출력되는 time 중 중간값을 사용하기
    # 여기서 스케줄러나 데이터베이스에 정보를 전달하는 코드 작성하기
    
