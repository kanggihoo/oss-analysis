# context-mode 코드베이스 분석

분석 대상: `context-mode`  
저장소 위치: `/Users/kkh/Desktop/oss-analysis/context-mode`  
분석 기준: `.git`, `node_modules`, `dist`, `build`, `target`, `.next`, `coverage`, `vendor` 제외

## 1. 이 프로젝트의 목적

`context-mode`는 MCP 도구와 외부 툴 호출이 대량의 원문 데이터를 모델 context window에 그대로 밀어 넣는 문제를 줄이기 위한 로컬 MCP 서버/플러그인 프로젝트다.

핵심 아이디어는 원문을 모델에게 직접 보여주지 않고, 로컬 샌드박스 실행과 SQLite FTS5 인덱스에 보관한 뒤 필요한 조각만 `ctx_search`로 다시 꺼내는 것이다. README는 이를 "315 KB becomes 5.4 KB", "98% reduction" 같은 수치로 설명하지만, 이 수치는 프로젝트의 주장/벤치마크 문서에 근거한 것이며 모든 사용 상황에서 고정 보장되는 값은 아니다.

또 다른 큰 목적은 compaction 이후 작업 맥락을 잃지 않게 하는 것이다. `PostToolUse`, `PreCompact`, `SessionStart` 훅이 파일 접근, git 작업, 오류, 태스크, 규칙, 결정, subagent 사용 같은 이벤트를 `SessionDB`에 저장하고, compaction 직전에 resume snapshot을 만들어 다음 세션 시작 시 다시 주입한다.

주요 근거:
- `README.md`: 프로젝트 문제 정의, 설치 방식, `ctx_*` 도구 설명
- `src/server.ts`: MCP 도구 등록과 실행/색인/검색/운영 기능
- `hooks/posttooluse.mjs`, `hooks/precompact.mjs`, `hooks/sessionstart.mjs`: 세션 연속성 훅
- `src/session/db.ts`, `src/session/snapshot.ts`: 세션 이벤트 저장과 resume snapshot 생성
- `src/store.ts`: FTS5 기반 ContentStore

## 2. 프로젝트 유형과 사용 방식

프로젝트 유형은 TypeScript 기반의 혼합형 도구다.

- MCP 서버: `src/server.ts`
- CLI/런처: `src/cli.ts`, `start.mjs`, `cli.bundle.mjs`
- 멀티 플랫폼 플러그인/어댑터: `src/adapters/**`, `hooks/**`, `.claude-plugin`, `.codex-plugin`, `.cursor-plugin`, `.openclaw-plugin`, `.pi/extensions`
- 로컬 분석 대시보드: `insight/**`
- 스킬/운영 문서: `skills/**`, `docs/**`

실제 사용 방식은 플랫폼에 따라 다르다.

- Claude Code: marketplace plugin 또는 MCP-only 설치 후 `context-mode` MCP 서버와 훅 사용
- Gemini CLI, VS Code Copilot, Cursor, Codex, OpenClaw, OpenCode/OMP/Pi 등: 각 플랫폼 설정 파일과 훅 엔트리를 통해 MCP 서버와 라우팅 규칙 연결
- 공통적으로 사용자는 `ctx_execute`, `ctx_index`, `ctx_search`, `ctx_stats`, `ctx_doctor`, `ctx_insight` 같은 MCP 도구를 호출하게 된다.

규모는 분석 제외 경로 기준 약 482개 파일이며, 주요 확장자는 `.ts` 243개, `.mjs` 73개, `.json` 49개, `.md` 48개, `.tsx` 23개다. 책임 영역이 `src`, `hooks`, `configs`, `tests`, `insight`, `skills`로 나뉘는 중대형 도구 프로젝트에 가깝다.

## 3. 핵심 기능

1. 샌드박스 실행
   - `ctx_execute`: 코드/명령을 서브프로세스에서 실행하고, stdout 요약만 context로 반환한다.
   - `ctx_execute_file`: 파일 전체를 모델 context에 넣지 않고 `FILE_CONTENT`로 샌드박스 안에서 처리한다.
   - `PolyglotExecutor`는 JavaScript, TypeScript, Python, Shell, Ruby, Go, Rust, PHP, Perl, R, Elixir, C# 런타임을 탐지해 임시 파일로 실행한다.

