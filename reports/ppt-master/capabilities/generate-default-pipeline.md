---
sha: "3af3e8ef774c4d67ee57e1306d9256d08c9ee1bf"
created: 2026-11-17
updated: 2026-11-17
sources:
  - skills/ppt-master/SKILL.md
  - skills/ppt-master/workflows/routing.md
  - skills/ppt-master/workflows/generate-pptx.md
  - skills/ppt-master/workflows/governance/failure-recovery.md
  - skills/ppt-master/references/artifact-ownership.md
  - skills/ppt-master/references/strategist.md
  - skills/ppt-master/references/executor-base.md
  - skills/ppt-master/references/confirm-surface.md
  - skills/ppt-master/templates/design_spec_reference.md
  - skills/ppt-master/templates/spec_lock_reference.md
  - skills/ppt-master/templates/schemas/design_spec.schema.json
  - skills/ppt-master/templates/schemas/spec_lock.schema.json
  - skills/ppt-master/scripts/docs/project.md
  - skills/ppt-master/scripts/project_manager.py
  - skills/ppt-master/scripts/project_management/cli.py
  - skills/ppt-master/scripts/project_management/project_specs.py
  - skills/ppt-master/scripts/project_utils.py
  - skills/ppt-master/scripts/attribution_guard.py
  - skills/ppt-master/scripts/console_encoding.py
  - skills/ppt-master/scripts/source_to_md.py
  - skills/ppt-master/scripts/total_md_split.py
  - skills/ppt-master/scripts/finalize_svg.py
  - skills/ppt-master/scripts/slide_roster.py
  - skills/ppt-master/scripts/apply_template.py
  - skills/ppt-master/scripts/confirm_ui/server.py
  - skills/ppt-master/scripts/svg_quality/cli.py
  - skills/ppt-master/scripts/svg_quality/checker.py
  - skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py
  - skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py
  - skills/ppt-master/scripts/svg_to_pptx/pptx_package/discovery.py
depends: []
status: ready
---

# Default 생성 파이프라인 (공유 계약 C1·C2 포함)

> 사용자가 소스나 주제를 주면, agent가 `SKILL.md`·workflow 문서를 읽고 Step 1~7(소스 변환 → 프로젝트 초기화 → 템플릿 후보 준비 → Strategist 2단계 확정과 설계 문서 → 이미지 확보 → 페이지별 SVG 작성 → 후처리·내보내기)을 스크립트와 함께 실행해 `exports/*.pptx`를 만드는 경로이다. 이 문서는 단계 경계, 단계마다의 입출력 파일, 사용자 확정 gate, 실패 시 복귀 지점, 그리고 모든 단계가 공유하는 프로젝트 디렉터리(C1)와 `design_spec.md`/`spec_lock.md`(C2)의 계약을 쓴다.

<!--
읽는 법
- 이 스펙의 목적은 agent 환경에 이 파이프라인을 연동하거나 일부를 차용하는 것이다. Strategist·Executor 프롬프트 본문(`references/*.md`)은 풀어 쓰지 않고, 파이프라인이 그 문서에 기대하는 입력·출력만 쓴다. 본문은 C-ID와 2.2로 안내한다.
- 검증 수준 `코드 확인(문서 선언)`은 "문서를 직접 읽어 그렇게 선언돼 있음을 확인했다. agent가 따라야 하는 규칙이고 스크립트가 강제하지 않는다"는 뜻이다. 스크립트 동작은 `코드 확인`만 쓴다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

1. **진입**: agent가 `SKILL.md`를 읽고 `attribution_guard.py`를 실행한다(실패하면 skill 중단). `routing.md`로 경로를 하나 고르고, 일반 Generate이면 `workflows/generate-pptx.md`만 읽는다(1.3.1).
2. **Plan (Step 1~5)**: 소스를 Markdown으로 바꾸고(Step 1), `projects/<name>_<date>/`를 만들어 소스를 가져오고(Step 2), 템플릿 후보를 내부적으로 준비한다(Step 3). Strategist 단계(Step 4)에서 사용자가 Stage 1(소통 계약 + 템플릿/자유 디자인)과 Stage 2(전체 해결안 + 제작 옵션)를 ⛔ 확정하면, agent가 `design_spec.md`(I~X절)와 `spec_lock.md`를 쓰고 `project_manager.py validate`를 돌린다. §VIII에 확보할 이미지가 있으면 Step 5가 이미지를 확보한다.
3. **Do·Check·Act (Step 6)**: agent가 live preview를 띄우고 §IX 순서대로 페이지마다 SVG를 `svg_output/`에 직접 쓴다. 5번째 페이지 뒤에 early gate, 전체 완성 뒤에 final gate(`svg_quality_checker.py`)를 통과해야 한다. 노트가 켜져 있으면 `notes/total.md`를 쓴다.
4. **Step 7**: 노트가 켜져 있으면 `total_md_split.py`로 `notes/<SVG 이름>.md`를 만들고, `finalize_svg.py`로 `svg_final/` 미리보기를 만들고, `svg_to_pptx.py`로 `exports/<name>_<timestamp>.pptx`와 검증 보고서를 만든다. 내보내기는 `svg_output/`만 읽고, 통과한 final 보고서가 없으면 거부한다.
5. **개정**: 전달 뒤 수정 요청은 계획으로 돌아가지 않고 소유 층(SVG → §IX → notes)을 고친 뒤 final gate와 Step 7을 다시 돌린다. 이전 내보내기는 남고 새 파일이 새 timestamp로 생긴다.
6. **실패**: 필수 산출물이 실패하면 다음 gate가 막히고, 소유 단계로 돌아가 거기서부터 다시 한다(1.3.3의 실패 표). 편의 기능(확인 화면, live preview)의 실패는 막지 않고 chat이나 생략으로 대체한다.

### 1.2 범위·통합 지점 [필수]

- **제공**: 소스·주제 → 최종 `.pptx` 한 벌까지의 단계 순서, gate와 주체(AI/스크립트/사용자) 구분, 단계별 입출력 파일, 실패 시 복귀 지점. 공유 계약 C1(프로젝트 디렉터리 레이아웃)과 C2(`design_spec.md`/`spec_lock.md`의 역할과 일관성 검사). 1행(진입·경로 선택) 규칙.
- **제외와 경계** (이 스펙은 아래의 내부를 쓰지 않고, 무엇을 넘기고 받는지만 정의한다):

| 제외 | 이 파이프라인이 넘기는 것 | 이 파이프라인이 받는 것 |
|---|---|---|
| Quick, Image to PPTX, Beautify 중 Quick을 고른 경우 | 없음. `routing.md`가 이 경로를 고르면 `generate-pptx.md`를 읽지 않는다(R-04) | 없음. Beautify가 Quick을 고르지 않으면 이 파이프라인으로 들어오고, 그 profile 고유 규칙은 이 스펙 밖이다 |
| Create Template | 없음(템플릿 만들기는 별도 경로) | 현재 대화에서 넘어온 exact workspace root 경로. Step 3 후보, Step 4 Stage 1 선택지, `apply-template-workspace` 설치 입력이 된다(R-15, R-18) |
| Edit Native PPTX | 없음. "PPTX를 그대로 두고 수정"은 다른 경로(R-05) | 없음. "PPTX를 재디자인"은 PPTX를 소스로 받아 이 경로로 들어온다(Step 1·2의 PPTX intake) |
| 내레이션/TTS (`generate-audio`) | 내보낸 deck, `notes/`, `design_spec.md §I`의 Narration Audio 결과 | 이 파이프라인의 마지막 항목이 "Narration Audio가 켜졌으면 `generate-audio` 실행"으로 넘긴다(R-48) |
| 이미지 확보 내부 (Step 5) | 확보할 행(`design_spec.md §VIII`)과 `spec_lock.md images`, 확정된 AI 이미지 경로 | `images/` 아래 파일, `image_prompts.json`/`image_queries.json`/`image_sources.json`, 갱신된 `analysis/image_analysis.csv`. 모든 행이 terminal 상태(R-30) |
| 확인·미리보기 화면 내부 (`confirm_ui`, `svg_editor`, `spec_review`) | `recommendations.stage1/2.json`, 서버 시작 명령 | `template_selection.json`, `result.json`(사용자 receipt). live preview는 Step 6에서 곁가지로 시작만 하고, 제출된 annotation은 Step 7 이후에 적용한다(R-41) |
| SVG 작성 규칙과 품질 검사 | `design_spec.md`, `spec_lock.md`, `images/`, `icons/`, `templates/` | `svg_output/*.svg`, `validation/svg_quality_report.json`(final, 0 error), early 보고서(R-36) |
| `svg_to_pptx` 변환 내부 | 프로젝트 경로, 플래그(R-46) | `exports/*.pptx`, `validation/<exports 파일 stem>.report.json`, `backup/<timestamp>/svg_output/`(R-47) |
| `attribution_guard` 판정 내부 | 없음 | 종료 코드 0이면 진행, non-zero이면 skill 중단(R-01, R-02) |

- **외부 의존·선행 계약**: 선행 스펙 없음. agent가 `SKILL_DIR`(이 `SKILL.md`가 있는 디렉터리의 절대경로)을 호스트에서 받아 매 명령에서 펼친다(R-03). 외부 의존은 Python 3과 각 스크립트의 의존 패키지, (Step 5 조건부) 이미지 API·검색 provider, 사용자 브라우저(확인 화면). 이 스펙은 실행해 보지 않았다.
- **소유 상태·부작용**: 프로젝트 디렉터리 하나(`projects/<name>_<date>/`, C1)를 만들고 그 안에서만 쓴다. `svg_final/`은 `finalize_svg.py`를 돌릴 때마다 통째로 교체된다(R-45). `exports/`와 `backup/`은 쌓이기만 하고 지워지지 않는다(R-47). `validation/workflow.log`는 append-only 감사 로그이고 생성 중에는 읽지 않는다(R-11).

### 1.3 인터페이스와 데이터 의미 [필수]

#### 1.3.1 경로 선택 (1행)

`SKILL.md`의 Mandatory Load Order(`SKILL.md:25-57`)와 `routing.md`의 선택 규칙(`routing.md:13-63`)을 짧게 옮긴 것이다. 로드 순서는 (1) `SKILL.md` 읽기 → (2) `python3 "${SKILL_DIR}/scripts/attribution_guard.py"` → (3) `routing.md` 읽기 → (4) 최상위 경로 하나와 활성 profile 선택 → (5) 선택된 runtime authority와 명시적으로 트리거된 보조 문서만 읽기이다.

| 최상위 경로 | 요청 모양 | Runtime authority | 이 스펙 |
|---|---|---|---|
| Generate PPTX | 소스·주제로 새 deck을 만들거나 보이는 디자인을 재생성 | 일반: `workflows/generate-pptx.md`(Default). 명시적 Quick: `profiles/quick-generate.md`. Image to PPTX: `profiles/image-to-pptx.md`(항상 Quick). Beautify: `profiles/beautify-pptx.md`(명시적 Quick이면 Quick, 아니면 Default) | **일반 Default와 Beautify의 Default만** 본문 |
| Create Template | 재사용 brand/style/layout/deck 템플릿 만들기 | `workflows/create-template.md` | 제외 |
| Edit Native PPTX | 기존 PPTX의 네이티브 디자인을 유지한 채 채우기·수정 | `workflows/edit-native-pptx.md` | 제외 |

Default에 남는 요청 조건(`routing.md:41-58`): 주제만 있거나 소스에 사실 공백이 있으면 `topic-research`를 Step 1 안에서 실행. PPTX를 split·merge·re-outline으로 재디자인하면 PPTX를 소스로 보고 Default(명시적 Quick 의도가 없는 한). 미리보기·선택·annotation 요청은 Default + `live-preview`(Quick + 미리보기 의도도 Default로 되돌아온다). 페이지 전환·자동 진행·deck 전체 애니메이션은 `references/animations.md`의 내보내기 수준 계약으로 처리하고 Step 7.3 플래그로 반영한다. 기존 PPTX의 페이지를 재디자인 없이 빼거나 순서만 바꾸는 요청은 Generate가 아니라 Edit Native PPTX다.

#### 1.3.2 단계별 주체 (AI / 스크립트 / 사용자)

"AI"는 레포 밖에서 `SKILL.md`·workflow 문서를 읽고 따르는 agent다. 아래 표의 "사용자" 열에 ⛔가 있는 곳만 agent가 멈추고 사용자의 명시적 확정을 기다린다.

