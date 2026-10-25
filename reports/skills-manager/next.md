---
sha: "7a2219219287f4ef4c543fc169ebcc5b0bff085c"
created: 2026-10-15
updated: 2026-10-24
---

# Next Session Plan: skills-manager

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] `repos/skills-manager`를 `7a22192`로 pull, 기능 지도 재작성(overview 1·2절)
- [x] 사용자 범위 승인: 외부 스킬 설치, 출처 메타데이터, 변경 확인, 원본 diff (이유: `my-skills`가 남의 스킬을 래핑하므로 "원본이 바뀌었는지, 무엇이 바뀌었는지"가 필요)
- [x] 스펙 5개 작성·통합 검토(overview 2절 "스펙 통합 검토"): [skill-source-metadata](capabilities/skill-source-metadata.md), [skill-install-external](capabilities/skill-install-external.md), [skill-update-check](capabilities/skill-update-check.md), [skill-source-diff](capabilities/skill-source-diff.md), [skill-update-apply](capabilities/skill-update-apply.md) — 모두 ready (갱신 적용은 같은 날 추가 승인)
- [x] 순수 git CLI 실행 확인 2건과 판단 규칙 파이썬 번역 실행 1건(`artifacts/skills-manager/skill-update-check-demos/`, `skill-source-diff-demos/`, `skill-update-apply-demos/`). 앱·cargo·네트워크 실행은 하지 않음
- [ ] 재구현 검증(워크플로 4장 6번)은 요청이 없어 하지 않음. 구조도(archify)는 사용자 지시로 생략

---

## 2. 해결되지 않은 남은 질문

- [ ] **Q1·Q2 재확인**: 둘 다 `e6dcedf` 기준이다. 이번 구간에서 `scenario_service.rs`, `installer.rs`, `agent_workspace.rs`, `git_backup.rs`(Q2는 `skills.rs`, `sync.rs`, `git_fetcher.rs`, `tool_adapters.rs`, `skill_store.rs`, `browse.rs`도)가 바뀌었다.
- [ ] **다른 기기에서 Git 스킬 확인이 `unknown`에 머무는가**: 코드 읽기로는 그렇다(출처 메타데이터 R-12, R-13). 두 기기(또는 격리 홈 2개)에서 실제로 확인해야 한다. 앱 실행이 필요하므로 사용자 동의가 먼저다.
- [ ] **갱신 적용 UI 결함 후보(추론)**: 승인 호출이 다시 보류(Held)를 돌려주면 `ConfirmDialog.handleConfirm`이 이어서 `onClose()`를 불러 새 대화상자가 바로 지워질 수 있다(갱신 적용 R-41). 앱 실행으로 확인 필요
- [ ] `resync_copy_targets`가 부르는 `sync_engine`(copy 모드 사본 재동기화)은 읽지 않았다. 에이전트 배포 스펙을 쓸 때 경계를 맞출 것
- [ ] Preset(scenario)의 "한 번 복사" 의미, 에이전트 폴더 이동 시 보존 복사본(`move_into_kept_copies`) 조건, `file_watcher` 재스캔, `core/merge/` 병합

---

## 3. 기능 스펙 후보

범위 밖이라 승인 전이다. 사용자가 고르면 지도의 행 단위로 쓴다.

| 기능 | 근거 | 상태 |
|---|---|---|
| 라이브러리 사본의 로컬 수정 감지·보존 | 갱신 적용 스펙 "적용 메모"(원본에 없는 기능. 저장 해시가 reindex로 덮이므로 기준선 열이 필요) | 새 기능 후보. `my-skills`가 래핑한 스킬을 고쳐 쓴다면 필요 |
| Git 체크아웃 획득(신규 공유 계약 후보) | 설치 R-04·R-05, 원본 diff R-08·R-09, 갱신 적용(`clone_repo_ref_scoped`, `checkout_revision`, `resolve_skill_dir`)이 `git_fetcher`를 각자 설명(소비자 3곳) | 승인 대기. 한 문서가 소유하고 세 스펙이 링크하는 편이 중복이 없다 |
| 주기적 자동 확인·트레이 확인 | 변경 확인 R-24, R-25와 갱신 적용 R-42가 호출 입구만 기술 | 승인 대기 |
| 로컬 설치·폴더 일괄 가져오기·압축 | 설치 스펙 경계 | 승인 대기 |
| 에이전트 배포·덮어쓰기 보호 | [q1](./questions/q1-same-name-conflict-and-overwrite.md) (새 SHA 재확인 필요) | 승인 대기 |

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

다음에 쓸 기능 스펙이 있으면: 사용자가 범위를 승인한 뒤 `Git 체크아웃 획득`(소비자 3곳) 또는 `에이전트 배포·덮어쓰기 보호`(갱신 적용이 copy 사본 재동기화로 의존).

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `src-tauri/src/core/sync_engine.rs`, `commands/skills.rs`의 `resync_copy_targets`(3224~) | `is_target_current`, `recorded_target_is_current` | 에이전트 배포 스펙, 갱신 적용의 copy 사본 경계 |
| `src-tauri/src/core/git_fetcher.rs` | `clone_repo_ref_scoped`(캐시·sparse·LRU), `find_skill_dir` | Git 체크아웃 획득 |
| `src-tauri/src/core/skill_auto_updater.rs` | `start` | 자동 확인 스펙 |

---

## 5. 참고 사항 및 후속 제안

- 스펙 작성에서 새로 확인한 점(상세와 근거는 각 스펙 2.1): `well-known` 출처는 변경 확인 대상이 아니다. skills.sh로 설치한 것은 사이트 URL이면 `well-known`, 저장소 기반이면 `skillssh`(git처럼 확인)다. diff는 git·skillssh·local·import만 되고 CLI에는 diff 명령이 없다. `install_git`(앱)과 CLI `--git`은 스킬 목록을 열거하지 않고 폴더 하나를 한 스킬로 설치한다(경로를 읽어 도출, 실행 안 함).
- 출처 메타데이터 스펙 "적용 메모": 새 기기에서도 `source_revision`을 갖게 하는 방안은 사용자 결정이 필요해 비워 두었다.
- 실험할 때는 CLI `--skills-root` 옵션이나 테스트 HOME 오버라이드로 실제 `~/.skills-manager`를 건드리지 않는다.
- 이번 세션은 macOS(darwin)에서 진행했다. 이전 메모의 "이 PC는 Windows"는 2026-10-15 세션 기준이다.
