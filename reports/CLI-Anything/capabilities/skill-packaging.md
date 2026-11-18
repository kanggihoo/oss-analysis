---
sha: "34f519533bc175d2fe287ab8316b0dd99bb9cc43"
created: 2026-11-18
updated: 2026-11-18
sources:
  - cli-anything-plugin/skill_generator.py
  - cli-anything-plugin/templates/SKILL.md.template
  - cli-anything-plugin/guides/skill-generation.md
  - cli-anything-plugin/HARNESS.md
  - cli-anything-plugin/commands/cli-anything.md
  - cli-anything-plugin/repl_skin.py
  - .github/scripts/sync_root_skills.py
  - .github/scripts/validate_root_skills.py
  - .github/workflows/check-root-skills.yml
  - .github/scripts/generate_meta_skill.py
  - skills/README.md
  - skills/cli-anything-gimp/SKILL.md
  - gimp/agent-harness/cli_anything/gimp/gimp_cli.py
  - iterm2/agent-harness/setup.py
depends:
  - ../capabilities/harness-contract.md
status: draft
---

# SKILL.md 생성·루트 skills/ 동기화

> 하니스 디렉터리(`<sw>/agent-harness`)를 입력으로 받아 AST로 CLI 메타데이터를 뽑아 `SKILL.md`를 쓰고, 하니스 안의 `SKILL.md`를 루트 `skills/<skill-id>/SKILL.md`로 복사(name 정규화)하며, CI가 그 복사본의 일치를 검사하는 패키징 절차를 정의한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 입력은 `gimp/agent-harness`다. 단계 1, 4, 5는 사람이나 에이전트가 직접 실행한다. 이 레포에는 이 단계를 자동으로 부르는 hook이나 workflow가 없다(R-23).

1. 에이전트가 HARNESS.md Phase 6.5 지시에 따라 `python skill_generator.py <sw>/agent-harness`를 실행한다(수동, R-23).
2. `extract_cli_metadata`가 `cli_anything/<pkg>/README.md`(첫 문단 → 소개, apt/brew 설치 명령 → system package), `setup.py`(version), `<pkg>_cli.py`(Click 데코레이터 → 명령 그룹·명령)를 읽어 `SkillMetadata`를 만든다(R-01~R-12). 예시는 고정 문구 2개에 조건부 1개다(R-13).
3. `generate_skill_md`가 Jinja2 template으로 렌더링한다. Jinja2가 없거나 template 파일이 없으면 `generate_skill_md_simple`로 폴백한다(R-14).
4. `generate_skill_file`이 같은 내용을 두 곳에 쓴다. 기본값은 루트 `skills/<skill_name>/SKILL.md`와 하니스 안 `cli_anything/<pkg>/skills/SKILL.md`다(R-16).
5. 사람이나 에이전트가 하니스 안 `SKILL.md`를 필요하면 직접 고친다. 현재 `skills/`의 `SKILL.md` 70개 중 상당수가 생성기 출력 형태를 벗어나 있다(R-25).
6. `sync_root_skills.py`(수동 실행)가 `*/agent-harness/cli_anything/*/skills/SKILL.md`와 `.../*/SKILL.md`를 찾아 각각 `skills/<id>/SKILL.md`로 쓴다. 이때 `name` frontmatter를 `<id>`로 바꾼다. 내용이 같으면 건너뛰고, 다르면 덮어쓰며, 지우는 동작은 없다(R-17~R-20).
7. `check-root-skills.yml`이 PR과 `main` push에서 `validate_root_skills.py`만 실행한다. 복사본이 없거나 기대값과 다르면 exit 1로 실패한다(R-21, R-22).
8. 설치 표면은 `skills/`이고, `npx skills add HKUDS/CLI-Anything --skill <id>`로 고른다는 것이 README의 설명이다(R-26, 외부 도구 동작은 미확인).

### 1.2 범위·통합 지점 [필수]

- 제공: (a) 하니스 디렉터리에서 `SKILL.md`를 만드는 생성기, (b) 하니스 안 `SKILL.md`를 루트 `skills/`로 옮기는 동기화 스크립트, (c) 일치 검사 CI, (d) 루트 `skills/` 디렉터리 배치 규칙.
- 제외: 하니스 CLI 구현 자체(형제 스펙 harness-contract), `registry.json` 형식(형제 스펙 registry-schema), cli-hub 설치기. `.github/scripts/generate_meta_skill.py`(registry에서 meta-skill을 만드는 스크립트)도 제외한다. 이 스크립트의 출력 경로는 `cli-hub-skill/SKILL.md`이고 `skills/cli-hub-meta-skill/`을 만들지 않는다(R-24). 하니스 안에 따로 복제된 `mubu/agent-harness/skill_generator.py`(434줄), `zotero/agent-harness/skill_generator.py`(297줄)는 열어 보지 않았다(확인 한계).
- 외부 의존·선행 계약:
  - harness-contract가 정하는 입력 구조를 생성기가 가정한다. 이 스펙은 입력으로 읽는 부분만 정의한다. `<sw>/agent-harness/setup.py`, `<sw>/agent-harness/cli_anything/<pkg>/__init__.py`, `.../<pkg>/README.md`, `.../<pkg>/<pkg>_cli.py`. 생성기는 `cli_anything/` 아래에서 `__init__.py`가 있는 디렉터리를 하니스 패키지로 취급한다(R-01).
  - Jinja2는 선택 의존이다. 이 레포 어디에도 생성기용 jinja2 의존 선언이 없다(R-14, 2.1 검색 범위).
  - `ReplSkin`(`cli-anything-plugin/repl_skin.py`)은 `skills/<skill-id>/SKILL.md`를 위로 거슬러 올라가며 찾아 배너에 경로를 표시한다. 이 표시 규칙은 harness-contract 소관이고, 여기서는 skill id를 정하는 세 번째 규칙이라는 점만 쓴다(R-18).
  - `npx skills add`는 레포 밖 도구다. 입력은 `--skill <id>`, 정상 결과는 해당 skill 설치다. 실제 매칭 방식은 미확인이다(U-01).
- 소유 상태·부작용:
  - 생성기: 루트 `skills/<skill_name>/SKILL.md`(없으면 디렉터리 생성), 하니스 안 `cli_anything/<pkg>/skills/SKILL.md`를 쓴다. 기존 파일은 확인 없이 덮어쓴다.
  - 동기화: 루트 `skills/<id>/SKILL.md`만 쓴다. 하니스 안 소스는 바꾸지 않는다. 지우는 동작이 없다.
  - validate: 읽기 전용이다.

