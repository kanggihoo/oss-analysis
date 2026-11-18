---
sha: "34f519533bc175d2fe287ab8316b0dd99bb9cc43"
created: 2026-11-18
updated: 2026-11-18
sources:
  - gimp/agent-harness/cli_anything/gimp/gimp_cli.py
  - gimp/agent-harness/cli_anything/gimp/core/session.py
  - gimp/agent-harness/cli_anything/gimp/core/project.py
  - gimp/agent-harness/cli_anything/gimp/core/export.py
  - gimp/agent-harness/cli_anything/gimp/utils/gimp_backend.py
  - gimp/agent-harness/cli_anything/gimp/__main__.py
  - gimp/agent-harness/setup.py
  - cli-anything-plugin/repl_skin.py
  - cli-anything-plugin/HARNESS.md
  - cli-anything-plugin/guides/pypi-publishing.md
  - cli-anything-plugin/guides/session-locking.md
  - cli-anything-plugin/guides/auto-save-dry-run.md
  - cli-anything-plugin/commands/validate.md
  - cli-anything-plugin/skill_generator.py
  - .github/scripts/sync_root_skills.py
  - registry.json
  - blender/agent-harness/cli_anything/blender/blender_cli.py
  - blender/agent-harness/cli_anything/blender/core/session.py
  - blender/agent-harness/cli_anything/blender/core/scene.py
  - blender/agent-harness/cli_anything/blender/utils/blender_backend.py
  - blender/agent-harness/setup.py
  - firefly-iii/agent-harness/cli_anything/firefly_iii/firefly_iii_cli.py
  - firefly-iii/agent-harness/cli_anything/firefly_iii/utils/firefly_iii_backend.py
  - jumpserver/agent-harness/cli_anything/jumpserver/jumpserver_cli.py
  - jumpserver/agent-harness/cli_anything/jumpserver/utils/__init__.py
  - jumpserver/agent-harness/cli_anything/jumpserver/core/session.py
  - jumpserver/agent-harness/setup.py
  - unimol_tools/agent-harness/pyproject.toml
  - godot/agent-harness/setup.py
  - intelwatch/agent-harness/cli_anything/intelwatch/intelwatch_cli.py
depends:
  - ../capabilities/harness-sop.md
status: draft
---

# 하니스 계약 (CLI 표면 + 패키지 레이아웃)

> 앱 하나를 감싼 CLI 하니스가 `<sw>/agent-harness/` 패키지 하나로 배포되고, `cli-anything-<sw> [--json] <group> <cmd>`로 호출되며, 하위 명령이 없으면 REPL이 뜨고, 프로젝트 상태를 JSON 파일로 저장하고, 실패를 JSON으로 알리는 공통 형식을 정의한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표는 gimp다. 같은 템플릿을 따르는 blender는 이름만 다르고, HTTP 방식인 firefly-iii와 jumpserver는 일부 규칙을 따르지 않는다(1.4의 R-19~R-21).

1. 설치 단위는 `<sw>/agent-harness/`다. 이 디렉터리에서 `pip install .`(레지스트리는 `pip install git+https://github.com/HKUDS/CLI-Anything.git#subdirectory=<sw>/agent-harness`)을 하면 `setup.py`의 `console_scripts`가 `cli-anything-<sw>` 명령을 만든다.
2. `cli-anything-<sw> --json --project p.json layer new -n A`처럼 호출하면 click group `cli`가 전역 옵션 `--json`, `--project`, `--dry-run`을 먼저 받는다. `--project`가 있으면 파일을 읽어 메모리 `Session`에 올린다.
3. 하위 명령은 변경 전에 `Session.snapshot()`으로 현재 상태를 복사해 undo stack에 쌓고, project dict를 고치고, `output(data, message)`로 결과를 출력한다. `--json`이면 `indent=2` JSON, 아니면 `key: value` 줄이다.
4. 명령이 예외를 던지면 `handle_error` decorator가 잡아 `{"error": ..., "type": ...}`를 stdout에 쓰고 종료 코드 1로 끝낸다(C2).
5. 명령이 정상으로 끝나면 group의 `result_callback`이 `_modified`가 켜져 있고 `project_path`가 있을 때 `--dry-run`이 아니면 project 파일을 저장한다. 프로세스가 끝나면 undo/redo stack은 사라진다.
6. 하위 명령 없이 `cli-anything-<sw>`만 실행하면 `ReplSkin` 배너와 prompt가 뜨고, 한 줄씩 같은 `cli`에 다시 넘긴다. REPL이 끝나면 위 5번의 자동 저장이 한 번 더 돈다.

### 1.2 범위·통합 지점 [필수]

- 제공: 하니스 하나가 지켜야 하는 외부 형식. 패키지 레이아웃, 설치 진입점(`console_scripts`, `python -m`), 전역 옵션, REPL 진입, 세션 파일, 오류 JSON, 패키지 안 `skills/SKILL.md` 위치(공유 계약 C1의 패키지 쪽 절반).
- 제외: 각 하니스의 도메인 명령 내용(`layer`, `filter` 등), SOP 문서 자체(`harness-sop`), `SKILL.md` 내용 생성과 루트 `skills/` 동기화(`skill-packaging`). 개별 하니스 `core/` 구현은 읽지 않았다.
- 외부 의존·선행 계약: 선행 스펙 `harness-sop`는 별도 문서 없이 경계만 쓴다. 입력은 대상 앱의 분석 결과(데이터 모델, 백엔드 CLI, 명령 후보)와 7단계 절차의 산출물이다. 정상 결과는 이 문서의 1.3~1.4를 만족하는 `agent-harness/` 디렉터리다. 실패 경계는 아래와 같다. 이 계약을 기계적으로 검사하는 코드는 레포에 없고(2.1 R-21), `commands/validate.md`가 에이전트에게 체크리스트를 읽게 하는 프롬프트일 뿐이다. 그래서 계약 위반은 제작 단계에서 막히지 않고 설치·실행에서야 드러난다. 외부 라이브러리는 `click`, `prompt-toolkit`(REPL), `setuptools`다.
- 소유 상태·부작용: project 파일(사용자가 `--project`로 지정한 경로, 하니스 이름 규칙은 `.<sw>-cli.json`이 안내문에만 있고 강제되지 않음), 사용자 홈의 REPL history(`~/.cli-anything-<sw>/history`, `ReplSkin` 생성 시 디렉터리 생성), 프로세스 안 `Session`(undo/redo stack, `_modified`). undo/redo는 파일에 저장되지 않는다(R-12).

### 1.3 인터페이스와 데이터 의미 [필수]

패키지 레이아웃(`gimp` 기준, R-01~R-04). 표 아래 줄은 변형이다.

