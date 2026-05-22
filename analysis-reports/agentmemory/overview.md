# agentmemory 코드베이스 이해 보고서

## 1. 이 프로젝트의 목적

agentmemory는 AI 코딩 에이전트가 세션을 넘어 기억을 유지하도록 만드는 영속 메모리 시스템이다. README는 Claude Code, Codex CLI, Cursor, Gemini CLI, Hermes, OpenClaw, OpenCode 등 MCP, hook, REST를 지원하는 에이전트가 같은 메모리 서버를 공유할 수 있다고 설명한다.

코드상 핵심 목적은 에이전트 실행 중 발생한 hook 이벤트와 사용자가 명시적으로 저장한 기억을 받아 `iii-engine`의 상태 저장소에 보관하고, 이를 검색 가능한 형태로 압축/색인한 뒤 다음 세션에서 관련 컨텍스트로 되돌려주는 것이다.

주요 근거:

- `README.md`: 설치, Quick Start, agent 연동, memory pipeline, MCP/API 설명
- `package.json`: npm 패키지 `@agentmemory/agentmemory`, CLI binary `agentmemory`
- `AGENTS.md`: iii-engine의 Worker/Function/Trigger 구조를 반드시 경유한다는 아키텍처 규칙
- `src/index.ts`: 서버 기동, iii worker 등록, 메모리 함수/REST/MCP/viewer 연결

## 2. 프로젝트 유형과 사용 방식

프로젝트 유형은 TypeScript 기반의 CLI/daemon/library 혼합형이다.

- CLI/daemon: `agentmemory` 명령이 iii-engine을 준비하고 memory worker를 띄운다.
- MCP 서버: `@agentmemory/mcp` 또는 `agentmemory mcp`가 MCP 클라이언트에 도구를 제공한다.
- REST API: `/agentmemory/*` HTTP endpoint를 통해 observe/search/remember/context 등을 제공한다.
- agent plugin/hooks: `plugin/`, `src/hooks/`, `src/cli/connect/*`가 Claude Code, Codex CLI 등으로부터 세션 이벤트를 수집한다.
- 웹 viewer: `src/viewer/*`가 로컬 UI를 제공한다.
- 보조 패키지/통합: `packages/mcp`, `integrations/*`, `examples/python`, `eval`, `benchmark`, `website`.

설치는 보통 `npm install -g @agentmemory/agentmemory` 또는 `npx @agentmemory/agentmemory`이고, 서버 실행 후 `agentmemory connect <agent>`로 에이전트 설정에 MCP/hook을 연결하는 방식이다.

## 3. 핵심 기능

핵심 기능은 다음 흐름으로 묶인다.

1. 세션과 tool 사용 이벤트 수집
   - `src/hooks/session-start.ts`, `src/hooks/post-tool-use.ts`, `src/hooks/stop.ts`
   - `src/functions/observe.ts`
   - `src/triggers/events.ts`

2. 관측값 저장과 정규화
   - `RawObservation`을 만들고 민감정보를 제거한 뒤 `KV.observations(sessionId)`에 저장한다.
   - 기본값은 LLM을 쓰지 않는 synthetic compression이다.
   - LLM 기반 압축은 `AGENTMEMORY_AUTO_COMPRESS=true`일 때 `mem::compress`로 수행된다.

3. 검색 색인
   - BM25: `src/state/search-index.ts`
   - Vector: `src/state/vector-index.ts`
   - Hybrid search: `src/state/hybrid-search.ts`
   - index persistence: `src/state/index-persistence.ts`

4. 명시적 장기 기억 저장/삭제
   - `src/functions/remember.ts`의 `mem::remember`, `mem::forget`
   - 유사한 기존 memory는 supersede/version 구조로 갱신된다.

5. 컨텍스트 생성
   - `src/functions/context.ts`
   - project profile, pinned slot, lesson, summary, 중요한 observation을 예산 안에서 XML 형태의 `<agentmemory-context>`로 렌더링한다.

