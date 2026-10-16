# CodeBurn Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/getagentseal/codeburn`
- **분석 Commit SHA**: `9a40cc603fcd194caca9daa8c5134a61ea7e0e2b` (2026-10-13, npm `codeburn` v0.9.27)
- **분석 일자**: `2026-10-15`
- **작업트리 상태**: 추적 파일 변경 없음. 미추적 파일만 있음(`.codex/`, `.graphifyignore`, `AGENTS.md`, `graphify-out/` — 이전 세션의 graphify 산출물)
- **분석 목적**: 학습. AI 코딩 도구 로그 → 토큰·비용 집계 파이프라인 이해 (비슷한 도구: tokscale, claude-devtools, codenotch)
- **메타데이터**: `artifacts/codeburn/repo-metadata.txt`

> 초기 작업(1차)이다. 구조와 대표 흐름 하나(`codeburn report`)만 코드로 확인했다. 테스트와 실행은 하지 않았다.

### 이전 분석과의 관계
- 예전 wiki 노트는 `f1bf7a1`(2026-06-10, 1851 commit 전) 기준이었다. 2026-10-15에 `wiki/projects/codeburn.md`와 `wiki/concepts/codeburn-*.md` 10개를 이 기준(`9a40cc6`)으로 처음부터 다시 썼다. 옛 내용은 남기지 않았다.

---

## 2. 프로젝트 개요

Claude Code, Codex, Cursor 같은 AI 코딩 도구가 **로컬에 남긴 세션 로그를 읽어서**, 토큰 사용량, 비용(USD → 표시 통화), 작업 분류, 캐시 효율, 최적화 후보를 보여 주는 Node.js CLI다. API를 호출해서 사용량을 받아 오는 게 아니라 **이미 디스크에 있는 로그를 다시 읽는다**는 점이 핵심이다.

- **진입점**: `src/cli.ts`는 Node 버전(>=22.13)만 확인하고 `main.js`를 동적 import한다 (`src/cli.ts:21`). 명령 등록은 `src/main.ts`(commander)가 맡고, 명령은 약 38개다.
- **기본 명령은 `report`**: 인자 없이 `codeburn`을 실행하면 `report`가 돈다 (`src/main.ts:876`, `{ isDefault: true }`). 터미널에서는 Ink(React for CLI) 대시보드가 뜬다.
- **provider**: 도구별 로그 형식을 읽는 어댑터. `discoverSessions()`로 로그 위치를 찾고, `createSessionParser().parse()`로 호출 단위 레코드(`ParsedProviderCall`)를 흘려보낸다 (`src/providers/types.ts`).
- **캐시 2단**: 로그 파일 단위의 **세션 캐시**(`~/.cache/codeburn/session-cache.v10/`)와 날짜 단위의 **일별 캐시**(`~/.cache/codeburn/daily-cache.v75.json`). 바뀐 파일만 다시 파싱하고, 지난 날짜는 일별 캐시에서 합계를 꺼낸다.
- **비용**: 모델 가격은 LiteLLM 가격표(원격 → 캐시 → 번들 스냅숏 순)로 계산하고 (`src/models.ts:537,1516`), 계산과 집계는 USD로 한다. 세션 캐시에는 대부분 토큰만 두고 비용은 읽을 때마다 현재 가격표로 다시 계산한다 (`src/parser.ts:2984`). 예외는 도구가 직접 기록한 비용을 쓰는 provider(`REPORTED_COST_PROVIDERS`)와 청구 데이터에서 온 호출(`costFromBilling`)이다 (`src/parser.ts:2794,2821`). 통화 변환은 화면에 찍을 때만 한다 (`src/currency.ts:182,192`).
- **같은 CLI를 여러 화면이 공유**: menubar 앱들은 `codeburn status --format menubar-json`을 실행하고, Electron 앱과 VS Code 확장은 `codeburn serve --stdio`를 띄운다. 즉 **주변 앱은 계산하지 않고 CLI 출력만 받는다** (코드 확인: spawn 지점만, 앱 내부는 미확인).

### 주요 기능

근거 표기:
- **README**: README 설명만 근거로 함
- **구조**: 명령과 모듈이 있고 `.description()` 문구가 그렇다는 것까지만 확인함. 동작은 미검증
- **코드 확인**: 동작 코드까지 읽음

이번 세션에서 동작까지 읽은 것은 `report` 흐름뿐이다.

**1) 보기: 어디에 얼마 썼나**

