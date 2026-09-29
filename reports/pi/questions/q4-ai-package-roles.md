# Q4: `pi-ai` 패키지는 무엇을 담당하나?

- **Commit**: `4259686d9290c0d73ae7192b796aee3e530a9779` · **작성일**: 2026-09-29 · **목적**: 학습 (Q1 1단계)
- **대상**: `packages/ai` (`@earendil-works/pi-ai` v0.87.1, src 25.9k줄)
- **관련 그림**: [구조](../diagrams/ai-architecture.html) · [streamSimple 단계](../diagrams/ai-streamsimple-workflow.html) · [시퀀스](../diagrams/ai-stream-sequence.html) · [카탈로그 흐름](../diagrams/ai-model-catalog-dataflow.html) · [메시지 상태](../diagrams/ai-message-lifecycle.html)

## 결론

`pi-ai`는 **"어떤 LLM이든 같은 모양으로 부르는" 층**이다. 입력(`Context`)과 출력(`AssistantMessage` + 이벤트 스트림)을 하나로 정하고, 그 아래에서 provider별 인증·wire 형식·모델 카탈로그·비용 계산 차이를 흡수한다. agent 루프나 tool 실행은 하지 않는다. 그 일은 `pi-agent-core`가 맡는다. `코드 확인`

## 핵심 설계: `api`와 `provider`를 나눈다

이 패키지를 이해하는 가장 중요한 구분이다.

| 개념 | 위치 | 의미 | 개수 |
|---|---|---|---|
| **api** (wire 프로토콜) | `src/api/*.ts` | HTTP 요청/SSE 파싱 방식. 예: `anthropic-messages`, `openai-completions`, `openai-responses`, `google-generative-ai`, `bedrock-converse-stream` | `KnownApi` 10종 (`types.ts:17`) |
| **provider** (벤더/계정) | `src/providers/*.ts` | baseUrl + 인증 방법 + 모델 목록 + 사용할 api의 조합 | 약 42개 (`*.models.ts` 42개) |

- 하나의 api를 여러 provider가 재사용한다. 예를 들어 Groq, Cerebras, DeepSeek 같은 OpenAI 호환 벤더는 `openai-completions` api를 공유하고, 벤더별 차이는 `Model.compat` 설정(`OpenAICompletionsCompat`, `types.ts:787`)으로 조정한다. `코드 확인` (groq·cerebras·deepseek의 `api: openAICompletionsApi()`)
- provider 정의 예시: `providers/anthropic.ts` → `createProvider({ id, baseUrl, auth: { apiKey, oauth }, models, api: anthropicMessagesApi() })` `코드 확인`

## 주요 기능별 담당

| 기능 | 핵심 파일 | 내용 | 검증 |
|---|---|---|---|
| **공통 타입 계약** | `types.ts` (1166줄) | `Message`(system/user/assistant/toolResult), `AssistantMessage`, `Tool`, `Usage`, `StopReason`, `Model`, `AssistantMessageEvent` | 코드 확인 |
| **스트리밍 이벤트 프로토콜** | `utils/event-stream.ts`, `types.ts:765` | `start → text/thinking/toolcall_{start,delta,end} → done or error`. async iterator로 소비하고 `.result()`로 최종 메시지를 받는다 | 코드 확인 |
| **모델 레지스트리 + 호출 진입점** | `models.ts` (1250줄) | `createModels()` → `Models`. `getModel`/`getAvailable`/`refresh`/`login`/`stream`/`streamSimple`/`complete` | 코드 확인 |
| **provider 조립** | `models.ts:1028` `createProvider` | 정적 모델 + 동적 모델(`fetchModels`)을 합치고, 모델의 `api`에 따라 구현을 dispatch한다 | 코드 확인 |
| **wire 구현** | `api/*.ts` | 벤더 SDK/HTTP 호출 → 공통 이벤트로 변환. 가장 큰 파일은 openai-completions(1726줄), openai-codex(1697줄), anthropic(1528줄) | 코드 확인 (anthropic만 읽음) |
| **lazy loading** | `api/lazy.ts`, `api/*.lazy.ts` | 첫 호출 때 `import()`로 구현을 불러온다. 스트림은 동기로 즉시 반환하고, setup 실패는 `error` 이벤트로 바꾼다 | 코드 확인 |
| **인증** | `auth/resolve.ts`, `auth/oauth/*` | 우선순위: 요청 `apiKey` → 저장된 credential(oauth/api_key) → 환경변수·ambient. OAuth는 만료 5분 전에 lock을 걸고 한 번만 refresh한다(double-checked locking) | 코드 확인 |
| **simple 옵션 통합** | `api/simple-options.ts` | `streamSimple`은 `reasoning: ThinkingLevel` 하나만 받고, provider별 thinking budget/effort로 변환한다 (`anthropic-messages.ts:866`) | 코드 확인 |
| **cross-provider hand-off** | `api/transform-messages.ts` | 다른 모델이 만든 이력을 현재 모델에 맞게 바꾼다. tool call ID 정규화(OpenAI 450자+ → Anthropic `^[a-zA-Z0-9_-]{,64}$`), thinking 블록 처리, 이미지 미지원 모델이면 placeholder로 대체 | 코드 확인 |
| **모델 카탈로그** | `providers/*.models.ts` + `data/*.json`, `scripts/generate-models.ts` | 빌드 때 models.dev·OpenRouter 등에서 받아 자동 생성한다. chat 카탈로그에는 tool calling을 지원하는 모델만 넣는다(README) | 코드 확인 |
| **비용/토큰** | `models.ts:1187` `calculateCost`, `utils/estimate.ts` | `Usage`에 input/output/cache 토큰과 비용을 기록한다 | 코드 확인 (계산식 상세 미확인) |
| **재시도·오버플로 판정** | `utils/retry.ts`, `utils/overflow.ts` | `isRetryableAssistantError`, `retryAssistantCall`, `isContextOverflow`. 판정 함수만 제공하고 실제 재시도 정책은 상위(agent)가 쓴다 | 코드 확인 |
| **테스트용 가짜 provider** | `providers/faux.ts` | 미리 정해 둔 응답을 스트리밍한다. agent/coding-agent 테스트에서 사용 | 코드 확인 (사용처는 추론) |
| **부가 모달리티** | `images*.ts`, `api/*classify*` | 이미지 생성(`generateImages`)과 classifier(`classify`)는 chat과 별도 계약 | 코드 확인 (세부 미확인) |
| **구 API 호환** | `compat.ts` | 예전 전역 레지스트리 방식의 `stream()`/`getModel()`/`registerApiProvider()` | 코드 확인 |

