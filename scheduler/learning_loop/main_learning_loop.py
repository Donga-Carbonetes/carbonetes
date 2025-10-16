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


# DB Configuration
db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": "carbonetes"
}


# 함수 도입 부
def learning_loop(): 
    logging.info("[학습기]학습을 시작합니다.")
    
    # [2] 로그 수집
    task_data = get_processed_tasks(db_config)
    logging.info(task_data)
    logging.info("[학습기] [2] 로그 수집 완료")
     
    # [3] 초기 개체군 형성
    candidates_weight = generate_candidates(n=5, include_current=True)# n 가중치 후보 갯수
    logging.info(candidates_weight)
    logging.info("[학습기] [3] 초기 개체군 형성 완료")
    
    # [4] 시뮬레이션(재실행 가상화)
    sim_result = run_simulation_as_dicts_from_modules(task_data, candidates_weight)
    logging.info(sim_result)
    logging.info("[학습기] [4] 시뮬레이션 완료")

    # [5] 성능지표 계산(Fitness)
    best_result = calculate_and_get_best_result(sim_result, 1.00, 0.05)
    # simulation_results, alpha, gamma, use_p95_latency=True
    logging.info(best_result)
    logging.info("[학습기] [5] 성능지표 계산 완료")

    # [7] 정책 저장
    save_best_weights_to_db(best_result)
    logging.info("[학습기] [7] 정책 저장 완료")
    logging.info(f'Learning Loop: Success Weight Save')


def save_best_weights_to_db(best_result: dict):
    """
    가장 좋은 가중치 조합 하나를 DB에 저장합니다.
    기존 테이블 데이터를 모두 지우고 새로운 최적의 가중치만 추가합니다.

    Args:a
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


#################################################################
# 이 스크립트가 직접 실행될 때 learning_loop() 함수를 호출합니다.
#################################################################
if __name__ == "__main__":
    # 로깅 기본 설정 (레벨, 포맷 등)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 메인 학습 루프 실행
    learning_loop()