```
<sw>/agent-harness/
  setup.py                         # name="cli-anything-<sw>", console_scripts, package_data
  <SOFTWARE>.md                    # 앱별 분석 문서 (gimp는 GIMP.md)
  cli_anything/                    # __init__.py 없음 (PEP 420 namespace)
    <pkg>/                         # <pkg> = <sw>를 소문자로, 하이픈은 밑줄로 바꾼 이름 (3MF -> threemf)
      __init__.py  __main__.py     # __main__은 main() 호출
      README.md
      <pkg>_cli.py                 # click group `cli`와 `main()`
      core/  (project.py, session.py, export.py, 도메인 모듈)
      utils/ (<sw>_backend.py, repl_skin.py)
      skills/SKILL.md              # package_data로 wheel에 포함
      tests/ (TEST.md, test_core.py, test_full_e2e.py)
```

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| 호출 형식 | `cli-anything-<sw> [--json] [--project PATH] [--dry-run] <group> <cmd> [args]` | 전역 옵션은 group에 선언되어 하위 명령 앞에 와야 한다. `--json`은 flag, `use_json`. `--project`는 string, 기본 None. `--dry-run`은 flag, 기본 False. 옵션 선언 블록은 C-04 |
| `python -m cli_anything.<pkg>` | 인자 없음 | `__main__.py`가 `main()`을 호출한다. gimp의 `__main__.py` docstring(`python3 -m cli.gimp_cli`)은 옛 경로라 틀리다 |
| 성공 출력 | `output(data, message)`: dict·list·scalar | `--json`이면 `json.dumps(data, indent=2, default=str)`를 stdout에. 아니면 message 한 줄 뒤에 dict는 `key: value`(중첩은 2칸 들여쓰기), list는 `[i]` 또는 `- item`. 이 `--json`은 호출마다 따로 적용된다(R-15) |
| 오류 JSON (C2) | `{"error": string, "type": string}` | 한 줄(`json.dumps` 기본 구분자, `ensure_ascii=True`), stdout. 대응은 R-10 |
| 종료 코드 | int | 잡힌 오류 1, click 사용법 오류 2, 정상 0. REPL 안에서는 프로세스가 끝나지 않는다 |
| project 파일 (C2) | JSON object | 최상위에 domain이 정한 필수 키(gimp `version`·`canvas`, blender `version`·`scene`)와 `metadata` object(`created`, `modified`, `software`)가 있어야 한다. `save_session`이 `metadata.modified`를 현재 로컬 시각 `isoformat()`(타임존 없음)으로 덮어쓴다. `indent=2`, `sort_keys=True`, `default=str`, ASCII 이스케이프. undo/redo는 들어가지 않는다 |
| `session status` | object | `has_project`, `project_path`, `modified`, `undo_count`, `redo_count`, 그리고 이름 키(gimp `project_name`, blender `scene_name`). project가 없어도 오류 없이 값이 `false/null/0`으로 나온다 |
| `session undo` / `redo` / `history` | `{"undone": desc}` / `{"redone": desc}` / `[{"index","description","timestamp"}]` | history는 가장 최근 변경이 index 0 |
| REPL | stdin 한 줄 | R-15 |
| 백엔드 래퍼 | `utils/<sw>_backend.py`의 `find_<sw>() -> str`, 실행 함수 `-> dict` | `shutil.which`로 찾고, 없으면 `RuntimeError`에 설치 안내를 담는다. 실행은 `subprocess.run(..., capture_output=True, text=True, timeout=...)`이고 결과는 `returncode`·`stdout`·`stderr` dict(C-10) |

### 1.4 행동 규칙과 남은 질문 [필수]

패키지·배포

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 하니스를 만든다 | `<sw>/agent-harness/` 아래에 `setup.py`, `cli_anything/<pkg>/{__init__,__main__,<pkg>_cli}.py`, `core/`, `utils/`, `tests/`, `README.md`, `skills/SKILL.md`를 둔다. `<pkg>_cli.py`는 69개 중 Python 68개 전부에 있다. `core/` 64, `utils/*_backend.py` 53, `tests/TEST.md` 54로 나머지는 선택처럼 쓰인다 | 코드 확인(gimp, 전수 존재 점검) |
| R-02 | 패키지를 만든다 | `cli_anything/`에는 `__init__.py`를 두지 않고 `<pkg>/`에는 둔다. `setup.py`는 `find_namespace_packages(include=["cli_anything.*"])`를 쓴다. 이 `include` 패턴은 `cli_anything` 자체를 포함하지 않으므로, 소스 트리에 빈 `cli_anything/__init__.py`가 있어도 wheel에는 들어가지 않는다 | 코드 확인(gimp·godot wheel을 직접 빌드해 파일 목록 확인) |
| R-03 | 설치한다 | `console_scripts`에 `cli-anything-<sw>=cli_anything.<pkg>.<pkg>_cli:main`이 등록된다. 설치 루트는 `agent-harness/`이고, 레지스트리의 `install_cmd`가 `#subdirectory=<sw>/agent-harness`를 쓰므로 그 디렉터리에 `setup.py`나 `pyproject.toml`이 있어야 한다. 실제 이름은 하니스마다 다르다(함수 `main` 58, `cli` 7, `entrypoint` 2, `cli_main` 1, 스크립트 이름 `ccswitch`·`sts2`, lldb는 스크립트 2개) | 코드 확인 |
| R-04 | wheel을 만든다 | `install_requires`에 `click>=8.0.0`, `prompt-toolkit>=3.0.0`, `python_requires=">=3.10"`을 둔다. `package_data={"cli_anything.<pkg>": ["skills/*.md"]}`로 `skills/SKILL.md`를 싣는다. gimp wheel에는 `skills/SKILL.md`, `tests/*.py`, `utils/repl_skin.py`가 들어가고 `README.md`와 `tests/TEST.md`는 빠진다 | 코드 확인(gimp wheel 빌드) |
| R-05 | 백엔드가 로컬 실행 파일이다 | `find_<sw>()`는 후보 이름을 `shutil.which`로 찾고 없으면 설치 안내가 담긴 `RuntimeError`를 던진다. 이 오류는 R-10으로 JSON이 된다. 실행 함수는 `timeout`을 주고 `returncode`·`stdout`·`stderr`를 dict로 돌려주며 호출자가 결과 파일 존재로 성공을 판단한다(`render_project`) | 코드 확인(gimp) |

