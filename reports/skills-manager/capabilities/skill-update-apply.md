---
sha: "7a2219219287f4ef4c543fc169ebcc5b0bff085c"
created: 2026-10-24
updated: 2026-10-24
sources:
  - src-tauri/src/commands/skills.rs
  - src-tauri/src/core/removals.rs
  - src-tauri/src/core/skill_store.rs
  - src-tauri/src/core/installer.rs
  - src-tauri/src/core/git_fetcher.rs
  - src-tauri/src/core/content_hash.rs
  - src-tauri/src/core/sync_metadata.rs
  - src-tauri/src/core/app_state.rs
  - src-tauri/src/core/repo_lock.rs
  - src-tauri/src/core/scenario_service.rs
  - src-tauri/src/core/skill_auto_updater.rs
  - src-tauri/src/bin/skills-manager-cli.rs
  - src/lib/tauri.ts
  - src/views/MySkills.tsx
  - src/components/ConfirmDialog.tsx
  - src/context/AppContext.tsx
  - src/i18n/en.json
  - skills/manage-skills/SKILL.md
depends:
  - ../capabilities/skill-source-metadata.md
  - ../capabilities/skill-update-check.md
  - ../capabilities/skill-install-external.md
status: ready
reimplementation: 미실행
---

# 스킬 원본 변경 적용·출처 재연결 (update apply / re-point)

> 라이브러리에 든 스킬 하나(또는 여러 개)와, 필요하면 "사라질 파일 승인 토큰"·새 출처(폴더 경로 또는 Git URL)를 받아, 원본에서 다시 가져온 내용으로 라이브러리 사본을 통째로 교체하고 출처 필드·상태를 기록하며, 교체로 사라질 파일이 있으면 아무것도 바꾸지 않고 목록과 토큰을 돌려주고, 출처만 다시 지정(relink·detach·set-source)하는 기능이다.

<!--
용어 (이 문서 안에서만)
- 저장 해시: `skills.content_hash` 열 값. 내용 해시 범위·무시 목록은 선행 스펙 skill-source-metadata R-10, C-10이 소유한다.
- 원격 폴더 해시: 새로 받은 임시 체크아웃 안의 스킬 폴더를 같은 `hash_directory`로 해시한 값.
- 스테이징 사본(staged): 새 내용을 라이브러리 폴더 옆 `.<이름>.staged-<uuid>`에 복사해 둔 것. 교체(swap) 직전까지 라이브러리는 그대로다.
- Held: 교체로 사라질 파일이 있어서 아무것도 바꾸지 않고 목록과 토큰만 돌려주는 결과.
- 배포 사본(copy 모드): 에이전트 폴더에 복사로 배포된 스킬 폴더(`skill_targets.mode = 'copy'`).
이 문서가 소유하는 것: 교체 절차, 교체 직전 확인(사라질 파일·승인 토큰), 출처 재지정 연산, 실패 때 상태, 입구(앱·CLI)와 승인 토큰이 오가는 방식.
소유하지 않는 것: 변경 판정(skill-update-check), 원본 diff(skill-source-diff), 새 설치(skill-install-external), 필드 의미(skill-source-metadata), 에이전트 배포 엔진 내부, 자동 적용 타이머·옵트인.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표: 앱의 "Update"(= `update_skill(skill_id, approved_removals=None)`) 한 번, git·skillssh 스킬.

1. 스킬 행을 읽고(락 없음) `git_source_from_skill`로 clone URL·브랜치·하위 폴더·locator를 구해 URL을 검증하고, `git ls-remote`로 원격 head(`remote_revision`)를 구한다. 여기까지 실패하면 `error`(head 조회 실패) 또는 상태 불변(그 앞 단계)이다(R-14, R-15).
2. `update_status`를 `updating`으로 쓰고(R-16), 임시 폴더에 범위 지정 clone을 받아 head로 checkout하고 스킬 폴더를 정하고, 그 폴더를 해시해 저장 해시와 비교한다: `content_changed = 저장 해시 ≠ 원격 폴더 해시`(R-01, R-17). 로컬 사본의 디스크 내용은 해시하지 않는다.
3. 저장소 락(`RepoLock`, 최대 20초 대기)을 잡는다(R-18). 내용이 바뀌었으면 새 내용을 스테이징 사본으로 복사한다(R-19).
4. 사라질 파일 목록을 계산한다: 라이브러리(스테이징 사본 기준)와 copy 모드 배포 사본에서 "새 버전에 없는 경로"(R-05~R-08). 목록이 비어 있지 않고 호출자가 가져온 토큰이 `토큰(head, 목록)`과 다르면 Held: 스테이징 사본을 지우고, `update_available`로 기록하고 `{pending_removals, removal_approval}`을 돌려준다. 파일은 하나도 안 바뀐다(R-09~R-11).
5. 아니면 라이브러리 폴더를 스테이징 사본으로 바꿔치기(swap)하고(R-20), 출처 필드·`content_hash`·상태 `up_to_date`를 쓰고(R-21), copy 모드 배포 사본을 다시 맞추고(R-22), 메타데이터 파일을 다시 쓴다. 내용이 안 바뀌었으면 swap 없이 출처 필드와 상태만 쓴다(R-04, R-21).
6. 클로저 안에서 실패하면 `error`와 메시지를 쓰고 오류를 돌려준다(R-23). 성공이면 DB에서 다시 읽은 스킬과 `content_changed`를 돌려준다. 임시 체크아웃은 성공·실패와 무관하게 지운다.

같은 "스테이징 → 사라질 파일 확인 → swap" 뼈대를 쓰는 다른 입구: 일괄 갱신(R-26), 로컬 재가져오기(R-27), relink(R-28). 뼈대를 쓰지 않는 입구: detach(R-29), set-source(R-30~R-34, 사라질 파일 확인 없음).

**내가 고친 사본은 어떻게 되나** (실무 질문 (a)~(e)의 요약. 근거는 R-ID):
- (a) 판정은 "저장 해시 대 원격 폴더 해시"다. 사본 디스크 내용과는 비교하지 않는다(R-01). 저장 해시는 프로세스 시작마다 디스크 해시로 다시 쓰인다(R-02).
- (b) 병합·충돌 감지는 없다. 바뀌면 폴더 전체가 교체된다(R-03).
- (c) 목록은 "새 버전에 없는 경로"만 잡는다. 같은 경로의 파일을 고친 것은 안 잡는다(R-05, R-06).
- (d) local·import 재가져오기는 해시 비교 없이 항상 교체(R-27), set-source는 저장 해시와 비교해 다르면 `--force` 필요, `--force`는 사라질 파일 확인이 없다(R-31, R-33).
- (e) 토큰은 `head 문자열 + (위치,경로) 목록`만 묶는다(R-09). 승인 뒤에도 목록 밖 변경은 막지 못한다(R-13).

### 1.2 범위·통합 지점 [필수]

- 제공: 
  - git·skillssh 스킬 갱신(`update_skill`, 내부 `update_git_skill_internal`), 일괄 갱신(`batch_update_skills`), local·import 재가져오기(`reimport_local_skill`), 출처 재지정(`relink_local_skill_source`, `detach_local_skill_source`, 내부 `set_git_source_internal`과 CLI `skills set-source`), 교체로 사라질 파일 확인과 승인 토큰, 실패·취소·동시 실행 때 상태, CLI `skills update`, My Skills 화면의 호출·승인 대화상자.
- 제외:
  - 변경 판정과 `update_status`의 확인 쪽 값: [skill-update-check](skill-update-check.md). 이 기능은 `update_available`를 만들지 않고(예외: Held 기록, R-11) 읽지도 않는다. 갱신은 `update_status`와 무관하게 호출할 수 있다.
  - 원본 diff 표시: [skill-source-diff](skill-source-diff.md). 거기서 diff가 원본 폴더 대 사본이라는 것과 이 기능의 "교체"가 같은 두 폴더를 쓴다는 점만 공유한다.
  - 새 스킬 설치: [skill-install-external](skill-install-external.md). 임시 체크아웃(`clone_repo_ref_scoped`, 설치 R-04)과 스킬 폴더 결정(`resolve_skill_dir`, 설치 R-05), 복사 규칙(설치 R-13, C-17, C-18)은 거기 정의를 그대로 쓴다. 그래서 `depends`에 넣었다.
  - 주기 스케줄러·앱 시작 자동 적용(`skill_auto_updater.rs`, `AppContext.tsx`의 `auto_update_apply`): 타이머·옵트인·간격은 범위 밖. 이 문서는 "승인 토큰 없이 부르면 사라질 파일이 있을 때 적용하지 않는다"는 경계만 R-42에 둔다.
  - 에이전트 배포 엔진(`sync_engine`, `recorded_target_is_current`의 내부 판정): `resync_copy_targets`의 입력·결과 경계만 R-22에 둔다. 읽지 않았다.
  - Git clone 캐시·sparse 내부: 설치 R-04, R-05.
- 외부 의존·선행 계약:
  - [skill-source-metadata](skill-source-metadata.md): 출처 필드·`update_status` 값·내용 해시 범위·메타데이터 파일 재작성(R-10, R-11, R-18). 이 기능이 쓰는 setter(`update_skill_after_install`, `update_skill_after_reinstall`, `update_skill_source_metadata`, `update_skill_check_state`, `update_skill_update_status`)의 열 단위 효과는 그 문서 C-03, C-04.
  - [skill-update-check](skill-update-check.md): `git_source_from_skill`(C-04, R-04), `resolve_remote_revision`(C-08, R-16), 저장소 락 설명(1.2).
  - 저장소 락 `RepoLock::acquire_foreground(작업명)`: 파일 락을 50ms 간격으로 최대 20초 시도하고 못 잡으면 `skills repository is busy: <작업명>` 오류(`database` kind). 이 기능의 작업명: `update installed skill`, `reimport local skill`, `relink local skill`, `detach local skill`, `set skill source`(C-24).
  - 설정 `proxy_url`(앱: `store.proxy_url()`). 시계는 UTC ms.
  - 배포 기록 `skill_targets`: `get_targets_for_skill(skill_id)`가 `{tool, target_path, mode, status, source_hash}`를 돌려준다는 것만 쓴다(중앙 라이브러리·상태 스펙 미작성).
  - copy 모드 배포 사본 재동기화(`resync_copy_targets`, R-22): 에이전트 배포 스펙(미작성)이 소유할 엔진을 호출하는 경계다.
- 소유 상태·부작용:
  - 라이브러리 스킬 폴더(통째 교체), 같은 폴더 옆의 임시 `.<이름>.staged-<uuid>`·`.<이름>.backup-<uuid>`(성공·실패 뒤 지운다, R-20), OS 임시 체크아웃(git 경로, 항상 지운다).
  - `skills` 행의 `update_status`(+`last_check_error`, `last_checked_at`, `remote_revision`), 출처 필드, `content_hash`, `description`, `updated_at`(스킬 `name`은 안 바뀐다, R-21).
  - copy 모드 배포 사본과 그 `skill_targets` 행(R-22), 메타데이터 파일(R-21).
  - 감사 로그 `update` 행(앱 입구만, R-25). 앱 메모리의 취소 레지스트리 키 `update:<skill_id>`(R-16).

### 1.3 인터페이스와 데이터 의미 [필수]