2. 색인과 검색
   - `ctx_index`: 문자열 또는 파일을 `ContentStore`에 색인한다.
   - `ctx_fetch_and_index`: URL fetch 결과를 HTML→Markdown, JSON, plain text 형태로 색인한다.
   - `ctx_search`: FTS5 BM25, trigram, fuzzy/proximity 계열 fallback으로 필요한 조각만 회수한다.
   - `ctx_batch_execute`: 여러 명령을 실행하고 결과를 한 번에 색인한 뒤 여러 query를 바로 검색한다.

3. 컨텍스트 라우팅
   - `hooks/core/routing.mjs`는 `Bash`, `Read`, `Grep`, `WebFetch`, 외부 MCP 호출을 감지해 context-mode 도구 사용을 유도하거나 차단/수정한다.
   - 예: stdout으로 큰 본문을 흘릴 가능성이 있는 `curl/wget`, `WebFetch`, 빌드 도구 출력은 `ctx_execute`, `ctx_fetch_and_index`, `ctx_search` 쪽으로 redirect된다.

4. 세션 연속성
   - `PostToolUse`: tool call 결과에서 파일, 오류, git, task, decision, rule, skill, intent 등 이벤트를 추출해 `SessionDB`에 저장한다.
   - `PreCompact`: 저장된 이벤트로 XML 형태의 resume snapshot을 만든다.
   - `SessionStart`: routing block, 세션 이벤트 directive, resume snapshot, 자동 주입 상태를 추가 context로 제공한다.

5. 통계와 운영 도구
   - `ctx_stats`: bytes returned/indexed/sandboxed/cache saved와 lifetime 통계를 보여준다.
   - `ctx_doctor`: 런타임, FTS5/SQLite, 훅 등록, 버전 등을 점검한다.
   - `ctx_upgrade`: 업그레이드 명령을 생성한다.
   - `ctx_purge`: 세션 또는 프로젝트 단위로 인덱스/세션 데이터를 삭제한다.
   - `ctx_insight`: 로컬 Insight 대시보드를 띄운다.

## 4. 실행/사용 진입점

패키지 진입점:

- `package.json`
  - `bin.context-mode = ./cli.bundle.mjs`
  - `exports["./cli"] = ./cli.bundle.mjs`
  - `main = ./build/adapters/opencode/plugin.js`
- `cli.bundle.mjs`: 배포용 CLI 번들
- `server.bundle.mjs`: 배포용 MCP 서버 번들

소스 기준 실행 흐름:

1. `context-mode` 바이너리가 `cli.bundle.mjs`를 실행한다.
2. 소스 개발 모드에서는 `src/cli.ts`가 인자를 해석한다.
3. 인자가 없으면 `src/server.ts`를 import해 MCP stdio 서버를 시작한다.
4. `doctor`, `upgrade`, `hook`, `insight`, `statusline` 인자는 CLI 서브커맨드로 처리한다.
5. Claude Code 플러그인 경로에서는 `start.mjs`가 먼저 실행되어 project dir/env/plugin cache를 보정하고 서버를 띄운다.

MCP 서버 진입점:

- `src/server.ts`
  - `new McpServer({ name: "context-mode", version })`
  - `StdioServerTransport`
  - 11개 `ctx_*` 도구 등록
  - prompts/resources 빈 handler 등록: 일부 클라이언트가 `listPrompts`/`listResources`를 호출해도 transport가 깨지지 않도록 방어

훅 진입점:

- 공통 Claude 계열: `hooks/pretooluse.mjs`, `hooks/posttooluse.mjs`, `hooks/precompact.mjs`, `hooks/sessionstart.mjs`
- 플랫폼별: `hooks/codex/*`, `hooks/cursor/*`, `hooks/gemini-cli/*`, `hooks/vscode-copilot/*`, `hooks/jetbrains-copilot/*`, `hooks/kiro/*`
- CLI dispatcher: `src/cli.ts`의 `HOOK_MAP`과 `context-mode hook <platform> <event>`

Insight 진입점:

- MCP 도구: `ctx_insight`
- 서버: `insight/server.mjs`
- UI: `insight/src/main.tsx`, `insight/src/router.tsx`, `insight/src/routes/**`

## 5. 주요 모듈과 책임

`src/server.ts`

