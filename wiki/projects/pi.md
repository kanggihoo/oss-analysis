---
title: pi
created: 2026-10-06
updated: 2026-10-06
type: project
tags: [open-source, project, architecture, agent-framework, developer-tools, pattern, judgment]
sources:
  - reports/pi/overview.md
  - reports/pi/ai/00-role.md
  - reports/pi/ai/01-types.md
  - reports/pi/ai/02-models-registry.md
  - reports/pi/ai/03-0-event-stream.md
  - reports/pi/ai/03-1-api-anthropic.md
  - reports/pi/ai/03-2-api-openai-responses.md
  - reports/pi/ai/03-3-api-openai-compare.md
  - reports/pi/ai/03-4-api-openai-codex-legacy.md
  - reports/pi/ai/04-auth.md
  - reports/pi/ai/04-01-auth-env-and-storage.md
  - reports/pi/ai/05-utils.md
  - reports/pi/ai/06-call-flow.md
  - reports/pi/agent/00-role.md
  - reports/pi/agent/01-types.md
  - reports/pi/agent/02-agent-loop.md
  - reports/pi/agent/03-agent-class.md
  - reports/pi/agent/04-proxy.md
  - reports/pi/agent/05-call-flow.md
  - artifacts/pi/agent-demos/
  - repos/pi/packages/agent/src/agent-loop.ts
  - repos/pi/packages/agent/src/agent.ts
  - repos/pi/packages/agent/src/proxy.ts
  - artifacts/pi/repo-metadata.txt
  - artifacts/pi/ai-demos/
  - repos/pi/packages/ai/src/models.ts
  - repos/pi/packages/ai/src/types.ts
  - repos/pi/packages/ai/src/utils/event-stream.ts
  - repos/pi/packages/ai/src/auth/resolve.ts
  - repos/pi/packages/ai/src/api/lazy.ts
  - repos/pi/packages/ai/src/api/anthropic-messages.ts
  - repos/pi/packages/ai/src/api/openai-responses.ts
confidence: medium
---

# pi

`pi`(`earendil-works/pi`)는 "통합 LLM API, agent loop, TUI, coding agent CLI"를 묶은 TypeScript 모노레포다. **이 페이지는 `ai`(`@earendil-works/pi-ai`)와 `agent`(`@earendil-works/pi-agent-core`) 패키지를 source로 검증한 요약이다(그 범위는 `confidence: high`).** `coding-agent` 등 나머지 패키지는 아직 이 commit 기준으로 분석하지 않았으므로 선언만 적었다. 상세 근거는 `reports/pi/ai/00~06`, `reports/pi/agent/00~05`에 있다. 방법론은 [[evidence-backed-analysis]]를 따랐다.

## 분석 기준
- **commit** `3874b3e98` (2026-10-02, worktree clean, `ai` 분석), 분석일 2026-10-04~06. `agent` 분석은 `28dcce2ba`(v1.0.4)에서 했고 `packages/agent/src`는 두 commit이 동일하다(`git diff`가 `CHANGELOG.md`/`package.json`뿐).
- 이전 분석(Q1~Q8)은 `4259686d9` 기준이다. 그 사이 `agent` 패키지에서 harness가 삭제되는 등 큰 변경이 있었다(`7fd478a2e`). 아래 "달라진 점" 참고.

## 패키지 지도 (선언만 확인, `packages/*/package.json`)
`ai`(통합 LLM API) → `agent`(agent loop) → `coding-agent`(CLI 제품, 세션·도구) 순으로 쌓이고, `tui`, `chord`, `protocol`, `client`, `server`, `durable`, `codemode`, `mcp`, `telemetry`, `evals`가 곁에 있다. 의존 방향과 표는 `reports/pi/overview.md` §2. 이 commit에서 `ai`를 직접 의존하는 패키지는 `agent`, `coding-agent`, `evals`, `durable` 넷뿐이다(`reports/pi/ai/00-role.md` §7).

