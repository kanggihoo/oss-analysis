# agent 08: `StreamFn` (AI를 부르는 함수의 모양)

- 기준 commit: `3874b3e98` (`repos/pi` 체크아웃). 작성일: 2026-10-15. `packages/agent/src`는 `28dcce2ba`와 같다.
- 선행 문서: [01-types](./01-types.md) §6, [02-agent-loop](./02-agent-loop.md) §6, [04-proxy](./04-proxy.md) §9, [ai/03-0-event-stream](../ai/03-0-event-stream.md), [ai/06-call-flow](../ai/06-call-flow.md)
- 읽은 파일: `agent/src/types.ts:15-37`, `agent/src/agent.ts:230-250`(생성자의 기본값 부분은 03에서), `agent/src/stream-fn.ts`, `coding-agent/src/core/sdk.ts:380-425`, `ai/src/types.ts:276-300`, `:356-382`, `ai/src/models.ts:880-912`. 루프 쪽 호출은 02 §6에서 읽은 `agent-loop.ts:381-469`를 인용했다.
- 검증 수준: 선언, 호출 지점, 대입 지점은 `코드 확인`. 루프의 `error`, `aborted` 처리와 가짜 `streamFn` 동작은 05에서 `실행 확인`한 것을 인용했다. 이 문서에서 새로 실행한 것은 없다.

## 0. 이 문서의 질문
- `StreamFn`은 무엇이고, 입력과 출력은 실제로 어떤 값인가?
- `agent`는 이것을 언제, 어떤 인자로 부르는가?
- 누가 이 모양의 함수를 만들어 넘기는가?
- `ai` 패키지에도 비슷한 모양의 타입이 있는데 어떤 관계인가?
- 실패는 어떻게 표현하고, 계약을 어기면 어떻게 되는가?

## 1. 한 줄 답
`StreamFn`은 "대화 기록을 받아 AI 응답 이벤트 스트림을 즉시 돌려주는 함수"라는 모양이다. `agent`는 Claude인지 OpenAI인지 모른 채 이 모양의 함수만 호출하고, 어떤 함수를 꽂을지는 위층(`coding-agent`)이 정한다.

## 2. 선언 (`agent/src/types.ts:15-37`)
```ts
export type StreamFn = (
	model: Model<Api>,
	context: TranscriptContext,
	options?: SimpleStreamOptions,
) => AssistantMessageEventStream | Promise<AssistantMessageEventStream>;
```
주석(`:19-31`)의 내용은 다음과 같다.
- `Models.streamSimple`이 이 모양을 만족한다.
- 루프는 정규화된 transcript를 넘긴다. 시스템 프롬프트와 도구 선언은 `context.systemPrompt`나 `context.tools`가 아니라 transcript의 system 메시지가 가진다.
- 계약 셋:
  1. 요청, 모델, 실행 실패로 throw하거나 reject된 Promise를 돌려주면 안 된다.
  2. 반드시 `AssistantMessageEventStream`을 돌려줘야 한다.
  3. 실패는 스트림의 프로토콜 이벤트와, `stopReason`이 `"error"` 또는 `"aborted"`이고 `errorMessage`가 있는 최종 `AssistantMessage`로 표현해야 한다.

## 3. 입력과 출력을 실제 값으로 보기
"a.txt 읽어줘"를 Claude에게 보내는 장면이다. 값은 설명용이고, 필드 이름은 선언을 따랐다.

