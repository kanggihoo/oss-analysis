# hermes-agent Gateway -> Codex -> Session 흐름 집중 분석

분석 목적: 여러 메시징 플랫폼에서 들어온 메시지가 Gateway를 거친 뒤 어떻게 `AIAgent`와 Codex 런타임으로 전달되는지, 그리고 세션이 어떻게 자동 관리되는지 확인한다.

## 결론

`openai-codex` 로그인 후 기본 경로는 `codex -p "메시지"` 같은 터미널 CLI 실행이 아니다. Hermes가 자체 OAuth 토큰을 `~/.hermes/auth.json`에 저장하고, 그 access token을 `api_key`로 써서 `https://chatgpt.com/backend-api/codex`에 OpenAI SDK Responses API 형태로 직접 호출한다.

실제 `codex` 바이너리를 subprocess로 띄우는 경로는 별도 옵션인 `codex_app_server` 런타임을 켰을 때만 동작한다. 이때도 `codex -p`가 아니라 `codex app-server`를 실행하고, Hermes와 Codex CLI app-server가 stdio JSON-RPC 2.0으로 `thread/start`, `turn/start`, `turn/interrupt`를 주고받는다.

Gateway 세션은 플랫폼별 메시지를 `MessageEvent`와 `SessionSource`로 정규화한 뒤, deterministic `session_key`를 만들고, 그 키에 매핑된 `session_id`의 transcript를 불러와 `AIAgent.run_conversation(..., conversation_history=...)`에 넘기는 구조다.

## 1. Gateway 이후 전체 흐름

대표 흐름:

```text
Telegram/Slack/Discord/... adapter
  -> MessageEvent + SessionSource
  -> BasePlatformAdapter.handle_message / _process_message_background
  -> GatewayRunner._handle_message_with_agent
  -> SessionStore.get_or_create_session(source)
  -> SessionStore.load_transcript(session_id)
  -> GatewayRunner._run_agent(...)
  -> AIAgent(..., session_id=session_id, session_db=SessionDB)
  -> AIAgent.run_conversation(message, conversation_history=agent_history, task_id=session_id)
  -> Codex Responses API or codex app-server
  -> result.messages / final_response
  -> SessionDB + JSONL transcript persistence
  -> adapter.send(...) back to original platform
```

근거:

- `gateway/platforms/base.py`: 공통 이벤트 처리, active session, pending message, interrupt 관리.
- `gateway/session.py`: `SessionSource`, `SessionEntry`, `SessionStore`, `build_session_key`, transcript load/save.
- `gateway/run.py`: `_handle_message_with_agent`, `_run_agent`, AIAgent 생성과 `run_conversation` 호출.
- `run_agent.py`: `AIAgent._persist_session`, `_flush_messages_to_session_db`.

## 2. Gateway가 메시지를 세션으로 묶는 방식

플랫폼 adapter는 각 플랫폼 payload를 공통 `MessageEvent`로 바꾸고, 원천 정보는 `SessionSource`에 담는다.

`gateway/session.py`의 `build_session_key()`가 세션 라우팅의 단일 기준이다.

- DM: `agent:main:{platform}:dm:{chat_id}` 형태. thread가 있으면 thread까지 붙는다.
- group/channel: `agent:main:{platform}:{chat_type}:{chat_id}`에 thread_id를 붙이고, 설정에 따라 user_id/user_id_alt도 붙인다.
- thread는 기본적으로 shared session이다. `thread_sessions_per_user`가 켜진 경우에만 user별로 나뉜다.
- group/channel은 기본값상 `group_sessions_per_user=True`라 사용자별로 분리된다.

`SessionStore.get_or_create_session()`는 이 `session_key`를 기준으로 기존 `SessionEntry`를 찾고, 없거나 reset policy에 걸리면 새 `session_id`를 만든다. 새 ID 형식은 대략 `YYYYMMDD_HHMMSS_<uuid8>`이다.

## 3. Gateway가 AIAgent에 넘기는 내용

`GatewayRunner._handle_message_with_agent()`는 다음을 수행한다.

- `session_store.get_or_create_session(source)`로 `session_key/session_id` 확보.
- `build_session_context(source, config, session_entry)`로 플랫폼/채팅/사용자 맥락 생성.
- `build_session_context_prompt()` 결과를 ephemeral system prompt로 주입.
- `session_store.load_transcript(session_id)`로 과거 메시지 복원.
- `_run_agent(...)` 호출.

`GatewayRunner._run_agent()` 안에서는 기존 transcript를 `agent_history`로 변환한다. 이때 단순 user/assistant 메시지는 `{role, content}`로 정리하고, tool call이 있는 assistant/tool 메시지는 `tool_calls`, `tool_call_id`, reasoning, Codex replay 필드를 보존한다. 그 다음 `AIAgent`를 만들거나 `_agent_cache`에서 재사용하고, 최종적으로 다음 형태로 호출한다.