### 1.3 인터페이스와 데이터 의미 [필수]

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `python skill_generator.py <harness_path> [-o/--output PATH] [-t/--template PATH]` | harness_path: string(`agent-harness` 디렉터리). 출력: stdout `Generated: <path>` | `-o`를 주면 그 경로에 쓰고, 하니스 안 복사본은 항상 따로 쓴다(R-16). 오류(ValueError, SyntaxError)는 잡지 않아 traceback과 함께 종료한다. |
| `extract_cli_metadata(harness_path)` | string → `SkillMetadata` | `skill_name`, `skill_description`, `software_name`(= `cli_anything/` 아래 패키지 디렉터리 이름, 밑줄 유지), `skill_intro`, `version`, `system_package`(optional), `command_groups`, `examples`. |
| `CommandGroup` / `CommandInfo` / `Example` | `name`, `description`, `commands` / `name`, `description` / `title`, `description`, `code` | 모두 문자열. 그룹 순서는 소스 파일의 줄 순서다. |
| `generate_skill_md(metadata, template_path?)` | → string | Jinja2 template 또는 simple 폴백. 두 출력은 절 구성이 다르다(아래 표). |
| `generate_skill_file(harness_path, output_path?, template_path?)` | → string(쓴 경로) | R-16. |
| `sync_root_skills.py` | 인자 없음. stdout에 `create:`/`overwrite:` 줄과 `Synced N root skill(s); M already up to date.` | 항상 exit 0이다(R-20). |
| `validate_root_skills.py` | 인자 없음. exit 0 / 1 | R-21. |
| frontmatter `name` | string | template은 `name: >-` 접힌 스칼라(줄바꿈 후 값), simple은 `name: "<id>"`. sync가 쓰면 항상 `name: "<id>"`로 바뀐다(R-19). |
| frontmatter `description` | string | `Command-line interface for <Display>` 뒤에 소개가 있으면 ` - <소개 100자>` + 100자 초과 시 `...`(R-04). simple은 큰따옴표로 감싸고 내부 `"`를 이스케이프하지 않는다(R-14). |

SKILL.md 절별 출처. 고정 문구는 값이 하니스와 무관하다.

| 절 | 값의 출처 | Jinja2 template | simple 폴백 |
|---|---|---|---|
| `# <skill_name>` + 소개 문단 | `skill_name`, `skill_intro` | 있음 | 있음 |
| Installation / Prerequisites | `pip install cli-anything-<software_name>`(밑줄 원문). `system_package`가 있으면 `Install <software_name>: ...` 줄 추가 | `<software_name> must be installed`(원문 이름) | `<Display> must be installed`(Display 이름) |
| Usage / Basic Commands | 고정 문구(`project new -o project.json`, `--json project info -p project.json`) | 있음 | 있음 |
| REPL Mode | 고정 문구 | 있음 | 없음 |
| Command Groups | `command_groups`. 그룹마다 `### <name>`, 설명, `\| Command \| Description \|` 표 | 그룹 명령이 0개여도 표 머리를 출력 | 명령이 0개면 표를 생략. 그룹이 하나도 없으면 절 자체 생략(둘 다) |
| Examples | `examples`(R-13) | 있음 | 있음 |
| State Management / Output Formats | 고정 문구(`Up to 50 levels` 등) | 있음 | 없음 |
| For AI Agents | 고정 5항목 | 있음 | 있음 |
| More Information | 고정 문구(README, TEST.md, HARNESS.md 참조) | 있음 | 없음 |
| Version | `version` | 있음 | 있음 |

skill id를 정하는 규칙은 세 곳이다.

