# agent 06: `agent`와 `coding-agent`의 관계, 계층을 나눈 이유

- 기준 commit: `28dcce2ba` (`packages/agent/src`는 `3874b3e98`과 같다). 작성일: 2026-10-14
- 선행 문서: [00-role](./00-role.md), [01-types](./01-types.md), [02-agent-loop](./02-agent-loop.md), [03-agent-class](./03-agent-class.md), [04-proxy](./04-proxy.md)
- 훅 상세: [07-hooks](./07-hooks.md)
- 읽은 파일: `coding-agent/src/core/tools/tool-definition-wrapper.ts`(앞 40줄), `coding-agent/src/core/agent-session.ts`(`grep`으로 `agent.state.tools` 사용 줄만), `agent/src/agent-loop.ts:726-780`, `agent/README.md`(앞 30줄), `mcp/README.md:34-41`, `codemode/README.md:117-120`. 나머지는 00~05의 기록을 가져왔다.
- 검증 수준: 관계(누가 누구를 부르는가)는 `코드 확인`. 계층을 나눈 이유는 개발자가 직접 적은 문서를 찾지 못했으므로 코드, README, CHANGELOG에서 읽어낸 `추론`이다.

## 1. 이 문서의 질문
- `coding-agent`는 `agent`를 어떻게 쓰는가? 도구는 누가 정의하고 누가 호출하는가?
- 왜 반복 루프(`agent`)와 제품(`coding-agent`)을 나눴는가?

## 2. 관계 한 장 요약
`agent`는 반복의 순서를 맡고, `coding-agent`는 반복에 들어가는 내용을 채운다. `coding-agent`가 함수와 설정을 넘기면 `agent`가 필요한 때 그것을 호출한다.

```
coding-agent (내용을 채운다)              agent (순서를 맡는다)
──────────────────────────────           ──────────────────────────────
streamFn  (ai의 streamSimple을 감싼 것) ──▶  AI를 부를 때 호출
tools     (read, bash, edit 등 execute) ──▶  AI가 도구를 요청하면 execute() 호출
훅        (beforeToolCall, 압축 등)     ──▶  정해진 지점에서 호출
구독자    (화면, 세션 저장)             ◀──  이벤트 10종을 받는다
```

## 3. 넘기는 것 네 가지

### 3.1 `streamFn`: AI를 부르는 함수 (상세: [08-stream-fn](./08-stream-fn.md))
`coding-agent`(`core/sdk.ts:387-420`)가 `Models.streamSimple`을 감싼 함수를 만들어 `new Agent({ streamFn })`에 넘긴다. `agent`는 provider를 모르고 이 함수만 호출한다(00-role §3.1, §5).

### 3.2 `tools`: 실행 함수가 들어 있는 도구 객체
- `coding-agent`의 `core/tools/`에 `read.ts`, `bash.ts`, `edit.ts`, `write.ts`, `grep.ts`, `find.ts`, `ls.ts`, `powershell.ts` 같은 구현이 있다.
- 이 구현은 `coding-agent` 자체 형식인 `ToolDefinition`이다. `tool-definition-wrapper.ts`의 `wrapToolDefinition`이 이를 `AgentTool` 모양으로 바꾼다. 필드(`name`, `label`, `description`, `parameters`, `outputSchema`, `prepareArguments`, `executionMode`)를 그대로 옮기고 `execute`만 한 번 감싸서 `coding-agent`용 컨텍스트(`ctxFactory`)를 끼워 준다(`코드 확인`).
- 바꾼 배열을 `agent.state.tools = declared`로 등록한다(`agent-session.ts:1570`).
- AI가 `read`를 요청하면 `agent-loop.ts`가 이름이 같은 도구를 찾아 `validateToolArguments`로 인자를 검사하고(`:726`) `beforeToolCall`을 거친 뒤 `tool.execute(...)`를 부른다(02 §7.3). `agent`는 `execute` 안에서 무슨 일이 일어나는지 모른다.

### 3.3 훅: 정해진 지점에 끼우는 정책
훅은 모두 10개다. `coding-agent`가 7개(`convertToLlm`, `transformContext`, `prepareRequest`, `prepareNextTurn`, `finishTurn`, `beforeToolCall`, `afterToolCall`)를 채우고, 끼어들기 훅 2개(`getSteeringMessages`, `getFollowUpMessages`)는 `Agent` 클래스가 스스로 채우며(큐에는 `coding-agent`가 `agent.steer`, `agent.followUp`으로 넣는다), `getApiKey`는 채우는 곳을 찾지 못했다. 훅은 `AgentSession`이 `Agent`의 필드에 꽂고, 몸체 안에서 확장(extension) 핸들러(`pi.on("tool_call", ...)` 등)에 연결된다. 표, 호출 순서, 예시는 [07-hooks](./07-hooks.md)에 있다(2026-10-15 확인).

### 3.4 구독자: 이벤트를 받는 쪽
`agent.subscribe(...)`로 이벤트 10종을 받는다(01 §5.3). `coding-agent`가 이것으로 화면 갱신과 세션 저장을 하는지는 `미확인`(coding-agent 단계에서 확인).

