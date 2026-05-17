# code-review-graph 분석 보고서

## 1. 이 프로젝트의 목적

`code-review-graph`는 코드베이스를 정적 분석해서 SQLite 기반 지식 그래프로 만들고, AI 코딩 도구가 전체 저장소를 다시 읽지 않고도 변경 영향 범위, 호출자/피호출자, import 관계, 테스트 커버리지 단서, 주요 실행 흐름을 질의할 수 있게 하는 Python 프로젝트다.

README의 설명은 "Tree-sitter로 AST를 만들고, 함수/클래스/import/call/test 관계를 그래프로 저장한 뒤 MCP로 AI assistant에 정확한 컨텍스트를 제공한다"는 구조다. 구현도 이 설명과 일치한다.

주요 근거:

- `pyproject.toml`: 패키지 이름, CLI entry point `code-review-graph = code_review_graph.cli:main`, MCP 서버 의존성 `mcp`, `fastmcp`, 파서 의존성 `tree-sitter`, `tree-sitter-language-pack`, 그래프/커뮤니티용 `networkx`.
- `code_review_graph/parser.py`: Tree-sitter 기반 멀티언어 파서.
- `code_review_graph/graph.py`: SQLite 저장소와 impact radius 질의.
- `code_review_graph/main.py`: FastMCP 기반 MCP tool/prompt 노출.
- `code_review_graph/tools/*`: MCP tool의 실제 구현.

## 2. 프로젝트 유형과 사용 방식

유형은 "Python CLI + MCP server + AI coding tool integration"이다. 부가적으로 VS Code extension, slash-command/skill 템플릿, hook installer, multi-repo daemon이 붙어 있다.

일반 사용 흐름:

1. `pip install code-review-graph` 또는 `pipx install code-review-graph`
2. 대상 저장소 루트에서 `code-review-graph install`
3. `code-review-graph build`
4. AI 도구에서 MCP tool 또는 `/code-review-graph:*` skill을 사용
5. 이후 `code-review-graph update`, `watch`, hooks, daemon이 그래프를 갱신

저장 위치는 기본적으로 대상 저장소의 `.code-review-graph/graph.db`다. `code_review_graph/incremental.py`의 `get_data_dir()` / `get_db_path()` 흐름이 이 경로를 결정하고, `docs/schema.md`도 같은 저장 방식을 설명한다.

## 3. 핵심 기능

- 전체 빌드: `full_build()`가 대상 저장소의 추적 파일을 수집하고 각 파일을 파싱해 노드/엣지를 저장한다.
- 증분 업데이트: `incremental_update()`가 git diff 또는 명시 파일 목록을 기준으로 변경 파일과 그 dependent 파일만 다시 파싱한다.
- 그래프 저장: `GraphStore`가 `nodes`, `edges`, `metadata`, `flows`, `communities`, `nodes_fts`, `embeddings` 계열 테이블을 관리한다.
- 영향 범위 분석: `GraphStore.get_impact_radius_sql()`이 변경 파일의 노드를 seed로 잡고 SQLite recursive CTE로 양방향 edge traversal을 수행한다.
- AI용 컨텍스트 생성: `get_minimal_context`, `detect_changes`, `get_review_context`, `query_graph`, `semantic_search_nodes`, `get_affected_flows` 등이 MCP tool로 노출된다.
- 후처리: signature 생성, FTS5 index, flow tracing, community detection, summary table 계산.
- optional semantic search: embedding DB를 추가로 만들고 FTS5/BM25 + vector search를 RRF로 결합한다.
- installer: Codex, Claude Code, Cursor 등 여러 AI 도구의 MCP 설정, hooks, instructions, skills를 생성/주입한다.

## 4. 실행/사용 진입점

CLI:

- `code_review_graph/cli.py::main`
- `pyproject.toml`의 `[project.scripts]`
- 주요 명령: `install`, `build`, `update`, `status`, `watch`, `visualize`, `wiki`, `detect-changes`, `serve`, `mcp`, `register`, `repos`, `daemon`

