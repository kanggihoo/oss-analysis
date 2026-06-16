---
repo: Understand-Anything
local_checkout: /Users/kkh/Desktop/oss-analysis/repos/Understand-Anything
verification_commit: 7a3b7511b26a1816be3b6cc5683b34779e0abce9
baseline_artifacts:
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/2-understand-anything-pipeline.md
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/3-understand-anything-core.md
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/4-understand-anything-dashboard.md
---

# Understand-Anything core library verification

## 1. KnowledgeGraph schema

현재 source 기준 `@understand-anything/core`의 canonical schema는 `understand-anything-plugin/packages/core/src/types.ts`와 `schema.ts`다.

### NodeType: 21개 confirmed

`types.ts:1-7`이 NodeType 21개를 직접 선언한다.

- Code: `file`, `function`, `class`, `module`, `concept`
- Non-code: `config`, `document`, `service`, `table`, `endpoint`, `pipeline`, `schema`, `resource`
- Domain: `domain`, `flow`, `step`
- Knowledge: `article`, `entity`, `topic`, `claim`, `source`

Gemini core baseline의 “NodeType 21가지” claim은 confirmed다. Pipeline baseline 중 graph-reviewer section의 “노드 타입 16가지” claim은 current source 기준 corrected/stale다.

### EdgeType: 35개 confirmed

`types.ts:9-19`와 `schema.ts:3-14`가 EdgeType 35개를 선언한다. 카테고리는 structural, behavioral, data flow, dependencies, semantic, infrastructure/schema, domain, knowledge로 나뉜다. Knowledge-specific edges(`cites`, `contradicts`, `builds_on`, `exemplifies`, `categorized_under`, `authored_by`)도 포함된다.

### KnowledgeGraph root

`KnowledgeGraph`는 `version`, optional `kind`, `project`, `nodes`, `edges`, `layers`, `tour`를 갖는다(`types.ts:90-99`). Dashboard가 knowledge graph mode를 구분할 수 있도록 `kind?: "codebase" | "knowledge"`가 포함되어 있다(`types.ts:91-94`).

### DomainMeta 실제 shape

Gemini pipeline baseline이 제시한 `DomainMeta` 예시(`description`, `flowType`, `order`, `inputs`, `outputs`, `triggers`, `involvedActors`)는 현재 `types.ts`와 다르다. 현재 `DomainMeta`는 `entities`, `businessRules`, `crossDomainInteractions`, `entryPoint`, `entryType`만 정의한다(`types.ts:29-36`). 따라서 baseline의 DomainMeta interface claim은 corrected다.

## 2. sanitize / autoFix / normalize / validate pipeline

`schema.ts`는 LLM/agent output을 robust하게 받기 위한 layered pipeline을 구현한다.

- Alias maps: `NODE_TYPE_ALIASES`는 `func/fn/method→function`, `doc/readme/docs→document`, domain/knowledge aliases 등을 포함한다(`schema.ts:16-75`). `EDGE_TYPE_ALIASES`는 `extends→inherits`, `invokes→calls`, `references→cites`, `conflicts_with→contradicts` 등을 포함한다(`schema.ts:77-120`).
- `sanitizeGraph`: top-level null collection을 empty array로 바꾸는 등 구조 준비를 한다(`schema.ts:148-151`).
- `autoFixGraph`: schema issues를 수집하며 node/edge type, complexity, weight/direction/default 값 등을 canonicalize한다(`schema.ts:196-199` 이후).
- `normalizeGraph`: duplicate/dangling-ish graph cleanup을 수행하는 public function이다(`schema.ts:462-497`).
- `validateGraph`: fatal non-object check부터 Zod validation까지 수행하는 public validation entrypoint다(`schema.ts:499-502` 이후). Dashboard도 graph load 시 이 함수를 사용한다(`packages/dashboard/src/App.tsx:134-139`, `195-200`).

Batch merge script도 독립적으로 같은 방향의 normalization을 수행한다. `merge-batch-graphs.py`의 valid prefixes는 schema node types를 반영하고(`merge-batch-graphs.py:32-39`), `TYPE_TO_PREFIX`와 `COMPLEXITY_MAP`은 `func→function`, `low/easy→simple`, `medium/intermediate→moderate`, `high/hard/difficult→complex`를 처리한다(`42-76`).

## 3. Persistence and path sanitization

Persistence file names는 `knowledge-graph.json`, `meta.json`, `fingerprints.json`, `config.json`로 정의된다(`persistence/index.ts:8-11`). Gemini baseline이 말한 저장 파일 구성은 source 기준 confirmed이며, domain graph 저장도 존재한다(`persistence/index.ts:152-157`).

Security/path privacy 측면에서 중요한 함수는 `sanitiseFilePaths`다. 주석은 absolute filePath가 knowledge-graph.json에 그대로 저장되면 developer directory layout이 유출될 수 있다고 설명한다(`persistence/index.ts:36-40`, `74-76`). `saveKnowledgeGraph`와 `saveDomainGraph` 모두 저장 전에 sanitization을 수행한다(`74-79`, `152-157`).

## 4. GraphBuilder

`GraphBuilder`는 `analyzer/graph-builder.ts`에 있다.

