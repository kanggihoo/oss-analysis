---
title: CodeBurn Domain Terminology
created: 2026-06-10
updated: 2026-10-15
type: concept
tags: [open-source, project, developer-tools, architecture, evidence]
sources:
  - repos/codeburn/src/types.ts
  - repos/codeburn/src/providers/types.ts
  - repos/codeburn/src/providers/index.ts
  - repos/codeburn/src/classifier.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/session-cache.ts
  - repos/codeburn/src/behavioral-weight.ts
  - repos/codeburn/src/day-aggregator.ts
  - repos/codeburn/src/models.ts
  - repos/codeburn/src/main.ts
  - repos/codeburn/src/dashboard.tsx
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-turn-classification-engine.md
confidence: high
---
# CodeBurn Domain Terminology

검증 기준 checkout: repos/codeburn at 9a40cc603fcd194caca9daa8c5134a61ea7e0e2b (2026-10-15).

[[codeburn]] 코드를 읽을 때 반복해서 나오는 타입과 지표 용어를 현재 source 기준으로 정리한다. 분류 로직 자체는 [[codeburn-turn-classification-engine]], 입력 수집과 캐시는 [[codeburn-data-ingestion-and-caching]], provider 구조는 [[codeburn-provider-plugin-system]]을 본다.

## 1. 데이터 흐름 순서로 본 핵심 타입

수집 → turn 묶기 → 분류 → 세션 집계 → 프로젝트 집계 순서다. (코드 확인, 각 행의 근거 참조)

| 용어 | 한 줄 정의 | 근거 |
|---|---|---|
| `Provider` | AI 코딩 도구 하나(Claude Code, Codex 등)의 로그를 찾고 읽는 플러그인 객체. `discoverSessions()`, `createSessionParser()`, 표시명 resolver, 선택적 `probeRoots()`를 가진다. | `src/providers/types.ts:140-165` |
| `network` / `durableSources` | `Provider` 플래그. 전자는 디스크 파일 없이 API로 가져와 매번 재조회, 후자는 외부 프로세스가 오래된 기록을 지울 수 있어 캐시 항목을 지우지 않음. | `src/providers/types.ts:143-152` |
| `coreProviders` | 내장 provider 배열. 현재 32개(claude, codex, copilot, gemini, pi 등). | `src/providers/index.ts:200` |
| `SessionSource` | discovery가 찾은 분석 입력 단위(파일/DB 경로 + `project` + `provider`). Claude 설정 위치 구분용 `sourceKind`, copilot DB용 `retainWhilePresent` 등이 추가됨. | `src/providers/types.ts:4-26` |
| `ParsedProviderCall` | 비-Claude provider parser가 내보내는 평평한 call 레코드. 토큰 필드, `costUSD`, `tools`, `bashCommands`, `userMessage`, 선택적 `turnId`를 가진다. | `src/providers/types.ts:32-129` |
| `ParsedApiCall` | turn 안의 assistant API call 한 번. `usage: TokenUsage`, `costUSD`, `tools`, `skills`, `hasPlanMode`, `hasAgentSpawn`, `toolSequence` 등을 담는다. | `src/types.ts:111-187` |
| `ToolCall` | `toolSequence`의 원소. `{ tool, file?, command? }`로 retry 판정에 쓰인다. | `src/types.ts:189-193` |
| `ParsedTurn` | 사용자 메시지 하나 + 그 뒤 assistant call 목록. turn = 사용자 한 번 말하고 AI가 응답한 한 교환. | `src/types.ts:90-109` |
| `ClassifiedTurn` | `ParsedTurn` + `category`, `subCategory?`, `retries`, `hasEdits`, `projectContinuation?`. | `src/types.ts:210-219` |
| `TaskCategory` | turn의 작업 종류 13개 문자열 union. | `src/types.ts:195-208` |
| `CATEGORY_LABELS` | category → 화면 표시명(`feature`→`Feature Dev`, `git`→`Git Ops`). | `src/types.ts:403-417` |
| `SessionSummary` | 세션 하나의 집계. 비용/토큰 합계, `turns: ClassifiedTurn[]`, model/tool/MCP/bash/category/skill/subagent breakdown, PR·lineage 메타데이터. | `src/types.ts:256-371` |
| `ProjectSummary` | 프로젝트별 세션 묶음과 합계. `totalProxiedCostUSD`, `subagentAnchors`가 새로 있다. | `src/types.ts:373-396` |
| `CachedTurn` | 세션 캐시에 저장되는 turn 형태. category는 저장하지 않는다. | `src/session-cache.ts:97-114` |

Turn 생성 경로 두 가지 (코드 확인):
- Claude: `groupIntoTurns()`가 JSONL entry를 순회하며 텍스트가 있는 user entry마다 새 turn을 시작하고, assistant call이 없는 turn은 버린다. `src/parser.ts:1682-1720`
- 그 외 provider: `providerCallsToCachedTurns()`가 `sessionId + turnId`로 call을 묶고, `turnId`가 없으면 call 하나가 turn 하나가 된다. `src/parser.ts:2945-2975`

## 2. 토큰과 비용 용어

