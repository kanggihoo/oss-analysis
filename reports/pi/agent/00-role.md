# agent 00: pi에서 `agent` 패키지(`pi-agent-core`)의 역할

- **기준 commit**: `3874b3e98` (2026-10-02, worktree clean) / **분석일**: 2026-10-06
- **대상**: `repos/pi/packages/agent` (`@earendil-works/pi-agent-core` v1.0.0)
- **선행 문서**: [ai/00-role](../ai/00-role.md)(ai 패키지의 역할), [ai/06-call-flow](../ai/06-call-flow.md)(호출 경로 종합, 특히 ⑦ `agent-loop.ts:414`)
- **읽은 파일**: `src/types.ts`(529줄 전체), `src/stream-fn.ts`(20줄), `src/index.ts`(5줄), `package.json`, `README.md`(앞 80줄), `CHANGELOG.md`(앞 40줄), `src/agent.ts`와 `src/agent-loop.ts`는 **공개 선언(export, 클래스 필드, 메서드 이름)과 일부만**(`agent-loop.ts:385-455`는 ai 06에서), `src/proxy.ts`는 앞 35줄, `coding-agent/src/core/sdk.ts`(`:380-420`). 사용처는 `grep`으로 확인했다. 줄 번호는 모두 이 commit 기준이다.
- **검증 수준**: 선언, 의존, 사용처는 `코드 확인`. **루프와 `Agent` 클래스의 내부 동작은 아직 읽지 않았다**(`미확인`, 다음 문서에서). 실행한 것은 없다.

## 0. 이 문서의 질문
- `agent` 패키지는 무엇을 하고, 무엇을 하지 않는가? (ai 패키지 위, coding-agent 아래)
- 이 commit에서 무엇이 남았고, 누가 이 패키지를 쓰는가?
- 이전 분석(Q5, Q6, `4259686d9` 기준)이 바뀐 코드와 얼마나 어긋나는가?

## 1. 한 줄 답
**`agent`는 "AI를 부르고 → 도구 호출이 오면 실행하고 → 결과를 붙여 다시 부르는" 반복(agent loop)을 대신 해 주는 층이다.** ai 패키지는 한 번 부르면 답 한 번(+도구 호출 요청)만 주는데, 그 도구 호출을 실제로 실행하고 이어서 다시 부르는 일은 ai가 하지 않았다(ai/00-role §4). 그 일이 여기 있다. 회사별 차이도, 대화 저장도, 재시도도, 화면도 모른다.

```
coding-agent  (제품: 세션 파일, 도구 구현, 압축, 재시도, 화면)
     │ 사용 (new Agent, setDefaultStreamFn, runToolCall)
     ▼
agent         (반복: 부르기 → 도구 실행 → 결과 붙여 다시 부르기. 상태, 이벤트, 큐)   ← 여기
     │ streamFn 으로 호출 (기본은 주입받음)
     ▼
ai            (회사별 차이를 숨기고 이벤트 스트림으로 답한다)
```

## 2. 이 commit에서 남은 것

### 2.1 파일 구성 (`packages/agent`)
| 파일 | 줄 | 한 줄 역할 | 이 문서에서 읽은 정도 |
|---|---|---|---|
| `src/agent-loop.ts` | 940 | 반복 자체: `agentLoop`, `agentLoopContinue`, `runAgentLoop`, `runAgentLoopContinue`, `runToolCall` | 공개 선언만 (`:32`, `:38`, `:71`, `:102`, `:128`, `:683`, `:790`, `:810`) |
| `src/agent.ts` | 613 | 상태, 구독자, 큐를 가진 `Agent` 클래스(루프를 감싸서 쓰기 편하게) | 공개 필드와 메서드 이름 |
| `src/types.ts` | 529 | `AgentMessage`, `AgentTool`, `AgentEvent`, `AgentLoopConfig` 등 타입 | **전체** |
| `src/proxy.ts` | 406 | `streamProxy`: LLM 호출을 서버로 중계하는 스트림 함수 | 앞 35줄 |
| `src/stream-fn.ts` | 20 | `setDefaultStreamFn` / `getDefaultStreamFn` | **전체** |
| `src/index.ts` | 5 | 공개 API 목록 | **전체** |
| `test/` | 4개 파일 (`agent-loop.test.ts` 2193줄, `agent.test.ts` 1216줄, `e2e.test.ts` 416줄, `proxy.test.ts` 118줄) | | 줄 수만 |
| `examples/mcp-codemode` | | 예제 | 이름만 |

