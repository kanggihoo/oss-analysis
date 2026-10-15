---
title: CodeBurn Subscription Plans and Currency
created: 2026-06-11
updated: 2026-10-15
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence]
sources:
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-pricing-and-currency-resolution.md
  - wiki/concepts/codeburn-day-aggregation-and-caching.md
  - repos/codeburn/src/config.ts
  - repos/codeburn/src/plans.ts
  - repos/codeburn/src/plan-usage.ts
  - repos/codeburn/src/copilot-aiu.ts
  - repos/codeburn/src/budget.ts
  - repos/codeburn/src/quota.ts
  - repos/codeburn/src/quota/index.ts
  - repos/codeburn/src/currency.ts
  - repos/codeburn/src/main.ts
  - repos/codeburn/src/parser.ts
confidence: high
---
# CodeBurn Subscription Plans and Currency

검증 기준 checkout: repos/codeburn at 9a40cc603fcd194caca9daa8c5134a61ea7e0e2b (2026-10-15).

[[codeburn]]이 "API 가격으로 환산하면 얼마 썼나"를 구독료(plan)·예산(budget)과 비교하는 방식과, 그 결과를 사용자 통화로 보여주는 경계를 정리한다. 단가 계산과 환율 로드 자체는 [[codeburn-pricing-and-currency-resolution]], 기간 집계는 [[codeburn-day-aggregation-and-caching]]를 본다.

용어:
- plan: 사용자가 등록한 월 구독(예: Claude Max). 월 금액과 갱신일을 가진다.
- API-equivalent 비용: 실제 청구액이 아니라 token을 API 단가로 환산한 USD. plan 비교의 "사용량"이 이것이다.
- budget: plan과 별개인 일/주/월 지출 한도. 표시 통화 단위로 저장된다.
- AI credit: GitHub Copilot 과금 단위. 1 credit = $0.01, 1e9 nano-AIU = 1 credit. `src/copilot-aiu.ts:6-7` (코드 확인)

## 1. Plan 데이터 모델 — `src/config.ts`

- `Plan = { id, monthlyUsd, monthlyCredits?, provider, resetDay?, setAt }`. `src/config.ts:10-19` (코드 확인)
- `PlanProvider`: `claude | codex | cursor | grok | copilot | antigravity | all`. `src/config.ts:8` (코드 확인)
- 저장: config의 `plans`(provider별 맵). 옛 단일 `plan` 필드는 `plans`가 비었을 때만 읽고, 저장 시 지운다. `src/config.ts:151-187` (코드 확인)
- `all` plan은 provider별 plan이 하나라도 있으면 버려진다(둘은 공존 불가). `src/config.ts:159-161`, `:178-184` (코드 확인)
- 활성 조건: `id !== 'none'`이고 `monthlyUsd`가 유한한 양수. `src/plan-usage.ts:359-361` (코드 확인)

## 2. 내장 preset — `src/plans.ts:16-95`

| id | monthlyUsd | provider |
|---|---:|---|
| claude-pro / claude-max-5x / claude-max | 20 / 100 / 200 | claude |
| cursor-pro | 20 | cursor |
| supergrok / supergrok-heavy | 30 / 300 | grok |
| copilot-pro / -pro-plus / -max | 1500 / 7000 / 20000 credits × $0.01 | copilot |
| google-ai-pro / -ultra-5x / -ultra-20x | 19.99 / 99.99 / 199.99 | antigravity |

모두 `resetDay: 1`. 이외 `custom`, `none`. (코드 확인) 금액은 코드 주석의 외부 문서 기준이며 현재 실제 가격인지는 미확인.

## 3. CLI — `codeburn plan [show|set <id>|reset]` `src/main.ts:2234`

- `--provider`, `--reset-day`(1~28 정수), custom용 `--monthly-usd`, copilot custom용 `--credits`. (코드 확인)
- copilot custom은 `--credits`만 허용, `--monthly-usd`와 혼용 시 오류. `src/main.ts:2327-2337` (코드 확인)
- `set none`은 해당 provider plan 삭제. `src/main.ts:2312-2319` (코드 확인)

## 4. 사용량 계산 — `src/plan-usage.ts`

`getPlanUsages(today)` `:338`
- 입력: 오늘 날짜.
- 내부 동작: 활성 plan을 모으고, 가장 이른 period 시작일~오늘로 세션을 한 번 파싱. plan이 1개면 그 provider로만, 여러 개면 `'all'`로 파싱 후 `getPlanScopedProjects`(`:270`)로 provider·기간별 잘라낸다. (코드 확인)
- 반환값: `PlanUsage[]`(`:13-32`): `spentApiEquivalentUsd`, `budgetUsd`, `percentUsed`, `status`, `projectedMonthUsd`, `daysUntilReset`, copilot이면 credit 필드.

