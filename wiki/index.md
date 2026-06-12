# Wiki Index

> Content catalog for the `oss-analysis` LLM Wiki.
> Read this first to find relevant pages for any query.
> Last updated: 2026-06-11 | Total pages: 36

## Projects

- [[claude-code-history-viewer]] — Tauri/React/Rust desktop and optional WebUI tool for browsing multi-provider AI coding assistant conversation history.
- [[codeburn]] — Source-verified architecture notes for the AI coding token/cost observability pipeline from provider logs to TUI, menubar JSON, and MCP surfaces.
- [[graphify]] — Open-source knowledge graph tool overview and source-verified architecture notes.
- [[oss-analysis-workspace]] — Current workspace structure and operating model for repo analysis and wiki synthesis.
- [[tokscale]] — Source-verified architecture notes for the Rust CLI/core plus Next.js social platform that tracks AI coding assistant token usage.

## Concepts

- [[codeburn-codex-provider]] — Source-verified Codex provider deep dive: `~/.codex` rollout discovery, large JSONL streaming, token/cost normalization, fork deduplication, Codex-specific result cache, and test-backed drift from DeepWiki.
- [[codeburn-data-ingestion-and-caching]] — Source-verified explanation of how CodeBurn discovers provider sources, reads JSONL/files by size strategy, parses turns, and caches compact session/daily data.
- [[codeburn-day-aggregation-and-caching]] — Source-verified explanation of how CodeBurn folds parsed sessions into daily entries and maintains `daily-cache.json` for period queries.
- [[codeburn-domain-terminology]] — Source-verified glossary of CodeBurn domain entities, token/cost metrics, classification metrics, waste patterns, and plan/budget terms.
- [[codeburn-optimization-engine]] — Source-verified explanation of `codeburn optimize`: Claude JSONL scanning, detector pipeline, MCP schema-tax analysis, health scoring, trend/urgency sorting, and context-budget utility boundaries.
- [[codeburn-pricing-and-currency-resolution]] — Source-verified path for model price and FX data: bundled LiteLLM/models.dev/OpenRouter snapshots, runtime LiteLLM cache, Frankfurter exchange-rate cache, and USD-to-display conversion.
- [[codeburn-provider-plugin-system]] — Source-verified explanation of CodeBurn's provider adapter interface, core vs lazy registry, discovery/filter flow, parser/cache integration, SQLite provider family, and provider-specific normalization drift from DeepWiki.
- [[codeburn-report-status-export-commands]] — Source-verified command-flow notes for CodeBurn `report`, `status`, `today`, `month`, and `export`: JSON report shape, menubar JSON aggregation, CSV/JSON export files, currency rounding, and overwrite/CSV-injection guards.
- [[codeburn-subscription-plans-and-currency]] — Source-verified explanation of subscription plan USD budgets, provider-scoped plan usage, median-daily projection, FX conversion, rounding boundaries, and proxy-covered cost attribution.
- [[codeburn-turn-classification-engine]] — Source-verified explanation of CodeBurn's deterministic turn classifier: tool pattern matching, keyword refinement, bash command breakdown, retry detection, and category aggregation.
- [[deepwiki-first-baseline]] — How DeepWiki is captured as an external baseline before local graph analysis.
- [[evidence-backed-analysis]] — Verification policy for turning analyzer/report claims into trusted knowledge.
- [[graphify-agent-skill-integration]] — How graphify installs as Codex/Claude-style agent skills, how AGENTS.md query-first policy works, and why Codex hooks are currently no-op compatibility.
- [[graphify-cli-reference]] — Source-verified graphify CLI lifecycle: install, extract, update, cluster-only, query, path, explain, affected, export, hooks, and benchmark.
- [[graphify-extract-query-mechanics]] — How `extract` decides AST vs LLM work, and how `query` performs lexical seed selection plus BFS/DFS traversal without an LLM.
- [[graphify-export-and-visualization]] — When to use graph.html, SVG, D3 tree, callflow HTML, Obsidian, wiki, GraphML, Neo4j, and graph.json exports.
- [[graphify-graph-analysis]] — How graphify turns NetworkX graphs into god nodes, surprises, affected nodes, questions, diffs, and import-cycle findings.
- [[graphify-knowledge-graph-pipeline]] — Source-verified pipeline from file detection through graph report/export.
- [[graphify-llm-semantic-extraction]] — When graphify uses LLM backends, how to configure them, and which providers are supported.
- [[graphify-report-generation]] — How graphify formats graph analysis outputs into GRAPH_REPORT.md sections and audit guidance.
- [[llm-wiki-operating-model]] — How this wiki is structured and maintained by the agent, including the judgment accumulation layer.
- [[open-source-analysis-judgment-model]] — Shared lens for turning source-verified repo analysis into Taste Notes, reusable patterns, and comparison hooks.
- [[tokscale-cli-terminal-commands]] — Source-verified terminal command reference for installing/running Tokscale, report flags, client/date filters, and group-by semantics.
- [[tokscale-operational-cli-commands]] — Source-verified operational command reference for Tokscale graph/wrapped/time-metrics, pricing lookup, auth/submit, provider integrations, and headless capture.
- [[tokscale-data-flow-pipeline]] — Source-verified Tokscale local-first ETL path: client scan, parser normalization, pricing, aggregation, TUI/report output, and social submit merge.
- [[tokscale-pricing-cost-and-cache]] — Source-verified explanation of Tokscale's pricing sources, model lookup, cost calculation, disk/stale/in-memory cache layers, and current-source differences from DeepWiki.
- [[tokscale-report-generation-and-aggregation]] — Source-verified explanation of Tokscale's model/month/hour reports, graph result generation, TUI aggregation, wrapped PNG summary, and source-message cache boundary.
- [[tokscale-rust-core-processing-layer]] — Source-verified hierarchy of Tokscale's Rust core modules and the current npm wrapper/standalone-binary boundary versus stale NAPI claims.
- [[tokscale-session-parsing-and-source-cache]] — Source-verified explanation of how Tokscale discovers agent/client logs, caches parsed source messages, incrementally parses Codex JSONL, and normalizes client-specific data into `UnifiedMessage`.
- [[workspace-boundaries]] — Clear separation between `repos/`, `artifacts/`, `reports/`, and `wiki/`.

## Comparisons

## Queries

- [[how-to-update-this-wiki]] — Practical update procedure for future repo analysis and wiki maintenance.