CLI 표면과 세션

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | 어떤 하위 명령이든 | group `cli`가 `--json`, `--project`, `--dry-run`을 받는다. 하위 명령에는 `--json`이 없다. `--json`은 전역 `_json_output`을 정한다 | 코드 확인 |
| R-07 | `--project`만 주거나 인자 없이 실행 | `invoke_without_command=True`이고 `ctx.invoked_subcommand is None`이면 `ctx.invoke(repl, project_path=None)`로 REPL에 들어간다. `repl`은 하위 명령으로도 있고 자기 `--project` 옵션이 있다 | 코드 확인(실행으로 확인) |
| R-08 | `--project PATH` | group callback이 `Session`에 project가 없으면 `open_project(PATH)`로 읽어 `set_project`한다(undo/redo 비움, `_modified=False`). 파일이 없으면 `FileNotFoundError`, 필수 키가 없으면 `ValueError`다. 이 호출은 `handle_error` 밖이라 JSON 오류가 아니라 traceback과 종료 코드 1이 된다 | 코드 확인(실행으로 확인) |
| R-09 | `output()` 호출 | `--json`이면 stdout에 `indent=2` JSON이고, 아니면 C-03의 텍스트 형식이다. `project json` 명령은 flag와 무관하게 항상 JSON을 쓴다 | 코드 확인 |
| R-10 | 명령이 예외를 던진다 | `handle_error`가 `FileNotFoundError`는 type `"file_not_found"`, `ValueError`·`IndexError`·`RuntimeError`(하위 클래스 포함, 예 `JSONDecodeError`, `UnicodeEncodeError`)는 type을 클래스 이름으로, `FileExistsError`는 type `"file_exists"`로 처리한다. `--json`이면 stdout에 `{"error": str(e), "type": ...}`, 아니면 stderr에 `Error: <msg>`. 일회성 실행은 `sys.exit(1)`, REPL은 종료하지 않는다. 그 밖의 예외(`KeyError`, `PermissionError`)와 click 사용법 오류는 처리되지 않는다. 사용법 오류는 종료 코드 2의 텍스트다 | 코드 확인(실행으로 확인) |
| R-11 | project를 바꾸는 명령 | 명령은 변경 전에 `sess.snapshot(description)`을 호출해야 한다. `snapshot`이 project를 `deepcopy`해 undo stack에 쌓고(최대 `MAX_UNDO=50`, 넘으면 가장 오래된 것 삭제), redo stack을 비우고, `_modified=True`로 만든다. `snapshot`을 빼먹은 명령은 변경되어도 `_modified`가 꺼져 있어 자동 저장되지 않는다. 실제 사례가 `canvas dpi`다 | 코드 확인(실행으로 확인) |
| R-12 | `session undo` / `redo` | undo stack이 비면 `RuntimeError("Nothing to undo.")`(redo는 `"Nothing to redo."`). 성공하면 현재 상태를 반대쪽 stack에 `"redo point"`/`"undo point"`로 쌓고 project를 복원하고 `_modified=True`다. undo/redo stack은 프로세스 메모리에만 있어서 새 프로세스의 `session undo`는 항상 `Nothing to undo.`다. 즉 undo는 REPL(한 프로세스) 안에서만 쓸 수 있다 | 코드 확인(실행으로 확인) |
| R-13 | `save_session(path=None)` | project가 없으면 `RuntimeError("No project to save.")`, `path`도 `project_path`도 없으면 `ValueError("No save path specified.")`. 아니면 `metadata.modified`를 갱신하고 `_locked_save_json`으로 쓴 뒤 `project_path`를 저장 경로로 바꾸고 `_modified=False`로 둔다. `_locked_save_json`은 파일을 `"r+"`로 열어(없으면 상위 디렉터리를 만들고 `"w"`), `fcntl.flock(LOCK_EX)`를 얻은 뒤에 `truncate`하고 쓴다. `fcntl`을 못 쓰는 환경(Windows)에서는 잠금 없이 같은 순서로 쓴다. 임시 파일 교체가 아니므로 쓰는 도중 중단되면 파일이 깨질 수 있다 | 코드 확인(잠금 분기는 읽기만, 비잠금 분기는 실행 확인). 깨질 수 있다는 판단은 추론 |
| R-14 | 일회성 명령이 정상 종료 | `result_callback`이 `_repl_mode`가 아니고, `--dry-run`이 아니고, `has_project()`이고, `_modified`이고, `project_path`가 있을 때만 `save_session()`한다. 저장이 예외를 던지면 stderr에 `Warning: Auto-save failed: ...`만 쓰고 종료 코드는 그대로다. 명령이 `handle_error`로 `sys.exit(1)` 하면 callback이 돌지 않아 저장되지 않는다(`snapshot` 뒤에 실패해도 파일은 그대로) | 코드 확인(실행으로 확인) |
| R-15 | REPL | `ReplSkin("<sw>", version=...)`로 배너를 찍고 `create_prompt_session()`을 만든다. 한 줄 입력을 처리한다: 빈 줄 무시, `quit`/`exit`/`q`(대소문자 무시)는 종료, `help`는 `skin.help(dict)`. 그 밖의 줄은 `shlex.split`(실패하면 `str.split`) 후 `cli.main(args, standalone_mode=False)`로 같은 group에 넘긴다. `SystemExit`은 삼키고, `click.UsageError`는 `skin.warning`, 그 밖의 예외는 `skin.error`로 보여 주고 계속한다. EOF/Ctrl-C는 종료한다. 줄마다 group callback이 다시 돌아서 `_json_output`이 그 줄의 `--json` 여부로 다시 정해진다. 그래서 바깥 `--json`은 REPL 줄에 이어지지 않고, 줄마다 `--json`을 붙여야 JSON이 나온다. REPL 안에서는 자동 저장이 꺼지고(R-14의 `_repl_mode`) `project save`로만 저장된다. REPL 루프가 끝난 뒤 `_repl_mode`가 False로 돌아오고 group의 `result_callback`이 한 번 더 돌아, `_modified`이고 `project_path`가 있고 `--dry-run`이 아니면 저장된다. `HARNESS.md`·`auto-save-dry-run.md`는 "REPL은 자동 저장하지 않는다"고 쓰지만 실제는 종료 시점에 저장한다 | 코드 확인(실행으로 확인, 단 prompt_toolkit 대신 stdin `input()` 경로) |
| R-16 | `ReplSkin(software, version)` | `utils/repl_skin.py`는 `cli-anything-plugin/repl_skin.py`의 복사본이다(`repl_skin.py`가 있는 62개 중 49개가 바이트 동일). 생성자가 `skill_id = cli-anything-<slug>`(slug는 소문자, `_`→`-`, 별칭 `iterm2_ctl`→`iterm2`), 설치 안내(`npx skills add HKUDS/CLI-Anything --skill <id> -g -y`), 전역 skill 경로(`~/.agents/skills/<id>/SKILL.md`, 환경변수 `CLI_ANYTHING_GLOBAL_SKILLS_DIR`), history 파일(`~/.cli-anything-<software>/history`, 디렉터리 생성)을 정하고 배너에 보여 준다. 색은 `NO_COLOR`·`CLI_ANYTHING_NO_COLOR`가 있거나 stdout이 tty가 아니면 끈다. `error()`만 stderr, 나머지 메시지는 stdout이다. `create_prompt_session()`은 `prompt_toolkit`이 `ImportError`면 None을 돌려주고 `get_input`이 `input()`으로 대신한다 | 코드 확인(gimp, plugin 원본) |
| R-17 | SKILL.md 위치 (C1 패키지 쪽) | 패키지 안 원본은 `cli_anything/<pkg>/skills/SKILL.md`다. `ReplSkin`은 `repl_skin.py`에서 부모 디렉터리를 거슬러 올라가며 `skills/<skill_id>/SKILL.md`(레포 루트 정본)를 먼저 찾고, 없으면 `<pkg>/skills/SKILL.md`를 `skill_path`로 쓴다. 루트 동기화 스크립트는 `*/agent-harness/cli_anything/*/skills/SKILL.md`와 `*/agent-harness/cli_anything/*/SKILL.md` 두 위치를 모두 원본으로 찾는다. 루트 이름은 `cli-anything-<pkg의 _를 -로>`다 | 코드 확인 |

