# agent 04: 프록시 스트림 (`proxy.ts`, `stream-fn.ts`)

- **기준 commit**: `28dcce2ba` (`packages/agent/src`는 `3874b3e98`과 동일) / **분석일**: 2026-10-06
- **선행 문서**: [01-types](./01-types.md)(`StreamFn`), [02-agent-loop](./02-agent-loop.md), [ai/03-0-event-stream](../ai/03-0-event-stream.md)
- **읽은 파일**: `proxy.ts` 406줄, `stream-fn.ts` 20줄, `index.ts` 5줄 전체 (줄 번호는 `proxy.ts` 기준, 다른 파일은 파일명 표시). 사용처 확인으로 `grep`만 했다.
- **검증 수준**: 코드 흐름은 `코드 확인`. 실행 없음. **서버 쪽 구현은 이 repo에 없어 `미확인`**(서버가 실제로 이 형식을 보내는지).

## 1. 이 문서의 질문
(1) `streamProxy`는 무엇이고 누가 쓰나? (2) 서버가 보내는 이벤트는 ai의 이벤트와 무엇이 다르고, 클라이언트는 어떻게 다시 조립하나? (3) 실패와 중단은 어떻게 표현하나? (4) `stream-fn.ts`는 02의 `미확인`(기본 `streamFn`)과 어떻게 이어지나?

## 2. 한 줄 답
**`streamProxy`는 "LLM을 직접 부르지 않고 서버(`proxyUrl/api/stream`)에 요청하는 `StreamFn`"이다.** 서버는 이벤트에서 무거운 `partial` 필드를 빼고 보내고, 클라이언트가 **하나의 `partial` 객체를 이벤트마다 갱신하며 원래 `AssistantMessageEvent`로 복원**한다. 쓰는 곳은 이 repo에서 **테스트, README, 브라우저 스모크뿐**이고 `coding-agent`는 쓰지 않는다 (§8).

## 3. 왜 `partial`을 빼나 (문제 → 예 → 해결)
- 문제: ai의 이벤트는 `text_delta`마다 **그때까지의 전체 메시지(`partial`)**를 실어 보낸다(ai/01). 네트워크로 보내면 같은 내용이 계속 반복된다.
- 예: 100번의 `text_delta`가 오면 `partial.content[0].text`가 점점 길어지는 메시지 전체를 100번 전송.
- 해결: 서버는 **변화분만**(`delta`, `contentIndex`)을 보낸다(`:36-59`, 주석 `:34`). 클라이언트가 같은 변화를 `partial`에 적용해 **원래 이벤트와 같은 모양**을 만든다. 그러면 뒤의 루프(02)는 직접 호출한 스트림과 구분 없이 쓴다.

## 4. 타입 (`:36-83`)
| 타입 | 내용 |
|---|---|
| `ProxyAssistantMessageEvent` | 서버가 보내는 이벤트. ai의 `AssistantMessageEvent`와 같은 종류(`start`, `text_*`, `thinking_*`, `toolcall_*`, `done`, `error`)지만 **`partial`이 없다** |
| `ProxySerializableStreamOptions` | 서버에 보내도 되는 옵션만 `Pick`: `temperature`, `samplingParams`, `maxTokens`, `reasoning`, `cacheRetention`, `sessionId`, `headers`, `metadata`, `transport`, `thinkingBudgets`, `maxRetryDelayMs` (`:61-74`) |
| `ProxyStreamOptions` | 위 + `signal`, `authToken`, `proxyUrl` (`:76-83`) |

- 이벤트 차이 상세: `toolcall_start`에 `id`, `toolName`이 있고(`:44`), `toolcall_end`는 **완성된 `toolCall` 전체**를 싣는다(`:46`). `done`/`error`에는 `usage`와 선택적 `providerThinkingLevel`이 있다. `done.reason`은 `stop | length | toolUse`, `error.reason`은 `aborted | error`로 **타입이 좁혀져 있다**(`:49`, `:55`).
- 옵션을 **`Pick`으로 명시**하는 것이 중요하다: 02 §6에서 `streamFn`에는 `AgentLoopConfig` 전체(훅 함수들 포함)가 펼쳐져 오는데, `buildProxyRequestOptions`(`:104-118`)는 **직렬화 가능한 11개 필드만 골라** 보낸다. 함수가 JSON에 섞이지 않는다 (`코드 확인`). 따라서 02 §6의 "`streamFn`이 여분 필드를 무시하는가"에 대한 `proxy` 쪽의 답은 "**골라서 쓴다**".
- `onPayload`/`onResponse`/`onProviderStreamEvent`는 보내지 않는다 → 프록시 경유 시 **이 훅들은 의미 없음**(`추론`: 호출하는 코드가 없음, `코드 확인`).

