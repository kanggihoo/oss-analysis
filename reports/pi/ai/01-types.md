# ai 01: `types.ts` — pi-ai의 공용 서식 모음

- **기준 commit**: `3874b3e98` (2026-10-02, worktree clean) / **분석일**: 2026-10-04
- **선행 문서**: [00-role](./00-role.md) (ai 패키지의 역할)
- **대상**: `repos/pi/packages/ai/src/types.ts` (1168줄 전체 읽음). 줄 번호는 모두 이 파일 기준이다.
- **검증 수준**: 타입 정의는 `코드 확인`이다. 런타임 동작은 `미확인`이며 다음 단계에서 본다. `추론`은 따로 표시한다.
- 이 파일은 타입만 정의한다. 로직은 `utils/transcript.ts`, `utils/event-stream.ts`, `api/*`에 있다.

> [!NOTE]
> **2026-10-06 갱신** (`3874b3e98` → `28dcce2ba` diff 반영): `Model`에 `samplingParamsByThinkingLevel`, 타입 `SamplingParams`/`SamplingParamsByThinkingLevel`이 추가되었고 `KnownProvider`의 `azure-openai-responses`가 `azure`로 바뀌었다(`types.ts`). 그 밖의 줄 번호는 ±수 줄 어긋날 수 있다.

## 0. 이 파일은 무엇인가
pi-ai는 Claude, GPT, Gemini 같은 여러 AI 회사의 서비스를 같은 방식으로 호출하게 해 주는 "통역사"다. `types.ts`는 그 통역사가 쓰는 **공용 서식 모음**이다.

예: 사용자가 "main.ts의 버그를 고쳐 줘"라고 한다.
1. 대화와 도구 목록을 `Context`에 담는다.
2. 통역사가 회사별 말투(Anthropic은 `messages`, OpenAI는 `chat/completions`)로 바꿔 보낸다.
3. 답이 조각조각 도착하고, 그때마다 `text_delta` 같은 알림(`AssistantMessageEvent`)이 나온다.
4. 끝나면 `done` 알림과 함께 최종 답(`AssistantMessage`)이 나온다.

회사가 달라도 위쪽 코드는 같은 서식만 보면 된다.

## 1. 한눈에 보는 관계
```
Context(입력) --normalizeContext()--> TranscriptContext(다듬은 입력)
                                              │  + Model(누구에게) + SimpleStreamOptions(어떻게)
                                              ▼
                                  AssistantMessageEventStream
                                    알림 12종 (start … done | error)
                                              ▼
                                  AssistantMessage (최종 답) ── 다음 턴의 Context.messages에 들어감
```

## 2. 주요 타입 카탈로그

### 2.1 대화 한 줄: `Message` (610줄)
`Message = SystemMessage | UserMessage | AssistantMessage | ToolResultMessage`. `role` 값으로 구분한다.

| 타입 | role | 역할 | 주요 인자 |
|---|---|---|---|
| `SystemMessage` (522) | `"system"` | AI에게 주는 지침과 도구 목록 | `content`(지침 글), `sections`(이름 붙은 지침 조각, `null`이면 삭제), `toolsAdded`, `toolsRemoved`, `timestamp` |
| `UserMessage` (540) | `"user"` | 사용자가 한 말 | `content`(글 또는 글+이미지), `timestamp` |
| `AssistantMessage` (546) | `"assistant"` | AI의 답 (최종본) | `content`(글/생각/도구호출 배열), `api`, `provider`, `model`, `usage`, `stopReason`, `errorMessage`, `timestamp` |
| `ToolResultMessage` (594) | `"toolResult"` | 도구를 실행한 결과 | `toolCallId`(어떤 호출의 결과인지), `toolName`, `content`, `isError`, `details`, `timestamp` |

### 2.2 메시지 안의 조각: content 타입 (389~425)
**어느 메시지에 어떤 조각이 들어가는가**가 중요하다.

