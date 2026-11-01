---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/bin/archify.mjs
  - archify/renderers/shared/utils.mjs
  - archify/renderers/shared/cli.mjs
  - archify/renderers/shared/i18n.mjs
  - archify/renderers/shared/legend.mjs
  - archify/renderers/shared/diagnostics.mjs
  - archify/renderers/shared/geometry.mjs
  - archify/renderers/shared/automatic-labels.mjs
  - archify/renderers/shared/node-card-style.mjs
  - archify/renderers/shared/layout-report.mjs
  - archify/renderers/shared/software-notices.mjs
  - archify/renderers/shared/text-fit.mjs
  - archify/renderers/shared/desktop-readability.mjs
  - archify/renderers/shared/route-quality.mjs
  - archify/renderers/shared/atomic-output.mjs
  - archify/renderers/shared/path-semantics.mjs
  - archify/renderers/architecture/render-architecture.mjs
  - archify/renderers/architecture/routing.mjs
  - archify/renderers/architecture/grid.mjs
  - archify/renderers/workflow/render-workflow.mjs
  - archify/renderers/workflow/workflow-compiler.mjs
  - archify/renderers/sequence/render-sequence.mjs
  - archify/renderers/dataflow/render-dataflow.mjs
  - archify/renderers/dataflow/dataflow-compiler.mjs
  - archify/renderers/lifecycle/render-lifecycle.mjs
  - archify/renderers/erd/render-erd.mjs
  - archify/renderers/erd/grid.mjs
  - archify/renderers/class/render-class.mjs
  - archify/renderers/tree/render-tree.mjs
  - archify/renderers/timeline/render-timeline.mjs
  - archify/renderers/waterfall/render-waterfall.mjs
  - archify/assets/template.html
  - archify/locales/en.json
  - archify/locales/manifest.json
  - archify/schemas/architecture.schema.json
  - archify/schemas/common.schema.json
depends: [input-validation.md]
status: ready        # 이 스펙 자체의 미결정 없음(이전 M-01~M-05는 하위 스펙으로 이관·해소, M-06은 확인 한계로 이동, 하단 "미결정" 절). 선행 input-validation.md는 ready. 하위 스펙(rendering-architecture-routing, rendering-workflow, rendering-other-types, rendering-contracts)의 draft 여부는 이 status에 영향을 주지 않는다(이 문서는 공통 계층과 architecture 배치·경계·진단만 소유)
reimplementation: 미실행
---

# 렌더링 (검증된 JSON → 타입별 SVG → template.html 슬롯 → HTML 한 파일)

> 검증을 통과한 diagram 객체 하나와 `assets/template.html`을 받아, 타입별 렌더러가 SVG를 만들고 `applyTemplate`이 슬롯 8종을 채워 원본 JSON 없이 HTML 한 파일을 쓰는 기능이다. 이 문서는 공통 계층과 architecture의 배치·경계·viewBox·진단을 소유하고, architecture 자동 라우팅·workflow·나머지 8개 타입·SVG 훅 계약·출력 쓰기 내부는 아래 하위 스펙 링크 절이 가리키는 문서로 나뉜다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 호출자가 `archify render <type> <input.json> [output.html]`을 실행하거나(R-01), `deliver`·`finalize`가 같은 렌더러를 staging 경로로 자식 프로세스로 실행한다. 렌더러는 `renderers/<type>/render-<type>.mjs <input> [output]`이고 품질·근거·진단 형식은 환경 변수로 받는다(R-02, R-03).
2. 렌더러는 `loadDiagram`(또는 비동기 `loadDiagramWithBrandMarks`)으로 `{diagram, template, outPath, sourceEvidence}`를 받는다. 이 경계의 앞(파싱·`meta.output` 형식·스키마·로케일 경고·관계 ID 계약·엔지니어링 프로파일·근거 검증)은 [input-validation.md](input-validation.md) 소관, 출력 경로 해석은 [delivery.md](delivery.md)가 소유하며 delivery.md R-12와 같은 호출 규약(`node <renderer> <input> <output>`)을 쓴다. 이 스펙은 그 결과를 "검증을 통과한 diagram 객체"로만 받는다.
3. 타입별 컴파일러가 노드 크기를 재고 → 배치하고 → (연결이 있으면) 라우팅하고 → 라벨을 놓고 → viewBox를 정한 뒤 → 타입별 레이아웃 진단(렌더 진단)을 검사해 SVG 문자열 하나를 만든다(R-17, R-20~R-37, R-40~R-48).
4. 렌더 진단이 하나라도 오류면 파일을 쓰지 않고 진단을 던진다. stderr에 진단, 종료 코드 1(R-04). 기존 출력 파일은 건드리지 않는다.
5. `writeDiagram`이 `applyTemplate`로 슬롯 8종(`<html>`, `<title>`, `<h1>`, 부제 줄, i18n 데이터, SVG, 카드, 근거 데이터)을 채운 HTML 문자열을 만든다(R-06~R-13).
6. 같은 폴더의 임시 파일에 쓰고, 기존 파일이 있으면 하드링크 백업 → 공개 이름 격리 제거 순서로 비운 뒤 후보를 공개 이름에 `link`한다(rename 덮어쓰기가 아니다). 성공하면 stdout에 절대 경로 한 줄을 찍고 종료 0이다(R-14).
7. 원본 JSON은 HTML 어디에도 없다(R-12). 이후 staging 교체·provenance는 [delivery.md](delivery.md), HTML 안의 뷰어 동작은 viewer 행(feature map 11, 스펙 없음) 소관이다.

**하위 스펙**: [rendering-architecture-routing](rendering-architecture-routing.md)(architecture 자동 라우팅·라벨 위치), [rendering-workflow](rendering-workflow.md)(workflow 컴파일러), [rendering-other-types](rendering-other-types.md)(dataflow·lifecycle·erd·class·sequence·tree·timeline·waterfall), [rendering-contracts](rendering-contracts.md)(SVG `data-*` 훅의 쓰는 쪽·읽는 쪽, 품질 프로파일 비대칭, 출력 쓰기 두 경로). 이 문서의 R-ID와 같은 내용은 각 문서에 다시 쓰지 않고 링크로 넘긴다. 하위 스펙은 이 문서에 의존하고(`depends: [rendering.md]`) 이 문서는 하위 스펙에 의존하지 않는다.

### 1.2 범위·통합 지점 [필수]
- 제공: (a) 공통 계층(슬롯 치환·이스케이프, 카드, i18n 주입, 범례 데이터, SVG 루트 속성, 쓰기 규칙, 렌더러 CLI 계약, 진단 전달). (b) architecture의 배치·경계·라우팅·라벨·viewBox·레이아웃 진단. (c) 나머지 9개 타입의 타입별 요약 표(1.3 H)와 하위 스펙으로 가는 링크.
- 제외: 입력 로드·검증 단계와 진단 객체의 필드 정의(input-validation.md), staging·provenance·잠금·commit pair·출력 경로 우선순위(delivery.md), HTML 안 뷰어 JS·CSS 동작(viewer.md), 산출 후 `check`·`browser-check`(verification-gates 행), explainer 렌더러(`renderers/explainer`, 별도 행). architecture 자동 라우팅 상세·workflow 컴파일러·8개 타입의 알고리즘은 하위 스펙 소관. 타입별 SVG 내부의 시각 품질(색·간격 취향)은 확인하지 못했다(확인 한계).
- 외부 의존·선행 계약: (1) 호출자가 렌더러를 부르고 종료 코드·stdout·stderr를 읽는다. (2) `loadDiagram`이 검증된 diagram, 템플릿 문자열(`</head>` 앞에 소프트웨어 고지 script 삽입, C-38), `outPath`, `sourceEvidence`(없으면 null)를 준다. (3) 번들 데이터 `archify/assets/template.html`, `archify/locales/*.json`, `archify/NOTICE` 등 고지 파일이 스킬 설치 폴더에 있어야 한다.
- 소유 상태·부작용: 프로세스 안의 진단 기록 목록(`recorded`), 문서별 로케일 카탈로그, 같은 폴더의 임시 파일 `.archify-render-<pid>-<time36>-<seq>.tmp`(성공·실패 모두 정리). 만드는 외부 상태는 출력 HTML 한 파일뿐이다. `--layout-json`에서는 HTML을 쓰지 않는다.

### 1.3 인터페이스와 데이터 의미 [필수]

**A. 렌더러 CLI 계약 (공통)**

| 항목 | 값 | 의미·제약 |
|---|---|---|
| 공개 진입 | `archify render <type> <input.json> [output.html] [--quality standard\|showcase] [--repo-root path]` | 위치 인자 3개까지. 이 둘 말고 `--`로 시작하는 인자는 `Unknown render option` 오류. `<type>`이 10종(+explainer)이 아니면 `cli/unknown-diagram-type`. |
| 렌더러 직접 실행 | `node renderers/<type>/render-<type>.mjs [input.json] [output.html]` | `argv[2]` 없으면 `<스킬>/examples/<타입별 기본 예제>`(architecture는 `web-app.architecture.json`), `argv[3]` 없으면 `meta.output`, 그것도 없으면 `<type>.html`. 출력 경로 우선순위의 상세는 delivery 소관. |
| 환경 변수 | `ARCHIFY_QUALITY_PROFILE`(`--quality`), `ARCHIFY_REPO_ROOT`(`--repo-root`), `ARCHIFY_DIAGNOSTIC_FORMAT=json` | `render`는 앞 둘만 전달한다. JSON 형식은 `deliver`가 전달한다([delivery.md](delivery.md) R-12. `rendererEnv`는 3번째 인자를 받지만 `commandRender`는 넘기지 않는다). |
| 성공 | stdout에 `outPath`(절대 경로) 한 줄, 종료 0 | 경고(로케일 폴백 등)는 stderr에 `archify: <message>`로 나오고 종료 코드에 영향 없음. |
| 진단 실패(기본) | stderr: 첫 줄 `Error.message`, 이어서 진단마다 `[code] message Fix: a; b.`, 종료 1 | 분류된 진단(`archifyDiagnostics`가 있는 Error)만. 그 외 예외는 Node 기본 처리(스택, 비정상 종료). |
| 진단 실패(JSON 모드) | stderr에 한 줄 `{"schemaVersion":1,"ok":false,"source":"renderer","error":…,"diagnostics":[…]}`, 종료 1 | 큰 payload도 끝까지 쓴다(EAGAIN 재시도). 분류 안 된 예외는 `internal/unclassified` 진단 하나. |
| `--layout-json` | 직접 호출에서 `argv`에 있으면 HTML을 쓰지 않고 stdout에 레이아웃 JSON | architecture, workflow, erd, class, tree, timeline, waterfall 렌더러가 지원한다. 공개 `validate --layout-json`은 architecture·workflow만 허용(그 외 타입은 인자 오류). 실패하면 stdout JSON에 진단이 합쳐지고 종료 1. |
| 브랜드 마크 | architecture, workflow, sequence, dataflow, lifecycle은 `loadDiagramWithBrandMarks`(URL 캡처 비동기 단계 포함), erd·class·tree·timeline·waterfall은 동기 `loadDiagram` | 브랜드 규칙은 이 스펙에서 제외(`brand/*` 진단은 렌더 입력 단계). 렌더러는 `brand`가 있는 노드에 마크와 `data-node-brand*` 속성을 낸다. |

**B. `applyTemplate(template, {title, subtitle, svg, cards, locale, visualPreset='classic', sourceEvidence=null})` 슬롯 목록**