## ai 패키지: 한 줄과 구조
**어떤 회사의 모델이든 같은 입력(`Context`)으로 부르고 같은 출력(이벤트 스트림과 `AssistantMessage`)을 받게 하는 층.** 도구 실행, 응답 단위 재시도 실행, 압축, 저장은 하지 않는다(위층의 일).

```
models.streamSimple(model, context, options)
 → normalizeContext          Context → TranscriptContext (지침·도구를 맨 앞 시스템 메시지로)
 → lazyStream                빈 스트림을 즉시 반환, 준비는 뒤에서
     → applyAuth             호출 옵션 > 저장된 credential > 환경변수 (OAuth는 락 안에서 갱신)
     → Provider.streamSimple model.api 로 통신 코드를 고름 (지연 로딩)
        → 통신 코드          요청 변환 → 전송(재시도) → 서버 이벤트를 공용 이벤트로 push → done|error
 → for await / result()      호출한 쪽
```
- **핵심 타입**: `Model`(데이터), `Provider`(서비스 하나), `Models`(Provider 모음이자 호출 입구), `AssistantMessageEvent`(12종), `AssistantMessage`(`stopReason`, `usage`) — `reports/pi/ai/01`, `02`.
- **통신 코드 세 종류를 읽음**: Claude(`anthropic-messages`), OpenAI(`openai-responses`), OpenAI 호환(`openai-completions`) 비교, legacy Codex. 모두 같은 뼈대(`03-1`~`03-4`).
- **모델 데이터는 빌드 때 외부 목록에서 생성**한 JSON이고 git에 없다(`src/providers/data/`, `.gitignore`). 2026-10-04 생성분 기준 `openai-completions`는 26개 provider, 716개 모델을 맡는다(`02` §6, `03-3` §1).

## agent 패키지: 한 줄과 구조
**"AI 호출 → 도구 실행 → 결과를 붙여 다시 호출"을 반복하는 상태 없는 루프(`agent-loop.ts`)와 그 위의 상태 래퍼(`Agent`, `agent.ts`), 서버 중계 스트림(`proxy.ts`)이 전부인 6개 파일 패키지.** 사용처 `Agent`는 `coding-agent` 하나(`sdk.ts:387`).

```
agent.prompt("hi")
 → runWithLifecycle        잠금, isStreaming=true
 → runAgentLoop(스냅샷 context, config 스냅샷, emit=processEvents)
     [턴] prepareNextTurn(2턴째~) → 대기 메시지 주입 → prepareRequest
          → transformContext → convertToLlm → normalizeContext → getApiKey → streamFn
          → (도구) 준비(순차) → 실행(병렬/순차) → afterToolCall → toolResult
          → finishTurn → turn_end → steering 확인
     follow-up / finishTurn:continue 확인 → 종료
 → processEvents: 상태 갱신 → 구독자 순차 await
```
- **상태는 이벤트로만**: 루프에는 복사본을 넘기고 `message_end`로 `state.messages`를 갱신. 설정은 run 시작 때 복사(실행 중 변경은 다음 run부터). `코드 확인` + 실행 확인(`reports/pi/agent/03`, `05`).
- **종료 결정은 7단계 우선순위**(`error/aborted` > `finishTurn:end` > 도구 `terminate`(전부일 때) > steering > follow-up > `finishTurn:continue`). [[pi-agent-turn-end-decision-priority]]
- **병렬 도구**: 준비(검증, `beforeToolCall`)는 순차, 실행만 동시, 완료 이벤트는 완료 순, `toolResult` 메시지는 호출 순. 실행 확인.
- **throw 정책이 비대칭**: 도구 쪽은 루프가 `isError` 결과로 흡수, 그 밖의 훅은 호출자 책임, `Agent`가 안전망(`handleRunFailure`). [[stealable-pattern-hook-injected-loop-with-throw-contract]]
- **도구 목록은 대화 기록의 system 메시지(`toolsAdded/toolsRemoved`)로 실린다**(`declareToolChanges`).
- **`streamProxy`**: 서버가 `partial`을 뺀 이벤트를 보내면 클라이언트가 하나의 `partial`을 갱신하며 복원. 이 repo에서는 `coding-agent`가 쓰지 않고 테스트, README, 브라우저 스모크만 쓴다. `setDefaultStreamFn`은 provider 목록 의존 없이 호스트가 기본 모델 런타임을 설치하는 전역 변수.

