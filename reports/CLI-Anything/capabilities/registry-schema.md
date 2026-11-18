---
sha: "34f519533bc175d2fe287ab8316b0dd99bb9cc43"
created: 2026-11-18
updated: 2026-11-18
sources:
  - registry.json
  - public_registry.json
  - matrix_registry.json
  - .github/scripts/generate_meta_skill.py
  - .github/scripts/update_registry_dates.py
  - .github/scripts/tests/test_update_registry_dates.py
  - .github/workflows/deploy-pages.yml
  - .gitignore
  - cli-hub/cli_hub/registry.py
  - cli-hub/cli_hub/installer.py
  - cli-hub/cli_hub/cli.py
  - CONTRIBUTING.md
  - .github/PULL_REQUEST_TEMPLATE.md
  - docs/hub/openapi.json
  - docs/hub/index.html
  - cli-hub-meta-skill/SKILL.md
  - cli-anything-plugin/HARNESS.md
  - QGIS/agent-harness/setup.py
  - freecad/agent-harness/setup.py
  - unimol_tools/agent-harness/pyproject.toml
  - sketch/agent-harness/package.json
  - zotero/agent-harness/setup.py
depends:
  - ../capabilities/harness-families.md
status: draft
---

# 레지스트리 항목 형식

> `registry.json`(하니스 79개)과 `public_registry.json`(외부 CLI 24개)의 항목 필드·`meta` 블록·하니스 디렉터리와 `skills/` 대응 규칙, 그리고 이 두 파일을 읽는 `generate_meta_skill.py`와 `update_registry_dates.py`의 동작을 정의한다.

<!--
작성 메모(작성자). 이 문서의 개수·분포는 scratch 디렉터리에서 `python -I`로 돌린 읽기 전용 스크립트의 전수 결과다. 스크립트와 실행 로그는 레포·artifacts에 남기지 않았다(2.1 "확인 방법" 참고).
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 사례는 "하니스 `foo`를 레포에 추가하는 PR이 merge되어 허브에 나타나기까지"다.

1. 기여자가 PR에서 `registry.json`의 `clis` 배열 끝에 항목 객체 하나를 직접 쓴다. 외부 저장소의 CLI면 같은 형식으로 쓰되 `source_url`과 `skill_md`에 외부 URL을 넣는다. 항목을 만들어 주는 생성 코드는 찾지 못했다(R-34). 공개 서드파티 CLI(npm, brew 등)가 들어가는 `public_registry.json`에 항목을 추가하는 절차 문서는 찾지 못했다(R-34).
2. PR이 `main`에 merge되고 `registry.json`, `public_registry.json`, `*/agent-harness/**`, 두 스크립트 등이 바뀌면 `deploy-pages.yml`이 돈다(R-26).
3. 워크플로가 먼저 `update_registry_dates.py`를 돌려 두 registry의 모든 항목에 대해 `name → 날짜` 맵을 `docs/hub/registry-dates.json`에 쓴다(R-27~R-30).
4. 이어서 `generate_meta_skill.py`가 registry 3개(`matrix_registry.json` 포함)를 읽어 `cli-hub-skill/SKILL.md`를 만들고, 워크플로가 그것을 DO Spaces에 올린다(R-22~R-25).
5. 워크플로가 `registry.json`·`public_registry.json`을 가공 없이 `docs/hub/`로 복사하고 Jekyll로 빌드해 GitHub Pages에 배포한다. 배포된 주소가 `cli-hub`가 받는 `REGISTRY_URL`이다(R-16, R-26).
6. 사용자가 `cli-hub install foo`를 실행하면 `cli-hub`가 두 registry를 받아(1시간 cache) 합치고, 항목의 `install_cmd`와 `install_strategy`로 설치한다(R-16~R-19).
7. 웹 허브(`docs/hub/index.html`)도 같은 JSON을 받아 카드를 그리고, `registry-dates.json`으로 갱신일을 붙인다(R-31).

### 1.2 범위·통합 지점 [필수]

- 제공: 항목 필드 목록과 필수/선택 구분, 값 규칙, `meta` 블록, 항목과 하니스 디렉터리·`skills/`의 대응 규칙, `category` 값 목록과 분포, 두 스크립트가 registry를 읽고 쓰는 규칙(읽기 전용인지, 어디에 무엇을 쓰는지, 실패 시).
- 제외:
  - `cli-hub`의 설치·삭제·갱신 동작 전체(`installer.py`). 필드 의미를 정하는 부분인 `_install_strategy`와 pip 경로만 R-18~R-20에서 좁게 다룬다.
  - `matrix_registry.json`과 `cli-hub-matrix/`(부속). 생성기가 읽는 키만 R-23에 적고, 구조 대조는 2.3에 둔다.
  - 하니스 내부 구현, `SKILL.md` 생성기(`skill_generator.py`)와 `skills/` 동기화 스크립트(별도 스펙 `skill-packaging`의 영역).
  - 웹 허브의 화면 구성. 필드를 읽는 규칙만 R-08, R-11, R-14, R-31에서 다룬다.
- 외부 의존·선행 계약:
  - 선행 스펙 `capabilities/harness-families.md`(frontmatter `depends`). 그 스펙은 앱별 하니스의 위치·역할·연결 방식을 정의하고, 이 스펙은 registry의 `category` 문자열 값과 분포만 직접 다룬다. 이 스펙은 그 문서의 내용에 기대지 않는다.
  - 하니스 패키지 레이아웃(`setup.py`의 `console_scripts`, 패키지 `skills/SKILL.md`)과 루트 `skills/` 구조는 각각 `harness-contract`, `skill-packaging` 스펙의 영역이다. 이 스펙은 registry 값이 그 구조와 일치하는지만 점검한 결과(R-09~R-13)를 적는다.
  - 호출자가 제공하는 것: GitHub Actions의 `ubuntu-latest` 실행 환경, `git`(전체 이력, `fetch-depth: 0`), 외부 네트워크(GitHub API, npm, PyPI), DO Spaces 자격 증명.
- 소유 상태·부작용:
  - 소유 상태는 사람이 편집하는 JSON 3개(`registry.json`, `public_registry.json`, `matrix_registry.json`)다. 두 스크립트는 이 파일들을 쓰지 않는다(R-22, R-27).
  - 스크립트 산출물은 `cli-hub-skill/SKILL.md`(`.gitignore:48-49`가 추적 제외)와 `docs/hub/registry-dates.json`(추적되지 않음)이다. 둘 다 CI가 만들고 매번 덮어쓴다.
  - `cli-hub`는 사용자 홈의 `~/.cli-hub/registry_cache.json`, `~/.cli-hub/public_registry_cache.json`을 쓴다(R-16).

### 1.3 인터페이스와 데이터 의미 [필수]

**파일 구조**

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `registry.json` | `{ "meta": object, "clis": list<entry> }` | 하니스 79개. 항목은 대부분 이 레포 안 `<dir>/agent-harness`를 가리키고, 11개는 외부 저장소, 2개는 pip가 아닌 설치 명령이다(R-08, R-09). |
| `public_registry.json` | 같은 모양, 24개 | 서드파티·공식 CLI. 하니스 규약(`cli-anything-<name>`, `--json`, REPL)을 따른다는 보장이 없다. 설치 전략을 `package_manager`·`install_strategy`로 고른다(R-05, R-18). |
| `meta` | `{ "repo": string, "description": string, "updated": "YYYY-MM-DD" }` | 사람이 쓰는 값이다. 읽는 곳은 `generate_meta_skill.py`의 `repo`, `updated` 두 키뿐이다(R-32). `matrix_registry.json`의 `meta`에만 `schema_doc`이 더 있다. |
| `clis` 원소 | map | 아래 필드 표. 배열 순서에 의미가 없다(R-35). 두 파일 합쳐 `name` 중복 0이어서 `cli-hub`는 이름 하나로 두 파일을 한꺼번에 조회한다(R-17). |

**하니스 항목(`registry.json`) 필드. n=79**

