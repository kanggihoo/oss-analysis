# Wiki Log

> Chronological record of wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: create, update, ingest, query, lint, archive, delete

## [2026-06-09] create | oss-analysis wiki initialized
- Created initial wiki structure under `/Users/kkh/Desktop/oss-analysis/wiki`.
- Domain: open-source codebase analysis and cross-project architecture knowledge.

## [2026-06-09] update | Rebuilt wiki structure for current workspace layout
- Confirmed current workspace roles: `repos/` for source checkouts, `artifacts/` for analyzer/external-baseline outputs, `reports/` for human-facing reports, `wiki/` for durable LLM-managed synthesis.
- Rebuilt `SCHEMA.md`, `index.md`, and `README.md` around the current layout.
- Created seed pages: [[oss-analysis-workspace]], [[workspace-boundaries]], [[llm-wiki-operating-model]], [[evidence-backed-analysis]], [[deepwiki-first-baseline]], [[how-to-update-this-wiki]].

## [2026-06-09] update | Workflow and wiki maintenance initialized
- Updated root `OSS_ANALYSIS_WORKFLOW.md` to match the canonical workspace layout and wiki ownership model.
- Added `scripts/wiki-lint.py` as the wiki health-check command referenced by the workflow.
- Verified wiki health with `python3 scripts/wiki-lint.py`: 0 issues, 0 warnings, 6 indexed pages.

## [2026-06-10] update | graphify overview and architecture notes
- Added [[graphify]] as a project overview based on `artifacts/graphify/deepwiki/pages-md/2-core-architecture.md` and verified source paths under `repos/graphify/`.
- Added [[graphify-knowledge-graph-pipeline]] as a reusable concept page for the detect/extract/build/dedup/cluster/analyze/report/export pipeline.
- Updated `index.md` to list 8 indexed pages.

## [2026-06-10] update | graphify LLM backend semantics
- Added [[graphify-llm-semantic-extraction]] based on `artifacts/graphify/deepwiki/pages-md/2.2-extraction-engine.md` and verified source paths under `repos/graphify/graphify/llm.py` and `repos/graphify/graphify/__main__.py`.
- Updated [[graphify]] and [[graphify-knowledge-graph-pipeline]] with links to the LLM backend page.
- Updated `index.md` to list 9 indexed pages.

## [2026-06-10] update | graphify graph analysis process
- Added [[graphify-graph-analysis]] based on `artifacts/graphify/deepwiki/pages-md/2.4-graph-analysis.md` and verified implementation paths under `repos/graphify/graphify/analyze.py`, `repos/graphify/graphify/affected.py`, and related tests.
- Updated [[graphify]] and [[graphify-knowledge-graph-pipeline]] with links to the graph analysis page.
- Updated `index.md` to list 10 indexed pages.

## [2026-06-10] update | graphify report generation process
- Added [[graphify-report-generation]] based on `artifacts/graphify/deepwiki/pages-md/2.5-report-generation.md` and verified implementation paths under `repos/graphify/graphify/report.py`, `repos/graphify/graphify/__main__.py`, and `repos/graphify/tests/test_report.py`.
- Updated [[graphify]], [[graphify-knowledge-graph-pipeline]], and [[graphify-graph-analysis]] with links to the report generation page.
- Updated `index.md` to list 11 indexed pages.

## [2026-06-10] update | graphify export and visualization
- Added [[graphify-export-and-visualization]] based on `deepwiki-ko/graphify/3-export-and-visualization.md` and verified implementation paths under `repos/graphify/graphify/export.py`, `repos/graphify/graphify/tree_html.py`, `repos/graphify/graphify/callflow_html.py`, `repos/graphify/graphify/wiki.py`, and `repos/graphify/graphify/__main__.py`.
- Updated [[graphify]], [[graphify-knowledge-graph-pipeline]], [[graphify-report-generation]], and [[graphify-graph-analysis]] with links to the export/visualization page.
- Updated `index.md` to list 12 indexed pages.

## [2026-06-10] update | graphify CLI reference
- Added [[graphify-cli-reference]] based on `artifacts/graphify/deepwiki/pages-md/4.1-cli-reference.md` and verified implementation paths under `repos/graphify/graphify/__main__.py`, `repos/graphify/graphify/skill.md`, `repos/graphify/graphify/querylog.py`, and `repos/graphify/graphify/benchmark.py`.
- Verified the current CLI shape with `python3 -m graphify --help` from `repos/graphify`.
- Updated [[graphify]], [[graphify-knowledge-graph-pipeline]], [[graphify-report-generation]], [[graphify-graph-analysis]], and [[graphify-export-and-visualization]] with links to the CLI page.
- Updated `index.md` to list 13 indexed pages.

## [2026-06-10] update | graphify extract/query mechanics
- Added [[graphify-extract-query-mechanics]] based on source-verified behavior in `repos/graphify/graphify/__main__.py`, `repos/graphify/graphify/serve.py`, `repos/graphify/graphify/llm.py`, and `repos/graphify/graphify/extract.py`.
- Recorded the distinction between code-only AST extraction, semantic LLM extraction for docs/papers/images, `cluster-only` placeholder labels without backend, and query's lexical scoring plus BFS/DFS traversal.
- Updated [[graphify]], [[graphify-cli-reference]], [[graphify-knowledge-graph-pipeline]], and [[graphify-llm-semantic-extraction]] with links to the new page.
- Updated `index.md` to list 14 indexed pages.

## [2026-06-10] update | graphify agent skill integration
- Added [[graphify-agent-skill-integration]] based on `deepwiki-ko/graphify/4.4-claude-code-skill-integration.md` and verified Codex-specific implementation paths under `repos/graphify/graphify/__main__.py`, `repos/graphify/graphify/skill-codex.md`, `repos/graphify/graphify/skills/codex/references/`, and `repos/graphify/graphify/always_on/agents-md.md`.
- Recorded the distinction between graphify Python LLM backends and host-agent LLM work for docs/images semantic extraction and community naming.
- Clarified that current Codex `.codex/hooks.json` registers `graphify hook-check`, but `hook-check` is a no-op and guidance comes from `AGENTS.md` plus the skill.
- Updated [[graphify]], [[graphify-cli-reference]], [[graphify-extract-query-mechanics]], and [[graphify-llm-semantic-extraction]] with links to the new page.
- Updated `index.md` to list 15 indexed pages.

## [2026-06-10] update | claude-code-history-viewer DeepWiki baseline and overview
- Extracted DeepWiki baseline for `jhlee0409/claude-code-history-viewer` into `artifacts/claude-code-history-viewer/deepwiki/` with 51/51 pages matched and 0 missing pages.
- Cloned local source into `repos/claude-code-history-viewer/` at commit `9d86b46e0312b1533d24875cf35b33ebacf9723b`.
- Added source-verified reports: `reports/claude-code-history-viewer/overview.md` and `reports/claude-code-history-viewer/deepwiki-comparison.md`.
- Added [[claude-code-history-viewer]] project page and updated `index.md` to list 16 indexed pages.

## [2026-06-10] update | codeburn domain terminology
- Updated local checkout `repos/codeburn/` to commit `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3` for source verification.
- Added [[codeburn-domain-terminology]] based on DeepWiki `artifacts/codeburn/deepwiki/pages-md/1.2-key-concepts-and-terminology.md` and verified implementation paths under `repos/codeburn/src/types.ts`, `repos/codeburn/src/providers/types.ts`, `repos/codeburn/src/providers/index.ts`, `repos/codeburn/src/parser.ts`, `repos/codeburn/src/classifier.ts`, `repos/codeburn/src/optimize.ts`, `repos/codeburn/src/config.ts`, and `repos/codeburn/src/plan-usage.ts`.
- Updated `index.md` to list 17 indexed pages.

## [2026-06-10] update | tokscale architecture structure
- Added [[tokscale]] project page based on `artifacts/tokscale/deepwiki/pages-md/2-architecture.md` and Korean translation `deepwiki-ko/tokscale/2-architecture.md`.
- Source-verified architecture claims against `repos/tokscale/Cargo.toml`, `repos/tokscale/crates/tokscale-core/src/lib.rs`, `repos/tokscale/crates/tokscale-core/src/clients.rs`, `repos/tokscale/crates/tokscale-core/src/scanner.rs`, `repos/tokscale/crates/tokscale-core/src/aggregator.rs`, `repos/tokscale/crates/tokscale-core/src/pricing/mod.rs`, `repos/tokscale/crates/tokscale-cli/src/main.rs`, `repos/tokscale/crates/tokscale-cli/src/tui/data/mod.rs`, `repos/tokscale/packages/cli/package.json`, `repos/tokscale/packages/frontend/package.json`, `repos/tokscale/packages/frontend/src/lib/db/schema.ts`, and `repos/tokscale/packages/frontend/src/app/api/submit/route.ts` at commit `aebe4ea8b9a80d84cb2ff0e3b3472db9ac34051d`.
- Updated `index.md` to list 18 indexed pages.

## [2026-06-10] update | codeburn architecture structure
- Added [[codeburn]] project page based on `artifacts/codeburn/deepwiki/pages-md/2-core-architecture.md` and Korean translation `deepwiki-ko/codeburn/2-core-architecture.md`.
- Source-verified architecture claims against `repos/codeburn/package.json`, `repos/codeburn/src/cli.ts`, `repos/codeburn/src/main.ts`, `repos/codeburn/src/providers/types.ts`, `repos/codeburn/src/providers/index.ts`, `repos/codeburn/src/parser.ts`, `repos/codeburn/src/classifier.ts`, `repos/codeburn/src/models.ts`, `repos/codeburn/src/day-aggregator.ts`, `repos/codeburn/src/daily-cache.ts`, `repos/codeburn/src/usage-aggregator.ts`, `repos/codeburn/src/menubar-json.ts`, `repos/codeburn/src/dashboard.tsx`, `repos/codeburn/src/format.ts`, and `repos/codeburn/src/mcp/server.ts` at commit `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.
- Recorded DeepWiki drift notes: `src/cli.ts` is currently a launcher, `hydrateCache()` lives in `src/usage-aggregator.ts`, and `DailyCache` defaults to `~/.cache/codeburn/daily-cache.json`.
- Updated `index.md` to list 19 indexed pages.

## [2026-06-10] update | tokscale data flow pipeline
- Added [[tokscale-data-flow-pipeline]] based on `artifacts/tokscale/deepwiki/pages-md/2.2-data-flow-pipeline.md`.
- Source-verified the local-first ETL path against `repos/tokscale/crates/tokscale-core/src/clients.rs`, `repos/tokscale/crates/tokscale-core/src/scanner.rs`, `repos/tokscale/crates/tokscale-core/src/sessions/mod.rs`, `repos/tokscale/crates/tokscale-core/src/sessions/codex.rs`, `repos/tokscale/crates/tokscale-core/src/message_cache.rs`, `repos/tokscale/crates/tokscale-core/src/pricing/lookup.rs`, `repos/tokscale/crates/tokscale-core/src/aggregator.rs`, `repos/tokscale/crates/tokscale-core/src/lib.rs`, `repos/tokscale/crates/tokscale-cli/src/commands/wrapped.rs`, `repos/tokscale/crates/tokscale-cli/src/tui/data/mod.rs`, and `repos/tokscale/packages/frontend/src/app/api/submit/route.ts` at commit `aebe4ea8b9a80d84cb2ff0e3b3472db9ac34051d`.
- Updated [[tokscale]] with a cross-link to the pipeline page and updated `index.md` to list 20 indexed pages.

## [2026-06-10] update | codeburn data ingestion and caching
- Added [[codeburn-data-ingestion-and-caching]] based on `artifacts/codeburn/deepwiki/pages-md/2.1-data-ingestion-and-parsing-pipeline.md`.
- Source-verified discovery, file reading, large JSONL line parsing, turn grouping, session cache, and daily cache behavior against `repos/codeburn/src/fs-utils.ts`, `repos/codeburn/src/parser.ts`, `repos/codeburn/src/session-cache.ts`, `repos/codeburn/src/daily-cache.ts`, `repos/codeburn/src/cli-date.ts`, `repos/codeburn/src/providers/types.ts`, and `repos/codeburn/src/providers/index.ts` at commit `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.
- Recorded the current-source correction that `readSessionFile()` uses a 128MB whole-file cap while `readSessionLines()` is the 2GB streaming path; the DeepWiki 8MB tier description is not current for this checkout.
- Updated [[codeburn]] with a cross-link to the focused deep dive and updated `index.md` to list 21 indexed pages.

## [2026-06-10] update | tokscale rust core processing layer
- Added [[tokscale-rust-core-processing-layer]] based on `artifacts/tokscale/deepwiki/pages-md/3.4.1-core-architecture-and-napi-integration.md`.
- Source-verified the Rust core hierarchy against `repos/tokscale/Cargo.toml`, `repos/tokscale/crates/tokscale-core/Cargo.toml`, `repos/tokscale/crates/tokscale-cli/Cargo.toml`, `repos/tokscale/crates/tokscale-core/src/lib.rs`, `repos/tokscale/crates/tokscale-core/src/clients.rs`, `repos/tokscale/crates/tokscale-core/src/scanner.rs`, `repos/tokscale/crates/tokscale-core/src/sessions/mod.rs`, `repos/tokscale/crates/tokscale-core/src/message_cache.rs`, `repos/tokscale/crates/tokscale-core/src/pricing/mod.rs`, `repos/tokscale/crates/tokscale-core/src/pricing/lookup.rs`, `repos/tokscale/crates/tokscale-core/src/aggregator.rs`, `repos/tokscale/packages/cli/src/index.ts`, `repos/tokscale/packages/cli/package.json`, and `repos/tokscale/.github/workflows/build-native.yml` at commit `aebe4ea8b9a80d84cb2ff0e3b3472db9ac34051d`.
- Recorded current-source correction: DeepWiki's NAPI native-addon bridge claim is stale for this checkout; current production packaging is an npm wrapper that locates and spawns a platform-specific standalone `tokscale-cli` Rust binary using `tokscale-core` as an `rlib` dependency.
- Updated [[tokscale]] and [[tokscale-data-flow-pipeline]] with cross-links and updated `index.md` to list 22 indexed pages.

## [2026-06-10] update | codeburn turn classification engine
- Added [[codeburn-turn-classification-engine]] based on `artifacts/codeburn/deepwiki/pages-md/2.2-turn-classification-engine.md`.
- Source-verified deterministic turn classification against `repos/codeburn/src/classifier.ts`, `repos/codeburn/src/bash-utils.ts`, `repos/codeburn/src/parser.ts`, and `repos/codeburn/src/types.ts` at commit `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.
- Recorded the distinction between category classification, which primarily uses tool-set and user-message regex rules, and bash command breakdown, which stores extracted command base names for reporting.
- Updated [[codeburn]] with a cross-link to the focused deep dive and updated `index.md` to list 23 indexed pages.

## [2026-06-10] update | codeburn pricing and currency resolution
- Added [[codeburn-pricing-and-currency-resolution]] based on `artifacts/codeburn/deepwiki/pages-md/2.3-pricing-and-cost-calculation.md`.
- Source-verified model price source/caching and FX source/caching against `repos/codeburn/package.json`, `repos/codeburn/scripts/bundle-litellm.mjs`, `repos/codeburn/src/models.ts`, `repos/codeburn/src/currency.ts`, `repos/codeburn/src/config.ts`, `repos/codeburn/src/fetch-utils.ts`, `repos/codeburn/src/parser.ts`, `repos/codeburn/src/session-cache.ts`, `repos/codeburn/src/daily-cache.ts`, and `repos/codeburn/src/main.ts` at commit `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.
- Recorded current-source distinctions: runtime model price fetch uses LiteLLM GitHub JSON, build-time fallback generation uses models.dev/OpenRouter, model pricing cache respects `CODEBURN_CACHE_DIR`, exchange-rate cache is fixed under `~/.cache/codeburn/exchange-rate.json`, and currency preference is stored under `~/.config/codeburn/config.json`.
- Updated [[codeburn]] with a cross-link to the focused deep dive and updated `index.md` to list 24 indexed pages.

