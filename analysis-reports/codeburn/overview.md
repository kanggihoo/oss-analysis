# codeburn 코드베이스 개요

## 1. 이 프로젝트의 목적

CodeBurn은 로컬 디스크에 남아 있는 여러 AI 코딩 도구의 세션 데이터를 읽어, 토큰 사용량과 비용을 날짜, 프로젝트, 모델, provider, 작업 유형 단위로 보여주는 TypeScript 기반 CLI/TUI 도구다. README는 "See where your AI coding tokens go"를 핵심 설명으로 두고, Claude Code, Codex, Cursor, Gemini CLI, Copilot, OpenCode 등 19개 AI 코딩 도구를 지원한다고 설명한다.

중요한 설계 방향은 "wrapper/proxy가 아니라 로컬 로그 분석기"라는 점이다. API 키를 가로채거나 실행을 감싸지 않고, 각 도구가 이미 저장한 JSONL, SQLite, VS Code extension 데이터, 기타 로컬 저장소를 읽어 공통 구조로 정규화한다. 비용 계산은 `src/models.ts`의 LiteLLM 가격 데이터와 내장 fallback/alias 정책을 통해 수행한다.

## 2. 프로젝트 유형과 사용 방식

프로젝트 유형은 npm 배포형 Node.js CLI 애플리케이션이며, 기본 화면은 Ink/React 기반 TUI다. 동시에 macOS menubar 앱과 GNOME Shell extension이 별도 UI 클라이언트로 존재한다. 이 두 GUI는 자체적으로 세션을 파싱하지 않고 `codeburn status --format menubar-json`을 실행해 CLI 출력 계약을 소비한다.

대표 사용 방식은 다음과 같다.

```bash
codeburn
codeburn today
codeburn month
codeburn report -p 30days
codeburn report --from 2026-04-01 --to 2026-04-10
codeburn status --format json
codeburn export -f json
codeburn optimize
codeburn compare
codeburn models --by-task
```

패키지 엔트리는 `package.json`의 `bin.codeburn = dist/cli.js`이고, 소스 런처는 `src/cli.ts`다. `src/cli.ts`는 Node.js 버전을 검사한 뒤 `src/main.ts`를 동적 import한다.

## 3. 핵심 기능

- 기간별 비용/토큰 집계: Today, 7 Days, 30 Days, Month, 6 Months, `--from/--to` 커스텀 범위.
- 프로젝트별 집계: 세션의 cwd 또는 provider가 제공하는 프로젝트 정보를 `ProjectSummary`로 묶는다.
- provider별 분석: Claude, Codex, Cursor, Gemini, Copilot, OpenCode 등 provider별 저장소 차이를 `src/providers/*`에서 흡수한다.
- 모델/작업 유형 분석: `src/classifier.ts`, `src/model-efficiency.ts`, `src/models-report.ts`가 모델별 비용, one-shot rate, 작업 카테고리별 비용을 만든다.
- TUI 대시보드: `src/dashboard.tsx`가 기간 탭, 프로젝트/모델/활동/도구/MCP/쉘 명령 패널을 렌더링한다.
- 최적화 제안: `src/optimize.ts`가 중복 read, MCP 과다 노출, bash 출력 과다, bloated `CLAUDE.md`, context bloat 같은 waste finding을 만든다.
- 모델 비교: `src/compare.tsx`, `src/compare-stats.ts`가 두 모델의 비용/효율/작업 유형별 성능을 비교한다.
- 메뉴바/패널 표시: `src/menubar-json.ts`의 계약을 macOS Swift 앱과 GNOME extension이 소비한다.
- export: `src/export.ts`가 CSV/JSON 파일로 분석 결과를 저장한다.

## 4. 실행/사용 진입점

가장 중요한 진입점은 다음 순서로 읽으면 된다.

- `src/cli.ts`: 실행 파일 런처. Node.js `>=22.13.0`을 요구하고 `main.js`를 import한다.
- `src/main.ts`: Commander.js 기반 CLI 등록부. `report`가 기본 명령이며 `status`, `today`, `month`, `export`, `menubar`, `currency`, `model-alias`, `plan`, `optimize`, `compare`, `models`, `yield`를 등록한다.
- `src/parser.ts`: raw 세션 로그와 provider parser 결과를 `ProjectSummary[]`로 정규화하는 중심 파이프라인.
- `src/dashboard.tsx`: TUI 실행과 refresh, 키 입력, provider/period 전환.
- `src/providers/index.ts`: provider registry. `discoverAllSessions`, `getAllProviders`, `getProvider`가 provider 계층의 공개 진입점이다.