| 기능 | 명령 | 하는 일 | 근거 |
|---|---|---|---|
| 터미널 대시보드 | `codeburn` (= `report`), `today`, `month` | 기간별 비용 합계와 도구·모델·프로젝트·작업별 표. 화살표 키로 기간, `p` 키로 도구를 바꾼다 | 코드 확인 (`src/main.ts:876`, `src/dashboard.tsx:2480`) |
| 짧은 요약 | `status`, `overview` | 오늘과 이번 달 요약. `--format menubar-json`은 주변 앱이 읽는 JSON | 구조 (`src/main.ts:1192`, `:1069`) |
| 세션·모델 상세 | `sessions`, `models` | 세션별 상세, 모델별 토큰·비용 표(작업 종류나 에이전트별로 나눌 수 있음) | 구조 (`src/main.ts:3048`, `:2898`) |
| 비교 | `compare`, `compare-periods` | 두 모델을 나란히 비교하거나, 두 기간의 차이(B − A)를 계산 | 구조 (`src/main.ts:2600`, `:2720`) |
| 컨텍스트 분석 | `context [session]` | 세션의 컨텍스트 창을 무엇이 채웠는지 역할·블록·도구별로 분해(실험 기능) | 구조 (`src/main.ts:2491`) |
| 성과 연결 | `yield`, `spend` | `yield`는 main에 반영된 작업과 버려진 작업의 비용을 나눈다(실험 기능). `spend`는 모델 × 프로젝트 비용 흐름 데이터를 출력 | 구조 (`src/main.ts:3197`, `:3222`) |
| 검증·진단 | `audit`, `doctor` | `audit`은 provider 원본 토큰 값과 표시 값·비용 계산을 대조한다. `doctor`는 provider별로 탐색 경로, 찾은 세션, 파싱 상태를 보여 준다 | 구조 (`src/main.ts:2846`, `:3313`) |
| 내보내기 | `export` | CSV 또는 JSON 파일로 저장 | 구조 (`src/main.ts:1519`) |

**2) 고치기: 낭비 찾기와 설정 변경**

| 기능 | 명령 | 하는 일 | 근거 |
|---|---|---|---|
| 낭비 탐지 | `optimize` | 세션과 설정을 읽고 낭비 후보를 찾는다(매 턴 다시 읽는 파일, 쓰지 않는 MCP 서버, 너무 긴 `CLAUDE.md` 등). 각 후보에 등급, 해결책, 예상 절감액을 붙인다 | README, 구조 (`src/main.ts:2416`) |
| 자동 적용과 되돌리기 | `optimize --apply`, `act list/undo/report` | 설정 변경을 백업 후 적용하고 되돌린다. `act report`는 적용한 지 3일 지난 변경의 예상 절감과 실제 절감을 비교 | README, 구조 (`src/act/cli.ts:13-108`) |

**3) 예산과 한도**

| 기능 | 명령 | 하는 일 | 근거 |
|---|---|---|---|
| 구독 플랜 | `plan` | 쓰는 구독(예: `claude-max`)을 등록하면 플랜 사용률과 이번 달 초과 예상을 보여 준다 | README, 구조 (`src/main.ts:2234`) |
| 예산 | `budget` | 지출 예산을 정하고 현재 지출과 비교 | 구조 (`src/main.ts:1123`) |
| 실시간 한도 | `quota` | 로그인된 도구에서 5시간·주간 한도 창을 읽어 온다 | README, 구조 (`src/main.ts:3330`) |
| 지출 상한 | `guard install/status/uninstall` | Claude Code hook을 설치해 세션이 $5를 넘으면 경고하고 $15에서 멈춘다(기본값, 변경 가능) | 기본값만 코드 확인 (`src/guard/store.ts:55-56`), 나머지 README |

**4) 비용 계산 조정**

| 명령 | 하는 일 | 근거 |
|---|---|---|
| `currency [code]` | 표시 통화 설정. 저장은 USD, 표시할 때만 환산 | 코드 확인 (`src/currency.ts:182,192`) |
| `model-alias` | provider가 쓰는 모델 이름을 가격표의 표준 이름에 연결 | 구조 (`src/main.ts:1773`) |
| `price-override` | 모델 가격을 직접 지정하거나 추가(100만 토큰당 USD) | 구조 (`src/main.ts:1830`) |
| `model-flat-rate` | 정액제 모델로 표시해 비용을 $0으로 계산 | 구조 (`src/main.ts:1975`) |
| `model-savings` | 로컬 모델 사용량을 유료 모델 기준의 "절감액"으로 표시 | 구조 (`src/main.ts:1916`) |
| `proxy-path` | 구독 기반 프록시를 거친 프로젝트의 비용을 "구독이 부담한 비용"으로 분리 | 구조 (`src/main.ts:2056`) |
| `project link`, `gateway-totals`, `import cursor` | 폴더를 프로젝트에 묶기, Vercel AI Gateway 합산 여부 정하기, Cursor 공식 CSV로 추정치 대체 | 구조 (`src/main.ts:2130`, `:2206`, `:1707`) |

