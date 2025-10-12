import os
import time
import json
import datetime
import threading
import statistics
import subprocess
import mysql.connector
from minio import Minio
from minio.error import S3Error
import requests
from kubernetes import client as k8s_client, config as k8s_config


# ==============================
# 환경 변수 설정
# ==============================
POD_NAME = os.getenv("POD_NAME")
POD_NAMESPACE = os.getenv("POD_NAMESPACE", "default")
NODE_NAME = os.getenv("NODE_NAME")
SAMPLE_SEC = float(os.getenv("METRIC_SAMPLE_SEC", "2"))
TASK_NAME = os.getenv("TASK_NAME")

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE")
}

MINIO_HOST = os.getenv("MINIO_HOST")
MINIO_PORT = os.getenv("MINIO_PORT")

minio_client = Minio(
    f"{MINIO_HOST}:{MINIO_PORT}",
    access_key="rootuser",
    secret_key="rootpass123",
    secure=False
)

BUCKET = "mybucket"
OBJECT_NAME = f"{TASK_NAME}.py"
DOWNLOAD_DIR = "./tmp/myapp"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ==============================
# CPU 샘플러 클래스
# ==============================
class CPUSampler:
    """
    Kubelet Summary API (/stats/summary)에서 현재 파드의 CPU를 주기적으로 수집.
    usageNanoCores가 있으면 즉시값 사용, 없으면 usageCoreNanoSeconds의 차분 기반 계산.
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

        # Kubernetes API client 설정
        k8s_config.load_incluster_config()
        self.core = k8s_client.CoreV1Api()

        # in-cluster API 서버 정보
        self.apiserver_host = os.environ.get("KUBERNETES_SERVICE_HOST")
        self.apiserver_port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
        self.token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        self.ca_path = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
        with open(self.token_path, "r") as f:
            self.bearer = f.read().strip()

    def _to_m(self, nano_cores: int) -> int:
        return int(round(nano_cores / 1_000_000.0))

    def _rate_to_nano_cores(self, delta_usage_ns: int, delta_seconds: float) -> int:
        if delta_seconds <= 0:
            return 0
        return int(delta_usage_ns / delta_seconds)

    def _fetch_summary(self) -> dict:
        url = f"https://{self.apiserver_host}:{self.apiserver_port}/api/v1/nodes/{self.node_name}/proxy/stats/summary"
        headers = {"Authorization": f"Bearer {self.bearer}"}
        try:
            r = requests.get(url, headers=headers, verify=self.ca_path, timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception:
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
                return

            total_nano_cores = 0
            for c in pod.get("containers", []):
                cpu = c.get("cpu", {})
                cname = c.get("name", "unknown")
                if "usageNanoCores" in cpu and cpu["usageNanoCores"] is not None:
                    total_nano_cores += int(cpu["usageNanoCores"])
                elif "usageCoreNanoSeconds" in cpu and cpu["usageCoreNanoSeconds"] is not None:
                    tstr = cpu.get("time", "").rstrip("Z")
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

            self.samples_m.append(self._to_m(total_nano_cores))
        except Exception:
            pass

    def _loop(self):
        while not self._stop.is_set():
            self.sample_once()
            time.sleep(self.interval)

    def start(self):
        self._th = threading.Thread(target=self._loop, daemon=True)
        self._th.start()

    def stop(self):
        self._stop.set()
        if hasattr(self, "_th"):
            self._th.join(timeout=5)

    def median_m(self):
        return int(statistics.median(self.samples_m)) if self.samples_m else None


# ==============================
# 데이터베이스 관련 함수
# ==============================
def save_cpu_median(task_name, median_m):
    if median_m is None:
        return
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        UPDATE task_info  
           SET cpu_m = %s
         WHERE task_name = %s
    """, (int(median_m), task_name))
    conn.commit()
    cur.close()
    conn.close()


def update_task_status_and_completed_at(task_name, status):
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        UPDATE task_info SET status = %s, completed_at = NOW() WHERE task_name = %s
    """, (status, task_name))
    conn.commit()
    cur.close()
    conn.close()


# ==============================
# 작업 다운로드 및 실행
# ==============================
def download_task():
    download_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, OBJECT_NAME))
    try:
        minio_client.fget_object(BUCKET, OBJECT_NAME, download_path)
        return download_path
    except S3Error as e:
        print(f"❌ MinIO 다운로드 실패: {e}")
        exit(1)


def run_task(download_path):
    try:
        process = subprocess.Popen(
            ["python", download_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for _ in process.stdout:
            pass
        process.wait()
        return process.returncode
    except Exception:
        return 1


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    sampler = CPUSampler(NODE_NAME, POD_NAMESPACE, POD_NAME, interval=SAMPLE_SEC)
    sampler.start()

    path = download_task()
    ret = run_task(path)

    sampler.stop()
    median_m = sampler.median_m()
    save_cpu_median(TASK_NAME, median_m)

    if ret == 0:
        update_task_status_and_completed_at(TASK_NAME, "terminated")
