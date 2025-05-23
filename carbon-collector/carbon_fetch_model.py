import requests
from datetime import datetime
from typing import Dict

AUTH_TOKEN = ""
ZONE = ""

def fetch_latest_carbon_intensity(zone: str = ZONE, token: str = AUTH_TOKEN) -> Dict:
    url = f"https://api.electricitymap.org/v3/carbon-intensity/latest?zone={zone}"
    headers = {"auth-token": token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def calculate_integrated_emission(carbon_intensity: float, minutes: int) -> float:
    hours = minutes / 60.0
    return carbon_intensity * hours

def get_carbon_info(duration_minutes: int) -> Dict:
    """
    탄소집약도 API를 호출하여 zone, datetime, carbonIntensity, 적분값을 반환

    :param duration_minutes: 예상 소요 시간 (분 단위)
    :return: {
        "zone": "KR",
        "datetime": "2025-05-20T14:00:00Z",
        "carbonIntensity": 438,
        "integratedEmission": 657.0
    }
    """
    data = fetch_latest_carbon_intensity()
    carbon_intensity = data["carbonIntensity"]
    integrated_emission = calculate_integrated_emission(carbon_intensity, duration_minutes)

    return {
        "zone": data["zone"],
        "datetime": data["datetime"],
        "carbonIntensity": carbon_intensity,
        "integratedEmission": round(integrated_emission, 2)
    }
