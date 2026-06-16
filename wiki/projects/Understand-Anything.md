---
title: Understand-Anything
created: 2026-06-15
updated: 2026-06-15
type: project
tags: [open-source, project, architecture, knowledge-graph, understand-anything, developer-tools, security, workflow]
sources:
  - repos/Understand-Anything/package.json
  - repos/Understand-Anything/pnpm-workspace.yaml
  - repos/Understand-Anything/understand-anything-plugin/skills/understand/SKILL.md
  - repos/Understand-Anything/understand-anything-plugin/skills/understand-domain/SKILL.md
  - repos/Understand-Anything/understand-anything-plugin/skills/understand-knowledge/SKILL.md
  - repos/Understand-Anything/understand-anything-plugin/packages/core/src/types.ts
  - repos/Understand-Anything/understand-anything-plugin/packages/core/src/schema.ts
  - repos/Understand-Anything/understand-anything-plugin/packages/core/src/persistence/index.ts
  - repos/Understand-Anything/understand-anything-plugin/packages/dashboard/vite.config.ts
  - repos/Understand-Anything/understand-anything-plugin/packages/dashboard/src/App.tsx
  - reports/Understand-Anything/overview.md
  - reports/Understand-Anything/gemini-baseline-comparison.md
confidence: high
---

# Understand-Anything

Understand-Anything is a multi-platform AI coding-agent plugin that turns codebases, domain flows, or Karpathy-pattern wikis into `.understand-anything/knowledge-graph.json` and a local interactive dashboard. This page is source-verified at commit `7a3b7511b26a1816be3b6cc5683b34779e0abce9`; Gemini artifacts were used only as a baseline, following [[evidence-backed-analysis]] and [[workspace-boundaries]].

## Current package boundary

The repository is a pnpm workspace, not a single CLI binary. Root `package.json` orchestrates `build`, `test`, `dev:dashboard`, and `lint`; `pnpm-workspace.yaml` includes `understand-anything-plugin/packages/*`, `understand-anything-plugin`, and `homepage`.

The production analysis plugin is under `understand-anything-plugin/`:

- `skills/`: slash skill definitions such as `/understand`, `/understand-domain`, `/understand-knowledge`, `/understand-dashboard`, `/understand-chat`, `/understand-diff`, `/understand-explain`, `/understand-onboard`.
- `agents/`: LLM agent prompt definitions: project scanner, file analyzer, assemble reviewer, architecture analyzer, tour builder, graph reviewer, domain analyzer, article analyzer.
- `packages/core/`: shared graph schema, validation, persistence, Tree-sitter/plugin registry, language configs, search, graph utilities.
- `packages/dashboard/`: Vite/React dashboard with ReactFlow, ELK, D3-force utilities, Zustand store, theme/i18n, and local security middleware.
- `hooks/`: Claude-style `SessionStart` and `PostToolUse` hook config that routes stale/commit-triggered auto-update work to `auto-update-prompt.md`.

## Source-verified operation model

`/understand` is a hybrid deterministic-script + LLM-agent pipeline. Deterministic scripts own file enumeration, `.understandignore`, language/category detection, import map extraction, semantic batching, structural extraction, batch graph merge/normalization, and fingerprint baselines. LLM agents own semantic file summaries, assemble review, architecture layer assignment, tour building, and optional full graph review.

Important current-source corrections:

1. `graph-reviewer` is not always the final gate. Default validation is an inline deterministic script; the LLM graph reviewer is used for `--review`.
2. Slash-command routing is represented by `understand-anything-plugin/skills/*/SKILL.md` and platform plugin manifests, not by `.claude/commands/` files in this checkout.
3. The pipeline has explicit Phase 0.5 `.understandignore` review, Phase 1.5 Louvain/neighborMap batching, fingerprint generation before `meta.json`, and cleanup that preserves `scan-result.json`.
4. Core `NodeType` count is 21 and `EdgeType` count is 35 in current source. The older “16 node types” baseline is stale.
5. Current `DomainMeta` is `entities`, `businessRules`, `crossDomainInteractions`, `entryPoint`, `entryType`; the baseline interface with `description/flowType/order/inputs/outputs/triggers/involvedActors` is stale for this checkout.

