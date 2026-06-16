---
type: deepwiki-translation
repo: codex
source: artifacts/codex/deepwiki/pages-md/7-sdks-and-external-integrations.md
deepwiki_url: https://deepwiki.com/openai/codex/7-sdks-and-external-integrations
section: "7"
order: 65
---

# SDK와 외부 통합

<details>
<summary>관련 소스 파일</summary>

다음 파일들은 이 위키 페이지를 생성하기 위한 컨텍스트로 사용되었습니다.

- [.github/workflows/python-runtime-build.yml](.github/workflows/python-runtime-build.yml)
- [.github/workflows/python-runtime-release.yml](.github/workflows/python-runtime-release.yml)
- [.github/workflows/python-sdk-release.yml](.github/workflows/python-sdk-release.yml)
- [codex-rs/exec/src/event_processor_with_jsonl_output.rs](codex-rs/exec/src/event_processor_with_jsonl_output.rs)
- [codex-rs/exec/src/exec_events.rs](codex-rs/exec/src/exec_events.rs)
- [codex-rs/exec/tests/event_processor_with_json_output.rs](codex-rs/exec/tests/event_processor_with_json_output.rs)
- [codex-rs/exec/tests/suite/add_dir.rs](codex-rs/exec/tests/suite/add_dir.rs)
- [sdk/python-runtime/README.md](sdk/python-runtime/README.md)
- [sdk/python/README.md](sdk/python/README.md)
- [sdk/python/_runtime_setup.py](sdk/python/_runtime_setup.py)
- [sdk/python/docs/api-reference.md](sdk/python/docs/api-reference.md)
- [sdk/python/docs/faq.md](sdk/python/docs/faq.md)
- [sdk/python/docs/getting-started.md](sdk/python/docs/getting-started.md)
- [sdk/python/examples/README.md](sdk/python/examples/README.md)
- [sdk/python/notebooks/sdk_walkthrough.ipynb](sdk/python/notebooks/sdk_walkthrough.ipynb)
- [sdk/python/pyproject.toml](sdk/python/pyproject.toml)
- [sdk/python/scripts/update_sdk_artifacts.py](sdk/python/scripts/update_sdk_artifacts.py)
- [sdk/python/src/openai_codex/__init__.py](sdk/python/src/openai_codex/__init__.py)
- [sdk/python/src/openai_codex/api.py](sdk/python/src/openai_codex/api.py)
- [sdk/python/src/openai_codex/generated/notification_registry.py](sdk/python/src/openai_codex/generated/notification_registry.py)
- [sdk/python/src/openai_codex/generated/v2_all.py](sdk/python/src/openai_codex/generated/v2_all.py)
- [sdk/python/src/openai_codex/types.py](sdk/python/src/openai_codex/types.py)
- [sdk/python/tests/test_artifact_workflow_and_binaries.py](sdk/python/tests/test_artifact_workflow_and_binaries.py)
- [sdk/python/tests/test_contract_generation.py](sdk/python/tests/test_contract_generation.py)
- [sdk/python/tests/test_public_api_signatures.py](sdk/python/tests/test_public_api_signatures.py)
- [sdk/python/tests/test_real_app_server_integration.py](sdk/python/tests/test_real_app_server_integration.py)
- [sdk/python/uv.lock](sdk/python/uv.lock)
- [sdk/typescript/README.md](sdk/typescript/README.md)
- [sdk/typescript/eslint.config.js](sdk/typescript/eslint.config.js)
- [sdk/typescript/samples/basic_streaming.ts](sdk/typescript/samples/basic_streaming.ts)
- [sdk/typescript/src/codex.ts](sdk/typescript/src/codex.ts)
- [sdk/typescript/src/codexOptions.ts](sdk/typescript/src/codexOptions.ts)
- [sdk/typescript/src/events.ts](sdk/typescript/src/events.ts)
- [sdk/typescript/src/exec.ts](sdk/typescript/src/exec.ts)
- [sdk/typescript/src/index.ts](sdk/typescript/src/index.ts)
- [sdk/typescript/src/items.ts](sdk/typescript/src/items.ts)
- [sdk/typescript/src/thread.ts](sdk/typescript/src/thread.ts)
- [sdk/typescript/src/threadOptions.ts](sdk/typescript/src/threadOptions.ts)
- [sdk/typescript/src/turnOptions.ts](sdk/typescript/src/turnOptions.ts)
- [sdk/typescript/tests/abort.test.ts](sdk/typescript/tests/abort.test.ts)
- [sdk/typescript/tests/codexExecSpy.ts](sdk/typescript/tests/codexExecSpy.ts)
- [sdk/typescript/tests/exec.test.ts](sdk/typescript/tests/exec.test.ts)
- [sdk/typescript/tests/responsesProxy.ts](sdk/typescript/tests/responsesProxy.ts)
- [sdk/typescript/tests/run.test.ts](sdk/typescript/tests/run.test.ts)
- [sdk/typescript/tests/runStreamed.test.ts](sdk/typescript/tests/runStreamed.test.ts)

