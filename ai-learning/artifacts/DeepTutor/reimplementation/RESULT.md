# DeepTutor 재구현 검증 결과 (mastery-engine.md + review-scheduler.md)

## 1. 구현 언어·범위
- Python 3.14(표준 라이브러리만, `unittest`). 원본 모듈 import·실행 없음, 원본은 `git show <SHA>:path | sed -n` 으로 읽기만 함(SHA a31d826).
- 파일: `reimpl_learning/models.py`(상태 dataclass, 필드명은 스펙 1.3 그대로), `reimpl_learning/scheduler.py`, `reimpl_learning/engine.py`(policy+mastery+grading+service+메모리 저장소), `test_mastery_engine.py`, `test_review_scheduler.py`, `test_extras.py`.
- 구현한 R-ID: mastery-engine R-01~R-22 전부(단 R-22는 단일 문항만, R-17은 아래 한계). review-scheduler R-01~R-18 전부(+ `schedule_next`, `get_due_tasks`).
- 제외(스펙 1.2): 문항 그룹, `resume`, 시각 과제 *생성/검증*(단 R-04 ①의 `visual_achievements` 판정식은 R-04 때문에 구현), 출처 노출 독립성 판정, 레슨 증거 검증, 문제 수리, 이벤트 발행, 경로 리스. `PendingQuestion.options`는 단순 list(선택지 파싱 없음). SQLite 대신 `MemoryStore`.

## 2. 테스트 결과 (`cd 작업폴더 && python3 -m unittest -v`)
- 총 51개, **통과 51, 실패 0**. (스펙 T-ID 45개 = mastery T-01~T-28 + scheduler T-01~T-17, 내가 R-ID 규칙 문장으로 추가한 6개 = `test_extras.py`)
- 단 수치 허용오차를 스펙 서술(±0.001)보다 넓힌 곳이 있다(아래 3-A). 이것을 빼면 scheduler T-01/T-02/T-08/T-16(stability≈28.475)은 실패한다.
- 원본을 실행하지 않았으므로 "원본과 같은 출력"은 주장하지 않는다. 통과 = 스펙 T-ID 기대값과 일치함만 의미한다.

## 3. 스펙 결함 후보·추측 (R-ID/T-ID, 무엇이 없거나 모호했나, 내가 정한 것)

### A. 기대값이 규칙과 안 맞음 (스펙 수치 오류 후보)
1. scheduler T-01/T-02/T-08/T-16: `stability ≈ 28.475`. R-04대로(3/−ln0.9) 계산하면 **28.47366**. 스펙의 "±0.001일" 허용오차를 적용하면 규칙대로 구현해도 실패(차 0.0013). 28.475는 −ln0.9≈0.105361을 반올림해 나눈 값으로 보인다. 테스트는 ±0.002로 비교.
2. scheduler T-06: `stability ≈ 60.902`, 실제 60.8995(차 0.0025, ±0.001 위반). 위 1번의 파생 오차(28.475×2.1388). 테스트는 ±0.01. T-07(7.364 vs 7.3633), T-11(1.096 vs 1.0958)은 ±0.001 안.
3. scheduler T-10 두 번째 문장("같은 상황에서 partial, quality 0.2, 이미 scheduled_after_failure=True인 상태"): 이 상태를 어떻게 만드는지 입력 수치가 없다. 나는 첫 번째 실패 직후 상태에서 0.01일 뒤 partial/0.2를 넣어 검증했다(추측). 첫 번째 문장의 "안정도 감소"는 수치 없이 부등호만이라 부등호만 검증.

