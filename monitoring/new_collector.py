# resource_stats.py

import re
import requests
from typing import Dict, Tuple

# ─────────────────────────────────────────────────────────────
# Prometheus 메트릭 정규식 (collector.py 기준) :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}
# ─────────────────────────────────────────────────────────────
CPU_LINE_RE = re.compile(
    r'^node_cpu_seconds_total\{cpu="(?P<cpu>\d+)",mode="(?P<mode>\w+)"\}\s+(?P<value>[0-9.eE+\-]+)',
    re.MULTILINE
)
MEM_TOTAL_RE = re.compile(r'^node_memory_MemTotal_bytes\s+(?P<total>\d+)', re.MULTILINE)
MEM_AVAILABLE_RE = re.compile(r'^node_memory_MemAvailable_bytes\s+(?P<avail>\d+)', re.MULTILINE)

# ─────────────────────────────────────────────────────────────
# /metrics 에서 CPU 누적 시간 읽어오기
# ─────────────────────────────────────────────────────────────
def fetch_cpu_times(endpoint: str) -> Dict[str, Dict[str, float]]:
    resp = requests.get(f"http://{endpoint}/metrics", timeout=3)
    resp.raise_for_status()
    text = resp.text

    cpu_times: Dict[str, Dict[str, float]] = {}
    for m in CPU_LINE_RE.finditer(text):
        cpu = m.group('cpu')
        mode = m.group('mode')
        value = float(m.group('value'))
        cpu_times.setdefault(cpu, {})[mode] = value

    return cpu_times

# ─────────────────────────────────────────────────────────────
# 이전/현재 스냅샷 비교로 CPU 사용률 계산
# ─────────────────────────────────────────────────────────────
def compute_cpu_usage(prev: Dict[str, Dict[str, float]], curr: Dict[str, Dict[str, float]]) -> float:
    total_prev = sum(sum(m.values()) for m in prev.values())
    total_curr = sum(sum(m.values()) for m in curr.values())
    idle_prev  = sum(m.get('idle', 0.0) for m in prev.values())
    idle_curr  = sum(m.get('idle', 0.0) for m in curr.values())

    delta_total = total_curr - total_prev
    delta_idle  = idle_curr  - idle_prev
    if delta_total <= 0:
        return 0.0
    return round((1 - delta_idle / delta_total) * 100, 2)

# ─────────────────────────────────────────────────────────────
# /metrics 에서 메모리 총량/가용량 읽어오기
# ─────────────────────────────────────────────────────────────
def fetch_memory_stats(endpoint: str) -> Tuple[float, float]:
    resp = requests.get(f"http://{endpoint}/metrics", timeout=3)
    resp.raise_for_status()
    text = resp.text

    total = float(MEM_TOTAL_RE.search(text).group('total')) if MEM_TOTAL_RE.search(text) else 0.0
    avail = float(MEM_AVAILABLE_RE.search(text).group('avail')) if MEM_AVAILABLE_RE.search(text) else 0.0
    return total, avail

# ─────────────────────────────────────────────────────────────
# 메모리 사용률 계산
# ─────────────────────────────────────────────────────────────
def compute_mem_usage(total: float, avail: float) -> float:
    if total <= 0:
        return 0.0
    used = total - avail
    return round((used / total) * 100, 2)

# ─────────────────────────────────────────────────────────────
# 내부 스냅샷 저장소 (각 노드별 prev_cpu)
# ─────────────────────────────────────────────────────────────
_last_cpu_snapshots: Dict[str, Dict[str, Dict[str, float]]] = {}

# ─────────────────────────────────────────────────────────────
def get_cpu_usage(endpoint: str) -> float:
    """
    endpoint 예: '211.43.14.15:9100'
    이전 스냅샷과 비교하여 CPU 사용률(%)을 반환.
    최초 호출 시에는 0.0을 반환하고, 다음 호출부터 값을 계산합니다.
    """
    curr = fetch_cpu_times(endpoint)
    prev = _last_cpu_snapshots.get(endpoint)
    usage = compute_cpu_usage(prev, curr) if prev else 0.0
    _last_cpu_snapshots[endpoint] = curr
    return usage

# ─────────────────────────────────────────────────────────────
def get_memory_usage(endpoint: str) -> float:
    """
    endpoint 예: '211.43.14.15:9100'
    즉시 메모리 사용률(%)을 반환합니다.
    """
    total, avail = fetch_memory_stats(endpoint)
    return compute_mem_usage(total, avail)

# ─────────────────────────────────────────────────────────────
def get_resource_usage(endpoint: str) -> Tuple[float, float]:
    """
    튜플 형태로 (cpu_usage, mem_usage) 를 반환합니다.
    """
    return get_cpu_usage(endpoint), get_memory_usage(endpoint)
