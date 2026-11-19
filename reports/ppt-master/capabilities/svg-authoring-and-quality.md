---
sha: "3af3e8ef774c4d67ee57e1306d9256d08c9ee1bf"
created: 2026-11-17
updated: 2026-11-17
sources:
  - skills/ppt-master/references/shared-standards-core.md
  - skills/ppt-master/references/shared-standards.md
  - skills/ppt-master/references/semantic-svg.md
  - skills/ppt-master/references/native-shape-authoring.md
  - skills/ppt-master/references/svg-image-embedding.md
  - skills/ppt-master/scripts/docs/svg-contract.md
  - skills/ppt-master/scripts/svg_quality_checker.py
  - skills/ppt-master/scripts/svg_quality/cli.py
  - skills/ppt-master/scripts/svg_quality/checker.py
  - skills/ppt-master/scripts/svg_authoring_contract.py
  - skills/ppt-master/scripts/slide_roster.py
  - skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py
  - skills/ppt-master/scripts/svg_to_pptx/pptx_package/discovery.py
  - skills/ppt-master/workflows/generate-pptx.md
  - skills/ppt-master/workflows/profiles/quick-generate.md
  - skills/ppt-master/workflows/stages/verify-charts.md
  - skills/ppt-master/workflows/stages/visual-review.md
  - skills/ppt-master/workflows/governance/failure-recovery.md
depends: []
status: ready
---

# SVG 작성 계약·품질 검사

> agent가 페이지마다 쓰는 SVG(`svg_output/*.svg`)에 대해, 허용 문법(C3)을 알려 주고 `svg_quality_checker.py`가 단계(early/final 등)별로 검사해 `validation/svg_quality_*report.json`을 쓰며, final 보고서(C4)가 `svg_to_pptx` 내보내기의 gate가 되는 기능이다. 15행(차트 좌표 보정·시각 검토·실패 복구)의 트리거와 입출력도 여기서 다룬다.

<!--
경로 표기: 이 문서의 `skills/ppt-master/...`는 repos/ppt-master 기준이다. SKILL_DIR = repos/ppt-master/skills/ppt-master.
용어: "checker" = `svg_quality_checker.py`(wrapper)가 위임하는 `svg_quality/checker.py`의 SVGQualityChecker. "exporter" = `svg_to_pptx.py` → `svg_to_pptx/pptx_package/cli.py`.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

1. agent(Executor)가 `svg_output/`에 페이지 SVG를 하나씩 쓴다. 쓰는 형태는 C3(허용 문법 표 1.3과 reference 문서)를 따른다.
2. 페이지 5장을 쓰면(계획 로스터가 7장 이상일 때만) early 검사를 한 번 돌린다: `svg_quality_checker.py <project> --canonical-authoring --stage early --json` → `validation/svg_quality_early_report.json`. 지금까지 쓴 모든 페이지를 부분 로스터 규칙으로 검사한다.
3. agent는 한 번의 실행으로 나온 issue 전체를 보고 한꺼번에 고친 뒤 한 번 다시 돌린다(개별 수정마다 돌리지 않는다. 워크플로 규칙).
4. 모든 페이지를 쓴 뒤, 데이터 차트가 있으면 verify-charts(1.4 R-22)로 좌표를 보정한다.
5. final 검사를 돌린다: `svg_quality_checker.py <project> [--quick-generate] --canonical-authoring --stage final --json` → `validation/svg_quality_report.json`(C4). 검사 오류가 하나라도 있으면 exit status 1이지만 보고서는 그래도 쓰인다.
6. (사용자가 명시 요청한 경우만) visual-review(R-23)를 돈다.
7. `svg_to_pptx.py`가 `validation/svg_quality_report.json`을 읽어 현재 `svg_output/`의 fingerprint와 맞고 blocking이 0이고 stage가 `final`인지 확인한 뒤에만 변환한다. 아니면 오류와 재실행 명령을 출력하고 exit 1.

### 1.2 범위·통합 지점 [필수]

- 제공: (a) SVG 작성 계약 C3의 요약과 원문 위치, (b) checker의 CLI·단계·보고서 계약, (c) final 보고서를 exporter gate로 쓰는 계약 C4, (d) verify-charts·visual-review·failure-recovery의 트리거와 입출력.
- 제외: checker 개별 검사 규칙 본문(C-ID로 위치만), `svg_to_pptx` 변환 내부(스펙 `svg-to-pptx-cli`), Strategist/Executor의 디자인 판단, 이미지 확보(이미지 파일 규약 스펙), `finalize_svg.py`, `--template-mode`(템플릿 워크스페이스 검사)·`--roundtrip`(PPTX 편집 경로)의 상세. 이 둘은 CLI 표에서 존재만 적는다.
- 외부 의존·선행 계약: 없음(선행 스펙 없음). 입력은 프로젝트 디렉터리의 `svg_output/`, 있으면 `design_spec.md`·`spec_lock.md`. Python 표준 라이브러리 위주이나 checker가 `svg_to_pptx/drawingml/*`의 검증기를 공유해 import한다(svg-contract.md 서두). 따라서 checker 단독 이식은 불가능하고 exporter의 검증 모듈이 함께 필요하다.
- 소유 상태·부작용: checker는 `svg_output/`을 읽기만 하고 SVG를 고쳐 쓰지 않는다(R-11). 쓰는 것은 `validation/svg_quality_{,early_,first_page_,page_}report.json`과 `--export`가 주는 텍스트 보고서뿐이다. exporter는 보고서를 읽기만 한다(고치지 않는다). gate 판정 외에도 receipt(`validation/<stem>.report.json`)에 `quality_gate`·`quality`·`quality_introduced_warnings`를 기록하려고 항상 읽는다(R-26).

### 1.3 인터페이스와 데이터 의미 [필수]

**(A) C3 — SVG 작성 계약 요약 표.** 원문이 이미 있는 항목은 위치만 쓴다. 규칙 전체는 `fail-closed`다(R-01).