### B. 규칙이 말하지 않았거나 모호 — 내가 정한 것
- scheduler R-16 / R-11(`간격`): **memory 초기 상태(review_count=0, 첫 간격 0)는 간격을 0으로 본다**는 분기(`_scheduled_interval_days`)가 R-11·R-16 문장에 없다. R-04에는 초기 간격 0이 있지만 `set_desired_retention`(R-16)이 "R-11의 간격 규칙"으로 재계산할 때 memory 신규 상태가 0이 되는지 스펙만으로는 알 수 없다. C-03 코드를 읽고 반영함(C-03 필요했음).
- scheduler `get_due_tasks`(1.3): "현재 시각 기준, 정렬 후 자름"만 있다. `due_at<=now` 필터 여부가 불명 — 이름을 따라 **필터함**(추측, 원본 줄 범위는 1.5에 없음). 현재 시각은 `time.time()`.
- scheduler `schedule_next`: 증거의 `timestamp`가 "지금"이라 `now` 없이 호출 시 `time.time()`. 그대로 구현.
- scheduler R-14 `reason`의 `evidence`: 증거가 없는 지식점은 `evidence_source=""`, `evidence_id=""`로 정함(스펙은 "복사"만 말함).
- engine R-13: 스펙은 `now`를 받는다고 하지 않는다. 결정적 비교를 위해 `apply_grade(..., now=None)`, `record_qualitative(..., now=None)`, `record_quiz_attempt(..., now=None)` 등에 **`now` 인자를 내가 추가**(None이면 `time.time()`). `grade_and_record`는 `apply_grade`의 별칭(스펙이 두 이름을 같은 몸통이라 함, 시그니처는 추측).
- engine R-13: `apply_grade`의 `scheduler.build_review_queue`에 `now`를 같이 넘김(원본은 시계). 증거 timestamp·초기 상태 시각·큐 기준이 모두 같은 `now`가 되도록 한 것.
- R-14: `evidence_id`는 "두 id+kp의 결정적 UUID5"라고만 되어 있고 **네임스페이스·문자열 포맷이 스펙에 없다**. C-19 코드를 읽어 `uuid5(NAMESPACE_URL, "deeptutor:qualitative:{session}:{turn}:{kp}").hex` 로 구현(C-19 필요했음). 스펙만으로는 원본과 같은 id를 재현할 수 없다.
- R-14: `record_qualitative_for_path`의 거부 메시지 문구는 스펙에 없음(내 문구). 지식점 없음 → `MasteryInteractionError("Unknown objective ...")`는 R-15·T-28의 문구를 유추.
- R-14 직후 "R-13의 복습 갱신과 같은 절차"라고 했으나 qualitative 쪽은 `now=timestamp`를 `schedule_review`에 넘기고 초기 상태도 `now=timestamp`로 만든다는 차이는 R-14 문장에 없다(C-19에 있음).
- R-07 `next_objective`: `learner_profile`이 `None`이면 probe(스펙은 `teaching_strategy` 기본 probe_first만 말함; C-14로 확인함). `NextStep.reason` 문장 4종(answer_pending/review 대체/teach/probe/below gate/complete)은 스펙에 **문구가 없다**. 코드(C-14)에서 가져옴(C-14 필요했음). `pending_question` 공개 투영은 "정답키·해설 제외"만 알아서 `question_id, knowledge_point_id, module_id, prompt, question_type, options`로 추측.
- R-15: `set_learner_mastery_override`는 "지식점이 없으면 거부" 문구만. 거부 예외 종류=`MasteryInteractionError`로 통일(C-20 코드와 동일). `mastered=false`일 때 "기록이 있을 때만 제거"는 pop 하는 것과 관측상 같아 단순화.
- R-15 defer: "대기 질문·활성 상호작용은 폐기(포기)" — 폐기 조건(지식점 일치)이 단일 문항일 때 `pending.knowledge_point_id==target`임을 그룹 코드에서 유추. `abandoned_question` 반환 키는 코드에서 가져옴(스펙에 반환 형태 없음).
- R-16/R-17: 영수증(receipt) 형태가 스펙에 없다(`result/final/needs_clarification/is_correct/feedback/confidence`는 C-21에만 있음, `replayed`만 R-17에 있음). 내 구현은 `{result, final, is_correct, replayed}` 최소 dict. 
- R-17: (a) `awaiting_input` 상태로 가는 전이 조건이 스펙에 없다(register_question 직후는 `registered`, 채점 요청 없이 `awaiting_input`이 되는 경로 미정의) → 구현에서 `awaiting_input`은 아예 설정하지 않음. (b) 같은 question_id 재채점 시 확인 순서(재생 검사 vs `NoPendingInteractionError`)가 불명 — 채점 후엔 대기 질문이 비므로 **재생 검사를 먼저** 하도록 정함. (c) non-final verdict일 때 `answered` 외에 학습자의 답을 어디 저장하는지 불명 → 저장 안 함. (d) verdict 없이 `grade_interaction`을 부르면(결정론 채점) final로 간주하는지 불명 → final로 간주. (e) `NoPendingInteractionError`/`StaleInteractionError`가 `MasteryInteractionError`의 하위 클래스인지 불명(1.3은 "세 이름"만 나열) → 하위 클래스로 둠. Stale 생성자 인자(제출 id, 현재 id)는 추측.
- R-22: 입력 검증 순서가 모호하다. 스펙은 "새 문항 지식점이 경로에 없으면 거부 / retain이면 기존 반환 / replace는 id 검사" 순서를 번호로 주지 않았다. 코드(C-25) 순서는 ①retain 반환 → ②replace id 검사 → ③지식점 검사. 내 구현도 그 순서(그래서 활성 문항이 있고 retain이면 알 수 없는 kp 문항도 거부되지 않고 기존 것이 반환됨). 스펙 문장만 읽은 구현자는 순서를 바꿀 수 있다.
- R-22: `pending_action` 오류 시 `retain`/`replace` 외에 `pending=None`도 거부(스펙에 없는 입력 검증, 코드 참고).
- R-22/T-25: "활성 상호작용"의 정의가 없다. 구현: status ∈ {registered, awaiting_input, answered} 중 가장 나중에 넣은 것(`Tx.active_interaction`). 원본은 `_interaction_from_legacy_pending`로 옛 집계를 복구하지만 제외.
- 저장소(1.2): `store.mutate(book_id, fn)`의 `fn` 인자 모양(`tx.progress`, `tx.active_interaction()`, `tx.put_interaction()`, `tx.abandon_active_interactions()`)은 스펙에 없어 코드의 사용 형태를 따라 내가 만듦. 실패 시 롤백 = 복사본에서 실행하고 예외 없을 때만 커밋(원자성의 해석).
- R-04 ①: 스펙은 "증명된 시각 과제"만 말하고 정의를 1.4에 쓰지 않음(1.5 C-10 설명에 "독립·verified·힌트 없음·정답"). 실제 코드는 `result=="correct"`, `key_status=="verified"`, `not hints_used`만 보고 증거에 `independent` 필드가 없다 → **C-10 설명의 "독립"은 코드와 불일치**(독립은 `hints_used` 없음으로만 표현).
- R-02/R-19: `LearningProgress.desired_retention` 범위 검증(0.7..0.99)은 생성 시에만 함(pydantic은 대입 검증 안 함과 동일하다고 가정).
- R-18: 합성 증거(시도 기반)의 `source` 기본값 등은 스펙에 없음(기본값 `mastery_path`). `recompute_objective_state`에서 `replay`에 `now`를 안 넘기는 것, 이름은 스펙에 `_recompute_objective_state`만 있어 공개 함수 `recompute_objective_state`로 지음.
- R-12: `record_quiz_attempt`가 `RetryAttempt.timestamp`에 `time.time()`을 쓴다는 점, `error_records.id`가 uuid4 hex라는 점은 스펙에 없음(코드 반영). 비교 시 비결정 필드.
- R-05/R-06(scheduler): `hydrate`가 `stability==0`인 상태를 채울 때 `desired_retention`이 0이면 0.9. 구현만 했고 T-ID로 검증되는 사례 없음(테스트 없음 → 미검증).
- R-18(scheduler) `review_reason`, R-11 `interval_index` 세부, R-03 표 사용: T-ID에 사례가 없는 항목이 많다(아래 4).

