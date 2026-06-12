---
title: CodeBurn
created: 2026-06-10
updated: 2026-06-11
type: project
tags: [open-source, project, architecture, developer-tools, tooling, evidence, deepwiki]
sources:
  - artifacts/codeburn/deepwiki/pages-md/2-core-architecture.md
  - deepwiki-ko/codeburn/2-core-architecture.md
  - wiki/concepts/codeburn-domain-terminology.md
  - repos/codeburn/package.json
  - repos/codeburn/src/cli.ts
  - repos/codeburn/src/main.ts
  - repos/codeburn/src/providers/types.ts
  - repos/codeburn/src/providers/index.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/classifier.ts
  - repos/codeburn/src/models.ts
  - repos/codeburn/src/day-aggregator.ts
  - repos/codeburn/src/daily-cache.ts
  - repos/codeburn/src/usage-aggregator.ts
  - repos/codeburn/src/menubar-json.ts
  - repos/codeburn/src/dashboard.tsx
  - repos/codeburn/src/format.ts
  - repos/codeburn/src/mcp/server.ts
confidence: high
---

# CodeBurn

CodeBurn은 AI coding assistant가 로컬에 남긴 session/log data를 읽어 token 사용량, 비용, task category, cache 효율, one-shot/retry 지표, 최적화 후보를 보여주는 developer observability tool이다. DeepWiki의 architecture page를 baseline으로 삼았지만, 이 페이지는 현재 local checkout `repos/codeburn`의 source path를 기준으로 검증한 구조만 정리한다. 용어 정의는 [[codeburn-domain-terminology]]를 참조한다.

