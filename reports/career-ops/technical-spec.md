# Career-Ops 기술 스펙: 구조와 동작 방식

작성일: 2026-06-14  
목적: Career-Ops를 평가하거나 개선하기보다, 다른 프로젝트에서 설계/구현 방식을 참고할 수 있도록 구조와 실행 메커니즘을 소스 근거 중심으로 정리한다.

## 0. 근거와 검증 범위

### 사용한 입력

- 기존 wiki 요약: `wiki/projects/career-ops.md`
- Gemini 분석 산출물:
  - `artifacts/career-ops/gemini/1-overview.md`
  - `artifacts/career-ops/gemini/2-agent-mode.md`
  - `artifacts/career-ops/gemini/3-pdf-and-latex-generation-engine.md`
  - `artifacts/career-ops/gemini/4-batch-processing.md`
  - `artifacts/career-ops/gemini/5-application-tracker-and-data-layer.md`
  - `artifacts/career-ops/gemini/7-interview-preparation-and-story-bank.md`
  - `artifacts/career-ops/gemini/8-multi-agent-and-tool-integration.md`
  - `artifacts/career-ops/gemini/0-필요없을거 같은기능.md`
- 실제 checkout: `repos/career-ops`
- 기존 capture 보고서: `reports/career-ops/initial-capture.md`

### 검증 기준 checkout

- HEAD: `57b34c07e01cd106528936398507e1b4552ca295`
- `node doctor.mjs --json` 실제 결과:

```json
{"onboardingNeeded":true,"missing":["cv.md","config/profile.yml","modes/_profile.md","portals.yml"],"warnings":["Playwright MCP tools not detected"]}
```

주의: 현재 local working tree에는 `modes/ar`, `modes/de`, `modes/fr`, `modes/ja`, `modes/pt`, `modes/ru`, `modes/tr`, `modes/ua` 하위 파일 삭제가 `git status --short`에 표시된다. 따라서 이 문서는 현재 worktree에서 직접 읽은 파일과, 필요한 경우 문서/테스트가 확인한 의도된 구조를 구분해 기록한다.

## 1. 프로젝트 목적

Career-Ops는 AI coding CLI를 구직 작업 공간의 “command center”로 사용하게 만드는 로컬 우선 job-search automation 프로젝트다. 프로젝트 설명은 `package.json`에서 “AI-powered job search pipeline — works with any AI coding CLI”로 정의되어 있으며, Claude Code, OpenCode, Gemini, Codex, Qwen을 대상으로 한다. (`repos/career-ops/package.json:2-5`)

핵심 목적은 다음이다.

1. 구직자의 `cv.md`, `config/profile.yml`, `modes/_profile.md`를 바탕으로 채용 공고를 A-F 평가와 Block G posting legitimacy로 분석한다.
2. 평가 결과를 `reports/`에 저장하고, 필요하면 ATS 친화 CV PDF 또는 LaTeX 산출물을 `output/`에 만든다.
3. `data/applications.md`를 canonical tracker로 사용해 지원 상태를 추적한다.
4. `scan.mjs`, provider 플러그인, Playwright/WebSearch 기반 agent workflow로 새 공고를 수집해 `data/pipeline.md`에 넣는다.
5. 단일 평가, scan, batch, dashboard, interview-prep가 모두 동일한 flat-file 데이터 계층을 공유하도록 한다.

이 철학은 README/AGENTS 계층에서 “AI-powered, CLI-agnostic job search automation” 및 “pipeline tracking, offer evaluation, CV generation, portal scanning, batch processing”으로 설명된다. (`repos/career-ops/AGENTS.md:45-70`)

## 2. 핵심 기능

