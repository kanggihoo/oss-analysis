---
title: CodeBurn Report Status Export Commands
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [open-source, cli, commands, reporting, developer-tools, tooling, evidence, deepwiki]
sources:
  - artifacts/codeburn/deepwiki/pages-md/3.2-report-status-and-export-commands.md
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
  - wiki/concepts/codeburn-day-aggregation-and-caching.md
  - wiki/concepts/codeburn-pricing-and-currency-resolution.md
  - wiki/concepts/codeburn-subscription-plans-and-currency.md
  - repos/codeburn/src/cli.ts
  - repos/codeburn/src/main.ts
  - repos/codeburn/src/export.ts
  - repos/codeburn/src/format.ts
  - repos/codeburn/src/currency.ts
  - repos/codeburn/src/usage-aggregator.ts
  - repos/codeburn/src/menubar-json.ts
  - repos/codeburn/tests/export.test.ts
  - repos/codeburn/tests/menubar-json.test.ts
  - repos/codeburn/tests/cli-status-menubar.test.ts
  - repos/codeburn/tests/cli-export-date-range.test.ts
confidence: high
---
# CodeBurn Report Status Export Commands

이 페이지는 [[codeburn]]의 non-interactive reporting/export command surface를 정리한다. DeepWiki `3.2 Report, Status, and Export Commands`를 baseline으로 삼았지만, durable claim은 현재 `repos/codeburn` source와 실제 help/test 실행으로 확인했다. Provider/session parsing boundary는 [[codeburn-data-ingestion-and-caching]], period/day cache는 [[codeburn-day-aggregation-and-caching]], currency/plan boundary는 [[codeburn-pricing-and-currency-resolution]] 및 [[codeburn-subscription-plans-and-currency]]를 참조한다.

