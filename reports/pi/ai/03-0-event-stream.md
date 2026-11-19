# ai 03-0: `utils/event-stream.ts` — 이벤트를 쌓고 하나씩 꺼내 주는 통

> **[2026-11-17 재검증]** `3874b3e98` → `4afe78de` 기준으로 `utils/event-stream.ts`, `api/lazy.ts`, `models.ts`의 `lazyStream` 호출부 diff를 읽고 대조했다(실행 없음, `코드 확인`). 바뀐 것: ① `AssistantMessageEventStream`이 최종 메시지에 `durationMs`(응답 시간)를 붙인다(§2.2) ② `lazyStream`이 observer와 `signal`을 받고, 준비 단계 실패를 `aborted`/`error`로 구분한다(§8.3) ③ `EventStream.done`이 `private`에서 `protected`로 바뀌었다. 본문의 **줄 번호는 이전 SHA 기준**이고 아래 표처럼 밀렸다: `EventStream` `:26`, 생성자 `:35`, `push` `:43-58`, `end` `:60-70`, `[Symbol.asyncIterator]` `:72-84`, `result` `:86-88`, `AssistantMessageEventStream` `:97-131`. `push`·`end`·큐·`waiting` 동작 자체는 diff에 없어 §3~§6과 §7 실험 결과는 그대로다(`FifoQueue`·`push`·`end`·이터레이터 본문을 새 파일에서 다시 읽어 동일함을 확인).

- **기준 commit**: `3874b3e98` / **분석일**: 2026-10-05
- **선행 문서**: [01-types](./01-types.md) (`AssistantMessageEvent`, `AssistantMessage`)
- **이어서 읽을 문서**: [03-1-api-anthropic](./03-1-api-anthropic.md), [03-2-api-openai-responses](./03-2-api-openai-responses.md), [03-4-api-openai-codex-legacy](./03-4-api-openai-codex-legacy.md) (세 문서의 코드 모두 이 스트림 객체를 만들어서 `push`한다)
- **읽은 파일**: `utils/event-stream.ts`(약 125줄 전체), `api/lazy.ts`, `agent/src/agent-loop.ts`(`:385-455`). 줄 번호는 모두 이 commit 기준이다.
- **검증 수준**: 코드 읽기는 `코드 확인`. 이 파일을 그대로 불러서 생산자와 소비자를 돌리는 실험을 했다(`실행 확인`, §7). 실험 스크립트와 출력은 `artifacts/pi/ai-demos/event-stream-demo.ts`, `event-stream-demo.2026-10-05.log`에 있다.

## 0. 이 문서를 먼저 읽는 이유
`stream()`이 돌려주는 것이 `AssistantMessageEventStream`이다. 03-1~03-4의 모든 `push`, `end`, `.result()`, `for await`가 이 클래스의 메서드다. 이 클래스를 모르고 03을 읽으면 `stream.push(...)`가 무엇을 하는지 알 수 없다.

**먼저 정리할 오해 두 가지**
- 이 스트림은 **SSE나 WebSocket 같은 네트워크 연결이 아니다.** 이 파일에는 네트워크 코드가 없다. 이벤트를 쌓아 두는 **메모리 안의 대기열**이다. 네트워크에서 읽는 코드는 `api/*.ts`에 있고, 읽은 결과를 이 객체에 `push`한다.
- `streamSimple`이나 `stream`을 호출했을 때 돌려받는 것은 함수가 아니라 **이 클래스의 객체**다. `return stream(...)`은 `stream`을 호출한 결과를 돌려준다는 뜻이다. 03-1 §1에서 `stream`은 함수 이름이면서 그 안의 변수 이름(`const stream = new AssistantMessageEventStream()`, `anthropic-messages.ts:578`)이기도 하다. 둘을 구분해서 읽어야 한다.