검증 기준 checkout: `repos/codeburn` at `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.

## Current entrypoint and packaging

- npm package 이름은 `codeburn`이고 Node.js `>=22.13.0`을 요구한다. `package.json`의 bin은 `dist/cli.js`를 가리키며, build script는 `src/cli.ts`를 `dist/cli.js`로 복사한다. (`repos/codeburn/package.json:2-18`, `repos/codeburn/package.json:36-38`)
- `src/cli.ts`는 실제 CLI 본체가 아니라 Node version guard 후 `./main.js`를 dynamic import하는 thin launcher다. (`repos/codeburn/src/cli.ts:1-15`)
- 실제 command registration과 orchestration은 `src/main.ts`가 맡는다. `program.hook('preAction')`에서 timezone, config, model aliases, local-model savings, proxy paths, currency를 로드하고, 이후 `report`, `status`, `today`, `month` 등 command action이 pipeline을 호출한다. (`repos/codeburn/src/main.ts:133-159`, `repos/codeburn/src/main.ts:410-578`)

## Source-verified architecture pipeline

```text
local provider logs / network provider data
→ Provider registry + discovery
→ parser normalization + dedup + session cache
→ ParsedApiCall / ParsedTurn / ClassifiedTurn
→ classification + model pricing / cost calculation
→ SessionSummary / ProjectSummary
→ day/period aggregation + daily cache
→ CLI/TUI, JSON/menubar payload, MCP tools
```

### 1. Provider registry and discovery

`Provider`는 AI coding tool별 adapter interface다. 각 provider는 `discoverSessions()`로 source를 찾고 `createSessionParser()`로 source를 `ParsedProviderCall` stream으로 변환한다. (`repos/codeburn/src/providers/types.ts:38-48`)

`getAllProviders()`는 core provider 배열과 optional dynamic imports를 결합해 전체 provider registry를 만든다. 현재 source에는 Claude, Cline, Codebuff, Codex, Copilot, Devin, Droid, Gemini, IBM Bob, Kilo Code, Kiro, Kimi, Mistral Vibe, Mux, OpenClaw, Pi/OMP, Qwen, Roo Code와 optional Antigravity/Forge/Goose/Cursor/OpenCode/Cursor Agent/Crush/Warp/Vercel Gateway loader가 있다. `discoverAllSessions()`는 filter에 맞는 provider들의 `discoverSessions()` 결과를 합친다. (`repos/codeburn/src/providers/index.ts:155-186`)

### 2. Parsing, normalization, and deduplication

`parseAllSessions()`가 ingestion의 중심 함수다. 이 함수는 memory session cache를 먼저 확인하고, disk session cache를 로드한 뒤, `discoverAllSessions()`로 source 목록을 얻는다. Claude source는 별도 path로 처리하고, non-Claude source는 provider별로 `parseProviderSources()`에 전달한다. (`repos/codeburn/src/parser.ts:2231-2260`)

`parseProviderSources()`는 file fingerprint와 disk cache를 비교해 unchanged source는 재사용하고 changed source만 provider parser로 다시 읽는다. provider가 network source이면 fingerprint 없이 매번 fetch 대상으로 취급한다. parser 실패는 전체 run을 깨지 않고 failed cache marker로 기록한다. (`repos/codeburn/src/parser.ts:1947-2044`)

Deduplication은 두 층이다.

- Parse-time: cached turn들의 `deduplicationKey`를 parser dedup set에 넣어 중복 provider call을 억제한다. (`repos/codeburn/src/parser.ts:1991-2000`)
- Query-time: `seenKeys`로 provider/source 간 중복 call을 다시 거르고, date range도 assistant call timestamp 기준으로 적용한다. (`repos/codeburn/src/parser.ts:2063-2085`)

### 3. Internal entity model

Raw provider call은 canonical cached turn을 거쳐 `ClassifiedTurn`과 `SessionSummary`로 집계된다. Core type hierarchy는 다음과 같다.

| Entity | Role | Evidence |
|---|---|---|
| `ParsedApiCall` | provider/model call 1회: tokens, cost, tools, MCP tools, skills, subagents, bash commands, dedup key 포함 | `repos/codeburn/src/types.ts:72-96` |
| `ParsedTurn` | user message 1개와 그 뒤 assistant call sequence | `repos/codeburn/src/types.ts:65-70`, `repos/codeburn/src/parser.ts:1166-1208` |
| `ClassifiedTurn` | `ParsedTurn` + category/retries/hasEdits | `repos/codeburn/src/types.ts:119-124`, `repos/codeburn/src/classifier.ts:193-217` |
| `SessionSummary` | session-level cost/token/tool/category/model/MCP/bash/subagent aggregate | `repos/codeburn/src/types.ts:126-156`, `repos/codeburn/src/parser.ts:1263-1390` |
| `ProjectSummary` | project path 기준 session summary 묶음과 project total | `repos/codeburn/src/types.ts:158-171`, `repos/codeburn/src/parser.ts:2293-2319` |

`parseAllSessions()` 마지막 단계는 Claude/non-Claude project result를 normalized project path로 merge한다. 이 때문에 같은 repo를 Claude Code와 Codex 등 여러 provider로 사용해도 project-level summary에서 중복 project가 줄어든다. (`repos/codeburn/src/parser.ts:2266-2319`)

### 4. Classification and costing

Task classification은 `classifyTurn()`에서 수행된다. Tool이 있으면 edit/read/bash/task/search/MCP/Skill tool set 기반으로 1차 분류하고, user message keyword로 `feature`, `debugging`, `refactoring` 등을 보정한다. Tool이 없거나 pattern이 없으면 conversation classifier로 fallback한다. (`repos/codeburn/src/classifier.ts:18-22`, `repos/codeburn/src/classifier.ts:60-94`, `repos/codeburn/src/classifier.ts:119-153`, `repos/codeburn/src/classifier.ts:193-217`)

Costing은 `models.ts`가 담당한다. Bundled LiteLLM snapshot과 fallback data를 `ModelCosts`로 로드하고, `calculateCost()`는 input/output/cache write/cache read/web search token/request 비용과 fast multiplier를 합산한다. Unknown model은 0 cost로 처리하되 경고와 alias/model-savings hint를 낸다. (`repos/codeburn/src/models.ts:1-33`, `repos/codeburn/src/models.ts:201-204`, `repos/codeburn/src/models.ts:537-583`)

### 5. Aggregation and caching

Aggregation은 session/project summary와 day/period summary 두 레벨로 나뉜다.

- `buildSessionSummary()`는 classified turn들을 session-level totals와 breakdowns로 접는다. (`repos/codeburn/src/parser.ts:1263-1390`)
- `aggregateProjectsIntoDays()`는 `ProjectSummary[]`를 calendar day별 `DailyEntry[]`로 접고, cost/savings/calls/tokens/model/category/provider totals를 만든다. (`repos/codeburn/src/day-aggregator.ts:29-100`)
- `buildPeriodData()`와 `buildPeriodDataFromDays()`는 current period payload에 필요한 category/model/session/tokens totals를 만든다. (`repos/codeburn/src/usage-aggregator.ts:12-53`, `repos/codeburn/src/day-aggregator.ts:103-154`)
- `DailyCache`는 versioned daily cache이며 기본 cache path는 `~/.cache/codeburn/daily-cache.json`이고 `CODEBURN_CACHE_DIR`로 override 가능하다. (`repos/codeburn/src/daily-cache.ts:14-16`, `repos/codeburn/src/daily-cache.ts:43-60`)
- `hydrateCache()`는 `ensureCacheHydrated()`에 `parseAllSessions(range, 'all')`, `aggregateProjectsIntoDays`, local-model savings config hash를 넘겨 daily history를 backfill한다. 현재 source에서 이 함수는 DeepWiki가 언급한 `src/cli.ts`가 아니라 `src/usage-aggregator.ts`에 있다. (`repos/codeburn/src/usage-aggregator.ts:55-73`)

### 6. Presentation surfaces

CodeBurn은 같은 aggregation pipeline을 여러 UI/API surface로 내보낸다.

| Surface | Implementation | Evidence |
|---|---|---|
| Interactive TUI | `report`, `today`, `month` command가 `renderDashboard()`를 호출하고, dashboard는 Ink/React 기반이다. | `repos/codeburn/src/main.ts:410-458`, `repos/codeburn/src/main.ts:546-578`, `repos/codeburn/src/dashboard.tsx:1-20` |
| Compact status | `status` command의 terminal output은 `parseAllSessions()` 후 `renderStatusBar()`로 렌더링한다. | `repos/codeburn/src/main.ts:461-544`, `repos/codeburn/src/format.ts:31-63` |
| JSON report | `report --format json`과 `today/month --format json`은 `buildJsonReport()`를 출력한다. | `repos/codeburn/src/main.ts:125-130`, `repos/codeburn/src/main.ts:161-220`, `repos/codeburn/src/main.ts:439-453` |
| Menubar JSON | `status --format menubar-json`은 `buildMenubarPayloadForRange()`를 호출하고, 최종 schema는 `buildMenubarPayload()`가 만든다. | `repos/codeburn/src/main.ts:487-503`, `repos/codeburn/src/usage-aggregator.ts:89-120`, `repos/codeburn/src/menubar-json.ts:304-341` |
| MCP server | MCP tools는 같은 `buildMenubarPayloadForRange()` aggregate를 재사용해 `get_usage`, `get_savings` 같은 read-only local usage tools를 제공한다. | `repos/codeburn/src/mcp/server.ts:1-21`, `repos/codeburn/src/mcp/server.ts:31-47` |

## DeepWiki baseline drift notes

`artifacts/codeburn/deepwiki/pages-md/2-core-architecture.md`는 high-level pipeline을 이해하는 데 유용하지만, 현재 checkout과 비교하면 다음 보정이 필요하다.

| DeepWiki 표현 | 현재 소스 기준 보정 |
|---|---|
| `src/cli.ts`가 command orchestration과 `hydrateCache`를 조정하는 것처럼 설명 | `src/cli.ts`는 Node version guard launcher이고 실제 CLI orchestration은 `src/main.ts`; `hydrateCache()`는 `src/usage-aggregator.ts`에 있음 |
| `DailyCache`가 `~/.config/codeburn/cache/v4/`에 저장된다고 설명 | 현재 `daily-cache.ts` 기준 기본 path는 `~/.cache/codeburn/daily-cache.json`; `CODEBURN_CACHE_DIR`로 override 가능 |
| `ProjectSummary` line range와 type shape | 현재 `src/types.ts:158-171`이며 `totalSavingsUSD`, `totalProxiedCostUSD` 등 DeepWiki page 작성 시점보다 확장된 field가 있음 |
| provider count / registry | 현재 registry는 core + optional dynamic providers로 구성되며, exact supported provider set은 `src/providers/index.ts` 기준으로 재검증해야 함 |

## Related pages

- [[codeburn-codex-provider]]
- [[codeburn-data-ingestion-and-caching]]
- [[codeburn-day-aggregation-and-caching]]
- [[codeburn-domain-terminology]]
- [[codeburn-optimization-engine]]
- [[codeburn-pricing-and-currency-resolution]]
- [[codeburn-provider-plugin-system]]
- [[codeburn-report-status-export-commands]]
- [[codeburn-subscription-plans-and-currency]]
- [[codeburn-turn-classification-engine]]
- [[deepwiki-first-baseline]]
- [[evidence-backed-analysis]]
- [[workspace-boundaries]]
