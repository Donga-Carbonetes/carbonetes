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

NODE_EXPORTERS  = [addr.strip() for addr in os.getenv("NODE_EXPORTERS", "").split(",") if addr.strip()]
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", 5))
CPU_TDP         = float(os.getenv("CPU_TDP", 95.0))  # 여전히 TDP가 필요한 경우

# ─────────────────────────────────────────────────────────────
# 메트릭 정규식
# ─────────────────────────────────────────────────────────────
CPU_LINE_RE = re.compile(
    r'^node_cpu_seconds_total\{cpu="(?P<cpu>\d+)",mode="(?P<mode>\w+)"\}\s+(?P<value>[0-9.eE+\-]+)',
    re.MULTILINE
)
MEM_TOTAL_RE = re.compile(
    r'^node_memory_MemTotal_bytes\s+(?P<total>\d+)',
    re.MULTILINE
)
MEM_AVAILABLE_RE = re.compile(
    r'^node_memory_MemAvailable_bytes\s+(?P<avail>\d+)',
    re.MULTILINE
)

# ─────────────────────────────────────────────────────────────
# TDP 반환 (더 이상 필요 없으면 삭제)
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
        logger.warning(f"[{endpoint}] CPU 메트릭 파싱 실패")
    return cpu_times

# ─────────────────────────────────────────────────────────────
# /metrics 에서 메모리 총량/가용량 파싱
# ─────────────────────────────────────────────────────────────
def fetch_memory_stats(endpoint: str) -> tuple[float, float]:
    url = f"http://{endpoint}/metrics"
    resp = requests.get(url, timeout=3)
    resp.raise_for_status()
    text = resp.text

    total = None
    avail = None
    t_match = MEM_TOTAL_RE.search(text)
    a_match = MEM_AVAILABLE_RE.search(text)
    if t_match:
        total = float(t_match.group('total'))
    if a_match:
        avail = float(a_match.group('avail'))

    if total is None or avail is None:
        logger.warning(f"[{endpoint}] 메모리 메트릭 파싱 실패")
        return 0.0, 0.0
    return total, avail

# ─────────────────────────────────────────────────────────────
# 이전/현재 스냅샷 차이로 CPU 사용률 계산
# ─────────────────────────────────────────────────────────────
def compute_cpu_usage(prev, curr) -> float:
    total_prev = sum(sum(m.values()) for m in prev.values())
    total_curr = sum(sum(m.values()) for m in curr.values())
    idle_prev  = sum(m.get('idle', 0.0) for m in prev.values())
    idle_curr  = sum(m.get('idle', 0.0) for m in curr.values())

    td  = total_curr - total_prev
    idl = idle_curr - idle_prev
    if td <= 0:
        return 0.0
    return round((1 - idl/td) * 100, 2)

# ─────────────────────────────────────────────────────────────
# 메모리 사용률 계산
# ─────────────────────────────────────────────────────────────
def compute_mem_usage(total: float, avail: float) -> float:
    if total <= 0:
        return 0.0
    used = total - avail
    return round((used / total) * 100, 2)

# ─────────────────────────────────────────────────────────────
# 로컬 파일에 CPU/메모리 사용량 기록
# ─────────────────────────────────────────────────────────────
def report_metrics(node: str, cpu_usage: float, mem_usage: float):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"{ts} node={node} cpu={cpu_usage}% mem={mem_usage}%\n"
    with open("metrics_records.txt", "a") as f:
        f.write(line)
    logger.info(f"[{node}] CPU {cpu_usage}%, MEM {mem_usage}% 기록됨")

# ─────────────────────────────────────────────────────────────
# 정주영 작성: collect_once() 함수
# ─────────────────────────────────────────────────────────────
def collect_once() -> list[dict]:
    """모든 NODE_EXPORTERS에서 현재 CPU/Memory 사용률을 수집하여 리스트로 반환"""
    results = []
    for ep in NODE_EXPORTERS:
        try:
            curr_cpu = fetch_cpu_times(ep)
            prev_cpu = collect_once._snapshots.get(ep)
            total, avail = fetch_memory_stats(ep)
            mem_usage = compute_mem_usage(total, avail)

            if prev_cpu:
                cpu_usage = compute_cpu_usage(prev_cpu, curr_cpu)
            else:
                cpu_usage = 0.0  # 첫 호출이면 비교 불가

            result = {
                "node": ep,
                "cpu_usage": cpu_usage,
                "mem_usage": mem_usage
            }
            results.append(result)

            collect_once._snapshots[ep] = curr_cpu
        except Exception as ex:
            logger.error(f"[{ep}] 처리 중 오류 발생: {ex}")
            results.append({
                "node": ep,
                "cpu_usage": None,
                "mem_usage": None,
                "error": str(ex)
            })
    logger.info(f"[collect_once] 수집 결과: {results}")
    return results

# 내부 상태 저장용 변수 초기화
collect_once._snapshots = {}