---
title: CodeBurn Report Status Export Commands
created: 2026-06-11
updated: 2026-10-15
type: concept
tags: [open-source, cli, commands, reporting, developer-tools, tooling, evidence]
sources:
  - repos/codeburn/src/main.ts
  - repos/codeburn/src/export.ts
  - repos/codeburn/src/format.ts
  - repos/codeburn/src/usage-aggregator.ts
  - repos/codeburn/src/menubar-json.ts
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
  - wiki/concepts/codeburn-day-aggregation-and-caching.md
  - wiki/concepts/codeburn-pricing-and-currency-resolution.md
  - wiki/concepts/codeburn-subscription-plans-and-currency.md
  - wiki/concepts/codeburn-optimization-engine.md
confidence: medium
---
# CodeBurn Report Status Export Commands

검증 기준 checkout: repos/codeburn at 9a40cc603fcd194caca9daa8c5134a61ea7e0e2b (2026-10-15).

[[codeburn]]의 보고·상태·내보내기 CLI 명령(`report`, `today`, `month`, `status`, `export`)이 어떤 집계 함수로 이어지는지 정리한다. 세션 파싱은 [[codeburn-data-ingestion-and-caching]], 일 단위 캐시는 [[codeburn-day-aggregation-and-caching]], 통화·플랜은 [[codeburn-pricing-and-currency-resolution]]·[[codeburn-subscription-plans-and-currency]], optimize finding은 [[codeburn-optimization-engine]] 참조.

용어:
- **durable period** (`DurablePeriod`): 일 캐시(지난 날) + 오늘 live 파싱을 합친 기간 집계. `data`(헤드라인 합계), `days`, `knownProjects`, `liveProjects` 등을 담는다. (`src/usage-aggregator.ts:860`, 코드 확인)
- **menubar payload** (`MenubarPayload`): 메뉴바/데스크톱 앱이 매 폴링마다 받는 JSON. (`src/menubar-json.ts:808-861`, 코드 확인)
- **preAction hook**: 모든 명령 실행 전 timezone, config(모델 별칭·가격 override·proxy·gateway 포함 여부 등), 통화를 로드. (`src/main.ts:558-583`, 코드 확인)

## 명령 표면 (`src/main.ts`)

| 명령 | 위치 | `--format` | 비고 |
|---|---|---|---|
| `report` (기본 명령) | `:876-927` | `tui`(기본), `json` | `--period`(기본 `week`), `--day`, `--from/--to`, `--refresh` |
| `today` / `month` | `:1481-1497` / `:1500-1516` | `tui`, `json` | 고정 기간 단축형 |
| `status` | `:1191-1478` | `terminal`(기본), `json`, `menubar-json` | `--scope local\|combined`, `--days`, `--no-optimize`, `--no-timeline` |
| `export` | `:1518-1603` | `csv`(기본), `json` | `-o`, `--from/--to`, 신규 `--route`, `--billing` |

공통: `--provider`(기본 `all`, `assertProvider`로 검증), 반복 가능한 `--project/--exclude`. (코드 확인)

## `report` (`src/main.ts:887-926`)

- 입력: 위 옵션. `--day`와 `--from/--to` 동시 지정은 오류. (`:893-901`, 코드 확인)
- 내부 동작:
  1. `syncCursor()` — Cursor 사용량 동기화. JSON 경로는 백그라운드로 두고 기다리지 않는다. (`:905`, `:536-548`, 코드 확인)
  2. `--format json` + `--day`/`--from/--to`: `buildDurablePeriod()` → `buildJsonReport()` → `attachPlanSummaries()`로 플랜 요약을 붙여 출력. (`:906-914`, 코드 확인)
  3. `--format json` + 기간만: `runJsonReport(period, …)` — 동일하게 `getDateRange` → `buildDurablePeriod` → `buildJsonReport` → `attachPlanSummaries`. (`:916`, `:517-524`, 코드 확인)
  4. 그 외: `renderDashboard()`(Ink TUI). `--period`를 사용자가 안 줬으면 `autoPeriod=true`로 "오늘, 비었으면 7일"을 대시보드가 고른다. (`:925-926`, 코드 확인)
- 반환값: stdout JSON 또는 대화형 TUI.

`today`/`month`는 JSON이면 `runJsonReport('today'|'month', …)`, 아니면 `renderDashboard`. (`src/main.ts:1492-1496`, `:1511-1515`, 코드 확인)

## `status` (`src/main.ts:1206-1478`)

옵션 조합 검증이 많다: `--combined-details`는 `menubar-json --scope combined` 전용, `--days`는 `--day/--from/--to`와 배타, `--scope combined`는 provider/project/exclude 필터와 배타. (`:1207-1241`, 코드 확인)

### `--format menubar-json` (`:1245-1426`)

