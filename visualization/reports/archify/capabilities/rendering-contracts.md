---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/renderers/shared/cli.mjs
  - archify/renderers/shared/legend.mjs
  - archify/renderers/shared/geometry.mjs
  - archify/renderers/shared/node-card-style.mjs
  - archify/renderers/shared/atomic-output.mjs
  - archify/renderers/architecture/render-architecture.mjs
  - archify/renderers/workflow/workflow-compiler.mjs
  - archify/renderers/sequence/render-sequence.mjs
  - archify/renderers/dataflow/render-dataflow.mjs
  - archify/renderers/dataflow/dataflow-compiler.mjs
  - archify/renderers/lifecycle/render-lifecycle.mjs
  - archify/renderers/erd/render-erd.mjs
  - archify/renderers/class/render-class.mjs
  - archify/renderers/tree/render-tree.mjs
  - archify/renderers/timeline/render-timeline.mjs
  - archify/renderers/waterfall/render-waterfall.mjs
  - archify/scripts/check-render-output.mjs
  - archify/bin/archify.mjs
  - archify/bin/visual-check.mjs
  - archify/delta/architecture-delta.mjs
  - archify/explainer/diagrams.mjs
  - archify/schemas/common.schema.json
  - viewer/motion-governor.js
  - viewer/reader-layout.js
  - viewer/semantic-lens.js
  - viewer/export-cleanup.js
  - viewer/tree-branches.js
  - viewer/viewer.css
  - viewer/template.source.html
depends: [rendering.md]
status: ready            # 2026-11-02: 이 스펙 자체의 미결정 없음, 선행 스펙 ready
---

# 렌더링 계약 점검 (SVG `data-*` 훅의 쓰는 쪽·읽는 쪽, 품질 프로파일 비대칭, 출력 쓰기 두 경로)

> rendering.md의 미결정 M-05(렌더러가 SVG에 심는 `data-*` 훅과 메타를 누가 쓰고 누가 읽는지)와 M-04(`atomic-output.mjs`의 교체 방식과 중단 후 상태)를 원본 코드와 실행으로 닫고, viewer.md·verification-gates.md·delivery.md와 어긋나는 곳을 목록으로 만든 점검 스펙이다.

> **이 스펙 자체의 미결정: 없음.** 아래 어긋남(D-xx)은 기존 스펙의 서술 보정 사항이고 이 스펙의 구현 선택이 아니다. `status: draft`인 이유는 선행 rendering.md가 `draft`이기 때문이다. 확인 한계는 1.4 끝.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 타입별 렌더러가 SVG 문자열을 만들 때 루트 `<svg>`에 공통 속성(`svgRootAttrs`)과 타입별 속성을 붙이고, 노드·엣지·범례·프레임·경로에 `data-*` 훅을 붙인다. 읽는 쪽은 세 곳이다: HTML 안 뷰어(`viewer/*.js`·`viewer.css`, template.html에 인라인), 정적 검사(`check-render-output.mjs`)·브라우저 검사(`visual-check.mjs`), explainer·delta 같은 후속 도구. 렌더러 자신도 CSS 선택자로 일부 훅을 쓴다(R-04, 1.3 A).
2. `--quality`(환경 변수 `ARCHIFY_QUALITY_PROFILE`)와 `meta.quality_profile`은 루트 속성 두 개(`data-quality-profile`, `data-quality-gates`)로 기록되지만, SVG 본문을 만드는 렌더 단계의 게이트는 소비처마다 환경 변수를 보거나(workflow·dataflow·erd·class·공유 게이트) `meta`만 본다(architecture·sequence)(R-02, R-03).
3. `meta.animation`은 스키마가 `trace|none`을 받지만 렌더러는 읽지 않는다. `data-animation="trace"`는 항상 붙는다(R-01).
4. 단일 파일 쓰기(`writeDiagram` → `publishRegularFileBinding`)는 같은 폴더 임시 파일을 만들고 기존 파일을 `.archify-remove-<hex>/` 안 하드링크 백업으로 옮긴 뒤 공개 이름에 후보를 `link`한다. rename 덮어쓰기가 아니다(R-12, R-13).
5. `deliver`의 쌍 교체(`commitDeliveryPair`)는 같은 기본 연산(`backupPublicRegularFileBinding`, `quarantineRemoveRegularFileBinding`)을 쓰되 폴더 잠금·journal·staging 아래에서 두 파일을 **단계별로**(HTML·provenance 백업 둘 다 → 링크 둘 다) 처리한다(R-14~R-16). 잠금·journal·쌍 교체는 `atomic-output.mjs`가 아니라 `bin/archify.mjs`에 있다.
6. 미리 만든 잠금 파일은 `deliver`만 막고 `render`는 보지 않는다(R-17, R-18). 중단 시 사후 상태는 코드 추적으로 정리했다(1.3 F, R-19).

### 1.2 범위·통합 지점
- 제공: SVG 훅 전수 표(쓰는 쪽·값·읽는 쪽), 스펙 간 어긋남 목록, 품질 프로파일이 속성·본문에 반영되는 규칙, 출력 쓰기 두 경로의 차이와 중단 후 상태.
- 제외: 훅이 만들어지는 레이아웃 알고리즘(rendering.md), 뷰어 상호작용의 세부(viewer.md), 검사 항목의 임계값(verification-gates.md), 출력 경로 해석·provenance 형식(delivery.md). 프로세스 kill로 중단을 재현하지 않았다.
- 외부 의존: 설치본 `~/.claude/skills/archify`(레포 `archify/`와 `diff -rq` 차이 없음, 이번에 재확인), Node v26.10.0, macOS APFS. 레포 clone 안의 코드는 실행하지 않았다.
- 소유 상태·부작용: 없음(점검 스펙). 데모 산출물은 [spec-demos/rendering/contracts/](../../../artifacts/archify/spec-demos/rendering/contracts/)에 스크립트·TSV·텍스트만 있다.

### 1.3 인터페이스와 데이터 의미

**A. SVG 훅 전수 표**
"쓰기" = 렌더러 코드(`archify/renderers/`), "읽기" = `grep`으로 찾은 참조처(분기 하나하나는 읽지 않음). V=뷰어(`viewer/*`), C=`check-render-output.mjs`, VC=`visual-check.mjs`, X=explainer(`explainer/diagrams.mjs`), Δ=`delta/architecture-delta.mjs`. 표의 "없음"은 위 목록에서 찾지 못했다는 뜻이다.

*루트 `<svg>` 속성*