## Taste Notes

### Responsibility Boundaries
- **ai는 판정 함수를 제공하고 정책은 위에 맡긴다.** 재시도 가능 여부(`isRetryableAssistantError`)와 컨텍스트 초과 판정(`isContextOverflow`)은 ai에 있고, 반복과 압축 결정은 `coding-agent`(`agent-session.ts:1805-1822`, `:3660-3756`)와 `durable`이 한다.
- **저장 위치는 앱이 정한다.** `CredentialStore`, `ModelsStore`는 인터페이스이고 ai의 기본 구현은 메모리뿐이다. 파일(`auth.json`)은 `coding-agent`가 넣는다.

### Architecture Decision Taste
1. **wire 프로토콜(`api`)과 서비스(`provider`)를 분리하고 차이는 `compat` 데이터로 맞춘다.** *대안*: 회사마다 클라이언트 클래스. *이유*: 26개 provider가 `openai-completions` 하나를 공유. *대가*: 그 파일이 1726줄이 되고 알 수 없는 서버는 OpenAI와 같다고 가정한다. *근거*: `types.ts:1097-1141`, `openai-completions.ts:1585-1726`. → [[pi-ai-provider-api-separation]]
2. **즉시 반환 + 뒤에서 채우기, 실패도 값으로.** *대안*: `Promise<Stream>`을 돌려주고 예외로 실패 전달. *이유*: 호출한 쪽이 곧바로 `for await` 할 수 있고, 인증·로딩 실패도 같은 이벤트 경로로 받는다. `.result()`는 reject하지 않는다. *대가*: 호출 한 번에 스트림 세 개를 복사로 잇는다. *근거*: `utils/event-stream.ts`, `api/lazy.ts`, 종단 실험(`reports/pi/ai/06` §4). → [[stealable-pattern-async-event-stream-with-final-result]]
3. **저장된 credential이 provider를 소유한다.** *대안*: 실패하면 환경변수로 폴백. *이유*: 구독 로그인이 만료됐는데 조용히 종량제 API 키로 바뀌는 것을 막는다(이유는 주석의 "silent"에서 읽은 `추론`). *근거*: `auth/resolve.ts:24-28`, `:70-93`, 실험 `auth-owner-demo`. → [[stealable-pattern-stored-credential-owns-provider]]
4. **쓰기는 `modify` 하나로 직렬화하고 갱신은 락 안에서 재확인한다.** 동시 5개 호출에서 갱신이 1번만 일어남을 실행으로 확인(`artifacts/pi/ai-demos/auth-resolve-demo`).
5. **통신 코드와 OAuth 구현을 지연 로딩한다.** 내장 provider 42개를 등록해도 쓰는 것만 불러온다(`lazyApi`, `lazyOAuth`).

### Trade-offs / Risks
- **(agent) 중단 시 `toolResult` 짝이 맞지 않을 수 있다.** 순차 실행 중 중단되면 남은 도구 호출에 결과가 없는 채 기록이 남고 `Agent`는 메우지 않는다(실행 확인, `reports/pi/agent/05` §3.3). ai 변환 단계나 coding-agent가 메우는지는 `미확인`.
- **(agent) 안전망이 래퍼에만 있다.** `agentLoop`(스트림 반환판)는 루프 reject를 처리하지 않아 스트림이 끝나지 않는다(실행 확인). 실패 run의 `agent_end.messages`는 실패 메시지 하나뿐.
- **(agent) 프록시에서 `toolcall_end` 없이 끊기면 최종 메시지에 `partialJson` 필드가 남는다**(실행 확인).
- **(agent) 느린 구독자는 AI 스트림 소비를 늦춘다**(`message_update`가 `await emit`, 코드 확인).
- **오류 문구 정규식에 의존한다.** 재시도(`retry.ts`)와 초과 판정(`overflow.ts`)이 서버별 문구로 분류하므로 서버가 문구를 바꾸면 놓칠 수 있다(`추론`: 파일이 서버별 예시와 이슈 번호를 주석으로 쌓아 가는 구조).
- **외부의 비공식 경로.** legacy `openai-codex`는 Codex CLI의 공개 OAuth 클라이언트와 문서화되지 않은 ChatGPT 백엔드를 쓴다(제3자 자료). 현재 권장 경로는 `openai` provider의 Sign in with ChatGPT(공식 문서 일치).
- **Claude 구독 토큰은 Claude Code처럼 보이는 요청을 보낸다**(헤더, 시스템 문장, 도구 이름 철자, `anthropic-messages.ts:1016-1036`, `:1168-1183`). 이유는 코드에 없다.
- **재시도가 두 층**(요청 단위와 응답 단위)이고 겹침은 확인하지 못했다.
- 모델 데이터가 빌드 시점의 외부 목록에 의존하므로 같은 commit도 날짜에 따라 달라질 수 있다.

