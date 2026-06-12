---
title: CodeBurn Subscription Plans and Currency
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence, deepwiki]
sources:
  - artifacts/codeburn/deepwiki/pages-md/3.5-subscription-plans-and-currency.md
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-pricing-and-currency-resolution.md
  - wiki/concepts/codeburn-day-aggregation-and-caching.md
  - repos/codeburn/src/config.ts
  - repos/codeburn/src/plans.ts
  - repos/codeburn/src/plan-usage.ts
  - repos/codeburn/src/currency.ts
  - repos/codeburn/src/main.ts
  - repos/codeburn/src/export.ts
  - repos/codeburn/src/types.ts
  - repos/codeburn/src/parser.ts
confidence: high
---
# CodeBurn Subscription Plans and Currency

이 페이지는 [[codeburn]]에서 구독제 plan의 월 비용을 USD budget으로 저장하고, 실제 사용량의 API-equivalent USD 비용과 비교한 뒤, 표시/JSON/export 단계에서 환율을 이용해 local currency로 변환하는 방식을 정리한다. Token 단가와 FX fetch/cache의 일반 구조는 [[codeburn-pricing-and-currency-resolution]], 일별/기간별 aggregate는 [[codeburn-day-aggregation-and-caching]]를 참조한다.

검증 기준 checkout: `repos/codeburn` at `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.

## 핵심 모델

```text
codeburn plan set claude-max
→ config.plans.claude = { id, monthlyUsd, provider, resetDay, setAt }
→ getPlanUsages()
→ parseAllSessions(periodStart..today, provider/all)
→ PlanUsage: spentApiEquivalentUsd, budgetUsd, percentUsed, projectedMonthUsd
→ toJsonPlanSummary(): budget/spent/projectedMonthEnd = convertCost(USD)
```

Plan usage 계산 자체는 항상 USD 기준이다. Currency는 `budgetUsd`, `spentApiEquivalentUsd`, `projectedMonthUsd` 같은 plan summary 숫자를 UI/JSON/export에 내보낼 때 곱해지는 display layer다.

## Plan config 저장 구조

`Plan`은 `id`, `monthlyUsd`, `provider`, optional `resetDay`, `setAt`으로 구성된다. Provider scope는 `all`, `claude`, `codex`, `cursor`다. (`repos/codeburn/src/config.ts:7-16`, `repos/codeburn/src/plans.ts:3-4`)

설정 파일 경로는 다음이다.

```text
~/.config/codeburn/config.json
```

현재 source는 과거 단일 `config.plan`도 읽지만, 새 저장은 provider-keyed `config.plans`를 사용한다. `savePlan()`은 provider가 `all`이면 `{ all: plan }`만 저장하고, provider-specific plan을 저장할 때는 `all` plan을 제거한 뒤 해당 provider key에 저장한다. `clearPlan(provider?)`는 특정 provider 또는 전체 plan을 제거한다. (`repos/codeburn/src/config.ts:22-56`, `repos/codeburn/src/config.ts:75-85`, `repos/codeburn/src/config.ts:87-162`)

예시:

```json
{
  "plans": {
    "claude": {
      "id": "claude-max",
      "monthlyUsd": 200,
      "provider": "claude",
      "resetDay": 1,
      "setAt": "2026-06-11T00:00:00.000Z"
    },
    "codex": {
      "id": "custom",
      "monthlyUsd": 200,
      "provider": "codex",
      "resetDay": 1,
      "setAt": "2026-06-11T00:00:00.000Z"
    }
  }
}
```

## Built-in subscription presets

| Plan id | Display name | monthlyUsd | provider | resetDay |
|---|---|---:|---|---:|
| `claude-pro` | Claude Pro | 20 | `claude` | 1 |
| `claude-max` | Claude Max 20x | 200 | `claude` | 1 |
| `claude-max-5x` | Claude Max 5x | 100 | `claude` | 1 |
| `cursor-pro` | Cursor Pro | 20 | `cursor` | 1 |
| `custom` | Custom | user input | `all` or provider option | user input |

근거: `repos/codeburn/src/plans.ts:6-63`, `repos/codeburn/src/main.ts:888-1028`.

주의: DeepWiki는 `claude-max`를 “Claude Max”라고만 적지만 현재 display label은 `Claude Max 20x`다. 금액 자체는 `$200/month`로 동일하다.

## CLI plan flow

`codeburn plan` command는 `show`, `set`, `reset`을 처리한다. (`repos/codeburn/src/main.ts:888-1028`)

- `codeburn plan` / `codeburn plan --format json`: 저장된 plan을 보여준다.
- `codeburn plan set claude-max`: preset provider인 `claude` plan으로 저장한다.
- `codeburn plan set custom --monthly-usd 200 --provider codex`: custom USD budget을 provider-specific으로 저장한다.
- `codeburn plan reset --provider codex`: 특정 provider plan만 제거한다.
- `--reset-day`는 1..28 정수만 허용된다.

Plan command의 text output은 plan budget을 `$<monthlyUsd>/month`로 보여준다. 즉 plan 설정 자체는 선택 currency로 변환해 저장하지 않는다.

## Billing period와 projection

`resetDay`는 `clampResetDay()`에서 1..28로 제한된다. 오늘 날짜가 resetDay 이상이면 billing period는 현재 월 resetDay부터 다음 월 resetDay 직전까지이고, 오늘이 resetDay 전이면 이전 월 resetDay부터 현재 월 resetDay까지다. (`repos/codeburn/src/plan-usage.ts:23-44`)

`getPlanUsageFromProjects()`는 다음을 계산한다. (`repos/codeburn/src/plan-usage.ts:110-129`)

| Field | 계산 |
|---|---|
| `spentApiEquivalentUsd` | scoped projects의 `totalCostUSD` 합계 |
| `budgetUsd` | `plan.monthlyUsd` |
| `percentUsed` | `spent / budget * 100` |
| `status` | `>100`이면 `over`, `>=80`이면 `near`, 아니면 `under` |
| `projectedMonthUsd` | trailing 7-day median daily cost 기반 월말 projection |
| `daysUntilReset` | 오늘부터 period end까지 calendar day 차이 |

Projection은 periodStart부터 today까지 날짜별 call cost를 모으고, 비어 있는 날은 0으로 채운 뒤, 최근 7일 median daily cost를 남은 일수에 곱해 현재 spent에 더한다. 단순 평균이 아니라 median을 쓰기 때문에 하루짜리 spike가 projection을 과도하게 끌어올리는 것을 줄인다. (`repos/codeburn/src/plan-usage.ts:46-107`)

## Provider별 여러 plan 처리

현재 구현은 여러 provider-specific plan을 지원한다. `getPlanUsages()`는 `readPlans()`에서 active plan들을 가져오고, plan이 하나뿐이면 해당 provider만 `parseAllSessions(range, plan.provider)`로 읽는다. Plan이 여러 개이면 가장 이른 periodStart부터 `parseAllSessions(range, 'all')`을 한 번 수행한 뒤, `getPlanScopedProjects()`가 각 plan provider와 periodStart..today 범위에 맞는 assistant call만 남긴 scoped project clone을 만든다. (`repos/codeburn/src/plan-usage.ts:132-214`)

이 설계 때문에 같은 report payload에 legacy-compatible `plan` field와 provider-keyed `plans` map이 함께 붙을 수 있다. (`repos/codeburn/src/main.ts:73-93`)

## Currency와 plan summary 변환

Currency preference는 `config.currency`에 저장되고, `program.hook('preAction')`에서 `loadCurrency()`가 실행된다. (`repos/codeburn/src/main.ts:140-159`)

`loadCurrency()`는 USD가 아니면 Frankfurter API에서 `USD → code` 환율을 가져온다.

```text
https://api.frankfurter.app/latest?from=USD&to=<CODE>
```

환율 cache는 다음 위치에 24시간 TTL로 저장된다.

```text
~/.cache/codeburn/exchange-rate.json
```

Fetched/cached rate는 `0.0001 <= rate <= 1_000_000` 범위인지 검증된다. Fetch 실패 시 rate `1`로 fallback되므로 해당 표시값은 USD-equivalent가 될 수 있다. (`repos/codeburn/src/currency.ts:14-28`, `repos/codeburn/src/currency.ts:74-132`)

Plan JSON summary는 `toJsonPlanSummary()`에서 USD 숫자에 `convertCost()`를 적용한다.

```text
budget            = convertCost(planUsage.budgetUsd)
spent             = convertCost(planUsage.spentApiEquivalentUsd)
projectedMonthEnd = convertCost(planUsage.projectedMonthUsd)
percentUsed       = round(percentUsed, 1)   // FX와 무관
```

근거: `repos/codeburn/src/main.ts:45-70`.

중요한 점은 `percentUsed`와 `status`가 USD 기준 비율이라는 것이다. `budgetUsd`와 `spentApiEquivalentUsd`에 같은 환율을 곱해도 비율은 변하지 않기 때문에, 환율은 표시 금액에만 영향을 주고 plan burn 판단에는 영향을 주지 않는다.

## Rounding boundary

`convertCost(costUSD)`는 `costUSD * active.rate`만 반환하고 반올림하지 않는다. JPY/KRW처럼 소수 자릿수가 0인 통화에서 session별로 먼저 반올림하면 aggregate가 왜곡될 수 있기 때문이다. (`repos/codeburn/src/currency.ts:164-172`)

반올림은 display/export boundary에서 한다.

- `formatCost(costUSD)`는 active currency의 fraction digits를 보고 문자열을 만든다. 0-decimal currency는 정수로 표시한다. (`repos/codeburn/src/currency.ts:174-185`)
- CSV/export row들은 `roundForActiveCurrency(convertCost(value))`를 사용한다. (`repos/codeburn/src/export.ts:48-83`, `repos/codeburn/src/export.ts:107-151`, `repos/codeburn/src/export.ts:188-247`)
- `report/status/today/month` JSON plan summaries는 `convertCost()` 결과를 그대로 넣는다. Consumer가 필요한 rounding/display를 담당한다. (`repos/codeburn/src/main.ts:58-70`, `repos/codeburn/src/main.ts:83-93`)

## Subscription-covered proxy cost와 plan의 차이

CodeBurn에는 plan budget 외에 `proxyPaths`라는 구독 기반 proxy attribution도 있다. `proxyPaths` 아래 project는 full API-rate `totalCostUSD`를 유지하되, 같은 금액을 `totalProxiedCostUSD`로 기록해 `netCost = totalCostUSD - totalProxiedCostUSD`를 계산한다. 이는 “구독으로 커버된 would-be API 비용” 표시용이며, plan budget burn 계산과는 별개다. (`repos/codeburn/src/config.ts:45-55`, `repos/codeburn/src/types.ts:165-170`, `repos/codeburn/src/parser.ts:1658-1675`, `repos/codeburn/src/main.ts:377-385`)

## Current-source corrections vs DeepWiki

- DeepWiki는 plan을 단일 `plan`처럼 설명하지만 현재 source는 provider-keyed `plans` map을 우선 사용하고, legacy `plan`은 migration/read compatibility로 처리한다.
- `claude-max` display label은 현재 `Claude Max 20x`다.
- Plan 설정/저장은 항상 USD budget이며, `codeburn plan show` text도 `$monthlyUsd/month`를 보여준다. Currency conversion은 report/status/export payload boundary에서 수행된다.
- Exchange-rate cache는 현재 `CODEBURN_CACHE_DIR`를 쓰지 않고 `~/.cache/codeburn/exchange-rate.json`에 고정된다. 이 점은 [[codeburn-pricing-and-currency-resolution]]의 current-source correction과 동일하다.

관련 페이지: [[codeburn]], [[codeburn-pricing-and-currency-resolution]], [[codeburn-day-aggregation-and-caching]], [[codeburn-domain-terminology]], [[evidence-backed-analysis]].
