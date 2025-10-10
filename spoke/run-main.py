import mysql.connector
from minio import Minio
from minio.error import S3Error
import subprocess
import os, time, threading, statistics, datetime, json
from kubernetes import client as k8s_client, config as k8s_config

db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE")
}

POD_NAME = os.getenv("POD_NAME")
POD_NAMESPACE = os.getenv("POD_NAMESPACE", "default")
NODE_NAME = os.getenv("NODE_NAME")
SAMPLE_SEC = float(os.getenv("METRIC_SAMPLE_SEC", "2"))

minio_host = os.getenv("MINIO_HOST")
minio_port = os.getenv("MINIO_PORT")

client = Minio(
    f"{minio_host}:{minio_port}",
    access_key="rootuser",
    secret_key="rootpass123",
    secure=False
)

task_name = os.getenv("TASK_NAME")
bucket_name = "mybucket"
object_name = f"{task_name}.py"
download_dir = "./tmp/myapp"
os.makedirs(download_dir, exist_ok=True)


def save_cpu_median(task_name, median_m):
    """CPU 중앙값(millicores)만 task_name 기준으로 UPDATE"""
    if median_m is None:
        return
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    cur.execute("""
        UPDATE task_resource_usage
           SET cpu_m = %s
         WHERE task_name = %s
    """, (int(median_m), task_name))
    conn.commit()
    cur.close()
    conn.close()

def update_task_status_and_completed_at(task_name, status):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    query = """
        UPDATE task_info SET status = %s, completed_at = NOW() WHERE task_name = %s
    """ 

    cursor.execute(query, (status, task_name))
    conn.commit()

    cursor.close()
    conn.close()

def download_task():
    download_path = os.path.abspath(os.path.join(download_dir, object_name))

    try:
        client.fget_object(bucket_name, object_name, download_path)
        print(f"Task downloaded to {download_path}")
        print(f"{object_name} downloaded")
        return download_path
    except S3Error as e:
        print(e)
        exit(1)
    
def run_task(download_path):
    try:
        process = subprocess.Popen(
            ["python", download_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # 줄 단위로 버퍼링
        )

        print(f"Task {task_name} executed")
        for line in process.stdout:
            print(line,end="")

        process.wait()
        print(f"\n✅ 실행 종료 (종료 코드: {process.returncode})")

        if process.returncode != 0:
            print("⚠️ 오류가 발생했습니다.")
            
        
        return process.returncode
            
    except Exception as e:
        print(f"❌ 실행 중 예외 발생: {e}")
        
class CPUSampler:
    """
    Kubelet Summary API (/stats/summary)에서 우리 파드의 CPU를 2초 주기로 수집.
    usageNanoCores가 있으면 즉시값, 없으면 usageCoreNanoSeconds 차분/시간으로 레이트 계산.
    """
    def __init__(self, node_name, namespace, pod_name, interval=2.0):
        self.node_name = node_name
        self.namespace = namespace
        self.pod_name = pod_name
        self.interval = interval
        self.samples_m = []
        self._stop = threading.Event()
        self.started_at = None
        self.ended_at = None
        self._last_ns = None
        self._last_ts = None

        k8s_config.load_incluster_config()
        self.core = k8s_client.CoreV1Api()

    def _to_m(self, nano_cores: int) -> int:
        # 1 core = 1e9 nano-cores -> m = (nano / 1e9) * 1000
        return int(round(nano_cores / 1_000_000.0))

    def _rate_to_nano_cores(self, delta_usage_ns: int, delta_seconds: float) -> int:
        if delta_seconds <= 0:
            return 0
        # usageCoreNanoSeconds 는 누적값(나노초 * 코어) → 초당 나노코어
        return int(delta_usage_ns / delta_seconds)

    def _fetch_summary(self) -> dict:
        raw = self.core.connect_get_node_proxy_with_path(
            name=self.node_name, path="stats/summary"
        )
        # python k8s client returns string
        return json.loads(raw)

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
            # 컨테이너별 합산
            for c in pod.get("containers", []):
                cpu = c.get("cpu", {})
                # 1) 즉시값이 있으면 가장 정확
                if "usageNanoCores" in cpu and cpu["usageNanoCores"] is not None:
                    total_nano_cores += int(cpu["usageNanoCores"])
                # 2) 없으면 누적값으로 레이트 계산
                elif "usageCoreNanoSeconds" in cpu and cpu["usageCoreNanoSeconds"] is not None:
                    now_ts = datetime.datetime.fromisoformat(cpu.get("time").rstrip("Z"))
                    curr_ns = int(cpu["usageCoreNanoSeconds"])
                    if self._last_ns is not None and self._last_ts is not None:
                        delta_ns = max(0, curr_ns - self._last_ns.get(c.get("name"), 0))
                        delta_t = (now_ts - self._last_ts.get(c.get("name"), now_ts)).total_seconds()
                        total_nano_cores += self._rate_to_nano_cores(delta_ns, delta_t)
                    # 캐시 갱신
                    if self._last_ns is None: self._last_ns = {}
                    if self._last_ts is None: self._last_ts = {}
                    self._last_ns[c.get("name")] = curr_ns
                    self._last_ts[c.get("name")] = now_ts
                # else: 값이 없으면 스킵

            self.samples_m.append(self._to_m(total_nano_cores))
        except Exception:
            # 일시 오류는 무시하고 다음 주기
            pass

    def _loop(self):
        while not self._stop.is_set():
            self.sample_once()
            time.sleep(self.interval)

    def start(self):
        self.started_at = datetime.datetime.utcnow()
        self._th = threading.Thread(target=self._loop, daemon=True)
        self._th.start()

    def stop(self):
        self._stop.set()
        if hasattr(self, "_th"):
            self._th.join(timeout=5)
        self.ended_at = datetime.datetime.utcnow()

    def median_m(self):
        return int(statistics.median(self.samples_m)) if self.samples_m else None

if __name__ == "__main__":

    # 1) 메트릭 수집 시작
    sampler = CPUSampler(POD_NAMESPACE, POD_NAME, interval=SAMPLE_SEC)
    sampler.start()

    download_path = download_task()
    return_code = run_task(download_path)

    sampler.stop()
    median_m = sampler.median_m()
    save_cpu_median(task_name, POD_NAME, POD_NAMESPACE,
                    median_m, SAMPLE_SEC, len(sampler.samples_m),
                    sampler.started_at, sampler.ended_at)


    if return_code == 0:
        update_task_status_and_completed_at(task_name, "terminated")
        print(f"✅ 모든 프로그램이 정상적으로 종료되었습니다 (종료 코드: {return_code})")




