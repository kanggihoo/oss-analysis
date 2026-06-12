---
title: Open Source Analysis Judgment Model
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [open-source, workflow, architecture, evidence, judgment]
sources: [SCHEMA.md, AGENTS.md, OSS_ANALYSIS_WORKFLOW.md, wiki/concepts/llm-wiki-operating-model.md]
confidence: high
---

# Open Source Analysis Judgment Model

This page defines the shared judgment model for turning open-source repository analysis into accumulated engineering taste. The model extends [[llm-wiki-operating-model]]: the wiki should not only preserve how a repository works, but also capture which source-verified decisions are worth learning from.

The model is a common evaluation lens, not a scorecard. Project-specific judgments belong in `wiki/projects/<repo>.md` under `Taste Notes`; reusable design patterns belong in `wiki/concepts/stealable-pattern-*.md`; cross-repo synthesis belongs in `wiki/comparisons/*.md`.

## Purpose

For each analyzed repository, first establish factual behavior through [[evidence-backed-analysis]] and source paths under `repos/<repo>/`. Then extract a small number of durable judgments that can improve future design decisions.

A good judgment note should answer:

- What decision did the project make?
- What plausible alternative did it avoid?
- Why is the chosen boundary or structure tasteful in this context?
- What trade-off or risk comes with that decision?
- Which exact source paths support the claim?

## Judgment dimensions

### 1. Responsibility Boundary

Ask where the project places responsibility boundaries. Prefer source-verified observations over inferred non-goals.

Look for boundaries such as:

- Core domain logic versus CLI, TUI, Web UI, or integration wrappers.
- Provider-specific parsing versus shared aggregation or reporting.
- Config, cache, storage, and network-fetch boundaries.
- Command routing versus business logic.
- Analyzer artifacts versus final human-facing reports, as described in [[workspace-boundaries]].

Project-page output should be short:

```md
### Responsibility Boundaries

- Core parsing lives in `...`, while CLI routing stays in `...`.
- Provider-specific behavior is isolated behind `...` and normalized before aggregation.
```

### 2. Architecture Decision Taste

Capture only the 3-5 most instructive design decisions per repository. Do not try to evaluate every module in a large codebase.

Use this shape when a decision is worth preserving:

```md
#### Decision: <short name>

- Decision:
- Alternative:
- Why it is tasteful:
- Trade-off:
- Evidence:
```

The goal is not to praise famous projects. The goal is to preserve the internal evaluation function: why this structure is better in this context, and when the same pattern might fail elsewhere.

### 3. Trade-offs / Risks

Every strong design choice usually buys one property by spending another. Record the cost when it is visible from source, docs, tests, or verified behavior.

Useful forms:

- The boundary improves extension, but central metadata may become a bottleneck.
- The local cache improves speed, but correctness depends on invalidation or fingerprinting.
- A thin CLI keeps commands simple, but advanced workflows may increase flag complexity over time.

### 4. Stealable Patterns

When a decision is reusable beyond one repository, link or create a focused concept page named `stealable-pattern-<pattern>.md`.

A stealable pattern page should include:

- Pattern definition.
- Why it is useful.
- Where it appears.
- Failure modes.
- Evidence links back to project pages and source paths.

Project pages should only list the relevant pattern links:

```md
### Stealable Patterns

- `stealable-pattern-provider-registry.md`
- `stealable-pattern-core-ui-separation.md`
```

### 5. Comparison Hooks

When a repository resembles another analyzed project, leave a short hook for future comparison instead of forcing a comparison immediately.

```md
### Comparison Hooks

- Compare with [[tokscale]] on local AI usage log parsing and pricing-cache boundaries.
- Compare with [[graphify]] on analyzer artifact generation and CLI command design.
```

When enough hooks accumulate, promote them into a `wiki/comparisons/*.md` page.

## Default project-page section

Use this compact section in project pages after the source-verified architecture or flow notes:

```md
## Taste Notes

### Responsibility Boundaries

- ...

### Architecture Decision Taste

#### Decision: ...

- Decision:
- Alternative:
- Why it is tasteful:
- Trade-off:
- Evidence:

### Trade-offs / Risks

- ...

### Stealable Patterns

- ...

### Comparison Hooks

- ...
```

## Explicitly not default sections

The following lenses may still be useful during analysis, but they are not default wiki sections:

- Quality Signals: omit unless a repository's verification strategy is itself central to the analysis.
- First Meaningful Success: omit by default; most mature README-driven projects already cover this well enough for the wiki's purpose.
- Prompt / Intent Review or Agent-Readiness: inspect `AGENTS.md`, `SKILL.md`, `CLAUDE.md`, or similar files when relevant, but do not create a standard wiki section for every repository.
- Taste Rubric: do not maintain a separate rubric file; this judgment model is the shared lens.

## Update path

The relationship between pages is:

```text
[[open-source-analysis-judgment-model]]
    -> defines the shared lens
wiki/projects/<repo>.md
    -> stores project-specific Taste Notes
wiki/concepts/stealable-pattern-*.md
    -> stores reusable design patterns
wiki/comparisons/*.md
    -> stores cross-project synthesis
```

This keeps the wiki lightweight while making repo analysis compound into judgment, not just stored facts.
