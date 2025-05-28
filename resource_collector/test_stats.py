# test_stats.py
import time
import os
from new_collector import get_cpu_usage, get_memory_usage, get_resource_usage
from dotenv import load_dotenv
load_dotenv()
ENDPOINT = os.getenv("K3S2_NODE_EXPORTERS")
def main():
    # 1) 첫 번째 호출: CPU 사용률은 0.0, 메모리는 즉시 반환
    ENDPOINT = os.getenv("K3S2_NODE_EXPORTERS")
    cpu1 = get_cpu_usage(ENDPOINT)
    mem1 = get_memory_usage(ENDPOINT)
    print(f"첫 호출  → CPU: {cpu1:.2f}%, MEM: {mem1:.2f}%")

    # 2) 잠시 대기 (CPU 델타를 측정하기 위해)
    time.sleep(5)

    # 3) 두 번째 호출: 실제 CPU 사용률이 계산되어 반환
    cpu2, mem2 = get_resource_usage(ENDPOINT)
    print(f"두 번째 → CPU: {cpu2:.2f}%, MEM: {mem2:.2f}%")

if __name__ == "__main__":
    main()