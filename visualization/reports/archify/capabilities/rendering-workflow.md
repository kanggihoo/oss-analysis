---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/renderers/workflow/render-workflow.mjs
  - archify/renderers/workflow/workflow-compiler.mjs
  - archify/renderers/workflow/workflow-migration-geometry.mjs
  - archify/renderers/workflow/workflow-placement-repair.mjs
  - archify/renderers/workflow/README.md
  - archify/schemas/workflow.schema.json
  - archify/renderers/shared/geometry.mjs
  - archify/renderers/shared/route-quality.mjs
  - archify/renderers/shared/spatial-grid.mjs
  - archify/renderers/shared/legend.mjs
  - archify/renderers/shared/text-fit.mjs
  - archify/renderers/shared/desktop-readability.mjs
  - archify/renderers/shared/cli.mjs
  - archify/examples/agent-tool-call.workflow.json
  - archify/examples/release-delivery.workflow.json
depends: [rendering.md]
status: ready            # 2026-11-02: 이 스펙 자체의 미결정 없음, 선행 스펙 ready
reimplementation: 미실행
---

# 렌더링: workflow 렌더러 (입력 정규화 → 열·레인 배치 → 라우트 선택 → 검증 → SVG)

> 검증을 통과한 workflow 문서 하나(`schema_version` 1 또는 2)를 받아, `compileWorkflow`가 `{ok, svg, receipt, diagnostics}`를 돌려주는 과정을 재현할 수 있게 쓴다. v1은 고정 좌표로, v2는 열 제약 풀이·후보 라우트 비용 선택·바깥쪽 피드백 루프로 배치한다. [rendering.md](rendering.md) R-40·M-02를 대체하는 하위 스펙이다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. `render-workflow.mjs`가 `loadDiagramWithBrandMarks`로 diagram을 받고, `compileWorkflow({workflow, qualityProfile: 환경 ARCHIFY_QUALITY_PROFILE || meta.quality_profile, sourceEvidence})`를 격리된 진단 기록 범위 안에서 부른다(R-01).
2. 컴파일러 바깥층이 v2·showcase·핀 없음 조건에서만 돌아가는 보정 루프를 겹쳐 부른다. 바깥에서 안으로 `compileWorkflow` → `compileWorkflowWithFeedback`(sublabel 폭 확대 에포크) → `compileWithLayoutFeedback`(열 간격·레인 간격 피드백, 최대 4번 컴파일) → `compileWithRouteOrderFeedback`(v2 라우트 순서 재시도 ≤3) → `compileWorkflowInternal`(R-21).
3. `compileWorkflowInternal`은 스키마·관계 ID 검사 → v2 정규 순서 정렬 → `semanticChecks` 검사 → 레이아웃(v1 고정, v2 열 풀이) → 범례 발자국 → 레인 기하 → 노드 측정 순으로 장면을 만든다(R-03~R-08).
4. 같은 `try` 안에서 `validateReadableInputsBeforeRouting` → `validateReadablePinnedGeometry`(라우트를 처음 계획) → `validateWorkflow` → `finalizeReadableViewBox` → `validateReadableNodeText` → `renderSvg`가 이 순서로 돈다. 어느 단계든 진단 오류를 던지면 `ok:false`다(R-09~R-20).
5. 성공이면 `{ok:true, svg, receipt}`, 실패면 `{ok:false, error, diagnostics, receipt}`다. 렌더러는 `--layout-json`이면 `receipt`만 JSON으로 찍고, 아니면 실패 시 진단을 던지고 성공 시 `writeDiagram`을 부른다(R-01, R-23).
6. 같은 문서·같은 프로파일이면 결과는 같다. 컴파일러에는 난수·시계가 없다(R-26).

### 1.2 범위·통합 지점 [필수]
- 제공: workflow `compileWorkflow`의 단계 순서, 모든 상수, 열 제약 풀이, 레인 높이·캔버스 공식, 라우트 후보·비용·선택·수리, 라벨 위치, 핀 충돌 분류, 피드백 루프, 레이아웃 진단 code와 조건, SVG 구성, v1↔v2 차이와 마이그레이션 좌표 변환.
- 제외: 스키마 검증 자체와 진단 객체 필드(input-validation.md), 템플릿 슬롯·`writeDiagram`(rendering.md), `supportedFixes` 문구의 검증 탐색(R-22는 동작만 쓰고 문구 전체는 코드 참조), 브랜드 마크 본문, HTML 안 뷰어, `check`·`browser-check`. `migrate workflow` 명령 자체의 CLI 계약(auxiliary-commands.md 소관)은 좌표 변환 규칙만 쓴다.
- 외부 의존·선행 계약: rendering.md의 공통 계층(R-14~R-19, C-03, C-07, C-22, C-24, C-26, C-36)과 공유 게이트. `validateSchema('workflow', …)`와 `validateCrossCollectionContracts`가 컴파일러 안에서 다시 호출된다(실패하면 `supportedFixes`는 비운다).
- 소유 상태·부작용: 컴파일 한 번 안에서만 사는 캐시(`pathCache`, `readableSideCache`, 장애물 격자, 라벨 사각형 WeakMap, 후보 수정 검증 캐시 ≤128개)와 노드 객체에 매단 자동 폭(WeakMap). 입력 문서는 고치지 않는다(수정 후보는 `cloneWorkflow` 복사본). 파일 부작용은 없다(쓰기는 렌더러 몫).

### 1.3 인터페이스와 데이터 의미 [필수]

**A. 공개 경계**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `compileWorkflow({workflow, qualityProfile?, sourceEvidence?})` | 파싱된 문서 하나 → `{ok:true, svg, receipt}` 또는 `{ok:false, error, diagnostics, receipt}` | 문서가 객체가 아니면 `workflow/input-contract`(계약 `fixed-v1`). `qualityProfile`이 문서의 `meta.quality_profile`과 다르면 앞의 값으로 문서를 복사해 덮어쓴다. 즉 workflow에서는 환경 변수(`--quality`)가 모든 게이트에 적용된다(architecture와 다름). |
| `receipt` | `{contract, viewBox, requiredViewBox, columns, nodes[id,lane,col,x,y,width,height], edges[id,from,to,points], labels[edge,label,x,y,width,height], diagnostics}` | 성공 영수증에는 `ok` 키가 없다. 늦은 검사에서 실패한 완성 계획에는 같은 기하와 `ok:false`가 붙고 `viewBox`는 시도한 값, `requiredViewBox`는 그 계획의 측정값이다. 앞 단계(스키마·의미·핀 사전 검사 등)에서 실패하면 `{contract, diagnostics}`만 있다. 라벨 `x,y`는 마스크 좌상단이 아니라 앵커(`lx,ly`)다. |
| `archify validate workflow <json> --layout-json` | stdout에 `receipt` JSON | 실패하면 종료 1이고 HTML은 없다. 스키마 실패는 영수증이 아니라 stderr 텍스트(stdout 비어 있음, T-17). |
| 렌더러 직접 `render-workflow.mjs` | rendering.md R-04·R-05 | `--layout-json`이면 `compiled.receipt` 출력 후 `ok`가 거짓이면 종료 코드 1. |

**B. 입력 필드 → 렌더 효과** (스키마는 input-validation 소관, 값 범위만 적는다)

| 필드 | 효과 |
|---|---|
| `schema_version` 1 / 2 | 1은 `fixed-v1`(고정 좌표, 기존 바이트 보존), 2는 `readable-v2`. 서로 자동 변환되지 않는다. |
| `lanes[id,label,variant:"normal"\|"exception"]` | 위에서 아래로 쌓는 띠. 라벨 접두 `NN / `(1부터 2자리) 또는 `exception`이면 `EX / `. exception은 안쪽 `c-security-group` 프레임(6px 안쪽)을 더 그린다. |
| `phases[id,label,fromCol,toCol,variant]` | 레인 위쪽 띠(y 27~43)의 머리말. 열 구간이 서로 겹치면 진단. |
| `groups[id,label,lane,fromCol,toCol,variant]` | 레인 안 프레임. 노드가 하나도 없으면 진단. |
| `mainPath[]` | 연속 쌍마다 같은 방향 edge가 있어야 하고 `col`이 줄어들면 안 된다. 애니메이션 단계 번호의 기준이기도 하다. |
| `semanticChecks{allowedRoots,allowedTerminals,requiredEdges,requiredPaths}` | 레이아웃 전에 위상만 검사(R-03). SVG·영수증 바이트에 영향 없음. |
| `nodes[id,lane,col 0..5,type,label,sublabel,tag,icon,brand,sources,width≥32,height≥32,yOffset]` | `width` 기본 92(v2는 자동 확대 가능), `height` 기본 52(`tag`가 있으면 68), `yOffset`은 레인 내용 영역 중심 기준 세로 이동. |
| `edges[id,from,to,label,variant,role:main\|branch\|async\|return\|error,fromSide,toSide,route,via,labelAt,labelDx,labelDy,labelSegment,channelX,channelY,bias,width]` | v2에서 `via`·`labelAt`·`channelX`·`channelY`는 **절대 핀**, `route` 프리셋은 후보군 제한(핀 아님), `fromSide/toSide`는 방향 제약. `width` 기본 1.4(emphasis 1.8). |
| `meta.viewBox [≥700, ≥240]` | 있으면 그대로 쓰고 키우지 않는다. v2에서는 이것도 "절대 기하 보존 정책"을 켠다(R-05). |
| `meta.legend`, `quality_profile`, `animation`, `visual_preset` | 범례 항목 선택(공통), 게이트 심각도(R-18), 루트 속성(R-24). |

**C. 상수 표**

