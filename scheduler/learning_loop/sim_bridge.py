# sim_bridge.py
from typing import List, Dict, Optional
from datetime import datetime
from sim import Simulator, SimulatorConfig, HistTask, WeightVector

# ---------- 1) 로그(dict) → HistTask ----------
def to_histtasks(rows: List[Dict]) -> List[HistTask]:
    """
    get_task_info.get_processed_tasks(...) 가 반환하는 dict 리스트를
    sim.HistTask 리스트로 변환한다.
    기대 키(예시):
      task_id, task_name, dispatched_at, estimated_runtime, actual_runtime,
      avg_cpu_usage (m), avg_mem_usage, cluster_name, carbon_intensity, completion_at, queue_delay
    """
    tasks: List[HistTask] = []
    for r in rows:
        dispatched = r.get("dispatched_at")
        if isinstance(dispatched, str):
            dispatched = datetime.fromisoformat(dispatched.replace("Z", ""))
        elif dispatched is None:
            dispatched = datetime.utcnow()

        exec_sec = int(r.get("actual_runtime") or r.get("estimated_runtime") or 60)
        avg_cpu_m = float(r.get("avg_cpu_usage") or 0.0)
        carbon = float(r.get("carbon_intensity") or 0.0)
        cluster = r.get("cluster_name") or ""  # 없으면 'default'로 취급됨(sim.py 내부)

        tasks.append(HistTask(
            job_id=str(r.get("task_id") or r.get("task_name")),
            arrival_ts=dispatched,
            exec_sec=exec_sec,
            avg_cpu=avg_cpu_m,              # m 단위 → sim.py에서 % 자동 변환
            carbon_intensity=carbon,        # 0이면 클러스터 평균 탄소 사용
            placed_cluster=cluster,
        ))
    return tasks

# ---------- 2) 가중치(dict) → WeightVector ----------
def to_weightvectors(candidate_rows: List[Dict]) -> List[WeightVector]:
    """
    generate.generate_candidates(...) 가 반환하는 dict 리스트를
    sim.WeightVector 리스트로 변환한다.
    예상 키: a_w, b_w, c_w, d_w
    """
    wvecs: List[WeightVector] = []
    for c in candidate_rows:
        a = float(c.get("a_w"))
        b = float(c.get("b_w"))
        cw = float(c.get("c_w"))
        d = float(c.get("d_w"))
        wvecs.append(WeightVector(a=a, b=b, c=cw, d=d))
    return wvecs

# ---------- 3) 시뮬레이션 실행 ----------
def run_simulation_as_dicts_from_modules(
    task_rows: List[Dict],
    weight_rows: List[Dict],
    cfg: Optional[SimulatorConfig] = None,
    clusters_spec: Optional[list] = None,
) -> List[Dict]:
    """
    - get_task_info.get_processed_tasks() 결과와
      generate.generate_candidates() 결과를 받아
      sim.py 시뮬레이션을 수행하고
      결과를 dict 리스트로 반환한다.
    - clusters_spec이 None이면 로그로부터 자동 생성(sim.py의 clusters_from_tasks 사용)
    """
    cfg = cfg or SimulatorConfig(
        capacity_m=4000.0,
        cluster_cpu_unit="m",
        task_avg_cpu_unit="m",
        alpha=1.0, beta=100.0, gamma=0.1, zeta=0.0
    )

    tasks = to_histtasks(task_rows)
    weight_vecs = to_weightvectors(weight_rows)

    sim = Simulator(cfg)
    results = sim.evaluate_population(tasks, clusters_spec, weight_vecs)

    out: List[Dict] = []
    for w, m in results:
        out.append({
            "weights": {"a": w.a, "b": w.b, "c": w.c, "d": w.d},
            "fitness": m.fitness,
            "total_carbon": m.total_carbon,
            "sla_miss": m.sla_miss,
            "p95_latency": m.p95_latency,
            "mean_latency": m.mean_latency,
            "assignments": m.assignments,  # 필요 없으면 제거 가능
        })
    return out