치환은 아래 순서로 한 문자열에 적용한다. 모든 치환은 함수 replacer라서 값 안의 `$&`·`$'`·`` $` ``·`$$`가 해석되지 않는다.

| # | 템플릿의 찾는 문자열(정확히 일치해야 함) | 채워지는 것 | 이스케이프 |
|---|---|---|---|
| 0 | `{{i18n:<key>}}`(템플릿 전체, 단일 키 규칙 `[a-zA-Z0-9_.-]+`) | 로케일 카탈로그의 해당 문장 | HTML 이스케이프. 키가 카탈로그에 없으면 `Missing Archify i18n message` Error(처음 치환). |
| 1 | `    <!-- ARCHIFY:I18N_DATA -->` | `    <script id="archify-i18n-data" type="application/json">{"locale":<해석된 로케일>,"messages":{<viewer.* 키만>}}</script>` | JSON 안 `<` `>` `&`를 `<` `>` `&`로 |
| 2 | `<html lang="en" data-theme="dark" data-preset="[VISUAL PRESET]">` | `<html lang="<해석된 로케일>" data-theme="dark" data-preset="<visualPreset>">` | `esc` |
| 3 | `<title>[PROJECT NAME] Architecture Diagram</title>` | `<title><page.title 문장, {title}=meta.title></title>` (영어 `{title} Diagram`) | `esc` |
| 4 | `<h1>[PROJECT NAME] Architecture</h1>` | `<h1><meta.title></h1>` | `esc` |
| 5 | `^[ \t]*<p class="subtitle">[Subtitle description]</p>[ \t]*(\r?\n)?` (여러 줄 모드) | `subtitle`이 비지 않은 문자열이면 같은 들여쓰기·줄바꿈의 `<p class="subtitle"><esc(subtitle)></p>`, 아니면 줄 전체(들여쓰기·줄바꿈 포함)를 삭제 | `esc` |
| 6 | `      <!-- ARCHIFY:SVG_SLOT_START -->` ~ `      <!-- ARCHIFY:SVG_SLOT_END -->`(공백 6칸, 사이 임의) | `svg` 문자열이 **센티널 주석을 포함해** 블록 전체를 대체 | 호출자 책임(렌더러가 만든 SVG) |
| 7 | `    <!-- ARCHIFY:CARDS_SLOT_START -->` ~ `    <!-- ARCHIFY:CARDS_SLOT_END -->`(공백 4칸) | `cards`(이미 `renderCards`로 만든 HTML)가 블록 전체를 대체 | 카드 항목 `esc` |
| 8 | `    <!-- ARCHIFY:SOURCE_EVIDENCE_DATA -->` | `sourceEvidence`가 있으면 `    <script id="archify-source-evidence-data" type="application/json">…</script>`, 없으면 빈 문자열 | 1과 같은 JSON 이스케이프 |

- 사전 검사(`Error`, 누락 시 `applyTemplate: template missing …`): 6·7 센티널, 5의 부제 줄, 2~4와 1의 문자열이 모두 있어야 한다. 8은 `sourceEvidence`가 있을 때만 필수(없는데 증거가 있으면 `repository evidence requires placeholder`).
- 로케일은 `resolveLocale(locale)`로 한 번 해석해 `lang`·i18n 데이터·`<title>` 문장에 같이 쓴다. `meta.locale`이 번들(`en`·`zh-CN`·`zh-TW`·`es`·`ko`·`ar`, 대소문자 무시)이 아니고 사용 가능한 `meta.translations`도 없으면 영어로 폴백하고 `lang="en"`이다. 번들이 아니어도 사용 가능한 `translations`가 있으면 저자 지정 태그를 그대로 쓴다.
- 템플릿에는 고정 요소가 있다(`<meta name="generator" content="archify 3.2.0">` 등). 렌더러는 이를 바꾸지 않는다.

**C. `writeDiagram({outPath, template, diagramType, meta, svg, cards, sourceEvidence=null})`**

| 입력 | 의미 |
|---|---|
| `diagramType` | `architecture`·`workflow`·`sequence`·`dataflow`·`lifecycle`·`erd`·`tree`·`class`·`timeline`·`waterfall` 중 하나. 아니면 `Error: writeDiagram: unknown diagram type`. |
| `meta` | `title`, `subtitle`, `locale`, `visual_preset`(없으면 `classic`)만 `applyTemplate`로 전달. |
| `cards` | 카드 객체 배열 또는 `undefined`. `renderCards`로 변환(아래 D). |
| `svg` | 렌더러가 만든 `<svg>…</svg>` 문자열(6칸 들여쓴 블록). |
| 동작 | 아래 R-14. 반환값 없음, 성공 시 stdout에 `outPath`. |

**D. `renderCards(cards)` 출력 모양**

`<!-- Info Cards -->` 주석 뒤 `<div class="cards">` 안에 카드마다 `<div class="card"><div class="card-header"><div class="card-dot <dot>"></div><h3><title></h3></div><ul><li><item></li>…</ul></div>`를 빈 줄로 구분해 놓는다. `cards`가 배열이 아니거나 비면 `<div class="cards">`가 비어 있다(요소는 남는다). `dot`은 `esc` 처리만 하고 값 검증은 스키마(7색)가 한다.

**E. 모든 타입 SVG 공통 계약**

| 항목 | 값 |
|---|---|
| 루트 | `<svg viewBox="0 0 W H" … role="img" lang="<로케일>" aria-labelledby="archify-diagram-title archify-diagram-description" data-animation="trace" data-preset="<preset>" [data-engineering-profile] data-quality-profile="standard\|showcase" [data-quality-gates="advisory"]>` (`svgRootAttrs`). `data-animation`은 항상 `trace`이고 `meta.animation`(`trace\|none`)은 렌더러가 읽지 않는다(무효). `data-quality-profile`은 `--quality`/환경 변수 → `meta.quality_profile` 순으로 정하되 `showcase`가 아니면 모두 `standard`, 어느 쪽도 없으면 `standard` + `advisory`. 소비처별 차이는 1.3 I. |
| 접근성 이름 | 루트 첫 두 자식 `<title id="archify-diagram-title">`(meta.title), `<desc id="archify-diagram-description">`(meta.subtitle 또는 `diagram.description.<kind>` 문장) |
| 공통 `<defs>` | 화살촉 마커 4종(`arrowhead`, `-emphasis`, `-security`, `-dashed`), 배경 `pattern#grid` (`renderDefinitions`) |
| 노드 | `<g id="node-<id>" data-node-id data-node-label tabindex="0" role="button" aria-label aria-pressed="false" [data-node-kind/sublabel/tag/context/brand…]>` + `<title>` 툴팁(`focusNodeAttrs`, `focusNodeTitle`). 의미 심볼(`data-semantic-sigil`)은 렌더러가 SVG 안에 직접 그리며 포커스 대상이 아니다. |
| 엣지 | `data-edge-from data-edge-to [data-edge-label] [data-edge-key=<인덱스>] [data-edge-id]` (`focusEdgeAttrs`), 애니메이션 순서 `data-animate="<kind>" style="--step:<0..12>"` |
| 범례 | `<g data-legend …>` 안 `data-legend-semantic-kind`·(상호작용 항목은) `data-legend-kind data-legend-label` |
| 타입별 훅 | 위 공통 훅 말고 훅은 **타입별로 다르다**. `data-motion-choreography`는 sequence·dataflow·lifecycle·timeline·waterfall만, `data-composition-points`는 관계 경로가 있는 8개 타입(timeline·waterfall 없음), 교차 헤일로(`data-composition-crossover="halo"`)는 architecture·dataflow·lifecycle의 자동 라우트만, 독립 포트 표지(`data-composition-independent`)는 architecture(`labelAt` 없을 때)·lifecycle만, `data-composition-route="straight"`는 `route:"straight"`·`via` 없음·점 2개의 **대각선**일 때만(architecture·dataflow), `data-diagram-type`은 architecture + 저자 `meta.viewBox`일 때만, `data-reader-fit` 값·`data-reader-min-text`·`-primary-text`는 타입·`meta.viewBox` 유무별. 전체 표(값·쓰는 곳·읽는 곳)는 [rendering-contracts.md](rendering-contracts.md) 1.3 A가 소유한다. |

**F. architecture: 입력 키 → 렌더 효과** (입력 스키마 검증은 input-validation 소관, 아래는 렌더러가 읽는 값)

| 키 | 렌더 효과 |
|---|---|
| `components[]` `id,type,label` 필수 | `type`(frontend·backend·database·cloud·security·messagebus·external)이 색 클래스 `c-<type>`·텍스트 `t-<type>`·범례 묶음을 정한다. `icon`은 모서리 심볼만 바꾸고 `icon:"none"`이면 생략. |
| `pos:[x,y]`, `size:[w,h]` | 위치·크기. `size` 기본 `[120,60]`. `pos`가 있으면 `row/col`보다 우선. |
| `row,col` + `layout{mode:"grid",origin,cols,gapX,gapY,cellW,cellH}` | 격자 배치. 기본 `origin [40,80]`, `cols 4`, `gapX 30`, `gapY 40`, `cellW 130`, `cellH 64`. `pos` 값 = `[ox + col×(cellW+gapX), oy + row×(cellH+gapY)]`. `layout`이 없으면 자유 배치(모든 컴포넌트가 `pos` 필요). |
| `sublabel`, `tag`, `brand` | 노드 보조 문구·태그·로고. 폭에 맞춰 글자 크기를 줄이고, 최소 크기로도 안 맞으면 진단. |
| `boundaries[]` `kind(region\|security-group),label,wraps[],pad` | `wraps` 멤버의 외곽 사각형 + 여백 → 프레임. `pad` 기본 30. |
| `connections[]` `from,to` 필수, `label,variant,fromSide,toSide,route,via,labelAt,labelDx,labelDy,labelSegment,width` | 라우팅·라벨. `variant`: default·emphasis·security·dashed → 선 클래스·화살촉·라벨 색. `route`: auto·straight·orthogonal-h·orthogonal-v. `width` 기본 1.5(emphasis 1.8). |
| `meta.viewBox` | 있으면 그대로 쓰고 키우지 않는다(넘치면 진단). 없으면 자동. |
| `meta.legend{mode,entries}` | `auto`(쓰인 종류만) · `all` · `hidden`, 항목별 `label`·`visible`. 범례가 안 들어가면 `legend`를 지정했을 때만 오류, 지정 안 했으면 숨김. |
| `meta.quality_profile`, `meta.engineering_profile` | 아래 1.3 I, R-15, R-24, R-26. `deployment-ownership`이면 경계 중첩 규칙이 엄격해진다(R-25). |
| `meta.animation` | 스키마는 `trace\|none`을 받지만 렌더러가 읽지 않는다. `none`이어도 `data-animation="trace"`가 붙고 SVG 본문이 같다(R-16). |
| `cards[]` | 공통 카드 슬롯(D). |

**G. architecture 고정 상수**

`defaultW 120`, `defaultH 60`, `margin 40`, `boundaryPad 30`, `boundaryExtraBottom 20`, `boundaryLabelBaseline 18`, `boundaryLabelClearance 4`, `boundaryLabelFontPreferred 9`, `boundaryLabelFontMinimum 6`, `boundaryLabelMaskHeight 16`, `boundaryLabelRailGap 2`, `boundaryLabelFrameInset 4`, `legendH 28`. 컴포넌트 최소 간격 8px, 연결 최소 길이 24px, 라우트 모서리 반지름 8, 라벨 박스 `width=max(30, textUnits×4.8+10)`, `height 14`, 글자 8px(C-11, C-12, C-15, C-22).

**H. 타입별 표 (architecture 제외 9종)** — 상세 알고리즘은 마지막 열의 C-ID. "읽은 범위"는 2.1.

