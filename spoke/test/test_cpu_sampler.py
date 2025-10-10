import time
import os
import sys
import json
import datetime
import threading
import statistics
import yaml
import requests
from kubernetes import client as k8s_client, config as k8s_config

# 실시간 로그 출력 (라인 버퍼링)
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

class CPUSampler:
    """
    Kubelet Summary API (/stats/summary)에서 우리 파드의 CPU를 주기적으로 수집.
    usageNanoCores가 있으면 즉시값, 없으면 usageCoreNanoSeconds 차분/시간으로 레이트 계산.
    """
    def __init__(self, node_name, namespace, pod_name, interval=2.0):
        self.node_name = node_name
        self.namespace = namespace
        self.pod_name = pod_name
        self.interval = interval
        self.samples_m = []
        self._stop = threading.Event()
        self._last_ns = {}
        self._last_ts = {}

        k8s_config.load_incluster_config()
        self.core = k8s_client.CoreV1Api()

        # in-cluster API 서버 정보/토큰/CA
        self.apiserver_host = os.environ.get("KUBERNETES_SERVICE_HOST")
        self.apiserver_port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
        self.token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        self.ca_path = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
        with open(self.token_path, "r") as f:
            self.bearer = f.read().strip()

    def _to_m(self, nano_cores: int) -> int:
        # 나노코어 → millicore
        return int(round(nano_cores / 1_000_000.0))

    def _rate_to_nano_cores(self, delta_usage_ns: int, delta_seconds: float) -> int:
        if delta_seconds <= 0:
            return 0
        # 누적(ns*core) → 초당 나노코어
        return int(delta_usage_ns / delta_seconds)

    def _fetch_summary(self) -> dict:
        """
        1) API 서버를 통해 직접 HTTPS 호출 (가장 깨끗한 JSON 확보).
        2) 혹시 문자열에 접두문구/개행 등이 섞여 있으면 정리 후 JSON/YAML 파싱.
        """
        url = f"https://{self.apiserver_host}:{self.apiserver_port}/api/v1/nodes/{self.node_name}/proxy/stats/summary"
        headers = {"Authorization": f"Bearer {self.bearer}"}

        try:
            r = requests.get(url, headers=headers, verify=self.ca_path, timeout=5)
            ct = r.headers.get("Content-Type", "")
            raw = r.text
            # 🔍 raw 앞/뒤 일부 출력
            head = raw[:300].replace("\n", "\\n")
            tail = raw[-300:].replace("\n", "\\n")
            print(f"[DEBUG] GET {url} status={r.status_code} content-type={ct}")
            print(f"[DEBUG] raw head: {head}")
            print(f"[DEBUG] raw tail: {tail}")

            # 2xx가 아니면 예외
            r.raise_for_status()

            # Content-Type이 json이면 바로 시도
            if "json" in ct.lower():
                try:
                    return r.json()
                except Exception as je:
                    print(f"[WARN] r.json() 실패: {je}")

            # 문자열 정리: 첫 '{'부터 마지막 '}'까지 자르기
            cleaned = raw.strip()
            if not cleaned.startswith("{"):
                idx = cleaned.find("{")
                if idx != -1:
                    cleaned = cleaned[idx:]
            if not cleaned.endswith("}"):
                idx = cleaned.rfind("}")
                if idx != -1:
                    cleaned = cleaned[:idx + 1]

            # JSON → YAML 순으로 파싱
            try:
                return json.loads(cleaned)
            except Exception as e_json:
                print(f"[WARN] json.loads 실패: {e_json}")
                try:
                    return yaml.safe_load(cleaned)
                except Exception as e_yaml:
                    print(f"[ERROR] yaml.safe_load 실패: {e_yaml}")
                    print(f"[DEBUG] cleaned preview: {cleaned[:1000]}")
                    return {}
        except Exception as e:
            print(f"[ERROR] summary 호출 실패: {e}")
            return {}

    def _find_our_pod(self, summary: dict):
        for pod in summary.get("pods", []):
            ref = pod.get("podRef", {})
            if ref.get("namespace") == self.namespace and ref.get("name") == self.pod_name:
                return pod
        return None

    def sample_once(self):
        try:
            summary = self._fetch_summary()
            pod = self._find_our_pod(summary)
            if not pod:
                print("[WARN] 우리 파드가 summary에 없음")
                return

            total_nano_cores = 0
            for c in pod.get("containers", []):
                cpu = c.get("cpu", {})
                cname = c.get("name", "unknown")
                if "usageNanoCores" in cpu and cpu["usageNanoCores"] is not None:
                    total_nano_cores += int(cpu["usageNanoCores"])
                elif "usageCoreNanoSeconds" in cpu and cpu["usageCoreNanoSeconds"] is not None:
                    # RFC3339: "2025-10-10T07:53:53Z" 혹은 소수점 포함
                    tstr = cpu.get("time", "").rstrip("Z")
                    # 소수점이 있어도 fromisoformat이 처리
                    now_ts = datetime.datetime.fromisoformat(tstr)
                    curr_ns = int(cpu["usageCoreNanoSeconds"])
                    prev_ns = self._last_ns.get(cname)
                    prev_ts = self._last_ts.get(cname)
                    if prev_ns is not None and prev_ts is not None:
                        delta_ns = max(0, curr_ns - prev_ns)
                        delta_t = (now_ts - prev_ts).total_seconds()
                        total_nano_cores += self._rate_to_nano_cores(delta_ns, delta_t)
                    self._last_ns[cname] = curr_ns
                    self._last_ts[cname] = now_ts

            m_val = self._to_m(total_nano_cores)
            self.samples_m.append(m_val)
            print(f"[INFO] 샘플링: {m_val} m (샘플 수={len(self.samples_m)})")
        except Exception as e:
            print(f"[ERROR] 샘플링 실패: {e}")

    def _loop(self):
        while not self._stop.is_set():
            self.sample_once()
            time.sleep(self.interval)

    def start(self):
        print("[INFO] CPU 샘플러 시작")
        self._th = threading.Thread(target=self._loop, daemon=True)
        self._th.start()

    def stop(self):
        print("[INFO] CPU 샘플러 정지")
        self._stop.set()
        if hasattr(self, "_th"):
            self._th.join(timeout=5)

    def median_m(self):
        return int(statistics.median(self.samples_m)) if self.samples_m else None


if __name__ == "__main__":
    node_name = os.getenv("NODE_NAME")
    namespace = os.getenv("POD_NAMESPACE", "default")
    pod_name = os.getenv("POD_NAME")

    print(f"[DEBUG] node={node_name}, ns={namespace}, pod={pod_name}")
    sampler = CPUSampler(node_name, namespace, pod_name)

    sampler.start()
    for _ in range(30):  # 60초 동안 2초 간격
        time.sleep(2)
    sampler.stop()

    print(f"[RESULT] 샘플링 개수: {len(sampler.samples_m)}")
    print(f"[RESULT] 중앙값(m): {sampler.median_m()}")
    print(f"[RESULT] 전체 샘플: {sampler.samples_m}")
