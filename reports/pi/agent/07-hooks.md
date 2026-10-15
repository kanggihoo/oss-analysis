# agent 07: 훅 정리 (누가 채우고, 언제 부르고, 어떻게 바꾸나)

- 기준 commit: `3874b3e98` (`repos/pi` 체크아웃). 작성일: 2026-10-15. `packages/agent/src`는 `28dcce2ba`와 같다.
- 선행 문서: [01-types](./01-types.md) §4, [02-agent-loop](./02-agent-loop.md) §5~§7, [03-agent-class](./03-agent-class.md) §3, §10, [06-layering](./06-layering.md)
- 읽은 파일: `agent/src/agent.ts:186-230`, `:460-506`, `agent/src/types.ts`(훅 선언 줄), `coding-agent/src/core/sdk.ts:380-425`, `coding-agent/src/core/agent-session.ts:618-700`, `:750-775`, `:818-905`, `:1715-1750`, `coding-agent/src/core/extensions/runner.ts:764-772`, `:1233-1290`, `extensions/types.ts:1545-1612`, `coding-agent/examples/extensions/permission-gate.ts`. 나머지는 `grep`으로 대입 줄만 확인했다.
- 검증 수준: 훅이 어디서 채워지고 어디서 불리는지는 `코드 확인`. 실행한 것은 없다. 확장(extension) 로딩과 등록 과정은 읽지 않았다(`미확인`).

## 0. 이 문서의 질문
- `agent`가 부르는 훅은 모두 몇 개이고, 각각 누가 채우는가?
- 훅은 매번 호출되는가, 아니면 필요한 것만 골라 호출하는가? 호출됐을 때 할 일은 누가 정하는가?
- 사용자는 각 단계에서 실행할 로직을 어떻게 바꾸는가?

## 1. 용어
- 훅(hook): `agent` 루프에 정해진 자리가 있고, 그 자리에서 `agent`가 호출하는 함수다. 함수를 호출한다는 것은 그 함수 안의 코드를 실제로 실행한다는 뜻이다. 훅은 반환값이 루프의 동작을 바꾼다. 예를 들어 `beforeToolCall`이 `{ block: true }`를 돌려주면 도구는 실행되지 않고, `finishTurn`이 `{ action: "end" }`를 돌려주면 루프가 끝난다.
- 이벤트 구독자(`agent.subscribe`)는 훅이 아니다. "일어났음"을 알려 받는 용도이고 반환값을 쓰지 않는다(03 §5).
- `streamFn`도 훅이 아니다. 루프가 AI를 부를 때 쓰는 함수 하나로, 따로 다룬다([01 §6](./01-types.md)).

## 2. 훅 10개와 채우는 곳
`AgentLoopConfig`(`types.ts`)의 함수 필드는 10개다. `Agent`가 `createLoopConfig`(`agent.ts:460-506`)에서 이 10개를 루프에 넘긴다.

| # | 훅 | 부르는 시점 | 누가 채우나 | 근거 |
|---|---|---|---|---|
| 1 | `convertToLlm` (필수) | AI 호출 직전, 대화 기록을 AI가 이해하는 형태로 변환 | `coding-agent`가 `new Agent`에 넘김 | `sdk.ts:395` |
| 2 | `transformContext` | AI 호출 직전, 대화 기록 손보기 | `coding-agent`가 `new Agent`에 넘기고 `AgentSession`이 덧씌움 | `sdk.ts:412`, `agent-session.ts:1722`, `:1742` |
| 3 | `getApiKey` | AI 호출 직전, 키 새로 가져오기 | 채우는 곳을 찾지 못함 | `grep` 기준 |
| 4 | `prepareRequest` | 매 요청 직전 | `coding-agent`(`AgentSession`) | `agent-session.ts:761` |
| 5 | `prepareNextTurn` | 다음 턴 시작 직전(2턴째부터) | `coding-agent`(`AgentSession`, `...WithContext` 변형으로) | `agent-session.ts:876` |
| 6 | `finishTurn` | 턴 끝, 계속할지 결정 | `coding-agent`(`AgentSession`) | `agent-session.ts:860` |
| 7 | `beforeToolCall` | 도구 실행 직전 | `coding-agent`(`AgentSession`) | `agent-session.ts:625` |
| 8 | `afterToolCall` | 도구 실행 직후 | `coding-agent`(`AgentSession`) | `agent-session.ts:626` |
| 9 | `getSteeringMessages` | 도구 실행 뒤, 끼어든 메시지 확인 | `agent`의 `Agent` 클래스(큐에서 꺼냄) | `agent.ts:496` |
| 10 | `getFollowUpMessages` | 멈추려 할 때, 이어 처리할 메시지 확인 | `agent`의 `Agent` 클래스(큐에서 꺼냄) | `agent.ts:503` |

정리하면 `coding-agent`가 채우는 훅이 7개(1, 2, 4, 5, 6, 7, 8), `Agent` 클래스가 스스로 채우는 훅이 2개(9, 10), 채우는 곳을 못 찾은 훅이 1개(3)다.