소스는 6개 파일 약 2500줄이다(`src/*.ts` 합 2513줄). 테스트가 소스보다 많다(약 3900줄).

### 2.2 공개 API (`src/index.ts`, 전체 5줄)
```ts
export * from "./agent.ts";            // Agent, AgentOptions, AgentInitialState, QueueMode
export * from "./agent-loop.ts";       // agentLoop, agentLoopContinue, runAgentLoop, runAgentLoopContinue, runToolCall, ToolCallHooks, RunToolCallOptions, AgentEventSink
export * from "./proxy.ts";            // streamProxy, ProxyAssistantMessageEvent, ProxyStreamOptions
export { setDefaultStreamFn } from "./stream-fn.ts";     // getDefaultStreamFn 은 내보내지 않는다
export * from "./types.ts";            // 타입들
```
- `package.json`의 `exports`는 루트(`.`)와 `./package.json`뿐이다. 하위 경로 import는 없다.
- 의존성은 `@earendil-works/pi-ai`와 `typebox`(도구 스키마 타입) 둘뿐이다(`package.json`).

### 2.3 예전에는 훨씬 컸다: harness 삭제 (`코드 확인`, `CHANGELOG.md`)
`CHANGELOG.md [1.0.0] - 2026-10-01`: "Removed the experimental harness from `@earendil-works/pi-agent-core`: `AgentHarness`, sessions and session storage, the durable runtime, pico3, harness tools, compaction, skills, prompt templates, system prompt helpers, telemetry schemas, the search service types, and the `uuidv7` and pi-telemetry re-exports. ... The package now contains only `Agent`, the agent loop, the proxy stream, and their types. Use `@earendil-works/pi-durable` for durable sessions."
- 이전 SHA(`4259686d9`)에서 이 패키지는 약 3만 줄 더 많았다(`git diff --stat`: 112개 파일, 3.1만 줄 삭제, ai/00-role §7).
- 그 결과 **세션, 압축, 스킬, 프롬프트 템플릿, 텔레메트리 스키마는 이 패키지에 없다.** 세션과 압축은 `coding-agent`, 내구성 세션은 `pi-durable`이 맡는다.
- 이전 분석의 "agent-core의 `harness/...`가 재시도와 압축을 한다"는 서술은 이 commit에서 성립하지 않는다(ai/05 §2.3).

그 밖의 최근 변경: `0.87.0`에서 `shouldStopAfterTurn`이 `finishTurn`으로 바뀌었다(예제는 `CHANGELOG.md`). `0.99.0`에서 `onProviderStreamEvent` 옵션과 `AssistantMessage.thinkingLevel` 기록이 추가되었다.

## 3. 의존 관계

### 3.1 `agent`가 의존하는 것 (`코드 확인`)
| 대상 | 어디서 | 쓰는 것 |
|---|---|---|
| `@earendil-works/pi-ai` | `agent.ts`, `agent-loop.ts`, `types.ts`, `proxy.ts` (모두 **루트 import 4곳**, 하위 경로 없음) | 타입(`Message`, `Model`, `AssistantMessage`, `AssistantMessageEventStream`, `SimpleStreamOptions` 등), `normalizeContext`(`agent-loop.ts:397`), `validateToolArguments`(`:726`), 그리고 `proxy.ts`는 **`EventStream`과 `parseStreamingJson`을 직접 import**해서 ai 03-0의 스트림 클래스를 자기 스트림(`ProxyMessageEventStream`)의 부모로 쓴다(`proxy.ts:7-14`, `:17-28`) |
| `typebox` | `types.ts` | `Static`, `TSchema`(도구 매개변수 스키마 타입) |
- **provider 목록, 인증, 카탈로그를 전혀 모른다.** `types.ts:20`의 `StreamFn` 주석: "`Models.streamSimple`이 이 모양을 만족한다." 호출은 주입받은 `streamFn`으로만 한다.

### 3.2 `agent`를 쓰는 곳 (`코드 확인`)
이 commit에서 **`package.json`에 의존으로 선언한 패키지는 `coding-agent` 하나뿐**이다(`grep`). 실제 코드 import도 `coding-agent`에만 있다.
| | `src` | `test` | 내용 |
|---|---|---|---|
| `coding-agent` | 44회(파일 38개) | 47회 | 전부 루트 import |
| 그 외 | 0 | 0 | |

