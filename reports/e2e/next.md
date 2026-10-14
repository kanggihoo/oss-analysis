# e2e — 다음 세션 메모

- **분석 SHA**: `dbdec7088693d9d91f771ea4b6fad2e838e209c0` (2026-10-14, clean, shallow clone depth 50)
- **확인한 범위**: `agent/act.ts`(dispatch 전체 흐름), `agent/step-cache.ts`(`begin`, `conclude`, `failIfStale`), `cache/decide.ts`, `cache/store.ts` 머리 주석, `agent/tool-loop.ts` 진입부, `run/runner.ts` 시작부, `run/worker/entry.ts` 머리, `engine/contract.ts`·`surface.ts` 머리, 문서 `core-concepts.mdx`·`cache.mdx`.
- **실행한 것**: 없음 (설치·테스트·모델 호출 안 함).

## 남은 질문 (우선순위)
1. cache key 구성 → `cache/identity.ts`, `cache/context.ts`
2. replay와 요소 재탐색 → `agent/replay.ts` `replayTrace`/`verifyEndState`, `cache/relocate.ts`, `cache/anchors.ts`
3. 저장 확정 시점 → `cache/context.ts` `settleStagedTraces`, `run/execute.ts` 949행 부근 `createAgentCacheContext`
4. 모델이 보는 정보와 행동 문법 → `agent/observation.ts`, `agent/primitives.ts`, `agent/prompts.ts`
5. runner ↔ worker → `run/worker/protocol.ts`, `run/scheduler.ts`

## 실행 실험 후보 (비용 확인 후)
- 모델 호출 없는 locator 테스트와 `examples/with-vite`를 `pnpm install` 후 실행. 의존성 설치가 필요하므로 사용자 확인 필요.
- 캐시 동작은 모델 키가 필요하다 (`docs/subscriptions.mdx` 참고, 구독 모드 여부 확인).

## 참고
- 이 clone은 `--depth 50`이다. 변경 이력 분석이 필요하면 `git fetch --unshallow`.