**앱 명령** (Tauri `invoke`, JS 인자는 camelCase, 오류는 `{kind, message}`(설치 스펙 C-29))

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `update_skill` | `skillId: string`, `approvedRemovals?: string` → `UpdateSkillResult` | git·skillssh 한 스킬 갱신(R-14~R-25). `approvedRemovals`는 직전 Held 결과의 `removal_approval`을 그대로 돌려주는 값 |
| `batch_update_skills` | `skillIds: string[]` → `BatchUpdateSkillsResult` | id마다 순서대로, 승인 없이(R-26) |
| `reimport_local_skill` | `skillId`, `approvedRemovals?` → `ReimportSkillResult` | local·import 재가져오기(R-27) |
| `relink_local_skill_source` | `skillId`, `sourcePath: string`, `approvedRemovals?` → `ReimportSkillResult` | local·import의 `source_ref`를 다른 폴더로(R-28) |
| `detach_local_skill_source` | `skillId` → 스킬 DTO | 출처 경로를 지우고 `local_only`(R-29) |
| `UpdateSkillResult` | `{skill: 스킬 DTO, content_changed: bool, pending_removals: [{location: string, path: string}], removal_approval: string?}` | `pending_removals`가 비어 있지 않으면 **아무것도 바뀌지 않았다**. `removal_approval`은 Held일 때만 값이 있다. `content_changed`는 Held이면 false |
| `ReimportSkillResult` | `{skill, pending_removals, removal_approval}` | 같은 의미. `content_changed` 없음 |
| `PendingRemoval` | `{location, path}` | `location` = 라이브러리면 `"library"`, 배포 사본이면 그 에이전트 키. `path`는 폴더 기준 상대 경로, 폴더째 사라지면 끝에 `/`(R-05) |
| `BatchUpdateSkillsResult` | `{refreshed: int, unchanged: int, failed: string[], held_back: string[]}` | R-26 |
| 스킬 DTO | 갱신 뒤 DB에서 다시 읽은 `ManagedSkillDto`(필드는 C-26, 출처 필드 의미는 선행 스펙, 나머지는 라이브러리 관리 스펙) | |

**CLI** `skills-manager-cli [--json] skills …` (R-37, R-38)

| 명령 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `skills update [REF] [--all]` | → JSON 배열 `UpdateReport{skill_id, name, source_type, refreshed: bool, error?: string, held_back_removals?: string[]}` | REF와 `--all`은 정확히 하나(`pass either a ref or --all, not both`, `pass a skill ref or --all`). 승인 수단 없음. `held_back_removals`는 비어 있으면 필드 자체가 없다. 항목은 `"<location>: <path>"` |
| `skills set-source REF --git-url URL [--subpath P] [--branch B] [--force] [--dry-run]` | → JSON `SetSourceResult{skill_id, name, previous_source_type, previous_source_ref, clone_url, subpath?, branch?, revision, content_changed, dry_run}` | `--git-url`은 필수, `--subpath ""`는 "저장소 루트". R-30~R-34 |

**경로별 한눈 표** (R-ID에서 도출한 요약)

| 입구 | 대상 `source_type` | 새 내용의 출처 | "바뀌었다" 판정 | 같은 경로 파일의 로컬 수정 | 사라질 파일 확인 | 승인 방법 |
|---|---|---|---|---|---|---|
| 앱 `update_skill`, `batch_update_skills`, CLI `update`, 자동 갱신 | `git`, `skillssh` | 원격 head 체크아웃의 스킬 폴더 | 저장 해시 ≠ 원격 폴더 해시(R-01) | 바뀌면 조용히 덮어씀, 안 바뀌면 보존 | 있음(R-05) | 앱 단건만 토큰으로 승인. 일괄·CLI·자동은 보류(held) |
| 앱 `reimport_local_skill`, `batch_update_skills`, CLI `update` | `local`, `import` | `source_ref` 경로(폴더 또는 `.zip`/`.skill`) | 판정 없음, 항상 교체(R-27) | 조용히 덮어씀 | 있음 | 앱 단건만(토큰 도메인 `"reimport"`) |
| 앱 `relink_local_skill_source` | `local`, `import` | 사용자가 고른 폴더 | 판정 없음, 항상 교체(R-28) | 조용히 덮어씀 | 있음 | 앱만(토큰 = 고른 경로 문자열) |
| 앱 `detach_local_skill_source` | `local`, `import` | 없음 | 없음 | 파일 안 건드림 | 없음 | 없음 |
| CLI `set-source` | 모든 값 | 지정한 Git URL의 head | 저장 해시 ≠ 원격 폴더 해시(R-31) | 같으면 보존, 다르면 `--force` 없이 거절, `--force`면 조용히 덮어씀 | **없음** | `--force` 플래그 |

**UI 상태 데이터** (`MySkills.tsx`): `updatingSkillId: string?`(스피너·버튼 비활성), `batchUpdating: bool`, `pendingRemoval: {skill, removals: PendingRemoval[], approval: string?, relinkSource?: string}?`(승인 대화상자의 상태, R-40).

### 1.4 행동 규칙과 남은 질문 [필수]

**A. 무엇과 무엇을 비교하고, 로컬 수정은 어떻게 되나** (질문 a, b, c)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | git·skillssh 갱신(`update_git_skill_internal`)이 `content_changed`를 정한다 (질문 a) | `content_changed = (함수 시작 때 읽은 스킬 행의 content_hash ≠ SHA-256(임시 체크아웃 안 스킬 폴더 원본))`. 저장 해시가 NULL이면 항상 true. **라이브러리 사본의 현재 디스크 내용은 해시하지 않는다.** `source_revision`·`remote_revision`도 이 판정에 안 쓴다(리비전 비교는 변경 확인 스펙의 몫이라, "Update 배지가 떴는데 갱신이 `content_changed=false`"가 가능하다). 원격 쪽 해시는 스테이징 사본이 아니라 체크아웃 폴더를 해시한 값이고 범위는 metadata R-10을 따른다 | 코드 확인, 실행 확인(번역본: T-01~T-04) |
| R-02 | 저장 해시를 누가 쓰나 | 저장 해시는 설치·갱신·재가져오기·relink·set-source가 "방금 쓴 폴더의 해시"로 쓴다(R-21, R-27, R-28, R-33). 그리고 **앱·CLI 프로세스를 시작할 때마다**(메타데이터 폴더가 있으면, 설치 이후 항상) `reindex_from_metadata`가 모든 행의 `content_hash`를 디스크 폴더의 새 해시로 덮어쓴다(metadata R-12). 결과: 로컬 수정은 "프로세스가 다시 시작되기 전"에는 저장 해시 밖에 있고, 시작한 뒤에는 수정을 포함한 해시가 저장 해시가 된다. 그러면 R-01 비교는 "원격 대 (수정이 든) 디스크"가 되어, 원격 폴더가 그대로여도 `content_changed=true`이고 교체한다(R-03). 다른 reindex 호출처: Git 백업 pull 뒤 | 코드 확인, 실행 확인(번역본: T-03, T-04) |
| R-03 | `content_changed=true`일 때 (질문 b) | **병합·충돌 감지는 없다.** 새 내용을 스테이징 사본으로 복사하고(R-19) 라이브러리 폴더 전체를 그 사본으로 바꿔치기한다(R-20). 같은 경로의 파일은 로컬에서 고친 내용이 있어도 경고 없이 새 내용이 된다. 3-way 병합, `.orig` 보관, 백업 보존은 없다(swap이 끝나면 옛 폴더는 지운다). `skills.rs` 안에 병합·충돌 처리 코드가 없다(`merge::`·`conflict` 검색 결과 없음). `core/merge/`는 기기 간 라이브러리 병합이라 이 흐름과 무관하다 | 코드 확인, 실행 확인(번역본: T-01) |
| R-04 | `content_changed=false`일 때 | 스테이징도 swap도 하지 않는다. 라이브러리 파일은 그대로(로컬 수정·추가도 그대로). 출처 필드 `source_ref_resolved`=clone URL, `source_subpath`=이번에 해석한 하위 폴더, `source_branch`, `source_revision`=head를 쓰고(`updated_at`=지금), `update_status`=`up_to_date`, `remote_revision`=head, `last_check_error`=NULL로 쓴 뒤 copy 배포 사본을 다시 맞추고 메타데이터 파일을 다시 쓴다. 단 사라질 파일 확인은 배포 사본에 대해 여전히 한다(R-08) | 코드 확인, 실행 확인(번역본: T-03) |
| R-05 | 사라질 파일 목록 `removed_paths(현재 폴더, 대체 폴더)` (질문 c) | "현재 폴더에 있는데 대체 폴더에는 없는 경로"만 센다. 이름이 `__pycache__`, `.DS_Store`, `Thumbs.db`이거나 `.pyc`로 끝나는 항목은 어느 깊이에서도 제외한다(`.gitignore`·`.git`은 제외하지 않는다). 폴더째 없으면 그 폴더 하나만 `이름/`으로 올리고 안으로 들어가지 않는다. 같은 경로인데 종류(심볼릭 링크 / 폴더 / 파일)가 다르면 사라지는 것으로 센다. 같은 경로·같은 종류이면 폴더만 안으로 내려간다(파일은 내용 비교 없음). 현재 폴더가 없으면 빈 목록, 폴더가 아닌 파일·링크면 `.` 한 줄, 그 밖의 I/O 오류는 오류로 올려 갱신 자체를 실패시킨다("사라질 게 없다"고 잘못 답하지 않기 위해). 결과는 문자열 정렬, 경로 구분자는 Windows에서 `/`로 통일 | 코드 확인, 실행 확인(번역본: T-06) |
| R-06 | 목록이 **잡지 못하는 것** (질문 c) | (1) 같은 경로에 새 버전도 있는 파일의 내용 수정(`SKILL.md` 포함)과 실행 비트 변경. 목록에 없고 경고도 없이 새 내용으로 교체된다. (2) 폴더째 사라질 때 그 안의 개별 파일(`outputs/` 한 줄이 전부이고, 승인 뒤 그 안에 새로 생긴 파일도 같은 줄로 덮인다, R-13). (3) `content_hash`가 무시하는 이름(`.gitignore`, `Thumbs.db` 등)만 바뀐 경우는 R-01 판정 자체가 달라지지 않아 교체되지 않는다. (4) 심볼릭·정션 배포 사본의 내용(R-08). (5) 새 버전에서 업스트림이 지운 파일을 사용자가 고쳐 둔 경우는 목록에 **나온다**(경로가 없으므로) — 사용자 파일과 업스트림 삭제를 구분하지 않는다 | 코드 확인, 실행 확인(번역본: T-06) |
| R-07 | 비교 기준 트리 | 라이브러리와 비교하는 대상은 원격 체크아웃이 아니라 **스테이징 사본**이다. 복사 함수가 `.git`, `.DS_Store`, 모든 심볼릭 링크를 빼므로(설치 C-18) 라이브러리 폴더 안의 `.git/`, 심볼릭 링크는 새 버전에 같은 이름이 없는 한 항상 목록에 오른다 | 코드 확인, 실행 확인(번역본: T-06) |
| R-08 | copy 모드 배포 사본 | `pending_removals_for`는 스킬의 `skill_targets` 중 `mode='copy'`인 것마다 `removed_paths(target_path, 새 트리)`를 구해 `location`=그 `tool` 키로 목록에 더한다. 새 트리는 스테이징 사본이거나, `content_changed=false`이면 라이브러리 폴더다(교체가 없어도 배포 사본은 다시 만들어지므로 확인한다). 다른 모드(심볼릭 링크·정션)는 건너뛴다. 그래서 에이전트가 배포 사본 안에 쓴 파일이 목록에 오르고, `content_changed=false`인데 Held가 나올 수 있다 | 코드 확인, 실행 확인(번역본: T-07), 원본 테스트 열람(`a_metadata_only_update_still_checks_the_deployed_copies`, `symlink_deployments_are_not_reported`) |