- MCP 서버 본체다.
- `ctx_execute`, `ctx_execute_file`, `ctx_index`, `ctx_search`, `ctx_fetch_and_index`, `ctx_batch_execute`, `ctx_stats`, `ctx_doctor`, `ctx_upgrade`, `ctx_purge`, `ctx_insight`를 등록한다.
- security gate, ContentStore, SessionDB, stats sidecar, lifecycle guard, platform detection을 연결한다.

`src/executor.ts`, `src/runtime.ts`, `src/runPool.ts`

- `PolyglotExecutor`가 임시 파일을 만들고 런타임별 command를 구성해 실행한다.
- shell 실행은 project root에서, 다른 언어는 임시 디렉터리에서 실행된다.
- `runPool`은 `ctx_batch_execute`, `ctx_fetch_and_index`의 concurrency primitive다.

`src/store.ts`

- `ContentStore`가 문서/출력/JSON/fetch 결과를 chunk로 나누고 FTS5에 저장한다.
- DB 구성:
  - `sources`: source label, chunk count, code chunk count, file path, content hash
  - `chunks`: porter/unicode61 tokenizer 기반 FTS5 테이블
  - `chunks_trigram`: trigram tokenizer 기반 FTS5 테이블
  - `vocabulary`: fallback/fuzzy 검색 보조
- 파일 기반 source는 content hash로 stale detection 후 search 시 자동 refresh할 수 있다.

`src/session/**`

- `db.ts`: `session_events`, `session_meta`, `session_resume`, `tool_calls` 관리
- `extract.ts`: tool call에서 session event를 추출하는 pure logic
- `snapshot.ts`: compaction 후 주입할 resume snapshot 생성
- `analytics.ts`: conversation/lifetime/multi-adapter 통계 계산
- `purge.ts`: 세션/프로젝트 단위 데이터 삭제
- `event-emit.ts`, `persist-tool-calls.ts`: MCP 서버 쪽 byte accounting, tool call counter 저장

`src/db-base.ts`

- SQLite driver abstraction이다.
- Bun이면 `bun:sqlite`, 현대 Node이면 `node:sqlite`를 우선 검토하고, FTS5가 없으면 `better-sqlite3`로 fallback한다.
- WAL, busy timeout, retry, corruption recovery, cleanup helper를 제공한다.
- ADR 0001에 따라 single-writer lockfile이나 `locking_mode=EXCLUSIVE`는 제거되어 있다.

`src/adapters/**`

- 플랫폼별 hook/MCP 설정과 event/response format을 정규화한다.
- 핵심 계약은 `src/adapters/types.ts`의 `HookAdapter`, `HookParadigm`, `PlatformCapabilities`다.
- 감지는 `src/adapters/detect.ts`, 클라이언트명 매핑은 `src/adapters/client-map.ts`가 담당한다.

`hooks/**`

- 실제 플랫폼 훅 실행 파일이다.
- `hooks/core/routing.mjs`: 툴 호출 전 라우팅/차단/수정 판단
- `hooks/core/formatters.mjs`: 플랫폼별 hook response 형식 변환
- `hooks/session-helpers.mjs`: session DB path, events path, cleanup flag path 계산
- `hooks/session-loaders.mjs`: hook에서 TS 번들/빌드 산출물을 안전하게 로드

`configs/**`, plugin directories

- 플랫폼별 설치 설정 템플릿이다.
- `.claude-plugin`, `.codex-plugin`, `.cursor-plugin`, `.openclaw-plugin`, `.pi/extensions/context-mode`, `openclaw.plugin.json`이 배포/인식 산출물로 존재한다.
- `plugins/` 디렉터리는 현재 파일이 없어 핵심 산출물로 보기는 어렵다.

`insight/**`

- 로컬 분석 대시보드다.
- `insight/server.mjs`가 `INSIGHT_SESSION_DIR`, `INSIGHT_CONTENT_DIR` 아래 SQLite DB를 읽어 `/api/overview`, `/api/analytics`, `/api/category-analytics`, `/api/content`, `/api/sessions`, `/api/search` 등을 제공한다.
- React UI는 content/search/session/knowledge/enterprise route로 구성된다.

## 6. 핵심 개념과 용어

`ctx_*` 도구

