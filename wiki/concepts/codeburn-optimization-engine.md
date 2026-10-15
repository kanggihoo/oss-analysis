---
title: CodeBurn Optimization Engine
created: 2026-06-10
updated: 2026-10-15
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence]
sources:
  - repos/codeburn/src/main.ts
  - repos/codeburn/src/optimize.ts
  - repos/codeburn/src/context-budget.ts
  - repos/codeburn/src/act/optimize-apply.ts
  - repos/codeburn/src/usage-aggregator.ts
  - repos/codeburn/src/menubar-json.ts
  - repos/codeburn/src/dashboard.tsx
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-domain-terminology.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
  - wiki/concepts/codeburn-turn-classification-engine.md
  - wiki/concepts/codeburn-pricing-and-currency-resolution.md
confidence: medium
---
# CodeBurn Optimization Engine

검증 기준 checkout: repos/codeburn at 9a40cc603fcd194caca9daa8c5134a61ea7e0e2b (2026-10-15).

[[codeburn]]의 `codeburn optimize`가 파싱된 사용량과 Claude Code 세션 JSONL·설정 파일을 다시 훑어 "토큰 낭비 후보(finding)"를 찾고, 점수·분류·적용 가능한 수정안을 내는 구조를 정리한다. 용어는 [[codeburn-domain-terminology]], 세션 파싱은 [[codeburn-data-ingestion-and-caching]], turn/retry 신호는 [[codeburn-turn-classification-engine]], 비용 환산은 [[codeburn-pricing-and-currency-resolution]] 참조.

용어:
- **finding** (`WasteFinding`): 하나의 낭비 진단. id, 제목, 설명, impact, 절약 추정 토큰(`tokensSaved`), 수정안(`fix`)을 담는다. (`src/optimize.ts:555-579`, 코드 확인)
- **detector**: `detectXxx()` 함수 하나 = finding 하나를 만들거나 `null`을 돌려주는 규칙.
- **finding class**: 사용자가 어떻게 조치하는지 — `fix`(CodeBurn이 직접 설정 변경), `nudge`(습관 교정), `keep`(참고용). (`src/optimize.ts:376-380`, 코드 확인)
- **basis**: 절약 수치의 근거 — `measured`(provider가 센 실제 토큰 합) / `estimated`(모델링 추정). (`src/optimize.ts:382-386`, 코드 확인)

## CLI 진입점 (`src/main.ts:2415-2488`)

- 입력: `--period`(기본 `30days`), `--from/--to`, `--provider`, `--format text|json`(`--json` 별칭), `--project/--exclude`, 그리고 신규 `--apply`, `--yes`, `--dry-run`, `--only <ids>`, `--auto-revert`. (`src/main.ts:2418-2430`, 코드 확인)
- 내부 동작:
  1. `--apply`와 JSON 출력 동시 지정은 exit 2. (`src/main.ts:2434-2437`, 코드 확인)
  2. `loadPricing()` → 기간 계산 → `parseAllSessions(range, provider)` → 프로젝트 이름 필터. (`src/main.ts:2438-2455`, 코드 확인)
  3. `--apply`면 `act/optimize-apply.js`의 `runOptimizeApply()`로 분기하고 끝. (`src/main.ts:2456-2460`, 코드 확인)
  4. 아니면 적용 이력 journal을 `computeActReport()`로 읽어 "이미 적용한 fix" 헤더/실측 절감량을 붙이고, `--auto-revert`면 효과 없던 fix를 되돌린다. 이 단계 실패는 무시한다. (`src/main.ts:2466-2486`, 코드 확인)
  5. `runOptimize(projects, label, range, {...})`. (`src/main.ts:2487`, 코드 확인)

## `runOptimize()` (`src/optimize.ts:4384-4414`)

- 입력: `ProjectSummary[]`, 기간 라벨, `DateRange`, `{ format, appliedHeader, previouslyApplied, appliedFixes, provider }`.
- 내부 동작: `scanAndDetect()` 호출 → `json`이면 `buildOptimizeJsonReport()`를 그대로 출력, `text`면 `buildWorkflowReport()`(재작업 파일·코칭 노트)와 함께 `renderOptimize()`. (코드 확인)
- 반환값: 없음(stdout 출력).

JSON 스키마(`buildOptimizeJsonReport`, `src/optimize.ts:4416-4478`, 코드 확인): `period`, `summary`(healthScore/Grade, `potentialSavings*`, `costRateUSD`, `measuredSavingsUSD`, `byClass`), `findings[]`(id, severity, trend, class, basis, fix…), workflow 필드, `modelRecommendations`, `appliedFixes`.