**B. 승인 토큰** (질문 e)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-09 | `removal_approval_token(revision, pending)` | SHA-256을 계산하고 hex(소문자)로 돌려준다: 먼저 `revision` 문자열의 UTF-8 바이트, 이어서 `"<location>\0<path>"` 문자열을 문자열 정렬한 순서로 각각 먹이고 바이트 `0`을 하나씩 붙인다. `revision` 자리에 들어가는 값: git 갱신 = 이번에 조회한 원격 head, 재가져오기 = 상수 `"reimport"`, relink = 사용자가 준 `source_path` 문자열. **스킬 id, 파일 내용, 해시는 입력이 아니다**. 즉 토큰은 "이 head(또는 이 경로) 기준으로 이 (위치, 경로) 집합"만 가리킨다 | 코드 확인, 실행 확인(번역본: T-05), 원본 테스트 열람(`an_approval_does_not_carry_to_a_different_revision_or_list`) |
| R-10 | 교체 직전(스테이징 뒤, swap 전) 판정 | 목록이 비어 있으면 호출자의 토큰은 보지 않는다(있어도 무시). 목록이 비어 있지 않고 `approved_removals == 이번에 계산한 토큰`이면 진행한다. 비어 있지 않고 다르거나 없으면 Held(R-11). 따라서 승인 호출도 목록·head를 **다시 계산**하고 다시 비교한다 | 코드 확인 |
| R-11 | Held | 스테이징 사본 삭제(`StagedPathGuard`), 라이브러리·배포 사본·출처 필드 불변. git 갱신은 락 안에서 `update_skill_check_state(remote_revision=head, "update_available", error=NULL)`을 쓴다(`last_checked_at`=지금, `updating`이 남지 않게 하려는 처리). 재가져오기·relink는 호출 전의 `update_status`를 그대로 되돌린다(다른 열은 안 건드린다). 결과로 `pending_removals`(비어 있지 않음)와 `removal_approval`을 돌려주고 `content_changed`는 false(DTO가 없는 재가져오기 제외) | 코드 확인, 실행 확인(번역본: T-02, T-10), 원본 테스트 열람(`a_stale_reimport_approval_does_not_authorize_a_grown_list`) |
| R-12 | 승인 호출 | 승인 호출은 새 호출이다. git 갱신이면 `ls-remote`부터 clone·해시까지 다시 한다. 그 사이 원격이 움직였으면 head가 달라 토큰이 안 맞아 Held가 다시 나온다(새 토큰). 로컬에서 목록이 자라거나 줄어도 마찬가지다 | 코드 확인, 실행 확인(번역본: T-05) |
| R-13 | 승인 뒤의 변경이 토큰에 잡히는 범위 (질문 e, TOCTOU) | **잡힌다**: head 이동, 사라질 (위치,경로) 집합의 증가·감소(새 최상위 파일, 새 배포 사본 파일 등). **잡히지 않는다**: (1) 목록 밖 파일의 수정 — 특히 새 버전에도 있는 파일의 편집(R-06). (2) 이미 올라간 `outputs/` 같은 폴더 줄 안에 새로 생긴 파일. (3) 목록 계산과 swap 사이(스테이징·토큰 비교 직후부터 `rename`까지)에 에이전트 프로세스가 쓰는 파일: `RepoLock`은 Skills Manager끼리만 막는다. (4) copy 배포 사본: 목록 계산 시점과 `resync_copy_targets`(swap·DB 쓰기 뒤) 사이에 쓰인 파일(창이 (3)보다 길다, 추론: swap과 두 번의 DB 쓰기 뒤에 재동기화가 실행되는 순서에서 도출). 원본 주석(`skills.rs:2183-2191`)도 (2), (3)을 인정하고 "디렉터리를 먼저 얼려야 줄어든다"고 적었다 | 코드 확인, 실행 확인(번역본: T-05) / 추론((4)) |

**C. git·skillssh 갱신의 단계와 실패 때 상태**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-14 | 입력 검증 | 행이 없으면 `not_found` "Skill not found". `source_type`이 `git`·`skillssh`가 아니면 `invalid_input` "Only git-based skills can be updated". 이어 `git_source_from_skill`(변경 확인 R-04의 3분기와 같은 오류)과 `validate_git_url`(설치 R-02, `git` kind). 이 셋은 DB를 쓰지 않는다(상태 불변). `update_status`가 무엇이든 호출할 수 있다 | 코드 확인 |
| R-15 | `resolve_remote_revision` 실패 | `update_skill_check_state(remote_revision=이전 값, "error", 메시지)`를 쓰고(`last_checked_at`=지금) `git` kind 오류를 돌려준다. 이 시점엔 `updating`을 아직 쓰지 않았고 파일은 안 건드렸다 | 코드 확인 |
| R-16 | 원격 head를 얻은 뒤 `updating`을 쓰고 clone | `update_skill_update_status("updating")`(다른 열 불변) → `clone_repo_ref_scoped(clone_url, branch, subpath, cancel, proxy)`(설치 R-04). **clone이 실패·취소·시간초과하면 `AppError::classify_git_error`(설치 R-20)로 분류한 오류를 즉시 돌려주고 `updating`을 되돌리지 않는다**: `update_status`가 `updating`으로 남고 `last_check_error`도 안 바뀐다(아래 클로저의 `error` 기록 밖이다). `update_skill`은 취소 키 `update:<skill_id>`를 등록하지만(작업이 끝나면 제거) 이 키를 취소하는 UI·CLI 호출이 없다(`cancelInstall` 호출처는 설치 화면뿐). 다른 호출자(일괄, CLI, 자동, set-source)는 취소 토큰이 없다 | 코드 확인(상태 잔존은 구현에서 도출, 실행 안 함) |
| R-17 | clone 뒤 체크아웃·폴더 결정 | `checkout_revision(임시폴더, head)`(`git checkout --detach`, 실패하면 libgit2): clone 뒤 원격이 움직여 head가 clone에 없으면 실패한다(`git` kind, 원격 head는 `ls-remote`로 따로 구하므로 가능한 경주). 그다음 `resolve_skill_dir(임시폴더, source_subpath, locator)`(설치 R-05: 하위 폴더가 사라졌고 locator가 없으면 `not_found`, skillssh는 locator로 폴더를 다시 찾는다). 새로 얻은 폴더의 체크아웃 상대 경로(`relative_subpath`)가 이후 `source_subpath`에 기록된다(루트면 NULL). 해시(R-01)도 여기서 계산한다. 실패는 R-23 | 코드 확인 |
| R-18 | 락 구간 | 네트워크·체크아웃·해시는 락 밖이다. 락(`acquire_foreground("update installed skill")`)은 해시 직후 잡고 메타데이터 재작성까지 쥔다. 못 잡으면 `database` kind "skills repository is busy: update installed skill"이고 R-23(`error`)로 처리한다. 락을 잡은 뒤 **스킬 행을 다시 읽지 않는다**: R-01의 저장 해시·`central_path`·이름은 락 전 스냅샷 그대로다 | 코드 확인 |
| R-19 | `content_changed=true` 스테이징 | `install_skill_dir_to_destination(원격 폴더, skill.name, staged_path)`(설치 C-17, C-18: `.git`·`.DS_Store`·심볼릭 링크 제외 복사, 복사본 해시 계산). `staged_path`는 `<라이브러리 폴더 옆>/.<폴더이름>.staged-<uuid>`(C-05). 복사 실패는 `io` kind이고 스테이징 폴더를 지운다. 이어 `pending_removals_for`(R-05~R-08)와 R-10 판정 | 코드 확인 |
| R-20 | swap (`swap_skill_directory(staged, current)`) | 현재 폴더가 있으면 `.<이름>.backup-<uuid>`로 rename → staged를 현재 이름으로 rename → backup 삭제. 두 번째 rename이 실패하면 backup을 되돌리고 staged를 지우고 오류를 낸다. backup 삭제가 실패하면(교체는 이미 끝난 뒤인데도) 오류를 돌려준다. 같은 부모 폴더 안의 rename이라 같은 파일시스템이다. 현재 폴더가 없으면 staged를 그 이름으로 옮기기만 한다. 파일 삭제 헬퍼는 폴더면 재귀 삭제, 파일이면 삭제, 없으면 아무것도 안 한다 | 코드 확인, 실행 확인(번역본: T-08) |
| R-21 | 적용이 성공할 때 쓰는 값 | **내용 변경**: (1) `update_skill_source_metadata(source_ref_resolved=clone URL, source_subpath=R-17의 값, source_branch, source_revision=head)`(`updated_at`=지금), (2) `update_skill_after_install(name=기존 이름, description=새 SKILL.md의 값, source_revision=head, remote_revision=head, content_hash=스테이징 해시, "up_to_date")`(`updated_at`=`last_checked_at`=지금, `last_check_error`=NULL). 스킬 `name`·`source_ref`·`source_type`은 안 바뀐다. **내용 같음**: (1)과 `update_skill_check_state(head, "up_to_date", NULL)`. 둘 다 이어서 `resync_copy_targets`(R-22)와 `write_all_from_db_unlocked`(metadata R-18). (1)과 (2)는 한 트랜잭션이 아니다 | 코드 확인 |
| R-22 | `resync_copy_targets(store, skill_id)`의 경계 | 입력: 스킬 id(행을 DB에서 다시 읽어 방금 쓴 `central_path`·`content_hash`를 쓴다). 동작: 그 스킬의 `mode='copy'` 배포 행마다, 기록이 "현재"이면 건너뛰고(`recorded_target_is_current`: 행 `status='ok'`이고 배포 위치가 일반 폴더이거나 원본으로의 링크이며 해시가 맞음) 아니면 `sync_skill(라이브러리 폴더, target_path, Copy, Recorded{mode})`로 배포 사본을 다시 만든 뒤 행을 `synced_at`=지금, `status='ok'`, `last_error`=NULL, `source_hash`=라이브러리 `content_hash`로 다시 쓴다. 다른 모드는 건드리지 않는다. 실패하면(`sync_skill`이 기록과 디스크가 안 맞는다며 거절하는 경우 포함) 첫 오류가 `io` kind로 올라와 갱신 전체가 실패 처리된다(R-23). 두 판정 함수와 `sync_skill`의 내부는 읽지 않았다(확인 한계) | 코드 확인(경계만) |
| R-23 | 클로저 안 실패(체크아웃, 폴더 결정, 해시, 락, 스테이징, 목록 계산, swap, DB 쓰기, 재동기화, 메타데이터) | 임시 체크아웃은 지운다. 그다음 `update_skill_check_state(remote_revision=head, "error", 메시지)`을 쓰고(`last_checked_at`=지금) 오류를 그대로 돌려준다. **되돌리기는 없다**: swap 뒤에 실패하면 라이브러리는 이미 새 내용이고 DB의 `content_hash`·`source_revision`은 실패 지점에 따라 새 값이거나 옛 값이다. 예: 재동기화가 실패하면 라이브러리·DB 내용은 새것, 상태만 `error`, 메타데이터 파일은 안 다시 쓰였다. 다음 변경 확인(`error`는 TTL을 안 탄다)이 상태를 다시 정한다. DB 쓰기 (1)과 (2) 사이에서 실패하면 저장 해시는 옛 값이라 다음 갱신이 `content_changed=true`로 같은 내용을 다시 swap한다(자체 복구, 추론) | 코드 확인 / 추론(복구) |
| R-24 | 성공 반환 | `managed_skill_by_id`로 다시 읽은 스킬, `content_changed`, Held가 아니므로 `pending_removals=[]`·`removal_approval=null` | 코드 확인 |
| R-25 | 감사 로그 | 앱의 `update_skill`·`batch_update_skills`·`reimport_local_skill`만 `log_update_outcome`/`log_reimport_outcome`으로 `update` 행을 남긴다. 상세: git·skillssh 라벨은 항상 `git`로 `git; content changed` / `git; unchanged` / `git; held back — would remove N path(s)`, 재가져오기는 `local`(Held는 `local; held back — would remove N path(s)`), 실패는 오류 문자열. **CLI `update`·`set-source`, relink, detach, 자동 갱신(스케줄러)은 감사 로그를 남기지 않는다** | 코드 확인 |