| 훅 | 쓰는 곳 | 값 집합 | 읽는 곳 |
|---|---|---|---|
| `data-animation` | `svgRootAttrs` (cli.mjs:363), 10개 타입 전부 | `trace` 하나. `meta.animation`(`trace\|none`)은 무시 | V: `motion-governor.js:13`(Live/Still 가능 여부), `export.js:789`(WebM 가능 여부), `viewer.css:674-698`. C 없음 |
| `data-preset` | `svgRootAttrs` (364) | `classic\|signal-flow\|blueprint\|editorial`, 기본 `classic`. `<html data-preset>`에도 같은 값 | V·렌더러 CSS(`node-card-style.mjs:10-12`), X |
| `data-engineering-profile` | `svgRootAttrs` (365-367), `meta.engineering_profile`가 있을 때만 | `meta` 값 그대로 | `bin/archify.mjs:4396`(deliver 영수증의 engineering). 뷰어 없음 |
| `data-quality-profile` | `svgRootAttrs` (368-371) | `standard\|showcase`. 요청값이 `showcase`가 아니면 모두 `standard` | C `:122`(게이트 심각도·임계), X `:489`(SVG 찾는 정규식에만 사용) |
| `data-quality-gates` | `svgRootAttrs` (370) | `advisory` 또는 없음. 요청값(`--quality`/환경/`meta`)이 하나도 없을 때만 `advisory` | C `:124`(`container-border-run`의 오류/경고) |
| `data-layout-contract` | workflow-compiler.mjs:5487 | `readable-v2`(`schema_version` 2만). v1은 없음 | C `:123`(교차·회랑 검사 방식) |
| `data-motion-choreography` | sequence 1066, dataflow 1552, lifecycle 1101, timeline 497, waterfall 346 | `sequence`·`stream`·`walk`·`sweep`·`replay`(타입 순서). architecture·workflow·erd·class·tree는 **없음** | V: `motion-governor.js:36`(없으면 `relay`) |
| `data-reader-fit` | architecture 1143-1144, workflow 5484-5486, sequence 1065, dataflow 1551, lifecycle 1101, erd 1511, class 1030, tree 498, timeline 497, waterfall 346 | `intrinsic-height`(architecture 자동 viewBox, lifecycle·timeline 항상, erd·class·tree·dataflow는 `meta.viewBox` 없을 때), `width-first`(waterfall 항상, sequence는 `meta.viewBox` 없을 때, workflow는 v2·`meta.viewBox` 없음·세로로 쌓이고 레인 높이>104 또는 고정 폭 넘침 예측일 때), `authored-height`(architecture + 저자 `meta.viewBox`) | V: `reader-layout.js:12-16`(`width-first`·`intrinsic-height`만 해석, `authored-height`는 무시), C·VC·`shared/desktop-readability.mjs:108` |
| `data-reader-min-text` | architecture·tree·erd·class(모두 `meta.viewBox` 없을 때), timeline·waterfall(항상) | `7.5` | V `reader-layout.js:32`, C `:1221` |
| `data-reader-primary-text` | architecture(`meta.viewBox` 없을 때)만 | `14` | V `reader-layout.js:36`, C `:169,906` |
| `data-diagram-type` | architecture + 저자 `meta.viewBox`일 때만 | `architecture` | C `:136,169`, VC `:1851,1969` |
| `data-sequence-column-fit` | sequence | `spread\|fixed` | V `reader-layout.js:14`, C `:959,1039` |
| 타입 표지 | `data-node-ui=""`(architecture·workflow), `data-tree-ui=""`+`data-tree-direction`(`down\|right`), `data-erd-ui="cards"`, `data-class-ui=""`, `data-timeline-ui=""`, `data-waterfall-ui=""`+`data-waterfall-unit`, `data-lifecycle-layout="main-path-v3"` | 고정 문자열 | `data-tree-ui`만 V(`tree-branches.js:10`). 나머지는 SVG 안 `<style>` 선택자에서만 쓰이고 JS·검사 참조는 없음(`data-lifecycle-layout`은 참조처 없음) |

*노드·엣지*

| 훅 | 쓰는 곳 | 값 | 읽는 곳 |
|---|---|---|---|
| `data-node-id`, `data-node-label` | `focusNodeAttrs` (cli.mjs:392-412) | 스키마 id, 표시 라벨 | V 여러 파일, C, VC, X, Δ |
| `data-node-kind/sublabel/tag/context/brand` | 같은 함수, 값이 공백이 아닐 때만 | 타입별 문자열 | V(`focus.js`·`node-finder.js`·`node-outline.js`·`semantic-lens.js`·`semantic-radar.js`) |
| `data-node-brand-id/status/source` | 같은 함수 | 브랜드 메타 | **읽는 곳 없음** |
| `data-edge-from/to` | `focusEdgeAttrs` (423-429) | 노드 id | V 여러 파일, C, VC, X |
| `data-edge-label`, `data-edge-key`, `data-edge-id` | 같은 함수, 있을 때만 | 라벨, 인덱스, 관계 id | V(`focus.js`·`route-probe.js`·`guided-views.js`: key 없으면 `from\0to\0label`, id는 같은 key를 가진 조각을 구분), C, X |
| `data-animate` + `--step` | `animateAttr` (384-388) | `node\|edge`, step 0..12 | V(`motion-governor.js`·`focus.js` 등), `viewer.css` |
| `data-semantic-sigil` | `renderSemanticSigil` (utils.mjs:109) | 정규화된 심볼 이름 | C |
| `data-boundary-label` | architecture 경계 제목 `<text>` | `""` | V `reader-layout.js:89`, C, VC |
| `data-edge-role` | workflow v2만(workflow-compiler.mjs:5448) | `main\|branch\|async\|return\|error` 또는 `""` | C `:522`에서 읽어 객체에 담지만 **이후 사용처 없음** |

*범례·세부 수준*

| 훅 | 쓰는 곳 | 값 | 읽는 곳 |
|---|---|---|---|
| `data-legend`, `data-legend-bridge` | `renderLegend` (legend.mjs:210) | `""`. 상호작용 항목이 있으면 `data-legend-bridge=""`도 | V `semantic-lens.js:18`, `export-cleanup.js` |
| `data-legend-semantic-kind`, `-x`, `-baseline`, `-width` | legend.mjs:220 | 종류 id, 좌표·폭 | erd·class의 SVG CSS(`:has(...)`), V `semantic-lens.js` |
| `data-legend-kind`, `data-legend-label` | legend.mjs:218, 상호작용 항목만 | 종류 id, 문구 | V `semantic-lens.js:121`, `export-cleanup.js`, `viewer.css` |
| `data-detail` | waterfall을 뺀 9개 타입 | `context\|fine`(lifecycle 전이는 라벨이 있으면 `context`, 없으면 `fine`) | V `viewer.css:4082-4088`(map이면 둘 다 숨김, read면 `fine` 숨김), `reader-layout.js:89-95`, `export-cleanup.js:137`, C, VC |
| `data-detail-anchor` | lifecycle·dataflow·architecture·sequence·workflow | `""` | V `viewer.css:4077-4120`, `export-cleanup.js:137` |

*구조·합성(composition) 훅*

| 훅 | 쓰는 곳 | 값 | 읽는 곳 |
|---|---|---|---|
| `data-graph-role` | `automatic-crossover`·`automatic-crossover-underlay`: architecture·dataflow·lifecycle. `structural-frame`: architecture·dataflow·sequence·workflow. `structural-frame-label`·`-label-mask`: architecture(마스크 CSS는 `node-card-style.mjs:15`). `message-note-background`·`segment-label`: sequence | 좌변의 값 | V `viewer.css`·`export.js:400-408`, C `:86,927`, Δ `:456-457` |
| `data-composition-points` | architecture·workflow·sequence·dataflow·lifecycle·erd·class·tree의 관계 경로. **timeline·waterfall은 없음** | `"x,y;x,y…"` | C `:500`, Δ `:567` |
| `data-composition-crossover` | architecture·dataflow·lifecycle (자동 라우트) | `halo` | C `:484` |
| `data-composition-independent` | architecture·lifecycle | `true` | C `:514`(halo 검증을 통과한 경로만 `independentPorts`) |
| `data-composition-junction` | lifecycle | 괄호(bracket) 키 | C `:519` |
| `data-composition-routing` | workflow v2 자동 경로 | `workflow-v2-auto` | C `:518` |
| `data-composition-route` | `authoredStraightRouteAttrs` (geometry.mjs:1830-1837): `route:"straight"`이고 `via` 없음·점 2개·**대각선**일 때만 | `straight` | C `:509` |
| `data-composition-frame-kind/-id/-label` | architecture(`region\|security-group\|boundary`), dataflow(`stage`), sequence(`segment`), workflow(`lane\|exception-lane\|group`). `-label`은 architecture만 | 종류, 순번 문자열(`lane-0`, `group-1`…), 라벨 | C `:562,870,1052`, Δ `:456` |
| `data-composition-edge-from/-to/-id` | sequence 메시지 | 참가자 id, 메시지 id | C `:527-529`(`data-edge-*`가 없을 때 대체) |

