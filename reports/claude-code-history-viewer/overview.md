---
title: claude-code-history-viewer overview
repo: https://github.com/jhlee0409/claude-code-history-viewer
local_checkout: /Users/kkh/Desktop/oss-analysis/repos/claude-code-history-viewer
commit: 9d86b46e0312b1533d24875cf35b33ebacf9723b
generated_at: 2026-06-10T09:40:33Z
status: preliminary-source-verified
tags: [open-source-analysis, tauri, react, rust, deepwiki]
---

# claude-code-history-viewer — 개요

## 분석 범위

- 대상 repo: `https://github.com/jhlee0409/claude-code-history-viewer`
- local checkout: `repos/claude-code-history-viewer/`
- 분석 commit: `9d86b46e0312b1533d24875cf35b33ebacf9723b`
- DeepWiki baseline artifact: `artifacts/claude-code-history-viewer/deepwiki/`
- static artifacts:
  - `artifacts/claude-code-history-viewer/repo-metadata.txt`
  - `artifacts/claude-code-history-viewer/github-metadata.json`
  - `artifacts/claude-code-history-viewer/static-analysis/tokei.txt`
  - `artifacts/claude-code-history-viewer/static-analysis/tokei.json`
  - `artifacts/claude-code-history-viewer/static-analysis/file-summary.json`

## 한 줄 요약

`claude-code-history-viewer`는 Tauri 2 기반 데스크톱 앱이자 선택적 WebUI 서버로, 여러 AI coding assistant의 local conversation/history 파일을 React UI에서 탐색·검색·분석하도록 구성된 TypeScript/Rust 프로젝트다.

## 확인된 기본 메타데이터

GitHub API capture 기준(`artifacts/claude-code-history-viewer/github-metadata.json`):

- public repo: `jhlee0409/claude-code-history-viewer`
- GitHub description: `desktop app to browse and analyze your Claude Code conversation history`
- primary language: `TypeScript`
- license: MIT
- default branch: `main`
- topics: `claude`, `claude-code`, `codex`, `conversation-history`, `desktop-app`, `developer-tools`, `opencode`, `react`, `rust`, `tauri`

## 코드 규모 스냅샷

`tokei` capture 기준(`artifacts/claude-code-history-viewer/static-analysis/tokei.txt`):

| 언어 | Files | Lines | Code |
|---|---:|---:|---:|
| TSX | 250 | 47,724 | 41,645 |
| TypeScript | 233 | 38,974 | 28,981 |
| Rust | 55 | 37,243 | 32,046 |
| JSON | 74 | 10,160 | 10,149 |
| Markdown | 37 | 8,662 | 0 |
| YAML | 3 | 7,562 | 6,015 |
| Total | 673 | 159,550 | 124,670 |

별도 파일 요약(`static-analysis/file-summary.json`)에서는 `.tsx` 250개, `.ts` 233개, `.rs` 55개, `.md` 40개 등 총 769개 non-git 파일이 확인됐다.

## Source-verified architecture facts

아래 항목은 DeepWiki 설명이 아니라 local checkout에서 직접 확인한 사실이다.

### 1. Tauri 2 + React/Vite 애플리케이션

- `package.json`은 `@tauri-apps/api` `2.11.0`, `@tauri-apps/cli` `2.11.2`, `vite` `^7.1.12`, `react` `^19.1.0`, `typescript` `~5.8.3`를 사용한다.
- `src-tauri/Cargo.toml`은 Rust crate `claude-code-history-viewer`, version `1.13.0`, Tauri dependency `2.11.2`를 선언한다.
- `src-tauri/tauri.conf.json`은 productName `Claude Code History Viewer`, window label `main`, frontend dev URL `http://localhost:5173`, build commands `just vite-dev`/`just frontend-build`를 설정한다.
- `src/main.tsx`는 React root를 생성하고 `PlatformProvider`, `ThemeProvider`, `ModalProvider`, `ErrorBoundary`, `Toaster`, `App`을 조합한다.

