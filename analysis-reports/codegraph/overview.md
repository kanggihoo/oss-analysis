# CodeGraph 프로젝트 분석

## 1. 이 프로젝트의 목적

CodeGraph는 로컬 코드베이스를 정적 분석해 SQLite 기반 지식 그래프로 만들고, Claude Code, Cursor, Codex, opencode, Hermes Agent, Gemini, Antigravity, Kiro 같은 agent/IDE가 MCP 도구로 그 그래프를 조회하게 해 주는 개발자 도구다.

README는 이 프로젝트의 가치를 "사전 인덱싱된 knowledge graph를 agent가 조회해 파일 탐색/grep/읽기 호출을 줄이는 것"으로 설명한다. 실제 코드 구조도 이에 맞다. `src/extraction`이 소스 파일을 파싱하고, `src/resolution`이 미해결 참조를 연결하며, `src/db`가 결과를 저장하고, `src/mcp`와 `src/bin/codegraph.ts`가 CLI/MCP 사용면을 제공한다.

## 2. 프로젝트 유형과 사용 방식

유형은 TypeScript 기반 CLI + MCP 서버 + 정적 분석 라이브러리의 혼합형 프로젝트다.

주요 사용 방식은 세 가지다.

- 설치: `install.sh`, `install.ps1`, `npx @colbymchenry/codegraph`, `npm i -g @colbymchenry/codegraph`.
- 프로젝트 초기화/색인: `codegraph init -i`, `codegraph index`, `codegraph sync`, `codegraph status`.
- agent 연동: installer가 각 agent 설정에 `{ command: "codegraph", args: ["serve", "--mcp"] }` 형태의 MCP 서버 설정과 지시문을 기록한다.

패키지 메타데이터상 배포 이름은 `@colbymchenry/codegraph`, CLI bin은 `codegraph`, main/type 출력은 `dist/index.js`와 `dist/index.d.ts`다. Node 지원 범위는 `>=20.0.0 <25.0.0`이며, CLI 시작부에서도 Node 25 이상과 최소 버전 미만을 차단한다.

## 3. 핵심 기능

- 소스 코드 인덱싱: `ExtractionOrchestrator`가 파일 스캔, 언어 감지, Tree-sitter 파싱, 노드/엣지/미해결 참조 저장을 조정한다.
- 다언어 심볼 추출: `src/extraction/languages/*`와 WASM grammar가 TypeScript/JavaScript/Python/Go/Rust/Java/Swift/Kotlin 등 여러 언어를 다룬다.
- 참조 해석: `ReferenceResolver`가 framework resolver, import resolver, name matcher, callback synthesizer를 사용해 `unresolved_refs`를 실제 edge로 승격한다.
- 그래프 질의: `GraphTraverser`, `GraphQueryManager`, `ContextBuilder`가 callers/callees/impact/context/trace용 결과를 만든다.
- MCP 도구 제공: `src/mcp/tools.ts`가 `codegraph_search`, `codegraph_context`, `codegraph_explore`, `codegraph_node`, `codegraph_trace`, `codegraph_files`, `codegraph_status` 등을 노출한다.
- 자동 최신화: `FileWatcher`와 MCP engine이 파일 변경을 debounce한 뒤 `sync()`를 실행하고, pending 파일이 있으면 tool 응답에 staleness 경고를 붙인다.
- agent 설치/해제: `src/installer/targets/*`가 Claude, Cursor, Codex, opencode, Hermes, Gemini, Antigravity, Kiro별 설정 파일을 생성/수정/삭제한다.

## 4. 실행/사용 진입점

가장 중요한 진입점은 `src/bin/codegraph.ts`다. 이 파일은 shebang이 있는 CLI 엔트리이며, 인자가 없으면 `runInstaller()`를 실행하고, 인자가 있으면 `commander`로 명령을 파싱한다.

등록된 주요 명령은 `init`, `uninit`, `index`, `sync`, `status`, `query`, `files`, `context`, `serve`, `unlock`, `callers`, `callees`, `impact`, `affected`, `install`, `uninstall`이다.