*메타·script*: `<meta name="archify-reader-contract" content="declared-wide-v1">`은 **렌더러가 아니라 템플릿**(`viewer/template.source.html:7` → `archify/assets/template.html:7`)이 쓴다. 읽는 곳은 C `:1213`(정확히 1개이고 값이 같을 때만 "선언된 넓은 읽기" 예산)뿐이며 뷰어는 읽지 않는다. `<script id="archify-i18n-data">`·`<script id="archify-source-evidence-data">`는 rendering.md 1.3 B와 같다.

**B. 품질 프로파일 소비처**

| 소비처 | 보는 값 | 코드 |
|---|---|---|
| SVG 루트 `data-quality-profile/-gates` | 환경(`--quality`) → `meta.quality_profile`. workflow만 컴파일러가 환경을 먼저 합친 값(`resolvedQualityProfile`)을 `svgRootAttrs`의 두 번째 인자로 넘기고, 나머지 타입은 `svgRootAttrs`가 환경을 직접 읽는다. 결과는 같다 | cli.mjs:368-371, workflow-compiler.mjs:1381,5488 |
| 공유 게이트(`geometry.mjs`의 `clean*Problems`) | `profileIsAuthoritative`가 거짓이면 환경 → 인자 `profile`, 참이면 인자만. workflow는 참(인자가 이미 환경을 포함), 나머지는 거짓 | geometry.mjs:1302-1306, workflow-compiler.mjs:2877 등 |
| workflow·dataflow 컴파일러 | 환경 → `meta` (`process.env.ARCHIFY_QUALITY_PROFILE \|\| meta.quality_profile`) | render-workflow.mjs:18, render-dataflow.mjs:17 |
| erd·class | 공유 게이트에 `meta.quality_profile`을 넘기고 게이트가 환경을 우선 적용 | render-erd.mjs:1299-1347, render-class.mjs:777 |
| **architecture 본문** | 경계 제목 조합 켜짐(`Boolean(meta.quality_profile)`), 라벨 재배치·`route-out-of-bounds`·`boundary-encloses-non-member`·`label-gap`·`excessive-route-detour`: **`meta.quality_profile`만**. 예외로 `arrowhead-collision`은 환경 → `meta` | render-architecture.mjs:99,457,769,830,904,963 |
| **sequence 본문** | 메시지 라벨 글자 크기·폭 단위(showcase 6.6 / 그 외 5.2, 글자 11/9), `readableMessages`, 범례 높이 오류: **`meta.quality_profile`만** | render-sequence.mjs:67,117,846,919 |
| lifecycle·tree·timeline·waterfall | 본문에서 보지 않음(루트 속성만) | — |
| 정적 검사 | SVG 루트 `data-quality-profile`(환경 변수는 보지 않음), `data-quality-gates` | check-render-output.mjs:122-124 |

**C. 어긋남 목록 (기존 스펙 ↔ 코드)**

| D-ID | 어긋남 | 어느 스펙 |
|---|---|---|
| D-01 | rendering.md R-15는 "환경 우선"이라 쓰고 `meta`만 보는 항목을 architecture에 한정해 나열한다. sequence의 `meta`만 보는 소비처(라벨 크기·`readableMessages`·범례 오류)가 빠져 있고, R-42는 "showcase 6.6, standard 5.2"를 프로파일 출처 없이 쓴다 | rendering R-15, R-42 |
| D-02 | rendering.md R-15의 "`container-border-run`은 유효 프로파일이 있을 때만 검사"는 렌더러 쪽(`cleanBorderRunProblems`는 프로파일이 없으면 `[]`, 있으면 항상 `error`)만 맞다. 정적 검사는 항상 계산하고 `data-quality-gates="advisory"`면 경고, 아니면 오류다(verification-gates.md R-12와 같다). 두 문서가 같은 게이트를 다르게 요약한다 | rendering R-15 |
| D-03 | `meta.animation: "none"`이 `data-animation`을 바꾸는지 viewer.md가 "확인하지 않았다(rendering 소관)"로 남겼고 rendering.md는 `meta.animation`을 언급하지 않는다. 답은 "바꾸지 않는다, 입력은 허용되고 무효"다. `archify/schemas/README.md:27`은 아직 "opt-in"이라 쓴다(문서가 낡음) | viewer 확인 한계, rendering 1.3 |
| D-04 | rendering.md 1.3 E·R-16은 "모든 타입 SVG 공통 훅"으로 노드·엣지·범례만 적는다. `data-motion-choreography`(5개 타입만, 값이 타입별), `data-reader-*`(타입·`meta.viewBox`별), `data-detail*`, `data-graph-role`, `data-composition-*`는 어디에도 타입별 표가 없다. R-31의 "모든 경로에 `data-composition-points`"는 timeline·waterfall에 없고(관계 경로가 없음), 교차 헤일로(`data-composition-crossover`·`-independent`)는 architecture·dataflow·lifecycle만 만든다 | rendering R-16, R-31 |
| D-05 | viewer.md의 "렌더러가 뷰어에 약속하는 DOM 속성" 표에 뷰어가 실제로 읽는 `data-detail`·`data-detail-anchor`(map/read에서 숨김), `data-reader-min-text`·`data-reader-primary-text`, `data-legend*`(Lens·내보내기 정화), `data-graph-role`(교차 밑선), `data-edge-id`(조각 구분), `data-animate`가 없다. `data-reader-fit`은 값 3개 중 2개만 뷰어가 해석한다(`authored-height`는 검사 전용) | viewer 표 |
| D-06 | verification-gates.md R-20은 `data-diagram-type`을 "R-18의 architecture 예외와 R-21의 증거용"이라 하는데 렌더러는 architecture + 저자 `meta.viewBox`일 때만 이 속성을 쓴다(자동 viewBox인 architecture는 `data-reader-primary-text="14"`가 같은 역할). `data-edge-role`은 검사가 읽지만 쓰이지 않는다는 점도 어느 문서에 없다 | verification-gates R-20, R-21 |
| D-07 | verification-gates.md R-10이 쓰는 "halo 검증 통과 + `data-composition-independent`"는 architecture·lifecycle만 만들 수 있다(dataflow는 halo만, workflow는 `readable-v2`·`workflow-v2-auto` 경로) | verification-gates R-10, R-11 |
| D-08 | rendering.md R-27은 "`route`가 `straight`면 중간점 없음"이라고만 하고, `data-composition-route="straight"`가 대각선 직선일 때만 붙는 점(verification-gates R-09 예외의 출처)을 쓰지 않는다 | rendering R-27, R-31 |
| D-09 | rendering.md R-14 "교체 방식(원자 rename 여부)은 추론"과 M-04. 코드로 확정: rename 덮어쓰기가 아니라 R-13의 순서다. 같은 기본 연산을 delivery가 쓴다 | rendering R-14, M-04 |
| D-10 | delivery.md R-16은 "대상마다 HTML → provenance 순으로 ①~④"라 쓰지만 코드는 **단계별**이다: ① 두 대상 검증·후보 바인딩 → ② HTML 백업·공개 이름 제거, provenance 백업·공개 이름 제거 → ③ HTML `link`, provenance `link` → ④ 두 대상 링크 2개 확인 → 두 후보 제거 → 링크 1개 확인 → journal 삭제. 따라서 ②와 ③ 사이에 **두 공개 이름이 모두 없는** 구간이 있다(R-14) | delivery R-16, R-20 |
| D-11 | delivery.md T-17(잠금 `lock-stale` 등)은 "미실행, 코드 도출"이지만 이번에 실행으로 확인했다(R-17). 값도 일치 | delivery T-17, R-18 |

