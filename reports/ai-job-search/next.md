---
sha: "e16acee3abdaae57f8026789338a3c6eebf4608b"
created: 2026-10-21
updated: 2026-10-21
---

# Next Session Plan: ai-job-search

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] README, `CLAUDE.md`, `AGENTS.md`, 명령·스킬·에이전트 구성 파악
- [x] `/apply` 전체 단계(`apply.md`)와 `/rank`, `/scrape` 단계 목록
- [x] `posting_guard`, `job_key`, `scrape_state.select`, `rank_state`(점수·구간), 권한 가드의 구조
- [x] 도구 3개 실행 확인 (`artifacts/ai-job-search/tools-demos/`)
- [x] archify 그림 2개 (산출물·브라우저 검증 통과, 시각 검토 안 함)
- [x] Q1 평가, Q2 글쓰기, Q3 면접 (규칙 문서 읽음, 실행 안 함)
- [x] Q4 `/setup`, Q5 `/outcome`, Q6 `/upskill`·`/expand` (규칙 문서 전체 읽음, 실행 안 함)

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] `/upskill`의 가중 집계식은 코드가 아니라 `SKILL.md` 글이다. 실제 실행에서 지켜지는지는 미확인
- [ ] `/expand`의 방법 B(추론) 항목을 `01`에 넣으면 근거 감사가 사실로 취급한다는 위험 (q6 3-3). 내 도구에 옮길 때 표시 규칙 필요
- [ ] **사용자 관심 순서**: 평가·글쓰기·면접이 우선이고 검색·공고 가져오기는 제외. 아래 질문 중 포털·가드 관련은 우선순위 낮음
- [ ] `/rank`의 `posting-scorer`용 compact rubric이 `04`에서 어떻게 압축되는가 (`rank.md` Step 1~2)
- [ ] `outcome.md` 기록 형식과 `/setup` 보정(Calibration)이 실제로 무엇을 쓰는가
- [ ] `posting_guard`가 못 잡는 우회는 무엇인가 (`INSTRUCTION_PATTERNS`가 영어 위주인지, 한국어·덴마크어 지시문은?)
- [ ] `/scrape` Step 1~2의 포털 CLI 출력 계약(`date` 필드 등)과 CLI 한 개의 `search`·`detail` 흐름
- [ ] `rank_state.cmd_apply`가 점수·veto를 `seen_jobs.json`에 쓰는 규칙과 `cmd_sweep`의 만료 처리
- [ ] 서브에이전트의 "Edit/Write 없음"이 settings 허용 목록과 어떻게 함께 작동하는가
- [ ] `tests/` 실행 (`pytest` 설치가 필요하므로 사용자에게 먼저 묻기)

---

## 3. 기능 스펙 후보

아직 질문 문서(`questions/`)가 없어 트리거 조건을 채우지 못했다. 가까운 후보는 아래.

| 기능 | 근거 질문 문서 | 상태 |
|---|---|---|
| 프로필·공고 적합도 평가 (게이트 + 5차원 + 구간) | [q1](./questions/q1-fit-evaluation.md) | 후보. 진입점·핵심·실패 처리(게이트 불합격)가 확인됨 → 스펙으로 정리할지 사용자에게 묻기 |
| 근거 감사형 지원서 작성 | [q2](./questions/q2-application-writing.md) | 후보 |
| 제출 서류 기준 면접 준비 | [q3](./questions/q3-interview-prep.md) | 후보 |
| 서류 교차 확인과 확인 후 병합으로 프로필 만들기 | [q4](./questions/q4-profile-setup.md) | 후보. 자소서 도구의 입구 |
| 결과 기록에서 평가 기준 보정까지의 순환 | [q5](./questions/q5-outcome-calibration.md) | 후보 |
| 공고 무결성 게이트 | 없음. `posting_guard.py` 정독 필요 | 낮음 (사용자 관심 밖) |
| 공고 중복 제거 키 | 없음. `job_key.py`, `scrape_state.py` | 후보 |

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `tools/posting_guard.py` | `clean_html`, `scan`, `INSTRUCTION_PATTERNS` | 정제·탐지 규칙 전체와 한계 |
| `tools/rank_state.py` | `cmd_candidates`, `cmd_apply`, `cmd_sweep` | `/rank` 상태 갱신 규칙 |
| `.agents/skills/linkedin-search/cli/src/` | `cli.ts`, `commands/search.ts`, `helpers.ts` | 포털 CLI 한 개를 끝까지 (대표 하나) |
| `.claude/commands/setup.md` | Step 1~4 | 프로필이 파일로 만들어지는 과정 |

---

## 5. 참고 사항 및 후속 제안

- 이 레포의 "코드"는 대부분 Markdown 지시문이라, 동작 근거는 코드보다 프롬프트 문구가 된다. 지시문이 실제로 지켜지는지는 `추론`으로만 남는다.
- 전체 `/apply` 실행에는 Bun, LaTeX, 외부 접속, 채워진 프로필이 필요하다. 하려면 사용자에게 먼저 묻는다(9장).