MCP 서버 진입점은 `codegraph serve --mcp`에서 연결되는 `MCPServer.start()`다. 이 경로는 direct 모드 또는 daemon/proxy 모드로 나뉜다. direct 모드는 stdio transport와 세션을 직접 띄우고, daemon 모드는 `.codegraph` 아래 socket/pid/lock 정보를 사용해 하나의 공유 엔진을 여러 세션이 재사용한다.

라이브러리 성격의 공개 진입점은 `src/index.ts`의 `CodeGraph` 클래스다. 여기서 `init`, `open`, `indexAll`, `sync`, `watch`, `searchNodes`, `getCallers`, `getCallees`, `getImpactRadius`, `buildContext` 같은 고수준 API가 제공된다.

## 5. 주요 모듈과 책임

- `src/bin`: CLI 명령, Node 버전 가드, npm uninstall hook.
- `src/installer`: agent/IDE별 MCP 설정 작성, instructions 삽입, 설치/해제 오케스트레이션.
- `src/mcp`: MCP server, daemon/proxy/session/transport, tool schema와 실행 handler.
- `src/sync`: watcher, watch 비활성 정책, git hook fallback, worktree mismatch 경고.
- `src/context`: task 설명을 기반으로 관련 symbol, call path, code block을 구성하고 markdown/json으로 포맷.
- `src/search`: field query parser, 검색어 추출, path/name/kind 기반 scoring 유틸.
- `src/extraction`: 파일 스캔, ignore 처리, Tree-sitter parsing, 언어별 extractor, WASM grammar 로딩, parse worker.
- `src/resolution`: import/path alias/name matching/framework-specific resolver/callback edge 합성.
- `src/db`: SQLite schema, migration, connection, query builder.
- `src/graph`: 그래프 조회와 traversal.
- `__tests__`: extraction, resolution, graph, context, MCP, sync, installer, release scripts까지 폭넓게 검증.
- `scripts`: 번들 생성, npm package packing, local install, release note 처리, npm shim.
- `site`와 `docs`: 사용자 문서, benchmark/design 문서, Astro/Starlight 기반 웹사이트.

## 6. 핵심 개념과 용어

- `Node`: 함수, 클래스, 변수, route, component 등 코드 심볼 단위. `src/types.ts`의 `NODE_KINDS`가 기준이다.
- `Edge`: `calls`, `imports`, `extends`, `implements`, `references`, `decorates` 등 심볼 관계.
- `FileRecord`: 인덱싱된 파일의 hash, language, size, modified/indexed time, node count.
- `UnresolvedReference`: 파싱 시 바로 연결되지 않은 참조. `ReferenceResolver`가 나중에 해결한다.
- `ExtractionResult`: 파일 하나에서 나온 nodes, edges, unresolved references, errors.
- `daemon`: MCP에서 프로젝트당 공유되는 백그라운드 engine.
- `proxy`: agent stdio와 daemon socket을 연결하는 브리지.
- `pendingFiles`: watcher debounce 또는 lock 실패 때문에 아직 sync되지 않았을 수 있는 파일 목록.
- `AgentTarget`: installer가 지원 agent별 설정을 통일된 인터페이스로 다루는 추상 타입.

## 7. 입력/데이터/상태/제어 흐름

인덱싱 흐름은 `CodeGraph.init/open`에서 DB와 orchestrator/resolver/traverser/context builder를 구성한 뒤 시작된다. `indexAll()`은 파일을 스캔하고, ignore 규칙과 기본 제외 디렉터리를 적용하고, 언어별 grammar를 준비한 다음 parse worker로 파일을 파싱한다. 결과는 `nodes`, `edges`, `files`, `unresolved_refs` 테이블에 저장된다.

그 다음 `ReferenceResolver`가 미해결 참조를 처리한다. 해석 순서는 대략 framework-specific 규칙, import/re-export/path alias 규칙, 이름 매칭 규칙으로 이어진다. 성공한 참조는 edge로 저장되고, callback이나 framework route처럼 정적 파싱만으로 부족한 관계는 추가 합성된다.

