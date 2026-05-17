# RTK 코드베이스 이해 보고서

분석 대상: `/Users/kkh/Desktop/opensource분석/rtk`

분석 방식:
- 루트 구조, README, Cargo 설정, 파일 분포, 주요 entry point를 먼저 확인했다.
- 이후 `codebase_mapper` 서브에이전트 4개로 범위를 나눠 병렬 분석했다.
- 분석 범위는 `main/Cargo/build`, `core/parser/filters`, `cmds/analytics/discover/learn`, `hooks/docs/tests/scripts`이다.
- 이 보고서는 이해 목적의 구조 분석이며 코드 리뷰, 보안 감사, 리팩터링 제안이 아니다.

## 1. 이 프로젝트의 목적

RTK, 즉 Rust Token Killer는 LLM 기반 코딩 도구가 쉘 명령 결과를 컨텍스트에 넣기 전에 출력량을 줄이기 위한 Rust CLI 프록시다. README는 RTK를 “command outputs before they reach your LLM context” 단계에서 필터링하고 압축하는 단일 Rust 바이너리로 설명한다.

핵심 목적은 다음과 같다.

- `git status`, `git diff`, `cargo test`, `pytest`, `rg`, `ls`, `aws`, `docker` 같은 개발 명령의 원본 출력을 요약한다.
- AI agent hook/plugin이 사용자의 원래 명령을 `rtk <command>` 형태로 재작성하게 해 사용자가 매번 직접 `rtk`를 입력하지 않아도 되게 한다.
- 원본 대비 축약 출력의 토큰 절감량을 SQLite 기반 tracking DB에 기록하고 `rtk gain`, `rtk session`, `rtk discover` 같은 분석 명령으로 보여준다.

주요 근거:
- `/Users/kkh/Desktop/opensource분석/rtk/README.md`
- `/Users/kkh/Desktop/opensource분석/rtk/docs/contributing/ARCHITECTURE.md`
- `/Users/kkh/Desktop/opensource분석/rtk/src/main.rs`

## 2. 프로젝트 유형과 사용 방식

프로젝트 유형은 Rust 기반 CLI proxy/tooling 프로젝트다. 단일 바이너리 `rtk`가 중심이고, AI agent와의 자동 통합을 위해 hook/plugin 파일도 함께 제공한다.

사용 방식은 크게 두 가지다.

1. 직접 호출
   - 예: `rtk git status`, `rtk read file.rs`, `rtk cargo test`, `rtk grep pattern .`
   - `src/main.rs`의 `Cli`, `Commands` enum과 `run_cli()`가 clap 기반으로 명령을 파싱하고 하위 모듈에 위임한다.

2. Hook 기반 자동 재작성
   - 예: 사용자가 Claude Code/Codex/Cursor 등에서 `git status`를 실행하면 hook이 이를 `rtk git status`로 바꾸는 구조다.
   - `rtk init`이 agent별 hook/plugin/awareness 파일을 설치한다.
   - `rtk rewrite <cmd>` 또는 `rtk hook <agent>`가 재작성 경로의 핵심 entry point다.

규모는 `src` 중심 Rust 파일 100개 이상, 책임 디렉터리 6개 이상인 중간 규모 이상의 CLI 프로젝트로 판단된다.

## 3. 핵심 기능

- CLI 라우팅: `src/main.rs`가 clap 기반 명령 스키마와 실행 분기를 담당한다.
- 명령별 출력 필터링: `src/cmds`가 git, rust, js, python, go, dotnet, cloud, system, ruby 등 생태계별 adapter를 제공한다.
- 공통 실행 파이프라인: `src/core/runner.rs`, `src/core/stream.rs`가 외부 명령 실행, stdout/stderr 수집, 필터 적용, exit code 반환을 표준화한다.
- TOML 필터 DSL: `src/core/toml_filter.rs`와 `src/filters/*.toml`이 Rust 코드 없이 정규식 기반 필터를 추가하는 경로를 제공한다.
- Tracking: `src/core/tracking.rs`가 raw output 대비 filtered output의 토큰 절감량을 SQLite에 기록한다.
- Tee recovery: `src/core/tee.rs`가 축약 때문에 원본이 필요할 때 `[full output: ...]` 힌트로 원본 덤프 위치를 제공한다.
- Hook/rewrite: `src/hooks`, `hooks/`, `src/discover/registry.rs`, `src/discover/rules.rs`가 agent 입력 명령을 RTK 명령으로 바꾸는 계층이다.
- 분석/학습: `src/analytics`, `src/discover`, `src/learn`이 세션 분석, gain 계산, correction rule 생성을 담당한다.

