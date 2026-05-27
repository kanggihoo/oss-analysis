# CodeGraph MCP 집중 분석

## 1. 조사 범위와 결론

이 문서는 기존 `analysis-reports/codegraph/overview.md`의 전체 구조 요약과 `analysis-reports/codeburn/provider-parsing-and-commands.md`의 "진입점 -> 파싱/처리 흐름 -> 명령/메서드 의미" 방식에 맞춰, CodeGraph의 MCP 서버 동작과 MCP tool 표면만 좁게 정리한다.

핵심 결론은 다음과 같다.

- CodeGraph MCP는 `codegraph serve --mcp`로 시작되는 TypeScript/Node 기반 stdio MCP 서버다.
- 실제 JSON-RPC 메서드는 MCP 표준의 `initialize`, `initialized`, `tools/list`, `tools/call`, `ping`만 직접 처리한다.
- agent가 호출할 수 있는 CodeGraph tool은 코드 기준 총 10개다: `codegraph_search`, `codegraph_context`, `codegraph_callers`, `codegraph_callees`, `codegraph_impact`, `codegraph_node`, `codegraph_explore`, `codegraph_status`, `codegraph_files`, `codegraph_trace`.
- 서버 실행 모드는 direct, proxy, daemon 세 가지다. 기본은 프로젝트에 `.codegraph/`가 있으면 detached daemon을 공유하고, 각 MCP host 프로세스는 얇은 proxy로 daemon socket에 붙는다.
- 프로젝트 루트 탐지는 `initialize`의 `rootUri`/`workspaceFolders`, `--path`, MCP `roots/list`, 마지막으로 `process.cwd()` 순서의 단서를 사용한다.
- MCP tool 응답은 인덱스 stale 상태, git worktree mismatch, 입력 크기 제한, tool allowlist 같은 안전장치를 통과한다.

## 2. MCP 서버 실행 진입점

가장 바깥 진입점은 `src/bin/codegraph.ts`의 `serve` 명령이다.

근거:

- `src/bin/codegraph.ts:1142`에서 `.command('serve')`를 등록한다.
- `src/bin/codegraph.ts:1145`에서 `--mcp` 옵션을 등록한다.
- `src/bin/codegraph.ts:1146`에서 `--no-watch` 옵션을 등록하고, `src/bin/codegraph.ts:1153`에서 `CODEGRAPH_NO_WATCH=1`로 변환한다.
- `src/bin/codegraph.ts:1158-1161`에서 `MCPServer`를 import하고 `new MCPServer(projectPath).start()`를 호출한다.

수동 실행 형태:

```bash
codegraph serve --mcp
codegraph serve --mcp --path /absolute/path/to/project
codegraph serve --mcp --no-watch
```

installer가 쓰는 공통 MCP 설정은 `src/installer/targets/shared.ts`의 `getMcpServerConfig()` 기준으로 다음 형태다.

```json
{
  "type": "stdio",
  "command": "codegraph",
  "args": ["serve", "--mcp"]
}
```

Codex는 TOML `[mcp_servers.codegraph]` 형식으로 별도 작성하지만 의미는 같다. Cursor처럼 MCP host가 workspace cwd를 보장하지 않는 target은 target별 구현에서 `--path`를 붙일 수 있다.

주의할 점: `codegraph serve`를 `--mcp` 없이 실행했을 때 stderr에 보여주는 안내 목록에는 `codegraph_trace`, `codegraph_explore`가 빠져 있다. 실제 MCP tool 표면은 `src/mcp/tools.ts`의 `tools` 배열과 `tools/list` 결과가 기준이다.

## 3. 런타임 모드: direct, proxy, daemon

`src/mcp/index.ts`의 `MCPServer.start()`가 실행 모드를 결정한다.

결정 순서:

1. `CODEGRAPH_DAEMON_INTERNAL=1`이면 현재 프로세스가 detached daemon 본체이므로 `startDaemonProcess()`를 실행한다.
2. `CODEGRAPH_NO_DAEMON`이 truthy면 direct mode로 실행한다.
3. `.codegraph/` 루트를 찾지 못하면 daemon socket/lock을 둘 곳이 없으므로 direct mode로 실행한다.
4. 그 외에는 daemon socket에 proxy로 붙거나, daemon이 없으면 detached daemon을 spawn한 뒤 proxy로 붙는다.
5. daemon 경로에서 예외가 나면 direct mode로 fallback한다.

### direct mode

