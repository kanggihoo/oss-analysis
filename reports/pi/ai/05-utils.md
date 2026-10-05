# ai 05: `utils/` — 03에서 이름만 나온 보조 코드들

- **기준 commit**: `3874b3e98` / **분석일**: 2026-10-05
- **선행 문서**: [03-0-event-stream](./03-0-event-stream.md), [03-1-api-anthropic](./03-1-api-anthropic.md), [03-2-api-openai-responses](./03-2-api-openai-responses.md), [01-types](./01-types.md)
- **읽은 파일**: `src/utils/` 아래 `provider-retry.ts`(125줄), `retry.ts`(252줄), `overflow.ts`(188줄), `estimate.ts`(117줄), `json-parse.ts`(124줄), `validation.ts`(350줄), `error-body.ts`(149줄), `diagnostics.ts`, `models-error.ts`, `abort.ts`, `abort-signals.ts`, `sleep.ts`, `text.ts`, `sanitize-unicode.ts`, `hash.ts`, `uuid.ts`, `headers.ts`, `provider-env.ts`, `pi-user-agent.ts`, `model-operations.ts`, `typebox-helpers.ts`, `event-stream.ts`(03-0), `transcript.ts`(01, 03-1). `assistant-message-frame.ts`(490줄)는 앞 70줄만. 사용처는 `grep`과 `coding-agent/src/core/agent-session.ts`의 일부(`:2948-2972`, `:3640-3760`)를 읽어 확인했다. 줄 번호는 모두 이 commit 기준이다.
- **검증 수준**: 코드 읽기는 `코드 확인`. 재시도, 오버플로 판정, 토큰 추정, JSON 복구, 작은 도구들은 실제 파일을 불러서 돌렸다(`실행 확인`, §8). 단 `partial-json`과 `typebox`가 설치되어 있지 않아 **`parseStreamingJson`의 부분 해석과 `validateToolArguments`는 실행하지 못했다**(`미확인`).

## 0. 이 문서의 질문
- 03에서 본 `retryProviderRequest`, `parseStreamingJson`, `estimateContextTokens`, `isContextOverflow`, `validateToolArguments` 등은 정확히 무엇을 하는가?
- 03-4에서 "재시도는 이전에는 agent의 `harness`가 했다"는 Q4의 설명이 이 commit에서는 맞지 않았다. **지금은 누가 재시도하는가?**

## 1. 지도: 무엇이 어디에 있고 누가 쓰는가
| 묶음 | 파일 | 한 줄 역할 | 주요 사용처 |
|---|---|---|---|
| **재시도** | `provider-retry.ts` | 요청 한 번을 감싸서 일시 오류 때 다시 시도 | `api/anthropic-messages.ts:651`, `openai-responses.ts:183`, `openai-completions.ts:370` |
| 〃 | `retry.ts` | 실패한 **응답 메시지**가 재시도할 만한 오류인지 판정 + 재시도 반복문 | `coding-agent` `agent-session.ts`, `compaction.ts`, `durable` |
| **컨텍스트 크기** | `estimate.ts` | 대화가 몇 토큰인지 추정 | `api/simple-options.ts:17`, `coding-agent` |
| 〃 | `overflow.ts` | 응답이 "컨텍스트 초과"를 뜻하는지 판정 | `agent-session.ts:2956`, `durable/harness/generation.ts:457` |
| **JSON** | `json-parse.ts` | 깨진 JSON 복구, 잘린 JSON 해석 | 통신 코드의 도구 인자 해석 |
| 〃 | `validation.ts` | 도구 호출 인자가 스키마에 맞는지 검증하고 가능하면 형 변환 | `agent/src/agent-loop.ts:726`, `durable/harness/tool.ts:150` |
| **오류** | `error-body.ts` | SDK마다 다른 오류 객체에서 상태 코드와 본문을 꺼내 표시 문자열 만들기 | 통신 코드의 `catch` |
| 〃 | `diagnostics.ts` | `AssistantMessage.diagnostics`에 진단 기록 붙이기 | Codex 전송 실패 기록, Anthropic 입력 변형 기록 |
| 〃 | `models-error.ts` | `ModelsError`(코드가 있는 오류) | `models.ts`, `auth/resolve.ts` |
| **취소·대기** | `abort.ts`, `abort-signals.ts`, `sleep.ts` | 취소 신호 처리와 취소 가능한 대기 | `models.ts`, 인증, Codex |
| **문자열·환경** | `text.ts`, `sanitize-unicode.ts`, `hash.ts`, `uuid.ts`, `headers.ts`, `provider-env.ts`, `pi-user-agent.ts` | 작은 도구들 | 통신 코드 전반 |
| **모델 판별** | `model-operations.ts` | 모델 종류 확인과 오류 결과 만들기 | `models.ts` |
| 이미 본 것 | `event-stream.ts`(03-0), `transcript.ts`(01, 03-1) | | |
| 읽지 않은 것 | `assistant-message-frame.ts`, `node-http-proxy.ts`, `oauth-page.ts` | | §9 |

