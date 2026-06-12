---
title: Tokscale
created: 2026-06-10
updated: 2026-06-11
type: project
tags: [open-source, project, architecture, developer-tools, deepwiki]
sources: [artifacts/tokscale/deepwiki/pages-md/2-architecture.md, deepwiki-ko/tokscale/2-architecture.md, artifacts/tokscale/repo-metadata.txt, repos/tokscale/Cargo.toml, repos/tokscale/crates/tokscale-core/src/lib.rs, repos/tokscale/crates/tokscale-core/src/clients.rs, repos/tokscale/crates/tokscale-core/src/scanner.rs, repos/tokscale/crates/tokscale-core/src/aggregator.rs, repos/tokscale/crates/tokscale-core/src/pricing/mod.rs, repos/tokscale/crates/tokscale-cli/src/main.rs, repos/tokscale/crates/tokscale-cli/src/tui/data/mod.rs, repos/tokscale/packages/cli/package.json, repos/tokscale/packages/frontend/package.json, repos/tokscale/packages/frontend/src/lib/db/schema.ts, repos/tokscale/packages/frontend/src/app/api/submit/route.ts]
confidence: high
---

# Tokscale

Tokscale은 AI coding assistant의 로컬 사용 기록을 수집해 토큰·비용·활동량을 계산하고, CLI/TUI와 웹 소셜 플랫폼으로 보여주는 developer tool이다. 이 페이지는 DeepWiki 아키텍처 문서를 출발점으로 삼되, 현재 로컬 checkout `repos/tokscale/`의 source path로 핵심 구조를 검증한 요약이다. DeepWiki/번역본은 [[deepwiki-first-baseline]]에 해당하는 외부 baseline이고, 아래 결론의 신뢰도는 `repos/tokscale` 소스 검증에 기반한다. 이 증거 경계는 [[evidence-backed-analysis]]와 [[workspace-boundaries]]의 운영 원칙을 따른다.

## Verification snapshot

- Repository: `https://github.com/junhoyeo/tokscale`
- Local checkout: `repos/tokscale/`
- Verified commit: `aebe4ea8b9a80d84cb2ff0e3b3472db9ac34051d`
- DeepWiki source: `artifacts/tokscale/deepwiki/pages-md/2-architecture.md`
- Korean reading copy: `deepwiki-ko/tokscale/2-architecture.md`

## Architecture at a glance

Tokscale은 크게 세 계층으로 볼 수 있다.

1. **Rust CLI/application layer** — `crates/tokscale-cli`가 `tokscale` 명령, subcommand routing, TUI, social submission/auth flow를 담당한다.
2. **Rust core processing layer** — `crates/tokscale-core`가 client별 로컬 저장소 scan, session parsing, token/cost normalization, pricing lookup, aggregation을 담당한다.
3. **Next.js social web layer** — `packages/frontend`가 `tokscale.ai`용 leaderboard/profile/embed/API/database layer를 담당한다.

루트 `Cargo.toml`은 Rust workspace member를 `crates/tokscale-core`와 `crates/tokscale-cli`로 정의하고, workspace dependency로 `tokscale-core`, `rayon`, `simd-json`, `walkdir`, `reqwest`, `tokio`, `rusqlite`, `clap`, `ratatui` 등을 선언한다 (`repos/tokscale/Cargo.toml:1-91`). 즉 DeepWiki가 설명한 “native Rust core + CLI + web frontend” 방향은 맞지만, 현재 source 기준에서 성능 핵심 crate 이름은 `tokscale-core`이고 CLI binary crate는 `tokscale-cli`다.

## Rust workspace and CLI layer

`crates/tokscale-cli/src/main.rs`는 `clap` 기반 `Cli` struct와 `Commands` enum을 통해 `models`, `monthly`, `hourly`, `pricing`, `clients`, `login/logout/whoami`, `graph`, `tui`, `submit`, `headless`, `wrapped` 같은 명령을 라우팅한다 (`repos/tokscale/crates/tokscale-cli/src/main.rs:23-252`). `--light`, `--json`, `--home`, date range, client filters, `--no-spinner` 같은 공통 플래그도 entrypoint에 직접 정의되어 있다.

TUI 데이터 계층은 `crates/tokscale-cli/src/tui/data/mod.rs`에서 core crate의 `parse_local_unified_messages`, `ClientId`, `GroupBy`, `LocalParseOptions`, `ModelPerformance`, `UnifiedMessage`를 import해 사용한다 (`repos/tokscale/crates/tokscale-cli/src/tui/data/mod.rs:1-12`). 같은 파일은 TUI에 필요한 `TokenBreakdown`, `ModelUsage`, `AgentUsage`, `DailyUsage`, `HourlyUsage`, `MinutelyUsage`, `UsageData`, `DataLoader` 구조를 별도로 정의한다 (`repos/tokscale/crates/tokscale-cli/src/tui/data/mod.rs:29-170`). 이 구조 때문에 CLI/TUI는 core parser 결과를 사용자-facing dashboard 모델로 한 번 더 가공하는 adapter 계층으로 볼 수 있다.