| 필드 | 분포 | 타입·의미·제약 |
|---|---|---|
| `name` | 79/79 | string, 고유, `[a-z0-9_-]+`. `cli-hub install <name>`의 인자이고 `matrix_registry.json`의 `clis` 목록이 참조하는 키다. 하니스 디렉터리 이름과 같은 경우가 많지만 보장은 없다(R-09). |
| `display_name` | 79/79 | string. 허브 표시명. 생성기·`cli-hub`가 `KeyError`를 내는 키다(R-21). |
| `version` | 79/79 | string, `X.Y.Z` 형식 79개. 하니스 `setup.py` 버전과 같아야 한다는 규칙은 CONTRIBUTING에 있고 66개 중 65개가 맞다(R-15). |
| `description` | 79/79 | string, 한 줄(36~238자). 생성기가 마크다운 표 셀에 그대로 넣는다(R-23). |
| `requires` | 79/79 | string 77개, `null` 2개(mermaid, macrocli). 사용자가 따로 준비할 런타임. |
| `homepage` | 79/79 | string(URL). 대상 앱의 홈페이지라고 CONTRIBUTING이 정의하지만 3개는 이 레포 URL이다(2.1 문서 대 실제). |
| `source_url` | 78/79 | `null` 67개, string 11개, 키 없음 1개(qgis). `null`이면 in-repo, string이면 외부 저장소(R-08). |
| `install_cmd` | 79/79 | string. 66개는 `pip install git+https://github.com/HKUDS/CLI-Anything.git#subdirectory=<dir>/agent-harness`, 7개는 다른 저장소의 `pip install git+…`, 4개는 PyPI `pip install <pkg>`, 2개는 pip가 아닌 명령(sketch, clibrowser)(R-09, R-19). |
| `entry_point` | 79/79 | string, 고유. 설치 뒤 PATH에 생기는 실행 파일 이름. 66개 in-repo 항목은 해당 `setup.py`/`pyproject.toml`의 `console_scripts` 이름과 일치한다(R-10). |
| `skill_md` | 79/79 | 상대 경로 63개(`skills/…` 56, 패키지 안 `…/skills/SKILL.md` 7), URL 11개, `null` 5개(R-11). |
| `category` | 79/79 | string, 31가지 값. 열거형이 아니다(R-07). |
| `contributors` | 78/79 | list of `{ "name": string, "url": string }`. 길이 1이 75개, 2가 3개(R-14). |
| `contributor`, `contributor_url` | 1/79 (qgis) | `contributors` 대신 쓴 단수형 string 두 개(R-14). |
| `install_strategy` | 1/79 (siyuan) | `"pip"`. 하니스 항목은 기본값이 `pip`라서 효과가 없다(R-18). |

**외부 항목(`public_registry.json`) 필드. n=24**

하니스 항목과 같은 키 11개(`name`, `display_name`, `version`, `description`, `category`, `requires`, `homepage`, `source_url`, `skill_md`, `entry_point`, `contributors`)는 24/24다. 다른 점은 아래와 같다.

| 필드 | 분포 | 의미·제약 |
|---|---|---|
| `requires` | 24/24 string | `null`이 없다. |
| `source_url` | string 18, `null` 6 | 외부 저장소. 날짜 갱신기가 GitHub 날짜를 찾는 1순위 단서다(R-29). |
| `version` | `latest` 13, 숫자형 10, `bundled` 1 | 자유 문자열(R-06). |
| `skill_md` | URL 22, `npx skills add …` 명령 문자열 2(feishu, wecom) | 항상 string이다. 가리키는 곳이 `SKILL.md`가 아니라 문서 페이지나 README일 수 있다(예: sanity, shopify). |
| `package_manager` | 22/24: npm 11, pip 4, brew 2, bundled 2, go 1, uv 1, script 1 | 키가 없는 2개는 obsidian-agent-cli, pieces(둘 다 `install_cmd`는 있음). |
| `install_cmd` | 22/24 | 없는 2개는 `bundled`인 android-cli, obsidian-cli. |
| `npm_package`, `npx_cmd` | 각 11 | 정확히 `package_manager == "npm"`인 11개와 같은 집합이다. |
| `install_strategy` | 8: `command` 6, `bundled` 2 | R-18. |
| `uninstall_cmd`, `update_cmd` | 각 5 | `command` 전략의 제거·갱신 명령. |
| `uninstall_notes`, `update_notes` | 각 3 | 명령이 없을 때 사용자에게 보여 줄 문장. |
| `install_notes`, `detect_cmd` | 각 2 | `bundled` 전략에서 "이미 있는지" 검사하는 명령과 안내 문장. |
| `docs_url` | 2 | 날짜 갱신기의 마지막 대체 단서로만 읽힌다(R-29). |
| `platform`(2), `engines`(1) | 선택 | `cli-hub`와 웹 허브에서 읽는 곳을 찾지 못했다(2.1 R-05). |

**`category` 값. 열거형이 아니라 자유 문자열이다**

| 파일 | 값(항목 수) |
|---|---|
| `registry.json` (31가지) | `3d`(3) `ai`(8) `audio`(2) `automation`(3) `communication`(2) `database`(2) `debugging`(2) `design`(2) `devops`(6) `diagrams`(2) `finance`(1) `game`(1) `gamedev`(3) `generation`(1) `graphics`(6) `image`(3) `knowledge`(2) `knowledge-management`(1) `music`(1) `network`(2) `office`(4) `osint`(1) `project-management`(1) `science`(2) `scientific`(1) `search`(2) `storage`(1) `streaming`(1) `testing`(1) `video`(6) `web`(6) |
| `public_registry.json` (12가지) | `ai`(4) `audio`(1) `communication`(3) `data-science`(1) `devops`(3) `devtools`(1) `knowledge`(1) `mobile`(1) `music`(1) `productivity`(2) `scientific`(1) `web`(5) |

두 파일에 같은 값이 8개(`ai`, `audio`, `communication`, `devops`, `knowledge`, `music`, `scientific`, `web`) 있고, `public_registry.json`에만 있는 값이 4개(`mobile`, `data-science`, `productivity`, `devtools`)다. 합치면 35가지다. 뜻이 겹치는 쌍은 `science`(unimol_tools, stata) / `scientific`(qgis, public의 arcgis-pro), `knowledge`(obsidian, joplin) / `knowledge-management`(siyuan), `game`(slay_the_spire_ii) / `gamedev`(ueatelier, godot, sbox)다. 생성기는 값마다 섹션을 따로 만들기 때문에 이 쌍은 생성된 `SKILL.md`에서 `### Science`와 `### Scientific`처럼 별개 제목이 된다(R-07).

