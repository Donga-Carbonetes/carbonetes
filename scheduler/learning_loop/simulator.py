# sim.py  (auto m→% 변환 지원 버전)
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from statistics import quantiles
from datetime import datetime
import random

# ==============================
# ======= Public Models ========
# ==============================

@dataclass
class HistTask:
    job_id: str
    arrival_ts: datetime
    exec_sec: int
    avg_cpu: float              # 입력 단위: config.task_avg_cpu_unit ('m'|'pct'|'auto')
    carbon_intensity: float     # 0.0이면 클러스터 carbon 사용
    placed_cluster: str
    user_region: Optional[str] = None
    data_region: Optional[str] = None
    data_size_gb: float = 0.0
    sla_deadline_sec: Optional[int] = None


@dataclass
class WeightVector:
    a: float
    b: float
    c: float
    d: float


@dataclass
class SimCluster:
    """
    cpu_usage_input: DB/수집기에서 온 '원시값'
      - config.cluster_cpu_unit이 'm'이면 밀리코어 숫자
      - 'pct'면 % (0~100)
      - 'auto'면 값의 범위로 추정
    """
    name: str
    region: str
    cpu_usage_input: float
    eta_sec: int
    carbon: float

    # 내부 계산용(%). bootstrap 시 채워짐
    cpu_usage_pct: float = 0.0


@dataclass
class SimMetrics:
    fitness: float
    total_carbon: float
    sla_miss: int
    p95_latency: float
    mean_latency: float
    assignments: List[Tuple[str, str]] = field(default_factory=list)


# ==============================
# ========= Config =============
# ==============================

@dataclass
class SimulatorConfig:
    # Fitness = alpha*carbon + beta*sla_miss + gamma*P95 + zeta*mean
    alpha: float = 1.0
    beta: float = 100.0
    gamma: float = 0.1
    zeta: float = 0.0

    pctl_for_latency: float = 0.95

    ranges: dict = field(default_factory=lambda: {
        "work_nodes": (0.0, 10.0),
        "penalty":    (1.0, 1e4),
        "workspan":   (0.0, 24*3600.0),
        "carbon":     (0.0, 1000.0),
    })

    # ★ 총 CPU 용량(밀리코어). 요청: 기본 4000m.
    capacity_m: float = 4000.0

    # ★ 입력 단위 설정 (cluster CPU / task avg_cpu)
    #   'm'  : 밀리코어 입력
    #   'pct': 퍼센트(0~100) 입력
    #   'auto': 값 범위로 자동 판단(>100 => m, 0..1 => fraction, else => pct)
    cluster_cpu_unit: str = "m"
    task_avg_cpu_unit: str = "m"

    # 작업 배치 시 CPU% 증가 기본값(작업 avg_cpu가 없을 때)
    cpu_increment_on_assign_pct: float = 20.0

    # 재현성용
    seed: Optional[int] = None


# ==============================
# ===== Helper Functions =======
# ==============================

