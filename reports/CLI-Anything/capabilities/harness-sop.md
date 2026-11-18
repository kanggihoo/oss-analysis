---
sha: "34f519533bc175d2fe287ab8316b0dd99bb9cc43"
created: 2026-11-18
updated: 2026-11-18
sources:
  - cli-anything-plugin/HARNESS.md
  - cli-anything-plugin/commands/cli-anything.md
  - cli-anything-plugin/commands/refine.md
  - cli-anything-plugin/commands/test.md
  - cli-anything-plugin/commands/validate.md
  - cli-anything-plugin/commands/list.md
  - cli-anything-plugin/guides/auto-save-dry-run.md
  - cli-anything-plugin/guides/session-locking.md
  - cli-anything-plugin/guides/pypi-publishing.md
  - cli-anything-plugin/guides/skill-generation.md
  - cli-anything-plugin/guides/mcp-backend.md
  - cli-anything-plugin/guides/filter-translation.md
  - cli-anything-plugin/.claude-plugin/plugin.json
  - cli-anything-plugin/verify-plugin.sh
  - cli-anything-plugin/scripts/setup-cli-anything.sh
  - cli-anything-plugin/README.md
  - cli-anything-plugin/skill_generator.py
  - .claude-plugin/marketplace.json
  - gimp/agent-harness/cli_anything/gimp/core/export.py
  - gimp/agent-harness/setup.py
  - gimp/agent-harness/cli_anything/gimp/gimp_cli.py
  - skills/cli-anything-gimp/SKILL.md
  - drawio/agent-harness/cli_anything/drawio/core/export.py
  - freecad/agent-harness/cli_anything/freecad/tests/test_full_e2e.py
  - cli-hub/setup.py
depends: []
status: draft
---

# 하니스 제작 절차 (SOP·규칙·제작 명령)

> 에이전트가 앱 소스 경로나 GitHub URL을 받아 Phase 1~7(6.5 포함)로 `cli-anything-<software>` 하니스를 만들 때 따를 단계, 산출물, 필수·금지 규칙과, 제작·보강·테스트·검증·탐색 명령 5종의 입력·단계·산출물을 정한 문서 계약이다.

이 기능은 실행되는 코드가 아니고, 코딩 에이전트가 읽고 따르는 마크다운이다. 이 스펙의 R-ID는 "문서가 에이전트에게 무엇을 요구하는가"이고, 에이전트가 실제로 그렇게 했는지는 R-ID가 아니라 2.1의 "문서와 실제 상태의 차이"가 다룬다. 검증 수준 `코드 확인`은 이 문서에서 "문서 문구를 직접 읽었다"는 뜻이다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 사용자가 `/cli-anything <앱 소스 경로 | GitHub URL>`을 실행한다. 에이전트는 다른 일보다 먼저 `HARNESS.md`를 읽는다(R-01). URL이면 로컬에 clone하고, 디렉터리 이름에서 software 이름을 정한다(R-03).
2. Phase 1~2에서 백엔드 엔진·데이터 모델·기존 CLI를 분석하고, 상호작용 모델·명령 그룹·상태 모델·출력 형식을 설계한 뒤 앱별 SOP 문서 `<SOFTWARE>.md`를 쓴다(R-04).
3. Phase 3에서 데이터 계층 → probe/info → 변경 명령 → 백엔드 모듈 → 렌더링 → 세션 → REPL 순으로 구현한다. 세션 저장은 락을 쓰고(R-07), session 기반 CLI는 one-shot 변경 뒤 auto-save하며 `--dry-run`으로 끈다(R-08).
4. Phase 4에서 코드보다 먼저 `TEST.md`에 테스트 계획을 쓰고(R-09), Phase 5에서 unit·E2E·실제 소프트웨어 E2E·subprocess 테스트를 쓴 뒤(R-10~R-13), Phase 6에서 통과한 결과를 같은 `TEST.md`에 덧붙인다(R-14).
5. Phase 6.5에서 `SKILL.md`를 생성하고(R-15), Phase 7에서 `setup.py`를 만들어 `pip install -e .`와 PATH 설치를 검증한다(R-16).
6. 11개 성공 기준(R-24)을 만족하면 제작이 끝난다. 이후 `refine`(커버리지 확장, R-25), `test`(재실행과 결과 기록, R-26), `validate`(규칙 점검 보고, R-27), `list`(설치·생성된 하니스 탐색, R-28)를 쓴다.

Phase 번호 순서가 문서에서 명시적으로 강제하는 선후는 두 가지다. `TEST.md` 계획은 테스트 코드보다 먼저(`cli-anything-plugin/HARNESS.md:113`), `SKILL.md` 생성은 Phase 6이 성공한 뒤(`cli-anything-plugin/guides/skill-generation.md:87-89`).

### 1.2 범위·통합 지점

- 제공: 하니스 제작 SOP의 단계·산출물·필수·금지 규칙, 제작 명령 5종의 인자·단계·성공/실패 처리, 이 문서들이 플러그인 `cli-anything`으로 배포되는 방식.
- 제외와 경계:
  - 하니스 내부의 CLI 표면(`--json`·세션 파일·오류 JSON 형식)과 패키지 레이아웃 상세는 형제 스펙 harness-contract가 맡는다. 여기서는 SOP가 "무엇을 요구하는가"(R-17, R-20, R-21)까지만 쓴다.
  - 앱 69개의 분류와 백엔드 방식은 harness-families, `SKILL.md` 생성기·루트 동기화는 skill-packaging, 레지스트리 항목 형식은 registry-schema가 맡는다. R-15는 SOP가 요구하는 산출 위치까지만 적는다.
  - `guides/preview-methodology.md`, `docs/PREVIEW_PROTOCOL.md`의 상세는 feature map 행 6(제외)이다. R-22는 `HARNESS.md`가 정한 요구 수준(MUST/SHOULD)만 쓴다.
  - 개별 하니스의 `core/` 구현은 읽지 않았다.
  - `guides/timecode-precision.md`(29.97fps 반올림), `guides/filter-translation.md`(필터 변환 함정)는 영상·오디오 하니스에만 해당하는 조건부 지침이라 세부를 옮기지 않는다. R-19는 연결 조건과 위치만 적는다.
- 외부 의존·선행 계약: 없음(`depends: []`). 이 문서를 읽고 실행하는 코딩 에이전트(Claude Code 등)와 Python·pytest·Click 환경을 호출자가 제공한다. 명령 파일을 슬래시 명령으로 올리는 것은 Claude Code 플러그인 메커니즘이고 이 레포 코드가 아니다(R-29).
- 소유 상태·부작용: 이 기능 자체는 상태가 없다. 에이전트가 따르면 `<software>/agent-harness/` 아래 파일 트리, `skills/cli-anything-<software>/SKILL.md`, `TEST.md`가 생기고 `pip install -e .`로 로컬 환경에 패키지가 설치된다. `test`는 `TEST.md`를 갱신한다(R-26). `list`와 `validate`가 파일을 바꾸는지는 문서에 쓰여 있지 않다(U-03).

### 1.3 인터페이스와 데이터 의미

