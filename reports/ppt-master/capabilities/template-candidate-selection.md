---
sha: "3af3e8ef774c4d67ee57e1306d9256d08c9ee1bf"
created: 2026-11-19
updated: 2026-11-19
sources:
  - skills/ppt-master/workflows/generate-pptx.md
  - skills/ppt-master/workflows/routing.md
  - skills/ppt-master/references/confirm-surface.md
  - skills/ppt-master/references/strategist.md
  - skills/ppt-master/workflows/stages/apply-template-workspace.md
  - skills/ppt-master/workflows/create-template.md
  - skills/ppt-master/scripts/docs/confirm_ui.md
  - skills/ppt-master/scripts/confirm_ui/server.py
  - skills/ppt-master/scripts/confirm_ui/static/app.js
  - skills/ppt-master/scripts/apply_template.py
  - skills/ppt-master/scripts/register_template.py
  - skills/ppt-master/templates/brands/brands_index.json
  - skills/ppt-master/templates/styles/styles_index.json
  - skills/ppt-master/templates/layouts/layouts_index.json
  - skills/ppt-master/templates/decks/decks_index.json
depends:
  - ../capabilities/generate-default-pipeline.md
  - ../capabilities/confirm-and-preview-ui.md
status: ready
---

# 템플릿 후보 준비와 Stage 1 템플릿 선택

> Default 생성의 Step 3에서 agent가 `recommendations.stage1.json`에 넣는 `template_options`(`default_mode`, `explicit_workspace_roots`)와, 그 입력에서 확정 서버가 후보 목록을 만들고 사용자의 선택을 `template_selection.json`으로 굳혀 설치 단계로 넘기는 경계를 쓴 스펙이다.

<!--
읽는 법
- 이 스펙이 답하려는 질문은 "Step 3에서 AI가 Stage 1 화면에 보여줄 후보를 골라 담는가"다. 결론은 1.1에 있고 근거는 R-01~R-04다.
- Stage 1 화면의 서버 수명(포트, lock, exit code), `result.json` 필드, Stage 2는 선행 `confirm-and-preview-ui.md`가 쓴다. 여기서는 다시 쓰지 않고 "선행 R-xx"로 부른다. 설치기 내부(`apply_template.py`의 mapping, collision, rollback)와 Create Template 절차는 쓰지 않는다. 경계만 1.3.4에 둔다.
- 검증 수준 `코드 확인(문서 선언)`은 문서를 읽어 선언을 확인했고 스크립트가 강제하지 않는다는 뜻이다. 스크립트 동작은 `코드 확인`, 실제로 돌려 본 것은 `실행 확인`으로 구분한다. 실행은 2.1 "실행 기록"에 명령과 출력을 둔다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

**결론.** "Step 3에서 AI가 후보를 골라 담는다"는 이해는 이 SHA에서 맞지 않다. UI 방식에서 agent가 Step 3에 하는 일은 `recommendations.stage1.json`에 `template_options` 블록 하나를 넣는 것이고, 그 안에서 agent의 판단이 들어가는 값은 `default_mode`(화면이 어느 모드로 시작할지) 하나다. 화면에 나오는 후보 목록은 서버가 `brands/styles/layouts/decks` index 4개를 읽어 등록된 항목을 전부 만든다. agent는 index도 후보 spec도 열지 않는다(R-01, R-02). 화면에는 "추천" 표시도 정렬도 필터도 없고, 미리 선택되는 것은 사용자가 정확한 root 하나를 줬을 때 그 root뿐이다(R-04, R-05).

1. **Step 3 (agent, 사용자에게 보이는 것 없음)**: UI 방식이면 `confirm_ui/recommendations.stage1.json`에 `template_options`(`schema_version: 1`, `phase: "template"`, `lang`, `default_mode`, `explicit_workspace_roots`)를 넣는다. `default_mode`는 사용자가 템플릿 사용 의사를 분명히 밝혔거나 정확한 root를 줬으면 `templates`, 아니면 `free_design`이다. 서버를 아직 띄우지 않는다(R-01). chat·위임 방식이면 파일을 만들지 않고 같은 경계를 컨텍스트에 들고 있는다(R-03).
2. **Stage 1 화면 (서버)**: `GET /api/recommendations`가 Stage 1 recommendation에 서버가 만든 `template_options` 카탈로그(`library` 4종 그룹, `explicit`, `preselected_keys`, `options_sha256`)를 얹어 내려준다. 후보 키는 서버가 정한다(R-02, R-06).
3. **사용자 선택 (브라우저)**: 화면은 먼저 `Free design` / `Use templates`를 묻는다. `Use templates`일 때만 Brand·Style·Layout·Deck 드롭다운(각 `None` 포함)과 지정 root 체크박스가 펼쳐진다. 템플릿 모드에서 선택이 0개면 버튼이 막히고, 종류 중복도 막힌다(R-09, R-10).
4. **제출 (서버)**: 서버는 `options_sha256`과 키를 현재 후보에 대조해 `template_selection.json`을 쓰고 같은 요청에서 `result.json`(`stage1-confirmed`)을 쓴다. 이 두 파일이 사용자 영수증이다(R-08, R-11, R-12).
5. **설치 입력 (agent)**: agent는 두 파일을 한 번 읽고, `templates`이면 확정된 root 전부를 `apply-template-workspace`에 넘기고, `free_design`이면 설치를 건너뛴다. 설치기는 `template_selection.json`과 root snapshot이 같은지 확인하고 `selection_sha256`을 `template_install.json`에 적는다(R-13, R-14).
6. **등록**: 사용자 정의 템플릿이 후보 목록에 나오는 길은 둘이다. `register_template.py`로 library index에 등록하거나, 등록하지 않고 정확한 root를 `explicit_workspace_roots`로 넘기는 것이다. 디렉터리를 index 없이 `templates/<kind_dir>/` 아래에 두는 것만으로는 후보가 되지 않는다(R-15, R-16).

