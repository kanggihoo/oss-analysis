---
sha: "a31d82624c27d75f4e771d4fcb78dce16470b383"
created: 2026-10-27
updated: 2026-10-27
sources:
  - repos/DeepTutor/deeptutor/learning/scheduler.py
  - repos/DeepTutor/deeptutor/learning/models.py
  - repos/DeepTutor/deeptutor/learning/policy.py
  - repos/DeepTutor/deeptutor/learning/service.py
depends:
  - ./mastery-engine.md
status: ready
reimplementation: "Python 3 표준 라이브러리, 두 스펙의 전 R-ID(SQLite 대신 메모리 저장소, 제외 범위 미구현). 스펙 T-ID 45개와 추가 6개 51개 통과. 순수 계산 함수는 원본(기준 SHA 복사본)과 같은 입력으로 비교해 불일치 0(compute_mastery 2000, grade_answer 231, 초기 상태 400, schedule_review 1822, retrievability 1822, replay 400, forgetting_risk 800, next_objective 600사례, 고정 시드, 변이 3종으로 비교의 검출력 확인; 영수증·저장소·evidence_id 등 service.py 경로는 원본과 비교하지 않음). 결과: ../../../artifacts/DeepTutor/reimplementation/RESULT.md, 비교: ../../../artifacts/DeepTutor/mastery-demos/diff_test.py. 재검증 필요: 이 판에서 보강한 R-11·R-16의 memory 신규 상태 간격 0 분기, R-18 review_reason 문장·라벨·반올림, get_due_tasks(C-15), T-18~T-26은 위 재구현 비교 범위 밖이다(다만 T-18~T-26은 원본 실행으로는 확인함, run_pure2.py; 순수 계산 규칙의 의미는 바꾸지 않음)"
---

# 복습 스케줄러: 지식점별 복습 시각·망각 위험 계산

> 지식점별 반복 상태(`RepetitionState`)와 평가 증거(`LearningEvidence`)를 입력받아, 다음 복습 시각과 현재 기억 확률·망각 위험을 계산하고, 복습 과제 큐(`ReviewTask`)를 만든다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 지식점이 처음 평가되면 호출자가 `get_initial_state(유형, desired_retention=경로값)`로 반복 상태를 만든다. 첫 복습 시각은 유형별 첫 간격(memory 0일, concept 3일, procedure 3일, design 14일)이다(R-04).
2. 평가 증거가 생길 때마다 `schedule_review(상태, 유형, 증거)`가 상태를 **제자리에서** 갱신한다. 정답이면 **안정도**(stability, 일 단위)가 커지고, 오답이면 줄어든다(R-08~R-10). 직전 복습과 너무 가깝다면(같은 세션) 갱신하지 않는다(R-07).
3. 다음 복습 간격은 `안정도 × (−ln 목표 기억률)` 일이고, 실패 직후면 절반으로 줄인다(R-03, R-11).
4. 증거를 반영한 뒤 `build_review_queue(progress)`가 **모든** 반복 상태에서 복습 과제를 만들고 망각 위험 순으로 정렬해 `progress.review_queue`에 저장한다(R-14).
5. 호출자는 `due_at <= now`인 과제만 골라(`policy.due_reviews`) 쓴다. 다음 목표 선택은 `mastery-engine.md`의 `next_objective`가 한다(R-15).
6. 경로의 목표 기억률을 바꾸면 이미 잡힌 일정을 새 목표에 맞게 늘리거나 줄인다(R-16). 증거 기록이 망가졌을 때는 `replay`로 증거 순서대로 상태를 다시 만든다(R-17).

### 1.2 범위·통합 지점 [필수]
- 제공: 초기 상태, 증거 → 상태 전이, 기억 확률, 망각 위험, 복습 과제 큐와 정렬, 목표 기억률 변경, 증거 재생, 복습 사유 문장.
- 제외(이유):
  - **어떤 증거를 언제 만들지**(채점·질적 판정 → 증거 기록)는 `mastery-engine.md`(R-13, R-14)가 정한다. 이 스펙은 증거를 입력으로만 본다.
  - **다음에 무엇을 할지 고르는 정책**: `next_objective`는 `mastery-engine.md`. 이 스펙은 큐를 만드는 쪽까지만 다룬다.
  - **교체 가능한 다른 스케줄러**: `RetentionScheduler`는 교체용 인터페이스 정의일 뿐이고 구현은 `SpacedRepetitionScheduler`(별칭 `BaselineRetentionScheduler`) 하나다. 인터페이스에는 `get_initial_state`·`schedule_review`·`retrievability`·`forgetting_risk`·`build_review_queue`·`replay`만 있고, `hydrate`·`review_reason`·`set_desired_retention`·`schedule_next`·`get_due_tasks`는 구현 클래스에만 있다(`scheduler.py:65-110`).
- 외부 의존·선행 계약:
  - 선행 스펙 `mastery-engine.md`: `LearningProgress`·`RepetitionState`·`ReviewTask`·`LearningEvidence` 필드 의미, 증거가 만들어지는 규칙, `due_reviews`.
  - 스케줄러가 `progress`에서 읽는 것은 `error_records`, `learning_evidence`, `repetition_states`, `knowledge_types`, `desired_retention`뿐이고, 쓰는 것은 `repetition_states`의 각 상태와 `review_queue`, `desired_retention`뿐이다(읽은 범위 기준).
  - 시계: 모든 시각은 epoch **초**. `now`를 넘기지 않으면 `time.time()`을 쓴다(`schedule_review`는 `now`가 없으면 **증거의 `timestamp`**).
  - 환경변수 `LEARNING_DEBUG`(R-01).
- 소유 상태·부작용: `RepetitionState`(지식점마다 하나)와 `review_queue`. `hydrate`는 읽기용으로 보이는 `build_review_queue`·`set_desired_retention`에서도 상태를 **바꾼다**(R-06).

### 1.3 인터페이스와 데이터 의미 [필수]

**`RepetitionState`**(C-13):