### 2. Zustand slice 기반 frontend state

- `src/store/useAppStore.ts`는 `zustand` `create()`로 단일 `useAppStore`를 만들고 project/message/search/analytics/settings/globalStats/metadata/captureMode/board/filter/navigation/watcher/navigator/provider/archive/sessionPicker slice를 합성한다.
- provider 관련 상태는 `src/store/slices/providerSlice.ts`에서 관리되며 `detectProviders()`가 `api<ProviderInfo[]>("detect_providers")`를 호출한다.

### 3. Rust backend command surface

- `src-tauri/src/lib.rs`는 `commands`, `models`, `providers`, `utils`, `wsl` 모듈을 공개하고 Tauri `invoke_handler`에 project/session/stats/settings/provider/archive/update/watcher/WSL 관련 command를 등록한다.
- 동일 파일에서 `tauri_plugin_fs`, `dialog`, `store`, `updater`, `process`, `http`, `opener`, `os`, `single_instance` 플러그인을 초기화한다.

### 4. Multi-provider history ingestion

- `src-tauri/src/providers/mod.rs`는 `aider`, `antigravity`, `claude`, `cline`, `codex`, `cursor`, `forgecode`, `gemini`, `opencode` provider module을 선언한다.
- `ProviderId` enum은 9개 provider(`Aider`, `Claude`, `Cline`, `Codex`, `Cursor`, `Gemini`, `ForgeCode`, `OpenCode`, `Antigravity`)를 정의한다.
- `src-tauri/src/commands/multi_provider.rs`의 `scan_all_projects()`는 active provider 목록을 받아 Claude/Codex/Gemini/ForgeCode/OpenCode/Cline/Cursor/Aider/Antigravity 순으로 scan을 시도한다.

### 5. 선택적 WebUI server mode

- `src-tauri/Cargo.toml`은 `webui-server` feature를 별도로 두고 `axum`, `tower-http`, `tokio`, `rust-embed` 등을 optional dependency로 둔다.
- `src-tauri/src/lib.rs`는 `--serve` 인자가 있으면 `run_server(&args)`로 분기한다.
- `src-tauri/src/server/mod.rs`는 Axum router를 구성하고 `/events`, `/scan_projects`, `/load_session_messages`, `/search_messages`, stats/settings/archive/provider/update 관련 REST endpoint를 등록한다.

### 6. 업데이트 시스템

- `src-tauri/tauri.conf.json`은 Tauri updater를 활성화하고 endpoint를 `https://github.com/jhlee0409/claude-code-history-viewer/releases/latest/download/latest.json`로 지정한다.
- `src-tauri/src/lib.rs`는 `tauri_plugin_updater`를 초기화하고 `force_quit_and_relaunch` command를 등록한다.
- `src-tauri/src/commands/update.rs`는 macOS/Windows/Linux별 detached relaunch helper를 구현한다.

### 7. i18n, tests, CI

- `src/i18n/locales/` 아래에 `en`, `ko`, `ja`, `zh-CN`, `zh-TW` locale JSON 묶음이 존재한다.
- `package.json`에는 `generate:i18n-types`, `i18n:flatten`, `i18n:sync`, `i18n:validate` script가 있다.
- `.github/workflows/`에는 `rust-tests.yml`, `update-flow-tests.yml`, `updater-release.yml`, `server-release.yml`, `pages.yml`, `issue-to-spec.yml` 등이 있다.
- frontend test 파일은 `src/test/`, Rust integration/config tests는 `src-tauri/tests/`에서 확인된다.

## 아직 검증하지 않은 항목

- graphify/Understand-Anything local graph 분석은 아직 실행하지 않았다.
- DeepWiki 각 page의 세부 architecture claim은 artifact로 저장했지만, 이 보고서에서는 위 source path로 확인한 항목만 사실로 적었다.
- 빌드/테스트 실행은 이번 작업 범위에 포함하지 않았다. 필요하면 `pnpm install`, `pnpm build`, `pnpm test`, Rust test 순으로 별도 검증해야 한다.
