# pi 학습 가이드: `pi-ai`와 `pi-agent-core` 이해하기

- **기준 commit**: `4259686` (2026-09-29)
- **이 글의 범위**: 패키지 지도(Q1), `pi-ai`(Q4), `agent-loop`(Q5), `Agent` 클래스(Q6), coding-agent의 hook 구현(Q7), 세션 projection(Q8). 상세 근거와 줄 번호는 각 질문 문서에 있다.
- **읽는 법**: 처음부터 순서대로 읽으면 된다. 그림이 필요하면 각 절 끝의 링크를 연다.

---

## 1. pi는 어떤 프로젝트인가

pi는 **터미널에서 동작하는 코딩 에이전트**(`pi` CLI)와, 그것을 만드는 데 쓴 부품들을 한 레포에 모아 둔 TypeScript monorepo다. 패키지는 14개지만 역할로 묶으면 네 무리다.

```
[제품]      coding-agent ─ 사용자가 실행하는 pi CLI
              │
[핵심]      agent-core ──► ai ──► Anthropic / OpenAI / Google ...
[독립 부품] tui · codemode · mcp · telemetry
[실험]      chord · protocol/client/server · durable · session-backends
```

비유하면 이렇다.

- **ai**는 "통역사"다. 어느 나라 말(어느 LLM 회사 API)이든 같은 문장 형식으로 주고받게 해 준다.
- **agent-core**는 "작업 반장"이다. 통역사에게 질문하고, 답에 "이 도구를 써라"가 있으면 도구를 돌리고, 결과를 다시 알려 주는 일을 끝날 때까지 반복한다.
- **coding-agent**는 "현장"이다. 파일 읽기/쓰기, bash 같은 실제 도구와 화면·세션 저장을 붙여서 반장을 일하게 한다.

그래서 공부도 **아래에서 위로** 한다. 통역사(ai) → 반장(agent-core) → 현장(coding-agent) 순서다. 실험 무리(chord 등)는 지금의 `pi` 동작을 이해하는 데 필요 없어서 마지막에 본다. (실험 트랙이라는 판단은 `추론`이다. 그 코드를 coding-agent에서는 `src/experimental/` 아래에서만 쓴다.)

> 그림: [패키지 구조도](./diagrams/structure.html)

---

## 2. `pi-ai`: 모든 LLM을 같은 모양으로 부르기

### 2.1 해결하는 문제

LLM 회사마다 API가 다르다. Anthropic은 `messages` API, OpenAI는 `chat/completions`와 `responses`, Google은 또 다른 형식을 쓴다. 인증 방법(API key, OAuth), 추론(thinking) 설정 방식, tool call ID 형식도 제각각이다.

`pi-ai`는 이 차이를 전부 안에서 처리한다. 바깥에는 **입력 하나, 출력 하나**만 보인다.

- **입력** `Context`: 대화 메시지 목록 + (선택) system prompt와 tool 목록
- **출력** `AssistantMessage`: 모델의 답. 여기에 텍스트, 추론(thinking), tool 호출이 담긴다. 한꺼번에 받거나 조각(이벤트)으로 흘려받을 수 있다.

### 2.2 가장 중요한 구분: api와 provider

이 패키지는 두 개념을 나눠 둔다. 이 구분만 알면 폴더 구조가 바로 읽힌다.

| | **api** (`src/api/`) | **provider** (`src/providers/`) |
|---|---|---|
| 뜻 | 통신 방식. 요청을 어떤 JSON으로 보내고, 응답 스트림을 어떻게 해석하나 | 회사/계정. 주소(baseUrl) + 인증 방법 + 모델 목록 + 쓸 api |
| 예 | `anthropic-messages`, `openai-completions` | `anthropic`, `groq`, `deepseek`, `openrouter` |
| 개수 | 10종 | 약 42개 |

