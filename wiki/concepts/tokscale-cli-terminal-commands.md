---
title: Tokscale CLI Terminal Commands
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [open-source, developer-tools, cli, terminal, commands, evidence, deepwiki]
sources: [artifacts/tokscale/deepwiki/pages-md/3.2-commands-reference.md, repos/tokscale/README.md, repos/tokscale/package.json, repos/tokscale/packages/tokscale/package.json, repos/tokscale/packages/tokscale/bin.js, repos/tokscale/packages/cli/package.json, repos/tokscale/packages/cli/bin.js, repos/tokscale/packages/cli/src/index.ts, repos/tokscale/scripts/cli.sh, repos/tokscale/crates/tokscale-cli/Cargo.toml, repos/tokscale/crates/tokscale-cli/src/main.rs, repos/tokscale/crates/tokscale-core/src/clients.rs, repos/tokscale/crates/tokscale-core/src/lib.rs]
confidence: high
---

# Tokscale CLI Terminal Commands

이 페이지는 DeepWiki `3.2 Commands Reference`를 baseline으로 삼고, 현재 checkout `repos/tokscale/`의 `clap` command definition과 실제 `--help` 출력으로 검증한 terminal 사용 명령어 모음이다. Tokscale의 데이터 처리 흐름은 [[tokscale-data-flow-pipeline]], report 집계 semantics는 [[tokscale-report-generation-and-aggregation]], pricing lookup/cache는 [[tokscale-pricing-cost-and-cache]]에 별도로 정리되어 있다. DeepWiki는 [[deepwiki-first-baseline]]에 해당하는 외부 second opinion이며, 아래 명령은 [[evidence-backed-analysis]] 원칙에 따라 source/help output을 확인했다.

## Verification snapshot

- Repository: `https://github.com/junhoyeo/tokscale`
- Local checkout: `repos/tokscale/`
- Verified commit: `aebe4ea8b9a80d84cb2ff0e3b3472db9ac34051d`
- DeepWiki baseline: `artifacts/tokscale/deepwiki/pages-md/3.2-commands-reference.md`
- CLI verification: `/Users/kkh/.cargo/bin/cargo run -q -p tokscale-cli -- --help`, plus focused `models`, `pricing`, `graph`, `wrapped`, `headless`, `cursor`, `codex`, `usage`, `time-metrics`, `clients`, `submit` help output.
- Tool-shell note: 이 Hermes tool shell의 `PATH`에는 `cargo`가 없었지만 `/Users/kkh/.cargo/bin/cargo`는 동작했다. 일반 사용자 터미널에서는 PATH 설정에 따라 `cargo`가 바로 동작할 수 있다.

## Install / run entrypoints

현재 repository는 Rust CLI binary와 npm wrapper를 함께 배포한다.

```bash
# 설치 없이 실행: README의 quick start
npx tokscale@latest
bunx tokscale@latest
deno x npm:tokscale@latest

# non-interactive table output
npx tokscale@latest --light
```

Source-verified packaging boundary:

- `packages/tokscale`는 npm alias package이며 `dependencies`로 `@tokscale/cli`를 가리키고, `bin.js`는 `await import("@tokscale/cli")`만 수행한다 (`repos/tokscale/packages/tokscale/package.json:1-40`, `repos/tokscale/packages/tokscale/bin.js:1-2`).
- `@tokscale/cli`는 `tokscale` binary entry를 `./bin.js`로 선언하고, platform-specific native binary packages를 optional dependencies로 둔다 (`repos/tokscale/packages/cli/package.json:1-40`).
- wrapper implementation은 현재 platform/arch/libc에 맞는 native `tokscale` binary를 찾은 뒤 `spawnSync(binary, process.argv.slice(2))`로 실행한다. binary가 없으면 `cargo build --release -p tokscale-cli`를 안내한다 (`repos/tokscale/packages/cli/src/index.ts:166-228`).
- local development path는 `bun run cli` → `scripts/cli.sh` → `bun packages/cli/src/index.ts "$@"`이고, source build script는 `cargo build --release -p tokscale-cli`를 실행한다 (`repos/tokscale/package.json:10-17`, `repos/tokscale/scripts/cli.sh:1-7`).

