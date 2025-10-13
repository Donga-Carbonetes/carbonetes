# log_adapter.py
from sim import HistTask
from datetime import datetime
from get_tasks import get_processed_tasks  # 기존 코드 import

def to_histtasks(db_config):
    """MySQL에서 가져온 로그를 sim.py용 HistTask 리스트로 변환"""
    processed_tasks = get_processed_tasks(db_config)
    hist_tasks = []
    for row in processed_tasks:
        try:
            dispatched = row.get("dispatched_at")
            if isinstance(dispatched, str):
                dispatched = datetime.fromisoformat(dispatched.replace("Z", ""))

            exec_sec = int(row.get("actual_runtime") or row.get("estimated_runtime") or 60)
            avg_cpu = float(row.get("avg_cpu_usage") or 0.0)
            carbon = float(row.get("carbon_intensity") or 0.0)

            hist_tasks.append(HistTask(
                job_id=str(row.get("task_id")),
                arrival_ts=dispatched or datetime.utcnow(),
                exec_sec=exec_sec,
                avg_cpu=avg_cpu,          # m 단위 → sim.py가 자동 변환
                carbon_intensity=carbon,  # 없으면 0.0 → 클러스터 carbon 사용
                placed_cluster=row.get("cluster_name") or "",
            ))
        except Exception as e:
            print(f"⚠️ 변환 실패: {e}")
    return hist_tasks
