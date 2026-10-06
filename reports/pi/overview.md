# pi Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/earendil-works/pi.git`
- **분석 Commit SHA**: `4259686d9290c0d73ae7192b796aee3e530a9779` (구조도·Q1~Q8 기준). **`ai` 패키지 상세 분석은 최신 `3874b3e98983c70fa05fa193b675d42cfcb8b9f8`(2026-10-02) 기준** — [`ai/`](./ai/) 참고
- **분석 일자**: `2026-09-29`
- **작업트리 상태**: `clean`
- **분석 목적**: `미정 (사용자 확인 필요)`
- **메타데이터**: [`artifacts/pi/repo-metadata.txt`](../../artifacts/pi/repo-metadata.txt)
- **외부 baseline**: DeepWiki snapshot `artifacts/pi/deepwiki/` — commit `406a221` (2026-06-11) 기준, **HEAD보다 2069 commits 뒤처짐**. 당시 코드 기준은 [`repo-metadata.2026-06-11-deepwiki-baseline.txt`](../../artifacts/pi/repo-metadata.2026-06-11-deepwiki-baseline.txt)에 보관

---

## 2. 프로젝트 개요

GitHub 설명: "AI agent toolkit: unified LLM API, agent loop, TUI, coding agent CLI" (MIT, ⭐110k). TypeScript monorepo (~348k LOC TS, 1700 files; `artifacts/pi/static-analysis/tokei.txt`).

### 패키지 구성 (`packages/*/package.json` description 기준, 검증 수준: 코드 확인 — 선언만 확인, 구현 미확인)

| 패키지 | npm 이름 | 설명 | DeepWiki baseline에 존재 |
|---|---|---|---|
| `ai` | pi-ai | 통합 LLM API, 모델 탐색·provider 설정 | O |
| `agent` | pi-agent-core | transport 추상화·상태 관리를 가진 범용 agent | O |
| `tui` | pi-tui | differential rendering TUI 라이브러리 | O |
| `coding-agent` | pi-coding-agent | read/bash/edit/write 도구와 세션 관리를 가진 CLI | O |
| `chord` | chord | 서비스·replicated state·RPC·plugin 조합 런타임 | X (신규) |
| `protocol` | pi-protocol | 원격 세션용 transport-neutral CBOR 프로토콜 | X (신규) |
| `client` | pi-client | framed CBOR 기반 원격 세션 client | X (신규) |
| `server` | pi-server | experimental server | X (신규) |
| `session-backends` | — | (package.json 설명 없음, 미확인) | X (신규) |
| `durable` | pi-durable | 대화·task·문서 durable 런타임 | X (신규) |
| `codemode` | pi-codemode | 주입된 tool 호출만 가능한 sandboxed JS 실행 | X (신규) |
| `mcp` | pi-mcp | standalone MCP client | X (신규) |
| `telemetry` | pi-telemetry | vendor-neutral telemetry 계약·스키마 | X (신규) |
| `evals` | pi-evals | (설명 없음) | X (신규) |

