# Hermes Agent의 Codex 로그인 및 실행 경로

## 질문 요지

Gateway가 여러 외부 메시지 플랫폼의 입력을 모아서 `AIAgent`로 넘기는 구조는 이해했지만, 사용자가 `openai-codex`로 로그인한 경우 Hermes 내부에서 Codex를 어떤 방식으로 실행하거나 호출하는지가 핵심 질문이다.

결론부터 말하면 Hermes에는 Codex 관련 경로가 두 가지 있다.

1. 기본 경로: Codex CLI를 실행하지 않고, Hermes가 Codex backend API를 직접 호출한다.
2. 선택 경로: `codex_app_server` 런타임을 켰을 때만 `codex app-server` subprocess를 실행한다.

즉 `openai-codex`로 로그인했다고 해서 항상 Codex CLI 프로세스를 내부에서 띄우는 것은 아니다.

## 1. 기본 경로: Codex CLI를 실행하지 않음

`openai-codex`로 로그인한 기본 상태에서는 Hermes가 Codex CLI를 subprocess로 실행하지 않는다. 대신 Hermes가 자체 device-code login으로 받은 OAuth 토큰을 `~/.hermes/auth.json`에 저장하고, 그 access token을 사용해서 `https://chatgpt.com/backend-api/codex`의 Responses API를 직접 호출한다.

흐름은 다음과 같다.

```text
hermes auth / hermes model
  -> OpenAI Codex device code login
  -> access_token / refresh_token을 ~/.hermes/auth.json에 저장
  -> config.yaml의 model.provider = openai-codex

사용자 메시지
  -> Gateway 또는 CLI
  -> AIAgent
  -> provider=openai-codex 감지
  -> api_mode=codex_responses
  -> OpenAI SDK responses.stream/create로 chatgpt.com/backend-api/codex 호출
```

이 경로에서는 Codex CLI의 `codex` 바이너리를 실행하지 않는다. Hermes의 일반 agent loop가 그대로 동작하며, tool call이 나오면 Hermes의 tool dispatcher가 도구를 실행하고 결과를 다시 모델에 넣는다.

관련 근거:

- `hermes_cli/auth.py`: Codex OAuth 토큰을 Hermes auth store인 `~/.hermes/auth.json`에 저장한다.
- `hermes_cli/auth.py`: `resolve_codex_runtime_credentials()`가 `provider=openai-codex`, `base_url=https://chatgpt.com/backend-api/codex`, `api_key=access_token`을 반환한다.
- `agent/agent_init.py`: provider가 `openai-codex`이면 `api_mode`를 `codex_responses`로 설정한다.
- `agent/codex_runtime.py`: `run_codex_stream()`이 Responses API streaming 요청을 실행한다.
- `agent/transports/codex.py`: `api_mode='codex_responses'`일 때 OpenAI-style messages를 Responses API input/tools 형식으로 변환한다.

요약하면 이 기본 경로는 다음과 같다.

```text
Hermes
  -> Codex OAuth token 확보
  -> chatgpt.com/backend-api/codex 호출
  -> Hermes 자체 tool loop로 도구 실행
```

## 2. 선택 경로: 실제 Codex CLI subprocess 실행

Hermes에는 별도 옵션으로 Codex CLI의 app-server 런타임을 사용할 수 있다. 이 경로는 사용자가 명시적으로 켜야 한다.

예:

```text
/codex-runtime on
```

또는 config 기준:

```yaml
model:
  openai_runtime: codex_app_server
```

이 옵션이 켜지면 Hermes는 `codex app-server`를 subprocess로 실행한다.

```text
subprocess.Popen(["codex", "app-server"])
```

그 뒤 Hermes와 Codex app-server는 stdin/stdout 기반 newline-delimited JSON-RPC 2.0으로 통신한다.

흐름은 다음과 같다.

```text
Hermes
  -> codex app-server subprocess 실행
  -> initialize
  -> initialized
  -> thread/start
  -> turn/start
  -> item/completed, turn/completed 이벤트 수신
  -> Codex 이벤트를 Hermes messages 형태로 변환
```

이 경로에서는 terminal/file/patch/MCP 같은 실제 작업 실행의 많은 부분이 Codex runtime 안에서 처리된다. Hermes는 Codex app-server가 내보내는 이벤트를 읽고, 그 이벤트를 Hermes의 표준 message list 형태로 투영한다.

관련 근거:

- `hermes_cli/codex_runtime_switch.py`: `/codex-runtime` 명령으로 `model.openai_runtime` 값을 `auto` 또는 `codex_app_server`로 바꾼다.
- `hermes_cli/runtime_provider.py`: `model.openai_runtime == codex_app_server`이고 provider가 `openai` 또는 `openai-codex`이면 `api_mode`를 `codex_app_server`로 바꾼다.
- `agent/codex_runtime.py`: `api_mode == codex_app_server`일 때 `CodexAppServerSession`을 생성하고 `run_turn()`을 호출한다.
- `agent/transports/codex_app_server.py`: `subprocess.Popen(["codex", "app-server"])`로 Codex CLI app-server를 실행한다.
- `agent/transports/codex_app_server_session.py`: `initialize`, `thread/start`, `turn/start`, `turn/interrupt` 같은 JSON-RPC 요청을 보낸다.
- `agent/transports/codex_event_projector.py`: Codex의 `item/completed` 이벤트를 Hermes의 `{role, content, tool_calls, tool_call_id}` 메시지 형태로 변환한다.

요약하면 이 선택 경로는 다음과 같다.

