import torch
import time

def gpu_stress(duration_sec=10):
    start = time.time()
    while time.time() - start < duration_sec:
        a = torch.rand(8192, 8192).cuda()  # 큰 텐서 생성
        b = torch.mm(a, a)  # 행렬 곱 연산 (GPU 집중 사용)
        del a, b  # 메모리 정리

if __name__ == "__main__":
    gpu_stress()