### C. 스펙끼리 모순
- 발견한 직접 모순 없음. 다만 mastery R-13이 호출하는 `schedule_review(상태, 유형, 증거)`는 `now=None`이라 증거 timestamp를 쓰고(스케줄러 스펙 1.2 문장과 일치), 반면 R-14는 명시적으로 `now=timestamp`를 넘긴다고 구분해 둔다 — 결과는 같지만 두 스펙이 서로 다른 호출 형태를 가정한다.

## 4. T-ID로 검증되지 않은(= 내가 실행으로 확인 못 한) R-ID
- 구현은 했지만 T-ID 없음: scheduler R-05 직접 변환식, R-06 hydrate(레거시 상태), R-13의 일부 분기는 T-13으로 커버, R-18 `review_reason` 전체(문장 형식), R-14 `priority=1`(오류 있음)·`evidence_source` 복사, `get_due_tasks`, `schedule_next`. mastery R-01(extras 테스트만), R-11, R-15 override/defer(extras), R-18(extras에서 live vs replay 동일 1건), R-19의 `feynman_*`·`explained_objectives`·`stage_failure_*` 정리, R-20(extras), R-21 정규화 부분(공백 제거·중복 제거), `visual_achievements`.
- 이 항목들은 스펙 1.6 사례가 없어서 검증이 약하다 = 스펙 개선 대상.

## 5. 원본 1.5 범위 밖에서 추가로 연 파일
- 없음. 모든 읽기는 두 스펙 1.5의 파일·줄 범위(`git show a31d826:... | sed -n`)였다. `run_pure.py`/`run_pure.out`과 스펙 2부·적용 메모는 열지 않음.
- (참고: `service.py:2896-2955`는 `record_qualitative_in_memory`이고 스펙이 말한 `record_qualitative_for_path` 래퍼는 범위에 없어 R-14 문장으로만 구현. `get_due_tasks`(scheduler.py ~398-403)도 1.5 범위에 없음 → 위 추측. 이 둘이 1.5 누락 후보.)

