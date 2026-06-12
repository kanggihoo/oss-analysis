---
title: CodeBurn Provider Plugin System
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence, deepwiki]
sources:
  - artifacts/codeburn/deepwiki/pages-md/4-provider-plugin-system.md
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
  - wiki/concepts/codeburn-domain-terminology.md
  - repos/codeburn/src/providers/types.ts
  - repos/codeburn/src/providers/index.ts
  - repos/codeburn/src/providers/codex.ts
  - repos/codeburn/src/providers/cursor.ts
  - repos/codeburn/src/providers/opencode.ts
  - repos/codeburn/src/providers/antigravity.ts
  - repos/codeburn/src/providers/sqlite-session-parser.ts
  - repos/codeburn/src/sqlite.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/tests/provider-registry.test.ts
confidence: high
---
# CodeBurn Provider Plugin System

이 페이지는 [[codeburn]]의 provider plugin system을 정리한다. DeepWiki `4 Provider Plugin System`을 baseline으로 삼았지만, durable claim은 현재 `repos/codeburn` source를 직접 확인해 기록한다. Provider가 발견한 source를 core parser/cache가 처리하는 더 넓은 ingestion 흐름은 [[codeburn-data-ingestion-and-caching]], 공통 entity 용어는 [[codeburn-domain-terminology]]를 참조한다.