| 메시지 | 들어갈 수 있는 조각 | 줄 |
|---|---|---|
| `UserMessage` (사용자) | 글(`TextContent`), 이미지(`ImageContent`) | 542 |
| `AssistantMessage` (AI의 답) | 글(`TextContent`), 추론(`ThinkingContent`), 도구 호출(`ToolCall`). **이미지는 없다.** | 548 |
| `ToolResultMessage` (도구 결과) | 글(`TextContent`), 이미지(`ImageContent`) | 599 |

AI는 chat 답변으로 이미지를 만들지 않는다. 이미지를 **보는** 것(입력)은 되고, **만드는** 것은 별도 기능이다(§2.10의 `generateImages`, 결과는 `AssistantImages`).

AI의 답 한 번은 이 셋이 섞인 배열이다. 예: `[추론, 글("파일을 읽어 볼게요"), 도구호출(read), 도구호출(grep)]`. 도구 호출이 여러 개 들어갈 수 있다.

| 타입 | `type` 값 | 역할 | 주요 인자 |
|---|---|---|---|
| `TextContent` | `"text"` | 일반 글 | `text` |
| `ThinkingContent` | `"thinking"` | AI의 추론 과정 | `thinking`, `thinkingSignature`(다음 요청에 되돌려 보낼 서명), `redacted`(안전 필터로 가려졌는지) |
| `ImageContent` | `"image"` | 이미지 (사용자/도구 결과 쪽에서만 사용) | `data`(base64), `mimeType` |
| `ToolCall` | `"toolCall"` | "이 도구를 이 인자로 실행해 줘"라는 요청 | `id`, `name`, `arguments`(JSON 객체) |

### 2.3 보낼 묶음: `Context`, `TranscriptContext`, `Tool` (715~749)

| 타입 | 역할 | 주요 인자 |
|---|---|---|
| `Context` | 호출하는 쪽이 만드는 입력 | `systemPrompt`, `messages`, `tools` |
| `TranscriptContext` | `Context`를 다듬은 내부용 입력. 만드는 함수는 `normalizeContext()`(`utils/transcript.ts:30`)뿐이다(brand 타입). | `messages`만. 시스템 프롬프트와 도구는 맨 앞 `SystemMessage` 안에 들어간다. |
| `Tool` | AI가 쓸 수 있는 도구 한 개의 설명서 | `name`, `description`, `parameters`(인자 형식, typebox 스키마), `constrainedSampling` |

**`Context`와 `TranscriptContext`의 차이** (`utils/transcript.ts:30-34`, `코드 확인`)
- 같은 내용을 담은 두 가지 모양이다. 달라지는 것은 지침(`systemPrompt`)과 도구(`tools`)를 두는 위치뿐이다.
  ```
  Context             { systemPrompt: "...", tools: [...], messages: [유저, AI, ...] }
        │ normalizeContext()
        ▼
  TranscriptContext   { messages: [시스템메시지(지침+도구), 유저, AI, ...] }
  ```
- `Context`는 쓰기 편한 입력이다. 호출하는 쪽이 만들어서 `stream()` 같은 공개 함수에 넘긴다.
- `TranscriptContext`는 provider가 처리하기 쉬운 내부용이다. 지침과 도구가 맨 앞 `SystemMessage`가 되므로 모든 것이 `messages` 한 줄에 모인다. 둘 다 비어 있으면 시스템 메시지를 만들지 않는다.
- 기록 중간에 바뀌는 지침과 도구(`SystemMessage`의 `sections`, `toolsAdded`, `toolsRemoved`)도 같은 방식으로 다룰 수 있다.
- provider 쪽 함수는 `TranscriptContext`만 받는다. 이 타입은 `normalizeContext()`만 만들 수 있어서(brand), 변환하지 않은 `Context`가 실수로 들어가는 것을 막는다.

