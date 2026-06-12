---
title: CodeBurn Day Aggregation and Caching
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence, deepwiki]
sources:
  - artifacts/codeburn/deepwiki/pages-md/2.4-day-aggregation-and-caching.md
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
  - wiki/concepts/codeburn-pricing-and-currency-resolution.md
  - wiki/concepts/codeburn-turn-classification-engine.md
  - repos/codeburn/src/day-aggregator.ts
  - repos/codeburn/src/daily-cache.ts
  - repos/codeburn/src/usage-aggregator.ts
  - repos/codeburn/src/menubar-json.ts
  - repos/codeburn/src/export.ts
  - repos/codeburn/src/currency.ts
  - repos/codeburn/src/types.ts
confidence: high
---
# CodeBurn Day Aggregation and Caching

이 페이지는 [[codeburn]]이 이미 파싱된 `ProjectSummary` / `SessionSummary` / `ClassifiedTurn` 데이터를 일별 bucket으로 접고, 기간별 조회를 빠르게 하기 위해 `daily-cache.json`을 어떻게 유지하는지 정리한다. Raw log parsing과 session cache는 [[codeburn-data-ingestion-and-caching]], cost 계산은 [[codeburn-pricing-and-currency-resolution]], turn/category 산정은 [[codeburn-turn-classification-engine]]를 참조한다.

