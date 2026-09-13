# peers/peerjs initial capture

## Scope

- Repository: `https://github.com/peers/peerjs`
- Local checkout: `repos/peerjs`
- Artifact root: `artifacts/peerjs`
- Report type: initial capture + small source-verified surface check. DeepWiki content is treated only as an external baseline until source-verified.

## Completed capture work

### DeepWiki baseline

Extraction command completed successfully:

```text
[start] peers/peerjs
[index] OK
[toc] 19
[match] 19/19
[write] OK
Done: 19/19 missing=0
```

Saved under:

- `artifacts/peerjs/deepwiki/raw/index.html`
- `artifacts/peerjs/deepwiki/toc.json`
- `artifacts/peerjs/deepwiki/toc.md`
- `artifacts/peerjs/deepwiki/manifest.json`
- `artifacts/peerjs/deepwiki/pages-md/`
- `artifacts/peerjs/deepwiki/pages-meta/`
- `artifacts/peerjs/deepwiki/completeness-check.json`

Completeness verification (`artifacts/peerjs/deepwiki/completeness-check.json`):

```json
{
  "toc_count": 19,
  "manifest_missing_pages_count": 0,
  "filesystem_pages_md_count": 19,
  "filesystem_pages_meta_count": 19,
  "missing_md_slugs": [],
  "missing_meta_slugs": [],
  "complete": true
}
```

DeepWiki TOC includes high-level sections `Overview`, `Architecture`, `Core Classes`, `Utilities and Support`, and `Development` (`artifacts/peerjs/deepwiki/toc.md:3-21`).

### Local clone / metadata

- Clone path: `repos/peerjs`
- Remote: `https://github.com/peers/peerjs.git`
- Branch: `master`
- HEAD: `125f450c547887982ddecc86a6719f22e0f8f952`
- Describe: `v1.5.5-3-g125f450`
- Latest commit: `chore(deps): update swc monorepo (#1344)` by `renovate[bot]`, `2025-07-18T03:51:13Z`
- Metadata artifact: `artifacts/peerjs/repo-metadata.txt`

### GitHub/static artifacts

Created:

- `artifacts/peerjs/github-metadata.json`
- `artifacts/peerjs/static-analysis/tracked-files.txt`
- `artifacts/peerjs/static-analysis/tracked-files-count.txt`
- `artifacts/peerjs/static-analysis/top-level-file-counts.txt`
- `artifacts/peerjs/static-analysis/source-tree-counts.txt`
- `artifacts/peerjs/static-analysis/extension-counts.txt`
- `artifacts/peerjs/static-analysis/tokei.txt`
- `artifacts/peerjs/static-analysis/tokei.json`
- `artifacts/peerjs/static-analysis/initial-capture-summary.json`

Tracked-file footprint from `git ls-files`:

- Total tracked files: `100`
- Top-level split: `e2e` 48, `lib` 28, root files 13, `.github` 6, `__test__` 5 (`artifacts/peerjs/static-analysis/top-level-file-counts.txt`)
- Main extension mix: `.ts` 46, `.js` 24, `.json` 7, `.html` 7, `.yml` 6 (`artifacts/peerjs/static-analysis/extension-counts.txt`)
- Dominant subtrees: `e2e/datachannel` 27, `lib/<direct>` 18, `lib/dataconnection` 8 (`artifacts/peerjs/static-analysis/source-tree-counts.txt`)
- `tokei` summary: 87 counted files, 36,365 lines total; major languages are TypeScript 46 files / 4,006 lines, JavaScript 25 files / 1,984 lines, JSON 6 files / 29,491 lines (`artifacts/peerjs/static-analysis/tokei.txt:2-18`).

## Source-verified initial facts

