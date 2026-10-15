# Wiki Index

> Content catalog for the `oss-analysis` LLM Wiki.
> Read this first to find relevant pages for any query.
> Last updated: 2026-10-15 | Total pages: 61

## Projects

- [[career-ops]] — Source-verified project structure and initial setup model for the CLI-agnostic AI job-search automation workspace.
- [[cc-switch]] — Source-verified 1차 notes on the Tauri/Rust provider-switching manager for Claude Code/Codex/Gemini CLI: base-URL-rewrite proxy (not MITM), Anthropic↔Gemini/OpenAI format conversion, and log-file-based Session Manager/usage that do not need the proxy.
- [[claude-code-history-viewer]] — Tauri/React/Rust desktop and optional WebUI tool for browsing multi-provider AI coding assistant conversation history.
- [[claude-devtools]] — Source-verified 1차 core architecture and data pipeline for an Electron app that inspects Claude Code session logs.
- [[codeburn]] — Source-verified (9a40cc6, v0.9.27) map of the AI coding token/cost CLI: 43 provider log adapters → incremental parse with session/daily caches → read-time USD pricing → TUI, menubar JSON, serve, MCP; one CLI engine behind all GUI apps.
- [[codewiki]] — Source-verified overview of the dependency-graph documentation generator: graph → LLM clustering → recursive module agents, subscription (claude/codex CLI) backend, and fact-checked output reliability.
- [[deeptutor]] — Source-verified analysis of DeepTutor's intelligent learning-agent modules, prompt/context contracts, educational IRs, validation loops, and mastery engine.
- [[e2e]] — Source-verified first pass of the agentic E2E test framework: `agent.act` goals with a verified-then-replayed action cache, model fallback on divergence, and swappable executor/engine boundaries.
- [[folo]] — Source-verified client-only monorepo analysis for the multi-platform RSS reader: public SDK boundary, offline-first local SQLite, and the Electron-over-web shell pattern.
- [[codenotch]] — Source-verified notes for the macOS notch app that reads 20+ coding tools' usage limits: the five acquisition mechanisms behind the absent vendor API, convention-plus-credential account discovery, the situational polling schedule with persisted 429 back-off, and the Fidelity/ProviderStatus honesty model.
- [[deeptutor]] — Source-verified analysis of DeepTutor's intelligent learning-agent modules, prompt/context contracts, educational IRs, validation loops, and mastery engine.
- [[graft]] — Source-verified design notes for the local, regenerable markdown context graph that feeds coding agents; two-tier tree-sitter/LLM pipeline and refresh-on-query.
- [[graphify]] — Open-source knowledge graph tool overview and source-verified architecture notes.
- [[Understand-Anything]] — Source-verified plugin architecture for multi-agent code/wiki graph generation, core schema, dashboard security, and Gemini baseline drift.
- [[jev-ultrafast]] — Source-verified overview of the browser agent that chooses observed operation/target indices via one TypeSafe request, with a small LLM only for TYPE_TEXT; offline tests run.
- [[oss-analysis-workspace]] — Current workspace structure and operating model for repo analysis and wiki synthesis.
- [[pi]] — Source-verified summary of the `ai` (unified LLM API) and `agent` (agent loop, `Agent` wrapper, proxy stream) packages of the TypeScript agent toolkit, with run-verified loop behavior; coding-agent and other packages not yet analyzed.
- [[ponytail]] — Source-verified overview of the lazy-senior-dev agent skill, its ladder philosophy, safety boundaries, and thin multi-host adapter model.
- [[rea]] — First-pass map of the local MCP/CLI reverse-engineering toolkit: Evidence model, shared application layer, bring-your-own native providers (partly unverified).
- [[rsshub]] — Source-verified layered architecture of the self-hostable feed-generation server: route plugin model, request coalescing, and the 3,462-route catalog.
- [[skills-manager]] - Source-verified first-pass notes on the Tauri/Rust app that keeps AI agent skills in one central library and deploys them to 54 agents by symlink/junction/copy, with ownership-based overwrite protection (ReplacePolicy).
- [[tokscale]] — Source-verified architecture notes for the Rust CLI/core plus Next.js social platform that tracks AI coding assistant token usage.