| 위치 | 규칙 | 4개 사례의 결과 |
|---|---|---|
| 생성기 `_canonical_skill_name` | 하니스 경로의 마지막이 `agent-harness`면 그 부모 디렉터리 이름, 아니면 패키지 이름. `_`를 `-`로 바꾼다. 소문자 변환은 없다 | `3MF` → `cli-anything-3MF`, `QGIS` → `cli-anything-QGIS`, `cc-switch` → `cli-anything-cc-switch`, `iterm2` → `cli-anything-iterm2` |
| sync `_canonical_skill_id` | 소스 경로에서 `cli_anything` 다음 부분(패키지 이름). `_`를 `-`로 바꾼다. 소문자 변환은 없다 | `cli-anything-threemf`, `cli-anything-qgis`, `cli-anything-ccswitch`, `cli-anything-iterm2-ctl` |
| `ReplSkin.skill_id` | 소프트웨어 이름을 소문자화하고 `-`를 `_`로 바꾼 뒤 별칭표(`iterm2_ctl` → `iterm2`)를 적용하고 `_`를 `-`로 바꾼다 | `iterm2_ctl` → `cli-anything-iterm2`, 나머지는 패키지 이름 기준 소문자 |

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `extract_cli_metadata`에 하니스 경로를 준다 | `<harness>/cli_anything`이 없으면 `ValueError`("cli_anything directory not found"). 그 아래에 `__init__.py`가 있는 하위 디렉터리가 없으면 `ValueError`("No CLI package found"). 둘 이상이면 `iterdir()` 순서의 첫 번째를 쓴다(정렬 없음, 어느 것이 첫째인지는 파일시스템에 따라 다름). `software_name`은 그 디렉터리 이름이다 | 코드 확인 (C-14) |
| R-02 | `<pkg>/README.md`가 있다 | 소개는 C-01의 규칙으로 뽑는다. 줄을 `strip`한 뒤, 첫 `# ` 제목 줄 이후 첫 비어 있지 않은 줄들을 다음 빈 줄 전까지 공백 하나로 이어 붙인다. `##`로 시작하는 줄을 만나면 거기서 멈춘다. 제목 앞의 줄은 무시한다. 제목 바로 아래의 배지·이미지·인용 줄도 소개에 들어간다 | 코드 확인 (C-01) |
| R-03 | README가 없다 / README는 있지만 소개 줄이 하나도 없다(제목이 없거나 제목 뒤가 곧바로 `##`) | README 없음: `skill_intro`는 빈 문자열, `system_package`는 None. 소개 줄 없음: `skill_intro`는 고정 문자열 `CLI interface for the software.` | 코드 확인 (C-01, C-14) |
| R-04 | `skill_intro`가 있다 / 없다 | 있으면 `Command-line interface for <Display> - <intro[:100]>`, `len(intro) > 100`이면 뒤에 `...`. 없으면 `Command-line interface for <Display>`. `<Display>`는 `software_name`의 `_`·`-`를 공백으로 바꾸고 `.title()`한 값이다(`unimol_tools` → `Unimol Tools`) | 코드 확인 (C-14, C-08) |
| R-05 | README에 설치 명령이 있다 | C-02의 정규식을 `apt install`, `brew install`, `apt-get install` 순으로 시도하고 먼저 일치한 하나만 쓴다. 백틱 안에 `apt install <패키지 하나>`만 있어야 일치한다. `sudo`가 앞에 붙거나 패키지가 둘이면 일치하지 않는다. 결과는 `apt install X` 등 sudo 없는 문자열이다. 일치가 없으면 None | 코드 확인 (C-02) |
| R-06 | `<harness>/setup.py`가 있다 | 정규식 `version\s*=\s*["']([^"']+)["']`의 첫 일치를 version으로 쓴다. 일치가 없거나(`version=VERSION` 같은 변수 참조 포함) 파일이 없으면 `1.0.0`이다. 빈·깨진 `setup.py`도 `1.0.0`이다 | 코드 확인 (C-02) |
| R-07 | CLI 파일 | 읽는 파일은 `cli_anything/<software_name>/<software_name>_cli.py` 하나다. 없으면 `command_groups`는 빈 목록이고 오류도 경고도 없다. 있는데 Python 문법 오류가 있으면 `ast.parse`의 `SyntaxError`가 그대로 올라가 생성이 중단된다 | 코드 확인 (C-04, C-14) |
| R-08 | 함수에 붙은 데코레이터 | C-03의 모양만 그룹·명령으로 인식한다. `<이름>.group` 또는 `<이름>.command`(호출 여부 무관)이고 `<이름>`이 단순 `Name`이어야 한다(`@cli.group()`, `@click.command()`, `@filter_group.command("x")` 인식). `@group()`처럼 import한 이름, `@a.b.command()`처럼 속성이 중첩된 형태, 변수에 대입해 만든 `click.Group(...)`은 인식하지 못하고 조용히 무시한다. 이름은 첫 위치 인자(문자열 상수), 없으면 `name=` 키워드, 그것도 없으면 함수 이름에서 `_`를 `-`로 바꾼 값이다. 함수가 여러 데코레이터를 가지면 처음 일치한 하나만 본다. 중첩 함수도 `ast.walk`로 찾는다 | 코드 확인 (C-03, C-04) |
| R-09 | 그룹 함수(`.group` 데코레이터)들 | 줄 번호 순으로 처리한다. 표시 이름은 선언 이름을 title-case 한 값이다(`filter` → `Filter`, 이름이 없는 `cli` → `Cli`). 소유자가 `click`이거나 이미 그룹으로 등록된 `click` 소유 루트 그룹이면 경로는 `[이름]`이다(루트 그룹의 자식도 최상위 취급). 그 밖에는 소유자 그룹의 경로가 이미 처리됐으면 `[...소유자 경로, 이름]`, 아니면 `[소유자 변수 이름의 title-case, 이름]`이다. 그룹 이름은 경로를 공백으로 이은 문자열이다(`Filter Preset`). 루트 그룹(`@click.group(...) def cli`)도 `Cli`라는 그룹으로 목록에 들어간다 | 코드 확인 (C-04) |
| R-10 | 그룹·명령의 설명 | 함수 docstring을 `clean=False`로 읽어 앞뒤만 `strip`한다. 줄바꿈과 들여쓰기는 그대로 둔다. docstring이 없으면 그룹은 `Commands for <그룹명 소문자> operations.`, 명령은 `Execute <함수명> operation.`이다. 여러 줄 docstring은 표 셀에 그대로 들어가므로 Markdown 표가 깨질 수 있다(렌더링 영향은 추론) | 코드 확인 (줄바꿈 보존) / 추론 (표 깨짐) |
| R-11 | 명령 함수(`.command` 데코레이터)들 | 소유자 이름(소문자)이 R-09에서 등록된 그룹 함수 이름과 같을 때만 그 그룹의 `commands`에 붙는다. 같은 이름의 그룹 함수가 둘이면 나중 것이 이긴다. 소유자가 그룹 함수가 아니면(`@click.command()`의 `click`, 대입으로 만든 그룹 등) 그룹이 하나라도 있는 한 그 명령은 목록에서 조용히 사라진다 | 코드 확인 (C-04) |
| R-12 | 그룹이 하나도 없다 | 명령이 하나라도 있으면 `General` 그룹(설명 `General commands for the CLI.`) 하나에 모든 명령(소유자 무관)을 넣는다. 명령도 없으면 `command_groups`는 빈 목록이고 SKILL.md에 Command Groups 절이 없다 | 코드 확인 (C-04) |
| R-13 | 예시 생성 | `software_name`을 문자열에 끼워 넣는 것 외에 소프트웨어 종류별 분기는 없다. 항상 `Create a New Project`(`project new -o myproject.json`과 `--json` 변형), `Interactive REPL Session` 두 개를 만들고, 그룹 이름(소문자)에 `export`가 들어간 그룹이 있으면 첫 번째 일치에서 `Export Project`(`--project myproject.json export render output.pdf --overwrite`)를 추가한다. 명령 이름은 `cli-anything-<software_name>`으로 쓰므로 패키지 이름에 밑줄이 있으면 밑줄이 그대로 들어간다(`cli-anything-iterm2_ctl`). 이 하니스의 실제 console script는 `cli-anything-iterm2`다 | 코드 확인 (C-05, `iterm2/agent-harness/setup.py`) |
| R-14 | `generate_skill_md` 렌더러 선택 | `import jinja2`가 실패하면 simple 폴백을 쓴다. `template_path`가 없으면 `cli-anything-plugin/templates/SKILL.md.template`, 있으면 그 경로를 쓰고, 그 파일이 없으면 simple 폴백이다(경고 없음). 파일이 있는데 template 문법 오류가 있으면 Jinja2 예외가 올라간다. Environment는 기본 설정이라 autoescape가 꺼져 있다. simple은 `name`·`description`을 큰따옴표 안에 이스케이프 없이 넣으므로 소개에 `"`가 있으면 YAML이 깨질 수 있다(추론). 출력 절 구성 차이는 1.3 표다 | 코드 확인 (C-06, C-07, C-12) / 추론 (YAML) |
| R-15 | 생성기의 skill 이름 | `skill_name`은 1.3의 `_canonical_skill_name` 규칙이다. 이 값이 frontmatter `name`과 기본 출력 디렉터리 이름이 된다 | 코드 확인 (C-08) |
| R-16 | `generate_skill_file` 쓰기 | 기본 출력은 `<harness_path의 부모의 부모>/skills/<skill_name>/SKILL.md`다(경로 위치로 레포 루트를 추정하므로 `<repo>/<sw>/agent-harness` 형태가 아니면 엉뚱한 곳에 쓴다). `-o`를 주면 그 경로를 쓴다. 출력 디렉터리는 만들고 기존 파일은 덮어쓴다. 하니스 안 복사본 `cli_anything/<software_name>/skills/SKILL.md`는 출력 경로와 다르면 항상 같은 내용으로 따로 쓴다(`-o` 사용 시에도). 둘 중 하나가 실패해도 롤백은 없다 | 코드 확인 (C-12) |
| R-17 | sync 소스 찾기 | 글롭 `*/agent-harness/cli_anything/*/skills/SKILL.md`를 정렬해 먼저, `*/agent-harness/cli_anything/*/SKILL.md`를 정렬해 뒤에 모은다. 파일인 것만 쓴다. 같은 패키지가 두 위치에 파일을 가지면 같은 id로 두 번 처리된다(기준 SHA에는 그런 하니스가 없다). 패키지가 `cli_anything/` 밖에 SKILL.md를 두거나 `agent-harness`가 없는 구조는 찾지 못한다 | 코드 확인 (C-09) |
| R-18 | skill id 결정 | sync는 `cli_anything` 다음 경로 조각(패키지 이름)에서 id를 만든다(1.3 표). 생성기·`ReplSkin`과 규칙이 같지 않아 `3MF`, `QGIS`, `cc-switch`, `iterm2` 네 하니스에서 결과가 갈린다. 생성기를 그대로 쓰면 `skills/cli-anything-3MF/` 같은 디렉터리가 생기지만 sync는 `cli-anything-threemf`를 만든다. `ReplSkin`의 `iterm2_ctl` 별칭은 `iterm2_ctl`만 `cli-anything-iterm2`로 보낸다 | 코드 확인 (C-08, C-09, `repl_skin.py:131-156`) |
| R-19 | `_rewrite_name_frontmatter` | 내용이 `---\n`으로 시작하지 않거나 `---\n` 구분자가 둘 미만이면 내용을 바꾸지 않고 돌려준다(name이 추가되지 않음). frontmatter 안에서 `name:`으로 시작하는 첫 줄과 그 뒤 들여쓴(공백·탭) 이어지는 줄을 지우고 `name: "<id>"` 한 줄로 바꾼다(접힌 스칼라 형태도 정리됨). `name:`이 없으면 frontmatter 맨 위에 넣는다. 다른 키와 본문은 그대로다 | 코드 확인 (C-09) |
| R-20 | sync 쓰기 | 각 소스에 대해 `skills/<id>/SKILL.md`의 기대 내용(R-19 적용)을 만든다. 대상 파일이 있고 내용이 같으면 쓰지 않는다. 대상이 있고 다르면 `overwrite: <대상> <- <소스>`를 출력하고 덮어쓴다(대상에만 있는 수정은 사라진다). 없으면 디렉터리를 만들고 `create:`를 출력한다. `skills/` 아래 소스가 없는 디렉터리·파일은 건드리지도 지우지도 않는다. 항상 exit 0이다(소스가 0개여도) | 코드 확인 (C-10) |
| R-21 | validate 실패 조건 | 각 소스에 대해 대상이 없으면 `stale`, 있고 기대 내용과 다르면 `difflib.unified_diff(expected, actual)`에서 `+`로 나온 줄(대상에만 있는 줄, 빈 줄 제외)이 하나라도 있으면 `clobber`, 없으면 `stale`로 분류한다. clobber나 stale이 하나라도 있으면 stderr에 이유와 고칠 방법을 출력하고 exit 1이다. 소스 줄이 바뀌거나 지워진 경우에도 옛 줄이 대상에 남아 `+`로 잡히므로 clobber로 분류된다(메시지는 "대상을 직접 고쳤다"로 나오지만 실제 원인은 소스 변경이다). 소스 줄이 추가만 된 경우는 stale이다. 검사 대상은 소스가 있는 id뿐이다. 소스 없는 `skills/` 디렉터리(고아), 두 id 충돌, frontmatter 유효성은 보지 않는다 | 코드 확인 (C-11) / difflib 분류는 표준 라이브러리로 재현 |
| R-22 | CI | `*/agent-harness/**`, `skills/**`, 스크립트 두 개, workflow 파일이 PR 또는 `main` push로 바뀌면(또는 수동 `workflow_dispatch`) Python 3.10에서 `validate_root_skills.py`만 실행한다. sync는 실행하지 않는다. 실패하면 사람이 sync를 직접 돌려 커밋해야 한다 | 코드 확인 (`check-root-skills.yml:1-35`) |
| R-23 | 자동·수동 구분 | 레포 안에 생성기 또는 sync를 부르는 hook, workflow, 스크립트가 없다. 생성기는 HARNESS.md와 `commands/cli-anything.md`의 Phase 6.5 문서 지시를 따르는 에이전트가 실행한다. sync는 validate의 오류 메시지와 `web-yu-pri` TEST.md가 언급할 뿐 어떤 절차 문서에도 단계로 들어 있지 않다. 코드로 자동인 것은 각 스크립트 안의 변환뿐이다 | 코드 확인 (검색 범위는 2.1) |
| R-24 | 루트 `skills/`와 하니스 소스가 맞지 않는 항목 | 기준 SHA에서 `skills/`는 디렉터리 70개(`cli-anything-*` 69개 + `cli-hub-meta-skill`)와 `README.md`다. 하니스는 69개이고 이 중 68개가 `cli_anything/<pkg>/` 패키지를 가져 sync 소스 68개가 되며, 모두 대응 디렉터리가 있다. `sketch`는 `cli_anything/`이 없는 JS 하니스라 소스가 없다. 소스 없이 `skills/`에만 있는 것은 두 개다. `cli-hub-meta-skill`은 sync 규칙 밖의 손으로 관리하는 파일이다(`generate_meta_skill.py`는 `cli-hub-skill/SKILL.md`에 쓰고, 루트 `cli-hub-meta-skill/SKILL.md`와 내용이 다르다). `cli-anything-iterm2`는 같은 하니스의 `cli-anything-iterm2-ctl`과 name 줄만 다르고 본문이 같은 복사본이며, 생성기·`ReplSkin`의 id와 일치한다. sync는 이것을 만들지 않고, validate도 고아를 보지 않아 잡지 못한다. 이름 규칙 때문에 하니스 디렉터리 이름과 `skills/` 이름이 다른 것은 `3MF`→`threemf`, `QGIS`→`qgis`, `cc-switch`→`ccswitch`, `iterm2`→`iterm2-ctl`이다 | 코드 확인 (고아 원인은 `cli-anything-iterm2`가 왜 존재하는지에 한해 추론) |
| R-25 | 생성물과 현재 `skills/` | `skills/` 70개 중 frontmatter에 생성기 형태의 `Command-line interface for`가 있는 것이 31개, template의 `State Management`·`Output Formats`·`More Information` 세 절이 모두 남은 것이 15개다. 나머지는 손으로 쓰거나 생성 뒤 고친 것으로 보인다. 소스 `name`이 접힌 스칼라(`name: >-`, template 출력 그대로)인 것이 29개, sync id와 값이 다른 것이 6개(`cli-anything-3mf`, `cli-anything-iterm2`, `musescore`, `cli-anything-obs_studio`, `quietshrink`, `cli-anything-sts2`)이므로 이 6개는 sync가 있어야 루트의 `name`이 id와 맞는다. 대표인 `skills/cli-anything-gimp/SKILL.md`는 현재 생성기 출력과 다르다. 그룹이 `Filter Group`, `Export Group`으로 나오고(현재 규칙이면 `Filter`, `Export`), 루트 `Cli` 그룹이 없다 | 추론 (문자열 점검과 생성기를 실행하지 않은 비교) |
| R-26 | 설치 표면 | `skills/README.md`는 `skills/`를 `npx skills` 설치 표면으로, `skills/<skill-id>/SKILL.md`를 레포 루트 정본 복사본으로 설명한다. 같은 README가 "하니스 안 `skills/` 복사본은 로컬 런타임 발견용 호환 복사본"이라고도 쓴다. 그런데 sync·validate는 하니스 안 파일을 소스로, 루트 파일을 생성물로 다룬다(validate 메시지: "skills/ is produced from the harness SKILL.md sources"). 문서의 "canonical" 방향과 스크립트의 방향이 반대다 | 코드 확인 (두 문서·스크립트의 문구 대조) / `npx skills` 동작은 미확인 |