| 기능 영역 | 역할 | 실제 근거 |
|---|---|---|
| 초기 온보딩 | `cv.md`, `config/profile.yml`, `modes/_profile.md`, `portals.yml` 존재 여부를 `doctor.mjs --json`으로 판정 | `repos/career-ops/AGENTS.md:72-152`, `repos/career-ops/doctor.mjs:111-144`, `repos/career-ops/doctor.mjs:253-267` |
| 공고 평가 | URL/JD 입력을 liveness gate → archetype detection → A-F 평가 → Block G legitimacy 순서로 처리 | `repos/career-ops/modes/oferta.md:1-17`, `repos/career-ops/modes/oferta.md:18-155` |
| 자동 파이프라인 | JD 추출, live 여부 확인, 평가, report 저장, PDF/LaTeX 생성, 고득점 지원서 답변 초안, tracker 기록 | `repos/career-ops/modes/auto-pipeline.md:1-87` |
| 공고 스캔 | `portals.yml`을 읽고 local parser/API/agent scraping/WebSearch 경로로 URL 후보를 수집 | `repos/career-ops/modes/scan.md:1-29`, `repos/career-ops/scan.mjs:3-31` |
| provider plugin scanner | `providers/*.mjs`에서 provider를 로드하고 `id`, `detect`, `fetch` 계약으로 처리 | `repos/career-ops/scan.mjs:55-120`, `repos/career-ops/providers/_types.js:75-83` |
| PDF 생성 | AI가 HTML 템플릿을 채운 뒤 `generate-pdf.mjs`가 Playwright Chromium으로 PDF 출력 | `repos/career-ops/modes/pdf.md:1-23`, `repos/career-ops/generate-pdf.mjs:3-13` |
| LaTeX 생성 | `.tex` 구조 검증 후 `tectonic` 또는 `pdflatex`로 PDF 컴파일 | `repos/career-ops/generate-latex.mjs:3-14`, `repos/career-ops/generate-latex.mjs:121-180` |
| tracker 유지 | batch TSV 또는 Gemini 결과 TSV를 `merge-tracker.mjs`가 `data/applications.md`에 병합 | `repos/career-ops/merge-tracker.mjs:3-15`, `repos/career-ops/merge-tracker.mjs:26-69` |
| 데이터 검증 | canonical status, duplicate, report link, score format, pending TSV 등을 검사 | `repos/career-ops/verify-pipeline.mjs:3-15`, `repos/career-ops/verify-pipeline.mjs:119-180` |
| Go dashboard | `data/applications.md`를 읽어 Bubble Tea TUI에서 pipeline/report/progress view 제공 | `repos/career-ops/dashboard/main.go:10-15`, `repos/career-ops/dashboard/main.go:154-197` |
| batch processing | `batch-runner.sh`가 `claude -p` worker들을 스폰하고 state/lock/retry를 관리 | `repos/career-ops/batch/batch-runner.sh:1-12`, `repos/career-ops/batch/batch-runner.sh:42-83` |
| Gemini evaluator | Claude agent 없이 Gemini API로 A-G 평가를 수행하고 report/tracker addition 저장 | `repos/career-ops/gemini-eval.mjs:3-18`, `repos/career-ops/gemini-eval.mjs:200-254`, `repos/career-ops/gemini-eval.mjs:330-379` |
| 자동 업데이트 | User Layer는 보존하고 System Layer만 update/rollback/dismiss 처리 | `repos/career-ops/update-system.mjs:3-16`, `repos/career-ops/update-system.mjs:36-120` |

## 3. 디렉토리 구조

현재 worktree 기준 상위 구조는 다음과 같다.

```text
repos/career-ops/
├── AGENTS.md / CLAUDE.md / GEMINI.md / OPENCODE.md
├── DATA_CONTRACT.md
├── package.json
├── .agents/skills/career-ops/SKILL.md
├── .claude/skills/career-ops/SKILL.md      # canonical skill로 향하는 symlink
├── .opencode/skills/career-ops/SKILL.md    # canonical skill로 향하는 symlink
├── .claude-plugin/plugin.json
├── modes/                                  # 22개 prompt/mode 파일, 현재 worktree 기준
├── providers/                              # scanner provider plugin 11개 파일
├── templates/                              # CV/cover/template/status/portal examples
├── config/profile.example.yml
├── batch/                                  # batch orchestrator/prompt/log/tracker-additions
├── dashboard/                              # Go Bubble Tea TUI
├── data/                                   # applications/pipeline/scan-history 등 user data 위치
├── reports/                                # evaluation report 위치
├── output/                                 # generated PDF 위치
├── jds/                                    # saved JD 위치
├── interview-prep/                         # story-bank, company-specific interview docs
├── writing-samples/                        # style calibration samples
├── examples/                               # example CV/report/profile
├── docs/                                   # architecture/setup/scripts/customization docs
├── scaffolder/                             # `npx @santifer/career-ops init`용 package
└── *.mjs                                   # Node utility scripts
```

Gemini artifact의 구조 요약은 `/modes`, `/batch`, `/data`, `templates/`, `/interview-prep`를 중심축으로 설명한다. (`artifacts/career-ops/gemini/1-overview.md:7-29`) 실제 소스의 `DATA_CONTRACT.md`는 이 구조를 User Layer와 System Layer로 더 엄격히 분리한다. (`repos/career-ops/DATA_CONTRACT.md:5-74`)

### User Layer

업데이트가 자동으로 수정하면 안 되는 개인 데이터/작업 산출물이다.

- `cv.md`
- `config/profile.yml`
- `modes/_profile.md`
- `article-digest.md`
- `interview-prep/story-bank.md`
- `portals.yml`
- `data/applications.md`, `data/pipeline.md`, `data/scan-history.tsv`, `data/follow-ups.md`
- `writing-samples/*`
- `reports/*`, `output/*`, `jds/*`

근거: `repos/career-ops/DATA_CONTRACT.md:5-25`

### System Layer

업데이트 가능한 prompt, scripts, templates, dashboard, docs 계층이다.

- `modes/_shared.md`, `modes/oferta.md`, `modes/pdf.md`, `modes/scan.md`, 기타 mode files
- `AGENTS.md`, `CLAUDE.md`, `OPENCODE.md`, `GEMINI.md`
- `*.mjs`
- `batch/*`
- `dashboard/*`
- `templates/*`, `fonts/*`
- `.agents/`, `.claude/skills/`, `.opencode/skills/`, `.claude-plugin/`
- `docs/*`, `VERSION`, `DATA_CONTRACT.md`

