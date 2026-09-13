# claude-devtools wiki ingestion plan

- Repo: `matt1398/claude-devtools`
- Workspace: `/Users/kkh/Desktop/oss-analysis`
- Local checkout: `repos/claude-devtools`
- DeepWiki source pages: `artifacts/claude-devtools/deepwiki/pages-md/`
- Korean reading copy: `deepwiki-ko/claude-devtools/`
- Target wiki: `wiki/`

## 0차 완료 상태

Already completed before this plan:

- DeepWiki extraction: `artifacts/claude-devtools/deepwiki/`
  - `toc_count`: 54
  - `pages-md`: 54
  - `pages-meta`: 54
  - missing pages: 0
- Korean translation: `deepwiki-ko/claude-devtools/`
  - `00-index.md` plus 54 translated pages
  - run log: `artifacts/claude-devtools/deepwiki/translation-runs/20260617-071812-codex-ko.jsonl`
- Repo clone: `repos/claude-devtools`
  - branch: `main`
  - HEAD: `16cc3c87c1e4d0e08ee101fb52dad1b85dbbe48a`
  - describe: `v0.5.0`
  - dirty entries at verification: 0
- Initial capture report: `reports/claude-devtools/initial-capture.md`

## 1차 완료 범위: Core architecture + core data pipeline

Completed wiki outputs:

- `wiki/projects/claude-devtools.md`
- `wiki/concepts/claude-devtools-electron-process-and-ipc.md`
- `wiki/concepts/claude-devtools-session-discovery-and-jsonl-parsing.md`
- `wiki/concepts/claude-devtools-context-token-and-session-analysis.md`

1차 DeepWiki pages referenced:

- `artifacts/claude-devtools/deepwiki/pages-md/1-overview.md`
- `artifacts/claude-devtools/deepwiki/pages-md/3-architecture.md`
- `artifacts/claude-devtools/deepwiki/pages-md/3.1-electron-process-model.md`
- `artifacts/claude-devtools/deepwiki/pages-md/3.2-multi-context-system.md`
- `artifacts/claude-devtools/deepwiki/pages-md/3.3-ipc-communication-layer.md`
- `artifacts/claude-devtools/deepwiki/pages-md/3.4-state-management.md`
- `artifacts/claude-devtools/deepwiki/pages-md/4-session-discovery-and-parsing.md`
- `artifacts/claude-devtools/deepwiki/pages-md/4.1-project-scanner.md`
- `artifacts/claude-devtools/deepwiki/pages-md/4.2-path-encoding-and-project-ids.md`
- `artifacts/claude-devtools/deepwiki/pages-md/4.3-jsonl-parsing.md`
- `artifacts/claude-devtools/deepwiki/pages-md/4.4-caching-strategy.md`
- `artifacts/claude-devtools/deepwiki/pages-md/13-session-analysis-and-reporting.md`
- `artifacts/claude-devtools/deepwiki/pages-md/13.1-session-analyzer.md`
- `artifacts/claude-devtools/deepwiki/pages-md/13.2-cost-and-pricing.md`
- `artifacts/claude-devtools/deepwiki/pages-md/14.1-electronapi-interface.md`
- `artifacts/claude-devtools/deepwiki/pages-md/14.2-ipc-handler-reference.md`
- `artifacts/claude-devtools/deepwiki/pages-md/14.3-service-context-api.md`
- `artifacts/claude-devtools/deepwiki/pages-md/14.4-path-utilities.md`
- `artifacts/claude-devtools/deepwiki/pages-md/16-glossary.md`

1차 source verification paths used:

- `repos/claude-devtools/package.json`
- `repos/claude-devtools/README.md`
- `repos/claude-devtools/src/main/index.ts`
- `repos/claude-devtools/src/main/ipc/handlers.ts`
- `repos/claude-devtools/src/main/ipc/sessions.ts`
- `repos/claude-devtools/src/main/services/infrastructure/ServiceContext.ts`
- `repos/claude-devtools/src/main/services/infrastructure/ServiceContextRegistry.ts`
- `repos/claude-devtools/src/main/services/infrastructure/DataCache.ts`
- `repos/claude-devtools/src/main/services/discovery/ProjectScanner.ts`
- `repos/claude-devtools/src/main/services/discovery/SubagentResolver.ts`
- `repos/claude-devtools/src/main/services/parsing/SessionParser.ts`
- `repos/claude-devtools/src/main/services/parsing/MessageClassifier.ts`
- `repos/claude-devtools/src/main/services/analysis/ChunkBuilder.ts`
- `repos/claude-devtools/src/main/services/analysis/ConversationGroupBuilder.ts`
- `repos/claude-devtools/src/main/utils/jsonl.ts`
- `repos/claude-devtools/src/main/utils/pathDecoder.ts`
- `repos/claude-devtools/src/main/types/messages.ts`
- `repos/claude-devtools/src/main/types/chunks.ts`
- `repos/claude-devtools/src/preload/index.ts`
- `repos/claude-devtools/src/preload/constants/ipcChannels.ts`
- `repos/claude-devtools/src/shared/types/api.ts`
- `repos/claude-devtools/src/shared/utils/tokenFormatting.ts`
- `repos/claude-devtools/src/renderer/store/index.ts`
- `repos/claude-devtools/src/renderer/types/contextInjection.ts`
- `repos/claude-devtools/src/renderer/utils/contextTracker.ts`

