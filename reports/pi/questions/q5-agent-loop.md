# Q5: `agent-loop`은 어떻게 동작하나?

- **Commit**: `4259686d9290c0d73ae7192b796aee3e530a9779` · **작성일**: 2026-09-29 · **목적**: 학습 (Q1 1단계, Q4 다음)
- **대상**: `packages/agent/src/agent-loop.ts` (940줄, 전체 읽음), `agent.ts` 일부, `types.ts` `AgentLoopConfig`/`AgentEvent`
- **관련 그림**: [runLoop 제어 흐름](../diagrams/agent-loop-workflow.html) · [1턴 시퀀스](../diagrams/agent-loop-sequence.html)

## 결론

`agent-loop`은 **"LLM 응답 받기 → tool 실행 → 결과를 대화에 붙이기"를 tool 호출이 없을 때까지 반복하는 순수 함수 묶음**이다. 상태나 큐는 갖지 않고, 모든 정책은 `AgentLoopConfig`의 콜백(hook)으로 바깥에서 주입받는다. 상태(메시지 목록, steering/follow-up 큐, abort)는 `Agent` 클래스(`agent.ts`)가 갖는다. `코드 확인`

## 구성 요소

| 함수 | 줄 | 역할 |
|---|---|---|
| `agentLoop` / `agentLoopContinue` | 38 / 71 | `EventStream`을 반환하는 래퍼. 내부에서 `runAgentLoop*`를 실행하고 이벤트를 push한다 |
| `runAgentLoop` | 102 | 새 prompt를 context에 추가하고 `agent_start`, `turn_start`, prompt의 `message_start/end`를 emit한 뒤 `runLoop`을 호출한다 |
| `runAgentLoopContinue` | 128 | prompt 없이 현재 context에서 재개한다(재시도용). 마지막 메시지가 `assistant`이면 throw |
| **`runLoop`** | 163 | 이중 루프 본체 (아래 참고) |
| `streamAssistantResponse` | 381 | `AgentMessage[]`를 `Message[]`로 바꾸는 유일한 지점. pi-ai 이벤트를 `message_*` 이벤트로 변환한다 |
| `executeToolCalls` | 508 | sequential 또는 parallel 실행 선택 |
| `prepareToolCall` | 707 | tool 조회 → `prepareArguments` → `validateToolArguments` → `beforeToolCall` |
| `executePreparedToolCall` | 820 | `tool.execute(id, args, signal, onUpdate)` 호출. throw는 에러 결과로 바꾼다 |
| `finalizeExecutedToolCall` | 853 | `afterToolCall`로 결과 일부를 덮어쓴다 |
| `runToolCall` | 810 | 위 단계를 이벤트 없이 실행하는 공개 함수. tool이 다른 tool을 부를 때(codemode 등) 같은 hook을 거치게 한다 |
| `declareToolChanges` | 333 | 실행 가능한 tool 목록과 대화에 선언된 tool 목록의 차이를 system message(`toolsAdded`/`toolsRemoved`)로 넣는다 |

## `runLoop` 제어 흐름 (`agent-loop.ts:163-321`)

```
pending = getSteeringMessages()
outer: while (true)
  inner: while (hasMoreToolCalls || pending.length > 0)
    [2턴째부터] prepareNextTurn → context/model/thinking 교체, turn_start
    pending(+prepared) 메시지 emit 후 context에 push
    prepareRequest → 이번 요청의 context/model/thinking 교체
    message = streamAssistantResponse(...)
    if stopReason in (error, aborted): finishTurn → turn_end → agent_end → return   ← 무조건 종료
    toolCalls가 있으면:
      stopReason == length → 전부 실행하지 않고 에러 결과 (인자가 잘렸을 수 있음)
      아니면 executeToolCalls → hasMoreToolCalls = !terminate
    decision = finishTurn(...) ; turn_end
    decision == end → agent_end → return
    pending = getSteeringMessages()
  followUp = getFollowUpMessages()
  있으면 → pending = followUp; continue outer
  finishTurn이 continue였으면 → context만으로 1턴 더
  break → agent_end
```

### 루프가 끝나는 조건

| 조건 | 위치 | 비고 |
|---|---|---|
| `stopReason`이 `error` 또는 `aborted` | :245 | hook으로도 막을 수 없는 hard exit. 재시도는 상위에서 `agentLoopContinue`로 한다 |
| `finishTurn`이 `{ action: "end" }` 반환 | :289 | 큐를 확인하지 않고 바로 끝낸다 |
| tool 호출 없음 + steering 없음 + follow-up 없음 + 명시적 continue 없음 | :317 | 정상 종료 |
| tool 배치의 **모든** 결과가 `terminate: true` | :689 | 이번 turn 뒤에 tool 결과를 LLM에 다시 보내지 않는다. 하나라도 false면 계속 |

### steering과 follow-up의 차이

