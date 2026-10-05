# ai 03-4: 통신 코드 읽기 — `api/openai-codex-responses.ts` (OpenAI Codex, legacy)

> **이 문서는 legacy 경로를 다룬다.** `CHANGELOG.md`에 "Renamed the OpenAI Codex provider to 'OpenAI Codex (legacy)'; Sign in with ChatGPT on the `openai` provider supersedes it"라고 적혀 있다. **현재 권장 경로**는 `openai` provider(`openai-responses.ts`, ChatGPT 구독 로그인은 `auth/oauth/openai-chatgpt.ts`)이고 [03-2-api-openai-responses](./03-2-api-openai-responses.md)에 있다. 이 문서의 코드는 삭제된 것이 아니라 `openai-codex` provider로 **아직 등록되어 있고**(`providers/all.ts:162`) 계속 수정되고 있다(최근 커밋 2026-09-23). 응답 변환기(`processResponsesStream`)는 현재 경로와 **공용**이므로 그 설명은 03-2 §5에 정리되어 있다.

- **기준 commit**: `3874b3e98` / **분석일**: 2026-10-04
- **비교 문서**: [03-3-api-openai-compare](./03-3-api-openai-compare.md) (completions, responses, codex 세 통신 코드의 차이)
- **선행 문서**: [02-models-registry](./02-models-registry.md) §2.2(Codex provider), [03-1-api-anthropic](./03-1-api-anthropic.md)(같은 뼈대를 Claude로 읽음), [03-0-event-stream](./03-0-event-stream.md)(`push`, `for await`의 동작)
- **읽은 파일**: `api/openai-codex-responses.ts`(1697줄 전체), `api/openai-responses-shared.ts`의 `processResponsesStream`과 `mapStopReason`(`:433-809`). 줄 번호는 모두 이 commit 기준이다.
- **검증 수준**: 코드 읽기는 `코드 확인`. 실제 서버와 통신해서 실행한 것은 없다. 다만 SSE와 WebSocket을 읽는 함수(`parseSSE`, `parseWebSocket`)는 줄 범위 그대로 복사해서 가짜 입력으로 돌렸다(`실행 확인`, §7.0). `convertResponsesMessages`, `convertResponsesTools`, 인증(`auth/oauth/openai-codex.ts`)은 읽지 않았다(§10).

## 0. 이 문서의 질문
- `openai-codex` provider(02 §2.2)가 쓰는 통신 코드는 03-1의 Claude 코드와 **무엇이 같고 무엇이 다른가**?
- 이 파일은 왜 1697줄로 커졌는가? (Claude는 1646줄이지만 이 파일은 그중 약 절반이 WebSocket 처리다.)
- 응답 이벤트는 어떻게 pi 이벤트로 바뀌는가?

> `openai-codex` provider는 이름이 `OpenAI Codex (legacy)`다. `CHANGELOG.md:70`에 "`openai` provider의 ChatGPT 로그인이 이를 대체한다"고 적혀 있다. 이 파일은 현재도 코드에 남아 있고 `openai-codex` provider가 쓴다(`providers/openai-codex.ts`).

## 1. 한눈에 보는 구조

```
Provider "openai-codex"  (OAuth만, baseUrl https://chatgpt.com/backend-api)
  └ api: openAICodexResponsesApi()  → api/openai-codex-responses.ts (지연 로딩)
       ├ streamSimple   (:500-521)  reasoning을 reasoningEffort로 바꾸고 stream 호출
       └ stream         (:237-498)
            ① 인증 토큰에서 계정 ID를 꺼낸다            (extractAccountId)
            ② 요청 본문을 만든다                        (buildRequestBody)
            ③ 전송 방식을 고른다: WebSocket 먼저, 실패하면 SSE
            ④ 응답 이벤트를 processResponsesStream(공용)으로 pi 이벤트로 바꾼다
            ⑤ done 또는 error
```

03-1(Claude)과 같은 뼈대이고(빈 `output` 만들기, `try`/`catch`, `start`, `done`/`error`), 이 파일은 `(async () => { ... })()` 안쪽 구조도 같다. 달라지는 것은 **②요청 본문, ③전송 방식, ④응답 해석을 공용 코드에 맡기는 점**이다.

## 1.1 `stream()`의 줄 구조: 상자를 만들고, 뒤에서 채우고, 상자를 돌려준다
`stream()`(`openai-codex-responses.ts:237-498`)은 03-1의 Claude와 같은 모양이다. **"빈 상자(`AssistantMessageEventStream`)를 만들어 바로 돌려주고, 상자에 넣는 일은 뒤에서 따로 한다."** 상자가 무엇인지는 [03-0](./03-0-event-stream.md), 같은 구조를 Claude 코드로 설명한 것은 [03-1 §1.1](./03-1-api-anthropic.md)에 있다.

| 하는 일 | 줄 | 실제 코드 |
|---|---|---|
| 함수 시작 | `:237-241` | `export const stream = (model, context, options) => {` |
| **① 상자 만들기** | **`:242`** | `const stream = new AssistantMessageEventStream();` |
| 대화 정리 | `:243` | `resolveTranscript(context, ...)` |
| **② 뒤에서 일하는 함수 시작** | **`:245`** | `(async () => {` |
| ②의 끝 | **`:495`** | `})();` 끝의 `()`는 만들자마자 실행한다는 뜻 |
| **③ 상자 돌려주기** | **`:497`** | `return stream;` (괄호 없음: 상자 변수를 돌려준다) |

`streamSimple`은 `:517`에서 `return stream(model, context, {...})`로 `stream`을 **호출한 결과(상자)**를 그대로 돌려준다.

### 동기로 실행되는 부분과 비동기로 실행되는 부분
② 안에서 첫 `await`는 `:278`(`await options?.onPayload?.(body, model)`)이다. `async` 함수는 첫 `await`까지 동기로 실행되므로(JavaScript 규칙) 아래 구분은 규칙과 코드 구조에서 도출한 것이다(`추론`).

| 시점 | 줄 | 하는 일 |
|---|---|---|
| `stream()`이 돌려주기 **전** (동기) | `:246-262` | 빈 `AssistantMessage`(`output`) 만들기 |
| 〃 | `:265-268` | `apiKey` 확인. 없으면 `:267`에서 던진다 |
| 〃 | `:270-277` | 계정 ID 추출, 도구 입력 정리, **요청 본문 만들기**(`buildRequestBody`) |
| `:278`의 `await`에서 양보 | | 이 뒤로는 `return stream`이 먼저 실행된다. |
| 돌려준 **뒤** (비동기) | `:282-299` | 헤더 만들기, 전송 방식 정하기 |
| 〃 | `:301-374` | **WebSocket으로 시도** (§5.1) |
| 〃 | `:376-483` | WebSocket을 안 쓰거나 실패했으면 **SSE로 전송** |
| 〃 | `:484-494` | 실패 처리 (`catch`) |