| 타입 | 입력 키 → 컴파일 결과 구조 | 레이아웃 방식 | 렌더 진단 code | viewBox 규칙 | 알고리즘 |
|---|---|---|---|---|---|
| workflow | `lanes,phases,groups,mainPath,semanticChecks,nodes,edges`, `schema_version` 1은 fixed-v1, 2는 readable-v2. `compileWorkflow`가 `{ok, svg, receipt, diagnostics}`를 돌려주고 `render-workflow.mjs`가 `ok`면 `writeDiagram`, 아니면 진단을 던진다. | v1: 6칸 고정 열(`[88,220,300,430,500,625]`), 레인 `x40 y52 w640 h104 gap20`, 노드 92×52. v2: 열 6개(시작 94, 기본 피치 120)를 제약 풀이로 정하고(인접 열 120 + 같은 레인 노드 간격·라벨·phase·group 제약을 도착 열 순서로 훑어 `x_to = max(x_to, x_from+minimum)`, 피드백 제약이 있으면 한 번 더 풀이하고, 열은 오른쪽으로만 밀림), 후보 라우트 17개를 12개 검사 + 15차원 사전식 비용으로 고른다. 라우트 실패 시 열·레인 간격 피드백으로 다시 풀고(최대 3회 재풀이), 교차·모호 통로 오류면 라우트 순서를 바꿔 최대 3번 다시 시도. 상세: [rendering-workflow.md](rendering-workflow.md) R-04~R-21. | `workflow/*` 진단 code 표는 [rendering-workflow.md](rendering-workflow.md) 1.3 F(핵심: `unknown-endpoint`, `unknown-edge-endpoint`, `unknown-node-lane`, `duplicate-node-id`, `duplicate-lane-id`, `invalid-node-column`, `non-finite-node-geometry`, `node-overlap`, `column-capacity`(v1 전용), `viewbox-capacity`, `sublabel-readability`, `explicit-pin-conflict`, `route-preset-conflict`, `solver-budget-exhausted`, `absolute-geometry-sizing`(경고), `required-path/edge`, `unexpected-root/terminal`, `semantic-node-reference`, `input-contract`). `workflow/short-edge`·`workflow/label-node-overlap`은 `column-capacity`의 `suppresses` 목록에만 나오는 문자열이고 실제로 발행되지 않는다(같은 위반은 `layout/constraint`). 공유 `composition/proper-crossing`, `ambiguous-corridor`, `arrowhead-collision` | 자동은 v1 기본 폭 720, v2는 열·레인 계산 결과 + `finalizeReadableViewBox`. 저자 `meta.viewBox` 허용(타입 규칙은 R-17). v2 SVG에 `data-layout-contract="readable-v2"`, `data-reader-fit="width-first"`는 v2·`meta.viewBox` 없음이고 (같은 열 세로 스택이 있고 레인 높이가 104 초과) 또는 고정 폭 넘침 예측(가로세로비 1.55 미만이고 1440×900 기준 높이+고정 크롬 126 > 900)일 때만. | [rendering-workflow.md](rendering-workflow.md) |
| sequence | `participants[id,type,label,sublabel]`, `messages[from,to,y,label,variant,note]`, `activations[participant,from,to]`, `segments[from,to,label]`, `meta.column_fit` | **메시지 y는 저자가 정한다**. 열은 참가자 순서대로 놓는다. `spread`(기본)는 폭에 맞춰 참가자 상자 86~190px와 열 간격 `gap`(폭에 따라 정해지는 값)을 키우고, `fixed`는 상자 86px·간격 108 고정(자동 폭 920). 노트는 이웃한 두 생명선 사이에 줄바꿈. | `sequence/unknown-endpoint`, `participant-label/sublabel-overflow`, `self-message-unsupported`, `segment-message-border-run`, `segment-label-overlap`, `note-overlap`, `note-canvas-limit`(뒤 네 개는 showcase 전용), 공유 composition 게이트 | 없으면 자동: 폭 = 2~3명이고 짧으면 560/640/720/800/920 중 처음 맞는 값, 아니면 920(넘치면 최대 가독 폭까지 키움). 높이 = `max(327, 내용 끝+65, 범례 필요 높이)`. 저자 viewBox는 스키마가 `[480,480]` 이상으로 제한하므로 "타임라인 120px 미만" 진단은 스키마 통과 입력으로는 도달하지 못한다(`schema/minimum`이 먼저 난다). | [rendering-other-types.md](rendering-other-types.md) E (C-27) |
| dataflow | `stages[label]`, `nodes[stage,row,width,height,yOffset]`, `flows[from,to,label,classification,variant,route,channelX/Y,via…]` → `compileDataflow`가 SVG 문자열을 반환 | 열 = `stageX(i)=100+i×215`(스테이지 폭 168), 행 y = `[128,242,356,470,584][row]+yOffset`, 노드 기본 112×58. 흐름은 라우터·라벨 배치기로 놓고, 레이아웃 오류면 포트 재균형(`rebalancePorts`)으로 한 번 더 시도. | `dataflow/unknown-endpoint`, `node-above-area`, `node-below-area`, 공유 composition 게이트 | 자동: 폭 `max(480, 내용 폭+24)` 높이 720. showcase+자동이면 라벨에 맞춰 높이 재산정(`max(360, 내용 바닥+24+74)`), 폭은 라벨 오른쪽 끝+24까지 키움. 저자 viewBox는 그대로. | C-34, [rendering-other-types.md](rendering-other-types.md) A |
| lifecycle | `mainPath[], states[id,type,label,sublabel,tag,step], transitions[from,to,label,note,variant]` (schema_version 3) | 메인 경로가 맨 윗줄(0행)의 척추. 나머지 상태는 메인 경로까지의 거리(BFS)로 아래 행에 놓는다. 전이를 spine·arc(위쪽 호)·same·between으로 분류하고, 여러 단계에서 한 상태로 나가는 전이는 괄호(bracket)·프레임으로 묶는다. 간격을 5번까지 넓혀 가며(단 `spineGap`은 척추 행 폭이 `readableWidthBudget`을 넘게 되면 올리지 않음) 라벨이 놓이는 최소 비용 배치를 고른다. | `lifecycle/duplicate-state`, `unknown-main-path-state`, `repeated-main-path-state`, `unknown-endpoint`, `main-path-gap`, `state-text-too-long`, `too-wide`, `label-unplaced`, `crowded-side-transitions` | 저자 viewBox 없음. 폭 `max(640, 내용 오른쪽+56)`, 높이 `내용 바닥 + (범례 있으면 78+추가, 없으면 32)`. | C-28, [rendering-other-types.md](rendering-other-types.md) B |
| erd | `entities[id,label,attributes,row,col,pos,width]`, `relationships[from,to,fromCardinality,toCardinality,fromOptional,toOptional,identifying,…]`, `layout{mode:"grid",origin,gapX,gapY,entityW,headerH,rowH}` | **띠 격자**: 각 열은 그 열의 가장 넓은 상자, 각 행은 가장 큰 높이를 갖고 상자는 열 안에서 가운데 정렬. 기본 `origin[32,40] gapX56 gapY44 entityW240 headerH30 rowH20`, 엔티티 높이 = `headerH + max(1,속성 수)×rowH + 6`. 관계 선은 공용 라우터 + 같은 corridor는 레인 오프셋 12, fan-in은 공용 trunk로 묶음, 카디널리티 마커는 `<defs>` 확장. 도메인(`tag`) 띠 캡션. | `erd/domain-not-drawn`, `erd/header-text-capacity`, `erd/attribute-text-capacity`, `layout/marker-capacity`, `layout/constraint`(자기 관계 `from===to`도 이 code로 거부) | 자동: 폭 `ceil(최대 x+24)`(범례가 더 넓으면 범례 폭+48), 높이 `ceil(최대 y+24+34+범례 추가)`에 범례가 안 맞으면 34씩 최대 4번 추가. 저자 viewBox 허용. | C-29, [rendering-other-types.md](rendering-other-types.md) C |
| class | `types[id,label,kind,attributes,methods,row,col,pos,width]`, `relationships[from,to,kind,…]`, `layout{origin,gapX,gapY,typeW,typeMaxW}` | 격자(항상 켬, 기본 `gapX128 gapY84 typeW180 typeMaxW300`, 반칸 열 `col:1.5` 허용). 상자 높이 = 헤더 + 속성/메서드 구획. 일반화(상속·구현)는 자동 라우트이고 (`to`,`kind`)가 같은 멤버가 2개 이상이며 상위 바닥과 첫 하위 top의 간격이 40 이상일 때 한 버스(위쪽 상위 타입에서 아래로)로 묶는다. 다른 타입을 관통하거나 일반 경로와 충돌하면 그 묶음은 버스 없이 일반 라우트로 간다(충돌 롤백). 관계 표기 6종(dependency, association, inheritance, realization, composition, aggregation)은 `NOTATION` 표. | `class/inheritance-cycle`, `class/inheritance-kind`, `class/realization-target`, `class/title-text-capacity`, `layout/marker-capacity`, `layout/constraint`(자기 관계도 이 code로 거부) | 자동: 폭 `max(320, ceil(최대 x+24))`, 높이 `max(240, …)` + 범례 구간(위 erd와 같은 보정). 저자 viewBox 허용. | C-30, [rendering-other-types.md](rendering-other-types.md) D |
| tree | `nodes[id,label,parent,sublabel,collapsed]`(루트 1개), `layout{direction:down\|right,gapX,gapY,nodeW,nodeMaxW}` | 세대마다 띠 하나(가장 큰 노드 크기)를 공유. 다른 축은 말단부터 차례로 놓고 부모를 자식들의 가운데에 맞춘다. 말단 3개 이상이 연속된 down 방향은 들여쓴 목록으로 쌓는다. 접힘 상태와 무관하게 좌표 고정. | `tree/duplicate-id`, `tree/missing-parent`, `tree/root-count`, `tree/cycle`(묶음 코드 `tree/structure`), `layout/constraint`(저자 viewBox에 노드가 넘칠 때) | 자동: down `[max(320, ceil(최대 x+32)), max(240, ceil(최대 y+32+11.5))]`, right는 가로에 11.5를 더함. 저자 viewBox 허용(노드가 viewBox−16 안에 안 들면 진단). | C-31, [rendering-other-types.md](rendering-other-types.md) |
| timeline | `lanes[id,label]`, `events[id,at,title,detail,lane,kind]`, `meta.timezone`, `layout{width,breaks}` | 시간축 선형. 가장 긴 공백이 중앙 간격의 8배이고 전체의 10% 초과면 최대 8개를 휴지기(`≈ 길이`)로 압축(`breaks:none`이면 끔). 카드는 레인 선 위·아래 열로 겹침 없이 쌓는다. 눈금은 표시 시간대의 벽시계 정시. | `timeline/duplicate-id`, `duplicate-lane-id`, `unknown-lane`, `invalid-timestamp`, `invalid-timezone`(묶음 `timeline/input`) | 저자 viewBox 없음. 폭 `ceil(축 오른쪽+28)`(축 폭 기본 960, 레인 라벨 폭 포함), 높이 = 마지막 레인 바닥+28(+범례 34+추가). | C-32, [rendering-other-types.md](rendering-other-types.md) |
| waterfall | `spans[id,name,start,end,duration,parent,status,service]`, `meta.unit`, `layout.width` | 행 하나 = span 하나(부모→자식, 시작 시각 순 깊이 우선). x는 `axisX0 + (t−t0)×scale`, `scale = 축폭(기본 760)/wall`, 눈금 간격은 {1,2,2.5,5}×10ⁿ 중 80px 이상. `incomplete`는 기록된 마지막 시각까지 열린 막대. | `waterfall/duplicate-id`, `invalid-timing`, `missing-parent`, `cycle`(묶음 `waterfall/input`) | 저자 viewBox 없음. 폭 `ceil(축 오른쪽 + max(24, 가장 긴 막대 라벨이 넘는 폭) + 28)`, 높이 `ceil(행 바닥 + 28 (+34+범례 추가))`. | C-33, [rendering-other-types.md](rendering-other-types.md) |

**I. 품질 프로파일 소비처 (타입별 요약)** — 코드 줄과 9개 조합 실행 결과는 [rendering-contracts.md](rendering-contracts.md) 1.3 B, R-02, R-03.