**D. 출력 쓰기 경로 비교**

| 항목 | 단일 파일(`writeDiagram`, finalize 영수증·preview·explainer도 같은 기본 연산) | `deliver` 쌍 교체(`commitDeliveryPair`) | deliver의 journal·실패 표지(`writeDeliveryProvenance`) |
|---|---|---|---|
| 위치 | cli.mjs:234-303 → atomic-output.mjs:1120-1329 | bin/archify.mjs:3236-3624 | bin/archify.mjs:1009-1200 |
| 대상 수 | 1 | 2(HTML, provenance), 단계별 | 1 |
| 잠금·journal | 없음 | 폴더 잠금 `.archify-delivery-lock.json`(+레거시), journal `<stem>.delivery-pending.json` | 같은 잠금 소유 아래 호출 |
| 후보 위치 | 같은 폴더 `.archify-render-<pid>-<time36>-<seq>.tmp` | staging `.archify-delivery-XXXXXX/` 안(렌더러가 거기에 씀) | `.archify-provenance-*` staging |
| 백업 위치 | `.archify-remove-<32hex>/previous` + `publication-recovery-v1.json`(0600, fsync) | staging의 `.previous-output`·`.previous-provenance`, **복구 기록 파일 없음** | staging의 `.previous-journal` |
| 공개 이름 제거 | `quarantineRemoveRegularFileBinding`: `rename`으로 `.archify-remove-<hex>/` 안으로 옮기고 inode·모드·해시 확인 뒤 `unlink` | 같은 함수 | 같은 함수 |
| 새 이름 | `link(후보, 공개 이름)`. `EEXIST`면 `target-created-during-commit` | 같은 `link`. `EEXIST`면 `target-claimed-during-publish` | 같은 `link` |
| 실패 시 | 함수 안 `rollback`이 새 이름 제거 → 백업 복원 → 기록 정리 | 두 단계 되돌리기(새 링크 전부 제거 → 백업 전부 복원), 못 하면 `commit-recovery-required` | 별도 구현 |
| 복구 도구 | `bin/recover-output.mjs`가 `publication-recovery-v1.json`을 읽는다 | 없음(사람이 staging 백업을 `link`) | 없음 |

**E. 단일 파일 쓰기(`writeDiagram`) 순서**: `applyTemplate` → `mkdir -p` → `captureAtomicOutput`(요청 항목·쓰기 슬롯(부모 dev/inode·이름)·대상(없음/일반 파일 1링크의 dev·inode·모드)) → `verifyAtomicOutput` → 임시 후보 작성(`O_EXCL\|O_NOFOLLOW`, 기존 대상 모드 유지) → 입력 별칭 재검사 → `captureRegularFileBinding`(후보의 sha256·크기·inode·모드를 열린 디스크립터에 묶음) → `verifyAtomicOutput` → `publishRegularFileBinding`(R-13) → 후보 바인딩 해제 → stdout에 `outPath`.

**F. 중단·실패 후 사후 상태(코드 추적, kill 시뮬레이션 안 함)**

