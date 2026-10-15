# [Q] 같은 이름·다른 내용 스킬과 덮어쓰기 문제를 skills-manager는 어떻게 처리하는가 (cc-switch 비교)

- **상위 개요**: [overview.md](../overview.md)
- **분석 Commit SHA**: `e6dcedf968f3f0ebf62e24edf5d90ec8cbf23509` (2026-10-15)
- **검증 수준**: `코드 확인` (읽기만, 실행 안 함). 실행 검증은 하지 않았다.
- **비교 대상**: [cc-switch q5](../../cc-switch/questions/q5-skills-mcp-management.md) (SHA `d35726e`, 같은 시나리오를 실행해 확인)

## 1. 질문 및 결론

- **질문**: 앱(Claude/Codex 등)마다 같은 이름이지만 내용이 다른 스킬(예: Codex에만 `agents/openai.yaml`)이 있을 때, 중앙 관리 도구가 어떻게 처리하는가?
- **핵심 결론**: skills-manager는 cc-switch의 문제를 대부분 설계로 막는다.
  1. 같은 이름도 **내용 해시가 다르면 별개 스킬**로 다룬다(병합/덮어쓰기 없음).
  2. 앱 폴더를 덮어쓰기 전에 **"우리가 배포한 것인지"를 기록으로 증명**해야 하고, 증명 못 하면 거부한다.
  3. 거부는 에러로 삼키지 않고 **충돌 목록으로 사용자에게 보고**한다.
  다만 이미 배포된 복사본을 사용자가 수정했고 원본이 바뀌면 그 수정은 덮어쓰일 수 있다(5절).

## 2. 동작 설명

### 구조 (cc-switch와 같은 뼈대)
중앙 라이브러리 `~/.skills-manager`(설정 가능) + SQLite + 앱별 skills 폴더에 symlink/복사 배포. 배포마다 `skill_targets` 행(어느 스킬을 어느 앱의 어느 경로에 어떤 모드로 배포했는지, 배포 시점 `source_hash`)을 기록한다.

### 같은 이름·다른 내용
| 단계 | skills-manager | cc-switch |
|---|---|---|
| 발견(scan) | 이름+**내용 해시**로 그룹화(`group_discovered`: 키 `fp:{name}:{fingerprint}`). 같은 이름이라도 내용이 다르면 **다른 그룹** | 폴더명만으로 한 항목, `found_in`만 모음 |
| 해시 범위 | 스킬 폴더의 모든 파일(`.git`, `.DS_Store`, `*.pyc` 등 제외). `agents/openai.yaml` 차이도 해시가 달라진다 | 해시로 비교하지 않음 |
| 가져오기(import) | 중앙에 같은 이름이 있고 내용이 다르면 `<name>-2`, `<name>-3`…로 **새 폴더 할당**(`unique_skill_dest`), 내용이 같으면 재사용 | 앱 순서상 먼저 발견된 쪽(Claude)이 원본, 나머지는 버려짐 |
| 이미 등록됐는지 판단 | `source_ref` 경로 일치 또는 내용 해시 일치(`match_imported_skill_id`). 이름만 같다고 "가져옴"으로 보지 않음(테스트 `does_not_mark_same_name_as_imported_without_path_or_hash_match`) | 폴더명 |

주의: `unique_skill_dest` 문서 주석은 "같은 metadata name이면 재사용"이라고 쓰여 있으나 코드는 **내용 해시가 같을 때만** 재사용한다. 코드가 기준이다.

### 덮어쓰기 안전장치 (`core/sync_engine.rs`)
- 배포 대상을 `symlink_metadata`로 분류한다(`TargetState`: 없음 / 우리 링크 / 남의 링크 / 실제 폴더 / 실제 파일). `is_dir()`처럼 링크를 따라가지 않아 Windows junction을 실제 폴더로 착각해 지우지 않는다.
- 삭제 권한을 `ReplacePolicy`로 호출부가 명시한다.
  - `NoClobber`: 우리 것임을 증명 못 하면 모두 거부
  - `Recorded{mode}`: `skill_targets` 행이 정확히 그 경로를 가리키고, **현재 파일 종류가 기록된 모드와 일치**할 때만 허용(예: symlink로 기록했는데 실제 폴더가 와 있으면 거부)
  - `UserConfirmed`: 사용자가 가져오기/`--force`/"원본에서 갱신"을 명시한 경우만
- 삭제 직전에 다시 확인하고(체크~삭제 사이 경쟁 방지), 분류된 종류에 맞는 삭제 함수만 쓴다(`remove_classified_target`). 원본이 대상 안에 있거나 그 반대인 겹침도 거부한다(`ensure_dst_not_inside_src`).
- 거부는 `ReplaceRefused` → `TargetConflict{target, reason}`로 **구조화되어 호출자에 반환**된다(`sync_desired_targets`). 앱 시작 시에는 충돌이 있어도 기동을 막지 않고, CLI는 에러로 보여 준다. 코드 주석에 이 설계가 이슈 #363(조용한 데이터 손실)의 수정이라고 명시.
- 가져오기(`DeployIntent::AdoptExisting`)는 별도 경로로, 사용자가 선택한 스캔 경로만 `UserConfirmed`로 교체한다. 일반 배포(`Managed`)와 코드 경로를 공유하지 않는다.

