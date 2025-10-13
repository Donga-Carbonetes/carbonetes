import pymysql
import os
from dotenv import load_dotenv
import random
import copy


load_dotenv()

def connect_db():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "carbonetes"),
        charset='utf8'
    )

# -------------------------------------------
# 최근 가중치 로드
# -------------------------------------------
def get_current_weight():
    conn = connect_db()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM weights LIMIT 1;")  # 가장 최근 1개
    result = cursor.fetchone()
    conn.close()
    return result

# -------------------------------------------
# 돌연변이
# -------------------------------------------
def mutate(weight_dict, mutation_rate=0.05):
    return {
        k: min(1.0, max(0.0, v + random.uniform(-mutation_rate, mutation_rate)))
        for k, v in weight_dict.items()
    }

# -------------------------------------------
# 교배
# -------------------------------------------
def crossover(parent1, parent2):
    return {k: (parent1[k] + parent2[k]) / 2.0 for k in parent1}

# -------------------------------------------
# 지역 탐색 (선택적)
# -------------------------------------------
def local_search(base_weight, epsilon=0.01):
    best = copy.deepcopy(base_weight)
    for k in best:
        for delta in [-epsilon, epsilon]:
            neighbor = copy.deepcopy(best)
            neighbor[k] = min(1.0, max(0.0, neighbor[k] + delta))
    return best

# -------------------------------------------
# 후보 5개 생성
# -------------------------------------------
def generate_candidates(n=5, use_local_search=True):
    current = get_current_weight()
    print("[현재 가중치]", current)
    candidates = []

    for _ in range(n):
        mutated = mutate(current)
        crossed = crossover(current, mutated)
        improved = local_search(crossed) if use_local_search else crossed
        candidates.append(improved)

    return candidates

# -------------------------------------------
# 메인 실행 
# -------------------------------------------
if __name__ == "__main__":
    candidates = generate_candidates(n=5)
    print("[생성된 5개 후보]")
    for i, c in enumerate(candidates, 1):
        print(f"{i}. {c}")