## 1. 한 장 요약
```
생산자 (이벤트를 만드는 쪽)                    소비자 (이벤트를 쓰는 쪽)
 stream.push(event) ───►  [ 대기열 queue ]  ───►  for await (const e of stream)
 stream.end()                waiting 목록         await stream.result()
```
- **생산자**가 `push`로 이벤트를 넣고, **소비자**가 `for await`로 하나씩 꺼낸다.
- 소비자가 꺼낼 이벤트가 없으면 **잠들어서 기다린다.** 기다리는 동안 JavaScript의 다른 코드(생산자 포함)가 실행된다.
- 마지막 이벤트(`done` 또는 `error`)가 오면 `.result()`가 최종 `AssistantMessage`를 돌려준다.

## 2. 선언: `EventStream<T, R = T>` (`:25`)
```ts
export class EventStream<T, R = T> implements AsyncIterable<T>
```
| 부분 | 뜻 |
|---|---|
| `class` | 데이터와 메서드를 함께 가진 객체의 설계도 |
| `<T, R = T>` | **제네릭**: 클래스를 쓸 때 정하는 타입. `T`는 이벤트 하나의 타입, `R`은 마지막에 돌려줄 최종 결과의 타입. `= T`는 `R`을 안 정하면 `T`와 같다는 기본값 |
| `implements AsyncIterable<T>` | "`for await`로 `T`를 하나씩 꺼낼 수 있다"고 TypeScript가 검사해 달라는 선언. **능력 자체는 §5의 `[Symbol.asyncIterator]` 메서드가 준다.** |

### 2.1 실제로 쓰이는 형태 (`:91-104`)
```ts
export class AssistantMessageEventStream extends EventStream<AssistantMessageEvent, AssistantMessage> {
    constructor() {
        super(
            (event) => event.type === "done" || event.type === "error",   // isComplete
            (event) => {                                                   // extractResult
                if (event.type === "done") return event.message;
                else if (event.type === "error") return event.error;
                throw new Error("Unexpected event type for final result");
            },
        );
    }
}
```
| | 정해진 값 |
|---|---|
| `T` | `AssistantMessageEvent` (01 §2.7의 12종 이벤트) |
| `R` | `AssistantMessage` (완성된 답) |

자식 클래스의 생성자는 인자가 없다. 그래서 사용하는 쪽은 `new AssistantMessageEventStream()`만 쓴다. 부모 `EventStream`은 범용이라 "어느 이벤트가 마지막인가"를 스스로 모르므로, 자식이 `super(...)`로 판단 기준을 함수로 넘겨 준다.


### 2.2 [2026-11-17] 자식 클래스가 응답 시간을 잰다 (`event-stream.ts:90-131`)
이전 SHA의 자식 클래스는 생성자만 있었다. 지금은 `push`와 `end`를 덮어써서(`override`) **최종 `AssistantMessage`에 `durationMs`를 붙인다**(커밋 `36a686ee8` "record response, tool execution, and durable task times", `f284a2460`).
```ts
readonly #startedAt = Date.now();                    // 벽시계 시각
readonly #startedAtMonotonic = performance.now();    // 단조 시계(시스템 시간 조정에 영향 없음)
push(event) { if done → #time(event.message); else if error → #time(event.error); super.push(event) }
end(result?) { if (result !== undefined) #time(result); super.end(result) }
#time(message) {
  if (this.done || message.durationMs !== undefined || message.timestamp < this.#startedAt) return;
  message.durationMs = max(0, round(performance.now() - this.#startedAtMonotonic));
}
```
- **언제 붙나**: `done`/`error` 이벤트를 `push`할 때, 또는 결과를 넘겨 `end(result)`할 때. 이미 `done`이면(`this.done`) 건너뛴다.
- **언제 안 붙나**(주석 `:90-95`, `:127`): 메시지에 이미 `durationMs`가 있을 때, 또는 `message.timestamp`가 이 스트림 생성 시각보다 이를 때. 즉 **다른 곳에서 시작된 응답을 전달만 하는 스트림**은 시간을 재지 않는다. 예: 나중에 `fetchDeferred`로 가져온 응답.
- **A→B→C 세 스트림(§8.1)에서의 결과**: 가장 안쪽 A가 `done`을 `push`할 때 메시지에 `durationMs`를 쓴다. 같은 메시지 객체가 B, C로 전달되므로 B·C에서는 `durationMs !== undefined`라 다시 재지 않는다(`추론`: 객체를 복사하지 않고 같은 참조를 `push`한다는 것은 `forwardStream`이 `event.message`를 그대로 넘기는 코드로 확인, `lazy.ts:49-53`. 세 스트림 실행은 하지 않았다).
- **타입**: `AssistantMessage.durationMs?: number`(`types.ts:623`). 주석: `timestamp`부터 응답이 끝날 때까지 단조 시계로 잰 밀리초, 옛 메시지나 나중에 가져온 결과에는 없음. `ToolResultMessage`에도 같은 이름 필드가 있고(`types.ts:663`) 이것은 도구 실행 시간이다(agent 02 §7.5).
- 이 시간이 `coding-agent`에서 쓰이는 곳은 `core/agent-session.ts:1446`(도구 이벤트의 `durationMs` 전달)과 `core/tools/render-utils.ts:160`(`Took …` 표시)를 확인했고, 응답 시간(`AssistantMessage.durationMs`)을 쓰는 곳은 찾지 않았다(`미확인`).

