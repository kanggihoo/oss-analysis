# agent 02: 루프 본체 (`packages/agent/src/agent-loop.ts`)

- 기준 commit: `28dcce2ba` (v1.0.4 직후). 분석일: 2026-10-06
  - 01의 기준 `3874b3e98`과 다르지만 `git diff 3874b3e98 HEAD -- packages/agent`는 `CHANGELOG.md`, `package.json`뿐이라 `src` 줄 번호는 01과 같다(`코드 확인`).
- 선행 문서: [00-role](./00-role.md), [01-types](./01-types.md), [ai/06-call-flow](../ai/06-call-flow.md)
- 읽은 파일: `agent-loop.ts` 940줄 전체 (이 문서의 줄 번호는 모두 이 파일), 훅 주석은 `types.ts:255-340`
- 검증 수준: 호출 지점과 순서는 `코드 확인`. 이 문서는 읽기만으로 작성했고, 실행 확인은 [05-call-flow](./05-call-flow.md)에서 같은 주장을 가짜 `streamFn`으로 재현했다(§5.1, §7.2, §7.4, §7.5 모두 일치). 외부 모듈(`normalizeContext`, `validateToolArguments`, `EventStream`)의 내부는 ai 문서를 참조하고, 여기서는 호출만 확인했다.

## 1. 이 문서의 질문
01에서 `미확인`으로 남긴 것은 다음과 같다. (1) 각 훅이 어디서 몇 번째로 불리나, (2) `terminate`/`finishTurn`/큐 중 무엇이 먼저인가, (3) 병렬 실행 시 이벤트 순서, (4) 종료 조건, (5) `convertToLlm`/`transformContext` 순서, (6) `getApiKey`가 어떻게 옵션에 들어가나.

## 2. 한 줄 답
`runLoop`(`:163`)는 "AI에게 묻기, 도구 실행, 다음 턴 정하기"를 이중 `while`로 돌린다. 안쪽 루프는 도구 호출이나 steering 메시지가 있는 동안, 바깥 루프는 follow-up 메시지나 `finishTurn`의 `continue`가 있을 때 한 번 더 돈다. 도구 하나를 실행하는 단계(`prepareToolCall`, `execute`, `afterToolCall`)는 `runToolCall`(`:810`)이 export되어 다른 곳에서도 쓸 수 있다.

## 3. 진입 함수 4개 (`:38-151`)
| 함수 | 하는 일 | 줄 |
|---|---|---|
| `agentLoop` | `runAgentLoop`를 기다리지 않고(`void`) 시작하고, 이벤트를 `EventStream`에 push하고, 끝나면 `stream.end(messages)`. 스트림을 즉시 반환 | `:38-61` |
| `agentLoopContinue` | 새 메시지 없이 현재 context로 이어서 실행. 빈 context이거나 마지막이 `assistant`면 동기 throw | `:71-100` |
| `runAgentLoop` | 이벤트 sink(`emit`)를 직접 받는 본체. 프롬프트를 context에 붙이고 `agent_start`, `turn_start`, 프롬프트별 `message_start/end`, `runLoop` 순으로 진행 | `:102-126` |
| `runAgentLoopContinue` | 위의 continue 판. 같은 검증 후 `agent_start`, `turn_start`, `runLoop` | `:128-151` |

- `createAgentStream`(`:153`)은 `agent_end` 이벤트가 오면 스트림을 끝내고, 그 이벤트의 `messages`를 최종 결과로 삼는다(ai의 `EventStream`, ai/03-0 참조).
- `streamFn ?? getDefaultStreamFn()`(`:124`, `:149`): 타입은 필수인데 런타임에 비어 있으면 기본값(`stream-fn.ts`)을 쓴다. coding-agent가 `setDefaultStreamFn`으로 기본을 바꾼다고 handoff에 있으나 이 문서에서는 `미확인`이다.
- 두 `Continue`가 던지는 에러는 같은 검사인데 방식이 다르다. `agentLoopContinue`는 함수 호출 시점의 동기 throw이고, `runAgentLoopContinue`는 async 함수의 reject다(`코드 확인`).
- 반환값 `newMessages`는 이번 실행에서 새로 생긴 메시지만이다(기존 `context.messages`는 제외). `runAgentLoop`는 `[...context.messages, ...]` 복사본으로 시작하지만(`:112-115`), `runAgentLoopContinue`는 `{ ...context }`(`:144`)라서 `messages` 배열이 호출자와 같은 참조다. 루프가 `currentContext.messages.push`를 하므로 이 함수를 직접 부르면 호출자의 배열이 바뀐다. `Agent`를 거치면 `slice()` 복사본을 넘기므로 영향이 없다(03 §5.1, `코드 확인`).
- `agentLoop`(`:38-61`)에는 `.catch`가 없다. `runAgentLoop`가 reject되면(throw 금지 훅 위반, 기본 `streamFn` 미설정 등) 처리되지 않은 rejection이 되고, `agent_end`가 오지 않으므로 반환한 스트림은 끝나지 않는다. `Agent`는 `runAgentLoop`를 직접 부르고 `handleRunFailure`로 받으므로 안전하다(04 §9, 실행 확인 05 H1).

