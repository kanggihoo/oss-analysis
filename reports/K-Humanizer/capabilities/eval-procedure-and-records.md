---
sha: "916a0e1cd5f4a84de4ec7e485386c7d9941d7e00"
created: 2026-11-10
updated: 2026-11-10
sources:
  - docs/validation-plan.md
  - evals/reports/2026-11-07-business-korean/business-review.md
  - evals/reports/2026-11-07-business-korean/metrics.jsonl
  - evals/reports/2026-11-07-business-korean/runs.jsonl
  - evals/reports/2026-08-25/model-baseline.md
  - skills/k-humanizer/references/evaluation.md
depends:
  - ./eval-fixtures-and-validators.md
status: ready
---

# 평가 절차·실행 기록

> 스킬을 어떤 절차로 평가하고 결과를 어떻게 귀속·보고하는지(비즈니스 forward test, v0 수동 검토)와, 레포가 남긴 두 평가 기록(2026-08-25 v0 기준선, 2026-11-07 비즈니스 개발 점검)의 내용과 한계를 정리한다.

<!-- 이 스펙은 코드가 아니라 절차 문서와 기록 문서가 원본이다. C-ID는 줄 범위. 수치는 보고서에 적힌 값을 옮겼고 원자료로 재계산하지 않았다(일부 fixture 건수만 직접 셈). 검증 수준 `코드 확인` = 문서를 직접 읽음. -->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 평가 대상은 "작문 보조"이지 AI 탐지기 우회가 아니다. 우선 평가 대상은 한국어가 모국어가 아닌 사람이 한국 고객·파트너·사용자를 위해 쓰는 비즈니스 한국어다.
2. 스킬 revision을 정하고 귀속 정보(생성 모델, 스킬 해시, fixture, harness)를 기록한다.
3. 생성기에게 케이스마다 `id`와 `input`만 주고 출력을 받아 원본 그대로 저장한다.
4. 다른 모델이나 사람이 케이스의 `grading`과 루브릭으로 독립 검토한다.
5. 보고서를 쓴다: 귀속, 케이스 수, 모든 하드 페일, 놓친 `keep_unchanged`·`ask_one_question`, 반복 실패 유형. 모델 채점은 "모델 채점"이라 표시한다.
6. 결과는 그 조합(생성 모델·판정·스킬 revision·fixture·harness)에만 적용된다고 적고, 다른 실행과 합치지 않는다.

### 1.2 범위·통합 지점
- 제공: 평가 질문, 입력 모드별 평가 기준, 비즈니스 도메인별 위험, 하드 페일, 증거 상태, forward test 절차와 파일 형식, 보고서 요구, v0 수동 검토 프로토콜과 릴리스 기준, 레포가 남긴 두 기록의 요약.
- 제외: fixture 스키마와 검증 스크립트([eval-fixtures-and-validators](./eval-fixtures-and-validators.md)), 채점 루브릭 본문([evaluation-rubric](./evaluation-rubric.md)). 평가를 실제로 돌리는 harness 코드는 레포에 없다.
- 외부 의존·선행 계약: fixture와 검증기, 루브릭. 생성·판정에는 외부 LLM이 필요하다(보고서는 `claude-sonnet-5-5`가 생성하고 `claude-opus-5-5`가 판정했다고 적는다).
- 소유 상태·부작용: 평가 결과는 `evals/reports/YYYY-MM-DD/`에 파일로 남긴다(`.gitignore`는 `evals/reports/` 아래를 기본 제외하고 `*.md`, `model-baseline.*`만 예외로 두지만 2026-11-07 폴더의 파일들은 이미 `git ls-files`에 추적돼 있다).