## 2. 재시도는 두 층이다

```
[1층] 요청 한 번 안에서      retryProviderRequest (provider-retry.ts)    통신 코드(api/*.ts)가 부름
         서버가 오류 상태 코드(503 등)를 돌려주면 같은 요청을 다시 보낸다. 응답이 시작되기 전 단계.

[2층] 응답 메시지 단위       isRetryableAssistantError / retryAssistantCall (retry.ts)
         스트림이 끝난 뒤 stopReason="error"인 AssistantMessage를 보고 "이 턴을 다시 시작할까?"를 정한다.
         ai 패키지는 판정 함수와 반복문만 제공하고, 실제로 부르는 것은 coding-agent와 durable이다.
```

### 2.1 1층: `retryProviderRequest` (`provider-retry.ts`)
통신 코드가 요청을 보낼 때 감싼다(03-1 §1.2, 03-2 §1.2).
```ts
const response = await retryProviderRequest(
    () => client.beta.messages.create(params, requestOptions).asResponse(),
    { maxRetries: options?.maxRetries, maxRetryDelayMs: options?.maxRetryDelayMs, signal: options?.signal },
);
```
**왜 SDK의 재시도를 끄고 직접 하는가** (주석 `:22`, `:97-104`): "OpenAI와 Anthropic SDK의 재시도를 그대로 재현하되, 대기를 취소할 수 있게 만든다. SDK의 내장 재시도 타이머는 요청의 `AbortSignal`을 무시하므로 SDK는 `maxRetries: 0`으로 부르고 이 함수로 감싸야 한다." 그래서 03의 통신 코드에 `maxRetries: 0`이 있었다.

| 규칙 | 줄 | 내용 |
|---|---|---|
| **기본 횟수** | `:109` | `maxRetries ?? 0`. **주지 않으면 재시도하지 않는다.** |
| **재시도 대상** (`isRetryableProviderError`) | `:23-35` | 서버가 `x-should-retry: true/false` 헤더를 주면 그대로 따른다. 없으면 **상태 코드가 없는 오류(연결 실패 등)**, **408, 409, 429, 500 이상**이면 재시도. 그 외(400, 401 등)는 바로 실패 |
| **대기 시간** | `:51-67` | ① `retry-after-ms` 헤더 ② `retry-after` 헤더(초 또는 날짜) ③ 없으면 `min(0.5 × 2^횟수, 8)초`에 최대 25%를 줄이는 지터 |
| **긴 대기는 거부** | `:37-49` | 서버가 요청한 대기가 `maxRetryDelayMs`(기본 60초, 0이면 제한 없음)보다 길면 재시도하지 않고 즉시 실패: `"Server requested 120s retry delay (max: 60s). ..."` |
| **취소** | `:75-95`, `:117` | 대기 중에도 `signal`이 오면 즉시 중단(`AbortError`) |
| **SDK 호환** | `:114` 주석 | 재시도마다 새 SDK 요청이라 `X-Stainless-Retry-Count` 헤더는 계속 0이다. |

- **Codex 통신 코드는 이것을 쓰지 않고 자체 반복문을 쓴다**(03-4 §6.2). `openai-completions.ts`와 `openai-responses.ts`, `anthropic-messages.ts`는 쓴다.
- 이 파일이 던지는 "Server requested ... retry delay" 오류 문구는 2층의 재시도 대상 패턴(`"retry delay"`, `retry.ts:87`)에 들어 있다. 주석: "제공자가 요청한 대기 상한 실패는 바깥의 재시도 정책으로 흘러가서, 호출자가 대기를 사용자에게 보이거나 중단할 수 있게 한다(#1123)."

### 2.2 2층: `retry.ts`