근거: `repos/career-ops/DATA_CONTRACT.md:27-68`, `repos/career-ops/update-system.mjs:36-120`

## 4. 주요 컴포넌트

### 4.1 Agent instruction layer

- `AGENTS.md`: canonical agent instruction. data contract, update check, onboarding, main files, personalization, ethical use 등을 정의한다.
- `CLAUDE.md`, `GEMINI.md`, `OPENCODE.md`: wrapper/overlay. 현재 `GEMINI.md`와 `OPENCODE.md`는 `AGENTS.md`를 import하는 얇은 파일이다. (`repos/career-ops/GEMINI.md:1-2`, `repos/career-ops/OPENCODE.md:1-2`)
- `.agents/skills/career-ops/SKILL.md`: open agent skill standard 기반 command router. `.claude/skills/...`와 `.opencode/skills/...`는 이 canonical skill로 향하는 symlink로 확인되었다.

### 4.2 Mode prompt layer

`modes/`는 실행 코드가 아니라 AI agent가 읽는 prompt/program 계층이다. 현재 worktree 기준 22개 mode file이 있다.

- `_shared.md`: sources of truth, scoring, Block G, archetype detection, global rules, tool rules.
- `_profile.template.md`: user override 파일의 템플릿.
- `oferta.md`: 단일 공고 A-G 평가.
- `auto-pipeline.md`: JD/URL 입력 시 전체 pipeline.
- `scan.md`: portal discovery agent workflow.
- `pdf.md`, `latex.md`, `cover.md`: 문서 생성.
- `pipeline.md`, `batch.md`, `tracker.md`: 큐/배치/tracker 처리.
- `contacto.md`, `apply.md`, `followup.md`: outreach/application form/follow-up.
- `deep.md`, `interview-prep.md`, `interview.md`: company/interview intelligence.
- `training.md`, `project.md`, `patterns.md`: 성장/의사결정/패턴 분석.
- `update.md`: system update flow.

핵심 공통 규칙은 `_shared.md`가 “cv.md, article-digest.md, config/profile.yml, modes/_profile.md를 항상 읽고, _profile.md가 default를 override한다”고 정의한다. (`repos/career-ops/modes/_shared.md:11-24`)

### 4.3 Node utility scripts

`package.json`의 scripts가 실제 CLI surface를 제공한다. (`repos/career-ops/package.json:6-24`)

- setup/health: `doctor.mjs`, `cv-sync-check.mjs`
- pipeline integrity: `verify-pipeline.mjs`, `normalize-statuses.mjs`, `dedup-tracker.mjs`, `merge-tracker.mjs`
- document generation: `generate-pdf.mjs`, `generate-latex.mjs`, `generate-cover-letter.mjs`
- discovery/liveness: `scan.mjs`, `scan-ats-full.mjs`, `check-liveness.mjs`, `liveness-core.mjs`, `liveness-browser.mjs`
- analytics: `analyze-patterns.mjs`, `followup-cadence.mjs`, `tracker.mjs`
- alternative LLM path: `gemini-eval.mjs`
- update: `update-system.mjs`

### 4.4 Scanner provider plugins

`scan.mjs`는 `providers/*.mjs`를 동적으로 로드한다. `_`로 시작하는 파일은 helper라 provider로 로드하지 않는다. (`repos/career-ops/scan.mjs:55-84`) provider resolution 순서는 다음이다.

1. `tracked_companies` entry의 explicit `provider:`가 있으면 우선.
2. `parser.command`/`parser.script`가 있으면 `local-parser`.
3. 각 provider의 `detect(entry)`를 순서대로 실행.

근거: `repos/career-ops/scan.mjs:87-120`

Provider runtime contract는 `id`, optional `detect(entry)`, required `fetch(entry, ctx)`다. (`repos/career-ops/providers/_types.js:75-83`)

### 4.5 Document generation engine

HTML/PDF 경로:

1. `modes/pdf.md`가 JD 기반 keyword extraction, company location 기반 paper size, role archetype 기반 framing, HTML template 채우기, `node generate-pdf.mjs` 실행까지 prompt-level 절차를 정의한다. (`repos/career-ops/modes/pdf.md:1-23`)
2. `generate-pdf.mjs`는 Playwright Chromium을 사용해 HTML을 PDF로 렌더링한다. (`repos/career-ops/generate-pdf.mjs:3-13`)
3. `normalizeTextForATS()`는 em dash, smart quote, zero-width, nbsp, arrow, bullet, currency glyph 등을 body text 기준으로 정리한다. (`repos/career-ops/generate-pdf.mjs:24-89`)

LaTeX 경로:

1. `generate-latex.mjs`가 `.tex` input을 읽고 required sections/commands, `\begin{document}`, unresolved placeholders, `\pdfgentounicode=1`를 검사한다. (`repos/career-ops/generate-latex.mjs:21-119`)
2. `tectonic`이 있으면 우선 사용하고 없으면 `pdflatex`로 fallback한다. (`repos/career-ops/generate-latex.mjs:121-180`)
3. compile 후 PDF를 target path로 복사하고 aux/log 파일을 정리한다. (`repos/career-ops/generate-latex.mjs:200-232`)

### 4.6 Tracker/data integrity layer

`data/applications.md`는 flat-file DB 역할을 한다. Gemini artifact도 이 파일을 SSOT로 설명한다. (`artifacts/career-ops/gemini/5-application-tracker-and-data-layer.md:4-24`)

- canonical table: `#`, `Date`, `Company`, `Role`, `Score`, `Status`, `PDF`, `Report`, `Notes`
- canonical states는 `templates/states.yml`에 정의된다: `evaluated`, `applied`, `responded`, `interview`, `offer`, `rejected`, `discarded`, `skip`. (`repos/career-ops/templates/states.yml:1-56`)
- `merge-tracker.mjs`는 8/9-column TSV와 markdown table row를 처리하고 report link normalization, tracker lock, additions dir, data dir를 다룬다. (`repos/career-ops/merge-tracker.mjs:3-69`)
- `verify-pipeline.mjs`는 canonical status, duplicate, report links, score format, row format, pending TSV, stale reservation sentinels를 검사한다. (`repos/career-ops/verify-pipeline.mjs:119-262`)

### 4.7 Dashboard TUI

`dashboard/`는 Go Bubble Tea 기반 TUI다.

- `dashboard/main.go`는 Bubble Tea, data/model/theme/screens 패키지를 import한다. (`repos/career-ops/dashboard/main.go:10-15`)
- `ParseApplications`, `ComputeMetrics`, `ComputeProgressMetrics`로 tracker를 읽고 pipeline/progress/report view 상태를 구성한다. (`repos/career-ops/dashboard/main.go:36-41`, `repos/career-ops/dashboard/main.go:154-197`)
- report open, status update, refresh, progress view, URL open 등을 event-driven update로 처리한다. (`repos/career-ops/dashboard/main.go:47-140`)
- data parser는 `{path}/applications.md`와 `{path}/data/applications.md`를 모두 시도한다. (`repos/career-ops/dashboard/internal/data/career.go:48-60`)

## 5. 데이터 흐름

전체 데이터 흐름은 다음처럼 요약할 수 있다.

```text
User input / scan target
  ├─ pasted JD text
  ├─ URL
  ├─ portals.yml scan config
  └─ batch-input.tsv
        ↓
JD acquisition / liveness
  ├─ Playwright browser snapshot
  ├─ WebFetch fallback
  ├─ WebSearch fallback
  ├─ scan.mjs provider APIs/local parser
  └─ liveness-core classifier
        ↓
Prompt evaluation context
  ├─ cv.md
  ├─ config/profile.yml
  ├─ modes/_profile.md
  ├─ article-digest.md
  ├─ modes/_shared.md
  └─ selected mode prompt
        ↓
Evaluation output
  ├─ reports/{###}-{company-slug}-{YYYY-MM-DD}.md
  ├─ output/cv-{candidate}-{company}-{YYYY-MM-DD}.pdf
  ├─ batch/tracker-additions/*.tsv
  └─ interview-prep/story-bank.md / company prep docs
        ↓
Data integrity and UI
  ├─ merge-tracker.mjs → data/applications.md
  ├─ verify-pipeline.mjs / normalize / dedup
  ├─ dashboard/main.go TUI
  └─ analyze-patterns/followup/tracker derived outputs
```

`scan.mjs`의 코드 기준 흐름은 “load providers → read portals.yml → resolve targets → load dedup sets → fetch provider jobs → title/location/salary filter → seen URL/company-role dedup → optional Playwright liveness verification → append pipeline/history”다. (`repos/career-ops/scan.mjs:619-720`, `repos/career-ops/scan.mjs:720-840`)

## 6. Workflow 구조

### 6.1 First-run onboarding workflow

1. 첫 세션에서 `node update-system.mjs check`를 조용히 실행한다. (`repos/career-ops/AGENTS.md:25-43`)
2. `node doctor.mjs --json`으로 cold-start state를 확인한다. (`repos/career-ops/AGENTS.md:72-83`)
3. `modes/_profile.md`가 없으면 template에서 복사한다.
4. `cv.md`, `config/profile.yml`, `portals.yml`이 없으면 onboarding mode로 진입한다.
5. `data/applications.md`가 없으면 canonical table header를 만든다. (`repos/career-ops/AGENTS.md:114-121`)
6. 기본 setup 후 추가 context를 받아 `config/profile.yml`, `modes/_profile.md`, `article-digest.md`에 축적한다. (`repos/career-ops/AGENTS.md:123-138`)

### 6.2 Single JD / URL evaluation workflow