| 소비처 | 보는 값 |
|---|---|
| SVG 루트 `data-quality-profile`·`-gates` | 모든 타입: 환경(`--quality`) → `meta.quality_profile` |
| architecture 본문, sequence 본문 | **`meta.quality_profile`만**(`--quality`만 주면 루트는 showcase인데 본문은 standard 경로). architecture는 경계 제목 조합·라벨 재배치(R-24, R-33)·`route-out-of-bounds`·`boundary-encloses-non-member`·`label-gap`·`excessive-route-detour`, 예외로 `arrowhead-collision`은 환경 → `meta`. sequence는 메시지 라벨 글자·폭 단위(showcase 6.6·11, 그 외 5.2·9)·`readableMessages`·showcase 전용 진단·범례 오류 |
| workflow·dataflow·erd·class 본문 | 환경 → `meta`(환경 우선). 공유 게이트(`clean*Problems`)도 환경을 먼저 본다 |
| lifecycle·tree·timeline·waterfall | 본문에서 보지 않고 루트 속성만 |
| 정적 검사(`check`) | SVG 루트 `data-quality-profile`(환경 변수는 안 봄)와 `data-quality-gates`. 그래서 `--quality`만 준 architecture·sequence는 본문은 standard 경로인데 검사만 showcase가 될 수 있다(검사가 이 불일치를 못 잡는다) |

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `archify render <type> <in> [out]`, 위치 인자가 3개 초과·2개 미만, 또는 `--`로 시작하는 알 수 없는 인자 | 위치 인자 3개까지면 `renderers/<type>/render-<type>.mjs <in> [out]`을 자식 프로세스로 실행하고 자식의 종료 상태를 그대로 따른다. 인자 오류는 렌더러를 실행하지 않고 오류. 타입이 TYPES에 없으면 `cli/unknown-diagram-type` | 코드 확인 |
| R-02 | 렌더러 직접 실행, 입력 인자 생략 | `<스킬>/examples/<기본 예제>`를 읽고 출력은 `argv[3]` → `meta.output` → `<type>.html`(현재 디렉터리) 순으로 정한다. 인자 없이 architecture를 실행하면 현재 디렉터리에 `web-app-rendered.html`이 생기고 stdout이 그 절대 경로 | 실행 확인 |
| R-03 | `--quality X`, `--repo-root P` | 자식 프로세스 환경에 `ARCHIFY_QUALITY_PROFILE=X`, `ARCHIFY_REPO_ROOT=P`(값이 있을 때만) | 코드 확인 |
| R-04 | 렌더 중 분류된 진단 오류(`archifyDiagnostics`) | 파일을 쓰지 않는다(기존 출력 보존). stderr `message` + 진단별 `[code] message Fix: …`, 종료 1. `ARCHIFY_DIAGNOSTIC_FORMAT=json`이면 stderr 한 줄 JSON `{schemaVersion:1, ok:false, source:"renderer", error, diagnostics[]}`. 진단 한 건의 필드는 `code, severity, message, subject, evidence, supportedFixes`(필드·정리 규칙·code 접두사의 원본은 [input-validation.md](input-validation.md) 1.3 B이고, 이 표의 종료 코드·stderr 모양은 그 문서의 "종료 코드와 stderr" 표와 같은 값임을 대조했다), JSON 모드 기록은 `code+message+subject`가 같으면 한 번만 | 실행 확인 |
| R-05 | 직접 실행에 `--layout-json`(지원 7개 타입) | HTML을 쓰지 않고 레이아웃 JSON을 stdout에. architecture 성공 JSON 키: `ok, diagram_type, layout, viewBox, components, boundaries, connections, labels`. 실패 시 같은 키에 `schemaVersion, source, error, diagnostics, contract:"archify-architecture-layout-v1"`를 합쳐 stdout, 종료 1. workflow는 `compiled.receipt`를 JSON으로 | 실행 확인(architecture 실패 경로) / 코드 확인(나머지) |
| R-06 | 템플릿에 필요한 슬롯·플레이스홀더가 없음 | `applyTemplate: template missing …` Error. `sourceEvidence`가 있는데 8번 슬롯이 없으면 별도 Error | 코드 확인 |
| R-07 | 정상 입력 | 슬롯 0~8이 1.3 B 표대로 채워지고 `ARCHIFY:` 센티널 주석이 하나도 남지 않는다 | 실행 확인 |
| R-08 | 제목·부제·카드 문구에 `& < > " '` 또는 `$&`, `</script>` | HTML 문맥은 `&amp; &lt; &gt; &quot; &#39;`로 이스케이프, `$` 시퀀스는 문자 그대로 보존. JSON script는 `<` `>` `&`를 `\u00XX`로 | 실행 확인 |
| R-09 | `meta.subtitle` 없음·공백만 | `<p class="subtitle">` 줄 전체가 사라진다. 있으면 `<h1>` 줄 다음 줄에 같은 들여쓰기로 | 실행 확인 |
| R-10 | `meta.locale` | 번들 6종이면 그 로케일의 `<title>` 문장·`{{i18n:}}`·i18n 데이터, `lang`은 매니페스트의 정규 태그. 번들도 없고 사용 가능한 `translations`도 없으면 영어로 폴백하고 stderr에 `archify: meta.locale "<x>" has no bundled catalog and no usable meta.translations; the Viewer chrome and <html lang> fall back to English.`, 종료 0. i18n 데이터에는 `viewer.` 키만 | 실행 확인 |
| R-11 | `cards` 있음/없음/빈 배열 | 카드 구조는 1.3 D. 없으면 `<div class="cards">`가 빈 채로 남는다. 10개 타입 모두 `cards`를 `writeDiagram`에 넘긴다 | 실행 확인(tree·class·waterfall·timeline은 카드 없음, 나머지는 예제 카드 수 일치) |
| R-12 | native 10개 타입 어느 것이든 | 산출 HTML에 입력 JSON이나 `diagram_type` 문자열이 없다. 담기는 것은 렌더러가 만든 SVG 속 값과 카드·제목·부제뿐 | 실행 확인(18개 산출물에서 `diagram_type` 0건) |
| R-13 | `sourceEvidence`가 null/객체 | null이면 8번 슬롯은 빈 문자열(그 줄은 공백만 남음), 객체면 `<script id="archify-source-evidence-data">`에 `{schemaVersion, verified, repository{url,revision,shortRevision,label,href}, referenceCount, nodes{<id>:[{path,line,endLine,href}]}}`. 증거가 있는 노드에는 메뉴 배지를 위해 노드 위 18px(`evidenceHeader`) 등 여백이 생기는 타입이 있다(tree) | 실행 확인(architecture) / 코드 확인(tree 여백) |
| R-14 | `writeDiagram` 쓰기 | (1) `applyTemplate`로 HTML 문자열 생성. (2) 출력 폴더를 `mkdir -p`. (3) 대상 스냅샷을 잡고 비정규 파일·다중 하드링크면 거부. (4) 같은 폴더에 `.archify-render-<pid>-<time36>-<seq>.tmp`를 `O_EXCL\|O_NOFOLLOW`로 만들어 쓴다. 기존 대상이 있으면 그 모드(권한)를 유지하고 새 파일은 umask. (5) 입력 파일로의 별칭 재검사 후 후보를 확인(sha256·크기·inode)하고 `publishRegularFileBinding`으로 공개한다: 기존 대상이 있으면 하드링크 백업(`.archify-remove-<hex>/previous` + 복구 기록) → 공개 이름을 격리 폴더로 옮겨 확인 후 제거 → 후보를 공개 이름에 `link` → 후보 이름 제거. **rename 덮어쓰기가 아니고** 제거와 `link` 사이에는 공개 이름이 없는 구간이 있다(원본 주석이 crash-atomic이 아니라고 명시). (6) 임시 파일은 성공이든 실패든 소유 확인 후 삭제. (7) 성공 시 stdout에 `outPath`. 실패 코드 `output/target-not-regular-file`, `target-hardlinked`, `target-changed`, `target-indeterminate` 4종은 `publishRegularFileBinding` 실패를 접은 것이고(`committed-with-warning`은 성공으로 처리), 파일시스템 예외(mkdir·쓰기 실패 등)는 `output/write`다. 실패하면 기존 대상은 그대로(복원 실패 시에도 `target-indeterminate`로 접힘). `deliver`의 쌍 교체는 같은 기본 연산을 쓰되 잠금·journal이 있고 단계별로 도는 다른 경로다. 순서·롤백·중단 후 상태: [rendering-contracts.md](rendering-contracts.md) R-12~R-21, 1.3 D~F | 코드 확인(순서·롤백, `atomic-output.mjs:1120-1329`) / 실행 확인(디렉터리 대상 거부, 모드 유지, 하위 폴더 생성, 임시 파일 잔존 0, 하드링크 대상 거부) |
| R-15 | `--quality`(환경)와 `meta.quality_profile` | 루트 `data-quality-profile`·`-gates`는 환경(`--quality`) 우선, 없으면 `meta.quality_profile`, 둘 다 없으면 `standard`+`advisory`이고 `showcase`가 아닌 값은 `standard`다(CLI의 `--quality foo`는 종료 2, 렌더러 직접 실행의 환경 `foo`는 `standard`·advisory 없음). **본문 게이트가 어느 값을 보는지는 타입별로 다르다**(1.3 I): architecture·sequence 본문은 `meta`만, workflow·dataflow·erd·class는 환경 우선, lifecycle·tree·timeline·waterfall은 루트 속성만 쓴다. 정적 검사는 루트 속성만 본다. 공유 게이트의 켜짐: `clean-flow/*`는 항상, `composition/proper-crossing`·`ambiguous-corridor`·경로 리듬·라벨-라우트 간격·라벨 캔버스 포함은 유효 `showcase`에서만 오류, `container-border-run`은 **렌더러에서** 유효 프로파일(standard든 showcase든)이 있으면 항상 오류(정적 검사는 `data-quality-gates`로 오류/경고를 가른다: [verification-gates.md](verification-gates.md) R-12). architecture의 경계 제목 조합(R-24)·라벨 자동 재배치(R-33)·`boundary-encloses-non-member`·`route-out-of-bounds`·`label-gap`(R-26)·`excessive-route-detour`는 환경이 아니라 `meta.quality_profile`만 본다(`--quality showcase`만 주면 루트는 showcase이고 본문은 standard 경로). 근거와 9개 조합 결과: [rendering-contracts.md](rendering-contracts.md) R-02, R-03 | 실행 확인(루트 속성 90건, architecture·sequence 본문 차이) / 코드 확인(소비처 전수) |
| R-16 | 모든 타입 SVG 루트 | 1.3 E 표의 공통 속성·`<title>/<desc>`·`<defs>`·노드/엣지/범례 훅을 갖는다. 그 밖의 훅(`data-motion-choreography`, `data-reader-*`, `data-detail*`, `data-graph-role`, `data-composition-*`)은 **타입·`meta.viewBox`·자동/명시 라우트별로 다르게** 붙는다(1.3 E 타입별 훅 행, 전체 표는 [rendering-contracts.md](rendering-contracts.md) R-04~R-09). `meta.animation: "none"`이어도 `data-animation="trace"`가 붙고 SVG 본문이 바이트 단위로 같다(rendering-contracts R-01). `<svg>` 앞에 6칸 들여쓰기, 닫는 태그 `      </svg>` | 실행 확인(루트·title·desc, `meta.animation` 10타입×3조건) / 코드 확인(훅, 읽는 곳은 grep 수준) |
| R-17 | viewBox 결정(타입별) | 저자 `meta.viewBox`를 스키마가 허용하는 타입은 architecture·workflow·sequence·dataflow·erd·class·tree. lifecycle·timeline·waterfall은 스키마에 없어 항상 자동. 자동값은 1.3 H·R-27 공식. 저자 viewBox는 자동으로 키우지 않고 넘침을 진단으로 알린다 | 코드 확인(렌더러·스키마 키 목록) / 실행 확인(자동값 10건) |
| R-18 | 렌더 진단 전달 | 렌더러는 문제 문장 목록을 `throwDiagnosticProblems(prefix, problems, {code='layout/constraint', subject, diagnostics})`로 던진다. 구조화된 상세가 없는 문장은 기본 code `layout/constraint`(또는 앞서 기록된 같은 문장의 진단)로 나간다. 메시지 `prefix:\n- 문장…` | 코드 확인 |
| R-19 | 렌더 진단 code 목록 | architecture는 R-35 표, 나머지 타입은 1.3 H 표의 code. 공유 게이트(`clean-flow/*`, `composition/*`, `legend/*`)는 R-35 아래 | 코드 확인 |
| R-20 | architecture 컴포넌트 위치 | `pos` 있으면 그것, 없고 `layout.mode:"grid"`면 `[ox+col×(cellW+gapX), oy+row×(cellH+gapY)]`, 둘 다 없으면 NaN→검증 문제. `layout`이 있는데 `mode`가 `grid`가 아니면 `layout.mode must be "grid"…`. 격자 검증: `col ≥ cols`, 같은 셀 중복, 음수 | 코드 확인 |
| R-21 | architecture 컴포넌트 검증 | 비유한 pos/size → `architecture/non-finite-component-geometry`, 크기 ≤0 → `architecture/invalid-component-size`, viewBox 밖 → `layout/component-out-of-bounds`(수정안: 겹친 만큼 이동하거나 `meta.viewBox`를 최소 [W,H]로), 라벨 추정폭 `textUnits×6.6 > width+8` → `architecture/component-label-overflow`, sublabel·tag가 최소 글자(6px)로도 폭 `width−8`에 안 들면 `architecture/component-sublabel-overflow`·`component-tag-overflow`, 간격 8px 미만 → `layout/component-overlap`(수정 제안 2개 포함) | 실행 확인(overlap, out-of-bounds) / 코드 확인(나머지) |
| R-22 | architecture 경계 프레임 | 멤버 bbox에서 `pad`(기본 30)씩 넓히고 위쪽은 `max(pad, 22[, quality_profile 있으면 24])`, 아래쪽은 추가 20. `x=minX−pad`, `y=minY−topPad`, `width=maxX−minX+2pad`, `height=maxY−minY+topPad+20`. 멤버 id가 없으면 건너뜀(그 wraps는 진단 문장). 클래스 `kind` region→`c-region` rx12, security-group→`c-security-group` rx8 | 실행 확인(2컴포넌트 경계: x10 y50 w420 h110) |
| R-23 | architecture 자동 viewBox | `meta.viewBox`가 없으면 `[ceil(maxX+40), ceil(maxY+40+28+범례 추가높이)]`. maxX·maxY는 컴포넌트·경계 프레임·연결 라벨 박스·라우트 점 전부의 최대. 범례 최소 폭이 `폭−80`을 넘으면 폭을 `ceil(범례 minWidth+80)`로 올리고 다시 잰다 | 실행 확인(440×208, 경계 포함 470×228) |
| R-24 | quality_profile이 있는 architecture의 경계 제목 | 제목 상자를 프레임 안쪽 레일(`boundaryLabelMaskHeight 16`, 글자 9→최소 6)에 놓고, 컴포넌트·다른 제목과 겹치면 위로 올리며, 라우트와 겹치면 레일을 따라 슬라이드한다. 프레임은 제목을 포함하도록 위로 늘어난다. 최대 32번 반복해 viewBox 폭에 맞는 데스크톱 가독 최소 글자(`minimumReadableSourceTextPx`)로 수렴하지 못하면 `composition/desktop-readability` 문제. 프로파일 없음이면 이전 방식(프레임 y 고정) | 코드 확인 |
| R-25 | `engineering_profile:"deployment-ownership"` | 경계 둘의 `wraps`가 일부만 겹치면(부분 교차) 오류, 프레임이 겹치는데 포함 관계가 `wraps` 포함 관계와 다르거나 멤버가 안 겹치는데 프레임이 겹치면 오류. 이 프로파일이 아니면 이 규칙은 적용 안 함 | 코드 확인 |
| R-26 | `meta.quality_profile:"showcase"`인 architecture | 경계 프레임이 `wraps`에 없는 컴포넌트를 통째로 포함하면 `layout/boundary-encloses-non-member`. 연결 라우트 점이 viewBox 밖이면 `layout/route-out-of-bounds`. 짧은 수평 틈에 라벨이 안 들면 `composition/label-gap`. 화살촉 간격 부족 `composition/arrowhead-collision`은 유효 프로파일(환경 포함)이 showcase일 때 | 코드 확인 |
| R-27 | 명시 지오메트리 | `via`가 있으면 그 점들을 그대로(공선점·0길이 구간 포함) 쓰고 정규화하지 않는다. `route`가 `straight`면 중간점 없음, `orthogonal-h`면 `[[midX,sy],[midX,ey]]`, `orthogonal-v`면 `[[sx,midY],[ex,midY]]`. 명시 라우트는 자동 라우트보다 먼저 계획된다. 점이 `normalize`되는 것은 자동 라우트뿐. `route:"straight"`이고 `via`가 없고 점이 2개인 **대각선**일 때만 경로에 `data-composition-route="straight"`가 붙고, 정적 검사의 직각 검사(verification-gates R-09)가 이 표지를 예외로 읽는다 | 실행 확인(`orthogonal-v`, 같은 y에서 점 `160,110;160,110;280,110;280,110` 보존) / 코드 확인(`authoredStraightRouteAttrs`) |
| R-28 | 자동 연결 변·포트 | 변 추론 `defaultFromSide`: `dx≠0 && |dx|≥|dy|`면 `dx<0?left:right`, 아니면 `dy>0?bottom:top`(`defaultToSide`는 반대편). `fromSide/toSide`가 `auto`가 아니면 저자 값 고정. 같은 변·같은 상자에 자동 연결이 2개 이상이면 상대 중심 좌표 순으로 정렬해 변 가운데 기준 ±간격으로 포트를 퍼뜨림(간격 기본 최대 14, 화살촉이 더 필요하면 `max(14, 3.5×(선굵기 합)+3.5)`, 가장자리 여백 16). 팬아웃 변(`preferReadableRoutes`)은 형제 이웃이 같은 쪽 기본 변을 쓰고 그 사이 가로 통로가 다른 상자로 막힐 때만 수직 변으로 바뀐다("한 줄로 늘어선 이웃은 항상 같은 수직 변"이 아니다). 상세: [rendering-architecture-routing.md](rendering-architecture-routing.md) R-04~R-07 | 코드 확인(실행 사례는 routing T-05, T-07, T-10, T-11) |
| R-29 | 자동 라우트 후보 순서(`routeVia`의 `auto`) | 앞에서부터 처음 "유효"한 후보를 쓴다. 대략 ①`|Δ|<4`이면 직선 ②리듬 브리지 ③포트가 가까운 평행 변이면 바깥 채널(±16) ④수평 먼저·수직 먼저 두 꺾임과 변 인식 브리지(라벨 직사각형이 컴포넌트와 2px 넘게 겹치지 않는 후보를 우선) ⑤중점에서 16씩 벌린 평행 채널 ⑥장애물 격자 최단 경로(굽힘 벌점 48, 격자 노드 4096·장애물 80, 계획 전체 64회 한도) ⑦없으면 변 규칙을 지키는 첫 후보로 폴백해 검증이 보고하게 한다(architecture는 타입 우선 후보가 없음). 수락 술어·단계별 검사 차이·격자 좌표 규칙은 [rendering-architecture-routing.md](rendering-architecture-routing.md) R-08~R-12, R-25 | 코드 확인 / 실행 확인(routing T-01~T-06) |
| R-30 | 연결 계획 순서·라벨 예약·개선 스윕 | 명시 라우트가 먼저, 자동은 두 중심 간 맨해튼 거리 오름차순(동률은 입력 순). 각 연결은 변 후보 쌍(추론 변 우선, 다음 추론에서 벗어난 끝 수·포트 거리 순)을 돌며 처음 "깨끗한" 라우트를 고른다. 라벨이 있으면 라벨 직사각형을 예약해 이후 연결의 장애물로 쓰되, 예약을 무시한 결과 `plain`이 `길이(plain)×1.25+64 < 길이(chosen)`일 때만 plain으로 교체한다. 계획이 끝나면 **개선 스윕 6단계를 정해진 순서로 각 1회**(상호 연결 쌍 → 복잡한 경로 → 마주 보는 직선 → 라벨 때문에 막힌 경로 → 코너 포트 한 번 꺾기 → 자동 viewBox일 때 아래 여백 24px 안의 교차 해소) 돈다. 스윕은 격자 탐색을 쓰지 않고 한 번에 연결 하나만 바꾸며, 새 경로는 비용(`길이 + 굽힘×48 + 교차×160`)이 엄격히 작을 때만 채택한다. 상세: [rendering-architecture-routing.md](rendering-architecture-routing.md) R-02, R-13~R-21 | 코드 확인 / 실행 확인(routing T-02, T-03, T-13) |
| R-31 | 경로 그리기 | `d`는 `roundedPath(points, 8)`(모서리마다 반지름 `min(8, 앞길이/2, 뒷길이/2)`, 1 미만이면 직선 모서리). 선 클래스·마커는 `variant`로 `a-default/arrowhead` 등. architecture의 자동 라우트는 불투명 마스크 밑선(`stroke-width+4`, `data-graph-role="automatic-crossover-underlay"`)과 `data-composition-crossover="halo"`를 쓴다(교차 시 X가 보이도록. 같은 헤일로는 dataflow·lifecycle의 자동 라우트에도 있고 다른 타입에는 없다). 명시 라우트는 밑선 없음. `data-composition-points="x,y;x,y…"`는 관계 경로가 있는 8개 타입의 경로에 붙고 timeline·waterfall에는 없다(관계 경로가 없음) | 실행 확인(속성) / 코드 확인(타입별 쓰기, rendering-contracts R-08) |
| R-32 | 연결 라벨 위치 | `labelAt` 있으면 그 좌표. 없으면 점 2개면 `[(x0+x1)/2+labelDx, y0−10+labelDy]`, 3개 이상이면 `labelSegment`(기본 1) 구간 중점의 `[…+labelDx, …−10+labelDy]`. 박스는 `lx` 중심, `y=ly−10`, 폭 `max(30, textUnits×4.8+10)`, 높이 14, 마스크 사각형(`c-mask`) 위에 글자 8px 중앙 정렬 | 실행 확인(HTTPS: `x=220 y=100`) |
| R-33 | 라벨 자동 재배치 | `meta.quality_profile==="showcase"`일 때만, `labelAt/labelDx/labelDy/labelSegment` 중 하나라도 있는 라벨은 건드리지 않고, 컴포넌트·경계 제목·다른 라벨·다른 연결 선과 겹치거나 viewBox 밖이면 후보 위치(선 옆 비율 0.5/0.25/0.75/…, 슬라이딩, 고리 오프셋)를 순서대로 시도해 첫 빈 곳으로 옮긴다. 캔버스·노드·라우트는 바꾸지 않는다(범례 대역 보존) | 코드 확인 |
| R-34 | 라벨 충돌 진단 | 라벨 박스가 컴포넌트와 겹치면(허용 −2px) 문제(`labelDx/labelDy/labelSegment/labelAt` 안내와 이동 제안 포함), showcase+짧은 수평 틈이면 `composition/label-gap`. 프로파일이 있으면 경계 제목과 라벨 겹침도 문제. showcase에서는 라벨-라우트 간격과 캔버스 포함 검사도 한다 | 코드 확인 |
| R-35 | architecture 레이아웃 진단 code | 아래 표 | 코드 확인(overlap·out-of-bounds는 실행 확인) |
| R-36 | architecture SVG 구성 | z-순서: 배경 격자 사각형 → 경계 프레임 → 연결 경로 → 컴포넌트 → 연결 라벨 → 경계 라벨 → 범례. 컴포넌트는 `c-mask` 바닥 사각형 + 색 사각형(rx 8, 선 1.5) + 의미 심볼 + 로고 + 라벨(11px 기본, 폭에 맞게 최소 8)·sublabel(9→6)·tag(7→6). 카드 스타일 CSS(`nodeCardStyle`)가 SVG 안 `<style>`로 들어가고 루트에 `data-node-ui=""`. 자동 viewBox면 `data-reader-fit="intrinsic-height" data-reader-min-text="7.5" data-reader-primary-text="14"`, 저자 viewBox면 `data-diagram-type="architecture" data-reader-fit="authored-height"` | 실행 확인(루트 속성) / 코드 확인(z-순서) |
| R-37 | architecture 범례 | 카탈로그 7종, `mode:"auto"`는 쓰인 컴포넌트 타입만, `all`은 전부, `hidden`은 없음. 항목별 `entries.<kind>.label`, `visible` 덮어쓰기. 범례 기준선 y = `viewBox[1]−16`, 제목은 콘텐츠 바닥+8보다 위로 못 올라감. 범례가 안 들어가면 `meta.legend`를 지정했을 때 `legend/*` 오류, 지정하지 않았으면 숨김 | 코드 확인 |
| R-38 | architecture 호출 순서 | 로드 → 컴포넌트 측정 → (경계 사각형·라우터 생성·연결 라벨 박스·경계 제목 수렴·자동 viewBox) → (showcase면 라벨 재배치) → `validateArchitecture` → `renderSvg` → `writeDiagram`. 검증이 실패하면 `renderSvg`와 쓰기 전에 종료 | 코드 확인 |
| R-40 | workflow | `render-workflow.mjs`: `compileWorkflow({workflow, qualityProfile, sourceEvidence})` → `{ok,svg,receipt,diagnostics}`. 컴파일러는 입력을 다시 스키마·ID 계약 검증하고 → 정규화 → 의미 계약 검증 → 레이아웃(v1 고정/v2 제약풀이) → 범례·레인 → 노드 측정 → 라우트·라벨 → 검증 → viewBox 확정 → SVG 순서로 돈다. 실패는 `ok:false`로 오고 렌더러가 진단으로 던진다. 열 풀이·라우트 후보·비용·피드백 루프(바깥쪽 순서 포함)·핀 충돌·진단 code는 [rendering-workflow.md](rendering-workflow.md) R-01~R-27 | 코드 확인(구조) / 상세는 rendering-workflow가 코드 확인·실행 확인 |
| R-41 | dataflow | 1.3 H 표의 좌표 공식. `compileDataflow`가 레이아웃 오류(`Data-flow layout validation failed:`로 시작)면 `rebalancePorts=true`로 한 번 더 시도하고, 두 번 다 실패하면 첫 진단을 던진다. 행 `row`는 0..4만. 프리셋 라우터·showcase 후처리·진단 상세는 [rendering-other-types.md](rendering-other-types.md) R-01~R-06 | 코드 확인 |
| R-42 | sequence | 메시지 y는 입력 그대로. 메시지 화살표는 생명선 중심에서 안쪽 7px에서 시작·끝, 라벨 박스 폭 `max(34, textUnits×단위폭+12)`(단위폭·글자 크기는 `meta.quality_profile=="showcase"`이면 6.6·11, 아니면 5.2·9. `--quality`만으로는 바뀌지 않는다, R-15). 열: `fixed`는 상자 86·간격 108(자동 폭 920), `spread`(기본)는 폭에서 상자 86~190과 간격을 계산. 타임라인 높이 = `lifelineBottom−lifelineTop`, `lifelineTop 142`, `lifelineBottom = viewBox높이−65`. 120px 미만 문장은 코드에 있으나 스키마가 `meta.viewBox`를 `[480,480]` 이상으로 막아 스키마 통과 입력으로는 도달하지 못한다(`schema/minimum`이 먼저). `inspect-sequence-width`는 렌더러가 만들지 않는다: `check`의 `collectSequenceColumnSpace`와 `finalize`의 권고([verification-gates.md](verification-gates.md) R-38). 상세: [rendering-other-types.md](rendering-other-types.md) E, R-25~R-29 | 코드 확인(자동 viewBox 값은 실행 확인) |
| R-43 | lifecycle | `mainPath` 상태는 0행, 다른 상태는 가까운 메인 경로 상태에서의 BFS 거리 행(연결 없는 상태는 1행). 척추 전이는 `mainPath[i]→mainPath[i+1]` 중 첫 전이. 상수 `STATE_H 64`, 폭 140~220, 여백 x56 y28. 간격 `{spineGap 72, rowGap 44, drop 58, firstTrack 34}`에서 시작해 라벨이 안 놓이면 라운드마다 `+28, +28, +14, +6`으로 최대 5번. 단 척추 행 전체 폭이 `readableWidthBudget`(`floor(930×가장 작은 글자/6)`)을 넘게 되는 라운드에서는 `spineGap`만 올리지 않는다. 상세: [rendering-other-types.md](rendering-other-types.md) B, R-07~R-13 | 코드 확인 |
| R-44 | erd·class | 격자 `bandedLayout`: 열 x는 앞 열 최대폭 + `max(gapX, 라벨 요구 간격)`의 누적, 행 y는 앞 행 최대 높이 + gapY의 누적, 상자는 열 안 가운데. 반칸 열 상자는 두 열 중심의 중점. 같은 셀 중복·음수·배치 불가는 문제. 자기 관계(`from===to`)는 두 타입 모두 `layout/constraint`로 거부한다. class의 일반화 버스는 멤버 2개 이상·간격 40 이상·비관통·충돌 롤백 조건이 있다(1.3 H). 상세: [rendering-other-types.md](rendering-other-types.md) C, D, R-14~R-24 | 코드 확인 |
| R-45 | tree | 규칙은 1.3 H 표. 접힌 노드도 좌표를 차지한다. 노드 폭 = `max(140, 가장 긴 단어 폭+30)` 이상, 라벨은 같은 줄 수가 되는 가장 좁은 폭으로 줄바꿈. 최소 입력 `r→a,b` 3노드 viewBox 372×246 | 실행 확인(372×246) / 코드 확인(규칙) |
| R-46 | timeline | 표 H 규칙. 시각은 오프셋이 있는 ISO 8601이어야 하고 표시 시간대는 `meta.timezone`(기본 UTC). 최소 입력 2이벤트 viewBox 1016×237 | 실행 확인 / 코드 확인 |
| R-47 | waterfall | 표 H 규칙. `end`·`duration`이 모두 있으면 일치해야 하고, 둘 다 없으면 `status:"incomplete"`여야 한다. 최소 입력 2 span viewBox 1035×174 | 실행 확인 / 코드 확인 |
| R-48 | 10개 번들 예제 | 모두 종료 0, stdout 한 줄 절대 경로, stderr 비어 있음, `diagram_type` 0건. viewBox는 T-05 표 값 | 실행 확인 |

