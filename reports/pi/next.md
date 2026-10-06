# Next Session Plan / Handoff: pi

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `28dcce2ba` (v1.0.4, 2026-10-05). `ai` 문서는 `3874b3e98` 기준이며 `packages/agent/src`는 두 SHA가 동일(`git diff`는 `CHANGELOG.md`/`package.json`뿐). `packages/ai`는 2026-10-06에 diff를 읽고 문서를 보정했다(`ai/*` 머리의 NOTE 참고). `coding-agent`는 `agent-session.ts`(+54/−19), `sdk.ts`(+12/−6) 등을 새 SHA 기준으로 읽을 것
- **작성/갱신 일자**: `2026-10-06` (agent 00~05 완료 후 handoff)
- **이전 기준 SHA**: `4259686d9290c0d73ae7192b796aee3e530a9779` (Q1~Q8과 learning-guide, 다이어그램이 이 기준)
- **분석 목표**: pi를 완벽하게 이해한다. 순서는 `ai` → `agent` → `coding-agent`. 기준은 항상 `repos/pi`의 최신 commit.

---

## 0. 한 장 요약 (새 세션은 여기부터)

| 패키지 | 상태 | 문서 |
|---|---|---|
| `ai` | **완료** (코드 확인 + 로컬 실행 실험) | [`ai/00~06`](./ai/) 13개 |
| `agent` | **완료** (코드 확인 + 실행 확인) | [`agent/00~05`](./agent/) 6개 |
| `coding-agent` | 시작 전 | |

**지금 멈춘 지점**: `agent` 시리즈 완료. 다음은 `coding-agent` 단계(§2.2). 먼저 `core/sdk.ts`부터.

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

### 1.2 `agent` 패키지 (완료, 6/6)
- [00-role](./agent/00-role.md) 역할·의존·harness 삭제·Q5~Q8 대조 · [01-types](./agent/01-types.md) 타입 4묶음, 훅 표 · [02-agent-loop](./agent/02-agent-loop.md) 턴 순서, 종료 7단계, 병렬/순차 · [03-agent-class](./agent/03-agent-class.md) 스냅샷+이벤트 상태, 큐, `handleRunFailure` · [04-proxy](./agent/04-proxy.md) `streamProxy`, `setDefaultStreamFn` · [05-call-flow](./agent/05-call-flow.md) 종합 + 실행 확인
- 실험: `artifacts/pi/agent-demos/` (`agent-flow-demo.ts`, `proxy-demo.ts`, `lib.ts`, `pi-ai-shim.ts`, `loader.mjs`, 출력 `*.2026-10-06.out`). 실행: `cd artifacts/pi/agent-demos && node --no-warnings --import ./register.mjs agent-flow-demo.ts`. `typebox@1.3.27`, `partial-json@0.1.7`은 **이 폴더에만** 설치(`.gitignore`에 `artifacts/**/node_modules/` 추가). `pi-ai-shim.ts`가 agent가 쓰는 ai 함수만 실제 소스에서 가져온다.
- Q5·Q6 재검증: 본문 **일치**, 두 문서 머리에 재검증 메모 추가. Q7·Q8은 coding-agent 단계에서.
- wiki: [[pi]]에 agent 절 추가, `stealable-pattern-hook-injected-loop-with-throw-contract`, `pi-agent-turn-end-decision-priority`, `wiki/index.md`, `wiki/log.md` 갱신 완료(wiki-lint 새 이슈 없음).
- **알려진 구멍 → coding-agent에서 메워지는지 확인할 것**: ① 중단 시 `toolResult` 짝 불일치(05 F, `Agent`는 안 메움) ② 압축처럼 context를 교체하는 훅이 `state.messages`를 어떻게 갱신하나(`추론`) ③ 실패 run의 `agent_end.messages`가 `[failure]` 하나뿐 → 구독자가 `message_end`로 저장하는가 ④ 느린 구독자가 스트림을 늦춤 ⑤ `setDefaultStreamFn` 호출 위치(`sdk.ts:2`는 import만 확인)

### 1.3 문서 위생 발견 (낡은 문서, 수정은 하지 않음)
- `packages/telemetry/README.md:326,371,380`: 삭제된 `AGENT_TELEMETRY_SCHEMAS`를 `pi-agent-core`에서 가져온다고 적음
- `packages/agent/src/types.ts:357`: 주석 예제의 모듈명이 `@mariozechner/agent`
- `packages/agent/src/proxy.ts:85-103`: `streamProxy` 설명 주석과 `@example`이 `buildProxyRequestOptions` 위에 붙어 있고, 예제가 일반 화살표 함수 안에서 `await`를 씀(`:98`)

### 1.4 이전 분석(4259686d9)과 달라진 점
- `packages/agent`는 6개 파일만 남음. harness 삭제(`7fd478a2e`, 2026-10-01), `chord` 의존과 `packages/session-backends`도 사라짐.
- 재시도는 agent가 아니라 `coding-agent`(`core/agent-session.ts:1805-1822`, `:3660-3756`)와 `durable`이 한다.
- `openai` provider의 Sign in with ChatGPT가 현재 경로, `openai-codex`는 legacy.
- 따라서 **Q5~Q8과 learning-guide의 agent 관련 서술은 재검증 대상**. Q7의 `_runAgentPrompt` → `agent.continue()` 서술은 현재 `_handlePostAgentRun`/`_prepareRetry` 구조와 달라 보인다(`미확인`).

