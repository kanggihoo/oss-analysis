# agent 01: 타입 정리 (`packages/agent/src/types.ts`)

- **기준 commit**: `3874b3e98` / **분석일**: 2026-10-06
- **선행 문서**: [00-role](./00-role.md), [ai/01-types](../ai/01-types.md)
- **읽은 파일**: `types.ts` 529줄 전체 (이 문서의 줄 번호는 모두 이 파일)
- **검증 수준**: 선언과 주석은 `코드 확인`. **각 훅이 루프의 어느 지점에서 실제로 호출되는지는 `agent-loop.ts`를 읽기 전이라 `미확인`** (다음 문서 02). 실행한 것은 없다.

## 0. 먼저 큰 그림: 타입 4묶음
| 묶음 | 타입 | 한 줄 |
|---|---|---|
| A. 메시지 | `AgentMessage`, `CustomAgentMessages` | 대화 기록의 한 칸. ai의 `Message`에 앱 고유 메시지를 더한 것 |
| B. 도구 | `AgentTool`, `AgentToolResult`, `AgentToolUpdateCallback`, `AgentToolCall`, `AgentToolCallOutcome` | 도구 정의와 실행 결과 |
| C. 루프 설정 | `AgentLoopConfig`와 그 훅들의 입출력 타입 | 반복을 어떻게 돌릴지, 어디서 끼어들지 |
| D. 상태와 알림 | `AgentState`, `AgentContext`, `AgentEvent`, `ThinkingLevel` | 지금 상태, 화면에 알리는 이벤트 |
| (연결) | `StreamFn` | ai를 부르는 함수의 모양 |

## 1. 장난감 모델: 이 타입들이 쓰이는 순서
```
기록 messages = [사용자: "a.txt 읽어줘"]
① convertToLlm(messages)         → AI가 이해하는 Message[] 로 변환   (AgentLoopConfig)
② streamFn(model, context)       → AI 응답: "read 도구를 path=a.txt 로 부르겠다" (toolCall)
③ AgentTool.execute(id, {path})  → AgentToolResult { content: [파일 내용] }
④ 결과를 toolResult 메시지로 기록에 붙임
⑤ ①로 돌아가 다시 부름 → AI가 "파일 내용은 …" 이라고 답하면 끝
```
①~⑤ 한 바퀴(AI 응답 한 번 + 그 도구 실행)가 **턴(turn)**이다(`:518` 주석). 아래는 이 흐름에 나오는 타입을 하나씩 본다. 위 순서는 타입 주석에서 읽은 흐름이고, 실제 호출 지점은 02에서 확인한다(`미확인`).

## 2. A. 메시지
### 2.1 `AgentMessage` (`:374`)
```ts
type AgentMessage = Message | CustomAgentMessages[keyof CustomAgentMessages];
```
- `Message`는 ai 패키지의 `system / user / assistant / toolResult` 메시지다(ai/01).
- `CustomAgentMessages`(`:365`)는 **기본은 빈 인터페이스**다. 앱이 `declare module`로 필드를 추가하면(주석 예: `artifact`, `notification`) 그 값이 `AgentMessage`에 합쳐진다. 이것을 declaration merging(같은 이름 인터페이스를 여러 곳에서 선언하면 합쳐지는 TypeScript 기능)이라 한다.
- 빈 인터페이스의 `keyof`는 `never`이므로 아무도 확장하지 않으면 `AgentMessage`는 그냥 `Message`다. (TypeScript 규칙에서 `추론`, 실행 안 함.)
- **왜 필요한가**: 화면용 알림 같은 것을 대화 기록에 같이 보관하고 싶은데, AI에게는 보내면 안 된다. 그래서 **AI에게 보내기 직전에** `convertToLlm`이 걸러낸다(§4.1).
- 주의: 주석 예제의 모듈 이름이 `"@mariozechner/agent"`(`:357`)로 이전 패키지 이름이다. 실제 패키지는 `@earendil-works/pi-agent-core`이므로 **주석이 낡았다** (`코드 확인`).

