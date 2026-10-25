---
sha: "7a2219219287f4ef4c543fc169ebcc5b0bff085c"
created: 2026-10-24
updated: 2026-10-24
sources:
  - src-tauri/src/core/skill_store.rs
  - src-tauri/src/core/migrations.rs
  - src-tauri/src/core/sync_metadata.rs
  - src-tauri/src/core/content_hash.rs
  - src-tauri/src/commands/skills.rs
  - src-tauri/src/commands/scan.rs
  - src-tauri/src/commands/agent_workspace.rs
  - src-tauri/src/commands/projects.rs
  - src-tauri/src/core/scenario_service.rs
  - src/views/MySkills.tsx
depends: []
status: ready
reimplementation: 미실행
---

# 스킬 출처 메타데이터 (skill source metadata)

> 라이브러리에 든 스킬 한 개(`skills` 테이블 한 행)가 "어디서 왔고, 지금 원본과 같은가"를 기록하는 필드 11개의 의미, 값을 쓰는 연산, 그리고 기기 사이에서 어떤 필드만 옮겨지는지를 정한다. 설치·변경 확인·diff 스펙이 공유하는 선행 계약이다.

<!--
이 문서가 소유하는 것: 필드 의미와 값 도메인, "누가 어떤 값을 쓰는가"의 교차 표, 메타데이터 파일로 나가는 부분집합과 reindex 때 복원 규칙, 내용 해시의 범위.
이 문서가 소유하지 않는 것: 설치 흐름(skill-install-external), 원격 비교와 상태 판정 알고리즘(skill-update-check), 파일 단위 diff(skill-source-diff).
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 스킬을 라이브러리에 넣는 연산(Git·skills.sh·웹사이트 설치, 로컬 설치, 가져오기)이 출처 필드를 처음 쓴다. 같은 `central_path`에 이미 행이 있으면 새 행을 만들지 않고 그 행의 출처 필드를 통째로 덮어쓴다(R-05).
2. 변경 확인은 주로 `remote_revision`, `update_status`, `last_checked_at`, `last_check_error`를 바꾼다. 비교 기준은 `source_revision`(이 사본이 받아온 원격 리비전)이다. 예외로 git 계열은 저장된 `source_ref_resolved`·`source_subpath`·`source_branch`가 해석값과 다르면 정규화해 쓰고(`updated_at`도 갱신), 하위 폴더가 안 바뀌었으면 `source_revision`을 새 head로 옮긴다(R-07, R-09). 판정 규칙은 `skill-update-check` 스펙이 정한다.
3. 갱신 적용(update, set-source, reimport)은 사본 내용을 바꾸고 `source_revision`, `remote_revision`, `content_hash`, `update_status`를 같이 쓴다(R-08).
4. 매번 라이브러리가 바뀌면 `metadata/skills/<id>.json`에 출처 필드의 **일부만**(type, ref, subpath, branch) 내보낸다(R-11).
5. 다른 기기가 이 메타데이터로 reindex하면, 내보내지 않은 필드(`source_ref_resolved`, 두 리비전, 상태 셋)는 같은 `id`의 이전 행에서 가져오고 이전 행이 없으면 비운다(R-12). 그 결과 새 기기에 처음 나타난 Git 스킬은 `source_revision`이 비어 있다(R-13).

### 1.2 범위·통합 지점 [필수]
- 제공: 출처 필드의 의미와 값 도메인, 필드를 쓰는 연산 목록, 기기 간 이동 규칙, 내용 해시의 범위, 화면이 상태값을 읽는 방식.
- 제외: 설치 연산 자체의 흐름·임시 폴더·진행 이벤트(`skill-install-external`), 원격 리비전 조회·판정 분기(`skill-update-check`), 원본과의 파일 diff(`skill-source-diff`), 갱신을 적용하는 파일 교체 절차와 삭제 확인(범위 밖 — 값을 쓰는 규칙만 R-08에 둔다), 배포 대상(`skill_targets`)·태그·Preset 컬럼.
- 외부 의존·선행 계약: SQLite 한 개(`skills` 테이블, `central_path`는 UNIQUE). 중앙 라이브러리 폴더와 `metadata/` 폴더(`sync_metadata`가 읽고 쓴다). 저장소 락은 호출자가 잡는다(이 문서의 setter 자체는 락을 잡지 않는다).
- 소유 상태·부작용: `skills` 테이블의 출처 관련 열과 `metadata/skills/<id>.json`의 `source` 객체. 이 필드를 쓰는 연산은 대부분 끝에 `write_all_from_db_unlocked`로 메타데이터 파일을 다시 쓴다(코드 확인: R-07, R-08).