| 구분 | 상수 | 값 |
|---|---|---|
| v1 | 레인 | x 40, y 52, 폭 640, 높이 104, 간격 20, 제목 띠 30 |
| v1 | 열 중심 `[col0..col5]` | 88, 220, 300, 430, 500, 625 (`LEGACY_COLUMN_CENTERS`) |
| v1 | 노드 기본 / 기본 viewBox 폭 | 92×52 / 720 |
| v2 | 열 수, 기준 피치, 시작 x, 풀이 반복 한도 | 6, 120, 94, 3(실효 2번: 둘째 판은 피드백 제약 포함) |
| v2 | 채널 우회 예산 | 112 (`4×28`) |
| v2 | 같은 레인 노드 간격 | 핀·viewBox 없음 32, 있음 8 (`preservesWorkflowAbsoluteGeometry`) |
| v2 | 직선 직접 간격 | 28 (+ 라벨 마스크 폭+8) |
| v2 | 열 시작 보정 | 왼쪽 안쪽 여유 8, 첫 열 최소 반폭 46, 레인 라벨 보정 +2 |
| v2 | 레인 폭 하한 / 오른쪽 여유 | 640 / 오른쪽 끝+8, 캔버스 오른쪽 +16 |
| 공통 | 레이아웃 선 | 레인 라벨 x+14, y+22, 글자 10 굵기 600 |
| 공통 | 그룹 프레임 | 위 여유 8, 아래 4, 라벨 기준선 −2, 마스크 올림 10, 마스크 높이 14, 노드 안쪽 여유 4, 라벨 글자 7 |
| 공통 | 라우트 리듬 | 직선 28, 끝 토막 8, 안쪽 굽이 16 (`HARD_ROUTE_RHYTHM`), 출구 토막 `outwardStub` 16 |
| 공통 | 라벨 | 폭 `max(30, textUnits×4.8+10)`, 높이 14, `y = ly−10`, 글자 8 |
| 공통 | 노드 글자 | label 11→9, sublabel 8→6, tag 7→6, 폭 계수 0.6, 안쪽 여백 8 |
| 공통 | 범례 | 글자 7, 항목 간격 7, 종류 7(`frontend, backend, security, messagebus, database, cloud, external`), x 20 |
| 공통 | 장애물 격자 셀 | 160 |
| 공통 | 가독 한계 | 데스크톱 폭 930(960−30), 투영 최소 글자 6, sublabel 글자 상한 8 → 최대 캔버스 폭 `floor(930×8/6)=1240` |

`textUnits`(글자 폭 단위)는 rendering.md C-26, 범례 계산(`resolveLegend`·`legendFootprint`·`measureLegend`)은 C-33이 소유한다. 이 스펙은 두 함수를 위 인자(글자 7, 간격 7)로 부른다는 것만 정한다.

**D. v2 열 풀이 (`createReadableLayout`)**

입력은 정규 순서로 정렬된 문서와 피드백 `{rankGapMinimums, rankGapContributors, laneGapMin, laneGapContributors, fanInLabelClearance, routeFirst}`다. 단계는 다음 순서다.

1. 제약 모으기. 모두 `{from 열, to 열, minimum px}` 형태이다.
   (a) 인접 열마다 `minimum=120`. (b) 피드백의 `rankGapMinimums["from:to"]`. (c) 같은 레인에서 열이 다르고 세로 구간이 겹치는(`|Δ yOffset| < h₁/2+h₂/2+8`) 노드 쌍: `w₁/2 + nodeClearance + w₂/2`. (d) 같은 레인 다른 열 edge(`via/channelX/channelY` 없고 `route`가 auto/straight이며 두 노드 `yOffset` 같음): `w₁/2+28+w₂/2`. 이때 `label`이 있고 `labelAt`이 없으면 직접 간격 요구 `max(28, 라벨 폭+8)`를 구한다. 라벨 팽창 비용 `요구−28`이 112보다 크고 edge가 완전 자동(`route` auto, `fromSide/toSide/channel*` 없음)이면 "라벨 채널 선호" edge로 기록하고 라벨 제약은 넣지 않는다. 아니면 비용이 0 초과일 때 `w₁/2+요구+w₂/2`를 **피드백 제약 목록**에 넣는다. (e) phase: 단일 열이면 `col→col+1`에 `120+max(0, 라벨폭−92)`, 여러 열이면 `from→to`에 `max(0, 라벨폭−92)`(라벨폭 = `textUnits×5.6+8`). (f) group: 같은 식에서 라벨폭 `textUnits×5.6+20`, 기준 100(`minimum − 100`).
2. 풀이. 반복 0은 열 `x_c = 94 + 120c`에서 시작해, 도착 열 `to=1..5` 순서로 그 열을 도착으로 하는 제약을 `(to, from, minimum)` 오름차순으로 훑으며 `x_to = max(x_to, x_from + minimum)`로 올린다(오차 0.0001). 피드백 제약이 있으면 반복 1에서 같은 풀이를 제약 목록에 그것을 더해 처음부터 다시 한다(반복은 거기서 끝). 열은 오른쪽으로만 밀린다.
3. 보정 이동(모든 열 같은 양). 순서대로 (i) 왼쪽: `max(0, 40+8+firstExtent−x₀)`, `firstExtent`는 0열 노드 반폭의 최댓값(최소 46). (ii) 레인 머리말: `via`·`channelX` 없는 edge가 `fromSide`/`toSide`로 `top`을 지정한 노드마다 `머리말 오른쪽 = 54 + textUnits("<접두> / <레인 라벨>")×6.2`이고 `머리말 오른쪽+2−x_col`의 최댓값만큼. (iii) 내용 왼쪽: 라벨 채널 edge는 `16−라벨 왼쪽`, phase는 `16−왼쪽`(폭 = `max(x_to−x_from+92, 라벨폭)`, 단일 열이면 왼쪽 `x−46`, 아니면 가운데 정렬), group은 `44−bounds.x`의 최댓값.
4. 레인 폭 `laneW = max(640, ceil(오른쪽끝−40+8), ceil(최대 라벨 폭))`. 오른쪽끝은 `x₅+50`, 모든 노드 오른쪽, 모든 group 오른쪽 중 최대. 최대 라벨 폭은 레인마다 `textUnits("NN / 라벨")×6.2+30`(접두는 항상 번호, EX 아님). `defaultViewBoxWidth = 40+laneW+16`.
5. 높이(R-07). 6. 반환 `{contract:"readable-v2", laneW, laneH, laneHeights, laneGap, groupHeaderHeights, groupFooterHeights, colXs, channelLabelEdgeKeys, widthContributors, heightContributors}`. 기여자 문자열은 진단 `evidence.contributors`용이며 기하에는 영향이 없다.

**E. 라우트 후보와 비용**

후보 가족(`readableAutomaticCandidateSet`)은 이 순서의 17개다: `facing-straight`, `horizontal-then-vertical`, `vertical-then-horizontal`, `lane-gap-corridor`, `column-gap-corridor`, `outside-left`, `outside-right`, `top-corridor`, `bottom-corridor`, 그리고 오프셋 −12, +12, −24, +24마다 (`lane-gap-corridor`, `column-gap-corridor`) 한 쌍. 좌표는 아래와 같다.

| 값 | 식 |
|---|---|
| `midX` | `(start.x+end.x)/2` |
| `laneGapY` | 같은 레인이면 `laneTop(from.lane)−16`, 아니면 `bottom(from)+(top(to)−bottom(from))×(bias ?? 0.5)` |
| `topY` | `max(8, min(두 레인 top)−16)` |
| `bottomY` | `max(두 레인 bottom)+16` |
| `outsideLeft` / `outsideRight` | `laneX−20 = 20` / `laneX+laneW+12` |
| 코리도 via | 시작·끝 점에서 변 바깥쪽으로 16 나간 점(`outwardStub`)을 잇는다. Y 코리도는 `[sStub,[sStub.x,y],[eStub.x,y],eStub]`, X 코리도는 `[sStub,[x,sStub.y],[x,eStub.y],eStub]` |

점열은 `joinRoutePoints`(중복점·앞으로 가는 공선점 제거)로 만든다. 후보가 실행 가능하려면 아래 12개 검사를 이 순서로 통과해야 하고(첫 실패가 사유), 통과한 후보만 비용을 계산한다. (`readableCandidateRejection`)

| # | 검사 | 사유 문자열 |
|---|---|---|
| 1 | 점 2개 이상 | `route endpoints` |
| 2 | 모든 구간이 가로 또는 세로이고 길이>0.0001 | `orthogonal non-zero segments` |
| 3 | 직선 28, 첫·끝 토막 8, 안쪽 16 이상 | `readable segment rhythm` |
| 4 | 첫·끝 구간이 지정한 변 방향을 수직으로 지킴 | `perpendicular endpoint-side direction` |
| 5 | 안쪽 구간이 끝점 노드를 안 지남 | `node clearance` |
| 6 | 자동 라벨(`labelAt` 없음)이 노드와 −2 여유로 안 겹침 | `edge-label node clearance` |
| 7 | 라우트·라벨이 레인/phase/group 머리말 장애물을 안 지남 | `lane/phase/group label clearance` |
| 8 | 무관한 노드와 2px 여유 | `node clearance` |
| 9 | 이미 놓인 라벨과 라벨끼리 −2, 라우트와 4px 간격 | `placed edge-label clearance` |
| 10 | 라우트·자동 라벨 좌표가 모두 x≥0, y≥0 | `canvas origin` |
| 11 | 구조 프레임(레인·exception·group) 테두리와 공선 겹침 없음 | `structural-frame border clearance` |
| 12 | 범례 사각형과 안 겹침(범례 있을 때) | `legend clearance` |

비용 벡터는 아래 15차원을 **앞에서부터 사전식**으로 비교한다(`compareCost`, 같으면 다음 차원). 값이 없으면 0.

| 순위 | 차원 | 정의 |
|---|---|---|
| 1 | `properCrossingCount` | 이미 놓인 라우트와의 진짜 직교 교차 수 |
| 2 | `unrelatedBendContactCount` | (자동 라우트만) 무관한 라우트와 굽이점이 닿는 수 |
| 3 | `sharedCorridorPx` | 8px 이상 공선 겹침 길이 합(짧은 같은 방향 동일 포트 트렁크 24 이하는 면제) |
| 4 | `automaticForwardReversePx` | 앞으로 가는 edge(`to.col>from.col`, role이 return/error 아님)에서 x가 줄어드는 길이 합 |
| 5 | `labelRouteClearanceDeficit` | 라벨-라우트 간격 8 미만분 합 |
| 6 | `laterArrivalBlockCount` | 같은 열 위쪽 레일에서 이후 도착을 가로막는 수(대기 edge ≤8개일 때만) |
| 7 | `oppositeParallelDeficit` | 반대 방향 평행 간격 <8, 겹침 24 초과분×(8−간격)의 최댓값 |
| 8 | `interiorPreferred28Deficit` | 안쪽 구간이 28 미만인 부족분 합 |
| 9 | `excessiveVerticalTravelPx` | 같은 열·세로 이동에서 `경로길이−2|Δcy|` |
| 10 | `bendCount` | 점 수−2 |
| 11 | `stretchMilli` | `round(경로길이/맨해튼거리×1000)` |
| 12 | `canvasGrowthPx` | 음수 쪽 + `maxX−minimumCanvasWidth` + `maxY−autoHeight` 초과분 |
| 13 | `portDisplacementMilli` | 자연 포트에서 벗어난 거리×1000 |
| 14 | `legacyCoordinateDisplacement` | 두 노드 중심의 v1 열 중심과의 거리 합 |
| 15 | `stableCandidateOrdinal` | 후보 순번(쌍 `pairOrdinal×9`, 포트 대안 `portOrdinal×144` 오프셋) |

**F. 진단 code 표**

심각도는 error, `warning`은 영수증에만 남고 컴파일을 막지 않는다. "단계"는 R-ID로 연결한다. v1 문서는 같은 위반을 대부분 구조화 code 없이 `layout/constraint`로 낸다(R-27).