## 3. B. 도구
### 3.1 `AgentTool` (`:464-497`)
ai의 `Tool<TParameters>`(이름, 설명, 매개변수 스키마 = AI에게 보여 주는 설명서)에 **실행 코드와 부가 정보**를 더한 것.
| 필드 | 뜻 |
|---|---|
| `label` | 화면에 보일 사람용 이름 (`:466`) |
| `execute(toolCallId, params, signal?, onUpdate?)` | 실제 실행. `params`는 스키마 타입(`Static<TParameters>`)으로 검증이 끝난 값 |
| `prepareArguments?` | 스키마 검증 **전에** 인자를 보정하는 호환용 함수. 스키마에 맞는 객체를 돌려줘야 한다 (`:471`) |
| `outputSchema?` | 성공 결과의 `structuredContent` 모양(JSON Schema) (`:476`) |
| `executionMode?` | 이 도구만 `"sequential"`/`"parallel"` 지정 (`:496`) |
| `replay?: "never" \| "safe"` | 의도는 기록됐는데 결과를 모르는 작업을 복구할 때의 정책 (`:488`). 사용처는 `pi-durable`일 것으로 `추론`, 미확인 |

`execute` 주석(`:478-479`): **실패는 throw하거나 `isError: true`로 돌려준다.** 실패를 `content`에 글로만 적지 말라는 뜻이다.

### 3.2 `AgentToolResult<T>` (`:424-446`) — 도구가 돌려주는 것
| 필드 | 누가 보나 |
|---|---|
| `content` (텍스트/이미지 배열) | **AI가 본다** |
| `details: T` | 로그, 화면용. AI에게 안 감 |
| `structuredContent?` | 프로그램용 결과(`outputSchema`와 맞음). 주석: "Not sent to the model" |
| `usage?` | 도구 실행 자체의 사용량. 주 LLM 컨텍스트 계산에는 안 씀 |
| `isError?` | throw 없이 실패 보고. AI는 에러 결과로 본다 |
| `terminate?` | "이 묶음 뒤에 멈춰도 좋다"는 힌트. **묶음의 모든 결과가 true일 때만** 멈춘다 |

### 3.3 나머지
| 타입 | 뜻 |
|---|---|
| `AgentToolCall` (`:58`) | `AssistantMessage.content` 중 `type: "toolCall"` 블록. AI가 한 도구 호출 요청 |
| `AgentToolUpdateCallback` (`:461`) | 도구가 실행 중 중간 결과를 알리는 함수. 주석: `execute`가 끝난 뒤의 호출은 **무시된다** |
| `AgentToolCallOutcome` (`:449`) | 훅까지 다 거친 도구 호출 최종 결과 `{ toolCall, result, isError }`. `coding-agent`가 4회 import (00-role §3.2) |
| `ToolExecutionMode` (`:47`) | `"sequential"`(하나씩) / `"parallel"`(준비는 차례로, 실행은 동시에) |

`parallel`의 순서 규칙(`:43-45`): `tool_execution_end` 이벤트는 **끝난 순서**로, tool-result 메시지는 **AI가 요청한 순서**로 나온다. 화면에는 먼저 끝난 것이 먼저 보이지만 기록은 요청 순서로 쌓인다는 뜻이다.

## 4. C. 루프 설정 `AgentLoopConfig` (`:193-342`)
`SimpleStreamOptions`(ai의 호출 옵션: 키, 온도 등)를 **상속**하고 `model`(필수)에 아래 훅을 더한다. 즉 ai에 줄 옵션과 루프용 훅이 한 객체에 섞여 있다(ai/01 §2.4의 옵션 계층 위에 한 층이 더 있음).

### 4.1 호출 직전에 메시지를 다듬는 두 훅
| 훅 | 입력 → 출력 | 용도 |
|---|---|---|
| `transformContext?` (`:244`) | `AgentMessage[]` → `AgentMessage[]` | 오래된 메시지 정리, 외부 정보 주입. **AgentMessage 수준**에서 작업 |
| `convertToLlm` (**필수**, `:222`) | `AgentMessage[]` → `Message[]` | 앱 고유 메시지를 AI용으로 변환하거나 버림 |
순서는 주석상 `transformContext` → `convertToLlm`(`:225`). 둘 다 **throw하지 않는다는 계약**이다. throw하면 "정상 이벤트 순서 없이 루프가 중단된다"(`:204`).

### 4.2 턴과 요청 흐름을 바꾸는 훅 3개
| 훅 | 호출 시점 (주석) | 할 수 있는 일 |
|---|---|---|
| `prepareRequest` (`:271`) | **매 요청 직전, 첫 요청 포함**. 대기 메시지는 이미 기록에 붙은 뒤 | `context`, `model`, `thinkingLevel` 교체 (이후 요청에도 유지) |
| `finishTurn` (`:264`) | 응답과 도구 결과가 모두 기록된 뒤, `turn_end` 직전 | `{action:"end"}` 종료 / `{action:"continue"}` 한 번 더 요청. `undefined`면 기본 동작 |
| `prepareNextTurn` (`:278`) | `turn_end` 뒤, 다음 턴을 **계속할 때** 직전 | 컨텍스트/모델/추론수준 교체 또는 메시지 추가 |