### 1.3 인터페이스와 데이터 의미 [필수]
**출처 필드** (`SkillRecord`, 전부 `skills` 열 이름과 같음)

| 필드 | 타입 | 의미 | 기본값·누락 | 메타 파일로 나가나 |
|---|---|---|---|---|
| `source_type` | string, NOT NULL | 출처 종류. 값은 아래 표 | 필수 | 나감(`source.type`) |
| `source_ref` | string? | 사용자가 준 원본 식별자. Git은 입력 URL 원문, skills.sh는 `owner/repo/skill-id`, 웹사이트는 정규화한 skills.sh URL, local·import는 이 기기의 원본 경로 | NULL 가능 | 나감(`source.ref`), 단 `local`·`import`는 항상 `null`로 나감 |
| `source_ref_resolved` | string? | 실제로 clone·다운로드한 주소. Git·skills.sh는 clone URL, 웹사이트는 해석된 URL | NULL | 안 나감 |
| `source_subpath` | string? | 저장소 안 스킬 폴더의 상대 경로. 저장소 루트면 NULL | NULL | 나감 |
| `source_branch` | string? | 설치 때 해석한 브랜치. 기본 브랜치를 쓰면 NULL | NULL | 나감 |
| `source_revision` | string? | 이 라이브러리 사본이 받아온 원격 리비전(커밋 해시). 변경 확인의 비교 기준 | NULL | 안 나감 |
| `remote_revision` | string? | 마지막으로 관찰한 원격 최신 리비전. 확인할 때마다 덮어씀 | NULL | 안 나감 |
| `content_hash` | string? | 라이브러리 사본 내용의 SHA-256(범위는 R-10) | NULL | 안 나감 |
| `update_status` | string, 기본 `'unknown'` | 변경 상태. 값은 아래 표 | `'unknown'` | 안 나감 |
| `last_checked_at` | int? (Unix epoch ms) | 마지막 확인·갱신 시각 | NULL | 안 나감 |
| `last_check_error` | string? | 마지막 실패 메시지. 성공하면 NULL | NULL | 안 나감 |

**`source_type` 값** (닫힌 enum은 아니고 문자열이다. 아래 5개가 코드가 쓰는 전부다. 코드 확인: R-02)

| 값 | 만드는 연산 | `source_ref` | 리비전 필드 | 초기 `update_status` |
|---|---|---|---|---|
| `git` | Git 설치(앱·CLI), set-source | 입력 URL 원문 | 설치 시점 HEAD 해시 두 개 모두 | `up_to_date` |
| `skillssh` | skills.sh 설치(앱·CLI) | `owner/repo/skill-id` | 설치 시점 HEAD 해시 두 개 모두 | `up_to_date` |
| `well-known` | 웹사이트(skills.sh `/site/…`) 설치 | 정규화된 skills.sh URL | 다운로드가 준 리비전(없을 수 있음) 두 개 모두 | `local_only` |
| `local` | 로컬 폴더 설치, 폴더 일괄 가져오기, 워크스페이스에서 올리기 | 원본 폴더 경로 | NULL | `local_only` |
| `import` | 스캔·adopt, 앱이 모르던 폴더 편입, 병합·복원 중 만든 행 | 원본 폴더 경로(경우에 따라 중앙 사본 경로) | NULL | `local_only` |

**`update_status` 값**

