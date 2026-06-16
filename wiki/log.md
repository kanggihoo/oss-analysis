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