| 주제 | 허용·요구 | 금지·오류 | 원문 위치 |
|---|---|---|---|
| XML | 엄격한 XML. 타이포 기호는 원문 Unicode(`—` `©` `→`), 예약문자는 `&amp; &lt; &gt; &quot; &apos;` | HTML 이름 엔티티(`&nbsp;` `&mdash;`), 맨 `&` `<` | core §1.0 |
| 전역 금지 | — | `mask`, `<style>`, `class`, 외부 CSS, `<foreignObject>`, `textPath`, `@font-face`, `<animate*>`/`<set>`, `<script>`·event 속성, `<iframe>` | core §1.0 |
| inline `style` 허용 속성 | paint/line(`fill stroke stroke-width stroke-dasharray stroke-linecap stroke-linejoin fill-opacity stroke-opacity vector-effect`), text(`font-family font-size font-weight font-style text-anchor letter-spacing text-decoration`), alpha(`opacity stop-color stop-opacity flood-color flood-opacity`), 리터럴 geometry, `shape-rendering` | 그 밖의 inline 속성, `!important`, blend mode 등. `filter`·`clip-path`·`marker-start/end`·`<tspan>`의 `baseline-shift`는 style이 아니라 직접 속성 | core §1.0, svg-contract §1 |
| 길이 단위 | `x y width height rx ry cx cy r x1…y2 dx dy stroke-width`는 viewBox 공간의 단위 없는 소수(`x="120"`) | `px`는 읽기 호환(경고). 다른 단위·%·수식은 오류 | core §2.1, svg-contract §2.1 |
| 캔버스 | 루트 `viewBox="0 0 W H"`(W,H 양의 정수 px). 한 빌드의 모든 페이지가 같은 viewBox. 1 SVG px = 9,525 EMU | 0이 아닌 원점, 비양수 크기, 루트 `transform`. 루트 `width/height`는 viewBox를 덮어쓰지 못함 | core §4.1, svg-contract §4 |
| 색 | 새 단색은 대문자 `#RRGGBB`, 또는 `none`, 또는 로컬 `url(#id)` | 루트에 paint/effect | core §1.0 Default |
| 텍스트 | 비어 있지 않은 `font-family`(보이는 텍스트가 있으면 루트에 직접), `font-size`는 양의 단위 없는 px, `font-weight` `normal/bold/100~900`, `text-anchor`는 `<svg>`·`<g>`·`<text>`에만 | `<tspan>`의 `text-anchor` | core §1.0, svg-contract §1 |
| 줄 구성 | 한 단락 = `<text>` 하나, 이어지는 줄은 `<tspan x=부모x dy=양수>`. 행간은 `dy`로 쓴다 | CSS `line-height`, 같은 단락을 형제 `<text>`로 쪼개기(휴리스틱 경고) | core §4.2 |
| 그룹핑 | 보이는 최상위 `<g>`마다 페이지 안에서 유일한 설명적 `id`와 `data-pptx-bounds="x y w h"`. 의미 단위 하나 = 그룹 하나(애니메이션 앵커) | 슬라이드 전체를 감싸는 `<g>` 하나, 그룹 없는 낱개 요소 다수, 익명 최상위 그룹 | core §4.3 |
| 구조 마커 | 평면(flat) 페이지는 루트에 `data-pptx-page-role`(`cover/toc/section/content/ending`) 하나. 구조형(structured) 페이지는 `data-pptx-master/-layout`(+`-name`), 루트 직계 원자에 `data-pptx-layer="master\|layout"`, 슬롯 `<g id data-pptx-placeholder data-pptx-bounds>` + `data-pptx-carrier="true"` 자식. 프레임 역할은 `data-pptx-role`(`background decoration header footer logo watermark chrome page-number`) | flat에 Master/Layout/layer/placeholder 마커, structured에 `page-role`. 마커를 제거해도 브라우저 렌더링은 같아야 함 | semantic-svg §1~§4 |
| 네이티브 객체 마커 | 차트·표는 `data-pptx-native-authority`, `data-pptx-replace-with`, plot 영역 마커 등(`native-data-interface.md`, 본 스펙 범위 밖) | 마커를 손으로 만든 값 | core §4, native-data-interface.md |
| 선 끝 마커 | `<line>`·`<path>`의 `marker-start/end`가 `<defs>`의 로컬 `<marker orient="auto">` 하나를 참조. 자식은 삼각형·stealth·open arrow·diamond·oval 5형태 | 그 밖의 marker 모양 | core §1.1, svg-contract §1.1 |
| 이미지 | `<image href="../images/x.png" x y width height preserveAspectRatio="xMidYMid slice\|meet\|none"/>`. `svg_output/`에는 외부 상대 참조를 둔다 | `data:` href는 `svg_final/` 미리보기 형태이지 작성 형태가 아님. `clip-path`는 `<image>`에만(정확히 한 도형의 로컬 `<clipPath>`) | svg-image-embedding.md, core §1.2 |
| `<use>` | 같은 문서 `href="#id"`(`<symbol>` 또는 요소). 아이콘은 `<use data-icon="library/name">`(별개 형식) | 재사용 대상에 layer·placeholder·차트/표 마커 | core §1.3, §4.1 |
| 네이티브 preset 도형 | `preset_shape_svg.py render …`가 출력한 `<g data-pptx-authoring="preset">` 조각을 그대로 삽입 | 그 메타데이터·path를 손으로 쓰거나 편집(검사가 다시 렌더해 어긋나면 실패) | core §1.5, native-shape-authoring.md |
| 투명도 | 하위 요소 paint에 alpha | `<g opacity>`는 허용하되 근사(경고만) | core §2.2 |

**(B) checker CLI** (`python3 scripts/svg_quality_checker.py <target> [옵션]`, 외부 계약이므로 원문 이름)