6. 요약/통합/그래프/보존 정책
   - `src/functions/summarize.ts`
   - `src/functions/consolidate.ts`
   - `src/functions/consolidation-pipeline.ts`
   - `src/functions/graph.ts`, `src/functions/graph-retrieval.ts`
   - `src/functions/retention.ts`
   - `src/functions/audit.ts`

## 4. 실행/사용 진입점

주요 entry point:

- `src/cli.ts`: npm binary `agentmemory`의 실제 CLI 진입점
- `src/index.ts`: worker/daemon 런타임 진입점
- `src/mcp/standalone.ts`: standalone MCP 서버 진입점
- `packages/mcp/bin.mjs`: `@agentmemory/mcp` shim. 내부적으로 `@agentmemory/agentmemory/dist/standalone.mjs`를 import한다.
- `src/triggers/api.ts`: REST endpoint 등록
- `src/mcp/server.ts`: iii worker 안에 MCP endpoint 등록
- `src/hooks/*.ts`: agent hook으로 실행되는 단일 Node 스크립트들
- `src/viewer/server.ts`: local viewer HTTP 서버

CLI 명령은 `src/cli.ts` 하단의 `commands` 맵에 등록되어 있다.

- `init`
- `connect`
- `status`
- `doctor`
- `demo`
- `upgrade`
- `stop`
- `remove`
- `mcp`
- `import-jsonl`

## 5. 주요 모듈과 책임

상위 구조 기준:

- `src/`: 핵심 runtime. 약 165개 파일.
- `src/functions/`: 메모리 기능 단위. observe, search, remember, summarize, graph, retention, governance 등.
- `src/state/`: KV schema, BM25/vector index, hybrid search, index persistence.
- `src/triggers/`: REST/event trigger 등록.
- `src/mcp/`: MCP tool/resource/prompt endpoint와 standalone MCP transport.
- `src/hooks/`: Claude/Codex류 hook 이벤트를 REST API로 전송하는 스크립트.
- `src/cli/`: onboarding, doctor, connect adapter, 제거 계획 등 CLI 보조 로직.
- `src/providers/`: Anthropic/OpenAI/OpenRouter/Gemini/MiniMax/noop/agent-sdk LLM provider, embedding provider.
- `plugin/`: 에이전트 plugin용 hooks, skills, opencode commands.
- `integrations/`: Hermes, OpenClaw, pi, filesystem watcher 등 first-party 통합.
- `packages/mcp/`: 독립 npm MCP shim 패키지.
- `examples/python/`: iii-sdk로 직접 `mem::*` 함수를 호출하는 예제.
- `eval/`, `benchmark/`: 검색 품질과 성능 측정용 코드.
- `website/`: Next.js 기반 마케팅/문서 사이트.

## 6. 핵심 개념과 용어

- `Session`: 한 에이전트 작업 세션. `src/types.ts`의 `Session`.
- `RawObservation`: hook에서 들어온 원본 관측값. tool name/input/output, prompt, image ref 등을 담는다.
- `CompressedObservation`: 검색 가능한 정규화 관측값. title, narrative, facts, concepts, files, importance, confidence를 가진다.
- `Memory`: 사용자가 명시적으로 저장하거나 consolidation으로 생성된 장기 기억.
- `KV`: `src/state/schema.ts`의 scope 정의. `mem:sessions`, `mem:memories`, `mem:index:bm25`, `mem:graph:*`, `mem:slots`, `mem:lessons` 등.
- `iii-engine`: worker, function, trigger, state, stream, HTTP를 제공하는 외부 runtime. `StateKV`는 `state::get/set/list/update/delete`를 `sdk.trigger()`로 호출한다.
- `BM25`, `Vector`, `Graph`: hybrid retrieval의 세 축.
- `Slot`: pinned editable memory. `src/functions/slots.ts`.
- `Lesson`: 반성/회고 기반으로 저장되는 학습 항목. `src/functions/lessons.ts`, `src/functions/reflect.ts`.
- `Audit`: 삭제/변경 같은 중요 조작의 기록. `src/functions/audit.ts`.