훅은 아니지만 `Agent`에 함께 넘기는 것:
| 항목 | 뜻 | 누가 채우나 |
|---|---|---|
| `streamFn` (`Agent`의 필드명은 `streamFunction`) | AI를 부르는 함수 | `coding-agent`, `sdk.ts:396` |
| `onPayload`, `onResponse`, `onProviderStreamEvent` | 요청과 응답을 들여다보는 콜백. 루프가 아니라 `streamFn`이 소비한다 | `coding-agent`, `sdk.ts:408-410` |

`Agent`의 public 함수 필드는 13개로 세어진다(00-role §5). 위 10개 중 9, 10은 필드가 아니라 `createLoopConfig`가 만든 함수이고, 필드에는 `streamFunction`, 콜백 3개, `prepareNextTurnWithContext`가 더 있다. `prepareNextTurnWithContext`는 `prepareNextTurn`의 변형으로, 있으면 그것을 부르고 없으면 `prepareNextTurn(signal)`을 부르는 어댑터를 `Agent`가 끼워 준다(03 §10).

## 3. 한 턴 안에서 부르는 순서
02 §5, §6, §7에서 코드와 실행으로 확인한 순서다.
```
[턴 시작]
 prepareNextTurn            (2턴째부터)
 getSteeringMessages        (끼어든 메시지 확인)
 prepareRequest
 transformContext → convertToLlm → (normalizeContext) → getApiKey → streamFn     (AI 호출)
 [도구가 요청되면]
   beforeToolCall → execute → afterToolCall
 finishTurn
[턴 끝]  →  steering 확인 → 없으면 getFollowUpMessages (멈추려 할 때)
```

## 4. 훅은 매번 호출되고, 할 일은 훅 안에서 정한다

### 4.1 호출 여부
- `agent` 루프는 훅 필드가 비어 있으면 건너뛰고, 채워져 있으면 정해진 자리에서 매번 호출한다. 단계마다 "어떤 훅을 활성화할지"를 고르는 로직은 없고, 자리마다 호출문이 고정되어 있다.
- `coding-agent`에서는 `AgentSession`이 시작할 때 훅을 `Agent`의 필드에 꽂는다. 그래서 설치한 훅은 도구를 실행할 때마다 호출된다.

### 4.2 호출됐을 때 할 일
호출된 훅이 그때그때 할 일이 있는지 확인한다. `_beforeToolCall`(`agent-session.ts:630-650`)이 대표적이다.
```ts
if (!runner.hasHandlers("tool_call")) return undefined;   // 확장이 아무도 안 걸어 뒀다: 아무것도 안 함
return await runner.emitToolCall({...});                  // 있다: 등록된 핸들러들을 차례로 실행하고 결과를 돌려줌
```
- `undefined`는 "바꿀 것 없음"이라서 `agent`는 기본 동작을 그대로 진행한다.
- 핸들러가 `{ block: true, reason }`을 돌려주면 도구가 실행되지 않고 에러 결과가 기록된다.

### 4.3 훅을 덧씌우는 방식 (`previousX`)
같은 훅을 여러 기능이 쓰므로, 새 훅을 꽂을 때 기존 것을 저장해 두고 새 함수 안에서 함께 부른다. `finishTurn`이 예다(`agent-session.ts:859-868`).
```ts
const previousFinishTurn = this.agent.finishTurn;
this.agent.finishTurn = async (turn, signal) => {
    const extensionContinue = await this._dispatchTurnEndBoundary(...);   // 확장의 turn_end 처리
    const previousDecision = await previousFinishTurn?.(turn, signal);     // 이전에 꽂힌 것
    if (previousDecision?.action === "end") return previousDecision;       // end가 우선
    if (extensionContinue || previousDecision?.action === "continue") return { action: "continue" };
    return undefined;
};
```
`prepareRequest`(`:760-761`), `prepareNextTurnWithContext`(`:872-876`), `transformContext`(`:1721-1722`, `:1741-1742`)도 같은 방식이다.

### 4.4 설정 시점
`Agent`는 run을 시작할 때 훅과 설정을 읽어 복사한다(03 §10). 그래서 run 도중에 훅 필드를 바꿔도 현재 run에는 반영되지 않는다. `AgentSession`은 시작 시점에 훅을 꽂으므로 이 제약과 충돌하지 않는다(`추론`, 설치 시점의 정확한 순서는 읽지 않았다).

## 5. 사용자가 로직을 바꾸는 방법: 확장(extension)
`coding-agent`는 훅의 몸체를 확장 시스템(`extensionRunner`)에 연결한다. 사용자는 확장 파일에서 `pi.on("이벤트", 핸들러)`로 핸들러를 등록해서 각 단계의 로직을 바꾼다.