| 옵션·인자 | 의미·기본값·잘못된 입력 |
|---|---|
| `<target>` | 첫 인자. SVG 파일, 디렉터리, 프로젝트 디렉터리, 또는 `--all <base>`(기본 `projects`). 첫 인자가 `--all` 아닌 `--옵션`이면 오류 exit 1. 인자 없음·`-h/--help/help`는 usage 출력 후 exit 0 |
| `--stage early\|first-page\|page\|final` | 기본 `final`. 그 밖의 값, 값 누락은 `[ERROR]` exit 1. 단계별 차이는 R-12 |
| `--page <basename\|path>` | `--stage page`에서만, 그때는 필수. `svg_output/` 아래의 기존 `.svg`로 풀려야 하며 아니면 오류 exit 1 |
| `--json` | JSON 보고서를 쓴다. 경로는 R-14. stdout은 사람이 읽는 요약이고 JSON이 아니다 |
| `--json-output <path>` | 보고서 경로를 덮어쓴다(이것만 줘도 JSON을 쓴다). 경로 누락 오류 |
| `--export` / `--output <path>` | 텍스트 보고서(기본 `svg_quality_report.txt`, 현재 디렉터리) |
| `--format <ppt169\|ppt43\|…>` | 기대 canvas format. `CANVAS_FORMATS`에 있으면 그 viewBox를 계약에 추가한다. **없는 값은 무시되지 않고 오류**(`Unsupported canvas format: X`, `checker.py:2663-2669`). 값 자체가 명령줄에 없을 때만 조용히 무시된다 |
| `--canonical-authoring` | 컴팩트 작성 형태에서 벗어난 것을 경고로 보고한다. 소스를 고쳐 쓰지 않는다(R-11) |
| `--quick-generate` | lockless Quick 프로젝트용: `design_spec.md`·`spec_lock.md`를 무시하고 첫 SVG로 canvas를 정하며 완전한 로스터에서 flat/structured를 추론. `--template-mode`와 같이 못 씀, `--all`과도 못 씀 |
| `--roundtrip`, `--template-mode`, `--slot-capacity-report` | 각각 PPTX 편집 workspace 검사, 템플릿 workspace 검사, 슬롯 용량 advisory JSON. 본 스펙 범위 밖. `--roundtrip`은 `--stage/--format/--page/--all/--template-mode/--quick-generate/--canonical-authoring`와 같이 못 씀 |

**(C) 보고서 파일(C4의 일부).** 이름은 단계가 정한다.

| stage | 기본 파일 | 읽는 쪽 |
|---|---|---|
| `final` | `validation/svg_quality_report.json` | exporter gate(R-18) |
| `early` | `validation/svg_quality_early_report.json` | agent(사람) |
| `first-page` | `validation/svg_quality_first_page_report.json` | agent |
| `page` | `validation/svg_quality_page_report.json` | agent |

**(D) 보고서 구조(`ppt-master.svg-quality-report.v1`).** exporter가 읽는 필드만 `★`로 표시한다.

