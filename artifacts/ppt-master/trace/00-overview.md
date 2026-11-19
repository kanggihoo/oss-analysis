# ppt-master 실행 trace 종합 (Step 1~7)

- 기준: `repos/ppt-master` `3af3e8e`, venv `repos/ppt-master/.venv`(Python 3.12.13)
- 실행 일자: 2026-11-19 (약 15:15 ~ 17:01)
- 입력: [`input/portfolio.md`](input/portfolio.md). 가상 백엔드 개발자 포트폴리오, 5개 절
- 결과: `repos/ppt-master/projects/portfolio_demo_20261119/exports/portfolio_demo_20261119_170127.pptx` 7장. 사본은 [`snapshots/`](snapshots/)
- 목적: Default Generate 경로를 실제로 한 번 끝까지 실행하면서 단계마다 **무엇을 호출하고, 무엇이 필요하고, 무엇이 만들어지는지** 확인한다. 이 run에서 agent 역할은 분석 세션의 Claude가 했으므로 "스펙만으로 재현되는가"는 검증 범위 밖이다.

## 1. 한눈에 보는 표

| Step | 누가 | 호출 | 필요한 것 | 만들어지는 것 | 문서 |
|---|---|---|---|---|---|
| 진입 | agent | `attribution_guard.py`, `routing.md` 읽기 | `SKILL_DIR`, Python | 종료 코드 0. Default 경로 선택 | [01-03](01-03-intake-and-init.md) |
| 1 소스 | agent | 없음 (Markdown은 직접 읽음) | `.md` 파일 | 없음 | 〃 |
| 2 프로젝트 | 스크립트 | `project_manager.py init`, `import-sources` | 프로젝트 이름, 소스 경로 | `projects/<이름>_<날짜>/` 폴더 12개 항목, `sources/portfolio.md`, `validation/workflow.log` | 〃 |
| 3 템플릿 후보 | agent | 파일 쓰기 하나(UI 방식일 때) | 사용자의 템플릿 의사 유무 | 사용자에게 보이는 것은 없음 | 〃, 스펙 [template-candidate-selection](../../../reports/ppt-master/capabilities/template-candidate-selection.md) |
| 4 Stage 1 | agent + 서버 + **사용자** | `recommendations.stage1.json` 쓰기, `server.py --daemon`, `--wait-only --wait-stage stage1` | 소통 계약 초안, 브라우저 | `result.json`(`stage1-confirmed`), `template_selection.json`(`free_design`) | [04a](04a-stage1.md) |
| 4 Stage 2 | agent + 서버 + **사용자** | reference 7개 읽기, `recommendations.stage2.json` 쓰기, `--wait-only` | Stage 1 결과, 카탈로그 문서 | `result.json`(`final`): 방향, 색, 글꼴, 페이지 수, 노트 여부 등 | [04b](04b-stage2.md) |
| 4 설계서·lock | agent | `icon_sync.py`, `design_spec.md`와 `spec_lock.md` 직접 쓰기, `project_manager.py validate` | 확정값, `design_spec_reference.md`, `spec_lock_reference.md` | `design_spec.md`(208줄), `spec_lock.md`(68줄), `icons/` 10개 | [04c](04c-design-spec-and-lock.md) |
| 5 이미지 | - | 건너뜀 | 이미지 출처 `ai`/`web`/`slice`일 때만 | - | 이번 run은 `none` |
| 6 SVG | agent | `text_measure.py calibrate`, `svg_editor/server.py --live --daemon`, SVG 직접 작성 7개, `svg_quality_checker.py` early·final, `stamp_native_fallbacks.py`, `notes/total.md` 작성 | 설계서, lock, Executor reference | `svg_output/*.svg` 7개, `validation/*.json`, `notes/total.md` | [06-07](06-07-executor-and-export.md) |
| 7 내보내기 | 스크립트 | `total_md_split.py`, `finalize_svg.py`, `svg_to_pptx.py` (각각 따로) | final gate 통과, 노트 | `notes/<이름>.md` 7개, `svg_final/` 7개, `exports/*.pptx`, 내보내기 보고서 | 〃 |

사용자가 직접 한 일은 두 번(Stage 1 확정, Stage 2 확정)이다. API 키는 쓰지 않았다.

## 2. 구분해서 알아둘 것

### 서버는 두 종류다