1차 source-verified corrections:

- The durable architecture primitive is `ServiceContext` + `ServiceContextRegistry`, not just a generic multi-context description.
- `pathDecoder.ts` explicitly says encoded-path decoding is lossy for paths with dashes; current source prefers `cwd` hints when available.
- `get-session-detail` strips raw `messages` and subagent `messages` before IPC transfer and returns a fingerprint so renderer refreshes can short-circuit unchanged sessions.
- `DataCache` is in-memory LRU/TTL with version and optional file fingerprint invalidation, not a persistent parsed-session cache.
- `calculateMetrics()` currently sums token counts but does not compute actual USD pricing; `costUsd` is normally undefined.
- The DeepWiki `13.1-session-analyzer.md` baseline has no extracted source refs, and current checkout has no `src/main/services/analysis/SessionAnalyzer.ts`; session analysis is distributed across parser/classifier/chunk/context-tracker modules.

## 2차 후속: Product UI and interaction model

Scope:

- App shell
- Session views
- Command palette
- Settings interface
- Real-time updates

DeepWiki pages to reference:

- `artifacts/claude-devtools/deepwiki/pages-md/9-user-interface.md`
- `artifacts/claude-devtools/deepwiki/pages-md/9.1-application-shell.md`
- `artifacts/claude-devtools/deepwiki/pages-md/9.2-session-views.md`
- `artifacts/claude-devtools/deepwiki/pages-md/9.3-command-palette.md`
- `artifacts/claude-devtools/deepwiki/pages-md/9.4-settings-interface.md`
- `artifacts/claude-devtools/deepwiki/pages-md/9.5-real-time-updates.md`

Source verification candidates:

- `repos/claude-devtools/src/renderer/App.tsx`
- `repos/claude-devtools/src/renderer/main.tsx`
- `repos/claude-devtools/src/renderer/components/chat/`
- `repos/claude-devtools/src/renderer/components/layout/`
- `repos/claude-devtools/src/renderer/components/sidebar/`
- `repos/claude-devtools/src/renderer/components/settings/`
- `repos/claude-devtools/src/renderer/components/common/`
- `repos/claude-devtools/src/renderer/store/slices/`
- `repos/claude-devtools/src/renderer/hooks/`
- `repos/claude-devtools/src/renderer/utils/`

Suggested wiki outputs:

- `wiki/concepts/claude-devtools-ui-session-exploration-model.md`
- `wiki/concepts/claude-devtools-command-settings-realtime-ui.md`

## 3차 후속: External surfaces and environment integration

Scope:

- SSH remote access
- HTTP sidecar server
- Notification system
- Configuration management
- Claude root detection

DeepWiki pages to reference:

- `artifacts/claude-devtools/deepwiki/pages-md/5-ssh-remote-access.md`
- `artifacts/claude-devtools/deepwiki/pages-md/5.1-ssh-connection-manager.md`
- `artifacts/claude-devtools/deepwiki/pages-md/5.2-ssh-configuration.md`
- `artifacts/claude-devtools/deepwiki/pages-md/5.3-remote-file-operations.md`
- `artifacts/claude-devtools/deepwiki/pages-md/6-notification-system.md`
- `artifacts/claude-devtools/deepwiki/pages-md/6.1-notification-manager.md`
- `artifacts/claude-devtools/deepwiki/pages-md/6.2-trigger-system.md`
- `artifacts/claude-devtools/deepwiki/pages-md/6.3-filtering-and-throttling.md`
- `artifacts/claude-devtools/deepwiki/pages-md/7-configuration-management.md`
- `artifacts/claude-devtools/deepwiki/pages-md/7.1-config-ipc-handlers.md`
- `artifacts/claude-devtools/deepwiki/pages-md/7.2-claude-root-detection.md`
- `artifacts/claude-devtools/deepwiki/pages-md/8-http-sidecar-server.md`

Source verification candidates:

- `repos/claude-devtools/src/main/services/infrastructure/SshConnectionManager.ts`
- `repos/claude-devtools/src/main/services/infrastructure/SshFileSystemProvider.ts`
- `repos/claude-devtools/src/main/services/infrastructure/SshConfigParser.ts`
- `repos/claude-devtools/src/main/services/infrastructure/HttpServer.ts`
- `repos/claude-devtools/src/main/http/`
- `repos/claude-devtools/src/main/ipc/ssh.ts`
- `repos/claude-devtools/src/main/ipc/config.ts`
- `repos/claude-devtools/src/main/ipc/notifications.ts`
- `repos/claude-devtools/src/main/services/infrastructure/ConfigManager.ts`
- `repos/claude-devtools/src/main/services/infrastructure/NotificationManager.ts`
- `repos/claude-devtools/src/main/services/infrastructure/TriggerManager.ts`

Suggested wiki outputs:

- `wiki/concepts/claude-devtools-ssh-remote-access.md`
- `wiki/concepts/claude-devtools-notification-http-and-config-boundary.md`

## 4차 후속: Build, quality, release, contribution workflow

Scope:

- Getting started
- Build system
- Dependency management
- Testing
- CI pipeline
- Release/distribution
- Code signing/notarization
- Auto-updates
- Contributing and adding IPC methods

DeepWiki pages to reference:

- `artifacts/claude-devtools/deepwiki/pages-md/2-getting-started.md`
- `artifacts/claude-devtools/deepwiki/pages-md/10-build-system.md`
- `artifacts/claude-devtools/deepwiki/pages-md/10.1-electron-vite-configuration.md`
- `artifacts/claude-devtools/deepwiki/pages-md/10.2-native-module-handling.md`
- `artifacts/claude-devtools/deepwiki/pages-md/10.3-dependency-management.md`
- `artifacts/claude-devtools/deepwiki/pages-md/11-testing.md`
- `artifacts/claude-devtools/deepwiki/pages-md/11.1-unit-tests.md`
- `artifacts/claude-devtools/deepwiki/pages-md/11.2-ci-pipeline.md`
- `artifacts/claude-devtools/deepwiki/pages-md/12-release-and-distribution.md`
- `artifacts/claude-devtools/deepwiki/pages-md/12.1-release-workflow.md`
- `artifacts/claude-devtools/deepwiki/pages-md/12.2-code-signing-and-notarization.md`
- `artifacts/claude-devtools/deepwiki/pages-md/12.3-auto-updates.md`
- `artifacts/claude-devtools/deepwiki/pages-md/15-contributing.md`
- `artifacts/claude-devtools/deepwiki/pages-md/15.1-development-setup.md`
- `artifacts/claude-devtools/deepwiki/pages-md/15.2-adding-ipc-methods.md`
- `artifacts/claude-devtools/deepwiki/pages-md/15.3-code-style-and-quality.md`

Source verification candidates:

- `repos/claude-devtools/package.json`
- `repos/claude-devtools/pnpm-lock.yaml`
- `repos/claude-devtools/pnpm-workspace.yaml`
- `repos/claude-devtools/electron.vite.config.ts`
- `repos/claude-devtools/vite.standalone.config.ts`
- `repos/claude-devtools/vitest.config.ts`
- `repos/claude-devtools/vitest.critical.config.ts`
- `repos/claude-devtools/eslint.config.js`
- `repos/claude-devtools/.github/workflows/ci.yml`
- `repos/claude-devtools/.github/workflows/release.yml`
- `repos/claude-devtools/resources/`
- `repos/claude-devtools/build/`
- `repos/claude-devtools/CONTRIBUTING.md`

Suggested wiki outputs:

- `wiki/concepts/claude-devtools-build-test-release-pipeline.md`
- `wiki/concepts/claude-devtools-ipc-extension-workflow.md`

## 5차 후속: Consolidation and judgment layer

Scope:

- Update `wiki/projects/claude-devtools.md` after 2차~4차.
- Add compact `Taste Notes` only after enough source-verified subsystems exist.
- Extract reusable patterns and comparison hooks.

Possible comparison targets already in wiki:

- `wiki/projects/claude-code-history-viewer.md`
- `wiki/projects/codeburn.md`
- `wiki/projects/tokscale.md`

Potential outputs:

- `wiki/concepts/stealable-pattern-local-first-ai-session-log-inspection.md`
- `wiki/comparisons/claude-code-session-observability-tools.md`

## 아직 source-verified 하지 않은 영역

The following DeepWiki areas remain baseline-only after 1차:

- UI components, session views, command palette, settings UI, and realtime update rendering details.
- SSH remote connection behavior and SFTP/file-operation semantics.
- HTTP sidecar route surface and security/port behavior.
- Notification trigger matching, throttling, persistence, and click behavior.
- Config persistence, WSL Claude root detection, and settings mutation boundaries.
- Build/test/CI/release/signing/auto-update behavior.
- Contribution workflow and adding IPC methods beyond the existing core IPC shape.