## 4. 실행/사용 진입점

주요 실행 진입점은 다음과 같다.

- `/Users/kkh/Desktop/opensource분석/rtk/src/main.rs`
  - `main()`
  - `run_cli()`
  - `run_fallback()`
  - `Cli`, `Commands`, `HookCommands`
- `/Users/kkh/Desktop/opensource분석/rtk/src/hooks/rewrite_cmd.rs`
  - `run(cmd: &str)`
  - hook 스크립트가 명령 재작성을 위임하는 얇은 bridge다.
- `/Users/kkh/Desktop/opensource분석/rtk/src/hooks/hook_cmd.rs`
  - `run_claude()`, `run_cursor()`, `run_gemini()`, `run_copilot()`
  - agent별 JSON/protocol 입력을 처리한다.
- `/Users/kkh/Desktop/opensource분석/rtk/src/core/runner.rs`
  - `run_filtered()`, `run_streamed()`, `run_passthrough()`
  - 명령 adapter가 가장 자주 호출하는 공통 실행 wrapper다.

빌드 진입점:
- `/Users/kkh/Desktop/opensource분석/rtk/build.rs`
  - `src/filters/*.toml`을 빌드 시점에 병합해 built-in filter 리소스로 만든다.

## 5. 주요 모듈과 책임

`src/main.rs`
- CLI schema, top-level routing, fallback 실행 정책을 담당한다.
- 알 수 없는 명령이 들어왔을 때 `run_fallback()`으로 TOML 필터 매칭 또는 passthrough 실행을 시도한다.

`src/cmds`
- 외부 CLI별 adapter 계층이다.
- 각 모듈은 실제 명령을 실행하고 raw output을 파싱/요약한 뒤 tracking에 연결한다.
- 예: `git/git.rs`, `rust/cargo_cmd.rs`, `js/lint_cmd.rs`, `python/ruff_cmd.rs`, `go/go_cmd.rs`, `cloud/aws_cmd.rs`, `system/read.rs`.

`src/core`
- 특정 도구 지식이 없는 공통 인프라 계층이다.
- 실행 runner, streaming, tee, tracking, telemetry, config, TOML filter engine, utility를 제공한다.

`src/filters`
- 빌트인 TOML 필터 정의 디렉터리다.
- `build.rs`가 이 파일들을 병합해 런타임에 내장 필터로 사용할 수 있게 한다.

`src/discover`
- 명령 재작성 규칙과 세션 분석을 담당한다.
- `registry.rs`는 command classification/rewrite의 중심이고, `rules.rs`는 RTK로 바꿀 수 있는 명령 패턴 목록이다.

`src/hooks`와 `hooks`
- `src/hooks`는 설치, 무결성, 권한, trust, hook command bridge 같은 lifecycle 관리 계층이다.
- 루트 `hooks/`는 실제 agent별 스크립트/plugin/README를 담는다.

`src/analytics`
- tracking DB와 Claude usage 정보를 읽어 gain, session, economics 분석을 만든다.

`src/learn`
- 세션 로그에서 실패 후 수정 패턴을 찾아 CLI correction rule을 생성한다.

`docs`, `scripts`, `tests`
- `docs/contributing/ARCHITECTURE.md`, `docs/contributing/TECHNICAL.md`는 설계 문서다.
- `scripts/test-all.sh`, `scripts/check-installation.sh`, `scripts/test-tracking.sh`는 통합/설치/추적 검증 단서를 제공한다.
- `tests/fixtures`는 외부 명령 출력 fixture 중심이며, Rust 단위 테스트는 주로 각 `src/*` 파일 내부 `#[cfg(test)]`에 있다.