기간: `computePeriodFromResetDay`(`:39`)는 오늘 날짜가 resetDay 이상이면 이번 달 resetDay~다음 달 resetDay, 아니면 전달부터. resetDay는 1~28로 clamp(`:34-37`). (코드 확인)

`getPlanUsageFromProjects(plan, projects)` `:217` (코드 확인)
- USD plan: spent = 프로젝트 `totalCostUSD` 합, percent = spent/monthlyUsd. `:252-253`
- status: 100% 초과 `over`, 80% 이상 `near`, 그 외 `under`. `:9`, `:231`, `:254`
- 월말 예상 `projectMonthEnd`(`:177`): 최근 최대 7일의 일별 비용 **중앙값** × 남은 일수 + spent. `:210-214`
- Copilot plan: 비용이 아니라 credit으로 계산. `copilotCreditSpend`(`:111`)가 nano-AIU가 기록된 요청은 정확 credit으로, 없는 요청은 token 비용/$0.01로 추정해 `estimatedCredits`에 더한다. 미기록 요청이 하나라도 있으면 진행률 막대가 추정치를 따른다. `:228-229`

## 5. Budget — `src/budget.ts`, `src/main.ts`

- `computeBudgetStatus`(`src/budget.ts:44`): pct = spent/budget, 선형 예측 projected = spent × totalDays / elapsedDays, 100% 이상 `over`, 80% 이상 `warn`. (코드 확인) plan의 중앙값 예측과 방식이 다르다.
- budget 금액은 **표시 통화**로 저장된다(`src/config.ts:56`). 그래서 비교 전에 USD 비용을 `convertCost`로 먼저 바꾼다. `src/main.ts:333-334`, `:416-417` (코드 확인)
- `codeburn budget --check`(`src/main.ts:1130`) → `runBudgetCheck`(`:401`)는 하나라도 over면 exit code 1. `:429` (코드 확인)

## 6. 통화 변환 경계

- plan 금액(`monthlyUsd`)과 `PlanUsage`는 USD로 유지된다. JSON 출력 시 `toJsonPlanSummary`가 `budget`, `spent`, `projectedMonthEnd`만 `convertCost`로 바꾼다. `src/main.ts:186-198` (코드 확인)
- copilot 요약은 원래 USD(`monthlyUsd`, `spentApiEquivalentUsd`)와 credit 필드를 같이 싣는다. `src/main.ts:199-210` (코드 확인)
- 텍스트 `plan show`는 `$${monthlyUsd}/month`를 그대로 찍어 환율을 적용하지 않는다. `src/main.ts:2275` (코드 확인)
- `codeburn currency <code>`는 ISO 4217 검증 후 config 저장 → `loadCurrency()`; 환율이 없으면 USD로 표시하며 안내. `src/main.ts:1649-1700` (코드 확인)

## 7. 관련되지만 다른 것

- proxy path: 구독 프록시를 거친 프로젝트는 `totalCostUSD`를 그대로 두고 같은 값을 `totalProxiedCostUSD`로 표시한다. plan과 무관한 별도 표기. `src/parser.ts:2754-2764` (코드 확인)
- `codeburn quota`(`src/main.ts:3330`): provider 서버에서 실제 쿼터 창(5시간/주간 등)을 읽는 기능. `src/quota/index.ts`가 provider별 reader를 묶는다. plan 계산과 데이터 경로가 분리되어 있다. (코드 확인)
- `src/quota.ts`: live/derived 쿼터 창을 합치고 pace를 계산하는 순수 모델. 현재 `src` 안에서 import하는 곳이 없고 `tests/quota.test.ts`만 사용한다. (코드 확인) 향후 통합용으로 보인다(추론).

## 미확인
- preset 금액과 Copilot credit 할당량이 현재 실제 가격과 일치하는지.
- `codeburn quota` provider reader들이 호출하는 외부 엔드포인트의 동작.
- dashboard(`src/dashboard.tsx:1798`, `:2316`)가 plan 금액을 어느 통화로 렌더링하는지 세부.
- 여러 plan이 겹칠 때(예: claude와 codex) UI에서 어떤 plan을 대표로 보여주는지(JSON은 첫 항목을 `plan`으로 노출, `src/main.ts:250-253`).