**(a) 재시도할 만한 오류인지 판정: `isRetryableAssistantError`** (`:247-252`)
```ts
if (message.stopReason !== "error" || !message.errorMessage) return false;
if (NON_RETRYABLE_PROVIDER_LIMIT_ERROR_PATTERN.test(errorMessage)) return false;   // 먼저: 한도 소진은 재시도 불가
return RETRYABLE_PROVIDER_ERROR_PATTERN.test(errorMessage);                         // 그다음: 일시 오류 문구
```
**판정 기준은 오류 메시지 문자열**이다(정규식).
| 분류 | 패턴 예 (`:7-28`, `:30-102`) |
|---|---|
| **재시도 불가**(우선 검사) | `GoUsageLimitError`, `Monthly usage limit reached`, `insufficient_quota`, `out of budget`, `quota exceeded`, `billing`, `subscription_sharing_usage_limit_exceeded`(ChatGPT 구독 한도, "몇 초가 아니라 몇 시간 뒤에 풀림") |
| **재시도 가능** | `overloaded`, `model is at capacity`, `rate limit`, `too many requests`, `429`/`500`/`502`/`503`/`504`, `service unavailable`, `server error`, 네트워크류(`fetch failed`, `connection refused`, `socket hang up`, `timeout`, `terminated`), WebSocket(`websocket closed`), **스트림이 중간에 끊긴 문구**(`ended without`, `stream ended before message_stop`, `stream ended before a terminal response event`), 서버가 "다시 시도하라"고 한 문구, ChatGPT 구독의 일시 오류(`subscription_sharing_usage_unavailable`) |
- 패턴 목록에는 어떤 이슈에서 추가했는지가 주석으로 남아 있다(예: `#2264`, `#3317`, `#4433`, `#6019`). 03-1에서 본 "stream ended before message_stop" 오류가 여기서 **재시도 대상**으로 분류된다는 점이 연결된다.
- **이 함수는 정책이 아니라 분류만 한다.** 주석: "컨텍스트 초과를 먼저 따로 처리한 뒤 호출자가 자기 재시도 예산과 대기를 적용한다."

**(b) 재시도 정책과 대기 시간** (`:104-127`)
```ts
interface RetryPolicy { enabled; maxRetries; baseDelayMs; maxAgentDelayMs? }
retryDelayMs(policy, attempt) = min( baseDelayMs × 2^(attempt-1), maxAgentDelayMs ?? 60_000 )
```
1회째 `baseDelayMs`, 2회째 2배, 3회째 4배, ...이고 60초에서 잘린다(§8에서 `baseDelayMs=1000`일 때 1, 2, 4, 8, 16, 32, 60초 확인). 주석: `coding-agent`의 `settings.retry`(`enabled`, `maxRetries`, `baseDelayMs`, `maxAgentDelayMs`)와 같은 모양이다.

**(c) 반복문: `retryAssistantCall`** (`:186-236`)
```
produce() 로 AssistantMessage 를 얻는다
  stopReason == "aborted"  → 반환 (취소는 재시도하지 않음)
  stopReason != "error"    → 반환 (성공)
  재시도 불가 또는 횟수 소진 → 반환 (마지막 오류 메시지)
  아니면 → 대기 후 produce() 다시   (대기 중 취소되면 aborted 로 바꿔 반환)
콜백: onRetryScheduled(몇 번째, 최대, 대기 ms, 오류) → 대기 → onRetryAttemptStart → onRetryFinished(성공 여부)
```
`policy`가 없거나 `enabled: false`이면 첫 응답을 그대로 반환한다(`produce()`를 직접 부르는 것과 같음).

### 2.3 그러면 지금은 누가 재시도하는가 (`코드 확인`)
**Q4의 설명("agent-core의 `harness/...`가 한다")은 이 commit에서는 틀렸다.** harness가 삭제되었고(00 §7), 이 commit에서 2층 재시도를 부르는 곳은 아래 세 곳이다.
| 곳 | 위치 | 하는 일 |
|---|---|---|
| **`coding-agent`: 에이전트 턴 재시도** | `core/agent-session.ts`: 호출 지점 `_handlePostAgentRun` `:1805-1822`, 판정 `_isRetryableError` `:3660-3663`, 준비 `_prepareRetry` `:3713-3756` | 에이전트 실행이 끝난 뒤 `_handlePostAgentRun`이 `_isRetryableError(message) && await _prepareRetry(message)`를 부르고(`:1817`), `_isRetryableError`가 **먼저 컨텍스트 초과인지 보고(초과면 재시도 대신 압축으로 처리), 아니면 `isRetryableAssistantError`로 판정**한다(`:3662-3663`). `_prepareRetry`가 `settings.retry`를 읽어(`enabled`, `maxRetries`) 횟수를 세고, `retryDelayMs(settings, 시도횟수)`로 대기 시간을 정하고, `auto_retry_start` 이벤트를 내보내고, 실패한 시도를 모델 입력에서 빼고(`_omitRecoveryAttempt`), 취소 가능한 `sleep`으로 기다린 뒤 `true`를 돌려준다(그러면 호출자가 에이전트를 다시 이어 간다). |
| **`coding-agent`: 요약 호출** | `core/compaction/compaction.ts:614-638` | 대화 요약(compaction)과 브랜치 요약의 LLM 호출을 `retryAssistantCall`로 감싼다. 같은 `settings.retry` 예산을 쓴다(`agent-session.ts:3666-3669` 주석). |
| **`durable` 패키지** | `harness/generation.ts:457-479`, `harness/compaction.ts:179` | `isContextOverflow`, `isRetryableAssistantError`, `retryDelayMs`를 직접 사용 |
- `agent` 패키지의 `agent-loop.ts`에는 재시도 코드가 없다(`grep`으로 `retry` 판정 함수를 부르는 곳이 없음을 확인).
- 3층으로 정리하면 **통신 코드(요청 재시도, 응답 시작 전) → `coding-agent`(응답 단위 재시도, 대기 이벤트로 화면에 표시)**다. 같은 일시 오류에 두 번 재시도가 겹칠 수 있는지(1층에서 `maxRetries`를 몇으로 넘기는지)는 확인하지 않았다(`미확인`).