| 단계 | AI(agent)가 하는 일 | 스크립트가 하는 일 | 사용자가 하는 일 |
|---|---|---|---|
| 0 진입 | 문서 읽기, 경로 선택, guard 실행 결과 판단 | `attribution_guard.py`가 종료 코드로 응답 | 요청과 소스 제공 |
| 1 소스 변환 | 직접 읽을 소스와 변환할 소스 구분, 사실 공백이면 `topic-research` | `source_to_md.py`가 PDF·DOCX·XLSX·PPTX·EPUB·HTML·LaTeX·URL을 Markdown과 conversion profile로 변환 | — |
| 2 프로젝트 초기화 | `init`, `import-sources` 명령 실행, 출력의 `skipped` 읽기 | `project_manager.py init`이 디렉터리 생성, `import-sources`가 소스 보관·변환·PPTX intake·이미지 복사 | — |
| 3 템플릿 후보 준비 | UI 분기면 `template_options`를 `recommendations.stage1.json`에 담고, chat 분기면 컨텍스트에 보관 | — (서버가 나중에 index를 읽음) | — (눈에 보이는 정지 없음) |
| 4 Strategist | Stage 1 권장안, Stage 2 해결안 3개와 제작 옵션 작성, 설치된 템플릿 검토, `design_spec.md`·`spec_lock.md` 작성과 Gate 1·2 감사, `icon_sync.py` 실행 | `confirm_ui/server.py`(화면, `template_selection.json`·`result.json` 기록), `apply-template-workspace`(템플릿 설치), `project_manager.py validate` | **⛔ Stage 1 확정, ⛔ Stage 2 확정**, (옵션) 완성된 spec 검토 승인 |
| 5 이미지 (조건부) | 행별 프롬프트·검색어 작성, 웹 후보 선택(비전 가능 시), 자동화 소진 시 사용자에게 선택지 제시 | `image_gen.py`, `image_search.py`, `slice_images.py`, `image_treat.py`, `analyze_images.py` | **⛔ 자동화 소진 시** 복구 재시도·수동 생성·취소 중 선택, 수동 파일 제공 |
| 6 Executor | Design Parameter 확인 출력, 페이지별 SVG 직접 작성, 검사 위반 수정, 노트(`notes/total.md`) 작성 | `text_measure.py calibrate`, `svg_editor/server.py --live`(곁가지), `svg_quality_checker.py`(early·final) | (옵션) 시각 검토 요청, live preview 열람 |
| 7 내보내기 | 명령 실행, 경고 보고 | `total_md_split.py`, `finalize_svg.py`, `svg_to_pptx.py` | **⛔ 수동 이미지 파일이 필요하면** 파일 제공 |
| 개정 | 수정할 층을 정해 고침 | 같은 검사·변환 재실행 | 수정 요청 |

#### 1.3.3 단계별 입력·출력·선행 조건·실패 복귀

선행 조건은 각 Step의 🚧 GATE이고, 실패 복귀는 `failure-recovery.md`의 표(`:15-43`)와 resume pointers(`:71-86`)를 단계별로 모은 것이다. 파일 위치는 C1(1.3.5)이다.

| 단계 | 선행 조건 | 입력 | 출력·성공 기준 | 실패하면 |
|---|---|---|---|---|
| 1 | 사용자가 주제나 원하는 결과와 가용한 초기 자료를 줬다 | 소스 파일·URL·디렉터리, 주제 | `<stem>.md`, `<stem>.conversion_profile.json`, 자산 폴더 `<stem>_files/`(`image_manifest.json`). 주제만이면 `topic-research` 결과 쌍(Markdown + facts JSON) | 변환 실패는 그 입력이 없는 것으로 보고 다음 단계로 간다(`import-sources`가 다시 변환을 시도할 수 있음, R-14) |
| 2 | Step 1 끝 | 프로젝트 이름, (선택) `--format`, 소스 경로 + Step 1이 쓴 Markdown | 프로젝트 디렉터리와 `sources/`, `images/`, `analysis/` 채움. `validation/workflow.log` | 이미 있는 디렉터리면 `init`이 오류 종료. `import-sources`는 사용 가능한 결과가 하나도 없으면 exit 1 |
| 3 | Step 2 끝 | 템플릿 index 4개(`brands/styles/layouts/decks_index.json`), 사용자가 준 exact root | UI: `confirm_ui/recommendations.stage1.json`의 `template_options`. chat: 컨텍스트 상태. 선택·검증·설치는 하지 않음 | — |
| 4 | Step 1~3 끝, Stage 1 시작 전 | `references/strategist.md`·`plan-core.md`·`canvas-formats.md`, `analysis/`의 구조화 사실, `sources/` content 파일, 사용자 이미지(`analyze_images.py` 후 CSV) | `design_spec.md`, `spec_lock.md`(+ 내레이션 분기만 `notes/total.md`), 템플릿 설치 시 `templates/`, `icons/` 풀, `validate` 통과 | 확정 없음 → 멈춤. Gate 1·2 불일치 → 해당 파일 재작성. `validate` 오류 → 파일 수리(R-20~R-22) |
| 5 | Step 4 끝, `design_spec.md`·`spec_lock.md` 존재 | §VIII 행 | `images/` 파일, 필요한 `image_*.json`, 모든 행 terminal, 갱신된 `analysis/image_analysis.csv` | 두 파일이 없으면 Step 5 시작 전에 `failure-recovery.md` §3 resume 표로. AI 소진 → 사용자 3택(R-30) |
| 6 | Step 4(와 Step 5) 끝 | `design_spec.md`, `spec_lock.md`, `images/`, `icons/`, `templates/`, `references/executor-base.md` 등 | `svg_output/*.svg` 전부, `validation/svg_quality_report.json`(final, error 0), 켜졌으면 `notes/total.md` | checker error → 한 번의 통합 수정 후 재검사. 설계 정보 부족 → Step 4 Gate 1/2로 돌아가 해당 조각만 수리(R-40) |
| 7 | Step 6의 모든 gate 통과, final 보고서 0 error, 노트가 켜졌으면 `notes/total.md`가 모든 페이지를 덮음 | `svg_output/`, `notes/`, `images/`, `icons/`, final 보고서 | 7.1: `notes/<stem>.md`. 7.2: `svg_final/`. 7.3: `exports/<name>_<timestamp>.pptx`, `validation/<exports 파일 stem>.report.json`(stem에 `_native_charts_tables`·`_narrated`·`_kiosk` 접미사와 `-o` 지정 이름이 그대로 반영됨), `backup/<timestamp>/svg_output/` | 소유 원본(SVG·notes·assets)을 고치고 실패한 하위 단계부터 재실행. 계획은 원본이 바뀌지 않으면 다시 하지 않는다(R-43, R-50) |

#### 1.3.4 CLI 계약

명령 이름과 옵션은 외부 계약이므로 원문 그대로 쓴다. 모든 명령은 `${SKILL_DIR}/scripts/` 아래이고, 하위 모듈은 호출하지 않고 wrapper만 부른다.

| 명령 | 입력 | 종료 코드·출력 | 비고 |
|---|---|---|---|
| `attribution_guard.py` (인자 없음) | — | 성공 0. 실패는 stderr에 일반 메시지 하나를 쓰고 **78** | 대부분의 스크립트가 시작할 때 같은 검사를 자동 호출한다(R-01) |
| `source_to_md.py <입력...> [-t <type>] [-o <path>] [--json]` | 파일·URL·디렉터리 | 변환 결과를 `<입력 stem>.md`(기본: 입력 옆)와 profile 옆에 씀. `-o`는 출력 파일(입력 1개) 또는 디렉터리(디렉터리가 있거나 `/`로 끝날 때) | `-t`는 자동 감지가 모호할 때만 |
| `project_manager.py init <name> [--format <key>] [--dir <base>] [--quick-generate]` | 이름 | 성공 0 + `[OK] Project initialized: <path>`. 실패는 `[ERROR] ...` + 1 | `--quick-generate`는 이 스펙 밖 |
| `project_manager.py import-sources <project_path> <소스...> [--no-image-propagation] [--move\|--copy]` | 경로·디렉터리·URL | 사용 가능한 결과가 하나라도 있으면 0, 없으면 `[ERROR] No usable sources imported` + 1. 요약(archived/markdown/assets/images/analysis/notes/skipped)을 출력 | `--move`와 `--copy`는 상호 배타. Generate는 기본(이미지 전파) 사용 |
| `project_manager.py validate <project_path>` | 프로젝트 경로 | error가 없으면 0(경고만 있어도 0), error가 있으면 `[ERROR] Project structure is invalid.` + 1 | 검사 범위는 R-24·R-25 |
| `confirm_ui/server.py <project> --daemon` / `--wait-only [--wait-stage stage1\|final]` / `--shutdown` | 프로젝트 경로 | `--wait-only`는 해당 `result.json` stage가 쓰이면 0, 준비 오류나 서버 종료는 1, stage 건너뜀·Stage 1 영수증 오류는 **2**(`server.py:2152`, `:2166`), 기본 590초(`--wait-timeout`) 안에 안 오면 **124**(`server.py:2128`). 최종 `--wait-only`는 stage2 파일과 설치가 준비되지 않았으면 기다리지 않고 즉시 1이다(confirm-and-preview-ui R-08) | 서버 내부는 별도 스펙 |
| `analyze_images.py <project_path>/images` | `images/` | `analysis/image_analysis.csv`를 재생성 | 파생 view이며 저장소가 아님 |
| `text_measure.py calibrate <project_path> --outline` | 프로젝트 | `validation/text_calibration.json` 기록, role별 보정표 출력 | Step 6, 첫 페이지 전 |
| `svg_editor/server.py <project_path> --live --daemon` | 프로젝트 | 곁가지 서버. URL은 출력이나 `live_preview/lock.json` | 기본 포트는 6060부터 빈 포트 |
| `svg_quality_checker.py <project_path> --canonical-authoring --stage early\|final --json` | 프로젝트 | `--json`이면 `validation/svg_quality_early_report.json` 또는 `validation/svg_quality_report.json`을 씀. 보고된 error가 1개 이상이면 exit 1, 아니면 0 | 규칙 내용은 별도 스펙 |
| `total_md_split.py <project_path>` | 프로젝트 | 성공 0. 아래 R-44의 실패는 1 | |
| `finalize_svg.py <project_path>` | 프로젝트 | 성공 0, 실패 1(`svg_final/`은 발행되지 않음) | |
| `svg_to_pptx.py <project_path> [--no-notes] [--native-charts-and-tables] [--image-sizing display] [-a ...] [--no-animations]` | 프로젝트 | 성공 0. final 보고서 gate 실패나 postflight 실패는 1 | 플래그 선택은 R-46 |

#### 1.3.5 C1. 프로젝트 디렉터리 레이아웃

`project_manager.py init`이 만드는 것(`cli.py:348-366`)은 `svg_output/`, `svg_final/`, `images/`, `icons/`, `notes/`, `templates/`, `live_preview/`, `sources/`, `analysis/`, `validation/`, `exports/` 11개 디렉터리와 `README.md`다. 아래 표의 "근거 수준"에서 `코드 확인`은 만드는 코드를 읽은 것, `문서 선언`은 `artifact-ownership.md`·workflow 문서의 선언만 읽은 것이다. 파일 정렬은 파일명의 숫자 구간을 숫자 값으로 비교한다(`slide_roster.py:27-47`, C-14).