## 5. 요청 (`:120-172`)
```
POST {proxyUrl}/api/stream
Authorization: Bearer {authToken}
Content-Type: application/json
body: { model, context, options(11개 필드) }
```
- `model`은 **`Model` 객체 전체**를 JSON으로 보낸다(`:167`). `baseUrl`, 가격 같은 모델 정보가 서버로 간다. 서버가 모델 id만 보고 자기 설정을 쓰는지 이 값을 쓰는지는 `미확인`.
- `context`는 `TranscriptContext`(`:122`). 02 §6 3단계에서 `normalizeContext({ messages })`로 만들어 온 것이다. **`tools` 필드는 따로 없고** 도구는 대화 기록의 system 메시지(`toolsAdded`)로 간다(02 §8). 이것이 서버에 도구 정의가 가는 방식이다 (`추론`: `TranscriptContext`의 정의는 ai 쪽, `미확인`).
- 인증은 **서버용 토큰 하나**다. LLM provider 키는 서버가 관리한다(`:2-3` 주석). 01의 `getApiKey`와는 **다른 층**: 이 경로에서는 루프가 해석한 `apiKey`를 쓰지 않는다 (옵션 `Pick`에 `apiKey`가 없음, `코드 확인`).
- `!response.ok`: 본문의 `{ error }`를 읽어 `"Proxy error: ..."`로 던진다. 본문 파싱이 실패하면 상태줄만 쓴다(`:174-185`).

## 6. 이벤트 조립 (`:187-219`, `processProxyEvent` `:270-406`)
### 6.1 SSE 파싱
- `response.body.getReader()`로 청크를 읽어 `TextDecoder`(`stream: true`)로 디코드, `"\n"`으로 쪼개 **마지막 미완성 줄은 `buffer`에 남긴다**(`:212-214`).
- `data: `로 시작하는 줄만 처리하고, 빈 `data`는 무시한다(`:193-195`). 다른 SSE 필드(`event:`, `id:`, `:` 주석)는 **버린다**.
- 스트림이 끝난 뒤 개행 없이 끝난 마지막 줄도 처리한다(`:225-230`, 주석: 최종 이벤트가 개행으로 끝나지 않을 수 있음). `decoder.decode()`로 남은 바이트도 비운다.

### 6.2 변화분 적용 (모두 같은 `partial` 하나를 갱신)
| 서버 이벤트 | `partial`에 하는 일 | 줄 |
|---|---|---|
| `start` | 그대로 `start` 방출 | `:275` |
| `text_start` | `content[i] = { type:"text", text:"" }` | `:278-280` |
| `text_delta` | `content[i].text += delta` (없거나 타입 다르면 **throw**) | `:282-294` |
| `text_end` | `textSignature = contentSignature`, 이벤트에 `content: text` 채움 | `:296-308` |
| `thinking_*` | 같은 구조 (`thinking`, `thinkingSignature`) | `:310-340` |
| `toolcall_start` | `content[i] = { type:"toolCall", id, name, arguments:{}, partialJson:"" }` | `:342-350` |
| `toolcall_delta` | `partialJson += delta` → **`parseStreamingJson`으로 `arguments` 재계산** → 객체를 `{...content}`로 교체 | `:352-366` |
| `toolcall_end` | `Object.assign(content, toolCall)`, `partialJson` 삭제 | `:368-381` |
| `done` | `stopReason`, `usage`, `providerThinkingLevel` 반영 후 `message: partial` | `:383-389` |
| `error` | `stopReason`, `errorMessage`, `usage` 반영 후 `error: partial` | `:391-398` |

