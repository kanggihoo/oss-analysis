---
sha: "7a2219219287f4ef4c543fc169ebcc5b0bff085c"
created: 2026-10-24
updated: 2026-10-24
sources:
  - src-tauri/src/commands/skills.rs
  - src-tauri/src/core/content_hash.rs
  - src-tauri/src/core/git_fetcher.rs
  - src-tauri/src/core/installer.rs
  - src-tauri/src/core/path_guard.rs
  - src-tauri/src/core/skill_metadata.rs
  - src-tauri/src/core/error.rs
  - src/lib/tauri.ts
  - src/components/SkillDetailPanel.tsx
  - src/components/SkillSourceDiffViewer.tsx
  - src/components/DocumentDiffViewer.tsx
  - src/i18n/en.json
  - CHANGELOG.md
depends:
  - ../capabilities/skill-source-metadata.md
status: ready
reimplementation: 미실행
---

# 스킬 원본과 내 사본의 차이 보기 (source diff)

> 중앙 라이브러리에 든 스킬 하나의 id를 받아, 그 스킬의 원본(Git 저장소 또는 로컬 폴더)에서 `SKILL.md` 계열 문서를 읽어 주고(`get_source_skill_document`), 원본 폴더와 라이브러리 사본의 파일 목록·내용 차이를 파일별 항목(추가/삭제/변경)으로 돌려주며(`get_skill_source_diff`), 상세 패널이 이를 Local/Diff/Source 탭으로 보여 준다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

대표 흐름은 git 출처 스킬의 Diff 탭이다. 로컬 출처는 3~6단계 없이 2단계에서 원본 폴더로 바로 간다.

1. My Skills에서 스킬을 열면 상세 패널이 뜬다. 출처가 `git`·`skillssh`이거나 `source_ref`가 있는 `local`·`import`이면 Local/Diff/Source 탭이 보이고, 열자마자 `get_source_skill_document`가 한 번 호출된다(R-20, R-21).
2. 사용자가 Diff 탭을 처음 누르면 `get_skill_source_diff(skillId)`가 한 번 호출된다. 백엔드는 스킬 행을 읽고 `source_type`으로 갈라 `well-known`·그 밖의 값은 즉시 거절한다(R-01, R-02).
3. git 계열은 `source_ref_resolved`/`source_ref`/`source_branch`/`source_subpath`에서 clone URL·브랜치·하위 폴더·locator id를 구한다(R-05). URL 스킴을 검사한다(R-06).
4. `git ls-remote`로 원격 최신 revision을 구한다(R-07).
5. OS 임시 폴더에 그 저장소를 clone하고 위 revision으로 checkout한 뒤, 스킬이 든 폴더를 찾는다(R-08, R-09, R-19).
6. 라이브러리 사본(old)과 원본 폴더(new)를 같은 파일 범위로 열거해 파일 경로 순으로 비교하고, 항목마다 `status`·`content_kind`·텍스트를 채운다(R-13~R-17). 임시 폴더를 지운다(R-10).
7. 프런트엔드는 항목을 파일별 카드로 그리고, 텍스트 항목은 줄 단위 좌우 diff로 그린다(R-22, R-23). 실패하면 이유를 버리고 "Source content is unavailable right now"를 보인다(R-21).

### 1.2 범위·통합 지점

- 제공: 스킬 하나의 (a) 원본 문서 본문 (b) 원본 폴더 대 라이브러리 사본의 파일 단위 diff DTO (c) 이 둘을 보여 주는 상세 패널 탭과 diff 뷰어. 앱 전용이다. CLI에는 diff 명령이 없다(R-24).
- 제외: 변경 여부 판정과 `update_status` 등 상태 컬럼 기록(update check 스펙), 변경 적용(update·reimport·relink), 에이전트 배포 사본과의 비교, 원본을 라이브러리로 가져오는 설치 흐름. `DocumentDiffViewer`는 Workspace·Project 화면도 쓰지만 그 사용처는 이 스펙 밖이다(`DocumentDiffViewer`의 알고리즘만 R-23에서 다룬다).
- 외부 의존·선행 계약:
  - 선행 스펙 `skill-source-metadata`: 스킬 행의 `source_type`·`source_ref`·`source_ref_resolved`·`source_branch`·`source_subpath`·`central_path`의 일반 의미와 값 집합. 이 스펙은 "각 컬럼을 어떻게 읽어 원본을 찾는가"(R-03, R-05)만 정한다.
  - git 실행 계층: `ls-remote`·clone·checkout은 외부 계약으로 본다. 입력은 (clone URL, 브랜치 또는 없음, 하위 폴더 또는 없음, 프록시 URL 또는 없음), 정상 결과는 "그 브랜치 끝(depth 1)이 checkout된 임시 폴더", 실패는 R-10의 오류 종류다. clone은 하위 폴더가 정리된 경로이고 그곳이 스킬 폴더이면 그 폴더만 받는 좁은 clone을 먼저 시도하고, 어떤 이유로든 실패하면 전체 clone으로 되돌아간다(취소 제외). 폴더 캐시·잠금·1 GiB 정리 같은 clone 내부는 이 스펙 밖이다.
  - 프록시: `store.proxy_url()`(설정에서 읽음, 없으면 없음)을 `ls-remote`와 clone에 넘긴다.
