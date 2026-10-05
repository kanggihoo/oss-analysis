# Next Session Plan / Handoff: pi

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `3874b3e98983c70fa05fa193b675d42cfcb8b9f8` (2026-10-02, worktree clean)
- **작성/갱신 일자**: `2026-10-06` (agent 00, 01 작성 후 handoff)
- **이전 기준 SHA**: `4259686d9290c0d73ae7192b796aee3e530a9779` (Q1~Q8과 learning-guide, 다이어그램이 이 기준)
- **분석 목표**: pi를 완벽하게 이해한다. 순서는 `ai` → `agent` → `coding-agent`. 기준은 항상 `repos/pi`의 최신 commit.

---

## 0. 한 장 요약 (새 세션은 여기부터)

| 패키지 | 상태 | 문서 |
|---|---|---|
| `ai` | **완료** (코드 확인 + 로컬 실행 실험) | [`ai/00~06`](./ai/) 13개 |
| `agent` | **진행 중**: 00, 01 완료 / 02~05 남음 | [`agent/00-role`](./agent/00-role.md), [`agent/01-types`](./agent/01-types.md) |
| `coding-agent` | 시작 전 | |

**지금 멈춘 지점**: `agent/02-agent-loop` 작성 직전. `agent-loop.ts`(940줄) 본문은 아직 읽지 않았다.

### 0.1 사용자 선호 (`OSS_ANALYSIS_WORKFLOW.md` §7에 상세)
- 자연스러운 한국어, 용어는 먼저 정의, 한 번에 한 개념을 짧게.
- 장난감 모델 + 실제 `파일:줄` 대응. 예시는 OpenAI/Claude로 (Groq 같은 호환 서비스 말고).
- 모든 주장에 `파일:줄`과 검증 수준(`코드 확인 / 실행 확인 / 추론 / 미확인`). 코드만으로 외부 서버 동작을 단정하지 않는다.
- **문서화는 요청 없이 알아서** 한다("설명만"이라고 하면 제외). 실행 실험은 비용이 작을 때만(외부 접속, 설치, 빌드, repo 변경은 허락 받고).
- 병렬 문서는 같은 구조. 번호 `NN-주제.md`, 하위는 `NN-1`/`NN-01`. 낡은 경로는 현재 경로로 교체.
- 스타일 분석은 메모리에 저장하지 말라고 했다(사용자 지시).

### 0.2 문서 공통 구조 (ai/agent 문서 형식)
머리말(기준 commit, 선행 문서, 읽은 파일, 검증 수준) → 이 문서의 질문 → 한 줄 답 → 표와 `파일:줄` → `미확인` 목록 → 다음.

---

## 1. 지금까지 한 일

### 1.1 `ai` 패키지 (완료)
- [00-role](./ai/00-role.md) 역할·의존 · [01-types](./ai/01-types.md) · [02-models-registry](./ai/02-models-registry.md) · [03-0-event-stream](./ai/03-0-event-stream.md)
- 통신 코드: [03-1](./ai/03-1-api-anthropic.md) Claude · [03-2](./ai/03-2-api-openai-responses.md) OpenAI Responses(현재) · [03-3](./ai/03-3-api-openai-compare.md) OpenAI 계열 비교 · [03-4](./ai/03-4-api-openai-codex-legacy.md) legacy Codex
- [04-auth](./ai/04-auth.md) · [04-01](./ai/04-01-auth-env-and-storage.md) · [05-utils](./ai/05-utils.md) · [06-call-flow](./ai/06-call-flow.md)
- 실험: `artifacts/pi/ai-demos/` (스크립트와 날짜별 로그), `artifacts/pi/hydrate-model-data.2026-10-04.log`
- wiki: [[pi]], `pi-ai-provider-api-separation`, `stealable-pattern-async-event-stream-with-final-result`, `stealable-pattern-stored-credential-owns-provider`