> [!WARNING]
> DeepWiki는 4개 패키지 시절 기준이다. 신규 10개 패키지(원격 세션·durable·codemode 등)는 DeepWiki로 커버되지 않으므로 local 코드로만 파악한다.

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 패키지 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 12개 노드(14 패키지 중 evals 제외, 원격 3종 병합)와 의존 방향 |
| coding-agent 내부 구조 | [coding-agent-structure.json](./diagrams/coding-agent-structure.json) | [coding-agent-structure.html](./diagrams/coding-agent-structure.html) | 진입점·3개 모드 → AgentSession → ResourceLoader/Extensions/Tools/SessionManager/ModelRuntime. showcase 9/9, 소스 참조 18개 확인, visual-check 통과 |
| RPC prompt 흐름 ① | [rpc-prompt-1-preflight.json](./diagrams/rpc-prompt-1-preflight.json) | [rpc-prompt-1-preflight.html](./diagrams/rpc-prompt-1-preflight.html) | stdin prompt → preflight hooks → response → agent loop → pi-ai |
| RPC prompt 흐름 ② | [rpc-prompt-2-tool.json](./diagrams/rpc-prompt-2-tool.json) | [rpc-prompt-2-tool.html](./diagrams/rpc-prompt-2-tool.html) | tool_execution_start → tool_call hook → execute → end → agent_settled |
| pi-ai 구조 | [ai-architecture.json](./diagrams/ai-architecture.json) | [ai-architecture.html](./diagrams/ai-architecture.html) | consumer → Models → Provider → api → vendor, 옆에 auth·catalog·utils |
| pi-ai streamSimple 단계 | [ai-streamsimple-workflow.json](./diagrams/ai-streamsimple-workflow.json) | [ai-streamsimple-workflow.html](./diagrams/ai-streamsimple-workflow.html) | setup 단계와 실패가 error 이벤트로 모이는 경로 |
| pi-ai 호출 시퀀스 | [ai-stream-sequence.json](./diagrams/ai-stream-sequence.json) | [ai-stream-sequence.html](./diagrams/ai-stream-sequence.html) | Anthropic 예시: 동기 반환 → auth → import → SSE → 이벤트 |
| pi-ai 모델 카탈로그 | [ai-model-catalog-dataflow.json](./diagrams/ai-model-catalog-dataflow.json) | [ai-model-catalog-dataflow.html](./diagrams/ai-model-catalog-dataflow.html) | 빌드 타임 생성 + 런타임 refresh → getAvailable |
| pi-ai 메시지 상태 | [ai-message-lifecycle.json](./diagrams/ai-message-lifecycle.json) | [ai-message-lifecycle.html](./diagrams/ai-message-lifecycle.html) | StopReason 7종과 deferred·재시도 경계 |
| agent-loop 제어 흐름 | [agent-loop-workflow.json](./diagrams/agent-loop-workflow.json) | [agent-loop-workflow.html](./diagrams/agent-loop-workflow.html) | runLoop 이중 루프, hook 위치, 종료 조건 |
| agent-loop 1턴 시퀀스 | [agent-loop-sequence.json](./diagrams/agent-loop-sequence.json) | [agent-loop-sequence.html](./diagrams/agent-loop-sequence.html) | Agent → runLoop → streamFn → tool, 이벤트 순서 |
| AgentSession 재시도·compaction | [agent-session-postrun-workflow.json](./diagrams/agent-session-postrun-workflow.json) | [agent-session-postrun-workflow.html](./diagrams/agent-session-postrun-workflow.html) | run 이후 retry/compaction/queue 판정 루프 |
| 세션 projection | [session-projection-dataflow.json](./diagrams/session-projection-dataflow.json) | [session-projection-dataflow.html](./diagrams/session-projection-dataflow.html) | 세션 파일 → projection → convertToLlm → LLM |

- 근거: `packages/*/package.json` dependencies + 실제 `src` import 횟수 ([`artifacts/pi/static-analysis/cross-package-imports.txt`](../../artifacts/pi/static-analysis/cross-package-imports.txt))
- archify 검증: showcase 9/9 checks, 0 error / 0 warning, 소스 참조 15개를 `4259686`에서 확인, browser visual-check 통과(1440·1600·1920·2048)
- **검증 수준**: 패키지 의존 방향 = `코드 확인` (import 문 기준) / 런타임 호출 순서·데이터 흐름 = `미확인`

### 그림 읽는 가이드
1. **맨 위 `pi-coding-agent`에서 시작합니다.** `pi` CLI, SDK, 실행 모드가 모두 이 패키지에 있고, 그 아래 레이어 전체를 조합합니다.
2. **초록 굵은 선을 따라갑니다.** `pi-coding-agent → pi-agent-core → pi-ai → LLM provider APIs`가 LLM 호출의 핵심 경로입니다. `pi-ai`는 여러 vendor SDK(Anthropic/OpenAI/Google/Bedrock)를 통합 API 하나로 감쌉니다.
3. **옆으로 붙는 도구 확장**: `pi-codemode`(QuickJS sandbox)와 `pi-mcp`는 coding-agent의 `src/extensions/`에서 도구로 붙습니다.
4. **아래쪽 기반 런타임**: `chord`는 agent, 원격 세션, durable이 공통으로 쓰는 조합 런타임입니다. 원격 세션(server/client/protocol)은 coding-agent의 devDependency이고 `src/experimental/`에서만 씁니다.
5. **주의할 점**: 화살표는 패키지 의존 방향일 뿐 호출 순서가 아닙니다. `pi-durable`은 레포 안에서 import하는 곳이 없습니다(외부 소비자용인지는 `추론`/`미확인`).