### 1.2 범위·통합 지점 [필수]

- **제공**: Step 3이 만드는 `template_options` 입력 계약, 서버가 만드는 후보 카탈로그와 키·digest, `default_mode`와 `explicit_workspace_roots` 검증, 선택 규칙(0개, 종류 중복, 자유 디자인), `template_selection.json` 구조와 `selection_sha256`, 설치 단계에 넘기는 입력 경계, 후보 목록과 index 등록의 관계.
- **제외**: Stage 1 화면의 소통 계약 필드와 서버 수명·exit code·`result.json` 전체(선행 `confirm-and-preview-ui.md`), 설치기 내부와 Stage 2의 `template_application`·prototype 선택(`apply-template-workspace.md`, `strategist-template.md`), Create Template 절차와 템플릿 내부 스키마, `register_template.py`의 spec 검증 규칙 내부, 프론트엔드 스타일과 다국어 문구.
- **외부 의존·선행 계약**: 선행 `generate-default-pipeline.md`의 Step 3·Step 4 gate(R-15, R-17, R-18), 선행 `confirm-and-preview-ui.md`의 서버 명령·종료 코드·라운드 규칙(선행 R-05, R-07, R-11, R-12, R-15, R-16). 번들 library(`skills/ppt-master/templates/{brands,styles,layouts,decks}`와 index 4개).
- **소유 상태·부작용**: agent가 쓰는 것은 `confirm_ui/recommendations.stage1.json`의 `template_options`뿐이다. 서버가 쓰는 것은 `confirm_ui/template_selection.json`과 Stage 1 `result.json`이다. 설치기가 쓰는 것은 프로젝트 루트의 `template_install.json`과 `templates/`·`images/`·`icons/`다. 이 스펙의 코드는 library index를 읽기만 하고 고치지 않는다.

### 1.3 인터페이스와 데이터 의미 [필수]

#### 1.3.1 입력: `recommendations.stage1.json.template_options` (agent가 씀)

| 필드 | 타입·제약 | 의미 |
|---|---|---|
| `schema_version` | int, 정확히 `1` | 아니면 Stage 1이 준비되지 않은 것으로 거부(R-07) |
| `phase` | string, 정확히 `"template"` | 같음 |
| `lang` | optional non-empty string | UI 언어. 있으면 카탈로그에 `strip()`해 그대로 전달 |
| `default_mode` | `"free_design"` 또는 `"templates"`, 필수 | 화면 시작 모드. 사용자를 잠그지 않는다(R-05) |
| `explicit_workspace_roots` | array, 필수(비어도 키가 있어야 함) | 이번 실행에 사용자가 준 정확한 workspace root. 각 항목은 비어 있지 않은 string, 절대 경로, 존재하는 디렉터리, 중복 없음. 값이 하나라도 있으면 `default_mode`는 `templates`여야 한다(R-07) |

`template_options` 안에 library 항목을 쓰는 필드는 없다. 서버가 index에서 직접 읽는다(R-02).

#### 1.3.2 카탈로그: `GET /api/recommendations`가 얹는 `template_options` (서버가 만듦)

| 필드 | 의미 |
|---|---|
| `default_mode`, `lang`, `schema_version`, `phase` | 입력을 그대로 전달 |
| `library.{brand,style,layout,deck}` | 각 index의 **모든** 항목. 후보 하나는 `key`(`library:<kind>:<id>`), `source: "library"`, `kind`, `id`, `label`(= `id`), `summary`(index의 `summary`, 없으면 빈 문자열), `workspace_root`(canonical 절대 경로). 순서는 index JSON의 항목 순서다 |
| `explicit` | 등록되지 않은 exact root의 후보. `key`(`explicit:<root 경로 sha256>:<kind>`), `source: "explicit"`, `kind`(spec frontmatter에서 읽음), `label`(root 디렉터리 이름), `workspace_root` |
| `preselected_keys` | 정확히 root 하나가 입력됐을 때 그 root의 후보 키(여러 kind면 전부). 아니면 `[]` |
| `options_sha256` | 아래 R-06의 digest. 브라우저가 제출 때 되돌려 보낸다 |

#### 1.3.3 출력: `confirm_ui/template_selection.json` (서버가 씀, 필드는 정확히 아래 9개)

| 필드 | 의미 |
|---|---|
| `schema_version` (1), `phase` (`"template"`), `status` (`"confirmed"`) | 고정값 |
| `mode` | `free_design`이면 `selections`가 `[]`, `templates`이면 1개 이상 |
| `selections` | `{source, kind, workspace_root}` 배열, library이면 `id`가 더 있다(그 외 필드 금지). `source`, `kind`, `id`, `workspace_root` 순으로 정렬. 종류(kind)마다 최대 1개 |
| `root_snapshots` | 선택된 root마다 `{workspace_root, source, kinds, specs[{kind,id,path}], files{경로: sha256}}`. `files`는 root의 `templates/`·`images/`·`icons/` 전체 바이트의 해시. `free_design`이면 `[]` |
| `options_sha256` | 제출 당시 카탈로그의 digest |
| `selection_sha256` | `sha256(canonical_json({mode, selections, options_sha256, root_snapshots}))` |
| `confirmed_at` | 서버 로컬 시각 `YYYY-MM-DDTHH:MM:SS` |