| 항목 | 만드는 주체와 시점 | 읽는 단계 | 근거 수준 |
|---|---|---|---|
| 프로젝트 루트 `projects/<name>_<YYYYMMDD>/` | `init`(Step 2) | 모든 단계 | 코드 확인 |
| `README.md` | `init`(Step 2) | 아무것도 읽지 않는다(`validate`가 없으면 경고만 냄) | 코드 확인 |
| `sources/` | `init`이 디렉터리를, `import-sources`가 내용(원본 보관본, 변환된 `<stem>.md`, `*.conversion_profile.json`, `*_files/`와 그 `image_manifest.json`)을 채움(Step 2). `topic-research`의 `*.facts.json`도 파일로 가져옴 | Step 4(content 파일을 Strategist가 읽음). Step 6은 검증용으로만 | 디렉터리·채움: 코드 확인. 읽기 규칙: 문서 선언 |
| `analysis/` | `init`이 디렉터리, `import-sources`가 PPTX 소스의 `<stem>.identity.json`·`<stem>.slide_library.json`·`source_profile.json`을 씀(`cli.py:504-519`), `analyze_images.py`가 `image_analysis.csv`를 씀(`analyze_images.py:486`) | Step 4(`source_profile.json`의 `decks[]`, CSV를 §VIII 전에), Step 6(이미지 inventory) | 위치·생성: 코드 확인. 읽기 규칙: 문서 선언 |
| `images/` | `init`이 디렉터리. 채우는 쪽은 `import-sources`(직접 준 비트맵과 변환 자산 전파, `image_manifest.json` 병합), Step 5(ai·web·slice), 템플릿 설치(`images/` 포함) | Step 4(CSV 경유), Step 6(`<image href>`), Step 7.2(임베드) | 코드 확인(import), 문서 선언(Step 5·템플릿) |
| `images/image_prompts.json`·`image_prompts.md`·`image_queries.json`·`image_sources.json` | agent와 `image_gen.py`·`image_search.py`(Step 5, 해당 경로가 트리거될 때만) | Step 5 안과 final 검사 | 문서 선언. 형식은 image-file-contract 스펙 |
| `icons/` | `init`이 디렉터리, agent가 `icon_sync.py <project_path> <lib/name>...`으로 채움(Step 4, §VI·lock을 쓸 때) | Step 6(페이지에서 참조), Step 7.2(임베드), 검사·내보내기 | 디렉터리: 코드 확인. 채움: 문서 선언 |
| `templates/` | `init`이 빈 디렉터리, `apply-template-workspace`가 Stage 1 확정 뒤 `design_spec.<kind>.<id>.md`와 구조 SVG roster, 자산을 설치(Step 4). 자유 디자인이면 비어 있음 | Step 4 Stage 2, Step 6(mirror·layout 경로) | 디렉터리: 코드 확인. 설치: 문서 선언 |
| `template_install.json` (프로젝트 **루트**) | 설치기가 씀(`apply_template.py:473-474`, `:568`). 문서는 confirm_ui 파일과 함께 나열하지만 코드 위치는 루트다 | `confirm_ui` 서버가 Stage 2 전에 검증(`server.py:742-751` `_read_template_installation`→`apply_template.read_template_install`. `:1868`은 세션이 이 파일 버전을 표시하는 곳) | 코드 확인 |
| `confirm_ui/` | `init`이 만들지 않는다. agent가 `recommendations.stage1.json`·`recommendations.stage2.json`을 쓰고 서버가 `template_selection.json`·`result.json`·`session.json`을 씀(`server.py:80-95`, `:937`). 잠금 파일 `.confirm_ui.lock`은 프로젝트 루트 | Step 4만. `result.json`은 최종 값을 한 번만 읽어 설계 문서로 옮긴다 | 코드 확인(파일 이름·소유), 문서 선언(읽기 횟수) |
| `design_spec.md`, `spec_lock.md` (프로젝트 루트) | agent(Strategist, Step 4)가 각각 한 번에 완성본으로 씀 | Step 4(검증), Step 5(§VIII), Step 6(Executor), Step 7(노트 정책) | 위치·이름: 코드 확인(`project_utils.py:90-95`, `project_specs.py:1441`). 작성 주체: 문서 선언 |
| `live_preview/` | `init`이 디렉터리, `svg_editor` 서버가 `lock.json`, `server.log`, `edits.jsonl`, `annotations.jsonl`을 씀 | Step 6 이후(annotation은 Step 7 뒤에 읽음) | 디렉터리·`lock.json` 이름: 코드 확인. 나머지: 문서 선언 |
| `svg_output/` | `init`이 디렉터리, agent(Executor)가 페이지마다 SVG 한 개를 씀(Step 6). 이름은 `<index>_<page_name>.svg`이고 roster 전체가 같은 0 채움 폭을 쓴다 | final 검사, `total_md_split`, `finalize_svg`, 내보내기, `backup/`. 내보내기가 읽는 유일한 페이지 원본 | 위치: 코드 확인. 이름 규칙: 문서 선언(`executor-base.md:329-331`). `validate`는 `^(slide_\d+_\w+\|P?\d+_.+)\.svg$`가 아니면 경고(`project_utils.py:683`) |
| `notes/total.md` | agent(Step 6 Logic Construction), 노트가 켜졌을 때만. 내레이션 분기는 Gate 2 직후 Step 4에서 | Step 7.1 | 문서 선언 |
| `notes/<SVG 이름>.md` | `total_md_split.py`(Step 7.1) | `svg_to_pptx.py`가 notes를 켠 채 실행될 때 `find_notes_files`가 읽음 | 코드 확인(`total_md_split.py:257`, `discovery.py:61-106`) |
| `svg_final/` | `finalize_svg.py`(Step 7.2)가 `svg_output/`를 복사·가공해 디렉터리를 **통째로 교체**(R-45) | 내보내기는 읽지 않는다. 사람이 미리보기로 열 수 있음 | 코드 확인 |
| `validation/workflow.log` | `init`이 첫 기록을 쓰고(`cli.py:1412`), 이후 프로젝트 인자를 가진 Python 도구가 자동 기록. agent가 `workflow_log.py`로 수동 메모 | 생성 중에는 읽지 않는다(사용자가 요청한 감사 때만) | 코드 확인(첫 기록), 문서 선언(읽기 금지) |
| `validation/text_calibration.json` | `text_measure.py calibrate`(Step 6, 첫 페이지 전) | Step 6 페이지 작성 | 코드 확인(`text_measure.py:756`) |
| `validation/svg_quality_early_report.json`, `validation/svg_quality_report.json` | `svg_quality_checker.py --json`(Step 6) | final 보고서는 `svg_to_pptx.py`가 `svg_output/`의 fingerprint와 맞춰 봄 | 코드 확인(`svg_quality/cli.py:89-110`, `pptx_package/cli.py:3160-3185`) |
| `validation/<exports 파일 stem>.report.json` | `svg_to_pptx.py`의 postflight(Step 7.3) | agent가 `[POSTFLIGHT]` 요약을 읽고 경고를 알림 | 코드 확인(`pptx_package/cli.py:3917-3948`) |
| `exports/<name>_<YYYYMMDD_HHMMSS>[_native_charts_tables][_narrated][_kiosk].pptx` | `svg_to_pptx.py`(Step 7.3). `<name>`은 디렉터리 이름에서 `_<date>`와 `_<format>`을 뺀 이름 | 사용자 | 코드 확인(`pptx_package/cli.py:2683-2712`, `project_utils.py:111-168`) |
| `backup/<timestamp>/svg_output/`(그리고 있으면 `templates/native_payloads` 저장소 파일을 같은 상대 경로로) | `svg_to_pptx.py`가 성공했을 때, `-o`나 `output` 외 `-s`를 쓰지 않은 기본 실행에서만(`-s output`은 기본으로 취급됨) | 재내보내기 원본 보관용 | 코드 확인(`pptx_package/cli.py:2712`, `:3884-3913`) |
| `animations.json` (프로젝트 루트, 선택) | agent의 `customize-animations` 단계(조건부, 이 스펙 밖) | `svg_to_pptx.py`가 사이드카로 읽음 | 문서 선언 |

#### 1.3.6 C2. `design_spec.md`와 `spec_lock.md`

두 파일은 같은 결정을 두 가지 독자에게 보여 주는 계약이다. 필드 전체는 옮기지 않고 위치만 안내한다(C-05, C-06).

| | `design_spec.md` | `spec_lock.md` |
|---|---|---|
| 역할 | 사람이 읽는 전체 결정: 의도, 페이지별 brief(§IX), 근거, 자원, 제작 옵션. 이후 단계는 `result.json`이 아니라 이 파일을 읽는다 | 기계가 읽는 실행 앵커와 라우팅: 색·타이포 role, 아이콘, 이미지 행, 페이지 리듬, 구조 모드. 페이지 로컬 값은 넣지 않는다 |
| 누가·언제 쓰나 | Strategist(agent)가 최종 확정을 한 번 소비해 `design_spec_reference.md`를 읽고 §I~§X 전체를 한 번에 씀(Step 4 Gate 1) | Strategist가 감사를 통과한 `design_spec.md`와 컨텍스트로 `spec_lock_reference.md`를 읽고 한 번에 씀(Step 4 Gate 2, refine 승인 뒤) |
| 누가 읽나 | Step 5(§VIII 행), Step 6 Executor(§IX가 페이지 roster와 문구의 권위), Step 7(노트 정책 §X), 검사기(§IX roster·`Audience move`) | Executor(컨텍스트당 한 번 전체를 읽고, 5페이지마다 한 번 다시 읽음), Step 5(`images`), 검사기와 내보내기(구조 모드) |
| 절·섹션 | 첫 줄 `<!-- ppt-master-schema: design-spec/v1 -->`. I Project Information, II Canvas Specification, III Visual Theme, IV Typography System, V Layout Principles, VI Icon Usage Specification, VII Visualization Reference List(조건부), VIII Image Resource List, IX Content Outline(`Slide NN` 블록마다 `Audience move`와 `Relationships` 필수), X Speaker Notes Requirements. §I에 Speaker Notes·Custom Animations·Narration Audio의 효과 결과와 출처, Page Count, Generation Mode, Spec Refinement가 있다 | 첫 줄 `<!-- ppt-master-schema: spec-lock/v1 -->`. 필수: `canvas`, `communication`, `mode`, `visual_style`, `colors`, `typography`, `icons`, `page_rhythm`(행마다 `P<NN>: anchor\|dense\|breathing`), `forbidden`. 선택: `images`, `pptx_structure`와 구조 4섹션, `page_visualizations`, `page_charts`(`spec_lock.schema.json`의 `sections`, 검토자 확인) |
| 이 파일에만 있는 것 | 페이지 문구·구성, `Fact IDs`, 제작 옵션 3개(notes·animations·narration)의 효과 결과 | `forbidden`의 사용자 금지 규칙(원문 인용 + `(user)`). 제작 옵션 3개는 lock에 넣지 않는다 |
| 일관성의 소유자 | `validate`는 구조만 본다. 확정값 → 설계 문서 일치(Gate 1)와 설계 문서 → lock 일치(Gate 2)는 agent의 감사이고 스크립트가 아니다(R-24, R-25) | 같음 |