| 중단 지점 | 단일 파일 경로 | deliver 쌍 교체 |
|---|---|---|
| 후보 작성 전·중 | 공개 파일 그대로. `.archify-render-*.tmp`가 남을 수 있음(정상 종료·예외 종료에서는 `finally`가 소유 확인 뒤 삭제) | 잠금·journal·staging만 남고(렌더·검사 단계) 공개 HTML·provenance는 그대로. journal 때문에 `check`는 막힘 |
| 복구 기록·백업 링크 직후 | 공개 파일이 그대로이고 이름이 하나 더(링크 수 2). `.archify-remove-<hex>/`에 기록 파일 | 해당 없음(같은 단계가 백업 링크 직후) |
| 공개 이름 `rename`~`unlink` 사이 | 공개 이름 **없음**. 이전 내용은 `.archify-remove-<hex>/` 안 두 이름(`previous`와 옮겨진 파일) | HTML만 이 상태, provenance는 그대로 |
| 백업·제거 완료, 후보 `link` 전 | 공개 이름 **없음**, 이전 내용은 `.archify-remove-<hex>/previous`에만(`recover-output.mjs` 대상) | HTML 백업 후 provenance 백업이 끝나면 **HTML·provenance 둘 다 없음**, 이전 내용은 staging `.previous-*`에 하나씩. 복구는 사람이 한다 |
| 후보 `link` 직후 | 새 파일이 공개 이름에 있고 후보 임시 파일도 같은 inode(링크 수 2). 백업 남아 있음 | HTML만 새 파일이고 provenance 공개 이름은 아직 없음 → 둘 다 링크되면 링크 수 2 |
| 후보·백업 정리 중 | 새 파일이 공개. `.archify-remove-*`·`.tmp` 잔재만(`committed-with-warning`이면 성공으로 처리) | 새 쌍이 공개이고 journal이 아직 있어 `check`는 막힘. journal 삭제 뒤에야 풀림 |
| 예외(중단 아님) | `rollback`: 새 이름 제거 → 백업을 `link`로 복원. 복원이 안 되면 결과에 `recoveryFile`을 싣는다 | 새 링크 전부 제거 → 백업 전부 복원 → `delivery/commit`. 복원 실패·소유권 상실이면 `commit-recovery-required`(잠금·journal·staging 유지) |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 10개 타입 어느 것이든, `meta.animation`이 없음/`trace`/`none` | 루트에 `data-animation="trace"`가 항상 붙고 SVG 본문이 바이트 단위로 같다. `data-animate` 개수도 같다 | 실행 확인(10타입 × 3조건, `01-matrix.tsv`: SVG 해시 동일) / 코드 확인(`animateAttr`는 `meta`를 받지만 쓰지 않음, `svgRootAttrs`에 `meta.animation` 참조 없음) |
| R-02 | `--quality`(환경)·`meta.quality_profile` 9개 조합 | `data-quality-profile` = 환경 → `meta`, `showcase`가 아니면 `standard`. `data-quality-gates="advisory"`는 둘 다 없을 때만(명시적 `standard`도 advisory 아님). 충돌 시 환경이 이긴다. CLI `--quality foo`는 종료 2(`Unknown quality profile "foo". Expected standard or showcase.`). 렌더러 직접 실행에서 환경 `foo`는 `standard`+advisory 없음 | 실행 확인(10타입 90건, 잘못된 값 2건) |
| R-03 | 환경과 `meta`가 다른 입력 | architecture·sequence 본문은 `meta.quality_profile`만 본다. `--quality showcase`만 주면 루트는 showcase인데 본문은 standard 경로다(architecture 경계 라벨 위치가 `meta` showcase 때와 다름, sequence 라벨 글자 9 vs 11). 환경 `standard` + `meta` showcase면 sequence 본문은 showcase, 루트는 standard. workflow·dataflow·erd·class는 환경 → `meta`라 본문이 환경을 따른다. 정적 검사는 루트 속성만 보므로 이 불일치를 검사하지 못한다 | 실행 확인(architecture 2종·sequence 비교, 90건 중 해시 비교) / 코드 확인(소비처 전수, B표) |
| R-04 | 루트·노드·엣지·범례·구조 훅 | 1.3 A 표대로 쓰고 읽는다. 읽는 곳이 없는 훅이 있다(`data-node-brand-id/status/source`, `data-lifecycle-layout`, `data-erd-ui` 등 타입 표지는 CSS 전용, `data-edge-role`은 읽기만 하고 미사용) | 코드 확인(grep 전수: `renderers/`, `viewer/`, `scripts/`, `bin/`, `explainer/`, `delta/`) / 실행 확인(루트 속성 90건) |
| R-05 | `data-motion-choreography` | sequence→`sequence`, dataflow→`stream`, lifecycle→`walk`, timeline→`sweep`, waterfall→`replay`. architecture·workflow·erd·class·tree는 속성이 없고 뷰어가 `relay`로 본다 | 실행 확인(10타입) / 코드 확인(뷰어 기본값) |
| R-06 | `data-reader-fit`의 값 | 1.3 A 조건대로. 예제 입력에서 관찰: architecture·lifecycle·erd·class·tree·timeline `intrinsic-height`, waterfall `width-first`, workflow v2 예제·sequence·dataflow 예제는 속성 없음(앞 둘은 조건 불충족, 뒤 둘은 예제가 `meta.viewBox`를 가짐). `authored-height`는 뷰어가 해석하지 않는다 | 실행 확인(예제 10건) / 코드 확인(조건) |
| R-07 | `data-detail`·`data-detail-anchor` | 값은 `context\|fine`(anchor는 빈 값). 뷰어 CSS가 세부 수준 `map`에서 둘 다, `read`에서 `fine`을 숨기고, 포커스·호버·Reach 등 강조 중에는 숨김을 해제한다. 내보내기 정화가 두 속성을 제거한다. 검사 쪽은 `fine`을 글자 가독성 대상에서 뺀다 | 코드 확인(viewer.css:4076-4120, export-cleanup.js:137, reader-layout.js:89-95) |
| R-08 | 관계 경로의 합성 훅 | `data-composition-points`는 관계 경로가 있는 8개 타입이 쓴다. 헤일로·독립 포트는 architecture·dataflow·lifecycle(독립은 architecture·lifecycle)만, `workflow-v2-auto`는 workflow v2만, 프레임 종류는 1.3 A대로. 읽는 쪽은 정적 검사(와 delta의 프레임·점)뿐이고 뷰어는 읽지 않는다 | 코드 확인 |
| R-09 | 메타 `archify-reader-contract` | 템플릿 고정값 `declared-wide-v1` 하나. 렌더러는 바꾸지 않는다. 정적 검사만 읽는다 | 코드 확인 |
| R-10 | `delta`·`explainer`가 SVG 문자열을 정규식으로 파싱 | delta는 `<rect data-graph-role="structural-frame" … data-composition-frame-kind … data-composition-frame-label …/>`처럼 **속성 순서**에 의존한다(렌더러 순서 `graph-role, frame-kind, frame-id, frame-label`와 일치). 속성 순서 변경은 delta를 깨는 숨은 계약이다. explainer는 `data-node-id`, `data-edge-id\|key\|from\|to`, `data-edge-label`만 쓴다 | 코드 확인 |
| R-11 | `render`로 기존 일반 파일(링크 1개)에 쓸 때 | 같은 폴더에 후보를 쓰고(R-12) 교체 후 `.archify-render-*`·`.archify-remove-*` 잔재가 없다. 새 파일이 다른 inode다(rename 덮어쓰기와 관찰상 같음). 대상이 하드링크면 `output/target-hardlinked`로 거부, 기존 내용 유지 | 실행 확인(`04-render-replace.txt`) |
| R-12 | `writeDiagram` | 1.3 E 순서. 후보 임시 파일은 `O_EXCL\|O_NOFOLLOW`로 만들어 기존 대상 모드를 `fchmod`로 맞추고, 후보 바인딩은 sha256·크기·inode·모드를 묶는다. 대상이 요청 후 바뀌면 `output/target-changed`, 일반 파일이 아니면 `target-not-regular-file`, 링크 2개 이상이면 `target-hardlinked`, 그 밖에는 `target-indeterminate` | 코드 확인 / 실행 확인(디렉터리·하드링크 거부는 rendering T-10, `04`) |
| R-13 | `publishRegularFileBinding`(대상이 일반 파일) | ① 대상 스냅샷·후보 바인딩 재검증. ② `.archify-remove-<32hex>/`(0700) 생성, 안에 `publication-recovery-v1.json`(백업 sha256·크기·모드·dev/inode, 대상 경로·부모 dev/inode)을 `O_EXCL`로 쓰고 fsync. ③ `backupPublicRegularFileBinding`: 공개 파일을 `<dir>/previous`로 **`link`**(링크 2개 확인) → 공개 이름을 같은 폴더의 새 `.archify-remove-*`로 **`rename`**하고 inode·모드·해시가 묶음과 같을 때만 `unlink`(다르면 `link`로 되돌림) → `previous` 링크 1개 확인. ④ `link(후보, 공개 이름)`(`EEXIST` → 롤백). ⑤ 두 이름 링크 2개 확인. ⑥ 후보 이름을 같은 방식으로 격리 제거하고 공개 이름 링크 1개 확인. ⑦ 백업·기록 제거. 대상이 없으면 ②③⑦ 없이 `link`만. 주석이 "crash-atomic 아님: 이전 이름 제거와 후보 링크 사이 공개 이름이 없다"고 명시 | 코드 확인(atomic-output.mjs:1120-1329, 911-1000, 755-904) / 실행 확인(결과 상태만, R-11) |
| R-14 | `commitDeliveryPair` 성공 경로 | 순서(전부 매 변경 직전 잠금·journal 소유권 재확인): (1) HTML·provenance 각각 스냅샷 검증, 후보를 대상 모드로 `chmod`, 후보 바인딩, 이전 파일 바인딩. (2) HTML 백업(→ staging `.previous-output`, 공개 이름 제거), provenance 백업(→ `.previous-provenance`). (3) HTML 후보 `link`, provenance 후보 `link`. (4) 두 공개 이름 링크 2개 확인. (5) 두 후보 이름 격리 제거. (6) 두 공개 이름 링크 1개 확인. (7) journal을 격리 제거. 이전 파일 백업은 staging 정리 때까지 유지. (2) 끝~(3) 사이에 두 공개 이름이 모두 없고, (3)의 HTML~provenance 사이에 HTML만 새 파일이다 | 코드 확인(archify.mjs:3236-3452) |
| R-15 | `commitDeliveryPair` 도중 예외 | (a) 소유권 상실이면 즉시 중단, `recoveryDetails`(staging 경로·백업 목록)를 싣고 되돌리지 않음. (b) 아니면 역순으로 새로 링크된 공개 이름을 격리 제거(링크 수 기대 2 또는 1) → 백업된 항목을 역순으로 복원(`link` → 두 이름 링크 2개 확인 → 백업 이름 제거 → 링크 1개 확인; 다른 파일이 선점했으면 중단). 전부 되돌리면 "previous files were restored", 일부라도 못 하면 `rollbackErrors`·`recoverableBackups`를 싣고 "could not be fully restored"(R-13~R-17은 delivery.md가 소유) | 코드 확인(archify.mjs:3453-3614), 실행하지 않음 |
| R-16 | 잠금·journal 소유 | 폴더 잠금은 `deliveryLockPath`(출력의 실제 부모 폴더 + `.archify-delivery-lock.json`)에 `open('wx', 0o600)`으로 만들고 `{schemaVersion:1, receiptId, pid}\n`을 쓴 뒤 닫는다. 레거시 `<stem>.delivery-lock.json`도 같이 만든다(이미 있으면 `rejectExistingDeliveryLock`). 해제는 소유 확인 후 격리 제거. journal은 `beginDeliveryAttempt`가 `writeDeliveryProvenance`(자체 staging `.archify-provenance-*`, 같은 백업→제거→`link` 연산)로 쓴다. 둘 다 `atomic-output.mjs`가 아니라 `bin/archify.mjs`(520-757, 985-1200)에 있고 `atomic-output.mjs`는 바인딩·격리 제거·백업·publish 기본 연산만 제공한다 | 코드 확인 |
| R-17 | 출력 폴더에 미리 만든 잠금 + `deliver` | 사전 산출물이 없든 있든: 유효 v1(UUID v4, 죽은 pid) → `delivery/lock-stale`, 산 pid → `delivery/concurrent-attempt`, JSON 아님·빈 파일·디렉터리 → `delivery/lock-invalid`, 레거시 `a.delivery-lock.json`(죽은 pid) → `delivery/lock-stale`. 모두 종료 1, `stage:"prepare"`, `provenance` 필드 없음. 잠금 파일은 지우지 않고 journal·실패 표지·staging을 만들지 않으며 기존 HTML·provenance 바이트는 그대로(해시 일치) | 실행 확인(`03-lock.txt`, 12건) |
| R-18 | 같은 폴더에서 잠금이 있는 채로 `render` | 잠금을 보지 않고 성공(종료 0), 임시·격리 잔재 없음. `render`는 잠금·journal 계약 바깥이다 | 실행 확인(`03-lock.txt`, `04`) |
| R-19 | 중단 후 사후 상태 | 1.3 F 표. 단일 파일 경로는 중단돼도 이전 내용이 `.archify-remove-<hex>/`(링크 기록 있음)에 남고 복구 도구가 있다. deliver는 잠금·journal이 남아 `check`를 막고, 쌍 교체 중이면 staging 백업을 사람이 `link`한다 | 코드 확인(중단은 시뮬레이션하지 않음) |
| R-20 | `writeDiagram`이 `publishRegularFileBinding` 결과를 처리 | 상태가 `committed`/`committed-with-warning`이면 성공(경고의 `cleanupState`·`recoveryFile`은 버려짐). 그 밖은 `throwAtomicOutputFailure`가 `reason.code`만 보고 4개 코드로 접는다: `different`→`target-changed`, 일반 파일 아님→`target-not-regular-file`, 하드링크→`target-hardlinked`, 나머지(복원 실패 등 `recovery-required` 포함)→`target-indeterminate`("could not be determined safely"). 결과의 `recoveryDirectory`·`recoveryFile`은 진단 evidence에 들어가지 않는다 | 코드 확인(cli.mjs:133-165,276-284), 실행하지 않음 |
| R-21 | 같은 이름을 쓰는 서로 다른 프로세스(잠금 없는 단일 파일 경로) | 보호는 스냅샷 재검증과 `link`의 `EEXIST`뿐이다. 대상 상태가 바뀌었음을 `verify`가 보면 `target-changed`, `link` 시점에 남이 만들었으면 롤백 | 코드 확인 |