`coding-agent`가 가져가는 것 (`src` 기준 상위):
`AgentTool` 16, `ThinkingLevel` 16, `AgentMessage` 14, `AgentToolResult` 5, `AgentToolCallOutcome` 4, `StreamFn` 3, `Agent` **2**, `AgentState` 2, `setDefaultStreamFn` 1, `runToolCall` 1 등. 즉 **대부분은 타입**이고, `Agent` 클래스를 실제로 만드는 곳은 두 곳, 함수 `runToolCall`은 한 곳이다.

이전에는 `server`, `session-backends`, `chord` 등도 이 패키지를 썼으나 지금은 아니다. 다른 패키지의 언급은 아래와 같고 모두 실행 코드의 import가 아니다.
| 위치 | 내용 |
|---|---|
| `client/tsconfig.test.json:9`, `server/vitest.config.ts:19-20` | 테스트용 경로 별칭 |
| `server/CHANGELOG.md:9` | "the package no longer depends on `@earendil-works/pi-agent-core`" |
| `codemode/README.md`, `mcp/README.md` | 도구를 `AgentTool`로 감싸는 사용 예시(타입 import) |
| **`telemetry/README.md:326`, `:371`, `:380`** | `AGENT_TELEMETRY_SCHEMAS`를 `pi-agent-core`에서 가져온다고 적혀 있다. 위 CHANGELOG에 따르면 텔레메트리 스키마는 이 패키지에서 **삭제**되었으므로 이 README는 **낡았다.**(`추론`: 실제 export 여부는 `index.ts`에서 확인, 위 2.2에 없음) |

### 3.3 ai 패키지와 맞닿는 곳: `StreamFn` 계약 (`types.ts:19-37`)
```ts
type StreamFn = (model, context: TranscriptContext, options?: SimpleStreamOptions)
    => AssistantMessageEventStream | Promise<AssistantMessageEventStream>;
// 계약: 요청/모델/실행 실패로 throw하거나 reject하지 않는다. 실패는 스트림의 이벤트와
//       stopReason "error" | "aborted" 인 최종 AssistantMessage 로 표현한다.
```
- ai/06 §5에서 본 "실패도 값으로 전달한다"와 같은 계약이다. agent는 그 계약을 **믿고** 쓴다.
- 입력은 **정규화된 `TranscriptContext`**다. 주석: 시스템 프롬프트와 도구 선언은 `context.systemPrompt`/`context.tools`가 아니라 transcript의 시스템 메시지가 가진다. agent 루프도 `normalizeContext`를 직접 부른다(`agent-loop.ts:397`).

## 4. `agent`가 하는 일, 하지 않는 일

### 4.1 하는 일 (`types.ts`에서 확인, 동작은 다음 문서)
| 기능 | 근거(선언) | 쉬운 설명 |
|---|---|---|
| **AI 호출 → 도구 실행 → 다시 호출 반복** | `agentLoop`, `AgentLoopConfig` | 이 패키지의 핵심 |
| **앱 고유 메시지 허용** | `AgentMessage = Message \| CustomAgentMessages[...]` (`:374`) | 앱이 `notification`, `artifact` 같은 메시지를 대화에 넣을 수 있다. 호출 직전 `convertToLlm`(필수)이 AI가 이해하는 `user/assistant/toolResult`로 걸러 바꾼다(`:222`) |
| **호출 직전 전처리** | `transformContext?` (`:244`) | 오래된 메시지 정리, 외부 정보 주입 |
| **도구 정의와 실행** | `AgentTool extends Tool` + `execute(toolCallId, params, signal, onUpdate)` (`:464-497`) | ai의 `Tool`(설명서)에 실행 함수와 화면용 `label`을 더한 것 |
| **도구 실행 전후 훅** | `beforeToolCall`(막기), `afterToolCall`(결과 덮어쓰기) (`:326`, `:341`) | 정책은 훅으로 주입 |
| **도구 병렬 실행** | `toolExecution: "sequential" \| "parallel"`, 기본 `"parallel"` (`:317`) | 도구별 `executionMode`로 덮어쓸 수 있다 |
| **턴 흐름 제어** | `finishTurn`, `prepareRequest`, `prepareNextTurn` (`:264`, `:271`, `:278`) | 턴이 끝난 뒤 계속/종료 결정, 다음 요청의 컨텍스트, 모델, 추론 수준 교체 |
| **실행 중 개입** | `getSteeringMessages`(진행 중 끼어들기), `getFollowUpMessages`(끝난 뒤 이어 처리) (`:293`, `:306`), `QueueMode` | 사용자가 에이전트가 일하는 동안 메시지를 넣는 기능 |
| **API 키를 호출마다 해석** | `getApiKey?(provider)` (`:254`) | 도구 실행이 길어지는 동안 만료되는 OAuth 토큰 대응(주석) |
| **상태** | `AgentState` (`:382-421`): `model`, `thinkingLevel`, `tools`, `messages`, `isStreaming`, `streamingMessage`, `pendingToolCalls`, `errorMessage` | `Agent` 클래스가 관리 |
| **이벤트로 알림** | `AgentEvent` 10종 (`:514-529`) | 아래 4.3 |
| **LLM 호출 중계** | `streamProxy` (`proxy.ts`) | 브라우저 앱이 서버를 거쳐 호출할 때(`proxy.ts` 머리말) |

