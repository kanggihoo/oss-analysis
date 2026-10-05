# ai 03-1: 통신 코드 읽기 — `api/anthropic-messages.ts` (Claude)

- **기준 commit**: `3874b3e98` / **분석일**: 2026-10-04
- **선행 문서**: [01-types](./01-types.md), [02-models-registry](./02-models-registry.md)
- **짝 문서**: [03-2-api-openai-responses](./03-2-api-openai-responses.md) (OpenAI 현재 경로), [03-4-api-openai-codex-legacy](./03-4-api-openai-codex-legacy.md) (OpenAI Codex, legacy)
- **비교 문서**: [03-3-api-openai-compare](./03-3-api-openai-compare.md) (OpenAI 계열 통신 코드 세 가지의 차이)
- **먼저 읽으면 좋은 문서**: [03-0-event-stream](./03-0-event-stream.md) (`stream.push`, `for await`, `.result()`가 무엇인지)
- **읽은 파일**: `api/anthropic-messages.ts`(1646줄 전체), `api/simple-options.ts`, `api/transform-messages.ts`(235줄 전체), `utils/transcript.ts`(나머지 부분), `utils/event-stream.ts`, 비교용으로 `api/openai-responses.ts`(415줄 전체)와 `openai-responses-shared.ts`(함수 목록과 이벤트 분기). 줄 번호는 모두 이 commit 기준이다.
- **검증 수준**: 코드 읽기는 `코드 확인`. 실제 서버와 통신해서 실행한 것은 없다. 모델 값은 02에서 `실행 확인`한 `data/anthropic.json`(2026-10-04 생성)을 인용했다. 읽지 않은 파일은 §9에 적었다.

## 0. 이 문서의 질문
02에서 `Provider.stream()`이 "`model.api`에 맞는 통신 코드를 호출한다"고 했다. 그 **통신 코드 안에서 실제로 무슨 일이 일어나는가**를 Claude(`anthropic-messages`) 하나로 끝까지 따라간다.

1. 우리가 넘긴 `model`, `context`, `options`가 Anthropic 요청으로 어떻게 바뀌는가?
2. Anthropic이 보내는 응답은 어떻게 `AssistantMessageEvent`로 바뀌는가?
3. `compat`, `reasoning` 같은 값은 어디서 쓰이는가?
4. 실패하면 어떻게 되는가?

## 1. 한눈에 보는 구조

`api/anthropic-messages.ts`는 아래 두 함수를 내보낸다(`ProviderStreams` 계약, 01 §2.9).
| 내보내는 것 | 줄 | 역할 |
|---|---|---|
| `stream` | 573-903 | 실제 통신을 하는 함수. Anthropic 전용 옵션(`AnthropicOptions`)을 받는다. |
| `streamSimple` | 930-978 | `reasoning` 같은 통일된 옵션을 Anthropic 옵션으로 바꾼 뒤 `stream`을 부른다. |

```
streamSimple(model, context, options)     ← 간편 옵션을 Anthropic 옵션으로 변환 (§3)
   └ stream(model, context, anthropicOptions)
        ① 빈 AssistantMessage(output)를 만든다
        ② 요청을 만든다                       (§4: 클라이언트, 요청 본문, 헤더)
        ③ 서버에 보낸다 (실패 시 재시도)
        ④ 응답을 한 조각씩 읽으며 pi 이벤트로 바꿔 push 한다   (§5)
        ⑤ done 또는 error 이벤트로 끝낸다                    (§6)
```

**02에서 말한 "inner 스트림"이 바로 이 `stream` 함수가 만드는 `AssistantMessageEventStream`이다.** `stream`은 `new AssistantMessageEventStream()`을 만들고(`:578`), 즉시 반환하면서(`:902`) 안쪽 비동기 함수(`:582-900`)에서 이벤트를 `push`한다. `lazyStream`의 `forwardStream`이 이것을 outer로 복사한다.

## 1.1 `stream()`의 줄 구조: 상자를 만들고, 뒤에서 채우고, 상자를 돌려준다
`stream()`(`anthropic-messages.ts:573-903`)이 하는 일은 **"빈 상자(`AssistantMessageEventStream`)를 만들어 바로 돌려주고, 상자에 넣는 일은 뒤에서 따로 한다"**는 것이다. 상자가 무엇인지는 [03-0](./03-0-event-stream.md)에 있다.

| 하는 일 | 줄 | 실제 코드 |
|---|---|---|
| 함수 시작 | `:573-577` | `export const stream = (model, context, options) => {` |
| **① 상자 만들기** | **`:578`** | `const stream = new AssistantMessageEventStream();` |
| **② 뒤에서 일하는 함수 시작** | **`:582`** | `(async () => {` |
| ②의 끝 | **`:900`** | `})();` 끝의 `()`는 만들자마자 실행한다는 뜻 |
| **③ 상자 돌려주기** | **`:902`** | `return stream;` |

- `:902`의 `return stream`은 괄호가 없으므로 **함수를 부르는 것이 아니라 변수 `stream`(상자)을 돌려준다.** 함수 이름과 변수 이름이 둘 다 `stream`이라 헷갈리기 쉽다.
- `streamSimple`(`:944`, `:954`, `:972`)은 `return stream(...)`으로 `stream`을 **호출한 결과(상자)**를 그대로 돌려준다. `streamSimple`이 함수를 돌려주는 것이 아니다.

### 동기로 실행되는 부분과 비동기로 실행되는 부분
`async` 함수는 호출되면 **첫 `await`를 만날 때까지 동기적으로 실행**된다는 JavaScript 규칙이 있다. ②의 첫 `await`는 `:642`(`await options?.onPayload?.(...)`)이므로, 아래 구분은 이 규칙과 코드 구조에서 도출한 것이다(`추론`, 실행으로 확인하지 않음).

| 시점 | 줄 | 하는 일 |
|---|---|---|
| `stream()`이 돌려주기 **전** (동기) | `:584-601` | 빈 `AssistantMessage`(`output`) 만들기 |
| 〃 | `:604-640` | 인증 확인, 클라이언트 만들기 |
| 〃 | `:641` | 요청 본문 만들기 |
| `:642`의 `await`에서 양보 | | 이 뒤로는 `return stream`이 먼저 실행된다. |
| 돌려준 **뒤** (비동기) | `:646-659` | 요청 전송, 재시도, 응답 헤더 확인 |
| 〃 | `:660` | `start` 이벤트 push |
| 〃 | `:665-861` | 서버 조각을 읽으며 이벤트 push (§5) |
| 〃 | `:863-899` | `done` 또는 `error` push 후 `end()` |

동기 구간에서 난 예외(인증 없음, `buildParams` 오류 등)도 `try`/`catch`(`:603`, `:889`) 안에 있어서 던져지지 않고 **`error` 이벤트로 상자에 들어간다.** 상자를 돌려주기 전에 넣은 이벤트는 대기열에 쌓여 있다가 소비자가 나중에 꺼낸다.

### 상자에 넣는 곳 (`stream.push`)
| 줄 | 실제 코드 | 언제 |
|---|---|---|
| `:651-658` | `const response = await retryProviderRequest(...)` | (넣지 않음) 서버에 요청을 보내고 응답이 시작되기를 기다린다 |
| **`:660`** | `stream.push({ type: "start", partial: output })` | 서버가 응답을 시작했을 때 |
| `:665` | `for await (const event of iterateAnthropicEvents(...))` | 서버 조각을 하나씩 받는 반복문 시작 |
| `:705` | `stream.push({ type: "text_start", ... })` | 글이 시작될 때 |
| `:745-750` | `stream.push({ type: "text_delta", ... })` | 글 조각이 올 때마다 |
| **`:887`** | `stream.push({ type: "done", ... })` | 모든 응답이 끝났을 때 |
| **`:888`** | `stream.end()` | 상자를 닫음 |
| `:897`, `:898` | `stream.push({ type: "error", ... })`, `stream.end()` | 실패했을 때 (`catch`, `:889`) |

