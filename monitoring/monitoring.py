import time
import os
from dotenv import load_dotenv
from new_collector import get_cpu_usage
from prometheus_client import start_http_server, Gauge
import mysql.connector
from carbon_fetch_model import fetch_latest_carbon_intensity

load_dotenv()

db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": "carbonetes"
}

PORT = 8801
INTERVAL_SEC = 10
TARGET_PORT = 9100  


cpu_usage_gauge = Gauge("carbon_cpu_usage_percent", "CPU usage in percent", ["cluster"])
co2_emission_gauge = Gauge("carbon_emission_g_co2eq", "Carbon emission per interval (gCO2eq)", ["cluster"])


def get_cluster_info():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT cluster_name, cluster_ip, tdp, region, token FROM cluster")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result  

def calculate_emission(cpu_percent: float, tdp: float, ci: float, seconds: int) -> float:
    hours = seconds / 3600.0
    return (cpu_percent / 100.0) * tdp * hours * ci


def collect_metrics(clusters):
    while True:
        for cluster_name, cluster_ip, tdp, region, token in clusters:
            endpoint = f"{cluster_ip}:{TARGET_PORT}"
            try:
                cpu = get_cpu_usage(endpoint)
                json_data = fetch_latest_carbon_intensity(region, token)
                co2 = calculate_emission(cpu, tdp, json_data['carbonIntensity'], INTERVAL_SEC)

                cpu_usage_gauge.labels(cluster=cluster_name).set(cpu)
                co2_emission_gauge.labels(cluster=cluster_name).set(co2)

                print(f"[{time.strftime('%H:%M:%S')}] "f"{cluster_name:<12}:{region:<8} → "f"CPU: {cpu:>6.2f}%  \tCO₂: {co2:>7.3f} g")

            except Exception as e:
                print(f"[ERROR] {cluster_name} ({endpoint}): {e}")
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    print(f"탄소 Exporter 시작: 포트 {PORT} 에서 Prometheus에 메트릭 노출 중")
    start_http_server(PORT)

    clusters = get_cluster_info()
    print(f"수집 대상 클러스터 목록: {[name for name, *_ in clusters]}")
    collect_metrics(clusters)
