---
sha: "63f62b2cafdaf0c30d9a409eae9d08b8d7ea272e"
created: 2026-10-23
updated: 2026-10-23
sources:
  - src/core/ai/gateway.ts
  - src/core/ai/types.ts
  - src/core/ai/defaults.ts
  - src/core/ai/model-resolver.ts
  - src/core/ai/build-gateway-config.ts
  - src/core/ai/provider-env.ts
  - src/core/ai/recipes/index.ts
  - src/core/ai/recipes/openai.ts
  - src/core/ai/recipes/anthropic.ts
  - src/core/ai/recipes/voyage.ts
  - src/core/ai/embed-batch-plan.ts
  - src/core/ai/embedding-guard.ts
  - src/core/ai/dims.ts
  - src/core/ai/voyage-gateway.ts
  - src/core/ai/query-embed-cache.ts
  - src/core/ai/errors.ts
  - src/core/ai/chat-fallback.ts
  - src/core/ai/chat-input-estimate.ts
  - src/core/ai/thinking-off.ts
  - src/core/ai/budget-record.ts
  - src/core/ai/invocation-guard.ts
  - src/core/ai/guarded-generation.ts
  - src/core/ai/key-warnings.ts
  - src/core/ai/key-redact.ts
  - src/core/minions/handlers/shell-redact.ts
  - src/core/model-id.ts
  - src/core/anthropic-pricing.ts
  - src/core/ai/legacy-model-pin.ts
  - src/core/ai/openai-latest.ts
  - src/core/ai/expansion-prompt.ts
  - src/core/ai/capabilities.ts
  - src/core/llm-json.ts
  - src/core/model-config.ts
  - src/core/model-pricing.ts
  - src/core/embedding-pricing.ts
  - src/core/config.ts
  - src/core/config-db-merge.ts
  - src/cli/db-plane-config.ts
  - src/core/embedding.ts
  - src/core/embed-preflight.ts
  - src/core/embed-cost-cap.ts
  - src/core/facts/backstop.ts
  - src/core/budget/budget-tracker.ts
  - src/core/budget/reservation-cost.ts
  - src/commands/config.ts
  - src/commands/config/model-pin-shadow.ts
  - src/commands/providers.ts
  - src/commands/models.ts
  - src/commands/pricing.ts
depends: []
status: ready
reimplementation: 미실행
---

# AI 게이트웨이·설정·예산

> 임베딩·채팅·쿼리 확장·리랭크 호출을 `provider:model` 문자열 하나로 받아 레시피(공급자 데이터)로 라우팅하고, 모델·키·base URL 설정을 정하고, 키가 없거나 실패했을 때의 동작과 예산 추적(막기/기록)을 정하는 기능이다.

<!-- 작성 메모: 이 문서는 gbrain@63f62b2c의 원본 동작이다. 우리가 바꾸고 싶은 점은 "적용 메모"에만 둔다. -->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 엔진 연결 전에 `loadConfig()`가 `~/.gbrain/config.json`(파일 평면) 위에 환경변수를 덮어쓰고, `buildGatewayConfig`가 모델 문자열·차원·base URL·키(`env` 스냅샷)를 `AIGatewayConfig`로 만들어 `configureGateway`에 넘긴다(스키마 생성에 임베딩 차원이 필요하기 때문). 이후 게이트웨이는 호출 시점의 `process.env`가 아니라 이 스냅샷을 읽는다(예외는 불변식 참고).
2. 엔진 연결 뒤 CLI는 DB 설정 평면을 파일·환경변수 값이 없는 칸에만 병합해(R-12) `configureGateway`를 다시 부르고, `reconfigureGatewayWithEngine`이 **expansion·chat 모델만** DB 설정(`models.*`)과 키 보유 여부까지 반영해 다시 정한다. 임베딩 모델·차원은 DB에서 병합하지도 다시 정하지도 않는다.
3. 호출자는 `isAvailable(touchpoint, model?)`(임베딩은 이유까지 주는 `diagnoseEmbedding`)로 먼저 쓸 수 있는지 묻거나, 바로 부른다. 게이트웨이 호출은 `embed`·`embedQuery`·`chat`·`expand`·`rerank`다.
4. 호출마다 `provider:model` → 레시피 → 터치포인트(임베딩/확장/채팅/리랭크) 존재 확인 → 인증 확인(키 없으면 `AIConfigError`) → AI SDK 모델 객체(캐시) 순으로 간다. 리랭크만 SDK 없이 직접 HTTP다.
5. 예산 추적기(`BudgetTracker`)가 현재 비동기 컨텍스트에 걸려 있으면 `embed`·`chat`·`rerank`는 공급자 호출 **전에** `reserve`(상한 초과면 `BudgetExhausted`를 던져 호출 자체가 일어나지 않음), 호출 뒤에 `record`한다. `expand`는 `record`만 한다. 추적기가 없으면 아무것도 막지 않고 기록하지도 않는다.
6. 성공하면 결과를 돌려주고, 실패하면 `AIConfigError`(사용자가 고칠 것, 재시도 무의미) / `AITransientError`(재시도 가능) / `RerankError`로 정규화한다. `expand`는 실패해도 원 질의만 담은 배열을, `rerank`의 호출자는 보통 입력 순서를 유지하는 쪽으로 처리한다(후자는 검색 스펙의 몫).

### 1.2 범위·통합 지점

- 제공: (a) 호출 인터페이스 `embed`·`embedOne`·`embedQuery`·`chat`·`expand`·`rerank`와 사용 가능성 질의 `isAvailable`·`diagnoseEmbedding`, (b) 모델·키·base URL 설정 규칙과 설정 키, (c) 키 없음·실패 때 호출자가 보는 동작, (d) 예산 추적(`reserve`/`record`)과 가격 조회, (e) `config`·`providers`·`models`·`pricing` 명령의 AI 관련 동작.
- 제외(이유):
  - 25개 레시피의 개별 값. 공통 계약(`Recipe`)과 대표(OpenAI, Anthropic, 기본 임베딩인 Voyage)만 다룬다. 요청 범위이고, 나머지 레시피는 같은 `Recipe` 모양의 데이터 파일이다.
  - 멀티모달 임베딩·OCR(`embedMultimodal*`, `generateOcrText`), 서브에이전트용 `toolLoop`, System One `decide`, claude-cli 서브프로세스 어댑터 내부, TypeSafe 리랭커 전송 형식. 소비자·호출 경로가 달라 별도 스펙 후보다(보고 2).
  - 예산 상한을 **정하는** 쪽: 동의(`consent`), `spend.posture`, 임베딩 비용 게이트, 일별 장부(`budget/daily-ledger.ts`). 게이트웨이는 추적기가 걸린 범위에서만 막는다. 상한을 거는 소비자는 R-68에 목록만 둔다.
  - 검색의 리랭커 활성·모델 선택(`search.reranker.*`, 검색 모드 번들)과 리랭크 실패 시 대응. 검색 스펙의 몫이다.
  - 가격표의 숫자(`CANONICAL_PRICING`, `EMBEDDING_PRICING`). 조회 규칙만 다룬다.
  - `providers`·`models` 명령의 출력 표·JSON 스키마(표현 계층). 소비 스펙이 서식에 의존하지 않으므로 동작(어떤 호출을 하고 어떤 종료 코드를 내는지)만 R-14, R-15, R-19에 둔다.
  - 안내 문구·부가 기록: 단가 없음 안내문과 `fix` 액션 구성(`budget/no-pricing.ts`), 모델별 인메모리 장부(`budget/models-used.ts`, `snapshot().models`), 파생 상한 소진 로그, 모델 404 힌트 문장(`model-not-found-hint.ts`), `chat_fallback_hop` 알림 큐(`fallback-hop-queue.ts`), 채팅 사용량 sink 저장 형식(`chat-usage.ts`), OpenRouter Claude 경로 전용 캐시 헤더, 리랭크 실패 감사 JSONL 서식(`rerank-audit.ts`). 호출 허용·거부와 반환값에 영향이 없다.
  - 가드레일 훅(`classifyGatewayGuardrail`: 사용자 메시지·질의만 보는 관찰 전용, 실패해도 무시)과 `GBRAIN_AI_CALL_LOG` 호출 로그: 호출 결과를 바꾸지 않는 관측 장치다.
- 외부 의존·선행 계약: 선행 스펙 없음. 호출자가 제공해야 하는 것은 설정 파일·환경변수의 키, 네트워크, (엔진 재구성 시) `getConfig(key)`를 가진 엔진이다. 외부 공급자 API의 실제 응답·과금은 미확인이다(1.4 확인 한계).
- 소유 상태·부작용: 프로세스 전역 `_config`·모델 캐시·쿼리 임베딩 캐시(512개, 10분)·배치 축소 상태·no_key 알림 기록·structured-output 거부 기록. 파일 쓰기는 `~/.gbrain/model-cache.json`(OpenAI 모델 발견 캐시, R-10), 예산 감사 JSONL(`~/.gbrain/audit/budget-YYYY-Www.jsonl`), 리랭크 실패 감사 JSONL, `config set`·`pricing set`의 설정 파일·DB 설정 쓰기다.

### 1.3 인터페이스와 데이터 의미

