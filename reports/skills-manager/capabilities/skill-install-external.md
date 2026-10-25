---
sha: "7a2219219287f4ef4c543fc169ebcc5b0bff085c"
created: 2026-10-24
updated: 2026-10-24
sources:
  - src-tauri/src/commands/skills.rs
  - src-tauri/src/core/git_fetcher.rs
  - src-tauri/src/core/git_command.rs
  - src-tauri/src/core/installer.rs
  - src-tauri/src/core/well_known.rs
  - src-tauri/src/core/scanner.rs
  - src-tauri/src/core/skill_metadata.rs
  - src-tauri/src/core/skill_store.rs
  - src-tauri/src/core/sync_metadata.rs
  - src-tauri/src/core/sync_engine.rs
  - src-tauri/src/core/content_hash.rs
  - src-tauri/src/core/path_guard.rs
  - src-tauri/src/core/repo_lock.rs
  - src-tauri/src/core/install_cancel.rs
  - src-tauri/src/core/error.rs
  - src-tauri/src/core/migrations.rs
  - src-tauri/src/bin/skills-manager-cli.rs
  - src/lib/tauri.ts
  - src/views/InstallSkills.tsx
  - src/components/AgentControlSetupCard.tsx
  - README.md
  - skills/manage-skills/SKILL.md
depends:
  - ../capabilities/skill-source-metadata.md
status: ready
reimplementation: 미실행
---

# 외부 스킬 설치 (Git 저장소 · skills.sh · well-known 사이트)

> Git URL(또는 `owner/repo`), skills.sh 항목(`source` + `skill_id`), skills.sh 웹사이트 스킬 주소(`https://skills.sh/site/<domain>/<skill>`)를 받아 원본을 OS 임시 폴더로 내려받고, (Git은 미리보기로 스킬 목록을 보여 준 뒤) 고른 스킬을 중앙 라이브러리 폴더에 복사하고 출처 메타데이터와 함께 DB에 기록한다.

용어: **스킬 폴더** = `SKILL.md` 또는 `skill.md` 파일이 직접 들어 있는 폴더. **라이브러리 폴더** = `central_repo::skills_dir()`(기본 `~/.skills-manager/skills`). **임시 체크아웃** = OS 임시 폴더 아래에 만든 원본 사본. **출처 컬럼** = 선행 스펙이 의미를 소유하는 `source_type`, `source_ref`, `source_ref_resolved`, `source_subpath`, `source_branch`, `source_revision`, `remote_revision`, `update_status`.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

대표 흐름은 앱의 Git 미리보기 → 확정이다. 다른 경로와의 차이는 1.3의 경로 표와 R-12 이후에 있다.

1. 사용자가 URL을 준다. skills.sh 사이트 주소로 읽히면 well-known 경로, 아니면 git 경로다(R-01).
2. `preview_git_install`이 URL을 `clone_url`·`branch`·`subpath`로 나누고(R-03) 임시 체크아웃을 만든다(R-04). 진행 이벤트 `install-progress`가 나간다(R-21).
3. 체크아웃 안에서 스킬 폴더를 정하고 열거해(R-05, R-06) `{temp_dir, skills:[{rel_path, name, description}]}`를 돌려준다. 임시 체크아웃은 남는다(R-07).
4. 사용자가 항목을 고르고 이름을 고친다. 닫으면 `cancel_git_preview`가 임시 체크아웃을 지운다(R-11).
5. `confirm_git_install`이 `temp_dir`을 검증하고(R-11) URL을 다시 파싱해 같은 방식으로 열거한 뒤, 락을 잡고 선택 항목마다 이름을 정해(R-13) 라이브러리 폴더에 복사하고 DB에 기록한다(R-16, 값은 1.3 표). 중간에 실패하면 거기서 멈추고 앞서 끝낸 항목은 남는다(R-09, R-23).
6. 성공·실패와 무관하게 임시 체크아웃을 지운다(R-09).

### 1.2 범위·통합 지점

- 제공: 위 세 종류 입력을 라이브러리로 입고하는 앱 명령(`install_git`, `preview_git_install`, `confirm_git_install`, `cancel_git_preview`, `install_from_skillssh`, `cancel_install`), 사이트 스킬 내부 함수(`install_site_skill`, `install_site_skill_dir`), CLI `skills install`이 같은 경로를 부르는 방식, 설치 이름 충돌 처리, 임시 폴더 검증·정리, 진행 이벤트, 취소, 오류 분류.
- 제외:
  - 로컬 폴더·압축 설치(`install_local`, `installer::PreparedSource`의 `.zip`/`.skill` 처리)와 `batch_import_folder`: 사용자 범위 밖. 이 스펙의 설치 경로는 항상 폴더를 입력으로 받아 압축 분기에 닿지 않는다(R-13).
  - 에이전트 배포(sync). CLI `--sync*`가 프리셋 id를 넘기는 데서 멈추고, 그 뒤 프리셋 동기화 효과는 다른 스펙이다(R-16).
  - 설치 후 업데이트 확인·적용·diff. 같은 `clone_repo_ref_scoped`, `resolve_skill_dir`을 쓰지만 호출 맥락이 다르다.
  - skills.sh 리더보드·검색(`skillssh_api.rs`). 설치 경로는 이 모듈을 부르지 않고, 목록이 준 문자열 쌍 `(source, skill_id)`만 받는다.
- 외부 의존·선행 계약:
  - 선행 스펙 `skill-source-metadata`: 출처 컬럼의 일반 의미, `source_type` 값 정의, 읽기·쓰기 규칙. 이 스펙은 설치가 각 컬럼에 쓰는 값만 정한다.
  - 중앙 라이브러리·상태(별도 공유 계약, 미작성): 아래 항목은 입력·결과만 이 스펙에서 정의한다.
    - 쓰기 락 `RepoLock::acquire_foreground(작업명)`: 파일 락 `<base_dir>/.skills-manager.lock`을 50ms 간격으로 최대 20초 시도하고, 못 잡으면 `skills repository is busy: <작업명>` 오류(`repo_lock.rs:25-73`).
    - SQLite `skills` 테이블: `id TEXT PRIMARY KEY`, `central_path TEXT NOT NULL UNIQUE`(`migrations.rs:71-91`). `(source_type, source_ref)`에는 유일 제약이 없다.
    - 내용 해시 `hash_directory(dir) -> string`: 스킬 폴더 안 일반 파일(`C-32` 무시 목록 제외, 심볼릭 링크 제외)을 경로순으로 정렬해 상대경로·내용·실행 비트를 SHA-256 hex로 만든다. 이 스펙은 "같은 내용이면 같은 문자열"로만 쓴다.
    - 메타데이터 파일 전체 재작성 `write_all_from_db_unlocked(store)`: DB 기록 직후 호출한다. 파일 위치·포맷·오래된 파일 삭제는 `skill-source-metadata` R-11, R-18이 소유한다.
  - 시스템 `git`(없거나 실패하면 libgit2), 네트워크, 설정 `proxy_url`(빈 문자열은 "없음"), 자격증명(`git_credentials`, 이 스펙 밖).
  - 외부 서비스가 클라이언트 가정대로 동작한다는 전제: GitHub류 git 서버, skills.sh `/site/<domain>/<skill>`, 사이트의 `.well-known/agent-skills/index.json` 또는 `.well-known/skills/index.json`.
- 소유 상태·부작용:
  - 라이브러리 폴더 아래 새 스킬 폴더(복사본), DB `skills` 행 insert 또는 update, 메타데이터 파일 재작성, 감사 로그 행(R-24).
  - OS 임시 폴더: `skills-manager-clone-<uuid>`(git), `skills-manager-well-known-<임의>`(사이트). 앱 메모리의 취소 레지스트리(R-22).
  - 원본의 git 캐시 `<base_dir>/cache/repos/…`는 속도 최적화다. 관찰되는 설치 결과는 같다(추론). 재구현은 필수가 아니다(2.2).

### 1.3 인터페이스와 데이터 의미

