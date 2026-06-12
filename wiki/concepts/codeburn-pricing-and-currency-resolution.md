---
title: CodeBurn Pricing and Currency Resolution
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence, deepwiki]
sources:
  - artifacts/codeburn/deepwiki/pages-md/2.3-pricing-and-cost-calculation.md
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
  - wiki/concepts/codeburn-turn-classification-engine.md
  - repos/codeburn/package.json
  - repos/codeburn/scripts/bundle-litellm.mjs
  - repos/codeburn/src/models.ts
  - repos/codeburn/src/currency.ts
  - repos/codeburn/src/config.ts
  - repos/codeburn/src/fetch-utils.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/session-cache.ts
  - repos/codeburn/src/daily-cache.ts
  - repos/codeburn/src/main.ts
confidence: high
---
# CodeBurn Pricing and Currency Resolution

이 페이지는 [[codeburn]]이 token 사용량을 USD 비용으로 바꾸기 위해 model price 정보를 어디서 가져오고, 환율 정보를 어디서 가져오며, 각각 어디에 저장하는지 정리한다. 앞단에서 token/call/turn이 만들어지는 과정은 [[codeburn-data-ingestion-and-caching]], turn category와 command breakdown은 [[codeburn-turn-classification-engine]]를 참조한다.

검증 기준 checkout: `repos/codeburn` at `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.

## 전체 그림

```text
build time
→ scripts/bundle-litellm.mjs
→ LiteLLM + manual entries → src/data/litellm-snapshot.json
→ models.dev + OpenRouter gap-fill → src/data/pricing-fallback.json

runtime
→ loadPricing()
→ ~/.cache/codeburn/litellm-pricing.json 이 24h 이내면 사용
→ 아니면 LiteLLM GitHub JSON fetch 후 cache 저장
→ 실패하면 bundled snapshot/fallback 사용
→ calculateCost()가 token × model rate로 costUSD 계산
→ ParsedApiCall / session-cache / daily-cache / reports에 USD 기준으로 누적

currency display
→ codeburn currency KRW 같은 config는 ~/.config/codeburn/config.json에 저장
→ loadCurrency()가 Frankfurter API에서 USD→KRW 환율 fetch
→ ~/.cache/codeburn/exchange-rate.json에 24h cache
→ 내부 costUSD는 유지하고 표시/export 단계에서 active currency로 변환
```

## 1. Build-time bundled pricing snapshot

CodeBurn은 release/build 시점에 `scripts/bundle-litellm.mjs`를 실행해 bundled pricing data를 만든다. `package.json`의 `build` script도 `node scripts/bundle-litellm.mjs && tsup ...` 순서다. (`repos/codeburn/package.json:13-16`)

Bundler의 입력 source는 네 종류다.

| Source | URL / 위치 | 용도 | 저장 위치 |
|---|---|---|---|
| LiteLLM | `https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json` | primary provider list price | `src/data/litellm-snapshot.json` |
| `MANUAL_ENTRIES` | `scripts/bundle-litellm.mjs` 내부 | LiteLLM에 아직 없는 hand-curated primary overrides | `src/data/litellm-snapshot.json` |
| models.dev | `https://models.dev/api.json` | first-party maker official price gap-fill | `src/data/pricing-fallback.json` |
| OpenRouter | `https://openrouter.ai/api/v1/models` | last-resort resale/backstop price | `src/data/pricing-fallback.json` |

근거: `repos/codeburn/scripts/bundle-litellm.mjs:5-27`, `repos/codeburn/scripts/bundle-litellm.mjs:39-47`, `repos/codeburn/scripts/bundle-litellm.mjs:118-168`.

중요한 설계는 primary snapshot과 fallback을 분리한다는 점이다. `litellm-snapshot.json`은 exact/canonical/prefix lookup에 쓰이고, `pricing-fallback.json`은 정상 lookup이 모두 실패한 뒤 마지막으로만 consult된다. 이렇게 해서 OpenRouter 같은 reseller 가격이 canonical provider 가격을 shadow하지 않게 한다. (`repos/codeburn/scripts/bundle-litellm.mjs:14-19`)

## 2. Runtime model pricing cache