`src/mcp/index.ts`의 `startDirect()`가 담당한다.

- `new MCPEngine()`을 만든다.
- `new StdioTransport()`를 만든다.
- `new MCPSession(transport, engine, { explicitProjectPath })`를 시작한다.
- `projectPath`가 있으면 `engine.ensureInitialized(projectPath)`를 background로 시작한다.
- stdin close/end와 SIGINT/SIGTERM, PPID watchdog으로 프로세스를 정리한다.

direct mode는 예전 방식과 호환되는 단일 프로세스/단일 MCP client 구조다. `CODEGRAPH_NO_DAEMON=1`이면 이 경로로 고정된다.

### daemon mode

`src/mcp/daemon.ts`의 `Daemon`이 담당한다.

- 프로젝트당 하나의 detached daemon 프로세스가 뜬다.
- daemon은 `.codegraph/daemon.pid` lockfile과 daemon socket을 사용한다.
- POSIX에서는 socket이 `.codegraph/daemon.sock`에 만들어지며, 경로가 너무 길면 temp dir의 hash 기반 socket으로 fallback한다.
- Windows에서는 `\\.\pipe\codegraph-<hash>` named pipe를 사용한다.
- daemon은 `MCPEngine` 하나를 공유하고, 연결마다 `MCPSession`을 새로 만든다.
- 마지막 client가 끊긴 뒤 `CODEGRAPH_DAEMON_IDLE_TIMEOUT_MS` 동안 idle이면 종료한다. 기본값은 300초다.

lockfile은 `src/mcp/daemon.ts`의 `tryAcquireDaemonLock()`에서 atomic hard-link 방식으로 만든다. 목적은 동시에 여러 launcher가 daemon을 띄울 때 빈 pidfile이나 stale pidfile 때문에 두 daemon이 생기는 것을 막는 것이다.

### proxy mode

`src/mcp/proxy.ts`의 `runProxy()`가 담당한다.

- MCP host가 실제로 spawn한 프로세스는 daemon이 아니라 proxy가 된다.
- proxy는 daemon socket에 연결하고 daemon이 처음 보내는 hello line을 읽는다.
- hello의 `codegraph` version이 현재 package version과 다르면 direct mode fallback을 요구한다.
- version이 맞으면 stdin -> socket, socket -> stdout으로 byte를 그대로 pipe한다.
- proxy 자체도 PPID watchdog을 갖고 있어 host가 SIGKILL 등으로 죽으면 socket을 닫고 종료한다.

즉 기본 정상 경로는 다음과 같다.

```text
MCP host
  -> codegraph serve --mcp launcher/proxy process
  -> .codegraph daemon socket
  -> detached CodeGraph daemon
  -> MCPSession
  -> MCPEngine
  -> ToolHandler
  -> CodeGraph API / SQLite index / watcher
```

## 4. MCP JSON-RPC 프로토콜 처리

프로토콜 처리는 `src/mcp/session.ts`의 `MCPSession`이 담당한다. `src/mcp/transport.ts`는 newline-delimited JSON-RPC 2.0 transport를 제공한다.

지원하는 MCP/JSON-RPC method:

| Method | 처리 위치 | 의미 |
| --- | --- | --- |
| `initialize` | `MCPSession.handleInitialize()` | 빠르게 handshake 응답을 보내고, root 단서가 있으면 background init을 시작한다. |
| `initialized` | `MCPSession.handleMessage()` | client 초기화 완료 notification. 별도 동작 없음. |
| `tools/list` | `MCPSession.handleToolsList()` | lazy init을 재시도한 뒤 `ToolHandler.getTools()` 결과를 반환한다. |
| `tools/call` | `MCPSession.handleToolsCall()` | tool 이름과 arguments를 검증하고 `ToolHandler.execute()`로 dispatch한다. |
| `ping` | `MCPSession.handleMessage()` | 빈 `{}` result를 반환한다. |

그 외 method는 request일 때 JSON-RPC `MethodNotFound` 에러를 반환한다.

`initialize`의 중요한 특징은 heavy init을 기다리지 않는다는 점이다. `src/mcp/session.ts`는 handshake 응답에 `protocolVersion`, `capabilities: { tools: {} }`, `serverInfo`, `instructions`를 먼저 보낸다. 그 뒤 `engine.ensureInitialized()`를 background로 시작한다. `__tests__/mcp-initialize.test.ts`는 이 순서를 회귀 테스트한다.