## [2026-06-10] update | tokscale session parsing and source cache
- Added [[tokscale-session-parsing-and-source-cache]] based on `artifacts/tokscale/deepwiki/pages-md/3.4.2-session-parsing-and-data-sources.md`.
- Source-verified client registry, scanner source discovery, source-message cache/fingerprinting, Codex incremental JSONL parsing, Claude Code sidechain/subagent handling, OpenCode/Kilo SQLite parsing, Cursor CSV format detection, and Gemini JSON/JSONL fallback against `repos/tokscale/crates/tokscale-core/src/clients.rs`, `repos/tokscale/crates/tokscale-core/src/scanner.rs`, `repos/tokscale/crates/tokscale-core/src/sessions/mod.rs`, `repos/tokscale/crates/tokscale-core/src/sessions/claudecode.rs`, `repos/tokscale/crates/tokscale-core/src/sessions/codex.rs`, `repos/tokscale/crates/tokscale-core/src/sessions/opencode.rs`, `repos/tokscale/crates/tokscale-core/src/sessions/cursor.rs`, `repos/tokscale/crates/tokscale-core/src/sessions/gemini.rs`, `repos/tokscale/crates/tokscale-core/src/sessions/kilo.rs`, `repos/tokscale/crates/tokscale-core/src/message_cache.rs`, and `repos/tokscale/crates/tokscale-core/src/lib.rs` at commit `aebe4ea8b9a80d84cb2ff0e3b3472db9ac34051d`.
- Recorded the current-source correction that `SourceFingerprint` includes sampled hashes plus a full SHA-256 content hash, and that Codex receives a special append-only incremental parse path while most other sources use fingerprint hit/miss caching.
- Updated [[tokscale]], [[tokscale-data-flow-pipeline]], [[tokscale-rust-core-processing-layer]], and `index.md` to cross-link the focused deep dive and list 25 indexed pages.

## [2026-06-10] update | tokscale pricing cost and cache
- Added [[tokscale-pricing-cost-and-cache]] based on `artifacts/tokscale/deepwiki/pages-md/3.4.3-pricing-system.md`.
- Source-verified pricing source fetch, custom/Cursor overrides, model lookup, cost calculation, pricing dataset cache, stale-cache fallback, and in-memory lookup cache against `repos/tokscale/crates/tokscale-core/src/pricing/mod.rs`, `repos/tokscale/crates/tokscale-core/src/pricing/cache.rs`, `repos/tokscale/crates/tokscale-core/src/pricing/litellm.rs`, `repos/tokscale/crates/tokscale-core/src/pricing/openrouter.rs`, `repos/tokscale/crates/tokscale-core/src/pricing/models_dev.rs`, `repos/tokscale/crates/tokscale-core/src/pricing/custom.rs`, `repos/tokscale/crates/tokscale-core/src/pricing/lookup.rs`, `repos/tokscale/crates/tokscale-core/src/pricing/aliases.rs`, `repos/tokscale/crates/tokscale-core/src/paths.rs`, `repos/tokscale/crates/tokscale-core/src/lib.rs`, `repos/tokscale/crates/tokscale-cli/src/main.rs`, and `repos/tokscale/README.md` at commit `aebe4ea8b9a80d84cb2ff0e3b3472db9ac34051d`.
- Recorded the current-source correction that Tokscale now fetches three external pricing datasets—LiteLLM, OpenRouter, and models.dev—while Cursor prices are internal static overrides and custom prices are local exact overrides.
- Updated [[tokscale]], [[tokscale-data-flow-pipeline]], [[tokscale-rust-core-processing-layer]], and `index.md` to cross-link the focused deep dive and list 27 indexed pages; also indexed the pre-existing [[codeburn-day-aggregation-and-caching]] page to restore wiki-lint consistency.

## [2026-06-10] update | codeburn day aggregation and caching
- Added/verified [[codeburn-day-aggregation-and-caching]] based on `artifacts/codeburn/deepwiki/pages-md/2.4-day-aggregation-and-caching.md`.
- Source-verified day bucketing, `DailyEntry`/`DailyCache` shape, cache hydration, retention, atomic writes, period rollup, menubar/status/MCP integration, and export differences against `repos/codeburn/src/day-aggregator.ts`, `repos/codeburn/src/daily-cache.ts`, `repos/codeburn/src/usage-aggregator.ts`, `repos/codeburn/src/menubar-json.ts`, `repos/codeburn/src/export.ts`, `repos/codeburn/src/currency.ts`, and `repos/codeburn/src/types.ts` at commit `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.
- Recorded current-source corrections: `DAILY_CACHE_VERSION` is now 8, minimum supported version is 8, `CODEBURN_CACHE_DIR` overrides the daily-cache path, process-local lock chain is distinct from cross-process atomic rename safety, and export rows are built from `ProjectSummary[]` rather than reading `daily-cache.json` directly.
- Updated [[codeburn]] with a cross-link to the focused deep dive and confirmed `index.md` lists 27 indexed pages.

## [2026-06-10] update | codeburn optimization engine
- Added [[codeburn-optimization-engine]] based on `artifacts/codeburn/deepwiki/pages-md/3.3-optimization-engine-(codeburn-optimize).md`.
- Source-verified `codeburn optimize` command flow, Claude JSONL scanner, `ScanData` extraction, detector order, MCP schema-tax costing, ghost entity detection, low-worth/context-heavy/outlier detectors, health scoring, trend logic, urgency sorting, rendering, and context-budget utility boundaries against `repos/codeburn/src/main.ts`, `repos/codeburn/src/optimize.ts`, `repos/codeburn/src/context-budget.ts`, `repos/codeburn/src/providers/index.ts`, `repos/codeburn/src/parser.ts`, and `repos/codeburn/src/types.ts` at commit `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.
- Recorded current-source corrections: DeepWiki line ranges are stale, current detector set is broader than the DeepWiki page, unused-MCP logic is date-range/config-aware rather than a fixed 30-day rule, and `context-budget.ts` is an exported utility not directly invoked by `scanAndDetect()`.
- Updated [[codeburn]] with a cross-link to the focused deep dive and updated `index.md` to list 28 indexed pages.

## [2026-06-11] update | tokscale report generation and aggregation
- Added [[tokscale-report-generation-and-aggregation]] based on `artifacts/tokscale/deepwiki/pages-md/3.4.4-report-generation-and-aggregation.md`.
- Source-verified model/month/hour report entrypoints, `GroupBy` variants, core graph aggregation, TUI `DataLoader::aggregate_messages()`, wrapped PNG summary generation, intensity/streak logic, and source-message cache boundary against `repos/tokscale/crates/tokscale-core/src/aggregator.rs`, `repos/tokscale/crates/tokscale-core/src/lib.rs`, `repos/tokscale/crates/tokscale-core/src/message_cache.rs`, `repos/tokscale/crates/tokscale-cli/src/main.rs`, `repos/tokscale/crates/tokscale-cli/src/tui/data/mod.rs`, and `repos/tokscale/crates/tokscale-cli/src/commands/wrapped.rs` at commit `aebe4ea8b9a80d84cb2ff0e3b3472db9ac34051d`.
- Recorded current-source corrections: current report code is not centered on a single `finalize_report()` function, `GroupBy` now includes `Session` and `ClientSession`, and graph intensity differs by surface (`u8` 0-4 in core/wrapped versus `f64` 0.0-1.0 in TUI).
- Updated [[tokscale]], [[tokscale-data-flow-pipeline]], [[tokscale-pricing-cost-and-cache]], and `index.md` to cross-link the focused deep dive and list 29 indexed pages.

## [2026-06-11] update | codeburn subscription plans and currency
- Added [[codeburn-subscription-plans-and-currency]] based on `artifacts/codeburn/deepwiki/pages-md/3.5-subscription-plans-and-currency.md`.
- Source-verified provider-keyed plan config, preset monthly USD budgets, `codeburn plan` command behavior, reset-day billing period, median-daily projection, multiple provider-scoped usage calculation, plan JSON currency conversion, FX fetch/cache/validation, rounding boundaries, and subscription-covered proxy cost attribution against `repos/codeburn/src/config.ts`, `repos/codeburn/src/plans.ts`, `repos/codeburn/src/plan-usage.ts`, `repos/codeburn/src/currency.ts`, `repos/codeburn/src/main.ts`, `repos/codeburn/src/export.ts`, `repos/codeburn/src/types.ts`, and `repos/codeburn/src/parser.ts` at commit `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.
- Recorded current-source corrections: current config prefers provider-keyed `plans` over legacy `plan`, `claude-max` displays as `Claude Max 20x`, plan budgets are stored in USD and converted only at report/status/export boundaries, and exchange-rate cache remains fixed under `~/.cache/codeburn/exchange-rate.json`.
- Updated [[codeburn]] with a cross-link to the focused deep dive and updated `index.md` to list 30 indexed pages.

## [2026-06-11] update | codeburn provider plugin system
- Added [[codeburn-provider-plugin-system]] based on `artifacts/codeburn/deepwiki/pages-md/4-provider-plugin-system.md`.
- Source-verified provider interface shape, `ParsedProviderCall` schema, core provider registry, optional lazy provider loaders, `discoverAllSessions()` provider filtering, `parseProviderSources()` cache/dedup/date-filter integration, SQLite provider shim/parser, and representative Codex/Cursor/OpenCode/Antigravity behavior against `repos/codeburn/src/providers/types.ts`, `repos/codeburn/src/providers/index.ts`, `repos/codeburn/src/providers/codex.ts`, `repos/codeburn/src/providers/cursor.ts`, `repos/codeburn/src/providers/opencode.ts`, `repos/codeburn/src/providers/antigravity.ts`, `repos/codeburn/src/providers/sqlite-session-parser.ts`, `repos/codeburn/src/sqlite.ts`, `repos/codeburn/src/parser.ts`, and `repos/codeburn/tests/provider-registry.test.ts` at commit `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.
- Recorded current-source corrections: the registry is larger than DeepWiki's provider list, SQLite integration now uses `node:sqlite` rather than `better-sqlite3`, `providers` exports only core providers while `getAllProviders()` includes lazy providers, Cursor uses workspace mapping plus orphan sources, and Antigravity includes statusline plus RPC/cache paths.
- Updated [[codeburn]] with a cross-link to the focused deep dive and updated `index.md` to list 32 indexed pages.
- Added `cli`, `terminal`, and `commands` to `wiki/SCHEMA.md` tag taxonomy because the follow-up wiki-lint surfaced those pre-existing tags on [[tokscale-cli-terminal-commands]].

## [2026-06-11] update | codeburn codex provider
- Added [[codeburn-codex-provider]] based on `artifacts/codeburn/deepwiki/pages-md/4.3-other-providers-(codex-copilot-opencode-piomp-and-more).md`, focused on the Codex provider rather than all secondary providers.
- Source-verified Codex provider registry membership, `CODEX_HOME`/`~/.codex` discovery, `sessions/YYYY/MM/DD/rollout-*.jsonl` scan, large `session_meta` handling, streaming JSONL parser, tool normalization, `last_token_usage` vs `total_token_usage` handling, cached-token subtraction, cost calculation, fork replay deduplication, Codex-specific `codex-results.json` cache, and test-backed edge cases against `repos/codeburn/src/providers/codex.ts`, `repos/codeburn/src/codex-cache.ts`, `repos/codeburn/src/fs-utils.ts`, `repos/codeburn/src/parser.ts`, `repos/codeburn/src/providers/index.ts`, `repos/codeburn/tests/providers/codex.test.ts`, and `repos/codeburn/tests/provider-registry.test.ts` at commit `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.
- Recorded current-source corrections: DeepWiki's cumulative-delta summary is incomplete because `last_token_usage` is preferred, Codex cache stores project plus parsed calls in cache version 3, fork dedup uses parent namespace plus cumulative token breakdown, and DeepWiki line ranges are stale for the current checkout.
- Attempted `pnpm exec vitest run tests/providers/codex.test.ts tests/provider-registry.test.ts`; it failed because `vitest` is not installed in the checkout (`node_modules/.bin/vitest` missing), so this update is source/test-file inspected rather than locally test-executed.
- Updated [[codeburn]] and [[codeburn-provider-plugin-system]] with cross-links and updated `index.md` to list 33 indexed pages.

## [2026-06-11] update | codeburn report status export commands
- Added [[codeburn-report-status-export-commands]] based on `artifacts/codeburn/deepwiki/pages-md/3.2-report-status-and-export-commands.md`.
- Source-verified the launcher-vs-command split, `report --format json`, `status` terminal/json/menubar-json paths, `today`/`month` JSON shortcuts, export period construction, CSV directory output, JSON export schema, currency loading/rounding, CSV injection guard, and overwrite safety against `repos/codeburn/src/cli.ts`, `repos/codeburn/src/main.ts`, `repos/codeburn/src/export.ts`, `repos/codeburn/src/format.ts`, `repos/codeburn/src/currency.ts`, `repos/codeburn/src/usage-aggregator.ts`, `repos/codeburn/src/menubar-json.ts`, `repos/codeburn/tests/export.test.ts`, `repos/codeburn/tests/menubar-json.test.ts`, `repos/codeburn/tests/cli-status-menubar.test.ts`, and `repos/codeburn/tests/cli-export-date-range.test.ts` at commit `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.
- Recorded current-source corrections: current command logic lives in `src/main.ts` rather than `src/cli.ts`, `report` defaults to TUI and needs `--format json` for JSON, status terminal and JSON report use different date attribution boundaries, CSV export uses a `.codeburn-export` marker guard, JSON export uses a schema-marker overwrite guard, and export output includes `README.txt` plus `summary.csv`.
- Verified actual CLI help after `npm ci` with `npx tsx src/main.ts --help`, `report --help`, `status --help`, and `export --help`; the help commands succeeded while Node printed `DEP0205 module.register()` deprecation warnings through the `tsx` path.
- Ran `npm exec vitest -- run tests/export.test.ts tests/menubar-json.test.ts tests/cli-status-menubar.test.ts tests/cli-export-date-range.test.ts`: 4 test files / 24 tests passed.
- Updated [[codeburn]] with a cross-link and updated `index.md` to list 34 indexed pages.

## [2026-06-11] update | tokscale CLI terminal commands
- Added [[tokscale-cli-terminal-commands]] based on DeepWiki `artifacts/tokscale/deepwiki/pages-md/3.2-commands-reference.md` and source-verified current `clap` command definitions/help output against `repos/tokscale/crates/tokscale-cli/src/main.rs`, `repos/tokscale/crates/tokscale-core/src/clients.rs`, `repos/tokscale/crates/tokscale-core/src/lib.rs`, npm wrapper packages, and README at commit `aebe4ea8b9a80d84cb2ff0e3b3472db9ac34051d`.
- Recorded current-source corrections: canonical client filtering is `--client/-c` while legacy boolean client flags are hidden deprecated compatibility flags; current command surface includes additional commands such as `qr`, `usage`, `codex`, `antigravity`, `trae`, `warp`, `delete-submitted-data`, and `time-metrics` beyond the DeepWiki table; current provider filter accepts `custom`, `litellm`, `openrouter`, and `models.dev`.
- Updated [[tokscale]], [[tokscale-report-generation-and-aggregation]], and `index.md` to cross-link the command reference; `scripts/wiki-lint.py` currently reports 34 indexed pages.

## [2026-06-11] update | Open-source analysis judgment model
- Added [[open-source-analysis-judgment-model]] as the shared lens for turning source-verified repo analysis into `Taste Notes`, `stealable-pattern-*` concept pages, and future `comparisons/` pages.
- Updated [[llm-wiki-operating-model]] with the judgment accumulation layer.
- Updated `wiki/SCHEMA.md` with `judgment` and `pattern` tags plus the default `Taste Notes` dimensions: `Responsibility Boundaries`, `Architecture Decision Taste`, `Trade-offs / Risks`, `Stealable Patterns`, and `Comparison Hooks`.
- Recorded the agreed exclusions from default wiki sections: `Quality Signals`, `First Meaningful Success`, `Prompt / Intent Review`, and a separate `Taste Rubric` file.
- Updated `index.md` to list 36 indexed pages.
- Verified wiki health with `python3 scripts/wiki-lint.py`: 0 issues, 0 warnings, 36 indexed pages.

## [2026-06-14] update | career-ops project structure and setup
- Added [[career-ops]] based on DeepWiki overview/setup/config/examples pages and source verification against `repos/career-ops` at commit `57b34c07e01cd106528936398507e1b4552ca295`.
- Source-verified setup and architecture claims against `repos/career-ops/README.md`, `repos/career-ops/AGENTS.md`, `repos/career-ops/DATA_CONTRACT.md`, `repos/career-ops/package.json`, `repos/career-ops/doctor.mjs`, `repos/career-ops/scaffolder/bin/cli.mjs`, `repos/career-ops/config/profile.example.yml`, `repos/career-ops/templates/portals.example.yml`, `repos/career-ops/modes/_shared.md`, `repos/career-ops/modes/auto-pipeline.md`, `repos/career-ops/modes/oferta.md`, `repos/career-ops/scan.mjs`, `repos/career-ops/generate-pdf.mjs`, `repos/career-ops/generate-latex.mjs`, `repos/career-ops/merge-tracker.mjs`, and `repos/career-ops/dashboard/main.go`.
- Verified current cold-start signal with `node doctor.mjs --json`: onboarding needed in the analysis checkout because `cv.md`, `config/profile.yml`, `modes/_profile.md`, and `portals.yml` are absent; Playwright MCP warning is reported.
- Updated `index.md` to list 37 indexed pages.