- context-mode가 MCP로 노출하는 도구군이다.
- 데이터 수집, 실행, 색인, 검색, 통계, 진단, 업그레이드, purge, Insight UI 실행을 담당한다.

Sandbox

- 모델이 원문을 읽고 머릿속으로 처리하지 않고, 코드가 로컬에서 데이터를 처리한 뒤 결과 요약만 출력하게 하는 실행 모델이다.
- README의 "Think in Code"가 이 철학을 설명한다.

ContentStore

- 원문 문서/명령 출력/fetch 결과를 SQLite FTS5에 저장하는 지식 저장소다.
- source label과 chunk를 기준으로 검색한다.

SessionDB

- 세션 이벤트, 메타데이터, resume snapshot, tool call counter를 저장하는 per-project SQLite DB다.
- DB 파일명은 project dir hash와 worktree suffix를 반영한다.

Routing Block

- 세션 시작 시 모델에게 주입되는 context-mode 사용 지침이다.
- hook-capable 플랫폼은 `SessionStart`에서 주입하고, MCP-only 또는 일부 플랫폼은 설정 파일/문서로 보완한다.

HookAdapter

- 플랫폼별 hook 입력/출력 포맷, 설정 파일 경로, session dir, config dir, instruction file을 정규화하는 인터페이스다.

Multi-writer

- `SessionDB`와 `ContentStore`는 여러 프로세스가 같은 DB path를 열 수 있다는 설계를 택한다.
- 동시성 처리는 SQLite WAL, busy timeout, `withRetry`에 맡긴다.

Resume Snapshot

- compaction 직전에 저장된 이벤트를 요약한 XML 형태의 table of contents다.
- 전체 원문을 다시 주입하지 않고, 필요한 경우 `ctx_search(..., source: "session-events")`로 세부 정보를 검색하도록 유도한다.

## 7. 입력/데이터/상태/제어 흐름

기본 MCP 실행 흐름:

1. 플랫폼이 MCP 서버를 실행한다.
2. `start.mjs` 또는 `src/cli.ts`가 project/config 환경을 보정한다.
3. `src/server.ts`가 stdio transport에 연결된다.
4. platform detection 결과를 `_detectedAdapter`에 저장한다.
5. MCP tool call이 들어오면 tool별 handler가 security check 후 실행/색인/검색/통계 처리를 한다.
6. 응답은 `trackResponse`를 통해 bytes returned/calls 통계에 반영된다.
7. 큰 원문은 `ContentStore`에 저장되고, 모델에게는 source label과 `ctx_search` 안내가 반환된다.

컨텍스트 절감 흐름:

1. 모델 또는 훅이 `Read`, `Bash`, `WebFetch`, 외부 MCP 호출 등 큰 출력 가능성이 있는 도구를 사용하려 한다.
2. `hooks/core/routing.mjs`가 호출을 검사한다.
3. 위험한 `curl/wget`, `WebFetch`, 대형 `Read`, 빌드 도구 출력 등은 `ctx_execute`, `ctx_execute_file`, `ctx_fetch_and_index`, `ctx_search` 사용 쪽으로 유도된다.
4. `ctx_execute`나 `ctx_batch_execute`는 stdout이 크면 자동으로 FTS5에 색인하고, 결과 본문 대신 검색 안내를 반환한다.
5. 이후 `ctx_search`가 필요한 snippet만 context로 가져온다.

세션 연속성 흐름:

1. `PostToolUse`가 tool call 이후 이벤트를 추출한다.
2. 이벤트는 `SessionDB.session_events`에 저장된다.
3. `PreCompact`가 compaction 직전 이벤트를 읽어 `session_resume.snapshot`에 저장한다.
4. `SessionStart`가 `compact` 또는 `resume` source로 실행되면 snapshot 또는 session-events directive를 주입한다.
5. `server.ts`의 `maybeIndexSessionEvents`는 `*-events.md` 파일을 `ContentStore`에 `session-events` source로 색인해 후속 검색을 가능하게 한다.

Insight 데이터 흐름:

1. `ctx_insight`가 `insight` 소스 파일을 cache dir에 복사하고 의존성 설치/빌드를 수행한다.
2. `insight/server.mjs`가 `INSIGHT_SESSION_DIR`, `INSIGHT_CONTENT_DIR`에서 DB를 읽는다.
3. `/api/overview`, `/api/analytics`, `/api/category-analytics`, `/api/content`, `/api/sessions`, `/api/search`가 UI에 데이터를 제공한다.