## 4. 간단한 예시: `runLoop`가 하는 일
```
pending = getSteeringMessages()            ← 시작 시 한 번 (사용자가 기다리는 동안 친 것)
while true:                                 ← 바깥 루프
  hasMoreToolCalls = true
  while hasMoreToolCalls or pending 있음:   ← 안쪽 루프 = 한 번 돌 때마다 1턴
     (2번째 턴부터) prepareNextTurn → steering 재확인 → turn_start
     대기 메시지(prepared + pending)를 context에 넣음
     prepareRequest
     message = streamAssistantResponse()    ← AI 호출
     error/aborted 이면: finishTurn → turn_end → agent_end → 끝
     toolCalls 있으면 실행 (length로 잘렸으면 전부 에러 처리)
     decision = finishTurn() ; turn_end
     decision == end 이면: agent_end → 끝
     pending = getSteeringMessages()
  followUp = getFollowUpMessages()
  있으면 pending 으로 두고 바깥 루프 계속
  없고 explicitContinuation 이면 한 턴 더
  아니면 break
agent_end
```

## 5. 한 턴의 순서와 훅 호출 지점 (`:183-299`)
| # | 단계 | 줄 | 비고 |
|---|---|---|---|
| 1 | `prepareNextTurn(lastCompletedTurn)` | `:186` | 첫 턴은 건너뜀(`lastCompletedTurn` 없음). 반환값으로 context, 메시지, model, thinking 교체. `thinkingLevel: "off"`는 `reasoning: undefined`로 바뀐다(`:196-197`) |
| 2 | steering 재확인 | `:204-206` | 이미 pending이 있으면 부르지 않음. 주석 이유: 한 번에 하나만 주입하는 모드에서 한 턴에 둘이 들어가는 것을 막기 위해 |
| 3 | `turn_start` 이벤트 | `:207` | 첫 턴의 `turn_start`는 `runAgentLoop`가 이미 냄(`:118`) |
| 4 | 대기 메시지 주입 | `:211-217` | `declareToolChanges`(§8)를 거쳐 `message_start/end` 이벤트, `context.messages`와 `newMessages`에 추가 |
| 5 | `prepareRequest` | `:219` | 매 요청 전. context, model, thinking 교체 |
| 6 | AI 응답 | `:242` | `streamAssistantResponse`(§6) |
| 7 | 오류/중단 확인 | `:245-256` | `finishTurn` 호출 후 `turn_end`, `agent_end`로 즉시 종료 |
| 8 | 도구 실행 | `:263-278` | §7 |
| 9 | `finishTurn` | `:286` | `turn_end` 이벤트 직전 |
| 10 | `turn_end` | `:287` | |
| 11 | steering 확인 | `:295` | `finishTurn`이 `end`가 아닐 때만 |

### 5.1 "끝낼지 계속할지"를 정하는 세 곳의 우선순위 (01의 질문)
| 순위 | 규칙 | 코드 |
|---|---|---|
| 1 (최우선) | `stopReason`이 `error`/`aborted`면 `finishTurn`의 결정과 무관하게 종료 | `:245-256`. 이때 `finishTurn`은 호출되지만 반환값은 버린다 |
| 2 | `finishTurn`이 `{ action: "end" }`이면 큐를 확인하지 않고 종료 | `:289-292` |
| 3 | 도구 배치가 전부 `terminate`이면 `hasMoreToolCalls = false` | `:272`, `shouldTerminateToolBatch`(`:689`) |
| 4 | steering 메시지가 있으면 계속 | `:295-296`, `:183` |
| 5 | (안쪽 루프 종료 후) follow-up이 있으면 계속 | `:302-308` |
| 6 | `finishTurn`의 `continue`는 위 3~5가 하나도 없을 때만 한 턴을 강제 | `:294-297`, `:311-314` |
| 7 | 그 외 종료 | `:317` |