질의 흐름은 CLI 또는 MCP에서 `CodeGraph` 공개 API로 들어간다. 예를 들어 `codegraph_context`는 `ContextBuilder.buildContext()`를 호출해 검색 후보를 찾고, root node 주변을 graph traversal로 확장하며, 관련 코드 조각과 관계 정보를 markdown으로 구성한다.

MCP 실행 흐름은 agent -> stdio/proxy -> `MCPSession` -> `ToolHandler.execute()` -> `CodeGraph` API 순서다. watcher가 pending 파일을 알고 있으면 `withStalenessNotice()`가 응답 앞에 경고를 붙여 agent가 stale index를 그대로 믿지 않도록 한다.

## 8. 설정 및 환경 구성

프로젝트 상태는 주로 `.codegraph/` 아래 DB, lock, daemon socket/pid 파일로 관리된다. DB schema는 `src/db/schema.sql`이며, 핵심 테이블은 `nodes`, `edges`, `files`, `unresolved_refs`, `project_metadata`, `schema_versions`다. `nodes_fts` FTS5 가상 테이블도 있어 symbol/name/docstring/signature 검색을 빠르게 한다.

중요한 환경변수는 다음과 같다.

- `CODEGRAPH_ALLOW_UNSAFE_NODE`: Node 버전 가드 우회.
- `CODEGRAPH_NO_DAEMON`: MCP daemon 사용 안 함.
- `CODEGRAPH_DAEMON_INTERNAL`, `CODEGRAPH_DAEMON_IDLE_TIMEOUT_MS`: daemon 내부 실행/수명 제어.
- `CODEGRAPH_NO_WATCH`, `CODEGRAPH_FORCE_WATCH`, `CODEGRAPH_WATCH_DEBOUNCE_MS`: watcher 정책 제어.
- `CODEGRAPH_MCP_TOOLS`: MCP tool allowlist.
- `CODEGRAPH_EXPLORE_LINENUMS`: explore 결과 line number 출력 제어.
- `CODEGRAPH_RESOLVER_CACHE_SIZE`: resolver LRU cache 크기 조정.
- 설치 스크립트용 `CODEGRAPH_VERSION`, `CODEGRAPH_INSTALL_DIR`, `CODEGRAPH_BIN_DIR`, `CODEGRAPH_DOWNLOAD_BASE`, `CODEGRAPH_NO_DOWNLOAD`.

## 9. 의존성 구조

런타임 핵심 의존성은 `commander`, `@clack/prompts`, `chokidar`, `ignore`, `jsonc-parser`, `picomatch`, `tree-sitter-wasms`, `web-tree-sitter`다. CLI는 `commander`, installer는 `@clack/prompts`와 JSON/TOML 관련 유틸, watcher는 `chokidar`, extraction은 Tree-sitter WASM 계열에 의존한다.

개발 의존성은 TypeScript, Vitest, Node 타입이다. `better-sqlite3` 타입 의존이 있으나 실제 DB backend는 범위 내에서 Node 내장 sqlite adapter와 일반 SQLite adapter 추상화가 함께 보인다.

내부 의존 방향은 비교적 명확하다. `src/index.ts`가 db/extraction/resolution/graph/context/sync를 묶는 facade이고, CLI와 MCP가 이 facade를 호출한다. `types.ts`와 `errors.ts`는 전역 계약 역할을 한다.

## 10. 빌드/실행/테스트 방식

`package.json` 기준 주요 스크립트는 다음과 같다.

- `npm run build`: `tsc`, schema/WASM asset copy, CLI chmod.
- `npm run dev`: TypeScript watch.
- `npm run cli`: build 후 `node dist/bin/codegraph.js`.
- `npm test`: `vitest run`.
- `npm run test:eval`: `vitest run __tests__/evaluation/`.
- `npm run eval`: build 후 evaluation runner 실행.
- `npm run clean`: `dist` 삭제.
- `preuninstall`: `node dist/bin/uninstall.js`.

