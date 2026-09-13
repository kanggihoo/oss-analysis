---
title: claude-devtools Session Discovery and JSONL Parsing
created: 2026-06-17
updated: 2026-06-17
type: concept
tags: [open-source, architecture, developer-tools, evidence]
sources: [artifacts/claude-devtools/deepwiki/pages-md/4-session-discovery-and-parsing.md, artifacts/claude-devtools/deepwiki/pages-md/4.1-project-scanner.md, artifacts/claude-devtools/deepwiki/pages-md/4.2-path-encoding-and-project-ids.md, artifacts/claude-devtools/deepwiki/pages-md/4.3-jsonl-parsing.md, artifacts/claude-devtools/deepwiki/pages-md/4.4-caching-strategy.md, artifacts/claude-devtools/deepwiki/pages-md/14.4-path-utilities.md, repos/claude-devtools/src/main/services/discovery/ProjectScanner.ts, repos/claude-devtools/src/main/services/parsing/SessionParser.ts, repos/claude-devtools/src/main/utils/jsonl.ts, repos/claude-devtools/src/main/utils/pathDecoder.ts, repos/claude-devtools/src/main/ipc/sessions.ts, repos/claude-devtools/src/main/services/infrastructure/DataCache.ts, repos/claude-devtools/src/main/types/messages.ts]
confidence: high
---

# claude-devtools Session Discovery and JSONL Parsing

This note covers the source-verified ingestion path for Claude Code session files in [[claude-devtools]]. It is the core data pipeline behind [[claude-devtools-electron-process-and-ipc]] and feeds the context/session analysis in [[claude-devtools-context-token-and-session-analysis]].

## Verification snapshot

- Verified checkout: `repos/claude-devtools` at `16cc3c87c1e4d0e08ee101fb52dad1b85dbbe48a` / `v0.5.0`.
- DeepWiki baseline pages: `4`, `4.1`, `4.2`, `4.3`, `4.4`, `14.4`.
- Primary source paths: `ProjectScanner.ts`, `SessionParser.ts`, `jsonl.ts`, `pathDecoder.ts`, `ipc/sessions.ts`, `DataCache.ts`, `types/messages.ts`.

## Discovery model

`ProjectScanner` scans the configured Claude projects directory, defaulting to `getProjectsBasePath()` from `pathDecoder.ts`. That path resolves to `getClaudeBasePath()/projects`, where `getClaudeBasePath()` is either an override set by config or the auto-detected `~/.claude` base path.

The scanner filters directory entries through `isValidEncodedPath()`, then scans each encoded project directory for root-level `.jsonl` files. For local filesystems it tries to extract `cwd` from session files during project discovery; over SSH it intentionally avoids reading every file body at discovery time. This is an important performance and remote-access boundary.

## Path encoding and project IDs

`pathDecoder.ts` documents Claude Code's encoded path convention: path separators become dashes, for example `/Users/name/project` becomes `-Users-name-project`. The file explicitly warns this decode is lossy for paths containing dashes, so `extractProjectName()` prefers a `cwdHint` when available. Composite project IDs use the shape `{encodedPath}::{8-char-hex}` and `extractBaseDir()` strips the suffix when building session/subagent file paths.

```text
encoded project dir
→ validate with isValidEncodedPath()
→ optional cwd extraction for accurate display/splitting
→ projectId may be plain encoded path or encoded::hash composite
→ buildSessionPath(projectsDir, projectId, sessionId)
```

## JSONL parsing model

`SessionParser.parseSession()` asks `ProjectScanner` for the session path and delegates file parsing to `parseJsonlFile()`. `parseJsonlFile()` creates a read stream and reads line-by-line with `readline`, skipping empty lines and logging parse errors without aborting the whole file.

Each JSON object is converted into `ParsedMessage` by `parseChatHistoryEntry()` in `jsonl.ts`. The parser preserves `uuid`, `parentUuid`, `type`, `timestamp`, `role`, `content`, token `usage`, model/request metadata, `cwd`, git branch, agent ID, sidechain/meta flags, and extracted tool calls/results. `types/messages.ts` then defines guards such as `isParsedRealUserMessage()` and `isParsedUserChunkMessage()` so later chunking can separate actual user prompts from tool results/system output/noise.

## Caching and refresh boundary

`DataCache` is an in-memory LRU/TTL cache for `SessionDetail` and `SubagentDetail`, defaulting to 50 entries and 10 minutes. Cache entries carry a schema version and optional file fingerprint. `ipc/sessions.ts` fingerprints the target JSONL file using `mtimeMs-size`; if the renderer passes a matching known fingerprint, `get-session-detail` returns an `unchanged` sentinel instead of reparsing. Otherwise it reads from `DataCache`, or parses, resolves subagents, builds session detail, then stores it with the observed fingerprint.

Cache invalidation is both event-driven and safety-net driven: `DataCache.invalidateSession()` and project/subagent invalidators remove related entries, while fingerprint mismatch protects against missed FileWatcher events.

## Current-source corrections from DeepWiki

- DeepWiki correctly identifies path encoding as central, but the current source stresses that decode is lossy and `cwd` extracted from JSONL is preferred for accurate names.
- The current session detail IPC does not send raw parsed messages to the renderer; after building chunks/process summaries, `ipc/sessions.ts` strips `messages` and process `messages` from the IPC payload.
- DeepWiki's caching page should be read through current `DataCache`: it is an in-memory LRU/TTL cache with version and fingerprint invalidation, not a persistent parsed-session cache.

## Evidence paths

- `repos/claude-devtools/src/main/services/discovery/ProjectScanner.ts:110-145` — scans projects and sorts by recent activity.
- `repos/claude-devtools/src/main/services/discovery/ProjectScanner.ts:203-260` — scans one encoded project directory, filters `.jsonl`, reads cwd locally.
- `repos/claude-devtools/src/main/utils/pathDecoder.ts:27-45` — encode/decode functions and lossy decode warning.
- `repos/claude-devtools/src/main/utils/pathDecoder.ts:169-198` — composite project ID validation/base extraction.
- `repos/claude-devtools/src/main/utils/pathDecoder.ts:320-328` — projects/todos base paths.
- `repos/claude-devtools/src/main/services/parsing/SessionParser.ts:68-139` — parse session file then classify message groups.
- `repos/claude-devtools/src/main/utils/jsonl.ts:52-82` — streaming JSONL parser.
- `repos/claude-devtools/src/main/utils/jsonl.ts:104-194` — raw entry to `ParsedMessage` mapping.
- `repos/claude-devtools/src/main/ipc/sessions.ts:221-292` — fingerprint/cache/parse/build/strip return path.
- `repos/claude-devtools/src/main/services/infrastructure/DataCache.ts:31-44` and `75-110` — cache config and get path.