## 3. 생성자: 함수 두 개를 받는다 (`:34-39`)
```ts
constructor(isComplete: (event: T) => boolean, extractResult: (event: T) => R) {
    this.isComplete = isComplete;
    this.extractResult = extractResult;
    this.finalResultPromise = new Promise((resolve) => {
        this.resolveFinalResult = resolve;
    });
}
```
- **함수를 값으로 넘길 수 있다.** `(event: T) => boolean`은 "`T`를 받아서 `boolean`을 돌려주는 함수"의 타입이다. 나중에 `push`가 이 함수를 호출한다(**콜백**).
  - `isComplete(event)`: 이 이벤트가 마지막인가?
  - `extractResult(event)`: 마지막 이벤트에서 최종 결과를 어떻게 꺼내는가?
- **`new Promise((resolve) => { this.resolveFinalResult = resolve; })`**: Promise는 "나중에 값이 채워질 약속"이다. 안쪽 함수는 만들자마자 즉시 한 번 실행되고 `resolve`(채우는 열쇠)를 받는다. 여기서는 열쇠를 **바로 쓰지 않고 객체 필드에 보관**해 둔다. 나중에 `push`나 `end`가 부른다. 만드는 곳(생성자)과 채우는 곳(`push`/`end`)이 다르기 때문이다.
- 선언부의 `!`(`resolveFinalResult!`, `:31`)는 "생성자에서 반드시 채우니 TypeScript는 오류를 내지 말라"는 표시다.

## 4. 클래스가 가진 것 (`:25-35`)
| 필드 | 역할 |
|---|---|
| `queue` | 아직 안 꺼낸 이벤트의 **대기열** (`FifoQueue`, 먼저 들어온 것이 먼저 나가는 구조) |
| `waiting` | 이벤트가 없어서 **잠든 소비자들이 맡겨 둔 열쇠(`resolve`)의 목록** |
| `done` | 끝났는지 여부. **[2026-11-17]** `private` → `protected`(자식이 `#time`에서 읽으려고) |
| `finalResultPromise` | `.result()`가 돌려줄 최종 결과의 약속 |
| `isComplete`, `extractResult` | 생성자에서 받은 두 함수 |

## 5. 세 가지 동작

### 5.1 `push(event)`: 이벤트를 넣는다 (`:37-52`)
```ts
push(event: T): void {
    if (this.done) return;                                    // ①
    if (this.isComplete(event)) {                             // ②
        this.done = true;
        this.resolveFinalResult(this.extractResult(event));
    }
    const waiter = this.waiting.dequeue();                    // ③
    if (waiter) {
        waiter({ value: event, done: false });                // ④
    } else {
        this.queue.enqueue(event);                            // ⑤
    }
}
```
1. 이미 끝났으면 무시한다. `done`/`error` 뒤에 늦게 온 이벤트가 섞이지 않게 한다.
2. 마지막 이벤트이면 `done = true`로 하고, 최종 결과를 꺼내 `.result()`의 약속을 채운다. **이 이벤트도 아래로 계속 내려가 소비자에게 전달된다**(`return`하지 않는다). 소비자는 `done` 이벤트도 받는다.
3. 잠든 소비자가 있는지 확인한다.
4. 있으면 그 소비자의 열쇠를 `{ value: event, done: false }`로 호출한다. 열쇠가 채우는 Promise는 소비자가 `await`하고 있던 것이라, 호출 즉시 소비자가 이어서 실행될 준비가 된다. `done: false`는 "끝이 아니고 이것이 다음 값"이라는 표준 형식이다.
5. 없으면 대기열에 쌓는다.

