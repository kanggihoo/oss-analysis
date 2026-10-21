---
sha: "e16acee3abdaae57f8026789338a3c6eebf4608b"
created: 2026-10-21
updated: 2026-10-21
---

# ai-job-search Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/MadsLorentzen/ai-job-search` (MIT, `framework_version: 1.0.0`)
- **기준 SHA**: `e16acee` (2026-10-21), 작업트리 Clean. 상세는 `artifacts/ai-job-search/repo-metadata.txt`
- **분석 목적**: 학습 / 설계 참고 (사용자가 목적을 따로 말하지 않아 가정함)
- **한 줄 정의**: 앱이 아니라 **Claude Code 작업공간**이다. 슬래시 명령·스킬·서브에이전트 정의(Markdown)가 흐름을 정하고, 결정적으로 처리해야 할 부분만 Python·Bun(TypeScript) 도구로 뺐다.

| 구성 | 위치 | 규모 (코드 확인) |
|---|---|---|
| 슬래시 명령 | `.claude/commands/*.md` | 12개: setup, apply, rank, interview, outcome, expand, reset, html-report, notion-sync, gmail-sync, add-portal, add-template |
| 스킬 | `.claude/skills/` | `job-application-assistant`(프로필·평가·문서 규칙 `01`~`09`), `job-scraper`(`/scrape`), `upskill` |
| 서브에이전트 | `.claude/agents/*.md` | `posting-fetcher`, `posting-scorer`, `application-reviewer` |
| 포털 검색 CLI | `.agents/skills/*/cli` | 6개: freehire, linkedin(기본 켜짐), jobindex, jobnet, jobbank, jobdanmark(덴마크용, 기본 꺼짐) |
| Python 도구 | `tools/*.py` | 16개 파일. 테스트 `tests/` 67개 파일 |
| 개인 데이터 | `CLAUDE.md`, `01-candidate-profile.md`, `cv/`, `documents/` | `/setup`이 채운다. 템플릿 상태에서는 `[YOUR_NAME]` 같은 자리표시자 |

---

## 2. 프로젝트 개요

구직자가 포크해서 프로필을 채우면, Claude Code가 공고 검색 → 적합도 평가 → CV·커버레터 작성 → 면접 준비 → 결과 기록까지 한 작업공간에서 돕는다. 핵심 설계는 두 가지다.

1. **초안 작성자와 검토자를 나눈다.** 메인 Claude가 초안을 쓰고, 별도 서브에이전트(`application-reviewer`)가 회사를 조사해 수정안을 JSON으로 돌려준다 (`.claude/commands/apply.md` Step 3~4, 코드 확인).
2. **공고를 신뢰하지 않는다.** 공고 본문은 제3자가 쓴 글이라, 숨은 텍스트·지시문 모양의 줄을 코드(`tools/posting_guard.py`)로 먼저 걸러내고, 웹을 만지는 에이전트에서 Edit/Write 도구를 뺀다 (코드 확인).

### 주요 기능

설명 출처는 README와 명령 문서이고, 코드 근거는 `repos/ai-job-search` 기준 SHA에서 읽은 것이다.