대조 결과와 이탈

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-18 | blender | gimp와 같은 템플릿이다. `session.py`는 에러 문구와 status 키(`scene_name`)만 다르고 `_locked_save_json`, `Session` 본문이 같다. `handle_error`, `cli`, `auto_save_on_exit`, `repl_skin.py`(plugin 원본과 바이트 동일)도 같다. 다른 점은 첫 group 이름(`project` 대신 `scene`), project 필수 키(`scene`), 오류 문구, `setup.py` 장식 필드, `utils/blender_backend.py`의 `find_blender`다 | 코드 확인 |
| R-19 | firefly-iii (HTTP, 무상태) | 세션 파일, `--project`, `--dry-run`, undo가 없다. group이 `--base-url`·`--pat`(또는 환경변수 `FIREFLY_III_BASE_URL`·`FIREFLY_III_PAT`)를 요구하고, 없거나 연결 검증(`GET /api/v1/about`, timeout 10)이 실패하면 어떤 하위 명령보다 먼저 stderr에 텍스트 `Error: ...`를 쓰고 종료 코드 1이다. `--json`을 줘도 JSON 오류는 없다. 명령 실행 중 백엔드가 던지는 `RuntimeError`는 처리되지 않아 traceback과 종료 코드 1이다. REPL은 `invoke_without_command`와 `ctx.invoke(repl)`로 들어가며 자체 축소판 `repl_skin.py`(165줄)를 쓴다 | 코드 확인(실행으로 확인: 가짜 서버가 `/api/v1/about`만 200으로 답함) |
| R-20 | jumpserver (HTTP, 자체 세션) | 세션 파일은 project가 아니라 인증 정보(`~/.jumpserver-cli/session.json`: `base_url`, `username`, `token`, `token_expiry` 등)이고 undo가 없다. 하위 명령 없이 실행하면 REPL이 아니라 help가 나온다. REPL은 `--interactive`/`-i`로만 들어가며 `cmd.Cmd` 기반이다(`ReplSkin` 미사용). `--json`과 `--json-output`이 같은 뜻이다. 오류는 `{"status": "error", "message": ..., "detail"?}` 한 줄을 stderr에 쓰고 종료 코드 1(click 오류는 2)이다. 진입 함수는 `cli_main`, `--dry-run`은 명령마다 있다. `setup.py`에 `package_data`가 없고 `pyproject.toml`도 함께 있다 | 코드 확인(실행으로 확인) |
| R-21 | 계약 이탈과 검사 수단 | 같은 계약을 따르지 않는 하니스가 확인된 것만 5가지 유형이다. 상세는 2.1. 계약을 기계적으로 검사하는 코드는 레포에 없다. `commands/validate.md`는 에이전트가 읽는 체크리스트고, `skill_generator.py`만 패키지 디렉터리의 `__init__.py`와 `setup.py` 존재를 전제로 한다 | 코드 확인(검색 범위는 2.1) |

- 불변식: 일회성 실행에서 프로세스 사이에 남는 상태는 project 파일뿐이다(R-12). 파일에 쓰이는 시점은 R-13(`project save`, 자동 저장, `project new -o`)로 한정된다.
- 미결정: 없음
- 확인 한계: GIMP·Blender가 이 환경에 없어 backend 실행(Script-Fu, `--background`)은 하지 않았다(`find_gimp` 실패 경로만 실행). 실행은 Windows, Python 3.12, click 8.5.1에서 했고 `fcntl` 잠금 분기는 실행하지 못했다. REPL은 TTY가 없어 `create_prompt_session`을 None으로 바꾼 wrapper로 `input()` 경로만 돌렸다. jumpserver의 help 종료 코드는 click 버전에 따라 다를 수 있다(8.5.1에서 2). 69개 일괄 점검은 문자열 휴리스틱이라 구현 방식이 다른 경우를 놓친다.