## 3. 컨텍스트 크기

### 3.1 토큰 추정: `estimate.ts`
**실제 토큰 수는 서버만 안다.** 그래서 대화가 몇 토큰인지 미리 알아야 할 때(예: 출력 길이를 줄이거나 압축할 때)는 추정한다.
| 함수 | 줄 | 하는 일 |
|---|---|---|
| `estimateTextTokens(text)` | `:38-40` | `ceil(글자 수 / 4)` (`CHARS_PER_TOKEN = 4`) |
| `estimateMessageTokens(message)` | `:46-69` | 메시지 하나 추정. 이미지 한 장은 **4800글자 = 1200토큰**으로 침(`ESTIMATED_IMAGE_CHARS`). 도구 호출은 이름 + 인자 JSON 글자 수. 시스템 메시지는 도구 추가/제거 JSON까지 |
| `estimateContextTokens(context)` | `:97-112` | **마지막 응답의 `usage` + 그 뒤에 추가된 메시지 추정** |

`estimateContextTokens`의 요령(`:71-112`): 가장 최근 `assistant` 메시지의 **서버가 보고한 `usage.totalTokens`**를 기준으로 삼고, 그 뒤에 쌓인 메시지(`trailing`)만 글자 수로 추정해 더한다. 서버 값이 더 정확하기 때문이다. 단 아래 응답의 usage는 기준으로 쓰지 않는다.
- `aborted`나 `error`로 끝난 응답
- **그 응답 뒤에 더 늦은 시각의 메시지가 끼어든 경우**(주석: 압축 요약이 삽입되면 이전 응답의 usage는 지금의 앞부분을 설명하지 못한다)
- 사용량 기록이 하나도 없으면 전체를 글자 수 / 4로 추정한다.

**쓰이는 곳**: `api/simple-options.ts:17`의 `clampMaxTokensToContext`가 `model.contextWindow - 추정 토큰 - 4096`으로 **한 번에 받을 수 있는 출력 최대치를 자른다**(03-1 §3의 `buildBaseOptions`). 대화가 길수록 출력 한도가 줄어든다. `coding-agent`에도 같은 이름의 `estimateContextTokens`(`compaction.ts:196`, `AgentMessage` 기준)가 따로 있다(읽지 않음, `미확인`).

### 3.2 컨텍스트 초과 판정: `overflow.ts`
**문제**: 입력이 모델의 컨텍스트 창을 넘으면 서버마다 다른 문구로 오류를 낸다. `isContextOverflow(message, contextWindow?)`가 그것을 한 함수로 판정한다(`:137-171`). **세 가지 경우**를 본다.
| 경우 | 조건 | 예 |
|---|---|---|
| **1. 오류 문구** | `stopReason == "error"`이고 문구가 `OVERFLOW_PATTERNS` 25개 중 하나와 맞음 | Anthropic `prompt is too long: 213462 tokens > 200000 maximum`, OpenAI `exceeds the context window`, Google `input token count ... exceeds the maximum`, xAI, OpenRouter, llama.cpp, Mistral 등 서버별 문구(주석 `:9-35`가 서버별 예시 목록) |
| **2. 조용한 초과** | `contextWindow`를 주었고 `stopReason == "stop"`인데 `input + cacheRead > contextWindow` | z.ai처럼 초과를 거부하지 않고 받아 주는 서버 |
| **3. 길이 종료 초과** | `contextWindow`를 주었고 `stopReason == "length"`, `output == 0`, `input + cacheRead ≥ contextWindow × 0.99` | Xiaomi MiMo: 입력을 창에 맞게 잘라서 출력 자리가 없다 |

