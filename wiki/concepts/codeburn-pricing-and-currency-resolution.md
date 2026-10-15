---
title: CodeBurn Pricing and Currency Resolution
created: 2026-06-10
updated: 2026-10-15
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence]
sources:
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
  - wiki/concepts/codeburn-subscription-plans-and-currency.md
  - repos/codeburn/src/models.ts
  - repos/codeburn/src/currency.ts
  - repos/codeburn/src/config.ts
  - repos/codeburn/src/cache-dir.ts
  - repos/codeburn/src/fetch-utils.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/main.ts
  - repos/codeburn/scripts/bundle-litellm.mjs
confidence: high
---
# CodeBurn Pricing and Currency Resolution

검증 기준 checkout: repos/codeburn at 9a40cc603fcd194caca9daa8c5134a61ea7e0e2b (2026-10-15).

[[codeburn]]이 token 수를 USD 비용으로 바꾸는 방법(가격표 로드 → 모델 이름 해석 → 비용 공식)과, USD를 사용자 통화로 바꾸는 방법(환율 로드 → 표시 변환)을 정리한다. token/call이 만들어지는 앞단은 [[codeburn-data-ingestion-and-caching]], plan 예산 비교는 [[codeburn-subscription-plans-and-currency]], 용어는 [[codeburn-domain-terminology]]를 본다.

용어:
- `ModelCosts`: 한 모델의 token당 USD 단가 묶음(input/output/cache write/cache read/web search/fast 배수). `src/models.ts:10` (코드 확인)
- LiteLLM: 모델별 가격 JSON을 공개하는 오픈소스 프로젝트. CodeBurn은 그 GitHub raw JSON을 가격 원천으로 쓴다.
- Frankfurter: 환율 API. CodeBurn은 USD 기준 환율 하나만 받아온다.

## 1. 가격표 계층 (우선순위 순)

| 계층 | 위치 | 근거 |
|---|---|---|
| 사용자 `priceOverrides` (USD/1M tokens) | `~/.config/codeburn/config.json` | `src/config.ts:34`, `src/models.ts:793` (코드 확인) |
| 내장 강제 가격 `BUILTIN_PRICE_OVERRIDES` (composer-*, swe-2, deepseek-v3.2, kimi-k2.7-code-highspeed) | 코드 상수 | `src/models.ts:127-137`, 적용 `:230-235` (코드 확인) |
| live LiteLLM 데이터 (24h 디스크 캐시) | `litellm-pricing.json` | `src/models.ts:93-94`, `:296` (코드 확인) |
| 번들 snapshot (빌드 시 생성) | `src/data/litellm-snapshot.json` | `src/models.ts:6`, `:237-244` (코드 확인) |
| gap-fill (models.dev / OpenRouter, 빌드 시 생성) | `src/data/pricing-fallback.json` | `src/models.ts:7`, `:245-255`; `scripts/bundle-litellm.mjs:21-22` (코드 확인) |

- 프로세스 시작 시 `pricingCache`는 snapshot + 내장 강제 가격으로 이미 채워져 있다. `src/models.ts:257` (코드 확인)
- gap-fill은 `getModelCosts`의 마지막 소문자 fallback에서만 쓰여 정식 이름을 가리지 못한다. `src/models.ts:245-247`, `:278-292` (코드 확인)
- 캐시 경로는 `CODEBURN_CACHE_DIR` 또는 `~/.cache/codeburn`. `src/cache-dir.ts:12-13` (코드 확인)

## 2. `loadPricing()` — `src/models.ts:537`