## 7. 입력/데이터/상태/제어 흐름

대표적인 자동 수집 흐름은 다음과 같다.

1. 에이전트 hook 실행
   - 예: `plugin/hooks/hooks.codex.json`은 `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `Stop` 이벤트에서 `plugin/scripts/*.mjs`를 실행한다.
   - 원본 TypeScript는 `src/hooks/*.ts`이고 `tsdown.config.ts`가 `plugin/scripts`와 `dist/hooks`로 빌드한다.

2. hook 스크립트가 REST API 호출
   - `session-start.ts`는 `/agentmemory/session/start`를 호출한다.
   - `post-tool-use.ts`는 `/agentmemory/observe`에 tool 사용 결과를 보낸다.
   - `stop.ts`는 `/agentmemory/summarize`를 호출한다.

3. REST endpoint가 iii function 호출
   - `src/triggers/api.ts`의 `api::observe`는 `mem::observe`를 trigger한다.
   - 입력 검증과 auth middleware가 이 계층에서 수행된다.

4. `mem::observe`가 저장/stream/index 수행
   - `stripPrivateData()`로 민감정보를 제거한다.
   - `KV.observations(sessionId)`에 raw observation을 저장한다.
   - `stream::set`, `stream::send`로 viewer용 live stream을 발행한다.
   - 기본은 `buildSyntheticCompression()`으로 즉시 `CompressedObservation`을 만들고 BM25/vector index에 넣는다.
   - `AGENTMEMORY_AUTO_COMPRESS=true`이면 `mem::compress`를 비동기로 호출한다.

5. 검색/회상
   - `mem::search`: BM25 검색 후 observation/memory를 가져온다.
   - `mem::smart-search`: `HybridSearch`를 통해 BM25, vector, graph 결과를 reciprocal-rank 방식으로 합치고 lesson recall도 병렬 수행한다.
   - MCP 도구 `memory_recall`, `memory_smart_search`, `memory_save` 등은 REST proxy 또는 local fallback을 통해 이 기능을 노출한다.

6. 컨텍스트 재주입
   - `event::session::started`와 `/agentmemory/session/start` 계열은 `mem::context`를 호출한다.
   - 다만 hook이 stdout에 컨텍스트를 실제로 쓰는 것은 `AGENTMEMORY_INJECT_CONTEXT=true`일 때만이다. 기본값은 background capture만 수행한다.

상태 저장은 직접 SQLite를 만지는 대신 `src/state/kv.ts`가 iii `state::*` function을 호출하는 형태다. 실제 iii config는 `iii-config.yaml`에서 `./data/state_store.db` file-based KV를 가리킨다.

## 8. 설정 및 환경 구성

주요 설정 파일:

- `package.json`: npm metadata, bin, scripts, dependencies.
- `tsconfig.json`: TypeScript strict ESM 설정.
- `tsdown.config.ts`: `src/index.ts`, `src/cli.ts`, `src/mcp/standalone.ts`, hooks를 ESM으로 빌드.
- `iii-config.yaml`: REST 3111, stream 3112, engine bridge 49134, file-based state store.
- `.env.example`, `src/config.ts`: 환경 변수 기준 설정.
- `docker-compose.yml`, `iii-config.docker.yaml`: Docker 실행 보조.

`src/config.ts`의 주요 환경 변수:

- `III_ENGINE_URL`: 기본 `ws://localhost:49134`
- `III_REST_PORT`: 기본 `3111`
- `III_STREAMS_PORT`: 기본 `3112`
- `TOKEN_BUDGET`: 기본 `2000`
- `MAX_OBS_PER_SESSION`: 기본 `500`
- LLM provider: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `MINIMAX_API_KEY`
- embedding provider: `EMBEDDING_PROVIDER`, `OPENAI_API_KEY`, `VOYAGE_API_KEY`, `COHERE_API_KEY`, `OPENROUTER_API_KEY`
- `AGENTMEMORY_AUTO_COMPRESS`: 기본 off
- `AGENTMEMORY_INJECT_CONTEXT`: 기본 off
- `GRAPH_EXTRACTION_ENABLED`: 기본 off
- `CONSOLIDATION_ENABLED`: 코드상 `isConsolidationEnabled()`은 true일 때만 활성. README 예시는 true로도 설명된다.
- `AGENTMEMORY_SECRET`: REST/viewer/MCP proxy auth용 bearer secret
- `TEAM_ID`, `USER_ID`, `TEAM_MODE`: team memory 기능
- `SNAPSHOT_ENABLED`, `SNAPSHOT_DIR`, `SNAPSHOT_INTERVAL`

LLM API key가 없으면 `detectProvider()`는 `noop` provider를 선택한다. 이는 Stop hook 재귀와 토큰 낭비를 피하기 위한 안전 기본값이다.

## 9. 의존성 구조

런타임 의존성:

- `iii-sdk`: 핵심 worker/function/trigger/state/stream 통신
- `@clack/prompts`: CLI UI
- `dotenv`: 환경 파일
- `zod`: schema/validation 계층 일부
- `@anthropic-ai/claude-agent-sdk`, `@anthropic-ai/sdk`: agent-sdk/Anthropic provider

optional dependency:

- `@xenova/transformers`, `onnxruntime-node`, `onnxruntime-web`: local embeddings, CLIP, reranker 계열
- `@node-rs/jieba`, `tiny-segmenter`: CJK/tokenization 보조

dev dependency:

- `typescript`, `tsx`, `tsdown`, `vitest`, `@types/node`

provider 구조는 `src/providers/index.ts`가 `createProvider`, `createFallbackProvider`, `createEmbeddingProvider`, `createImageEmbeddingProvider`를 제공하고, 실제 provider별 구현은 `src/providers/*`, `src/providers/embedding/*`에 나뉜다.

## 10. 빌드/실행/테스트 방식

빌드:

- `npm run build`
- `tsdown`으로 `dist/index.mjs`, `dist/cli.mjs`, `dist/standalone.mjs`, `dist/hooks/*` 생성
- viewer asset, iii config, docker compose, env example도 dist로 복사한다.

실행:

- `npm run dev`: `tsx src/index.ts`
- `npm run start`: `node dist/cli.mjs`
- 일반 사용: `npx @agentmemory/agentmemory` 또는 global `agentmemory`

테스트:

- `npm test`: `vitest run --exclude test/integration.test.ts`
- `npm run test:integration`: 통합 테스트
- `npm run test:all`: 전체

이번 분석에서는 사용자 요청에 따라 테스트 코드를 직접 분석하거나 실행하지 않았다.

## 11. 에러 처리와 디버깅 포인트

주요 방어/디버깅 포인트:

- `src/index.ts`: iii function timeout이나 unhandled rejection이 daemon을 죽이지 않도록 top-level safety net을 둔다.
- `src/config.ts`: LLM provider 미설정 시 `noop`으로 안전하게 동작하고 agent-sdk fallback은 명시 opt-in 필요.
- `src/hooks/sdk-guard.ts`: Claude Agent SDK child session에서 hook 재귀가 발생하지 않도록 `AGENTMEMORY_SDK_CHILD`와 `entrypoint === "sdk-ts"`를 검사한다.
- `src/functions/observe.ts`: hook payload 검증, dedup, session별 keyed lock, observation limit, image ref cleanup.
- `src/functions/search.ts`: embedding 실패나 dimension mismatch는 검색/저장을 깨지 않고 warn 후 skip.
- `src/index.ts`: persisted vector index dimension mismatch는 시작 시 거부하거나 `AGENTMEMORY_DROP_STALE_INDEX=true`일 때 폐기한다.
- `src/mcp/rest-proxy.ts`: server livez probe 실패 시 standalone MCP는 local InMemoryKV fallback으로 내려간다.
- `src/viewer/server.ts`: viewer proxy는 allowed host/origin/CSP를 강하게 제한한다.
- `agentmemory doctor`: `src/cli.ts`와 `src/cli/doctor-diagnostics.ts`에서 설치/포트/hook 문제 진단 흐름을 제공한다.

## 12. 확장하거나 기여할 때 봐야 할 구조

새 memory 기능을 추가하려면 보통 다음 파일들이 함께 움직인다.

- `src/functions/<area>.ts`: `mem::*` function 등록
- `src/triggers/api.ts`: REST endpoint 등록
- `src/mcp/tools-registry.ts`: MCP tool definition
- `src/mcp/server.ts`: MCP call handler
- `src/index.ts`: function registration
- `src/types.ts`, `src/state/schema.ts`: 새 타입/KV scope가 필요할 때
- `plugin/skills/*`: agent-facing skill이 필요할 때

`AGENTS.md`는 MCP tool/REST endpoint/version/KV/audit operation 추가 시 갱신해야 하는 파일 목록을 명시한다. `CONTRIBUTING.md`도 “Adding an MCP tool”, “Adding an auto-hook”, release process를 요약한다.

## 13. 처음 기여자가 먼저 읽어야 할 파일

추천 순서:

1. `README.md`: 제품 목적, 설치, 사용 방식, API/MCP 표면 이해
2. `AGENTS.md`: 프로젝트 내부 아키텍처 규칙과 동시 갱신 규칙
3. `package.json`: 빌드/실행/테스트 스크립트와 패키지 형태
4. `src/index.ts`: 전체 worker bootstrapping과 function registration
5. `src/types.ts`: Session/Observation/Memory/Provider 등 도메인 모델
6. `src/state/schema.ts`: KV scope와 id 생성 규칙
7. `src/functions/observe.ts`: 자동 수집의 핵심
8. `src/functions/search.ts`, `src/state/hybrid-search.ts`: 회상/검색의 핵심
9. `src/functions/remember.ts`: 명시적 장기 기억 저장/삭제
10. `src/triggers/api.ts`: REST API 표면
11. `src/mcp/tools-registry.ts`, `src/mcp/server.ts`, `src/mcp/standalone.ts`: MCP 표면
12. `src/hooks/session-start.ts`, `src/hooks/post-tool-use.ts`, `src/hooks/stop.ts`: 실제 에이전트 이벤트 수집 방식
13. `src/cli.ts`, `src/cli/connect/index.ts`: 사용자 설치/연동 흐름

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

- README의 tool count 일부는 위치별로 `51 Tools`, `53 MCP tools` 같은 표현이 섞여 있고, 코드의 `src/mcp/tools-registry.ts`에는 `memory_*` tool이 다수 있다. 정확한 현재 공개/숨김 tool 수는 `getAllTools()`/`getVisibleTools()` 런타임 값을 확인하면 더 명확하다.
- `src/mcp/server.ts`는 큰 switch 기반 handler라 전체 case를 끝까지 읽지는 않았다. 주요 동작은 registry와 standalone/proxy/API 흐름으로 확인했다.
- `website/`는 제품 사이트이므로 런타임 memory system 분석에서는 제외했다.
- `test/`는 사용자 요청에 따라 읽거나 실행하지 않았다. 따라서 테스트 커버리지나 실제 동작 검증 결과는 이 보고서 범위 밖이다.
- 실제 iii-engine 버전/설치 방식별 시작 흐름은 CLI 코드와 README상 단서로만 분석했다. 로컬에서 daemon을 실행해 확인하지 않았다.