- **제외 규칙** (`NON_OVERFLOW_PATTERNS`, `:76-80`): `rate limit`, `too many requests`, Bedrock의 `Throttling error:` 접두사가 있으면 초과가 아니라고 본다. 주석: Bedrock이 "Too many tokens, please wait before trying again."라고 속도 제한 오류를 내는데 이것이 `too many tokens` 패턴과 맞아 초과로 오인되기 때문이다.
- Cerebras는 오류 본문이 없어서 `400`/`413 (no body)`일 때만 초과로 본다(`:65`, `:146-148`).
- 정규식은 **오류 문구가 서버 설정과 버전에 따라 달라지면 놓칠 수 있다.** 커스텀 provider를 추가했을 때는 이 파일의 패턴을 늘리거나 호출자가 직접 확인해야 한다고 주석이 안내한다(`:122-131`).
- `isRecoverableLength(message, desiredMaxOutput)` (`:179-181`): `length`로 끝났는데 출력이 원래 원하던 최대치보다 적으면 컨텍스트 압력이나 서버의 잘림일 수 있어 **한 번 압축하고 재시도**해 볼 수 있다는 판정이다.
- **쓰이는 곳**: `agent-session.ts:2956-2962`(`explicitOverflow`, `contextOverflow`, `recoverableLength`로 자동 압축 결정), `durable/harness/generation.ts:457`. 압축을 하면 재시도 대신 압축으로 처리한다(`_isRetryableError`가 초과를 먼저 걸러내는 이유, §2.3).

## 4. JSON

### 4.1 깨진 JSON 복구: `json-parse.ts`
- **`repairJson`** (`:32-83`): 문자열 안에서만 두 가지를 고친다. ① **실제 제어 문자**(줄바꿈 등)를 `\n` 같은 이스케이프로 바꾼다. ② **잘못된 이스케이프**(`\U` 등) 앞의 역슬래시를 두 번으로 만든다. 문자열 밖은 건드리지 않는다. 모델이 도구 인자를 만들 때 Windows 경로(`C:\Users\x`)나 문자열 안의 줄바꿈을 규칙 없이 써서 JSON이 깨지는 경우를 위한 것으로 보인다(`추론`).
- **`parseJsonWithRepair`** (`:85-95`): 먼저 `JSON.parse`, 실패하면 `repairJson` 후 다시 시도, 고쳐도 같으면 원래 오류를 던진다.
- **`parseStreamingJson`** (`:104-124`): 스트리밍 중 **잘린 JSON**을 항상 객체로 돌려준다(03-1 §5.2의 `toolcall_delta`). 순서는 `parseJsonWithRepair` → 실패하면 `partial-json` 라이브러리로 부분 해석 → 실패하면 `repairJson` 후 부분 해석 → 그래도 실패하면 `{}`. **어떤 입력에도 예외를 던지지 않는다.** `partial-json`의 동작 자체는 실행하지 못했다(`미확인`).

### 4.2 도구 인자 검증: `validation.ts`
AI가 만든 도구 호출 인자가 도구의 스키마에 맞는지 확인한다. `validateToolArguments(tool, toolCall)` (`:317-350`)의 흐름:
```
1. args = structuredClone(toolCall.arguments)                       원본을 건드리지 않음
2. normalizeOptionalNulls(args, schema)    필수가 아닌 필드가 null 이고 스키마가 null 을 허용하지 않으면 그 필드를 삭제   (:240-269)
3. Value.Convert(schema, args)             TypeBox 의 형 변환 (문자열 "3" → 숫자 3 등)
4. 스키마가 TypeBox 로 만든 것이 아니면(TypeBox.Kind 심볼이 없으면)
      coerceWithJsonSchema 로 직접 형 변환                                                                           (:323-335)
5. validator.Check(args) 가 true 이면 args 반환, 아니면
      오류 목록과 받은 인자를 담은 Error 를 던진다 ("Validation failed for tool ...")                                (:341-349)
```
- **관대하게 변환한다.** `coercePrimitiveByType`(`:59-131`)의 규칙: `number`는 `null → 0`, 숫자 문자열 → 숫자, `true/false → 1/0`. `boolean`은 `null → false`, `"true"/"false"` 문자열, `1/0`. `string`은 `null → ""`, 숫자/불리언 → 문자열. `null` 타입은 `""`, `0`, `false → null`. `anyOf`/`oneOf`는 먼저 그대로 맞는 후보를 찾고, 없으면 복사본을 변환해서 맞는 후보를 고른다(`:175-192`).
- 컴파일된 검증기는 스키마 객체를 키로 `WeakMap`에 캐시한다(`:6`, `:271-280`).
- 오류 경로 표시는 `a.b.c` 형태이고, 필수 필드가 없으면 그 필드 이름까지 붙인다(`formatValidationPath`, `:282-293`).
- `validateToolCall(tools, toolCall)`는 이름으로 도구를 찾고(없으면 `Tool "x" not found`) 위를 부른다(`:302-308`).
- **쓰이는 곳**: `agent/src/agent-loop.ts:726`(`validateToolArguments(tool, preparedToolCall)`), `durable/harness/tool.ts:150`. 즉 도구를 실행하기 전의 마지막 관문이다.
- `typebox`가 설치되어 있지 않아 **실제로 돌려 보지 못했다**(`미확인`). 위 설명은 코드 읽기이다.

