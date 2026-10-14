---
title: e2e (tester-army)
type: project
updated: 2026-10-14
---

# e2e (tester-army)

웹·모바일 E2E 테스트 프레임워크. 테스트 안에서 `agent.act('자연어 목표')`로 LLM 에이전트가 앱을 조작하고, 결과는 locator/`expect`로 검증한다. 기준 commit `dbdec70` (2026-10-14). 초기 분석이며 빌드·실행은 하지 않았다.

## 핵심 설계 (코드 확인)
- **replay cache**: `act` 단계의 행동을 기록해 두었다가, 뒤따르는 검증이 통과한 경우에만 저장한다. 다음 실행은 모델 호출 없이 재생하고, 어긋나면 그 지점부터 모델이 이어받는다. 재생 실패는 에러가 아닌 miss다 (`agent/act.ts` `dispatchStep`, `agent/step-cache.ts` `begin`, `cache/decide.ts`).
- **act만 캐시**: assert는 상태를 바꾸지 않으므로 trace가 비어 캐시하지 않는다.
- **교체 가능한 두 경계**: 모델 루프는 `StepExecutor`(`agent/executor.ts`), 앱 조작은 `Engine` SPI(`engine/contract.ts`) 뒤에 있다. 웹(Playwright)·모바일(agent-device)·호스팅 환경이 별도 패키지다.
- **`cache.strict`**: 낡은 recording을 모델에 넘기지 않고 `REPLAY_STALE`로 실패시켜 CI에서 재기록을 리뷰 대상으로 만든다.
- **저장소**: `.e2e/cache/` 파일 하나/키, atomic rename, lock 없음.

## 상세
- [overview](../../reports/e2e/overview.md), [구조도](../../reports/e2e/diagrams/structure.html), [act 실행 흐름](../../reports/e2e/diagrams/flow.html), [next](../../reports/e2e/next.md)

## 미확인
cache key 구성, 요소 재탐색 방식, runner↔worker IPC, 모델 프롬프트와 도구, 실제 실행.