## 호출 경로 (`Models.streamSimple`)

```
caller → Models.streamSimple(model, context, opts)          models.ts:889
  ├─ normalizeContext(context)   systemPrompt/tools → system message로 접음   utils/transcript.ts:30
  └─ lazyStream(...)  ← 스트림은 즉시 반환                   api/lazy.ts
       ├─ requireChatProvider(model)
       ├─ applyAuth → getAuth → resolveProviderAuth         models.ts:831, auth/resolve.ts:33
       └─ provider.streamSimple → (lazy import) api/anthropic-messages.ts:866
            └─ reasoning → effort/budget 변환 → stream()      :511
                 └─ SDK 호출, SSE → AssistantMessageEvent push
                    실패 시 stopReason=error|aborted로 error 이벤트  :825
```

**에러 계약**: provider 호출 실패는 throw하지 않는다. 스트림 안의 `error` 이벤트와 `AssistantMessage.stopReason`으로 알린다. 예외는 하나로, `streamSimple`을 직접 호출했는데 인증이 없으면 동기로 throw한다(`types.ts:755` 주석). `코드 확인`

## 상위 패키지와의 경계

- **`pi-agent-core`는 provider 레지스트리를 모른다.** `agent-loop.ts`는 주입받은 `streamFn`을 쓰고, 없으면 `setDefaultStreamFn()`으로 등록된 전역 fallback을 쓴다(`agent/src/stream-fn.ts`). agent가 ai에서 가져오는 것은 타입과 유틸(retry, validation, frame)뿐이다. `코드 확인`
- **`coding-agent`가 둘을 연결한다.** `core/sdk.ts:40`에서 `setDefaultStreamFn(streamSimple)`(compat)을 호출하고, 실제 세션은 `core/model-runtime.ts:210`의 `createModels({ credentials, modelsStore })`로 만든 런타임의 `streamSimple`을 쓴다. `코드 확인`
- import 집계(agent+coding-agent src): 루트 `pi-ai` 111회, `/compat` 13회, 나머지 subpath는 몇 회씩. `코드 확인`

## 설계 포인트 (학습 관점)

1. **side-effect free 루트**: `index.ts` 주석에 따르면 루트 export에는 카탈로그, provider factory, OAuth 구현이 들어 있지 않다. 이것들은 `/providers/*`, `/api/*`, `/compat` subpath로 분리되어 있어 tree-shaking이 된다. `코드 확인`
2. **`TranscriptContext` branded type**: `normalizeContext()`만 이 타입을 만들 수 있다. 그래서 정규화하지 않은 `Context`가 provider 코드에 들어가지 못하게 타입 수준에서 막는다(`types.ts:744-747`). `코드 확인`
3. **`partial`은 공유 객체**: 이벤트마다 스냅샷을 만들지 않고, 계속 자라는 같은 `AssistantMessage`를 가리킨다(`types.ts:758` 주석). 소비자가 이 객체를 저장하려면 복사해야 한다. `코드 확인`(주석) / 복사 필요성은 `추론`

## 다이어그램 작성 중 추가로 확인한 사실 (`코드 확인`)

- 모델 목록은 정적 카탈로그 위에 런타임 결과를 덮어쓴다. `createProvider`의 `currentModels()`가 baseline 모델과 `dynamicModels`를 합치고, type+id가 같으면 dynamic 쪽을 쓴다. `Models.refresh()`(`models.ts:545`)는 먼저 저장된 캐시를 복원하고, credential을 확인한 다음 네트워크에서 받아 `modelsStore`에 persist한다. generation이 최신이 아니면 결과를 버린다.
- 레포 안에서 런타임 카탈로그를 쓰는 provider는 `providers/radius.ts`뿐이다. coding-agent는 `FileModelsStore(models-store.json)`를 사용한다(`model-runtime.ts:222`).
- deferred 응답은 `DeferredHandle`을 받아 `fetchDeferred`/`streamDeferred`로 새 스트림을 여는 방식이다. 이 커밋에서 이를 실제로 구현한 provider는 faux뿐이다.
- pi-ai는 재시도를 직접 하지 않는다. 판정 함수(`isRetryableAssistantError`, `isContextOverflow`, `isRecoverableLength`)만 제공하고, 실제 재시도는 agent-core(`harness/runtime/drive/response.ts`, `harness/compaction`)와 coding-agent(`agent-session.ts`)가 한다.

## 다음에 볼 것

- `openai-completions.ts`의 `compat` 자동 감지(URL 기반): 벤더 차이를 어떻게 흡수하는지
- `transform-messages.ts` 후반: thinking 블록을 같은 모델/다른 모델일 때 각각 어떻게 처리하는지
- `coding-agent/src/core/model-runtime.ts`: `Models` 위에 route/fallback을 어떻게 얹는지 (`:732`에서 재귀 호출)
- → 이어서 Q1 1단계의 `agent/src/agent-loop.ts`
