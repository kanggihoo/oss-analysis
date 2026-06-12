---
title: claude-code-history-viewer DeepWiki baseline
repo: https://github.com/jhlee0409/claude-code-history-viewer
deepwiki_url: https://deepwiki.com/jhlee0409/claude-code-history-viewer
artifact_root: /Users/kkh/Desktop/oss-analysis/artifacts/claude-code-history-viewer/deepwiki
generated_at: 2026-06-10T09:40:03Z
status: extracted-not-authoritative
tags: [deepwiki, baseline, open-source-analysis]
---

# DeepWiki baseline — claude-code-history-viewer

## Extraction result

`deepwiki-markdown-extraction` skill의 표준 script를 사용해 DeepWiki 원문 Markdown을 Next.js/RSC payload에서 추출했다.

실행 명령:

```bash
cd /Users/kkh/Desktop/oss-analysis
python3 /Users/kkh/.hermes/profiles/oss-analyst/skills/research/deepwiki-markdown-extraction/scripts/deepwiki_extract.py \
  jhlee0409/claude-code-history-viewer \
  --out artifacts/claude-code-history-viewer/deepwiki \
  --request-delay 1.0
```

터미널 결과:

```text
[start] jhlee0409/claude-code-history-viewer
[index] OK
[toc] 51
[match] 51/51
[write] OK
Done: 51/51 missing=0
```

`manifest.json` 확인 결과:

- DeepWiki URL: `https://deepwiki.com/jhlee0409/claude-code-history-viewer`
- index fetch status: `200`
- index content type: `text/html; charset=utf-8`
- index sha256: `3aadcb416016bacc5b76aabd0adcd44ea5bce6621fc5249321f6122bb539f799`
- TOC items: `51`
- Markdown chunks: `51`
- matched pages: `51`
- missing pages: `0`
- individual page refetches: `[]` — index payload만으로 전 page가 match됨

## Artifact layout

주요 산출물:

```text
artifacts/claude-code-history-viewer/deepwiki/
├── raw/index.html
├── toc.json
├── toc.md
├── manifest.json
├── next-payload/markdown-chunks.json
├── pages-md/
└── pages-meta/
```

대표 page Markdown:

- `artifacts/claude-code-history-viewer/deepwiki/pages-md/1-overview.md`
- `artifacts/claude-code-history-viewer/deepwiki/pages-md/2-architecture-overview.md`
- `artifacts/claude-code-history-viewer/deepwiki/pages-md/2.5-multi-provider-system.md`
- `artifacts/claude-code-history-viewer/deepwiki/pages-md/5-backend-systems.md`
- `artifacts/claude-code-history-viewer/deepwiki/pages-md/8-update-system.md`
- `artifacts/claude-code-history-viewer/deepwiki/pages-md/9-development-guide.md`

## DeepWiki TOC coverage

DeepWiki는 다음 영역을 baseline으로 제공한다. 이 목록은 `toc.md`에서 확인한 구조이며, source 검증 전에는 외부 baseline/second opinion으로만 취급한다.

1. Overview
   - Installation and Setup
   - Key Features
2. Architecture Overview
   - System Architecture
   - Frontend Architecture
   - Backend Architecture
   - Data Flow
   - Multi-Provider System
3. Core Components
   - Project Tree / Session Item
   - Session Board / Interaction Cards and Lanes / Activity Timeline
   - Message Viewer
   - Analytics Dashboard / Analytics Views
   - Token Stats Viewer
   - Settings Manager
   - Header and Navigation
   - Archive Manager
   - Recent Edits Viewer
4. State Management
   - Store Architecture
   - State Slices
   - Data Models
5. Backend Systems
   - Project and Session Commands
   - Statistics and Analytics
   - Settings Management
   - File Watcher
   - Provider Implementations
   - WebUI Server Mode
   - WSL Support
6. Content Rendering
   - Content Renderers
   - Brushing System
   - Tool Icons and Display
   - ANSI and Terminal Rendering
7. Internationalization
   - Translation System
   - Type Generation
8. Update System
   - Release Workflow
   - Auto-Updater
9. Development Guide
   - Build System
   - Testing
   - Utility Functions
10. Glossary

## Initial source cross-check

DeepWiki TOC의 큰 축은 local source layout과 대체로 맞는다.

| DeepWiki 영역 | local source evidence | 상태 |
|---|---|---|
| Frontend Architecture | `src/main.tsx`, `src/App.tsx`, `src/layouts/`, `src/components/`, `src/hooks/` | 확인됨 |
| State Management | `src/store/useAppStore.ts`, `src/store/slices/*.ts` | 확인됨 |
| Backend Systems | `src-tauri/src/lib.rs`, `src-tauri/src/commands/`, `src-tauri/src/models/` | 확인됨 |
| Multi-Provider System | `src-tauri/src/providers/mod.rs`, `src-tauri/src/commands/multi_provider.rs`, `src/store/slices/providerSlice.ts` | 확인됨 |
| WebUI Server Mode | `src-tauri/Cargo.toml` feature `webui-server`, `src-tauri/src/server/mod.rs`, `src-tauri/src/lib.rs` `--serve` branch | 확인됨 |
| Update System | `src-tauri/tauri.conf.json` updater config, `src-tauri/src/commands/update.rs`, `.github/workflows/updater-release.yml` | 확인됨 |
| Internationalization | `src/i18n/locales/en`, `ko`, `ja`, `zh-CN`, `zh-TW`, package i18n scripts | 확인됨 |
| Testing / CI | `src/test/`, `src-tauri/tests/`, `.github/workflows/rust-tests.yml`, `update-flow-tests.yml` | 확인됨 |

## 취급 원칙

- `pages-md/` 아래 Markdown은 원문 baseline으로 보존한다.
- DeepWiki claim은 최종 사실이 아니다. 보고서에는 local source path로 검증한 claim만 fact로 올린다.
- 다음 단계에서 graphify/Understand-Anything을 실행하면 결과는 `artifacts/claude-code-history-viewer/graphify/`, `artifacts/claude-code-history-viewer/understand-anything/`에 분리 저장한다.