- `explicitContinuation`(`:174`)은 `continue` 결정이 "이미 다른 이유로 계속되는 경우"에는 `false`로 지워져(`:296-298`, `:305`) 턴이 하나 더 추가되지 않는다. 주석(`types.ts:258-260`)과 일치한다.
- 강제된 한 턴은 새 메시지 없이 현재 context만으로 요청한다(`:310` 주석). 이때 `pendingMessages`는 `[]`이지만 `hasMoreToolCalls = true`(`:180`)로 시작하므로 안쪽 루프를 한 번 돈다.
- `terminate`는 도구 전부가 `terminate: true`여야 한다(`.every`, `:690`). 하나라도 아니면 계속된다. 도구가 0개이면 `false`다(`length > 0`).
- `terminate`로 `hasMoreToolCalls`가 `false`가 되어도 steering이 있으면 계속된다(`:296`). `terminate`는 "도구 호출 때문에 계속할 필요 없음"이지 "실행 종료"가 아니다.

## 6. AI 호출: `streamAssistantResponse` (`:381-469`)
호출 순서(질문 5, 6의 답)는 다음과 같다.
1. `transformContext(messages, signal)`가 있으면 호출한다(`:390-392`). `AgentMessage[]`를 받아 `AgentMessage[]`를 돌려주며 잘라내기, 압축 같은 일을 한다.
2. `convertToLlm(messages)`는 필수다(`:395`). `AgentMessage[]`를 ai의 `Message[]`로 바꾼다.
3. `normalizeContext({ messages: llmMessages })`(`:397`)는 ai 쪽 함수다. `tools`, `systemPrompt`는 여기에 들어가지 않는다. 요청에 보이는 도구 목록은 시스템 메시지의 `toolsAdded/toolsRemoved`로 대화 기록에 실려 간다(§8). (실행 확인: ai의 `normalizeContext`는 `systemPrompt`/`tools`가 있을 때만 맨 앞 system 메시지를 만들고, 이 경로에서는 `messages`를 그대로 통과시킨다. 첫 system 메시지는 `Agent` 생성자가 만든 것, 05 §2.)
4. `apiKey = (await getApiKey?.(config.model.provider)) || config.apiKey`(`:400-401`). 훅이 비어 있거나 빈 값을 주면 정적 `apiKey`로 대체한다. 훅이 throw하면 처리하는 곳이 없다(try/catch 없음). 계약상 금지라 그렇다.
5. `streamFunction(config.model, llmContext, { ...config, apiKey, signal })`(`:403-407`). 두 번째 인자의 옵션은 `AgentLoopConfig` 전체를 펼친 것에 키와 signal을 더한 것이다. 훅들도 옵션 객체에 같이 실려 가고, `StreamFn`은 자기가 아는 필드만 쓴다(`추론`; ai 쪽이 모르는 필드를 무시한다는 것은 이 문서에서 `미확인`).

스트림 소비 (`:414-458`):
| ai 이벤트 | 하는 일 |
|---|---|
| `start` | `partial`을 `context.messages`에 push하고 `message_start` 발행 (`:416-420`) |
| `text_*`, `thinking_*`, `toolcall_*` | `context.messages`의 마지막 칸을 새 `partial`로 교체하고 `message_update` 발행 (`:432-440`) |
| `done`, `error` | `response.result()`로 최종 메시지를 받아 마지막 칸을 교체하고, `message_end`를 발행한 뒤 반환 (`:443-455`) |