### 4.2 `AgentState`와 ai 패키지의 연결 (`types.ts:382-421`)
- `systemPrompt`는 **읽기 전용**이고 "transcript의 시스템 메시지를 재생해서 얻는다." 바꾸려면 시스템 메시지를 추가한다.
- `tools`를 새 배열로 바꾸면 "transcript에 선언된 도구와의 차이를 **다음 요청 전에 시스템 메시지로 모델에 알린다**."
- 이것은 ai/01 §2.1에서 본 `SystemMessage`의 `content`/`sections`/`toolsAdded`/`toolsRemoved` 기능을 agent가 쓰는 곳이다.

### 4.3 이벤트 10종 (`types.ts:514-529`)
`agent_start`/`agent_end`, `turn_start`/`turn_end`, `message_start`/`message_update`/`message_end`, `tool_execution_start`/`tool_execution_update`/`tool_execution_end`.
- **턴(turn)** = 어시스턴트 응답 한 번 + 그 응답의 도구 호출과 결과. (`:518` 주석)
- `message_update`는 ai의 `AssistantMessageEvent`(`text_delta` 등)를 감싸서 전달한다(`assistantMessageEvent` 필드, `:524`).
- 주석(`:510-512`): `agent_end`가 마지막 이벤트이지만, `await`하는 구독자가 끝날 때까지 실행은 끝난 것이 아니다.

### 4.4 하지 않는 일 (다른 층에 있음)
| 일 | 누가 | 근거 |
|---|---|---|
| 회사별 요청 변환, 인증, 모델 목록 | ai | `agent`는 `streamFn`만 호출 |
| **응답 단위 재시도**(과부하, 속도 제한 등) | **`coding-agent`**(`agent-session.ts:1805-1822`, `:3660-3756`)와 `durable` | ai/05 §2.3. `agent-loop.ts`에는 재시도 판정 함수 호출이 없다 |
| 컨텍스트 초과 시 압축 | `coding-agent` (`agent-session.ts:2948-2972`) | 〃 |
| 세션 저장(JSONL 트리), 요약, 스킬, 프롬프트 템플릿 | `coding-agent` / `pi-durable` | `CHANGELOG.md 1.0.0` |
| 도구의 실제 구현(read, bash, edit 등) | `coding-agent` | `agent`는 `AgentTool` 인터페이스만 정의 |
| 화면 | `tui`, `coding-agent` | |

## 5. 위층과 연결되는 지점 (`coding-agent`, `코드 확인`)
- **기본 `streamFn` 등록**: `core/sdk.ts:39` `setDefaultStreamFn(streamSimple)`. 주석(`:37`): 호출자가 `streamFn`을 주지 않고 저수준 루프를 부르는 경우를 위한 것이고 "Agent core remains(…)" 즉 agent는 provider 카탈로그에 의존하지 않는다. `stream-fn.ts`가 이 패턴을 제공한다: 등록하지 않았는데 필요하면 "No default stream function configured. Pass streamFn explicitly or call setDefaultStreamFn()"을 던진다(`stream-fn.ts:17`).
- **`Agent` 만들기**: `core/sdk.ts:387-420`.
  ```ts
  const agent = new Agent({
      initialState: { systemPrompt: "", model, thinkingLevel, tools: [], messages: existingSession.messages },
      convertToLlm: convertToLlmWithBlockImages,
      streamFn: async (model, context, options) => {
          const requestOptions = buildRequestOptions(model, options);
          ... cacheWarmer.start(...)   // 캐시 예열
          return modelRuntime.streamSimple(model, context, requestOptions);      // ← ai 의 Models.streamSimple
      },
      onPayload: ..., onResponse: ..., onProviderStreamEvent: ...,
      sessionId: sessionManager.getSessionId(),
      transformContext: async (messages) => extensionRunner?.emitContext(messages) ?? messages,
      steeringMode: ..., followUpMode: ..., transport: ..., thinkingBudgets: ...,
  ```
  즉 `coding-agent`가 `streamFn`을 직접 만들어서 `Models.streamSimple`(ai/06 ②)을 감싸 넘긴다.