`vitest.config.ts`는 `__tests__/**/*.test.ts`를 수집하고 Node 환경에서 실행한다. 테스트 범위는 extraction, graph, context, sync/watcher, MCP daemon/tool/input limits/staleness, framework integration, installer targets, release scripts, security, SQLite backend, worktree detection 등을 포함한다.

번들/릴리스 쪽은 `BUNDLING.md`, `scripts/build-bundle.sh`, `scripts/pack-npm.sh`, `scripts/npm-shim.js`, `scripts/prepare-release.mjs`, `scripts/extract-release-notes.mjs`가 담당한다.

## 11. 에러 처리와 디버깅 포인트

CLI는 Node 버전 미지원, 모듈 로드 실패, 미초기화 프로젝트, 설치 대상 오류를 사용자 메시지와 `process.exit(1)`로 처리한다. `loadCodeGraph()` 실패 시 재설치 안내를 출력한다.

인덱싱 쪽은 parse worker timeout, WASM memory 문제, worker recycle, parse 실패 재시도 같은 안정성 장치를 둔다. 파일 단위 오류는 `ExtractionError`로 수집되고 `files.errors`나 결과 객체에 남는다.

DB/그래프 쪽은 `DatabaseError`, `ParseError`, `FileError`, `SearchError`, `ConfigError` 같은 도메인 오류 타입이 있다.

MCP 쪽 디버깅 포인트는 `codegraph_status`, stderr의 `[CodeGraph MCP]` 로그, staleness banner, worktree mismatch notice, daemon socket/pid/lock 파일이다. daemon 연결 실패, hello/version mismatch, lock 획득 실패 시 fallback 또는 pending 유지 전략이 있다.

## 12. 확장하거나 기여할 때 봐야 할 구조

새 언어를 추가하려면 `src/extraction/languages/index.ts`, 해당 언어 extractor, `src/extraction/grammars.ts`, 필요 시 WASM grammar와 tests를 함께 봐야 한다.

새 framework-aware resolver를 추가하려면 `src/resolution/frameworks/*`에 구현하고 `src/resolution/frameworks/index.ts` 등록, extraction/resolution tests를 추가하는 흐름이 자연스럽다.

새 MCP tool을 추가하려면 `src/mcp/tools.ts`의 `tools` 배열, input schema, `ToolHandler.execute()` switch, handler 구현, output budget/staleness/worktree notice 적용 여부를 같이 수정해야 한다.

새 agent/IDE 설치 대상을 추가하려면 `src/installer/targets/<id>.ts`, `targets/registry.ts`, `targets/types.ts`의 target id/인터페이스, 그리고 installer tests를 봐야 한다.

DB 스키마를 바꾸려면 `src/db/schema.sql`, `src/db/migrations.ts`, `src/db/queries.ts`, `src/types.ts`를 같이 맞춰야 한다.

## 13. 처음 기여자가 먼저 읽어야 할 파일

1. `README.md`: 제품 목적, 설치/사용 흐름, 지원 언어/agent, 주요 기능.
2. `package.json`: 빌드/테스트/배포 entry와 의존성.
3. `src/bin/codegraph.ts`: CLI 명령과 사용자 진입점.
4. `src/index.ts`: `CodeGraph` facade와 인덱싱/검색/그래프 API.
5. `src/types.ts`: 노드/엣지/파일/추출/컨텍스트 타입 계약.
6. `src/extraction/index.ts`: 전체 인덱싱 파이프라인.
7. `src/extraction/tree-sitter.ts`와 `src/extraction/languages/index.ts`: 언어별 추출 구조.
8. `src/resolution/index.ts`: 참조 해결 파이프라인.
9. `src/db/schema.sql`와 `src/db/queries.ts`: 저장 모델과 조회 API.
10. `src/mcp/tools.ts`: agent가 실제로 호출하는 MCP tool 표면.
11. `src/mcp/index.ts`, `src/mcp/daemon.ts`, `src/mcp/session.ts`: MCP 실행 구조.
12. `src/context/index.ts`: agent에게 반환되는 고수준 context 구성 방식.
13. `__tests__/integration/full-pipeline.test.ts`: 전체 파이프라인 기대 동작.