```text
Hermes
  -> codex app-server subprocess 실행
  -> JSON-RPC로 thread/turn 제어
  -> Codex가 자체 runtime에서 command/file/MCP 작업 수행
  -> Hermes가 이벤트를 받아 세션 메시지로 변환
```

## 3. 두 경로의 차이

| 구분 | 기본 `openai-codex` 경로 | `codex_app_server` 경로 |
|---|---|---|
| Codex CLI 실행 | 실행하지 않음 | `codex app-server` 실행 |
| 인증 저장 위치 | Hermes의 `~/.hermes/auth.json` | Codex CLI의 자체 auth/config도 사용 |
| 모델 호출 | Hermes가 `chatgpt.com/backend-api/codex` 직접 호출 | Codex app-server가 처리 |
| API 모드 | `codex_responses` | `codex_app_server` |
| tool 실행 | Hermes tool dispatcher | Codex runtime 중심, Hermes 도구는 MCP callback으로 일부 제공 |
| 통신 방식 | OpenAI SDK Responses API | stdio JSON-RPC |
| 활성화 조건 | provider가 `openai-codex`이면 기본 적용 | `/codex-runtime on` 또는 `model.openai_runtime: codex_app_server` |

## 4. 왜 Hermes가 Codex CLI 토큰을 그대로 쓰지 않는가

코드 주석상 Hermes는 Codex CLI나 VS Code extension과 refresh token rotation 충돌이 나지 않도록, Hermes 전용 Codex OAuth 세션을 따로 유지한다.

즉 Codex CLI의 `~/.codex/auth.json`을 무조건 공유해서 쓰는 것이 아니라, 필요하면 기존 Codex CLI 토큰을 import할 수는 있지만 최종적으로는 Hermes auth store에 별도로 저장한다.

관련 흐름:

```text
~/.codex/auth.json 존재 확인
  -> 사용자가 import 허용
  -> Hermes가 ~/.hermes/auth.json에 복사 저장
  -> 이후 Hermes는 자체 저장소 기준으로 refresh
```

이 설계의 이유는 한 클라이언트가 refresh token을 갱신하면서 다른 클라이언트의 세션을 깨뜨리는 문제를 피하기 위해서다.

## 5. `codex_app_server`를 켜면 MCP 설정도 옮긴다

`codex_app_server`를 켤 때 Hermes는 Codex가 Hermes 쪽 도구를 일부 호출할 수 있도록 `~/.codex/config.toml`에 MCP 서버 설정을 migration한다.

특히 `hermes-tools`라는 MCP server entry를 만들어 Codex subprocess가 Hermes의 일부 도구 표면으로 callback할 수 있게 한다.

대표적으로 언급되는 도구:

- `web_search`
- `web_extract`
- `browser_*`
- `vision_analyze`
- `image_generate`
- `skill_view`
- `skills_list`
- `text_to_speech`
- `kanban_*`

단, `delegate_task`, `memory`, `session_search`, `todo`처럼 Hermes agent loop context가 필요한 기능은 기본 Hermes runtime에서만 의미가 있다고 코드 메시지에 명시되어 있다.

관련 근거:

- `hermes_cli/codex_runtime_plugin_migration.py`: Hermes MCP config를 Codex의 `~/.codex/config.toml` 형식으로 변환한다.
- `hermes_cli/codex_runtime_plugin_migration.py`: `hermes-tools` MCP entry를 생성한다.
- `hermes_cli/codex_runtime_switch.py`: runtime enable 시 migration을 실행하고 결과 메시지를 만든다.

## 6. 내부 메시지 변환

Codex app-server 런타임에서는 Codex가 자체 이벤트를 발생시킨다.

예:

- `agentMessage`
- `reasoning`
- `commandExecution`
- `fileChange`
- `mcpToolCall`
- `dynamicToolCall`
- `turn/completed`

Hermes는 이 이벤트를 그대로 저장하지 않고, `CodexEventProjector`를 통해 Hermes의 기존 대화 메시지 구조로 변환한다.

예를 들어 Codex의 `commandExecution`은 Hermes 입장에서는 다음처럼 보이도록 변환된다.

```text
assistant message:
  tool_calls = [{ name: "exec_command", arguments: ... }]

tool message:
  tool_call_id = ...
  content = command output
```

Codex의 `fileChange`는 `apply_patch` tool call처럼 변환된다.

이 덕분에 Hermes의 세션 저장, memory review, skill nudge 같은 기존 후처리 로직이 `codex_app_server` 런타임에서도 같은 message 형태를 읽을 수 있다.

## 7. 최종 정리

`openai-codex` 로그인은 기본적으로 “Codex CLI 실행”을 뜻하지 않는다.

기본값에서는 다음처럼 동작한다.

```text
Hermes 자체 agent loop
  + Hermes가 관리하는 Codex OAuth token
  + chatgpt.com/backend-api/codex Responses API 직접 호출
  + Hermes 자체 tool dispatcher
```

반면 `codex_app_server`를 켠 경우에는 다음처럼 동작한다.

```text
Hermes
  + codex app-server subprocess
  + stdio JSON-RPC
  + Codex runtime의 command/file/patch/MCP 처리
  + Hermes message projection
```

따라서 “Codex로 로그인했으면 내부에서 Codex를 실행해야 하는 것 아닌가?”에 대한 답은 다음과 같다.

기본적으로는 실행하지 않는다. Hermes가 Codex OAuth 토큰으로 Codex backend API를 직접 호출한다. Codex CLI를 실제 subprocess로 실행하는 것은 `codex_app_server` 런타임을 명시적으로 활성화했을 때만 발생한다.