호출 인터페이스(모두 `src/core/ai/gateway.ts`, `embed`의 얇은 래퍼는 `src/core/embedding.ts`):

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `configureGateway(cfg: AIGatewayConfig)` | 설정 → 없음 | 전역 설정 교체. 모델 캐시·쿼리 임베딩 캐시·배치 축소 상태·no_key 기록을 비운다. 설정 안 된 채 호출하면 `requireConfig`가 `AIConfigError`("AI gateway is not configured")를 던진다. |
| `reconfigureGatewayWithEngine(engine)` | 엔진 → 정해진 `AIGatewayConfig` | expansion·chat 모델만 다시 정함(R-08). 여러 번 불러도 안전. |
| `isAvailable(touchpoint, modelOverride?)` | `'embedding'\|'expansion'\|'chat'\|'reranker'` → bool | 설정 없음·모델 없음·레시피 모름·터치포인트 없음·필수 키 없음이면 false. 던지지 않는다. 키 값이 유효한지는 모른다. |
| `diagnoseEmbedding(modelOverride?)` | → `{ok:true,...}` 또는 `{ok:false, reason}` | reason: `no_gateway_config`, `no_model_configured`, `unknown_provider`, `no_touchpoint`, `user_provided_dims_unset`, `missing_env`(+`missingEnvVars`). |
| `embed(texts: string[], opts?)` | 문자열 목록 → `Float32Array[]` | 입력과 같은 길이·순서. 빈 목록 → `[]`. `opts`: `abortSignal`, `maxRetries`, `inputType('query'\|'document')`, `embeddingModel`, `dimensions`. |
| `embedOne(text, opts?)` / `embedQuery(text, opts?)` | → `Float32Array` | `embedQuery`는 `input_type='query'`, `queryPrefix` 접두, 프로세스 내 LRU 캐시(R-23). |
| `embedding.ts embed(text)` / `embedBatch(texts, {onBatchComplete, abortSignal, maxRetries})` | → 벡터(들) | 래퍼. 100개씩 잘라 진행 콜백(R-27). |
| `chat(opts: ChatOpts)` | → `ChatResult` | `ChatOpts`: `model?`, `system?`, `messages: {role:'system'\|'user'\|'assistant'\|'tool', content: string \| ChatBlock[]}[]`, `tools?`, `maxTokens?`, `temperature?`, `abortSignal?`, `timeoutMs?`, `providerOptions?`, `cacheSystem?`, `responseSchema?`, `purpose?`, `thinking?:'off'`, `allowFallback?`. `ChatBlock`: `text`/`reasoning`/`tool-call`/`tool-result`. `ChatResult`: `text`, `blocks`, `stopReason('end'\|'tool_calls'\|'length'\|'refusal'\|'content_filter'\|'other')`, `usage{input_tokens,output_tokens,cache_read_tokens,cache_creation_tokens,reasoning_tokens?}`, `model`("provider:model"), `providerId`, `responseModel?`, `providerMetadata?`, `fallbackFrom?`, `fallbackReason?`. |
| `expand(query)` | 문자열 → `string[]` | 첫 원소가 원 질의. 실패·불가 시 `[query]`. 던지는 것은 호출 정책 거부뿐(R-41). |
| `rerank({query, documents, topN?, model?, signal?, timeoutMs?})` | → `{index, relevanceScore}[]` | 공급자가 준 순서 그대로(게이트웨이는 다시 정렬하지 않는다). 실패는 `RerankError(reason)`. |
| `withBudgetTracker(tracker, fn)` / `getCurrentBudgetTracker()` | | 비동기 컨텍스트(AsyncLocalStorage)에 추적기를 건다. 중첩하면 안쪽이 이기고 나가면 바깥이 복원된다. |

오류 타입(`src/core/ai/errors.ts`): `AIConfigError(message, fix?)` = 사용자가 고쳐야 함(키 없음, 모델 없음, 차원 불일치, 4xx), `AITransientError` = 재시도 가능(5xx, 429, 타임아웃, 네트워크), `RerankError(message, reason, status?)`(`reason`은 `no_key`·`auth`·`rate_limit`·`network`·`unreachable`·`timeout`·`payload_too_large`·`unknown`), `EmbeddingZeroNormError`(`code='embedding_zero_norm'`, `failures[{index,reason}]`, `vectors`(입력 정렬, 실패 자리 null)), `BudgetExhausted(reason:'cost'|'runtime'|'no_pricing', spent, cap, modelId?)`.

설정 키(원문 이름·기본값):

| 키 | 평면·환경변수 | 기본값·의미 |
|---|---|---|
| `embedding_model` | 파일 / `GBRAIN_EMBEDDING_MODEL` | `provider:model`. 없으면 "신원 미확인" 상태로 임베딩 불가(R-05). `config set` 거부(R-17). |
| `embedding_dimensions` | 파일 / `GBRAIN_EMBEDDING_DIMENSIONS`(정수) | 게이트웨이 폴백 1024(`DEFAULT_EMBEDDING_DIMENSIONS`). `config set` 거부. |
| `expansion_model` | 파일 / `GBRAIN_EXPANSION_MODEL` | 기본 `anthropic:claude-haiku-4-5-20251001` |
| `chat_model` | 파일 / `GBRAIN_CHAT_MODEL` | 기본 `anthropic:claude-sonnet-4-6` |
| `chat_fallback_chain` | 파일 / `GBRAIN_CHAT_FALLBACK_CHAIN`(쉼표 구분) | 없음. `provider:model` 목록 |
| `chat_fallback_on_refusal` | 파일 / `GBRAIN_CHAT_FALLBACK_ON_REFUSAL` | true. false면 거부된 요청을 다음 모델로 넘기지 않음 |
| `provider_base_urls.<레시피id>` | 파일 / DB(R-12) / 환경변수 `LLAMA_SERVER_BASE_URL`·`LLAMA_SERVER_RERANKER_BASE_URL`·`OLLAMA_BASE_URL`·`LMSTUDIO_BASE_URL`·`LITELLM_BASE_URL`·`OPENROUTER_BASE_URL` | 설정이 환경변수를 이긴다(R-11) |
| `provider_chat_options.<레시피id>` 또는 `.<id>:<model>` | DB/파일 | 채팅 `providerOptions` 덮어쓰기. 값은 JSON 객체 하나(점 표기 하위 키는 의미 없음) |
| `<vendor>_api_key` | 파일 (`config set`으로 파일에 씀) | `openai`·`anthropic`·`openrouter`·`voyage`·`dashscope`·`deepseek`·`litellm`·`together`·`google`·`azure_openai` (R-02) |
| `models.default`, `models.tier.{utility,reasoning,deep,subagent}`, `models.chat`, `models.expansion`, `models.aliases.<이름>`, `GBRAIN_MODEL` | DB / 환경변수 | R-08, R-09 |
| `pricing.overrides` | DB(JSON) | R-66 |
| 시간 제한 환경변수 | 프로세스 시작 시 1회 읽음 | `GBRAIN_AI_CHAT_TIMEOUT_MS`(300000, 채팅·확장), `GBRAIN_AI_EMBED_TIMEOUT_MS`(60000, 서브배치당) |
| 기타 환경변수 | | `GBRAIN_EMBED_MAX_BATCH_TOKENS`(레시피에 한도가 없을 때 운영자 한도), `GBRAIN_MODEL_DISCOVERY=off\|0`(OpenAI 발견 끔) |

`Recipe`(공통 계약, `types.ts`): `id`(소문자, `provider:model`의 provider), `tier('native'|'openai-compat')`, `implementation('native-openai'|'native-google'|'native-anthropic'|'openai-compatible'|'claude-cli')`, `auth_env.required[]`/`optional[]`(필수 키 환경변수 이름), `base_url_default`, `touchpoints{embedding?, expansion?, chat?, reranker?, decide?}`, `aliases{별칭→정식 모델 id}`, 선택 훅(`resolveAuth`, `default_headers`/`resolveDefaultHeaders`, `resolveOpenAICompatConfig`, `compat.fetch`, `probe`, `authPresent`), `billing:'subscription'`, `unpriced_models`. 임베딩 터치포인트: `models`, `default_dims`, `model_dims`, `default_model`, `dims_options`, `max_batch_tokens`·`chars_per_token`·`safety_factor`·`max_batch_items`·`no_batch_cap`, `max_input_tokens`, `matryoshka`, `user_provided_models`. 채팅: `supports_tools`, `supports_subagent_loop`, `supports_prompt_cache`, `thinking_by_default`, `supports_structured_outputs`, 컨텍스트·단가 힌트. 리랭커: `models`, `default_model`, `path`, `top_param`, `max_payload_bytes`, `default_timeout_ms`. 레시피는 `recipes/index.ts`의 정적 배열에 등록하며(25개: openai, google, anthropic, claude-cli, ollama, openrouter, voyage, litellm, deepseek, groq, together, llama-server, llama-server-reranker, lmstudio, minimax, dashscope, dashscope-rerank, zhipu, azure-openai, nan, moonshot, mistral, nvidia, perplexity, typesafe), 새 `native-*` 구현은 게이트웨이의 `instantiate*` switch도 고쳐야 한다. 필드 정의의 원본은 C-76, 등록부는 C-77이다.

CLI(AI 관련):

| 명령 | 동작 |
|---|---|
| `gbrain config show\|get <key> [--raw]\|set <key> <value> [--force --coverage-override --yes]\|unset <key>\|unset --pattern <prefix>` | 설정 읽기·쓰기. 평면 규칙은 R-16~R-18. |
| `gbrain providers list\|test [--touchpoint embedding\|chat] [--model id]\|env <id>\|explain [--json]` | 엔진 없이 동작. `list`는 레시피별 터치포인트 지원·키 준비 표, `test`는 실제 호출 1회(임베딩 `embedOne('gbrain smoke test')`, 채팅 `maxTokens:16`), `env`는 필요 환경변수, `explain`은 선택 매트릭스. |
| `gbrain models` / `models doctor [--skip=<provider>] [--json]` / `--json` | 읽기 전용 라우팅 표 / 설정된 모델에 1토큰급 호출로 도달성 점검(R-19). |
| `gbrain pricing set\|list\|unset` | `pricing.overrides` 갱신(R-66). CLI 전용. |

### 1.4 행동 규칙과 남은 질문

