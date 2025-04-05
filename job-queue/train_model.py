# train_model.py

import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--epochs", type=int, default=5)
args = parser.parse_args()

for i in range(args.epochs):
    print(f"[Epoch {i+1}] 학습 중...")
    time.sleep(1)

print("학습 완료!")