### 상자를 꺼내서 쓰는 쪽은 다른 파일이다
| 파일과 줄 | 코드 | 설명 |
|---|---|---|
| `anthropic-messages.ts:944` | `return stream(model, context, {...})` | `streamSimple`이 상자를 그대로 돌려줌 |
| `api/lazy.ts:35` | `for await (const event of source) { target.push(event); }` | 이 상자에서 꺼내 다른 상자에 다시 넣음 (상자가 세 개인 이유는 03-0 §8.1) |
| `agent/src/agent-loop.ts:414` | `for await (const event of response) {` | 마지막 상자에서 꺼내 실제로 사용함 |

### 실행 순서
```
1. anthropic-messages.ts:578   상자를 만든다
2. anthropic-messages.ts:582   뒤에서 일하는 함수를 시작한다 (요청 준비까지 바로 실행)
3. anthropic-messages.ts:902   상자를 돌려준다                    ← 여기서 호출한 쪽으로 돌아간다
4. lazy.ts:35                  상자에서 꺼내려고 for await 시작 (비어 있으면 기다림)
5. anthropic-messages.ts:660   (뒤에서) 응답이 시작되면 start 를 상자에 넣음
6. anthropic-messages.ts:745   (뒤에서) 글 조각이 올 때마다 text_delta 를 상자에 넣음 → 4번이 꺼내 감
7. anthropic-messages.ts:887   (뒤에서) done 을 넣고 888번에서 상자를 닫음
```
3번에서 상자를 돌려준 뒤에도 2번에서 시작한 함수는 계속 일한다. 5~7번이 그것이다.

## 1.2 실제 API 호출은 어디이고, 서버 조각은 무엇인가
**실제 API 호출은 `:651-658`이다.**
```ts
const response = await retryProviderRequest(
    () => client.beta.messages.create(params, requestOptions).asResponse(),   // :652 ← 서버에 요청을 보낸다
    { maxRetries: ..., maxRetryDelayMs: ..., signal: ... },
);
```
| 줄 | 하는 일 |
|---|---|
| `:629` | `createClient`: 요청을 보낼 도구(Anthropic SDK 객체)를 만든다. 통신은 아직 안 한다. |
| `:641` | `buildParams`: 보낼 내용을 만든다. 통신은 아직 안 한다. `stream: true`가 들어 있다(`:1164`). |
| **`:652`** | `client.beta.messages.create(params, ...)`: **서버에 요청을 보낸다.** |
| `:651` | `retryProviderRequest`: 실패하면 다시 시도하는 감싸개 |

- `stream: true`는 "응답을 한꺼번에 주지 말고 만들어지는 대로 조금씩 보내 달라"는 뜻이다.
- `.asResponse()`가 돌려주는 `response`는 **응답 전체가 아니라, 응답이 시작되었다는 신호(헤더)를 받은 상태의 연결**이다. 본문(글 내용)은 이후에 서버가 계속 조금씩 보낸다.
- **서버 조각**이란 AI가 답을 만드는 동안 서버가 그때그때 보내 주는 데이터 한 덩어리다. 응답에 5초가 걸리면 조각은 그 5초 동안 여러 번 나뉘어 도착한다.

**`:665`의 반복문은 도착한 조각을 하나씩 받아 처리한다.**
```
서버에서 조각 도착 → event로 들어옴 → 반복문 몸통 실행(665~861) → 다음 조각을 기다림 → ...
```
다음 조각이 아직 안 왔으면 `for await`가 거기서 기다린다(03-0 §6). 시간이 가장 오래 걸리는 줄이 이 줄이다. 몸통에서는 조각의 종류(`event.type`)에 따라 `output`을 갱신하고 `stream.push`를 한다(§5.2).

## 1.3 왜 `stream.push`를 하고, `yield`로 돌려주지 않는가
**왜 전처리만 하고 끝내지 않고 `push`하는가**
- 받은 조각을 모아서 `return`하면 서버가 응답을 **다 끝낼 때까지** 호출한 쪽이 아무것도 받지 못한다. 20초 걸리는 답이면 20초 동안 화면이 비어 있다가 한꺼번에 나타난다.
- 함수는 `return`을 한 번만 할 수 있다. `stream()`은 이미 `:902`에서 상자를 `return`했으므로, 그 뒤에 도착하는 수십 개의 조각을 `return`으로 전달할 수 없다. 여러 값을 시간이 지나면서 하나씩 전달할 때는 상자에 `push`한다.
- 받는 쪽은 실제로 이벤트가 올 때마다 바로 처리한다: `agent-loop.ts:414-441`에서 `text_delta`마다 `message_update`를 내보낸다.

**`yield`(비동기 제너레이터)로 해도 "올 때마다 받기"는 된다.** 사실 안쪽 `iterateAnthropicEvents`(`:532`)가 `async function*`이고 `yield event`를 한다. 즉 **서버 조각을 읽는 안쪽은 `yield`, 호출한 쪽에 돌려주는 바깥은 `push`**다. 바깥이 `push`인 이유는 아래 해석이다. 코드나 문서에 직접 적혀 있지 않아서 읽은 사실에서 도출한 `추론`이다.

| | 제너레이터(`yield`) | `EventStream`(`push`) |
|---|---|---|
| 조각이 올 때마다 받기 | 됨 | 됨 |
| 완성본 `.result()` | 없음(모아야 함) | 있음 |
| 아무도 꺼내지 않아도 요청 시작 | 안 됨(첫 `for await`에서 시작) | 됨 |
| 콜백(WebSocket 등)에서 값 넣기 | 직접 변환 필요 | `push`만 호출 |
| 오류 전달 | 보통 예외 | `error` 이벤트와 `.result()` |

근거가 된 코드 사실
1. 같은 객체를 두 가지로 쓴다: `agent-loop.ts:409`(`response.result()`)와 `:414`(`for await`). `complete()`는 이벤트를 꺼내지 않고 `.result()`만 기다린다(`models.ts:887-893`).
2. `push` 방식은 `stream()`을 호출하는 순간 요청이 나간다(`:582-900`). 제너레이터는 첫 `next()` 때까지 몸통이 실행되지 않는다(JavaScript 규칙).
3. WebSocket은 데이터가 콜백으로 온다. `openai-codex-responses.ts`의 `parseWebSocket`(`:1307-1423`)은 직접 큐와 열쇠를 만들어 콜백을 `yield` 방식으로 바꾼다. 이는 `EventStream`이 하는 일과 같은 구조다.
4. 모든 통신 코드의 반환 타입이 `AssistantMessageEventStream`으로 정해져 있다(`types.ts:286-299`, `:371-375`).

한 줄로 줄이면 "이벤트도 받고 완성본도 받아야 하고, 요청은 누가 안 꺼내도 시작되어야 해서 `yield`만으로는 부족하다"이다.

## 2. 이 파일이 받는 옵션: `AnthropicOptions` (`:233-293`)
`StreamOptions`(01 §2.4)를 상속하고 Anthropic 전용 항목을 더한다.