명령은 `cli-anything-plugin/commands/<이름>.md` 파일 하나가 슬래시 명령 하나를 정의한다. 파일 이름이 `cli-anything.md`인 명령만 `/cli-anything`이고 나머지는 `/cli-anything:<이름>`이라고 문서에 적혀 있다(`cli-anything-plugin/README.md:84-122`는 이름 표기만 보여 주고, 이 이름이 파일명에서 나온다는 것은 추론, R-29).

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `/cli-anything <software-path-or-repo>` | 입력: 필수 1개. 로컬 경로(`/home/user/gimp`, `./blender`) 또는 GitHub URL(`https://github.com/GNOME/gimp`, `github.com/blender/blender`). 출력: 하니스 트리와 `SKILL.md` | 앱 이름만(`gimp`)은 받지 않는다. URL이면 로컬에 clone하고 그 사본에서 작업한다. software 이름은 디렉터리 이름에서 정한다(R-03). |
| `/cli-anything:refine <software-path> [focus]` | 입력: 로컬 경로 필수(최초 build에 쓴 같은 소스 트리), `focus` 자연어 선택. 출력: 새 명령·테스트·문서 갱신 | URL은 받지 않는다. `focus`가 있으면 능력 분석과 gap 분석을 그 영역으로 좁힌다(R-25). |
| `/cli-anything:test <software-path-or-repo>` | 입력: build와 같은 형식. 출력: pytest 결과와 갱신된 `TEST.md` | 실패하면 `TEST.md`를 갱신하지 않는다(R-26). |
| `/cli-anything:validate <software-path-or-repo>` | 입력: build와 같은 형식. 출력: 8개 범주의 점검 보고서 | 점검 항목 목록은 C-07, 보고서 형식은 `cli-anything-plugin/commands/validate.md:94-113`. 통과 판정 기준은 U-03. |
| `/cli-anything:list [--path <dir>] [--depth <n>] [--json]` | 입력: `--path` 기본 현재 디렉터리, `--depth` 기본 무제한, `--json` 플래그. 출력: 표 또는 JSON(`tools` 배열, `total`, `installed`, `generated_only`) | 설치된 하니스와 생성된 하니스를 이름 기준으로 합친다(R-28). |
| 하니스 산출물 | `<software>/agent-harness/` 아래: `<SOFTWARE>.md`, `setup.py`, `cli_anything/<software>/` 안에 `README.md`·`<software>_cli.py`·`core/`·`utils/`(`<software>_backend.py`, `repl_skin.py`)·`tests/`(`TEST.md`, `test_core.py`, `test_full_e2e.py`)·`skills/SKILL.md`. 저장소 루트의 `skills/cli-anything-<software>/SKILL.md` | 필수 파일과 이름의 상세 계약은 harness-contract. 이 스펙은 SOP 각 Phase가 어떤 파일을 만들라고 하는지만 R-04~R-21에서 쓴다. |

### 1.4 행동 규칙과 남은 질문