동기 구간에서 난 예외(`:267`의 인증 없음, 계정 ID 추출 실패 등)는 `try`(`:264`)/`catch`(`:484`) 안에 있어서 밖으로 던져지지 않고 **`error` 이벤트로 상자에 들어간다.** (Claude 코드와 같은 성질. `추론`)

### 상자에 넣는 곳 (`stream.push`)
03-1과 달라지는 점이 있다. **Claude 코드는 `text_delta` 같은 이벤트를 이 파일 안에서 push하지만, Codex 코드는 `start`와 `done`/`error`만 이 파일에서 push하고 나머지는 공용 변환기가 push한다.**

| 위치 | 줄 | 실제 코드 | 언제 |
|---|---|---|---|
| 이 파일 | **`:319`** | `stream.push({ type: "start", partial: output })` | WebSocket으로 **첫 이벤트가 도착했을 때** (`onStart` 콜백, `:315-321`) |
| 〃 | `:473` | `stream.push({ type: "start", partial: output })` | SSE 응답 헤더를 받고 본문을 읽기 직전 |
| 〃 | `:308` | `await processWebSocketStream(...)` | WebSocket 경로에서 이벤트를 읽고 변환 |
| 〃 | `:475` | `await processStream(...)` | SSE 경로에서 이벤트를 읽고 변환 |
| 〃 | `:334-339` | `stream.push({ type: "done", ... })`, `stream.end()` | WebSocket 성공 |
| 〃 | `:482-483` | `stream.push({ type: "done", ... })`, `stream.end()` | SSE 성공 |
| 〃 | `:492-493` | `stream.push({ type: "error", ... })`, `stream.end()` | 실패 (`catch`, `:484`) |
| **공용** `openai-responses-shared.ts` | `:474`, `:483`, `:502` | `thinking_start`, `text_start`, `toolcall_start` | 새 블록이 시작될 때 |
| 〃 | `:609`, `:639`, `:457` | `thinking_delta`, `text_delta`, `toolcall_delta` | 조각이 올 때마다 |
| 〃 | `:694`, `:704`, `:721` | `thinking_end`, `text_end`, `toolcall_end` | 블록이 끝날 때 |

`processResponsesStream`은 **상자(`stream`)를 인자로 받아서 그 안에서 `push`한다**(공용 `:433-439`, 호출 `:1543-1562`와 `:668-679`). 상자를 넘겨 주면 어디서든 `push`할 수 있다는 점이 `push` 방식의 장점이다(§1.3).

### 상자를 꺼내서 쓰는 쪽
03-1과 같다. `api/lazy.ts:35`의 `forwardStream`이 꺼내서 다른 상자에 넣고, 마지막 상자를 `agent/src/agent-loop.ts:414`가 꺼내 쓴다(03-0 §8).

### 실행 순서 (WebSocket 성공 경로)
```
1. openai-codex-responses.ts:242   상자를 만든다
2. openai-codex-responses.ts:245   뒤에서 일하는 함수를 시작한다 (요청 본문 만들기까지 바로 실행)
3. openai-codex-responses.ts:497   상자를 돌려준다                    ← 여기서 호출한 쪽으로 돌아간다
4. lazy.ts:35                      상자에서 꺼내려고 for await 시작 (비어 있으면 기다림)
5. openai-codex-responses.ts:308   (뒤에서) WebSocket을 연결하고 요청을 보낸다 (§1.2)
6. openai-codex-responses.ts:319   (뒤에서) 첫 이벤트가 오면 start 를 상자에 넣음
7. openai-responses-shared.ts:639  (뒤에서) 글 조각이 올 때마다 text_delta 를 상자에 넣음 → 4번이 꺼내 감
8. openai-codex-responses.ts:334   (뒤에서) done 을 넣고 339번에서 상자를 닫음
```
SSE 경로에서는 5번이 `:400`의 `fetch`, 6번이 `:473`이 된다.

## 1.2 실제 API 호출은 어디이고, 서버 조각은 무엇인가
**이 파일은 OpenAI SDK를 쓰지 않는다.** `:2-7`의 `import`는 모두 `import type`이라 타입 이름만 가져오고 실행 중에는 지워진다. `Tool as OpenAITool`, `ResponseCreateParamsStreaming`, `ResponseInput`은 요청의 모양이고, `ResponseStreamEvent`는 변환기에 넘기는 이벤트의 모양이다. 반면 `openai-responses.ts`는 `import OpenAI from "openai"`로 SDK를 실제로 쓴다. Codex 코드는 `fetch`와 `WebSocket`으로 **직접 통신**한다.

**실제 요청은 전송 방식에 따라 두 곳이다.**
| 방식 | 줄 | 하는 일 |
|---|---|---|
| **WebSocket** | **`:1096`** `new WebSocketCtor(url, { headers })` (`connectWebSocket`, `:1075`) | 연결을 연다 (`acquireWebSocket`, `:1508`이 재사용 여부를 정해 부름) |
| 〃 | **`:1542`** `socket.send(JSON.stringify({ type: "response.create", ...requestBody }))` | **요청을 보낸다** |
| **SSE** | **`:400-405`** `response = await (options?.fetch ?? globalThis.fetch)(resolveCodexUrl(model.baseUrl), { method: "POST", headers: sseHeaders, body: sseBody, signal })` | 요청을 보낸다 (재시도 반복문 `:390-461` 안) |

- 앞에서 만든 요청 본문(`body`)이 `stream: true`로 나가므로 서버는 응답을 만들어지는 대로 조금씩 보낸다(`buildRequestBody`, `:556`).
- SSE에서 `fetch`가 끝난 시점에 받은 `response`는 **응답 전체가 아니라 헤더를 받은 상태의 연결**이다(`response.ok`는 `:419`에서 확인). 본문은 이후에 조금씩 도착한다.
- **서버 조각**이란 서버가 응답을 만드는 동안 그때그때 보내 주는 데이터 한 덩어리다. SSE에서는 `response.body`의 글자 덩어리, WebSocket에서는 `message` 이벤트로 오는 메시지 하나가 조각이다.