- **`Agent`의 공개 필드가 곧 훅 목록**이다(`agent.ts:188-215`): `convertToLlm`, `transformContext`, `streamFunction`, `getApiKey`, `onPayload`, `onResponse`, `onProviderStreamEvent`, `beforeToolCall`, `afterToolCall`, `finishTurn`, `prepareRequest`, `prepareNextTurn`, `prepareNextTurnWithContext`. 메서드: `subscribe`, `prompt`, `continue`, `steer`, `followUp`, `abort`, `waitForIdle`, `reset`, 큐 조회·비우기 계열(`agent.ts:230-373`).
- **저수준 노출**: `coding-agent`는 `runToolCall`도 가져다 쓴다(`core/agent-session.ts:31`, `:711`, `core/nested-tool-calls.ts`). 도구가 내부에서 다른 도구를 부를 때 같은 도구 파이프라인(검증, 훅)을 타게 하려는 것으로 보인다(`nested-tool-calls.ts` 주석, `추론`).

## 6. 이전 분석(Q5~Q8, 4259686d9 기준)과의 대조
| 이전 서술 | 이 commit에서 확인한 것 | 다음에 할 일 |
|---|---|---|
| Q4/Q7: 재시도(3회, 2·4·8초)와 overflow compaction은 루프 밖 `_runAgentPrompt`가 `agent.continue()`로 | `agent.continue()`는 `Agent`에 있다(`agent.ts:384`). 재시도는 `_handlePostAgentRun`→`_isRetryableError`→`_prepareRetry`(`agent-session.ts:1805-1822`, `:3660-3756`)로 보이고 `retryDelayMs(settings, 시도횟수)`를 쓴다(ai/05 §2.3). **함수 이름과 구조가 달라졌다** | `coding-agent` 단계에서 Q7 재검증 |
| Q5: agent-loop는 "상태 없는 이중 루프" | 파일은 940줄이고 훅이 `finishTurn`, `prepareRequest`, `prepareNextTurn` 등 이전 서술에 없던 것이 보인다(`types.ts`). `0.87.0`에서 `shouldStopAfterTurn`이 `finishTurn`으로 대체됨 | `agent-loop.ts` 전체를 새로 읽기 |
| Q6: `Agent` 클래스는 `processEvents`로만 상태 갱신, `handleRunFailure` | 같은 이름이 있다(`agent.ts:532`, `:565`). 내용은 확인 전 | `agent.ts` 전체를 새로 읽기 |
| learning-guide의 agent 관련 서술 | 위와 같이 재검증 필요 | |

## 7. 읽지 않은 것 (`미확인`)
- `agent-loop.ts`의 루프 본문(턴 구조, 도구 준비·실행·마무리, 병렬 실행의 이벤트 순서, 종료 조건)
- `agent.ts`의 `Agent` 내부(`prompt`/`continue`, 큐, 구독자 순차 `await`, 실패 처리, `waitForIdle`)
- `proxy.ts` 본문(서버가 보내는 이벤트에서 `partial`을 뺀 형식을 다시 조립하는 부분)
- 테스트 4개 파일, `examples/mcp-codemode`
- `coding-agent`가 `Agent`를 쓰는 나머지(`agent-session.ts`), 두 번째 `new Agent` 위치
- `durable` 패키지가 이 패키지의 개념을 어떻게 이어받았는지

## 8. 다음 문서 계획 (agent 시리즈)
| 번호 | 내용 |
|---|---|
| **01-types** | 이미 읽은 `types.ts`의 `AgentMessage`, `AgentTool`, `AgentEvent`, `AgentLoopConfig`를 쉬운 말과 표로 정리 |
| 02-agent-loop | `agent-loop.ts` 루프 본문: 턴, 도구 실행(순차/병렬), 훅 호출 지점, 종료 조건, ai 스트림을 받는 `:385-455` |
| 03-agent-class | `Agent` 클래스: 상태, 큐(steering/follow-up), 구독자, 실패 처리, `waitForIdle` |
| 04-proxy | `streamProxy`와 `ProxyMessageEventStream` |
| 05-call-flow | `agent.prompt("...")` 한 번이 지나가는 길(ai/06과 이어서) + 실행 실험(가짜 `streamFn`) |