**스크립트 인터페이스**

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `python3 .github/scripts/generate_meta_skill.py` | 인자 없음. 입력: `<repo_root>/registry.json`(필수), `public_registry.json`·`matrix_registry.json`(선택). 출력: `<repo_root>/cli-hub-skill/SKILL.md` | `repo_root`는 스크립트 파일 위치 기준 세 단계 위 디렉터리라 실행 위치(cwd)와 무관하다(C-03). |
| `python3 .github/scripts/update_registry_dates.py` | 인자 없음. 입력: 두 registry의 `clis`. 출력: `<repo_root>/docs/hub/registry-dates.json` = `{ "<name>": "YYYY-MM-DD" \| null }` | 항목마다 날짜 하나. 못 찾으면 `null`(C-09). |

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `registry.json`, `public_registry.json`을 읽는다. | 둘 다 최상위 키는 `meta`, `clis`이고 항목은 `clis`의 원소다. 개수는 79, 24다. `matrix_registry.json`은 `clis` 대신 `matrices`를 쓰고 `meta.schema_doc`이 더 있다. | 코드 확인 |
| R-02 | 두 파일의 `name`, `entry_point`를 모은다. | 두 값 모두 103개에서 중복 0이다(`name`은 대소문자를 무시해도 0). `name` 문자 집합은 `[a-z0-9_-]`이고 `registry.json`과 `public_registry.json` 사이에 같은 `name`도 없다. | 코드 확인 |
| R-03 | `registry.json` 항목의 키 집합. | 77개는 정확히 12키(`name`, `display_name`, `version`, `description`, `requires`, `homepage`, `source_url`, `install_cmd`, `entry_point`, `skill_md`, `category`, `contributors`)다. 예외는 2개다. qgis는 `source_url`·`contributors`가 없고 `contributor`·`contributor_url`이 있다. siyuan은 12키에 `install_strategy`가 더 있다. 79개가 모두 가진 키는 10개(위 12키에서 `source_url`, `contributors` 제외)다. | 코드 확인 |
| R-04 | `registry.json` 항목의 값 타입. | `requires`는 string 77·`null` 2, `source_url`은 `null` 67·string 11·키 없음 1, `skill_md`는 string 74·`null` 5, `contributors` 원소는 모두 `name`, `url` 두 string이다. 그 외 필수 키는 모두 string이다. | 코드 확인 |
| R-05 | `public_registry.json` 항목의 키 집합. | 24개가 모두 가진 키는 11개이고, 나머지는 선택이다. `install_cmd`, `package_manager`는 22/24, `npm_package`와 `npx_cmd`는 `package_manager`가 `npm`인 11개에만 있다. 선택 키의 분포는 1.3 표와 같다. | 코드 확인 |
| R-06 | `version` 값. | 하니스 항목은 79개 모두 `X.Y.Z`다. 외부 항목은 `latest`(13), `bundled`(1), 숫자형(10)이 섞여 있어 형식 규칙이 없다. | 코드 확인 |
| R-07 | `category` 값. | 값 목록은 열거형이 아니다(OpenAPI `CliEntry.category`는 `type: string`, CONTRIBUTING은 "기존 값 중 하나"라고만 쓴다). 생성기는 값마다 섹션을 만들고 제목을 `str.title()`로 만들기 때문에 `3d`는 `3D`, `knowledge-management`는 `Knowledge-Management`, `ai`는 `Ai`로 나온다. `cli-hub list`는 값을 `upper()`로 보여 주고, `category`가 없으면 `uncategorized`로 묶는다. | 코드 확인 |
| R-08 | 하니스 항목의 `source_url`. | 값이 string이면 외부 저장소 항목이다. 11개가 모두 `skill_md`가 URL이고 `install_cmd`가 이 레포 밖 저장소 또는 PyPI를 가리킨다. 값이 `null`이면 in-repo로 읽는다. 웹 허브는 `null`일 때 `https://github.com/HKUDS/CLI-Anything/tree/main/<name>/agent-harness`로 "Source" 링크를 만든다. `name`이 디렉터리 이름과 다른 qgis(`QGIS`), 3mf(`3MF`)는 이 링크가 실제 디렉터리 대소문자와 다르다(GitHub 경로의 대소문자 구분은 미확인). 예외로 sketch, clibrowser는 `source_url`이 `null`인데 `install_cmd`가 pip 형식이 아니다(R-19). | 코드 확인(링크 규칙·분포) / 추론(링크가 깨지는지) |
| R-09 | in-repo 항목(`install_cmd`에 `#subdirectory=`가 있는 66개). | `<dir>`는 66개 모두 레포에 추적되는 실제 디렉터리이고 끝이 `/agent-harness`다. `<dir>`는 64개에서 `name`과 같고 qgis(`QGIS`), 3mf(`3MF`)만 대소문자가 다르다. 그래서 `update_registry_dates.py`는 `name`보다 `install_cmd`의 `<dir>`를 먼저 쓴다(R-28). | 코드 확인 |
| R-10 | in-repo 항목의 `entry_point`. | `#subdirectory=` 66개와 디렉터리가 있는 sketch(`package.json`의 `bin`), zotero(`setup.py`)까지 68개 모두 `entry_point`가 그 패키지가 선언한 실행 파일 이름과 일치한다(불일치 0). `entry_point`는 63개가 `cli-anything-<name>`이고 예외는 `cc-switch`→`cli-anything-ccswitch`, `slay_the_spire_ii`→`cli-anything-sts2`, `unimol_tools`→`cli-anything-unimol-tools`이다. 외부 항목의 `entry_point`는 점검하지 못했다. | 코드 확인(68개) / 미확인(나머지 하니스 항목 11개와 외부 registry 24개) |
| R-11 | `skill_md` 값. | 네 가지 형태가 있다. (a) `skills/cli-anything-<id>/SKILL.md` 56개, (b) 하니스 패키지 안 사본 `<dir>/agent-harness/cli_anything/<pkg>/skills/SKILL.md` 7개(calibre, lldb, qgis, unrealinsights, macrocli, 3mf, minimax), (c) URL 11개, (d) `null` 5개(adguardhome, comfyui, mermaid, sketch, clibrowser). 상대 경로 63개는 모두 레포에 실제 파일로 있다. 웹 허브는 `^skills/([^/]+)/SKILL\.md$`와 맞는 (a)에만 `npx skills add HKUDS/CLI-Anything --skill <id> -g -y` 명령을 만들고, (b)는 `blob/main/<경로>` 링크, (c)는 URL 링크로 쓴다. | 코드 확인 |
| R-12 | 루트 `skills/`와 항목의 대응. | `skills/` 하위 디렉터리 70개 중 56개가 (a)로 가리켜진다. 나머지 14개는 (b) 7개(calibre, lldb, macrocli, minimax, qgis, threemf, unrealinsights), `skill_md`가 `null`인 3개(adguardhome, comfyui, mermaid), 외부 URL인 zotero, registry 항목이 없는 iterm2-ctl과 rekordbox, 허브용 `cli-hub-meta-skill`이다. `skills/` 디렉터리 이름은 pip 패키지 이름을 따르므로 `cc-switch`→`cli-anything-ccswitch`, `slay_the_spire_ii`→`cli-anything-slay-the-spire-ii`, `unimol_tools`→`cli-anything-unimol-tools`처럼 `cli-anything-<name>`과 다른 경우가 있다. | 코드 확인 |
| R-13 | 하니스 디렉터리(`*/agent-harness`)와 항목. | 디렉터리 69개 중 66개가 `#subdirectory=`로 가리켜진다. 나머지 3개는 sketch(항목 있음, 설치 명령이 `cd sketch/agent-harness && npm install && npm link`), zotero(항목 있음, 설치는 PyPI이고 같은 이름의 in-repo 디렉터리도 존재), rekordbox(registry 3개 파일에 항목 없음)다. `#subdirectory=`가 가리키는데 디렉터리가 없는 항목은 0개다. | 코드 확인 |
| R-14 | `contributors` 값과 단수형 예외. | 정상 항목은 `{name,url}` list다. qgis만 `contributor`, `contributor_url`을 쓴다. 웹 허브는 `c.contributors \|\| (c.contributor ? [...] : [])`로 단수형도 받아들이지만 `cli-hub info`는 `contributors`만 읽으므로 qgis의 기여자가 출력되지 않는다. 웹 허브는 `contributors`가 `[{name: "CLI-Anything-Team"}]` 하나뿐이면 "Community" 배지를 붙이지 않는다(해당 항목 10개). | 코드 확인 |
| R-15 | 하니스 항목 `version`과 패키지 버전. | in-repo 66개 중 65개는 `setup.py`/`pyproject.toml`의 버전과 같다. freecad만 registry `1.1.0`, `setup.py` `1.0.0`이다. 어느 코드도 두 값을 자동으로 맞추거나 검사하지 않는다(R-33). | 코드 확인 |
| R-16 | `cli-hub`가 registry를 받는다. | `https://hkuds.github.io/CLI-Anything/registry.json`과 `public_registry.json`을 `requests.get(timeout=15)`로 받고, `~/.cli-hub/`의 cache 파일에 `{_cached_at, data}`로 저장한다. cache가 3600초 안이면 네트워크를 쓰지 않는다. 요청이 실패하면 나이와 상관없이 기존 cache를 반환하고, cache도 없으면 예외를 올린다. 단 외부 registry는 어떤 예외든 `None`으로 바꿔 하니스 목록만 쓴다. 두 registry의 항목을 합칠 때 항목을 복사해 `_source`(`harness`/`public`)를 붙이며, 하니스가 앞에 온다. `_source`는 registry 파일의 필드가 아니다. | 코드 확인 |
| R-17 | `cli-hub`가 항목을 찾는다. | `get_cli(name)`은 대소문자를 무시한 `name` 일치의 첫 항목이다. `search_clis`는 `name`, `description`, `category`, `display_name`의 부분 문자열 일치이고, `description`이 없으면 `KeyError`다. | 코드 확인 |
| R-18 | `cli-hub`가 설치 전략을 고른다. | 우선순위는 (1) 항목의 `install_strategy`, (2) `_source`가 `harness`(기본값)면 `pip`, (3) `npm_package`가 있거나 `package_manager == "npm"`이면 `npm`, (4) `package_manager == "uv"`면 `uv`, (5) `"bundled"`면 `bundled`, (6) 그 외 `command`다. 현재 데이터에서 하니스 79개는 모두 `pip`이고(siyuan의 명시값도 `pip`), 외부 24개는 `npm` 11, `command` 10, `bundled` 2, `uv` 1이다. `package_manager`가 `pip`인데 `install_strategy`가 없는 외부 항목 2개(py4csr, arcgis-pro)는 `command`로 간다. | 코드 확인 |
| R-19 | 하니스 항목의 `install_cmd`가 `pip install `으로 시작하지 않는다(sketch, clibrowser). | `install_strategy`가 없어서 `pip` 경로로 간다. `_pip_install`이 `install_cmd`에서 `"pip install "` 부분 문자열만 지우고 나머지를 공백으로 쪼개 `python -m pip install` 뒤에 붙이므로 `cd sketch/agent-harness && npm install && npm link`가 pip 인자가 된다. 그 결과 설치가 실패한다고 예상되지만 실행해 보지는 않았다. | 코드 확인(분기) / 추론(실패 결과) |
| R-20 | `cli-hub uninstall <name>`이 하니스 항목의 pip 패키지 이름을 정한다. | 이름을 `cli-anything-<name>`으로 만든다. in-repo 66개 중 65개는 pip의 이름 정규화(`_`·`-` 동일 취급) 뒤 `setup.py`/`pyproject.toml`의 패키지 이름과 같고, cc-switch만 패키지 이름이 `cli-anything-ccswitch`라 다르다. cc-switch의 pip 제거가 실제로 어떻게 끝나는지는 실행하지 않았다. | 코드 확인(이름 비교) / 미확인(pip 동작) |
| R-21 | 소비자가 항목 키를 읽는다. | 키가 없으면 `KeyError`가 나는 곳은 다음과 같다. `name`(조회·표시), `description`(`list`, `search`, 생성기), `display_name`(설치 메시지, 생성기), `version`(`info`, `installed.json` 기록), `entry_point`(설치 메시지, `info`, 외부 항목 생성기 표), `install_cmd`(`pip`·`uv` 전략은 `cli["install_cmd"]`, `command` 전략은 `.get`), `npm_package`(`npm` 전략), `category`(생성기 `cli['category']`). `cli-hub`는 `category`를 `.get(..., "uncategorized")`로, `requires`, `homepage`, `skill_md`, `contributors`, `source_url`을 `.get`으로 읽어 없어도 동작한다. | 코드 확인 |
| R-22 | `generate_meta_skill.py`를 실행한다. | `registry.json`을 읽고(없으면 `FileNotFoundError`), `public_registry.json`과 `matrix_registry.json`은 파일이 있을 때만 읽는다(없으면 빈 목록). 쓰는 곳은 `<repo_root>/cli-hub-skill/SKILL.md` 하나이고 상위 디렉터리를 만들며 파일 전체를 덮어쓴다. 세 registry 파일은 수정하지 않는다. 파일 입출력에 `encoding`을 지정하지 않아 실행 환경의 기본 인코딩을 쓴다. | 코드 확인 |
| R-23 | 생성기가 문서 내용을 만든다. | `total_count = len(하니스) + len(외부)`(matrix 제외)이고 `description`에 `{total}+`, 본문에 하니스 수와 외부 수가 들어간다. 하니스는 `category`별로, 외부 항목도 `category`별로 섹션을 만들고, 섹션과 섹션 안 항목을 각각 `category`, `name` 오름차순으로 정렬한다. 하니스 표는 `Name \| Description \| Install`(설치 칸은 `` `cli-hub install <name>` ``)이고 `skill_md`를 출력하지 않는다. 외부 표는 `entry_point`와 `skill_md`를 더 쓰며 `skill_md`가 비면 `'—'`, `http`로 시작하지 않으면 백틱으로 감싼다. matrix 표는 matrix가 1개 이상일 때만 만든다(0개여도 "CLI Matrices" 안내 절은 남는다). 마지막 줄에 `registry.json`의 `meta.repo`, `meta.updated`를 `Repository`, `Last Updated`로 넣는다. `description`의 `\|`를 이스케이프하지 않지만 현재 데이터에는 `\|`가 없다. | 코드 확인 |
| R-24 | 생성 중 필수 키가 없거나 JSON이 깨져 있다. | `KeyError`/`json.JSONDecodeError` 같은 예외가 처리되지 않아 프로세스가 비정상 종료한다. 파일 쓰기는 문서 조립이 끝난 뒤 마지막에 하므로 이전 `cli-hub-skill/SKILL.md`는 그대로 남는다. 워크플로에서 이 step이 실패하면 뒤 step(업로드, 배포)은 GitHub Actions 기본 동작상 실행되지 않는다. | 코드 확인(예외·쓰기 순서) / 추론(Actions 기본 동작) |
| R-25 | 생성 결과와 추적되는 `cli-hub-meta-skill/SKILL.md`. | 생성 결과는 `name: cli-anything-hub`로 시작하고 `cli-hub-skill/`은 `.gitignore`로 추적되지 않는다. 추적되는 `cli-hub-meta-skill/SKILL.md`(`name: cli-hub-meta-skill`, 115줄)는 생성물이 아니라 손으로 쓴 소개 문서이고 "Live Catalog" 절에서 DO Spaces의 URL을 가리킨다. 두 파일은 내용이 다르다. | 코드 확인 |
| R-26 | `deploy-pages.yml`이 도는 조건과 순서. | `main` push에서 `*/agent-harness/**`, 세 registry, `cli-hub/**`, `cli-hub-matrix/**`, `docs/hub/**`, 워크플로 자신, 두 스크립트가 바뀌었거나 `workflow_dispatch`일 때 돈다. 순서는 checkout(`fetch-depth: 0`), Python 3.10, `update_registry_dates.py`, `generate_meta_skill.py`, `aws s3 cp cli-hub-skill/SKILL.md`(DO Spaces, `public-read`), `registry.json`·`public_registry.json`·`matrix_registry.json`을 `docs/hub/`로 `cp`, Jekyll 빌드, `cli-hub-matrix/`를 사이트에 복사, 업로드·배포다. registry 파일은 변환 없이 복사된다. | 코드 확인 |
| R-27 | `update_registry_dates.py`를 실행한다. | 두 registry의 `["clis"]`를 이어 붙이고 항목마다 `dates[cli["name"]] = get_cli_date(cli)`를 계산한다. 계산이 모두 끝난 뒤 `docs/hub/registry-dates.json`을 `indent=2`, UTF-8로 열어 덮어쓴다(끝 줄바꿈 없음). registry 파일은 수정하지 않는다. 이름이 겹치면 뒤(외부 registry)가 이긴다(현재는 겹침 0). `Updated dates for N CLI entries`를 출력한다. | 코드 확인 |
| R-28 | 항목이 이 레포의 하니스인지 판별해 날짜를 정한다. | 로컬 경로 후보를 (1) `install_cmd`의 `#subdirectory=` 값, (2) `skill_md`에서 `/agent-harness/` 앞부분 + `/agent-harness`, (3) `name`, `name`의 `-`→`_`, `_`→`-` 뒤에 `/agent-harness`를 붙인 경로 순으로 보고 처음 존재하는 것을 쓴다. 찾으면 그 경로의 마지막 커밋 시각(UTC 날짜)이 날짜다. 이때 하위의 `repl_skin.py`, `SKILL.md`만 바뀐 커밋은 제외하고, 제외하면 커밋이 없을 때만 제외 없이 다시 본다. 현재 데이터에서 66개는 (1), 2개(zotero, sketch)는 (3)으로 로컬을 찾고 나머지 11개는 외부로 간다. zotero는 외부 항목인데도 이름이 같은 in-repo 디렉터리를 찾아 로컬 날짜를 쓴다. 외부 registry의 24개는 모두 외부로 간다. | 코드 확인 |
| R-29 | 외부로 간 항목의 날짜. | 우선순위는 (1) `source_url`(없으면 `install_cmd`의 첫 `https://github.com/…` URL에서 `.git` 제거, 없으면 `homepage`/`docs_url` 중 `github.com`이 든 값)이 GitHub 저장소 URL이면 API의 `pushed_at` 앞 10자, (2) `package_manager == "npm"`이면 npm registry의 `latest` 게시일, (3) `install_cmd`가 `pip install <패키지>` 형태(URL·`git+` 토큰이면 제외)면 PyPI 최신 파일 업로드일, (4) `homepage`, `docs_url`의 HEAD 응답 `Last-Modified`다. 앞 단계가 `None`이면 다음 단계로 간다. 모든 요청은 인증 토큰 없이 보내고 timeout은 10초다. | 코드 확인 |
| R-30 | 날짜 조회가 실패한다. | 네트워크·JSON 오류와 `git log` 비정상 종료는 모두 `None`이 되어 그 항목이 `null`로 기록된다. 다른 항목은 계속 처리하고 종료 코드도 0이다. 반면 registry 파일 누락·`name`/`clis` 키 누락·`git` 실행 파일 없음(`FileNotFoundError`)은 잡지 않아 스크립트가 중단되고, 이 경우 `registry-dates.json`은 쓰기 전이라 이전 파일이 남는다. | 코드 확인 |
| R-31 | `registry-dates.json`의 위치와 소비. | `docs/hub/registry-dates.json`은 레포에 추적되지 않고 CI가 만든다. 웹 허브는 `https://hkuds.github.io/CLI-Anything/registry-dates.json`, `../../registry-dates.json` 순으로 받고, 받으면 `dates[c.name]`을 `c.last_modified`로 붙여 "Updated" 정렬·표시에 쓴다. 받지 못해도(`if (dates)`) 카드는 그대로 그려진다. | 코드 확인 |
| R-32 | `meta` 블록. | `repo`, `description`, `updated`는 사람이 쓴 문자열이다. 읽는 곳은 `generate_meta_skill.py`(`registry.json`의 `meta.repo`, `meta.updated`)뿐이고 `description`을 읽는 코드와 `meta.updated`를 쓰는 코드는 찾지 못했다. 기준 SHA에서 `registry.json`의 `meta.updated`는 `2026-06-19`, `public_registry.json`은 `2026-08-20`인데 `registry.json`의 마지막 커밋은 2026-08-21이다. | 코드 확인(읽는 곳) / 코드 확인(값 비교) |
| R-33 | registry 항목이 형식에 맞는지 자동으로 검사하는가. | 필드 필수 여부, `category` 값, `skill_md` 경로 실재, `entry_point`와 `console_scripts` 일치, `version` 동기를 검사하는 스크립트나 CI step을 찾지 못했다. PR 템플릿의 체크리스트와 `deploy-pages.yml`의 생성 step(R-24)이 간접적으로 `name`, `category`, `display_name`, `description` 존재만 강제한다. | 코드 확인(부재: 검색 범위는 2.1) |
| R-34 | 에이전트가 하니스를 만드는 7단계 절차(`HARNESS.md`)와 registry. | 7단계 문서와 `cli-anything-plugin/`, 에이전트별 어댑터 디렉터리에는 `registry.json` 항목을 만들거나 고치라는 지시가 없다. 항목을 추가하라는 지시는 `CONTRIBUTING.md`와 `.github/PULL_REQUEST_TEMPLATE.md`에만 있고(기여자 몫), 어댑터 중 hermes, reasonix의 `SKILL.md`는 `registry.json`을 "하니스 목록"으로 참조만 한다. | 코드 확인(부재: 검색 범위는 2.1) |
| R-35 | `clis` 배열 순서. | 알파벳순이 아니다(첫 항목 jumpserver, 마지막 magnific). 생성기(`name` 정렬), `cli-hub list`(`name` 정렬), 웹 허브(정렬 상태값)가 각자 정렬하므로 순서가 결과에 영향을 주지 않는다. 항목을 끝에 이어 붙이는 관례인지는 알 수 없다. | 코드 확인(정렬 코드) / 추론(관례) |