**D. 일괄 갱신**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-26 | `batch_update_skills(skill_ids)` | 목록 순서대로 하나씩(병렬 없음). 행이 없으면 `failed`에 `"<id>: Skill not found"`. `git`·`skillssh`이면 `update_git_skill_internal(승인 없음, 취소 없음)`: Held면 `held_back`에 스킬 이름, 아니면 `content_changed`에 따라 `refreshed`/`unchanged`, 오류는 `failed`에 `"<이름>: <메시지>"`. `local`·`import`이면 `reimport_local_skill_internal(승인 없음)`: Held면 `held_back`, 성공이면 **항상** `refreshed`(원본이 안 바뀌었어도), 오류는 `failed`. 그 밖(`well-known` 등)은 `failed`에 `"<이름>: Source type cannot be refreshed"`. 감사 로그는 스킬마다 남는다(R-25). **행 읽기의 DB 오류가 나면 전체가 그 오류로 끝나고 지금까지의 카운트는 버려진다**(앞서 적용된 갱신은 남는다). 일괄 호출은 사라질 파일 승인 수단이 없다 | 코드 확인 |

**E. 로컬 재가져오기·재연결**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-27 | `reimport_local_skill_internal(skill_id, approved)` (질문 d) | 행이 없으면 `not_found`. `source_type`이 `local`·`import`가 아니면 `invalid_input` "Only local skills can be reimported". `source_ref`가 NULL이면 `not_found` "Local skill is missing its original source path". 경로가 없으면 `update_skill_check_state(None, "source_missing", "Original source path no longer exists")`를 쓰고 `not_found` "Original source path no longer exists". 있으면 `update_status`=`updating`(락 전)을 쓰고 락(`reimport local skill`) 안에서 `install_from_local_to_destination(source_ref, 기존 이름, staged)`(폴더는 그대로, `.zip`/`.skill`은 풀어서; 이름 정제 실패는 `io` kind)로 스테이징한다. **저장 해시 비교는 없다: 항상 교체한다.** 사라질 파일 확인은 라이브러리 대 스테이징 + copy 배포 사본(R-05~R-08), 토큰은 `토큰("reimport", 목록)`. Held면 R-11(이전 `update_status` 복원). 아니면 swap 후 `update_skill_after_install(name, description=원본의 값, source_revision=NULL, remote_revision=NULL, content_hash=스테이징 해시, "local_only")`(`last_check_error`=NULL), 재동기화, 메타데이터 재작성. 클로저 실패는 `update_skill_check_state(None, "error", 메시지)`. 같은 경로의 파일에 대한 로컬 수정은 소리 없이 원본 내용이 된다. 원본이 폴더인지 `SKILL.md`가 있는지는 검사하지 않는다 | 코드 확인, 실행 확인(번역본: T-10), 원본 테스트 열람(`a_stale_reimport_approval_does_not_authorize_a_grown_list`) |
| R-28 | `relink_local_skill_source(skill_id, source_path, approved)` | 행·타입 검사(`Only local skills can relink source paths`), `source_path`가 없으면 `not_found` "Selected source path does not exist", `is_valid_skill_dir`(설치 C-14: 폴더이고 바로 아래에 `SKILL.md`/`skill.md`)가 아니면 `invalid_input` "Selected source path is not a valid skill directory"(그래서 압축 파일은 못 고른다). 이 검사들은 상태를 안 쓴다. 통과하면 `updating`을 쓰고 R-27과 같은 스테이징·목록·Held(이전 `update_status` 복원)를 한다(토큰은 `토큰(source_path 문자열, 목록)`이라 같은 경로를 다시 고른 승인만 유효). 적용은 swap 후 `update_skill_after_reinstall(source_type=기존 값, source_ref=source_path, resolved·subpath·branch·두 리비전=NULL, content_hash=스테이징 해시, "local_only")`, 재동기화, 메타데이터 재작성. 클로저 실패는 `error`. 백엔드는 `source_missing`일 때만 허용하지 않는다(UI만 그때 버튼을 보인다, R-39) | 코드 확인 |
| R-29 | `detach_local_skill_source(skill_id)` | 행·타입 검사(`Only local skills can detach source paths`). 락(`detach local skill`) 안에서 `update_skill_after_reinstall(source_type=기존 값, source_ref=NULL, resolved·subpath·branch·두 리비전=NULL, content_hash=기존 값, "local_only")`와 메타데이터 재작성. **파일을 안 건드리고 `updating` 표시도 안 쓴다.** 이후 `source_ref`가 NULL인 local은 변경 확인이 `local_only`로 둔다(변경 확인 R-07) | 코드 확인 |

**F. set-source (출처를 Git으로 다시 지정)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-30 | `set_git_source_internal` 입력 해석과 clone | 행이 없으면 `not_found`. **`source_type`에 제한이 없다**(local·import·well-known·skillssh·git 모두 허용). `validate_git_url(git_url)`을 파싱 전에 한다(트리 URL 해석이 `ls-remote`를 쓰므로). `parse_git_source_resolved(git_url, proxy)`(설치 R-03) 뒤 플래그가 URL에서 얻은 값보다 우선한다: `--branch`가 있으면 그 값, `--subpath ""`는 "루트"(NULL), `--subpath X`는 X, 플래그가 없으면 URL이 정한 값. 이어 `resolve_remote_revision`(변경 확인 R-16)과 `clone_repo_ref_scoped`(취소 없음)와 `checkout_revision`. 여기까지는 DB를 쓰지 않아 실패해도 상태가 안 바뀐다. 스킬 폴더는 **엄격 규칙** `resolve_repoint_skill_dir`(C-11)로 정한다: subpath가 없으면 체크아웃 루트가 스킬 폴더여야 하고(아니면 `invalid_input` "Repository root is not a skill directory (no SKILL.md); pass --subpath"), 있으면 체크아웃 밖이면 `invalid_input` "Subpath '<s>' resolves outside the repository"(절대 경로·`..`·밖을 가리키는 링크 포함), 폴더가 아니면 `not_found` "Subpath '<s>' does not exist in the repository", `SKILL.md`가 없으면 `invalid_input` "Subpath '<s>' is not a skill directory (no SKILL.md)". `resolve_skill_dir`처럼 `skills/`로 폴백하지 않는다 | 코드 확인, 원본 테스트 사례 이름 열람(`repoint_*` 8개) |
| R-31 | 내용 비교·거절·`--dry-run` (질문 d) | `content_changed = (행의 저장 해시 ≠ 원격 폴더 해시)`(R-01과 같은 규칙, 같은 스냅샷). `--dry-run`이면 이 시점에서 `{content_changed, resolved subpath}`를 돌려주고 끝난다(쓰기·락 없음, 네트워크·clone은 했다). dry-run이 아니고 `content_changed`이고 `--force`가 없으면 `invalid_input` "New source content differs from the current library copy; re-run with --dry-run to inspect, or --force to overwrite". 이 거절은 상태를 안 쓴다. **어느 파일이 다른지는 알려 주지 않는다** | 코드 확인, 실행 확인(번역본: T-09) |
| R-32 | 락 뒤 스냅샷 재확인 | 락(`set skill source`)을 잡은 뒤 행을 다시 읽는다. 행이 없으면 `not_found` "Skill was removed while fetching the source". `central_path`, `content_hash`, `source_type`, `source_ref` 중 하나라도 처음 읽은 값과 다르면 `invalid_input` "Skill changed while fetching the source; re-run the command". 이 두 경우 상태를 안 쓴다. (갱신 R-18은 이 재확인이 없다) | 코드 확인 |
| R-33 | set-source 적용 | `updating`을 쓴 뒤: **내용이 같으면** 파일 작업 없음(저장 해시가 같다고 본 것이므로 라이브러리의 손 수정·추가 파일은 그대로, `description`은 기존 값). **다르면(그리고 `--force`)** 스테이징 → **사라질 파일 확인 없이** swap: 라이브러리에만 있던 파일은 목록·승인 없이 사라진다. 이어 `update_skill_after_reinstall(source_type="git", source_ref=입력 URL(트림), source_ref_resolved=clone URL, source_subpath=해석한 하위 폴더, source_branch=결정한 브랜치, 두 리비전=head, content_hash=원격 폴더 해시, "up_to_date")`(`updated_at`=`last_checked_at`=지금, `last_check_error`=NULL), `resync_copy_targets`, 메타데이터 재작성. 행의 `id`·태그·프리셋 멤버십·배포 기록은 그대로다. 결과 `SetSourceResult.content_changed`는 R-31 값 | 코드 확인, 실행 확인(번역본: T-09) |
| R-34 | set-source 실패 때 상태 | 네트워크 단계·검증·거절·재확인 실패는 상태 불변(`updating`을 쓰기 전). `updating`을 쓴 뒤의 실패(스테이징, swap, DB, 재동기화, 메타데이터)는 `update_skill_check_state(revision, "error", 메시지)`: `revision`은 출처 재지정이 DB에 커밋된 뒤면 새 head, 아니면 행의 옛 `remote_revision`. 이 함수에는 `updating` 잔존 경로가 없다(프로세스 종료 제외) | 코드 확인 |

