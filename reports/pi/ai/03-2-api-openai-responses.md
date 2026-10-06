# ai 03-2: 통신 코드 읽기 — `api/openai-responses.ts` (OpenAI, 현재 경로)

- **기준 commit**: `3874b3e98` / **분석일**: 2026-10-05
- **선행 문서**: [03-0-event-stream](./03-0-event-stream.md)(`push`, `for await`), [03-1-api-anthropic](./03-1-api-anthropic.md)(같은 뼈대를 Claude로 읽음), [04-auth](./04-auth.md)(인증 일반)
- **함께 볼 문서**: [03-3-api-openai-compare](./03-3-api-openai-compare.md)(OpenAI 계열 세 통신 코드 비교), [03-4-api-openai-codex-legacy](./03-4-api-openai-codex-legacy.md)(legacy Codex 경로)
- **읽은 파일**: `api/openai-responses.ts`(415줄 전체), `api/openai-responses-shared.ts`(`:1-809` 전체: 메시지 변환, 도구 변환, `processResponsesStream`, `mapStopReason`), `auth/oauth/openai-chatgpt.ts`(`:1-310` 거의 전체), `providers/openai.ts`. 줄 번호는 모두 이 commit 기준이다.
- **검증 수준**: 코드 읽기는 `코드 확인`. 응답을 pi 이벤트로 바꾸는 `processResponsesStream`은 줄 범위 그대로 복사해서 가짜 이벤트로 돌렸다(`실행 확인`, §5.2). 웹 검색으로 OpenAI 공식 문서를 확인한 부분은 출처를 붙였다. **실제 서버와 통신하거나 실제 로그인을 해 본 것은 없다**(`미확인`).

> [!NOTE]
> **2026-10-06 갱신** (`3874b3e98` → `28dcce2ba` diff 반영): 콜백 서버 실패 처리와 `samplingParams` 합성이 바뀌었다(아래 §7 단계 3, `samplingParams` 행, 맨 끝 부록). 이 파일의 다른 줄 번호는 diff가 작아 대체로 유효하나 전수 재확인은 하지 않았다.

## 0. 이 문서의 위치: 왜 이것이 "현재 경로"인가
`openai` provider(OpenAI 본사 모델)는 이 통신 코드를 쓴다(`providers/openai.ts`).
```ts
createProvider({
  id: "openai", baseUrl: "https://api.openai.com/v1",
  auth: { apiKey: envApiKeyAuth("OpenAI API key", ["OPENAI_API_KEY"]),          // API 키
          oauth: lazyOAuth({ name: "OpenAI (ChatGPT subscription)", ... }) },  // ChatGPT 구독 로그인
  models: Object.values(OPENAI_MODELS),     // 2026-10-04 생성 데이터 기준 44개, 모두 api = "openai-responses"
  api: openAIResponsesApi(),                // 이 문서의 통신 코드
})
```
| | 현재 경로 (이 문서) | legacy 경로 (03-4) |
|---|---|---|
| provider | `openai` | `openai-codex` (이름이 `OpenAI Codex (legacy)`) |
| 로그인 | API 키 또는 `openai-chatgpt.ts`(Sign in with ChatGPT) | `openai-codex.ts` (Codex CLI의 공개 OAuth 클라이언트) |
| 통신 코드 | `openai-responses.ts` (415줄, SDK 사용) | `openai-codex-responses.ts` (1697줄, SDK 없음, WebSocket 우선) |
| 서버 | `api.openai.com/v1` | `chatgpt.com/backend-api` |

근거: `CHANGELOG.md`("Added Sign in with ChatGPT to the `openai` provider ... Renamed the OpenAI Codex provider to 'OpenAI Codex (legacy)'; Sign in with ChatGPT on the `openai` provider supersedes it", 커밋 `02eed88fd`, 2026-09-29). legacy 코드는 삭제되지 않았고 `providers/all.ts:162`에 등록되어 있다.

이 통신 코드를 쓰는 provider는 `openai`(44개 모델) 외에 opencode(30), cloudflare-ai-gateway(24), github-copilot(18), opencode-go(6), meta(5), xai(4)다(03-3 §1).

## 1. 한눈에 보는 구조
```
Provider "openai"
  └ api: openAIResponsesApi()  → api/openai-responses.ts (지연 로딩)
       ├ streamSimple (:238-256)  reasoning을 reasoningEffort로 바꾸고 stream 호출
       └ stream       (:127-236)
            ① 빈 AssistantMessage(output) 만들기
            ② 클라이언트 만들기 (OpenAI SDK, createClient)
            ③ 요청 본문 만들기 (buildParams, 대화·도구는 공용 변환기)
            ④ SDK로 요청 전송 (client.responses.create)
            ⑤ 응답 이벤트를 공용 processResponsesStream으로 pi 이벤트로 변환
            ⑥ done 또는 error
```
03-1(Claude)과 같은 뼈대다. 다른 점은 **④ 요청을 SDK가 보내고, 응답의 SSE 해석도 SDK가 하며, ⑤ 변환은 공용 파일이 한다**는 것이다. 그래서 파일이 415줄로 짧다.

## 1.1 `stream()`의 줄 구조: 상자를 만들고, 뒤에서 채우고, 상자를 돌려준다
03-1 §1.1과 같은 구조이고 줄 번호만 다르다(`openai-responses.ts`).