## 8. 설정 및 환경 구성

런타임/패키지:

- Node.js `>=22.5.0`
- package manager 표기는 `pnpm@10.23.0`
- 배포 바이너리는 `context-mode`
- TypeScript module target은 `NodeNext`, `ES2022`

주요 환경 변수:

- `CONTEXT_MODE_PROJECT_DIR`: 모든 플랫폼 공통 project dir fallback
- `CLAUDE_PROJECT_DIR`, `CLAUDE_CONFIG_DIR`, `CLAUDE_SESSION_ID`: Claude Code 계열
- `CODEX_HOME`, `GEMINI_PROJECT_DIR`, `CURSOR_CWD`, `VSCODE_CWD`, `IDEA_INITIAL_DIRECTORY` 등: 플랫폼별 감지/경로 해석
- `CTX_FETCH_STRICT=1`: `ctx_fetch_and_index`에서 private/loopback IP도 차단하는 strict SSRF 모드
- `CONTEXT_MODE_REQUIRE_SECURITY=1`: security module 로드 실패 시 fail-closed
- `CONTEXT_MODE_EXTERNAL_MCP_NUDGE_EVERY`: 외부 MCP nudge 주기
- `CONTEXT_MODE_IDLE_TIMEOUT_MS`: MCP 서버 idle shutdown opt-in
- `INSIGHT_SESSION_DIR`, `INSIGHT_CONTENT_DIR`, `INSIGHT_PARENT_PID`, `PORT`: Insight dashboard

저장 경로:

- session DB: `<adapter config root>/context-mode/sessions/<projectHash><worktreeSuffix>.db`
- content DB: `<adapter config root>/context-mode/content/<projectHash>.db`
- stats sidecar: `<sessionsDir>/stats-<sessionId>.json`
- session events markdown: `<sessionsDir>/<projectHash><suffix>-events.md`

플랫폼 설정:

- Adapter가 `getConfigDir`, `getSessionDir`, `getSettingsPath`, `getInstructionFiles`, `getMemoryDir`를 제공한다.
- home-rooted 플랫폼과 project-scoped 플랫폼을 구분해 경로를 계산한다.

## 9. 의존성 구조

런타임 의존성:

- `@modelcontextprotocol/sdk`: MCP 서버/stdio transport
- `better-sqlite3`: SQLite fallback/native driver
- `zod`: MCP tool input schema
- `turndown`, `turndown-plugin-gfm`, `@mixmark-io/domino`: fetch한 HTML을 Markdown으로 변환
- `@clack/prompts`, `picocolors`: CLI UX

개발 의존성:

- `typescript`
- `tsx`
- `esbuild`
- `vitest`
- `@types/node`, `@types/better-sqlite3`, `@types/turndown`

내부 의존 구조:

- `src/server.ts`가 거의 모든 core module을 조립한다.
- `src/store.ts`와 `src/session/db.ts`는 `src/db-base.ts`의 SQLite abstraction에 의존한다.
- `hooks/**`는 런타임에서 직접 TS를 import하지 않고, `hooks/session-*.bundle.mjs` 또는 build 산출물을 loader로 불러온다.
- `src/adapters/**`는 hook format/config generation 쪽에 집중하고, MCP server 자체는 플랫폼 독립적으로 유지된다.

## 10. 빌드/실행/테스트 방식

주요 npm scripts:

- `npm run build`
  - `tsc`
  - `server.bundle.mjs`, `cli.bundle.mjs`, hook bundle 생성
  - `assert-bundle`
  - `assert-asymmetric-drift`
- `npm run dev`
  - `npx tsx src/server.ts`
- `npm run doctor`
  - `npx tsx src/cli.ts doctor`
- `npm run typecheck`
  - `tsc --noEmit`
- `npm test`
  - `vitest run`
- `npm run benchmark`
  - `npx tsx tests/benchmark.ts`
- `npm run install:openclaw`
  - OpenClaw plugin install script

Vitest 설정:

- 테스트 include: `tests/**/*.test.ts`
- pool: `forks`
- test timeout/hook timeout: 30초
- local max workers: 3, CI max workers: 2
- CI retry: 2

