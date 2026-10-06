---
title: "pi Agent: Who Decides to End or Continue a Turn"
created: 2026-10-06
updated: 2026-10-06
type: concept
tags: [architecture, agent-framework, developer-tools]
sources:
  - reports/pi/agent/02-agent-loop.md
  - reports/pi/agent/05-call-flow.md
  - artifacts/pi/agent-demos/agent-flow-demo.ts
  - repos/pi/packages/agent/src/agent-loop.ts
  - repos/pi/packages/agent/src/types.ts
confidence: high
---

# pi Agent: Who Decides to End or Continue a Turn

[[pi]]의 에이전트 루프에서 "계속할지 끝낼지"를 정하는 곳은 **여럿**이고 우선순위가 있다. 여러 종료 신호를 한 루프에서 섞을 때의 참고 사례다. 모두 `agent-loop.ts:245-318`(코드 확인)이고 05에서 가짜 `streamFn`으로 실행 확인했다.

| 순위 | 신호 | 효과 | 실행 확인 |
|---|---|---|---|
| 1 | AI 응답 `stopReason`이 `error`/`aborted` | `finishTurn`은 호출하되 **반환값을 버리고** 즉시 종료 | `finishTurn`이 `continue`를 줘도 요청 1회로 끝 |
| 2 | `finishTurn`이 `{action:"end"}` | 큐를 보지 않고 종료 | follow-up이 큐에 **남은 채** 종료 |
| 3 | 도구 결과가 **전부** `terminate: true` | 도구 때문에 계속할 필요 없음 | 하나라도 아니면 계속 |
| 4 | steering 메시지 있음 | 계속 (턴마다 `drain`) | |
| 5 | follow-up 메시지 있음 | 멈추려는 순간에만 확인, 있으면 계속 | |
| 6 | `finishTurn`이 `{action:"continue"}` | 위 3~5가 **하나도 없을 때만** 한 턴 강제 | 도구 호출이 있었던 턴에는 요청이 추가되지 않음 |
| 7 | 그 외 | 종료 | |

## 읽을 때 주의
- `terminate`는 "실행 종료"가 아니라 "이번 도구 때문에는 계속하지 않음"이다. steering이 있으면 계속된다.
- `continue`는 "무조건 한 번 더"가 아니라 **"다음 요청이 최소 1개 있게 보장"**이다. 다른 이유로 이미 계속되면 중복되지 않는다.
- `stopReason: "length"`로 잘린 응답은 도구를 **하나도 실행하지 않고** 에러 결과로 돌려 AI가 다시 호출하게 한다(인자가 불완전하지만 파싱·검증은 통과할 수 있어서, `agent-loop.ts:264-270`).
- 가장 센 규칙(1)은 호스트 훅으로도 못 이긴다. 재시도가 루프 밖(`coding-agent`)에 있는 것은 이 때문으로 `추론`한다(coding-agent 구현은 아직 확인 전).

관련: [[stealable-pattern-hook-injected-loop-with-throw-contract]]
