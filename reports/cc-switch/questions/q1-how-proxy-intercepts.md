# [Q] 프록시는 요청을 어떻게 "가로채는가"

- **상위 개요**: [overview.md](../overview.md)
- **분석 Commit SHA**: `d35726e`
- **검증 수준**: `코드 확인` (설정 쓰기와 라우트 정의까지. 요청 처리 본문은 미확인)

## 1. 질문 및 결론

- **질문**: CC Switch 프록시는 CLI의 API 요청을 어떻게 가로채는가?
- **핵심 결론**: 네트워크 스니핑/MITM/시스템 프록시가 아니다. 각 CLI가 지원하는 **base URL 환경변수/설정**을 `http://127.0.0.1:15721`로 바꿔 두고, 앱 프로세스 안의 Rust HTTP 서버가 그 포트에서 대기한다.

## 2. 동작 설명

```
CLI ──(base URL = 127.0.0.1:15721, 키 = PROXY_MANAGED)──▶ CC Switch 로컬 서버 ──(진짜 URL+키)──▶ provider
```

| CLI | 쓰는 설정 | 근거 |
|---|---|---|
| Claude Code | `settings.json`의 `env.ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN=PROXY_MANAGED`, 모델은 고정 별칭(`claude-sonnet-5` 등) | `live/project/claude.rs` `proxy_projection()` |
| Gemini CLI | `.env`의 `GOOGLE_GEMINI_BASE_URL`, `GEMINI_API_KEY=PROXY_MANAGED` | `live/project/gemini.rs` (테스트 L220-240) |
| Codex | `config.toml`의 `model_providers.<name>.base_url`, `experimental_bearer_token=PROXY_MANAGED` | `mode/controller.rs` 테스트 픽스처 |

- 진짜 URL/키/모델은 앱의 SQLite(`~/.cc-switch/cc-switch.db`)에만 있다.
- 서버는 앱 프로세스 안에서 돈다 (`proxy/server.rs`, axum 0.7 + hyper 1.0 + tokio, `Cargo.toml`).
- `PROXY_MANAGED`가 업스트림으로 새지 않도록 하는 가드: `forwarder.rs:3724`.
- 우회 방지: `proxy_projection` 주석에 "프록시 우회를 막기 위해 다른 핵심 필드(Bedrock 등 클라우드 자격증명)를 비운다"고 있다. CLI가 설정을 읽는 방식에 의존하는 구조이고, base URL을 못 바꾸는 도구는 붙일 수 없다.
- 프록시가 항상 끼는 건 아니다. 프록시를 켜기 전 direct 모드에서는 provider의 URL/키를 settings에 직접 써서 CLI가 provider에 바로 접속한다.

## 3. 코드 근거

| 구분 | 파일 | 식별자 | 설명 |
|---|---|---|---|
| Claude 설정 투영 | `src-tauri/src/live/project/claude.rs` | `proxy_projection`, `PROXY_TOKEN_PLACEHOLDER`, `PROXY_*_ALIAS` | base URL/placeholder/별칭 |
| 서버 라우트 | `src-tauri/src/proxy/server.rs:299-` | `build_router` | `/v1/messages`, `/chat/completions`, `/models` 등 |
| 키 교체 가드 | `src-tauri/src/proxy/forwarder.rs:44, 3724` | `PROXY_AUTH_PLACEHOLDER` | placeholder 업스트림 유출 차단 |

## 5. 남은 질문

- [ ] 켜고 끌 때 원본 설정을 어떻게 복구하는가 (`live/engine.rs`, `mode/controller.rs` `enter`/`exit`)
- [ ] 앱 강제 종료 시 CLI 설정이 죽은 127.0.0.1을 가리키는가 (README는 "종료 시 direct provider로 되돌려 쓰고 재시작 시 재연결"이라 하나 코드 미확인)
