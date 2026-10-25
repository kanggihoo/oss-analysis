---
sha: "7a2219219287f4ef4c543fc169ebcc5b0bff085c"
created: 2026-10-24
updated: 2026-10-24
sources:
  - src-tauri/src/commands/skills.rs
  - src-tauri/src/core/git_fetcher.rs
  - src-tauri/src/core/skill_store.rs
  - src-tauri/src/core/content_hash.rs
  - src-tauri/src/core/installer.rs
  - src-tauri/src/core/repo_lock.rs
  - src-tauri/src/core/sync_metadata.rs
  - src-tauri/src/core/app_state.rs
  - src-tauri/src/core/skill_auto_updater.rs
  - src-tauri/src/core/well_known.rs
  - src-tauri/src/core/error.rs
  - src-tauri/src/lib.rs
  - src-tauri/src/bin/skills-manager-cli.rs
  - src/context/AppContext.tsx
  - src/views/MySkills.tsx
  - src/components/SkillDetailPanel.tsx
  - README.md
  - skills/manage-skills/SKILL.md
depends:
  - ../capabilities/skill-source-metadata.md
status: ready
reimplementation: 미실행
---

# 스킬 원본 변경 확인 (update check)

> 중앙 라이브러리의 스킬 하나(또는 전부)와 `force` 플래그를 받아, 스킬마다 "원본이 바뀌었나"를 출처 종류별 규칙으로 판정해 `update_status`·`remote_revision`·`last_checked_at`·`last_check_error` 컬럼에 기록하고, 앱·트레이·스케줄러·CLI가 그 판정을 부르는 입구를 제공한다.

