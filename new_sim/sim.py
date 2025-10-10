# simulator.py
# Learner [4] Simulation (Replay Virtualization) — 4 weights only (a,b,c,d)
# - Input  : [2] Log collection -> List[HistTask]
# - Input  : [3] Initial population -> List[WeightVector] (외부 생성값을 '그대로' 전달)
# - Output : per-weight SimMetrics (fitness, carbon, SLA, latency, assignments)
#
# 협업 규약:
#   - 실행기(온라인) 점수식과 동일한 4항목 a/b/c/d만 사용
#   - [3] 초기 개체군은 반드시 외부에서 생성하여 evaluate_population()에 전달
#   - [2] 로그 수집은 HistTask 리스트를 제공
#
# 트러블슈팅 가이드(요약):
#   - population이 빈 리스트면: Simulator.ensure_population()에서 예외 발생 → [3] 단계 점검
#   - 점수 폭주/스케일 이상: SimulatorConfig.ranges(정규화 범위), cpu_increment_on_assign 확인
#   - 탄소 수치 이상: HistTask.carbon_intensity 또는 클러스터 carbon 주입 로직 확인([INTEGRATION] 주석 지점)
#   - SLA 계산 이상: HistTask.sla_deadline_sec 값 유효성/단위(초) 확인

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
    """
    [2] 로그 수집 단계가 제공해야 하는 '단일 작업' 레코드.
    필수: job_id, arrival_ts(datetime), exec_sec(int), avg_cpu(float)
    선택: carbon_intensity(없으면 0.0 허용), placed_cluster, sla_deadline_sec 등

    ⚠ 문제 발생 시 점검:
      - arrival_ts 타입이 datetime인지 확인 (str이면 파싱 필요)
      - exec_sec, avg_cpu가 음수가 아닌지 확인
      - carbon_intensity가 음수/None이면 0.0으로 주입하거나 클러스터 carbon 사용
    """
    job_id: str
    arrival_ts: datetime
    exec_sec: int
    avg_cpu: float
    carbon_intensity: float  # 없으면 0.0으로 들어와도 됨
    placed_cluster: str      # 실제 과거 배치(참고용)
    # ↓ 확장 필드(이번 버전에서는 사용하지 않지만 로그는 보존)
    user_region: Optional[str] = None
    data_region: Optional[str] = None
    data_size_gb: float = 0.0
    sla_deadline_sec: Optional[int] = None


@dataclass
class WeightVector:
    """
    [3] 초기 개체군 후보 (외부 생성).
    score = a*ActiveNodes + b*Penalty(CPU) + c*Workspan + d*Carbon

    ⚠ 문제 발생 시 점검:
      - a,b,c,d가 모두 숫자인지(문자/None 금지)
      - 음수 허용은 정책적 선택이지만 기본은 0 이상 권장
    """
    a: float
    b: float
    c: float
    d: float


@dataclass
class SimCluster:
    """
    시뮬레이터 내부의 가상 클러스터 상태.
    - carbon: 클러스터 측 탄소 신호(간단히 상수/최근 평균으로 둡니다)

    ⚠ 문제 발생 시 점검:
      - cpu_usage_pct(%)가 0~100 범위를 벗어나면 점수 왜곡 가능
      - eta_sec(초), carbon 스케일/단위가 환경과 맞는지 확인
    """
    name: str
    region: str
    cpu_usage_pct: float     # 현재 CPU 사용률(%)
    eta_sec: int             # 현재 큐 길이(초)
    carbon: float            # 탄소 신호(클러스터 기준)


@dataclass
class SimMetrics:
    """
    한 가중치로 전체 리플레이를 수행했을 때의 지표.
    - fitness가 낮을수록 좋은 정책.

    assignments: [(job_id, cluster_name)] — 선택 결과를 디버깅/검증에 활용
    """
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
    """
    피트니스 구성:
      fitness = alpha*total_carbon + beta*sla_miss + gamma*p95_latency + zeta*mean_latency

    ranges: 각 점수항 정규화(0..1 스케일) 구간.
      - 범위가 현실과 동떨어지면 특정 항목이 과도하게 지배할 수 있음 → 조정 필요

    cpu_increment_on_assign:
      - 작업 배치 시 CPU 사용률 증가량(간이 모델)
      - 과도하면 penalty가 급증 → score 왜곡 가능

    seed:
      - 재현성 확인용 (시뮬레이션 자체는 결정적이나, 확장 시 랜덤 요소 도입 대비)
    """
    alpha: float = 1.0
    beta: float = 100.0
    gamma: float = 0.1
    zeta: float = 0.0

    pctl_for_latency: float = 0.95  # P95 계산용

    ranges: dict = field(default_factory=lambda: {
        "work_nodes": (0.0, 10.0),        # 활성 노드(분산도 surrogate)
        "penalty":    (1.0, 1e4),         # CPU penalty ~ 10^(4 * usage%)
        "workspan":   (0.0, 24*3600.0),   # ETA+실행시간(0~24h)
        "carbon":     (0.0, 1000.0),      # gCO2 (스케일링 용)
    })

    cpu_increment_on_assign: float = 20.0
    seed: Optional[int] = None