server-initiated request도 있다. `MCPSession.retryInitIfNeeded()`에서 client가 roots capability를 광고했지만 `rootUri`/`workspaceFolders`가 없으면 transport의 `request('roots/list')`로 client에게 workspace root를 묻는다. `__tests__/mcp-roots.test.ts`가 이 경로를 검증한다.

## 5. 프로젝트 루트와 CodeGraph 인스턴스 초기화

프로젝트 초기화 상태는 `.codegraph/`와 그 안의 DB를 기준으로 한다.

root 결정 흐름:

1. `initialize.params.rootUri`
2. `initialize.params.workspaceFolders[0].uri`
3. `codegraph serve --mcp --path <path>`의 explicit project path
4. client가 roots capability를 제공하면 server-initiated `roots/list`
5. 최후 fallback으로 `process.cwd()`

`src/mcp/engine.ts`의 `MCPEngine.ensureInitialized(searchFrom)`은 `findNearestCodeGraphRoot(searchFrom)`로 가까운 `.codegraph/` 루트를 찾고 `CodeGraph.open(resolvedRoot)`를 호출한다. 열기에 성공하면 `ToolHandler.setDefaultCodeGraph(cg)`를 설정하고 watcher와 catch-up sync를 시작한다.

초기화는 idempotent하게 `initPromise`로 직렬화된다. daemon mode에서 여러 client가 동시에 첫 tool call을 날려도 CodeGraph open과 watcher는 한 번만 수행된다.

## 6. watcher, catch-up sync, stale 응답

MCP engine은 기본적으로 file watcher를 켠다.

근거:

- `src/mcp/engine.ts`의 `MCPEngine` 기본 option은 `{ watch: true }`다.
- `startWatching()`은 `watchDisabledReason()`을 확인한다.
- `CODEGRAPH_WATCH_DEBOUNCE_MS`는 100ms 이상 60초 이하의 정수일 때만 debounce override로 인정된다.
- watcher 시작 후 sync 완료 시 stderr에 auto-sync 로그를 남긴다.
- `catchUpSync()`는 서버 연결 직후 `cg.sync()`를 background로 실행해 서버가 꺼져 있던 동안의 파일 변경을 흡수한다.

stale index 신호는 `src/mcp/tools.ts`의 `withStalenessNotice()`에서 붙는다.

- watcher가 pending file을 알고 있으면 tool response text에 해당 파일 path가 포함되는지 검사한다.
- response가 pending file을 직접 참조하면 상단 banner를 붙인다.
- pending file이 response에는 없지만 프로젝트 어딘가에 있으면 footer를 붙인다.
- `codegraph_status`는 자동 banner 대신 `### Pending sync:` 섹션으로 pending file을 직접 표시한다.

이 동작은 `__tests__/mcp-staleness-banner.test.ts`에서 검증된다.

## 7. MCP tool 전체 목록

실제 tool 목록은 `src/mcp/tools.ts:357`의 `export const tools` 배열이다. 모든 tool은 optional `projectPath`를 받는다. `projectPath`가 있으면 해당 경로에서 가까운 `.codegraph/`를 찾아 cross-project query를 수행한다.

| Tool | Required args | Optional args | 핵심 동작 |
| --- | --- | --- | --- |
| `codegraph_search` | `query` | `kind`, `limit`, `projectPath` | `cg.searchNodes()`로 symbol을 검색하고 위치/종류/signature 중심으로 반환한다. |
| `codegraph_context` | `task` | `maxNodes`, `includeCode`, `projectPath` | `cg.buildContext()`를 호출해 task 관련 entry point, 관련 symbol, code context를 markdown으로 구성한다. |
| `codegraph_callers` | `symbol` | `limit`, `projectPath` | matching symbol 전체에 대해 `cg.getCallers()`를 모아 호출자를 반환한다. |
| `codegraph_callees` | `symbol` | `limit`, `projectPath` | matching symbol 전체에 대해 `cg.getCallees()`를 모아 피호출자를 반환한다. |
| `codegraph_impact` | `symbol` | `depth`, `projectPath` | `cg.getImpactRadius()` 결과를 병합해 변경 영향권을 파일별 symbol 목록으로 반환한다. |
| `codegraph_node` | `symbol` | `includeCode`, `projectPath` | 단일 symbol의 location/signature/docstring/source 또는 container outline과 caller/callee trail을 반환한다. |
| `codegraph_explore` | `query` | `maxFiles`, `projectPath` | `cg.findRelevantContext()` 결과를 파일별로 묶고, 관련 source section과 relationship map을 budget 안에서 반환한다. |
| `codegraph_status` | 없음 | `projectPath` | index stats, node kind/language 분포, DB backend/journal mode, pending sync, worktree mismatch를 반환한다. |
| `codegraph_files` | 없음 | `path`, `pattern`, `format`, `includeMetadata`, `maxDepth`, `projectPath` | index의 file list를 tree/flat/grouped 형태로 반환한다. filesystem scan이 아니라 DB의 indexed files를 사용한다. |
| `codegraph_trace` | `from`, `to` | `projectPath` | 두 symbol 사이의 shortest call path를 찾고 각 hop의 body와 call-site를 inline한다. |