## 1.3 왜 `stream.push`를 하는가 (03-1 §1.3과 같은 이유, Codex 쪽 근거)
같은 설명이 [03-1 §1.3](./03-1-api-anthropic.md)에 있다. 이 파일에서 확인되는 근거만 적는다(해석은 `추론`).
- `return`은 한 번뿐이다. `stream()`은 `:497`에서 이미 상자를 돌려줬으므로, 그 뒤에 오는 이벤트는 `push`로만 전달할 수 있다.
- **WebSocket은 데이터가 콜백(`message` 이벤트)으로 온다.** `parseWebSocket`(`:1307-1423`)이 직접 큐를 만들어 콜백을 `yield` 방식으로 바꾼다(§7.0). 이는 `EventStream`이 범용으로 하는 일과 같다.
- **여러 함수가 같은 상자에 넣는다.** 이 파일(`start`, `done`, `error`)과 공용 변환기(`text_delta` 등)가 모두 같은 `stream`에 `push`한다. 제너레이터라면 각 도우미 함수가 값을 위로 다시 `yield`해 주어야 한다.
- `.result()`가 필요하다. 이 파일은 `assertSuccessfulOutput`(`:110-117`)로 `output`을 검사한 뒤 `done`을 push하고, 같은 `output`이 `.result()`의 값이 된다.

## 2. 입력: `OpenAICodexResponsesOptions` (`:79-85`)
`StreamOptions`를 상속하고 Codex 전용 항목을 더한다.

| 항목 | 값 | 뜻 |
|---|---|---|
| `reasoningEffort` | `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max` | 추론 강도 |
| `reasoningSummary` | `auto`, `concise`, `detailed`, `off`, `on`, `null` | 추론 요약 방식 |
| `serviceTier` | OpenAI 서비스 등급 (`flex`, `priority` 등) | 처리 속도와 가격 등급 |
| `textVerbosity` | `low`, `medium`, `high` | 답변 길이 성향 (기본 `low`) |
| `toolChoice` | `auto`, `none`, `required` | 도구 사용 방식 |

옵션 중 `transport`(`StreamOptions`, 01 §2.4)가 이 파일에서 특히 중요하다. 값은 `sse`, `websocket`, `websocket-cached`, `auto`다(기본 `auto`, `:294`).

## 3. `streamSimple` (`:500-521`)
```
1. apiKey가 없으면 동기로 throw  (:505-508)
2. buildBaseOptions로 공통 옵션 정리
3. reasoning이 있으면 clampThinkingLevel(model, reasoning)로 모델이 지원하는 수준에 맞춤
   "off"이면 reasoningEffort를 비운다
4. stream(model, context, { ...base, reasoningEffort })
```
Claude의 `streamSimple`(adaptive/예산 두 갈래, 03-1 §3)보다 훨씬 단순하다. 변환은 `thinkingLevelMap`이 모델 데이터에 담아 두고, 실제 값 대응은 `buildRequestBody`(§4.3)에서 한다.

## 4. 요청 만들기

### 4.1 인증과 헤더 (`:1627-1697`)
이 provider는 API 키 대신 **OAuth 액세스 토큰(JWT)**을 `options.apiKey`로 받는다. 이 파일은 그 토큰에서 계정 ID를 꺼낸다.

- `extractAccountId(token)` (`:1627-1638`): 토큰을 `.`으로 나눈 가운데 부분(payload)을 base64로 풀어서 `payload["https://api.openai.com/auth"].chatgpt_account_id`를 꺼낸다. 형식이 맞지 않거나 값이 없으면 "Failed to extract accountId from token" 예외를 던진다.
- `buildBaseCodexHeaders` (`:1640-1659`): 공통 헤더. `Authorization: Bearer <토큰>`, `chatgpt-account-id`, `originator: pi`, `User-Agent`. 호출자의 `headers` 중 값이 `null`인 것은 삭제한다.
- SSE용 (`buildSSEHeaders`, `:1661-1679`): 위에 `OpenAI-Beta: responses=experimental`, `accept: text/event-stream`, `content-type: application/json`, 세션 ID가 있으면 `session-id`와 `x-client-request-id`.
- WebSocket용 (`buildWebSocketHeaders`, `:1681-1697`): `accept`, `content-type`, 기존 `OpenAI-Beta`를 지우고 `OpenAI-Beta: responses_websockets=2026-02-06`, `x-client-request-id`, `session-id`를 넣는다.

### 4.2 주소 (`:641-654`)
`baseUrl`(기본 `https://chatgpt.com/backend-api`) 뒤에 `/codex/responses`를 붙인다. 이미 붙어 있으면 그대로 둔다. WebSocket 주소는 같은 주소의 `https`를 `wss`로 바꾼다.

### 4.3 요청 본문: `buildRequestBody` (`:527-600`)
| 필드 | 값 | 비고 |
|---|---|---|
| `model` | `model.id` | |
| `store` | `false` | 서버에 대화를 저장하지 않는다. 주석: ChatGPT Codex는 `store: true`를 거부한다(`:1519`). |
| `stream` | `true` | |
| `instructions` | 맨 앞 시스템 메시지의 텍스트. 없으면 `"You are a helpful assistant."` | **시스템 프롬프트를 `input`이 아닌 `instructions` 필드로 보낸다.** |
| `input` | `convertResponsesMessages(...)` 결과 (`includeSystemPrompt: false`) | 대화 기록 |
| `text.verbosity` | `options.textVerbosity` 또는 `"low"` | |
| `include` | `["reasoning.encrypted_content"]` | 암호화된 추론 내용을 항상 받는다. 다음 요청에 되돌려 보내기 위한 것이다. |
| `prompt_cache_key` | 세션 ID (`clampOpenAIPromptCacheKey`) | 프롬프트 캐시용 |
| `tool_choice` | `options.toolChoice` 또는 `"auto"` | |
| `parallel_tool_calls` | `true` | 도구를 한 번에 여러 개 호출할 수 있다. |
| `temperature`, `service_tier` | 주어졌을 때만 | |
| `tools` | 도구가 있을 때 `convertResponsesTools(...)` | |
| `reasoning` | 아래 | |

**추론 설정** (`:582-597`)
```
reasoningEffort가 있으면
    effort = "none"이면  thinkingLevelMap.off가 정의돼 있으면 그 값, 없으면 "none"
             아니면      thinkingLevelMap[reasoningEffort] ?? reasoningEffort
    effort가 null이 아니면 reasoning = { effort, summary: reasoningSummary ?? "auto" }
reasoningEffort가 없고, 모델이 추론 지원이고, thinkingLevelMap.off가 null이 아니면
    reasoning = { effort: thinkingLevelMap.off ?? "none" }     ← 추론을 끈다
```