# ==============================
# ===== Helper Functions =======
# ==============================

def _normalize(val: float, lo: float, hi: float) -> float:
    """[내부] 0..1 정규화. hi<=lo면 정규화 생략(원시값 유지)."""
    if hi <= lo:
        return val
    val = max(lo, min(hi, val))
    return (val - lo) / (hi - lo)

def _cpu_penalty(usage_pct: float) -> float:
    """CPU 사용률이 높을수록 기하급수적으로 증가하는 페널티(실행기와 동일 계열)."""
    return 10 ** (4.0 * (usage_pct / 100.0))

def _active_nodes_if_assign(usages: List[float], target_idx: int) -> int:
    """해당 노드에 작업을 넣는다고 가정했을 때 활성 노드 수(8.5% 이상) 카운트."""
    tmp = list(usages)
    tmp[target_idx] = min(100.0, tmp[target_idx] + 30.0)  # 간단한 증가 모델
    return sum(1 for u in tmp if u >= 8.5)


# ==============================
# ======== Simulator ===========
# ==============================

class Simulator:
    """
    Learner [4] Simulation 엔진 — 4가중치 전용.
    - evaluate_population(): 개체군 전체 평가
    - simulate(): 특정 가중치에 대한 상세 시뮬레이션
    """

    def __init__(self, config: SimulatorConfig):
        self.cfg = config
        if config.seed is not None:
            random.seed(config.seed)

    # ---------- [ADD] 빈 개체군 방지 검증 ----------
    @staticmethod
    def ensure_population(weights_population: list):
        """
        [INTEGRATION] [3] 단계에서 초기 개체군을 '반드시 생성'하여 넘겨야 합니다.
        비어 있으면 즉시 예외를 발생시켜 파이프라인 문제를 조기에 드러냅니다.
        """
        if not weights_population:
            raise ValueError(
                "[simulator] weights_population is empty. "
                "Generate initial population in step [3] and pass it to evaluate_population()."
            )

    # ---------- [INTEGRATION] ----------
    # [2] 또는 외부 모듈에서 "초기 클러스터 스냅샷"을 만들어 전달합니다.
    # 형식: [(name, region, cpu_usage_pct, eta_sec, carbon), ...]
    # 데이터 연결 지점: 모니터링/메트릭 수집 어댑터에서 이 튜플 리스트를 만들어 주입
    def bootstrap_clusters(self, clusters_spec: List[Tuple[str, str, float, int, float]]) -> List[SimCluster]:
        return [SimCluster(*row) for row in clusters_spec]

    def _score_cluster(self, clusters: List[SimCluster], idx: int,
                       task: HistTask, w: WeightVector) -> float:
        """
        단일 클러스터의 배치 점수(낮을수록 좋음).
        score = a*ActiveNodes + b*Penalty + c*Workspan + d*Carbon

        ⚠ 점수 폭주 시:
          - ranges(정규화 구간) 재점검
          - cpu_increment_on_assign 과도 여부 확인
          - carbon 단위/스케일 확인 (너무 큰 값이면 d 항이 지배)
        """
        c = clusters[idx]

        # 기본 피처 계산
        active_nodes = _active_nodes_if_assign([x.cpu_usage_pct for x in clusters], idx)
        penalty      = _cpu_penalty(c.cpu_usage_pct)
        workspan     = c.eta_sec + task.exec_sec

        # 탄소 신호:
        #   - 작업 로그에 carbon_intensity가 유효하면 우선 사용
        #   - 없으면 클러스터 carbon 사용
        # ---------- [INTEGRATION] ----------
        # 운영에서 "시간대별/리전별 예측 탄소"를 쓰는 경우, 이 지점에서 주입하도록 어댑터를 연결
        carbon_val   = task.carbon_intensity if task.carbon_intensity > 0.0 else c.carbon

        # 정규화(0..1)
        r = self.cfg.ranges
        nw = _normalize(active_nodes, *r["work_nodes"])
        np = _normalize(penalty,      *r["penalty"])
        ns = _normalize(workspan,     *r["workspan"])
        nc = _normalize(carbon_val,   *r["carbon"])

        # 최종 점수
        return w.a*nw + w.b*np + w.c*ns + w.d*nc

    def _apply_assignment(self, clusters: List[SimCluster], idx: int, task: HistTask):
        """
        가상 배치 적용:
        - 선택된 클러스터의 큐(ETA) 증가
        - CPU 사용률 증가(간단 모델: avg_cpu 없으면 config 기본값)

        ⚠ CPU 증가량이 너무 크면 penalty 폭주 → 점수 왜곡 → ranges와 함께 조절 필요
        """
        inc = task.avg_cpu if (task.avg_cpu and task.avg_cpu > 0.0) else self.cfg.cpu_increment_on_assign
        clusters[idx].eta_sec += task.exec_sec
        clusters[idx].cpu_usage_pct = min(100.0, clusters[idx].cpu_usage_pct + inc)

    def simulate(self, tasks: List[HistTask], clusters: List[SimCluster], w: WeightVector) -> SimMetrics:
        """
        한 가중치(w)에 대해 작업 시퀀스 전체를 리플레이하고 성능지표를 계산합니다.

        ⚠ 로그 정합성 이슈 발생 시:
          - tasks가 arrival_ts 기준 오름차순인지 (내부에서 정렬하지만 timezone 문제 주의)
          - exec_sec 음수/0 여부
        """
        tasks_sorted = sorted(tasks, key=lambda t: t.arrival_ts)

        total_carbon = 0.0
        sla_miss = 0
        latencies: List[float] = []
        assigns: List[Tuple[str, str]] = []

        for task in tasks_sorted:
            # 1) 현재 상태에서 모든 클러스터 점수 계산 -> 최솟값 선택
            scores = [(self._score_cluster(clusters, i, task, w), i)
                      for i in range(len(clusters))]
            scores.sort(key=lambda x: x[0])
            chosen_idx = scores[0][1]
            chosen = clusters[chosen_idx]

            # 2) 레이턴시(대기시간) = 현재 ETA
            latency = chosen.eta_sec
            latencies.append(latency)

            # 3) 탄소 누적(간단 모델)
            # ---------- [INTEGRATION] ----------
            # 총 탄소를 실제 단위로 정교하게 하려면(예: kWh 연동),
            # 여기서 실행시간×전력×탄소강도 형태로 교체
            carbon_val = task.carbon_intensity if task.carbon_intensity > 0.0 else chosen.carbon
            total_carbon += carbon_val * task.exec_sec

            # 4) SLA 체크 (deadline 제공 시)
            if task.sla_deadline_sec and (latency + task.exec_sec) > task.sla_deadline_sec:
                sla_miss += 1

            # 5) 상태 업데이트(가상 배치)
            self._apply_assignment(clusters, chosen_idx, task)
            assigns.append((task.job_id, chosen.name))

        # 6) 레이턴시 요약(P95/평균)
        if len(latencies) >= 2:
            qtiles = quantiles(latencies, n=100)
            p95 = qtiles[int(self.cfg.pctl_for_latency*100) - 1]
        else:
            p95 = latencies[0] if latencies else 0.0
        mean_lat = sum(latencies)/len(latencies) if latencies else 0.0

        # 7) 피트니스(낮을수록 좋음)
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
        """
        [3] 초기 개체군 후보 각각을 동일한 초기 클러스터 상태에서 시뮬레이션.
        반환: [(WeightVector, SimMetrics)] — fitness 오름차순(최적이 맨 앞)

        [INTEGRATION] weights_population은 '반드시' [3]에서 생성되어 이 함수로 전달됩니다.
        내부에서 population을 만들지 않습니다.
        """
        # ---------- [ADD] 개체군 검증 ----------
        self.ensure_population(weights_population)

        results = []
        for w in weights_population:
            clusters = self.bootstrap_clusters(base_clusters_spec)
            metrics = self.simulate(tasks, clusters, w)
            results.append((w, metrics))
        results.sort(key=lambda x: x[1].fitness)
        return results