검증 기준 checkout: `repos/codeburn` at `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.

## Current command surface

현재 `src/cli.ts`는 Node version guard와 `import('./main.js')`만 담은 launcher다. 실제 Commander command 정의는 `src/main.ts`에 있다. (`repos/codeburn/src/cli.ts:1-15`, `repos/codeburn/src/main.ts:133-159`)

`npx tsx src/main.ts --help`로 확인한 report/status/export command surface는 다음과 같다.

| Command | 현재 역할 | 주요 non-interactive format |
|---|---|---|
| `codeburn report` | 기본은 interactive dashboard이며 `--format json`일 때 JSON report를 출력 | `--format json` |
| `codeburn status` | today/month compact summary 및 menubar/MCP payload 계열 | `--format terminal`, `json`, `menubar-json` |
| `codeburn today` / `month` | period shortcut dashboard | `--format tui`, `json` |
| `codeburn export` | usage data를 CSV directory 또는 JSON file로 저장 | `--format csv`, `json` |

실제 help 출력 검증에서 `report`, `status`, `export` 모두 `--provider`, repeatable `--project`, repeatable `--exclude`를 제공했다. `report`는 `--day`, `--from`, `--to`, `--period`, `--refresh`를 가진다. `status menubar-json`은 `--period`, `--day`, `--from`, `--to`, `--days`, `--no-optimize`를 가진다. `export`는 `--from/--to` custom range와 `-o/--output`을 가진다.

## JSON report path

`codeburn report --format json`은 다음 flow를 따른다. (`repos/codeburn/src/main.ts:410-458`)

```text
report --format json
→ loadPricing()
→ getDateRange() or parseDayFlag()/parseDateRangeFlags()
→ parseAllSessions(range, provider)
→ filterProjectsByName(project, exclude)
→ buildJsonReport(projects, label, periodKey)
→ attachPlanSummaries()
→ stdout JSON
```

`buildJsonReport()`는 `ProjectSummary[]`에서 headline overview, daily, projects, models, activities, tools, MCP servers, shell commands, skills, subagents, Claude agent types, top sessions를 만든다. Overview에는 `cost`, `proxiedCost`, `netCost`, `savings`, `calls`, `sessions`, `cacheHitPercent`, token buckets가 포함된다. (`repos/codeburn/src/main.ts:161-407`)

Cache hit 계산은 menubar JSON과 맞춰 `cacheRead / (input + cacheRead)`이다. `cache_write`는 served token이 아니라 저장된 token이므로 denominator에 넣지 않는다. (`repos/codeburn/src/main.ts:173-180`, `repos/codeburn/src/menubar-json.ts:196-200`, `repos/codeburn/tests/menubar-json.test.ts:125-143`)

Plan integration은 DeepWiki의 단일 `plan` 설명보다 확장되어 있다. `attachPlanSummaries()`는 configured plan usage가 있으면 legacy-compatible `plan` 하나와 provider-keyed `plans` map을 같이 붙인다. (`repos/codeburn/src/main.ts:58-93`)

## Status and menubar JSON path

`codeburn status`의 terminal format은 month range를 parse한 뒤 `renderStatusBar()`에 넘긴다. `renderStatusBar()`는 turn의 user timestamp가 아니라 첫 assistant call timestamp를 local date로 bucket한다. 이 boundary는 midnight을 걸친 turn이 비용 발생 시점에 귀속되도록 하는 의도적 선택이다. (`repos/codeburn/src/main.ts:461-544`, `repos/codeburn/src/format.ts:31-63`)

```text
status --format terminal
→ loadPricing()
→ parseAllSessions(month range, provider)
→ filterProjectsByName(project, exclude)
→ renderStatusBar(projects)
→ Today / Month cost + calls line
```

`status --format json`은 today와 month를 각각 parse하고 `buildPeriodData()`로 `{ cost, savings, calls }`를 만든 뒤 currency rate를 적용해 JSON을 출력한다. Plan summary도 `attachPlanSummaries()`로 붙는다. (`repos/codeburn/src/main.ts:507-538`, `repos/codeburn/src/usage-aggregator.ts:12-53`)

`status --format menubar-json`은 `buildMenubarPayloadForRange()`를 호출한다. 이 path는 menubar app뿐 아니라 MCP server와 공유되는 aggregation path이며, all-provider일 때 daily cache와 today parse를 섞어 current/history/provider tabs를 만든다. `--no-optimize`이면 expensive `scanAndDetect()` pass만 생략하고 retry/routing/local-model breakdown은 계속 계산된다. (`repos/codeburn/src/main.ts:487-504`, `repos/codeburn/src/usage-aggregator.ts:84-408`, `repos/codeburn/src/menubar-json.ts:304-341`)

## Export path

`codeburn export`는 기본적으로 30일 parse 결과에서 Today/7 Days/30 Days period를 구성하고, `--from`/`--to`가 있으면 단일 custom period만 export한다. (`repos/codeburn/src/main.ts:580-644`)

```text
export
→ loadPricing()
→ parseAllSessions(30days or custom range, provider)
→ filterProjectsByName(project, exclude)
→ PeriodExport[]
→ exportCsv() or exportJson()
→ saved path message
```

CSV export는 단일 CSV 파일이 아니라 directory를 만든다. `.csv`로 끝나는 output path는 extension을 제거해 folder name으로 쓰고, folder 안에 marker와 table별 file을 쓴다. (`repos/codeburn/src/export.ts:300-344`)

```text
.codeburn-export
README.txt
summary.csv
daily.csv
activity.csv
models.csv
projects.csv
sessions.csv
tools.csv
shell-commands.csv
```

`summary`, `daily`, `activity`, `models`는 모든 `PeriodExport[]`에 대해 작성된다. `projects`, `sessions`, `tools`, `shell-commands`는 `30 Days` period가 있으면 그것을 detail period로 쓰고, 없으면 마지막 period를 쓴다. (`repos/codeburn/src/export.ts:304-341`)

JSON export는 `schema: "codeburn.export.v2"`, generated timestamp, active currency metadata, summary/period tables, detail projects/sessions/tools/shellCommands를 하나의 JSON file로 저장한다. Output path가 `.json`으로 끝나지 않으면 `.json`을 붙인다. (`repos/codeburn/src/export.ts:346-399`)

## Currency and rounding boundary

CLI pre-action은 config/model alias/proxy path를 hydrate하고 `loadCurrency()`를 호출한다. (`repos/codeburn/src/main.ts:140-159`) `loadCurrency()`는 config currency가 있으면 Frankfurter API 또는 `~/.cache/codeburn/exchange-rate.json` cache에서 USD exchange rate를 가져오고, 실패 시 rate 1을 사용한다. (`repos/codeburn/src/currency.ts:74-143`)

Export rows는 `convertCost()` 후 `roundForActiveCurrency()`를 적용한다. 따라서 JPY/KRW처럼 fraction digit이 0인 currency는 row boundary에서 자연 소수 자릿수로 rounding되고, `convertCost()` 자체는 unrounded value를 반환해 per-session rounding accumulation error를 피한다. (`repos/codeburn/src/export.ts:71-83`, `repos/codeburn/src/export.ts:193-226`, `repos/codeburn/src/currency.ts:56-72`, `repos/codeburn/src/currency.ts:164-185`)

## Export safety and CSV injection guards

CSV cell escaping은 spreadsheet formula injection을 막기 위해 `^[\t\r=+\-@]`로 시작하는 cell 앞에 single quote를 붙인다. 이후 comma/quote/newline이 있으면 double quote로 감싸고 내부 quote를 escape한다. (`repos/codeburn/src/export.ts:9-26`)

Export path safety는 DeepWiki 설명보다 현재 source가 더 강하다.

- CSV: existing file overwrite를 거부하고, existing directory는 `.codeburn-export` marker가 있을 때만 비운다. 즉 root/home directory 단순 guard가 아니라 marker-based reuse guard다. (`repos/codeburn/src/export.ts:284-324`)
- JSON: existing file이 있으면 첫 4KB에서 `"schema": "codeburn.export.v` marker를 확인하고, CodeBurn export로 보이지 않으면 overwrite를 거부한다. Existing directory도 거부한다. (`repos/codeburn/src/export.ts:346-399`)