공통 규칙과 Phase

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `/cli-anything`, `refine`, `test`, `validate`를 실행한다 | 네 명령 문서는 모두 실행 전에 `HARNESS.md`를 읽으라고 요구한다. `/cli-anything`은 "Do not improvise — follow the harness specification"까지 적는다. `list`에는 그런 요구가 없다. `HARNESS.md`가 `./HARNESS.md`로 어느 경로를 가리키는지는 U-01. | 코드 확인 |
| R-02 | 하니스를 처음부터 만든다 | `HARNESS.md`는 Phase 1~7(6.5 포함, 8단계)을 정의한다. `commands/cli-anything.md`는 이 앞에 Phase 0(소스 확보)을 더해 9단계로 설명하고, 각 Phase가 `HARNESS.md` 기준을 따른다고 적는다. Phase 0은 `HARNESS.md`에 없다. | 코드 확인 |
| R-03 | `/cli-anything`에 인자를 준다 | 인자는 필수다. 로컬 경로나 GitHub URL만 받고, 앱 이름만 주는 것은 "NOT accepted"다(거절 시 에이전트가 하는 동작은 문서에 없음, U-02). URL이면 로컬 작업 디렉터리에 clone한 뒤 그 사본에서 작업하고, 로컬 경로면 존재와 소스 포함 여부를 확인한다. software 이름은 디렉터리 이름이다(`/home/user/gimp`는 `gimp`). | 코드 확인 |
| R-04 | Phase 1~2 | Phase 1: 백엔드 엔진, GUI 동작과 API 호출의 대응, 데이터 모델(파일 포맷·상태 표현), 기존 CLI 도구, undo/redo(command pattern)를 분석한다. Phase 2: 상호작용 모델(REPL / subcommand / 둘 다, 둘 다를 권장), 명령 그룹(project, core, import/export, config, session), 상태 모델(무엇을 지속하는지·어디에 저장하는지·직렬화 방식), 출력 형식(사람용과 `--json`)을 정한다. 설계 결과로 앱별 SOP `<SOFTWARE>.md`(예: `GIMP.md`)를 쓴다. `HARNESS.md`의 Phase 2는 이 파일을 언급하지 않고 `commands/cli-anything.md`와 디렉터리 구조 절만 요구한다. | 코드 확인 |
| R-05 | Phase 3 구현 | 순서: 데이터 계층(XML/JSON) → probe/info 명령 → 변경 명령(논리 연산마다 명령 하나) → 백엔드 통합 → 렌더링/export → 세션 관리 → REPL. `utils/<software>_backend.py`는 실행 파일을 `shutil.which()`로 찾고, `subprocess.run()`으로 인자를 붙여 호출하고, 못 찾으면 설치 안내가 든 오류를 낸다. export는 유효한 중간 파일을 만든 뒤 실제 소프트웨어를 호출한다. 모든 import는 `cli_anything.<software>.*` 네임스페이스다. | 코드 확인 |
| R-06 | Phase 3 REPL | `cli-anything-plugin/repl_skin.py`를 `utils/repl_skin.py`로 복사해 `ReplSkin`으로 배너·프롬프트·help·메시지를 만든다. 메인 Click group에 `invoke_without_command=True`를 주고 하위 명령이 없으면 `repl`을 호출해, `cli-anything-<software>`만 입력하면 REPL이 뜨게 한다. `ReplSkin`은 모노레포에서 실행하면 루트 `skills/cli-anything-<software>/SKILL.md`를, 설치된 환경에서는 패키지 안 `skills/SKILL.md`를 배너 경로로 보여 준다. | 코드 확인 |
| R-07 | 세션 JSON을 저장한다 | 맨 `open("w")` 뒤 `json.dump`는 쓰지 않는다(락을 잡기 전에 파일이 잘린다). `"r+"`로 열고, 락을 잡은 뒤, 락 안에서 truncate하고 쓰는 `_locked_save_json` 패턴을 `core/session.py`에 복사한다(C-02). 파일이 없으면 디렉터리를 만들고 `"w"`로 첫 저장을 한다. `fcntl`이 없거나 `OSError`면(Windows·미지원 파일시스템) 락 없이 진행한다. | 코드 확인 |
| R-08 | session 기반 CLI(`core/session.py`에 `save_session()`과 `_modified`, `--project` 플래그, 변경 전 `sess.snapshot()`)를 만든다 | `cli-anything.md`는 이것을 필수(Required)로 두고 성공 기준 11번에 넣는다. 메인 group에 `--dry-run` 옵션을 달고 `@cli.result_callback()`을 추가한다(C-03). one-shot 명령은 실행·출력 뒤 `_modified`이고 `project_path`가 있으면 저장한다. `--dry-run`이면 저장하지 않는다. REPL에서는 `--dry-run`을 받되 무시하고 자동 저장도 하지 않는다. `handle_error`가 `sys.exit(1)`로 끝난 오류 경로에서는 callback이 호출되지 않으므로 저장되지 않는다. 자동 저장이 예외를 내면 stderr에 `Warning: Auto-save failed: ...`만 쓰고 명령은 이미 끝난 상태다. stateless API client, 서비스 wrapper, 영속 프로젝트 파일이 없는 하니스에는 적용하지 않는다. group이 세션을 inline으로 여는 하니스는 `ctx.call_on_close`로 같은 동작을 낼 수 있다. | 코드 확인 |
| R-09 | Phase 4 | 테스트 코드를 쓰기 전에 `agent-harness/cli_anything/<software>/tests/TEST.md`를 만든다. 반드시 들어갈 4항목: (1) 테스트 인벤토리 계획(`test_core.py` XX개, `test_full_e2e.py` XX개), (2) 모듈별 unit 계획(함수·엣지 케이스·개수), (3) E2E 계획(워크플로, 생성할 실제 파일, 검증할 출력 속성, 포맷 검증), (4) 현실적 워크플로 시나리오(이름·모사 대상·연쇄 연산·검증 항목). | 코드 확인 |
| R-10 | Phase 5 | 테스트 계층과 파일: unit(`test_core.py`, 합성 데이터, 외부 의존 없음), E2E 중간 파일 검증(`test_full_e2e.py`, 프로젝트 파일 구조 유효성), E2E 실제 백엔드(R-11), subprocess(R-12). 그 외 나열되는 round-trip 테스트(CLI로 만든 프로젝트를 GUI로 열어 확인)와 agent 테스트(에이전트가 CLI만으로 실제 작업 수행)는 MUST 표현이 없고 성공 기준(R-24)에도 없다. 현실적 워크플로 시나리오로 다중 구간 편집, montage, PiP, 색 보정, 오디오 믹싱, undo/redo 스트레스, 저장·불러오기 round-trip, 반복 수정이 예시된다. | 코드 확인 |
| R-11 | 실제 백엔드 E2E를 쓴다 | 반드시 실제 소프트웨어를 호출해 프로젝트를 만들고 export한 뒤 출력을 검증한다: 파일 존재와 크기 > 0, 올바른 포맷(PDF는 `%PDF-` magic bytes, DOCX/XLSX/PPTX는 유효한 ZIP/OOXML), 가능하면 내용. 사용자가 직접 열어 볼 수 있게 산출물 경로를 출력한다. "No graceful degradation": 소프트웨어가 없으면 테스트는 skip이 아니라 실패한다. 중간 파일만 테스트하는 것은 금지다. | 코드 확인 |
| R-12 | subprocess 테스트를 쓴다 | 설치된 `cli-anything-<software>` 명령을 사용자·에이전트처럼 `subprocess.run`으로 호출하며, 최종 출력(중간 ODF가 아님)까지 만든다. 명령 해석은 항상 `_resolve_cli("cli-anything-<software>")`로 하고(C-01) `sys.executable`·모듈 경로를 직접 박지 않는다. `cwd`를 지정하지 않는다. 환경변수 `CLI_ANYTHING_FORCE_INSTALLED=1`이면 PATH에 명령이 없을 때 `RuntimeError`, 아니면 `python -m` 모듈로 fallback하며 어느 쪽을 쓰는지 `[_resolve_cli] ...` 줄을 출력한다. CI·릴리스 테스트는 force 모드로 돌려 설치된 명령이 쓰였음을 보장한다. 최소 `--help`, `--json`, 프로젝트 생성, 핵심 명령, 전체 워크플로를 시험한다. | 코드 확인 |
| R-13 | export·render를 검증한다 | 오류 없이 끝났다는 것만으로는 통과가 아니다. 프로그램으로 출력을 분석한다: magic bytes, OOXML ZIP 구조, 영상·이미지는 프레임 probe와 밝기·채도 비교(해상도가 다르면 letterbox 검은 막대를 제외), 오디오는 시작·끝 RMS와 스펙트럼 비교, 길이·포맷을 기대값과 비교한다. | 코드 확인 |
| R-14 | Phase 6 | 모든 테스트가 성공한 뒤 기존 `TEST.md`에 덧붙인다(덮어쓰지 않는다): 테스트 결과(`pytest -v --tb=no` 전체 출력), 요약 통계(총 개수·통과율·실행 시간), 커버리지 메모(미커버 영역). 결과적으로 `TEST.md`는 구현 전 계획과 실행 후 결과를 모두 가진다. | 코드 확인 |
| R-15 | Phase 6.5 | Phase 6 뒤에 `SKILL.md`를 생성한다. frontmatter는 `name: "cli-anything-<software>"`, `description`, 본문은 설치 전제, 명령 문법, 명령 그룹, 예시, 에이전트용 지침(`--json`, 오류 처리). 자체완결적이어야 한다. `skill_generator.py` 자동 추출 또는 `templates/SKILL.md.template`(Jinja2) 사용이 안내된다. 정식 위치는 `skills/cli-anything-<software>/SKILL.md`, 호환용 사본은 `cli_anything/<software>/skills/SKILL.md`이고 `setup.py`에 `package_data={"cli_anything.<software>": ["skills/*.md"]}`를 넣어 pip과 함께 배포한다. 하니스가 preview를 지원하면 producer(`cli-anything-<software> preview ...`)와 consumer(`cli-hub previews ...`)를 `README.md`와 `SKILL.md`에 따로 쓰고, live preview면 `preview live status --json`의 반환과 쓰임을 설명한다. 생성기 동작 상세는 skill-packaging이 맡는다. | 코드 확인 |
| R-16 | Phase 7 | `setup.py`는 `find_namespace_packages(include=["cli_anything.*"])`(`find_packages` 금지)를 쓰고 패키지명 `cli-anything-<software>`, `console_scripts` 항목 `cli-anything-<software>=cli_anything.<software>.<software>_cli:main`, `python_requires=">=3.10"`을 둔다(C-10). 시스템 패키지(LibreOffice, Blender 등)는 `install_requires`로 표현할 수 없으므로 `README.md`에 적고 백엔드 모듈이 설치 안내가 든 `RuntimeError`를 내게 한다. 검증: `pip install -e .`, `which cli-anything-<software>`와 `--help`, `CLI_ANYTHING_FORCE_INSTALLED=1`로 pytest(출력에 `[_resolve_cli] Using installed command: ...`가 보여야 한다). 단계 제목은 "PyPI Publishing"이지만 문서가 요구하는 동작은 로컬 설치와 검증까지이고 PyPI 업로드 단계는 없다. | 코드 확인 |
| R-17 | 패키지를 배치한다 | `cli_anything/` 디렉터리에는 `__init__.py`를 두지 않는다(PEP 420 namespace). 그 아래 `<software>/` 하위 패키지에는 둔다. 이유로 문서가 드는 것은 여러 PyPI 패키지가 같은 `cli_anything` namespace에 하위 패키지를 따로 설치해 공존하게 하는 것이다. 문서는 이것을 "Critical"로 표시하고 `validate`가 점검한다. | 코드 확인 |
| R-18 | 렌더링·export 구현 | 실제 소프트웨어를 하드 의존성으로 두고 렌더링·export에서 반드시 그 앱(LibreOffice `--headless`, `blender --background`, `gimp -i -b`, `inkscape --actions`, `melt`, `sox`, `obs-websocket` 등)을 호출한다. Python으로 재구현(예: Pillow 합성기로 GIMP 대체)하지 않는다. 대체 라이브러리로 우아하게 강등(graceful degrade)하지 않는다. 소프트웨어가 없으면 설치 안내와 함께 오류를 낸다. 네이티브 포맷을 직접 파싱·수정해 데이터 계층으로 쓰고, 유효한 중간 파일을 만든 뒤 실제 앱에 넘긴다. 문서는 이 규칙을 "#1 rule"이라 부른다. | 코드 확인 |
| R-19 | 효과(filter)를 가진 하니스 | 프로젝트 파일에 효과를 넣어도 단순 도구(예: ffmpeg concat demuxer)로 렌더링하면 효과가 조용히 무시된다("Rendering Gap", "#2 pitfall"). 렌더링 우선순위는 네이티브 엔진(예: `melt`) → 변환된 filtergraph(예: MLT 필터를 ffmpeg `-filter_complex`로) → 사용자가 직접 실행할 렌더 스크립트다. registry의 모든 filter/effect는 대응하는 렌더 매핑이 있거나 "project-only (not rendered)"로 명시해야 한다. 변환 매핑이 없는 효과는 crash하지 않고 경고 후 건너뛴다. 영상·오디오 하니스는 `filter-translation.md`, `timecode-precision.md`를 읽는다. | 코드 확인 |
| R-20 | CLI 설계 | 짧은 규칙 목록은 C-04가 원본이다. 요지: 모든 명령은 `--json`을 지원해야 하고(MUST), REPL이 기본 동작이어야 하고(MUST), 오류는 명확하게 즉시 실패해야 하고, 가능하면 멱등이어야 하고, `info`·`list`·`status` 같은 introspection 명령을 둔다. | 코드 확인 |
| R-21 | 문서·구조 | 모든 `cli_anything/<software>/` 디렉터리에 설치·실행·테스트·기본 사용법을 담은 `README.md`, 모든 `tests/`에 커버리지·워크플로·전체 결과를 담은 `TEST.md`가 있어야 한다(MUST). 규칙 전체는 "non-negotiable, every harness MUST follow all of them"으로 선언된다(C-04). 디렉터리 트리 자체는 harness-contract. | 코드 확인 |
| R-22 | 하니스가 중간 시각·검사 상태를 노출한다 | preview 지원은 선택이지만, 노출하면 일관된 계약을 따라야 한다(MUST). `preview recipes`·`capture`·`latest`를 둔다(SHOULD), diff 도구는 `preview diff`도 둔다(SHOULD). producer는 `cli-anything-<software> preview ...`(실제 백엔드, bundle·session·trajectory 생성), consumer는 `cli-hub previews ...`(읽기 전용 inspect/html/watch/open, 렌더링 금지)로 역할을 분리하고, consumer를 렌더 경로로 제시하지 않는다. 출력은 `preview-bundle/v1`, 모든 preview 명령은 `--json`을 지원한다(MUST). GUI 창 screen-scrape와 Python 가짜 렌더는 금지다. 상세는 C-05. | 코드 확인 |
| R-23 | 앱에 네이티브 CLI가 없고 MCP 서버가 있다 | MCP backend 패턴을 쓴다: `utils/<service>_backend.py`가 `mcp` SDK 클라이언트로 MCP 서버를 호출하고, 기본은 명령마다 서버를 새로 띄우며 CLI가 URL·작업 디렉터리 같은 상태를 유지한다. daemon 모드는 선택이다. `install_requires`에 `mcp>=0.1.0`을 넣는다. 예: `browser/agent-harness`(DOMShell). | 코드 확인 |