- 내부 동작:
  1. 기간 결정: `--days` > `--from/--to` > `--day` > `--period`(기본 `today`). (`:1247-1254`, 코드 확인)
  2. `queryKey` 구성: 기간·필터·Claude 설정 디렉터리·각종 가격 config hash·통화·가격 데이터 세대·gateway 포함 여부. (`:1271-1325`, 코드 확인)
  3. 디스크 스냅샷: `--no-optimize`이고 resident `serve` 자식이 아닐 때만 `computeCorpusFingerprint` → `loadStatusSnapshot` 재사용. optimize 결과는 설정 파일 상태에 의존해 지문으로 무효화할 수 없으므로 optimize 경로는 스냅샷을 쓰지 않는다(주석 근거). (`:1326-1355`, 코드 확인)
  4. 스냅샷 miss면 `buildMenubarPayloadForRange(periodInfo, {...queryScope, daysSelection})`. 하이드레이션이 완전하고 stale이 아닐 때만 스냅샷 저장. (`:1356-1373`, 코드 확인)
  5. `--scope combined`: `pullDevices()`로 페어링된 다른 기기 사용량을 합쳐 `payload.combined`(실패해도 로컬 payload는 출력). (`:1374-1410`, 코드 확인)
  6. 마지막에 `cursorSync` 상태와 `providerIssues`를 붙여 한 줄 JSON 출력. (`:1413-1425`, 코드 확인)

`buildMenubarPayloadForRange()` (`src/usage-aggregator.ts:1634`): status menubar-json과 MCP 서버가 공유하는 집계. `opts.optimize === false`면 `scanAndDetect()` 생략(`:2079`), `timeline === false`면 granular history 생략(`:2081`), 마지막에 `buildMenubarPayload()`로 조립(`:2088`). (코드 확인)

### `--format json` / `terminal` (`:1428-1477`)

- 둘 다 `withLoadWindow(month)` 안에서 today·month `buildDurablePeriod()` 두 번. (코드 확인)
- `json`: `{ currency, today{cost,savings,calls}, month{...}, localModelSavings? }`. 비용은 `getCurrency().rate` 곱 후 소수 둘째 자리 반올림. 이후 `attachPlanSummaries`. (`:1440-1466`, 코드 확인)
- `terminal`: `renderStatusBar([], totals)`가 "Today $x n calls  Month $y n calls" 한 줄. (`:1474-1477`, `src/format.ts:82-94`, 코드 확인)

## `export` (`src/main.ts:1529-1602`)

- 입력: `-f csv|json`, `-o`, `--from/--to`, `--provider`, `--route`, `--billing`, `--project/--exclude`.
- 내부 동작:
  1. `fp()` 필터 = 이름 필터 + `filterProjectsByBillingRoute({route, billing})`. (`:1540-1546`, 코드 확인)
  2. custom range면 단일 기간, 아니면 30일 1회 파싱 후 `filterProjectsByDateRange`로 Today / 7 Days / 30 Days 3개 기간을 잘라낸다. (`:1556-1573`, 코드 확인)
  3. 모두 비었으면 CSV는 안내문 후 종료, JSON은 빈 배열의 유효 파일을 쓴다. (`:1576-1582`, 코드 확인)
  4. 기본 파일명 `codeburn-<YYYY-MM-DD>.<format>` → `exportJson`/`exportCsv`. 보호 장치 오류는 스택 없이 메시지만 출력 후 exit 1. (`:1584-1599`, 코드 확인)

### `exportCsv()` (`src/export.ts:403-454`)

- 출력 경로를 폴더로 취급(`.csv` 확장자 제거). 기존 일반 폴더(마커 없음)를 주면 그 안에 `codeburn-export-<date>` 하위 폴더를 만든다. 파일이 있으면 거부, 마커 없는 폴더 재사용 거부, 마커(`.codeburn-export`)가 있으면 비우고 재작성. (코드 확인)
- 파일: `README.txt`, `summary`, `daily`, `activity`, `models`(전 기간) + `records`, `projects`, `sessions`, `tools`, `mcp`, `shell-commands`(30 Days 또는 마지막 기간). (`:438-451`, 코드 확인)

### `exportJson()` (`src/export.ts:456-521`)

- `schema: 'codeburn.export.v2'`, `currency{code,rate,symbol}`, summary, periods[daily/activity/models], projects/sessions/records/tools/mcp/shellCommands. (`:461-478`, 코드 확인)
- 경로가 폴더면 내부에 dated 파일, `.json` 아니면 확장자 추가. 기존 파일은 앞 4KB에 `"schema": "codeburn.export.v` 문자열이 없으면 덮어쓰기 거부. (`:484-518`, 코드 확인)

### 통화 · CSV 안전

- 비용 셀은 `roundForActiveCurrency(convertCost(...))`로 활성 통화 변환. (`src/export.ts:5`, `:89-90`, 코드 확인)
- `escCsv()`: `\t \r = + - @`로 시작하는 값 앞에 `'`를 붙여 스프레드시트 수식 주입을 막는다. (`src/export.ts:12-18`, 코드 확인)
- `csvCell()`: 부동소수 노이즈를 소수 8자리로 정리. (`src/export.ts:31-36`, 코드 확인)

## 미확인

- `buildJsonReport()`(`src/main.ts:599`) 출력 필드 전체와 `attachPlanSummaries()`(`:247`) 플랜 요약 형태.
- `buildDurablePeriod()` 내부의 캐시 하이드레이션·오늘 overlay 세부 → [[codeburn-day-aggregation-and-caching]] 쪽 검증 필요.
- `loadStatusSnapshot`의 settle window 동작, `pullDevices()`의 기기 페어링 프로토콜.
- `export`의 각 `build*Rows` 열 정의, `--route/--billing` 필터 의미.
- 실행 확인 없음(help/test 미실행).