## 5. 오류 정리

### 5.1 `error-body.ts`: SDK마다 다른 오류 객체를 한 모양으로
**문제**: 게이트웨이나 프록시 뒤에서 서버가 비정상 응답을 주면 SDK가 본문을 오류 메시지에 합쳐 주지 못해 `"403 status code (no body)"` 같은 불투명한 메시지가 된다. 본문은 SDK 오류 객체의 **SDK마다 다른 필드 이름**에 들어 있다.
- `normalizeProviderError(error)` (`:38-54`)가 알려진 모양을 순서대로 본다.
  - 상태 코드: `statusCode`(Mistral) → `status`(`openai`, `@google/genai`) → `$metadata.httpStatusCode`(Bedrock) → `$response.statusCode`(Bedrock)
  - 본문: `body` 문자열(Mistral) → `error` 객체(`openai`의 파싱된 본문) → `$response.body`(Bedrock). 빈 객체와 아직 읽지 않은 스트림은 본문이 아니라고 본다. **일반 객체(plain object)만** 본문으로 인정한다(주석 `:98-111`: AWS SDK의 `$response.body`는 HTTP 스트림 래퍼라서 문자열로 만들면 `{"_events":...}` 같은 쓰레기가 되어 진짜 메시지를 덮어쓴다).
  - 본문은 4000글자(`MAX_PROVIDER_ERROR_BODY_CHARS`)로 자른다.
- `formatProviderError(norm, prefix?)` (`:128-135`): 메시지에 본문이 이미 있거나 상태·본문을 못 찾았으면 메시지를 그대로, 아니면 `"<prefix> (<상태>): <본문>"`. §8 실험에서 `403 status code (no body)` + `error: {error:{message:"blocked by gateway"}}`가 `OpenAI API error (403): {"error":{"message":"blocked by gateway"}}`가 되었다.
- **쓰이는 곳**: 03-1, 03-2, 03-3, 03-4의 통신 코드 `catch`(`formatProviderError(normalizeProviderError(error))`).

### 5.2 `diagnostics.ts`와 `models-error.ts`
- **`AssistantMessageDiagnostic`** (`diagnostics.ts:10-15`): `{ type, timestamp, error?, details? }`. `appendAssistantMessageDiagnostic(message, diagnostic)`가 `AssistantMessage.diagnostics`에 붙인다. 쓰이는 예: Codex의 `provider_transport_failure`(03-4 §5.1), Anthropic의 `anthropic_input_transformations`(03-1 §3).
- **`ModelsError`** (`models-error.ts`): 코드가 있는 오류. 코드는 6가지다: `model_source`, `model_validation`, `provider`, `stream`, `auth`, `oauth`. 생성자가 `cause`의 내용을 메시지 뒤에 붙인다. 주석: "호출자가 `error.message`만 보여 주므로 원인을 메시지에 남긴다."

## 6. 취소와 대기
- **`operationSignal(signal?)`** (`abort.ts:9-11`): 선택 인자인 신호가 없으면 새 `AbortController`의 신호를 만든다. 공개 API가 신호 유무를 신경 쓰지 않아도 되게 한다.
- **`raceWithAbortSignal(operation, signal)`** (`abort.ts:17-50`): 작업과 취소 신호를 경주시킨다. 신호가 먼저 오면 reject하되, **버려진 작업의 이후 실패를 조용히 처리**해서 처리되지 않은 reject가 남지 않게 한다(주석). `models.ts`와 인증 코드가 쓴다.
- **`combineAbortSignals(signals)`** (`abort-signals.ts`): 여러 신호를 하나로 합친다. 하나가 취소되면 합쳐진 신호도 취소되고, `cleanup()`으로 리스너를 정리한다. Codex가 호출자 취소와 헤더 제한 시간을 합칠 때 쓴다(03-4 `:398`).
- **`sleep(ms, signal)`** (`sleep.ts`): 취소 가능한 대기. 이 이름의 함수가 `retry.ts`, `provider-retry.ts`, `openai-codex-responses.ts`에도 각자 복사되어 있다(`abortableSleep` 등, 중복으로 보이며 이유는 `미확인`).

