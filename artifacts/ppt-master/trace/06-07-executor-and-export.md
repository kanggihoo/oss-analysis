# ppt-master 실행 trace: Step 6 (Executor) · Step 7 (후처리와 내보내기)

- 기준: `repos/ppt-master` `3af3e8e`, 프로젝트 `projects/portfolio_demo_20261119`
- 실행 일자: 2026-11-19
- 앞 단계: [04c-design-spec-and-lock.md](04c-design-spec-and-lock.md)
- 산출물 사본: [`snapshots/`](snapshots/)에 `svg_output/*.svg` 7개, `notes/total.md`, 내보낸 `.pptx`, 내보내기 보고서, final 품질 보고서를 복사했다.
- 실행 주체: 이 세션의 agent가 `generate-pptx.md` Step 6~7을 따라 직접 SVG를 썼다. 따라서 이 trace는 "문서를 읽은 agent가 이 파이프라인을 끝까지 돌릴 수 있는가"를 보여 주고, "스펙만으로 재현되는가"는 검증하지 않는다.

## 1. Step 6 흐름과 호출

| # | 호출 | 받은 것 | 나온 것 |
|---|---|---|---|
| 1 | reference 읽기 | `executor-base.md` 전체, `shared-standards-core.md` 전체, `semantic-svg.md`, `modes/pyramid.md`, `visual-styles/swiss-minimal.md`, 표 경로용 `executor-visualization.md`, `executor-table.md`, `native-data-interface.md` | agent context. 로스터를 훑어 triggered module을 정했다: core, table(P06), native-data(P06), notes(마지막) |
| 2 | `visualization_recall.py validate table/record_table` | `table/record_table` | `templates/tables/record_table.svg`로 resolve. 이 SVG는 구조 참고용으로 앞 3500자만 읽었다 |
| 3 | `text_measure.py calibrate <project> --outline` | `spec_lock.md`의 역할 7개 | 역할별 "100px당 글자 수" 표. `04`의 설계서 긴 제목이 42px에서 2줄이 된다는 근거(`06-text-calibrate.out`) |
| 4 | `svg_editor/server.py <project> --live --daemon` | 프로젝트 경로 | `http://127.0.0.1:6060`, `pid=47848`. Bash 호출이 끝난 뒤에도 살아 있었다(`live_preview/lock.json`: `{"pid": 47848, "port": 6060}`) |
| 5 | 설계 파라미터 확인 출력 | 목표, canvas, 본문 크기, 색, 글꼴, 보정표, preview URL | 대화 메시지 1개. 파일은 만들지 않는다 |
| 6 | SVG 5개(P01~P05) 직접 작성 | `design_spec.md` §IX, `spec_lock.md`, 위 reference | `svg_output/01_표지.svg` ~ `05_배포자동화.svg` |
| 7 | **early gate** `svg_quality_checker.py <project> --canonical-authoring --stage early --json` | P01~P05 | 종료 0. 5개 전부 Passed, 0 warning. `validation/svg_quality_early_report.json`. 7장 로스터라 이 gate가 실행됨 |
| 8 | SVG 2개(P06, P07) 작성. P06은 `data-pptx-replace-with="table"` marker + JSON `<metadata>` + 가시 fallback | | `06_기술역량.svg`, `07_맺음.svg` |
| 9 | `stamp_native_fallbacks.py <P06.svg>` (dry) → `--write` | | `would-update` → `updated`. `data-pptx-fallback-sha256="314de2e5…"`가 `<g id="skills-table">`에 기록됨 |
| 10 | **final gate 1차** `… --stage final --json` | 7장 | 종료 0, error 0, warning 3개(전부 `06`의 표). `validation/svg_quality_report.json` |
| 11 | 표 JSON 보완(consolidated repair): `columns[0,2].align: "l"`, 줄무늬 행 2개(PostgreSQL, AWS)의 cell `fill` | warning 3개 | JSON만 고침 |
| 12 | `stamp --write` 재실행 → **final gate 2차** | | stamp는 `unchanged`, final gate는 7/7 Passed, warning 0 |
| 13 | `notes/total.md` 작성 (`executor-notes.md` §1~2 규칙) | 7개 최종 SVG | 7개 소절(`# 01_표지` … `# 07_맺음`), `---`로 구분 |

### Early gate 직후 쓰라고 한 한 줄