| 필드 | 의미 |
|---|---|
| `schema` ★ | 고정 문자열 `ppt-master.svg-quality-report.v1`. 다르면 exporter는 `unsupported-schema` |
| `stage` ★ | 위 4값 중 하나 |
| `source_fingerprint` ★ | `{algorithm:"sha256", digest, file_count, files:[{file, sha256}]}`. 이름순 파일마다 `이름 \0 파일sha256 \n`을 이어 붙인 sha256 |
| `categories.blocking.{count ★, issues}` | 오류. 파일 단위(`file`,`message`)와 프로젝트 단위(`scope`,`message`: template·animation·illustration·communication_trace·pptx_structure) |
| `categories.introduced` | 경고. `count`만 exporter 출력에 쓰임(`quality_introduced_warnings`) |
| `categories.inherited` | 원본(prototype·mirror)에서 그대로 온 정보성 항목. gate에 영향 없음 |
| `categories['source-import']` | 소스 import 경고 요약. gate에 영향 없음 |
| `summary`, `issue_types`, `drift`, `carrier_receipt`, `project_issues`, `files` | 검사 요약·상세. exporter는 `summary`를 읽어 컨텍스트에 싣지만 gate 판정에는 안 쓴다 |

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 생성 SVG(`svg_output/`)에 허용 목록에 없는 inline 시각 속성이나 매핑 없는 conditional 계약이 있다 | checker와 exporter 사전검사가 같은 검증기를 쓰므로 둘 다 오류로 본다. 호환 철자는 경고만 내고 막지 않는다 | 코드 확인(checker는 `svg_contracts.py:730-745`에서, exporter는 `drawingml/converter.py:2212`에서 같은 `project_geometry_length_errors`/길이 파서를 호출) |
| R-02 | XML이 well-formed가 아니다(HTML 엔티티, 맨 `&`·`<`) | 그 파일에 `Invalid XML` 오류. 이후 파싱 기반 검사는 건너뛴다 | 코드 확인 |
| R-03 | 전역 금지 요소·속성(`<style>`, `class`, `mask`, `foreignObject`, `textPath`, 애니메이션, script 등)이 있다 | 오류. 위치는 `svg_contracts.check_forbidden_elements` 등 C-04 | 코드 확인(함수 존재·호출), 개별 판정은 문서 의존 |
| R-04 | geometry 길이에 단위 `px`가 있다 / `px` 외 단위·%·수식이 있다 / 숫자 철자가 틀리다 / 음수 불가 속성에 음수가 있다 | `px` 단위와 비-canonical 철자(`120.0` 등)는 경고(Recommendation). `px` 외 단위·%·수식, 숫자 철자 오류(앞 `+`, 지수 표기, 끝 소수점 `120.` 등), 음수 불가 속성(`width`·`height`·`r`·`rx`·`ry`·`stroke-width` 등)의 음수는 오류. 잘못된 명시값은 기본값으로 대체되지 않는다. **fail-open 경로**: `svg_to_pptx`의 길이 검증기 import에 실패하면 오류가 아니라 경고 한 줄(`Unable to import svg_to_pptx geometry length validators…`)만 내고 이 검사를 건너뛴다(`svg_contracts.py:736-745`, 직접 읽음) | 코드 확인(`svg_contracts.py:730-775`, 검토자가 `drawingml/utils.py:444-462`의 파서까지 확인) |
| R-05 | 최상위 보이는 `<g>`에 `data-pptx-bounds`가 없거나, 두 root 그룹이 양 축 모두 1px 넘게 겹치거나, 그룹 텍스트가 bounds를 넘는다 | 겹침 1px 초과는 오류. 모듈 경계 초과는 5%까지 경고, 5% 초과는 오류. 루트 viewBox를 넘는 텍스트 초과는 오류. 구조 슬롯·구조 role 그룹·off-canvas Morph 끝점은 겹침 면제. **bounds 누락은 `require_bounds`일 때만 오류**(template-mode이거나 루트에 `data-pptx-page-role` 또는 구조 속성이 있을 때. `checker.py:4718-4725`), 그 밖에는 경고. `data-pptx-bounds`가 `<g>`가 아닌 요소에 있으면 오류. compact authored-preset 그룹은 bounds 누락 검사에서 면제. `data-pptx-morph-staging`은 별도 규칙(`checker.py:4640-4705`) | 코드 확인(상수 `checker.py:441-442`, `require_bounds` 조건 직접 읽음). 5% 판정과 면제 목록은 검토자 확인 |
| R-06 | 최상위 그룹을 `id` 없이 쓰거나, 페이지에 그룹 밖 낱개 요소가 있거나, 같은 최상위 그룹 id가 중복된다 | id 없는 최상위 그룹과 그룹 밖 낱개 요소는 **경고**(`svg_output` 안에서만). **중복 최상위 그룹 id는 오류**(`Duplicate top-level group id …; animation target ids must be unique`, `checker.py:5845-5851`). "거대 그룹 하나" 검사는 이 함수에 없다 | 코드 확인(`checker.py:5793-5890` `_check_animation_group_ids`. 중복 id는 메인이 직접 읽음, 나머지는 검토자 확인) |
| R-07 | `--canonical-authoring`이고 SVG가 컴팩트 형태가 아니다(루트에 공유 paint, 루트 `font-family` 누락, 상속 가능 선언의 중복 등) | 항상 경고(`Noncanonical compact authoring: …`)이고 오류가 아니다. 템플릿 모드도 경고. 소스는 안 고쳐진다 | 코드 확인 |
| R-08 | `--stage early` | 대상이 프로젝트면 `svg_output/`의 직계 `*.svg` 전체(숫자 파일명 순)를 파일마다 부분 로스터 규칙으로 검사. 없으면 `[ERROR]` exit 1. 부분 로스터에서는 슬라이드 점프 링크 상한·outline 로스터·outline 하이퍼링크 검사를 건너뛴다(최종 gate까지 미룸) | 코드 확인 |
| R-09 | `--stage first-page` / `--stage page --page X` | first-page는 첫 SVG 한 장만, page는 X 한 장만 검사. 둘 다 `partial_roster` | 코드 확인 |
| R-10 | `--stage final`(기본), round-trip 아님, target이 디렉터리 | 로스터가 불완전하면(structured 잠금에 선언된 슬라이드가 없음) early를 쓰라는 `[TIP]`을, 구조형 슬롯에 native 객체를 채우면 표준 export가 실패한다는 `[TIP]`을 출력한다. TIP은 요약보다 **앞에** 나온다(`print_summary` 앞, `cli.py:308-326`). target이 파일이면 TIP이 나오지 않는다 | 코드 확인(메인이 `cli.py:308-327` 직접 읽음) |
| R-11 | checker 실행 | 소스 SVG를 쓰거나 고치지 않는다("the checker never rewrites source SVG"). 정규화는 별도 도구(`compact_svg_styles.py --inplace`, `compact_svg_coordinates.py --inplace`)가 한다 | 추론(checker의 `svg_output` 쓰기 호출을 검색하지 않음. docstring·CLI help 근거) |
| R-12 | 옵션 조합 오류: `--stage`와 `--page` 불일치, `--template-mode`+`--quick-generate`, `--roundtrip`+금지 옵션, `--all`+(`--roundtrip`/`--quick-generate`/`--stage`≠final) | `[ERROR]` 출력 후 exit 1. 아무 보고서도 쓰지 않는다. 예외 하나: `--json-output`에 경로가 없는 오류는 사전 검사가 아니라 검사·요약·`--export` 텍스트 보고서 **뒤**에 난다(`cli.py:330-340`). 그래서 이 경우 `--export` 텍스트 보고서는 이미 쓰였을 수 있고 JSON만 안 쓴다 | 코드 확인(메인이 `cli.py:330-340` 직접 읽음) |
| R-13 | 정상 실행 끝 | 요약 출력 → (`--export`) 텍스트 보고서 → (`--json`/`--json-output`) JSON 보고서 → `summary.errors>0`이면 exit 1, 아니면 exit 0. 경고는 exit status에 영향이 없다. 오류가 있어도 JSON은 이미 쓰였다 | 코드 확인 |
| R-14 | `--json` 보고서 경로 | `--json-output`이 있으면 그 경로. 없으면 stage별 파일명(1.3 C)을 `<project>/validation/` 아래에 둔다. project 판정은 세 규칙이다(`_resolve_project_path`, `checker.py:8167-8180`): (a) target(또는 파일이면 부모)의 이름이 `svg_output` 등 SVG 작업 디렉터리 이름이면 `_project_root_for_svg_path`로 프로젝트 루트를 구한다. (b) 그 target에 `svg_output/`이나 `design_spec.md`가 있으면 그 target이 프로젝트다. (c) 그 밖에는 target의 부모다. 예: `svg_quality_checker.py projects/p/svg_output --json`은 `projects/p/validation/svg_quality_report.json`을 쓰므로 gate 보고서가 된다. `--all <base> --json`은 target 문자열이 `--all`이라 cwd에 쓸 가능성이 높다(코드 경로상 추정, 실행 안 함) | 코드 확인(메인이 `checker.py:8167-8182` 직접 읽음). `--all`은 추론 |
| R-15 | JSON 보고서 내용 | 1.3 D의 구조. blocking = 파일 오류 + 프로젝트 단위 오류, introduced = 경고, inherited/source-import = 정보 | 코드 확인 |
| R-16 | `source_fingerprint` 계산(checker) | 존재하는 결과 파일들을 이름순으로, `이름 \0 sha256 \n`을 이어 sha256. 검사 시 읽은 바이트의 sha256을 쓰므로 검사 후 수정된 파일은 fingerprint와 어긋난다. 읽기 실패 파일은 sha256 `null`+`error`, 집계에는 문자열 `unreadable`이 들어간다 | 코드 확인 |
| R-17 | exporter가 보고서를 읽는다 | 상태를 하나로 정한다. (1) 파일 없음 `not-provided` (2) 읽기·JSON 파싱 실패 `unreadable` (3) schema 불일치 `unsupported-schema` (4) `stage != final` `non-final` (5) `blocking.count`가 정수 아님 `unverified` (6) `blocking.count>0` `failed` (7) fingerprint 불일치 `stale` (8) fingerprint 없음·형식 불일치 `unverified` (9) 그 외 `passed`. 번호 순으로 먼저 걸린 것이 이긴다(예: blocking이 있으면서 fingerprint도 어긋나면 `failed`). 세부: fingerprint가 dict인데 `algorithm`이 `sha256`이 아니면 `unverified`가 아니라 불일치로 보아 `stale`이 된다. 보고서 JSON이 파싱되지만 dict가 아니면(`[]` 등) `quality.get`에서 `AttributeError`로 크래시한다(`unreadable`이 아님, 검토자 확인) | 코드 확인 |
| R-18 | exporter가 `release_quality_gate`를 적용하는 조건 | `(--quick-generate 이거나 --source가 없음/`output`) 이고 dangerous compatibility export가 아님`일 때만 적용한다. 적용되면 현재 SVG 목록(`discover_slide_svgs`, 직계 `*.svg` 숫자순)의 fingerprint를 같은 알고리즘으로 다시 계산해 R-17을 돌리고, `passed`가 아니면 stderr에 상태명을 넣은 오류와 `svg_quality_checker.py "<project>"[ --quick-generate] --canonical-authoring --stage final --json` 안내를 출력하고 exit 1 한다. 변환 파일은 쓰지 않는다. gate보다 먼저 `spec_lock.md` 요구(`cli.py:2490-2494`)와 빈 SVG 목록 오류(`cli.py:2745-2770`)가 걸릴 수 있다 | 코드 확인 |
| R-19 | `--source <다른 디렉터리>`(예 `-s final`)나 `--enable-dangerous-nonconforming-svg-export`로 내보낸다 | 품질 gate가 적용되지 않는다(R-18 조건 밖). `--roundtrip`은 `args.source`를 `authoring-svg-flat`로 강제하고(`cli.py:2418`) `--quick-generate`와 같이 못 쓰므로 gate가 켜지지 않는다. dangerous 쪽은 경고를 출력하고 receipt에 `dangerous_nonconforming_svg_export=enabled`를 남긴다 | 코드 확인 |
| R-20 | exporter가 `--canonical-authoring`·`--quick-generate`로 만든 보고서인지 확인하는가 | 확인하지 않는다. gate는 stage·blocking·fingerprint만 본다. 따라서 `--canonical-authoring` 없이 쓴 final 보고서, 또는 `--quick-generate` 없이 쓴 final 보고서도 `passed`가 될 수 있다. 워크플로 문서의 "생략하면 export가 거부하거나 canonical 검사를 건너뛴다"는 후자 쪽(검사 생략)만 맞다 | 코드 확인(`pptx_package/cli.py`의 `canonical` 검색 결과, 2.1) |
| R-21 | early 게이트 운영(워크플로) | P01~P05 → early(계획 로스터 6장 이하면 생략) → 나머지 → final. 모든 checker 호출은 gate 지점(검사 대상 페이지가 전부 존재)이나 한 번의 통합 수리 직후여야 한다. early 결과에서 같은 범주 이슈가 둘 이상이면 방법 수준 편향이므로 P06 전에 규칙을 바로잡는다(`text_measure.py calibrate`) | 코드 확인(문서 문장), 준수는 agent 규율이라 checker가 강제하지 않음(추론) |
| R-22 | verify-charts 트리거: 값이 SVG geometry를 정하는 데이터 차트가 하나 이상 있고, SVG 작성이 끝났으며 `finalize_svg.py`/`svg_to_pptx.py` 전 | 입력: 차트 객체 목록(Default는 `design_spec.md §IX`, Quick는 활성 컨텍스트와 `chart-plot-area` 마커), 각 SVG, 축 눈금 범위. 처리: `svg_position_calculator.py`로 좌표 계산(문서가 정한 처리 모드는 `direct-calc`·`decomposable-calc`·`partial-calc`·`formula-verify`·`manual-verify` 5가지) 후 SVG와 비교하고 스케일이 맞을 때만 손으로 수정. 출력: 객체마다 `verify-charts: …` 한 줄 영수증(개수 = 목록 길이), 수정된 SVG. 이후 checker final을 다시 돈다. 목록이 비면 `verify-charts: active profile declares no data-driven chart objects, nothing to verify` 한 줄을 내고 종료 | 코드 확인(문서). 계산기 코드는 미열람 |
| R-23 | visual-review 트리거: 사용자가 명시 요청했고 모든 페이지가 있으며 checker가 통과한 뒤, finalize/export 전 | 입력: `<project_path>`, `visual_review.py`가 `.preview/<page>.png`를 만든다(playwright chromium, live-preview 서버 필요). 하위 agent들이 rubric으로 위치·간격만 고치고 원본은 `.review/backup/`에 둔다. 출력: `| page | role | status | … |` 표, 필요 시 `.review/brand_review.json`. 자동 호출하지 않는다. 브랜드·구조 결정은 건드리지 않고 `needs_human`으로 올린다 | 코드 확인(문서). `visual_review.py` 코드는 미열람 |
| R-24 | 실패 복구(failure-recovery §1) | checker 오류: 한 번의 필터 없는 실행으로 전체 issue를 보고 한꺼번에 고친 뒤 한 번 재실행. 경고: 수정 의무 없음. `svg_to_pptx.py` 실패: 통과 final 보고서가 없으면 final checker로 blocking 전체를 구해 고치고 `passed`가 된 뒤 다시 내보낸다. 변환 오류면 그 변환 문제를 고치고 Step 7.3을 다시 돈다. 원칙: 실패한 필수 산출물은 다음 gate를 막고, 편의 표면의 실패는 막지 않으며, 파생물이 낡으면 원천에서 재생성한다 | 코드 확인(문서) |
| R-25 | checker 대상 디렉터리가 없거나 SVG가 하나도 없다(`--stage final --json`) | `[ERROR]`가 `summary.errors`만 올리고 `categories.blocking`에는 들어가지 않는다. `--json`이면 `blocking.count=0`, `file_count=0` 보고서가 쓰이고 exit 1. 이 보고서가 exporter를 통과하지는 않는다(exporter가 SVG 0개 오류로 gate 이전에 먼저 거부, R-18) | 코드 확인(메인이 `checker.py:7282-7290` 직접 읽음, 7445-7451·exporter 쪽은 검토자 확인) |
| R-26 | exporter가 gate가 꺼진 경로(`-s final`·dangerous·roundtrip)로 내보낸다 | 거부하지는 않지만 receipt 작성 시 `_quality_report_context`·`_quality_gate_status`를 항상 돌려 `quality_gate`·`quality`(summary·categories)·`quality_introduced_warnings`를 기록한다. `quality_gate=='failed'`이면 receipt의 `report_status`가 `failed`다(`pptx_package/cli.py:1447-1470`) | 코드 확인(메인이 직접 읽음) |
| R-27 | `visual-review`가 `fixed`로 SVG를 제자리 수정한 뒤 바로 내보낸다 | `visual-review.md`는 수정 뒤 final checker를 다시 돌리라고 적지 않는다(`prereq_failed`일 때만). SVG 바이트가 바뀌었으므로 직전 final 보고서의 fingerprint가 어긋나 exporter가 `stale`로 거부하고 재실행 명령을 안내한다 | 추론(문서가 재검사를 안 적었다는 것은 코드 확인. `stale` 결과는 R-16~R-18에서 도출) |
| R-28 | non-quick checker가 `spec_lock.md`를 가진 프로젝트를 검사한다 | `spec_lock.md`에 `canvas` 절이 있는데 `viewBox`가 없으면 오류(`spec_lock.md canvas section must declare viewBox`, `checker.py:2646-2658`). 있으면 그 viewBox를 canvas 계약에 쓴다. Quick은 첫 SVG가 canvas를 정한다 | 코드 확인(메인이 직접 읽음) |