```bash
# source checkout에서 local development 실행
cd repos/tokscale
bun install
bun run cli -- --help

# native binary build가 필요한 경우
bun run build:core
# 또는 wrapper가 안내하는 Rust build
cargo build --release -p tokscale-cli
```

## Current command surface

현재 `tokscale --help` 기준 top-level command는 DeepWiki 표보다 넓다. DeepWiki가 다룬 `models/monthly/hourly/pricing/clients/login/logout/whoami/graph/tui/submit/headless/wrapped` 외에 `qr`, `usage`, `codex`, `antigravity`, `trae`, `warp`, `delete-submitted-data`, `time-metrics`가 현재 help output에 나타난다 (`repos/tokscale/crates/tokscale-cli/src/main.rs:93-316`).

```bash
# 전체 command와 global option 확인
tokscale --help

# 각 command의 세부 option 확인
tokscale models --help
tokscale pricing --help
tokscale graph --help
tokscale wrapped --help
tokscale headless --help
tokscale cursor --help
tokscale codex --help
tokscale usage --help
tokscale time-metrics --help
```

검증된 top-level commands:

| Command | Terminal use |
|---|---|
| `tokscale` | TTY에서는 TUI를 실행하고, `--json` 또는 non-TTY/`--light`에서는 model report path를 실행한다. |
| `tokscale models` | model usage report. `--json`, `--light`, `--group-by`, client/date filters 지원. |
| `tokscale monthly` | monthly/daily breakdown report. `--json`, `--light`, client/date filters 지원. |
| `tokscale hourly` | hourly report. `--json`, `--light`, client/date filters 지원. |
| `tokscale pricing <model-id>` | model pricing lookup. `--provider`, `--json`, `list-overrides` 지원. |
| `tokscale clients` | local scan locations/session counts. `--json` 지원. |
| `tokscale graph` | contribution graph JSON export. `--output`, client/date filters 지원. |
| `tokscale wrapped` | year-in-review PNG generation. `--year`, `--output`, `--agents`, `--clients`, `--short` 지원. |
| `tokscale submit` | social platform upload. `--dry-run`, client/date filters 지원. |
| `tokscale headless codex ...` | subprocess stdout capture; 현재 source는 `codex` source만 허용한다. |
| `tokscale usage` | subscription usage/quota command. `--json`, `--light` 지원. |
| `tokscale time-metrics` | active/wall-clock/continuous/concurrent session metrics. `--json`, client/date filters 지원. |
| `tokscale login/logout/whoami/qr` | Tokscale social auth/token 관련 command. |
| `tokscale cursor ...` | Cursor API cache account/sync commands. |
| `tokscale codex ...` | Codex account import/list/switch/remove/status commands. |
| `tokscale antigravity ...`, `tokscale trae ...`, `tokscale warp ...` | provider/client integration commands. |
| `tokscale delete-submitted-data` | server에 제출된 usage data 삭제 command. |

## Report commands for terminal use

Terminal 자동화나 wiki/research 환경에서는 TUI보다 `--light`, `--json`, `--no-spinner` 조합이 재현성이 높다.

```bash
# 기본 TUI
npx tokscale@latest

# table output: terminal에서 빠르게 확인
tokscale --light --no-spinner
tokscale models --light --no-spinner

# JSON output: script/automation에 적합
tokscale --json --no-spinner
tokscale models --json --no-spinner > tokscale-models.json
tokscale monthly --json --no-spinner > tokscale-monthly.json
tokscale hourly --json --no-spinner > tokscale-hourly.json

# 특정 client와 기간만 집계
tokscale models --json --client claude,codex --week --no-spinner
tokscale monthly --light --client opencode --month --no-spinner
tokscale hourly --json --since 2026-06-01 --until 2026-06-11 --no-spinner

# custom HOME 아래의 AI tool session data를 읽기
tokscale models --json --home /path/to/test-home --no-spinner
```