1. 사용자가 JD text 또는 URL을 입력한다.
2. skill router가 subcommand가 아닌 JD/URL 입력으로 판단하면 `auto-pipeline`으로 보낸다. (`repos/career-ops/.agents/skills/career-ops/SKILL.md:17-43`)
3. URL이면 Playwright → WebFetch → WebSearch 순서로 JD를 추출한다. (`repos/career-ops/modes/auto-pipeline.md:5-18`)
4. liveness gate를 통과하지 못하면 평가/report/PDF를 중단한다. (`repos/career-ops/modes/auto-pipeline.md:19-30`)
5. `oferta.md`의 A-G 평가를 실행한다. (`repos/career-ops/modes/auto-pipeline.md:31-34`)
6. `reports/{###}-{company-slug}-{YYYY-MM-DD}.md` 저장, `Legitimacy` header 포함. (`repos/career-ops/modes/auto-pipeline.md:35-39`)
7. `config/profile.yml`의 `cv.output_format`에 따라 `modes/latex.md` 또는 `modes/pdf.md` 경로로 이동한다. (`repos/career-ops/modes/auto-pipeline.md:40-46`)
8. score가 4.5 이상이면 application form 답변 초안을 report에 추가한다. (`repos/career-ops/modes/auto-pipeline.md:47-82`)
9. tracker에 기록한다. (`repos/career-ops/modes/auto-pipeline.md:83-87`)

### 6.3 Scan / pipeline workflow

1. `portals.yml`에서 `tracked_companies`, `job_boards`, `title_filter`, `location_filter`, `salary_filter`를 읽는다. (`repos/career-ops/scan.mjs:626-645`)
2. provider를 resolve한다. local parser가 있으면 먼저 시도하고 실패하면 API provider로 fallback할 수 있다. (`repos/career-ops/scan.mjs:720-739`)
3. title/location/salary filter, seen URL/company-role dedup를 적용한다. (`repos/career-ops/scan.mjs:745-769`)
4. `--verify`면 Playwright로 liveness를 순차 확인한다. 프로젝트 규칙상 Playwright는 병렬 실행하지 않는다. (`repos/career-ops/scan.mjs:524-527`, `repos/career-ops/scan.mjs:788-806`)
5. live offer만 `data/pipeline.md`와 `data/scan-history.tsv`에 기록하고, expired/no-apply/invalid는 scan-history에 skip 상태로 기록한다. (`repos/career-ops/scan.mjs:808-840`)
6. `modes/pipeline.md`가 `data/pipeline.md`의 pending entry를 읽어 `auto-pipeline`으로 넘기는 구조다. Gemini artifact도 `[ ]`, `[x]`, `[!]` 큐 상태 모델로 설명한다. (`artifacts/career-ops/gemini/2-agent-mode.md:60-68`)

### 6.4 Batch processing workflow

Gemini artifact는 batch를 orchestrator/worker 구조로 설명한다. (`artifacts/career-ops/gemini/4-batch-processing.md:9-48`) 실제 `batch-runner.sh`는 현재 주석상 Claude Code-specific이다.

1. `batch/batch-input.tsv`를 입력 큐로 사용한다.
2. `batch-runner.pid`로 중복 실행을 막는다. (`repos/career-ops/batch/batch-runner.sh:112-136`)
3. `batch-state.tsv`를 초기화/관리한다. (`repos/career-ops/batch/batch-runner.sh:158-163`)
4. `.batch-state.lock` 디렉토리 기반 state lock으로 concurrent write를 방지한다. (`repos/career-ops/batch/batch-runner.sh:165-200`)
5. `claude -p` worker에 `batch-prompt.md`와 placeholders를 주입해 평가/report/PDF/tracker TSV를 생성한다. (`repos/career-ops/batch/batch-runner.sh:1-12`, `repos/career-ops/batch/batch-prompt.md:46-64`)
6. 완료 후 `merge-tracker.mjs`, `verify-pipeline.mjs`로 data layer를 정리한다.

## 7. Agent 구조

Career-Ops의 agent 구조는 “코드가 직접 모든 판단을 수행”하는 형태가 아니라 “AI coding CLI가 markdown instruction을 읽고 tool/code scripts를 호출”하는 형태다.

```text
User
  ↓ slash command or pasted JD
Skill router (.agents/skills/career-ops/SKILL.md)
  ↓ mode routing
Context loader
  ├─ modes/_shared.md
  ├─ modes/{mode}.md
  ├─ cv.md
  ├─ config/profile.yml
  ├─ modes/_profile.md
  └─ optional article/writing/report data
  ↓
Main agent or delegated subagent
  ├─ scan/apply/pipeline(3+ URLs): subagent 권장/지정
  ├─ oferta/pdf/etc.: main mode execution
  └─ batch: headless CLI worker process
  ↓
Scripts / browser / API / files
```

`SKILL.md`는 `scan`, `apply`, `pipeline(3+ URLs)`를 subagent로 위임하라고 명시한다. (`repos/career-ops/.agents/skills/career-ops/SKILL.md:96-105`) `modes/scan.md`도 main context 소모를 피하기 위해 subagent 실행을 권장한다. (`repos/career-ops/modes/scan.md:9-19`)

