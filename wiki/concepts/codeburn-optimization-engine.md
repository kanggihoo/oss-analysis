---
title: CodeBurn Optimization Engine
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence, deepwiki]
sources:
  - artifacts/codeburn/deepwiki/pages-md/3.3-optimization-engine-(codeburn-optimize).md
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-domain-terminology.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
  - wiki/concepts/codeburn-turn-classification-engine.md
  - wiki/concepts/codeburn-pricing-and-currency-resolution.md
  - repos/codeburn/src/main.ts
  - repos/codeburn/src/optimize.ts
  - repos/codeburn/src/context-budget.ts
  - repos/codeburn/src/providers/index.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/types.ts
confidence: high
---
# CodeBurn Optimization Engine

이 페이지는 [[codeburn]]의 `codeburn optimize`가 파싱된 사용량과 Claude Code session JSONL/config를 다시 스캔해 token waste 후보를 찾고, health score와 실행 가능한 fix를 출력하는 방식을 정리한다. 기본 domain term은 [[codeburn-domain-terminology]], session parsing/caching은 [[codeburn-data-ingestion-and-caching]], turn/retry/edit signal은 [[codeburn-turn-classification-engine]], 비용 환산은 [[codeburn-pricing-and-currency-resolution]]를 참조한다.

검증 기준 checkout: `repos/codeburn` at `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.

## CLI entrypoint

`codeburn optimize`는 `src/main.ts`의 commander subcommand다. 실행 시 먼저 model pricing을 로드하고, 선택한 기간을 `getDateRange()`로 만든 뒤, `parseAllSessions(range, provider)` 결과를 `runOptimize(projects, label, range)`에 넘긴다. (`repos/codeburn/src/main.ts:1031-1040`)

```text
codeburn optimize --period 30days --provider all
→ loadPricing()
→ parseAllSessions(range, provider)
→ runOptimize(projects, label, range)
→ scanAndDetect(projects, range)
→ renderOptimize(...)
```

## Two input streams

Optimization engine은 두 종류의 입력을 결합한다.

| Input | 어디서 옴 | 용도 |
|---|---|---|
| `ProjectSummary[]` | `parseAllSessions()`가 이미 만든 provider-normalized summary | cost, calls, sessions, turns, retries, edit/one-shot metrics, MCP inventory/breakdown, token totals |
| `ScanData` | `scanSessions()`가 Claude JSONL을 직접 lightweight scan | raw tool calls, project cwd, API cache creation metadata, user slash-command messages |

`scanAndDetect()`는 `ProjectSummary[]`가 비어 있으면 바로 health A를 반환하고, 아니면 60초 process-local `resultCache`를 확인한다. Cache miss면 `computeInputCostRate(projects)`, `scanSessions(dateRange)`, `aggregateMcpCoverage(projects)`를 실행한 뒤 detector suite를 돌린다. (`repos/codeburn/src/optimize.ts:2261-2328`)

## JSONL scanner

`scanSessions()`는 `discoverAllSessions('claude')`로 Claude source만 찾고, 각 source directory에서 `.jsonl`과 subagent `.jsonl`을 수집한다. Date range보다 mtime이 오래된 file은 skip하고, file 읽기는 concurrency 4로 제한한다. (`repos/codeburn/src/optimize.ts:264-299`, `repos/codeburn/src/optimize.ts:404-429`)

`scanJsonlFile()`은 전체 parser를 다시 수행하지 않고 optimization에 필요한 field만 뽑는다.

- `cwd` → project config/MCP/CLAUDE.md 탐색용
- `user.message.content` → slash command 사용 여부 탐지용
- assistant usage의 `cache_creation_input_tokens`와 `version` → cache bloat 탐지용
- assistant content의 `tool_use` block → read/edit/MCP/agent/skill detector용 compact tool call

Tool input은 전부 저장하지 않고 `Read.file_path`, `Agent/Task.subagent_type`, `Skill.skill/name`만 남긴다. (`repos/codeburn/src/optimize.ts:230-254`, `repos/codeburn/src/optimize.ts:320-402`)

## Detector pipeline

Current source의 detector set은 DeepWiki 요약보다 넓다. `scanAndDetect()`의 synchronous detector order는 다음이다. (`repos/codeburn/src/optimize.ts:2286-2315`)

1. `detectCacheBloat`
2. `detectLowReadEditRatio`
3. `detectJunkReads`
4. `detectDuplicateReads`
5. `detectUnusedMcp`
6. `detectMcpToolCoverage`
7. `detectMcpProfileAdvisor`
8. `detectCapabilityReliability`
9. `detectLowWorthSessions`
10. `detectContextBloat`
11. `detectSessionOutliers`
12. `detectBloatedClaudeMd`
13. `detectBashBloat`

그 다음 async detector인 `detectGhostAgents`, `detectGhostSkills`, `detectGhostCommands`를 `Promise.all()`로 실행한다. 모든 finding은 `urgencyScore()`로 정렬한 뒤 health score를 계산한다. (`repos/codeburn/src/optimize.ts:2317-2327`)

## 주요 waste detector 동작

| Detector | 무엇을 본다 | Trigger / 계산 |
|---|---|---|
| Junk reads | `Read`/`FileReadTool`의 `file_path` | `node_modules`, `.git`, `dist`, build/cache directory read가 3회 이상이면 flag. Extra read × 600 token 추정. (`repos/codeburn/src/optimize.ts:148-154`, `repos/codeburn/src/optimize.ts:486-532`) |
| Duplicate reads | 같은 project/session 안의 같은 file read 반복 | junk path를 제외하고 extra duplicate read가 5회 이상이면 flag. (`repos/codeburn/src/optimize.ts:535-593`) |
| Low read:edit ratio | Read/Grep/Glob vs Edit/Write tool count | edit 10회 이상이고 reads/edits가 4 미만이면 flag. 최근 48h ratio가 회복되면 resolved/improving 처리. (`repos/codeburn/src/optimize.ts:1528-1575`) |
| Cache bloat | assistant usage의 `cache_creation_input_tokens` | API samples 10개 이상, median cache creation이 project/session baseline의 1.4배 이상이면 flag. (`repos/codeburn/src/optimize.ts:1577-1646`) |
| Bloated CLAUDE.md | project `CLAUDE.md`, `.claude/CLAUDE.md` | `@` import를 depth 5까지 따라가 expanded lines가 200 초과이면 flag. (`repos/codeburn/src/optimize.ts:144-146`, `repos/codeburn/src/optimize.ts:1464-1526`) |
| Unused MCP | configured MCP vs observed calls/breakdown | 최근 24h 내 새 config와 tool-coverage detector가 이미 담당한 server는 제외하고, 호출 없는 configured server를 flag. (`repos/codeburn/src/optimize.ts:452-480`, `repos/codeburn/src/optimize.ts:1399-1462`) |
| MCP tool coverage | `mcpInventory`, `mcpBreakdown`, call `mcpTools` | server가 10개 초과 tool을 expose하고, 2 session 이상 loaded됐고, coverage가 20% 미만이면 unused schema tax로 flag. (`repos/codeburn/src/optimize.ts:627-731`, `repos/codeburn/src/optimize.ts:839-911`) |
| Ghost agents/skills/commands | `~/.claude/agents`, `~/.claude/skills`, `~/.claude/commands` | 정의됐지만 기간 내 Agent/Task/Skill/slash command 사용 흔적이 없으면 flag. (`repos/codeburn/src/optimize.ts:1668-1758`) |
| Low-worth sessions | session cost, edit turns, retries, delivery command | 의미 있는 비용이 들었지만 edit/delivery signal이 약하거나 retries가 많으면 review candidate로 flag. (`repos/codeburn/src/optimize.ts:1819-1987`) |
| Context bloat | effective input/cache tokens vs output tokens | effective input 75k 이상, input/output ratio 25:1 이상이면 session opener 형태의 reset 제안. (`repos/codeburn/src/optimize.ts:1989-2100`) |
| Session outliers | project 내 peer session 평균 대비 cost | 같은 project에서 session cost가 peer average의 2배 초과이고 $1 이상이면 flag. (`repos/codeburn/src/optimize.ts:2102-2170`) |

## MCP schema tax 계산

MCP coverage detector는 단순히 unused tool 수 × token으로 끝내지 않는다. `estimateMcpSchemaCost()`는 session이 flagged server inventory를 실제로 loaded했는지 확인하고, 각 assistant call의 `cacheCreationInputTokens` / `cacheReadInputTokens` bucket에 unused schema token이 들어갈 수 있는 최대치를 cap으로 적용한다. Cache write는 1.25배, cache read는 0.1배로 effective input token을 산정한다. (`repos/codeburn/src/optimize.ts:733-837`)

이 때문에 DeepWiki의 “schema tax” 설명은 맞지만, current implementation은 cached-prefix billing을 반영하는 쪽으로 더 정교하다.

## Health score, trend, urgency

`WasteFinding`은 `title`, `explanation`, `impact`, `tokensSaved`, `fix`, optional `trend`를 담는다. Fix는 `paste`, `command`, `file-content` 중 하나이며 paste에는 `claude-md`, `session-opener`, `prompt`, `shell-config` destination이 붙을 수 있다. (`repos/codeburn/src/optimize.ts:167-196`)

Health score는 findings의 impact penalty로 계산된다.

```text
high = 15
medium = 7
low = 3
max penalty = 80
score = 100 - min(80, penalty)
A >= 90, B >= 75, C >= 55, D >= 30, F < 30
```

근거: `repos/codeburn/src/optimize.ts:122-129`, `repos/codeburn/src/optimize.ts:2176-2193`.

Trend는 최근 48시간 window와 baseline period rate를 비교한다. 최근 activity가 있고 recent count가 0이면 `resolved`, recent rate가 baseline rate의 0.5 미만이면 `improving`, 아니면 `active`다. (`repos/codeburn/src/optimize.ts:256-262`, `repos/codeburn/src/optimize.ts:2210-2239`)

Findings display order는 health penalty order가 아니라 `urgencyScore()`다. 현재 urgency는 impact weight 0.5 + normalized token saving weight 0.5로 계산한다. (`repos/codeburn/src/optimize.ts:130-138`, `repos/codeburn/src/optimize.ts:2195-2199`, `repos/codeburn/src/optimize.ts:2324`)

## Context budget utility

`src/context-budget.ts`는 fixed prompt overhead를 추정하는 utility다. 계산식은 DeepWiki 요약과 일치한다.

```text
total = 10,400 system base
      + MCP tool count × 400
      + skill count × 80
      + CLAUDE.md chars / 4