`result.json`에는 선택 키가 들어가지 않고 `stage1_sha256`, `selection_sha256`만 복사된다. 같은 제출에서 `template_selection.json`이 먼저, `result.json`이 나중에 쓰인다(R-11).

#### 1.3.4 설치 단계와의 경계

| 방향 | 내용 |
|---|---|
| 서버 → agent | `template_selection.json`(`mode`, `selections`, `root_snapshots`, `selection_sha256`)과 `result.json`. agent는 이를 한 번 읽는다 |
| agent → 설치기 | `python3 scripts/apply_template.py <project_path> --root <workspace_root> [--root ...]`. 인자는 `selections`의 `workspace_root`를 중복 없이 모은 것이다. 선택에 없던 root나 바이트가 바뀐 root를 넘기면 설치기가 `Selected roots or source bytes differ from the Stage-1 confirmation`으로 exit 1 한다 |
| 설치기 → 서버 | 프로젝트 루트 `template_install.json`: `selection_sha256`(= `template_selection.json`의 값), `roots`(= `root_snapshots`), `installed_specs`, `active_roster`, `files`(설치된 파일의 해시). 서버는 Stage 2를 열 때와 제출할 때 `read_template_install`로 직접 검증한다 |
| `free_design` | 설치기를 부르지 않는다. 서버는 설치 영수증을 요구하지 않는다 |