- **steering** (`Agent.steer()`): 작업 중에 끼워 넣는 메시지. 매 turn이 끝날 때 확인한다. 현재 turn의 tool call은 건너뛰지 않는다(`types.ts` 주석).
- **follow-up** (`Agent.followUp()`): agent가 멈추려는 시점에만 확인한다. 끝난 뒤에 처리할 메시지.
- 두 큐 모두 `PendingMessageQueue`이고, mode가 `all`이면 한 번에 전부, 아니면 하나씩 꺼낸다(`agent.ts:143-175`).

## tool 실행 세부

- **모드**: 기본은 `parallel`이다. 설정이 `sequential`이거나, 호출된 tool 중 하나라도 `executionMode: "sequential"`이면 전체를 순차 실행한다(:516).
- **parallel의 순서 보장**: 준비 단계(prepare, `beforeToolCall`)는 순서대로 하고 실행만 동시에 한다. `tool_execution_end`는 끝난 순서대로 emit되고, `toolResult` 메시지는 원래 assistant 메시지의 순서대로 emit된다(:646-654).
- **실패를 throw하지 않는다**: tool 없음, 검증 실패, `beforeToolCall`의 block, execute 중 throw, `afterToolCall` 중 throw는 모두 `isError: true`인 toolResult가 되어 LLM에 다시 전달된다. 모델이 스스로 고칠 기회를 주는 설계다. `코드 확인` / 의도는 `추론`
- **`length`로 잘린 응답**: tool call 인자가 잘렸을 수 있으므로 하나도 실행하지 않는다. "완전한 인자로 다시 호출하라"는 에러 결과를 돌려준다(:478).

## 이벤트 계약 (`types.ts:514`)

```
agent_start
  turn_start
    message_start/end            (prompt, steering, system 메시지)
    message_start → message_update* → message_end   (assistant 스트리밍)
    tool_execution_start → tool_execution_update* → tool_execution_end
    message_start/end            (toolResult)
  turn_end { message, toolResults }
  turn_start ...
agent_end { messages }
```

- **turn** = assistant 응답 1개와 그에 따른 tool 호출·결과.
- `streamAssistantResponse`는 `start` 이벤트에서 partial 메시지를 context에 먼저 넣고, 이후 이벤트마다 교체한다. `message_update`에는 `{ ...partialMessage }` **복사본**을 보낸다. Q4에서 추론한 "partial은 공유 객체라 복사가 필요하다"를 여기서 실제로 처리하고 있다. `코드 확인`

## hook 목록과 호출 시점 (`AgentLoopConfig`)

| hook | 시점 | 용도 예 |
|---|---|---|
| `getSteeringMessages` | 시작할 때, 각 turn이 끝날 때 | 작업 중 사용자 입력 |
| `prepareNextTurn` | 2번째 turn부터, turn 시작 전 | compaction, 모델 교체 |
| `prepareRequest` | 모든 LLM 요청 직전 | 요청 단위로 context/model 교체 |
| `transformContext` | `convertToLlm` 전 | 오래된 메시지 정리 |
| `convertToLlm` (필수) | LLM 호출 직전 | custom 메시지를 LLM 메시지로 변환하거나 제거 |
| `getApiKey` | LLM 호출마다 | 만료가 짧은 OAuth 토큰 |
| `beforeToolCall` | 인자 검증 후, 실행 전 | 권한 확인, 차단 |
| `afterToolCall` | 실행 후, `tool_execution_end` 전 | 결과 수정 |
| `finishTurn` | tool 결과 뒤, `turn_end` 전 | 종료 또는 강제 계속 |
| `getFollowUpMessages` | 멈추려는 시점 | 대기 중인 다음 메시지 |

`convertToLlm`, `transformContext`, `getApiKey`, `getSteeringMessages`, `getFollowUpMessages`는 계약상 **throw하면 안 된다**. throw하면 정상적인 이벤트 순서 없이 루프가 중단된다(`types.ts` 주석). `코드 확인`

## `Agent` 클래스와의 관계

- `Agent.prompt()`는 `runWithLifecycle` 안에서 `runAgentLoop(messages, createContextSnapshot(), createLoopConfig(), processEvents, signal, streamFunction)`을 호출한다(`agent.ts:432-445`).
- context는 **복사본**을 넘긴다(`messages.slice()`). 루프는 그 복사본을 바꾸고, `Agent`는 이벤트(`processEvents`)를 받아 자기 상태를 갱신한다. `코드 확인` (processEvents 내부는 `미확인`)
- 실행 중에 `prompt()`를 다시 부르면 throw한다. 이때는 `steer()`/`followUp()`을 쓰라고 안내한다(`agent.ts:376`).
- `abort()`는 `AbortController.abort()`만 호출한다. 실제 중단은 signal을 전달받은 pi-ai 스트림과 tool들이 한다.

## 다음에 볼 것

- `agent.ts` `processEvents` / `handleRunFailure`: 이벤트로 상태를 어떻게 갱신하고, 루프 밖에서 throw가 나면 어떻게 처리하는지
- coding-agent `core/agent-session.ts`: `finishTurn`/`prepareNextTurn`/`beforeToolCall`을 실제로 무엇으로 채우는지 (재시도, compaction, extension `tool_call` hook)
- `agent/src/harness/`: pico3 계열이 이 루프를 대체하는지 감싸는지