- **서버가 안 보내는 값을 클라이언트가 만든다**: `text_end`의 `content`(= 누적된 `text`), `thinking_end`의 `content`, `toolcall_*`의 `arguments`(부분 JSON 파싱). 이 값들이 ai 쪽 원래 이벤트에 있었기 때문에 **복원해서 모양을 맞춘다**.
- **`toolcall_delta`의 `arguments`는 클라이언트가 `parseStreamingJson`(ai 유틸)으로 재계산**한다. 서버가 `arguments`를 보내지 않으므로, 부분 인자는 클라이언트 쪽 파서에 달려 있다. 실패하면 `|| {}`(`:356`). `parseStreamingJson` 자체의 부분 해석은 ai/05 참조(`partial-json` 미설치로 실행 확인은 미실시).
- `toolcall_delta`에서 `content`를 **새 객체로 교체**하는 이유는 주석 "Trigger reactivity"(`:357`)뿐. UI 프레임워크가 객체 참조 변화로 변경을 감지하는 용도로 `추론`.
- `partialJson`은 `ToolCall`의 정식 필드가 아니라 **`satisfies ToolCall & { partialJson }`로 끼워 넣은 임시 필드**다(`:349`). `toolcall_end`에서 지운다. **`toolcall_end` 없이 스트림이 끊기면 `partialJson`이 남은 채** `error` 이벤트의 `partial`로 나간다 (`코드 확인`; 이 `partial`이 최종 메시지가 되므로 기록에 `partialJson` 필드가 섞일 수 있음 `추론`).
- **방출하는 `partial`은 항상 같은 객체**다(복사 없음, `:276`, `:280` 등 전부). 그래서 02 §6에서 본 루프의 `{ ...partialMessage }` 얕은 복사가 여기서 의미가 생긴다. 얕은 복사라 `content` 배열은 공유되며, `toolcall_delta`가 요소를 교체(`:357`)하므로 **배열 안의 객체 참조는 바뀐다**.
- 타입 불일치는 `throw`(`text_delta`, `text_end`, `thinking_*`, `toolcall_delta`)인데 **`toolcall_end`만 조용히 `undefined`**(`:380`)를 돌려 이벤트를 버린다. 비일관(`코드 확인`).
- `default`: 알 수 없는 이벤트는 `console.warn` 후 `undefined`(버림). `never` 검사로 컴파일 시점에는 모든 타입이 다뤄졌음을 보장(`:400-404`).