`validate`가 실제로 확인하는 것(코드 확인, R-24): 두 파일의 schema marker, 필수 섹션의 존재·순서·중복, `[fill...]` placeholder 잔존, §I Page Count = §IX `Slide` 블록 수, 각 `Slide` 블록의 `Audience move`·`Relationships`, §VIII가 `ai` 행을 가지면 §III `AI Image Strategy` 하위 제목, lock의 enum·페이지 키 형식·custom 참조 id·이미지 값 문법·`forbidden`의 `(user)` 태그, lock 내부 참조(`pptx_layouts` 소스, structured일 때 페이지 매핑 키가 `page_rhythm` 키와 같음, `page_visualizations` 페이지가 `page_rhythm`에 있음, 시각화 SVG 자산 존재), 디렉터리 이름에 등록 포맷이 있을 때 lock의 `canvas.format`·`viewBox`가 그것과 같음. 확인하지 않는 것은 R-25.

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 어떤 스크립트든 시작할 때 integrity 검사가 실패 | 이 파이프라인이 부르는 모든 명령(`source_to_md.py`, `project_manager.py`, `confirm_ui/server.py`, `analyze_images.py`, `image_gen.py`, `image_search.py`, `slice_images.py`, `text_measure.py`, `svg_editor/server.py`, `svg_quality_checker.py`, `total_md_split.py`, `finalize_svg.py`, `svg_to_pptx.py`, `workflow_log.py`)가 시작할 때 같은 검사를 호출하고(`configure_utf8_stdio()`를 부르는 파일이 tests 제외 96개), 실패하면 stderr에 일반 메시지 하나를 쓰고 exit 78(`attribution_guard.py`의 `require_skill_integrity`). 추가로 별도의 두 번째 신원 검사도 실패하면 메시지 없이 exit 78(`console_encoding.py`). 판정 조건은 이 스펙 밖 | 코드 확인 |
| R-02 | agent가 Mandatory Load Order 2번에서 `attribution_guard.py`를 실행해 non-zero를 받음 | 즉시 skill을 중단한다. 검사를 들여다보거나 고치거나 우회하지 않는다. Windows에서 `python3`가 시작조차 안 되면(출력 없는 exit 9009) guard 결과가 아니므로 `python`으로 다시 실행한다 | 코드 확인(문서 선언) |
| R-03 | agent가 어떤 경로를 만들 때 | 호스트가 준 `SKILL_DIR` 절대경로를 유지하고 호출마다 `${SKILL_DIR}`를 펼친다. `skills/ppt-master/` 접두사는 `SKILL_DIR`로 바꾼다. `cd`·CWD·레포 checkout 가정 금지. 사용 가능한 값이 없으면 묻고, 찾거나 추측하지 않는다 | 코드 확인(문서 선언) |
| R-04 | 요청이 일반 Generate이거나 명시적 Quick 의도가 없는 Beautify | `workflows/generate-pptx.md` 하나만 runtime authority로 로드한다. 명시적 Quick은 `quick-generate.md`를 로드하고 `generate-pptx.md`는 로드하지 않으며, Default는 `quick-generate.md`를 로드하지 않는다. Image to PPTX와 Beautify는 상호 배타이고 둘의 runtime을 함께 로드하지 않는다. 선택 뒤 다른 최상위 경로의 절차를 로드하지 않는다 | 코드 확인(문서 선언) |
| R-05 | 요청이 `routing.md` §2·§3의 한 행에 맞음 | 경로 선택 질문을 하지 않는다(route-choice menu 금지). 기존 deck 요청이 모호할 때만 "보이는 디자인을 재생성(Generate)인가, 네이티브 deck을 유지하며 수정(Edit Native PPTX)인가" 질문 하나를 한다. 경로 선행 조건이 없으면 사실을 말하고 그 경로를 멈춘다. 명시적 경로 지시는 선행 조건이 충족될 때만 따른다 | 코드 확인(문서 선언) |
| R-06 | 어느 Step에서든 | Step 순서대로 실행한다(완료된 non-blocking 단계는 바로 다음으로). `⛔ BLOCKING`에서는 사용자의 명시적 확정이 올 때까지 멈추고 사용자 대신 정하지 않는다. 닫히지 않은 gate를 넘어 단계를 묶지 않는다. 단계 진입 전 선행 조건을 확인한다. 소유 단계 이전에 뒤 단계 산출물을 미리 만들지 않는다. 실패는 그 결함을 소유한 가장 얕은 층(페이지 → 계획 산출물 → 도구의 원본 산출물)에서 고치고, 선언된 지점부터 재개하며, 필수 산출물을 조용히 낮추지 않는다. 역할을 바꾸기 전 해당 role reference를 읽고 `## [Role Switch: <Role Name>]` 배너를 출력한다 | 코드 확인(문서 선언) |
| R-07 | Step 1: 사용자가 소스를 줌 | PDF·DOCX·Office·XLSX/XLSM·PPTX·EPUB·HTML·LaTeX·RST·URL은 `source_to_md.py`. CSV·TSV와 Markdown은 직접 읽는다(넓은 공개 데이터셋은 필요한 행·열만 잘라서 읽는다). `source_to_md.py`는 입력 옆(`-o`가 있으면 그곳)에 `<stem>.md`와 `<stem>.conversion_profile.json`을 쓰고 자산은 `<stem>_files/`에 둔다. 출력이 입력과 같은 파일이면 UTF-8이 아닌 입력은 거부한다 | 코드 확인 |
| R-08 | Step 1: 주제만 있거나 읽은 뒤에도 외부로 검증 가능한 사실이 비어 있음 | `topic-research`를 실행하고 그 결과 쌍(Markdown + facts JSON)을 소스로 쓴다. Step 2는 facts JSON의 URL을 펼치지 않고 파일로만 가져온다. 닫힌 코퍼스는 주어진 자료 안에 머문다 | 코드 확인(문서 선언) |
| R-09 | Step 2: `init <name> [--format <key>]` | `<name>`은 `/`·`\`·절대경로·`.`·`..`·빈 문자열이면 거부(`ValueError`). 디렉터리 이름은 `--format` 없으면 `<name>_<YYYYMMDD>`, 있으면 `<name>_<format>_<YYYYMMDD>`(별칭 `xhs` → `xiaohongshu` 정규화). `<name>`이 이미 `_<8자리>`로 끝나면 그대로 쓴다. 등록되지 않은 `--format`이면 거부. 기준 디렉터리는 `--dir`, 없으면 repo checkout 안에서는 repo의 `projects/`, skill만 설치된 환경에서는 `<현재 작업 폴더>/projects/`. 같은 이름의 디렉터리가 있으면 `FileExistsError`로 `[ERROR]` + exit 1 | 코드 확인 |
| R-10 | Step 2: `init` 성공 | C1의 11개 디렉터리와 `README.md`를 만든다. `confirm_ui/`, `backup/`, `exports` 안 파일은 만들지 않는다. 캔버스가 정해지지 않았으면(`--format` 없음) 그 사실을 알리고, 캔버스는 Stage 1에서 확정해 `spec_lock.md`에 기록한다 | 코드 확인 |
| R-11 | Step 2: `init` 성공 직후와 이후 | `validation/workflow.log`에 첫 NOTE("Project initialized: profile=default…")가 쓰이고, 쓰기에 실패하면 경고만 내고 exit 0을 유지한다. 이후 프로젝트 인자를 가진 Python 도구는 자동으로 명령 요약을 이 로그에 append한다. agent는 중요한 인수인계·재작업 사유·승인된 예외·수동 복구에만 `workflow_log.py <project_path> "<detail>"`을 한 번 쓰고, 생성·재개 중에는 이 로그를 읽지 않는다 | 코드 확인(첫 기록, 자동 기록 설치는 `console_encoding.py:88`), 코드 확인(문서 선언)(읽지 않는 규칙) |
| R-12 | Step 2: 캔버스 | `--format <registered_format>`은 사용자나 소스의 명시적 사실이 정확히 등록된 캔버스를 정할 때만 붙인다. 아니면 붙이지 않고 Stage 1이 프로젝트 초기화 캔버스에서 시작해 확정하며 `spec_lock.md`가 viewBox를 기록한다 | 코드 확인(문서 선언) |
| R-13 | Step 2: `import-sources <project_path> <소스...>` 입력 | 소스 경로와 함께 Step 1이 쓴 같은 stem의 Markdown을 넘긴다(그러면 재변환이 억제되고 그 Markdown과 sidecar·자산이 가져와진다. 소스만 주면 원본은 보관되고 다시 변환된다). `-o`로 다른 곳에 썼다면 둘 다 넘긴다. 디렉터리는 비재귀로 펼친다. 레포의 `projects/` 아래 소스는 기본 이동(`--copy`면 복사), 다른 프로젝트 안 파일과 그 밖의 경로는 복사(`--move`는 `projects/` 아래에만 적용). 직접 준 비트맵은 원본을 `sources/`에 보관하고 충돌 안전 이름으로 `images/`에도 복사한다. 내용이 대화에만 있으면 이 명령을 생략한다 | 코드 확인(`cli.py:848-1224`, `scripts/docs/project.md:35-78`), 코드 확인(문서 선언)(생략 규칙) |
| R-14 | Step 2: `import-sources` 결과 | 사용 가능한 결과(archived/markdown/assets/images/analysis 중 하나라도)가 있으면 exit 0, 없으면 `[ERROR]` + exit 1. 출력된 `Skipped:` 입력은 없는 것으로 취급한다. URL 변환이 쓸 만한 Markdown을 못 내면 URL 기록만 보관한다. PPTX 계열 소스는 `analysis/`에 intake 산출물을 쓴다(실패해도 notes에 남기고 계속) | 코드 확인 |
| R-15 | Step 3 | 사용자에게 보이는 페이지·질문·receipt·선택·설치 없이 후보만 준비한다. 후보는 `routing.md` §7의 등록된 index 4개의 root와 이번 실행에 준 모든 exact root이고, index에서 파생한 root만 허용한다. 이름만 준 템플릿은 로컬 경로로 풀지 않고 스타일 요청으로 본다. UI 분기: `template_options`(`schema_version: 1`, `phase: "template"`, UI `lang`, 절대경로 `explicit_workspace_roots` 배열(없으면 빈 배열), `default_mode`)를 `recommendations.stage1.json`에 넣는다. `default_mode`는 명시적 템플릿 의도나 exact root가 있으면 `templates`, 아니면 `free_design`. chat/위임 분기: 같은 경계를 컨텍스트에 보관하고 UI 파일을 만들지 않는다. 템플릿 모드는 선택이 1개 이상 필요하고 exact root가 하나뿐일 때만 미리 선택할 수 있다 | 코드 확인(문서 선언) |
| R-16 | Step 4 문서 로딩 순서 | Stage 1 전에 `strategist.md`·`plan-core.md`·`canvas-formats.md`를 한 번에 읽는다. Stage 1 확정과 설치 뒤에 템플릿이 설치됐으면 `strategist-template.md`를, 확정된 delivery가 녹화·자동 진행·영상이면 `video-design.md`를 읽는다. Stage 2 해결안·이미지 권장안·roster를 쓰기 전에 고정된 planning-capability 묶음(`strategist-image.md`, `modes/_index.md`, `visual-styles/_index.md`, `image-renderings/_index.md`, `templates/icons/README.md`, `charts/chart-vocabulary.md`, `tables/table-vocabulary.md`)을 한 번에 읽는다. 사용자 이미지가 있으면 설계 문서 전에 `analyze_images.py <project_path>/images`를 돌리고 CSV를 §VIII 전에 읽는다 | 코드 확인(문서 선언) |
| R-17 | Step 4: ⛔ 2단계 확정 | Stage 1은 소통 계약과 템플릿 모드(`free_design` 또는 `templates`)를 함께 확정한다. 최종 Stage 2는 Stage 1 선택이 설치(또는 자유 디자인이 닫힘)된 뒤 전체 해결안과 제작 옵션을 확정한다. 확정은 사용자만 한다. agent는 권장안을 쓰고 서버를 운영하고 상태를 읽고 템플릿을 적용할 뿐, 대신 확정하거나 제출을 자동화하거나 payload를 합성하거나 사용자 결과 상태를 쓰지 않는다. 침묵은 확정이 아니다. 사용자가 명시적으로 위임했을 때만 agent가 Stage 1 결정·설치·Stage 2 도출을 하고 UI receipt를 위조하지 않은 채 요약 하나를 낸다. 제출된 값(공백·특이한 덮어쓰기 포함)이 권위를 가진다. 선택 사항 `refine_spec: true`는 Design Spec Gate 1 뒤에 승인 gate를 하나 더한다 | 코드 확인(문서 선언). 사용자 결과 파일을 agent가 쓰지 못하게 코드로 막는지는 확인 못함(U-02) |
| R-18 | Step 4: UI 분기의 파일 소유와 명령 순서 | agent가 쓰는 것: `recommendations.stage1.json`(+ `template_options`), `recommendations.stage2.json`(`stage: "stage2"`, 서버가 쓴 `selection_sha256` 복사). 서버가 쓰는 것: `template_selection.json`, `result.json`. 설치기가 쓰는 것: 프로젝트 루트의 `template_install.json`. 아직 확정되지 않은 활성 stage 파일만 제자리에서 덮어쓰고, 다른 stage payload나 접미사 있는 개정본으로 쓰지 않는다. 순서: Stage 1 작성(후보 spec·prototype은 열지 않음) → `server.py <project_path> --daemon` → URL과 요약 안내 → `--wait-only --wait-stage stage1` → exit 0은 "중간 단계이므로 계속"이며 최종 응답이 아니다 → `result.json`과 `template_selection.json`을 한 번 읽음 → `templates`면 각 root에 `apply-template-workspace`를 실행(자유 디자인이면 건너뜀) → 설치된 상태를 본 뒤 Stage 2 작성 → `--wait-only` → 완전한 `result.json`을 한 번 읽고 `stage: final` + `status: confirmed`일 때만 진행 → 항상 `--shutdown` 순서 제약: 최종 `--wait-only`는 agent가 `recommendations.stage2.json`을 쓰고 템플릿 설치가 끝난 뒤에만 부른다. 그 전에 부르면 기다리지 않고 즉시 exit 1이다(confirm-and-preview-ui R-08). | 코드 확인(파일 이름·exit 124·CLI 옵션: `server.py:80-95`, `:2085-2135`, `:2755-2800`, `apply_template.py:57,568`), 코드 확인(문서 선언)(순서) |
| R-19 | Step 4: UI 실패·전환·중단 | UI 실행 실패나 대기 timeout(exit 124, 확정 결과가 아직 없으면)은 막지 않는다. `confirm_ui/result.json`을 한 번 다시 확인한 뒤 chat 확인으로 대체하고 서버 정리는 계속 의무다. 사용자가 중간에 chat으로 바꾸면 현재 stage를 확정할 때까지 막히고, 저장된 확정 stage는 유지한 채 남은 stage를 chat으로 끝내며 UI를 다시 띄우지 않는다. Stage 1 뒤에 중단됐고 UI가 계속 선택돼 있으면 Stage 1 결과를 읽어 Stage 1을 바꾸지 않고 새 `recommendations.stage2.json`을 만들어 `--wait-only`로 이어 간다. 최종 확정이 없으면 막히고 사용자의 확정이나 값 변경이 필요하다. Stage 1 증거가 없으면 Stage 1부터 다시 한다 exit 124는 사용자 미응답과 stage2 파일의 검증 거부를 구분하지 않는다(confirm-and-preview-ui의 "원본이 정하지 않은 것"). | 코드 확인(문서 선언) |
| R-20 | Step 4: 최종 확정 → `design_spec.md` (Gate 1) | 확정 값을 한 번 소비해 `templates/design_spec_reference.md`를 읽고 I~X절 완전한 `design_spec.md`를 placeholder·`scaffold-*` 없이 한 번에 쓴다(첫 줄 schema marker). 깊이는 확정된 `design_spec_depth`(`brief` 기본 또는 `complete`)를 따른다. 확정한 값은 의미 유형(literal·semantic·identity anchor·reference·permission)을 보존하고 모든 제작·타이포·이미지 소스·`image_notes` 의무를 담는다. 확정 값 → 설계 문서를 필드별로 감사(Gate 1)하고 `result.json`은 다시 열지 않는다(재개 때 보관된 상태가 없을 때만 한 번). Gate 1을 통과하기 전에는 lock을 쓰지 않는다. 확정된 값이 설계 문서에서 빠지거나 약해지면 막힌다 | 코드 확인(문서 선언) |
| R-21 | Step 4: `refine_spec: true` | 완성된 `design_spec.md`를 `refine-spec`으로 사용자가 검토하도록 열고, 임의 수정을 받되 lock은 건드리지 않고 사용자의 명시적 승인(chat)까지 멈춘다. 기본은 끔이고 "Spec-refinement note"는 항상 안내한다 | 코드 확인(문서 선언) |
| R-22 | Step 4: `spec_lock.md` (Gate 2)와 validate | Gate 1과 (켜졌으면) 승인 뒤에 `spec_lock_reference.md`를 읽고 승인된 설계 문서와 컨텍스트로 lock을 한 번에 쓴다(첫 줄 schema marker, `##` 섹션과 `- key: value` 줄만, `forbidden`은 예외). lock은 확정된 identity를 바꾸거나 refinement를 버리거나 방향을 새로 도입하지 않는다. 그 뒤 lock 앵커를 설계 문서와 비교하고 `project_manager.py validate <project_path>`를 돌린다. 스키마가 맞아도 충실도는 증명되지 않으므로 확정 값 → 설계 문서 불일치, 설계 문서 → lock 불일치, 적용 안 된 개정은 막는다. 수리는 보관된 확정(또는 승인된 개정)에서 하고 재개·refine은 기존 파일을 고칠 뿐 scaffold를 쓰지 않는다 | 코드 확인(문서 선언) |
| R-23 | Step 4: 제작 필드 | Speaker Notes·Custom Animations·Narration Audio는 최신 명시적 사용자 지시 → 최종 Stage 2의 proactive 값 → 기본값(`true`/`false`/`false`) 순으로 정해 `design_spec.md §I`의 세 행에 출처와 함께 기록한다. 원래의 proactive 필드는 증거로만 두고 lock에는 넣지 않는다. Narration Audio가 켜지면 명시적으로 끄지 않은 Speaker Notes를 켜고 그 의존을 밝힌다. 노트를 끄고 오디오를 켠 채 둘 때는 질문을 하나 한다(오디오도 끌지, 필요한 노트를 유지할지). 이후의 명시적 지시는 해당 §I 행만 고치고 소유 단계에서 재개하며 확인 화면을 다시 열지 않는다 | 코드 확인(문서 선언) |
| R-24 | `project_manager.py validate <project_path>` 호출 | 프로젝트 경로가 없거나 디렉터리가 아니면 error. `svg_output/`가 없으면 error. `design_spec.md`(또는 legacy 이름 3개)가 있으면 design schema로, `spec_lock.md`가 있으면 lock schema로 검증하고, `design_spec.md`는 있는데 `spec_lock.md`가 없으면 error(`Communication trace: missing spec_lock.md...`). schema marker가 있고 값이 틀리거나 지원하지 않으면 error, marker가 없으면 legacy 경고로 건너뛰고 legacy communication trace를 돌린다. 확인하는 내용은 1.3.6 마지막 문단. `README.md` 없음, `svg_output/`가 비어 있음, SVG 이름 비표준, 디렉터리 이름에 `_YYYYMMDD` 없음, SVG의 viewBox가 등록 포맷과 다르거나 서로 다름은 **경고**. error가 하나도 없으면 exit 0(경고만 있어도 0). 이 명령은 프로젝트 산출물(`design_spec.md`, `spec_lock.md`, SVG 등)을 쓰거나 고치지 않고 `confirm_ui/result.json`을 읽지 않는다. 단 프로젝트에 `validation/workflow.log`가 이미 있으면 모든 프로젝트 CLI가 그렇듯 이 명령의 stdout·stderr를 그 로그에 덧붙인다(`console_encoding.py:88` `install_auto_transcript`, `workflow_transcript.py:302-347`. 환경변수 `PPT_MASTER_DISABLE_WORKFLOW_TRANSCRIPT`가 있으면 끈다) | 코드 확인 |
| R-25 | `validate`가 보장하지 않는 것 | (a) `design_spec.md`가 없으면 error가 아니라 경고이므로 `design_spec.md`도 `spec_lock.md`도 없는 프로젝트가 `svg_output/`만 있으면 통과한다. (b) lock의 `page_rhythm` 행과 §IX `Slide` 블록, `svg_output/` 파일의 일치는 `validate`가 확인하지 않는다(찾은 비교는 lock 내부 참조뿐). (c) 설계 문서 → lock의 값 일치, 확정 값 → 설계 문서 충실도는 확인하지 않는다. (d) §IX roster ↔ `svg_output/` 파일 번호의 일치는 `validate`가 아니라 final 단계의 `svg_quality_checker.py`가 확인한다(R-36). 구현자가 gate에서 두 파일의 존재와 이 일치를 직접 확인하지 않으면 원본도 보장하지 않는 구간이 생긴다 | 코드 확인(a·c·d). (b)는 검색 범위 안에서 못 찾은 것(2.1) |
| R-26 | Step 4: 아이콘 풀 | 확정에서는 일반 라이브러리 하나와 stroke만 정한다. 승인 뒤 §VI·lock을 쓸 때 agent가 `icon_sync.py <project_path> <lib/name>...`으로 curated 풀을 `icons/`에 복사·검증한다. non-zero 종료면 빠진 개념만 선택된 라이브러리(브랜드면 `simple-icons`)에서 다시 고르고 깨끗해질 때까지 다시 돌린다. 빠진 아이콘을 다음으로 넘기거나 라이브러리를 바꾸지 않는다. Executor는 동기화하지 못한다(없으면 Strategist로 되돌림) | 코드 확인(문서 선언) |
| R-27 | Step 4~5: `generation_mode` | 기본 `continuous`는 Step 5 뒤 바로 Step 6으로 간다. `split`이거나 무거운 실행(긴 분량·큰 소스·이 chat에 남은 많은 조사)이면 Step 4에서 분할을 권하거나 확인한다. 응답이 없거나 "continue"이면 `continuous`다. `split`이면 Step 5 뒤 "Planning Session Complete" 인수인계를 출력하고 이 대화를 멈추며, 새 chat에서 프로젝트를 지정한 재개 요청(`resume-execute` stage)으로 Step 6에 들어간다 | 코드 확인(문서 선언) |
| R-28 | Step 4: 사용자가 최종/literal 내레이션 스크립트를 줌 | Stage 2에서 장면별로 분절하고 §IX에 각 분절을 받치는 화면 상태를 두고 §X에 출처와 verbatim 정책을 쓴다. Gate 2 뒤(Step 5나 split 인수인계 전)에 정확한 분절을 `notes/total.md`에 한 번 쓰고 Step 7.1에서만 분할한다. 이 경우만 Step 4의 출력에 `notes/total.md`가 있다 | 코드 확인(문서 선언) |
| R-29 | Step 5 진입 | §VIII에 `Acquire Via`가 `ai`·`web`·`slice`인 행이 하나라도 있거나 `Reference: Derived from <canonical bare filename>; treatment=...` 대기 파생이 있으면 실행한다. user만 있는 계획과 `placeholder` 행은 트리거하지 않는다. 시작 gate는 `design_spec.md`와 `spec_lock.md`가 존재하는 것이고 없으면 Step 5를 멈추고 `failure-recovery.md` §3으로 간다. 먼저 `references/image-base.md`를 읽고 행 종류에 따라 `image-generator.md`·`image-searcher.md`를 추가로 읽는다 | 코드 확인(문서 선언) |
| R-30 | Step 5 완료 | 모든 행이 terminal이어야 한다(`Pending`·`Failed`·`Needs-Selection` 없음). AI 행이 풀리지 않으면 `auto`는 경로 A, 경로 B 순으로 시도하고 조용히 수동으로 가지 않으며, 둘 다 소진되거나 확정된 `api`/`host-native` 경로가 재시도 뒤에도 안 되면 사용자에게 (1) 같은 경로 복구·재시도 (2) 목록의 파일을 수동 생성 (3) 영향받는 AI 이미지를 취소하고 계획 수정 중 하나를 묻는다(`manual`을 확정했을 때만 `Needs-Manual` 행이 생긴다). 웹 실패는 멈추지 않고 다른 질의·provider·라이선스 전략을 시도하고 안 되면 `Needs-Manual`로 표시·보고하고 계속한다. 끝나면 `analyze_images.py <project_path>/images`로 CSV를 갱신한다 | 코드 확인(문서 선언) |
| R-31 | Step 5·6 중 §VIII가 `image_notes`가 명시한 소스·자산·페이지 역할을 빠뜨린 것이 드러남 | Step 4 Gate 1로 돌아가 보관된 최종 상태에서 설계 문서를 고친다 | 코드 확인(문서 선언) |
| R-32 | Step 6 진입과 컨텍스트 | 선행 조건은 Step 4(와 Step 5)가 끝난 것이다. core 묶음(`executor-base.md`, `shared-standards-core.md`, `semantic-svg.md`, `preset-shape-vocabulary.md`, 해결된 `modes/<id>.md`와 `visual-styles/<id>.md`, 로스터 점검으로 트리거된 module)을 한 번에 읽고, `spec_lock.md`가 지정한 상세 파일만 읽는다. 컨텍스트가 유효하면 설계 문서와 lock을 다시 읽지 않는다. 새로 시작·재개·압축·외부 변경된 컨텍스트에서는 `design_spec.md` → `spec_lock.md`를 한 번씩 읽고 (중간이면) 마지막 SVG와 트리거된 참조도 읽는다. 5페이지마다(P05, P10…) 다음 페이지 전에 `spec_lock.md`를 전체 한 번 다시 읽는다(검사·출력·수리 없음). 둘 중 하나가 없으면 멈추고 빠진 gate 산출물을 알린다 | 코드 확인(문서 선언) |
| R-33 | Step 6: 페이지 roster | `design_spec.md §IX`가 순서 있는 큐다. 페이지 하나가 최종 슬라이드 하나에 같은 id·순서로 대응하고, 그리는 중에는 추가·삭제·병합·분할·순서 변경을 하지 않는다. continuous 실행은 Stage 1이 확정한 범위 안에서 영향받은 §IX 블록과 `page_rhythm` 행을 먼저 고치고 `validate`를 다시 돌릴 수 있고, 범위를 벗어나면 Stage 1을 다시 확정한다. 페이지 SVG는 현재 main agent가 직접 쓴다(하위 agent·slide 파일 생성기 금지) | 코드 확인(문서 선언) |
| R-34 | Step 6: 첫 SVG 전 | 압축된 소통 목표, 캔버스 크기, 본문 폰트 크기, 색 구성(주·보조·강조 HEX), 폰트 계획, role별 보정표, live preview URL을 담은 확인 메시지 하나를 출력한다. 보정표는 `text_measure.py calibrate <project_path> --outline`의 결과이고 `validation/text_calibration.json`에 쓰인다. 미리보기가 안 떴으면 이때 그 사실을 말한다 | 코드 확인(`text_measure.py:756`), 코드 확인(문서 선언)(출력 규칙) |
| R-35 | Step 6: live preview | 첫 SVG 전에 `svg_editor/server.py <project_path> --live --daemon`을 시작해 Step 7까지 켜 둔다. 기본은 6060부터 첫 빈 포트(`--port N`은 엄격 바인딩)이고 URL은 출력이나 `live_preview/lock.json`에서 읽어 보고한다. 곁가지 프로세스이므로 기다리거나 확정을 요구하지 않고, 실패하거나 금지됐으면 그 사실만 보고하고 생성을 계속한다. 사용자가 **Exit preview**를 누르거나 채팅으로 요청할 때까지 켜 둔다 | 코드 확인(문서 선언), 코드 확인(`lock.json` 이름, `svg_editor/server.py:45-48`) |
| R-36 | Step 6: 검사 cadence와 gate | P01~P05 → early gate(roster가 6페이지 이하면 건너뜀) → 나머지 페이지 → final gate를 한 컨텍스트에서 한다. early: `svg_quality_checker.py <project_path> --canonical-authoring --stage early --json`을 5번째 SVG 뒤 6번째 전에 돌린다(보고서 `validation/svg_quality_early_report.json`, 한 줄 `gate-signal: method=… \| page-local=… \| not-exercised=…`을 출력). final: 모든 SVG가 존재한 뒤 `--stage final --json`(보고서 `validation/svg_quality_report.json`, 이후 노트 작성 전). 검사기 호출은 gate 지점이나 하나의 통합 수리 직후에만 한다. `--json` 없이는 내보내기가 거부된다. 성공 시 stdout 요약과 exit status만 쓰고 JSON 전체를 컨텍스트에 붙이지 않는다. 검사기는 error가 1개 이상이면 exit 1이다. 비-partial(final) 실행에서는 §IX 블록의 `Audience move`·`Relationships`, `Slide` 번호 집합 ↔ `svg_output/` 파일 번호 집합, §IX의 링크 대상까지 error로 비교한다 | 코드 확인(`svg_quality/cli.py:89-110,296-358`, `svg_quality/checker.py:7540-7560`, `project_utils.py:240-470`), 코드 확인(문서 선언)(cadence) |
| R-37 | Step 6: 검사 결과 처리 | checker error는 막는다. 한 번의 필터 없는 실행의 전체 이슈를 보고, 모든 error와 선택한 warning을 하나의 통합 수리 패스에서 고치고 한 번 검증을 다시 돌린다. 남은 실패는 다음 배치이며 개별 수정 사이에 검사하지 않는다. warning은 막지 않고 필수 수정이 아니다. final 뒤 carrier-receipt 검토를 하고 고치면 final 검사를 한 번 다시 돌린다 | 코드 확인(문서 선언) |
| R-38 | Step 6: 노트 | `design_spec.md §I`의 Speaker Notes가 켜졌으면 `references/executor-notes.md`를 읽고, 얼린 `notes/total.md`가 있으면 모든 정보성 최종 SVG 그룹과 대조해 검증(고칠 대상은 페이지나 계획이고 스크립트가 아니다)하고, 없으면 각 페이지의 최종 SVG에 근거해 `notes/total.md`를 쓴다. 꺼졌으면 아무것도 읽거나 만들지 않는다 | 코드 확인(문서 선언) |
| R-39 | Step 6: 조건부 gate (내보내기 전) | 차트 페이지가 있으면 `verify-charts`. 사용자가 명시적으로 요청했을 때만 `visual-review`. `animations.json`이 이미 있으면 항상 `customize-animations`를 내보내기 전에 실행하고, 없으면 페이지·객체별 명시적 요청이나 §I의 Custom Animations 켜짐일 때만 실행한다(§IX의 Motion suggestion은 입력일 뿐 트리거가 아니다). deck 전체 모션 요청은 `animations.md`의 플래그를 Step 7.3에서 해결한다. 해당 없으면 아무것도 읽지 않는다 | 코드 확인(문서 선언) |
| R-40 | Step 6: Executor가 계획 정보 부족을 발견 | Executor는 `spec_lock.md`를 고치지 않는다. 필요한 role·계획 세부가 없으면 해당 페이지가 막히고 Step 4 Gate 1/2의 Design Spec/lock 조각을 `executor-base.md` §2.1에 따라 고친 뒤 현재 페이지로 돌아온다. 확정된 의도가 바뀔 때만 사용자에게 묻는다 | 코드 확인(문서 선언) |
| R-41 | Step 6~7 중 사용자가 live preview에 annotation 제출 | 생성 중에는 읽거나 적용하지 않는다. Step 7 이후 사용자가 요청하면 `live-preview`의 Step 2에서 적용한다 | 코드 확인(문서 선언) |
| R-42 | Step 7 진입 | 모든 최종 페이지가 `svg_output/`에 있고, 조건부 gate가 통과했고, final 보고서 0 error이며, 노트가 켜졌으면 `notes/total.md`가 모든 페이지를 덮는다. 필수 행이 `Needs-Manual`이면 예상 파일과 slice 출력이 모두 `images/`에 있어야 Step 7의 첫 명령을 실행한다. 하나라도 없으면 멈추고 정확한 파일 이름을 나열하며 `finalize_svg.py`·`svg_to_pptx.py`를 돌리지 않고 점선 placeholder를 내보내지 않는다. 파일이 도착하면 `analyze_images.py`를 다시 돌리고 placeholder를 교체하고 `no-crop` 컨테이너를 실제 비율에 맞추고 final 검사를 다시 돌린다 | 코드 확인(문서 선언) |
| R-43 | Step 7 전체 | 명령은 하나씩 별개 호출로 실행하고, 이전 하위 단계가 exit 0이고 성공 기준이 맞아야 다음으로 간다. 실패하면 소유 원본을 고치고 실패한 하위 단계부터 재개한다. 계획 단계는 원본이 바뀌지 않으면 다시 하지 않는다 | 코드 확인(문서 선언) |
| R-44 | Step 7.1: 노트가 켜졌을 때만 `total_md_split.py <project_path>` | `svg_output/`의 SVG 파일 이름(stem)과 `notes/total.md`의 제목을 대조한다. 제목 줄(`#`~`######`)은 stem과 정확히 같거나, 정규화(영문·숫자·한자 이외는 `_`)한 이름이 유일하게 같거나, 앞의 숫자(`Slide 3`·`P3`·`第3页` 포함)가 유일하게 같거나, 정규화한 이름이 유일한 stem에 포함될 때 그 stem으로 매핑한다. 같은 stem의 제목이 반복되면 본문을 이어 붙인다. 매핑되지 않은 제목은 알림만 하고 무시한다. SVG가 없거나 `notes/total.md`가 없거나 매핑된 제목이 하나도 없거나 SVG 중 하나라도 노트가 없으면 이유를 출력하고 exit 1이며 아무 파일도 쓰지 않는다. 일치하면 `notes/<stem>.md`를 쓰고, 현재 페이지와 맞지 않는 옛 번호 파일은 지우지 않고 advisory로만 알린다. 성공 기준은 발행되는 모든 슬라이드에 대응하는 `notes/<stem>.md`가 있는 것이다 보강: `-o` 옵션이 있다. 노트 본문 안의 `## 3. 소제목` 같은 헤딩도 숫자 매핑이 유일하면 노트를 그 stem으로 쪼갠다. 쓰기 도중 예외가 나면 일부 파일만 쓰인 채 exit 1일 수 있다(`split_notes`는 성공 개수가 SVG 수와 같은지로 판정) | 코드 확인(C-08) |
| R-45 | Step 7.2: `finalize_svg.py <project_path>` | `svg_output/`가 없거나 SVG가 없으면 `[ERROR]` + exit 1. 있으면 임시 후보 디렉터리에 `svg_output/`를 복사하고 아이콘 임베드, 이미지 정렬·임베드, tspan 평탄화를 적용한 뒤 후보를 `svg_final/`에 원자적으로 교체한다(기존 `svg_final/` 전체가 바뀌고 이전 파일은 남지 않는다). 이미지·평탄화 오류가 있으면 `svg_final/`을 발행하지 않고 exit 1이다. `svg_final/`은 미리보기일 뿐이므로 없어도 7.3은 막히지 않는다. 단 `finalize_svg.py`가 실패했다는 것은 실패 처리 표에서 막는 실패로 분류된다 프로젝트 루트에 임시 디렉터리 `.svg_final.candidate-*`와 `.svg_final.publish-*`를 만들었다가 `finally`에서 지운다(복구 실패 시 recovery 디렉터리가 남는다) | 코드 확인(C-09), 코드 확인(문서 선언)(분류) |
| R-46 | Step 7.3: 명령과 플래그 | 노트가 켜졌으면 `svg_to_pptx.py <project_path>`, 꺼졌으면 `--no-notes`를 붙인다. 추가: 편집 가능한 Chart/Table 전달을 명시했거나 구조 `chart`/`table` placeholder 슬롯이 있으면 `--native-charts-and-tables`. final 검사가 큰 이미지를 보고하면 `--image-sizing display`. 보존·생성된 `animations.json`이 있으면 기본 명령 그대로(내보내기가 사이드카를 읽음). deck 전체 모션 설정은 `animations.md`에서 해결된 플래그. Custom Animations 명시적 끔은 `-a none`, 전체 모션 끔은 `--no-animations`. `--conversion-trace`는 기본 내보내기에 붙이지 않는다 | 코드 확인(문서 선언), 플래그 이름은 코드 확인(`pptx_package/cli.py:2312-2320`) |
| R-47 | Step 7.3: 내보내기 실행 | 원본이 `svg_output/`인 release 내보내기(`-s`로 다른 디렉터리를 고르지 않은 기본 실행. `-o`는 gate를 건너뛰지 않는다)는 현재 `svg_output/`의 fingerprint와 맞는 통과한 `final` 보고서가 없으면 오류와 `svg_quality_checker.py ... --stage final --json` 안내를 stderr에 쓰고 exit 1이다. 통과하면 `exports/<name>_<YYYYMMDD_HHMMSS>.pptx`(플래그에 따라 `_native_charts_tables`·`_narrated`·`_kiosk` 접미사)를 쓰고, 성공 시 `svg_output/`를 `backup/<timestamp>/svg_output/`로 복사하고(`-o`를 쓰면 backup 없음), postflight 보고서 `validation/<exports 파일 stem>.report.json`(`pptx_package/cli.py:1473`, 접미사 포함 stem)을 쓰고 `[POSTFLIGHT]` 요약을 출력한다. postflight가 실패하면 "must not be used" 오류와 함께 잘못된 파일 위치를 알리고(파일은 남음) exit 1이다. notes를 켠 채 `notes/`가 없거나 특정 페이지의 노트가 없거나 비어 있으면 그 페이지에는 노트를 붙이지 않을 뿐 오류가 아니다. 이전 내보내기는 지우지 않는다. agent는 요약만 읽고 경고를 알리며 성공 시 보고서 전체를 읽지 않는다 `notes/` 파일이 읽거나 디코딩할 수 없는 상태이면 `NotesFileReadError`로 exit 1이다(`discovery.py:111-115`, `pptx_package/cli.py:3326-3333`). 노트 매칭은 파일 stem이 SVG stem과 같거나(우선) stem의 `slide_?\d+` 번호가 n번째 SVG를 가리키는 방식이다(round-trip이 아닐 때) | 코드 확인(C-10, `builder.py:2152-2178`, `discovery.py:78-88`) |
| R-48 | Step 7 완료 | 내보낸 PPTX 경로를 보고한다. `design_spec.md §I`의 Narration Audio가 켜졌으면 `generate-audio`를 실행하고, 아니면 보조 post-export stage는 명시적 트리거가 있을 때만 실행한다 | 코드 확인(문서 선언) |
| R-49 | 전달된 프로젝트의 수정 요청 | 이 경로 안에서 계획을 다시 시작하지 않고 소유 층을 고친다. 문구·조건·제목 변경은 SVG → 그 §IX 블록 → `notes/total.md` → 그 줄을 반복하는 모든 페이지 순이다. 페이지를 삽입·삭제·이동하면 roster를 먼저 재번호하고(파일, 푸터, 목차 번호, §IX 블록, `page_rhythm`/`page_visualizations` 행, `animations.json` 키, `notes/total.md` 제목, 같은 deck 하이퍼링크 대상) 그 뒤 페이지를 쓰거나 지운다. deck 전체 색·글꼴은 `update_spec.py`, 파생 색조·옛 값에 맞춘 페이지·spec 서술은 손으로 고친다. 이후 final 검사, `animation_config.py validate`, (노트가 바뀌었으면) 7.1, 7.2, 7.3을 다시 돌린다. 문서는 7.1·7.2가 쓰기만 하므로 재번호 뒤 `notes/`와 `svg_final/`의 페이지별 파일을 먼저 지우라고 하지만, 코드에서 `svg_final/`은 통째로 교체되어 지울 필요가 없고(R-45), `notes/`의 옛 파일은 지워지지 않는다(R-44) | 코드 확인(문서 선언), 불일치는 2.1 |
| R-50 | 필수 산출물의 실패 | 필수 산출물이 실패하면 다음 gate가 막힌다. 편의 표면(확인 화면·live preview)의 실패는 chat 확인이나 생략으로 대체하고 막지 않는다. gate 산출물이 없으면 그 gate에서 멈추고 이름을 댄다. 파생 산출물이 낡았으면 소유 원본에서 다시 만든다. 검증·내보내기 실패는 소유 원본을 고치고 실패한 작업과 그 하위만 다시 돌린다. 마지막으로 좋았던 상태에 따른 재개 지점은 아래 표다. 어떤 gate도 하위 명령이 누락을 견디리라는 이유로 건너뛰지 않고, 확정된 실행 값을 경로를 진행시키려고 바꾸지 않는다 | 코드 확인(문서 선언) |