## 추가 조사: 그래프 저장 스키마와 edge 연결 기준

CodeGraph가 `codegraph init`, `codegraph index`, `CodeGraph.init(..., { index: true })` 같은 색인 작업을 수행하면 프로젝트 루트의 `.codegraph/` 아래 SQLite DB가 만들어지고, `src/db/schema.sql` 기준으로 다음 저장 구조가 생긴다. `src/db/migrations.ts`의 `CURRENT_SCHEMA_VERSION`은 4이며, 현재 `schema.sql`에는 v2-v4에서 추가된 `project_metadata`, `edges.provenance`, `unresolved_refs.file_path/language`, `idx_nodes_lower_name`, `idx_edges_provenance`, composite edge index 구조가 이미 반영되어 있다.

| 구분 | 이름 | 역할 |
| --- | --- | --- |
| 일반 테이블 | `schema_versions` | 적용된 schema/migration version과 적용 시각을 기록한다. |
| 일반 테이블 | `nodes` | 코드 심볼 저장소다. 파일, 모듈, 클래스, 함수, 메서드, 변수, import, route, component 등이 `id`, `kind`, `name`, `qualified_name`, `file_path`, `language`, line/column 범위, docstring/signature 같은 메타데이터와 함께 저장된다. |
| 일반 테이블 | `edges` | 심볼 간 관계 저장소다. `source`와 `target`은 모두 `nodes.id`를 참조하고, `kind`가 관계 종류를 나타낸다. `line`, `col`은 호출/참조 위치, `metadata`는 confidence/resolvedBy 같은 JSON, `provenance`는 `tree-sitter` 또는 `heuristic` 같은 생성 출처를 담는다. |
| 일반 테이블 | `files` | 색인된 파일의 `content_hash`, `language`, `size`, `modified_at`, `indexed_at`, `node_count`, extraction errors를 저장한다. `sync()`는 이 테이블과 현재 파일시스템의 size/mtime/hash를 비교한다. |
| 일반 테이블 | `unresolved_refs` | 파싱 단계에서 아직 대상 node를 확정하지 못한 참조 후보를 저장한다. `from_node_id`, `reference_name`, `reference_kind`, 위치, `file_path`, `language`가 들어가며, resolver가 성공적으로 edge로 승격하면 해당 row는 삭제된다. |
| 일반 테이블 | `project_metadata` | 프로젝트 단위 metadata/provenance를 key-value로 저장한다. |
| 가상 테이블 | `nodes_fts` | SQLite FTS5 검색 인덱스다. `nodes`의 `id`, `name`, `qualified_name`, `docstring`, `signature`를 검색 대상으로 삼는다. |
| 트리거 | `nodes_ai`, `nodes_ad`, `nodes_au` | `nodes` insert/delete/update 시 `nodes_fts`를 자동 동기화한다. |
| 인덱스 | `idx_nodes_*`, `idx_edges_*`, `idx_files_*`, `idx_unresolved_*` | 이름, qualified name, file path, language, edge source/target+kind, unresolved ref 조회를 빠르게 하기 위한 SQLite index다. |

그래프의 node 종류는 `src/types.ts`의 `NODE_KINDS`가 기준이다. 주요 값은 `file`, `module`, `class`, `struct`, `interface`, `trait`, `protocol`, `function`, `method`, `property`, `field`, `variable`, `constant`, `enum`, `enum_member`, `type_alias`, `namespace`, `parameter`, `import`, `export`, `route`, `component`다. 파일 하나를 파싱할 때 `TreeSitterExtractor.extract()`가 먼저 `file:<path>` 형태의 file node를 만들고, 이후 AST를 순회하면서 함수/클래스/메서드/변수 같은 심볼 node를 추가한다.