- 불변식: (1) 일반 파일을 공개 이름에서 지울 때는 항상 격리 폴더 `rename` 후 열린 바인딩과 inode·모드·해시를 확인한 뒤에만 `unlink`한다(다르면 `link`로 복원하거나 `recovery-required`). (2) 새 공개 이름은 항상 `link`로 만든다(덮어쓰기 없음). 전제: 같은 파일시스템, 대상이 하드링크가 아님.
- 미결정: 없음.
- 확인 한계: ① 훅의 "읽는 곳"은 `grep` 수준이다(각 분기의 의미는 R-07 등 일부만 읽음). ② 뷰어 훅 값에 대한 동작(map/read/full 표시)은 브라우저에서 확인하지 않았다. ③ `data-node-kind` 등의 타입별 값 집합은 렌더러가 넘기는 문자열이고 전수 나열하지 않았다. ④ 프로세스 kill·경쟁·`rename`/`link` 주입 실패는 실행하지 않았다(F표, R-15, R-19, R-20은 코드 추적). ⑤ Windows·대소문자 구분 FS·SMB 경로는 코드 주석만 읽었다. ⑥ 원본 테스트는 `test/animation.test.mjs` 앞 80줄만 열었다(R-01의 보조 근거, 실행 확인 아님).

### 1.5 필수 코드 참조
Apache-2.0(overview 1절).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `archify/renderers/shared/cli.mjs:361-372,384-429` `svgRootAttrs`,`animateAttr`,`focusNodeAttrs`,`focusEdgeAttrs` | 루트 속성 결정, 노드·엣지 훅 | R-01, R-02, R-04 |
| C-02 | `archify/renderers/shared/geometry.mjs:962-1000,1302-1306,1830-1837` `cleanBorderRunProblems`,`qualityProfileForGate`,`authoredStraightRouteAttrs` | 환경·인자 우선순위, 대각선 직선 표지 | R-03, R-08 |
| C-03 | `archify/renderers/shared/atomic-output.mjs:1120-1329` `publishRegularFileBinding` | 단일 파일 publish 순서와 롤백 | R-13 |
| C-04 | `archify/renderers/shared/atomic-output.mjs:755-904,911-1000` `quarantineRemoveRegularFileBinding`,`backupPublicRegularFileBinding` | 격리 제거, 하드링크 백업 | R-13, R-14 |
| C-05 | `archify/renderers/shared/atomic-output.mjs:302-463,1458-1608` `captureRegularFileBinding`,`verifyRegularFileBinding`,`captureAtomicOutput`,`verifyAtomicOutput` | 스냅샷·바인딩 정의 | R-12 |
| C-06 | `archify/bin/archify.mjs:3236-3624` `commitDeliveryPair` | 쌍 교체 단계 순서·롤백 | R-14, R-15 |
| C-07 | `archify/bin/archify.mjs:136-216,520-757,985-1008` `deliveryLockPath`,`rejectExistingDeliveryLock`,`acquireDeliveryLock`,`beginDeliveryAttempt` | 잠금·journal | R-16, R-17 |
| C-08 | `archify/renderers/shared/cli.mjs:133-303` `throwAtomicOutputFailure`,`stageRenderedHtml`,`writeDiagram` | 임시 후보, 오류 접기 | R-12, R-20 |

범위 안 helper: `entryType`·`captureRegularFileHandle`은 "일반 파일·링크 수 1·핸들과 경로 inode 일치"로 푼다(R-12). `createRemovalQuarantine`는 "`.archify-remove-<32hex>` 0700 디렉터리 생성"(R-13).