### 1.2 `agent` 패키지 (2/6)
- [00-role](./agent/00-role.md): 역할(AI 호출 → 도구 실행 → 재호출 반복), 6개 파일 구성, 의존(`pi-ai`, `typebox`), 사용처는 `coding-agent` 하나(`new Agent`는 `sdk.ts:387`), harness 삭제(v1.0.0), 이전 Q5~Q8 대조표
- [01-types](./agent/01-types.md): `types.ts` 전체. 타입 4묶음, 훅 표, 이벤트 10종. 주요 발견: throw 금지 계약이 곳곳에 있음, "끝낼지 계속할지"를 정하는 곳이 셋(`finishTurn`, 도구 `terminate` 힌트, 큐)

### 1.3 문서 위생 발견 (낡은 문서, 수정은 하지 않음)
- `packages/telemetry/README.md:326,371,380`: 삭제된 `AGENT_TELEMETRY_SCHEMAS`를 `pi-agent-core`에서 가져온다고 적음
- `packages/agent/src/types.ts:357`: 주석 예제의 모듈명이 `@mariozechner/agent`

### 1.4 이전 분석(4259686d9)과 달라진 점
- `packages/agent`는 6개 파일만 남음. harness 삭제(`7fd478a2e`, 2026-10-01), `chord` 의존과 `packages/session-backends`도 사라짐.
- 재시도는 agent가 아니라 `coding-agent`(`core/agent-session.ts:1805-1822`, `:3660-3756`)와 `durable`이 한다.
- `openai` provider의 Sign in with ChatGPT가 현재 경로, `openai-codex`는 legacy.
- 따라서 **Q5~Q8과 learning-guide의 agent 관련 서술은 재검증 대상**. Q7의 `_runAgentPrompt` → `agent.continue()` 서술은 현재 `_handlePostAgentRun`/`_prepareRetry` 구조와 달라 보인다(`미확인`).

---

## 2. 앞으로 할 일 (순서대로)

### 2.1 `agent` 나머지 (다음 세션 첫 작업)
| 번호 | 문서 | 읽을 곳 | 확인할 것 |
|---|---|---|---|
| **02** | `agent/02-agent-loop.md` | `agent-loop.ts` 전체 (`agentLoop` `:32`, `agentLoopContinue` `:38`, `runAgentLoop` `:71`, `runAgentLoopContinue` `:102`, ai 스트림 소비 `:385-455`, `normalizeContext` `:397`, `for await` `:414`, `validateToolArguments` `:726`, `runToolCall` `:790`) | 01에서 `미확인`으로 남긴 것: 각 훅의 호출 지점과 순서, `terminate`/`finishTurn`/큐의 우선순위, 병렬 실행의 이벤트 순서, 종료 조건, `convertToLlm`/`transformContext` 호출 순서, `getApiKey`가 옵션에 들어가는 방식 |
| 03 | `agent/03-agent-class.md` | `agent.ts` (613줄: 필드 `:188-215`, 메서드 `:230-373`, `continue` `:384`, `handleRunFailure`, `processEvents`) | 상태 갱신, steering/follow-up 큐와 `QueueMode`, 구독자 순차 `await`, `waitForIdle`, 실패 처리, Q6 재검증 |
| 04 | `agent/04-proxy.md` | `proxy.ts` (406줄: `streamProxy`, `ProxyMessageEventStream`) | 서버 이벤트에서 `partial`을 뺀 형식을 다시 조립하는 부분 |
| 05 | `agent/05-call-flow.md` | 종합 | `agent.prompt("...")` 한 번의 경로(ai/06과 이어서). **가짜 `streamFn`으로 실행 실험** (외부 접속 없이 가능, `partial-json`/`typebox` 미설치 시 허락 받고 설치 여부 결정) |

각 문서 끝에서: `agent/00-role` §6 대조표 갱신, `overview.md`에 해당 절 추가.

### 2.2 `coding-agent`
- `core/sdk.ts` (`setDefaultStreamFn` `:39`, `new Agent` `:387-420`, 두 번째 `new Agent` 위치 확인)
- `core/agent-session.ts`: `_handlePostAgentRun`, `_isRetryableError`, `_prepareRetry`, 자동 압축(`:2948-2972`), `runToolCall` 사용(`:31`, `:711`), `core/nested-tool-calls.ts`
- `core/compaction/compaction.ts` (`retryAssistantCall` `:638`, `estimateContextTokens` `:196`)
- `core/session-manager.ts` (`buildSessionProjection`, Q8 재검증), `core/auth-storage.ts`, `core/model-runtime.ts:211`
- 대표 실행 흐름: `pi` CLI에서 프롬프트 1회 → 도구 호출 → 응답

