import numpy as np
import math

# ----------------------------------
# 파라미터 (목적 함수 가중치 계수)
# ----------------------------------
alpha = 1.0     # 노드 수 최소화
beta = 1.0      # 리소스 집중 패널티
gamma = 2.0     # 리소스 집중 민감도
delta = 1.0     # makespan
epsilon = 1.0   # 탄소 배출 최소화

# ----------------------------------
# 예제 노드 및 작업 데이터
# ----------------------------------
nodes = ['A', 'B']
tasks = [
    {'id': 'T1', 'duration': 2},
    {'id': 'T2', 'duration': 3},
    {'id': 'T3', 'duration': 1}
]

# 시간 슬롯
time_slots = list(range(0, 8))  # 시간 단위 (0 ~ 7)

# 시간대별 탄소 집약도 (예측 기반)
carbon_intensity = {
    'A': [500 - 50 * math.sin(math.pi * t / 12) for t in time_slots],
    'B': [450 + 20 * math.cos(math.pi * t / 6) for t in time_slots],
}

# 노드별 사용률 초기값 (작업 할당 후 갱신됨)
node_usage = {n: [0] * len(time_slots) for n in nodes}
used_nodes = set()
schedule = []

# ----------------------------------
# 작업 할당 함수
# ----------------------------------
def compute_objective(n, start, task_duration):
    ci = carbon_intensity[n]
    usage = node_usage[n]

    # 탄소 배출량
    carbon = sum(ci[start:start + task_duration])

    # 리소스 사용률 최대값 (예: 작업 1개 = 100% CPU)
    new_usage = usage[:]
    for i in range(start, start + task_duration):
        new_usage[i] += 1.0  # 1단위 CPU 사용률 (가중치화 가능)

    max_usage = max(new_usage)
    resource_penalty = math.exp(gamma * max_usage)

    # makespan은 가장 마지막 할당 시각
    end_time = start + task_duration
    return (
        alpha * (1 if n not in used_nodes else 0) +
        beta * resource_penalty +
        delta * end_time +
        epsilon * carbon
    )

# ----------------------------------
# 작업 스케줄링 시작
# ----------------------------------
for task in tasks:
    best = None
    best_score = float('inf')

    for node in nodes:
        for t in time_slots:
            if t + task['duration'] > len(time_slots):
                continue

            score = compute_objective(node, t, task['duration'])

            if score < best_score:
                best_score = score
                best = {'task': task['id'], 'node': node, 'start': t, 'end': t + task['duration'], 'score': score}

    # 할당 기록
    schedule.append(best)
    used_nodes.add(best['node'])
    for i in range(best['start'], best['end']):
        node_usage[best['node']][i] += 1.0  # 자원 사용 기록

# ----------------------------------
# 결과 출력
# ----------------------------------
print("📋 최종 스케줄")
for s in schedule:
    print(f"{s['task']} → {s['node']} @ {s['start']}~{s['end']} (목적 함수 값: {s['score']:.2f})")