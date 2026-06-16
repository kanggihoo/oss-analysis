---
repo: Understand-Anything
local_checkout: /Users/kkh/Desktop/oss-analysis/repos/Understand-Anything
verification_commit: 7a3b7511b26a1816be3b6cc5683b34779e0abce9
baseline_artifacts:
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/2-understand-anything-pipeline.md
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/3-understand-anything-core.md
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/4-understand-anything-dashboard.md
---

# Gemini baseline vs current source comparison

## Method

Baseline files were read from `artifacts/Understand-Anything/gemini/`. Claims below are treated as hypotheses and verified against current source at commit `7a3b7511b26a1816be3b6cc5683b34779e0abce9`.

## Pipeline claims

| Baseline claim | Current source evidence | Verdict |
|---|---|---|
| `/understand` is a 7-phase hybrid deterministic + LLM pipeline. | `skills/understand/SKILL.md` defines phases: scan, batch, analyze, assemble review, architecture, tour, review/save. Deterministic scripts include `scan-project.mjs`, `extract-import-map.mjs`, `compute-batches.mjs`, `extract-structure.mjs`, `merge-batch-graphs.py`. | confirmed, with current-source additions |
| Project scan uses git ls-files fallback walk, `.understandignore`, language/category detection. | `scan-project.mjs:5-24`, `17-24`, plus `/understand` ignore gate `SKILL.md:194-231`. | confirmed |
| Import map uses PluginRegistry + TreeSitterPlugin, resolves TS aliases/index files and filters external packages. | `extract-import-map.mjs:5-13`, `61`; tsconfig parsing/resolution comments at `115-180`. | confirmed |
| Batch analysis considers file size/line count and import coupling. | `/understand` runs `compute-batches.mjs` (`SKILL.md:280-293`); script uses import graph + Louvain (`compute-batches.mjs:3-12`) and extracts exports for neighborMap (`42-87`). | confirmed |
| Merge script normalizes IDs/complexity and drops dangling edges. | `SKILL.md:343-359`; `merge-batch-graphs.py:32-76`, `178-220`. | confirmed |
| `tested_by` edges are recovered by file naming/mirroring. | `/understand` explicitly states two-pass tested_by linker and production→test direction (`SKILL.md:357`). | confirmed |
| `assemble-reviewer`, `architecture-analyzer`, `tour-builder` are LLM agents. | `SKILL.md:391-414`, `418-488`, `501-570`; corresponding `agents/*.md` exist. | confirmed |
| `graph-reviewer` is final validation gate. | Default path uses inline deterministic validator (`SKILL.md:613-680`); `graph-reviewer` only when `--review` is passed (`694-718`). | corrected |
| `/understand-domain` uses existing graph or lightweight context scan and saves `domain-graph.json`. | `skills/understand-domain/SKILL.md:11-15`, `89-110`, `123-140`. | confirmed |
| `/understand-knowledge` parses Karpathy wiki, uses article-analyzer, merge-knowledge-graph, dashboard. | `skills/understand-knowledge/SKILL.md:11-20`, `30-50`, `52-90`, `91-125`. | confirmed |
| Auto-update is based on staleness, git diff, fingerprints, decision matrix. | `hooks/hooks.json:3-24`, `hooks/auto-update-prompt.md:19-33`, `94-149`, `change-classifier.ts:4-21`, `55-84`. | confirmed, but hook routing corrected |

## Core claims

| Baseline claim | Current source evidence | Verdict |
|---|---|---|
| NodeType has 21 values. | `types.ts:1-7`. | confirmed |
| EdgeType has 35 values. | `types.ts:9-19`, `schema.ts:3-14`. | confirmed |
| Pipeline baseline’s graph-reviewer section says 16 node types. | Current `types.ts` has 21 node types. | corrected/stale |
| sanitize → autoFix → normalize → validate flow exists. | `schema.ts:148`, `196`, `462`, `499`. | confirmed |
| Alias mappings canonicalize `func/fn`, `doc/readme`, `extends/invokes`, etc. | `schema.ts:16-120`. | confirmed |
| `.understand-anything` stores `knowledge-graph.json`, `meta.json`, `fingerprints.json`, `config.json`; domain graph also exists. | `persistence/index.ts:8-11`, `152-157`. | confirmed |
| `sanitiseFilePaths` prevents absolute local path leak. | `persistence/index.ts:36-40`, `74-79`, `152-157`; dashboard serving also sanitizes graph JSON `vite.config.ts:308-333`. | confirmed |
| `GraphBuilder` has addFile/addFileWithAnalysis/addNonCodeFileWithAnalysis/build. | `graph-builder.ts:60-63`, `84-87`, `105-108`, `228-231`, `320-323`. | confirmed |
| TreeSitterPlugin exposes analyzeFile/extractCallGraph/resolveImports with web-tree-sitter. | `tree-sitter-plugin.ts:31-33`, `124-127`, `221-295`. | confirmed |
| 12 non-code parsers. | `plugins/parsers/index.ts:1-12`, `31-44`. | confirmed |
| DomainMeta fields include `description`, `flowType`, `order`, `inputs`, `outputs`, `triggers`, `involvedActors`. | Current `DomainMeta` is `entities`, `businessRules`, `crossDomainInteractions`, `entryPoint`, `entryType` (`types.ts:29-36`). | corrected |

