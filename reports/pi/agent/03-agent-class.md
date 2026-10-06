# agent 03: `Agent` 클래스 (`packages/agent/src/agent.ts`)

- **기준 commit**: `28dcce2ba` (`packages/agent/src`는 `3874b3e98`과 동일)  / **분석일**: 2026-10-06
- **선행 문서**: [01-types](./01-types.md), [02-agent-loop](./02-agent-loop.md)
- **읽은 파일**: `agent.ts` 613줄 전체 (이 문서의 줄 번호는 모두 이 파일)
- **검증 수준**: 코드 흐름은 `코드 확인`. 실행한 것은 없다(05에서 가짜 `streamFn`으로). 동작 결과로 적은 것 중 코드 구조에서 끌어낸 것은 `추론`으로 표시.

## 1. 이 문서의 질문
(1) `Agent`는 루프 위에 무엇을 얹는가? (2) 상태는 어떻게 갱신되나? (3) steering / follow-up 큐와 `QueueMode`는 어떻게 동작하나? (4) 루프에서 예외가 나면? (5) 02에서 `미확인`으로 남긴 것(`messages` 공유, `toolResult` 누락, 훅 throw).

## 2. 한 줄 답
`Agent`는 **상태가 없는 `runLoop`에 "대화 기록 + 실행 잠금 + 큐 2개 + 구독자"를 얹은 래퍼**다. 루프에는 매번 **복사본 context**와 **그때 값으로 만든 config**를 넘기고, 루프가 내보내는 이벤트(`processEvents`)로만 자기 상태를 갱신한다.

## 3. 구성 (`:188-254`)
| 묶음 | 필드 | 줄 |
|---|---|---|
| 상태 | `_state` (`MutableAgentState`) | `:189`, 생성 `:82-111` |
| 큐 | `steeringQueue`, `followUpQueue` (`PendingMessageQueue`) | `:191-192` |
| 구독자 | `listeners: Set` | `:190` |
| 실행 잠금 | `activeRun?: { promise, resolve, abortController }` | `:218` |
| 주입 훅(public 필드) | `convertToLlm`, `transformContext`, `streamFunction`, `getApiKey`, `beforeToolCall`, `afterToolCall`, `finishTurn`, `prepareRequest`, `prepareNextTurn`(+`WithContext`) | `:194-217` |
| 요청 옵션 | `sessionId`, `thinkingBudgets`, `transport`(기본 `"auto"`), `maxRetryDelayMs`, `toolExecution`(기본 `"parallel"`), `onPayload/onResponse/onProviderStreamEvent` | `:198-228` |

- 훅들이 **public 필드**라서 생성 뒤에도 `agent.beforeToolCall = ...`처럼 바꿀 수 있다 (`코드 확인`).
- `defaultConvertToLlm`(`:38`)은 `system/user/assistant/toolResult` 역할만 남긴다. 사용자 정의 메시지는 기본으로 AI에 안 간다.
- 생성자 `:232`: `options ?? {}`를 쓰고 `streamFn`이 없으면 `getDefaultStreamFn()` (주석: 옛 컴파일 소비자 호환). 타입은 `streamFn` 필수.
- `DEFAULT_MODEL`(`:57`)은 `provider: "unknown"` 등의 빈 모델. `initialState.model`을 안 주면 이것이 되어 **요청 시점에야** 실패한다(`추론`).

## 4. 상태 모델 (`:70-111`)
- `systemPrompt`는 **getter**다(`:89`): `getCurrentSystemPrompt(messages)`로 **대화 안 system 메시지에서 다시 계산**한다. 별도 저장 필드가 없다 → 프롬프트를 바꾸려면 system 메시지를 기록에 추가해야 한다 (Q6과 일치).
- 생성자는 `systemPrompt`와 `tools`로 **첫 system 메시지를 만든다**(`createInitialSystemMessage`). 이미 `messages[0]`이 system이면 안 만든다(`:85-86`). 02 §8의 `declareToolChanges`와 짝이다: 도구 정보가 기록 안에 있다.
- `tools`, `messages`는 setter가 `slice()`로 **얕은 복사**해 저장한다(`:97-105`). 배열 자체를 바꾸는 `push`는 getter가 돌려준 원본에 직접 되므로 허용된다.
- `state` getter는 `_state`를 그대로 돌려준다(`:276`). 타입은 `AgentState`(읽기 전용 느낌)지만 **런타임 객체는 같은 것**이다 (`코드 확인`).

