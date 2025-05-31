import os
import requests
from typing import Dict
from dotenv import load_dotenv

# .env 파일 로딩
load_dotenv()

def get_zone_and_token(country_code: str) -> tuple[str, str]:
    """
    .env에서 국가코드에 따라 zone과 api token을 불러온다.
    :param country_code: KR, DE, FR 등
    :return: (zone, token)
    """
    zone = os.getenv(f"{country_code}_ZONE")
    token = os.getenv(f"{country_code}_API_TOKEN")

    if not zone or not token:
        raise ValueError(f"{country_code}에 대한 ZONE 또는 API_TOKEN 환경변수가 설정되지 않았습니다.")
    
    return zone, token

def fetch_latest_carbon_intensity(zone: str, token: str) -> Dict:
    url = f"https://api.electricitymap.org/v3/carbon-intensity/latest?zone={zone}"
    headers = {"auth-token": token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def calculate_integrated_emission(carbon_intensity: float, minutes: int) -> float:
    hours = minutes / 60.0
    return carbon_intensity * hours  # 단위: gCO2eq

def get_carbon_info(duration_minutes: int, country_code: str = "KR") -> Dict:
    """
    기본값은 KR로 유지, 기본값이 필요 없으면 country_code: str로 사용가능
    특정 국가의 zone에 대해 탄소집약도 데이터를 가져오고 적분 값을 계산하여 반환.
    :param duration_minutes: 작업 소요 시간 (분)
    :param country_code: KR, DE, FR 등의 국가 코드
    :return: {
        "zone": "KR",
        "datetime": "2025-05-20T14:00:00Z",
        "carbonIntensity": 438,
        "integratedEmission": 657.0
    }
    """
    zone, token = get_zone_and_token(country_code)
    data = fetch_latest_carbon_intensity(zone, token)
    carbon_intensity = data["carbonIntensity"]
    integrated_emission = calculate_integrated_emission(carbon_intensity, duration_minutes)

    return {
        "zone": data["zone"],
        "datetime": data["datetime"],
        "carbonIntensity": carbon_intensity,
        "integratedEmission": round(integrated_emission, 2)
    }