## Concepts

- [[claude-devtools-context-token-and-session-analysis]] — Source-verified model for token metrics, chunks/conversation groups, subagents, and renderer-side context visibility.
- [[claude-devtools-electron-process-and-ipc]] — Source-verified Electron main/preload/renderer boundary, ServiceContext registry, IPC surface, and renderer state boundary.
- [[claude-devtools-session-discovery-and-jsonl-parsing]] — Source-verified `.claude/projects` discovery, encoded path handling, JSONL parsing, and session detail cache/fingerprint boundary.
- [[codeburn-codex-provider]] — Codex provider at 9a40cc6: multi-home `~/.codex` discovery (launcher/WSL), `token_usage_record` vs `token_count`, Fast/Flex tier pricing, resumable v22 cache, fork-history dedup, worker parsing.
- [[codeburn-data-ingestion-and-caching]] — Ingestion at 9a40cc6: provider discovery → fingerprint/append/full reparse (append only for Claude) → `session-cache.v10/` per-provider UTC-day pieces with envelope-last commit, cross-process locks, in-memory reuse layers.
- [[codeburn-day-aggregation-and-caching]] — Daily cache at 9a40cc6: `daily-cache.v75.json`, 365-day backfill, carried slices and settle window, forward-only watermark, per-call day attribution, live-vs-cached slice choice.
- [[codeburn-domain-terminology]] — Glossary at 9a40cc6: provider/session/turn/call entities, token and cost fields, classification terms (category, subCategory, one-shot, retry), behavioral vs accounting turns.
- [[codeburn-optimization-engine]] — `codeburn optimize` at 9a40cc6: 21 finding ids classed fix/nudge/keep with measured/estimated basis, health score and urgency, `--apply`/`--dry-run`/`--auto-revert` via `act`, per-project model recommendation.
- [[codeburn-pricing-and-currency-resolution]] — Pricing at 9a40cc6: LiteLLM cache (schema v8) → bundled snapshot fallback, forced/long-context/fast/Flex/date-dependent rates, cost recomputed on read unless reported, Frankfurter FX at display time.
- [[codeburn-provider-plugin-system]] — Provider adapters at 9a40cc6: 32 core + 11 lazy registry, `discoverSessions`/`createSessionParser` contract, `failedProviders`, Claude's dedicated scan path, reported-cost vs repriced providers.
- [[codeburn-report-status-export-commands]] — `report`/`status`/`today`/`month`/`export` at 9a40cc6: auto period, menubar-json snapshot and `--scope combined`, export CSV/JSON files with overwrite guards and route/billing filters.
- [[codeburn-subscription-plans-and-currency]] — Plans at 9a40cc6: 12 presets stored per provider, median-7-day month projection vs straight-line `budget`, display-currency budgets, Copilot AI credits; `codeburn quota` is a separate live path.
- [[codeburn-turn-classification-engine]] — `classifyTurn` at 9a40cc6: tool/keyword rules with earliest-keyword refinement, skill-based subCategory, read-only bash excluded from retry verify, classification recomputed on every cache read.
- [[deepwiki-first-baseline]] — How DeepWiki is captured as an external baseline before local graph analysis.
- [[deeptutor-mode-workflows]] — Source-verified per-mode runtime flows for DeepTutor: entrypoints, prompt/context, tools, validators, streaming, and persistence.
- [[evidence-backed-analysis]] — Verification policy for turning analyzer/report claims into trusted knowledge.
- [[graphify-agent-skill-integration]] — How graphify installs as Codex/Claude-style agent skills, how AGENTS.md query-first policy works, and why Codex hooks are currently no-op compatibility.
- [[graphify-cli-reference]] — Source-verified graphify CLI lifecycle: install, extract, update, cluster-only, query, path, explain, affected, export, hooks, and benchmark.
- [[graphify-extract-query-mechanics]] — How `extract` decides AST vs LLM work, and how `query` performs lexical seed selection plus BFS/DFS traversal without an LLM.
- [[graphify-export-and-visualization]] — When to use graph.html, SVG, D3 tree, callflow HTML, Obsidian, wiki, GraphML, Neo4j, and graph.json exports.
- [[graphify-graph-analysis]] — How graphify turns NetworkX graphs into god nodes, surprises, affected nodes, questions, diffs, and import-cycle findings.
- [[graphify-knowledge-graph-pipeline]] — Source-verified pipeline from file detection through graph report/export.
- [[graphify-llm-semantic-extraction]] — When graphify uses LLM backends, how to configure them, and which providers are supported.
- [[graphify-query-practices-for-coding]] — Source-verified practices for turning Korean/abstract coding intents into graph vocabulary queries using query/explain/path/affected.
- [[graphify-report-generation]] — How graphify formats graph analysis outputs into GRAPH_REPORT.md sections and audit guidance.
- [[llm-wiki-operating-model]] — How this wiki is structured and maintained by the agent, including the judgment accumulation layer.
- [[open-source-analysis-judgment-model]] — Shared lens for turning source-verified repo analysis into Taste Notes, reusable patterns, and comparison hooks.
- [[stealable-pattern-learning-ai-agent-modules]] — Reusable learning-AI architecture patterns extracted from DeepTutor: prompt sections, IRs, validation, evidence compression, and deterministic mastery gates.
- [[tokscale-cli-terminal-commands]] — Source-verified terminal command reference for installing/running Tokscale, report flags, client/date filters, and group-by semantics.
- [[tokscale-operational-cli-commands]] — Source-verified operational command reference for Tokscale graph/wrapped/time-metrics, pricing lookup, auth/submit, provider integrations, and headless capture.
- [[tokscale-data-flow-pipeline]] — Source-verified Tokscale local-first ETL path: client scan, parser normalization, pricing, aggregation, TUI/report output, and social submit merge.
- [[tokscale-pricing-cost-and-cache]] — Source-verified explanation of Tokscale's pricing sources, model lookup, cost calculation, disk/stale/in-memory cache layers, and current-source differences from DeepWiki.
- [[tokscale-report-generation-and-aggregation]] — Source-verified explanation of Tokscale's model/month/hour reports, graph result generation, TUI aggregation, wrapped PNG summary, and source-message cache boundary.
- [[tokscale-rust-core-processing-layer]] — Source-verified hierarchy of Tokscale's Rust core modules and the current npm wrapper/standalone-binary boundary versus stale NAPI claims.
- [[tokscale-session-parsing-and-source-cache]] — Source-verified explanation of how Tokscale discovers agent/client logs, caches parsed source messages, incrementally parses Codex JSONL, and normalizes client-specific data into `UnifiedMessage`.
- [[workspace-boundaries]] — Clear separation between `repos/`, `artifacts/`, `reports/`, and `wiki/`.
- [[pi-ai-provider-api-separation]] — Source-verified pattern for separating wire protocol (api) from service (provider) with per-model compat data, shown with 26 providers sharing one OpenAI-compatible client.
- [[stealable-pattern-async-event-stream-with-final-result]] — Reusable design of a push/for-await event stream whose `result()` never rejects, returned immediately while async setup finishes behind it.
- [[stealable-pattern-hook-injected-loop-with-throw-contract]] — Hook-injected stateless agent loop where tool failures are absorbed into error results, other hooks must not throw, and the wrapper is the safety net.
- [[pi-agent-turn-end-decision-priority]] — Seven-level priority among error/aborted, finishTurn end/continue, tool terminate, steering, and follow-up in pi's agent loop, run-verified.
- [[stealable-pattern-stored-credential-owns-provider]] — Auth resolution rule where a stored login owns the provider (no silent env fallback) and token refresh is serialized with double-checked locking.

## Comparisons

## Queries

- [[how-to-update-this-wiki]] — Practical update procedure for future repo analysis and wiki maintenance.