- 불변식: 한 registry 안과 두 registry 사이에서 `name`과 `entry_point`는 유일하다(R-02, 현재 데이터 기준이고 이를 강제하는 코드는 없다, R-33). `source_url`이 string인 하니스 항목은 `skill_md`가 URL이고 `install_cmd`가 이 레포 밖을 가리킨다(R-08, 데이터 규칙이고 강제 코드는 없다).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-19, R-20 | `cli-hub install sketch`·`install clibrowser`가 실제로 성공하는가, `cli-hub uninstall cc-switch`는 어떻게 끝나는가. | 하니스 항목에서 pip가 아닌 `install_cmd`를 허용할지, 그때 `install_strategy`를 필수로 요구할지 설계가 갈린다. 원본에서 이 항목들이 정상 설치되는지는 코드만으로 닫히지 않는다. | 격리된 venv에서 `cli-hub install sketch`, `install clibrowser`, `install cc-switch` 후 `uninstall cc-switch`를 실행하고 종료 코드·메시지를 기록한다. |
| U-02 | R-25 | DO Spaces에 올라가는 `SKILL.md`와 `cli-hub-meta-skill/SKILL.md`가 가리키는 `reeceyang.sgp1.cdn.digitaloceanspaces.com/SKILL.md`가 같은 객체인가. | 생성기 출력이 실제 사용자에게 가는 경로인지 확정되지 않는다. 구현자는 생성물 배포 위치를 추측해야 한다. | 워크플로의 버킷 값은 secret이라 레포에서 볼 수 없다. 해당 URL을 받아 생성기 출력과 비교하거나 레포 관리자에게 확인한다. |