```python
agent.run_conversation(
    _run_message,
    conversation_history=agent_history,
    task_id=session_id,
)
```

중요한 점: Gateway는 메시지마다 새 `AIAgent`를 만들 수도 있지만, `session_id`와 `conversation_history`를 주입하므로 이전 대화를 이어갈 수 있다. 또한 `_agent_cache`가 있어 설정 signature가 같으면 같은 session_key의 agent를 재사용해 prompt caching 비용을 줄인다.

## 4. Codex 로그인과 기본 전달 경로

`hermes_cli/auth.py`에 Codex 관련 주석이 명확하다. OpenAI Codex OAuth token은 `~/.hermes/auth.json`에 저장되며, `~/.codex/`와 분리된다. 이유는 Codex CLI나 VS Code extension과 refresh token rotation이 충돌하지 않게 하기 위해서다.

로그인 흐름:

```text
hermes auth / hermes model
  -> _login_openai_codex()
  -> _codex_device_code_login()
  -> auth.openai.com device code flow
  -> access_token / refresh_token 수신
  -> _save_codex_tokens()
  -> ~/.hermes/auth.json 저장
  -> config.yaml model.provider=openai-codex 갱신
```

`resolve_codex_runtime_credentials()`는 Hermes auth store에서 token을 읽고, access token이 곧 만료될 경우 refresh token으로 갱신한 뒤 다음 runtime credential을 돌려준다.

```text
provider = openai-codex
base_url = https://chatgpt.com/backend-api/codex
api_key = access_token
source = hermes-auth-store
auth_mode = chatgpt
```

기본 `api_mode`는 `codex_responses`다. `agent/agent_init.py`에서도 provider가 `openai-codex`면 `agent.api_mode = "codex_responses"`로 잡는다.

## 5. Codex에 메시지가 실제 전달되는 방식

기본 경로:

```text
AIAgent.run_conversation()
  -> agent.api_mode == "codex_responses"
  -> agent/transports/codex.py ResponsesApiTransport
  -> agent/codex_runtime.py run_codex_stream()
  -> OpenAI SDK client.responses.stream(**api_kwargs)
  -> chatgpt.com/backend-api/codex
```

`agent/codex_runtime.py`의 `run_codex_stream()`는 `active_client.responses.stream(**api_kwargs)`를 호출한다. streaming이 깨지면 `run_codex_create_stream_fallback()`에서 `responses.create(stream=True)`로 fallback한다.

이 경로에서는 Hermes의 일반 agent loop가 살아 있다. 모델이 tool call을 반환하면 Hermes의 tool dispatcher가 도구를 실행하고, 결과를 다시 메시지에 붙여 다음 API call로 이어간다.

검색 결과 `codex -p` 실행 경로는 확인되지 않았다. `codex` subprocess 사용은 `agent/transports/codex_app_server.py`의 `codex app-server`뿐이다.

## 6. codex_app_server 옵션 경로

`model.openai_runtime: codex_app_server` 또는 `/codex-runtime` 토글로 켜지는 선택 경로다.

활성 조건:

- provider가 `openai` 또는 `openai-codex`.
- runtime 설정이 `codex_app_server`.
- `agent.api_mode == "codex_app_server"`.

실제 실행:

```text
CodexAppServerClient
  -> subprocess.Popen([codex_bin, "app-server", ...])
  -> stdio JSON-RPC 2.0
  -> initialize
  -> thread/start
  -> turn/start
  -> item/completed, turn/completed 등 notification 수신
```

`agent/conversation_loop.py`는 `agent.api_mode == "codex_app_server"`이면 일반 Hermes tool loop를 우회하고 `agent._run_codex_app_server_turn(...)`로 바로 반환한다. `agent/codex_runtime.py`의 `run_codex_app_server_turn()`는 `CodexAppServerSession.run_turn(user_input=user_message)`를 호출하고, 반환된 Codex 이벤트를 `projected_messages`로 Hermes 메시지 배열에 splice한다.

이 경로에서는 command/file/MCP류 실행이 Codex app-server 내부 이벤트로 들어오며, `agent/transports/codex_event_projector.py`가 `commandExecution`, `fileChange`, `mcpToolCall`, `dynamicToolCall` 등을 Hermes의 assistant/tool message 형태로 재구성한다.

## 7. 자동 세션 관리

세션은 두 층으로 관리된다.

첫째, Gateway 레벨:

- `gateway/sessions/sessions.json` 성격의 index가 `session_key -> session_id` 매핑을 유지한다.
- `SessionStore.get_or_create_session()`이 reset policy, idle expiry, suspended, resume_pending 상태를 평가한다.
- `SessionStore.load_transcript()`가 SQLite `SessionDB.get_messages_as_conversation()`을 우선 읽고, legacy JSONL에 더 많은 메시지가 있으면 JSONL을 사용한다.
- `SessionStore.rewrite_transcript()`는 `/retry`, `/undo`, `/compress` 같은 transcript 재작성 흐름에서 SQLite와 JSONL을 함께 갱신한다.

