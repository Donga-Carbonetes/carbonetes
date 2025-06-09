import logging
import time
import os
import sys
import math
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv
import random

from carbon_collector.carbon_fetch_model import get_carbon_info
from resource_collector.new_collector import get_resource_usage

load_dotenv()

kluster_nodes = ["K3S1", "K3S2", "NEWK3S1"]
kluster_region = ["KR", "JP", "FR"]
kluster_name = ["k3s-1", "k3s-2", "new-k3s-1"]

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
        self.expected_finish_at = None

    def get_remaining_time(self):
        if self.expected_finish_at is None:
            return 0
        remaining = (self.expected_finish_at - datetime.now()).total_seconds()
        return max(0, remaining)

    def assign_task(self, task_duration):
        now = datetime.now()
        remaining = self.get_remaining_time()
        self.expected_finish_at = now + timedelta(seconds=remaining + task_duration)
        print(f"✅ {self.name} - 종료 예정: {self.expected_finish_at}")

nodes = {name: Node(name) for name in kluster_nodes}

a_w, b_w, c_w, d_w = 1, 1, 1, 1

def process_task(task_name, estimated_time):
    logging.info(f"처리 시작 - 작업 이름: {task_name}, 예상 시간: {estimated_time}초")

    try:
        while True:
            result_score = []
            nodes_rsc_list = []
            nodes_crb_list = []
            remaining_times = []

            for node, region in zip(kluster_nodes, kluster_region):
                endpoint = os.getenv(f"{node}_NODE_EXPORTERS")
                cpu, ram = get_resource_usage(endpoint)
                retry = 0
                while (cpu < 0 or ram < 0) and retry < 3:
                    cpu, ram = get_resource_usage(endpoint)
                    retry += 1
                nodes_rsc_list.append(cpu)
                carbon_info = get_carbon_info(estimated_time, country_code=region)
                nodes_crb_list.append(carbon_info.get("integratedEmission", 0))
                remaining_times.append(nodes[node].get_remaining_time())

            for idx, node in enumerate(kluster_nodes):
                usage = nodes_rsc_list[idx]

                if usage > 60:
                    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
                        writer = csv.writer(file)
                        writer.writerow([
                            time.strftime("%Y-%m-%d %H:%M:%S"), task_name, node,
                            round(usage, 2), "-", "-", "-", "-", "미배치 (리소스 초과)"
                        ])
                    result_score.append(999999)
                    continue

                temp_usage = nodes_rsc_list[:]
                temp_usage[idx] = 50
                count = sum(1 for u in temp_usage if u >= 8.5)
                work_nodes = a_w * count

                normalized = usage / 100
                penalty = b_w * (10 ** (4 * normalized))
                remaining = remaining_times[idx]
                workspan = c_w * (remaining + estimated_time)
                carbon = d_w * nodes_crb_list[idx]

                score = work_nodes + penalty + workspan + carbon
                result_score.append(score)

                with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        time.strftime("%Y-%m-%d %H:%M:%S"), task_name, node,
                        round(usage, 2), work_nodes, round(penalty, 2),
                        round(workspan, 2), round(carbon, 6), round(score, 2)
                    ])

            logging.info(f"스코어 목록: {result_score}")
            result_idx = min(range(len(result_score)), key=lambda i: result_score[i])
            best_node = kluster_nodes[result_idx]

            valid_score = {kluster_nodes[i]: s for i, s in enumerate(result_score) if s != 999999}

            if valid_score:
                if best_node in valid_score:
                    nodes[best_node].assign_task(estimated_time)
                    return kluster_name[result_idx]
                else:
                    fallback_node = min(valid_score, key=valid_score.get)
                    nodes[fallback_node].assign_task(estimated_time)
                    logging.warning(f"⚠ 대체 노드 사용: {fallback_node}")
                    return kluster_name[kluster_nodes.index(fallback_node)]
            else:
                logging.warning("⚠ 모든 노드가 미배치 상태입니다. 5초 후 재시도")
                time.sleep(5)

    except Exception as e:
        logging.error(f"❌ 작업 처리 중 오류: {e}")