- 확인 한계:
  - 외부 URL(`skill_md`, `source_url`, `homepage`) 도달 여부와 외부 항목의 `install_cmd` 동작은 검사하지 않았다.
  - `update_registry_dates.py`의 외부 호출 결과(GitHub API 속도 제한 영향 등)와 실제 날짜 값은 실행하지 않았다. 로컬 `git log` 경로 분기만 실행했고, 분석용 clone이 얕아(`--depth 50`) 날짜 값 자체는 신뢰하지 않는다.
  - `generate_meta_skill.py`는 scratch 디렉터리에 스크립트와 registry 사본을 두고 실행했다(`python -I -X utf8`). 인코딩 옵션 없이 실행하면 Windows 기본 로캘(cp949)에서 `UnicodeDecodeError`가 났다. 워크플로가 도는 `ubuntu-latest`의 로캘은 확인하지 않았다.
  - 실행 로그와 점검 스크립트는 저장하지 않았다. 같은 결과는 2.1의 확인 방법으로 다시 낼 수 있다.

### 1.5 필수 코드 참조 [필수]

라이선스는 Apache 2.0이라 인용이 허용된다(overview 1절). 정적 안내 문구(`generate_meta_skill.py:41-98`, `158-192`)는 registry 형식과 무관해 포함하지 않는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `cli-hub/cli_hub/registry.py:9-117` 모듈 전체 | registry URL 2개, cache 위치·TTL(3600초), 실패 시 stale cache 반환, 외부 registry 실패 시 `None`, `_source` 태그와 병합 순서, `get_cli`·`search_clis`·`list_categories` | R-16, R-17, R-21 |
| C-02 | `cli-hub/cli_hub/installer.py:106-119` `_install_strategy` | 설치 전략 결정 우선순위 | R-18 |
| C-03 | `.github/scripts/generate_meta_skill.py:7-39` | 입력 경로(`repo_root`), 선택 입력 처리, `total_count`, 카테고리 그룹핑 | R-22, R-23 |
| C-04 | `.github/scripts/generate_meta_skill.py:99-156` | 섹션·항목 정렬과 하니스·외부·matrix 표의 열, `skill_md` 표시 규칙 | R-23 |
| C-05 | `.github/scripts/generate_meta_skill.py:193-205` | `meta.repo`/`meta.updated` 출력, 출력 파일 쓰기, 완료 메시지 | R-22, R-23 |
| C-06 | `.github/scripts/update_registry_dates.py:17-57`, `138-193` | 정규식 상수, pip 옵션 목록, `_extract_pypi_package`, `get_pypi_date` | R-29 |
| C-07 | `.github/scripts/update_registry_dates.py:87-122`, `220-253` | `_git_log_timestamp`, `get_last_modified`(제외 glob), `_extract_install_subdirectory`, `_extract_skill_subdirectory`, `resolve_harness_path` | R-28 |
| C-08 | `.github/scripts/update_registry_dates.py:60-84`, `125-135`, `196-217`, `256-305` | `_fetch_json`, `_fetch_last_modified`, GitHub·npm 날짜, `extract_external_source_url`, `get_external_date`, `get_cli_date` | R-29, R-30 |
| C-09 | `.github/scripts/update_registry_dates.py:308-322` | `_load_registry`, `main`의 쓰기 순서와 출력 형식 | R-27 |
| C-10 | `.github/workflows/deploy-pages.yml:3-18`, `43-69` | 트리거 경로, 두 스크립트 실행 순서, 업로드·registry 복사 | R-26 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출. T-01~T-07, T-09는 scratch 디렉터리에서 실제로 실행(함수 호출 포함)해 확인한 결과이고, T-08, T-10은 코드 읽기로만 도출했다. 사본 디렉터리에서 실행했고 원본 레포의 `git status`는 0줄이었다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01~R-04 | 기준 SHA의 `registry.json`을 읽어 키 집합을 센다. | 키 집합 3종: 77개(12키), qgis 1개(`contributor`, `contributor_url` 있음, `source_url`·`contributors` 없음), siyuan 1개(12키 + `install_strategy`). `name` 중복 0, `entry_point` 중복 0. |
| T-02 | R-05, R-18 | `public_registry.json`의 `package_manager`와 `_install_strategy`를 항목마다 적용한다. | `package_manager` 분포 npm 11, pip 4, brew 2, bundled 2, go 1, uv 1, script 1, 없음 2. 설치 전략은 npm 11, command 10, bundled 2, uv 1. py4csr(`pip`, `install_strategy` 없음)은 `command`다. |
| T-03 | R-09, R-10, R-28 | qgis 항목(`install_cmd` `#subdirectory=QGIS/agent-harness`, `name: qgis`)으로 `resolve_harness_path`를 호출한다. | `<repo_root>/QGIS/agent-harness`를 반환한다(`name`의 소문자 `qgis/agent-harness`가 아님). 레포 테스트 `test_resolve_harness_path_prefers_install_subdirectory_for_qgis`가 같은 기대값이다. |
| T-04 | R-22, R-23 | scratch에 스크립트와 세 registry 사본을 두고 `generate_meta_skill.py`를 UTF-8 모드로 실행한다. | 종료 코드 0, `Generated meta-skill with 79 harness CLIs + 24 public CLIs + 5 matrices at <scratch>/cli-hub-skill/SKILL.md` 출력. 생성 파일은 428줄, `description`에 `103+`, 첫 `name`은 `cli-anything-hub`. 하니스 섹션 제목에 `### 3D`, `### Ai`, `### Knowledge-Management`, `### Science`, `### Scientific`이 따로 있다. |
| T-05 | R-22, R-23 | 위 사본에서 `public_registry.json`, `matrix_registry.json`을 지우고 다시 실행한다. | 종료 코드 0. `+ 0 public CLIs + 0 matrices`로 출력하고 "Curated Matrices" 표는 없으며 "CLI Matrices" 안내 절은 남는다. |
| T-06 | R-24 | 사본 `registry.json`의 첫 항목에서 `category`를 지우고, 이전 `cli-hub-skill/SKILL.md`(내용 `OLD`)가 있는 상태에서 실행한다. 별도로 `registry.json`이 없는 디렉터리에서도 실행한다. | 앞의 경우 종료 코드 1, `KeyError: 'category'`, 기존 파일 내용은 `OLD` 그대로. 뒤의 경우 종료 코드 1, `FileNotFoundError`. |
| T-07 | R-28 | zotero 항목(외부 `source_url`, `install_cmd` `pip install cli-anything-zotero`)을 `resolve_harness_path`에 넣는다. | `<repo_root>/zotero/agent-harness`를 반환한다(이름 규칙 3번). 그래서 날짜는 GitHub API가 아니라 로컬 `git log`로 정해진다. |
| T-08 | R-29 | 외부 항목 `{package_manager:"pip", install_cmd:"python -m pip install py4csr", source_url:null}`의 날짜를 구한다. | GitHub 단서가 없으면 PyPI 단계로 가서 패키지 이름 `py4csr`의 최신 파일 업로드일 앞 10자를 쓴다. 네트워크가 막히면 `homepage`/`docs_url` HEAD 단계로 가고 거기서도 실패하면 `null`이다. |
| T-09 | R-19 | `_source: "harness"`이고 `install_strategy`가 없는 항목 `{install_cmd: "cd sketch/agent-harness && npm install && npm link"}`로 `_install_strategy`를 호출한다. | `"pip"`를 반환한다(sketch, clibrowser 둘 다 확인). 이후 동작은 U-01. |
| T-10 | R-30 | `update_registry_dates.py` 실행 중 `api.github.com` 요청이 모두 예외를 낸다. | 해당 항목은 `null`이 되고 스크립트는 `Updated dates for 103 CLI entries`로 정상 종료한다. 이 사례는 코드 읽기로만 도출했다(네트워크 호출을 하지 않음). |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

