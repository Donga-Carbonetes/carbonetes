
import time

def memory_bomb(duration_sec=10):
    big_list = []
    start = time.time()
    while time.time() - start < duration_sec:
        big_list.append([0] * 10**6)  # 리스트에 큰 데이터 추가

if __name__ == "__main__":
    memory_bomb()