대표 테스트 범위:

- `tests/core/server.test.ts`: MCP server/tool 핵심 동작
- `tests/core/routing.test.ts`: PreToolUse 라우팅 정책
- `tests/session/**`: SessionDB, snapshot, continuity, stats
- `tests/hooks/**`: hook 파이프라인
- `tests/adapters/**`: 플랫폼 adapter
- `tests/analytics/**`: Insight/analytics
- `tests/plugins/**`, `tests/scripts/**`: 배포 산출물/스크립트 검증

## 11. 에러 처리와 디버깅 포인트

실행/출력 문제:

- `ctx_execute`, `ctx_execute_file`, `ctx_batch_execute`는 exit code, timeout, partial output, large stdout을 분기 처리한다.
- non-zero exit은 `src/exit-classify.ts`로 error 여부를 분류한다.
- stdout이 너무 크면 원문을 직접 반환하지 않고 `ContentStore`에 색인한다.

보안/라우팅 문제:

- `src/security.ts`와 `hooks/core/routing.mjs`를 같이 봐야 한다.
- 서버 쪽은 `checkDenyPolicy`, `checkNonShellDenyPolicy`, `checkFilePathDenyPolicy`를 사용한다.
- 훅 쪽은 `routePreToolUse`가 `deny`, `ask`, `modify`, `context`, `null`을 반환한다.
- `CONTEXT_MODE_REQUIRE_SECURITY=1`이면 security module 로드 실패 시 모든 PreToolUse를 deny한다.

DB/동시성 문제:

- `src/db-base.ts`의 WAL, busy timeout, `withRetry`가 핵심이다.
- ADR 0001은 single-writer lockfile과 `locking_mode=EXCLUSIVE`를 제거한 이유를 설명한다.
- 동시 실행/좀비 MCP 문제는 DB layer가 아니라 `src/util/sibling-mcp.ts`, `src/lifecycle.ts`, `start.mjs` 쪽에서 봐야 한다.

세션 연속성 문제:

- `hooks/posttooluse.mjs`: 이벤트가 저장되는지 확인
- `hooks/precompact.mjs`: snapshot이 생성되는지 확인
- `hooks/sessionstart.mjs`: snapshot/directive가 주입되는지 확인
- `src/session/db.ts`: `session_events`, `session_resume.consumed`, `session_meta` 상태 확인

Insight 문제:

- `ctx_insight` handler는 cache dir 복사, dependency install, Vite build, local server spawn, browser open을 순서대로 수행한다.
- `insight/server.mjs`는 API를 `127.0.0.1`에 띄우고, OPTIONS 요청은 405로 처리한다.
- 주요 환경 변수는 `INSIGHT_SESSION_DIR`, `INSIGHT_CONTENT_DIR`, `PORT`다.

## 12. 확장하거나 기여할 때 봐야 할 구조

새 MCP 도구 추가:

- `src/server.ts`에 `server.registerTool(...)` 추가
- Zod input schema, security check, `trackResponse`, stats/event accounting 고려
- 큰 출력이면 `ContentStore` 색인/검색 유도 정책을 맞춰야 한다.
- 테스트는 `tests/core/server.test.ts` 또는 관련 기능 테스트에 추가한다.

새 플랫폼 adapter 추가:

- `src/adapters/types.ts`의 `HookAdapter` 계약 확인
- `src/adapters/<platform>/index.ts` 구현
- 필요하면 `hooks/<platform>/*` 추가
- `src/adapters/detect.ts`, `src/adapters/client-map.ts`에 감지/매핑 추가
- `configs/<platform>`, plugin manifest, docs/platform-support, adapter tests 갱신

검색/색인 로직 변경:

- `src/store.ts`의 schema, chunking, `searchWithFallback`, stale refresh를 봐야 한다.
- FTS5 schema 변경은 migration/drop-recreate 영향이 크다.
- `ctx_search` output cap, throttling, source filter와도 연결된다.

세션 이벤트/analytics 변경:

- `src/session/extract.ts`: 이벤트 추출 규칙
- `src/session/db.ts`: schema와 migration
- `src/session/snapshot.ts`: compaction 후 주입 내용
- `src/session/analytics.ts`: stats/Insight 계산
- `tests/session/**`, `tests/analytics/**` 동시 갱신 필요