## `scanAndDetect()` — 핵심 파이프라인 (`src/optimize.ts:4054-4145`)

- 입력: `projects`, `dateRange?`, `provider?`.
- 내부 동작:
  1. 결과 캐시: `cacheKey()`(provider + 기간 + 프로젝트/세션/sidechain/비용 fingerprint)로 60초 TTL 메모. (`src/optimize.ts:4022-4052`, `:4063-4065`, `:706`, 코드 확인)
  2. `computeInputCostRate()`: 총비용×0.7 ÷ (input+cacheRead+cacheWrite 토큰) = 토큰당 단가. 토큰 절약을 달러로 바꿀 때 쓴다. (`src/optimize.ts:4002-4014`, 코드 확인)
  3. `userStartedProjects()`로 사용자가 시작한 세션만 남긴 `behavioralProjects`를 행동 detector에 쓴다. (`src/optimize.ts:4068`, 코드 확인)
  4. `scanSessions()`: provider가 Claude를 포함할 때만 `discoverAllSessions('claude')`의 JSONL을 동시성 4로 다시 읽어 tool call, cwd, API call, user message, session opener를 모은다. 기간 시작보다 mtime이 오래된 파일은 건너뛴다. (`src/optimize.ts:1286-1324`, `:705`, 코드 확인)
  5. 세션 단위 finding 중복 제거: low-worth → context-bloat → outlier 순으로 앞 detector가 지목한 세션을 뒤에서 제외. 신생 프로젝트의 첫 세션도 outlier에서 제외. (`src/optimize.ts:4074-4084`, 코드 확인)
  6. `claudeOnly()` 래퍼: Claude 스캔/`~/.claude` 설정에 의존하는 detector는 다른 `--provider`에서 실행하지 않는다(빈 스캔을 "미사용"으로 오판하지 않기 위해). (`src/optimize.ts:4085-4091`, 코드 확인)
  7. 동기 detector 18개 실행 후, Claude 범위일 때 ghost agents/skills/commands 3개를 `Promise.all`. (`src/optimize.ts:4092-4124`, 코드 확인)
  8. 정렬: `urgencyScore` 내림차순 후 class 순서(fix → nudge → keep)로 stable sort. (`src/optimize.ts:4129-4130`, 코드 확인)
  9. `computeHealth()` + 프로젝트별 `recommendModelDefault()`(기본 모델 추천). (`src/optimize.ts:4131-4137`, 코드 확인)
- 반환값: `OptimizeResult { findings, costRate, healthScore, healthGrade, modelRecommendations }`. (`src/optimize.ts:581-587`, 코드 확인)

## Detector 목록 (`FindingId`, `src/optimize.ts:353-374`)

21개 id는 `--only` 필터와 apply plan 라우팅의 안정 키라 바뀌지 않는다고 주석에 명시. (`src/optimize.ts:350-352`, 코드 확인)

| 그룹 | FindingId (class) |
|---|---|
| 파일 읽기 | `read-edit-ratio`(fix), `build-folder-reads`(fix), `redundant-rereads`(nudge) |
| 캐시 | `warmup-heavy`(nudge, `detectCacheBloat`), `low-cache-hit-sessions`(nudge) |
| MCP | `unused-mcp`, `mcp-low-coverage`, `mcp-project-scope`, `mcp-deferral-off`, `mcp-alwaysload-hygiene`, `mcp-defer-threshold` (모두 fix) |
| 세션 행동 | `retry-heavy-capabilities`, `low-worth-sessions`, `cost-outliers`(nudge), `context-heavy-sessions`(keep) |
| 설정/정의 | `claude-md-too-long`(nudge), `bash-output-cap`(fix), `unused-agents`/`unused-skills`/`unused-commands`(fix), `recurring-context`(nudge) |

근거: `FINDING_CLASS` (`src/optimize.ts:392-414`, 코드 확인). basis는 `context-heavy-sessions`, `cost-outliers`만 `measured`이고 나머지는 추정. (`src/optimize.ts:433-457`, 코드 확인)

예시 detector — `detectJunkReads` (`src/optimize.ts:1423-1471`, 코드 확인):
- 입력: tool call 목록, 기간. 내부: Read 계열 호출의 `file_path`가 `JUNK_DIRS`(node_modules 등) 패턴이면 카운트, 3회 미만이면 `null`, trend가 `resolved`면 `null`. 절약 = 읽기 수 × `AVG_TOKENS_PER_READ`(600). 반환: `build-folder-reads` finding + CLAUDE.md에 붙여넣을 규칙 문장.

