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
from generate import generate_candidates
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
    candidates_weight = generate_candidates(n=5) # n 가중치 후보 갯수

    # [4] 시뮬레이션(재실행 가상화)
    sim_result = simulater()