- Class definition: `graph-builder.ts:60-63`
- `addFile`: file node 추가 및 language set update(`84-87`)
- `addFileWithAnalysis`: structural analysis를 함수/클래스/edge로 붙이는 entry(`105-108` 이후)
- `addNonCodeFileWithAnalysis`: config/docs/infra parser output을 child nodes로 붙임(`228-231` 이후)
- `build`: `KnowledgeGraph` object를 반환(`320-323` 이후)

Gemini baseline의 GraphBuilder method list는 source 기준 confirmed다. 다만 LLM 분석 자체를 GraphBuilder가 직접 호출하는 구조라기보다, LLM agent output과 deterministic parser result를 graph shape로 조립하는 core utility로 보는 편이 정확하다. `layer-detector.ts`, `tour-generator.ts`, `language-lesson.ts` 같은 analyzer utilities는 존재하지만 `/understand` pipeline의 LLM orchestration은 skill/agent prompt가 담당한다.

## 5. Tree-sitter plugin and language support

Tree-sitter plugin은 `web-tree-sitter`를 사용한다. `TreeSitterPlugin` class는 `plugins/tree-sitter-plugin.ts:31-33`에 있고, async init은 `web-tree-sitter` import로 시작한다(`124-127`). Public methods는 다음과 같다.

- `analyzeFile(filePath, content)` — `tree-sitter-plugin.ts:221-224`
- `resolveImports(filePath, content)` — `252-257`
- `extractCallGraph(filePath, content)` — `277-295`

Core dependency 목록은 TypeScript/JavaScript, Python, Go, Rust, Java, C#, C++, PHP, Ruby tree-sitter packages와 `web-tree-sitter`를 포함한다(`packages/core/package.json:39-53`). Gemini baseline의 multi-language Tree-sitter claim은 confirmed다. 단, baseline에 나온 “C/Lua 12가지 이상 언어 지원”은 language config에는 더 많은 파일 언어 id가 있으나 tree-sitter extractor support와 scanner language id support가 서로 다를 수 있다. 정확한 parser support는 `packages/core/src/languages/configs/*`와 `plugins/extractors/*`를 같이 봐야 한다.

## 6. Non-code parsers

Built-in non-code parser index는 정확히 12개 parser를 export/register한다. Evidence: `plugins/parsers/index.ts:1-12` exports and `31-44` register calls.

| Parser | Source path |
|---|---|
| Markdown | `packages/core/src/plugins/parsers/markdown-parser.ts` |
| YAML | `packages/core/src/plugins/parsers/yaml-parser.ts` |
| JSON | `packages/core/src/plugins/parsers/json-parser.ts` |
| TOML | `packages/core/src/plugins/parsers/toml-parser.ts` |
| Env | `packages/core/src/plugins/parsers/env-parser.ts` |
| Dockerfile | `packages/core/src/plugins/parsers/dockerfile-parser.ts` |
| SQL | `packages/core/src/plugins/parsers/sql-parser.ts` |
| GraphQL | `packages/core/src/plugins/parsers/graphql-parser.ts` |
| Protobuf | `packages/core/src/plugins/parsers/protobuf-parser.ts` |
| Terraform | `packages/core/src/plugins/parsers/terraform-parser.ts` |
| Makefile | `packages/core/src/plugins/parsers/makefile-parser.ts` |
| Shell | `packages/core/src/plugins/parsers/shell-parser.ts` |

Gemini baseline의 “12가지 비코드 파일 분석기” claim은 source 기준 confirmed다.

## 7. Plugin registry and discovery

`PluginRegistry`는 central dispatch hub다. 등록은 `registry.ts:20-24`에서 `languageMap`에 plugin을 넣으며, 나중에 등록된 plugin이 같은 language key를 덮어쓰는 효과를 낸다. `analyzeFile`, `resolveImports`, `extractCallGraph`는 file path에 맞는 plugin을 찾아 delegate한다(`registry.ts:56-72`).

Plugin config discovery는 `plugins/discovery.ts`에 있다. `DEFAULT_PLUGIN_CONFIG`는 tree-sitter plugin을 기본 활성화한다(`discovery.ts:14-24`). `parsePluginConfig`는 잘못된 JSON/shape에서 default를 반환한다(`30-60`), `serializePluginConfig`는 pretty JSON을 만든다(`66-68`).

## 8. Incremental update primitives

Core에는 standalone `change-classifier.ts`가 있다. `UpdateDecision.action`은 `SKIP`, `PARTIAL_UPDATE`, `ARCHITECTURE_UPDATE`, `FULL_UPDATE` union이다(`change-classifier.ts:4-8`). Decision matrix는 comment와 implementation에서 확인된다(`15-21`, `55-84`). Fingerprint generation/check는 `fingerprint.ts`, `/understand`의 `build-fingerprints.mjs`, `auto-update-prompt.md`와 함께 동작한다.

## 검증 명령

- `pnpm --filter @understand-anything/core build` → 성공
- `pnpm --filter @understand-anything/core test` → 33 test files / 670 tests passed
- `pnpm test` → skill/dashboard utility tests 포함 16 test files / 200 tests passed