**R-35. architecture 레이아웃 진단 code**

| code | 조건 | 프로파일 |
|---|---|---|
| `architecture/non-finite-component-geometry` | pos·size에 유한수가 아님 | 항상 |
| `architecture/invalid-component-size` | 폭·높이 ≤ 0 | 항상 |
| `layout/component-out-of-bounds` | 컴포넌트가 viewBox 밖 | 항상 |
| `architecture/component-label-overflow` | `textUnits(label)×6.6 > width+8` | 항상 |
| `architecture/component-sublabel-overflow`, `…-tag-overflow` | 최소 글자(6px)로도 `width−8`에 안 들어감 | 항상 |
| `layout/component-overlap` | 간격 8px 미만 | 항상 |
| `architecture/unknown-endpoint` | 연결의 from/to가 컴포넌트가 아님 | 항상(수정 제안: 이웃 우선 후보 3개) |
| `layout/boundary-out-of-bounds` | 프레임이 viewBox 밖(왼쪽·위쪽 넘침은 viewBox를 키워도 못 고친다고 안내) | 항상 |
| `layout/self-loop-ports` | 자기 연결의 두 포트 거리 24px 미만 | 항상 |
| `layout/route-out-of-bounds` | 라우트 점이 viewBox 밖 | `meta.quality_profile==="showcase"` |
| `layout/boundary-encloses-non-member` | 프레임이 비멤버 컴포넌트를 통째 포함 | `meta.quality_profile==="showcase"` |
| `composition/arrowhead-collision` | 같은 대상의 자동 연결 화살촉 간격 부족 | 유효 showcase |
| `composition/label-gap` | 짧은 수평 틈에 라벨이 안 들어감 | `meta.quality_profile==="showcase"` |
| `clean-flow/endpoint-side-direction`, `clean-flow/edge-through-node` | 끝점 변 방향 위반, 라우트가 노드를 관통 | 항상(내용은 `cleanEndpointSideProblems`, `cleanFlowProblems`) |
| `composition/proper-crossing` | 서로 다른 두 연결이 진짜 교차(자동·자동 쌍은 헤일로로 통과) | 유효 showcase만 검사 |
| `composition/ambiguous-corridor`, `composition/label-route-clearance`, `composition/label-canvas-containment`, `composition/micro-segment`·`short-interior-segment`(경로 리듬) | 같은 통로 공유, 라벨-라우트 간격, 라벨이 캔버스 밖, 구간 너무 짧음 | 유효 showcase |
| `composition/container-border-run` | 라우트가 프레임 테두리를 따라 달림 | 유효 프로파일이 있을 때(standard·showcase) |
| `composition/excessive-route-detour` | `via`로 먼 우회 | `meta.quality_profile==="showcase"` |
| `composition/desktop-readability` | 경계 제목 반복이 32번 안에 수렴하지 않음(문장 앞에 `[composition/desktop-readability]` 표기) | `meta.quality_profile` 있음 |
| `legend/vertical-overflow`, `legend/label-too-wide`, `legend/content-overlap` | 범례가 안 들어감 | `meta.legend` 지정 시 오류, 아니면 숨김 |
| `layout/constraint` | 구조화된 상세가 없는 문장의 기본 code(경계 멤버 없음, 경계·제목 겹침, 라벨-컴포넌트 겹침 등) | 항상 |