**설정·모델 선택**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `loadConfig()` | 파일 설정 위에 `GBRAIN_EMBEDDING_MODEL`·`GBRAIN_EMBEDDING_DIMENSIONS`(parseInt)·`GBRAIN_EXPANSION_MODEL`·`GBRAIN_CHAT_MODEL`·`GBRAIN_CHAT_FALLBACK_CHAIN`·`GBRAIN_CHAT_FALLBACK_ON_REFUSAL`이 비어 있지 않을 때 값을 덮어쓴다(환경변수 우선). `process.env`는 변경하지 않는다. (엔진 연결 뒤에는 R-12의 DB 병합이 추가된다.) C-15 | 코드 확인 |
| R-02 | 게이트웨이 `env` 만들기 | `mergedProviderEnv`: 파일의 `*_api_key`를 해당 환경변수 이름으로 접고(`CONFIG_API_KEY_ENV` 표), 그 위에 **비어 있지 않은** `process.env` 전부를 얹는다(빈 문자열·undefined는 버림, `'0'`·`'false'`는 유효). 환경변수 `GEMINI_API_KEY`는 `GOOGLE_GENERATIVE_AI_API_KEY`가 없을 때 별칭. Azure는 endpoint·deployment·Entra 값도 접는다. C-13 | 코드 확인 |
| R-03 | `configureGateway` 호출 | 모델 객체 캐시·쿼리 임베딩 캐시·배치 축소 상태·no_key 기록을 비우고, 환경변수 `GBRAIN_AI_CALL_LOG`가 있으면 호출 로그 관찰자를 설치한다. 이후 호출은 이 스냅샷의 `env`만 쓴다(키를 바꾸려면 재구성). `refreshGatewayEnvFromFilePlane()`은 모델·URL은 두고 키 env만 다시 접는다. C-12 | 코드 확인 |
| R-04 | 기본값 | `configureGateway`: `expansion_model ?? 'anthropic:claude-haiku-4-5-20251001'`, `chat_model ?? 'anthropic:claude-sonnet-4-6'`, `reranker_model`은 없으면 그대로 undefined, `embedding_dimensions`는 채우지 않는다. 읽는 쪽: `getEmbeddingDimensions() ?? 1024`, `rerank()`의 모델 = `input.model ?? getRerankerModel() ?? 'voyage:rerank-3-lite'`. `buildGatewayConfig`는 `reranker_model`을 채우지 않으므로 보통 호출자가 `input.model`을 준다. C-12, C-16, C-48, C-64 | 코드 확인 |
| R-05 | `embedding_model` 설정 없음(공백 포함) | `buildGatewayConfig`가 `embedding_identity_unverified=true`로 표시하고, `getEmbeddingModel`/`getEmbeddingDimensions`는 `AIConfigError`(저장된 벡터를 새 기본값으로 해석하면 안 됨, `gbrain migrate embeddings --status` 안내)를 던진다. 따라서 `embed`·`embedQuery`(모델 override 없을 때)가 던지고, `isAvailable('embedding')`/`diagnoseEmbedding()`(override 없을 때)은 불가(`unknown_provider`)다. `configureGateway`를 직접 부르는 경로(`providers`)는 이 표시가 없어 기본 `voyage:voyage-4`로 간다. C-14, C-16, C-17 | 코드 확인 |
| R-06 | 모델 문자열 해석 | 첫 `:`이 구분자(없으면 첫 `/`), provider는 소문자·trim. 구분자 없음·빈 provider/model → `AIConfigError`. 모르는 provider → `AIConfigError`("Unknown provider", 알려진 id 목록). `recipe.aliases`의 별칭은 정식 id로 바꾼다(`anthropic:claude-haiku-4-5` → `claude-haiku-4-5-20251001`). C-01, C-02 | 실행 확인 (`demo-pure`) |
| R-07 | 터치포인트 검사 | 레시피에 그 터치포인트가 있는지만 본다(모델 id 허용 목록 아님: `models` 배열은 안내용). 없으면 `AIConfigError`(예: Anthropic 임베딩). 예외: `rerank`는 리랭커 `models`가 비어 있지 않으면 목록에 없는 모델을 `RerankError('unknown')`로 거부한다. 존재하지 않는 모델은 공급자의 404로 호출 때 드러난다. C-03, C-48 | 실행 확인 + 코드 확인 |
| R-08 | 엔진 연결 뒤 chat·expansion 모델 결정(`resolveGatewayModels`) | 1순위부터: ①`models.chat`/`models.expansion`(DB) ②`models.tier.reasoning`/`models.tier.utility` ③`models.default` ④환경변수 `GBRAIN_MODEL` — 여기서 정해지면 끝(별칭 풀이 포함). 아니면 ⑤파일 평면 핀(`chat_model`/`expansion_model`, 환경변수 `GBRAIN_CHAT_MODEL`/`GBRAIN_EXPANSION_MODEL` 포함)이 **서비스 가능**(그 provider의 필수 키가 있음)할 때 그 핀 ⑥DB의 옛 키 `chat_model`/`expansion_model`(파일 핀이 없고 ⑤가 기본값으로 떨어진 경우만, 서비스 가능할 때만) ⑦키 인지형 티어 기본값(R-09). 서비스 불가 핀은 stderr 경고 1회 후 건너뛴다. 값에 `:`가 없으면 기존 provider 접두를 붙인다. 임베딩은 이 경로에서 다시 정하지 않는다. C-10, C-07, C-08, C-11 | 코드 확인 |
| R-09 | 티어 기본값(`resolveTierDefault`) | 병합 env에서 `ANTHROPIC_API_KEY`가 있으면 Anthropic 표(`utility` haiku-4-5, `reasoning`·`subagent` sonnet-4-6, `deep` opus-4-7), 없고 `OPENAI_API_KEY`가 있으면 OpenAI 표(R-10), 둘 다 없으면 Anthropic 표 그대로(키 없는 설치는 호출 때 실패한다). 별칭: `opus`·`sonnet`·`haiku`·`gemini`·`gpt` + 사용자 `models.aliases.<이름>`(깊이 2 초과는 중단). `subagent` 티어가 도구·서브에이전트 루프를 못 하는 모델로 풀리면 경고 후 `TIER_DEFAULTS.subagent`로 교체. C-05, C-06, C-09 | 코드 확인 |
| R-10 | OpenAI 모델 발견 | OpenAI로 가는 첫 embed/chat/expand 직전(재구성마다 1회)에 `OPENAI_API_KEY`가 있고 `GBRAIN_MODEL_DISCOVERY`가 off/0이 아니고 `gbrain setup`이 공급자 사용을 거절로 기록하지 않았으면 `GET <OPENAI_BASE_URL 또는 https://api.openai.com/v1>/models`(3초 제한)를 호출해, 가격표에 있는 모델만 골라 티어를 정하고 `~/.gbrain/model-cache.json`에 쓴다(24시간 TTL, 실패 시 10분 백오프, 계정·엔드포인트 지문이 바뀌면 즉시 재시도). 실패는 모두 무시(fail-open). 티어가 바뀌면 모델을 다시 정한다. 캐시가 없으면 `openai` 레시피 채팅 목록을 같은 문법으로 순위 매긴 정적 값을 쓴다. C-52 | 코드 확인 |
| R-11 | base URL | openai-compatible: `base_urls[레시피id] ?? recipe.base_url_default`, 둘 다 없으면 `AIConfigError`("requires a base URL"). `base_urls` = 환경변수 6종(위 표) 위에 설정의 `provider_base_urls`(설정 우선). 네이티브(openai/anthropic/google)는 환경변수 `OPENAI_BASE_URL`/`ANTHROPIC_BASE_URL`/`GOOGLE_GENERATIVE_AI_BASE_URL`만 읽고(파일의 `provider_base_urls.{anthropic,openai,google}`는 환경변수가 비었을 때만 파일 평면에서 접음, DB 값은 접지 않음), 값 끝에 `/v1`이 없으면 붙인다(Google은 버전 세그먼트가 없으면 `/v1beta`). C-14, C-30 | 코드 확인 |
| R-12 | 엔진 연결 뒤 DB 평면 병합(`mergeDbPlaneConfig` → `loadConfigWithEngine`) | 병합 대상: 제공자 API 키 10종, `expansion_model`, `chat_model`, `chat_fallback_chain`(쉼표 문자열 또는 JSON 문자열 배열), `chat_fallback_on_refusal`(`'true'`/`'false'`만), `provider_chat_options.<선택자>`(선택자당 JSON 객체 하나), `provider_base_urls.<id>`. 우선순위는 환경변수 > 파일 > DB이며 **파일·환경변수에 값이 없는 칸만** DB로 채운다. `embedding_model`·`embedding_dimensions`는 DB에서 절대 병합하지 않는다. 성공하면 병합 결과로 `configureGateway`를 다시 부른 뒤 `reconfigureGatewayWithEngine`을 부른다. 병합 실패(설정 테이블 없음 등)는 조용히 무시하고 파일·환경변수 값으로 간다. DB 값 읽기는 엔진 핸들당 ~30초 메모. 마운트된 다른 브레인에는 호스트 설정으로만 게이트웨이를 구성하고 마운트의 DB 모델 설정은 병합하지 않는다. C-65, C-66 | 코드 확인 |

**설정 명령(`config`)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-14 | `providers test [--touchpoint embedding\|chat] [--model id]` | `--model`이 있으면 같은 `buildGatewayConfig` 결과 위에 그 모델만 바꿔(임베딩은 `embedding_identity_unverified=false`, 차원 = 레시피 `default_dims ?? 1536`) 게이트웨이를 다시 구성하고, 설정된 모델과 다르면 "격리 시험이며 실제 경로를 검증하지 않는다"는 안내를 stderr에 쓴다. `isAvailable(touchpoint)`가 false면 종료 1. 아니면 실제 호출 1회(임베딩 `embedOne('gbrain smoke test')`, 채팅 `maxTokens:16`, `allowFallback:false`)를 하고 성공이면 지연·차원/응답 미리보기를 출력한다. 오류 종료 코드: `AIConfigError` 2(fix 출력), `AITransientError` 1, 그 밖 4. C-67 | 코드 확인 |
| R-15 | `providers list\|env <id>\|explain` | `list`는 게이트웨이가 보는 env(파일 키 접힘) 기준으로 레시피별 터치포인트 지원과 키 준비 상태를 표로 낸다(`authPresent` 훅이 있으면 그것, 필수 키가 없으면 준비됨). `env`는 레시피의 필수·선택 환경변수를 낸다(모르는 id는 종료 1). `explain`은 선택 매트릭스를 내고 로컬 서버(Ollama, LM Studio)는 1초 제한으로 점검한다. 세 명령 모두 엔진 없이 동작하고 `test` 외에는 공급자 호출을 하지 않는다. | 코드 확인 |
| R-16 | `config set <vendor>_api_key <값>`(`FILE_PLANE_API_KEYS` 10개) | DB가 아니라 `~/.gbrain/config.json`에 쓰고 값은 `***`로 가려 출력한다. `unset`도 파일에서 지운다(없으면 "not found", 종료 1). `database_url`/`database_path`도 파일로 라우팅, `engine`은 직접 설정 거부. C-60 | 코드 확인 |
| R-17 | `config set embedding_model\|embedding_dimensions` | 항상 거부(종료 1, `--force`도 소용없음): 파일 평면의 스키마 크기 설정이라 DB에 써도 무시된다. 이미 임베딩 중이면 `gbrain migrate embeddings --to <model> [--dim N] --dry-run`을, 아니면 임베딩 켜는 명령을 안내한다. C-61 | 코드 확인 |
| R-18 | `config set <그 외 키>` | 알려진 키(`KNOWN_CONFIG_KEYS`)·접두(`models.` 등)가 아니면 "Unknown config key"+가장 가까운 키 제안 후 종료 1, `--force`면 경고하고 씀(`budget.*`는 어떤 것도 읽지 않는 키라고 안내하고 `spend.posture`로 유도). 알려진 키는 DB 설정(`engine.setConfig`)에 쓴다. `chat_model`/`expansion_model`을 DB에 쓰면 `models.*`·`GBRAIN_MODEL`·환경변수·파일 핀 중 더 높은 것이 있을 때 그것이 이긴다고 경고한다. `get`은 환경변수·파일 평면이 DB를 이기며 어느 평면이 답했는지 stderr에 쓰고, 비밀 키는 `--raw` 없이는 `***`. C-60, C-62 | 코드 확인 |
| R-19 | `models doctor` | 엔진 설정으로 임베딩·리랭커 설정 점검(토큰 0), 설정된 chat·expansion 모델에 `chat({maxTokens:16, allowFallback:false})` 호출, 임베딩 도달성, 리랭커가 켜진 경우 리랭커 도달성을 점검하고 하나라도 실패면 종료 1. `--skip=<provider>`로 건너뛴다. `models`(읽기)는 라우팅 표만 출력한다. | 코드 확인(흐름) |