### 3.1 입력
```ts
streamFn(
  model,     // { provider: "anthropic", api: "anthropic-messages", id: "claude-...", ... }  어떤 모델을 어떤 방식으로 부를지
  context,   // { messages: [ system(프롬프트, 도구 목록), user("a.txt 읽어줘") ] }          보낼 대화 기록
  options    // { apiKey, signal, ...AgentLoopConfig의 나머지 }                              호출 옵션
)
```
- `context`는 `{ messages }` 모양의 `TranscriptContext`다. 시스템 프롬프트와 도구 목록은 맨 앞 system 메시지에 들어 있다. 05 §2에서 가짜 `streamFn`으로 받아 확인했다(첫 요청의 role이 `['system','user']`).
- `options`에는 루프가 `{ ...config, apiKey, signal }`로 `AgentLoopConfig` 전체를 펼쳐 넣는다(02 §6 #5, 05 §2에서 훅 함수가 옵션에 실려 오는 것을 확인). `StreamFn`은 자기가 아는 필드만 쓰고, `streamProxy`는 직렬화 가능한 11개만 골라 보낸다(04 §4).

### 3.2 출력
함수는 응답이 끝나기를 기다리지 않고 스트림 객체를 즉시 돌려준다(`Promise`로 감쌀 수도 있다). 이 객체에서 이벤트가 하나씩 나온다.
```
start
text_start, text_delta("파일을"), text_delta(" 읽겠습니다"), text_end
toolcall_start, toolcall_delta, toolcall_delta, toolcall_end     ← "read 도구를 path=a.txt로 불러 줘"
done  (stopReason: "toolUse", 최종 AssistantMessage 포함)
```
- 이벤트는 `start`, `text_*`(3종), `thinking_*`(3종), `toolcall_*`(3종), `done`, `error`의 12종이다(ai/01).
- 호출한 쪽은 `for await`로 이벤트를 받거나 `.result()`로 최종 `AssistantMessage`만 받는다(ai/03-0 §5).

## 4. 시간 순서
```
① agent 루프:   streamFn(model, context, options) 호출                   agent-loop.ts:403-407
② streamFn:     스트림 객체를 즉시 돌려줌 (응답은 아직 안 왔음)
③ 뒤에서:       서버로 요청 전송, 응답이 오는 대로 이벤트를 스트림에 push
④ agent 루프:   for await로 이벤트를 받아, message_start/update/end 이벤트로 바꿔 구독자에게 전달
⑤ done 또는 error가 오면 끝. response.result()로 최종 메시지를 받아 대화 기록의 마지막 칸을 교체
```
호출 직전의 인자 준비 순서는 `transformContext`, `convertToLlm`, `normalizeContext`, `getApiKey`이고, 그 결과가 `streamFn`의 `context`와 `options.apiKey`가 된다(02 §6).

## 5. 누가 이 모양의 함수를 만들어 넘기나
`StreamFn` 모양만 맞으면 어떤 함수든 꽂을 수 있다.

| 함수 | 하는 일 | 어디서 |
|---|---|---|
| `Models.streamSimple`을 감싼 함수 | 모델에 맞는 Claude, OpenAI 요청으로 바꿔 직접 전송 | `coding-agent`가 `new Agent`에 넘김 (`sdk.ts:396-407`) |
| `streamProxy` | 서버로 중계 | 이 repo에서는 테스트와 README, 브라우저 스모크만 쓴다 (04 §8) |
| 기본값(`getDefaultStreamFn()`) | `setDefaultStreamFn`으로 등록해 둔 함수 | `Agent`에 `streamFn`을 안 넘겼을 때 (`stream-fn.ts`) |
| 가짜 함수 | 미리 정한 응답을 이벤트로 돌려줌 | 05의 실험, 테스트 |

### 5.1 `coding-agent`가 만든 함수 (`sdk.ts:396-407`)
```ts
streamFn: async (model, context, options) => {
	const requestOptions = buildRequestOptions(model, options);
	if (options?.sessionId === sessionManager.getSessionId()) {
		cacheWarmer.start({ model, context, options: requestOptions }, cacheContextIsCurrent(model));   // 캐시 예열
	}
	return modelRuntime.streamSimple(model, context, requestOptions);   // ai의 Models.streamSimple
},
```
- `agent`가 준 `options`를 `buildRequestOptions`로 다듬어 `ai`에 넘기고, 세션 요청일 때는 프롬프트 캐시를 미리 데우는 일을 곁들인다. 캐시 예열(`cacheWarmer`)의 동작은 읽지 않았다(`미확인`).
- 이 함수 하나가 `agent`가 `ai`에 닿는 유일한 길이다.

### 5.2 기본값 등록 (`stream-fn.ts`, 04 §9)
- `setDefaultStreamFn(fn)`으로 모듈 변수 하나에 함수를 넣어 둔다. `coding-agent`가 `sdk.ts:39`에서 `streamSimple`을 등록한다(00-role §5).
- `Agent` 생성자와 `runAgentLoop`/`runAgentLoopContinue`는 `streamFn ?? getDefaultStreamFn()`을 쓴다. 등록하지 않았는데 필요해지면 "No default stream function configured. Pass streamFn explicitly or call setDefaultStreamFn()"을 던진다.
- 이 구조 덕분에 `agent`는 provider 목록이나 `ai`의 `Models`에 의존하지 않는다.

## 6. `ai` 패키지의 비슷한 타입과의 관계
`ai` 패키지에도 같은 모양의 선언이 있다.

| | `ai`의 `StreamFunction` (`types.ts:371`) | `ai`의 `ProviderStreams.streamSimple` (`types.ts:288`) | `agent`의 `StreamFn` (`types.ts:33`) |
|---|---|---|---|
| model | `Model<TApi>` | `Model<Api>` | `Model<Api>` |
| context | `TranscriptContext` | `TranscriptContext` | `TranscriptContext` |
| options | `TOptions` (`StreamOptions` 계열, API별로 달라짐) | `SimpleStreamOptions` | `SimpleStreamOptions` |
| 출력 | `AssistantMessageEventStream` | `AssistantMessageEventStream` | `AssistantMessageEventStream` 또는 그 Promise |
| 실패 계약 | 스트림 안의 `error`/`aborted` | 같음 | 같음 |

- 한 모양이 층마다 반복된다. 통신 코드(`api/*.ts`)가 `stream`/`streamSimple`을 내보내고, `Models.streamSimple`(`models.ts:895`)이 이를 감싸 같은 모양으로 다시 내보내고, `agent`의 `StreamFn`은 그 모양을 `agent` 쪽에서 독립적으로 선언한 것이다.
- `agent`가 `ai`의 `StreamFunction`을 가져다 쓰지 않고 따로 선언한 이유는 문서에 없다. `agent`가 API별 옵션 타입이나 `Models`에 묶이지 않게 하려는 것으로 보인다(`추론`).
- 사소한 차이: `ai`의 `StreamFunction` 주석(`types.ts:366-367`)은 직접 `streamSimple()`을 부를 때 요청 인증이 없으면 동기적으로 throw할 수 있다는 예외를 적고 있다. `agent`의 `StreamFn`에는 이 예외가 없다. 이 예외가 `Models.streamSimple` 경로에서 실제로 일어나는지는 확인하지 않았다(`미확인`).

체인으로 보면 다음과 같다.
```
agent 루프 ─ streamFn ─▶ coding-agent의 함수 ─▶ Models.streamSimple ─▶ api/anthropic-messages.ts의 stream ─▶ 서버
 (agent의 StreamFn)                              (ai, 같은 모양)         (ai의 StreamFunction)
```
각 층이 자기 스트림을 하나씩 만들고, 안쪽 스트림을 `for await`로 읽어 바깥 스트림에 `push`한다. 이 연쇄는 [ai/03-0 §8.1](../ai/03-0-event-stream.md)의 A, B, C 그림과 같다. `StreamFn`은 입력과 출력을 정하는 함수 모양이고, `EventStream`은 출력으로 돌려주는 통의 구조다.

## 7. 실패 계약
### 7.1 약속
실패해도 throw하지 않고 스트림 안의 값으로 알린다.
```
나쁜 예:  streamFn(...)  →  예외 "서버 과부하"가 호출한 쪽으로 튀어나옴
약속:     streamFn(...)  →  스트림: start, ..., error  (stopReason: "error", errorMessage: "서버 과부하")
```
예를 들어 OpenAI 서버가 과부하로 거절해도 "에러로 끝난 응답"이 스트림에 담겨 정상적으로 돌아온다.

### 7.2 `agent` 쪽 처리
- 루프는 `try/catch` 없이 `streamFn`을 부르고, 응답의 `stopReason`을 본다. `error`나 `aborted`로 끝나면 `finishTurn`의 결정과 무관하게 그 자리에서 종료한다(02 §5.1 #1, 05 C6에서 `실행 확인`).
- 스트림의 `done`과 `error` 이벤트를 구분하지 않는다. 같은 분기에서 최종 메시지를 받고, 오류 여부는 `stopReason`으로 본다(02 §6).
- 계약을 일부 어겨도 루프가 죽지 않게 했다. `start` 없이 `done/error`만 오거나, `done/error` 없이 스트림이 끝나는 경우를 처리한다(02 §6, `agent-loop.ts:448-468`).
- `streamProxy`도 이 계약을 지킨다. HTTP 실패, 연결 끊김, 중단이 모두 `error` 이벤트로 바뀐다(04 §7, 05 §4에서 `실행 확인`).

### 7.3 계약을 어기고 throw하면
`streamFn`이 throw하거나 reject하면 루프에는 이를 받는 try/catch가 없어 `runLoop`가 reject된다(02 §7.3).
- `Agent`를 거치면 `handleRunFailure`가 가짜 에러 메시지와 이벤트로 마무리하고 잠금을 푼다(03 §7, 05 E에서 `convertToLlm` throw로 확인).
- `agentLoop`(스트림 반환 판)를 직접 쓰면 `catch`가 없어 처리되지 않은 rejection이 되고, 반환한 스트림은 끝나지 않는다(02 §3, 05 H1에서 확인).

## 8. 읽으면서 알게 된 것
1. `StreamFn`은 `agent`가 provider를 모른 채 AI를 부르게 하는 연결점이다. 도구 구현을 `coding-agent`가 `execute`로 넘기는 것(06 §3.2)과 같은 방식으로, 실제 일을 하는 부분을 밖에서 주입받는다.
2. 같은 모양(입력 3개, 출력 이벤트 스트림, 실패는 값으로)이 `agent`, `Models`, 통신 코드 세 층에서 반복된다. 층을 바꿔 끼워도 호출 방식이 같다.
3. `options`에는 훅 함수까지 포함된 `AgentLoopConfig` 전체가 실려 간다. 받는 쪽이 필요한 필드만 골라 쓴다는 것이 이 구조의 전제다.

## 9. 읽지 않은 것 (`미확인`)
- `buildRequestOptions`와 `cacheWarmer`의 내용(`sdk.ts`의 나머지)
- `ai`의 `StreamFunction`이 허용하는 동기 throw가 `Models.streamSimple` 경로에서 일어나는지
- `agent`가 `ai`의 `StreamFunction`을 쓰지 않고 따로 선언한 의도(문서 없음)
