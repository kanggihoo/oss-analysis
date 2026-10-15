# [Q] 설치하면 ~/.claude/settings.json이 바뀌는가

- **상위 개요**: [overview.md](../overview.md)
- **분석 Commit SHA**: `d35726e`
- **검증 수준**: `실행 확인` (이 PC의 실제 파일 상태) + `코드 확인` (백업 함수 존재) + `추론` (startup 동작)

## 1. 질문 및 결론

- **질문**: CC Switch를 설치하면 `~/.claude/settings.json`의 env가 바로 수정되는가?
- **핵심 결론**: 아니다. 설치/실행만으로는 안 바뀐다. 사용자가 **provider를 활성화**하거나 **로컬 라우팅을 켰을 때** 쓴다.

## 2. 동작 설명

| 단계 | 동작 | 근거 |
|---|---|---|
| 첫 실행 | 기존 Claude/Codex/Gemini 설정을 읽어 `default` provider로 가져오고 공식 provider 카드를 추가 | README L306 |
| 첫 쓰기 직전 | 원본 설정을 `~/.cc-switch/backups/live-first-write/`에 백업 | README L409, `live/engine.rs` `ensure_first_write_backup` |
| provider 활성화 | 해당 provider의 URL/키/모델을 `env`에 직접 기록 (프록시 없음) | README, `mode/controller.rs` |
| 로컬 라우팅 on | `ANTHROPIC_BASE_URL=127.0.0.1:15721`, `PROXY_MANAGED`로 교체 | Q1 |
| 라우팅 off / 앱 종료 | direct provider 설정으로 되돌려 씀 (종료 후 재시작하면 재연결) | README L447 (코드 미확인) |

## 4. 검증 결과 (이 PC, 2026-10-15)

- `C:/Users/SSAFY/.claude/settings.json`에는 `env` 블록이 없다 (hooks/model/theme만). `ANTHROPIC_BASE_URL`, `PROXY_MANAGED` 없음.
- `~/.cc-switch/backups/`에는 `db_backup_*.db`만 있고 `live-first-write/`가 없다. 즉 CC Switch가 이 파일을 다시 쓴 적이 없다.
- `cc-switch.exe`는 실행 중이고 `cc-switch.db`는 갱신되고 있었다.

## 5. 남은 질문

- [ ] `startup()`(`mode/controller.rs:1467`)이 시작 시 설정 파일에 무엇을 쓰는지
- [ ] provider 활성화를 실제로 했을 때 `live-first-write/` 백업이 생기는지 (직접 실행 확인, 현재 사용 중인 구독 로그인에 영향이 있으니 주의)