### 코드로 확인한 추가 사실
- coding-agent가 가장 많이 import하는 패키지는 `pi-ai`(94) > `pi-tui`(87) > `pi-agent-core`(70) > `chord`(29)입니다. 그림에는 `cli → ai` 직접 의존을 선으로 그리지 않고 카드에만 적었습니다.
- `pi-server`도 `pi-agent-core`를 직접 import하지만(6), 선이 복잡해져 그림에서는 생략했습니다.
- `pi-tui`, `pi-mcp`, `pi-codemode`, `pi-telemetry`는 내부 패키지에 의존하지 않는 leaf입니다.

---

## 3.4 ai 패키지 상세 문서 (최신 commit `3874b3e98` 기준)

코드 흐름 순서로 번호를 붙인 13개 문서. 한 번의 `models.streamSimple(...)` 호출이 지나가는 길은 [06-call-flow](./ai/06-call-flow.md)에 종합되어 있다.

| 문서 | 내용 |
|---|---|
| [00-role](./ai/00-role.md) | ai 패키지의 역할, 의존 관계, 현재 import 횟수 |
| [01-types](./ai/01-types.md) | `Message`, `Context`, `Model`, `AssistantMessageEvent` 등 타입 카탈로그 |
| [02-models-registry](./ai/02-models-registry.md) | `Models`, `Provider`, `createProvider`, 모델 데이터 생성 |
| [03-0](./ai/03-0-event-stream.md) · [03-1](./ai/03-1-api-anthropic.md) · [03-2](./ai/03-2-api-openai-responses.md) · [03-3](./ai/03-3-api-openai-compare.md) · [03-4](./ai/03-4-api-openai-codex-legacy.md) | 이벤트 스트림, 통신 코드(Claude, OpenAI Responses, OpenAI 계열 비교, legacy Codex) |
| [04-auth](./ai/04-auth.md) · [04-01](./ai/04-01-auth-env-and-storage.md) | 인증 해석 순서, OAuth, 환경변수 이름과 로그인 저장 위치 |
| [05-utils](./ai/05-utils.md) | 재시도, 컨텍스트 초과 판정, 토큰 추정, JSON 복구, 오류 정리 |
| [06-call-flow](./ai/06-call-flow.md) | 호출 경로 종합과 종단 실험, Q4와 달라진 점 |

> [!WARNING]
> 아래 Q4~Q8과 learning-guide는 이전 SHA(`4259686d9`) 기준이다. ai 관련 서술 중 달라진 점은 [06-call-flow §8](./ai/06-call-flow.md)에, agent 쪽 Q5·Q6은 2026-10-06에 재검증을 마쳤고(일치, [agent/00 §6](./agent/00-role.md)), Q7·Q8(AgentSession, 세션 투영)은 coding-agent 단계에서 재검증한다. 요약은 [`wiki/projects/pi.md`](../../wiki/projects/pi.md).

## 3.45 agent 패키지 상세 문서 (commit `28dcce2ba` 기준, `packages/agent/src`는 `3874b3e98`과 동일)