---

## 2. 앞으로 할 일 (순서대로)

### 2.1 `agent` 나머지 — **완료** (02~05 작성, 2026-10-06)

### 2.2 `coding-agent`
- `core/sdk.ts` (`setDefaultStreamFn` `:39`, `new Agent` `:387-420`, 두 번째 `new Agent` 위치 확인)
- `core/agent-session.ts`: `_handlePostAgentRun`, `_isRetryableError`, `_prepareRetry`, 자동 압축(`:2948-2972`), `runToolCall` 사용(`:31`, `:711`), `core/nested-tool-calls.ts`
- `core/compaction/compaction.ts` (`retryAssistantCall` `:638`, `estimateContextTokens` `:196`)
- `core/session-manager.ts` (`buildSessionProjection`, Q8 재검증), `core/auth-storage.ts`, `core/model-runtime.ts:211`
- 대표 실행 흐름: `pi` CLI에서 프롬프트 1회 → 도구 호출 → 응답

### 2.3 마무리 작업
- ~~agent 시리즈 wiki 반영, overview 추가, Q5·Q6 재검증 표시~~ 완료. **남은 것**: Q7·Q8에 재검증 결과 표시(coding-agent 단계 후), `learning-guide.md`의 agent 관련 서술 갱신, coding-agent 완료 후 wiki `pi` 페이지 확장

### 2.4 남은 질문 (ai 쪽 포함)
- [ ] 분석 목적 (학습 / 설계 참고 / 도입 검토) 확인 안 됨
- [ ] chord의 실제 역할, `pi-durable`의 소비자와 용도, `replay` 필드 사용처
- [ ] 두 층 재시도(`retryProviderRequest`, `retryAssistantCall`)가 같은 오류에서 겹치는지
- [x] `parseStreamingJson` 부분 해석: 05 프록시 실험에서 `{"path":"a."}` → `{"path":"a.txt"}` 확인. [ ] `validateToolArguments`의 검증 실패 메시지는 직접 실행 안 함(실험 A, 도구 호출은 통과 경로만)
- [ ] ai 미분석: Google/Bedrock/Mistral/Radius/Azure 통신 코드, 이미지·분류·deferred, `providers/faux.ts`와 `test/`, `compat.ts`, `assistant-message-frame.ts`
- [ ] 서버 쪽 동작(예: Responses `previous_response_id`, WebSocket 이점)은 코드와 mock 테스트로만 확인, 실제 서버는 `미확인`

---

## 3. 주의할 점 (함정)

- 이전 분석(`4259686d9`)의 서술을 그대로 옮기지 말 것. 반드시 현재 코드로 재확인. 특히 Q4~Q8, learning-guide.
- `Models.streamSimple`과 통신 코드 모듈의 `streamSimple`은 다르다. 인증 누락은 전자는 `error` 이벤트, 후자는 동기 throw (ai/06 §8).
- `stream`이라는 이름이 겹친다(outer/inner 스트림, `stream()` 함수). 설명할 때 어느 것인지 명시.
- 모델 데이터 JSON(`packages/ai/src/providers/data/`)은 `.gitignore` 대상. 2026-10-04에 `npm run hydrate-model-data`로 생성. 외부 목록 기반이라 날짜에 따라 다름.
- `repos/pi/AGENTS.md` 규칙: `npm run build`/`npm test` 임의 실행 금지, 전체 vitest 금지(e2e 활성화 위험), 필요하면 `./test.sh` 또는 개별 테스트. 이 워크스페이스에서는 repo 변경 없이 읽기 위주.
- 워크스페이스 git: `reports/pi/agent/02~05`, `artifacts/pi/agent-demos/`, 새 wiki 개념 페이지 2개 등은 **아직 untracked/미커밋**. 사용자가 요청하기 전에는 커밋하지 않는다.
- wiki-lint의 9개 이슈는 이전부터 있던 것(codenotch/codewiki 태그), 이번 작업과 무관.
- **ai 보정 한계**: 03-1은 줄 번호를 전수 재확인하지 않았다. 모델 데이터(`providers/data/`)는 2026-10-04 생성분이라 새 SHA에서 `azure` 반영 여부를 알려면 `npm run hydrate-model-data` 재실행이 필요하다(허락 필요).
- repo HEAD가 세션 중에 `3874b3e98` → `28dcce2ba`로 올라 있었다(사용자나 다른 세션이 pull한 것으로 보임). coding-agent 분석 전에 `git -C repos/pi log --oneline 3874b3e98..HEAD -- packages/coding-agent packages/ai`로 변경을 확인할 것.
- 메모리(`~/.claude/projects/.../memory/`)에 초기에 만든 파일 2개(`feedback_explanation-style.md`, `project_pi-ai-analysis-plan.md`)가 있다. 사용자가 삭제를 요청한 적은 없으나 스타일 분석은 저장하지 말라고 했으므로, 지울지 물어볼 것.

---

## 4. 참고

- DeepWiki(`artifacts/pi/deepwiki/`)는 2069 commits 전 기준: second opinion으로만.
- 이전 분석 `reports/pi/agent/package-file-roles.md`(commit `ff6181f` 기준)는 작업트리에서 삭제된 상태. 필요하면 `git restore`.
- 상세 절차와 스타일: `OSS_ANALYSIS_WORKFLOW.md` (§7 사용자 맞춤 스타일), `AGENTS.md`.