소비자는 대기열이 비었을 때만 잠든다. 그래서 잠든 소비자가 있으면 대기열은 비어 있다. 4번이 대기열을 건너뛰어도 **순서는 유지된다.**

### 5.2 `end(result?)`: 닫는다 (`:54-63`)
```ts
end(result?: R): void {
    this.done = true;
    if (result !== undefined) this.resolveFinalResult(result);
    while (this.waiting.length > 0) {
        const waiter = this.waiting.dequeue()!;
        waiter({ value: undefined as any, done: true });
    }
}
```
- `done = true`로 하고, 결과를 받았으면 `.result()`의 약속을 채운다.
- **잠든 소비자를 모두 깨운다.** `done: true`는 "더 값이 없다, 반복을 끝내라"는 뜻이다. 이벤트가 더 안 올 스트림에서 소비자가 영영 잠들지 않게 한다.
- 대기열은 비우지 않는다. 남은 이벤트는 소비자가 계속 꺼낼 수 있다.
- **주의**: `end()`를 결과 없이 부르고, 그전에 `done`/`error` 이벤트도 `push`하지 않았다면 `.result()`의 약속은 영영 채워지지 않는다. 코드를 읽고 알게 된 성질이고, 실제로 그런 경로가 있는지는 확인하지 않았다(`미확인`). 이 코드베이스의 호출들은 `push(done|error)` 뒤에 `end()`(03-1 `:887-888`, `:897-898`)이거나 `end(await source.result())`(`lazy.ts:38`)이다.

### 5.3 `async *[Symbol.asyncIterator]()`: `for await`가 쓰는 메서드 (`:65-82`)
```ts
async *[Symbol.asyncIterator](): AsyncIterator<T> {
    while (true) {
        if (this.queue.length > 0) {                          // ①
            yield this.queue.dequeue()!;
        } else if (this.done) {                               // ②
            return;
        } else {                                              // ③
            const result = await new Promise<IteratorResult<T>>((resolve) => this.waiting.enqueue(resolve));
            if (result.done) return;                          // ④
            yield result.value;                               // ⑤
        }
    }
}
```
- **`async *`는 비동기 제너레이터**다. `yield 값`으로 값을 하나 내보내고, 다음 값이 요청될 때까지 그 자리에서 일시 정지한다.
- 이 메서드를 **코드에서 직접 부르는 곳은 없다.** `for await (const e of stream)`을 쓰는 순간 JavaScript가 자동으로 호출한다.
- 각 분기:
  1. 대기열에 이벤트가 있으면 하나 꺼내서 `yield`한다.
  2. 대기열이 비었고 `done`이면 `return`(반복 종료).
  3. 대기열이 비었고 아직 안 끝났으면 **잠든다.** 새 Promise를 만들고 그 열쇠를 `waiting`에 넣고 `await`로 멈춘다.
  4. 깨어났는데 `done: true`이면(`end()`가 깨운 경우) 반복을 끝낸다.
  5. 깨어났는데 값이면(`push`가 준 경우) `yield`한다.
- **①이 ②보다 먼저**다. 스트림이 `done`이어도 대기열에 남은 이벤트가 있으면 먼저 다 꺼낸다. 그래서 마지막 `done` 이벤트도 놓치지 않는다.

### 5.4 `result()` (`:86-88`)
생성자에서 만든 `finalResultPromise`를 돌려준다. 마지막 이벤트가 `push`되거나 `end(결과)`가 불릴 때 채워진다. **`resolve`만 있고 `reject`는 없으므로 이 약속은 실패하지 않는다.** 오류도 `error` 이벤트의 `AssistantMessage`(`stopReason: "error"`)로 채워진다. 01/02에서 정리한 "`.result()`는 reject하지 않는다"의 근거가 이 구조다.

