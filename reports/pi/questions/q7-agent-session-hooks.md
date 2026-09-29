# Q7: coding-agent는 agent-loop의 hook을 무엇으로 채우나?

- **Commit**: `4259686d9290c0d73ae7192b796aee3e530a9779` · **작성일**: 2026-09-29 · **목적**: 학습 (Q5·Q6 후속)
- **대상**: `packages/coding-agent/src/core/sdk.ts` (`new Agent`, :389-424), `core/agent-session.ts` (4295줄 중 hook 설치, 이벤트 처리, 재시도, compaction 구간)
- **관련 그림**: [run 이후 재시도·compaction 루프](../diagrams/agent-session-postrun-workflow.html)

## 결론

coding-agent는 hook을 두 곳에서 채운다.

- **`sdk.ts`**: `Agent`를 만들 때 넣는 기본값(`convertToLlm`, `streamFn`, `transformContext`)
- **`AgentSession`**: 그 뒤에 덧씌우는 나머지. 기존 hook을 `previous...`로 보관해 두고 자기 로직으로 감싼다(체인).

가장 중요한 사실은 두 가지다.

1. **대화의 원본은 세션 파일이다.** `prepareRequest`가 매 요청마다 루프의 context를 버리고 `sessionManager.buildSessionProjection()`으로 다시 만든다. `Agent`나 루프가 들고 있는 대화는 원본이 아니다. `코드 확인`
2. **재시도와 compaction은 루프 밖에서 한다.** agent-loop는 `error`가 나면 바로 끝난다(Q5). 그러면 `AgentSession._runAgentPrompt`가 결과를 보고 `agent.continue()`로 다시 돌린다. `코드 확인`

## hook별로 넣는 것

| hook | 설치 위치 | 하는 일 |
|---|---|---|
| `streamFn` | `sdk.ts:398` | `modelRuntime.streamSimple` 호출. 세션 요청일 때만 prompt cache warmer를 시작한다 |
| `convertToLlm` | `sdk.ts:275` | `messages.ts`의 `convertToLlm`에 이미지 차단 설정(`blockImages`)을 덧씌운다. 설정을 호출할 때마다 읽으므로 세션 중간에 바꿔도 반영된다 |
| `transformContext` | `sdk.ts:414` + `agent-session.ts:1685, 1705` | ① extension의 `context` 이벤트(`emitContext`) ② `prepareLoadout`으로 숨긴 tool 선언 제거 ③ `forceSystemPrompt`로 system prompt 강제 교체. 이 순서대로 체인된다 |
| `prepareRequest` | `agent-session.ts:748` | **세션 projection으로 context를 교체**한다. 가상 모델(virtual model)이면 `resolveModel`로 실제 모델을 고르고(`reason: retry/user/continuation`), 그 모델 기준으로 compaction 임계치를 넘으면 compaction 후 다시 준비한다 |
| `prepareNextTurn` | `agent-session.ts:863` | 다음 turn 전에 임계치 compaction(`_compactBeforeNextAssistantResponse`)을 하고, system prompt와 tool 목록을 다시 만든다(`_preparePromptAndToolLoadout`) |
| `beforeToolCall` | `agent-session.ts:612, 617` | extension의 `tool_call` 이벤트로 전달한다. extension이 `block`을 반환하면 실행하지 않는다. extension이 throw하면 루프의 `prepareToolCall`이 잡아서 에러 결과로 바꾼다(Q5) |
| `afterToolCall` | `agent-session.ts:643` | extension의 `tool_result` 이벤트로 결과를 수정한다. 그다음 결과 이미지를 모델 한도에 맞게 줄인다(`normalizeToolResultImages`) |
| `finishTurn` | `agent-session.ts:847` | extension의 `turn_end` boundary를 실행한다. extension이 continue를 요청하면 `{ action: "continue" }`를 반환한다 |
| 중첩 tool 호출 | `agent-session.ts:697-720` | tool이 `ctx.executeTool()`로 다른 tool을 부르면 `runToolCall`(Q5)로 실행한다. 같은 before/after hook을 `parentToolCallId`와 함께 거친다 |

`getSteeringMessages`/`getFollowUpMessages`는 `Agent`의 큐를 그대로 쓴다(Q6). `AgentSession`은 UI 표시용 텍스트 목록(`_steeringMessages`)을 따로 들고 있다가, 해당 user 메시지의 `message_start`가 오면 목록에서 지운다(:1072-1089).

## 이벤트 처리: 세션 저장 (`_handleAgentEvent`, :1061)

