---
title: claude-devtools Context Token and Session Analysis
created: 2026-06-17
updated: 2026-06-17
type: concept
tags: [open-source, architecture, developer-tools, evidence]
sources: [artifacts/claude-devtools/deepwiki/pages-md/13-session-analysis-and-reporting.md, artifacts/claude-devtools/deepwiki/pages-md/13.1-session-analyzer.md, artifacts/claude-devtools/deepwiki/pages-md/13.2-cost-and-pricing.md, artifacts/claude-devtools/deepwiki/pages-md/16-glossary.md, repos/claude-devtools/src/main/utils/jsonl.ts, repos/claude-devtools/src/main/services/parsing/MessageClassifier.ts, repos/claude-devtools/src/main/services/analysis/ChunkBuilder.ts, repos/claude-devtools/src/main/services/analysis/ConversationGroupBuilder.ts, repos/claude-devtools/src/main/services/discovery/SubagentResolver.ts, repos/claude-devtools/src/main/types/chunks.ts, repos/claude-devtools/src/renderer/types/contextInjection.ts, repos/claude-devtools/src/renderer/utils/contextTracker.ts, repos/claude-devtools/src/shared/utils/tokenFormatting.ts]
confidence: high
---

# claude-devtools Context Token and Session Analysis

This note explains how [[claude-devtools]] turns parsed messages from [[claude-devtools-session-discovery-and-jsonl-parsing]] into session metrics, chunks/conversation groups, subagent views, and renderer-side context visibility. It also records a cost-model correction from the DeepWiki baseline.

## Verification snapshot

- Verified checkout: `repos/claude-devtools` at `16cc3c87c1e4d0e08ee101fb52dad1b85dbbe48a` / `v0.5.0`.
- DeepWiki baseline pages: `13`, `13.1`, `13.2`, `16`.
- Primary source paths: `jsonl.ts`, `MessageClassifier.ts`, `ChunkBuilder.ts`, `ConversationGroupBuilder.ts`, `SubagentResolver.ts`, `types/chunks.ts`, `contextInjection.ts`, `contextTracker.ts`, `tokenFormatting.ts`.

## Metrics and cost boundary

`calculateMetrics()` in `src/main/utils/jsonl.ts` deduplicates streaming assistant entries by `requestId` before summing token usage. It sums `input_tokens`, `output_tokens`, `cache_read_input_tokens`, and `cache_creation_input_tokens`, computes duration from message timestamps, and returns message count plus token totals.

The important correction: current source does not implement a real pricing lookup in this path. `costUsd` is initialized to `0`, and the returned `costUsd` is only set when it is greater than zero, which does not happen in the verified function. Therefore DeepWiki “Cost & Pricing” prose should be treated as display/formatting and token accounting, not as a source-verified monetary pricing engine.

## Message classification and chunks

`MessageClassifier` maps parsed messages into five categories: `user`, `system`, `compact`, `hardNoise`, and `ai`. `ChunkBuilder.buildChunks()` filters sidechain messages out of the main-thread chunk list, classifies the rest, creates independent `UserChunk`, `AIChunk`, `SystemChunk`, and `CompactChunk` objects, and flushes buffered AI messages around user/system/compact boundaries.

`types/chunks.ts` defines the visualization model:

- `UserChunk`: one genuine user message.
- `AIChunk`: assistant responses, sidechain messages, tool executions, and spawned processes.
- `SystemChunk`: local command output rendered like a system response.
- `CompactChunk`: compaction boundary.
- `Process`: resolved subagent execution with timing, metrics, optional Task linkage, and team metadata.

`ConversationGroupBuilder` provides a separate grouping model: one real user message plus all AI/internal responses until the next real user message. It separates Task executions from regular tool executions to avoid double-counting Task calls that already have linked subagent processes.

## Subagent/task interpretation

`SubagentResolver` reads subagent files from `{sessionId}/subagents/`, parses each JSONL file, filters warmup and compact artifacts, computes metrics/timing, links subagents to Task calls, propagates team metadata, detects parallelism, and enriches team colors. Parent Task linkage is result-based first: it reads `agentId` / `agent_id` from tool result metadata and maps that to the Task call ID. It then has additional matching logic for team-member cases.

## Context visibility model

Context visibility is mostly renderer-side. `contextInjection.ts` defines a discriminated union of context sources:

- `claude-md`
- `mentioned-file`
- `tool-output`
- `thinking-text`
- `task-coordination`
- `user-message`

`contextTracker.ts` computes per-AI-group context stats. It adds global CLAUDE.md injections on the first group, detects directory CLAUDE.md files from read/@mention paths, includes mentioned files under a max token cap, aggregates tool output tokens, separates team/task coordination tools such as `SendMessage`, `TeamCreate`, `TaskCreate`, and `TaskList`, includes user-message tokens, and aggregates thinking/text output. Token estimation uses the shared heuristic in `tokenFormatting.ts`: roughly `ceil(text.length / 4)`.

The tracker also models compaction phases: compact items reset accumulated context state and create phase metadata with pre/post compaction token deltas derived from assistant usage when available.

## Current-source corrections from DeepWiki

- `artifacts/claude-devtools/deepwiki/pages-md/13.1-session-analyzer.md` did not include extracted source references, and current checkout has no `src/main/services/analysis/SessionAnalyzer.ts`. The source-verified analysis path is distributed across parser, classifier, chunk builder, conversation group builder, subagent resolver, and renderer context tracker.
- DeepWiki's cost/pricing framing is too strong for this checkout: source-verified main metrics calculate token counts but not real USD cost.
- Context visibility is not just a backend session analyzer. It combines main-process parsing/chunk data with renderer-side context estimation and UI grouping.

## Evidence paths

- `repos/claude-devtools/src/main/utils/jsonl.ts:262-308` — metrics calculation and no-op USD cost boundary.
- `repos/claude-devtools/src/main/services/parsing/MessageClassifier.ts:42-64` — message category rules.
- `repos/claude-devtools/src/main/services/analysis/ChunkBuilder.ts:66-151` — independent chunk construction.
- `repos/claude-devtools/src/main/services/analysis/ConversationGroupBuilder.ts:26-72` — user-to-next-user conversation grouping.
- `repos/claude-devtools/src/main/services/analysis/ConversationGroupBuilder.ts:108-167` — Task vs regular tool execution split.
- `repos/claude-devtools/src/main/services/discovery/SubagentResolver.ts:38-80` and `89-131` — subagent parse/resolve path.
- `repos/claude-devtools/src/main/services/discovery/SubagentResolver.ts:198-260` — Task result linkage start.
- `repos/claude-devtools/src/main/types/chunks.ts:23-70` and `92-143` — Process and chunk types.
- `repos/claude-devtools/src/renderer/types/contextInjection.ts:199-220` and `226-286` — context injection union and stats shape.
- `repos/claude-devtools/src/renderer/utils/contextTracker.ts:60-72`, `761-914`, and `965-999` — context source categories, aggregation, and phase processing start.
- `repos/claude-devtools/src/shared/utils/tokenFormatting.ts:59-72` — token estimation heuristic.
