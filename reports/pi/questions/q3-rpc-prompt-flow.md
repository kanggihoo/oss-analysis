# Q3: RPC `prompt` 명령 하나는 어떤 경로로 처리되어 이벤트로 돌아오나? RPC는 다른 패키지를 묶은 패키지인가?

- **Commit**: `4259686d9290c0d73ae7192b796aee3e530a9779` · **작성일**: 2026-09-29
- **그림**: [① 접수와 LLM 호출](../diagrams/rpc-prompt-1-preflight.html) · [② tool 호출과 이벤트 반환](../diagrams/rpc-prompt-2-tool.html)

## 결론

- **RPC는 패키지가 아니다.** `pi-coding-agent` 안의 실행 모드 하나다(`src/modes/rpc/`, 4개 파일, 약 1.8k줄). `AgentSession`을 stdin/stdout JSONL로 노출하는 **얇은 입출력 adapter**다. (코드 확인)
- 패키지들을 실제로 묶는 곳은 **`AgentSession` + `sdk.ts createAgentSession()`**이다. 여기서 `new Agent(...)`(agent-core)를 만들고, `streamFn`으로 `modelRuntime.streamSimple`(pi-ai)을 연결하고, tools·extensions·resources를 붙인다. Interactive·Print·RPC 세 모드는 모두 이 결과물을 공유한다. (코드 확인)
- 별도 패키지 `pi-protocol`/`pi-client`/`pi-server`는 **이 RPC와 다른 것**이다. CBOR 기반 실험적 원격 세션이며 `experimental/`에서만 쓰인다. (코드 확인)

## 호출 경로 (코드 확인)

| # | 단계 | 위치 |
|---|---|---|
| 1 | stdin에서 JSONL 한 줄 읽기 | `modes/rpc/rpc-mode.ts:808` `attachJsonlLineReader` |
| 2 | `case "prompt"` → `session.prompt(message, { source: "rpc", preflightResult })`. **await하지 않고** 바로 반환 | `rpc-mode.ts:394-413` |
| 3 | preflight 순서: `/`로 시작하면 extension command 처리 → `input` hook → skill·template 펼치기 → 실행 중이면 steer/followUp queue | `core/agent-session.ts:1879-1935` |
| 4 | `before_agent_start` hook (prompt·systemPrompt 변경 가능) | `agent-session.ts:1973` |
| 5 | `preflightResult("started")` → RPC `response success` 출력. **모델 작업 완료를 뜻하지 않는다** | `agent-session.ts:2020`, `rpc-mode.ts:405` |
| 6 | `_runAgentPrompt` → `this.agent.prompt(messages)` | `agent-session.ts:1736-1743` |
| 7 | `runLoop`: `turn_start` → `streamAssistantResponse` → `streamFn` = `modelRuntime.streamSimple()` | `agent/src/agent-loop.ts:163~`, `core/sdk.ts:398-408` |
| 8 | toolCall이 있으면 `executeToolCalls` (sequential/parallel) | `agent-loop.ts:270, 508-522` |
| 9 | **`tool_execution_start`를 먼저 emit** → `prepareToolCall` → `beforeToolCall` | `agent-loop.ts:543, 707-760` |
| 10 | `beforeToolCall` = `AgentSession._beforeToolCall` → `ExtensionRunner.emitToolCall` (`tool_call` hook) | `agent-session.ts:612, 617-627`, `extensions/runner.ts:1233` |
| 11 | `block: true`면 도구를 실행하지 않고 error 결과(`reason`)로 대체. 이 결과가 모델에게 전달됨 | `agent-loop.ts:745-755` |
| 12 | 허용이면 `execute` → `afterToolCall`(`tool_result` hook) → `tool_execution_end` emit | `agent-loop.ts:820-935`, `agent-session.ts:643-649` |
| 13 | tool result를 context에 넣고 LLM 재호출. toolCall 없는 답변이면 `turn_end` → `agent_end` | `agent-loop.ts` runLoop |
| 14 | 모든 agent 이벤트: `agent.subscribe(_handleAgentEvent)` → extension 이벤트 → `_emit` → `session.subscribe` listener → `toJsonEvent` → stdout. 이어서 `message_end`는 `SessionManager.appendMessage`로 JSONL 저장 | `agent-session.ts:472, 1061-1116`, `rpc-mode.ts:355-357` |
| 15 | retry·compaction·queue가 없으면 `agent_settled` (extension에 먼저 보낸 뒤 listener에 전달) | `agent-session.ts:1037-1043` |

## HarnessLens 설계에 주는 의미

1. **"완료" 판단은 `response`가 아니라 `agent_settled`로 한다.**
2. **차단된 호출도 trace에 남는다.** `tool_execution_start` → `tool_execution_end(isError: true)`가 그대로 나간다. 다만 start 시점에는 허용 여부를 모른다. 차단 여부는 end의 isError·결과 text로 판별하거나, extension이 별도 표식을 남겨야 한다. (코드 확인 / 판별 방법은 추론)
3. **Policy extension의 `tool_call` handler는 인자 검증 뒤에 실행된다**(`validateToolArguments` 이후). 따라서 검증된 args(path 등) 기준으로 판단할 수 있다. (코드 확인)

## 그림에서 생략
- `message_start/update/end`, `turn_start/end` 이벤트
- `afterToolCall` → `tool_result` hook의 결과 수정
- parallel 실행 경로, steer·follow_up queue, auto-retry·compaction

## 남은 질문
- 실제 `pi --mode rpc`에서 차단된 호출의 `tool_execution_end` payload 형태 (실행 확인 필요)