**5) 다른 화면과 연동**

| 기능 | 명령 / 위치 | 하는 일 | 근거 |
|---|---|---|---|
| 웹 대시보드 | `web` | `dash/`(Vite + React)를 로컬에서 띄운다 | 구조 (`src/main.ts:1161`, `src/web-dashboard.ts`) |
| menubar·tray | `menubar`, `mac/`, `windows/`, `gnome/` | macOS 메뉴 막대, Windows 트레이, GNOME 패널. 셋 다 `status --format menubar-json`을 실행 | spawn 지점 코드 확인, 앱 내부 미확인 |
| 데스크톱 앱·VS Code | `app/`(Electron), `vscode/` | `serve --stdio` 상주 서버로 질의해서 매번 CLI를 새로 띄우는 비용을 줄인다 | spawn 지점 코드 확인 (`app/electron/cli.ts:1041`, `vscode/src/extension.ts:7`) |
| MCP 서버 | `mcp` | 에이전트에게 `get_usage`, `get_savings` 도구를 제공. 프로젝트 이름은 기본으로 가명 처리 | 도구 이름 코드 확인 (`src/mcp/server.ts:47-96`, `src/mcp/redact.ts:29`) |
| 여러 기기 합산 | `share`, `devices`, `identity` | 다른 기기와 사용량을 공유하고 합쳐 본다 | 구조 (`src/main.ts:930-1054`) |
| 원격 전송 | `sync setup/push/auto` | 사용량 telemetry를 원격 OTLP endpoint로 보낸다(사용자가 설정할 때만) | 구조 (`src/sync/cli.ts:113-114`) |
| 플러그인 | `plugin list/info/verify/add` | 플러그인을 로드하고 검증. 플러그인이 명령을 추가할 수 있다 | 구조 (`src/plugins/cli.ts:28-177`) |
| 관리 | `update`, `antigravity-hook` | CLI·menubar·데스크톱 앱 업데이트, Antigravity CLI 사용량 수집 hook 설치 | 구조 (`src/main.ts:1629`, `:3261`) |

**지원 도구**
- provider 43개: core 32개와 선택적으로 불러오는 lazy 11개 (코드 확인, `src/providers/index.ts:200-204`). README 제목은 "Works with 42 tools"인데, `pi.ts` 하나가 `pi`와 `omp` 두 provider를 내보내서 개수가 하나 다른 것으로 보인다 (`추론`).

**개인정보** (README 기준, CLI 부분만 일부 확인)
- 계정, API 키, 프록시 없이 디스크의 파일만 읽는다.
- CLI는 아무것도 전송하지 않는다고 README가 밝힌다. 데스크톱 앱과 Windows 트레이만 동의를 받은 뒤 익명 telemetry를 보낸다. 다만 `sync`를 설정하면 사용자가 지정한 OTLP endpoint로 데이터가 나간다 (`src/sync/cli.ts:114`).
- 가격표(LiteLLM)와 환율(Frankfurter)은 네트워크에서 받아 온다 (`src/models.ts:93`, `src/currency.ts:15`). README의 "phoning home 없음"은 사용 데이터를 보내지 않는다는 뜻이고, 이런 공개 데이터 조회까지 없다는 뜻은 아니다 (`추론`).

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | CLI → TUI → parser → provider → 로그, 그리고 두 캐시 |
| 대표 실행 흐름 | [report-flow.json](./diagrams/report-flow.json) | [report-flow.html](./diagrams/report-flow.html) | `codeburn report` 한 번이 화면에 그려지기까지 |

검증: 두 그림 모두 archify `deliver --quality showcase` 통과, `visual-check` 통과(1440×900~2048×1320, light/dark). 구조도는 노드마다 `sources`(파일:줄)를 달고 `--repo-root`로 실제 파일 존재를 검사했다. 스크린숏을 한 번 직접 보고 글자 겹침이 없는지만 확인했다.

