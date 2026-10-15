# [Q] Session Manager는 프록시인가, 프록시는 무슨 기능을 하는가

- **상위 개요**: [overview.md](../overview.md)
- **분석 Commit SHA**: `d35726e`
- **검증 수준**: `코드 확인` (Session Manager), `추론/모듈명 기반` (프록시 기능 표)

## 1. 질문 및 결론

- **질문**: Session Manager에서 메시지 기록이 보이는데 이것도 프록시인가? 프록시는 무엇을 하는가?
- **핵심 결론**: Session Manager는 프록시와 무관하게 **로컬 JSONL 파일을 읽는다**. 프록시의 주된 가치는 대화 기록이 아니라 **다른 provider/API 형식 사용, failover, 모델 매핑**이다.

## 2. Session Manager

- `session_manager/providers/claude.rs`는 `get_claude_config_dir().join("projects")`(L39) 아래 `*.jsonl`을 재귀 수집(`collect_jsonl_files`, L234-248)해 파싱한다. 이 파일은 Claude Code가 직접 저장한다.
- 복구 명령은 `claude --resume {session_id}` (L217).
- Codex, Gemini, OpenCode, Pi, Hermes 등도 각자 파서(`providers/*.rs`)를 쓴다.
- 프록시 on/off와 무관하게 동작한다.

## 3. 프록시가 하는 일 (모듈 구성 기준)

| 기능 | 관련 모듈 |
|---|---|
| 프로토콜 변환 (Anthropic ↔ OpenAI/Gemini) | `proxy/providers/transform*.rs`, `streaming*.rs` |
| 장애 전환 | `circuit_breaker.rs`, `failover_switch.rs`, `provider_router.rs` |
| 모델명 매핑 | `model_mapper.rs` |
| 요청 보정 | `thinking_*_rectifier.rs`, `cache_injector.rs`, `media_sanitizer.rs` |
| 사용량 기록 | `proxy/usage/` (parser, calculator, logger) |

- 사용량 통계는 프록시 없이도 가능: 기본은 각 도구의 로컬 세션 로그 스캔 (`services/session_usage*.rs`, README L363).
- 요청 본문을 프록시가 별도 저장하는지는 `usage/logger.rs`를 읽지 않아 미확인.

## 5. 남은 질문

- [ ] `usage/logger.rs`가 저장하는 항목 (본문 포함 여부)
- [ ] failover 판단 기준과 circuit breaker 임계값