## 5. 이벤트 → 상태: `processEvents` (`:565-612`)
| 이벤트 | 상태 변화 |
|---|---|
| `message_start`, `message_update` | `streamingMessage = event.message` |
| `message_end` | `streamingMessage` 비움, **`messages.push(event.message)`** |
| `tool_execution_start`/`end` | `pendingToolCalls`에 id 추가/삭제 (**매번 새 `Set`으로 교체**) |
| `turn_end` | assistant 메시지에 `errorMessage`가 있으면 `state.errorMessage` |
| `agent_end` | `streamingMessage` 비움 |

그 뒤 `for (listener of listeners) await listener(event, signal)` — **등록 순서대로 하나씩 기다린다**(`:609-611`). 활성 run이 없으면 throw(`:606-608`).

### 5.1 02와 합쳐서 보는 핵심 (`코드 확인` + `추론`)
- 루프의 `emit` = `processEvents`(`:441`, `:453`). 루프는 `await emit(...)`(02)하므로 **구독자가 느리면 그 이벤트에서 루프가 멈춘다**. 특히 `message_update`는 스트림 `for await` 안에서 `await emit`이라(02 §6) **구독자가 느리면 AI 스트림 소비도 느려진다**(`코드 확인`). 그 사이 ai 쪽 스트림 버퍼가 어떻게 되는지는 ai/03-0 참조(`미확인`).
- **상태는 이벤트로만 바뀐다**: `state.messages`에는 `message_end`일 때만 들어가고, 루프가 쓰는 context는 **별개 복사본**이다(`createContextSnapshot`, `:460-465`). 그래서 02 §3의 걱정(`runAgentLoopContinue`가 호출자 `messages`를 직접 바꿈)은 **`Agent` 경유에서는 해당하지 않는다**: 넘기는 것이 `slice()` 복사본(`:462`).
- 반대로 루프가 **이벤트 없이** context를 바꾸는 경우(`prepareNextTurn`/`prepareRequest`가 context를 교체)는 `state.messages`에 **반영되지 않는다**: `Agent`가 받는 것은 이벤트뿐이기 때문(`추론`). 압축(compaction)처럼 context를 교체하는 쪽이 `state.messages`도 따로 갱신해야 할 것이다 → coding-agent에서 확인(`미확인`).
- `message_start`에서 `streamingMessage`가 **루프가 낸 얕은 복사본**(02 §6)이다. 그래서 `state.streamingMessage`와 루프 안 context의 partial은 다른 객체다 (`코드 확인`).
- `message_end`의 `push`는 **구독자 호출 전**이므로, 구독자 안에서 `agent.state.messages`를 읽으면 이미 그 메시지가 들어 있다(`코드 확인`).

## 6. 실행 생명주기 (`:507-556`)
```
prompt / continue
  └ runWithLifecycle(executor)
       activeRun = { promise, resolve, abortController }       ← 잠금
       isStreaming = true, streamingMessage/errorMessage 초기화
       try   executor(signal)
       catch handleRunFailure(error, signal.aborted)
       finally finishRun()    → isStreaming=false, pendingToolCalls 비움, resolve(), activeRun = undefined
```
- 잠금 확인이 **세 군데** 중복: `prompt`(`:374`), `continue`(`:385`), `runWithLifecycle`(`:508`). 각각 다른 메시지로 throw한다.
- `waitForIdle()`(`:350`): `activeRun.promise`. `finishRun`에서 resolve되므로 **`agent_end` 구독자들이 끝난 뒤**다(`:561-563` 주석과 일치). `agent_end`가 곧 idle은 아니다.
- `abort()`(`:341`): `abortController.abort()`만 한다. 중단 결과는 02 §5.1 #1(`stopReason: "aborted"`)과 §7.5로 이어진다.
- `reset()`(`:355`): 실행 중이면 throw. `getCurrentSystemMessage`로 **맨 앞(현재) system 메시지만 남기고** 비우고 큐도 비운다(`:360-367`). 도구 변경분(`toolsAdded`)을 담은 system 메시지가 여러 개 쌓였다면 **현재 것 하나**만 남는다고 읽힌다(`getCurrentSystemMessage` 내부는 `미확인`).

