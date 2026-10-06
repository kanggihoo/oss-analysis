---
title: "Stealable Pattern: Hook-Injected Loop with a Throw Contract"
created: 2026-10-06
updated: 2026-10-06
type: concept
tags: [architecture, pattern, agent-framework, developer-tools]
sources:
  - reports/pi/agent/02-agent-loop.md
  - reports/pi/agent/03-agent-class.md
  - reports/pi/agent/05-call-flow.md
  - artifacts/pi/agent-demos/agent-flow-demo.ts
  - repos/pi/packages/agent/src/agent-loop.ts
  - repos/pi/packages/agent/src/agent.ts
  - repos/pi/packages/agent/src/types.ts
confidence: high
---

# Stealable Pattern: Hook-Injected Loop with a Throw Contract

"AI에게 묻기 → 도구 실행 → 다시 묻기"를 도는 에이전트 루프를 **정책 없이** 만들고, 정책은 훅으로 바깥에서 주입하며, **누가 throw해도 되는지를 훅마다 정해 두는** 설계다. 출처는 [[pi]]의 `agent` 패키지다.

## 구조 세 층
1. **루프(`runLoop`)**: 상태가 없다. 입력은 context 스냅샷과 `AgentLoopConfig`(훅 묶음), 출력은 이벤트 스트림. 재시도, 압축, 권한 확인, 큐는 모두 훅 뒤에 있다(`agent-loop.ts:163`).
2. **래퍼(`Agent`)**: 대화 기록, 큐, 실행 잠금, 구독자를 갖는다. 루프에 **복사본**을 넘기고, 루프가 내보내는 **이벤트로만** 자기 상태를 갱신한다(`agent.ts:460`, `:565`).
3. **호스트(coding-agent 등)**: 훅을 채워 넣어 재시도, 압축, 승인 정책을 만든다.

## throw 계약이 비대칭이다 (핵심)
| 훅 | throw 하면 | 근거 |
|---|---|---|
| 도구 `execute`, `prepareArguments`, `beforeToolCall`, `afterToolCall`, 스키마 검증 | **루프가 흡수**해서 `isError: true` 도구 결과로 바꿈 → AI가 스스로 고칠 기회 | `agent-loop.ts:724-775`, `:841-847`, `:892-895` |
| `convertToLlm`, `transformContext`, `getApiKey`, 큐 훅, `finishTurn`, `prepareRequest`, `prepareNextTurn`, `StreamFn` | **금지**(계약). 어기면 루프가 reject | `types.ts` 주석, 루프에 try/catch 없음 |
| 위를 어겼을 때 | **래퍼가 안전망**: 가짜 error 메시지로 `message_start/end → turn_end → agent_end`를 대신 내보내고 잠금을 해제 | `agent.ts:532-548` |

- 이유(`추론`): 도구 실패는 모델의 입력으로 돌려줄 수 있는 정상 흐름이고, 변환/키 해석 실패는 모델이 고칠 수 없다. 앞의 것만 루프가 책임진다.
- 실행 확인: `convertToLlm`이 throw해도 구독자는 정상 종료와 같은 모양의 이벤트를 받았고 `isStreaming`은 `false`로 돌아왔다(`reports/pi/agent/05` §3.2).

## 가져다 쓸 때의 주의
- **안전망은 래퍼에만 있다.** 루프 함수를 직접 쓰는 `agentLoop`(스트림 반환판)는 reject를 처리하지 않아 스트림이 끝나지 않는다(05 H1). 루프만 노출하지 말고 래퍼를 통해 쓰게 하거나 `.catch`를 붙인다.
- **스냅샷 입력 + 이벤트 출력**이면 상태가 어긋날 일이 적지만, 훅이 context를 **교체**하면 이벤트가 안 나가 래퍼의 상태에 반영되지 않는다(`추론`, 압축 훅 설계 때 확인 필요).
- 래퍼는 config를 **run 시작 때 복사**한다. 실행 중 설정 변경은 다음 run부터 적용된다(05 G). 필요하면 `prepareNextTurn` 같은 훅으로 run 안에서 바꾼다.

## 관련
[[pi-agent-turn-end-decision-priority]], [[stealable-pattern-async-event-stream-with-final-result]]