**왜 변환하나: AI 회사마다 지침을 넣는 자리가 다르기 때문이다** (`코드 확인`: `utils/transcript.ts:52-55`의 주석, 회사별 형식은 일반적인 API 형식이며 api별 코드는 아직 `미확인`)
```
OpenAI식:    messages: [ {system: "지침"}, {user: "질문"} ]     ← 지침이 대화 안에 있음
Anthropic식: system: "지침", messages: [ {user: "질문"} ]        ← 지침이 대화 밖에 따로 있음
```
- pi-ai는 여러 회사의 모델을 같은 방식으로 다루려는 패키지라서, 입력을 한 가지 모양(`TranscriptContext`)으로 먼저 통일한다.
- provider는 그 통일된 모양에서 자기 회사 형식으로 옮기기만 한다. OpenAI식은 맨 앞 시스템 메시지를 그대로 쓰고, Anthropic식은 `withoutInitialSystemMessage()`로 맨 앞 메시지를 떼어 `system` 칸에 넣는다(주석: "프롬프트를 메시지 목록 밖에 두는 API용").
- 변환이 없으면 모든 provider가 `systemPrompt` 칸, 맨 앞 시스템 메시지, 중간 시스템 메시지를 각자 처리해야 한다. 그 정리를 `normalizeContext` 한 곳에서 한다.
- 대화 중간에 지침이 바뀌는 기능(`SystemMessage`의 `sections`, `toolsAdded`) 때문에 이 설계가 되었다는 해석은 `추론`이다.

### 2.4 호출 옵션 (상속 구조)
```
ProviderRequestOptions (132)  ← 통신 공통
   └ StreamOptions (187)        ← 생성 방식
        └ SimpleStreamOptions (350)  ← 추론 수준 등 간편 옵션
```

| 타입 | 역할 | 주요 인자 |
|---|---|---|
| `ProviderRequestOptions` | 인증과 HTTP 설정 | `signal`(취소), `apiKey`, `fetch`, `env`, `headers`, `timeoutMs`, `maxRetries`, `maxRetryDelayMs`, `onPayload`, `onResponse` |
| `StreamOptions` | 생성 방식 | `temperature`, `maxTokens`, `cacheRetention`, `sessionId`, `transport`, `samplingParams`(타입 `SamplingParams`), `metadata` |
| `SimpleStreamOptions` | 통일된 간편 옵션 | `reasoning`(추론 수준), `toolChoice`, `thinkingBudgets`, `deferred` |

작은 타입: `ThinkingLevel`(85, `minimal`/`low`/`medium`/`high`/`xhigh`/`max`), `CacheRetention`(110, `none`/`short`/`long`), `Transport`(118, `sse`/`websocket`/`websocket-cached`/`auto`), `ToolChoice`(84, `auto`/`none`).

### 2.5 모델 명세서: `Model` (1056~1168)

| 타입 | 역할 | 주요 인자 |
|---|---|---|
| `BaseModel` (1097) | 모든 모델의 공통 필드 | `id`, `name`, `api`, `provider`, `baseUrl`, `input`(text/image), `inputLimits`, `cost`, `headers` |
| `Model` (1111) | 대화용 모델 | 공통 필드 + `reasoning`(추론 지원 여부), `thinkingLevelMap`, `promptCache`, `contextWindow`, `maxTokens`, `samplingParams`, **`samplingParamsByThinkingLevel`**(추론 수준별 덮어쓰기, 새 필드), `compat` |
| `ImageModel` (1145) | 이미지 생성 모델 | 공통 필드 + `output` |
| `ClassifierModel` (1152) | 분류 모델 | 공통 필드 + `contextWindow` |
| `ModelCost` (1068) | 가격 ($/백만 토큰) | `input`, `output`, `cacheRead`, `cacheWrite`, `tiers`(입력 토큰 구간별 가격) |

`api`와 `provider`는 다른 값이다.
- `KnownApi`(17): 통신 방식 10종. 예: `anthropic-messages`, `openai-completions`
- `KnownProvider`(39): 회사 약 40종. 예: `anthropic`, `openai`
- 둘 다 `| (string & {})`가 붙어 있어 임의 문자열도 허용한다(확장 가능).

