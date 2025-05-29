# task_processor.py
import logging
import time
import os
import math
import time
from carbon_collector.carbon_fetch_model import get_carbon_info
from resource_collector.new_collector import get_resource_usage
from dotenv import load_dotenv
load_dotenv()

kluster_nodes = ["K3S1", "K3S2"] # Slave Node 
kluster_region = ["KR", "DE"] # Nodes Location K3S1: KR , K3S2: DE

class Node:
    def __init__(self, name):
        self.name = name
        self.assigned_time = 0  # 남은 작업 시간 (초)
        self.last_updated = time.time()

    def update_remaining_time(self):
        now = time.time()
        elapsed = now - self.last_updated
        self.assigned_time = max(0, self.assigned_time - elapsed)
        self.last_updated = now

    def assign_task(self, task_duration):
        self.update_remaining_time()
        self.assigned_time += task_duration
        print(f"✅ 작업 {task_duration}s 배정됨 → 노드 {self.name}, 남은 시간: {self.assigned_time:.2f}s")

    def get_remaining_time(self):
        self.update_remaining_time()
        return self.assigned_time


# 패널티 조정치 
a_w = 1
b_w = 1
c_w = 1
d_w = 1


def process_task(task_name, estimated_time):
    result_score = []
    nodes_rsc_list = []
    nodes_crb_list = []
    logging.info(f"처리 시작 - 작업 이름: {task_name}, 예상 시간: {estimated_time}초")
    try:
        # 정보 추출 항
        for node, region in kluster_nodes, kluster_region:
            # 엔드포인트 선
            endpoint = f"{node}_NODE_EXPORTERS"
            endpoint = os.getenv(endpoint)
            # 리소스 추출
            cpu, ram = get_resource_usage(endpoint)
            nodes_rsc_list.append((cpu+ram)/2)  # 일단 CPU, RAM 백분율 평균 사용 
            # 탄소집약도 추출
            nodes_crb_list.append(get_carbon_info(estimated_time, country_code=region))

        
        for idx in range(len(kluster_nodes)):
            # 실행 중인 노드 수 계산 항
            temp = nodes_rsc_list
            temp[idx] = 50 # 배치된 값 임의 부여
            count = sum(1 for n in temp if n <= 26)

            # 지수 패널티 항 
            penalty = b_w * math.exp(nodes_rsc_list)



            

        time.sleep(estimated_time)
        logging.info(f"처리 완료 - 작업 이름: {task_name}")
        
    except Exception as e:
        logging.error(f"작업 처리 중 오류 발생 - 작업 이름: {task_name}, 에러: {e}")