| code | 조건 | 판 | 심각도·단계 |
|---|---|---|---|
| `workflow/input-contract` | 입력이 객체가 아님 / 스키마 검증이 분류 안 된 예외 | 둘 | error, R-03 |
| (스키마·`relationship/duplicate-id` 등) | 스키마·관계 id 위반. `supportedFixes` 비움 | 둘 | error, R-03 |
| `workflow/semantic-node-reference` | `semanticChecks`가 없는 노드 id 참조(경로 포함). 이게 있으면 아래 의미 검사는 건너뜀 | 둘 | error, R-03 |
| `workflow/unexpected-root` / `unexpected-terminal` | `allowedRoots`(`allowedTerminals`)가 있고 들어오는(나가는) edge 0인 노드가 목록에 없음 | 둘 | error, R-03 |
| `workflow/required-edge` | `requiredEdges`의 `from→to` edge가 없음(방향 정확히 일치) | 둘 | error, R-03 |
| `workflow/required-path` | `requiredPaths`의 방향 도달성이 없음(BFS) | 둘 | error, R-03 |
| `workflow/column-capacity` | v1: 같은 레인 다른 열 edge에서 세로 구간이 겹치는 두 노드의 부호 있는 간격이 요구(직접 직선 28, 아니면 8)보다 작음. edge 순서로 첫 위반 하나만 | v1 | error, R-04. `suppresses`: `workflow/short-edge`, `clean-flow/endpoint-side-direction`, `workflow/label-node-overlap` |
| `workflow/duplicate-lane-id`, `duplicate-node-id` | id 중복(저작 순서 첫 중복) | v2 | error, R-09 |
| `workflow/unknown-edge-endpoint` | edge from/to가 없는 노드 | v2 | error, R-09 |
| `workflow/unknown-node-lane` | 노드의 lane이 없음 | v2 | error, R-09 |
| `workflow/invalid-node-column` | 열이 0..5 정수가 아님(스키마가 막아 정상 경로로는 도달 안 함) | v2 | error, R-09 |
| `workflow/non-finite-node-geometry` | 측정 좌표가 유한하지 않음 | v2 | error, R-09 |
| `workflow/node-overlap` | 같은 레인 두 노드가 8px 미만(`rectsOverlap(…,8)`). 모든 쌍을 한 번에 보고 | v2 | error, R-09 |
| `workflow/explicit-pin-conflict` | 핀·방향 제약이 불변식을 어김. `evidence.invariant`는 R-16 표, 추가로 원점 밖 기하(핀 있음) | v2 | error, R-16 |
| `workflow/route-preset-conflict` | 프리셋 후보가 실행 불가. `evidence`에 사유·후보점·변·요구 길이 8/16/28 | v2 | error, R-15 |
| `workflow/solver-budget-exhausted` | 자동 후보가 하나도 없고 피드백도 못 줌 / 피드백 소진 / 원점 밖 기하(핀 없음) | v2 | error, R-14 |
| `workflow/viewbox-capacity` | `meta.viewBox`가 `requiredViewBox`보다 작음 | v2 | error, R-19 |
| `workflow/sublabel-readability` | R-20 | v2 | error |
| `workflow/absolute-geometry-sizing` | 절대 기하 보존 때문에 자동 폭 확대가 꺼졌는데, 폭을 늘리면 글자 검사가 풀리는 노드가 있음. 이미 다른 pin/preset/budget 오류가 난 실패에만 덧붙는 `warning` | v2 | warning |
| `workflow/unknown-endpoint` | `mainPath`가 없는 노드 id 참조(후보 3개 검증 수정 포함) | 둘 | error, R-18 |
| `layout/constraint` | 구조화 상세가 없는 문장. 레인·노드·phase·group id 중복, phase 겹침·범위, 빈 group, 같은 레인 8px, mainPath 쌍 edge 없음·뒤로 감, 라벨-노드·라벨-라벨 겹침, v1 viewBox 폭·범례 높이, v1 알 수 없는 레인/끝점, 노드 글자(`workflowNodeTextProblems`) | 둘 | error, R-18 |
| `clean-flow/endpoint-side-direction`, `clean-flow/edge-through-node` | 끝점 변 방향 위반, 무관한 노드 2px 관통 | 둘 | error 항상 |
| `composition/proper-crossing` | 서로 다른 두 edge의 진짜 교차. v2는 끝점을 공유해도 검사, 앞으로 가는 공선 점은 합쳐서 본다 | 둘 | showcase error, 아니면 v2만 warning, v1은 검사 안 함 |
| `composition/ambiguous-corridor` | 8px 이상 공선 겹침. v2는 공유 끝점도 포함하고 24px 이하 같은 방향·같은 포트·같은 variant·width·role 트렁크는 면제 | 둘 | showcase error, 아니면 v2만 warning |
| `composition/arrowhead-collision` | 같은 노드·같은 축·같은 방향 도착 화살촉 간격이 `3.5×(폭₁+폭₂)` 미만 | v2 | showcase error, 아니면 warning |
| `composition/container-border-run` | 라우트가 프레임 테두리를 따라 공선 달림 | 둘 | 유효 프로파일이 있을 때만(standard·showcase) error |
| `composition/micro-segment`, `short-interior-segment` | 구간<8 / 안쪽 구간<16 | 둘 | showcase error |
| `composition/label-route-clearance` | 라벨 사각형과 다른 edge 라우트 거리 <4 | 둘 | showcase error |
| `composition/label-canvas-containment` | 라벨이 캔버스 밖 | v1만 | showcase error |
| `legend/vertical-overflow`, `label-too-wide`, `content-overlap` | `meta.legend`를 지정했는데 범례가 안 들어감(지정 안 했으면 숨김) | 둘 | error, R-24 |

`workflow/short-edge`와 `workflow/label-node-overlap`은 코드에서 `column-capacity`의 `suppresses` 목록 문자열로만 나오고 실제로 발행되는 진단이 아니다. 같은 위반의 실제 code는 `layout/constraint`다.