### 2.6 방언 메모: `*Compat` (789~967)
`Model.compat`에 들어간다. api에 따라 타입이 하나씩 정해지고(1131-1141), 해당 없는 api는 `never`다.

| 타입 | 대상 api | 대표 인자 |
|---|---|---|
| `OpenAICompletionsCompat` | `openai-completions` | `supportsDeveloperRole`, `maxTokensField`, `thinkingFormat`, `requiresToolResultName` (약 40개) |
| `OpenAIResponsesCompat` | `openai-responses` 외 2종 | `supportsLongCacheRetention`, `supportsStrictMode` |
| `AnthropicMessagesCompat` | `anthropic-messages` | `supportsTemperature`, `forceAdaptiveThinking`, `supportsCacheControlOnTools` |
| `BedrockCompat` | `bedrock-converse-stream` | `supportsStrictMode` |
| `MistralConversationsCompat` | `mistral-conversations` | `supportsMidConvoSystemMessages` |

대부분 "미지정이면 baseUrl로 자동 감지"라고 주석에 적혀 있다. 감지 코드는 아직 안 읽었다(`미확인`).

### 중간 정리: 호출은 `model` + `context` + `options`로 이루어진다
2.1~2.6의 타입이 호출에서 어디에 쓰이는지 한 장으로 묶었다. 근거는 `StreamFunction`의 시그니처(`types.ts:371-375`)이고, `코드 확인`이다.

```
streamSimple(model, context, options)  →  AssistantMessageEventStream (2.7, 알림 스트림)
             │       │        └ 2.4 SimpleStreamOptions  : 어떻게 (추론 수준, 길이, 인증, 제한 시간)
             │       └ 2.3 Context                       : 무엇을 (지침, 도구, 대화 기록)
             └ 2.5 Model                                 : 누구에게 (회사, 통신 방식, 가격, 방언)
```

| 인자 | 타입 | 한 줄 요약 |
|---|---|---|
| `model` | `Model` (2.5) | 명세서. `api`가 어느 통신 코드를 쓸지 정하고, `compat`(2.6)가 모델 고유의 방언을 알려 준다. |
| `context` | `Context` → `TranscriptContext` (2.3) | 보낼 내용. 지침과 도구를 `messages` 맨 앞 한 줄로 합쳐 provider에 넘긴다. 이 안의 메시지(2.1)에는 content 조각(2.2)이 들어 있다. |
| `options` | `SimpleStreamOptions` (2.4) | 호출 방식. `ProviderRequestOptions` → `StreamOptions` → `SimpleStreamOptions`의 3층 상속이다. |

헷갈리기 쉬운 구분
- **`Context` vs `TranscriptContext`**: 같은 내용이고, 지침과 도구를 두는 위치만 다르다(별도 칸 vs 맨 앞 `SystemMessage`). 대화 중간에 지침과 도구가 바뀔 수 있어서 내부는 후자로 통일한다.
- **`Tool` vs `ToolCall`**: `Tool`은 요청 전에 AI에게 알려 주는 도구 설명서이고, `ToolCall`은 AI가 답하면서 낸 실행 요청이다.
- **`stream` vs `streamSimple`**: `streamSimple`은 `reasoning: "high"` 같은 통일된 옵션을 받고 회사별 설정으로 바꿔 준다. 변환 코드는 아직 읽지 않았다(`미확인`).
- **`api` vs `provider`**: 통신 방식과 회사는 다른 값이다.

### 2.7 답변 도착 알림: `AssistantMessageEvent` (767)
12종이고, `done`과 `error`를 제외하고 모두 `partial`(지금까지 온 답)을 함께 가진다.