- 소유 상태·부작용: DB·라이브러리 폴더·원본 폴더를 쓰지 않는다(읽기 전용). git 경로는 OS 임시 폴더에 `skills-manager-clone-<uuid>` 디렉터리를 만들었다가 지운다. clone 계층의 저장소 캐시(앱 캐시 폴더 아래)는 갱신될 수 있고 이 기능은 지우지 않는다. `RepoLock`을 잡지 않는다(R-01).

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `get_source_skill_document` | `skillId: string` → `SourceSkillDocumentDto` 또는 `AppError` | 원본에서 읽은 문서 한 개. 네트워크가 필요할 수 있다. Tauri invoke 이름과 인자 이름(`skillId`)이 외부 계약이다. |
| `get_skill_source_diff` | `skillId: string` → `SkillSourceDiffDto` 또는 `AppError` | 라이브러리 사본(old)과 원본(new)의 파일 단위 diff. 같은 계약 이름. |
| `SourceSkillDocumentDto` | `skill_id`, `filename`, `content`, `source_label`, `revision` (모두 string) | `filename`은 읽은 파일의 이름(`SKILL.md` 등, R-12). `content`는 파일 전체(UTF-8). `revision`은 git이면 원격 revision 문자열 전체, 로컬이면 고정 문자열 `"workspace"`. |
| `SkillSourceDiffDto` | `skill_id`, `source_label`, `revision`, `entries: list<SkillSourceDiffEntryDto>` | `entries`는 `relative_path` 오름차순(바이트 순서), 변경 없는 파일은 없다. 빈 목록이 "차이 없음"이다. 복사본이고 호출마다 새로 만든다. |
| `SkillSourceDiffEntryDto` | `relative_path` string, `status` `"added"｜"removed"｜"modified"`, `content_kind` `"text"｜"binary"｜"too_large"｜"permission_only"`, `original_text`·`updated_text` optional string, `executable_before`·`executable_after` bool | `original_*`은 라이브러리 사본 쪽, `updated_*`는 원본 쪽. 텍스트는 `content_kind == "text"`일 때만 채워지고 그 외는 null. `added`이면 `original_text`는 항상 null, `removed`이면 `updated_text`는 항상 null. 실행 비트는 R-15. 필드 이름은 JSON 키 그대로가 외부 계약이다. |
| `source_label` | string | `source_type` → 표시 이름: `skillssh`→`skills.sh`, `git`→`Git`, `local`→`Local`, `import`→`Imported`, 그 밖→원래 값. diff 명령은 `local`·`import`·`git`·`skillssh`만 통과시키므로 사실상 이 넷. |
| `AppError` | `{kind, message}` JSON, `kind`는 snake_case | 이 기능이 내는 kind: `not_found`, `invalid_input`, `git`, `network`, `cancelled`, `io`, `database`, `internal`. 부분 결과는 없다(성공하면 DTO, 실패하면 오류). |
| 상세 패널 상태 | 탭 `local｜diff｜source`, `sourceDoc`, `sourceDiff`, `sourceDiffFailed`, `sourceLoading` | 상태 전이는 R-21. |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 두 명령 공통 | 둘 다 blocking 스레드에서 실행한다. `skillId`로 DB에서 스킬 행을 읽고 없으면 `not_found`("Skill not found"), DB 읽기 실패는 `database`. DB를 쓰지 않고 `RepoLock`도 잡지 않으므로 같은 시각의 설치·업데이트와 직렬화되지 않는다(비교 중에 사본이 바뀔 수 있다, 아래 불변식). 취소 수단(cancel 플래그)은 전달하지 않는다. | 코드 확인 |
| R-02 | `source_type`으로 처리를 가른다 | `local`·`import`는 R-03, `git`·`skillssh`는 R-05 이하 git 경로. 그 밖(`well-known`, 알 수 없는 값 포함)은 네트워크·파일 접근 없이 `invalid_input`("Skill does not support source diff preview")으로 거절하고 문서 명령도 같다. `well-known`은 "저장소가 없는 웹사이트 스냅샷"이라 비교할 원본이 없다(업데이트 확인도 이 출처는 건드리지 않는다) | 코드 확인 |
| R-03 | `local`·`import`: 원본은 `source_ref`가 가리키는 경로 | `source_ref`가 null이면 `not_found`("Local skill is missing its original source path"). 경로가 존재하지 않으면 `not_found`("Original source path no longer exists"). 있으면 그 경로를 바로 읽는다: 문서 명령은 그 폴더에서 R-12로 문서를 읽고, diff 명령은 `central_path`(old)와 그 폴더(new)를 R-13으로 비교한다. 임시 폴더·네트워크·clone은 없다. `revision`은 `"workspace"`. 원본이 디렉터리인지는 검사하지 않는다. | 코드 확인 |
| R-04 | `local` 출처의 `source_ref`가 `.zip`/`.skill` 파일 | 이 명령들은 압축을 풀지 않고 경로를 폴더처럼 읽는다(업데이트 확인은 `PreparedSource`로 풀어서 비교하는데 이 명령들은 아니다). 문서 명령은 `not_found`("No documentation file found")가 된다(코드 확인: 후보 파일 `파일/SKILL.md`가 없고 걷기가 파일 하나만 본다. 걷기 동작은 추론). diff 명령은 오류 없이 돌아오고, 파일 하나가 `relative_path: ""`인 `added`/`binary` 항목이 되고 사본의 모든 파일이 `removed`로 나올 것이다(추론: `strip_prefix`가 빈 경로를 내는 `list_content_files` 동작과 walkdir의 루트 처리. 실행하지 않음). 프런트엔드는 이 경우에도 탭을 노출한다(R-20). | 코드 확인(호출 경로) / 추론(결과) |
| R-05 | git 계열에서 clone 대상을 구한다(`git_source_from_skill`) | C-07 그대로: ①`source_ref_resolved`가 있으면 그것이 clone URL이고 브랜치=`source_branch`, 하위 폴더=`source_subpath`, locator id=(`skillssh`이면 `source_ref`의 마지막 `/` 뒤 조각, 아니면 없음). ②없으면 `git`은 `source_ref`가 null일 때 `invalid_input`("Git skill is missing its source URL"), 아니면 `parse_git_source(source_ref)`(C-08~C-10)로 URL·브랜치·하위 폴더를 구하되 저장된 `source_branch`·`source_subpath`가 있으면 그쪽이 우선, locator 없음. ③`skillssh`는 `source_ref`가 null이면 `invalid_input`("skills.sh skill is missing its source reference"), 마지막 `/`가 없으면 `invalid_input`("Invalid skills.sh source reference"), 아니면 URL=`https://github.com/<마지막 / 앞>.git`, 브랜치·하위 폴더는 저장된 값, locator=마지막 조각. 이 단계는 DB 값만 읽고 네트워크를 쓰지 않는다. | 코드 확인 |
| R-06 | clone URL | `validate_git_url`(C-11)을 clone·`ls-remote` 전에 통과해야 한다. 허용: `https://`·`http://`·`ssh://`·`git@`로 시작하는 것(대소문자 무시)과 `user/repo`형 축약(스킴 없음, `\` 없음, `/`·`.`·`~`로 시작하지 않음, `/` 포함, Windows 드라이브 경로 아님). 그 밖(`file://`, 로컬 경로 등)은 `git`("URL scheme not allowed: only https, http, ssh, and git@ are permitted"). | 코드 확인 |
| R-07 | 원격 revision 결정(`resolve_remote_revision`) | 후보 ref를 순서대로 찾는다: 브랜치가 지정됐으면 `refs/heads/<이름>`, `refs/tags/<이름>^{}`, `refs/tags/<이름>`, 없으면 `HEAD`(C-13). 먼저 `git ls-remote <url> <후보들>`(프록시는 `-c http.proxy`/`https.proxy`)를 쓰고 출력에서 후보 순서대로 정확한 ref 이름 일치를 고른다(첫 줄을 쓰지 않는다). `ls-remote` 실행이 실패하거나 ref가 없으면 임시 bare 저장소에 anonymous remote를 만들어 libgit2로 같은 후보를 찾는다(저장된 자격증명 사용). 둘 다 못 찾으면 `git`("Unable to resolve remote revision for <url>"). 폴백이 만든 임시 bare 저장소(`skills-manager-remote-<uuid>`)는 코드에서 지우지 않는다. 이 호출에는 별도 시간 제한이 없다. 이 결과가 `revision`이고 이후 checkout 대상이다. | 코드 확인 |
| R-08 | clone과 checkout(git 경로) | `clone_repo_ref_scoped(clone_url, branch, subpath, 취소 없음, 프록시)`로 임시 폴더를 받는다(좁은 clone 시도 후 전체 clone 폴백, 시간 제한 300초는 clone 계층). 실패는 `AppError::classify_git_error`: 메시지에 `cancelled`/`canceled`가 있으면 `cancelled`, `connection refused`·`could not resolve host`·`failed to connect`·`connection timed out`·`network is unreachable`가 있으면 `network`, 그 밖은 `git`(대소문자 무시). 이어서 그 임시 폴더에서 `git checkout --detach <R-07의 revision>`(C-14, 실패하면 libgit2로 같은 일)을 하고, 실패는 `git`. | 코드 확인 |
| R-09 | 스킬 폴더 결정(`resolve_skill_dir`, C-15~C-18) | 하위 폴더가 있으면 `repo/<subpath>`가 체크아웃 밖이면 `invalid_input`("Path '<subpath>' resolves outside the repository"). locator가 있으면 그 폴더가 `SKILL.md`/`skill.md`를 직접 가진 폴더일 때만, 없으면 디렉터리이기만 하면 채택한다. 채택 못 했고 locator가 없으면 `not_found`("Path '<subpath>' does not exist in the repository"). locator가 있으면 `find_skill_dir(repo, locator)`(C-19: `<id>/`, `skills/<id>/`, `.agents/skills/<id>/`, 깊이 6까지 재귀: 폴더 이름 일치+유효 스킬 폴더 즉시 채택, 아니면 `SKILL.md`의 `name`이 id인 첫 폴더. 못 찾으면 `git`("Skill '<id>' was not found in the fetched version of this repository. Check the source and its subpath.")). 하위 폴더도 locator도 없으면 `find_skill_dir(repo, None)`: 루트에 `SKILL.md`/`skill.md`가 있으면 루트, 아니면 `skills/`, 아니면 `skill/`, 아니면 루트. 결과가 체크아웃 밖이면 `invalid_input`("Resolved skill directory is outside the repository"). | 코드 확인 |
| R-10 | 임시 폴더 정리와 실패 전달 | R-08의 clone이 성공해 임시 폴더가 생긴 뒤에는, checkout·폴더 결정·문서 읽기·diff 계산이 성공하든 실패하든 임시 폴더를 `remove_dir_all`(오류 무시)한다. clone 자체가 실패하면 clone 계층이 자기 부분 결과를 지운다. 오류는 변환 없이 그대로 invoke 오류로 나간다. 스레드 패닉 시의 정리는 코드에 없다(추론). | 코드 확인 |
| R-11 | `get_source_skill_document` 결과 | 원본 폴더(로컬은 R-03의 폴더, git은 R-09의 스킬 폴더)에서 R-12로 파일 하나를 `read_to_string`으로 읽어 `{skill_id, filename, content, source_label, revision}`을 돌려준다. 파일이 UTF-8이 아니면 `io`. 문서 명령은 R-02·R-03·R-05~R-10 단계를 diff 명령과 같은 순서·같은 오류로 거치며 R-13 이후는 하지 않는다. | 코드 확인 |
| R-12 | 문서 파일 선택(`read_skill_document_from_dir`, C-06) | 1) 폴더 바로 아래에서 `SKILL.md`, `skill.md`, `CLAUDE.md`, `claude.md`, `README.md`, `readme.md` 순으로 `exists()`인 첫 파일. 2) 없으면 깊이 4까지 걷는 중 이름이 위 여섯 중 하나인 첫 파일(걷기 순서는 정해 두지 않는다). 3) 없으면 `not_found`("No documentation file found"). `filename`은 후보 이름(1단계) 또는 실제 파일 이름(2단계). 대소문자 구분 없는 파일 시스템에서는 `skill.md`만 있는 폴더도 1단계에서 `SKILL.md`로 보고될 수 있다(추론). | 코드 확인 |
| R-13 | diff 범위·방향·순서 | old=`central_path`(라이브러리 사본), new=원본 폴더. 두 폴더를 `list_content_files`(C-03~C-05)로 열거한다: 일반 파일만(심볼릭 링크·디렉터리 제외), 이름이 `.git`·`.DS_Store`·`Thumbs.db`·`.gitignore`·`__pycache__` 중 하나이거나 `.pyc`로 끝나는 파일·폴더와 그 아래는 제외, `node_modules`·`.venv`·`venv`는 제외하지 않는다. 상대 경로는 `/` 구분(Windows에서 변환)이고 UTF-8 변환이 손실될 수 있다. 읽을 수 없는 하위 폴더는 없는 것처럼 건너뛴다(오류 없음). 열거 키의 합집합을 오름차순으로 정렬해 항목을 만든다. `central_path`가 없어도 오류가 아니라 old가 빈 목록이 된다(→ 원본 파일이 전부 `added`). | 코드 확인 |
| R-14 | 한쪽에만 있는 파일 | new에만: `status: "added"`, `executable_before=false`, `executable_after`=원본 파일의 실행 여부, 내용은 R-16으로 분류해 `updated_text`에 넣는다. old에만: `status: "removed"`, 대칭(`original_text`, `executable_after=false`). 파일을 읽지 못하면 내용이 없는 것으로 R-16에서 `binary`가 된다. | 코드 확인 |
| R-15 | 양쪽에 있는 파일 | 두 바이트열을 모두 읽을 수 있고 같으면: 실행 여부(`is_executable`, C-04)도 같으면 항목을 만들지 않고, 다르면 `modified`/`permission_only`(텍스트 null, 실행 플래그만 채움). 바이트가 다르면(또는 한쪽이라도 못 읽으면) `modified`이고 `content_kind`는: 양쪽 `text`이면 `text`(두 텍스트 모두 채움), 아니면 어느 한쪽이 `too_large`이면 `too_large`, 아니면 `binary`(텍스트 null). 두 실행 플래그는 항상 채운다. 실행 여부는 unix에서 `mode & 0o111`이 0이 아닌지이고 Windows에서는 항상 false다. | 코드 확인 |
| R-16 | 내용 분류(`classify_diff_bytes`, `MAX_DIFF_FILE_BYTES = 256*1024`, C-02) | 읽기 실패→`binary`; 길이가 256 KiB(262144바이트)를 **초과**하면 `too_large`(바이너리 여부보다 먼저); NUL 바이트가 있으면 `binary`; UTF-8로 해석되면 `text`; 아니면 `binary`. 이유 주석: 줄 diff가 O(n²)라 큰 파일은 화면을 멈추기 때문에 본문을 보내지 않는다. | 코드 확인 |
| R-17 | 줄바꿈만 다른 파일 | 정규화하지 않는다. CRLF와 LF만 다른 파일은 `modified`/`text`로 나오고 두 텍스트에 `\r`이 그대로 남는다. `differs_only_by_line_endings`는 업데이트 확인(`local_source_status`)에서만 쓰이고 diff 명령은 부르지 않는다. 따라서 업데이트 확인은 "최신"인데 diff는 변경 항목을 보이는 경우가 있다. | 코드 확인 |
| R-18 | 결과 DTO | `entries`가 비면 프런트엔드는 "No changes — the source matches the central library"를 보인다(R-22). `SkillSourceDiffDto.source_label`·`revision`은 채워 보내지만 diff 뷰어는 쓰지 않는다. | 코드 확인 |
| R-19 | 확인한 revision과 clone 결과가 다를 때(R-07 이후 원격이 전진) | R-07에서 얻은 revision A와 달리 clone이 받은 끝이 B이고 B의 depth-1 clone에 A 커밋이 없으면, checkout A가 실패한다. 명령은 `git` 오류로 끝나고 diff는 돌아오지 않는다(임시 폴더는 정리됨, R-10). git CLI 쪽 실패는 실행으로 확인했고, libgit2 폴백이 같은 이유로 실패하는 것과 clone 계층 캐시를 거치는 경우는 추론이다. | 실행 확인(git CLI) / 추론(폴백·캐시) |
| R-20 | UI 노출 조건 | 패널이 `source_type`이 `git`·`skillssh`이거나, `local`·`import`이면서 `source_ref`가 truthy일 때만 Local/Diff/Source 탭과 상태 처리를 켠다. 그 밖(`well-known` 등, `source_ref`가 없는 로컬)에는 탭이 없고 로컬 문서(`get_skill_document`)만 보인다. 백엔드의 R-02는 이 조건과 달리 `source_ref` 존재를 보지 않고 값 검사를 한다. | 코드 확인 |
| R-21 | UI 상태 전이(`SkillDetailPanel`) | 아래 표를 따른다. 실패 이유(`kind`·`message`)는 화면에 쓰이지 않는다. | 코드 확인 |
| R-22 | diff 표시(`SkillSourceDiffViewer`) | 항목당 카드 하나: 상태 배지(Added 초록/Removed 빨강/Modified 파랑), 경로(한 줄 말줄임, 툴팁에 전체), `modified`이고 두 실행 플래그가 다르면 `Permission 0644 → 0755` 형태 배지(false→`0644`, true→`0755`로 고정 표기). `content_kind == "text"`이면 `DocumentDiffViewer`에 `original_text ?? ""`, `updated_text ?? ""`를 넘기고, 그 밖은 요약 한 줄(`binary`: "Binary file changed", `too_large`: "File changed but is too large to preview", `permission_only`: "Only file permissions changed"). 항목이 없으면 R-18의 문구. | 코드 확인 |
| R-23 | 텍스트 줄 diff(`DocumentDiffViewer`, C-19) | 두 텍스트를 `\n`으로 나눠 줄 단위 LCS(동적 계획법 표 (n+1)×(m+1))로 정렬하고, 같은 줄은 context, 왼쪽에만은 removed, 오른쪽에만은 added로 한다. 동점이면 removed를 먼저 낸다. 바뀐 줄 앞뒤 3줄을 포함하고, 간격이 이어지면(`다음 시작 <= 끝 + 1`) 한 hunk로 합친다. hunk마다 `@@ -<시작>,<줄수>`, `@@ +<시작>,<줄수>` 머리를 단다. 변경 줄이 없으면 "No content changes"(하드코딩 영어). 텍스트가 다르면 줄도 달라서 diff 명령이 낸 `text` 항목에서는 이 문구가 나오지 않는다. 줄바꿈은 `\n`만 보므로 `\r`은 줄 내용에 남는다. | 코드 확인 |
| R-24 | CLI | `skills-manager-cli.rs`에 이 기능을 부르는 명령은 없다(`build_source_diff_entries`·`get_skill_source_diff`는 `commands/skills.rs`와 `lib.rs` 등록부에만 있다). | 코드 확인(grep) |