### 1.3 인터페이스와 데이터 의미
| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| 스킬 revision | 문자열 `<저장소 기준 커밋 12자>+skill-<해시 12자>` | 해시는 `skills/k-humanizer` 아래 모든 파일을 상대 경로 순으로 정렬해 각 경로, NUL 바이트, 파일 내용, NUL 바이트를 이어 붙인 SHA-256이다. 전체 해시는 보고서에 쓰고 평가한 스냅샷을 커밋으로 보존한다. harness(일괄/케이스별 프로세스, CLI 버전, 격리 플래그)도 기록 |
| 생성 입력 | 케이스마다 `id`, `input`만 | `domain`·`mode`·`grading`은 숨긴다 |
| 원본 출력 파일 | `business-outputs.jsonl`, 한 줄 = `id`, `input`(그대로), `output`(편집 없이 질문 포함), `generator_model`, `skill_revision` | 실패·빈 생성도 버리지 않고 기록 |
| 검토 파일 | `business-review.jsonl` | 케이스마다 `expected_behavior` 충족 여부, 잃은 `must_preserve`, 발생한 `avoid`, 하드 페일 여부, 짧은 노트(5축 점수는 선택), 모든 줄에 모델·판정(또는 사람)·`skill_revision` 반복 |
| 평가 보고서 | `business-review.md` | 귀속, 검토 케이스 수, 모든 하드 페일, 놓친 사례, 반복 실패 유형. 판정의 산문 요약이 아니라 검토 행에서 센다 |
| v0 점수 기록 | `model-baseline.jsonl` | [eval-fixtures-and-validators](./eval-fixtures-and-validators.md) R-05의 형식 |

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 평가 설계 | AI 탐지기 우회가 아니라 의미 보존·한국어 자연스러움·맥락 적합·편집 절제·실용성을 본다. 질문 5개: 의미 보존, 실제 쓸 한국어, 독자·관계·채널·목적 적합, 불필요한 재작성 회피, 보내거나 붙이거나 게시할 수 있는가 | 코드 확인 |
| R-02 | 증거 상태 | v0 골든셋(220건)과 점수 기록은 동결이며 편집·재채점·확장하지 않는다. 비즈니스 보충셋 결과는 자신의 생성 모델·판정·스킬 revision·fixture revision·harness를 인용해야 하고 그 조합에만 적용된다. 개발 세트 점검이며 held-out이 아니다. 이전 실행을 다시 쓰거나 재채점하지 않고 건수를 합치지 않는다 | 코드 확인 |
| R-03 | forward test | 스킬 revision당 fixture 전체를 한 번 제한된 한 번의 패스로 돌린다. 재시도·최선 선택·출력 편집을 하지 않는다. 가능하면 케이스마다 깨끗한 컨텍스트(Claude Code는 `--safe-mode`, `--restricted`)를 쓰고 일괄 실행은 별도 harness로 기록한다 | 코드 확인 |
| R-04 | forward test 단계 | (1) 귀속 기록 (2) 생성기에는 `id`와 `input`만 (3) 원본 출력 저장, 실패·빈 생성도 기록 (4) 독립 검토: 다른 모델이나 생성 지시를 보지 못한 사람, 검토자에게는 `input`·`grading`·출력·루브릭을 준다 (5) 보고: 모델 채점은 사람 검토가 아님을 표시하고 실패 케이스를 합계에 남기며 판정의 "하드 페일 없음" 표시가 의미가 맞았다는 증거가 아니므로 검토에서 발견한 모호성도 보고한다 | 코드 확인 |
| R-05 | 비즈니스 보충셋 목표(달성한 결과가 아님) | 하드 페일 0, 모든 `keep_unchanged`·`ask_one_question`에서 기대 행동 충족, 회귀 케이스가 목소리·기술 용어·기여 경계·명시된 불확실성을 잃지 않음. 2026-11-07 점검은 질문 사례 목표를 충족하지 못했다 | 코드 확인 |
| R-06 | v0 골든셋 릴리스 기준(v1.0) | 모든 도메인 평균 4.2 이상, Meaning Fidelity 4.7 이상, Practical Usefulness 4.2 이상, 골든셋의 치명적 사실 이탈 없음, 조작된 이력서 지표·인과·완료 상태·소유 주장 없음. 비즈니스 보충셋은 이 평균이 아니라 하드 페일과 목표를 쓴다 | 코드 확인 |
| R-07 | v0 수동 검토 프로토콜 | 220건 전부에 모델·버전을 기록해 실행, 출력은 `evals/reports/YYYY-MM-DD/`, 루브릭으로 채점, 반복 실패 상위 10개 기록, 가장 작은 규칙·예시만 고침. 점수 기록 한 줄마다 생성 모델·판정(또는 사람)·skill revision 반복. 독립 모델이 처음 채점하면 `judge_model`에 쓰고 모델 채점으로 취급해 사람 검토로 제시하지 않는다. 요약 전에 검증기로 완결성과 점수 범위를 확인한다 | 코드 확인 |
| R-08 | 공개 데이터셋 후보 | 라이선스·출처를 확인한 뒤에만 쓴다(Hugging Face `coastral/korean-writing-style-instruct`, `jojo0217/korean_safe_conversation`, KatFish/KatFishNet, Open Korean Corpora 같은 코퍼스 조사) | 코드 확인 |
| R-09 | 기록 읽기: 2026-08-25 v0 기준선 | 220건 전부, 생성 `gpt-5.4`, 판정 `claude-opus-5`, revision `814ffb022be6+skill-dfc50447df35`. 전체 평균 4.765(기준 4.200), Meaning 4.800(기준 4.700), Usefulness 4.664(기준 4.200), 치명 실패 0. 도메인 평균은 전부 4.2 초과(가장 낮은 도메인은 문서·보고서 4.47). 실패 라벨 21개(과소 편집 12, 부자연스러운 한국어 4, 맥락 불일치 3, 과편집 1, 일반적 조직 적합 1). 하위 10건을 보존. 판정의 `resume_017` 점수는 루브릭 상한과 모순이어서 보정 시 평균이 4.765에서 4.764로, Meaning이 4.800에서 4.795로 바뀌지만 기준은 통과. 모델 채점이며 사람 검증 벤치마크가 아니다 | 코드 확인 (보고서 값, 재계산 안 함) |
| R-10 | 기록 읽기: 2026-11-07 비즈니스 개발 점검 | 생성 `claude-sonnet-5-5`, 판정 `claude-opus-5-5`. 실행 4회는 합치지 않는다: 초기(30건, 일괄 세션) 기대 행동 충족 26, 전체 재실행(32건) 29, 점수 안 매긴 진단 7건, 케이스별 격리 최종(7건+탐침 1) 6/8. 판정이 표시한 하드 페일은 모두 0이지만 판정 라벨이 의미 정확성을 증명하지 않는다. `keep_unchanged` 충족: 6/7, 7/7, 1/1. `ask_one_question` 충족: 0/2, 2/3, 0/2. 열린 문제 4개: 한 필드가 비면 관련 세부까지 묻거나 질문을 쪼개는 과질문, 영어 요청에 노트·질문이 한국어로 나오는 응답 언어 불일치(명시적으로 영어를 요청한 탐침은 성공), `bk_landing_002`의 문단 흐름, 상태 표현 모호성(`bk_ad_005`의 베타) | 코드 확인 (보고서 값, 재계산 안 함) |