**앱 명령** (Tauri `invoke`, JS 쪽 인자는 camelCase — `src/lib/tauri.ts:273-306`)

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `install_git` | `repo_url: string`, `name?: string` → `void` | 미리보기 없이 하나를 설치(R-12). 입력이 사이트 주소면 R-18. UI에서는 Agent 제어 카드가 트리 URL로 부른다 |
| `preview_git_install` | `repo_url` → `{temp_dir: string, skills: [{rel_path: string, name: string, description?: string}]}` | 열거만 한다(R-07, R-08). `temp_dir`은 호출자가 `confirm` 또는 `cancel_git_preview`로 돌려줘야 지워진다 |
| `confirm_git_install` | `repo_url`, `temp_dir`, `items: [{rel_path, name}]` → `void` | `rel_path`로 미리보기 항목을 고르고 `name`을 설치 이름 후보로 쓴다(R-09, R-10) |
| `cancel_git_preview` | `temp_dir` → `void` | 항상 성공(R-11) |
| `install_from_skillssh` | `source: string`, `skill_id: string` → `void` | `source`에 `/`가 있으면 GitHub `owner/repo`(R-14), 없으면 사이트 도메인(R-18) |
| `cancel_install` | `key: string` → `bool` | 등록된 작업이면 취소 플래그를 세우고 `true`(R-22) |
| 이벤트 `install-progress` | `{skill_id: string, phase: "cloning" 또는 "installing" 또는 "done", detail?: string}` | R-21 |
| 오류 | `{kind: snake_case enum, message: string}` | `kind`: `database, io, network, git, not_found, invalid_input, cancelled, internal, target_conflict`(`C-29`). 설치 경로는 `target_conflict`를 만들지 않는다. R-20 |

**CLI** `skills-manager-cli [--json] skills install <reference> [--local 또는 --git 또는 --skillssh] [--name N] [--sync 또는 --sync-preset REF]`. 세 종류 플래그는 서로 배타(clap). 성공 출력 `InstallReport{ok:true, skill_id, name, central_path, source_type, synced: bool, preset_id?: string}`. R-25, R-26.

**내부 데이터**

| 데이터 | 의미 |
|---|---|
| `ParsedGitSource{original_url, clone_url, branch?, subpath?}` | `original_url`은 입력을 trim한 값. `branch`는 GitHub 트리 URL에서 나온 ref 이름(브랜치 또는 태그), 없으면 기본 브랜치 |
| `InstallSourceMetadata` | 출처 컬럼 8개의 묶음. 경로별 값은 아래 표 |
| `InstallResult{name, description?, central_path, content_hash}` | `name`은 최종 라이브러리 폴더 이름. `description`은 원본 `SKILL.md` frontmatter의 값 |
| 취소 키 | `install_git`·`preview_git_install` = `repo_url` 원문, `install_from_skillssh` = `<source>/<skill_id>` |
| `rel_path` | 열거 기준 폴더(R-06)에서의 상대경로, 구분자 `/`. 기준 폴더 자신이면 그 폴더 이름 |

**설치 경로별 출처 컬럼 기록값** (값의 일반 의미는 선행 스펙. 열: A=git 직접(`install_git`, CLI `--git`), B=git 확정(`confirm_git_install`), C=skills.sh 저장소(`install_from_skillssh`, CLI skillssh), D=well-known 직접(`install_site_skill`, CLI), E=well-known 확정(`confirm_git_install`의 사이트 분기))

| 컬럼 | A | B | C | D | E |
|---|---|---|---|---|---|
| `source_type` | `git` | `git` | `skillssh` | `well-known` | `well-known` |
| `source_ref` | trim한 입력 URL(`original_url`) | `repo_url` 원문(trim 안 함) | `<source>/<skill_id>` | 정규화한 `https://skills.sh/site/<domain>/<skill>` | D와 같음 |
| `source_ref_resolved` | `clone_url` | `clone_url` | `https://github.com/<source>.git` | 실제로 받은 파일 URL(v2: 인덱스 URL 기준으로 푼 `entry.url`, v1: `<인덱스 폴더>/<skill>/SKILL.md`) | 사용자가 준 URL 원문 |
| `source_subpath` | 체크아웃 루트 기준 스킬 폴더 상대경로, 루트면 NULL | 같음(각 항목의 폴더) | 같음 | NULL | NULL |
| `source_branch` | `parsed.branch`(없으면 NULL) | `parsed.branch` | NULL | NULL | NULL |
| `source_revision` | 체크아웃 `HEAD` 커밋 SHA | 같음 | 같음 | v2에서 `entry.digest`가 있으면 그 문자열(`sha256:<hex>`), 아니면 NULL(v1은 항상 NULL) | NULL |
| `remote_revision` | `source_revision`과 같은 값 | 같음 | 같음 | `source_revision`과 같은 값 | NULL |
| `update_status` | `up_to_date` | `up_to_date` | `up_to_date` | `local_only` | `local_only` |

