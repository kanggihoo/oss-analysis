---
title: Tokscale Operational CLI Commands
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [open-source, developer-tools, cli, terminal, commands, evidence, deepwiki]
sources: [artifacts/tokscale/deepwiki/pages-md/3.2-commands-reference.md, repos/tokscale/README.md, repos/tokscale/package.json, repos/tokscale/packages/tokscale/package.json, repos/tokscale/packages/tokscale/bin.js, repos/tokscale/packages/cli/package.json, repos/tokscale/packages/cli/bin.js, repos/tokscale/packages/cli/src/index.ts, repos/tokscale/scripts/cli.sh, repos/tokscale/crates/tokscale-cli/Cargo.toml, repos/tokscale/crates/tokscale-cli/src/main.rs, repos/tokscale/crates/tokscale-core/src/clients.rs, repos/tokscale/crates/tokscale-core/src/lib.rs]
confidence: high
---

# Tokscale Operational CLI Commands

이 페이지는 [[tokscale-cli-terminal-commands]]에서 분리한 operational command reference다. Report/filter 중심 명령은 원래 페이지에 남기고, 여기에는 graph export, Wrapped PNG, pricing lookup, social auth/submit, provider integration, `headless` capture를 모았다. Tokscale의 집계 의미는 [[tokscale-report-generation-and-aggregation]], pricing/cache 경계는 [[tokscale-pricing-cost-and-cache]], local-first data flow는 [[tokscale-data-flow-pipeline]]을 참조한다.

검증 기준 checkout: `repos/tokscale` at `aebe4ea8b9a80d84cb2ff0e3b3472db9ac34051d`.

## Graph, wrapped, and time metrics

```bash
# contribution graph JSON을 stdout으로 출력
tokscale graph --year 2026 --no-spinner

# 파일로 저장
tokscale graph --year 2026 --output tokscale-graph-2026.json --no-spinner

# Wrapped PNG 생성
tokscale wrapped --year 2026 --output tokscale-2026-wrapped.png --no-spinner

# top OpenCode agents 대신 top clients 표시
tokscale wrapped --year 2026 --clients --short --no-spinner

# session active-time metrics
tokscale time-metrics --week --no-spinner
tokscale time-metrics --json --client claude,codex --month --no-spinner
```

`graph`는 `--output`, client/date filters, `--benchmark`, `--no-spinner`를 지원한다. `wrapped`는 `--output`, `--year`, client filters, `--short`, `--agents`, `--clients`, `--disable-pinned`, `--no-spinner`를 지원한다. `time-metrics`는 `--json`, client/date filters, `--no-spinner`를 지원한다. 세 surface의 aggregation 차이는 [[tokscale-report-generation-and-aggregation]]에 정리되어 있다.

## Pricing lookup and custom overrides

```bash
# model pricing lookup
tokscale pricing "claude-3-5-sonnet-20241022" --no-spinner
tokscale pricing "gpt-4o" --json --no-spinner

# 특정 pricing source 강제
tokscale pricing "grok-code" --provider openrouter --no-spinner
tokscale pricing "claude-3-5-sonnet" --provider litellm --no-spinner
tokscale pricing "some-local-model" --provider custom --json --no-spinner

# custom-pricing.json override 목록 확인
tokscale pricing list-overrides
tokscale pricing list-overrides --json
```

현재 `run_pricing_lookup()`는 provider를 `custom`, `litellm`, `openrouter`, `models.dev`로 제한한다. `model_id`가 `list-overrides`이면 별도 override listing path로 빠진다 (`repos/tokscale/crates/tokscale-cli/src/main.rs:3142-3171`). Custom pricing file과 lookup/cache semantics는 [[tokscale-pricing-cost-and-cache]]에 정리되어 있다.

## Auth, submit, and integration commands

```bash
# Tokscale social auth
tokscale login
tokscale login --token "$TOKSCALE_API_TOKEN"
tokscale whoami
tokscale qr --yes
tokscale logout

# 제출 전 dry-run
tokscale submit --dry-run --week
tokscale submit --dry-run --client claude,codex --since 2026-06-01 --until 2026-06-11

# 실제 제출
tokscale submit --week

# Cursor API cache integration
tokscale cursor login --name work
tokscale cursor accounts --json
tokscale cursor sync --json
tokscale cursor status --name work
tokscale cursor switch work
tokscale cursor logout --name work --purge-cache

# Codex account integration
tokscale codex import --name work
tokscale codex accounts --json
tokscale codex status --name work --json
tokscale codex switch work
tokscale codex remove work

# Other integration commands
tokscale antigravity sync
tokscale antigravity status --json
tokscale antigravity purge-cache

tokscale trae login --variant solo
tokscale trae login --manual --variant ide
tokscale trae status --json
tokscale trae sync --since 30 --include-aux
tokscale trae logout --variant solo

tokscale warp login --token "$WARP_TOKEN"
tokscale warp login --token "$WARP_COOKIE" --cookie
tokscale warp status --json
tokscale warp sync --json
tokscale warp logout --purge-cache

# Server-side submitted data deletion command
tokscale delete-submitted-data
```

Routing verification: `main.rs` delegates `cursor` to `run_cursor_command()`, `codex` to `run_codex_command()`, `antigravity` to `run_antigravity_command()`, `trae` to `run_trae_command()`, and `warp` to `run_warp_command()` (`repos/tokscale/crates/tokscale-cli/src/main.rs:697-719`, `repos/tokscale/crates/tokscale-cli/src/main.rs:5349-5533`). `submit` intentionally bypasses general `settings.json defaultClients` fallback so upload defaults can differ from view filters (`repos/tokscale/crates/tokscale-cli/src/main.rs:656-663`).

## Headless capture

`headless`는 command stdout을 Tokscale이 읽을 수 있는 파일로 저장하는 capture wrapper다. 현재 source는 `source`가 `codex`가 아니면 error로 종료한다 (`repos/tokscale/crates/tokscale-cli/src/main.rs:5640-5655`).

```bash
# Codex stdout을 jsonl로 capture; --json은 자동 추가됨
tokscale headless codex exec "summarize this repository"

# output file 직접 지정
tokscale headless --output /tmp/codex-run.jsonl codex exec "summarize this repository"

# json/jsonl format override
tokscale headless --format jsonl codex exec "summarize this repository"

# Codex args를 그대로 넘기고 자동 --json 추가를 끄기
tokscale headless --no-auto-flags codex exec --json "summarize this repository"
```

Default output path는 configured headless root가 있으면 그 아래, 없으면 `~/.config/tokscale/headless/<source>/` 아래에 timestamp+uuid filename으로 만들어진다 (`repos/tokscale/crates/tokscale-cli/src/main.rs:5671-5703`). Timeout은 TUI settings의 native timeout을 사용하며, timeout 발생 시 exit code 124로 종료한다 (`repos/tokscale/crates/tokscale-cli/src/main.rs:5705-5728`).

## Durable interpretation

Tokscale terminal interface는 세 가지 사용 모드를 동시에 제공한다: interactive local dashboard, scriptable local analytics, account/social/integration operations. 현재 source 기준으로 operational command를 문서화할 때도 [[deepwiki-first-baseline]]은 baseline일 뿐이며, 실제 command routing과 flags는 `repos/tokscale/crates/tokscale-cli/src/main.rs`와 `--help` 출력으로 검증해야 한다.

관련 페이지: [[tokscale]], [[tokscale-cli-terminal-commands]], [[tokscale-report-generation-and-aggregation]], [[tokscale-pricing-cost-and-cache]], [[tokscale-data-flow-pipeline]], [[evidence-backed-analysis]].
