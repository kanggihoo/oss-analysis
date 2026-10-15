---
title: CodeBurn Day Aggregation and Caching
created: 2026-06-10
updated: 2026-10-15
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence]
sources:
  - repos/codeburn/src/day-aggregator.ts
  - repos/codeburn/src/daily-cache.ts
  - repos/codeburn/src/usage-aggregator.ts
  - repos/codeburn/src/main.ts
  - repos/codeburn/src/cache-dir.ts
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
  - wiki/concepts/codeburn-pricing-and-currency-resolution.md
  - wiki/concepts/codeburn-turn-classification-engine.md
confidence: high
---
# CodeBurn Day Aggregation and Caching

검증 기준 checkout: repos/codeburn at 9a40cc603fcd194caca9daa8c5134a61ea7e0e2b (2026-10-15).

[[codeburn]]이 파싱된 `ProjectSummary[]`를 일별 bucket으로 접고, 과거 날짜를 `daily-cache.v75.json`에 봉인(seal)해 기간 조회를 빠르게 하는 방법을 정리한다. 원천 파싱과 session cache는 [[codeburn-data-ingestion-and-caching]], 비용 계산은 [[codeburn-pricing-and-currency-resolution]], category/turn 판정은 [[codeburn-turn-classification-engine]]를 본다.

## 용어
- **`DailyEntry`**: 하루 합계(cost, calls, sessions, tokens, edit/one-shot turn)와 `models`/`categories`/`providers`/`projects` 분해(daily-cache.ts:484-508).
- **`ProviderDaySlice`**: 하루 안의 provider별 조각. 병합·carry-forward의 단위.
- **watermark (`lastComputedDate`)**: 어디까지 과거가 파생되었는지 표시하는 날짜.
- **carried**: 원본 session 파일이 사라져 재파생할 수 없어 이전 캐시 값을 그대로 이어받은 day 표시(daily-cache.ts:503-507).
- **settle window**: 최근 `SETTLE_DAYS = 7`일. 아직 원본이 있어 재파생 결과를 신뢰하는 구간(daily-cache.ts:1446).

## aggregateProjectsIntoDays (day-aggregator.ts:57)
- 입력: `ProjectSummary[]`, `dateKeyFn`(기본 local 날짜 `dateKey`, tz 재파생 시 `dateKeyInTz`)(day-aggregator.ts:27-47).
- 내부 동작:
  - session은 `firstTimestamp` 날짜에 1회 집계. 여러 project로 쪼개진 session은 가장 이른 조각만 day/provider `sessions`를 올린다(day-aggregator.ts:85-110). 코드 확인.
  - **두 가지 bucket 규칙**: category/editTurns/oneShotTurns 같은 turn 단위 판정은 turn timestamp 날짜에, cost/calls/tokens/model/project/provider 수치는 **각 call 자신의 날짜**에 넣는다(day-aggregator.ts:111-133, 203). 코드 확인. 자정을 걸친 turn에서 일별 합이 기간 headline과 맞도록 하려는 것(주석 근거, 코드 확인).
  - turn의 call 수가 가장 많은 provider만 그 turn 수를 소유하고, cost는 등장한 모든 provider slice에 나눠 담는다(day-aggregator.ts:157-188). 코드 확인.
  - 보조 회계 call(copilot rollup 등)은 cost/tokens만 더하고 calls/turn 가중치는 0(`isBehavioralTurn`, `behavioralCallWeight`, day-aggregator.ts:135-141, 195-199). 코드 확인.
- 반환값: 날짜순 `DailyEntry[]`(day-aggregator.ts:274).

## buildPeriodDataFromDays (day-aggregator.ts:277)
- 입력: `DailyEntry[]`, label. 내부 동작: 합계·model·category를 단순 합산, cost 내림차순 정렬. 반환값: `PeriodData`(menubar-json 타입). 코드 확인.

## daily cache 파일
- `DAILY_CACHE_VERSION = 75`, 최소 지원 28(daily-cache.ts:364-365). 파일 `daily-cache.v75.json`을 `CODEBURN_CACHE_DIR`(기본 `~/.cache/codeburn`) 아래에 둔다(daily-cache.ts:429, 553-555; cache-dir.ts:11-14). 코드 확인.
- `DailyCache`(daily-cache.ts:510-547): `savingsConfigHash`, `tzKey`, `lastComputedDate`, `days`, `complete`, `watermarkTrusted`, `pendingRederive`. 코드 확인.
- `loadDailyCache`(daily-cache.ts:781): 현재 버전 파일을 읽어 마이그레이션, 실패하거나 없으면 `adoptOlderDailyCaches`로 이전 버전 파일들의 day를 합집합으로 이어받는다(:817). 코드 확인.
- `saveDailyCache`(daily-cache.ts:930): temp 파일 + fsync + rename 원자적 저장. 코드 확인.
- 보존 기간 `DAILY_CACHE_RETENTION_DAYS = 3650`(10년), 백필 창 `BACKFILL_DAYS = 365`(daily-cache.ts:1669-1677). 코드 확인.
- `PENDING_REDERIVE_PROVIDER_VERSIONS`: 회계 기준이 바뀐 provider(copilot 75, codex 43, cursor 71 등)에 한해 마이그레이션 후 첫 완전 재파생에서 call 수 감소를 허용(daily-cache.ts:385-417). 코드 확인.