MCP server:

- `code_review_graph/main.py::mcp = FastMCP(...)`
- `code_review_graph/main.py::main`
- `code-review-graph serve` 또는 `.mcp.json`의 `uvx code-review-graph serve`

핵심 MCP tools:

- `build_or_update_graph_tool`
- `get_minimal_context_tool`
- `get_impact_radius_tool`
- `query_graph_tool`
- `get_review_context_tool`
- `semantic_search_nodes_tool`
- `detect_changes_tool`
- `list_flows_tool`
- `get_affected_flows_tool`
- `list_communities_tool`
- `get_architecture_overview_tool`

MCP prompts:

- `review_changes`
- `architecture_map`
- `debug_issue`
- `onboard_developer`
- `pre_merge_check`

## 5. 주요 모듈과 책임

- `parser.py`: 파일 언어 감지, Tree-sitter parser 로딩, AST traversal, `NodeInfo`/`EdgeInfo` 추출. 핵심 클래스는 `CodeParser`.
- `graph.py`: SQLite schema, `GraphNode`/`GraphEdge`, upsert, file 단위 atomic replace, graph query, impact radius.
- `incremental.py`: 저장소 루트 탐색, ignore 처리, tracked file 수집, full/incremental build, dependent file 탐색, watch mode.
- `tools/build.py`: MCP build tool 구현과 postprocess orchestration.
- `tools/query.py`: impact radius, predefined graph query, semantic search, stats, graph traversal.
- `tools/review.py`: review context, affected flows, detect changes wrapper.
- `changes.py`: git/svn diff hunk을 line range로 파싱하고 변경 라인을 graph node에 매핑, risk score 계산.
- `flows.py`: entry point 탐지, call graph 기반 execution flow tracing, criticality 계산.
- `communities.py`: Leiden 또는 file-based community detection, architecture overview.
- `search.py`: FTS5 rebuild, BM25 search, embedding search, RRF merge.
- `embeddings.py`: local/Google/MiniMax/OpenAI-compatible embedding provider와 embedding store.
- `skills.py`: AI tool별 MCP config, hooks, skill, instructions 설치.
- `main.py`: FastMCP tool/prompt registration.
- `registry.py`, `tools/registry_tools.py`: multi-repo registry와 cross-repo search.
- `daemon.py`, `daemon_cli.py`: 여러 저장소 watch daemon.

## 6. 핵심 개념과 용어

- Node: `File`, `Class`, `Function`, `Type`, `Test`.
- Edge: `CALLS`, `IMPORTS_FROM`, `INHERITS`, `IMPLEMENTS`, `CONTAINS`, `TESTED_BY`, `DEPENDS_ON`, `REFERENCES` 등.
- Qualified name: `file_path::function_name`, `file_path::ClassName.method_name` 형식. `GraphStore._make_qualified()`와 `CodeParser._qualify()`가 같은 개념을 쓴다.
- Blast radius: 변경 파일의 node에서 시작해 edge를 정방향/역방향으로 따라가며 도달 가능한 영향 노드/파일 집합.
- Flow: entry point에서 `CALLS` edge를 따라간 실행 경로.
- Community: graph edge 구조를 기반으로 묶은 관련 코드 클러스터.
- Risk score: flow 참여, cross-community caller, 테스트 커버리지, 보안 키워드, caller 수를 조합한 변경 위험도.

## 7. 입력/데이터/상태/제어 흐름

### 그래프 생성 원리

1. 파일 수집
   - `full_build()`는 `collect_all_files()`로 git tracked files와 ignore pattern을 반영해 source 파일 목록을 만든다.
   - 기본 제외 대상은 `.git`, `.code-review-graph`, `node_modules`, venv, build/dist, lockfile, binary 등이다.