MCP schema 비용은 `estimateMcpSchemaCost()`가 로드된 세션의 cache write/read 토큰에 상한을 두고 `CACHE_WRITE_MULTIPLIER`(1.25)·`CACHE_READ_DISCOUNT`(0.10)로 환산한다. (`src/optimize.ts:86-87`, `:1713-1750`, 코드 확인 — 내부 `estimateMcpSchemaCostAttributed` 세부는 미확인)

## Class 판정 (`findingClass`, `src/optimize.ts:466-478`)

정적 class가 `fix`라도 apply payload가 없거나, 설정이 shell profile에 있거나, deferral 원인이 `env-false`/`proxy-verified`가 아니면 `nudge`로 강등. `classTotals()`는 fix 그룹에 `applyTokensSaved`(실제 적용 가능한 부분)만 합산해 "apply 가능 절감액"을 과장하지 않는다. (`src/optimize.ts:494-516`, 코드 확인)

## 점수 · trend · urgency

- Health: impact 페널티 high 15 / medium 7 / low 3, 상한 80, `score = 100 - min(80, sum)`. 등급 A≥90, B≥75, C≥55, D≥30, 그 외 F. finding 0개면 100/A. (`src/optimize.ts:200-207`, `:3940-3951`, 코드 확인)
- Urgency: impact 가중(1/0.5/0.2)×0.5 + min(1, tokensSaved/5M)×0.5. 표시 순서용이며 점수와 별개. (`src/optimize.ts:214-216`, `:3953-3958`, 코드 확인)
- Trend: 최근 48시간 발생률 vs 기간 baseline 발생률. baseline 0이면 `active`, 최근 활동이 있는데 최근 0건이면 `resolved`(finding 숨김), 최근률 < baseline×0.5면 `improving`. (`src/optimize.ts:707-711`, `:3968-4004`, 코드 확인)

## `--apply` 흐름 (`runOptimizeApply`, `src/act/optimize-apply.ts:130-200`)

`scanAndDetect()` → `planFindings()`로 finding별 plan 생성(`act/plans.ts`의 `buildPlan`) → plan 없는 것은 수동 안내 → `--only` 검증(잘못된 id면 exit 2) → `--dry-run`이면 목록만 출력 → `--yes`면 일괄 적용하되 CLAUDE.md 규칙은 명시적 `--only` 없이는 건너뜀. (코드 확인) 백업/journal/undo 세부(`act/backup.ts`, `act/journal.ts`, `act/undo.ts`)는 미확인.

## 다른 소비자

- 메뉴바: `buildMenubarPayloadForRange()`가 `opts.optimize !== false`일 때 `scanAndDetect()`를 돌리고(`src/usage-aggregator.ts:2079`), `buildOptimize()`가 findingCount·savingsUSD·상위 finding만 payload에 넣는다(`src/menubar-json.ts:665-681`). 코드 확인. → [[codeburn-report-status-export-commands]]
- 대시보드 TUI: `src/dashboard.tsx:1836`에서 `scanAndDetect()` 호출, class 헤더는 `classHeaderLine()` 공유. (코드 확인)

## Context budget (`src/context-budget.ts`)

`estimateContextBudget(projectPath?, modelContext = 1_000_000)` (`:114-132`, 코드 확인):
- 입력: 프로젝트 경로. 내부: 시스템 기본 10,400 + MCP tool 수×400 + skill 수×80 + 메모리 파일(CLAUDE.md 등) 문자 기반 토큰 추정. 반환: `ContextBudget` (`:13-20`).
- 현재 호출처는 `src/dashboard.tsx:1748` 뿐이며 optimize 엔진은 이를 쓰지 않는다. (grep 기준 코드 확인)

## 미확인

- 18개 동기 detector 각각의 임계값·계산식 상세(이 노트는 `detectJunkReads`만 본문 검증).
- `scanJsonlFileMemoized`의 증분 재스캔 메모(`src/optimize.ts:1076-1285`) 정확성 — 주석만 읽음.
- `act/plans.ts` plan 종류별 실제 파일 변경, 백업·undo 동작.
- `renderOptimize()` 텍스트 출력 레이아웃.
- 실행 확인 없음(앱 미실행).