- 불변식: sync를 실행한 직후에는 모든 소스에 대해 `skills/<id>/SKILL.md`가 R-19가 만든 기대 내용과 같다(R-20, 다른 프로세스가 동시에 쓰지 않는다는 전제). 이때 validate는 통과한다.
- 불변식이 성립하지 않는 것: 같은 id로 두 소스가 매핑되면 나중 소스가 이긴다. 같은 파일에 같은 입력으로 생성기를 두 번 돌리면 같은 결과다(생성기는 시각·난수를 쓰지 않는다. 단 R-01의 `iterdir()` 순서와 Jinja2 설치 여부는 환경에 따라 다르다).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-18, R-26 | `npx skills add <repo> --skill <id>`가 `<id>`를 디렉터리 이름으로 매칭하는가, frontmatter `name`으로 매칭하는가. 레포 안에서 `skills/`가 탐색 위치인가 | sync가 두 값을 항상 같게 만들어 이 레포에서는 구분되지 않는다. 비슷한 절차를 새로 만들 때 둘 중 무엇을 어길 때 설치가 깨지는지 모른다 | vercel-labs/skills 레포의 `docs/commands.md`, `docs/creating-skills.md`를 읽는다(루트 README만 열어 봤고 매칭 규칙은 나오지 않았다) |