**G. SVG 출력** → R-24.

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 렌더러 실행 | C-01. `compileWorkflow` 결과가 `ok`면 `writeDiagram`(카드·`sourceEvidence` 포함), 아니면 `throwDiagnosticError(compiled.error, compiled.diagnostics)`. 컴파일 중 던져진 분류된 오류(`archifyDiagnostics`)는 격리 범위를 나온 뒤 다시 기록되어 위로 전파된다. `--layout-json`이면 어느 쪽이든 `receipt`를 출력하고 실패 시 종료 1 | 코드 확인 + 실행 확인(T-27) |
| R-02 | `schema_version` | 1은 `createLegacyLayout`, 2는 `createReadableLayout`. v1은 v2 규칙으로 해석되지 않는다. 컴파일러가 허용하는 값은 1, 2뿐(그 외 문제 문장). 번들 예제 4개: agent-tool-call·holiday-planning은 v2, incident-response·release-delivery는 v1이고 모두 `quality_profile: showcase` | 코드 확인 + 실행 확인(T-02, T-26) |
| R-03 | 컴파일 입구 | 순서: (1) 입력 객체 검사 (2) `qualityProfile` 덮어쓰기 (3) 스키마·관계 id 검증(실패 시 `supportedFixes` 비운 진단으로 `ok:false`, 계약은 v2면 `readable-v2` 아니면 `fixed-v1`) (4) `canonicalReadableWorkflow`: v2만 자동 폭 지정과 정렬(노드: 레인 순서→`col`→id, edge: `compareWorkflowEdges`=id→from→to→label→route→JSON, phase: fromCol→toCol→id, group: 레인→fromCol→toCol→id). v1은 순서 그대로 (5) `semanticContractDiagnostics`(F 표: 모르는 id 참조가 있으면 그것만, 아니면 root→terminal→required-edge→required-path 순) (6) 레이아웃. 정렬은 SVG 순서와 `data-edge-key`에 영향을 준다(진단은 원본 인덱스를 쓴다) | 코드 확인 + 실행 확인(T-14, T-17) |
| R-04 | v1 레이아웃 | C-02 상수 그대로. 열 풀이·피드백 없음. 자동 폭 없음(노드 폭 92 또는 `width`). `validateWorkflow` 앞부분에서 `enforceLegacyColumnCapacity`가 같은 레인·다른 열·세로 구간 겹침 edge마다 부호 있는 간격(`|Δcx|−w₁/2−w₂/2`)을 요구(직접 직선=`via` 없음·route auto/straight·`cy` 같음이면 28, 아니면 8)와 비교해 모자라면 `workflow/column-capacity` 하나를 던진다. `supportedFixes`는 (a) v2로 옮기면 용량이 생길 때 `migrate…` 문구 (b) 겹치지 않는 가장 가까운 열 (c) 폭 축소. 검증은 `acceptsFix`(R-22). v1 viewBox 자동은 `[720, 52+Σ레인높이+(n−1)×20+124]`이고 저자 값이 있으면 폭≥696, 범례 `lastLaneBottom+44+18`≤높이가 아니면 `layout/constraint` 문장 | 코드 확인 + 실행 확인(T-02, T-03, T-29) |
| R-05 | v2 열 풀이 | 1.3 D 순서와 상수 그대로. "절대 기하 보존" 정책(`preservesWorkflowAbsoluteGeometry`) = `meta.viewBox`가 배열이거나 어느 edge든 `via`/`labelAt`/`channelX`/`channelY`가 있음. 이 정책이면 노드 간격 8·자동 폭 확대 없음, 아니면 간격 32·자동 폭 허용. 정책은 마이그레이션 계획용 투영에서 심볼로 덮어쓸 수 있다(R-25) | 코드 확인 + 실행 확인(T-01, T-04, T-05, T-07, T-08, T-09, T-10) |
| R-06 | v2 자동 노드 폭 | `width`가 없고 정책이 꺼져 있으면 `labelW = max(92, ceil((textUnits(label)×6.8−6)/4)×4)`. sublabel(8px)·tag(7px)가 최소 6px로도 `availableNodeTextWidth(labelW)=labelW−8`에 안 들어가면 `ceil((최소폭(글자 8 또는 7)+labelW−(labelW−8))/4)×4`. 최댓값이 92보다 크면 200 이하로 자름(`null`이면 92). showcase 확대 에포크(R-20)의 `widthOverrides`는 이 값과 큰 쪽을 쓴다. 노드 검사 `estLabelW = textUnits×6.8 > width+6`이면 라벨 문제 | 코드 확인 + 실행 확인(T-08) |
| R-07 | v2 레인·캔버스 높이 | 공유 높이 `laneH = 30 + max(74, ceil(2×max(h/2+|yOffset|)+8))`. "세로 스택"(같은 레인·같은 열에 서로 다른 `yOffset` 둘 이상)이 있고 `meta.viewBox`·절대 핀이 없으면 레인마다 자기 노드로 측정(`laneBaseHeights`). 그룹 예약: 레인의 group마다 group 열 범위의 노드에 대해 `header = max ceil(minTop − topOffset)`(`minTop` = 라벨과 가로로 겹치면 11 아니면 9, `topOffset = (baseContentH−h)/2+yOffset`), `footer = max ceil(1 − (baseContentH−4−topOffset−h))`. 레인 높이 = 기본+header+footer. 레인 간격 `max(20, ceil(laneGapMin))`. 자동 높이 `52 + Σ레인높이 + (n−1)×간격 + 124 + 범례 추가 높이`, 범례 y `lastLaneBottom+44+범례 추가`. 범례는 `minimumCanvasWidth = max(defaultViewBoxWidth, 한 줄 minWidth+40)`로 포장 폭 `−40`을 정해 줄 수를 구한다(v1은 추가 높이 0) | 코드 확인 + 실행 확인(T-06, T-07) |
| R-08 | 노드 측정 | `width = node.width ‖ 자동 폭(v2) ‖ 92`, `height = node.height ‖ (tag?68:52)`, `cx = colXs[col]`, `contentH = 레인높이−30−groupHeader−groupFooter`, `y = laneTop+30+groupHeader+(contentH−height)/2+yOffset`, `x = cx−width/2`. `laneTop(i)=52+Σ앞 레인 높이+i×간격`. 노드는 장애물 격자(셀 160)에 `node`로 등록된다 | 코드 확인 + 실행 확인(T-01) |
| R-09 | v2 라우팅 전 검사 | `validateReadableInputsBeforeRouting`: 레인 id 중복 → 노드 id 중복 → edge 끝점 → 노드 lane → 열 범위 → 비유한 기하 순으로 저작 순서의 첫 위반 하나를 던지고, 겹침만 모든 쌍을 한 번에 던진다(F 표). 같은 입력의 `supportedFixes`는 후보를 `acceptsFix`로 검증해 만든다(R-22) | 코드 확인 + 실행 확인(T-15, T-17) |
| R-10 | 변 선택 | v2 자동 edge(`via`/`channel*` 없음, route auto, 양쪽 side 지정 아님)는 변 쌍 순서 `[v1식 one-bend 변 쌍, (저자 지정 또는 `legacyDefault`) 변 쌍, 4×4 조합(right, bottom, left, top 순; 저자 지정 쪽은 고정)]`에서 중복을 뺀 목록을 만들고, 첫 쌍에서 후보가 하나라도 실행 가능하면 그것, 아니면 모든 쌍의 후보를 비용 순으로 정렬해 첫 후보의 변 쌍을 쓴다. 결과는 `readableSideCache`에 edge 객체 키로 저장. 못 구하면 `null`이고 `edgeSides`는 라벨 채널 edge면 `top/top`, 아니면 `chosenSide(저자, legacyDefault)`. `legacyDefaultFromSide`: `to.cx<from.cx`면 left, `>`면 right, 같으면 `to.cy>from.cy`면 bottom 아니면 top(`to`는 반대편). 포트: 같은 변·같은 노드에 자동 edge가 2개 이상이면 `automaticPortSpread`(gutter 16, 간격 최대 14, 상대 중심 좌표 순 정렬)로 퍼뜨림. 앵커는 변 중앙 | 코드 확인 + 실행 확인(T-21) |
| R-11 | 자동 라우트 계획 순서 | `validateReadablePinnedGeometry`가 라우트를 처음 부르는 곳이다. (1) 절대 핀 edge 중 같은 끝점을 공유하는 핀 없는 edge가 있는 것을 먼저 `validateReadableRouteControls`+`pathFor`. (2) edge 어디에도 `labelAt/labelDx/labelDy/labelSegment`가 없을 때만, 독립 자동 edge(핀·route·side·labelAt 없음)가 "맞은편 직선이 청결"하면 그 직선 계획을 먼저 예약(`clearStraightAutomaticPlan`: 점 정렬+무관 노드 통과 안 함, role이 main이 아닌 return이 먼저 안 놓인 main 역방향이면 제외, 일반 계획기에서 점 2개가 나올 때만). (3) 피드백 `routeFirst` 인덱스(원본 인덱스) edge를 먼저. (4) 나머지를 정규 순서로 `validateReadableRouteControls`+`pathFor`. 이후 `validateWorkflow`의 `pathFor`는 캐시를 읽는다. 놓인 라우트는 `registerRouted`로 격자(`route`, `label`)·노드별 라우트 맵에 등록되어 뒤 edge의 검사·비용에 쓰인다 | 코드 확인 |
| R-12 | 후보 선택 | 한 변 쌍·포트 조합마다 1.3 E의 17개 후보를 만들어 12개 검사를 통과한 것에 비용을 매기고 사전식 정렬한다. `readableAutomaticRoute`는 (a) `fromSide/toSide` 둘 다 저자 지정이 없고 `labelAt`도 없고 자연 포트의 맞은편 직선(`aligned-facing`)이 실행 가능하면 비용 −1 순번으로 후보에 넣고 (b) 변 쌍마다(주 쌍 먼저) 후보를 모으고, 포트 후보가 둘 이상(`automaticPortCandidates`)이면 포트 조합 대안도 모으고 (c) 주 쌍에 후보가 없으면 `readableAutomaticVia`의 확장 결과를 `outside-right` 가족으로 넣는다. 최종 순서는 정렬 후 R-13의 수리 후보를 더해 다시 정렬한 첫 번째다 | 코드 확인 |
| R-13 | 수리 후보(순서) | 정렬 뒤 순서대로 후보를 더하고 매번 재정렬한다. (1) 굽이점이 무관 라우트에 닿고 교차가 없는 계획 최대 4개에 `automaticEndpointRepairs`(끝점 포트를 −8, +8, −10, +10 미끄러뜨림, 노드 변 안쪽 16 안, 후보 검사·비용 재검사, 교차 0·접촉·공유 코리도 비악화, 새 이웃과 코리도 없음, 화살촉 충돌 없음). (2) `readableInternalDetourPlans`: 같은 열이고 경로가 직접 거리의 2배 초과이며 64 초과 우회일 때 노드 측면 ±8 트랙 최대 24개. (3) 최상위 계획의 공유 코리도 > 0이면 서로 다른 변·끝점 계획 최대 8개 씨앗에서 안쪽 구간을 ±16, ±32 이동한 후보 중 비용이 줄어드는 최선 하나. (4) 끝점 수리. (5) 그래도 공유 코리도 > 0이면 좁은 슬롯 끝점 수리(구간당 최대 4곳). (6) `readableFreeSpacePlans`: 레인이 다르고 `labelDx/labelDy/labelSegment/bias`가 없고 공유 코리도·교차·접촉 중 하나가 있을 때, 변 쌍 4개(세로, left-left, right-right, 현재)별로 `shortestOrthogonalGridRoute`(C-31)를 호출. 장애물은 노드(패딩 8)·라벨·장면 머리말(4)·다른 라우트 구간(8), 끝 토막 16, 굽힘 벌점 24, 장애물 200개·격자 노드 25600 한도, `accept`는 실행 가능+교차·접촉·공유·라벨간격 0 | 코드 확인 |
| R-14 | 실행 가능 후보 없음 | `readableAutomaticVia`가 (1) 후보가 있으면 비용 최선. (2) 없으면 `outside-right` 확장: 라벨이 노드·라벨·라우트와 겹치는 만큼 `outsideRight`를 `+deficit×2`씩 밀고, 성장폭 `max(32, 라벨폭, 가장 오른쪽 배치+16−x)`로 최대 7번 탐색(성장폭 2배씩), 실행 가능해지면 이분법(최대 53번, 0.001까지)으로 가장 왼쪽 x를 구한다. (3) 그래도 없으면 절대 핀이 어딘가 있을 때 라벨·라우트 핀 충돌 분류(R-16, `classifyFailedAutomaticCandidatePins`). (4) 가로로 마주 보는 변 쌍이고 열이 다르며 `요구 간격 = w₁/2+32+w₂/2`가 실제 열 간격보다 크면 `rank-gap-minimum` 피드백 요청. (5) 레인이 다르고 `laneGap<32`이면 `lane-gap-minimum`(32) 피드백 요청. (6) 아니면 `workflow/solver-budget-exhausted`(`evidence.attemptedCandidateFamilies` 17개, `candidateCount`). `readableAutomaticRoute`는 변 쌍 전체에서 계획이 하나도 없을 때 피드백(우선순위 rank-gap→lane-gap→쌍 순번)을 던지고, 저자 변이 있으면 `explicit-pin-conflict`(`readable route feasibility with authored endpoint sides`), 아니면 첫 실패를 그대로 던진다 | 코드 확인 + 실행 확인(T-18: 자기 연결). 피드백 요청 경로는 입력을 못 찾아 코드 확인만 |
| R-15 | 프리셋·via·channel | `via`가 있으면 그것(`normalize` 없이). `route`가 `auto`가 아니고 `channel*` 없으면 `readablePresetVia`: `straight` 중간점 없음, `drop` `y=gapYBetween(bias ?? 0.5)`의 `[[sx,y],[ex,y]]`, `outside-right` `x=laneX+laneW+12`, `return-left` `x=min(from.x,to.x)−28`, `bottom-channel` `y=max(두 노드 bottom)+32`, `up-channel` `y=min(두 노드 top)−28`(앞의 둘은 `[[x,sy],[x,ey]]`/`[[sx,y],[ex,y]]` 꼴). 후보가 12개 검사를 통과하고 `routeMatchesPresetFamily`면 채택(`drop`은 같은 레인이면 불가). 아니면 `route-preset-conflict`: 첫 실패 사유(`node clearance`면 노드·구간·끝점 역할·여유 포함, `placed edge-label clearance`면 충돌 상세, `readable segment rhythm`이면 구간 번호·실제·요구 길이), `supportedFixes`는 (`edge-label node clearance`이고 라벨 핀 없으면) `labelSegment` 0~2 중 검증된 하나, 다른 프리셋 5개, 프리셋 제거 중 `acceptsFix`를 통과한 것. 핀 없는 프리셋(`controlled`)은 `readableControlledRoute`가 변 쌍을 열거하며 실행 가능·프리셋 가족 일치·channel 핀 포함 후보 중 비용 최선을 택하고, 없으면 절대 핀이면 진단용 후보, 프리셋만이면 위 충돌을 던진다. 프리셋과 `channel*` 호환: `drop`/`bottom-channel`/`up-channel`은 `channelY`만, `outside-right`/`return-left`는 `channelX`만, `straight`는 없음(어기면 `route preset compatibility` 핀 충돌) | 코드 확인 + 실행 확인(T-12, T-22) |
| R-16 | v2 핀 충돌 | `validateReadablePinnedGeometry`의 edge마다 순서: 원점 밖 라벨·via·channel → 핀 라우트면 유한 좌표 → 0길이 구간 → 대각선 → 직선 28/끝 8/안쪽 16 → `via`가 있으면 channel 핀 보존 → 프리셋 가족 → 끝점 변 방향 → 노드 통과 → 범례 → 머리말 → 프레임 테두리. `labelAt`이면 노드(−2)·범례·머리말과 겹침. 마지막으로 `validateReadablePairwisePinConflicts`: 라벨-라우트 간격 4(어느 한쪽이 핀일 때), 라벨끼리 −2, **showcase일 때만** 핀이 있는 라우트 쌍의 진짜 교차(끝점 공유 쌍 제외)와 8px 코리도 겹침. 모두 `workflow/explicit-pin-conflict`로 `evidence.invariant`는 R-16 표 문자열. `supportedFixes`는 핀 필드 제거 조합을 크기 1부터 전체 재컴파일로 검증해 처음 통과한 크기의 조합들이다(`labelAt` 단독 제거는 `labelAt` 이동 후보 8개 ±24, ±48 우선). `conflictingPins`는 그 조합의 필드(`edge, field, path, value`). 같은 이름의 자동 라우트 실패는 R-14(3) | 코드 확인 + 실행 확인(T-11, T-13, T-20) |
| R-17 | 라벨 위치 | 라벨 점은 `workflowEdgeLabelPoint`. v1: `labelAt`·`labelSegment`·점≠3이면 `labelPoint`, 아니면 긴 쪽 구간(`≥`면 0)의 `labelPoint`에 세로 구간이면 `y+10`. v2: (a) `labelAt`·`labelSegment` 정수·점 2개 이하는 `labelPoint`(점 2개: 중점 x+`labelDx`, `y₀−10+labelDy`; 3개↑: `labelSegment`(기본 1, 범위 자름) 구간 중점 `y−10+labelDy`). 다만 점 2개이고 세로이며 라벨 핀이 없으면 `x`(피드백 `fanInLabelClearance`이고 절대 기하 보존이 아니며 같은 도착 노드로 들어오는 다른 edge들이 모두 한쪽이면 반대쪽으로 `라벨폭/2+8` 옮김), `y`는 중점. (b) 그 외 점 3개↑: 구간을 (가로 우선, 긴 순, 인덱스 순)으로 정렬해 가장 긴 가로 구간 중점(세로 구간이면 `y+10`)이 기본. 그 구간 길이가 `라벨폭+8` 미만이고 노드와 겹치면 길이 28 이상인 다음 구간 중 노드와 안 겹치고 한 레인 안(레인 가장자리 4 안쪽)인 첫 것. 라벨 사각형 `{x=lx−w/2, y=ly−10, w, h14}`. 라벨이 있는 edge는 라우트가 등록될 때 격자에 `label`로 등록되고 이후 후보의 검사 9에서 장애물 | 코드 확인 + 실행 확인(T-01, T-05) |
| R-18 | `validateWorkflow` 순서 | (1) 구조 문제(스키마 버전, 배열 아님…) 있으면 즉시 던짐 (2) v1 `enforceLegacyColumnCapacity` (3) 문제 문장 수집: 레인·노드·phase·group id 중복, 노드 레인·열·비유한 기하·글자 문제(`workflowNodeTextProblems`: 라벨 `textUnits×6.8>width+6`, 브랜드 레일, sublabel·tag가 최소 6px로도 `width−8`에 안 듦)·레인 가로·세로 포함, phase 범위·라벨 폭(`textUnits×5.6 > span+8`)·겹침, group 레인·범위·빈 group, 같은 레인 8px 간격, edge 끝점·점 2개 직선 길이 <28 (4) `cleanEndpointSideProblems` → `cleanFlowProblems`(2px) → `cleanCrossingProblems` → `cleanAmbiguousCorridorProblems`(최소 겹침 8) → v2 화살촉 충돌 → `cleanBorderRunProblems` → `cleanRouteRhythmProblems`(showcase) (5) `mainPath`: 없는 id는 `workflow/unknown-endpoint`(후보 3개 검증), 쌍마다 edge 없음·`col` 감소 (6) 라벨 사각형이 노드와 −2 이하로 겹침, 라벨끼리 겹침, `cleanLabelRouteClearanceProblems`(임계 4, showcase) (7) v1이면 viewBox 폭·범례 높이·라벨 캔버스 포함 (8) 문제가 하나라도 있으면 `throwDiagnosticProblems('Workflow layout validation failed', 문제, {diagnostics: 기록된 workflow 진단})`. 상세가 있는 문장은 같은 문장의 진단 객체로, 없으면 `layout/constraint` | 코드 확인 + 실행 확인(T-16, T-20) |
| R-19 | viewBox 확정 | `finalizeReadableViewBox`(v1은 그대로). 콘텐츠 경계 초기값 `left=40, top=27, right=40+laneW, bottom=legendY+18`에 모든 노드 사각형, 라우트 점, 라벨 마스크, phase 띠(y 27, 높이 16), group 프레임과 라벨 마스크, 범례 사각형을 포함. `requiredViewBox = [max(minimumCanvasWidth, ceil(right+16)), max(autoHeight, ceil(bottom+18))]`. left 또는 top이 음수면 오류(절대 핀이 있으면 `explicit-pin-conflict`, 없으면 `solver-budget-exhausted`, `subject.path=/meta/viewBox`). `meta.viewBox`가 없으면 `viewBox = requiredViewBox`, 있으면 어느 축이든 작으면 `workflow/viewbox-capacity`(수정: 최소 크기로 설정, viewBox 생략 — 둘 다 `acceptsFix` 검증), 충분하면 저자 값 그대로 | 코드 확인 + 실행 확인(T-10) |
| R-20 | sublabel 가독 | `validateReadableNodeText`: 최소 글자 = 6, 단 v2·showcase·`meta.viewBox` 없음이면 `max(6, ceil(minimumReadableSourceTextPx(viewBox폭)×10)/10)` (= `6/min(1, 930/W)`). 최소가 8을 넘으면(`fontBudgetExceeded`) 또는 `sublabel` 최소 폭 `textUnits×최소×0.6`이 `width−8`을 넘으면 노드마다 `workflow/sublabel-readability`(`evidence`: `requiredFontPx, maximumSlotFontPx=8, canvasWidthPx, maximumCanvasWidthPx=1240, requiredTextWidthPx, availableTextWidthPx`). 렌더 글자 크기는 `fittedNodeFontSize`로 label 11→9, sublabel 8→`min(8, 최소)`, tag 7→6 | 코드 확인 + 실행 확인(T-19) |
| R-21 | 피드백 루프(바깥쪽) | 아래 순서이고 모두 컴파일러 안 이름. (1) `compileWorkflowWithFeedback`: 결과가 `ok`이거나 v1·showcase 아님·절대 기하 보존이면 첫 결과 반환. 아니면(showcase v2 핀 없음) 실패가 **전부** `sublabel-readability`이고 영수증이 `readable-v2`+노드를 가진 동안 반복: `minimum = max(requiredFontPx)`, `maximum = min(maximumSlotFontPx)`, `tick = round(minimum×10)`가 `minimumTick(초기 60)`보다 크고 80 이하여야 함. 저자 `width` 없고 sublabel이 있는 노드마다 현재 폭에서 모자라면 `width = min(200, ceil((필요폭+현재 폭−가용 폭)/4)×4)`를 `widthOverrides`에 넣고 문서 복사본으로 `compileWithLayoutFeedback`을 빈 피드백으로 다시 한다. (2) `compileWithLayoutFeedback`: `attempt=0..3`(최대 4번) 컴파일, `WorkflowLayoutFeedback`을 받으면 `rank-gap-minimum`이면 `rankGapMinimums["from:to"]`를 더 큰 값으로(이미 같거나 크면 포기), `lane-gap-minimum`이면 `laneGapMin`을 올려 다시. 새 값이 없거나 마지막 시도면 `feedbackFailure`(`solver-budget-exhausted`, 후보 가족 증거). (3) `compileWithRouteOrderFeedback`: v2에서 결과의 오류가 있고 **전부** `composition/ambiguous-corridor`·`proper-crossing`이면 두 edge 중 정규 순서가 뒤인 원본 인덱스를 `routeFirst`에 더하고 `fanInLabelClearance:true`로 다시(최대 3번). 오류 수가 줄거나 R-20 에포크가 고칠 수 있는 sublabel 오류만 남으면 그 결과를 채택(문서는 안 바뀜). (4) 마지막 껍질 `addVerifiedCrossingRepair`(오류가 전부 `proper-crossing`, 절대 기하 보존 아님: 두 edge의 `fromSide/toSide/route`를 각각·함께 제거해 컴파일해 보고 통과하면 `evidence.verifiedRepair`와 `supportedFixes` 앞에 문구 추가), `addVerifiedPlacementRepair`(showcase v2, 오류가 전부 ordering 코드이고 이미 `verifiedRepair` 없음: `proposeWorkflowPlacement`, C-32의 `col`·`yOffset` 제안을 컴파일로 검증해 통과하면 같은 방식으로 덧붙임) — 결과 `ok`/기하는 바꾸지 않는다 | 코드 확인 |
| R-22 | 수리 후보 검증 | `acceptsFix(mutator)`: `discoverFixes`가 꺼져 있으면 항상 거짓. 문서 복사본에 변경을 적용해 `compileWorkflowWithFeedback({discoverFixes:false})`가 `ok`인지로 판정(진단 기록은 억제). 키는 문서 JSON, 캐시 128개까지. 진단에 붙는 `supportedFixes`·`evidence.verifiedRepair`는 이렇게 통과한 것만이다. 기하·acceptance에는 영향이 없다 | 코드 확인 |
| R-23 | 영수증·`--layout-json` | `measuredPlanReceipt` 형식은 1.3 A. 완전한 계획(`hasCompleteMeasuredPlan`: 노드·라우트 수 일치, 유한 좌표, 라벨 사각형 존재)에서 검증이 실패하면 같은 형식에 `ok:false`를 붙인다. 성공 영수증의 `diagnostics`에는 warning이 들어 있다(예: `composition/proper-crossing`). 솔버 반복·후보 점수는 영수증에 없다 | 코드 확인 + 실행 확인(T-10, T-20) |
| R-24 | SVG | 루트 `<svg viewBox="0 0 W H" [data-reader-fit="width-first"] [data-layout-contract="readable-v2"] …svgRootAttrs data-node-ui="">`. `width-first`는 v2·`meta.viewBox` 없음이고 (세로 스택이 있고 어떤 레인 높이가 104 초과) 또는 `predictedFixedWidthOverflow`(viewBox 폭/높이 비율이 1.55 미만이고, 1440×900 데스크톱에서 SVG 폭 `1440−64−30=1346`일 때의 높이 `round(1346×H/W)`에 고정 크롬 `12+39+75=126`을 더한 값이 900 초과). 자식 순서: `<title>/<desc>`, `renderDefinitions`, `nodeCardStyle`, 배경 격자 사각형, 레인(+exception 프레임, 라벨), phase, group, **edge 경로(정규 순서)**, 노드, edge 라벨, 범례. 레인 `rx 10`, 경로 `roundedWorkflowPath`(반지름 8에서 `(길이−8)/모서리수`로 줄임), 속성 `data-composition-points`, 독립 자동 edge(v2)는 `data-composition-routing="workflow-v2-auto"`, v2는 `data-edge-role`. 선 클래스·마커는 variant별 `arrowClassMap`, 굵기 `width ?? (emphasis 1.8 : 1.4)`. phase: 가는 선 y 35(x+8~x+폭−8)와 `rx 8` 라벨 칩(y 27, 높이 16, 글자 y 38.5, 8px). group: `rx 9`, 라벨 `x+10`, y는 v2 `frameY−2`, v1 `frameY+14`, 프레임 높이 v2 `레인높이−30−8−4`, v1 `104−30−16`. 노드: 마스크·색 사각형(`rx 8`, 선 1.5)·의미 심볼·브랜드·label(y 21, 굵기 600, 최소 9)·sublabel(y 38)·tag(y h−12), `focusNodeAttrs`. 범례는 R-19의 범례 사각형과 같은 배치이고 `meta.legend` 없으면 안 들어갈 때 숨김, 있으면 `legend/*` 오류 | 코드 확인 + 실행 확인(T-28) |
| R-25 | v1→v2 마이그레이션 좌표 | `migrate workflow … --to-schema 2`는 v2 계획의 열 중심 배열을 구해 v1 열 중심(`[88,220,300,430,500,625]`)에서 그 열로 가는 **조각별 선형 사상**(`x ≤ 88`이면 첫 구간, 그 이상은 `x ≤ 다음 중심`인 첫 구간, 밖은 마지막 구간 외삽, 소수 6자리 반올림)을 만들어 모든 `via[*][0]`, `labelAt[0]`, `channelX`에 적용하고 y는 그대로 둔다. 계획은 `intrinsicWorkflow`(`viewBox` 제거, 정책 심볼 보존) → 실패하면 `planningWorkflow`(라우트가 있는 edge·`labelAt` 있는 라벨 제거, 영향 받는 `semanticChecks`·`mainPath` 제거). 마이그레이션 결과가 컴파일에 실패하면 목적 파일을 쓰지 않는다. `workflow/column-capacity`의 "migrate" 수정 문구는 이 계획을 `discoverFixes:false`로 재컴파일해 통과할 때만 붙는다 | 코드 확인 + 실행 확인(T-25) |
| R-26 | 결정성 | 같은 문서·같은 프로파일이면 영수증과 SVG가 같다. 정렬은 정규 순서(`stableCompare`)이고 후보 순번이 마지막 동률 규칙이다 | 실행 확인(T-27) / 추론(시계·난수 전수 확인은 안 함) |
| R-27 | v1 라우트·검사 | v1은 자동 폭·후보 비용·피드백이 없다. 변: `legacyAutomaticOneBendSides`(자동, 레인이 다르고 중심 x·y 둘 다 다를 때 `{세로 먼저}` 두 쌍 중 첫 실행 가능), 아니면 `chosenSide(저자, legacyDefault)`. `via` 없고 자동이면 같은 레인 `sameLaneAutoVia`(중점 x 두 점, 정렬되면 없음), 다른 레인 one-bend 코리도 아니면 `gapYBetween` 코리도 `[[sx,y],[ex,y]]`(`bias` 기본 0.5). 점은 정규화하지 않는다. 구조화 code 대신 `layout/constraint` 문장을 쓰는 위반: 중복 id, 알 수 없는 끝점·레인, 같은 레인 8px 겹침(+ 따라오는 `clean-flow/endpoint-side-direction`), 노드 글자, phase·group·mainPath | 코드 확인 + 실행 확인(T-02, T-30) |

