 ---
repo: Understand-Anything
local_checkout: /Users/kkh/Desktop/oss-analysis/repos/Understand-Anything
verification_commit: 7a3b7511b26a1816be3b6cc5683b34779e0abce9
baseline_artifacts:
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/2-understand-anything-pipeline.md
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/3-understand-anything-core.md
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/4-understand-anything-dashboard.md
---

# Understand-Anything architecture

## 1. Monorepo와 배포 경계

현재 checkout의 root `package.json`은 private ESM workspace이며, root scripts는 `prepare`, `build`, `test`, `dev:dashboard`, `lint`만 제공한다(`package.json:2-35`). Workspace package 목록은 `pnpm-workspace.yaml:1-4`에 명시된 `understand-anything-plugin/packages/*`, `understand-anything-plugin`, `homepage`다.

중요한 점은 실제 분석 기능이 root `src/`가 아니라 `understand-anything-plugin/` 아래에 집중되어 있다는 것이다. `understand-anything-plugin/package.json:2-15`는 `@understand-anything/skill` 패키지를 정의하고, `@understand-anything/core`를 workspace dependency로 끌어온다.

```text
repos/Understand-Anything/
├── package.json / pnpm-workspace.yaml      # workspace orchestration
├── .claude-plugin/ .cursor-plugin/ ...     # platform plugin manifests
├── understand-anything-plugin/
│   ├── skills/                             # slash-command skill definitions + scripts
│   ├── agents/                             # LLM subagent prompt definitions
│   ├── hooks/                              # auto-update hook prompt/config
│   ├── src/                                # chat/diff/explain/onboard context helpers
│   └── packages/
│       ├── core/                           # schema, persistence, parsers, graph builder
│       └── dashboard/                      # Vite + React dashboard
├── homepage/                               # marketing/demo site package
└── tests/skill/                            # root vitest skill-script tests
```

## 2. Command / skill boundary

Slash command surface는 `understand-anything-plugin/skills/*/SKILL.md`로 구현된다. 현재 source inventory에서 `.claude/commands`는 존재하지 않았고, plugin manifests가 skills/agents 디렉터리를 참조한다. 예: Cursor manifest는 `skills: "./understand-anything-plugin/skills/"`, `agents: "./understand-anything-plugin/agents/"`를 선언한다(`.cursor-plugin/plugin.json:13-14`).

| Skill | Evidence | 역할 |
|---|---|---|
| `/understand` | `understand-anything-plugin/skills/understand/SKILL.md:7-18` | codebase graph 생성, auto-update config, review/language/subdirectory arguments |
| `/understand-domain` | `understand-anything-plugin/skills/understand-domain/SKILL.md:7-15` | existing graph 또는 lightweight scan 기반 business/domain graph 생성 |
| `/understand-knowledge` | `understand-anything-plugin/skills/understand-knowledge/SKILL.md:7-20` | Karpathy-pattern wiki graph 분석 |
| `/understand-dashboard` | `understand-anything-plugin/skills/understand-dashboard/SKILL.md` | dashboard 실행 |
| `/understand-chat`, `/understand-diff`, `/understand-explain`, `/understand-onboard` | `understand-anything-plugin/src/*.ts`, `skills/*/SKILL.md` | 저장된 graph를 context로 질의/차이/설명/onboarding 산출 |

## 3. Core 책임 경계

Core package는 browser-safe subpath exports를 제공한다. `packages/core/package.json:7-27`은 main entry 외에 `./search`, `./types`, `./schema`, `./languages` exports를 정의한다. 이 경계는 dashboard가 Node.js 파일 시스템 모듈을 끌어오지 않고 schema/search/types만 import할 수 있게 하는 설계다.

Core 내부 책임은 다음과 같이 나뉜다.