## 6. 기다리고 깨우는 원리: 두 코드가 `waiting` 목록으로 만난다
`push`가 열쇠를 부르는 곳과 소비자가 `await`하는 곳은 **서로 다른 위치의 코드**다. 둘은 서로를 모르고, `waiting` 목록만 공유한다.

```
[소비자 코드] asyncIterator ③                       [공용 목록]            [생산자 코드] push ③④
 await new Promise((resolve) =>                    waiting
        this.waiting.enqueue(resolve))   ───────►  [resolve]  ◄──────   const waiter = this.waiting.dequeue()
 ↑ 열쇠를 목록에 넣고 await로 멈춤                                          waiter({ value: event, done: false })
                                                                           ↑ 목록에서 열쇠를 꺼내 호출 → 소비자의 Promise가 채워짐
 ↓ 채워지면 await 아래로 이어서 실행 → yield result.value
```

### 6.1 왜 "기다리는 동안 다른 코드가 실행"되는가
- JavaScript는 **스레드 하나**로 코드를 실행하고, 한 코드가 끝나거나 `await`로 양보해야 다음 코드가 실행된다.
- 소비자가 `await`에서 멈추면 스레드를 양보한다. 그동안 생산자(예: 서버 응답을 읽는 코드)가 실행되어 `push`를 한다.
- 만약 소비자가 동기 반복문으로 값을 기다린다면 스레드를 붙잡고 있어서, 값을 만드는 생산자가 실행될 기회를 못 얻고 영원히 끝나지 않는다. `for await`는 이 문제를 피한다.
- 일반 `for...of`는 값이 **이미 다 있는** 것을 순회하고, `for await...of`는 값이 **나중에 도착하는** 것을 순회한다.

## 7. 실험: 실제 코드로 확인 (`실행 확인`)
`event-stream.ts`를 그대로 불러서 소비자는 `for await`로, 생산자는 시간 간격을 두고 `push`하게 했다(`artifacts/pi/ai-demos/event-stream-demo.ts`). `waiting`과 `queue`의 길이를 같이 찍었다.

```
[+  0ms] 소비자: for await 시작
[+  2ms] 메인: consumer() 호출 직후. 소비자는 이미 멈춰 있음 (waiting=1 ← 소비자의 열쇠가 들어 있음)
[+103ms] 생산자: push(start)
[+103ms] 소비자: 'start' 이벤트를 받음   (waiting=0, queue=0)
[+202ms] 생산자: push(text_delta) 를 연속 2번
[+202ms] 생산자: 두 번 push 직후  (waiting=0, queue=1)  ← 소비자가 아직 못 꺼낸 이벤트가 쌓임
[+202ms] 소비자: 'text_delta' 이벤트를 받음   (waiting=0, queue=1)
[+203ms] 소비자: 'text_delta' 이벤트를 받음   (waiting=0, queue=0)
[+303ms] 생산자: push(done)
[+304ms] result() 가 채워짐: stopReason=stop
[+304ms] 소비자: 'done' 이벤트를 받음   (waiting=0, queue=0)
[+304ms] 소비자: for await 종료
```
읽는 법
- `[+2ms]` `waiting=1`: 소비자가 시작했지만 이벤트가 없어서 열쇠를 맡기고 잠들었다. **"기다린다"는 이 상태다.**
- `[+103ms]` `waiting`이 1에서 0으로: `push`가 열쇠를 꺼내 호출했고, 소비자가 바로 `start`를 받았다.
- `[+202ms]` `queue=1`: 생산자가 `push`를 **연달아 두 번** 했다. 첫 번째는 열쇠를 호출해 소비자를 깨울 준비만 했고(소비자는 생산자의 현재 코드가 끝난 뒤에야 이어서 실행된다), 두 번째는 `waiting`이 비어 대기열에 쌓였다. 곧이어 소비자가 첫 번째를 받고 반복을 이어서 대기열의 두 번째를 꺼냈다.
- `[+304ms]` `result()`가 `done` 이벤트를 소비자가 받기 **전에** 채워졌다. `push`의 ②가 이벤트를 소비자에게 넘기기 전에 최종 결과를 먼저 채우기 때문이다.