- 불변식: (1) 같은 입력·같은 SHA·같은 환경이면 SVG는 같다(렌더러에 시계·난수 없음. 임시 파일 이름만 시간·pid를 쓰고 HTML에는 들어가지 않는다). 전제: 로케일 카탈로그·템플릿이 같다. `추론`(시간·난수 호출을 전수 확인하지는 않았다). (2) 출력 HTML에 `ARCHIFY:` 센티널은 남지 않는다. (3) 렌더 진단 실패 시 출력 파일의 바이트는 바뀌지 않는다.
- 미결정: 없음. 이전 목록 M-01~M-05는 하위 스펙으로 이관·해소했고(하단 "미결정" 절의 대응표) M-06은 확인 한계로 옮겼다.
- 확인 한계: (1) 렌더 결과의 시각 품질(색·겹침의 사람 눈 판단)과 브라우저 렌더링은 확인하지 않았다(이전 M-06). 타입별 알고리즘 문장은 좌표·크기·진단까지만 검증했다. (2) 설치본 `~/.claude/skills/archify`로 실행했다(레포 `archify/`와 `diff -rq` 차이 없음, overview 기록). 레포 clone 안의 코드는 실행하지 않았다. 원본 테스트(316개)는 열지 않았다. (3) 이 문서가 직접 읽지 않은 부분(architecture 라우터 개선 스윕·workflow 컴파일러 본문·8개 타입 상세·`atomic-output.mjs`)은 하위 스펙이 읽은 범위와 확인 한계를 따른다.

### 1.5 필수 코드 참조 [필수]
기준은 frontmatter SHA. 라이선스는 Apache-2.0(overview 1절).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `archify/renderers/shared/utils.mjs:130-201` `SVG_SLOT_RE`,`CARDS_SLOT_RE`,`SUBTITLE_SLOT_RE`,`serializeScriptJson`,`TEMPLATE_PLACEHOLDERS`,`applyTemplate` | 슬롯 정규식·치환 순서·이스케이프·사전 검사 | R-06~R-09, R-13 |
| C-02 | `archify/renderers/shared/utils.mjs:114-128` `renderCards` | 카드 HTML 모양 | R-11 |
| C-03 | `archify/renderers/shared/cli.mjs:361-430` `svgRootAttrs`,`svgAccessibleText`,`animateAttr`,`focusNodeAttrs`,`focusNodeTitle`,`focusEdgeAttrs` | SVG 루트·접근성·노드/엣지 데이터 속성 | R-15, R-16 |
| C-04 | `archify/renderers/shared/cli.mjs:114,122-231,233-303` `START_TYPES`,`throwOutputError`,`throwAtomicOutputFailure`,`stageRenderedHtml`,`writeDiagram` | 쓰기 순서·임시 파일·진단 code. 공개 교체 내부(`publishRegularFileBinding`, 백업·격리 제거)는 [rendering-contracts.md](rendering-contracts.md) C-03·C-04 | R-14 |
| C-05 | `archify/renderers/shared/i18n.mjs:8-10,126-200,204-228,294-324` + `archify/locales/manifest.json` | 로케일 해석, 카탈로그 층, `translateMessage`, `viewerCatalog`, `localizeTemplate` | R-10 |
| C-06 | `archify/renderers/shared/legend.mjs:35-55,75-203,204-227` `resolveLegend`,`legendFootprint`,`measureLegend`,`renderLegend` | 범례 항목 선택·측정·마크업 | R-37 |
| C-07 | `archify/renderers/shared/diagnostics.mjs:16-31,33-42,71-104,117-134,136-147,159-209` | 진단 정규화·기록·던지기·실패 JSON·경계(핸들러) | R-04, R-18 |
| C-08 | `archify/bin/archify.mjs:2243-2252,2428-2434,4271-4288` `rendererPath`,`rendererEnv`,`commandRender` | 렌더러 선택·환경 변수 전달·인자 규칙 | R-01, R-03 |
| C-09 | `archify/renderers/shared/utils.mjs:14-33,35-112` `renderDefinitions`,`SIGIL_*`,`renderSemanticSigil` | 공통 defs, 의미 심볼 | R-16 |
| C-10 | `archify/renderers/architecture/grid.mjs:1-62` | 격자 기본값·`pos` 공식·격자 검증 문장 | R-20 |
| C-11 | `archify/renderers/architecture/render-architecture.mjs:63-140` `layout`,`measureComponent`,`componentSteps`,`boundaryRect` | 상수, 컴포넌트 측정, 경계 프레임 | R-20, R-22 |
| C-12 | `archify/renderers/architecture/render-architecture.mjs:154-208,451-452` 연결 라벨 박스, `autoViewBoxFor`, `viewBox`, `legendY` | 라벨 박스·자동 viewBox | R-23, R-32 |
| C-13 | `archify/renderers/architecture/render-architecture.mjs:217-355,395-430` 경계 제목 배치와 수렴 | 경계 제목 규칙 | R-24 |
| C-14 | `archify/renderers/architecture/render-architecture.mjs:357-394` `routerOptions`,`hasAutomaticRouteGeometry`,`connectionGeometry` | 라우터 옵션(`distinctAutomaticPorts`, `preferReadableRoutes`, `readabilityBottomMargin`) | R-27, R-29, R-30 |
| C-15 | `archify/renderers/architecture/render-architecture.mjs:487-1013` `validateArchitecture` | 레이아웃 진단 전체 | R-21, R-25, R-26, R-34, R-35 |
| C-16 | `archify/renderers/architecture/render-architecture.mjs:1015-1176` 보고·그리기 함수·`renderSvg` | SVG 구성과 마크업 | R-31, R-36 |
| C-17 | `archify/renderers/architecture/render-architecture.mjs:1178-1204` 끝부분 | `--layout-json` 분기와 쓰기 분기 | R-05, R-38 |
| C-18 | `archify/renderers/architecture/routing.mjs:396-700` `routeVia` | 명시 route/via, 자동 후보 순서 | R-27, R-29 |
| C-19 | `archify/renderers/architecture/routing.mjs:701-886` 팬아웃 변, 포트 간격, 변 추론, `automaticEndpoint`, `connectionGeometry`, `routedForGeometry` | 변·포트·`d` 생성 | R-28, R-31 |
| C-20 | `archify/renderers/architecture/routing.mjs:894-1010` `candidateSidePairs`,`routeIsClear`,`crossingCount`,`readabilityCost`,`computePath` | 변 쌍 선택·비용 | R-30 |
| C-21 | `archify/renderers/architecture/routing.mjs:1011-1469` `planRoutes`,`pathFor`,`routingMetrics` | 계획 순서·개선 스윕 | R-30 |
| C-22 | `archify/renderers/shared/geometry.mjs:1332-1395,1517-1527,1703-1781,1783-1816,1839-1927` `joinRoutePoints`,`normalizeRoutePoints`,`anchor`,`automaticPortSpread`,`defaultFromSide/ToSide`,`chosenSide`,`roundedPath`,`labelPoint`,`componentFill/Text`,`arrowClassMap`,`edgeLabelAccent` | 앵커·포트 퍼뜨림·기본 변·모서리 둥글리기·라벨 점·색 표 | R-28, R-31, R-32 |
| C-23 | `archify/renderers/shared/automatic-labels.mjs:6-290` `placeAutomaticLabels`,`reservedLabelRect` | 라벨 후보 순서·충돌 정의 | R-33 |
| C-24 | `archify/renderers/shared/geometry.mjs:377-531,627-1005,1106-1330` `routeHonorsEndpointSides`,`cleanEndpointSideProblems`,`cleanFlowProblems`,`cleanCrossingProblems`,`collectAmbiguousCorridors`,`collectArrowheadCollisions`,`cleanAmbiguousCorridorProblems`,`collectBorderRuns`,`cleanBorderRunProblems`,`cleanRouteRhythmProblems`,`cleanLabelRouteClearanceProblems`,`cleanLabelCanvasContainmentProblems` | 공유 게이트와 프로파일별 심각도 | R-15, R-35 |
| C-25 | `archify/renderers/shared/route-quality.mjs:261-670` `shortestOrthogonalGridRoute`,`cleanRouteDetourProblems` | 격자 최단 경로 탐색, 우회 게이트 | R-29, R-35 |
| C-26 | `archify/renderers/shared/text-fit.mjs:24-52` + `archify/renderers/shared/desktop-readability.mjs:1-35` + `archify/renderers/shared/utils.mjs:203-260` `textUnits` | 글자 폭 단위(`textUnits`, 폭 계수 0.6, 패딩 8)·가독 최소 글자 | R-21, R-24 |
| C-27 | `archify/renderers/sequence/render-sequence.mjs:54-160,293-345,364-402,554-931,932-1104` | 열·캔버스·메시지·검증·SVG | R-42 |
| C-28 | `archify/renderers/lifecycle/render-lifecycle.mjs:25-60,106-232,244-494,857-977` | 상수·분류·간격 라운드·`layout()`·검증·viewBox | R-43 |
| C-29 | `archify/renderers/erd/grid.mjs:1-150`, `archify/renderers/erd/render-erd.mjs:69-96,193-322,503-526,546-935,1074-1358` | 띠 격자·도메인 띠·자동 viewBox·레인·trunk·검증 | R-44 |
| C-30 | `archify/renderers/class/render-class.mjs:62-95,230-253,282-325,359-375,415-520,623-820` | 격자·상자 높이·관계 표기·viewBox·버스·순환·검증 | R-44 |
| C-31 | `archify/renderers/tree/render-tree.mjs:28-113,115-312,319-324,329-368,380-390` | 구조 검증·말단 목록 쌓기·폭 측정·띠·viewBox·간선·캔버스 검사 | R-45 |
| C-32 | `archify/renderers/timeline/render-timeline.mjs:34-66,67-135,192-292,318-391` | 시간대·휴지기·눈금·카드 줄 쌓기·viewBox | R-46 |
| C-33 | `archify/renderers/waterfall/render-waterfall.mjs:35-130,160-270` | 타이밍 검증·행·스케일·눈금·viewBox | R-47 |
| C-34 | `archify/renderers/dataflow/render-dataflow.mjs:1-23`, `archify/renderers/dataflow/dataflow-compiler.mjs:62-140,250-430,1055-1072,1579-1605` | 레이아웃 상수·viewBox·검증·재시도 | R-41 |
| C-35 | `archify/renderers/workflow/render-workflow.mjs:1-47`, `archify/renderers/workflow/workflow-compiler.mjs:122-137,233-330,663-670,1362-1453,5478-5518,5541-5640,5715-5848,5917-5920` | v1 상수·v2 제약 시작부·실패 포장·컴파일 입구·SVG·영수증·피드백 루프 | R-40 |
| C-36 | `archify/renderers/shared/node-card-style.mjs:1-32` | architecture·workflow가 SVG 안에 넣는 카드 CSS | R-36 |
| C-37 | `archify/renderers/shared/layout-report.mjs:1-57` | `--layout-json`의 컴포넌트·경계·연결 직렬화 | R-05 |
| C-38 | `archify/renderers/shared/software-notices.mjs:1-6`, `archify/renderers/shared/cli.mjs:87` | 템플릿 `</head>` 앞 고지 script 삽입 | R-07 |