CLI 외 UI 진입점은 `mac/Sources/CodeBurnMenubar/CodeBurnApp.swift`와 `gnome/extension.js`다. 둘 다 최종적으로 CLI를 subprocess로 실행한다.

## 5. 주요 모듈과 책임

- `src/main.ts`: 명령/옵션 등록, 전역 hook, timezone/verbose/config/currency 초기화, 명령별 파이프라인 연결.
- `src/parser.ts`: Claude JSONL 파싱, provider parser 결과 통합, dedup, turn grouping, `SessionSummary`/`ProjectSummary` 생성.
- `src/providers/`: 각 AI 도구의 세션 발견과 파싱. 공통 계약은 `Provider`, `SessionSource`, `SessionParser`, `ParsedProviderCall`.
- `src/models.ts`: LiteLLM 가격 로딩, 모델명 alias/fallback, cache read/write/web search/fast mode 비용 계산.
- `src/classifier.ts`: 도구 사용과 사용자 메시지 패턴으로 `TaskCategory` 분류, edit retry/one-shot 계산 기반 제공.
- `src/day-aggregator.ts`, `src/daily-cache.ts`: 일별 rollup과 `~/.cache/codeburn/daily-cache.json` 관리.
- `src/dashboard.tsx`: Ink 기반 인터랙티브 대시보드.
- `src/menubar-json.ts`: macOS/GNOME이 소비하는 JSON DTO.
- `src/optimize.ts`: waste detector와 health grade 산출.
- `mac/`: SwiftUI/AppKit 기반 macOS menubar 앱.
- `gnome/`: GJS 기반 GNOME Shell extension.
- `docs/providers/`: provider별 저장 위치, 형식, quirks 문서.

## 6. 핵심 개념과 용어

- `Provider`: AI 도구 하나를 CodeBurn에 연결하는 adapter 계약. `discoverSessions()`와 `createSessionParser()`가 핵심이다.
- `ParsedProviderCall`: provider별 raw 데이터를 공통 호출 단위로 바꾼 결과. model, token counts, cost, tools, timestamp, deduplicationKey를 포함한다.
- `ParsedTurn` / `ClassifiedTurn`: 사용자 요청과 assistant call 묶음. `classifyTurn()` 이후 category, retries, hasEdits가 붙는다.
- `SessionSummary`: 세션 하나의 비용, 토큰, 모델, 도구, MCP, bash command, 카테고리 breakdown.
- `ProjectSummary`: 프로젝트 단위 집계. 대시보드와 report/export의 기본 입력이다.
- `DailyEntry`: 일별 비용/콜/세션/모델/category/provider rollup. `daily-cache.json`에 저장된다.
- `menubar-json`: `status --format menubar-json`이 출력하는 GUI 클라이언트용 계약.
- `one-shot rate`: edit turn 중 retry 없이 끝난 비율.
- `model alias`: provider가 내보내는 모델명을 LiteLLM 가격 키로 매핑하는 내장/사용자 alias.

## 7. 입력/데이터/상태/제어 흐름

전체 흐름은 다음과 같다.

```text
CLI command/options
  -> getDateRange / parseDateRangeFlags
  -> parseAllSessions(dateRange, provider)
  -> discoverAllSessions / provider.createSessionParser
  -> ParsedProviderCall 또는 Claude JSONL ParsedApiCall
  -> classifyTurn
  -> SessionSummary
  -> ProjectSummary[]
  -> filterProjectsByName
  -> dashboard / json report / export / menubar-json / optimize / compare
```

Claude는 `src/parser.ts`가 JSONL을 직접 읽고, 다른 provider는 `src/providers/*`의 `SessionParser.parse()`가 `ParsedProviderCall`을 yield한다. `seenKeys`는 같은 호출이 중복 집계되지 않도록 provider parser와 Claude parser 양쪽에서 사용된다.

일별 화면과 menubar는 성능 때문에 `daily-cache.ts`를 사용한다. 과거 날짜는 캐시에 저장하고, 오늘 데이터는 다시 파싱해 합산한다. 캐시 경로는 기본 `~/.cache/codeburn`이고 `CODEBURN_CACHE_DIR`로 override할 수 있다.

