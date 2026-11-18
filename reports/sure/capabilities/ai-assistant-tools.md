---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-18
updated: 2026-11-18
sources:
  - app/models/assistant.rb
  - app/models/assistant/base.rb
  - app/models/assistant/builtin.rb
  - app/models/assistant/configurable.rb
  - app/models/assistant/external.rb
  - app/models/assistant/external/client.rb
  - app/models/assistant/external/model_catalog.rb
  - app/models/assistant/function.rb
  - app/models/assistant/function_tool_caller.rb
  - app/models/assistant/history_trimmer.rb
  - app/models/assistant/provided.rb
  - app/models/assistant/responder.rb
  - app/models/assistant/token_budget.rb
  - app/models/assistant/token_estimator.rb
  - app/models/assistant/function/*.rb
  - app/models/ai.rb
  - app/models/ai/availability.rb
  - app/models/ai/consent.rb
  - app/models/ai/config.rb
  - app/models/ai/config/endpoint.rb
  - app/models/ai/config/model.rb
  - app/models/ai/legacy_env_config.rb
  - app/models/ai/route.rb
  - app/models/ai/router.rb
  - app/models/ai/routes.rb
  - app/models/chat.rb
  - app/models/message.rb
  - app/models/assistant_message.rb
  - app/models/user_message.rb
  - app/models/tool_call.rb
  - app/models/tool_call/function.rb
  - app/models/chat_reservation.rb
  - app/jobs/assistant_response_job.rb
  - app/jobs/process_pdf_job.rb
  - app/controllers/chats_controller.rb
  - app/controllers/messages_controller.rb
  - app/controllers/concerns/requires_ai_consent.rb
  - app/controllers/concerns/ai_feature_guard.rb
  - app/controllers/api/v1/chats_controller.rb
  - app/controllers/api/v1/messages_controller.rb
  - app/controllers/api/v1/base_controller.rb
  - app/controllers/imports_controller.rb
  - app/controllers/mcp_controller.rb
  - app/models/provider.rb
  - app/models/provider/registry.rb
  - app/models/provider/llm_concept.rb
  - app/models/provider/openai.rb
  - app/models/provider/openai/chat_config.rb
  - app/models/provider/openai/chat_parser.rb
  - app/models/provider/openai/chat_stream_parser.rb
  - app/models/provider/openai/generic_chat_parser.rb
  - app/models/provider/openai/usage_cost.rb
  - app/models/provider/anthropic.rb
  - app/models/provider/anthropic/chat_config.rb
  - app/models/provider/anthropic/chat_parser.rb
  - app/models/provider/anthropic/message_formatter.rb
  - app/models/llm_usage.rb
  - app/models/usage.rb
  - app/models/family/ai_settings.rb
  - app/models/family/ai_promptable.rb
  - app/models/family/vector_searchable.rb
  - app/models/family_document.rb
  - app/models/vector_store.rb
  - app/models/vector_store/base.rb
  - app/models/vector_store/registry.rb
  - app/models/vector_store/embeddable.rb
  - app/models/vector_store/openai.rb
  - app/models/vector_store/pgvector.rb
  - app/models/vector_store/qdrant.rb
  - app/models/user.rb
  - app/models/account.rb
  - app/models/category.rb
  - app/models/import.rb
  - app/models/setting.rb
  - app/helpers/languages_helper.rb
  - app/helpers/application_helper.rb
  - app/views/api/v1/chats/show.json.jbuilder
  - app/views/assistant_messages/_assistant_message.html.erb
  - config/currencies.yml
  - config/routes.rb
  - db/schema.rb
  - .env.example
depends:
  - ./transactions.md
  - ./transfer-matching.md
  - ./budgets.md
  - ./recurring-transactions.md
  - ./account-balances.md
  - ./investments-securities.md
  - ./transaction-classification.md
  - ./goals.md
  - ./reports-insights.md
  - ./imports.md
  - ./provider-import-adapter.md
status: draft
---

# AI 어시스턴트 (채팅 대화 루프, 도구 49개, provider 선택, 외부 assistant, 문서 벡터 검색)

> 로그인한 사용자가 채팅으로 질문하면, 가족의 계정·거래·예산 등을 function tool로 읽고 일부는 쓰면서 답하는 대화 루프, 그 루프가 쓰는 LLM provider 선택·토큰 예산·시스템 프롬프트, 내장 assistant 대신 외부 에이전트 endpoint로 대화를 넘기는 계약, 업로드한 가족 문서를 벡터 검색으로 찾는 규칙을 정의한다.

이 문서에서 쓰는 이름은 다음과 같다. **턴**은 사용자 메시지 하나와 그 답 하나(`AssistantMessage` 하나)다. **라운드**는 "모델 요청 한 번 + 그 응답이 요구한 도구 실행 전부"이고, 한 응답이 도구 호출 여러 개를 요구해도 라운드는 하나다. **도구**는 모델에게 노출하는 function tool(`Assistant::Function` 하위 클래스, 이름은 `get_budget` 같은 snake_case)이다. **내장 assistant**는 `Assistant::Builtin`, **외부 assistant**는 `Assistant::External`이다. **가족 범위**는 도구가 `family.*`로 찾는 범위이고, **접근 계정**은 `user.accessible_accounts.visible`(소유 또는 공유받은 계정 중 숨김이 아닌 것), **쓰기 계정**은 `Account.writable_by(user)`(소유 또는 `full_control` 공유)다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

대표 흐름은 AI를 켠 `member` 사용자가 내장 assistant로 "이번 달 식비 예산 얼마 남았어?"를 묻는 경우다. 기준은 1.4다.

1. 사용자가 메시지를 보낸다(웹 `POST /chats`, `POST /chats/:chat_id/messages`, 또는 API v1). 서버는 사용자의 AI 사용 가능 판정(R-02)과 진입 가드(R-03)를 확인하고, `UserMessage`를 `complete`로 저장한다(R-04~R-06).
2. 저장이 commit되면 서버가 `pending` 상태의 빈 `AssistantMessage`를 만들고 `AssistantResponseJob`(큐 `ai_high_priority`)에 넣는다(R-06, R-09).
3. job이 가족의 assistant 종류(R-01)로 구현을 고른다. `external`이면 R-40~R-46으로 가고, 아니면 내장 assistant가 계속한다.
4. 내장 assistant는 메시지의 `ai_model`을 지원하는 LLM provider를 고르고(R-15), 시스템 프롬프트(정적 지시문 + 세션 컨텍스트, R-26·R-27)와 도구 목록(R-60)을 만들어 첫 모델 요청을 보낸다(R-36).
5. 응답이 도구 호출을 요구하면 서버가 순서대로 실행하고(R-62), 결과를 붙여 다시 요청한다. 라운드는 최대 8번이고 마지막 라운드의 후속 요청은 도구 호출을 금지한다(R-17·R-18). 위 질문이면 `get_budget`(R-75) 한 라운드 뒤 텍스트 답이 온다.
6. 텍스트는 provider가 스트리밍하면 조각마다, 아니면 한 번에 `AssistantMessage.content`에 덧붙고, 덧붙을 때마다 채팅 화면에 push된다(R-12·R-13·R-22).
7. 턴이 끝나면 요청마다 `llm_usages` 행이 남는다(R-25). 중간에 실패하면 메시지는 지워지거나 `failed`가 되고 `chats.error`가 채워져 화면에 오류와 Retry가 나온다(R-14·R-23).

### 1.2 범위·통합 지점

- 제공: 채팅·메시지 저장과 응답 job, 내장 assistant의 도구 호출 루프, 시스템 프롬프트 조립, history 자르기와 토큰 예산, provider 선택과 요청·응답 계약, 외부 assistant 호출 계약, AI 사용 가능 판정과 `Ai::Router` 규칙, 가족 문서 업로드·청킹·벡터 검색(pgvector, OpenAI vector store), 도구 49개의 입력·범위·반환·실패.
- 제외:
  - 도구가 부르는 도메인 로직. 거래·이체·예산·정기 거래·계정 잔액·보유종목·분류 규칙은 선행 스펙 링크로 대신하고 중복하지 않는다(1.4.2 표의 "도메인 링크").
  - MCP 서버(행 16). `/mcp`가 같은 도구 registry를 외부 클라이언트에 노출한다는 사실(R-60)과 오류 변환 차이(R-62)만 쓰고 JSON-RPC·OAuth는 쓰지 않는다.
  - 공개 API v1 일반(행 17). 이 기능의 `chats`·`messages` 엔드포인트만 쓴다(R-03, R-08).
  - 권한(Family 테넌시, `AccountShare`, 역할)은 승인 범위 밖이다. "접근 계정"·"쓰기 계정" 판정을 입력으로 받는다는 것까지만 쓰고 정의는 가정이다(U-01).
  - `Ai::Router`의 채팅 외 feature(`categorize`, `detect_merchants` 등, 행 10), `Ai::Transport`(health probe, 행 20), Langfuse·OpenTelemetry·`Ai::Instrumentation`, `Usage`(설치 단위 telemetry).
  - LLM provider SDK 구현 세부(`ruby-openai`, Anthropic gem의 직렬화·재시도). 호출 경계와 요청·응답 계약(R-36·R-37)만 쓴다(확인 한계).
  - 도구가 읽는 다른 기능의 본체는 선행 스펙으로 링크하고 입출력만 쓴다. Goal은 [goals](./goals.md), 명세서 보관함(`AccountStatement`)은 [imports](./imports.md), 출처 인용 문법(`Provenance::Citation`)은 [provider-import-adapter](./provider-import-adapter.md) R-71, 인사이트·`IncomeStatement`는 [reports-insights](./reports-insights.md), 규칙 엔진은 [transaction-classification](./transaction-classification.md)이다.
  - 화면(채팅 UI, 동의 화면, Stimulus watchdog), 큐 우선순위 보류(`ChatReservation`, `BackgroundJobHealth`). 응답 내용에 영향이 없고 R-10에 서버가 받는 신호만 썼다.
  - eval 러너(`Eval::Runners::ChatRunner` 등, 행 20)가 `chat_response`를 직접 부른다는 사실은 확인했으나 본문은 읽지 않았다.
- 외부 의존·선행 계약: LLM 서버(OpenAI Responses API 또는 Chat Completions 호환, Anthropic Messages), 임베딩 서버(`POST {base}/embeddings`), PostgreSQL(+pgvector 확장), job 큐와 Redis, 화면에 변경을 push하는 채널(원본은 Turbo stream broadcast). 현재 사용자·가족과 접근/쓰기 계정 판정은 호출자가 제공한다. 도메인 규칙은 [transactions](./transactions.md), [transfer-matching](./transfer-matching.md), [budgets](./budgets.md), [recurring-transactions](./recurring-transactions.md), [account-balances](./account-balances.md), [investments-securities](./investments-securities.md), [transaction-classification](./transaction-classification.md)이다.
- 소유 상태·부작용: `chats`, `messages`, `tool_calls`, `llm_usages`, `family_documents` 행과 `families.vector_store_id`, 벡터 저장소(OpenAI 쪽 store·file, 또는 `vector_store_chunks` 표)를 만들고 바꾼다. 쓰기 도구는 거래·태그·카테고리·예산·목표·잔액 앵커·규칙·이체·청구서·평가·명세서·가져오기 초안 등 선행 스펙 소유 상태를 바꾼다. 읽기 도구도 `get_budget`은 예산 행을 만들 수 있다(R-75).

### 1.3 인터페이스와 데이터 의미

**데이터**

| 데이터 | 타입 | 의미·제약 |
|---|---|---|
| `Chat` | 행 | `user_id`(필수, 채팅은 사용자 소유라 같은 가족의 다른 사용자는 못 본다), `title`(필수), `error`(jsonb, 아래 형식, 없으면 null), `latest_assistant_response_id`(string, OpenAI Responses 응답 id). `instructions` 컬럼은 있으나 이 범위 코드에서 읽지 않았다. |
| `Chat.error` | jsonb | `{message, technical_message, type}`를 JSON 문자열로 직렬화해(`update!(error: payload.to_json)`) jsonb 열에 넣고 읽을 때 `parsed_error_payload`가 다시 파싱한다. `message`는 분류된 사용자용 문구 키(R-14), `technical_message`는 원 오류 메시지, `type`은 오류 클래스 이름. 옛 형식(JSON 문자열 하나)도 읽는다. |
| `Message` | 행 | `type`(`UserMessage`·`AssistantMessage`), `chat_id`, `content`(text), `ai_model`(두 type 모두 필수), `status`(`pending`·`complete`·`failed`, DB 기본 `complete`). `content`는 `pending`이 아니면 비어 있을 수 없다. 정렬은 `created_at` 오름차순. |
| `ToolCall::Function` | 행 | `message_id`, `function_name`·`function_result`(필수, result는 jsonb), `function_arguments`(jsonb, 모델이 보낸 JSON 문자열 그대로 저장), `provider_id`·`provider_call_id`(모델 쪽 tool call 식별자), `extra_content`(jsonb, 모델이 준 부가 필드). `AssistantMessage`에 속한다. |
| `llm_usages` | 행 | 모델 요청 하나당 한 행: `family_id`, `provider`, `model`, `operation`(채팅은 `chat`), `prompt_tokens`·`completion_tokens`·`total_tokens`, `cache_read_tokens`·`cache_creation_tokens`(Anthropic), `estimated_cost`(USD, 모르면 null), `status`, `metadata`. |
| `FamilyDocument` | 행 | `family_id`, `filename`(필수), `content_type`, `file_size`, `provider_file_id`(벡터 저장소 쪽 파일 id), `status`(`pending`·`processing`·`ready`·`error`, 기본 `pending`), `metadata`. `has_one_attached :file`이 선언돼 있으나 `upload_document`는 파일을 첨부하지 않는다(`family_document.rb:4`). `Family`의 `has_many :family_documents, dependent: :destroy`는 벡터 저장소의 청크·파일을 정리하지 않는다(`family/vector_searchable.rb:4-6`). `Family#search_documents`(`family/vector_searchable.rb:25-38`)는 호출처가 없다(검색 도구는 어댑터를 직접 부른다, R-81). |
| 가족 설정 | 필드 | `assistant_type`(`builtin`·`external`·`mcp_only`), `vector_store_id`, `ai_prompt_overrides`(jsonb, 키 `chat_system` 등, 값은 문자열 최대 20,000자, NUL 문자 금지, 빈 값은 저장 때 삭제). |
| 사용자 설정 | 필드 | `ai_enabled`(기본 false, 사용자 동의 스위치), `ui_layout`(`dashboard`·`intro`, guest는 `intro`), `preferences.preview_features_enabled`, `role`. |

**연산(웹과 API)**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| 채팅 시작 | `POST /chats`, `chat[content]`, `chat[ai_model]` → 채팅 화면으로 redirect | R-03, R-04 |
| 메시지 보내기 | `POST /chats/:chat_id/messages`, `message[content]`, `message[ai_model]` → redirect | R-03, R-06 |
| 재시도 | `POST /chats/:id/retry` | R-07 |
| 제목 수정·삭제 | `PATCH /chats/:id`, `DELETE /chats/:id` | 제목은 채팅 시작 때 정해지고(R-04) 자동 생성하지 않는다. |
| 응답 미도착 신고 | `POST /chats/:chat_id/messages/:id/report_timeout`(브라우저 watchdog이 부른다) | R-10. 200·409·404. |
| API v1 채팅 | `GET /api/v1/chats`(20개/쪽), `GET /api/v1/chats/:id`(메시지 50개/쪽, `tool_calls` 포함), `POST /api/v1/chats`(`title`, `message`, `model`), `PATCH`(`title`만), `DELETE`(204) | R-03. 응답의 `error`는 `presentable_error_message`. |
| API v1 메시지 | `POST /api/v1/chats/:chat_id/messages`(`content`, `model`), `POST .../messages/retry` | R-06, R-08 |
| 도구 호출 | 모델이 `{name, arguments(JSON 문자열)}`로 요청 → 도구 반환값(JSON 객체) | R-60~R-69, 1.4.2 |
| 외부 assistant 호출 | `POST <EXTERNAL_ASSISTANT_URL>`(OpenAI Chat Completions 호환, SSE) | R-41~R-43 |
| 외부 agent 목록 | `GET <url의 /chat/completions를 /models로 바꾼 주소>` → `{data:[{id}]}` | R-46 |

**설정 키(외부 계약, 원문 이름 그대로)**

| 키 | 의미·기본값 |
|---|---|
| `ASSISTANT_TYPE` | 가족의 `assistant_type`보다 우선(R-01). |
| `ASSISTANT_MAX_TOOL_CALL_ITERATIONS` | 라운드 상한. 양의 정수가 아니면 8(R-17). |
| `LLM_PROVIDER` / `Setting.llm_provider` | `anthropic`이면 provider 탐색 순서가 anthropic, openai(R-15). 기본 `openai`. |
| `LLM_CONTEXT_WINDOW`, `LLM_MAX_RESPONSE_TOKENS`, `LLM_MAX_HISTORY_TOKENS`, `LLM_SYSTEM_PROMPT_RESERVE` | 토큰 예산(R-29~R-32). 기본 2048 / 512 / 계산 / 256. |
| `AI_RESPONSE_TIMEOUT` | watchdog 대기(초). 기본 90, 최소 30(R-10). |
| `OPENAI_ACCESS_TOKEN`, `OPENAI_URI_BASE`, `OPENAI_MODEL`, `OPENAI_REQUEST_TIMEOUT`(기본 60, 최소 1), `OPENAI_EXTRA_HEADERS`(JSON 객체, 값의 `{session_id}`는 채팅 id로 치환), `OPENAI_SUPPORTS_RESPONSES_ENDPOINT` | R-35, R-22. `OPENAI_EXTRA_HEADERS`·`OPENAI_SUPPORTS_RESPONSES_ENDPOINT`는 ENV 전용(Setting 없음), 나머지는 ENV가 `Setting` 필드보다 우선. |
| `ANTHROPIC_ACCESS_TOKEN`(또는 `ANTHROPIC_API_KEY`), `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, `ANTHROPIC_REQUEST_TIMEOUT`(기본 600초, 채팅 Anthropic client timeout, `anthropic.rb:67`), `ANTHROPIC_MAX_TOKENS`(기본 4096) | R-35, R-32 |
| `EXTERNAL_ASSISTANT_URL`, `_TOKEN`, `_MODEL`, `_AGENT_ID`, `_SESSION_KEY`(기본 `agent:main:main`), `_ALLOWED_EMAILS` | R-40 |
| `VECTOR_STORE_PROVIDER`(`openai`·`pgvector`·`qdrant`), `EMBEDDING_URI_BASE`, `EMBEDDING_ACCESS_TOKEN`, `EMBEDDING_MODEL`(기본 `mxbai-embed-large`), `EMBEDDING_DIMENSIONS`(기본 1024), `QDRANT_URL`, `QDRANT_API_KEY` | R-50, R-55 |

### 1.4 행동 규칙과 남은 질문

#### 1.4.1 채팅·대화 루프·provider·외부 assistant·벡터 검색

정의된 R-ID는 113개다. 번호는 R-118까지 있고 R-39, R-49, R-57~R-59는 쓰지 않는 번호다(재사용하지 않는다).

**진입과 가용성**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 가족의 assistant 종류를 구한다(`effective_assistant_type`) | `ENV["ASSISTANT_TYPE"]`(비어 있지 않으면) > 가족 `assistant_type` > `"builtin"`. 값은 `builtin`·`external`·`mcp_only`이고 가족 저장 때 이 셋만 허용한다. 구현 선택은 `external`이면 외부 assistant, 그 밖의 모든 값(알 수 없는 ENV 값, `mcp_only` 포함)은 내장 assistant 클래스로 간다. `mcp_only`는 `assistant_enabled? = false`이고, 먼저 `User#ai_available?`가 false를 돌려줘 `ai_enabled?`가 false가 되므로 R-03의 웹·API 가드가 요청을 막는다. 화면도 막는다(`insights_helper.rb:128`의 "Dig in with AI" 판정, `layouts/application.html.erb:3-4`의 채팅 표면 제거). `Chat#ask_assistant`의 pending 삭제 분기(R-09)는 `mcp_only`로 바뀌기 전에 이미 큐에 들어간 job에서만 관찰된다. `mcp_only`여도 `/mcp`는 같은 도구를 계속 서비스한다. | 코드 확인 |
| R-02 | 사용자의 AI 사용 가능 판정(`User#ai_enabled?`) | `ai_enabled`(사용자 동의 스위치, 기본 false)이고 `ai_available?`일 때만 true다. `ai_available?`는 assistant 종류가 `mcp_only`면 false, 앱 모드가 self-hosted가 아니면 true, self-hosted이면 `external`은 `Assistant::External.available_for?(user)`, 그 밖에는 OpenAI 또는 Anthropic이 설정(`configured?`)돼 있어야 true다. guest는 저장 때 `ai_enabled = true`·`ui_layout = intro`로 강제된다(R-16). | 코드 확인 |
| R-03 | 채팅·메시지 요청이 들어온다 | 웹: `chats#create`, `chats#retry`, `messages#create`는 `ai_enabled?`가 false면 아무것도 만들지 않고 각각 `chats_path`·`chat_path`로 redirect한다. `chats#index/new/show`는 가드가 없다(화면이 동의 안내를 inline으로 보여 준다). `report_timeout`은 false면 403이다. 모든 채팅 조회는 `Current.user.chats` 범위라 남의 채팅 id는 not found다. API v1: `chats`·`messages` 모든 액션이 `ai_enabled?` false면 403 `{error:"feature_disabled", message}`, 읽기(`index`·`show`)는 `read`, 쓰기(`create`·`update`·`destroy`, 메시지 `create`·`retry`)는 `write` scope를 요구한다. 채팅이 없으면 404 `{error:"Chat not found"}`다. API 키 인증 요청은 키별 요청 수 제한(`check_api_key_rate_limit`)을 넘으면 429이다(`api/v1/base_controller.rb:31`, `:130-143`, 요청 수 제한일 뿐 토큰·비용 상한이 아니다, R-34). | 코드 확인 |
| R-04 | 채팅을 시작한다(`Chat.start!(prompt, model:)`) | `title = prompt.first(80)`(문자 80개). 모델은 입력이 있으면 그것, 없으면 R-05의 기본 모델. `UserMessage`(content=prompt, `ai_model`=모델)를 채팅과 함께 만든다. API v1 `POST /chats`는 `title`이 필수(없으면 저장 실패, 422 `{error:"Failed to create chat"}`)이고 `message`가 있으면 그 내용으로 `UserMessage`를 만들며 실패하면 채팅을 지우고 422 `{error:"Failed to create initial message"}`를 낸다. | 코드 확인 |
| R-05 | 기본 모델을 정한다(`Chat.default_model`) | `Setting.llm_provider == "anthropic"`이고 Anthropic이 설정돼 있으면 `Provider::Anthropic.effective_model`(ENV > Setting > `claude-sonnet-4-6`). 아니면 OpenAI가 설정돼 있으면 `Provider::Openai.effective_model`(ENV > Setting > `gpt-4.1`). 아니면 Anthropic이 설정돼 있으면 그 모델. 어느 것도 없으면 OpenAI의 `effective_model`(`gpt-4.1`)이다. 항상 비어 있지 않은 문자열을 돌려준다. | 코드 확인 |
| R-06 | `UserMessage`가 저장돼 commit된다 | 내용이 비어 있으면 저장 검증이 실패하고 응답 job은 만들지 않는다(웹 `messages#create`는 오류 문장으로 redirect, API는 422 `{error:"Failed to create message"}`). 저장되면 `Chat#ask_assistant_later`가 (1) `chats.error`를 지우고, (2) `content = ""`·`status = pending`·`ai_model`=사용자 메시지의 모델인 `AssistantMessage`를 만들고, (3) `AssistantResponseJob.perform_later(사용자 메시지, pending 메시지)`를 넣는다. `ai_model`을 생략하면 R-05 기본 모델이다. | 코드 확인 |
| R-07 | `chats#retry` | `chats.error`를 지운 뒤, 사용자·assistant 메시지 중 마지막 것이 `UserMessage`일 때만 R-06의 `ask_assistant_later`를 그 메시지로 다시 호출한다. 마지막이 assistant 메시지이면 아무 응답도 요청하지 않고 채팅 화면으로 redirect한다. 이전 `failed` 메시지는 지우지 않는다. | 코드 확인 |
| R-08 | API v1 `POST /chats/:chat_id/messages/retry` | 마지막 메시지가 `AssistantMessage`이면 `content: ""`인 새 `AssistantMessage`를 `create!`하고 `AssistantResponseJob.perform_later(새 메시지)`를 넣은 뒤 202 `{message:"Retry initiated", message_id}`를 낸다. 아니면 422 `{error:"No assistant message to retry"}`다. 코드상 두 군데가 정상 경로를 막는 것으로 보인다. (a) 새 메시지는 DB 기본 `status = complete`이고 `content`가 비어 있어 R-11 검증(`pending`이 아니면 content 필수)에 걸려 `create!`가 `RecordInvalid`를 낼 것이다. (b) 통과해도 job이 넘긴 메시지에서 `request_response`를 부르는데(R-09) 이 메서드는 `UserMessage`에만 있다. 실행해 보지 않았다(U-02). 원본 컨트롤러 테스트도 이 사례를 `skip "Retry functionality needs debugging"`로 건너뛴다(`test/controllers/api/v1/messages_controller_test.rb:61-62`). `Api::V1::BaseController`에는 `RecordInvalid`용 `rescue_from`이 없어(`:42-45`) (a)에서 예외가 그대로 올라가 500이 될 가능성이 크다(추론). | 코드 확인(구조) / 추론(결과) |
| R-09 | `AssistantResponseJob#perform(message, pending)` | `message.request_response(assistant_message: pending)`를 부른다. `UserMessage#request_response`는 `Chat#ask_assistant`로 가고, 가족의 `assistant_enabled?`가 false(`mcp_only`, R-03 가드가 막으므로 이미 큐에 있던 job에서만 도달한다)이면 pending 메시지를 지우고 아무것도 호출하지 않고 끝낸다. 아니면 `chat.assistant.respond_to(message, assistant_message: pending)`를 부른다(내장·외부는 R-01로 고른다). job 종료 때 `hold_reservation`(큐 우선순위 보류, 범위 밖)을 항상 부른다. 이 job에는 재시도 정의가 없다. | 코드 확인 |
| R-10 | 브라우저 watchdog이 "응답이 안 왔다"고 신고한다(`report_timeout`) | 대기 한도는 `max(30초, ENV AI_RESPONSE_TIMEOUT > Setting.ai_response_timeout > 90초)`다. 서버는 자기 기준으로 `한도 − 10초`보다 오래된 `pending`일 때만 처리한다. 메시지 행을 잠근 상태에서 다시 읽어 아직 `pending`이고 그만큼 오래됐으면, `content`가 비었으면 삭제, 있으면 `status = failed`로 바꾸고, `chats.error`에 `{message:"no_response" 문구, technical_message, type:"DeliveryTimeout"}`를 쓰고 오류를 화면에 push한 뒤 200을 준다. 아직 덜 오래됐거나 이미 `pending`이 아니면 409(watchdog이 재신고하도록 2xx를 주지 않는다), 메시지가 없으면 404다. | 코드 확인 |

**메시지 상태와 오류 저장**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-11 | 메시지 저장 검증과 history 대상 | `content` 필수(`pending` 예외), `ai_model` 필수(User·Assistant). 모델에 보내는 history는 `UserMessage`·`AssistantMessage` 중 `status = complete`인 것만이고 `created_at` 오름차순이다. `pending`·`failed` 메시지는 보내지 않는다. 연속 `failed` 뒤에 사용자 메시지가 이어지면 user 메시지가 연속으로 간다(합치지 않는다). | 코드 확인 |
| R-12 | `AssistantMessage#append_text!(text)` | 이미 삭제됐거나 frozen이면 false를 돌려주고 쓰지 않는다. `pending`이면 먼저 `UPDATE ... WHERE status = pending`으로 `complete`로 바꿔 보고, 바뀐 행이 없으면(watchdog이 먼저 지우거나 `failed`로 바꿨음) false를 돌려주고 쓰지 않는다. 성공하면 `content += text`를 저장한다. 그래서 watchdog이 이미 오류를 알린 메시지에 늦은 텍스트가 되살아나지 않는다. | 코드 확인 |
| R-13 | 메시지 생성·수정·삭제가 commit된다 | 채팅 단위 stream으로 화면에 push한다(생성은 목록에 append, 수정은 그 메시지 갱신, 삭제는 제거). 그래서 스트리밍 응답은 `append_text!`가 저장될 때마다 갱신된다. push 채널 구현은 원본의 Turbo stream이고 재구현 때 다른 채널로 바꿀 수 있다. | 코드 확인 |
| R-14 | `Chat#add_error(e)`(내장·외부 공통 실패 경로) | `chats.error`에 `{message, technical_message, type}`을 쓰고 오류 영역을 화면에 push한다. `technical_message`는 오류 메시지 원문이다. `message`는 원문을 위에서부터 검사해 분류한다. (1) `429`, `rate limit`, `too many requests`, `quota exceeded` → 속도 제한 문구, (2) `5xx` 세 자리, `service unavailable`, `temporarily unavailable`, `gateway timeout`, `bad gateway`, `overloaded`, `/time(?:out|d?\s*out)/i`(timeout·timed out), `connection reset` → 일시 장애 문구, (3) `unauthorized`, `authentication`, `invalid api key`, `incorrect api key`, `access token` → 설정 오류 문구, (4) 그 밖·빈 문자열 → 기본 오류 문구. 정규식은 대소문자를 구분하지 않고 (1)이 (2)보다 먼저다. 다음 질문·재시도(R-06, R-07) 때 `chats.error`가 지워진다. | 코드 확인 |

**내장 assistant의 대화 루프**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-15 | 내장 assistant가 provider를 고른다(`get_model_provider(message.ai_model)`) | 탐색 순서는 `Setting.llm_provider == "anthropic"`이면 anthropic, openai, 아니면 openai, anthropic이다(`LLM_PROVIDER` ENV가 비어 있지 않으면 그 값). 순서대로 provider가 설정돼 있고(`get_provider`가 nil이 아님) `supports_model?(message.ai_model)`가 true인 첫 것을 쓴다. OpenAI는 커스텀 endpoint(`OPENAI_URI_BASE`가 비어 있지 않고 공식이 아님. 공식은 https·포트 443·host가 `api.openai.com` 또는 `<하위도메인>.api.openai.com`·경로가 빈 값 또는 `/v1`)이면 어떤 모델명이든 지원하고, 공식 endpoint면 모델명이 `gpt-4`·`gpt-5`·`gpt-6`·`o1`·`o3`로 시작해야 한다. Anthropic은 커스텀 `base_url`이면 어떤 모델명이든, 아니면 `claude`로 시작해야 한다. 찾지 못하면 `No LLM provider configured that supports model '<모델>'`로 시작하는 오류를 낸다(설정된 provider가 있으면 "Available providers"와 각 provider의 지원 모델 설명을 붙인다). 이 오류는 R-23 경로로 간다. 그래서 OpenAI 커스텀 endpoint와 Anthropic이 모두 설정된 설치에서 `claude-...` 모델 메시지는 `llm_provider`가 `anthropic`이 아닌 한 OpenAI로 간다. | 코드 확인 |
| R-16 | 내장 assistant의 구성(`config_for(chat)`) | 사용자의 `ui_layout`이 `intro`이면(guest. 저장 때 guest는 `intro`, 그 밖은 `dashboard`로 강제되는 `before_validation`) 지시문은 소개 대화용 프롬프트이고 도구는 없다. 아니면 지시문은 R-26이고 도구는 R-60의 목록이다. 지시문·도구는 턴마다(`Assistant.for_chat`이 불릴 때) 새로 만든다. | 코드 확인 |
| R-17 | 응답이 도구 호출을 요구한다 | 첫 요청 뒤 `function_requests`가 있는 동안 반복한다. 반복마다 `iteration += 1`을 하고, `iteration`이 상한보다 크면 `ToolCallLimitError`("Assistant exceeded the tool-call limit of N for one response")를 낸다. 상한은 `ASSISTANT_MAX_TOOL_CALL_ITERATIONS`(10진 정수로 읽고 양수일 때)이고 아니면(미설정·0·음수·숫자가 아님) 8이다. 한 응답의 호출 여러 개는 라운드 하나이고 응답에 나온 순서대로 하나씩 실행한다(병렬 실행 없음). 라운드마다 결과에 `round: iteration`을 붙이고, 실행이 끝나면 `:response` 이벤트(`id`, `function_tool_calls`)를 낸다. | 코드 확인 |
| R-18 | 마지막 허용 라운드(`iteration == 상한`)의 후속 요청 | 그 라운드의 도구는 실행하고, 후속 요청에 `tool_choice: none`을 실어 모델이 텍스트로 답하게 한다. 도구 정의 목록은 요청에 그대로 둔다(Anthropic이 도구 블록이 있는데 도구 정의가 없는 메시지를 거절하기 때문). OpenAI는 도구가 있을 때만 `tool_choice: "none"`을 싣고 Anthropic은 `{type: "none"}`이다. 모델이 그래도 도구 호출을 요구하면 다음 반복에서 R-17의 `ToolCallLimitError`가 난다. | 코드 확인 |
| R-19 | 후속 요청에 도구 결과를 싣는다 | provider가 응답 맥락을 보존하는 방식(OpenAI Responses 경로, `supports_responses_endpoint?` true)이면 이번 라운드의 결과만 싣고 `previous_response_id`로 이어 붙인다. 그 밖(OpenAI 커스텀 endpoint, Anthropic)은 이번 턴에 지금까지 쌓인 모든 라운드의 결과를 라운드 순서대로 다시 싣는다. 라운드마다 "assistant의 도구 호출 메시지 하나 + 그 결과들"로 재구성해 이전 요청을 확장하는 모양을 유지한다. | 코드 확인 |
| R-20 | `Assistant::Builtin#respond_to`의 이벤트 처리 | 텍스트 조각(`output_text`): `assistant_message.content`가 비어 있을 때(첫 조각)는 한 DB transaction 안에서 덧붙이기와 `chat.update_latest_response!(그 시점에 들고 있는 response id)`를 같이 하고, 이후 조각은 덧붙이기만 한다. `:response`에 도구 호출이 있으면 `assistant_message.tool_calls`에 그 `ToolCall::Function`들을 저장하고 들고 있는 response id를 그 응답의 id로 바꾼다. 도구 호출이 없는 마지막 `:response`면 `chats.latest_assistant_response_id`에 그 응답 id를 저장한다. 한 턴의 모든 라운드 텍스트가 같은 `AssistantMessage.content`에 이어 붙는다. 시작 시 들고 있는 response id는 채팅의 이전 `latest_assistant_response_id`이고 첫 요청의 `previous_response_id`로 쓴다. | 코드 확인 |
| R-21 | 스트림 텍스트의 공백과 빈 응답 | 공백뿐인 조각은 메시지에 저장할 수 없으므로(R-11) 첫 비공백 조각이 올 때까지 모아 두었다가 그 조각과 합쳐 한 번에 내보낸다. 한 턴의 모든 요청 응답에서 텍스트가 한 번도 없었으면 도구를 호출했는지와 관계없이 `EmptyResponseError`("Assistant returned neither text nor tool calls")를 낸다. `any_response_has_text`는 텍스트만 보므로, 도구만 호출한 라운드 뒤 마지막 응답이 비어도 앞 라운드에 텍스트가 한 번도 없었다면 오류이고 R-23 경로로 메시지가 삭제되거나 `failed`가 된다. 앞 라운드에 텍스트가 있었으면 마지막 응답이 비어도 오류가 아니다. 도구 호출이 있던 이 경우를 다루는 원본 테스트는 없다(`test/models/assistant_test.rb:305-322`는 다른 사례). | 코드 확인 |
| R-22 | 스트리밍 여부 | OpenAI Responses 경로(공식 endpoint, 또는 `OPENAI_SUPPORTS_RESPONSES_ENDPOINT`가 참): 스트림 이벤트에서 텍스트 조각(`response.output_text.delta`, `response.refusal.delta`)을 그대로 내보내고 `response.completed`를 응답으로 삼는다. `response.completed`가 없이 끝나면(`response.failed`·`response.incomplete`·`error` 이벤트 포함) 오류를 낸다. OpenAI 커스텀 endpoint: 스트리밍하지 않는다. 한 번 응답을 받은 뒤 텍스트를 한 조각으로 내보낸다(화면은 전체 생성이 끝나야 보인다). Anthropic: 항상 스트리밍하고 텍스트 이벤트마다 내보낸다. `OPENAI_SUPPORTS_RESPONSES_ENDPOINT`는 문자열이 비어 있지 않으면 불리언으로 변환한 값이 우선하고, 없으면 `커스텀 endpoint가 아님`이다. | 코드 확인 |
| R-23 | 내장 assistant 턴이 어디서든 실패한다(provider 없음, 요청 오류, 상한 초과, 빈 응답 등 모든 `StandardError`) | pending 메시지가 저장돼 있으면, `content`가 비어 있으면 삭제하고(그 메시지의 `tool_calls`도 함께 삭제), 비어 있지 않으면 `status`를 `failed`로 바꾼다(history에서 빠진다, R-11). 이어서 `chat.add_error(e)`(R-14)를 부른다. 자동 재시도는 없고 사용자가 Retry(R-07)한다. 도구 부작용(쓰기)은 되돌리지 않는다. | 코드 확인 |
| R-24 | 도구 호출·결과를 영속하고 history로 재생한다 | `ToolCall::Function`에 모델의 호출 식별자·이름·인자·결과를 저장한다(R-17의 `:response`에서). 다음 턴의 history 재생(R-30)에서 assistant 메시지에 tool call과 결과가 다시 실린다. 같은 채팅의 이전 턴 도구 결과는 새 요청에서도 모델에게 보인다(자르기 규칙 R-31 안에서). | 코드 확인 |
| R-25 | LLM 사용량 기록 | OpenAI·Anthropic provider가 요청 하나마다 `llm_usages` 행을 `operation = "chat"`으로 만든다. 성공 행은 응답에 usage가 있을 때만 만들어지고(없으면 행 없음, `openai.rb:880`, `anthropic.rb:480`), OpenAI 경로의 `provider` 열은 모델명으로 `LlmUsage.infer_provider`가 추정한다(가격표에 없는 모델·커스텀 모델은 `"openai"`, 규칙은 `llm_usage.rb:115-139`). Anthropic provider는 항상 `"anthropic"`이다. 토큰 수(OpenAI는 `prompt_tokens`/`input_tokens`, `completion_tokens`/`output_tokens`, `total_tokens`, Anthropic은 `input_tokens`+`output_tokens` 합과 캐시 토큰), `estimated_cost`(`config/llm_pricing.yml` 가격표로 `LlmUsage.calculate_cost`가 계산, 가격이 없는 모델·커스텀 모델은 null, OpenRouter 공식 endpoint는 응답의 `usage.cost`를 그대로). 실패 행: 토큰 0, `estimated_cost` null, `metadata`에 오류 메시지와 HTTP 상태 추출값. Anthropic 스트림이 도중에 끊기면 그때까지 쌓인 토큰을 부분 행으로 기록한다. 가족 없이(`family: nil`) 부르면 기록하지 않는다. 기록 실패는 삼키고 로그만 남긴다. 외부 assistant는 이 행을 만들지 않는다(R-45). 토큰 사용량의 상한(월 한도, 차단)은 검사하지 않는다(R-34). | 코드 확인 |

**시스템 프롬프트와 컨텍스트**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-26 | 기본 지시문을 만든다(`default_instructions`) | 결과는 `"<정적 지시문>\n<세션 컨텍스트>"`다. 정적 지시문은 가족의 `ai_prompt(:chat_system)`(비어 있지 않은 문자열)이 있으면 그것, 없으면 상수 `STATIC_INSTRUCTIONS`다. 정적 부분은 날짜·통화·가족별 값을 넣지 않아 요청 간 바이트가 같다(provider 프롬프트 캐시를 위해서이고 가족 override를 쓰면 그 이점을 포기한다). 상수 본문이 담는 필수 구성은 (1) 정체성("Sure"라는 오픈소스 개인 금융 앱의 친절한 어시스턴트), (2) 목적(계정·거래·소득·지출·순자산·예산·예측 질문에 답함), (3) 요청 분류 CHAT(도구 호출 금지)·LOOKUP(가장 구체적인 도구 하나)·ANALYSIS(먼저 필요한 도구를 정하고 독립 호출은 같은 라운드에), (4) 도구 규칙: 대화나 세션 컨텍스트에 이미 있는 데이터는 다시 조회하지 않되 쓰기 뒤나 다른 기간·더 상세한 요청이면 다시 조회, 총계·추이는 `get_income_statement`·`get_balance_sheet`를 우선, 결과에 `error`와 `hint`가 있으면 hint를 따라 한 번만 고쳐 재시도하고 같은 호출을 반복하지 않음, 도구·함수 이름을 답에 노출하지 않음, 데이터가 부족하면 어떤 범위의 데이터인지 밝힘, (5) 응답 규칙: 핵심 숫자만, 소개·결론·사과 금지, 후속 질문 유도, markdown, 금액은 선호 통화·날짜는 선호 형식, (6) 금융 조언 제한(특정 상품 매수·매도 권유 금지, 사용자 상황을 가정하지 않고 도구로 조회). 응답 언어를 지정하는 문장은 없다. 모델이 사용자 질문의 언어를 따르는지는 이 코드가 보장하지 않는다(U-03, T-19). | 코드 확인 |
| R-27 | 세션 컨텍스트를 만든다(`session_context`) | 항상 (1) `Today's date`: 서버 시간대의 `Date.current`(가족 시간대가 아니다), (2) `Date format`: 가족의 `date_format` 문자열, (3) `Preferred currency`: `<ISO 코드> (symbol, precision, format, separator, delimiter)`. 사용자가 있으면 (4) Accounts: 접근 계정이 0개면 생략, 25개를 넘거나 `small_context?`(R-29)이면 `"<N> accounts: <accountable 종류별 개수>. Call get_accounts for the list."`, 아니면 계정마다 `- 이름: 종류, 자산/부채 분류, 포맷된 잔액` 한 줄, (5) Categories: 가족 카테고리가 0개면 생략, 60개를 넘거나 `small_context?`이면 `"<N> categories. Call get_categories for the list."`, 아니면 이름들을 쉼표로 잇고 끝에 `Uncategorized`를 붙인다. | 코드 확인 |
| R-28 | intro 지시문 | `intro` 레이아웃(R-16)의 지시문: 새 가족을 맞는 따뜻한 안내자로서 한 번에 질문 하나씩 생애 단계·재무 책임·단기 우선순위를 파악하고, 상세 분석 요청은 대시보드가 곧 다룬다고 안내하며, markdown, 통화는 `<기호> (<ISO>)`·날짜는 가족 형식, 도구 호출 금지. | 코드 확인 |

**history와 토큰 예산**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-29 | 컨텍스트 창 크기와 작은 창 판정(`TokenBudget`) | `LLM_CONTEXT_WINDOW`(양의 정수) > `Setting.llm_context_window`(양수) > 2048. `small_context?`는 창이 4096 미만일 때 true이고 R-27이 계정·카테고리를 개수로 접는다. | 코드 확인 |
| R-30 | history 메시지 배열을 만든다(OpenAI 호환 Chat Completions 경로) | R-11의 complete 메시지를 순서대로 `{role, content}`로 만든다. 현재 사용자 메시지도 그 안에 들어 있다. tool call이 있는 assistant 메시지는 `{role:"assistant", content(없으면 ""), tool_calls:[{id, type:"function", function:{name, arguments(JSON 문자열, 비었으면 "{}")}, extra_content?}]}` 하나와 이어지는 `{role:"tool", tool_call_id, content}`들(결과가 문자열이면 그대로, nil이면 "", 그 밖은 JSON 문자열)로 만든다. tool call이 없고 `content`가 비어 있는 메시지는 건너뛴다. Anthropic은 현재 메시지를 뺀 이전 메시지 레코드를 쓰고(R-36), OpenAI Responses 경로는 history를 보내지 않는다(서버가 `previous_response_id`로 가진다). | 코드 확인 |
| R-31 | history 자르기(OpenAI 호환 Chat Completions 경로에서만) | 예산 `max_history_tokens`는 `LLM_MAX_HISTORY_TOKENS`(양수)면 그 값, 아니면 `max(컨텍스트 창 − 응답 예산 − 지시문 추정 토큰, 256)`이다. 응답 예산은 `LLM_MAX_RESPONSE_TOKENS`(양수) > `Setting.llm_max_response_tokens`(양수) > 512, 지시문 추정은 `TokenEstimator.estimate(instructions)`(지시문이 비었으면 `LLM_SYSTEM_PROMPT_RESERVE` 기본 256). 자르기: "assistant tool call 메시지 + 뒤따르는 `role: tool` 메시지들"을 한 묶음으로 보고, 묶음 단위로 가장 최신부터 거꾸로 세어 누적 추정 토큰이 예산을 넘는 첫 묶음에서 멈춘다(그 묶음과 더 오래된 묶음은 버린다). 가장 최신 묶음은 예산을 넘어도 항상 남긴다. 예산이 0 이하면 빈 배열이다. 추정 토큰은 `ceil(글자 수 / 4 × 1.25)`이고 글자 수는 문자열이면 길이, 배열이면 원소 합, 해시이면 `to_json` 길이다. Responses 경로와 Anthropic 경로에는 자르기가 없다. | 코드 확인 |
| R-32 | 응답 길이 상한 | OpenAI는 `LLM_MAX_RESPONSE_TOKENS` 또는 `Setting.llm_max_response_tokens`가 양수로 명시됐을 때만 `max_output_tokens`(Responses) / `max_tokens`(Chat Completions)를 요청에 싣는다. 512는 R-31 계산용이고 요청에는 싣지 않는다. Anthropic은 항상 `max_tokens = ENV ANTHROPIC_MAX_TOKENS`(기본 4096)를 싣는다. 입력이 모델 한도를 넘으면 provider 오류가 나고 R-23·R-14로 간다(추론: 서버 오류 문구는 외부 동작, U-05). | 코드 확인 / 추론(오류 경로) |
| R-33 | 도구 결과와 요청 크기 제한 | 도구 결과(`function_result`)·in-flight 결과를 글자 수·토큰 수로 자르는 코드는 없다. 크기 제어는 각 도구의 페이지 크기·최대 건수뿐이다(1.4.2). 메시지 `content` 길이 상한도 모델 검증에 없다. | 코드 확인(부재, 2.1) |
| R-34 | 토큰·비용 상한 | 가족·사용자별 토큰 예산이나 비용 한도로 요청을 막는 코드는 없다. `llm_usages`는 기록(R-25)과 통계 화면 용도다. R-31의 "예산"은 컨텍스트 창 안에서 history를 자르는 규칙이다. | 코드 확인(부재, 2.1) |

**provider 선택(`Ai::Router`)과 요청·응답 계약**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-35 | provider 구성 | OpenAI: 토큰 = `OPENAI_ACCESS_TOKEN` > `Setting.openai_access_token`(없으면 provider 없음), `uri_base`, `model`. 커스텀 endpoint인데 모델이 비어 있으면 provider를 만들지 않고 오류 로그를 남긴다. 요청 타임아웃은 `OPENAI_REQUEST_TIMEOUT` > Setting > 60(초, 최소 1). `OPENAI_EXTRA_HEADERS`는 JSON 객체여야 하고 파싱에 실패하거나 객체가 아니면 `{}`로 두고 오류 로그를 남긴다. 값의 `{session_id}`는 채팅 id로 요청마다 치환하고 그 헤더는 그 요청의 client 복사본에만 붙는다. Anthropic: 토큰 = `ANTHROPIC_ACCESS_TOKEN` > `ANTHROPIC_API_KEY` > Setting, `base_url`, 모델 기본 `claude-sonnet-4-6`. 프록시·TLS 설정은 `Ai::Transport::Http`의 공통 해석(HTTPS_PROXY 다음 HTTP_PROXY, NO_PROXY의 CIDR, loopback은 프록시 안 씀)을 쓴다. | 코드 확인 |
| R-36 | 모델 요청 계약(내장 assistant) | 공통 입력: 사용자 메시지 content, 모델명, 지시문, 도구 정의 `[{name, description, params_schema(JSON Schema), strict}]`, 이번 라운드(들)의 결과, `tool_choice`(`none` 또는 없음), 스트림 핸들러. **OpenAI Responses**: `POST responses {model, input, instructions, tools:[{type:"function", name, description, parameters, strict}], previous_response_id, stream, tool_choice:"none"?, max_output_tokens?}`. `input`은 `[{role:"user", content: 사용자 메시지}]`와 이번 라운드 결과의 `{type:"function_call_output", call_id, output(문자열)}`들이다. 사용자 메시지는 후속 요청에도 매번 같이 실린다(원본 동작, U-04). **OpenAI 호환 Chat Completions**: `chat {model, messages:[{role:"system", content: 지시문}, ...R-31로 자른 history, ...라운드별 assistant tool_calls 메시지와 tool 메시지], tools:[{type:"function", function:{name, description, parameters, strict}}], tool_choice:"none"?, max_tokens?}`. 이 경로는 비스트리밍이다. **Anthropic Messages**: `messages.create {model, max_tokens, messages, system_:[{type:"text", text: 지시문, cache_control:{type:"ephemeral"}}], tools:[{name, description, input_schema(strict 키 제거)}] 마지막 도구에 cache_control ephemeral, tool_choice:{type:"none"}?}`. `messages`는 이전 메시지(user는 `content`가 있을 때만 그대로, assistant는 `tool_use` 블록들 다음 `text` 블록, 도구를 썼으면 바로 뒤에 `tool_result` 블록들을 담은 user 턴)와 현재 사용자 메시지, 이어서 라운드마다 assistant `tool_use` 턴과 user `tool_result` 턴이다. `tool_use.input`은 항상 JSON 객체(파싱 불가·비객체는 `{}`), `tool_result.content`는 문자열(nil은 "")이다. | 코드 확인 |
| R-37 | 모델 응답 계약 | provider 응답은 `{id, model, messages:[{id, output_text}], function_requests:[{id, call_id, function_name, function_args(JSON 문자열), extra_content?}]}`로 정규화된다. OpenAI Responses는 `output`의 `message` 항목(텍스트 또는 refusal 문장을 줄바꿈으로 합침)과 `function_call` 항목에서, Chat Completions는 `choices[0].message`의 `content`·`tool_calls`(id를 `id`와 `call_id`로 같이 쓰고 `extra_content` 보존)에서, Anthropic은 `text` 블록들(줄바꿈으로 합침)과 `tool_use` 블록들(입력이 없는 호출은 `"{}"`)에서 만든다. 응답이 `success?`가 아니면 provider 오류를 그대로 raise한다(R-23). | 코드 확인 |
| R-38 | provider 오류의 형태 | 내장 assistant 경로는 provider의 `with_provider_response`가 요청 중 모든 예외를 provider 오류 객체(메시지, 가능하면 `details`)로 감싸 돌려주고 responder가 그것을 raise한다. 이 경로에는 재시도·failover가 없다(`Ai::Router`의 route 목록은 failover 용도로 정의돼 있으나 채팅 디스패치가 쓰지 않는다, R-48). | 코드 확인 |
| R-47 | `Ai::Router#resolve(feature)`의 규칙 | 입력은 feature 키(`Ai::Routes::MATRIX`: `chat`, `bill_setup`, `extract_pdf`, `embed`, `search_documents`, `categorize`, `shadow_categorize`, `detect_merchants`, `enhance_merchants`), 가족, 사용자다. (1) 그 feature(또는 `route_of`가 가리키는 feature)의 route 중 `route.agent?`가 "가족의 채팅 모드가 external이고 feature가 `chat`인가"와 같고, 사용자가 허용되고(`serves_user?`: agent route는 `EXTERNAL_ASSISTANT_ALLOWED_EMAILS`가 비어 있지 않으면 사용자 이메일이 그 목록에 있어야 함), 가족을 서빙하는(`serves?`) 것만 남긴다. 남은 것이 없으면 `not_configured`. (2) 동의 검사: feature의 consent 키가 `chat`·`bill_setup`이고 사용자 `ai_enabled`가 false이면 `user_disabled`(다른 feature는 사용자 동의 검사를 하지 않는다). (3) 남은 route 중 agent이거나 모델이 feature의 필요 capability(`chat`은 `tools`·`streaming`, `extract_pdf`는 `structured_output`, `embed`는 `embedding` 등)를 가진 것만 남기고 없으면 `capability_missing`. 모두 통과하면 route 순서를 유지한 `Plan`을 돌려주고 `Ai.available?`는 true다. 사용자에게 보일 문구는 관리자(`manages_instance_settings?`)와 일반 구성원이 다르다. route 목록은 프로세스마다 ENV와 `Setting`에서 만든다(OpenAI·Anthropic 모델의 capability는 모델명 prefix 허용 여부와 PDF 지원 여부로 정해진다). | 코드 확인 |
| R-48 | 채팅 디스패치와 `Ai::Router`의 관계 | 채팅 응답 경로(R-09, R-15)는 `Ai.available?(:chat)`·`Ai.plan(:chat)`·`requires_ai :chat`을 호출하지 않는다. 채팅 가능 여부는 R-02, provider 선택은 R-15가 정한다. `Ai::Router`는 이 기능에서 (a) `ai_feature`를 가진 도구의 노출(R-60: `import_bank_statement` → `extract_pdf`), (b) `search_family_files` 실행(R-81), (c) 문서 업로드 가드(R-53)에 쓰인다. `chat` feature의 route 목록은 만들어지지만 채팅 응답은 읽지 않는다. | 코드 확인(부재, 2.1) |

**외부 assistant**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-40 | 외부 assistant 구성(`Assistant::External.config`) | `url` = `EXTERNAL_ASSISTANT_URL` > `Setting.external_assistant_url`, `token` = `EXTERNAL_ASSISTANT_TOKEN` > Setting. `model` = `EXTERNAL_ASSISTANT_MODEL` > `Setting.external_assistant_model`(비어 있으면) > 옛 설정: `EXTERNAL_ASSISTANT_AGENT_ID` > `Setting.external_assistant_agent_id` > `"main"`을 `openclaw/` 접두사 없으면 붙인 값. `agent_id`(헤더 `X-Agent-Id`)는 선택된 모델이 있으면 그 모델에서 `openclaw/`를 뗀 값(`openclaw`·`openclaw/default`·빈 값은 `"main"`), 선택된 모델이 없으면 `EXTERNAL_ASSISTANT_AGENT_ID` 또는 옛 모델에서 구한 값이다. `session_key`는 `EXTERNAL_ASSISTANT_SESSION_KEY` 기본 `agent:main:main`. `configured?`는 url·token·model이 모두 있을 때 true다(모델은 옛 기본값이 있어 사실상 url과 token이 기준). `allowed_user?`는 `EXTERNAL_ASSISTANT_ALLOWED_EMAILS`(쉼표 구분, 공백 제거, 소문자)가 비어 있으면 모두 허용, 있으면 사용자 이메일(소문자)이 그 목록에 있어야 하며 이메일이 비어 있으면 거부한다. `available_for?(user) = configured? && allowed_user?(user)`. | 코드 확인 |
| R-41 | 외부 assistant 턴 시작 | `configured?`가 아니면 `Assistant::Error`("External assistant is not configured. ...")를, 허용되지 않은 사용자면 `Assistant::Error`("Your account is not authorized to use the external assistant.")를 낸다. 통과하면 `POST <url>`로 JSON `{model, messages, stream: true, user: "sure-family-<family_id>"}`를 보낸다. `messages`는 이 채팅의 `status = complete`인 `UserMessage`·`AssistantMessage`를 시간순으로 마지막 20개만 `{role, content}`로 만든 것이다(현재 사용자 메시지 포함). 시스템 프롬프트, 세션 컨텍스트, 도구 정의, tool call 기록은 보내지 않는다. 헤더는 `Authorization: Bearer <token>`, `Content-Type: application/json`, `Accept: text/event-stream`, `X-Agent-Id`, `X-Session-Key`다. 연결 타임아웃 10초, 읽기 타임아웃 120초. | 코드 확인 |
| R-42 | 외부 응답 스트림 파싱 | HTTP 2xx가 아니면 `Assistant::Error`("External assistant returned HTTP <코드>.")를 낸다(본문 앞 500자는 로그만). 본문을 줄 단위로 읽어 `data:` 줄만 처리한다(접두사 뒤 공백 하나 제거). `[DONE]`이면 종료. 그 밖은 JSON으로 파싱하고(실패하면 경고 로그 후 그 줄만 건너뜀) 첫 파싱 성공 응답의 `model`을 기록하고, `choices[0].delta.content`가 null이 아니면 그 문자열을 `AssistantMessage`에 덧붙인다(R-12). 버퍼가 1 MiB(1,048,576바이트)를 넘으면 `Assistant::Error`("External assistant stream exceeded maximum buffer size.")다. 종료 후 내용이 비어 있으면 `Assistant::Error`("External assistant returned an empty response.")다. 성공하면 기록한 `model`로 `ai_model`을 갱신한다. | 코드 확인 |
| R-43 | 외부 요청의 일시 오류 재시도 | `Net::OpenTimeout`, `Net::ReadTimeout`, `Errno::ECONNREFUSED`, `Errno::ECONNRESET`, `Errno::EHOSTUNREACH`, `SocketError`가 나고 아직 텍스트가 한 조각도 흘러나오지 않았으면 최대 2번 재시도한다(첫 시도 포함 최대 3번, 대기 1초 후 2초). 모두 실패하면 `Assistant::Error`("External assistant is temporarily unavailable.")다. 텍스트가 이미 흐른 뒤에 끊기면 재시도하지 않고 `Assistant::Error`("External assistant connection was interrupted.")다. HTTP 오류 응답(R-42)은 재시도하지 않는다. | 코드 확인 |
| R-44 | 외부 assistant 실패 정리 | `Assistant::Error`와 `ActiveRecord::ActiveRecordError`는 응답이 아직 완료되지 않았다면 pending 메시지를 내용 유무와 관계없이 삭제하고(내장 assistant의 `failed` 보존과 다르다) `chat.add_error`를 부른다. 그 밖의 예외는 로그를 남기고 같은 삭제 후 `Assistant::Error`("Something went wrong with the external assistant. Check server logs for details.")로 감싸 `chat.add_error`를 부른다. | 코드 확인 |
| R-45 | 외부 assistant의 도구·기록 | 외부 경로는 우리 쪽 도구·프롬프트·history 자르기를 쓰지 않고, 모델 호출 기록(`llm_usages`)도 만들지 않는다(요청 시작 때 설치 telemetry `Usage.capture`만 부른다). 외부 에이전트가 가족 데이터를 읽으려면 `/mcp`(행 16)로 같은 도구 registry를 호출해야 한다(R-60). | 코드 확인(부재, 2.1) |
| R-46 | 외부 agent 목록 조회(`ModelCatalog`) | URL의 경로가 `/chat/completions`로 끝나야 하고(아니면 오류) 그 부분을 `/models`로 바꾸고 query·fragment를 지운 주소에 `GET`한다(헤더 `Authorization: Bearer`, `Accept: application/json`, 연결 5초·읽기 10초). HTTP 2xx가 아니거나 JSON이 `{data:[객체...]}`가 아니면 오류. 각 항목에서 `id`가 비어 있지 않은 것만 `{id, label}`로 돌려주고, `openclaw`·`openclaw/default`·`openclaw/<이름>`은 번역된 라벨, 그 밖은 id를 라벨로 쓴다. | 코드 확인 |

**벡터 검색(가족 문서)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-50 | 벡터 저장소 선택(`VectorStore::Registry.adapter`) | 백엔드는 `VECTOR_STORE_PROVIDER`(`openai`·`pgvector`·`qdrant`로 인식되는 값)가 있으면 그것, 없으면 `Setting.llm_provider == "anthropic"`이면 `pgvector`, 없으면 OpenAI 토큰이 있으면 `openai`, 아니면 없음이다. 어댑터는 호출마다 새로 만든다. `openai`는 `embed` route의 vector store endpoint에 API key가 있어야 만들어지고, `pgvector`는 `vector_store_chunks` 표가 이미 있거나 서버에 `vector` 확장이 설치 가능(`pg_available_extensions`)할 때만 만들어지며, `qdrant`는 `QDRANT_URL`(기본 `http://localhost:6333`)·`QDRANT_API_KEY`로 만든다. 만들 수 없으면 nil이다. | 코드 확인 |
| R-51 | Qdrant 어댑터 | 모든 연산(`create_store`, `delete_store`, `upload_file`, `remove_file`, `search`)이 "Qdrant adapter is not yet implemented" 오류를 돌려준다. 그래서 `qdrant`를 고르면 문서 업로드는 실패(R-54)하고 `search_family_files`는 `search_failed`(R-81)로 끝난다. 설정 안내 문구는 qdrant를 선택지로 안내하지만 구현은 없다(문서와 구현 차이). | 코드 확인 |
| R-52 | 가족 문서 저장소 확보(`Family#ensure_vector_store!`) | `vector_store_id`가 이미 있으면 그것을 돌려준다. 없으면 어댑터가 `create_store(name: "Family <id> Documents")`를 하고, 성공하면 `families.vector_store_id`에 저장한다. 저장에 실패하면 방금 만든 store를 지우려 시도하고(실패는 무시) nil을 돌려준다. 어댑터가 없거나 생성이 실패해도 nil이다. pgvector의 `create_store`는 UUID만 만들고 DB에는 아무것도 쓰지 않는다. | 코드 확인 |
| R-53 | 문서가 업로드되는 경로(진입점은 두 곳뿐) | (a) 가져오기 화면(`DocumentImport` 유형, `imports#create`): `Ai.availability(:embed)`가 가능해야 하고, 어댑터가 있어야 하며, 파일 크기가 `Import::MAX_PDF_SIZE`(25 MB) 이하여야 하고, 확장자(소문자)가 어댑터의 `supported_extensions`에 있어야 한다. 확장자가 `.pdf`이면 PDF 형식 검사(`valid_pdf_file?`) 뒤 PDF 가져오기로 가서(역할이 admin 또는 member가 아니면 거부) `PdfImport`를 만들고 job이 처리한다(아래 (b)). `.pdf`가 아니면 그 자리에서 `Family#upload_document`를 호출하고 성공이면 알림, nil이면 "document_upload_failed" 알림이다. (b) PDF 처리 job(`ProcessPdfJob`): `process_with_ai`로 문서 종류를 정한 직후 `Ai.available?(:embed, family:)`이면 PDF 원본을 `metadata: {"type" => 문서 종류}`와 함께 업로드한다. `upload_document`가 nil을 돌려주면 경고 로그만 남기고 job은 계속한다. `family_documents.create!` 등에서 예외가 나면 job의 바깥 rescue가 `PdfImport`를 `failed`로 만들고 다시 raise한다(`process_pdf_job.rb:43-52`). 이 두 곳 말고 `upload_document`를 부르는 곳은 찾지 못했다. | 코드 확인(부재 일부, 2.1) |
| R-54 | `Family#upload_document(file_content:, filename:, metadata:)` | 어댑터가 없거나 R-52가 nil이거나 `adapter.upload_file`이 실패하면 nil을 돌려주고 `family_documents` 행을 만들지 않는다. 성공하면 `FamilyDocument`를 `filename`, `content_type`(파일명으로 추정한 MIME), `file_size`(바이트 수), `provider_file_id`(어댑터가 돌려준 `file_id`), `status = "ready"`, `metadata`로 만든다. 상태가 `pending`·`processing`·`error`로 바뀌는 경로(`mark_error!` 등)와 문서 삭제(`remove_document`)의 호출처는 `app`·`lib`에서 찾지 못했다. | 코드 확인(부재, 2.1) |
| R-55 | pgvector 업로드·청킹(`VectorStore::Pgvector#upload_file`) | 확장자가 `.pdf`·`.txt`·`.md`·`.csv`·`.json`·`.xml`·`.html`·`.css`·`.js`·`.ts`·`.py`·`.rb`·`.go`·`.java`·`.php`·`.c`·`.cpp`·`.sh`·`.tex`일 때만 텍스트를 뽑는다(PDF는 페이지 텍스트를 빈 줄로 이어 붙임, 텍스트류는 UTF-8로 변환하되 잘못된 바이트는 치환). 그 밖의 확장자나 텍스트가 비면 "Could not extract text from <파일>" 오류다. 청킹: 텍스트를 빈 줄(`\n\s*\n`)로 문단으로 나누고 문단은 앞뒤 공백을 지우며 빈 문단은 버린다. 문단이 2000자를 넘으면 2000자 조각을 1800자 간격(겹침 200자)으로 하드 분할한다. 조각을 현재 청크에 `"\n\n"`로 이어 붙이되 이어 붙인 길이가 2000자를 넘으면 현재 청크를 확정하고, 새 청크는 확정한 청크의 마지막 200자 + `"\n\n"` + 조각으로 시작한다(그래서 새 청크는 2000자를 넘을 수 있다). 청크가 하나도 없으면 "No chunks produced from <파일>" 오류. 임베딩: 청크를 50개씩 `POST <embedding_uri_base>/embeddings {model, input:[...]}`(타임아웃 읽기 120초·연결 10초, `Authorization: Bearer`는 키가 있을 때)로 보내 `data[].index` 순서로 정렬해 합친다(`data`가 없으면 오류). `file_id`는 UUID이고 청크들은 한 DB transaction 안에서 `vector_store_chunks`(`store_id`, `file_id`, `filename`, `chunk_index`, `content`, `embedding`, `metadata`)에 insert된다. 표가 없으면 첫 사용 때 `vector` 확장을 켜고 `vector(EMBEDDING_DIMENSIONS, 기본 1024)` 열로 표를 만든다. 임베딩 모델 기본값은 `mxbai-embed-large`, 기본 서버는 `https://api.openai.com/v1/`다. | 코드 확인 |
| R-56 | 검색 어댑터 계약(`search(store_id:, query:, max_results: 10)`) | 반환은 `[{content, filename, score, file_id}]`다. pgvector: 질의를 임베딩하고 같은 `store_id`의 청크를 코사인 거리(`embedding <=> query`) 오름차순으로 `max_results`개 가져오며 `score = 1 − 거리`다. 최소 점수 기준은 없다. OpenAI: 호스팅 vector store에 `vector_stores.search(query, max_num_results)`를 보내고 각 결과의 텍스트 조각들을 줄바꿈으로 합쳐 `content`로 한다. OpenAI 쪽은 청킹·임베딩을 서버가 하고 업로드는 파일을 올린 뒤 store에 붙이며(붙이기 실패 시 올린 파일을 지움), 지원 확장자 목록은 `SUPPORTED_EXTENSIONS`(`.c .cpp .css .csv .docx .gif .go .html .java .jpeg .jpg .js .json .md .pdf .php .png .pptx .py .rb .sh .tar .tex .ts .txt .xlsx .xml .zip`)다. | 코드 확인 |

**도구 공통 계약**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-60 | 모델·MCP 클라이언트에 노출하는 도구 목록(`Assistant.function_classes(user)`) | 기본 35개(1.4.2의 R-70~R-104 중 `get_*`·쓰기·이체·규칙 도구)에, `user.preview_features_enabled?`이면 preview 14개(R-105~R-118)를 더하고, `user.guest?`이면 가족 설정 도구 5개(`create_tag`, `update_tag`, `create_category`, `update_category`, `delete_category`)를 뺀다. 마지막으로 `ai_feature`를 가진 도구(`import_bank_statement`만, feature `extract_pdf`)는 `Ai.available?(feature, family:, user:)`일 때만 남긴다(`feature.nil? || user.nil? || Ai.available?`라서 사용자가 nil이면 항상 포함된다, `assistant.rb:112-113`). 내장 assistant는 이 목록의 클래스를 `chat.user`로 만들어 쓴다. 단 guest는 R-16 때문에 내장 채팅에서 도구가 없으므로 guest 제외는 `/mcp`에서만 관찰된다. `/mcp`의 `tools/list`·`tools/call`도 같은 목록을 쓰고, 목록에 없는 도구는 호출할 수 없다(없는 이름과 같은 "Unknown tool" 응답). | 코드 확인 |
| R-61 | 도구 정의(`to_definition`) | `{name, description(모델이 읽는 영문 지침), params_schema, strict}`다. `params_schema`는 `{type:"object", properties, required, additionalProperties:false}`이고 enum이 빈 배열이면(새 가족의 계정명 등) 그 제약을 지우고 `type: "string"`만 남긴다. `strict`는 `strict_mode?`이고 기본은 true인데 49개 중 `get_bill_details`를 뺀 모든 도구가 false로 덮어쓴다. 그래서 대부분 선택 인자를 가진다. 호출 인자는 JSON 객체이고 `required`에 없는 키는 없을 수 있다. | 코드 확인 |
| R-62 | 도구 호출 실행(`FunctionToolCaller`) | 인자 문자열(비어 있으면 `"{}"`)을 JSON으로 파싱해 도구의 `call(hash)`를 부르고 반환 객체를 `function_result`로 저장한다. 도구는 예외를 모델에게 던지지 않고 아래 객체로 바뀐다. 이름이 목록에 없으면 `{error:"Unknown tool: <이름>", hint:"Only call tools from the provided list."}`, JSON 파싱 실패는 `{error:"Arguments were not valid JSON", hint:"Re-send <이름> with valid JSON arguments."}`, `RecordNotFound`는 SQL을 감추고 `{error:"No such record, or it is not one you have access to", hint:"That record was not found. List valid options first (for example get_accounts or get_categories) and retry once with an exact match."}`(없는 id와 권한 없는 id를 구별하지 않는다), `Date::Error`·`ArgumentError`·`KeyError`는 `{error:<예외 메시지>, hint:"Check argument formats (dates are YYYY-MM-DD) and retry once with corrected arguments."}`, 그 밖의 모든 예외는 `{error:"<도구명> failed unexpectedly", hint:"Do not retry with the same arguments. Answer with the data you already have and note the gap."}`다. 예외 클래스가 위 목록에 없는 도구 내부 오류(`TypeError`, `Assistant::Error`, 검증 예외 등)는 모두 마지막 항목으로 간다. `/mcp`의 `tools/call`은 다르게 처리해 모든 예외를 `{content:[{type:"text", text:{error:"The tool failed to run", tool:<이름>}}], isError:true}`로 바꾼다. | 코드 확인 |
| R-63 | 도구 반환의 세 가지 오류 형태 | 이 기능의 도구는 실패를 반환값으로 알린다. (a) `{success:false, error:<키>, message}`(대부분의 쓰기·조회 도구, 추가 필드를 붙이는 도구도 있다), (b) `{error:<문장>, hint:<문장>}`(bills 도구 7개와 R-62의 변환 객체, `success` 키가 없다), (c) `{error:<키>, message}`(`get_balance_sheet`, `get_valuations`, `get_income_statement`, `success` 키가 없다). 성공 객체에 `success: true`가 있는 도구와 없는 도구가 섞여 있다(읽기 도구 대부분은 없다). 결과는 JSON 문자열로 모델에게 돌아가고 `nil`은 빈 문자열이다. | 코드 확인 |
| R-64 | 페이지 인자 공통 | 페이지 크기를 받는 도구(`get_transactions`·`get_tags`·`get_categories`·`get_merchants`·`get_rules`)는 `page_size`가 없으면 도구별 기본(50), 있으면 정수로 바꿔 1~100(`MAX_PAGE_SIZE`)로 자른다. `page`가 없거나 0 이하·숫자가 아니면 1이다. `get_holdings`·`get_valuations`는 `page_size`를 받지 않고 50으로 고정이다. 응답에 `total_results`·`page`·`page_size`·`total_pages`가 있다. | 코드 확인 |
| R-65 | 도구의 데이터 범위(사용 지점만, 정의는 U-01) | 읽기 도구는 가족 범위(태그, 카테고리, 규칙, 인사이트, 명세서 일부) 또는 접근 계정 범위(`accessible_accounts.visible`, 정기 거래·청구서는 `recurring_transactions.accessible_by(user)`, 가맹점은 `available_merchants_for(user)`)다. 쓰기 도구는 쓰기 계정 범위(`create_transaction`, `delete_transaction`, `set_opening_balance`, `record_valuation`, 이체 쓰기 도구, `create_bill`·`update_bill`·`record_bill_payment`의 계정 지정)이거나 거래의 annotate 범위(`update_transaction`: 소유자·`full_control`은 모든 필드, `read_write` 공유는 `name`을 뺀 필드만)다. 반례로 `create_goal`과 `import_bank_statement`는 접근·쓰기 계정 판정을 쓰지 않고 `family.accounts`로 찾는다(R-91, R-93). | 코드 확인 |
| R-66 | 쓰기 도구의 서버측 확인 절차 | 서버에 사용자 확인 단계(승인 토큰, 승인 화면, 확인 후 실행)는 없다. 모델이 도구를 호출하면 즉시 실행한다. 사용자 확인에 해당하는 서버측 장치는 `apply_rule`의 `preview_token`(R-104)뿐이다. 그 밖에 서버가 효과를 제한하는 게이팅은 있다. `create_rule`·`update_rule`은 규칙을 항상 비활성으로 저장해 `apply_rule` 전에는 거래를 바꾸지 않고(R-102, R-103), `import_bank_statement`는 가져오기 초안만 만들어 사용자가 게시해야 반영된다(R-93). 나머지는 도구 `description`이 모델에게 "사용자에게 확인하라"고 적은 문장뿐이다. 그 문장이 있는 도구: `delete_category`("Confirm with the user before calling"), `create_goal`("Only call once they've confirmed"), `create_bill`·`update_bill`·`record_bill_payment`("Confirm ... with the user before"). 시스템 프롬프트(R-26)에는 쓰기 전 확인 규칙이 없다. `delete_transaction`·`create_transaction`·`update_transaction`·`update_budget`·`set_opening_balance`·`record_valuation`·`create_tag` 등의 description에는 확인 문장이 없다. 채팅 화면은 도구 호출을 debug 모드에서만 보여 주고 승인 UI는 없다. | 코드 확인(부재, 2.1) |
| R-67 | dry run·미리보기 | 변경 없이 효과만 돌려주는 `dry_run: true`는 `match_transfer`(R-95), `unmatch_transfer`(R-97), `update_transfer`(R-98), `set_opening_balance`(R-92) 네 도구만 지원한다. 규칙은 `preview_rule`로 영향을 미리 보고(R-101) `create_rule`·`update_rule`이 같은 미리보기를 같이 돌려준다. 그 밖의 쓰기 도구에는 dry run이 없다. | 코드 확인(부재, 2.1) |
| R-68 | 파괴적 동작과 보호 장치 요약 | 삭제·되돌리기 어려운 도구와 서버가 거는 보호는 다음뿐이다. `delete_transaction`: 쓰기 계정 범위 + 선택적 `account_id` 일치 확인 + 분할 자식 삭제 거부(R-84). `delete_category`: 가족 범위 + 자기 자신을 대체로 지정 거부, 카테고리 잠금은 검사하지 않음(R-89). `unmatch_transfer`: dry run, 거래는 유지, 수수료 거래는 삭제(R-97). `apply_rule`: `preview_token`과 정의·매칭 수 일치(R-104). `review_transfer`의 reject, `update_rule`의 정의 교체는 비활성화를 동반한다(R-96, R-103). 삭제·변경을 되돌리는 도구나 실행 취소는 없다. | 코드 확인 |
| R-69 | 예산·월 인자의 공통 해석(`MonthResolvable`) | `month`는 `YYYY-MM` 또는 영문 3글자 월 `MMM-YYYY`만 받는다(정규식으로 전체를 검사한 뒤 파싱, 다른 형식은 `Assistant::Error`("Invalid month: <입력>. Use YYYY-MM or MMM-YYYY.")). 월 시작일이 1이면 그 달 1일, 가족의 `month_start_day`가 1이 아니면 그 달의 시작일(`month_start_day`일)이다. 입력이 없으면 시작일이 1이면 오늘의 달 1일, 아니면 오늘이 속한 사용자 정의 기간의 시작일이다. | 코드 확인 |

#### 1.4.2 도구 표 (49개)

도구는 사용자가 아니라 모델이 호출하므로 아래 표는 모델이 보는 이름·입력과 서버가 돌려주는 값이다. 입력의 `*`는 `required` 항목이다(대부분 `strict: false`라서 나머지 키는 없어도 된다). "도메인 링크"의 R-ID는 선행 스펙의 규칙이고 그 규칙의 동작을 이 문서에서 반복하지 않는다. "실패"의 코드는 `{success:false, error:<코드>, message}` 형태(R-63의 (a))이며 다른 형태는 따로 적는다. 모든 행의 검증 수준은 코드 확인이고 예외는 행에 쓴다. C-ID는 R-ID 번호에서 30을 뺀 번호다(R-70 → C-40, R-118 → C-88).

**읽기 도구**

| R-ID | 도구 | 입력 | 범위·권한 | 성공 반환 | 도메인 링크 | 실패 |
|---|---|---|---|---|---|---|
| R-70 | `get_transactions` (항상, 읽기) | `page`, `page_size`(기본 50), `order`(`asc`·`desc`, 기본 desc), `sort_by`(`date`·`amount`(절댓값)), `search`, `amount`+`amount_operator`(`equal`·`less`·`greater`), `start_date`, `end_date`, `types[]`(`income`·`expense`·`transfer`), `statuses[]`(`pending`·`confirmed`), `account_ids[]`, `accounts[]`(이름), `categories[]`(이름, `"Uncategorized"` 허용, R-75와 T-14), `merchants[]`, `tags[]` | 접근 계정 범위의 id 집합을 항상 적용한다. | `{transactions:[{id, entry_id, name, date, amount(항상 양수), currency, formatted_amount, classification(income·expense), account, notes, category, merchant, tags[], is_transfer, kind, pending?(참일 때만), excluded?(참일 때만), transfer_account?(반대편 계정이 접근 가능할 때만), clean_name?, rail?, operation_date?}], total_results, page, page_size, total_pages, total_income, total_expenses(둘 다 포맷된 문자열)}`. `total_*`는 필터 전체 기준이고 세금우대 계정은 제외라 현재 쪽 합과 다를 수 있다. | [transactions](./transactions.md) R-18·R-42·R-43·R-45·R-53·R-55·R-68, [transfer-matching](./transfer-matching.md) R-35 | 도구가 직접 내는 실패 없음(잘못된 날짜 등은 R-62) |
| R-71 | `get_accounts` (읽기) | `include_balance_series`(기본 false), `series_period`(`Period` 키, 기본 `last_365_days`) | 접근 계정 | `{as_of_date, accounts:[{id, name, balance, currency, balance_formatted, classification, type(accountable 종류), subtype, start_date, is_linked, provider, status, terms?, historical_balances?}]}`. `terms`는 Loan(`interest_rate`, `base_interest_rate?`, `rate_type`, `term_months`, `monthly_payment`+`_formatted`, `original_balance`+`_formatted`)과 CreditCard(`apr`, `minimum_payment`, `annual_fee`, `available_credit`, `expiration_date`)만 있고 입력 안 된 키는 생략한다. `historical_balances`는 `{start_date, end_date, interval, currency, values[실수]}`이고 기간 시작이 계정 시작일보다 이르면 계정 시작일로 올린다. | [account-balances](./account-balances.md) R-01·R-09·R-15(`start_date`)·R-41~R-43·R-48 | 없음 |
| R-72 | `get_holdings` (읽기) | `page*`, `accounts[]`(Investment·Crypto 계정 이름), `securities[]`(ticker) | 접근 계정 중 Investment·Crypto 자체 쿼리를 쓴다. | 계정·종목 쌍마다 `qty ≠ 0`인 행 중 가장 최근 날짜의 행 하나(`DISTINCT ON (account_id, security_id)`, `where.not(qty: 0)`가 DISTINCT ON보다 먼저 걸리고 `date` 내림차순)를 뽑으므로 최신 행 수량이 0인 종목은 마지막으로 0이 아니던 옛 행으로 다시 나타난다(T-26). 이 행들을 금액 내림차순으로, `{holdings:[{ticker, name, quantity, price, currency, amount, formatted_amount, weight, average_cost, formatted_average_cost, account, date}], total_results, page, page_size(50 고정), total_pages, total_value}`. `total_value`는 필터 전체의 `sum(:amount)`를 환산 없이 합산해 가족 통화로 포맷한다. | 자체 쿼리(`get_holdings.rb:105-147`)라 [investments-securities](./investments-securities.md) R-39·R-52·R-53을 쓰지 않는다 | 없음 |
| R-73 | `get_balance_sheet` (읽기) | `period`(`Period` 키), `start_date`+`end_date`(둘 다 있어야 우선), `interval`(`1 day`·`1 week`·`1 month`, 기본 `1 month`) | 접근 계정 | `{as_of_date, oldest_account_start_date, currency, net_worth:{current, monthly_history}, assets:{...}, liabilities:{...}, insights:{debt_to_asset_ratio}}`. 기본 기간은 `max(5년 전, 가족의 가장 이른 entry 날짜)`~오늘, 시계열은 `{start_date, end_date, interval, currency, values[]}`이고 `period.days / (1·7·30)`이 400을 넘으면 거부한다. 기간 시작이 오늘이면 시계열은 `[]`. | [account-balances](./account-balances.md) R-41~R-43·R-46·R-48 | R-63 (c)형 `invalid_date`(형식 오류, 시작>끝), `too_many_points` |
| R-74 | `get_income_statement` (읽기) | `start_date*`, `end_date*`, `account_ids[]`, `group_by`(`none`·`month`), `compare_previous_period` | `income_statement(user:)`의 적격 계정(숨김·보고 제외·세금우대 계정은 제외) | 기본: `{currency, period, income:{total, by_category:[{name, total, percentage_of_total, subcategory_totals[]}]}, expense:{...}, insights:{net_income, savings_rate, median_monthly_income, median_monthly_expenses, avg_monthly_expenses}, invested?, monthly_series?, previous_period?}`. `account_ids`를 주면 카테고리 분해 없이 `{income:{total, by_category:nil}, expense:{...}, net, breakdown_omitted_reason}`. `invested`는 가족 `investment_contributions_as_spending`이 false일 때만. `group_by: "month"`는 달력 월 버킷(최대 36). `previous_period`는 같은 길이의 직전 기간과 `income_change`·`expenses_change`(`amount`, `percent`). | [budgets](./budgets.md) R-17(소비 계약만), 본체는 [reports-insights](./reports-insights.md) R-01~R-07·R-14 | (c)형 `invalid_date`, `unknown_account_ids`(+`unknown_ids`), `too_many_periods`. 필수 인자 누락은 `Date.parse(nil)`의 `TypeError`가 R-62의 마지막 항목으로 간다(추론, U-06). |
| R-75 | `get_budget` (읽기, 단 쓰기 부작용 있음) | `month`(R-69), `prior_months`(0~11) | 가족의 예산. 가족이 `personal_budgets`이면 사용자 본인 예산 | `{currency, months:[{month, period, is_current, initialized, totals:{budgeted_spending, allocated_spending, available_to_allocate, actual_spending, available_to_spend, percent_of_budget_spent, overage_percent}, income:{expected_income, actual_income, remaining_expected_income}, categories:[{name, budgeted, actual, available, percent_spent, status(over_budget·unbudgeted·near_limit·on_track·no_activity), suggested_daily_spending?(현재 기간만), color, subcategories:[{...같은 필드, inherits_parent_budget}]}]}], months_unavailable?}`. 대상 월은 `find_or_bootstrap`으로 예산 행이 없으면 만들고, 이전 달은 있는 것만 읽는다. 유효 범위 밖 달은 `months`에서 빠지고 개수가 `months_unavailable`에 든다. | [budgets](./budgets.md) R-01·R-03·R-06·R-14·R-18~R-21·R-32·R-33 | 월 형식 오류는 `Assistant::Error`가 `get_budget`에서 rescue되지 않으므로 R-62 마지막 항목(`get_budget failed unexpectedly`)이 된다. `update_budget`과 다르다. |
| R-76 | `get_categories` (읽기) | `page`, `page_size`(50) | 가족 범위 | `{categories:[{id, name, name_with_parent, color, icon, parent_id, is_subcategory}], total_results, ...}` 이름·계층 순 | [transaction-classification](./transaction-classification.md) R-60·R-62 | 없음 |
| R-77 | `get_tags` (읽기) | `page`, `page_size`(50) | 가족 범위 | `{tags:[{id, name, color}], total_results, ...}` 이름순 | [transaction-classification](./transaction-classification.md) R-63 | 없음 |
| R-78 | `get_merchants` (읽기) | `page`, `page_size`(50), `search`(이름 부분 일치, 대소문자 무시) | `available_merchants_for(user)`(가족 가맹점 + 접근 계정 거래의 가맹점 + 최근 연결 해제된 것) | `{merchants:[{id, name, source(family·provider)}], total_results, ...}` 이름순 | [transactions](./transactions.md) R-75 | 없음 |
| R-79 | `get_recurring_transactions` (항상, 읽기) | `status`(`active`·`inactive`·`all`, 기본 active, 모르는 값은 active), `upcoming_within_days`(1~365) | 접근 가능한 반복 거래(`accessible_by(user)`). 가족의 반복 거래 꺼짐(`recurring_transactions_disabled?`) 검사 없음 | `{as_of_date, total_results, truncated(200건 초과), recurring_transactions:[{id, name, amount, expected_amount_range?, currency, status, expected_day_of_month, next_expected_date, last_occurrence_date, occurrence_count, is_manual, is_transfer, account?, destination_account?}], totals_by_currency}`. 최대 200건, `status` 순 `next_expected_date` 순. | [recurring-transactions](./recurring-transactions.md) R-01·R-52·R-64 | 없음 |
| R-80 | `get_uncategorized_transactions` (읽기) | `start_date`(기본 180일 전, 시작이 끝보다 늦으면 끝으로, 끝에서 730일보다 이르면 730일 전으로 자름), `end_date`(기본 오늘), `account_ids[]`, `limit`(기본 20, 1~50) | 접근 계정 ∩ `account_ids`. 형식이 틀린 날짜는 오류 없이 기본값으로 대체 | 카테고리 없는 거래를 지급처 그룹으로 묶어 `{as_of_date, period, summary:{transaction_count, payee_count, totals_by_currency:{<통화>:{expense:{amount, formatted, transaction_count}, income:{...}, transaction_count}}}, payees:[{payee, rail, currency, classification, transaction_count, total_amount, total_amount_formatted, first_seen, last_seen, accounts[], transaction_ids(최대 10)}], truncated, enrichment:{auto_categorize_rule·auto_detect_merchants_rule(absent·active·inactive), llm_routes:{categorize, detect_merchants}, note}}`. 그룹 키는 가맹점 이름 또는 정규화한 이름(대문자)+`rail`+통화+분류이고 `investment_contribution`·`loan_payment` 종류는 지출로 센다. 합계는 통화별로만 낸다. | [transaction-classification](./transaction-classification.md) R-28·R-52·R-53·R-56, [transactions](./transactions.md) R-18 | 없음 |
| R-81 | `search_family_files` (항상, 읽기) | `query*`, `max_results`(기본 10, 1~20) | 가족의 `vector_store_id`(가족 전체 문서, 계정·구성원별 구분 없음, U-01) | 성공 `{success:true, query, result_count, results:[{content, filename, score}]}`, 결과가 없으면 `{success:true, results:[], message:"No matching documents found for the query."}`. 검사 순서: (1) `vector_store_id` 없음 → `no_documents` (2) `Ai.availability(:search_documents)` 불가 → `ai_unavailable`(+`reason`, 문구) (3) 어댑터 없음 → `provider_not_configured` (4) 검색 실패(Qdrant 포함, R-51) → `search_failed`("Failed to search documents: <원문>") (5) 예외 → `search_failed`("An error occurred while searching documents: <앞 200자>"). | 본 문서 R-50~R-56 | (a)형, 위 코드 |

**쓰기 도구**

| R-ID | 도구 | 입력 | 범위·권한·확인 | 성공 반환 | 도메인 링크 | 실패 |
|---|---|---|---|---|---|---|
| R-82 | `create_transaction` (항상, 쓰기) | `account_id*`, `date*`(ISO 8601), `amount*`, `name*`, `type`(`income`·`expense`·`inflow`·`outflow`), `currency`, `notes`(null 허용), `category_id`, `merchant_id`, `tag_ids[]`, `external_id`, `source`(기본 `"mcp"`), `user_modified` | 쓰기 계정. 카테고리·태그는 가족 소유, 가맹점은 `available_merchants_for`에 있어야 한다. 서버 확인 없음, dry run 없음. 부호: `type`이 `income`·`inflow`면 `-|amount|`, `expense`·`outflow`면 `+|amount|`, 없으면 입력 그대로(음수 = 수입). 통화 기본은 계정 통화 > 가족 기본 통화. `external_id`가 있으면 (계정, `source`, `external_id`)가 같은 거래가 이미 있을 때 새로 만들지 않고 기존 거래를 돌려준다. 저장 뒤 `lock_saved_attributes!`를 항상 걸고 태그가 있으면 `lock_attr!(:tag_ids)`, `user_modified`가 참이면 `mark_user_modified!`를 부른다(`create_transaction.rb:190-192`). | `{success:true, created:true, transaction:{id, entry_id, name, date, amount(문자열), amount_formatted, currency, type, notes, category?, merchant?, tags[]}, message, warning?}`. 중복이면 `created:false`. 저장 뒤 계정 sync를 큐에 넣고 그 큐 등록이 실패하면 `warning`만 달린다(생성은 성공). | [transactions](./transactions.md) R-03~R-07·R-13·R-18·R-68·R-69(API 경로와 같은 Entry 경로) | `account_not_found`, `invalid_date`, `invalid_amount`, `invalid_name`, `invalid_currency`, `invalid_uuid`, `invalid_category`, `invalid_merchant`, `invalid_tags`, `validation_failed`, `idempotency_conflict`(같은 키가 거래가 아닌 entry) |
| R-83 | `update_transaction` (항상, 쓰기) | `id*`, `name`, `notes`(null=지움), `category_id`(null=지움), `merchant_id`(null=지움), `tag_ids[]`(전체 교체, 빈 배열=전부 지움) | 접근 계정의 거래를 찾고, 권한은 소유자·`full_control`이면 전체, `read_write`이면 `name`을 보낼 때 거부. 분할 자식 거부. 서버 확인 없음. 바꾼 값은 속성 잠금(`lock_saved_attributes!`, 태그는 `lock_attr!(:tag_ids)`)이 걸려 이후 자동화가 덮어쓰지 못한다. | `{success:true, transaction:{id, name, date, notes, category?:{id,name}, merchant?:{id,name}, tags:[{id,name}]}, message}` | [transactions](./transactions.md) R-09~R-15·R-68·R-75 | `not_found`, `split_child`, `not_authorized`, `invalid_uuid`, `invalid_category`, `invalid_merchant`, `invalid_tags`, `no_changes`, `validation_failed` |
| R-84 | `delete_transaction` (항상, 쓰기, 파괴적) | `id*`, `account_id`(선택 보호 장치) | 쓰기 계정. `account_id`를 주면 그 계정의 거래여야 한다. 분할 자식은 개별 삭제 거부(분할 원본을 지워야 함). 서버 확인 없음, description에 확인 문장 없음(R-66). 되돌리기 없음. | `{success:true, deleted:true, transaction:{id, entry_id, account_id, name, date, amount, amount_formatted, currency, type}, message, warning?}`(삭제 전 스냅샷). 이체의 다리를 지우면 반대 다리 `kind`가 되돌아가고 이체와 수수료 거래가 지워지는 효과는 도메인 규칙을 따른다. | [transactions](./transactions.md) R-20·R-68, [transfer-matching](./transfer-matching.md) R-31 | `not_found`, `split_child`, `delete_aborted` |
| R-85 | `create_tag` | `name*`, `color`(hex, 기본은 팔레트에서 무작위) | 가족 범위. guest는 목록에서 제외(R-60) | `{success:true, tag:{id, name, color}, message}` | [transaction-classification](./transaction-classification.md) R-63 | `name_required`, `validation_failed`(이름 중복 등) |
| R-86 | `update_tag` | `name*`(현재 이름), `new_name`, `color` | 가족 범위. 이름으로 찾는다 | `{success:true, tag, message}` | 위와 같음 | `not_found`, `no_changes`, `validation_failed` |
| R-87 | `create_category` | `name*`, `color`, `icon`(lucide, 기본은 이름에서 제안), `parent_id` | 가족 범위. 카테고리가 잠겨 있으면(`categories_locked?`) 거부. 하위는 부모 색을 상속하고 2단계까지 | `{success:true, category:{id, name, name_with_parent, color, icon, parent_id}, message}` | [transaction-classification](./transaction-classification.md) R-60 | `categories_locked`, `name_required`, `parent_not_found`, `validation_failed` |
| R-88 | `update_category` | `id*`, `name`, `color`, `icon`, `parent_id`(빈 문자열 = 최상위로, null = 변경 없음) | 가족 범위. 잠금 검사는 하지 않는다(코드에 `categories_locked?` 호출 없음) | `{success:true, category, message}` | 위와 같음 | `not_found`, `parent_not_found`, `invalid_parent`(자기 자신), `no_changes`, `validation_failed`(하위가 있는 카테고리를 하위로 만드는 경우 등) |
| R-89 | `delete_category` (파괴적) | `id*`, `replacement_id`(생략·null = 거래를 미분류로, 그 밖의 값은 가족 카테고리 id여야 함) | 가족 범위. description에 "Confirm with the user before calling this tool"(R-66). `replace_and_destroy!`가 거래를 대체 카테고리로 옮기고 하위는 최상위로 만들고 예산 배정을 지운다. | `{success:true, id, replacement_id, message}` | [transaction-classification](./transaction-classification.md) R-61, [budgets](./budgets.md) R-38 | `not_found`, `replacement_not_found`, `invalid_replacement` |
| R-90 | `update_budget` (쓰기) | `month`(R-69), `budgeted_spending`(≥0), `expected_income`(≥0), `categories[]:{category(이름·대소문자 무시 또는 id), amount(≥0)}` | 가족의 예산(personal이면 사용자 본인). `BudgetShare` 권한(`editable_by?`)을 확인하지 않는다(파일에 호출 없음). 서버 확인·dry run 없음. 하나도 안 주면 거부. 유효 범위 밖 달 거부. 한 DB transaction에서 예산을 만들거나 찾고, `budgeted_spending`만 주고 `expected_income`을 안 주며 예산의 예상 소득이 null이면 `expected_income = 0`을 같이 쓴다. 카테고리 변경은 하위 먼저, 부모 나중에 적용하고(부모 합 동기화가 순서에 영향받지 않게) 이월 체인 재계산은 부르지 않는다. 합성 "미분류"는 설정 불가. | `{success:true, month, totals:{budgeted_spending, expected_income, allocated_spending, available_to_allocate}, updated_categories:[{category, budgeted_spending}], message}` 금액은 가족 통화로 포맷한 문자열. | [budgets](./budgets.md) R-03·R-06·R-12·R-38 | (a)형 `no_changes`, `invalid_month`, `invalid_params`(월 형식, 음수·비숫자 금액, 카테고리 없음, 미분류 지정, 배정 행 없음 — 메시지에 원인), `validation_failed` |
| R-91 | `create_goal` (항상, 쓰기) | `name*`, `target_amount*`(>0), `target_date`, `linked_account_names*[]`(Depository 계정 이름, 1개 이상), `earmarks`({계정 이름: 금액}), `notes` | 계정을 `family.accounts`의 Depository(숨김 제외)에서 이름으로 찾는다. 접근 권한 필터가 없다(코드 확인, 의도는 추론). description에 "Only call once they've confirmed"(R-66). 이름이 중복이면 거부, 다른 목표가 계정 전체를 이미 점유(`allocated_amount` null)했는데 `earmarks`에 없으면 거부. 통화는 가족 기본 통화, 색은 팔레트에서 무작위. `target_date` 형식이 틀리면 오류 없이 nil로 두고 만든다. `earmarks`가 Hash가 아니면 `{}`이고, 값이 숫자가 아니거나 0 이하이면 조용히 버려져 그 계정은 계정 전체 점유(whole-account)로 연결된다(`create_goal.rb:185-190`, `:213-221`). 이 도구는 기본 목록에 있어 preview를 꺼도 호출되고 guest도 `/mcp`에서 호출할 수 있다([goals](./goals.md) R-02 (c)). | `{success:true, goal_id, name, target_amount_formatted, currency, target_date, url, linked_account_names, message}` | [goals](./goals.md) R-37·R-02 | `name_required`, `target_amount_invalid`, `no_linked_accounts`(+`available_accounts`), `unknown_accounts`(+`unknown_names`), `ambiguous_accounts`(+`ambiguous_names`), `account_claimed_in_full`(+`claimed_account_names`), `validation_failed`; `available_accounts` 항목은 `{name, currency, free_to_earmark, claimed_in_full}` |
| R-92 | `set_opening_balance` (쓰기, dry run 지원) | `account_id*`, `balance*`(숫자, boolean 거부), `date`(생략 시 현재 날짜 유지), `dry_run` | 쓰기 계정(숨김 제외), 연동 계정은 거부(수동 계정만). 날짜는 가장 이른 entry보다 앞이어야 한다(`date_error`). dry run이면 변경 없이 `{success:true, dry_run:true, account:{id,name,currency}, before, after, current_balance}`. | `{success:true, changed, account, before:{date, balance}, after:{date, balance}, current_balance:{changes, by?, reason}}`. `current_balance`는 이후 잔액 갱신(reconciliation)이 있으면 `changes:false`와 이유, 변화량이 0이면 `false`, 아니면 `changes:true, by:<변화량>`이다. | [account-balances](./account-balances.md) R-13(`set_opening_anchor_balance`)·R-12·R-16(이후 reconciliation valuation 조회) | `not_found`, `linked_account`, `invalid_balance`, `invalid_date`(+`oldest_entry_date`), `update_failed` |
| R-93 | `import_bank_statement` (쓰기: 가져오기 초안 생성, `extract_pdf`가 가능할 때만 노출) | `pdf_import_id*`, `account_id`(생략하면 후보 목록을 돌려준다) | PDF import는 `family.imports`에서 `type: "PdfImport"`로, 계정은 `family.accounts.find_by(id:)`로 찾는다. 접근·쓰기 권한 필터가 없다(코드 확인). 문서 종류가 `bank_statement`여야 한다. `Ai.availability(:extract_pdf)`가 불가하면 거부. `Provider::Registry.preferred_llm_provider`(R-15와 같은 순서)의 `extract_bank_statement`로 LLM을 호출하고(비용 발생, `llm_usages` 기록은 provider 쪽), 결과를 CSV(`date, amount, name, category, notes`)로 만들어 `TransactionImport`를 만든다(`date_format %Y-%m-%d`, `signage_convention inflows_positive`)와 행을 생성한다. 거래를 직접 만들지는 않고 사용자가 검토 후 게시해야 한다. | `{success:true, import_id, transaction_count, transactions_preview(앞 5건), statement_period, account_holder, message}` | 행 8 [imports](./imports.md) | `PDF import not found`, `not_bank_statement`(+`available_actions`), `account_required`(+`available_accounts`: 보이는 Depository `{id, name}`), `account_not_found`(+`available_accounts`), `ai_unavailable`(+`reason`, 문구), `extraction_failed`(제공자 오류·타임아웃·`Faraday::Error`·`RuntimeError`), `no_transactions_found`. 오류 코드가 `error`에 문장으로 들어가는 것도 섞여 있다. |

**이체 도구**

| R-ID | 도구 | 입력 | 범위·권한·확인 | 성공 반환 | 도메인 링크 | 실패 |
|---|---|---|---|---|---|---|
| R-94 | `get_transfer_match_candidates` (읽기) | `transaction_id*` | 접근 계정의 거래 | `{success:true, transaction:{transaction_id, account_id, account, name, date, amount(절댓값 문자열), amount_formatted, currency, direction(inflow·outflow), kind}, transfer?:{transfer_id, status, counterpart?}, candidates:[...같은 필드 + days_apart, previously_rejected]}`. 이미 이체이면 `transfer`만 있고 `candidates`는 `[]`. 후보는 `Transfer::Matcher#candidates`(반대 방향·금액 일치·30일 이내) 중 접근 계정의 것만. `counterpart`도 접근 계정일 때만. | [transfer-matching](./transfer-matching.md) R-07~R-12·R-23·R-19 | `not_found` |
| R-95 | `match_transfer` (쓰기, dry run 지원) | `transaction_id*`, `counterpart_transaction_id` 또는 `target_account_id`(정확히 하나), `dry_run` | 두 거래 모두(또는 거래 + 대상 계정) 쓰기 계정. 이미 이체이면 거부(같은 쌍이 확정이면 `already_matched:true`로 성공, 같은 쌍이 pending이면 `pending_match`로 `review_transfer`의 confirm을 안내, 다른 짝이 pending이면 먼저 reject하라는 `already_linked`). `target_account_id`이면 그 계정에 반대 거래를 새로 만든다. dry run이면 변경 없이 설명. 서버 확인 없음. | 실제: `{success:true, created_counterpart, transfer:{transfer_id, status, outflow, inflow}}`, dry run: `{success:true, dry_run:true, transaction, counterpart?, creates_counterpart_in?:{account_id, account, name}, outflow_kind}` | [transfer-matching](./transfer-matching.md) R-03·R-23·R-24·R-26 | `invalid_arguments`, `not_found`, `account_not_found`, `pending_match`, `already_linked`(+`transfer`), `Transfer::Matcher::Error`의 코드(`e.code`) |
| R-96 | `review_transfer` (쓰기) | `transfer_id*`, `action*`(`confirm`·`reject`) | 두 다리 모두 쓰기 계정, `pending` 이체만. 행을 잠그고 다시 `pending`인지 확인한 뒤 처리. `reject`는 두 거래를 풀고 같은 짝의 자동 제안을 막는 거절 기록을 남긴다. | `{success:true, action:"confirmed", transfer:{transfer_id, outflow, inflow, status}}` 또는 `{success:true, action:"rejected", transfer:{transfer_id, outflow, inflow}}` | [transfer-matching](./transfer-matching.md) R-18·R-19·R-26·R-30 | `invalid_arguments`, `not_found`, `not_pending`(다른 요청이 먼저 처리한 경우 포함) |
| R-97 | `unmatch_transfer` (쓰기, dry run 지원, 파괴적) | `transaction_id` 또는 `transfer_id`(정확히 하나), `reject`(기본 true), `dry_run` | 두 계정 모두 쓰기. 확정·pending 모두 가능. 행을 잠그고 `reject`이면 `reject!`(해제 + 거절 기록), 아니면 이체 삭제. 수수료 거래는 이체와 함께 삭제되고 목록이 반환에 든다. 수수료가 있으면 계정 sync를 큐에 넣는다. | `{success:true, unmatched:true, rejected, transfer:{id, name, status, outflow:{..., kind_after}, inflow:{..., kind_after}, deleted_fee_transactions[]}, message, warning?}`. dry run은 `{success:true, dry_run:true, reject, transfer, message}`. | [transfer-matching](./transfer-matching.md) R-18·R-19·R-30·R-31, [transactions](./transactions.md) R-20 | `invalid_arguments`, `not_found` |
| R-98 | `update_transfer` (쓰기, dry run 지원) | `transaction_id` 또는 `transfer_id`(정확히 하나), `investment_contribution*`(true·false, 문자열 `true·t·1`·`false·f·0`·숫자 0·1도 허용), `dry_run` | 두 계정 모두 쓰기. 확정된 현금 → 투자·암호화폐 이체만 전환 가능. | `{success:true, transfer:{id, name, status, investment_contribution, outflow:{id, account, kind, category}, inflow:{id, account}}, message}`, dry run은 `dry_run:true`와 같은 모양 | [transfer-matching](./transfer-matching.md) R-29 | `invalid_arguments`, `not_found`, `not_switchable` |

**규칙 도구** (정의·조건·동작의 의미는 [transaction-classification](./transaction-classification.md) R-07·R-08·R-20·R-28~R-37, 허용 값·검증은 `RuleSupport`)

| R-ID | 도구 | 입력 | 범위·권한·확인 | 성공 반환 | 도메인 링크 | 실패 |
|---|---|---|---|---|---|---|
| R-99 | `get_rule_options` (읽기) | 없음 | 가족 범위 | `{success:true, conditions:[{condition_type, label, value_type, operators:[{value, label}], values}...] + 복합 조건 `compound`(연산자 `and`·`or`, 한 단계), actions:[{action_type, label, value_type, values}...]}`. AI 호출 동작(`auto_categorize`, `auto_detect_merchants`)과 `split_transaction`은 목록에서 뺀다. | R-07·R-08·R-20 | 없음 |
| R-100 | `get_rules` (읽기) | `rule_id`, `active`, `search`(이름·조건 값·동작 값·규칙이 설정하는 카테고리 이름), `page`, `page_size`(50) | 가족 범위 | `rule_id`면 `{success:true, rule:{...serialize, match_count}}`, 아니면 `{success:true, rules:[serialize...], total_results, ...}` 이름순(이름 없는 규칙은 뒤). `serialize`는 id, name, active, effective_date, 조건·동작(id를 이름으로 풀어 같이), updated_at, 마지막 실행 | R-28·R-31 | `not_found` |
| R-101 | `preview_rule` (읽기) | `rule_id` 또는 정의(`conditions[]`, `actions[]`, `effective_date`), `sample_size`(0~25, 기본 10) | 가족 범위. 둘 다 주거나 둘 다 안 주면 거부. 미저장 정의는 `active:false`로 만들어 검증만 한다. 샘플은 사용자가 볼 수 있는 계정의 최근 매칭 거래만, `match_count`는 가족 전체 기준. | `{success:true, rule, preview:{match_count, visible_match_count, sample:[{id, date, account, name, amount, currency, category, merchant, excluded}], actions, preview_token?}}`. `preview_token`은 저장된 규칙이고 `match_count > 0`이면 샘플이 있을 때(또는 매칭이 0건일 때)만 발급한다. 서명된 값이고 규칙 id·사용자 id·정의 digest·매칭 수를 담고 30분 뒤 만료된다. | R-07·R-08·R-36 | `invalid_arguments`, `not_found`, `invalid_rule`(+`problems[]`), `regex_timeout` |
| R-102 | `create_rule` (쓰기) | `conditions*[]`, `actions*[]`, `name`, `effective_date`, `sample_size` | 가족 범위. 규칙은 항상 `active: false`로 저장되어 어떤 거래도 바꾸지 않는다. | `{success:true, rule, preview:{...R-101과 같음}, message}` | R-36 | `invalid_arguments`, `invalid_rule`(+`problems[]`), `regex_timeout`(규칙은 이미 저장됨) |
| R-103 | `update_rule` (쓰기) | `rule_id*`, `name`(빈 문자열 = 지움), `conditions[]`/`actions[]`(통째로 교체), `effective_date`(빈 문자열 = 지움), `active`(`false`만 허용), `sample_size` | 가족 범위. 정의를 바꾸면 규칙은 자동으로 `active:false`가 된다(다시 활성화하려면 `apply_rule`). AI 동작이 든 규칙의 정의는 못 바꾼다. 이름만 바꾸면 활성 상태 유지. | `{success:true, rule, preview, message}` | R-36 | `not_found`, `cannot_activate`, `no_changes`, `ai_action`, `invalid_rule`, `regex_timeout` |
| R-104 | `apply_rule` (쓰기, 파괴적) | `rule_id*`, `preview_token*`, `override_locked`(기본 false) | 가족 범위. AI 동작이 든 규칙 거부. 토큰이 서명 검증·만료·규칙 id·사용자 id 모두 맞아야 한다. 규칙 행을 잠그고 현재 정의 digest와 매칭 수가 토큰 값과 같을 때만 `active: true`로 바꾼다. 이메일 동작이 있으면 알림 기준선이 시간 초과였을 때 거부. 활성화한 뒤 `apply_later`로 백그라운드 적용(`override_locked`가 true면 사용자가 손으로 정한 값도 덮어씀)한다. 이후 동기화 때도 계속 실행된다(되돌림은 `update_rule active:false`로 이후 실행만 막는다). | `{success:true, rule, applied_to:<매칭 수>, override_locked, message}` | [transaction-classification](./transaction-classification.md) R-21·R-28·R-37 | `not_found`, `ai_action`, `preview_required`(토큰 없음·위조·만료·다른 규칙·다른 사용자), `preview_stale`(+`rule`, `preview`: 정의나 매칭 수가 달라짐, 아무것도 적용하지 않음), `baseline_timed_out`, `regex_timeout` |

**preview 도구** (`preview_features_enabled?`인 사용자에게만, R-60)

| R-ID | 도구 | 입력 | 범위·권한·확인 | 성공 반환 | 도메인 링크 | 실패 |
|---|---|---|---|---|---|---|
| R-105 | `upload_account_statement` (쓰기) | `filename*`(허용 확장자 `AccountStatement::ACCEPTED_FILE_EXTENSIONS`), `content_base64*`(URL-safe도 허용, 패딩 보정), `account_id` | 역할이 admin 또는 member여야 한다(`statement_manager?`). `account_id`는 쓰기 계정. 크기 `AccountStatement::MAX_FILE_SIZE` 이하. 같은 내용(SHA-256)은 중복으로 처리한다. | `{success:true, duplicate:false, statement:{id, filename, content_sha256, content_type, byte_size, period_start_on, period_end_on, currency, opening_balance, closing_balance, review_status, account, suggested_account, match_confidence, institution_name_hint, account_last4_hint, uploaded_at}, message}`. 중복이면 `duplicate:true`와 기존 명세서(보는 권한이 없으면 `content_sha256`만). | [imports](./imports.md)(`AccountStatement`) | `forbidden`, `filename_required`, `unsupported_file_type`(+`accepted_extensions`), `invalid_content`, `empty_file`, `file_too_large`, `account_not_found`, `invalid_file`, `validation_failed`, `upload_failed` |
| R-106 | `list_account_statements` (읽기) | `account_id`, `review_status`(`unmatched`·`linked`·`rejected`), `content_sha256`, `overlapping_from`, `overlapping_until`, `limit`(기본 25, 최대 100) | `statement_manager?`. 계정 없는 명세서 + 접근 계정에 연결된 명세서 | `{success:true, returned, has_more, statements:[R-105의 statement]}`. | [imports](./imports.md)(`AccountStatement`) | `forbidden`, `invalid_account_id`, `invalid_review_status`, `invalid_date` |
| R-107 | `get_account_statement` (읽기) | `statement_id*` | `statement_manager?`, 그 명세서를 `viewable_by?(user)` | `{success:true, statement:{...R-105의 필드, reconciliation_status, reconciliation_checks:[{check, statement_amount, ledger_amount, difference, status}], reconciliation_note?}}` | [imports](./imports.md)(`AccountStatement`), [account-balances](./account-balances.md) R-16 | `forbidden`, `not_found` |
| R-108 | `get_statement_coverage` (읽기) | `account_id*`, `year` | `statement_manager?`, 접근 계정 | `{success:true, account:{id, name, currency}, year, available_years, summary, months:[{month("YYYY-MM"), status, reconciliation_status?, statement_ids, unconfirmed_statement_ids, ...}]}` | [imports](./imports.md)(`AccountStatement`) | `forbidden`, `invalid_account_id`, `account_not_found` |
| R-109 | `record_valuation` (쓰기) | `account_id*`, `date*`, `amount*`, `source*`(출처 인용 문법 `["estimated: "] 인용 [" (grade: A|B|C)"]`) | 쓰기 계정. 출처를 가장 먼저 검증한다(없거나 문법에 안 맞으면 거부). 같은 날짜의 평가가 있으면 덮어쓴다(`replaced_existing`). 계정 행을 잠그고 `create_reconciliation`으로 만든 뒤 entry 메모에 출처를 덧붙인다(이미 같은 줄이 있으면 중복 추가 안 함). 서버 확인 없음. | `{success:true, entry_id, account:{id, name, currency}, date, amount, amount_formatted, replaced_existing, provenance, message}` | [account-balances](./account-balances.md) R-12·R-16·R-17, [provider-import-adapter](./provider-import-adapter.md) R-71(출처 문법) | `invalid_source_citation`, `invalid_date`, `invalid_amount`, `invalid_account_id`, `account_not_found`, `valuation_failed`, `validation_failed` |
| R-110 | `get_valuations` (읽기) | `account_id`, `start_date`, `end_date`, `page` | 접근 계정 | `{valuations:[{entry_id, account:{id, name, currency}, date, amount, amount_formatted, kind, notes}], total_results, page, page_size(50), total_pages}` 최신 순 | [account-balances](./account-balances.md) R-12 | (c)형 `invalid_account_id`, `invalid_date`(형식·시작>끝) |
| R-111 | `get_insights` (읽기) | `insight_type`(`Insight::TYPES`), `include_acknowledged`, `limit`(기본 10, 최대 50) | 가족 범위의 `visible` 인사이트(기본), `include_acknowledged`면 만료되지 않은 것 중 모든 활성 구성원이 접근 가능한 계정에 관한 것(`about_shared_accounts`) | `{insights:[{id, type, title, body, priority, status, period_start, period_end, generated_at, metadata}]}` | [reports-insights](./reports-insights.md) R-45~R-48 | 없음 |
| R-112 | `get_bills` (읽기) | `status`(`active`·`suggested`·`paused`·`ended`·`all`, 기본 active), `payment_state`(`overdue`·`due`·`upcoming`·`partial`·`paid`), `bill_type`, `search`, `due_within_days`(1~365) | 접근 가능한 반복 거래. 가족의 반복 거래 꺼짐이면 즉시 R-63 (b)형 `{error:"Bills & recurring transactions are disabled for this family", hint:"Do not retry..."}`. | `{as_of_date, total_results, truncated(100건 초과), family_currency, bills:[{id, name, bill_type, status, amount, currency, frequency, next_due_date, autopay, detected_automatically, category, account, destination_account, monthly_equivalent, payment_url, current_occurrence:{due_on, effective_due_on, state, expected, paid, remaining, partially_paid}}], totals:{active_count, overdue_count, active_monthly_equivalent_by_currency}, hint?}`. 결과가 없고 필터가 `status`뿐이면 다른 상태의 개수를 안내하는 `hint`가 붙는다. | [recurring-transactions](./recurring-transactions.md) R-31·R-50~R-52·R-64 | (b)형: 모르는 `status`·`bill_type`·`payment_state` 값, 범위 밖 `due_within_days` |
| R-113 | `get_bill_details` (읽기, `strict: true`) | `bill_id*` | 접근 가능한 반복 거래, 꺼짐 검사 | `{bill:{...R-112의 필드 + amount_strategy, weekend_adjust, end_mode, end_on, end_after_count, anchor_date, notes, notify_days_before, overdue_grace_days, trial_ends_on, renews_on, cancelled_on, schedule_pinned, expected_amount_min·max·avg}, analytics?, open_occurrences[], history[최근 12건 + payments], history_window, upcoming_due_dates[3], price_changes[24개월], price_change_window}` | [recurring-transactions](./recurring-transactions.md) R-31·R-35·R-46·R-47 | (b)형(잘못된 id), `RecordNotFound`는 R-62 변환 |
| R-114 | `get_paycheck_plan` (읽기) | `periods_limit`(1~6, 기본 3) | `PaycheckPlanner.new(family, user:)`, 꺼짐 검사 | `{as_of_date, family_currency, unconvertible_count, periods:[{starts_on, ends_on, bridge, income, income_sources, due_total, reserved_total, safe_after_bills, cash_on_hand?, short, shortfall?, bills_due[], reserved_for_later[], largest_obligation?}], unconfirmed_excluded?:{count, note}}` | [recurring-transactions](./recurring-transactions.md) R-57~R-60 | (b)형: 선언된 소득 일정이 없으면 `No declared income schedule` |
| R-115 | `get_bill_audit` (읽기) | `lookback_months`(1~24, 기본 12) | 접근 가능한 반복 거래, 꺼짐 검사 | `{as_of_date, possible_duplicates, price_changes, upcoming_trials, upcoming_renewals, long_overdue, dormant, awaiting_confirmation, undeclared_candidates}`, 각 섹션은 `{items(최대 20), truncated, count}`. 갱신·체험 만료 창은 30일. | [recurring-transactions](./recurring-transactions.md) R-20·R-46~R-48 | (b)형: 범위 밖 `lookback_months` |
| R-116 | `create_bill` (쓰기) | `name*`, `amount*`(≥0.01), `first_due_on*`, `frequency`(`FrequencyPreset::PRESETS`, 기본 `monthly`), `is_income`, `bill_type`(`bill`·`subscription`·`installment`, 소득이면 무시), `account_name`, `category_name`, `autopay`, `payment_url`, `notes` | 꺼짐 검사. 계정은 `Account.writable_by(user)`에서 이름이 정확히 하나일 때만(없거나 중복이면 거부), 카테고리는 가족 카테고리의 정확한 이름. description에 "Confirm the details with the user before calling this"(R-66). 불리언 입력은 `true·t·1`과 `false·f·0` 계열만 받는다. | `{created:true, bill:{R-112의 series 필드}, upcoming_due_dates[3]}` | [recurring-transactions](./recurring-transactions.md) R-05·R-11·R-61 | (b)형: 불리언 오류, 계정 없음·중복, 카테고리 없음, 모르는 frequency, 모델 검증 오류 문장(`hint: "Fix the named fields and retry once."`) |
| R-117 | `update_bill` (쓰기) | `bill_id*`, `name`, `amount`(앞으로만 적용, 부호는 소득이면 음수로 저장), `account_name`, `category_name`(`"Uncategorized"` = 지움), `bill_type`, `status`(`active`·`paused`), `frequency`+`due_day_of_month`·`weekday`(0=일)·`month_of_year`, `autopay`, `payment_url`, `notes`, `renews_on`, `trial_ends_on` | 꺼짐 검사. 연결 계정이 있으면 그 계정이 쓰기 계정이어야 한다(읽기 공유면 "shared with you read-only"로 거부). 계정 지정은 R-116과 같은 규칙. `frequency` 없이 `due_day_of_month`·`weekday`·`month_of_year`만 주면 거부. 일정을 바꾸면 일정을 고정(`pin_schedule`)한다. description에 "Confirm the change with the user before calling this". `status: "paused"`는 `inactive`로 저장되고 조회 때 다시 `paused`로 보인다. | `{updated:true, changed_fields[], bill}` | [recurring-transactions](./recurring-transactions.md) R-36·R-62·R-64 | (b)형: 권한, 변경할 필드 없음(`No recognized fields to change`), 날짜·금액·유형·상태·frequency 오류, 모델 검증 오류 |
| R-118 | `record_bill_payment` (쓰기) | `bill_id*`, `occurrence_due_on`, `amount`(생략 = 전액 결제), `paid_on`(기본 오늘) | 꺼짐 검사, 쓰기 가능한 청구서(R-117과 같은 계정 검사). 열린 회차를 `occurrence_due_on`으로 찾고, 없으면 현재 회차(전액 결제인데 아직 낼 때가 아니면 거부). 부분 결제는 남은 금액을 넘으면 거부. 전액이면 `mark_paid!`, 부분이면 `allocate!(source: "user_created", cap_at_remaining: true)`. description에 "Confirm with the user before recording anything". 취소 도구는 없다. | `{recorded:true, bill, occurrence:{due_on, effective_due_on, state, expected, paid, remaining, partially_paid, status}}` | [recurring-transactions](./recurring-transactions.md) R-42~R-44 | (b)형: 권한, 열린 회차 없음(`Open due dates: ...` 안내), 날짜·금액 오류, 초과 결제(`OverAllocationError`) |

- 불변식: 도구 호출은 모델의 한 응답 안에서 순서대로 실행되고, 어떤 도구도 모델에게 예외를 던지지 않는다(R-62). `AssistantMessage.content`에는 한 턴의 모든 라운드의 텍스트가 이어 붙는다(R-20). `status = failed`·`pending` 메시지는 모델 history에 들어가지 않는다(R-11). 규칙 활성화는 `apply_rule` 한 경로뿐이고 거기서만 `preview_token`이 필요하다(R-102~R-104).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-65, R-81, R-91, R-93 | `accessible_accounts.visible`, `writable_by`, `annotatable_by`, `AccountShare`의 정의와 가족 문서 검색의 구성원별 범위는 권한 스펙(승인 밖) 소관이다. 이 문서는 [transactions](./transactions.md) R-68(소유자·`full_control`=쓰기, `read_write`=annotate, `read_only`=읽기)을 가정으로 썼다. | 다중 사용자 가족에서 도구 하나마다 어느 계정 집합을 입력으로 받을지, `create_goal`·`import_bank_statement`의 필터 없음과 문서 검색의 가족 전체 공개를 원본대로 둘지 | 권한(행 18) 스펙이 승인되면 그 규칙으로 R-65를 다시 쓴다. |
| U-02 | R-08 | API v1 `POST /chats/:chat_id/messages/retry`의 실제 응답(후보: `RecordInvalid`가 처리되지 않은 500이 가장 유력하고, 통과해도 job이 `NoMethodError`로 실패한다. 422나 202 정상은 코드상 근거가 없다). 실행해 보지 않았다. | API 재시도 기능을 재구현할지, 어떤 상태 코드를 줄지 | 요청 스펙 테스트나 실행 로그. `Message` 검증과 `AssistantMessage#request_response` 부재를 근거로 본다. |
| U-03 | R-26, R-70, R-90, T-18~T-21 | 사용자 locale `ko`가 `LanguagesHelper::SUPPORTED_LOCALES`에 없고 `config/locales/models/category/ko.yml`도 없다. 그래서 `Category.all_uncategorized_names`와 `Category.uncategorized_name`이 한국어 "미분류"를 포함하지 않는다. 시스템 프롬프트에는 응답 언어 지시가 없다. 한국어 사용자가 이 설치에서 어떤 locale로 쓰는지, 모델이 한국어로 답하는지는 코드로 정해지지 않는다. | `"Uncategorized"` 별칭(R-70, R-90)과 가족 카테고리 이름(한글)의 매칭, 응답 언어 | 실제 한국어 locale 설정과 모델 응답을 실행해 본다. 한국어 별칭을 추가할지는 적용 메모에서 정한다. |
| U-04 | R-36 | OpenAI Responses 경로가 후속 요청마다 사용자 메시지를 `input`에 다시 싣는데, 서버가 `previous_response_id` 체인에 이 메시지를 중복으로 기록하는지, `previous_response_id`의 유효 기간(TTL)이 얼마인지는 외부 서버 동작이다. 코드의 오류 문구는 만료를 원인 후보로 든다(`build_stream_error_message`). | 재구현이 같은 요청 모양을 따를지, 체인 만료 시 복구(체인을 끊고 history를 다시 보내는 것)가 필요한지 | OpenAI 공식 문서와 실제 호출 로그. |
| U-05 | R-14, R-32 | provider별 오류 문구(429, 5xx, 인증, 컨텍스트 초과)가 R-14의 패턴에 걸리는지는 서버가 보내는 문구에 달려 있고 확인하지 않았다. | 사용자에게 보이는 오류 분류의 정확도 | 각 provider의 실제 오류 응답 문구. |
| U-06 | R-74 | `get_income_statement`가 필수 인자 없이 호출되거나 `start_date > end_date`일 때 `Period.custom`·`Date.parse`가 내는 예외 클래스와 그에 따른 반환(R-62의 어느 항목)을 확인하지 않았다. 코드상 `Date::Error`만 도구 안에서 rescue한다. | 모델에게 가는 오류 문구와 hint(재시도 유도 여부) | `Period` 검증과 `Date.parse(nil)` 실행. |

- 확인 한계: 모든 항목은 코드 정독과 `grep`으로 확인했고 앱을 실행하지 않았다. 원본 테스트는 열지 않았다. `ruby-openai`·Anthropic gem의 요청 직렬화·재시도·헤더는 읽지 않았다(R-36은 앱이 넘기는 인자까지). OpenAI·Anthropic 서버의 응답 형식·오류 문구와 외부 에이전트(OpenClaw 등)의 실제 동작은 확인하지 않았다(코드는 "클라이언트가 그렇게 가정했다"는 증거다). `Debuggable`(채팅 debug 모드), Langfuse·Instrumentation, `ChatReservation`·`BackgroundJobHealth`의 큐 동작, 같은 채팅에서 두 턴이 동시에 돌 때의 경합은 읽지 않았다. 환경이 `config/llm_pricing.yml`의 가격표로 비용을 추정하는 규칙(R-25)은 `LlmUsage.calculate_cost`까지만 읽었다.

### 1.5 필수 코드 참조

라이선스: 인용 허용 여부는 [overview](../overview.md) 1절을 따른다. 아래 줄 범위는 모두 기준 SHA의 파일이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `app/models/assistant.rb:4-8`, `:17-46`, `:48-56`, `:66-120` `REGISTRY`, `PREVIEW_FUNCTION_CLASSES`, `FAMILY_CONFIG_FUNCTION_CLASSES`, `function_classes`, `implementation_for` | 도구 registry 35개 목록과 노출 조건 | R-01, R-16, R-60 |
| C-02 | `app/models/assistant/builtin.rb:14-96` `respond_to`, `function_tool_caller`, `build_no_provider_error_message` | 이벤트 처리, 실패 정리, provider 없음 오류 문구 | R-15, R-20, R-23 |
| C-03 | `app/models/assistant/responder.rb:1-72` `respond`, `group_by_round` | 루프, 상한, 마지막 라운드의 도구 금지, 빈 응답 오류 | R-17, R-18, R-19, R-21 |
| C-04 | `app/models/assistant/responder.rb:77-144` `request_response`, `get_llm_response`, `max_tool_call_iterations` | 공백 조각 보류, 요청 인자, 응답 실패 raise, 상한 해석 | R-17, R-21, R-37 |
| C-05 | `app/models/assistant/responder.rb:168-229` `complete_chat_messages`, `openai_messages_payload` | history 대상과 OpenAI 호환 메시지 모양 | R-11, R-30 |
| C-06 | `app/models/assistant/function_tool_caller.rb:11-77` | 도구 실행과 오류 변환 객체의 정확한 문구 | R-62 |
| C-07 | `app/models/assistant/configurable.rb:12-53` `STATIC_INSTRUCTIONS` | 정적 지시문 전문(구현자는 이 텍스트를 그대로 가져갈 수 있다) | R-26 |
| C-08 | `app/models/assistant/configurable.rb:56-71`, `:74-103`, `:105-182` `config_for`, `intro_instructions`, `session_context`, `accounts_context`, `categories_context` | 구성, intro 지시문, 세션 컨텍스트 | R-16, R-27, R-28 |
| C-09 | `app/models/assistant/token_budget.rb:1-26`, `app/models/assistant/token_estimator.rb:1-19`, `app/models/assistant/history_trimmer.rb:1-55` | 컨텍스트 창, 추정, 묶음 단위 자르기 알고리즘 | R-29, R-31 |
| C-10 | `app/models/provider/openai.rb:13-24`, `:58-80`, `:129-218` `supports_model?`, `supports_responses_endpoint?`, `max_history_tokens` | 모델 허용 prefix, 예산 계산, 타임아웃 | R-15, R-22, R-31, R-32, R-35 |
| C-11 | `app/models/provider/openai.rb:433-480`, `:527-639` `chat_response`, `native_chat_response` | Responses 경로 요청 인자와 스트림 처리 | R-22, R-36 |
| C-12 | `app/models/provider/openai.rb:642-813` `generic_chat_response`, `build_generic_messages`, `build_generic_tools` | Chat Completions 경로 요청과 history·tool 메시지 구성 | R-30, R-31, R-36 |
| C-13 | `app/models/provider/openai/chat_config.rb:7-44`, `app/models/provider/openai/chat_parser.rb:8-58`, `app/models/provider/openai/chat_stream_parser.rb:10-41`, `app/models/provider/openai/generic_chat_parser.rb:8-60` | 요청 `input`·`tools` 모양, 응답·스트림 이벤트 파싱 | R-22, R-36, R-37 |
| C-14 | `app/models/provider/anthropic.rb:77-85`, `:276-433`, `app/models/provider/anthropic/chat_config.rb:20-94`, `app/models/provider/anthropic/message_formatter.rb:17-139`, `app/models/provider/anthropic/chat_parser.rb:8-58` | Anthropic 요청·history·응답 파싱 | R-15, R-18, R-22, R-36, R-37 |
| C-15 | `app/models/provider/registry.rb:26-36`, `:82-109`, `app/models/provider.rb:32-75`, `app/models/assistant/provided.rb:4-16` | provider 탐색 순서와 구성, 오류 감싸기 | R-15, R-35, R-38 |
| C-16 | `app/models/chat.rb:4-28`, `:40-72`, `:75-142`, `:164-233`, `:264-287` | 오류 패턴, 시작·기본 모델·재시도·응답 요청, watchdog, 오류 분류 | R-04~R-07, R-09, R-10, R-14 |
| C-17 | `app/models/message.rb:1-24`, `app/models/assistant_message.rb:16-41`, `app/models/user_message.rb:1-17`, `app/models/tool_call/function.rb:1-53` | 메시지 검증·상태, `append_text!` 경쟁 처리, tool call 직렬화 | R-11, R-12, R-13, R-24 |
| C-18 | `app/controllers/chats_controller.rb:1-81`, `app/controllers/messages_controller.rb:1-59`, `app/controllers/concerns/requires_ai_consent.rb:8-15`, `app/jobs/assistant_response_job.rb:1-10` | 웹 진입점과 가드, job | R-03, R-06, R-07, R-09, R-10 |
| C-19 | `app/controllers/api/v1/chats_controller.rb:1-89`, `app/controllers/api/v1/messages_controller.rb:1-60`, `app/controllers/api/v1/base_controller.rb:347-351` | API v1 진입점과 가드 | R-03, R-04, R-06, R-08 |
| C-20 | `app/models/family/ai_settings.rb:36-42`, `:89-91`, `app/models/user.rb:264-287`, `:925-949`, `app/models/family/ai_promptable.rb:13`, `:60-73`, `:90-110` | assistant 종류, AI 사용 가능 판정, guest 강제 설정, 프롬프트 override 제약 | R-01, R-02, R-16, R-26 |
| C-21 | `app/models/assistant/external.rb:1-128`, `app/models/assistant/external/client.rb:1-152`, `app/models/assistant/external/model_catalog.rb:15-75` | 외부 assistant 구성·요청·SSE 파싱·재시도·정리·agent 목록 | R-40~R-46 |
| C-22 | `app/models/ai/router.rb:7-33`, `app/models/ai/routes.rb:9-27`, `app/models/ai/consent.rb:3-12`, `app/models/ai/route.rb:6-38`, `app/models/ai/availability.rb:5-21`, `app/models/ai.rb:8-24` | feature 표와 router 규칙 | R-47, R-48 |
| C-23 | `app/models/ai/legacy_env_config.rb:34-53`, `:86-146`, `app/models/ai/config/model.rb:3-13` | route 목록·capability·벡터 백엔드 결정 규칙 | R-47, R-50 |
| C-24 | `app/models/vector_store/registry.rb:8-75`, `app/models/vector_store.rb:7-37`, `app/models/family/vector_searchable.rb:8-84` (이 파일의 줄 번호는 파일 시작 기준) | 어댑터 선택과 가족 store·문서 연산 | R-50, R-52, R-54 |
| C-25 | `app/models/vector_store/embeddable.rb:4-148` | 청킹·임베딩 알고리즘 | R-55 |
| C-26 | `app/models/vector_store/pgvector.rb:16-149`, `app/models/vector_store/openai.rb:19-85`, `app/models/vector_store/qdrant.rb:24-65`, `app/models/vector_store/base.rb:2-5`, `:45-48` | 어댑터별 연산과 지원 확장자, Qdrant 미구현 | R-51, R-55, R-56 |
| C-27 | `app/models/family_document.rb:1-25`, `app/controllers/imports_controller.rb:250-324`, `app/jobs/process_pdf_job.rb:68-82`, `app/models/import.rb:36` | 문서 업로드 진입과 제한 | R-53, R-54 |
| C-28 | `app/models/provider/openai.rb:851-919`, `app/models/provider/anthropic.rb:458-508`, `app/models/provider/openai/usage_cost.rb:2-39`, `app/models/llm_usage.rb:40-139` | 사용량 행 기록과 비용 추정 | R-25 |
| C-29 | `app/models/assistant/function.rb:12-146` | 도구 기본 계약(스키마 구성, 빈 enum 제거, 페이지 정규화) | R-61, R-64 |
| C-30 | `app/controllers/mcp_controller.rb:98-138` | `/mcp`가 같은 registry를 쓰는 지점과 오류 변환 | R-60, R-62 |
| C-40 | `app/models/assistant/function/get_transactions.rb:74-261` | `get_transactions` 스키마·반환 | R-70 |
| C-41 | `app/models/assistant/function/get_accounts.rb:44-94` | `get_accounts` | R-71 |
| C-42 | `app/models/assistant/function/get_holdings.rb:59-120` | `get_holdings` | R-72 |
| C-43 | `app/models/assistant/function/get_balance_sheet.rb:31-85` | `get_balance_sheet` | R-73 |
| C-44 | `app/models/assistant/function/get_income_statement.rb:43-113` | `get_income_statement` | R-74 |
| C-45 | `app/models/assistant/function/get_budget.rb:46-83`, `app/models/assistant/function/month_resolvable.rb:4-28` | `get_budget`, 월 해석 | R-69, R-75 |
| C-46 | `app/models/assistant/function/get_categories.rb:37-79` | `get_categories` | R-76 |
| C-47 | `app/models/assistant/function/get_tags.rb:36-68` | `get_tags` | R-77 |
| C-48 | `app/models/assistant/function/get_merchants.rb:27-77` | `get_merchants` | R-78 |
| C-49 | `app/models/assistant/function/get_recurring_transactions.rb:29-73` | `get_recurring_transactions` | R-79 |
| C-50 | `app/models/assistant/function/get_uncategorized_transactions.rb:62-112` | `get_uncategorized_transactions` | R-80 |
| C-51 | `app/models/assistant/function/search_family_files.rb:38-157` | `search_family_files` | R-81 |
| C-52 | `app/models/assistant/function/create_transaction.rb:69-224` | `create_transaction` | R-82 |
| C-53 | `app/models/assistant/function/update_transaction.rb:24-96` | `update_transaction` | R-83 |
| C-54 | `app/models/assistant/function/delete_transaction.rb:51-117` | `delete_transaction` | R-84 |
| C-55 | `app/models/assistant/function/create_tag.rb:22-50` | `create_tag` | R-85 |
| C-56 | `app/models/assistant/function/update_tag.rb:21-57` | `update_tag` | R-86 |
| C-57 | `app/models/assistant/function/create_category.rb:25-75` | `create_category` | R-87 |
| C-58 | `app/models/assistant/function/update_category.rb:26-83` | `update_category` | R-88 |
| C-59 | `app/models/assistant/function/delete_category.rb:25-60` | `delete_category` | R-89 |
| C-60 | `app/models/assistant/function/update_budget.rb:49-149` | `update_budget` | R-90 |
| C-61 | `app/models/assistant/function/create_goal.rb:39-162` | `create_goal` | R-91 |
| C-62 | `app/models/assistant/function/set_opening_balance.rb:39-103` | `set_opening_balance` | R-92 |
| C-63 | `app/models/assistant/function/import_bank_statement.rb:41-167` | `import_bank_statement` | R-93 |
| C-64 | `app/models/assistant/function/get_transfer_match_candidates.rb:38-77`, `app/models/assistant/function/transfer_match_support.rb:9-68` | `get_transfer_match_candidates`와 공통 직렬화 | R-94 |
| C-65 | `app/models/assistant/function/match_transfer.rb:47-122` | `match_transfer` | R-95 |
| C-66 | `app/models/assistant/function/review_transfer.rb:33-85` | `review_transfer` | R-96 |
| C-67 | `app/models/assistant/function/unmatch_transfer.rb:47-122`, `app/models/assistant/function/transfer_support.rb:5-44` | `unmatch_transfer`와 이체 조회 공통 | R-97 |
| C-68 | `app/models/assistant/function/update_transfer.rb:42-98` | `update_transfer` | R-98 |
| C-69 | `app/models/assistant/function/get_rule_options.rb:32-44`, `app/models/assistant/function/rule_support.rb:20-33`, `:100-160`, `:239-290` | `get_rule_options`, 허용 값·정의 검증 | R-99 |
| C-70 | `app/models/assistant/function/get_rules.rb:41-97` | `get_rules` | R-100 |
| C-71 | `app/models/assistant/function/preview_rule.rb:38-74`, `app/models/assistant/function/rule_support.rb:385-448` | `preview_rule`, 미리보기와 `preview_token` | R-101 |
| C-72 | `app/models/assistant/function/create_rule.rb:31-66` | `create_rule` | R-102 |
| C-73 | `app/models/assistant/function/update_rule.rb:35-100` | `update_rule` | R-103 |
| C-74 | `app/models/assistant/function/apply_rule.rb:40-118`, `app/models/assistant/function/rule_support.rb:410-450` | `apply_rule`, 토큰 검증 | R-104 |
| C-75 | `app/models/assistant/function/upload_account_statement.rb:44-127`, `app/models/assistant/function/statement_vault_support.rb:8-67` | `upload_account_statement`와 공통 | R-105 |
| C-76 | `app/models/assistant/function/list_account_statements.rb:50-146` | `list_account_statements` | R-106 |
| C-77 | `app/models/assistant/function/get_account_statement.rb:62-96` | `get_account_statement` | R-107 |
| C-78 | `app/models/assistant/function/get_statement_coverage.rb:52-92` | `get_statement_coverage` | R-108 |
| C-79 | `app/models/assistant/function/record_valuation.rb:59-145` | `record_valuation` | R-109 |
| C-80 | `app/models/assistant/function/get_valuations.rb:25-98` | `get_valuations` | R-110 |
| C-81 | `app/models/assistant/function/get_insights.rb:28-79` | `get_insights` | R-111 |
| C-82 | `app/models/assistant/function/get_bills.rb:38-122`, `app/models/assistant/function/bills_support.rb:11-168` | `get_bills`, bills 공통 | R-112 |
| C-83 | `app/models/assistant/function/get_bill_details.rb:33-65` | `get_bill_details` | R-113 |
| C-84 | `app/models/assistant/function/get_paycheck_plan.rb:36-68` | `get_paycheck_plan` | R-114 |
| C-85 | `app/models/assistant/function/get_bill_audit.rb:33-76` | `get_bill_audit` | R-115 |
| C-86 | `app/models/assistant/function/create_bill.rb:32-111` | `create_bill` | R-116 |
| C-87 | `app/models/assistant/function/update_bill.rb:38-92` | `update_bill` | R-117 |
| C-88 | `app/models/assistant/function/record_bill_payment.rb:32-88` | `record_bill_payment` | R-118 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 사례의 모델 응답은 가정한 입력이고, 서버 규칙의 결과만 기대값이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-17, R-18 | `ASSISTANT_MAX_TOOL_CALL_ITERATIONS` 미설정. 모델이 1~8번째 응답 모두 `get_transactions` 호출을 요구하고, 8번째 라운드 도구 실행 뒤 보낸 후속 요청(`tool_choice: none`)에는 텍스트로 답한다. | 도구를 8번 실행한다. 8번째 후속 요청만 `tool_choice: none`이고 앞의 7번은 아니다. 턴은 `complete`로 끝나고 `chats.latest_assistant_response_id`가 마지막 응답 id가 된다. |
| T-02 | R-17, R-23 | T-01과 같은 설정에서 모델이 `tool_choice: none` 요청에도 9번째로 도구 호출을 요구한다. 앞 라운드에서 이미 텍스트가 일부 나왔다. | 9번째 반복에서 `ToolCallLimitError`("Assistant exceeded the tool-call limit of 8 for one response")가 난다. 이미 나온 텍스트가 있는 메시지는 `status = failed`가 되고, `chats.error.message`는 기본 오류 문구(원문에 `5xx`·`timeout`이 없음), `type`은 `Assistant::Responder::ToolCallLimitError`다. 이미 실행한 도구의 부작용은 남는다. |
| T-03 | R-17 | `ASSISTANT_MAX_TOOL_CALL_ITERATIONS`가 `"2"`, `"0"`, `"abc"`, `"-3"`일 때 각각의 상한. | 2, 8, 8, 8. |
| T-04 | R-15 | `Setting.llm_provider = "openai"`, OpenAI가 공식 endpoint(`OPENAI_URI_BASE` 없음)와 키로, Anthropic도 키로 설정. 메시지의 `ai_model`이 `"claude-sonnet-4-6"`이다. 이어서 OpenAI를 `OPENAI_URI_BASE=http://ollama:11434/v1`, `OPENAI_MODEL=qwen3`로 바꾸고 같은 메시지를 처리한다. | 처음: OpenAI의 `supports_model?`(prefix 불일치)가 false라 Anthropic이 선택된다. 바꾼 뒤: OpenAI가 커스텀 endpoint라 어떤 모델명이든 지원하므로 OpenAI가 선택된다. 둘 다 없으면 오류 `No LLM provider configured that supports model 'claude-sonnet-4-6'`로 시작하는 문장이고 메시지는 R-23대로 정리된다. |
| T-05 | R-31 | `LLM_MAX_HISTORY_TOKENS=300`. history가 user 메시지 5개이고 각각 JSON 길이가 400자(추정 `ceil(400/4×1.25)=125` 토큰), 마지막 것이 현재 메시지다. | 최신부터 125, 250까지 누적(≤300)이라 최신 2개를 남기고, 세 번째에서 375 > 300이라 멈춰 앞의 3개는 버린다. |
| T-06 | R-31 | T-05에서 `LLM_MAX_HISTORY_TOKENS`를 비우고 컨텍스트 창 2048, 응답 예산 512, 지시문 3200자(추정 1000토큰). 또 history의 가장 최신 묶음(tool call + 결과 3개)이 추정 900토큰이다. | 예산은 `max(2048 − 512 − 1000, 256) = 536`이다. 가장 최신 묶음은 900 > 536이어도 남고, 그보다 오래된 묶음은 모두 버린다. |
| T-07 | R-31 | `TokenEstimator.estimate("가"*400)`와 `estimate("a"*400)`, `estimate({role:"user", content:"안녕"})`. | 둘 다 125. 해시는 `to_json` 길이(`{"role":"user","content":"안녕"}` = 30자, 글자 수 기준)로 `ceil(30/4×1.25)=10`. 언어·바이트 수와 무관하게 글자 수로 센다. |
| T-08 | R-27 | KRW 가족, `date_format "%Y-%m-%d"`, 접근 계정 4개(Depository 3, CreditCard 1), 컨텍스트 창 2048(작은 창). 카테고리 12개. | `Today's date: <서버 날짜>`, `Date format: %Y-%m-%d`, `Preferred currency: KRW (symbol ₩, precision 0, format %u%n, separator ".", delimiter ",")`, 계정은 `4 accounts: 3 Depository, 1 CreditCard. Call get_accounts for the list.`, 카테고리도 `12 categories. Call get_categories for the list.`. 창을 8192로 올리면 계정은 4줄(`- 이름: Depository, asset, ₩1,234,000`), 카테고리는 이름들 + `Uncategorized`로 바뀐다. |
| T-09 | R-62 | 모델이 `{name:"get_budget", arguments:"{\"month\": \"2026-13\"}"}`, `{name:"nope", arguments:""}`, `{name:"get_tags", arguments:"{bad"}`, `{name:"update_category", arguments:"{\"id\":\"11111111-1111-1111-1111-111111111111\"}"}`(가족에 없는 id)를 요청한다. | 순서대로 (a) `get_budget failed unexpectedly`(`Assistant::Error`가 rescue 목록에 없어서) + `Do not retry with the same arguments...`, (b) `Unknown tool: nope`, (c) `Arguments were not valid JSON`, (d) `update_category`는 `valid_uuid?`를 통과해 `find_by`가 nil이라 도구가 직접 `{success:false, error:"not_found", message:"Category with id '...' not found."}`를 낸다. `RecordNotFound` 변환은 `find`/`find_by!`를 쓰는 도구(예: `get_bill_details`의 `find`)에서 `No such record, or it is not one you have access to`로 나온다. |
| T-10 | R-101~R-104 | 규칙 `create_rule({conditions:[{condition_type:"transaction_name", operator:"like", value:"스타벅스"}], actions:[{action_type:"set_transaction_category", value:"<식비 카테고리 id>"}]})`. 현재 매칭 48건. 이어서 (a) `apply_rule({rule_id, preview_token:"x"})`, (b) 올바른 토큰으로 `apply_rule`, (c) 그 사이 사용자가 스타벅스 거래 3건을 추가한 뒤 이전 토큰으로 `apply_rule`. | 생성: 규칙은 `active:false`, `preview.match_count 48`, 토큰 발급. (a) `preview_required`. (b) 규칙 `active:true`, `applied_to:48`, 백그라운드 적용 큐 등록. (c) 정의 digest는 같지만 매칭 수가 51이라 `preview_stale`(`rule`, `preview` 포함, 새 토큰), 아무것도 적용되지 않고 규칙은 `active:false` 그대로. 30분 뒤에는 `preview_required`. |
| T-11 | R-89 | `delete_category({id:"<식비>", replacement_id:"<외식>"})`와 `delete_category({id:"<식비>", replacement_id:""})`와 `delete_category({id:"<식비>", replacement_id:"<식비>"})`. | 첫째: 식비의 거래가 외식으로 옮겨지고 식비 삭제, `{success:true, id, replacement_id:"<외식 id>", message:"Category '식비' deleted. Its transactions were moved to '외식'."}`. 둘째: 빈 문자열은 "생략"이 아니므로 가족 카테고리 id가 아니라 `replacement_not_found`. 셋째: `invalid_replacement`. 확인 절차는 서버에 없다. |
| T-12 | R-82 | 쓰기 계정에 `create_transaction({account_id, date:"2026-11-18", amount:2194.15, type:"expense", name:"로쉬", external_id:"row-7"})`을 두 번 호출한다. 이어서 `amount:50, type:"income"`, 그리고 `type` 없이 `amount:-30`. | 첫 호출: `created:true`, 저장 금액 `+2194.15`. 둘째(같은 계정·`source "mcp"`·`external_id`): `created:false`로 기존 거래를 돌려준다. income은 `-50`, 부호 없는 입력은 `-30` 그대로 저장(수입). |
| T-13 | R-70 | 가족에 "Uncategorized"라는 이름의 실제 카테고리가 없고 `get_transactions({categories:["Uncategorized"]})`. 다른 가족: 실제 카테고리 "Uncategorized"가 있을 때. | 첫째: 필터 값이 센티널 `"__uncategorized__"`로 바뀌어 카테고리 없는 거래를 찾는다. 둘째: 실제 이름 그대로 그 카테고리 거래를 찾는다. |
| T-14 | R-70, U-03 | 한국어 사용자 가족에 카테고리 "식비", "미분류"가 없고 `get_transactions({categories:["미분류"]})`. | 별칭 목록(`"Uncategorized"`와 현재 locale의 `Category.uncategorized_name`)에 "미분류"가 없으면(locale `ko`가 지원 목록에 없어 기본 locale 값 "Uncategorized"로 fallback한다, 추론) 이름 `"미분류"`로 필터한다. 그런 카테고리가 없으므로 결과는 0건이다(검색 필터의 이름 일치는 [transactions](./transactions.md) R-45). 모델이 `"Uncategorized"`를 보내야 미분류 거래를 얻는다. |
| T-15 | R-90, R-69 | 한국어 가족(KRW, `month_start_day` 1). `update_budget({month:"2026-11", budgeted_spending:3000000, categories:[{category:"식비", amount:500000},{category:"미분류", amount:100000}]})`. 가족에 카테고리 "식비"가 있고 "미분류"는 없다. | `categories`를 처리하기 전 `budgeted_spending`이 저장된다. "식비"는 `LOWER(name) = "식비"`로 찾아 갱신한다. "미분류"는 `Category.all_uncategorized_names`(지원 locale 목록, 한국어 없음)에도 없어서 "unallocated remainder" 메시지가 아니라 `Category '미분류' not found. Use get_categories to list categories.`로 `invalid_params`가 나고, 전체가 한 DB transaction이라 이 호출의 변경(예산 총액 포함)이 모두 롤백된다. `month:"11월"`은 `Invalid month: 11월. Use YYYY-MM or MMM-YYYY.`(`invalid_params`). |
| T-16 | R-55 | 텍스트 3문단, 길이 1500, 1500, 500자(문단 사이 빈 줄). | 청크 3개. 첫째 1500자(문단 1). 둘째는 문단 2를 붙이면 `1500+2+1500 > 2000`이라 첫 청크를 확정하고, 첫 청크의 마지막 200자 + `"\n\n"` + 문단 2 = 1702자. 문단 3을 붙이면 `1702+2+500 > 2000`이라 둘째를 확정하고, 마지막 200자 + `"\n\n"` + 문단 3 = 702자가 셋째. |
| T-17 | R-55 | 한 문단 4000자. | 하드 분할 조각 길이 2000, 2000, 400(오프셋 0, 1800, 3600). 조립: 조각 1(2000) → 조각 2는 합쳐서 2000을 넘으므로 청크 1(2000) 확정, 새 청크 = 마지막 200자 + `"\n\n"` + 조각 2 = 2202(상한 초과 허용) → 조각 3을 붙이면 넘으므로 청크 2(2202) 확정, 새 청크 = 200 + 2 + 400 = 602. 청크 길이는 2000, 2202, 602. |
| T-18 | R-56, R-81 | pgvector, 가족에 업로드한 문서가 청크 2개. `search_family_files({query:"2024년 소득세 환급액", max_results:50})`. | `max_results`는 20으로 자른다. 질의를 임베딩해 코사인 거리 순으로 최대 20개를 가져오고 청크가 2개이므로 `{success:true, query, result_count:2, results:[{content, filename, score}, ...]}`, `score = 1 − 거리`. `vector_store_id`가 없는 가족은 `{success:false, error:"no_documents", message:"No documents have been uploaded to the family document store yet."}`. |
| T-19 | R-26 | 한국어 질의 "이번 달 식비 예산 얼마 남았어?". | 서버는 질의를 번역·정규화하지 않는다. 시스템 프롬프트는 영어 고정이고 응답 언어 지시가 없다. 한국어 이름은 도구 인자에 그대로 전달된다(`update_budget`의 `category: "식비"`, 이름 매칭 규칙은 T-15). 한국어로 답할지는 모델에 달려 있어 코드로 보장되지 않는다(U-03). |
| T-20 | R-04 | 한국어 100자(공백 포함) 질문으로 채팅을 시작. | `title`은 앞 80문자(바이트 아님). |
| T-21 | R-81, R-51 | `VECTOR_STORE_PROVIDER=qdrant`일 때 가져오기 화면에 `.txt` 문서를 올린다. 이어서 `search_family_files({query:"보험 약관"})`. | `Ai.availability(:embed)`는 가능(`qdrant`는 embed route가 있다). `ensure_vector_store!`의 `create_store`가 "Qdrant adapter is not yet implemented"로 실패해 `upload_document`가 nil이고 `document_upload_failed` 알림, `family_documents` 행 없음, `vector_store_id` 없음. 검색은 `no_documents`. 이미 `vector_store_id`가 있던 가족이면 `search_failed`("Failed to search documents: Qdrant adapter is not yet implemented"). |
| T-22 | R-41, R-42 | `EXTERNAL_ASSISTANT_URL=https://agent.example/v1/chat/completions`, 토큰, 모델 미설정. 채팅에 사용자·assistant 메시지가 25개 complete. 응답 스트림: `data: {"model":"openclaw/main","choices":[{"delta":{"content":"안"}}]}`, `data: {"choices":[{"delta":{"content":"녕"}}]}`, `data: [DONE]`. | 요청 본문은 `{"model":"openclaw/main","messages":[마지막 20개 {role,content}],"stream":true,"user":"sure-family-<family_id>"}`, 헤더 `X-Agent-Id: main`, `X-Session-Key: agent:main:main`. 메시지 내용은 "안녕", `ai_model`은 `openclaw/main`으로 갱신. `llm_usages` 행은 생기지 않는다. 모델이 `openclaw/finance`이면 `X-Agent-Id: finance`, `openclaw/default`이면 `main`. |
| T-23 | R-43, R-44 | 외부 서버가 처음 두 번 연결 거부(`ECONNREFUSED`), 세 번째에 응답한다. 다른 경우: 텍스트 `"안"`이 흐른 뒤 연결이 끊긴다. | 첫째: 1초, 2초 대기 후 세 번째 시도에서 성공. 둘째: 재시도 없이 `Assistant::Error("External assistant connection was interrupted.")`, pending 메시지는 `"안"`이 있어도 삭제되고 `chats.error`가 쓰인다(내장 assistant는 `failed`로 남기는 것과 다르다). 세 번 모두 연결 거부이면 `External assistant is temporarily unavailable.`. |
| T-24 | R-60 | 일반 `member`(preview 꺼짐), 같은 사용자가 preview를 켠 뒤, `guest`. 각각 `/mcp tools/list`(또는 내장 채팅 도구 목록). | member: 35개(`import_bank_statement`는 `extract_pdf` 가능할 때만 포함). preview 켠 member: 49개(같은 조건). `guest`는 `/mcp`에서 가족 설정 도구 5개를 뺀 목록, 내장 채팅에서는 도구가 없다(R-16). preview 도구를 `tools/call`로 이름만 알고 호출해도 "Unknown tool". |
| T-25 | R-23, R-14 | 내장 assistant가 응답 도중 provider 오류 `"429 Too Many Requests"`를 받는다. 텍스트가 일부 나온 경우와 안 나온 경우. | 나온 경우 메시지 `status = failed`(history 제외), 안 나온 경우 메시지 삭제. 둘 다 `chats.error = {message:<속도 제한 문구>, technical_message:"429 Too Many Requests", type:<오류 클래스>}`이고 화면에 오류와 Retry가 나온다. Retry 후 마지막이 사용자 메시지이면 새 pending 메시지가 만들어진다. |
| T-26 | R-72 | 투자 계정에서 종목 AAPL의 `holdings` 행이 2026-11-10 `qty 10`이고 2026-11-15 이후 `qty 0`(전량 매도), 최신 날짜는 2026-11-18 `qty 0`이다. `get_holdings({page:1})`. | `DISTINCT ON` 서브쿼리는 `qty ≠ 0`인 행만 대상으로 날짜 내림차순 첫 행을 뽑으므로 2026-11-10 행이 선택되어 `{ticker:"AAPL", quantity:10.0, date:"2026-11-10", ...}`가 목록에 남는다(이미 판 종목이 옛 수량으로 보인다). `total_value`에도 그 행의 `amount`가 환산 없이 더해진다. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-20 `family/ai_settings.rb:12`, `:36-42`; C-01 `assistant.rb:116-120`; C-16 `chat.rb:132-142` | `REGISTRY.fetch(type) { REGISTRY["builtin"] }`라서 `mcp_only`와 모르는 값이 builtin 클래스로 간다. `mcp_only`는 `ai_available?`(`user.rb:264-266`)와 `ask_assistant`(`chat.rb:135`)에서 막히고 화면도 막는다(`insights_helper.rb:128`, `layouts/application.html.erb:3-4`). |
| R-02 | C-20 `user.rb:264-287`, `:925-949` | `app_mode.self_hosted?` 아니면 `true`를 돌려주는 분기를 그대로 썼다(managed 모드의 실제 키 관리는 확인하지 않음). |
| R-03 | C-18 `chats_controller.rb:5-7`, `:74-80`, `messages_controller.rb:5-10`, `:56-58`, `requires_ai_consent.rb:8-15`; C-19 `api/v1/chats_controller.rb:3-8`, `:68-80`, `api/v1/messages_controller.rb:2-6`, `base_controller.rb:347-351` | "채팅 조회는 `Current.user.chats`" 전칭: `grep -n "chats" app/controllers/chats_controller.rb app/controllers/messages_controller.rb app/controllers/api/v1/*chats* app/controllers/api/v1/messages_controller.rb` 에서 `Chat.find`·`Chat.all`을 찾지 못했다. 다른 컨트롤러(`application_controller`의 `set_default_chat` 등)는 열지 않았다. |
| R-04 | C-16 `chat.rb:40-52`; C-19 `api/v1/chats_controller.rb:19-48` | 제목 길이는 Ruby `String#first(80)`(문자 기준). |
| R-05 | C-16 `chat.rb:54-72`; C-10 `provider/openai.rb:51-62` | `Provider::Anthropic.effective_model`은 `anthropic.rb:45-50`. |
| R-06 | C-17 `user_message.rb:4-8`, `message.rb:11`; C-16 `chat.rb:125-130`; C-18 `messages_controller.rb:12-26`; C-19 `api/v1/messages_controller.rb:8-26`(파일 시작 기준) | |
| R-07 | C-16 `chat.rb:75-88`; C-18 `chats_controller.rb:52-55` | |
| R-08 | C-19 `api/v1/messages_controller.rb:28-43`(파일 시작 기준), C-17 `message.rb:5-11`, `user_message.rb:14-16`; `db/schema.rb` `messages.status` 기본 `"complete"` | "`request_response`는 `UserMessage`에만 있다"는 전칭: `grep -rn "request_response\b" app lib --include=*.rb --include=*.erb` 결과가 `jobs/assistant_response_job.rb:5`, `models/user_message.rb:14`, `responder.rb`의 private 메서드(다른 객체)뿐이다. 동적 정의(`define_method`)는 확인하지 않았다. 실행하지 않았으므로 결과는 추론(U-02). |
| R-09 | C-18 `jobs/assistant_response_job.rb:1-10`; C-16 `chat.rb:132-142`; C-17 `user_message.rb:14-16` | 재시도 정의 없음: 이 파일에 `retry_on`·`discard_on`이 없다는 것만 확인. `ApplicationJob`의 기본값은 읽지 않았다. |
| R-10 | C-16 `chat.rb:159-233`; C-18 `messages_controller.rb:28-45` | 값은 `Chat.response_timeout`(`:180-186`), 서버 한도는 `undelivered_response_timeout`(`:196-198`). |
| R-11 | C-17 `message.rb:5-18`; C-05 `responder.rb:171-184` | "연속 user 메시지를 합치지 않는다"는 `openai_messages_payload`·`MessageFormatter#build`에 병합 코드가 없다는 읽은 범위의 부재 확인. |
| R-12 | C-17 `assistant_message.rb:16-41` | |
| R-13 | C-17 `message.rb:13-16` | 화면 push 구현은 Turbo(원본 한정). |
| R-14 | C-16 `chat.rb:4-28`, `:94-107`, `:264-303` | 패턴과 순서는 파일 그대로. i18n 문구 내용은 열지 않았다. |
| R-15 | C-15 `provider/registry.rb:26-36`, `:82-109`; `assistant/provided.rb:4-16`; C-10 `openai.rb:129-135`, `:160-162`; C-14 `anthropic.rb:77-85`; C-02 `builtin.rb:20-26`, `:80-95` | `LLM_PROVIDER` ENV 우선은 `setting.rb:295-297`. |
| R-16 | C-08 `configurable.rb:56-71`; C-20 `user.rb:925-949` | "guest는 항상 intro"는 `before_validation` 콜백(`user.rb:81-82`)이 저장 때 적용한다는 코드 사실. 콜백을 우회하는 쓰기(`update_columns` 등)는 확인하지 않았다. |
| R-17 | C-03 `responder.rb:30-72`, `:114-119`; `.env.example:44-59`(상한 예시 5, 기본은 코드의 8) | `.env.example`의 예시값과 코드 기본값이 다르다(문서 예시일 뿐). |
| R-18 | C-03 `responder.rb:53-67`; C-11 `openai.rb:577`(Responses), `:673`(Chat Completions); C-14 `anthropic/chat_config.rb:30-37` | 두 줄 모두 `tool_choice == :none && 도구 있음`일 때만 `"none"`을 넣는다. |
| R-19 | C-03 `responder.rb:61-66`, `:110-112`; C-12 `openai.rb:727-797`; C-14 `message_formatter.rb:17-40` | Anthropic은 `supports_responses_endpoint?`를 정의하지 않아 `respond_to?`가 false. |
| R-20 | C-02 `builtin.rb:35-57` | |
| R-21 | C-04 `responder.rb:77-108`; C-03 `:32`, `:66`, `:69` | `any_response_has_text`는 텍스트만 본다(독립 검토에서 확인). 도구 호출이 있던 경우의 원본 테스트는 없다(`test/models/assistant_test.rb:305-322`). |
| R-22 | C-11 `openai.rb:137-146`, `:527-639`; C-12 `:642-725`; C-13 `chat_stream_parser.rb:10-41`; C-14 `anthropic.rb:372-405`; `.env.example:46-48` | `.env.example`가 "OpenAI-compatible providers are not streamed"라고 쓴 것과 코드가 일치한다. |
| R-23 | C-02 `builtin.rb:58-68`; C-17 `message.rb:3` | "tool_calls도 삭제"는 `has_many :tool_calls, dependent: :destroy`(`message.rb:3`). |
| R-24 | C-02 `builtin.rb:48-52`; C-17 `tool_call/function.rb:1-53`; C-05 `responder.rb:196-226` | |
| R-25 | C-28 `openai.rb:851-919`, `anthropic.rb:372-405`, `:458-508`; `usage_cost.rb:2-39`; `llm_usage.rb:40-139` | 가격표 파일 `config/llm_pricing.yml`은 열지 않았다. Anthropic partial 기록은 `anthropic.rb:372-385`. |
| R-26 | C-07; C-08 `configurable.rb:109-113`; C-20 `family/ai_promptable.rb:13`, `:60-73`, `:90-110` | "응답 언어 지시가 없다"는 부재 주장: `grep -in "language\|respond in\|locale" app/models/assistant/configurable.rb` 결과 없음(intro 지시문의 "format currency ... dates" 외). 가족 override 문구에 포함될 수 있다. |
| R-27 | C-08 `configurable.rb:115-182` | `Date.current`의 시간대는 `config.time_zone` 설정에 달려 있다(`config/application.rb:28`은 주석 처리, recurring 스펙 R-30 참고). 가족 시간대를 쓰는 코드는 이 파일에 없다. |
| R-28 | C-08 `configurable.rb:74-103` | |
| R-29 | C-09 `token_budget.rb:1-26` | |
| R-30 | C-05 `responder.rb:196-229`; C-14 `message_formatter.rb:17-72` | |
| R-31 | C-09; C-10 `openai.rb:168-218`; C-12 `:727-797` | Responses·Anthropic 경로에 자르기가 없다는 것은 `HistoryTrimmer`의 호출처가 `build_generic_messages`뿐이라는 부재 확인: `grep -rn "HistoryTrimmer" app lib`(`provider/openai.rb:740` 외에 없음). |
| R-32 | C-10 `openai.rb:174-189`; C-11 `:578`, C-12 `:674`; C-14 `anthropic.rb:361-363` | OpenAI `max_output_tokens`/`max_tokens` 설정 줄은 각 경로의 `explicit_max_response_tokens` 사용 줄. |
| R-33 | 2.1 부재 검색: `grep -rn "truncate\|bytesize\|MAX_RESULT\|\.first(" app/models/assistant/*.rb app/models/provider/openai.rb app/models/provider/anthropic.rb` | `function_result`·`ToolCall`에 크기 제한이 없다. 못 찾은 것일 뿐 DB 컬럼 제한(jsonb 크기)이나 ActiveJob 직렬화 제한은 확인하지 않았다. |
| R-34 | 2.1 부재 검색: `grep -rniE "monthly_limit\|spend_limit\|llm_budget\|usage_limit\|token_limit\|cost_limit\|max_cost" app lib config db/schema.rb`(`.rb`, `.rake`, `.yml`, `.erb`) | `invalid_llm_budget`(`settings/hostings_controller.rb:306`)은 R-31의 예산 입력 검증 문구다. 동적 호출(`send`)이나 `docs/`의 운영 가이드는 보지 않았다. |
| R-35 | C-15 `registry.rb:82-109`; C-10 `openai.rb:13-24`, `:58-107`; C-14 `anthropic.rb:62-75` | 프록시 해석은 `ai/transport/http.rb`(읽지 않음)에 위임한다는 호출 사실만. |
| R-36 | C-11 `openai.rb:433-480`, `:527-639`; C-12 `:642-813`; C-13 `chat_config.rb:7-44`; C-14 `anthropic/chat_config.rb:20-94`, `message_formatter.rb:17-139`; C-04 `responder.rb:121-137` | gem 직렬화는 읽지 않았다(확인 한계). 사용자 메시지 재전송은 `chat_config.rb:19-21`과 `responder.rb:123-124`(매 요청 `message.content`)의 조합. |
| R-37 | C-13 `chat_parser.rb:8-58`, `generic_chat_parser.rb:8-60`; C-14 `anthropic/chat_parser.rb:8-58`; C-04 `responder.rb:139-143` | |
| R-38 | C-15 `provider.rb:32-75`; C-04 `responder.rb:139-143` | "재시도·failover 없음"은 `responder.rb`·`builtin.rb`·provider의 `chat_response`에 재시도 코드가 없다는 읽은 범위의 확인(gem 내부 재시도는 확인하지 않음, 확인 한계). |
| R-40 | C-21 `external.rb:1-65` | |
| R-41 | C-21 `external.rb:67-128`, `external/client.rb:21-44`, `:127-144` | 연결·읽기 타임아웃 상수는 `client.rb:6-10`. 프록시 해석(`Ai::Transport::Http.net_http_proxy`)은 열지 않았다. |
| R-42 | C-21 `external/client.rb:69-112`, `:146-151`, `external.rb:90-95` | |
| R-43 | C-21 `external/client.rb:12-19`, `:36-65` | `Net::HTTPSuccess` 아닌 응답은 `Assistant::Error`라서 `TRANSIENT_ERRORS`에 걸리지 않는다. |
| R-44 | C-21 `external.rb:96-111` | |
| R-45 | C-21 `external/client.rb:44`; 2.1 부재 검색: `grep -rn "llm_usages\|record_llm_usage" app/models/assistant/` 결과 없음 | 같은 계정을 `ai_assistant_served_daily`로 센 것은 `Usage.capture`(telemetry)뿐. |
| R-46 | C-21 `external/model_catalog.rb:15-75`; 호출처 `app/controllers/settings/hostings_controller.rb`(`grep -rn "ModelCatalog" app`) | 호출처 본문은 읽지 않았다. |
| R-47 | C-22 `router.rb:7-33`, `routes.rb:9-27`, `consent.rb:3-12`, `route.rb:6-38`, `availability.rb:5-21`; C-23 `legacy_env_config.rb:34-53`, `:86-123` | |
| R-48 | 부재 검색: `grep -rn "Ai\.available\|Ai\.availability\|Ai\.plan\|requires_ai\|Ai::Router\|ai_feature_available" app lib config --include=*.rb --include=*.rake --include=*.erb`. 결과: `:chat`을 인자로 쓰는 호출이 없고 `requires_ai`는 `:bill_setup`·`:enhance_merchants`에서만, `ai_feature_available?`는 `:bill_setup`에서만 쓰인다. `Ai.available?(feature)`로 변수를 넘기는 곳은 `application_helper.rb:6-8`이고 그 호출처는 `bills_helper`·bills 뷰다. | 놓쳤을 가능성: 문자열로 feature 키를 조립하는 동적 호출(`send`), `docs/`·테스트. |
| R-50 | C-23 `legacy_env_config.rb:125-146`; C-24 `vector_store/registry.rb:8-75`; C-26 `pgvector.rb:26-35` | |
| R-51 | C-26 `qdrant.rb:24-65`; `search_family_files.rb:76-84`(안내 문구에 qdrant 포함) | 문서(파일 머리 주석 "not yet wired up")와 구현이 일치한다. 구현 이력은 확인하지 않았다. |
| R-52 | C-24 `family/vector_searchable.rb:8-23`(파일 시작 기준), `pgvector.rb:41-45` | `delete_store` 호출(`rescue nil`)이 실패 시 정리의 유일한 사용처. |
| R-53 | C-27 `imports_controller.rb:87-90`, `:250-324`; `process_pdf_job.rb:19`, `:68-82`; `import.rb:36` | 부재 검색: `grep -rn "upload_document" app lib config --include=*.rb --include=*.rake --include=*.erb` 결과는 `imports_controller.rb:300`, `process_pdf_job.rb:73`뿐. `valid_pdf_file?`(`imports_controller`)·`PdfImport.create_from_upload!`는 열지 않았다. |
| R-54 | C-24 `family/vector_searchable.rb:40-63`(파일 시작 기준), C-27 `family_document.rb:1-25`; 부재 검색: `grep -rn "mark_error!\|mark_ready!\|remove_document\|\.remove_file" app lib --include=*.rb --include=*.rake` | `mark_ready!`·`mark_error!`·`remove_document`의 호출처 없음(`family_document.rb`·`vector_searchable.rb`의 정의만). 놓쳤을 가능성: 뷰(`.erb`)·JS·테스트·동적 호출. |
| R-55 | C-25 `embeddable.rb:4-148`; C-26 `pgvector.rb:16-18`, `:58-101`, `:159-189`; C-24 `vector_store.rb:7-37` | T-16·T-17의 값은 `chunk_text`·`hard_split`을 손으로 추적해 구했다. 실행하지 않았다. |
| R-56 | C-26 `pgvector.rb:117-149`, `openai.rb:63-85`, `base.rb:2-5`, `:36-48` | OpenAI 호스팅 store의 청킹·점수는 외부 동작(확인하지 않음). |
| R-60 | C-01 `assistant.rb:17-46`, `:66-120`; C-29 `function.rb:12-15`; C-30 `mcp_controller.rb:98-138`; `grep -rn "ai_feature =" app` 결과 `import_bank_statement.rb:4`뿐 | 49개는 클래스 수(`assistant.rb`의 `Function::` 참조 49개)와 `app/models/assistant/function/*.rb` 중 `bills_support`·`month_resolvable`·`rule_support`·`statement_vault_support`·`transfer_match_support`·`transfer_support`(support 모듈 6개)를 뺀 파일 수 49개가 같다는 것으로 확인했다. |
| R-61 | C-29 `function.rb:35-99`; 각 도구 파일의 `strict_mode?` | `strict_mode?` 오버라이드 부재 확인: `for f in app/models/assistant/function/*.rb; do grep -q "def strict_mode?" $f \|\| echo $f; done` → `get_bill_details.rb`와 support 모듈 6개뿐. |
| R-62 | C-06 `function_tool_caller.rb:11-77`; C-30 `mcp_controller.rb:111-138`; `get_budget.rb:63-83`(`call`에 rescue 없음), `month_resolvable.rb:14-28`(`parse_month`), `assistant.rb:2`(`Assistant::Error = Class.new(StandardError)`) | "`Assistant::Error`가 rescue 목록에 없다"는 `StandardError` 직접 하위라 `Date::Error`·`ArgumentError`·`KeyError`·`JSON::ParserError`·`ActiveRecord::RecordNotFound`의 상위 클래스가 아니라는 Ruby 클래스 계층에 의존한다(추론 아님, 정의가 `Class.new(StandardError)`). `Date.parse(nil)`이 `TypeError`를 낸다는 Ruby 동작은 실행하지 않았다(U-06). |
| R-63 | 각 도구 파일의 `error` 헬퍼; `get_balance_sheet.rb:147-149`, `get_valuations.rb:109-111`, `get_income_statement.rb:55-80`, `bills_support.rb:25-30` | 모든 도구를 한 줄씩 훑어 분류했다. 도구가 49개라 개별 분류가 틀렸을 가능성은 R-ID별 표의 "실패" 칸이 기준이다. |
| R-64 | C-29 `function.rb:17`, `:108-120`; `get_holdings.rb:90`, `get_valuations.rb:79` | |
| R-65 | 각 도구 파일의 범위 지정 줄(1.4.2의 "범위" 칸). `create_goal.rb:93`, `import_bank_statement.rb:58`, `:87`, `update_transaction.rb:99-113` | `accessible_accounts`·`writable_by`·`annotatable_by`의 정의는 `account.rb:115-150`, `user.rb:230-232`(정의만, 권한 스펙은 U-01). |
| R-66 | 도구 description의 "Confirm" 문장: `grep -n -i "confirm\|ask the user\|before calling\|dry_run" app/models/assistant/function/*.rb`; 시스템 프롬프트 C-07; 화면 `app/views/assistant_messages/_assistant_message.html.erb:22-24`, `chats/*`, `messages/*`에서 `grep -rniE "confirm\|approve" app/views/chats app/views/assistant_messages app/views/messages`(채팅 삭제 확인 대화상자 `CustomConfirm.for_resource_deletion("chat")`만) | 부재 주장이다. 놓쳤을 가능성: Stimulus JS(`chat_controller.js`는 `confirm|approve|tool_call` 검색 결과 없음), `docs/llm-guides/`의 운영 지침, 모델이 따르는 프롬프트 override. |
| R-67 | `grep -n "dry_run" app/models/assistant/function/*.rb` 결과: `match_transfer.rb`, `unmatch_transfer.rb`, `update_transfer.rb`, `set_opening_balance.rb`뿐 | 부재 주장. 다른 이름(`preview`)은 `preview_rule`·`create_rule`·`update_rule`(R-101~R-103). |
| R-68 | 각 도구 파일(1.4.2) | 요약이므로 개별 근거는 R-84, R-89, R-97, R-104. |
| R-69 | C-45 `month_resolvable.rb:4-28`; `budgets.md` R-01·R-02 | |
| R-70~R-118 | C-40~C-88(R-ID 번호 − 30). 도메인 링크는 선행 스펙의 R-ID이고 그 동작은 해당 스펙의 2.1을 따른다. | 도구 49개를 한 파일씩 읽고(`call`·스키마·보조 메서드 전체), 줄 범위는 `def params_schema`부터 `def call` 끝까지다. 읽은 파일은 frontmatter `sources`의 `function/*.rb`다. |
| R-70 | `get_transactions.rb:173-261`(반환), `:177-190`(Uncategorized 별칭), `:192-198`(접근 계정 id 집합) | `Transaction::Search`·`LabelNormalizer`의 동작은 transactions 스펙 소관. |
| R-72 | `get_holdings.rb:86-120`, `:127-147` | `build_holdings_query`가 자체 쿼리다. T-26의 동작은 `DISTINCT ON` 서브쿼리 구조에서 도출했고 실행하지 않았다. |
| R-75 | `get_budget.rb:63-125`; `month_resolvable.rb:14-28` | `BudgetCategory::Group.for`·`status` 판정 메서드의 본문은 budgets 스펙 R-14·R-20. |
| R-81 | `search_family_files.rb:54-157` | 검사 순서는 `return`이 나오는 줄 순서 그대로. |
| R-82 | `create_transaction.rb:138-224`; transactions R-69(API 경로의 같은 Entry 경로 주석: `create_transaction.rb:3-9`) | |
| R-90 | `update_budget.rb:90-149`; budgets R-38 (d) | `BudgetCategory#update_budgeted_spending!` 본문은 budgets R-12. |
| R-91 | `create_goal.rb:73-162`, `assistant.rb:17-36`(preview 목록에 없음) | Goal 모델 본문은 읽지 않았다(goals 스펙 R-37 참조). |
| R-93 | `import_bank_statement.rb:57-167` | `Provider::*#extract_bank_statement` 본문은 읽지 않았다(PDF 추출은 범위 밖). |
| R-104 | `apply_rule.rb:60-118`, `rule_support.rb:410-450` | `Rule#apply_later`·`matching_scope`·`notification_baseline_timed_out?` 본문은 transaction-classification 스펙 소관. |
| T-01~T-25 | 구현에서 도출(실행하지 않음). 값은 각 R-ID의 근거 줄을 손으로 따라가 구했다. T-07의 해시 길이는 `{"role":"user","content":"안녕"}`의 문자 수 30(공백 없는 JSON)로 셌다. T-14의 "locale `ko` fallback"은 `config.i18n.fallbacks = true`(`config/application.rb:35`)와 `ko`가 `SUPPORTED_LOCALES`에 없는 것(`languages_helper.rb:158-176`)에서 나온 추론이다. | 시스템 프롬프트의 정확한 문장·T-08의 계정 줄 포맷은 C-08에서 따랐다. |

### 2.2 코드 읽는 순서

1. `assistant.rb`(registry) → `chat.rb`·`user_message.rb`·`assistant_message.rb`(상태와 진입) → `assistant_response_job.rb`.
2. 내장 assistant: `builtin.rb` → `responder.rb` → `function_tool_caller.rb` → `configurable.rb`(프롬프트) → `provider/openai.rb`(`chat_response`, 예산, 두 경로) 또는 `provider/anthropic.rb` + `anthropic/chat_config.rb`·`message_formatter.rb`.
3. 외부 assistant: `external.rb` → `external/client.rb`.
4. 도구: `function.rb`(기본 계약) → 필요한 도구 파일과 `*_support.rb`.
5. 벡터 검색: `vector_store/registry.rb` → `family/vector_searchable.rb` → `embeddable.rb` → `pgvector.rb`·`openai.rb` → `search_family_files.rb` → `imports_controller.rb`·`process_pdf_job.rb`.
6. 가용성: `user.rb#ai_available?` → `family/ai_settings.rb` → `ai/router.rb`·`ai/routes.rb`·`ai/legacy_env_config.rb`.

원본의 구현 전략: 정적 프롬프트와 세션 컨텍스트를 분리해 provider 프롬프트 캐시를 쓰고(R-26), 도구 정의의 마지막 항목에 Anthropic `cache_control`을 건다(R-36). 도구 결과는 항상 반환값(데이터)으로 모델에게 돌려주고 예외를 던지지 않아 한 번의 잘못된 호출이 턴 전체를 죽이지 않게 한다(R-62).

### 2.3 비교·재사용 출처

같은 기능을 다른 레포에서 스펙으로 만든 것은 없다. 원본 코드를 복사하지 않았다. 정적 지시문(`STATIC_INSTRUCTIONS`)은 라이선스가 허용하는지 [overview](../overview.md) 1절에서 확인한 뒤 가져간다.

### 2.4 검토 기록

`draft`다(미결정 U-01~U-06이 남았고 선행 스펙도 `draft`). 2026-11-18에 한 점검의 범위는 다음과 같다.

- **독립 검토(검토자 서브에이전트 1명)**: 대화 루프·상태(R-02~R-24), 프롬프트·history·예산(R-26~R-34), provider·외부 assistant·벡터(R-36~R-56), 쓰기 도구 전부, 도구 개수(49), 선행 스펙 링크 표본, T-01~T-25 중 대부분 재계산, 부재 주장(`upload_document`, `mark_error!`, Qdrant 미구현, `HistoryTrimmer` 호출처)을 확인했다. 중요 오류 5건(R-21, R-72, R-92·R-71 링크, R-91, R-01·R-09), 사소 다수가 나왔다. 작성자가 전부 반영했고 T-26을 추가했으며 U-07~U-09는 해당 스펙이 생겨 삭제했다. 정의된 R-ID는 113개다(번호 R-39·R-49·R-57~R-59는 쓰지 않음).
- **메인 표본 점검**: R-21(`assistant/responder.rb:64-69`), R-01·R-09(`user.rb:264-266`), R-72(`assistant/function/get_holdings.rb:105-125`)를 원본에서 직접 확인했다.
- **대조하지 못한 것**: `ruby-openai`·`anthropic` gem의 내부 재시도와 직렬화(R-38), 읽기 도구 일부의 반환 필드(R-99, R-100, R-106~R-108, R-110, R-111, R-113~R-115), `/mcp` 요청의 `Time.use_zone`(R-69), 외부 서버 오류 문구(U-05), `Debuggable`·Langfuse·`ChatReservation`.
- 재구현: 미수행.

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-26, R-70, R-90 | 한국어 사용자를 위해 시스템 프롬프트에 응답 언어 지시를 넣고, "미분류"를 `Uncategorized` 별칭으로 받는다. | 원본은 응답 언어를 지정하지 않고 한국어 별칭이 없어 T-14·T-15처럼 실패한다. | 별칭 목록과 프롬프트 한 문장이 추가된다. T-14·T-15 기대값이 달라진다. |
| R-66 | 쓰기·삭제 도구에 서버측 확인 단계(예: `apply_rule`의 `preview_token`과 같은 확인 토큰)를 넣을지 정한다. | 원본은 모델이 description을 따르는 것에 의존한다(R-66). | 도구 호출이 두 단계가 된다. 승인 UI가 필요하다. |
| R-65, R-91, R-93 | `create_goal`·`import_bank_statement`에 접근·쓰기 계정 판정을 건다. | 원본은 `family.accounts`로 찾아 공유 권한을 무시한다. | `account_not_found` 계열 실패가 늘어난다. U-01 해소와 함께 정한다. |
| R-08 | API 재시도 경로를 고쳐 구현한다. | 원본은 동작하지 않는 것으로 보인다(U-02). | 응답 코드와 흐름을 새로 정의한다. |
| R-51 | Qdrant를 지원하려면 어댑터를 새로 구현한다. | 원본은 미구현이다. | R-50~R-56에 어댑터 규칙이 추가된다. |
