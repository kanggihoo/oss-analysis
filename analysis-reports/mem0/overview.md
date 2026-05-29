# mem0 프로젝트 개요

분석 대상: `C:\Users\SSAFY\Desktop\oss-analysis\mem0`

분석 방식: 저장소 루트 구조, README, 빌드/의존성 파일, 핵심 디렉터리, 주요 진입점 후보를 먼저 확인한 뒤 `mem0`, `server`, `mem0-ts`, `cli/skills/plugin/docs/examples` 범위로 나누어 정적 분석했다. 테스트 코드는 실행하지 않았다.

## 1. 이 프로젝트의 목적

Mem0는 AI assistant/agent에 장기 기억(long-term memory)을 붙이기 위한 메모리 레이어다. 사용자의 선호, 대화 맥락, agent 실행 상태, 세션별 정보를 저장하고 이후 질의 시 관련 기억을 검색해 LLM 응답 컨텍스트로 넣는 구조를 제공한다.

루트 `README.md`는 Mem0를 "The Memory Layer for Personalized AI"로 소개하고, 사용 방식을 크게 Python/TypeScript SDK, self-hosted server, cloud platform, CLI, agent skills/plugin으로 나눈다.

핵심 근거:

- `README.md`: 프로젝트 소개, quickstart, library/server/cloud/CLI 사용 방식.
- `pyproject.toml`: Python 패키지 `mem0ai`, 설명 `Long-term memory for AI Agents`.
- `mem0/__init__.py`: Python SDK 공개 진입점 `Memory`, `AsyncMemory`, `MemoryClient`, `AsyncMemoryClient`.
- `mem0-ts/package.json`: TypeScript SDK 패키지 `mem0ai`.
- `server/main.py`: self-hosted REST API 진입점.

## 2. 프로젝트 유형과 사용 방식

이 저장소는 단일 라이브러리라기보다 mixed/monorepo 성격이다.

- Python SDK: `mem0/`
- TypeScript SDK: `mem0-ts/`
- Self-hosted server + dashboard: `server/`
- CLI: `cli/`
- Agent skill/plugin/MCP 통합: `skills/`, `mem0-plugin/`
- Vercel AI SDK 통합: `vercel-ai-sdk/`
- 문서와 예제: `docs/`, `examples/`, `cookbooks/`

사용자는 세 가지 방식 중 하나를 고를 수 있다.

- Library mode: `pip install mem0ai` 또는 `npm install mem0ai` 후 앱 코드에서 `Memory`/`MemoryClient` 사용.
- Self-hosted mode: `server`에서 `make bootstrap` 또는 `docker compose up`으로 API와 dashboard 실행.
- Cloud/Platform mode: API key 기반 SDK/CLI/API 호출.

## 3. 핵심 기능

Mem0의 핵심 기능은 대화나 텍스트에서 기억할 만한 사실을 추출하고, 이를 벡터 저장소에 저장한 뒤, 이후 질의에 맞는 기억을 검색하는 것이다.

주요 기능:

- 메모리 추가: `Memory.add()` / server `POST /memories` / CLI `mem0 add`
- 메모리 검색: `Memory.search()` / server `POST /search` / CLI `mem0 search`
- 메모리 조회/목록/수정/삭제: `get`, `get_all`, `update`, `delete`, `delete_all`, `reset`
- LLM 기반 fact extraction
- embedding 생성과 vector store 저장/검색
- `user_id`, `agent_id`, `run_id` 기반 scope 분리
- metadata filter, keyword/BM25, entity matching, optional reranking
- history DB를 통한 변경 이력 저장
- self-hosted server의 인증, API key, dashboard, request log, runtime config 관리

## 4. 실행/사용 진입점

Python SDK:

- `mem0/__init__.py`: `Memory`, `AsyncMemory`, `MemoryClient`, `AsyncMemoryClient` 공개.
- `mem0/memory/main.py`: 로컬 메모리 엔진 `Memory`, `AsyncMemory`.
- `mem0/client/main.py`: hosted/platform API용 HTTP client.

Self-hosted server:

- `server/main.py`: `app = FastAPI(...)`, `/memories`, `/search`, `/configure` 등 REST API.
- `server/Makefile`: `make bootstrap`, `make up`, `make down`, `make seed`.
- `server/docker-compose.yaml`: API, PostgreSQL/pgvector, dashboard 구성.