## [2026-06-15] update | graphify coding query practices
- Added [[graphify-query-practices-for-coding]] based on source verification against `repos/graphify/graphify/serve.py`, `repos/graphify/graphify/__main__.py`, `repos/graphify/graphify/querylog.py`, `repos/graphify/graphify/skill.md`, `repos/graphify/tools/skillgen/fragments/references/query/cli.md`, and installed Codex skill files under `/Users/kkh/.codex/skills/graphify/`.
- Recorded the current CLI behavior verified with `uv run python -m graphify --help` at `repos/graphify` commit `8a04560`: `query` is lexical seed selection plus BFS/DFS traversal, while coding-work prompts should ask the AI to expand Korean/abstract intent into actual graph node label/source_file vocabulary before running `graphify query`.
- Updated [[graphify]], [[graphify-cli-reference]], and [[graphify-extract-query-mechanics]] with cross-links to the focused query-practices page.
- Updated `index.md` to list 38 indexed pages.


## [2026-06-15] update | Understand-Anything source-verified analysis
- Added [[Understand-Anything]] based on Gemini baseline artifacts and source verification against `repos/Understand-Anything` at commit `7a3b7511b26a1816be3b6cc5683b34779e0abce9`.
- Wrote reports: `reports/Understand-Anything/overview.md`, `architecture.md`, `pipeline.md`, `core.md`, `dashboard.md`, and `gemini-baseline-comparison.md`.
- Source-verified pipeline/core/dashboard claims against `understand-anything-plugin/skills/*`, `agents/*`, `hooks/*`, `packages/core/src/*`, and `packages/dashboard/*`.
- Verified commands after `pnpm install --frozen-lockfile`: core build/test, skill build, dashboard build, root tests, and lint all succeeded; dashboard build emitted a large ELK chunk warning.
- Updated `index.md` to list 39 indexed pages.

## [2026-06-17] update | claude-devtools 1차 core wiki ingestion
- Added [[claude-devtools]], [[claude-devtools-electron-process-and-ipc]], [[claude-devtools-session-discovery-and-jsonl-parsing]], and [[claude-devtools-context-token-and-session-analysis]].
- Wrote follow-up plan: `reports/claude-devtools/wiki-ingestion-plan.md` with 0차 status, 1차 completed scope, and 2차~5차 goal roadmap.
- Source-verified against `repos/claude-devtools` at commit `16cc3c87c1e4d0e08ee101fb52dad1b85dbbe48a` / `v0.5.0`; key paths included `src/main/index.ts`, `src/main/ipc/sessions.ts`, `src/main/services/infrastructure/ServiceContext.ts`, `ServiceContextRegistry.ts`, `DataCache.ts`, `src/main/services/discovery/ProjectScanner.ts`, `SubagentResolver.ts`, `src/main/services/parsing/SessionParser.ts`, `MessageClassifier.ts`, `src/main/services/analysis/ChunkBuilder.ts`, `ConversationGroupBuilder.ts`, `src/main/utils/jsonl.ts`, `pathDecoder.ts`, `src/preload/index.ts`, `src/shared/types/api.ts`, `src/renderer/store/index.ts`, `src/renderer/types/contextInjection.ts`, and `src/renderer/utils/contextTracker.ts`.
- Recorded current-source corrections: no standalone `SessionAnalyzer.ts`, cost metrics do not currently compute actual USD pricing, encoded path decode is lossy and prefers `cwd`, session detail IPC strips raw messages, and `DataCache` is in-memory LRU/TTL with fingerprint invalidation.
- Updated `index.md` to list 43 indexed pages.

## [2026-06-20] update | DeepTutor intelligent learning-agent modules
- Added [[deeptutor]] based on the provided `deepwiki-ko/DeepTutor/4*` module pages and source verification against `repos/DeepTutor` at commit `88c2565389dd6b8bdee228b50f8c76d8c990d6b6`.
- Added [[stealable-pattern-learning-ai-agent-modules]] to preserve reusable learning-AI design patterns: explicit prompt context sections, Explore→Plan→Generate, educational IRs, label/tool action grammar, evidence compression, local validation/repair, streamable artifacts, and deterministic mastery gates.
- Source-verified important module claims against current paths including `deeptutor/runtime/bootstrap/builtin_capabilities.py`, `deeptutor/agents/chat/agentic_pipeline.py`, `deeptutor/capabilities/solve/*`, `deeptutor/agents/research/pipeline.py`, `deeptutor/agents/question/pipeline.py`, `deeptutor/book/*`, `deeptutor/co_writer/*`, `deeptutor/agents/vision_solver/vision_solver_agent.py`, `deeptutor/agents/visualize/*`, `deeptutor/agents/math_animator/*`, `deeptutor/capabilities/mastery/*`, and `deeptutor/learning/*`.
- Recorded current-source corrections: DeepWiki's separate Auto Mode capability is not registered in current source; Smart Solver is a chat-loop extension rather than a standalone solve pipeline; several older `deeptutor/capabilities/deep_*.py` paths have moved.
- Updated `index.md` to list 45 indexed pages.

## [2026-06-20] update | DeepTutor mode workflow details
- Added [[deeptutor-mode-workflows]] as a source-verified per-mode runtime map for `chat`, `deep_solve`, `deep_research`, `deep_question`, `book`, `co_writer`, `visualize`, `math_animator`, `geogebra_analysis`/Vision Solver, and `mastery_path`.
- Recorded each mode/service's entrypoint, LLM prompt/context construction, tool or validator usage, streaming/result shape, and persistence location, verified against `repos/DeepTutor` at commit `88c2565389dd6b8bdee228b50f8c76d8c990d6b6`.
- Updated [[deeptutor]] with a cross-link to the detailed mode workflow page and updated `index.md` to list 46 indexed pages.

## [2026-06-21] update | ponytail project overview
- Added [[ponytail]] based on `deepwiki-ko/ponytail/1-overview.md`, `1.1-the-ponytail-philosophy.md`, and `1.2-agent-portability-and-supported-hosts.md`.
- Source-verified ladder philosophy, safety boundaries, adapter model, runtime mode state, OpenCode/Pi injection surfaces, MCP prompt/tool surface, and test/CI status against `repos/ponytail` at commit `6da37bfa7d0282522c7785759f4d2f1544015354`.
- Updated `index.md` to list 47 indexed pages.

## [2026-09-11] update | workspace operating model and templates
- Overhauled `AGENTS.md` and `OSS_ANALYSIS_WORKFLOW.md` around the core flow: **archify로 파악 → 질문 → 코드 검증 → reports 기록 → wiki 축적**.
- Established strict distinction between `reports/` (detailed question investigations, evidence paths, diagrams, and `next.md`) and `wiki/` (durable, reusable synthesized knowledge).
- Added standardized workspace templates under `templates/`: `request-template.md`, `overview-template.md`, `question-template.md`, and `next-template.md`.
- Updated `scripts/analyze-repo.sh` to initialize the updated report structure (`diagrams/`, `questions/`, `overview.md`, and `next.md`).
- Aligned `wiki/SCHEMA.md` workspace boundary and Git ignore policy (`/repos/` ignored, tracking reports/wiki/diagrams/templates).

## [2026-09-15] update | Graft first analysis pass
- Added [[graft]] (`wiki/projects/graft.md`) from a first analysis pass over `repos/Graft` at commit `f9e65396e638e517aecae0d731017f53084d70ed` (shallow clone, clean worktree).
- Created `reports/Graft/` with `overview.md`, `next.md`, and two archify diagrams in `diagrams/` (`structure.json`/`.html` — module map with the deterministic-core boundary; `flow.json`/`.html` — one `graft ask` call end to end). Both delivered at showcase quality: 9/9 artifact checks, 0 composition errors/warnings, 17 source references verified against the local checkout; `visual-check` passed at 1440x900, 1600x1000, 1920x1080, and 2048x1320. Receipts kept in `artifacts/Graft/`.
- Source-verified the load-bearing claims: the two-tier pipeline (`src/graph/extract.ts` tree-sitter Tier 1 vs `src/ai/*` `--deep`), refresh-on-query via `src/graph/refresh.ts:150 ensureFreshGraph()` comparing working-tree bytes rather than git state, the vendor-neutral provider factory (`src/ai/llm/factory.ts`), and the two integration surfaces (`src/cli.ts` 24 commands, `src/mcp/server.ts` with `src/mcp/tools.ts` calling the engine directly).
- Marked as unverified: README's benchmark numbers (tool call -46%, tokens -42%, time -60%, correctness 54% -> 66%) — no reproduction procedure found in the repo, and nothing was executed this session (`npm test`, 122 test files, not run).
- Left unread and queued in `reports/Graft/next.md`: `src/ask/ask.ts` ranking internals (1,588 lines, the largest file), `src/brain/*` (the open-source/cloud boundary), and `src/app/*` (GitHub App runtime).
- Added the `graft` tag to `wiki/SCHEMA.md`; updated `index.md` to list 48 indexed pages.


## [2026-09-14] add | rsshub and folo project pages
- Added [[rsshub]] — source-verified layered architecture (entrypoint / middleware / registry / route plugins), request-coalescing cache, HTTP-vs-browser collection split, and static catalog stats (1,906 sites, 3,462 routes, 3.0% browser-based, 58.2% Chinese-language) at commit `0a4ecdb02390fb047bb675a1764e1dedbf5cf9bc`.
- Added [[folo]] — source-verified client-only monorepo: public `@follow-app/client-sdk` boundary to a closed backend (`api.folo.is`), one React codebase for web + Electron desktop, and one drizzle schema over two SQLite engines (wa-sqlite WASM / expo-sqlite) at commit `44f0e5df06eba774afe1f1aea30d90a742da5dec`.
- Recorded the complementary relationship between the two: RSSHub generates feeds (fully open, self-hostable), Folo reads them (client open, backend closed).
- Updated `index.md` to list 50 indexed pages.

## [2026-09-20] update | rsshub as an endpoint catalog, not a dependency
- Added [reports/rsshub/questions/q3-vps-info-adoption.md](../reports/rsshub/questions/q3-vps-info-adoption.md): how far to adopt RSSHub in the scheduler-based `vps-info` (signal-archive) collector, and which providers to pull.
- Verified at commit `0a4ecdb02390fb047bb675a1764e1dedbf5cf9bc` that **RSSHub has no persistence layer at all** — zero DB dependencies in `package.json`, state limited to TTL caches (`routeExpire` 300s / `contentExpire` 3600s, `lib/config.ts:795-796`). It is a request-time transformer, not an archive, so the only overlap with a collect-and-store project is the single "site → normalized item list" step.
- Concluded the practical use is as an **endpoint catalog**: read `lib/routes/<site>/*.ts` for the URL each site is actually called with, and implement directly — the real cost of adding a provider is endpoint discovery, which RSSHub has already done for 1,906 sites.
- Recorded that `DataItem` is not worth adopting as a common format (half of it is feed-rendering-only; it has no dedup/first-seen/run-history concepts), that some routes proxy official feeds (`theverge`, `openai`), and that `/hackernews/*` is HTML scraping — a downgrade from the Firebase official API.
- Updated [[rsshub]] with a "소비하는 쪽에서 쓸 때" section and refreshed `reports/rsshub/next.md`.

## [2026-09-24] update | rsshub re-verified against the vps-info TypeScript redesign
- Added [reports/rsshub/questions/q4-vps-info-typescript-redesign.md](../reports/rsshub/questions/q4-vps-info-typescript-redesign.md): what to adopt from RSSHub now that `vps-info` is a TypeScript (Fastify + Drizzle) resident collector with a DB-owned schedule.
- Re-verified the main [[rsshub]] claims at commit `0a4ecdb02390fb047bb675a1764e1dedbf5cf9bc`, and newly recorded `Data.allowEmpty` + the empty-route exception (`lib/middleware/parameter.ts:71`), the shared `ofetch` client's retry status codes (including 400/409) with `timeout` commented out (`lib/utils/ofetch.ts`), and the typed error-to-status mapping (`lib/errors/`).
- Kept the endpoint-catalog conclusion; added that TypeScript consumers can reuse the MIT libraries (`ofetch`, `rss-parser`, `cheerio`) but must not copy AGPL route code, and that directory-scan registration only pays off at thousands of plugins.
- Marked the Python-era parts of Q3 as superseded, linked Q4 from `overview.md`, and refreshed `reports/rsshub/next.md`.

## [2026-09-29] setup | claude-devtools re-baselined for a new analysis round
- Fast-forwarded `repos/claude-devtools` from `16cc3c8` (v0.5.0) to `1486f2042c87bb547a4e34808ab54ab34a33f132` (8 commits, 13 files, small UI/deploy changes); kept the old metadata as `artifacts/claude-devtools/repo-metadata.2026-05-deepwiki-baseline.txt`.
- Created [reports/claude-devtools/overview.md](../reports/claude-devtools/overview.md) and [next.md](../reports/claude-devtools/next.md) in the current template format. No change to [[claude-devtools]] content yet.
- Re-cloned `repos/claude-devtools` fresh (same HEAD `1486f20`) and added the archify architecture map [reports/claude-devtools/diagrams/structure.html](../reports/claude-devtools/diagrams/structure.html) (showcase 9/9, visual-check pass).


## [2026-09-30] analysis | Understand-Anything CodeWiki baseline
- Re-pointed `repos/Understand-Anything` origin to Egonex-AI and fast-forwarded to `b05cc3b20990afca537b4fc0a49b4d7fbdc65bb0`; generated CodeWiki output in `artifacts/Understand-Anything/codewiki/`.
- Verified key claims against source and wrote [reports/Understand-Anything/overview.md](../reports/Understand-Anything/overview.md), and `next.md`; existing [[Understand-Anything]] wiki page (2026-06) left unchanged, not yet reconciled. archify structure map added at reports/Understand-Anything/diagrams/structure.html and /understand flow diagram at diagrams/flow.html; agent-to-Phase mapping verified in overview.

## [2026-09-30] analysis | CodeWiki cloned, run on itself, and fact-checked
- Cloned `repos/CodeWiki` at `3e3d848698c7bf1a0ce2e0b49e66841acd0248aa`; installed into `repos/CodeWiki/.venv` (uv, Python 3.12) and set the claude-code subscription provider (`claude-sonnet-5-5`). Usage notes added to the root `AGENTS.md`.
- Generated Korean self-docs twice (`artifacts/CodeWiki/codewiki/` with depth 2, `codewiki-depth4/` with depth 4) and fact-checked samples against source, including the upstream 1.0.1 `docs/`: [reports/CodeWiki/questions/q1-output-quality.md](../reports/CodeWiki/questions/q1-output-quality.md).
- Added [reports/CodeWiki/overview.md](../reports/CodeWiki/overview.md), [next.md](../reports/CodeWiki/next.md), the archify map [diagrams/structure.html](../reports/CodeWiki/diagrams/structure.html) (showcase 9/9, visual-check pass), and [[codewiki]].
## [2026-09-15] update | Graft full system architecture
- Added a third archify diagram, `reports/Graft/diagrams/system.json`/`.html`, covering the whole system rather than the module map: local CLI runtime, the separate GitHub App runtime, and every external service. Delivered at showcase quality (9/9 artifact checks, 0 errors/warnings, 21 source references verified against the local checkout) and `visual-check` passed at 1440x900, 1600x1000, 1920x1080, and 2048x1320.
- Source-verified the four network egress points and recorded them in [[graft]]: `--deep` to the user's own LLM endpoint, opt-in brain rules to `/api/public/brains/<id>/rules/anchors` (`src/brain/link.ts:133`), `https://api.github.com` from the GitHub App runtime only (`src/app/identity.ts:115`), and telemetry to the baked `https://events.nanonets.com` (`src/telemetry/key.ts:44`).
- Recorded that brain-rule fetches are bounded by `AbortSignal.timeout(5000)` with a 6-hour cache TTL and a 6-rule prompt cap, and that `src/app/*` is a webhook server plus `WorkQueue` plus forked child workers reusing the same Graph Core without going through the CLI.
- Narrowed the open questions in `reports/Graft/next.md` accordingly: `src/brain` and `src/app` are now confirmed at import-graph and signature level; their runtime semantics remain unread.