| 항목 | 뜻 |
|---|---|
| `thinkingEnabled` | 확장 추론(extended thinking)을 켤지 |
| `thinkingBudgetTokens` | 추론에 쓸 토큰 예산 (오래된 모델 전용, 기본 1024) |
| `effort` | 추론 강도 `low`~`max` (adaptive 추론 모델 전용) |
| `thinkingDisplay` | 추론 내용을 요약해서(`summarized`) 받을지, 비워서(`omitted`) 받을지. 기본 `summarized` |
| `interleavedThinking` | 오래된 모델에서 "인터리브 추론" 베타 헤더를 보낼지 (기본 true) |
| `toolChoice` | `auto`, `any`, `none`, 또는 특정 도구 강제 |
| `client` | 미리 만든 Anthropic SDK 객체. 주면 내부에서 클라이언트를 만들지 않는다. |

## 3. `streamSimple`: `reasoning` 한 값을 Anthropic 설정으로 바꾼다 (`:910-978`)
01에서 "`streamSimple`은 `reasoning: "high"` 같은 통일된 옵션을 회사별 설정으로 바꿔 준다"고 했는데, 그 변환이 이 부분이다.

```
streamSimple(model, context, options)
 1. 인증 확인: apiKey나 인증 헤더가 없으면 여기서 즉시 throw  (:935-937)   ← 동기 예외
 2. 공통 옵션 정리: buildBaseOptions (simple-options.ts)
 3. reasoning이 없으면 → thinkingEnabled: false 로 stream 호출        (:943-948)
 4. reasoning이 있으면
     ├ model.compat.forceAdaptiveThinking === true 이면 (:952-959)
     │     effort = mapThinkingLevelToEffort(model, reasoning)
     │     → { thinkingEnabled: true, effort } 로 stream 호출
     └ 아니면 (오래된 모델, 예산 방식) (:961-977)
           adjustMaxTokensForThinking: 추론 예산을 정하고 maxTokens를 조정
           clampMaxTokensToContext: 컨텍스트 창을 넘지 않게 자름
           → { thinkingEnabled: true, thinkingBudgetTokens } 로 stream 호출
```

- **`mapThinkingLevelToEffort`** (`:910-928`): `model.thinkingLevelMap[reasoning]`에 문자열이 있으면 그것을 쓰고, 없으면 `minimal`, `low`는 `"low"`, `medium`은 `"medium"`, 나머지는 `"high"`로 바꾼다.
- **예산 방식의 기본 예산** (`simple-options.ts`): `minimal` 1024, `low` 2048, `medium` 8192, `high` 16384 토큰. `xhigh`, `max`는 `high`로 취급한다. 예산을 잡은 뒤에도 답변용으로 최소 1024토큰은 남기도록 줄인다.
- **`buildBaseOptions`** (`simple-options.ts`): 호출자의 옵션을 `StreamOptions` 모양으로 옮기면서 `maxTokens`를 `min(요청값 또는 모델 최대값, 컨텍스트 창 - 현재 대화 추정 토큰 - 안전 여유 4096)`으로 자른다. 대화가 길수록 한 번에 받을 수 있는 출력이 줄어든다.

### 인증 오류는 두 곳에서 난다
- `streamSimple`이 부를 때 인증이 없으면 **동기로 throw**한다(`:935-937`, 01에서 본 "직접 호출하면 인증 누락만 동기 throw" 규칙이 이 코드다).
- `Models.streamSimple`을 통해 부르면 인증 확정(`applyAuth`)이 `lazyStream` 안에서 먼저 일어나고, 거기서 실패하면 `error` 이벤트가 된다(02 §4.4). 그래서 보통은 이 동기 throw에 닿지 않는다.

## 4. 요청 만들기

### 4.1 `stream`이 시작할 때 (`:573-601`)
- `resolveTranscript(context, supportsMidConvoSystemMessages)`(`:579`, 정의는 `transcript.ts:115`): 모델이 대화 중간의 시스템 메시지를 받을 수 있으면 그대로 두고, 아니면 모든 시스템 메시지를 합쳐서 **맨 앞 한 줄**로 만든다(`collapseSystemMessages`). 01에서 본 `SystemMessage`의 중간 변경 기능이 모델에 따라 이렇게 처리된다.
- 결과를 담을 빈 `AssistantMessage`(`output`)를 만든다(`:584-601`). `api`, `provider`, `model`, 0으로 채운 `usage`, `stopReason: "pending"`이다. 이후 응답을 받는 동안 이 객체를 계속 채워 나간다. 이벤트의 `partial`이 가리키는 것이 바로 이 `output`이다(01에서 "partial은 공유 객체"라고 한 이유).

### 4.2 클라이언트 만들기: `createClient` (`:984-1080`)
Anthropic 공식 SDK(`@anthropic-ai/sdk`)의 객체를 만든다. **인증 방식에 따라 세 가지 경로**가 있다.

| 경로 | 조건 | 인증 방식 |
|---|---|---|
| GitHub Copilot | `model.provider === "github-copilot"` | Bearer 토큰 + Copilot 전용 동적 헤더 (`:994-1013`) |
| OAuth | API 키에 `sk-ant-oat`가 들어 있음 (`:980-982`, `:1016-1036`) | Bearer 토큰 + **Claude Code 흉내 헤더** |
| 일반 | 그 외 | API 키 또는 헤더로 준 인증, 또는 workload identity federation (`:1038-1079`) |

**OAuth 경로의 특징**(Claude Pro/Max 구독 로그인): `user-agent: claude-cli/<버전>`, `x-app: cli` 헤더를 보내고(`:1027-1028`), 시스템 프롬프트 맨 앞에 `"You are Claude Code, Anthropic's official CLI for Claude."`를 추가하며(`:1168-1183`), 도구 이름을 Claude Code의 표준 철자(`Read`, `Write`, `Bash` 등, `:103-126`)로 바꿔 보내고 응답에서 다시 원래 이름으로 되돌린다(`fromClaudeCodeName`, `:127-134`, `:729-731`). 코드 주석은 이를 "Stealth mode: Mimic Claude Code's tool naming exactly"(`:97`)라고 적었다. 이 동작의 이유는 코드에 직접 적혀 있지 않다(`추론`: 구독 토큰이 Claude Code 형태의 요청만 받도록 되어 있어서로 보이지만 확인하지 못했다).

헤더는 여러 출처를 합친다. 기본 헤더, 세션 친화 헤더, **모델의 `headers`**, 마지막으로 **호출자가 준 `options.headers`**(뒤에 오는 것이 앞을 덮어쓴다, `mergeHeaders` `:295-303`).

### 4.3 요청 본문 만들기: `buildParams` (`:1126-1296`)
Anthropic Messages API의 요청 객체를 만든다. 순서대로 정리한다.