**읽은 파일과 이유.** `CONTRIBUTING.md`(기여 문서이지만 "Registry fields" 표 53-123줄이 항목 필수 여부와 값 규칙을 정하는 유일한 설명이라 열었다), `.github/PULL_REQUEST_TEMPLATE.md`(같은 이유로 registry 관련 줄만), `.github/workflows/deploy-pages.yml`(두 스크립트의 실행 순서와 산출물 위치를 정하는 배포 설정이라 열었다), `.gitignore`(생성물 추적 여부), `docs/hub/openapi.json`(레포 안에서 registry 항목 스키마를 기계 형식으로 쓴 유일한 문서), `docs/hub/index.html`(웹 허브가 필드를 어떻게 읽는지, 해당 함수만). 테스트(`test_update_registry_dates.py`)는 `def test` 이름을 검색하고 qgis 사례 14-23줄만 열었다.

**전수 점검 방법.** 아래 점검은 모두 scratch 디렉터리의 스크립트를 `python -I`(필요하면 `-X utf8`)로 레포 루트에서 실행해 얻었다. 스크립트는 `json.load`로 항목을 읽고 `os.path`, `git ls-files`, 정규식으로 대조한다. 레포를 수정하지 않았고 점검 뒤 `git status --short`는 0줄이었다.
- 키·타입 분포: `registry.json` 79개, `public_registry.json` 24개의 모든 항목 키를 `Counter`로 세고 키 집합 조합을 비교했다.
- `#subdirectory=` 실재: 정규식 `git\+https://github\.com/HKUDS/CLI-Anything\.git#subdirectory=(\S+)`로 66개를 추출해 `os.path.isdir`와 `git ls-files` 경로 접두사(대소문자 포함)로 확인했다.
- `skill_md` 실재: URL이 아닌 63개를 `os.path.isfile`과 `git ls-files` 목록으로 확인했다.
- `entry_point`: 66개의 `setup.py`/`pyproject.toml`에서 `"<이름>=<모듈>:<함수>"`(setup.py) 또는 `<이름> = "<모듈>:<함수>"`(`[project.scripts]`) 문자열을 정규식으로 뽑아 비교했다. sketch는 `package.json`의 `bin` 키(`sketch-cli`), zotero는 `setup.py` 줄 58을 눈으로 확인했다. 정규식이므로 `console_scripts` 블록 밖의 같은 모양 문자열을 잘못 집을 가능성은 이론상 남는다.
- 버전·패키지 이름: 같은 파일에서 `version=`/`PACKAGE_VERSION`/`name=`/`PACKAGE_NAME` 정규식 추출.
- 설치 전략: `installer.py`의 `_install_strategy`를 `ast`로 잘라 `exec`한 뒤 103개 항목에 적용했다(`_source`는 파일에 따라 부여).
- 날짜 경로: `update_registry_dates.py`를 `importlib`로 읽어(`-B`로 `.pyc` 생성 방지) `resolve_harness_path`, `get_last_modified`, `extract_external_source_url`을 103개 항목에 적용했다(네트워크 함수는 호출하지 않음).

