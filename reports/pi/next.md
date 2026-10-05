# Next Session Plan: pi

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `3874b3e98983c70fa05fa193b675d42cfcb8b9f8` (2026-10-02, worktree clean)
- **작성/갱신 일자**: `2026-10-06`
- **이전 기준 SHA**: `4259686d9290c0d73ae7192b796aee3e530a9779` (Q1~Q8과 learning-guide, 다이어그램이 이 기준)

---

## 1. 이번 세션에서 확인한 범위

- [x] **`ai` 패키지 전체 흐름** (최신 commit 기준): [`ai/`](./ai/) 문서 13개
  - [00-role](./ai/00-role.md) 역할과 의존 관계 · [01-types](./ai/01-types.md) 타입 · [02-models-registry](./ai/02-models-registry.md) `Models`/`Provider`/모델 데이터
  - [03-0-event-stream](./ai/03-0-event-stream.md) · [03-1](./ai/03-1-api-anthropic.md) Claude · [03-2](./ai/03-2-api-openai-responses.md) OpenAI Responses(현재 경로) · [03-3](./ai/03-3-api-openai-compare.md) OpenAI 계열 비교 · [03-4](./ai/03-4-api-openai-codex-legacy.md) legacy Codex
  - [04-auth](./ai/04-auth.md) · [04-01](./ai/04-01-auth-env-and-storage.md) 환경변수와 로그인 저장 · [05-utils](./ai/05-utils.md) · [06-call-flow](./ai/06-call-flow.md) 종합
- [x] wiki 반영: [[pi]] (`wiki/projects/pi.md`)와 개념 3개 (`pi-ai-provider-api-separation`, `stealable-pattern-async-event-stream-with-final-result`, `stealable-pattern-stored-credential-owns-provider`)
- [x] 실행 실험 스크립트와 날짜별 출력: `artifacts/pi/ai-demos/`, 모델 데이터 생성 로그 `artifacts/pi/hydrate-model-data.2026-10-04.log`

## 2. 이번에 확인한, 이전 분석(4259686d9 기준)과 달라진 점

- `packages/agent`는 이 commit에서 6개 파일(`agent-loop.ts`, `agent.ts`, `types.ts`, `stream-fn.ts`, `proxy.ts`, `index.ts`)만 남았다. 실험적 harness가 `7fd478a2e`(2026-10-01)에서 삭제되었고 `chord` 의존도 사라졌다. `packages/session-backends`는 없어졌다.
- 재시도는 agent가 아니라 `coding-agent`(`core/agent-session.ts:1805-1822`, `:3660-3756`)와 `durable`이 한다.
- `openai` provider의 Sign in with ChatGPT가 현재 경로이고 `openai-codex`는 legacy.
- 위 변화 때문에 **Q5~Q8과 learning-guide의 agent 관련 서술은 재검증 대상**이다. Q7의 "재시도(3회, 2·4·8s)와 overflow compaction은 `_runAgentPrompt`가 `agent.continue()`로 처리"는 현재 코드의 `_handlePostAgentRun`/`_prepareRetry` 구조와 달라 보인다(`미확인`).

## 3. 해결되지 않은 남은 질문

- [ ] 분석 목적 (학습 / 설계 참고 / 도입 검토)
- [ ] **agent 패키지를 새 기준으로**: `agent-loop.ts`(`:414`의 `for await`로 ai 스트림을 받는 곳), `agent.ts`, `stream-fn.ts`, `proxy.ts`
- [ ] Q5~Q8 재검증과 갱신 (session projection, compaction, `AgentSession`)
- [ ] `coding-agent`가 `Models`를 연결하는 부분 (`core/sdk.ts:39`, `core/model-runtime.ts:211`), `AuthStorage` 나머지
- [ ] chord의 실제 역할, pi-durable의 소비자와 용도
- [ ] 대표 실행 흐름 (예: `pi` CLI에서 프롬프트 1회 → 도구 호출 → 응답)
- [ ] ai 안의 미분석: Google/Bedrock/Mistral/Radius/Azure 통신 코드, 이미지·분류·deferred, `providers/faux.ts`와 `test/`, `compat.ts`, `assistant-message-frame.ts`
- [ ] 두 층 재시도(요청 단위 `retryProviderRequest`, 응답 단위 `retryAssistantCall`)가 같은 오류에서 겹치는지
- [ ] `partial-json`, `typebox`가 설치된 환경에서 `parseStreamingJson`의 부분 해석과 `validateToolArguments` 실행

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `packages/agent/src/agent-loop.ts` | `runLoop`, `streamAssistantResponse`(`:385-455`), `validateToolArguments` 호출(`:726`) | ai 스트림을 받아 도구 실행과 다음 턴으로 이어가는 부분 |
| `packages/agent/src/agent.ts` | `Agent`, `processEvents`, `handleRunFailure` | Q6 재검증 |
| `packages/agent/src/stream-fn.ts` | `setDefaultStreamFn`, `getDefaultStreamFn` | ai와의 연결 지점 |
| `packages/coding-agent/src/core/sdk.ts` | `setDefaultStreamFn(streamSimple)` (`:39`) | coding-agent가 ai를 연결하는 곳 |
| `packages/coding-agent/src/core/agent-session.ts` | `_handlePostAgentRun`, `_isRetryableError`, `_prepareRetry`, 자동 압축(`:2948-2972`) | 재시도와 overflow compaction의 현재 구현 |
| `packages/coding-agent/src/core/compaction/compaction.ts` | `retryAssistantCall` 사용(`:638`), `estimateContextTokens`(`:196`) | 요약 호출과 토큰 추정 |
| `packages/coding-agent/src/core/session-manager.ts` | `buildSessionProjection` | Q8 재검증 |

---

## 5. 참고 사항 및 후속 제안

- DeepWiki(`artifacts/pi/deepwiki/`)는 2069 commits 전 기준 — second opinion으로만 사용.
- 모델 데이터 JSON(`packages/ai/src/providers/data/`)은 `.gitignore` 대상이고, 현재 로컬에는 2026-10-04에 `npm run hydrate-model-data`로 만든 것이 있다. 외부 목록 기반이라 날짜에 따라 달라진다.
- 설명과 문서화 스타일은 `OSS_ANALYSIS_WORKFLOW.md` 7장을 따른다. 문서화는 알아서 진행하고, 실행 실험은 비용이 크지 않을 때만 한다.
- 이전 분석 존재: `reports/pi/agent/package-file-roles.md`(commit `ff6181f` 기준)는 작업트리에서 삭제된 상태이며 필요하면 `git restore`로 복원할 수 있다.