| 값 | 쓰는 연산 | 뜻 |
|---|---|---|
| `up_to_date` | 설치(git·skillssh), 확인, 갱신 | 원본과 같다 |
| `update_available` | 확인, 삭제 확인에서 멈춘 git 갱신(재가져오기·relink가 멈추면 이전 상태를 복원) | 원본이 다르다 |
| `unknown` | 확인(리비전을 모를 때), reindex가 이전 행 없이 만든 행 | 판정 불가 |
| `error` | 확인·갱신·set-source·reimport 실패 | `last_check_error`에 이유 |
| `source_missing` | local·import 확인, reimport | 원본 경로가 없다 |
| `local_only` | local·import·well-known 설치, reimport 성공 | 비교할 원격이 없다 |
| `updating` | 갱신·set-source·reimport 진행 중 | 진행 표시. git 갱신이 clone 실패·취소로 끝나면 되돌려지지 않고 남는 경로가 있다(`skill-update-apply` R-16) |
| `checking` | **아무 연산도 쓰지 않는다**(백엔드·프런트에서 쓰는 곳 없음, 읽기만 함) | 건너뜀 판정이 "안정 상태 아님"으로 취급(R-14) |

**메타데이터 파일** `metadata/skills/<skill_id>.json`: `{schema_version, skill_id, path, path_key, enabled, tags, source: {type, ref, subpath, branch}}`. `source`의 4개 필드가 R-11이 말하는 이동 가능한 부분이다(C-05).

**화면 DTO** `ManagedSkillDto`는 위 출처 필드를 이름 그대로 모두 내려보낸다(`description`만 `SKILL.md`에서 다시 읽은 값을 우선한다, R-15).