### 1.6 수락 사례 [필수]
출처: 모두 실행 관찰이다(설치본 `archify render`, 입력·스크립트·요약: [spec-demos/rendering/](../../../artifacts/archify/spec-demos/rendering/), 재실행 `sh demos.sh`, 결과 [summary.txt](../../../artifacts/archify/spec-demos/rendering/summary.txt)). 입력 JSON은 `in/min/*.json`.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-07 R-08 R-09 R-10 | [min.architecture.json](../../../artifacts/archify/spec-demos/rendering/in/min/min.architecture.json): 컴포넌트 2(`web`,`api`), 연결 1(`HTTPS`), `meta{title:"A $& B </script>", subtitle:"sub <b>", visual_preset:"blueprint", locale:"ko"}`, 카드 1 | `<html lang="ko" data-theme="dark" data-preset="blueprint">`, `<title>A $&amp; B &lt;/script&gt; 다이어그램</title>`, `<h1>A $&amp; B &lt;/script&gt;</h1>`, 그 아래 줄 `<p class="subtitle">sub &lt;b&gt;</p>`, `<script id="archify-i18n-data">{"locale":"ko",…}`, `id="archify-software-notices"` script 있음, `ARCHIFY:` 0건 |
| T-02 | R-23 | T-01 입력 | `<svg viewBox="0 0 440 208"` (maxX 400+40, maxY 140+40+28) |
| T-03 | R-22 R-23 R-27 | [boundary.architecture.json](../../../artifacts/archify/spec-demos/rendering/in/min/boundary.architecture.json): 같은 두 컴포넌트, 경계 `region`/`Cloud` wraps 둘, 연결 `route:"orthogonal-v"`, locale 없음 | `viewBox 0 0 470 228`, 프레임 `x=10 y=50 width=420 height=110 rx=12 class="c-region"`, 경계 라벨 `x=18 y=73 font-size=9`, 연결 `data-composition-points="160,110;160,110;280,110;280,110"` (명시 지오메트리 점 보존) |
| T-04 | R-11 R-12 | 번들 `payment-platform.tree.json`(`cards` 없음) | 종료 0, `<div class="cards">` 안이 비어 있음, `diagram_type` 0건 |
| T-05 | R-12 R-48 | 번들 예제 10개 | 모두 종료 0, stdout 한 줄 절대 경로, stderr 0바이트. viewBox: architecture 1080×588, workflow 1108×684, sequence 820×920, dataflow 1080×520, lifecycle 1152×500, erd 999×488, class 993×430, tree 1069×396, timeline 1123×485, waterfall 1089×308 |
| T-06 | R-04 R-35 R-21 | [overlap.architecture.json](../../../artifacts/archify/spec-demos/rendering/in/min/overlap.architecture.json): `api`를 `pos [100,80]`(`web`과 겹침). 출력 경로에 먼저 `seed` 파일 | 종료 1, stderr 첫 줄 `Architecture layout validation failed:`, 이어서 `[layout/component-overlap] Components "web" and "api" are less than 8px apart …  Suggested fix: move "api" pos to [168, 80] (right of "web") or [100, 148] (below)`, 출력 파일은 `seed` 그대로 |
| T-07 | R-04 R-21 | [oob.architecture.json](../../../artifacts/archify/spec-demos/rendering/in/min/oob.architecture.json): T-01에서 `meta.viewBox [320,240]` | 종료 1, `[layout/component-out-of-bounds] Component "api" falls outside the viewBox 320x240 … Fix: set meta.viewBox to at least [400, 240].`, 출력 파일 생성 안 됨 |
| T-08 | R-04 | T-06 입력에 `ARCHIFY_DIAGNOSTIC_FORMAT=json`으로 렌더러 직접 실행 | stderr JSON에서 `ok:false`, `source:"renderer"`, `diagnostics[0].code="layout/component-overlap"`, 종료 1 |
| T-09 | R-05 | T-06 입력 `--layout-json`(직접 실행) | stdout JSON 키 `ok, diagram_type, layout, viewBox, components, boundaries, connections, labels, schemaVersion, source, error, diagnostics, contract`, 종료 1 |
| T-10 | R-14 | 출력 경로가 이미 디렉터리 `out/dir.html` | 종료 1, `[output/target-not-regular-file] Output already exists and is not a regular file.` |
| T-11 | R-14 | 기존 `out/mode.html`(`old`, 권한 640)에 렌더 / 없는 `out/newdir/deep/x.html`에 렌더 | 앞: 권한 `-rw-r-----` 유지, 임시 `.archify-render-*` 잔존 0, 내용 교체. 뒤: 하위 폴더를 만들고 파일 생성 |
| T-12 | R-10 | `meta.locale:"fr"`([fr.architecture.json](../../../artifacts/archify/spec-demos/rendering/in/min/fr.architecture.json)), translations 없음 | 종료 0, stderr `archify: meta.locale "fr" has no bundled catalog and no usable meta.translations; the Viewer chrome and <html lang> fall back to English.`, `<html lang="en"`, `<title>… Diagram</title>`, i18n 데이터 `"locale":"en"` |
| T-13 | R-13 | [evidence.architecture.json](../../../artifacts/archify/spec-demos/rendering/in/min/evidence.architecture.json)(`meta.repository`, `web.sources`) + `--repo-root <clone>` / 같은 입력의 T-01(근거 없음) | 앞: `id="archify-source-evidence-data"` script 1개, 내용에 `"verified":true`, `"nodes":{"web":[{"path":"archify/renderers/shared/utils.mjs","line":150,"endLine":201,"href":"…#L150-L201"}]}`. 뒤: 해당 script 0개 |
| T-14 | R-15 R-16 | T-01 입력에 `--quality showcase` / 없이 | 루트가 `data-quality-profile="showcase"`(advisory 없음) / `data-quality-profile="standard" data-quality-gates="advisory"` |
| T-15 | R-02 | 인자 없이 `render-architecture.mjs`를 빈 폴더에서 실행 | 그 폴더에 `web-app-rendered.html` 생성, stdout이 그 절대 경로, 종료 0 |
| T-16 | R-45 | [t1.tree.json](../../../artifacts/archify/spec-demos/rendering/in/min/t1.tree.json): 루트 `r`, 자식 `a`,`b` | `viewBox 0 0 372 246` (폭 32+140+28+140+32, 높이 64+41+56+41+32+11.5→246) |
| T-17 | R-46 R-47 R-42 R-43 R-41 | [e1.timeline](../../../artifacts/archify/spec-demos/rendering/in/min/e1.timeline.json) 이벤트 2개(10:00Z, 10:30Z), [w1.waterfall](../../../artifacts/archify/spec-demos/rendering/in/min/w1.waterfall.json) span 2개(0~100ms, 자식 10~60), [s1.sequence](../../../artifacts/archify/spec-demos/rendering/in/min/s1.sequence.json) 참가자 2·메시지 2(y 180, 220), [l1.lifecycle](../../../artifacts/archify/spec-demos/rendering/in/min/l1.lifecycle.json) 상태 2, [d1.dataflow](../../../artifacts/archify/spec-demos/rendering/in/min/d1.dataflow.json) 스테이지 2·노드 2 | 각각 `viewBox` 1016×237, 1035×174, 560×327, 640×170, 480×720. 모두 종료 0 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
읽은 범위: 공통 계층 전부(`utils.mjs`, `cli.mjs`, `diagnostics.mjs`, `i18n.mjs` 핵심 함수, `legend.mjs` 일부, `layout-report.mjs`, `node-card-style.mjs`, `software-notices.mjs`). architecture: `render-architecture.mjs` 전체, `grid.mjs`, `routing.mjs`의 `routeVia`·변·포트·`computePath`·`planRoutes` 앞부분(약 1011~1090행)·`pathFor`, `geometry.mjs`의 `anchor`·`automaticPortSpread`·기본 변·`roundedPath`·`labelPoint`·`cleanCrossingProblems`·품질 프로파일 분기, `automatic-labels.mjs` 전체. tree·timeline·waterfall은 배치·viewBox 구간 전부. lifecycle은 분류·간격 라운드·검증(244~494 `layout()` 본문 제외). sequence는 열·캔버스·검증 앞부분(554~600)과 `renderSvg`. erd·class는 `grid.mjs`/상수/viewBox. dataflow 컴파일러는 앞 140줄, viewBox·재시도·`heightForLabels`. workflow 컴파일러는 함수 목록, 레거시 레이아웃, 읽기 쉬운 레이아웃의 시작 100줄, 입구(1362~1453), 꼬리(5478~5640), 피드백 루프(5715~5920). 열지 않음: 브랜드 마크 본문, 각 렌더러의 README(viewBox 줄만 grep), 테스트. 이 문서가 읽지 않은 `routing.mjs` 개선 스윕 후반·`route-quality.mjs` 본문은 [rendering-architecture-routing.md](rendering-architecture-routing.md), `workflow-compiler` 본문은 [rendering-workflow.md](rendering-workflow.md), 나머지 타입 상세는 [rendering-other-types.md](rendering-other-types.md), `atomic-output.mjs`와 SVG 훅 grep은 [rendering-contracts.md](rendering-contracts.md)가 읽었다.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-08 `commandRender` | 코드 읽음. `render`에서 알 수 없는 `--` 인자는 `Unknown render option` |
| R-02 | `cli.mjs:53,88-97,99` `loadDiagram`, `output-path.mjs` 우선순위(delivery 소관), T-15 | 실행 확인: `summary.txt`의 `default-example` 줄 |
| R-03 | C-08 `rendererEnv`(2428-2434), `commandRender`가 3번째 인자를 넘기지 않음(4271-4288) | 코드 확인. JSON 모드 전달 경로는 `deliver` 쪽 호출을 읽지 않았음 |
| R-04 | C-07 `installRendererDiagnosticBoundary`(159-209), `throwDiagnosticError`(71-76), `formatDiagnostics`(136-147), T-06 T-07 T-08 | 실행 확인. 텍스트 형식의 `Fix:` 이어 붙이기는 `formatDiagnostics` 그대로 |
| R-05 | C-17(1178-1204), C-37, `bin/archify.mjs:6990` `--layout-json is currently supported for architecture and workflow diagrams only`, `render-workflow.mjs:30-35`, T-09 | architecture 실패 경로만 실행. 7개 타입의 `layoutJsonMode`는 grep으로 확인(sequence·dataflow·lifecycle은 없음). 문서(Q3·overview)의 "validate --layout-json은 architecture·workflow 한정"은 CLI에 대해 맞고, 렌더러 자체는 7개 타입이 지원한다 |
| R-06 | C-01 `applyTemplate` 159-178 | 코드 읽음(오류 문장 그대로) |
| R-07 | C-01 188-200, C-38, T-01 | 실행 확인(`ARCHIFY:` 0건) |
| R-08 | C-01 136-141,179-181,190-192, T-01 | 실행 확인: 제목 `A $& B </script>` 결과 |
| R-09 | C-01 132,184-186,193-195, T-01, 번들 예제(부제 없는 web-app) | 실행 확인 |
| R-10 | C-05 157-200,294-324, C-01 183,191, T-01 T-12, `cli.mjs:28-43` `applyLocaleTranslations`(경고 출력은 input-validation 소관) | 실행 확인(ko, fr) |
| R-11 | C-02, 각 `writeDiagram` 호출(`cards: <diagram>.cards`), `schemas/*.schema.json`에 10개 모두 `cards` 속성, T-04 | 실행 확인 |
| R-12 | C-01 `applyTemplate` 인자에 JSON 없음, T-04 T-05 | 실행 확인(`summary.txt`의 `json_in_html=0` 18줄). 문서(Q1)와 같음 |
| R-13 | C-01 133,159-177,198-200, T-13, `render-tree.mjs:194-243` `evidenceHeader` | architecture 실행 확인, tree 여백은 코드 |
| R-14 | C-04, T-06 T-10 T-11, [rendering-contracts.md](rendering-contracts.md) R-12~R-14, C-03·C-04 | 실행 확인(디렉터리 거부·모드·mkdir) + 코드 확인(`atomic-output.mjs:1120-1329` 하드링크 백업 → 격리 제거 → `link`, 주석이 crash-atomic 아님을 명시). 이전의 "원자 교체는 추론"을 코드 확인으로 대체 |
| R-15 | C-03 `svgRootAttrs`(361-372), C-24 `qualityProfileForGate`(geometry.mjs:1302-1306), `render-architecture.mjs:99,457,769,830,884-904,963` 등 `arch.meta?.quality_profile` 직접 비교와 904의 환경 변수 우선 비교, [rendering-contracts.md](rendering-contracts.md) 1.3 B·R-02·R-03·T-02~T-06, `render-sequence.mjs:67,117,846,919`, `render-workflow.mjs:18`, `render-dataflow.mjs:17` | 코드 확인 + 실행 확인(루트 속성 90건, `--quality`만 줄 때 architecture·sequence 본문 해시 차이, 나머지 8개 타입은 같음) |
| R-16 | C-03, C-09, T-01 T-14, [rendering-contracts.md](rendering-contracts.md) 1.3 A·R-01·R-04~R-09 | 실행 확인(루트 속성, `meta.animation` 3조건 SVG 해시 동일), 훅의 쓰는 곳은 각 렌더러 줄, 읽는 곳은 grep 수준 |
| R-17 | 각 렌더러의 `meta?.viewBox` 사용, `schemas/<type>.schema.json` `meta.properties`를 `python3 -I`로 나열, T-02 T-05 T-16 T-17 | 코드·스키마 확인 + 실행 확인(자동값). **문서와 다름**: Q3 2.1 표는 viewBox가 "timeline·lifecycle·tree 제외"라 했지만 스키마·코드는 tree가 viewBox를 허용(`render-tree.mjs:319`, tree 스키마 meta에 `viewBox`)하고 waterfall은 허용하지 않는다. 구현을 사실로 썼다 |
| R-18 | C-07 `throwDiagnosticProblems`(78-104) | 코드 읽음 |
| R-19 | 1.3 H 표 code는 각 렌더러의 `code:` 문자열 grep(`rg`/`grep -o`)로 수집 후 해당 위치 열람. workflow·dataflow는 grep 목록 | 코드 확인. grep으로 못 잡는 template literal code(`sequence/participant-*-overflow`, `architecture/component-*-overflow`)는 직접 읽음. 타입별 상세 의미는 일부만 읽음 |
| R-20 | C-10 | 코드 읽음, 실행은 격자 입력을 만들지 않았다(코드 확인) |
| R-21 | C-15 `render-architecture.mjs:487-600`(컴포넌트 검사), `:608-628`(겹침), T-06 T-07 | overlap·out-of-bounds 실행 확인 |
| R-22 | C-11 `boundaryRect`(110-140), T-03 | 실행 확인 |
| R-23 | C-12 `autoViewBoxFor`(185-208), T-02 T-03 | 실행 확인(440×208, 470×228) |
| R-24 | C-13, `render-architecture.mjs:99,426` | 코드 확인. 제목 슬라이드 결과는 실행하지 않았다 |
| R-25 | C-15 `render-architecture.mjs:493,640-735` (`requiresNestedBoundaryMembership`) | 코드 확인 |
| R-26 | C-15 `render-architecture.mjs:769-800`(boundary-encloses-non-member), `:830-840`(route-out-of-bounds), `:904-925`(arrowhead-collision), `:963-975`(label-gap) | 코드 확인. 실행하지 않았다 |
| R-27 | C-18 396-405, C-19 869-886, T-03, `geometry.mjs:1830-1837` `authoredStraightRouteAttrs` | 실행 확인(zero-length 점 보존), 대각선 표지는 코드 확인 |
| R-28 | C-22 `defaultFromSide/ToSide`, `automaticPortSpread`, C-19 701-760, [rendering-architecture-routing.md](rendering-architecture-routing.md) R-04~R-07, C-06·C-17 | 코드 확인. 팬아웃 조건은 routing 스펙 R-07로 정정(실행으로 분기 결과가 바뀌는 입력은 못 만듦) |
| R-29 | C-18, [rendering-architecture-routing.md](rendering-architecture-routing.md) R-08~R-12, R-25, C-05 | 코드 확인 + 실행 확인(routing T-01~T-06). 이전 M-01의 helper 미독은 해소 |
| R-30 | C-19~C-21, [rendering-architecture-routing.md](rendering-architecture-routing.md) R-02, R-13~R-21, C-07~C-10 | 코드 확인 + 실행 확인(routing T-02, T-03, T-13). 스윕 상세는 routing 스펙이 읽음 |
| R-31 | C-22 `roundedPath`, C-16 `renderConnectionPath` 1057-1072, T-03 | 속성은 실행 확인 |
| R-32 | C-22 `labelPoint`, C-12 `connectionLabelBoxAt`, T-01(`<text x="220" y="100">`) | 실행 확인 |
| R-33 | C-23, `render-architecture.mjs:454-477` | 코드 확인 |
| R-34 | C-15 `render-architecture.mjs:954-1006` | 코드 확인 |
| R-35 | C-15, C-24, C-25, C-06 | 표의 "프로파일" 열은 코드 분기. 실행은 overlap·out-of-bounds만 |
| R-36 | C-16 1083-1176, C-36 | 루트 속성 실행 확인(`data-node-ui` 등), 나머지 코드 |
| R-37 | C-06 `resolveLegend`, C-16 `renderLegend`(1107-1134) | 코드 확인 |
| R-38 | C-17, 파일 전체 위에서 아래로 실행되는 모듈 최상위 코드 | 코드 확인 |
| R-40 | C-35, [rendering-workflow.md](rendering-workflow.md) R-01~R-27, C-01~C-35 | 코드 확인(구조) + 상세는 rendering-workflow(코드 확인·실행 확인) |
| R-41 | C-34, [rendering-other-types.md](rendering-other-types.md) R-01~R-06 | 코드 확인(앞부분, 재시도). T-17 viewBox 실행 확인. 후처리·라벨 세부는 other-types 스펙(그쪽 확인 한계 참조) |
| R-42 | C-27, T-17, [rendering-other-types.md](rendering-other-types.md) E·R-25~R-29 | 코드 확인 + 최소 입력 viewBox 실행 확인. 120px 미만 진단의 도달 불가는 other-types 실행(`sq`)으로 확인 |
| R-43 | C-28, [rendering-other-types.md](rendering-other-types.md) B·R-07~R-13 | 코드 확인(`render-lifecycle.mjs:216-232`로 `spineGap` 조건 재확인) |
| R-44 | C-29 C-30, `erd/grid.mjs` 전체, [rendering-other-types.md](rendering-other-types.md) C·D·R-14~R-24 | 코드 확인(`render-erd.mjs:1211`, `render-class.mjs:709`, `:408-431`로 자기 관계·버스 조건 재확인) |
| R-45 | C-31, T-16 | 실행 확인 |
| R-46 | C-32, T-17 | 실행 확인 |
| R-47 | C-33, T-17 | 실행 확인 |
| R-48 | T-05, `summary.txt` | 실행 확인 |
| T-01~T-17 | [demos.sh](../../../artifacts/archify/spec-demos/rendering/demos.sh)가 만든 [summary.txt](../../../artifacts/archify/spec-demos/rendering/summary.txt), 입력 `in/`, `in/min/` | 설치본 실행(출력 HTML은 용량 때문에 삭제하고 재생성 가능). 시각 검토는 하지 않았다(확인 한계) |