Groq, Cerebras, DeepSeek은 회사는 다르지만 모두 "OpenAI 호환" 방식으로 통신한다. 그래서 셋 다 `openai-completions` api 하나를 같이 쓰고, 세부 차이는 모델별 `compat` 설정으로 맞춘다. 새 회사를 붙일 때 통신 코드를 다시 짤 필요가 없다.

### 2.3 한 번의 호출이 지나가는 길

`models.streamSimple(model, context, { reasoning: "high" })`를 부르면 이렇게 진행된다.

1. **즉시 스트림을 돌려준다.** 아직 네트워크 요청은 가지 않았다. 호출한 쪽은 곧바로 `for await`로 기다릴 수 있다.
2. **뒤에서 준비한다.**
   - 입력 정규화: system prompt와 tool 목록을 system 메시지 하나로 접는다.
   - provider 찾기: `model.provider`가 `"anthropic"`이면 Anthropic provider를 쓴다.
   - 인증: 요청에 직접 준 key → 저장된 로그인 정보 → 환경변수 순서로 찾는다. OAuth 토큰이 5분 안에 만료되면 여기서 갱신한다.
   - 구현 불러오기: `anthropic-messages` 코드를 **처음 쓸 때만** `import()`로 불러온다. 안 쓰는 회사의 SDK는 아예 로드하지 않는다.
3. **옵션을 바꾼다.** `reasoning: "high"`라는 공통 옵션을 Anthropic의 effort 값이나 thinking token 예산으로 바꾼다.
4. **요청하고 흘려보낸다.** SSE 응답을 받는 대로 공통 이벤트로 바꿔 스트림에 넣는다.

```
start → text_delta … → toolcall_start → toolcall_delta … → toolcall_end → done
```

### 2.4 실패를 다루는 방식: throw하지 않는다

네트워크 오류, 인증 실패, 모듈 로드 실패는 예외로 던지지 않는다. 스트림의 마지막 이벤트가 `error`가 되고, 메시지의 `stopReason`이 `"error"`(또는 사용자가 중단했으면 `"aborted"`)가 된다. 예외는 하나뿐이다. `streamSimple`을 직접 호출했는데 인증이 아예 없으면 즉시 throw한다.

덕분에 호출하는 쪽은 `try/catch` 없이 **"마지막 메시지의 stopReason만 보면 된다"**. 이 규칙이 뒤의 agent-loop 설계와 이어진다.

`stopReason`은 7가지다.

| 값 | 뜻 |
|---|---|
| `pending` | 아직 생성 중 |
| `stop` | 정상적으로 답을 마침 |
| `toolUse` | "이 도구를 실행해 달라"며 멈춤 |
| `length` | 출력 토큰 한도에 걸려 잘림 |
| `deferred` | 나중에 받아 가라는 handle만 줌 (이 커밋에서는 테스트용 faux provider만 구현) |
| `error` / `aborted` | 실패 / 사용자 중단 |

### 2.5 알아 두면 좋은 기능

- **모델 바꾸기(hand-off)**: 대화 도중 Claude에서 GPT로 바꿔도 이전 이력을 새 모델에 맞게 변환한다. 예를 들어 OpenAI의 450자가 넘는 tool call ID를 Anthropic 규칙(64자, 영숫자)에 맞게 줄인다.
- **모델 목록**: 빌드할 때 models.dev와 OpenRouter 같은 곳에서 받아 코드로 생성한다. tool 호출을 지원하는 모델만 넣는다. 실행 중에 목록을 새로 받는 provider(`radius`)도 있다.
- **재시도는 하지 않는다**: "다시 시도할 만한 오류인가"를 판정하는 함수만 준다. 실제 재시도는 위층(agent, coding-agent)이 한다.

> 그림: [구조](./diagrams/ai-architecture.html) · [호출 시퀀스](./diagrams/ai-stream-sequence.html) · [준비 단계와 실패 경로](./diagrams/ai-streamsimple-workflow.html) · [stopReason 상태](./diagrams/ai-message-lifecycle.html) · [모델 목록 흐름](./diagrams/ai-model-catalog-dataflow.html)
> 상세: [Q4](./questions/q4-ai-package-roles.md)

