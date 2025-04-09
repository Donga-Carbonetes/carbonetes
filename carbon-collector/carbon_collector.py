# 탄소 수집기 서버
#클라이언트가 보낸 전력 소비량 데이터를 받아서, 탄소 배출량을 계산해 응답
from flask import Flask, request, jsonify
from datetime import datetime
import csv

app = Flask(__name__)

# CSV 파일이 저장되는 경로 
CSV_FILE = 'power_log.csv'
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

    return jsonify({
        "cluster": cluster_name,
        "power_usage_W": power_usage,
        #탄소 배출량은 기본 단위가 kgCO₂ -> gCO₂(그램)으로 바꾸기 위해 * 1000을 하고, 소수점 둘째자리까지 반올림
        "carbon_emission_g": round(carbon_emission * 1000, 2)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