- 확인 한계:
  - 생성기를 실행하지 않았다(사용자가 실행을 허용하지 않았다). R-02~R-14의 결과는 코드를 읽고 도출했고, 실제 하니스 69개의 출력과 비교하지 않았다. R-25의 "현재 생성기 출력과 다르다"는 이 이유로 추론이다.
  - `validate_root_skills.py`도 실행하지 못했다(실행 시도가 권한 분류기에 거부되어 우회하지 않았다). 기준 SHA의 `skills/`가 validate를 통과하는지는 확인하지 못했다. R-21의 분류 규칙은 표준 라이브러리 `difflib`로 작은 문자열 사례를 돌려 확인했다.
  - 하니스 안에 복제된 `mubu/agent-harness/skill_generator.py`, `zotero/agent-harness/skill_generator.py`는 열지 않았다. 같은 이름의 생성기가 둘 더 있다는 사실만 확인했다.
  - Click이 `name`을 생략한 명령에 붙이는 실제 이름은 Click 버전에 따라 다를 수 있다(함수 이름의 접미사 처리 등, 미확인). 생성기는 `함수명.replace("_", "-")`만 쓰므로 표의 명령 이름이 실제 CLI와 다를 수 있다.
  - 생성기 테스트(`cli-anything-plugin/tests/test_skill_generator.py`)는 함수·사례 이름만 훑고 열지 않았다.

### 1.5 필수 코드 참조 [필수]