| 하는 일 | 줄 | 실제 코드 |
|---|---|---|
| 함수 시작 | `:127-131` | `export const stream = (model, context, options) => {` |
| **① 상자 만들기** | **`:132`** | `const stream = new AssistantMessageEventStream();` |
| 대화 정리 | `:133` | `resolveTranscript(context, getCompat(model).supportsMidConvoSystemMessages)` |
| **② 뒤에서 일하는 함수 시작** | **`:136`** | `(async () => {` |
| ②의 끝 | **`:233`** | `})();` |
| **③ 상자 돌려주기** | **`:235`** | `return stream;` (괄호 없음: 상자 변수를 돌려준다) |

`streamSimple`은 `:252`에서 `return stream(model, context, {...})`로 `stream`을 **호출한 결과(상자)**를 그대로 돌려준다.

### 동기 구간과 비동기 구간
②의 첫 `await`는 `:174`(`await options?.onPayload?.(params, model)`)다. `async` 함수는 첫 `await`까지 동기로 실행되므로 아래는 규칙과 코드 구조에서 도출한 구분이다(`추론`).
| 시점 | 줄 | 하는 일 |
|---|---|---|
| `stream()`이 돌려주기 **전** (동기) | `:137-153` | 빈 `AssistantMessage`(`output`) 만들기 |
| 〃 | `:157-173` | `apiKey` 확인(`getClientApiKey`), 클라이언트 만들기, **요청 본문 만들기**(`buildParams`) |
| `:174`의 `await`에서 양보 | | 이 뒤로는 `return stream`이 먼저 실행된다. |
| 돌려준 **뒤** (비동기) | `:178-191` | 요청 전송(`retryProviderRequest`)과 응답 헤더 확인 |
| 〃 | `:192` | `start` 이벤트 push |
| 〃 | `:194-199` | `processResponsesStream`으로 응답을 읽으며 이벤트 push |
| 〃 | `:201-232` | 종료 검사, `done` 또는 `error` push |

동기 구간의 예외(`:157`의 "No API key", `buildParams` 오류)는 `try`(`:155`)/`catch`(`:214`) 안이라 던져지지 않고 `error` 이벤트로 상자에 들어간다(`추론`).

### 상자에 넣는 곳 (`stream.push`)
Codex 코드와 마찬가지로 **이 파일은 `start`와 `done`/`error`만 push하고, `text_delta` 등은 공용 변환기가 push한다.**
| 위치 | 줄 | 실제 코드 | 언제 |
|---|---|---|---|
| 이 파일 | **`:192`** | `stream.push({ type: "start", partial: output })` | 요청 헤더를 받은 직후 |
| 〃 | `:194-199` | `await processResponsesStream(openaiStream, output, stream, model, {...})` | 응답 이벤트를 읽고 변환 |
| 〃 | **`:212-213`** | `stream.push({ type: "done", ... })`, `stream.end()` | 정상 종료 |
| 〃 | **`:230-231`** | `stream.push({ type: "error", ... })`, `stream.end()` | 실패 (`catch`, `:214`) |
| **공용** `openai-responses-shared.ts` | `:474`, `:483`, `:502` | `thinking_start`, `text_start`, `toolcall_start` | 새 블록이 시작될 때 |
| 〃 | `:609`, `:639`, `:457` | `thinking_delta`, `text_delta`, `toolcall_delta` | 조각이 올 때마다 |
| 〃 | `:694`, `:704`, `:721` | `thinking_end`, `text_end`, `toolcall_end` | 블록이 끝날 때 |

`processResponsesStream`은 상자(`stream`)를 **인자로 받아서** 그 안에서 `push`한다(`:194-199`).

### 상자를 꺼내서 쓰는 쪽
03-1과 같다. `api/lazy.ts:35`의 `forwardStream`이 꺼내서 다른 상자에 넣고, 마지막 상자를 `agent/src/agent-loop.ts:414`가 꺼내 쓴다(03-0 §8).

## 1.2 실제 API 호출은 어디이고, 서버 조각은 무엇인가
**실제 API 호출은 `:183-190`이다.**
```ts
const { data: openaiStream, response } = await retryProviderRequest(
    () => client.responses.create(params, requestOptions).withResponse(),   // :184 ← 서버에 요청을 보낸다
    { maxRetries: options?.maxRetries, maxRetryDelayMs: options?.maxRetryDelayMs, signal: options?.signal },
);
```
| 줄 | 하는 일 |
|---|---|
| `:165` | `createClient`: OpenAI SDK(`new OpenAI({...})`)를 만든다. 통신은 아직 안 한다. |
| `:173` | `buildParams`: 보낼 요청 내용을 만든다. `stream: true`가 들어 있다(`:333`). |
| **`:184`** | `client.responses.create(params, ...)`: **서버에 요청을 보낸다.** |
| `:178-182` | `requestOptions`: 취소 신호, 제한 시간, **SDK 자체 재시도는 끈다**(`maxRetries: 0`). 재시도는 공용 `retryProviderRequest`가 한다. |

**03-1(Claude), 03-4(Codex)와 다른 점: SSE 해석을 SDK가 한다.**
- `.withResponse()`는 `{ data, response }`를 돌려준다. `response`는 헤더(상태 코드 등)이고, **`data`는 SDK가 SSE를 해석해서 만든 `ResponseStreamEvent` 객체의 비동기 스트림**이다.
- 그래서 이 파일에는 SSE 줄을 읽거나 JSON으로 바꾸는 코드가 **없다.** 03-1의 `iterateSseMessages`, 03-4의 `parseSSE` 같은 함수가 필요 없다. `processResponsesStream(openaiStream, ...)`이 SDK가 준 객체를 바로 받는다.
- **서버 조각** = SDK가 돌려주는 `ResponseStreamEvent` 하나(예: `response.output_text.delta`). `processResponsesStream`의 `for await`(`openai-responses-shared.ts:599`)가 하나씩 받는다.