## 6. 핵심 개념과 용어

- CLI proxy: 사용자의 원래 명령을 대신 실행하고 출력만 압축해 반환하는 방식.
- Adapter: 외부 CLI 하나 또는 도구군 하나를 실행/파싱/요약하는 `src/cmds` 모듈.
- Filter mode: `CaptureOnly`, `Buffered`, `Streaming`, `Passthrough`.
- TOML filter: Rust 코드 없이 정규식과 단계별 transform으로 출력을 줄이는 규칙.
- Tracking: raw/filtered output의 토큰 추정치와 절감량을 SQLite에 저장하는 기능.
- Tee: 축약된 출력 뒤에 원본 파일 위치를 남겨 필요할 때 복구할 수 있게 하는 기능.
- Rewrite: `git status` 같은 원래 명령을 `rtk git status`로 변환하는 기능.
- Hook: Claude/Cursor/Copilot/Codex 등 AI agent의 command execution 전 단계에 끼워 넣는 통합 지점.
- Discover: 기존 세션에서 RTK 적용 기회를 분석하거나 rewrite 가능성을 분류하는 기능.
- Learn: 실패한 명령과 후속 수정 명령의 패턴을 찾아 규칙 후보를 만드는 기능.

## 7. 입력/데이터/상태/제어 흐름

직접 호출 흐름:

1. 사용자가 `rtk git status` 같은 명령을 실행한다.
2. `src/main.rs::run_cli()`가 clap으로 인자를 파싱한다.
3. `Commands` match 분기가 `cmds::git::git::run(...)` 같은 adapter로 위임한다.
4. adapter는 `core::runner::run_filtered()` 또는 `run_streamed()`를 통해 실제 외부 명령을 실행한다.
5. raw stdout/stderr를 파싱하거나 정규식/상태기계/JSON parser로 축약한다.
6. filtered output을 사용자에게 출력한다.
7. `core::tracking::TimedExecution::track()`이 raw/filtered 토큰 추정치와 실행 시간을 저장한다.
8. `main()`이 adapter가 반환한 exit code로 종료한다.

Hook 기반 흐름:

1. 사용자가 AI agent에서 `git status` 같은 일반 쉘 명령을 실행한다.
2. agent별 hook/plugin이 command payload를 읽는다.
3. hook이 `rtk rewrite <cmd>` 또는 `rtk hook <agent>`를 호출한다.
4. `src/discover/registry.rs`와 `src/discover/rules.rs`가 명령을 재작성할 수 있는지 판단한다.
5. agent protocol에 맞는 JSON이나 updated input으로 `rtk git status`를 반환한다.
6. agent가 재작성된 명령을 실행하면 직접 호출 흐름으로 이어진다.

Fallback 흐름:

1. clap parsing이 실패했지만 help/version/meta command가 아니면 `run_fallback()`이 동작한다.
2. `core::toml_filter::find_matching_filter()`로 TOML 필터가 있는지 찾는다.
3. 필터가 있으면 raw output에 TOML DSL을 적용한다.
4. 필터가 없으면 passthrough 실행한다.

## 8. 설정 및 환경 구성

주요 설정 파일/디렉터리:

- `~/.config/rtk/config.toml`
  - `[tracking]`, `[display]`, `[filters]`, `[tee]`, `[telemetry]`, `[hooks]`, `[limits]` 섹션 단서가 있다.
- `.rtk/filters.toml`
  - 프로젝트 로컬 필터이며 trust가 필요하다.
- `~/.local/share/rtk/history.db` 또는 플랫폼별 data dir
  - tracking DB 위치로 사용된다.

주요 환경 변수:

- `RTK_NO_TOML=1`: TOML 필터 탐색 스킵.
- `RTK_TOML_DEBUG=1`: TOML 필터 디버그.
- `RTK_TEE=0`: tee 비활성화.
- `RTK_TEE_DIR`: tee raw output 저장 위치 제어.
- `RTK_DISABLED=1`: hook rewrite 비활성화 경로.
- `RTK_HOOK_AUDIT=1`: hook rewrite audit log.
- `RTK_TELEMETRY_DISABLED=1`: telemetry 비활성화.

