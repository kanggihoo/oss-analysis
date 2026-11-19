# ppt-master 실행 trace: Step 1~3 (소스 → 프로젝트 → 템플릿 후보)

- 기준: `repos/ppt-master` `3af3e8e`, venv `repos/ppt-master/.venv`(Python 3.12.13, 패키지 목록 `00-pip-freeze.txt`)
- 실행 일자: 2026-11-19
- 입력: [`input/portfolio.md`](input/portfolio.md) (가상 백엔드 개발자 포트폴리오, 5개 절)
- 실행한 주체: 이 세션의 agent가 `SKILL.md`·`generate-pptx.md`를 읽고 명령을 직접 실행했다. 따라서 "스펙만으로 재현되는가"는 이 trace의 검증 범위가 아니다.

## 진입 (SKILL.md)

| 호출 | 필요한 것 | 결과 | 확인 |
|---|---|---|---|
| `python scripts/attribution_guard.py` | `SKILL_DIR` 절대경로, 인터프리터 | 종료 코드 0, 출력 없음 | 실행 확인 |
| `routing.md` 읽기 → 경로 선택 | 사용자 요청 문장 | Generate PPTX, ordinary Default(`generate-pptx.md`). Quick·Image to PPTX·Beautify 조건에 해당하지 않음 | 문서 읽기 (agent 판단) |

`SKILL.md`는 Windows에서 `python3`가 없으면 `python`으로 다시 실행하라고 적고 있다. 이 환경에서는 venv의 `python.exe`를 직접 썼다.

## Step 1. 소스 처리

- 입력이 Markdown이므로 워크플로 표의 "Markdown → Read directly"에 따라 `source_to_md.py`를 호출하지 않았다.
- 충분성 검사(`topic-research`)는 하지 않았다. 입력이 폐쇄 코퍼스이고 외부 사실 검증이 필요한 주장이 없다(가상 샘플임을 소스 첫 줄에 명시).
- 만들어진 파일: 없음.

## Step 2. 프로젝트 초기화

| 호출 | 출력 | 종료 |
|---|---|---|
| `project_manager.py init portfolio_demo` | `projects/portfolio_demo_20261119` 생성. "Canvas is determined during authoring and recorded in spec_lock.md" | 0 |
| `project_manager.py import-sources <project> input/portfolio.md` | `sources/portfolio.md` 생성. "Archived originals"와 "Normalized markdown"이 같은 파일을 가리킨다 | 0 |

- `--format`은 붙이지 않았다. 사용자·소스가 정확한 canvas를 정한 적이 없어서 Stage 1에서 확정한다(워크플로 "truthful canvas token" 규칙). 그래서 프로젝트 이름에 canvas가 없고 `_20261119`만 붙었다.
- `init` 직후 구조: `README.md`, `analysis/`, `exports/`, `icons/`, `images/`, `live_preview/`, `notes/`, `sources/`, `svg_final/`, `svg_output/`, `templates/`, `validation/workflow.log`. 전체 목록은 `02-tree-after-init.txt`, import 뒤 목록은 `02-tree-after-import.txt`.
- `import-sources` 뒤 바뀐 것은 `sources/portfolio.md` 한 개뿐이다. Markdown 입력은 변환 profile, `images/` 전파, `analysis/` 산출물이 생기지 않았다.
- `validation/workflow.log`: `init`은 `NOTE`(`profile=default`), `import-sources`는 `PYTHON` 항목(argv, cwd, stdout 일부, `elapsed_ms=608`)을 자동으로 남겼다. 스크립트가 직접 쓴 것이고 agent가 따로 쓰지 않았다.

## Step 3. 템플릿 후보 준비


이 단계에서 사용자에게 보이는 화면이나 질문은 없다. 템플릿을 실제로 고르는 일은 다음 단계(Step 4 Stage 1)에서 일어난다. 아래는 스펙 [template-candidate-selection](../../../reports/ppt-master/capabilities/template-candidate-selection.md)으로 확인한 내용이다.

### 한 줄 요약

Step 3에서 agent는 후보를 고르지 않는다. 후보 목록은 Stage 1 서버가 만든다. agent가 하는 일은 "이번 run은 템플릿 쓰는 모드로 시작할지, 자유 디자인으로 시작할지"와 "사용자가 직접 넘긴 템플릿 폴더가 있는지"를 정리해 두는 것이다.

### 호출 순서 (템플릿 선택이 끝날 때까지)

Step 3은 1번 하나뿐이고 2번부터는 Step 4 Stage 1이다. 이어서 보려고 한 표에 넣었다. `templates`를 골랐을 때의 전체 흐름이고, `free_design`이면 7~9번을 건너뛴다.