<!--
용어 (이 문서 안에서만)
- 사전 조회(prefetch): 원격의 현재 head(커밋 id)를 저장소 락 밖에서 미리 구하는 단계. 결과 타입 `PrefetchedRemote`.
- 기록 단계: 락을 잡은 채 사전 조회 결과(또는 로컬 디스크)로 판정해 컬럼을 쓰는 단계. 함수 `check_skill_update_internal_with_remote`.
- 하위 트리 비교: 모노레포의 하위 폴더 스킬이 자기 폴더가 안 바뀌었으면 repo head가 움직여도 최신으로 보는 규칙(#561).
- 컬럼의 일반 의미, `source_type` 값 집합, 설치가 쓰는 초기값은 선행 스펙 `skill-source-metadata`가 소유한다. 이 문서는 "이 기능이 각 컬럼을 언제 읽고 어떤 값으로 쓰는가"만 쓴다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

대표: 앱 시작 때 전체 확인 (`check_all_skill_updates(force=false)`).

1. 호출자가 전체 확인을 시작한다. 스킬 목록을 한 번 읽는다.
2. **Phase A (락 밖, 네트워크)**: `source_type`이 `git`·`skillssh`이고 TTL로 건너뛰지 않는 스킬만 골라 `(clone_url, branch)`로 묶는다. 같은 원격은 한 번만, 최대 8개를 동시에 조회한다. 원격마다 head 커밋 id를 구하고, 하위 폴더 스킬이 있으면 그 폴더가 안 바뀐 `(옛 revision, 하위 폴더)` 쌍도 구한다. 실패한 원격은 오류 값으로 저장하고 계속 간다.
3. **Phase B (스킬마다 락, 네트워크 없음)**: 모든 스킬(출처 불문)을 차례로, 락을 즉시 시도해 잡고 기록 단계를 부른다. 락을 못 잡은 스킬은 건너뛰고 실패 목록에 넣는다.
4. 기록 단계가 스킬의 출처 종류로 갈라진다: git 계열은 사전 조회 결과와 `source_revision`을 비교하고, `local`/`import`는 원본 폴더를 해시해 저장된 `content_hash`와 비교하며, `well-known`은 아무것도 하지 않고, 그 밖은 `unknown`을 쓴다. (R-01~R-11)
5. 실패가 하나도 없으면 `()`를 돌려주고, 있으면 `"Failed to check N skill(s): <id>: <message>; ..."` 하나의 오류를 돌려준다. 호출자는 목록을 다시 읽어 화면에 반영한다.

한 스킬 확인(`check_skill_update`)은 같은 흐름을 한 스킬에 대해 순서만 바꿔 한다: 사전 조회(락 밖) → 락(최대 20초 대기) → 기록 단계 → 갱신된 스킬 반환.

### 1.2 범위·통합 지점

- 제공: 스킬별 원본 변경 판정과 그 기록. 단일 확인, 전체 확인, 원격 중복 제거·동시 조회, TTL·`force` 규칙, 모노레포 하위 폴더 판정, `local`/`import` 원본 폴더 비교, 앱 시작·버튼·트레이·스케줄러·CLI `skills check`의 호출 계약.
- 제외:
  - 변경의 실제 적용(update, reimport, relink): 다른 스펙. 이 기능은 `update_available`로 표시만 한다.
  - 파일 단위 diff(`get_skill_source_diff`): 별도 스펙.
  - 스케줄러 `skill_auto_updater.rs`의 타이머·간격 설정·옵트인 적용: 별도 스펙. 이 문서는 스케줄러가 확인을 부르는 입구(R-25)만 적는다.
  - `well-known` 출처의 변경 확인: 원본이 하지 않는다(R-10). 만드는 것은 적용 범위 밖이다.
- 외부 의존·선행 계약:
  - 선행 스펙 `skill-source-metadata`: 컬럼의 일반 의미와 `source_type` 값. 이 기능이 분기하는 값은 `git`, `skillssh`, `local`, `import`, `well-known`, 그 밖.
  - 저장소 락(`RepoLock`): 비대기 획득은 이미 잡혀 있으면 즉시 `skills repository is busy: <작업명>` 오류, foreground 획득은 최대 20초까지 50ms 간격으로 재시도한 뒤 같은 오류.
  - 설정 저장소: `update_check_ttl_minutes`(R-12), `proxy_url`(비어 있으면 없음).
  - 네트워크: `git` 실행 파일(`ls-remote`, `fetch`)과 libgit2 폴백. 시계: UTC 밀리초.
  - 파일시스템: `local`/`import`의 원본 경로(폴더 또는 `.zip`/`.skill` 압축 파일)와 라이브러리 복사본.
  - 설치·재설치·update가 쓰는 초기값. 읽기만 한다(예: 설치 직후 git 스킬은 `up_to_date`, `last_checked_at`=설치 시각이라 TTL 안에서는 확인이 건너뛰어진다).
- 소유 상태·부작용: 한 스킬 행의 `update_status`, `remote_revision`, `last_checked_at`, `last_check_error`. 예외적으로 `source_revision`(하위 폴더 동일 시 전진, R-14)과 `source_ref_resolved`·`source_subpath`·`source_branch`(해석값 정규화, R-05)와 그때 `updated_at`을 쓴다. 임시 폴더: 하위 트리 비교의 `skills-manager-subtree-*`는 만들고 지운다. libgit2 폴백이 만드는 `skills-manager-remote-*` 빈 bare 저장소는 지우지 않는다(코드에 삭제 없음, R-16). 사전 조회가 쓰는 메모리 값은 호출 하나의 수명이다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `check_skill_update` (Tauri 명령) | `skill_id: string`, `force?: bool`(기본 false) → 스킬 DTO 또는 오류 | 한 스킬. 사전 조회는 락 밖, 기록은 foreground 락 안(R-19). 오류는 `{kind, message}`. |
| `check_all_skill_updates` (Tauri 명령) | `force?: bool`(기본 false) → `()` 또는 오류 하나 | 전체. 스킬별 결과는 반환하지 않고 DB에만 남는다(R-17, R-18). |
| `prefetch_skill_remote(store, skill_id, force, proxy)` | → `PrefetchedRemote?` | 락 없이 부른다. 네트워크를 쓴다(R-15). |
| `check_skill_update_internal_with_remote(store, skill_id, force, prefetched?)` | → 스킬 DTO 또는 오류 | 기록 단계. **네트워크를 쓰지 않는다**(`local`/`import`는 디스크를 읽는다). 호출자가 락을 쥔 채 부르는 것이 전제. |
| `check_skill_update_internal(store, skill_id, force, proxy)` | → 스킬 DTO 또는 오류 | 사전 조회 + 기록 단계를 락 없이 잇는다. CLI가 쓴다. |
| `PrefetchedRemote` | `{key:(clone_url, branch?), result: head(string) 또는 오류 문자열, unchanged: set<(revision, subpath)>}` | `key`가 현재 소스와 맞을 때만 적용된다(R-03). |
| 스킬 DTO의 이 기능 필드 | `update_status: string`, `remote_revision?: string`, `last_checked_at?: int`(UTC ms), `last_check_error?: string`, `source_revision?: string` | 필드 전체 목록은 선행 스펙·라이브러리 관리 스펙 소유. |
| `update_status` 값 (이 기능이 쓰는 것) | `up_to_date`, `update_available`, `unknown`, `error`, `source_missing`, `local_only` | `updating`은 update 흐름이 쓰고 이 기능은 읽기만 한다(R-12). `checking`은 TTL 판정의 "불안정" 목록에만 있고 어디서도 쓰지 않는다. |
| 설정 `update_check_ttl_minutes` | 문자열 정수(분), 기본 60 | 없거나 정수로 못 읽으면 60. UI·CLI에 이 값을 바꾸는 전용 입구는 없다(범용 `set_settings`로만 쓸 수 있음). |
| CLI `skills check [REF] [--all] [--force]` | → JSON 배열 `{skill_id, name, source_type, update_status, last_check_error?, skipped}` | REF와 `--all`은 정확히 하나. 둘 다면 `pass either a ref or --all, not both`, 둘 다 없으면 `pass a skill ref or --all`. REF는 id·name·중앙 경로·폴더 이름 중 하나(CLI 공통 규칙). (R-26) |

호출 지점 (상세는 R-22~R-26):

| 호출자 | 입구 | `force` | 대상 | 락 |
|---|---|---|---|---|
| 앱 시작(UI) | `check_all_skill_updates` | false | 전체 | Phase B 스킬마다 비대기 |
| My Skills "전체 확인" | `check_all_skill_updates` | true | 전체 | 위와 같음 |
| My Skills 스킬 카드 확인 | `check_skill_update` | true | 한 스킬 | foreground(20초) |
| 트레이 "업데이트 확인" | prefetch → with_remote | true | 전체, 순차 | 스킬마다 비대기 |
| 주기 스케줄러 | prefetch → with_remote | true | 전체, 순차 | 스킬마다 비대기 |
| CLI `skills check` | `check_skill_update_internal` | `--force` 또는 `local`/`import` | 지정/전체, 순차 | 없음 |

### 1.4 행동 규칙과 남은 질문

**판정 (출처 종류 × 결과).** 아래 R-01~R-11은 기록 단계(`check_skill_update_internal_with_remote`, C-01)가 TTL 건너뜀(R-12) 뒤에 하는 일이다. 세부 쓰기 순서는 C-01.

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `git`/`skillssh` 스킬이고, 사전 조회가 현재 소스와 맞고(R-03) 성공(head). | `remote_revision`=head, `last_check_error`=NULL, `last_checked_at`=지금(UTC ms). `update_status`: `source_revision`==head → `up_to_date`. ≠head이고 하위 폴더 스킬이며 `(source_revision, source_subpath)`가 사전 조회의 `unchanged`에 있으면(R-14) → `source_revision`:=head로 쓰고 `up_to_date`. ≠head 그 밖 → `update_available`. `source_revision`이 NULL → `unknown`(`remote_revision`은 기록). 설치 내용(`content_hash`)은 비교하지 않는다. | 코드 확인 |
| R-02 | 위와 같되 사전 조회 결과가 오류 문자열. | `remote_revision`은 이전 값 유지, `update_status`=`error`, `last_check_error`=그 문자열, `last_checked_at`=지금. 호출자에게 `Err{kind:git, message}`를 돌려준다. | 코드 확인 |
| R-03 | `git`/`skillssh`인데 사전 조회가 없거나(`None`), 그 `key`가 현재 소스의 `(clone_url, branch)`와 다르다(subpath는 보지 않음). | 네 컬럼 모두 불변(`last_checked_at` 포함). 오류 없이 현재 스킬을 돌려준다("이번 라운드는 건너뜀"). 이 단계는 그 자리에서 원격을 조회하지 않는다. 재설치가 행을 유지한 채 소스를 바꾼 경우 옛 원격의 head가 새 소스에 기록되는 일을 막는 규칙이다. R-05의 정규화 쓰기는 그 전에 이미 일어났을 수 있다. | 코드 확인 |
| R-04 | git 소스 해석(`git_source_from_skill`, C-04). `source_ref_resolved`가 있으면 `clone_url`=그 값, `branch`·`subpath`=`source_branch`·`source_subpath`. 없고 `git`이면 `source_ref`를 `parse_git_source`로 파싱하되 branch·subpath는 컬럼 값이 있으면 컬럼 우선. 없고 `skillssh`이면 `source_ref`의 마지막 `/` 앞(`owner/repo`)으로 `https://github.com/owner/repo.git`을 만들고 branch·subpath는 컬럼. | 해석할 수 없으면(`source_ref` 없음, `skillssh`인데 `/` 없음) `invalid_input` 오류. 이 오류는 컬럼을 쓰지 않는다(상태 불변): 단일 확인은 `Err`, 전체 확인은 실패 목록에 `id: message`. | 코드 확인 |
| R-05 | R-04의 `(clone_url, subpath, branch)` 중 하나라도 저장된 `source_ref_resolved`·`source_subpath`·`source_branch`와 다르다(NULL과 값도 다름). | 사전 조회 적용 여부를 보기 전에 세 컬럼을 해석값으로 쓰고 `updated_at`=지금. `source_revision`은 같은 값으로 다시 쓴다. | 코드 확인 |
| R-06 | `local`/`import`, `source_ref`(원본 경로)가 있고 존재하며 해시 계산 성공. | `update_status`=`local_source_status`(R-08), `remote_revision`=NULL, `last_check_error`=NULL, `last_checked_at`=지금. | 코드 확인 |
| R-07 | `local`/`import`의 예외: `source_ref`가 NULL → `local_only`(오류 없음). 경로가 없음 → `source_missing`, `last_check_error`=`Original source path no longer exists`. 해시 계산 오류(지원 안 하는 압축 확장자, 읽기 실패, 압축 안에 skill 폴더가 여럿 등) → `error`, `last_check_error`=오류 문자열. | 모두 `remote_revision`=NULL, `last_checked_at`=지금. **`error`여도 호출은 성공(`Ok`)이고 오류를 돌려주지 않는다**(git 계열 R-02와 다르다). | 코드 확인 |
| R-08 | `local_source_status`: 저장된 `content_hash`와 원본의 지금 해시. | `content_hash` NULL → `local_only`. 같음 → `up_to_date`. 다르지만 R-09가 true → `up_to_date`. 그 밖 → `update_available`. | 코드 확인 |
| R-09 | "줄 끝만 다른가"(`differs_only_by_line_endings`): 원본과 라이브러리 복사본의 지금 상태를 CRLF→LF로 접어 해시한 값 비교. | 같으면 true. 접기는 NUL이 없고 UTF-8로 읽히는 파일의 `\r\n`만 바꾼다. `node_modules`·`.venv`·`venv` 폴더는 이 비교에서 뺀다(#502). 어느 한쪽이라도 읽기 오류·순회 불가·빈 폴더면 오류 → false(바이트 해시 판정 유지). 즉 이 비교는 `update_available`를 `up_to_date`로 낮출 수만 있다. | 코드 확인 |
| R-10 | `well-known` 스킬. | **어떤 컬럼도 쓰지 않는다**(`last_checked_at` 포함). 오류 없이 현재 스킬을 돌려준다. 설치가 `local_only`로 둔 상태가 그대로 남는다. 설치가 `source_revision`·`remote_revision`에 index digest를 기록할 수 있어도 확인은 읽지 않는다. 전체 확인의 Phase B에서도 락만 잡고 아무것도 안 한다. CLI는 `skipped:true`로 보고한다(R-26). 즉 변경 확인 대상이 아니다. | 코드 확인 |
| R-11 | 위에 없는 `source_type` 값. | `update_status`=`unknown`, `remote_revision`=NULL, `last_check_error`=NULL, `last_checked_at`=지금. `unknown`은 TTL의 "불안정" 상태라 다음 호출에도 건너뛰지 않는다. | 코드 확인 |

**건너뜀·강제.**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-12 | `should_skip_update_check`(C-03): `force`=true → 건너뛰지 않음. 아니면 TTL=`update_check_ttl_minutes`(정수 분, 없거나 못 읽으면 60). 상태가 "안정"(`unknown`·`checking`·`updating`·`error` 이외)이고 `last_checked_at`이 있고 지금−`last_checked_at` < TTL(ms)이면 건너뜀. | 건너뛴 스킬은 네트워크·디스크 비교 없이 현재 스킬을 그대로 돌려주고 컬럼은 불변. 출처 종류와 무관하게 적용된다(`local`/`import`/`well-known`도). `local_only`, `source_missing`, `update_available`, `up_to_date`는 안정 상태라 TTL 안에서는 다시 확인하지 않는다. `last_checked_at`이 NULL이거나 TTL ≤ 0이면 건너뛰지 않는다. | 코드 확인 |
| R-13 | 건너뜀 판정의 평가 지점과 오류. | 판정은 두 곳에서 따로 한다: 사전 조회 쪽(단일: 오류면 "건너뛰지 않음"으로 보고 조회, 전체: 오류면 로그만 남기고 조회 대상에 포함)과 기록 단계(오류면 그 스킬의 확인이 `Err`로 끝남). 실제로 쓸지는 기록 단계의 판정이 정한다. | 코드 확인 |
| R-14 | 하위 폴더 스킬: `source_subpath`가 비어 있지 않고 `source_revision`이 있으면 "설치한 폴더" `(source_revision, source_subpath)`를 사전 조회에 건다. 루트 스킬(`source_subpath` NULL·빈 값)은 걸지 않는다. | 루트 스킬은 저장소 head가 움직이면 항상 `update_available`. 하위 폴더 스킬은 그 폴더가 같으면 `up_to_date`가 되고 `source_revision`이 head로 전진한다(`updated_at`은 그대로). 이후 확인은 새 head 기준이라 다시 비교하지 않는다. `source_revision` 전진과 R-01의 상태 기록은 별개의 두 쓰기이고 한 트랜잭션이 아니다. | 코드 확인 |

**사전 조회·동시성.**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-15 | `prefetch_skill_remote`: 스킬을 못 읽거나 없음 / `source_type`이 `git`·`skillssh`가 아님 / 건너뜀(R-12, 오류는 "건너뛰지 않음") / git 소스 해석 불가(R-04). | 위 경우 `None`(그 뒤 기록 단계도 네트워크 없음). 아니면 그 스킬의 `(clone_url, branch)` 원격을 조회해(R-16) head와, 하위 폴더 스킬이면 `unchanged`(R-20)를 담은 `PrefetchedRemote`를 돌려준다. 락을 쥔 채 부르면 안 된다(#315). | 코드 확인 |
| R-16 | 원격 head 해석(`resolve_remote_revision`, C-08·C-09). 후보 ref 이름: `branch` 있음 → `refs/heads/<b>`, `refs/tags/<b>^{}`, `refs/tags/<b>`(이 순서). 없음 → `HEAD`. | 먼저 `git ls-remote <url> <후보들>`(proxy 있으면 `-c http.proxy=… -c https.proxy=…`). 출력에서 후보 순서대로 **정확한 ref 이름**이 같은 줄을 고른다(첫 줄을 쓰지 않음). 태그는 peeled 줄(`^{}`)의 커밋 id를 쓴다. git 실행 실패·종료 코드 비정상·일치 줄 없음 중 하나면 libgit2 익명 remote로 같은 후보를 다시 찾는다(자격 증명 콜백 설치, proxy 적용). 그래도 없으면 `Unable to resolve remote revision for <url>`. 앱이 거는 타임아웃은 없다. | 코드 확인 (ref 선택 전제는 R-21) |
| R-17 | `check_all_skill_updates` Phase A. | 대상은 `git`·`skillssh`이고 R-12로 건너뛰지 않으며(판정 오류면 포함) git 소스 해석이 되는 스킬. `RemoteKey(clone_url, branch)`로 묶고(문자열 그대로, 정규화 없음), 묶음마다 하위 폴더 스킬들의 `(source_revision, source_subpath)` 합집합을 `installed`로 건다. 원격당 **정확히 한 번** 해석하고, 동시에 최대 8개(`MAX_CHECK_CONCURRENCY`)를 work-stealing으로 돌린다. 원격의 실패는 `Err(message)`로 저장될 뿐 배치를 멈추지 않는다. 이 단계는 `RepoLock`을 쓰지 않는다. | 코드 확인 |
| R-18 | `check_all_skill_updates` Phase B와 결과. | **모든** 스킬을 `get_all_skills` 순서로, 스킬마다 `RepoLock::acquire`(비대기)를 잡고 기록 단계를 부른다. `git`·`skillssh` 스킬의 사전 조회는 지금 소스로 다시 만든 `RemoteKey`로 Phase A 결과에서 찾는다(없으면 `None`, R-03). 락 실패·기록 단계 `Err`(스킬이 그사이 삭제되어 not found 포함)는 `"<skill id>: <message>"`로 모으고 **계속** 진행한다. 끝나면 실패가 없으면 `Ok(())`, 있으면 `internal` 오류 `Failed to check N skill(s): a; b; …`. 성공한 스킬의 기록은 그대로 남는다. | 코드 확인 |
| R-19 | `check_skill_update`: 사전 조회(락 밖) → `RepoLock::acquire_foreground`(최대 20초 대기) → 기록 단계. | 락을 못 얻으면 `skills repository is busy: check skill update` 오류(kind database)이고 컬럼 불변. 그 외 결과는 R-01~R-11. 반환 값은 기록 뒤 DB에서 다시 읽은 스킬. | 코드 확인 |
| R-20 | 하위 트리 비교 `unchanged_subtrees`(C-10). 입력: 원격 url, head, `installed` 쌍 집합, proxy. | 후보 쌍은 `revision`≠head이고 `revision`·head가 40자리 16진수이고 `subpath`가 비어 있지 않은 것만. 후보가 없으면 빈 집합. 빈 bare 저장소에 `git fetch --no-tags --depth=1 --filter=blob:none <url> <정렬·중복 제거한 revision들+head>`를 한 번 한 뒤(앱의 git 감시 규칙: 300초 타임아웃), 쌍마다 `checkout_inputs`(subpath 트리 id, subpath 위 모든 디렉터리(루트 포함)의 `.gitattributes` 항목 id 또는 없음)가 revision과 head에서 같고 둘 다 존재하며 subpath가 디렉터리일 때만 "안 바뀜"이다. **어떤 실패든**(fetch 실패, 서버가 revision 하나라도 모름, 경로 없음 등) 그 호출의 결과는 빈 집합이고 기록 단계는 `update_available`로 폴백한다. 임시 저장소는 항상 지운다. | 코드 확인 |
| R-21 | R-16·R-20이 기대는 순수 git 동작(로컬 `file://` 저장소). | (a) `ls-remote`에 `refs/heads/<b>`·`refs/tags/<b>^{}`·`refs/tags/<b>`를 주면 같은 이름의 브랜치와 태그가 있어도 각 ref가 따로 출력되고, 주석 태그는 태그 객체 줄과 `^{}` 줄(커밋)이 따로 나온다. 없는 ref는 종료 코드 0에 빈 출력이다. 없는 경로는 종료 코드 128. (b) `--filter=blob:none --depth=1` fetch로 head와 옛 커밋의 트리 객체를 받아 `git rev-parse <rev>:<path>`로 하위 폴더 트리 id를 비교할 수 있다. 바뀐 폴더는 id가 달라지고 안 바뀐 형제 폴더는 같다. (c) 루트에 `.gitattributes`가 새로 생기면 하위 폴더 트리 id가 같아도 그 항목 id가 달라진다. (d) 모르는 revision이 하나 섞이면 fetch 전체가 종료 코드 128(`not our ref`)이다. (e) 서버가 filter를 허용하지 않으면 경고만 내고 성공한다. | 실행 확인 (git 2.50.1, `file://`만) |

**호출 지점.**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-22 | 앱 시작: 로딩이 끝나고 관리 스킬이 하나 이상이며 그중 `git`/`skillssh`가 하나 이상일 때. | 3초 뒤 한 번(진행 중 플래그로 중복 방지), `check_all_skill_updates(false)`. 이어서 목록을 다시 읽고, 설정 `auto_update_apply`가 `on`이면 `update_available`인 `git`/`skillssh`를 일괄 적용(범위 밖). 목록을 반영하고 `update_available`가 있으면 토스트로 알리며 `auto_update_last_run_at`을 지금으로 쓴다. `check_all_skill_updates`가 오류를 돌려주면(스킬 하나만 실패해도, R-18) 그 뒤 단계 전부(목록 재읽기·알림·자동 적용·`auto_update_last_run_at` 기록)를 건너뛰고 콘솔 로그만 남긴다(토스트 없음). `local`/`import`만 있는 라이브러리에서는 시작 확인이 아예 안 돈다. | 코드 확인 |
| R-23 | My Skills 버튼. | "전체 확인": `check_all_skill_updates(true)`, 성공 시 토스트, 실패 시 오류 토스트, 어느 쪽이든 끝에 목록을 다시 읽는다. 스킬 카드의 확인: `check_skill_update(id, true)`, 실패하면 오류 토스트, 어느 쪽이든 목록을 다시 읽는다. | 코드 확인 |
| R-24 | 트레이 "업데이트 확인". | 실행 중 플래그가 이미 서 있으면 무시한다. 모든 스킬 id를 차례로: 200ms 대기 → `prefetch_skill_remote(force=true)`(락 밖) → `RepoLock::acquire`(비대기) → 기록 단계(`force=true`). 락 실패·확인 실패는 로그만 남기고 다음 스킬로 간다(`local`/`import`/`well-known`도 같은 루프를 지난다). 끝나면 스케줄러의 라운드 완료 기록(`record_round_completion`)을 부른다. | 코드 확인 |
| R-25 | 주기 스케줄러의 입구(타이머·적용은 범위 밖). | 라운드마다 모든 스킬 id를 차례로: 200ms 대기 → `prefetch_skill_remote(force=true)` → `RepoLock::acquire`(비대기, 실패하면 그 스킬은 건너뛰고 실패로 센다) → 기록 단계(`force=true`). 결과 `update_status`가 `update_available`일 때만 다음 단계(적용)로 넘어간다. | 코드 확인 |
| R-26 | CLI `skills check`. | 대상은 REF 하나 또는 `--all`. `source_type`이 `git`·`skillssh`·`local`·`import`가 아닌 스킬은 확인하지 않고 `{update_status: 저장된 값, last_check_error: 저장된 값, skipped:true}`로 보고한다. 나머지는 스킬마다 순차로 `check_skill_update_internal`(원격 묶음·동시성·락 없음)을 부른다. `local`/`import`는 `--force` 없이도 `force`=true(TTL이 디스크 비교를 막지 않게). 스킬별 오류는 프로세스 실패가 아니라 그 스킬의 보고 항목(`update_status`=`error`, `last_check_error`=메시지, `skipped:false`)이다. 이 오류가 R-04처럼 DB에 쓰이지 않은 오류면 보고서만 `error`이고 DB 컬럼은 그대로다. | 코드 확인 |

**상태가 화면에서 읽히는 방법.**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-27 | My Skills 목록·상세·알림. | `update_available` → "Update" 배지·개수·알림 토스트, 그리고 `canRefresh`(`git`/`skillssh`, 또는 `local`/`import`이면서 `source_ref` 있음)일 때만 갱신 버튼. `source_missing`·`error` → 빨간 배지(이름만, 메시지 없음). `up_to_date`·`unknown`·`local_only`·그 밖은 배지 없음. `last_checked_at`·`last_check_error`는 화면에서 읽지 않는다(`error`의 이유는 확인 호출의 오류 토스트로만 보인다). `remote_revision`·`source_revision`은 상세 패널이 원본 문서·diff를 다시 읽는 키로만 쓴다. | 코드 확인 |
| R-28 | `last_check_error`·`Err` 메시지의 내용. | git 계열은 `resolve_remote_revision`의 `anyhow::Error::to_string()`(최상위 메시지만, 폴백 뒤라면 libgit2 쪽 오류)을 그대로 쓴다. 마스킹하지 않는다. `local`/`import`는 R-07의 고정 문구 또는 해시 오류 문자열. | 코드 확인 |
| R-29 | 앱·CLI를 시작할 때 메타데이터 reindex가 돈 뒤의 `local`/`import` 확인 | 저장된 `content_hash`는 reindex가 라이브러리 사본의 디스크 해시로 다시 쓴 값이다(`skill-source-metadata` R-12). 그래서 라이브러리 사본을 손으로 고친 `local`/`import` 스킬은 재시작 뒤 R-08에서 원본 폴더 해시와 달라 보여 `update_available`이 될 수 있다. 재시작 전에는 설치·갱신 때 기록한 해시가 기준이다 | 코드 확인(읽기만, 실행하지 않음) |

- 불변식:
  - 원격 조회(`ls-remote`, 하위 트리 `fetch`)는 항상 `RepoLock` 밖에서 하고, 기록 단계는 네트워크를 쓰지 않는다. 단 `local`/`import`의 원본 해시는 기록 단계에서(락을 쥔 채) 계산한다.
  - `last_checked_at`은 R-01(성공)·R-02·R-06·R-07·R-11처럼 컬럼을 기록한 경우에만 바뀐다. 건너뜀(R-12)·사전 조회 없음(R-03)·`well-known`(R-10)·해석 오류(R-04)에서는 바뀌지 않는다.
  - `update_available`를 `up_to_date`로 낮추는 규칙은 둘뿐이고(하위 트리 동일 R-14, 줄 끝만 다름 R-09) 둘 다 "확인하지 못하면 낮추지 않는다" 쪽이다.
  - 사전 조회 결과는 그 스킬의 지금 `(clone_url, branch)`와 같을 때만 쓰인다.
  - 전제: 이 기능은 설치·update가 `source_revision`을 "설치한 커밋 id"로 기록했다고 가정한다. `source_revision`이 NULL이면 git 계열 확인은 `unknown`에 머문다(R-01). 메타데이터 파일에는 revision 필드가 없어서, 이 DB에 행이 없던 스킬이 메타데이터 재구성(`reindex_from_metadata`, 앱 시작 때 실행)으로 들어오면 `source_revision`이 NULL이다(2.1 R-01). 이 값을 채우는 쪽은 설치·update다(이 기능이 아님).
- 미결정: 없음.
- 확인 한계:
  - 외부 원격(GitHub 등)의 실제 동작은 확인하지 않았다: `ls-remote`·`fetch --filter=blob:none`·SHA 지정 fetch를 서버가 허용하는지, 오래된 revision을 서버가 계속 가지고 있는지, 코드 주석의 "약 400KB(heygen-com/hyperframes)"는 미확인이다. R-21은 로컬 `file://` 저장소와 git 2.50.1에서만 확인했다.
  - 앱·`cargo test`는 실행하지 않았다. 원본 테스트는 사례 이름과 해당 본문만 읽었다(읽은 것은 실행 확인이 아니다).
  - `ls-remote`·libgit2 폴백에는 앱이 거는 타임아웃이 없다(코드 확인). git·OS 기본 타임아웃은 미확인이다.
  - 원격 오류 문자열의 구체 문구와 거기에 URL(`user:token@` 포함 가능)이 들어가는지는 git·libgit2 의존이며 미확인이다.
  - 앱과 CLI가 동시에 같은 DB를 쓸 때의 동작(CLI 확인은 락이 없다, R-26)은 확인하지 않았다.

### 1.5 필수 코드 참조

라이선스: MIT(`overview.md` 1절)라 인용을 허용한다. `content_hash.rs` 항목은 라이브러리 상태의 공유 계약(저장된 `content_hash`의 정의)이며, 이 기능은 "원본의 지금 해시 vs 저장된 `content_hash`"로만 쓴다. 해시 알고리즘이 바이트 단위로 같아야 저장된 값과 맞는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src-tauri/src/commands/skills.rs:2754-2885` `check_skill_update_internal_with_remote` | 기록 단계 전체: 건너뜀 → 출처별 분기, git의 정규화 쓰기·사전 조회 필터·상태 결정과 쓰기 순서, `local`/`import` 분기, `well-known` 무동작, 그 밖 `unknown`. | R-01~R-03, R-05~R-07, R-10, R-11, R-14 |
| C-02 | `src-tauri/src/commands/skills.rs:2887-2931` `local_source_status`, `differs_only_by_line_endings` | `local`/`import` 판정표와 줄 끝 비교(오류는 false). | R-08, R-09 |
| C-03 | `src-tauri/src/commands/skills.rs:2933-2958` `should_skip_update_check` | TTL 설정 읽기·기본 60·"안정 상태" 목록·밀리초 비교. | R-12 |
| C-04 | `src-tauri/src/commands/skills.rs:292-298`, `2960-3016` `GitSkillSource`, `git_source_from_skill`, `skill_ssh_id` | git 소스 해석 3분기와 오류. `locator_skill_id`(=`skillssh`의 마지막 `/` 뒤)는 확인에서 쓰지 않고 update 쪽이 쓴다. | R-04 |
| C-05 | `src-tauri/src/commands/skills.rs:1496-1594` `check_all_skill_updates` | Phase A 대상 선정·묶음, Phase B 순회·락·실패 집계. | R-17, R-18 |
| C-06 | `src-tauri/src/commands/skills.rs:1596-1663` `RemoteKey`, `PrefetchedRemote`, `installed_subtree`, `resolve_remote` | 원격 키(`clone_url`+`branch`, subpath 무시 비교), 사전 조회 값, 하위 폴더 쌍 만들기, "head 해석 → unchanged 계산" 순서. | R-03, R-14, R-15, R-17 |
| C-07 | `src-tauri/src/commands/skills.rs:1673-1746` `prefetch_skill_remote`, `MAX_CHECK_CONCURRENCY`, `resolve_remotes_concurrent`, `resolve_concurrent` | `None` 조건, 동시 8개 work-stealing, 원격당 1회, 실패는 값으로 저장. | R-15, R-17 |
| C-08 | `src-tauri/src/core/git_fetcher.rs:1187-1216` `resolve_remote_revision` | git CLI 우선 → libgit2 폴백 → 후보 순서 탐색 → 실패 문구. | R-16 |
| C-09 | `src-tauri/src/core/git_fetcher.rs:1643-1707` `candidate_ref_names`, `select_remote_revision`, `resolve_remote_revision_with_git` | 후보 ref 이름 3개와 정확한 이름 선택, `ls-remote` 인자. | R-16 |
| C-10 | `src-tauri/src/core/git_fetcher.rs:1236-1306` `unchanged_subtrees` | 후보 쌍 필터, 한 번의 blobless depth-1 fetch, `checkout_inputs` 비교, 실패 시 빈 집합, 임시 저장소 정리. | R-20 |
| C-11 | `src-tauri/src/core/skill_store.rs:277-330` `update_skill_source_metadata`, `update_skill_source_revision`, `update_skill_check_state` | 컬럼 쓰기 단위: 정규화는 5컬럼+`updated_at`, revision 전진은 `updated_at` 불변, check_state는 4컬럼+`last_checked_at`=지금(UTC ms). | R-01, R-02, R-05, R-14 |
| C-12 | `src-tauri/src/core/content_hash.rs:7-25` `IGNORED`, `is_ignored`, `DEPENDENCY_DIRS` | 해시에서 빼는 이름과 줄 끝 비교에서만 더 빼는 의존성 폴더. | R-08, R-09 |
| C-13 | `src-tauri/src/core/content_hash.rs:80-168` `walk_content_files`, `hash_entries`, `hash_directory` | 저장 해시(바이트 정확): 정렬된 파일의 상대 경로+내용+(unix) 실행 비트. | R-08 |
| C-14 | `src-tauri/src/core/content_hash.rs:185-218` `is_foldable_text`, `fold_crlf` | 접기 규칙. | R-09 |
| C-15 | `src-tauri/src/core/content_hash.rs:247-286` `hash_entries_eol_insensitive`, `hash_directory_eol_insensitive` | 길이 프레임 해시, 읽기 오류·빈 폴더는 오류, 의존성 폴더 제외. | R-09 |
| C-16 | `src-tauri/src/core/installer.rs:17-80` `PreparedSource` | 원본이 폴더가 아니면 `.zip`/`.skill`만 임시 폴더에 풀고, `SKILL.md`/`skill.md`가 든 폴더(깊이 4까지, 여럿이면 오류, 없으면 압축 루트)를 해시 대상으로 삼는다. | R-06, R-07, R-09 |
| C-17 | `src-tauri/src/core/installer.rs:132-144` `hash_local_source`, `hash_local_source_eol_insensitive` | 원본 해시 두 가지가 `PreparedSource`를 거친다. | R-06, R-09 |
| C-18 | `src-tauri/src/bin/skills-manager-cli.rs:1845-1898` `run_check` | CLI 분기: 건너뜀 대상, `local`/`import` 강제, 오류를 보고 항목으로. | R-26 |

### 1.6 수락 사례

출처: 사례별로 표기. "구현"=구현에서 도출, "테스트"=원본 테스트를 읽고 같은 사례를 도출(위치는 2.1, 실행하지 않음), "git 실행"=`artifacts/skills-manager/skill-update-check-demos/`의 순수 git 실행 관찰.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 | 출처 |
|---|---|---|---|---|
| T-01 | R-01 | `git` 스킬, `source_revision`=A, 사전 조회 head=B(≠A), 루트 스킬, `force`=true | `update_available`, `remote_revision`=B, `last_check_error`=NULL, `last_checked_at`≈지금 | 테스트 |
| T-02 | R-01 | 같은 상태에서 head=A | `up_to_date`, `remote_revision`=A | 구현 |
| T-03 | R-01 | `source_revision`=NULL, head=B | `unknown`, `remote_revision`=B | 구현 |
| T-04 | R-14, R-20 | 한 저장소의 루트 스킬, `skills/a`, `skills/b`가 모두 커밋 C1에서 설치됨. 새 커밋 C2가 `skills/a`만 수정. 세 스킬을 `force`=true로 확인 | `a`=`update_available`(`source_revision`=C1 유지), `b`=`up_to_date`이고 `source_revision`=`remote_revision`=C2, 루트=`update_available` | 테스트 |
| T-05 | R-14, R-20 | T-04 뒤 루트에 `.gitattributes`(`skills/b/** text eol=crlf`)만 추가한 커밋 C3, `b` 확인 | `b`=`update_available`, `b.source_revision`=C2 그대로 | 테스트, git 실행(트리 id 같고 `.gitattributes` 항목만 달라짐) |
| T-06 | R-20 | `b`의 `source_revision`이 서버에 없는 40자리 id, 확인 | `update_available`, `source_revision` 불변 | 테스트, git 실행(fetch 실패) |
| T-07 | R-20 | 같은 원격의 하위 폴더 스킬 `x`(옛 revision 서버에 있음)와 `y`(옛 revision 서버에 없음)를 전체 확인 | 한 번의 fetch가 실패하므로 `unchanged`가 비어, `x`의 폴더가 실제로 안 바뀌었어도 `x`·`y` 모두 `update_available`(구현 코드 기준; 원본 주석의 "그 쌍만 빠진다"와 다르다, 2.1) | 구현, git 실행(fetch 전체 실패) |
| T-08 | R-02 | 사전 조회 결과가 `Err("could not read from remote")` | 호출은 `Err`(git, 그 메시지), 저장: `error`, `last_check_error`=그 메시지, `remote_revision` 이전 값 | 테스트 |
| T-09 | R-03 | `git` 스킬, 사전 조회 `None`, `force`=false | 컬럼 불변, `last_checked_at`=NULL 유지, 성공 반환 | 테스트 |
| T-10 | R-03 | 사전 조회 key가 `old.git`, 스킬은 `new.git` | 폐기: `update_status`·`remote_revision`·`last_checked_at` 불변 | 테스트 |
| T-11 | R-12 | `up_to_date`, `last_checked_at`=30분 전, TTL 기본 60, `force`=false | 건너뜀(컬럼 불변, 네트워크 없음). `force`=true면 조회. 61분 전이면 조회. | 구현 |
| T-12 | R-12 | `update_status`=`error`(또는 `unknown`)이고 방금 확인됨, `force`=false | 건너뛰지 않고 다시 조회 | 구현 |
| T-13 | R-12 | 설정 `update_check_ttl_minutes`=`abc` / `0` | `abc`→60분 취급, `0`→절대 건너뛰지 않음 | 구현 |
| T-14 | R-06, R-08 | `local`, 원본 폴더의 해시 == 저장된 `content_hash` | `up_to_date`, `remote_revision`=NULL | 구현 |
| T-15 | R-08 | 원본 `SKILL.md` 본문이 바뀜 | `update_available` | 테스트 |
| T-16 | R-09 | 원본은 CRLF, 라이브러리 복사본은 LF, 내용 같음 | `up_to_date` | 테스트 |
| T-17 | R-09 | 원본에 `node_modules/pkg/index.js`만 추가됨 | `up_to_date` | 테스트 |
| T-18 | R-09 | 라이브러리 복사본 폴더가 사라지고 원본은 CRLF만 다름 | `update_available`(비교 오류 → false) | 테스트 |
| T-19 | R-07 | `local`, `source_ref`=NULL / 존재하지 않는 경로 / 지원 안 하는 확장자 파일 | `local_only` / `source_missing`+고정 문구 / `error`+오류 문자열. 세 경우 모두 호출은 `Ok`. | 구현 |
| T-20 | R-10 | `well-known` 스킬(`local_only`, `last_checked_at`=T0), `force`=true로 확인 | 컬럼 전부 불변, `last_checked_at`=T0 그대로 | 구현 |
| T-21 | R-11 | 알 수 없는 `source_type` | `unknown`, `last_checked_at`=지금 | 구현 |
| T-22 | R-04, R-05 | `git` 스킬, `source_ref`=`acme/skills`, `source_ref_resolved`=NULL | 해석 `https://github.com/acme/skills.git`. 기록 단계가 `source_ref_resolved`를 그 값으로 쓰고 `updated_at` 갱신 | 구현 |
| T-23 | R-04 | `skillssh`, `source_ref`=`vercel/skills/foo`, `source_ref_resolved`=NULL | 해석 `https://github.com/vercel/skills.git`, `subpath`·`branch`는 컬럼 값 | 구현 |
| T-24 | R-17 | 같은 `(clone_url, branch)`인 스킬 3개와 다른 원격 1개를 전체 확인 | 원격 조회 2회. 첫 원격의 `unchanged`는 3개 스킬의 쌍을 한꺼번에 답한다 | 테스트(동시성·한 번 해석) |
| T-25 | R-17, R-18 | 원격 R1 실패·R2 성공으로 전체 확인 | R2 스킬은 정상 기록, R1 스킬은 `error`+메시지, 호출은 `Err("Failed to check 1 skill(s): <id>: <msg>")` | 구현 |
| T-26 | R-18 | Phase B에서 다른 작업이 락을 쥐고 있음 | 그 스킬은 컬럼 불변, 실패 목록에 `<id>: skills repository is busy: check skill update` | 구현 |
| T-27 | R-24, R-25 | 트레이·스케줄러가 `local` 스킬을 포함한 라이브러리를 확인 | `force`=true라 TTL 없이 매번 원본 해시 비교 | 구현 |
| T-28 | R-26 | CLI `skills check --all`: `well-known` 1개, `local` 1개(원본 변경됨), 원격 실패 `git` 1개 | `well-known`: `skipped:true`와 저장 값, `local`: `update_available`(TTL 무시), `git`: `update_status`=`error`+메시지. 프로세스는 실패하지 않는다 | 구현 |
| T-29 | R-21 | 브랜치 `main`과 같은 이름의 주석 태그가 있는 저장소에 `ls-remote refs/heads/main refs/tags/main^{} refs/tags/main` | 세 ref 줄이 따로 나오고 앱은 브랜치 줄(첫 후보)을 쓴다. 태그 `v1`만 물으면 `^{}` 줄(커밋)을 쓴다. `HEAD` 질의는 기본 브랜치 커밋. | git 실행 |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (repo@7a22192 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 (상태 결정 `skills.rs:2810-2838`). 상태 쓰기 `update_skill_check_state` C-11. `source_revision`이 메타데이터 파일에 없고 재구성 때 이전 DB 값 또는 NULL로 채워지는 경로: `core/sync_metadata.rs:26-33` `SourceMeta`(revision 필드 없음), `:238-260`(`source_revision: previous…`, `update_status` 기본 `unknown`), 시작 때 호출 `core/app_state.rs:176-180`. | 직접 읽음. "새로 들어온 행은 `unknown`에 머문다"는 이 위치들을 이은 추론(그 재구성 경로가 실제로 쓰이는 장면은 선행 스펙·백업 스펙 소관). |
| R-02 | C-01 `skills.rs:2839-2849`(`AppError::git(message)`, `core/error.rs:94-100`). | 직접 읽음. |
| R-03 | C-01 `skills.rs:2788-2809`(`prefetched.filter(key.matches)`), C-06 `RemoteKey::matches`. 테스트 `matching_prefetched_remote_is_applied`, `prefetched_remote_for_a_different_source_is_discarded`, `missing_prefetch_never_resolves_under_the_lock`(`skills.rs:4054`, `:4076`, `:4231`)를 읽음. | 코드 확인. 테스트는 읽기만. |
| R-04 | C-04. `skillssh`가 `source_ref_resolved`를 먼저 쓰는 이유: 설치가 `source_ref_resolved`를 저장한다(`skills.rs:1083-1092`(git), `:1200-1209`(skillssh)). | 직접 읽음. |
| R-05 | C-01 `skills.rs:2772-2786`, C-11 `skill_store.rs:277-301`(`updated_at` 갱신). | 직접 읽음. 이 쓰기가 R-03에서도 남는 점은 `:2776-2786`이 `:2798` 앞에 있어서다. |
| R-06, R-07 | C-01 `skills.rs:2852-2873`. 설치가 `local`의 초기 `update_status`를 `local_only`, `last_checked_at`을 설치 시각으로 둠: `skills.rs:900-910`, `:2692-2714`. | 직접 읽음. `Ok`로 돌아오는 점은 `:2870-2873`에서 `Err`로 바뀌는 경로가 없는 것으로 확인. |
| R-08 | C-02 `skills.rs:2888-2903`. | 직접 읽음. |
| R-09 | C-02 `:2923-2931`, C-12~C-17. | 직접 읽음. "접기 대상이 UTF-8·NUL 없음 파일"은 C-14 주석·코드. 해시를 실제로 돌려 보지는 않았다. |
| R-10 | C-01 `skills.rs:2874-2876`(주석 "A website snapshot has no revision to compare against; it stays `local_only`"). 설치가 digest를 revision 컬럼에 기록: `skills.rs:989-998`, `core/well_known.rs:232-248`. CLI: C-18 `:1858-1871`. 전체 확인 Phase B가 이 스킬도 지나감: C-05 `:1558-1581`. | 직접 읽음. "digest를 읽지 않는다"는 `check_*` 호출 그래프에서 `well-known` 분기가 비어 있음을 확인(`grep`으로 `remote_revision` 읽기 위치도 확인). 의도는 주석(추론 수준: 개발자 서술). |
| R-11 | C-01 `skills.rs:2877-2881`. | 직접 읽음. 해당 값이 실제로 생기는 경로(다른 기기의 메타데이터 등)는 확인하지 않음. |
| R-12 | C-03. 기본 60·"안정 상태"·엄격한 `<`. `checking`을 쓰는 곳 없음: `grep -rn '"checking"'`이 `skills.rs:2950` 하나. 설정 키가 코드에서 `skills.rs:2943`에만 있음(`grep`, `src/`·`src-tauri/src/` 전체). `updating`을 쓰는 곳: `skills.rs:1904`, `:2137`, `:2451`, `:2579`. | 직접 읽음, `grep`. |
| R-13 | C-05 `skills.rs:1520-1531`(전체: 오류면 경고 로그 후 계속), C-07 `:1683`(`unwrap_or(false)`), C-01 `:2765`(`?`). | 직접 읽음. |
| R-14 | C-06 `installed_subtree`(`skills.rs:1640-1643`), C-01 `:2812-2829`, C-11 `update_skill_source_revision`(주석: "`updated_at` is left alone"). 테스트 `a_monorepo_commit_flags_only_the_skill_it_touches`(`:4313-4341`). | 직접 읽음. 쓰기 두 문장이 별개: `skills.rs:2822-2837`. 한 트랜잭션이 아님은 `skill_store.rs`의 두 함수가 각자 `conn.execute`인 것에서. |
| R-15 | C-07 `skills.rs:1673-1693`. | 직접 읽음. |
| R-16 | C-08, C-09. `git_command()`는 `Command::new("git")`(Linux AppImage에서만 `LD_LIBRARY_PATH` 제거): `core/git_command.rs:3-16`. 타임아웃 인자 없음(`cmd.output()`: `git_fetcher.rs:1696-1698`). libgit2 폴백이 만든 임시 bare 저장소를 지우는 코드가 없음(`:1196-1216`). | 직접 읽음. 폴백이 실제로 도는지와 타임아웃은 실행하지 않음(확인 한계). |
| R-17 | C-05 `:1506-1544`, C-06, C-07. `PrefetchedRemote.unchanged`가 원격 단위 합집합으로 계산되는 점은 테스트 `one_resolution_answers_every_sibling_of_a_remote`(`:4363-4382`). | 직접 읽음. |
| R-18 | C-05 `:1546-1594`. 락: `core/repo_lock.rs:41-46`(비대기), `:18-25`·`:52-73`(foreground 20초·50ms). 락을 스킬마다 잡는 이유 주석: `repo_lock.rs:80-93`. | 직접 읽음. |
| R-19 | `skills.rs:1476-1493`(`prefetch` 다음에 `acquire_foreground`), 락 오류가 `AppError::db`로 변환됨. | 직접 읽음. |
| R-20 | C-10. fetch 인자 `skills.rs`가 아닌 `git_fetcher.rs:1260-1262`, 감시 실행 `:858-934`(타임아웃 `CLONE_TIMEOUT_SECS`=300: `:19`, 비정상 종료는 `bail!`). 실패를 빈 집합으로: `:1296-1305`. | 직접 읽음. "revision 하나가 서버에 없으면 그 원격의 모든 쌍이 빠진다"는 코드(한 번의 fetch, `?` 전파)와 git 실행(R-21 d)의 결합. |
| R-21 | `artifacts/skills-manager/skill-update-check-demos/git-behaviors.sh`, 출력 `git-behaviors.out.2026-10-24.txt`(A: 트리 id 비교, B: `.gitattributes`, C: 모르는 revision, D: filter 거부, E: ls-remote). | 실행 확인. 앱 코드는 실행하지 않았고 `unchanged_subtrees`의 알고리즘(`:1268-1291`)을 libgit2 대신 `git rev-parse <rev>:<path>`로 옮겨 쓴 셸이다. fetch 인자와 ls-remote 후보는 앱과 같은 형태. git 2.50.1(Apple Git-155), `file://` 로컬 저장소에서만. |
| R-22 | `src/context/AppContext.tsx:346-413`(조건 `:348-351`, 지연 `:413`, `auto_update_last_run_at` `:403-404`). | 직접 읽음. |
| R-23 | `src/views/MySkills.tsx:862-886`. | 직접 읽음. |
| R-24 | `src-tauri/src/lib.rs:524-615`(플래그 `:525-531`, 루프 `:556-585`, 완료 기록 `:599`). | 직접 읽음. |
| R-25 | `src-tauri/src/core/skill_auto_updater.rs:146-225`(루프 `:163-198`, `FOREGROUND_YIELD` `:35`). | 직접 읽음. 타이머·옵트인·`record_round_completion`은 읽지 않음(범위 밖). |
| R-26 | C-18, clap 정의 `bin/skills-manager-cli.rs:145-151`, 디스패치 `:913-920`, 선택 `:1900-1915`, ref 해석 `:1439-1455`. 락이 없음: `RepoLock` 사용처가 `:1597` 이후 설치·adopt·git pull뿐(`grep`). | 직접 읽음. |
| R-27 | `src/views/MySkills.tsx:1139-1142`(`canRefresh`), `:1177-1197`(`statusBadge`), `:1577-1585`; `src/components/SkillDetailPanel.tsx:54-61`, `:115-122`; `src/context/AppContext.tsx:252-286`(알림). `last_check_error`·`last_checked_at`을 읽는 UI 코드가 없음: `grep -rn` over `src/`(타입 정의 `lib/tauri.ts:31-33` 제외). | 직접 읽음, `grep`. |
| R-28 | `git_fetcher.rs:1215`(문구), `skills.rs:1651-1653`(`err.to_string()`), `:2845`. | 직접 읽음. 마스킹이 없음은 이 경로에 `log_sanitize`가 없는 것으로(하위 트리 비교의 로그에만 있음, `git_fetcher.rs:1298-1303`). |
| R-29 | `skill-source-metadata` R-12, `skill-update-apply` R-01; `src-tauri/src/core/app_state.rs:175-179`, `core/sync_metadata.rs:232-261`. | 두 문서가 쓴 reindex 동작에서 도출. 두 기기 시나리오나 재시작 후 실제 표시는 실행하지 않음. |
| T-01~T-03 | R-01 근거. T-01은 테스트 `matching_prefetched_remote_is_applied`에서. | 구현 도출. |
| T-04~T-06 | 테스트 `a_monorepo_commit_flags_only_the_skill_it_touches`(`skills.rs:4313`), `an_unfetchable_installed_revision_still_reports_an_update`(`:4346`). git 쪽은 demo A·B·C. | 테스트는 읽기만, 앱 결과는 미실행. |
| T-07 | C-10 + demo C. 원본 주석 `git_fetcher.rs:1233-1235`("an old revision the server no longer has … just leaves that pair out")과 코드·실행이 다름. | 코드 + git 실행. 서버가 GitHub일 때의 거동은 미확인. |
| T-08~T-10 | 테스트 `failed_prefetch_for_the_current_source_records_the_error`(`:4201`), `missing_prefetch_never_resolves_under_the_lock`(`:4231`), `prefetched_remote_for_a_different_source_is_discarded`(`:4076`). | 테스트 읽기. |
| T-15~T-18 | 테스트 `a_local_source_with_a_real_edit_still_reports_an_update`(`:4182`), `a_local_source_that_differs_only_in_line_endings_is_up_to_date`(`:4126`), `a_local_source_with_only_installed_dependencies_is_up_to_date`(`:4143`), `a_missing_library_copy_is_not_up_to_date`(`:4163`). | 테스트 읽기. |
| T-24 | 테스트 `one_resolution_answers_every_sibling_of_a_remote`(`:4363`), `resolve_concurrent_runs_remotes_in_parallel`(`:4008`). | 테스트 읽기. |
| T-29 | demo E. | 실행 확인. |
| (문서 ≠ 구현) | ① `README.md:78` "Check for upstream updates on Git-based skills; re-import local ones" — 구현은 `local`/`import`도 원본 폴더 해시로 확인한다(R-06). ② `skills/manage-skills/SKILL.md:136` "`check` is the dry-run partner of `update`" — 구현은 파일을 바꾸지 않지만 DB 상태 컬럼은 쓴다(R-01~R-07). ③ `git_fetcher.rs:1233-1235` 주석(위 T-07). ④ `skill_auto_updater.rs:30-31` 주석 "Each check holds the central-repo lock for a network round-trip" — #315 이후 네트워크는 락 밖이다(R-25). ⑤ `lib.rs:544-546` 주석 "Update checks only mutate `update_status` columns" — 구현은 `source_revision`(R-14)과 `source_ref_resolved`·`source_subpath`·`source_branch`·`updated_at`(R-05)도 쓴다. ⑥ SKILL.md는 `local`/`import` 확인이 TTL 캐시를 안 탄다고 쓰는데 이는 CLI만 해당하고, 앱의 시작 확인(`force`=false)은 `local_only`·`up_to_date` 같은 안정 상태에서 TTL을 적용한다(R-12, R-22). | 위치 직접 열람. |

### 2.2 코드 읽는 순서

1. `commands/skills.rs:1476-1594` 두 입구(락 순서와 Phase A/B)
2. `:2754-2885` 기록 단계(출처별 분기)
3. `:1596-1746` 원격 키·사전 조회·동시성
4. `core/git_fetcher.rs:1187-1216`, `:1643-1707` head 해석, `:1236-1306` 하위 트리 비교
5. `:2887-3016` 로컬 판정·TTL·소스 해석, `core/content_hash.rs` 해시
6. 호출 지점: `AppContext.tsx:346-413`, `lib.rs:524-615`, `skill_auto_updater.rs:146-225`, `skills-manager-cli.rs:1845-1898`

원본의 전략: ① 락을 쥔 채 네트워크를 쓰지 않는다(#315, 사전 조회/기록 분리). ② 같은 원격은 한 번만 조회하고(`RemoteKey`) 동시 8개로 제한. ③ 하위 폴더 스킬의 거짓 업데이트를 막되 확인하지 못하면 항상 `update_available` 쪽으로 폴백. ④ 줄 끝·의존성 폴더 같은 거짓 업데이트 억제는 "낮추기만 하는" 보조 비교로.
