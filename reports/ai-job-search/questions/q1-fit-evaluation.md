---
sha: "e16acee3abdaae57f8026789338a3c6eebf4608b"
created: 2026-10-21
updated: 2026-10-21
sources:
  - .claude/skills/job-application-assistant/04-job-evaluation.md
  - .claude/skills/job-application-assistant/01-candidate-profile.md
  - .claude/skills/job-application-assistant/02-behavioral-profile.md
  - .claude/commands/apply.md
  - .claude/commands/setup.md
  - tools/rank_state.py
---

# [Q] 프로필과 공고가 주어지면 어떻게 평가하는가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: `코드 확인` (문서·코드를 읽음). 실제 평가 실행은 `미확인` (이 레포의 프로필 파일이 `[YOUR_NAME]` 같은 자리표시자 상태라 돌릴 입력이 없다)

## 1. 질문 및 결론

- **질문**: 기존 프로필과 공고문이 주어졌을 때 적합도를 어떤 방식으로 평가하는가.
- **핵심 결론**: 평가는 **채점표(rubric)를 프롬프트로 주고 LLM이 점수를 매기는 방식**이다. 코드가 하는 일은 4개 점수의 가중합과 구간 이름 붙이기뿐이다 (`tools/rank_state.py`). 이 레포의 차별점은 점수 공식이 아니라 (a) 점수 전에 거르는 두 게이트, (b) 채점표의 기준이 사용자 프로필로 채워지는 구조, (c) 지원 결과로 채점표를 보정하는 경로다.

## 2. 동작 설명

용어: **rubric**은 "점수대별 의미"를 적어 둔 채점표다. **게이트**는 점수를 매기기 전에 통과/불합격을 먼저 가르는 필터다.

### 입력 → 처리 → 출력

| 단계 | 입력 | 처리 | 출력 |
|---|---|---|---|
| 0. 공고 정제 | 공고 원문 | `posting_guard.py`로 숨은 텍스트 제거 | 정제된 공고 (평가 대상이 이것) |
| 1. 게이트 | 공고의 시민권·허가·언어 요구 문구 + 프로필의 `Languages` 표 | 문구를 원문 그대로 읽고 표로 분류 | 불합격이면 **채점·초안 없이 중단**하고 문구를 인용해 보고 |
| 2. 5개 차원 채점 | 공고 + `01-candidate-profile.md` + `02-behavioral-profile.md` + 커리어 목표 | 차원마다 점수대 표에 맞춰 LLM이 판단 | 기술·경력·행동·커리어 점수(0~100), 위치 PASS/FAIL |
| 3. 합산 | 4개 점수 | 가중 평균 | 총점과 구간 이름 |
| 4. 보고 | 위 전부 | 정해진 출력 양식 | 표 + 강점 + 부족한 점 + 권고 + 회사 조사 체크리스트 |

### 게이트 두 개 (점수 전에 실행)

1. **Eligibility Gate** (자격): 공고가 시민권·영주권을 요구하면 **불합격, 채점 안 함**. 보안 허가(clearance) 요구도 대부분 불합격. 공고에 아무 말이 없으면 "침묵은 허가가 아니다"라며 진행하되 **미검증 표시**를 붙이고 회사 자체 사이트를 확인하게 한다. 회사 전체의 "외국인 환영" 문구는 이 직무에 대한 허가가 아니라고 못박는다. 불합격은 조용히 버리지 않고 **인용과 함께 사용자에게 보고**한다 (`04-job-evaluation.md:9-31`).
2. **Language Gate** (언어): 공고가 요구하는 언어가 프로필의 언어 표에 **아예 없으면 불합격**. 있는데 요구 수준이 더 높아 보이면 **FLAG**(점수·초안은 진행하되 사용자에게 격차를 보고). 이 직무의 업무 조건인 언어만 보고, 공고가 쓰인 언어는 보지 않는다 (`04-job-evaluation.md:33-47`).

### 5개 차원

| 차원 | 형식 | 가중치 | 기준 (요지) |
|---|---|---|---|
| Technical Skills | 0~100 | 30% | 80+ 핵심 요건이 주력 기술 / 60~79 대부분 일치, 배울 수 있는 격차 1~2개 / 40~59 상당한 보충 필요 / 0~39 근본 불일치 |
| Experience | 0~100 | 25% | **직함이 아니라 일의 기능과 성격**으로 맞춘다 ("Data Consultant"와 "Data Scientist"가 같을 수 있다) |
| Behavioral/Culture | 0~100 | 15% | 행동 프로필과 문화의 일치. 조사할 위험 신호: 부서 무질서, 개발 없이 유지보수 위주, 리더십과의 궁합 |
| Location | PASS/FAIL | 없음 | 통근 가능 PASS, 이주 필요 FAIL, 잦은 해외 출장 FLAG |
| Career Alignment | 0~100 | 30% | 커리어 목표에 맞는가. **할 수 있는가뿐 아니라 그 일이 에너지를 주는가**(energize/drain)와 생활 조건(안정성, 유연성, 성장)도 본다 |

(`04-job-evaluation.md:49-123`, 가중치 `:237-243`)

### 합산과 구간 (코드)