## ensureCacheHydrated (daily-cache.ts:1703)
- 입력: `parseSessions(range)`, `aggregateDays`, config hash, `sessionComplete()`, 선택적 `aggregateDaysInTz`.
- 내부 동작 (`withDailyCacheLock` 안, daily-cache.ts:1662, 1729):
  1. 오늘 이후 날짜 entry 제거. 캐시는 어제까지만 저장한다(:1733-1742). 코드 확인.
  2. `watermarkTrusted`가 없는 캐시는 watermark를 실제 최신 day로 당긴다(:1760-1763). settle window 안의 residue-only day(호출 없이 category만 남은 날)가 있으면 그 전날로 당긴다(:1779-1791). 코드 확인.
  3. **전체 재파생**: config hash 변경, `complete !== true`, timezone 변경 중 하나면 `backfillStart`(365일 전)~어제를 파싱해 다시 만든다(:1811-1834). 기존 day를 버리지 않고 baseline으로 두며, 완전 파싱이면 `mergeDayEntries(fresh, baseline, carried=true, …)`, 부분 파싱이면 baseline 우선으로 빈 곳만 채운다(:1890-1892). tz 변경 시 지금까지 한 번 더 파싱해 자정을 넘어 이동한 turn을 baseline에서 뺀다(:1850-1876). 코드 확인.
  4. **증분 gap**: 아니면 `lastComputedDate + 1`부터 어제까지, 그리고 settle window(7일)도 함께 다시 파싱해 병합(:1931-1972). 이미 봉인된 날은 줄어들지 않는다(`sealedBefore`, :1537-1541, 1969-1971). 코드 확인.
  5. watermark 전진과 `complete`/`watermarkTrusted` 표시는 **session 파싱이 complete일 때만**(:1915-1920, 1979). 부분 파싱은 watermark를 유지해 다음 실행이 다시 채운다. 코드 확인.
- 반환값: 갱신된 `DailyCache`.
- 병합 guard: settle window 밖에서 fresh call 수가 baseline보다 적으면 원본이 사라진 것으로 보고 baseline 유지(`isPartialSurvival`, daily-cache.ts:1452-1454). 코드 확인.

## 기간 조회: buildDurablePeriod (usage-aggregator.ts:908)
- 입력: `PeriodInfo`(range, label), `opts`(provider, project/exclude, daysSelection).
- 내부 동작:
  - provider가 `all`이면 `hydrateCache()`(usage-aggregator.ts:226)로 daily cache를 채운다. 이때 parser는 `parseAllSessions(range, 'all', { includeAggregateOnly: true })`, hash는 savings+price override+flat-rate 설정 결합(usage-aggregator.ts:219-224). provider 탭이면 캐시를 그대로 load만 한다(:929). 코드 확인.
  - 기간 range를 한 번 파싱하고 today 조각은 같은 파싱에서 잘라 쓴다(range가 오늘을 포함할 때, :938-958). 코드 확인.
  - `unionDaysForPeriod`(usage-aggregator.ts:685): 캐시의 어제까지 day + 오늘 live day를 합친다. 같은 날짜에 live 파싱이 provider slice의 call을 더 많이 설명하면 그 slice가 이긴다(`'prefer-richer'`, :708-735). 코드 확인.
  - project 필터가 있으면 캐시 day도 project로 잘라내고, project 분해가 없는 옛 day 비용은 `unattributedCostUSD`로 따로 보고한다(:972-998). 코드 확인.
- 반환값: `DurablePeriod`. 호출처: `main.ts:520, 912, 1093, 1431-1432, 1470-1471`. 코드 확인.

## 설계 의도 (추론)
- session 원본은 provider가 지우는 휘발성 데이터라 daily cache가 장기 지출의 유일한 기록이 된다. 그래서 "재파생하되 버리지 않는다", "부분 파싱은 봉인하지 않는다", "봉인된 날은 줄지 않는다"가 반복되는 원칙이다. 추론(주석 근거 daily-cache.ts:1793-1805, 1670-1676).

## 관련
[[codeburn-domain-terminology]] · [[codeburn-provider-plugin-system]] · [[codeburn-codex-provider]] · [[codeburn-subscription-plans-and-currency]] · [[codeburn-optimization-engine]] · [[codeburn-report-status-export-commands]]

## 미확인
- `withDailyCacheLock`는 프로세스 내부 promise chain(daily-cache.ts:1660-1666)이다. 여러 프로세스가 동시에 daily cache를 쓸 때의 보호는 확인하지 못했다.
- `hydrateCache`의 백필 파싱(365일~어제)과 기간 파싱은 range가 달라 별개의 `parseAllSessions` 호출이다. 두 번째 호출이 싸게 끝나는 것은 session cache 재사용 덕분이라고 추론하며 실행으로 확인하지 않았다.
- `mergeDayEntries`(daily-cache.ts:1508) 본문의 `carried` 표시, `subtract` 적용 순서 세부.
- `detectPhantomSpend`, `withoutImportReplacedSlices`의 역할.