### 1.4 행동 규칙과 남은 질문 [필수]
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `skills` 테이블 생성 | 위 11개 필드가 같은 열 이름으로 있다. `source_type`만 NOT NULL, `update_status` 기본 `'unknown'`, `central_path` UNIQUE. 구버전 DB에는 뒤에 붙은 열(`source_ref_resolved`, `source_subpath`, `source_branch`, `remote_revision`, `update_status`, `last_checked_at`, `last_check_error`)을 마이그레이션이 추가한다 | 코드 확인 |
| R-02 | 코드가 `source_type`에 쓰는 문자열 | `git`, `skillssh`, `well-known`, `local`, `import` 다섯 가지뿐이다. 다른 값을 만드는 곳은 없다 | 코드 확인 |
| R-03 | Git 설치(앱 `install_git`, 앱 `confirm_git_install`)가 행을 쓴다 | `source_ref`=입력 URL(직접 설치 `install_git`은 앞뒤 공백을 자른 값, 미리보기 확정 `confirm_git_install`은 자르지 않은 원문), `source_ref_resolved`=clone URL, `source_subpath`=체크아웃 안 스킬 폴더의 상대 경로, `source_branch`=URL이 정한 브랜치, `source_revision`=`remote_revision`=clone HEAD, `update_status='up_to_date'` | 코드 확인 |
| R-04 | skills.sh 설치(`install_from_skillssh`)·웹사이트 설치(`install_site_skill_dir`)가 행을 쓴다 | skills.sh: `source_ref`=`<source>/<skill_id>`, resolved=`https://github.com/<source>.git`, 리비전 두 개=clone HEAD, `up_to_date`. 웹사이트: `source_ref`=정규화한 skills.sh URL, `source_subpath`·`source_branch`=NULL, **`update_status='local_only'`**. 직접 설치는 resolved=받은 파일 URL, 두 리비전=다운로드 결과(v2 인덱스면 `sha256:<hex>` digest, v1이면 NULL). 미리보기 확정 경로(`confirm_git_install`의 사이트 분기)는 resolved=입력 URL, 두 리비전=NULL | 코드 확인 |
| R-05 | 설치 연산이 `store_installed_skill_unlocked`를 부른다 | 설치된 `central_path`로 이미 행이 있으면 그 행의 `name`, `description`, 출처 필드 전부, `content_hash`, `update_status`를 덮어쓰고 `status='ok'`, `last_checked_at`=지금, `last_check_error`=NULL로 만들며 `id`는 유지한다. 없으면 UUID로 새 행을 넣고 `last_checked_at`=지금. 둘 다 끝에 메타데이터 파일을 다시 쓴다 | 코드 확인 |
| R-06 | 로컬 설치·폴더 일괄 가져오기·워크스페이스 업로드·스캔/adopt | `source_type`은 `local`(설치·일괄·업로드) 또는 `import`(스캔·adopt 등), `source_ref`=원본 경로, resolved·subpath·branch·두 리비전=NULL, `update_status='local_only'` | 코드 확인(설치·일괄: 저장 직전 리터럴, 업로드·adopt: 행 리터럴) |
| R-07 | 변경 확인이 상태를 기록한다 | `update_skill_check_state`가 `remote_revision`, `update_status`, `last_checked_at`=지금, `last_check_error`를 한 번에 쓴다. `remote_revision`은 항상 덮어쓰므로 `None`을 넘기면 값이 비워진다. 실패 확인은 이전 `remote_revision`을 그대로 넘겨 `error`로 표시한다. git 계열 확인은 이에 더해, 저장된 `source_ref_resolved`·`source_subpath`·`source_branch` 중 하나라도 `git_source_from_skill`이 해석한 값과 다르면 `update_skill_source_metadata`로 세 값을 해석값으로 바꾸고(`source_revision`은 그대로 넘기며 `updated_at`=지금) 상태를 기록한다 | 코드 확인 |
| R-08 | 갱신 적용 | 내용이 바뀌면 `update_skill_after_install`이 `source_revision`, `remote_revision`, `content_hash`, `name`, `description`을 쓰고 `updated_at`·`last_checked_at`=지금, `last_check_error`=NULL, `update_status`는 호출자가 정한 값(`up_to_date`)으로 만든다. 내용이 같으면 `update_skill_source_metadata`로 resolved·subpath·branch·source_revision만 갱신하고 `update_skill_check_state`로 상태를 `up_to_date`로 둔다. set-source는 `update_skill_after_reinstall`로 `source_type='git'`과 모든 출처 필드를 새 값으로 한 번에 바꾼다. reimport는 `local_only`로 끝나며 리비전은 NULL. relink는 `source_type`을 그대로 두고 `source_ref`만 새 경로로 바꾸고 resolved·subpath·branch·리비전을 NULL로 비우며 `local_only`로 끝낸다(사본은 새 원본으로 교체). detach는 `source_ref`를 NULL로 비우고 `local_only`로 둔다(사본·`content_hash`는 그대로). 셋 다 `update_skill_after_reinstall`을 쓴다(`skill-update-apply`) | 코드 확인 |
| R-09 | `update_skill_source_revision` | `source_revision`만 바꾸고 `updated_at`은 건드리지 않는다("내용은 안 바뀌었고 원격만 앞섰다"는 기록). 이 setter의 호출은 모노레포 하위 폴더가 안 바뀐 경우뿐이다 | 코드 확인 |
| R-10 | `content_hash`를 계산한다 | 스킬 폴더 아래 일반 파일만(디렉터리는 제외) 경로순으로 훑어, 각 파일의 상대 경로(Windows `\`는 `/`로 통일) 바이트와 파일 내용 바이트(와 unix에서는 실행 비트 `mode & 0o111` 4바이트)를 SHA-256에 이어 먹인다. 이름이 `.git`, `.DS_Store`, `Thumbs.db`, `.gitignore`, `__pycache__`이거나 `.pyc`로 끝나는 항목은 파일·디렉터리 모두 제외한다. 읽을 수 없는 하위 디렉터리는 없는 것으로 친다. `node_modules`, `.venv`, `venv`는 해시에 **포함**된다(CRLF 무시 비교에서만 빠진다) | 코드 확인 |
| R-11 | 메타데이터 파일을 쓴다 | `source`에 `type`, `ref`, `subpath`, `branch` 네 개만 쓴다. `source_type`이 `import` 또는 `local`이면 `ref`는 `null`이다(기기 경로는 옮기지 않는다). `source_ref_resolved`, 두 리비전, `content_hash`, 상태 셋은 쓰지 않는다 | 코드 확인 |
| R-12 | 메타데이터로 reindex한다(다른 기기가 받은 뒤, 시작 때 등) | 파일마다 `central_path`를 다시 정하고 행을 upsert한다. `source_type`·`source_subpath`·`source_branch`는 파일 값. `source_ref`는 `local`·`import`이면 **같은 `id`의 이전 행** 값(없으면 NULL), 그 밖은 파일 값. `source_ref_resolved`, `source_revision`, `remote_revision`, `last_checked_at`, `last_check_error`는 이전 행 값(없으면 NULL), `update_status`는 이전 행 값(없으면 `'unknown'`). `content_hash`는 디스크의 폴더를 새로 해시한 값으로 대체하고, 해시가 이전 행과 같으면 `updated_at`을 유지, 다르면 지금으로 바꾼다. 스킬 폴더가 없으면 행을 지운다 | 코드 확인 |
| R-13 | R-12로 처음 만들어진 `git`·`skillssh` 행(이전 행 없음) | `source_revision`, `remote_revision`, `update_status`가 비어 있다(`'unknown'`). 변경 확인은 `source_revision`이 없으면 `'unknown'`으로 기록한다(`skill-update-check`). `source_revision`을 채우는 곳은 설치, 갱신, 모노레포 하위 폴더 미변경 경로뿐이라 확인만으로는 채워지지 않는다 | 코드 확인(읽기만, 두 기기 시나리오는 실행하지 않음) |
| R-14 | 건너뜀 판정이 상태를 본다 | `update_status`가 `unknown`, `checking`, `updating`, `error`이면 "안정 상태가 아님"이라 TTL 안이라도 다시 확인한다(TTL 규칙은 `skill-update-check`) | 코드 확인 |
| R-15 | 화면이 스킬을 읽는다 | `ManagedSkillDto`는 출처 필드를 그대로 싣고 `description`은 `SKILL.md`의 값을 우선한다. 출처 라벨은 `skillssh`→"skills.sh", `git`→"Git", `local`→"Local", `import`→"Imported", 그 밖(`well-known`)은 값 문자열 그대로. 프런트는 `update_status`가 `update_available`이면 "Update" 배지, `source_missing`·`error`이면 빨간 배지를 보이고 나머지는 배지가 없다. "갱신 가능"(`canRefresh`)은 `git`·`skillssh`이거나 `source_ref`가 있는 `local`·`import`이다(`well-known`은 아님) | 코드 확인 |
| R-16 | 이미 있는 `local` 행의 `source_ref`가 같은 원본을 가리킬 때 / adopt가 에이전트 폴더를 배포로 바꿀 때 | `update_skill_source_ref`로 `source_ref`만 바꾼다: 워크스페이스·프로젝트에서 같은 스킬을 다시 올리면 `source_ref`를 그 경로로 갱신(`local`이고 이미 같은 원본일 때만), adopt가 에이전트 폴더를 배포 사본으로 바꾸면 `source_ref`를 중앙 사본 경로로 다시 가리킨다(#425) | 코드 확인(호출 지점과 조건 일부만) |
| R-17 | `(source_type, source_ref)` 완전 일치 조회 `get_skill_by_source_ref` | 일치하는 첫 행을 돌려준다(유일 제약이 아니므로 여러 행이면 임의의 첫 행). skills.sh·웹사이트 설치의 이름 충돌 처리만 이것으로 기존 행을 찾는다. Git 설치는 쓰지 않는다(`skill-install-external` R-13) | 코드 확인(정의와 호출 지점) |
| R-18 | `write_all_from_db_unlocked`(출처 필드를 바꾸는 연산 끝에서 호출) | 메타데이터 폴더 `<라이브러리 폴더>/.skills-manager/`를 만들고 `schema.json`을 쓰고, 모든 스킬마다 `skills/<id>.json`을 다시 쓰고(R-11), 프리셋 파일을 쓴 뒤, 현재 스킬 id 집합에 없는 `skills/*.json`을 지운다(프리셋·멤버십 파일도 같은 방식) | 코드 확인 |

- 불변식: (1) `source_revision`은 라이브러리 사본의 출처 리비전이고 `remote_revision`은 관찰값이라 둘은 일치하지 않을 수 있다. 일치하면 `up_to_date`다(`skill-update-check`가 `source_revision == remote_revision`으로 판정). (2) `local`·`import`·`well-known`은 리비전 비교를 쓰지 않는다. (3) 메타데이터 파일은 기기 경로(`local`·`import`의 `source_ref`)를 담지 않는다. 전제: 위 setter들을 통해서만 쓴다 — `upsert_skill`(reindex·병합)은 11개 필드를 통째로 쓴다.
- 미결정: 없음. 범위 밖으로 둔 것: 병합 엔진·자동 백업이 `import` 행을 만드는 경우(`core/merge/decision.rs`, `core/auto_backup.rs`)의 필드 값, `status`·`enabled` 열.
- 확인 한계: 앱·CLI를 실행하지 않았다. R-13은 코드 읽기로 도출한 결과이고 두 기기에서 실제로 `unknown`이 유지되는지는 확인하지 않았다. `skillssh` 설치가 앱 경로(`install_from_skillssh`)와 CLI(`bin/skills-manager-cli.rs`)에서 같은 값을 쓰는지는 앱 경로만 줄 단위로 읽었다.

### 1.5 필수 코드 참조 [필수]
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src-tauri/src/core/skill_store.rs:19-39` `SkillRecord` | 필드 이름·타입 | R-01 |
| C-02 | `src-tauri/src/core/migrations.rs:71-91` `skills` DDL, `:184-190` `add_column_if_missing` | 열·기본값·UNIQUE, 구버전 보강 | R-01 |
| C-03 | `src-tauri/src/core/skill_store.rs:277-339` `update_skill_source_metadata`, `update_skill_source_revision`, `update_skill_check_state`, `update_skill_update_status` | 필드별 setter와 `updated_at` 처리 | R-07, R-09 |
| C-04 | `src-tauri/src/core/skill_store.rs:352-434` `update_skill_after_install`, `update_skill_source_ref`, `update_skill_after_reinstall` | 갱신·재설치가 한 번에 쓰는 열 | R-05, R-08, R-16 |
| C-05 | `src-tauri/src/core/sync_metadata.rs:25-31` `SourceMeta`, `:446-471` `write_skill_file` | 메타 파일의 이동 가능한 부분집합과 local·import의 ref 제거 | R-11 |
| C-06 | `src-tauri/src/core/sync_metadata.rs:224-262` reindex의 `SkillRecord` 조립 | 이전 행에서 복원하는 필드와 기본값 | R-12 |
| C-07 | `src-tauri/src/commands/skills.rs:2645-2731` `store_installed_skill_unlocked` | 재설치(덮어쓰기) vs 새 행 | R-05 |
| C-08 | `src-tauri/src/commands/skills.rs:281-290` `InstallSourceMetadata` 와 생산자 리터럴: `:901-910`(local), `:989-998`(well-known), `:1083-1092`(git, `install_git`), `:1200-1209`(skillssh), `:1441-1450`(git, `confirm_git_install`) | 설치가 쓰는 값 | R-03, R-04, R-06 |
| C-09 | `src-tauri/src/commands/skills.rs:2216-2252`(갱신 적용), `:2473-2488`(set-source), `:2616-2626`(reimport) | 적용 연산이 쓰는 값 | R-08 |
| C-10 | `src-tauri/src/core/content_hash.rs:7-16`, `:80-138`, `:143-168` `IGNORED`, `is_ignored`, `walk_content_files`, `hash_entries`, `hash_directory` | 내용 해시 범위·바이트 열 | R-10 |
| C-11 | `src-tauri/src/commands/skills.rs:714-722` `source_label_for_skill`; `src/views/MySkills.tsx:1139-1142` `canRefresh`, `:1177-1197` `statusBadge` | 화면이 값을 읽는 방식 | R-15 |
| C-12 | `src-tauri/src/core/sync_metadata.rs:81-83` `metadata_dir`, `:114-121` `write_all_from_db_unlocked`, `:329-335` `write_skill_records_from_db`, `:360-366` `remove_stale_metadata_files`(스킬 부분), `:423-444` `remove_stale_json_files` | 메타데이터 폴더 위치, 전체 재작성 순서, 오래된 파일 삭제 | R-18 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 아래는 "스펙대로 구현한 코드가 만족해야 하는 관찰"이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03, R-05 | 빈 라이브러리에서 `https://github.com/o/r`의 하위 폴더 스킬을 Git 설치(HEAD=`abc`) | 새 행: `source_type=git`, `source_ref`=입력 URL, `source_ref_resolved`=`https://github.com/o/r.git`, `source_subpath`=그 폴더, `source_revision=remote_revision=abc`, `update_status=up_to_date`, `last_checked_at`=지금 |
| T-02 | R-05 | T-01 직후 같은 스킬을 HEAD=`def`로 다시 설치(같은 `central_path`) | 새 행이 아니라 같은 `id`의 출처 필드가 `def`로 덮어써지고 `last_check_error`=NULL |
| T-03 | R-04 | 웹사이트 스킬 설치(다운로드 리비전 없음) | `source_type=well-known`, 리비전 둘 다 NULL, `update_status=local_only` |
| T-04 | R-06 | 로컬 폴더 `/p/x` 설치 | `source_type=local`, `source_ref=/p/x`, 리비전 NULL, `update_status=local_only` |
| T-05 | R-11, R-12 | T-04 행을 내보낸 뒤 다른 기기(이전 행 없음)에서 reindex | 메타 파일의 `ref`는 `null`, 새 행의 `source_ref`=NULL, `update_status=unknown` |
| T-06 | R-12, R-13 | T-01 행을 내보낸 뒤 다른 기기(이전 행 없음)에서 reindex | `source_type=git`, `source_ref`=입력 URL, `source_subpath`=그 폴더, `source_ref_resolved`=NULL, `source_revision`=NULL, `remote_revision`=NULL, `update_status=unknown`, `content_hash`=디스크 폴더의 새 해시 |
| T-07 | R-12 | T-01 행이 있는 같은 기기에서 같은 `id`로 reindex | 이전 행의 `source_ref_resolved`, 두 리비전, 상태 셋이 유지되고 해시가 같으면 `updated_at`도 유지 |
| T-08 | R-10 | 폴더 A와 같은 내용에 `.DS_Store`와 `a.pyc`를 추가한 폴더 B, 그리고 `node_modules/x.js`를 추가한 폴더 C | A와 B의 해시는 같고, C의 해시는 다르다 |
| T-09 | R-07 | `update_skill_check_state(id, None, "error", Some("m"))` | `remote_revision`=NULL, `update_status=error`, `last_check_error="m"`, `last_checked_at`=지금 |
| T-10 | R-15 | `source_type=well-known`, `update_status=local_only`인 스킬 | 배지 없음, "갱신 가능" 아님, 출처 라벨은 `well-known` |
| T-11 | R-18 | 스킬 두 개(id=a, b)가 있고 `skills/c.json`이 남아 있다 | 호출 뒤 `skills/a.json`, `skills/b.json`이 현재 값으로 쓰이고 `skills/c.json`은 삭제된다 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@7a22192 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01, C-02 | DDL 열 목록 직접 읽음. 구버전 보강은 `add_column_if_missing` 호출 목록 |
| R-02 | C-08(5개 리터럴), `core/sync_metadata.rs` `"import"`, `commands/agent_workspace.rs` `"local"`, `commands/scan.rs` `"import"` | `grep 'source_type: "'`로 모든 리터럴을 모아 테스트 코드·테스트 헬퍼를 제외하고 값 5종임을 확인. 동적으로 문자열을 만드는 곳은 `grep`에서 못 찾음(`source_type: ...to_string()` 중 `"..."` 리터럴이 아닌 것은 `skill.source_type` 복사뿐) |
| R-03 | C-08 `:1083-1092`, `:1441-1450` | 두 생산자의 구조체 리터럴을 열어 대조. `install_git`은 `parsed.original_url`, `confirm_git_install`은 `repo_url`을 `source_ref`로 쓴다. `parse_git_source`가 `original_url`에 `url.trim()`한 입력을 넣고(`core/git_fetcher.rs:36-46`), `parse_git_source_resolved`는 그 값을 바꾸지 않고 `branch`·`subpath`만 다시 해석한다(`:1551-1575`을 앞부분만 읽음)가 근거다. 그래서 두 경로의 차이는 입력 앞뒤 공백뿐이다(`skill-install-external` R-19가 같은 결론을 낸다) |
| R-04 | C-08 `:989-998`, `:1200-1209`; 웹사이트 `install_site_skill` `:949-957`(`downloaded.revision.clone()`), `install_site_skill_dir` `:968-1000` | 구조체 리터럴 직접 읽음. `well-known`의 `revision`은 `well_known::download_site_skill`이 돌려주는 `Option<String>`(`core/well_known.rs:96-117`, v2 인덱스 `download_v2_entry`와 v1 `download_v1_entry`가 `(resolved_url, revision)`을 돌려줌)이고, 값이 언제 채워지는지는 `skill-install-external`이 소유한다 |
| R-05 | C-07 | 함수 전체 읽음 |
| R-06 | C-08 `:901-910`; `commands/skills.rs` `batch_import_folder` 리터럴; `commands/agent_workspace.rs`·`commands/projects.rs`·`commands/scan.rs`의 `SkillRecord` 리터럴 | 각 리터럴을 열어 값 대조. `scenario_service.rs`·`commands/tools.rs`·`commands/presets.rs`·`commands/git_backup.rs`·`core/auto_backup.rs`·`core/merge/decision.rs`의 `import` 행 생성은 필드를 열어보지 않았다 |
| R-07 | C-03 | setter와 `update_git_skill_internal`의 오류 경로(`Some(&remote_revision)`을 넘김) |
| R-08 | C-04, C-09 | 세 연산의 해당 줄 읽음. 삭제 확인(`pending_removals`)에서 멈추면 `update_available`로 되돌린다(`:2199-2207`). 그 흐름은 갱신 스펙 범위 밖 |
| R-09 | C-03, `check_skill_update_internal_with_remote` `:2818-2826` | setter 정의와 유일한 호출 지점 확인 |
| R-10 | C-10 | 코드 읽음. 실행하지 않음 |
| R-11 | C-05 | 직접 읽음 |
| R-12 | C-06 | 직접 읽음. `previous`는 reindex 시작 때 만든 `existing_by_id`(같은 `skill_id`)이다 |
| R-13 | C-06, `commands/skills.rs:2812-2829` | `source_revision`을 쓰는 곳을 `grep`으로 모아 확인: 설치(C-08), 갱신(C-09), `update_skill_source_metadata` 호출들, `update_skill_source_revision`(R-09 한 곳). 확인만으로 `None`이 채워지는 경로는 없음 |
| R-14 | `commands/skills.rs:2933-2958` `should_skip_update_check` | 직접 읽음 |
| R-15 | C-11, `commands/skills.rs:2020-2075` `managed_skill_to_dto` | 직접 읽음. 프런트 배지는 `MySkills.tsx` 한 곳만 열었다(`AppContext.tsx`도 `update_available`을 읽는다) |
| R-16 | `commands/agent_workspace.rs:262-276`, `core/scenario_service.rs:960-978`, `commands/projects.rs:1010` | 호출 지점 주변만 읽음. 앞쪽 조건(어떤 스킬이 후보인지)은 전부 읽지 않음 |
| R-17 | `core/skill_store.rs:260-275`, `commands/skills.rs:3148-3160`(호출 한 곳) | 정의와 호출 하나만 확인. Git이 쓰지 않는다는 점은 `skill-install-external`이 근거를 가진다 |
| R-18 | C-12 | 함수들을 직접 읽음 |
| T-01~T-10 | 구현에서 도출 | 실행하지 않음. T-06은 R-12와 R-13을 합친 도출이다 |

문서와 구현 차이: `CHANGELOG.md`(1.42.1)는 "모노레포 스킬이 항상 업데이트로 보이던 문제"를 고쳤다고 하는데, 그 설명대로 `update_skill_source_revision`이 있다(R-09). `update_status` 값 `checking`은 i18n 문자열이 있어 UI가 쓸 것처럼 보이지만 쓰는 코드는 없다(R-14).

### 2.2 코드 읽는 순서 [선택]
`SkillRecord`(C-01) → 설치 생산자 5개(C-08)와 `store_installed_skill_unlocked`(C-07) → 확인 기록 setter(C-03)와 `check_skill_update_internal_with_remote` → 갱신·set-source(C-09) → 메타데이터 내보내기·reindex(C-05, C-06).

### 2.3 비교·재사용 출처 [선택]
- 같은 기능을 다른 레포에서 스펙으로 만든 것은 없다. 참고: `my-skills`(개인 저장소)는 출처 메타데이터 없이 git으로 직접 관리한다.
- 코드를 복사해 재사용한 것은 없다. 라이선스는 MIT(overview 1절).

## 적용 메모 [선택]
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-13 | 새 기기에서 처음 만들어진 Git 스킬도 `source_revision`을 가진 채 시작하게 하는 방안 | 지금은 두 번째 기기에서 변경 확인이 `unknown`에 머문다(코드 읽기 결과) | 메타 파일 `source`에 리비전을 넣거나, 비어 있을 때 첫 확인이 현재 원격을 기준으로 삼을지 정해야 한다. 정한 적 없음 — 필요하면 사용자 결정 |