```python
# tools/rank_state.py:56-57, 287-308 (요지)
WEIGHTS = {"technical": 0.30, "experience": 0.25, "behavioral": 0.15, "career": 0.30}
BANDS = ((75, "Strong Fit"), (60, "Good Fit"), (45, "Moderate Fit"), (30, "Weak Fit"), (0, "Poor Fit"))
total = sum(score[dim] * weight)           # Fraction으로 계산
return int(total + Fraction(1, 2))          # 반올림
```

| 구간 | 의미 (`04-job-evaluation.md:245-250`) |
|---|---|
| Strong 75+ | 꼭 지원, 전부 맞춤화 |
| Good 60~74 | 지원, 격차는 커버레터에서 다룸 |
| Moderate 45~59 | 신중히, 사용자와 상의 |
| Weak 30~44 | 전략적 이유가 없으면 건너뜀 |
| Poor <30 | 건너뜀 |

`Fraction`을 쓰는 이유는 코드 주석에 있다: 이진 부동소수점이면 59.5가 59.49999…가 되어 낮은 구간으로 떨어질 수 있다 (`rank_state.py:296-300`, 코드 확인). 가중합 예시: 기술 80, 경력 70, 행동 60, 커리어 75 → 73 → Good Fit (`artifacts/ai-job-search/tools-demos/output-2026-10-21.txt`, 실행 확인).

### 채점표를 내 상황으로 채우는 방법

`04-job-evaluation.md`에는 `[YOUR_PRIMARY_SKILLS]`, `[YOUR_ENERGIZING_TASKS]`, `[YOUR_CAREER_GOAL_1]` 같은 자리표시자가 있고, `/setup`이 프로필 정보로 채운다 (`setup.md:366` "Update `04-job-evaluation.md`"). 즉 **점수 기준표의 틀은 고정, 기준 내용은 사용자별**이다. 행동 프로필(`02-*.md`)에는 "이런 키워드가 공고에 있으면 강한 일치 / 이런 키워드면 마찰 가능"이라는 **키워드 매핑 칸**이 있다.

### 결과로 보정 (calibration)

지원 후 `/outcome`이 `job_posting.md`와 `outcome.md`를 한 쌍으로 쌓는다. `/setup` 경로 A는 이 쌍을 읽어 면접·합격까지 간 직무 유형은 "강한 적합 신호"로, 같은 유형의 무응답·거절이 2건 이상 반복되면 그 패턴을 `04-job-evaluation.md`의 "Calibration from Past Applications"에 **추가**한다. 기존 채점 틀은 고치지 않는다 (`setup.md:172`, 코드 확인. 실제 효과는 `미확인`).

### 정직 규칙

초안 단계에서 경력 점수가 50 미만이면 "공고에 맞추려면 상당한 재서술이 필요하다"고 먼저 경고한다 (`03-writing-style.md` 규칙 6). 대규모 `/rank`에서는 공고가 아니라 **가져온 본문**으로만 채점하게 한다. 제목만 보고 채점하지 않는다 (`rank.md` Step 2).

## 3. 코드 근거 (Source Evidence)

| 구분 | 파일 경로 | 식별자 | 설명 | 검증 |
|---|---|---|---|---|
| 게이트 | `.claude/skills/job-application-assistant/04-job-evaluation.md:9-47` | Eligibility Gate, Language Gate | 점수 전 필터 | 코드 확인 |
| 채점 기준 | 같은 파일 `:49-123` | Scoring Dimensions | 5개 차원, 점수대 표 | 코드 확인 |
| 출력 양식 | 같은 파일 `:149-183` | Output Format | 표 + 판정 + 체크리스트 | 코드 확인 |
| 합산 | `tools/rank_state.py:287` | `overall_score` | 가중합, 반올림 | 실행 확인 |
| 구간 | `tools/rank_state.py:57, 304` | `BANDS`, `band` | 75/60/45/30 | 실행 확인 |
| 호출 지점 | `.claude/commands/apply.md` Step 1 | "Evaluate fit" | 평가 후 사용자 승인을 받아야 초안으로 진행 | 코드 확인 |

## 4. 검증 과정 및 실행 결과

- 수행: 위 파일을 읽고, `overall_score`·`band`를 직접 호출했다 (가짜 점수 입력).
- 결과: 73 → Good Fit, 손계산 73.0과 일치.
- **구간 안의 숫자는 규칙이 없다** (`코드 확인`): 차원별 기준표는 점수대(80~100, 60~79 등)와 그 의미만 정하고, 그 안에서 몇 점을 줄지는 정하지 않는다. 코드는 점수가 0~100 숫자인지만 검사하고 타당성은 보지 않는다 (`rank_state.py:293-295`). 숫자를 고르는 일은 전부 LLM 판단이다.
- **판단**: LLM이 매기는 각 차원 점수가 같은 입력에서 얼마나 재현되는지는 확인하지 못했다. 채점표가 구체적인 문장형 기준이라 편차를 줄이려는 설계로 읽히지만 이는 `추론`이다.

## 5. 남은 질문 및 추가 조사 사항

- [ ] `/rank`의 `posting-scorer`가 쓰는 "compact rubric"이 `04`에서 어떻게 압축되는지 (`rank.md` Step 1~2)
- [ ] 위치·언어 veto가 `seen_jobs.json`에 저장되는 형식 (`rank_state.py:cmd_apply`)
- [ ] 내 프로필로 실제 평가를 돌려 보면 어떤 출력이 나오는가 (실행하려면 프로필 입력 필요)