## 8. Skill 구조

Canonical skill file은 다음 frontmatter와 routing table을 가진다.

- name: `career-ops`
- user invocable: true
- argument hint: `scan | deep | pdf | latex | cover | oferta | ofertas | apply | batch | tracker | pipeline | contacto | training | project | interview-prep | interview | patterns | followup | update`
- no args: discovery menu
- JD text or URL: `auto-pipeline`
- explicit subcommand: corresponding mode

근거: `repos/career-ops/.agents/skills/career-ops/SKILL.md:1-43`

Context loading 정책도 skill에 있다.

- `_shared.md + mode file`이 필요한 modes: `auto-pipeline`, `oferta`, `ofertas`, `pdf`, `contacto`, `apply`, `pipeline`, `scan`, `batch`
- standalone mode file만 필요한 modes: `tracker`, `deep`, `interview-prep`, `interview`, `latex`, `training`, `project`, `patterns`, `followup`, `cover`
- delegated modes: `scan`, `apply`, `pipeline(3+ URLs)`

근거: `repos/career-ops/.agents/skills/career-ops/SKILL.md:82-107`

Symlink 구조는 terminal inspection으로 다음처럼 확인되었다.

```text
.claude/skills/career-ops/SKILL.md -> ../../../.agents/skills/career-ops/SKILL.md
.opencode/skills/career-ops/SKILL.md -> ../../../.agents/skills/career-ops/SKILL.md
.agents/skills/career-ops/SKILL.md   # canonical real file
```

## 9. Prompt 구조

Prompt 계층은 3층으로 볼 수 있다.

### 9.1 Global/system prompt: `_shared.md`

- 항상 읽어야 하는 source of truth 정의: `cv.md`, `article-digest.md`, `config/profile.yml`, `modes/_profile.md`, `writing-samples/`. (`repos/career-ops/modes/_shared.md:11-24`)
- scoring system: 6 blocks A-F와 1-5 global score. (`repos/career-ops/modes/_shared.md:27-45`)
- Block G posting legitimacy: High Confidence / Proceed with Caution / Suspicious, score와 분리된 qualitative assessment. (`repos/career-ops/modes/_shared.md:46-73`)
- archetype detection: AI Platform/LLMOps, Agentic/Automation, Technical AI PM, AI Solutions Architect, AI Forward Deployed, AI Transformation. (`repos/career-ops/modes/_shared.md:74-88`)
- global never/always/tool rules. (`repos/career-ops/modes/_shared.md:89-130`)

### 9.2 User override prompt: `_profile.md`

`modes/_profile.md`는 user layer이며 업데이트로 덮어쓰면 안 된다. 사용자 archetype, narrative, negotiation script, proof points, location policy, comp target 등이 여기에 들어간다. `AGENTS.md`와 `DATA_CONTRACT.md` 모두 사용자별 customization을 `_profile.md` 또는 `config/profile.yml`에 넣고 `_shared.md`에 넣지 말라고 한다. (`repos/career-ops/AGENTS.md:11-23`, `repos/career-ops/DATA_CONTRACT.md:5-25`)

### 9.3 Mode prompt

Mode prompt는 특정 task의 control-flow specification 역할을 한다.

- `oferta.md`: liveness gate, archetype detection, Block A-G, cover draft format.
- `auto-pipeline.md`: extraction/liveness/evaluation/report/PDF/application draft/tracker sequence.
- `scan.md`: local parser/API/Playwright/WebSearch discovery strategy.
- `pdf.md`: HTML/PDF content-generation and ATS rules.
- `batch-prompt.md`: batch worker용 self-contained prompt. 외부 skill 없이 필요한 평가 절차를 내장한다. (`repos/career-ops/batch/batch-prompt.md:1-29`)

## 10. 외부 시스템 연동 방식

### 10.1 Playwright / browser / MCP

- `generate-pdf.mjs`는 Playwright Chromium을 직접 import해 headless PDF render에 사용한다. (`repos/career-ops/generate-pdf.mjs:13`)
- agent mode에서는 Playwright browser tools가 URL/JD extraction, liveness, application form reading에 쓰인다. (`repos/career-ops/modes/auto-pipeline.md:5-29`, `repos/career-ops/modes/oferta.md:5-17`)
- `doctor.mjs`는 Playwright MCP tools가 설정되지 않으면 “Playwright MCP tools not detected”를 non-fatal warning으로 표면화한다. 이유는 SPA job board가 비어 있거나 stale content를 반환할 수 있기 때문이다. (`repos/career-ops/doctor.mjs:70-96`)
- `.claude-plugin/plugin.json`은 Claude plugin permissions로 `Bash(node:*)`, Greenhouse/Ashby WebFetch, WebSearch를 허용한다. (`repos/career-ops/.claude-plugin/plugin.json:9-17`)

### 10.2 ATS / job board APIs

