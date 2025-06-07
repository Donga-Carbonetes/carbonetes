# task_processor.py
import logging
import time
import os
import math
import time
import csv
from datetime import datetime, timedelta

# For Test 
import random

from carbon_collector.carbon_fetch_model import get_carbon_info
from resource_collector.new_collector import get_resource_usage
from dotenv import load_dotenv
load_dotenv()

kluster_nodes = ["K3S1", "K3S2", "NEWK3S1"] # Slave Node 
kluster_region = ["KR", "JP", "FR"] # Nodes Location K3S1: KR , K3S2: FR
kluster_name = ["k3s-1", "k3s-2", "new-k3s-1"]
 
# 로그 CSV 파일 초기화 (최초 실행 시 헤더 작성)
csv_file = "task_log.csv"
if not os.path.exists(csv_file):
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            "timestamp", "task_name", "node", "resource_usage_avg",
            "active_node_count", "penalty", "workspan",
            "carbon_emission", "score"
        ])

class Node:
    def __init__(self, name):
        self.name = name
        self.expected_finish_at = None  # 작업 종료 시각

    def get_remaining_time(self):
        if self.expected_finish_at is None:
            return 0
        remaining = (self.expected_finish_at - datetime.now()).total_seconds()
        return max(0, remaining)

    def assign_task(self, task_duration):  # 초 단위
        now = datetime.now()
        remaining = self.get_remaining_time()
        self.expected_finish_at = now + timedelta(seconds=remaining + task_duration)
        print(f"✅ 작업 {task_duration}s 배정됨 → 노드 {self.name}, 종료 예정: {self.expected_finish_at}")



nodes = {name: Node(name) for name in kluster_nodes}

def get_max_remaining_time():
    max_node = max(nodes.values(), key=lambda n: n.get_remaining_time())
    return max_node.name, max_node.get_remaining_time()


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
        for node, region in zip(kluster_nodes, kluster_region):
            # 엔드포인트 선
            endpoint = f"{node}_NODE_EXPORTERS"
            endpoint = os.getenv(endpoint)
            # 리소스 추출
            cpu, ram = get_resource_usage(endpoint)
            count_tmp = 0
            while True:
                if cpu < 0 or ram < 0: # 음수 결과 반환 시 재시도 
                    cpu, ram = get_resource_usage(endpoint)
                    count_tmp = count_tmp + 1
                elif count_tmp == 4:
                    break
                else:
                    break
            

            nodes_rsc_list.append((cpu+ram)/2)  # 일단 CPU, RAM 백분율 평균 사용 
            # 탄소집약도 추출
            carbon_info = get_carbon_info(estimated_time, country_code=region)
            carbon_value = carbon_info.get("integratedEmission", 0)
            nodes_crb_list.append(carbon_value)

        for idx in range(len(kluster_nodes)):

            # 실행 중인 노드 수 계산 항
            # 노드 리소스 리스트 복사
            temp = nodes_rsc_list[:]  # 또는 list(nodes_rsc_list)

            # 현재 작업이 배치된다고 가정하고 해당 노드 리소스 값을 50%로 임의 설정
            temp[idx] = 50  

            # 8.5 이상 사용중인 노드로 표기 
            count = sum(1 for n in temp if n >= 8.5)
            work_nodes = a_w * count
            logging.info(f"노드 수 (가용 노드 수): {work_nodes}")



            # 리소스 사용률 제한 85% 이상 시 미배치 
            if nodes_rsc_list[idx] > 85 :
                with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        time.strftime("%Y-%m-%d %H:%M:%S"),  # timestamp
                        task_name,                           # 작업 이름
                        kluster_nodes[idx],                  # 노드 이름
                        round(nodes_rsc_list[idx], 2),       # 평균 리소스 사용률
                        "-",                                 # active_node_count
                        "-",                                 # penalty
                        "-",                                 # workspan
                        "-",                                 # carbon
                        "미배치 (리소스 초과)"               # score
                        ])

                result_score.append(999999)  # MAX_INT = 999999
                continue
            
            # 지수 패널티 항 
            normalized = nodes_rsc_list[idx] / 100.0  # 0 ~ 1

            penalty = b_w * (10 ** (4 * normalized))  # 10^0 ~ 10^4 ⇒ 1 ~ 10000
            logging.info(f"패널티 : {penalty}")

            # 전체 실행 시간 (현재 노드 기준 예상 소요 시간)
            remaining = nodes[kluster_nodes[idx]].get_remaining_time()
            workspan = remaining + estimated_time
            workspan = c_w * workspan
            logging.info(f"실행 시간 : {workspan}")

            workspan = c_w * workspan
            logging.info(f"실행 시간 : {workspan}")

            # 시간 기반 탄소 배출량 최소화 항 
            carbon = d_w * nodes_crb_list[idx]
            logging.info(f"탄소 배출량 : {carbon}")


            # 다목적 함수의 최소 값 
            result_score.append(work_nodes + penalty + workspan + carbon)

            # CSV 로그 저장
            with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([
                    time.strftime("%Y-%m-%d %H:%M:%S"),  # timestamp
                    task_name,                           # 작업 이름
                    kluster_nodes[idx],                  # 노드 이름
                    round(nodes_rsc_list[idx], 2),       # 평균 리소스 사용률
                    work_nodes,                          # 활성 노드 수
                    round(penalty, 2),                   # 패널티
                    round(workspan, 2),                  # 예상 실행 시간
                    round(carbon, 6),                    # 탄소 배출량
                    round(work_nodes + penalty + workspan + carbon, 2)                      # 총 점수
                ])

        
        logging.info(result_score)
        result_idx = min(range(len(result_score)), key=lambda i: sum(result_score))
        logging.info(f"처리 완료 - 작업 이름: {task_name}")


        # Return
        # 노드 이름과 점수를 dict로 매핑
        score_dict = {kluster_name[i]: result_score[i] for i in range(len(kluster_name))}

        # 점수가 999999인 노드 제거
        score_dict = {k: v for k, v in score_dict.items() if v != 999999}

        # 남은 노드 중 하나를 무작위로 선택
        if score_dict:
            return random.choice(list(score_dict.keys()))
        else:
            logging.warning("모든 노드가 미배치 상태입니다.")
            return "no_available"  # 또는 예외처리
        
    except Exception as e:
        logging.error(f"작업 처리 중 오류 발생 - 작업 이름: {task_name}, 에러: {e}")