## 7. 루프 밖에서 예외가 나면 (`:532-548`) — 02의 `미확인` 해소
- 02에서 본 대로 도구 쪽 외의 훅(`convertToLlm`, `transformContext`, `getApiKey`, 큐, `finishTurn`, `prepareRequest`, `prepareNextTurn`)이 throw하면 `runLoop`가 reject된다. 여기서 `catch`가 받는다(`:525`).
- `handleRunFailure`는 **가짜 assistant 메시지**를 만든다: 빈 텍스트, `stopReason: aborted ? "aborted" : "error"`, `errorMessage: error.message`, `usage` 0. 이어서 `message_start` → `message_end` → `turn_end { toolResults: [] }` → `agent_end { messages: [failureMessage] }`를 **직접 `processEvents`로 보낸다**(`:544-547`).
- 효과: 구독자는 정상 종료와 **같은 이벤트 모양**을 받는다. `state.messages`에도 이 빈 에러 메시지가 `message_end`로 **쌓인다**. 이 메시지에는 **어디서 실패했는지(턴 중간 등)가 없다**.
- 주의 1: `agent_end`의 `messages`는 **`[failureMessage]` 하나뿐**이다. 정상 종료에서는 이번 run의 새 메시지 전체인데(02 §3) 실패 때는 그 앞에 만든 메시지가 빠진다 (`코드 확인`). 구독자가 `agent_end.messages`로 저장하면 실패 run은 앞의 메시지를 놓친다 → 구독자가 `message_end`로 저장해야 안전(`추론`, coding-agent에서 확인).
- 주의 2 (`추론`): 구독자 자신이 throw하면 그 예외도 `processEvents`에서 올라와 `runLoop`를 reject시키고, `handleRunFailure`가 다시 `processEvents`를 불러 구독자를 또 부른다. 구독자가 또 throw하면 `catch` 안에서 던져지므로 `prompt()`가 reject된다. `finally`의 `finishRun`은 어느 경우에도 실행되어 잠금은 풀린다.
- 즉 throw 금지 계약(01, 02)의 **안전망**이 여기 있다: 계약을 어겨도 이벤트 순서와 잠금은 유지된다.

## 8. `prompt`와 `continue` (`:371-411`)
- `prompt(string, images?)`: `{ role: "user", content: [text, ...images], timestamp }` 한 개로 만든다(`:425-429`). 메시지나 배열을 넘길 수도 있다. 실행 중이면 throw("`steer()`나 `followUp()`을 쓰라").
- `continue()`:
| 마지막 메시지 | 동작 |
|---|---|
| 없음, 또는 전부 system | throw "No messages to continue from" (`:390`) |
| `user` / `toolResult` | `runContinuation` → `runAgentLoopContinue` (`:410`) |
| `assistant` | steering 큐를 `drain` → 있으면 그것을 prompt로 실행(`skipInitialSteeringPoll`), 없으면 follow-up 큐 `drain` → 있으면 실행, 둘 다 없으면 throw (`:394-407`) |
- `skipInitialSteeringPoll`(`:397`, `:468-502`): 루프의 **첫** `getSteeringMessages()`(02 §4)를 한 번 건너뛴다(`[]` 반환). 이미 `drain`한 steering을 방금 prompt로 넣었으므로, 같은 큐에서 다음 것을 한 턴에 또 넣지 않으려는 것(주석 없음, 구조에서 `추론`).
- follow-up 경로(`:403`)는 `skipInitialSteeringPoll`을 안 준다. steering이 비어 있어서 건너뛸 이유가 없다.
- 이 경로가 coding-agent의 재시도(`agent.continue()`)에서 쓰이는지는 `미확인` (00 §6의 재검증 대상).

## 9. 큐 (`PendingMessageQueue`, `:143-174`)
| 메서드 | 동작 |
|---|---|
| `enqueue` | 뒤에 추가 |
| `peek` | `mode === "all"`이면 전부(복사), 아니면 **첫 하나** |
| `drain` | `peek` 결과를 꺼내고 그만큼 앞에서 제거 |
| `clear`, `hasItems` | |
- 기본 모드 둘 다 `"one-at-a-time"`(`:247-248`). 모드는 `steeringMode`/`followUpMode` setter로 **실행 중에도** 바꿀 수 있다(`:281-296`).
- 루프 연결(`:496-503`): `getSteeringMessages: () => steeringQueue.drain()`, `getFollowUpMessages: () => followUpQueue.drain()`. 두 번째 인자 없이 매번 `drain`하므로 `one-at-a-time`이면 **턴마다 하나씩** 들어간다.
- 02 §4의 흐름과 합치면: steering은 매 턴 끝에서 `drain`되고, follow-up은 에이전트가 멈추려 할 때만(안쪽 루프 밖) `drain`된다.
- `peekQueuedMessages()`(`:330`): **steering이 하나라도 있으면 steering만**, 없을 때 follow-up. 루프의 우선순위(steering 먼저)와 같다. 소비하지 않는다.
- `steer()`/`followUp()`은 **실행 중이 아니어도** 쓸 수 있고(잠금 확인 없음) 다음 `continue()`나 run에서 소비된다 (`코드 확인`).