`agent.subscribe(this._handleAgentEvent)`(:472)로 등록한다. 이벤트마다 다음 순서로 처리한다.

1. **extension 먼저**: `_emitExtensionEvent(event)`
2. **공개 구독자**: `_emit(event)`로 TUI 등에 전달한다. `agent_end`에는 `willRetry` 필드를 붙여서, UI가 "끝났다"와 "곧 재시도한다"를 구분할 수 있게 한다.
3. **`message_end`면 세션 파일에 저장**: 일반 메시지는 `appendMessage`, custom 메시지는 `appendCustomMessageEntry`로 저장한다.
4. **assistant 응답이 성공하면 재시도 횟수를 초기화한다.**

Q6에서 본 대로 `Agent`는 구독자를 하나씩 await한다. 그래서 루프는 세션 저장이 끝난 뒤에야 다음으로 진행한다. `코드 확인` (그래서 저장이 빠져도 루프가 앞서 나가지 않는다는 해석은 `추론`)

## run 이후 루프: 재시도와 compaction (`_runAgentPrompt`, :1736)

```
agent.prompt(messages)
while (중단 요청 없음)
  if _handlePostAgentRun():   ← 다시 돌릴 이유가 있나
      agent.continue(); continue
  if !_runBeforeSettleBoundary(): break   ← extension이 settle 직전에 이어 가게 할 수 있음
  agent.continue()
finally: _emitAgentSettled()
```

`_handlePostAgentRun`(:1764)은 마지막 assistant 메시지를 보고 다음 중 하나로 판단한다.

| 경우 | 조건 | 처리 |
|---|---|---|
| **일시적 오류 재시도** | `_isRetryableError`: context overflow가 **아니고** `isRetryableAssistantError`(pi-ai)가 true | `_prepareRetry`(:3660): 기본 최대 3회, 2s·4s·8s 지수 backoff(`retryDelayMs`). `auto_retry_start`를 emit하고, 실패한 시도는 모델에게 보내는 projection에서 뺀다(`_omitRecoveryAttempt`). 대기는 중단할 수 있다(`abortRetry`) |
| **재시도 소진** | error이고 `_retryAttempt > 0` | `auto_retry_end { success: false }`를 보낸 뒤, 종료하지 않고 아래 compaction 판정으로 넘어간다(:1784-1796) |
| **context overflow / 잘린 응답** | `_checkCompaction`(:2862): 같은 모델에서 `isContextOverflow` 또는 `isRecoverableLength` | `_runAutoCompaction("overflow", willRetry)`: 대화를 요약해 줄이고 한 번만 다시 시도한다. 두 번째에도 실패하면 "Context overflow recovery failed after one compact-and-retry attempt" |
| **임계치 compaction** | 응답은 성공했지만 context가 임계치를 넘음 | compaction만 하고 재시도는 하지 않는다 |
| **대기 메시지** | `agent.hasQueuedMessages()` | `continue()`로 이어 간다 |

- **overflow는 재시도 대상이 아니다.** 같은 요청을 다시 보내도 또 넘치기 때문이다. 대신 compaction으로 처리한다(:3606 주석).
- 재시도가 예약되면 `_failedResponse`가 설정되고, 다음 `prepareRequest`가 이를 `resolveModel(reason: "retry", failed)`에 넘긴다. 가상 모델이면 실패한 모델과 다른 모델로 route할 수 있다. `코드 확인` (실제 route 정책은 `미확인`)
- compaction 앞에서 extension이 `session_before_compact`로 취소하거나 자기 요약을 넣을 수 있다(:3043-3065).

## 층 사이의 책임 분담

| 관심사 | pi-ai | agent-core | coding-agent |
|---|---|---|---|
| 재시도 | "재시도할 만한가" 판정 함수 | `error`면 즉시 종료, `continue()` 제공 | 횟수, backoff, 모델 re-route |
| context 한도 | `isContextOverflow` 판정 | 모름 | compaction(요약) 후 1회 재시도 |
| tool 권한 | 모름 | `beforeToolCall` 자리 | extension `tool_call`로 전달 |
| 대화 저장 | 모름 | 이벤트 emit | `message_end` → 세션 파일, projection이 원본 |

## 남은 질문

- `sessionManager.buildSessionProjection()`: 세션 파일(entry 트리)에서 모델에게 보낼 메시지를 어떻게 만드나 (context_edit, compaction entry 반영)
- `_runDefaultCompaction`: 요약 prompt와 어떤 메시지를 남길지(`firstKeptEntryId`) 정하는 기준
- `modelRuntime.resolveModel`: 가상 모델의 route 정책