| 단계 | 줄 | 하는 일 |
|---|---|---|
| 캐시 설정 | 1132 | `getCacheControl`: 캐시 유지 방침을 정한다. 기본 `short`, `long`이고 모델이 지원하면 `ttl: "1h"`. `none`이면 캐시 표시를 안 붙인다 (`:71-95`). |
| 대화 변환 | 1136-1154 | `transformMessages`로 다른 모델이 만든 이력을 이 모델에 맞게 고치고(§4.4), 맨 앞 시스템 메시지를 떼어 낸 뒤 `convertMessages`로 Anthropic 형식으로 바꾼다(§4.5). |
| 기본 필드 | 1157-1166 | `model`, `messages`, `max_tokens`(옵션 또는 모델 최대값), `stream: true`, `betas` |
| 시스템 프롬프트 | 1168-1193 | 맨 앞 시스템 메시지 텍스트를 `system` 칸에 넣는다. 캐시 표시를 붙인다. OAuth면 Claude Code 문장을 앞에 더한다. |
| temperature | 1195-1203 | 값이 주어졌고, 추론이 꺼져 있고, `supportsMidConvoEffort`가 아니고, `compat.supportsTemperature`가 true일 때만 보낸다. |
| 도구 | 1205-1240 | `convertTools`로 도구 정의를 Anthropic 형식으로 바꾼다(§4.6). 마지막 도구에 캐시 표시를 붙인다. |
| 추론 설정 | 1242-1273 | §4.7 |
| metadata | 1275-1280 | `options.metadata.user_id`가 문자열이면 `metadata.user_id`로 보낸다. 다른 키는 무시한다. |
| toolChoice | 1282-1288 | 그대로 전달 |
| fallbacks | 1290-1293 | `compat.allowedFallbackModels`가 있으면 서버 쪽 대체 모델 목록으로 보낸다. |

호출자가 `options.onPayload`를 주었으면 이 요청 본문을 보내기 전에 확인하거나 통째로 바꿀 수 있다(`:642-645`).

### 4.4 `transformMessages`: 다른 모델이 만든 이력을 이 모델에 맞게 고친다 (`transform-messages.ts`)
대화 도중 모델을 바꾸면(예: GPT로 대화하다가 Claude로 교체) 이전 `AssistantMessage`는 다른 모델이 만든 것이다. 그대로 보내면 서버가 거부할 수 있어서 보내기 전에 고친다. **두 번에 걸쳐** 처리한다.

**1차 변환** (`:77-156`)
- **이미지**: 모델이 이미지를 못 받으면(`model.input`에 `"image"`가 없으면) 이미지를 `"(image omitted: model does not support images)"` 같은 문구로 바꾼다 (`:35-57`).
- **같은 모델인지 판단**: `provider`, `api`, `model id`가 모두 같아야 같은 모델이다 (`:95-98`).
- **추론(thinking) 블록**: 같은 모델이면 서명이 있는 블록을 그대로 둔다(다음 요청에 되돌려 보내야 하므로). 다른 모델이면 일반 글로 바꾸고, 가려진(redacted) 추론은 버린다 (`:101-117`). 가려진 추론은 암호화된 내용이라 같은 모델에서만 유효하기 때문이다.
- **도구 호출 ID**: 다른 모델이 만든 ID는 `normalizeToolCallId`로 바꾼다. Anthropic은 `영문, 숫자, _, -`만 허용하고 64자까지라서, 이 규칙에 맞게 바꾸고(`:1299-1301`) 대응하는 `toolResult`의 ID도 같이 바꾼다 (`:127-145`, `:83-90`). 주석에 "OpenAI Responses는 450자가 넘고 `|` 같은 문자가 들어간 ID를 만든다"고 적혀 있다(`:60-63`).
- 다른 모델이 만든 `thoughtSignature`(Google 전용)는 지운다 (`:131-134`).

**2차 변환** (`:158-234`)
- `stopReason`이 `error`나 `aborted`인 `assistant` 메시지는 **통째로 건너뛴다**. 중간에 끊긴 불완전한 응답을 다시 보내면 서버가 오류를 낼 수 있기 때문이다 (`:195-203`).
- 도구를 호출했는데 결과가 없는 경우(짝이 없는 `toolCall`)에는 `"No result provided"`라는 가짜 `toolResult`(`isError: true`)를 끼워 넣는다. 사용자가 새 메시지를 보내서 도구 흐름이 끊긴 경우도 같다 (`:167-186`, `:222-225`).
- 도구 호출과 결과 사이에 끼어든 시스템 메시지는 결과 뒤로 미룬다 (`:163-166`).

### 4.5 `convertMessages`: pi 메시지를 Anthropic 형식으로 (`:1317-1519`)
| pi 메시지 | Anthropic 형식 | 비고 |
|---|---|---|
| `UserMessage` | `{ role: "user", content }` | 빈 글은 건너뛴다. 이미지는 `base64` 블록. |
| `AssistantMessage`의 글 | `text` 블록 | 빈 글은 건너뛴다. |
| `thinking` | `thinking` 블록(서명 포함) | **서명이 없으면** 일반 글로 바꾼다. 중단된 응답의 추론이 이런 상태다. `compat.allowEmptySignature`인 모델은 빈 서명으로 그대로 보낸다 (`:1411-1445`). |
| `thinking` (redacted) | `redacted_thinking` 블록 | 암호화된 내용을 그대로 돌려 보낸다. |
| `ToolCall` | `tool_use` 블록 (`id`, `name`, `input`) | |
| `ToolResultMessage` | `tool_result` 블록 | **연속된 `toolResult`는 하나의 `user` 메시지로 합친다.** 주석: z.ai의 Anthropic 호환 서버에 필요 (`:1469-1485`). |
| 중간 `SystemMessage` | `{ role: "system", content }` | 모델이 받을 수 있을 때만 여기까지 온다. **다음 `assistant` 메시지 직전에 몰아서 낸다.** Anthropic은 `tool_use` 바로 뒤에 `tool_result`가 와야 해서 그 사이에 시스템 메시지가 끼면 거부하기 때문이다 (`:1327-1336`). |

마지막에는 **마지막 `user`/`system` 메시지의 마지막 블록에 캐시 표시(`cache_control`)를 붙인다**(`:1490-1516`). 대화 기록 전체를 캐시 대상으로 삼는 지점이다.

### 4.6 `convertTools`: 도구 정의 변환 (`:1583-1618`)
- `Tool`의 `name`, `description`, `parameters`(JSON 스키마)를 Anthropic의 `input_schema`로 옮긴다.
- 모델이 허용하면(`compat.supportsEagerToolInputStreaming`) 도구마다 `eager_input_streaming: true`를 붙인다. 도구 호출 인자를 조각조각 일찍 받기 위한 것이다. 허용하지 않는 서버에는 대신 오래된 베타 헤더(`fine-grained-tool-streaming-2025-05-14`)를 보낸다(`:1109`, `:1541-1546`).
- `strict`(스키마를 엄격하게 지키게 하는 옵션)는 `compat.supportsStrictTools`가 true일 때만 쓴다. Anthropic이 거부하는 스키마 키워드(`minimum`, `maxItems`, 일부 `format` 등)가 있으면 `strict`를 쓰지 않는다 (`:1548-1581`).
- 마지막 도구에 캐시 표시를 붙인다(`compat.supportsCacheControlOnTools`가 true일 때).

**도구 변경을 서버가 직접 지원하는 경우** (`nativeToolChanges`, `:1142-1146`, `:1206-1228`): 모델이 `supportsMidConvoSystemMessages`와 `supportsMidConvoToolChanges`를 모두 지원하고 처음부터 도구가 있으며 같은 이름의 도구를 다시 정의한 적이 없으면, 처음 도구만 활성으로 보내고 **나중에 추가되는 도구는 `defer_loading: true`로 미리 선언**해 둔다. 대화 중에 `tool_addition` 블록으로 켜는 방식이다. 주석에 따르면 이렇게 하면 도구가 바뀌어도 앞부분 캐시가 깨지지 않는다(요청 수준의 도구 목록은 늘어나기만 한다). 도구가 바뀔 때 캐시가 전부 무효화된 것을 측정했다는 주석도 있다(`:199-205`).