**G. 동시 실행·중단**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-35 | 락과 동시 호출 | 파일 락은 앱·CLI·트레이·스케줄러가 공유한다. 이 기능은 각자 쓰기 구간(R-18)만 잡고 네트워크는 락 밖이다. 같은 스킬에 대한 동시 `update_skill`을 막는 장치는 백엔드에 없다(UI는 `updatingSkillId`로 버튼만 막는다). 락 대기 중 같은 스킬이 이미 갱신됐다면 낡은 스냅샷 때문에 같은 내용을 다시 swap한다(안전, 추론). 락 대기 중 그 스킬이 삭제됐다면(삭제는 락 안에서 라이브러리 폴더와 행을 지운다) 갱신은 폴더가 없는 자리에 스테이징 사본을 옮겨 놓고(R-20), 행이 없어 DB 쓰기가 아무 행도 못 바꾸고, `resync_copy_targets`가 `not_found`로 실패한다: 행 없이 폴더만 되살아난다(추론, 코드 경로에서 도출) | 코드 확인 / 추론(삭제·중복 경주) |
| R-36 | `updating`이 남는 경우와 그 표시 | 코드가 `updating`을 쓰는 곳은 갱신(R-16), 재가져오기·relink(락 전), set-source(락 안) 네 곳뿐이고, 되돌리는 쪽은 R-11·R-23·R-34·R-27·R-28의 `error`/복원이다. 되돌리지 않는 경우: (1) git 갱신 중 clone 실패·취소(R-16), (2) 프로세스 종료·패닉(복구 코드 없음, 시작 때 `updating`을 지우는 코드 없음). `updating`은 변경 확인이 "안정 상태가 아님"으로 보아 TTL 안에서도 다시 확인한다(metadata R-14). 화면은 `updating` 배지를 그리지 않는다(`statusBadge`는 `update_available`·`source_missing`·`error`만, R-39): `updating`으로 남은 스킬은 배지·"Update" 알약 없이 보이지만 카드 메뉴의 갱신 항목은 `canRefresh`만 보므로 그대로 누를 수 있다 | 코드 확인 |

**H. 입구: CLI와 UI**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-37 | CLI `skills update [REF] [--all]` | 대상은 REF 하나 또는 `--all`(모든 행, 순서는 DB 순서). 스킬마다 순차로: `git`·`skillssh` → `update_git_skill_internal(승인 없음)`, `refreshed = content_changed`(Held면 false + `held_back_removals`). `local`·`import` → `reimport_local_skill_internal(승인 없음)`, `refreshed = (사라질 파일 없음)`이라 원본이 안 바뀌었어도 true. 그 밖은 `error: "source type '<x>' cannot be refreshed"`. 스킬별 오류는 프로세스 실패가 아니라 그 항목의 `error`(종료 코드 0). `update_status`를 보지 않으므로 `check` 없이도 호출되고 up_to_date 스킬도 갱신 경로를 지난다. 승인 수단은 없다(`held_back_removals`를 사람에게 보여 줘야 하기 때문, 주석). 감사 로그 없음(R-25). 출력은 `--json`이면 한 줄, 아니면 들여쓴 JSON | 코드 확인 |
| R-38 | CLI `skills set-source` | R-30~R-34를 그대로 부른다(앱 UI 입구는 없다: `src/` 어디에서도 `set-source`·`set_git_source`를 호출하지 않는다). REF는 id·이름·중앙 경로·폴더 이름 중 하나. 실패는 `AppError`가 `details`를 갖지 않으므로 `--json`에서 `{ok:false, code:"COMMAND_FAILED", message, error}`, 종료 코드 1(설치 R-26 끝 문장과 같은 공통 경로). 성공 출력은 `SetSourceResult` JSON | 코드 확인 |
| R-39 | My Skills 화면의 호출 | `canRefresh` = `git`·`skillssh`이거나 `source_ref`가 있는 `local`·`import`(변경 확인 R-27과 같음). 호출 입구: (1) `update_status == update_available && canRefresh`일 때의 "Update" 알약(그리드·리스트)과 상단 "Update N" 버튼(= `update_available`인 `canRefresh` 전체를 `batch_update_skills`), (2) 카드/행 메뉴의 갱신 항목(라벨 `Re-import`/`Update`)은 `canRefresh`면 상태와 무관하게 있다, (3) 다중 선택의 일괄 갱신은 선택한 `canRefresh` 스킬 전부를 `batch_update_skills`(상태 무관). (4) `source_missing`인 local·import에만 "Relink"/"Detach" 버튼(Relink는 폴더 선택 대화상자 → `relink_local_skill_source`). 단건은 `local`·`import`이면 `reimport_local_skill`, 아니면 `update_skill`. 결과 표시: 단건 성공 `content_changed`면 "updated" 토스트, 아니면 "already up to date" 토스트(재가져오기는 "reimported"); 실패는 오류 토스트이고 어느 쪽이든(Held 제외) 목록을 다시 읽는다. 일괄은 `refreshed`·`unchanged`·`held_back`(앞 3개 이름을 `、`로 이어 경고 토스트)·`failed`(건수만 오류 토스트)로 토스트를 나눠 띄우고 끝에 목록을 다시 읽는다 | 코드 확인 |
| R-40 | 승인 대화상자와 토큰 전달 | 단건 호출의 결과에서 `pending_removals`가 비어 있지 않으면 `pendingRemoval = {skill, removals, approval, relinkSource?}`를 저장하고(목록 재읽기·성공 토스트 없음) `ConfirmDialog`(tone `warning`)를 연다: 제목 "This update removes files", 본문은 건수와 "내 파일이면 스킬 폴더 밖으로 옮기라"는 안내와 "nothing has changed yet", 항목마다 `path`(`library`) 또는 `<에이전트 키>: <path>` 한 칩(자르지 않음, 스크롤), 확인 버튼 "Update anyway". 확인하면 대화상자 상태를 비운 뒤 같은 입구(relink면 저장해 둔 `relinkSource`로)를 `approved = 저장한 approval`로 다시 호출한다. 취소·Esc·바깥 클릭은 백엔드를 부르지 않고 상태만 비운다(스킬은 `update_available` 그대로) | 코드 확인 |
| R-41 | 승인 호출이 다시 Held로 돌아올 때 (UI) | `onConfirm`이 `setPendingRemoval(null)` → 핸들러 호출(다시 Held면 새 `pendingRemoval`을 저장) → 반환 후 `ConfirmDialog.handleConfirm`이 `onClose()`(= `setPendingRemoval(null)`)를 부른다. 이 순서에서는 다시 묻는 대화상자가 곧바로 지워지고 토스트도 없다: 사용자는 "Update anyway"를 눌렀는데 아무 일도 일어나지 않은 것처럼 보이고 파일은 안 바뀐다. 코드 순서에서 도출한 결과이고 앱을 실행하지 않았다 | 추론 |
| R-42 | 자동 적용 경계(타이머·옵트인은 범위 밖) | 주기 스케줄러(`skill_auto_updater`)는 `update_available`로 판정된 스킬을 `update_git_skill_internal(승인 없음, 취소 없음)`로, 앱 시작 때 `auto_update_apply == "on"`이면 `update_available`인 git·skillssh를 `batch_update_skills`로 적용한다. 둘 다 사라질 파일이 하나라도 있으면 Held로 **적용하지 않고** 건수만 센다(`held_back`). 사라질 파일이 없으면 적용된다 — 같은 경로 파일의 로컬 수정은 이 경로에서도 경고 없이 덮인다(R-06) | 코드 확인 |

- 불변식:
  - Held에서 파일·행의 출처 필드는 안 바뀐다. 바뀌는 열은 git 갱신의 `update_status`·`remote_revision`·`last_checked_at`·`last_check_error`뿐이다(R-11).
  - 교체(swap)는 라이브러리 폴더 하나를 단위로 한다: 새 폴더 전체가 들어오거나(성공), 옛 폴더가 그대로다(Held·스테이징 실패·rename 실패). 부분 복사 상태는 라이브러리 폴더 이름 아래 남지 않는다. 전제: R-20의 두 `rename`이 같은 파일시스템에서 원자적이다.
  - 갱신·재가져오기·relink는 사라질 파일 확인과 같은 스테이징 사본을 swap한다(확인한 트리와 설치되는 트리가 같다). set-source `--force`는 확인이 없다.
  - 저장 해시는 "마지막으로 이 기능이 쓰거나 프로세스 시작이 다시 계산한 디스크 해시"이지 "설치 당시 기준선"이 아니다(R-02). 따라서 로컬 수정 여부를 이 값으로는 알 수 없다.
- 미결정: 없음.
- 확인 한계:
  - 앱·CLI·Rust·`cargo test`를 실행하지 않았다. 실행 확인(번역본)은 이 스펙의 판단 규칙(해시 비교, 사라질 파일 목록, 토큰, swap)을 Python으로 옮겨 로컬 `file://` 저장소로 돌린 것이다(2.3). Rust 출력과 해시 바이트는 대조하지 않았다.
  - 원격(GitHub 등)의 실제 동작(오래된 revision 보존, clone 속도, 인증)은 확인하지 않았다. R-17의 clone/ls-remote 경주는 소스 diff 스펙 R-19의 git CLI 실험이 같은 현상을 보였다.
  - `resync_copy_targets`가 쓰는 `recorded_target_is_current`·`is_target_current`·`sync_skill`의 내부는 읽지 않았다(R-22는 호출 경계).
  - Windows 동작(`rename` 의미, 경로 구분자)은 `cfg(windows)` 코드를 읽지 않았다.
  - R-41은 React 상태 갱신 순서에서 도출했다. R-13(4), R-23의 자체 복구, R-35의 경주 결과는 코드 경로에서 도출한 추론이다.

### 1.5 필수 코드 참조 [필수]