Runtime에서는 `src/models.ts`가 `src/data/litellm-snapshot.json`과 `src/data/pricing-fallback.json`을 import한다. Process 시작 시 `pricingCache`는 bundled snapshot으로 초기화된다. (`repos/codeburn/src/models.ts:1-5`, `repos/codeburn/src/models.ts:61-82`)

`loadPricing()`의 흐름은 다음과 같다.

```text
loadCachedPricing()
→ ~/.cache/codeburn/litellm-pricing.json 이 있고 24h 이내면 사용
→ cached pricing에 bundled snapshot fallback merge
→ cache miss/stale이면 LiteLLM GitHub JSON fetch
→ fetch 성공 시 ~/.cache/codeburn/litellm-pricing.json 저장
→ fetch 실패 시 process 초기 bundled snapshot 유지
```

Runtime live pricing의 fetch URL은 LiteLLM GitHub raw JSON 하나다. models.dev/OpenRouter는 runtime fetch가 아니라 build-time fallback generation에서만 쓰인다. (`repos/codeburn/src/models.ts:30-32`, `repos/codeburn/src/models.ts:153-181`, `repos/codeburn/src/models.ts:183-217`)

Runtime pricing cache path는 다음과 같다.

```text
${CODEBURN_CACHE_DIR:-~/.cache/codeburn}/litellm-pricing.json
```

근거: `repos/codeburn/src/models.ts:119-126`.

Cache file payload는 `{ timestamp, data }` 형태이며 TTL은 24시간이다. (`repos/codeburn/src/models.ts:31`, `repos/codeburn/src/models.ts:174-188`)

## 3. Model name resolution 순서

Raw provider log의 model string은 provider마다 다르기 때문에 `getModelCosts()`가 여러 단계로 canonicalize한다.

1. `modelAliases` user config가 있으면 built-in alias보다 우선한다.
2. `BUILTIN_ALIASES`로 provider-specific 이름을 canonical LiteLLM 이름으로 바꾼다.
3. provider prefix, date suffix, `@pin`을 정리한 exact/canonical key를 `pricingCache`에서 찾는다.
4. longest-prefix match를 시도한다.
5. 마지막으로 lowercase index에서 bundled fallback + gap-fill을 찾는다.
6. 그래도 없으면 `null`이고 `calculateCost()`는 cost를 0으로 처리한다.

근거: `repos/codeburn/src/models.ts:326-332`, `repos/codeburn/src/models.ts:449-500`, `repos/codeburn/src/models.ts:537-562`.

User alias와 local-model savings, currency preference는 모두 config file에 들어간다. 기본 config path는 다음과 같다.

```text
~/.config/codeburn/config.json
```

근거: `repos/codeburn/src/config.ts:22-56`, `repos/codeburn/src/config.ts:58-85`.

## 4. Cost 계산 공식

`calculateCost()`는 USD 기준 비용만 계산한다. 입력은 model, input/output token, cache write/read token, web search request, speed, 1-hour cache creation token이다. (`repos/codeburn/src/models.ts:537-583`)

공식은 개념적으로 다음과 같다.

```text
multiplier × (
  inputTokens × inputCostPerToken
  + outputTokens × outputCostPerToken
  + 5mCacheWriteTokens × cacheWriteCostPerToken
  + 1hCacheWriteTokens × cacheWriteCostPerToken × 1.6
  + cacheReadTokens × cacheReadCostPerToken
  + webSearchRequests × 0.01
)
```

Cache write/read 단가가 upstream entry에 없으면 `buildCosts()`가 write=1.25×input, read=0.1×input으로 보정한다. Web search는 request당 `$0.01`이다. (`repos/codeburn/src/models.ts:30-53`, `repos/codeburn/src/models.ts:140-150`)

## 5. 계산된 cost는 어디에 저장되나

Model pricing JSON 자체와 계산 결과 저장 위치는 다르다.

| 대상 | 저장 위치 / 구조 | 의미 |
|---|---|---|
| Live LiteLLM pricing cache | `~/.cache/codeburn/litellm-pricing.json` 또는 `CODEBURN_CACHE_DIR/litellm-pricing.json` | 24h runtime model price cache |
| Bundled primary snapshot | `repos/codeburn/src/data/litellm-snapshot.json` | offline primary price fallback |
| Bundled gap-fill fallback | `repos/codeburn/src/data/pricing-fallback.json` | models.dev/OpenRouter last-resort prices |
| Per-call computed USD | `ParsedApiCall.costUSD` / `CachedCall.costUSD` | provider call별 계산된 USD cost |
| Parsed session cache | `~/.cache/codeburn/session-cache.json` | compact turns와 call cost 저장 |
| Daily aggregate cache | `~/.cache/codeburn/daily-cache.json` | 날짜별 aggregate cost/savings 저장 |