---

## 3. `agent-loop`: 도구를 쓰며 일하는 반복문

### 3.1 에이전트란 무엇인가

LLM은 스스로 파일을 읽지 못한다. 대신 "`read` 도구를 `src/main.ts` 인자로 불러 달라"는 **tool call**을 답으로 낸다. 누군가 그걸 실제로 실행하고 결과를 대화에 붙여서 다시 물어봐야 한다. 이 반복을 해 주는 것이 agent loop다.

사용자가 "main.ts에 있는 버그 고쳐 줘"라고 했을 때의 예:

```
turn 1  LLM: "read(main.ts) 해 줘"          stopReason=toolUse
        loop: read 실행 → 파일 내용을 toolResult로 추가
turn 2  LLM: "edit(main.ts, ...) 해 줘"     stopReason=toolUse
        loop: edit 실행 → "수정 완료"를 toolResult로 추가
turn 3  LLM: "고쳤습니다. 원인은 ..."        stopReason=stop
        loop: tool 호출 없음 → 종료
```

여기서 **turn**은 "LLM 응답 1개 + 그 응답이 요청한 tool 실행들"을 말한다.

### 3.2 루프는 두 겹이다

```
바깥 루프
  안쪽 루프: tool 호출이나 끼어든 메시지(steering)가 남아 있는 동안
    ① 대기 메시지를 대화에 넣는다
    ② LLM에 요청하고 응답을 흘려받는다
    ③ 응답에 tool call이 있으면 실행하고 결과를 붙인다
    ④ turn 끝 → 새로 끼어든 메시지가 있나 확인
  멈추려는 시점: 나중에 처리할 메시지(follow-up)가 있으면 바깥 루프를 한 번 더
  없으면 종료
```

사용자가 에이전트에게 말을 거는 방법은 두 가지다.

- **steering** (`agent.steer()`): "잠깐, 테스트 파일도 같이 봐" 같은 **작업 중 방향 전환**이다. 지금 turn의 tool 실행을 마친 뒤 곧바로 다음 요청에 들어간다.
- **follow-up** (`agent.followUp()`): "끝나면 커밋 메시지도 써 줘" 같은 **끝난 뒤의 다음 일**이다. 에이전트가 멈추려 할 때만 들어간다.

### 3.3 루프는 정책을 모른다: hook으로 주입

`agent-loop.ts` 자체는 상태도 큐도 없고, "언제 멈출지"나 "이 도구를 허용할지" 같은 정책도 모른다. 그런 판단은 모두 설정(`AgentLoopConfig`)으로 받은 콜백에 묻는다.

| 언제 | hook | 예 |
|---|---|---|
| LLM 요청 직전 | `prepareRequest`, `transformContext`, `convertToLlm` | 오래된 메시지 정리, 화면용 메시지 제외 |
| 요청할 때마다 | `getApiKey` | 곧 만료되는 토큰 새로 받기 |
| tool 실행 직전 | `beforeToolCall` | 권한 확인, 위험한 명령 차단 |
| tool 실행 직후 | `afterToolCall` | 결과 가공 |
| turn 끝 | `finishTurn` | "여기서 끝내" 또는 "한 번 더" |
| 다음 turn 전 | `prepareNextTurn` | 대화 요약(compaction), 모델 바꾸기 |

그래서 같은 루프를 coding-agent는 자기 정책으로, 테스트는 가짜 정책으로 돌릴 수 있다.

### 3.4 실패도 대화의 일부다

tool 쪽 실패는 루프를 멈추지 않는다. 아래 경우는 모두 **에러 내용이 담긴 toolResult**가 되어 LLM에 다시 전달되고, 모델이 보고 스스로 고친다. (스스로 고치게 하려는 의도라는 해석은 `추론`이다.)