**임베딩 호출**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | `embed(texts)` 입력 처리 | 각 텍스트를 8000자로 자른다(서로게이트 쌍을 쪼개지 않음; null/undefined는 빈 문자열). 공백뿐인 입력은 공급자에 보내지 않는다. 결과는 항목별로 검사해, 빈 입력·영벡터(노름<1e-6)·NaN/Inf가 하나라도 있으면 `EmbeddingZeroNormError`를 던지되 나머지 항목의 벡터는 오류의 `vectors`(입력 정렬)에 담아 준다. C-18, C-19 | 실행 확인 (`demo-pure`: 절단, 영벡터·빈 입력) |
| R-21 | 요청 분할 | 레시피 `max_batch_tokens`(없으면 `GBRAIN_EMBED_MAX_BATCH_TOKENS`)가 있으면 `max_batch_tokens × safety_factor`(레시피 기본 0.8, 축소 상태 반영) 토큰 예산으로 앞에서부터 묶는다(토큰 추정 = `ceil(글자수/chars_per_token)`, 기본 4). `max_batch_items`(또는 `no_batch_cap`이면 16)로 개수 상한을 한 번 더 자른다. 한도 선언이 없으면 한 요청이다. 공급자가 토큰 한도 오류를 내면(`isTokenLimitError`) 그 서브배치를 반으로 나눠 재귀하고, 레시피의 안전계수를 ×0.5(하한 0.05)로 줄이며, 연속 10회 성공하면 ×1.5씩(선언값까지) 되돌린다. 1개짜리 서브배치는 더 쪼개지 않고 오류로 낸다. C-18, C-20, C-21, C-22 | 실행 확인 (`demo-pure`: 분할 결과) + 코드 확인(축소) |
| R-22 | 차원 | 유효 차원 = `opts.dimensions ?? cfg.embedding_dimensions ?? 1024`. 공급자 옵션: OpenAI `text-embedding-3-*` → `{openai:{dimensions}}`(범위 1..1536(small)/3072(large) 밖이면 `AIConfigError`), Google `gemini-embedding*`·`text-embedding-004` → `outputDimensionality`, Voyage 가변 차원 모델 → `output_dimension`(256/512/1024/2048 외는 `AIConfigError`), 그 외는 옵션 없음. 응답 벡터 길이가 유효 차원과 다르면(선언된 Matryoshka 앞부분 자르기 후에도) `AIConfigError`("Embedding dim mismatch", 마이그레이션 안내). 레시피 `default_dims`(`embeddingDimsForModel`)는 게이트웨이 안에서는 `diagnoseEmbedding`의 "차원 미설정" 판정에만 쓰인다(`user_provided_models`이거나 선언 차원 0인데 `embedding_dimensions`가 없으면 불가). C-04, C-17, C-23, C-24, C-26 | 코드 확인 + 실행 확인(`embeddingDimsForModel`) |
| R-23 | `embedQuery` | `input_type='query'`로 보낸다(호출자가 `inputType`을 주지 않는 문서 임베딩은 `input_type`을 보내지 않는다. NVIDIA 모델은 `query`가 아니면 `passage`를 보낸다). `queryPrefix`가 있으면 앞에 붙인다. 캐시 키 = (레시피, 모델, base URL, 차원, 실제 전송 문자열), 512개 LRU·10분 TTL, 읽기·쓰기는 복사본, `configureGateway`가 비우고 비우기 전에 시작한 호출은 저장하지 않는다. 호출 가드(R-69)가 걸려 있으면 캐시를 읽지 않는다. C-27 | 코드 확인 |
| R-24 | 시간 제한·재시도 | 서브배치마다 `AbortSignal.timeout(60s)`(`GBRAIN_AI_EMBED_TIMEOUT_MS`)와 호출자 `abortSignal`을 `any`로 합친다(짧은 쪽이 이김). `maxRetries`는 호출자가 줄 때만 SDK에 넘기고, 호출 가드가 걸리면 0이다. SDK 기본 재시도 횟수는 SDK의 몫이다(소스 주석은 2회, 미확인). C-20, C-22 | 코드 확인 |
| R-25 | 임베딩 실패 매핑 | `normalizeAIError`: 상태 4xx(429 제외) → `AIConfigError`(404 또는 메시지가 model-not-found 정규식에 맞으면 모델 확인 안내, 401/403은 키 확인 안내), `LoadAPIKeyError`·`InvalidArgumentError` → `AIConfigError`, 그 밖(5xx·429·타임아웃·네트워크) → `AITransientError`. 메시지는 컨텍스트 `[embed(provider:model)]`가 붙고 현재 env의 키 값은 지워진다. 추가로 임베딩 401/403은 프로세스당 첫 1회 stderr에 `[gbrain] Error [embedding_auth_failed]: ... Fix: ...`(어느 키 출처가 쓰였는지 이름만, 키 값은 없음)를 출력하고, 이 출력이 원래 오류를 대체하지는 않는다. Google 임베딩의 400/413/422 거절은 호출 가드의 비과금으로 처리한다(다른 공급자는 최대치 유지). C-31, C-32, C-33, C-68, C-69 | 코드 확인 |
| R-26 | 키 없음(임베딩) | `embed`는 공급자 호출·예산 `reserve` 전에 `AIConfigError("<공급자> embedding requires <ENV>.", fix=setup_hint)`를 던진다(재시도 없음). 사전 점검은 `isAvailable('embedding')`(불리언) 또는 `diagnoseEmbedding()`(이유). `validateEmbeddingCreds()`는 이유별 안내문을 담은 `EmbeddingCredentialError`를 던진다(sync·embed·import 입구가 사용, `--no-embed` 안내 포함). OpenAI는 `OPENAI_BASE_URL`이 있으면 키 없이도 가능(`'unauthenticated'` 자리표시자). 필수 키가 없는 레시피(Ollama 등)는 항상 가능. C-17, C-29, C-30, C-34 | 코드 확인 |
| R-27 | `embedBatch(texts, opts)` | 비어 있으면 `[]`. 100개 이하이고 `onBatchComplete`가 없으면 `embed` 한 번. 아니면 100개씩 순서대로 `embed`하고 조각마다 `onBatchComplete(done,total)`을 부른다. `EmbeddingZeroNormError`만 모아 두었다가 끝에서 전체 입력 정렬로 합쳐 던지고(성공 벡터 유지), 다른 오류는 즉시 전파한다. `embedding.ts embed(text)`는 `embedOne`이다. C-28 | 코드 확인 |

**채팅·확장·리랭크**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-30 | `chat(opts)` 기본 | 모델 = `opts.model ?? chat_model`. 최대 출력 = `opts.maxTokens ?? 4096`(Claude 5 계열이거나 레시피가 `thinking_by_default`인 모델은 32000). 시간 제한 = `opts.timeoutMs ?? 300000`ms를 호출자 신호와 합친다. `temperature`는 지정했을 때만 전달. `stopReason`: Anthropic `refusal`→`refusal`, `content-filter`→`content_filter`, `tool-calls`→`tool_calls`, `length`/`max-tokens`→`length`, `stop`/`end`/`end-turn`→`end`, 나머지 `other`. 성공 시 사용량을 등록된 sink로 흘리고(실패·미등록은 무시), 호출 가드가 있으면 허가를 받는다. C-35, C-36, C-37, C-38 | 코드 확인 |
| R-31 | 키 없음·불가(채팅) | `chat`은 호출 자체에서 `AIConfigError`를 던진다: 게이트웨이 미설정, 모르는 provider, 채팅 터치포인트 없음, 또는 `"<공급자> chat requires <ENV>."`(fix=setup_hint). 이 오류는 공급자 해석 단계에서 나므로 예산 보류는 `finally`에서 풀린다. 호출자는 `isAvailable('chat', model)`로 미리 거를 수 있고(레시피가 채팅을 갖고 `auth_env.required`가 모두 env에 있으면 true), 거르지 않은 호출은 던진다. C-17, C-36, C-37 | 코드 확인 |
| R-32 | 채팅 공급자 실패 | `normalizeAIError(err, 'chat(provider:model)', 키 가리기, 모델 404 힌트)`로 던진다. 예산 기록은 공급자가 알려준 사용량, 없으면 최악치(추정 입력, `maxOutputTokens`)를 `.failed`로 남긴다. 정책 거부(호출 가드)는 정규화·기록 없이 그대로 던진다. C-31, C-37 | 코드 확인 |
| R-33 | `chat_fallback_chain`이 있고 `allowFallback !== false` | 시도 순서 = 호출 모델, 그다음 체인에서 아직 안 쓴 것. 각 시도는 완전한 단일 모델 `chat()`(예산·사용량·가드 포함)이다. 다음으로 넘어가는 경우: 공급자 오류, 또는 `stopReason`이 `refusal`/`content_filter`(`chat_fallback_on_refusal !== false`일 때). 멈추는 경우: 호출 가드 거부, `BudgetExhausted`, 호출자 중단 신호, 체인 끝. `chat_fallback_on_refusal=false`면 구조적 거부는 그 결과를 반환하고 공급자의 콘텐츠 정책 오류는 던진다. 체인 모델이 답하면 `fallbackFrom`(호출 모델)·`fallbackReason`(≤200자)이 붙는다. 모두 실패하면 앞선 거부 결과가 있으면 그것을, 아니면 호출 모델의 오류를 던진다. 첫 홉은 `chat_fallback_hop` 안전 알림 1건을 큐에 넣는다. C-44, C-70 | 코드 확인 |
| R-34 | 채팅 옵션 조립 | `providerOptions`는 이 순서로 합친다(깊은 병합, 뒤가 이김): ①`cacheSystem`이고 레시피가 프롬프트 캐시를 지원하면 `anthropic.cacheControl={type:'ephemeral'}` ②네이티브 OpenAI이고 `system`이 있으면 `openai.promptCacheKey` ③설정 `provider_chat_options`(`<id>` 다음 `<id>:<model>`) ④호출의 `opts.providerOptions` ⑤`thinking:'off'`면 모델별 끄기 옵션(Anthropic·DeepSeek은 `thinking:{type:'disabled'}`, 끌 수 없는 모델은 출력 한도를 32000까지 올림). 시스템 프롬프트는 캐시 표시가 필요하면 `providerOptions`를 가진 system 메시지 객체로 보낸다. `responseSchema`는 `supports_structured_outputs`인 openai-compatible 레시피에서만 적용하고, 공급자가 json_schema를 거부하면 스키마 없이 1회 재시도하며 그 레시피를 프로세스 동안 기억한다. 메시지는 `toModelMessages`로 SDK 형식으로 바꾸고(도구 결과는 `tool` 역할), 짝 없는 `tool-call`은 `repairToolPairing`이 오류 스텁 결과를 채운다. C-35, C-39, C-40, C-41, C-43 | 코드 확인 |
| R-40 | `expand(query)` 입구 | 질의가 비거나 공백이면 `[query]`. `isAvailable('expansion')`이 false이면(확장 모델의 레시피에 `expansion` 터치포인트가 없거나 필수 키가 없음) 아무 출력 없이 `[query]`를 돌려준다. 가드레일 훅은 관찰만 한다. C-46 | 코드 확인 |
| R-41 | `expand` 실행·결과 | 구현 선택: `claude-cli`와 "구조화 출력 미지원 openai-compatible" → 텍스트 생성 후 `parseLlmJson` 허용 파싱(`queries`만 검증), 네이티브(OpenAI·Anthropic·Google)는 `generateObject`(스키마 `{queries: string[1..5]}`, 이름 `query_expansions`, 실패하면 폴백 없이 `[query]`), 구조화 지원 openai-compatible도 같은 호출을 하되 공급자가 거부하면 텍스트 경로로 1회 재시도하고 그 레시피를 기억한다. 결과 = `[원 질의, ...확장]`에서 소문자·trim 기준 중복과 빈 문자열 제거. 프롬프트는 3~4개 재작성을 요구하지만 스키마는 1~5개를 받으므로 결과는 최대 6개가 될 수 있다. 실패하면 `[query]`; `AIConfigError`일 때만 `[ai.gateway] expansion disabled: ...` 경고를 콘솔에 쓰고 일시 오류는 조용하다. 호출 가드 거부는 그대로 던진다. **`BudgetExhausted`는 던지지 않는다**(R-61). C-45, C-46, C-47, C-50 | 코드 확인 |
| R-50 | `rerank(input)` 입구 | `query`가 비면 `RerankError('unknown')`, 문서가 없으면 `[]`. 모델 = `input.model ?? getRerankerModel() ?? 'voyage:rerank-3-lite'`. 모르는 provider는 `AIConfigError`(RerankError 아님), 리랭커 터치포인트 없음·모델 목록 불일치는 `RerankError('unknown')`. | 코드 확인 |
| R-51 | 키 없음(리랭크) | 커스텀 `resolveAuth`가 없는 레시피에서 `auth_env.required` 중 env에 없는 것이 있으면 HTTP 없이 `RerankError('no_key')`를 던진다. 프로세스·모델당 첫 1회만 리랭크 실패 감사 JSONL에 `no_key` 행을 쓰고 아무것도 출력하지 않는다. 키가 있는데 서버가 401/403이면 `auth`다. 인증 해석 자체의 `AIConfigError`는 `RerankError('auth')`로 바뀐다. C-48, C-49 | 코드 확인 |
| R-52 | 리랭크 호출 | `POST <baseURL><tp.path ?? '/rerank'>`, 본문 `{model, query, documents, [top_param ?? 'top_n']: topN}`(`topN`이 있을 때). 본문 바이트가 `max_payload_bytes`를 넘으면 호출 전에 `RerankError('payload_too_large')`. 시간 제한 `input.timeoutMs ?? 5000`ms(`timeout`). HTTP 실패: 401/403→`auth`, 429→`rate_limit`, ≥500→`network`, 그 외→`unknown`(본문 앞 500자 포함). 연결 실패→`unreachable`. 응답 JSON의 `results[]` 또는 `data[]`를 받아 `{index, relevanceScore(=relevance_score, 없으면 0)}`로 바꾼다. 둘 다 없으면 `RerankError('unknown')`. C-48 | 코드 확인 (공급자 실제 응답은 미확인) |