## [2026-09-21] update | Codenotch first analysis pass
- Cloned `vinzdg/codenotch` into `repos/codenotch` (shallow `--depth 50`) at commit `414ceaf6173d9988c01ed76d8e924cf0118e3755` (2026-09-20, "Codenotch 1.16.0 appcast"), clean worktree. Baseline recorded in `artifacts/codenotch/repo-metadata.txt`.
- Added [[codenotch]] (`wiki/projects/codenotch.md`) and `reports/codenotch/` with `overview.md`, `next.md`, and two archify diagrams in `diagrams/` (`structure.json`/`.html` — `Sources/` module map with the AppDelegate wiring and the usage/activity split; `flow.json`/`.html` — one usage refresh pass from timer tick to notch publish, including the deadline/abandon path). Both delivered at showcase quality: 9/9 artifact checks, 0 composition errors/warnings; the module map verified 10 source references against the local checkout at the pinned revision. `visual-check` passed at 1440x900, 1600x1000, 1920x1080, and 2048x1320 in both themes.
- Source-verified the load-bearing design claims: `Fidelity { official, derived, manual }` with a `~` qualifier (`Sources/Model/UsageModel.swift:15`); the deliberate split between `needsAuth`, `signedOutByOwner`, and `accessDenied` in `UsageProviderError` (`Sources/Providers/UsageProvider.swift:70-118`); declared `headlineID`/`weeklyID` rather than positional window selection; the pure `UsageStore.shouldRefresh(...)` polling predicate and `hasWindowRolledOver(...)` (`Sources/Model/UsageStore.swift:296-337`); the deadline that abandons rather than cancels a pass because `SecItemCopyMatching` blocks past `Task.cancel()`; `ActivityCoordinator` feeding only `isBusy` into the store; `SessionCompletionWatcher` reporting transitions rather than states; and `NotchPlacement` as the single mapping from 1-D stack space to screen coordinates.
- Marked as unverified: the 429 back-off (60s doubling to a 15-minute cap, persisted across relaunch) is a README claim whose implementation was not located this session; the "every adapter's response shape is pinned by tests" claim was not checked against `Tests/`; the `windows/` Rust/Tauri port was only counted, not read.
- Recorded a hard constraint in `reports/codenotch/next.md`: the app is macOS-only (`xcodegen` + `xcodebuild`) and the analysis machine is Windows, so **the verification ceiling for this repo is `코드 확인` — `실행 확인` is not reachable here.**
- Left unread and queued: 76 of 77 files under `Sources/Providers` (only the protocol was read; `ClaudeOAuthProvider.swift`'s 663 lines are doc-comment only), all of `Sources/Notch`/`Features`/`Settings`, and all 93 test files. Five entry questions drafted in `overview.md`, with `ClaudeOAuthProvider`'s three-source fallback recommended first.
- Updated `wiki/index.md` to 49 indexed pages.

## [2026-09-21] update | Codenotch usage-acquisition deep dive (Q1)
- Answered the session's driving question — how Codex / Claude Code / Gemini usage is actually obtained — in `reports/codenotch/questions/q1-how-usage-is-fetched.md`, and added a third archify diagram `reports/codenotch/diagrams/system.json`/`.html` (Korean-authored; archify's `meta.locale` supports only `en`/`zh-CN`, so the Viewer UI and `<html lang>` fall back to English while the authored content stays Korean). Delivered at showcase quality: 9/9 artifact checks, 0 errors/warnings, 10 source references verified against the local checkout at `414ceaf…`; `visual-check` passed at 1440x900, 1600x1000, 1920x1080, and 2048x1320 in both themes. Receipt in `artifacts/codenotch/`.
- Source-verified that **no vendor publishes a usage API**: every host the code calls is an internal path — `api.anthropic.com/api/oauth/usage` with an `anthropic-beta: oauth-2025-04-20` header, `chatgpt.com/backend-api/wham/usage`, `cloudcode-pa.googleapis.com/v1internal:loadCodeAssist` and `daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary`, `cursor.com/api/usage-summary`, `api.github.com/copilot_internal/user`, `opencode.ai/zen/go/v1/usage`, `cli-chat-proxy.grok.com/v1/billing`, `api.kimi.com/coding/v1/usages`. Extracted by grepping every HTTPS literal under `Sources/Providers/` and confirming each in its file. No network call was made.
- Recorded the five acquisition mechanisms in [[codenotch]]: CLI subprocess (`claude --print --no-session-persistence --strict-mcp-config /usage`, which removes this app's need for keychain access entirely because Claude Code files a new keychain item on every token rotation), the login keychain, read-only files/SQLite/Chromium HTTP cache (`~/.codex/auth.json`, Cursor's `state.vscdb`, Claude Desktop's zstd-encoded cache — the reason a decode-only Zstandard is vendored), local daemons and language servers, and Codenotch's own WKWebView session for the three providers that have no borrowable credential.
- The Antigravity/Gemini path is the notable one and is now a stealable pattern in [[codenotch]]: Google's `retrieveUserQuotaSummary` answers 403 to a personal account because the API judges *which client* is asking, so the provider calls **Antigravity's own language server on this machine** — the same door Antigravity's window uses. Port discovery spawns `ps` and `lsof`, both of the server's two ports are tried because it does not advertise which serves the RPC, and the CSRF header is `x-codeium-csrf-token` (`AntigravityBridge.swift:1-35`).
- Account auto-discovery is a two-stage test, source-verified at `ClaudeProfile.swift:33-90`: the `~/.claude-<slug>` / `~/.codex-<slug>` directory convention (used because a Finder-launched app never inherits a shell's `CLAUDE_CONFIG_DIR` or `CODEX_HOME`), then whether a keychain item exists under that directory's own service name. The second stage is what keeps the `claude-mem` plugin — which passes every filename rule — from being drawn as an account. Discovery runs once at launch (`AppDelegate.swift:69-71`), so adding a profile needs a restart; local runtimes are judged by whether their port answers and return `isVisibleWhenAbsent = false` so a stopped daemon takes no ring.
- Resolved the previously open Q3: the 429 back-off lives in the *provider*, not the store — `min(15min, max(60 * 2^min(n,4), Retry-After))` at `ClaudeOAuthProvider.swift:429-435`, with the server's `Retry-After: 0` honoured only as a floor-raiser, and the deadline persisted through `UsageArchive.saveBackoffUntil` / `loadBackoffUntil` so a relaunch cannot bypass it (`CodexLocalProvider.swift:27`).
- Still unread and queued in `reports/codenotch/next.md`: every `*Usage.swift` response parser (~20 files, where `LimitWindow` normalization lives), `fetch(retryingOnUnauthorized:)`'s HTTP-to-`ProviderStatus` mapping, `CredentialCache`'s modification-date invalidation, and all 93 test files. Verification ceiling remains `코드 확인` — the app is macOS-only and this machine is Windows.

## [2026-10-06] create | pi `ai` package summary and reusable patterns
- Created [[pi]] (`wiki/projects/pi.md`) from the 13-document analysis in `reports/pi/ai/` (00-role through 06-call-flow, including 03-1~03-4 and 04-01) at commit `3874b3e98` (2026-10-02). Scope is the `ai` package only; `confidence: medium` at page level because the other packages are declared-only, while the `ai` claims are source-verified (and run where cheap).
- Created three concept pages: [[pi-ai-provider-api-separation]] (api vs provider with per-model `compat`), [[stealable-pattern-async-event-stream-with-final-result]] (`EventStream<T, R>`: push, `for await`, and a `result()` that never rejects), and [[stealable-pattern-stored-credential-owns-provider]] (precedence, no silent env fallback, serialized `modify`).
- Evidence by execution (cheap local runs of the real source with fake inputs, scripts and dated logs in `artifacts/pi/ai-demos/`): event-stream producer/consumer timing, SSE and WebSocket parsing, OpenAI Responses event conversion, the auth precedence cases and single-refresh locking, retry/overflow/token-estimate behavior, `detectCompat` per provider, and an end-to-end call with a fake wire layer. `partial-json` and `typebox` were not installed, so `parseStreamingJson`'s partial parse and `validateToolArguments` were read but not run.
- Corrected earlier claims from the 4259686d9-era analysis: retry is no longer done by an agent harness (it was deleted in `7fd478a2e`; `coding-agent` and `durable` do it); the synchronous throw on missing auth applies only when a wire module's `streamSimple` is called directly; `openai` with Sign in with ChatGPT is the current path and `openai-codex` is legacy. Q5~Q8 are flagged for re-verification at the `agent` stage.
- Web check (OpenAI developer docs): the Sign in with ChatGPT token-sharing flow matches `auth/oauth/openai-chatgpt.ts` (`dynamic_agent_client`, `resource=https://api.openai.com/v1`, `chatgpt.tokens.use.direct`). No official statement about retiring the older Codex backend path was found.
- Updated `wiki/index.md` to 56 indexed pages (matches `scripts/wiki-lint.py`).

## [2026-10-06] update | pi `agent` package analysis complete
- Read `agent-loop.ts` (940 lines), `agent.ts` (613), `proxy.ts` (406), `stream-fn.ts` and wrote `reports/pi/agent/02-agent-loop`, `03-agent-class`, `04-proxy`, `05-call-flow`. Analyzed at `28dcce2ba` (v1.0.4); `packages/agent/src` is identical to `3874b3e98` (the diff is `CHANGELOG.md` and `package.json` only).
- Ran the real `agent.ts`/`agent-loop.ts`/`proxy.ts` against fake `streamFn`s and a local SSE server (127.0.0.1 only) in `artifacts/pi/agent-demos/`. `typebox@1.3.27` and `partial-json@0.1.7` were installed with `--ignore-scripts` into that folder only (user-approved); `repos/pi` untouched. All 15 loop/Agent claims and the proxy claims matched the code reading.
- Findings: termination priority has seven levels and `error`/`aborted` beats `finishTurn`; parallel tools prepare sequentially, run concurrently, end in completion order, and write results in call order; abort during sequential tools leaves a `toolCall` without `toolResult` and `Agent` does not fill it; `agentLoop` (stream-returning) never ends if the loop rejects; a failed run's `agent_end.messages` is only the synthetic failure message; `streamProxy` leaves `partialJson` in the final message when cut mid tool call and is not used by coding-agent.
- Re-verified earlier Q5 and Q6 (match); added notes to both. Q7/Q8 wait for the coding-agent stage.
- Added [[stealable-pattern-hook-injected-loop-with-throw-contract]] and [[pi-agent-turn-end-decision-priority]]; updated [[pi]] and `wiki/index.md`.

## [2026-10-06] update | pi ai docs re-checked against `28dcce2ba`
- Read the `3874b3e98..28dcce2ba` diff for the `ai` files our docs cite (`auth/resolve.ts`, `auth/oauth/openai-chatgpt.ts`, `api/anthropic-messages.ts`, `api/simple-options.ts`, `api/openai-*.ts`, `models.ts`, `types.ts`, `utils/transcript.ts`, `utils/retry.ts`, `providers/azure*`) and patched `reports/pi/ai/01, 02, 03-1, 03-2, 03-3, 04, 05, 06` with dated NOTE blocks. Whole-repo diff is 280 files but the new work is `packages/env` and `durable`, outside what was analyzed; `packages/agent/src` is unchanged.
- Behavior changes recorded: OAuth refresh now ignores the caller's signal once started (only the lock wait is cancellable); `samplingParamsByThinkingLevel`; Anthropic `tool_addition` carries the definition by value; provider `azure-openai-responses` became `azure`; ChatGPT login fails on a busy callback port instead of falling back to paste. Not re-run: model data counts and the 03-1 line numbers beyond the edited paragraph.
- Updated [[pi]] and [[stealable-pattern-stored-credential-owns-provider]].

## [2026-10-09] ingest | jev-ultrafast first pass
- Analyzed `repos/jev-ultrafast` at `1231850a0bf1` with the `open-source-codebase-understanding` skill (registered via symlink `.claude/skills/open-source-codebase-understanding`). 40 tracked files, so analyzed directly without subagents.
- Ran `uv run pytest`: 31 passed (offline). Live/paid scripts and `scripts/check_guards.py` (real Chrome) not run.
- Wrote `reports/jev-ultrafast/overview.md`, `next.md`, archify diagrams `structure` (architecture) and `tick-flow` (sequence), both showcase-validated and visual-checked; metadata in `artifacts/jev-ultrafast/repo-metadata.txt`.
- Added [[jev-ultrafast]]; updated `wiki/index.md` to 57 pages.

## [2026-10-14] ingest | e2e first pass
- Cloned `repos/e2e` (shallow, depth 50) at `dbdec7088693`; worktree clean. Read-only analysis: no install, build, test, or model call.
- Wrote `reports/e2e/overview.md`, `next.md`, archify diagrams `structure` (architecture) and `flow` (sequence), both showcase-validated and visual-checked; metadata in `artifacts/e2e/repo-metadata.txt`.
- Added [[e2e]]; updated `wiki/index.md` to 58 pages.

## [2026-10-14] create | rea
- First-pass analysis of morluto/rea @ 60c0880: reports/rea (overview, next, 2 archify diagrams), wiki/projects/rea.md.

## [2026-10-14] update | pi agent layering
- Added `reports/pi/agent/06-layering.md` (agent vs coding-agent relationship, why the layers are split; reasons marked `추론`). Added a summary bullet to [[pi]]. Rewrote `reports/pi/agent/00~05` with the humanizer skill (prose only, no fact changes).

## [2026-10-15] update | pi tool-change cache run
- Ran `artifacts/pi/agent-demos/tool-change-demo.ts` against both `3874b3e98` and `28dcce2ba` (git archive extracts in scratchpad, SDK stubbed, no network): real `Agent` + real `anthropic-messages.ts` request builder. Resolved the 03-1 vs checkout discrepancy (different commits, no contradiction). Updated `reports/pi/agent/00,02,05`, `reports/pi/ai/03-1`, [[pi]].

## [2026-10-15] update | pi agent hooks
- Added `reports/pi/agent/07-hooks.md` (10 hooks: who fills, when called, extension handlers, throw policy). Linked from `00-role` §8, `01-types` §4, `06-layering` §3.3; summary bullet in [[pi]]. Corrected hook line refs (sdk.ts convertToLlm :395, streamFn :396, transformContext :412).

## [2026-10-15] update | pi agent StreamFn
- Added `reports/pi/agent/08-stream-fn.md` (StreamFn input/output, call sequence, who supplies it, relation to ai `StreamFunction`, failure contract). `01-types` §6 shortened with a link; summary bullet in [[pi]].
## [2026-10-15] ingest | cc-switch first pass (proxy and session manager)
- Read `repos/cc-switch` at `d35726e` while answering questions: proxy interception, settings.json write timing, Session Manager vs proxy, format conversion. Wrote `reports/cc-switch/overview.md`, `next.md`, `questions/q1-q4`; metadata appended to `artifacts/cc-switch/repo-metadata.txt` (earlier entry was shallow clone `bfaaba1`).
- Findings: proxy works by rewriting each CLI base URL to `127.0.0.1:15721` (not MITM); install alone does not modify `~/.claude/settings.json` (confirmed on this PC); Session Manager reads `~/.claude/projects/**/*.jsonl`, unrelated to the proxy; Anthropic<->Gemini/OpenAI conversion lives in `proxy/providers/transform*.rs` with 193 commits touching it.
- Not done: archify diagrams, restore-on-exit/startup code, `usage/logger.rs`. Added [[cc-switch]]; updated `wiki/index.md` to 58 pages.

## [2026-10-15] update | cc-switch skills/MCP management and same-name skill probe
- Read `services/skill.rs` and `mcp/`; ran the real `SkillService` in an isolated test home (`CC_SWITCH_TEST_HOME`) from a scratch copy of the repo; test source and output in `artifacts/cc-switch/skill-dup-probe/`. `repos/cc-switch` untouched.
- Result: for a same-named skill with different content in Claude and Codex, import takes the first-found (Claude) as SSOT and a later `resync_all_apps` replaces the Codex folder, dropping its `agents/openai.yaml`. Wrote `reports/cc-switch/questions/q5-skills-mcp-management.md`; updated overview, next, [[cc-switch]].

## [2026-10-15] update | cc-switch MCP per-app conversion documented
- Read `mcp/*.rs`, `services/mcp.rs`, `claude_plugin.rs`. Wrote `reports/cc-switch/questions/q6-mcp-per-app-conversion.md` (code reading only, not executed); added skill sync problem summary to q5; updated overview, next, [[cc-switch]].

## [2026-10-15] ingest | skills-manager first pass
- Cloned `repos/skills-manager` at `e6dcedf` (clean, v1.42.0). Read README, layout, `sync_engine.rs`, `scenario_service.rs`, `tool_adapters.rs`, `migrations.rs`; traced one path (`sync_skill_to_tool`). No tests or app run.
- Wrote `reports/skills-manager/overview.md`, `next.md`, archify diagrams `structure` and `deploy-flow` (automated gates passed, not visually reviewed); metadata in `artifacts/skills-manager/repo-metadata.txt`.
- Added [[skills-manager]]; updated `wiki/index.md` to 59 pages.

## [2026-10-15] update | skills-manager same-name conflict compared with cc-switch
- Read `sync_engine.rs`, `scenario_service.rs`, `scanner.rs`, `installer.rs`, `commands/{scan,projects,agent_workspace}.rs` at `e6dcedf`; wrote `reports/skills-manager/questions/q1-same-name-conflict-and-overwrite.md` (code reading only). Linked from overview/next; updated [[skills-manager]].
- Note: while writing, I overwrote `artifacts/skills-manager/repo-metadata.txt` (just created by another session with the same SHA); content rewritten with the same fields.

## [2026-10-15] ingest | teamai-cli initial setup
- Cloned `repos/teamai-cli` at `7ba8bcc` (clean, v0.22.0). Read README, product-overview, `package.json`, `src/index.ts` command list, `ResourceType`, `hook-dispatch`. No run/tests/diagrams.
- Wrote `reports/teamai-cli/overview.md` (feature map by 3 layers) and `next.md`; metadata in `artifacts/teamai-cli/repo-metadata.txt`. Wiki project page not yet written.

## [2026-10-15] ingest | codeburn re-baseline first pass
- Fast-forwarded `repos/codeburn` `f1bf7a1` → `9a40cc6` (v0.9.27; tracked files clean, untracked graphify outputs only). Metadata in `artifacts/codeburn/repo-metadata.txt`.
- Mapped entry/commands, provider registry (43), session cache v10 / daily cache v75, and the `codeburn report` path (code reading via subagent + spot-checks; no run/tests).
- Wrote `reports/codeburn/overview.md` (with old-vs-new baseline diff table), `next.md`, archify diagrams `structure` and `report-flow` (deliver + visual-check passed; screenshots glanced once).
- Added a re-baseline warning to [[codeburn]]; concept notes not yet re-verified.

## [2026-10-15] update | codeburn wiki rebuilt on 9a40cc6
- Rewrote [[codeburn]] and all 10 `codeburn-*` concept notes from scratch against `9a40cc6` (old `f1bf7a1`/DeepWiki-based content removed; code reading only, no run). Notable drift: providers 19+9 → 32+11; session cache → `session-cache.v10/` per-provider UTC-day pieces; daily cache v75; optimize 21 finding ids with `--apply`/`act undo`; 12 plan presets; cost repriced on read except `REPORTED_COST_PROVIDERS`/`costFromBilling`.
- Added a "주요 기능" (features by group, with evidence level) section to `reports/codeburn/overview.md`; corrected cache/cost wording in overview/next.


## [2026-10-16] schema | capability spec layer added
- Added `wiki/capabilities/` and `type: capability` to [[SCHEMA]] (directory layout, Layer 2 description with stealable-pattern/capability/comparison distinction, capability frontmatter fields `capability`/`status`/`source_revisions`/`verification`, page threshold, tag `capability`).
- New templates: `templates/capability-spec-template.md` (A 재구현 계약 / B 근거와 참조 구현, [필수]/[선택] 섹션; structure agreed after review with Codex GPT-6-Astra) and `templates/capability-request-template.md` (Agent A 스펙 작성, Agent B 재구현 검증 요청문).
- Added section 8 to `OSS_ANALYSIS_WORKFLOW.md`, a capability pointer to `AGENTS.md`, and an empty `## Capabilities` section to `wiki/index.md`. No capability page written yet.

## [2026-10-16] workflow | analysis flow: diagram explanation, Q&A loop, capability trigger
- `AGENTS.md` and `OSS_ANALYSIS_WORKFLOW.md` 2장: step 3 now requires a written explanation of the diagrams in `overview.md`; removed the old steps 4 (suggest follow-up questions) and 5; Q&A is now a user-driven loop; added a trigger section for moving to capability specs (explicit request → start; feature entry/core/failure confirmed in `questions/`, or same feature analyzed in another repo → one-line proposal; declined → `next.md` 기능 스펙 후보).
- Removed the CodeWiki section from `AGENTS.md` (details remain in [[codewiki]] and `reports/CodeWiki/`).
- Updated `templates/overview-template.md` (그림 해설 section), `templates/next-template.md` (기능 스펙 후보), `templates/request-template.md` and workflow 6장 request text.

## [2026-10-16] workflow | AGENTS.md reduced to a router
- `AGENTS.md` now holds only a situation → section routing table into `OSS_ANALYSIS_WORKFLOW.md` and the template table; rules live only in the workflow doc. Moved the two items that existed only in `AGENTS.md` (evidence-backed analysis statement; repos = 1차 근거, artifacts = 참고 후보) into workflow intro and 1장.
- Fixed references to removed `AGENTS.md` sections: `templates/next-template.md` (→ workflow 2장), [[codewiki]] and `reports/CodeWiki/overview.md` (CodeWiki usage now only in `git show c0051fa:AGENTS.md`); updated AGENTS.md role in workflow 1장 tree and [[SCHEMA]].

## [2026-10-16] capability | first spec: claude-code-session-log-reading (claude-devtools)
- Re-read session discovery / JSONL parsing / fingerprint cache at `1486f20` (code reading; repo tests not run, no `node_modules`). Wrote `reports/claude-devtools/questions/q1-session-discovery-and-jsonl-parsing.md`.
- Inspected the real Claude Code 2.1.301 logs on this PC with `artifacts/claude-devtools/log-format-demos/inspect_session_log.py` (format stats only): 16 line types, `cwd` first at line index 4, 80/116 multi-line `requestId`s each carrying one block with identical usage; project dir names turn `:` `\` `.` into `-`.
- Added [[claude-code-session-log-reading]] (draft, 14 requirements, 3 changes vs original) and linked it from [[claude-devtools]], `reports/claude-devtools/overview.md`, `next.md`; added a 2026-10-16 note to [[claude-devtools-session-discovery-and-jsonl-parsing]].
- Template fixes found by this pilot: A5 source column no longer holds test paths (moved to B1); Agent B extraction command now also strips frontmatter.

## [2026-10-16] workflow | wiki reduced to index/log; everything per repo lives in reports
- Deleted `wiki/projects/` (21), `wiki/concepts/` (41), `wiki/queries/`, `wiki/raw/`; originals stay at `git show b52364d:<path>` (full list: `git ls-tree -r --name-only b52364d wiki/`). `wiki/` now holds only `README.md`, `index.md` (repo table: baseline SHA, overview, capability spec), `log.md`, `SCHEMA.md` (index/log format, capability frontmatter).
- Capability specs are now per repo: moved the spec to `reports/claude-devtools/capabilities/claude-code-session-log-reading.md`.
- `OSS_ANALYSIS_WORKFLOW.md`: new 3장 "어디에 저장하나" (artifacts / reports / wiki), 5장 "레포가 업데이트됐을 때" (no script), 8.1·8.4 AI investigates directly without waiting for user questions; `AGENTS.md` routing and templates updated to the new paths.
- Replaced "축적된 위키 지식" links in 15 `reports/*/overview.md` with `git show b52364d:` pointers; older planning notes (`initial-capture.md`, `wiki-ingestion-plan.md`, past `next.md` checkboxes) left as historical text.

## [2026-10-16] workflow | reports frontmatter: sha, created, updated, sources (+status, reimplementation)
- [[SCHEMA]] now defines one frontmatter for every `reports/<repo>/` document: `sha`, `created`, `updated` (content changed or re-checked; not for link/typo fixes), `sources` (cited original files, used to find docs to re-check after upstream changes); capabilities add `status` and `reimplementation`. Dropped `title`, `type`, `repo`, `url`, `confidence`, doc-level `verification`, `tags`, `capability`, `source_revisions`.
- Added the frontmatter to the question/overview/next/capability-spec templates and removed their duplicate SHA/date body lines; applied it to claude-devtools `q1` and the capability spec. Older reports get it when their content is next edited.
- `OSS_ANALYSIS_WORKFLOW.md` 5장 update steps now match `git diff --name-only` against `sources`; 8.4/8.5 use `reimplementation`. Deleted `scripts/wiki-lint.py`.

## [2026-10-16] workflow | wiki/ folder removed; index, log, SCHEMA, README moved to root
- `git mv wiki/{README,SCHEMA,index,log}.md .`; `wiki/` no longer exists. `README.md` rewritten as the workspace guide; `SCHEMA.md` intro and `index.md` links (`../reports/` → `reports/`) adjusted.
- Updated paths in `AGENTS.md`, `OSS_ANALYSIS_WORKFLOW.md` (intro, 1장 tree, 2장, 3장 table, 5장, 6장, 7.4, 8장), `templates/request-template.md`, `templates/capability-request-template.md`.

## [2026-10-16] workflow | AGENTS.md and OSS_ANALYSIS_WORKFLOW.md rewritten with writing-for-agents
- `OSS_ANALYSIS_WORKFLOW.md` (306 → 157 lines): procedures first (1 저장 위치, 2 새 레포 분석, 3 질문과 답변 + 기능 스펙 트리거, 4 기능 스펙, 5 레포 업데이트, 6 세션 마무리), reference after (7 근거·검증 수준, 8 설명·문서화, 9 실행 실험). Every step ends with a checkable 완료 condition (e.g. capability A extraction greps 0 source paths). Removed duplicates (old 6장 request text, 4장 question checklist, 7.7 checklist, 8.2/8.3), the stale `Workspace:` path, and rephrased prohibitions as target behaviour.
- `AGENTS.md`: three always-on rules (evidence + 검증 수준, where to write, auto-documentation) plus a situation → chapter routing table; template table dropped (lives in workflow 1장).
- `templates/request-template.md` and the Agent A part of `templates/capability-request-template.md` reduced to inputs + "follow chapter N"; anchors in `next-template.md`, `capability-request-template.md` updated.

## [2026-10-16] update | overview 템플릿에 '주요 기능' 절 추가
- `templates/overview-template.md` 2절에 주요 기능 표, `OSS_ANALYSIS_WORKFLOW.md` 2장 3단계에 반영.

## [2026-10-16] update | claude-devtools 분석 목적 확정
- `reports/claude-devtools/overview.md` 1절: 분석 목적을 '.jsonl 세션 로그 분석 방식 학습'으로 기록.

## [2026-10-16] create | searxng clone, 기준 SHA 기록
- `repos/searxng`를 `0ce72dd`에서 clone, `artifacts/searxng/repo-metadata.txt` 작성 (worktree clean). overview·index 행은 분석 목적 확인 후 작성.

## [2026-10-16] create | searxng overview 1~2절 작성
- `reports/searxng/overview.md` 1절(목적: 학습+AI 검색 도구 설계 참고), 2절(소스 구성, 주요 기능, AI 연동), `index.md` 행 추가. 3절 구조도·실행 흐름은 미작성.

## [2026-10-16] update | searxng 주요 기능 정리로 마무리
- `reports/searxng/overview.md` 1절 목적을 '주요 기능 파악'으로 축소, 2절에 봇 제한·자동완성·프라이버시 행 추가, 3절은 그리지 않음으로 표시.

## [2026-10-16] update | searxng 분석 마무리
- `reports/searxng/overview.md` 2절에 '한 번의 검색이 처리되는 방식'(engine별 URL, 사전 수집 없음, 질의 확장 없음) 추가, 5절에 next 링크.
- `reports/searxng/next.md` 작성. 분석은 주요 기능 수준에서 종료.

## [2026-10-16] create | context-mode overview 1~2절
- `artifacts/context-mode/repo-metadata.txt`, `reports/context-mode/overview.md`(목적: hook 트리거·강제 학습), `index.md` 행 추가. 3절 이후 미작성.

## [2026-10-17] query | context-mode Q1 Claude Code hook 정의 방식
- `reports/context-mode/questions/q1-claude-code-hook-definition.md` 작성, overview 4절 링크.

## [2026-10-17] query | claude-devtools Q2 attachment·system prompt
- `reports/claude-devtools/questions/q2-attachment-and-system-prompt.md` 작성, `artifacts/claude-devtools/log-format-demos/attachment_types.py`·`2026-10-17-attachment-output.txt` 추가.
- `reports/claude-devtools/capabilities/claude-code-session-log-reading.md`에 R-15(`attachment` 보존, 변경)·T-07·A2 Attachment 행·B1 행 추가, 미결정에 `prompt_snapshot` 완전성 추가. overview 4절 링크.

## [2026-10-17] create | 세션 로그 HTML 뷰어
- `artifacts/claude-devtools/session-viewer/render_session.py` 작성(R-04·R-09·R-11·R-15 적용, `--check` 자체 검사). system prompt는 첫 `prompt_snapshot`의 `cliPrefix`+`systemPrompt`+`tools`로 표시.
- 스펙 R-15 미결정·Q2 미확인을 한 세션 관찰 결과로 갱신(스냅샷 5개 모두 `systemPrompt` 동일, `cliPrefix`·`tools`는 별도 필드).

## [2026-10-17] create | claude-devtools 기능 스펙 session-picker
- `reports/claude-devtools/capabilities/claude-code-session-picker.md` 작성(draft): 저장소·worktree 묶기, 세션 쪽 나누기, 날짜 그룹·고정·숨김·정렬. 근거는 `1486f20`의 GitIdentityResolver·WorktreeGrouper·ProjectScanner.listSessionsPaginated·DateGroupedSessions·ConfigManager.
- 미결정: 노이즈 세션 수 불일치(R-05), 삭제된 worktree 미병합(R-03), `most-context`의 `contextConsumption` 출처(R-11). `overview.md` 5절·`index.md` 링크 추가.

## [2026-10-17] update | session-picker worktree 제외, 세션 목록 서버
- `reports/claude-devtools/capabilities/claude-code-session-picker.md`: R-01~R-04 채택을 `제외`로, 적용 목적에 "worktree는 무시, 프로젝트 폴더 하나 = 선택지 하나" 결정 추가.
- `artifacts/claude-devtools/session-viewer/serve.py` 작성: `~/.claude/projects`를 훑어 프로젝트 → 세션(날짜 그룹, 최근순) 목록을 보여 주고 누른 세션을 `render_session`으로 렌더링(127.0.0.1만). curl로 목록·프로젝트·세션 200, 경로 조작·없는 세션 404 확인.

## [2026-10-17] update | 세션 뷰어 가독성 개선
- `artifacts/claude-devtools/session-viewer/render_session.py`: system prompt를 로그 조각(13~16개) 대신 한 덩어리로, 도구 정의는 이름별 접기, attachment·도구 입력은 JSON 대신 `key: 값` 텍스트(여러 줄 문자열은 실제 줄바꿈)로 표시. 같은 type이 1개면 번호 접기 없이 바로 표시.

## [2026-10-17] create | agent-skills clone, overview 1~2절
- `repos/agent-skills`(`aeac41d`, 0.6.13) clone, `artifacts/agent-skills/repo-metadata.txt`, `reports/agent-skills/overview.md`, `index.md` 행. hook 3종(session-start, simplify-ignore, sdd-cache) 확인, 플러그인이 hook을 등록하지 않음. 3절 이후 미작성.

## [2026-10-17] query | agent-skills Q1 hook 설정·트리거 동작
- `reports/agent-skills/questions/q1-claude-code-hook-setup-and-trigger.md` 작성, overview 4절 링크.

## [2026-10-18] create | Scrapling clone, overview 1~2절, Q1 정적/동적 판단·봇 차단 우회
- `repos/Scrapling`(`7a68493`, 0.4.15) clone, `artifacts/Scrapling/repo-metadata.txt`, `reports/Scrapling/overview.md`, `questions/q1-static-dynamic-and-bot-evasion.md`, `index.md` 행.
- 확인: 정적/동적 자동 판단 코드 없음(사용자가 fetcher 선택). 우회는 curl_cffi TLS 지문·실제 헤더 → patchright 스텔스 브라우저 → Turnstile 위젯 좌표 클릭(최대 3회) + 프록시 로테이션. 실행 확인 없음, archify 생략.

## [2026-10-18] query | Scrapling Q2 봇 차단 대응에서 배울 점
- `reports/Scrapling/questions/q2-bot-evasion-lessons.md` 작성, overview 4절 링크. 추가로 `_page.py`·`navigation.py`·`throttle.py`·`cache.py`·`spiders/engine.py`·`docs/spiders/proxy-blocking.md`를 읽음.
- 정정: Q1의 "정적→동적 승격 권장 흐름을 문서에서 확인 못 함"은 오류. proxy-blocking.md에 차단 시 `sid`를 stealth 세션으로 바꾸는 예제가 있어 Q1 수정. 기본값(robots 미준수, autothrottle 꺼짐, 지연 0) 확인.

## [2026-10-20] ingest | hyperframes clone, overview 1~2절
- `repos/hyperframes`(`b7fa007`, 0.8.181) clone, `artifacts/hyperframes/repo-metadata.txt`, `reports/hyperframes/overview.md`, `index.md` 행.
- 확인: README·determinism·frame-adapters 문서, 패키지 구성, 렌더 경로(`frameCapture.ts` beginFrame, `streamingEncoder.ts` ffmpeg spawn), 어댑터 파일 목록, 레지스트리 블록 210·컴포넌트 238, 스킬 21개. 실행·archify 없음.

## [2026-10-20] query | hyperframes 사용 방식(스킬 vs 앱 vs CLI)
- `README.md`, `skills/hyperframes-cli/SKILL.md`, `packages/cli/src/templates/blank/index.html`을 읽고 overview 2절에 "사용 방식" 소절 추가.

## [2026-10-20] ingest | hyperframes Prompt Guide 34페이지 수집
- `artifacts/hyperframes/crawl_prompt_guide.mjs`(fetch, Playwright 불필요)로 `https://hyperframes.heygen.com/<page>.md`를 받아 `artifacts/hyperframes/prompt-guide/`에 레벨별 폴더·순번 파일로 저장(744K, `manifest.json`). 목록·순서는 `repos/hyperframes/docs/docs.json` "Prompt Guide" 그룹. 내용 분석은 아직 안 함(후보 원재료).

## [2026-10-20] ingest | hyperframes Prompt Guide 한국어 번역 34페이지
- Haiku 서브에이전트 10개(파일 2~4개씩)가 `artifacts/hyperframes/prompt-guide/`를 번역해 `official-ko/hyperframes/`에 같은 디렉터리 구조로 저장. 26개 파일에 공통인 `DocsVideo` 컴포넌트 코드(약 250줄)는 번역 대상에서 빼고 플레이스홀더로 바꿨다가 번역 후 원본 그대로 복원.
- 검증: 원문 대비 제목·코드 펜스·표 행·목록 항목·JSX 태그 수, 코드 블록 내용, URL 집합이 34개 모두 일치. 예외 1건: 묶음 0이 2개 파일의 `llms.txt` URL을 `.com`→`.ai`로 바꿔서 직접 되돌림. 줄 수는 일부 파일에서 문단 줄바꿈을 합쳐 줄었음(내용 누락 아님).
- 번역 품질(용어 일관성, 어색한 문장)은 검수하지 않음.

## [2026-10-21] ingest | ai-job-search clone, overview, archify 2개
- `repos/ai-job-search`(`e16acee`, MIT) clone, `artifacts/ai-job-search/repo-metadata.txt`, `reports/ai-job-search/overview.md`·`next.md`, `index.md` 행.
- 읽음: README, `CLAUDE.md`, `AGENTS.md`, `.claude/commands/apply.md`·`rank.md`, `job-scraper/SKILL.md`, 에이전트 3개, `tools/` 주요 파일 docstring과 핵심 함수. 실행: `posting_guard`, `make_key`, `overall_score`(`artifacts/ai-job-search/tools-demos/`). `pytest` 없어 테스트는 안 돌림.
- archify: `diagrams/structure`(architecture), `flow`(workflow, `/apply`). 9개 산출물 검사와 4개 뷰포트 `visual-check` 통과, 시각 검토는 안 함. flow는 처음 세로 넘침으로 실패해 레인 3개로 줄여 통과.

## [2026-10-21] query | ai-job-search 평가·글쓰기·면접 (Q1~Q3)
- 사용자 요청: 검색·공고 가져오기는 제외하고, 평가 방식·지원서 글쓰기·면접 진행을 자신에게 적용할 관점으로. `reports/ai-job-search/questions/q1~q3` 작성, overview 4절 링크, `next.md` 갱신.
- 읽음: `04-job-evaluation.md`, `03-writing-style.md`, `05`·`06`·`07`·`08`, `interview.md`, `apply.md` Step 2~4, `setup.md` 추론 규칙, `cover_example.tex`. 실행 없음. 레포에 실제 산출 예시는 없고 `*_example.tex`는 뼈대뿐.

## [2026-10-21] query | ai-job-search Q4~Q6: /setup, /outcome, /upskill·/expand
- 사용자 요청으로 `reports/ai-job-search/questions/q4-profile-setup.md`, `q5-outcome-calibration.md`, `q6-upskill-expand.md` 작성(설명 스킬 `explain-clearly`의 순서: 결론 한 문장, 비유와 한계, 실제 사례, 흔한 오해). overview 4절 링크와 `next.md` 갱신.
- 읽음: `setup.md` 전체, `outcome.md` 전체, `upskill/SKILL.md` 전체, `expand.md` 전체, `rank_state.py`의 `gaps` 저장(:447, :486). 실행 없음.
- 정정: 앞 세션에서 overview 4절에 Q1~Q3 링크를 넣었다고 보고했으나 치환 실패로 빠져 있어 이번에 반영. q1에 "구간 안의 숫자를 고르는 규칙 없음" 추가.

## [2026-10-22] workflow | 기능 스펙 절차 개편: 기능 지도 → 범위 승인 → 원본 동작 스펙
- Codex(gpt-6.1-sol)와 11라운드 토론, defuddle(`9db7260`)로 지도·하위 스펙 시뮬레이션(scratch, reports 미작성). 지도 일부(추출기 등록 24개, `parseAsync` 분기)는 원본과 대조.
- 바꾼 것: `OSS_ANALYSIS_WORKFLOW.md` 서두·1~6장(읽기 기본값·제외 목록, 기능 지도, 부속 서비스 포함 여부를 묻는 범위 승인 단계, 원본 동작 스펙, C-ID 코드 참조, 통합 검토, 보고 2단), 7장 검증 수준 R-ID 단위. `SCHEMA.md` `depends`·`status`·`sources`. 템플릿 capability-spec(A/B·채택 열·클린룸 제거, 1부 동작/2부 근거/적용 메모), capability-request(지도 행 지시문, 재구현 제공 범위), overview(라이선스·범위·기능 지도), request(스펙 범위), next(다음 기능). `AGENTS.md` 라우팅.
- 기존 claude-devtools 스펙 2개는 이전 형식 그대로 두고, 다음 수정 때 옮긴다.
- 스킬 `oss-repo-spec` 추가(`.agents/skills/oss-repo-spec/SKILL.md`, `.claude/skills/`에 심볼릭 링크): 위 절차를 기준 고정 → 지도 → 구조도 → 범위 승인(멈춤) → 기능별 스펙 → 통합 검토 순서로 실행.

## [2026-10-22] delete | CodeWiki, e2e, folo, jev-ultrafast, knowledge-catalog, rsshub
- Removed `repos/`, `reports/`, `artifacts/`, `deepwiki-ko/` entries of these six repos at user request, and their rows from `index.md`. Earlier log entries are kept as history.

## [2026-10-22] ingest | gpt-researcher 기능 지도와 구조도 (범위 승인 대기)
- `oss-repo-spec`으로 새 레포 분석 시작. `repos/gpt-researcher`를 `--depth 50`으로 clone(SHA `3582a68`), 작업트리 clean, `artifacts/gpt-researcher/repo-metadata.txt` 작성. 라이선스는 LICENSE(Apache 2.0)와 pyproject·setup.py(MIT) 표기가 어긋나 overview에 그대로 기록.
- 읽음: README, pyproject, `agent.py`, `skills/researcher.py`·`writer.py`·`deep_research.py`·`context_manager.py`, `actions/retriever.py`, `scraper/scraper.py`, `context/select.py`·`jev_filter.py`, `config/variables/default.py`, `llm_provider/generic/base.py`, `backend/server/*`·`chat/chat.py`·`report_type/*`, `multi_agents/agents/orchestrator.py`, `deep_agents/agent.py`, cli.py. 실행 없음, 테스트·docs·frontend 컴포넌트·evals 코드는 열지 않음.
- 쓴 것: `reports/gpt-researcher/overview.md`(기능 지도 21행·공유 계약 3개·그림 해설), `diagrams/structure.json`·`.html`(archify finalize 4게이트 통과, 시각 검토 미실시), `next.md`. `index.md`에 행 추가. 스펙 범위는 사용자 승인 전이라 기능 스펙은 쓰지 않음.

## [2026-10-22] capability | gpt-researcher 기능 스펙 9개 작성 (ready 5 / draft 4)
- 사용자 범위 승인(연구 파이프라인·소스 모드·Retriever·스크래퍼·컨텍스트 선별·보고서 작성·상세 보고서·Deep Research·MCP 연동, 벡터스토어 경로·LLM 설정 등은 제외)에 따라 서브에이전트(sonnet, effort high)로 `reports/gpt-researcher/capabilities/` 스펙 9개를 병렬로 썼다. 선행 순서대로 3개 → 5개 → 1개 파도로 나눠 시작했고, 보고서 작성 스펙은 서브에이전트가 파일 쓰기를 거부당해 사용자 확인 뒤 메인 세션이 그대로 저장했다.
- 오프라인 실행(LLM·네트워크·설치 없이 소스 줄을 대체물과 함께 실행): `artifacts/gpt-researcher/{scrapers,context-selection,deep-research,report-writing,source-modes,mcp,detailed-report}-demos/`.
- 통합 검토: 스펙 9개의 frontmatter·depends·코드 줄 범위가 존재하는지 확인했고, 스펙 사이 어긋남을 고쳤다(research-pipeline에 MCP 사전 실행 포인터, report-writing의 `get_draft_section_titles` 설명, context-selection의 detailed-report 링크, deep-research `depends`에 research-pipeline 추가). overview 지도의 9행에 스펙 링크·상태·진입점 정정(`_search` 미사용, 초기 검색, `DEEP_RESEARCH_*` 설정 키 등)과 공유 계약 URL 안전성, 대표 흐름을 반영했다.
- 남은 미결정 4건은 `next.md`에 있다. 재구현 검증은 하지 않았다.

## [2026-10-22] ingest | herdr-plugin 폴더 신설, herdr 플러그인 4개 overview (지도만)
- `herdr-plugin/`(trading/과 같은 방식: `repos/`·`artifacts/`·`reports/`, `GUIDE.md`, `repos.lock.tsv`)을 만들고 herdr-bar(`261de9b`), herdr-projects(`8258d96`), herdr-nvim(`3ca8671`), herdr-auto-title(`69d7182`)를 `--depth 50`으로 clone. 모두 clean, 라이선스 MIT. `.gitignore`에 `/herdr-plugin/repos/` 추가.
- 사용자 지시로 archify 구조도와 기능 스펙은 만들지 않고, 레포마다 `reports/<repo>/overview.md`(기능 지도·공유 계약·글로 쓴 구조 해설)만 서브에이전트(sonnet)로 병렬 작성. 읽기만 했고 빌드·실행 없음, herdr 서버 쪽 동작은 미확인으로 표시.

## [2026-10-22] ingest | gpt-researcher Q1 서브쿼리 결과 합치기
- 사용자 질문("서브쿼리를 어떻게 합치게 되는가")을 서브에이전트(sonnet, effort high)에 탐색 범위를 정해 맡겼다. 합치기(`researcher.py:385-408`), 서브쿼리 하나의 처리, URL 중복, MCP 결합, 길이 제한, 실패 처리를 읽고 가짜 검색·스크래퍼로 원본 합치기 소스를 실행했다(`artifacts/gpt-researcher/context-merge-demos/`). 메인 세션이 `_get_new_urls`, 합치기 코드, 길이 제한 Grep을 다시 확인했다.
- 쓴 것: `reports/gpt-researcher/questions/q1-subquery-context-merge.md`, `overview.md` 4절 링크. 결론은 별도 병합 로직 없음, `" "`로 이어 붙임, 중복은 URL 단위로만 제거, 합친 뒤 길이 제한 없음.
- 같은 날 스펙 에이전트 3개(Deep Research, 보고서 작성, 상세 보고서)가 "백그라운드 작업이 남았다"며 멈추지 않아 중단했다. 그 사이 `detailed-report.md` R-31 행에서 줄바꿈 표기가 실제 줄바꿈으로 바뀌어 표 행이 쪼개져 있던 것을 되돌렸고, 스펙 9개의 표를 다시 검사해 열 개수 불일치가 없음을 확인했다.

## [2026-10-22] ingest | gpt-researcher Q2 합친 뒤 과정, 프롬프트·도구 위치
- 사용자 질문(합친 뒤 전처리 여부, 최종 개수, 보고서 전까지의 과정, LLM 프롬프트와 도구 정의 위치)에 대해 `researcher.py:212-240`, `agent.py:343-413`, `prompts.py`의 프롬프트 함수 전체, `curator.py`, `mcp/research.py`, `utils/tools.py`, `backend/chat/chat.py`, `deep_agents/tools.py`를 읽고, 기존 capabilities 스펙의 해당 줄 번호(R-ID, C-ID)를 찾아 대응시켰다. 실행 없음.
- 쓴 것: `reports/gpt-researcher/questions/q2-prompts-tools-and-pre-report-flow.md`, `overview.md` 4절 링크. 프롬프트 13종 중 스펙에 정리된 것은 9종, 도구 3곳 중 스펙에 정리된 것은 MCP 1곳이다.

## [2026-10-22] ingest | prompt-eval 폴더 신설, dspy·promptfoo·prompt-optimizer clone (초기 작업)
- `prompt-eval/`(herdr-plugin/과 같은 방식)을 만들고 dspy(`3fdb93f`, main), promptfoo(`dfe2d45`, main), prompt-optimizer(`a201f47`, develop)를 `--depth 50`으로 clone. 목적은 내 스킬·프롬프트의 평가, 모델 비교, 개선에 쓸 도구 파악. `.gitignore`에 `/prompt-eval/repos/` 추가.
- 3개 모두 작업트리 clean. LICENSE 파일 확인: dspy MIT, promptfoo MIT, prompt-optimizer AGPL-3.0-only.
- `GUIDE.md`, `repos.lock.tsv`, `artifacts/<repo>/repo-metadata.txt` 작성. overview와 기능 지도는 쓰지 않음. 먼저 볼 곳(`promptfoo`의 `claude-agent-sdk.ts`와 `optimizer/`, dspy `teleprompt/`)은 디렉터리·grep 수준의 후보다.

## [2026-10-22] ingest | prompt-eval 3개 레포 overview(기능 지도·구조도), 스펙 범위 승인 대기
- oss-repo-spec 1~3단계를 레포마다 서브에이전트(sonnet 계열)에 병렬로 맡겼다. 레포 코드는 읽기만 했고 설치·빌드·실행은 없다. 레포마다 `overview.md`(기능 지도, 공유 계약, 목적 질문 Q1~Q3 초기 답, 그림 해설)와 `diagrams/structure.{json,html}`(archify deliver 검증, 로컬 Chrome visual-check 통과, 시각 검토는 스크린샷 일부만)을 썼다.
- 기능 지도 행 수: dspy 27(핵심 24/부속 3), promptfoo 27(핵심 19/부속 8), prompt-optimizer 21(핵심 12/부속 9). 모두 스펙 미작성, 범위 승인 전.
- 메인 세션이 보고 중 3건(promptfoo `skill-used` 어서션, dspy GEPA `skills` 인자, prompt-optimizer MCP 도구 이름)을 grep으로 다시 확인했다. `visual-check` 부산물은 `artifacts/prompt-optimizer/structure-visual-check/`, `artifacts/promptfoo/structure-visual-check/`에 있다.
- `index.md`에 3행 추가(임시 "클론만 한 레포" 절은 삭제), `prompt-eval/GUIDE.md` 현재 단계 갱신.

## [2026-10-22] ingest | gbrain overview(기능 지도 44행·구조도), 스펙 범위 승인 대기
- `repos/gbrain`에 clone(`63f62b2c`, master, 0.60.371.0, 작업트리 clean)하고 `artifacts/gbrain/repo-metadata.txt`를 썼다. 라이선스: 루트 MIT(Garry Tan), 하위 LICENSE 4개(company-brain MIT, skillpack-reference 자리표시자, node 벤더, postgres UNLICENSE).
- 추적 파일이 12,864개라 영역 6개(저장·쓰기 / 검색·그래프 / 메모리 / 수집·소스 / 서빙·접근 / 잡·운영·스킬)를 서브에이전트가 읽기 전용으로 조사했다. 보고는 후보로 읽고 메인 세션이 코드에서 다시 확인한 것: 엔진 기본값, 쓰기 진입점, 스키마 버전 264, 소스 해석 7단계, `IngestionDaemon` 미연결, 사이클 30단계, `remote:false` 위치, 발행 게이트 위치, scope 6종, 검색 모드 번들, `facts` DDL 위치. 보고 원문은 파일로 보존하지 않았다(대화에만 있음). 나머지 행의 세부는 서브에이전트 보고 기준이다.
- 쓴 것: `reports/gbrain/overview.md`(기능 지도 44행 — 핵심 34/부속 10, 공유 계약 4, 대조 범위·문서와 구현 차이·미탐색), `reports/gbrain/diagrams/structure.{json,html}`(archify deliver 통과, visual-check 통과, 시각 검토는 1440×900 light 한 장). 부산물은 `artifacts/gbrain/structure-visual-check/`. 스펙은 쓰지 않았다.
- `index.md`에 gbrain 행 추가. 다음: 사용자가 스펙 범위를 승인하면 `next.md`를 쓰고 4장으로 간다.

## [2026-10-22] ingest | gbrain Q1(개요·Claude 기본 메모리와의 차이)
- 질문에 답하려고 `src/core/verbs.ts` `remember` 핸들러, `src/core/facts-fence.ts`·`facts/fence-write.ts` 머리 주석, `persistence/memory-mutations.ts`의 fence 사용, `docs/architecture/system-of-record.md`, `docs/guides/memory-boundaries.md`를 읽었다. 실행은 하지 않았다.
- 쓴 것: `reports/gbrain/questions/q1-what-it-is-vs-builtin-memory.md`, `overview.md` 4절 링크. Claude Code 기본 메모리 열은 이 세션 환경을 관찰한 것이고 claude.ai 앱 메모리는 미확인이다.

## [2026-10-22] update | gbrain Q1 후속("중앙 메모리 + .md" 범위)
- `persistence/memory-mutations.ts` `planRememberTarget`(70~135줄)와 `docs/architecture/system-of-record.md`(26~36, 79~100줄)를 읽었다. 실행은 하지 않았다.
- `reports/gbrain/questions/q1-what-it-is-vs-builtin-memory.md`에 4절 추가(.md가 원본이지만 엔티티 없이 저장한 사실·쓰기 설정 꺼짐·서브에이전트 샌드박스·이력/철회 장부는 DB에만 있음), `overview.md` 4절 한 줄 갱신.

## [2026-10-22] workflow | prompt-eval 방향 결정: dspy 제외, 두 레포에서 필요한 기능만 선별
- 사용자 결정: dspy는 스펙 범위에서 제외(overview 1절 "스펙 범위", `prompt-eval/GUIDE.md`, `index.md`에 이유 기록). promptfoo와 prompt-optimizer에서 필요한 기능만 골라 스킬 평가·개선·모델 적합도 기록 환경을 만든다.
- 4단계 범위 승인용 선별안을 사용자에게 제시했다. 승인 전이라 두 레포 overview 1절 "스펙 범위"는 아직 바꾸지 않았다.

## [2026-10-22] capability | prompt-eval 기능 스펙 21개 작성(promptfoo 15, prompt-optimizer 6)
- 사용자 승인 범위(2026-10-22)대로 스펙을 서브에이전트(레포·기능별, 4개 웨이브)에 맡겨 썼다. 선행 계약부터: 공유 계약 4+1개, 기능 14+5개. 작업자는 자기 스펙 파일만 썼고 지도·index·log는 메인 세션이 고쳤다. 원본은 읽기만 했고 설치·빌드·실행·모델 호출은 없다(`실행 확인` 없음).
- 선행 스펙이 서로 지적한 정정을 다시 맡겨 반영했다: config-loading(변수 파일 오류가 단계 목록 생성 중에 남), provider-contract(`PROMPTFOO_DELAY_MS` 분기 도달 경로), eval-run(`--suggest-prompts`는 n회 호출·동시 4·대화형 선택), template-rendering(기본 템플릿 선택 R-17 확정, 이미지 템플릿은 범위 밖). 미결정이 남았던 스펙(agent-providers, script-bridges, llm-evaluation, prompt-optimize, iterate-rewrite)은 읽을 수 있는 코드를 읽어 닫았고 외부 라이브러리 동작은 확인 한계로 옮겼다.
- 결과: promptfoo ready 15 / draft 0, prompt-optimizer ready 6 / draft 0. 두 overview의 지도 상태 칸을 링크와 `ready`로 바꾸고 틀린 서술(Skill 도구 추가 조건, 약 120개 factory, 어서션 핸들러 줄 번호, generate 호출 수, 정렬 규칙, 4개 스냅샷, 구조화 비교 조건)을 고쳤다. `next.md` 2개 추가. 빈 파일 `eb-ui.md`(오타로 생긴 0바이트)를 삭제했다.
- 남은 결정: `agent-workspace`(`copy_working_dir`·`workspaceDiff`)를 별도 스펙으로 뺄지, 웹 UI를 그대로 쓸지 새로 만들지는 사용자 결정 대기. 재구현 검증(4장 6번)은 요청이 없어 하지 않았다.
## [2026-10-23] update | defuddle 재clone 및 overview.md 최초 작성 (지도만)
- `repos/defuddle`가 삭제된 상태라 `https://github.com/kepano/defuddle.git`을 현재 HEAD(`556d74e8c8fd68c49912d4b11a4ae9ec04d7b2b5`, `0.19.5-2-g556d74e`)로 새로 clone. 이전 캡처(`9db7260`, `0.18.1`) 대비 `git diff --stat`로 343개 파일 변경 확인(`bilibili`/`gmail` 추출기 추가, `src/frontmatter.ts` 신설, `AGENTS.md` 보안 규칙 신설, CI 워크플로 추가, website에 Stripe 과금·API 키·Durable Objects 추가).
- README·package.json·`src/defuddle.ts`·`src/extractor-registry.ts`·`src/node.ts`·`src/cli.ts`·`src/frontmatter.ts`·`src/utils/dom.ts`·`website/src/index.ts`·`website/src/convert.ts`·`website/wrangler.toml`을 코드로 읽고 기능 지도 10행(핵심 8 + 부속 2) 작성, archify 전체 모듈 구조도(`reports/defuddle/diagrams/structure.{json,html}`, finalize validate/deliver/check/browser-check 통과, 교차선 시각 재검토는 안 함) 1개 작성. README Options 표에 없는 `removeContentPatterns` 옵션을 코드에서 발견해 문서-구현 차이로 기록.
- 쓴 것: `reports/defuddle/overview.md`(신규), `reports/defuddle/initial-capture.md`(overview 링크 한 줄 추가), `artifacts/defuddle/repo-metadata.txt`(새 SHA로 갱신), `index.md`(defuddle을 "첫 수집만" 표에서 "분석한 레포" 표로 이동), `reports/defuddle/next.md`(신규).
- 지도 요약을 보여주고 스펙 범위를 물은 결과, 사용자가 "지도만 유지(스펙 보류)"를 선택했고 website 부속 2행(변환 API, API 키·과금)은 제외로 확정했다. 기능 스펙(4장)은 시작하지 않음, 후보는 `next.md` 3절에 기록.

## [2026-10-23] ingest | defuddle Q1 지원 사이트·defuddle.md·Cloudflare Worker·fetch 방식
- 사용자 질문(지원 사이트 목록, defuddle.md/API 키의 정체, Cloudflare Worker가 왜 나오는지, Puppeteer/Playwright 헤드리스 브라우저 사용 여부)에 답했다. `src/extractor-registry.ts` 등록 순서 전체, `website/src/index.ts`의 과금·Stripe·Durable Object 로직, `website/wrangler.toml`, `src/fetch.ts`의 `fetchPage()`, `src/utils/linkedom-compat.ts`를 코드로 확인하고 저장소 전체에서 `puppeteer|playwright|headless|chromium`을 검색해 0건임을 확인했다.
- 쓴 것: `reports/defuddle/questions/q1-supported-sites-and-website-service.md`, `overview.md` 4절 링크. 결론: 등록 24개 중 실제 "사이트"는 21개(+패턴 매칭 2개 + 범용 폴백 1개), defuddle.md/API 키는 라이브러리와 별개인 Cloudflare Worker 상용 서비스, 헤드리스 브라우저는 쓰지 않고 평범한 `fetch()` + `linkedom`(JS 미실행) 조합이다. 사용자가 세션 초반에 기능 스펙을 보류하기로 해 스펙 트리거는 다시 묻지 않음.

## [2026-10-23] ingest | defuddle Q2 YouTube 자막 가져오는 방식
- 사용자 질문("fetch로 가져온 HTML 안에 자막이 숨어있는 거냐")에 답했다. `src/extractors/youtube.ts`의 `extractAsync()`(95~106행), `parseInlineJson()`(566~602행), `fetchPlayerData()`의 InnerTube iOS/Android/Web 3단 폴백(796~888행), `fetchCaptionXml()`의 SSRF 방지 호스트 검사(649~681행), `parseTranscriptXml()`(983행~), `fetchChapters()`(890~919행)를 코드로 읽었다. 실행(실제 네트워크 요청)은 하지 않음.
- 쓴 것: `reports/defuddle/questions/q2-youtube-transcript-fetch.md`, `overview.md` 4절 링크. 결론: 처음 fetch한 HTML에는 자막 트랙 URL 목록만 들어있고, 실제 자막 텍스트는 그 URL로 별도 요청해야 받는다. defuddle은 신뢰성을 위해 YouTube 비공식 InnerTube API에도 추가로 질의한다(최대 3회 네트워크 요청 체인). 브라우저 확장 환경에서는 "자막 보기" 버튼을 실제로 클릭하는 별도 DOM 경로가 있다는 점도 구분해 기록.

## [2026-10-23] ingest | defuddle Q3 YouTube 언어 지정 방법 및 "가끔 아랍어" 버그 원인
- 사용자 질문(언어 우선순위 지정 가능 여부, CLI로 받을 때 가끔 아랍어 자막이 나오는 이유)에 답했다. `src/cli.ts`→`src/node.ts`→`pickCaptionTrack()`(`src/extractors/youtube.ts:229-250`)의 `--lang` 처리 순서, `getDefaultCaptionTrack()`/`getOriginalLanguageTrack()`의 폴백 체인을 코드로 읽고, `git log`/`git show f6ca46d`로 이 증상과 정확히 일치하는 과거 버그(GitHub #410, 자동 더빙 영상에서 기본 자막 인덱스 부재 시 알파벳순 0번째 트랙 선택)와 그 수정 커밋을 찾았다. `git tag`로 마지막 릴리스(`0.19.5`)가 수정 커밋보다 먼저임을 확인해 npm 배포 여부는 추론으로 남기고 실제 레지스트리 확인은 하지 않았다(외부 접속, 사용자 동의 필요).
- 쓴 것: `reports/defuddle/questions/q3-youtube-language-priority-and-arabic-bug.md`, `overview.md` 4절 링크. 결론: `--lang`으로 지정 가능(최우선), 미지정 시 기본 추측 실패하면 알파벳순 0번째(종종 Arabic)로 빠지는 버그가 있었고 분석 SHA(`556d74e`)에는 수정이 포함돼 있으나 npm 정식 배포 여부는 미확인.

## [2026-10-23] ingest | defuddle Q3 후속 — npm 배포 여부 실행 확인
- 사용자 요청으로 `registry.npmjs.org/defuddle` 공개 API를 curl로 받아 확인했다(외부 접속, 사용자 동의 하에 실행). `dist-tags.latest=0.19.5`, 배포 시각 `2026-10-10T15:35:10.787Z` 확인. `git log --date=iso-strict`로 태그 커밋(`e87d416`, 15:32:07Z)·버그 수정 커밋(`f6ca46d`, 17:42:13Z)·분석 HEAD(`556d74e`, 17:59:08Z)를 UTC로 대조해 수정이 npm 배포 2시간 10분 뒤에 들어갔음을 확인. `.github/workflows/release.yml`로 "태그 push = CI가 npm publish" 구조도 확인.
- 쓴 것: `reports/defuddle/questions/q3-youtube-language-priority-and-arabic-bug.md`에 "npm 배포 여부" 절 추가(미확인 → 실행 확인으로 격상), `overview.md` 4절 요약 갱신. 결론: `npx defuddle`/`npm install defuddle`는 현재도 버그 있는 `0.19.5`를 받는다. 우회책은 `--lang` 명시.

## [2026-10-24] ingest | herdr-plugin에 herdr-mobile-relay, ovis, collie overview 추가 (지도만)
- `herdr-plugin/`에 herdr-mobile-relay(`278b8c2`, AGPL-3.0-or-later), ovis(`5e44913`, MIT), collie(`c6a690d`, MIT)를 `--depth 50`으로 clone. 모두 main, clean. `repos.lock.tsv`, `artifacts/<repo>/repo-metadata.txt`, `GUIDE.md` 분석 대상 표, `index.md` 행을 갱신.
- 사용자 지시로 graphify·archify 시각화와 기능 스펙은 만들지 않고, 레포마다 `reports/<repo>/overview.md`(기능 지도·공유 계약·글로 쓴 구조 해설)만 서브에이전트(sonnet) 3개로 병렬 작성. 기능 지도 행: herdr-mobile-relay 24, ovis 32, collie 37. 읽기만 했고 빌드·실행 없음(`실행 확인` 없음), herdr 서버 쪽 동작은 미확인으로 표시.
- 메인 세션 점검: 각 레포의 LICENSE, `herdr-plugin.toml`의 actions·panes·startup·events 개수를 직접 확인해 보고와 일치함을 봤다. 줄 번호는 서브에이전트가 자체 점검했고 메인 세션은 전수 재검증하지 않았다.

## [2026-10-24] capability | gbrain 기능 스펙 7개(질문 ①~④ 범위) + 통합 검토
- 사용자 질문(마크다운 저장 위치·방식, 메모리 호출 트리거, 필요한 것만 LLM에 건네는 방법, 자동 저장 판단)에 맞춰 스펙 범위를 8행(1, 2+3 합본, 6, 11, 12, 16, 37)으로 승인받고 서브에이전트로 선행 순서(37·1 → 2+3 → 6 → 11 → 12·16)대로 작성했다. 읽기만 했고 `bun`이 없어 DB·핸들러·외부 공급자는 실행하지 못했다. 순수 함수는 `deno`로 발췌 실행해 `artifacts/gbrain/*-demos/`에 두었다.
- 쓴 것: `reports/gbrain/capabilities/{ai-gateway,engine-and-schema,page-storage-and-import,hybrid-search,memory-verbs,fact-extraction,ambient-context}.md`(모두 ready), `reports/gbrain/next.md`, `overview.md`(1절 범위·목적, 지도 상태·선행 보정, 통합 흐름·통합 검토).
- 메인 세션이 코드로 재확인해 고친 것: write-through로 파일도 쓰는 경로(1행 R-26 추론→코드 확인, 분할 저장 기본 `'on'`), 의미 캐시 비활성(`query-cache.ts:35`), `classifyAgainstCandidates` 호출자 없음, `captureGateDecision`, HTTP MCP의 `metaHook`과 push 경로의 핫 사실(11행 R-39), 마이그레이션 259개, 지도 선행 `38`→`37`. C-ID 198개의 줄 범위를 스크립트로 확인하고 1건을 고쳤다. Q1 결론을 "소스에 폴더가 있을 때 파일이 원본"으로 보정했다.

## [2026-10-24] update | skills-manager, teamai-cli 최신화와 overview 재작성 (지도만, archify 생략)
- `repos/skills-manager`를 `e6dcedf`→`7a22192`, `repos/teamai-cli`를 `7ba8bcc`→`a44493f`로 pull(작업트리 clean). 사용자 지시로 archify 구조도와 기능 스펙은 만들지 않았다. 읽기만 했고 빌드·실행·테스트는 하지 않았다.
- 읽은 것: 두 레포의 명령 등록부(skills-manager `lib.rs` `generate_handler!` 124개와 CLI clap, teamai-cli `index.ts` 명령 표), 어댑터·에이전트 목록, 진입 파일 머리와 공개 함수, `git diff <이전 SHA>..HEAD` 파일 목록. skills-manager는 배포 경로(`sync_engine.rs`, `scenario_service.rs`)를 새 SHA에서 다시 읽었다.
- 쓴 것: `reports/skills-manager/overview.md`(지도 17행 + 공유 계약 2), `reports/teamai-cli/overview.md`(지도 29행 + 공유 계약 6), 각 `next.md`, `artifacts/<repo>/repo-metadata.txt`, `index.md` SHA. 두 overview에 frontmatter를 붙이고 1절에 이전 기준 대비 변경 표를 넣었다.
- 정정: skills-manager "에이전트 54개"는 틀렸다(이전 SHA 56, 지금 58). teamai-cli "리소스 타입 7종"은 이제 14종, "에이전트 20개"는 README 표 행 수이고 코드 `KNOWN_AGENTS`는 38개. 기존 질문 문서(skills-manager Q1·Q2, teamai-cli Q1)는 인용 파일이 바뀌어 재확인 대상으로 `next.md`에 적었고 고치지 않았다.

## [2026-10-24] capability | skills-manager 외부 스킬 설치·변경 확인·diff 스펙 4개 + 통합 검토
- 사용자 질문(`my-skills`가 남의 스킬을 래핑하므로 원본 변경 여부와 변경 내용을 확인하고 싶다)에 맞춰 범위를 승인받았다: 외부 스킬 설치, 출처 메타데이터(공유 계약에서 분리), 변경 확인, 원본 diff. 나머지 지도 행은 "제외: 사용자 범위". 메인 세션이 출처 메타데이터를 쓰고, 나머지 셋은 서브에이전트 3개가 병렬로 썼다. 앱·cargo·네트워크 실행 없이 코드를 읽었고, 순수 git CLI 실행 2건만 `artifacts/skills-manager/{skill-update-check,skill-source-diff}-demos/`에 두었다.
- 쓴 것: `reports/skills-manager/capabilities/{skill-source-metadata,skill-install-external,skill-update-check,skill-source-diff}.md`(모두 ready, 재구현 검증 미실행), `overview.md`(1절 범위, 지도 행 분할·상태, 공유 계약 분리, 문서와 구현의 차이, "스펙 통합 검토"), `next.md`, `index.md` 기능 스펙 칸.
- 통합 검토에서 고친 것: 출처 메타데이터가 "변경 확인은 상태 4열만 쓴다"고 쓴 서술(정규화·`source_revision` 이동도 씀), 설치 스펙의 미결정 U-01을 메타데이터 R-11·R-18로 해소, 원본 diff의 중복 R-02를 합침, well-known 직접 설치와 미리보기 확정 경로의 값 차이 반영. C-ID `경로:줄 범위` 83쌍의 시작·끝 줄을 `git show 7a22192`로 확인했다.
- 새로 확인한 것: well-known 출처는 변경 확인·diff 대상이 아니다. 새 기기에서 처음 만들어진 git 스킬은 메타데이터 파일에 리비전이 없어 확인이 `unknown`에 머문다(코드 읽기, 실행 미확인). `install_git`(앱)과 CLI `--git`은 스킬을 열거하지 않고 폴더 하나를 한 스킬로 복사한다. 문서·주석과 구현이 다른 곳 6건은 overview 2절 "문서와 구현의 차이".

## [2026-10-24] update | herdr-plugin 모바일 원격 제어 비교·추천 문서 작성
- 사용자 요청으로 herdr-mobile-relay·ovis·collie의 폰 연결 방식(Cloudflare 터널·게이트웨이·Tailscale), 설치 난이도, 모바일 UX를 비교하고 추천(ovis, 사용 목적: 자리 비운 동안 작업 지시·진행 확인·승인 응답)을 정리했다. 각 레포의 스크린샷 5장과 relay QUICKSTART, ovis INSTALL.md, collie README 설치 절을 읽었다. 실행 없음, UX 평가는 `추론`.
- 쓴 것: `herdr-plugin/reports/mobile-remote-comparison.md`, `herdr-plugin/GUIDE.md`에 링크 절 추가.

## [2026-10-24] capability | skills-manager 갱신 적용·출처 재연결 스펙 추가 (사용자 추가 승인)
- 사용자가 "1번도 조사해줘"(갱신 적용 조사)로 범위를 넓혀 `skill-update-apply`를 서브에이전트 하나로 썼다. 읽기 위주였고, 판단 규칙(해시, 사라질 파일 목록, 승인 토큰, swap, 갱신·set-source·재가져오기 결정부)을 파이썬으로 옮겨 `artifacts/skills-manager/skill-update-apply-demos/`에서 실행했다(소스 대체 범위는 스펙 2.3). 앱·cargo·네트워크는 실행하지 않았다.
- 쓴 것: `reports/skills-manager/capabilities/skill-update-apply.md`(ready, R-42·C-28·T-26), 선행 스펙 보정(`skill-source-metadata` R-08에 relink·detach와 `update_status` 표 보정, `skill-update-check` R-29 추가), `overview.md`(범위, 지도 행, 통합 검토 5개로 갱신), `next.md`, `index.md`.
- 메인 세션이 직접 확인한 것: 앱 시작 때 `reindex_or_rebuild_metadata`가 돌고 reindex가 `content_hash`를 디스크 해시로 다시 계산한다(`app_state.rs:175-179`, `sync_metadata.rs:232-261`). C-ID 30쌍 시작·끝 줄 확인. 새로 확인한 것: 갱신은 병합이 아니라 통째 교체이며 같은 경로 파일의 로컬 수정은 경고 없이 덮인다(사라질 파일만 경고). UI 결함 후보(보류 재응답 시 대화상자가 바로 닫힘)는 추론이고 앱 실행으로 확인하지 못했다.

## [2026-10-24] ingest | teamai-cli packages·mcp 조사(q2)와 cc-switch 기존 분석 재독
- 사용자가 `my-skills`에서 스킬뿐 아니라 플러그인·MCP도 다루고 싶다고 해서 두 조사를 했다. (1) teamai-cli `packages`·`mcp` 본문을 서브에이전트 하나가 읽어 `reports/teamai-cli/questions/q2-packages-and-mcp-sync.md`를 썼다. 읽기 위주, 순수 함수 복사본을 `node`로 실행(선언 해시·엔트리 해시, 소스 대체 범위는 문서에 명시)해 `artifacts/teamai-cli/packages-mcp-demos/`에 두었다. 앱·`claude` CLI·npm·네트워크는 실행하지 않았다. (2) cc-switch는 기존 `q5-skills-mcp-management.md`, `q6-mcp-per-app-conversion.md`만 읽었고 고치지 않았다. 두 문서의 SHA `d35726e`는 현재 `repos/cc-switch`에 없어(HEAD `bfaaba1`) 재확인하지 못했다.
- 메인 세션 점검: q2의 `파일:줄` 인용 32개가 모두 `a44493f`의 파일 길이 안에 있고 무작위 5개가 설명한 함수와 맞음. 나머지 동작 주장은 재검증하지 않았다.
- 쓴 것: q2, `reports/teamai-cli/overview.md` 4절 링크, `next.md`(기능 스펙 후보 2개, 답한 질문 표시).

## [2026-10-24] review | prompt-eval 스펙 21개 구현 준비 점검
- promptfoo 15개·prompt-optimizer 6개 스펙의 frontmatter, 1.4 미결정, 적용 메모 전부와 skill-calls-metadata 1부를 읽고 구현 가능성을 판단했다(`추론`, 재구현·실행 없음). 원본 재현은 문서상 준비됨(전부 `ready`, 미결정 없음)이나 재구현 검증은 아직 없다. 내 평가 환경 구현은 사용자 결정 7개, 실행으로 닫을 사실 3개, 적용 메모에 흩어진 공통 결정 8개가 남았다.
- 쓴 것: `prompt-eval/GUIDE.md` "구현 준비 점검" 절 추가, 목적과 범위 절에 링크 문장 한 줄.

## [2026-10-25] workflow | gbrain 분석을 agent-memory/ 폴더로 이동
- `reports/gbrain`, `artifacts/gbrain`, `repos/gbrain`을 `agent-memory/{reports,artifacts,repos}/gbrain`으로 옮겼다(herdr-plugin/ 방식의 주제 폴더). 이동한 문서·산출물 안의 `reports|artifacts|repos/gbrain` 경로 문자열은 `agent-memory/…`로 고쳤고(문서 본문 경로와 데모 스크립트의 절대 경로), 상대 링크는 같은 폴더 안이라 그대로다.
- `agent-memory/GUIDE.md`, `agent-memory/repos.lock.tsv`를 새로 썼고 `.gitignore`에 `/agent-memory/repos/`를 추가했다. `index.md`의 gbrain 행을 새 경로로 고쳤다. 이전 `log.md` 항목은 고치지 않았다(당시 경로 기준).

## [2026-10-25] ingest | agentmemory overview(기능 지도 38행·구조도), 스펙 범위 승인 대기
- `agent-memory/repos/agentmemory`에 clone(`70517d2b`, main, v0.9.30-52, 작업트리 clean)하고 `agent-memory/artifacts/agentmemory/repo-metadata.txt`를 썼다. 라이선스: 루트·`packages/mcp` Apache 2.0.
- 읽은 것: README(설치·파이프라인·검색·도구·설정 절), `package.json`, `tsdown.config.ts`, `iii-config.yaml`, `src/index.ts`·`config.ts`·`state/schema.ts`·`types.ts` 색인, `registerFunction` 전수 grep, `triggers/events.ts`, `hooks/session-start.ts`·`post-tool-use.ts`·`_capture.ts`, `functions/{observe,compress,context,search,remember,…}` 진입부, `mcp/tools-registry.ts`·`standalone.ts`, `cli/connect/index.ts`, `providers/index.ts`, `viewer/server.ts`, `plugin/`·`integrations/`·`deploy/` README. 서브에이전트는 쓰지 않았고 코드를 실행하지 않았다. 테스트는 열지 않았다.
- 쓴 것: `agent-memory/reports/agentmemory/overview.md`(기능 지도 38행 — 핵심 30/부속 8, 공유 계약 6, 대조 범위·문서와 구현 차이 3건·미탐색), `diagrams/structure.{json,html}`(archify deliver·visual-check 통과, 시각 검토는 1440×900 light 한 장), `next.md`. `index.md`에 agentmemory 행 추가. 다음: 사용자가 스펙 범위를 승인하면 4장으로 간다.

## [2026-10-25] update | ovis 설치·폰 접속 가이드 작성 (macOS·Windows)
- 사용자 요청으로 ovis 플러그인 설치, 텔레메트리 끄기(`OVIS_TELEMETRY=0`, `DO_NOT_TRACK=1`을 플러그인 `env` 파일에), Tailscale로 폰 접속하는 절차를 macOS와 Windows로 나눠 정리했다. `INSTALL.md`, `docs/guide.md`, `install.ps1`, `herdr-plugin.toml`, `scripts/plugin.{ts,ps1}`, `server/telemetry.ts`를 읽었다. 실행 없음.
- 쓴 것: `herdr-plugin/reports/ovis/install-and-mobile-access.md`, `GUIDE.md`와 `mobile-remote-comparison.md`에 링크 추가. 인용 줄 번호는 다시 열어 고쳤다(`install.ps1`, `plugin.ps1`).

## [2026-10-25] ingest | ai-learning/ 신설, DeepTutor·learnharness 기능 지도와 구조도, 스펙 범위 승인 대기
- 주제 폴더 `ai-learning/`(GUIDE.md, repos.lock.tsv, repos/·artifacts/·reports/)를 만들고 `.gitignore`에 `/ai-learning/repos/`를 추가했다. 두 레포를 clone했다: DeepTutor `a31d8262`(main, v1.6.15, clean, 루트 Apache-2.0), learnharness `b277ee3e`(main, v0.3.7, clean, AGPL-3.0).
- 레포별 서브에이전트 하나씩이 README·매니페스트·진입점·호출 경로를 읽고 overview(기능 지도 DeepTutor 53행 핵심 33/부속 20/공유 계약 8, learnharness 29행 핵심 19/부속 10/공유 계약 6)와 archify 구조도(deliver·visual-check 통과, 시각 검토는 각 한두 장)를 썼다. 코드 실행·의존성 설치 없음, 테스트·CI는 열지 않았다. 메인 세션은 LICENSE, 라우트 수, 문서에만 있는 `PracticeStore`, `USER_TOGGLEABLE_TOOL_NAMES` 존재를 직접 확인했고 나머지 주장은 재검증하지 않았다.
- 쓴 것: `ai-learning/reports/{DeepTutor,learnharness}/{overview,next}.md`, `diagrams/structure.{json,html}`, `ai-learning/artifacts/*/{repo-metadata.txt,structure-visual-check/}`. 기능 스펙은 아직 없다(사용자 범위 승인 전).

## [2026-10-25] ingest | claude-video(watch) 기능 지도와 구조도, 스펙 범위 승인 대기
- `repos/claude-video`에 clone(`03ceb42`, main, 스킬 v0.3.2, 작업트리 clean)하고 `artifacts/claude-video/repo-metadata.txt`를 썼다. 라이선스: 루트 MIT(하위 LICENSE 없음).
- 읽은 것: README, AGENTS.md, SKILL.md 전문, 매니페스트 4개·hooks·`.skillignore`·CHANGELOG, `watch.py`·`config.py` 전문, 나머지 스크립트는 심볼 목록과 `download_url`·`transcribe_video`·`upload_file`·`delete_file`·`setup.py` `_status`·`main`·fps 함수·상수. 테스트·CI(tests.yml)·`dev-sync.sh`는 열지 않았다. 서브에이전트 없음, 코드 실행 없음.
- 쓴 것: `reports/claude-video/overview.md`(기능 지도 11행 — 핵심 10/부속 1, 공유 계약 4, 대조 범위·미탐색), `diagrams/structure.{json,html}`(archify deliver 9/9·visual-check 통과, 시각 검토는 1440×900 light 한 장), `artifacts/claude-video/structure-visual-check/`, `next.md`. `index.md`에 행 추가. 기능 스펙은 사용자 범위 승인 후.

## [2026-10-26] workflow | 변경 파일 점검과 handoff.md 작성, 커밋·푸시
- 사용자 요청으로 `git status`(수정 23·미추적 17개 묶음)와 `index.md`·`log.md`를 대조했다. 모든 변경에 log 항목이 있었고 `claude-video`는 다른 세션의 작업이라 파일 존재와 index·log 행만 확인했다(내용 미검증). 루트 `gbrain` 삭제 11개는 `agent-memory/`로의 이동이다.
- 쓴 것: 루트 `handoff.md`(범위 승인 대기 5곳, 변경 묶음, 주의점). 커밋 대상은 원본 clone(`repos/`류)을 제외한 전부.

## [2026-10-26] ingest | roast-room 질문 q1: 좌석 간 대화와 mesh 통신
- `repos/roast-room`에 clone(`e40f406`, main, MIT, clean)하고 `artifacts/roast-room/repo-metadata.txt`를 썼다. 기능 지도는 만들지 않았다(질문 단위 분석).
- 읽은 것: `SKILL.md`, `round-prompts.md`, `council-musk.md`, `settings.json`, `app/lib/{council,anthropic}.mjs` 전문, `watch.mjs`·`server.mjs`·`seats.mjs` 일부. 코드 실행·서브에이전트 없음.
- 쓴 것: `reports/roast-room/overview.md`(간이), `questions/q1-seat-communication.md`. `index.md`에 행 추가. 결론: mesh 없음, 의장 중심 hub-and-spoke(파일/프롬프트로 카드 전달), SSE는 UI 표시용.

## [2026-10-26] update | roast-room q1 후속: 좌석 권한·스폰 주기·json 역할
- `live-room.md` 전문과 12개 좌석 frontmatter(`tools`, `maxTurns`)를 확인해 `reports/roast-room/questions/q1-seat-communication.md`에 2.4절을 추가하고, 확인된 미확인 항목 하나를 지웠다. 코드 실행 없음.
