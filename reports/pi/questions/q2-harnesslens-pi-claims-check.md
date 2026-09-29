# Q2: HarnessLens 기획서에 나온 pi 관련 주장은 사실인가?

- **Commit**: `4259686d9290c0d73ae7192b796aee3e530a9779` · **작성일**: 2026-09-29
- **대상**: 외부 LLM이 작성한 "HarnessLens" 기획서의 pi 관련 서술
- **방법**: `repos/pi/packages/coding-agent`의 `docs/`, `examples/`, `src/`를 직접 대조

## 결론

기능에 대한 주장은 **대부분 사실**이다. 다만 **설계에 직결되는 전제 2개가 pi의 실제 동작과 다르다.**
1. pi는 `backend/AGENTS.md` 같은 하위 디렉터리 규칙을 자동으로 불러오지 않는다.
2. RPC client만으로는 tool 실행을 막을 수 없고, pi extension이 필요하다.

## 주장별 판정

| # | 주장 | 판정 | 근거 (검증 수준) |
|---|---|---|---|
| 1 | SDK embedding + RPC integration 공식 제공 | ✅ 사실 | `docs/sdk.md`, `docs/rpc.md` (코드 확인) |
| 2 | RPC = JSONL stdin/stdout 장기 실행 subprocess, IDE·custom UI용 | ✅ 사실 | `docs/rpc.md` 1–4행: "long-lived subprocess … IDEs, and custom user interfaces", strict JSONL(LF) framing (코드 확인) |
| 3 | SDK는 Node.js/Bun in-process 방식 | ✅ 사실 | `docs/rpc.md` 비교표 "Node.js or Bun hosts". 추가로 TS용 `RpcClient`를 export하고 예시 `examples/rpc-client.ts`가 있음 (코드 확인) |
| 4 | 기본 tool = read/bash/edit/write | ✅ 사실 | `src/core/sdk.ts:265` `defaultActiveToolNames = ["read","bash","edit","write"]` (코드 확인) |
| 5 | grep/find/ls도 built-in, 선택 활성화 | ✅ 사실 (+보충) | `src/core/tools/index.ts` `ToolName`에 `powershell`도 있음 (코드 확인) |
| 6 | SDK에서 tool allowlist 가능 | ✅ 사실 (+보충) | `sdk.ts` 옵션에 allowlist `tools`, denylist `excludeTools`, 전체 끄기 `noTools: "all"\|"builtin"`, 추가 `customTools`. settings에 `defaultTools`도 있음 (코드 확인) |
| 7 | 이벤트 `tool_execution_start/end`, `message_update`, `agent_settled` | ✅ 사실 | agent·coding-agent src에서 emit 확인. `tool_execution_update`, `turn_*`, `agent_before_settle`도 있음. `agent_settled`는 "더 이상 자동으로 이어갈 작업(retry/compaction/queue) 없음"을 뜻함 (`docs/json.md:48`) (코드 확인) |
| 8 | subscription / API key / local model 지원, `/login` | ✅ 사실 | `docs/quickstart.md:3`, `docs/providers.md:8`. local은 llama.cpp 문서 + `models.json`으로 Ollama/LM Studio/vLLM 연결 (코드 확인) |
| 9 | edit가 SDK consumer에게 unified patch 제공 | ✅ 사실 | `src/core/tools/edit.ts:73-74, 202` — `details.patch` = `generateUnifiedPatch()`, `details.diff`도 있음. RPC `tool_execution_end.result.details`로도 전달됨 (`docs/json.md:114`) (코드 확인. RPC로 patch가 실제로 오는지는 실행 미확인) |
| 10 | 출처 링크 | ⚠️ 일부 비공식 | `brahdian/pi_coding_agent`, `pi-packages/earendil-works-pi`는 공식 `earendil-works/pi`가 아닌 제3자 mirror·fork. 해당 내용 자체는 공식 레포에서 재확인됨 |

## 설계에 영향을 주는 차이 (기획서의 암묵적 전제)

### A. 디렉터리별 AGENTS.md 적용 — ❌ pi 동작과 다름
- 기획서 전제: `backend/AGENTS.md → applies backend/**`
- 실제 동작: `src/core/resource-loader.ts` `loadProjectContextFiles()`가 불러오는 범위
  1. global(`agentDir`)
  2. **cwd부터 루트까지의 상위 디렉터리**
  - 각 디렉터리에서는 `AGENTS.override.md > AGENTS.md > AGENTS.MD > CLAUDE.md > CLAUDE.MD` 중 **첫 번째 1개만** 쓴다.
  - **하위 디렉터리는 탐색하지 않는다.** 따라서 repo 루트에서 실행하면 `backend/AGENTS.md`는 agent가 직접 `read`하지 않는 한 context에 들어가지 않는다. (코드 확인)
- 영향: "Expected Context"에서 하위 규칙은 **pi가 보장하지 않는 context**다. 오히려 누락이 자주 일어날 곳이고, HarnessLens가 잡아낼 가치가 있다.

### B. AGENTS.md는 tool 이벤트로 보이지 않는다
- 기획서의 trace `Prompt → AGENTS.md → grep …`에서 AGENTS.md는 `read` 이벤트가 아니다. system prompt에 **자동 주입**된다.
- RPC `get_state` 응답 필드에는 불러온 context 파일 목록이 없다(`docs/rpc-commands.md` get_state). SDK에서는 `ResourceLoader.getAgentsFiles()`로 얻을 수 있다(`resource-loader.ts:135`). (코드 확인)
- 영향: RPC만 쓰면 "자동 주입된 context"를 알려면 위 A의 탐색 규칙을 HarnessLens가 직접 재현하거나, extension/SDK로 꺼내야 한다. extension `before_agent_start`의 `systemPromptOptions`로 얻을 수 있는지는 `미확인`.

### C. Policy Engine의 DENY — RPC client 단독으로는 불가
- RPC 명령(`docs/rpc-commands.md`)에는 tool 승인·거부 명령이 없다.
- 차단 수단은 **extension의 `tool_call` handler**다. `return { block: true, reason }`로 막는다(`docs/extensions.md:105,169-175`). handler가 실패하면 fail-safe로 차단한다(`:256`).
- extension의 `ctx.ui.confirm` 등은 RPC에서 `extension_ui_request`/`response`로 client에 전달된다(`docs/rpc-extension-ui.md`).
- 공식 보안 문서: "does not ask for approval before every tool call", "lack of a built-in sandbox" (`docs/security.md:3,99`)
- 영향: 구조는 `Tauri → pi RPC + HarnessLens 전용 pi extension(-e)`이 되어야 한다. 즉 **policy는 extension에 둔다**.

### D. bash 파일 변경 감지
- pi에는 bash 안의 파일 변경(`sed -i`, `python -c`)을 구분하는 기능이 없다(`추론`: 관련 코드 미발견).
- `tool_call`에서 bash `command`를 검사하는 heuristic 경고는 C의 extension으로 구현할 수 있다.

## 실행한 명령
- `grep`/`sed`로 `docs/{rpc,rpc-commands,rpc-extension-ui,json,sdk,extensions,providers,models,quickstart,security}.md`, `src/core/{sdk,resource-loader}.ts`, `src/core/tools/{index,edit}.ts` 대조
- 이벤트 타입 집계: `grep -rhoE 'type: "(tool_execution_|message_|agent_|turn_)…"' agent/src coding-agent/src`

## 남은 질문
- RPC로 `tool_execution_end.result.details.patch`가 실제로 오는지 → `pi --mode rpc`로 실행 확인
- extension `before_agent_start`에서 주입된 context 파일 목록을 얻을 수 있는가