## 1.3 왜 `stream.push`를 하는가
03-1 §1.3과 같다. 이 파일에서 확인되는 근거만 적는다(해석은 `추론`). `stream()`은 `:235`에서 이미 상자를 돌려줬으므로 그 뒤에 오는 이벤트는 `push`로만 전달할 수 있고, 같은 상자에 **이 파일**(`start`, `done`, `error`)과 **공용 변환기**(`text_delta` 등)가 함께 넣는다. 호출하는 쪽은 `for await`와 `.result()`를 둘 다 쓴다(`agent-loop.ts:409`, `:414`).

## 2. 입력: `OpenAIResponsesOptions` (`:117-122`)
`StreamOptions`를 상속하고 Responses 전용 항목을 더한다.
| 항목 | 값 | 뜻 |
|---|---|---|
| `reasoningEffort` | `minimal`, `low`, `medium`, `high`, `xhigh`, `max` | 추론 강도 |
| `reasoningSummary` | `auto`, `detailed`, `concise`, `null` | 추론 요약 방식 |
| `serviceTier` | OpenAI 서비스 등급 | 처리 속도와 가격 등급(§5.3) |
| `toolChoice` | OpenAI SDK의 `tool_choice` 타입 | 도구 사용 방식 |

## 3. `streamSimple` (`:238-256`)
```
1. getClientApiKey(...)로 인증 확인. 없으면 동기로 throw  (:243)
2. buildBaseOptions로 공통 옵션 정리 + toolChoice 전달
3. reasoning이 있으면 clampThinkingLevel(model, reasoning)로 모델이 지원하는 수준에 맞춤. "off"이면 reasoningEffort를 비움  (:249-250)
4. stream(model, context, { ...base, reasoningEffort })                                       (:252-255)
```
Claude의 `streamSimple`(adaptive와 예산 두 갈래)보다 단순하다. `reasoning` 값을 `thinkingLevelMap`으로 모델 값으로 바꾸는 일은 `buildParams`(§4.3)에서 한다.

## 4. 요청 만들기

### 4.1 인증과 클라이언트
- **`getClientApiKey`** (`:58-62`): `apiKey`가 있으면 그것, 없는데 `Authorization`이나 `cf-aig-authorization` 헤더가 있으면 `"unused"`(SDK에 넘길 자리 채우기), 둘 다 없으면 `"No API key for provider: ..."`를 던진다. 이 키는 04-auth에서 본 `applyAuth`의 결과다. **ChatGPT 구독 로그인이면 이 자리에 OAuth `access` 토큰이 들어온다**(04 §5.1, §7).
- **`createClient`** (`:258-300`): `new OpenAI({ apiKey, baseURL: model.baseUrl, dangerouslyAllowBrowser: true, fetch, defaultHeaders })`. 헤더는 아래 순서로 만들고 뒤의 것이 앞을 덮어쓴다.
  1. `User-Agent`(pi 정보), 모델의 `headers`
  2. GitHub Copilot이면 동적 헤더(`:268-275`)
  3. 세션 ID가 있으면 세션 친화 헤더(`:277-286`): 형식이 `openrouter`이면 `x-session-id`, 아니면 `x-client-request-id`(형식이 `openai`이면 `session_id`도)
  4. 호출자의 `options.headers`(`:288-291`)

### 4.2 compat (`getCompat`, `:82-95`)
`model.compat`에서 값을 읽고 없으면 기본값을 쓴다. 이 파일이 쓰는 값은 10개다.
| 값 | 기본값 | 쓰이는 곳 |
|---|---|---|
| `supportsDeveloperRole` | `true` | (공용 변환기가 `developer`/`system` 선택, §4.5) |
| `supportsMidConvoSystemMessages` | `false` | `resolveTranscript`(`:133`): 대화 중간의 시스템 메시지를 그대로 보낼지 맨 앞에 합칠지 |
| `sessionAffinityFormat` | 주소가 OpenRouter이면 `openrouter`, 아니면 `openai` | 세션 헤더(§4.1) |
| `supportsLongCacheRetention` | `true` | 프롬프트 캐시(§4.7) |
| `supportsStrictMode` | `false` | 도구 `strict` 사용 여부(§4.6) |
| `supportsOpenAIGrammarTools` | `false` | 문법으로 제약한 도구 사용 여부 |
| `supportsAdditionalTools`, `supportsToolSearch` | `false` | 대화 중 도구 추가 방식 |
| `supportsExplicitPromptCacheMode` | `false` | 캐시 옵션 형식(§4.7) |
| `supportsMaxOutputTokens` | `true` | `max_output_tokens`를 보낼지 |

03-3 §6에서 본 `openai-completions`의 compat 자동 감지(`detectCompat`)와 달리, 이 파일은 **서버를 이름으로 구분해서 기본값을 바꾸지 않고**(세션 헤더 형식만 주소로 구분) 대부분 모델 데이터의 `compat`에 맡긴다.

