# agent 05: `agent.prompt("...")` 한 번의 경로 (종합 + 실행 확인)

- **기준 commit**: `28dcce2ba` (`packages/agent/src`는 `3874b3e98`과 동일) / **분석일**: 2026-10-06
- **선행 문서**: [02-agent-loop](./02-agent-loop.md), [03-agent-class](./03-agent-class.md), [04-proxy](./04-proxy.md), [ai/06-call-flow](../ai/06-call-flow.md)
- **실행 환경**: Node v26.5.0, `typebox@1.3.27`, `partial-json@0.1.7`을 **`artifacts/pi/agent-demos/`에만** 설치(`--ignore-scripts`, 사용자 허락). `repos/pi`는 변경하지 않았다.
- **검증 수준**: 아래 표의 "실행 확인"은 실제 `agent.ts`, `agent-loop.ts`, `proxy.ts` 소스를 그대로 불러 가짜 `streamFn`/로컬 HTTP 서버로 돌린 결과다. **가짜 `streamFn`이므로 실제 LLM, 실제 provider 변환(ai)은 포함하지 않는다.**

## 1. 실험을 어떻게 했나 (한계 포함)
- `@earendil-works/pi-ai`는 openai 등 SDK 의존성이 많아 전체를 쓰지 않고, **`pi-ai-shim.ts`가 agent가 쓰는 함수만 실제 소스 파일에서 re-export**한다(`EventStream`, `transcript.ts`의 함수들, `validateToolArguments`, `parseStreamingJson`). 연결은 Node의 resolve 훅(`loader.mjs`, `register.mjs`)이 한다. 따라서 **agent 쪽 코드와 이 ai 함수들은 실제 것**이고, `streamFn`만 가짜다.
- 파일: `artifacts/pi/agent-demos/` (`agent-flow-demo.ts`, `proxy-demo.ts`, `lib.ts`, 출력 `*.2026-10-06.out`). 실행: `node --no-warnings --import ./register.mjs <demo>.ts`.
- 한계: 가짜 `streamFn`은 `signal`을 무시한다(아래 F에서 영향). `module.register()`는 Node 26에서 deprecated 경고가 나온다(동작에는 영향 없음).

## 2. 한 번의 `agent.prompt("hi")` 경로
도구 하나(`read`)를 부르고 답하는 경우. `[ ]`는 실제로 출력된 순서.
```
agent.prompt("hi")                              agent.ts:373
 └ normalizePromptInput → [user 메시지]           :413
 └ runWithLifecycle  (activeRun 잠금, isStreaming=true)    :507
    └ runAgentLoop(messages, 스냅샷 context, config, processEvents, signal, streamFn)   agent-loop.ts:102
       emit agent_start, turn_start, message_start/end(user)
       runLoop                                                 :163
         [1턴]
         prepareRequest                                        :219
         streamAssistantResponse                               :381
           transformContext → convertToLlm → normalizeContext → getApiKey → streamFn(...)
           ← message_start / message_update* / message_end (assistant, stopReason=toolUse)
         executeToolCalls → beforeToolCall → execute → afterToolCall
           tool_execution_start/end, message_start/end(toolResult)
         finishTurn → turn_end
         steering 확인 (없음)
         [2턴]
         prepareNextTurn → turn_start
         prepareRequest → transformContext → convertToLlm → getApiKey → streamFn(...)
         ← assistant(stopReason=stop)
         finishTurn → turn_end
         steering 없음, follow-up 없음 → 종료
       emit agent_end
 └ finally finishRun  (isStreaming=false, activeRun 해제)
 이벤트마다 processEvents: 상태 갱신 → 구독자 순차 await
```

### 실행 확인 (A, `agent-flow-demo.2026-10-06.out`)
- **훅 순서**: `prepareRequest > transformContext > convertToLlm > getApiKey(fake) > beforeToolCall > execute > afterToolCall > finishTurn > prepareNextTurn > prepareRequest > transformContext > convertToLlm > getApiKey(fake) > finishTurn`
  - 02 §5(`prepareNextTurn`은 2턴째부터, `prepareRequest`가 `transformContext` 앞) 및 §6(transform → convert → apiKey)과 **일치**.