def _normalize(val: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return val
    val = max(lo, min(hi, val))
    return (val - lo) / (hi - lo)

def _cpu_penalty(usage_pct: float) -> float:
    return 10 ** (4.0 * (usage_pct / 100.0))

def _active_nodes_if_assign(usages_pct: List[float], target_idx: int) -> int:
    tmp = list(usages_pct)
    tmp[target_idx] = min(100.0, tmp[target_idx] + 30.0)  # 정책 가정치(+30%p)
    return sum(1 for u in tmp if u >= 8.5)

# ---- 단위 변환 유틸 ----
def _to_percent_auto(v: float, capacity_m: float) -> float:
    """
    'auto' 추정 규칙:
      - v > 100           → m 로 간주 → m→%
      - 0 <= v <= 1       → fraction(0..1) → %로 환산
      - 그 외(0~100 범위) → % 로 간주
    """
    if v is None:
        return 0.0
    if v > 100.0:
        return _m_to_percent(v, capacity_m)
    if 0.0 <= v <= 1.0:
        return v * 100.0
    return float(v)

def _m_to_percent(v_m: float, capacity_m: float) -> float:
    if not capacity_m or capacity_m <= 0:
        return 0.0
    return max(0.0, min(100.0, (float(v_m) / float(capacity_m)) * 100.0))

def _normalize_cpu_input(v: float, unit: str, capacity_m: float) -> float:
    unit = (unit or "m").lower()
    if unit == "m":
        return _m_to_percent(v, capacity_m)
    elif unit == "pct":
        return max(0.0, min(100.0, float(v)))
    elif unit == "auto":
        return _to_percent_auto(v, capacity_m)
    else:
        # 알 수 없는 설정 → 안전하게 auto
        return _to_percent_auto(v, capacity_m)


# ==============================
# ======== Simulator ===========
# ==============================

class Simulator:
    def __init__(self, config: SimulatorConfig):
        self.cfg = config
        if config.seed is not None:
            random.seed(config.seed)

    @staticmethod
    def ensure_population(weights_population: list):
        if not weights_population:
            raise ValueError(
                "[simulator] weights_population is empty. "
                "Generate initial population in step [3] and pass it to evaluate_population()."
            )

    # base_clusters_spec: [(name, region, cpu_usage_input, eta_sec, carbon), ...]
    # DB에서 'm' 숫자로 온 값을 그대로 넣어도 됨(기본 unit='m'으로 변환)
    def bootstrap_clusters(self, clusters_spec: List[Tuple[str, str, float, int, float]]) -> List[SimCluster]:
        clusters: List[SimCluster] = []
        for name, region, cpu_in, eta, carbon in clusters_spec:
            c = SimCluster(
                name=name,
                region=region,
                cpu_usage_input=float(cpu_in),
                eta_sec=int(eta),
                carbon=float(carbon),
            )
            # ★ 여기서 자동 변환
            c.cpu_usage_pct = _normalize_cpu_input(
                c.cpu_usage_input, self.cfg.cluster_cpu_unit, self.cfg.capacity_m
            )
            clusters.append(c)
        return clusters

    def _score_cluster(self, clusters: List[SimCluster], idx: int,
                       task: HistTask, w: WeightVector) -> float:
        c = clusters[idx]

        # 모든 클러스터의 % 사용률로 리스트 구성
        usages_pct = [x.cpu_usage_pct for x in clusters]
        active_nodes = _active_nodes_if_assign(usages_pct, idx)
        penalty      = _cpu_penalty(c.cpu_usage_pct)
        workspan     = c.eta_sec + task.exec_sec

        carbon_val   = task.carbon_intensity if task.carbon_intensity > 0.0 else c.carbon

        r = self.cfg.ranges
        nw = _normalize(active_nodes, *r["work_nodes"])
        np = _normalize(penalty,      *r["penalty"])
        ns = _normalize(workspan,     *r["workspan"])
        nc = _normalize(carbon_val,   *r["carbon"])

        return w.a*nw + w.b*np + w.c*ns + w.d*nc

    def _apply_assignment(self, clusters: List[SimCluster], idx: int, task: HistTask):
        # 작업 avg_cpu 입력 단위에 따라 % 증가량 계산
        inc_pct = _normalize_cpu_input(
            task.avg_cpu, self.cfg.task_avg_cpu_unit, self.cfg.capacity_m
        )
        if inc_pct <= 0.0:
            inc_pct = self.cfg.cpu_increment_on_assign_pct

        clusters[idx].eta_sec += task.exec_sec
        clusters[idx].cpu_usage_pct = min(100.0, clusters[idx].cpu_usage_pct + inc_pct)

    def simulate(self, tasks: List[HistTask], clusters: List[SimCluster], w: WeightVector) -> SimMetrics:
        tasks_sorted = sorted(tasks, key=lambda t: t.arrival_ts)

        total_carbon = 0.0
        sla_miss = 0
        latencies: List[float] = []
        assigns: List[Tuple[str, str]] = []

        for task in tasks_sorted:
            scores = [(self._score_cluster(clusters, i, task, w), i)
                      for i in range(len(clusters))]
            scores.sort(key=lambda x: x[0])
            chosen_idx = scores[0][1]
            chosen = clusters[chosen_idx]

            latency = chosen.eta_sec
            latencies.append(latency)

            carbon_val = task.carbon_intensity if task.carbon_intensity > 0.0 else chosen.carbon
            total_carbon += carbon_val * task.exec_sec

            if task.sla_deadline_sec and (latency + task.exec_sec) > task.sla_deadline_sec:
                sla_miss += 1

            self._apply_assignment(clusters, chosen_idx, task)
            assigns.append((task.job_id, chosen.name))

        if len(latencies) >= 2:
            qtiles = quantiles(latencies, n=100)
            p95 = qtiles[int(self.cfg.pctl_for_latency*100) - 1]
        else:
            p95 = latencies[0] if latencies else 0.0
        mean_lat = sum(latencies)/len(latencies) if latencies else 0.0

        fitness = (self.cfg.alpha * total_carbon +
                   self.cfg.beta  * float(sla_miss) +
                   self.cfg.gamma * float(p95) +
                   self.cfg.zeta  * float(mean_lat))

        return SimMetrics(
            fitness=fitness,
            total_carbon=total_carbon,
            sla_miss=sla_miss,
            p95_latency=p95,
            mean_latency=mean_lat,
            assignments=assigns
        )

    def evaluate_population(self,
                            tasks: List[HistTask],
                            base_clusters_spec: List[Tuple[str, str, float, int, float]],
                            weights_population: List[WeightVector]):
        self.ensure_population(weights_population)
        results = []
        clusters = self.bootstrap_clusters(base_clusters_spec)  # ★ 한 번만 객체화
        for w in weights_population:
            # 각 후보마다 같은 시작 상태가 필요하므로 깊은 복제
            cloned = [SimCluster(c.name, c.region, c.cpu_usage_input, c.eta_sec, c.carbon, c.cpu_usage_pct)
                      for c in clusters]
            metrics = self.simulate(tasks, cloned, w)
            results.append((w, metrics))
        results.sort(key=lambda x: x[1].fitness)
        return results