### drift(원본과 달라진 사본) 감지
- 복사 모드의 "이미 최신" 판단은 **배포 시점 원본 해시 == 현재 원본 해시**이고 대상이 존재할 때(`is_target_current`). 대상 내용 자체를 비교하는 것은 아니다.
- 프로젝트/에이전트 워크스페이스는 중앙과 로컬을 해시와 수정 시각으로 비교해 `in_sync / project_only / project_newer / center_newer / diverged`로 분류한다(`classify_sync_status`). 로컬이 더 새로우면 "원본에서 갱신"을 거부한다(`update_agent_local_skill_from_center`).
- 시작 시 복구(`backfill_stranded_agent_targets`)는 내용이 원본과 같은 것만 자동 처리하고, 달라진(diverged) 스킬은 건드리지 않고 사용자 조치로 남긴다.

### Windows symlink 실패
symlink 실패 시 바로 복사하지 않고 **junction(권한 불필요)을 먼저** 시도하고, 그것도 안 되면(예: UNC 경로) 복사로 폴백한다(`sync_skill` Windows 분기). 복사 폴백일 때 "수동 재동기화로 symlink 재시도"한다는 로그도 남긴다.

## 3. cc-switch 문제 대비 판정

| cc-switch에서 확인된 문제 | skills-manager | 근거 |
|---|---|---|
| 1. 같은 이름·다른 내용을 한 스킬로 취급 | **해결**: 해시로 구분, 이름 충돌 시 `-2` 할당 | `scanner.rs group_discovered`, `installer.rs unique_skill_dest` |
| 2. 재동기화 때 조용히 덮어씀(앱 전용 파일 삭제, 경고 없음) | **해결**: 기록 없는 대상은 거부하고 충돌로 보고 | `sync_engine.rs ReplacePolicy`, `scenario_service.rs TargetConflict` |
| 3. 앱 전용 파일(openai.yaml 등)을 만들어 주지 않음 | **동일**: 폴더를 그대로 배포, 앱별 변환/오버레이 없음 | `copy_skill_dir`, `sync_skill` (파일 종류별 처리 없음) |
| 4. 앱별 보호가 일부 앱에만 | **해결**: 모든 앱에 같은 정책 적용 | `ReplacePolicy` 공통 |
| 5. Windows symlink 실패 시 복사, 반영 지연 | **부분 해결**: junction 우선, 복사 폴백은 존재하며 재시도는 수동 | `sync_skill` Windows 분기 |

## 4. 코드 근거

| 구분 | 파일 | 식별자 |
|---|---|---|
| 덮어쓰기 정책/분류 | `src-tauri/src/core/sync_engine.rs` | `TargetState`, `ReplacePolicy`, `authorize_replacement`, `classify_target`, `remove_classified_target`, `sync_skill`, `is_target_current` |
| 충돌 보고 | `src-tauri/src/core/scenario_service.rs` | `replace_policy`, `TargetConflict`, `sync_desired_targets`, `DeployIntent` |
| 그룹화/해시 | `src-tauri/src/core/scanner.rs`, `content_hash.rs` | `group_discovered`, `hash_directory`, `list_content_files` |
| 가져오기/이름 할당 | `src-tauri/src/commands/scan.rs`, `core/installer.rs` | `match_imported_skill_id`, `import_all_discovered`, `unique_skill_dest` |
| drift | `src-tauri/src/commands/projects.rs`, `agent_workspace.rs` | `classify_sync_status`, `update_agent_local_skill_from_center`, `backfill_stranded_agent_targets` |

## 5. 남은 약점과 미확인

- **배포된 복사본의 사용자 수정**: 기록(`Recorded{copy}`)이 있는 실제 폴더는 원본 해시가 바뀌면 교체 대상이다. 대상의 현재 내용이 우리가 배포한 것과 같은지는 비교하지 않는다(`is_target_current`는 원본 해시만 봄). 즉 복사 모드에서 사용자가 에이전트 쪽 복사본을 수정하고 중앙 원본이 갱신되면 수정이 덮어쓰일 수 있다. 코드 읽기 결론이며 실행 확인은 하지 않았다. (워크스페이스 화면의 `project_newer` 보호는 수동 "원본에서 갱신" 경로에 있다.)
- **`-2` 폴더명의 부작용**: 에이전트에 배포되는 폴더 이름은 중앙 폴더명(`target_dir_name`)이라 `dup-skill-2`가 된다. SKILL.md의 `name`은 그대로이므로 에이전트 쪽에서 이름이 겹치는지는 에이전트 규칙에 달려 있고 이 레포로는 알 수 없다. 미확인.
- 앱별로 SKILL.md 내용을 달리하는 기능(오버레이/변환)은 찾지 못했다 (문제 3).
- 백업/멀티 디바이스 병합(`git_backup.rs`, `core/merge/`)은 이번 질문 범위 밖이라 읽지 않았다.
- cc-switch처럼 격리 홈에서 같은 시나리오를 실행하는 검증은 하지 않았다 (`next.md`).