| 용어 | 한 줄 정의 | 근거 |
|---|---|---|
| `TokenUsage` | 표준 토큰 묶음: `inputTokens`, `outputTokens`, `cacheCreationInputTokens`, `cacheReadInputTokens`, `cachedInputTokens`, `reasoningTokens`, `webSearchRequests`. | `src/types.ts:3-11` |
| cache write / cache read | prompt cache에 새로 쓴 입력 토큰 / 캐시에서 읽은 입력 토큰. 세션 합계 `totalCacheWriteTokens`, `totalCacheReadTokens`. | `src/types.ts:6-7`, `src/types.ts:324-325` |
| `cacheCreationOneHourTokens` | Claude 1시간 TTL cache write 토큰(가격이 5분 TTL과 다름 — 추론). | `src/types.ts:126`, `src/parser.ts:1579` |
| `costUSD` | call 하나의 USD 비용. 캐시에서 읽을 때 저장 비용이 없으면 토큰으로 다시 계산한다. | `src/types.ts:115`, `src/parser.ts:3001` |
| `costFromBilling` / `fallbackCostUSD` | provider 자체 청구 기록에서 온 비용인지 / 카탈로그에 없는 모델일 때만 쓰는 도구 기록 비용. | `src/providers/types.ts:44-56` |
| `isEstimated` | 토큰 수 자체가 추정(내용 길이 기반 등)인 call. 합계는 바꾸지 않고 `totalEstimatedCostUSD`로 따로 표시. | `src/types.ts:142-147`, `src/types.ts:320` |
| `savingsUSD` | local 모델 call의 실제 비용은 0으로 두고, `savingsBaselineModel` 기준 가상 비용을 절약액으로 기록. | `src/types.ts:135-141`, `src/parser.ts:1322-1339` |
| `route` / `billing` | 결제 경로 id(`bedrock` 등) / 결제 방식 `BillingMode = 'metered' \| 'subscription'`. | `src/types.ts:178-186`, `src/models.ts:1803` |
| `nanoAiu` | Copilot 크레딧 단위. 1e9 nano-AIU = 1 credit = $0.01. | `src/types.ts:174-177` |

가격 해석 상세는 [[codeburn-pricing-and-currency-resolution]], 구독 플랜은 [[codeburn-subscription-plans-and-currency]].

## 3. 분류·효율 지표

| 용어 | 한 줄 정의 | 근거 |
|---|---|---|
| `retries` | 한 turn 안에서 같은 파일을 edit → (읽기 전용이 아닌) Bash 검증 → 다시 edit 한 횟수. | `src/classifier.ts:157-194` |
| `hasEdits` | turn의 어떤 call이든 `EDIT_TOOLS` 도구를 썼는지. | `src/classifier.ts:196-198` |
| edit turn | behavioral이면서 `hasEdits`인 turn. | `src/parser.ts:1893-1894` |
| one-shot turn | edit turn 중 `retries === 0`. | `src/parser.ts:1896`, `src/day-aggregator.ts:142` |
| one-shot rate | `oneShotTurns / editTurns`. edit turn이 0이면 표시 안 함. | `src/main.ts:747`, `src/dashboard.tsx:998` |
| `subCategory` | turn에서 처음 호출된 Skill 이름. category와 무관하게 skill이 있으면 설정되고 `skillBreakdown` 키가 된다. | `src/classifier.ts:218-219`, `src/parser.ts:1899-1911` |
| supplementary accounting | 비용·토큰은 실제지만 별도 요청으로 세지 않는 call(Copilot rollup 등). `supplementaryAccounting` 플래그. | `src/types.ts:164-170` |
| behavioral turn | supplementary가 아닌 call이 하나라도 있고 `projectContinuation`이 아닌 turn. 이것만 turn/edit/one-shot 수에 들어가고, 비용은 항상 category에 더해진다. | `src/behavioral-weight.ts:39-42`, `src/parser.ts:1885-1897` |
| `projectContinuation` | 한 turn의 call이 여러 프로젝트에 걸칠 때 첫 조각이 아닌 나머지 조각. `hasEdits: false`, `retries: 0`으로 강제. | `src/parser.ts:179-185` |
| `requestCount` | call 하나가 대표하는 요청 수(Vercel AI Gateway 일별 집계). `behavioralCallWeight()`로만 읽음. | `src/behavioral-weight.ts:25-29` |

## 4. 세션 관계 용어 (Claude 중심)

- sidechain / subagent: Claude가 `Agent`/`Task`로 띄운 하위 에이전트 transcript. `isSidechain`, `agentType`, `parentSessionId`, `agentId`로 표시되며 비용은 모든 합계에 그대로 포함된다. `src/types.ts:268-294` (코드 확인)
- `SessionLineage`: provider가 디스크에 명시적으로 기록한 부모-자식 관계만 담는다(`evidence: 'provider-recorded'`). 시간 근접성 추론은 금지. `src/types.ts:228-254` (코드 확인)
- PR attribution: `prRefs`(turn), `prLinks`(session), `prAttributionSource`로 PR별 비용을 나눈다. `src/types.ts:99-103`, `src/types.ts:263-266`, `src/types.ts:328-330` (코드 확인)

waste finding 용어(junk reads, duplicate reads 등)는 [[codeburn-optimization-engine]], 일별 집계 용어는 [[codeburn-day-aggregation-and-caching]], 리포트 명령은 [[codeburn-report-status-export-commands]], Codex 특이 필드는 [[codeburn-codex-provider]]를 본다.

## 미확인

- `cacheCreationOneHourTokens`가 가격 계산에서 정확히 어떻게 쓰이는지 (가격 노트 범위, 이 노트에서는 미확인).
- `coreProviders` 외에 `getAllProviders()`가 동적으로 추가하는 provider 범위 (`src/providers/index.ts:241`, 본문 미확인).
- `src/main.ts`, `src/dashboard.tsx`의 one-shot rate 계산은 grep 결과 줄만 확인, 주변 맥락은 미확인.