제작 명령

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-24 | `/cli-anything` 완료 판정 | 다음 11개를 모두 만족하면 성공이다(C-06): 모든 core 모듈이 구현·동작, one-shot과 REPL 모두 지원, 모든 명령이 `--json` 지원, 테스트 100% 통과, subprocess 테스트가 `_resolve_cli()`를 쓰고 `CLI_ANYTHING_FORCE_INSTALLED=1`에서 통과, `TEST.md`에 계획과 결과, `README.md`에 설치·사용법, 올바른 frontmatter와 명령 문서가 있는 `SKILL.md`, `setup.py`와 로컬 설치 성공, PATH에서 `cli-anything-<software>` 사용 가능, session 기반 CLI는 auto-save + `--dry-run`. 기준을 못 채웠을 때의 재시도·중단 규칙은 문서에 없다(U-04). | 코드 확인 |
| R-25 | `/cli-anything:refine <software-path> [focus]` | 이미 build된 하니스에만 쓴다. 로컬 경로만 받는다(URL이면 먼저 `/cli-anything`으로 clone). 6단계: (1) 현재 커버리지 목록 작성(CLI 진입점·core 모듈·테스트를 읽고 `{function: covered | not_covered}` 지도 생성), (2) 소프트웨어 능력 분석(공개 API·CLI·스크립팅·batch 연산, 관찰 가능한 출력이 있는 함수 위주), (3) gap 분석(영향 큼, 쉬운 승리, 조합 가능성 순)과 gap 보고서를 사용자에게 제시해 처리할 gap을 확인받음, (4) 선택한 gap의 명령·core 함수 구현(기존 패턴: Click group, `--json`, 세션 통합, `handle_error`), (5) 새 함수마다 unit, 새 명령마다 E2E, 새 명령과 기존 명령을 묶은 워크플로 테스트를 추가하고 기존+신규를 모두 돌려 회귀 확인, (6) `README.md`·`TEST.md`·`<SOFTWARE>.md` 갱신. `focus`가 있으면 2·3단계를 그 영역으로 좁히되 구현 전 결과를 제시하는 것은 유지한다. 기존 명령은 삭제하지 않고 추가·개선만 한다. 반복 실행하며 한 번에 응집된 기능군 하나만 다룬다. 성공 기준: 기존 테스트 통과(무회귀), 신규 테스트 100% 통과, 새 명령이 같은 패턴을 따름, 커버리지가 실제로 늘었음, 문서 갱신. | 코드 확인 |
| R-26 | `/cli-anything:test <software-path-or-repo>` | 하니스를 `/root/cli-anything/<software-name>/agent-harness/`에서 찾고(경로가 고정 문자열로 적혀 있음, U-02), `pytest -v -s --tb=short`로 실행하고, 출력을 저장하고, 출력에 `[_resolve_cli] Using installed command:`가 나오는지 확인하고, `TEST.md`의 `## Test Results`에 `Last run: <시각>`, `pytest -v --tb=no` 전체 출력, `**Summary**: N passed in Xs`를 덧붙이고, 통과·실패 요약을 보고한다. 테스트가 실패하면 실패한 테스트를 보이고, `TEST.md`를 갱신하지 않으며(이전 통과 결과 유지), 오류 메시지 기반 수정안을 제시하고, 수정 뒤 재실행을 제안한다. `[_resolve_cli]` 줄이 없을 때의 처리는 문서에 없다(U-05). | 코드 확인 |
| R-27 | `/cli-anything:validate <software-path-or-repo>` | 하니스를 `/root/cli-anything/<software-name>/agent-harness/`에서 찾아 8개 범주를 `HARNESS.md` 기준으로 점검하고 범주별 통과 개수와 `Overall: PASS (52/52 checks)` 형식의 보고서를 낸다(C-07). 범주: 디렉터리 구조, 필수 파일, CLI 구현 표준, core 모듈 표준, 테스트 표준, 문서 표준, PyPI 패키징 표준, 코드 품질. 점검 항목에 SKILL.md 존재·형식, preview, auto-save/`--dry-run`, `ReplSkin` 사용은 들어 있지 않다(D-10). FAIL 조건과 파일 수정 여부는 U-03. | 코드 확인 |
| R-28 | `/cli-anything:list [--path] [--depth] [--json]` | 설치된 하니스: `importlib.metadata.distributions()`에서 패키지명이 `cli-anything-`로 시작하는 것을 모아 software 이름·버전·`shutil.which("cli-anything-<software>")` 실행 파일을 얻고 status `installed`(C-08). 생성된 하니스: `<path>/**/agent-harness/cli_anything/*/__init__.py` glob(`--depth n`이면 깊이 0..n 패턴을 각각 만든다)에서 software 이름·`setup.py`의 `version` 정규식·source 경로를 얻고 status `generated`(C-09). 합치기: software 이름으로 중복 제거, 둘 다 있으면 `installed`로 표시하고 source 경로는 generated 것을 유지한다. 출력은 표(기본) 또는 `--json`. 오류: 하나도 없으면 "No CLI-Anything tools found", 잘못된 `--path`는 "Path not found: <path>", 권한 거부는 그 디렉터리를 건너뛰고 경고하며 계속한다. `HARNESS.md`를 읽지 않고 stdlib만 쓴다. | 코드 확인 |
| R-29 | 이 문서들을 Claude Code에서 쓴다 | 플러그인 이름 `cli-anything`(`plugin.json`: `name`, `description`, `author`만 있고 명령 목록이 없다), 루트 `.claude-plugin/marketplace.json`이 `source: "./cli-anything-plugin"`으로 가리킨다. 명령은 `commands/*.md` 파일에서 오고 파일명이 명령명이 된다는 것은 Claude Code의 플러그인 규약에 대한 추론이다. `verify-plugin.sh`는 필수 파일로 `plugin.json`, `README.md`, `LICENSE`, `PUBLISHING.md`, 4개 명령 파일(`list.md` 제외), `scripts/setup-cli-anything.sh`의 존재와 실행 권한을 확인한다. | 추론(명령 발견 방식), 코드 확인(나머지) |