## 8. 설정 및 환경 구성

사용자 설정 파일은 `src/config.ts` 기준 `~/.config/codeburn/config.json`이다. 여기에는 `currency`, `plan`, `modelAliases`가 저장된다. 저장은 임시 파일 후 rename 방식으로 처리한다.

주요 환경/옵션은 다음과 같다.

- `--timezone` 또는 `CODEBURN_TZ`: 날짜 그룹핑용 IANA timezone.
- `--verbose`: `CODEBURN_VERBOSE=1`로 provider/가격 경고를 더 노출.
- `CODEBURN_CACHE_DIR`: CodeBurn 캐시 디렉터리 override.
- `CLAUDE_CONFIG_DIRS`, `CLAUDE_CONFIG_DIR`: Claude 세션/설정 위치 확장.
- `CODEX_HOME`: Codex 세션 위치 override.
- provider별 환경변수: `QWEN_DATA_DIR`, `GOOSE_PATH_ROOT`, `XDG_DATA_HOME`, `CRUSH_GLOBAL_DATA`, `FACTORY_DIR` 등은 provider 구현/문서에 분산되어 있다.
- macOS: `CODEBURN_BIN`으로 CLI 경로 override 가능하며 `CodeburnCLI.swift`에서 인자/경로 검증을 한다.
- GNOME: schema에 refresh interval, default period, disabled providers, custom codeburn path, compact mode 등이 정의되어 있다.

## 9. 의존성 구조

런타임 핵심 의존성은 `commander`, `ink`, `react`, `chalk`, `strip-ansi`다. TypeScript 실행/빌드/테스트는 `tsx`, `tsup`, `typescript`, `vitest`를 사용한다.

빌드는 `tsup.config.ts` 기준 `src/main.ts`를 ESM 단일 번들로 `dist/cli.js`에 출력한다. 다만 `package.json`의 `build` 스크립트는 `tsup` 실행 후 `src/cli.ts`를 `dist/cli.js`로 복사하고 실행 권한을 부여한다. 이는 런처가 Node 버전을 먼저 검사하고 `main.js`를 import하도록 만들기 위한 구조로 보인다.

SQLite가 필요한 provider(Cursor/OpenCode/Goose/Crush 등)는 `src/sqlite.ts`의 `node:sqlite` 래퍼를 통해 접근한다. 무거운 provider는 `src/providers/index.ts`에서 lazy import되어 해당 도구가 없는 사용자에게 비용을 줄인다.

가격 데이터는 `scripts/bundle-litellm.mjs`가 LiteLLM 가격 JSON을 가져와 `src/data/litellm-snapshot.json`으로 번들링한다. 런타임에서는 `src/models.ts`가 24시간 TTL 캐시를 우선 사용하고 실패하면 snapshot으로 fallback한다.

## 10. 빌드/실행/테스트 방식

개발 실행:

```bash
npm install
npm run dev -- status
npm run dev -- report -p week
```

빌드:

```bash
npm run build
```

`npm run build`는 `bundle-litellm` 후 `tsup` 번들을 만들고, CLI 런처를 `dist/cli.js`로 배치한다. `prepublishOnly`도 build를 실행한다.

테스트:

```bash
npm test
```

테스트는 Vitest 기반이며 `tests/`에 CLI, parser, optimize, cache, models, provider fixture 테스트가 있다. 사용자가 테스트 실행은 필요 없다고 했으므로 이번 분석에서는 테스트를 실행하지 않았다.

macOS menubar는 `mac/Package.swift` 기반 Swift package이고, 릴리스 번들은 `mac/Scripts/package-app.sh`로 만든다. GNOME extension은 `gnome/install.sh`가 로컬 extension 디렉터리에 복사하는 구조다.

## 11. 에러 처리와 디버깅 포인트