**Claude, OpenAI Responses와 다른 점**
- `max_output_tokens`를 보내지 않는다. 이 본문 어디에도 `options.maxTokens`가 쓰이지 않는다. (`openai-responses.ts`는 `max_output_tokens`를 보낸다, `:340-342`.)
- `compat.supportsStrictMode`의 기본값이 `true`다(`:537`). `openai-responses.ts`의 같은 항목 기본값은 `false`다(`:88`). 같은 이름의 compat 값이라도 이 두 파일에서 기본값이 다르다. 이유는 코드에 적혀 있지 않다.
- 호출자가 준 `onPayload`로 본문을 확인하거나 통째로 바꿀 수 있다(`:278-281`).

### 4.4 이 파일이 쓰는 compat 값 (`코드 확인`)
`supportsMidConvoSystemMessages`(`:243`, `:545`), `supportsOpenAIGrammarTools`(`:273`, `:538`), `supportsStrictMode`(`:537`), `supportsAdditionalTools`, `supportsToolSearch`(`:539-541`). 전부 모델 데이터의 `compat`에서 온다. 이 provider의 실제 모델 값은 확인하지 않았다(`data/openai-codex.json`은 있으나 이 문서에서는 열어 보지 않음).

## 5. 전송 방식: WebSocket 먼저, 안 되면 SSE

이 파일이 길어진 이유다. Codex 통신 코드는 전송 방식이 두 가지다.

| 방식 | 설명 |
|---|---|
| **SSE** | 요청 한 번에 서버가 응답을 조각조각 보내 주는 HTTP 방식. 03-1의 Claude와 같다. |
| **WebSocket** | 연결을 열어 두고 메시지를 주고받는 방식. 같은 연결을 **다음 요청에도 재사용**할 수 있다. |

`options.transport`의 의미 (`:294-301`, `:1518`)
| 값 | 동작 |
|---|---|
| `sse` | SSE만 쓴다. |
| `websocket` | WebSocket을 쓰되, 이전 요청과 이어 붙이는 최적화는 하지 않는다(전체 대화를 보낸다). |
| `websocket-cached` | WebSocket을 쓰고, 이어 붙이는 최적화(§5.2)를 쓴다. |
| `auto` (기본) | WebSocket을 먼저 시도하고, 실패하면 SSE로 넘어간다. 이어 붙이는 최적화도 쓴다. |

### 5.1 `stream` 안의 전송 흐름 (`:294-474`)
```
transport가 "sse"가 아니고, 이 세션이 SSE 강제 상태가 아니면 (:301)
   반복:
      processWebSocketStream(...) 시도
        성공 → done 이벤트 push 후 end, return                        (:330-340)
        실패 →
          ├ previous_response_not_found 에러면, 한 번만 다시 시도          (:345-348)
          ├ websocket_connection_limit_reached 에러가 시작 전에 나면, 한 번만 다시 시도  (:349-352)
          ├ 취소되었거나, Codex 서버/프로토콜/콜백 에러면(전송 문제가 아니면) 그대로 throw (:353-355)
          └ 그 외(전송 문제):
               진단 정보(provider_transport_failure)를 output에 기록           (:356-365)
               이 세션을 "SSE 강제" 상태로 표시                                (:366)
               WebSocket이 이미 이벤트를 내보냈다면 → throw (이미 시작된 응답은 이어 못 붙임)
               아니면 → SSE로 넘어간다                                       (:367-371)

SSE 경로 (:376-483)
   본문을 zstd로 압축 (가능할 때만)
   fetch로 POST → 응답 상태 확인 → 필요하면 재시도
   start 이벤트 push, processStream(...)
```
- **한 번 실패하면 그 세션은 계속 SSE를 쓴다.** `recordWebSocketFailure`가 세션 ID를 `websocketSseFallbackSessions`에 넣고(`:978-986`), 이후 호출은 처음부터 WebSocket을 건너뛴다(`:296-299`).
- WebSocket에서 응답이 이미 시작된 뒤에 실패하면 SSE로 다시 시도하지 않는다(중복 응답을 막기 위한 것으로 보이며 `추론`).
- `start` 이벤트는 WebSocket이든 SSE든 **첫 이벤트가 오는 순간 한 번만** push한다(`startEmitted`, `:295`, `:315-321`, `:471-474`).

### 5.2 WebSocket 연결 재사용과 "이어 붙이기" (`:865-1591`)
**연결 재사용** (`acquireWebSocket`, `:1153-1248`)
- 세션 ID와 계정 ID가 같으면 이미 열린 연결을 재사용한다. 다른 요청이 쓰는 중(`busy`)이면 새로 연결한다.
- 사용이 끝난 연결은 5분(`SESSION_WEBSOCKET_CACHE_TTL_MS`) 동안 유휴 상태로 두고 닫는다. 만든 지 55분(`SESSION_WEBSOCKET_MAX_AGE_MS`)이 넘으면 재사용하지 않는다.
- 세션 ID가 없으면 매 요청마다 새로 연결하고 끝나면 닫는다.
- 연결 시도 제한 시간은 기본 15초(`DEFAULT_WEBSOCKET_CONNECT_TIMEOUT_MS`)다.

**이어 붙이기(continuation): 서버가 직전 응답을 기억할 때만 쓰는 선택적 최적화** (`:1425-1477`, `:1518-1522`, `:1565-1580`)
- **기본은 전체 대화를 보내는 것이다.** AI 서버는 기본적으로 이전 대화를 기억하지 않는다. WebSocket이라는 통신 방식 자체가 대화를 기억해 주는 것이 아니다. pi는 항상 전체 대화(`context.messages`)를 가지고 있고, 위층(`agent-loop.ts:397-407`)은 매번 전체를 넘긴다.
- 그런데 이 Codex 통신 코드는 **서버가 "직전 응답을 기억하고 이어 붙이는" 기능을 지원하는 경우** 변경분만 보내도록 해 두었다. 요청에 `previous_response_id`("직전 응답 `r1`에 이어서")를 넣으면 서버가 `r1`까지의 대화를 알고 있다고 보고 새 입력만 받는 OpenAI Responses API의 기능이다.
  - 근거(`코드 확인`): 변경분만 보내는 요청 본문을 만드는 코드(`:1472-1476`), 서버가 `previous_response_not_found`(이전 응답을 못 찾음)를 돌려줄 수 있다고 보고 처리하는 코드(`:64`, `:345-348`), 그리고 주석 "ChatGPT Codex Responses rejects `store: true`. WebSocket continuation still works via connection-scoped previous_response_id state"(`:1519-1520`, 저장은 거부하지만 연결이 열려 있는 동안은 서버가 직전 응답 상태를 기억해 준다는 해석).
  - 추가 단서 (`코드 확인`, 모두 이 저장소 안의 기록):
    - `packages/ai/CHANGELOG.md:1046`: "Added `websocket-cached` transport support for OpenAI Codex Responses used with ChatGPT subscription auth. This keeps the same WebSocket open for a session and, after the first request, sends only new conversation items instead of resending the full chat history when possible." 프로젝트가 직접 적은 설계 설명이다.
    - `CHANGELOG.md:448`: "Fixed OpenAI Codex WebSocket sessions to retry once without a missing previous-response continuation after `previous_response_not_found` errors (#6955 ...)". 이 오류를 처리하도록 **수정이 들어간 기록**이다. 서버가 이어 붙이기를 항상 받아 주지는 않는다는 뜻으로 읽힌다(`추론`).
    - `test/openai-codex-stream.test.ts:2192-2198`, `:2412`: 두 번째 요청에 `previous_response_id: "resp_1"`이 들어가는지 확인하는 테스트. 이 테스트는 **개발자가 만든 가짜 WebSocket(`MockWebSocket`, `:2243`)**을 쓰며, 서버가 `previous_response_not_found` 오류를 돌려주는 상황도 가짜 서버가 흉내 낸다(`:2290-2298`). 즉 **pi가 어떻게 보내고 어떻게 반응하는지**를 검증하는 것이지 실제 서버의 동작을 검증하는 것은 아니다.
  - 즉 변경분 전송은 **"서버가 연결 범위로 직전 응답을 기억하는 기능" + "같은 WebSocket 연결 유지"**가 함께 있을 때 가능하다. 서버가 실제로 그렇게 동작하는지는 통신해서 확인하지 못했다(`미확인`).