| R-ID / T-ID | 근거 (repo@34f5195 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | `registry.json:2-7`, `public_registry.json:2-7`, `matrix_registry.json:2-20`(`matrices`, `meta.schema_doc`) | 세 파일 최상위 키 출력. `matrix_registry.json`의 `meta.schema_doc`이 가리키는 `docs/cli-matrix/matrix_registry.schema.md`는 `git ls-files | grep -i schema` 결과에 없고 `ls docs`에도 `cli-matrix`가 없다(2.3). |
| R-02 | 전수 스크립트(`name`, `entry_point`, 소문자 `name` 각각 `Counter`), 합집합 `r & p` 빈 집합 | 부재·전칭 주장이다. 범위는 SHA의 두 파일 103개이고 이후 추가분은 해당 없다. |
| R-03, R-04 | `registry.json:719-732`(qgis), `registry.json:1383-1402`(siyuan, 줄 1392 `install_strategy`), 키 집합 `frozenset` 비교 결과 3종(77/1/1) | 전수. `requires` null은 mermaid(줄 511 근처 항목), macrocli, `skill_md` null 줄은 `registry.json:132, 246, 520, 781, 990`. |
| R-05 | 키 `Counter` 결과(`public_registry.json` 24개), `public_registry.json:209`(android-cli), `:323`(obsidian-cli), `:347`(py4csr), `:409`(arcgis-pro) | `platform`/`engines` 소비처 없음 주장: `grep -rn -E "\"platform\"|'platform'|engines" cli-hub/cli_hub/*.py docs/hub/index.html`에서 `analytics.py`의 `platform.system()`(실행 OS 이름이라 registry 필드가 아님)만 나왔다. 놓칠 수 있는 곳: `cli-hub-matrix/`, 다른 클라이언트(`docs/hub/*.md`, `llms*.txt`) 본문. `docs_url`은 `update_registry_dates.py:267`만 읽는다. |
| R-06 | 정규식 `\d+\.\d+\.\d+` 전수, 외부 `version` `Counter` | 전수. |
| R-07 | `docs/hub/openapi.json:156-199`(`category: string`, `required: [name, description, category]`), `CONTRIBUTING.md:71`, `.github/scripts/generate_meta_skill.py:33-34, 99-101`(`.title()`), `cli-hub/cli_hub/cli.py:211-217`(`upper()`) | `category` 값 목록은 `Counter`. 합쳐 35가지. 뜻이 겹치는 쌍은 값 이름 유사성과 항목 설명을 보고 정한 것이라 판단이 들어갔다(`science`/`scientific` 외 `graphics`/`image`/`design`/`3d`의 겹침 여부는 따지지 않았다). 생성 결과는 scratch 실행(T-04)에서 `grep -n "^### "`로 확인. |
| R-08 | `docs/hub/index.html:2506-2508`(`source_url ? Source : tree/main/<name>/agent-harness`), 교차 집합 계산(`source_url` 있는 집합 == `skill_md`가 URL인 집합, `non-monorepo` 13개 중 `source_url` 없음은 clibrowser, sketch) | 링크가 실제 깨지는지는 GitHub 동작에 달려 있어 `추론`으로 두었다. |
| R-09 | `CONTRIBUTING.md:68`(형식), 66개 `isdir` 전수, `name != <dir>`는 qgis, 3mf만 | `.github/scripts/tests/test_update_registry_dates.py:14-23`가 qgis에서 `install_cmd`의 `<dir>`을 우선하는 의도를 보여 준다. |
| R-10 | 66개 정규식 일치 결과(불일치 0), `sketch/agent-harness/package.json:6-8`(`bin` `sketch-cli`), `zotero/agent-harness/setup.py:56-58`(`cli-anything-zotero`) | `registry.json`의 나머지 11개(zotero, sketch를 뺀 외부 저장소 10개와 clibrowser)와 `public_registry.json` 24개는 코드가 이 레포에 없어 점검하지 못했다. 그래서 "전부 일치" 주장은 68개 범위다. |
| R-11 | `CONTRIBUTING.md:70`, `registry.json:781, 990`(null), `registry.json:719-732`(qgis의 패키지 사본 경로), `docs/hub/index.html:2156-2160, 2169-2172, 2175-2178`(`repoSkillId`, `harnessSkillCmd`, `renderSkillAction`) | 상대 경로 63개 존재는 전수. URL 11개 도달 여부는 미확인. |
| R-12 | `ls skills`와 `skill_md` 접두사 집합 차집합(14개), `rekordbox`·`iterm2-ctl`이 세 registry에 없다는 점은 `grep -il rekordbox registry.json public_registry.json matrix_registry.json`에 파일 없음(README만 일치) | iterm2-ctl은 `grep -n iterm2 registry.json`에서 `iterm2` 항목만 나왔다. 패키지 이름과 `skills/` 이름이 같다는 점은 `setup.py`의 `name=`과 대조했다(`cc-switch`→`cli-anything-ccswitch`는 `cc-switch/agent-harness/setup.py:5`). |
| R-13 | `ls -d */agent-harness`(69개)와 `#subdirectory=` 집합 차집합(rekordbox, sketch, zotero) | rekordbox 항목 부재: 위 `grep -il` 결과. 놓칠 가능성: 다른 이름(`rekordbox-cli` 등)으로 등록된 경우는 `grep -i rekordbox`가 이름 일부를 잡으므로 없다고 판단했다. |
| R-14 | `registry.json:730-731`, `docs/hub/index.html:2514-2518`, `cli-hub/cli_hub/cli.py:291-294` | `CLI-Anything-Team` 단독 기여자 항목 수 10은 전수 계산. |
| R-15 | `freecad/agent-harness/setup.py:7`(`1.0.0`), `registry.json` freecad 항목(줄 791 근처 `1.1.0`), `CONTRIBUTING.md:119-123` | 66개 중 `setup.py`에서 버전을 추출하지 못한 mubu, joplin(상수 `PACKAGE_VERSION`)은 정규식을 `PACKAGE_VERSION`까지 넓혀 비교했다. |
| R-16 | C-01(`registry.py:9-70`) | 코드만 읽었다. 네트워크 동작은 실행하지 않았다. |
| R-17 | C-01(`registry.py:93-117`), `cli-hub/cli_hub/cli.py:191` | 코드 확인. |
| R-18 | C-02(`installer.py:106-119`), `installer.py:301-312`(`_perform_action`의 전략별 핸들러 표), 103개 적용 결과 | 전략 문자열이 표에 없으면 `command`로 간다(`actions.get(strategy, actions["command"])`). |
| R-19 | `installer.py:184-192`(`_pip_install`), `registry.json:772-790`(sketch, 줄 779 `install_cmd`), `:981-996`(clibrowser, 줄 988) | 분기는 `_install_strategy` 103개 적용으로 확인했고, pip 호출 결과는 실행하지 않아 `추론`이다(U-01). |
| R-20 | `installer.py:195-203`(`_pip_uninstall`: `f"cli-anything-{cli['name']}"`), 패키지 이름 대조 | pip의 `_`/`-` 정규화는 pip 공식 동작(미확인, 일반 지식). |
| R-21 | `cli-hub/cli_hub/cli.py:191-217, 262-295`, `installer.py:122-129, 184-192, 315-330`, `registry.py:102-117`, `generate_meta_skill.py:34, 38, 106-110, 128-135` | 키별 `[]`/`.get` 사용을 줄 단위로 읽었다. `cli-hub/cli_hub/matrix.py`, `preview.py`의 사용은 범위 밖이라 보지 않았다. 부재·전칭 주장이므로 범위는 `cli.py`, `installer.py`, `registry.py`, 생성기다. |
| R-22 | C-03, C-05(`generate_meta_skill.py:8-27, 200-205`), 파일 전체 `open()`·`write_text()` 호출에 `encoding` 인자 없음 | T-04의 UTF-8 모드 없는 실행이 cp949에서 `UnicodeDecodeError`. |
| R-23 | C-03~C-05, T-04, T-05 | 출력 줄 수 428, 헤더 확인은 scratch 출력물. |
| R-24 | `generate_meta_skill.py:14-15, 34, 106-110, 200-201`(쓰기가 마지막), T-06 | Actions의 "step 실패 시 뒤 step 생략"은 GitHub Actions 일반 동작이라 레포 코드로는 확인할 수 없다(`deploy-pages.yml`에 `if: always()`나 `continue-on-error`가 없음은 `grep -n "always\|continue-on-error" .github/workflows/deploy-pages.yml` 무결과로 확인). |
| R-25 | `cli-hub-meta-skill/SKILL.md:1-5, 60-62`, `generate_meta_skill.py:2, 12, 43`, `.gitignore:48-49`(`/cli-hub-skill/`), `.gitignore:42`(`!/cli-hub-meta-skill/`), `deploy-pages.yml:57` | scratch 생성물과 추적 파일을 `diff`했고 첫 diff가 `name:` 줄이다. 메인 세션이 처음 가정한 "생성기가 `cli-hub-meta-skill/SKILL.md`를 만든다"는 이 SHA에서 성립하지 않는다. |
| R-26 | C-10(`deploy-pages.yml:3-18, 43-69`) | 파일 전체를 읽었다. 환경변수 secret 값은 레포에서 볼 수 없다. |
| R-27 | C-09(`update_registry_dates.py:308-322`) | 코드 확인. `docs/hub/registry-dates.json`이 SHA에 없음은 `git ls-files | grep registry-dates` 무결과. |
| R-28 | C-07, T-03, `test_update_registry_dates.py:14-23`, 103개 적용 결과(66 install_subdir / 2 name_fallback / 11 none, 외부 registry 24 none) | `get_last_modified`의 날짜 값은 얕은 clone이라 신뢰하지 않았고 경로 분기와 `None` 여부만 확인했다. |
| R-29 | C-06, C-08(`update_registry_dates.py:60-84, 125-135, 138-217, 256-305`) | 코드 확인. 각 외부 서비스의 응답 형식은 코드가 가정한 것이다(실제 API 응답은 미확인). |
| R-30 | `update_registry_dates.py:60-84, 87-101, 313-322`(예외 처리 범위와 쓰기 순서) | `except Exception`, `except (CalledProcessError, ValueError)` 범위를 줄 단위로 확인했다. `subprocess.run`의 `FileNotFoundError`가 잡히지 않는다는 판단은 `except` 절 목록에서 도출한 것이고 실행하지는 않았다. |
| R-31 | `docs/hub/index.html:1553-1554, 1810-1821, 2052-2054, 2523-2524`, `docs/hub/openapi.json`(`/registry-dates.json`) | 코드 확인. `.gitignore`에 `registry-dates.json` 항목은 없지만 추적 파일이 아니다. |
| R-32 | `registry.json:2-6`, `public_registry.json:2-6`, `generate_meta_skill.py:195-197` | "읽는 곳 없음" 검색: `grep -rn -E "\[.meta.\]|get\(.meta.|\.meta\b" cli-hub/cli_hub/*.py docs/hub/index.html .github/scripts/*.py`에서 생성기 두 줄만 일치(`preview.py`의 CSS `.meta-grid`는 무관). 놓칠 수 있는 곳: `docs/hub`의 다른 HTML·JS. `git log -1 --format=%ci -- registry.json`은 2026-08-21, `meta.updated`는 2026-06-19. |
| R-33 | 검색: `grep -rIl "registry\.json" .` 결과 중 검증 로직 후보는 `.github/scripts/pr-labeler.js`(라벨링), `.github/labeler.yml`, `mubu/…/test_agent_harness.py:54`(`registry.json` 파일 존재만 확인), 생성기, 날짜 갱신기뿐이다. 워크플로는 `grep -n -i registry .github/workflows/*.yml`에서 `deploy-pages.yml`만 일치. `.github/PULL_REQUEST_TEMPLATE.md:30, 40-42, 51`은 수동 체크리스트 | 부재 주장. 범위는 SHA의 추적 파일 전체 `grep`(확장자 제한 없음). 놓칠 가능성: 외부 CI(레포 밖), 클라이언트 쪽 런타임 검증(`cli-hub`의 코드는 읽음). `test_update_registry_dates.py`를 실행하는 워크플로도 없다(`grep -rn "test_update_registry_dates\|pytest" .github/workflows` 무결과). |
| R-34 | `grep -rIn -E "registry\.json\|public_registry" cli-anything-plugin codex-skill hermes-skill reasonix-skill cursor-plugin opencode-commands qoder-plugin skill_generation openclaw-skill`에서 `hermes-skill/SKILL.md:123`, `reasonix-skill/SKILL.md:155`만 일치, `grep -n -E "registry\|cli-hub" cli-anything-plugin/HARNESS.md`는 `registry`가 앱 내부 레지스트리를 뜻하는 줄 495와 `cli-hub previews` 언급(줄 276, 508, 570, 576)뿐 | 부재 주장. `HARNESS.md` 전문을 다시 읽지는 않았고 검색에 의존했다. `commands/*.md`는 `grep -n -i registry`로만 확인했다. `CONTRIBUTING.md:21, 33`과 PR 템플릿이 항목 추가를 요구하는 유일한 위치이고, 둘 다 `registry.json`만 언급하며 `public_registry.json`에 추가하는 절차는 어디에도 쓰여 있지 않다. |
| R-35 | 이름 목록 정렬 비교(`names != sorted(names)`), `generate_meta_skill.py:106, 128`(`sorted(..., key=name)`), `cli.py:215`(`sorted(by_cat[cat], key=name)`), `docs/hub/index.html:2043-2054`(정렬 상태) | 이어 붙이는 관례라는 추정은 마지막 항목들이 최근 외부 CLI라는 관찰에서 나온 추론이다. |
| T-01~T-03 | 위 R-03, R-05, R-09, R-18, R-28 근거와 같다 | scratch 실행(T-01, T-02, T-03). T-03의 qgis는 레포 테스트가 같은 기대를 갖는다. |
| T-04~T-06 | scratch 디렉터리 `gen`(전체 입력), `gen3`(public·matrix 제거), `gen2`(`category` 삭제 + 기존 출력 `OLD`), `gen4`(registry 없음) | 직접 실행 결과. 로그는 저장하지 않았다. |
| T-07~T-10 | R-28, R-29, R-19, R-30 근거와 같다 | T-07은 `resolve_harness_path` 실제 호출, T-08·T-10은 코드 읽기만, T-09는 `_install_strategy` 실제 호출(sketch, clibrowser 모두 `pip`). |

**문서 대 실제 차이**(구현을 사실로 쓰고 차이만 남긴다)

| 문서 | 문서의 주장 | 실제 |
|---|---|---|
| `CONTRIBUTING.md:59-72` | 12개 필드가 모두 필수(`Required: Yes`), `contributors`는 `{name, url}` 배열 | qgis는 `source_url` 없음, `contributors` 대신 `contributor`·`contributor_url`(`registry.json:730-731`). 필수 키 중 `contributors`는 78/79다. |
| `CONTRIBUTING.md:70` | in-repo `skill_md`는 `skills/cli-anything-<sw>/SKILL.md` 형식의 상대 경로이고 아직 없으면 `null` | 7개가 패키지 안 사본 경로를 쓰고(R-11), `null` 5개 중 3개(adguardhome, comfyui, mermaid)는 `skills/`에 파일이 이미 있다(R-12). |
| `CONTRIBUTING.md:68` | `install_cmd`는 "Full pip install command" | sketch(`cd … && npm install && npm link`), clibrowser(`cargo install --git …`)는 pip 명령이 아니다(R-19). |
| `CONTRIBUTING.md:66` | `homepage`는 대상 앱의 공식 홈페이지이며 자기 레포가 아님 | cc-switch, slay_the_spire_ii, macrocli는 이 레포 URL이다(전수 계산: `homepage`가 `https://github.com/HKUDS/CLI-Anything`로 시작하는 항목). |
| `CONTRIBUTING.md:71` | `category`는 "기존 값 중 하나" | 열거형이 아니고 뜻이 겹치는 값 쌍이 있다(R-07). |
| `CONTRIBUTING.md:121` | 수정 시 `version`을 올린다 | freecad는 registry `1.1.0` ≠ `setup.py` `1.0.0`(R-15). |
| `CONTRIBUTING.md:53` | "허브가 `main`의 `registry.json`을 직접 읽어 merge 즉시 반영된다" | `cli-hub`는 Pages에 배포된 사본을 받아 1시간 cache한다(R-16). 웹 허브는 상대 경로 사본을 먼저 쓰고 `raw.githubusercontent.com/…/main`을 대체로 쓴다(`docs/hub/index.html:1545-1548`). |
| `.github/PULL_REQUEST_TEMPLATE.md:30` | in-repo 항목은 `source_url: null` | qgis는 키가 없다(`undefined`로 읽힘, 웹 허브는 falsy라 같은 링크를 만든다). |
| `docs/hub/openapi.json:156-199` | `CliEntry`의 `required`는 `name`, `description`, `category`이고 `skill_md`는 `type: string` | `skill_md` `null`이 5개(`registry.json`)다. 선언되지 않은 키(`requires`, `source_url`, `contributors`, `install_strategy` 등)는 `additionalProperties: true`로 허용된다. |
| `.github/scripts/generate_meta_skill.py:2` | docstring은 출력이 `cli-hub-skill/SKILL.md` | 코드도 같다(줄 12). 메인 세션과 `next.md`가 적은 `cli-hub-meta-skill/SKILL.md`는 생성 대상이 아니다(R-25). |

### 2.2 코드 읽는 순서 [선택]

1. `registry.json` 앞 두 항목과 qgis(719-732), siyuan(1383-1402), sketch(772-790)를 보며 키 집합 3종을 눈에 익힌다.
2. `public_registry.json`에서 `feishu`(npm)와 `android-cli`(bundled)를 비교한다.
3. `cli-hub/cli_hub/registry.py`(117줄)로 두 파일이 어떻게 합쳐지는지 보고, `installer.py:106-119`로 `install_strategy`가 필드로 어떻게 소비되는지 본다.
4. `.github/workflows/deploy-pages.yml`로 두 스크립트의 실행 순서를 보고, `generate_meta_skill.py`(208줄, 선형)와 `update_registry_dates.py`(분기는 `resolve_harness_path`와 `get_external_date`)를 읽는다.
5. `CONTRIBUTING.md:53-123`을 마지막에 읽고 2.1의 "문서 대 실제 차이" 표와 맞춰 본다.

### 2.3 비교·재사용 출처 [선택]

같은 기능을 다룬 다른 레포 스펙은 없다. 같은 레포 안의 `matrix_registry.json`과 구조를 대조한 결과만 남긴다(범위 밖, 코드 확인).

- 최상위 배열이 `clis`가 아니라 `matrices`이고, `meta`에 `schema_doc: "docs/cli-matrix/matrix_registry.schema.md"`가 더 있다. 이 문서는 기준 SHA에 없다.
- 항목 키는 `name`, `display_name`, `version`, `schema_version`, `description`, `category`, `matrix`, `matrix_id`, `homepage`, `skill_md`, `clis`, `capabilities`, `recipes`, `known_gaps`, `suggest_to_user_template`로 하니스·외부 항목과 완전히 다르다.
- `clis`는 하니스·외부 항목의 `name` 문자열 목록이고, 5개 matrix의 참조가 모두 두 registry 합집합에서 해석된다(미해석 0). 그래서 registry의 `name`은 외부에서 참조되는 키다.
- `skill_md`는 `cli-hub-matrix/<name>/SKILL.md` 상대 경로이고 생성기 matrix 표가 `` `{skill}` ``로 출력한다(R-23).

### 2.4 검토 기록 [필수, ready 스펙]

- 방식: 미수행(`draft`). 작성자가 전수 스크립트로 자체 대조했을 뿐이고 메인 점검과 독립 검토는 받지 않았다.
- 대조한 R-ID: 해당 없음.
- 대조하지 않은 R-ID: R-01~R-35 전부.
- 재구현: 미수행.

## 적용 메모 [선택]

Claude Code에서 "앱 → CLI + skill" 생성 절차를 설계할 때 원본과 다르게 둘 후보다. 원본의 미결정(U-01, U-02)을 해소한 것으로 치지 않는다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-03, R-14, R-33 | 항목에 필수 키 집합과 `contributors`만 허용하는 검증 step을 둔다. | 원본은 문서(CONTRIBUTING)와 실제(qgis)가 다르고 이를 막는 검사가 없다. | 생성 절차 마지막 단계에서 항목 검증이 실패하면 생성 실패로 끝난다. T-01의 키 집합 3종은 1종이 된다. |
| R-07 | `category`를 열거형으로 두고 별칭 쌍(`science`/`scientific` 등)을 하나로 정한다. | 값마다 섹션이 따로 생겨 같은 분야가 갈린다. | 항목 검증이 `category` 허용 값 목록을 가진다. |
| R-11, R-12 | `skill_md` 형태를 `skills/<id>/SKILL.md` 하나로 통일하고 `skill_md`가 `null`이면 `skills/`에 파일이 없어야 한다는 규칙을 둔다. | 원본은 4가지 형태가 섞여 웹 허브만 (a) 형태에서 설치 명령을 만든다. | 항목의 `skill_md`와 `skills/` 디렉터리의 일치를 검증한다. |
| R-18, R-19 | `install_cmd`가 pip 형식이 아니면 `install_strategy`를 필수로 요구한다. | 원본은 하니스 항목의 기본 전략이 `pip`라 sketch, clibrowser의 `install_cmd`가 pip로 넘어간다(U-01). | 항목 검증이 `install_cmd`의 첫 토큰과 `install_strategy`를 대조한다. |
| R-25 | 생성 대상 파일 이름과 추적 여부를 하나로 정한다. | 원본은 생성물(`cli-hub-skill/`, 비추적)과 손 문서(`cli-hub-meta-skill/`, 추적)가 비슷한 이름으로 공존한다. | 생성 단계의 출력 경로와 배포 대상이 문서에 명시된다. |