- `finishTurn`에서 에러, 중단된 응답은 **무조건 종료**("hard exits", `:261`).
- 입력은 `AgentTurnContext`(`:135`): `message`(그 턴의 AI 응답), `toolResults`, `context`, `newMessages`. 반환 `AgentTurnDecision`은 `continue`/`end` 둘뿐(`:147`).
- `prepareNextTurn`이 돌려주는 `AgentLoopTurnUpdate`(`:161`)는 `context? messages? model? thinkingLevel?`. `prepareRequest`의 `AgentRequestUpdate`(`:180`)는 거기서 `messages`를 뺀 것이다.
- 이름이 비슷해 헷갈린다. `prepareRequest`는 **요청마다**, `prepareNextTurn`은 **턴 사이에만** 불린다(주석 기준, 실제 호출은 02에서 `미확인`).

### 4.3 실행 중 끼어들기 두 훅
| 훅 | 언제 | 비유 |
|---|---|---|
| `getSteeringMessages` (`:293`) | 현재 턴의 도구 실행이 끝난 뒤. 메시지가 있으면 다음 AI 호출 전에 기록에 붙는다. 이미 요청된 도구는 건너뛰지 않는다 | 일하는 중 "방향 바꿔줘" |
| `getFollowUpMessages` (`:306`) | 도구 호출도, steering도 없어서 **멈추려 할 때**. 있으면 한 턴 더 | 끝나면 "이것도 해줘" |
둘 다 "throw 금지, 없으면 `[]`". `QueueMode`(`:55`)는 큐에 여러 개가 쌓였을 때 `"all"`(전부) / `"one-at-a-time"`(가장 오래된 하나씩) 주입 방식이며, 큐 자체는 `Agent` 클래스에 있다(`미확인`, 03에서).

### 4.4 도구 실행 훅과 모드
| 항목 | 뜻 |
|---|---|
| `toolExecution?` (`:317`) | 기본 `"parallel"` |
| `beforeToolCall(ctx, signal?)` (`:326`) | **인자 검증 후, 실행 전**. `{block:true, reason?}`를 돌려주면 실행 대신 에러 결과가 기록된다 |
| `afterToolCall(ctx, signal?)` (`:341`) | 실행 후, `tool_execution_end` 전. 결과의 일부를 **필드 단위로** 덮어쓴다(`content`, `details`, `isError`, `usage`, `terminate`) |

- 입력 `BeforeToolCallContext`(`:107`): `assistantMessage`, `toolCall`, 검증된 `args`, `context`. `AfterToolCallContext`(`:119`)는 거기에 `result`, `isError`.
- **덮어쓰기 규칙(`:79-90`)**: 안 준 필드는 원본 유지, 깊은 병합 없음(`content` 배열은 통째로 교체). 특이점: `content`를 주고 `structuredContent`를 안 주면 **`structuredContent`는 버려진다**(내용과 안 맞을 수 있어서).
- 두 훅은 abort signal을 받고 **훅이 직접 지켜야 한다**고 주석에 있다.
- 훅 이름이 말해 주듯, 권한 확인, 로그, 결과 가공 같은 **정책은 이 훅으로 넣고 루프는 모른다**(해석, `추론`).

### 4.5 `getApiKey` (`:254`)
`(provider: string) => string | undefined`(Promise 가능). 호출마다 키를 해석한다. 이유(주석): 도구가 오래 돌 때 짧게 사는 OAuth 토큰(GitHub Copilot 예)이 만료될 수 있어서. 실패하면 `undefined`를 돌려주고 throw하지 않는다. ai의 `applyAuth`(ai/04)와는 층이 다르다(이쪽은 루프가 옵션에 키를 넣어 주는 것, 연결 방식은 02에서 `미확인`).