검증 기준 checkout: `repos/codeburn` at `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.

## 한 문장 요약
CodeBurn은 매번 모든 session file을 다시 파싱해서 기간별 chart를 만들지 않는다. 과거 날짜는 `DailyEntry[]`로 미리 접어 `daily-cache.json`에 저장하고, 조회 시에는 cache에 있는 historical days와 오늘만 새로 파싱한 today data를 합쳐 `PeriodData`를 만든다.

## 전체 흐름
```text
ProjectSummary[]
→ aggregateProjectsIntoDays()
→ DailyEntry[]
→ ensureCacheHydrated()
→ ~/.cache/codeburn/daily-cache.json
→ getDaysInRange(cache, start, end)
→ buildPeriodDataFromDays(days, label)
→ menubar/status/MCP payload
```

`usage-aggregator.ts`의 `hydrateCache()`는 `ensureCacheHydrated()`에 `parseAllSessions(range, 'all')`, `aggregateProjectsIntoDays`, `getLocalModelSavingsConfigHash()`를 넘긴다. 즉 daily cache는 all-provider historical summary를 빠르게 만들기 위한 layer다. (`repos/codeburn/src/usage-aggregator.ts:55-73`)

## 1. `DailyEntry`가 저장하는 것
`DailyEntry`는 하루치 cost/token/call/session/category/model/provider summary다. 현재 source 기준 field는 다음이다.

| Field group | 내용 | Evidence |
|---|---|---|
| scalar totals | `date`, `cost`, `savingsUSD`, `calls`, `sessions`, token totals, `editTurns`, `oneShotTurns` | `repos/codeburn/src/daily-cache.ts:18-29` |
| `models` | model별 calls/cost/savings/token totals | `repos/codeburn/src/daily-cache.ts:30-38` |
| `categories` | category별 turns/cost/savings/editTurns/oneShotTurns | `repos/codeburn/src/daily-cache.ts:39` |
| `providers` | provider별 calls/cost/savings | `repos/codeburn/src/daily-cache.ts:40` |

`DailyCache`는 `{ version, savingsConfigHash, lastComputedDate, days }` 구조다. `savingsConfigHash`는 `localModelSavings` mapping이 바뀌면 historical savings를 다시 계산해야 하기 때문에 저장된다. (`repos/codeburn/src/daily-cache.ts:43-51`)

## 2. 일별 aggregation rule
`aggregateProjectsIntoDays(projects)`는 project → session → turn → assistant call을 순회하며 날짜별 bucket을 만든다. (`repos/codeburn/src/day-aggregator.ts:29-101`)

| Entity / metric | 날짜 귀속 방식 | Evidence |
|---|---|---|
| session count | `session.firstTimestamp`의 날짜에 `sessions += 1` | `repos/codeburn/src/day-aggregator.ts:37-40` |
| turn category/edit metrics | turn의 첫 assistant call timestamp 날짜에 귀속 | `repos/codeburn/src/day-aggregator.ts:42-61` |
| call cost/token/provider/model metrics | 각 assistant call의 own timestamp 날짜에 귀속 | `repos/codeburn/src/day-aggregator.ts:63-95` |

이 차이가 중요하다. 하나의 turn 안에 여러 assistant call이 있고 날짜가 넘어가면, turn/category metric은 첫 assistant call 날짜에 놓이지만 cost/token은 call timestamp별로 더 세밀하게 분산될 수 있다.

## 3. 기간별 rollup
`buildPeriodDataFromDays(days, label)`은 여러 `DailyEntry`를 한 기간 summary인 `PeriodData`로 접는다. 합산 대상은 cost/savings/calls/sessions/token totals이고, category/model breakdown은 cost descending으로 정렬된다. (`repos/codeburn/src/day-aggregator.ts:103-154`, `repos/codeburn/src/menubar-json.ts:1-24`)

이 함수는 이미 만들어진 daily buckets만 입력으로 받으므로, "지난 30일", "이번 달", "최근 6개월" 같은 기간 조회를 raw session parsing 없이 빠르게 계산할 수 있다.

## 4. Daily cache 저장 위치와 versioning
Daily cache 기본 경로는 다음이다.

```text
${CODEBURN_CACHE_DIR:-~/.cache/codeburn}/daily-cache.json
```

근거: `repos/codeburn/src/daily-cache.ts:54-60`.

현재 source 기준 version은 `8`이고, minimum supported version도 `8`이다. DeepWiki page의 version `4` 설명은 현재 checkout 기준으로 stale하다. Version 8은 local-model savings가 daily rollup에 포함되면서 도입된 구조다. (`repos/codeburn/src/daily-cache.ts:8-16`)

`loadDailyCache()`는 version이 supported range이면 `migrateDays()`로 missing field를 채워 현재 `DailyCache`로 올리고, version이 맞지 않으면 old cache를 `.v<version>.bak`으로 best-effort backup한 뒤 empty cache로 시작한다. (`repos/codeburn/src/daily-cache.ts:66-121`)

## 5. Hydration: 필요한 gap만 다시 파싱한다
`ensureCacheHydrated()`는 cache와 raw provider logs 사이를 동기화한다. 핵심은 오래된 history 전체를 매번 다시 만들지 않고 gap만 backfill하는 것이다. (`repos/codeburn/src/daily-cache.ts:199-253`)

흐름:

```text
loadDailyCache()
→ savingsConfigHash가 다르면 cached days 전체 discard
→ yesterday 이상 날짜가 cache에 있으면 제거
→ gapStart = lastComputedDate 다음날 또는 오늘-365일
→ gapStart <= yesterdayEnd 이면 그 기간만 parseSessions(range)
→ aggregateDays(gapProjects)
→ addNewDays()
→ saveDailyCache()
```

현재 source는 `BACKFILL_DAYS = 365`, `DAILY_CACHE_RETENTION_DAYS = 730`이다. 즉 최초/재수화는 기본 1년 backfill이고, cache file은 2년 retention window 바깥의 old entries를 prune한다. (`repos/codeburn/src/daily-cache.ts:188-193`, `repos/codeburn/src/daily-cache.ts:145-174`)

## 6. 오늘/어제 처리
Daily cache는 안정된 과거 history용이다. `ensureCacheHydrated()`는 cache에 yesterday 이상 날짜가 있으면 `date < yesterdayStr`만 남긴다. 즉 yesterday와 today는 session file이 계속 쓰이는 중일 수 있으므로 stale cache를 쓰지 않게 한다. (`repos/codeburn/src/daily-cache.ts:208-234`)

`buildMenubarPayloadForRange()`는 all-provider 조회에서 historical days를 cache에서 가져오고, today는 `parseAllSessions(todayRange, 'all')`로 새로 파싱한 뒤 `aggregateProjectsIntoDays()`로 만든 today days를 합친다. (`repos/codeburn/src/usage-aggregator.ts:94-145`)

## 7. 저장 안전성
`saveDailyCache()`는 final file에 직접 쓰지 않는다.

```text
daily-cache.json.<random>.tmp
→ write JSON
→ handle.sync()
→ close
→ rename(temp, final)
```

근거: `repos/codeburn/src/daily-cache.ts:124-143`.

`withDailyCacheLock()`은 module-level promise chain으로 같은 process 안의 daily cache 작업을 직렬화한다. 다만 이 lock은 file lock이 아니라 process-local lock이다. 여러 process가 동시에 실행될 수 있는 상황에서 최종 파일 손상을 줄이는 핵심 장치는 temp file + fsync + atomic rename이다. (`repos/codeburn/src/daily-cache.ts:180-186`)

## 8. Menubar/status/MCP에서 cache를 쓰는 방식
All-provider period 조회는 daily cache path를 적극 사용한다.

- `hydrateCache()`로 historical cache를 준비한다.
- range start/end 문자열로 `getDaysInRange(cache, start, historicalEnd)`를 가져온다.
- today가 range에 포함되면 fresh today days를 붙인다.
- `buildPeriodDataFromDays()`로 current period payload를 만든다.

근거: `repos/codeburn/src/usage-aggregator.ts:127-145`.

Provider filter가 `all`이 아닌 경우에는 `loadDailyCache()`만 하고, 해당 provider의 `parseAllSessions(periodInfo.range, pf)`를 직접 수행해 `buildPeriodData()`로 period data를 만든다. 즉 provider-specific period view는 all-provider daily cache만으로 해결하지 않는다. (`repos/codeburn/src/usage-aggregator.ts:147-164`)

## 9. Export와의 관계
`export.ts`도 daily/activity/model CSV/JSON row를 만들지만, 현재 `buildDailyRows()`는 `DailyCache`를 직접 읽는 path가 아니라 전달받은 `ProjectSummary[]`에서 row를 만든다. Cost fields는 [[codeburn-pricing-and-currency-resolution]]에서 설명한 active currency conversion을 거쳐 표시된다. CSV cell은 `=`, `+`, `-`, `@`, tab, carriage return으로 시작하면 single quote를 붙여 formula injection을 막는다. (`repos/codeburn/src/export.ts:9-14`, `repos/codeburn/src/export.ts:48-83`)

## Current-source corrections vs DeepWiki
- DeepWiki는 `DAILY_CACHE_VERSION`을 4로 설명하지만 현재 source는 version 8, minimum supported version 8이다.
- DeepWiki의 "Lock Chain prevents concurrent CLI/Menubar corruption" 설명은 current source 기준으로는 process-local 직렬화로 좁혀 말해야 한다. Cross-process safety는 atomic temp write/rename이 담당한다.
- Daily cache path는 `CODEBURN_CACHE_DIR` override를 존중한다.
- Export daily rows는 daily-cache file을 직접 읽는 layer가 아니라 `ProjectSummary[]`를 flat rows로 변환하는 별도 reporting path다.

관련 페이지: [[codeburn]], [[codeburn-data-ingestion-and-caching]], [[codeburn-pricing-and-currency-resolution]], [[codeburn-turn-classification-engine]], [[evidence-backed-analysis]].