## 8. 실제 코드에서 누가 `push`하고 누가 `for await`하는가

| 역할 | 위치 | 코드 |
|---|---|---|
| **생산자** | `api/anthropic-messages.ts`의 `stream()` 안쪽 비동기 함수 | `stream.push({ type: "start", ... })` (`:942`), `done`(`:1166`), `error`(`:1171`) (`4afe78de` 기준. 이전 SHA는 `:660`, `:887`, `:897`) |
| **생산자** | `api/openai-codex-responses.ts`의 `stream()` | 같은 방식. 단 응답 변환은 공용 `processResponsesStream`이 `stream.push`를 호출한다 (03-2 §5, 03-4 §7) |
| **중간 소비자 + 생산자** | `api/lazy.ts:42-58` `forwardStream` | `for await (const event of source) { target.push(event); observer?.onEvent?.(event); ... }` 후 결과를 모아 `target.end(result)` (§8.3) |
| **최종 소비자** | `agent/src/agent-loop.ts:424` | `for await (const event of response) { switch (event.type) ... }`, 완료 시 `await response.result()` (`:419`의 `result` 함수. 이전 SHA는 `:409`, `:414`, `:445`) |

`forwardStream`은 한 스트림에서 `for await`로 읽어서 다른 스트림에 `push`하므로 소비자이면서 생산자다.

### 8.1 한 요청에서 스트림은 세 개이고, 두 번 복사된다
`Models.streamSimple`을 부르는 경우의 그림이다(`lazyStream`이 두 군데에서 쓰이기 때문. 02 §2.3, §4.3).
```
 A  anthropic-messages.ts의 stream()이 만든 스트림
      ▲ push      ← 서버 응답(SSE)을 pi 이벤트로 바꿔 넣는 생산자
      │ for await ← lazyApi의 forwardStream (소비자)
      ▼
 B  lazyApi(api/lazy.ts)가 만든 스트림
      ▲ push      ← 위 forwardStream
      │ for await ← Models.stream의 forwardStream (소비자)
      ▼
 C  Models.stream(models.ts)이 만든 스트림  ← 호출한 쪽이 받는 스트림
      ▲ push      ← 위 forwardStream
      │ for await ← agent-loop.ts:424 (최종 소비자)
```
- 이 그림은 `agent-loop`의 `streamFunction`이 `Models.streamSimple`일 때의 구성이다. 어느 함수가 연결되는지는 `coding-agent`의 설정에 달려 있고(00 §5), 이 문서에서는 확인하지 않았다.
- 코드의 `lazyStream`에는 `outer`(자기가 만들어 돌려주는 스트림)와 `inner`(`setup()`이 돌려준 스트림)라는 변수가 있다. "inner"는 `stream()` 함수의 이름 때문이 아니라 `lazyStream` 입장에서 **"내가 만들지 않은, 나중에 받는 스트림"**을 가리키는 이름이다. 위 그림에서 B는 C를 만든 `lazyStream`에게 inner이고, A는 B를 만든 `lazyStream`에게 inner다. 그래서 inner는 상대적인 이름이다.

### 8.2 `agent-loop`가 이벤트를 받는 모습 (`agent-loop.ts:403-455`, 줄 번호는 이전 SHA 기준. 현재는 `:412-424` 근처, 호출에 `identity`가 추가됨 — agent 02)
```ts
const response = await streamFunction(config.model, llmContext, { ...config, apiKey, signal });
const result = async () => Object.assign(await response.result(), { thinkingLevel: ... });
for await (const event of response) {
    switch (event.type) {
        case "start": ...                            // 빈 partial을 대화 기록에 추가
        case "text_delta" 등 9종: ...                 // partial을 갱신하고 message_update 이벤트를 내보냄
        case "done": case "error": {
            const finalMessage = await result();     // 최종 AssistantMessage를 받아 기록을 교체
            ...
```
`agent`는 이 스트림이 `AssistantMessageEventStream`이라는 사실만 이용하고, 어느 회사의 응답인지는 모른다. 이 부분은 `agent` 패키지를 읽을 때 자세히 본다.

