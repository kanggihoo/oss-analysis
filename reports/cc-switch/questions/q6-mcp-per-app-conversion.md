# [Q] MCP는 앱(Claude/Codex/OpenCode 등)마다 형식이 다른데 어떻게 관리·변환하는가 (plugin 포함)

- **상위 개요**: [overview.md](../overview.md)
- **분석 Commit SHA**: `d35726e`
- **검증 수준**: `코드 확인` (읽기만, 실행 안 함). Gemini/Grok/Hermes/Pi/Mcode의 세부 형식은 `미확인`

## 1. 질문 및 결론

- **질문**: MCP 서버 정의가 앱마다 다른 포맷인데 CC Switch는 어떻게 한 곳에서 관리하는가? plugin도 같은가?
- **핵심 결론**
  - MCP는 **공통 형식으로 DB에 저장하고, 앱 설정 파일에 쓸 때 앱별로 변환**한다 (스킬과 달리 변환 코드가 있다).
  - 활성/비활성은 파일 복사가 아니라 **앱 설정 파일의 서버 항목을 id 단위로 추가/제거**하는 것이다. DB에 없는 항목(사용자가 직접 넣은 서버)은 건드리지 않는다.
  - **plugin은 관리하지 않는다.** provider 전환 시 보존만 한다.
  - 가져오기에서 같은 id가 이미 DB에 있으면 DB 정의가 이기고, 앱 쪽 다른 정의는 가져오지 않는다 (코드 읽기 기준, 미실행).

## 2. 동작 설명

### 저장과 검증
- DB(`cc-switch.db`)에 `McpServer { id, name, server(공통 스펙), apps(앱별 on/off) }` 형태로 저장.
- 공통 스펙: `type`(stdio/http/sse, 생략 시 stdio), `command`/`args`/`env`/`cwd`(stdio), `url`/`headers`(http/sse). stdio에 `command` 없거나 http/sse에 `url` 없으면 거부 (`mcp/validation.rs`).

### 앱별 쓰기·변환

| 앱 | 대상 | 변환/특징 |
|---|---|---|
| Claude | `~/.claude.json`의 `mcpServers` (JSON) | 읽어서 해당 id만 넣거나 빼고 되씀 (`mcp/claude.rs`) |
| Codex | `~/.codex/config.toml`의 `[mcp_servers]` (TOML) | JSON↔TOML 변환. Codex는 `type`이 없어 `command`면 stdio, `url`이면 http로 추론 (`codex_entry_transport_type`). `toml_edit`로 다른 키/주석 보존, 문법이 깨진 파일은 덮어쓰지 않고 에러, 잘못된 `[mcp.servers]` 형식은 정리. `~/.codex`가 없으면 아무것도 쓰지 않음 |
| OpenCode | OpenCode JSON | `stdio`→`local`, `command`+`args`→`command: [cmd, ...args]`, `env`→`environment`, `http/sse`→`remote` (`convert_to_opencode_format`, 역변환 `convert_from_opencode_format`) |
| Gemini, Grok Build, Hermes | 각자 파일 | 앱별 모듈 (`mcp/{gemini,grokbuild,hermes}.rs`, 형식 미확인) |
| Pi, Mcode | 각자 파일 | 파일과 DB를 함께 커밋하고 실패 시 원복 (`sync_and_commit`). 비활성 플래그가 사용자 기존 서버까지 덮지 않도록 명시적 disable/delete 때만 제거 |
| Claude Desktop, OpenClaw | - | MCP 동기화 안 함 (`live_sync_apps`에서 제외) |

### 동작별 흐름 (`services/mcp.rs`)
- **토글/편집**: DB 갱신 → 켜면 해당 앱에 `sync_single_server_to_*`, 끄면 `remove_server_from_*`. 편집에서 앱 체크를 해제하면 그 앱에서 제거(`upsert_server`).
- **삭제**: DB 행 삭제 후 켜져 있던 모든 앱에서 제거(`delete_server`).
- **재동기화/provider 전환**: `project_servers_to_app`이 DB의 서버를 하나씩 돌며 켜진 앱이면 쓰고, 꺼졌으면 id로 제거. 한 서버 실패가 나머지를 막지 않고, 실패는 모아서 보고. DB에 없는 서버는 그대로 둠.
- **가져오기**(`import_from_*`): 앱 파일의 서버를 DB로 읽어옴. 이미 같은 id가 있으면 **그 앱만 켜고 다른 필드는 덮어쓰지 않는다**. 가져오기는 앱 파일을 되쓰지 않는다. (스킬과 같은 "한 정의만 남는다" 성격이지만, 스킬은 앱 순서상 첫 발견이 이기고 MCP는 DB에 있는 쪽이 이긴다.)

## 3. plugin / hooks / permissions
- `claude_plugin.rs`는 이름과 달리 plugin 관리가 아니라 `~/.claude/config.json`에 `primaryApiKey="any"`를 넣고 빼는 기능이다.
- `live/floor.rs`에 `enabledPlugins`, `hooks`, `permissions`, `statusLine`, `env` 키가 나온다. 문맥상 provider 전환 때 보존하는 키 목록으로 보이나 용도는 추가 확인 필요.
- README는 provider를 바꿔도 plugins/hooks/permissions/MCP/직접 넣은 env는 그대로 두고 연결 필드(endpoint, key, model 등)만 교체한다고 명시 (README L405).
- 즉 앱별로 다른 plugin 체계를 변환하지 않고 **손대지 않는 방식으로 회피**한다.

## 4. 코드 근거

| 구분 | 파일 | 식별자 |
|---|---|---|
| 검증 | `src-tauri/src/mcp/validation.rs` | `validate_server_spec` |
| Codex TOML | `src-tauri/src/mcp/codex.rs` | `sync_enabled_to_codex`, `upsert_mcp_server_table`, `remove_mcp_server_from_doc`, `codex_entry_transport_type` |
| OpenCode 변환 | `src-tauri/src/mcp/opencode.rs` | `convert_to_opencode_format`, `convert_from_opencode_format` |
| 서비스 | `src-tauri/src/services/mcp.rs` | `upsert_server`, `delete_server`, `toggle_app`, `project_servers_to_app`, `import_from_claude` |
| plugin 관련 | `src-tauri/src/claude_plugin.rs`, `live/floor.rs` | `write_claude_config`, 보존 키 목록 |

## 5. 검증 수준과 한계
- 위 내용은 모두 코드 읽기 결과이고 스킬(q5)처럼 격리 홈에서 실행해 보지 않았다.
- `mcp/claude.rs`, `mcp/codex.rs`에는 파일 전체를 되쓰는 `sync_enabled_to_*` 함수도 있다. `lib.rs`에서 재노출되고 주석상 구 버전 호환 경로로 보이나, 현재 어디서 호출되는지는 확인하지 못했다. 주 경로(`project_servers_to_app`)는 항목 단위다.

## 6. 남은 질문
- [ ] 같은 id가 앱 파일에 다른 내용으로 있을 때 import → resync 결과를 q5처럼 격리 홈에서 실행 확인
- [ ] 변환에서 손실되는 앱 고유 필드의 왕복 보존 범위 (`codex.rs` L169 이후 확장 필드 처리)
- [ ] Gemini/Grok/Hermes/Pi/Mcode의 실제 파일 포맷과 변환 규칙
- [ ] `live/floor.rs`의 보존 키 목록이 쓰이는 시점