`scan.mjs`의 provider layer는 pure HTTP+JSON 방식의 zero-token scanner다. (`repos/career-ops/scan.mjs:3-31`) 현재 provider 파일은 다음을 포함한다.

- `ashby.mjs`
- `greenhouse.mjs`
- `lever.mjs`
- `local-parser.mjs`
- `recruitee.mjs`
- `smartrecruiters.mjs`
- `solidjobs.mjs`
- `workable.mjs`
- `workday.mjs`

`modes/scan.md`는 agentic discovery strategy로 Level 0 local parser, Level 1 Playwright, Level 2 ATS APIs/feeds, Level 3 WebSearch를 정의한다. (`repos/career-ops/modes/scan.md:29-148`)

### 10.3 Gemini API

`gemini-eval.mjs`는 `@google/generative-ai`와 `GEMINI_API_KEY`를 사용한다. (`repos/career-ops/gemini-eval.mjs:14-18`, `repos/career-ops/gemini-eval.mjs:31-47`) 실행 시 `_shared.md`, `oferta.md`, `cv.md`, `config/profile.yml`, `_profile.md`를 하나의 system prompt로 결합해 Gemini 모델에 전달한다. (`repos/career-ops/gemini-eval.mjs:200-254`) API error message에서는 API key 문자열을 `[REDACTED]`로 scrub한다. (`repos/career-ops/gemini-eval.mjs:270-285`)

### 10.4 GitHub Releases / update endpoint

`update-system.mjs`는 GitHub releases API와 raw `VERSION` URL을 통해 update check를 수행한다. (`repos/career-ops/update-system.mjs:26-34`) 적용 대상은 `SYSTEM_PATHS` allowlist에 제한된다. (`repos/career-ops/update-system.mjs:36-120`)

### 10.5 LaTeX toolchain

`generate-latex.mjs`는 local `tectonic` 또는 `pdflatex` 실행 파일을 탐지한다. 둘 다 없으면 compile error를 JSON으로 출력하고 종료한다. (`repos/career-ops/generate-latex.mjs:133-148`)

### 10.6 Canva MCP optional path

`modes/pdf.md`는 `config/profile.yml`에 `cv.canva_resume_design_id`가 있으면 Canva CV generation 선택지를 제안하고, design export/import/content edit flow를 정의한다. (`repos/career-ops/modes/pdf.md:95-130`) 이는 optional path이며 기본 HTML/PDF flow와 별개다.

## 11. 실행 흐름 상세

### 11.1 신규 사용자 시작

```text
npx @santifer/career-ops init
  → repo/package scaffold
cd career-ops
  → claude / gemini / codex / qwen / opencode / copilot
agent reads AGENTS.md
  → node update-system.mjs check
  → node doctor.mjs --json
  → missing user layer files? onboarding
  → cv.md / config/profile.yml / portals.yml / data/applications.md 준비
```

Scaffolder가 `cv.md`, `config/profile.yml`, `portals.yml`를 의도적으로 만들지 않아 첫 agent launch에서 onboarding을 유도한다는 내용은 기존 wiki가 source-verified로 기록했다. (`wiki/projects/career-ops.md:64-101`)

### 11.2 URL 하나 평가

```text
/career-ops https://company/jobs/123
  → SKILL.md detects URL/JD input as auto-pipeline
  → Step 0: Playwright/WebFetch/WebSearch로 JD 추출
  → Step 0.5: liveness gate
  → oferta.md A-G evaluation
  → reports/{###}-{company}-{date}.md
  → config.profile.yml의 cv.output_format 확인
      ├─ html/default → modes/pdf.md → generate-pdf.mjs → output/*.pdf
      └─ latex → modes/latex.md → generate-latex.mjs → output/*.tex/*.pdf
  → score >= 4.5면 application answers draft
  → batch/tracker-additions/*.tsv
  → merge-tracker.mjs
  → data/applications.md
```

### 11.3 Scan 후 pipeline 처리

```text
/career-ops scan
  → mode delegated to subagent 권장
  → node scan.mjs로 local parser/API zero-token pass
  → 필요한 경우 Playwright/WebSearch agent pass
  → data/pipeline.md에 URL inbox 추가

/career-ops pipeline
  → data/pipeline.md pending 항목 처리
  → 각 항목을 auto-pipeline으로 평가
  → 완료/오류 상태 마킹
```

### 11.4 Batch 처리

```text
batch/batch-input.tsv
  → batch/batch-runner.sh --parallel N
  → acquire batch-runner.pid
  → init/update batch-state.tsv
  → reserve report number
  → spawn claude -p worker with batch-prompt.md
  → each worker writes report/PDF/tracker TSV
  → merge-tracker.mjs
  → verify-pipeline.mjs
```

주의: Gemini artifact는 batch를 멀티 CLI worker처럼 넓게 설명하지만, 현재 `batch-runner.sh` 주석은 “Claude Code-specific”이며 `claude -p` flags에 묶여 있다고 명시한다. (`repos/career-ops/batch/batch-runner.sh:4-12`)

### 11.5 Gemini 단방향 평가