| | 확인 화면 | live preview |
|---|---|---|
| 스크립트 | `confirm_ui/server.py` | `svg_editor/server.py --live` |
| 포트 | 5050 | 6060 (6060부터 빈 포트를 찾는다) |
| 언제 | Step 4 (Stage 1, Stage 2) | Step 6 시작부터 사용자가 **Exit preview**를 누를 때까지 |
| 역할 | 사용자 확정을 받는다. 확정하면 스스로 종료 | SVG 페이지를 화면으로 보여 준다(문서 설명 기준) |

### agent는 서버에 HTTP를 보내지 않는다

agent는 `recommendations.stage1.json`, `recommendations.stage2.json`을 파일로 쓴다. 서버는 브라우저가 `/api/session`, `/api/recommendations`를 요청할 때 그 파일을 읽어서 응답한다. 확정은 브라우저가 `POST /api/confirm`을 보내고, 서버가 `result.json`을 쓴다. 상세는 [04b](04b-stage2.md) 2절.

### 설계서·lock·SVG는 모두 agent가 직접 쓴 파일이다

이들을 만들어 주는 스크립트는 없다. `executor-base.md`가 "the current main agent hand-writes every page SVG — never a sub-agent, and never a generator that writes slide files"라고 정해 둔다. 스크립트가 하는 일은 확인(`validate`, `svg_quality_checker.py`)과 변환(`finalize_svg.py`, `svg_to_pptx.py`)이다. 도형 조각을 출력해 주는 보조 스크립트(`preset_shape_svg.py`, `shape_boolean_svg.py`)는 있지만 이번 덱은 사각형과 선만 써서 쓰지 않았다.

### 설계서와 lock

`design_spec.md`는 "무엇을 왜 만드는가"의 전체 기획서(페이지별 내용 포함)이고, `spec_lock.md`는 그중 SVG를 쓰는 동안 흔들리면 안 되는 값(색, 글꼴, 크기, 페이지 리듬, 금지 목록)만 뽑은 기준표다. 충돌하면 설계서가 이긴다.

## 3. 이번 run에서 새로 알게 된 것

- 템플릿 후보는 agent가 고르는 것이 아니라 서버가 index 4개를 읽어 전부 보여 준다. 화면에 "추천" 표시나 정렬은 없다(스펙 `template-candidate-selection`).
- 템플릿 모드에서 선택 0개 제출은 서버가 400으로 거부한다. `free_design` 제출은 `selections: []`로 통과한다(실행 확인).
- 확인 화면 서버의 기본 자동 종료는 900초다. 사용자가 15분 넘게 읽으면 서버가 내려가고 `--wait-only`가 종료 코드 1로 끝난다. 이번 run에서 서버가 세 번 사라졌다. 첫 `--daemon` 서버(Stage 1 직후)와 Stage 2 재시도 때 복구된 서버는 원인을 확인하지 못했고, 가운데 하나(Stage 1 때 복구된 서버)는 로그에 `idle for 900s, shutting down`이 찍힌 자동 종료였다. 그 뒤 Bash가 아니라 PowerShell `Start-Process`로 분리해 띄웠더니 정상 확정까지 갔다([04b](04b-stage2.md) 5절).
- 팔레트의 색 대비를 Stage 2에서 따져 보지 않았다. 설계서를 쓰며 계산했더니 주황 `#E58A00`은 흰색 위에서 2.64:1로 본문 기준(4.5:1)에 미달해, 사용 규칙으로 막았다([04c](04c-design-spec-and-lock.md) 2절).
- 표(P06)를 `Native-ready: yes`로 쓰면 SVG 안에 marker 그룹과 JSON이 들어가야 하고, final gate가 JSON이 fallback과 어긋나면 warning을 낸다. 이번에 3개가 나와 JSON을 보완했다([06-07](06-07-executor-and-export.md) 1절).
- 7장 로스터라서 Step 6의 early gate(P05 뒤)가 실행됐다. 6장 이하이면 이 gate는 건너뛴다.

## 4. 이 run에서 하지 않은 것과 규칙에서 벗어난 것

하지 않은 것: Step 5(이미지), 템플릿 모드(`templates`), `--native-charts-and-tables`, 애니메이션, 내레이션 오디오, `verify-charts`, `visual-review`, Revision Round(수정 요청 처리), PowerPoint나 LibreOffice로 열어 보는 확인.

규칙에서 벗어난 것(agent의 누락): `preset-shape-vocabulary.md`를 읽지 않음, 페이지마다 `modules:` 한 줄을 쓰지 않음(P01·P06만), P05 뒤 lock 재읽기를 하지 않음, Stage 2 전에 읽어야 하는 reference 일부를 끝까지 읽지 않음, 확정 뒤 "설계서 검토 안내" 한 줄을 하지 않음. 이번 덱은 단순해서 결과에 영향은 없었지만 규칙상 누락이다.