### 1.5 필수 코드 참조 [필수]

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gimp/agent-harness/cli_anything/gimp/core/session.py:10-33` `_locked_save_json` | 잠금 후 truncate하는 파일 쓰기 | R-13 |
| C-02 | `gimp/agent-harness/cli_anything/gimp/core/session.py:36-155` `Session` | project 보관, `snapshot`·`undo`·`redo`·`status`·`save_session`·`list_history`의 정확한 문구와 키 | R-11, R-12, R-13 |
| C-03 | `gimp/agent-harness/cli_anything/gimp/gimp_cli.py:36-83` `get_session`, `output`, `_print_dict`, `_print_list` | 전역 상태와 텍스트 출력 형식 | R-09 |
| C-04 | `gimp/agent-harness/cli_anything/gimp/gimp_cli.py:86-154` `handle_error`, `cli`, `auto_save_on_exit` | 전역 옵션 선언 블록, `--project` 로드, REPL 진입, 오류 JSON 매핑, 자동 저장 조건 | R-06, R-07, R-08, R-10, R-14 |
| C-05 | `gimp/agent-harness/cli_anything/gimp/gimp_cli.py:735-818` `repl`, `main` | REPL 루프와 진입점 | R-15 |
| C-06 | `gimp/agent-harness/setup.py:9-61` | `setup.py` 형태: namespace 패키지 탐색, 의존성, `console_scripts`, `package_data` | R-02, R-03, R-04 |
| C-07 | `gimp/agent-harness/cli_anything/gimp/utils/gimp_backend.py:25-34` `find_gimp`, `:47-74` `batch_script_fu` | 실행 파일 탐색 오류와 subprocess 호출 형태 | R-05 |
| C-08 | `gimp/agent-harness/cli_anything/gimp/core/project.py:76-92` `open_project`, `save_project` | project 파일 검증(필수 키)과 `project new -o`가 쓰는 비잠금 저장 | R-08, R-13 |
| C-09 | `cli-anything-plugin/repl_skin.py:113-178` `ReplSkin.__init__`, `_detect_color_support` | skill 경로 탐색, history 경로, 색 판정 | R-16, R-17 |
| C-10 | `cli-anything-plugin/repl_skin.py:486-529` `create_prompt_session`, `get_input` | prompt_toolkit 세션과 fallback 입력 | R-15, R-16 |
| C-11 | `.github/scripts/sync_root_skills.py:13-23` `_canonical_skill_id`, `:58-62` `_discover_sources` | 패키지 안 SKILL.md 탐색 위치와 루트 이름 규칙 | R-17 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출. 원본 테스트는 열지 않았다. gimp 사례는 `gimp/agent-harness`를 임시 디렉터리에 복사해 `python -m cli_anything.gimp`로 실행한 결과다(venv에 click, prompt-toolkit만 설치, GIMP 없음). 그래서 backend 호출과 prompt_toolkit 화면은 검증하지 않는다. REPL 사례는 `create_prompt_session`을 None으로 바꾼 wrapper에서 stdin을 파이프로 넣었다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-10, R-11 | project 없이 `--json layer list` | stdout `{"error": "No project loaded. Use 'project new' or 'project open' first.", "type": "RuntimeError"}`, 종료 코드 1 |
| T-02 | R-10 | T-01에서 `--json` 없이 | stderr `Error: No project loaded. ...`, 종료 코드 1 |
| T-03 | R-13, R-14 | `--json project new -o p.json -n t` 후 `--json --project p.json layer new -n A` | p.json 최상위 키 `canvas, guides, layers, metadata, name, selection, version`, `layers` 길이 1, 종료 코드 0 |
| T-04 | R-12 | T-03 직후 새 프로세스에서 `--json --project p.json session undo` | `{"error": "Nothing to undo.", "type": "RuntimeError"}`, 종료 코드 1 |
| T-05 | R-08 | `--json --project nope.json layer list` | JSON 없음, stderr에 `FileNotFoundError: Project file not found: nope.json` traceback, 종료 코드 1 |
| T-06 | R-10 | `layer remove abc` | click 사용법 오류 텍스트, 종료 코드 2 |
| T-07 | R-10, R-14 | `--json --project p.json layer remove 9`(layer 1개) | `{"error": "Layer index 9 out of range (0-0)", "type": "IndexError"}`, 종료 코드 1 |
| T-08 | R-14 | `--dry-run --project p.json layer new -n D` | 종료 코드 0, p.json 내용 그대로(`layers` 수 변하지 않음) |
| T-09 | R-11, R-14 | `--project p.json canvas dpi 300` | 출력은 `new_dpi: 300`인데 p.json의 `canvas.dpi`는 72 그대로 |
| T-10 | R-14 | `--project p.json layer set 0 bogus 1`(snapshot 후 `ValueError`) | 종료 코드 1, p.json 바이트 해시 불변 |
| T-11 | R-07, R-15 | `--json --project p.json`만 주고 stdin에 `layer new -n B`, `session status`, `--json session status`, `session undo`, `layer new -n C`, `layer remove 99`, `bogus`, `quit` | 첫 두 줄은 텍스트, 세 번째 줄만 JSON, undo는 `Undone: Add layer: B`, `remove 99`는 텍스트 `Error: ...`, `bogus`는 `Usage error: No such command 'bogus'.`로 REPL 계속, 종료 후 p.json에 A와 C 두 layer가 저장됨 |
| T-12 | R-07, R-15 | 명시적 `--project p.json repl`로 `layer new -n H`, `quit` | 종료 후 p.json layer 수 +1 |
| T-13 | R-14, R-15 | `--dry-run --project p.json` REPL에서 `layer new -n E`, `quit` | p.json 변화 없음 |
| T-14 | R-13, R-15 | `--dry-run` REPL에서 `layer new -n F`, `project save`, `layer new -n G`, `quit` | F까지만 저장(layer 수 +1), G는 저장되지 않음 |
| T-15 | R-13 | 인자 없는 REPL에서 `project new -n q` 후 `project save` | `Error: No save path specified.` 출력 후 REPL 계속 |
| T-16 | R-02, R-04 | gimp와 godot `agent-harness`에서 `pip wheel --no-deps` | wheel에 `cli_anything/<pkg>/skills/SKILL.md`와 `entry_points.txt`의 `cli-anything-<sw> = cli_anything.<pkg>.<pkg>_cli:main`, `cli_anything/__init__.py`는 없음(godot 소스에는 0바이트 `cli_anything/__init__.py`가 있음) |
| T-17 | R-19 | firefly-iii, 환경변수 없이 `--json accounts list` | stderr 텍스트 `Error: FIREFLY_III_BASE_URL and FIREFLY_III_PAT are required` 외 안내, 종료 코드 1 |
| T-18 | R-19 | 가짜 서버(`/api/v1/about`만 200, 나머지 404)에서 `--json --base-url ... --pat x accounts get --id 3` | traceback 끝 `RuntimeError: Resource not found: /accounts/3`, 종료 코드 1, JSON 없음 |
| T-19 | R-20 | jumpserver, 로그인 없이 `--json asset list` | stderr `{"status": "error", "message": "Not authenticated. Please login first.", "detail": "..."}`, 종료 코드 1 |
| T-20 | R-20 | jumpserver, 인자 없이 실행 | REPL이 아니라 help, click 8.5.1에서 종료 코드 2 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | `cli-anything-plugin/HARNESS.md:672-707` Directory Structure, gimp `git ls-files gimp` 목록, `cli-anything-plugin/commands/validate.md:27-43` 필수 파일 목록 | 문서의 트리를 gimp 파일 목록과 대조했다. 전수 점검: 69개 `*/agent-harness`에 대해 임시 Python 스크립트(`os.path.exists`)로 `cli_anything/<pkg>/<pkg>_cli.py`(Python 하니스 68개 전부 있음), `core/`(64, 없는 곳: dify-workflow, intelwatch, mubu, quietshrink, sketch), `utils/*_backend.py`(53), `tests/TEST.md`(54), `README.md`(64), `__main__.py`(58), `core/session.py`(40)를 셌다. 이름 규칙 예외는 `<pkg>_backend.py`가 아닌 `sox_backend.py`(audacity), `melt_backend.py`(kdenlive, shotcut), `lo_backend.py`(libreoffice) 등 13곳. 놓칠 가능성은 `utils/` 밖에 있는 backend, `tests/` 안 파일이 섞인 것(browser) |
| R-02 | `cli-anything-plugin/HARNESS.md:702-707`, `gimp/agent-harness/setup.py:23`, `godot/agent-harness/setup.py:23`, T-16 | 문서와 구현의 차이: `cli_anything/__init__.py`가 있는 곳은 chromadb, comfyui, godot, intelwatch, obsidian, pm2, seaclip, videocaptioner 8곳이고 모두 0바이트다(`os.path.exists`와 `wc -c`). `setup.py` 67개 전부가 `find_namespace_packages`를 쓰고 `find_packages`는 0개다. 8곳은 모두 같은 `include=["cli_anything.*"]` 패턴이고, 그중 godot의 wheel만 직접 빌드해 그 파일이 없음을 확인했다. 나머지 7곳은 같은 패턴이라는 근거로 같은 결과라고 추론했다. source 트리에서 `agent-harness`를 현재 디렉터리로 두고 import할 때의 영향은 추론이다 |
| R-03 | `gimp/agent-harness/setup.py:51-55`, `cli-anything-plugin/guides/pypi-publishing.md:27-70`, `registry.json` gimp·blender 항목의 `install_cmd`, `unimol_tools/agent-harness/pyproject.toml:26-27`, `jumpserver/agent-harness/setup.py:37-41` | `setup.py` 전수에서 `"cli-anything-...=module:func"` 정규식으로 추출: 함수 `main` 58, `cli` 7, `entrypoint` 2, `cli_main` 1, 스크립트 이름이 `cli-anything-<dir>`와 다른 곳 `cc-switch`(`ccswitch`), `slay_the_spire_ii`(`sts2`), lldb는 2개. `setup.py`가 있는 하니스는 67개이고 `unimol_tools`는 `pyproject.toml`만 있으며(`git ls-files unimol_tools | grep setup`에 결과 없음), `sketch`는 `package.json`과 `src/cli.js`인 Node 하니스라 `cli_anything/`이 없다. 메인 점검의 "console_scripts 67"은 `setup.py` 기준 수치이고 `unimol_tools`를 더하면 68이다. 레지스트리 79개 중 `install_cmd`가 `pip install git+...`인 것이 73개, PyPI 이름(`pip install cli-anything-...`)은 4개(전수 집계)다. 그래서 "각각 PyPI 패키지"는 형태일 뿐 PyPI 게시를 뜻하지 않는다(게시 여부는 확인하지 않음) |
| R-04 | `gimp/agent-harness/setup.py:35-59`, `cli-anything-plugin/HARNESS.md:286-292`, T-16 | gimp wheel 파일 목록(`zipfile`)으로 포함·제외 확인. `package_data`의 skills 항목이 없는 `setup.py`는 jumpserver와 Node인 sketch뿐이고(`setup.py` 전수 문자열 점검), `unimol_tools`는 `pyproject.toml`의 `package-data`가 `*.md`다. jumpserver는 `MANIFEST.in`이 없어 wheel에 `SKILL.md`가 들어가는지는 빌드하지 않아 추론이다 |
| R-05 | C-07, `cli-anything-plugin/HARNESS.md:54-58,482-488`, `gimp/agent-harness/cli_anything/gimp/utils/gimp_backend.py:367-451` `render_project`, `blender/agent-harness/cli_anything/blender/utils/blender_backend.py:14-22` | 문서와 구현의 차이: `HARNESS.md:485-488`은 "대체 라이브러리로 fallback하지 말라"고 하지만 gimp의 `core/export.py:68-84` `render`는 `render_project`가 어떤 예외든 던지면(`except Exception: pass`) Pillow 경로로 넘어간다. 이 사실은 gimp 하니스 도메인 동작이므로 계약 규칙에는 넣지 않았다. HTTP 하니스의 backend는 `requests` 클라이언트이고 같은 `RuntimeError` 규칙을 쓴다(`firefly_iii_backend.py:59-105`) |
| R-06 | C-04(`gimp_cli.py:117-139`), `blender/agent-harness/cli_anything/blender/blender_cli.py:191-214` | gimp와 blender의 선언을 읽었다. 하위 명령에 `--json`이 없다는 것은 `gimp_cli.py`에서 `"--json"` 문자열이 117행 한 번뿐이라는 검색(`grep -c`) 범위의 결과다. 하위 명령 41개 모두에 `@handle_error`가 붙어 있고 group callback·`result_callback`에는 붙어 있지 않다(`grep -c '@handle_error'` 41) |
| R-07 | `gimp_cli.py:138-139,735-740`, `cli-anything-plugin/HARNESS.md:99-109`, T-11, T-12 | 문자열 점검 `invoke_without_command=True` 64개는 실제 REPL 진입을 뜻하지 않을 수 있다. `ctx.invoke(...repl...)` 패턴(`ctx\.invoke\(\s*[a-z_]*repl[a-z_]*`)은 `*_cli.py`에서 49개였다. quietshrink, cc-switch처럼 같은 옵션을 다른 용도로 쓰는 곳이 있어 나머지 15개의 실제 동작은 열지 않았다(추론: 이 중 일부는 REPL이 아니다) |
| R-08 | C-04(`gimp_cli.py:132-136`), C-08(`project.py:76-84`), T-05 | 실행으로 확인. `handle_error`는 group callback이 아니라 각 하위 명령 함수에만 붙어 있다(`gimp_cli.py`에서 `@handle_error` 위치 확인) |
| R-09 | C-03, `gimp_cli.py:227-232` `project_json` | 읽기 |
| R-10 | C-04(`gimp_cli.py:86-113`), `blender_cli.py:160-186`, T-01, T-02, T-06, T-07 | 실행으로 확인. `handle_error`는 `FileNotFoundError`를 먼저 잡고 그다음 `(ValueError, IndexError, RuntimeError)`, `FileExistsError` 순서다. 오류 JSON 모양의 전수 분포는 정규식 휴리스틱이다. `"error"`+`"type"`을 쓰는 곳 35(대표 gimp·blender 포함), `{"status":"error","message"}`를 쓰는 곳 4(cloudcompare, godot, jumpserver, wiremock), `"error"` 키만 쓰는 곳 17(adguardhome 등), 오류 JSON 문자열이 없는 곳 13(firefly-iii, pm2, zotero 등). 표본 확인: adguardhome(`{"error": str(exc)}`, `sys.exit(1)`), godot(`{"status": "error", "message"}`), pm2·zotero(오류 JSON 코드 없음). 이 분포는 정규식이 놓친 형식(헬퍼 함수 안)을 센 것이 아니라서 실제와 다를 수 있다 |
| R-11 | C-02(`gimp/agent-harness/cli_anything/gimp/core/session.py:63-76`), `gimp_cli.py:439-446` `canvas_dpi`, T-09 | 실행으로 확인. gimp의 project 내용을 바꾸는 명령 18개(layer 8, canvas 5, filter 3, draw 2) 중 `snapshot` 호출은 17곳(`gimp_cli.py:256-717`)이고 `canvas dpi`만 호출이 없다. 도메인 함수 내부(`layers.py` 등)는 열지 않았다 |
| R-12 | C-02(`gimp/agent-harness/cli_anything/gimp/core/session.py:78-127,146-155`), T-04 | 실행으로 확인. 21개 하니스에 `_undo_stack`·`def undo(`가 있고, 그중 어느 `save_session`도 undo 기록을 파일에 쓰지 않았다(`json.dump` 호출 근처에 `undo`·`history`를 쓰는 곳을 정규식으로 찾았으나 없음). 이 점은 gimp `save_session`의 docstring("project + undo history")과 다르다. 이 정규식은 함수 안에서 다른 이름으로 저장하는 경우를 놓친다 |
| R-13 | C-01, C-02(`gimp/agent-harness/cli_anything/gimp/core/session.py:129-144`), `cli-anything-plugin/guides/session-locking.md:1-39`, C-08(`project.py:87-92`), `gimp_cli.py:164-185` `project_new` | `_locked_save_json` 22개(`session.py` 40개 중), 같은 함수를 쓰는 레포 전체 파일은 23개 하니스로 집계. 가이드는 "모든 하니스" 대상이라고 쓰지만 잠금 코드는 일부에만 있다. `project new -o`와 `project save`는 서로 다른 writer다(`project new -o`는 `save_project`, 잠금 없음, 디렉터리 생성 없음). 쓰기 중단 시 손상 가능성은 추론 |
| R-14 | C-04(`gimp_cli.py:142-154`), `cli-anything-plugin/guides/auto-save-dry-run.md:1-87`, T-07~T-10, T-13, T-14 | 실행으로 확인. `--dry-run`이 있는 하니스는 22개(문자열 `--dry-run`), jumpserver는 명령 단위 옵션이다(`commands_asset.py:95`). `result_callback`이 `SystemExit` 때 돌지 않는 점은 T-10으로 확인 |
| R-15 | C-05(`gimp_cli.py:735-818`), `gimp_cli.py:129-130`, T-11~T-15 | 실행으로 확인. 문서와 구현의 차이는 R-15 본문에 적었다(`auto-save-dry-run.md:61-67`은 "REPL never auto-saves"). 줄마다 `--json`이 필요하다는 점은 T-11의 세 번째 줄로 확인. blender도 같은 코드(`blender_cli.py:191-228,1074-1148`)지만 blender REPL은 실행하지 않았다. `_repl_commands`(help 목록, `gimp_cli.py:756-767`)는 손으로 쓴 사전이라 명령 추가 때 어긋날 수 있다는 점은 추론이다 |
| R-16 | C-09, C-10, `cli-anything-plugin/repl_skin.py:340-364` 메시지 함수, `firefly-iii/agent-harness/cli_anything/firefly_iii/utils/repl_skin.py` | 바이트 비교(`cmp`)로 62개 중 49개가 동일, 다른 13개(3MF, QGIS, calibre, exa, firefly-iii, macrocli, mermaid, minimax, n8n, unimol_tools, unrealinsights, videocaptioner, wavetone)는 줄 수가 87~703으로 다르다. 메인 점검의 "`ReplSkin` 62"는 `repl_skin.py` 정의 파일이 있는 하니스 수다. `ReplSkin(`을 하니스 코드(정의 파일·tests 제외)에서 실제로 호출하는 곳은 57개다(cc-switch, comfyui, intelwatch, jumpserver, live2d, n8n, notebooklm, quietshrink, rekordbox, web-yu-pri, wiremock은 호출 없음) |
| R-17 | C-09(`repl_skin.py:141-156`), C-11, `cli-anything-plugin/HARNESS.md:262-265,280-284`, `gimp/agent-harness/setup.py:56-58` | `git ls-files | grep agent-harness/.*SKILL.md`로 70개: 패키지 `skills/SKILL.md` 67, 패키지 루트 `SKILL.md` 1(unimol_tools), 다른 위치 2(`firefly-iii/agent-harness/skills/cli-anything-firefly-iii/SKILL.md`, `openrefine/agent-harness/skills/cli-anything-openrefine/SKILL.md`, 둘은 `_discover_sources` glob에 걸리지 않음). `skills/SKILL.md`가 없는 하니스는 sketch, unimol_tools(루트에 있음). 이름 변환 규칙의 나머지(`name` frontmatter 정규화)는 형제 스펙 `skill-packaging`이 소유한다 |
| R-18 | `blender/agent-harness/cli_anything/blender/core/session.py`와 gimp 대조(`diff`, 이름 치환 후 문구 차이만), `blender_cli.py:160-228`, `blender/agent-harness/cli_anything/blender/core/scene.py:134-151`, `blender/agent-harness/setup.py:59`, `cmp utils/repl_skin.py cli-anything-plugin/repl_skin.py` | 읽기와 `diff`. blender의 `preview live` 하위 명령(`blender_cli.py:66-134,890-`)은 계약 범위 밖이라 읽지 않았다 |
| R-19 | `firefly_iii_cli.py:68-108,152-210`, `firefly_iii_backend.py:34-105`, T-17, T-18 | 실행으로 확인(가짜 HTTP 서버를 임시 디렉터리에 띄움). `firefly_iii_cli.py:75-81`은 `--preset` 옵션(MCP 시절 흔적으로 보임, 추론)이 있다 |
| R-20 | `jumpserver_cli.py:46-87,210-267,284-308`, `jumpserver/agent-harness/cli_anything/jumpserver/utils/__init__.py:18-40`, `jumpserver/agent-harness/cli_anything/jumpserver/core/session.py:19-61`, `jumpserver/agent-harness/setup.py:1-45`, T-19, T-20 | 실행으로 확인(click 8.5.1). 종료 코드 2는 click 버전 의존일 수 있다 |
| R-21 | 아래 이탈 하니스 표본, 검색 명령은 아래 문단 | 표본 확인 |
| T-01~T-20 | 임시 디렉터리 `gimp-h`(gimp 복사본), `ff-h`, `js-h`(firefly-iii·jumpserver 복사본)에서 실행. 원본 레포는 수정하지 않았다 | 환경: Windows, Python 3.12, click 8.5.1, `PYTHONUTF8=1`(기본 cp949 인코딩에서는 배너 출력이 `UnicodeEncodeError`가 되고 그것도 R-10 경로로 `{"error": ..., "type": "UnicodeEncodeError"}`가 됨을 실행으로 확인) |

R-21의 이탈 하니스. 전수 점검(`os.path.exists`·정규식, 기준 SHA 작업트리)에서 메인 점검의 수치를 재현했고(`--json` 65, `invoke_without_command=True` 64, `setup.py` console_scripts 67, `skills/SKILL.md` 67, `TEST.md` 54, `cli_anything/__init__.py` 8곳) 아래 하니스를 열어 확인했다.

- Python 패키지가 아닌 것: `sketch`(Node, `package.json`, 진입점 `sketch-cli`, `registry.json` 772-780행), `slay_the_spire_ii`는 Python이지만 C# bridge를 포함하고 `--json` 옵션 없이 항상 JSON을 출력한다.
- `setup.py` 없이 `pyproject.toml`만 있는 것: `unimol_tools`. `pyproject.toml`만 `setup.py`와 함께 있는 곳은 jumpserver, mubu, n8n, nslogger, zotero다(`git ls-files '*/agent-harness/pyproject.toml'`).
- 단순 전달 래퍼: `intelwatch`(`intelwatch_cli.py:9-30`, `click.command`가 `npx intelwatch`에 인자를 넘김, group·`--json`·REPL 없음), `dify-workflow`(upstream CLI에 인자를 전달, 자체 `--json` 없음, `ctx.invoke(repl)`은 있음).
- REPL이 없거나 방식이 다른 것: `live2d`(`repl` 문자열이 `*.py` 전체에 없음), `jumpserver`(R-20), `wiremock`(`invoke_without_command` 없음, `repl_skin.py`는 있으나 호출 없음).
- 오류·세션 형식이 다른 것: `firefly-iii`(R-19), `jumpserver`(R-20), 앞의 오류 JSON 분포.

