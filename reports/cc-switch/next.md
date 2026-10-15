# Next Session Plan: CC Switch

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `d35726e28695844deaf0098450b34911f5be7b78`
- **작성/갱신 일자**: `2026-10-15`

## 1. 이번 세션에서 확인한 범위

- [x] 프록시의 가로채기 방식 (설정 base URL 변경), Claude/Gemini/Codex 설정 투영
- [x] 프록시 서버 기술 스택, 라우트 목록 일부
- [x] Session Manager의 Claude 로그 읽기
- [x] Anthropic↔Gemini 변환 함수 위치, 변환 코드 규모, git 이력 수치
- [x] 이 PC의 settings.json/백업 폴더 상태

## 2. 해결되지 않은 남은 질문

- [ ] 라우팅 on/off, 앱 종료, 비정상 종료 시 설정 복구 (`enter`/`exit`/`startup`)
- [ ] `live/patch`의 병합 방식: 사용자가 직접 편집한 settings.json을 덮어쓰는가
- [ ] `handle_messages` → `forwarder` → 변환 → 응답 처리 전체 흐름
- [ ] failover/circuit breaker 판단 기준
- [ ] `usage/logger.rs`의 저장 항목(본문 포함 여부)
- [ ] provider 활성화를 실제로 해 보고 settings.json과 `live-first-write/` 변화 확인
- [ ] Symlink 모드(Windows 개발자 모드/macOS)에서 q5의 같은 이름 스킬 시나리오 재현
- [ ] q6: 같은 id MCP가 앱 파일에 다른 내용으로 있을 때 import→resync를 격리 홈에서 실행 확인

## 3. 다음에 볼 파일 및 함수

| 대상 | 함수 / 모듈 | 확인 목적 |
|---|---|---|
| `src-tauri/src/mode/controller.rs` | `startup`(L1467), `enter`(L577), `exit`(L721) | 설정 쓰기/복구 시점 |
| `src-tauri/src/live/engine.rs` | `plan`, `stage`, `ensure_first_write_backup` | 원자적 쓰기와 백업 |
| `src-tauri/src/proxy/handlers.rs` | `handle_messages` | 요청 처리 진입점 |
| `src-tauri/src/proxy/forwarder.rs` | 전송/재시도 | 업스트림 호출 |
| `src-tauri/src/proxy/usage/logger.rs` | - | 기록 항목 |

## 4. 참고 사항

- archify로 구조도(프록시 경로 + Session Manager 경로)와 요청 1건 시퀀스를 `diagrams/`에 만들 예정.
- `artifacts/cc-switch/repo-metadata.txt`의 첫 기록은 shallow clone `bfaaba1`이고, 이번 분석은 `d35726e`다.