**예산 추적**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-60 | 추적기가 없는 컨텍스트 | `embed`·`chat`·`rerank`·`expand`는 `reserve`도 `record`도 하지 않는다. 즉 아무것도 막지 않는다. 게이트웨이는 스스로 추적기를 만들지 않는다. C-20, C-36, C-48 | 코드 확인 |
| R-61 | 추적기가 있는 컨텍스트 | `embed`·`chat`·`rerank`: 공급자 호출 전에 `reserve`, 호출 뒤(성공·실패 모두) `record`, 호출이 공급자에 닿지 않았으면 `release`. `reserve`가 던지는 `BudgetExhausted`는 정규화 없이 그대로 호출자에게 전파되고 호출은 일어나지 않는다(`chat` 폴백 체인도 거기서 멈춘다). 임베딩은 키·차원·분할 사전 점검이 다 끝난 뒤에 `reserve`하므로 설정 오류가 보류를 남기지 않는다. 리랭크는 no_key·payload 점검 뒤에 `reserve`한다. `expand`는 `reserve`를 부르지 않고 성공(`gateway.expand`)·실패(`gateway.expand.failed`, 최악치 입력 추정+출력 512토큰)만 `record`하므로 어떤 상한도 `expand`를 막지 못한다. C-20, C-36, C-45, C-48 | 코드 확인 |
| R-62 | `reserve(estimate)` | ①`maxRuntimeMs`가 있고 경과 시간이 초과면 `BudgetExhausted('runtime')` ②예상 비용 = `(입력추정×입력단가 + maxOutputTokens×출력단가)/1e6`(R-65 조회). 단가가 없으면(unpriced): 사용자 상한(`capSource` 'user'이면서 `maxCostUsd` 설정)이면 `BudgetExhausted('no_pricing')`(+`gbrain pricing set` 안내) 후 감사 행; 상한이 없거나 derived/default 상한이면 stderr에 `BUDGET_TRACKER_NO_PRICING` 경고를 (모델·종류당) 1회 쓰고 보류 없이 진행 ③`누적 + 보류중 + 예상 > maxCostUsd`이면 `BudgetExhausted('cost')`+`reserve_denied` 감사 ④통과하면 상한이 있을 때만 `r<번호>` 보류를 잡는다. 각 `BudgetExhausted` 직전에 `onExhausted` 콜백을 1회 호출한다. C-51 | 코드 확인 |
| R-63 | `record(actual)` | 비용을 계산해 누적에 더하고 보류가 있으면 풀며 모델별 장부와 감사 행을 남긴다. 누적이 상한을 넘으면 그 시점에 `BudgetExhausted('cost')`를 던지지만, 게이트웨이의 `recordOnTracker`가 이를 **삼킨다**: 호출 결과·오류는 그대로이고 초과는 다음 `reserve`에서 드러난다. 단가 없는 모델이 실제로 응답하면 비용 미상으로 기록하되, 잡혀 있던 보류액이 있으면 그 금액을 지출로 확정한다. 감사 파일 쓰기 실패는 무시한다. C-51, C-53 | 코드 확인 |
| R-64 | 추정·측정 | 채팅 입력 추정 = (system+텍스트 블록+도구 호출 입력/결과+도구 정의 글자수)/4 올림. 임베딩 예약 = 절단된 입력 글자수/`chars_per_token`(기본 4); 기록은 모든 서브배치가 사용량(`usage.tokens`)을 보고했을 때만 그 합, 아니면 추정치(`estimated`). 리랭크 = (질의+문서 글자수)/(레시피 임베딩 `chars_per_token` ?? 4), 기록도 추정치. 실패 기록은 공급자 사용량이 있으면 그것, 없으면 최악치. C-42, C-53 | 코드 확인 |
| R-65 | 가격 조회(`priceFor`) | 순서: 운영자 `pricing.overrides`(정확 일치→정식화한 키→`<provider>:*` 와일드카드; 와일드카드는 `billing:'subscription'` 공급자만) → 표 조회(채팅·리랭크: Anthropic 표, 별칭 정식화, `canonicalLookup`; 임베딩·리랭크·decide: `lookupEmbeddingPrice`) → 무료 로컬(임베딩 `ollama`·`llama-server`·`lmstudio`, 채팅 `ollama`·`llama-server`, 리랭크 `llama-server-reranker`는 0달러). 없으면 null(unpriced). 긴 프롬프트 임계를 넘으면 요청 전체를 상위 단가로 계산한다(`priceAtPromptSize`). 가격표 값은 이 스펙 밖. C-53, C-54, C-55 | 실행 확인(`demo-pure`) + 코드 확인 |
| R-66 | `pricing.overrides` | DB 설정의 JSON 객체. 값은 숫자 하나(입력=출력 단가) 또는 `{input, output?}`/`{pricePerMTok}`; 소문자 키로 정규화, 음수·비유한 값·허용 안 되는 키(`*` 단독, 종량제 공급자의 와일드카드)는 버려 그 모델은 unpriced로 남는다. 읽기 실패는 undefined(fail-open). `gbrain pricing set <model> --input X --output Y`/`--rate X [--source url]`는 읽어서 한 항목만 바꿔 다시 쓴다(`config set pricing.overrides`는 통째 교체). `pricing`은 CLI 전용이며 MCP로 도달할 수 없다. C-56, C-57 | 코드 확인 |
| R-67 | 감사 JSONL | 추적기는 `reserve`·`reserve_denied`·`reserve_no_pricing`·`reserve_unpriced`·`release`·`record`·`record_unpriced`·`runtime_denied` 행을 `~/.gbrain/audit/budget-YYYY-Www.jsonl`(ISO 주 단위, `schema_version:1`)에 덧붙인다. 쓰기 실패는 무시한다. C-51 | 코드 확인 |
| R-68 | 추적기를 거는 쪽 | 게이트웨이 밖에서 `new BudgetTracker({maxCostUsd,...})` + `withBudgetTracker`로 거는 소비자 예: 임베딩 실행의 `embedCostCap`(상한이 양수일 때), 사실 추출 drain, 재색인, 백필, 브레인스톰, 평가. 사실 추출 백스톱은 앰비언트 추적기가 없으면 **상한 없는** 기록 전용 추적기를 건다(절대 `BudgetExhausted`를 못 던짐). 상한 값·동의 흐름은 각 소비 스펙의 몫이다. | 코드 확인 (grep) |
| R-69 | 호출 가드·관찰 | `withAIInvocationGuard`가 걸려 있으면 모든 공급자 시도 전에 허가를 받고, 거부 오류는 폴백·정규화를 건너뛰고 그대로 전파된다(`isAIInvocationPolicyError`). 가드가 있으면 SDK 재시도는 0이다. 관찰자·미터는 실행을 바꾸지 않고 호출마다 이벤트(모델, 결과, 사용량, ms)를 받는다. C-58 | 코드 확인 |

