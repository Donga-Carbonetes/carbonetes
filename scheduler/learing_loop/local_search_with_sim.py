# local_search_with_sim.py
# --------------------------------------------------------
# 시뮬레이션 기반 지역 탐색 (Memetic Algorithm의 Local Search 단계)
# --------------------------------------------------------

from copy import deepcopy
from sim_bridge import run_simulation_as_dicts_from_modules
from calculate_fitness import calculate_and_get_best_result

def local_search_with_sim(best_result, task_data, alpha=1.0, gamma=0.05, epsilon=0.02):
    """
    시뮬레이션 기반 지역 탐색.
    best_result(가장 좋은 가중치)를 기준으로 ±epsilon씩 변화시켜 더 나은 후보를 탐색합니다.

    Args:
        best_result (dict): calculate_fitness에서 반환된 best_result (custom_fitness 포함)
        task_data (list): get_task_info()로 불러온 작업 데이터
        alpha (float): 탄소 항 가중치
        gamma (float): 지연시간 항 가중치
        epsilon (float): 탐색 범위 (가중치를 ±epsilon 만큼 변화)
    """
    base_weights = deepcopy(best_result["weights"])
    best_score = best_result["custom_fitness"]
    improved = False

    print("\n[지역 탐색 시작] 기준 가중치:", base_weights)

    for k in base_weights.keys():
        for delta in [-epsilon, epsilon]:
            neighbor = deepcopy(base_weights)
            neighbor[k] = max(0.0, min(1.0, neighbor[k] + delta))  # 0~1 사이로 제한

            # 시뮬레이션 실행
            neighbor_result = run_simulation_as_dicts_from_modules(task_data, [neighbor])
            evaluated = calculate_and_get_best_result(neighbor_result, alpha, gamma)

            print(f" - 탐색 중 {k} 변경 ({'+' if delta>0 else '-'}{epsilon}): fitness={evaluated['custom_fitness']}")

            if evaluated["custom_fitness"] < best_score:
                best_result = evaluated
                best_score = evaluated["custom_fitness"]
                improved = True
                print(f"   ✅ 개선됨! ({k}: {neighbor[k]}) → 새로운 best fitness={best_score}")

    if not improved:
        print("[지역 탐색 결과] 개선 없음 (현재 조합이 최적)")
    else:
        print("[지역 탐색 결과] 새로운 최적 가중치 발견!")

    return best_result