### 4.7 추론(thinking) 설정 (`:1242-1273`)
```
if (model.compat.supportsMidConvoEffort)                      ← Opus 5.5 같은 최신 모델
    thinking = { type: "adaptive", display, block_binding: {...} }
    output_config = { effort: "high" }
    (대화에 시스템 메시지로 현재/과거 effort를 끼워 넣는다. insertThinkingLevelMessages)
else if (model.reasoning)
    if (thinkingEnabled)
        if (forceAdaptiveThinking)  thinking = { type: "adaptive", display }, output_config = { effort }   ← adaptive
        else                         thinking = { type: "enabled", budget_tokens, display }               ← 예산 방식
    else if (thinkingEnabled === false && thinkingLevelMap.off !== null)
        thinking = { type: "disabled" }
```
- **adaptive**: 모델이 언제, 얼마나 생각할지 스스로 정한다. **예산 방식**: 정한 토큰 수까지 생각한다.
- 추론을 끌 수 없는 모델(`thinkingLevelMap.off === null`)은 `disabled`를 보내지 않는다.
- 오래된 모델에 인터리브 추론(도구 호출 사이에도 생각)을 쓰려면 베타 헤더(`interleaved-thinking-2025-05-14`)를 보낸다. adaptive 모델은 이것이 내장되어 있어 보내지 않는다 (`:1110-1117`).

### 4.8 베타 헤더: `getBetaFeatures` (`:1082-1124`)
Anthropic의 시험 기능은 요청의 `betas`로 켠다. 모델 설정에 `anthropic-beta` 헤더가 직접 있으면 그것만 쓰고(`null`이면 하나도 안 보냄), 없으면 상황에 따라 계산한다.
- OAuth 토큰이면 `claude-code-20250219`, `oauth-2025-04-20`
- 도구가 있는데 eager 스트리밍을 못 쓰는 서버면 `fine-grained-tool-streaming-...`
- 오래된 추론 모델이면 `interleaved-thinking-...`
- `allowedFallbackModels`가 있으면 `server-side-fallback-...`
- `supportsMidConvoEffort`이면 `mid-conversation-output-config-...`, `thinking-binding-controls-...`
- `nativeToolChanges`이면 `mid-conversation-tool-changes-...`

## 5. 응답 해석: Anthropic 이벤트를 pi 이벤트로 바꾼다

### 5.1 SSE를 직접 읽는다 (`:381-571`)
**SSE(Server-Sent Events)**는 서버가 연결을 열어 둔 채로 응답을 조각조각 계속 보내 주는 방식이다. 앞에서 "스트림 객체는 SSE 연결이 아니다"라고 했는데, 그 SSE 연결을 읽는 코드가 바로 이 파일 안에 있다.

```
서버 응답(response.body) ─ iterateSseMessages ─► {event, data} 한 건씩        (:473-530)
                         ─ iterateAnthropicEvents ─► 파싱된 Anthropic 이벤트   (:532-571)
                         ─ stream 안의 for await 루프 ─► pi 이벤트로 push      (:665-861)
```
- `iterateSseMessages`: 바이트 스트림을 줄 단위로 읽고, 빈 줄이 나올 때마다 이벤트 한 건(`event:` 이름 + `data:` 내용)을 내보낸다. `\r\n`, `\n`, `\r` 모두 처리한다. 취소 신호(`signal.aborted`)가 오면 중단한다.
- `iterateAnthropicEvents`: 이벤트 이름이 `error`이면 예외를 던진다. 알려진 6가지 이름(`message_start`, `message_delta`, `message_stop`, `content_block_start`, `content_block_delta`, `content_block_stop`) 외에는 무시한다. `data`는 JSON 복구가 가능한 파서(`parseJsonWithRepair`)로 읽고, 실패하면 원문(raw)을 포함한 에러를 던진다. `message_start`는 받았는데 `message_stop`이 없으면 "ended before message_stop"으로 실패한다.
- SDK로 요청은 보내지만(`client.beta.messages.create(...).asResponse()`, `:652`) 응답 해석은 SDK의 스트림 객체 대신 이 파일이 직접 한다. 이유는 코드에 적혀 있지 않다(`추론`: 비표준 서버와 중간 프록시의 응답, 원문 보존 때문으로 보인다).

### 5.1.1 `iterateAnthropicEvents`: 서버 연결에서 조각을 읽어 오는 3단계
`stream()`의 `for await` 반복문(`:665`)이 읽는 것이 `iterateAnthropicEvents`(`:532-571`)다. 이 함수는 안쪽의 `iterateSseMessages`(`:473-530`)를 다시 읽는다. **비동기 제너레이터(`async function*`)가 겹쳐 있는 구조**다.

```
서버 연결(response.body, 바이트 덩어리)
   └ iterateSseMessages     (:473-530)   바이트 → 글자 → "줄" → SSE 이벤트 한 건 { event, data, raw }
        └ iterateAnthropicEvents (:532-571)   SSE 한 건 → JSON 해석 → Anthropic 이벤트 한 건
             └ stream() 안의 for await (:665)   Anthropic 이벤트 한 건 → pi 이벤트로 바꿔 push
```
각 단계는 다음 단계가 "하나 줘"라고 요청할 때 위 단계에서 하나를 가져온다. 서버 연결에서 읽는 일은 맨 아래 `reader.read()` 한 곳에서만 일어난다.

**1단계: `iterateSseMessages`(바이트를 SSE 이벤트로)**
| 줄 | 하는 일 |
|---|---|
| `:477` | `body.getReader()`로 연결에서 덩어리를 읽는 도구를 얻는다. |
| `:484-486` | 취소 신호(`signal.aborted`)가 왔으면 "Request was aborted"로 중단한다. |
| `:488` | `await reader.read()`: **다음 덩어리가 도착할 때까지 기다린다.** 이 줄이 서버를 기다리는 곳이다. |
| `:493` | `decoder.decode(value, { stream: true })`: 바이트를 글자로 바꿔 `buffer`에 이어 붙인다. `stream: true`는 한글처럼 여러 바이트인 글자가 덩어리 사이에서 잘려도 이어서 처리하게 한다(JavaScript `TextDecoder`의 동작). |
| `:494-502` | `buffer`에서 **한 줄**씩 잘라 낸다(`consumeLine`, `:456-471`). 줄바꿈은 `\r`, `\n`, `\r\n` 모두 인정한다. 줄바꿈이 아직 없으면(`null`) 다음 덩어리를 기다린다. |
| `:497` | 줄 하나를 `decodeSseLine`(`:418-442`)에 넣는다. |
| `:498-500` | `decodeSseLine`이 이벤트 한 건을 완성해 돌려주면 `yield`한다. |
| `:505-526` | 연결이 끝났으면 남은 글자와 마지막 이벤트를 마저 처리한다. |
| `:527-529` | `finally`: 연결 읽기 도구를 풀어 준다. |

`decodeSseLine`(`:418-442`)이 줄 하나를 처리하는 규칙은 이렇다.
- **빈 줄**: 지금까지 모은 것을 이벤트 한 건으로 완성한다(`flushSseEvent`, `:402-416`). SSE는 빈 줄이 "이벤트 하나의 끝"이다.
- `:`로 시작하는 줄: 주석이므로 무시한다.
- `event: 이름` 줄: 이벤트 이름을 기록한다.
- `data: 내용` 줄: 내용을 모은다(여러 줄이면 `\n`으로 합친다). 콜론 뒤 공백 하나는 제거한다.