edge 종류는 `src/types.ts`의 `EdgeKind`가 기준이며, 실제 연결은 크게 두 단계로 만들어진다.

1. 파싱 중 바로 확정 가능한 구조 관계는 즉시 `edges`에 들어간다.
   - `contains`: file -> class/function/import, class -> method/field처럼 AST 상위 scope가 하위 심볼을 포함하는 관계다. `TreeSitterExtractor.createNode()`가 `nodeStack`의 부모 node와 새 node 사이에 `contains` edge를 만든다. Liquid, Svelte, Vue, DFM, MyBatis 같은 전용 extractor도 파일/컴포넌트 내부 구조를 `contains`로 저장한다.

2. 대상이 나중에야 확정되는 관계는 `unresolved_refs`에 저장했다가 resolver가 `edges`로 승격한다.
   - `calls`: 함수/메서드 본문에서 `foo()`, `obj.foo()`, `Module::foo()`, 언어별 bare call 패턴이 발견될 때 생성된다. `extractCall()`은 caller node를 `from_node_id`로, callee 문자열을 `reference_name`으로 저장한다. resolver는 import 기반 해석, framework 해석, name matching으로 실제 callee node를 찾아 `calls` edge를 만든다.
   - `imports`: import/include/require/use 문에서 생성된다. 언어별 `extractImport()`가 import node를 만들고, file node 또는 현재 scope에서 import 대상 module/file/symbol로 향하는 unresolved ref를 남긴다. `resolveViaImport()`는 상대 경로, alias, re-export, Java/Kotlin FQN import, Go module package import, C/C++ include 등을 고려해 대상 file 또는 exported symbol을 찾는다.
   - `extends`: class/interface/trait/protocol inheritance 문법에서 생성된다. `extractInheritance()`이 `extends_clause`, `superclass`, `base_clause`, Python class argument list, Go embedded type, Rust trait bounds, C#/C++ base list 등 언어별 AST 모양을 읽어 parent type 이름을 unresolved ref로 저장한다.
   - `implements`: interface 구현 문법에서 생성된다. Java/Kotlin/C#/Dart/PHP trait use 등에서 interface/protocol/trait 후보가 추출된다. 또한 resolver의 `createEdges()`는 원래 `extends` 후보였더라도 target이 `interface` 또는 `protocol`이고 source가 concrete class/struct이면 edge kind를 `implements`로 승격한다.
   - `references`: 호출/상속/import로 좁히기 어려운 일반 참조다. 대표적으로 타입 annotation, route -> handler, framework 설정 파일 -> controller/class, DFM event handler, MyBatis mapper 참조, React/Vue/Svelte component 참조 등이 이 관계로 저장된다.
   - `instantiates`: `new Foo(...)`, `Foo()`가 class/struct로 resolve되는 경우 생성된다. `extractInstantiation()`은 명시적 constructor syntax를 `instantiates` 후보로 저장한다. 또 Python/Ruby처럼 `Foo()`가 일반 call처럼 보이는 언어에서는 `createEdges()`가 `calls` 후보의 target이 class/struct임을 확인하고 `instantiates`로 승격한다.
   - `decorates`: `@Decorator`, Java annotation, Python decorator 같은 문법에서 생성된다. `extractDecoratorsFor()`가 decorator 이름을 unresolved ref로 저장하고, resolver가 decorator 함수/클래스/interface node에 연결한다.
   - `type_of`, `returns`, `exports`, `overrides`: 타입 정의상 edge kind로 열려 있지만, 이번 확인 범위의 핵심 생성 경로에서는 위 edge들보다 덜 직접적으로 보인다. 타입 annotation은 현재 주로 `references`로 저장되며, export 여부는 edge보다 `nodes.is_exported`와 import resolver의 exported symbol 탐색에 더 많이 쓰인다.

edge의 `source`와 `target`은 다음 기준으로 확정된다.

