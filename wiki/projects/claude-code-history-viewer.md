---
title: Claude Code History Viewer
created: 2026-06-10
updated: 2026-06-10
type: project
tags: [open-source, project, architecture, developer-tools, deepwiki, testing, ci-cd]
sources:
  - repos/claude-code-history-viewer/package.json
  - repos/claude-code-history-viewer/src-tauri/Cargo.toml
  - repos/claude-code-history-viewer/src-tauri/tauri.conf.json
  - repos/claude-code-history-viewer/src-tauri/src/lib.rs
  - repos/claude-code-history-viewer/src-tauri/src/providers/mod.rs
  - repos/claude-code-history-viewer/src/store/useAppStore.ts
  - artifacts/claude-code-history-viewer/deepwiki/manifest.json
  - artifacts/claude-code-history-viewer/deepwiki/toc.md
  - reports/claude-code-history-viewer/overview.md
  - reports/claude-code-history-viewer/deepwiki-comparison.md
confidence: medium
---

# Claude Code History Viewer

`jhlee0409/claude-code-history-viewer`는 Tauri 2 기반 desktop application이자 optional WebUI server로, 여러 AI coding assistant의 local conversation/history 파일을 React UI에서 탐색·검색·분석하는 developer tool이다. 이 페이지는 [[deepwiki-first-baseline]]으로 수집한 DeepWiki 외부 baseline과 `repos/claude-code-history-viewer/` local source verification을 분리해서 기록한다.

## Evidence snapshot

- Repo checkout: `repos/claude-code-history-viewer/`
- Verified commit: `9d86b46e0312b1533d24875cf35b33ebacf9723b`
- DeepWiki artifact root: `artifacts/claude-code-history-viewer/deepwiki/`
- Human reports:
  - `reports/claude-code-history-viewer/overview.md`
  - `reports/claude-code-history-viewer/deepwiki-comparison.md`

DeepWiki extraction succeeded with `toc_count=51`, `matched_pages_count=51`, and `missing_pages_count=0` in `artifacts/claude-code-history-viewer/deepwiki/manifest.json`. As with [[evidence-backed-analysis]], DeepWiki remains a second opinion until checked against local source paths.

## Source-verified architecture

- Frontend: React 19 + TypeScript + Vite, with entrypoint `src/main.tsx` and app orchestration in `src/App.tsx`.
- State: `src/store/useAppStore.ts` uses Zustand slice composition for project, message, search, analytics, settings, metadata, provider, archive, and session-picker domains.
- Backend: `src-tauri/src/lib.rs` registers Tauri commands and plugins for filesystem, dialog, store, updater, process, HTTP, opener, OS, and single-instance behavior.
- Provider ingestion: `src-tauri/src/providers/mod.rs` defines provider modules and IDs for Aider, Claude Code, Cline, Codex CLI, Cursor, Gemini CLI, ForgeCode, OpenCode, and Antigravity.
- Server mode: `src-tauri/Cargo.toml` gates Axum/Tokio/Rust-Embed behind the `webui-server` feature, and `src-tauri/src/lib.rs` branches to server mode when `--serve` is present.
- Update system: `src-tauri/tauri.conf.json` enables Tauri updater against GitHub Release `latest.json`; `src-tauri/src/commands/update.rs` implements OS-specific detached relaunch helpers.

## Analysis notes

- This repo is useful as a cross-project reference for local AI assistant history formats, multi-provider ingestion, and Tauri desktop/server dual-mode packaging.
- The codebase has a large TypeScript/TSX frontend surface and a substantial Rust backend command layer; future deep analysis should split UI components, provider parsers, and update/server systems into separate reports.
- Workspace separation follows [[workspace-boundaries]]: source remains in `repos/`, DeepWiki/static captures in `artifacts/`, human synthesis in `reports/`, and durable reusable notes here in `wiki/`.

## Next useful work

1. Run graphify after the DeepWiki baseline and compare its graph clusters against the verified source paths.
2. Build a focused code map for provider ingestion: `providers/*.rs` → `commands/multi_provider.rs` → frontend provider/filter state.
3. Run build/test verification if the goal shifts from architecture analysis to operational validation.