## Dashboard and security boundary

The dashboard is a local Vite server bound to `127.0.0.1`. Its middleware protects `/knowledge-graph.json`, `/domain-graph.json`, `/diff-overlay.json`, `/meta.json`, `/config.json`, and `/file-content.json` with a query token derived from `UNDERSTAND_ACCESS_TOKEN` or a random 16-byte hex token.

The source file viewer is gated by more than the token. `/file-content.json` rejects missing paths, null bytes, requested absolute paths, `..` traversal, files outside the project root, files not present in graph node `filePath` allowlist, non-files, files over 1MB, and binary buffers. Graph JSON serving also sanitizes absolute `filePath` values before returning them to the browser.

## Taste Notes

### Responsibility Boundaries

- Skills orchestrate agent-facing workflows and define slash-command contracts.
- Deterministic scripts do high-volume mechanical work so LLM agents spend tokens on semantic judgment.
- Core owns schema, normalization, persistence, parser/plugin contracts, and browser-safe subpath exports.
- Dashboard owns local visualization and source-preview serving, with access-token and path allowlist enforcement.
- Hooks only trigger prompt-driven update behavior; they do not directly mutate graphs by themselves.

### Architecture Decision Taste

1. **Deterministic-first scanning** / alternative: ask an LLM to enumerate files / why tasteful: repeatable, cheaper, easier to test / trade-off: more script surface to maintain / evidence: `scan-project.mjs`, `extract-import-map.mjs`, root tests.
2. **Graph-derived file allowlist** / alternative: token-only local file API / why tasteful: limits source preview to analyzed files / trade-off: stale or incomplete graphs block legitimate previews / evidence: dashboard `vite.config.ts`.
3. **Core subpath exports** / alternative: import core main entry everywhere / why tasteful: dashboard can import `schema/search/types` without pulling Node persistence modules / trade-off: exported API maintenance burden / evidence: `packages/core/package.json`.
4. **Default deterministic validation plus opt-in LLM review** / alternative: always run graph-reviewer / why tasteful: saves tokens and gives a fast quality gate / trade-off: semantic issues may need `--review` or human inspection / evidence: `/understand` Phase 6.
5. **Fingerprint before meta write** / alternative: write meta first and update fingerprints later / why tasteful: avoids permanent false FULL_UPDATE escalation / trade-off: save phase can abort late / evidence: `/understand` Phase 7 comments.

### Trade-offs / Risks

- The pipeline is powerful but prompt/skill heavy; platform-specific plugin installation paths and symlink behavior are part of the runtime contract.
- Dashboard build succeeds but produces a large ELK chunk; current source mitigates with manual chunks but still emits a Vite chunk warning.
- Domain/knowledge graph paths share the same schema, which is convenient but means stale baseline docs can easily confuse type details unless checked against `types.ts`.

### Stealable Patterns

- Use analyzer outputs as hypotheses, then verify against primary source as in [[evidence-backed-analysis]].
- Split mechanical graph construction from semantic LLM synthesis, similar in spirit to [[graphify-knowledge-graph-pipeline]] but implemented as agent skills and dashboard-first outputs.
- Protect local source preview endpoints with both session token and graph-derived path allowlist.

### Comparison Hooks

- Compare with [[graphify]] on CLI-first local graph extraction versus plugin/agent-first graph generation.
- Compare with [[deepwiki-first-baseline]] for external baseline capture versus local source-verified graph creation.

## Verification results

After installing dependencies with `pnpm install --frozen-lockfile`, the following commands succeeded in the local checkout:

- `pnpm --filter @understand-anything/core build`
- `pnpm --filter @understand-anything/core test` — 33 test files / 670 tests passed
- `pnpm --filter @understand-anything/skill build`
- `pnpm --filter @understand-anything/dashboard build` — success with large chunk warning for `elk`
- `pnpm test` — 16 test files / 200 tests passed
- `pnpm lint`