| 기능 | 설명 (출처: README·명령 문서) | 코드 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|
| 프로필 구축 `/setup` | `documents/` 폴더 읽기 / CV 붙여넣기 / 인터뷰 3경로로 프로필 문서를 채운다 | `.claude/commands/setup.md` Step 0 (3경로 안내, 공개 포크 경고) | 코드 확인 (문서 읽음, 실행 안 함) |
| 공고 검색 `/scrape` | 설치된 포털 CLI로 검색, 이전에 본 공고·지원한 공고를 제외하고 적합도 high/medium/low로 보여 준다 | `.claude/skills/job-scraper/SKILL.md` Step 1~5, `tools/scrape_state.py:select`(url 또는 company+title로 중복 판정), `tools/job_key.py:make_key`(정규 키) | 코드 확인 + 일부 실행 확인(`make_key`) |
| 포털 CLI | 포털마다 `search`/`detail` 명령. LinkedIn·FreeHire는 인증·의존성 없이 동작 | `.agents/skills/linkedin-search/cli/src/cli.ts`, `…/freehire-search/cli/src/cli.ts`, 각 `SKILL.md`의 `enabled:` | 코드 확인 (CLI 본체는 실행하지 않음. 실제 포털 접속이라 9장 기준 제외) |
| 일괄 점수화 `/rank` | 모인 공고를 병렬 에이전트로 점수화해 순위 목록을 만든다. 위치·언어 불합격은 제외, 마감 7일 이내는 🔥 | `.claude/commands/rank.md` Step 2~3, `tools/rank_state.py:overall_score`(:287), `band`(:304), `WEIGHTS`(:56), `cmd_candidates`(:181), `cmd_sweep`(:235) | 코드 확인 + 실행 확인(점수 73 → Good Fit) |
| 적합도 평가 | 기술 30%·경력 25%·행동 15%·커리어 30% 가중 평균, 위치는 통과/불합격. 시민권·언어는 점수 전에 거르는 게이트 | `.claude/skills/job-application-assistant/04-job-evaluation.md` Eligibility Gate / Language Gate / Weighting, `tools/rank_state.py:WEIGHTS` | 코드 확인 (평가는 LLM이 하고, 합산·구간 매핑만 코드) |
| 지원서 작성 `/apply` | 공고 가져오기 → 평가 → 사용자 확인 → CV·커버레터 초안 → 검토 에이전트 → 수정 → PDF 컴파일·검증 → tracker 기록 | `.claude/commands/apply.md` Step 0~6b, `.claude/agents/application-reviewer.md` | 코드 확인 (문서 읽음, 전체 실행은 안 함) |
| 공고 무결성 검사 | 숨은 HTML, 보이지 않는 유니코드, 지시문 모양 줄, 숨은 URL, 혼합 문자 단어를 찾아 제거·보고 | `tools/posting_guard.py:guard`(:399), `clean_html`(:235), `scan`(:335), `verdict`(:367), `INSTRUCTION_PATTERNS`(:113) | 실행 확인 (아래 3절) |
| 근거 감사 (환각 방지) | 초안의 날짜·직함·수치를 프로필 3종(`01-candidate-profile.md` + `cv/main_example.tex` + `CLAUDE.md`)의 합집합과 대조 | `.claude/commands/apply.md` Step 2 "Grounding Audit", Step 3 "Factual Grounding Audit" | 코드 확인 (프롬프트 규칙이라 지켜지는지는 `추론`) |
| PDF 검증 | 페이지 수(CV 2, 커버레터 1), ATS 텍스트 추출, 레이아웃 구멍·고아 제목, 날짜 ASCII 검사 | `tools/verify_pdf.py:find_non_ascii_date_ranges`(:159), `tools/verify_layout.py:find_orphans`(:296), `apply.md` Step 5 | 코드 확인 (LaTeX 컴파일 안 함) |
| 면접 준비 `/interview` | 지원한 CV·커버레터·공고 기록을 근거로 단계별 준비 자료와 모의 면접 | `.claude/commands/interview.md`, `07-interview-prep.md` | 코드 확인 (문서만) |
| 결과 기록 `/outcome` | 면접·합격·불합격을 tracker와 `documents/applications/<회사>_<직무>/`에 기록, 연락 없는 지원서 후속 메일 초안 | `.claude/commands/outcome.md` | 코드 확인 (문서만) |
| 부가 명령 | `/upskill`(부족 기술 학습 계획), `/expand`, `/html-report`(대시보드), `/notion-sync`, `/gmail-sync`, `/add-portal`, `/add-template`, `/reset` | `.claude/commands/*.md`, `.claude/skills/upskill/SKILL.md` | 코드 확인 (제목·도입부만 읽음) |
| 포크 동기화 | 업스트림 변경 중 내 포크가 안 가져온 것을 보고서로 분류 (병합은 안 함) | `tools/check_upstream_updates.py:main`(:79), `tools/upstream_triage.py` | 코드 확인 (docstring) |
| 공급망·권한 방어 | 허용 권한 확대, `.gitignore` 약화, 설치 스크립트, 에이전트 도구 확대를 CI에서 실패시킨다 | `tools/security_guards.py:check_permissions`(:406), `check_gitignore`(:477), `check_package_manifests`(:504), `check_agent_tool_grants`(:565), `.github/workflows/ci.yml`, `.claude/settings.json` | 코드 확인 |

