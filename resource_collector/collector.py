#!/usr/bin/env python3
import logging
import sys
import os
import time
import re
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────
# 로깅 설정 (콘솔 + 파일)
# ─────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(ch)

fh = logging.FileHandler("collector.log")
fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(fh)

# ─────────────────────────────────────────────────────────────
# 환경 변수 로드
# ─────────────────────────────────────────────────────────────
load_dotenv()

NODE_EXPORTERS  = [addr.strip() for addr in os.getenv("NODE_EXPORTERS","").split(",") if addr.strip()]
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", 5))
CPU_TDP         = float(os.getenv("CPU_TDP", 95.0))

# ─────────────────────────────────────────────────────────────
# CPU 메트릭 정규식 (node_cpu_seconds_total)
# ─────────────────────────────────────────────────────────────
CPU_LINE_RE = re.compile(
    r'^node_cpu_seconds_total\{cpu="(?P<cpu>\d+)",mode="(?P<mode>\w+)"\}\s+(?P<value>[0-9.eE+\-]+)',
    re.MULTILINE
)

# ─────────────────────────────────────────────────────────────
# TDP 반환 함수
# ─────────────────────────────────────────────────────────────
def get_cpu_tdp() -> float:
    return CPU_TDP

# ─────────────────────────────────────────────────────────────
# /metrics 에서 CPU 누적 시간 파싱
# ─────────────────────────────────────────────────────────────
def fetch_cpu_times(endpoint: str) -> dict[str, dict[str, float]]:
    url = f"http://{endpoint}/metrics"
    resp = requests.get(url, timeout=3)
    resp.raise_for_status()
    text = resp.text

    cpu_times: dict[str, dict[str, float]] = {}
    for m in CPU_LINE_RE.finditer(text):
        cpu = m.group('cpu')
        mode = m.group('mode')
        value = float(m.group('value'))
        cpu_times.setdefault(cpu, {})[mode] = value

    if not cpu_times:
        logger.warning(f"[{endpoint}] CPU 메트릭 파싱 실패: 응답 앞부분:\n{text[:200]}")
    return cpu_times

# ─────────────────────────────────────────────────────────────
# 이전/현재 스냅샷 차이로 CPU 사용률 계산
# ─────────────────────────────────────────────────────────────
def compute_cpu_usage(prev, curr) -> float:
    total_prev = sum(sum(m.values()) for m in prev.values())
    total_curr = sum(sum(m.values()) for m in curr.values())
    idle_prev  = sum(m.get('idle', 0.0) for m in prev.values())
    idle_curr  = sum(m.get('idle', 0.0) for m in curr.values())

    td  = total_curr - total_prev
    idl = idle_curr  - idle_prev
    if td <= 0:
        return 0.0
    return round((1 - idl/td) * 100, 2)

# ─────────────────────────────────────────────────────────────
# CPU 사용률 → 전력 추정
# ─────────────────────────────────────────────────────────────
def estimate_power(cpu_usage: float) -> float:
    return round((cpu_usage / 100.0) * get_cpu_tdp(), 2)

# ─────────────────────────────────────────────────────────────
# 로컬 파일에 전력 기록
# ─────────────────────────────────────────────────────────────
def report_power(node: str, power: float):
    # ISO8601 UTC timestamp
    ts = datetime.now(timezone.utc).isoformat()
    line = f"{ts} node={node} power={power}W\n"
    with open("power_records.txt", "a") as f:
        f.write(line)
    logger.info(f"[{node}] 전력 {power}W 기록됨")

# ─────────────────────────────────────────────────────────────
# 메인 루프 (첫 스냅샷도 로그)
# ─────────────────────────────────────────────────────────────
def main():
    last_snapshots: dict[str, dict[str, dict[str, float]]] = {}

    if not NODE_EXPORTERS:
        logger.error("NODE_EXPORTERS 환경 변수가 설정되지 않았습니다.")
        return

    logger.info(f"Collector 시작: targets={NODE_EXPORTERS}, interval={SCRAPE_INTERVAL}s")
    while True:
        for ep in NODE_EXPORTERS:
            try:
                logger.debug(f"[{ep}] 메트릭 수집 시도")
                curr = fetch_cpu_times(ep)
                prev = last_snapshots.get(ep)
                if prev:
                    usage = compute_cpu_usage(prev, curr)
                    power = estimate_power(usage)
                    report_power(ep, power)
                else:
                    logger.info(f"[{ep}] 첫 스냅샷 저장: {curr}")
                last_snapshots[ep] = curr
            except Exception as ex:
                logger.error(f"[{ep}] 처리 중 오류 발생: {ex}")
        time.sleep(SCRAPE_INTERVAL)

if __name__ == "__main__":
    main()
