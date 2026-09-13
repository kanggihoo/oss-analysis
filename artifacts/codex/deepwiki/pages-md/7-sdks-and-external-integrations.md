# SDKs and External Integrations

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

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



This page provides a high-level overview of the official SDKs and integration packages available for embedding Codex into external applications and workflows. These tools allow developers to interact with the Codex agent programmatically, manage conversation lifecycles, and extend shell capabilities via the Model Context Protocol (MCP).

## TypeScript SDK (`@openai/codex-sdk`)

The TypeScript SDK provides a high-level, promise-based interface for interacting with Codex from Node.js environments (v18+). It functions by wrapping the `codex` CLI (provided by the `@openai/codex` package) and exchanging structured JSONL events over standard I/O [sdk/typescript/README.md:1-13]().

### Core Components
- **`Codex` Class**: The entry point for the SDK. It handles global configuration such as API keys, base URLs, and environment variable overrides [sdk/typescript/src/codex.ts:14-22]().
- **`Thread` Class**: Manages a specific conversation session. It tracks the `_id` (thread ID) and provides methods to execute turns [sdk/typescript/src/thread.ts:41-63]().
- **`CodexExec`**: An internal utility that handles the `spawn` logic for the underlying binary, serializing configuration into CLI flags like `--config` and `--experimental-json` [sdk/typescript/src/exec.ts:63-87]().

### Execution Modes
The SDK supports both atomic and streaming execution:
- **`thread.run()`**: Buffers all events and returns a completed `Turn` object containing the `finalResponse`, a list of `ThreadItem` objects, and `Usage` statistics [sdk/typescript/src/thread.ts:115-138]().
- **`thread.runStreamed()`**: Returns an `AsyncGenerator` of `ThreadEvent` objects, allowing real-time UI updates for tool calls, reasoning, and file changes [sdk/typescript/src/thread.ts:66-112]().

For details, see [TypeScript SDK](#7.1).

**Sources:** [sdk/typescript/src/codex.ts:14-22](), [sdk/typescript/src/thread.ts:41-138](), [sdk/typescript/src/exec.ts:63-87](), [sdk/typescript/src/index.ts:1-41]()

---

## Python SDK (`openai-codex`)

The Python SDK provides a native client for interacting with the Codex App Server. It utilizes Pydantic models generated from the app-server protocol schemas to provide a type-safe interface for Python developers [sdk/python/README.md:1-9]().

### Key Features
- **Client Implementation**: Includes both synchronous `Codex` and asynchronous `AsyncCodex` clients for managing thread lifecycles and submitting turns [sdk/python/src/openai_codex/api.py:76-118]().
- **Pydantic Wire Models**: Maps complex server notifications and items to local Python objects, ensuring compatibility with the Rust-based `app-server` [sdk/python/src/openai_codex/types.py:1-102]().
- **Lifecycle Management**: Provides high-level methods for starting (`thread_start`), resuming (`thread_resume`), and forking (`thread_fork`) threads [sdk/python/src/openai_codex/api.py:129-210]().
- **Runtime Packaging**: Published SDK builds pin an exact `openai-codex-cli-bin` runtime dependency containing the platform-specific binary [sdk/python/README.md:10-13]().

For details, see [Python SDK](#7.2).

**Sources:** [sdk/python/README.md:1-20](), [sdk/python/src/openai_codex/api.py:76-210](), [sdk/python/docs/api-reference.md:1-112]()

---

## Shell Tool MCP Package (`@openai/codex-shell-tool-mcp`)

The `@openai/codex-shell-tool-mcp` package is an NPM-distributed tool that enables the Model Context Protocol (MCP) to interact with local shell environments.

### Key Features
- **Patched Shells**: Includes specialized versions of Bash and Zsh compiled with an `EXEC_WRAPPER` to allow the agent to intercept and safely execute commands.
- **Sandbox State**: Implements the `codex/sandbox-state/update` capability to synchronize the agent's current permission level (e.g., `ReadOnly` vs `WorkspaceWrite`) with the shell environment.
- **Rule Enforcement**: Automatically respects `.rules` files found in the working directory to constrain agent behavior during shell sessions.

For details, see [Shell Tool MCP Package](#7.3).

---

## Integration Architecture

The following diagrams illustrate how the SDKs bridge the gap between Natural Language (user input) and the Code Entity Space (CLI execution and event processing).

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
**Sources:** [sdk/typescript/src/thread.ts:70-112](), [sdk/typescript/src/exec.ts:181-208](), [sdk/typescript/README.md:5-10]()

### Python SDK Session Flow
This diagram shows how the Python SDK manages sessions via the `AppServerClient` and its associated Pydantic wire models.

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
**Sources:** [sdk/python/src/openai_codex/api.py:76-166](), [sdk/python/README.md:3-9](), [sdk/python/docs/getting-started.md:71-78]()

---

## Summary Table

| Feature | TypeScript SDK | Python SDK | Shell Tool MCP |
| :--- | :--- | :--- | :--- |
| **Primary Target** | Web/Node.js Apps | Data Science/Backend | Terminal/IDE |
| **Communication** | CLI Stdout (JSONL) [sdk/typescript/src/exec.ts:216-225]() | App Server (JSON-RPC) [sdk/python/README.md:3]() | MCP Protocol |
| **Package** | `@openai/codex-sdk` [sdk/typescript/README.md:10]() | `openai-codex` [sdk/python/README.md:11]() | `@openai/codex-shell-tool-mcp` |
| **Source Path** | `sdk/typescript/` | `sdk/python/` | `shell-tool-mcp/` |
| **Main Entry** | `Codex` [sdk/typescript/src/codex.ts:14]() | `Codex` [sdk/python/src/openai_codex/api.py:76]() | N/A (Server) |

**Sources:** [sdk/typescript/README.md:10](), [sdk/typescript/src/codex.ts:14](), [sdk/typescript/src/exec.ts:216-225](), [sdk/python/README.md:11](), [sdk/python/src/openai_codex/api.py:76]()
