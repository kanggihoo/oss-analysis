---
title: Evidence-backed Analysis
created: 2026-06-09
updated: 2026-06-09
type: concept
tags: [evidence, open-source, architecture, workflow, deepwiki, graphify, understand-anything]
sources: [AGENTS.md, OSS_ANALYSIS_WORKFLOW.md]
confidence: high
---

# Evidence-backed Analysis

Evidence-backed analysis means that important conclusions are verified against primary source material before they are written as facts in reports or the wiki.

## Evidence levels

| Level | Examples | Use |
|---|---|---|
| Primary | `repos/<repo>/` source, manifests, lockfiles, CI files, official docs, command output | Can support high-confidence claims. |
| Secondary | DeepWiki pages, graphify reports, Understand-Anything dashboards, generated summaries | Useful as hypotheses or baselines. |
| Tertiary | Memory, recollection, previous unverified summaries | Never enough for final factual claims. |

## Verification rules

- Architecture claim: verify actual files/modules exist in `repos/<repo>/`.
- Runtime-flow claim: identify entrypoint and call/data flow.
- Dependency/security claim: inspect manifests, lockfiles, CI, or advisories.
- Test/CI claim: inspect test directories and `.github/workflows/` or equivalent.
- Project-health claim: inspect GitHub metadata, releases, issues/PRs, or commit history when needed.

## Confidence mapping

- `confidence: high`: verified against primary evidence in the current analysis or directly defined by workspace instructions.
- `confidence: medium`: based on repo docs/reports or strong analyzer evidence but not fully source-verified in the current edit.
- `confidence: low`: external-baseline-only, analyzer-only, incomplete, or intentionally exploratory.

## Analyzer handling

[[deepwiki-first-baseline]] can provide a structured external baseline. graphify and Understand-Anything can provide local graph hypotheses. All of them must be reconciled with `repos/<repo>/` before becoming final report/wiki facts.

## Connection

This policy is the quality gate for [[llm-wiki-operating-model]] and depends on the directory separation in [[workspace-boundaries]].