## 7. 종료, 실패, 중단 (`:127-262`) — 모두 `error` 이벤트 + `end()`로
| 상황 | 결과 | 줄 |
|---|---|---|
| 정상 (`done`/`error` 이벤트 수신) | `sawTerminalEvent = true`, 끝에 `stream.end()` | `:199`, `:245` |
| **터미널 이벤트 없이 EOF** | `stopReason: "error"`, `errorMessage: "Connection closed by proxy server before the response completed"`로 `error` 푸시 | `:232-243` |
| HTTP 실패, 네트워크 실패, JSON 파싱 실패, 타입 불일치 throw | `catch`: `reason = signal.aborted ? "aborted" : "error"`, 메시지 기록, `error` 푸시 후 `end()` | `:246-256` |
| 중단 | `abort` 리스너가 `reader.cancel`. 루프 안/후에서 `signal.aborted`면 `"Request aborted by user"`로 throw → `catch`에서 `reason: "aborted"` | `:149-157`, `:208`, `:221` |
| 정리 | `finally`에서 abort 리스너 제거 | `:257-261` |
- **throw하지 않는다**: `streamProxy` 안의 모든 실패가 **스트림 이벤트**로 바뀐다. 01의 "`StreamFn`은 throw 금지, 실패는 스트림 `error` 이벤트로" 계약을 지킨다(`코드 확인`). 02 §5.1 #1에 따라 이 `error`/`aborted`는 루프가 **hard exit**로 처리한다.
- 터미널 이벤트가 **여러 번** 와도 막지 않는다(`sawTerminalEvent`는 플래그뿐). 이후 `stream.push`는 `EventStream`이 처리(ai/03-0, `미확인`).
- `catch`에서 `partial`을 그대로 `error`에 싣는다. **중단 직전까지 쌓인 내용이 `error` 메시지에 남는다**(`코드 확인`).
- 비동기 즉시실행 함수(`:127`)는 **`await`/`catch` 없이** 실행되고 `stream`을 먼저 반환한다(`:264`). 안쪽에서 `catch`가 모든 것을 잡지만 `catch` 안의 `stream.push` 자체가 던지면 처리되지 않은 rejection이 된다(`추론`, 가능성은 낮음).
- 에러 메시지에 `partial.errorMessage`를 쓰므로 02의 §7.5와 달리, 여기서는 **중단 시 도구 호출 부분 인자가 `partial`에 있다**. 루프는 `stopReason === "aborted"`이면 도구를 실행하지 않는다(02 §5 #7).

## 8. 쓰는 곳 (`grep`)
| 위치 | 용도 |
|---|---|
| `packages/agent/README.md`, `CHANGELOG.md` | 문서 |
| `packages/agent/test/proxy.test.ts` (3.9K) | 테스트 |
| `scripts/browser-smoke-entry.ts` | 브라우저 번들 스모크 (이 파일이 `streamProxy`를 import하는지만 확인, 용도 `미확인`) |
| `packages/coding-agent` | **사용 안 함** (`streamProxy` 검색 결과 없음) |
- 즉 **외부 앱(웹앱 등)이 `Agent`를 서버 경유로 쓰게 해 주는 공개 API**이고, pi의 CLI는 쓰지 않는다. 00 §2에서 "사용처는 coding-agent 하나"라고 한 것은 **`Agent` 클래스**에 대한 것이고 `streamProxy`는 별개다 (`코드 확인`, 00 문구 보정 필요).
- 서버 쪽(`/api/stream`)은 이 repo에서 못 찾았다(검색 범위는 위 `grep`뿐, 전체 repo 구조 확인은 `미확인`). 예제: README (`미확인`).

## 9. `stream-fn.ts` — 02의 `미확인` 해소
```ts
let defaultStreamFn: StreamFn | undefined;
setDefaultStreamFn(fn | undefined)        // export (index.ts:4)
getDefaultStreamFn(): StreamFn            // 없으면 throw "No default stream function configured..."
```
- 주석(`stream-fn.ts:5-9`): 호스트가 **기본 모델 런타임을 설치**할 수 있게 하고, `pi-agent-core`가 provider 목록이나 호환 계층에 **의존하지 않게** 한다. 00의 "의존은 `pi-ai`, `typebox`뿐"과 이어지는 설계다.
- 모듈 변수 하나(**프로세스 전역 상태**). 호출 지점: `Agent` 생성자(`agent.ts:236`), `runAgentLoop`/`runAgentLoopContinue`(`agent-loop.ts:124`, `:149`).
- 사용처: `coding-agent/src/core/sdk.ts`가 `setDefaultStreamFn`을 import한다(`sdk.ts:2`). 호출 위치와 설치하는 함수는 coding-agent 단계에서 확인(`미확인`). 테스트도 이 함수로 기본값을 설치/제거한다(`agent.test.ts:109,124`, `agent-loop.test.ts:96,122`).
- **발견**: `getDefaultStreamFn()`이 던질 때:
  - `Agent` 생성자: **생성 시점에 throw**(`streamFn`도 기본값도 없을 때).
  - `runAgentLoop`: `async`이므로 **reject**. `Agent` 경유면 03 §7의 `handleRunFailure`가 받는다.
  - **`agentLoop`(`agent-loop.ts:38`)**: `void runAgentLoop(...).then(stream.end)`에 **`catch`가 없다** → reject되면 처리되지 않은 rejection이고 **반환한 `EventStream`은 끝나지 않는다**(`agent_end`가 안 와서). 다른 이유로 `runLoop`가 throw해도(02 §7.3의 throw 금지 훅 위반 등) 같다 (`코드 확인`, 실행 없음 → 05에서 확인 대상).

## 10. 발견 (정리)
1. **프록시 = 변화분 전송 + 클라이언트 복원.** 서버는 `partial`/`arguments`/`content`를 안 보낸다.
2. **`partial`은 단일 객체를 갱신**하고 같은 참조를 계속 방출한다. 안전은 루프의 얕은 복사에 의존.
3. **`streamProxy`는 `StreamFn`의 throw 금지 계약을 준수**: 실패는 모두 `error` 이벤트로.
4. **`streamProxy`는 coding-agent가 쓰지 않는 공개 API.**
5. **옵션은 `Pick`으로 직렬화 가능한 것만 보낸다.** 훅과 `apiKey`는 서버로 안 감.
6. **`agentLoop`(스트림 반환 판)은 루프 reject를 처리하지 않는다** (§9). `Agent`는 안전.
7. 사소한 문서 위생: `proxy.ts:85-103`의 `streamProxy` 설명 주석(`@example` 포함)이 **`buildProxyRequestOptions` 위에** 붙어 있다. 예제도 `await`를 일반 화살표 함수 안에서 쓴다(`:98`) — 그대로 쓰면 구문 오류 (`코드 확인`, 수정하지 않음).

## 11. 미확인
- 서버 구현(`/api/stream`)과 실제 이벤트 형식 일치 여부
- `TranscriptContext` 정의와 도구 전달 방식(ai 쪽)
- 터미널 이벤트 이후 `push`의 동작(`EventStream`)
- `scripts/browser-smoke-entry.ts`의 용도
- `parseStreamingJson`의 부분 해석 (05에서 의존성 설치 허락 후)

## 12. 다음
[05-call-flow](./05-call-flow.md): `agent.prompt("...")` 한 번의 종합 경로 + 가짜 `streamFn` 실행 실험.