- `source`: 대부분 참조가 발생한 enclosing node다. 함수 본문 call이면 caller function/method node, class inheritance면 class node, file-level import면 file node, framework route면 route node가 source가 된다.
- `target`: resolver가 찾은 실제 definition node다. 같은 파일/가까운 디렉터리/같은 언어/export 여부/call kind별 선호도/import mapping/framework resolver confidence 등을 점수화해 결정한다.
- `metadata`: resolver가 만든 edge에는 `{ confidence, resolvedBy }`가 들어간다. `resolvedBy`는 `framework`, `import`, `name`, `jvm-import` 같은 해석 경로를 나타낸다.
- `provenance`: callback/event/render처럼 정적 AST만으로 빠지는 동적 연결은 `src/resolution/callback-synthesizer.ts`가 후처리로 `calls` edge를 합성하고 `provenance: 'heuristic'` 및 `metadata.synthesizedBy`를 남긴다.

대표적인 관계 형성 예시는 다음과 같다.

| 코드/구조 예시 | 생성되는 node/edge |
| --- | --- |
| `src/a.ts` 안의 `function login()` | `file:src/a.ts` node와 `login` function node, 그리고 `file -> login` `contains` edge |
| `login()` 본문에서 `validateUser()` 호출 | `login -> validateUser` `calls` edge. 처음에는 `reference_name='validateUser'` unresolved ref이고, resolver가 대상 function node를 찾으면 edge로 저장한다. |
| `import { validateUser } from './auth'` | import node와 `imports` unresolved ref. import resolver가 `./auth` 경로와 exported symbol을 찾아 file/symbol node에 연결한다. |
| `class AdminService extends UserService` | `AdminService -> UserService` `extends` edge. target이 interface/protocol이면 `implements`로 승격될 수 있다. |
| `new UserRepository()` | `caller -> UserRepository` `instantiates` edge |
| `@Controller()` 또는 `@login_required` | decorated symbol -> decorator target의 `decorates` edge |
| Express `router.get('/users', listUsers)` | `route` node `GET /users`와 route -> `listUsers` `references` edge |
| callback 등록 후 dispatcher가 callback 호출 | dispatcher method -> callback function `calls` edge, `provenance='heuristic'`, `metadata.synthesizedBy='callback'` |

조회는 이 저장 구조를 직접 사용한다. `searchNodes()`는 `nodes_fts MATCH`와 BM25, LIKE fallback, fuzzy name fallback으로 시작 node를 찾고, `getCallers()`, `getCallees()`, `getImpactRadius()`, `findPath()`는 `edges`의 `source`, `target`, `kind` index를 따라 incoming/outgoing traversal을 수행한다. 따라서 CodeGraph의 검색 가능성은 별도 vector DB나 embedding API가 아니라 SQLite 테이블과 FTS5/관계 edge 인덱스에서 나온다.

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

- GitHub Actions 실제 릴리스/배포 파이프라인은 이번 범위에서 깊게 읽지 않았다. `BUNDLING.md`와 scripts는 확인했지만 `.github/workflows/*`까지 연결 순서를 확정하려면 추가 분석이 필요하다.
- `src/db/queries.ts`의 모든 query 함수와 scoring 세부 규칙은 개요 수준으로만 확인했다. 검색 품질이나 성능을 깊게 이해하려면 `queries.ts`, `search/query-utils.ts`, `context/index.ts`를 더 좁게 읽어야 한다.
- 지원 언어/프레임워크 목록은 README와 파일 구조 기준으로 파악했다. 실제 runtime mapping과 테스트 커버리지의 완전한 매칭표는 추가 정리가 필요하다.
- npm 패키지 제거 시 local scope 설정까지 어디까지 정리되는지는 `preuninstall`과 `src/bin/uninstall.ts` 기준으로는 전역 cleanup 중심으로 보이며, local 잔존 정책은 추가 확인 여지가 있다.
- 사이트 문서의 배포 방식과 링크 검사/문서 빌드 검증 여부는 `site`와 package scripts만으로는 확정하지 않았다.