</details>



이 페이지는 Codex를 외부 애플리케이션과 워크플로에 임베드하기 위해 사용할 수 있는 공식 SDK와 통합 패키지를 고수준으로 개괄합니다. 이러한 도구를 통해 개발자는 Codex 에이전트와 프로그래밍 방식으로 상호작용하고, 대화 수명 주기를 관리하며, Model Context Protocol(MCP)을 통해 셸 기능을 확장할 수 있습니다.

## TypeScript SDK(`@openai/codex-sdk`)

TypeScript SDK는 Node.js 환경(v18+)에서 Codex와 상호작용하기 위한 고수준 promise 기반 인터페이스를 제공합니다. 이 SDK는 `@openai/codex` 패키지가 제공하는 `codex` CLI를 감싸고 표준 입출력을 통해 구조화된 JSONL 이벤트를 교환하는 방식으로 동작합니다 [sdk/typescript/README.md:1-13]().

### 핵심 구성 요소
- **`Codex` Class**: SDK의 진입점입니다. API 키, base URL, 환경 변수 재정의 같은 전역 구성을 처리합니다 [sdk/typescript/src/codex.ts:14-22]().
- **`Thread` Class**: 특정 대화 세션을 관리합니다. `_id`(thread ID)를 추적하고 턴을 실행하는 메서드를 제공합니다 [sdk/typescript/src/thread.ts:41-63]().
- **`CodexExec`**: 내부 바이너리의 `spawn` 로직을 처리하고, 구성을 `--config`, `--experimental-json` 같은 CLI 플래그로 직렬화하는 내부 유틸리티입니다 [sdk/typescript/src/exec.ts:63-87]().

### 실행 모드
SDK는 원자적 실행과 스트리밍 실행을 모두 지원합니다.
- **`thread.run()`**: 모든 이벤트를 버퍼링하고 `finalResponse`, `ThreadItem` 객체 목록, `Usage` 통계를 포함하는 완료된 `Turn` 객체를 반환합니다 [sdk/typescript/src/thread.ts:115-138]().
- **`thread.runStreamed()`**: `ThreadEvent` 객체의 `AsyncGenerator`를 반환하여 도구 호출, reasoning, 파일 변경에 대한 실시간 UI 업데이트를 가능하게 합니다 [sdk/typescript/src/thread.ts:66-112]().

