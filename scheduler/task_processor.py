import logging
import time
import os
import sys
import math
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(BASE_DIR, '..'))
sys.path.append(BASE_DIR)
sys.path.append(PARENT_DIR)

load_dotenv()

# 클러스터 정보
kluster_nodes = ["K3S1", "K3S2"]
kluster_region = ["KR", "FR"]
kluster_name = ["k3s-1", "k3s-2"]

# 가중치 (튜닝 대상)
a_w = 1
b_w = 1
c_w = 1
d_w = 1

TDP = 95
CARBON_INTENSITY = {
    "KR": 310,
    "FR": 18
}

class parameters:
    def __init__(self, work_nodes, penalty, workspan, carbon):
        self.work_nodes = work_nodes
        self.penalty = penalty
        self.workspan = workspan
        self.carbon = carbon

    def __repr__(self):
        return f"parameters(work_nodes={self.work_nodes}, penalty={self.penalty}, workspan={self.workspan}, carbon={self.carbon})"

# -------------------------
# 노드 클래스
# -------------------------
class Node:
    def __init__(self, name):
        self.name = name
        self.assigned_time = 0
        self.current_cpu = 0
        self.tasks = []  # (end_time, cpu)
        self.last_updated = time.time()

    def update_state(self):
        now = time.time()
        self.tasks = [(et, cpu) for et, cpu in self.tasks if et > now]
        self.current_cpu = sum(cpu for et, cpu in self.tasks)
        self.last_updated = now

    def can_assign(self, task_cpu):
        self.update_state()
        return (self.current_cpu + task_cpu) <= 100

    def assign_task(self, task_duration, task_cpu, params):
        self.update_state()
        end_time = time.time() + task_duration
        self.tasks.append((end_time, task_cpu))
        self.current_cpu += task_cpu
        self.assigned_time += task_duration

        # 노드별 아이콘 지정
        icon = "✅" if self.name == "K3S1" else "❌"
        print(f"{icon} {self.name}에 작업 배정됨 - {task_duration}s, {task_cpu}% CPU → 현재: {self.current_cpu}%")

        print(f"파라미터: {params}")


    def get_remaining_time(self):
        self.update_state()
        return self.assigned_time

# -------------------------
# 노드 목록 초기화
# -------------------------
nodes = {
    "K3S1": Node("K3S1"),
    "K3S2": Node("K3S2")
}

def get_max_remaining_time():
    max_node = max(nodes.values(), key=lambda n: n.get_remaining_time())
    return max_node.name, max_node.get_remaining_time()

# -------------------------
# 탄소 배출량 계산 함수
# -------------------------
def calculate_emission(cpu_percent: float, tdp: float, ci: float, seconds: int) -> float:
    hours = seconds / 3600.0
    return (cpu_percent / 100.0) * tdp * hours * ci

# -------------------------
# 메인 스케줄러 함수
# -------------------------
def process_task(task_name, estimated_time, task_cpu):
    result_score = []
    params = []
    logging.info(f"처리 시작 - 작업 이름: {task_name}, 예상 시간: {estimated_time}초")

    try:
        for idx, node_key in enumerate(kluster_nodes):
            node = nodes[node_key]

            # CPU 초과 시 배제
            if not node.can_assign(task_cpu):
                result_score.append(float('inf'))
                continue

            # 모의 리소스 사용률 (정적) 
            current_cpu = node.current_cpu
            ci = CARBON_INTENSITY[kluster_region[idx]]
            carbon = calculate_emission(task_cpu, TDP, ci, estimated_time)

            # 병렬 작업 수에 따른 패널티
            work_nodes = a_w * (1 if current_cpu  <= 26 else 0)
            penalty = b_w * math.exp(current_cpu / 100.0)


            node_remaining = node.get_remaining_time()
            global_max = get_max_remaining_time()[1]
            workspan = max(node_remaining + estimated_time, global_max)
            workspan = c_w * workspan

            score = work_nodes + penalty + workspan + (d_w * carbon)
            result_score.append(score)
            params.append(parameters(work_nodes, penalty, workspan, carbon))

        if all(s == float('inf') for s in result_score):
            logging.warning(f"⚠️ 작업 배치 실패 - 가능한 노드 없음: {task_name}")
            return None

        result_idx = min(range(len(result_score)), key=lambda i: result_score[i])
        selected_node_key = kluster_nodes[result_idx]
        selected_node = nodes[selected_node_key]
        selected_node.assign_task(estimated_time, task_cpu, params)

        logging.info(f"처리 완료 - 작업 이름: {task_name}")
        return kluster_name[result_idx]

    except Exception as e:
        logging.error(f"작업 처리 중 오류 발생 - 작업 이름: {task_name}, 에러: {e}")
        return None
