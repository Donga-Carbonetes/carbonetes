import time

def cpu_stress(duration_sec=10):
    start = time.time()
    while time.time() - start < duration_sec:
        [x**2 for x in range(10**6)]  # 큰 연산 반복

if __name__ == "__main__":
    cpu_stress()