- 없는 도구 이름
- 인자 형식 오류
- `beforeToolCall`이 차단
- 실행 중 예외

특이한 경우도 하나 있다. 응답이 토큰 한도(`length`)에 걸려 잘렸으면 tool call의 인자도 잘렸을 수 있다. 그래서 **하나도 실행하지 않고** "인자를 온전히 해서 다시 불러라"라는 에러를 돌려준다.

루프가 **즉시 멈추는** 경우는 LLM 응답 자체가 `error`이거나 `aborted`일 때뿐이다. 2.4절의 "throw 대신 stopReason" 규칙 덕분에 루프는 이 한 곳만 확인하면 된다. 재시도는 위층이 `agentLoopContinue`로 한다.

### 3.5 도구는 기본적으로 동시에 실행한다

LLM이 도구 세 개를 한꺼번에 요청하면 이렇게 처리한다.

- **준비는 순서대로 한다.** 권한 확인(`beforeToolCall`) 같은 준비 단계를 요청 순서대로 거친다.
- **실행은 동시에 한다.**
- **결과는 원래 순서대로 대화에 붙인다.** 실행은 끝난 순서가 제각각이어도 대화 속 순서는 흔들리지 않는다.

도구 정의에 `executionMode: "sequential"`이 붙은 도구가 하나라도 섞여 있으면 그 배치는 전부 순차로 실행한다. 이 커밋의 내장 도구(`read`, `bash` 등)에는 그런 표시가 없고, extension이 정의하는 도구가 이 옵션을 쓸 수 있다(`coding-agent/src/core/extensions/types.ts:619`).

### 3.6 이벤트: 바깥에 알리는 방법

루프는 진행 상황을 이벤트로 흘려보낸다. 화면(TUI)과 세션 저장은 이 이벤트만 보고 동작한다.

```
agent_start
  turn_start
    message_start → message_update … → message_end      (LLM 답이 흘러나옴)
    tool_execution_start → (update …) → tool_execution_end
    message_start/end                                   (tool 결과)
  turn_end
  … 다음 turn …
agent_end
```

> 그림: [runLoop 제어 흐름](./diagrams/agent-loop-workflow.html) · [1턴 시퀀스](./diagrams/agent-loop-sequence.html)
> 상세: [Q5](./questions/q5-agent-loop.md)

---

## 4. `Agent` 클래스: 루프에 기억과 손잡이를 붙이기

`agent-loop`은 기억이 없는 함수다. 실제로 쓰려면 대화를 기억하고, 실행 중인지 알고, 중간에 멈추게 할 수 있어야 한다. 그 역할을 `Agent` 클래스가 한다.

### 4.1 상태는 이벤트로만 바뀐다

`Agent`는 루프에 대화의 **복사본**을 넘긴다. 루프가 `message_end` 이벤트를 보내면 그때 자기 대화 목록에 메시지를 추가한다. 대화가 바뀌는 길이 이벤트 하나뿐이다.

그래서 이벤트를 구독하는 화면이나 세션 파일이 `Agent`가 가진 대화와 어긋날 수 없다. 이렇게 설계한 이유는 이 일관성 때문으로 보인다(`추론`).

| 이벤트 | `Agent` 상태 변화 |
|---|---|
| `message_start/update` | `streamingMessage`: 지금 흘러나오는 메시지 (화면의 "입력 중…") |
| `message_end` | 대화 목록에 추가 |
| `tool_execution_start/end` | 실행 중인 도구 목록에서 추가/제거 |
| `turn_end` | 에러가 있으면 `errorMessage` 기록 |

### 4.2 구독자는 하나씩 기다린다

`agent.subscribe(fn)`으로 등록한 구독자는 이벤트마다 **등록한 순서대로, 앞의 것이 끝나야 다음 것**이 호출된다. 구독자가 이벤트를 디스크에 쓰는 데 오래 걸리면 루프도 그만큼 기다린다.