사용자가 Step 7 뒤에 렌더링 화면을 직접 보고 확인했다. 구체적으로 어색한 부분이 있었는지는 기록에 없다.

## 5. SVG로 복잡한 도형을 그릴 수 있는가

문서 기준으로 가능하다. 다만 조건이 있다. 이번 덱에서는 쓰지 않았다.

- **Office preset 187종**: 사각형 변형, 삼각형, 다각형, 화살표, chevron, 순서도 기호, callout, 별, banner, 괄호, 연결선 등을 `preset_shape_svg.py render <이름> --frame X Y W H --fill …`로 출력한 조각을 SVG에 붙여 넣는다. 예를 들어 `chevron`을 실제로 실행(출력만 확인, 파일에는 쓰지 않음)하면 `<g id="demo-chevron" data-pptx-authoring="preset" … data-pptx-prst="chevron" …><path d="M 100 100 L 292 100 …"/></g>`가 나온다. 이 조각은 PowerPoint에서 편집 가능한 네이티브 도형으로 내보내진다. 메타데이터를 손으로 쓰면 checker가 거부한다.
- **Boolean(합치기, 빼기)**: `shape_boolean_svg.py`. 윤곽을 합치거나 자르는 도형에만 쓴다.
- **자유 곡선(path)**: 마지막 수단이다. preset이나 독립 조합으로 안 되는 도형에만 쓰라고 한다("freeform is the last tier").
- **효과**: gradient, 그림자, glow 등은 `svg-effects.md`에 허용되는 방식이 있다. 단 `mask`, `<style>`, `class`, `<foreignObject>`, `textPath`, `<animate*>`, 스크립트는 전역 금지이고, `clip-path`는 이미지에만 쓸 수 있다.
- **데이터 차트와 표**: 값이 도형의 길이나 위치를 정하면 차트이고, `chart/<key>` 33종과 `table/<key>` 6종 참조가 있다.

이 중 `native-shape-authoring.md`(182줄)와 `svg-effects.md`는 이번에 읽지 않았다. 위 설명은 `executor-base.md`, `shared-standards-core.md`, `preset-shape-vocabulary.md` 앞부분과 `preset_shape_svg.py` 실행 출력으로 확인한 범위다. 선택 규칙과 한계(어떤 도형이 PowerPoint에서 실제로 어떻게 보이는지)는 확인하지 않았다.

## 6. 파일 안내

| 파일 | 내용 |
|---|---|
| `00-overview.md` | 이 문서 |
| `00-pip-freeze.txt` | venv 패키지 93개 목록 |
| `01-03-intake-and-init.md` | 진입, Step 1~3, 템플릿 후보의 의미와 호출 순서 |
| `02-*.txt`, `02-*.out` | `init`·`import-sources` 출력과 폴더 구조 목록 |
| `04a-stage1.md` | Stage 1 확인 화면, 서버 복구 |
| `04b-stage2.md` | Stage 2 권고 작성, 서버 수명 문제 |
| `04c-design-spec-and-lock.md` | 설계서·lock 작성, 색 대비 점검, Gate 1 |
| `04-*.out`, `04c-*.out`, `06-*.out`, `07-*.out` | 각 단계 명령의 원 출력 |
| `06-07-executor-and-export.md` | SVG 작성, gate, 노트, 내보내기 |
| `snapshots/` | `design_spec.md`, `spec_lock.md`, `result.final.json`, `recommendations.stage2.json`, `svg_output/`, `notes/total.md`, `.pptx`, 보고서 |
| `input/portfolio.md` | 입력 소스 |

## 7. 남은 것

- 수정 요청 경로 검증(Revision Round): 사용자가 본 어색한 부분을 SVG에서 고치고 final gate와 Step 7을 다시 돌리면 새 timestamp의 `.pptx`가 생기고 이전 것은 남는지 확인
- `templates` 경로 검증: 라이브러리 후보 하나를 골라 `apply_template.py`와 `template_install.json` 검증, `strategist-template.md` 적용, `structured` 구조까지
- 이미지 경로(Step 5)와 복잡한 도형(`native-shape-authoring.md`) 사용
- 별도 세션 재구현 검증(스펙과 허용된 C-ID 코드만 받은 세션이 같은 결과를 만드는지)