- 불변식: final 보고서가 `passed`이려면 stage=`final`, `blocking.count=0`, 그리고 보고서 작성 이후 `svg_output/`의 직계 `*.svg` 파일 이름·바이트가 하나도 바뀌지 않았어야 한다(R-16·R-17·R-18). 같은 SVG 바이트면 같은 fingerprint다. 단 exit status와 `blocking.count`는 같지 않다: 입력 오류(디렉터리 없음·SVG 0개)는 exit 1이면서 `blocking.count=0`일 수 있다(R-25).
- 미결정: 없음

- 확인 한계: checker를 실행해 보지 않았다(의존성·무실행 규칙). 보고서 JSON 구조·종료 코드는 코드 읽기로만 확인했고 실제 출력 예는 확보하지 못했다. 개별 검사 규칙(약 10,300줄)은 열지 않았다.

### 1.5 필수 코드 참조 [필수]
라이선스는 MIT(overview 1절)이므로 인용 가능. 개별 규칙은 코드가 문서보다 정확하므로 아래 위치에서 읽는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `skills/ppt-master/scripts/svg_quality/cli.py:168-356` `main` | 옵션 파싱·조합 검증(184-256, 258-266), 단계 분기(278-306), TIP(308-324), 요약(326)→export(330-337)→JSON(339~)→exit(~356). TIP이 요약보다 앞 | R-08~R-13 |
| C-02 | `skills/ppt-master/scripts/svg_quality/cli.py:27-113` `_first_page_target`·`_early_targets`·`_page_target`·`_default_json_report_path` | 단계별 대상 풀이, `--page`가 `svg_output/` 밖이면 거부, 보고서 파일명 표(99-104) | R-08, R-09, R-14 |
| C-03 | `skills/ppt-master/scripts/svg_quality/checker.py:10138-10207, 10209-10282, 10285-10318` `_provenance_categories`·`export_json_report`·`_quality_source_fingerprint` | 보고서 구조와 fingerprint 알고리즘. 그대로 옮겨도 되는 짧은 자기완결 코드 | R-15, R-16 |
| C-04 | `skills/ppt-master/scripts/svg_quality/svg_contracts.py:197-1131` (`check_forbidden_elements` 197, `check_paint_compatibility` 292, `check_authoring_property_contract` 499, `check_text_property_contract` 559, `check_marker_contract` 631, `check_clip_path_contract` 645, `check_mask_contract` 659, `check_geometry_length_values` 730, `check_stroke_style_values` 777, `check_transform_values` 998, `check_font_size_values` 1060) | 항목별 문법 검사 함수. 규칙 본문은 여기서 읽는다 | R-01, R-03, R-04 |
| C-05 | `skills/ppt-master/scripts/svg_quality/checker.py:1270-1400` `check_file` | 파일 하나 검사 순서(sha256 기록, XML 파싱, canonical 검사, 계약 검사 호출) | R-02, R-16 |
| C-06 | `skills/ppt-master/scripts/svg_quality/checker.py:441-442, 4257-4410, 4780-4805` | bounds 상수, 모듈 텍스트 초과 판정, root 그룹 겹침 판정 | R-05 |
| C-07 | `skills/ppt-master/scripts/svg_authoring_contract.py:284-401` `canonical_authoring_errors` + `checker.py:2541-2588` `_check_canonical_authoring` | 컴팩트 작성 위반 목록 생성과 경고화 | R-07 |
| C-08 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:1251-1268` `_svg_source_fingerprint` | exporter 쪽 fingerprint(C-03과 같은 알고리즘, 입력만 `native_files`) | R-16, R-18 |
| C-09 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:1270-1352` `_quality_report_context`·`_quality_gate_status` | exporter가 읽는 필드와 상태 9종의 판정 순서. C4의 핵심 | R-17 |
| C-10 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3160-3185` | gate 적용 조건과 실패 메시지·안내 명령 | R-18, R-19 |
| C-11 | `skills/ppt-master/scripts/slide_roster.py:45-47` `discover_slide_svgs` | 검사·내보내기가 공유하는 로스터 정의(직계 `*.svg` 숫자순) | R-08, R-16 |
| C-12 | `skills/ppt-master/references/shared-standards-core.md`(전체 259줄), `scripts/docs/svg-contract.md`(809줄), `references/semantic-svg.md`(75줄), `references/native-shape-authoring.md`(182줄), `references/svg-image-embedding.md`(53줄) | C3의 원문. 1.3 A 표에서 부족한 문법 전체(effects·gradient·freeform·transform 문법은 `svg-effects.md`와 svg-contract Part II) | R-01~R-07 |
| C-13 | `skills/ppt-master/scripts/text_measure.py` (`measure`/`wrap`/`box`/`calibrate` 서브커맨드, 855-905) | agent가 텍스트 폭을 미리 재는 CLI. docstring은 checker의 폭 추정기와 같다고 한다 | R-05, R-21 |

### 1.6 수락 사례 [필수]
출처: 모두 구현 읽기에서 도출(실행·원본 테스트 미열람).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-13, R-14, R-17 | `projects/p/svg_output/`의 SVG 3장이 오류 없이 통과, `--stage final --json` | `projects/p/validation/svg_quality_report.json` 생성(`stage:"final"`, `blocking.count:0`), exit 0. 이후 `svg_to_pptx.py projects/p`는 gate를 통과 |
| T-02 | R-13 | 한 페이지에 `&nbsp;` 포함, `--stage final --json` | 그 파일에 `Invalid XML` 오류, 보고서는 쓰이고 `blocking.count>=1`, exit 1. 이후 export는 `failed`로 거부 |
| T-03 | R-18 | T-01 직후 `svg_output/slide_02.svg`를 한 글자 수정하고 `svg_to_pptx.py p` | 상태 `stale`, 오류 `requires a passing final SVG quality report … found stale`와 재실행 명령 출력, exit 1, PPTX 없음 |
| T-04 | R-17 | 보고서 없이 export | `not-provided`로 거부(경로 `validation/svg_quality_report.json` 포함 컨텍스트) |
| T-05 | R-17, R-20 | `--stage early --json`만 돌리고 export | 보고서 파일명이 `…_early_report.json`이라 final 경로엔 파일이 없어 `not-provided`. 같은 파일을 final 경로에 복사하면 `non-final` |
| T-06 | R-12 | `--stage page`만 주고 `--page` 없음 | `[ERROR] --stage page requires --page …` exit 1, 보고서 없음 |
| T-07 | R-08 | 프로젝트에 SVG가 없고 `--stage early` | `[ERROR] --stage early found no authored SVG pages` exit 1 |
| T-08 | R-07 | 루트에 `fill`이 있고 `--canonical-authoring` 없이/있이 돌림 | 없이: 이 규칙 검사 없음. 있이: 경고 `Noncanonical compact authoring`(오류 아님), exit 0 |
| T-09 | R-19 | 통과 보고서 없이 `svg_to_pptx.py p -s final` | gate 미적용(조건 밖). 이후 동작은 변환 스펙 소관 |
| T-10 | R-09 | `--stage page --page ../outside.svg` | `--page must resolve to a path under svg_output/` 오류, exit 1 |
| T-11 | R-25 | 존재하지 않는 디렉터리에 `--stage final --json` | `[ERROR] Directory does not exist`, `blocking.count=0`·`file_count=0` JSON이 쓰이고 exit 1. 이 보고서로는 exporter gate를 통과하지 못한다 |
| T-12 | R-04 | `svg_to_pptx` 길이 검증기를 import하지 못하는 환경에서 `width="50%"` 포함 SVG를 검사 | 오류가 아니라 `Unable to import svg_to_pptx geometry length validators` 경고만 나온다. exporter는 같은 SVG를 거부한다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repos/ppt-master@3af3e8e `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | `scripts/docs/svg-contract.md:1-14`, `shared-standards-core.md:31`, C-04 | 문서가 "같은 검증기"라고 쓴다. checker 쪽 호출은 `checker.py:1361-1368`, `svg_contracts.py:730-745`. exporter 쪽은 `svg_to_pptx/drawingml/converter.py:2212`(`project_geometry_length_errors(root)`)와 2153-2226의 `_require_project_*` 계열에서 확인(메인이 직접 읽음). 단 geometry 길이 검증기 import가 checker에서 실패하면 checker만 경고로 건너뛰고 exporter는 여전히 검증한다(R-04) |
| R-02 | `checker.py:2591-2612` `_parse_xml_root` | 오류 문구와 early return을 직접 읽음 |
| R-03 | C-04 `check_forbidden_elements`(197), `check_mask_contract`(659) | 함수 위치·호출만 확인. 금지 목록은 core §1.0 문서 기준 |
| R-04 | `svg_contracts.py:730-775`, `drawingml/utils.py:444-462`, `shared-standards-core.md:136`, `svg-contract.md:341-395`, C-04 | 함수 본문과 fail-open 경로는 직접 읽음. 숫자 철자·음수 판정은 검토자 확인 |
| R-05 | `checker.py:441-442`, `checker.py:4617-4815`(`require_bounds` 4718-4725), `svg-contract.md:409-458` | 상수와 `require_bounds` 조건은 직접 읽음. 5% 판정·면제는 검토자 확인 |
| R-06 | `checker.py:5793-5890`, `shared-standards-core.md:190-215` | 중복 id 오류는 직접 읽음. 경고 분류는 검토자 확인(U-01 해소) |
| R-07 | `checker.py:2541-2588`, `svg_authoring_contract.py:284-401`, `cli.py:154-155` | `result['warnings'].extend`로만 추가됨을 직접 읽음 |
| R-08 | `cli.py:37-43, 282-294`, `checker.py:7549-7560, 3155` | `partial_roster`가 outline 로스터·하이퍼링크 상한 검사를 끄는 것을 코드로 확인. 그 밖에 partial_roster가 끄는 검사가 있는지는 `grep -n "partial_roster" checker.py`로 1229·3155·7549·7554 네 곳만 찾았고(파일 전체), 다른 파일의 `partial_roster` 참조는 검색하지 않았다 |
| R-09 | `cli.py:27-35, 46-86, 296-306` | 직접 읽음 |
| R-10 | `cli.py:308-327`, `checker.py:7755-7775` | `_has_incomplete_page_roster`는 structured 잠금 경로에서만 `True`가 된다(`grep -n "_has_incomplete_page_roster" scripts/svg_quality/*.py`, 7769만). TIP 출력 위치와 `Path(target).is_dir()` 조건은 직접 읽음. flat·Quick에서는 TIP이 안 나올 수 있다 |
| R-11 | `checker.py:2541-2560`(docstring), `cli.py:154-155` | `svg_output` 쓰기 호출은 검색하지 않았다. 추론 |
| R-12 | `cli.py:175-266`, `cli.py:330-340` | 조건문과 `--json-output` 경로 누락 오류 위치를 직접 읽음 |
| R-13 | `cli.py:326-356`, `checker.py:9608-9650` `print_summary` | `export_json_report` 호출 뒤에 `sys.exit(1)`이므로 오류가 있어도 JSON이 쓰임 |
| R-14 | `cli.py:89-113`, `336-351`, `checker.py:8167-8182` | `_resolve_project_path` 세 규칙을 직접 읽음. `--all` 동작은 추론 |
| R-15 | C-03 | 직접 읽음 |
| R-16 | C-03 `_quality_source_fingerprint`, `checker.py:1311` | 직접 읽음 |
| R-17 | C-09 | 직접 읽음. 조건 순서가 판정 우선순위다 |
| R-18 | C-10, `discovery.py:16-58`, `pptx_package/cli.py:2737-2742, 2354` | 직접 읽음. `-s output`·`-s` 미지정은 `native_source = args.source or 'output'`(2737)로 같다. `-s svg_output`은 `release_quality_gate`의 `args.source in {None,'output'}`에 안 걸려 gate가 꺼지는 것으로 읽힌다(`dir_map`은 이름 `svg_output`을 그대로 디렉터리로 쓰므로 파일은 찾는다). 실행 확인은 하지 않았다 |
| R-19 | `cli.py:2354-2400, 3160-3163`, `cli.py:1447-1560` | 직접 읽음 |
| R-20 | `grep -n "canonical" scripts/svg_to_pptx/pptx_package/cli.py`(파일 1개)에서 안내 문자열(3183) 외 게이트 판정 사용처 없음. `quick-generate.md`의 "omitting `--canonical-authoring` or `--json` makes the export refuse or skip the canonical check"는 `--json` 생략 쪽만 구현과 맞다. 다른 `svg_to_pptx/` 하위 모듈에서 보고서 내용을 더 읽는지는 `grep -rn svg_quality_report scripts/svg_to_pptx` 등으로 확인하지 않았다 | **문서와 구현이 다르다.** 구현을 사실로 R-20에 썼다. 보고서에 `--canonical-authoring` 사용 여부 필드가 없는 것도 근거(1.3 D에 없음) |
| R-21 | `generate-pptx.md:261-308`, `quick-generate.md:197-209` | 문서 읽음 |
| R-22 | `workflows/stages/verify-charts.md:1-87` | 문서 읽음 |
| R-23 | `workflows/stages/visual-review.md:1-78` | 문서 읽음 |
| R-24 | `workflows/governance/failure-recovery.md:7-9, 36-37, 42, 47-61` | 문서 읽음 |
| R-25 | `checker.py:7282-7290`, `7445-7451`, `pptx_package/cli.py:2745-2770` | 디렉터리 없음 분기는 직접 읽음. SVG 0개와 exporter 거부는 검토자 확인 |
| R-26 | `pptx_package/cli.py:1447-1470` | 직접 읽음 |
| R-27 | `workflows/stages/visual-review.md:11, 57, 63` | 문서에서 "SVG updated in place"와 재검사 지시 없음을 직접 읽음. `stale`은 R-16~R-18에서 도출한 추론 |
| R-28 | `checker.py:2646-2658` | 직접 읽음 |
| T-01~T-10 | R-ID 근거 위치에서 도출 | 실행하지 않음. 기대값은 코드 경로 추적 결과이며 stderr 문구는 코드(3171-3178)에서 가져옴 |