## Core processing layer

`crates/tokscale-core/src/lib.rs`는 `aggregator`, `clients`, `parser`, `pricing`, `scanner`, `sessionize`, `sessions` 등을 모듈로 구성하고 주요 타입과 함수를 re-export한다 (`repos/tokscale/crates/tokscale-core/src/lib.rs:1-25`). 핵심 data shape인 `TokenBreakdown`은 input/output/cache read/cache write/reasoning token bucket을 포함하며 total 계산을 제공한다 (`repos/tokscale/crates/tokscale-core/src/lib.rs:174-187`).

Local parse path는 `parse_local_unified_messages()`에서 `LocalParseOptions`를 해석하고 pricing service를 로드한 뒤 `parse_local_unified_messages_resolved()`로 넘긴다 (`repos/tokscale/crates/tokscale-core/src/lib.rs:2610-2624`). resolved path는 `parse_all_messages_with_pricing_with_env_strategy()` 결과를 filter해서 `Vec<UnifiedMessage>`로 반환한다 (`repos/tokscale/crates/tokscale-core/src/lib.rs:2066-2079`). 구형/호환 API인 `parse_local_clients()`는 scanner 결과를 기반으로 OpenCode, Claude, Codex 등 client별 parser를 병렬 적용하고 dedup을 수행한다 (`repos/tokscale/crates/tokscale-core/src/lib.rs:2081-2215`).

## Client discovery and parsing model

Tokscale은 client registry를 `crates/tokscale-core/src/clients.rs`의 `define_clients!` macro로 정의한다. 각 client는 id, root strategy, relative path, filename pattern, headless 지원 여부, local parse 여부, default submission 여부를 갖는다 (`repos/tokscale/crates/tokscale-core/src/clients.rs:171-430`). 검증한 구간에는 OpenCode, Claude, Codex, Cursor, Gemini, Amp, Droid, OpenClaw, Pi, Kimi, Qwen, RooCode, KiloCode, Mux, Kilo, Crush, Hermes, Copilot, Goose, Codebuff, Antigravity, Zed, Kiro, Trae, Warp, Cline, Gajae-Code 계열 정의가 포함된다.

Scanner는 `walkdir`와 `rayon`을 사용하는 병렬 file scanner로 선언되어 있고 (`repos/tokscale/crates/tokscale-core/src/scanner.rs:1-8`), user-configured scanner settings를 `~/.config/tokscale/settings.json`의 `scanner` key 및 extra scan paths로 모델링한다 (`repos/tokscale/crates/tokscale-core/src/scanner.rs:30-63`). `ScanResult`는 client별 file buckets와 OpenCode/SQLite, Hermes, Goose, Zed, Kiro 등 특수 DB path들을 별도 필드로 보관한다 (`repos/tokscale/crates/tokscale-core/src/scanner.rs:72-93`).

## Aggregation and pricing

Aggregation은 `crates/tokscale-core/src/aggregator.rs`의 parallel map-reduce 패턴이 핵심이다. `aggregate_by_date()`는 `UnifiedMessage`를 날짜별 accumulator로 fold/reduce한 뒤 정렬된 `DailyContribution`으로 변환하고 intensity를 계산한다 (`repos/tokscale/crates/tokscale-core/src/aggregator.rs:13-58`). `aggregate_by_session()`은 session id별 token/cost/client/model breakdown을 합산하고 최근 활동 순으로 정렬한다 (`repos/tokscale/crates/tokscale-core/src/aggregator.rs:60-100`). `calculate_summary()`는 total tokens/cost, active days, client/model set 등을 계산한다 (`repos/tokscale/crates/tokscale-core/src/aggregator.rs:103-148`).

Pricing layer는 custom pricing, LiteLLM, OpenRouter, models.dev data를 조합한다. `PricingService::fetch_inner()`는 LiteLLM, OpenRouter, models.dev fetch를 `tokio::join!`으로 병렬 수행하고 custom pricing과 함께 service를 만든다 (`repos/tokscale/crates/tokscale-core/src/pricing/mod.rs:130-152`). Cost calculation은 custom override를 먼저 확인한 다음 lookup backend로 fallback한다 (`repos/tokscale/crates/tokscale-core/src/pricing/mod.rs:229-267`).

## Web frontend and social API layer