### Stealable Patterns
[[stealable-pattern-async-event-stream-with-final-result]], [[stealable-pattern-stored-credential-owns-provider]], [[stealable-pattern-hook-injected-loop-with-throw-contract]], 개념 [[pi-ai-provider-api-separation]], [[pi-agent-turn-end-decision-priority]].

### Comparison Hooks
- 통합 LLM 클라이언트 계열과 `api`/`provider` 분리 방식 비교(미작성).
- 판정은 라이브러리, 정책은 앱에 두는 분업을 다른 에이전트 프레임워크와 비교(미작성).

## `3874b3e98` → `28dcce2ba`에서 ai 쪽 달라진 점 (2026-10-06, diff 읽기 기준, 일부 `미확인`)
- OAuth 갱신이 `refreshStoredOAuthCredential`로 분리됐고, 호출자 `signal`은 **락 대기만** 취소한다. 갱신이 시작되면 취소를 무시하고 15초 제한만 받는다(회전된 리프레시 토큰을 잃지 않으려고, `resolve.ts:102-158`).
- `samplingParams`가 `model` < `model.samplingParamsByThinkingLevel[추론수준]` < 호출 옵션 순으로 합쳐진다(`simple-options.ts:24`).
- Anthropic 도구 변경이 **정의 값을 담은 `tool_addition`**으로 바뀌었다(`defer_loading` 미리 선언과 재정의 제약 제거, beta `inline-tools-2026-09-15`).
- provider `azure-openai-responses` → `azure`(api 2개). ChatGPT 로그인은 콜백 포트 사용 중이면 붙여 넣기 대신 오류. `retry.ts`에 HTTP/2 스트림 취소 문구 추가.
- 상세: `reports/pi/ai/06-call-flow.md` §8 끝, 각 문서 머리 NOTE.

## 이전 분석(Q4 등)에서 달라진 점
- 재시도는 agent의 `harness`가 하지 않는다. harness는 삭제되었고 `coding-agent`와 `durable`이 한다(`reports/pi/ai/05` §2.3).
- 인증 누락의 동기 throw는 통신 코드 모듈의 `streamSimple`을 직접 부를 때만이다. `Models.streamSimple`은 `error` 이벤트(`reports/pi/ai/06` §4, §8).
- 이전 Q5(agent-loop), Q6(Agent 클래스)는 현재 코드와 **일치**한다(`reports/pi/agent/00` §6). Q7·Q8은 대기.
- `openai`의 ChatGPT 구독 로그인이 새 경로이고 `openai-codex`는 legacy(`reports/pi/ai/03-2` §0).

## 아직 분석하지 않은 것
`coding-agent`, `tui`, `chord` 등 나머지 패키지(`agent`는 분석 완료, 이전 Q5·Q6 재검증 결과 일치, Q7·Q8은 coding-agent 단계에서 재검증). ai 안에서도 Google/Bedrock/Mistral 통신 코드, 이미지·분류·deferred, `providers/faux.ts`, `compat.ts`는 읽지 않았다(`reports/pi/ai/06` §9). 이전 Q5~Q8은 새 commit 기준 재검증이 필요하다. 다음 시작점은 `reports/pi/next.md`.
