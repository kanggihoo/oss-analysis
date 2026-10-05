---
title: "Stealable Pattern: Async Event Stream with a Final Result"
created: 2026-10-06
updated: 2026-10-06
type: concept
tags: [architecture, pattern, agent-framework, developer-tools]
sources:
  - reports/pi/ai/03-0-event-stream.md
  - reports/pi/ai/06-call-flow.md
  - artifacts/pi/ai-demos/event-stream-demo.ts
  - artifacts/pi/ai-demos/call-flow-demo.ts
  - repos/pi/packages/ai/src/utils/event-stream.ts
  - repos/pi/packages/ai/src/api/lazy.ts
  - repos/pi/packages/ai/src/api/anthropic-messages.ts
confidence: high
---

# Stealable Pattern: Async Event Stream with a Final Result

스트리밍 응답을 "이벤트를 하나씩 받기"와 "끝나면 완성본 받기"로 **둘 다** 쓰게 하는 객체 설계다. 출처는 [[pi]]의 `EventStream<T, R>`다.

## 구조
```ts
class EventStream<T, R = T> implements AsyncIterable<T> {
    constructor(isComplete: (e: T) => boolean, extractResult: (e: T) => R) { ... }
    push(event: T): void          // 생산자가 넣는다
    end(result?: R): void         // 닫고, 잠든 소비자를 모두 깨운다
    [Symbol.asyncIterator]()      // for await 로 하나씩 꺼낸다
    result(): Promise<R>          // 마지막 이벤트가 오면 채워지는 약속
}
```
- **큐 + 깨우는 열쇠 목록.** 소비자는 큐가 비면 자기 `resolve`를 목록에 맡기고 잠든다. `push`는 잠든 소비자가 있으면 열쇠를 호출해 바로 넘기고, 없으면 큐에 쌓는다. 서로를 직접 부르지 않는다(`event-stream.ts:37-82`).
- **판단 기준을 생성자로 주입**한다: 어느 이벤트가 마지막인가, 거기서 최종 결과를 어떻게 꺼내나. 그래서 범용 클래스로 두고 자식이 `AssistantMessageEvent`/`AssistantMessage`를 정한다(`:91-104`).
- **`result()`는 reject가 없는 약속**이다. 실패도 마지막 이벤트(`error`)의 값으로 채운다.

## 이 구조가 해결하는 문제
1. **즉시 반환.** 생산 함수는 객체를 만들자마자 `return`하고, 안쪽 비동기 함수가 `push`로 채운다(`anthropic-messages.ts:578-902`). 호출한 쪽은 바로 `for await` 할 수 있다.
2. **이벤트와 완성본을 같은 객체에서.** 화면은 `for await`로 실시간 표시, 단발 호출은 `.result()`만 기다리면 된다. `complete()`는 이벤트를 꺼내지 않는다(`models.ts:887-893`).
3. **`return`은 한 번뿐이라서 `push`.** 이미 반환한 뒤 도착하는 값은 객체에 넣는 수밖에 없다.
4. **콜백으로 오는 입력(WebSocket 메시지)을 `yield` 방식으로 바꾸는 일**을 범용으로 한다. legacy Codex의 `parseWebSocket`이 같은 구조를 손으로 다시 구현한다(`openai-codex-responses.ts:1307-1423`).
5. **준비가 비동기일 때 바깥/안쪽 두 객체.** 인증과 코드 로딩이 끝나기 전에 빈 바깥 스트림을 돌려주고, 안쪽 스트림이 생기면 이벤트를 복사한다. 준비 실패는 던지지 않고 `error` 이벤트로 넣는다(`api/lazy.ts:31-56`).

## 실행으로 확인한 동작 (`artifacts/pi/ai-demos/`)
- 소비자가 먼저 시작하면 `waiting=1`로 잠들고, `push`가 열쇠를 꺼내 호출하면 바로 깨어난다.
- 연달아 `push`하면 첫 번째는 깨우고 두 번째부터 큐에 쌓인다(`queue=1`).
- **`result()`는 소비자가 `done` 이벤트를 꺼내기 전에 이미 채워진다.**
- 인증이 없으면 예외가 아니라 `error` 이벤트와 `stopReason=error`가 전달된다(`call-flow-demo`).

## 주의
- 다 쓰기 전까지 큐는 소비되지 않으면 계속 쌓인다(`complete()`처럼 이벤트를 안 꺼내는 사용에서 `추론`).
- `end()`를 결과 없이 부르고 마지막 이벤트도 없었다면 `result()`는 영영 채워지지 않는다(코드 읽기, 해당 경로가 있는지는 `미확인`).
- 이벤트의 `partial`이 **계속 갱신되는 공유 객체**라서 이벤트를 저장해 두면 값이 바뀐다.
- 제너레이터(`async function*`)로도 "올 때마다 받기"는 되지만 `result()`가 없고 첫 `next()` 전에는 시작하지 않는다(JS 규칙). 이벤트와 완성본이 둘 다 필요하고 아무도 안 꺼내도 요청이 나가야 하면 이 패턴이 맞다(이유 해석은 `추론`).

관련: [[pi]], [[pi-ai-provider-api-separation]], [[stealable-pattern-stored-credential-owns-provider]].
