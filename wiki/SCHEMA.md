# Wiki Schema

Created: 2026-06-09
Updated: 2026-06-11
Domain: open-source codebase analysis, repo architecture intelligence, analyzer evidence, and reusable cross-project knowledge for `/Users/kkh/Desktop/oss-analysis`.

## Purpose

This wiki is the long-term LLM-managed knowledge layer for the `oss-analysis` workspace. It is not a replacement for source checkouts, analyzer artifacts, or human-facing reports.

Current canonical workspace boundary:

```text
/Users/kkh/Desktop/oss-analysis/
├── AGENTS.md
├── OSS_ANALYSIS_WORKFLOW.md
├── scripts/
├── repos/       # local source checkouts; primary evidence
├── artifacts/   # raw analyzer/external-baseline outputs; evidence candidates
├── reports/     # human-facing repo reports; currently may be empty until new analysis
└── wiki/        # this LLM Wiki; durable synthesis and cross-links
```

## Directory layout

```text
wiki/
├── SCHEMA.md
├── index.md
├── log.md
├── README.md
├── raw/
│   ├── articles/
│   ├── papers/
│   ├── transcripts/
│   ├── assets/
│   └── workspace/
├── projects/
├── concepts/
├── comparisons/
├── queries/
└── _meta/
```

## Layer rules

### Layer 1: `raw/`

`raw/` stores immutable source captures only when a source must be preserved inside the wiki. In this workspace, repo checkouts and analyzer outputs already have canonical homes outside the wiki:

- Source code: `repos/<repo>/`
- DeepWiki/static/graphify/Understand-Anything outputs: `artifacts/<repo>/`
- Human reports: `reports/<repo>/`

Therefore, do not duplicate large repo or artifact trees into `wiki/raw/` by default. Prefer source references in frontmatter and only create raw snapshots for small web articles, pasted notes, or source documents that do not already have a stable workspace path.

### Layer 2: synthesized wiki pages

- `projects/`: repo or workspace-level durable summaries.
- `concepts/`: reusable concepts, workflows, analyzer boundaries, recurring architecture patterns.
- `comparisons/`: cross-repo or tool comparisons.
- `queries/`: durable answers that would be expensive to recreate.

### Layer 3: schema/navigation/log

- `SCHEMA.md`: this file; conventions and taxonomy.
- `index.md`: catalog of every non-raw wiki page.
- `log.md`: append-only action log.

## Conventions

- File names: lowercase, hyphenated, no spaces.
- Every non-raw wiki page starts with YAML frontmatter.
- Use `[[wikilinks]]` for internal wiki links; every non-raw page should have at least two outbound links when possible.
- Every new or updated non-raw page must be listed in `index.md`.
- Every wiki edit batch must be appended to `log.md`.
- Tags must come from the taxonomy below. Add a tag here before using it.
- Keep pages scannable. Split pages that exceed roughly 200 lines.
- Do not create pages for transient task progress; use the session transcript for that.
- DeepWiki, graphify, and Understand-Anything are second opinions, not authorities.
- Important claims must be verified against `repos/<repo>/` source files before being treated as facts.
- If a page is based on an analyzer artifact only, set `confidence: low` or `medium` and state what has not been verified.

## Frontmatter

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: project | concept | comparison | query | summary
tags: [open-source]
sources: [AGENTS.md, OSS_ANALYSIS_WORKFLOW.md]
confidence: high | medium | low
# Optional:
contested: true
contradictions: [other-page-slug]
---
```

## Source/provenance rules

Use `sources:` to list durable workspace paths or raw captures. Examples:

```yaml
sources: [AGENTS.md, OSS_ANALYSIS_WORKFLOW.md]
sources: [artifacts/graphify/deepwiki/toc.md, artifacts/graphify/deepwiki/pages-md/1-overview.md]
sources: [repos/graphify/README.md, repos/graphify/pyproject.toml]
```

Claim strength:

- `confidence: high`: verified against primary source files or workspace instructions.
- `confidence: medium`: synthesized from trusted reports/docs but not fully source-verified in the current edit.
- `confidence: low`: analyzer-only, external-baseline-only, or explicitly incomplete.

## Tag taxonomy

- `open-source`
- `workspace`
- `project`
- `architecture`
- `code-map`
- `dependency`
- `testing`
- `ci-cd`
- `cli`
- `commands`
- `security`
- `terminal`
- `license`
- `maintainer-activity`
- `agent-framework`
- `knowledge-graph`
- `graphify`
- `understand-anything`
- `deepwiki`
- `llm-wiki`
- `comparison`
- `risk`
- `onboarding`
- `inference`
- `developer-tools`
- `mcp`
- `workflow`
- `evidence`
- `judgment`
- `pattern`
- `tooling`
- `reporting`

## Page thresholds

Create or update a page when:

- A repo has been analyzed beyond a quick lookup.
- A concept appears across multiple repos or will guide future analyses.
- A comparison is likely to be reused.
- A query answer would be costly to recreate.
- A workspace convention affects future analysis quality.

Do not create pages for:

- Passing mentions.
- Temporary status updates.
- Raw analyzer dumps without synthesis.

## Judgment model and Taste Notes

The wiki also accumulates engineering judgment, not only architecture facts. Use `wiki/concepts/open-source-analysis-judgment-model.md` as the shared lens for this layer.

Project pages may include a compact `Taste Notes` section when source-verified analysis reveals reusable decisions. Default dimensions:

1. `Responsibility Boundaries`: where the project separates core logic, adapters, UI, storage, cache, command routing, and analyzer/report responsibilities.
2. `Architecture Decision Taste`: the 3-5 most instructive source-verified design decisions, written as decision / alternative / why tasteful / trade-off / evidence.
3. `Trade-offs / Risks`: visible costs of otherwise strong decisions.
4. `Stealable Patterns`: links to reusable `wiki/concepts/stealable-pattern-*.md` pages when a decision generalizes beyond one repo.
5. `Comparison Hooks`: short links or notes that can later become `wiki/comparisons/*.md` pages.

Do not create default sections for `Quality Signals`, `First Meaningful Success`, or `Prompt / Intent Review`. Inspect those only when directly relevant to the repo or user request.

## Verification policy

Primary evidence:

- `repos/<repo>/` source files.
- Manifests and lockfiles.
- CI/test files.
- Official docs in the repo.
- Actual command output.

Secondary evidence:

- `artifacts/<repo>/deepwiki/`.
- `artifacts/<repo>/graphify/`.
- `artifacts/<repo>/understand-anything/`.
- Existing report drafts.

Rules:

1. Architecture claims need actual module/file paths.
2. Runtime-flow claims need entrypoints and call/data paths.
3. Dependency/security claims need manifests, lockfiles, CI, or advisories.
4. Unverified analyzer claims must be labeled as unverified or low/medium confidence.
5. Reports and wiki pages should cite exact paths used as evidence.

## Update policy

When new information conflicts with existing content:

1. Check provenance and dates.
2. Preserve both claims when the contradiction is real.
3. Mark `contested: true` and list `contradictions:`.
4. Add the issue to `log.md` and surface it to the user.

## Standard update flow

1. Read `SCHEMA.md`, `index.md`, and recent `log.md`.
2. Search existing pages before creating new ones.
3. Read relevant `repos/`, `artifacts/`, or `reports/` sources.
4. Write/update synthesized pages.
5. Update `index.md`.
6. Append to `log.md`.
7. Verify there are no broken wikilinks or missing index entries.