| 필드 | 의미·제약 |
|---|---|
| `next_review_at` | 다음 복습 예정 시각(초). 필수 |
| `stability` | 안정도(일). 0이면 "아직 채워지지 않은 옛 상태"(R-06) |
| `difficulty` | 0.05~0.95. 지식 유형별 시작값에서 증거로 움직인다(R-09) |
| `retrievability` | 마지막 갱신 때 저장한 기억 확률. 읽을 때는 R-12로 다시 계산하므로 표시용 보조값 |
| `desired_retention` | 이 상태의 목표 기억률(경로값 복사). 0.7~0.99 |
| `interval_index` | 간격표에서 가장 가까운 칸의 번호. **라벨일 뿐** 간격을 정하지 않는다(R-03) |
| `consecutive_correct`, `consecutive_wrong` | 연속 성공·실패 카운터. 각각 2에 도달하면 0으로 돌아간다(R-10) |
| `review_count`, `lapse_count` | 복습 횟수(같은 세션 연습도 +1), 실패 횟수 |
| `last_review_at` | 마지막 증거 시각. 없을 수 있음 |
| `last_scheduled_at` | `next_review_at`을 정한 시각(초기 일정 또는 마지막 **갱신된** 복습). 같은 세션 연습은 이 값을 바꾸지 않는다 |
| `scheduled_after_failure` | 마지막 갱신이 실패였는지 |

**`ReviewTask`**: `id`=`"review_<kp_id>"`, `knowledge_point_id`, `knowledge_type`, `due_at`(=상태의 `next_review_at`), `priority`(정수, 작을수록 먼저), `state`, `forgetting_risk`(0..1, 소수점 4자리 반올림), `reason`(영어 문장), `evidence_source`, `evidence_id`.

