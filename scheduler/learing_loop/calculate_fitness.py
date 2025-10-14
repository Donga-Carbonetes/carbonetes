def calculate_and_get_best_result(simulation_results, alpha, gamma, use_p95_latency=True):
    """
    시뮬레이션 결과 리스트에 대해 새로운 fitness 점수를 계산하고,
    그중 가장 좋은 결과(가장 낮은 점수) 하나만 반환합니다.

    Args:
        simulation_results (list): 시뮬레이션 결과 딕셔너리의 리스트.
        alpha (float): 총 탄소 배출량(Total Carbon)에 적용될 가중치.
        gamma (float): 지연 시간(Latency)에 적용될 가중치.
        use_p95_latency (bool): True이면 P95 Latency를, False이면 Mean Latency를 사용합니다.

    Returns:
        dict: 'custom_fitness'가 추가된 가장 좋은 결과 딕셔너리.
              입력 리스트가 비어있으면 None을 반환합니다.
    """
    if not simulation_results:
        return None

    updated_results = []
    for result in simulation_results:
        total_carbon = result['total_carbon']
        
        # 사용할 지연시간 선택
        latency = result['p95_latency'] if use_p95_latency else result['mean_latency']

        # 요청된 수식: α * Total Carbon + γ * Latency
        custom_fitness = (alpha * total_carbon) + (gamma * latency)
        
        new_result = result.copy()
        new_result['custom_fitness'] = round(custom_fitness, 4)
        updated_results.append(new_result)
        
    # 'custom_fitness' 점수가 가장 낮은 딕셔너리를 찾아 반환
    best_result = min(updated_results, key=lambda x: x['custom_fitness'])
    
    return best_result
