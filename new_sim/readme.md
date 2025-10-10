1) 어디에 두고, 어떻게 import 하나요?

폴더 구조(예시)

project/
└─ learner/
   ├─ sim.py            # ← 지금 파일(시뮬레이터 모듈)  :contentReference[oaicite:1]{index=1}
   ├─ adapters.py       # DB/로그 → HistTask, 클러스터 스냅샷 변환
   ├─ population.py     # 초기 개체군(가중치) 생성
   └─ trainer.py        # 학습기의 main 러닝 루프(여기서 sim.py 호출)


trainer.py 같은 학습기 메인에서 이렇게 import 합니다:

from sim import Simulator, SimulatorConfig, HistTask, WeightVector  # ← sim.py의 공개 API


(모듈 이름은 파일명 기준. 파일명이 sim.py니까 from sim import ...)

2) 무엇을 누가 준비해서 넘겨야 하나요?

sim.py의 핵심 공개 API는 다음입니다.

입력

tasks: list[HistTask] ← [2] 로그 수집에서 생성

base_clusters_spec: list[tuple] ← “초기 스냅샷” [(name, region, cpu%, eta_sec, carbon), ...]

weights_population: list[WeightVector] ← [3] 초기 개체군(가중치 후보들)

호출

Simulator(cfg).evaluate_population(tasks, base_clusters_spec, weights_population)

출력

[(WeightVector, SimMetrics)] (fitness 오름차순 정렬: 0번이 최적)

즉, 학습기 메인 러닝 루프가 위 3가지를 준비해서 evaluate_population(...)에 넘기면 됩니다. (시뮬레이터는 내부에서 population을 만들지 않습니다 — 빈 리스트가 오면 예외를 던지도록 방어 코드가 들어있습니다.)

3) 최소 실행 예제 (trainer.py)

아래 파일 하나로 “학습기 1회 실행”이 됩니다. 메인에서 실행하면 이게 동작합니다. (실제 DB·로그 환경에 맞게 adapters/population 부분만 교체하세요.)

# learner/trainer.py
from sim import Simulator, SimulatorConfig, HistTask, WeightVector
from datetime import datetime

# (임시) [2] 로그 수집 결과 대체 — 실제에선 adapters.py로 DB에서 읽어오세요
def load_histtasks_dummy() -> list[HistTask]:
    return [
        HistTask(job_id="job-1", arrival_ts=datetime(2025, 10, 11, 10, 0, 0),
                 exec_sec=120, avg_cpu=15.0, carbon_intensity=0.0,
                 placed_cluster="c-kr-1"),
        HistTask(job_id="job-2", arrival_ts=datetime(2025, 10, 11, 10, 0, 5),
                 exec_sec=300, avg_cpu=10.0, carbon_intensity=0.0,
                 placed_cluster="c-jp-1"),
    ]

# (임시) 현재 클러스터 스냅샷 — 실제에선 adapters.py로 DB/모니터링에서 읽어오세요
def load_cluster_snapshot_dummy():
    # [(name, region, cpu_usage_pct, eta_sec, carbon)]
    return [
        ("c-kr-1", "KR", 25.0,  0, 150.0),
        ("c-jp-1", "JP", 30.0, 30, 180.0),
        ("c-fr-1", "FR", 15.0, 10, 110.0),
    ]

# (임시) [3] 개체군 — 실제에선 population.py로 GA/랜덤/그리드 생성
def load_population_dummy() -> list[WeightVector]:
    return [
        WeightVector(1.0, 1.0, 1.0, 1.0),
        WeightVector(0.8, 1.2, 1.0, 1.1),
        WeightVector(1.2, 0.8, 1.1, 0.9),
    ]

def train_once():
    # 1) 데이터 로드
    tasks = load_histtasks_dummy()
    clusters_spec = load_cluster_snapshot_dummy()
    population = load_population_dummy()

    # 2) 시뮬레이터 구성/호출
    cfg = SimulatorConfig(alpha=1.0, beta=100.0, gamma=0.1, zeta=0.0, seed=42)
    sim = Simulator(cfg)
    results = sim.evaluate_population(tasks, clusters_spec, population)

    # 3) 결과 사용: 0번이 최적
    best_w, best_m = results[0]
    print("[BEST] weights:", best_w)
    print("        fitness:", round(best_m.fitness, 3))
    print("        carbon :", round(best_m.total_carbon, 2))
    print("        p95    :", round(best_m.p95_latency, 2),
          "| mean:", round(best_m.mean_latency, 2),
          "| sla_miss:", best_m.sla_miss)

    # 4) (선택) DB에 저장 → 실행기(Serving Loop)는 다음 작업부터 최신 가중치 사용
    # save_best_weights_to_db(best_w)  # policy_store.py에 구현

if __name__ == "__main__":
    # 메인으로 실행하면 이 함수가 실행됩니다.
    train_once()


요약: 메인문이 실행되면 위 train_once()가 돌고, 그 안에서 sim.evaluate_population(...)이 호출되어 시뮬레이션이 수행됩니다. 시뮬레이터 자체는 자동 실행되지 않습니다 — 반드시 이런 식으로 호출해야 합니다.

4) 실제 운영 연결(실행기와 합치기)

실행기(Serving Loop)는 지금처럼 DB weights 테이블에서 (a_w,b_w,c_w,d_w)를 읽어 사용.

학습기(trainer.py)는 주기적으로 위 시뮬레이터를 돌려 최적 가중치를 찾고 weights 테이블을 업데이트.

실행기는 다음 작업부터 자동으로 최신 가중치 적용(서로 느슨 결합).

주기 실행은 cron/Kubernetes Job/Airflow 등으로 python learner/trainer.py만 돌리면 끝.

adapters/population/policy_store는 환경에 맞춘 구현으로 교체.

5) 자주 묻는 포인트

정규화 범위는 어디서 바꾸나요?
→ SimulatorConfig.ranges를 조절하세요. 환경 스케일에 맞아야 a/b/c/d의 균형이 맞습니다.

탄소 신호가 없으면?
→ HistTask.carbon_intensity == 0.0이면 클러스터의 carbon 값을 씁니다. 초기 스냅샷에 현실적인 값을 넣어주세요.

빈 개체군(population) 전달 시?
→ Simulator.ensure_population에서 즉시 예외를 내며 멈춥니다. [3]에서 반드시 생성해서 넘기세요.