재개 지점(`failure-recovery.md:71-86`, 마지막으로 좋은 상태 → 재개):

| 마지막으로 좋은 상태 | 재개 |
|---|---|
| Stage 1 확정, Stage 2 없음·미확정, UI 선택됨 | confirmed Stage 1과 현재 입력에서 새 `recommendations.stage2.json`을 만들고 `--wait-only` |
| 최종 확정 증거는 있고 `design_spec.md` 없음 | Step 4: 증거를 한 번 읽고 `design_spec.md`를 처음부터 쓰고 Gate 1을 통과한 뒤 lock을 새로 씀(남은 lock은 대체, lock에서 설계 문서를 복원하지 않음) |
| 최종 확정 증거와 `design_spec.md`는 있고 lock 없음 | Step 4: 설계 문서를 한 번 감사하고 lock을 씀 |
| 두 파일이 있으나 Gate 1 실패 | 증거를 한 번 읽고 `design_spec.md`를 고치고 영향받은 lock 행을 다시 씀(lock에서 추론하지 않음) |
| Gate 1 통과, Gate 2 실패 | 설계 문서를 두고 어긋난 lock 행만 다시 씀 |
| 최종 확정 증거 없음 | `result.json`이 Stage 1만 증명하면 최종 Stage 2에서 재개, 아니면 Step 4를 Stage 1부터 다시. 부분 산출물에서 확정을 추론하지 않음 |
| 두 계획 산출물 완료, split 선택 | `resume-execute` |
| 이미지 확보 완료, SVG 시작 전 | Step 6 |
| SVG 완료·checker 통과, 노트 켜짐인데 노트 없음 | Step 6 Logic Construction |
| SVG 완료, 노트 꺼짐 | 조건부 모션 처리, 그 뒤 7.2와 `--no-notes` 내보내기 |
| SVG와 노트 완료 | 7.1 |
| 7.1 완료 | 7.2 |
| 7.2 완료, PPTX 없음 | 7.3 |
| 내보낸 뒤 annotation 저장됨 | `live-preview` Step 2 |