TypeScript SDK:

- `mem0-ts/src/client/index.ts`: cloud `MemoryClient` 공개 API.
- `mem0-ts/src/oss/src/index.ts`: OSS/local `Memory`와 adapter 공개 API.
- `mem0-ts/tsup.config.ts`: 실제 빌드 entry는 `src/client/index.ts`, `src/oss/src/index.ts`.

CLI/plugin:

- `cli/node/src/index.ts`: Node CLI command 등록.
- `cli/node/package.json`: `bin.mem0 = ./dist/index.js`.
- `cli/python/pyproject.toml`: `mem0 = "mem0_cli.app:main"`.
- `mem0-plugin/mcp_config.json`: MCP endpoint와 `MEM0_API_KEY` 인증 설정.

## 5. 주요 모듈과 책임

### Python SDK: `mem0/`

- `mem0/memory/main.py`: 동기/비동기 메모리 엔진. `add`, `search`, `update`, `delete`, `history`, `reset` 흐름을 제어한다.
- `mem0/configs/base.py`: `MemoryConfig` 통합 설정. vector store, LLM, embedder, reranker, history DB 경로를 묶는다.
- `mem0/utils/factory.py`: provider 문자열을 실제 LLM/embedder/vector store/reranker 구현체로 연결한다.
- `mem0/memory/storage.py`: SQLite 기반 history 저장.
- `mem0/llms/`, `mem0/embeddings/`, `mem0/vector_stores/`, `mem0/reranker/`: provider별 adapter 구현.
- `mem0/exceptions.py`: SDK 예외 계층.

### Server: `server/`

- `server/main.py`: FastAPI 앱, 주요 memory REST API, 설정 API, request logging middleware.
- `server/auth.py`: JWT, refresh token, API key, `ADMIN_API_KEY`, `AUTH_DISABLED` 인증 흐름.
- `server/server_state.py`: 현재 config와 `mem0.Memory` 싱글턴 관리. `/configure` 변경 시 인스턴스를 재생성한다.
- `server/db.py`, `server/models.py`: SQLAlchemy DB/session과 `User`, `APIKey`, `RequestLog`, `Settings`, `RefreshTokenJti`.
- `server/routers/*`: auth, API keys, entities, requests 라우터.
- `server/dashboard/`: Next.js dashboard.

### TypeScript SDK: `mem0-ts/`

- `src/client/mem0.ts`: cloud API client `MemoryClient`.
- `src/common/exceptions.ts`: HTTP 상태별 SDK 예외 매핑.
- `src/oss/src/memory/index.ts`: local OSS `Memory` 구현.
- `src/oss/src/utils/factory.ts`: TS adapter factory.
- `src/oss/src/config/manager.ts`: config normalize/merge, Python SDK 호환 key 처리.

### CLI, skills, plugin, integrations

- `cli/`: Node/Python CLI 구현. `init`, `add`, `search`, `list`, `get`, `update`, `delete`, `import`, `config`, `entity`, `event`, `status`, `version`.
- `skills/`: agent가 Mem0 SDK/CLI/Vercel AI SDK를 쓰는 방법을 알려주는 skill graph.
- `mem0-plugin/`: MCP, hooks, slash commands를 묶은 assistant plugin.
- `vercel-ai-sdk/`: Vercel AI SDK provider/wrapper.

## 6. 핵심 개념과 용어

- Memory: 저장된 기억 단위. 보통 `memory` text와 metadata, id, score, timestamp를 가진다.
- Scope: `user_id`, `agent_id`, `run_id`로 기억의 소유/세션 범위를 나눈다.
- LLM: 대화에서 저장할 fact를 추출하거나 instruction을 생성하는 모델.
- Embedder: memory text/query를 벡터로 바꾸는 adapter.
- Vector store: Qdrant, pgvector, Pinecone, Redis, MongoDB, Chroma 등 벡터 저장소.
- History DB: memory 변경 이벤트를 저장하는 SQLite 또는 서버 DB 기반 이력.
- Entity store/linking: entity를 별도 벡터 collection에 저장하고 memory와 연결해 검색 품질을 높이는 구조.
- Reranker: 검색 결과를 후처리해 재정렬하는 optional component.
- Agent mode: CLI/플러그인이 AI agent 루프에서 쓰기 좋도록 JSON envelope와 안정적 출력 형식을 제공하는 모드.