**연산**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `SpacedRepetitionScheduler(desired_retention=0.9)` | → 객체 | 범위 밖이면 `ValueError`. 생성 때 `LEARNING_DEBUG`를 읽는다(R-01) |
| `get_initial_state(유형, now?, desired_retention?)` | → 새 `RepetitionState` | R-04 |
| `hydrate(상태, 유형)` | → 같은 객체 | R-06 |
| `schedule_review(상태, 유형, 증거, now?)` | → **같은 객체**(제자리 갱신) | R-07~R-11 |
| `schedule_next(상태, 유형, is_correct)` | → 같은 객체 | 편의 함수. 증거(`review`, quality 1.0/0.0, `timestamp`=지금)를 만들어 `schedule_review` 호출. 호출처 미확인 |
| `retrievability(상태, now?)` | → float 0..1 | R-12 |
| `forgetting_risk(상태, progress, kp_id, now?)` | → float 0..1 | R-13 |
| `review_reason(상태, progress, kp_id, now?, latest_evidence?)` | → 영어 문장 | R-14의 `reason` |
| `build_review_queue(progress, now?)` | → 정렬된 `ReviewTask` 목록(저장은 호출자) | R-14 |
| `get_due_tasks(progress, max_tasks=5)` | → 최대 `max_tasks`개 | `progress.review_queue`(저장된 큐)에서 `due_at <= time.time()`인 과제만 고르고(**필터함**), `review_sort_key(now=그 시각)`로 정렬해 앞에서 `max_tasks`개를 돌려준다. `now` 인자가 없다(C-15). `policy.due_reviews`와 같은 필터·정렬에 자르기가 붙은 것이다. 이 범위에서 호출처를 찾지 못했다 |
| `set_desired_retention(progress, 값, now?)` | → 없음(제자리) | R-16 |
| `replay(유형, 증거목록, now?, desired_retention?, initial_state?)` | → 새 `RepetitionState` | R-17 |
| `review_sort_key(task, now)` | → 정렬 키 | R-15 |

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 시간 단위 | 안정도·간격은 **일** 단위, 시각은 **초**. 환경변수 `LEARNING_DEBUG`가 `1`/`true`/`yes`(소문자 비교)이면 스케줄러가 "1일 = 1초"로 계산한다(객체 생성 때 한 번 읽음). 이때 간격 3 → 3초 | 코드 확인(C-03) |
| R-02 | 목표 기억률 검증 | 유한한 값이고 0.7 이상 0.99 이하여야 하며 아니면 `ValueError`. 기본 0.9 | 코드 확인(C-01) |
| R-03 | 유형별 표 `INTERVAL_SEQUENCES`: memory `[0,1,3,7,14,30,60]`, concept `[3,7,14,30]`, procedure `[3,7,14]`, design `[14,28]`(일) | 표는 **다음 간격을 단계별로 고르는 용도가 아니다.** 쓰이는 곳은 ① 첫 복습 간격(`[0]`) ② 안정도가 없는 옛 상태를 채울 때 `interval_index` 칸의 간격 ③ 계산한 간격에서 가장 가까운 칸 번호(`interval_index`) 표시. 실제 다음 간격은 `안정도 × (−ln 목표 기억률)`이고 표의 최댓값을 넘을 수 있다 | 코드 확인(C-01, C-11, R-11) |
| R-04 | `get_initial_state` | 안정도 = `첫간격 / (−ln 0.9)`(첫간격이 0이면 0.5; **목표 기억률이 아니라 기본 0.9로 계산**). 첫 간격이 0이면(memory) 초기 간격 0, 아니면 `안정도 × (−ln 목표)`. `next_review_at = now + 초기간격×단위`. `difficulty`=유형 시작값(memory 0.3, concept 0.4, procedure 0.5, design 0.6), `retrievability=1`, 카운터 0, `last_review_at=None`, `last_scheduled_at=now`, `scheduled_after_failure=False`. 목표 기억률이 0.9가 아니면 첫 간격이 달라진다(목표가 낮을수록 길어짐) | 코드 확인(C-04) |
| R-05 | 안정도 ↔ 간격 변환 | `안정도 = max(0.5, 간격 / −ln r)`(간격 ≤ 0이면 0.5), `간격 = max(1e-6, max(안정도,1e-6) × −ln r)`. `r`은 `[1e-6, 1−1e-6]`로 자른다 | 코드 확인(C-03) |
| R-06 | `hydrate` | `stability > 0`이면 `difficulty <= 0`일 때만 유형 시작값으로 채운다. 아니면 `interval_index`를 표 범위로 자르고, 그 칸의 간격으로 안정도를 계산(R-05, 상태의 `desired_retention`이 0이면 기본값 0.9를 쓰고 그 값을 상태에도 기록), 난이도를 시작값으로, `retrievability <= 0`이면 1로 채운다. **`next_review_at`은 절대 바꾸지 않는다.** `schedule_review`·`build_review_queue`·`set_desired_retention`이 먼저 호출하므로 이 세 곳은 상태를 변경한다 | 코드 확인(C-04) |
| R-07 | 같은 세션 규칙: 증거 시각이 `last_review_at`과 가까울 때 | 먼저 `moment = max(증거시각, last_review_at)`(과거 증거가 마지막 복습을 되돌리지 못함). `last_review_at`이 있고 `경과일 < min(0.25, 0.5 × 간격(이전 안정도, 기본 0.9))`이면(창은 **기본 목표 0.9로 고정**, 사용자 목표와 무관): ① quality ≥ 0.5면 `review_count+1`, `last_review_at=moment`, `retrievability=1`, `consecutive_wrong=0`만 바꾸고 **return**(안정도·`next_review_at`·`last_scheduled_at`·난이도는 그대로) ② quality < 0.5인데 `scheduled_after_failure`이고 증거가 `partial`이거나 `qualitative`이면 `review_count+1`, `last_review_at=moment`, `retrievability=max(quality, 0.2)`만 바꾸고 return ③ 그 밖의 실패는 아래 R-08~R-11로 진행(연속 실패로 센다). `last_review_at`이 없으면(첫 증거) 이 규칙은 적용되지 않는다. 경과일은 `max(0, moment − last_review_at)/단위`이고 비교는 엄격한 부등호라, 경과일이 창과 같으면(예: 정확히 0.25일 = 21600초) 같은 세션이 **아니라서** R-08~R-11을 그대로 적용한다(T-23) | 코드 확인(C-05) |
| R-08 | quality 결정 `_resolved_quality` | 증거에 `quality`가 있으면 그 값(0..1로 자름). 없으면 correct 1.0 / partial 0.4 / 그 외 0.0에서 `min(0.25, 힌트수×0.08)`과 `min(0.2, (시도수−1)×0.05)`를 빼고 0..1로 자름(**`quality`가 있을 때는 힌트·시도 감점 없음**). `quality < 0.5`가 실패, 0.5 이상이 성공 | 코드 확인(C-10) |
| R-09 | 난이도 갱신(R-07에서 return하지 않은 경우) | `오차 = (1−q) − 난이도`, `놀람 = 이전 기억확률 − q`, `난이도 += 0.12×오차 + 0.08×놀람`, 결과를 `[0.05, 0.95]`로 자름. 이전 기억확률은 갱신 전 상태를 `moment`에서 R-12로 계산 | 코드 확인(C-05) |
| R-10 | 실패(q < 0.5) | `consecutive_wrong+1`, `consecutive_correct=0`, `lapse_count+1`. `안정도 = max(0.05, 이전안정도 × (0.55 − 0.25×이전기억확률) × (1 − 0.25×난이도))`(난이도는 R-09 갱신 후 값). `retrievability = max(q, 0.2)`. 그 다음 `consecutive_wrong >= 2`이면 0으로 되돌린다(2에 오래 머물지 않음) | 코드 확인(C-05) |
| R-11 | 성공(q ≥ 0.5)과 일정 확정 | `consecutive_wrong=0`, `consecutive_correct+1`. `노력 = 1 + (1−이전기억확률)×1.5`, `간격보너스 = 1 + min(경과일/이전안정도, 4)×0.15`(경과일은 `last_review_at`이 없으면 0), `학습성 = 1.35 − 0.6×난이도`, `품질강도 = max(0, (q−0.5)/0.5)`, `성장 = 1 + 품질강도×학습성×노력×간격보너스`, `q ≥ 0.8`이고 `consecutive_correct ≥ 2`이면 성장×1.15. `안정도 = max(0.5, 이전안정도×성장)`, `retrievability=1`, `consecutive_correct`가 2 이상이면 0으로 되돌림. **q = 0.5(예: 서비스의 부분 점수)면 성장 1.0이라 안정도는 그대로**이고 시계만 새로 시작한다. 성공·실패 공통 마무리: `review_count+1`, `last_review_at=last_scheduled_at=moment`, `scheduled_after_failure = (q < 0.5)`, `간격 = _scheduled_interval_days(상태)`(C-03): `review_count == 0`이고 그 유형의 첫 간격이 0(memory)이면 **0일**, 아니면 `안정도 × (−ln 상태의 목표)`이고 `scheduled_after_failure`면 `min(간격, max(간격×0.5, 0.1))`(곧 최소 0.1일 보장하며 절반으로). 첫 분기는 `schedule_review`에서는 일어나지 않고(위에서 `review_count`를 먼저 올린다) R-16 ①에서만 일어난다, `next_review_at = moment + 간격×단위`, `interval_index` = 표에서 간격에 가장 가까운 칸 | 코드 확인(C-05, C-03) |
| R-12 | `retrievability` | `exp(−경과일 / max(안정도,1e-6))`를 0..1로 자른 값. 기준 시각은 `last_review_at`, 없으면 `next_review_at`(미래면 경과 0 → 1.0) | 코드 확인(C-06) |
| R-13 | `forgetting_risk` | `위험 = 1 − 기억확률`. `now > next_review_at`이면 `+ min(연체일/7, 0.25)`. 이 지식점에 `active`/`retrying` 오류 기록이 있으면 `+0.2`. `lapse_count`가 있으면 `+ min(0.1×lapse_count, 0.2)`. 결과를 0..1로 자름 | 코드 확인(C-06, C-02) |
| R-14 | `build_review_queue` | `repetition_states`의 **모든** 지식점에 대해 과제를 만든다(기한 전인 것 포함). 유형은 `knowledge_types[kp]`, 없으면 memory. `hydrate`를 먼저 적용. `priority` = `active`/`retrying` 오류가 있으면 1, 아니면 유형값(memory 2, concept 3, procedure 4, design 5). `due_at=next_review_at`. 지식점별 **마지막으로 추가된** 증거(타임스탬프가 아니라 리스트 순서)의 `source`·`evidence_id`를 복사한다(증거가 없으면 둘 다 빈 문자열). `reason`은 `review_reason(상태, progress, kp, now, 그 증거)`(R-18, C-07)이다. 결과를 `review_sort_key`로 정렬해 반환 | 코드 확인(C-08) |
| R-15 | 정렬과 큐 읽기 | 정렬 키 `(−망각위험, −연체초, priority)` 오름차순: 위험 큰 것, 더 연체된 것, 우선순위 숫자 작은 것 순. `policy.due_reviews(progress, now)`는 **저장된** `review_queue`에서 `due_at <= now`만 골라 같은 키로 `now` 기준 연체를 다시 계산해 정렬한다. 큐의 `forgetting_risk`는 **마지막으로 큐를 만든 시점의 값**이며 읽을 때 갱신되지 않는다(큐는 채점·질적 판정·목표 기억률 변경·재계산 때 다시 만들어진다) | 코드 확인(C-02, C-12, mastery-engine R-13) |
| R-16 | `set_desired_retention(progress, 값)` | 값 검증(R-02). 각 상태마다 `hydrate` 후 `desired_retention`을 새 값으로 바꾸고: ① `last_scheduled_at`이 있으면 안정도는 그대로 두고 R-11의 간격 규칙(실패 직후 절반 포함)으로 `next_review_at = last_scheduled_at + 간격`과 `interval_index`를 다시 계산 — **memory이고 `review_count == 0`인 신규 상태는 간격이 0**이라 목표를 바꿔도 `next_review_at = last_scheduled_at`, `interval_index=0`이다(이 분기가 없으면 `0.5×(−ln 새 목표)`일이 된다, T-21) ② 없고 `last_review_at`이 있으면 `last_review_at`부터의 기존 간격에 `(−ln 새)/(−ln 옛)`을 곱함 ③ 둘 다 없고 `next_review_at`이 지금보다 미래면 지금부터 남은 시간에 같은 비율을 곱함(이미 연체된 것은 그대로). ②③은 `interval_index`를 바꾸지 않는다. 각 상태의 옛 목표도 R-02로 검증되어 범위 밖이면 `ValueError`가 나고, 그때까지 처리한 상태는 이미 바뀐 채로 남는다(T-22). 마지막에 `progress.desired_retention`을 새 값으로 쓰고 큐를 다시 만든다. 증거는 추가되지 않으며 평가로 세지 않는다 | 코드 확인(C-09) |
| R-17 | `replay` | `initial_state`가 있으면 깊은 복사본에서 시작하고, 이때 `desired_retention`도 주면 `ValueError`("initial_state already contains desired_retention"). 없고 증거가 비어 있으면 `get_initial_state(now)`. 증거가 있으면 **첫 증거의 `timestamp`**를 시작 시각으로 초기 상태를 만든 뒤 증거를 **주어진 순서대로** `schedule_review(..., now=증거.timestamp)`로 적용 | 코드 확인(C-14) |
| R-18 | `review_reason` | 문장 조각을 `"; "`로 잇고 마침표로 끝낸다. 조각 순서와 조건: ① 기한: `연체 = now − next_review_at`. 연체가 1단위(일) 이상이면 `due {기간} ago`, 0 이상 1단위 미만이면 `due now`, 음수면 `due in {기간}`(기간은 연체 절댓값을 일로 환산) ② `retrievability NN%`(R-12 값의 정수 퍼센트, 파이썬 `.0%` 서식). `기억확률 + 1e-9 < 상태의 목표`(0이면 0.9)이면 뒤에 ` below NN% target`(목표의 정수 퍼센트)을 붙인다 ③ `lapse_count`가 있으면 `N lapse`(1) / `N lapses`(2 이상). 없고 `consecutive_wrong + (이 지식점에 `active`/`retrying` 오류가 있으면 1)`이 0보다 크면 `recent failure` ④ 증거가 주어지고 그 `source`가 C-01의 `_EVIDENCE_SOURCE_LABELS` 키 5개 중 하나면 `latest {표의 라벨} assessment: {증거 결과}`(그 밖의 출처, 증거 기본값 `mastery_path` 포함은 조각 없음). 기간 문구(`_format_span`): 1/24일 미만 `moments`, 1일 미만 `N hour(s)`(`max(1, round(일×24))`, 1이면 `hour`), 1.5일 미만 `1 day`, 그 이상 `N days`(`round(일)` — 파이썬 `round`라 .5는 짝수 쪽, 2.5일이면 `2 days`) | 코드 확인(C-07, C-01) |