**R-21 상태 전이 (`SkillDetailPanel`, 패널 한 번 마운트 기준)**

| 상태·입력 | 다음 상태 | 보이는 것 |
|---|---|---|
| 마운트, `supportsSourceDiff` | `sourceLoading=true`, 탭 `local`. 원본 문서 요청 1회(요청 번호로 낡은 응답 무시, git 계열이면 이때 ls-remote·clone이 일어난다) | 로컬 문서(`get_skill_document` 결과) 또는 로딩/없음 문구. 로컬 문서가 로딩 중이면 어느 탭이든 로딩 문구가 우선 |
| 원본 문서 응답(성공) | `sourceDoc` 저장, `sourceLoading=false` | Source 탭 활성화, 칩 `<source_label> · <revision 앞 7자>`(로컬은 `workspa`) |
| 원본 문서 응답(실패) | `sourceDoc=null`, `sourceLoading=false` | Source 탭을 누르면 "Source content is unavailable right now" |
| Source 탭 | `sourceLoading` 중에는 버튼이 비활성 | 문서를 `SkillMarkdown`으로 렌더링 |
| Diff 탭을 처음 누름 | `diffRequestedRef=true`, `get_skill_source_diff` 1회 | 로딩 문구 |
| diff 응답(성공, `skill_id` 일치) | `sourceDiff` 저장 | R-22의 뷰어 |
| diff 응답(실패) | `sourceDiffFailed=true` | "Source content is unavailable right now". 같은 마운트 안에서는 재시도하지 않는다 |
| 다른 탭 갔다 Diff로 복귀 | 상태 유지, 재요청 없음 | 저장된 결과 또는 실패 문구 |
| 패널 `key` 변경(스킬 id·`updated_at`·`source_type`·`source_ref`·`source_revision`·`remote_revision` 중 하나가 바뀜) | 컴포넌트 전체 재마운트(모든 상태·diff 캐시 초기화) | 처음 상태 |
| `source_ref_resolved`만 바뀜 | 원본 문서만 다시 요청, diff는 다시 요청하지 않음(낡은 diff가 남을 수 있음) | |