### 5.1 훅과 확장 이벤트의 대응
`extensions/types.ts:1545-1612`에 등록 가능한 이벤트가 나열되어 있다. 훅과 이어지는 것은 아래와 같다.
| 훅 | 확장 이벤트 | 근거 |
|---|---|---|
| `beforeToolCall` | `tool_call` | `agent-session.ts:630-650` (`코드 확인`) |
| `afterToolCall` | `tool_result` | `agent-session.ts:656-690` (`코드 확인`) |
| `transformContext` | `context`, `context_with_system` | `runner.ts:1289` `emitContext`가 두 단계로 처리한다는 주석 (`코드 확인`) |
| `finishTurn` | `turn_end`의 결과 | `agent-session.ts:860-868`이 `_dispatchTurnEndBoundary`로 확장에 넘기고 그 결과(`emitBoundary`)가 계속하라고 하면 `continue`를 돌려줌 (`코드 확인`) |

`prepareRequest`, `prepareNextTurn`은 확장 이벤트가 아니라 `AgentSession`이 직접 하는 일(모델 선택 확인, 압축, 시스템 프롬프트와 도구 목록 갱신)이다(`agent-session.ts:761-800`, `:876-905`).

### 5.2 핸들러 실행 규칙 (`emitToolCall`, `runner.ts:1233-1250`)
- 확장마다 등록한 핸들러를 순서대로 실행한다.
- 결과가 있으면 기억해 두고, 어느 핸들러가 `block`을 돌려주면 거기서 바로 반환한다. 이 규칙은 `tool_call`에 대해 읽었고 다른 이벤트는 같다고 확인하지 않았다.
- `hasHandlers(eventType)`은 확장 전체에서 그 이벤트의 핸들러가 하나라도 있는지 본다(`runner.ts:764-772`).

### 5.3 예: 위험한 bash 명령 막기 (`examples/extensions/permission-gate.ts`)
```ts
pi.on("tool_call", async (event, ctx) => {
  if (event.toolName !== "bash") return undefined;          // bash가 아니면 상관 안 함
  if (/rm -rf|sudo|chmod 777 같은 패턴이 있으면) {
    // 화면이 있으면 사용자에게 허용 여부를 묻고, 없으면 기본으로 막는다
    return { block: true, reason: "Blocked by user" };
  }
  return undefined;                                          // 그 외는 그대로 진행
});
```
`beforeToolCall` 훅 → `emitToolCall` → 이 핸들러 순서로 이어진다. `agent`와 `coding-agent`의 코드를 바꾸지 않고 파일 하나로 정책을 바꿀 수 있다.

## 6. 끼어들기 훅(9, 10)은 다르게 동작한다
- `Agent`에 큐 2개(`steeringQueue`, `followUpQueue`)가 있고, 훅 9, 10은 그 큐에서 `drain()`으로 꺼내 주는 단순한 함수다(`agent.ts:496-503`). 첫 `getSteeringMessages` 호출은 `skipInitialSteeringPoll`일 때 건너뛴다(03 §8).
- 큐에 넣는 것은 `coding-agent`가 한다. 사용자가 입력하면 `AgentSession`이 `agent.steer(...)` 또는 `agent.followUp(...)`을 부른다(`agent-session.ts:2198`, `:2215`, `:2263-2265`).
- 꺼내는 방식(전부 또는 하나씩)은 `steeringMode`, `followUpMode` 설정으로 정하고, 이 값은 `settingsManager`에서 온다(`sdk.ts:416-417`, `agent-session.ts:2645`).
- `agent-session.ts:2371`의 `getSteeringMessages()`는 훅이 아니라 화면에 대기 메시지를 보여 주려고 큐 내용을 읽는 별개의 메서드다. 이름만 같다.

## 7. throw 정책 (02 §7.3 요약)
| 훅 | 던지면 |
|---|---|
| `beforeToolCall`, `afterToolCall` (그리고 도구의 `execute`) | 루프가 try/catch로 받아 `isError: true`인 도구 결과로 바꾼다 |
| 나머지 훅(`convertToLlm`, `transformContext`, `getApiKey`, `prepareRequest`, `prepareNextTurn`, `finishTurn`, 큐 훅) | 루프가 처리하지 않아 `runLoop`가 reject되고, `Agent`가 `handleRunFailure`로 이벤트 순서를 맞춰 마무리한다(03 §7) |

## 8. 읽지 않은 것 (`미확인`)
- `getApiKey`를 `coding-agent`가 정말로 채우지 않는지. 키 해석은 `streamFn` 안의 `ai` 쪽(`modelRuntime.streamSimple`)이 하는 것으로 보이지만 읽지 않았다.
- 확장 로딩과 `pi.on` 등록이 내부에서 어디에 저장되는지, `context`와 `context_with_system`의 두 단계 처리 세부.
- `prepareRequest`, `prepareNextTurnWithContext` 본문의 나머지 분기(압축 임계, 가상 모델 처리 등).
- `AgentSession`이 훅을 설치하는 호출 순서와 시점.