- **불변식**: (1) 내보내기 입력의 유일한 페이지 원본은 `svg_output/`다. `svg_final/`, `design_spec.md`, `spec_lock.md`, 템플릿은 내보내기 시점에 보이는 내용을 더하지 않는다(`generate-pptx.md:18`, `executor-base.md` 근거, R-45·R-47). (2) `design_spec.md`와 `spec_lock.md`는 같은 확정에서 나온 두 판본이고 서로 병렬 초안이 아니다. (3) 확정 증거는 `confirm_ui/result.json`의 `stage: final` + `status: confirmed`(또는 chat의 명시적 최종 확정)이고, 계획 산출물만으로는 아무것도 증명하지 않는다. 이 불변식들은 문서 선언이고 코드가 강제하지 않는 부분이 있다(R-17, R-25).
- 미결정: 없음

- 확인 한계: 스크립트와 파이프라인을 실행하지 않았다(읽기만). `references/strategist.md`·`executor-base.md`의 본문은 Step 4·6이 인용하는 절과 헤딩만 읽었고, `plan-core.md`는 헤딩만 열었으며, 해당 본문의 의미는 다루지 않았다. `confirm_ui/server.py`, `svg_editor/server.py`, `source_to_md` 하위 변환기, 이미지 도구는 진입 함수와 파일 이름·종료 코드만 확인했다. `attribution_guard`의 판정 조건은 의도적으로 읽지 않았다. 외부 시스템(이미지 API, 브라우저 동작)의 실제 보장은 확인하지 않았다.

### 1.5 필수 코드 참조 [필수]