라이선스는 Apache 2.0이고 인용·복사 조건은 overview 1절을 따른다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `cli-anything-plugin/skill_generator.py:192-213` `extract_intro_from_readme` | 소개 문단 추출 상태 기계(제목 뒤 첫 문단, `##`에서 중단, 폴백 문자열) | R-02, R-03 |
| C-02 | `cli-anything-plugin/skill_generator.py:216-245` `extract_system_package`, `extract_version_from_setup` | 설치 명령 정규식 세 개와 시도 순서, version 정규식과 기본값 | R-05, R-06 |
| C-03 | `cli-anything-plugin/skill_generator.py:34-113` `_click_decorator_info`, `_function_docstring`, `CommandInfo`, `CommandGroup`, `Example`, `SkillMetadata` | 데코레이터 AST 형태 인식, 선언 이름 해석, docstring 읽기, 데이터 클래스 필드 | R-08, R-10 |
| C-04 | `cli-anything-plugin/skill_generator.py:248-338` `extract_commands_from_cli` | 그룹 경로 계산, 명령 붙이기, General 폴백 | R-07~R-12 |
| C-05 | `cli-anything-plugin/skill_generator.py:341-374` `generate_examples` | 예시 3종과 export 조건 | R-13 |
| C-06 | `cli-anything-plugin/templates/SKILL.md.template:1-123` | Jinja2 template 전체(절 구성과 고정 문구) | R-14 |
| C-07 | `cli-anything-plugin/skill_generator.py:427-529` `generate_skill_md_simple` | 폴백 출력 전체 | R-14 |
| C-08 | `cli-anything-plugin/skill_generator.py:21-31` `_format_display_name`, `_canonical_skill_name` | 표시 이름과 생성기 skill id 규칙 | R-04, R-15, R-18 |
| C-09 | `.github/scripts/sync_root_skills.py:9-62` `REPO_ROOT`, `_canonical_skill_id`, `_rewrite_name_frontmatter`, `_discover_sources` | sync id 규칙, name 재작성, 소스 글롭 | R-17~R-19 |
| C-10 | `.github/scripts/sync_root_skills.py:65-89` `main` | 건너뜀·덮어쓰기·생성 분기와 출력 | R-20 |
| C-11 | `.github/scripts/validate_root_skills.py:14-110` `_mirror_only_lines`, `_load_sync_helpers`, `main` | stale/clobber 분류, 오류 메시지, exit code. sync 함수는 `exec`로 읽어 쓴다 | R-21 |
| C-12 | `cli-anything-plugin/skill_generator.py:377-424`, `532-603` `generate_skill_md`, `generate_skill_file`, CLI `main` | 렌더러 선택, 두 파일 쓰기, 인자 | R-14, R-16 |
| C-13 | `.github/workflows/check-root-skills.yml:1-35` | CI 트리거 경로와 실행 명령 | R-22 |
| C-14 | `cli-anything-plugin/skill_generator.py:116-189` `extract_cli_metadata` | 패키지 탐색, README·setup·CLI 파일 조립, description 조립 | R-01, R-03, R-04, R-07 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출(코드를 읽고 손으로 따라가 기대값을 정했다. 생성기·sync는 실행하지 않았고, T-10의 분류만 `difflib` 소규모 사례로 재현했다). 원본 테스트는 열지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | README가 `# T`, 빈 줄, `First line`, `continued`, 빈 줄, `## Sec` | 소개는 `First line continued` |
| T-02 | R-03, R-04 | (a) README가 `# T`, 빈 줄, `## Sec`. (b) README 없음 | (a) 소개 `CLI interface for the software.`, description은 `Command-line interface for Gimp - CLI interface for the software.`(software `gimp`). (b) 소개 빈 문자열, description은 `Command-line interface for Gimp` |
| T-03 | R-04 | 소개가 120자 | description 끝이 `- <앞 100자>...` |
| T-04 | R-05 | README에 (a) `` `sudo apt install gimp` `` (b) `` `brew install blender` `` (c) `` `apt-get install x` ``와 `` `brew install y` `` 둘 다 | (a) None (b) `brew install blender` (c) `brew install y`(시도 순서가 apt, brew, apt-get) |
| T-05 | R-08~R-11 | `@click.group(invoke_without_command=True) def cli`(docstring `Root.`), `@cli.group("filter") def filter_group`(docstring `Filters.`), `@filter_group.command("list-available") def lst`(docstring `List.`), `@cli.command() def undo_all`(docstring 없음) | 그룹 `Cli`(설명 `Root.`, 명령 `undo-all` / `Execute undo_all operation.`), 그룹 `Filter`(설명 `Filters.`, 명령 `list-available` / `List.`). 순서는 `Cli`, `Filter` |
| T-06 | R-09 | T-05에 `@filter_group.group("preset") def preset_group`을 추가 | 그룹 `Filter Preset`(소유자 경로 `[Filter]` + `Preset`) |
| T-07 | R-11, R-12 | (a) 그룹 없이 `@click.command() def solo` 하나. (b) 그룹이 있는 파일에 `@click.command() def solo`를 추가 | (a) `General` 그룹에 `solo`. (b) `solo`는 어느 그룹에도 들어가지 않고 사라짐 |
| T-08 | R-07 | CLI 파일 (a) 없음 (b) 문법 오류 | (a) 그룹 없음, SKILL.md에 Command Groups 절 없이 생성. (b) `SyntaxError`로 생성 중단, 파일은 쓰이지 않음 |
| T-09 | R-15, R-18 | 하니스 `3MF/agent-harness`, 패키지 `threemf` | 생성기 기본 출력 `skills/cli-anything-3MF/SKILL.md`, sync 대상 `skills/cli-anything-threemf/SKILL.md` |
| T-10 | R-21 | 소스 대비 대상이 (a) 없음 (b) 소스에 줄이 추가돼 대상이 뒤처짐 (c) 소스의 줄이 수정돼 대상이 뒤처짐 (d) 대상에 줄이 추가됨 (e) 소스 없는 `skills/foo/`가 있음 | (a) stale, exit 1 (b) stale, exit 1 (c) clobber로 분류, exit 1 (d) clobber, exit 1 (e) 통과, exit 0(다른 항목이 모두 일치할 때) |
| T-11 | R-19 | 소스 frontmatter가 `name: >-`, `  cli-anything-gimp`, `description: >-`, `  x` | 대상 frontmatter가 `name: "cli-anything-gimp"`, `description: >-`, `  x`. frontmatter가 없는 소스는 대상이 소스와 같고 name은 추가되지 않음 |
| T-12 | R-20 | sync를 연속으로 두 번 실행 | 두 번째는 `Synced 0 root skill(s); N already up to date.`, exit 0. 대상을 손으로 고친 뒤 실행하면 `overwrite:` 줄이 나오고 수정이 사라짐 |
| T-13 | R-16 | `generate_skill_file(h, "/tmp/x/SKILL.md")` | `/tmp/x/SKILL.md`와 `cli_anything/<pkg>/skills/SKILL.md`가 같은 내용으로 쓰이고, 루트 `skills/`에는 쓰이지 않음 |
| T-14 | R-14 | Jinja2 미설치 환경에서 `generate_skill_md` | simple 출력(`State Management`, `Output Formats`, `More Information` 절 없음, `name`이 큰따옴표) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-14. `cli-anything-plugin/skill_generator.py:129-142` | 코드를 직접 읽었다. 정렬이 없다는 것은 `iterdir()` 사용(135-136)으로 확인했다. 순서가 환경마다 다를 수 있다는 점은 정렬 코드가 없다는 사실에서 도출한 것이다. 기준 SHA에서 `cli_anything/` 아래 패키지가 둘 이상인 하니스는 찾지 못했다(`git ls-files`에 정규식 `^([^/]+)/agent-harness/cli_anything/([^/]+)/`를 적용한 결과 하니스마다 패키지 하나, 68개 모두 `__init__.py` 있음) |
| R-02, R-03 | C-01, C-14 (`:144-152`) | 코드 읽음. 배지 줄이 소개에 들어간다는 것은 코드상 `# ` 이후 비어 있지 않은 모든 줄을 모은다는 사실에서 도출 |
| R-04 | C-14 (`:171-178`), C-08 (`:21-23`) | 코드 읽음 |
| R-05, R-06 | C-02 | 코드 읽음. `sudo` 사례는 정규식이 백틱 바로 뒤에 `apt`를 요구한다는 점에서 도출 |
| R-07 | C-04 (`:250-251`), C-14 (`:161-166`) | 코드 읽음. 하니스 68개 패키지 모두 `<pkg>_cli.py`가 있다(`git ls-files` 정규식 점검, 누락 0개). 따라서 파일 없음 경로는 현재 하니스에서는 발생하지 않는다 |
| R-08 | C-03 `:34-69`, C-04 `:252-259` | 코드 읽음. "인식하지 못하는 형태"는 `isinstance` 조건을 거꾸로 읽어 도출. 실제 하니스 중 인식에 실패하는 것이 몇 개인지는 세지 않았다 |
| R-09 | C-04 `:264-299` | 코드 읽음. `gimp_cli.py:117-124`(루트 `cli`), `:450-451`(`@cli.group("filter") def filter_group`)가 T-05의 근거 형태다. 현재 `skills/cli-anything-gimp/SKILL.md`의 `### Filter Group`(`:102`)과 어긋나는 점이 R-25의 근거다 |
| R-10 | C-03 `:72-77`, C-04 `:294`, `:316` | 코드 읽음. 표가 깨지는지는 렌더러 동작이라 추론 |
| R-11 | C-04 `:301-317` | 코드 읽음 |
| R-12 | C-04 `:319-336` | 코드 읽음 |
| R-13 | C-05 | "소프트웨어 종류별 분기가 없다"는 전칭 부정 주장이다. 확인 방법: `generate_examples` 함수 전체(341-374)를 읽었고, `software_name`은 f-string에만 쓰인다. `skill_generator.py` 전체를 읽었으며 다른 호출처에서 예시를 바꾸는 코드는 없었다(`generate_examples` 호출은 169줄 하나). docstring의 "based on software type"(342줄)과 구현이 다르다. 놓칠 수 있는 것: 하니스 쪽 복제 생성기(mubu, zotero)는 열지 않았다. 콘솔 스크립트 이름 불일치는 `iterm2/agent-harness/setup.py:21-23` |
| R-14 | C-06, C-07, C-12 `:388-404` | 코드 읽음. "생성기용 jinja2 의존 선언이 없다"는 부재 주장이다. 확인 방법: `git grep -n -i jinja -- . ':!docs' ':!*.html'`에서 `skill_generator.py`·template·`guides/skill-generation.md:57` 외에는 `QGIS/agent-harness/setup.py:39`뿐이었고, `cli-anything-plugin/`에는 `setup.py`·`requirements*`·`pyproject.toml`이 없다(`git ls-files cli-anything-plugin`). 놓칠 수 있는 것: 설치 스크립트가 pip로 설치하는 경우(`scripts/setup-cli-anything.sh`의 `SKILL.md`·jinja 문자열은 검색에서 나오지 않았다) |
| R-15 | C-08 | 코드 읽음 |
| R-16 | C-12 `:546-570` | 코드 읽음. 문서(`guides/skill-generation.md:60-76`, `HARNESS.md:262-265`, `commands/cli-anything.md:76`)가 같은 두 곳 쓰기를 설명한다. 문서와 구현이 같다 |
| R-17 | C-09 `:58-62` | 코드 읽음. "그런 하니스가 없다"는 부재 주장이다. 확인 방법: `git ls-files` 결과에 정규식 `^[^/]+/agent-harness/cli_anything/[^/]+/(skills/)?SKILL\.md$`를 적용해 68개를 얻고, id를 계산해 중복이 없음을 확인했다. 직접 위치(`.../<pkg>/SKILL.md`)는 `unimol_tools` 하나다 |
| R-18 | C-08, C-09 `:13-23`, `cli-anything-plugin/repl_skin.py:131-156` | 코드 읽음. 4개 사례는 `git ls-files` 결과로 디렉터리 이름과 패키지 이름을 비교해 얻었다(`3MF`/`threemf`, `QGIS`/`qgis`, `cc-switch`/`ccswitch`, `iterm2`/`iterm2_ctl`). 다른 불일치는 없었다. `_canonical_skill_id`의 `else` 가지(`software_dir = parts[0]`, 22-23줄)는 `_discover_sources` 글롭이 항상 `cli_anything`을 경로에 넣으므로 현재 호출 경로에서는 도달하지 않는다(추론: 다른 호출자는 `validate_root_skills.py`뿐이고 같은 소스 목록을 쓴다) |
| R-19 | C-09 `:26-55` | 코드 읽음. 사례는 손으로 따라감 |
| R-20 | C-10 | 코드 읽음. "지우는 동작이 없다"는 부재 주장이다. 확인 방법: `sync_root_skills.py` 전체 93줄을 읽었고 `unlink`·`rmtree`·`remove` 호출이 없다. 동적 호출은 없다 |
| R-21 | C-11. 분류 근거 `validate_root_skills.py:65-71`, `_mirror_only_lines:14-27` | 코드 읽음. 소스 줄 수정이 clobber로 분류되는 것은 `difflib.unified_diff(expected, actual)`에서 `+`가 `actual` 쪽 줄이라는 점에서 도출했고, `python -I`로 작은 문자열 4쌍(소스 추가, 소스 수정, 소스 삭제, 대상 추가)을 돌려 각각 `[]`, `['b']`, `['b']`, `['x']`가 나오는 것을 확인했다. 고아·충돌·frontmatter 검사가 없다는 것은 `main`(37-110)을 전부 읽고 `discover_sources()` 반복 외에 `skills/`를 훑는 코드가 없는 것으로 확인했다 |
| R-22 | C-13 | 코드 읽음 |
| R-23 | `cli-anything-plugin/HARNESS.md:232-290`, `cli-anything-plugin/commands/cli-anything.md:72-77`, `README.md:944` | "자동으로 부르는 곳이 없다"는 부재 주장이다. 확인 방법: `git grep -l "skill_generator\|generate_skill_file\|sync_root_skills\|validate_root_skills"`로 나온 파일을 분류했다. 문서·설치 스크립트(복사만)·테스트·CI(validate만)였고 `git ls-files | grep -i "hooks\|\.claude-plugin\|pre-commit\|Makefile"`에서 hook 정의는 `.claude-plugin/marketplace.json`, `cli-anything-plugin/.claude-plugin/plugin.json`뿐이며 `plugin.json`에서 `hook` 문자열은 나오지 않았다. 놓칠 수 있는 것: `README.md:944`의 "auto-generated during Phase 6.5"는 에이전트가 문서 지시를 따라 실행한다는 뜻으로 읽었다(`HARNESS.md`가 실행 주체를 에이전트로 쓴다). 에이전트 런타임(Codex, Cursor 등)의 자체 자동화는 보지 않았다 |
| R-24 | `skills/` 목록, `.github/scripts/generate_meta_skill.py:12`, `:200-201` | `ls -d skills/*/`로 디렉터리 70개, `git ls-files skills`로 파일 71개(`README.md` 포함)를 셌다. 소스 68개의 id 집합과 `skills/` 디렉터리 이름을 비교해 소스 쪽 id가 모두 `skills/`에 있고, `skills/`에만 있는 것이 `cli-anything-iterm2`와 `cli-hub-meta-skill`임을 확인했다. `cli-anything-iterm2`와 `cli-anything-iterm2-ctl`의 `SKILL.md`는 `diff`에서 2번째 줄(`name`)만 다르다. `cli-hub-meta-skill/SKILL.md`와 `skills/cli-hub-meta-skill/SKILL.md`는 `diff`에서 후자에 `Preview Consumption` 절(87-112줄)이 더 있다. `cli-anything-iterm2`가 왜 존재하는지(`ReplSkin` 별칭 때문에 남겼는지, 과거 생성기 출력인지)는 저장소가 `--depth 50` shallow clone이라 이력으로 확인하지 못했다. 추론. overview의 "skills/ 71개"는 `README.md`를 센 값이고 디렉터리는 70개다 |
| R-25 | `skills/cli-anything-gimp/SKILL.md:1-5,57,102,128`, `gimp/agent-harness/cli_anything/gimp/gimp_cli.py:117-124,450-451` | 문자열 점검(파이썬 임시 스크립트로 frontmatter의 `Command-line interface for`, template 절 제목, `name` 줄을 셌다. 스크립트는 레포에 두지 않음). "손으로 쓰거나 고쳤다"는 구조 짐작이라 추론이다. gimp 불일치는 현재 생성기가 `filter_group`이 아니라 선언 이름 `filter`를 쓰는 것(C-03, `:67`)과 루트 그룹이 목록에 들어가는 것(C-04)에서 도출했다. 생성기를 실행하지 않았으므로 추론 |
| R-26 | `skills/README.md:1-31`, `validate_root_skills.py:81-84`, `sync_root_skills.py:80-82` | 문서 문구와 스크립트 메시지를 대조했다. `npx skills`의 실제 동작은 레포 밖이다. 공식 README(github.com/vercel-labs/skills)에서 `--skill <name>` 예시만 확인했고 매칭 규칙은 나오지 않았다. 제3자 자료는 보지 않았다 |
| T-01~T-09, T-11, T-13, T-14 | 해당 R-ID의 C-ID | 코드를 손으로 따라가 기대값을 만들었다. 실행하지 않았다 |
| T-10 | C-11 | (c), (d)는 `difflib` 소규모 재현. (a), (b), (e)는 `main` 읽기 |
| T-12 | C-10 | 코드 읽음. 실행하지 않았다 |