- 문서와 구현의 차이: (1) R-20. (2) 워크플로 문서는 "Without `--json` the export is refused"라고 하는데 이는 `not-provided`로 맞다. (3) `shared-standards-core.md`가 쓰는 "exporter preflight와 checker가 한 검증기를 공유"는 U-02로 남김.
- 부재·전칭 주장의 검색: "checker가 `--canonical-authoring` 여부를 보고서에 기록하지 않는다" = `export_json_report`(10209-10275)의 payload 키 목록을 전부 읽었고 해당 키가 없음. 다른 곳에서 보고서에 덧붙이는 경로는 검색하지 않았다.

### 2.2 코드 읽는 순서 [선택]
1. `cli.py` `main`(C-01)으로 옵션·단계를 잡는다 → `_default_json_report_path`(C-02)로 파일명.
2. `checker.py` `check_directory`(7270) → `check_file`(1270)으로 파일 하나의 흐름을 본 뒤 `svg_contracts.py`(C-04)로 규칙을 확인한다. 10,000줄 중 규칙은 `_check_*` 40여 개 메서드로 나뉘어 있다.
3. 보고서는 C-03, exporter 쪽은 C-09 → C-10. 이 세 군데만 알면 C4 gate를 재구현할 수 있다.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙 없음. `svg-to-pptx-cli` 스펙은 이 문서의 C4(R-16~R-20, C-08~C-10)를 참조한다.