라이선스는 MIT(overview 1절)이므로 인용에 제약이 없다. 아래 C-ID는 모두 `skills/ppt-master/` 아래 경로이고, 작은 helper는 글로 풀었다. 디렉터리 이름 규칙(`parse_project_name`)과 정렬(`slide_roster`)은 표준 라이브러리 외 내부 helper라 C-ID로 넣었다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `skills/ppt-master/scripts/project_management/cli.py:288-399` `ProjectManager.init_project` | 이름 검증, 디렉터리 이름 규칙(날짜·format 접미사), 생성할 11개 디렉터리, README 내용, 이미 있는 디렉터리 거부 | R-09, R-10 |
| C-02 | `skills/ppt-master/scripts/project_management/cli.py:848-1224` `ProjectManager.import_sources` (+ `:504-527` `_import_pptx_intake`) | 입력 분류(URL·디렉터리·MD·PDF·PPTX·비트맵), 보관·변환·이미지 전파·skipped 사유 | R-13, R-14 |
| C-03 | `skills/ppt-master/scripts/project_management/cli.py:1380-1472` `main`의 `init`·`import-sources` 분기, `:1484-1508` `validate` 분기 | 종료 코드, 출력 문구, `workflow.log` 첫 기록 | R-11, R-14, R-24 |
| C-04 | `skills/ppt-master/scripts/project_management/cli.py:1226-1251` `validate_project`, `skills/ppt-master/scripts/project_utils.py:602-700` `validate_project_structure`, `skills/ppt-master/scripts/project_management/project_specs.py:1421-1504` `validate_project_artifacts` | error와 경고의 구분, marker 처리, lock 누락 error | R-24, R-25 |
| C-05 | `skills/ppt-master/scripts/project_management/project_specs.py:1272-1418` `validate_markdown_text`, `:858-905` `_declared_page_count`·`_validate_slides`, `:1053-1259` `_validate_spec_lock_relations` | 섹션 순서·필수·조건부·slide 필드·Page Count·lock 내부 참조·디렉터리 이름 대비 canvas 검사 | R-24 |
| C-06 | `skills/ppt-master/templates/schemas/design_spec.schema.json:1-92`, `skills/ppt-master/templates/schemas/spec_lock.schema.json:1-349` | I~X 제목 정규식, 필수 섹션, 조건부 규칙, lock 섹션·enum·`page_rhythm` 키 형식 | R-20, R-22, R-24 |
| C-07 | `skills/ppt-master/templates/design_spec_reference.md:1-196`, `skills/ppt-master/templates/spec_lock_reference.md:1-107` | `design_spec.md`·`spec_lock.md`를 쓰는 정확한 형식(두 파일의 필드 문법은 이 문서가 소유) | R-20, R-22 |
| C-08 | `skills/ppt-master/scripts/total_md_split.py:40-115`, `:137-233`, `:235-275`, `:278-376` | 노트 제목 ↔ SVG stem 매칭 4단계, 불일치 시 exit 1(무기록), `notes/<stem>.md` 쓰기, stale advisory | R-44 |
| C-09 | `skills/ppt-master/scripts/finalize_svg.py:127-170` `_publish_candidate_directory`, `:320-412` `finalize_project` | 후보 디렉터리 → 원자적 교체, 실패 시 미발행 | R-45 |
| C-10 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2683-2712`, `:3160-3185`, `:3884-3955`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/discovery.py:61-106` | 출력 이름, final 보고서 gate와 exit 1, backup 위치, postflight 실패 처리, `notes/` 탐색 | R-47 |
| C-11 | `skills/ppt-master/scripts/attribution_guard.py:196-219`, `skills/ppt-master/scripts/console_encoding.py:59-88` | 실패 시 exit 78, 거의 모든 CLI가 시작할 때 같은 검사를 호출 | R-01 |
| C-12 | `skills/ppt-master/scripts/confirm_ui/server.py:80-95`, `:1005-1030`, `:2085-2135`, `:2755-2800` | 확인 화면이 읽고 쓰는 파일 이름, `--wait-only` 종료 코드(124 포함), CLI 옵션 | R-18, R-19 |
| C-13 | `skills/ppt-master/scripts/project_utils.py:111-168` `parse_project_name` | 디렉터리 이름에서 name·format·date 분해(`exports/` 파일 이름의 `<name>`) | R-47 |
| C-14 | `skills/ppt-master/scripts/slide_roster.py:27-47` | 페이지 파일의 숫자 구간 정렬 | R-44 |
| C-15 | `skills/ppt-master/scripts/project_utils.py:240-470` `validate_communication_trace`, `validate_outline_roster` + `skills/ppt-master/scripts/svg_quality/checker.py:7540-7560` | final 검사에서 §IX 블록 필드와 roster를 `svg_output/`와 대조하는 호출 위치 | R-36 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출(코드를 읽고 도출. 원본 테스트는 열지 않았고 실행도 하지 않았다).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-09, R-10 | 오늘이 `D`일 때 `init demo` | `projects/demo_D/`에 C1의 11개 디렉터리와 `README.md`, `validation/workflow.log`. exit 0 |
| T-02 | R-09 | `init demo --format ppt169`, 그리고 `init demo_20260101` | 각각 `demo_ppt169_D`, `demo_20260101`(날짜를 다시 붙이지 않음). 같은 이름이 이미 있으면 `[ERROR]` + exit 1 |
| T-03 | R-09 | `init "a/b"`, `init ..`, `init demo --format unknown` | 모두 `[ERROR]` + exit 1, 디렉터리 미생성 |
| T-04 | R-14 | 존재하지 않는 경로 하나만 `import-sources`로 넘김 | `Skipped:` 출력, `[ERROR] No usable sources imported` + exit 1 |
| T-05 | R-14 | 파일 두 개 중 하나만 변환 성공 | exit 0. 실패한 입력은 `Skipped:`에 나오고 agent는 그 입력을 없는 것으로 본다 |
| T-06 | R-24 | `design_spec.md`·`spec_lock.md` 없이 `svg_output/`에 SVG 한 개가 있는 프로젝트에 `validate` | 경고(README 없음 등)만 있으면 exit 0. 두 파일이 없다는 사실은 경고(`Missing design specification file`)로만 나타난다 |
| T-07 | R-24 | `design_spec.md`만 있고 `spec_lock.md` 없음 | `[ERROR]`(`missing spec_lock.md`) + exit 1 |
| T-08 | R-24 | §I Page Count 8, §IX `Slide` 블록 7개 | `validate` error(`Page Count is 8 but the content outline has 7`) + exit 1 |
| T-09 | R-24 | §IX의 한 `Slide` 블록에 `Audience move` 줄 없음 | `validate` error(해당 slide 필드 누락) + exit 1 |
| T-10 | R-36 | §IX 8개, `svg_output/`에 SVG 7개(`08_*.svg` 없음), final 검사 | error(`Outline roster: ... no SVG for Slide 08`), exit 1. 같은 상황에서 `--stage early`는 이 비교를 하지 않는다 |
| T-11 | R-36 | 계획된 roster가 6페이지 | early gate를 건너뛰고 모든 SVG가 끝난 뒤 final gate만 한다 |
| T-12 | R-44 | `notes/total.md`에 `# 02_overview` 제목이 없고 SVG는 `01_cover.svg`·`02_overview.svg` | `Error: SVG files and notes do not match` + exit 1, `notes/`에 새 파일 없음 |
| T-13 | R-44 | 제목이 `Slide 2`처럼 번호뿐이고 stem이 `02_overview` 하나만 앞 숫자 2 | 그 stem으로 매핑되어 `notes/02_overview.md`가 쓰인다 |
| T-14 | R-45 | `svg_final/`에 옛 `09_old.svg`가 있고 `svg_output/`에는 없음, 7.2 재실행 | 성공 뒤 `svg_final/`에 `09_old.svg`가 없다(디렉터리가 통째로 교체됨) |
| T-15 | R-47 | final 보고서가 없거나 `svg_output/`가 보고서 이후 바뀜 | `svg_to_pptx.py`가 stderr에 gate 오류와 final 검사 명령 안내를 쓰고 exit 1. 새 PPTX 없음 |
| T-16 | R-47 | 정상 프로젝트 `demo_ppt169_D`에서 export 두 번 | `exports/demo_<ts1>.pptx`, `exports/demo_<ts2>.pptx`와 각각의 `.report.json`, `backup/<ts>/svg_output/`가 모두 남는다. `<name>`은 `demo` |
| T-17 | R-47 | 노트가 켜졌는데 `notes/`가 없는 채로 기본 export | 오류 없이 노트 없는 PPTX를 만들 수 있다(코드 기준). 이 상황을 막는 것은 워크플로 gate(R-42)뿐이다(svg-to-pptx-cli R-10) |
| T-18 | R-19 | UI 확인 대기가 590초 안에 확정을 못 받음 | `--wait-only`가 exit 124. agent는 `result.json`을 한 번 확인하고 없으면 chat 확인으로 이어 가며 `--shutdown`을 부른다 |
| T-19 | R-30, R-42 | Step 5 후 `Needs-Manual` 이미지 행이 있고 파일 미도착 | Step 7의 첫 명령 전에 멈추고 필요한 파일 이름을 나열한다. `finalize_svg.py`·`svg_to_pptx.py`를 실행하지 않는다 |
| T-20 | R-01 | integrity 검사가 실패하는 환경에서 아무 스크립트나 실행 | stderr 메시지 하나 후 exit 78(두 번째 신원 검사 실패면 메시지 없이 exit 78) |
| T-21 | R-49 | 전달 뒤 페이지 하나를 삽입 | roster 재번호 → 해당 페이지 작성 → final 검사(roster 불일치면 error) → 7.1(노트가 바뀌었을 때)·7.2·7.3. 이전 export는 남고 새 파일이 새 timestamp로 생긴다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

문서가 가리키는 위치는 모두 repo@3af3e8e 기준이다. 경로는 `skills/ppt-master/` 기준 상대 경로다.