- 불변식: 제작 명령 4종(build, refine, test, validate)은 `HARNESS.md`를 규칙의 기준으로 삼는다. `validate.md:7`은 "single source of truth for all validation checks", `refine.md:7`은 "single source of truth for architecture, patterns, and quality requirements"라고 쓴다. 명령 문서와 `HARNESS.md`가 충돌할 때 어느 쪽이 이기는지는 문서에 없다. 이 불변식은 `HARNESS.md`에 없는 규칙(Phase 0, auto-save, `validate`의 필수 파일 목록)에는 성립하지 않는다.
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-01 | 명령 문서의 `./HARNESS.md`는 어떤 기준 경로인가? 명령 파일은 `commands/`에 있고 `HARNESS.md`는 플러그인 루트에 있다. 설치 안내는 `~/.claude/plugins/cli-anything/HARNESS.md`(`README.md:47`), `setup-cli-anything.sh`는 `/root/cli-anything/HARNESS.md`(`:38`)를 가리킨다 | 구현자가 `HARNESS.md`를 어디서 읽게 할지 정해야 한다 | Claude Code가 플러그인 명령의 상대 경로를 해석하는 방식(외부 시스템)을 확인 |
| U-02 | R-03, R-26, R-27 | 앱 이름만 준 경우 에이전트가 무엇을 하는가(거절 문구·되묻기)? clone 위치와 `<software-name>/agent-harness/`의 기준 디렉터리는 어디인가? `test`·`validate`는 `/root/cli-anything/...` 고정 경로를 쓰는데 build의 출력 위치(`cli-anything.md:89-94`는 상대 표기)와 같은가? | 입력 검증 동작과 하니스 위치 규칙을 구현자가 정해야 한다 | 에이전트 실행 기록이 없어 문서만으로는 닫히지 않음. 실제 build를 한 번 실행해 출력 위치를 관찰해야 함 |
| U-03 | R-27 | `validate`의 FAIL 조건(항목 하나라도 실패? 임계값?), 점검 방법(grep? AST? 실행?), 파일을 수정하는지(읽기 전용인지), 위반 시 보고 형식은? 예시 보고서는 전부 통과한 경우만 보여 준다 | 점검 결과 형식과 종료 동작을 구현자가 정해야 한다 | `validate`를 위반이 있는 하니스(예: `__init__.py`가 있는 chromadb)에 실행해 보고서를 보는 방법. 이번 범위에서는 미실행 |
| U-04 | R-24 | build 도중 테스트가 실패하거나 성공 기준을 못 채우면 에이전트가 고쳐서 다시 도는가, 중단하고 보고하는가? | 제작 루프의 종료 조건을 구현자가 정해야 한다 | 문서에 규정 없음. 실행 기록 필요 |
| U-05 | R-26 | 출력에 `[_resolve_cli] Using installed command:` 줄이 없으면(모듈 fallback 사용) `test`는 실패 처리하는가, 경고인가? 설치(`pip install -e .`)는 누가 하는가? | `test` 판정 규칙을 구현자가 정해야 한다 | 문서에 규정 없음. 실행 기록 필요 |

- 확인 한계: 에이전트가 이 문서를 실제로 따랐을 때의 행동(Phase를 건너뛰는지, 거절 문구, 자동 재시도)은 실행하지 않았고 문서에서 확인할 수 없다. 슬래시 명령이 `commands/*.md`에서 등록되는 방식은 Claude Code의 동작이고 이 레포 코드가 아니다(R-29는 `추론`). 2.1의 하니스 69개 수치는 문자열 검색이라 구현 방식이 다르면 놓친다. CI 워크플로 본문과 `tests/`는 열지 않았다.

### 1.5 필수 코드 참조

라이선스: Apache License 2.0(`LICENSE`, `cli-anything-plugin/LICENSE`). 인용 허용 여부는 overview 1절을 따른다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `cli-anything-plugin/HARNESS.md:168-183` `_resolve_cli` | 설치된 명령을 PATH에서 찾고, `CLI_ANYTHING_FORCE_INSTALLED=1`이면 못 찾을 때 `RuntimeError`, 아니면 `python -m` 모듈로 fallback하며 `[_resolve_cli]` 줄을 출력하는 helper. fallback 모듈 문자열 조립은 하이픈이 든 software 이름에서 틀린다(D-11). | R-12, R-16 |
| C-02 | `cli-anything-plugin/guides/session-locking.md:14-37` `_locked_save_json` | `"r+"` 열기 → `fcntl.flock(LOCK_EX)` → 락 안에서 `seek(0)`·`truncate()`·`json.dump`·`flush` → 락 해제. 파일이 없으면 `makedirs` 후 `"w"`. `fcntl` 없거나 `OSError`면 락 없이 진행. | R-07 |
| C-03 | `cli-anything-plugin/guides/auto-save-dry-run.md:16-43` `cli`, `auto_save_on_exit` | 메인 group의 `--dry-run` 옵션과 `result_callback`의 조건(REPL이면 건너뜀, dry-run이면 건너뜀, `sess.has_project() and sess._modified and sess.project_path`이면 `save_session()`, 예외는 stderr 경고). `_repl_mode`는 REPL 실행 중 true가 되는 모듈 전역 bool이고, `get_session()`은 프로세스 전역 `Session`을 돌려주며 `Session`은 `has_project()`, `_modified`, `project_path`, `save_session()`을 가진다(상세는 harness-contract). | R-08 |
| C-04 | `cli-anything-plugin/HARNESS.md:480-551` Principles & Rules | Backend & Rendering, CLI Design, Testing, Documentation 규칙 전체 목록(`--json` MUST, REPL 기본 MUST, 모든 export는 프로그램 검증 MUST, subprocess E2E MUST 등). | R-18, R-19, R-20, R-21 |
| C-05 | `cli-anything-plugin/HARNESS.md:553-670` Preview & Live Preview Norms | producer/consumer 분리, bundle·session·trajectory 3계층, 권장 명령 표면, `preview live status --json` 반환 항목, truthfulness 원칙. | R-22 |
| C-06 | `cli-anything-plugin/commands/cli-anything.md:134-147` Success Criteria | build 성공 기준 11개 목록. | R-24 |
| C-07 | `cli-anything-plugin/commands/validate.md:25-113` What This Command Validates, Validation Report | 8개 범주의 점검 항목과 보고서 형식. | R-27 |
| C-08 | `cli-anything-plugin/commands/list.md:27-43` 설치 스캔 | `importlib.metadata.distributions()`로 `cli-anything-` 접두 패키지를 찾고 이름·버전·실행 파일 경로를 얻는 코드. | R-28 |
| C-09 | `cli-anything-plugin/commands/list.md:61-115` `extract_version_from_setup`, `build_glob_patterns` | 깊이 제한별 glob 패턴 생성과 `cli_anything/<software>` 추출, `setup.py` 버전 정규식(`version\s*=\s*["']([^"']+)["']`). | R-28 |
| C-10 | `cli-anything-plugin/guides/pypi-publishing.md:31-50` `setup.py` 템플릿 | `find_namespace_packages(include=["cli_anything.*"])`, `install_requires` 기본(`click>=8.0.0`, `prompt-toolkit>=3.0.0`), `console_scripts`, `python_requires=">=3.10"`. | R-16 |

### 1.6 수락 사례

