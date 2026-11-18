# ai 05: `utils/` — 03에서 이름만 나온 보조 코드들

> **[2026-11-17 재검증]** `3874b3e98` → `4afe78de` 기준으로 `src/utils/` diff 전체와 현재 파일을 읽어 대조했다(실행 없음, 모두 `코드 확인`). 달라진 곳은 본문에 `[2026-11-17]`로 표시했다. 요약: ① `validation.ts` 350줄 → 69줄, 검증·형 변환이 `pi-schema`로 이동(§4.2) ② `streaming-json.ts`·`parseToolCallArguments` 추가(§4.1) ③ 재시도 패턴 대폭 추가, 상태 코드 패턴 정밀화(§2.2) ④ `CHARS_PER_TOKEN` 4 → 3.5(§3.1) ⑤ 삭제: `pi-user-agent.ts`, `assistant-message-frame.ts`(§7, §9) ⑥ `typebox-helpers.ts` → `string-enum.ts`. 줄 번호는 바뀐 파일만 새로 확인했고, diff가 없는 파일(`abort*.ts`, `hash.ts`, `uuid.ts`, `headers.ts`, `sanitize-unicode.ts` 등)은 그대로다. 문서 머리의 기준 SHA 표기와 §8 실행 결과는 이전 SHA 기준이다.

- **기준 commit**: `3874b3e98` / **분석일**: 2026-10-05
- **선행 문서**: [03-0-event-stream](./03-0-event-stream.md), [03-1-api-anthropic](./03-1-api-anthropic.md), [03-2-api-openai-responses](./03-2-api-openai-responses.md), [01-types](./01-types.md)
- **읽은 파일**: `src/utils/` 아래 `provider-retry.ts`(125줄), `retry.ts`(252줄), `overflow.ts`(188줄), `estimate.ts`(117줄), `json-parse.ts`(124줄), `validation.ts`(350줄), `error-body.ts`(149줄), `diagnostics.ts`, `models-error.ts`, `abort.ts`, `abort-signals.ts`, `sleep.ts`, `text.ts`, `sanitize-unicode.ts`, `hash.ts`, `uuid.ts`, `headers.ts`, `provider-env.ts`, `pi-user-agent.ts`, `model-operations.ts`, `typebox-helpers.ts`, `event-stream.ts`(03-0), `transcript.ts`(01, 03-1). `assistant-message-frame.ts`(490줄)는 앞 70줄만. 사용처는 `grep`과 `coding-agent/src/core/agent-session.ts`의 일부(`:2948-2972`, `:3640-3760`)를 읽어 확인했다. 줄 번호는 모두 이 commit 기준이다.
- **검증 수준**: 코드 읽기는 `코드 확인`. 재시도, 오버플로 판정, 토큰 추정, JSON 복구, 작은 도구들은 실제 파일을 불러서 돌렸다(`실행 확인`, §8). 다만 `partial-json`과 `typebox`가 설치되어 있지 않아 **`parseStreamingJson`의 부분 해석과 `validateToolArguments`는 실행하지 못했다**(`미확인`).

## 0. 이 문서의 질문
- 03에서 본 `retryProviderRequest`, `parseStreamingJson`, `estimateContextTokens`, `isContextOverflow`, `validateToolArguments` 등은 정확히 무엇을 하는가?
- Q4는 "재시도는 agent의 `harness`가 한다"고 설명했다. 03-4에서 보았듯 이 설명은 이 commit에서 맞지 않았다. **그러면 지금은 누가 재시도하는가?**