`gate-signal: method=none | page-local=0 | not-exercised=table, native-data marker, 아이콘 외 icon 사용 확인(P06·P07), 맺음말 anchor 페이지`

early gate가 한 번도 이슈를 내지 않아서 "method-level bias" 판단이 필요한 경우가 없었다.

### final gate 1차의 warning 3개와 원인

모두 `06_기술역량.svg`의 `skills-table` marker에서 나왔고, 메시지 끝에 `(blocks --native-charts-and-tables export)`가 붙어 있다. 이 gate의 종료 코드는 0이었다.

- `columns[].align "l"`: header 셀이 align을 안 쓰면 가운데 정렬로 내보내지는데, fallback은 왼쪽 정렬이었다
- `whole row 3 fill #F3F5F8 is not projected to cell fill`, `row 5`: fallback에 그린 줄무늬 행 색이 JSON의 셀 `fill`에 없었다. 1-based 행 번호이고 header가 1행이라 PostgreSQL(3행)과 AWS(5행)다

JSON만 고치면 되는 문제였고 가시 fallback은 건드리지 않았다. 고친 뒤 stamp를 다시 돌렸더니 `unchanged`였다. 해시가 가시 fallback만 대상으로 하고 JSON 변경은 포함하지 않는다는 뜻으로 읽힌다(`추론`, 코드 미확인).

### Carrier receipt (final gate 출력) 와 "absence needs a reason"

`Pages: 7 | text: 88 | images: 0 | icons: 7 | native presets 0 | inline emphasis 2 (pages 2) | gradients 0 | filters 0 | Native objects: tables 1`, `Relationship pages: 4 | pages carrying a preset or connector: 0`.

`executor-base.md` §3은 이 영수증에서 "없음"인 항목마다 이유를 한 줄 쓰라고 한다. 이번 run의 이유:

- native preset 없음, connector 없음: swiss-minimal은 직각과 단일 굵기 선만 쓴다. 순서·소속 관계는 번호 숫자, 좌→우 세 구역, 정렬로 표현했다. 화살표 preset을 넣지 않은 선택이고 문서 규칙상 "reason"이 필요한 항목이다
- gradient 0, filter 0: 확정된 `visual_style_behavior`가 "No gradients, no shadows"를 정했다
- inline emphasis 2: P04의 `35%`, P05의 `22회`에만 accent를 썼다. 나머지는 굵기로 구분했다

## 2. 규칙과 달랐던 점 (agent가 하지 않은 것)

- `references/preset-shape-vocabulary.md`는 Step 6의 "REQUIRED core" 목록에 있는데 읽지 않았다. 이번 덱은 사각형과 선만 써서 preset이 필요 없었지만, 문서 규칙은 "read before page one"이다.
- `generate-pptx.md`는 페이지마다 `P<NN> modules: …` 한 줄을 쓰라고 하는데, P01과 P06만 썼다.
- P05 뒤에 `spec_lock.md`를 한 번 전체 다시 읽는 "five-page lock re-read"를 하지 않았다. context가 압축되지 않았고 값이 외부에서 바뀌지 않았다고 판단했다.
- 페이지를 렌더링한 그림은 보지 못했다. live preview가 떠 있지만 agent가 화면을 볼 수 없어서, 레이아웃과 글자 겹침은 `final gate`의 bounds 검사로만 확인했다. 시각 확인은 사용자 몫이다.
- `Design Parameter Confirmation`은 대화 메시지로 한 번 냈다. 형식은 문서의 항목(목표, canvas, 본문 크기, 색, 글꼴, 보정표, preview URL)을 따랐다.
- 확정된 팔레트의 대비 규칙(`#E58A00` on 흰색 2.64:1)은 설계서에 사용 규칙으로 적었고, 이번 SVG에서 accent 글자는 남색 위에서만 썼다(P01 `0.4초`, P03 `1.8초`, P04 `0.4초`·`35%`, P05 `8분`·`22회`). 흰 바탕 위에서 accent는 막대(채움 도형)에만 썼다. 이 규칙을 검사하는 항목은 checker 출력에서 보이지 않아, 지켜졌는지는 SVG를 직접 본 것이다.

## 3. Step 7 (후처리와 내보내기)

문서는 "한 명령씩 따로 실행하고 앞 명령이 성공했을 때만 다음으로"라고 한다. 그대로 따랐다.

