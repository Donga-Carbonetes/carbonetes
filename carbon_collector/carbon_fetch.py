import requests
from datetime import datetime

# 사용자 입력
AUTH_TOKEN = ""  # 안전하게는 환경변수로
ZONE = ""
DURATION_MINUTES = 90  # 소요 시간: 90분 예시

def fetch_latest_carbon_intensity(zone: str, token: str) -> dict:
    url = f"https://api.electricitymap.org/v3/carbon-intensity/latest?zone={zone}"
    headers = {"auth-token": token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def calculate_integrated_emission(carbon_intensity_g_per_kwh: float, minutes: int) -> float:
    hours = minutes / 60.0
    return carbon_intensity_g_per_kwh * hours  # gCO2eq (탄소 총량)

def main():
    data = fetch_latest_carbon_intensity(ZONE, AUTH_TOKEN)

    zone = data["zone"]
    carbon_intensity = data["carbonIntensity"]
    datetime_str = data["datetime"]

    integrated_emission = calculate_integrated_emission(carbon_intensity, DURATION_MINUTES)

    # 출력
    print("=== 탄소집약도 정보 ===")
    print(f"Zone: {zone}")
    print(f"Datetime (UTC): {datetime_str}")
    print(f"Carbon Intensity: {carbon_intensity} gCO2eq/kWh")
    print(f"예상 소요 시간: {DURATION_MINUTES}분")
    print(f"총 탄소 배출량 (적분값): {integrated_emission:.2f} gCO2eq")

if __name__ == "__main__":
    main()