## Dashboard claims

| Baseline claim | Current source evidence | Verdict |
|---|---|---|
| Dashboard is Vite/React SPA. | `packages/dashboard/package.json:6-12`, `14-42`; `src/App.tsx`. | confirmed |
| Protected local endpoints include graph/domain/diff/file/config. | `vite.config.ts:250-256`; current source also includes `/meta.json`. | confirmed + added endpoint |
| Access token is env or random hex; token query required. | `vite.config.ts:9-13`, `185-191`, `263-268`. | confirmed |
| File content pipeline prevents traversal, non-graph files, >1MB, binary. | `vite.config.ts:114-177`, allowlist `55-69`, size `13`, `159-165`. | confirmed |
| Dashboard binds only localhost. | `vite.config.ts:185-189`. | confirmed |
| Graph load uses schema validation and warning/error handling. | `App.tsx:134-139`, `195-200`. | confirmed |
| ReactFlow + ELK structural layout. | ReactFlow in `GraphView.tsx`; ELK in `utils/elk-layout.ts:1`, `214`; build split in `vite.config.ts:210-213`. | confirmed |
| DomainGraphView uses D3 force layout. | Current `DomainGraphView.tsx` imports `mergeElkPositions`/`nodesToElkInput` from `utils/layout.ts`; `KnowledgeGraphView.tsx` directly uses `applyForceLayout` (`16`, `86`). | partially confirmed / corrected nuance |
| KnowledgeGraphView styles knowledge edges and filters knowledge node types. | `KnowledgeGraphView.tsx:26-31`, `124-128`, `246-292`. | confirmed |
| Zustand store caches maps and tracks node selection/search/persona/detail. | `store.ts:54-95`, `100-170`, `365-380`, `520-539`. | confirmed |
| Lazy components include LearnPanel, CodeViewer, PathFinderModal, OnboardingOverlay. | `App.tsx:28-35`, usage `395-400`, `657-681`, `697-707`. | confirmed |
| Theme/i18n supports en/ko/ja/zh/zh-TW/ru and CSS variables. | `locales/index.ts:1-33`, `theme-engine.ts:13-21`, `33-36`. | confirmed |

## 핵심 차이 요약

1. `/understand` command routing은 `.claude/commands`가 아니라 `understand-anything-plugin/skills/*/SKILL.md`와 platform plugin manifest 기반이다.
2. `graph-reviewer`는 항상 실행되는 final gate가 아니다. 기본 경로는 inline deterministic validator이고, LLM reviewer는 `--review`일 때 실행된다.
3. Pipeline에는 Gemini baseline보다 더 구체적인 Phase 0.5 `.understandignore` confirmation gate, Phase 1.5 Louvain/neighborMap batching, fingerprint baseline before `meta.json`, `scan-result.json` 보존 cleanup이 있다.
4. `DomainMeta` baseline interface는 current source와 다르다. 현재는 `entities/businessRules/crossDomainInteractions/entryPoint/entryType` 중심이다.
5. Dashboard endpoint set에는 baseline에 없는 `/meta.json`도 token-protected로 포함되고, graph JSON serving path에서도 absolute filePath sanitization을 수행한다.

## Source에서 찾지 못했거나 nuance가 필요한 claim

- Pipeline baseline의 “architecture structural metrics script”는 `/understand` source에서 독립 script path로 확인하지 못했다. 현재 확인된 것은 architecture-analyzer LLM dispatch와 normalization 규칙이다.
- Dashboard baseline의 “DomainGraphView = D3 force”는 current code에서 direct import로는 확인되지 않았다. D3 force는 shared layout/KnowledgeGraphView 경로에서 확인되고, DomainGraphView는 ELK helper를 import한다.
- “SemanticSearchEngine cosine similarity”는 core에 embedding/search 관련 파일이 있지만 dashboard store의 직접 경로는 `SearchEngine`이다. semantic mode가 실제로 어떻게 연결되는지는 추가 focused trace가 필요하다.