## 6. 호출 방법 (메인 세션 비교용)
작업 폴더(`.../artifacts/DeepTutor/reimplementation`)를 `sys.path`에 넣고:
```python
from reimpl_learning.models import *            # KnowledgeType, LearningEvidence, RepetitionState, LearningProgress, QuizAttempt, PendingQuestion, ...
from reimpl_learning.scheduler import SpacedRepetitionScheduler, validate_desired_retention
from reimpl_learning.engine import *
```
- 상태: 일반 dataclass(kw_only). `st = RepetitionState(next_review_at=..., stability=..., ...)`, `ev = LearningEvidence(knowledge_point_id="a", timestamp=..., quality=1.0, result="correct")`, `p = LearningProgress(book_id="p")`. 모듈/지식점: `LearningModule(id,name,order,knowledge_points=[KnowledgePoint(id,name,type,module_id,...)])`, `replace_modules(p, modules)`로 `knowledge_types`까지 채움.
- 스케줄러: `s = SpacedRepetitionScheduler(desired_retention=0.9)`;
  `s.get_initial_state(kt, now=None, desired_retention=None)`, `s.schedule_review(state, kt, evidence, now=None)`(제자리, 같은 객체 반환), `s.retrievability(state, now=None)`, `s.forgetting_risk(state, progress, kp_id, now=None)`, `s.build_review_queue(progress, now=None)`(저장은 호출자: `p.review_queue = ...`), `s.replay(kt, evidences, now=None, desired_retention=None, initial_state=None)`, `s.set_desired_retention(progress, value, now=None)`, `s.review_reason(...)`, `s.hydrate(state, kt)`. 시각 epoch 초, `LEARNING_DEBUG=1`이면 객체 생성 시 1일=1초.
- 엔진 순수 함수: `compute_mastery(list)`, `calculate_mastery(progress, kp_id)`, `next_objective(progress, now=None, pending_session_id="")`(→`NextStep` frozen dataclass), `grade_answer(user, expected, question_type="short")`, `classify_error(user)`, `is_mastered/mastery_source/objective_status/display_mastery/learning_stage(progress, kp)`, `due_reviews(progress, now=None)`, `validate_objective_relations(modules, sources=())`.
- 기록 함수(제자리): `apply_grade(progress, *, question_id, knowledge_point_id, module_id="", user_answer, expected_answer, question_type, scheduler=None, verdict=None, assistance_used=False, visual_context=None, now=None)`, `record_qualitative(progress, kp_id, *, passed, evidence="", scheduler=None, session_id="", turn_id="", verdict=None, now=None)`(→bool), `set_learner_mastery_override(progress, kp_id, *, mastered, note="")`, `replace_modules(progress, modules)`, `record_quiz_attempt(progress, attempt, now=None)`.
- 저장소 흐름: `st = MemoryStore(); st.create(progress)`; `st.register_question(book_id, PendingQuestion(...), pending_action="retain"|"replace", replace_question_id="", now=None)`→`(progress, interaction, created)`; `st.grade_interaction(book_id, question_id, user_answer, verdict=None, scheduler=None, now=None)`→영수증 dict; `st.mutate(book_id, lambda tx: defer_objective(tx, kp_id))`.

## 7. 스펙 개선 제안
1. 수치 정정: `28.475`→`28.4737`(또는 허용오차 ±0.003으로 완화), `60.902`→`60.8995`. 허용오차 서술과 실제 기대값이 모순.
2. 1.3에 `evidence_id` 생성식(네임스페이스·문자열 포맷)을 적을 것. 지금은 C-19 없이 재현 불가.
3. 1.3/R-17에 영수증(receipt)의 필드 목록, `awaiting_input` 전이 조건, 확인 순서(재생 검사 vs `NoPending`)를 명시. R-22는 검사 순서를 번호로.
4. R-16/R-11에 "memory 신규 상태(review_count=0)는 간격 0" 예외를 명시.
5. `NextStep.reason` 문구와 `pending_question` 투영 필드를 정하거나 "비교 대상 아님"이라고 선언. `get_due_tasks` 필터 여부와 코드 참조(C-ID) 추가.
6. T-ID 보강: `review_reason` 문장(구간별 `moments`/`N hours`/`1 day`/`N days`, below target), `hydrate` 레거시 채움, `set_desired_retention`의 anchor 없는 두 분기(②③), 같은 세션 규칙의 경계(경과일==창), `consecutive_wrong>=2` 리셋, `record_qualitative` 힌트/verdict 조합, `replace_modules` 의 `feynman_*`, `validate_objective_relations` 공백·중복 정규화·미지 선행 id, defer 대상 자동 결정(R-15) 사례.
7. T-10은 입력 수치를 명시(두 번째 문장의 이전 상태 구성법). R-04 ①에서 시각 과제 증명 조건을 1.4에 직접 쓰고 C-10의 "독립" 서술을 코드와 맞출 것.
8. 저장소 계약(`mutate`의 `fn` 인자 모양)을 1.2에 최소 정의(원자성은 "예외 시 변경 없음").
