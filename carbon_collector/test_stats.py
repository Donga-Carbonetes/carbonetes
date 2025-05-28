from carbon_fetch_model import get_carbon_info

result = get_carbon_info(90)  # 90분짜리 작업

print(result)
# 출력 예시:
# {
#     'zone': 'KR',
#     'datetime': '2025-05-20T14:00:00Z',
#     'carbonIntensity': 438,
#     'integratedEmission': 657.0
# }