README의 성과 주장("69건 지원, 첫 면접 20건, 취업 1건")은 제작자 개인의 경험담으로, 코드로 확인할 수 없다. `미확인`.

### 사용 방식

- Claude Code CLI 안에서 `/setup` → `/scrape` → `/apply <URL>` 순서로 쓴다. 별도 서버나 앱은 없다. (README Quick start, 코드 확인으로 구조 일치)
- 다른 에이전트(Codex, Gemini CLI 등)는 `AGENTS.md`에서 시작하고, 포털 CLI는 그대로 쓸 수 있으며 전체 흐름은 커뮤니티 포크가 따로 옮겼다고 README가 적는다. (`AGENTS.md`는 `.claude/`를 단일 원본으로 가리킨다. 코드 확인. 다른 에이전트에서의 동작은 `미확인`)
- 공개 포크에 개인정보가 올라가지 않게 비공개 레포로 쓰라는 경고가 README와 `/setup` Step 0에 있다. (코드 확인)

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 명령·에이전트·도구·상태 파일 관계와 권한 가드 |
| 대표 실행 흐름: `/apply` | [flow.json](./diagrams/flow.json) | [flow.html](./diagrams/flow.html) | URL 입력부터 최종 결과까지 10단계 |

**그림 검증 상태** (세 가지를 구분해 적는다)

- 산출물 검증: 두 그림 모두 `deliver --quality showcase`에서 9개 검사 전부 통과 (실행 확인).
- 브라우저 확인: `visual-check`가 1440×900, 1600×1000, 1920×1080, 2048×1320에서 넘침 없이 통과 (실행 확인). 처음 만든 flow는 4개 레인·카드 때문에 세로가 넘쳐 실패했고, 레인을 3개로 줄이고 카드를 뺀 뒤 통과했다.
- 시각 검토(사람 또는 이미지 검토자가 보는 단계): **하지 않았다.** 글자 겹침·가독성은 눈으로 확인하지 못했다.
- 그림에 넣은 관계는 아래 표의 코드 근거로 확인했다. `파일:심볼`이 없는 화살표는 없다.

### 그림 해설

**읽는 순서**
1. `.claude/commands/apply.md`(흐름 전체)를 먼저 읽는다. 이 레포의 "코드"는 대부분 이 Markdown이다.
2. 흐름이 호출하는 에이전트 정의 `.claude/agents/*.md` 3개 (도구 목록이 핵심).
3. 그 에이전트가 쓰는 `tools/posting_guard.py`와 상태 도구 `scrape_state.py`, `rank_state.py`, `job_key.py`.
4. 마지막으로 `.claude/settings.json`과 `tools/security_guards.py`(권한을 어떻게 묶는지).