| 문서 | 내용 |
|---|---|
| [00-role](./agent/00-role.md) | 역할(AI 호출 → 도구 실행 → 재호출 반복), 6개 파일, 의존, harness 삭제, 이전 Q5~Q8 대조표 |
| [01-types](./agent/01-types.md) | `types.ts`: 타입 4묶음, 훅 표, 이벤트 10종 |
| [02-agent-loop](./agent/02-agent-loop.md) | `runLoop` 이중 루프, 턴 순서와 훅 호출 지점, 종료 7단계 우선순위, 병렬/순차 이벤트 순서, `declareToolChanges` |
| [03-agent-class](./agent/03-agent-class.md) | `Agent`: 스냅샷 입력 + 이벤트 전용 상태 갱신, 큐, 실패 처리(`handleRunFailure`), run 시작 시 config 스냅샷 |
| [04-proxy](./agent/04-proxy.md) | `streamProxy`: `partial`을 뺀 이벤트를 클라이언트가 복원, `setDefaultStreamFn` |
| [05-call-flow](./agent/05-call-flow.md) | `agent.prompt()` 한 번의 경로 + 가짜 `streamFn`/로컬 SSE 서버 실행 확인(`artifacts/pi/agent-demos/`) |

핵심 발견(요약은 [`wiki/projects/pi.md`](../../wiki/projects/pi.md)): 훅으로 정책을 주입하는 상태 없는 루프, throw 정책의 비대칭(도구는 루프가 흡수, 나머지 훅은 호출자 책임, `Agent`가 안전망), 알려진 구멍(중단 시 `toolResult` 짝 불일치, 프록시 `partialJson` 잔존, `agentLoop`의 reject 미처리).

## 3.5 학습 가이드

- [learning-guide.md](./learning-guide.md): Q1·Q4~Q8을 이어서 읽는 설명 글 (ai → agent-loop → Agent → AgentSession → 세션 파일)

## 4. 핵심 질문 및 세부 답변 목록 (Questions)

다이어그램을 탐색하며 도출된 질문과 코드 기반 검증 보고서 링크입니다.

- [Q1: 패키지 지도와 학습 순서](./questions/q1-package-map-and-learning-order.md) - *pi-ai → agent-core → coding-agent를 아래부터, chord·원격·durable은 실험 트랙이라 마지막*
- [Q2: HarnessLens 기획서의 pi 주장 검증](./questions/q2-harnesslens-pi-claims-check.md) - *기능 주장은 대부분 사실. 단 하위 디렉터리 AGENTS.md는 자동 로드 안 됨, 차단은 RPC가 아닌 extension `tool_call`로만 가능*
- [Q3: RPC prompt 흐름과 RPC의 정체](./questions/q3-rpc-prompt-flow.md) - *RPC는 패키지가 아닌 coding-agent의 입출력 adapter. 조립은 AgentSession/createAgentSession이 담당*
- [Q4: pi-ai 패키지의 역할](./questions/q4-ai-package-roles.md) - *api(wire 프로토콜 10종)와 provider(벤더 약 42개)를 분리한 통합 LLM 층. agent-core는 streamFn 주입으로만 ai를 쓰고, coding-agent가 Models 런타임을 연결*
- [Q5: agent-loop 동작](./questions/q5-agent-loop.md) - *상태 없는 이중 루프(tool/steering → follow-up). 정책은 전부 AgentLoopConfig hook, 실패는 toolResult 에러로 LLM에 되돌리고 error/aborted만 hard exit*
- [Q6: Agent 클래스](./questions/q6-agent-class.md) - *상태는 이벤트(processEvents)로만 갱신, 구독자는 순차 await, 루프 밖 예외도 가짜 error 메시지로 이벤트 순서 보장*
- [Q7: coding-agent의 hook 구현](./questions/q7-agent-session-hooks.md) - *세션 파일 projection이 대화 원본(prepareRequest에서 교체). 재시도(3회, 2·4·8s)와 overflow compaction(1회)은 루프 밖 _runAgentPrompt가 agent.continue()로 처리*
- [Q8: 세션 projection](./questions/q8-session-projection.md) - *append-only JSONL 트리(id/parentId). leaf→root 경로 → 최신 compaction으로 자르기 → context_edit 적용 → 메시지 변환. 숨김·요약은 새 entry로 표현*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **축적된 위키 지식**: [wiki/projects/pi.md](../../wiki/projects/pi.md)