### 8.3 [2026-11-17] `lazyStream`의 변화 (`api/lazy.ts:42-93`)
- **관찰자(observer)**: `lazyStream(model, setup, observer?, signal?)`. `LazyStreamObserver { onEvent?, onResult? }`는 주석에 따르면 "기존 전달 경로를 동기적으로 읽기만 보는" 용도다(`:35`). `forwardStream`이 이벤트를 `target.push`한 직후 `observer.onEvent`를 부르고, 끝나면 `observeResult`가 `onResult`를 **한 번만** 부른다(`observedResult` 플래그, `:72-77`). `Models.stream`·`streamSimple`은 `observeModelRequest(model, options, false)`를 넘긴다(`models.ts:933-945` 근처). `observeModelRequest`(`telemetry.ts:121-`)는 요청 하나를 텔레메트리 span으로 감싸 첫 청크 시간, 블록별 글자 수, 최종 토큰·비용을 기록한다(02 §4.3).
- **결과 수집**: 이전은 `target.end(hasResult(source) ? await source.result() : undefined)`였다. 지금은 루프 중 `done`/`error` 이벤트의 메시지를 `result`에 잡아 두고, 소스에 `result()`가 있으면 그것으로 덮어쓴 뒤 `target.end(result)`한다(`:48-58`). 소스에 `result()`가 없어도 이벤트에서 얻은 결과를 `end`에 넘긴다는 점이 달라졌다.
- **준비 단계 실패의 구분**: `setup()`(인증, provider 로드)이 던지면 이전에는 항상 `reason: "error"`였다. 지금은 `signal?.aborted`이면 `"aborted"`, 아니면 `"error"`이고, 메시지의 `stopReason`과 `timestamp`(= `lazyStream` 진입 시각)가 거기에 맞춰진다(`:83-89`, `createSetupErrorMessage`). 취소된 요청이 오류로 보고되지 않는다(CHANGELOG v1.5.1 "cancellation during lazy provider loading ... reported as an error instead of an abort").
- **`lazyApi`**: `stream`·`streamSimple`·`fetchDeferred`가 `options?.signal`을 `lazyStream`에 넘긴다.
- 이 준비 단계 실패 메시지의 `timestamp`는 `lazyStream`이 `outer`를 만들기 직전에 잡은 `startedAt`이다(`:71`). `AssistantMessageEventStream`은 그 바로 뒤에 `#startedAt`을 잡으므로, `timestamp`가 1ms라도 이르면 `#time`이 `message.timestamp < this.#startedAt`로 보고 `durationMs`를 붙이지 않는다(`추론`, 두 `Date.now()`가 같은 ms면 붙는다. 실행하지 않음).

## 9. 한 줄씩 정리
- `EventStream<T, R>`: 이벤트(`T`)를 쌓아 두고 하나씩 꺼내 주며, 끝나면 최종 결과(`R`)를 주는 통.
- 생성자는 "마지막 이벤트 판단 함수"와 "결과 꺼내는 함수"를 받고, 결과를 담을 약속(Promise)과 그것을 채울 열쇠를 만든다.
- `push`는 이벤트를 넣는다. 잠든 소비자가 있으면 열쇠로 깨우고, 없으면 대기열에 쌓는다.
- `for await`는 대기열에서 꺼내고, 비었으면 열쇠를 `waiting`에 맡기고 잠든다.
- 생산자와 소비자는 서로를 직접 부르지 않고 `queue`와 `waiting`으로만 만난다.
- `AssistantMessageEventStream`은 최종 메시지에 응답 시간 `durationMs`를 붙인다(§2.2, 2026-11-17).
- 이 객체는 네트워크 연결이 아니라 메모리 안의 대기열이고, 한 요청에서 A, B, C 세 개가 이어져 두 번 복사된다.

## 10. 읽지 않은 것 (`미확인`)
- `FifoQueue`(`:3-23`)의 구현 세부(두 배열로 앞에서 꺼내기를 효율적으로 하는 구조로 보이나 이 문서의 이해에 필요하지 않아 생략)
- `agent` 패키지가 이 스트림을 소비하는 전체 흐름 (agent 단계에서)