2. 파일별 파싱
   - `CodeParser.detect_language()`가 확장자와 shebang으로 언어를 결정한다.
   - `CodeParser.parse_bytes()`가 Tree-sitter parser를 로드하고 AST를 만든다.
   - Vue/Svelte는 `<script>` 블록을 다시 JS/TS parser로 위임한다.
   - Notebook은 code cell을 추출해 Python/R/SQL 단위로 파싱한다.
   - ReScript, SQL, Nix 등은 Tree-sitter + 보완 regex/전용 로직을 쓴다.

3. 노드/엣지 추출
   - `_extract_from_tree()`가 AST를 재귀 순회한다.
   - `_extract_classes()`는 `Class` node와 `CONTAINS`, `INHERITS` edge를 만든다.
   - `_extract_functions()`는 `Function`/`Test` node와 `CONTAINS` edge를 만든다.
   - `_extract_imports()`는 import문을 `IMPORTS_FROM` edge로 저장한다.
   - `_extract_calls()`는 함수 호출을 `CALLS` edge로 저장한다.
   - `_extract_value_references()`는 callback, map/dict value, 배열 요소 등 함수가 값으로 전달되는 패턴을 `REFERENCES` edge로 보강한다.
   - 테스트 파일에서 test function이 production function을 호출하면 `TESTED_BY` edge를 추가한다.

4. 이름 해석
   - `_collect_file_scope()`가 파일 scope의 import map과 local definition set을 미리 모은다.
   - `_resolve_call_target()`는 local definition 또는 imported symbol이면 qualified name으로 바꾸고, 실패하면 bare name으로 둔다.
   - `GraphStore.resolve_bare_call_targets()`는 저장 후 전역 node table을 보고 bare `CALLS` target을 추가로 해석한다.
   - import path는 Python module, JS/TS relative import와 tsconfig alias, Java package, Dart package, Bash/Nix relative path 등을 언어별로 해석한다.

5. 저장
   - `GraphStore.store_file_nodes_edges()`가 한 파일의 기존 node/edge를 삭제하고 새 node/edge를 transaction으로 저장한다.
   - `nodes.file_hash`에 SHA-256을 저장해 이후 변경 여부를 빠르게 판단한다.
   - SQLite는 WAL mode를 사용한다.

6. 후처리
   - `tools/build.py::_run_postprocess()`가 signature, FTS5, flows, communities, summary table을 만든다.
   - `postprocess="minimal"`이면 signature + FTS만 수행한다.
   - `postprocess="full"`이면 flow/community까지 수행한다.

### 증분 업데이트 원리

`incremental_update()`는 다음 순서다.

1. `get_changed_files(repo_root, base)` 또는 명시 `changed_files`로 변경 파일을 잡는다.
2. 각 변경 파일에 대해 `find_dependents()`로 해당 파일을 import하는 dependent 파일을 찾는다.
3. 변경 파일 + dependent 파일을 합친다.
4. 삭제 파일은 그래프에서 제거한다.
5. 파일 hash가 기존 `nodes.file_hash`와 같으면 재파싱을 건너뛴다.
6. 남은 파일만 다시 parse/store 한다.
7. ReScript/Spring/Temporal resolver는 관련 파일 변경 시에만 다시 수행한다.

### AI가 그래프를 이용하는 방식

AI 도구는 저장된 DB를 직접 읽기보다 MCP tool을 호출한다.