`agent_end` 이벤트가 나왔다고 곧바로 끝난 게 아니다. 그 이벤트의 구독자까지 모두 끝나야 `waitForIdle()`이 풀린다.

### 4.3 한 번에 하나만 실행한다

- 실행 중에 `prompt()`를 또 부르면 에러가 난다. 에러 메시지가 "`steer()`나 `followUp()`을 쓰라"고 안내한다.
- `abort()`는 중단 신호만 보낸다. 실제로 멈추는 것은 신호를 받은 LLM 스트림과 도구들이다.
- 루프 밖에서 예상하지 못한 예외가 나도 `handleRunFailure`가 가짜 error 메시지를 만들어 `message_end → turn_end → agent_end`를 대신 보낸다. 그래서 구독자는 항상 끝까지 정상적인 이벤트 순서를 받는다.

### 4.4 `continue()`: 멈춘 곳에서 다시

- 마지막 메시지가 사용자 메시지나 tool 결과이면(예: 에러로 멈춘 뒤) 그 상태 그대로 LLM에 다시 요청한다. **재시도**가 이 방식이다.
- 마지막이 LLM의 답이면(정상 종료) 쌓인 steering이나 follow-up 메시지로 이어 간다. 둘 다 없으면 에러다.

> 상세: [Q6](./questions/q6-agent-class.md)

---

## 5. coding-agent의 `AgentSession`: hook에 실제 정책을 채우기

3.3절에서 루프는 정책을 모르고 hook에 묻는다고 했다. 그 hook을 실제로 채우는 곳이 coding-agent의 `AgentSession`이다.

### 5.1 대화의 원본은 세션 파일이다

`pi`는 대화를 세션 파일에 저장해 두고, 나중에 이어 하거나 가지를 쳐서(branch) 다른 방향으로 진행할 수 있다. 그래서 대화의 **원본은 세션 파일**이다.

- 루프가 `message_end` 이벤트를 보내면 `AgentSession`이 그 메시지를 세션 파일에 저장한다.
- 매 LLM 요청 직전(`prepareRequest`)에는 루프가 들고 있던 대화를 버린다. 대신 세션 파일에서 "모델에게 보낼 대화"(projection)를 새로 만들어 넣는다.

이렇게 하면 요약(compaction)이나 실패한 시도 숨기기처럼 **세션 파일에서 한 편집**이 다음 요청에 곧바로 반영된다.

### 5.2 hook마다 무엇을 넣나

| hook | 채우는 내용 |
|---|---|
| `streamFn` | `modelRuntime.streamSimple`. 여기서 pi-ai와 연결된다 |
| `convertToLlm` | 화면 전용 메시지를 빼고, 설정에서 이미지를 막았으면 이미지를 "Image reading is disabled."로 바꾼다 |
| `transformContext` | extension이 context를 고칠 기회를 준다. 숨긴 tool 선언을 빼고, 강제 system prompt를 적용한다 |
| `prepareRequest` | 세션 projection으로 교체한다. "자동 선택" 같은 가상 모델이면 이번 요청에 쓸 실제 모델을 고른다 |
| `prepareNextTurn` | 대화가 한도에 가까우면 미리 요약하고, system prompt와 tool 목록을 새로 만든다 |
| `beforeToolCall` / `afterToolCall` | extension의 `tool_call` / `tool_result` 이벤트로 넘긴다. extension이 위험한 명령을 막거나 결과를 고칠 수 있다 |
| `finishTurn` | extension이 "한 턴 더"를 요청할 수 있게 한다 |

hook은 **이어 붙이는(chain)** 방식으로 설치된다. 새 hook이 기존 hook을 `previous...`로 보관했다가 먼저 부르고, 그 결과에 자기 로직을 더한다.

### 5.3 재시도와 요약은 루프 밖에서 한다

agent-loop는 LLM 오류가 나면 바로 끝난다(3.4절). 그 뒤는 `AgentSession`이 이어받는다. `agent.prompt()`가 끝나면 마지막 답을 보고 다시 돌릴지 정한다.