**구조도: 모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 슬래시 명령·스킬 | 각 작업의 단계별 지시문. 실행은 Claude Code(메인 모델)가 한다 | 사용자 입력(`$ARGUMENTS`) → 서브에이전트 호출, 도구 실행, 파일 읽기·쓰기 | `.claude/commands/apply.md`, `.claude/skills/job-scraper/SKILL.md` | 코드 확인 |
| 프로필 문서 | 후보자 사실의 원본. 평가·작성 규칙 | 명령이 읽는다. 새로 확인된 사실은 `01-candidate-profile.md`에 되쓴다(`apply.md` 상단 "Standing rule") | `CLAUDE.md`, `.claude/skills/job-application-assistant/01~09-*.md` | 코드 확인 |
| 읽기 전용 서브에이전트 | 웹을 만지는 일(공고 가져오기, 점수화, 회사 조사)을 맡고 쓰기 권한이 없다 | 입력은 프롬프트에 인라인으로 받고 텍스트·JSON으로 돌려준다 | `.claude/agents/posting-fetcher.md`, `posting-scorer.md`, `application-reviewer.md` frontmatter `tools:` (Edit·Write 없음) | 코드 확인 |
| 권한 가드 | Bash 허용 목록·deny 목록, 에이전트 도구 상한을 고정하고 CI에서 확대를 막는다 | `.claude/settings.json` ↔ `tools/security_guards.py`의 허용 목록 | `.claude/settings.json` `permissions.allow/ask/deny`, `tools/security_guards.py:check_permissions` | 코드 확인 (CI 실행은 안 함) |
| 포털 CLI | 포털별 `search`·`detail`을 Bun으로 실행해 JSON·텍스트로 출력 | 질의·URL → 공고 목록·본문 | `.agents/skills/*/cli/src/cli.ts`, `commands/search.ts`, `commands/detail.ts` | 코드 확인 |
| Python 도구 | 결정적 처리: 공고 정제, 중복 제거, 키 생성, 점수 합산, PDF·레이아웃 검사, 브라우저 헤더 재요청 | 파일·stdin → 판정 줄, JSON, 종료 코드 | `tools/posting_guard.py`, `scrape_state.py`, `rank_state.py`, `job_key.py`, `verify_pdf.py`, `verify_layout.py`, `fetch_page.py`, `robots_check.py` | 코드 확인, 3개 실행 확인 |
| 상태 파일 | 본 공고 기록과 지원 기록 | `job_scraper/seen_jobs.json`(점수·상태), `job_search_tracker.csv`(지원 행) | `tools/scrape_state.py:select`, `tools/rank_state.py:cmd_apply`(:311), `apply.md` Step 6b | 코드 확인 |
| CV·커버레터 | LaTeX 원본을 `cv/main_<회사>_<직무>.tex`, `cover_letters/cover_<…>.tex`로 쓰고 PDF로 컴파일 | 초안 → 컴파일 → `verify_*` 검사 | `apply.md` Step 2, Step 5 | 코드 확인 (컴파일 안 함) |
| 채용 포털·웹 | 외부 시스템 | CLI의 HTTP 요청 | `.agents/skills/*/SKILL.md`(LinkedIn은 "Personal use only" 경고) | 코드 확인. 포털 쪽 동작은 `미확인` |

**실행 흐름: `/apply <URL>`**

1. 공고 가져오기 — 입력 `URL` → 처리 `posting-fetcher`가 포털 CLI `detail` → WebFetch → `fetch_page.py`(robots.txt 확인) → WebSearch 순으로 시도 → 출력 본문 (`apply.md` Step 0, `posting-fetcher.md`, 코드 확인)
2. 무결성 검사 — 입력 본문 → 처리 `posting_guard.py`가 숨은 블록 제거, 지시문 모양 줄 찾기 → 출력 정제 텍스트 + 판정 줄 (`posting_guard.py:guard`, 실행 확인)
3. 적합도 평가 — 입력 정제 텍스트 + `01`·`04` 문서 → 처리 출처 호스트 분류(설치된 포털 / 알려진 ATS 도메인 6개 / 미확인), 평가 기준 적용 → 출력 평가 보고 (`apply.md` Step 1, 코드 확인)
4. 사용자 확인 — "초안을 쓸까요?"에 아니오면 중단 (`apply.md` Step 1 끝, 코드 확인)
5. 초안 작성 — 입력 프로필 3종 + 템플릿 → 처리 근거 감사 후 파일 쓰기 → 출력 `.tex` 2개 (`apply.md` Step 2, 코드 확인)
6. 검토 — 입력 초안 전문을 프롬프트에 인라인 → 처리 `application-reviewer`가 회사를 조사하고 비평 → 출력 `old_string/new_string` JSON + 서술 제안 (`apply.md` Step 3, 코드 확인)
7. 수정·PDF 검증 — 처리 Edit으로 수정 적용, `lualatex`/`xelatex` 컴파일, `verify_pdf.py`·`verify_layout.py` 실행, 키워드 커버리지 표 (`apply.md` Step 4~5d, 코드 확인. 실행은 안 함)
8. 최종 결과 — 체크리스트 보고, `job_search_tracker.csv`에 `drafted` 행 추가, 공고를 `documents/applications/…/job_posting.md`에 보관 (`apply.md` Step 6~6b, 코드 확인)