- 불변식: 모델 채점 결과를 사람 검토나 held-out 검증으로 표시하지 않는다(R-04, R-07, R-09, R-10).
- 미결정: 없음.
- 확인 한계: 모든 수치는 보고서에 적힌 값이다. 원자료(`.jsonl`)를 열어 재계산하지 않았고 생성·판정 LLM이나 스킬 해시도 재현하지 않았다. 레포는 비즈니스 출력·검토 파일용 검증기가 없다고 적는다(`validation-plan.md:272`). 평가 harness 코드는 레포에 없고 보고서의 설명이 전부다.

### 1.5 필수 코드 참조
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `docs/validation-plan.md:1-18` | 평가 대상과 질문 5개 | R-01 |
| C-02 | `docs/validation-plan.md:19-128` | 입력 모드, 비즈니스 도메인별 위험, 어투·길이, 하드 페일 | R-01 |
| C-03 | `docs/validation-plan.md:129-221` | 증거 상태와 보충셋 형식 | R-02 |
| C-04 | `docs/validation-plan.md:222-282` | forward test 절차, 출력 형식, 보고서 요구, 목표 | R-03~R-05 |
| C-05 | `docs/validation-plan.md:283-424` | v0 레거시 도메인 10개의 대표 작업과 위험 | 1.2 |
| C-06 | `docs/validation-plan.md:425-514` | 골든셋 형식, 릴리스 기준, 공개 데이터셋 후보, v0 수동 검토 프로토콜 | R-06~R-08 |
| C-07 | `evals/reports/2026-08-25/model-baseline.md:1-146` | v0 기준선의 범위·결과·한계 | R-09 |
| C-08 | `evals/reports/2026-11-07-business-korean/business-review.md:1-265` | 개발 점검 4회의 표, 귀속, 열린 문제, 근원 검토 해소 표 | R-10 |