- 작업 시작: `get_minimal_context_tool(task=...)`가 전체 node/edge 수, risk, 주요 community/flow, 다음 tool 추천을 약 100 token 수준으로 반환한다.
- 변경 리뷰: `detect_changes_tool()`이 git diff line range를 node에 매핑하고, risk score, affected flows, test gaps, review priorities를 반환한다.
- 영향 범위: `get_impact_radius_tool()`이 changed file seed에서 BFS/recursive CTE로 impacted nodes/files/edges를 반환한다.
- 구체 질의: `query_graph_tool(pattern="callers_of" | "callees_of" | "imports_of" | "tests_for" | ...)`가 특정 symbol 주변 관계만 반환한다.
- 소스 필요 시: `get_review_context_tool(include_source=True)`가 변경 파일과 관련 node 주변 source snippet만 포함한다.
- 검색: `semantic_search_nodes_tool()`은 FTS5/embedding 기반으로 관련 symbol을 찾는다.
- 흐름/아키텍처: `list_flows_tool`, `get_flow_tool`, `get_affected_flows_tool`, `list_communities_tool`, `get_architecture_overview_tool`이 실행 경로와 모듈 클러스터 관점을 제공한다.

즉, AI는 "전체 파일 읽기" 대신 "작업 요약 → 위험도 → 필요한 주변 관계 → 필요한 snippet" 순서로 컨텍스트를 점진적으로 확장하게 설계되어 있다. 이 정책은 `prompts.py`의 `_TOKEN_EFFICIENCY_PREAMBLE`에도 명시되어 있다.

## 8. 설정 및 환경 구성

필수:

- Python 3.10+
- `mcp`, `fastmcp`
- `tree-sitter`, `tree-sitter-language-pack`
- `networkx`
- `watchdog`

선택:

- `code-review-graph[embeddings]`: local sentence-transformers embedding.
- `google-embeddings`, `communities`, `wiki`, `eval`, `enrichment`.

설치/통합:

- `code-review-graph install`은 플랫폼을 감지하고 MCP config를 작성한다.
- `.mcp.json` 예시는 `uvx code-review-graph serve`.
- `skills.py::install_platform_configs()`는 Codex, Claude Code, Cursor 등 플랫폼별 config format에 맞춰 server entry를 병합한다.
- `skills.py::generate_hooks_config()` / `generate_codex_hooks_config()`는 AI 도구의 PostToolUse hook에서 `code-review-graph update --skip-flows`를 실행하게 만든다.
- `skills.py::install_git_hook()`는 pre-commit hook으로 `code-review-graph update`와 `detect-changes --brief`를 실행한다.

환경 변수/옵션 단서:

- `CRG_SERIAL_PARSE`: serial parse 강제.
- `CRG_PARSE_EXECUTOR`: parse executor override.
- `CRG_RECURSE_SUBMODULES`: submodule 포함 여부.
- `CRG_GIT_TIMEOUT`: git/svn diff timeout.
- `CRG_EMBEDDING_MODEL`, `CRG_OPENAI_*`: embedding provider/model 설정.
- `CRG_TOOLS`: MCP tool allow-list.

## 9. 의존성 구조

핵심 의존성:

- Tree-sitter: 언어별 AST 파싱.
- SQLite: 로컬 persistent graph DB.
- NetworkX: 일부 graph traversal/analysis와 legacy BFS.
- FastMCP/MCP: AI 도구가 graph 기능을 tool로 호출하는 인터페이스.
- Watchdog: watch mode.

선택 의존성:

- igraph: Leiden community detection.
- sentence-transformers/numpy 또는 cloud embedding provider: semantic search.
- jedi: Python call resolution enrichment.
- ollama: wiki 생성 관련 optional 기능.

## 10. 빌드/실행/테스트 방식

사용자 관점 실행:

```bash
pip install code-review-graph
code-review-graph install
code-review-graph build
code-review-graph status
code-review-graph update
code-review-graph watch
code-review-graph serve
```

개발/패키징:

- `pyproject.toml`은 hatchling build backend를 사용한다.
- CLI entry point는 `code_review_graph.cli:main`.
- MCP stdio server는 `code-review-graph serve`.

테스트 코드는 요청 범위에서 제외했고 읽지 않았다.

## 11. 에러 처리와 디버깅 포인트

