# Q6: `Agent` 클래스는 루프를 어떻게 감싸고 상태를 관리하나?

- **Commit**: `4259686d9290c0d73ae7192b796aee3e530a9779` · **작성일**: 2026-09-29 · **목적**: 학습 (Q5 후속)
- **대상**: `packages/agent/src/agent.ts` (613줄, 핵심 구간 전부 읽음), `types.ts` `AgentState`

## 결론

`Agent`는 상태가 없는 `runLoop` 위에 **상태·큐·실행 잠금·구독**을 얹은 래퍼다. 핵심은 세 가지다.

1. **상태는 이벤트로만 갱신된다.** 루프에는 대화의 복사본을 넘기고, 루프가 emit한 이벤트를 `processEvents`가 받아서 `Agent`의 대화 목록에 반영한다. `코드 확인`
2. **구독자(listener)는 하나씩 await된다.** 구독자가 느리면 루프도 그만큼 기다린다. `코드 확인` (느린 구독자가 루프를 늦추는 것은 코드 구조에서 나온 `추론`)
3. **루프 밖에서 예외가 나도 이벤트 순서는 지킨다.** `handleRunFailure`가 가짜 error 메시지를 만들어 `message_start/end → turn_end → agent_end`를 대신 emit한다. `코드 확인`

## `processEvents`: 이벤트 → 상태 (`agent.ts:565`)

| 이벤트 | 상태 변화 |
|---|---|
| `message_start` / `message_update` | `streamingMessage` = 현재 메시지 (UI의 "작성 중" 표시용) |
| `message_end` | `streamingMessage` 비우고 **`messages`에 push** |
| `tool_execution_start` / `_end` | `pendingToolCalls` Set에 id 추가 / 제거 (매번 새 Set으로 교체) |
| `turn_end` | assistant 메시지에 `errorMessage`가 있으면 `state.errorMessage`에 기록 |
| `agent_end` | `streamingMessage` 비움 |

상태를 반영한 뒤 `for (listener of listeners) await listener(event, signal)`로 구독자를 **등록한 순서대로 차례차례** 호출한다. 활성 run이 없는데 호출되면 throw한다.

**왜 이렇게 했나 (`추론`)**: 대화 목록을 바꾸는 경로가 이벤트 하나뿐이라서, UI나 세션 저장처럼 이벤트를 구독하는 쪽과 `Agent` 상태가 어긋날 수 없다.

## 실행 생명주기

```
prompt(input)
  ├─ activeRun 있으면 throw ("steer() 또는 followUp()을 쓰라")
  └─ runWithLifecycle
       ├─ activeRun = { promise, resolve, abortController }
       ├─ isStreaming = true, errorMessage 초기화
       ├─ try   runAgentLoop(복사본 context, createLoopConfig(), processEvents, signal, streamFunction)
       ├─ catch handleRunFailure(error, aborted)   ← 가짜 error 메시지로 이벤트 순서 보장
       └─ finally finishRun()  → isStreaming=false, pendingToolCalls 비움, activeRun.resolve()
```

- **`waitForIdle()`**은 `activeRun.promise`를 반환한다. 이 promise는 `agent_end` 구독자까지 모두 끝난 뒤에 resolve된다. 즉 `agent_end` 이벤트가 곧 idle을 뜻하지는 않는다(`agent.ts:563` 주석).
- **`abort()`**는 `abortController.abort()`만 호출한다. 실제 중단은 signal을 받은 pi-ai 스트림과 tool이 한다.
- **`reset()`**은 실행 중이면 throw한다. 대화는 맨 앞 system 메시지(prompt·tool 선언)만 남기고 지우며, 큐도 비운다.

## `continue()`: 재시도·재개 (`agent.ts:384`)

- 마지막 메시지가 `user`나 `toolResult`이면 → `runAgentLoopContinue`로 그대로 재개한다.
- 마지막 메시지가 `assistant`이면 (정상적으로 끝난 상태):
  - steering 큐가 있으면 그것을 새 prompt로 실행한다. 첫 steering 확인은 건너뛴다(`skipInitialSteeringPoll`). 같은 메시지를 두 번 넣지 않기 위해서다.
  - 없으면 follow-up 큐로 실행한다.
  - 둘 다 없으면 throw.

## 큐 (`PendingMessageQueue`, `agent.ts:143`)

- `steer()`/`followUp()`은 enqueue만 한다. 루프가 `getSteeringMessages`/`getFollowUpMessages` hook을 통해 `drain()`으로 꺼낸다(`createLoopConfig`, `agent.ts:496-503`).
- mode의 기본값은 `"one-at-a-time"`이다. 한 번에 하나씩 꺼내므로, 여러 개가 쌓여 있으면 turn마다 하나씩 들어간다. `"all"`이면 한 번에 전부 꺼낸다.

## 상태 모델 (`AgentState`, `types.ts:382`)

- `systemPrompt`는 **읽기 전용이다.** 대화 안의 system 메시지에서 다시 계산한다. prompt를 바꾸려면 system 메시지를 새로 추가해야 한다.
- `tools`/`messages`에 새 배열을 대입하면 최상위 배열을 복사해서 저장한다. tool 목록이 바뀌면 다음 요청 전에 `declareToolChanges`(Q5)가 system 메시지로 모델에게 알린다.
- 생성자는 `initialState.systemPrompt`와 `tools`로 맨 앞 system 메시지를 만든다. `messages`가 이미 system 메시지로 시작하면 만들지 않는다.
- `defaultConvertToLlm`은 system/user/assistant/toolResult 메시지만 남긴다. custom 메시지(`CustomAgentMessages` 확장)는 기본적으로 LLM에 보내지 않는다.

## 남은 질문

- coding-agent가 `subscribe`로 무엇을 하는가? (세션 저장, TUI 렌더링으로 보이지만 `미확인`)
- 구독자가 느리면 LLM 스트림이 쌓이는데, 이것이 의도된 backpressure인가? (`추론`, 공식 문서 확인 필요)