"이탈하는 하니스는 이것뿐이다"는 주장이 아니다. 위는 문자열 점검에서 항목이 빠진 하니스(`--json` 4곳, `invoke_without_command` 5곳, `ReplSkin(` 호출 11곳, `TEST.md` 15곳)를 우선으로 열어 본 결과이고, `TEST.md`가 없는 15곳(3MF, browser, godot, intelwatch, live2d, macrocli, novita, openscreen, quietshrink, rekordbox, shotcut, siyuan, sketch, unimol_tools, videocaptioner)은 열지 않았다. 문자열 점검은 `--json` 옵션이 하위 명령에만 있거나 헬퍼로 선언된 경우를 놓칠 수 있고, 오류 JSON 분포는 정규식이므로 값은 후보다.

### 2.2 코드 읽는 순서 [선택]

`cli-anything-plugin/HARNESS.md`의 `Directory Structure`(672-707)와 `Principles & Rules`(480-532)로 문서가 요구하는 형식을 먼저 읽고, `gimp/agent-harness/setup.py`로 패키지 진입을 본 뒤, `gimp_cli.py` 위에서 아래로(전역 상태 36-60, `handle_error` 86-113, `cli` 116-154, `repl` 735-809), `core/session.py`, `cli-anything-plugin/repl_skin.py:106-178`을 읽는다. 변형은 `firefly_iii_cli.py`와 `jumpserver_cli.py`가 각각 200줄대와 300줄이라 한 번에 읽힌다.