- 파싱 실패: `full_build()`와 `incremental_update()`는 파일별 예외를 `errors` 배열에 누적하고 계속 진행한다.
- SQLite 동시성: `GraphStore`는 WAL mode와 `busy_timeout`을 설정한다.
- file 단위 저장: `store_file_nodes_edges()`는 `BEGIN IMMEDIATE` transaction으로 한 파일 데이터를 atomic replace 한다.
- diff 실패: `changes.py`는 git/svn subprocess 오류 시 빈 range를 반환하고 logging한다.
- MCP event loop blocking: 오래 걸리는 build, postprocess, embedding, detect_changes는 `asyncio.to_thread()`로 감싼다.
- 대형 저장소: `postprocess="minimal"` 또는 `--skip-flows`로 flow/community detection을 건너뛸 수 있다.
- graph stale: `code-review-graph build` 또는 `build_or_update_graph_tool(full_rebuild=True)`.
- missing nodes: 언어 지원/ignore pattern/Tree-sitter grammar 여부 확인.

## 12. 확장하거나 기여할 때 봐야 할 구조

그래프 생성 언어 지원을 확장하려면:

- `parser.py`의 `EXTENSION_TO_LANGUAGE`
- `_CLASS_TYPES`, `_FUNCTION_TYPES`, `_IMPORT_TYPES`, `_CALL_TYPES`
- `_extract_*` 계열 언어별 handler
- `_resolve_module_to_file()`의 import path resolution

그래프 스키마/저장을 바꾸려면:

- `graph.py`의 `_SCHEMA_SQL`, `GraphStore`
- `migrations.py`
- `docs/schema.md`

AI tool 출력을 바꾸려면:

- `main.py`의 MCP tool registration
- `tools/*.py`의 tool 구현
- `prompts.py`의 prompt workflow
- `docs/LLM-OPTIMIZED-REFERENCE.md`

설치 경험을 바꾸려면:

- `cli.py`의 command parser
- `skills.py`의 platform config/hook/skill/instruction injection

성능/대형 저장소를 다루려면:

- `incremental.py`의 parallel parse, hash skip, dependent detection
- `tools/build.py::_run_postprocess()`
- `flows.py`, `communities.py`, `search.py`

## 13. 처음 기여자가 먼저 읽어야 할 파일

1. `README.md`: 프로젝트가 해결하려는 문제와 사용자 흐름.
2. `docs/architecture.md`: 전체 data flow와 저장 구조.
3. `pyproject.toml`: entry point와 의존성.
4. `code_review_graph/cli.py`: 사용자가 실행하는 명령 구조.
5. `code_review_graph/main.py`: AI가 호출하는 MCP tool/prompt 목록.
6. `code_review_graph/parser.py`: 그래프 node/edge가 실제로 생성되는 핵심.
7. `code_review_graph/graph.py`: DB schema, 저장, impact traversal.
8. `code_review_graph/incremental.py`: full/incremental build 흐름.
9. `code_review_graph/tools/build.py`, `tools/query.py`, `tools/review.py`, `tools/context.py`: AI가 소비하는 핵심 tool 결과 구조.
10. `code_review_graph/changes.py`: review/risk scoring이 diff와 graph를 연결하는 방식.

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

- 실제 성능 수치와 recall/F1은 README와 docs의 주장만 확인했고, 테스트/벤치마크 실행은 하지 않았다.
- 테스트 코드는 사용자 요청에 따라 확인하지 않았다.
- VS Code extension 내부 동작은 관심사 중심 분석에서 제외했다. 핵심 Python/MCP 흐름만 확인했다.
- 대상 저장소 AGENTS.md는 graph MCP tool 우선 사용을 지시하지만, 현재 세션에 해당 MCP server tool이 노출되어 있지 않아 로컬 파일 기반으로 분석했다.
- `parser.py`가 매우 넓은 언어별 예외 처리를 포함하므로, 특정 언어에서 call/import resolution 정확도가 어느 정도인지는 별도 샘플 실행이 필요하다.