설치 내부(`templates/design_spec.<kind>.<id>.md` 이름 규칙, Layout 우선 roster, asset 충돌 거부 등)는 이 스펙의 범위 밖이다.

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | Step 3, UI 방식 | agent는 `recommendations.stage1.json`에 `template_options`를 넣는 것까지만 한다. 서버를 띄우지 않고, 사용자에게 보이는 페이지·질문·선택·설치도 없다. agent는 후보 index·spec·prototype을 열지 않고 Stage 1을 쓴다(템플릿 사실은 canvas·page range 참고에만 쓴다) | 코드 확인(문서 선언) |
| R-02 | 후보 목록 생성 | 서버가 `_build_template_library`로 index 4개를 읽어, 각 항목의 `workspace_root`가 `<kind_dir>/<id>` 직계 자식이고 `templates/design_spec.md`가 있고 frontmatter `kind`가 index 종류와 같은지 검사한 뒤 **모든** 항목을 후보로 만든다. 디렉터리를 스캔하지 않는다. agent가 후보를 골라 넣는 경로는 없고, `template_options`에 library 항목을 쓰는 필드도 없다. 하나라도 검사에 실패하면 카탈로그 전체가 만들어지지 않고 Stage 1이 준비되지 않은 것이 된다(선행 R-05의 exit 1, 화면은 409) | 코드 확인, 실행 확인(번들 index에서 brand 21·style 14·layout 7·deck 2개 전부) |
| R-03 | Step 3, chat·위임 방식 | 파일을 만들지 않는다. chat은 소통 추천을 먼저 쓴 뒤에 index 4개를 읽고, 사용자가 `templates`를 고른 경우에만 등록 후보와 지정 root를 펼치며 선택 1개 이상을 요구한다. 일반 요청은 `free_design`, 명시적 템플릿 의도나 지정 root가 있으면 `templates`, root가 정확히 하나면 미리 선택 가능하다. "What templates exist?"에는 index가 가리키는 workspace 경로를 나열한다. 위임이면 agent가 이 결정을 내리고 설치하며, 어떤 기준으로 후보를 고르는지 문서는 정하지 않는다 | 코드 확인(문서 선언). 이 분기는 서버 코드가 없다 |
| R-04 | 추천·정렬·필터 존재 여부 | 없다. 후보 객체는 `key/source/kind/id/label/summary/workspace_root`만 갖고 점수·추천·배지 필드가 없다. 서버는 정렬하지 않고(index 항목 순서 그대로), `app.js`의 후보 정규화·렌더(`normalizeTemplateCandidates`, `renderTemplateSelectField`)도 정렬·필터·추천 표시를 하지 않는다. 드롭다운 옵션 순서가 곧 후보 순서이고 `None`이 맨 앞에 있다. `strategist.md`의 "candidates never influence the communication recommendation"은 Stage 1 소통 계약 추천이 후보 목록에서 독립이라는 규칙이고, 템플릿을 추천하지 않는다는 문장은 아니다. 템플릿 추천이 없다는 결론은 이 R-04의 코드 읽기에서 나온다 | 코드 확인 |
| R-05 | `default_mode`와 미리 선택 | `default_mode`는 agent가 정한다. 문서 규칙은 명시적 템플릿 의도 또는 지정 root가 있으면 `templates`, 아니면 `free_design`이다. "명시적 의도"인지의 판단은 agent(LLM)의 몫이고 코드가 판정하지 않는다. 서버가 강제하는 것은 `explicit_workspace_roots`가 비어 있지 않으면 `default_mode == templates`라는 한 방향뿐이다(어기면 Stage 1 준비 오류). `templates`이고 root가 없는 입력은 허용되며 화면은 템플릿 모드로 시작해 선택 0개 상태가 된다. 사용자는 언제든 모드를 바꿀 수 있다. 미리 선택은 서버가 `len(explicit_workspace_roots) == 1`일 때만 `preselected_keys`로 내리고(그 root가 library root와 같아도), root가 둘 이상이면 아무것도 선택하지 않는다 | 코드 확인(서버 규칙), 코드 확인(문서 선언)(agent 판단 기준), 실행 확인(`templates`+빈 root 허용, root 둘이면 `preselected_keys == []`) |
| R-06 | 카탈로그 digest | `options_sha256`은 `sha256(canonical_json({schema_version, phase, default_mode, lang, explicit_workspace_roots, stage1_sha256, library_indexes(4개 index 원문), library, explicit, preselected_keys}))`다. 따라서 stage1 recommendation 전체, index 내용, 후보 목록 중 하나라도 바뀌면 값이 바뀐다 | 코드 확인 |
| R-07 | `template_options` 검증 실패 | 아래 중 하나면 Stage 1이 "준비되지 않음"이다(launch는 exit 1, `GET /api/recommendations`는 409): `template_options`가 object가 아님, `schema_version`이 정확한 int 1이 아님, `phase`가 `template`이 아님, `default_mode`가 두 값이 아님, `lang`이 비어 있지 않은 string이 아님, `explicit_workspace_roots` 키 없음 또는 array 아님, root가 있는데 `default_mode`가 `templates`가 아님, root 항목이 비어 있는 string이 아니거나 절대 경로가 아니거나 디렉터리가 아니거나(`resolve()` 후) 중복이거나, 그 root에 `templates/design_spec.md` 또는 `templates/design_spec.<kind>.<id>.md`가 없거나 둘이 섞여 있음 | 코드 확인, 실행 확인(상대 경로, 없는 경로, spec 없는 디렉터리, 같은 root 두 번, `free_design`+root 모두 409와 사유) |
| R-08 | 지정 root의 분류 | 지정 root의 canonical 경로가 index에서 파생된 등록 root와 **정확히 같으면** 새 `explicit` 후보를 만들지 않고 해당 library 후보를 쓰며 미리 선택 키도 library 키다. 같지 않으면 `explicit` 후보가 spec 하나당 하나 생긴다(kind는 spec frontmatter, qualified 파일명이면 파일명과 frontmatter의 kind·id가 일치해야 함). 한 root가 같은 kind를 둘 이상 내놓으면 오류다. 화면은 root 단위 체크박스 하나로 보이고, 선택하면 그 root의 모든 kind가 선택되며, 일부 kind만 제출하면 서버가 거부한다 | 코드 확인, 실행 확인(등록 root → `explicit: []`+`library:brand:anthropic` 미리 선택, 미등록 복사본 → `explicit` 후보+미리 선택) |
| R-09 | 브라우저 쪽 제출 조건 | `free_design`이면 항상 제출 가능하고 선택은 비운다. `templates`이면 선택된 키가 1개 이상이어야 하고 같은 `kind`가 둘이면 막는다. 막히면 상태줄에 "Choose free design or use templates. When using templates, select at least one workspace." 또는 "Choose at most one workspace per kind."를 보이고 요청을 보내지 않는다. 제출 payload는 `options_sha256`과 `template_selection: {mode, selection_keys}`(`free_design`이면 `[]`)를 싣는다 | 코드 확인(소스를 읽음, 브라우저 미실행) |
| R-10 | 서버 쪽 제출 검증 (브라우저를 우회한 요청 포함) | Stage 1 `POST /api/confirm`은 순서대로 거부한다. Stage 1 준비 오류 → 409. `template_selection`이 object가 아님 → 400. `options_sha256` 불일치 → **409** `Stage 1 options changed; reload the page`. 그 다음 `_resolve_template_confirmation`의 `ValueError`는 모두 **400** `invalid Stage 1 template selection: <사유>`: payload 필드가 `mode`·`selection_keys` 외이면, `mode`가 두 값이 아니면, 키가 string 배열이 아니거나 중복이면, `free_design`인데 키가 있으면, **`templates`인데 키가 0개이면(`templates mode requires at least one selection key`)**, 현재 후보에 없는 키(서버가 카탈로그에서 만든 키만 유효, 임의 경로 불가), 같은 kind가 둘 이상(`at most one workspace for kind`), 선택된 지정 root가 노출하는 kind를 다 선택하지 않음. 거부되면 `template_selection.json`과 `result.json`은 써지지 않는다 | 코드 확인, 실행 확인(0개 → 400, `free_design`+키 → 400, 모르는 키 → 400, brand 둘 → 400, 오래된 digest → 409, 거부 뒤 `confirm_ui/`에 영수증 없음) |
| R-11 | 성공한 Stage 1 제출 | 서버가 `template_selection.json`(R-12 구조)을 먼저 쓰고 `result.json`(`stage: stage1`, `status: stage1-confirmed`, `stage1_sha256`, `selection_sha256`)을 쓴다. 이어서 `--wait-only --wait-stage stage1`은 `template_selection.json`이 현재 상태에서 유효할 때만 exit 0이고, 유효하지 않으면 exit 2다. 두 파일은 한 트랜잭션이 아니라 순차 쓰기다 | 코드 확인, 실행 확인(`free_design` 제출 뒤 `--wait-only`가 exit 0) |
| R-12 | `free_design` 확정과 선택 사후 상태 | `free_design`을 고르고 제출하면 `mode: free_design`, `selections: []`, `root_snapshots: []`인 영수증이 쓰이고, `selection_sha256`이 계산된다(`result.json`의 값과 같다). 설치기는 부르지 않으며 서버도 `template_install.json`을 요구하지 않는다. 사용자가 아무것도 고르지 않은 채 두 선택지 중 하나를 확정하는 제출은 없다. 화면은 항상 `default_mode`의 모드가 선택된 상태이고, `templates`가 기본인데 0개이면 R-09·R-10으로 제출이 막혀 `free_design`으로 바꾸거나 후보를 골라야 한다 | 코드 확인, 실행 확인(`free_design` 영수증과 digest 일치) |
| R-13 | 확정된 `templates` 선택을 읽을 때 | 서버는 영수증을 읽을 때마다 구조와 digest를 다시 검증하고(`selection_sha256` 재계산), 선택된 root의 현재 파일 해시가 `root_snapshots`와 같은지, 현재 카탈로그의 `options_sha256`이 영수증과 같은지, 선택이 현재 후보에 있는지, 지정 root의 kind가 전부 선택됐는지를 본다. root 원본이 바뀌었거나 index·stage1 내용이 바뀌었으면 오류이고 다시 확정해야 한다. 단 root가 프로젝트 자신이면(제자리 사용) 설치 영수증이 입증하는 변경만 허용한다 | 코드 확인 |
| R-14 | 설치 입력과 영수증 | agent는 확정된 모든 root를 한 번에 `apply_template.py --root`로 넘긴다. 설치기는 `confirm_ui/template_selection.json`이 있으면 `mode == templates`이고 `root_snapshots`가 같아야 진행하고 `selection_sha256`을 영수증에 복사한다. 서버는 그 영수증이 선택과 일치(roots, installed specs, active roster, 파일 해시)해야 Stage 2를 연다. 같은 digest가 `recommendations.stage2.json`의 최상위 `selection_sha256`에도 있어야 한다 | 코드 확인, 실행 확인(library 2개 설치 후 `template_install.json.selection_sha256 == template_selection.json.selection_sha256`, `_stage2_ready_error`가 `None`, 일부 root만 넘기면 exit 1) |
| R-15 | 사용자 정의 템플릿이 후보가 되는 길 | `register_template.py <id> --kind <kind>`가 `templates/<kind_dir>/<id>/templates/design_spec.md`에서 entry(brand: `summary, primary_color` / style: `summary, keywords` / layout: `summary, canvas_format, page_count, page_types` / deck: `summary, canvas_format, page_count, primary_color`)를 만들어 index에 쓰면 다음 Stage 1부터 library 후보가 된다. 등록은 library 범위만 한다. 프로젝트 범위 workspace는 등록하지 않고 정확한 root를 `explicit_workspace_roots`로 넘겨야 `explicit` 후보가 된다. 서버가 후보 카탈로그에 싣는 index 필드는 `summary`뿐이고 나머지 필드는 후보 표시에 쓰이지 않는다(단 index 원문 전체가 `options_sha256`에는 들어간다) | 코드 확인, 실행 확인(`register_template.py anthropic --kind brand --dry-run`이 현재 `brands_index.json`과 같은 21개 entry를 재생성) |
| R-16 | "index만이 발견 경로"라는 규칙 | 선택 후보를 만드는 서버 코드는 index만 읽고 kind 디렉터리를 스캔하지 않는다(규칙이 코드와 일치). 번들에서 디렉터리 수와 index 항목 수는 4종 모두 같다. index에 항목이 있는데 디렉터리가 없거나 `design_spec.md` 또는 frontmatter kind가 어긋나면 그 항목만 빠지지 않고 카탈로그 전체가 실패한다. index에 없는 디렉터리는 조용히 후보에서 빠진다. 디렉터리를 스캔하는 곳은 `register_template.py`의 `--rebuild-all`뿐이고 그것은 index를 쓰는 도구이지 후보 발견 경로가 아니다 | 코드 확인(검색 범위는 2.1) |

