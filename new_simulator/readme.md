공통 설계(핵심 철학)

스코어 기반 최소화 배치: 후보 클러스터마다 점수 계산 → 최저 점수 노드 선택.

점수식 구조 동일:
score = a·ActiveNodes + b·Penalty(CPU) + c·Workspan + d·Carbon
(둘 다 “정규화 → 가중합” 패턴 사용)

ETA(대기시간) 모델: 배치하면 그 노드의 대기시간/큐가 실행시간만큼 증가.

탄소·자원·대기 요소를 동시에 고려해서 균형 배치.

코드 단위 대응표
1) 가중치 로딩

실행기 코드: load_weights() 로 **DB(weights 테이블)**에서 a,b,c,d 읽음.

시뮬레이터: 입력으로 List[WeightVector](개체군) 받음.
→ 운영에서는 학습기가 DB에 최적 가중치를 쓰면, 실행기가 그걸 읽는 구조.

2) 클러스터 상태 스냅샷

실행기 코드: get_cluster_info_from_db() → Node 객체(이름/IP/리전, ETA).

시뮬레이터: bootstrap_clusters(spec) → SimCluster(이름/리전/CPU/ETA/Carbon).
→ 둘 다 “외부에서 가져온 스냅샷을 내부 객체로 전환”해서 씀.

3) ETA(대기시간) 업데이트

실행기 코드: Node.assign_task() → expected_finish_at 갱신 → ETA=남은 시간.

시뮬레이터: _apply_assignment() → eta_sec += exec_sec.
→ 같은 개념(대기시간 증가), 구현만 다름(시뮬레이터는 “초” 누적식).

4) 활성 노드(분산도) surrogate

실행기 코드:

temp_usage = [u...] ; temp_usage[idx] = 50  # 가정치
count = sum(1 for u in temp_usage if u >= 8.5)


시뮬레이터:

_active_nodes_if_assign(...): 대상 노드 사용률 +30%p 가정 후 ≥8.5% 카운트


차이: 실행기는 “그 노드에 할당 시 사용률을 50%로 고정 가정”, 시뮬레이터는 “+30%p 증가 가정”.
→ 정책 파라미터 차이일 뿐, 의도(“넣는다고 가정했을 때 활성 노드 수”)는 동일.

5) CPU 페널티

둘 다 동일 공식: 10 ** (4 * (usage / 100))
→ 고사용률 노드에 급격한 페널티.

6) Workspan

둘 다: 현재 대기(ETA) + 이번 작업 실행시간(estimated_time/exec_sec).

7) Carbon(탄소) 항

실행기 코드: get_carbon_info(...).integratedEmission 사용(리전/기간 기반 추정).

시뮬레이터: task.carbon_intensity가 있으면 우선, 없으면 cluster.carbon 사용.
→ 실제 운영 지표 vs. 오프라인 리플레이용 대체 신호의 차이.

8) 정규화 + 가중합

실행기 코드: normalize(x, min, max)(epsilon 포함), 상수 범위로 스케일 → a_w,b_w,c_w,d_w 가중합.

시뮬레이터: SimulatorConfig.ranges로 스케일 → WeightVector(a,b,c,d) 가중합.
→ 같은 구조. 실행기는 고정 범위 상수, 시뮬레이터는 설정에서 조정.

9) 후보 중 최소 점수 선택

둘 다: argmin(scores)로 베스트 노드 선택 → 배치/상태 갱신.

10) 로깅/지표

실행기 코드: CSV(task_log.csv)에 매 배치 시 스냅샷 저장(원시값/정규화/점수).

시뮬레이터: 한 가중치 시뮬레이션 후 SimMetrics 반환(p95/mean latency, 탄소 합, SLA).
→ 실행기는 온라인 로그 축적, 시뮬레이터는 오프라인 성능 요약.

무엇이 다른가? (역할관점 정리)
구분   실행기(지금 코드)   시뮬레이터(제가 만든 코드)
목적   실시간 배치 (들어온 작업 즉시 스케줄)   오프라인 평가 (로그로 여러 가중치 후보 비교)
상태 입력   실시간 CPU/탄소/ETA, DB 가중치   과거 로그(HistTask), 초기 스냅샷, 후보 가중치 집합
산출   선택 노드, CSV 로깅   (WeightVector, SimMetrics) 리스트(피트니스 오름차순)
정규화   상수 범위   Config로 조정
분산 surrogate   대상 노드 사용률=50% 가정   대상 노드 사용률 +30%p 가정
탄소 항   API의 integratedEmission   task.carbon_intensity 또는 cluster.carbon
지표   로그만   mean/p95 latency, total carbon, SLA 미스 등
결론 (요청하신 “비슷한 부분”)

점수식/최소화/배치 업데이트 구조는 거의 동일합니다.

ActiveNodes / CPU Penalty / Workspan / Carbon → 정규화 후 a,b,c,d 가중합

argmin으로 최적 노드 선택

배치 후 ETA 증가(큐가 늘어남)

차이는 실시간 vs. 오프라인, 데이터 소스, 파라미터값(50% vs +30%p), 정규화 범위 관리 방식 정도예요.