- 불변식: (1) `embed`·`chat`·`expand`·`rerank` 호출 경로는 설정·키를 스냅샷 `env`에서 읽는다. 호출 시점의 `process.env` 읽기는 두 가지뿐이다: OpenAI로 가는 호출 직전의 `GBRAIN_MODEL_DISCOVERY`(R-10), 모듈 로드 시 시간 제한 환경변수. 모델 재결정(`resolveModelDetailed`)은 `process.env.GBRAIN_MODEL`을 직접 읽는다(재구성 시점). (2) `embed`의 결과는 입력과 같은 길이·순서이거나 던진다(일부만 반환하지 않음; 영벡터는 `vectors`로 구조화해 던짐). (3) `reserve`가 던지면 공급자 호출은 일어나지 않는다. (4) `BudgetExhausted`는 `record`에서 던져져도 게이트웨이 호출자에게 나가지 않는다.
- 미결정: 없음. (R-10의 OpenAI 순위 규칙은 C-52로, 가격 조회 규칙은 C-53~C-55로 닫혀 있다. 가격표 숫자 자체와 25개 레시피 값은 데이터이며 1.2에서 제외했다.)
- 확인 한계: 외부 공급자 API의 실제 응답 형식·한도·과금(예: Voyage `output_dimension` 값, OpenAI `/models` 응답, 리랭크 응답 모양)은 코드가 "그렇게 가정했다"는 증거일 뿐 실제 호출로 확인하지 않았다(미확인). 외부 AI SDK(`ai`, `@ai-sdk/*`)의 기본 재시도 횟수·메시지 변환 내부도 미확인이다. 실행 확인은 `deno`로 순수 함수만 돌린 결과다(`agent-memory/artifacts/gbrain/ai-gateway-demos/`); `BudgetTracker` 자체와 게이트웨이 함수는 의존 모듈(JSON import, AI SDK) 때문에 이 환경에서 실행하지 않았다(코드 확인).

### 1.5 필수 코드 참조