## 10. `createLoopConfig` (`:467-505`) — "run 시작 시점의 스냅샷"
- 필드 값(`model`, `reasoning`, `sessionId`, `transport`, `thinkingBudgets`, `toolExecution`, 훅들)을 **run 시작 때 읽어 객체에 복사**한다. 그래서 **run 도중에** `agent.state.model = ...`이나 `agent.beforeToolCall = ...`를 바꿔도 **현재 run에는 반영되지 않는다**(`코드 확인`; 다음 run부터 적용). run 안에서 바꾸려면 `prepareRequest`/`prepareNextTurn`(02 §5)으로 해야 한다. 큐 훅(`getSteeringMessages` 등)만 `this`의 큐를 매번 참조하므로 실시간이다.
- `reasoning: thinkingLevel === "off" ? undefined : thinkingLevel`(`:471`): `off`를 `undefined`로 변환. 루프의 같은 규칙(02 §5 #1)과 대응.
- `prepareNextTurn`은 **두 변형**: `prepareNextTurnWithContext(context, signal)`가 있으면 그것을, 아니면 `prepareNextTurn(signal)`을 부르는 어댑터(`:484-492`). 루프(`types.ts`)의 시그니처는 `(context) => ...`라서 **`Agent`가 `signal`을 끼워 주는 것**이다. 둘 다 없으면 `undefined`.
- `onPayload`, `onResponse`, `onProviderStreamEvent`는 설정에 실어 보내 `streamFn`이 소비(ai 쪽). 

## 11. 이전 분석(Q6)과 대조 — 재검증 결과
| Q6의 서술 | 현재 코드 | 결과 |
|---|---|---|
| 상태는 이벤트로만 갱신 | `processEvents`(`:565`) | **일치** |
| 구독자 순차 `await`, 느리면 루프도 늦음 | `:609-611`, 02 §6 | **일치** (스트림 소비도 늦어짐은 추가 확인) |
| `handleRunFailure`가 가짜 error 메시지로 이벤트 순서 보장 | `:532-548` | **일치**. 추가: `agent_end.messages`가 `[failure]` 하나뿐 |
| `continue()` steering → follow-up → throw | `:394-407` | **일치** |
| `waitForIdle`은 `agent_end` 구독자까지 후 | `:350`, `:561-563` | **일치** |
| `systemPrompt` 읽기 전용 | getter `:89` | **일치** |
| 큐 기본 `one-at-a-time` | `:247-248` | **일치** |
| 남은 질문: 느린 구독자 = 의도된 backpressure? | 코드는 `await`이므로 구조상 backpressure. 의도 문서는 `미확인` | `추론` 유지 |
→ Q6 본문은 이 SHA에서도 유효. **추가된 것**: §5.1(복사본/이벤트 전용 상태), §10(스냅샷), 02 §7.5의 `toolResult` 누락은 `Agent`가 메우지 **않는다**(코드에 해당 처리 없음).

## 12. 02의 `미확인` 해소 표
| 02의 미확인 | 답 |
|---|---|
| continue 경로가 호출자 `messages`를 바꾸는가 | `Agent` 경유에서는 **아니오** (`slice()`로 넘김, `:462`) |
| 훅 throw를 `Agent`가 어떻게 복구하나 | `handleRunFailure`가 가짜 에러 메시지와 이벤트로 마무리, 잠금은 `finally`로 해제 (§7) |
| 중단 시 `toolResult` 누락을 누가 메우나 | **`Agent`는 안 메운다** (코드 없음). coding-agent/provider 변환 쪽 `미확인` |

## 13. 발견 (정리)
1. **`Agent` = 스냅샷 입력 + 이벤트 전용 출력.** 루프와 `Agent`는 객체를 공유하지 않는다.
2. **run 도중 설정 변경은 현재 run에 안 먹는다**(큐 제외). 바꾸려면 루프 훅을 써야 한다.
3. **context를 교체하는 훅은 `state.messages`를 갱신하지 않는다**(`추론`) → coding-agent의 압축 처리 확인 필요.
4. **실패 run의 `agent_end.messages`는 `[failureMessage]`뿐.** 이벤트(`message_end`)로 저장해야 안 놓친다.
5. **느린 구독자는 AI 스트림 소비를 늦춘다.**

## 14. 미확인
- `getCurrentSystemMessage`/`getCurrentSystemPrompt`/`createInitialSystemMessage`의 내부(ai 쪽)
- coding-agent가 `subscribe`로 무엇을 하는지, 압축 시 `state.messages` 갱신 방법
- 구독자 throw 시나리오 실행 확인(05)
- 느린 구독자일 때 ai `EventStream`의 버퍼 동작

## 15. 다음
[04-proxy](./04-proxy.md): `proxy.ts`(406줄).
