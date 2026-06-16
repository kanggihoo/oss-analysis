---
repo: Understand-Anything
local_checkout: /Users/kkh/Desktop/oss-analysis/repos/Understand-Anything
verification_commit: 7a3b7511b26a1816be3b6cc5683b34779e0abce9
baseline_artifacts:
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/2-understand-anything-pipeline.md
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/3-understand-anything-core.md
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/4-understand-anything-dashboard.md
---

# Understand-Anything dashboard verification

## 1. Package and runtime boundary

Dashboard는 `@understand-anything/dashboard` Vite/React app이다. `package.json`은 `vite`, `react@19`, `@xyflow/react`, `elkjs`, `d3-force`, `zustand`, `prism-react-renderer`, `react-markdown`, `@understand-anything/core`를 선언한다(`packages/dashboard/package.json:14-42`). Build script는 `tsc -b && vite build`다(`6-12`).

실제 build 검증: `pnpm --filter @understand-anything/dashboard build` 성공. Vite output은 성공했지만 `elk` chunk가 1,438.65 kB라서 chunk-size warning이 있었다.

## 2. Local API middleware and protected endpoints

Vite middleware는 `packages/dashboard/vite.config.ts`에 정의된다.

- Access token: `UNDERSTAND_ACCESS_TOKEN` 환경변수가 있으면 사용하고, 없으면 `crypto.randomBytes(16).toString("hex")`로 session token을 생성한다(`vite.config.ts:9-13`).
- Server bind: `host: "127.0.0.1"`, `port: 5173`, browser open URL은 `/?token=${ACCESS_TOKEN}`다(`185-191`).
- Console output: listening 시 `http://127.0.0.1:<port>/?token=<token>`를 출력한다(`238-244`).
- Protected endpoints: `/knowledge-graph.json`, `/domain-graph.json`, `/diff-overlay.json`, `/meta.json`, `/config.json`, `/file-content.json`가 token protected다(`247-256`).
- Token mismatch: query token이 다르면 403 JSON을 반환한다(`263-268`).

Gemini baseline이 말한 `/knowledge-graph.json`, `/domain-graph.json`, `/diff-overlay.json`, `/file-content.json`, `/config.json`은 confirmed이며, current source에는 `/meta.json`도 protected endpoint로 추가되어 있다.

## 3. File-content security pipeline

`readSourceFile(url)`은 `vite.config.ts:114-177`에 있다. Baseline의 path traversal/local file read security claim은 대부분 confirmed다. Current source evidence:

1. Missing path / null byte reject: `115-118`.
2. Requested absolute path reject: `118`.
3. `path.normalize` and `..`/absolute recheck: `120-128`.
4. `knowledge-graph.json` 존재 요구: `130-133`.
5. Project root derived from graph file and `path.resolve` root binding: `135-146`.
6. Graph-derived allowlist: `graphFilePathSet(...).has(safeRelativePath)` 아니면 404(`147-149`). Allowlist는 graph node `filePath`들을 normalize해 만든다(`55-69`).
7. `fs.statSync` + `isFile`: `151-158`.
8. 1MB limit: `MAX_SOURCE_FILE_BYTES = 1024 * 1024`(`13`), reject 413(`159-161`).
9. Binary/null byte buffer reject: `163-165`.
10. Response includes safe relative path, language, content, sizeBytes, lineCount(`166-175`).

Nuance/correction: graph JSON serving path에서는 absolute filePath를 client에 보내기 전에 projectRoot-relative로 바꾸거나 외부 absolute path는 basename만 남긴다(`308-333`). 반면 `/file-content.json` 요청 자체는 absolute requested path를 무조건 거부한다(`118`).

## 4. Graph load validation and app shell

`App.tsx`는 graph load 후 core `validateGraph`를 호출한다. Code graph load는 `validateGraph(data)` 성공 시 `setGraph(result.data)`와 `setGraphIssues(result.issues)`를 호출한다(`App.tsx:134-139`). Domain graph도 동일하게 검증한다(`195-200`).

TokenGate는 token이 없을 때 표시된다(`App.tsx:100-103`). Heavy/optional components는 React `lazy`로 분리된다: `CodeViewer`, `LearnPanel`, `PathFinderModal`, `KeyboardShortcutsHelp`, `OnboardingOverlay`(`App.tsx:28-35`). Code viewer는 bottom slide-up과 modal 두 presentation을 지원한다(`657-681`).

Sidebar behavior는 current source 주석과 JSX에서 확인된다. NodeInfo가 우선이고 Learn mode에서는 LearnPanel을 추가하며, idle/non-learn에서는 ProjectOverview를 보여준다(`App.tsx:388-400`).

## 5. Zustand store

Store는 `packages/dashboard/src/store.ts`의 `useDashboardStore`다. 주요 source evidence:

- `buildGraphIndexes`가 `nodesById`, `nodeIdToLayerId`, `nodeIdToLayerIds`를 만든다(`store.ts:54-95`). `nodeIdToLayerId`는 first matching layer wins, `nodeIdToLayerIds`는 all membership을 보존한다(`61-72`).
- State에는 `graph`, lookup maps, `selectedNodeId`, `searchQuery`, `searchResults`, `persona`, `diffMode`, `detailLevel` 등이 있다(`100-170`).
- Default persona는 `junior`, detailLevel은 `file`이다(`289-310`, `342-348`).
- `setGraph`는 `SearchEngine`을 만들고 기존 search query에 대한 results를 재계산하며 indexes를 store에 저장한다(`365-380`).
- `selectNode`와 history는 `396-412` 이후, `setSearchQuery`는 `520-532`, persona change는 layout caches reset과 함께 `534-539`에서 처리된다.

Gemini baseline의 Zustand store claim은 confirmed다. 다만 baseline의 “SemanticSearchEngine cosine similarity”는 현재 store path에서 확인된 primary evidence는 `SearchEngine` 사용(`store.ts:365-367`, `520-523`)이다. 별도 embedding search module은 core에 존재하지만 대시보드 store의 현재 search path는 source를 더 좁혀 해석해야 한다.

## 6. Structural graph: ReactFlow + containers + ELK + edge aggregation

`GraphView.tsx`가 structural/codebase graph를 렌더링한다.

- ReactFlow node types에는 custom, layer-cluster, portal, container가 포함된다(`GraphView.tsx:58-62`).
- `deriveContainers`를 import하고(`51-54`) filtered nodes/edges에서 containers/ungrouped를 산출한다(`476-480`).
- TourFitView와 SelectedNodeFitView가 ReactFlow viewport fitting을 담당한다(`95-98`, `181-185`, `1550-1551`).
- Portal node component는 import/registered되어 있다(`21-24`, `58-62`).

Container derivation은 `utils/containers.ts`가 담당하며 `detectCommunities` from `./louvain`를 import한다(`containers.ts:1-5`). `deriveContainers` entrypoint는 `containers.ts:91-94`다. Baseline의 LCP/fallback Louvain 설명은 관련 source가 존재하지만 세부 알고리즘 주장은 `containers.ts` 구현을 기준으로 읽어야 한다.

ELK layout은 `utils/elk-layout.ts`가 `elkjs/lib/elk.bundled.js`를 import한다(`elk-layout.ts:1`). ELK instance는 `const elk = new ELK()`(`214`)이며 fallback/repair utilities도 있다(`56` 이후). Build output에서 `elk`가 별도 chunk로 분리된 것도 `vite.config.ts:210-213`과 일치한다.

Edge aggregation/portal metadata는 `utils/edgeAggregation.ts`의 `PortalInfo`와 related functions에서 확인된다(`edgeAggregation.ts:10-13`, `79-84`).

## 7. Domain and knowledge graph layouts

Domain view는 `components/DomainGraphView.tsx`다. It uses `DomainClusterNode`, `FlowNode`, `StepNode` node types(`DomainGraphView.tsx:13-29`). Current source에서 이 파일은 `mergeElkPositions`, `nodesToElkInput`을 `utils/layout`에서 import한다(`21`). Baseline의 D3 force claim은 domain view 자체보다는 shared layout utility/knowledge view와 함께 봐야 한다.

Knowledge graph view는 `components/KnowledgeGraphView.tsx`다. It imports ReactFlow and `applyForceLayout`(`KnowledgeGraphView.tsx:1-17`), styles knowledge edges such as `cites`, `contradicts`, `builds_on`, `exemplifies`, `categorized_under`, `authored_by`(`26-31`), filters knowledge node types `article/entity/topic/claim/source`(`124-128`), and renders ReactFlow(`246-292`). Thus `/understand-knowledge` force-directed layout claim is confirmed.

Shared `applyForceLayout` is in `utils/layout.ts`; source search confirmed `KnowledgeGraphView.tsx` imports it, and build dependency includes `d3-force`(`packages/dashboard/package.json:18`).

## 8. Code viewer

`CodeViewer` is lazy-loaded(`App.tsx:29`) and receives `accessToken` in both bottom panel and modal forms(`657-681`). Dashboard package includes `prism-react-renderer` dependency(`packages/dashboard/package.json:25`), matching baseline claim. File content is fetched through the token-protected `/file-content.json` middleware described above, not by browser direct file access.

## 9. Theme and i18n

Theme engine is implemented in `themes/theme-engine.ts`. `applyTheme(config)` obtains preset/accent and writes CSS variables onto `document.documentElement.style`(`theme-engine.ts:33-36`). It also derives glass variables such as `glass-bg`, `glass-border`, `glow-accent` from accent RGB/opacity(`13-21`). Theme persistence is handled by ThemeContext/presets files; baseline’s `ua-theme` localStorage claim is consistent with source search, but the central evidence should be `themes/ThemeContext.tsx` plus `theme-engine.ts`.

Locales are explicit in `locales/index.ts`: `en`, `zh`, `zh-TW`, `ja`, `ko`, `ru` are imported/exported(`1-18`), and `resolveLocaleKey` maps browser/friendly language strings to canonical locale keys(`24-33`). Gemini baseline’s i18n language list is confirmed.
