import itertools
import subprocess
import json

step = 0.1
values = [round(i * step, 1) for i in range(int(1/step) + 1)]  # 0.0 ~ 1.0

# 가중치 합이 1.0인 조합만 추출
combinations = [
    (a, b, c, d)
    for a, b, c, d in itertools.product(values, repeat=4)
    if round(a + b + c + d, 1) == 1.0
]

best_score = float('inf')
best_weights = None

for a, b, c, d in combinations:
    with open("weights.json", "w") as f:
        json.dump({"a_w": a, "b_w": b, "c_w": c, "d_w": d}, f)

    result = subprocess.run(
        ["python", "evaluate_weights.py"], capture_output=True, text=True)

    try:
        score = float(result.stdout.strip())
        if score < best_score:
            best_score = score
            best_weights = (a, b, c, d)
    except:
        continue

print(f"✅ 최적 가중치: {best_weights}, 최소 점수: {best_score}")