## 4. 반대 방향: `coding-agent`가 `agent`의 저수준 함수도 쓴다
`runToolCall`을 가져다 쓴다(`agent-session.ts:31`, `:711`, `nested-tool-calls.ts`). 도구가 내부에서 다른 도구를 부를 때 같은 검증과 훅을 타게 하려는 것으로 보인다(`추론`, 00-role §5).

## 5. 왜 나눴나 (`추론`)
아래 이유들은 개발자의 설명이 아니라 코드와 문서에서 읽어낸 것이다. 근거를 같이 적는다.

### 5.1 도구 내용은 제품마다 다르고, 반복은 같다
- 반복의 순서(요청 찾기, 검증, 훅, 실행, 결과 붙이기, 다음 호출)는 도구가 `read`든 주문 조회든 같다.
- 도구의 내용은 제품마다 다르다. 코딩 에이전트는 `read`, `bash`, `edit`이 필요하고, 다른 앱은 MCP 도구나 자기 업무 도구가 필요하다.
- 근거: `agent/README.md`의 Quick Start는 도구 없이 모델, 시스템 프롬프트, `streamFn`만 넘겨 `Agent`를 쓴다. `mcp/README.md:34`와 `codemode/README.md:117`은 각자의 도구를 `AgentTool`로 감싸 `Agent`에 주는 방법을 적고 있다. `AgentTool` 모양만 맞추면 어디서 만든 도구든 꽂을 수 있다.

### 5.2 `streamFn` 주입과 같은 방식이다
`agent`는 provider 목록, 인증, 카탈로그에 의존하지 않는다(`stream-fn.ts` 주석, 04 §9). 실제 일을 하는 부분은 밖에서 주입받고 `agent`는 반복과 순서만 책임지는 구조가 `streamFn`과 도구에 똑같이 적용되어 있다.

### 5.3 정책과 실행을 분리한다
권한 확인, 로깅, 결과 가공은 `beforeToolCall`/`afterToolCall` 훅으로 넣는다. 도구 코드는 일만 하고 "실행해도 되는가"는 밖에서 정한다. 이 설계는 `wiki/concepts/stealable-pattern-hook-injected-loop-with-throw-contract.md`에 패턴으로 정리되어 있다.

### 5.4 패키지를 작게 유지하는 방향이다
- 근거: `CHANGELOG.md [1.0.0]`에서 harness(세션, 압축, 스킬, 프롬프트 템플릿, 텔레메트리 스키마 등)를 전부 삭제했고, 이 패키지는 `Agent`, 루프, proxy, 타입만 남았다(00-role §2.3). 이전 SHA 대비 약 3만 줄이 줄었다.
- 도구 구현을 위층에 두는 것도 같은 방향으로 보인다. 다만 CHANGELOG는 무엇을 지웠는지만 적고 이유를 적지 않았다.

### 5.5 다른 실행 환경을 같은 루프로 지원한다
`streamProxy`(04)는 브라우저나 웹앱이 서버를 거쳐 AI를 부르게 하는 `StreamFn`이다. 루프가 `streamFn`만 알기 때문에 "직접 호출"과 "서버 경유"를 바꿔 끼워도 `Agent`와 루프는 바뀌지 않는다. 이 repo에서 `coding-agent`는 `streamProxy`를 쓰지 않는다(04 §8).

## 6. 나눈 것의 비용
- 변환 계층이 하나 더 있다. `coding-agent`는 `ToolDefinition`을 `AgentTool`로 바꾸는 래퍼가 필요하다(§3.2).
- 이 repo 안에서 `agent`를 의존으로 선언하고 import하는 패키지는 `coding-agent` 하나뿐이다(00-role §3.2). `server`, `session-backends`, `chord` 등은 이전에는 썼으나 지금은 쓰지 않는다. 그래서 "여러 제품이 공유한다"는 재사용의 이점은 설계상 열려 있을 뿐, 이 repo 안에서는 아직 실제로 쓰이지 않는다.
- 위층에서 채워야 할 구멍이 생긴다. 05 §5에서 정리한 알려진 구멍(중단 시 `toolResult` 짝 불일치, 압축 후 `state.messages` 갱신 등)은 `agent`가 메우지 않으므로 `coding-agent`가 어떻게 다루는지 확인해야 한다.

## 7. 읽지 않은 것 (`미확인`)
- `coding-agent`가 채우는 훅의 전체 목록과 각 훅의 내용(`agent-session.ts` 대부분)
- `subscribe`로 무엇을 하는지(화면, 세션 저장, 재시도)
- 개발자가 계층을 나눈 이유를 직접 적은 문서(README, 설계 문서, 커밋 메시지)가 있는지. 이번에는 `agent/README.md` 앞 30줄과 `CHANGELOG.md`만 봤다.

## 8. 다음
`coding-agent` 단계: `core/sdk.ts` 전체, `core/agent-session.ts`, `core/tools/`의 도구 하나(`read.ts`)를 읽고 이 문서의 §3.3, §3.4를 확인한다.