- 불변식: (1) 두 명령은 쓰기가 없다(DB·라이브러리·원본, R-01·R-03). (2) diff는 항상 "라이브러리 사본 → 원본" 방향이다(R-13). (3) `entries`에는 같은 `relative_path`가 한 번만 나오고 오름차순이다. (4) 같은 두 폴더(그 사이 아무도 쓰지 않음)와 같은 revision이면 같은 결과다. 전제: R-01처럼 잠금이 없어 비교 중에 사본이 바뀌면 일부 파일은 옛것, 일부는 새것을 읽을 수 있다(추론).
- 미결정: 없음.
- 확인 한계: Rust 코드를 빌드·실행하지 않았다. R-04의 압축 원본 결과와 walkdir 루트가 파일일 때의 동작은 코드 경로로 추론했다(walkdir 소스는 열지 않았다). R-13의 심볼릭 링크 제외도 walkdir가 기본으로 링크를 따라가지 않는다는 라이브러리 지식에 기댄다. 실제 GitHub·skills.sh 원격이 `ls-remote`·clone에 어떻게 답하는지(태그·SHA 직접 지정·인증)는 확인하지 않았다. clone 계층의 캐시·좁은 clone 내부는 읽기만 했고 이 스펙의 계약은 입력·정상 결과·오류 종류로 한정했다. 이 기능의 원본 테스트는 없다(`classify_diff_bytes`·`build_source_diff_entries` 테스트 이름 검색 결과 없음).