### 2.4 검토 기록 [필수, ready 스펙]
- 방식: 메인 점검 + 독립 검토(검토자 서브에이전트, 읽기 전용). 다른 스펙(`svg-to-pptx-cli`)이 `depends`로 의존하므로 독립 검토를 돌렸다.
- 대조한 R-ID: 메인 R-17(판정 순서), R-18(gate 적용 조건), R-20(`canonical` grep) 일치. 메인이 `--format` 오류, TIP 위치·조건, 디렉터리 없음 분기, 중복 id 오류, roundtrip 소스 강제, `_resolve_project_path`, `require_bounds`, 길이 검증기 fail-open, receipt의 gate 상태 기록, `spec_lock` canvas 오류를 직접 열어 확인. 검토자가 R-02, R-04~R-13, R-15~R-24 중 고위험 14개 전부와 표본을 대조. 불일치 R-04·R-05·R-06·R-10·R-12·R-14·R-17·R-18·R-19·R-22와 누락 4건(R-25~R-28)은 반영함. 미결정 U-01~U-03은 코드 확인으로 해소.
- 대조하지 않은 R-ID: R-03(함수 존재만 확인), R-21의 문서 일치 외 동작, 그 외 R-ID의 세부 줄. R-04의 숫자 철자·음수 판정, R-05의 5% 판정·면제 목록, R-25의 SVG 0개 분기는 검토자 확인만 있고 메인이 재확인하지 않았다.
- 재구현: 미수행

## 적용 메모 [선택]

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-20 | (제안, 미결정) 보고서에 `canonical_authoring`·`quick_generate` 사용 여부를 넣고 gate가 확인하는 것을 고려 | 문서가 약속한 "canonical 검사 증명"을 구현은 강제하지 않는다 | 이 변경을 하면 T-08과 gate 사례가 바뀐다. 원본 동작은 아니므로 지금은 적용하지 않음 |