- 다른 통신 코드는 이런 최적화를 하지 않는다. `anthropic-messages.ts`는 요청마다 `messages` 전체를 보내고(`:1157-1163`, `cache_control`은 서버의 앞부분 계산 재사용용이지 보내는 양을 줄이지 않는다), `openai-responses.ts`도 `previous_response_id` 없이 `store: false`로 전체 `input`을 보낸다(`:330-338`). 호출하는 쪽은 항상 전체 대화를 넘기고, **회사별 차이는 통신 코드가 안에서 처리한다**(Codex 코드는 가능하면 변경분만, 안 되면 전체).

```
이전 요청: input = [A, B]   → 서버 응답 R1 (response id = r1, 응답 항목 = [C])
이번 요청: input = [A, B, C, D]

이전 입력 + 이전 응답 항목 = [A, B, C] 가 이번 입력의 앞부분과 같다면
   → 보낼 내용: previous_response_id: "r1", input: [D]      (변경분만)
다르면
   → 전체 [A, B, C, D]를 보낸다
```
**전체를 그대로 보내는 경우**
| 경우 | 코드 |
|---|---|
| 새 연결이라 직전 응답 기억이 없다 (첫 요청이거나 연결이 끊김) | `entry.continuation`이 비어 있으면 본문 그대로 (`:1460-1465`) |
| 이번 입력이 "지난 입력 + 지난 응답"으로 시작하지 않는다 | `getCachedWebSocketInputDelta`가 `undefined` (`:1466-1470`) |
| 모델, 도구, 지침 등이 바뀌었다 | `requestBodiesMatchExceptInput`이 `false` (`:1442-1444`) |
| 서버가 `previous_response_not_found`를 돌려줌 | 상태를 지우고 한 번 더 시도 (`:345-348`, `:1581-1586`) |
| SSE로 전송 | 항상 전체를 보냄. `previous_response_id`를 쓰지 않는다 |

- 응답이 성공하면 `lastRequestBody`, `lastResponseId`, `lastResponseItems`(도구 결과 항목은 뺀 응답 내용)를 연결 항목에 저장한다(`:1565-1580`). 실패하거나 취소되면 저장한 상태를 지우고 연결을 닫는다(`:1581-1586`).
- 줄어드는 것은 **서버로 보내는 요청의 크기**다. 모델이 읽는 대화의 길이는 서버가 이어 붙이므로 그대로다. 실제로 얼마나 빨라지거나 싸지는지는 확인하지 않았다(`미확인`, 목적은 `추론`).

**WebSocket 메시지 보내기와 받기**
- 보내기: `socket.send(JSON.stringify({ type: "response.create", ...requestBody }))` (`:1542`). 본문은 압축하지 않고 JSON 그대로 보낸다(`:376-378` 주석).
- 받기: `parseWebSocket`(`:1307-1423`)이 메시지를 큐에 쌓고 `AsyncGenerator`로 꺼내 준다. 완료 이벤트(`response.completed`/`done`/`incomplete`)를 받기 전에 연결이 닫히면 "WebSocket stream closed before response.completed"로 실패한다. 유휴 제한 시간(`httpTimeoutMs`)이 있으면 그 시간 동안 이벤트가 없을 때 실패한다.

## 6. SSE 경로 상세 (`:376-483`)

### 6.1 zstd 압축 (`:208-231`, `:376-383`)
Node나 Bun 실행 환경에서 `node:zlib`의 `zstdCompressSync`(압축 수준 3)로 본문을 압축하고 `content-encoding: zstd` 헤더를 붙인다. 브라우저 환경이나 실패하면 압축하지 않고 JSON 그대로 보낸다. 주석은 "공식 Codex 클라이언트도 같은 엔드포인트에 압축해서 보낸다"고 적었다(`:58-59`).

### 6.2 재시도: 이 파일은 자체 구현이다 (`:385-461`)
03-1의 Claude와 `openai-responses.ts`는 공용 `retryProviderRequest`를 쓴다. **이 파일은 그 함수를 import하지 않고** 직접 반복문(`for attempt ...`)을 쓴다.

- `maxRetries` 기본값이 **0**이다(`DEFAULT_MAX_RETRIES`, `:54`, `:388`). 호출자가 `options.maxRetries`를 주지 않으면 재시도하지 않는다.
- 재시도할지 판단 (`isRetryableError`, `:129-137`): 상태 코드가 429, 500, 502, 503, 504이거나 오류 문구가 `rate limit`, `overloaded`, `service unavailable` 등과 맞으면 재시도한다. 단 429이면서 `Monthly usage limit reached`, `insufficient_quota`, `billing` 같은 **한도 소진 문구**이면 재시도하지 않는다(`:123-127`).
- 기다리는 시간: 서버가 `retry-after-ms` 또는 `retry-after` 헤더로 알려 주면 그 시간, 없으면 `1초 × 2^시도횟수`(지수 증가)(`:425-429`). 서버가 요청한 대기 시간이 `maxRetryDelayMs`(기본 60초)보다 길면 재시도하지 않고 "Server requested Ns retry delay (max: Ms)"로 실패한다(`:168-176`). 이는 01 §2.4의 `maxRetryDelayMs` 설명("길게 기다리라고 하면 즉시 실패시켜 상위에서 처리")과 같은 동작이다.
- 네트워크 오류도 재시도한다. 단 `usage limit`이 들어간 오류와 대기 시간 초과 오류는 제외한다(`:450-458`).
- 응답 헤더를 기다리는 제한 시간은 `timeoutMs`(`AbortSignal.timeout`)다. 초과하면 "Codex SSE response headers timed out after Nms"(`:396-409`).
- 마지막 시도 또는 재시도 불가 오류이면 `parseErrorResponse`로 사람이 읽을 문구를 만든다(§8).