### 1.6 수락 사례
출처: 모두 **원본 실행 관찰**(설치본, scratch). 스크립트·출력: [01-quality-animation-matrix.mjs](../../../artifacts/archify/spec-demos/rendering/contracts/01-quality-animation-matrix.mjs) → [01-matrix.tsv](../../../artifacts/archify/spec-demos/rendering/contracts/out/01-matrix.tsv), [02-quality-body-diff.mjs](../../../artifacts/archify/spec-demos/rendering/contracts/02-quality-body-diff.mjs) → [02-body-diff.txt](../../../artifacts/archify/spec-demos/rendering/contracts/out/02-body-diff.txt), [03-lock-deliver-render.mjs](../../../artifacts/archify/spec-demos/rendering/contracts/03-lock-deliver-render.mjs) → [03-lock.txt](../../../artifacts/archify/spec-demos/rendering/contracts/out/03-lock.txt), [04-render-replace.sh](../../../artifacts/archify/spec-demos/rendering/contracts/04-render-replace.sh) → [04-render-replace.txt](../../../artifacts/archify/spec-demos/rendering/contracts/out/04-render-replace.txt). 입력은 `archify/examples/*.json`을 `meta`만 바꿔 임시로 만든 것이고 HTML은 즉시 지웠다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | 10개 타입 예제에서 `meta.animation` 삭제 / `trace` / `none` | 세 경우 모두 종료 0, `data-animation="trace"`, SVG 해시 동일(타입당 3건 동일), `data-animate` 개수 동일 |
| T-02 | R-02 | 같은 예제에서 `meta.quality_profile` 삭제·`standard`·`showcase`, `--quality standard\|showcase`, 충돌 2조합 | 없음: `standard`+`advisory`. 명시 `standard`: `standard`, advisory 없음. 충돌(`--quality standard` + meta showcase)은 `standard`, (`--quality showcase` + meta standard)는 `showcase`. 모든 타입·모든 조합에서 루트 속성이 이 규칙과 일치 |
| T-03 | R-02 | `render … --quality foo` / 렌더러 직접 `ARCHIFY_QUALITY_PROFILE=foo` | 종료 2 `Unknown quality profile "foo". Expected standard or showcase.` / 종료 0, `data-quality-profile="standard"`, advisory 없음 |
| T-04 | R-03 | architecture `production-deployment`(경계 3개)와 `web-app`을 `--quality showcase`(meta 없음) vs `meta.quality_profile: showcase` | 루트 속성은 동일, 본문은 다름(production 8/328줄, web-app 2/275줄: 경계 라벨 마스크·글자 x좌표 `224` vs `628`) |
| T-05 | R-03 | sequence `cache-miss-request`를 같은 두 방식으로 | 루트 동일, 본문 24/279줄 다름(라벨 글자 9 vs 11, 상자 폭 58.8 vs 71.4). `--quality standard` + meta showcase의 본문은 `meta` standard와도 24줄 다름(루트는 standard) |
| T-06 | R-03 | workflow·dataflow·erd·class·lifecycle·tree·timeline·waterfall에서 `--quality showcase` vs meta showcase | SVG 해시 동일(8개 타입) |
| T-07 | R-05, R-06 | 10개 예제 | choreography: sequence/stream/walk/sweep/replay(해당 5개), 나머지 5개 없음. reader-fit: architecture·lifecycle·erd·class·tree·timeline `intrinsic-height`, waterfall `width-first`, 나머지 3개 없음 |
| T-08 | R-11 | `render tree`로 같은 경로에 두 번 | 폴더에 `a.html`만, inode가 바뀜(144371856→144371860), 링크 1개 |
| T-09 | R-11 | 하드링크가 있는 대상에 `render` | 종료 1 `[output/target-hardlinked]`, 대상 내용 `old` 그대로 |
| T-10 | R-17 | 사전 산출물 없는 폴더에 유효 v1 잠금(죽은 pid)을 두고 `deliver --json` | 종료 1, `stage:"prepare"`, 코드 `delivery/lock-stale`, 폴더 목록 불변(잠금 1개) |
| T-11 | R-17 | 같은 상태에서 산 pid / `garbage` / 빈 파일 / 디렉터리 / 레거시 `a.delivery-lock.json`(죽은 pid) | `delivery/concurrent-attempt` / `delivery/lock-invalid` ×3 / `delivery/lock-stale`. 모두 종료 1, 폴더 목록 불변 |
| T-12 | R-17 | 먼저 `deliver` 성공(`a.html`+`a.delivery.json`) 후 T-10·T-11의 잠금 6종을 각각 만들고 `deliver` | 코드·종료 코드 T-10·T-11과 같고 HTML·provenance 해시 전후 동일, journal·실패 표지 없음 |
| T-13 | R-18 | T-10 상태(잠금 있음)에서 같은 폴더에 `render lifecycle … r.html` | 종료 0, `r.html` 생성, 임시·격리 잔재 없음, 잠금 파일은 그대로 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
읽은 범위: `atomic-output.mjs` 1~130, 302~1608(바인딩·격리 제거·백업·publish·스냅샷 전부; 130~302의 해시·디스크립터 검사 helper와 1610~1982의 복구 도구용 `recoverRetiredPublication` 계열은 열지 않음), `cli.mjs` 110~430, `commitDeliveryPair`(3236~3624), `acquireDeliveryLock`·`rejectExistingDeliveryLock`·소유권 해제(120~220, 440~757), `beginDeliveryAttempt`·`writeDeliveryProvenance` 앞부분(985~1200), 각 렌더러의 루트 `<svg>` 반환 줄과 훅 grep, 뷰어 8개 파일의 참조 줄, `check-render-output.mjs`의 속성 읽는 줄. 열지 않음: `recordDeliveryFailure` 본문, `recoverRetiredPublication` 본문, 뷰어 JS의 분기 상세.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 `svgRootAttrs`(363), `common.schema.json:21-23` `animation` enum, `schemas/README.md:27`, T-01 | 코드 + 실행. `meta.animation` 읽는 곳을 `grep`으로 찾지 못함(렌더러·스크립트·bin) |
| R-02 | C-01(368-371), `bin/archify.mjs:2428-2434` `rendererEnv`, `extractQualityArgs`(`Unknown quality profile`), T-02 T-03 | 실행 확인(90건) |
| R-03 | B표 각 줄 인용, T-04~T-06 | 소비처는 `grep quality_profile\|ARCHIFY_QUALITY_PROFILE` 전수. 본문 차이는 실행 비교 |
| R-04 | 1.3 A 표 각 줄의 쓰는 곳·읽는 곳. 쓰기: `grep -rhoE "data-…" renderers`, 읽기: 같은 `grep`을 `viewer/`·`archify/scripts`·`archify/bin`·`archify/explainer`·`archify/delta`에 적용 | 코드 확인(grep 수준). 90건 루트 속성은 실행 |
| R-05 | sequence 1066, dataflow 1552, lifecycle 1101, timeline 497, waterfall 346, `motion-governor.js:28-36,412-442`, T-07 | 실행 + 코드 |
| R-06 | architecture 1138-1150, workflow 5478-5488, 나머지 각 렌더러 줄, `reader-layout.js:12-16,32-36`, `visual-check.mjs:1969`, T-07 | 코드 + 예제 실행 |
| R-07 | `viewer.css:4076-4120`, `reader-layout.js:89-95`, `export-cleanup.js:137-139`, 렌더러 `data-detail` 값(`"context"`·`"fine"`, lifecycle 삼항) | 코드 확인 |
| R-08 | 1.3 A "composition" 표의 각 렌더러 줄, `check-render-output.mjs:484-529,562,870` | 코드 확인 |
| R-09 | `viewer/template.source.html:7`, `check-render-output.mjs:1205-1216,1279` | 코드 확인 |
| R-10 | `delta/architecture-delta.mjs:456-457,507,567`, `explainer/diagrams.mjs:408-412`, `render-architecture.mjs:1046,1051` | 코드 확인 |
| R-11 | T-08 T-09 | 실행 확인 |
| R-12 | C-08, C-05 | 코드 확인 |
| R-13 | C-03, C-04, `atomic-output.mjs:586-723` 기록 생성, `:494-512` 격리 폴더 | 코드 확인. 실행은 결과 상태(R-11)만 |
| R-14 | C-06 `commitDeliveryPair` 3295-3452(단계별 `for` 6개) | 코드 확인. delivery.md R-16과 다름(D-10) |
| R-15 | C-06 3453-3614 | 코드 확인, 주입 실패는 실행 안 함 |
| R-16 | C-07 | 코드 확인 |
| R-17 | C-07 `rejectExistingDeliveryLock`·`acquireDeliveryLock`, T-10~T-12 | 실행 확인 |
| R-18 | T-13, `cli.mjs`에 잠금 참조 없음 | 실행 확인 |
| R-19 | 1.3 F 표: C-03, C-04, C-06 | 코드 추적 |
| R-20 | C-08 `throwAtomicOutputFailure`(133-165), `writeDiagram`(276-284) | 코드 확인 |
| R-21 | C-03 4~5단계, C-05 | 코드 확인 |
| T-01~T-13 | 1.6의 스크립트·출력 | 실제 출력과 대조 |