### 1.6 수락 사례
출처: 구현에서 도출(절차 문서를 적용한 예).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | 새 스킬 revision으로 비즈니스 32건을 돌렸는데 이전 실행(30건) 결과와 합쳐 평균을 내려 함 | 합치지 않는다. 새 보고서는 자신의 revision·fixture·harness를 인용하고 이전 실행은 그대로 둔다 |
| T-02 | R-04 | 판정 모델의 요약은 "비정상 케이스 8건"이라 하는데 검토 행과 fixture에서 세면 7건 | 보고서는 검토 행에서 센 7건을 쓴다(실제 2026-11-07 보고서가 이 불일치를 기록) |
| T-03 | R-04 | 판정이 하드 페일을 한 건도 표시하지 않았는데 검토에서 `베타 버전으로 변경될 수 있습니다`가 의미 모호함을 발견 | 판정의 "없음"을 그대로 쓰지 않고 모호성을 보고서에 적는다(`bk_ad_005`) |
| T-04 | R-03 | 일괄 세션에서 7건을 다시 돌림 | 별도 harness 실행으로 기록하고 케이스별 격리 실행과 구분한다 |
| T-05 | R-07 | 새 v0 점수 기록을 만듦 | 모든 줄에 생성 모델·판정·skill revision을 반복하고 검증기 통과 뒤에 요약한다. 기준 미달 케이스도 보고서에 남긴다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
| R-ID / T-ID | 근거 (repo@916a0e1) | 확인 방법·한계 |
|---|---|---|
| R-01 | `validation-plan.md:1-18` | 직접 읽음 |
| R-02 | `validation-plan.md:129-152` | 직접 읽음 |
| R-03, R-04 | `validation-plan.md:222-282` | 직접 읽음 |
| R-05 | `validation-plan.md:273-282` | 직접 읽음 |
| R-06 | `validation-plan.md:449-469` | 직접 읽음 |
| R-07 | `validation-plan.md:480-514` | 직접 읽음 |
| R-08 | `validation-plan.md:471-478` | 직접 읽음. 외부 데이터셋은 열지 않음 |
| R-09 | `model-baseline.md:8-146` | 전문을 읽음. 수치는 보고서의 값 |
| R-10 | `business-review.md:9-265`, `metrics.jsonl`·`runs.jsonl`(앞부분) | 보고서 전문을 읽고 `metrics.jsonl`·`runs.jsonl`의 앞부분이 표와 일치함을 확인. 원자료 `.jsonl`은 열지 않음 |
| T-01~T-05 | 위 근거의 적용 | 구현에서 도출. T-02는 보고서가 기록한 실제 불일치(`business-review.md`의 "Every figure above…" 문단)에서 가져옴 |
| 문서 차이 | `evaluation.md:219-221`("30건")과 `validation-plan.md:154-157`("32건") | **차이**: 루브릭의 "Test fixtures" 절은 30건이라 적지만 현재 fixture는 32건이다. 30건은 첫 점검 때 fixture다. [evaluation-rubric](./evaluation-rubric.md) 2.1에도 적음 |

### 2.2 코드 읽는 순서
`validation-plan.md:1-18` → 증거 상태(`:129-152`) → forward test(`:222-282`) → 기록 두 개(`model-baseline.md`, `business-review.md`).

## 적용 메모
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| — | 없음 | — | — |