**미확인 영역**
- 실제 `/apply`·`/scrape` 전체 실행(프로필이 템플릿 상태이고 LaTeX·Bun이 필요하며 외부 접속이 필요해 하지 않았다).
- 포털 CLI의 실제 응답과 각 포털의 이용 약관 상태.
- `tests/` 67개의 통과 여부(`pytest`가 설치돼 있지 않아 돌리지 않았다).
- `/setup`, `/interview`, `/outcome`, `/gmail-sync`, `/notion-sync`, `/expand`, `/add-portal`, `/add-template`, `/reset`, `/html-report`, `/upskill`의 단계별 내용(도입부만 읽음).
- 서브에이전트가 프롬프트의 신뢰 경계 규칙을 실제로 지키는지(모델 동작이라 `추론`).

### 실행으로 확인한 것

`artifacts/ai-job-search/tools-demos/run_demo.sh`가 레포의 실제 `tools/*.py`를 그대로 호출한다. 입력은 형식을 보이려는 가짜 예시다. 출력은 `output-2026-10-21.txt`.

| 호출 | 입력 | 결과 |
|---|---|---|
| `posting_guard.py --html --json` | `display:none` 안에 "Ignore previous instructions…"를 넣은 HTML | 숨은 블록 1개 제거, 같은 문장을 instruction-like로 보고, 판정 줄에 ⚠, 정제 텍스트에는 그 문장이 없음. 종료 코드 0(막지 않고 알린다는 설계와 일치) |
| `job_key.make_key("Novo Nordisk A/S", "Data Scientist (Remote/Hybrid)")` | 회사명에 `/`, 직무에 괄호·`/` | `novo-nordisk-a-s_data-scientist-remote-hybrid` (경로 문자가 사라진 키) |
| `rank_state.overall_score / band` | 기술 80, 경력 70, 행동 60, 커리어 75 | 73 → Good Fit (직접 계산한 73.0과 일치) |

---

## 4. 질문과 조사 기록 (Questions)

**분석 초점**: 검색·공고 가져오기는 해외 포털 전제라 관심 밖이다. 자신에게 적용할 수 있는 **평가 → 글쓰기 → 면접** 흐름을 본다.

- [Q1: 프로필과 공고로 어떻게 평가하는가](./questions/q1-fit-evaluation.md) - *LLM이 기준표를 보고 4개 차원을 채점하고, 코드는 가중합만 한다. 점수 전에 자격·언어 게이트가 먼저 거른다. 구간 안의 숫자를 고르는 규칙은 없다.*
- [Q2: 지원서 글을 어떻게 쓰는가](./questions/q2-application-writing.md) - *프로필 사실만 쓰는 근거 감사, 요구사항마다 응답, 별도 검토 에이전트. 내용 규칙은 전부 프롬프트 수준.*
- [Q3: 면접 준비는 어떻게 하는가](./questions/q3-interview-prep.md) - *제출한 지원서 한 건 기준 준비 문서 6섹션과 대화형 모의 면접. 평가의 "부족한 점"이 예상 질문이 된다.*
- [Q4: 프로필은 어떻게 만들어지는가 (`/setup`)](./questions/q4-profile-setup.md) - *서류끼리 어긋나면 멈추고 묻고, 추론은 "검토 전 믿지 말라" 표시, 확인 후에만 쓴다. 면접 답변은 스텁까지만.*
- [Q5: 지원 결과 기록과 보정 (`/outcome`)](./questions/q5-outcome-calibration.md) - *결과만 기록하고, 평가 기준 보정은 `/setup`이 한다. 보정은 점수식을 바꾸는 게 아니라 `04`에 메모를 추가하는 것.*
- [Q6: 부족한 기술과 숨은 역량 (`/upskill`, `/expand`)](./questions/q6-upskill-expand.md) - *`/upskill`은 저장된 `gaps`를 가중 집계해 학습 계획을, `/expand`는 서류·GitHub에서 숨은 역량을 찾는다. `/expand`의 추론이 확인을 거쳐 사실로 승격될 위험이 있다.*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 없음