라이선스 인용 허용 여부는 overview 1절을 따른다(이 문서는 규칙의 위치만 가리킨다). 줄 번호는 모두 기준 SHA다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/core/ai/model-resolver.ts:26-57` `parseModelId` | `provider:model` 해석(콜론 우선, 슬래시 대체, 오류 3종) | R-06 |
| C-02 | `src/core/ai/model-resolver.ts:64-79` `resolveRecipe` | 레시피 조회·별칭 정식화·모르는 provider 오류 | R-06 |
| C-03 | `src/core/ai/model-resolver.ts:113-129` `assertTouchpoint` | 터치포인트 존재만 검사 | R-07 |
| C-04 | `src/core/ai/model-resolver.ts:154-194` `embeddingDimsForModel`, `lookupDims` | 모델별 차원(대소문자 무시, `provider:` 접두 제거 재시도) → `default_dims` → 0 | R-22 |
| C-05 | `src/core/model-config.ts:64-96` `DEFAULT_ALIASES`, `TIER_DEFAULTS` | 별칭·티어 기본 모델 표 | R-09 |
| C-06 | `src/core/model-config.ts:107-225` `openaiStaticTierFallback`, `PROVIDER_TIER_DEFAULTS`, `resolveTierDefault`, `providerKeyReady` | 키 인지형 티어 기본값, 서비스 가능 판정 | R-09 |
| C-07 | `src/core/model-config.ts:227-302` `resolveEffectiveModelForTier` 외 | 파일 핀·`GBRAIN_MODEL` 우선순위, 서비스 불가 핀 경고 | R-08 |
| C-08 | `src/core/model-config.ts:449-522` `resolveModelDetailed` | CLI 플래그→새 키→옛 키→`models.tier.*`→`models.default`→환경변수→티어 기본값→폴백(티어가 있으면 폴백은 도달하지 않음) | R-08 |
| C-09 | `src/core/model-config.ts:661-680` `resolveAlias` | 사용자 별칭→기본 별칭→그대로, 깊이 2 중단 | R-09 |
| C-10 | `src/core/ai/gateway.ts:574-644` `resolveGatewayModels`, `prefixWithProviderFrom` | 엔진 연결 뒤 chat·expansion 재결정 순서와 접두 규칙 | R-08 |
| C-11 | `src/core/ai/legacy-model-pin.ts:15-32` `readLegacyModelPin` | DB 옛 키 `chat_model`/`expansion_model`이 적용되는 조건 | R-08 |
| C-12 | `src/core/ai/gateway.ts:133-134`, `459-493` 기본 모델 상수, `configureGateway` | 기본값, 캐시 비우기 | R-03, R-04 |
| C-13 | `src/core/ai/provider-env.ts:37-86` `CONFIG_API_KEY_ENV`, `mergedProviderEnv` | 키 접기·환경변수 우선·별칭 | R-02 |
| C-14 | `src/core/ai/build-gateway-config.ts:6-97` `foldNativeBaseUrlsFromFilePlane`, `buildGatewayConfig` | 환경변수→`base_urls`, 파일 평면 native URL 접기, `embedding_identity_unverified` | R-05, R-11 |
| C-15 | `src/core/config.ts:741-759` `loadConfig` 병합부 | AI 관련 환경변수 덮어쓰기 | R-01 |
| C-16 | `src/core/ai/gateway.ts:826-907` `requireConfig`, getter들 | 미설정 오류, 임베딩 신원 미확인 오류, 기본값 | R-04, R-05 |
| C-17 | `src/core/ai/gateway.ts:934-1092` `diagnoseEmbedding`, `isAvailable` | 사용 가능성 판정과 이유 | R-05, R-22, R-26, R-31 |
| C-18 | `src/core/ai/embed-batch-plan.ts:13-110` | 8000자 절단, 토큰 예산 분할, 개수 상한, 상수 | R-20, R-21 |
| C-19 | `src/core/ai/embedding-guard.ts:14-131` | 빈 입력·영벡터 검사, `EmbeddingZeroNormError`, 위치 복원 | R-20 |
| C-20 | `src/core/ai/gateway.ts:1599-1683` `embed` | 임베딩 호출 순서, 예약·기록 | R-20~R-24, R-60, R-61, R-64 |
| C-21 | `src/core/ai/gateway.ts:218-227`, `1690-1700`, `1706-1738` `isTokenLimitError`, 안전계수 축소·회복 | 안전계수 축소·회복 | R-21 |
| C-22 | `src/core/ai/gateway.ts:1759-1833` `embedSubBatch` | 서브배치 호출, 차원 검사, 반분 재귀, 오류 정규화 | R-21, R-22, R-24, R-25 |
| C-23 | `src/core/ai/dims.ts:36-99` | Voyage 가변 차원 모델·허용 차원, OpenAI 허용 범위 | R-22 |
| C-24 | `src/core/ai/dims.ts:163-322` `dimsProviderOptions` | 구현체별 차원·input_type 공급자 옵션 | R-22, R-23 |
| C-25 | `src/core/ai/gateway.ts:237`, `250-255`, `1096`, `1117-1245` `voyageCompatFetch` | Voyage 요청(`encoding_format=base64`, `dimensions`→`output_dimension`, `input_type` 복원)·응답(base64 float32 디코드, `prompt_tokens` 보정, 256MiB 상한). `MAX_VOYAGE_RESPONSE_BYTES`=256×1024×1024 | R-22 |
| C-26 | `src/core/ai/voyage-gateway.ts:10-51` | 출력 차원 필드 설정, 차원 불일치 오류 문구 | R-22 |
| C-27 | `src/core/ai/query-embed-cache.ts:16-50` | 쿼리 임베딩 캐시 | R-23 |
| C-28 | `src/core/embedding.ts:79-111` `embedBatch` | 100개 분할, 진행 콜백, 영벡터 오류 합치기 | R-27 |
| C-29 | `src/core/ai/gateway.ts:1428-1517` `resolveEmbeddingProvider`, `instantiateEmbedding` | 구현체별 키 확인·클라이언트 생성 | R-26 |
| C-30 | `src/core/ai/gateway.ts:287-456` 인증·base URL 해석, `recipeSupportsStructuredOutputs` | 기본 인증, 헤더 충돌 검사, base URL | R-11, R-26 |
| C-31 | `src/core/ai/errors.ts:14-47` | 오류 클래스 | R-25, R-32 |
| C-32 | `src/core/ai/errors.ts:86-156` `KNOWN_MODEL_RENAMES`, `modelNotFoundFix`, `normalizeAIError` | 상태→오류 클래스 매핑, 힌트 | R-25, R-32 |
| C-33 | `src/core/ai/errors.ts:277-363` `MODEL_NOT_FOUND_MESSAGE_RE`, `numericStatusOf`, `wrappedErrorLayers`, `isStructuredOutputRejection` | 모델 없음 메시지 정규식, 상태 읽기, 래핑된 오류 층 순회, 구조화 출력 거부 판정 | R-25, R-34 |
| C-34 | `src/core/embed-preflight.ts:48-128` | 이유별 안내문 | R-26 |
| C-35 | `src/core/ai/gateway.ts:2864-2897` | 기본 출력 토큰, Claude 5 판별, `isThinkingModel`(레시피 `thinking_by_default`가 참, 함수면 모델 id로 평가, 레시피 없으면 false) | R-30 |
| C-36 | `src/core/ai/gateway.ts:3540-3577` `chat` | 폴백 위임, 가드레일, 예약, `finally` 해제 | R-30, R-31, R-33, R-61 |
| C-37 | `src/core/ai/gateway.ts:3188-3201`, `3284-3350`, `3621-3864` `jsonSchemaOutput`, `chatSupportsPromptCache`, 채팅 공급자 생성, `chatAdmitted` 운영 경로 | 구현체별 키 확인, 옵션 조립, 호출, 결과 정규화, 실패 기록 | R-30~R-32, R-34 |
| C-38 | `src/core/ai/gateway.ts:3357-3370` `mapStopReason` | 종료 사유 매핑 | R-30 |
| C-39 | `src/core/ai/gateway.ts:2911-3076` `toJsonSafe`~`repairToolPairing` | 메시지→SDK 형식, 도구 쌍 복구 | R-34 |
| C-40 | `src/core/ai/gateway.ts:3436-3477` 깊은 병합, `applyConfiguredChatProviderOptions` | `provider_chat_options` 병합 | R-34 |
| C-41 | `src/core/ai/gateway.ts:3515-3538` `openAIPromptCacheKey`, `toAISDKTools` | 프롬프트 캐시 키, 도구 정의 변환 | R-34 |
| C-42 | `src/core/ai/chat-input-estimate.ts:20-50` | 채팅 입력 토큰 추정 | R-64 |
| C-43 | `src/core/ai/thinking-off.ts:53-149` | `thinking:'off'` 모델별 표(선택 옵션, 대표 규칙은 R-34) | R-34 |
| C-44 | `src/core/ai/chat-fallback.ts:52-152` | 체인 정규화·시도 순서·넘어가기·멈추기 | R-33 |
| C-45 | `src/core/ai/gateway.ts:2426-2481` `ExpansionSchema`, `parseExpansionResponse`, 추정 상수, `normalizeSdkUsage` | 확장 스키마·파싱·최악치 추정 | R-41, R-61 |
| C-46 | `src/core/ai/gateway.ts:2488-2671` `expand` | 입구 검사, 구현 선택, 기록, 중복 제거, 실패 시 `[query]` | R-40, R-41, R-61 |
| C-47 | `src/core/ai/expansion-prompt.ts:6-14` | 확장 프롬프트 원문 | R-41 |
| C-48 | `src/core/ai/gateway.ts:4258-4507` `RerankError`, `rerank` | 리랭크 전체(검사 순서, 요청, 오류 매핑, 예약) | R-07, R-50~R-52, R-60, R-61 |
| C-49 | `src/core/ai/gateway.ts:1408-1426` `noKeyOnce` | 프로세스·모델당 1회 감사 행 | R-51 |
| C-50 | `src/core/llm-json.ts:1-175` `parseLlmJson` | 펜스·추론 블록 제거 후 JSON 허용 파싱(실패 시 null) | R-41 |
| C-51 | `src/core/budget/budget-tracker.ts:245-632` `appendAuditLine`, `BudgetTracker` | `reserve`/`release`/`record` 전체, 감사 행 | R-62, R-63, R-67 |
| C-52 | `src/core/ai/gateway.ts:540-572`, `src/core/ai/openai-latest.ts:89-413` 발견 호출 지점, 순위 문법, 캐시, `refreshLatestOpenAIModels` | OpenAI 티어 순위와 발견 흐름 | R-10 |
| C-53 | `src/core/budget/reservation-cost.ts:33-253` | 가격 조회 순서, 무료 로컬 집합, 비용 계산 | R-63, R-64, R-65 |
| C-54 | `src/core/model-pricing.ts:94-107`, `286-319`, `src/core/anthropic-pricing.ts:33-37`, `src/core/model-id.ts:42-64` `priceAtPromptSize`, `canonicalLookup`, `ANTHROPIC_PRICING`(정식 표의 `anthropic:` 행을 접두 없이 본 뷰), `splitProviderModelId` | 긴 프롬프트 단가, 정식 가격표 조회 규칙 | R-65 |
| C-55 | `src/core/embedding-pricing.ts:102-138` `lookupEmbeddingPrice` | 임베딩 단가 조회(별칭, 중첩 id) | R-65 |
| C-56 | `src/core/budget/budget-tracker.ts:147-203` `parsePricingOverrides`, `loadPricingOverrides` | 오버라이드 정규화 | R-66 |
| C-57 | `src/commands/pricing.ts:59-121` | `pricing set` 병합 규칙 | R-66 |
| C-58 | `src/core/ai/invocation-guard.ts:1-181` | 호출 가드·관찰자 | R-69 |
| C-59 | `src/core/ai/budget-record.ts:14-38`, `src/core/budget/budget-tracker.ts:653-672` `usageFromError` | 기록 시 `BudgetExhausted` 삼키기, 실패 사용량 | R-63 |
| C-60 | `src/commands/config.ts:262-273`, `867-879`, `1148-1156` 파일 평면 키 목록과 라우팅 | API 키 파일 라우팅 | R-16 |
| C-61 | `src/commands/config.ts:1484-1515` `refuseSchemaSizingKey` | 임베딩 모델·차원 설정 거부 | R-17 |
| C-62 | `src/commands/config.ts:1168-1213` 미등록 키 거부, `src/commands/config/model-pin-shadow.ts:9-65` | 알 수 없는 키·모델 핀 가려짐 경고 | R-18 |
| C-63 | `src/core/ai/recipes/openai.ts:1-96`, `anthropic.ts:1-67`, `voyage.ts:1-96` | 대표 레시피 데이터 | R-09, R-22 |
| C-64 | `src/core/ai/defaults.ts:15-20` | 기본 임베딩 모델 `voyage:voyage-4`, 차원 1024, 기본 리랭커 `voyage:rerank-3-lite` | R-04 |
| C-65 | `src/cli/db-plane-config.ts:12-59` `mergeDbPlaneConfig` | 연결 뒤 병합→재구성 순서와 실패 시 동작 | R-12 |
| C-66 | `src/core/config-db-merge.ts:36-331` | 병합 대상 키 목록, "비어 있는 칸만 채움", `chat_fallback_chain` 파싱, `provider_chat_options` 병합 | R-12 |
| C-67 | `src/commands/providers.ts:182-312` `runTest` | `providers test` 흐름과 종료 코드 | R-14 |
| C-68 | `src/core/ai/key-warnings.ts:84-100` `authFailureStatus`, `reportEmbeddingAuthFailure` | 임베딩 401/403 첫 1회 stderr 알림 | R-25 |
| C-69 | `src/core/ai/errors.ts:510-528` `isUnbilledEmbeddingRejection` | 비과금 거절 판정 | R-25 |
| C-70 | `src/core/ai/errors.ts:158-220` `providerContentBlockReason` | 공급자 콘텐츠 정책 거절 판정(체인 전환 조건) | R-33 |
| C-71 | `src/core/ai/gateway.ts:84-85`, `src/core/ai/guarded-generation.ts:1-24` | 채팅·확장의 공급자 시도를 가드·관찰에 연결, 가드가 있으면 `maxRetries:0` | R-69 |
| C-72 | `src/core/ai/gateway.ts:99-121`, `152-157` | 시간 제한 환경변수, `withDefaultTimeout`, `authToHeaders` | R-24, R-30, R-52 |
| C-73 | `src/core/ai/gateway.ts:2773-2781` | `withBudgetTracker`, `getCurrentBudgetTracker` | R-60, R-61 |
| C-74 | `src/core/ai/key-redact.ts:1-18`, `src/core/minions/handlers/shell-redact.ts:41-56` | 오류 메시지에서 키 지우기: env의 `*_API_KEY\|_TOKEN\|_SECRET\|_PASSWORD` 값(8자 이상, 긴 것 먼저)을 `<REDACTED:이름>`으로, `***` 마스크 토큰은 `<REDACTED:masked_key>`, 키의 일부인 8자 이상 토큰은 `<REDACTED:key_fragment>`로 | R-25, R-32 |
| C-75 | `src/core/model-config.ts:356`, `566-637`, `src/core/ai/capabilities.ts:95-181` | `subagent` 티어 능력 판정(도구 없음·루프 불가·모름 → 교체, 캐시 없음 → 경고) | R-09 |
| C-76 | `src/core/ai/types.ts:11-538` | `Recipe`·터치포인트·`AIGatewayConfig`·`ParsedModelId` 정의(공통 계약의 원본) | R-06, R-07, R-21 |
| C-77 | `src/core/ai/recipes/index.ts:35-86` | 정적 등록부(25개), `getRecipe`, `listRecipes` | R-06 |

### 1.6 수락 사례

출처: T-01~T-08은 `agent-memory/artifacts/gbrain/ai-gateway-demos/demo-pure.mts`를 `deno run --no-remote --allow-read`로 실행해 관찰(2026-10-23, 원본 `src/` 파일을 import한 순수 함수 호출, 네트워크·키 없음; 출력 `demo-pure.out.2026-10-23.json`). 나머지는 구현에서 도출(미실행).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-06 | `parseModelId('openrouter:anthropic/claude-sonnet-4-6')`, `('anthropic/claude-sonnet-4-6')`, `('claude-sonnet-4-6')` | `{openrouter, anthropic/claude-sonnet-4-6}`, `{anthropic, claude-sonnet-4-6}`, 세 번째는 `AIConfigError`(접두 없음) |
| T-02 | R-06, R-07 | `resolveRecipe('anthropic:claude-haiku-4-5')`, `('nope:x')`, `assertTouchpoint(anthropic,'embedding')` | 모델 id가 `claude-haiku-4-5-20251001`, `AIConfigError`(Unknown provider), `AIConfigError`(터치포인트 없음) |
| T-03 | R-20 | `truncateEmbedInputs(['a'×9000, null, undefined])` | 길이 `[8000, 0, 0]` |
| T-04 | R-21 | Voyage `voyage-4`(0.5 안전계수, 문자 1=토큰 1, 예산 60000)에 8000자 11개 | 서브배치 크기 `[7, 4]` |
| T-05 | R-21 | OpenAI `text-embedding-3-small`(예산 100000×0.8, 4자/토큰)에 8000자 100개 | `[40, 40, 20]` |
| T-06 | R-21 | Ollama(`no_batch_cap`)에 1글자 40개 | `[16, 16, 8]` |
| T-07 | R-20 | `screenEmbeddings(['a',' ','c'], 보낸 인덱스 [0,2], 벡터 [[1,0],[0,0]])` | `EmbeddingZeroNormError`(이유 `empty_input`, `zero_norm`), 가져온 `vectors`는 정렬 유지 |
| T-08 | R-65 | `usageCostUsd`: `anthropic:claude-sonnet-4-6`(입력 1M) / `anthropic:claude-haiku-4-5`(1M) / `voyage:voyage-4` 임베딩(1M) / `ollama:bge-m3` 임베딩 / `litellm:x` 임베딩 / `litellm:gpt-4o` 채팅 / 같은 모델에 오버라이드 `{input:2.5,output:10}`(각 1M) | `3`, `1`, `0.06`, `0`, `null`, `null`, `12.5` (달러, 해당 SHA의 가격표 기준) |
| T-09 | R-05 | `embedding_model` 없는 설정으로 `configureGateway(buildGatewayConfig(cfg))` 후 `embed(['x'])` | 공급자 호출 없이 `AIConfigError`(명시적 임베딩 모델 없음) |
| T-10 | R-26 | `embedding_model='openai:text-embedding-3-small'`, `OPENAI_API_KEY` 없음, 추적기 없음 | `isAvailable('embedding')`=false, `diagnoseEmbedding()`={reason:'missing_env', missingEnvVars:['OPENAI_API_KEY']}, `embed`는 `AIConfigError("OpenAI embedding requires OPENAI_API_KEY.")` |
| T-11 | R-31 | `ANTHROPIC_API_KEY` 없음, `chat({messages})` | `AIConfigError("Anthropic chat requires ANTHROPIC_API_KEY.")`; 추적기가 있었다면 보류는 해제됨 |
| T-12 | R-40 | 키 없는 설치에서 `expand('q')` | `['q']`, 출력 없음 |
| T-13 | R-51 | `VOYAGE_API_KEY` 없음, `rerank({query:'q', documents:['a']})` | HTTP 없이 `RerankError(reason='no_key')`, 감사 행은 첫 호출에만 |
| T-14 | R-52 | 리랭크 서버가 `{"data":[{"index":1,"relevance_score":0.9}]}` 반환 | `[{index:1, relevanceScore:0.9}]` |
| T-15 | R-62, R-61 | 추적기 `maxCostUsd=0.01`(user), `chat` 입력 100만 토큰 추정 Sonnet | `reserve`가 `BudgetExhausted('cost')`, 공급자 호출 없음 |
| T-16 | R-62 | 같은 추적기, `litellm:gpt-4o`(unpriced) `chat` | `BudgetExhausted('no_pricing')`; 상한이 없는 추적기면 경고 1회 후 호출 진행 |
| T-17 | R-61 | 같은 `maxCostUsd=0.01` 추적기 범위 안에서 `expand('q')`(Haiku) 반복 | 막히지 않고 `record`만 쌓임(누적이 상한을 넘어도 `expand`는 던지지 않음) |
| T-18 | R-63 | 호출이 끝나 누적이 상한을 넘김 | 그 호출은 정상 결과를 반환하고, 다음 `reserve`가 `BudgetExhausted('cost')` |
| T-19 | R-33 | `chat_fallback_chain=['openai:gpt-5.2']`, 주 모델이 429 | 체인 모델 결과에 `fallbackFrom=주 모델`, `fallbackReason='failed (...)'`; 주 모델의 `BudgetExhausted`면 체인으로 가지 않음 |
| T-20 | R-17 | `gbrain config set embedding_model openai:text-embedding-3-large` | 종료 1, 아무것도 쓰지 않음, `migrate embeddings ... --dry-run` 안내 |
| T-21 | R-16 | `gbrain config set openai_api_key sk-...` | `~/.gbrain/config.json`에 저장, 출력은 `***` |
| T-22 | R-12 | 파일·환경변수에 `openai_api_key`가 없고 DB에 `openai_api_key`가 있음(엔진 연결 뒤 병합) | 게이트웨이 env에 `OPENAI_API_KEY`가 채워진다. 환경변수에 값이 있으면 DB 값은 무시된다. DB의 `embedding_model`은 어떤 경우에도 반영되지 않는다 |
| T-23 | R-14 | `providers test --touchpoint chat --model anthropic:claude-haiku-4-5`, 키 없음 | `isAvailable('chat')` false → 종료 1(실제 호출 없음). 키가 있고 공급자가 401이면 `AIConfigError`로 종료 2 |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (gbrain@63f62b2c) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-15 `config.ts:741-759` | 코드 읽기. |
| R-02 | C-13 `provider-env.ts:37-81` | 코드 읽기. 규칙 설명은 파일 헤더 주석(1-31행)과 일치. |
| R-03 | `gateway.ts:459-493`, `503-517` `refreshGatewayEnvFromFilePlane` | 코드 읽기. "호출 시점 `process.env`를 읽지 않는다"는 헤더 주석(17행)은 `process.env` grep으로 확인: 호출 경로에서는 `resolveAiTimeoutMs`(모듈 로드 시, 100행)만 읽는다. |
| R-04 | C-12, C-16, `defaults.ts:15-20`, `gateway.ts:4314-4318` | 코드 읽기. 문서와 구현 차이 2건: `dims.ts:51-56` 주석은 폴백 차원이 1536이라 하지만 `defaults.ts:16`과 `getEmbeddingDimensions`는 1024(구현 기준). `gateway.ts` 4-13행 헤더의 노출 함수 목록은 `chat`·`rerank` 이전 시점 것으로 낡았다. 리랭커는 "옵트인"이라 쓰여 있지만(`gateway.ts:135-138`) `rerank()`는 모델이 없으면 `DEFAULT_RERANKER_MODEL`을 쓴다. 옵트인은 호출자(`search.reranker.enabled`) 몫. |
| R-05 | `build-gateway-config.ts:83`, `gateway.ts:837-865`, `934-940` | 코드 읽기. T-09는 이 경로의 구현 도출(미실행). |
| R-06, T-01, T-02 | C-01, C-02, C-03 | 실행 확인: `demo-pure.out.2026-10-23.json`의 `parse colon/slash/bare`, `alias`, `unknown provider`, `anthropic embedding touchpoint`. |
| R-07 | C-03, `gateway.ts:4322-4333` | 코드 읽기 + 실행(`assertTouchpoint`). 헤더 주석(`model-resolver.ts:99-112`)이 "모델 목록은 허용 목록이 아니다"를 명시. |
| R-08 | C-10, C-07, C-08, C-11 | 코드 읽기. `resolveModelDetailed`는 `tier`가 주어지면 7단계에서 항상 반환하므로 호출자가 준 `fallback`은 gateway 경로에서 쓰이지 않는다(코드 추론이 아니라 521행 직전 분기 읽기). DB 키 읽기를 한 번에 하는 스냅샷(`config-snapshot.ts`)은 성능 장치라 제외. |
| R-09 | C-05, C-06, C-09, `capabilities.ts:169-181` | 코드 읽기. `gemini` 별칭 주석 등 이유 서술은 개발자 의도라 추론. |
| R-10 | C-52, `gateway.ts:557-572` `discoverBeforeOpenAICall` | 코드 읽기. 캐시 TTL·백오프 상수(`CACHE_TTL_MS`, `FETCH_TIMEOUT_MS`, `FAILURE_BACKOFF_MS`)는 `openai-latest.ts:89-90, 257`. 실제 `/models` 응답은 미확인. |
| R-11 | C-14, C-30 | 코드 읽기. |
| R-12 | C-65, C-66 | 코드 읽기(헤더 주석의 우선순위 서술과 `merged[field] !== undefined` 분기가 일치). `provider_base_urls`의 DB 병합은 `config.ts:947-956`의 `dbPrefixMap`로 읽었고 병합 분기 본문은 열지 않았다. 마운트 처리는 `main.ts:2745-2757` 주석·코드. |
| R-14 | C-67 | 코드 읽기. |
| R-15 | `providers.ts:126-180`, `314-340` | 코드 읽기(출력 서식은 제외). |
| R-16 | C-60 | 코드 읽기. 출력 가리기 규칙 `isSensitiveConfigKey`(`config.ts:32-36`)는 단어 경계의 `key\|secret\|token\|password\|pwd\|passwd\|auth`. |
| R-17 | C-61, `config.ts:1161-1166` | 코드 읽기. |
| R-18 | C-62, `config.ts:900-975` `get`, `1168-1213` | 코드 읽기. 키 검증의 세부 분기(`sync.*`, `facts.*`, `search.*` 등 값 검증)는 이 스펙 밖. |
| R-19 | `models.ts:764-929` | 코드 읽기. `models`(읽기) 표 구성(`buildReport`, 222-300행)은 열지 않았다(확인 한계). |
| R-20, T-03, T-07 | C-18, C-19 | 실행 확인: `truncate 8000`, `screen empty/zero`. |
| R-21, T-04~T-06 | C-18, C-21, C-22 | 실행 확인: `plan voyage`, `plan openai`, `plan ollama`(분할). 축소·회복은 코드 읽기만. |
| R-22 | C-04, C-17, C-22, C-23, C-24, C-25, C-26 | 코드 읽기, `embeddingDimsForModel` 실행(`dims openai`=1536, `dims voyage default`=1024). |
| R-23 | C-27, `gateway.ts:1841-1888`, `1096-1100` | 코드 읽기. 비-Voyage의 `input_type` 주입은 `openAICompatAsymmetricFetch`(1271-), NVIDIA는 `nvidiaCompatFetch`(1253-1269). |
| R-24 | C-20, C-22, `gateway.ts:99-121` | 코드 읽기. SDK 기본 재시도는 코드 주석(1570-1573행)만, 미확인. |
| R-25 | C-31, C-32, C-33, C-68, C-69, C-74 | 코드 읽기. |
| R-26, T-10 | C-17, C-29, C-34 | 코드 읽기. T-10은 구현 도출(미실행). |
| R-27 | C-28 | 코드 읽기. |
| R-30 | C-35, C-36, C-37, C-38, `chat-usage.ts:1-60`(sink 계약) | 코드 읽기. 사용량 sink의 형식(`ChatUsageRecord`)과 어디에 저장되는지는 이 스펙 밖(실패는 호출을 깨지 않음). |
| R-31, T-11 | C-17, C-36, C-37 | 코드 읽기. 호출자의 사전 점검 예: `isAvailable('chat')`(`extract-takes-from-pages.ts:205` 등), 사실 추출은 `isAvailable('chat', model)`(`facts/extract.ts:629`). |
| R-32 | C-31, C-32, C-37, C-74 | 코드 읽기. |
| R-33, T-19 | C-44, C-70 | 코드 읽기. |
| R-34 | C-35, C-37, C-39~C-43 | 코드 읽기. `thinking-off.ts` 표 전체는 선택 옵션이므로 C-43으로만 넘김. |
| R-40, R-41, T-12 | C-45, C-46, C-47, C-50 | 코드 읽기. 문서·구현 차이: 프롬프트·주석은 "3~4개/최대 4개"(`expansion-prompt.ts:8`, `gateway.ts:2484`)지만 스키마는 `.max(5)`(`gateway.ts:2426-2428`)이고 원 질의가 추가되므로 최대 6개(구현 기준). |
| R-50~R-52, T-13, T-14 | C-48, C-49 | 코드 읽기. 오류 이유 값 전체 목록(`RerankFailureReason`, `rerank-audit.ts:30-41`) 중 게이트웨이가 던지는 것은 R 본문의 8개뿐. |
| R-60~R-62, T-15~T-18 | C-20, C-36, C-45, C-48, C-51, C-59, `gateway.ts:2773-2781` | 코드 읽기. 구현 도출 사례이며 `BudgetTracker`는 `config.ts`→`version.ts`의 JSON import 때문에 이 환경(deno)에서 실행하지 못했다. |
| R-63, T-18 | C-51 `record`(479-560), C-59 | 코드 읽기. |
| R-64 | C-42, C-20, C-48 | 코드 읽기. |
| R-65, T-08 | C-53~C-55 | 실행 확인: `demo-pure.out.2026-10-23.json`의 `cost ...` 항목(가격표 값은 해당 SHA 기준). |
| R-66 | C-56, C-57, `config.ts:1677-1678` 키 등록 | 코드 읽기. |
| R-67 | C-51(`appendAuditLine` 245행~, 이벤트 이름) | 코드 읽기. |
| R-68 | `embed-cost-cap.ts:36-62`, `facts/backstop.ts:655-672`, `grep "new BudgetTracker("` 결과 24개 위치 | grep + 코드 읽기. 소비자별 상한 값은 열지 않음. |
| R-69 | C-58, C-71, `gateway.ts:1759-1790` | 코드 읽기. |
| T-20, T-21 | C-60, C-61 | 구현 도출(미실행). |

### 2.2 코드 읽는 순서

1. `gateway.ts` 1-140(상수·시간 제한), 459-640(구성·모델 재결정), 826-1092(getter·가용성), 1599-1833(`embed`), 2488-2671(`expand`), 3540-3864(`chat`), 4258-4507(`rerank`)을 이 순서로 읽는다. 다른 파일은 호출 순서대로 `model-resolver.ts` → `build-gateway-config.ts`/`provider-env.ts` → `embed-batch-plan.ts`/`embedding-guard.ts` → `budget-tracker.ts`/`reservation-cost.ts`.
2. 구현 전략: 모든 설정을 `configureGateway` 한 번의 스냅샷으로 얼리고(키 갱신은 재구성), 공급자 클라이언트는 `(레시피, 모델, base URL)`별 캐시, 임베딩은 입력 정리→분할→호출→검증, 예산은 `AsyncLocalStorage`에 걸린 추적기를 호출 전후로 참조한다.

### 2.3 비교·재사용 출처

없음(다른 레포에서 같은 기능을 스펙으로 만들지 않았다). 원본 코드를 복사하지 않았다.

## 적용 메모

없음.