## 1. 지도: 무엇이 어디에 있고 누가 쓰는가
| 묶음 | 파일 | 한 줄 역할 | 주요 사용처 |
|---|---|---|---|
| **재시도** | `provider-retry.ts` | 요청 한 번을 감싸서 일시 오류 때 다시 시도 | `api/anthropic-messages.ts:885`, `openai-responses.ts:221`, `openai-completions.ts:384`, `azure-openai-responses.ts:91`, `google-shared.ts:545`, `classifier-shared.ts:77`, `llama-cpp-classify.ts:246`, `openrouter-images.ts:73` (`4afe78de` 기준, 앞의 셋만 이전 문서에 있었음) |
| 〃 | `retry.ts` | 실패한 **응답 메시지**가 재시도할 만한 오류인지 판정 + 재시도 반복문 | `coding-agent` `agent-session.ts`, `compaction.ts`, `durable` |
| **컨텍스트 크기** | `estimate.ts` | 대화가 몇 토큰인지 추정 | `api/simple-options.ts:17`, `coding-agent` |
| 〃 | `overflow.ts` | 응답이 "컨텍스트 초과"를 뜻하는지 판정 | `agent-session.ts:2956`, `durable/harness/generation.ts:457` |
| **JSON** | `json-parse.ts`, `streaming-json.ts`(새로) | 깨진 JSON 복구, 완성된 도구 인자 파싱(`parseToolCallArguments`), 스트리밍 중 잘린 JSON의 증분 해석 | 통신 코드의 도구 인자 해석 |
| 〃 | `validation.ts` | 도구 호출 인자 검증. 형 변환과 검사는 `pi-schema`가 한다(69줄짜리 얇은 래퍼) | `agent/src/agent-loop.ts:736`, `durable/src/harness/tool.ts:527` |
| **오류** | `error-body.ts` | SDK마다 다른 오류 객체에서 상태 코드와 본문을 꺼내 표시 문자열 만들기 | 통신 코드의 `catch` |
| 〃 | `diagnostics.ts` | `AssistantMessage.diagnostics`에 진단 기록 붙이기 | Codex 전송 실패 기록, Anthropic 입력 변형 기록 |
| 〃 | `models-error.ts` | `ModelsError`(코드가 있는 오류) | `models.ts`, `auth/resolve.ts` |
| **취소·대기** | `abort.ts`, `abort-signals.ts`, `sleep.ts` | 취소 신호 처리와 취소 가능한 대기 | `models.ts`, 인증, Codex |
| **문자열·환경** | `text.ts`, `sanitize-unicode.ts`, `hash.ts`, `uuid.ts`, `headers.ts`, `provider-env.ts` | 작은 도구들 | 통신 코드 전반 |
| **모델 판별** | `model-operations.ts` | 모델 종류 확인과 오류 결과 만들기 | `models.ts` |
| 이미 본 것 | `event-stream.ts`(03-0), `transcript.ts`(01, 03-1) | | |
| 새로 생김 | `identity.ts`(193줄), `openrouter-cost.ts`, `version.ts` | 읽지 않음 | §9 |
| 읽지 않은 것 | `node-http-proxy.ts`, `oauth-page.ts` | | §9 |

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
| **기본 횟수** | `:111` | `maxRetries ?? 0`. **주지 않으면 재시도하지 않는다.** |
| **재시도 대상** (`isRetryableProviderError`) | `:23-35` | 서버가 `x-should-retry: true/false` 헤더를 주면 그대로 따른다. 없으면 **상태 코드가 없는 오류(연결 실패 등)**, **408, 409, 429, 500 이상**이면 재시도. 그 외(400, 401 등)는 바로 실패 |
| **대기 시간** | `:51-67` | ① `retry-after-ms` 헤더 ② `retry-after` 헤더(초 또는 날짜) ③ 없으면 `min(0.5 × 2^횟수, 8)초`에 최대 25%를 줄이는 지터 |
| **긴 대기는 거부** | `:37-49` | 서버가 요청한 대기가 `maxRetryDelayMs`(기본 60초, 0이면 제한 없음)보다 길면 재시도하지 않고 즉시 실패: `"Server requested 120s retry delay (max: 60s). ..."` |
| **취소** | `:75-95`, `:117` | 대기 중에도 `signal`이 오면 즉시 중단(`AbortError`) |
| **SDK 호환** | `:114` 주석 | 재시도마다 새 SDK 요청이라 `X-Stainless-Retry-Count` 헤더는 계속 0이다. |

- **[2026-11-17] 새 옵션 `noRetryStatuses`**(`provider-retry.ts:7`, `:121`): 기본 정책이 재시도할 상태 코드라도 목록에 있으면 즉시 실패한다. 넘기는 곳은 `api/classifier-shared.ts:61-102`뿐이다(`grep`, `ai/src` 범위). 이 표의 나머지 줄 번호는 +2줄쯤 밀렸고 규칙 내용은 diff에 없다.
- **Codex 통신 코드는 이것을 쓰지 않고 자체 반복문을 쓴다**(03-4 §6.2). `openai-completions.ts`와 `openai-responses.ts`, `anthropic-messages.ts`는 쓴다.
- 이 파일이 던지는 "Server requested ... retry delay" 오류 문구는 2층의 재시도 대상 패턴(`"retry delay"`, `retry.ts:87`)에 들어 있다. 주석: "제공자가 요청한 대기 상한 실패는 바깥의 재시도 정책으로 흘러가서, 호출자가 대기를 사용자에게 보여 주거나 중단할 수 있게 한다(#1123)."

### 2.2 2층: `retry.ts`