**2단계: `iterateAnthropicEvents`(SSE 이벤트를 Anthropic 이벤트로)**
| 줄 | 하는 일 |
|---|---|
| `:536-538` | 응답 본문이 없으면 예외 |
| `:543` | `for await (const sse of iterateSseMessages(...))`: 위 1단계에서 이벤트를 하나씩 받는다. |
| `:544-546` | 이벤트 이름이 `error`이면 `sse.data`를 메시지로 예외를 던진다. |
| `:548-550` | 이벤트 이름이 아래 6개가 **아니면 건너뛴다**: `message_start`, `message_delta`, `message_stop`, `content_block_start`, `content_block_delta`, `content_block_stop`(`:393-400`). 연결 유지용 `ping` 같은 이벤트가 여기서 버려진다. |
| `:553` | `parseJsonWithRepair`로 `sse.data`를 JSON 객체로 해석한다. |
| `:554-558` | `message_start`와 `message_stop`을 받았는지 기록한다. |
| `:559` | `yield event`: `stream()`의 반복문에 넘긴다. |
| `:560-565` | JSON 해석에 실패하면 원문(`raw`)을 포함한 예외를 던진다. |
| `:568-570` | `message_start`는 받았는데 `message_stop`이 없이 끝나면 "Anthropic stream ended before message_stop"으로 실패한다. 응답이 중간에 끊긴 경우를 잡는다. |

**SSE를 만드는 반복문과 pi가 직접 만든 SSE 타입** (`코드 확인`)
SSE를 다루는 코드는 Anthropic SDK가 아니라 pi가 이 파일에 직접 쓴 코드이고, 타입도 직접 정의했다(`:381-391`). SDK에서 가져온 타입 중 SSE와 관련 있는 것은 해석된 결과 이벤트의 모양인 `BetaRawMessageStreamEvent`(`RawMessageStreamEvent`) 하나뿐이다. 나머지 `import type`(`MessageCreateParamsStreaming`, `BetaTool`, `BetaStopReason` 등)은 요청 본문이나 종료 사유의 모양이며 SSE와 무관하다. `import type`은 컴파일 때만 쓰이고 실행 중에는 지워진다.

```ts
interface ServerSentEvent {      // 완성된 SSE 이벤트 한 건
    event: string | null;        //   이벤트 이름   예: "content_block_delta"
    data: string;                //   내용(JSON 글자). data 줄이 여러 개면 "\n"으로 합쳐진 것
    raw: string[];               //   원본 줄들 (오류 메시지에 넣으려고 보관)
}
interface SseDecoderState {      // 만드는 중인 이벤트의 메모장
    event: string | null;
    data: string[];
    raw: string[];
}
```
`SseDecoderState`는 줄을 읽으면서 적어 두는 **메모장**이고, `ServerSentEvent`는 빈 줄이 오는 순간 메모장을 정리해서 내보내는 **완성된 쪽지**다. 줄 하나씩 `decodeSseLine(line, state)`(`:418-442`)에 넣었을 때의 변화는 이렇다.

| 읽은 줄 | 코드가 하는 일 | 메모장 `state` | 돌려주는 값 |
|---|---|---|---|
| `event: content_block_delta` | `state.event = value` (`:435-436`) | `event="content_block_delta"`, `data=[]` | `null` (미완성) |
| `data: {...}` | `state.data.push(value)` (`:437-438`) | `data=['{...}']` | `null` |
| (빈 줄) | `flushSseEvent(state)` (`:419-421`, `:402-416`) | **비워짐** | **`ServerSentEvent`** |

`:`로 시작하는 줄은 주석이라 무시한다(`:424-426`). 빈 줄이 SSE에서 "이벤트 한 건의 끝"이므로 그 순간에만 쪽지가 나온다.

반복문이 세 군데 있으므로 구분해야 한다.
| 위치 | 반복문 | 받는 것 | 하는 일 |
|---|---|---|---|
| `iterateSseMessages` 안 (`:483-503`) | `while (true)` + 안쪽 `while (consumed)` (`:495`) | 서버 연결에서 읽은 글자 덩어리 | 줄을 잘라 `decodeSseLine`에 넣고 쪽지가 나오면 `yield`. **SSE 이벤트가 만들어지는 곳** |
| `iterateAnthropicEvents` 안 (`:543`) | `for await (const sse of iterateSseMessages(...))` | `ServerSentEvent` | `data`를 JSON으로 해석해 `yield` |
| `stream()` 안 (`:665`) | `for await (const event of iterateAnthropicEvents(...))` | `RawMessageStreamEvent` | pi 이벤트로 바꿔 `push` |

```
서버 연결 (바이트)
   ▼ iterateSseMessages의 while (:483-503):  글자 덩어리 → buffer → 한 줄(string) → decodeSseLine(line, SseDecoderState) → ServerSentEvent | null
   ▼ yield ServerSentEvent
   ▼ iterateAnthropicEvents의 for await (:543):  ServerSentEvent.data(string) → parseJsonWithRepair → RawMessageStreamEvent
   ▼ yield RawMessageStreamEvent
   ▼ stream()의 for await (:665):  RawMessageStreamEvent → pi 이벤트 → stream.push
```
`SseDecoderState`, `ServerSentEvent`는 pi가 정의한 타입이고, `RawMessageStreamEvent`만 SDK에서 가져온 타입이다. SDK는 요청을 보내는 데만 쓰인다(`:652`).

**실험: 복사한 코드로 확인** (`실행 확인`, `artifacts/pi/ai-demos/sse-parse-demo.ts`, 로그 `sse-parse-demo.2026-10-05.log`)
`:381-571`을 그대로 복사하고(`parseJsonWithRepair`만 `partial-json`이 설치되어 있지 않아 `JSON.parse`로 대체), 원본 730글자를 **줄 중간에서도 잘리는 37글자 덩어리 20개**로 나눠 보냈다.
```
조각1: "event: message_start\ndata: {\"type\":\"m"          ← 한 이벤트가 두 덩어리에 걸쳐 있다
조각2: "essage_start\",\"message\":{\"id\":\"msg_1\""
조각3: ",\"usage\":{\"input_tokens\":12}}}\n\nevent"
...
event 1개 받음: type=message_start
event 1개 받음: type=content_block_start
event 1개 받음: type=content_block_delta text="안"
event 1개 받음: type=content_block_delta text="녕"
event 1개 받음: type=content_block_stop
event 1개 받음: type=message_delta
event 1개 받음: type=message_stop
```
- 덩어리가 이벤트 경계와 상관없이 잘려도 `buffer`에 이어 붙여서 **이벤트가 완성되었을 때만** 내보낸다.
- 8건을 보냈는데 7건이 나왔다. 예시 데이터에 넣은 `ping`이 `:548-550`에서 걸러졌다.
- 이 SSE 예시 글자는 형식을 보이려는 것이고, 실제 Claude 응답을 기록한 것이 아니다.