- 불변식: 서버가 쓰는 `selections`의 모든 항목은 같은 제출에서 서버가 만든 후보의 투영이다. 브라우저가 보낸 경로 문자열은 `workspace_root`로 쓰이지 않는다. 한 `template_selection.json` 안에서 kind마다 선택은 최대 1개다.
- 미결정: 없음. 단 아래 "확인 한계"는 원본이 정하지 않은 것이다.
- 확인 한계:
  - chat·위임 분기에서 agent가 어떤 기준으로 library 후보를 나열·고르는지는 문서가 "index가 가리키는 경로를 나열", "위임이면 agent가 결정"까지만 말하고 정렬·추천·개수 기준을 정하지 않았다(코드가 없는 분기이므로 `미확인`이 아니라 원본이 정하지 않은 것).
  - 실제 브라우저에서 화면을 렌더하지 않았다. 화면 동작(R-09, 드롭다운 순서)은 `app.js` 소스를 읽은 것이다.
  - `explicit` root와 library root를 함께 골라 kind가 겹칠 때의 거부는 같은 검사(`_validate_template_selection`의 kind 중복)를 library 둘로만 실행해 확인했다.

### 1.5 필수 코드 참조 [필수]

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `scripts/confirm_ui/server.py:310-378` `_read_template_options_input` | `template_options` 입력 검증 순서와 오류 문구 | R-05, R-07 |
| C-02 | `server.py:381-450` `_build_template_library`, `:453-530` `_build_template_options` | index → 후보, 지정 root 분류, `preselected_keys`, `options_sha256` 구성 | R-02, R-05, R-06, R-08 |
| C-03 | `server.py:560-711` `_validate_template_selection`, `:688-711` `_validate_explicit_root_closure` | `template_selection.json` 필드·kind 중복·digest 재계산 | R-10, R-12, R-13 |
| C-04 | `server.py:789-853` `_resolve_template_confirmation` | 제출 키 검증과 영수증 생성 | R-10, R-11 |
| C-05 | `server.py:2564-2750` `confirm` (Stage 1 분기 `:2593-2628`, 쓰기 `:2741-2743`) | 제출 오류 순서와 두 파일 쓰기 순서 | R-10, R-11 |
| C-06 | `scripts/confirm_ui/static/app.js:1060-1117` `initTemplateOptions`, `:4327-4348` `templateSelectionValid` | 시작 모드·미리 선택 적용, 브라우저 제출 조건 | R-05, R-09 |
| C-07 | `scripts/apply_template.py:622-654` `apply_templates`, `:460-502` `read_template_install` | 설치기와 선택 영수증의 결합 | R-14 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출. 모두 임시 프로젝트에서 서버 모듈을 Flask test client로 호출해 얻은 값이다(2.1 "실행 기록").

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02, R-04 | `default_mode: free_design`, `explicit_workspace_roots: []`의 Stage 1에서 `GET /api/recommendations` | 200. `library`에 brand 21·style 14·layout 7·deck 2 후보가 모두 있고 `explicit: []`, `preselected_keys: []`. 후보 필드는 `id,key,kind,label,source,summary,workspace_root`뿐이고 brand 순서는 `accenture, alibaba, anthropic, aws, bain`(index 순서) |
| T-02 | R-10 | 위 카탈로그의 `options_sha256`과 `{mode: templates, selection_keys: []}`로 `POST /api/confirm` | 400 `invalid Stage 1 template selection: templates mode requires at least one selection key`. `confirm_ui/`에 `result.json`·`template_selection.json` 없음 |
| T-03 | R-10 | `{mode: free_design, selection_keys: ["library:brand:anthropic"]}` / `["library:brand:nope"]` / `["library:brand:anthropic","library:brand:aws"]` | 각각 400 `free_design cannot carry selection_keys` / `selection_keys contains unavailable candidate keys: library:brand:nope` / `template selection allows at most one workspace for kind 'brand'` |
| T-04 | R-10 | `options_sha256`을 `"0"*64`로 바꿔 제출 | 409 `Stage 1 options changed; reload the page` |
| T-05 | R-11, R-12 | `{mode: free_design, selection_keys: []}` 제출 후 `--wait-only --wait-stage stage1 --wait-timeout 5` | 200 `{"status":"ok"}`. `template_selection.json`은 `mode: free_design`, `selections: []`, `root_snapshots: []`. `result.json`은 `stage: stage1`, `status: stage1-confirmed`이고 `selection_sha256`이 영수증과 같다. wait는 exit 0 |
| T-06 | R-11, R-14 | `{mode: templates, selection_keys: ["library:brand:anthropic","library:style:consulting-decision"]}` 제출 | 200. `selections` 2개(`source/kind/id/workspace_root`), `root_snapshots` 2개(brand `files` 4개, style 1개). 설치 영수증이 없으므로 `_stage2_ready_error`가 `Cannot read ...template_install.json; run apply_template.py`를 반환 |
| T-07 | R-14 | T-06 뒤 `apply_template.py <project> --root <anthropic> --root <consulting-decision>` | `[OK] installed 5 file(s)`(spec 2, images 3), exit 0. `template_install.json.selection_sha256`이 `template_selection.json`과 같고 `installed_specs`는 `design_spec.brand.anthropic.md`, `design_spec.style.consulting-decision.md`, `_stage2_ready_error`는 `None`. 같은 프로젝트에 `--root <anthropic>`만 넘기면 `[ERROR] Selected roots or source bytes differ from the Stage-1 confirmation`, exit 1 |
| T-08 | R-05, R-07 | 지정 root가 `[]`이고 `default_mode: templates` / root 하나 있고 `default_mode: free_design` / 상대 경로 / 없는 경로 / `templates/`가 없는 디렉터리 / 같은 root 두 번 | 첫째는 200(`default_mode: templates`, `preselected_keys: []`). 나머지는 모두 409 `Stage 1 is not ready: invalid Stage 1 recommendations: <사유>` |
| T-09 | R-05, R-08 | 지정 root 하나가 `templates/brands/anthropic`(등록 root)와 같음 / 같은 내용을 복사한 미등록 `my_brand` / `my_brand`와 `my_style` 둘 | 첫째 `explicit: []`, `preselected_keys: ["library:brand:anthropic"]`. 둘째 `explicit`에 `source: explicit, kind: brand, label: my_brand` 하나, `preselected_keys`에 `explicit:<sha256>:brand` 하나. 셋째 `explicit` 둘, `preselected_keys: []`. 둘째의 키를 제출하면 `selections`에 `source: explicit`(id 없음), `root_snapshots[0].source: explicit` |
| T-10 | R-10 | `free_design` 카탈로그에서 서버 카탈로그에 없는 `explicit:abc:brand` 키로 제출 | 400 `selection_keys contains unavailable candidate keys: explicit:abc:brand` |
| T-11 | R-15 | `register_template.py anthropic --kind brand --dry-run` | exit 0, 출력된 index가 현재 `brands_index.json`과 동일(21개, id 알파벳순). 레포 파일은 바뀌지 않음 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