**기존 스펙 보정 제안** (이 스펙은 기존 파일을 고치지 않았다)

| 대상 | 어디를 어떻게 |
|---|---|
| rendering.md R-14 | "교체 방식(원자 rename 여부)은 추론"을 "코드 확인"으로 바꾸고 이 스펙 R-13을 링크: rename 덮어쓰기가 아니라 하드링크 백업(`.archify-remove-<hex>/previous` + 복구 기록) → 공개 이름 격리 제거 → `link`. 실패 코드 4종이 모든 publish 실패를 접은 것임(R-20)과 `committed-with-warning`이 성공으로 처리됨을 덧붙임 |
| rendering.md 1.4 M-04, M-05 | M-04: 해소(이 스펙 R-12~R-21), M-05: 해소(R-04~R-10, 어긋남 D-01~D-11). 2.1의 "열지 않음: `atomic-output.mjs`" 문구 수정 |
| rendering.md R-15 | (a) sequence의 `meta.quality_profile`만 보는 소비처 추가, architecture 나열에 "`--quality`만 주면 본문은 standard 경로"를 명시(R-03). (b) `container-border-run`: "렌더러는 프로파일이 있으면 오류, 정적 검사는 `data-quality-gates`로 오류/경고"로 정정(D-02). (c) 잘못된 환경 값(직접 실행)은 `standard`·advisory 없음, CLI는 종료 2 |
| rendering.md R-16·1.3 E | "모든 타입 공통"에 `data-motion-choreography`(타입 매핑)·`data-reader-*`·`data-detail*`·`data-graph-role`·`data-composition-*`의 타입별 쓰기 표(이 스펙 1.3 A)를 링크하거나 옮김. R-31의 "모든 경로"를 "관계 경로가 있는 8개 타입, 헤일로는 architecture·dataflow·lifecycle"로 정정. 1.3 F의 `meta` 표에 `meta.animation: none`은 허용되나 무효임을 추가 |
| rendering.md R-27 | `data-composition-route="straight"`는 대각선 직선일 때만이라는 한 줄 추가(D-08) |
| viewer.md "렌더러가 약속하는 DOM 속성" 표 | 행 추가: `data-detail`·`data-detail-anchor`, `data-reader-min-text`·`-primary-text`, `data-legend`·`-bridge`·`-kind`·`-label`, `data-graph-role`(자동 교차 밑선), `data-edge-id`·`data-animate`. `data-reader-fit`은 `width-first`·`intrinsic-height`만 해석, `authored-height`는 검사 전용이라고 명시. 248행 확인 한계("`meta.animation: none`…확인하지 않았다")를 "무효, `trace`가 항상 붙음(rendering-contracts R-01)"으로 닫음 |
| verification-gates.md R-10·R-11 | 헤일로·`data-composition-independent`를 만드는 타입을 명시(architecture·lifecycle, dataflow는 헤일로만) |
| verification-gates.md R-20·R-21 | `data-diagram-type`은 architecture + 저자 `meta.viewBox`에서만 존재, 자동 viewBox는 `data-reader-primary-text="14"`가 대신한다는 점. `data-edge-role`은 읽히지만 판정에 쓰이지 않음 |
| verification-gates.md R-19·R-14 | 프로파일은 SVG 루트 속성만 본다(환경 변수 무시)는 점과, 그래서 `--quality`만 준 architecture·sequence는 본문이 standard 경로인데 검사만 showcase가 될 수 있음(이 스펙 R-03)을 링크 |
| delivery.md R-16 | "대상마다 HTML → provenance 순으로 ①~④"를 단계별 서술로 교체: (1) 두 대상 검증·바인딩, (2) HTML 백업 → provenance 백업, (3) HTML `link` → provenance `link`, (4) 두 공개 이름 링크 2개 확인 → 두 후보 격리 제거 → 링크 1개 확인 → journal 삭제. 이 스펙 R-14 |
| delivery.md R-17, R-20 | R-17: 되돌리기는 "새 링크 전부 제거 → 백업 전부 복원" 두 루프(R-15). R-20: "②와 ③ 사이에서 죽으면 HTML만 없을 수 있고"를 "두 공개 이름이 모두 없을 수 있고 백업이 `.previous-output`·`.previous-provenance`에 각각 있다"로 정정 |
| delivery.md R-18, T-17 | T-17을 "실행 확인"으로 승격하고 사례를 늘림(산 pid, 형식 오류 3종, 레거시 잠금). R-18에 "잠금 해제도 격리 제거를 쓴다" 한 줄. 1.5 C-10 아래에 "같은 연산을 단일 파일 경로(`publishRegularFileBinding`)가 쓴다"를 덧붙이고, 2.1의 "문서와 구현 차이 (2)"에 이를 링크 |
| `archify/schemas/README.md:27` (원본 문서) | 스펙 수정 대상은 아님. "`meta.animation: trace` opt-in"은 구현과 다르다(모든 타입이 항상 trace). 원본 문서 차이로 overview의 "문서와 구현 차이"에 올릴 만함 |

feature map 보정 제안: (1) rendering 행의 상태 칸에 "M-04·M-05는 rendering-contracts로 해소"를 적고 새 행 `rendering-contracts`(depends rendering, 상태 draft)를 추가한다. (2) 출력 쓰기 기본 연산(`atomic-output.mjs`)이 render·finalize 영수증(`finalize.mjs:74`)·preview(`preview.mjs:687`)·explainer(`render-explainer.mjs:37`)·deliver 네 곳의 공유 계약인데 feature map에는 rendering R-14와 delivery 두 곳에 흩어져 있다. 소유 행을 하나로 정하거나 위 비교표를 공유 계약으로 가리키는 편이 낫다. (3) viewer 행(11)의 "렌더러가 약속하는 속성"은 rendering-contracts 1.3 A가 상세 출처임을 표시한다.

## 적용 메모
없음.