`tests/export.test.ts`는 formula-like project/model/command escaping, tab/carriage-return prefix escaping, per-model efficiency CSV columns, empty period handling, README wording을 검증한다. (`repos/codeburn/tests/export.test.ts:115-196`)

## Test/help verification

이번 wiki update 중 다음 명령을 실제 실행해 확인했다.

```bash
npm ci
npx tsx src/main.ts --help
npx tsx src/main.ts report --help
npx tsx src/main.ts status --help
npx tsx src/main.ts export --help
npm exec vitest -- run tests/export.test.ts tests/menubar-json.test.ts tests/cli-status-menubar.test.ts tests/cli-export-date-range.test.ts
```

결과는 `npm ci`가 218 packages 설치, 취약점 0개였고, Vitest는 4 files / 24 tests 모두 pass였다. Help 실행은 성공했지만 `tsx` 경로에서 Node `DEP0205 module.register()` deprecation warning이 stderr에 출력됐다.

## Current-source corrections vs DeepWiki

- DeepWiki는 command implementation을 `src/cli.ts`로 설명하지만, 현재 `src/cli.ts`는 launcher이고 실제 command logic은 `src/main.ts`에 있다.
- DeepWiki의 “`codeburn report` generates JSON” 표현은 현재 source 기준으로는 `codeburn report --format json`일 때만 정확하다. 기본 `report`는 interactive dashboard(`--format tui`)다.
- DeepWiki의 report line ranges는 현재 checkout과 맞지 않고, current JSON report는 `proxiedCost`, `netCost`, `savings`, model efficiency, skills/subagents/Claude agent types, `plans` map 등으로 확장되어 있다.
- Status terminal bucketing은 assistant-call timestamp 기준인 반면, `buildJsonReport()` daily rollup은 turn timestamp를 우선하고 없을 때 assistant-call timestamp로 fallback한다. 두 surface의 date attribution boundary가 완전히 같지는 않다.
- CSV export는 DeepWiki의 root/home overwrite guard보다 marker-based guard가 핵심이다. JSON export에도 schema-marker overwrite guard가 추가되어 있다.
- Export files에는 DeepWiki 목록 외에 `README.txt`와 `summary.csv`가 포함된다.

관련 페이지: [[codeburn]], [[codeburn-data-ingestion-and-caching]], [[codeburn-day-aggregation-and-caching]], [[codeburn-pricing-and-currency-resolution]], [[codeburn-subscription-plans-and-currency]], [[evidence-backed-analysis]].