### 2.3 비교·재사용 출처 [선택]

기능 스펙 `harness-sop`가 이 계약의 7단계 절차 쪽을 맡고, `skill-packaging`이 `SKILL.md` 생성과 루트 동기화를, `harness-families`가 백엔드 분류를 맡는다. 다른 레포의 같은 기능 스펙은 없다. 원본 코드를 복사해 쓰지 않았다.

### 2.4 검토 기록 [필수, ready 스펙]

`draft`라서 아직 해당하지 않는다. 메인 점검 때 채운다.
- 방식: 미수행
- 대조한 R-ID: 없음
- 대조하지 않은 R-ID: 전부
- 재구현: 미수행

## 적용 메모 [선택]

Claude Code에서 "앱 → CLI + skill" 생성 절차를 설계할 때 원본 계약에서 바꾸면 좋을 점의 후보다. 원본의 미결정을 해소한 것은 아니다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-12, R-14, R-15 | undo가 새 프로세스에서도 이어지게 하려면 history를 별도 파일에 저장하거나, undo를 REPL 전용 기능으로 명시한다 | 일회성 호출이 기본인 에이전트 사용에서는 `session undo`가 항상 실패한다(T-04). `status`가 `undo_count`를 보여 주는 것도 오해를 부른다 | project 파일 구조 또는 `session` 명령 설명이 바뀐다. T-04 기대값이 달라진다 |
| R-11, R-14 | 변경 감지를 `snapshot` 호출이 아니라 저장 직전 project 비교(해시 등)로 한다 | `snapshot`을 빼먹은 명령이 자동 저장되지 않는 결함(T-09)을 막는다 | `_modified` 의미가 바뀐다 |
| R-10, R-19, R-20 | 오류 JSON을 하니스 전체에서 한 모양(예 `{"error","type"}` stdout, 종료 코드 1)으로 통일하고, group callback 안의 오류(`--project` 로드)도 같은 처리를 거치게 한다 | HTTP 하니스는 텍스트·traceback·다른 JSON 키를 쓰고, `--project` 로드 실패는 JSON이 아니다(T-05, T-18, T-19). 에이전트가 오류를 한 방식으로 읽기 어렵다 | T-05, T-17~T-19 기대값이 달라진다 |
| R-15 | REPL 줄에 바깥 `--json`을 이어 준다 | 에이전트가 REPL을 쓸 때 줄마다 `--json`을 붙여야 하는 불편(T-11)을 없앤다 | `_json_output`을 줄마다 덮어쓰지 않는 흐름 |
| R-01~R-04, R-21 | 계약을 검사하는 스크립트(레이아웃, `__init__.py`, entry point, `package_data`)를 둔다 | 지금은 에이전트 프롬프트(`validate.md`)뿐이라 8곳의 `cli_anything/__init__.py`와 pyproject 전용·Node 하니스 같은 이탈이 잡히지 않는다 | 새 검사 명령 |