1. **Project positioning:** README describes PeerJS as “a complete, configurable, and easy-to-use peer-to-peer API built on top of WebRTC” supporting data channels and media streams (`repos/peerjs/README.md:1-8`).
2. **Package/runtime surface:** `package.json` identifies the npm package as `peerjs` version `1.5.5`, description `PeerJS client`, license MIT, Node engine `>= 14`, and published outputs `dist/bundler.cjs`, `dist/bundler.mjs`, and `dist/types.d.ts` (`repos/peerjs/package.json:1-19`, `106-114`).
3. **Build entrypoints:** Parcel targets compile from `lib/exports.ts` for CJS/ESM/types, from `lib/global.ts` for browser global bundles, and from `lib/dataconnection/StreamConnection/MsgPack.ts` for the MessagePack serializer bundle (`repos/peerjs/package.json:115-161`).
4. **Public module API:** `lib/exports.ts` exports `Peer`, `MsgPackPeer`, core connection types, serializer classes, enums, `PeerError`, and default export `Peer` (`repos/peerjs/lib/exports.ts:1-27`).
5. **Browser global API:** browser global bundle assigns `window.peerjs = { Peer, util }` and deprecated `window.Peer = Peer` (`repos/peerjs/lib/global.ts:1-9`).
6. **Peer construction and signaling setup:** `Peer` defaults to cloud host/port/path/key, configures token/config/referrer policy, builds `API` and `Socket`, validates WebRTC support and IDs, then either initializes with a supplied ID or retrieves one via API (`repos/peerjs/lib/peer.ts:225-298`).
7. **Server transport:** `Socket` builds a WebSocket URL from protocol/host/port/path/key, starts with `id`, `token`, and `version`, JSON-parses server messages, queues messages until an ID exists, and sends heartbeat messages on a timer (`repos/peerjs/lib/socket.ts:18-44`, `45-57`, `87-148`).
8. **HTTP API surface:** `API.retrieveId()` calls the PeerServer `id` endpoint; `API.listAllPeers()` calls the deprecated `peers` endpoint and reports permission guidance for cloud/self-hosted servers (`repos/peerjs/lib/api.ts:9-30`, `50-85`).
9. **Core connection APIs:** `Peer.connect()` creates a serializer-backed `DataConnection`; `Peer.call()` creates a `MediaConnection` from a supplied `MediaStream`; both refuse new connections after server disconnect (`repos/peerjs/lib/peer.ts:485-555`).
10. **Data connections:** `DataConnection` wraps a WebRTC `RTCDataChannel`, assigns `dc_` connection IDs, starts a `Negotiator`, emits `open`, exposes `send`, and handles answer/candidate signaling messages (`repos/peerjs/lib/dataconnection/DataConnection.ts:28-63`, `65-84`, `127-160`).
11. **Media connections:** `MediaConnection` wraps media streams, assigns `mc_` connection IDs, starts negotiation when a local stream is present, emits `stream` when remote tracks arrive, and answers incoming calls via `answer()` (`repos/peerjs/lib/mediaconnection.ts:27-70`, `86-91`, `115-151`).
12. **Negotiation mechanics:** `Negotiator` creates `RTCPeerConnection`, adds tracks for media, creates a data channel for originators, emits ICE candidates to the PeerServer socket, wires datachannel/track listeners, and closes peer/data channels in cleanup (`repos/peerjs/lib/negotiator.ts:13-49`, `51-88`, `129-159`, `161-191`).
13. **CI/test surface:** GitHub CI runs Node 16/18/20 with `npm ci`, `npm run check`, `npm run build`, and `npm run coverage` (`repos/peerjs/.github/workflows/test.yml:16-32`). BrowserStack workflow builds with `npm install && npm run build`, starts `http-server`, and runs `npm run e2e:bstack` with BrowserStack credentials (`repos/peerjs/.github/workflows/browserstack.yml:11-38`).
14. **Browser support docs/source drift:** README states official support as Firefox 80+, Chrome 83+, Edge 83+, Safari 15+ and notes Firefox 102+ for CBOR/MessagePack (`repos/peerjs/README.md:120-132`). The source `Supports` helper currently lists browser names `firefox`, `chrome`, `safari` and minimum versions Firefox 59, Chrome 72, Safari WebKit 605 (`repos/peerjs/lib/supports.ts:7-35`); treat README as user-facing support policy and `supports.ts` as runtime feature gate.
15. **Version-generation drift:** checkout `lib/version.ts` initially contained `1.5.4`, while package version is `1.5.5`. `npm run build` runs `build:version` and rewrites `lib/version.ts` to `1.5.5`; this mutation was captured then cleaned (`artifacts/peerjs/static-analysis/post-build-working-tree.txt`, `artifacts/peerjs/static-analysis/post-build-cleanup-status.txt`).

## Verification commands run

Artifacts:

- Dependency install log: `artifacts/peerjs/static-analysis/npm-ci.log`
- Type-check log: `artifacts/peerjs/static-analysis/npm-run-check.log`
- Jest log: `artifacts/peerjs/static-analysis/npm-test-runInBand.log`
- Build log: `artifacts/peerjs/static-analysis/npm-run-build.log`
- Post-build mutation note: `artifacts/peerjs/static-analysis/post-build-working-tree.txt`
- Cleanup status: `artifacts/peerjs/static-analysis/post-build-cleanup-status.txt`

Observed results:

```text
npm ci: exit 0; installed 1673 packages; npm audit summary reported 59 vulnerabilities (7 low, 19 moderate, 28 high, 5 critical).
npm run check: exit 0.
npm test -- --runInBand: exit 0; 3 test suites passed, 9 passed, 1 skipped, 10 total.
npm run build: exit 0; Parcel built dist/types.d.ts, dist/bundler.cjs, dist/bundler.mjs, dist/peerjs.min.js, dist/peerjs.js, dist/serializer.msgpack.mjs.
```

Build warnings/context:

- `npm ci` emitted deprecated package warnings and `allow-scripts` review warnings for several packages; install still completed.
- `npm ci` audit summary reported vulnerabilities; no remediation was applied in this capture.
- `npm run build` emitted `Opening /dev/tty failed (6): Device not configured` and stale Browserslist-data warnings, but completed successfully.
- Build changed tracked `lib/version.ts` from `1.5.4` to `1.5.5`; I restored it and removed generated `dist/`, leaving `git status --short` empty afterward.

## DeepWiki baseline claims not yet source-verified

The extracted DeepWiki pages are available and complete, but this initial capture only verified high-leverage source/runtime surfaces above. The detailed DeepWiki sections on architecture, connection flow, serialization, individual classes, and utilities should still be treated as hypotheses until compared page-by-page against `repos/peerjs`.

## Recommended next steps

1. Write a source-verified architecture report comparing `artifacts/peerjs/deepwiki/pages-md/2-architecture.md` and `2.2-connection-flow.md` against `lib/peer.ts`, `lib/socket.ts`, `lib/negotiator.ts`, and connection classes.
2. Run graphify after this DeepWiki baseline if a local code graph is needed; store it under `artifacts/peerjs/graphify/` and verify any graph summary against source.
3. Do a focused dependency/security pass on the 59 `npm audit` findings before interpreting them as project risk.
4. Decide whether to update the long-term `wiki/` after the DeepWiki architecture claims are source-verified.