`packages/frontend/package.json` 기준 frontend는 Next.js 16, React 19, Drizzle ORM, Neon serverless/Postgres, Vitest를 사용하는 private package다 (`repos/tokscale/packages/frontend/package.json:1-49`). Database schema는 Drizzle `pgTable` 정의로 users, sessions, api tokens, device codes, submissions, submitted devices, daily breakdown, groups 등을 모델링한다 (`repos/tokscale/packages/frontend/src/lib/db/schema.ts:23-180`, `repos/tokscale/packages/frontend/src/lib/db/schema.ts:181-360`). `submissions`는 total tokens/cost, token buckets, date range, source/model lists, schema version, active time/session metrics, MCP servers를 갖고 leaderboard composite index를 둔다 (`repos/tokscale/packages/frontend/src/lib/db/schema.ts:162-217`). `daily_breakdown`은 submission/device/date 단위 token/cost/source breakdown과 active time을 보관한다 (`repos/tokscale/packages/frontend/src/lib/db/schema.ts:265-328`).

`packages/frontend/src/app/api/submit/route.ts`는 CLI에서 올라오는 usage submission을 처리하는 `POST /api/submit` endpoint다. 이 route는 bearer token 추출, personal token authentication, JSON parse/validation, legacy `sources` to `clients` normalization, device-aware schema versioning, client-level merge를 수행한다 (`repos/tokscale/packages/frontend/src/app/api/submit/route.ts:1-180`). 따라서 CLI와 web backend의 통신 경계는 “CLI가 local usage를 aggregation/JSON submission으로 만들고, frontend API가 인증·검증·DB merge를 수행한다”로 정리할 수 있다.

## Distribution model

npm package `@tokscale/cli`는 `tokscale` binary entry를 제공하고, platform-specific native binary packages를 optional dependencies로 선언한다 (`repos/tokscale/packages/cli/package.json:1-40`). 예를 들어 `@tokscale/cli-darwin-arm64` package는 `os: [darwin]`, `cpu: [arm64]`, `main: bin/tokscale`를 갖는다 (`repos/tokscale/packages/cli-darwin-arm64/package.json:1-26`). 즉 배포 단위는 JS wrapper/package ecosystem 위에 native Rust binary를 얹는 구조다.

## Related deep dives

데이터가 실제로 수집·정규화·가격 계산·집계·제출 merge로 이어지는 단계별 흐름은 [[tokscale-data-flow-pipeline]]에 별도로 정리했다. 이 페이지는 구조 요약이고, pipeline page는 DeepWiki `2.2 Data Flow Pipeline`을 기준으로 `scanner`, `sessions`, `pricing`, `aggregator`, TUI `DataLoader`, frontend `POST /api/submit` 구현을 source-verified로 따라간다.

Rust core의 계층 구조와 현재 source 기준 NAPI/binary packaging drift는 [[tokscale-rust-core-processing-layer]]에 정리했다. 특히 현재 checkout에서는 DeepWiki의 “NAPI native addon” 설명보다 “npm wrapper가 platform-specific standalone Rust CLI binary를 실행하고, 그 binary가 `tokscale-core` library를 사용한다”는 구조가 source-verified 사실이다.

여러 agent/client별 session log가 어떻게 발견·파싱·캐시되는지, Claude sidechain/subagent, Codex incremental JSONL, OpenCode/Kilo SQLite, Cursor CSV, Gemini JSON/JSONL을 어떻게 `UnifiedMessage`로 정규화하는지는 [[tokscale-session-parsing-and-source-cache]]에 정리했다. Parser가 만든 token bucket을 실제 비용으로 바꾸는 pricing source, lookup algorithm, tiered cost calculation, persistent/stale/in-memory cache 구조는 [[tokscale-pricing-cost-and-cache]]에 정리했다. 가격 적용이 끝난 `UnifiedMessage`가 model/month/hour reports, graph JSON, TUI dashboard, wrapped PNG summary로 어떻게 재집계되는지는 [[tokscale-report-generation-and-aggregation]]에 정리했다. 터미널에서 `tokscale`을 설치·실행하고 `--json`, `--light`, `--client`, `--group-by`, `graph`, `wrapped`, `headless`, integration subcommands를 사용하는 source-verified command reference는 [[tokscale-cli-terminal-commands]]에 정리했다.

## Durable interpretation

Tokscale의 핵심 설계는 “많은 AI coding tool의 heterogeneous local state를 client registry + scanner + parser로 `UnifiedMessage` 계층에 정규화하고, token/cost aggregation을 Rust core에서 수행한 다음, CLI/TUI와 web API가 각각 로컬 탐색/소셜 공유 interface를 제공하는 구조”다. 이 구조는 단순 web app보다 local-first data ingestion과 native binary distribution의 비중이 크며, frontend는 primary parser가 아니라 submission/leaderboard/profile/embed를 담당하는 social surface로 보는 것이 정확하다.