### 6.3 SSE 직접 파싱: `parseSSE` (`:799-859`)
응답 본문을 `\n\n`(빈 줄)으로 나누고, 각 덩어리에서 `data:`로 시작하는 줄만 모아 JSON으로 읽는다. `[DONE]`은 무시한다. JSON이 깨졌으면 `CodexProtocolError`를 던진다. 03-1의 Claude 파서(`iterateSseMessages`)는 `\r`, `\n`, `\r\n`을 모두 처리하고 `event:` 이름도 읽는데, 이 파서는 `\n\n`만 찾고 `data:` 줄만 본다. 서버가 `\r\n\r\n`을 쓸 때의 동작은 확인하지 않았다(`미확인`).

## 7. 응답 해석

### 7.0 서버 조각을 읽는 반복문: SSE와 WebSocket (`코드 확인`, `실행 확인`)
03-1과 달리 이 파일에는 SSE 전용 타입(`ServerSentEvent` 등)이 없다. 읽는 함수가 **`Record<string, unknown>`(해석된 JSON 객체)**을 바로 내보낸다. 전송 방식에 따라 읽는 함수가 다르고, 그 뒤는 같다.

```
[SSE]       response.body (바이트 덩어리)
              └ parseSSE (:799-859)           글자 덩어리 → 이벤트 한 건 → JSON 객체
[WebSocket] socket의 'message' 이벤트 (콜백)
              └ parseWebSocket (:1307-1423)    메시지 → 큐 → JSON 객체
                  └ (WebSocket만) startWebSocketOutputOnFirstEvent (:1479-1491)  첫 객체가 올 때 start를 push하도록 알림
        ▼ 둘 다
    mapCodexEvents (:743-788)      for await (:749): 오류 이벤트 처리, 종료 이벤트를 response.completed로 통일
        ▼
    processResponsesStream (공용 openai-responses-shared.ts:433)   for await (:599): 객체 → pi 이벤트 → stream.push
```
반복문별 역할은 이렇다.
| 위치 | 반복문 | 받는 것 | 하는 일 |
|---|---|---|---|
| `parseSSE` (`:811`, `:824`) | `while (true)` + `while (idx !== -1)` | 글자 덩어리 | `\n\n`으로 이벤트를 자르고 **JSON 객체를 `yield`** (여기서 SSE 이벤트가 만들어진다) |
| `parseWebSocket` (`:1382`) | `while (true)` | 큐에 쌓인 메시지 | 큐에서 꺼내 `yield`, 비었으면 잠듦 |
| `mapCodexEvents` (`:749`) | `for await` | 위의 JSON 객체 | 정리하고 `yield` |
| `processResponsesStream` (공용 `:599`) | `for await` | 정리된 이벤트 | pi 이벤트로 바꿔 **`stream.push`** |

**`parseSSE`의 처리 (`:799-859`)**
| 줄 | 하는 일 |
|---|---|
| `:802`, `:815` | `response.body.getReader()`로 `await reader.read()`: **다음 덩어리가 올 때까지 기다린다.** |
| `:819` | 바이트를 글자로 바꿔 `buffer`에 이어 붙인다. |
| `:821` | 연결이 끝났는데 `buffer`에 글자가 남아 있으면 `\n\n`을 붙여 마지막 이벤트로 취급한다. |
| `:823-826` | `buffer`에서 **빈 줄(`\n\n`)이 나올 때마다** 이벤트 한 덩어리를 잘라 낸다. |
| `:828-831` | 그 덩어리에서 `data:`로 시작하는 줄만 모아 내용을 만든다. |
| `:833-834` | 내용이 `[DONE]`이면 무시한다. |
| `:835-842` | `JSON.parse`해서 `yield`. 실패하면 `CodexProtocolError`("Invalid Codex SSE JSON") |
| `:850-858` | `finally`: 취소 신호 해제, 읽기 도구 반환 |

03-1의 Claude 파서와 다른 점: **`event:` 이름을 읽지 않고**(내용 안의 `type` 필드를 쓴다) 상태를 기록하는 메모장 없이 `\n\n`만 찾는다. 서버가 `\r\n\r\n`을 쓸 때의 동작은 확인하지 않았다(`미확인`).

**`parseWebSocket`의 처리 (`:1307-1423`)** WebSocket은 데이터가 콜백으로 오기 때문에 직접 큐를 만든다.
| 변수 | 역할 |
|---|---|
| `queue` | 도착했지만 아직 안 꺼낸 메시지 |
| `pending` | 잠든 소비자를 깨울 열쇠(`resolve`) 하나 |
| `done`, `failed`, `sawCompletion` | 끝났는지, 실패했는지, 완료 이벤트를 받았는지 |

- `onMessage`(`:1325-1349`): 메시지를 글자로 바꿔 `JSON.parse`하고, 완료 이벤트(`response.completed`, `response.done`, `response.incomplete`)이면 `sawCompletion = true`, `done = true`로 하고 **`queue.push` 후 `wake()`**로 잠든 소비자를 깨운다.
- 반복문(`:1382-1409`): 큐에 있으면 `yield`, 비었고 `done`이면 종료, 아니면 `pending = resolve`로 열쇠를 맡기고 `await`로 잠든다(유휴 제한 시간이 있으면 같이 건다).
- 반복이 끝난 뒤(`:1411-1416`): `failed`가 있으면 던지고, 완료 이벤트 없이 끝났으면 "WebSocket stream closed before response.completed"로 실패한다.
- 이 구조는 [03-0](./03-0-event-stream.md)의 `EventStream`과 같다(큐 + 깨우는 열쇠). 다른 점은 소비자가 하나뿐이라서 열쇠 목록(`waiting`) 대신 하나(`pending`)만 둔다는 것이다.

**실험: 복사한 코드로 확인** (`artifacts/pi/ai-demos/codex-transport-demo.ts`, 로그 `codex-transport-demo.2026-10-05.log`)
`parseSSE`(`:799-859`)와 `parseWebSocket`(`:1307-1423`) 및 필요한 보조 코드를 줄 범위 그대로 복사해서 돌렸다. 입력은 형식을 보이려는 예시이고 실제 서버 응답이 아니다.