설치/통합 설정:

- `rtk init -g`는 Claude Code/Copilot 기본 통합을 설치한다는 README 단서가 있다.
- `rtk init --codex`, `rtk init --agent cursor`, `rtk init --agent hermes` 등 agent별 모드가 있다.
- `src/hooks/init.rs`, `src/hooks/constants.rs`, `hooks/*`가 실제 설치 대상 파일과 payload를 관리한다.

## 9. 의존성 구조

주요 Rust 의존성은 `Cargo.toml`에 있다.

- CLI/parser: `clap`, `anyhow`
- 출력 파싱/규칙: `regex`, `lazy_static`, `serde`, `serde_json`, `toml`, `quick-xml`
- 파일/경로/환경: `dirs`, `walkdir`, `ignore`, `which`, `tempfile`
- 저장/시간: `rusqlite`, `chrono`
- 보안/무결성: `sha2`, `getrandom`
- 네트워크/telemetry: `ureq`, `flate2`
- 표시: `colored`
- 모듈 선언 편의: `automod`

내부 의존성 방향은 대체로 다음과 같다.

- `main.rs` -> `cmds`, `core`, `hooks`, `discover`, `analytics`, `learn`
- `cmds` -> `core::runner`, `core::stream`, `core::tracking`, `core::utils`
- `hooks::rewrite_cmd` -> `discover::registry`
- `discover` -> rules/provider/report 기반 분석 및 rewrite
- `analytics` -> `core::tracking` 읽기
- `core`는 가능한 한 명령별 지식이 없는 공통 leaf 인프라로 설계되어 있다.

## 10. 빌드/실행/테스트 방식

빌드:

- 표준 Rust 프로젝트이므로 기본 빌드는 `cargo build`, 테스트는 `cargo test`로 추정 가능하며, 루트에 `Cargo.toml`과 `Cargo.lock`이 있다.
- `Cargo.toml`의 release profile은 `opt-level = 3`, `lto = true`, `panic = "abort"`, `strip = true`로 성능/바이너리 크기 최적화를 지향한다.
- `Cargo.toml` lint는 `unsafe_code = "deny"`, `warnings = "deny"`다.
- `build.rs`가 `src/filters` 변경에 반응하고 built-in TOML filter를 생성한다.

설치:

- README 기준 Homebrew, install script, `cargo install --git` 경로가 있다.
- 패키징 메타데이터로 deb/rpm asset 설정도 포함되어 있다.

테스트:

- 각 Rust 모듈 내부에 `#[cfg(test)] mod tests`가 넓게 존재한다.
- `tests/fixtures`는 dotnet, glab, golangci, gradlew 등 외부 도구 출력 fixture를 담는다.
- `scripts/test-all.sh`, `scripts/test-tracking.sh`, `scripts/check-installation.sh`, `scripts/check-test-presence.sh`가 보조 검증 경로다.
- `scripts/benchmark/*`는 benchmark/report 파이프라인 단서를 제공한다.

## 11. 에러 처리와 디버깅 포인트

공통 정책:

- exit code preservation을 중요 설계 원칙으로 둔다.
- 필터링 실패 시 가능하면 raw passthrough 또는 경고 후 원본 보존 경로를 선택한다.
- tee hint는 축약된 결과만으로 부족할 때 원본을 회수할 수 있게 한다.

주요 디버깅 지점:

- `src/main.rs::run_fallback()`: clap parse 실패 후 일반 명령으로 fallback할지 결정한다.
- `src/core/stream.rs`: stdout/stderr 병렬 처리, streaming mode, raw cap, broken pipe 처리가 있다.
- `src/core/toml_filter.rs`: TOML DSL parse/compile 실패, trust gate, filter priority 확인 지점이다.
- `src/core/tracking.rs`: tracking DB write/query, parse failure 기록 지점이다.
- `src/hooks/permissions.rs`: Claude Code류 permission allow/ask/deny 판단 지점이다.
- `src/hooks/integrity.rs`: hook SHA-256 무결성 검증 지점이다.
- `src/discover/registry.rs`: rewrite가 안 되거나 엉뚱하게 되는 경우 가장 먼저 볼 파일이다.
- `src/core/tee.rs`: `tee_and_hint()`는 실패 중심 원본 회수 경로이고, `force_tee_hint()`는 성공했지만 출력이 잘린 경우 원본 회수 힌트를 강제로 남기는 경로다.
- `src/cmds/cloud/curl_cmd.rs`, `src/cmds/cloud/aws_cmd.rs`: `force_tee_hint()`의 실제 호출 지점이다. `curl` 긴 텍스트 출력, `aws`/`s3` 출력 truncation 상황에서 성공 케이스 recovery hint로 사용된다.

## 12. 확장하거나 기여할 때 봐야 할 구조

새 명령 adapter를 추가할 때:

1. `src/cmds/README.md`를 읽고 adapter 패턴을 확인한다.
2. 해당 생태계 디렉터리(`src/cmds/git`, `src/cmds/js`, `src/cmds/python` 등)에 모듈을 추가한다.
3. 가능하면 `core::runner::run_filtered`, `run_streamed`, `run_passthrough` 중 하나를 사용한다.
4. JSON 강제 출력, 상태기계, regex block filter, passthrough 조건 중 적절한 파싱 전략을 선택한다.
5. `src/main.rs`의 `Commands` enum과 `run_cli()` match 분기에 연결한다.
6. hook rewrite까지 지원하려면 `src/discover/rules.rs`와 `src/discover/registry.rs` 경로를 확인한다.
7. 관련 단위 테스트와 fixture를 추가한다.

새 TOML filter를 추가할 때:

1. `src/filters/README.md`와 기존 `src/filters/*.toml`을 확인한다.
2. 필터 이름 중복과 테스트 정의를 주의한다.
3. `build.rs`가 built-in filter로 병합하므로 빌드 시 검증된다.

새 agent hook을 추가할 때:

1. `src/hooks/README.md`를 읽는다.
2. `src/hooks/init.rs`, `src/hooks/constants.rs`, `src/hooks/hook_check.rs`, `src/hooks/integrity.rs`를 함께 확인한다.
3. 필요하면 `src/hooks/hook_cmd.rs`에 agent protocol processor를 추가한다.
4. 루트 `hooks/<agent>/`에 script/plugin/README를 둔다.
5. `docs/guide/getting-started/supported-agents.md` 계열 문서를 갱신한다.

분석 기능을 확장할 때:

- session/rewrite opportunity 분석은 `src/discover`.
- gain/economics/session 통계는 `src/analytics`.
- 실패-수정 패턴 학습은 `src/learn`.
- DB schema/집계 변경은 `src/core/tracking.rs`.

## 13. 처음 기여자가 먼저 읽어야 할 파일

우선순위 순서:

1. `/Users/kkh/Desktop/opensource분석/rtk/README.md`
2. `/Users/kkh/Desktop/opensource분석/rtk/docs/contributing/ARCHITECTURE.md`
3. `/Users/kkh/Desktop/opensource분석/rtk/docs/contributing/TECHNICAL.md`
4. `/Users/kkh/Desktop/opensource분석/rtk/src/main.rs`
5. `/Users/kkh/Desktop/opensource분석/rtk/src/cmds/README.md`
6. `/Users/kkh/Desktop/opensource분석/rtk/src/core/README.md`
7. `/Users/kkh/Desktop/opensource분석/rtk/src/core/runner.rs`
8. `/Users/kkh/Desktop/opensource분석/rtk/src/core/stream.rs`
9. `/Users/kkh/Desktop/opensource분석/rtk/src/core/tracking.rs`
10. `/Users/kkh/Desktop/opensource분석/rtk/src/discover/registry.rs`
11. `/Users/kkh/Desktop/opensource분석/rtk/src/discover/rules.rs`
12. `/Users/kkh/Desktop/opensource분석/rtk/src/hooks/README.md`
13. `/Users/kkh/Desktop/opensource분석/rtk/hooks/README.md`