Claude parser와 provider parser들은 token을 읽은 뒤 `calculateCost()`를 호출해 `costUSD`를 만든다. Claude path는 `parseApiCall()`에서, non-Claude provider들은 각 provider parser에서 호출한다. (`repos/codeburn/src/parser.ts:1075-1139`, `repos/codeburn/src/providers/mux.ts:220-241`, `repos/codeburn/src/providers/forge.ts:197-215`)

`CachedCall`에도 `costUSD`가 optional field로 들어가므로 session cache가 parsed turn과 cost를 함께 보존할 수 있다. (`repos/codeburn/src/session-cache.ts:22-37`)

## 6. Currency preference와 환율 cache

CodeBurn 내부 계산은 USD 기준이다. 사용자가 표시 통화를 바꾸면 `codeburn currency KRW` 같은 command가 config에 currency code/symbol을 저장한다. (`repos/codeburn/src/main.ts:661-709`)

Currency config 저장 위치:

```text
~/.config/codeburn/config.json
```

저장되는 형태:

```json
{
  "currency": {
    "code": "KRW",
    "symbol": "₩"
  }
}
```

`loadCurrency()`는 config를 읽고, USD가 아니면 `getExchangeRate(code)`를 통해 환율을 얻는다. 환율 source는 Frankfurter API다.

```text
https://api.frankfurter.app/latest?from=USD&to=<CODE>
```

환율 cache path:

```text
~/.cache/codeburn/exchange-rate.json
```

주의: 현재 `currency.ts`의 exchange-rate cache는 `CODEBURN_CACHE_DIR` override를 쓰지 않고 `homedir()/.cache/codeburn`에 고정되어 있다. 이는 `models.ts`의 pricing cache와 다른 점이다. (`repos/codeburn/src/currency.ts:14-19`, `repos/codeburn/src/currency.ts:74-90`, `repos/codeburn/src/currency.ts:93-132`, `repos/codeburn/src/currency.ts:135-144`)

환율 cache payload는 `{ timestamp, code, rate }`이고 TTL은 24시간이다. Fetched rate는 `0.0001` 이상 `1,000,000` 이하인지 검증된다. Fetch 실패 시 rate `1`을 반환하므로 표시가 USD-equivalent로 fallback될 수 있다. (`repos/codeburn/src/currency.ts:14-26`, `repos/codeburn/src/currency.ts:93-132`)

## 7. 변환은 display/export boundary에서 한다

`convertCost(costUSD)`와 `formatCost(costUSD)`는 active currency rate를 곱해 표시값을 만든다. 내부 aggregate는 USD를 보존하고, JSON/export/dashboard 같은 표시 경계에서 변환한다. 이 설계는 JPY/KRW처럼 소수 자릿수가 0인 통화에서 per-session rounding으로 aggregate가 깨지는 문제를 피한다. (`repos/codeburn/src/currency.ts:164-185`, `repos/codeburn/src/main.ts:161-250`)

## Current-source corrections vs DeepWiki

- DeepWiki는 pricing cache가 `~/.cache/codeburn/`에 저장된다고 요약하지만, 정확히는 model pricing cache는 `CODEBURN_CACHE_DIR` override를 존중하고, exchange-rate cache는 현재 `~/.cache/codeburn/exchange-rate.json`에 고정된다.
- Runtime fetch는 LiteLLM GitHub JSON만 수행한다. models.dev와 OpenRouter는 `scripts/bundle-litellm.mjs`가 build-time fallback 파일을 만들 때 쓰는 source다.
- 환율 preference 자체는 exchange-rate cache가 아니라 `~/.config/codeburn/config.json`의 `currency` field에 저장된다. 관련 페이지: [[codeburn]], [[codeburn-data-ingestion-and-caching]], [[codeburn-turn-classification-engine]], [[codeburn-domain-terminology]], [[evidence-backed-analysis]].