*SSE*: 원본 315글자를 29글자씩 11개 덩어리로 잘라 보냈다(첫 덩어리가 `"event: response.created\ndata:"`로 끝나서 이벤트가 덩어리 사이에서 잘림).
```
[SSE] 객체 1개: type=response.created
[SSE] 객체 1개: type=response.output_text.delta delta="안"
[SSE] 객체 1개: type=response.output_text.delta delta="녕"
[SSE] 객체 1개: type=response.completed
[SSE] ('data: [DONE]' 은 무시되어 객체가 나오지 않았다)
```
덩어리가 어디서 잘려도 이벤트가 완성된 뒤에 객체로 나오고, `[DONE]`은 걸러졌다.

*WebSocket*: 가짜 소켓에 시간 간격을 두고 메시지를 보냈다.
```
[WS +  0ms] 소비자: for await (parseWebSocket) 시작
[WS + 51ms] 서버: response.created 전송
[WS + 53ms] 소비자: 'response.created' 받음
[WS +122ms] 서버: output_text.delta 2개를 연달아 전송
[WS +123ms] 소비자: 'response.output_text.delta' 받음
[WS +123ms] 소비자: 'response.output_text.delta' 받음
[WS +202ms] 서버: response.completed 전송
[WS +202ms] 소비자: 'response.completed' 받음
[WS +202ms] 소비자: for await 종료
[WS +262ms] 서버: 연결 닫음
```
- 콜백으로 도착한 메시지가 큐를 거쳐 `for await`로 하나씩 나온다. 연달아 온 두 메시지도 순서대로 나온다.
- **`response.completed`를 받으면 소비자는 연결이 닫히기를 기다리지 않고 바로 종료한다**(`+202ms`). `done = true`가 완료 이벤트에서 설정되기 때문이다(`:1334-1337`). 그 뒤의 `close`(`+262ms`)는 처리되지 않는다.

### 7.1 두 단계: `mapCodexEvents` → `processResponsesStream`
```
WebSocket 메시지 또는 SSE 데이터
   └ parseWebSocket / parseSSE                      원문 JSON 객체로 읽기
        └ mapCodexEvents (:743-788)                 Codex 특유의 이벤트를 정리
             └ processResponsesStream (공용, openai-responses-shared.ts:433)   pi 이벤트로 변환
                  └ stream.push(text_delta 등)
```
**`mapCodexEvents`가 하는 일**
- `options.onProviderStreamEvent` 콜백을 부른다. 콜백이 던진 예외는 `ProviderStreamEventCallbackError`로 감싸서, WebSocket 재시도와 SSE 폴백 대상에서 제외한다(`:751-755`).
- `type: "error"` 이벤트와 `response.failed` 이벤트는 `CodexApiError`(`code`, `payload` 포함)로 바꿔 던진다(`:759-772`).
- `response.done`, `response.completed`, `response.incomplete`는 모두 **`response.completed`로 통일**하고 `status`를 정리한 뒤 **읽기를 끝낸다**(`return`)(`:774-784`). `response.end_turn`이 있으면 `output.endTurn`에 기록한다(01의 `AssistantMessage.endTurn`).
- 나머지 이벤트는 그대로 통과시킨다.

### 7.2 `processResponsesStream`의 이벤트 변환 (공용, `openai-responses-shared.ts:599-758`)
OpenAI Responses 계열(`openai`, `openai-codex`, `azure-openai-responses`)이 함께 쓰는 변환기다. 03-1에서 `미확인`으로 남겼던 부분이다.

| OpenAI Responses 이벤트 | 하는 일 | pi 이벤트 |
|---|---|---|
| `response.created` | `output.responseId` 기록 | (없음) |
| `response.output_item.added` | 항목 종류에 따라 새 블록을 만든다: `reasoning`은 thinking, `message`는 text, `function_call`과 `custom_tool_call`은 toolCall | `thinking_start` / `text_start` / `toolcall_start` |
| `response.reasoning_summary_text.delta`, `response.reasoning_text.delta` | thinking에 덧붙임 | `thinking_delta` |
| `response.reasoning_summary_part.done` | thinking에 `"\n\n"` 추가 (요약 문단 구분) | `thinking_delta` |
| `response.output_text.delta`, `response.refusal.delta` | text에 덧붙임 (거절 문구도 글로 취급) | `text_delta` |
| `response.function_call_arguments.delta` | 인자 JSON 조각을 모으고 `parseStreamingJson`으로 해석해 `arguments` 갱신 | `toolcall_delta` |
| `response.function_call_arguments.done` | 최종 인자로 교체. 앞서 모은 것과 접두사가 같으면 남은 조각만 `delta`로 push | `toolcall_delta` |
| `response.custom_tool_call_input.delta/done` | 문법으로 제한된 도구(custom tool)의 입력을 모음 | `toolcall_delta` |
| `response.output_item.done` | 블록 완성. 추론은 요약 글과 서명(원본 항목 JSON)을 저장, 글은 서명(`textSignature`)을 저장, 도구 호출은 인자 확정하고 임시 필드 제거 | `thinking_end` / `text_end` / `toolcall_end` |
| `response.completed`, `response.incomplete` | 사용량 계산, 종료 사유 변환 (§7.3) | (없음) |
| `error`, `response.failed` | 예외를 던짐 | |

- Anthropic은 블록에 번호(`index`)가 붙어 오지만, OpenAI는 **`output_index`**(응답 항목 순번)로 오고, 이 파일은 `outputSlots`라는 표(`output_index` → 블록)로 관리한다. `contentIndex`는 Claude와 마찬가지로 `output.content` 배열 위치다.
- 이 변환기는 `thinkingSignature`에 **추론 항목 원본을 JSON 문자열로** 저장한다(`:692`). 다음 요청에 그대로 되돌려 보내기 위해서다. Claude는 `signature` 문자열 하나만 저장한다(03-1 §5.2).

### 7.3 사용량, 비용, 종료 사유 (`finalizeResponse`, `:552-597`)
- **토큰 수는 응답 마지막에 한 번만 받는다.** Claude는 시작과 끝 두 번 계산했다. 여기서는 `response.completed`에서 `usage`를 채우고 `calculateCost`를 한 번 부른다(`:577`).
- OpenAI의 `input_tokens`에는 캐시 읽기와 캐시 쓰기 토큰이 포함되어 있다. 그래서 `input = input_tokens - cached_tokens - cache_write_tokens`로 계산하고, `cacheRead`, `cacheWrite`를 따로 채운다(`:561-575`, 주석 `:567`). 추론 토큰은 `output_tokens_details.reasoning_tokens`에서 `usage.reasoning`으로 옮긴다.
- 그 뒤 서비스 등급별 배수를 적용한다(`applyServiceTierPricing`, `:616-629`): `flex` 0.5배, `priority` 2배(`gpt-5.5`는 2.5배). 응답이 `default` 등급이라고 해도 요청이 `flex`나 `priority`였으면 요청 값을 쓴다(`resolveCodexServiceTier`, `:631-639`).
- **종료 사유 변환** (`mapStopReason`, `:779-809`)
  | OpenAI `status` | pi `StopReason` | 비고 |
  |---|---|---|
  | `completed` | `stop` | |
  | `incomplete` + `max_output_tokens` | `length` | |
  | `incomplete` + 다른 사유 | `error` | 사유를 `errorMessage`에 담음 |
  | `failed`, `cancelled` | `error` | |
  | `in_progress`, `queued`, 없음 | `stop` | 주석: "wonky" |
