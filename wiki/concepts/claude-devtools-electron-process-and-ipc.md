---
title: claude-devtools Electron Process and IPC
created: 2026-06-17
updated: 2026-06-17
type: concept
tags: [open-source, architecture, developer-tools, evidence]
sources: [artifacts/claude-devtools/deepwiki/pages-md/3.1-electron-process-model.md, artifacts/claude-devtools/deepwiki/pages-md/3.3-ipc-communication-layer.md, artifacts/claude-devtools/deepwiki/pages-md/3.4-state-management.md, artifacts/claude-devtools/deepwiki/pages-md/14.1-electronapi-interface.md, artifacts/claude-devtools/deepwiki/pages-md/14.2-ipc-handler-reference.md, artifacts/claude-devtools/deepwiki/pages-md/14.3-service-context-api.md, repos/claude-devtools/src/main/index.ts, repos/claude-devtools/src/main/ipc/handlers.ts, repos/claude-devtools/src/main/services/infrastructure/ServiceContext.ts, repos/claude-devtools/src/main/services/infrastructure/ServiceContextRegistry.ts, repos/claude-devtools/src/preload/index.ts, repos/claude-devtools/src/preload/constants/ipcChannels.ts, repos/claude-devtools/src/shared/types/api.ts, repos/claude-devtools/src/renderer/store/index.ts]
confidence: high
---

# claude-devtools Electron Process and IPC

This note records the 1차 source-verified process and IPC boundary for [[claude-devtools]]. It should be read together with [[claude-devtools-session-discovery-and-jsonl-parsing]] because IPC mostly exposes the session-discovery and parsing services to the renderer.

## Verification snapshot

- Verified checkout: `repos/claude-devtools` at `16cc3c87c1e4d0e08ee101fb52dad1b85dbbe48a` / `v0.5.0`.
- DeepWiki baseline pages: `3.1`, `3.3`, `3.4`, `14.1`, `14.2`, `14.3`.
- Primary source paths: `src/main/index.ts`, `src/main/ipc/handlers.ts`, `src/main/services/infrastructure/ServiceContext.ts`, `src/preload/index.ts`, `src/shared/types/api.ts`, `src/renderer/store/index.ts`.

## Responsibility boundaries

```text
main process
  Electron lifecycle, BrowserWindow, filesystem, service context registry,
  session parsing/scanning/cache/file watcher, IPC handlers, HTTP sidecar wiring

preload process
  contextBridge-secured ElectronAPI implementation; no full ipcRenderer exposure

shared
  cross-process API/types/constants and pure utilities

renderer process
  React UI, Zustand slices, tab/session state, context visualization utilities
```

`src/main/index.ts` documents the main process responsibilities and initializes `ServiceContextRegistry`, local `ServiceContext`, `NotificationManager`, `UpdaterService`, `HttpServer`, and IPC handlers. `ServiceContext.ts` is the most important boundary: it constructs the data-service stack in dependency order (`ProjectScanner`, `MemoryReader`, `SessionParser`, `SubagentResolver`, `ChunkBuilder`, `DataCache`, `FileWatcher`) and owns lifecycle methods for watcher/cache cleanup.

`ServiceContextRegistry.ts` manages a map of contexts, keeps `local` as the permanent default, pauses/resumes file watchers on `switch()`, and refuses to destroy the local context. This makes local-vs-SSH a context concern, not a separate parser stack.

## IPC surface

`src/main/ipc/handlers.ts` initializes domain modules with the registry and registers project, session, search, subagent, validation, utility, notification, config, updater, SSH, context, memory, and window handlers. The preload bridge in `src/preload/index.ts` exposes these as `electronAPI` methods such as `getProjects`, `getSessions`, `getSessionDetail`, `getSessionMetrics`, `getWaterfallData`, `searchSessions`, `getRepositoryGroups`, config APIs, notifications APIs, SSH APIs, and context APIs.

The type contract lives primarily in `src/shared/types/api.ts`. Config-style operations use an `IpcResult<T>` wrapper in preload (`success`, `data`, `error`) and `invokeIpcWithResult<T>()` throws on failure; several session operations return direct data or `null`/empty arrays on errors from their main handlers.

## State management boundary

Renderer state is a Zustand slice composition in `src/renderer/store/index.ts`, with project/session/sessionDetail/subagent/conversation/tab/pane/config/connection/context/update/memory slices. `initializeNotificationListeners()` also subscribes to IPC file-change and notification events, then triggers refreshes through store actions. This means parsing and file watching stay in main services, while renderer state focuses on selection, tabs, UI refresh, and visualization state.

## Current-source corrections from DeepWiki

- DeepWiki's multi-context framing is broadly right, but current source makes `ServiceContext` the concrete unit of isolation; project/session parser/cache/watcher are not independent globals once inside a context.
- The preload bridge exposes many direct string-channel session calls plus constant-backed newer domains. The stable source of truth for the renderer API is `src/preload/index.ts` plus `src/shared/types/api.ts`, not just the channel constants file.
- The current source includes HTTP sidecar wiring in `src/main/index.ts`, but 1차 only verified how main services are passed to `HttpServer`; detailed HTTP routes are deferred to 3차.

## Evidence paths

- `repos/claude-devtools/src/main/index.ts:247-294` — service initialization and IPC registration.
- `repos/claude-devtools/src/main/index.ts:110-156` — FileWatcher events forwarded to renderer and HTTP SSE clients.
- `repos/claude-devtools/src/main/services/infrastructure/ServiceContext.ts:63-124` — per-context service construction.
- `repos/claude-devtools/src/main/services/infrastructure/ServiceContextRegistry.ts:31-146` — context map and switch lifecycle.
- `repos/claude-devtools/src/main/ipc/handlers.ts:65-103` — domain handler initialization/registration.
- `repos/claude-devtools/src/preload/index.ts:117-160` — typed IPC result helper and session API methods.
- `repos/claude-devtools/src/shared/types/api.ts:1-8` — shared API type intent.
- `repos/claude-devtools/src/renderer/store/index.ts:33-50` — Zustand slice composition.