## 5. D. 상태와 알림
### 5.1 `AgentState` (`:382-421`) — `Agent` 클래스가 가진 공개 상태
| 필드 | 설명 |
|---|---|
| `systemPrompt` (읽기 전용) | transcript의 시스템 메시지를 되감아서 얻는다. 바꾸려면 시스템 메시지를 추가 (`:384-388`). `initialState`에서는 맨 앞 시스템 메시지의 씨앗 |
| `model`, `thinkingLevel` | 이후 턴에 쓸 모델과 추론 수준 |
| `tools` (get/set) | 대입 시 최상위 배열을 **복사**. transcript에 선언된 도구와 달라지면 **다음 요청 전에 시스템 메시지로 AI에게 알린다** (`:397-399`) |
| `messages` (get/set) | 대화 기록. 대입 시 복사. 시스템 메시지가 프롬프트와 도구 선언을 가진다 |
| `isStreaming` | 처리 중이면 true. **`agent_end` 구독자가 다 끝날 때까지** true |
| `streamingMessage?` | 지금 스트리밍 중인 부분 응답 |
| `pendingToolCalls` | 실행 중인 도구 호출 id 집합 |
| `errorMessage?` | 가장 최근 실패/중단된 턴의 오류 |
`tools`/`messages`가 getter/setter인 이유(`:379-380`): 구현이 대입된 배열을 **복사해서 저장**하게 하려고.

### 5.2 `AgentContext` (`:500`)
`{ messages, tools? }` — 저수준 루프에 넘기는 **스냅샷**. `AgentState`의 일부만 뽑은 것으로 보인다(`추론`).

### 5.3 `AgentEvent` 10종 (`:514-529`)
| 묶음 | 이벤트 (필드) |
|---|---|
| 실행 | `agent_start`, `agent_end{messages}` |
| 턴 | `turn_start`, `turn_end{message, toolResults}` |
| 메시지 | `message_start{message}`, `message_update{message, assistantMessageEvent}`, `message_end{message}` |
| 도구 | `tool_execution_start{toolCallId, toolName, args}`, `tool_execution_update{…, partialResult}`, `tool_execution_end{…, result, isError}` |
- `message_start/end`는 system, user, assistant, toolResult **모두**에 나오고, `message_update`는 **assistant 스트리밍 중에만** 나온다(`:521-523`). `assistantMessageEvent`는 ai의 `AssistantMessageEvent`(`text_delta` 등)를 그대로 담는다.
- `agent_end`는 마지막 이벤트지만, 구독자를 `await`하면 그 처리가 끝나야 실행이 끝난 것이다(`:510-512`).
- `tool_execution_*`의 `args`, `result`가 `any`라 타입 정보가 약하다 (`:527-529`).

### 5.4 `ThinkingLevel` (`:349`)
`off | minimal | low | medium | high | xhigh | max`. 주석: `xhigh`, `max`는 일부 모델 계열만 지원하며 지원 여부는 ai의 모델 메타데이터로 판단한다. ai 쪽 추론 수준 타입과의 대응은 이 문서에서 `미확인`.

## 6. 연결: `StreamFn` (`:33-37`)
`(model, context: TranscriptContext, options?) => AssistantMessageEventStream | Promise<…>`. **throw, reject 금지**, 실패는 `stopReason: "error" | "aborted"`인 최종 `AssistantMessage`와 이벤트로 표현한다. `Models.streamSimple`이 이 모양을 만족한다 (00-role §3.3).

## 7. 읽으면서 알게 된 것 (정리)
1. **throw 금지 계약이 곳곳에 있다**: `StreamFn`, `convertToLlm`, `transformContext`, `getApiKey`, `getSteeringMessages`, `getFollowUpMessages`. 루프 쪽에 try/catch를 줄이는 대신 **호출자에게 책임을 넘기는 설계**다. 예외는 `execute`(도구)와 `beforeToolCall`/`afterToolCall` 쪽에서 허용되는 것으로 보이나(주석에 금지 문구 없음) 루프의 처리는 `미확인`.
2. **"끝낼지 계속할지"를 정하는 곳이 셋**이다: `finishTurn`(명시적), 도구 `terminate` 힌트(전부 true일 때), 큐(steering/follow-up). 우선순위는 02에서 확인.
3. **`terminate`가 세 곳에 중복**: `BeforeToolCallResult`, `AfterToolCallResult`, `AgentToolResult`. 결국 도구 결과 하나로 합쳐지는 값으로 보인다(`추론`).
4. 낡은 주석: `:357`의 `@mariozechner/agent`.

## 8. 읽지 않은 것 (`미확인`)
- 각 훅이 `agent-loop.ts` 어디서, 어떤 순서로 호출되는지
- `terminate`, `finishTurn`, 큐의 우선순위
- `AgentState`가 `Agent` 클래스에서 어떻게 갱신되는지
- `replay`의 사용처

## 9. 다음
**02-agent-loop**: `agent-loop.ts`를 처음부터 읽고 위 훅들이 호출되는 지점을 줄 번호로 표시. 시작점은 ai/06에서 본 `:385-455`(ai 스트림 소비)와 `:726`(`validateToolArguments`).