검증 기준 checkout: `repos/codeburn` at `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.

## Mental model

CodeBurn provider는 “AI coding tool별 raw history format → 공통 `ParsedProviderCall` stream” 변환 adapter다. Core parser는 모든 tool format을 직접 알지 않고, provider registry에서 선택된 provider의 discovery/parser를 호출한 뒤, 결과를 session/project/day/report 구조로 접는다.

```text
local files / SQLite DB / network API
→ Provider.discoverSessions()
→ SessionSource[]
→ Provider.createSessionParser(source, seenKeys, dateRange)
→ ParsedProviderCall stream
→ parseProviderSources(): cache, dedup, date filter
→ ClassifiedTurn / SessionSummary / ProjectSummary
→ dashboard, JSON, menubar, MCP, export
```

## Provider interface

현재 `Provider` interface는 다음 contract를 요구한다. (`repos/codeburn/src/providers/types.ts:38-48`)

| Field/method | 역할 |
|---|---|
| `name` | 내부 provider id. 예: `claude`, `codex`, `cursor`, `opencode` |
| `displayName` | 사용자-facing 이름 |
| `network?` | live API source provider 여부. true면 파일 fingerprint 없이 매 run 재-fetch |
| `modelDisplayName(model)` | raw model id를 사람이 읽기 쉬운 이름으로 표시 |
| `toolDisplayName(rawTool)` | provider-specific tool name을 CodeBurn canonical tool name으로 표시 |
| `discoverSessions()` | local filesystem/DB/API에서 `SessionSource[]` 발견 |
| `createSessionParser(source, seenKeys, dateRange?)` | source를 `ParsedProviderCall` async stream으로 변환 |

`ParsedProviderCall`은 provider/model, token buckets, `costUSD`, tools/bash commands, timestamp, speed, `deduplicationKey`, user message, session/project 정보를 담는다. (`repos/codeburn/src/providers/types.ts:13-36`)

## Registry: core providers + optional lazy providers

현재 source 기준 provider registry는 DeepWiki page보다 커졌다.

Core providers는 동기 import되어 `providers` export에 바로 들어간다. 현재 core set은 다음 19개다. (`repos/codeburn/src/providers/index.ts:1-19`, `repos/codeburn/src/providers/index.ts:155`, `repos/codeburn/tests/provider-registry.test.ts:5-7`)

```text
claude, cline, codebuff, codex, copilot, devin, droid, gemini,
ibm-bob, kilo-code, kiro, kimi, mistral-vibe, mux, openclaw,
pi, omp, qwen, roo-code
```

Optional lazy providers는 dynamic import wrapper가 `try/catch`로 로드한다. Import 실패 시 `null`을 반환하므로 optional provider나 dependency 문제로 전체 registry가 깨지지 않는다. `getAllProviders()`는 이 lazy loaders를 `Promise.all()`로 호출한 뒤 성공한 provider만 core list 뒤에 붙인다. (`repos/codeburn/src/providers/index.ts:21-153`, `repos/codeburn/src/providers/index.ts:157-171`)

현재 optional lazy set은 다음 9개다.

```text
antigravity, forge, goose, cursor, opencode, cursor-agent,
crush, warp, vercel-gateway
```

`getProvider(name)`은 특정 provider를 요청할 때 lazy provider는 개별 loader를 호출하고, core provider는 `coreProviders.find()`로 찾는다. (`repos/codeburn/src/providers/index.ts:189-227`)

## Discovery flow and provider filter

`discoverAllSessions(providerFilter?)`는 다음 순서로 동작한다. (`repos/codeburn/src/providers/index.ts:176-186`)

1. `getAllProviders()`로 core + loadable optional provider 목록을 만든다.
2. `providerFilter`가 있고 `all`이 아니면 `p.name === providerFilter`로 먼저 provider list를 줄인다.
3. 선택된 provider들의 `discoverSessions()`를 순차 호출한다.
4. 모든 provider의 `SessionSource[]`를 하나로 합친다.

따라서 CLI의 `--provider cursor` 같은 필터는 source discovery 전에 적용된다. 이 구조는 provider별 expensive scan을 줄이고, optional provider가 load되지 않는 경우에도 필터 결과가 빈 list로 자연스럽게 처리되게 한다.

## Core parser integration

Provider parser가 만든 call은 바로 report가 되지 않고 `parseProviderSources()`에서 cache/dedup/date-filter 경계를 통과한다. (`repos/codeburn/src/parser.ts:1947-2110`)

- Provider object는 `getProvider(providerName)`로 다시 가져온다.
- `provider.network`가 true인 source는 fingerprint가 없으므로 synthetic fingerprint로 매번 changed source 취급한다.
- 파일/DB source는 `fingerprintFile()`과 disk `SessionCache`를 비교해 unchanged source면 cached turns를 재사용한다.
- Parser dedup set은 기존 `seenKeys`와 unchanged cached call keys를 합쳐 changed source parse 중 중복 call 생성을 줄인다.
- Changed source parser가 yield한 `ParsedProviderCall[]`은 `canonicalizeProviderCallProject()`와 `providerCallsToCachedTurns()`를 거쳐 disk cache에 저장된다.
- Query-time에서도 `seenKeys`로 cross-provider/source 중복을 다시 제거하고, date range는 첫 call timestamp 기준으로 적용한다.

이 때문에 provider plugin의 책임은 “raw source에서 가능한 한 정확한 `ParsedProviderCall`을 yield”하는 것이고, caching, project/session rollup, classification은 core parser 쪽 책임으로 남는다.

## SQLite provider family

Cursor/OpenCode류 provider는 SQLite read-only wrapper를 공유한다. 현재 source는 DeepWiki의 “optional `better-sqlite3`” 설명과 달리 `node:sqlite` shim을 사용한다. `src/sqlite.ts`는 Node 내장 `node:sqlite`의 `DatabaseSync`를 lazy require하고, read-only DB wrapper와 `blobToText()`를 제공한다. Node 22/23의 SQLite ExperimentalWarning은 해당 warning만 한 번 가로채 조용히 처리한다. (`repos/codeburn/src/sqlite.ts:1-45`, `repos/codeburn/src/sqlite.ts:76-139`)

Generic SQLite provider parser는 `session`, `message`, `part` table을 기대한다. Session tree를 recursive CTE로 따라가 message/part를 읽고, assistant/model role message를 token/cost/tool data로 변환한다. 개별 message가 yield되지 않는 경우 session-level token row fallback도 있다. (`repos/codeburn/src/providers/sqlite-session-parser.ts:161-180`, `repos/codeburn/src/providers/sqlite-session-parser.ts:199-345`, `repos/codeburn/src/providers/sqlite-session-parser.ts:347-390`)

`discoverSqliteSessions()`는 provider config의 DB directory에서 prefix가 맞는 `.db` 파일을 찾고, top-level non-archived session row를 `SessionSource`로 만든다. (`repos/codeburn/src/providers/sqlite-session-parser.ts:394-445`)

## Provider examples

| Provider | Source shape | Source-verified behavior |
|---|---|---|
| `codex` | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | `session_meta` 첫 줄로 valid Codex file인지 확인하고 cwd를 project로 sanitize한다. Parser는 `readSessionLines(..., { largeLineAsBuffer: true })`로 큰 JSONL을 streaming 처리하고, `exec_command → Bash`, `read_file → Read`, `write_file/apply_patch → Edit`, `spawn_agent → Agent`로 tool 이름을 normalize한다. (`repos/codeburn/src/providers/codex.ts:31-41`, `repos/codeburn/src/providers/codex.ts:249-368`, `repos/codeburn/src/providers/codex.ts:603-631`) |
| `cursor` | OS별 Cursor `globalStorage/state.vscdb` + `workspaceStorage/*` | Global DB의 `cursorDiskKV`에서 `bubbleId:%`와 `agentKv:blob:%`를 읽고, workspace directory의 `workspace.json`/`composer.composerData`를 이용해 composerId를 workspace project에 매핑한다. Orphan composer catch-all source도 항상 만든다. (`repos/codeburn/src/providers/cursor.ts:79-107`, `repos/codeburn/src/providers/cursor.ts:300-340`, `repos/codeburn/src/providers/cursor.ts:680-816`) |
| `opencode` | XDG data dir 또는 `~/.local/share/opencode` 아래 `opencode*.db` | Generic SQLite parser를 config로 재사용한다. Model id는 provider prefix를 제거한 뒤 `getShortModelName()`으로 표시하고, `skill`, `patch` 같은 OpenCode built-in tool도 canonical tool name으로 map한다. (`repos/codeburn/src/providers/opencode.ts:8-21`, `repos/codeburn/src/providers/opencode.ts:23-66`) |
| `antigravity` | `.pb`/`.db` conversation files, statusline JSONL, local language server RPC | 여러 Antigravity app data roots를 scan하고, statusline events file도 source로 포함한다. Parser는 conversation file에서 cascade id/project path를 얻고, local server가 있으면 `GetAvailableModels`/`GetCascadeTrajectoryGeneratorMetadata` RPC로 usage metadata를 가져오며, 실패 시 cached cascade calls를 재사용한다. (`repos/codeburn/src/providers/antigravity.ts:19-45`, `repos/codeburn/src/providers/antigravity.ts:155-164`, `repos/codeburn/src/providers/antigravity.ts:476-532`, `repos/codeburn/src/providers/antigravity.ts:655-693`, `repos/codeburn/src/providers/antigravity.ts:990-1050`, `repos/codeburn/src/providers/antigravity.ts:1073-1100`) |

## Normalization boundary

Provider는 raw provider naming을 CodeBurn display layer에 맞춰 보정한다.

- Codex: `exec_command → Bash`, `read_file → Read`, `write_file/apply_diff/apply_patch → Edit`, `spawn_agent/close_agent/wait_agent → Agent`, `read_dir → Glob`. (`repos/codeburn/src/providers/codex.ts:31-41`, `repos/codeburn/tests/provider-registry.test.ts:75-89`)
- OpenCode: `bash → Bash`, `edit → Edit`, `task → Agent`, `skill → Skill`, `patch → Patch`; model은 `anthropic/claude-opus-...` 같은 provider prefix를 제거한 뒤 short name으로 표시한다. (`repos/codeburn/src/providers/opencode.ts:8-21`, `repos/codeburn/src/providers/opencode.ts:47-54`, `repos/codeburn/tests/provider-registry.test.ts:51-67`)
- Cursor: model display map이 `cursor-auto → Cursor (auto)`와 일부 model alias를 처리하지만, tool display는 현재 rawTool identity다. (`repos/codeburn/src/providers/cursor.ts:28-43`, `repos/codeburn/src/providers/cursor.ts:773-779`, `repos/codeburn/tests/provider-registry.test.ts:105-112`)
- Claude: test 기준 tool name은 identity로 유지되고 model id는 `claude-opus-4-6-... → Opus 4.6`, `claude-sonnet-4-6 → Sonnet 4.6`처럼 표시된다. (`repos/codeburn/tests/provider-registry.test.ts:69-95`)

## Current-source corrections vs DeepWiki

- DeepWiki의 core provider list는 현재 checkout보다 작고 오래됐다. 현재 core에는 `cline`, `codebuff`, `devin`, `ibm-bob`, `kimi`, `mistral-vibe`, `mux` 등이 포함되며 optional lazy provider에는 `forge`, `crush`, `warp`, `vercel-gateway`도 포함된다.
- DeepWiki가 optional dependency 예로 든 `better-sqlite3`는 현재 source의 SQLite path가 아니다. 현재는 `node:sqlite` wrapper(`src/sqlite.ts`)를 사용한다.
- `providers` export는 core provider만 담고, optional까지 포함한 전체 registry는 `getAllProviders()`를 await해야 한다.
- Cursor는 단순히 global `state.vscdb` 하나만 project로 취급하지 않고, `workspaceStorage/*`의 workspace mapping을 이용해 workspace별 source와 orphan source로 나눈다.
- Antigravity는 단순 `.pb` scan만이 아니라 statusline JSONL fallback/source와 local language server RPC/cache 경계를 함께 가진다.

관련 페이지: [[codeburn]], [[codeburn-codex-provider]], [[codeburn-data-ingestion-and-caching]], [[codeburn-domain-terminology]], [[codeburn-pricing-and-currency-resolution]], [[evidence-backed-analysis]].
