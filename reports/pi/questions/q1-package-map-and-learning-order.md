# Q1: 각 패키지는 무엇이고, 학습은 어떤 순서로 하나?

- **Commit**: `4259686d9290c0d73ae7192b796aee3e530a9779` · **작성일**: 2026-09-29 · **목적**: 학습
- **관련 그림**: [structure.html](../diagrams/structure.html)

## 결론

핵심 경로(`pi-ai → pi-agent-core → pi-coding-agent`)를 **아래부터 위로** 먼저 읽는다. 이어서 작고 독립적인 도구 패키지를 보고, `chord`와 원격·durable 계열은 마지막에 본다. `chord` 계열은 새 실험 트랙이라 **기존 동작을 이해하는 데는 필요 없다**.

## 패키지 요약 (src 크기 = `*.test.ts` 제외 `.ts` 라인 수)

| 순위 | 패키지 | 한 줄 설명 | src 규모 | 내부 의존 |
|---|---|---|---|---|
| 1 | `ai` (pi-ai) | 여러 LLM provider를 하나의 streaming API로 통합. 인증 해석, 토큰·비용 집계, 중간에 모델 바꾸기(hand-off) 지원 | 191 files / 25.9k | telemetry |
| 2 | `agent` (pi-agent-core) | tool 실행과 이벤트 streaming을 갖춘 상태 기반 agent. `Agent` + `agent-loop` | 117 / 33.6k | ai, chord, telemetry |
| 3 | `coding-agent` | 제품 본체 `pi` CLI. read/bash/edit/write 도구, 세션, extension, interactive/print/rpc 모드 | 301 / 83.1k | ai, agent, tui, codemode, mcp, chord (+원격 3종은 devDep) |
| 4 | `tui` (pi-tui) | differential rendering 기반의 깜빡임 없는 터미널 UI 프레임워크 | 45 / 19.2k | 없음 (leaf) |
| 5 | `codemode` | 모델이 쓴 JS를 QuickJS(WASM)에서 실행. 가능한 일은 주입된 tool 호출뿐이고, 중간 tool 결과는 LLM context에 들어가지 않음 | 10 / 1.6k | 없음 (leaf) |
| 5 | `mcp` (pi-mcp) | 공식 SDK 없이 직접 만든 작은 MCP client (stdio / Streamable HTTP) | 18 / 3.0k | 없음 (leaf) |
| 6 | `telemetry` | vendor 중립 telemetry 계약(`TelemetryContext`/`TelemetrySpan`) | 6 / 0.9k | 없음 |
| 7 | `chord` | plugin 기반 앱 조합 런타임: facet, service, replicated state, 원격 service 경계 | 29 / 8.8k | 없음 |
| 8 | `protocol` | 원격 세션용 CBOR envelope + byte-stream framing (protocol v8) | 8 / 0.9k | chord |
| 8 | `client` | protocol 위의 transport 중립 client | 8 / 1.1k | chord, protocol |
| 8 | `server` | 새 durable Session / Agent Harness 인터페이스용 실험적 로컬 서버 | 16 / 2.0k | chord, agent, protocol |
| 9 | `session-backends/sqlite-node` | `node:sqlite` 기반 agent-core Session 저장소 | 15 / 2.0k | agent, ai |
| 9 | `durable` | "Pico" durable 대화·task·문서 런타임 (memory/JSONL/SQLite 저장) | 37 / 11.6k | chord, ai |
| — | `evals` | `vitest-evals` 기반 coding-agent 행동 평가 (테스트 전용) | 5 / 1.4k | ai, coding-agent |

## 우선순위 근거

1. **pi-ai가 가장 아래 토대다** — 내부 의존이 telemetry뿐이고, coding-agent가 가장 많이 import하는 패키지다(94회). `코드 확인`
2. **agent-core는 두 층으로 나뉜다** — 기본 루프인 `agent-loop.ts`(940줄)와 `agent.ts`(613줄)는 `pi-ai`만 import한다. `chord` import 32회는 대부분 `harness/`(특히 `harness/pico3/` 18개 파일)에서 나온다. 따라서 루프 이해에는 chord가 필요 없다. `코드 확인`
3. **새 harness는 실험 트랙이다** — `pico3`/`AgentHarness`를 쓰는 coding-agent 코드는 `src/experimental/` 아래(`session-worker.ts`, `micro/*`)에서만 발견됐다. 그래서 chord·server·protocol·durable은 차세대 실험 아키텍처로 보인다. `추론` (공식 로드맵 미확인)
4. **coding-agent는 83k줄이라 통독하지 않는다** — `main.ts` → `core/agent-session.ts` → 내장 도구 → `modes/` 순으로 필요한 경로만 따라간다.
5. **tui, codemode, mcp는 독립 leaf다** — 핵심 경로와 무관하게 각각 따로 학습할 수 있다. 특히 codemode(1.6k)와 mcp(3k)는 작고 설계 패턴이 뚜렷해서 가성비가 좋다.

## 권장 학습 순서

- **1단계 (핵심)**: `ai/src/types.ts`, `ai/src/index.ts` → provider 하나(`ai/src/providers/anthropic.ts`) → `agent/src/agent-loop.ts`, `agent/src/agent.ts`
- **2단계 (제품)**: `coding-agent/src/main.ts` → `core/agent-session.ts` → `core/tools/` → `modes/`
- **3단계 (독립 모듈, 관심별)**: codemode, mcp, tui
- **4단계 (차세대 실험)**: chord → protocol/client/server → agent `harness/pico3` → durable

## 실행한 명령

- `packages/*/package.json` dependencies 추출
- src import 집계 → [`artifacts/pi/static-analysis/cross-package-imports.txt`](../../../artifacts/pi/static-analysis/cross-package-imports.txt)
- 패키지별 src 라인 수 (`*.test.ts` 제외), README 도입부 확인

## 남은 질문

- chord·durable·server 계열이 기존 `Agent`/`AgentSession`을 대체하려는 것인가? (CHANGELOG·issue 확인 필요)
- `pi-durable`에는 레포 내 소비자가 없다 — 어디서 쓰이는가?