R-16 `evidence.invariant` 문자열 전체: `viewBox-origin containment`, `finite route coordinates`, `non-zero route segments`, `orthogonal route segments`, `8px endpoint stub clearance`, `16px interior turn clearance`, `channel pin preservation`, `route preset compatibility`, `perpendicular endpoint-side direction`, `node clearance`, `legend clearance`, `lane/phase/group label clearance`, `structural-frame border clearance`, `edge-label node clearance`, `edge-label legend clearance`, `edge-label lane/phase/group clearance`, `explicit label-route clearance`, `explicit label-label clearance`, `explicit route-route crossing`(showcase), `explicit route-route corridor clearance`(showcase), `readable route feasibility with authored endpoint sides`.

- 불변식: (1) v1 문서는 v2 규칙으로 해석되지 않고 v1 출력은 같은 입력에서 바이트가 보존된다(README 계약, 컴파일러에 v1 분기가 따로 있음). (2) 성공 `receipt`의 모든 좌표는 유한하고 `viewBox ≥ requiredViewBox`이다(`meta.viewBox`가 없으면 같다). (3) 컴파일러는 입력 문서를 바꾸지 않는다. (4) 정렬 때문에 v2 SVG의 edge 순서는 저작 순서와 다를 수 있고, 진단 인덱스는 원본 기준이다.
- 미결정: **이 스펙 자체의 미결정 없음.** 읽은 범위: `render-workflow.mjs`·`workflow-compiler.mjs`·`workflow-migration-geometry.mjs`·`workflow-placement-repair.mjs`·`README.md` 전부, 컴파일러가 부르는 공유 helper(`geometry.mjs`의 앵커·열 정규화·게이트·라벨 간격, `route-quality.mjs`의 `shortestOrthogonalGridRoute`, `legend.mjs`, `text-fit.mjs`, `desktop-readability.mjs`, `spatial-grid.mjs`) 전부. 선행 [rendering.md](rendering.md)가 draft라 `status`는 draft이다.
- 확인 한계: (1) `rank-gap-minimum`·`lane-gap-minimum` 피드백과 `routeFirst` 재시도, `outside-right` 확장, 수리 후보(R-13)는 그 경로를 타는 입력을 찾지 못해 실행으로 확인하지 못했다(코드 확인). (2) `supportedFixes` 문구 전체와 `verifiedRepair` 내용은 동작(검증 방법)만 쓰고 모든 문구는 코드 참조(C-12). (3) 진짜 교차·모호 코리도·화살촉 충돌의 showcase 오류는 자동 라우트로는 만들지 못했다(자동 계획이 교차를 피함). 핀으로 만든 교차는 실행했다(T-20). (4) 브라우저 렌더 결과·시각 품질은 보지 않았다.