| 단계 | 명령 | 결과 |
|---|---|---|
| 7.1 | `total_md_split.py <project>` | `Found 7 SVG file(s)`, `Found 7 notes section(s)`, "one-to-one correspondence". `notes/<SVG 이름>.md` 7개 생성, 종료 0 |
| 7.2 | `finalize_svg.py <project>` | `[1/3] Expanding icons`(`02` 2개, `05` 3개, `07` 2개, 합계 7개 embed) → `[2/3] Aligning + embedding images`(`No images`) → `[3/3] Flattening text`(7 file). `svg_final/` 7개, 종료 0 |
| 7.3 | `svg_to_pptx.py <project>` (노트가 켜져 있어 `--no-notes` 없음, `--native-charts-and-tables` 없음) | `exports/portfolio_demo_20261119_170127.pptx`(42,694 bytes). `[POSTFLIGHT] status=passed quality_gate=passed slides=7 warning_categories=0`. 보고서 `validation/portfolio_demo_20261119_170127.report.json`, 백업 `backup/20261119_170127/svg_output` |

7.3의 출력에서 확인한 것:
- `Mode: Native DrawingML shapes (directly editable)`, `Native table/chart objects: Chart/Table replacement disabled`, `PPTX structure: flat`, `Transition effect: Fade`, `Speaker notes: 7 page(s)`
- 슬라이드별 `Converted N elements, skipped 0, promoted 1 background`. 모든 슬라이드가 `(Native) +notes`
- `Flat structure: project-owned Master + Blank Layout (10 stock layout(s), 2 stock content shape(s) removed, 6 system footer hook(s) retained)`
- 내보내기는 `svg_output/`을 읽는다(`svg_final/`은 읽지 않는다). 이번 출력에서 `svg_output backup`이 `svg_output`을 가리켰다

### 결과 파일을 직접 열어 본 것 (python-pptx)

- 슬라이드 7개, 크기 1280×720 px, 슬라이드마다 notes가 있다(첫 글자 비교: `안녕하세요, 4년 차 백엔드 개발자 김도윤입니다…` 등 `notes/total.md` 문장과 일치)
- 모든 텍스트가 그룹 안의 네이티브 텍스트 shape로 들어 있다(그룹을 풀어 세면 슬라이드별 텍스트 shape 8, 6, 14, 15, 20, 20, 5개). 예: 슬라이드 2의 제목은 `4년차 백엔드 개발자,` + 줄바꿈 + `느린 API를 측정으로 찾아 고칩니다`
- 표(P06)는 PowerPoint 표 객체가 아니다(`has_table` 0). `--native-charts-and-tables`를 쓰지 않았으므로 문서 규칙대로 shape와 텍스트로 변환됐다. 네이티브 표 변환은 이번 run에서 실행하지 않았다

## 4. 확인하지 못한 것

- 실제 PowerPoint(또는 LibreOffice)로 열었을 때의 모양. 글꼴 `Malgun Gothic`이 대상 PC에 있어야 같은 폭으로 보인다
- 줄바꿈과 겹침의 육안 확인(위 2절)
- `--native-charts-and-tables` 변환과 그 경로의 parity 경고 해소 여부(이번에는 warning 3개를 JSON 보완으로 없앴지만, 그 export는 실행하지 않았다)
- Step 5(이미지 확보)는 이미지 출처가 `none`이라 건너뛰었다
- animations, narration audio, verify-charts, visual-review는 조건이 없어 실행하지 않았다
- live preview 서버(`pid=47848`)는 문서 규칙대로 사용자가 **Exit preview**를 누르거나 요청할 때까지 두었다. 아직 내리지 않았다

## 5. 이 run의 최종 산출물 목록

`projects/portfolio_demo_20261119/`(원본은 `repos/` 아래라 `commit` 대상이 아니고, 핵심은 `snapshots/`에 복사):
`sources/portfolio.md`, `design_spec.md`(208줄), `spec_lock.md`(68줄), `icons/tabler-outline/*.svg` 10개, `svg_output/*.svg` 7개, `notes/total.md` + 슬라이드별 `.md` 7개, `svg_final/*.svg` 7개, `exports/portfolio_demo_20261119_170127.pptx`, `validation/{svg_quality_early_report.json, svg_quality_report.json, text_calibration.json, portfolio_demo_20261119_170127.report.json, workflow.log}`, `confirm_ui/*`, `backup/20261119_170127/svg_output/`.