| R-ID / T-ID | 근거 (`파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-11. `scripts/attribution_guard.py:196-205` `require_skill_integrity`(78), `:215-219` `main`. `scripts/console_encoding.py:59-66`, `:82-88` `configure_utf8_stdio`. 호출 목록은 `grep -rl "configure_utf8_stdio()" --include='*.py' scripts`(tests·`console_encoding.py` 제외) 96개와 `grep -rl require_skill_integrity scripts`(tests 제외) 11개 | **전칭 주장 "이 파이프라인의 모든 명령"**: 위 14개 명령은 각 파일에서 `configure_utf8_stdio()` 또는 `require_skill_integrity()` 호출을 직접 확인했다. `scripts/` 직속 Python 84개 중 두 호출이 모두 없는 22개(`slide_roster.py`·`project_specs.py`·`page_context.py`·`workflow_transcript.py` 등)는 라이브러리 모듈로 보이나 CLI 여부를 일일이 열지 않았다. 판정 내부는 읽지 않음 |
| R-02, R-03 | `SKILL.md:27-36` | 문서 선언만 읽음 |
| R-04, R-05 | `SKILL.md:44-57`, `workflows/routing.md:7-23`, `:29-33`, `:41-44`, `:61-63` | 문서 선언만 읽음. "Beautify가 Quick을 명시하지 않으면 Default"는 `SKILL.md:47`·`routing.md:42` |
| R-06 | `SKILL.md:112-133`, `workflows/generate-pptx.md:13-16` | 문서 선언 |
| R-07 | `workflows/generate-pptx.md:36-43`, C-02 일부, `scripts/source_to_md.py:58-59`, `:171-186`, `:400-445`, `scripts/source_to_md/_dispatcher.py:87-90`, `scripts/source_to_md/_conversion_profile.py:20-35`, `:158-182` | 입력이 로컬 파일일 때 `<stem>.md`의 기본 위치는 코드 확인. URL 입력의 기본 출력 위치는 읽지 않음(문서만) |
| R-08 | `workflows/generate-pptx.md:41`, `:45` | 문서 선언 |
| R-09 | C-01 `cli.py:288-346`, C-13 | 코드 확인. `init`의 `--dir` 기본(`cli.py:263-273` `default_projects_root`)도 확인 |
| R-10 | `cli.py:348-396`, 비교: `references/artifact-ownership.md:11-54`(`confirm_ui/`·`backup/` 미포함) | "만들지 않는다"는 `project_dirs` 목록(`cli.py:348-362`)에 없음. 검색 `grep -n "confirm_ui\|backup" project_management/cli.py`에서 `init_project`가 이들을 만드는 코드는 없음(README 문구에만 backup 언급). 서버가 `confirm_ui/`를 만든다(`confirm_ui/server.py:937`, `:2569`) |
| R-11 | `cli.py:1388-1422` 첫 기록, `scripts/workflow_log.py:32-65` `append_note`, `scripts/console_encoding.py:88` `install_auto_transcript`, `scripts/docs/project.md:194-240` | 자동 기록 내부(`workflow_transcript.py`)는 읽지 않음. "생성 중 읽지 않는다"는 문서 선언 |
| R-12 | `workflows/generate-pptx.md:62`, `scripts/docs/project.md:41-48`, `cli.py:305-343` | |
| R-13 | `workflows/generate-pptx.md:66`, `scripts/docs/project.md:20-78`, `cli.py:848-1224` | 분기 전부를 따라가지 않았다(PDF·PPTX·비트맵·URL·MD 분기는 확인, DOCX/XLSX 등 다른 변환 분기는 같은 구조라고 추정). 이동/복사 규칙은 문서와 `--move`/`--copy` 정의(`cli.py:1324-1330`)로 확인 |
| R-14 | `cli.py:255-260` `_has_usable_import`, `:1424-1472`, `:910-933` URL 분기, `:1118-1130` PPTX intake | 코드 확인 |
| R-15 | `workflows/generate-pptx.md:72-87`, `workflows/routing.md:103-116` | 문서 선언만 읽음. `template_options` 필드의 서버 쪽 검증은 읽지 않음 |
| R-16 | `workflows/generate-pptx.md:93-126` | 문서 선언. 로드되는 각 파일의 본문은 읽지 않음 |
| R-17 | `workflows/generate-pptx.md:128-130`, `references/strategist.md:19-21` | 문서 선언. 코드 쪽 강제는 없다: 서버는 `result.json`의 `stage`·`status`와 `stage1_sha256`(stage1 파일의 정규 JSON digest)만 확인하고 작성자를 구분하지 않는다. `Origin` 헤더 없는 `/api/confirm`도 받는다(`confirm_ui/server.py:189-197`, `:1030-1044`, `scripts/tests/test_local_server_security.py:53-59`, 메인이 직접 읽음). `scripts`에서 `result.json`을 읽는 비테스트 코드는 `confirm_ui/server.py`뿐이다(`grep -rn "result\.json" --include="*.py" scripts`, tests 제외). 상세는 [confirm-and-preview-ui R-04](confirm-and-preview-ui.md) |
| R-18 | `workflows/generate-pptx.md:132-152`, `references/confirm-surface.md`(1-40줄, 읽은 범위), C-12 `confirm_ui/server.py:80-95`, `:1005-1030`, `:2085-2135`, `:2755-2800`, `scripts/apply_template.py:57`, `:473-474`, `:568`, `scripts/confirm_ui/server.py:742-751` | 서버가 `--wait-only` 시 `result.json` 쓰임을 기다리는 로직(`:1005-1030`)과 exit 124는 읽음. stage1/stage2 payload 필드는 읽지 않음. 문서는 `template_install.json`을 confirm_ui 파일과 함께 나열하지만 코드에서는 프로젝트 루트(`apply_template.py:473`, `server.py:1868` `confirm_dir.parent`) |
| R-19 | `workflows/generate-pptx.md:139-154`, `workflows/governance/failure-recovery.md:17-20`, `:71-86` | 문서 선언. 124 코드 확인 |
| R-20 | `workflows/generate-pptx.md:156-162`, `references/strategist.md:228-265`, `templates/design_spec_reference.md:5-11` | 문서 선언. `strategist.md` §6.2의 표 일부를 읽음 |
| R-21 | `workflows/generate-pptx.md:160`, `:164-169` | 문서 선언 |
| R-22 | `workflows/generate-pptx.md:161-162`, `references/strategist.md:238-259`, `templates/spec_lock_reference.md:5-39`, `:101-107` | 문서 선언 |
| R-23 | `workflows/generate-pptx.md:171`, `references/strategist.md:238`, `workflows/governance/failure-recovery.md:61-65` | 문서 선언 |
| R-24 | C-04, C-05, C-06. 특히 `project_utils.py:644-700`, `project_specs.py:1421-1504`, `:1272-1418`, `:858-905`, `:1232-1259`, `templates/schemas/design_spec.schema.json:30-91`, `spec_lock.schema.json:68-73`, `:173-182`; `cli.py:1484-1508` | 코드 확인. 검증하는 lock 필드 문법 전부(`spec_lock.schema.json`의 349줄)는 읽지 않았다. 확인한 섹션은 `required`/`page_rhythm`/`pptx_structure`와 conditions 첫머리뿐 |
| R-25 | **(b)** `grep -rln "page_rhythm" scripts`(tests 제외) 결과는 `project_management/project_specs.py`, `project_management/page_context.py`, `prompt_audit_manifest.json`, `docs/*.md`뿐. `project_specs.py:1119-1160`은 lock 내부 비교, `page_context.py:507-511`은 누락 시 `dense` 경고. **(a)** `project_utils.py:651-659`, **(c)** `scripts/docs/project.md:88-112`가 "텍스트 동일성을 비교하지 않는다"고 직접 선언 | 검색 범위: `skills/ppt-master/scripts` 아래 tests 제외 `*.py`·`*.json`·`*.md`. 놓쳤을 가능성: `page_rhythm`이 아닌 다른 키(`pptx_layouts` 등)로 페이지 집합을 비교하는 검사, 동적 키 조립. 그래서 (b)는 `미확인`이 아니라 "이 범위에서 못 찾음"이다. 추가 확인(메인): `grep -rln "page_rhythm" skills/ppt-master/scripts/svg_quality skills/ppt-master/scripts/svg_to_pptx skills/ppt-master/scripts/svg_finalize`는 결과 없음(종료 코드 1). 그래서 final 검사기·변환기·finalize는 `page_rhythm`을 읽지 않는다. `spec_lock` 키 중 검사기가 읽는 것은 `canvas`·structured 계열이다(svg-authoring-and-quality R-28) |
| R-26 | `references/strategist.md:140-150`, `templates/icons/README.md`(경로만 인용) | 문서 선언. `icon_sync.py` 내부는 읽지 않음 |
| R-27 | `workflows/generate-pptx.md:168`, `:209-216` | 문서 선언 |
| R-28 | `workflows/generate-pptx.md:175-177` | 문서 선언 |
| R-29 | `workflows/generate-pptx.md:185-201` | 문서 선언 |
| R-30 | `workflows/generate-pptx.md:203-209`, `workflows/governance/failure-recovery.md:28-31` | 문서 선언 |
| R-31 | `workflows/generate-pptx.md:187` | 문서 선언 |
| R-32 | `workflows/generate-pptx.md:222-247`, `references/executor-base.md:261-306` 일부 | 문서 선언 |
| R-33 | `workflows/generate-pptx.md:247`, `references/executor-base.md:278` | 문서 선언 |
| R-34 | `workflows/generate-pptx.md:251`, `scripts/text_measure.py:756` | 출력 규칙은 문서 선언, 파일 위치는 코드 확인 |
| R-35 | `workflows/generate-pptx.md:253-259`, `scripts/svg_editor/server.py:45-48` | 시작·포트 규칙은 문서 선언 |
| R-36 | `workflows/generate-pptx.md:261-306`, `scripts/svg_quality/cli.py:89-110`, `:296-358`, `scripts/svg_quality/checker.py:7540-7560`, `scripts/project_utils.py:240-470` | exit 1 규칙과 보고서 이름은 코드 확인. `--stage early`의 partial roster가 roster 비교를 건너뜀은 `checker.py:7549` `if not self.partial_roster`와 `cli.py:279`(`checker.partial_roster = stage in {"early","page","first-page"}`)로 확인. cadence(언제 호출해야 하는지)는 문서 선언 |
| R-37 | `workflows/generate-pptx.md:293-306`, `workflows/governance/failure-recovery.md:36-37` | 문서 선언 |
| R-38 | `workflows/generate-pptx.md:308` | 문서 선언 |
| R-39 | `workflows/generate-pptx.md:312-316`, `workflows/routing.md:54-58` | 문서 선언 |
| R-40 | `workflows/generate-pptx.md:245`, `workflows/governance/failure-recovery.md:24` | 문서 선언 |
| R-41 | `workflows/generate-pptx.md:259`, `workflows/governance/failure-recovery.md:35` | 문서 선언 |
| R-42 | `workflows/generate-pptx.md:322-324` | 문서 선언 |
| R-43 | `workflows/generate-pptx.md:326` | 문서 선언 |
| R-44 | C-08. `scripts/total_md_split.py:40-115`, `:137-208`, `:211-232`, `:235-275`, `:278-376`; 번호 정렬 C-14 | 코드 확인. 실패 시 아무 파일도 쓰지 않음은 `main`에서 `split_notes` 호출 전 `sys.exit(1)`(`:328-352`)로 확인. 문서 `artifact-ownership.md:47`은 `notes/slide_*.md`라고 쓰지만 실제는 SVG stem 이름(`:257`) |
| R-45 | C-09. `scripts/finalize_svg.py:127-170`, `:341-400`, `:255-312`. `workflows/generate-pptx.md:336-342`, `:368` | 코드 확인. 문서(`generate-pptx.md:368`)는 "재번호 뒤 `svg_final/`의 페이지별 파일을 먼저 지운다"고 하지만 코드는 디렉터리 전체를 교체하므로 불필요하다(불일치, 구현을 사실로 씀). 단 `finalize_svg.py`의 `--only` 모드가 부분 처리를 할 때도 같은지는 읽지 않았다 |
| R-46 | `workflows/generate-pptx.md:344-362`, `scripts/svg_to_pptx/pptx_package/cli.py:2312-2320`(notes 플래그), `:2044-2054`(docstring) | 플래그 의미(`--native-charts-and-tables`, `-a`, `--no-animations`, `--image-sizing`)의 구현은 읽지 않음 |
| R-47 | C-10, C-13. `scripts/svg_to_pptx/pptx_package/cli.py:2683-2712`, `:3160-3185`, `:3884-3955`; `builder.py:2152-2178`, `:8131-8137`; `discovery.py:61-106`; 문서 `generate-pptx.md:364` | 코드 확인. "fingerprint가 다르면(낡음) 거부"의 판정 함수 `_quality_gate_status`·`_quality_report_context`는 호출만 확인했고 본문은 읽지 않았다(통과 아니면 `quality_gate != 'passed'`로 exit 1). `-o` 사용 시 backup 없음은 `cli.py:2002` 사용 예와 `:2694-2712`로 확인 |
| R-48 | `workflows/generate-pptx.md:370-378` | 문서 선언 |
| R-49 | `workflows/generate-pptx.md:368`, 비교 R-44·R-45 | 문서 선언 + 코드 대조 |
| R-50 | `workflows/governance/failure-recovery.md:9`, `:15-43`, `:47-61`, `:67-88` | 문서 선언 |
| T-01~T-21 | 해당 R-ID의 근거. T-14는 `finalize_svg.py:127-170`·`:341-400`, T-13은 `total_md_split.py:40-115`, T-10은 `project_utils.py:412-470`·`checker.py:7549-7557` | 모두 코드 읽기에서 도출. 실행해 보지 않았다 |

**문서(README·docs)와 구현이 다른 곳** (구현을 사실로 썼다):
- `references/artifact-ownership.md:47`은 분할 노트를 `notes/slide_*.md`라고 쓰지만 `total_md_split.py:257`은 `<SVG stem>.md`를 쓴다(`discovery.py:99-106`은 두 규약을 모두 읽는다).
- `workflows/generate-pptx.md:368`은 재번호 뒤 `svg_final/`의 페이지별 파일을 먼저 지우라고 하지만 `finalize_svg.py`는 `svg_final/`를 통째로 교체한다(R-45). 반대로 `notes/`의 옛 파일은 지워지지 않는다(`total_md_split.py:371-377`은 advisory만).
- `references/artifact-ownership.md:43`은 `template_install.json`을 `confirm_ui/` 경로와 같은 행에 두지만 코드는 프로젝트 루트에 쓴다(`apply_template.py:473`, 서버의 검증은 `server.py:742-751`).
- `workflows/generate-pptx.md:162`·`references/strategist.md:19`는 `validate`가 설계 문서의 존재와 정합을 책임지는 것처럼 읽히지만 코드는 설계 문서 부재를 경고로만 취급한다(`project_utils.py:651-657`)(R-25).
- `scripts/docs/project.md:88-112`는 `validate`가 값의 텍스트 동일성을 비교하지 않는다고 하는데, 코드는 §I Page Count ↔ §IX 블록 수, lock `canvas`와 디렉터리 이름의 포맷을 비교한다(`project_specs.py:889-894`, `:1232-1259`). 설계 문서와 lock 사이 값 비교는 실제로 없다.

### 2.2 코드 읽는 순서 [선택]

1. 문서: `SKILL.md`(로드 순서·전역 규율) → `workflows/routing.md`(§2·§3 표) → `workflows/generate-pptx.md`(Step 1~7과 Revision Round. 길지만 단계 순서·gate·명령의 권위) → `workflows/governance/failure-recovery.md`(§1 표와 §3 재개 표) → `references/artifact-ownership.md`(§1 표가 C1의 문서 판).
2. Step 4의 내용 계약: `references/strategist.md` §1(확인 단계)과 §6.2(설계 문서·lock 작성 규칙), `references/plan-core.md`(소통 계약·roster·자원·시각 시스템 규칙, 본문은 이 스펙이 풀지 않음), `templates/design_spec_reference.md`, `templates/spec_lock_reference.md`. 검증기 쪽은 C-04~C-06.
3. Step 6의 내용 계약: `references/executor-base.md`(페이지 표현 규칙, §2 청사진 수용, §3 실행 지침), `references/shared-standards-core.md`와 `scripts/docs/svg-contract.md`(SVG 문법, 별도 스펙).
4. 스크립트 순서(코드 따라가기): `project_manager.py` → `project_management/cli.py`(`init_project`, `import_sources`, `validate_project`) → `project_utils.py`(검증) → `total_md_split.py` → `finalize_svg.py` → `svg_to_pptx/pptx_package/cli.py`(`main`). 원본의 전략은 "단계마다 파일을 남기고 다음 단계가 그 파일만 읽는다"이다(C1이 그 목록).

### 2.4 검토 기록 [필수, ready 스펙]
- 방식: 메인 점검 + 독립 검토(검토자 서브에이전트, 읽기 전용). 다른 스펙(`svg-to-pptx-cli`, `image-file-contract`, `confirm-and-preview-ui`)이 `depends`로 의존하므로 독립 검토를 돌렸다.
- 대조한 R-ID: 메인이 R-09, R-10, R-24, R-44, R-45, R-47과 `validate`의 `workflow.log` append(`workflow_transcript.py:302-347`), report.json 이름(`pptx_package/cli.py:1473`), backup의 payload store 복사(`:3900-3912`)를 직접 열어 확인. 검토자가 C1 전 항목과 R-01, R-09, R-10, R-14, R-24, R-25(a), R-36, R-44, R-45, R-47, `--wait-only` 종료 코드, C2 lock 섹션, 줄 범위 C-01~C-15를 대조. 불일치 R-24(workflow.log append), C1의 report.json 이름과 backup 내용, R-47의 `NotesFileReadError`, C-09 줄 범위, C2 선택 섹션 `page_charts`, R-44·R-45 보강은 반영함.
- 대조하지 않은 R-ID: R-11~R-13, R-15~R-23, R-26~R-35, R-37~R-43, R-46, R-48~R-50은 대부분 문서 선언(`generate-pptx.md`·`failure-recovery.md`)을 읽은 것이고 코드 쪽 강제를 따라가지 않았다. `import_sources` 내부 분류(`cli.py:848-1224`)와 schema 필드 문법 전체는 읽지 않았다.
- 재구현: 미수행

## 적용 메모

없음(원본 동작만 썼다. 이 스펙을 읽는 환경에서 정할 점은 아래 두 가지만 기록한다).

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-25 | (제안, 미확정) 외부 연동 시 Step 4 gate에서 `design_spec.md`·`spec_lock.md` 두 파일의 존재와 `page_rhythm` ↔ §IX 일치를 직접 확인 | `validate`가 이 구간을 보장하지 않는다 | gate가 한 단계 늘어남. 원본 동작은 바뀌지 않음 |
| R-47 | (제안, 미확정) 노트 켜짐인데 `notes/<stem>.md`가 없으면 내보내기 전에 막기 | 원본 exporter는 노트 없이도 성공한다: `find_notes_files`가 빈 매핑을 주고 슬라이드 쪽은 빈 노트면 아무것도 추가하지 않는다(`pptx_package/cli.py:3326-3333`, `builder.py:2181-2185`, 메인이 직접 읽음) | 7.3 선행 조건에 노트 존재 검사 추가 |