### 2.2 코드 읽는 순서 [선택]

1. `cli-anything-plugin/skill_generator.py` 116-189 `extract_cli_metadata`로 입력 수집 순서를 본다.
2. 248-338 `extract_commands_from_cli`와 34-69 `_click_decorator_info`가 가장 복잡하다. `gimp_cli.py`의 데코레이터와 대조하며 읽는다.
3. `templates/SKILL.md.template`와 427-529 simple 폴백을 나란히 놓고 절 차이를 본다.
4. 532-570 `generate_skill_file`에서 두 곳에 쓰는 것을 본다.
5. `.github/scripts/sync_root_skills.py`(93줄), `validate_root_skills.py`(114줄), workflow(35줄) 순으로 읽는다. validate가 sync 소스를 `exec`로 불러 쓰는 구조(30-34줄)를 먼저 알아 둔다.

### 2.4 검토 기록 [필수, ready 스펙]

`status: draft`라 미수행이다. 메인 세션의 원본 대조 점검이 아직 없다.

## 적용 메모 [선택]

Claude Code에서 "앱 → CLI + skill" 절차를 설계할 때의 제안이다. 원본의 미결정을 해소한 것으로 치지 않는다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-15, R-18 | skill id를 한 함수로만 정하고 생성기·sync·런타임 배너가 같은 함수를 부른다 | 원본은 세 곳이 규칙이 달라 4개 하니스에서 결과가 갈리고, 고아 디렉터리(`cli-anything-iterm2`)가 생겼다 | T-09의 두 결과가 같아야 한다 |
| R-13 | 예시의 명령 이름은 `setup.py`의 `console_scripts` 이름에서 읽는다 | 원본은 패키지 이름을 그대로 써서 `iterm2_ctl`처럼 console script와 다른 명령이 예시에 들어간다 | R-13 사례에 `cli-anything-iterm2`가 기대값이 된다 |
| R-11 | 인식하지 못한 데코레이터·소유자를 경고로 남긴다 | 원본은 명령을 조용히 버려 SKILL.md가 CLI 표면을 일부 빠뜨려도 알 수 없다 | T-07(b)에 경고 출력이 추가된다 |
| R-21 | 고아 `skills/` 디렉터리와 `name`≠디렉터리 이름도 검사한다 | 원본 validate는 소스 쪽에서만 순회한다 | T-10(e)가 실패로 바뀐다 |
