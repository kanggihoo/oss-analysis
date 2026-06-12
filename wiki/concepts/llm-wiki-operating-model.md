---
title: LLM Wiki Operating Model
created: 2026-06-09
updated: 2026-06-11
type: concept
tags: [llm-wiki, knowledge-graph, workflow, evidence]
sources: [SCHEMA.md, AGENTS.md, OSS_ANALYSIS_WORKFLOW.md]
confidence: high
---

# LLM Wiki Operating Model

The LLM Wiki is the durable synthesis layer for the `oss-analysis` workspace. It is managed by the agent using interlinked Markdown pages and frontmatter.

## What the wiki stores

- Project-level durable summaries in `projects/`.
- Reusable analysis concepts in `concepts/`.
- Cross-repo/tool comparisons in `comparisons/`.
- High-value answers in `queries/`.

## What the wiki should not store

- Full repository copies; those belong in `repos/`.
- Raw analyzer dumps; those belong in `artifacts/`.
- Human-facing report suites; those belong in `reports/`.
- Temporary session progress; that stays in the conversation/session log.

See [[workspace-boundaries]] for the directory-level separation.

## Session startup routine

Before editing the wiki:

1. Read `wiki/SCHEMA.md`.
2. Read `wiki/index.md`.
3. Read recent `wiki/log.md` entries.
4. Search existing wiki pages before creating a new one.

## Update routine

After repo analysis or a durable query:

1. Identify whether the result belongs in `projects/`, `concepts/`, `comparisons/`, or `queries/`.
2. Cite exact source paths in frontmatter.
3. Link the page to at least two relevant wiki pages where possible.
4. Update `index.md`.
5. Append an entry to `log.md`.
6. Apply [[evidence-backed-analysis]] before treating claims as high confidence.

## Judgment accumulation

The wiki now treats open-source analysis as judgment accumulation, not only fact storage. Use [[open-source-analysis-judgment-model]] as the shared lens.

For project pages, add `Taste Notes` when a repository reveals source-verified decisions worth learning from:

- `Responsibility Boundaries`: where the project draws core/plugin/UI/cache/reporting boundaries.
- `Architecture Decision Taste`: 3-5 instructive decisions, each grounded in exact source paths.
- `Trade-offs / Risks`: the cost side of otherwise strong decisions.
- `Stealable Patterns`: links to reusable concept pages when a decision generalizes.
- `Comparison Hooks`: seeds for future `comparisons/` pages.

Do not add default wiki sections for `Quality Signals`, `First Meaningful Success`, or `Prompt / Intent Review`; use those only when a user asks or a repository makes them central.

## Relationship to analyzers

DeepWiki, graphify, and Understand-Anything can accelerate orientation, but their outputs are only evidence candidates. [[deepwiki-first-baseline]] describes the preferred external-baseline capture order.