자세한 내용은 [TypeScript SDK](#7.1)를 참조하세요.

**출처:** [sdk/typescript/src/codex.ts:14-22](), [sdk/typescript/src/thread.ts:41-138](), [sdk/typescript/src/exec.ts:63-87](), [sdk/typescript/src/index.ts:1-41]()

---

## Python SDK(`openai-codex`)

Python SDK는 Codex App Server와 상호작용하기 위한 네이티브 클라이언트를 제공합니다. 이 SDK는 app-server protocol schemas에서 생성된 Pydantic 모델을 활용하여 Python 개발자에게 타입 안전 인터페이스를 제공합니다 [sdk/python/README.md:1-9]().

### 주요 기능
- **클라이언트 구현**: thread 수명 주기를 관리하고 턴을 제출하기 위한 동기 `Codex`와 비동기 `AsyncCodex` 클라이언트를 모두 포함합니다 [sdk/python/src/openai_codex/api.py:76-118]().
- **Pydantic Wire Models**: 복잡한 서버 알림과 item을 로컬 Python 객체에 매핑하여 Rust 기반 `app-server`와의 호환성을 보장합니다 [sdk/python/src/openai_codex/types.py:1-102]().
- **수명 주기 관리**: thread를 시작(`thread_start`), 재개(`thread_resume`), 포크(`thread_fork`)하기 위한 고수준 메서드를 제공합니다 [sdk/python/src/openai_codex/api.py:129-210]().
- **런타임 패키징**: 게시된 SDK 빌드는 플랫폼별 바이너리를 포함하는 정확한 `openai-codex-cli-bin` 런타임 의존성을 고정합니다 [sdk/python/README.md:10-13]().

자세한 내용은 [Python SDK](#7.2)를 참조하세요.

**출처:** [sdk/python/README.md:1-20](), [sdk/python/src/openai_codex/api.py:76-210](), [sdk/python/docs/api-reference.md:1-112]()

---

## Shell Tool MCP Package(`@openai/codex-shell-tool-mcp`)

`@openai/codex-shell-tool-mcp` 패키지는 Model Context Protocol(MCP)이 로컬 셸 환경과 상호작용할 수 있게 하는 NPM 배포 도구입니다.

### 주요 기능
- **패치된 셸**: 에이전트가 명령을 가로채고 안전하게 실행할 수 있도록 `EXEC_WRAPPER`와 함께 컴파일된 Bash 및 Zsh의 특수 버전을 포함합니다.
- **샌드박스 상태**: 에이전트의 현재 권한 수준(예: `ReadOnly` vs `WorkspaceWrite`)을 셸 환경과 동기화하기 위해 `codex/sandbox-state/update` 기능을 구현합니다.
- **규칙 적용**: 작업 디렉터리에서 발견된 `.rules` 파일을 자동으로 준수하여 셸 세션 중 에이전트 동작을 제한합니다.

자세한 내용은 [Shell Tool MCP Package](#7.3)를 참조하세요.

---

## 통합 아키텍처

다음 다이어그램은 SDK가 Natural Language(사용자 입력)와 Code Entity Space(CLI 실행 및 이벤트 처리) 사이의 간극을 연결하는 방식을 보여줍니다.

### SDK to CLI Bridge (TypeScript)
```mermaid
graph TD
    subgraph "NaturalLanguageSpace"
        [UserPrompt] --> [UserInput_text_image]
    end

    subgraph "TypeScriptSDK_@openai/codex-sdk"
        [Thread_run] --> [CodexExec_run]
        [CodexExec_run] --> [JSON_parse_ThreadEvent]
    end

    subgraph "CodeEntitySpace_codex-cli"
        [CLI_codex_exec_experimental-json] --> [codex-core_Rust]
        [codex-core_Rust] --> [ThreadEvent_JSONL]
    end

    [UserInput_text_image] --> [Thread_run]
    [CodexExec_run] -- "spawn()" --> [CLI_codex_exec_experimental-json]
    [ThreadEvent_JSONL] -- "stdout" --> [JSON_parse_ThreadEvent]
    [JSON_parse_ThreadEvent] --> [Thread_run]
```
**출처:** [sdk/typescript/src/thread.ts:70-112](), [sdk/typescript/src/exec.ts:181-208](), [sdk/typescript/README.md:5-10]()

### Python SDK Session Flow
이 다이어그램은 Python SDK가 `AppServerClient`와 관련 Pydantic wire model을 통해 세션을 관리하는 방식을 보여줍니다.

```mermaid
graph LR
    subgraph "NaturalLanguageSpace"
        [Python_Script] -- "thread.run(prompt)" --> [Codex_Client]
    end

    subgraph "CodeEntitySpace_PythonSDK"
        [Codex_Client] --> [AppServerClient]
        [AppServerClient] --> [Pydantic_WireModels]
    end

    subgraph "CodeEntitySpace_AppServer"
        [JSON-RPC_v2] --> [CodexMessageProcessor]
        [CodexMessageProcessor] --> [Rust_Codex_Engine]
    end

    [AppServerClient] -- "stdio/json-rpc" --> [JSON-RPC_v2]
    [Rust_Codex_Engine] -- "TurnCompletedNotification" --> [Pydantic_WireModels]
    [Pydantic_WireModels] -- "TurnResult" --> [Python_Script]
```
**출처:** [sdk/python/src/openai_codex/api.py:76-166](), [sdk/python/README.md:3-9](), [sdk/python/docs/getting-started.md:71-78]()

---

## 요약 표

| 기능 | TypeScript SDK | Python SDK | Shell Tool MCP |
| :--- | :--- | :--- | :--- |
| **주요 대상** | Web/Node.js Apps | Data Science/Backend | Terminal/IDE |
| **통신** | CLI Stdout(JSONL) [sdk/typescript/src/exec.ts:216-225]() | App Server(JSON-RPC) [sdk/python/README.md:3]() | MCP Protocol |
| **패키지** | `@openai/codex-sdk` [sdk/typescript/README.md:10]() | `openai-codex` [sdk/python/README.md:11]() | `@openai/codex-shell-tool-mcp` |
| **소스 경로** | `sdk/typescript/` | `sdk/python/` | `shell-tool-mcp/` |
| **주요 진입점** | `Codex` [sdk/typescript/src/codex.ts:14]() | `Codex` [sdk/python/src/openai_codex/api.py:76]() | N/A(Server) |

**출처:** [sdk/typescript/README.md:10](), [sdk/typescript/src/codex.ts:14](), [sdk/typescript/src/exec.ts:216-225](), [sdk/python/README.md:11](), [sdk/python/src/openai_codex/api.py:76]()