- `source_subpath`는 OS 경로 문자열을 그대로 쓴다(Windows는 `\`). `rel_path`만 `/`로 정규화한다(`C-08`, `C-11`).
- 출처 컬럼 외 신규 행 기본값은 R-16.

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 앱 명령 `install_git`, `preview_git_install`, `confirm_git_install`에 입력 `repo_url` | `is_site_ref`(`C-23`: 호스트가 `skills.sh` 또는 `www.skills.sh`이고 경로가 정확히 `/site/<domain>/<skill>`이며 두 세그먼트가 안전 세그먼트)가 참이면 well-known 경로, 거짓이면 git 경로. 안전 세그먼트는 ASCII 영숫자·`.`·`-`만, 처음·끝이 `.`·`-`이면 안 됨. 임의 사이트 URL을 직접 받지 않는다: 도메인은 skills.sh URL 안에 들어 있다 | 코드 확인 |
| R-02 | git 경로 입력 검증 | `validate_git_url`(`C-01`)은 `install_git`과 CLI git 경로에서만 호출된다. `preview_git_install`·`confirm_git_install`은 호출하지 않는다(호출 위치 전수 검색). 실패는 `git` kind, 메시지 `URL scheme not allowed: only https, http, ssh, and git@ are permitted` | 코드 확인 |
| R-03 | git 입력을 `ParsedGitSource`로 분해 | `parse_git_source_resolved`(`C-02` ~ `C-05`). `https://github.com/<o>/<r>/tree/<path>`만 `branch`·`subpath`를 만든다. `<path>`에 `/`가 있을 때만 `git ls-remote --heads --tags <clone_url>`로 원격 ref 목록을 받아 브랜치 우선·최장 일치로 나누고, 호출 실패·빈 결과면 첫 세그먼트=브랜치, 나머지=subpath로 둔다. `ls-remote`에는 제한시간·취소가 없다. `confirm_git_install`은 URL을 다시 파싱하므로 미리보기와 결과가 달라질 수 있다(원격 ref 변화) | 코드 확인 (달라질 수 있다는 결과는 추론) |
| R-04 | git 임시 체크아웃 만들기 | `clone_repo_ref_scoped`(`C-06`): `subpath`가 `sparse_pattern`을 통과하면 좁은 체크아웃(`git clone --filter=blob:none --no-checkout --sparse --depth 1 [--branch B]` 후 `sparse-checkout set --cone <subpath>`, `checkout`)을 먼저 시도한다. 결과가 정확히 `<subpath>`에 스킬 폴더를 가진 경우만 성공으로 보고, 취소가 아닌 모든 실패는 전체 체크아웃으로 폴백한다. 전체 체크아웃은 `git clone --depth 1 [--branch B] <url>`을 먼저 하고, 시스템 git이 없거나 실패하면 libgit2 깊이 1 clone, `branch`가 태그이면 태그만 fetch해 분리 HEAD로 체크아웃한다. 프록시는 `-c http.proxy=P -c https.proxy=P`로 넘긴다. 제한시간 300초, 초과 시 `Git clone timed out after 300s — check your network connection`(좁은 체크아웃 쪽 메시지는 `git timed out after 300s`). 결과는 `<OS 임시>/skills-manager-clone-<uuid>`이며 `.git`이 있고 `HEAD`가 받은 커밋이다. 자식 `git`은 PATH의 `git`이고 Linux AppImage(`APPDIR` 설정)에서는 `LD_LIBRARY_PATH`를 상속하지 않는다 | 코드 확인 |
| R-05 | 체크아웃 안에서 스킬 폴더 결정 `resolve_skill_dir(repo_dir, subpath?, skill_id?)` | `C-10`, `C-09`. `subpath`가 있으면 후보 `repo_dir/subpath`가 `repo_dir` 밖이면(`is_path_safe`: 양쪽 canonicalize, 없는 경로는 존재하는 조상까지 올려 해석한 뒤 접두사 비교) `invalid_input`(`Path '<subpath>' resolves outside the repository`). `skill_id`가 없으면 후보가 디렉터리이면 채택, 아니면 `not_found`(`Path '<subpath>' does not exist in the repository`)이며 **스킬 폴더 여부는 검사하지 않는다**. `skill_id`가 있으면 후보가 스킬 폴더일 때만 채택하고 아니면 `find_skill_dir`로 간다. `find_skill_dir`의 오류는 `git` kind, 결과가 `repo_dir` 밖이면 `invalid_input`. `skill_id`도 `subpath`도 없으면 루트에 `SKILL.md`/`skill.md`가 있을 때 루트, 아니면 `skills/` 디렉터리, 아니면 `skill/`, 아니면 루트(검사 없음) | 코드 확인 |
| R-06 | 열거 `collect_git_skill_dirs(skill_dir)`와 미리보기 항목 | `C-11`, `C-12`. `skill_dir`이 스킬 폴더이면 `[skill_dir]`. 아니면 재귀로 스킬 폴더를 모으되 스킬 폴더를 만나면 그 아래로 내려가지 않고, `.hub`·`.git`·`node_modules`와 라이브러리 폴더를 가리키는 심볼릭 링크는 건너뛰며, 심볼릭 링크 디렉터리는 따라 들어간다(순환은 canonical 경로 집합으로 차단, 경로 안전 검사 없음). 결과는 경로순. 항목 `name` = `SKILL.md` frontmatter `name`(없거나 공백뿐이면 폴더 이름), `description` = frontmatter `description`(`C-14`). `skill_dir`이 R-05의 `skills/` 폴백이면 그 밖에 있는 스킬은 열거되지 않는다 | 코드 확인 |
| R-07 | `preview_git_install` git 경로 | 취소 토큰 등록(키 = `repo_url`), 이벤트 `cloning` 방출, URL 분해(R-03), 임시 체크아웃(R-04, 오류는 R-20 분류), 스킬 폴더 결정(R-05), 열거(R-06). 열거가 비어도 성공으로 `skills: []`와 `temp_dir`을 돌려주고 임시 체크아웃을 남긴다. 스킬 폴더 결정에서 실패하면 임시 체크아웃을 지우고 오류. 설치·DB 변경·락 없음 | 코드 확인 |
| R-08 | `preview_git_install` 사이트 경로 | 이벤트 `cloning` 방출(`detail` 없음), `download_site_skill`(R-17, 모든 실패는 `network` kind), 취소 플래그가 서 있으면 `cancelled`(`Installation cancelled by user`), 다운로드 폴더의 `skill/`을 R-06으로 열거. 결과는 사실상 항목 하나(`rel_path` = `skill`, `name` = frontmatter `name` 또는 `skill`). 열거가 비면 `not_found`(`Downloaded source contains no skills`)이나 다운로드가 `SKILL.md` 존재를 이미 확인하므로 정상 경로에선 닿지 않는다(추론). 오류이면 임시 폴더를 지운다 | 코드 확인 |
| R-09 | `confirm_git_install` git 경로 | 순서: `validate_clone_temp_path`(R-11) → `items`가 비면 아무것도 설치하지 않고 성공 → URL 재파싱(R-03) → R-05, R-06 재실행 → `HEAD` 커밋 읽기(실패 시 `git` kind) → 락(`confirm git install`) → 열거 결과를 순서대로 돌며 `items`에서 `rel_path`가 같은 첫 항목이 있는 폴더만 설치(없는 `rel_path`는 조용히 무시, 모두 무시돼도 성공). 항목마다 `name`을 trim해 비면 이름 미지정, 아니면 그 값을 설치 이름 후보로 `install_from_git_dir`(R-13) → 표 B 값으로 R-16. 항목이 실패하면 즉시 중단하고 오류를 돌려주며, 앞서 끝낸 항목은 폴더·DB 행이 남는다. 성공·실패 모두 `temp_dir`을 지우므로 같은 `temp_dir`로 다시 확정하면 `Clone session expired, please try again`. 진행 이벤트와 감사 로그는 없다 | 코드 확인 |
| R-10 | `confirm_git_install` 사이트 경로 | `validate_clone_temp_path` → `items`가 비면 성공 → `skill_dir_from_temp`(`<temp>/skill`에 `SKILL.md` 일반 파일이 있어야 하며, 없으면 `invalid_input` `Downloaded skill is missing SKILL.md`) → 열거(R-06) → 락(`confirm website skill install`) → 일치 항목마다 `install_site_skill_dir`(R-18의 이름·충돌·기록 규칙)에 `name = item.name`, `resolved_url = repo_url` 원문, `revision = None`을 넘긴다. 따라서 표 E 값이다(`source_ref_resolved`는 입력 URL, 리비전 NULL). 설치 이름은 `item.name`(trim, 비면 무시, `sanitize_skill_name` 실패 시 `invalid_input` `Invalid skill name: '<n>'`)이고 비면 사이트의 `<skill>`이다. 성공·실패 모두 임시 폴더 삭제 | 코드 확인 |
| R-11 | `validate_clone_temp_path(temp_dir)`와 `cancel_git_preview` | 경로가 없으면 `invalid_input` `Clone session expired, please try again`. 있으면 canonicalize하고, OS 임시 폴더(canonicalize) 아래이며 마지막 폴더 이름이 `skills-manager-clone-` 또는 `skills-manager-well-known-`으로 시작할 때만 통과(`C-13`), 아니면 `invalid_input` `Invalid temp directory`. `cancel_git_preview`는 통과한 경로만 지우고, 검증 실패는 무시하며 항상 성공을 돌려준다. 라이브러리 폴더·DB는 건드리지 않는다 | 코드 확인 |
| R-12 | `install_git` git 경로(앱)와 CLI `--git` 직접 설치 | 순서: `validate_git_url`(R-02) → R-03 → R-04 → 락(`install git skill`) → `resolve_skill_dir(…, subpath, None)`(R-05) → `HEAD` 커밋 → `install_from_git_dir(skill_dir, name)`(R-13) → 표 A 값으로 R-16 → 임시 체크아웃 삭제(성공·실패 무관). **열거하지 않고 R-05가 정한 폴더 하나를 한 스킬로 설치하며 스킬 폴더 여부를 검사하지 않는다.** 그래서 루트에 `SKILL.md`가 없는 레포 URL을 주면 `skills/`(또는 `skill/`, 없으면 체크아웃 루트) 폴더 전체가 한 스킬로 복사되고, 이름은 폴더 이름이다(루트면 임시 폴더 이름 `skills-manager-clone-<uuid>`). 트리 URL이 컨테이너 폴더를 가리켜도 같다. 이 결과는 경로를 따라 읽었고 실행하지 않았다 | 코드 확인 |
| R-13 | git 계열 설치 이름·충돌·복사 (`install_from_git_dir` = `install_from_local`, 폴더 입력) | `C-16` ~ `C-18`, `C-15`. 이름: 후보가 비어 있지 않으면 `sanitize_skill_name`(실패 시 `io` kind `Invalid skill name: '<n>'`), 아니면 `infer_skill_name`(frontmatter `name`을 sanitize한 값, 불가하면 폴더 이름). 목적지: `<라이브러리>/<name>`이 없으면 그것, 있고 내용 해시가 소스와 같으면 그 폴더, 아니면 `<name>-2`, `-3`, … (**파일시스템만 보고 DB는 보지 않는다**). 설치: 소스와 목적지가 같거나 서로 포함하면 거부(`ensure_dst_not_inside_src`, 임시 체크아웃과 라이브러리는 서로소라 정상 경로에선 닿지 않음), 목적지가 있으면 통째로 삭제하고 복사(`.git`, `.DS_Store`, 심볼릭 링크 제외), 해시 계산, 결과 `name` = 최종 폴더 이름. 따라서 같은 내용을 다시 설치하면 같은 폴더·같은 레코드(R-16 갱신), 내용이 바뀐 같은 스킬을 다시 설치하면 새 폴더 `-2`와 새 레코드가 생기고 기존 레코드는 그대로다. 같은 내용을 다른 출처에서 설치해도 폴더가 같으면 기존 레코드의 출처 컬럼이 새 출처 값으로 덮인다 | 코드 확인 |
| R-14 | `install_from_skillssh`(`source`에 `/` 있음)와 CLI skillssh | 취소 토큰(키 `<source>/<skill_id>`), `cloning`, `https://github.com/<source>.git`을 branch·subpath 없이 전체 체크아웃(R-04 전체 경로, `validate_git_url` 호출 없음), `installing`, 락(`install skillssh skill`), `resolve_skill_dir(None, Some(skill_id))`: `find_skill_dir`(`C-09`)가 `<id>`, `skills/<id>`, `.agents/skills/<id>` 순으로 스킬 폴더를 찾고, 없으면 깊이 6까지 재귀해 폴더 이름이 `<id>`인 스킬 폴더(즉시 채택) 또는 frontmatter `name`이 `<id>`인 첫 폴더를 채택하며, 없으면 `git` kind 오류 `Skill '<id>' was not found in the fetched version of this repository. Check the source and its subpath.`. 이어서 `HEAD` 커밋, 이름·목적지 결정(R-15), `install_skill_dir_to_destination`(`C-17`), 표 C 값으로 R-16. 임시 체크아웃 삭제. 설치 이름은 frontmatter가 아니라 `skill_id`(trim만, sanitize 안 함)이거나 기존 레코드 이름이다. 후보가 여럿이면 선택은 파일시스템 순회 순서에 의존한다(원본 주석도 비결정적이라고 적음) | 코드 확인 |
| R-15 | skills.sh·well-known 설치 이름 결정 `resolve_install_target(source_type, source_ref, base_name)` | `C-19`. `(source_type, source_ref)`가 같은 레코드가 있으면(여러 개면 임의의 첫 행) 그 레코드의 이름과 `central_path`를 그대로 쓴다(폴더 내용 교체, `id` 유지, 사용자가 준 이름은 무시). 없으면 `base_name.trim()`이 비었을 때 `invalid_input` `Skill id is empty`, 아니면 `<name>`, `<name>-2`, … 중 파일시스템에 없고 DB `central_path`에도 없는 첫 이름. 기록 없는 폴더는 내용이 같아도 재사용하지 않고 건너뛴다(R-13과 다름). 이 경로는 `install_skill_dir_to_destination`이 목적지를 통째로 지우고 다시 복사한다 | 코드 확인 |
| R-16 | DB 기록 `store_installed_skill_unlocked(result, metadata, active_scenario_id?)` | `C-20`, `C-21`. `central_path`가 같은 레코드가 있으면 갱신: `name`, `description`, `source_type`·`source_ref`·`source_ref_resolved`·`source_subpath`·`source_branch`·`source_revision`·`remote_revision`, `content_hash`, `update_status`를 새 값으로, `updated_at`·`last_checked_at` = 현재 ms, `status` = `ok`, `last_check_error` 비움. `id`, `enabled`, `created_at`은 유지. 없으면 insert: `id` = UUID v4, `enabled` = true, `created_at` = `updated_at` = `last_checked_at` = 현재 ms, `status` = `ok`, `last_check_error` 없음. 그 뒤 메타데이터 파일을 전체 재작성한다. 앱의 모든 설치 경로는 `active_scenario_id = None`이라 프리셋에 넣지 않는다. CLI `--sync`/`--sync-preset`만 프리셋 id를 넘기며, 그러면 `add_skill_to_scenario` 후 프리셋 동기화를 시도하고 동기화 실패는 경고 로그만 남기고 설치는 성공한다 | 코드 확인 |
| R-17 | 사이트 스킬 내려받기 `download_site_skill(url, proxy)` | `C-22` ~ `C-26`. `<domain>`의 `https://<domain>/`에서 `.well-known/agent-skills/index.json`, 이어 `.well-known/skills/index.json`을 순서대로 시도한다. 연결 실패·비성공 상태·본문 읽기 실패·JSON 아님·`skills` 배열 없음이면 다음 후보로 가고, 둘 다 안 되면 `No supported skills index found at https://<domain>/`. 배열에서 `name == <skill>` 항목이 없으면 `Skill '<skill>' was not found at https://<domain>/`. 인덱스에 `$schema` 키가 있으면 v2(`type`이 `skill-md`면 파일 하나를 `SKILL.md`로, `archive`면 zip을 풀고, `digest`가 있으면 `sha256:<hex>` 일치 검사), 없으면 v1(`files` 목록을 `<인덱스 폴더>/<skill>/<file>`에서 하나씩 받음). 모든 요청은 리다이렉트 포함 HTTPS만, 요청당 30초 제한, 한도·경로 규칙은 `C-26`. 결과는 `<OS 임시>/skills-manager-well-known-<임의>/skill/`에 `SKILL.md`가 있는 폴더이며 어느 단계든 실패하면 임시 폴더는 지워진다 | 코드 확인 (서버 응답 형식은 클라이언트 가정) |
| R-18 | 사이트 스킬 직접 설치 `install_site_skill` + `install_site_skill_dir` (앱: `install_git`의 사이트 입력, `install_from_skillssh`의 도메인 `source`, CLI) | `install_from_skillssh`는 `source`에 `/`가 없으면 `https://skills.sh/site/<source>/<skill_id>`를 만들어 이 경로로 보낸다. 순서: `cloning` → `download_site_skill`(실패는 모두 `network` kind, 잘못된 주소 포함) → `installing` → 락(`install website skill`) → 취소 플래그 확인(락을 잡은 직후, 쓰기 직전) → `parse_site_ref`(실패 `invalid_input`) → 설치 이름 = `name`(trim, 비면 무시, `sanitize_skill_name` 실패 시 `invalid_input`) 또는 `<skill>` → R-15(`source_type` = `well-known`, `source_ref` = 정규화 URL) → `install_skill_dir_to_destination` → 표 D 값(`resolved_url`·`revision`은 다운로드 결과)으로 R-16 → 임시 폴더 삭제. 정규화 URL이 `www.` 유무와 무관해서 시장·붙여넣기·CLI 어디서 설치해도 같은 레코드·폴더가 된다 | 코드 확인 |
| R-19 | 경로별 출처 값의 비대칭 | 1.3 표 값을 쓴다. 같은 입력이라도 경로에 따라 달라지는 곳: (1) git `source_ref`는 직접 설치(A)에서 trim한 URL, 확정(B)에서 trim 안 한 원문. (2) 사이트 `source_ref_resolved`·리비전은 직접(D)에서는 받은 파일 URL·digest, 미리보기 확정(E)에서는 입력 URL·NULL. (3) skills.sh 경로(C)는 `source_branch`가 항상 NULL이고 이름이 `skill_id` 기반이다. (4) git 경로(A, B)는 `source_ref`로 기존 레코드를 찾지 않는다(R-13). 선행 스펙이 이 값들을 읽는 쪽 규칙을 소유한다 | 코드 확인 |
| R-20 | 오류 분류 (앱) | `kind`와 조건: `git`: `validate_git_url` 실패, `HEAD` 읽기 실패, `find_skill_dir` 실패, 체크아웃 실패 중 분류에 안 걸린 것. 체크아웃 실패는 `classify_git_error`(`C-30`)로 `cancelled`(메시지에 `cancelled`/`canceled`), `network`(`connection refused`, `could not resolve host`, `failed to connect`, `connection timed out`, `network is unreachable` 중 하나, 소문자 비교), 그 외 `git`. `network`: 사이트 다운로드의 모든 실패. `invalid_input`: 경로 이탈, 임시 폴더 검증, 빈 skill id, 사이트 `SKILL.md` 누락, 잘못된 사이트 주소·이름(`install_site_skill_dir`). `not_found`: subpath 없음. `io`: 복사·이름 sanitize 실패 등 `installer` 오류. `database`: 락 실패(`skills repository is busy: <작업명>`)·DB·메타 파일 재작성 오류. `internal`: 블로킹 작업 join 실패. `message`는 오류의 `to_string()`(anyhow는 가장 바깥 설명만)이다 | 코드 확인 |
| R-21 | 진행 이벤트 `install-progress` | `skill_id`는 취소 키와 같은 값이다(`install_git`·미리보기 = `repo_url` 원문, `install_from_skillssh` = `<source>/<skill_id>`, 사이트 분기도 같은 키). 직접 설치: `cloning`(체크아웃 중에는 `detail` 문자열이 여러 번: git stderr 줄, `Updating cached repository…`, `Fetching only the requested skill directory…`, `Waiting for another install of this repository to finish…`, `Trying alternative clone method…`, libgit2 `Receiving objects: n/m (x KB)`) → `installing` → `done`. 실패하면 `done`은 없고 오류는 호출 결과로 간다. 미리보기: `cloning`(+`detail`)만. 확정·취소: 이벤트 없음. 이벤트 전송 실패는 무시한다. 사이트 분기의 `cloning`에는 `detail`이 없다 | 코드 확인 |
| R-22 | 취소 `cancel_install(key)` | `C-31`: 레지스트리는 `key → 취소 플래그`. `register`는 같은 키의 기존 토큰을 덮어쓰고, 작업이 끝나면(Drop, 성공·실패 무관) 그 키를 제거하므로 같은 키로 동시에 둘이 돌면 나중 것이 앞 것의 토큰을 가린다(추론). `cancel`은 등록돼 있으면 플래그를 세우고 `true`, 없으면 `false`. 등록하는 명령은 `install_git`, `preview_git_install`, `install_from_skillssh`뿐이다. 플래그를 읽는 곳: 체크아웃의 git 자식 프로세스 대기 루프(최대 200ms 간격, 자식 kill, `Installation cancelled`로 실패하고 만들던 임시 폴더·캐시 슬롯 정리), 캐시 복사, 사이트의 다운로드 완료 뒤(R-08, R-18). 체크아웃·다운로드가 끝난 뒤의 열거·복사·DB 기록 단계에서는 읽지 않으므로 그때의 `cancel_install`은 `true`를 돌려주고도 설치는 끝까지 진행된다(사이트 직접 설치는 락 직후 한 번 읽음). 취소된 체크아웃은 `cancelled` kind, 취소 시점까지 라이브러리·DB는 변하지 않는다. 캐시 락을 기다리는 동안과 `ls-remote`는 취소되지 않는다. 사이트 취소 메시지는 `Installation cancelled by user` | 코드 확인 |
| R-23 | 락·순서·정리·부분 실패 | 네트워크 단계(체크아웃·다운로드)는 락 밖이고 락은 열거·복사·기록 구간만 감싼다. 미리보기는 락을 쓰지 않는다. 복사 → DB → 메타 파일 순이고 한 단계가 실패해도 앞 단계를 되돌리지 않는다: 복사된 폴더는 DB 행 없이 남을 수 있고(이름 충돌 검사가 파일시스템을 보므로 다음 설치는 `-2`로 간다), 재설치(R-13, R-15)는 기존 폴더를 먼저 지운 뒤 복사하므로 복사 중 실패하면 부분 폴더가 남는다. 임시 체크아웃: 직접 설치와 확정은 성공·실패 무관 삭제, 미리보기는 성공 시 유지하고 실패 시 삭제 | 코드 확인 |
| R-24 | 감사 로그 | `install_git`(git·사이트)과 `install_from_skillssh`(저장소·사이트)는 끝나면 `install` 행을 하나 남긴다(`detail` = `git`, `skillssh`, `well-known` 중 하나, 성공이면 스킬 id·이름, 실패이면 오류 메시지). `preview_git_install`, `confirm_git_install`, `cancel_git_preview`, CLI `skills install`은 남기지 않는다(CLI는 `AuditDraft::new("install")` 호출이 없음) | 코드 확인 |
| R-25 | CLI 입력 분류 `classify_ref(reference, --local, --git, --skillssh)` | `C-27`. 플래그가 있으면 `local` > `git` > `skillssh` 순으로 그대로 따른다(서로 배타라 한 개만 올 수 있음). 플래그가 없으면 순서대로: 사이트 주소(`is_site_ref`) → well-known; `./`, `../`, `/`, `~/`로 시작 → 로컬; `://` 포함, `.git`으로 끝남, `git@`로 시작 → git; `owner/repo`·`owner/repo/skill`·`owner/repo@skill` 모양(세그먼트는 영숫자·`_`·`.`·`-`) → skills.sh; 그 외 `ambiguous ref '<ref>'; pass --local, --git, or --skillssh to disambiguate`. 앱의 `install_git`은 `owner/repo`를 GitHub git URL로 보지만 CLI는 skills.sh 약식으로 본다(`--git` 필요) | 코드 확인 |
| R-26 | CLI 실행 | `run_install`: 먼저 `--sync`(활성 프리셋 id, 없으면 `None`이고 오류 아님)·`--sync-preset REF`(id·이름·`current`, 없으면 `preset not found: <REF>`, 둘 이상이면 `preset reference is ambiguous: <REF>`)를 해석하므로 해석 실패면 아무것도 설치되지 않는다. `synced` = 프리셋 id가 있는지. git: R-12와 같은 단계(`validate_git_url`, R-03, R-04, R-05, R-13, 표 A)이나 취소 플래그가 세워지지 않고 진행 이벤트·감사 로그가 없으며 체크아웃 오류를 `classify_git_error`로 분류하지 않는다. skills.sh: `parse_skillssh_shorthand`(`C-28`)로 `(owner/repo, skill_id)`를 얻고(2부분이면 `skill_id` = repo 이름, `@`가 있으면 `head`가 정확히 2부분이어야 함) 전체 체크아웃(`clone_repo_ref`) 후 R-14 이후와 같다. `--name`은 무시한다. 사이트: R-18과 같으며 `resolved_url`·`revision`은 다운로드 결과다. 실패는 stderr `error: <원인 연쇄>`와 종료코드 1, `--json`이면 `{ok:false, code:"COMMAND_FAILED", message, error}`(설치 오류는 `details`가 없어 항상 이 코드). 인자 충돌은 clap 오류 | 코드 확인 |

- 불변식:
  - 라이브러리에 새로 생기는 폴더는 하나의 스킬 폴더 사본이다. `.git`, `.DS_Store`, 심볼릭 링크는 복사되지 않는다. 전제: R-13의 복사 함수를 거친다.
  - skills.sh·well-known 레코드는 `(source_type, source_ref)`로 다시 찾아져 폴더·`id`가 유지된다. git 레코드는 이 불변식이 없다(R-13).
  - 임시 체크아웃은 `skills-manager-clone-` 또는 `skills-manager-well-known-` 접두사 이름 폴더이고 라이브러리 폴더와 겹치지 않는다.
- 미결정: 없음. (이전에 U-01로 두었던 메타데이터 파일 규칙은 `skill-source-metadata` R-11, R-18이 소유하는 것으로 해소했다. 프리셋·멤버십 파일의 형식은 이 기능과 무관해 범위 밖이다.)
- 확인 한계:
  - 어떤 경로도 실행하지 않았다. 빌드·네트워크·앱 실행 없음. 모든 결과는 코드를 따라 읽은 것이다. R-12의 컨테이너 설치 결과와 R-22의 늦은 취소 동작이 특히 그렇다.
  - 외부 서비스 동작은 클라이언트 가정이다: GitHub `tree/` URL 의미, `--filter=blob:none`·`sparse-checkout --cone`을 서버·git 버전이 받는지, skills.sh `/site/…` 라우트, 사이트의 `.well-known` 인덱스 v1/v2 형식과 `$schema` 구분.
  - Windows 동작(`source_subpath` 구분자, 경로 규칙)은 `cfg(windows)` 코드를 읽기만 했다.
  - 원본의 캐시 슬롯(2.2)이 설치 결과를 바꾸지 않는다는 판단은 추론이다.

### 1.5 필수 코드 참조

라이선스는 MIT(overview 1절)라 인용이 허용된다. 모든 줄 범위는 `7a22192` 기준이다. 경로 접두사 `src-tauri/src/` 생략.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `core/git_fetcher.rs:52-82` `validate_git_url` | 허용 스킴(`https://`, `http://`, `ssh://`, `git@`, 대소문자 무시)과 `user/repo` 약식, 로컬·UNC·Windows 경로 거부 | R-02, R-12, R-26 |
| C-02 | `core/git_fetcher.rs:36-46` `parse_git_source` | 입력 trim, `normalize_url` 결과로 `ParsedGitSource` 생성 | R-03 |
| C-03 | `core/git_fetcher.rs:1339-1368` `normalize_url` | 전체 URL 통과(GitHub 트리면 분해), `user/repo[.git]` → `https://github.com/user/repo.git` | R-03 |
| C-04 | `core/git_fetcher.rs:1466-1585` 트리 URL 분해 함수들, `parse_git_source_resolved` | GitHub `…/tree/<path>` 정규식, 원격 ref 기준 브랜치 우선·최장 일치 분해, 실패 시 낙관 분해 | R-03 |
| C-05 | `core/git_fetcher.rs:1587-1641` `RemoteRefNames`, `list_remote_ref_names`, `parse_remote_ref_names` | `git ls-remote --heads --tags` 출력에서 브랜치·태그 이름 추출(`^{}` 항목 제외) | R-03 |
| C-06 | `core/git_fetcher.rs:580-644` `clone_repo_ref_scoped`, `is_cancellation`, `sparse_pattern` | 좁은 체크아웃 시도 후 폴백, 취소는 폴백하지 않음, subpath가 좁은 체크아웃에 쓸 만한지 판정. 호출하는 `clone_repo_sparse`·`clone_repo_full`은 R-04 글로 푼다 | R-04 |
| C-07 | `core/git_fetcher.rs:1169-1185` `get_head_revision` | `git rev-parse HEAD`, 실패하면 libgit2 | R-09, R-12, R-14 |
| C-08 | `core/git_fetcher.rs:1330-1337` `relative_subpath` | 스킬 폴더의 체크아웃 상대경로, 같으면 `None`, 접두사 아니면 `None`, OS 구분자 | R-12, R-14 |
| C-09 | `core/git_fetcher.rs:1370-1460` `find_skill_dir` | `skill_id` 탐색 순서와 폴백, id가 없을 때의 기본 폴더 | R-05, R-14 |
| C-10 | `commands/skills.rs:3094-3135` `resolve_skill_dir` | subpath·skill_id 우선순위, 안전 검사, 오류 종류 | R-05 |
| C-11 | `commands/skills.rs:3022-3042` `collect_git_skill_dirs`, `skill_rel_key` | 열거와 `rel_path` 규칙 | R-06 |
| C-12 | `core/scanner.rs:33-86` `collect_skill_dirs` | 재귀 열거, 제외 폴더, 순환 방지, 라이브러리 링크 제외 | R-06 |
| C-13 | `commands/skills.rs:3046-3075` `validate_clone_temp_path` | 임시 폴더 허용 조건과 두 오류 메시지. 접두사 문자열은 `skills-manager-clone-`(`git_fetcher.rs:23`), `skills-manager-well-known-`(`well_known.rs:8`) | R-11 |
| C-14 | `core/skill_metadata.rs:8-88` `parse_skill_md`, `parse_frontmatter`, `is_valid_skill_dir` | frontmatter 파싱(`---` 사이 YAML의 `name`, `description` 문자열), 스킬 폴더 판정(`SKILL.md`·`skill.md` 일반 파일) | R-06, R-14 |
| C-15 | `core/skill_metadata.rs:90-167` `sanitize_skill_name`, `infer_skill_name` | 설치 이름 정제(마지막 경로 성분, 제어·Windows 예약 문자 `_` 치환, 트림, 예약 이름 접두 `_`), 이름 추론 | R-13 |
| C-16 | `core/installer.rs:82-101` `install_from_local` | 이름 결정 → `unique_skill_dest` → 복사 설치 | R-13 |
| C-17 | `core/installer.rs:146-199` `install_from_git_dir`, `install_skill_dir_to_destination` | 목적지 교체 방식(삭제 후 복사), 결과값, 같은 폴더 가리킬 때의 단락 | R-13, R-14, R-15 |
| C-18 | `core/installer.rs:245-299` `unique_skill_dest`, `copy_skill_dir` | `-N` 접미사 규칙, 같은 내용 재사용, 복사 제외 대상 | R-13 |
| C-19 | `commands/skills.rs:3137-3187` `resolve_skillssh_install_target`, `resolve_install_target` | 재설치 시 기존 레코드 재사용, 새 이름 후보 선택 | R-15 |
| C-20 | `commands/skills.rs:2645-2731` `store_installed_skill_unlocked` | 신규 insert 기본값과 재설치 갱신 흐름, 프리셋 연결 | R-16 |
| C-21 | `core/skill_store.rs:393-434` `update_skill_after_reinstall` | 재설치 때 갱신되는 컬럼과 유지되는 컬럼 | R-16 |
| C-22 | `core/well_known.rs:8-47` 상수, `SiteRef`, `DownloadedSkill`, `DiscoveryIndex` | 한도 상수(50MiB, 100MiB, 4096, 512, 16, 64KiB, 16K), 호스트 목록, 정규 URL | R-01, R-17, R-18 |
| C-23 | `core/well_known.rs:49-79` `parse_site_ref`, `is_site_ref` | 사이트 주소 판정과 `source_url`·`domain`·`skill_name` 추출 | R-01, R-18 |
| C-24 | `core/well_known.rs:81-129` `download_site_skill`, `skill_dir_from_temp`, `cleanup_temp` | 인덱스 → 항목 → 임시 폴더 → v1/v2 분기, 임시 폴더 유지 방식 | R-08, R-10, R-17 |
| C-25 | `core/well_known.rs:131-249` `site_client`, `fetch_index`, `download_v1_entry`, `download_v2_entry` | HTTPS 전용 클라이언트, 인덱스 탐색, v1/v2 내려받기 | R-17 |
| C-26 | `core/well_known.rs:251-394` 다운로드·압축 해제 안전 규칙 | 크기·개수·경로 한도, digest 검사, 링크·특수 파일 거부, 안전 세그먼트 | R-17 |
| C-27 | `bin/skills-manager-cli.rs:1487-1543` `classify_ref`, `is_skillssh_shorthand` | CLI 입력 분류 | R-25 |
| C-28 | `bin/skills-manager-cli.rs:1737-1752` `parse_skillssh_shorthand` | `owner/repo[@skill]`·`owner/repo/skill` 분해 | R-26 |
| C-29 | `core/error.rs:36-50` `ErrorKind` | 오류 종류 목록과 직렬화 이름(snake_case) | 1.3, R-20 |
| C-30 | `core/error.rs:102-130` `AppError::classify_git_error` | 체크아웃 오류의 cancelled/network/git 분류 | R-20 |
| C-31 | `core/install_cancel.rs:5-42` `InstallCancelRegistry` | 키별 취소 플래그 등록·취소·제거 | R-22 |
| C-32 | `core/content_hash.rs:7-16` `IGNORED`, `is_ignored` | 내용 해시가 무시하는 이름(`.git`, `.DS_Store`, `Thumbs.db`, `.gitignore`, `__pycache__`, `*.pyc`) | 1.2 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. 실행·원본 테스트 열람 없음(테스트는 사례 이름 검색만). 네트워크가 필요한 사례를 로컬 원격이나 로컬 fixture로 대체해 검증하면 서버별 `git clone`·`ls-remote` 동작과 사이트의 `index.json` 응답은 검증하지 않는다(`validate_git_url`은 `file://`을 거부하므로 R-02 경로 밖의 함수 수준에서 대체한다).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03 | `parse_git_source`: `o/r`, `o/r.git`, `https://github.com/o/r`, `https://github.com/o/r/tree/main/skills/foo`, `git@github.com:o/r.git`, `https://gitlab.com/o/r/-/tree/main/x` | clone_url: `https://github.com/o/r.git`, 같음, `https://github.com/o/r`(`.git` 안 붙임), `https://github.com/o/r.git`+branch `main`+subpath `skills/foo`, 원문 그대로, 원문 그대로(트리 분해 안 함) |
| T-02 | R-03 | 원격 브랜치 `feature/x`가 있는 상태에서 `…/tree/feature/x/skills/foo`를 `parse_git_source_resolved`. 그리고 `ls-remote` 실패 상태에서 같은 URL | 앞: branch `feature/x`, subpath `skills/foo`. 뒤: branch `feature`, subpath `x/skills/foo` |
| T-03 | R-02 | `validate_git_url`: `o/r`, `HTTPS://h/o/r`, `SSH://h/o/r`, `git@h:o/r`, `o`, `file:///x`, `/a/b`, `./a/b`, `~/a/b`, `C:\x`, `C:/x/y`, `ext::sh -c x` | 앞 네 개 통과, 나머지 거부 |
| T-04 | R-04, R-20 | 체크아웃 중 취소 플래그를 세운다 | `cancelled` kind(`Installation cancelled`), 임시 폴더·캐시 슬롯 정리, 라이브러리·DB 변화 없음, 이벤트 `done` 없음 |
| T-05 | R-05 | `resolve_skill_dir(repo, "../x", None)`, `(repo, "missing", None)`, `(repo, None, Some("nope"))`, 심볼릭 링크로 repo 밖을 가리키는 subpath | `invalid_input`, `not_found`, `git` kind(`Skill 'nope' was not found …`), `invalid_input` |
| T-06 | R-05, R-12 | 루트에 `SKILL.md`가 없고 `skills/a/SKILL.md`, `skills/b/SKILL.md`가 있는 레포에 `install_git`(subpath 없음) | 폴더 `skills/` 전체가 한 스킬로 복사되고 이름은 `skills`, `source_subpath` = `skills`(목록에서 고르는 일 없음) |
| T-07 | R-06, R-07 | 같은 레포에 `preview_git_install` | `skills` = `a`, `b`(`rel_path`는 `skills` 기준 `a`, `b`), `temp_dir` 존재 |
| T-08 | R-07, R-11 | 스킬이 없는 레포를 미리보기한 뒤 `cancel_git_preview(temp_dir)` | 미리보기는 `skills: []`로 성공하고 폴더가 남아 있다가, 취소 뒤 폴더가 없다. 존재하지 않는 경로·허용 접두사가 아닌 경로로 `cancel_git_preview`를 불러도 성공이고 아무것도 지우지 않는다 |
| T-09 | R-09, R-13 | T-07 미리보기 후 `items = [{rel_path:"a", name:""}, {rel_path:"zzz", name:"x"}]`로 `confirm_git_install` | `a`만 설치(이름 = frontmatter `name` sanitize 값), `zzz`는 무시, 성공, 임시 폴더 삭제, 같은 `temp_dir`로 재확정하면 `Clone session expired, please try again`, 표 B 값, 감사 로그 없음 |
| T-10 | R-09, R-23 | 선택한 두 항목 중 열거 순서상 두 번째의 `name`이 `..`처럼 sanitize 불가 | 첫 항목은 설치된 채 남고 `io` kind `Invalid skill name: '..'`, 임시 폴더 삭제 |
| T-11 | R-11 | `confirm_git_install`에 `temp_dir` = 존재하는 `/tmp/other` 또는 `<임시>/not-prefixed` | `invalid_input` `Invalid temp directory`, 폴더 그대로 |
| T-12 | R-13 | 같은 git 스킬을 두 번 설치(내용 동일) → 원격 내용을 바꿔 세 번째 설치 | 두 번째: 같은 폴더·같은 `id`(갱신, `enabled`·`created_at` 유지). 세 번째: 새 폴더 `<name>-2`와 새 레코드, 첫 레코드는 그대로 |
| T-13 | R-14, R-15 | `source=o/r`, `skill_id=foo`, 레포에 `skills/foo/SKILL.md`. 설치 후 한 번 더 설치. 별도로 라이브러리에 레코드 없는 폴더 `foo`가 이미 있는 상태에서 첫 설치 | 첫 설치: 이름 `foo`, 표 C 값. 재설치: 같은 폴더·`id`(내용 교체). 폴더가 이미 있으면 `foo-2` |
| T-14 | R-14 | `skill_id`가 레포에 없음 | `git` kind `Skill '<id>' was not found in the fetched version of this repository. Check the source and its subpath.`, 라이브러리 변화 없음, 임시 폴더 삭제, 감사 로그에 실패 행 |
| T-15 | R-01, R-18 | `install_git("https://www.skills.sh/site/uizze.com/ui-radar")`, 인덱스 v1(`files:["SKILL.md"]`) | `source_ref` = `https://skills.sh/site/uizze.com/ui-radar`, `source_ref_resolved` = `https://uizze.com/.well-known/agent-skills/ui-radar/SKILL.md`(인덱스가 agent-skills일 때), `source_revision`·`remote_revision` NULL, `update_status` `local_only`, 이름 `ui-radar`, 감사 로그 `well-known` |
| T-16 | R-17, R-18 | 인덱스 v2 `$schema` 있음, `type:"archive"`, `digest` 일치 / 불일치 | 일치: 표 D 값, `source_revision` = `sha256:<hex>`. 불일치: `network` kind `Downloaded skill failed its SHA-256 digest check`, 라이브러리 변화 없음, 임시 폴더 삭제 |
| T-17 | R-17 | `files`에 `../SKILL.md` 또는 중복 파일, 4096개 초과, 압축에 심볼릭 링크 | 각각 오류(`Invalid skill file path`, `Skill contains duplicate files`, `Skill contains too many files`, `Archive contains a link or special file`), `network` kind, 임시 폴더 삭제 |
| T-18 | R-08, R-10 | 사이트 URL로 `preview_git_install` → `confirm_git_install(items=[{rel_path:"skill", name:""}])` | 미리보기 항목 하나(`rel_path` `skill`). 확정은 이름 = 사이트 `<skill>`, 표 E 값(`source_ref_resolved` = 입력 URL, 리비전 NULL) |
| T-19 | R-22 | 사이트 다운로드 중 `cancel_install(<URL>)` / git 체크아웃이 끝난 직후 `cancel_install(<URL>)` | 앞: 다운로드가 끝난 뒤 `cancelled`(`Installation cancelled by user`), 라이브러리 변화 없음, 임시 폴더 삭제. 뒤: `true`를 돌려주지만 설치 완료. 등록되지 않은 키는 `false` |
| T-20 | R-23 | 락을 20초 넘게 다른 프로세스가 쥔 상태에서 `install_git` | `database` kind `skills repository is busy: install git skill`, 임시 체크아웃 삭제, 라이브러리 변화 없음 |
| T-21 | R-25 | CLI 분류: `o/r`, `o/r/s`, `o/r@s`, `./x`, `x.git`, `https://github.com/o/r`, `github.com/o/r`, `foo`, `a/b/c/d`, `o/r --git`, skills.sh 사이트 URL | skillssh, skillssh, skillssh, local, git, git, skillssh(source `github.com/o`, skill `r`), ambiguous 오류, ambiguous 오류, git, well-known |
| T-22 | R-26 | CLI `install o/r@s --sync`(활성 프리셋 없음) / `--sync-preset nope` | 앞: 설치되고 `synced:false`, `preset_id` 없음. 뒤: `preset not found: nope`, 아무것도 설치되지 않음 |
| T-23 | R-26 | CLI `install o/r@s --name X` | `--name`은 무시되고 이름은 `s` |

## 2부. 근거

### 2.1 요구사항별 근거 지도

SHA는 모두 `7a22192`. 줄은 `commands/skills.rs`(약칭 `skills.rs`) 기준이며, 원본 테스트는 열지 않았다.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | `skills.rs:1032`, `:1246`, `:1380`; C-23 | 세 명령의 첫 분기를 읽음 |
| R-02 | C-01; 호출 전수: `skills.rs:1048`(`install_git`), CLI `:1622`(그 외 `skills.rs:446,645,2119,2378`과 `git_backup.rs`는 이 기능 밖) | `grep validate_git_url`로 호출 위치 전수 확인. 미리보기·확정에는 호출이 없음 |
| R-03 | C-02 ~ C-05; `skills.rs:1050`, `:1306`, `:1419` | `ls-remote` 호출에 타임아웃·취소 인자가 없음을 코드로 확인 |
| R-04 | C-06; `git_fetcher.rs:19`(300초), `:23`, `:260-340`, `:647-845`, `:936-1110`, `:1125-1167`; `git_command.rs:3-16` | 좁은 체크아웃·전체 체크아웃·libgit2 폴백·태그 처리 읽음. 캐시 경유는 2.2 |
| R-05 | C-09, C-10; `path_guard.rs:84-107` | 읽음. `is_path_safe`는 canonicalize 후 접두사 비교 |
| R-06 | C-11, C-12, C-14; `skills.rs:1331-1360` | 읽음 |
| R-07 | `skills.rs:1230-1367`, 특히 `:1331-1364`(`build_preview`, 실패 시에만 `cleanup_temp`) | 열거가 비어도 `Ok`로 반환하는 것을 코드로 확인. 프런트는 빈 목록 문구를 갖고 닫을 때 `cancelGitPreview`를 부른다(`InstallSkills.tsx:1569`, `:523-524`) |
| R-08 | `skills.rs:1246-1295` | 읽음 |
| R-09 | `skills.rs:1371-1461` | 읽음. 프런트는 확정 오류 뒤에도 미리보기 상태를 닫지 않는다(`InstallSkills.tsx:530-560`)이므로 같은 `temp_dir` 재시도가 가능해 보이나 백엔드는 이미 지웠다(추론) |
| R-10 | `skills.rs:1380-1411`; `well_known.rs:119-125` | 읽음 |
| R-11 | C-13; `skills.rs:1464-1473` | 읽음 |
| R-12 | `skills.rs:1003-1109`; C-08, C-09; `skill_metadata.rs:157-167`; UI 호출 `AgentControlSetupCard.tsx:15-16`, `:74` | 경로를 따라 읽음. `find_skill_dir`의 주석(`git_fetcher.rs:1436-1438`)은 이 폴백이 "열거 흐름용이고 단일 설치용이 아니다"라고 적는데 `install_git`·CLI가 단일 설치에 쓴다. 문서와 구현의 차이는 아래 |
| R-13 | C-15 ~ C-18; `sync_engine.rs:20-80`; `content_hash.rs:80-102`, `:143-168` | 읽음. `unique_skill_dest`가 DB를 보지 않음, 해시 비교로 재사용함을 코드로 확인 |
| R-14 | `skills.rs:1111-1226`; C-09 | 읽음. `skill_id`가 `sanitize_skill_name`을 거치지 않음은 `resolve_install_target`(C-19)에서 확인. `skill_id`에 `/`가 들어갈 때의 라이브러리 안 중첩 경로 가능성은 실행하지 않았다(추론) |
| R-15 | C-19; `skill_store.rs:248-275` | 읽음. `get_skill_by_source_ref`는 `LIMIT`·정렬 없이 첫 행 |
| R-16 | C-20, C-21; `migrations.rs:71-91`; `sync_metadata.rs:114-121` | 읽음. `presets::sync_skill_to_active_preset`는 `scenario_service::sync_skill_to_active_scenario`로 위임(`presets.rs:24-30`)하며 본문은 읽지 않았다(다른 스펙) |
| R-17 | C-22 ~ C-26 | 읽음. 외부 서버의 실제 응답은 확인하지 못함(확인 한계) |
| R-18 | `skills.rs:929-1001`, `:1143-1157`; `skills.rs:1032-1045` | 읽음 |
| R-19 | `skills.rs:1083-1092`, `:1200-1209`, `:989-998`, `:1441-1450`; CLI `:1640-1649`, `:1684-1693` | 표의 5개 경로를 모두 읽고 비교 |
| R-20 | C-29, C-30; `skills.rs:1048`, `:1073`, `:1080`, `:939`, `:1078`; `error.rs:58-203` | 각 `map_err` 호출을 읽고 `kind`를 대응 |
| R-21 | `skills.rs:1020-1030`, `:1053-1064`, `:1129-1139`, `:1164-1175`, `:1247-1254`, `:1297-1304`; `git_fetcher.rs:233-258`, `:344-478`, `:694-696`, `:1040-1042`, `:1068-1074`; 프런트 `InstallSkills.tsx:433-446`, `:485-496` | 프런트가 `skill_id`가 자기 키와 같은 이벤트만 쓰는 것을 확인 |
| R-22 | C-31; `skills.rs:320-335`, `:3378-3384`; `git_fetcher.rs:283`, `:402`, `:605-608`, `:821`, `:897`, `:992`, `:1059`; `skills.rs:946`, `:1259` | 취소 플래그를 읽는 위치를 전수 확인. 체크아웃 이후 단계에서 플래그를 읽지 않는다는 것은 `skills.rs:1075-1100`, `:1185-1217`에 `cancel` 사용이 없음으로 확인 |
| R-23 | `skills.rs:1077`, `:1098`; `installer.rs:184-189`; `repo_lock.rs:25-73`; `skills.rs:2645-2731` | 읽음 |
| R-24 | `skills.rs:802-813`, `:1041`, `:1102`, `:1153`, `:1219`; CLI는 `grep -n AuditDraft`로 install 호출 없음 확인 | 읽음 |
| R-25, R-26 | C-27, C-28; CLI `:121-138`, `:889-908`, `:1545-1584`, `:1616-1735`, `:3015-3037`, `:698-705`, `:3132-3157` | 읽음 |
| T-01 ~ T-23 | 각 관련 R-ID의 근거 | 모두 코드에서 계산한 기대값. 실행 안 함 |

**문서와 구현의 차이**

- `skills/manage-skills/SKILL.md:88`은 `skills install https://github.com/anthropics/skills.git` 같은 "아무 git URL"을 예로 들지만, 구현(R-12, R-26)은 단일 스킬이 아닌 레포를 목록에서 고르게 하지 않고 `skills/` 폴더 전체를 한 스킬로 복사한다(실행 미확인).
- 요청문·지도 문구 "well-known 사이트 URL"은 구현상 임의 사이트 URL이 아니라 `https://skills.sh/site/<domain>/<skill>` 형태만 받는다(R-01, `well_known.rs:49-75`).
- 지도 행 "skills.sh 리더보드·검색"은 `skillssh_api.rs`가 맡지만 설치 경로는 이 모듈을 부르지 않는다(`grep skillssh_api`: `browse.rs`, CLI `search`, `settings.rs`, `github_api.rs`만 사용).
- README의 `.zip`/`.skill` 설치는 로컬 설치의 `installer::PreparedSource` 경로이며 이 스펙의 경로에는 닿지 않는다(R-13: 입력이 항상 폴더).

### 2.2 코드 읽는 순서

1. 앱 진입: `commands/skills.rs`의 `install_git`(`:1003`), `preview_git_install`(`:1230`), `confirm_git_install`(`:1370`), `install_from_skillssh`(`:1111`). 프런트 호출: `src/lib/tauri.ts:273-306`.
2. 입력 해석: `git_fetcher.rs` `validate_git_url` → `parse_git_source_resolved` → `clone_repo_ref_scoped`. 폴더 결정은 `resolve_skill_dir`, 열거는 `collect_git_skill_dirs`.
3. 복사·기록: `installer.rs` `install_from_local` / `install_skill_dir_to_destination` → `skills.rs` `store_installed_skill_unlocked`. 이름 충돌은 git은 `unique_skill_dest`, skills.sh·사이트는 `resolve_install_target`.
4. 사이트: `well_known.rs` `download_site_skill`.
5. CLI: `bin/skills-manager-cli.rs`의 `classify_ref` → `run_install` → `install_*_action`.

원본의 구현 전략(재구현 필수 아님, 추론): git 체크아웃은 `<base_dir>/cache/repos/<sha256(canonical URL)[:16]>`(좁은 체크아웃은 `-sparse` 접미사) 슬롯에 `--depth 1`로 받아 두고 파일 락으로 직렬화한 뒤, 다음 설치에서는 `fetch --depth 1` + `reset --hard`로 갱신하고, 실패하면 슬롯을 지우고 다시 받는다. 설치용 임시 체크아웃은 슬롯에서 `git clone --local`(전체 슬롯)이나 폴더 복사 후 promisor 설정 제거(좁은 슬롯)로 만든다. 새 슬롯을 만들 때 캐시 합계가 1GiB를 넘으면 가장 오래 안 쓴 슬롯부터 지운다(`git_fetcher.rs:100-480`, `:647-845`).

## 적용 메모

없음.