```text
node gemini-eval.mjs --file ./jds/job.txt
  → dotenv/GEMINI_API_KEY 로드
  → _shared.md + oferta.md + cv.md + profile.yml + _profile.md 결합
  → GoogleGenerativeAI(modelName) 호출
  → A-G evaluation text 수신
  → SCORE_SUMMARY 파싱
  → reports/{num}-{company}-{date}.md 저장
  → batch/tracker-additions/{num}-{company}.tsv 저장
  → merge-tracker.mjs 실행
```

근거: `repos/career-ops/gemini-eval.mjs:200-379`

### 11.6 Dashboard 실행

```text
cd dashboard
# 또는 compiled wrapper가 있으면 해당 경로
career-ops dashboard --path <career-ops-root>
  → data.ParseApplications(path)
  → metrics/progress 계산
  → report summary batch load
  → Bubble Tea alt screen TUI
```

근거: `repos/career-ops/dashboard/main.go:154-197`

## 12. Gemini 분석 산출물 대비 source correction

이 문서는 Gemini 산출물을 baseline으로 사용했지만, 현재 source와 비교해 다음처럼 구분했다.

1. Gemini `8-multi-agent-and-tool-integration.md`는 `.claude/skills/career-ops/SKILL.md`를 중심으로 설명하지만, 현재 canonical real file은 `.agents/skills/career-ops/SKILL.md`이고 `.claude`/`.opencode` 경로는 symlink다.
2. Gemini `2-agent-mode.md`는 다국어 mode directory를 설명한다. `AGENTS.md`와 `update-system.mjs`에도 language mode가 문서화되어 있으나, 현재 worktree에는 해당 language mode 파일들이 deletion 상태로 표시된다. 따라서 이 문서에서는 “의도된/문서화된 i18n 구조”와 “현재 worktree에서 읽은 mode 파일 22개”를 분리했다.
3. Gemini `4-batch-processing.md`는 batch worker를 일반적인 multi-agent 구조로 설명하지만, 현재 `batch-runner.sh`는 Claude Code-specific이라고 주석으로 명시한다.
4. Gemini `3-pdf-and-latex-generation-engine.md`의 HTML/PDF, LaTeX 경로 설명은 현재 `generate-pdf.mjs`, `generate-latex.mjs`와 대체로 일치한다. 다만 실제 PDF 생성은 AI가 HTML을 만든 뒤 스크립트가 렌더링하는 분업 구조이며, `generate-pdf.mjs` 자체가 JD를 읽거나 이력서를 재작성하지는 않는다.
5. Gemini `5-application-tracker-and-data-layer.md`의 9-column tracker/state machine 설명은 `templates/states.yml`, `verify-pipeline.mjs`, `merge-tracker.mjs`와 일치한다.

## 13. 실행 검증 결과

이번 문서 작성 중 실제 실행한 명령과 결과는 다음과 같다.

| 명령 | 결과 |
|---|---|
| `git rev-parse HEAD` | `57b34c07e01cd106528936398507e1b4552ca295` |
| `git status --short` | language mode directories under `modes/{ar,de,fr,ja,pt,ru,tr,ua}` deletion 표시 |
| `node doctor.mjs --json` | onboarding needed: `cv.md`, `config/profile.yml`, `modes/_profile.md`, `portals.yml` missing; Playwright MCP warning |
| `node verify-pipeline.mjs` | `applications.md` 없음. fresh setup에서는 정상 메시지 후 exit 0 |
| `node test-all.mjs --quick` | 219 passed, 12 failed, 16 warnings. 주요 실패 원인은 local `node_modules` 부재로 `js-yaml` package를 못 찾는 것과 tracker sync 계열 실패. 문서 목적상 테스트를 고치거나 dependency install은 수행하지 않았다. |

## 14. 다른 프로젝트에서 참고할 설계 포인트

평가가 아니라 구조 이해 관점에서 재사용 가능한 설계 요소만 요약하면 다음이다.

1. **Prompt-as-workflow**: mode markdown을 task runner로 사용하고, Node/Go scripts는 deterministic IO와 rendering, integrity check만 담당한다.
2. **User/System layer split**: 개인 데이터와 update 가능한 system logic을 `DATA_CONTRACT.md`로 분리한다.
3. **Flat-file SSOT**: `data/applications.md`를 사람이 읽고 git으로 추적 가능한 DB로 삼되, merge/verify/dedup scripts로 무결성을 보강한다.
4. **Skill router + lazy context loading**: 모든 mode prompt를 한 번에 넣지 않고, command에 필요한 `_shared.md`/mode file만 읽는다.
5. **Human-in-the-loop boundary**: 평가, report, draft, CV 생성까지 자동화하지만 실제 지원 제출은 agent가 대신하지 않는 경계를 둔다. (`repos/career-ops/modes/_shared.md:91-100`)
6. **External baseline + source correction**: Gemini/DeepWiki 분석은 구조 후보로 활용하고, 실제 동작은 `modes/*.md`, `*.mjs`, `dashboard/*.go`에서 확인한다.