### 2.2 코드 읽는 순서 [선택]
`bin/archify.mjs` `commandRender`(4271) → `renderers/architecture/render-architecture.mjs` 위에서 아래로(모듈 최상위가 곧 실행 순서) → `shared/cli.mjs` `loadDiagram`/`writeDiagram` → `shared/utils.mjs` `applyTemplate` → `architecture/routing.mjs` `createRouter` 안 `routeVia` → `computePath` → `planRoutes`. 나머지 타입은 같은 뼈대(로드 → 측정 → 배치 → 검증 → `renderSvg` → `writeDiagram`)이고 workflow·dataflow만 컴파일러가 SVG를 반환한다.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙 없음. 원본 코드를 복사하지 않았다.

## 미결정

없음. 이전 목록의 처리: M-01(architecture 자동 라우터 helper·개선 스윕) → [rendering-architecture-routing.md](rendering-architecture-routing.md)(R-01~R-28, C-01~C-22), M-02(workflow 컴파일러) → [rendering-workflow.md](rendering-workflow.md)(R-01~R-27), M-03(dataflow·lifecycle·erd·class 선 라우팅 세부) → [rendering-other-types.md](rendering-other-types.md)(그쪽 문서 참조), M-04(`atomic-output.mjs` 내부)·M-05(SVG `data-*` 훅의 정의 일치) → [rendering-contracts.md](rendering-contracts.md)(R-04~R-21), M-06(시각 검토 없음) → 1.4 확인 한계로 이동. `status: ready`의 근거는 frontmatter 주석에 있고, 하위 스펙의 draft 여부는 이 문서의 status에 영향을 주지 않는다(이 문서는 공통 계층과 architecture 배치·경계·진단만 소유).