- 불변식: 같은 지식점에 대해 같은 증거 목록을 같은 순서로 `replay`하면 같은 상태가 나온다(`schedule_review`는 `now`가 주어지고 난수·시계를 쓰지 않음. `now=None`일 때만 증거 `timestamp`를 쓰며 그 값도 입력). 안정도는 항상 0.05 이상(실패)·0.5 이상(성공 후), 난이도는 0.05~0.95, 기억확률은 0..1.
- 미결정: 없음.
- 확인 한계: 스케줄러 계산은 실행으로 확인했지만, 증거를 스케줄러에 넘기는 호출 경로(`service.py`의 `_apply_grade`·`_recompute_objective_state`)는 `mastery-engine.md`에서 코드로만 읽었고 실행하지 못했다. 원본 테스트 `learning/tests/test_scheduler.py`는 파일명만 확인하고 열지 않았다. `RetentionScheduler` 인터페이스의 다른 구현은 없다(grep으로 구현 클래스 하나만 확인). T-18~T-26은 코드에서 손으로 도출했고 실행하지 못했다(위 1.6).

### 1.5 필수 코드 참조 [필수]
기준 SHA `a31d826`. 라이선스는 Apache-2.0(overview 1절).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `deeptutor/learning/scheduler.py:16-62` 유형별 표·상수·`validate_desired_retention` | 간격표, 우선순위, 난이도 시작값, 기본·최소·최대 기억률, `_MIN_STABILITY_DAYS=0.5`, `_FAIL_QUALITY=0.5`, `_SAME_SESSION_DAYS=0.25` | R-02, R-03, R-04 |
| C-02 | `deeptutor/learning/scheduler.py:113-124` `_error_kp_ids`·`review_sort_key` | 오류 있는 지식점 판정, 정렬 키 | R-13, R-14, R-15 |
| C-03 | `deeptutor/learning/scheduler.py:127-159` 생성자·단위·변환식·`_scheduled_interval_days` | 일/초 단위, 안정도↔간격, 실패 직후 절반 | R-01, R-05, R-11 |
| C-04 | `deeptutor/learning/scheduler.py:161-218` `hydrate`·`get_initial_state` | 옛 상태 채우기, 초기 상태 | R-04, R-06 |
| C-05 | `deeptutor/learning/scheduler.py:231-333` `schedule_review` | 같은 세션 규칙, 난이도·안정도 갱신, 일정 확정 | R-07, R-09, R-10, R-11 |
| C-06 | `deeptutor/learning/scheduler.py:335-360` `retrievability`·`forgetting_risk` | 기억 확률·위험 식 | R-12, R-13 |
| C-07 | `deeptutor/learning/scheduler.py:362-396,531-539` `review_reason`·`_format_span` | 사유 문장 | R-18 |
| C-08 | `deeptutor/learning/scheduler.py:404-438` `build_review_queue` | 큐 생성 | R-14 |
| C-09 | `deeptutor/learning/scheduler.py:440-479` `set_desired_retention` | 목표 변경 시 재일정 | R-16 |
| C-10 | `deeptutor/learning/scheduler.py:511-528` `_resolved_quality`·`_snap_interval_index` | quality 결정, 칸 번호 | R-08, R-03 |
| C-11 | `deeptutor/learning/scheduler.py:220-229` `schedule_next` | 편의 호출 | (1.3) |
| C-12 | `deeptutor/learning/policy.py:179-187` `due_reviews` | 저장 큐에서 기한 지난 것 정렬 | R-15 |
| C-13 | `deeptutor/learning/models.py:201-237` `RepetitionState`·`ReviewTask` | 필드와 기본값 | 1.3 |
| C-14 | `deeptutor/learning/scheduler.py:481-508` `replay` | 증거 재생 | R-17 |
| C-15 | `deeptutor/learning/scheduler.py:398-403` `get_due_tasks` | 저장 큐의 `due_at <= 지금` 필터, `review_sort_key` 정렬, `max_tasks`개 자르기 | 1.3, R-15 |