Date filters are inclusive where applicable. Current `DateRangeFlags`에는 `--today`, `--yesterday`, `--week`, `--month`, `--since <YYYY-MM-DD>`, `--until <YYYY-MM-DD>`, `--year <YYYY>`가 있다 (`repos/tokscale/crates/tokscale-cli/src/main.rs:1067-1099`). `--today`, `--yesterday`, `--week`, `--month`는 서로 일부 conflict가 걸려 있고, `--year`는 `normalize_year_filter()`를 통해 shortcut date filter와 함께 쓰이면 무시된다 (`repos/tokscale/crates/tokscale-cli/src/main.rs:1532-1578`).

## Client filters

현재 권장 client filter는 DeepWiki의 legacy boolean flag 목록보다 `-c/--client`다. `ClientFlags`는 repeatable/comma-separated value enum으로 정의되어 있고, 기존 `--claude`, `--codex` 같은 boolean flag는 source상 hidden deprecated compatibility path로 남아 있다 (`repos/tokscale/crates/tokscale-cli/src/main.rs:989-1065`).

```bash
# comma-separated
tokscale models --client claude,codex --json --no-spinner

# repeatable
tokscale models -c claude -c codex --json --no-spinner

# client scan inventory 확인
tokscale clients
tokscale clients --json
```

현재 help output의 possible values는 다음과 같다.

```text
opencode, claude, codex, cursor, gemini, amp, droid, openclaw, pi, kimi, qwen,
roocode, kilocode, mux, kilo, crush, hermes, copilot, goose, codebuff,
antigravity, zed, kiro, trae, warp, cline, gjc, grok, synthetic
```

Core client registry의 실제 local source path/pattern authority는 `repos/tokscale/crates/tokscale-core/src/clients.rs`다. 예를 들어 OpenCode는 `XDG_DATA_HOME/opencode/storage/message/*.json`, Claude는 `~/.claude/projects/*.jsonl`, Codex는 `CODEX_HOME` fallback `~/.codex/sessions/*.jsonl`, Cursor는 `~/.config/tokscale/cursor-cache/usage*.csv`, Gemini는 `GEMINI_CLI_HOME` fallback `~/.gemini/tmp/*.json|*.jsonl`이다 (`repos/tokscale/crates/tokscale-core/src/clients.rs:171-222`).

## Group-by strategies

`models`와 default report path는 `--group-by`를 지원한다. 현재 source의 `GroupBy::from_str()`는 comma form과 hyphen alias를 모두 받아들인다 (`repos/tokscale/crates/tokscale-core/src/lib.rs:152-171`).

```bash
# CLI default: client,model
tokscale models --light --group-by client,model --no-spinner

# 가장 크게 합치기
tokscale models --json --group-by model --no-spinner

# provider까지 분리
tokscale models --json --group-by client,provider,model --no-spinner

# workspace/session 기준 attribution
tokscale models --json --group-by workspace,model --no-spinner
tokscale models --json --group-by session,model --no-spinner
tokscale models --json --group-by client,session,model --no-spinner
```

유효값은 `model`, `client,model`, `client,provider,model`, `workspace,model`, `session,model`, `client,session,model`이다. `session`, `session-model`, `client-session`, `client-session-model` 같은 alias도 source에서 허용된다 (`repos/tokscale/crates/tokscale-core/src/lib.rs:158-165`).

## Operational command families

Graph export, Wrapped PNG generation, pricing lookup, social auth/submit, provider integration commands, and `headless` capture are split into [[tokscale-operational-cli-commands]] so this page stays focused on install/run entrypoints, report automation, client/date filters, and `--group-by` semantics.

For terminal automation, prefer `--json`, `--light`, `--no-spinner`, `--client/-c`, `--home`, and explicit date filters over TUI defaults. In Hermes tool-shell style environments, verify actual binary paths when `cargo` is not on `PATH`.

관련 페이지: [[tokscale]], [[tokscale-data-flow-pipeline]], [[tokscale-report-generation-and-aggregation]], [[tokscale-pricing-cost-and-cache]], [[tokscale-operational-cli-commands]], [[evidence-backed-analysis]].