라이선스: MIT(overview 1절)라 인용을 허용한다. 모든 줄 범위는 `7a22192` 기준이다. 경로는 `repos/skills-manager` 기준 전체 경로다. 다른 스펙이 이미 가진 코드는 그 C-ID를 쓴다: `git_source_from_skill`(변경 확인 C-04), `resolve_remote_revision`(변경 확인 C-08, C-09), `validate_git_url`(설치 C-01), `parse_git_source_resolved`(설치 C-02~C-05), `clone_repo_ref_scoped`(설치 C-06), `relative_subpath`(설치 C-08), `resolve_skill_dir`(설치 C-10), `is_valid_skill_dir`(설치 C-14), `install_skill_dir_to_destination`·복사 함수(설치 C-17, C-18), 복사 결과의 에러 종류(설치 C-29, C-30), `hash_directory`(metadata C-10), 출처 setter(metadata C-03, C-04), 메타데이터 재작성(metadata C-12), reindex의 행 조립(metadata C-06), `is_path_safe`(원본 diff C-16).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src-tauri/src/commands/skills.rs:26-81` `UpdateSkillResult`, `REIMPORT_APPROVAL_DOMAIN`, `ReimportSkillResult`, `PendingRemoval`, `LIBRARY_LOCATION`, `UpdateOutcome` | 결과 DTO 필드, 위치 문자열 `"library"`, 재가져오기 토큰 도메인 `"reimport"`, Held·Applied 구분 | R-09, R-11, R-24 |
| C-02 | `src-tauri/src/commands/skills.rs:83-146` `pending_removals_for`, `removal_approval_token` | 목록 조립(라이브러리 + copy 배포 사본, 새 트리 선택), 토큰 바이트 열 | R-05, R-08, R-09 |
| C-03 | `src-tauri/src/core/removals.rs:24-148` `is_regenerable`, `removed_paths`, `kind_of`, `collect`, `display_path` | 사라질 경로 계산 전체(제외 이름, 폴더 롤업, 종류 비교, 오류 처리, 표시 형식) | R-05, R-06, R-07 |
| C-04 | `src-tauri/src/commands/skills.rs:148-177` `StagedPathGuard` | Held·실패 때 스테이징 사본 정리, swap이 가져가면 해제 | R-11, R-19 |
| C-05 | `src-tauri/src/commands/skills.rs:3189-3222` `staged_path_for`, `swap_skill_directory`; `:3486-3493` `remove_path_if_exists` | 스테이징·backup 이름, rename 순서와 복구 | R-19, R-20 |
| C-06 | `src-tauri/src/commands/skills.rs:3224-3275` `resync_copy_targets` | copy 배포 사본 재동기화의 입력·건너뜀·행 갱신 | R-22 |
| C-07 | `src-tauri/src/commands/skills.rs:1748-1797` `update_skill`, `reimport_local_skill` | 명령 인자, 취소 키 `update:<id>`, blocking 실행, 감사 로그 호출 | R-16, R-25 |
| C-08 | `src-tauri/src/commands/skills.rs:179-188`, `:1799-1866` `BatchUpdateSkillsResult`, `batch_update_skills` | 일괄 분기와 집계 | R-26 |
| C-09 | `src-tauri/src/commands/skills.rs:2090-2282` `update_git_skill_internal` | git 갱신 전체: 단계 순서, 락 구간, 판정, 쓰기 값, 실패 때 상태 | R-01, R-04, R-10~R-24 |
| C-10 | `src-tauri/src/commands/skills.rs:1868-2018` `relink_local_skill_source`, `detach_local_skill_source` | relink·detach 검사·쓰기·실패 | R-28, R-29 |
| C-11 | `src-tauri/src/commands/skills.rs:2284-2344` `SetSourceResult`, `resolve_repoint_skill_dir` | set-source 결과 필드, 엄격 subpath 해석과 오류 문구 | R-30, R-31 |
| C-12 | `src-tauri/src/commands/skills.rs:2346-2538` `set_git_source_internal` | set-source 전체 | R-30~R-34 |
| C-13 | `src-tauri/src/commands/skills.rs:2540-2643` `reimport_local_skill_internal` | 재가져오기 전체 | R-27, R-11 |
| C-14 | `src-tauri/src/core/installer.rs:103-118` `install_from_local_to_destination` | 원본(폴더 또는 압축)을 정해진 목적지로 설치, 이름 정제 | R-27, R-28 |
| C-15 | `src-tauri/src/core/app_state.rs:54-59`, `:176-180` `initialize_store`, `initialize_cli_store`, 시작 때 reindex 호출; `src-tauri/src/core/sync_metadata.rs:162-270` `reindex_from_metadata_unlocked` | 모든 프로세스 시작에서 `content_hash`를 디스크 해시로 재계산하는 경로 | R-02 |
| C-16 | `src-tauri/src/bin/skills-manager-cli.rs:139-144`, `:204-226` `SkillsCommand::Update`, `SetSource` | CLI 인자와 설명 | R-37, R-38 |
| C-17 | `src-tauri/src/bin/skills-manager-cli.rs:542-556`, `:1773-1843`, `:1900-1915` `UpdateReport`, `run_update`, `select_skill_ids` | CLI 갱신 분기, `refreshed` 정의, 보류 보고 | R-37 |
| C-18 | `src-tauri/src/bin/skills-manager-cli.rs:909-912`, `:968-989` | CLI 디스패치(set-source 인자 전달) | R-38 |
| C-19 | `src/lib/tauri.ts:319-385` `UpdateSkillResult`, `PendingRemoval`, `updateSkill`, `BatchUpdateSkillsResult`, `ReimportSkillResult`, `reimportLocalSkill`, `relinkLocalSkillSource`, `detachLocalSkillSource` | invoke 이름과 인자 이름(camelCase) | 1.3, R-39 |
| C-20 | `src/views/MySkills.tsx:773-976` `handleBatchRefresh`, `pendingRemoval` 상태, `handleUpdateAvailableSkills`, `handleRefreshSkill`, `handleRelinkSource`, `handleDetachSource` | 호출 분기, 토스트, Held 처리 | R-39, R-40 |
| C-21 | `src/views/MySkills.tsx:1139-1142` `canRefresh`, `:1578-1584` `hasUpdate`·`isMissingLocalSource`, `:2065-2092` 승인 `ConfirmDialog` | 입구 노출 조건, 대화상자 연결과 확인 시 재호출 | R-39, R-40, R-41 |
| C-22 | `src/components/ConfirmDialog.tsx:50-58` `handleConfirm`, `:79-90` 세부 목록 칩 | 확인 뒤 `onClose` 호출 순서, 목록 표시 방식 | R-40, R-41 |
| C-23 | `src-tauri/src/core/skill_auto_updater.rs:200-219`; `src/context/AppContext.tsx:361-399` | 자동 적용이 승인 없이 부르고 Held를 세는 경계 | R-42 |
| C-24 | `src-tauri/src/core/repo_lock.rs:33-78` `RepoLock`, `acquire`, `acquire_blocking`, `acquire_foreground` | 파일 락 획득·대기 20초·busy 오류 문구 | R-18, R-35 |
| C-25 | `src-tauri/src/commands/skills.rs:815-889` `log_update_outcome`, `log_reimport_outcome` | 감사 로그 상세 문구 | R-25 |
| C-26 | `src-tauri/src/commands/skills.rs:202-236`, `:2077-2088` `ManagedSkillDto`, `TargetDto`, `managed_skill_by_id` | 갱신 결과에 실리는 스킬 DTO 필드 | 1.3, R-24 |
| C-27 | `src-tauri/src/core/git_fetcher.rs:1308-1328` `checkout_revision`, `:1462-1464` `cleanup_temp` | head로 `checkout --detach`(실패 시 libgit2), 임시 폴더 삭제(오류 무시) | R-17 |
| C-28 | `src-tauri/src/core/scenario_service.rs:275-321` `recorded_target_is_current` | R-22가 건너뜀 판정으로 부르는 함수의 입력·결과(내부 판정은 읽지 않음) | R-22 |

### 1.6 수락 사례 [필수]

출처 표기: "구현"=구현에서 도출, "번역본"=`artifacts/skills-manager/skill-update-apply-demos/update-apply-decisions.py`(Python으로 옮긴 판단 규칙, 출력 `update-apply-decisions.out.2026-10-24.txt`의 같은 번호 시나리오 S1~S10), "테스트"=원본 테스트를 읽고 같은 사례를 도출(위치는 2.1, 실행 안 함). 번역본은 Rust를 실행한 것이 아니고 DB·락·`resync_copy_targets`를 대체했으므로 그 부분과 해시 바이트 일치는 검증하지 않는다. 사례 속 "업스트림"은 `file://` 임시 저장소다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 | 출처 |
|---|---|---|---|---|
| T-01 | R-01, R-03 | git 스킬, 저장 해시=설치 때 해시, 라이브러리 `SKILL.md`를 손으로 수정, 업스트림이 같은 폴더의 `SKILL.md`를 수정. 승인 없이 `update_skill` | `content_changed=true`, `pending_removals=[]`, 라이브러리 `SKILL.md`=업스트림 내용(내 수정 소실, 경고 없음) | 번역본 S1 |
| T-02 | R-05, R-10, R-11 | T-01에 더해 라이브러리에만 `notes.md`를 추가. 승인 없이 호출, 그 뒤 반환된 `removal_approval`로 다시 호출 | 1차: Held, `pending_removals=[{library, notes.md}]`, 파일·`SKILL.md` 그대로, 스테이징 폴더 잔존 없음, `update_status=update_available`. 2차: 적용, `notes.md` 소실, `SKILL.md`=업스트림 | 번역본 S2 |
| T-03 | R-01, R-04 | 업스트림이 모노레포의 다른 폴더(`skills/bar`)만 바꿈, 앱 재시작 없음, 라이브러리 `SKILL.md` 손 수정 | `content_changed=false`, 파일 불변(손 수정 보존), `source_revision`=새 head, `up_to_date` | 번역본 S3 |
| T-04 | R-02 | T-03과 같고, 손 수정 뒤 앱 또는 CLI를 한 번 시작함(reindex) | 저장 해시가 수정 포함 해시가 되어 `content_changed=true`, 업스트림이 안 바뀌었는데도 `SKILL.md`가 옛 업스트림 내용으로 교체됨. 라이브러리에만 있는 추가 파일이 있으면 대신 Held | 번역본 S4(앞 문장), 구현(Held 문장) |
| T-05 | R-09, R-12, R-13 | Held 후 토큰 T를 받음. (a) 새 버전에도 있는 `SKILL.md`를 수정 (b) 사라질 `outputs/` 안에 새 파일 (c) 새 최상위 파일 `another.txt` (d) 다른 리비전 문자열 | 토큰이 (a) 같음 (b) 같음 (c) 달라짐, 옛 토큰 호출은 Held (d) 달라짐. 최신 목록의 토큰이면 적용 | 번역본 S5, 테스트(`an_approval_does_not_carry_to_a_different_revision_or_list`) |
| T-06 | R-05~R-07 | 현재 폴더: 내용만 다른 `SKILL.md`·`scripts/run.py`, `templates/`(파일 둘), `.gitignore`, `.git/`, `scripts/__pycache__/m.pyc`, `stray.pyc`, `.DS_Store`, 새 버전에서 폴더가 된 파일 `thing`, 새 버전에서 파일이 된 폴더 `other/`, 심볼릭 링크 `link` | 목록 = `.git/`, `.gitignore`, `link`, `other/`, `templates/`, `thing`(정렬). `SKILL.md`·`scripts/run.py`는 없다. `.pyc`·`__pycache__`·`.DS_Store`는 제외 | 번역본 S6, 테스트(`removals.rs` 사례) |
| T-07 | R-08 | copy 모드 배포 사본에만 `agent-note.md`, 심볼릭 모드 배포 사본에는 아무 파일. (a) 내용 변경 있음 (b) 내용 변경 없음 | 둘 다 Held, `pending_removals=[{claude_code, agent-note.md}]`만(심볼릭 배포 사본 항목 없음) | 번역본 S7, 테스트(`a_metadata_only_update_still_checks_the_deployed_copies`) |
| T-08 | R-20 | 존재하지 않는 staged로 swap / 정상 staged로 swap | 앞: 오류, 라이브러리·`.backup-*` 변화 없음. 뒤: 새 내용, 부모 폴더에 `foo`만 남음 | 번역본 S8 |
| T-09 | R-31, R-33 | local 스킬에 `set-source`. (a) 손 수정 후 재시작 없이 원격 내용=설치 때 내용 (b) 손 수정 후 재시작 뒤 `--force` 없이 (c) 같은 상태에서 `--dry-run` (d) 같은 상태에서 라이브러리에만 있는 파일을 두고 `--force` | (a) 적용, `content_changed=false`, 파일 불변(손 수정·추가 보존) (b) 거절 "New source content differs…" (c) `content_changed=true`, 파일 변화 없음 (d) 적용, 라이브러리에만 있던 파일 소실(목록·승인 없음) | 번역본 S9 |
| T-10 | R-11, R-27 | local 스킬, 원본 폴더 안 바뀜, 라이브러리 `SKILL.md`를 수정. 재가져오기. 이어 라이브러리에만 `mine.txt` 추가 후 재가져오기, 그 토큰으로 다시 | 첫 호출: 적용, `SKILL.md`=원본 내용(수정 소실). 둘째: Held `[{library, mine.txt}]`. 셋째: 적용, `mine.txt` 소실 | 번역본 S10, 테스트(`a_stale_reimport_approval_does_not_authorize_a_grown_list`) |
| T-11 | R-26 | 목록 [git 변경 있음 A, git Held B, local C, well-known D, 없는 id E] | `refreshed=2`(A, C), `unchanged=0`, `held_back=[B 이름]`, `failed=["D 이름: Source type cannot be refreshed", "E: Skill not found"]` | 구현 |
| T-12 | R-16, R-36 | git 스킬, `ls-remote`는 성공하고 clone이 실패(또는 취소 플래그) | 오류가 호출자에게 돌아가고 `update_status`가 `updating`으로 남음, `last_check_error`는 이전 값 그대로, 파일 불변. 화면은 배지 없음 | 구현 |
| T-13 | R-15 | `ls-remote` 실패 | `update_status=error`, `last_check_error`=메시지, `remote_revision`은 이전 값, `git` kind 오류, 파일·`updating` 없음 | 구현 |
| T-14 | R-14 | `update_skill`을 `local` 스킬에, `well-known` 스킬에 | `invalid_input` "Only git-based skills can be updated", 상태 불변 | 구현 |
| T-15 | R-23 | 스테이징 성공, swap 성공, 재동기화가 오류 | 호출은 `io` 오류, 라이브러리는 새 내용, `update_status=error`(`remote_revision`=새 head), 메타데이터 파일 안 다시 쓰임 | 구현 |
| T-16 | R-27 | local 스킬 `source_ref`=없는 경로 | `update_status=source_missing`, `last_check_error="Original source path no longer exists"`, `not_found` 오류 | 구현 |
| T-17 | R-28 | relink: `source_path`가 없는 경로 / `SKILL.md` 없는 폴더 / git 스킬 | 각각 `not_found` "Selected source path does not exist" / `invalid_input` "Selected source path is not a valid skill directory" / `invalid_input` "Only local skills can relink source paths". 상태 불변 | 구현 |
| T-18 | R-28, R-11 | relink가 Held를 돌려준 뒤 같은 `source_path`로 승인, 다른 `source_path`로 승인 | 같은 경로: 적용(`source_ref`=새 경로, `local_only`). 다른 경로: 토큰 불일치로 Held | 구현 |
| T-19 | R-29 | local 스킬 detach | `source_ref=NULL`, `update_status=local_only`, 파일·`content_hash` 불변, `updating` 없음 | 구현 |
| T-20 | R-30 | set-source: `--subpath ""`(루트에 `SKILL.md` 없음) / 없는 subpath / `../x` / `SKILL.md` 없는 폴더 / `--subpath` 없고 URL이 트리 URL | `invalid_input` "Repository root is not a skill directory (no SKILL.md); pass --subpath" / `not_found` / `invalid_input` "resolves outside the repository" / `invalid_input` "is not a skill directory (no SKILL.md)" / URL의 branch·subpath 사용. 모두 상태 불변 | 구현, 테스트 사례 이름(`repoint_*`) |
| T-21 | R-32 | set-source가 락을 기다리는 동안 다른 연산이 그 스킬의 `content_hash`를 바꿈 / 스킬이 삭제됨 | `invalid_input` "Skill changed while fetching the source; re-run the command" / `not_found` "Skill was removed while fetching the source". 상태 불변 | 구현 |
| T-22 | R-33, R-34 | set-source 성공(내용 같음) | `source_type=git`, `source_ref`=입력 URL, `source_ref_resolved`=clone URL, `source_subpath`=해석값, 두 리비전=head, `update_status=up_to_date`, `id`·태그·배포 기록 유지 | 구현 |
| T-23 | R-37 | CLI `skills update --all`: git Held 1, local 원본 불변 1, well-known 1, git 변경 1 | 배열 4개: Held는 `refreshed:false`+`held_back_removals:["library: <path>"]`, local은 `refreshed:true`, well-known은 `error:"source type 'well-known' cannot be refreshed"`, 변경 git은 `refreshed:true`. 종료 코드 0 | 구현 |
| T-24 | R-40 | 앱에서 Update → Held → 확인 | 대화상자에 경로 칩 전체, "Update anyway"를 누르면 같은 `skillId`와 저장한 `removal_approval`로 `update_skill`을 다시 부름 | 구현 |
| T-25 | R-41 | T-24에서 확인을 누르는 사이 업스트림에 새 커밋이 생김 | 두 번째 호출이 다른 head로 Held를 돌려주지만 대화상자 상태가 곧 비워져 화면에는 아무것도 안 뜬다(추론, 앱 미실행). 파일 불변 | 구현(추론) |
| T-26 | R-42 | `auto_update_apply=on`, 업스트림 변경, 라이브러리에만 있는 파일 없음, 사용자가 `SKILL.md`를 수정해 둠(재시작 전/후 무관하게 업스트림 폴더가 바뀜) | 적용된다(`refreshed`로 센다), 수정은 소실. 라이브러리에만 있는 파일이 있었다면 `held_back`에 이름이 들어가고 적용 안 됨 | 구현 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]