### 1.6 수락 사례 [필수]
출처: 구현에서 도출(손 계산)한 뒤 **T-01~T-26 전부를 실행해 확인했다**(2026-10-27; T-01~T-17은 `run_pure.py`, T-18~T-26은 `run_pure2.py`). 원본 `scheduler.py`·`models.py`·`policy.py`를 기준 SHA에서 꺼내 임시 폴더에 복사해 호출했고([`run_pure.py`](../../../artifacts/DeepTutor/mastery-demos/run_pure.py)(출력 [`run_pure.out`](../../../artifacts/DeepTutor/mastery-demos/run_pure.out))), 기대값과 모두 일치했다(T-10은 a·b 두 경우, T-12는 두 경우). 원본 테스트는 열람하지 않았다. 수치는 소수 셋째 자리 근처 허용오차(±0.001일)로 비교한다. `t0`는 임의의 epoch 초(T-23은 정수 초), `D=86400`. 달리 쓰지 않으면 목표 기억률 0.9, `−ln 0.9 ≈ 0.105361`. **T-18~T-26은 2026-10-27 재구현 검증(RESULT.md 7절 6번)의 지적을 반영해 코드에서 손으로 도출했다(계산기로 산술, 원본은 실행하지 않음, "손 계산(실행 없음)").** 수치는 소수 넷째 자리까지 쓰고 같은 허용오차(±0.001)로 비교한다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-04 | `get_initial_state(concept, now=t0)` | `stability ≈ 28.4737`, `difficulty=0.4`, `next_review_at = t0 + 3·D`, `last_scheduled_at=t0`, `last_review_at=None`, 카운터 0 |
| T-02 | R-04 | `get_initial_state(concept, now=t0, desired_retention=0.8)` | `stability ≈ 28.4737`(0.9로 계산), `next_review_at ≈ t0 + 6.354·D`, `desired_retention=0.8` |
| T-03 | R-04 | `get_initial_state(memory, now=t0)` | `stability=0.5`, `difficulty=0.3`, `next_review_at = t0`(즉시 복습 대상) |
| T-04 | R-02 | `validate_desired_retention`에 0.69 / 0.7 / 0.99 / NaN | `ValueError` / 통과 / 통과 / `ValueError` |
| T-05 | R-08 | 증거 `quality=None`, `result="correct"`, `hints_used=2`, `attempt_count=3` / `result="partial"`, 감점 없음 / `quality=0.3` | quality 0.74 (1.0−0.16−0.10) / 0.4(실패 취급) / 0.3(감점 없음, 실패 취급) |
| T-06 | R-09, R-11 | T-01의 상태에서 `now = t0 + 3·D`에 `quality=1.0`(결과 correct, 힌트 0) 증거 | `difficulty = 0.352`, `consecutive_correct=1`, `review_count=1`, `stability ≈ 60.8995`(성장 2.1388), 다음 간격 `≈ 6.416일`, `interval_index=1`(7일 칸), `scheduled_after_failure=False`, `last_review_at=last_scheduled_at=t0+3D` |
| T-07 | R-09, R-10, R-11 | T-01의 상태에서 `now = t0 + 3·D`에 `quality=0.0`(incorrect) 증거 | `difficulty = 0.552`, `lapse_count=1`, `consecutive_wrong=1`, `stability ≈ 7.3633`, `retrievability=0.2`, `scheduled_after_failure=True`, 다음 간격 `≈ 0.388일`(≈ 9.3시간, 절반 규칙 적용), `interval_index=0` |
| T-08 | R-08, R-11 | T-01의 상태에서 `now = t0 + 3·D`에 `quality=0.5`(부분) 증거 | 성공 취급: `difficulty ≈ 0.452`, `stability ≈ 28.4737`(변화 없음), 다음 간격 `≈ 3.0일`, `consecutive_correct=1` |
| T-09 | R-07 | T-06 직후 상태(마지막 복습 `m1`)에서 `m1 + 0.1·D`에 `quality=1.0` 증거 | 같은 세션: `review_count=2`, `last_review_at=m1+0.1D`, `retrievability=1.0`만 바뀌고 `stability`, `next_review_at`, `last_scheduled_at`, `difficulty`, `consecutive_correct`는 T-06 그대로 |
| T-10 | R-07, R-10 | T-06 직후 상태 `P6`(`review_count=1`, `last_review_at=m1`, 안정도 60.8995, 난이도 0.352, `consecutive_correct=1`)에서 (a) `m1 + 0.1·D`에 `quality=0.0`, `result="incorrect"` 증거 (b) `P6`에서 `scheduled_after_failure`만 True로 바꾼 상태(그 밖의 필드는 `P6` 그대로)에 `m1 + 0.1·D`, `quality=0.2`, `result="partial"` 증거 | (a) 같은 세션이지만 단축되지 않음: `lapse_count=1`, `consecutive_wrong=1`, `scheduled_after_failure=True`, `review_count=2`, `retrievability=0.2`, 난이도 ≈ 0.5096, 안정도 ≈ 15.9639(= 60.8995×0.3004×0.8726, 감소), 다음 간격 ≈ 0.8410일(실패 직후 절반 규칙), `last_review_at=last_scheduled_at=m1+0.1D`(수치는 손 계산, 실행 확인은 부등호·플래그만) (b) `review_count=2`, `last_review_at=m1+0.1D`, `retrievability=0.2`만 바뀌고 안정도(60.8995)·`next_review_at`·`last_scheduled_at`·난이도·`lapse_count`·`consecutive_*`는 그대로 |
| T-11 | R-11 | memory 초기 상태(T-03)에서 `now=t0`에 `quality=1.0` 증거 | `difficulty = 0.264`, `stability ≈ 1.096`, 다음 간격 `≈ 0.115일`(≈ 2.8시간, 간격표의 "1일"이 아님), `interval_index=0` |
| T-12 | R-12 | `stability=10`, `last_review_at=T`, `now=T+10·D` | `retrievability ≈ 0.368` (e⁻¹). `last_review_at`이 없고 `next_review_at`이 미래면 1.0 |
| T-13 | R-13 | `stability=10`, `last_review_at=T`, `next_review_at=T+5·D`, `now=T+10·D`, 오류 기록 없음, `lapse_count=0` | 위험 `≈ 0.882` (0.632 + 연체 가산 0.25로 상한). `lapse_count=1`이면 `≈ 0.982`, 거기에 `active` 오류 기록이 있으면 1.0(상한) |
| T-14 | R-14, R-15 | 지식점 A·B 모두 concept 초기 상태에 `next_review_at`만 A=`now−D`, B=`now+5·D`로 바꿈 → `build_review_queue(now)` 후 저장 | 큐 길이 2(B도 포함). 순서 A, B(A의 위험 `≈ 0.1774`, B는 0). `policy.due_reviews(progress, now)`는 `[A]`만 돌려준다 |
| T-15 | R-17 | `replay(concept, [])` / `replay(concept, 증거들, initial_state=S, desired_retention=0.8)` | 초기 상태 / `ValueError` |
| T-16 | R-16 | T-01 상태(`last_scheduled_at=t0`)를 가진 경로에서 `set_desired_retention(0.8)` | `stability` 그대로, `next_review_at ≈ t0 + 6.354·D`, `interval_index=1`, 상태와 경로의 `desired_retention=0.8`, 증거 추가 없음, 큐 재구성 |
| T-17 | R-01 | `LEARNING_DEBUG=1`로 만든 스케줄러, `get_initial_state(concept, now=t0)` | `next_review_at = t0 + 3.0`(초) |
| T-18 | R-18 | (실행 확인) T-01 상태(concept, `next_review_at=t0+3D`, 안정도 28.4737, 목표 0.9, `last_review_at=None`, `lapse_count=0`, `consecutive_wrong=0`)로 오류 기록·증거 없이 `review_reason`을 `now`만 바꿔 호출 | `t0+3.01D` → `due now; retrievability 100%.` / `t0+4D` → `due 1 day ago; retrievability 97%.` / `t0+5.5D`(연체 2.5일) → `due 2 days ago; retrievability 92%.` / `t0+13D` → `due 10 days ago; retrievability 70% below 90% target.` / `t0+2.5D` → `due in 12 hours; retrievability 100%.` / `t0+1.8D`(남은 1.2일) → `due in 1 day; retrievability 100%.` / `t0+2.98D`(남은 0.02일, 1시간 미만) → `due in moments; retrievability 100%.` / `t0` → `due in 3 days; retrievability 100%.` |
| T-19 | R-18 | (실행 확인) T-18의 `now=t0+13D`(기본 문장 `due 10 days ago; retrievability 70% below 90% target`)에서 상태·증거만 바꿈: (a) `lapse_count=1` (b) `lapse_count=2` (c) `lapse_count=0`, `consecutive_wrong=1` (d) `lapse_count=0`, `consecutive_wrong=0`, 이 지식점에 `active` 오류 기록 (e) `lapse_count=1`, 최신 증거 `source="deep_question"`, `result="incorrect"` (f) 최신 증거 `source="mastery_path"` (g) 상태의 `desired_retention`만 0.8 / 0.7로 | 기본 문장 뒤에 (a) `; 1 lapse` (b) `; 2 lapses` (c) `; recent failure` (d) `; recent failure` (e) `; 1 lapse; latest Question Bank assessment: incorrect` (f) 증거 조각 없음 (g) 0.8이면 `retrievability 70% below 80% target`, 0.7이면 `retrievability 70%`(기억확률 0.7038이 목표 0.7 이상이라 `below` 없음). 모든 문장은 마침표로 끝남 |
| T-20 | R-06 | (실행 확인) `hydrate`: (a) concept, `stability=0`, `interval_index=2`, `desired_retention=0.8`, `retrievability=0` (b) concept, `stability=0`, `interval_index=9`, `desired_retention=0` (c) memory, `stability=0`, `interval_index=0` (d) procedure, `stability=5`, `difficulty=0` | (a) `stability = 14/(−ln 0.8) = 62.7399`(표 칸 14일), 난이도 0.4, `retrievability=1.0`, `interval_index=2`, `desired_retention=0.8`, `next_review_at` 그대로 (b) 칸 번호를 3으로 잘라 `stability = 30/(−ln 0.9) = 284.7366`, 난이도 0.4, `desired_retention`이 0.9로 기록됨 (c) `stability=0.5`, 난이도 0.3 (d) 안정도 5 그대로, 난이도만 0.5(유형 시작값), 나머지 필드 그대로 |
| T-21 | R-11, R-16 | (실행 확인) T-03 상태(memory, `next_review_at=t0`, `last_scheduled_at=t0`, `review_count=0`, 안정도 0.5)를 가진 경로에서 `set_desired_retention(0.8, now=t0+D)`. 이어서 T-11 상태(memory, 한 번 복습 후 `review_count=1`, 안정도 1.0958, `last_scheduled_at=t0`)에서 같은 호출 | 앞의 경우 `next_review_at = t0`(간격 0, 분기가 없으면 `t0+0.1116D`), `interval_index=0`, 상태·경로의 목표 0.8, 큐의 이 지식점 `due_at=t0`. 뒤의 경우 분기에 걸리지 않아 `간격 = 1.0958×0.2231 = 0.2445일` → `next_review_at ≈ t0 + 0.2445D`, `interval_index=0` |
| T-22 | R-16 | (실행 확인) 목표 0.9 → 0.8 변경에서 비율 `(−ln 0.8)/(−ln 0.9) = 2.1179`. (a) `last_scheduled_at=None`, `last_review_at=L`, `next_review_at=L+10D`(안정도 20) (b) `last_scheduled_at=None`, `last_review_at=None`, `next_review_at=now+4D` (c) b와 같되 `next_review_at=now−4D`(이미 연체) (d) 상태의 `desired_retention`이 0.5(범위 밖, 안정도 5)인 상태가 포함된 경로 | (a) `next_review_at = L + 21.1790D`(② 분기), `interval_index` 그대로 (b) `next_review_at = now + 8.4716D`(③ 분기), `interval_index` 그대로 (c) `next_review_at` 그대로 (d) `ValueError`(옛 목표 검증), 그 앞에서 처리된 상태는 이미 바뀐 채로 남음. (a)(b)(c) 모두 상태의 `desired_retention`=0.8, 경로의 값=0.8 |
| T-23 | R-07, R-09, R-11 | (실행 확인) T-06 직후 상태 `P6`(마지막 복습 `m1=t0+3D`, 안정도 60.8995, 창 = min(0.25, 6.4164×0.5) = 0.25일, `t0`는 정수 초)에 `quality=1.0`, `result="correct"` 증거를 각각 따로 (a) `m1+21599초` (b) `m1+21600초`(경과일 21600/86400 = 정확히 0.25)에 적용 | (a) 경과일 0.249988 < 0.25라 같은 세션: `review_count=2`, `last_review_at=m1+21599초`, `retrievability=1.0`만 바뀌고 안정도 60.8995·`next_review_at`·`consecutive_correct=1`은 그대로 (b) 같은 세션이 아님: 난이도 ≈ 0.3094, `consecutive_correct` 1→2가 되어 0으로 되돌아감(성장에 ×1.15 포함), 안정도 ≈ 152.1299, `review_count=2`, `last_review_at=last_scheduled_at=m1+21600초`, 다음 간격 ≈ 16.0285일, `interval_index=2`(14일 칸) |
| T-24 | R-10 | (실행 확인) T-07 상태(`now=t0+3D`에 `quality=0.0` 실패 직후: `consecutive_wrong=1`, `lapse_count=1`, 안정도 7.3633, `scheduled_after_failure=True`, `last_review_at=t0+3D`)에서 `t0+13D`(경과 10일, 같은 세션 아님)에 `quality=0.0`, `result="incorrect"` 증거 | `lapse_count=2`, `consecutive_wrong`은 1+1=2가 되어 **0으로 되돌아감**, 난이도 ≈ 0.6263, 안정도 ≈ 3.0164, `retrievability=0.2`, `review_count=2`, `scheduled_after_failure=True`, 다음 간격 ≈ 0.1589일(0.3178의 절반, 최소 0.1일보다 큼), `interval_index=0` |
| T-25 | R-15 | (실행 확인) `progress.review_queue`에 과제 8개: T1~T7은 `due_at=0`(과거), `forgetting_risk`는 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1(연체·`priority`는 모두 같다고 둠), T8은 `due_at=지금+10일`, `forgetting_risk=0.99`. `get_due_tasks(progress)`와 `get_due_tasks(progress, max_tasks=2)` | 앞은 `[T1, T2, T3, T4, T5]`(위험 큰 순, T6·T7은 잘림, T8은 기한 전이라 필터됨), 뒤는 `[T1, T2]`. 저장된 `review_queue`는 바뀌지 않음 |
| T-26 | R-14 | (실행 확인) 지식점 A·B 모두 T-01 상태, `knowledge_types`는 A·B concept, 지식점 C는 T-03 상태이고 `knowledge_types`에 없음. A에 `active` 오류 기록. `learning_evidence`에 A의 증거 둘을 순서대로 추가: e1(`source="deep_question"`, `evidence_id="ev1"`, 결과 correct, `timestamp`가 더 늦음), e2(`source="book"`, `evidence_id="ev2"`, 결과 incorrect, `timestamp`가 더 이르다). `build_review_queue(now=t0+3.01D)` | A: `priority=1`(오류 있음), `evidence_source="book"`, `evidence_id="ev2"`(타임스탬프가 아니라 마지막으로 추가된 것), `reason = "due now; retrievability 100%; recent failure; latest Book assessment: incorrect."`. B: `priority=3`(concept), `evidence_source=""`, `evidence_id=""`, `reason = "due now; retrievability 100%."`. C: `knowledge_types`에 없어 memory로 보아 `priority=2`, `due_at=t0`. 큐 길이 3, `forgetting_risk`는 소수 4자리 반올림 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@a31d826 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-03 (`scheduler.py:130-134`) | 코드 읽음. `os`는 이 환경변수에만 쓰인다(`scheduler.py` 안 `os.` 사용을 읽은 범위에서 확인) |
| R-02 | C-01 (`56-62`), 생성자 `scheduler.py:128-131`, `models.py:655` | 코드 읽음. 경로 모델에도 같은 범위 검증(0.7~0.99)이 있다 |
| R-03 | C-01, C-04, C-10 | 코드 읽음. 간격표가 단계 목록이 아님은 `schedule_review`가 표를 `intervals`로 읽어 `_snap_interval_index`에만 쓰는 점(`scheduler.py:249-250,332`)에서 확인 |
| R-04 | C-04 (`183-218`) | 코드 읽음 |
| R-05 | C-03 (`136-146`) | 코드 읽음 |
| R-06 | C-04 (`161-181`), 호출 지점 `scheduler.py:239,417,457` | 코드 읽음 |
| R-07 | C-05 (`240-284`) | 코드 읽음. 주석의 이슈 번호(#1541, #1781)는 원본 코드 안의 설명이며 원본 이슈 내용은 열람하지 않았다 |
| R-08 | C-10 (`511-523`) | 코드 읽음. 서비스가 `quality`를 명시하는 값은 mastery-engine R-13·R-14 참조(0.6/1.0/0.0/0.5/0.9/0.2) |
| R-09, R-10, R-11 | C-05 (`285-333`), C-03 (`148-159`) | 코드 읽음 |
| R-12, R-13 | C-06 | 코드 읽음 |
| R-14 | C-08, C-02 | 코드 읽음. `get_due_tasks`는 C-15(`scheduler.py:398-403`) |
| R-15 | C-02, C-12 | 코드 읽음. 저장된 위험이 읽을 때 갱신되지 않음은 `due_reviews`가 `task.forgetting_risk`를 그대로 정렬 키로 쓰는 점(`policy.py:179-187`, `scheduler.py:121-124`)에서 확인 |
| R-16 | C-09, C-03 (`_scheduled_interval_days`, `scheduler.py:148-159`) | 코드 읽음. memory 신규 상태 간격 0 분기는 `scheduler.py:151-152`이고 `schedule_review`에서는 `review_count`를 먼저 올린 뒤(326행) 이 함수를 부르므로(330행) R-16에서만 발동한다 |
| R-17 | C-14 | 코드 읽음 |
| R-18 | C-07, C-01 (`scheduler.py:47-53` 라벨 표) | 코드 읽음 |
| T-01~T-17 | 해당 R-ID의 C-ID | **실행 확인**([`run_pure.py`](../../../artifacts/DeepTutor/mastery-demos/run_pure.py)(출력 [`run_pure.out`](../../../artifacts/DeepTutor/mastery-demos/run_pure.out))). 손 계산값 T-06 `3.0 × 2.1388 = 6.4164일`, T-07 `28.4737×0.30×0.862 = 7.3633`, T-11 `0.5×2.1916 = 1.0958`이 실행값과 같았다 |
| T-18~T-26 | 해당 R-ID의 C-ID | **실행 확인**(2026-10-27, [`run_pure2.py`](../../../artifacts/DeepTutor/mastery-demos/run_pure2.py)(출력 [`run_pure2.out`](../../../artifacts/DeepTutor/mastery-demos/run_pure2.out)), 33건 통과). 작업자가 코드를 따라가며 계산기로 구한 값을 원본(기준 SHA 복사본)에서 실행해 모두 확인했다. 비교하지 않은 부분: T-18의 `t0` 사례는 문장 앞부분(`due in 3 days; retrieva`)만, T-19(g)의 목표 0.7 문장은 출력만 하고 기대값과 비교하지 않았고, T-26의 B는 `priority`·`evidence_*`만 비교하고 `reason` 문장은 비교하지 않았으며 C는 큐 포함 여부만 봤다. 작업자의 계산 절차는 다음과 같다: 재구현 검증 지적(RESULT.md 3절 B, 4절, 7절 6번)을 반영해 코드에서 손으로 도출했다. 산술은 계산기(파이썬 산술)로 했고 원본 모듈은 import·실행하지 않았다. 계산 절차의 검산: 같은 식으로 T-01·T-06·T-07·T-08·T-11의 실행값(28.4737, 60.8995, 7.3633, 0.388일, 1.0958)을 재현했다 |

### 2.2 코드 읽는 순서 [선택]
`models.py`의 `RepetitionState` → `scheduler.py` 상수(16-62) → `get_initial_state` → `schedule_review`(R-07 → R-09~R-11) → `retrievability`·`forgetting_risk` → `build_review_queue` → `policy.due_reviews`. 모델은 기본값이 있는 pydantic 클래스이고 스케줄러 계산은 `math`·`time`·`os` 외 의존이 없다(`scheduler.py:3-14`).

### 2.3 비교·재사용 출처 [선택]
- 클래스 독스트링(`scheduler.py:65-67`)이 "지수 망각 모델이며 보정된 FSRS 적합이 아니다"라고 밝힌다. FSRS 공식과 같다는 주장은 하지 않는다.
- 같은 기능이 없는 다른 레포: learnharness는 복습 일정이 없다([overview](../../learnharness/overview.md#스킬화-관점-지도-2026-10-27-추가)).
- 코드를 복사한 적 없음.
- **overview 지도 보정 필요**: `overview.md` 2절 스킬화 지도 7번 행의 "유형별 간격표(일)" 표현은 R-03과 맞지 않는다. 표는 첫 간격과 라벨용이다(이 스펙이 근거).

## 적용 메모 [선택]
확인한 범위에서만 적는다. 우리 목적: Claude Code 스킬 안의 가벼운 학습 상태(파일 하나).

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-14, R-15 | 큐를 저장하지 않고, 읽을 때 `repetition_states`에서 기한 지난 지식점만 계산해 정렬한다 | 저장된 큐의 `forgetting_risk`가 읽는 시점과 어긋난다(R-15). 상태만 저장하면 큐 동기화가 필요 없다 | 큐 생성·정렬 로직은 같고 `review_queue` 필드가 사라진다. T-14의 "큐 길이 2" 대신 "기한 지난 목록 `[A]`"만 검증 |
| 전반 | pydantic 대신 dict + 필드 기본값으로 `RepetitionState`를 표현한다 | 스케줄러가 `progress`에서 읽고 쓰는 필드가 한정되어 있다(1.2). 이 전환 비용은 측정하지 않았다 | 기본값(난이도 0.3, 목표 0.9, 안정도 0 → `hydrate`)을 직접 지켜야 한다 |
| R-01 | `LEARNING_DEBUG`(초 단위 모드)는 테스트용이므로 생략하고 `now`를 인자로만 받아도 된다 | 환경변수는 이 한 곳에서만 쓰인다 | T-17 제외 |
