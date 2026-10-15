# Next Session Plan: skills-manager

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `e6dcedf968f3f0ebf62e24edf5d90ec8cbf23509`
- **작성/갱신 일자**: `2026-10-15`

## 1. 이번 세션에서 확인한 범위

- [x] README, 디렉터리 구조, 의존성, 에이전트 어댑터 개수
- [x] `sync_skill_to_tool` 한 경로: commands → scenario_service → sync_engine → skill_targets
- [x] SQLite 테이블 목록(`core/migrations.rs` v0→v1), `ReplacePolicy` 결정표
- [ ] 코드 실행·테스트는 하지 않음 (`cargo test` 미실행)

## 2. 남은 질문 (제안 후속 질문)

- [x] Q1(코드 읽기 완료, [q1](./questions/q1-same-name-conflict-and-overwrite.md)). 남은 것: cc-switch q5와 같은 시나리오를 격리 홈에서 실행해 확인, 배포된 복사본을 사용자가 수정한 뒤 원본이 바뀔 때 덮어쓰기 여부
- [ ] Q2. Preset(scenario)은 DB 상 무엇이며 "한 번 복사, 실시간 동기화 아님"이 코드와 일치하나? (`scenario_service`, `scenario_skill_tools`)
- [ ] Q3. 에이전트가 앱 없이 CLI로 관리하는 구조: `cli_bridge`가 CLI를 어디에 두고 `manage-skills` 스킬이 이를 어떻게 찾나?
- [ ] Q4. 외부 폴더 변경(file_watcher)은 DB와 어떻게 다시 맞추나? 앱이 몰랐던 스킬은 어떻게 표시되나?
- [ ] Q5. git 백업의 skill 단위 병합(`core/merge/`)과 충돌 처리(keep mine/remote/both)
- [ ] 마켓플레이스(skills.sh)·git 설치와 업데이트 감지(`git_fetcher.rs`, `skill_auto_updater.rs`)

## 3. 다음에 볼 파일 및 함수

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `src-tauri/src/commands/scan.rs`, `core/scanner.rs` | 스캔·adopt | Q1, Q4 |
| `src-tauri/src/core/scenario_service.rs` | `sync_desired_targets`, `apply_scenario_to_default` | Q2 |
| `src-tauri/src/core/cli_bridge.rs` | `ensure_bridge` | Q3 |
| `src-tauri/src/core/file_watcher.rs` | `start_file_watcher`, `mute_self_writes` | Q4 |
| `src-tauri/src/core/merge/` | | Q5 |

## 4. 참고 사항

- 이 PC는 Windows. symlink는 권한 문제로 junction → copy로 폴백한다(`sync_engine.rs`). 실험 시 실제 mode를 확인할 것.
- 실험할 때는 README의 CLI `--skills-root` 옵션이나 테스트 HOME 오버라이드로 실제 `~/.skills-manager`를 건드리지 않는다.