- 입력: 없음(모듈 상태와 디스크 캐시 사용).
- 내부 동작:
  1. `loadCachedPricing()`: 캐시 파일의 `version`이 `CACHE_SCHEMA_VERSION`(현재 8)과 같고 24h 이내면 사용. `src/models.ts:110`, `:509-520` (코드 확인)
  2. 테스트용 `CODEBURN_PRICING_SNAPSHOT_ONLY`면 fetch 없이 snapshot만. `src/models.ts:547-551` (코드 확인)
  3. 아니면 `fetchAndCachePricing()`이 LiteLLM URL을 `fetchWithTimeout`(기본 8초)으로 받는다. `src/models.ts:467`, `src/fetch-utils.ts:6` (코드 확인)
  4. 받은 맵은 `mergeSnapshotFallbacks`로 snapshot의 빈 이름을 채우고 내장 강제 가격을 덮는다. `src/models.ts:522-527` (코드 확인)
  5. fetch 실패는 조용히 무시하고 초기 snapshot을 유지한다. `src/models.ts:553-558` (코드 확인)
- 반환값: `Promise<void>`. 결과는 모듈 전역 `pricingCache`에 들어간다(`setPricingCache` `:529`).

LiteLLM 항목 해석(`parseLiteLLMEntry` `:417`) 요점 (코드 확인):
- 단가는 `safePerTokenRate`로 음수/NaN 거부, $1/token 상한. `:305-309`
- cache write/read 단가가 없으면 input의 1.25배 / 0.1배로 채우고 `cacheWriteCostIsExplicit`로 표시. `:143-161`
- long-context tier(`*_above_<n>k_tokens`), fast 배수(`provider_specific_entry.fast` 또는 `_priority` 키 비율), Flex tier(`_flex` 키)를 함께 읽는다. `:315`, `:337-361`, `:398-415`
- `anthropic/claude-x` 같은 접두어 행은 접두어 없는 이름으로도 색인되며, 제조사 행이 reseller 행보다 우선. `:477-497`

서버 측(LiteLLM JSON의 실제 내용, 스키마 안정성)은 코드로 판단할 수 없다. 클라이언트는 `Record<string, LiteLLMEntry>` 형태의 JSON을 가정한다. `src/models.ts:469` (미확인: 서버 측)

## 3. 모델 이름 해석 — `getModelCosts(model)` `src/models.ts:1294`

- 입력: 세션 로그의 raw model id.
- 내부 동작(먼저 맞는 것이 이김, 코드 확인):
  1. `@...`와 `-YYYYMMDD` 접미어 제거(`withPrefix`), alias 적용(`resolveAlias` `:1109`, 사용자 alias가 내장보다 우선).
  2. 사용자 override 정확 일치 → alias된 bare 이름 → `withPrefix` → canonical → router 접두어 후보(`routedModelCandidates`) 순.
  3. override prefix → 가격표 prefix(긴 키 우선) → override 대소문자 무시 → 가격표/gap-fill 소문자 색인.
  4. 알려진 variant 접미어를 떼고 재귀 재시도.
- 반환값: `ModelCosts | null`. null이면 비용 0.

시간 의존 가격: `pricingModelAt(model, timestamp)`는 `codex-auto-review`, `kimi-for-coding`/`kimi-code`만 호출 날짜에 따라 다른 모델로 가격을 매긴다. `src/models.ts:1272-1281` (코드 확인)

## 4. 비용 공식 — `calculateCost(...)` `src/models.ts:1516`

- 입력: model, input/output/cache-creation/cache-read tokens, web search 횟수, `speed`(`standard|fast|flex`), 1시간 cache write tokens, provider.
- 내부 동작 (코드 확인):
  - 가격을 못 찾으면 프로세스당 1회 stderr 경고 후 0. `:1528-1540`
  - 음수/NaN token은 0으로 clamp. `:1543`
  - `flex`면 Flex 단가, prompt token 합이 임계값을 넘고 provider가 `TIERED_PRICING_PROVIDERS`(codex, antigravity, claude)면 long-context 단가로 교체(`tieredCostsFor` `:203`, 집합 `:194`).
  - non-Anthropic 모델에 명시적 cache write 단가가 없으면 input 단가로 과금. `:1511-1514`
  - 1시간 cache write는 5분 단가 × 1.6. `:112`, `:1560`
  - `fast`면 전체에 `fastMultiplier`.
