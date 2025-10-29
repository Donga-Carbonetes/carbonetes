import mysql.connector
import os
import random
import copy


db_config = {
    "host": "211.253.31.134",
    "port": "30529",
    "user": "root",
    "password": "12341234",
    "database": "carbonetes",
    "charset": "utf8"  # 문자 인코딩 설정 추가
}


def connect_db():
    """
    db_config 딕셔너리를 사용하여 데이터베이스에 연결합니다.
    """
    # **db_config는 딕셔너리의 모든 항목을 키워드 인자로 풀어줍니다.
    return mysql.connector.connect(**db_config)

# -------------------------------------------
# 최근 가중치 로드 (변경 없음)
# -------------------------------------------


def get_current_weight():
    conn = connect_db()
    # 결과를 딕셔너리 형태로 받기 위해 cursor 생성 시 dictionary=True 옵션을 사용합니다.
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM weights LIMIT 1;")  # 가장 최근 1개
    result = cursor.fetchone()
    conn.close()
    return result

# -------------------------------------------
# 돌연변이 (변경 없음)
# -------------------------------------------


def mutate(weight_dict, mutation_rate=0.05):
    return {
        k: min(1.0, max(0.0, v + random.uniform(-mutation_rate, mutation_rate)))
        for k, v in weight_dict.items()
    }

# -------------------------------------------
# 교배 (변경 없음)
# -------------------------------------------


def crossover(parent1, parent2):
    return {k: (parent1[k] + parent2[k]) / 2.0 for k in parent1}

# -------------------------------------------
# 지역 탐색 (선택적) (변경 없음)
# -------------------------------------------


def local_search(base_weight, epsilon=0.01):
    best = copy.deepcopy(base_weight)
    for k in best:
        for delta in [-epsilon, epsilon]:
            neighbor = copy.deepcopy(best)
            neighbor[k] = min(1.0, max(0.0, neighbor[k] + delta))
    return best

# -------------------------------------------
# 후보 5개 생성 (변경 없음)
# -------------------------------------------


def generate_candidates(n=5, use_local_search=True, include_current=True):
    current = get_current_weight()
    print("[현재 가중치]", current)
    candidates = []

    if include_current:
        # DB의 현재 가중치 1개를 가장 첫 번째로 추가
        candidates.append(current)

    for _ in range(n):
        mutated = mutate(current)
        crossed = crossover(current, mutated)
        improved = local_search(crossed) if use_local_search else crossed
        candidates.append(improved)

    return candidates


# -------------------------------------------
# 메인 실행 (변경 없음)
# -------------------------------------------
if __name__ == "__main__":
    candidates = generate_candidates(n=5)
    print("[생성된 5개 후보]")
    for i, c in enumerate(candidates, 1):
        print(f"{i}. {c}")