- Node 버전 미달: `src/cli.ts`에서 즉시 stderr 출력 후 종료.
- 잘못된 period/format/timezone/date: `src/main.ts`, `src/cli-date.ts`에서 명시적으로 실패 처리.
- provider read 실패: JSON parse 실패는 항목 단위 skip, SQLite busy는 한 번만 경고 후 다음 refresh에서 재시도하는 방향.
- 가격 미확인 모델: 기본 비용 0으로 처리하며, 경고는 verbose 조건에서 노출된다. 사용자는 `codeburn model-alias`로 매핑할 수 있다.
- 캐시 파손/버전 불일치: `daily-cache.ts`, provider별 cache가 빈 캐시/fallback/recompute로 이어진다.
- export 파일 저장: `export.ts`는 잘못된 덮어쓰기와 symlink 등 파일 저장 위험을 방어하는 가드를 둔다.
- macOS/GNOME CLI 호출: 인자 allowlist, PATH 보강, timeout, JSON decode 실패 처리가 각각 `CodeburnCLI.swift`/`DataClient.swift`, `gnome/dataClient.js`에 있다.

디버깅할 때는 먼저 `src/main.ts`의 해당 command action, 그 다음 `parseAllSessions`, 마지막으로 대상 provider 파일을 따라가는 것이 빠르다.

## 12. 확장하거나 기여할 때 봐야 할 구조

새 CLI 명령을 추가하려면 `src/main.ts`에서 Commander command를 추가하고, 필요한 공통 집계는 `ProjectSummary[]`를 입력으로 받도록 맞추는 것이 기존 패턴이다.

새 provider를 추가하려면 다음을 봐야 한다.

1. `src/providers/types.ts`의 `Provider`/`ParsedProviderCall` 계약.
2. 비슷한 저장소 형식의 기존 provider. JSONL이면 `codex.ts`/`gemini.ts`, SQLite면 `cursor.ts`/`opencode.ts`, Cline 계열이면 `vscode-cline-parser.ts`.
3. `src/providers/index.ts`에 eager 또는 lazy 등록.
4. `docs/providers/<name>.md` 문서 추가.
5. fixture 기반 provider 테스트 추가. CONTRIBUTING은 새 provider에 실제 데이터 검증 증거를 요구한다.

menubar JSON을 바꾸는 경우 `src/menubar-json.ts`, `src/main.ts`의 `status --format menubar-json` 분기, `mac/Data/MenubarPayload.swift`, GNOME 렌더링 코드를 함께 봐야 한다.

Optimize detector를 추가하려면 `src/optimize.ts`의 detector 흐름과 `tests/optimize.test.ts`의 positive/negative 케이스 패턴을 확인해야 한다.

## 13. 처음 기여자가 먼저 읽어야 할 파일

1. `docs/architecture.md`: 전체 3-surface 구조와 파이프라인 설명.
2. `README.md`: 사용자 관점 기능과 provider 목록.
3. `CONTRIBUTING.md`: 개발/테스트/새 provider 기준.
4. `src/main.ts`: CLI 명령과 실행 흐름.
5. `src/parser.ts`: 공통 데이터 모델로 정규화되는 지점.
6. `src/types.ts`: `ProjectSummary`, `SessionSummary`, `TaskCategory` 등 핵심 타입.
7. `src/providers/types.ts`, `src/providers/index.ts`: provider 계약과 등록 구조.
8. `src/dashboard.tsx`: 기본 TUI 동작.
9. `src/models.ts`: 비용 계산과 모델 alias.
10. 변경 대상이 UI면 `src/menubar-json.ts`, `mac/Data/MenubarPayload.swift`, `gnome/dataClient.js`도 함께 확인.

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

- `gnome/schemas/org.gnome.shell.extensions.codeburn.gschema.xml`의 일부 provider filter 관련 키가 실제 runtime 코드에서 어디까지 반영되는지는 추가 확인이 필요하다. subagent 범위에서는 정의는 확인됐지만 직접 사용 흔적은 명확하지 않았다.
- `menubar-json`에는 명시적인 schema version 필드가 보이지 않는다. 현재는 Swift/GNOME 타입이 동일 계약을 따라가는 구조이므로, 향후 호환성 전략은 별도 확인이 필요하다.
- provider별 실제 비용 정확도는 각 도구의 최신 저장 형식과 모델명 노출 방식에 크게 의존한다. 코드상 fallback/alias는 많지만, 새 provider나 모델 변경은 실제 세션 데이터로 검증해야 한다.
- 이번 요청에 따라 테스트는 실행하지 않았다. 분석은 README, architecture 문서, package/build 파일, 주요 소스 파일, subagent 범위 분석 결과에 기반한다.