| 이벤트 | 시점 |
|---|---|
| `start` | 응답 시작 |
| `text_start` / `text_delta` / `text_end` | 글이 시작되고, 조각이 도착하고, 끝남 |
| `thinking_start` / `thinking_delta` / `thinking_end` | 추론에 대해 같은 3단계 |
| `toolcall_start` / `toolcall_delta` / `toolcall_end` | 도구 호출 요청에 대해 같은 3단계 (`end`에서 완성된 `toolCall` 전달) |
| `done` | 정상 종료. `reason`은 `stop`, `length`, `toolUse`, `deferred` 중 하나. `message` 포함 |
| `error` | 실패 종료. `reason`은 `aborted` 또는 `error`. `error`(AssistantMessage) 포함 |

`text_*`, `thinking_*`, `toolcall_*` 이벤트는 `contentIndex`(몇 번째 조각인지)도 가진다.

### 2.8 종료 사유와 사용량

| 타입 | 역할 | 값 / 인자 |
|---|---|---|
| `StopReason` (450) | 답이 끝난 이유 | `pending`, `stop`(정상), `length`(길이 초과), `toolUse`(도구 호출을 요청했음), `error`, `aborted`, `deferred` |
| `Usage` (427) | 사용량과 비용 | `input`, `output`, `cacheRead`, `cacheWrite`, `cacheWrite1h`, `reasoning`, `totalTokens`, `cost` |

### 2.9 함수 계약

| 타입 | 역할 |
|---|---|
| `StreamFunction` (371) | `(model, context, options) → AssistantMessageEventStream` 모양의 함수 타입 |
| `ProviderStreams` (286) | api 구현 모듈이 내보내야 하는 `stream`과 `streamSimple` (선택: `fetchDeferred`, `cancelDeferred`) |
| `ApiOptionsMap` (257) | api 이름별 전용 옵션 타입 대응표 |

### 2.10 부가 기능 타입 (대화와 무관)
- **이미지 생성**: `ImagesContext`, `ImagesOptions`, `AssistantImages`, `ProviderImages`
- **분류**: `ClassifierContext`(질문 3종: choice, score, bool), `ClassifierResult`, `ProviderClassifier`. `KnownClassifierApi`는 `typesafe-system-one`, `cloudflare-workers-ai-system-one`, `llama-cpp-classify`.
- **비동기 응답**: `DeferredHandle`(나중에 결과를 가져오기 위한 영수증)
- **도구 중첩 기록**: `NestedToolCalls`(572-592, 도구가 내부에서 다른 도구를 부른 기록. 모델에게는 보내지 않는다)

### 2.11 최종 정리: 타입과 함수로 본 호출 흐름
위에서 나온 타입과 함수를 한 번의 호출 순서로 엮었다. 함수 이름과 순서는 `models.ts`, `api/lazy.ts`, `utils/event-stream.ts`, README Quick Start에서 직접 확인했다(`코드 확인`). 각 단계의 내부 동작은 이후 문서에서 읽는다.

#### (1) 준비: `Model`을 구한다
```ts
const models = builtinModels();                        // providers/all.ts:184, 모든 내장 provider를 모은 Models
const model  = models.getModel("openai", "gpt-4o-mini"); // models.ts:472, → Model (2.5)
```
`Models`는 모델 목록과 호출 진입점을 가진 객체다. 아직 이 문서의 카탈로그에는 없는 타입이며 `models.ts` 단계에서 다룬다.

#### (2) 입력을 만든다: `Context`
```ts
const context: Context = {                   // 2.3
  systemPrompt: "You are a helpful assistant.",
  tools: [ { name: "get_time", description: "...", parameters: Type.Object({...}) } ],   // Tool
  messages: [ { role: "user", content: "지금 몇 시야?", timestamp: Date.now() } ],       // UserMessage (2.1)
};
```

#### (3) 호출한다: 4가지 함수 중 하나
| | 이벤트를 받음 | 최종 답만 받음 |
|---|---|---|
| api 전용 옵션 | `models.stream(model, context, options)` | `models.complete(...)` |
| 간편 옵션 (`SimpleStreamOptions`) | `models.streamSimple(...)` | `models.completeSimple(...)` |