- 반환값: USD `number`.

reasoning token 이중 과금 방지는 `billableOutputTokens`(`src/models.ts:65`)가 provider별로 output에 이미 포함됐는지 판단한다. (코드 확인) 세부는 [[codeburn-codex-provider]].

## 5. 비용은 저장값이 아니라 읽을 때 재계산

- 세션 캐시에서 call을 복원할 때 `cachedCallToApiCall`이 `calculateCost(pricingModelAt(...))`를 다시 호출한다. `src/parser.ts:2984` (코드 확인) → 가격표·alias·override가 바뀌면 캐시된 세션도 새 가격으로 보인다.
- 단, 도구가 직접 기록한 `call.costUSD`가 있으면 그것이 우선이고, 계산값이 0일 때만 `fallbackCostUSD`를 쓴다(`recordedCostFallback` `src/models.ts:1460`). `src/parser.ts:3001` (코드 확인)
- 상주 프로세스 무효화를 위해 `getPricingGenerationKey()`(`src/models.ts:588`)와 각종 `*ConfigHash()`가 있다. (코드 확인, 소비처 세부는 [[codeburn-day-aggregation-and-caching]])

## 6. 시작 시 설정 주입 — `preAction` `src/main.ts:558-583`

`readConfig()` 후 `setModelAliases`, `setPriceOverrides`, `setLocalModelSavings`, `setFlatRateModels`, `setFlatRateRemoved`, `setProxyPaths`를 호출하고 마지막에 `loadCurrency()`. (코드 확인)
- flat-rate 모델: 구독 상품이라 $0이 정답인 모델(`isFlatRateModel` `src/models.ts:1014`). 미가격 경고 대상에서 빠진다(`isExpectedFreeModel` `:1446`). (코드 확인)
- `loadPricing()`은 preAction이 아니라 각 명령이 호출한다(예: `src/main.ts:409`, `:518`, `:907`). (코드 확인)

## 7. 통화 — `src/currency.ts`

`loadCurrency()` `:139`
- 입력: config의 `currency: { code, symbol? }` (`src/config.ts:26-29`).
- 내부 동작: 설정이 없으면 USD로 리셋. 있으면 `getExchangeRate(code)` → 24h 이내 `exchange-rate.json` 캐시(`:76`) → 없으면 Frankfurter `?from=USD&to=<code>` fetch(`:15`, `:80-88`) → 실패 시 기한 무시하고 옛 캐시 → 그것도 없으면 null. `:113-136` (코드 확인)
- 환율은 0.0001~1,000,000 범위만 유효. `:18-27` (코드 확인)
- 반환값: `void`. 모듈 전역 `active = { code, rate, symbol }`. rate가 null이면 USD로 둔다(외화 기호 + USD 금액 혼용 방지). `:111-112`, `:150-154` (코드 확인)

변환 경계 (코드 확인):
- 저장·집계 비용은 항상 USD. `convertCost(usd)`(`:182`)는 반올림 없이 `usd * rate`만 하고, `formatCost(usd)`(`:192`)가 표시 시점에 통화 소수 자릿수로 반올림한다(JPY/KRW는 정수).
- `roundForActiveCurrency`(`:68`)는 export용 반올림.
- Frankfurter 응답 형태는 `{ rates: { [code]: number } }`로 가정한다. `:84-86` (서버 측 미확인)

## 미확인
- LiteLLM raw JSON과 Frankfurter API의 실제 가용성·응답 스키마·갱신 주기(서버 측).
- `BUILTIN_PRICE_OVERRIDES`·plan 가격 주석에 적힌 벤더 가격이 현재도 맞는지.
- `scripts/bundle-litellm.mjs`의 snapshot 생성 세부(필터 규칙)는 헤더와 URL만 확인.
- `getPricingGenerationKey`를 menubar/`serve`가 어떻게 소비하는지.
