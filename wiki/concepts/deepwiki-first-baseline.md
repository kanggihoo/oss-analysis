---
title: DeepWiki-first Baseline
created: 2026-06-09
updated: 2026-06-09
type: concept
tags: [deepwiki, workflow, evidence, open-source]
sources: [OSS_ANALYSIS_WORKFLOW.md, artifacts/graphify/deepwiki/toc.md]
confidence: medium
---

# DeepWiki-first Baseline

DeepWiki is used as an external baseline and second opinion for GitHub repository analysis. It should be captured before local graph generation when available, then compared against local source evidence.

## Purpose

DeepWiki helps identify likely architecture sections, terminology, and important files before deeper local analysis. It is not an authority.

## Current artifact pattern

A captured DeepWiki baseline should live under:

```text
artifacts/<repo>/deepwiki/
├── raw/
├── toc.md
├── toc.json
├── pages-md/
├── pages-meta/ or pages-json/
└── next-payload/
```

The current workspace already contains a DeepWiki capture for `graphify` under `artifacts/graphify/deepwiki/`.

## Capture strategy

- Store raw HTML, TOC, Markdown pages, and metadata separately.
- Keep DeepWiki material in `artifacts/<repo>/deepwiki/` so the wiki can cite it without duplicating large raw output.
- Use the captured baseline to form verification questions for local source analysis.

## Verification boundary

DeepWiki claims become useful questions to check against `repos/<repo>/`. They should be written to reports/wiki only after passing [[evidence-backed-analysis]], or otherwise labeled as unverified/medium/low confidence.

## Connection

This page supports [[llm-wiki-operating-model]] and respects [[workspace-boundaries]] by keeping DeepWiki raw output in `artifacts/`, not inside `wiki/`.