- 이벤트마다 `{ ...partialMessage }`로 얕은 복사본을 내보낸다(`:420`, `:438`). 구독자가 받은 객체와 context 안 객체가 같은 참조가 되지 않게 하려는 것으로 보이나(`추론`), 얕은 복사이므로 `content` 배열은 공유된다(`코드 확인`).
- 스트리밍 중에도 `context.messages`에는 미완성 assistant 메시지가 들어 있다. 중간에 다른 코드가 context를 읽으면 부분 메시지를 본다.
- `result()`는 `Object.assign(…, { thinkingLevel: config.reasoning ?? "off" })`로 요청한 추론 수준을 최종 메시지에 기록한다(`:409`). 어떤 `streamFn`이 답했든 같다. 이 필드가 `AssistantMessage`에 있는 것은 `types.ts`가 아니라 ai 쪽 정의다(`미확인`).
- `start` 없이 `done/error`만 오는 스트림도 처리한다. `addedPartial`이 `false`면 push한 뒤 `message_start`를 뒤늦게 낸다(`:448-453`). `for await`가 `done/error` 없이 끝나는 경우에도 마지막에 같은 처리를 한다(`:460-468`). `streamFn`이 계약을 어겨도 루프가 죽지 않게 한 것이다.
- `error` 이벤트와 `done`을 구분하지 않는다. 같은 분기에서 최종 메시지를 반환하고, 오류 여부는 호출자가 `stopReason`으로 본다(§5 #7).

## 7. 도구 실행 (`:259-278`, `:508-660`)
### 7.1 실행 방식 선택 (`:508-523`)
`config.toolExecution === "sequential"`이거나 이 메시지의 도구 중 하나라도 `executionMode === "sequential"`이면 배치 전체를 순차로 실행한다. 아니면 병렬이고, 기본값은 병렬이다(`:522`). 도구 하나가 "순차"를 요구하면 같은 메시지의 다른 도구도 순차가 된다.

### 7.2 순차(`:530-584`)와 병렬(`:586-660`)의 이벤트 순서
같은 도구 3개(A, B, C)가 있고 A는 느리고 B, C는 빠르다고 하자.
| | 순차 | 병렬 |
|---|---|---|
| `tool_execution_start` | A 시작, A 실행, A 끝, B 시작 … | A, B, C 순서대로 모두 먼저 (준비 단계는 순차) |
| 준비(검증, `beforeToolCall`) | 도구마다, 실행 직전 | A, B, C 순차로 먼저 모두 (`:596-644`) |
| 실행 | 하나씩 | `Promise.all`로 동시 (`:646`) |
| `tool_execution_end` | A, B, C (소스 순서) | 끝나는 순서 (B, C, A) |
| toolResult 메시지(`message_start/end`) | 도구마다 end 직후 | 전부 끝난 뒤 소스 순서로 A, B, C (`:650-654`) |

- 병렬에서도 `beforeToolCall`은 동시 실행이 아니라 순차다(준비 단계가 `for` 안에서 `await`). 느린 `beforeToolCall`(예: 사용자에게 승인 요청)이 뒤 도구의 시작을 막는다(`코드 확인`).
- 병렬이라도 도구 결과 메시지의 순서는 AI가 호출한 순서로 고정되어, 대화 기록의 결정성이 보장된다.
- 병렬에서 준비 단계에 즉시 결정된 것(도구 없음, 검증 실패, 차단)은 `tool_execution_end`가 바로 나가고(`:611`), 실행할 것은 함수로 모아 두었다가 나중에 실행한다(`:619`). 그래서 이 경우 `end`가 다른 도구의 실행보다 앞설 수 있다.

### 7.3 도구 한 개의 단계 (`prepareToolCall` `:707`, `executePreparedToolCall` `:820`, `finalizeExecutedToolCall` `:853`)
```
도구 찾기 (이름 일치)          → 없으면 에러 결과 "Tool X not found"
prepareArguments?(args)        ← 스키마 검증 전 보정
validateToolArguments(tool, call)   ← 스키마 검증 (throw 가능)
beforeToolCall({assistantMessage, toolCall, args(검증됨), context}, signal)
   → block 이면 에러 결과 (reason), terminate 도 같이 줄 수 있음
(abort 확인)
tool.execute(id, args, signal, onUpdate)   ← 실패는 catch 하여 에러 결과로
afterToolCall({..., result, isError}, signal)  → 결과 덮어쓰기, throw 하면 에러 결과로
```
- throw 금지와 허용의 구분(01의 질문): 도구 쪽(`execute`, `prepareArguments`, 검증, `beforeToolCall`, `afterToolCall`)은 전부 try/catch로 감싸져 있고 예외는 `isError: true`인 결과로 바뀐다(`:724-775`, `:841-847`, `:892-895`). 계약은 "throw해도 된다, 루프가 에러 결과로 바꿔 준다"이다. 반대로 `convertToLlm`, `transformContext`, `getApiKey`, 큐 훅, `finishTurn`, `prepareRequest`, `prepareNextTurn`은 try/catch가 없다. 던지면 `runLoop`가 reject되어 `agent_end`가 나가지 않는다(`코드 확인`, 처리는 03의 `Agent`에서 볼 일).
- `args`는 `beforeToolCall`에 검증된 값(`validatedArgs`)으로 가지만 `toolCall`은 원본(`preparedToolCall`이 아님)이다(`:730-731`). 실행되는 `prepared.toolCall`도 원본 `toolCall`이다(`:765`). 그래서 `prepareArguments`로 보정한 인자는 `args`(검증 후)에만 반영되고 `toolCall.arguments`는 보정 전이다. `tool_execution_start`의 `args`도 보정 전 값이다(`코드 확인`).
- `beforeToolCall` 이후 `signal.aborted`를 두 번 확인한다(`:737`, `:756`). 훅이 오래 걸려 그 사이 중단되면 실행하지 않고 `"Operation aborted"` 에러 결과를 낸다.
- 도구 업데이트 이벤트: `onUpdate`로 들어온 부분 결과는 `tool_execution_update`로 나간다. `execute`가 끝나면 `acceptingUpdates = false`가 되어 늦게 도착한 업데이트는 버린다(`:834`, `:838`). 끝나기 전에 쌓인 업데이트 이벤트는 모두 `await`한다(`:839`, `:843`). 따라서 `tool_execution_end`는 항상 모든 `update`보다 뒤다.
- `afterToolCall`의 덮어쓰기(`:877-890`): `content`, `details`, `usage`, `terminate`, `isError`는 `??`로 필드별 대체한다. `structuredContent`는 `content`를 바꾸면서 새 `structuredContent`를 주지 않으면 지운다(내용이 어긋날 수 있어서, 주석 `:878`).
- 에러 결과는 항상 `{ content: [{type:"text", text: message}], details: {} }`이다(`:905`). `isError`는 결과 객체 안이 아니라 별도 값으로 들고 다닌다.

### 7.4 잘린 응답 (`:264-270`, `:478-503`)
`stopReason === "length"`이면 도구를 하나도 실행하지 않고 전부 에러 결과로 돌려준다. 주석에 따르면 스트리밍 중 인자를 salvage 파서로 마무리하므로, 잘린 인자가 파싱도 검증도 통과하는데 내용이 불완전할 수 있기 때문이다. 에러 문구는 "다시 완전한 인자로 호출하라"고 AI에게 안내한다. 이때 `terminate`는 `false`이므로 AI가 다시 시도할 기회를 얻는다(`코드 확인`).

### 7.5 중단(abort) 시 (`:575`, `:613`, `:641`)
- 순차: 각 도구 직후 `signal.aborted`이면 `break`한다. 남은 도구에는 결과 메시지가 만들어지지 않는다.
- 병렬: 준비 중 `aborted`이면 `break`한다. 이미 모아 둔 도구는 실행 함수가 `"Operation aborted"`를 돌려준다(`:620-628`). `break` 이후의 도구 호출은 결과가 없다.
- 그 결과 assistant 메시지의 `toolCall` 개수보다 `toolResult`가 적은 대화 기록이 생길 수 있다. 일부 provider는 이런 기록을 거부하므로(`추론`, 실행 안 함), 이후 처리(03의 `Agent`, coding-agent)가 어떻게 메우는지 확인이 필요하다(`미확인`).
- 이 경로는 `signal`이 `aborted`일 때만 해당한다. `stopReason`이 `aborted`로 오는 경우는 §5 #7에서 이미 종료되므로 도구까지 오지 않는다. 도구 실행 중에 중단된 경우에만 해당한다.

## 8. `declareToolChanges` (`:333-375`): 01에 없던 개념
- 문제: 도구 목록이 중간에 바뀔 수 있다(예: 확장이 도구를 켬/끔). 그런데 AI에게 보내는 요청의 도구 정보를 매번 따로 넘기지 않고, 대화 기록의 system 메시지에 `toolsAdded`/`toolsRemoved`로 변경분을 적는 방식이다.
- 동작: 대기 메시지를 넣기 전에 (a) 지금까지 기록으로 계산한 "AI가 부를 수 있는 도구"(`getCurrentTools`)와 (b) 실제 실행 가능한 `context.tools`의 차이를 구한다. 다르면 system 메시지를 끼워 넣거나(`:359-362`) 대기 중인 system 메시지의 필드를 덮어쓴다(`:356`).
- 의미: 기록을 처음부터 재생하면 항상 `context.tools`가 나온다. 호출 지점은 첫 프롬프트(`:110`)와 매 턴 대기 메시지 주입(`:211`) 두 곳이다.
- `getCurrentTools`, `getToolStateChanges`, `toToolDeclaration`은 ai에서 import한다(`:9-15`). 이들의 내용은 이 문서에서 `미확인`이다(ai/01 기준 확인 필요).
- 이전 분석(Q5~Q8)에는 없는 개념이므로 재검증 때 반영해야 한다.

### 8.1 이 방식이 캐시와 어떻게 이어지나 (2026-10-15 추가, `ai` 코드 확인과 실행 확인)
- 배경: LLM 서비스의 캐시는 요청의 앞에서부터 같은 부분까지만 재사용된다. Anthropic은 `tools`, `system`, `messages` 순이라, 맨 앞의 도구 목록이 바뀌면 뒤 전체가 캐시 미스가 된다.
- pi의 방식: 맨 앞 system 메시지는 고치지 않고, 바뀐 시점 뒤에 변경분만 system 메시지로 쌓는다(위 §8). `ai`가 이를 요청으로 바꿀 때, 모델이 지원하면 처음 도구는 요청 맨 앞에 두고 이후 변경은 대화 중간의 블록(`tool_addition`, `tool_removal`)으로 싣는다. 주석은 도구가 바뀌어도 캐시된 앞부분이 유지된다고 적고 있다(`anthropic-messages.ts`, `코드 확인`).
- 캐시가 깨질 수 있는 경우(폴백): 현재 도구 목록 전체를 요청 맨 앞(`params.tools`)에 보낸다.
  - 두 commit 모두: 모델이 `supportsMidConvoSystemMessages`/`supportsMidConvoToolChanges`를 지원하지 않거나, 처음 도구가 없을 때.
  - `3874b3e98`만: 같은 이름의 도구를 다르게 재정의했을 때(`hasToolRedefinitions`). `28dcce2ba`에서는 `tool_addition`이 정의를 값으로 담아 재정의도 대화 중간에서 처리하므로 폴백하지 않는다.
- 두 commit의 차이(나중에 추가된 도구를 어떻게 싣는가):
  | | `3874b3e98` | `28dcce2ba` |
  |---|---|---|
  | 요청의 `tools` | 처음 도구, 자리표시자, 나중 도구(`defer_loading`)로 점점 늘어남 | 처음 도구와 자리표시자로 고정 |
  | `tool_addition` | 이름만 참조(`tool_reference`) | 정의를 값으로 포함 |
  | 재정의 | 폴백(캐시 깨질 수 있음) | 대화 중간에서 처리 |

#### 실행 확인 (2026-10-15, `artifacts/pi/agent-demos/tool-change-demo.ts`)
실제 `Agent`로 prompt를 두 번 하고 그 사이에 `agent.state.tools`를 바꿔 기록을 모은 뒤, 그 기록을 각 commit의 실제 `anthropic-messages.ts` 요청 만들기에 넣고 요청 본문을 비교했다. Anthropic SDK는 쓰지 않았고(빈 stub), 네트워크 호출도 없다. 출력: `tool-change-demo.3874b3e98.2026-10-15.out`, `tool-change-demo.28dcce2ba.2026-10-15.out`.
| 시나리오 | agent 기록 | `3874b3e98` 요청 2 | `28dcce2ba` 요청 2 |
|---|---|---|---|
| S1 도구 추가(`edit`) | 맨 앞 system 메시지 그대로, 뒤에 `toolsAdded=[edit]` system 메시지 | 일반 tools 동일, `edit[defer]`가 뒤에 추가, `tool_addition:edit` 블록 | tools 완전 동일, `tool_addition`(정의 포함) 블록 |
| S2 도구 제거(`bash`) | 뒤에 `toolsRemoved=[bash]` system 메시지 | tools 동일, `tool_removal:bash` 블록 | 같음 |
| S3 같은 이름 재정의(`read`) | 뒤에 `toolsAdded=[read]`, `toolsRemoved=[read]` | 폴백: `tools=[read]`만 보내 앞부분이 달라짐 | tools 동일, `tool_addition`(정의 포함) 블록 |
| S4 모델이 중간 변경 미지원 | 같음 | 폴백: `tools=[read, bash, edit]`로 앞부분이 달라짐 | 같음 |
- 모든 시나리오에서 agent 쪽 맨 앞 system 메시지는 요청 1과 요청 2에서 같았고, `system` 필드와 요청 1의 `messages`가 요청 2의 앞부분이라는 점도 같았다.
- 한계: 요청 본문의 모양만 비교했다. 실제 캐시 적중은 서버에서만 알 수 있고 호출하지 않았다. `defer_loading` 도구가 캐시 앞부분에 포함되지 않는다는 점은 코드 주석("measured")에 의존한다. Anthropic 경로만 확인했고 OpenAI 계열(`openai-completions.ts:1241`의 `anchorsAdditions`)은 `미확인`이다. `agent` 쪽은 `3874b3e98` 체크아웃의 `transcript.ts` shim을 썼다(`packages/agent/src`는 두 commit이 같다).

## 9. `runToolCall` (`:790-818`): export된 이유
`prepareToolCall`, `executePreparedToolCall`, `finalizeExecutedToolCall`을 이벤트도 메시지도 만들지 않고 그대로 실행한다. 주석에 따르면 도구가 다른 도구를 부를 때 권한 검사 같은 훅이 똑같이 적용되게 하려는 것이다. 사용처는 coding-agent의 `agent-session.ts:31,711`과 `nested-tool-calls.ts`로 handoff에 적혀 있으나 이 문서에서는 `미확인`이다(coding-agent 단계에서 확인).

## 10. 요약 표: 01의 `미확인` 해소 여부
| 01의 질문 | 답 | 위치 |
|---|---|---|
| 훅 호출 지점과 순서 | §5 표 | `:183-299` |
| `terminate`/`finishTurn`/큐 우선순위 | §5.1 표 | `:245-318` |
| 병렬 실행 이벤트 순서 | §7.2 표 | `:586-660` |
| 종료 조건 | error/aborted, `finishTurn: end`, 큐 없음 + `continue` 없음 | §5.1 |
| `convertToLlm`/`transformContext` 순서 | transform, convert, normalizeContext 순 | `:390-397` |
| `getApiKey`가 들어가는 방식 | 요청마다 호출해 `apiKey` 옵션을 덮어씀 (`||` 정적 키) | `:400-407` |
| 루프 쪽 throw 처리 | 도구 쪽만 catch, 나머지 훅은 catch 없음 | §7.3 |

## 11. 발견 (정리)
1. throw 정책이 비대칭이다. 도구 관련은 루프가 흡수하고, 그 밖의 훅은 호출자 책임이다. 01의 "곳곳에 throw 금지"가 정확히 이 구분임을 확인했다.
2. 종료 결정은 7단계 우선순위다(§5.1). 가장 강한 것은 `error/aborted`로, `finishTurn`도 이기지 못한다.
3. 병렬은 준비를 순차로 하고, 실행은 동시에 하고, 완료 이벤트는 완료 순으로, 결과 메시지는 호출 순으로 낸다.
4. 중단 시 `toolResult`가 비는 경우가 있다(§7.5, 05 F에서 실행 확인. 뒤에서 메우는지는 `미확인`).
5. `runAgentLoopContinue`는 호출자의 `messages` 배열을 직접 바꾸고, `agentLoop`는 reject를 처리하지 않는다(§3). `Agent`를 거치면 안전하다(03).
6. 도구 목록은 요청 옵션이 아니라 대화 기록(system 메시지)에 실린다(§8).

## 12. 미확인
- `normalizeContext`가 `tools`/`systemPrompt`를 어떻게 처리하는지, `streamFn`이 `...config`의 여분 필드를 무시하는지 (ai 쪽)
- ~~중단 시 `toolResult` 누락~~ → 05 F에서 누락을 확인했다. 메우는 곳은 `Agent`에 없다(03 §12). ai 변환 단계와 coding-agent는 `미확인`
- ~~훅 throw 복구~~ → 03 §7, 05 E에서 확인
- ~~`getDefaultStreamFn` 관계~~ → 04 §9. coding-agent의 설치 위치는 `sdk.ts:2` import만 확인했고 호출은 `미확인`
- ~~실행 확인 없음~~ → 05에서 §5.1, §7.2, §7.4, §7.5를 가짜 `streamFn`으로 재현했고 모두 일치

## 13. 다음
[03-agent-class](./03-agent-class.md): `agent.ts`. 상태 갱신, steering/follow-up 큐와 `QueueMode`, 구독자 순차 `await`, 실패 처리, 이 문서 §3, §7.5의 `미확인`을 확인한다.
