---
title: CodeBurn
created: 2026-06-10
updated: 2026-10-15
type: project
tags: [open-source, project, architecture, developer-tools, tooling, evidence]
sources:
  - reports/codeburn/overview.md
  - reports/codeburn/diagrams/structure.json
  - reports/codeburn/diagrams/report-flow.json
  - repos/codeburn/README.md
  - repos/codeburn/src/cli.ts
  - repos/codeburn/src/main.ts
  - repos/codeburn/src/providers/index.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/session-cache.ts
  - repos/codeburn/src/daily-cache.ts
  - repos/codeburn/src/usage-aggregator.ts
  - repos/codeburn/src/models.ts
  - repos/codeburn/src/currency.ts
  - repos/codeburn/src/dashboard.tsx
confidence: medium
---

# CodeBurn

AI 코딩 도구(Claude Code, Codex, Cursor 등 43개 provider)가 **이미 로컬 디스크에 남긴 세션 로그를 다시 읽어** 토큰, 비용, 작업 분류, 낭비 후보를 보여 주는 Node.js CLI다(npm `codeburn`). 계정, API 키, 프록시가 필요 없다.

- 검증 기준 checkout: `repos/codeburn` at `9a40cc603fcd194caca9daa8c5134a61ea7e0e2b` (v0.9.27, 2026-10-15)
- 상세 보고서: `reports/codeburn/overview.md` (주요 기능 표, archify 그림, `report` 흐름 10단계)
- 1차 분석이다. 코드로 읽은 것은 `report` 흐름 하나다.

## 핵심 구조 (코드 확인)

```text
에이전트 로컬 로그 (~/.claude, ~/.codex …)
→ provider registry (core 32 + lazy 11)         src/providers/index.ts:200-204
→ parser.parseAllSessions                       src/parser.ts:6299
    ↔ 세션 캐시 session-cache.v10/ (일별 piece)   src/session-cache.ts:239-244
    → 비용 calculateCost + 분류 classifyTurn      src/models.ts:1516, src/classifier.ts:200
→ usage-aggregator.buildDurablePeriod           src/usage-aggregator.ts:908
    ↔ 일별 캐시 daily-cache.v75.json              src/daily-cache.ts:429
→ 화면: Ink TUI, menubar JSON, MCP, serve, web
```

- **기본 명령은 `report`** (`src/main.ts:876`). `src/cli.ts`는 Node 버전만 확인하고 `main.js`를 불러오는 얇은 실행기다.
- **provider**: 도구별 로그 어댑터. `discoverSessions()`로 위치를 찾고, `createSessionParser().parse()`로 호출 단위 레코드 `ParsedProviderCall`을 흘려보낸다.
- **증분 파싱**: 파일마다 fingerprint를 비교해 "변경 없음 / 덧붙음 / 전체 재파싱"을 정한다. 재파싱할 양이 200MB 이상이면 worker_threads로 나눈다(Claude, Codex만).
- **세션 캐시에는 대부분 토큰만 두고, 비용은 읽을 때마다 현재 가격표로 USD로 다시 계산**한다 (`src/parser.ts:2984`). 예외는 도구가 기록한 비용을 쓰는 `REPORTED_COST_PROVIDERS`와 `costFromBilling` 호출이다 (`src/parser.ts:2794,2821`). 통화 변환은 표시할 때만 한다.
- **한 엔진, 여러 화면**: macOS menubar(Swift), Windows tray(Tauri), GNOME 확장은 `status --format menubar-json`을 실행한다. Electron 앱과 VS Code 확장은 `serve --stdio` 상주 서버를 쓴다. 주변 앱은 계산하지 않는다.

## 기능 범위 (요약)

보기(`report`/`sessions`/`models`/`compare`), 고치기(`optimize --apply`, `act undo`), 예산(`plan`/`budget`/`quota`/`guard`), 비용 조정(`currency`, `model-alias`, `price-override` 등), 연동(`web`, `mcp`, `menubar`, `sync`, `plugin`). 근거 수준을 붙인 전체 표는 `reports/codeburn/overview.md`의 "주요 기능" 절에 있다.

## 재사용할 설계 포인트

- **로그를 다시 읽는 관측 도구**: 도구 사이에 끼어들지 않으므로 이 도구가 멈춰도 에이전트는 영향을 받지 않는다. 대신 도구마다 로그 형식 어댑터가 필요하다. 비슷한 방식: [[tokscale]], [[claude-devtools]].
- **가격은 저장하지 않고 계산한다**: 캐시에는 토큰만 두고 비용은 읽을 때 계산한다. 그래서 가격표가 바뀌어도 캐시를 버리지 않아도 된다 (`추론`).
- **CLI를 단일 진실 원천으로**: GUI 앱들은 CLI의 JSON 출력만 소비한다. 숫자가 화면마다 어긋나지 않게 하는 구조로 보인다 (`추론`).

## Concept 노트

- [[codeburn-domain-terminology]]: 용어
- [[codeburn-provider-plugin-system]], [[codeburn-codex-provider]]: provider
- [[codeburn-data-ingestion-and-caching]], [[codeburn-day-aggregation-and-caching]]: 파싱과 캐시
- [[codeburn-turn-classification-engine]]: 작업 분류
- [[codeburn-pricing-and-currency-resolution]], [[codeburn-subscription-plans-and-currency]]: 가격, 통화, 플랜
- [[codeburn-optimization-engine]], [[codeburn-report-status-export-commands]]: optimize와 출력 명령

## 미확인

- `hydrateCache` backfill과 기간 파싱이 실제로 두 번 파싱하는지 (실행 미확인)
- guard, sync, plugins, sharing, act의 내부 동작
- 주변 앱(`mac/`, `windows/`, `app/`, `vscode/`, `gnome/`, `dash/`) 내부 구조
- 실행 확인 없음(테스트와 실제 실행 모두 하지 않음)
