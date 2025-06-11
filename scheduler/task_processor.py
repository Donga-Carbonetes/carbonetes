import logging
import time
import os
import sys
import math
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv
import random
import mysql.connector
from carbon_collector.carbon_fetch_model import get_carbon_info
from resource_collector.new_collector import get_resource_usage

db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": "carbonetes"
}

load_dotenv()

# kluster_nodes = ["K3S1", "K3S2", "NEWK3S1"]
# kluster_region = ["KR", "JP", "FR"]
# kluster_name = ["k3s-1", "k3s-2", "new-k3s-1"]
# endpoint = []

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
    def __init__(self, cluster_name, cluster_ip, region):
        self.cluster_name = cluster_name
        self.cluster_ip = cluster_ip
        self.region = region
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
        print(f"✅ {self.cluster_name} - 종료 예정: {self.expected_finish_at}")

def get_cluster_info_from_db():
    conn = None
    cursor = None
    clusters_data = []
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True) # 결과를 딕셔너리 형태로 반환
        query = "SELECT cluster_name, cluster_ip, region FROM cluster"
        cursor.execute(query)
        clusters_data = cursor.fetchall()
    except mysql.connector.Error as err:
        logging.error(f"데이터베이스에서 클러스터 정보를 가져오는 중 오류 발생: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return clusters_data

clusters_from_db = get_cluster_info_from_db()
nodes = {c['cluster_name']: Node(c['cluster_name'], c['cluster_ip'], c['region']) for c in clusters_from_db}

a_w, b_w, c_w, d_w = 1, 1, 1, 1

def process_task(task_name, estimated_time):
    logging.info(f"처리 시작 - 작업 이름: {task_name}, 예상 시간: {estimated_time}초")

    if not nodes:
        logging.error("초기화된 클러스터 노드가 없습니다. 데이터베이스에서 클러스터 정보를 가져오지 못했거나 클러스터가 정의되지 않았습니다.")
        return None

    try:
        while True:
            result_score = []
            processed_nodes_data = []

            for node_name, node_obj in nodes.items():
                endpoint = node_obj.cluster_ip
                cpu, ram = get_resource_usage(f'{endpoint}:9100')
                retry = 0
                while (cpu < 0 or ram < 0) and retry < 3:
                    cpu, ram = get_resource_usage(f'{endpoint}:9100')
                    retry += 1
                usage = cpu
                carbon_info = get_carbon_info(estimated_time, country_code=node_obj.region)
                carbon_emission = carbon_info.get("integratedEmission", 0)
                remaining = node_obj.get_remaining_time()

                processed_nodes_data.append({
                    "node_obj": node_obj,
                    "usage": usage,
                    "carbon": carbon_emission,
                    "remaining_time": remaining
                })

            for idx, data in enumerate(processed_nodes_data):
                node_obj = data["node_obj"]
                usage = data["usage"]
                carbon = data["carbon"]
                remaining = data["remaining_time"]

                if usage > 60:
                    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
                        writer = csv.writer(file)
                        writer.writerow([
                            time.strftime("%Y-%m-%d %H:%M:%S"), task_name, node_obj.cluster_name,
                            round(usage, 2), "-", "-", "-", "-", "미배치 (리소스 초과)"
                        ])
                    result_score.append(999999)
                    continue

                temp_usage = [d["usage"] for d in processed_nodes_data]
                temp_usage[idx] = 50
                count = sum(1 for u in temp_usage if u >= 8.5)
                work_nodes = a_w * count

                normalized = usage / 100
                penalty = b_w * (10 ** (4 * normalized))
                workspan = c_w * (remaining + estimated_time)
                carbon_score_term = d_w * carbon

                score = work_nodes + penalty + workspan + carbon_score_term
                result_score.append(score)

                with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        time.strftime("%Y-%m-%d %H:%M:%S"), task_name, node_obj.cluster_name,
                        round(usage, 2), work_nodes, round(penalty, 2),
                        round(workspan, 2), round(carbon, 6), round(score, 2)
                    ])

            logging.info(f"스코어 목록: {result_score}")
            result_idx = min(range(len(result_score)), key=lambda i: result_score[i])

            best_node_obj = processed_nodes_data[result_idx]["node_obj"]
            best_node_name = best_node_obj.cluster_name

            valid_score = {processed_nodes_data[i]["node_obj"].cluster_name: s for i, s in enumerate(result_score) if s != 999999}

            if valid_score:
                if best_node_name in valid_score:
                    nodes[best_node_name].assign_task(estimated_time)
                    return best_node_name
                else:
                    fallback_node_name = min(valid_score, key=valid_score.get)
                    nodes[fallback_node_name].assign_task(estimated_time)
                    logging.warning(f"⚠ 대체 노드 사용: {fallback_node_name}")
                    return fallback_node_name
            else:
                logging.warning("⚠ 모든 노드가 미배치 상태입니다. 5초 후 재시도")
                time.sleep(5)

    except Exception as e:
        logging.error(f"❌ 작업 처리 중 오류: {e}")