## 8. tool별 세부 동작

### codegraph_search

`handleSearch()`가 처리한다.

- `query`는 non-empty string이어야 하며 기본 최대 길이는 10,000자다.
- `limit`은 기본 10이고 1-100으로 clamp된다.
- `kind`가 있으면 NodeKind filter로 넘긴다.
- 출력은 `## Search Results` 아래 symbol name, kind, file path, line, signature를 나열한다.

### codegraph_context

`handleContext()`가 처리한다.

- `task`를 받아 `cg.buildContext(task, { maxNodes, includeCode, format: 'markdown' })`를 호출한다.
- 기본 `maxNodes`는 20, 기본 `includeCode`는 true다.
- `CLAUDE_SESSION_ID`가 있으면 `markSessionConsulted()`를 호출한다. 이는 Claude 쪽 hook/permission 흐름에서 CodeGraph를 먼저 consult했는지 표시하기 위한 것으로 보인다.
- feature request처럼 보이는 task에는 사용자에게 UX/edge case/acceptance criteria를 물으라는 reminder를 덧붙인다.

### codegraph_callers / codegraph_callees

`handleCallers()`와 `handleCallees()`가 처리한다.

- `findAllSymbols()`로 같은 이름의 여러 symbol을 찾아 aggregate한다.
- 여러 matching symbol이 있으면 결과 하단에 어떤 symbol들을 aggregate했는지 note를 붙인다.
- caller/callee는 node id 기준 dedupe 후 limit만큼 반환한다.

### codegraph_impact

`handleImpact()`가 처리한다.

- `depth` 기본값은 2이며 1-10으로 clamp된다.
- matching symbol마다 `cg.getImpactRadius(node.id, depth)`를 호출하고 nodes/edges를 병합한다.
- 출력은 파일별 affected symbol list 중심이다.

### codegraph_trace

`handleTrace()`가 처리한다.

- `from`, `to` symbol을 `findAllSymbols()`로 찾는다.
- 각 후보의 상위 3개 조합에서 `cg.findPath(f.id, t.id, ['calls'])`를 시도한다.
- path는 `MAX_HOPS = 7` 이하만 신뢰한다. 더 긴 path는 우회 가능성이 높다고 보고 직접 path 없음으로 처리한다.
- path가 있으면 각 hop의 file/line, call-site line, body 일부를 inline한다.
- destination이 추가로 호출하는 callee도 최대 6개까지 보여준다.
- heuristic edge는 `synthEdgeNote()`로 callback, event-emitter, React re-render, JSX render, Vue handler, interface implementation dispatch 등을 설명한다.

### codegraph_explore

`handleExplore()`가 처리한다.

- `query`로 `cg.findRelevantContext()`를 호출한다.
- 탐색 파라미터는 `searchLimit: 8`, `traversalDepth: 3`, `maxNodes: 200`, `minScore: 0.2`다.
- root node의 callers/callees 중 같은 파일에 있는 "glue node"를 추가해 흐름 연결 단서를 보강한다.
- file group을 score로 정렬하고, source file을 실제 disk에서 다시 읽어 line-numbered source section을 구성한다.
- 작은 파일은 전체를 반환하고, 큰 파일은 symbol range cluster를 구성해 budget 안에서 일부 section을 반환한다.
- output budget은 indexed file 수에 따라 달라진다.

`getExploreBudget()` 기준 권장 explore call 수:

| Indexed files | 권장 call 수 |
| --- | --- |
| `< 500` | 1 |
| `< 5,000` | 2 |
| `< 15,000` | 3 |
| `< 25,000` | 4 |
| 그 이상 | 5 |

`getExploreOutputBudget()` 기준 output cap:

| Indexed files | maxOutputChars | defaultMaxFiles | maxCharsPerFile |
| --- | ---: | ---: | ---: |
| `< 500` | 18,000 | 5 | 3,800 |
| `< 5,000` | 28,000 | 10 | 6,500 |
| `< 15,000` | 35,000 | 12 | 7,000 |
| 그 이상 | 38,000 | 14 | 7,000 |

`CODEGRAPH_EXPLORE_LINENUMS=0`이면 explore source line number 출력을 끌 수 있다. 기본은 켜져 있다.

### codegraph_node

`handleNode()`가 처리한다.

- 단일 symbol을 찾고 location/signature/docstring을 반환한다.
- `includeCode=true`일 때 leaf symbol은 `cg.getCode(node.id)` source를 반환한다.
- class/struct/interface/module 같은 container node는 전체 body 대신 member outline을 반환한다. 큰 class 전체 source로 context가 과도하게 커지는 것을 피하기 위한 정책이다.
- 출력 말미에는 `formatTrail()`로 direct callees/callers를 붙인다.

### codegraph_status

`handleStatus()`가 처리한다.

반환 항목:

- indexed file 수
- total nodes
- total edges
- DB size
- backend: `node:sqlite (Node built-in)`과 WAL/FTS5 설명
- journal mode: `wal`이면 concurrent reads safe라고 표시
- nodes by kind
- languages
- pending sync list
- worktree mismatch warning

### codegraph_files

`handleFiles()`가 처리한다.

- `cg.getFiles()`에서 indexed file list를 얻는다.
- `path` filter는 `/`, `.`, `./`, Windows slash 등을 project-relative POSIX path로 normalize한다.
- `pattern`은 간단한 glob-to-regex로 필터링한다.
- `format`은 `tree`, `flat`, `grouped`를 지원한다.
- `includeMetadata`가 true면 language와 symbol count를 함께 표시한다.

## 9. tool dispatch와 공통 안전장치

`ToolHandler.execute(toolName, args)`가 모든 tool 호출의 중앙 dispatch 지점이다.

공통 처리:

- `CODEGRAPH_MCP_TOOLS` allowlist 확인
- `projectPath`, `path`, `pattern` 길이와 타입 검증
- `query`, `task`, `symbol`, `from`, `to` non-empty string 및 최대 10,000자 검증
- switch 문으로 개별 handler 호출
- `codegraph_status`를 제외한 성공 응답에 worktree mismatch notice 적용
- `codegraph_status`를 제외한 성공 응답에 stale banner/footer 적용
- 예외는 MCP error packet이 아니라 `ToolResult`의 `isError: true` text로 변환

입력 제한:

- free-form string: `MAX_INPUT_LENGTH = 10_000`
- path-like string: `MAX_PATH_LENGTH = 4_096`
- 일반 output truncate: `MAX_OUTPUT_LENGTH = 15_000`
- `codegraph_explore`는 별도의 adaptive output cap을 사용한다.

`CODEGRAPH_MCP_TOOLS`:

- unset 또는 whitespace면 전체 tool 노출
- `trace,search,node`처럼 short name 허용
- `codegraph_trace`처럼 full name도 허용
- `tools/list`에서 노출 tool을 줄이고, cached client가 disabled tool을 호출해도 `execute()`에서 다시 막는다.

`__tests__/mcp-tool-allowlist.test.ts`가 list filtering과 execute guard를 검증한다.

## 10. MCP initialize 응답의 server instructions

`src/mcp/server-instructions.ts`의 `SERVER_INSTRUCTIONS`는 `initialize` 응답에 포함된다.

내용상 목표는 agent에게 다음 사용 원칙을 주입하는 것이다.

- 코드 구조 질문은 `codegraph_context` 먼저 사용
- 여러 관련 source는 `codegraph_explore`로 한 번에 확인
- 흐름 추적은 `codegraph_trace` 먼저 사용
- 단일 symbol은 `codegraph_node`
- file/folder 탐색은 `codegraph_files`
- stale banner가 있으면 해당 파일만 직접 Read
- grep/read loop나 별도 탐색 subagent 위임을 줄이기

즉 CodeGraph MCP는 tool 목록만 제공하는 서버가 아니라, initialize 단계에서 agent의 tool 선택 정책까지 같이 전달한다.

## 11. installer와 agent별 MCP 설정

installer target들은 공통적으로 `codegraph serve --mcp`를 agent 설정에 기록하고, 별도 instructions file에 CodeGraph 사용 지침을 삽입한다.

주요 target 단서:

- Claude: `.mcp.json` 또는 `~/.claude.json` 계열에 `mcpServers.codegraph` 작성, permission list 관리
- Cursor: `.cursor/mcp.json` 또는 `~/.cursor/mcp.json`; workspace cwd 문제가 있어 local 설정에서 `--path`를 붙이는 구조가 있다
- Codex: `~/.codex/config.toml`에 `[mcp_servers.codegraph]`
- opencode: JSONC 설정의 `mcp.codegraph`
- Hermes: YAML의 `mcp_servers.codegraph`와 toolset entry
- Gemini/Kiro/Antigravity: 각자의 MCP config path에 `mcpServers.codegraph`

공통 permission list인 `getCodeGraphPermissions()`에는 현재 `search`, `context`, `callers`, `callees`, `impact`, `node`, `status`만 들어 있다. `trace`, `explore`, `files`는 코드상 tool로 존재하지만 이 permission helper에는 없다. Claude permission 정책과 실제 최신 installer 흐름을 더 보려면 target별 permission 작성부를 추가 확인해야 한다.

## 12. 테스트가 보장하는 MCP 동작

MCP 관련 테스트에서 확인되는 주요 계약:

- `__tests__/mcp-initialize.test.ts`: initialize 응답은 CodeGraph open/watcher 시작보다 먼저 온다.
- `__tests__/mcp-roots.test.ts`: rootUri가 없고 roots capability가 있으면 `roots/list`로 project root를 찾는다.
- `__tests__/mcp-daemon.test.ts`: 여러 `serve --mcp` 프로세스가 하나의 detached daemon을 공유하고, stale lockfile/version mismatch/idle timeout/daemon opt-out을 처리한다.
- `__tests__/mcp-tool-allowlist.test.ts`: `CODEGRAPH_MCP_TOOLS`가 `tools/list`와 `execute()` 양쪽에서 적용된다.
- `__tests__/mcp-staleness-banner.test.ts`: pending file이 response에 포함되면 stale banner, 포함되지 않으면 footer, status에는 pending section이 표시된다.
- `__tests__/integration/mcp-input-limits.test.ts`: query/task/symbol/projectPath/path/pattern oversized input을 조기에 거부한다.
- `__tests__/concurrent-locking.test.ts`: default project와 explicit `projectPath`가 같은 DB를 중복 open하지 않아 concurrent MCP call에서 DB lock 문제를 피한다.

## 13. 처음 읽어야 할 MCP 파일 순서

1. `src/bin/codegraph.ts`: `serve --mcp` CLI 진입점과 `--path`, `--no-watch` 처리
2. `src/mcp/index.ts`: direct/proxy/daemon mode 선택과 lifecycle
3. `src/mcp/session.ts`: MCP JSON-RPC method 처리, initialize/tools/list/tools/call 흐름
4. `src/mcp/engine.ts`: CodeGraph open, watcher, catch-up sync, shared engine
5. `src/mcp/tools.ts`: tool schema, dispatch, handler 구현, stale/worktree/input guard
6. `src/mcp/daemon.ts`: detached daemon, lockfile, socket accept, idle timeout
7. `src/mcp/proxy.ts`: stdio-socket pipe, daemon version handshake, PPID watchdog
8. `src/mcp/transport.ts`: newline-delimited JSON-RPC transport와 server-initiated request
9. `src/mcp/daemon-paths.ts`: socket/pid path 계산
10. `src/mcp/server-instructions.ts`: initialize 응답에 포함되는 agent 사용 지침

## 14. 불확실하거나 추가 확인할 부분

- Claude permission list에서 `trace`, `explore`, `files`가 빠져 있는 것이 의도인지, target별 최신 permission 병합 흐름에서 보완되는지는 추가 확인이 필요하다.
- `ToolHandler.execute()`가 tool 실행 실패를 JSON-RPC error가 아니라 text `ToolResult`로 반환하는 정책이 모든 MCP client에서 동일하게 기대되는지는 client별 동작 확인이 필요하다.
- `codegraph serve` 비-MCP 안내 문구가 실제 tool 목록보다 오래된 것으로 보인다. 문서/CLI 안내 정합성 확인은 별도 범위다.
- daemon mode는 `.codegraph/` root가 있어야 기본 경로로 사용된다. 아직 init되지 않은 fresh checkout에서 direct mode로 뜬 뒤 나중에 `codegraph init`되는 경우의 사용자 경험은 `retryInitializeSync()` 단서가 있으나 전체 UX는 더 확인할 수 있다.