### 4.3 요청 본문: `buildParams` (`:302-385`)
| 필드 | 값 | 줄 | 비고 |
|---|---|---|---|
| `model` | `model.id` | `:331` | |
| `input` | `convertResponsesMessages(...)` 결과 | `:316-325`, `:332` | 대화 기록 (공용 변환기, §4.5) |
| `stream` | `true` | `:333` | |
| `prompt_cache_key` | 세션 ID. 캐시 보존이 `none`이면 없음 | `:334` | §4.7 |
| `prompt_cache_retention`, `prompt_cache_options` | 캐시 보존과 compat에 따라 | `:335-336` | ChatGPT 로그인이면 생략(§4.4) |
| `store` | `false` | `:337` | 서버에 대화를 저장하지 않는다. |
| `max_output_tokens` | `max(options.maxTokens, 16)` | `:340-342` | 최소 16(이슈 #6265). `supportsMaxOutputTokens`가 `false`이거나 ChatGPT 로그인이면 생략 |
| `temperature` | 주어졌을 때만 | `:344-346` | ChatGPT 로그인이면 생략 |
| `service_tier` | 주어졌을 때만 | `:348-350` | |
| `tools` | `convertResponsesTools(...)` | `:352-357` | 도구가 있을 때 (§4.6) |
| `tool_choice` | 주어졌을 때만 | `:359-361` | |
| `reasoning`, `include` | 아래 | `:363-379` | |
| `samplingParams` | `resolveSamplingParams(model, 추론수준, options.samplingParams)`의 결과를 덮어씀 | `:383-386`, 함수는 `simple-options.ts:24-34` | **마지막**에 적용되어 앞의 이름 있는 필드를 덮어쓴다. 우선순위는 `model.samplingParams` < **`model.samplingParamsByThinkingLevel[효과 추론수준]`** < 호출 옵션(`...` 스프레드 순서). 추론 수준은 `clampThinkingLevel`로 모델이 지원하는 값으로 맞춘 것. (이전 commit에는 추론 수준별 항목이 없었다) |

**추론 설정** (`:363-379`)
```
model.reasoning 이 true 이면
    reasoningEffort 또는 reasoningSummary 가 있으면
        effort = reasoningEffort 가 있으면 thinkingLevelMap[reasoningEffort] ?? reasoningEffort, 없으면 "medium"
        reasoning = { effort, summary: reasoningSummary || "auto" }
        include = ["reasoning.encrypted_content"]          ← 암호화된 추론 내용을 받아서 다음 요청에 되돌려 보내기 위함
    아니고, provider 가 github-copilot 이 아니고 thinkingLevelMap.off 가 null 이 아니면
        reasoning = { effort: thinkingLevelMap.off ?? "none" }       ← 추론을 끈다
    provider 가 xai 이면 include 도 넣는다
```

### 4.4 ChatGPT 구독 로그인 토큰이면 일부 필드를 뺀다 (`isChatGPTSignIn`, `:40-47`, `:329`)
```ts
function isChatGPTSignIn(model, apiKey) {
    return model.provider === "openai"
        && model.baseUrl === "https://api.openai.com/v1"
        && apiKey !== undefined
        && !apiKey.startsWith("sk-");        // 주석: API 키는 sk- 로 시작하고, 다른 자격 증명을 OpenAI에 직접 보내면 ChatGPT 로그인 토큰이다
}
```
이 토큰이면 `omitUnsupportedFields`가 `true`가 되어 `prompt_cache_retention`, `prompt_cache_options`, `max_output_tokens`, `temperature`를 **요청에서 뺀다**(주석: "Sign in with ChatGPT rejects these request fields", `:328`). 즉 **같은 `openai` provider, 같은 통신 코드라도 API 키로 부를 때와 ChatGPT 로그인으로 부를 때 요청 필드가 다르다.** 구분 기준이 토큰 접두사라는 점은 코드로 확인했고, 실제 로그인 토큰이 `sk-`로 시작하지 않는지는 확인하지 못했다(`미확인`).

### 4.5 대화 변환: `convertResponsesMessages` (공용 `:145-354`)
pi의 `Message`를 Responses의 `input` 항목 배열로 바꾼다. Responses 계열(이 파일, `azure-openai-responses`, legacy Codex)이 공용으로 쓴다.
| pi 메시지 | Responses `input` 항목 | 비고 |
|---|---|---|
| 맨 앞 시스템 메시지 | `{ role: "developer" 또는 "system", content }` | 추론 모델이고 `supportsDeveloperRole !== false`이면 `developer`, 아니면 `system` (`:213-215`, `:223-228`). legacy Codex는 `includeSystemPrompt: false`로 이 항목을 만들지 않는다 |
| 중간 시스템 메시지 | 같은 형식의 항목 | `supportsMidConvoSystemMessages`가 아니면 이미 맨 앞에 합쳐져 있다(`:151`) |
| 사용자 글 | `{ role: "user", content: [{ type: "input_text", text }] }` | 문자열도 배열로 감쌈 |
| 사용자 이미지 | `{ type: "input_image", detail: "auto", image_url: "data:<mime>;base64,..." }` | |
| 이전 AI의 **추론** | `thinkingSignature`(저장해 둔 추론 항목 JSON)를 `JSON.parse`해서 **그대로 되돌려 보냄** (`:264-268`) | 서명이 없으면 보내지 않음. 이것이 `include: ["reasoning.encrypted_content"]`로 받은 값이다. |
| 이전 AI의 **글** | `{ type: "message", role: "assistant", content: [{ type: "output_text", text }], status: "completed", id, phase }` (`:269-289`) | `id`는 저장해 둔 `textSignature`(`{"v":1,"id":...}` JSON 또는 옛 문자열)에서 꺼내고, 없으면 `msg_pi_<번호>`, 64자를 넘으면 `msg_<해시>` |
| 이전 AI의 **도구 호출** | `{ type: "function_call", id, call_id, name, arguments: JSON.stringify(...) }` (`:319-326`) | 문법 제약 도구이면 `custom_tool_call`(`:307-317`) |
| 도구 결과 | `{ type: "function_call_output", call_id, output }` (`:343-347`) | 모델이 이미지를 못 받으면 글 자리표시(`"(see attached image)"` 등, `:81-108`) |

**도구 호출 ID 처리** (`:154-177`): pi는 도구 호출 ID를 `call_id|item_id` 한 문자열로 들고 있다(응답 변환기가 `${call_id}|${item.id}`로 만든다, 공용 `:489`). 요청에 되돌릴 때는 `|`로 나눠서 `call_id`와 `item.id`를 따로 쓴다. 다른 provider나 다른 api가 만든 호출이면 `item.id`를 `fc_<해시>`로 새로 만든다(주석: "OpenAI Responses API requires item id to start with 'fc'"). **다른 모델이 만든 호출의 `id`는 아예 비운다**(`:296-305`, 주석: "OpenAI가 추론 항목과 짝을 지은 항목 ID를 검증하는 것을 피하기 위해"). 이 규칙은 03-1 §4.4의 `transformMessages`(모델 교체 시 이력 변환)와 함께 동작한다.

### 4.6 도구 변환: `convertResponsesTools` (공용 `:360-397`)
- 일반 도구: `{ type: "function", name, description, parameters, strict? }`. `strict`는 `supportsStrictMode`가 `true`일 때만 넣는다(`:392-394`). 이 파일의 `getCompat` 기본값은 `false`다(§4.2).
- 문법으로 제약한 도구(`supportsOpenAIGrammarTools` 켜짐): `{ type: "custom", name, description, format: { type: "grammar", syntax, definition } }` (`:366-379`). Responses는 `name`과 `description`이 도구 객체 바로 아래에 있다. 03-3에서 본 Chat Completions는 `function: { name, ... }`로 한 겹 더 감싼다(`openai-completions.ts:1498-1507`).

### 4.7 프롬프트 캐시 (`:97-114`, `:334-336`)
- `prompt_cache_key`: 세션 ID(`clampOpenAIPromptCacheKey`). 캐시 보존이 `none`이면 보내지 않는다.
- 일반 모델: 보존이 `long`이고 `supportsLongCacheRetention`이며 `supportsExplicitPromptCacheMode`가 아니면 `prompt_cache_retention: "24h"`.
- 명시 캐시 모드를 지원하는 모델(GPT-5.6 이상, `types.ts:886` 주석): 보존이 `none`이면 `prompt_cache_options: { mode: "explicit" }`, `long`이면 `{ ttl: "30m" }`.

## 5. 응답 해석: `processResponsesStream` (공용 `openai-responses-shared.ts:433-777`)

### 5.1 이벤트 변환 표
SDK가 준 `ResponseStreamEvent`를 하나씩 받아서 `output`을 채우고 `stream.push`한다(`:599-758`).
| OpenAI Responses 이벤트 | 하는 일 | pi 이벤트 |
|---|---|---|
| `response.created` | `output.responseId` 기록 | (없음) |
| `response.output_item.added` | 항목 종류에 따라 새 블록을 만든다: `reasoning`은 thinking, `message`는 text, `function_call`과 `custom_tool_call`은 toolCall | `thinking_start` / `text_start` / `toolcall_start` |
| `response.reasoning_summary_text.delta`, `response.reasoning_text.delta` | thinking에 덧붙임 | `thinking_delta` |
| `response.reasoning_summary_part.done` | thinking에 `"\n\n"` 추가 (요약 문단 구분) | `thinking_delta` |
| `response.output_text.delta`, `response.refusal.delta` | text에 덧붙임 (거절 문구도 글로 취급) | `text_delta` |
| `response.function_call_arguments.delta` | 인자 JSON 조각을 모으고 `parseStreamingJson`으로 해석해 `arguments` 갱신 | `toolcall_delta` |
| `response.function_call_arguments.done` | 최종 인자로 교체. 앞서 모은 것과 접두사가 같으면 **남은 조각이 있을 때만** `delta`로 push | `toolcall_delta` (남은 조각이 있을 때) |
| `response.custom_tool_call_input.delta/done` | 문법으로 제한된 도구의 입력을 모음 | `toolcall_delta` |
| `response.output_item.done` | 블록 완성. 추론은 요약 글과 서명(원본 항목 JSON), 글은 서명(`textSignature`), 도구 호출은 인자 확정하고 임시 필드 제거 | `thinking_end` / `text_end` / `toolcall_end` |
| `response.completed`, `response.incomplete` | 사용량 계산, 종료 사유 변환 (§5.3) | (없음) |
| `error`, `response.failed` | 예외를 던짐 | |

- OpenAI는 블록 번호를 **`output_index`**(응답 항목 순번)로 주고, 이 함수는 `outputSlots`라는 표(`output_index` → 블록)로 관리한다(`:441`, `:464-533`). `contentIndex`는 Claude, completions와 같이 `output.content` 배열 위치다.
- **Claude, completions와 달리 블록이 끝나는 즉시 `*_end`를 낸다**(`response.output_item.done`마다). 03-3 §4.2에서 본 completions는 스트림이 끝난 뒤 한꺼번에 낸다.
- `thinkingSignature`에는 **추론 항목 원본을 JSON 문자열로** 저장한다(`:692`). 요청에 되돌릴 때 §4.5에서 그대로 `JSON.parse`해서 쓴다. Azure 같은 서버는 `output_item.done`에 `encrypted_content`를 빼고 `response.completed`에만 담는 경우가 있어서, 종료 때 빠진 서명을 채우는 코드가 있다(`backfillReasoningSignatures`, `:534-551`, 이슈 #6409).

### 5.2 실험: 가짜 이벤트로 변환 과정 확인 (`실행 확인`)
`:433-809`를 줄 범위 그대로 복사하고(`parseStreamingJson`만 `partial-json`이 설치되어 있지 않아 간단히 대체, `calculateCost`와 `AssistantMessageEventStream`은 실제 파일을 사용) 서버가 보낸 것처럼 만든 이벤트 15개를 넣었다. 스크립트는 `artifacts/pi/ai-demos/responses-stream-demo.ts`, 출력은 `responses-stream-demo.2026-10-05.log`다. 입력 이벤트는 형식을 보이려는 예시이고 실제 서버 응답이 아니다.

```
서버 이벤트 15개 → pi 이벤트 12개:
  thinking_start, thinking_delta ×2, thinking_end,
  text_start,     text_delta ×2,     text_end,
  toolcall_start, toolcall_delta ×2, toolcall_end

최종 output:
  content: thinking, text, toolCall(read {"path":"a.ts"} id=call_1|fc_1)
  stopReason: toolUse     (서버 status는 completed, 도구 호출이 있어서 toolUse로 보정됨)
  usage: {"input":60,"output":20,"cacheRead":40,"reasoning":5,"totalTokens":120}
  cost : {"input":0.0003,"output":0.0003,"cacheRead":0.00002,"cacheWrite":0,"total":0.00062}
  thinkingSignature 있음: true   textSignature: {"v":1,"id":"msg_1"}
```
- 이벤트 15개 중 3개(`response.created`, `response.function_call_arguments.done`, `response.completed`)는 pi 이벤트를 만들지 않았다. `function_call_arguments.done`은 앞서 모은 인자와 같아서 남은 조각이 없기 때문이다.
- **도구 호출 ID가 `call_1|fc_1`**(`call_id|item.id`)로 만들어진 것이 확인된다(§4.5의 ID 규칙).
- **`input_tokens`(100)에서 캐시 읽기(40)를 뺀 60이 `usage.input`**이 되었고, 비용은 모델 가격(예시 값 $5/$15/$0.5 per 백만 토큰)으로 계산되었다.

### 5.3 사용량, 비용, 종료 사유 (`finalizeResponse`, `:552-597`)
- **토큰 수는 응답 마지막(`response.completed`)에 한 번만 받는다.** Claude(시작과 끝 두 번, 03-1 §5.2)와 달리 `calculateCost`도 한 번 부른다(`:577`).
- OpenAI의 `input_tokens`에는 캐시 읽기와 캐시 쓰기 토큰이 **포함**되어 있다. 그래서 `input = input_tokens - cached_tokens - cache_write_tokens`로 계산하고 `cacheRead`, `cacheWrite`를 따로 채운다(`:561-575`). 추론 토큰은 `output_tokens_details.reasoning_tokens`에서 `usage.reasoning`으로 옮긴다.
- **서비스 등급 배수** (`applyServiceTierPricing`, `openai-responses.ts:387-415`): `flex` 0.5배, `priority`와 `fast` 2배(모델이 `gpt-5.5`이면 `priority`/`fast` 2.5배). 비용 네 항목에 곱하고 합계를 다시 낸다.
- **종료 사유 변환** (`mapStopReason`, `:779-809`)
  | OpenAI `status` | pi `StopReason` | 비고 |
  |---|---|---|
  | `completed` | `stop` | |
  | `incomplete` + `max_output_tokens` | `length` | |
  | `incomplete` + 다른 사유 | `error` | 사유를 `errorMessage`에 담음 |
  | `failed`, `cancelled` | `error` | |
  | `in_progress`, `queued`, 없음 | `stop` | 주석: "wonky" |
- **도구 호출이 있으면 `toolUse`로 바꾼다**(`:594-596`). 서버는 완료 상태만 알려 주므로 pi가 `output.content`에 `toolCall`이 있는지로 판단한다. 실험 결과에서 확인했다.
- `message`의 `phase`가 `final_answer`이면 종료 사유를 `stop`으로 고정한다(`:443-447`).
- **미완성 도구 호출 방지** (`:763-776`): `stopReason`이 `toolUse`인데 `output_item.done`이 오지 않아 임시 버퍼가 남은 도구 호출이 있으면 **예외를 던진다.** 주석: "에이전트가 최종 메시지의 모든 도구 호출을 실행하므로, 인자가 잘렸거나 섞인 호출을 넘기지 않는다."
- 종료 이벤트가 하나도 없이 스트림이 끝나면 "OpenAI Responses stream ended before a terminal response event"로 실패한다(`:760-762`).

## 6. 오류 처리
- 큰 틀은 03-1과 같다(`:214-232`): `catch`에서 임시 필드를 지우고(`index`, `partialJson`, `customInput`), 취소 신호가 있으면 `aborted`, 아니면 `error`로 정하고, `errorMessage`를 담아 `error` 이벤트를 push한 뒤 `end()`한다. 예외를 밖으로 던지지 않는다.
- 오류 문구: `formatProviderError(normalizeProviderError(error), "<provider> API error")`. provider가 `openai`이면 이름을 `OpenAI`로 쓴다(`:222-225`). 두 함수(`utils/error-body.ts`)는 읽지 않았다(`미확인`).
- **ChatGPT 구독 한도 안내** (`:226-229`): 오류 문구에 `subscription_sharing_usage_limit_exceeded`가 들어 있으면 "Check your ChatGPT usage: https://chatgpt.com/settings/usage"를 덧붙인다(`CHATGPT_USAGE_URL`, `:34`). 구독 로그인으로 쓰다가 한도가 찼을 때의 처리다. `CHANGELOG.md`에도 "Subscription usage-limit errors are not retried and link to the ChatGPT usage page; temporary usage errors are retried"라고 적혀 있다. 재시도 규칙은 `utils/provider-retry.ts`에 있고 아직 읽지 않았다(`미확인`).

## 7. ChatGPT 구독 로그인: `auth/oauth/openai-chatgpt.ts` (현재 경로의 로그인)
`openai` provider의 `oauth`가 이 파일이다(`providers/openai.ts`, `lazyOAuth`, 선택 화면 라벨 `"Sign in with ChatGPT"`). 04-auth §6.3에서는 절반만 읽었고 이번에 거의 다 읽었다.

### 7.1 공식 문서와의 대응 (웹 확인)
OpenAI 개발자 문서([Sign in with ChatGPT: 토큰 공유(오픈소스 앱)](https://developers.openai.com/siwc/token-sharing-open-source/sign-in))는 이렇게 설명한다.
- 받은 토큰은 `resource` 파라미터로 지정한 **`https://api.openai.com/v1`**에서 쓴다.
- 요청하는 범위(scope)는 신원용 `openid profile email`과, 구독 한도 사용을 위한 `offline_access resource.invoke chatgpt.tokens.use.direct`다.
- `dynamic_agent_client`는 **첫 등록용 진입점**이고, 토큰 교환에는 콜백에서 돌려받은 발급된 `client_id`를 써야 한다.

pi 코드는 이것과 그대로 일치한다(`openai-chatgpt.ts:16`, `:21`, `:26-27`: `DYNAMIC_CLIENT_ID = "dynamic_agent_client"`, `RESOURCE = "https://api.openai.com/v1"`, `SCOPE`에 `offline_access resource.invoke chatgpt.tokens.use.direct`가 들어 있음). 이 공식 문서는 예전 Codex 전용 백엔드(`chatgpt.com/backend-api/codex`)나 그 폐기에 대해서는 말하지 않는다(`미확인`).

### 7.2 로그인 흐름 (`loginOpenAIChatGPT`, `:233-299`)
```
1. 설치 ID 확인: options.getDeviceId() 가 UUID 가 아니면 "requires a device ID" 오류           (:237, :225-231)
     OpenAI가 이 설치를 구분하는 "agent host" ID 로 urn:uuid:<uuid> 를 쓴다
2. PKCE verifier/challenge, 무작위 state, nonce 생성                                        (:238-240)
3. 로컬 콜백 서버 시작 (127.0.0.1:1455 /auth/callback). 포트가 사용 중(EADDRINUSE)이면 **오류로 중단** (:243-249, :85-132)
4. 로그인 주소를 사용자에게 알림 (auth_url 이벤트)                                           (:251-270)
     https://auth.openai.com/api/accounts/authorize
       ?client_id=dynamic_agent_client &agent_name_hint=Pi &ext_agent_host_id=urn:uuid:...
       &response_type=code &redirect_uri=... &resource=https://api.openai.com/v1
       &scope=... &state=... &code_challenge=...(S256) &nonce=...
5. 브라우저 콜백 또는 붙여 넣기 중 먼저 오는 것을 기다림 (Promise.race)                      (:282)
     콜백에는 code, state 와 함께 OpenAI가 발급한 client_id 가 와야 한다                    (:59-61)
     붙여 넣기는 "전체 콜백 URL"이어야 하고 주소가 redirect_uri 와 같아야 한다                (:64-78)
6. 받은 code 로 토큰 교환: POST https://auth.openai.com/api/accounts/oauth/token            (:183-206, :134-153)
     application/x-www-form-urlencoded:
       grant_type=authorization_code, client_id=(발급된 것), code, code_verifier, redirect_uri, resource
7. 검사 후 credential 생성                                                                   (:162-181, :200-205)
     id_token 이 있어야 함, scope 에 chatgpt.tokens.use.direct 가 있어야 함
     { type: "oauth", access, refresh, expires = now + expires_in - 3분, clientId, scopes }
```
- **로그인마다 클라이언트를 새로 등록한다**(`:15` 주석: "every login registers a new client with this ID; OpenAI returns the issued client ID in the callback"). 그래서 **발급된 `clientId`를 credential에 저장**하고, 갱신 때 그것을 쓴다.
- `expires`는 실제 만료보다 **3분 일찍**으로 저장한다(`EXPIRY_MARGIN_MS`, `:29`). 04 §5.1의 5분 여유와 별개의 안전 마진이다.
- 이 파일은 콜백 서버를 **자기 파일에 직접 구현**한다(`startCallbackServer`, `:85-132`). `CHANGELOG.md`는 "Anthropic, OpenAI Codex, OpenRouter, Radius의 브라우저 로그인 콜백 서버를 하나로 통합했다"고 적었는데, 이 목록에 이 파일은 없고 코드도 `auth/oauth/callback-server.ts`를 쓰지 않는다(`코드 확인`).
- 마지막 `finally`에 `callback.server.closeAllConnections()`(`:296`)가 있다. 주석: `close()`만으로는 브라우저가 미리 열어 둔 여분의 연결이 서버에 남아서, 같은 프로세스에서 다시 로그인할 때 새 콜백이 옛 서버로 가 "state mismatch"로 거부될 수 있다.

### 7.3 갱신과 요청용 인증
- **갱신** (`refreshAccessToken`, `:208-223`): 저장된 `clientId`가 없으면 "Stored OpenAI OAuth credential does not contain an issued client ID; reconnect ChatGPT"로 실패한다. 있으면 `grant_type=refresh_token`, `client_id`, `refresh_token`, `resource`를 같은 토큰 주소에 POST해서 새 토큰 쌍을 받는다. 갱신 시점과 락은 04-auth §5.1의 `resolveStoredOAuth`가 정한다.
- **`toAuth`** (`:307-309`): `{ apiKey: credential.access }`. OAuth `access` 토큰이 그대로 `options.apiKey`가 되어 이 문서 §4.1의 `getClientApiKey`로 들어오고, §4.4의 `isChatGPTSignIn`이 접두사로 이 토큰을 구분한다.
- 웹 자료(제3자 블로그, 공식 아님)는 이 방식의 액세스 토큰이 1시간, 리프레시 토큰이 30일 유효하고 갱신 때마다 교체된다고 설명한다([DEV Community](https://dev.to/hassann/sign-in-with-chatgpt-for-developers-the-oauth-flow-plan-usage-and-what-it-means-for-your-api-bill-48f7)). 이 값은 코드에서 확인하지 못했다(`미확인`).

## 8. 비교: Claude, OpenAI Responses, legacy Codex
자세한 비교는 [03-3](./03-3-api-openai-compare.md), 이 문서는 03-1과 03-4의 차이만 요약한다.
| | Claude (03-1) | OpenAI Responses (이 문서) | legacy Codex (03-4) |
|---|---|---|---|
| 요청 보내기 | `@anthropic-ai/sdk` | `openai` SDK | `fetch`와 `WebSocket` 직접 |
| 응답 SSE 해석 | **pi가 직접** (`iterateSseMessages`) | **SDK가 함** | **pi가 직접** (`parseSSE`) |
| 응답 → pi 이벤트 | 파일 안 루프 | **공용** `processResponsesStream` | **공용** `processResponsesStream` |
| 대화 변환 | 파일 안 | **공용** `convertResponsesMessages` | **공용** |
| 재시도 | 공용 `retryProviderRequest` | 공용 `retryProviderRequest` | 자체 구현 |
| 최대 출력 | `max_tokens` | `max_output_tokens`(최소 16) | 보내지 않음 |
| 인증 | API 키 또는 OAuth (Claude Code 흉내) | API 키 또는 ChatGPT 로그인(필드 일부 제거) | OAuth JWT |
| 사용량 계산 | 응답 중간과 끝 두 번 | 끝 한 번 | 끝 한 번 |

## 9. 읽지 않은 것 (`미확인`)
- `utils/provider-retry.ts`(재시도 규칙), `utils/error-body.ts`, `api/constrained-sampling.ts`, `api/openai-prompt-cache.ts`, `api/github-copilot-headers.ts`
- `api/azure-openai-responses.ts`(351줄, 같은 공용 변환기를 쓰는 형제)
- 실제 서버와의 통신, 실제 ChatGPT 로그인, 로그인 토큰의 실제 모양(`sk-` 접두사 여부)과 유효 기간
- 새 경로의 ChatGPT 로그인 토큰으로 `openai` provider의 모든 모델이 실제로 호출되는지(모델 목록에 있다는 것과 서버가 허용한다는 것은 별개)

## 10. 다음
05 utils: `retryProviderRequest`, `parseStreamingJson`, `estimateContextTokens`, `isContextOverflow`, `validation` 등 03에서 이름만 나온 것들. 06 호출 경로 종합.

## 부록 (2026-10-06): 콜백 서버 실패 처리 변경
- 이전(`3874b3e98`): 콜백 서버를 못 열면 "붙여 넣기로 진행하라"고 알리고 **계속**했다(`callback`이 `undefined`일 수 있음).
- 지금(`28dcce2ba`, `openai-chatgpt.ts:241-249`): `EADDRINUSE`이면 `Port 1455 is in use, probably by an unfinished login in another pi session or by the Codex CLI. Cancel that login and try again.` 오류로 **중단**하고, 다른 오류는 그대로 던진다. 이유(주석): 서버 없이 진행하면 브라우저 콜백이 같은 포트를 잡은 다른 프로세스(다른 로그인이나 Codex CLI)로 가서 state mismatch로 거부된다. 그래서 `callback`은 항상 존재하고 `callback?.`가 `callback.`로 바뀌었다(`:282`, `:295-296`). (`코드 확인`, 실행 안 함)