| R-ID / T-ID | 근거 (repo@7a22192 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-09 `skills.rs:2157-2160`(해시·`content_changed`), `:2107-2110`(스냅샷 읽기), `core/content_hash.rs:7-16, 80-168`(범위) | 직접 읽음. 비교 대상이 `skill.content_hash`(스냅샷)와 `hash_directory(&skill_dir)`(체크아웃 폴더)임을 확인. 번역본 S1·S3으로 판정 규칙 확인 |
| R-02 | C-15: `app_state.rs:54-59`(GUI·CLI 모두 `initialize_store_inner`), `:176-180`(메타데이터가 있으면 reindex), `sync_metadata.rs:155-160, 232-261`(`new_hash`가 `content_hash`로 들어감); 다른 호출처 `commands/git_backup.rs:1118`. 쓰는 쪽 setter: metadata C-03, C-04 | 직접 읽음. `content_hash`를 쓰는 곳을 `grep 'content_hash = '`로 모아 setter 둘(`skill_store.rs:366, 414`), `upsert_skill`(reindex·repoint) 외에 없음을 확인. 번역본 S4는 reindex를 "디스크 해시로 다시 쓰기"로 대체했고 실제 reindex를 돌리지 않았다 |
| R-03 | C-09 `:2167-2181`(스테이징), `:2210-2237`(swap·쓰기), C-05; `commands/skills.rs`에서 `merge::`·`conflict`·`three_way`·`patch` 검색 결과 없음 | 직접 읽음, `grep` |
| R-04 | C-09 `:2238-2253`, `:2157-2181`(`install_result` 없음 → `staged=None`) | 직접 읽음 |
| R-05 | C-03 `core/removals.rs:31-33, 47-148`, C-02 | 직접 읽음, 번역본 S6. 폴더 롤업·종류 비교·오류 정책은 파일 머리 주석과 함수 주석이 같은 설명을 한다 |
| R-06 | C-03(제외 이름 `is_regenerable`만), `core/content_hash.rs:7-16`(무시 이름이 더 많음), `skills/manage-skills/SKILL.md:147`("a file the user edited that the new version also ships is reported as surviving … overwrites their edits silently") | 직접 읽음. SKILL.md의 문서 서술과 구현이 일치한다 |
| R-07 | C-09 `:2163-2166`(주석: "Stage first, then compare … drops `.git` and every symlink"), 설치 C-18 `copy_skill_dir`(`installer.rs:274-299`) | 직접 읽음, 번역본 S6(`.git/`, `link`) |
| R-08 | C-02 `:110-127`; 테스트 `a_metadata_only_update_still_checks_the_deployed_copies`(`skills.rs:3677`), `symlink_deployments_are_not_reported`(`:3713`) 본문 읽음 | 직접 읽음, 번역본 S7. 테스트는 읽기만(실행 아님) |
| R-09 | C-02 `:131-146`; 테스트 `an_approval_does_not_carry_to_a_different_revision_or_list`(`:3745`) 본문 읽음; `:2192`(git), `:2602`(`"reimport"`), `:1925`(relink) | 직접 읽음, 번역본 S5. 스킬 id가 입력이 아님은 함수 시그니처 `(revision, pending)`에서 |
| R-10 | C-09 `:2192-2208`, C-13 `:2602-2611`, C-10 `:1924-1936` | 직접 읽음 |
| R-11 | C-09 `:2193-2208`(주석 포함), C-13 `:2603-2611`, C-10 `:1926-1936`(주석: `source_missing` 보존), C-04 | 직접 읽음, 번역본 S2 |
| R-12 | C-07 `:1768-1780`, C-09 시작부(`:2107-2148`)가 매 호출마다 실행됨 | 직접 읽음 |
| R-13 | C-09 `:2183-2191`(주석이 (2), (3)을 인정), `:2236`(`resync_copy_targets`가 swap·DB 쓰기 뒤), `:2210-2236` | 직접 읽음. (4)의 창 길이는 순서에서 도출한 추론 |
| R-14 | C-09 `:2107-2119` | 직접 읽음 |
| R-15 | C-09 `:2120-2134` | 직접 읽음 |
| R-16 | C-09 `:2136-2148`, C-07 `:1764-1766`; `cancel_install`을 부르는 곳: `grep cancelInstall\|cancel_install`이 `src/lib/tauri.ts:305`, `InstallSkills.tsx:470`(설치 키)뿐; `"updating"`을 쓰는 곳: `grep '"updating"'`이 `skills.rs:1904, 2137, 2451, 2579`(+ TTL 판정 `:2950`, i18n) | 직접 읽음, `grep`. clone 오류의 `?`가 클로저 밖에 있음을 확인(`:2148` 다음 줄에서 클로저가 시작) |
| R-17 | C-09 `:2149-2160`, C-27, 설치 R-05(`resolve_skill_dir`); 원본 diff R-19(같은 경주를 git CLI로 확인) | 직접 읽음 |
| R-18 | C-09 `:2161`, C-24; 락 오류 변환 `AppError::db` | 직접 읽음 |
| R-19 | C-09 `:2167-2181`, 설치 C-17 | 직접 읽음 |
| R-20 | C-05 `skills.rs:3198-3222`, `:3486-3493`; 번역본 S8 | 직접 읽음, 번역본으로 rename 순서·복구 확인(로컬 파일시스템) |
| R-21 | C-09 `:2210-2253`, metadata C-03, C-04(`skill_store.rs:277-301, 352-381`) | 직접 읽음. `update_skill_source_metadata`가 `updated_at`을 쓰므로 "내용 같음"에서도 `updated_at`이 바뀐다 |
| R-22 | C-06 `skills.rs:3224-3275`, C-28 `scenario_service.rs:275-321`(머리 주석 포함) | 직접 읽음. `is_target_current`·`sync_skill` 내부는 읽지 않음 |
| R-23 | C-09 `:2258-2281`, `:2149-2255`(클로저) | 직접 읽음. 자체 복구는 R-01과 `:2216-2235`의 두 쓰기 순서에서 추론 |
| R-24 | C-09 `:2258-2271` | 직접 읽음 |
| R-25 | C-25, C-07 `:1777`, C-08 `:1825, :1845`; CLI `run_update`(C-17)에 로그 호출 없음; `set_git_source_internal`·relink·detach 본문에 `AuditDraft`·`log_` 호출 없음; `skill_auto_updater.rs:200-219` | 직접 읽음 |
| R-26 | C-08 `skills.rs:1812-1857` | 직접 읽음 |
| R-27 | C-13 `:2545-2643`, C-14 | 직접 읽음, 번역본 S10 |
| R-28 | C-10 `:1868-1974`, 설치 C-14 | 직접 읽음 |
| R-29 | C-10 `:1976-2018` | 직접 읽음 |
| R-30 | C-12 `:2360-2410`, C-11 `:2304-2344`; 테스트 사례 이름 `repoint_accepts_a_valid_subpath`, `repoint_accepts_repo_root_when_it_is_a_skill`, `repoint_rejects_repo_root_without_skill_md`, `repoint_rejects_missing_subpath_instead_of_falling_back`, `repoint_rejects_subpath_that_is_not_a_skill_dir`, `repoint_rejects_absolute_subpath`, `repoint_rejects_parent_traversal_subpath`, `repoint_rejects_symlink_escaping_the_checkout`(`skills.rs:4394-4485`) | 직접 읽음. 테스트는 이름만 |
| R-31 | C-12 `:2415-2429` | 직접 읽음, 번역본 S9 |
| R-32 | C-12 `:2431-2448` | 직접 읽음 |
| R-33 | C-12 `:2450-2491`, `:2297-2300`(`SetSourceResult` 주석) | 직접 읽음, 번역본 S9 |
| R-34 | C-12 `:2405-2409`(주석), `:2510-2536` | 직접 읽음 |
| R-35 | C-24, C-09, `delete_managed_skills_by_ids`(`skills.rs:750-798`, 락 안에서 폴더와 행 삭제) | 직접 읽음. 경주 결과는 추론(실행 안 함) |
| R-36 | R-16 근거 + `skills.rs:2950`(`should_skip_update_check`), `MySkills.tsx:1177-1197`(`statusBadge`), `:1647-1657`, `:1677-1685`, `:1936-1947`(알약·메뉴) | 직접 읽음, `grep` |
| R-37 | C-17, C-16 | 직접 읽음 |
| R-38 | C-18, `skills-manager-cli.rs:3123-3161`(`error_envelope`), `grep -rn 'set-source\|set_git_source' src/`에 호출 없음 | 직접 읽음, `grep` |
| R-39 | C-19, C-20, C-21; `MySkills.tsx:1148-1151`(`availableUpdateCount`), `:1262-1281`(상단 버튼), 알약·메뉴·Relink/Detach 위치 `:1647-1657`, `:1677-1685`, `:1730-1745`, `:1936-1947`, `:1979-1995`, `:2021-2023` | 직접 읽음 |
| R-40 | C-20 `:805-813, :888-962`, C-21 `:2065-2092`, C-22, `src/i18n/en.json:390-392`(`removalTitle`, `removalMessage`, `removalConfirm`), `:461`(`batchHeldBack`) | 직접 읽음 |
| R-41 | C-21 `:2080-2091`, C-22 `:50-58` | 코드 순서 도출. 앱 미실행이라 추론 |
| R-42 | C-23, `skill_auto_updater.rs:200-219`, `AppContext.tsx:361-399` | 직접 읽음. 타이머·옵트인은 읽지 않음(범위 밖) |
| T-01~T-10 | `artifacts/skills-manager/skill-update-apply-demos/update-apply-decisions.py`, `update-apply-decisions.out.2026-10-24.txt` | 번역본 실행. 시나리오 S1~S10이 T-01~T-10에 일대일 대응 |
| T-11~T-23 | 해당 R-ID의 근거 | 구현에서 도출. 실행 안 함 |
| T-24~T-26 | 해당 R-ID의 근거 | 구현에서 도출(T-25는 추론) |

**문서와 구현의 차이**
- `UpdateSkillResult.content_changed`의 주석(`skills.rs:29-30`, `tauri.ts:321`): "False when a monorepo commit didn't touch this skill's subdirectory." 구현은 저장 해시 대 원격 폴더 해시 비교이고(R-01), 저장 해시가 재시작으로 디스크 해시가 되면 폴더가 안 바뀌어도 true가 된다(R-02).
- `SetSourceResult.content_changed`의 주석(`skills.rs:2295-2300`)과 `skills/manage-skills/SKILL.md:238`: "손으로 고친 것은 차이로 안 잡히고 남는다 / 기록된 해시와 비교하지 디스크 해시와 비교하지 않는다". 프로세스 시작 때 reindex가 기록된 해시를 디스크 해시로 다시 쓰기 전까지만 참이다(R-02, T-09).
- `update_git_skill_internal` 주석(`skills.rs:2098-2099`): "Unattended callers pass None and simply do not update". 구현은 "사라질 파일이 있을 때만" 적용을 미룬다. 없으면 자동으로 적용된다(R-42).
- `skills/manage-skills/SKILL.md:129, :346`("Re-fetch all eligible skills", "refreshed: true vs already up-to-date"): local·import의 `refreshed`는 사라질 파일이 없으면 원본이 그대로여도 true다(R-37). git은 `content_changed`다.
- `skills/manage-skills/SKILL.md:147`(같은 경로 파일의 수정은 조용히 덮임)와 `:240-246`(`--force`는 확인 없음)은 구현과 일치한다(R-06, R-33).
- `ConfirmDialog`의 "nothing has changed yet"(`en.json:391`)는 Held의 파일 불변과 맞는다. 다만 안내문이 "내 파일이면 폴더 밖으로 옮겨라"이고 같은 경로 파일의 수정은 이 대화상자가 다루지 않는다(R-06).
- 지도·metadata 문서와의 차이: 아래 2.3의 "선행 스펙과의 관계"에 둔다.

### 2.2 코드 읽는 순서 [선택]

1. `commands/skills.rs:26-188`(결과 DTO, 목록·토큰 함수, 스테이징 가드) → `core/removals.rs`(목록 규칙 전체).
2. `update_git_skill_internal`(`:2090-2282`)을 위에서 아래로: 검증 → head 조회 → `updating` → clone → 클로저(해시, 락, 스테이징, 목록, Held, swap, 쓰기).
3. 같은 뼈대의 변형: `reimport_local_skill_internal`(`:2540-2643`), `relink_local_skill_source`(`:1868-1974`). 뼈대가 다른 것: `set_git_source_internal`(`:2346-2538`).
4. `swap_skill_directory`·`resync_copy_targets`(`:3189-3275`), `batch_update_skills`(`:1799-1866`).
5. 저장 해시가 어떻게 되는지: `app_state.rs:176-180` → `sync_metadata.rs:162-270`.
6. 입구: `bin/skills-manager-cli.rs:1773-1843`·`:968-990`, `src/views/MySkills.tsx:773-976`·`:2065-2092`, `components/ConfirmDialog.tsx`.

원본의 전략: (1) "스테이징 사본에 대고 비교하고, 그 사본을 그대로 swap"해서 확인한 것과 설치되는 것이 같게 한다. (2) 목록은 경로만 비교해 "소유자 판별 없이 사라질 것"을 보여 준다(`removals.rs` 머리 주석). (3) 승인은 목록·head에 묶어 대화상자가 열려 있는 동안 바뀐 것을 다시 묻는다. (4) 확인 없이 도는 호출자(일괄·CLI·자동)는 사라질 파일이 있으면 그냥 적용하지 않는다.

### 2.3 비교·재사용 출처 [선택]

- 같은 기능을 다른 레포에서 스펙으로 만든 것은 없다. 코드를 복사해 재사용하지 않았다(라이선스 MIT, overview 1절).
- 번역본(`update-apply-decisions.py`)이 옮긴 코드와 줄 범위: `content_hash.rs:7-16, 80-168`, `installer.rs:274-299`, `removals.rs:24-148`, `skills.rs:93-146, 2157-2253, 2415-2471, 2584-2615, 3189-3222`. 대체한 것: SQLite 행(dict), `RepoLock`, `resync_copy_targets`(호출 안 함), 원격 clone(로컬 `git clone --depth 1 file://…`). 정렬은 경로 성분 튜플이라 ASCII 이름에서만 Rust `Path::cmp`와 같다. 이 번역본은 "스펙의 판단 규칙이 구현자가 읽은 대로 동작하는지"를 보이려는 것이고 원본 실행이 아니다.
- 선행 스펙과의 관계(지도 보정용 관찰, 선행 스펙은 고치지 않았다):
  - skill-source-metadata R-08은 갱신·set-source·reimport가 쓰는 값을 적지만 relink와 detach(둘 다 `update_skill_after_reinstall`로 `source_ref`를 바꾸고 `local_only`로 끝냄, 이 문서 R-28, R-29)는 적지 않았다. 모순은 아니고 누락이다.
  - metadata R-12는 reindex가 `content_hash`를 디스크 해시로 바꾼다고 쓴다. 이 문서 R-02는 그 결과가 "갱신이 비교하는 기준이 수정 포함 해시가 된다"는 점을 더한다. 같은 사실을 변경 확인 R-08(local·import는 저장 해시 대 원본 해시)도 쓰므로, 재시작 뒤 손 수정한 local 스킬의 라이브러리 사본이 원본과 달라져 `update_available`로 보이는 쪽도 같은 원인이다(변경 확인 스펙에 명시되지 않았고 이 문서가 확인한 범위는 갱신 쪽 비교뿐이다).
  - metadata `update_status` 표의 `update_available` "삭제 확인에서 멈춘 갱신"은 git 갱신 경로(R-11)만 맞고, 재가져오기·relink의 Held는 이전 상태를 복원한다.

## 적용 메모 [선택]
<!-- 원본과 다르게 할 점(후보). 원본의 위험이나 미결정을 해소한 것이 아니다. -->
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-01, R-02, R-06 | `my-skills`처럼 남의 스킬을 사본에 고쳐 쓰는 경우를 위해 "로컬 수정 있음"을 감지한다. 후보: 설치·갱신 때의 해시를 reindex가 덮어쓰지 않는 별도 열(예: 설치 기준 해시)에 두고, 갱신 직전에 디스크 해시가 그 값과 다르면 파일 단위 목록(수정된 파일 포함)으로 보류 | 원본은 같은 경로의 수정을 조용히 덮고(R-06), 재시작 뒤에는 수정 여부를 저장 해시로 알 수 없다(R-02) | `skills` 스키마 열 추가, `PendingRemoval`에 `modified` 종류, 토큰에 변경 파일 해시 포함, 일괄·자동 호출은 같은 보류 규칙. 정한 적 없음 — 필요하면 사용자 결정 |
| R-03 | 3-way 병합(설치 때 기준 사본 ↔ 내 사본 ↔ 새 원본) 또는 최소한 교체 전 옛 폴더 보존(`.backup` 유지) | 원본은 병합·백업이 없고 swap 뒤 옛 폴더를 지운다(R-20) | 기준 사본 저장 위치·크기·수명이 필요하다. 후보일 뿐 정한 적 없음 |
| R-13 | 토큰에 목록의 폴더 줄 안 파일과 수정 파일의 해시를 포함해 승인 뒤 변경을 막는다 | 원본은 목록 밖 변경과 `outputs/` 안 새 파일을 못 잡는다(R-13) | 토큰 계산 변경, 호출자 호환 |
| R-16, R-36 | clone 실패·취소 때 `updating`을 이전 상태로 되돌리거나 `error`로 기록한다 | 원본은 `updating`이 남고 화면이 배지 없이 보인다 | R-16 후 상태 변경, T-12 대체 |
| R-33 | set-source `--force`에도 사라질 파일 목록을 보여 주고 확인한다 | 원본은 `--force`에 확인이 없다(R-33) | CLI 인자·출력 확장 |
| R-41 | 다시 Held가 오면 대화상자를 유지하고 새 목록을 보인다 | 원본은 대화상자가 곧바로 지워진다(R-41, 추론) | `ConfirmDialog` 호출 순서 변경, T-25 대체 |