## 7. 입력/데이터/상태/제어 흐름

Python SDK `Memory.add()`의 큰 흐름:

1. 입력 `messages`를 문자열/dict/list 형태에서 표준 message list로 정규화한다.
2. `user_id`, `agent_id`, `run_id`, metadata를 합쳐 필터와 payload metadata를 만든다.
3. `infer=False`면 raw message를 직접 memory로 저장한다.
4. `infer=True`면 기존 memory 검색, LLM fact extraction, JSON 파싱, dedupe/hash 처리를 거친다.
5. embedder로 memory embedding을 만들고 vector store에 upsert한다.
6. SQLite history DB에 ADD/UPDATE/DELETE 이벤트를 기록한다.
7. entity extraction/linking이 켜진 흐름에서는 entity collection에도 연결 정보를 갱신한다.

`Memory.search()`의 큰 흐름:

1. query와 filters를 검증한다. 적어도 `user_id`, `agent_id`, `run_id` 중 하나가 필요하다.
2. query embedding을 생성한다.
3. vector search, keyword/BM25 search, entity matching 신호를 결합한다.
4. metadata filter와 score threshold를 적용한다.
5. 필요 시 reranker를 적용해 결과를 재정렬한다.
6. 결과를 `{"results": [...]}` 형태로 반환한다.

Self-hosted server 흐름:

1. `server/main.py` 시작 시 환경 변수로 `DEFAULT_CONFIG`를 구성한다.
2. `server_state.initialize_state(DEFAULT_CONFIG)`가 `Memory.from_config(...)`로 SDK 인스턴스를 만든다.
3. API 요청은 FastAPI middleware에서 request id와 request log를 남긴다.
4. 각 endpoint는 `verify_auth`/`require_auth`로 인증한 뒤 `get_memory_instance()`를 통해 SDK를 호출한다.
5. `/configure`는 DB `Settings["config_overrides"]`에 runtime override를 저장하고 Memory 인스턴스를 재생성한다.

TypeScript SDK 흐름:

- Cloud mode: `MemoryClient`가 API key와 host를 받아 REST endpoint를 호출하고 응답 key를 변환한다.
- OSS mode: `new Memory(config)`가 config manager와 factory를 통해 embedder/LLM/vector store/history manager를 만들고 로컬 `add/search/update/delete`를 수행한다.

## 8. 설정 및 환경 구성

Python SDK:

- `MemoryConfig`가 `vector_store`, `llm`, `embedder`, `reranker`, `history_db_path`, `custom_instructions`를 가진다.
- 기본 history DB 경로는 `MEM0_DIR` 또는 `~/.mem0/history.db` 기반이다.
- 기본 provider는 코드상 OpenAI LLM/embedder와 Qdrant vector store가 중심이다.

Self-hosted server:

- 주요 환경 변수: `OPENAI_API_KEY`, `POSTGRES_*`, `APP_DB_NAME`, `JWT_SECRET`, `ADMIN_API_KEY`, `AUTH_DISABLED`, `MEM0_TELEMETRY`, `DASHBOARD_URL`.
- `server/.env.example`, `server/docker-compose.yaml`, `server/main.py`가 운영 설정의 핵심 근거다.
- auth는 기본적으로 켜져 있고, `AUTH_DISABLED=true`는 local dev 전용으로 문서화되어 있다.

CLI/plugin:

- `MEM0_API_KEY`, `MEM0_BASE_URL`, `MEM0_USER_ID`, `MEM0_AGENT_ID`, `MEM0_APP_ID`, `MEM0_RUN_ID`.
- MCP plugin은 `Authorization: Token ${MEM0_API_KEY}`를 사용한다.

TypeScript SDK:

- Node `>=18`.
- telemetry 제어: `MEM0_TELEMETRY`, `MEM0_DISABLE_TELEMETRY`, `MEM0_TELEMETRY_SAMPLE_RATE`.
- TS OSS config manager가 `embedding_dims`, `lmstudio_base_url` 같은 Python 호환 key도 수용한다.

## 9. 의존성 구조

Python root `pyproject.toml`의 필수 의존성:

- `qdrant-client`, `pydantic`, `openai`, `posthog`, `pytz`, `sqlalchemy`, `protobuf`.

Python optional extras:

- `nlp`: `spacy`
- `vector_stores`: Chroma, Cassandra, Weaviate, Pinecone, FAISS, Upstash, Azure AI Search, pgvector/psycopg, MongoDB, Redis, Valkey, Elasticsearch, Milvus, Databricks 등
- `llms`: Groq, Together, LiteLLM, Ollama, VertexAI, Google Gemini 등
- `extras`: LangChain, sentence-transformers, OpenSearch, FastEmbed 등

Server:

- FastAPI, Uvicorn, SQLAlchemy/Alembic, psycopg, slowapi, passlib/bcrypt, python-jose, PostHog.
- Postgres/pgvector가 self-hosted 기본 스토리지 축이다.

TypeScript:

- Cloud/common: `axios`, `openai`, `uuid`, `zod`.
- Optional/peer provider: Anthropic, Azure, Google, Qdrant, Supabase, pg, Redis, Groq, Ollama, Mistral, LangChain, Cloudflare 등.
- Build/test: `tsup`, `typescript`, `jest`, `ts-jest`, `prettier`.

## 10. 빌드/실행/테스트 방식

요청 조건에 따라 테스트 코드는 실행하지 않았다. 정적 단서 기준 실행/빌드 방식은 다음과 같다.

루트 Python package:

- 설치/환경: `hatch env create` 또는 `pip install mem0ai`
- 포맷/린트: `hatch run format`, `hatch run lint`
- 빌드: `hatch build`
- 테스트 명령 단서: `hatch run test`, `pytest tests/ {args}` (`pyproject.toml`, `Makefile`)

Self-hosted server:

- `cd server && make bootstrap`: stack 시작, migration, admin/API key seed.
- `cd server && make up`: browser-first setup.
- API: `http://localhost:8888`
- Dashboard: `http://localhost:3000`

TypeScript SDK:

- `npm run build`: clean + prettier check + tsup.
- `npm run test`, `npm run test:unit`, `npm run test:integration` 단서가 있다.
- 실제 `tsup.config.ts`는 `src/client/index.ts`와 `src/oss/src/index.ts`를 entry로 사용한다. `package.json` 내부 `tsup.entry`에는 `src/index.ts`가 남아 있으나 실제 `src/index.ts`는 존재하지 않는다. 현재 빌드가 어느 설정을 우선하는지는 실행 검증 없이 단정하지 않았다.

CLI:

- Node CLI: `npm install -g @mem0/cli`, `cli/node/package.json`의 `bin.mem0`.
- Python CLI: `pip install mem0-cli`, `cli/python/pyproject.toml`의 console script.

## 11. 에러 처리와 디버깅 포인트

Python SDK:

- `mem0/exceptions.py`에 SDK 예외 계층이 있고, `Memory.add/search/update/delete`는 validation, provider, vector store, embedding, LLM, DB 실패를 분리하려는 구조를 가진다.
- 흔한 디버깅 포인트는 provider 미지원/키 누락, vector store 연결 실패, scope filter 누락, memory id 미존재, LLM JSON 파싱 실패다.

Server:

- `server/errors.py`와 `server/main.py`가 request id, upstream error wrapping, request log를 처리한다.
- 응답 header `X-Request-ID`와 DB `RequestLog`가 운영 디버깅 포인트다.
- 인증 문제는 `verify_auth`, `require_auth`, `JWT_SECRET`, `ADMIN_API_KEY`, API key revocation, refresh token JTI 경로를 봐야 한다.

TypeScript SDK:

- `src/common/exceptions.ts`가 `AuthenticationError`, `RateLimitError`, `ValidationError`, `MemoryNotFoundError`, `NetworkError`, `ConfigurationError`, `MemoryQuotaExceededError` 등으로 HTTP 실패를 래핑한다.
- OSS 쪽은 config schema/adapter 초기화 실패와 lazy initialization 경로가 주요 디버깅 지점이다.

CLI/plugin:

- CLI `--agent`/`--json` 모드는 오류도 JSON envelope로 내보내 agent loop 파싱을 안정화한다.
- plugin은 MCP 중복 등록, `MEM0_API_KEY` 누락, hook 미적용 여부를 먼저 봐야 한다.

