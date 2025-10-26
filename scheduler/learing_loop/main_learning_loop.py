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
from get_task_info import get_processed_tasks # [2] 로그 수집
from generate import generate_candidates      # [3] 초기 개체군 형성
from sim_bridge import run_simulation_as_dicts_from_modules # [4] 시뮬레이션(재실행 가상화)
from calculate_fitness import calculate_and_get_best_result
from local_search import local_search_with_sim


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
    candidates_weight = generate_candidates(n=5, include_current=True)# n 가중치 후보 갯수

    # [4] 시뮬레이션(재실행 가상화)
    sim_result = run_simulation_as_dicts_from_modules(task_data, candidates_weight)

    # [5] 성능지표 계산(Fitness)
    best_result = calculate_and_get_best_result(sim_result, 1.00, 0.05)
    # simulation_results, alpha, gamma, use_p95_latency=True
    
    # [6] 지역 탐색 수행
b   est_result = local_search_with_sim(best_result, task_data, alpha=1.0, gamma=0.05, epsilon=0.02)

    # [7] 정책 저장
    save_best_weights_to_db(best_result)
    logging.info(f'Learning Loop: Success Weight Save')


def save_best_weights_to_db(best_result: dict):
    """
    가장 좋은 가중치 조합 하나를 DB에 저장합니다.
    기존 테이블 데이터를 모두 지우고 새로운 최적의 가중치만 추가합니다.

    Args:
        best_result (dict): 'weights'와 'custom_fitness' 키를 포함한 딕셔너리.
    """
    if not best_result:
        print("저장할 최적의 결과가 없습니다.")
        return

    best_weights = best_result['weights']
    print(f"DB에 저장할 최적 가중치: {best_weights}")
    print(f"(근거 Fitness 점수: {best_result['custom_fitness']})")

    connection = None
    try:
        db_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", 3306)),
            "user": "root",
            "password": os.getenv("MYSQL_PASSWORD"),
            "database": "carbonetes"
        }
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # 테이블을 비워서 항상 최신 값만 유지
        cursor.execute("TRUNCATE TABLE weights")
        print("'weights' 테이블의 기존 데이터를 삭제했습니다.")

        # 새로운 최적 가중치 INSERT
        sql = "UPDATE weights SET a_w = %s, b_w = %s, c_w = %s, d_w = %s"
        values = (best_weights['a'], best_weights['b'], best_weights['c'], best_weights['d'])
        cursor.execute(sql, values)
        
        connection.commit()
        
        print("성공적으로 최적 가중치를 'weights' 테이블에 저장했습니다.")

    except Error as e:
        print(f"DB 작업 중 오류 발생: {e}")
        if connection and connection.is_connected():
            connection.rollback()

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            # print("MySQL 연결이 닫혔습니다.")