```

`countMcpTools()`는 각 configured MCP server를 5 tools로 추정하고, `countSkills()`는 `~/.claude/skills`와 project `.claude/skills/*/SKILL.md`를 센다. `scanMemoryFiles()`는 home/project CLAUDE memory files를 token estimate로 바꾼다. (`repos/codeburn/src/context-budget.ts:8-24`, `repos/codeburn/src/context-budget.ts:33-101`, `repos/codeburn/src/context-budget.ts:104-149`)

다만 current source에서 `scanAndDetect()`가 `estimateContextBudget()`을 직접 호출하지는 않는다. Optimize CLI의 main detector path는 `src/optimize.ts` 안의 detector들과 parsed project summaries/Claude JSONL scanner다. `context-budget.ts`는 별도 exported utility로 남아 있다.

## Output rendering

`runOptimize()`는 stderr에 “Analyzing your sessions...”를 출력하고, `scanAndDetect()` 결과를 `renderOptimize()`로 panel 형태로 출력한다. 각 finding은 impact, optional improving badge, potential token/cost savings, 그리고 destination-labeled fix block을 가진다. Destination label은 permanent CLAUDE.md rule과 one-time session opener/prompt/shell-config를 구분하기 위한 장치다. (`repos/codeburn/src/optimize.ts:2356-2419`, `repos/codeburn/src/optimize.ts:2475-2494`)

## Current-source corrections vs DeepWiki

- DeepWiki line ranges are stale: current `scanAndDetect()` is around `repos/codeburn/src/optimize.ts:2270-2328`, not the older `222-258` range.
- Detector set is broader than the DeepWiki page: MCP profile advisor, capability reliability, bash bloat, low-worth sessions, context-heavy sessions, and session outliers are also in the current pipeline.
- DeepWiki describes unused MCP servers as “not called within the last 30 days”; current code uses the CLI date range plus observed calls/session breakdown, suppresses recently modified config within 24h, and suppresses servers already handled by MCP tool coverage.
- `context-budget.ts` is accurate as an overhead estimator, but it is not directly called by `scanAndDetect()` in the current source.

관련 페이지: [[codeburn]], [[codeburn-domain-terminology]], [[codeburn-data-ingestion-and-caching]], [[codeburn-turn-classification-engine]], [[codeburn-pricing-and-currency-resolution]], [[evidence-backed-analysis]].