```
agent.prompt("버그 고쳐 줘")
  → 끝난 뒤 마지막 답 확인
     ├─ 일시적 오류 (과부하, rate limit, 서버 오류)
     │    → 2초 → 4초 → 8초 기다렸다가 agent.continue()   (기본 최대 3번)
     ├─ context가 넘침 / 답이 토큰 한도에 잘림
     │    → 대화를 요약(compaction)해서 줄이고 agent.continue()   (딱 1번만)
     ├─ 대기 중인 steering / follow-up 메시지
     │    → agent.continue()
     └─ 없음 → 종료 (agent_settled)
```

재시도에서 볼 점은 네 가지다.

- **context 초과는 재시도하지 않는다.** 같은 요청을 다시 보내도 또 넘치기 때문이다. 대신 요약해서 줄인 뒤 한 번만 다시 시도하고, 그래도 실패하면 "더 큰 모델로 바꾸라"는 에러를 낸다.
- **실패한 시도는 세션 파일에 남긴다.** 다만 모델에게 보내는 projection에서는 뺀다. 기록은 보존하면서 모델이 같은 실패를 다시 보지 않게 하려는 것으로 보인다(`추론`).
- **재시도 횟수는 성공하면 초기화한다.** 긴 작업 중 여기저기서 한 번씩 난 오류가 쌓여서 한도를 넘지 않게 하려는 것이다.
- **재시도할 때 다른 모델로 갈 수 있다.** 가상 모델을 쓰면 `resolveModel(reason: "retry")`로 실패한 모델 대신 다른 모델을 고를 수 있다. 어떤 기준으로 고르는지는 아직 확인하지 않았다.

### 5.4 세 층이 책임을 나누는 방식

| 관심사 | pi-ai | agent-core | coding-agent |
|---|---|---|---|
| 재시도 | "재시도할 만한가" 판정만 | 오류면 멈추고 `continue()` 제공 | 횟수, 대기 시간, 모델 교체 |
| context 한도 | "넘쳤나" 판정만 | 모름 | 요약 후 1회 재시도 |
| tool 권한 | 모름 | `beforeToolCall` 자리만 | extension으로 전달 |
| 대화 저장 | 모름 | 이벤트만 보냄 | 세션 파일이 원본 |

아래층은 **판단 재료와 자리**만 주고, **결정**은 맨 위 제품 층이 한다. 그래서 pi-ai와 agent-core를 다른 제품에 가져가도 그 제품의 정책을 끼울 수 있다(`추론`).

> 그림: [run 이후 재시도·compaction 루프](./diagrams/agent-session-postrun-workflow.html)
> 상세: [Q7](./questions/q7-agent-session-hooks.md)

### 5.5 세션 파일은 고치지 않고 덧붙이기만 한다

5.1절에서 대화의 원본은 세션 파일이라고 했다. 그 파일은 **한 줄에 기록 하나인 JSONL**이고, 이미 쓴 줄은 절대 고치지 않는다. 기록마다 `id`와 부모를 가리키는 `parentId`가 있어서 파일 전체가 **트리**를 이룬다.

```
user "버그 고쳐 줘"
 └ assistant "read 할게요"
    └ toolResult (파일 내용)
       ├ assistant "edit 할게요" …           ← 원래 가지
       └ user "아니, 테스트부터 봐"           ← branch로 새로 뻗은 가지 (leaf)
```

- **가지치기(branch)**: "현재 위치"(leaf)를 과거 기록으로 옮기기만 한다. 그 뒤에 쓰는 기록은 그 지점의 새 자식이 된다. 옛 가지는 파일에 그대로 남는다.
- **요약(compaction)**: 앞부분을 지우지 않는다. `compaction { 요약문, 여기부터는 남겨라(firstKeptEntryId) }` 기록을 하나 **추가**한다.
- **실패한 시도 숨기기**: 그 기록을 지우지 않는다. `context_edit { 대상: 그 기록, 교체: null }` 기록을 하나 **추가**한다.