### 그림 읽는 가이드
1. **가운데 가로줄이 주 경로**다: `CLI → Ink TUI → parser → provider registry → 에이전트 로컬 로그`.
2. **parser 아래 세션 캐시**: 파일마다 fingerprint(크기·수정 시각 등)를 비교해 "변경 없음 / 뒤에 덧붙음 / 전체 재파싱"을 정한다. 재파싱할 양이 200MB 이상이면 `parse workers`(worker_threads)로 나눈다 (Claude, Codex만).
3. **TUI 아래 usage-aggregator와 일별 캐시**: 오늘 분량은 방금 파싱한 결과로, 지난 날짜는 일별 캐시로 채워 기간 합계(`PeriodData`)를 만든다.
4. **왼쪽 위 주변 앱**은 CLI를 실행해서 JSON을 받는 소비자일 뿐이다.

### report 흐름 요약 (코드 확인)

| 단계 | 함수 | 위치 | 넘기는 데이터 |
|---|---|---|---|
| 1 | `preAction` 훅: 설정, 모델 별칭·가격 덮어쓰기, 환율 로드 | `src/main.ts:558-583` | 모듈 전역 상태 |
| 2 | `report` action → `renderDashboard` | `src/main.ts:887-926`, `src/dashboard.tsx:2480` | 기간, provider 필터 |
| 3 | `assembleDashboardData` | `src/dashboard.tsx:2284` | — |
| 4 | `parseAllSessions` → 캐시 상태로 3갈래(메모리 hit / cold 하이드레이션 / refresh lock) | `src/parser.ts:6299-6458` | — |
| 5 | `discoverAllSessionsWithFailures` | `src/providers/index.ts:298` | `SessionSource[]` |
| 6 | Claude는 `scanProjectDirs`, 나머지는 `parseProviderSources` | `src/parser.ts:2123`, `:3610` | `ParsedProviderCall` → `CachedTurn` |
| 7 | 캐시에서 되살리며 비용 재계산 + 분류 | `src/parser.ts:3046` → `calculateCost`, `classifyTurn` (`src/classifier.ts:200`) | `ClassifiedTurn` → `SessionSummary` → `ProjectSummary` |
| 8 | `saveCache` | `src/session-cache.ts:2390` | provider별·UTC 일별 piece + index + `envelope.json`(마지막에 기록) |
| 9 | `buildDurablePeriod` → `ensureCacheHydrated` | `src/usage-aggregator.ts:908`, `src/daily-cache.ts:1703` | `PeriodData` |
| 10 | Ink 렌더 (`InteractiveDashboard` / 비TTY는 `StaticDashboard`) | `src/dashboard.tsx:2522-2551` | 화면 |

- 단계 7에서 비용을 **캐시에 저장된 값 그대로 쓰지 않고, 읽을 때마다 현재 가격표로 다시 계산**한다 (`src/parser.ts:2984`). 가격표가 바뀌어도 캐시를 버릴 필요가 없게 한 것으로 보인다 (`추론`).
- 이 표의 일부(캐시 3갈래, 워커 기준)는 하위 에이전트가 코드에서 찾고 내가 핵심 줄만 다시 확인했다. `ensureCacheHydrated`의 backfill 알고리즘, `withSinglePassParse`가 실제로 중복 파싱을 막는지는 `미확인`.

---

## 4. 핵심 질문 및 세부 답변 목록 (Questions)

아직 답한 질문은 없다. 다음 후보 중에서 고르면 된다(추천 순).

1. **캐시가 어떻게 "바뀐 부분만" 다시 읽나?** `fingerprintFile`/`reconcileFile`의 3가지 결과(변경 없음 / 덧붙음 / 전체 재파싱)와 `CachedFile` 구조. 실행해서 두 번째 실행이 빠른지 볼 수 있다.
2. **비용은 정확히 어떻게 계산되나?** Claude 로그 한 줄의 `usage` → `calculateCost`까지. 캐시 읽기/쓰기 토큰 가격, 모델 별칭, 가격표 3단 폴백.
3. **provider 하나는 어떻게 생겼나?** Claude(대표) 하나를 끝까지 보고 Codex와 차이만 비교. 새 도구를 추가하려면 무엇을 구현해야 하는지.
4. **여러 프로세스가 동시에 돌면?** menubar가 주기적으로 `status`를 부르는 동안 사용자가 `report`를 열면 생기는 경쟁을 `hydrating.lock`/`session-refresh.lock`이 어떻게 막는지.
5. **작업 분류(classifier)는 무엇을 근거로 하나?** `classifyTurn`이 도구 호출과 bash 명령으로 coding/debugging 등을 정하는 규칙. 이전 노트 [[codeburn-turn-classification-engine]]와 차이도 확인.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **이전 wiki 요약**: 2026-10-16 삭제. 원문은 `git show b52364d:wiki/projects/codeburn.md`
- **외부 자료**: `artifacts/codeburn/deepwiki/` (이전 기준의 DeepWiki 추출본, 참고용)