**(a) 재시도할 만한 오류인지 판정: `isRetryableAssistantError`** (`retry.ts:284-289`)
```ts
if (message.stopReason !== "error" || !message.errorMessage) return false;
if (NON_RETRYABLE_PROVIDER_LIMIT_ERROR_PATTERN.test(errorMessage)) return false;   // 먼저: 한도 소진은 재시도 불가
return RETRYABLE_PROVIDER_ERROR_PATTERN.test(errorMessage);                         // 그다음: 일시 오류 문구
```
**판정 기준은 오류 메시지 문자열**이다(정규식).
| 분류 | 패턴 예 (`:7-28`, `:30-102`) |
|---|---|
| **재시도 불가**(우선 검사. **[2026-11-17] 추가**: `subscription_sharing_workplace_individual_usage_limit_exceeded`(ChatGPT Business 관리자 한도), Zhipu/Z.ai 코드 `1308`(HTTP 429로 오지만 몇 시간 뒤 풀림, #11537)) | `GoUsageLimitError`, `Monthly usage limit reached`, `insufficient_quota`, `out of budget`, `quota exceeded`, `billing`, `subscription_sharing_usage_limit_exceeded`(ChatGPT 구독 한도, "몇 초가 아니라 몇 시간 뒤에 풀림") |
| **재시도 가능** | `overloaded`, `model is at capacity`, `rate limit`, `too many requests`, `429`/`500`/`502`/`503`/`504`, `service unavailable`, `server error`, 네트워크류(`fetch failed`, `connection refused`, `socket hang up`, `timeout`, `terminated`), WebSocket(`websocket closed`), **스트림이 중간에 끊긴 문구**(`ended without`, `stream ended before message_stop`, `stream ended before a terminal response event`), 서버가 "다시 시도하라"고 한 문구, ChatGPT 구독의 일시 오류(`subscription_sharing_usage_unavailable`) |
- **[2026-11-17] 재시도 가능 패턴의 변화**(`retry.ts:38-130`): ① 상태 코드 `429|500|502|503|504|520|524`가 단순 부분 문자열에서 "앞뒤가 영숫자가 아닐 때만" 맞는 정규식으로 바뀌었다(요청 ID나 바이트 수 속 숫자 오탐 방지, #11057). ② 새로 추가: `server_busy`, `servers are currently busy`, `service is temporarily unavailable`(#10965), `provider returned an error`(#10842), `unable to forward upstream`, `upstream request failed`, `upstream_stream_read_error`, `stream was interrupted`, `http/2 stream failed`(#10920), `connection closed`(#12064), node-fetch `request to … failed, reason:`(#10996), 단독 Node 소켓 코드 `ECONNRESET|ECONNABORTED|ECONNREFUSED|ETIMEDOUT|EPIPE`(#12128), `connection reset by peer`, `websocket connection limit reached`(Codex 60분 연결 제한, #12124), `stream disconnected before completion`, `cut short after the reply had begun`(#11879). `pending stream has been canceled`(#10379)는 이전 문서에도 있었다.
- 패턴 목록에는 어떤 이슈에서 추가했는지가 주석으로 남아 있다(예: `#2264`, `#3317`, `#4433`, `#6019`, 새로 추가된 `#10379`: Bedrock SDK의 5분 세션 만료 뒤 HTTP/2 스트림 취소 `"pending stream has been canceled"`가 **재시도 가능** 목록에 들어감, `retry.ts` +3줄). 03-1에서 본 "stream ended before message_stop" 오류가 여기서 **재시도 대상**으로 분류된다는 점이 연결된다.
- **이 함수는 정책이 아니라 분류만 한다.** 주석: "컨텍스트 초과를 먼저 따로 처리한 뒤 호출자가 자기 재시도 예산과 대기를 적용한다."

**(b) 재시도 정책과 대기 시간** (`retry.ts:148-165`)
```ts
interface RetryPolicy { enabled; maxRetries; baseDelayMs; maxAgentDelayMs? }
retryDelayMs(policy, attempt) = min( baseDelayMs × 2^(attempt-1), maxAgentDelayMs ?? 60_000 )
```
1회째 `baseDelayMs`, 2회째 2배, 3회째 4배, ...이고 60초에서 잘린다(§8에서 `baseDelayMs=1000`일 때 1, 2, 4, 8, 16, 32, 60초 확인). 주석: `coding-agent`의 `settings.retry`(`enabled`, `maxRetries`, `baseDelayMs`, `maxAgentDelayMs`)와 같은 모양이다.

**(c) 반복문: `retryAssistantCall`** (`retry.ts:223-282`)
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
| **`coding-agent`: 에이전트 턴 재시도** | `core/agent-session.ts`: 호출 지점 `_handlePostAgentRun` `:2064-2073`, 판정 `_isRetryableError` `:3883-3886`, 준비 `_prepareRetry` `:3936-` (**[2026-11-17]** `4afe78de`에서 위치만 확인. 이전 SHA는 `:1805-1822`, `:3660-3663`, `:3713-3756`. 함수 본문은 다시 읽지 않았다) | 에이전트 실행이 끝난 뒤 `_handlePostAgentRun`이 `_isRetryableError(message) && await _prepareRetry(message)`를 부르고(`:2073`), `_isRetryableError`가 **먼저 컨텍스트 초과인지 보고(초과면 재시도 대신 압축으로 처리), 아니면 `isRetryableAssistantError`로 판정**한다(`:3662-3663`). `_prepareRetry`가 `settings.retry`를 읽어(`enabled`, `maxRetries`) 횟수를 세고, `retryDelayMs(settings, 시도횟수)`로 대기 시간을 정하고, `auto_retry_start` 이벤트를 내보내고, 실패한 시도를 모델 입력에서 빼고(`_omitRecoveryAttempt`), 취소 가능한 `sleep`으로 기다린 뒤 `true`를 돌려준다(그러면 호출자가 에이전트를 다시 이어 간다). |
| **`coding-agent`: 요약 호출** | `core/compaction/compaction.ts:613-637` | 대화 요약(compaction)과 브랜치 요약의 LLM 호출을 `retryAssistantCall`로 감싼다. 같은 `settings.retry` 예산을 쓴다(`agent-session.ts:3666-3669` 주석). |
| **`durable` 패키지** | `durable/src/harness/generation.ts:873`, `:898`, `harness/compaction.ts:197`(`4afe78de` 기준) | `isContextOverflow`, `isRetryableAssistantError`, `retryDelayMs`를 직접 사용 |
- `agent` 패키지의 `agent-loop.ts`에는 재시도 코드가 없다(`grep`으로 `retry` 판정 함수를 부르는 곳이 없음을 확인).
- 두 층으로 정리하면 **통신 코드(요청 재시도, 응답 시작 전) → `coding-agent`(응답 단위 재시도, 대기 이벤트로 화면에 표시)**다. 같은 일시 오류에 두 번 재시도가 겹칠 수 있는지(1층에서 `maxRetries`를 몇으로 넘기는지)는 확인하지 않았다(`미확인`).

## 3. 컨텍스트 크기

### 3.1 토큰 추정: `estimate.ts`
**실제 토큰 수는 서버만 안다.** 그래서 대화가 몇 토큰인지 미리 알아야 할 때(예: 출력 길이를 줄이거나 압축할 때)는 추정한다.
| 함수 | 줄 | 하는 일 |
|---|---|---|
| `estimateTextTokens(text)` | `:38-40` | `ceil(글자 수 / 3.5)` (`CHARS_PER_TOKEN = 3.5`. **[2026-11-17]** 이전 SHA는 4, 커밋 `27075fe07` "estimate request context at 3.5 characters per token") |
| `estimateMessageTokens(message)` | `:46-69` | 메시지 하나 추정. 이미지 한 장은 **4800글자**로 침(`ESTIMATED_IMAGE_CHARS`. 이전 문서의 "= 1200토큰"은 4로 나눈 값이고 지금은 3.5로 나눠 약 1372토큰). 도구 호출은 이름 + 인자 JSON 글자 수. 시스템 메시지는 도구 추가/제거 JSON까지 |
| `estimateContextTokens(context)` | `:97-112` | **마지막 응답의 `usage` + 그 뒤에 추가된 메시지 추정** |

`estimateContextTokens`의 요령(`:71-112`): 가장 최근 `assistant` 메시지의 **서버가 보고한 `usage.totalTokens`**를 기준으로 삼고, 그 뒤에 쌓인 메시지(`trailing`)만 글자 수로 추정해 더한다. 서버 값이 더 정확하기 때문이다. 다만 아래 두 경우의 usage는 기준으로 쓰지 않는다.
- `aborted`나 `error`로 끝난 응답
- **그 응답 뒤에 더 늦은 시각의 메시지가 끼어든 경우**(주석: 압축 요약이 삽입되면 이전 응답의 usage는 지금의 앞부분을 설명하지 못한다)

기준으로 쓸 usage가 하나도 없으면 전체를 글자 수 / 3.5로 추정한다.

**쓰이는 곳**: `api/simple-options.ts:17`의 `clampMaxTokensToContext`가 `model.contextWindow - 추정 토큰 - 4096`으로 **한 번에 받을 수 있는 출력 최대치를 자른다**(03-1 §3의 `buildBaseOptions`). 대화가 길수록 출력 한도가 줄어든다. `coding-agent`에도 같은 이름의 `estimateContextTokens`(`compaction.ts:196`, `AgentMessage` 기준)가 따로 있다(읽지 않음, `미확인`).

### 3.2 컨텍스트 초과 판정: `overflow.ts`
**문제**: 입력이 모델의 컨텍스트 창을 넘으면 서버마다 다른 문구로 오류를 낸다. `isContextOverflow(message, contextWindow?)`가 그것을 한 함수로 판정한다(`overflow.ts:144-181`). **세 가지 경우**를 본다.
| 경우 | 조건 | 예 |
|---|---|---|
| **1. 오류 문구** | `stopReason == "error"`이고 문구가 `OVERFLOW_PATTERNS` 29개 중 하나와 맞음(**[2026-11-17]** 이전 25개. 추가: LiteLLM `context window exceeded`, 그리고 provider·본문과 무관하게 HTTP 413을 초과로 보는 `^(?:[\w -]+ API error \(413\):|413(?:\s|:|$))`. 주석에 GitHub Copilot 413 "failed to parse request"와 요청 바이트 한도 초과가 추가됨) | Anthropic `prompt is too long: 213462 tokens > 200000 maximum`, OpenAI `exceeds the context window`, Google `input token count ... exceeds the maximum`, xAI, OpenRouter, llama.cpp, Mistral 등 서버별 문구(주석 `:9-35`가 서버별 예시 목록) |
| **2. 조용한 초과** | `contextWindow`를 주었고 `stopReason == "stop"`인데 `input + cacheRead > contextWindow` | z.ai처럼 초과를 거부하지 않고 받아 주는 서버 |
| **3. 길이 종료 초과** | `contextWindow`를 주었고 `stopReason == "length"`, `output == 0`, `input + cacheRead ≥ contextWindow × 0.99` | Xiaomi MiMo: 입력을 창에 맞게 잘라서 출력 자리가 없다 |

- **제외 규칙** (`NON_OVERFLOW_PATTERNS`, `:76-80`): `rate limit`, `too many requests`, Bedrock의 `Throttling error:` 접두사가 있으면 초과가 아니라고 본다. 주석: Bedrock이 "Too many tokens, please wait before trying again."라고 속도 제한 오류를 내는데 이것이 `too many tokens` 패턴과 맞아 초과로 오인되기 때문이다.
- Cerebras는 오류 본문이 없어서 `400`/`413 (no body)`일 때만 초과로 본다(`:65`, `:146-148`).
- 정규식은 **오류 문구가 서버 설정과 버전에 따라 달라지면 놓칠 수 있다.** 커스텀 provider를 추가했을 때는 이 파일의 패턴을 늘리거나 호출자가 직접 확인해야 한다고 주석이 안내한다(`:122-131`).
- `isRecoverableLength(message, desiredMaxOutput)` (`overflow.ts:186-188`): `length`로 끝났는데 출력이 원래 원하던 최대치보다 적으면 컨텍스트 압력이나 서버의 잘림일 수 있어 **한 번 압축하고 재시도**해 볼 수 있다는 판정이다.
- **쓰이는 곳**: `agent-session.ts:3173`(`explicitOverflow` 줄만 `4afe78de`에서 확인, 나머지 줄은 재확인 안 함. `explicitOverflow`, `contextOverflow`, `recoverableLength`로 자동 압축 결정), `durable/src/harness/generation.ts:873`. 압축을 하면 재시도 대신 압축으로 처리한다(`_isRetryableError`가 초과를 먼저 걸러내는 이유, §2.3).

## 4. JSON

### 4.1 깨진 JSON 복구와 스트리밍 해석: `json-parse.ts`, `streaming-json.ts`
> **[2026-11-17 재검증]** `json-parse.ts`는 149줄(+27)이고 `streaming-json.ts`(559줄)가 새로 생겼다. 아래는 `4afe78de` 기준이다.
- **`repairJson`** (`json-parse.ts:33`): 문자열 안에서만 제어 문자를 `\n` 같은 이스케이프로 바꾸고, 잘못된 이스케이프(`\U` 등) 앞의 역슬래시를 두 번으로 만든다. **변경**: 유효 이스케이프 집합(`VALID_JSON_ESCAPES`, `:4`)에서 `u`가 빠졌다(커밋 `4b994d5e5` "repair invalid \u escapes in tool-call arguments"). 유효한 `\uXXXX`를 어떻게 보존하는지는 `repairJson` 본문(`:33-84`)을 다시 읽지 않아 `미확인`.
- **`parseJsonWithRepair`** (`:86`): 먼저 `JSON.parse`, 실패하면 `repairJson` 후 다시 시도, 고쳐도 같으면 원래 오류를 던진다(diff 없음).
- **`parseToolCallArguments(json)`** (`:106-127`, **새로**): **끝난** 도구 호출의 인자 텍스트를 한 번에 파싱한다. 빈 텍스트면 `{ arguments: {} }`. 객체가 아니면(배열, `null`, 원시값) 또는 파싱에 실패하면 `arguments: {}`와 `argumentsError`(오류 문구 + "Received arguments:" + 받은 원문)를 돌려준다. 주석: `parseStreamingJson`과 달리 **부분적으로 파싱된 앞부분을 절대 유지하지 않는다**(#10944). 이 `argumentsError`는 `validateToolArguments`가 가장 먼저 확인해 모델에게 되돌려준다(§4.2).
- **`parseStreamingJson`** (`:129-149`): 순서와 동작은 이전 SHA와 같다(`parseJsonWithRepair` → `partial-json` → `repairJson` 후 `partial-json` → `{}`, 예외 없음). 다만 `agent/src/proxy.ts`는 더 이상 쓰지 않고(agent 04, `grep` 결과 0) `ToolCallArgumentsStream`을 쓴다. `api/*.ts`의 provider 코드가 어느 쪽을 쓰는지는 파일별로 확인하지 않았다(`미확인`. 커밋 `f715a15c1` 제목은 "parse streamed tool-call arguments incrementally").
- **`StreamingJsonParser`** (`streaming-json.ts:109`, **새로**): 조각으로 도착하는 JSON 텍스트를 **한 번만 읽는** 증분 파서. `append(piece)`로 읽고 `snapshot()`이 지금까지의 값을 준다. 파일 머리 주석의 규칙(`:1-36`):
  - 닫히지 않은 문자열은 읽은 만큼 보이고, 끝나지 않은 이스케이프는 완성될 때까지 보류한다. 닫히지 않은 컨테이너는 읽은 멤버·원소까지 보인다. 키나 값이 시작 전인 멤버는 뺀다. `true/false/null`은 접두사면 그 값, 숫자는 숫자가 된 시점부터 보인다.
  - 깨진 텍스트도 관대하게 읽고(제어 문자 유지, 잘못된 이스케이프는 글자 그대로, 쉼표·콜론 누락 허용, 알 수 없는 단어 버림, 루트 값 뒤 텍스트 무시) **절대 throw하지 않는다.**
  - `parseStreamingJson`과의 차이(주석): 닫히지 않은 문자열 끝의 공백을 유지, 제어 문자나 잘못된 이스케이프가 든 문자열도 스트리밍 중 보임(이전엔 문서가 끝날 때까지 버림), `NaN`·`Infinity`는 버림.
  - 스냅샷은 한 번 반환되면 **바뀌지 않는다**(열린 컨테이너만 복사해 새 스냅샷에 넣고 닫힌 것은 공유). 아주 큰 컨테이너가 열려 있으면 미리보기가 약간 뒤처질 수 있다(복사 "크레딧" 방식, `CREDIT_PER_APPEND = 256`, `CREDIT_PER_CHARACTER = 8`, `:93-94`).
  - `append()`는 변경 목록(`set`/`append`, 깊이 32까지, `MAX_REPORTED_DEPTH`, `:89`)도 돌려준다.
- **`ToolCallArgumentsStream`** (`:452-`, **새로**): 호출 하나의 인자를 담는다. 원문 텍스트(`#text`)는 끝날 때 한 번 완전 파싱하려고 들고 있고, 그 사이 부분 인자는 `StreamingJsonParser`가 준다. `append(delta)`는 부분 인자 객체(바뀔 때마다 새 객체)를, `replace(text)`는 provider가 완성 텍스트를 줄 때 이어 붙일 `delta`와 인자를, `finish()`는 `parseToolCallArguments(text)`를 돌려준다. 주석: **provider가 호출마다 자기 스트림 상태에 하나씩 두고 content 블록에는 두지 않으므로 원문이 partial 메시지나 transcript에 새지 않는다.** 부분 값이 객체가 아니면 `{}`로 보인다.
- 실행하지 않았으므로 구현의 존재와 주석 규칙까지만 `코드 확인`이고, 실제 입력별 결과는 `미확인`이다.

### 4.2 도구 인자 검증: `validation.ts`
> **[2026-11-17 재검증]** 파일이 350줄에서 **69줄**로 줄었다(커밋 `6536f8012` "validate tool arguments with pi-schema, drop TypeBox"). 형 변환 규칙(`coercePrimitiveByType`, `normalizeOptionalNulls`, `coerceWithJsonSchema`)과 TypeBox 의존이 이 파일에서 사라지고 `@earendil-works/pi-schema`로 넘어갔다. 아래는 `4afe78de` 기준이다.

`validateToolArguments(tool, toolCall)` (`validation.ts:51-68`)의 흐름:
```
1. toolCall.argumentsError 가 있으면 즉시 throw  "Invalid arguments for tool "X": <argumentsError>"
2. validator = getValidator(tool.parameters)   스키마 객체를 키로 WeakMap 캐시,
                                               compile(schema, { formats, coerce: true, unresolvedRefs: "reject" })   (:6-20)
3. result = validator.parse(structuredClone(toolCall.arguments))   복사본을 형 변환(coerce)한 뒤 검사
4. result.ok 이면 result.value 반환. 아니면 Error:
   "Validation failed for tool "X":\n  - 경로: 메시지 ...\n\nReceived arguments:\n<원본 JSON>"
```
- **형 변환은 `pi-schema`의 `coerce`가 한다.** `packages/schema/README.md`(`### Coercion`)에 따르면 3단계다. ① 필수가 아닌 속성의 `null`을 스키마가 거부하면 속성을 지운다. ② TypeBox 1.3.27의 `Value.Convert`를 포팅한 변환(`$ref`, `const`/`enum`, `anyOf`/`oneOf`, `allOf`, 그다음 `type`별: 문자열↔숫자·불리언, 정수는 소수 절삭, 단일 값을 1개짜리 배열로 감쌈 등). ③ Ajv `coerceTypes`식 원시값 변환(`["integer","null"]` 같은 type 배열용). 2와 3이 충돌하면 2가 이긴다(필수 문자열에 `null` → `"null"`). 이전 문서가 적은 `number`의 `null → 0`·숫자 문자열 → 숫자·불리언 → 1/0과 같은 방향이다. 이전 `coercePrimitiveByType`의 세부 규칙과 완전히 같은지는 `pi-schema/src/coerce.ts`를 읽지 않아 `미확인`이다(README 기준).
- **오류 경로**는 JSON Pointer를 점 경로로 바꾼 것이다(`/edits/0/oldText` → `edits.0.oldText`, `formatValidationPath`, `:23-30`). 이전의 "필수 필드가 없으면 그 이름까지 붙이는" 로직은 이 파일에 없다(오류 객체의 `path`가 이미 그렇게 오는지는 `미확인`).
- **스키마 종류**: TypeBox 여부를 확인하던 분기(`TypeBox.Kind`)가 없다. `pi-schema` 빌더, TypeBox, 일반 JSON Schema 객체를 구분 없이 받는다(주석 `:36-38`).
- **정의 없는 `$ref`**: `unresolvedRefs: "reject"`로 컴파일해서, MCP 서버 스키마의 정의 없는 `$ref`는 그 자리의 값만 거부하고 도구 호출 전체가 실패하지는 않는다(주석 `:15-16`).
- `validateToolCall(tools, toolCall)`는 이름으로 도구를 찾고(없으면 `Tool "x" not found`) 위를 부른다(`:40-46`).
- **쓰이는 곳**: `agent/src/agent-loop.ts:736`(`validateToolArguments(tool, preparedToolCall)`), `durable/src/harness/tool.ts:527`. 도구를 실행하기 전의 마지막 관문이다.
- 실행하지 않았고 `pi-schema`의 `compiler.ts`·`coerce.ts`·`validator.ts`는 읽지 않았다. README와 호출 코드가 근거다.

## 5. 오류 정리

### 5.1 `error-body.ts`: SDK마다 다른 오류 객체를 한 모양으로
**문제**: 게이트웨이나 프록시 뒤에서 서버가 비정상 응답을 주면 SDK가 본문을 오류 메시지에 합쳐 주지 못해 `"403 status code (no body)"` 같은 불투명한 메시지가 된다. 본문은 SDK 오류 객체의 **SDK마다 다른 필드 이름**에 들어 있다.
- `normalizeProviderError(error)` (`:38-54`)가 알려진 모양을 순서대로 본다.
  - 상태 코드: `statusCode`(Mistral) → `status`(`openai`, `@google/genai`) → `$metadata.httpStatusCode`(Bedrock) → `$response.statusCode`(Bedrock)
  - 본문: `body` 문자열(Mistral) → `error` 객체(`openai`의 파싱된 본문) → `$response.body`(Bedrock). 빈 객체와 아직 읽지 않은 스트림은 본문이 아니라고 본다. **일반 객체(plain object)만** 본문으로 인정한다(주석 `:98-111`: AWS SDK의 `$response.body`는 HTTP 스트림 래퍼라서 문자열로 만들면 `{"_events":...}` 같은 의미 없는 문자열이 되어 진짜 메시지를 덮어쓴다).
  - 본문은 4000글자(`MAX_PROVIDER_ERROR_BODY_CHARS`)로 자른다.
- **[2026-11-17 추가]** `withCauseDetail(error)`(`error-body.ts:68`): 상태도 본문도 없는 **연결 수준 실패**(OpenAI SDK의 `"Connection error."`, undici의 `"fetch failed"` 등)는 진짜 이유가 `cause` 체인 안쪽(최대 5단계)에 있으므로, 가장 깊은 cause의 메시지(와 `code`)를 `"<원래 메시지>: <상세>"`로 덧붙인다. `normalizeProviderError`가 상태·본문이 모두 없을 때만 쓴다(`:49`). `truncateErrorText`는 `ownedSlice`(`text.ts`)로 잘라 짧은 발췌가 큰 응답 본문 전체를 메모리에 붙들지 않게 했다(`:168`, V8 slice 뷰 문제, 주석).
- `formatProviderError(norm, prefix?)` (줄 번호는 위 추가분만큼 밀림): 메시지에 본문이 이미 있거나 상태·본문을 못 찾았으면 메시지를 그대로, 아니면 `"<prefix> (<상태>): <본문>"`. §8 실험에서 `403 status code (no body)` + `error: {error:{message:"blocked by gateway"}}`가 `OpenAI API error (403): {"error":{"message":"blocked by gateway"}}`가 되었다.
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
| `text.ts` | **[2026-11-17] `ownedSlice(text, start, end)` 추가**: 짧은 발췌가 큰 원문을 메모리에 붙들지 않게 복사해 자른다. 그 외: `contentText`(글 블록 이어 붙이기), `getSystemMessageText`(시스템 메시지의 본문 + 섹션을 한 프롬프트로), `renderSystemMessageUpdate`(나중 시스템 메시지를 `Updated system prompt section "이름":` / `Removed system prompt section "이름".` 형태로 표현. 주석: 요청 시점 전용이며 버전에 따라 바뀔 수 있음) |
| `sanitize-unicode.ts` | **짝이 맞지 않는 서로게이트 문자**만 제거한다(짝이 맞는 이모지는 유지). 홀로 남은 서로게이트가 있으면 많은 서버에서 JSON 직렬화 오류가 난다(주석). 03의 통신 코드가 글을 요청에 넣을 때마다 부른다. |
| `hash.ts` | `shortHash(str)`: 빠른 **비암호용** 해시(두 개의 32비트 값을 36진수로 이어 붙임). 긴 ID를 줄일 때 쓴다(예: 40자를 넘는 도구 호출 ID, 03-3 §3.3). 암호학적 용도가 아니다. |
| `uuid.ts` | `uuidv7(timestampMs?)`: **시간순으로 정렬되는 UUIDv7**. 같은 밀리초 안에서도 순서가 유지되도록 증가하는 순번을 넣는다. |
| `headers.ts` | `headersToRecord`(`Headers` → 객체), `providerHeadersToRecord(...출처들)`: **헤더 이름의 대소문자를 무시하고 뒤의 것이 앞을 덮어쓰며 값이 `null`이면 삭제**(01에서 본 "null이면 기본 헤더 제거"의 구현) |
| `provider-env.ts` | `getProviderEnvValue(name, env?)`: 우선순위 **호출 옵션의 `env` → `process.env` → Bun 샌드박스 대체(`/proc/self/environ` 읽기)**. Bun으로 컴파일한 실행 파일이 리눅스 샌드박스에서 `process.env`가 비어 있는 문제의 우회(주석, 이슈 `oven-sh/bun#27802`) |
| ~~`pi-user-agent.ts`~~ | **[2026-11-17] 삭제됨**(`adc5fa9f8` "move client identity and provider attribution into pi-ai"). 역할은 새 `identity.ts`(193줄)로 넘어간 것으로 보이나 내용은 읽지 않았다(`추론`) |
| `model-operations.ts` | `getModelType`(`type`이 없으면 `"chat"`), `isModelType`, `assertChatModel` 등(틀리면 `ModelsError("provider")`), 이미지/분류 호출 실패 때 에러가 담긴 결과 객체 만들기(`imageErrorResult`, `classifierErrorResult`, 02 §4.6) |
| `string-enum.ts`(이전 `typebox-helpers.ts`) | `StringEnum(values, opts)`: `{ type: "string", enum: [...] }`. **[2026-11-17]** 반환 타입이 TypeBox가 아니라 `pi-schema`의 `Schema<T[number]>`. 주석: Google 등 `anyOf`/`const`를 지원하지 않는 서버와 호환되는 형태 |

## 8. 실험: 실제 코드로 확인 (`실행 확인`, 2026-10-05 `3874b3e98` 기준)
> `4afe78de`에서는 다시 실행하지 않았다. 이 절이 다루는 `provider-retry.ts`·`retry.ts`·`overflow.ts`·`estimate.ts`·`error-body.ts`는 위처럼 바뀌었으므로(특히 `estimate.ts`의 3.5, 재시도·초과 패턴) 해당 결과는 현재 코드와 다를 수 있다. `sanitize-unicode.ts`·`hash.ts`·`uuid.ts`는 diff가 없어 그대로다.
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
- ~~`assistant-message-frame.ts`~~: **[2026-11-17] 삭제됨**(`b39979799` "remove unused assistant-message frame API"). 이전 문서가 쓰는 곳을 확인하지 못했다고 한 것과 맞게 미사용 API였다.
- `identity.ts`(193줄), `openrouter-cost.ts`(55줄), `version.ts`: 새 파일, 읽지 않았다.
- `node-http-proxy.ts`(161줄), `oauth-page.ts`(109줄)
- `partial-json`의 부분 해석 동작, `StreamingJsonParser`의 입력별 결과, `pi-schema`의 `compile`·`coerce` 내부(실행하지 않았고 `pi-schema` 소스는 README만 읽음)
- `coding-agent`의 재시도 설정 기본값(`settings.retry`), `_omitRecoveryAttempt`, 자동 압축의 나머지, `compaction.ts`의 자체 `estimateContextTokens`
- 1층과 2층 재시도가 같은 오류에서 어떻게 겹치는지(1층 `maxRetries`를 호출자가 얼마로 넘기는지)

## 10. 다음
**06 호출 경로 종합**: 지금까지 본 조각(`types`, `Models`, `lazyStream`, `Provider`, 통신 코드, `EventStream`, 인증, `utils`)을 한 번의 호출에 순서대로 엮어서 정리한다. 그 뒤 `agent` 패키지로 넘어가며, 이 commit에서 `agent`가 크게 바뀌었으므로(00 §7) 이전 Q5, Q6을 새 기준으로 다시 확인해야 한다.
