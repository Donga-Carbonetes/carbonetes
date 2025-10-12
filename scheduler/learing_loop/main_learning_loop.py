################################################
# Memetic Algorithm (메머틱 알고리즘) 프로젝트의 학습기(Learning Loop) 코드입니다.
################################################

import os
import logging
import random 
import copy 
import mysql.connector
from mysql.connector import Error


# Module import 
from get_task_info import get_processed_tasks

# DB Configuration
db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": "carbonetes"
}


# 함수 도입 부
def learning_loop(task_name, estimated_time): 
    logging.info("[학습기]학습을 시작합니다.")
    
    # [2] 로그 수집
    task_data = get_processed_tasks(db_config)

    # [3] 초기 개체군 형성






# [3] 초기 가중치 생성 + [6] 최적 가중치 탐색 (메모틱 알고리즘)
# 1. 현재 운영 중인 가중치 (DB에서 읽어 오거나 수정하겠습니다. 총합이 1이되도록 그냥 제가 가정한것임)
# ------------------------------
current_weights = {
    "a": 0.25,  # 활성화중인 노드 수(적게 쓰면 좋음)
    "b": 0.25,  # CPU 과부화(피하면 좋음)
    "c": 0.25,  # Workspan작업 지연시간(실행시간 짧으면 좋음)
    "d": 0.25   # 탄소비용(적으면 좋음)
}

# ------------------------------
# 2. 초기 세대 생성 (현재 가중치 + 랜덤)
# ------------------------------
def generate_initial_population(size=6): # 초기 후보 가중치만듦. 총 6개정도
    population = []
    population.append(current_weights)  # 현재 정책 포함

    for _ in range(size - 1): #5개만 랜덤 하나는 운영가중치
        a = round(random.uniform(0.1, 0.5), 2) 
        b = round(random.uniform(0.1, 0.5), 2)
        c = round(random.uniform(0.1, 0.5), 2)
        d = round(1 - a - b - c, 2)
        weights = {"a": a, "b": b, "c": c, "d": d}
        population.append(weights)

    return population

# ------------------------------
# 3. 점수 함수 (Fitness 계산용)
#    실제로는 시뮬레이션으로 계산할 예정이나 지금은 예시용으로 간단히 작성
# ------------------------------
def evaluate_fitness(weights):
    # 예시로는 단순히 d(탄소) 비중이 높은 쪽을 더 유리하다고 가정
    return 1.0 - weights["d"] + random.uniform(0, 0.1)  # d가 높을수록 좋음

# ------------------------------
# 4. Crossover (교배)
# ------------------------------
def crossover(w1, w2): #부모(w1,w2)의 평균값으로 자식 가중치 만들기
    child = {}
    for key in w1:
        child[key] = round((w1[key] + w2[key]) / 2, 2)
    return child

# ------------------------------
# 5. Mutation (돌연변이)
# ------------------------------
def mutate(weights, mutation_rate=0.2):#일정 확률(20%)로 랜덤 변경
    new_weights = copy.deepcopy(weights)
    if random.random() < mutation_rate:
        #랜덤한 항목 하나를 골라서 값에 변화(±0.1)를 줌
        key = random.choice(list(new_weights.keys()))
        change = round(random.uniform(-0.1, 0.1), 2)
        new_weights[key] = max(0.0, min(1.0, new_weights[key] + change))

        total = sum(new_weights.values())
        for k in new_weights:
            new_weights[k] = round(new_weights[k] / total, 2)

    return new_weights

# ------------------------------
# 6. Local Search (지역 탐색)
# ------------------------------
def local_search(weights):
    best = weights
    best_score = evaluate_fitness(best)

    for _ in range(3):  # 작은 범위에서 여러 번 시도
        candidate = mutate(best)
        score = evaluate_fitness(candidate)
        if score < best_score:
            best = candidate
            best_score = score

    return best

# ------------------------------
# 7. 메모틱 알고리즘 본체
# ------------------------------
def memetic_optimization(generations=5, pop_size=6):
    population = generate_initial_population(size=pop_size)

    for gen in range(generations):# 각후보의 잠수 계산후 낮은 순으로 정렬
        scored = [(evaluate_fitness(w), w) for w in population]
        scored.sort(key=lambda x: x[0])  # 점수가 낮을수록 좋은 것으로 가정
        print(f"세대 {gen}: 최고 점수 = {scored[0][0]:.4f}, 가중치 = {scored[0][1]}")

        survivors = [w for _, w in scored[:pop_size//2]] # 상위 절반만 생존자
        new_population = []
        # 생존자 중에서 모작위 두명 : 교배 -> 돌연변이 -> 지역탐색-> 새로운 자식 추가
        while len(new_population) < pop_size:
            p1, p2 = random.sample(survivors, 2)
            child = crossover(p1, p2)
            child = mutate(child)
            child = local_search(child)
            new_population.append(child)
        # 새로운 population 대체 후 다음 세대 이동
        population = new_population

    best_score, best_weights = scored[0]
    return best_weights # 최적의 가중치 반환

# ------------------------------
# 8. 실행 예시
# ------------------------------
if __name__ == "__main__":
    best_weights = memetic_optimization()
    print("\n최적 가중치 조합:", best_weights)