반환 타입: `stream*`은 `AssistantMessageEventStream`, `complete*`는 `Promise<AssistantMessage>` (`models.ts:310-323`). `complete*`는 내부에서 `stream*(...).result()`를 부르는 포장이다(`models.ts:887-889, 904-911`).

#### (4) 내부에서 일어나는 일 (`models.ts:880-915`, `api/lazy.ts`)
```
models.streamSimple(model, context, options)
 1. normalizeContext(context)        Context → TranscriptContext   (지침과 도구를 맨 앞 SystemMessage로)
 2. lazyStream(model, setup)         빈 AssistantMessageEventStream을 즉시 반환하고, 준비는 뒤에서 비동기로 진행
      └ setup:
         a. requireChatProvider(model)   model.provider에 해당하는 provider를 찾는다
         b. applyAuth(model, options)    API 키 등 인증을 확정한다
         c. provider.streamSimple(...)   provider가 model.api에 해당하는 통신 코드(api/*.ts)를 불러 호출한다
      └ 안쪽 스트림의 이벤트를 바깥 스트림으로 전달(forwardStream)하고 끝나면 end()
```
- 호출한 쪽은 반환된 스트림을 곧바로 `for await`로 기다릴 수 있다. 인증과 통신 코드 불러오기는 그 뒤에서 일어난다.
- 준비 중 실패(인증 오류, 코드 로딩 오류)는 예외로 던지지 않고, `stopReason: "error"`인 `AssistantMessage`를 담은 `error` 이벤트로 스트림에 넣는다(`lazy.ts:5-23, 44-56`).

#### (5) 응답: 이벤트가 도착한다 (2.7)
```
start → text_start → text_delta × N → text_end
      → toolcall_start → toolcall_delta × N → toolcall_end
      → done(reason, message)  또는  error(reason, error)
```
- 스트림은 `AsyncIterable`이라 `for await (const event of s)`로 받는다(`event-stream.ts:68-82`).
- `done` 또는 `error` 이벤트가 오면 스트림이 끝나고, 그 안의 `AssistantMessage`가 최종 결과가 된다(`event-stream.ts:91-104`).
- `await s.result()`는 그 최종 `AssistantMessage`를 준다. 이 Promise는 reject하지 않고 resolve만 한다(`event-stream.ts:86`, `finalResultPromise`는 resolve 함수만 갖는다). 실패한 경우에도 `stopReason: "error"`, `errorMessage`가 담긴 메시지가 반환된다. 그래서 `complete*`도 실패를 예외가 아니라 메시지의 `stopReason`으로 알린다. 앞에서 `미확인`으로 남겼던 질문의 답이다.

#### (6) 도구 호출이 오면: `ai`는 여기까지
- `stopReason`이 `"toolUse"`이면 답에 `ToolCall`이 들어 있다는 뜻이다. `ai`는 이 답을 돌려주는 데까지만 한다.
- 도구를 실행하고 결과(`ToolResultMessage`)를 붙여 다시 호출하는 반복은 `agent` 패키지가 한다. 자세한 내용은 [Q5](../questions/q5-agent-loop.md)를 참고하되, 이 commit에서 `agent`가 크게 바뀌었으므로 재검증이 필요하다([00-role](./00-role.md) §7).
- README Quick Start는 `ai`만 쓸 때 이 반복을 직접 하는 예시를 보여 준다.

#### 전체 한 장 요약
```
[준비]  builtinModels() → models.getModel() ─────────────► Model                (2.5, 2.6)
[입력]  systemPrompt + tools + messages ────────────────► Context               (2.1, 2.2, 2.3)
[옵션]  reasoning, maxTokens, apiKey, signal ───────────► SimpleStreamOptions   (2.4)
                    │
[호출]  models.streamSimple(model, context, options)
                    │ normalizeContext → lazyStream → 인증 → provider → api/*.ts → 외부 AI 서비스
                    ▼
[응답]  AssistantMessageEventStream: start … *_delta … done | error            (2.7)
                    │ .result()
                    ▼
        AssistantMessage { content[글|추론|도구호출], usage, stopReason }       (2.1, 2.8)
                    │ (도구 호출이 있으면) 실행 후 ToolResultMessage를 붙여 다시 호출
                    ▼
        context.messages에 추가 → 다음 호출
```