| # | 누가 | 호출 | 받는 것 | 나오는 것 | 검증 |
|---|---|---|---|---|---|
| 1 | agent | 파일 쓰기(스크립트 호출 없음) | 소통 계약 초안, `default_mode`, 사용자가 넘긴 폴더 목록 | `confirm_ui/recommendations.stage1.json`(안에 `template_options`) | 코드 확인(서버가 읽는 필드), 문서 선언(agent의 작성 시점) |
| 2 | agent | `server.py <project> --daemon` | 위 json | 서버 기동, 브라우저 URL | 실행 미확인 |
| 3 | 서버 | `_build_template_library` (agent가 부르지 않음) | index 4개 | 후보 목록(brand 21, style 14, layout 7, deck 2). 화면에 표시 | 코드 확인, 실행 확인(Flask test client) |
| 4 | agent | `server.py <project> --wait-only --wait-stage stage1` | 사용자가 제출할 때까지 대기 | 제출되면 종료 코드 0 | 실행 확인 |
| 5 | 서버 | 사용자가 제출하면 같은 요청에서 자동 | 사용자가 고른 선택 | `template_selection.json`(선택, `selection_sha256`)과 `result.json`(`stage1-confirmed`) | 실행 확인 |
| 6 | agent | 두 파일을 한 번 읽음 | 위 두 파일 | 확정된 선택 목록 | 문서 선언 |
| 7 | agent | `svg_quality_checker.py "<root>/templates" --template-mode --canonical-authoring` | 선택한 폴더 | 템플릿 구조 검사 결과. 오류가 있으면 설치 중단 | 문서 선언(`apply-template-workspace.md`), 실행 미확인 |
| 8 | agent | `apply_template.py <project> --root <폴더> [--root ...]` | 확정된 폴더 전부 | `templates/design_spec.<kind>.<id>.md`, `images/`, `icons/`, 프로젝트 루트의 `template_install.json` | 실행 확인 |
| 9 | 서버 | Stage 2를 열기 전에 `template_install.json`을 직접 검증 | 영수증의 `selection_sha256` | 일치하면 Stage 2 진행 | 코드 확인 |

- 1번에서 agent가 쓰는 것은 후보가 아니다. `default_mode`와 사용자가 넘긴 폴더 경로만 넣는다. 후보 목록은 3번에서 서버가 만든다.
- 5번 파일은 사용자가 확정했다는 증거라서 서버만 쓴다. agent가 쓰면 안 된다.
- 8번에서 선택과 다른 폴더를 넘기면 설치 스크립트가 exit 1과 `[ERROR] Selected roots or source bytes differ from the Stage-1 confirmation`을 낸다(실행 확인). agent가 선택과 다른 템플릿을 설치하는 것을 막는 장치다.
- `free_design`이면 설치 스크립트를 부르지 않고, 서버도 설치 영수증을 요구하지 않는다(스펙 `template-candidate-selection` 1.3.4, 코드 확인). 이번 run은 이 경우라 1~6번만 일어난다.

### 1. agent가 하는 일

UI 방식(브라우저 화면)을 쓸 때만 파일이 하나 생긴다. Step 4에서 `recommendations.stage1.json`을 쓸 때 그 안에 `template_options` 블록을 넣는다. 블록에는 두 가지가 핵심이다.

- `default_mode`: `free_design` 또는 `templates`. 사용자가 템플릿을 쓰겠다고 했거나 템플릿 폴더를 넘겼으면 `templates`, 아니면 `free_design`이다. 이 판단은 agent가 하고 코드는 검사하지 않는다.
- `explicit_workspace_roots`: 사용자가 직접 넘긴 템플릿 폴더의 절대 경로 목록. 없으면 빈 배열.

chat 방식을 쓰면 파일 없이 agent의 context에만 두고, 사용자가 `templates`를 골랐을 때에만 index 4개를 읽어 목록을 보여 준다.

이번 run은 사용자가 템플릿 얘기를 한 적이 없어서 `default_mode = free_design`, `explicit_workspace_roots = []`이다.

### 2. 후보 목록은 서버가 만든다

Stage 1 서버(`scripts/confirm_ui/server.py`의 `_build_template_library`)가 index 4개(`brands_index.json`, `styles_index.json`, `layouts_index.json`, `decks_index.json`)에 등록된 항목을 전부 후보로 만든다. 번들 기준 brand 21, style 14, layout 7, deck 2개다. 폴더는 훑지 않고 index만 읽는다.

화면에 "추천" 표시, 정렬, 필터는 없다. 순서는 index 순서 그대로이고, 미리 선택되는 것은 사용자가 정확한 폴더를 하나만 넘겼을 때 그 폴더뿐이다.

### 3. 선택하지 않으면

| 사용자가 제출한 것 | 결과 |
|---|---|
| `free_design` | 통과한다. `template_selection.json`에 `selections: []`가 기록된다 |
| `templates`인데 아무것도 안 고름 | 서버가 400으로 거부한다. 오류 문구는 `templates mode requires at least one selection key` |

둘 다 임시 프로젝트에서 서버를 직접 호출해 확인했다. 브라우저 화면에서도 같은 조건으로 제출이 막히는지는 소스만 읽었고 실행하지 않았다.

### 4. 커스텀 템플릿

두 가지 방법이 있다.

- `register_template.py <id> --kind brand|style|layout|deck`로 index에 등록하면 이후 Stage 1 후보 목록에 나온다(`library` 후보).
- 등록하지 않고 템플릿 폴더 경로를 직접 넘기면 `explicit` 후보가 된다.

실제 등록은 `repos/ppt-master` 파일을 고치므로 실행하지 않고 `--dry-run`만 했다.

### 5. 이 단계에서 만들어진 파일

없다. UI 방식을 고르면 Step 4 시작 때 `recommendations.stage1.json`이 처음 생긴다.

### 6. 검증 수준

- 실행으로 확인: 후보 목록 생성, 선택 0개 거부, `free_design` 통과, root 검증과 `library`/`explicit` 분류
- 문서 선언만 확인: agent가 index를 열지 않는다는 규칙, `default_mode`를 정하는 기준(agent 판단), chat 방식의 동작
- 확인하지 못함: 브라우저 렌더링, `--daemon` 기동, index 등록 실행(쓰기)

항목별 근거와 R-ID는 위 스펙에 있다.

## 다음

Step 4 Stage 1은 사용자 확정(⛔ BLOCKING)이 필요하다. 확정 전에는 `design_spec.md`, `spec_lock.md`를 만들지 않는다(Global discipline 5, "No speculative execution").