### 5.2 이벤트 변환 표 (`:665-861`)
| Anthropic 이벤트 | 하는 일 | pi 이벤트 |
|---|---|---|
| `message_start` | 응답 ID와 실제 응답 모델을 기록. 입력/캐시 토큰 수를 `usage`에 적고 `calculateCost` 호출 | (없음. `start`는 요청이 성공한 직후 이미 push됨, `:660`) |
| `content_block_start` (text) | `output.content`에 text 블록 추가 | `text_start` |
| 〃 (thinking) | thinking 블록 추가 | `thinking_start` |
| 〃 (redacted_thinking) | `redacted: true`인 thinking 블록 추가 (글은 `"[Reasoning redacted]"`) | `thinking_start` |
| 〃 (tool_use) | toolCall 블록 추가 (인자는 우선 빈 값, JSON 조각을 모을 `partialJson` 버퍼 포함) | `toolcall_start` |
| `content_block_delta` (text_delta) | 블록의 `text`에 덧붙임 | `text_delta` |
| 〃 (thinking_delta) | 블록의 `thinking`에 덧붙임 | `thinking_delta` |
| 〃 (input_json_delta) | `partialJson`에 덧붙이고, 현재까지의 JSON을 `parseStreamingJson`으로 해석해 `arguments`를 갱신 | `toolcall_delta` |
| 〃 (signature_delta) | 추론 블록의 서명에 덧붙임 | (없음) |
| `content_block_stop` | 블록 완성. 임시 필드(`index`, `partialJson`) 제거. 도구 인자는 마지막으로 한 번 더 해석 | `text_end` / `thinking_end` / `toolcall_end` |
| `message_delta` | `stop_reason`을 `StopReason`으로 변환(§5.4). 최종 토큰 수로 `usage` 갱신, `calculateCost` 다시 호출 | (없음) |
| (루프 종료 후) | 검사 후 `done` 또는 오류 | `done` / `error` |

- **`contentIndex`는 `output.content` 배열의 위치**다(`output.content.length - 1`). Anthropic이 주는 `index`는 블록을 찾기 위한 임시 필드로 쓰고(`findIndex`) 끝나면 지운다.
- **도구 호출 인자가 조각으로 오는 이유와 처리**: `input_json_delta`는 `{"pa`, `th":"main.ts"}`처럼 잘린 JSON을 준다. 조각을 모아 둔 문자열을 매번 `parseStreamingJson`으로 해석해서 `arguments`를 채우고, `content_block_stop`에서 최종 해석한다. 01에서 "`toolcall_end`에서 인자가 확정된다"고 한 것이 이 코드다. 해석기의 내부는 읽지 않았다(`미확인`).
- **`signature_delta`는 이벤트를 내보내지 않는다.** 추론의 서명은 사용자에게 보여 줄 내용이 아니라 다음 요청에 되돌려 보내기 위한 것이라, 블록에만 저장한다.
- **사용량(`usage`)**: `message_start`에서 한 번, `message_delta`에서 한 번 채운다. Anthropic은 `total_tokens`를 주지 않아서 `input + output + cacheRead + cacheWrite`로 직접 계산한다. `message_delta`에서는 값이 있는 필드만 덮어써서, 프록시가 `message_delta`에서 `input_tokens`를 빼도 `message_start`의 값이 유지된다(`:828-829`). 추론 토큰은 `output_tokens_details.thinking_tokens`에서 `usage.reasoning`으로 옮긴다(01에서 본 "`reasoning`은 `output`의 부분집합").
- **비용**: `calculateCost`는 두 번 호출한다. 응답 도중 중단돼도 입력 비용은 남도록 첫 호출을 일찍 한다(`:680-681` 주석). 응답 모델이 요청 모델과 다르고 `allowedFallbackModels`에 있으면 대체 모델의 가격으로 계산한다(`:671-679`).

### 5.3 예시: "파일 읽어줘"에 Claude가 `read`를 호출하는 경우
```
서버 이벤트                                         pi 이벤트
message_start (입력 토큰 1,200)                      (start는 이미 나갔음)
content_block_start (text)                          text_start (contentIndex 0)
content_block_delta text_delta "읽어 볼게요"          text_delta
content_block_stop                                  text_end   (content: "읽어 볼게요")
content_block_start (tool_use read)                 toolcall_start (contentIndex 1)
content_block_delta input_json_delta '{"path":"a'    toolcall_delta
content_block_delta input_json_delta '.ts"}'         toolcall_delta
content_block_stop                                  toolcall_end (toolCall: read {path:"a.ts"})
message_delta (stop_reason: tool_use, 출력 토큰 48)   (stopReason = "toolUse", usage 갱신)
message_stop                                        done (reason: "toolUse", message: output)
```
이것은 이벤트 흐름을 설명하려고 만든 예시이고, 실제 응답을 기록한 것이 아니다.

### 5.4 종료 사유 변환: `mapStopReason` (`:1620-1646`)
| Anthropic `stop_reason` | pi `StopReason` | 비고 |
|---|---|---|
| `end_turn` | `stop` | |
| `max_tokens` | `length` | |
| `tool_use` | `toolUse` | 에이전트는 이 값으로 도구를 실행한다. |
| `refusal` | `error` | 거절 이유를 `errorMessage`에 담는다. |
| `pause_turn`, `stop_sequence` | `stop` | 주석: `pause_turn`은 "이어서 다시 보내면 되므로 stop으로 충분" |
| `sensitive` | `error` | 안전 필터에 걸림 |
| 그 외 | 예외 | "Unhandled stop reason"으로 던진다. |

## 6. 실패하면 어떻게 되나
`stream`의 안쪽 비동기 함수 전체가 `try`/`catch`로 감싸져 있다(`:603`, `:889`).

- **정상 종료** (`:863-888`): 루프가 끝나면 (1) 취소되었으면 예외, (2) `stopReason`이 `pending`이면 "stream ended without a stop reason" 예외, (3) `stopReason`이 `error`/`aborted`이면 `errorMessage`로 예외, 아니면 (4) `done` 이벤트를 push하고 `end()`.
- **`catch`** (`:889-899`): 임시 필드를 지우고, `stopReason`을 취소 신호가 있으면 `aborted`, 아니면 `error`로 정하고, `errorMessage`를 담아 **`error` 이벤트를 push한 뒤 `end()`**한다. 예외를 밖으로 던지지 않는다.
- 그래서 01/02에서 정리한 "실패도 `stopReason`이 `error`인 `AssistantMessage`로 알린다"가 이 `catch`의 코드다. `.result()`는 reject하지 않고 이 메시지로 resolve된다.
- **재시도**: 요청을 보내는 부분만 `retryProviderRequest`로 감싼다(`:651-658`). SDK 자체 재시도는 끈다(`maxRetries: 0`, `:649`). 즉 재시도는 응답이 시작되기 전 단계에서만 한다. 재시도 규칙(`maxRetries`, `maxRetryDelayMs`)은 `utils/provider-retry.ts`에 있고 아직 읽지 않았다(`미확인`).

## 7. `compat` 값이 이 파일에서 쓰이는 곳
02의 Claude Opus 5.5 데이터(`data/anthropic.json`, 2026-10-04 생성)의 `compat`가 요청에 어떻게 반영되는지, 코드를 따라 정리한다. 실제로 서버에 보내 본 것은 아니다.

| `compat` 값 (Opus 5.5) | 쓰이는 곳 | 효과 |
|---|---|---|
| `supportsTemperature: false` | `buildParams` `:1196-1203` | `temperature`를 요청에 넣지 않는다. |
| `forceAdaptiveThinking: true` | `streamSimple` `:952`, `buildParams` `:1256` | `reasoning`을 `effort`로 바꾸고 `thinking: adaptive`를 보낸다. 예산 방식을 쓰지 않는다. |
| `supportsMidConvoEffort: true` | `stream` `:583`, `buildParams` `:1160`, `:1244-1250`, `getBetaFeatures` `:1119` | 항상 `thinking: adaptive`, `output_config.effort: "high"`를 보내고, 대화에 effort를 알리는 시스템 메시지를 끼워 넣는다(`insertThinkingLevelMessages`, `:1525-1539`). 응답의 `providerThinkingLevel`에도 기록한다. 이 경로에서는 `reasoning`이 없어도(`thinkingEnabled: false`) `thinking`이 꺼지지 않는다. `thinkingLevelMap.off`가 `null`인 것과 맞는다. |
| `supportsMidConvoSystemMessages: true` | `stream` `:579` | 대화 중간의 시스템 메시지를 합치지 않고 그대로 보낸다. |
| `supportsMidConvoToolChanges: true` | `buildParams` `:1142-1146` | 조건이 맞으면 도구 변경을 서버 기능으로 처리한다(§4.6). |
| `supportsStrictTools: true` | `convertTools` `:1593` | 스키마가 허용하면 `strict: true`로 보낸다. |
| (설정 없음) `supportsLongCacheRetention` 기본 true | `getCacheControl` `:90` | `long` 보존이면 `ttl: "1h"` |