모델에게 보낼 대화는 LLM 요청 때마다 이 트리를 처음부터 **해석**해서 만든다(`buildSessionProjection`).

1. 현재 leaf에서 부모를 따라 root까지 올라간다. 지금 가지의 기록만 남는다.
2. 가장 최근 compaction을 찾는다. 그 앞은 요약문 하나로 대신하고, `firstKeptEntryId`부터만 남긴다.
3. `context_edit`를 적용한다. `null`이면 빼고, 값이 있으면 내용만 바꾼다.
4. 기록을 메시지로 바꾼다. 요약문이나 extension 메시지 같은 pi 전용 메시지는 `convertToLlm`에서 user 메시지로 바뀐다.

이 방식 덕분에 원래 기록은 항상 복원할 수 있다. 모델이 무엇을 보는지는 "해석 규칙"만 바꿔서 조절한다. (복원이 쉽다는 점이 설계 이유라는 해석은 `추론`이다.)

**compaction은 어디서 자르나**
- **언제**: 대화 토큰이 `context window - 16384`를 넘으면 시작한다.
- **얼마나 남기나**: 최근 약 20000 토큰은 원문으로 둔다.
- **어디서 자르나**: user 메시지나 assistant 메시지 경계에서만 자른다. tool 결과에서 자르면 tool 호출과 결과가 떨어지기 때문에 그렇게 하지 않는다.

> 그림: [세션 파일 → 모델 컨텍스트](./diagrams/session-projection-dataflow.html)
> 상세: [Q8](./questions/q8-session-projection.md)


---

## 6. 전체를 한 번에 보면

사용자가 `pi`에 "버그 고쳐 줘"를 입력했을 때:

```
coding-agent            Agent.prompt("버그 고쳐 줘")
   │                       │  대화 복사본 + hook 묶음
   │                       ▼
agent-core              runLoop ── turn마다 ──► streamFn(model, context)
   │                       │                        │
   │                       │ ◄── 이벤트 스트림 ─────┤
   │                       │ tool call → beforeToolCall → execute → afterToolCall
   │                       │ 이벤트 → Agent 상태 갱신 → 구독자(TUI, 세션 저장)
   ▼                       ▼
ai                      Models.streamSimple → 인증 → provider → api 구현 → LLM 회사
```

층마다 경계가 분명하다.

- **ai**는 "대화 → 답 이벤트"만 안다. 루프도 도구 실행도 모른다.
- **agent-core**는 어느 회사 모델인지 모른다. 주입받은 `streamFn`만 부른다. coding-agent가 `setDefaultStreamFn(streamSimple)`로 둘을 연결한다.
- **coding-agent**는 실제 도구와 정책(hook), 화면을 채운다.

세 층을 관통하는 공통 원칙이 하나 있다. **실패를 예외로 던지지 않고 데이터(stopReason, toolResult의 isError, error 이벤트)로 흘려보낸다.** 그래서 위층은 흐름을 끊지 않고 실패를 보고, 재시도하거나 모델에게 고치게 할 수 있다.

---

## 7. 다음에 볼 것

1. **요약 생성** (`compaction/compaction.ts` `compact`, `generateSummary`): 요약 prompt와 파일 작업 목록(`fileOps`)을 어떻게 쓰는지 본다.
2. **extension 시스템** (`core/extensions/`): 5.2절의 `tool_call`/`tool_result`/`context` 이벤트를 extension이 어떻게 받는지 본다.
3. **독립 부품**: codemode(1.6k줄)와 mcp(3k줄). 작고 설계가 뚜렷하다.

## 검증 수준

- 이 글의 동작 설명은 모두 commit `4259686`의 코드로 확인했다(`코드 확인`). 실행해서 확인한 것은 없다.
- 설계 **의도**(왜 그렇게 했나)에 대한 문장은 `추론`으로 표시했다.