- **이벤트**: `agent_start | turn_start | message_start(user) | message_end(user) | message_start(assistant) | message_end(assistant) | tool_execution_start(read) | tool_execution_end(read) | message_start(toolResult:read) | message_end(toolResult:read) | turn_end(stop=toolUse, results=1) | turn_start | message_start(assistant) | message_end(assistant) | turn_end(stop=stop, results=0) | agent_end(messages=4)`.
- **`streamFn`이 받은 context**: 1번째 `['system','user']`, 2번째 `['system','user','assistant','toolResult']`. 첫 `system`은 `Agent` 생성자가 `systemPrompt`와 도구 선언으로 만든 것(03 §4). 즉 **도구와 시스템 프롬프트는 context 필드가 아니라 맨 앞 system 메시지로 간다**.
- **옵션**: `apiKey = "KEY-fake"`(`getApiKey`의 결과, 02 §6 #4), 그리고 **`beforeToolCall` 같은 훅 함수가 `streamFn`의 옵션에도 그대로 실려 온다**(`typeof` = `function`, 02 §6 #5의 "`AgentLoopConfig` 전체를 펼침"을 확인).
- **최종 상태**: `state.messages = [system, user, assistant, toolResult, assistant]`, `isStreaming=false`.
- `agent_end.messages`는 4개: 이 run에서 **새로 생긴 것만**(user, assistant, toolResult, assistant). `system`은 제외 (02 §3).

## 3. 02~04의 주장별 실행 결과
| # | 주장 (문서) | 실험 | 결과 |
|---|---|---|---|
| 1 | 병렬: start는 소스 순, end는 완료 순, toolResult는 소스 순 (02 §7.2) | B parallel (A 60ms, B, C) | start A,B,C → end **B,C,A** → toolResult **A,B,C**. **일치** |
| 2 | 순차는 도구마다 start → end → toolResult (02 §7.2) | B sequential | A(start,end,result) → B → C. **일치** |
| 3 | 도구 하나가 `executionMode: "sequential"`이면 배치 전체 순차 (02 §7.1) | B2 | A end 뒤에 B start. **일치** |
| 4 | 모든 도구가 `terminate`이면 다음 요청 없음 (02 §5.1) | C1 | requests=1. **일치** |
| 5 | 하나라도 아니면 계속 (02 §5.1) | C2 | requests=2. **일치** |
| 6 | `finishTurn: continue`가 단독이면 한 턴 추가 (02 §5.1 #6) | C3 | requests=2. **일치** |
| 7 | 도구 호출로 이미 계속되면 추가 요청 없음 (02 §5.1) | C4 | requests=2 (도구 턴 + 답), 중복 없음. **일치** |
| 8 | `finishTurn: end`는 follow-up 큐를 무시하고 종료 (02 §5.1 #2) | C5 | requests=1, 큐에 **follow-up이 남음**. **일치** |
| 9 | `error`는 `finishTurn`의 `continue`도 이김, 호출은 하되 반환값 버림 (02 §5.1 #1) | C6 | requests=1, `finishTurn` 호출 1, `state.errorMessage="boom"`. **일치** |
| 10 | `length`이면 도구를 실행하지 않고 에러 결과 (02 §7.4) | C7 | execute 0회, `isError=true`, 문구 확인, requests=2(AI가 재시도). **일치** |
| 11 | steering: one-at-a-time은 턴마다 하나, all은 한 번에 (03 §9) | D | 아래 §3.1 |
| 12 | 훅 throw → `handleRunFailure`가 이벤트 순서를 맞춤 (03 §7) | E (`convertToLlm` throw) | 아래 §3.2 |
| 13 | 순차 도구 중 중단 시 `toolResult` 누락 (02 §7.5) | F | **확인**: toolCall 2, toolResult **1** |
| 14 | run 도중 `state.model` 변경은 현재 run에 안 먹는다 (03 §10) | G | 한 run: `fake -> fake`, 다음 run: `changed`. **일치** |
| 15 | `agentLoop`(스트림 반환판)는 reject를 처리하지 않는다 (04 §9) | H1 | 스트림이 **300ms 후에도 안 끝남** + `unhandledRejection`. **확인** |

### 3.1 D: steering (실행에서 새로 알게 된 것)
`prompt` 전에 `steer(s1)`, `steer(s2)`를 넣은 경우(도구 호출 1회 + 답 1회).
| 모드 | 요청 1 | 요청 2 |
|---|---|---|
| `one-at-a-time` | `system,user,user` (**prompt + s1**) | `system,user,user,assistant,toolResult,user` (s2) |
| `all` | `system,user,user,user` (prompt + s1 + s2) | `system,user,user,user,assistant,toolResult` |
- **실행 전 예상과 다른 점**: steering은 "턴이 끝난 뒤"에만 들어가는 것이 아니라, **`runLoop` 시작 시점에도 한 번 `drain`**(`agent-loop.ts:176`)되어 **첫 요청에 prompt와 함께** 간다. 즉 큐에 미리 쌓아 둔 steering이 첫 AI 요청부터 보인다(이미 02 §4 흐름에는 있었으나 효과를 실행으로 확인). 의도(주석 `:175`: "사용자가 기다리는 동안 입력한 것")와 일치.
- `one-at-a-time`이면 나머지는 그 다음 턴 끝에서 들어간다.

### 3.2 E: 훅 throw
- 이벤트: `agent_start | turn_start | message_start(user) | message_end(user) | message_start(assistant) | message_end(assistant) | turn_end(stop=error, results=0) | agent_end(messages=1)`.
- 마지막 메시지: `assistant`, `stopReason=error`, `errorMessage="convert failed"`, `isStreaming=false`.
- 즉 `turn_start`와 user 메시지까지는 정상으로 나가고, 실패 후 **`handleRunFailure`가 `message_start/end → turn_end → agent_end`를 대신 낸다**. `agent_end.messages`는 **1개(실패 메시지)뿐**. 03 §7 주의 1과 **일치**: user 메시지는 `agent_end.messages`에 안 들어간다. (구독자가 `message_end`로 모았다면 user 메시지는 받았다.)

### 3.3 F: 중단 시 `toolResult` 누락 (새 확인)
- 설정: 순차 실행, 도구 A가 실행 중 `agent.abort()`를 호출, 도구 B는 남음.
- 결과: 대화 기록 `system,user,assistant,toolResult,assistant`. **assistant의 `toolCall`은 2개인데 `toolResult`는 1개**(A의 것). B에는 결과가 없다.
- 그 뒤 **AI에게 두 번째 요청이 나갔다**(마지막 `assistant`): 02 §5에서 `hasMoreToolCalls = !terminate`라 계속하기 때문. 이 마지막 `assistant`는 **가짜 `streamFn`이 `signal`을 무시해서** 생긴 것이다. 실제 provider라면 이미 `aborted`된 signal로 요청해 `stopReason: "aborted"`가 와 종료된다고 `추론`한다(실행 확인 안 함).
- 위험: **짝이 안 맞는 기록**(B의 toolCall에 결과 없음)이 그대로 다음 요청으로 간다. 일부 provider는 거부하므로, ai의 변환 단계(`transformMessages` 등)가 빈 결과를 채우는지는 ai 문서 확인 필요(`미확인`). `Agent`가 메우지 않음은 이 실험에서 확인.

## 4. 프록시 실험 (`proxy-demo.2026-10-06.out`)
로컬 `http://127.0.0.1:<port>/api/stream`에 SSE 서버를 띄워 `streamProxy`를 호출했다 (외부 접속 없음).
| 시나리오 | 결과 |
|---|---|
| 정상 | 이벤트 `start,text_start,text_delta×2,text_end,toolcall_start,toolcall_delta×2,toolcall_end,done`. **마지막 `done` 줄은 개행 없이** 보냈는데도 처리됨(04 §6.1). 방출된 `partial` **객체는 1개**(같은 참조, 04 §6.2). 최종 `content`: `"Hello"` + `read` toolCall, `arguments={"path":"a.txt"}` |
| 부분 인자 복원 | `toolcall_delta` 마다 `{"path":"a."}` → `{"path":"a.txt"}` (`parseStreamingJson`, 서버는 `arguments`를 안 보냄) |
| 요청 | `POST /api/stream`, `Authorization: Bearer TOKEN`, body 키 `model, context, options`. 옵션에 일부러 넣은 `apiKey`, `onPayload`, `beforeToolCall`은 **body에 없음**(`SECRET` 문자열 포함 여부 `false`). 보낸 옵션 키는 `reasoning`, `metadata`뿐 (`undefined`는 JSON에서 사라짐) |
| 터미널 이벤트 없이 EOF | `start,text_start,text_delta,error`, `stopReason=error`, `"Connection closed by proxy server before the response completed"`, 받은 내용(`"partial answer"`)은 남음 |
| HTTP 500 + `{error}` | 이벤트 `error` 하나, `"Proxy error: upstream down"` |
| `toolcall_end` 없이 끊김 | `stopReason=error`, **`content`에 `partialJson` 필드가 남음**: `{"type":"toolCall",...,"arguments":{"path":"b"},"partialJson":"{\"path\": \"b"}` (04 §6.2 `추론`을 **확인**) |
| 중단 (150ms 후 abort) | `start,text_start,text_delta,error`, `stopReason=aborted`, `"Request aborted by user"` |
→ 04의 모든 주장 일치. **새로 확인**: 끊긴 도구 호출의 `partialJson`이 최종 메시지에 남는다.

## 5. 이번 시리즈로 알게 된 것 (agent 전체)
1. **계층**: `Agent`(상태/큐/구독/잠금) → `runAgentLoop`(순수 루프, 훅으로 정책 주입) → `StreamFn`(ai 또는 `streamProxy`). 객체는 공유하지 않고 **스냅샷 입력 + 이벤트 출력**으로만 연결.
2. **throw 정책**: 도구 관련은 루프가 흡수, 그 밖의 훅은 호출자 책임이며 `Agent`가 최후 안전망(`handleRunFailure`).
3. **"끝낼지 계속할지" 7단계 우선순위**와 `terminate`는 "도구 전부"일 때만.
4. **병렬 도구**: 준비(검증, `beforeToolCall`)는 순차, 실행만 동시, 완료 이벤트는 완료 순, 결과 메시지는 호출 순.
5. **알려진 구멍(코드 확인 + 실행 확인)**: ① 중단 시 `toolResult` 짝 불일치(F) ② 끊긴 프록시 도구 호출의 `partialJson` 잔존 ③ `agentLoop`(스트림판)는 루프 reject 시 끝나지 않음(H1) ④ 실패 run의 `agent_end.messages`가 `[failure]` 하나뿐(E) ⑤ context 교체 훅은 `state.messages`에 반영 안 됨(`추론`, 실행 안 함).
6. **도구 정보는 system 메시지 델타로 대화 기록에 실린다** (이전 분석 Q5~Q8에는 요약만 있음).

## 6. `미확인`
- 실제 provider에서 `aborted` signal로 요청했을 때의 동작(F의 마지막 `assistant`)
- ai 변환 단계가 짝 없는 toolCall을 처리하는지
- context 교체 훅(`prepareNextTurn`/`prepareRequest`)과 `state.messages`의 관계 (coding-agent의 압축에서 확인)
- 느린 구독자일 때 스트림 버퍼 (실험 안 함)
- 실행 시간/성능 측정 없음

## 7. 다음
`coding-agent` 단계: `core/sdk.ts` → `core/agent-session.ts`(재시도, 압축, `runToolCall` 사용) → `session-manager.ts`. 위 §5의 알려진 구멍이 coding-agent에서 어떻게 메워지는지(중단 시 toolResult, 압축 후 `state.messages`, 구독자의 저장 방식)를 우선 확인한다.
