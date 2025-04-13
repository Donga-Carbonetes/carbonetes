# 탄소 수집기 서버
#클라이언트가 보낸 전력 소비량 데이터를 받아서, 탄소 배출량을 계산해 응답

from flask import Flask, request, jsonify # Flask 서버 구축
import csv # 전력 사용량 CSV로 저장
from prometheus_flask_exporter import PrometheusMetrics # Flask에 Prometheus Exporter
from prometheus_client import Gauge # Prometheus 지표(Gauge 타입)
from datetime import datetime # 날짜/시간 기록용

app = Flask(__name__) #Flask 앱 시작


# Prometheus exporter 초기화F8080
metrics = PrometheusMetrics(app)
# Custom Prometheus 메트릭
power_usage_metric = Gauge('power_usage_w', 'Current Power Usage in Watts', ['cluster']) #전력 사용량 (W)
carbon_emission_metric = Gauge('carbon_emission_g', 'Current Carbon Emission in grams', ['cluster']) #탄소 배출량 (g)
CSV_FILE = 'power_log.csv'

# 최초 실행 시 헤더 쓰기
with open(CSV_FILE, mode='a', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['timestamp', 'cluster', 'power_usage_W', 'carbon_emission_g'])

@app.route('/report_power', methods=['POST'])
def report_power():
    data = request.get_json()
    
    if data is None:
        return jsonify({"error": "Invalid JSON data"}), 400
    
    cluster_name = data.get("cluster", "unknown")
    power_usage = data.get("power", 0)

    # 탄소 집약도 (한국!)
    carbon_intensity = 0.424  # kgCO2/kWh

    # 탄소 배출량 계산 (전력 소비량을 kWh 단위로 변환)
    carbon_emission = power_usage * (1 / 1000) * carbon_intensity
    # CSV 저장
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), cluster_name, power_usage, round(carbon_emission * 1000, 2)])
    
    # Prometheus 메트릭 업데이트
    power_usage_metric.labels(cluster=cluster_name).set(power_usage)
    carbon_emission_metric.labels(cluster=cluster_name).set(round(carbon_emission * 1000, 2))

    return jsonify({
        "cluster": cluster_name,
        "power_usage_W": power_usage,
        #탄소 배출량은 기본 단위가 kgCO₂ -> gCO₂(그램)으로 바꾸기 위해 * 1000을 하고, 소수점 둘째자리까지 반올림
        "carbon_emission_g": round(carbon_emission * 1000, 2)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=18080)