대표 adapter를 빠르게 이해하려면 다음 파일이 좋다.

- `src/cmds/git/git.rs`: git subcommand routing과 필터링 대표.
- `src/cmds/rust/cargo_cmd.rs`: streaming/build/test/clippy 처리 대표.
- `src/cmds/js/lint_cmd.rs`: tool detection과 cross-routing 대표.
- `src/cmds/python/ruff_cmd.rs`: JSON 강제/파싱 대표.
- `src/cmds/system/read.rs`: 파일 읽기 축약 대표.

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

2차 확인으로 해소된 항목:

- `parser` 모듈은 실제 adapter에서 사용된다.
  - `OutputParser` 구현체는 `src/cmds/js/playwright_cmd.rs`, `src/cmds/js/vitest_cmd.rs`, `src/cmds/js/pnpm_cmd.rs`의 list/outdated parser에서 확인됐다.
  - `TestResult`는 Playwright/Vitest 출력 구조화에 쓰이고, `DependencyState`는 PNPM list/outdated 출력 구조화에 쓰인다.
  - `FormatMode`, `TokenFormatter`, `ParseResult`는 이 parser 결과를 compact/verbose/ultra 형태로 출력하는 데 사용된다.
  - `src/cmds/system/pipe_cmd.rs`도 parser 기반 wrapper 경로에서 `OutputParser`, `FormatMode`, `TokenFormatter`를 사용한다.
- `force_tee_hint()`는 성공했지만 출력이 잘린 경우의 recovery hint로 실제 사용된다.
  - `src/cmds/cloud/curl_cmd.rs`: 긴 일반 텍스트/TTY 출력 truncation 경로.
  - `src/cmds/cloud/aws_cmd.rs`: `run_aws_filtered`, `run_s3_ls`, `run_s3_transfer`의 `result.truncated` 경로.
  - 반대로 `tee_and_hint()`는 `core::runner`, `main.rs` fallback, `gt`, `lint`, `playwright`, `vitest`, `aws` 실패 경로처럼 exit code 기반 실패 회수에 더 많이 쓰인다.
- agent별 rewrite 방식은 다음처럼 구분된다.
  - 실행 전 rewrite: Claude Code, Cursor, Gemini CLI, VS Code Copilot Chat.
  - plugin API rewrite: OpenCode, OpenClaw, Hermes.
  - 권고/규칙 기반 only: Codex CLI, Cline/Roo Code, Windsurf, Kilo Code, Google Antigravity.
  - GitHub Copilot CLI는 `updatedInput`이 없어 deny-with-suggestion 방식으로 문서화되어 있으며, 완전한 투명 rewrite로 보기는 어렵다.

아직 남은 확인 필요 항목:

- 버전 메타가 서로 다르다.
  - `Cargo.toml`은 `0.34.3`.
  - `.release-please-manifest.json`과 `CHANGELOG.md` 최상단은 `0.36.0`.
  - `README.md`의 설치 확인 예시는 `0.28.2`, `README_ko.md`는 `0.27.x`.
  - 코드/문서 범위만으로는 왜 `Cargo.toml`과 release metadata가 어긋났는지 확정할 수 없다. checkout 상태, release automation, 문서 stale 여부를 별도 확인해야 한다.
- `parser/README.md`에는 `LintResult`, `BuildOutput` 같은 개념이 언급되지만, 이번 범위의 실제 Rust 타입/adapter 사용 지점은 확인되지 않았다. 문서 잔여분인지 예정된 추상화인지 추가 확인이 필요하다.
- agent별 “실제 적용률”은 코드와 문서만으로는 확정할 수 없다. hook/plugin 계층은 구조상 강제 rewrite가 가능하지만, rules/awareness 계층은 모델이 지시를 따르는 비율에 의존한다.
- 본 분석은 실행 테스트를 수행하지 않았다. 구조 이해를 목적으로 한 정적 분석이며, 실제 동작 검증은 `cargo test`, `scripts/test-all.sh`, `scripts/check-installation.sh` 등으로 별도 수행해야 한다.