## 7. 작은 도구들
| 파일 | 하는 일 |
|---|---|
| `text.ts` | `contentText`(글 블록 이어 붙이기), `getSystemMessageText`(시스템 메시지의 본문 + 섹션을 한 프롬프트로), `renderSystemMessageUpdate`(나중 시스템 메시지를 `Updated system prompt section "이름":` / `Removed system prompt section "이름".` 형태로 표현. 주석: 요청 시점 전용이며 버전에 따라 바뀔 수 있음) |
| `sanitize-unicode.ts` | **짝이 맞지 않는 서로게이트 문자**만 제거한다(짝이 맞는 이모지는 유지). 홀로 남은 서로게이트가 있으면 많은 서버에서 JSON 직렬화 오류가 난다(주석). 03의 통신 코드가 글을 요청에 넣을 때마다 부른다. |
| `hash.ts` | `shortHash(str)`: 빠른 **비암호용** 해시(두 개의 32비트 값을 36진수로 이어 붙임). 긴 ID를 줄일 때 쓴다(예: 40자를 넘는 도구 호출 ID, 03-3 §3.3). 암호학적 용도가 아니다. |
| `uuid.ts` | `uuidv7(timestampMs?)`: **시간순으로 정렬되는 UUIDv7**. 같은 밀리초 안에서도 순서가 유지되도록 증가하는 순번을 넣는다. |
| `headers.ts` | `headersToRecord`(`Headers` → 객체), `providerHeadersToRecord(...출처들)`: **헤더 이름의 대소문자를 무시하고 뒤의 것이 앞을 덮어쓰며 값이 `null`이면 삭제**(01에서 본 "null이면 기본 헤더 제거"의 구현) |
| `provider-env.ts` | `getProviderEnvValue(name, env?)`: 우선순위 **호출 옵션의 `env` → `process.env` → Bun 샌드박스 대체(`/proc/self/environ` 읽기)**. Bun으로 컴파일한 실행 파일이 리눅스 샌드박스에서 `process.env`가 비어 있는 문제의 우회(주석, 이슈 `oven-sh/bun#27802`) |
| `pi-user-agent.ts` | `pi (<OS> <버전>; <아키텍처>)`, 브라우저면 `pi (browser)`. 브라우저 번들을 깨지 않도록 `node:os`를 런타임에 동적으로 읽는다(주석). 03의 `User-Agent` 헤더 |
| `model-operations.ts` | `getModelType`(`type`이 없으면 `"chat"`), `isModelType`, `assertChatModel` 등(틀리면 `ModelsError("provider")`), 이미지/분류 호출 실패 때 에러가 담긴 결과 객체 만들기(`imageErrorResult`, `classifierErrorResult`, 02 §4.6) |
| `typebox-helpers.ts` | `StringEnum(values, opts)`: 문자열 열거형 스키마. 주석: Google 등 `anyOf`/`const`를 지원하지 않는 서버와 호환되는 형태 |

## 8. 실험: 실제 코드로 확인 (`실행 확인`)
`provider-retry.ts`, `retry.ts`, `overflow.ts`, `estimate.ts`, `sanitize-unicode.ts`, `hash.ts`, `uuid.ts`, `error-body.ts`를 **그대로 불러서** 돌렸다. `json-parse.ts`는 `partial-json`이 설치되어 있지 않아 `repairJson`/`parseJsonWithRepair`(`:3-95`)만 복사했다. 입력은 모두 가짜이고 실제 서버와 통신하지 않았다. 스크립트는 `artifacts/pi/ai-demos/utils-demo.ts`, 출력은 `utils-demo.2026-10-05.log`다.

**1. `retryProviderRequest`**
```
[+  10ms] 요청 1번째 시도
[+ 449ms] 요청 2번째 시도          ← 0.5초 × 지터(최대 -25%) 후
[+1223ms] 요청 3번째 시도          ← 1초 × 지터 후
→ 결과: 성공 (총 3번 시도, 503은 재시도 대상)
→ 400은 재시도하지 않고 바로 실패 (시도 1번)
→ 서버가 120초 대기를 요청하면 즉시 실패: Server requested 120s retry delay (max: 60s). Rate limited
→ maxRetries 를 안 주면 기본 0회라서 재시도 없음 (시도 1번)
```
**2. `isRetryableAssistantError`** (오류 문구 → 재시도 여부)
```
true  ← Anthropic: overloaded_error          true  ← fetch failed
true  ← 429 Too many requests                true  ← WebSocket closed 1006
false ← insufficient_quota: billing          false ← subscription_sharing_usage_limit_exceeded
false ← Validation failed for tool           false ← prompt is too long: 213462 tokens > 200000 maximum
```
- 마지막 줄(컨텍스트 초과)이 `false`인 것은 이 함수가 아니라 **호출자가 초과를 먼저 걸러내기 때문**이다(§2.3).

