import time
import queue
from collections import deque
from kubernetes import client, config, watch

# kubeconfig 로드 (Pod 내부에서 실행 시는 config.load_incluster_config() 사용)
try:
    config.load_incluster_config()
except:
    config.load_kube_config()

batch_v1 = client.BatchV1Api()
custom_api = client.CustomObjectsApi()

# 실행 중 Job stack (LIFO) / 대기 큐 (FIFO)
running_stack = []
waiting_queue = deque()

# CPU 임계값 설정
CPU_HIGH = 0.60  # 60%
CPU_LOW = 0.50   # 50% (히스테리시스 방지)

def get_cluster_cpu_usage():
    """
    클러스터 전체 CPU 사용률을 계산.
    metrics-server가 설치되어 있어야 함.
    """
    try:
        metrics = custom_api.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="nodes"
        )
        total_usage = 0
        total_capacity = 0
        for node in metrics["items"]:
            usage_str = node["usage"]["cpu"]
            # 예: "1234n" or "150m" 형태
            if usage_str.endswith("n"):
                usage_millicores = int(usage_str[:-1]) / 1e6
            elif usage_str.endswith("m"):
                usage_millicores = int(usage_str[:-1])
            else:
                usage_millicores = int(usage_str) * 1000

            capacity_str = node["metadata"]["annotations"].get("capacity.cpu", "1000m")
            capacity_millicores = int(capacity_str[:-1]) if capacity_str.endswith("m") else int(capacity_str) * 1000

            total_usage += usage_millicores
            total_capacity += capacity_millicores

        if total_capacity == 0:
            return 0.0
        return total_usage / total_capacity

    except Exception as e:
        print(f"[WARN] CPU metrics 조회 실패: {e}")
        return 0.0


def suspend_job(namespace, job_name, suspend=True):
    """
    Job을 일시중지(suspend=true)하거나 재개(suspend=false)
    """
    patch = {"spec": {"suspend": suspend}}
    batch_v1.patch_namespaced_job(name=job_name, namespace=namespace, body=patch)
    print(f"[INFO] Job {job_name} suspend={suspend}")


def is_mltask(job):
    labels = (job.metadata.labels or {})
    tmpl_labels = (job.spec.template.metadata.labels or {})
    return "mltask" in labels or "mltask" in tmpl_labels


def watch_jobs(namespace="default"):
    w = watch.Watch()
    for event in w.stream(batch_v1.list_namespaced_job, namespace=namespace, label_selector="mltask=true"):
        job = event["object"]
        etype = event["type"]
        name = job.metadata.name

        if etype == "ADDED":
            if name not in running_stack and not job.spec.suspend:
                running_stack.append((namespace, name))
                print(f"[ADD] {name} 실행 스택에 추가")

        elif etype == "MODIFIED":
            if job.status.succeeded or job.status.failed:
                if (namespace, name) in running_stack:
                    running_stack.remove((namespace, name))
                    print(f"[COMPLETE] {name} 완료 → 스택에서 제거")

        elif etype == "DELETED":
            if (namespace, name) in running_stack:
                running_stack.remove((namespace, name))
                print(f"[DELETE] {name} 삭제됨 → 스택에서 제거")


def controller_loop():
    """
    주기적으로 CPU를 감시하면서 suspend/resume 제어
    """
    while True:
        cpu_usage = get_cluster_cpu_usage()
        print(f"[CPU] 사용률: {cpu_usage * 100:.1f}%")

        if cpu_usage > CPU_HIGH:
            if running_stack:
                ns, job_name = running_stack.pop()
                suspend_job(ns, job_name, True)
                waiting_queue.append((ns, job_name))
                print(f"[ACTION] CPU 과부하 → {job_name} 일시중지 후 대기 큐로 이동")

        elif cpu_usage < CPU_LOW:
            if waiting_queue:
                ns, job_name = waiting_queue.popleft()
                suspend_job(ns, job_name, False)
                running_stack.append((ns, job_name))
                print(f"[ACTION] CPU 안정화 → {job_name} 재개")

        time.sleep(10)  # 10초 주기


if __name__ == "__main__":
    print("[START] Controller 실행 중 ...")
    # Job 감시 스레드 실행
    import threading
    t = threading.Thread(target=watch_jobs, daemon=True)
    t.start()

    # 메인 루프 실행
    controller_loop()