### 1.5 필수 코드 참조 [필수]
기준은 frontmatter SHA. 라이선스는 Apache-2.0(overview 1절). 줄 범위는 모두 `archify/renderers/` 기준.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `workflow/render-workflow.mjs:1-47` | 렌더러 흐름: 로드, 격리된 컴파일, 진단 재기록, `--layout-json`, 쓰기 | R-01 |
| C-02 | `workflow/workflow-compiler.mjs:80-136` `LEGACY_COLUMN_CENTERS`, `READABLE_CANDIDATE_COST_PRIORITY`, 그룹 상수, `HARD_ROUTE_RHYTHM`, `hardRouteSegmentMinimum`, `createLegacyLayout` | v1 상수, 비용 우선순위(1.3 E 표), 리듬 상수 | R-04, R-12 |
| C-03 | `workflow-compiler.mjs:138-231` | 절대 핀 판정, 세로 스택, 레인 독립 측정, 자동 노드 폭, 라벨 폭, 그룹 경계, 세로 구간 겹침 | R-05~R-07 |
| C-04 | `workflow-compiler.mjs:233-661` `createReadableLayout` | 열 제약 수집·풀이·보정·레인 폭·높이·그룹 예약(1.3 D의 식을 코드로) | R-05, R-07 |
| C-05 | `workflow-compiler.mjs:663-739` | `compilerFailure`, 정렬 helper, `canonicalReadableWorkflow` | R-03 |
| C-06 | `workflow-compiler.mjs:741-856` `semanticContractDiagnostics` | 의미 검사 5종과 `supportedFixes` 문구 | R-03 |
| C-07 | `workflow-compiler.mjs:858-1059` | 범례 발자국, 레인 기하(`laneTop`, `legendY`, 자동 높이), 노드 측정, 글자 문제, 단계 인덱스 | R-07, R-08, R-18 |
| C-08 | `workflow-compiler.mjs:1064-1233` `createLegacyCapacityRepair` | v1 열 용량 게이트와 수정 후보 | R-04 |
| C-09 | `workflow-compiler.mjs:1238-1360` `createAutomaticSideSelection` | 자동 변 쌍 선택 | R-10 |
| C-10 | `workflow-compiler.mjs:1362-1452` | 컴파일 입구, 스키마·의미·레이아웃 순서 | R-03 |
| C-11 | `workflow-compiler.mjs:1454-1578` | 범례 사각형, 장애물 격자, 구조 프레임, 머리말 장애물 | R-11, R-16 |
| C-12 | `workflow-compiler.mjs:1580-1840` | `acceptsFix`, 수정 후보 검증 helper 전부 | R-22 |
| C-13 | `workflow-compiler.mjs:1847-2191` | 핀 충돌 던지기, 라벨·라우트 핀 충돌, 쌍 검사 | R-16 |
| C-14 | `workflow-compiler.mjs:2193-2376` | 프리셋 핀 호환표, 방향 판정, 프리셋 가족 판정, 직선 예약 | R-11, R-15 |
| C-15 | `workflow-compiler.mjs:2378-2691` `validateReadablePinnedGeometry` | 라우트 첫 계획 순서와 핀 불변식 검사 | R-11, R-16 |
| C-16 | `workflow-compiler.mjs:2693-3036` `validateWorkflow` | 문제 문장 수집 순서와 게이트 호출 인자 | R-18 |
| C-17 | `workflow-compiler.mjs:3038-3257` | 라우팅 전 입력 검사 | R-09 |
| C-18 | `workflow-compiler.mjs:3259-3388` | span 계산, 장애물 질의, one-bend | R-10, R-18 |
| C-19 | `workflow-compiler.mjs:3390-3748` | 후보 12개 검사와 라벨 간격·프리셋 거절 사유 | R-12, R-15 |
| C-20 | `workflow-compiler.mjs:3750-3976` | 코리도 via, 비용 계산과 보조 지표, `compareCost` | R-12 |
| C-21 | `workflow-compiler.mjs:3978-4364` | 후보 집합, `outside-right` 확장, 피드백 요청, 프리셋·`routeVia` | R-12, R-14, R-15 |
| C-22 | `workflow-compiler.mjs:4366-4464` | 라벨 점, `edgeSides` | R-10, R-17 |
| C-23 | `workflow-compiler.mjs:4466-4934` | 포트 후보, 끝점·우회·자유공간 수리, `readableAutomaticRoute` | R-12, R-13 |
| C-24 | `workflow-compiler.mjs:4936-5126` | 제어 라우트, `registerRouted`, `pathFor` | R-11, R-15 |
| C-25 | `workflow-compiler.mjs:5130-5311` | 라벨 사각형, 콘텐츠 경계, viewBox 확정 | R-17, R-19 |
| C-26 | `workflow-compiler.mjs:5313-5517` | SVG 조립(레인·phase·group·노드·edge·범례) | R-24 |
| C-27 | `workflow-compiler.mjs:5520-5644` | 완전 계획 판정, 영수증, 절대 기하 크기 경고, 최종 `try/catch` | R-19, R-20, R-23 |
| C-28 | `workflow-compiler.mjs:5646-5920` | 피드백 실패, 라우트 순서·열 피드백·sublabel 에포크, 두 수리 껍질, `compileWorkflow` | R-21 |
| C-29 | `workflow/workflow-migration-geometry.mjs:1-161` | 정책 심볼, 계획 투영, 조각별 선형 사상, 매핑 후보 | R-05, R-25 |
| C-30 | `shared/geometry.mjs:10-100,318-386,1332-1371,1517-1526,1703-1781,1800-1816,1818-1880,1882-1927` | 사각형·구간 helper, 끝점 변 규칙, `joinRoutePoints`/`normalizeRoutePoints`, `anchor`, `automaticPortSpread`, 기본 변, `polylinePath`, `roundedPath`, `labelPoint`, 색·화살표 표 | R-10, R-17, R-24 |
| C-31 | `shared/route-quality.mjs:10-33,104-118,174-198,260-465,466-540`, `shared/spatial-grid.mjs:1-66` | 격자 최단 경로 탐색(좌표 모음·병합·bend 벌점 상태 탐색·수락 콜백)과 균일 공간 격자 | R-13 |
| C-32 | `workflow/workflow-placement-repair.mjs:1-94` | 선택적 노드 배치 제안(적격 조건, 열·yOffset 규칙) | R-21 |
| C-33 | `shared/legend.mjs:5-11,13-33,35-110,111-203,204-227` | 범례 항목 선택·폭·줄 포장·발자국·배치·충돌 진단 | R-07, R-24 |
| C-34 | `shared/geometry.mjs:206-270,388-531,532-626,627-862,863-1005,1070-1197,1302-1325,1397-1515` | 공유 게이트(라벨 간격, 끝점 방향, 노드 관통, 교차, 코리도, 화살촉, 테두리, 리듬)와 선분 helper | R-16, R-18 |
| C-35 | `shared/text-fit.mjs:24-52`, `shared/desktop-readability.mjs:1-35,88-132`, `shared/utils.mjs:239-260` | 글자 폭 단위·폭 계수·가독 한계·고정 폭 넘침 예측 | R-06, R-20, R-24 |

