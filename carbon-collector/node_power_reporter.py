#CPU 사용률과 TDP를 받아서 소비 전력을 계산
from dotenv import load_dotenv
import os

# 필요한 라이브러리 임포트
import psutil  # CPU 사용률 측정용
import requests  # HTTP 요청 전송용
import platform  # CPU 모델 정보 확인용

load_dotenv()  # .env 파일 로드
ip_address = os.getenv("IP_ADDRESS")  # .env에 저장된 IP 불러오기
# CPU 모델별 TDP 매핑(수동으로 추가한거라.. 정확하진 않을수 있고 적음.)
TDP_MAP = {
    "Intel(R) Core(TM) i5": 65,
    "Intel(R) Core(TM) i7": 95,
    "AMD Ryzen 5": 65,
    "AMD Ryzen 7": 105
}

def get_cpu_tdp():
    """ 현재 사용 중인 CPU의 TDP 값을 가져오는 함수 """
    cpu_model = platform.processor()  # 시스템 CPU 모델명 확인
    for model, tdp in TDP_MAP.items():
        if model in cpu_model:  # 모델명이 일치하면 해당 TDP 반환
            return tdp
    return 65  # 매핑에 없을 경우 기본값 65W 사용

def estimate_power():
    """ CPU 사용률 기반으로 전력 소비량(W) 추정하는 함수 """
    cpu_usage = psutil.cpu_percent()  # CPU 사용률 (0~100%)
    tdp = get_cpu_tdp()  # 해당 CPU의 최대 전력 소비 (TDP)
    power = (cpu_usage / 100) * tdp  # 사용률 비례 계산
    return round(power, 2)  # 소수점 둘째자리로 반올림

def report_power():
    """ 계산된 소비 전력을 JSON 형식으로 중앙 서버로 전송하는 함수 """
    power_usage = estimate_power()  # 현재 소비 전력 계산
    data = {
        "cluster": "cluster-1",  # 클러스터 이름 지정 (예시)
        "power": power_usage  # 전력 값 포함
    }
    # 서버로 POST 요청 보내기
    response = requests.post("http://{ip_address}:8080/report_power", json=data)
    # 서버 응답 출력
    print("서버 응답:", response.json())

if __name__ == "__main__":
    report_power()  # 메인 실행 시 전송 함수 호출