### 2.3 마무리 작업
- `agent` 시리즈 끝나면: `wiki/projects/pi.md`(agent 절, confidence 갱신), `wiki/concepts/`에 패턴 후보(예: "throw 금지 계약 + 훅으로 정책 주입", "턴 종료 결정 3곳"), `wiki/index.md`, `wiki/log.md`
- `overview.md` §3.4 이후에 agent 요약 추가, Q5~Q8 문서에 "새 SHA 기준 재검증 결과" 표시

### 2.4 남은 질문 (ai 쪽 포함)
- [ ] 분석 목적 (학습 / 설계 참고 / 도입 검토) 확인 안 됨
- [ ] chord의 실제 역할, `pi-durable`의 소비자와 용도, `replay` 필드 사용처
- [ ] 두 층 재시도(`retryProviderRequest`, `retryAssistantCall`)가 같은 오류에서 겹치는지
- [ ] `partial-json`, `typebox` 설치 환경에서 `parseStreamingJson`의 부분 해석과 `validateToolArguments` 실행
- [ ] ai 미분석: Google/Bedrock/Mistral/Radius/Azure 통신 코드, 이미지·분류·deferred, `providers/faux.ts`와 `test/`, `compat.ts`, `assistant-message-frame.ts`
- [ ] 서버 쪽 동작(예: Responses `previous_response_id`, WebSocket 이점)은 코드와 mock 테스트로만 확인, 실제 서버는 `미확인`

---

## 3. 주의할 점 (함정)

- 이전 분석(`4259686d9`)의 서술을 그대로 옮기지 말 것. 반드시 현재 코드로 재확인. 특히 Q4~Q8, learning-guide.
- `Models.streamSimple`과 통신 코드 모듈의 `streamSimple`은 다르다. 인증 누락은 전자는 `error` 이벤트, 후자는 동기 throw (ai/06 §8).
- `stream`이라는 이름이 겹친다(outer/inner 스트림, `stream()` 함수). 설명할 때 어느 것인지 명시.
- 모델 데이터 JSON(`packages/ai/src/providers/data/`)은 `.gitignore` 대상. 2026-10-04에 `npm run hydrate-model-data`로 생성. 외부 목록 기반이라 날짜에 따라 다름.
- `repos/pi/AGENTS.md` 규칙: `npm run build`/`npm test` 임의 실행 금지, 전체 vitest 금지(e2e 활성화 위험), 필요하면 `./test.sh` 또는 개별 테스트. 이 워크스페이스에서는 repo 변경 없이 읽기 위주.
- 워크스페이스 git: `reports/pi/agent/`, `reports/pi/ai/`, `wiki/projects/pi.md` 등은 **아직 untracked/미커밋**. 사용자가 요청하기 전에는 커밋하지 않는다.
- wiki-lint의 9개 이슈는 이전부터 있던 것(codenotch/codewiki 태그), 이번 작업과 무관.
- 메모리(`~/.claude/projects/.../memory/`)에 초기에 만든 파일 2개(`feedback_explanation-style.md`, `project_pi-ai-analysis-plan.md`)가 있다. 사용자가 삭제를 요청한 적은 없으나 스타일 분석은 저장하지 말라고 했으므로, 지울지 물어볼 것.

---

## 4. 참고

- DeepWiki(`artifacts/pi/deepwiki/`)는 2069 commits 전 기준: second opinion으로만.
- 이전 분석 `reports/pi/agent/package-file-roles.md`(commit `ff6181f` 기준)는 작업트리에서 삭제된 상태. 필요하면 `git restore`.
- 상세 절차와 스타일: `OSS_ANALYSIS_WORKFLOW.md` (§7 사용자 맞춤 스타일), `AGENTS.md`.