- **도구 호출이 있으면 `toolUse`로 바꾼다.** 위에서 `stop`이 되었어도 `output.content`에 `toolCall`이 하나라도 있으면 `stopReason`을 `toolUse`로 고친다(`:594-596`). Claude는 서버가 `tool_use`를 직접 알려 주지만(`mapStopReason`, 03-1 §5.4), OpenAI는 완료 상태만 알려 주므로 pi가 도구 호출 유무로 판단한다.
- `message`의 `phase`가 `final_answer`이면 종료 사유를 `stop`으로 고정한다(`:443-447`).
- **미완성 도구 호출 방지** (`:763-776`): `stopReason`이 `toolUse`인데 `output_item.done`이 오지 않아 임시 버퍼(`partialJson`)가 남은 도구 호출이 있으면 **예외를 던진다**. 주석은 "에이전트가 최종 메시지의 모든 도구 호출을 실행하므로, 인자가 잘렸거나 섞인 호출을 넘기지 않는다"고 적었다.
- 종료 이벤트가 하나도 없이 스트림이 끝나면 "stream ended before a terminal response event"로 실패한다(`:760-762`).

## 8. 오류 처리

- **큰 틀은 03-1과 같다** (`:484-494`): `catch`에서 임시 필드를 지우고, 취소 신호가 있으면 `aborted`, 아니면 `error`로 정하고, `errorMessage`를 담아 `error` 이벤트를 push한 뒤 `end()`한다. 예외를 밖으로 던지지 않는다.
- 오류 문구는 `formatProviderError(normalizeProviderError(error))`로 만든다. 이 두 함수(`utils/error-body.ts`)는 읽지 않았다(`미확인`).
- **ChatGPT 한도 안내** (`parseErrorResponse`, `:1596-1621`): 응답이 429이거나 오류 코드가 `usage_limit_reached`, `usage_not_included`, `rate_limit_exceeded`이면 `"You have hit your ChatGPT usage limit (<요금제> plan). Try again in ~N min."`이라는 친절한 문구를 만든다. 요금제는 `plan_type`, 남은 시간은 `resets_at`에서 계산한다.
- WebSocket에서 난 오류의 종류는 `CodexApiError`(서버가 보낸 오류), `CodexProtocolError`(JSON이 깨짐 등), `WebSocketCloseError`(연결 종료 코드, 크기 초과 1009는 "message too big" 문구 추가)다. 서버가 보낸 오류와 프로토콜 오류는 SSE로 폴백하지 않고 그대로 실패시킨다(§5.1).

## 9. 비교: 세 통신 코드

| | Anthropic Messages (03-1) | OpenAI Responses (03-1 §8) | OpenAI Codex (이 문서) |
|---|---|---|---|
| 요청 보내기 | SDK `client.beta.messages.create` | SDK `client.responses.create` | `fetch`(SSE) 또는 `WebSocket`을 직접 사용 (SDK 없음) |
| 인증 | API 키 또는 OAuth, Claude Code 흉내 | API 키 또는 ChatGPT 로그인 | OAuth JWT에서 계정 ID 추출 |
| 시스템 프롬프트 | `system` | `input` 안의 메시지 | `instructions` 필드 |
| 최대 출력 | `max_tokens` | `max_output_tokens` | **보내지 않음** |
| 전송 방식 | SSE | SSE | **WebSocket 우선, SSE 폴백**, 연결 재사용, 이어 붙이기 |
| 요청 압축 | 없음 | 없음 | SSE일 때 zstd |
| 재시도 | 공용 `retryProviderRequest` | 공용 `retryProviderRequest` | **자체 구현** (기본 0회) |
| 응답 해석 | 파일 안에서 직접 | 공용 `processResponsesStream` | 공용 `processResponsesStream` (+ `mapCodexEvents`) |
| 사용량 계산 | 응답 중간과 끝 두 번 | 응답 끝 한 번 | 응답 끝 한 번 |
| 도구 호출 종료 사유 | 서버가 `tool_use`로 알려 줌 | 도구 호출이 있으면 `toolUse`로 보정 | 〃 |
| 추론 서명 | `signature` 문자열 | 추론 항목 JSON | 〃 |

**세 파일 모두 같은 것**: 빈 `AssistantMessage`를 만들고, `AssistantMessageEventStream`을 반환하고, 안쪽 비동기 함수에서 `start`, `*_start/delta/end`, `done`/`error`를 push하고, 실패를 `error` 이벤트로 알리는 뼈대. 03-1의 §8.1에서 "다른 `api/*.ts`도 같은 뼈대인지는 두 파일만 읽어서 `미확인`"이라고 했는데, 이 파일이 세 번째 확인이다.

## 10. 읽지 않은 것 (`미확인`)
- `convertResponsesMessages`, `convertResponsesTools`(`openai-responses-shared.ts:145-410`): pi 메시지를 OpenAI `input` 항목으로 바꾸는 규칙
- `auth/oauth/openai-codex.ts`: 이 provider의 OAuth 로그인과 갱신 (04에서)
- `utils/error-body.ts`(`formatProviderError`, `normalizeProviderError`), `utils/abort-signals.ts`, `utils/node-http-proxy.ts`, `session-resources.ts`(`registerSessionResourceCleanup`)
- `openai-prompt-cache.ts`(`clampOpenAIPromptCacheKey`), `constrained-sampling.ts`
- 모델 데이터 `data/openai-codex.json`의 실제 값(모델 9개가 모두 `openai-codex-responses`라는 것만 02에서 확인)
- 실제 서버와의 통신: WebSocket 폴백, 이어 붙이기가 실제로 동작하는지는 코드만 읽었다.

## 11. 다음
04 인증: `auth/*`, `env-api-keys.ts`, `auth/oauth/*`(Anthropic, OpenAI Codex 포함). 이 문서에서 본 `options.apiKey`(JWT)가 어떻게 만들어지고 갱신되는지 확인한다.