### 1.6 수락 사례 [필수]
출처: 모두 실행 관찰이다. 설치본 `archify validate workflow <json> --layout-json`(`--quality`·`migrate`·`render`는 해당 사례에 표기). 입력은 [make-inputs.py](../../../artifacts/archify/spec-demos/rendering/workflow/make-inputs.py)가 만들고 `in/`에 있다. 재실행 `sh demos.sh`, 요약 [summary.txt](../../../artifacts/archify/spec-demos/rendering/workflow/summary.txt), SVG 조각 [render-slices.txt](../../../artifacts/archify/spec-demos/rendering/workflow/render-slices.txt). 레포 clone 안의 코드는 실행하지 않았다. 아래 입력 이름은 `in/<이름>.json`.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-05 R-08 R-17 | `w01-v2-base`: 레인 `L1,L2`, 노드 a(L1,0)·b(L1,1)·c(L2,2), edge `a→b`(label "go")·`b→c`, viewBox 없음 | 종료 0, 계약 `readable-v2`, 열 `[94,224,344,464,584,704]`(0→1이 130 = 46+38+46), viewBox 778×404, a `x48 y93 92×52`, b `x178`, c `x298 y217`, `a→b` `[[140,119],[178,119]]`, `b→c` `[[224,145],[224,243],[298,243]]`, 라벨 "go" `(159,109)` 폭 30 |
| T-02 | R-02 R-04 R-27 | `w02-v1-base`: T-01과 같고 `schema_version:1` | 계약 `fixed-v1`, 열 `[88,220,300,430,500,625]`, viewBox 720×404, `a→b` `[[134,119],[174,119]]`, `b→c` `[[220,145],[220,243],[254,243]]`, 라벨 `(154,109)`. `render`한 SVG 루트에 `data-layout-contract` 없음 |
| T-03 | R-04 | `w03-v1-column-capacity`: v1, 같은 레인 b(col1)·c(col2), edge `b→c` | 종료 1, 진단 하나 `workflow/column-capacity`: `Workflow columns 1→2 place nodes "b" and "c" so they overlap by 12px under the fixed-v1 layout.` |
| T-04 | R-05 | `w04-v2-same-shape`: T-03과 같은 모양, `schema_version:2` | 종료 0, 열 `[94,218,342,462,582,702]`(124 = 46+32+46), viewBox 776×404, `b→c` `[[264,119],[296,119]]` |
| T-05 | R-05 R-17 | `w05-v2-long-label`: T-01의 `a→b` 라벨을 "a rather long relationship label"(32자)로 | 종료 0, 열 `[94,218,338,458,578,698]`, viewBox 772×404. 직접 간격 팽창 비용 `163.6+8−28=143.6 > 112`라 라벨 채널을 선호해 열 간격을 키우지 않고 `a→b`가 `[[94,145],[94,172],[218,172],[218,145]]`로 돌아가며 라벨 `(156,162)` 폭 163.6 |
| T-06 | R-07 R-24 | `w06-v2-stack`: 레인 1, group 1(cols 1~3), 노드 3개가 같은 열 2에서 `yOffset −90/0/90`, edge는 bottom→top, viewBox 없음. `render` | 레인 높이 276, viewBox 768×452, 노드 y `91/181/271`, SVG 루트에 `data-reader-fit="width-first"`, group 프레임 `x164 y90 w340 h234` |
| T-07 | R-05 R-07 | `w07-v2-phase-group`: phase 라벨 38자(단일 열 0)와 group 라벨 24자(레인 L1, 열 1) 추가 | 열 `[94,342.8,517.2,637.2,757.2,877.2]`(0→1 `120+(220.8−92)=248.8`, 1→2 `120+(154.4−100)=174.4`), viewBox 952×404, group 프레임 `x292.8 y90 w154.4 h62` |
| T-08 | R-06 | `w29-auto-width`: a의 라벨 24자, b의 sublabel 30자, 폭 미지정 | a 폭 160, b 폭 152, 0열이 첫 열 반폭 80 때문에 `128`로 이동 → 열 `[128,322,442,…]`, viewBox 876×404 |
| T-09 | R-05 | `w31-lane-header-shift`: L1 레인 라벨 39자, edge `a→c`에 `fromSide:top, toSide:top` | 머리말 오른쪽 `54+44×6.2=326.8`, +2 → 열 시작 `328.8`(`[328.8,452.8,572.8,692.8,812.8,932.8]`), viewBox 1007×404, `a→c` `[[328.8,93],[328.8,36],[572.8,36],[572.8,217]]` |
| T-10 | R-19 R-23 | `w41-explicit-viewbox-ok`(viewBox `[900,500]`) / `w12-viewbox-capacity`(`[700,240]`) | 앞: 종료 0, `viewBox [900,500]`, `requiredViewBox [778,404]`(저자 값 그대로). 뒤: 종료 1, `workflow/viewbox-capacity` `…cannot contain the readable-v2 layout; minimum 778×404.`, 영수증에 `ok:false`와 완성 기하 |
| T-11 | R-16 | `w10-pin-labelat-on-node`: `a→b`에 `labelAt [94,120]`(a 위) | `workflow/explicit-pin-conflict`, `invariant:"edge-label node clearance"`, `labelRect {x79,y110,w30,h14}`, `obstacleNode:"a"`, 수정 `remove labelAt so readable-v2 can use its verified automatic label placement` |
| T-12 | R-15 | `w11-preset-drop-same-lane`: 같은 레인 `a→b`에 `route:"drop"` | `workflow/route-preset-conflict`, `invariant:"perpendicular endpoint-side direction"`, 후보점 `[[140,119],[140,104],[172,104],[172,119]]`, 요구 8/16/28, 수정에 `straight`·`bottom-channel` 프리셋과 route 제거 |
| T-13 | R-16 | `w13-pin-via-diagonal`: `b→c`에 `via [[300,200]]` | `explicit-pin-conflict`, `invariant:"orthogonal route segments"` |
| T-14 | R-03 | `w14-semantic`(allowedRoots [b], allowedTerminals [c], requiredEdges c→a, requiredPaths c→a) / `w15`(allowedRoots ["zzz"]) | 앞: code 순서 `unexpected-root`(a), `required-edge`, `required-path`. 뒤: `workflow/semantic-node-reference`만(`/semanticChecks/allowedRoots/0`) |
| T-15 | R-09 R-27 | `w16-node-overlap`(v2, 같은 레인 같은 열 두 노드) / `w44`(v1 같은 입력) | 앞: `workflow/node-overlap` 하나. 뒤: `layout/constraint`(8px 문장)와 `clean-flow/endpoint-side-direction`이 함께 나오고 영수증은 `ok:false` 기하 포함 |
| T-16 | R-18 | `w17-constraint-problems`: mainPath `[b,a]`, 노드 없는 group, 겹치는 phase 둘 | 종료 1, 전부 `layout/constraint`이고 순서가 phase 겹침 → 빈 group → mainPath edge 없음 → mainPath 뒤로 감. 영수증 `ok:false`(기하 포함) |
| T-17 | R-03 R-09 | `w21`(`b→zz`), `w22`(lane "nope"), `w23`(id 중복), `w24`(col 9) | `workflow/unknown-edge-endpoint`, `unknown-node-lane`, `duplicate-node-id`; `w24`는 stdout 비어 있고 stderr에 `[schema/maximum] /nodes/2/col … must be <= 5`(스키마가 막아 `invalid-node-column`은 안 나옴) |
| T-18 | R-14 | `w33-self-loop`: edge `a→a` | `workflow/solver-budget-exhausted`, `evidence.candidateCount:17`, 가족 목록은 1.3 E의 17개 순서 |
| T-19 | R-20 R-21 | `w34`(showcase, T-07의 폭 952 캔버스, a 폭 92 저작, sublabel 23자) / `w35`(같은 입력에서 폭만 뺌) | 앞: 종료 1, `workflow/sublabel-readability`, `requiredFontPx 6.2`, `requiredTextWidthPx 85.56`, `availableTextWidthPx 84`, `maximumCanvasWidthPx 1240`. 뒤: 종료 0, a 폭이 `ceil((85.56+8)/4)×4=96`으로 확대되고 viewBox 954×404 |
| T-20 | R-16 R-18 R-23 | `w37`(핀으로 교차하는 두 edge, standard) / `w38`(showcase) / `w37 --quality showcase` | 앞: 종료 0, 영수증 `diagnostics`에 `composition/proper-crossing` warning(점 `[334,165]`). 중간·뒤: 종료 1, `explicit-pin-conflict`, `invariant:"explicit route-route crossing"`(환경 변수가 문서 값보다 우선) |
| T-21 | R-10 | `w25-authored-sides`: `a→b`에 `fromSide:left,toSide:right`(b는 오른쪽) | 종료 0, 경로 `[[48,119],[32,119],[32,172],[286,172],[286,119],[270,119]]`(저자 변을 지키며 노드를 돌아감) |
| T-22 | R-15 | `w26-routes`: a(L1,1), b(L2,3), c(L2,4); `auto`, `drop`(bias 0.25), `return-left`(b→a) | 종료 0, `auto` `[[214,145],[214,243],[408,243]]`, `drop` `[[214,145],[214,161],[578,161],[578,217]]`(y=156+20×0.25), `ret` `[[408,243],[140,243],[140,119],[168,119]]`(x=168−28). 영수증에 `composition/ambiguous-corridor` warning(`auto`와 `ret`이 194px 공유) |
| T-23 | R-15 | `w30-pinned-via-ok`: `b→c`에 `via [[284,119],[284,243]]` | 종료 0, `b→c` `[[270,119],[284,119],[284,243],[298,243]]`(핀이 있어 노드 간격 8 규칙, 열 `[94,224,344,…]`, via는 정규화 안 됨) |
| T-24 | R-12 | `w18`·`w19`: 자동 `a→d`와 `b→c`(서로 엇갈림), standard / showcase | 둘 다 종료 0, 같은 경로: `e2`가 `[[264,119],[280,119],[280,296],[94,296],[94,269]]`로 돌아가 교차를 피한다(진단 없음) |
| T-25 | R-25 | `w40-v1-via`(v1, `b→c` `via [[220,166],[300,166]]`) `migrate … --to-schema 2 --json` / `w02` / 번들 `release-delivery`(v1) | 앞: 종료 0, `changedCoordinates` `/edges/1/via/0/0` 220→224, `/via/1/0` 300→344, 결과 문서에 viewBox 없고 v2 컴파일 성공. `w02`: `schema_version`만 다른 문서. `release-delivery`: 종료 1, `newSchemaDiagnostics`에 `workflow/route-preset-conflict`(`pull_request->build`, `drop`, `lane/phase/group label clearance`), 목적 파일 안 생김 |
| T-26 | R-02 | 번들 `agent-tool-call`(v2 showcase), `release-delivery`(v1 showcase) `validate --layout-json` | 앞: viewBox 1108×684, 열 `[114,278,495.2,659.2,838,1002]`, 노드 12, edge 11, 진단 없음. 뒤: 720×900, 열은 v1 고정, 노드 10·edge 10 |
| T-27 | R-01 R-26 | `w01`을 두 번 `--layout-json` | stdout 바이트 동일 |
| T-28 | R-24 | `render workflow in/w01…` 등 | v2 루트 `data-layout-contract="readable-v2"`, 자동 edge에 `data-composition-routing="workflow-v2-auto" data-edge-role=""`, `data-composition-points`; v1은 이 속성들 없음 |
| T-29 | R-04 | `w42-v1-viewbox-small`: v1, `viewBox [700,300]` | 종료 1, `layout/constraint` `Legend exceeds viewBox height 300 — set meta.viewBox[1] to at least 342.` |
| T-30 | R-27 | `w43`(v1 끝점 `zz`), `w45`(v1 레인 nope) | 둘 다 `layout/constraint`(v2의 구조화 code와 대비) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
읽은 범위: `workflow-compiler.mjs` 1~5920 전부(수정 후보 helper 1580~2191은 `acceptsFix` 중심으로 읽고 문구 목록은 훑음), 보조 모듈 세 개 전부, 스키마 전부, README 전부, 공유 helper는 위 C-30~C-35 범위.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01, C-28 `compileWorkflow` 5917-5920 | 코드 읽음. T-27 |
| R-02 | C-04 vs C-02, `compileWorkflowInternal` 1424-1426, 번들 예제 `schema_version` grep | 실행 확인(T-02, T-26) |
| R-03 | C-10 1381-1418, C-05, C-06 | 실행 확인(T-14, T-17) |
| R-04 | C-02, C-08 1178-1231, C-16 3011-3027, README "Fixed v1" 표 | 코드와 README 상수 일치 확인, 실행(T-02, T-03, T-29) |
| R-05 | C-04 233-415, C-29 `preservesWorkflowAbsoluteGeometry` | 식은 코드, 결과는 T-01 T-04 T-05 T-07 T-09 T-10 숫자로 대조(예: T-07 248.8, 174.4) |
| R-06 | C-03 171-178, C-27 5571-5606, C-28 | T-08 숫자 대조(160, 152) |
| R-07 | C-04 539-640, C-07 910-980 | T-06 숫자(276, 452) |
| R-08 | C-07 984-1019 | T-01 좌표 대조 |
| R-09 | C-17 | T-15 T-17 |
| R-10 | C-09, C-22 4447-4464, C-30 | T-21. `automaticPortSpread`의 상세는 C-30 코드 |
| R-11 | C-15 2378-2418, C-14 2336-2376, C-24 5061-5126 | 코드 확인. 직선 예약 효과를 입력으로 분리하지 않음 |
| R-12 | C-19, C-20, C-21 3978-4040, C-23 4693-4830 | T-24(교차 회피 경로) |
| R-13 | C-23 4503-4691, C-31 | 코드 확인. 해당 분기를 타는 입력을 못 찾음 |
| R-14 | C-21 4042-4203, C-23 4889-4934, C-28 5744-5800 | T-18만 실행. 피드백 요청 분기는 코드 확인 |
| R-15 | C-21 4205-4364, C-24 4945-5057, C-14 2193-2334 | T-12 T-22 T-23 |
| R-16 | C-13, C-15 2378-2691 | T-11 T-13 T-20 |
| R-17 | C-22 4366-4445, C-30 `labelPoint`, C-25 5132-5152 | T-01 T-05 |
| R-18 | C-16, C-34 | T-16 T-20 |
| R-19 | C-25 5154-5311 | T-10 |
| R-20 | C-26 5356-5399, C-28 5802-5848, C-35 | T-19 |
| R-21 | C-28 5646-5920, C-32 | 코드 확인. README의 "bounded"와 일치 |
| R-22 | C-12 1582-1601 `acceptsFix` 및 그 아래 helper | 코드 확인(출력은 문구만 영향) |
| R-23 | C-27 5520-5569, 5608-5644, C-01 | T-10 T-20 |
| R-24 | C-26 5313-5517, C-30, C-35 `predictedFixedWidthOverflow`, `shared/cli.mjs` `svgRootAttrs`(rendering.md C-03) | T-06 T-28. 시각 확인 없음 |
| R-25 | C-29, README "Migration" | T-25 |
| R-26 | 정렬·후보 순번 규칙(C-05, C-20) | T-27, 시계·난수 전수 미확인 |
| R-27 | C-09 1245-1265, C-21 `routeVia` 4349-4362, C-16 | T-02 T-15 T-29 T-30 |
| T-01~T-30 | [demos.sh](../../../artifacts/archify/spec-demos/rendering/workflow/demos.sh), `out/*.json`, `out/*.err`, [summary.txt](../../../artifacts/archify/spec-demos/rendering/workflow/summary.txt) | 설치본 실행. 큰 HTML은 남기지 않음. `--quality showcase`와 `migrate` 사례는 이 스크립트에 없고 위 표의 명령으로 따로 실행했다(출력은 `out/`) |