모든 경로는 `repos/ppt-master`@`3af3e8ef774c4d67ee57e1306d9256d08c9ee1bf` 기준이다.

| R-ID / T-ID | 근거 (`파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `skills/ppt-master/workflows/generate-pptx.md:72-87`(Step 3 표, "Do not launch yet; the server reads indexes"), `:132-136`(Stage 1은 후보 spec·prototype을 열지 않고 작성), `references/confirm-surface.md:41-45`, `scripts/docs/confirm_ui.md:316-318` | 문서 선언. agent가 index를 읽지 않는 것을 강제하는 코드는 없다. 서버는 `template_options` 입력만 읽는다(C-01) |
| R-02 | C-02 `server.py:381-450`, `:2461-2500`, `scripts/docs/confirm_ui.md:105-113` | 읽은 뒤 T-01로 실행 확인. **부재 주장**("agent가 후보를 고르는 경로 없음", "디렉터리 스캔 없음"): 검색 `grep -n "_index.json" scripts/confirm_ui/server.py`는 `:117-120`(상수)뿐이고 `grep -n "iterdir\|\.glob(\|os.listdir\|scandir" scripts/confirm_ui/server.py`의 후보 관련 사용은 `_template_design_specs`의 `templates_dir.glob('design_spec.*.md')`(`:226-229`, 한 workspace 안의 spec 파일 찾기)뿐이다. `grep -rn "_build_template_library\|_build_template_options" skills --include=*.py`는 `confirm_ui/server.py` 밖에서 `scripts/tests/test_template_flow_batch1.py`·`batch3.py`만 찾는다(테스트 호출, 열지 않았다). 놓쳤을 가능성: 동적 호출, 비 `.py` 파일 |
| R-03 | `workflows/generate-pptx.md:80-87`, `:154`, `references/confirm-surface.md:7-26`(Surface decision, "Chat/delegated Stage-1 listing"), `workflows/routing.md:103-116` §7 표 | 문서 선언. 이 분기를 구현한 코드는 찾지 못했다(선행 R-01과 같은 검색 범위) |
| R-04 | `server.py:416-441`(후보 필드), `:453-530`, `static/app.js:1047-1058` `normalizeTemplateCandidates`, `:1230-1258` `renderTemplateSelectField`; `references/strategist.md:25`(문장 위치) | **부재 주장**: 검색 `grep -n -i "recommended\|score\|rank\|sort" scripts/confirm_ui/server.py`의 후보 관련 결과는 `sorted()`가 spec 파일명(`:224`), 중복 kind 검사(`:480`), snapshot·selection 정렬(`:661`, `:672`, `:706`, `:820`, `:833`)에 쓰이는 것뿐이고(후보 순서를 바꾸지 않는다), `grep -n "\.sort(" scripts/confirm_ui/static/app.js`는 결과가 없다. 놓쳤을 가능성: CSS(`style.css`)로 순서를 바꾸는 경우(읽지 않았다), `catalogs.json`의 다른 용도(템플릿 후보에는 안 쓰임). `strategist.md`의 문장은 Stage 1 필드 표의 "확정 방식" 칸이며 후보 추천 여부를 직접 말하지 않는다 |
| R-05 | C-01 `:340-346`, C-02 `:508-523`, `:2461-2500`, `generate-pptx.md:82`, `routing.md:103-116`, `references/confirm-surface.md:26` | `default_mode`를 정하는 기준은 문서 선언이다. 서버 코드는 `:342-346`에서 한 방향 검사만 한다. T-08로 확인. agent 판단의 정확성(명시적 의도 해석)은 확인할 코드가 없다 |
| R-06 | C-02 `server.py:511-530`, `:189-197` `_json_sha256` | 코드 읽기. T-04가 불일치 시 409를 확인 |
| R-07 | C-01 `server.py:310-378`, `:754-763` `_stage1_ready_error`, `:856-870` `_confirmation_launch_error` | T-08로 6가지를 실행 확인. `schema_version`이 `True`나 `1.0`일 때의 거부(`type(...) is not int`)와 `lang` 검사, 항목이 비어 있는 string일 때는 실행하지 않았다(코드만) |
| R-08 | C-02 `server.py:462-499`, `:246-300` `_template_kind_from_spec`, `:213-243` `_template_design_specs`, C-03 `:688-711`, `:2593-2628` | T-09로 3경우 실행 확인. 다중 kind 지정 root(qualified spec)의 후보 생성과 closure 검사는 코드만 읽었다 |
| R-09 | C-06 `app.js:4327-4348`, `:4206-4216` `stage1Payload`, `:1298-1330` `renderTemplateSelection`, `:26-27`(문구, en) | 소스를 읽었고 브라우저는 실행하지 않았다 |
| R-10 | C-04 `server.py:789-853`, C-05 `:2564-2640`, C-03 | T-02~T-04, T-10으로 실행 확인. 지정 root 일부 kind만 제출하는 경우(`_validate_explicit_root_closure`)와 `payload` 필드가 `mode`·`selection_keys` 외인 경우는 코드만 읽었다 |
| R-11 | C-05 `server.py:2741-2743`(쓰기 순서), `:2133-2167` `_wait_result_status`(stage1 선택 유효성 `:2139-2152`) | T-05로 wait exit 0 실행 확인. exit 2 분기는 코드만 읽었다(선행 R-07과 같음) |
| R-12 | C-03 `server.py:560-711`, C-04 `:834-853`, `scripts/docs/confirm_ui.md:164-221`(스키마 선언) | T-05로 실행 확인. 필드가 정확히 9개라는 것은 `_validate_template_selection`의 `expected_fields`(`:561-571`)에서 읽었다 |
| R-13 | `server.py:714-739` `_read_template_selection`, `scripts/apply_template.py:505-516` `validate_template_snapshot_sources` | 코드 읽기. root 원본을 고쳐 거부되는 경로는 실행하지 않았다 |
| R-14 | `apply_template.py:622-654`, `:460-502`, `:553-566`, `server.py:742-786`, 선행 `confirm-and-preview-ui.md` R-11·R-16 | T-06, T-07로 실행 확인 |
| R-15 | `scripts/register_template.py:1-45`(index 스키마 선언), `:1155-1282` `_extract_entry`, `:1342-1357` `_load_index`/`_write_index`, `:1423-1498` `main`, `workflows/create-template.md:13`, `:337-345`(Step 7), `server.py:424-441`(`summary`만 사용) | T-11로 `--dry-run` 실행 확인. 실제 등록(쓰기)은 레포 파일을 고치므로 실행하지 않았다. 등록 후 새 후보가 화면에 나타나는 것은 R-02·R-16의 코드 읽기로 추론한다 |
| R-16 | `server.py:381-450`, `register_template.py:1360-1368` `_enumerate_ids`; 번들 개수 비교(실행) | **부재 주장**: 검색 `grep -rn "_index.json" scripts --include=*.py`의 결과 중 템플릿 후보 발견에 쓰는 곳은 `confirm_ui/server.py`·`register_template.py`·`svg_quality/checker.py:9199`(주석)뿐이다. 개수 비교: brands 21/21, styles 14/14, layouts 7/7, decks 2/2, 미등록·누락 없음(`PYTHONUTF8=1 python` 일회성 스크립트). 번들이 아닌 환경의 index drift 때 전체 실패하는 동작은 코드만 읽었다. 놓쳤을 가능성: chat 분기에서 agent가 디렉터리를 `ls`하는 것은 코드가 아니라 문서 규칙(`routing.md:116`)만 막는다 |
| T-01~T-11 | 실행 기록(아래) | 임시 프로젝트 `scratchpad/projA`, `projB`, `x1`~`x9`, `y1`. 서버 프로세스를 띄우지 않았다(Flask test client) |

**실행 기록**

- 환경: `repos/ppt-master/.venv/Scripts/python`, `PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1`. 스크립트 `exp1.py`·`exp2.py`·`exp3.py`는 scratchpad(`C:\Users\SSAFY\AppData\Local\Temp\claude\888c4886f3bc297b\8d0fcf8a-9d1e-4d59-96fa-8e1e2deba01d\scratchpad`)에 있고, `server.create_app(<임시 프로젝트>)`의 test client로 `GET /api/recommendations`, `POST /api/confirm`을 호출했다. 확정 서버 프로세스(`--daemon`)는 띄우지 않았으므로 `--shutdown`이 필요한 것이 없다.
- CLI로 실행한 것: `server.py <projA> --wait-only --wait-stage stage1 --wait-timeout 5` → `confirmation stage=stage1 received`, `[NEXT] Stage 1 is intermediate ...`, exit 0(projB도 동일, 설치 전이라도 exit 0). `apply_template.py <projB> --root ...anthropic --root ...consulting-decision` → `[OK] installed 5 file(s)`, `[receipt] ...template_install.json`, exit 0. root 하나만 `--dry-run --skip-validation`으로 넘기면 `[ERROR] Selected roots or source bytes differ from the Stage-1 confirmation`, exit 1. `register_template.py anthropic --kind brand --dry-run` → exit 0, 현재 index와 동일.
- 부작용: `git -C repos/ppt-master status --short`는 실행 전후 모두 `?? .venv/`뿐이다. 실행 프로젝트 `projects/portfolio_demo_20261119`는 건드리지 않았다.
- 실행하지 않은 것: 실제 브라우저 렌더, `--daemon` 기동, 다중 kind 지정 root, `--wait-timeout` 124 경로, 실제 index 등록(쓰기), library root와 explicit root의 kind 충돌.

### 2.2 코드 읽는 순서 [선택]

`generate-pptx.md` Step 3 표 → `scripts/docs/confirm_ui.md`의 "Stage-1 template-selection sidecar contract"(선언) → `server.py` `_read_template_options_input`(C-01) → `_build_template_library`·`_build_template_options`(C-02) → `confirm`의 Stage 1 분기(C-05)와 `_resolve_template_confirmation`(C-04) → `_validate_template_selection`(C-03) → `apply_template.py` `apply_templates`(C-07). 화면 쪽은 `app.js`의 `initTemplateOptions`와 `templateSelectionValid`(C-06)만 보면 된다.

### 2.3 비교·재사용 출처 [선택]

없음. 이 스펙은 다른 레포의 같은 기능을 다루지 않는다. 같은 주제의 인접 스펙은 `confirm-and-preview-ui.md`(화면 수명과 파일 계약)와 `generate-default-pipeline.md`(Step 3·4 gate)이고, 이 스펙은 그 둘이 "경계만" 쓴 후보 목록의 출처와 선택 규칙을 채운다.

### 2.4 검토 기록 [필수, ready 스펙]

- 방식: 메인 점검. 작성자가 R-ID 대부분을 코드 읽기와 실행으로 직접 확인했고, 독립 검토(검토자 서브에이전트)는 하지 않았다.
- 대조한 R-ID: R-02, R-04, R-05, R-07, R-08, R-10, R-11, R-12, R-14, R-15, R-16(실행 확인과 줄 대조). 작성 직후 `server.py` 인용 줄과 `app.js:4327-4348`을 다시 열어 R-10의 오류 순서와 R-09의 제출 조건을 맞춰 봤다.
- 대조하지 않은 R-ID: R-01·R-03(문서 선언만), R-06(코드 읽기만), R-09(브라우저 미실행), R-13(코드 읽기만).
- 재구현: 미수행.
