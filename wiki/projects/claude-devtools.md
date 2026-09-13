---
title: claude-devtools
created: 2026-06-17
updated: 2026-06-17
type: project
tags: [open-source, project, developer-tools, architecture, evidence]
sources: [reports/claude-devtools/initial-capture.md, artifacts/claude-devtools/deepwiki/pages-md/1-overview.md, artifacts/claude-devtools/deepwiki/pages-md/3-architecture.md, artifacts/claude-devtools/deepwiki/pages-md/4-session-discovery-and-parsing.md, artifacts/claude-devtools/deepwiki/pages-md/13-session-analysis-and-reporting.md, repos/claude-devtools/README.md, repos/claude-devtools/package.json, repos/claude-devtools/src/main/index.ts, repos/claude-devtools/src/main/services/infrastructure/ServiceContext.ts, repos/claude-devtools/src/main/ipc/sessions.ts, repos/claude-devtools/src/main/utils/jsonl.ts]
confidence: high
---

# claude-devtools

`claude-devtools` is an Electron/Vite/React TypeScript desktop app for inspecting Claude Code session logs already written under `.claude` rather than wrapping Claude Code at runtime. The repo description and README frame the product as a visual debugger for session transcripts, tool calls, token usage, subagents, and context visibility; this page records only the 1차 source-verified core architecture and data pipeline. See [[claude-devtools-electron-process-and-ipc]], [[claude-devtools-session-discovery-and-jsonl-parsing]], and [[claude-devtools-context-token-and-session-analysis]] for focused notes.

## Verification snapshot

- Local checkout: `repos/claude-devtools`
- Branch: `main`
- HEAD: `16cc3c87c1e4d0e08ee101fb52dad1b85dbbe48a`
- Describe: `v0.5.0`
- Dirty status at verification: `0` entries
- DeepWiki baseline: `artifacts/claude-devtools/deepwiki/pages-md/` with 54/54 pages extracted; 1차 used architecture, session parsing, context/session-analysis, API/path pages.

## Source-verified operating model

The app has a three-process Electron boundary: main process owns filesystem/session services and IPC registration, preload exposes a typed `window.electronAPI`, and renderer owns React/Zustand UI state. `package.json` declares `dist-electron/main/index.cjs` as the packaged main entry and `electron-vite`/`electron-builder` scripts, while `src/main/index.ts` describes the main entry responsibilities and initializes services before registering handlers.

The main process builds a `ServiceContextRegistry` and a permanent local `ServiceContext` backed by `LocalFileSystemProvider`, then wires `FileWatcher` events to both the renderer and optional HTTP sidecar broadcasts. A `ServiceContext` is an isolated stack containing `ProjectScanner`, `MemoryReader`, `SessionParser`, `SubagentResolver`, `ChunkBuilder`, `DataCache`, and `FileWatcher`; this is the core responsibility boundary that lets local and future SSH contexts share the same data-service shape.

The core data flow is:

```text
.claude/projects/<encoded-project>/*.jsonl
→ ProjectScanner discovers projects/sessions and resolves cwd/path metadata
→ SessionParser streams JSONL into ParsedMessage[]
→ SubagentResolver links Task tool calls to subagent JSONL files
→ ChunkBuilder builds chunks / conversation groups / waterfall data
→ DataCache stores SessionDetail by projectId/sessionId + file fingerprint
→ IPC/preload returns typed session/detail/metrics APIs to renderer state/UI
```

## Subsystem map from 1차

| Subsystem | Verified role | Main evidence |
|---|---|---|
| Electron process boundary | Main is privileged service/runtime, preload is IPC bridge, renderer is UI/state. | `src/main/index.ts`, `src/preload/index.ts`, `src/shared/types/api.ts`, `src/renderer/store/index.ts` |
| Service context | Bundles project/session/parser/cache/watcher services per local/SSH context. | `src/main/services/infrastructure/ServiceContext.ts`, `ServiceContextRegistry.ts` |
| Session discovery | Scans `.claude/projects`, validates encoded project directory names, groups sessions, extracts cwd when possible. | `src/main/services/discovery/ProjectScanner.ts`, `src/main/utils/pathDecoder.ts` |
| JSONL parsing | Streams session files line-by-line, converts raw entries into `ParsedMessage`, extracts tool calls/results. | `src/main/services/parsing/SessionParser.ts`, `src/main/utils/jsonl.ts`, `src/main/types/messages.ts` |
| Chunk/session analysis | Classifies messages, creates independent user/AI/system/compact chunks, and alternative conversation groups. | `src/main/services/parsing/MessageClassifier.ts`, `src/main/services/analysis/ChunkBuilder.ts`, `ConversationGroupBuilder.ts` |
| Context visibility | Renderer computes context-injection estimates across CLAUDE.md, mentioned files, tool outputs, thinking/text, task coordination, and user messages. | `src/renderer/types/contextInjection.ts`, `src/renderer/utils/contextTracker.ts`, `src/shared/utils/tokenFormatting.ts` |

## DeepWiki baseline vs current-source corrections

- DeepWiki's high-level Electron/process/service narrative matches the checkout, but the current source shows a concrete `ServiceContext`/`ServiceContextRegistry` boundary; this should be treated as the durable architecture primitive rather than a generic “multi-context system.”
- DeepWiki's cost/pricing page should not be read as a full pricing engine. In current source, `calculateMetrics()` sums usage tokens but initializes `costUsd = 0`, so `costUsd` is normally undefined unless future code changes this path.
- DeepWiki's session-analysis page `13.1-session-analyzer.md` has no extracted source references in the baseline capture. Current source has no `src/main/services/analysis/SessionAnalyzer.ts`; session analysis is distributed across `SessionParser`, `jsonl.ts`, `ChunkBuilder`, `ConversationGroupBuilder`, and renderer context-tracking utilities.
- Current IPC detail response strips raw `messages` and process message arrays before crossing to renderer, returning chunks/process summaries plus a fingerprint. This performance boundary is more specific than the DeepWiki overview.

## 1차 boundary and follow-ups

This page intentionally does not source-verify UI, SSH, HTTP sidecar, notification, build/release, or contribution workflow details beyond the 1차 core path. The follow-up plan lives in `reports/claude-devtools/wiki-ingestion-plan.md`.

Recommended next pages:

- 2차: UI/session exploration and command/settings/realtime model.
- 3차: SSH, HTTP sidecar, notification, configuration, Claude root detection.
- 4차: build/test/CI/release/contribution workflow.
- 5차: consolidation into Taste Notes and comparison hooks with [[claude-code-history-viewer]], [[codeburn]], and [[tokscale]].