문서와 구현이 다른 점(구현을 사실로 썼다):
- [rendering.md](rendering.md) 1.3 H의 workflow 행은 `workflow/short-edge`·`label-node-overlap`을 렌더 진단 code로 적었으나, 코드에서 두 문자열은 `column-capacity`의 `suppresses`에만 있고 발행되지 않는다(실제 code는 `layout/constraint`, T-15·T-29·T-30).
- 같은 행의 "넓으면 `data-reader-fit="width-first"`"는 불완전하다. 조건은 v2·viewBox 없음·(세로 스택으로 레인 104 초과 또는 고정 폭 넘침 예측)이다(R-24).
- 같은 행의 "교차·모호 통로 오류면 라우트 순서를 바꿔"는 맞지만 대상은 그 두 code의 오류만 있을 때이고 재시도마다 `fanInLabelClearance`가 켜진다(R-21).
- rendering.md R-15의 "게이트는 `meta.quality_profile`만 본다"는 architecture 한정이다. workflow는 `qualityProfile` 인자(환경 변수)가 문서 값을 덮어쓴다(T-20).
- README는 "v1 output is preserved byte-for-byte"라 하지만 이 분석에서 바이트 비교는 하지 않았다. 컴파일러는 v1에 별도 분기를 쓴다는 것만 확인했다.

### 2.2 코드 읽는 순서 [선택]
`render-workflow.mjs` → `compileWorkflow`(5917) → `compileWorkflowWithFeedback`(5802) → `compileWithLayoutFeedback`(5744) → `compileWithRouteOrderFeedback`(5715) → `compileWorkflowInternal`(1362). 그 안에서 `createReadableLayout`(233) → `resolveWorkflowLegendFootprint`(860) → `createWorkflowLaneGeometry`(910) → `measureWorkflowNodes`(984) → 끝의 `try`(5608)의 다섯 검증 함수 → `pathFor`(5083) → `readableAutomaticRoute`(4693) → `readableAutomaticCandidateSet`(3978) → `readableCandidateRejection`(3688) / `readableCandidateCost`(3908) → `finalizeReadableViewBox`(5253) → `renderSvg`(5478). 수정 후보 검증(1580~2191)은 진단 문구용이므로 뒤에 읽는다.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙 없음. 원본 코드를 복사하지 않았다.

## 미결정

이 스펙 자체의 미결정은 없다(1.4 참고). `status: draft`인 이유는 선행 [rendering.md](rendering.md)가 draft이고, 확인 한계(1.4)에 적은 경로(피드백 요청·수리 후보·자동 showcase 교차)를 실행으로 확인하지 못했기 때문이다.