플러그인/배포 변경:

- `package.json`의 `files`, `exports`, `bin`, platform metadata 확인
- `.claude-plugin`, `.codex-plugin`, `.cursor-plugin`, `.openclaw-plugin`, `.pi/extensions/context-mode` 동기화
- `scripts/version-sync.mjs`, `scripts/assert-bundle.mjs`, `scripts/assert-asymmetric-drift.mjs` 확인

## 13. 처음 기여자가 먼저 읽어야 할 파일

1. `README.md`
   - 프로젝트가 해결하려는 문제, 사용 방식, `ctx_*` 도구 개요를 파악한다.

2. `package.json`
   - 배포 entry, scripts, runtime dependencies, 지원 플랫폼 메타데이터를 확인한다.

3. `src/server.ts`
   - MCP 서버의 실제 도구 등록과 핵심 런타임 조립 지점이다.

4. `src/executor.ts`, `src/runtime.ts`
   - sandbox execution과 언어별 runtime 감지를 이해한다.

5. `src/store.ts`
   - context 절감의 핵심인 FTS5 ContentStore를 이해한다.

6. `src/session/db.ts`, `src/session/extract.ts`, `src/session/snapshot.ts`
   - session continuity 구조를 이해한다.

7. `hooks/core/routing.mjs`
   - 왜 특정 tool call이 context-mode 도구로 redirect되는지 확인한다.

8. `hooks/pretooluse.mjs`, `hooks/posttooluse.mjs`, `hooks/precompact.mjs`, `hooks/sessionstart.mjs`
   - 훅 기반 제어/기록/복구 흐름을 본다.

9. `src/adapters/types.ts`, `src/adapters/detect.ts`, `src/adapters/base.ts`
   - 멀티 플랫폼 추상화의 계약을 파악한다.

10. `docs/platform-support.md`
    - 플랫폼별 지원 수준, hook 형태, 설정 방식을 확인한다.

11. `docs/adr/0001-sessiondb-multi-writer.md`
    - SQLite multi-writer 설계 결정을 이해한다.

12. `CONTRIBUTING.md`
    - 로컬 개발, 빌드, 테스트, 기여 흐름을 확인한다.

13. `tests/core/server.test.ts`, `tests/core/routing.test.ts`, `tests/session/session-db.test.ts`
    - 실제로 보장되는 behavior를 빠르게 확인한다.

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

1. README/Benchmark 수치의 일반화 범위
   - README와 `BENCHMARK.md`에는 높은 context 절감률이 제시되지만, 이는 특정 입력/벤치마크 조건의 주장이다.
   - 실제 사용자 환경에서의 절감률은 tool mix, 출력 크기, hook 사용 가능 여부, 모델의 tool 선택에 따라 달라질 수 있다.

2. `plugins/` 디렉터리
   - 현재 `context-mode/plugins` 아래에는 파일이 확인되지 않았다.
   - 실질 배포 산출물은 `package.json.files`, `.claude-plugin`, `.codex-plugin`, `.cursor-plugin`, `.openclaw-plugin`, `.pi/extensions/context-mode`, `openclaw.plugin.json` 중심으로 보인다.

3. Insight `enterprise` 화면
   - `insight/src/routes/enterprise.tsx`의 일부 수치/문구가 실제 API backend 데이터인지, UI/문서 수준의 표시인지 추가 확인이 필요하다.
   - `insight/server.mjs`와 `insight/src/lib/api.ts`에서 확인된 주요 API는 overview, analytics, category analytics, content, sessions, search다.

4. 모든 플랫폼별 오류 처리의 세부 분기
   - adapter/hook 파일이 많아 전체 플랫폼별 예외 메시지와 edge case를 완전히 세분화하지는 않았다.
   - 플랫폼별 실제 설치 문제를 디버깅하려면 해당 adapter와 `tests/adapters/<platform>.test.ts`를 별도로 좁혀 읽는 것이 맞다.

5. 외부 클라이언트 버전별 호환성
   - `docs/platform-support.md`는 지원 매트릭스를 제공하지만, 각 클라이언트의 최신 hook/MCP API 변경까지는 이번 로컬 코드 분석만으로 검증하지 않았다.
   - 최신 클라이언트 동작은 실제 설치/실행 또는 upstream 문서 확인이 필요하다.