**3. `retryAssistantCall`** (`baseDelayMs: 100`, `maxRetries: 3`)
```
재시도 예약 1/3, 100ms 후 (model is at capacity)
재시도 예약 2/3, 200ms 후 (model is at capacity)
재시도 종료: 성공=true, 재시도 횟수=2
→ 최종 stopReason=stop, produce 호출 3번
→ 한도 소진 오류(insufficient_quota)는 재시도 없이 반환: produce 호출 1번
지연 시간 (baseDelayMs=1000): 1000, 2000, 4000, 8000, 16000, 32000, 60000ms   ← 60초에서 잘림
```
**4. `isContextOverflow`**
```
true  ← prompt is too long: 213462 tokens > 200000 maximum
true  ← Your input exceeds the context window of this model
true  ← The input token count (1196265) exceeds the maximum number of tokens allowed (1048575)
false ← Throttling error: Too many tokens, please wait before trying again.   (제외 규칙)
false ← rate limit: too many tokens per minute                                (제외 규칙)
false ← some unrelated error
조용한 초과(z.ai식): stopReason=stop, input 150000 > contextWindow 128000 → true
길이 종료 초과(MiMo식): stopReason=length, output=0, input 127500 ≥ 128000×0.99 → true
isRecoverableLength(length 종료, output 100 < 원하던 4000) → true
```
**5. `estimateContextTokens`**
```
마지막 응답이 보고한 토큰=1000, 그 뒤 추가된 메시지 추정=200 (800글자/4), 합계=1200
사용량 기록이 없으면 전부 글자수/4로 추정: 300 (1200글자/4)
```
**6. `parseJsonWithRepair`**
```
문자열 안의 실제 줄바꿈: {"a":"line1\nline2"}          ← 고쳐서 해석됨
잘못된 이스케이프:       {"p":"C:\\Users\\x"}            ← 고쳐서 해석됨
이미 올바른 JSON:        {"ok":true}
```
**7. 작은 도구들**
```
sanitizeSurrogates("Hi 🙈 \uD83D end") → "Hi 🙈  end"   (짝이 맞는 이모지는 유지, 홀로 남은 것만 제거)
shortHash("a"×500) → d33jejlgylnv                       (같은 입력은 항상 같은 값)
uuidv7 3개는 시간순으로 정렬 가능                         (정렬해도 순서가 같음)
오류 본문 복구: OpenAI API error (403): {"error":{"message":"blocked by gateway"}}
```

## 9. 읽지 않은 것 (`미확인`)
- `assistant-message-frame.ts`(490줄): 앞 70줄에서 `AssistantMessage`의 진행 상황을 **압축해서 재생 가능한 프레임**(`start`, `text_start`, `toolcall_checkpoint` 등)으로 담는 타입을 정의한다는 것과, 주석("종료 결과는 의도적으로 빠져 있으며 따로 저장해야 한다")만 확인했다. 쓰는 곳(저장, 복구)은 확인하지 않았다.
- `node-http-proxy.ts`(161줄), `oauth-page.ts`(109줄)
- `partial-json`의 부분 해석 동작, `typebox`의 `Value.Convert`와 `Compile`의 실제 동작(설치되어 있지 않아 실행하지 못함)
- `coding-agent`의 재시도 설정 기본값(`settings.retry`), `_omitRecoveryAttempt`, 자동 압축의 나머지, `compaction.ts`의 자체 `estimateContextTokens`
- 1층과 2층 재시도가 같은 오류에서 어떻게 겹치는지(1층 `maxRetries`를 호출자가 얼마로 넘기는지)

## 10. 다음
**06 호출 경로 종합**: 지금까지 본 조각(`types`, `Models`, `lazyStream`, `Provider`, 통신 코드, `EventStream`, 인증, `utils`)을 한 번의 호출에 순서대로 엮어서 정리한다. 그 뒤 `agent` 패키지로 넘어가며, 이 commit에서 `agent`가 크게 바뀌었으므로(00 §7) 이전 Q5, Q6을 새 기준으로 다시 확인해야 한다.