출처: 모두 문서 문구에서 도출. 원본 테스트는 열람하지 않았다. 문서를 에이전트가 따랐는지가 아니라 문서가 요구하는 결과를 쓴 것이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03 | `/cli-anything gimp` (이름만) | 인자로 받지 않는다(처리 방식은 U-02). `/cli-anything /home/user/gimp`면 software 이름 `gimp`. |
| T-02 | R-08 | session 기반 하니스에서 `cli-anything-kdenlive --project p.json bin import video.mp4` (one-shot, `--dry-run` 없음) | 명령이 끝난 뒤 `p.json`에 변경이 저장된다. |
| T-03 | R-08 | 같은 명령에 `--dry-run` | 명령이 실행되고 출력은 나오지만 `p.json`은 바뀌지 않는다. |
| T-04 | R-08 | REPL 모드에서 변경 명령 (`--dry-run` 유무 무관) | 자동 저장하지 않는다. 사용자가 저장해야 한다. |
| T-05 | R-08 | one-shot 명령이 `handle_error`에서 `sys.exit(1)`로 끝남 | `result_callback`이 호출되지 않아 저장되지 않는다. |
| T-06 | R-07 | 존재하지 않는 경로에 `_locked_save_json` 호출 | 디렉터리를 만들고 `"w"`로 열어 JSON을 쓴다. 이미 있는 파일은 `"r+"`로 열려 락 안에서 truncate한다. |
| T-07 | R-12 | PATH에 `cli-anything-foo`가 없고 `CLI_ANYTHING_FORCE_INSTALLED=1` | `_resolve_cli`가 `RuntimeError("cli-anything-foo not found in PATH. Install with: pip install -e .")`를 던진다. 변수가 없으면 `python -m cli_anything.foo.foo_cli`로 fallback하고 `[_resolve_cli] Falling back to: ...`를 출력한다. |
| T-08 | R-26 | `/cli-anything:test /home/user/gimp`에서 테스트 1개 실패 | 실패 테스트를 보여 주고, `TEST.md`는 이전 내용 그대로, 수정안 제시, 재실행 제안. |
| T-09 | R-25 | `/cli-anything:refine https://github.com/GNOME/gimp` | 로컬 경로만 받으므로 입력으로 받지 않는다(안내 방식은 문서에 없음). 먼저 `/cli-anything`으로 clone해야 한다. |
| T-10 | R-28 | `/cli-anything:list --depth 0` | `<path>/agent-harness/cli_anything/*/__init__.py` 한 패턴만 검색한다. `--depth 2`면 깊이 0, 1, 2 패턴을 모두 검색한다. |
| T-11 | R-28 | gimp가 설치돼 있고 `./gimp/agent-harness`도 있음 | 항목 하나, status `installed`, `source`는 `./gimp/agent-harness`. `total`·`installed`는 1, `generated_only`는 0. |
| T-12 | R-28 | `--path /nope` | "Path not found: /nope" 오류. |
| T-13 | R-17, R-27 | 하니스에 `agent-harness/cli_anything/__init__.py`가 있음 | `validate`의 디렉터리 구조 범주 중 "`cli_anything/` has NO `__init__.py`" 항목이 걸린다(보고 형식은 U-03). |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@34f5195 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `cli-anything-plugin/commands/cli-anything.md:5-7`, `cli-anything-plugin/commands/refine.md:5-7`, `cli-anything-plugin/commands/test.md:5-7`, `cli-anything-plugin/commands/validate.md:5-7`. `list.md`에는 요구 없음: `grep -c HARNESS cli-anything-plugin/commands/list.md` → 0 | "list에 없다"는 이 명령 하나의 `HARNESS` 문자열 검색 결과다. 다른 문서가 list에 읽기를 요구하는지는 이 범위에서 보지 않았다. |
| R-02 | `cli-anything-plugin/HARNESS.md:12,25,49,111,142,219,232,294` (Phase 제목), `cli-anything-plugin/commands/cli-anything.md:25-85` | `grep -n "### Phase" HARNESS.md`로 8개 Phase 제목 확인(Phase 0 없음). 명령 문서의 Phase 0은 `cli-anything.md:29-32`. |
| R-03 | `cli-anything-plugin/commands/cli-anything.md:11-32` | 문서 문구만. 거절 시 동작은 문서에 없다. |
| R-04 | `cli-anything-plugin/HARNESS.md:12-47`, `cli-anything-plugin/commands/cli-anything.md:34-44` | `<SOFTWARE>.md` 요구는 `cli-anything.md:44`와 `HARNESS.md:677`(디렉터리 구조)에만 있고 `HARNESS.md` Phase 2 본문(25-47)에는 없다. |
| R-05 | `cli-anything-plugin/HARNESS.md:49-68`, `cli-anything-plugin/commands/cli-anything.md:46-51` | 백엔드 모듈 예시는 LibreOffice `lo_backend.py`(`HARNESS.md:59-66`). |
| R-06 | `cli-anything-plugin/HARNESS.md:74-109` | `ReplSkin` 배너 경로 동작은 문서 설명이고 `repl_skin.py`는 읽지 않았다(harness-contract 몫). |
| R-07 | C-02, `cli-anything-plugin/HARNESS.md:69-73` | 락 코드는 문서의 코드 블록을 읽었고 실행하지 않았다. Windows에서 락이 없어진다는 점은 `session-locking.md:27-28`의 주석("Windows / unsupported FS — proceed unlocked")이 근거다. |
| R-08 | C-03, `cli-anything-plugin/guides/auto-save-dry-run.md:45-87`, `cli-anything-plugin/commands/cli-anything.md:128-132,147` | 예시 구현은 `gimp/agent-harness/cli_anything/gimp/gimp_cli.py:142-153`에서 같은 형태로 확인(`result_callback`, `_repl_mode`, `dry_run`). `HARNESS.md`는 이 규칙을 언급하지 않는다(`grep -n -i -E "dry\|auto-save" HARNESS.md` 0건). |
| R-09 | `cli-anything-plugin/HARNESS.md:111-140` | |
| R-10 | `cli-anything-plugin/HARNESS.md:142-217,406-478` | "round-trip", "agent test"는 `HARNESS.md:216-217` 목록 항목이고 `cli-anything.md:136-147`의 성공 기준에 없다("없다"는 이 한 문서 범위). |
| R-11 | `cli-anything-plugin/HARNESS.md:150-156,415-428,535-545` | |
| R-12 | C-01, `cli-anything-plugin/HARNESS.md:164-214,463-468`, `cli-anything-plugin/commands/cli-anything.md:64-65` | |
| R-13 | `cli-anything-plugin/HARNESS.md:157-163,388-404,539-540` | |
| R-14 | `cli-anything-plugin/HARNESS.md:219-230`, `cli-anything-plugin/commands/cli-anything.md:67-70` | |
| R-15 | `cli-anything-plugin/HARNESS.md:232-292`, `cli-anything-plugin/guides/skill-generation.md:34-135`, `cli-anything-plugin/commands/cli-anything.md:72-77` | 생성기가 정식·호환 두 위치에 쓰는 것은 `cli-anything-plugin/skill_generator.py:554-568` `generate_skill_file`에서 확인했다. 그 이상은 skill-packaging. |
| R-16 | `cli-anything-plugin/HARNESS.md:294-303`, `cli-anything-plugin/guides/pypi-publishing.md:27-109`, `cli-anything-plugin/commands/cli-anything.md:79-85` | "업로드 단계 없음": `grep -n -i -E "publish\|twine\|upload" cli-anything-plugin/guides/pypi-publishing.md cli-anything-plugin/commands/cli-anything.md` 결과가 제목 줄뿐이고, `grep -n -i -E "twine\|pypi" cli-anything-plugin/HARNESS.md`도 단계 제목과 구조 주석뿐이다. 이 3개 파일 범위이며 `PUBLISHING.md`는 읽지 않았다(플러그인 배포 문서로 추정). |
| R-17 | `cli-anything-plugin/HARNESS.md:302-303,702-707`, `cli-anything-plugin/guides/pypi-publishing.md:23-25`, `cli-anything-plugin/commands/validate.md:29-30,82` | 레포 상태는 D-01. |
| R-18 | `cli-anything-plugin/HARNESS.md:307-346,485-488,726-732` | 레포 상태는 D-02. |
| R-19 | `cli-anything-plugin/HARNESS.md:348-366,495-496`, `cli-anything-plugin/guides/filter-translation.md:24-26` | 문서 내부 긴장은 D-14. |
| R-20 | C-04 (`HARNESS.md:498-532`) | 레포 상태는 D-08. |
| R-21 | C-04 (`HARNESS.md:547-551`), `cli-anything-plugin/HARNESS.md:672-709` | 레포 상태는 D-05. |
| R-22 | C-05, `cli-anything-plugin/HARNESS.md:503-528` | `guides/preview-methodology.md`는 첫 40줄만 읽었다(범위 밖 행 6). |
| R-23 | `cli-anything-plugin/HARNESS.md:368-374`, `cli-anything-plugin/guides/mcp-backend.md:5-12,45-59` | |
| R-24 | C-06 | |
| R-25 | `cli-anything-plugin/commands/refine.md:3-104` | "삭제하지 않는다"는 `refine.md:104`. 사용자 확인 시점은 `:56`("confirm which gaps")과 `:103`("should present") 둘이라 강도 표현이 다르다. |
| R-26 | `cli-anything-plugin/commands/test.md:3-73` | 고정 경로 `test.md:23`. |
| R-27 | C-07 | 점검 항목 수 합 5+9+7+5+10+4+7+5=52(`validate.md:103-112`)가 예시 총점과 같다. |
| R-28 | C-08, C-09, `cli-anything-plugin/commands/list.md:117-237` | 코드 블록은 설명용 예시이고, 에이전트가 그대로 실행하는지는 U 범위 밖이다. 미실행. |
| R-29 | `cli-anything-plugin/.claude-plugin/plugin.json:1-7`, `.claude-plugin/marketplace.json:1-20`, `cli-anything-plugin/verify-plugin.sh:20-28`, `cli-anything-plugin/README.md:84-122` | 명령 자동 발견은 Claude Code 동작이라 웹 확인을 하지 않았고 `추론`이다. |
| T-01~T-13 | 각 관련 R-ID의 근거 | 문서 문구에서 도출. 실행하지 않았다. |