둘째, AIAgent/SQLite 레벨:

- `agent/agent_init.py`는 `session_id`가 주어지면 그대로 쓰고, 없으면 `YYYYMMDD_HHMMSS_<uuid6>` 형식으로 생성한다.
- `run_conversation()` 시작 시 `agent._ensure_db_session()`이 세션 row를 보장한다.
- `run_agent.py`의 `_persist_session()`은 메시지를 JSON log와 SQLite에 저장한다.
- `_flush_messages_to_session_db()`는 `conversation_history` 길이와 `_last_flushed_db_idx`를 기준으로 이미 저장된 과거 메시지를 중복 저장하지 않고 새 메시지만 `SessionDB.append_message()`로 넣는다.
- SQLite schema는 `sessions`와 `messages` 테이블을 갖고, `messages`에는 `role`, `content`, `tool_call_id`, `tool_calls`, `tool_name`, reasoning, Codex replay fields가 저장된다.

## 8. Compression split과 parent_session_id

컨텍스트가 커지면 `agent/conversation_compression.py`의 `compress_context()`가 이전 메시지를 요약하고 세션을 회전한다.

성공 시 흐름:

```text
old_session_id = agent.session_id
SessionDB.end_session(old_session_id, "compression")
agent.session_id = new timestamp_uuid
SessionDB.create_session(..., parent_session_id=old_session_id)
SessionDB.update_system_prompt(new_session_id, new_system_prompt)
agent._last_flushed_db_idx = 0
```

Gateway는 agent 실행 후 `agent.session_id != session_id`이면 compression split으로 판단하고, `SessionStore`의 현재 `session_key -> session_id` 매핑을 새 `session_id`로 업데이트한다. 그래서 다음 메시지는 압축된 새 transcript를 이어서 불러온다.

## 9. 질문에 대한 직접 답

Q. 여러 수단으로 메시지를 수집하면 하나의 Gateway에서 처리한 뒤 어떻게 되는가?

A. 플랫폼별 adapter가 메시지를 `MessageEvent`/`SessionSource`로 정규화한다. `BasePlatformAdapter`가 active/pending/interrupt를 관리하고, `GatewayRunner._handle_message_with_agent()`가 session_key/session_id를 정한 뒤 transcript를 불러와 `AIAgent.run_conversation()`으로 넘긴다. 결과는 `adapter.send()`로 원래 플랫폼의 chat/thread metadata를 사용해 돌아간다.

Q. Codex에 로그인한 경우 우리 메시지는 Codex에게 어떻게 전달되는가?

A. 기본값은 `codex -p "메시지"`가 아니다. Hermes가 `~/.hermes/auth.json`의 Codex OAuth access token을 사용해 `chatgpt.com/backend-api/codex`에 Responses API 요청을 직접 보낸다. `codex` CLI subprocess는 `codex_app_server` 런타임을 명시적으로 켠 경우에만 `codex app-server` 형태로 실행된다.

Q. 세션 관리는 자동으로 어떻게 되는가?

A. Gateway는 `session_key`로 대화 lane을 정하고 `SessionStore`가 이를 `session_id`에 매핑한다. 매 turn마다 transcript를 로드해 `conversation_history`로 넘기고, `AIAgent`는 새 메시지만 SQLite/JSONL에 저장한다. reset policy, resume_pending, suspended, compression split, parent_session_id chain으로 자동 재개/초기화/압축 continuation을 처리한다.

## 처음 더 읽을 파일

1. `gateway/run.py`: `_handle_message_with_agent`, `_run_agent`
2. `gateway/session.py`: `build_session_key`, `SessionStore.get_or_create_session`, `load_transcript`
3. `hermes_cli/auth.py`: `_login_openai_codex`, `_codex_device_code_login`, `resolve_codex_runtime_credentials`
4. `agent/agent_init.py`: `api_mode` 결정, session_id 생성
5. `agent/conversation_loop.py`: `run_conversation`, `codex_app_server` 분기
6. `agent/codex_runtime.py`: `run_codex_stream`, `run_codex_app_server_turn`
7. `agent/transports/codex_app_server*.py`: `codex app-server` subprocess와 JSON-RPC
8. `run_agent.py`: `_persist_session`, `_flush_messages_to_session_db`
9. `hermes_state.py`: SQLite schema, `append_message`, `replace_messages`, `get_messages_as_conversation`

## 남은 확인 후보

- 실제 사용자의 config에서 `model.openai_runtime`이 `auto`인지 `codex_app_server`인지 확인하면, 현재 설치가 어느 경로를 타는지 확정할 수 있다.
- Gateway platform별 reply metadata, draft streaming, progress message 정책은 플랫폼 adapter마다 차이가 있어 특정 플랫폼 기준으로 추가 확인이 필요하다.
