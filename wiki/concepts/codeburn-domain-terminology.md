---
title: CodeBurn Domain Terminology
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [open-source, project, developer-tools, architecture, evidence]
sources:
  - artifacts/codeburn/deepwiki/pages-md/1.2-key-concepts-and-terminology.md
  - deepwiki-ko/codeburn/1.2-key-concepts-and-terminology.md
  - repos/codeburn/src/types.ts
  - repos/codeburn/src/providers/types.ts
  - repos/codeburn/src/providers/index.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/classifier.ts
  - repos/codeburn/src/optimize.ts
  - repos/codeburn/src/config.ts
  - repos/codeburn/src/plan-usage.ts
confidence: high
---

# CodeBurn Domain Terminology

이 페이지는 DeepWiki의 CodeBurn 용어 설명을 출발점으로 삼되, 현재 local checkout `repos/codeburn`의 실제 TypeScript 소스에서 확인한 용어만 정리한다. DeepWiki는 [[deepwiki-first-baseline]]에 해당하는 외부 baseline이고, 아래 정의는 [[evidence-backed-analysis]] 기준으로 source path를 붙인 source-verified 메모다.

검증 기준 checkout: `repos/codeburn` at `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.

## Core entities

| Term | Source-verified meaning | Primary evidence |
|---|---|---|
| `Provider` | AI coding tool별 session discovery/parsing plugin abstraction. 각 provider는 `name`, `displayName`, model/tool display name resolver, `discoverSessions()`, `createSessionParser()`를 제공한다. | `repos/codeburn/src/providers/types.ts:38-48` |
| `SessionSource` | provider discovery 단계에서 발견된 분석 입력 단위. `path`, `project`, `provider`를 담는다. | `repos/codeburn/src/providers/types.ts:3-7` |
| Provider registry | `coreProviders`와 dynamic loader를 합쳐 전체 provider 목록을 만들고, `discoverAllSessions()`가 각 provider의 `discoverSessions()` 결과를 모은다. | `repos/codeburn/src/providers/index.ts:155-186` |
| `SessionSummary` | 하나의 session에 대한 집계 모델. cost, savings, token totals, API call count, classified turns, model/tool/MCP/bash/category/skill/subagent breakdown을 포함한다. | `repos/codeburn/src/types.ts:126-156`, `repos/codeburn/src/parser.ts:1263-1390` |
| `ParsedTurn` | 사용자 메시지 하나와 그 뒤 assistant API call sequence를 묶는 대화 원자 단위. | `repos/codeburn/src/types.ts:65-70`, `repos/codeburn/src/parser.ts:1166-1208` |
| `ParsedApiCall` | 한 turn 안의 단일 provider/model call. token usage, cost, tools, MCP tools, skills, subagent metadata, plan mode, bash commands, deduplication key, optional tool sequence 등을 보존한다. | `repos/codeburn/src/types.ts:72-96`, `repos/codeburn/src/parser.ts:1080-1139` |
| `ClassifiedTurn` | `ParsedTurn`에 `category`, optional `subCategory`, `retries`, `hasEdits`를 더한 enriched turn. | `repos/codeburn/src/types.ts:119-124`, `repos/codeburn/src/classifier.ts:193-217` |
| `TaskCategory` | turn 의도를 나타내는 enum-like string union. 현재 `coding`, `debugging`, `feature`, `refactoring`, `testing`, `exploration`, `planning`, `delegation`, `git`, `build/deploy`, `conversation`, `brainstorming`, `general`을 포함한다. | `repos/codeburn/src/types.ts:104-117`, `repos/codeburn/src/types.ts:178-192` |

## Token and cost vocabulary

| Term | Meaning | Primary evidence |
|---|---|---|
| `TokenUsage` | input/output/cache/reasoning/web-search token fields의 canonical shape. | `repos/codeburn/src/types.ts:1-9` |
| Input Tokens | model에 들어간 토큰 수. | `repos/codeburn/src/types.ts:2` |
| Output Tokens | model이 생성한 토큰 수. | `repos/codeburn/src/types.ts:3` |
| Cache Creation / Cache Write | prompt cache에 새로 기록된 input token 수. `SessionSummary.totalCacheWriteTokens`로 합산된다. | `repos/codeburn/src/types.ts:4`, `repos/codeburn/src/parser.ts:1321-1324` |
| Cache Read | prompt cache에서 읽은 input token 수. `SessionSummary.totalCacheReadTokens`로 합산된다. | `repos/codeburn/src/types.ts:5`, `repos/codeburn/src/parser.ts:1321-1324` |
| Cached Input Tokens | provider가 별도로 보고하는 cached input token field. | `repos/codeburn/src/types.ts:6`, `repos/codeburn/src/providers/types.ts:20` |
| Reasoning Tokens | reasoning-capable model의 내부 reasoning token field. | `repos/codeburn/src/types.ts:7`, `repos/codeburn/src/providers/types.ts:21` |
| `costUSD` | 각 `ParsedApiCall`의 USD 비용. Claude parser는 `calculateCost()` 결과를 `costUSD`에 넣는다. | `repos/codeburn/src/types.ts:76`, `repos/codeburn/src/parser.ts:1099-1108` |
| `savingsUSD` / local savings | local model call을 실제 비용 0으로 유지하면서, baseline paid model이었다면 발생했을 비용을 counterfactual savings로 추적하는 optional field. | `repos/codeburn/src/types.ts:89-96`, `repos/codeburn/src/config.ts:39-44` |

## Classification metrics

| Term | Source-verified meaning | Primary evidence |
|---|---|---|
| Turn classification | tool pattern이 있으면 `classifyByToolPattern()` → `refineByKeywords()` 경로를 타고, tool이 없거나 pattern이 없으면 `classifyConversation()`으로 분류한다. | `repos/codeburn/src/classifier.ts:60-94`, `repos/codeburn/src/classifier.ts:119-153`, `repos/codeburn/src/classifier.ts:193-217` |
| Tool heuristics | edit/read/bash/task/search/MCP/Skill tool 집합을 기준으로 coding, exploration, planning, delegation 등을 1차 판정한다. | `repos/codeburn/src/classifier.ts:18-22`, `repos/codeburn/src/classifier.ts:60-94` |
| Retry | tool sequence에서 같은 file에 대해 edit → bash verify → edit 패턴이 재등장하면 retry로 센다. | `repos/codeburn/src/classifier.ts:156-187` |
| One-shot turn | edit가 있었고 `retries === 0`인 classified turn. `categoryBreakdown[category].oneShotTurns`에 누적되며, 실무적으로 one-shot rate는 edit turn 대비 one-shot turn 비율로 해석하는 것이 안전하다. | `repos/codeburn/src/parser.ts:1291-1301` |
| `hasEdits` | turn 안 assistant call tool 목록에 edit tool이 있는지 여부. | `repos/codeburn/src/classifier.ts:189-190`, `repos/codeburn/src/classifier.ts:209` |
| `subCategory` | category가 `general`이고 Skill tool 사용 정보가 있을 때 첫 skill name으로 채워지는 optional field. | `repos/codeburn/src/classifier.ts:211-214` |

## Waste and optimization terms

| Term | Current implementation meaning | Primary evidence |
|---|---|---|
| Waste finding | `codeburn optimize` 계열이 감지하는 비용/토큰 낭비 후보. 결과는 impact, estimated token savings, fix action, trend 등을 담는다. | `repos/codeburn/src/optimize.ts` |
| Junk Reads | generated/dependency directory 같은 “코드가 아닌” 경로를 읽은 횟수가 threshold 이상이면 감지한다. 현재 구현의 title은 `Claude is reading build/dependency folders`다. | `repos/codeburn/src/optimize.ts:486-532` |
| Duplicate Reads | 같은 session/project 안에서 같은 file을 여러 번 읽은 extra reads를 합산한다. Junk path는 제외한다. | `repos/codeburn/src/optimize.ts:535-570` |
| Cache Bloat / large session warmup | API call들의 `cacheCreationTokens` median이 project/session 기반 baseline의 1.4배 이상이면 “Session warmup is unusually large”로 감지한다. | `repos/codeburn/src/optimize.ts:1577-1646` |
| Ghost Agents | `~/.claude/agents/*.md`에 정의됐지만 해당 기간의 `Agent`/`Task` call에서 호출되지 않은 custom agent를 찾는다. | `repos/codeburn/src/optimize.ts:1668-1696` |
| Ghost Skills / Commands | Claude skills/commands도 유사하게 “정의됐지만 호출되지 않은” 항목을 찾아 tool/schema/token overhead 후보로 본다. | `repos/codeburn/src/optimize.ts:1698-1744` |

## Plan and budget terms

| Term | Source-verified meaning | Primary evidence |
|---|---|---|
| `Plan` | subscription/budget tracking 단위. `id`, `monthlyUsd`, `provider`, optional `resetDay`, `setAt`을 갖는다. | `repos/codeburn/src/config.ts:7-16` |
| `PlanProvider` | plan scope. 현재 `claude`, `codex`, `cursor`, `all` 중 하나다. | `repos/codeburn/src/config.ts:7-8` |
| Reset day | billing cycle 시작일. 구현상 1–28 사이로 clamp한다. | `repos/codeburn/src/plan-usage.ts:23-44` |
| Projected month spend | 현재 기간의 지출에 trailing 7일 daily cost median과 남은 일수를 곱해 더한다. | `repos/codeburn/src/plan-usage.ts:71-108` |
| Plan status | monthly budget 대비 사용률이 100% 초과면 `over`, 80% 이상이면 `near`, 그 외 `under`. | `repos/codeburn/src/plan-usage.ts:7-20`, `repos/codeburn/src/plan-usage.ts:110-129` |

## Evidence boundary

- 이 페이지는 용어 사전이므로 CodeBurn의 전체 architecture report를 대체하지 않는다.
- DeepWiki 원문/번역본은 `artifacts/codeburn/deepwiki/pages-md/1.2-key-concepts-and-terminology.md`와 `deepwiki-ko/codeburn/1.2-key-concepts-and-terminology.md`에 보존되어 있다.
- source-verified 정의는 현재 checkout의 파일 구조와 line range를 기준으로 한다. 향후 CodeBurn이 빠르게 변경되면 이 페이지의 line range와 provider 목록은 재검증이 필요하다.

## Related pages

- [[deepwiki-first-baseline]]
- [[evidence-backed-analysis]]
- [[workspace-boundaries]]