**문서와 실제 상태의 차이** (규칙 문구 대 레포 상태. 하니스 목록은 `git ls-files | grep -E '^[^/]+/agent-harness/' | cut -d/ -f1 | sort -u` → 69개. 아래 수치는 이 목록에 `git ls-files`·`git grep` 문자열 검색을 한 결과이며, 이 SHA의 작업트리는 clean이다.)

| 차이 | 관련 R-ID | 확인 내용 | 한계 |
|---|---|---|---|
| D-01 | R-17 | `git ls-files \| grep -E '^[^/]+/agent-harness/cli_anything/__init__.py'`가 8개를 반환: chromadb, comfyui, godot, intelwatch, obsidian, pm2, seaclip, videocaptioner. 8개 모두 0바이트이고 `setup.py`가 `find_namespace_packages(include=["cli_anything.*"])`를 쓴다(`grep` 확인). 나머지 61개 중 Python 패키지가 있는 하니스에는 이 파일이 없다(`sketch`는 Node 하니스라 `cli_anything/`가 없다). | namespace 공존이 실제로 깨지는지는 pip 설치를 하지 않아 미확인. 파일이 있어도 한 환경에 8개를 같이 설치했을 때만 문제가 드러날 수 있다(추론). |
| D-02 | R-18 | gimp: `gimp/agent-harness/cli_anything/gimp/core/export.py:54-84` `render`가 `is_available() and not _project_has_draw_ops(project)`일 때만 GIMP를 쓰고, 아니면(또는 GIMP 쪽 예외를 `except Exception: pass`로 삼키면) `_render_via_pillow`로 간다(`:87-103`은 Pillow도 없을 때만 `RuntimeError`). `_project_has_draw_ops`는 `:311`. `skills/cli-anything-gimp/SKILL.md:19-23`은 "GIMP가 없어도 Pillow 경로로 렌더"하고 `:211`은 draw 연산이 있으면 GIMP가 있어도 Pillow 경로가 기본이라고 적는다. `gimp/agent-harness/setup.py:36-50`에서 Pillow는 `install_requires`가 아닌 `extras_require["pillow"]`이고, `GIMP.md:36-45`는 Pillow를 "primary engine"이라 부른다. drawio도 `drawio/agent-harness/cli_anything/drawio/core/export.py:111-127` `render_or_save`가 draw.io CLI가 없으면 오류 대신 `.drawio` 파일만 저장하고 수동 export 안내를 반환한다. 즉 R-18의 "대체 라이브러리로 강등 금지, 없으면 오류"는 최소 gimp와 drawio에서 지켜지지 않는다. | `core/export.py`·`*_backend.py`에서 `fallback\|falls back`를 검색해 이 문자열이 있는 하니스는 browser, drawio, exa, freecad, gimp, joplin, libreoffice, lldb, shotcut, tigris 10개다. 그중 libreoffice는 같은 앱의 다른 호출 방식(macOS `open -W -n -a`)이라 위반이 아니고, shotcut은 `HARNESS.md:361-364`가 허용한 변환 계층일 수 있다(나머지는 열지 않음). 전체 위반 수는 미확인. |
| D-03 | R-11 | `freecad/agent-harness/cli_anything/freecad/tests/test_full_e2e.py:539`가 `@pytest.mark.skipif(not _has_freecad(), reason="FreeCAD not installed")`로 실제 백엔드 테스트 클래스를 skip한다. "소프트웨어가 없으면 skip이 아니라 실패"(`HARNESS.md:156,426-428`)와 반대다. `git grep -E 'pytest\.skip\|skipif\|unittest\.skip\|importorskip' -- ':(glob)<sw>/agent-harness/**/tests/*.py'`가 하니스 69개 중 43개에서 걸린다. | 걸린 43개의 skip 사유가 모두 소프트웨어 부재는 아니다(예: inkscape는 `inkscape/agent-harness/cli_anything/inkscape/tests/test_full_e2e.py:370`에서 "Pillow not installed"로 skip). 사유별 분류는 하지 않았다. |
| D-04 | R-12, R-24 | 같은 방식의 `tests/*.py` 문자열 검색: `_resolve_cli` 43/69, `CLI_ANYTHING_FORCE_INSTALLED` 38/69, `class TestCLISubprocess` 34/69. `validate.md:66-68`은 이 세 가지를 점검 항목으로 둔다. | 클래스·헬퍼 이름이 다르게 쓰인 subprocess 테스트는 놓친다. 또한 69개가 모두 Python/pytest인 것은 아니다(`sketch`는 `tests/*.test.js`). |
| D-05 | R-21, R-27 | 파일 존재(경로 `^<sw>/agent-harness/cli_anything/[^/]+/<파일>$`): `tests/TEST.md` 54/69, `README.md` 64/69, `tests/test_core.py` 66/69, `tests/test_full_e2e.py` 63/69, `utils/repl_skin.py` 62/69. `validate.md:37-39`의 필수 파일 `core/project.py` 23/69, `core/session.py` 40/69, `core/export.py` 21/69. `agent-harness/` 바로 아래 `<SOFTWARE>.md`형 파일(README 제외 `*.md`)은 63/69이고 없는 곳은 comfyui, firefly-iii, n8n, novita, sketch, zoom. 즉 `validate`의 "Required Files" 9개 목록은 레포의 하니스 대부분이 충족하지 않는다. | 파일 이름만 센 것이다. 같은 역할을 다른 이름으로 구현한 경우를 가려내지 못한다(예: blender, inkscape, libreoffice는 `core/project.py`가 없다). |
| D-06 | R-16 | `setup.py`에 `find_namespace_packages`가 있는 하니스는 67/69. 없는 2개: `sketch`(Node 하니스: `package.json`, `src/cli.js`, Python 패키지 없음)와 `unimol_tools`(`pyproject.toml`, `setup.py` 없음). 즉 Phase 7의 `setup.py` 전제는 Python 하니스에 한정된다. 단계 제목의 "PyPI Publishing"과 달리 업로드 절차는 SOP에 없다(R-16 근거). | `unimol_tools/pyproject.toml`의 설정 내용은 열지 않았다. |
| D-07 | R-08 | `--dry-run`/`dry_run` 문자열(`cli_anything/**/*.py`, `dry.run`)이 있는 하니스 23/69. 이 규칙은 `cli-anything.md:128-132,147`과 가이드에만 있고 `HARNESS.md`에는 없으며(`grep` 0건) `validate.md`의 점검 항목에도 없다. 69개 중 몇 개가 "session 기반"이라 적용 대상인지는 가리지 못했다. | 위반 수가 아니라 "구현 흔적이 있는 수"다. |
| D-08 | R-20 | 문자열 검색(`cli_anything/**/*.py`): `--json` 65/69, `invoke_without_command` 64/69, `ReplSkin` 62/69. `validate.md:49-50`의 점검 항목 `--project` 26/69(`\-\-project` 포함), `def handle_error` 36/69. 규칙은 "Every command MUST support `--json`"(`HARNESS.md:529`), "REPL MUST be the default"(`:531-532`)다. overview의 65/64/62 수치와 같은 값으로 다시 확인했다. | 문자열 검색이라 구현 방식이 다르면 놓친다(overview와 같은 한계). 69개에 Node 하니스 `sketch`가 있다. |
| D-09 | R-26, R-27 | 명령 문서끼리 어긋난다. `test.md:28`은 `pytest -v -s --tb=short`로 실행하라 하고 `test.md:44`·`HARNESS.md:224`는 `-v --tb=no` 출력을 기록하라 한다. `test.md:23`, `validate.md:23`은 `/root/cli-anything/<software-name>/agent-harness/`를 고정하지만 `cli-anything.md:89-94`의 출력 위치는 `<software-name>/agent-harness/` 상대 표기이고, 플러그인 `README.md:47`은 플러그인 위치를 `~/.claude/plugins/cli-anything/`로 안내한다. `cli-anything-plugin/scripts/setup-cli-anything.sh:38`은 `/root/cli-anything/HARNESS.md`를 확인한다. `verify-plugin.sh:20-28`의 필수 파일에 `commands/list.md`는 없다. | 문서 간 비교이고 실행하지 않았다(U-01, U-02). |
| D-10 | R-27 | `validate.md`에는 SKILL.md 존재·형식, preview, auto-save/`--dry-run`, `ReplSkin` 점검이 없다: `grep -n -i -E "skill\|dry\|preview\|auto-save\|repl_skin\|ReplSkin" cli-anything-plugin/commands/validate.md cli-anything-plugin/commands/test.md cli-anything-plugin/commands/refine.md` → 0건. 반면 `HARNESS.md:232-292`(Phase 6.5)와 `cli-anything.md:128-147`(성공 기준 8, 11번)은 이를 요구한다. 레포 전체 하니스를 SOP에 맞춰 검사하는 CI는 보지 못했다: `ls .github/workflows`에 하니스 구조 검사로 보이는 이름이 없다(check-codex-skill, check-cursor-plugin, check-root-skills, deploy-pages, pr-labeler-tests, pr-labeler, publish-cli-hub). | 워크플로 본문은 열지 않았고 `check-root-skills`는 `SKILL.md` 동기화를 본다(skill-packaging 범위). 파일명 기준 판단이다. |
| D-11 | R-12 | C-01의 fallback 모듈 문자열은 `name.replace("cli-anything-", "cli_anything.") + "." + name.split("-")[-1] + "_cli"`다(`HARNESS.md:181`). `cli-anything-cc-switch`면 `cli_anything.cc-switch.switch_cli`가 되어 유효한 Python 모듈 경로가 아니다. `gimp`처럼 하이픈이 없는 이름에서만 맞다. | 코드 블록을 읽고 계산했다. 실행하지 않았다. 레포의 cc-switch 하니스 테스트가 이 helper를 그대로 쓰는지는 보지 않았다. |
| D-12 | R-28 | `list.md:33`의 설치 탐색은 패키지명 접두사 `cli-anything-`만 본다. `cli-hub/setup.py:52`의 패키지명은 `cli-anything-hub`이므로 이 규칙대로면 `hub`라는 하니스로 잡힌다(추론: 명령은 에이전트가 해석하는 산문이라 이 코드 블록을 그대로 실행하는지는 확인 불가). 같은 문서의 코드 예시 `list.md:67`은 bare `except:`를 쓰는데 `validate.md:92`는 bare `except:` 금지를 점검한다. | |
| D-13 | R-17, R-21 | 하니스 6개(browser, lldb, nsight-graphics, renderdoc, safari, shotcut)에 `agent-harness/HARNESS.md`가 있다. `validate.md:75`의 "No duplicate HARNESS.md"와 달리 플러그인 `HARNESS.md`와 바이트가 같은 것은 없다(`cmp`). lldb·nsight-graphics·renderdoc은 "<앱> CLI Harness Specification"으로 시작하는 하니스별 SOP이고 browser·safari는 MCP 연동 문서다. shotcut의 것은 플러그인 `HARNESS.md`와 같은 제목으로 시작하지만 238줄(플러그인은 747줄)이라 옛 사본으로 보인다(추론). | 내용은 첫 줄과 줄 수만 봤다. |
| D-14 | R-18, R-19 | 문서 내부 긴장: `HARNESS.md:361-364`는 렌더링 fallback으로 변환 계층과 사용자용 스크립트를 허용하고, `HARNESS.md:485-488`은 "gracefully degrade to a fallback library"를 금지한다. 둘을 조화시키는 문구는 없다. 읽는 방법으로는 앞의 fallback은 "실제 소프트웨어의 다른 도구(ffmpeg) 호출"이고 뒤는 "실제 소프트웨어를 안 쓰는 재구현"이라고 볼 수 있다(추론). 스크립트 생성은 어느 쪽에도 해당하지 않는다. | |