## 3. 설계 포인트

1. **api와 provider는 별개 축이다.** `Model`과 `AssistantMessage`가 둘 다 기록한다(1097-1108, 547-549). 모델을 바꿔도 이전 답의 출처를 알 수 있다는 점은 코드에서 읽은 구조이고, 그것이 설계 의도라는 해석은 `추론`이다.
2. **`TranscriptContext`는 brand 타입이다.** `unique symbol` 필드(738-749) 때문에 `normalizeContext()`만 만들 수 있다. 다듬지 않은 입력이 provider 코드로 들어가는 실수를 타입이 막는다.
3. **시스템 프롬프트와 도구는 대화 안에서 바뀐다.** 모든 system 메시지를 순서대로 재생하면 현재 지침과 도구 집합이 된다(522-538). 중간 system 메시지를 못 받는 모델은 `supportsMidConvoSystemMessages` 플래그가 false이고, 이때 맨 앞 메시지를 재구성한다고 주석에 적혀 있다. 폴백 구현은 `미확인`이다.
4. **오류도 스트림으로 전달한다.** 스트림이 반환된 뒤의 실패는 `error` 이벤트와 `stopReason: "error" | "aborted"`로 표현한다. 인증 누락만 동기 throw가 허용된다(360-370, 751-766). 단 이것은 **통신 코드 모듈의 `streamSimple`을 직접 부를 때**의 규칙이다. `Models.streamSimple`을 거치면 인증 확정이 `lazyStream` 안에서 일어나서 인증이 없어도 던지지 않고 `error` 이벤트가 된다([06 §4](./06-call-flow.md), [03-1 §3](./03-1-api-anthropic.md)).
5. **`partial`은 공유 참조다.** "이벤트 시점의 스냅샷이 아니라 live helper"라고 명시되어 있다(760-761). 이벤트를 저장해 두면 나중에 값이 바뀔 수 있다.
6. **`Usage.reasoning`은 `output`의 부분집합이다**(435-439). 출력 100토큰 중 40이 추론이면 `output=100, reasoning=40`이다. 더하면 이중 계산이 된다. `cacheWrite1h`도 `cacheWrite`의 부분집합이다(432-433).
7. **`ToolResultMessage<TDetails>`는 JSON 직렬화 가능성을 타입으로 강제한다.** `TDetails`가 JSON이 아니면 `never`가 된다(455-485, 594). 세션 저장을 전제로 한 설계로 보이며 이는 `추론`이다.
8. **Deferred 응답**: `SimpleStreamOptions.deferred`, `StopReason "deferred"`, `DeferredHandle`, `ProviderStreams.fetchDeferred`/`cancelDeferred`가 한 세트다. 이 commit에서 실제 구현 provider는 확인하지 않았다(`미확인`).

## 4. 기존 Q4와의 대조
- Q4의 `TranscriptContext` brand 설명과 일치한다(`types.ts:744-747`).
- Q4에 없던 내용: `SystemMessage`의 `sections`/`toolsAdded`/`toolsRemoved`, `NestedToolCalls`, `Model.inputLimits`, `ModelCost.tiers`.

## 5. 남은 질문 (다음 단계)
- `normalizeContext`는 `systemPrompt`와 `tools`를 어떻게 system 메시지로 접는가? → `utils/transcript.ts`
- `AssistantMessageEventStream`은 어떻게 구현되는가? → `utils/event-stream.ts`
- compat 자동 감지는 어디서 일어나는가? → `compat.ts`, `api/openai-completions.ts`
- 중간 system 메시지를 지원하지 않는 provider는 어떻게 합치는가?