- `src/types.ts` — `KnowledgeGraph`, `GraphNode`, `GraphEdge`, `DomainMeta`, `KnowledgeMeta` 타입. NodeType 21개와 EdgeType 35개는 `types.ts:1-19`에서 선언된다.
- `src/schema.ts` — Zod validation, alias/fix/normalize/validate pipeline. Edge enum과 alias map은 `schema.ts:3-14`, `schema.ts:16-120`에 있다.
- `src/persistence/index.ts` — `.understand-anything` 파일 저장/로드와 path sanitization. 파일 상수는 `persistence/index.ts:8-11`, path sanitization은 `persistence/index.ts:36-40`, save 시 적용은 `persistence/index.ts:74-79`, domain graph save도 `persistence/index.ts:152-157`에서 적용된다.
- `src/plugins/tree-sitter-plugin.ts` — `web-tree-sitter` 기반 multi-language parser. class와 init/import/callgraph methods는 `tree-sitter-plugin.ts:31-33`, `124-127`, `221-256`, `277-295`에서 확인된다.
- `src/plugins/registry.ts` — plugin registration and dispatch. 등록과 languageMap override는 `registry.ts:20-24`, analyze/import/callgraph delegation은 `registry.ts:56-72`에서 확인된다.
- `src/plugins/parsers/` — Markdown/YAML/JSON/TOML/Env/Dockerfile/SQL/GraphQL/Protobuf/Terraform/Makefile/Shell 12개 built-in non-code parser를 `parsers/index.ts:1-12`, `31-44`에서 export/register한다.

## 4. Pipeline 책임 경계

`/understand`는 AI agent가 전부를 즉흥적으로 탐색하는 구조가 아니라, deterministic script와 LLM agent를 단계별로 분리한다. 대표 script evidence는 다음과 같다.

- `scan-project.mjs:5-24`: git/file enumeration, `.understandignore`, language/category detection, line counting, complexity estimation은 deterministic script가 담당한다. README/manifest로 high-level narrative를 만드는 부분은 LLM이 담당한다고 주석으로 분리한다(`scan-project.mjs:12-15`).
- `extract-import-map.mjs:5-13`: TreeSitterPlugin + non-code parsers로 raw imports를 뽑고 language-specific resolver로 project-internal importMap을 만든다.
- `compute-batches.mjs:3-12`: scan-result에서 import graph를 읽어 Louvain community batching과 neighborMap을 만든다.
- `extract-structure.mjs:5-16`, `65-73`, `97-123`: file-analyzer가 쓰는 deterministic structure extraction script.
- `merge-batch-graphs.py:3-19`, `32-76`, `178-220`: batch JSON을 ID/complexity/direction normalize 후 assembled graph로 병합한다.

LLM agent는 `agents/*.md`에 정의되어 있고 `/understand` skill에서 명시적으로 dispatch된다. Phase 3 assemble reviewer(`SKILL.md:391-414`), Phase 4 architecture analyzer(`418-488`), Phase 5 tour builder(`501-570`), optional full graph reviewer(`694-718`)가 여기에 해당한다.

## 5. Dashboard 책임 경계

Dashboard package는 local Vite middleware + React SPA다. `packages/dashboard/package.json:14-29`는 `@xyflow/react`, `elkjs`, `d3-force`, `zustand`, `prism-react-renderer`, `react-markdown` 의존성을 선언한다.

- Local API/security middleware: `packages/dashboard/vite.config.ts`.
- App shell, schema validation, lazy overlays: `packages/dashboard/src/App.tsx`.
- State store/indexes/search/persona/detail mode: `packages/dashboard/src/store.ts`.
- Structural graph: `components/GraphView.tsx` + `utils/containers.ts`, `utils/elk-layout.ts`, `utils/edgeAggregation.ts`.
- Domain graph: `components/DomainGraphView.tsx`, `DomainClusterNode.tsx`, `FlowNode.tsx`, `StepNode.tsx`.
- Knowledge graph: `components/KnowledgeGraphView.tsx`.
- Theme/i18n: `themes/theme-engine.ts`, `themes/presets.ts`, `contexts/I18nContext.tsx`, `locales/*.ts`.