### 2.2 코드 읽는 순서

1. `cli-anything-plugin/commands/cli-anything.md` 전체(147줄)로 명령 형태와 Phase 0을 본다.
2. `cli-anything-plugin/HARNESS.md`를 Phase 1~7(12-303) → "Architecture Patterns & Pitfalls"(305-478) → "Principles & Rules"(480-551) 순으로 읽는다. 553-670은 preview 조건부 규범이다.
3. 나머지 명령 4개(`refine.md`, `test.md`, `validate.md`, `list.md`)는 각각 100~240줄이고 서로 독립이다.
4. `guides/`는 `HARNESS.md` 끝 표(739-747)가 Phase별로 가리키는 대로만 연다.
5. 규칙 대 현실은 `git ls-files | grep -E '^[^/]+/agent-harness/'`로 하니스 목록을 만든 뒤 D-01~D-13의 검색을 따른다.

### 2.3 비교·재사용 출처

같은 기능을 다른 레포에서 스펙으로 만든 것은 없다. 형제 스펙: harness-contract(CLI 표면·패키지 레이아웃), harness-families, skill-packaging(`reports/CLI-Anything/capabilities/skill-packaging.md`), registry-schema. 원본 코드 복사는 하지 않았다.

### 2.4 검토 기록

- 방식: 미점검(작성자 초안, `status: draft`)
- 대조한 R-ID: 없음
- 대조하지 않은 R-ID: 전부
- 재구현: 미수행

## 적용 메모

Claude Code에서 "앱 → CLI + skill" 생성 절차를 설계할 때 이 문서에서 가져가거나 바꿀 후보다. 원본의 미결정(U-01~U-05)을 여기서 해소한 것으로 치지 않는다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-01, R-26, R-27 | 하니스 위치와 `HARNESS.md` 위치를 고정 경로(`/root/cli-anything/...`)가 아니라 명령 인자·플러그인 변수로 받는다 | D-09처럼 문서마다 경로가 달라 구현이 흔들린다 | `test`/`validate`의 입력에 `--harness <dir>` 같은 인자를 추가하면 U-02 질문이 닫힌다 |
| R-11, R-18 | "실제 앱 필수, fallback 금지"를 지킬지 정책으로 먼저 정하고, 허용 fallback(예: gimp Pillow 경로)은 `SKILL.md` Prerequisites에 명시하게 한다 | D-02, D-03에서 규칙과 실제가 갈린다 | 규칙에 "허용 fallback 목록" 절을 두면 T-07류 테스트도 같이 바뀐다 |
| R-27 | `validate`에 SKILL.md, auto-save/`--dry-run`, `ReplSkin`, preview 점검을 추가하고 판정 기준(FAIL 조건)을 정한다 | D-10, U-03 | 보고서 범주가 8개에서 늘고 종료 코드 규칙이 필요하다 |