compat가 없는 모델에는 `getAnthropicCompat`(`:217-231`)이 기본값을 채운다. 예: `supportsTemperature` 기본 true, `supportsStrictTools` 기본 false, OpenRouter 주소이면 세션 친화 헤더 기본 켜짐. 이것이 01에서 본 "미지정이면 baseUrl로 자동 감지"의 이 파일 쪽 구현이다.

## 8. 비교: OpenAI Responses (`api/openai-responses.ts`)
`openai` provider(02)가 쓰는 통신 코드와 비교한다. `anthropic-messages.ts`와 같은 뼈대 위에서 달라지는 부분만 적는다.

### 8.1 같은 뼈대 (`openai-responses.ts:127-236`)
```
stream(model, context, options)
  new AssistantMessageEventStream()                              ← inner 스트림
  resolveTranscript(...)                                         ← 중간 시스템 메시지 처리
  (async () => {
     output = 빈 AssistantMessage (stopReason "pending")
     try {
        client 만들기 → params 만들기 → onPayload → retryProviderRequest(요청)
        onResponse → push(start)
        (응답을 읽으며 push)
        취소, pending, error 검사 → push(done) → end()
     } catch { 임시 필드 정리, stopReason, errorMessage, push(error), end() }
  })()
  return stream
```
`anthropic-messages.ts`와 줄 구성까지 같다. **모든 `api/*.ts` 통신 코드가 이 뼈대를 따른다**고 보이지만, 이 두 파일만 읽었다(나머지는 `미확인`).

### 8.2 다른 점
| | Anthropic Messages | OpenAI Responses |
|---|---|---|
| 요청 SDK | `@anthropic-ai/sdk` | `openai` |
| 대화 필드 | `system` + `messages` | `input` 배열 하나 |
| 응답 읽기 | SSE를 직접 파싱 (`iterateSseMessages`) | SDK가 주는 스트림을 `processResponsesStream`(shared)이 읽음 |
| 응답 이벤트 이름 | `content_block_delta` 등 | `response.output_text.delta`, `response.function_call_arguments.delta`, `response.completed` 등 (`openai-responses-shared.ts:601-747`) |
| 추론 옵션 | `thinking`(adaptive 또는 예산) + `output_config.effort` | `reasoning: { effort, summary }`, `include: ["reasoning.encrypted_content"]` (`:363-379`) |
| `reasoning` 변환 | `mapThinkingLevelToEffort` 또는 예산 계산 | `clampThinkingLevel(model, reasoning)`으로 모델이 지원하는 수준에 맞추고 `thinkingLevelMap`으로 값 변환 (`:249-250`, `:365-367`) |
| 캐시 | `cache_control` 표시를 블록에 붙임 | `prompt_cache_key`(세션 ID), `prompt_cache_retention`/`prompt_cache_options` (`:334-336`) |
| 저장 | | `store: false` (`:337`). 서버에 대화를 저장하지 않는다. |
| 최대 출력 | `max_tokens` | `max_output_tokens`, 최소 16 (`:340-342`) |
| 비용 | `calculateCost` | 같은 함수 + 서비스 등급별 배수(`flex` 0.5배, `priority`/`fast` 2배, `gpt-5.5`는 2.5배, `:387-415`) |
| ChatGPT 로그인 | | API 키가 `sk-`로 시작하지 않으면 ChatGPT 로그인으로 보고 일부 필드를 뺀다 (`:40-47`, `:329`) |
| provider별 분기 | `model.provider === "github-copilot"`, `"openrouter"` 등 (`createClient` `:994`, `:1041`) | `OPENAI_TOOL_CALL_PROVIDERS`(`openai`, `openai-codex`, `opencode`)를 `convertResponsesMessages`에 넘김 (`:31`, `:316`, 용도는 `미확인`), Copilot 동적 헤더 (`:268-275`) |

핵심은 **요청 형식과 응답 이벤트 이름만 다르고, 위로 올리는 이벤트(`start`, `text_*`, `toolcall_*`, `done`/`error`)와 오류 처리 방식은 같다**는 점이다. 이것이 ai 패키지가 회사 차이를 숨기는 방식이다.
(OpenAI Responses의 응답 이벤트가 pi 이벤트로 바뀌는 상세는 [03-2](./03-2-api-openai-responses.md) §5에서 `processResponsesStream`을 읽고 정리했다. 이 변환기는 `openai-responses.ts`와 `openai-codex-responses.ts`가 함께 쓴다.)

## 9. 읽지 않은 것 (`미확인`)
- `utils/provider-retry.ts`(재시도 규칙), `utils/json-parse.ts`(`parseStreamingJson`, `parseJsonWithRepair`), `utils/sanitize-unicode.ts`, `utils/estimate.ts`(`clampMaxTokensToContext`가 쓰는 토큰 추정) → 05 utils
- `api/openai-completions.ts`: compat 자동 감지(OpenAI 호환 서버용). 이번에는 `openai-responses`로 비교했다.
- `api/constrained-sampling.ts`(`strict` 스키마 처리), `api/github-copilot-headers.ts`
- `openai-responses-shared.ts`의 `convertResponsesMessages` (`processResponsesStream`은 [03-2](./03-2-api-openai-responses.md) §5에서, 메시지 변환은 §4.5에서 읽음)
- 다른 `api/*.ts`(Google, Bedrock, Mistral 등)
- 인증 상세 → 04

## 10. 이전 질문들과의 연결
| 이전 질문 | 이 문서의 답 |
|---|---|
| inner 스트림은 누가 만드는가? | `api/*.ts`의 `stream` 함수가 만든다 (`anthropic-messages.ts:578`). |
| 변환(raw 응답 → 공용 이벤트)은 누가 하는가? | 같은 `stream` 함수 안의 루프(`:665-861`)가 한다. |
| `stream`과 `streamSimple`의 차이는? | `streamSimple`은 `reasoning`을 회사별 설정으로 바꾸고 `stream`을 부른다(§3). |
| 스트림은 SSE 연결인가? | 스트림 객체는 아니다. SSE 연결을 읽는 코드는 이 파일의 `iterateSseMessages`다(§5.1). |
| 에러는 어떻게 전달되는가? | `catch`에서 `error` 이벤트를 push한다(§6). |
| 비용은 언제 계산되는가? | 응답의 토큰 수를 `usage`에 적은 직후(`:690`, `:859`). |

## 11. 다음 문서
- **04 인증**: `auth/*`, `env-api-keys.ts`, OAuth. 02에서 본 `getAuth`의 결과가 이 파일의 `options.apiKey`, `options.headers`가 되는 경로.
- **05 utils**: `retry`, `json-parse`, `estimate`, `validation` 등. 이 문서에서 이름만 나온 것들.
- **06 호출 경로 종합**
