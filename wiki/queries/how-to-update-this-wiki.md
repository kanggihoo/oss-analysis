---
title: How to Update This Wiki
created: 2026-06-09
updated: 2026-06-09
type: query
tags: [llm-wiki, onboarding, workflow, reporting]
sources: [SCHEMA.md, AGENTS.md, OSS_ANALYSIS_WORKFLOW.md]
confidence: high
---

# How to Update This Wiki

Use this procedure whenever a repository analysis, comparison, or durable question should update the LLM Wiki.

## Before analysis

1. Read `wiki/SCHEMA.md`.
2. Read `wiki/index.md`.
3. Read recent `wiki/log.md`.
4. Check whether a relevant page already exists.

## During repo analysis

1. Clone or update the repo under `repos/<repo>/`.
2. Store raw analyzer and baseline output under `artifacts/<repo>/`.
3. Write human-facing conclusions under `reports/<repo>/` when a report is requested or useful.
4. Verify key claims with [[evidence-backed-analysis]].

## Wiki update decision

| Result type | Wiki destination |
|---|---|
| Durable repo summary | `wiki/projects/<repo>.md` |
| Recurring architecture/tooling concept | `wiki/concepts/<concept>.md` |
| Cross-repo or analyzer comparison | `wiki/comparisons/<topic>.md` |
| Reusable answer to a costly query | `wiki/queries/<query>.md` |

## After editing

1. Ensure every new page has frontmatter.
2. Ensure tags are in `SCHEMA.md`.
3. Ensure every page has useful wikilinks.
4. Update `wiki/index.md`.
5. Append to `wiki/log.md`.

## Boundary reminder

The wiki is only the durable synthesis layer. Raw source code remains in `repos/`, analyzer baselines remain in `artifacts/`, and human-facing reports remain in `reports/`. See [[workspace-boundaries]] and [[llm-wiki-operating-model]].