### 1.5 필수 코드 참조

라이선스는 MIT(overview 1절)라 인용을 허용한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src-tauri/src/commands/skills.rs:246-278` `SourceSkillDocumentDto`, `SkillSourceDiffDto`, `SkillSourceDiffEntryDto` | 두 DTO의 필드 이름과 값 집합(주석의 `"added"｜"removed"｜"modified"`, `"text"｜"binary"｜"too_large"｜"permission_only"`) | R-11, R-13~R-16 |
| C-02 | `src-tauri/src/commands/skills.rs:488-603` `MAX_DIFF_FILE_BYTES`, `classify_diff_bytes`, `build_source_diff_entries` | 크기 상한, 분류, 합집합 순회, added/removed/modified/permission_only 판정, `too_large`·`binary` 결합 규칙. 이 함수들은 `list_content_files`(C-03~C-05)와 `ContentEntry::is_executable`(C-04)에만 의존한다. | R-13~R-16 |
| C-03 | `src-tauri/src/core/content_hash.rs:7-16` `IGNORED`, `is_ignored` | 제외 이름 목록과 `.pyc` 규칙 | R-13 |
| C-04 | `src-tauri/src/core/content_hash.rs:45-60` `ContentEntry::is_executable`, `exec_bits_of` | 실행 비트(unix만, `mode & 0o111`, 0이 아니면 실행) | R-13, R-15 |
| C-05 | `src-tauri/src/core/content_hash.rs:80-138` `walk_content_files`(`list_content_files`는 `strict=false, skip_deps=false`로 부름) | 열거 범위·정렬·상대 경로 규칙, 오류 무시. 같은 파일의 `list_content_files`는 `walk_content_files(dir, false, false).unwrap_or_default()`(`content_hash.rs:69-72`)다. | R-13 |
| C-06 | `src-tauri/src/commands/skills.rs:685-722` `read_skill_document_from_dir`, `source_label_for_skill` | 문서 후보 순서, 깊이 4 폴백, 라벨 표 | R-11, R-12, R-18 |
| C-07 | `src-tauri/src/commands/skills.rs:2960-3016` `git_source_from_skill`, `skill_ssh_id` | 컬럼 → clone URL·브랜치·하위 폴더·locator 해석과 오류 문구 | R-05 |
| C-08 | `src-tauri/src/core/git_fetcher.rs:1339-1368` `normalize_url` (`parse_git_source`는 `url.trim()` 뒤 이 함수를 부르는 얇은 래퍼, `:36-46`) | `source_ref`(URL·축약)에서 clone URL을 구하는 규칙 | R-05 |
| C-09 | `src-tauri/src/core/git_fetcher.rs:1466-1481` `parse_github_tree_url`, `parse_github_tree_url_path` | GitHub `…/tree/<경로>` URL에서 clone URL과 `<경로>`를 떼는 정규식 | R-05 |
| C-10 | `src-tauri/src/core/git_fetcher.rs:1536-1545` `split_tree_branch_path` (`parse_github_tree_url`은 빈 목록으로 부르므로 `match_known_ref`는 항상 `None`) | 첫 세그먼트=브랜치, 나머지=하위 폴더 | R-05 |
| C-11 | `src-tauri/src/core/git_fetcher.rs:52-82` `validate_git_url` | 허용 URL 스킴·축약 판정 | R-06 |
| C-12 | `src-tauri/src/core/git_fetcher.rs:1187-1216` `resolve_remote_revision` | 두 단계(git CLI → libgit2) 폴백과 최종 오류 | R-07 |
| C-13 | `src-tauri/src/core/git_fetcher.rs:1650-1681` `candidate_ref_names`, `select_remote_revision`; 그리고 `:1683-1707` `resolve_remote_revision_with_git` | 후보 ref 순서, ls-remote 출력에서 이름 일치로 고르는 규칙, CLI 호출 형식 | R-07 |
| C-14 | `src-tauri/src/core/git_fetcher.rs:1308-1328` `checkout_revision` | `git checkout --detach`와 libgit2 폴백 | R-08, R-19 |
| C-15 | `src-tauri/src/commands/skills.rs:3094-3135` `resolve_skill_dir` | 하위 폴더·locator 우선순위, 체크아웃 밖 거절, 오류 문구 | R-09 |
| C-16 | `src-tauri/src/core/path_guard.rs:84-122` `is_path_safe`, `resolve_non_existing`, `normalize` | "체크아웃 안인가" 판정(정규화, 없는 경로는 가장 가까운 존재하는 조상 기준) | R-09 |
| C-17 | `src-tauri/src/core/skill_metadata.rs:21-29`, `:79-88` `has_named_file_exact`, `is_valid_skill_dir` | 스킬 폴더 표지: 그 폴더 바로 아래 일반 파일 `SKILL.md` 또는 `skill.md`(대소문자 정확히 일치) | R-09 |
| C-18 | `src-tauri/src/core/git_fetcher.rs:1370-1460` `find_skill_dir` | locator 탐색 순서와 없을 때 오류, locator 없음 때의 루트/`skills`/`skill` 규칙 | R-09 |
| C-19 | `src/components/DocumentDiffViewer.tsx:24-136` `CONTEXT_LINES`, `buildDiffRows`, `buildHunks` | 줄 LCS, 동점 처리, hunk 병합. 나머지(`createHunk` `:138-151`)는 hunk 머리 숫자 계산이다. | R-23 |
| C-20 | `src-tauri/src/commands/skills.rs:408-486` `get_source_skill_document`; `:605-683` `get_skill_source_diff` | 두 명령의 단계 순서와 오류 문구의 원본. 위 R-ID가 풀어 쓴 흐름과 같다. | R-01~R-03, R-05~R-11 |

> C-ID 범위 안의 내부 helper 중 이 문서가 풀지 않은 것: `git_command()`(자식 프로세스 생성 래퍼, 외부 계약), `RemoteRefNames`·`match_known_ref`(C-10의 빈 목록 호출에서는 항상 `None`이라 무관), `git_credentials::install_git2_credentials`(R-07 libgit2 폴백의 자격증명, 범위 밖), `PreparedSource`(R-04, 이 기능이 쓰지 않음).

### 1.6 수락 사례

출처: 모두 구현에서 도출(원본 테스트는 없음). T-08만 원본 실행 관찰이 아니라 별도 git 실험(`artifacts/skills-manager/skill-source-diff-demos/`)이다. 로컬 사례는 임시 폴더 두 개로 만든다. 실행 비트 사례는 unix 전용이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | `source_type="well-known"`인 스킬로 두 명령 호출 | 둘 다 `invalid_input`("Skill does not support source diff preview"), 네트워크·파일 접근 없음 |
| T-02 | R-03 | `local` 스킬 `source_ref=null` / `source_ref`가 없는 경로 | 각각 `not_found`("Local skill is missing its original source path") / `not_found`("Original source path no longer exists") |
| T-03 | R-13, R-14, R-15 | 사본 {`SKILL.md`="a\n", `a.txt`="x"}, 원본 {`SKILL.md`="b\n", `new.md`="y"} (local) | `revision="workspace"`, `entries`가 `SKILL.md`(modified/text), `a.txt`(removed/text, `original_text="x"`), `new.md`(added/text, `updated_text="y"`) 순서(대문자 `S`가 소문자보다 앞) |
| T-04 | R-13, R-18 | 사본과 원본이 바이트·실행 비트까지 같음 | `entries=[]`, 뷰어는 "No changes — the source matches the central library" |
| T-05 | R-15 | 같은 내용, 원본만 `chmod +x` (unix) | 한 항목 `modified`/`permission_only`, 텍스트 둘 다 null, `executable_before=false`, `executable_after=true`, 뷰어는 `Permission 0644 → 0755` 배지와 "Only file permissions changed" |
| T-06 | R-16, R-15 | 변경된 파일: ①원본에 NUL 포함 ②정확히 262144바이트 텍스트 ③262145바이트 텍스트 ④사본은 텍스트, 원본은 262145바이트 | ①`binary` ②`text` ③`too_large` ④`too_large`(둘 다 text가 아니고 한쪽이 too_large). 사본 262145바이트 NUL 포함 파일이 원본에 없으면 `removed`/`too_large` |
| T-07 | R-13 | 양쪽에 `.git/x`, `.DS_Store`, `a.pyc`, `__pycache__/b`, `.gitignore`, 원본에만 `node_modules/m.js` | `node_modules/m.js`만 `added`로 나온다 |
| T-08 | R-19 | `ls-remote`로 A를 얻은 뒤 원격에 커밋 B가 추가되고 `--depth 1` clone이 B를 받음 | `git checkout --detach A` 실패(종료 코드 128), `--detach HEAD`는 성공 (`stale-revision-checkout.out`). Rust 명령은 `git` 오류로 끝남(추론) |
| T-09 | R-17 | 같은 줄 내용, 사본 LF·원본 CRLF | `modified`/`text`, 두 텍스트 모두 채워짐, 뷰어에서는 모든 줄이 바뀐 줄로 보임 |
| T-10 | R-16 | 원본 파일이 NUL 없는 비 UTF-8 바이트(`FF FE 41`) | `binary` |
| T-11 | R-05 | `skillssh`, `source_ref="owner/repo/skill-a"`, `source_ref_resolved`=null, `source_branch`=null | clone URL `https://github.com/owner/repo.git`, 브랜치 없음, locator `skill-a`. `source_ref="owner"`이면 `invalid_input`("Invalid skills.sh source reference") |
| T-12 | R-05 | `git`, `source_ref="https://github.com/a/b/tree/dev/x/y"`, 저장 컬럼 모두 null / 같은 조건에서 `source_branch="feature/z"`, `source_subpath="x/y"` | `https://github.com/a/b.git`, 브랜치 `dev`, 하위 폴더 `x/y` / 브랜치 `feature/z`, 하위 폴더 `x/y` |
| T-13 | R-06 | `source_ref_resolved="file:///tmp/r"`인 git 스킬 | `git`("URL scheme not allowed: …"), 프로세스를 띄우지 않음 |
| T-14 | R-09 | 하위 폴더 `../x` / 체크아웃에 없는 폴더 `p`+locator 없음 / `p`+locator `s`이고 저장소에 `skills/s/SKILL.md` 있음 / locator `z`가 어디에도 없음 | `invalid_input`("Path '../x' resolves outside the repository") / `not_found`("Path 'p' does not exist in the repository") / `skills/s` 사용 / `git`("Skill 'z' was not found in the fetched version of this repository. Check the source and its subpath.") |
| T-15 | R-12 | 폴더에 `README.md`만 있고 `sub/SKILL.md`가 있음 / `SKILL.md`와 `README.md` / 후보가 하나도 없음 / `SKILL.md`가 비 UTF-8 | `README.md`(바로 아래가 우선) / `SKILL.md` / `not_found`("No documentation file found") / `io` |
| T-16 | R-20, R-21 | `well-known` 스킬 패널 / `local`+`source_ref` 스킬 패널에서 Diff 탭을 눌렀다 Local로 갔다 다시 Diff / diff 호출이 오류 | 탭이 없다 / `get_skill_source_diff`는 한 번만 호출 / "Source content is unavailable right now", 패널을 닫았다 다시 열기 전에는 재시도 없음 |
| T-17 | R-04 | `local` 스킬 `source_ref="/x/s.zip"` | 문서 명령 `not_found`. diff 명령은 오류 없이 `relative_path ""` 항목과 사본 전체 `removed`(추론, 실행 안 함) |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (repo@7a22192 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | `src-tauri/src/commands/skills.rs:408-420`, `:605-620` (조회·`not_found`), `src-tauri/src/lib.rs:1019-1020` (명령 등록), `src/lib/tauri.ts:69-99`, `:248-252` (TS 타입·invoke 래퍼) | `commands/skills.rs`의 두 함수 본문에 `RepoLock`이 없음을 읽어 확인 |
| R-02 | C-20 (문서 명령 `:421-443` 로컬 분기와 거절, diff 명령 `:621-642`) | 코드 읽기. 거절이 `git_source_from_skill`보다 앞 |
| R-03 | C-20 | 코드 읽기 |
| R-04 | `src-tauri/src/core/installer.rs:17-73` `PreparedSource`(압축은 업데이트 확인 쪽에서만 풂), `src-tauri/src/commands/skills.rs:892-909` `install_local`(`source_ref`=입력 경로 그대로), `:2852-2866` 업데이트 확인의 `hash_local_source`, C-02·C-05·C-06 | 호출 경로는 코드 확인. 결과(`relative_path ""`)는 `strip_prefix` 의미와 walkdir 루트 처리에서 추론, 실행 안 함 |
| R-05 | C-07~C-10 | 코드 읽기. 컬럼 일반 의미는 선행 스펙 |
| R-06 | C-11 | 코드 읽기. 호출은 C-20 |
| R-07 | C-12, C-13 | 코드 읽기. 원격 동작은 확인 한계 |
| R-08 | C-20, `src-tauri/src/core/git_fetcher.rs:567-601` `clone_repo_ref_scoped`, `src-tauri/src/core/error.rs:103-130` `classify_git_error`, C-14 | 코드 읽기. 좁은 clone 조건은 `git_fetcher.rs:624-644` `sparse_pattern`, 폴백 주석 `:567-578` |
| R-09 | C-15~C-18 | 코드 읽기 |
| R-10 | C-20(끝의 `cleanup_temp`), `src-tauri/src/core/git_fetcher.rs:1462-1464` `cleanup_temp`, clone 실패 시 정리: `git_fetcher.rs:767-776` `copy_cached_repo` | 코드 읽기. 패닉 경로는 추론 |
| R-11, R-12 | C-06, C-20 | 코드 읽기. 대소문자 무시 FS는 `Path::exists` 의미에서 추론 |
| R-13 | C-03~C-05, `src-tauri/src/core/git_fetcher.rs:817-819` `copy_dir_contents` 주석("`content_hash` counts only regular files") | 코드 읽기. 심볼릭 링크 제외는 `entry.file_type().is_file()`(C-05)와 이 주석으로 확인 |
| R-14, R-15 | C-02, C-04 | 코드 읽기. 부분 실행 비트(예: `0o100` 대 `0o111`)는 해시 쪽은 비트값을 그대로 넣지만(`content_hash.rs:146-153`) diff는 `is_executable` 불리언만 비교한다 |
| R-16 | C-02 | 코드 읽기 |
| R-17 | `src-tauri/src/commands/skills.rs:2888-2903` `local_source_status`, `:2923-2931` `differs_only_by_line_endings`, `grep`으로 호출처가 이 한 곳뿐임을 확인, `CHANGELOG.md:166` | 문서(CHANGELOG)는 "Line endings alone no longer count as a difference"라고 쓰지만 대상은 업데이트 확인이다. diff 명령은 이 함수를 부르지 않는다(코드가 사실) |
| R-18 | C-02, C-20, `src/components/SkillSourceDiffViewer.tsx:17-24`, `src/i18n/en.json:340-353` | 코드 읽기 |
| R-19 | C-14, C-20, `artifacts/skills-manager/skill-source-diff-demos/stale-revision-checkout.sh` / `.out` | git CLI 부분만 실행 확인(file:// 임시 저장소, 네트워크 없음). Rust 폴백(`Oid::from_str` + `set_head_detached`)이 같은 이유로 실패하는지는 추론 |
| R-20 | `src/components/SkillDetailPanel.tsx:109-113` `supportsSourceDiff` | 코드 읽기 |
| R-21 | `src/components/SkillDetailPanel.tsx:54-61`(패널 key), `:99-183`(상태·효과), `:331-385`(렌더) | 코드 읽기. 실행하지 않음 |
| R-22 | `src/components/SkillSourceDiffViewer.tsx:11-69`, `src/i18n/en.json:340-353` | 코드 읽기 |
| R-23 | C-19, `src/components/DocumentDiffViewer.tsx:212-222` | 코드 읽기 |
| R-24 | `grep -n diff src-tauri/src/bin/skills-manager-cli.rs`에 해당 호출 없음, `src-tauri/src/lib.rs:1019-1020` | 검색 결과로 확인 |
| T-01~T-07, T-09~T-17 | 해당 R-ID의 근거 | 구현에서 도출. 실행하지 않음 |
| T-08 | `artifacts/skills-manager/skill-source-diff-demos/stale-revision-checkout.out` | 실행 확인(git CLI) |

**문서와 구현의 차이**
- 요청문·지도는 원본 문서를 `SKILL.md`/`README.md`로 적지만 구현은 여섯 이름(`SKILL.md`, `skill.md`, `CLAUDE.md`, `claude.md`, `README.md`, `readme.md`)과 깊이 4 탐색이다(R-12).
- `SkillSourceDiffDto` 주석(`skills.rs:255-257`)은 "배지가 update available인데 diff가 비는 일이 없다"고 쓴다. 구현은 (a) 업데이트 확인이 줄바꿈 차이를 무시하지만 diff는 아니고(R-17, 반대 방향의 불일치), (b) 해시는 실행 비트 값 전체를 접는데 diff는 "하나라도 켜졌는가"만 비교하며(R-15), (c) git 출처 배지는 content hash가 아니라 revision 비교 기반이라 이 주석이 보장하지 않는다(그쪽은 update check 스펙에서 다룬다, 이 문서는 확인하지 않음).
- 업데이트 확인은 `.zip`/`.skill` 로컬 원본을 풀어 비교하지만 diff 명령은 풀지 않는다(R-04).
- 없는 원본 경로를 `source_missing`으로 기록하는 건 업데이트 확인의 일이고 diff는 `not_found` 오류만 낸다(R-03).

### 2.2 코드 읽는 순서

1. `commands/skills.rs`의 `get_skill_source_diff`(C-20)를 위에서 아래로: 로컬 분기 → 타입 거절 → `git_source_from_skill`(C-07) → `validate_git_url`(C-11) → `resolve_remote_revision`(C-12/C-13) → `clone_repo_ref_scoped` → `checkout_revision`(C-14) → `resolve_skill_dir`(C-15/C-18) → `build_source_diff_entries`(C-02, 열거는 C-05) → `cleanup_temp`.
2. 문서 명령은 같은 뼈대에 마지막이 `read_skill_document_from_dir`(C-06)로 바뀐다. 두 명령이 거의 복제본이라 한쪽을 고치면 다른 쪽도 확인해야 한다.
3. 화면은 `SkillDetailPanel.tsx`(R-20/R-21) → `SkillSourceDiffViewer.tsx`(R-22) → `DocumentDiffViewer.tsx`(R-23). `DetailSheet.tsx`는 제목·메타·본문을 담는 오른쪽 시트 껍데기(Esc/바깥 클릭으로 닫기)일 뿐 diff 계약과 무관하다(열어 보기만 함, sources에 넣지 않음).

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 아직 없다. 원본 코드를 복사해 돌린 일은 없다. `artifacts/skills-manager/skill-source-diff-demos/stale-revision-checkout.sh`는 Rust 코드를 쓰지 않고 git CLI로 R-19의 git 쪽 동작만 재현한다.