## 12. 확장하거나 기여할 때 봐야 할 구조

새 LLM/embedder/vector store provider를 추가하려면 보통 다음 흐름을 따른다.

1. provider config 추가 또는 기존 config 확장.
2. `mem0/llms`, `mem0/embeddings`, `mem0/vector_stores` 또는 TS `src/oss/src/*`에 구현체 추가.
3. `mem0/utils/factory.py` 또는 TS `src/oss/src/utils/factory.ts`에 provider 매핑 추가.
4. 공개 export와 문서/예제를 갱신한다.

검색 품질/메모리 알고리즘을 바꾸려면 다음 파일을 우선 봐야 한다.

- `mem0/memory/main.py`
- `mem0/memory/utils.py`
- `mem0/utils/entity_extraction.py`
- `mem0/utils/scoring.py`
- `mem0/configs/prompts.py`
- TS 대응: `mem0-ts/src/oss/src/memory/index.ts`, `mem0-ts/src/oss/src/memory/scoring.ts`

서버 API를 확장하려면 다음 파일을 봐야 한다.

- `server/main.py`
- `server/routers/*`
- `server/auth.py`
- `server/server_state.py`
- `server/models.py`, `server/alembic/versions/*`
- dashboard API utility와 화면 코드: `server/dashboard/src/*`

CLI/plugin을 확장하려면:

- `cli/node/src/index.ts`, `cli/node/src/commands/*`
- `cli/python/src/mem0_cli/*`
- `skills/*/SKILL.md`, `skills/*/references/*`
- `mem0-plugin/hooks/hooks.json`, `mem0-plugin/scripts/*`

## 13. 처음 기여자가 먼저 읽어야 할 파일

전체 방향:

- `README.md`
- `pyproject.toml`
- `CONTRIBUTING.md`

Python SDK 동작:

- `mem0/__init__.py`
- `mem0/memory/main.py`
- `mem0/configs/base.py`
- `mem0/utils/factory.py`
- `mem0/memory/storage.py`
- `mem0/exceptions.py`

Self-hosted server:

- `server/README.md`
- `server/main.py`
- `server/auth.py`
- `server/server_state.py`
- `server/db.py`
- `server/models.py`
- `server/docker-compose.yaml`
- `server/Makefile`

TypeScript SDK:

- `mem0-ts/README.md`
- `mem0-ts/package.json`
- `mem0-ts/tsup.config.ts`
- `mem0-ts/src/client/index.ts`
- `mem0-ts/src/client/mem0.ts`
- `mem0-ts/src/oss/src/index.ts`
- `mem0-ts/src/oss/src/memory/index.ts`
- `mem0-ts/src/oss/src/utils/factory.ts`

CLI/agent integration:

- `cli/README.md`
- `cli/node/src/index.ts`
- `cli/python/src/mem0_cli/__main__.py`
- `skills/README.md`
- `mem0-plugin/README.md`
- `docs/platform/quickstart.mdx`
- `docs/platform/cli.mdx`
- `docs/platform/mem0-mcp.mdx`

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

- TypeScript `package.json`의 `tsup.entry: ["src/index.ts"]`와 실제 `tsup.config.ts` entry가 다르다. `src/index.ts`는 현재 존재하지 않지만, 실제 build script가 `tsup.config.ts`를 우선 사용하면 문제 없을 수 있다. 테스트/빌드는 요청상 실행하지 않았으므로 동작 여부는 미검증이다.
- server dashboard의 role 기반 권한 제어는 현재 범위에서 뚜렷한 별도 정책을 확인하지 못했다. 인증/사용자 존재 확인은 있으나 세부 role authorization은 추가 확인이 필요하다.
- 각 provider별 fallback 모델명, timeout, retry, batch size 같은 세부 기본값은 provider 파일별로 더 깊게 봐야 한다.
- examples 디렉터리는 규모가 크고 앱 코드 중심인 예제가 많아, 각 예제가 어떤 대표 통합을 보여주는지는 overview 수준에서만 확인했다.
- cloud platform API의 실제 운영 서버 스펙은 로컬 SDK/client 단서로만 파악했다. 공개 API 전체 계약은 docs/openapi 또는 플랫폼 문서와 추가 대조가 필요하다.

