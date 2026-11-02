---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/renderers/dataflow/render-dataflow.mjs
  - archify/renderers/dataflow/dataflow-compiler.mjs
  - archify/renderers/dataflow/label-capacity.mjs
  - archify/renderers/dataflow/joint-label-routing.mjs
  - archify/renderers/lifecycle/render-lifecycle.mjs
  - archify/renderers/erd/render-erd.mjs
  - archify/renderers/erd/grid.mjs
  - archify/renderers/class/render-class.mjs
  - archify/renderers/sequence/render-sequence.mjs
  - archify/renderers/tree/render-tree.mjs
  - archify/renderers/timeline/render-timeline.mjs
  - archify/renderers/waterfall/render-waterfall.mjs
  - archify/renderers/architecture/routing.mjs
  - archify/renderers/shared/route-quality.mjs
  - archify/renderers/shared/geometry.mjs
  - archify/renderers/shared/text-fit.mjs
  - archify/renderers/shared/desktop-readability.mjs
  - archify/scripts/check-render-output.mjs
  - archify/bin/finalize.mjs
  - archify/schemas/sequence.schema.json
depends: [rendering.md, rendering-architecture-routing.md]
status: draft          # 2026-11-02: U-01~U-06 해소 문구를 썼으나 작업이 편집 도중에 중단돼 C-ID·T-ID·2.1 정합을 검증하지 못함. 다시 확인 후 ready
---

# 렌더링 (나머지 8개 타입: dataflow·lifecycle·erd·class는 깊게, sequence·tree·timeline·waterfall은 입력→배치→출력)

> 검증을 통과한 diagram 객체 하나를 받아, 타입별 렌더러가 노드 크기 측정 → 배치 → (연결선) 라우팅 → 라벨 → 레이아웃 진단 → viewBox → SVG 문자열 순서로 처리하는 방식을, [rendering.md](rendering.md)의 공통 계층(슬롯·쓰기·진단 전달) 위에서 8개 타입별로 구현 가능한 수준까지 풀어 쓴다. rendering.md 1.4의 미결정 M-03을 해소하고 R-41~R-47의 얕은 부분을 대체한다.

이 문서가 소유하는 범위는 rendering.md 표 H의 dataflow·lifecycle·erd·class·sequence·tree·timeline·waterfall 행이다. architecture·workflow는 rendering.md, 입력 검증과 진단 객체의 필드는 [input-validation.md](input-validation.md)가 소유한다. 이 문서의 R-ID와 C-ID는 이 문서 안에서만 유효하고, rendering.md의 ID는 "rendering R-41"처럼 접두어를 붙여 부른다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 타입별 렌더러 모듈이 `loadDiagram`(dataflow·lifecycle·sequence는 비동기 브랜드 마크 변형)으로 검증된 객체를 받는다. 이 경계 앞은 rendering.md 1.1 단계 2까지와 같다.
2. **측정**: 노드·엔티티·타입·참가자·카드의 폭과 높이를 글자 폭 계수(`0.6×글자크기×textUnits`, 패딩 8)로 정한다. 저자가 준 `width`/`height`/`pos`가 항상 우선한다.
3. **배치**: 타입마다 다르다. dataflow는 스테이지×행 고정 격자, lifecycle은 척추(mainPath)+BFS 행, erd·class는 띠 격자(`bandedLayout`), sequence는 열 간격 + 저자가 준 y, tree는 세대별 띠 + 말단 순서 배치, timeline은 시간축 선형(휴지기 압축), waterfall은 깊이 우선 행.
4. **라우팅**: dataflow·lifecycle·sequence·tree는 렌더러 안의 코드가, erd·class는 architecture의 `createRouter`(옵션만 다르게 넘김)와 자체 trunk/bus 후보가 선을 만든다. timeline·waterfall은 선이 없다.
5. **라벨**: 연결 라벨 위치를 기본점에서 정하고, dataflow(showcase)·erd·class는 공유 `placeAutomaticLabels`로 충돌 라벨을 옮긴다.
6. **진단**: 타입별 검증 함수가 문제 문장 목록을 모으고 `throwDiagnosticProblems`로 한 번에 던진다. 구조화된 상세가 있는 문장만 전용 code를 갖고 나머지는 `layout/constraint`다(R-40). 문제가 있으면 파일을 쓰지 않는다.
7. 통과하면 viewBox(저자 값 또는 자동 공식)와 SVG 문자열이 확정되고, `writeDiagram`이 rendering.md R-06~R-14대로 HTML을 쓴다. 순서는 타입마다 조금 다르다: erd·class·sequence·tree는 viewBox를 먼저 정하고 그 위에서 라우팅·검증하지만, lifecycle은 배치 결과로 viewBox를 정한 뒤 검증한다(R-13).

### 1.2 범위·통합 지점 [필수]
- 제공: 8개 타입의 입력→배치 알고리즘의 단계·상수, 진단 code와 조건, 자동 viewBox 공식, 최소 입력의 관측 좌표.
- 제외: 공통 슬롯·쓰기·CLI(rendering.md), 스키마 검증(input-validation.md), 공유 게이트 함수(`cleanFlowProblems` 등)의 내부 계산(rendering.md C-24, 여기서는 호출 지점과 프로파일 조건만), `createRouter`·`planRoutes` 내부(rendering-architecture-routing.md가 소유, 이 문서는 erd·class가 넘기는 옵션과 효과만 1.3 J), 노드의 브랜드 마크(`renderBrandMark`·`brandMetadataFor`, 브랜드 기능), viewer JS, 산출 후 `check`·`browser-check`(verification-gates).
- 외부 의존·선행 계약: rendering.md의 `writeDiagram`·`applyTemplate`·진단 전달, 텍스트 폭 규칙(rendering.md C-26: `textUnits`, 폭 계수 0.6, 패딩 8), 범례 측정(`resolveLegend`·`legendFootprint`·`measureLegend`, rendering.md C-06). 공유 기하 함수는 1.3 I에서 필요한 것만 풀어 쓴다.
- 소유 상태·부작용: 렌더러 프로세스 안의 지역 상태(캐시 Map 등)뿐이다. 시계·난수는 쓰지 않는다(`추론`: 읽은 범위에서 `Date.now`·`Math.random` 호출은 보지 못했다. timeline은 `Date.parse`·`Intl.DateTimeFormat`으로 입력 시각만 변환한다).

### 1.3 인터페이스와 데이터 의미 [필수]

표기: "깊이 수준 A"는 알고리즘 단계·모든 상수·진단 code를 읽었다는 뜻이고, "B"는 입력→배치→출력과 진단 code까지 읽었다는 뜻이다. 읽지 못한 부분은 각 절 끝과 1.4 미결정에 적는다.

#### A. dataflow (깊이 수준 A, 단 showcase 후반 후처리는 단계 목록 수준)

`compileDataflow({dataflow, sourceEvidence, qualityProfile})`는 SVG 문자열을 돌려주고, `qualityProfile = ARCHIFY_QUALITY_PROFILE || meta.quality_profile`(환경 변수 우선)이다. **`automaticShowcase`** = 프로파일이 `showcase` && `meta.viewBox` 없음 && 어느 노드에도 `width` 없음. 이 값이 거짓(= standard 또는 저자 viewBox/폭 지정)이면 아래 "프리셋 라우터"만 쓴다.

| 항목 | 값 |
|---|---|
| 상수 | `stageY 46`, `stageH 36`, `stageBottomPad 74`, `leftX 100`, `colGap 215`, `stageW 168`, `nodeW 112`, `nodeH 58`, `rowYs [128,242,356,470,584]`, 라벨 높이 16(`FLOW_LABEL_HEIGHT`), `minimumNodeHeight 36`, 스테이지 프레임 반지름 10 |
| 노드 | `cx = 100 + 215×stage`, `y = rowYs[row] + (yOffset||0)`, `width = node.width ‖ 112`, `height = node.height ‖ 58`, `x = cx − width/2`, `cy = y + height/2`. `row`는 0..4(범위 밖이면 좌표가 NaN이 되어 R-06의 두 문장으로 진단) |
| 스테이지 프레임 | 중심 `cx`, 폭 168, `y 46`, 높이 `viewBox[1] − 46 − 74` |
| 자동 폭 | `max(480, ceil(max(마지막 스테이지 오른쪽, 모든 노드 오른쪽, 고정 라벨(labelAt) 오른쪽) + 24))`. 마지막 스테이지 오른쪽 = `stageX(n−1)+84` |
| 자동 높이 | 720. `automaticShowcase`면 라벨·경로 배치 후 `max(360, ceil(내용 바닥 + 24 + 74))`로 다시 정한다(내용 바닥 = 노드 바닥·경로 점 y·라벨 바닥의 최대) |
| 연결 변 | 가로 우선: 목적지 `cx`가 더 왼쪽이면 출발 `left`/도착 `right`, 오른쪽이면 `right`/`left`, `cx`가 같으면 `cy` 비교로 `bottom`/`top`(도착은 반대). `fromSide/toSide`가 `auto`가 아니면 저자 값. showcase+재균형 시도에서만 출발 변이 바뀔 수 있다 |
| 포트 | 같은 노드·같은 변에 자동 연결이 2개 이상이면 상대 중심 좌표 순으로 변 가운데 기준 `(i−(n−1)/2)×간격`. 간격 = `min(18, (변 길이−32)/(n−1))`. `route≠auto`·`via`·`channelX/Y`·`labelAt`이 있는 연결은 포트 퍼뜨림에서 빠진다 |
| 흐름 선 굵기 | `width ‖ (variant==="emphasis" ? 1.8 : 1.4)`. 경로 `d`는 모서리를 둥글리지 않는 꺾은선(`M x y L x y …`), 연속 중복점은 제거, 점이 2개 미만이면 끝점을 추가 |

**프리셋 라우터(`routeVia`)** — 명시값이 자동보다 먼저다.

| `route` | 중간점 |
|---|---|
| `via` 있음 | 그 배열을 그대로 |
| `straight` | 없음 |
| `vertical-channel` | `x = channelX ?? start.x ± 44(도착이 오른쪽이면 +)`: `[[x,sy],[x,ey]]` |
| `bottom-channel` | `y = channelY ?? max(from 바닥, to 바닥) + 26`: `[[sx,y],[ex,y]]` |
| `top-channel` | `y = channelY ?? min(from.y, to.y) − 24`: `[[sx,y],[ex,y]]` |
| `auto`(기본) | (1) showcase이고 두 포트 축 차이가 0 초과 16 미만이면 `automaticPortRhythmBridge`(바깥 채널 우회, 이웃 노드를 관통하지 않을 때만). (2) 출발·도착 방향이 직각이면 모서리 하나, 아니면 24px 스텁을 둔 두 후보 중 변 규칙을 지키고 노드를 관통하지 않는 첫 후보. (3) showcase이고 둘 다 수직 변이면 같은 x면 직선, 아니면 중점 y의 두 점. (4) `|sy−ey|<4`면 직선. (5) 아니면 `midX = sx + (ex−sx)/2`에서 세로로 꺾되, 그 x가 중간 스테이지 노드를 관통하면 인접 스테이지 사이 중점들 중 가장 가까운 비관통 x로 옮긴다 |

**showcase 후처리(`automaticShowcase`일 때만, 순서대로)** — 격자 탐색 `shortestOrthogonalGridRoute`는 rendering-architecture-routing.md R-25·C-20이 푼 같은 함수이고, 이 렌더러가 넘기는 인자와 수락 조건은 아래 3번, 라벨·경로 공동 수리 `repairLabelRoutes`는 아래 6번 (e)와 C-36이다.

1. 재균형 시도(2회차 `rebalancePorts=true`)일 때만: 왼/오른쪽 변의 포트 점유(`portSpan = 32 + (n−1)×min(18, ceil(최대 폭×(들어옴이면 7, 아니면 1))+2)`)가 노드 높이를 넘으면, 그 노드의 나가는 흐름 하나를 위/아래 변으로 옮기는 후보를 모아 거리 최소 하나만 채택. 후보가 하나도 없으면 `null`(= 재시도 실패, 첫 오류를 그대로 던진다).
2. 들어오는 화살이 몰린 노드는 `desired = max(높이, portSpan)`까지 위아래로 키운다(상한: 행 간격−10, 스테이지 머리 아래 여백, 이웃 노드와의 거리 규칙). `height`/`yOffset`을 저자가 준 노드와 라우트·라벨 핀이 붙은 노드는 건너뛴다.
3. 경로 수리 패스(최대 연결 수만큼): 노드를 관통하거나 다른 흐름과 통로를 공유하는 자동 경로를 `gridDetour`(= `shortestOrthogonalGridRoute` 호출) 또는 `compactCorridors`(통로 좌표 후보 최대 16개, 이웃 선에서 ±8)로 교체. 후보는 `readingCost = 길이 + (굽힘−1)×48 + 교차한 무관 흐름 수×160` 오름차순. `gridDetour` 인자: 출발·도착 노드는 그대로, 나머지 노드는 사방 `DETOUR_NODE_GAP 12`만큼 키운 장애물, `clearance 2`, `maximumObstacleCount 80`, `endpointStubPx 24`, `maximumGridNodes 4096`, `minimumAvoidedOverlapPx 8`, `routeSeparationPx 8`, `minimumSegmentPx 16`, `bendPenaltyPx 48`. 피할 선분 = 끝점을 공유하지 않는 흐름의 현재 경로(보류 집합에 든 흐름은 끝 스텁만), `allowAvoidedCrossings`는 경로 수리 패스가 false·true 둘 다 시도하고 교차 해소 패스(4번)는 false만 쓴다. 결과가 스테이지 프레임 변(바닥 제외)을 타면 `borderSegments`(스테이지 프레임 변, 바닥 제외)를 주고 한 번 더 탐색한다. 결과는 점 정규화 뒤 리듬 문제(구간 8 미만, 안쪽 16 미만)가 있으면 버린다. 격자 알고리즘 자체와 동률 처리는 rendering-architecture-routing.md R-25.
4. 교차 해소 패스: 무관한 흐름과 진짜 교차하는 자동 경로를, 교차를 줄이는 가장 싼 우회로 교체. 남은 자동↔자동 교차는 `data-composition-crossover="halo"`(굵기+4의 마스크 밑선)로 통과 표시하고 `resolvedCrossoverFlows`에 넣는다. 저자 지정 경로의 교차는 진단으로 남는다.
5. 포트 순서 재정렬(최대 16번 시도): 같은 노드·변의 자동 포트 2~8개를 첫 꺾임 위치 순서로 다시 대응시켜 경로가 짧아지고 교차가 늘지 않을 때만 채택.
6. 라벨: 기본점 = `legacyLabelPoint`(2점이면 `[(x0+x1)/2+dx, y0−10+dy]`, 3점 이상이면 `labelSegment`(기본 1) 구간 중점 `−10`). 수직 2점 자동 흐름은 출발 노드 안에 들어가지 않게 구간 중점 `−10`에서 시작. 크기 `폭 = round(max(34, 최장줄 textUnits×4.9+12)×10)/10`, `높이 = 16 + 11×(추가 줄 수 + (classification 있으면 1))`. `placeAutomaticLabels`(후보: 선 옆 비율·슬라이딩·고리, `maxOwnRouteDistance 36`, 배치 한계 `viewBox[1]−74`)가 충돌 라벨을 옮긴다. 이어서 (a) classification 두 번째 줄이 자기 선을 가리면 위로 재배치, (b) 라벨이 막은 통로 구간을 라벨 밖으로 밀기(시도 최대 16, 추가 비용 ≤ 굽힘 2개 분량=96, 굽힘·교차·공유 통로·노드 관통을 늘리지 않을 때만), (c) 짧은 포트 다리의 자유 끝점을 직선으로 맞추기(최대 16), (d) `wrapBlockedFlowLabels`(두 줄로 접기: 단어 경계 분할 최대 8형태, 위치 후보 최대 64), (e) `repairLabelRoutes`(라벨 하나와 막는 경로 몇 개를 한 제안으로 푼다. 노드+제목+라벨 합이 80 초과면 건너뜀, 탐색 최대 32. 후보 생성·정렬·종료·상수는 코드(C-36)가 기준이고, 호출 인자·결과 반영은 R-42). 라벨 위치가 `labelAt/labelDx/labelDy/labelSegment`로 고정된 흐름은 어느 단계에서도 옮기지 않는다.
7. 마지막에 `fitAutomaticWidthToLabels`(폭은 늘리기만), 높이 재산정, 스테이지 프레임 높이를 새 높이로 갱신.

**진단(`validateDataflow`, 문제를 모아 한 번에)**: `dataflow/node-above-area`(`y < 46+36+22 = 104`), `dataflow/node-below-area`(`y+height > viewBox[1]−74`; 수정안은 yOffset 낮추기·높이 줄이기·canvas 높이 키우기 중 단독으로 해소되는 것만, 산식은 R-46), `dataflow/unknown-endpoint`(수정안: 인접 스테이지 순서로 정렬한 노드 id 최대 3개), 그 밖은 모두 기본 code `layout/constraint`: 노드 id 중복, `stage`가 0..n−1 밖, `row`가 0..4 밖, 비유한 좌표, 노드가 `x<24` 또는 `x+width>viewBox[0]−24`, sublabel·tag가 최소 글자(`6`, showcase 자동은 `minimumReadableSourceTextPx(viewBox[0])` 이상)로도 `폭−8`에 안 들어감, 노드 간격 10px 미만, 라벨 없는 흐름(`must include a short data label`), 흐름 길이 34px 미만, `via`의 대각선 구간, 마지막 스테이지가 `viewBox[0]−24`를 넘음, 공유 게이트 `clean-flow/*`·`composition/*`(rendering R-35 아래 목록), 라벨-노드·라벨-라벨 겹침(허용 −2px). 오류 메시지 앞머리는 `Data-flow layout validation failed`.

**재시도**: 첫 시도가 `Data-flow layout validation failed:`로 시작하는 분류된 진단이면 `rebalancePorts=true`로 한 번 더 한다. 성공하면 그 결과, 재시도가 `null`을 돌려주거나 다시 레이아웃 오류를 던지면 **첫** 진단을 던진다. 다른 종류의 예외는 그대로 전파한다.

#### B. lifecycle (깊이 수준 A)

입력 `mainPath[]`, `states[id,type,label,sublabel,tag,step]`, `transitions[from,to,label,note,variant]`. `meta.viewBox`는 스키마에 없어 항상 자동이다.

| 항목 | 값 |
|---|---|
| 상수 | `STATE_H 64`, 폭 140..220, `MARGIN_X 56`, `MARGIN_TOP 28`, `PORT_PAD 22`, `PORT_STEP 26`, `CORNER 12`(경로 둥글리기), `FRAME_PAD 10`, `ARC_BASE 30`, `ARC_STEP 24`, `TRACK_STEP 18`, `LABEL_GAP 6`, `CLEARANCE 5`, `SPACING_ROUNDS 5`, 글자 `label 12→10`, `sublabel 9→8`, `tag 8→7`, `step 8`, 전이 라벨 글자 10·노트 9 |
| 상태 폭 | `ceil(min(220, max(140, 라벨 요구폭, sublabel 요구폭, tag 요구폭)))`. 요구폭: 텍스트는 `textUnits×font×0.6+8+36`(sublabel·tag), 라벨은 `minimumNodeTextWidth(label,12) + 좌측 장식(sigil 폭+2, step 있으면 26+step 폭) + 우측 장식(브랜드 26 또는 4, 근거 배지) + 4` |
| 전이 라벨 상자 | `폭 = ceil(max(label textUnits×10×0.6, note textUnits×9×0.6) + 12)`, 높이 = 라벨과 노트가 둘 다 있으면 28, 하나면 16 |
| `readableWidthBudget` | `floor(930 × 가장 작은 글자 / 6)`. 가장 작은 글자 = `min(10, 모든 상태의 맞춘 label 글자, sublabel 있는 상태의 맞춘 sublabel 글자)`. 보통 10이면 1550 |

**1. 분류**. 척추 전이 = `mainPath[i]→mainPath[i+1]`인 첫 전이(없으면 `main-path-gap`). 행(depth) = mainPath는 0, 나머지는 mainPath에서 전이를 양방향으로 따라간 BFS 거리, 연결 없는 상태는 1. 전이 종류: 두 끝이 모두 0행이면 척추 전이는 `spine`, 그 밖은 `arc`(위쪽 호). 같은 행이면 `same`, 다른 행이면 `between`. 0행에서 나가 같은 목적지로 가는 `between` 전이들을 `label|note|variant`가 모두 같은 묶음으로 나눠, 서로 다른 출발 상태가 2개 이상인 묶음이 **정확히 하나**일 때만 괄호(bracket)로 합친다. 괄호 출발 상태가 mainPath에서 연속이고 이미 정한 프레임과 겹치지 않으면 그 구간을 프레임(`FRAME_PAD` 10) 하나로 감싸고 목적지마다 프레임에서 한 번 나가는 선으로, 아니면 아래에 공유 버스를 둔다.

**2. 간격 라운드**(최대 5회). 초기 `{spineGap 72, rowGap 44, drop 58, firstTrack 34}`. 매 라운드 포트 배정 방식 `partner`(상대 쪽으로 당김)와 `even`(균등) 두 가지로 `layout()`을 돌려, 라벨이 모두 놓인 후보 중 `routeCost`가 가장 작은 것을 고른다. 하나라도 놓이면 종료. 첫 라운드 실패 시 미배치 라벨이 가장 적은 후보의 미배치 전이를 `spacingWideners`에 기록(too-wide 진단 문구에 쓰임). 다음 라운드 간격은 `spineGap+28, rowGap+28, drop+14, firstTrack+6`이되, 척추 행 전체 폭 `56×2 + 척추 상태 폭 합 + Σmax(다음 spineGap, 그 구간 최소 간격)`이 `readableWidthBudget`을 넘으면 `spineGap`만 올리지 않는다. 5회 후에도 실패하면 마지막 후보(`candidates[0]`)로 진행하고 R-13에서 `label-unplaced`가 된다. `routeCost = Σ경로 (점수−2)×10 + (점이 3개 이상인 경로의 수평 구간마다 길이×0.1, 길이 30 미만이면 +40)`.

**3. `layout()`**: (a) 척추 x: `x_0 = 56`, 다음 `x += 폭 + max(spineGap, 그 구간 최소 간격)`. 최소 간격 = (척추 전이에 라벨이 있으면 그 라벨 상자 폭, 없으면 0) + 26. (b) 1행부터 `placeRow`: 각 상태의 이상 x = 윗행에서 연결된 상태들의 중심 평균(1행은 괄호 목적지를 그 출발 상태 중심 평균으로 덮어씀, 연결 없으면 맨 오른쪽보다 +1), 가중치 = 연결 있으면 블록 크기·없으면 0.05. 블록을 이상 x 순으로 놓고 겹치면 클러스터로 합쳐 가중 평균 중심으로 정렬(등압 회귀식). 이웃 상태 간격 = `max(rowGap, 그 둘을 잇는 라벨 있는 전이의 라벨 폭 + 32)`. (c) 가장 왼쪽 요소가 `x=56`이 되게 전체 평행 이동. (d) 호 수준: 짧은 호부터 `level = 1 + 겹치는 호의 최대 level`. `spineTop = 28 + (maxLevel>0 ? 30 + (maxLevel−1)×24 + (라벨 있는 호가 있으면 12) : 0)`. (e) 같은 행 이웃 `same` 전이(양방향 포함)는 두 상태 옆면 사이 수평선으로 그린다. 같은 이웃 쌍의 전이가 3개 이상이면 `step = max(min(20, 48/(n−1)), 라벨 높이/2+5, 인접 라벨 높이 합/2+4)`로 간격을 정하고 그 행의 높이를 `step×(n−1)+16`까지 키운다. **6개 이상이면 `lifecycle/crowded-side-transitions`**(즉시 던짐). 이웃이 아닌 `same` 전이는 아래로 도는 루프다. (f) 포트(`distributePorts`): 변마다 상대 x의 방향(왼/오른)별로 정렬, 같은 호 쌍은 바깥 호가 더 바깥. 간격 `min(26, (폭−44)/(n−1))`, `even`이거나 척추의 위쪽 변이면 가운데 기준 균등, 아니면 `fitPorts`(등압 회귀로 상대 x에 최대한 가깝게). `snapPorts`가 거의 수직인 연결을 정확히 수직으로 맞춘다(12px 이상 간격·포트 폭 안이 유지될 때). (g) 프레임 출구(`placeFrameExits`): 목적지 포트 x를 프레임 안 `[x+16, x+w−16]`로 자르고 다른 포트와 14px 이상 떨어진 곳을 7px 단위로 최대 40번 탐색. (h) 행 사이 통로의 수평 구간은 `assignTracks`: 구간 겹침(±10px)이 없는 트랙을 탐욕 배정하되 5가지 정렬 순서를 시도해 교차 수가 가장 적은(동률이면 트랙 수가 적은) 것 채택. 트랙 y = `행 바닥 + firstTrack + 트랙×18`, 다음 행 top = `마지막 트랙 y(없으면 행 바닥+firstTrack) + drop`. (i) 경로: 척추는 두 상태 옆면 중앙을 잇는 직선, 호는 `[(out,spineTop),(out,y),(in,y),(in,spineTop)]`(`y = spineTop − 30 − (level−1)×24`), `between`·루프·프레임·버스는 `[상단 포트→트랙 y→하단 포트]`(같은 x면 직선). 선은 `roundedPath(points, 12)`로 그린다.

**4. 라벨(`placeLabels`)**: 모드 `above`(척추·옆면 직선: 선 위 `LABEL_GAP+h/2`, 안 되면 아래), `on`(호·루프·3개 이상 병렬: 선 위 비율 0.5/0.35/0.65/0.2/0.8), `beside`(수직 구간 옆 `±(6+w/2)`에 y 이동 0/−10/+10, 수평 구간 중앙은 마지막 후보), `none`(괄호의 두 번째 이후 전이). 후보가 허용되려면 `x ≥ 8`, `x+w ≤ 내용 오른쪽+56−8`, `y ≥ 4`, 상태·이미 놓인 라벨과 4px 이상, 다른 전이 선과 5px 이상, (모드가 `on`이 아니면) 자기 묶음 선과도 5px 이상. 모두 실패하면 첫 후보에 두고 `unplacedLabels`에 넣는다.

**5. 캔버스와 진단**: `폭 = max(640, ceil(내용 오른쪽 + 56))`, `높이 = ceil(내용 바닥 + (범례 항목이 있으면 78 + 범례 추가 높이, 없으면 32))`. 범례는 쓰인 상태 종류 + 항상 `start`, 종료 상태(나가는 전이가 없는 상태)가 있으면 `final` 항목 추가. 구조 검증(레이아웃 전, 문제를 모아 던짐): `lifecycle/duplicate-state`, `lifecycle/unknown-main-path-state`, `lifecycle/repeated-main-path-state`, `lifecycle/unknown-endpoint`, `lifecycle/main-path-gap`(mainPath의 연속 쌍에 전이가 없음), `lifecycle/state-text-too-long`(라벨 10px·sublabel 8px·tag 7px 최소로도 `220−8`(브랜드 마크가 있으면 −26)에 안 맞음). 레이아웃 검증: `lifecycle/too-wide`(`viewBox[0] > readableWidthBudget`), `lifecycle/label-unplaced`(`geometry.unplacedLabels`의 각 전이). 전자는 폭을 키울 수 있는 원인 목록(`wideStepLabels`, `spacingWideners`)을 evidence·수정안에 싣는다.

#### C. erd (깊이 수준 A, 라우터 내부 제외)

| 항목 | 값 |
|---|---|
| 상수 | `margin 24`, `legendH 34`, `padX 12`, `keyWidth 30`, 글자 `header 13→10`, `row 11→9`, `type 10.5→9`, `minRelationshipLength 24`, 관계 라벨 글자 9(폭 계수 0.62), 포트 간격 `ERD_PORT_SPACING 24`, 마커 높이 14·폭 24, 레인 간격 `LANE_STEP 12`, 도메인 띠 여백 `x 12`/`top 18`/`bottom 8` |
| 격자 기본 | `origin [32,40]`, `gapX 56`, `gapY 44`, `entityW 240`, `headerH 30`, `rowH 20`. `layout`이 없고 `row/col`이 있는 엔티티가 하나라도 있으면 기본 격자, `layout.mode≠"grid"`면 격자 없음(모든 엔티티가 `pos` 필요) |
| 엔티티 크기 | 폭 `entity.width ‖ entityW`, 높이 `headerH + max(1, 속성 수)×rowH + 6` |
| 띠 격자 | rendering R-44와 같다(열 x 누적 = 열 최대폭 + `max(gapX, 라벨 요구 간격)`, 행 y 누적 = 행 최대높이 + `gapY`, 열 안 가운데 정렬, 반칸 열 중점) |
| 라벨 요구 간격 | `meta.viewBox`도 `pos`도 `via`·`labelAt`·`route≠auto`·`channelX/Y`도 없을 때만: 인접 열(`|Δcol|=1`) 사이의 라벨 있는 관계마다 `ceil(max(30, textUnits×9×0.62+10) + 28×2)`를 그 사이 열 간격의 하한으로 쓴다(`gapX`는 최소로 유지) |
| 자동 viewBox | `폭 = ceil(최대 x + 24)`, 범례 `minWidth > 폭−48`이면 `ceil(minWidth+48)`. `높이 = ceil(최대 y + 24 + 34 + 범례 추가 높이)`, 범례가 `measureLegend`에 안 맞으면 34씩 최대 4번 추가. 저자 `viewBox`는 그대로 |

**도메인 띠**: `tag`가 같은 엔티티가 모두 격자로 놓였고(`pos` 없음) 셀들이 **꽉 찬 직사각형**(중복 없음, 셀 수 = 바운딩 박스 면적)이면 띠를 그린다. 띠 상자 = 멤버 바운딩 `x−12, y−18, 폭+24, 높이+18+8`, 캡션은 `(x+10, y+13)`. 색상은 도메인 첫 등장 순으로 `database, frontend, backend, cloud, messagebus, security`를 돌려 쓴다. 띠를 못 그리는 `tag`는 그대로 두면 이름이 사라지므로 **거부한다**(`erd/domain-not-drawn`). 사유 `reason`: `shared-cell`(같은 셀 중복: 이 코드는 내지 않고 격자 배치 문제로만 보고), `scattered`(셀 영역이 꽉 차지 않음, 즉 L·대각선), `no-grid`(멤버 중 `pos`가 있거나 row/col이 없음), `off-canvas`(캡션 점이 viewBox 안쪽 4px에 못 듦), `band-covers-entity`(띠가 다른 도메인의 엔티티와 겹침).

**라우팅 구성**: architecture의 `createRouter`를 다음 옵션으로 부른다: `sideFor`(가로 우선 `legacyDefault*`), `preferredCandidates = [trunk 후보, 레인 후보]`, `compositionFloors false`, `maxPortSpacing 24`, `preferReadableRoutes true`, `crossingFreeGridFirst true`, `componentGapPx 10`, `minimumTerminalSegmentPx 14`. 각 옵션의 효과와 넘기지 않는 옵션은 1.3 J, 후보 순서·개선 스윕은 rendering-architecture-routing.md. 이 렌더러가 얹는 것:
- **레인**: 같은 통로(`h|v` + 두 엔티티의 띠 키 쌍)를 공유하는 관계 2개 이상은 (`from`,`to`,`id`) 사전순으로 `(i − (n−1)/2)` 오프셋을 받고, 레인 후보 = 가운데 좌표 + 오프셋×12의 직교 두 점. 레인이 끝점 규칙을 깨거나 엔티티를 관통하면 건너뛴다.
- **trunk 묶음**: 자동 라우트(`via`·`route`·`channelX/Y`·`labelAt` 없음) 관계를 (엔티티, 변, 마커 스타일(`identifying:false`면 dashed, 아니면 `variant`))로 fan-in(`to`) 먼저, 그다음 fan-out(`from`)으로 묶는다. 이미 묶인 관계는 제외, 멤버 2개 미만이면 묶지 않는다. 묶음마다 trunk 좌표 = 변 바깥으로 `[16, 22, 12, 28]` 순으로 후보를 시도해 멤버 포트 구간(±10)을 엔티티가 가로막지 않는 첫 값. 12px 안의 같은 축·같은 스타일 trunk에는 그 좌표로 붙고(다른 스타일과는 12px 이내면 불가), 후보가 없으면 묶음을 해제한다.
- **trunk 후보 모양**(수평 변, `axis 0`): 두 끝이 모두 가로 변이면 `[[trunk,sy],[trunk,ey]]`, 한쪽만 가로면 반대쪽 끝에 12px 다리를 둔 3점 경로. 세로 변은 대칭. 둘 다 아니면 후보 없음.
- **그리기**: 각 관계 선은 논리 경로의 trunk 구간을 뺀 조각들을 `roundedPath(…, 8)`로 그린다(논리 점은 그대로 두어 게이트·라벨이 전체 경로를 본다). trunk 자체는 `(축, 좌표, 스타일)` 군집마다 구간을 합쳐 `data-er-trunk` 경로로 한 번 그린다. 합친 구간 사이 틈이 0.5 초과 `ERD_PORT_SPACING+8 = 32` 이하이고 무관한 선·엔티티를 가로지르지 않으면 이어 붙이고, 32 초과면 별개 trunk로 둔다. 라우터가 다른 변으로 옮긴 멤버는 trunk를 그리지 않고 전체를 그린다.
- **라벨**: trunk 멤버의 기본 라벨 구간은 `labelSegment 0`(출발 쪽 토막, trunk 위에 앉지 않게). 관계 라벨 상자 = `폭 max(30, textUnits×9×0.62+10)`, 높이 14, `y = ly−10`. 충돌 라벨은 공유 배치기로 옮기며 각 끝의 카디널리티 글리프(24×20)를 예약한다.

**진단**(`validateEr`, 모아서 `layout/constraint` 기본 + 아래 상세 code): `erd/header-text-capacity`(제목이 `폭−30−12`에 최소 글자로 안 들어감), `erd/domain-not-drawn`(위 사유 5종), `erd/attribute-text-capacity`(속성 행 `name 폭×11 + (type 있으면 type 폭×10.5+8)`가 `폭−24−키 열 폭`을 넘음; 수정안은 필요한 `width`), `layout/marker-capacity`(자동 라우트 관계 끝 2개 이상이 한 변을 공유하는데 `min(24, (변 길이−32)/(n−1)) < 14`). 그 밖은 `layout/constraint`: 격자 배치(셀 중복, 음수, 배치 불가), 엔티티 id·속성명 중복, 엔티티 겹침(간격 0), 알 수 없는 from/to, **자기 관계(`from===to`)는 항상 거부**, 관계 길이 24px 미만, `references`가 없는 엔티티·속성을 가리킴, 공유 게이트(끝점 변·노드 관통·교차·모호 통로·리듬·라벨-경로 간격: 교차·모호·리듬·라벨 간격은 `meta.quality_profile`이 있을 때 심각도 적용), 라벨-엔티티 겹침(−2px).

#### D. class (깊이 수준 A, 라우터 내부 제외)

| 항목 | 값 |
|---|---|
| 상수 | 격자 기본 `origin [32,40]`, `gapX 128`, `gapY 84`, `typeW 180`, `typeMaxW 300`(`layout`이 덮음, 항상 격자). `margin 24`, `legendH 34`, `padX 12`, `headerH 44`(스테레오타입 있는 kind) / `headerPlainH 34`, 이름 글자 13.5, 스테레오타입 9.5, 멤버 11, `rowH 20`, `compartmentPad 5`, `minRelationshipLength 28`, 마커 높이 16, 포트 간격 26, `BUS_MIN_GAP 40`, 관계 라벨 글자 9.5(계수 0.62) |
| 상자 폭 | `type.width`가 있으면 그것. 없으면 `max(헤더 요구폭, min(typeMaxW, max(typeW, 가장 긴 멤버 텍스트폭 + 24 + VIS_EXTRA)))`. `VIS_EXTRA = ceil(14+6−2×6.6)`, 헤더 요구폭 = `ceil(24 + 2×24 + max(이름폭×1.08, 스테레오타입폭))`. 제목은 줄바꿈하지 않는다 |
| 상자 높이 | `헤더 + Σ구획(속성, 메서드)(줄 수×20 + 10)`. 멤버가 상자 폭(`폭−24−VIS_EXTRA`)보다 길면 `(`·`, ` 뒤나 `): ` 앞에서 접고(들여쓰기 2, 파라미터 4), 한 토큰이 한 줄보다 길면 글자 단위로 자른다 |
| 배치 | `bandedLayout(…, entityW=typeW)` 후 같은 행 띠 안에서 세로 가운데 정렬(`y = 띠 y + (띠 높이−높이)/2`). `col`은 반칸(`1.5`) 허용. 배치 불가(NaN)면 렌더 초기에 `Class diagram placement failed`(`layout/constraint`) |
| 관계 표기 | dependency(점선, 열린 화살 `to`), association(실선, 열린 화살), inheritance(실선, 속 빈 삼각형 `to`), realization(점선, 삼각형), composition(실선, 채운 마름모 `from`), aggregation(실선, 빈 마름모 `from`). 일반화 = inheritance·realization |
| 자동 viewBox | `폭 = max(320, ceil(최대 x + 24))`(범례 폭 보정은 erd와 같음), `높이 = max(240, ceil(최대 y + 24 + (범례 있으면 34+추가)))`+같은 34씩 최대 4번 보정 |

**변 선택(`sideFor`)**: 두 상자의 x 구간이 겹치면(`overlapX`) 세로 변, 겹치지 않고 y도 겹치지 않으며 관계가 일반화면 세로 변, 그 외는 가로 우선 규칙. 세로일 때 `to.cy > from.cy`면 출발 `bottom`/도착 `top`, 아니면 반대.

**계층 버스**: 자동 라우트(`via`·`route≠auto`·`fromSide/toSide`·`labelAt` 없음)인 일반화를 (`to`, `kind`)로 묶어 **멤버 2개 이상**이고 `첫 하위 타입 top − 상위 바닥 ≥ 40`이면 한 버스를 만든다. `busY = round(상위 바닥 + (최소 하위 top − 상위 바닥)/2)`. 멤버 경로 = `|하위 cx − 상위 cx| < 0.5`면 `[(sx,top),(tx,bottom)]`, 아니면 `[(sx,top),(sx,busY),(tx,busY),(tx,bottom)]`. 다른 타입(자기 둘 제외)을 관통하면 그 묶음은 버스 없이 일반 라우트로 간다. **충돌 롤백**: 일반 라우터로 나머지 관계를 먼저 계획한 뒤, 버스 경로와 일반 경로(또는 다른 버스)가 (같은 타입 끝점이 16px 안, 모호 통로, 진짜 교차) 중 하나로 충돌하면 해당 버스 묶음을 통째로 취소하고 `distinctAutomaticPorts=true`로 라우터를 다시 만들어 반복한다(묶음은 매번 줄어드니 유한). 버스 멤버의 끝점 변은 하위 `top`/상위 `bottom`으로 간주한다. 일반 라우터 옵션은 `sideFor`(위), `maxPortSpacing 26`, `preferReadableRoutes true`, `crossingFreeGridFirst true`, `componentGapPx 10`, `distinctAutomaticPorts`(첫 시도 false, 롤백이 한 번이라도 있으면 true)이고 효과는 1.3 J.

**라벨**: 기본 구간 = `labelSegment` 지정값, 없으면 `길이 − (수직이면 22, 수평이면 폭+8)`이 최대인 구간. 수직이면 `[ax + w/2 + 6 + dx, 중점y + 4 + dy]`, 수평이면 `[중점x + dx, ay − 6 + dy]`. 충돌 라벨은 erd와 같이 공유 배치기로 이동(끝 마커 예약 20).

**진단**: `class/title-text-capacity`(헤더 요구폭 > 상자 폭), `class/realization-target`(realization이 `비인터페이스→인터페이스`가 아님), `class/inheritance-kind`(inheritance가 인터페이스 경계를 넘음), `class/inheritance-cycle`(inheritance 간선의 순환), `layout/marker-capacity`(변 하나의 끝 2개 이상에서 `min(26,(변 길이−32)/(n−1)) < 16`; 버스 멤버는 하나의 포트로 센다), 그 밖은 `layout/constraint`(타입 id·속성명 중복, 셀 중복, 상자 겹침(간격 0), 알 수 없는 타입, 자기 관계 거부, 관계 길이 28 미만, 공유 게이트, 라벨-타입 겹침).

#### E. sequence (깊이 수준 B+: 열·캔버스·노트·검증은 A, 마크업은 미독)

메시지 y는 저자가 정한다(렌더러는 y를 만들지 않는다). `meta.viewBox` 최솟값은 스키마상 `[480,480]`.

| 항목 | 값 |
|---|---|
| 모드 | `meta.column_fit` 기본 `spread`. `fixed`는 참가자 상자 86, 열 간격 108, `sideMargin 62`(=첫 상자 중심 x), `leftX = 62` |
| 자동 폭 | `fixed`면 920. `spread`면 `spreadParticipantWidth(920)`에서 모든 참가자 라벨(`textUnits×6.8 ≤ 폭+6`)·sublabel(6px 최소가 `폭−8`에 듦)이 맞고 참가자 ≤ 3이면 `[560,640,720,800,920]` 중 처음으로 `상자≥86 && 맞음 && 후보−80 ≥ 3×상자+16×(n−1) && timelineLabelsFit`인 값, 아니면 920. 920에서 안 맞으면 `min(readableCanvasWidth, max(920, ceil((min(190, 필요폭)+25)×n + 124)))`, `readableCanvasWidth = floor(930×7/6) = 1085` |
| spread 기하 | `상자 폭 = max(86, min(190, round((폭−124)/n) − 24))`, `span = n×상자 + (n−1)×16`, `margin = max(40, min(62, 폭−40−span))`, `gap = n>1 ? max(상자+16, (폭−40−margin−상자)/(n−1)) : 108`, `leftX = margin + 상자/2`. 자동 폭이고 어떤 라벨이 안 맞으면(최대 190, `폭−80−16(n−1)`를 n으로 나눈 용량 안에서) 필요 폭만큼 상자를 키운다 |
| 메시지 | 화살은 두 생명선 중심에서 안쪽 7px에서 시작·끝. 라벨 박스 폭 `max(34, textUnits×단위폭+12)`(showcase 6.6·글자 11·높이 18, standard 5.2·글자 9·높이 16) |
| 노트 | 글자 7, 줄 높이 11. 메시지가 건너는 간격 중 가장 넓은 간격(동률은 왼쪽) 안에서 `x = 왼 생명선 + 7 + 12`, 최대 폭 `오른 생명선 − 11 − x`. 넘치면 공백·`/ . - ? & = # _` 뒤·글자 단위로 접고(한자는 단어 분절), 첫 줄 baseline `y+18`, `bottom = y+22+(줄−1)×11` |
| 자동 높이 | `max(327, timelineRequired, legendRequired)`. `timelineRequired = max(내용 바닥 + 65, 모든 메시지 y+18+65)`, 내용 바닥 = max(메시지 `y+6`(노트 있으면 노트 바닥), 활성화 `to`, 구간 `to`). `legendRequired = ceil(내용 바닥 + 12 + 86 + 범례 추가)` |
| 캔버스 | `lifelineTop 142`, `lifelineBottom = viewBox[1] − 65`, 참가자 상자 `y 72, 높이 60` |

**진단(`validateSequence`)**: `sequence/participant-label-overflow`·`participant-sublabel-overflow`(라벨 `textUnits×6.8 > 상자+6`; sublabel은 최소 글자(standard 6, showcase 자동 spread는 가독 하한 이상)로도 `상자−8`에 안 듦; `fixed`이면 수정안에 `column_fit: "spread"` 추가), `sequence/unknown-endpoint`, `sequence/self-message-unsupported`(`from===to`, 수정안 없음), `sequence/note-canvas-limit`·`sequence/note-overlap`(**showcase 전용**: 노트 바닥 > `lifelineBottom+20`, 또는 이후 메시지의 라벨·경로·노트와 겹침; 수정안은 필요한 `viewBox[1]`·`y`), `sequence/segment-message-border-run`(showcase: 구간 경계 y가 메시지 y와 4px 미만), `sequence/segment-label-overlap`(showcase: 구간 라벨이 메시지·노트를 덮음, 가장 가까운 비충돌 `from`을 제안). 나머지는 `layout/constraint`: 참가자 id 중복, 타임라인 120px 미만(**스키마 최솟값 480 때문에 스키마를 통과한 입력으로는 도달하지 못함**), 메시지 y가 `[160, lifelineBottom−18]` 밖, 두 참가자 거리 60px 미만, 헤더 관통, 같은 가로 공간을 쓰는 메시지 y 차이 28 미만, 라벨 겹침, 구간 `to ≤ from`·캔버스 밖, 구간 라벨 폭 초과, 활성화 오류, 마지막 참가자가 `viewBox[0]−40`을 넘음, showcase에서 범례가 못 들어감, 공유 게이트.

**자문(advisory) `inspect-sequence-width`**: 렌더러가 아니라 산출 후 검사기와 `finalize`가 만든다. SVG 루트의 `data-sequence-column-fit`을 가진 HTML에서, `fixed`이고 참가자 4명 이상이며, 노드·경로·라벨 마스크·글자의 오른쪽 끝 최댓값을 뺀 오른쪽 빈 폭이 `2×참가자 폭 중앙값`을 넘고 비율이 0.25를 넘으면 `reviewSuggested:true`. `finalize`가 통과(`ok`)한 sequence에서 이 값을 보고 `layoutReviewRecommendation{action:"inspect-sequence-width", evidence, reason, repair}`를 영수증에 싣는다. 진단 code도 종료 코드도 아니다(권고).

#### F. tree (깊이 수준 B)

입력 `nodes[id,label,parent,sublabel,collapsed]`(루트 1개), `layout{direction,gapX,gapY,nodeW,nodeMaxW}`. `direction: "right"`면 오른쪽, 아니면 아래로(`down`).

| 항목 | 값 |
|---|---|
| 상수 | `margin 32`, `top 64`, 기본 `gapX`/`gapY` = down `28/56`, right `48/18`, `nodeW 140`, `nodeMaxW` = down 220/right 200, `padX 14`, `padY 12`, 글자 라벨 13(루트 14.5)·sublabel 11, 줄 높이 17/14, `toggleR 7.5`, 말단 쌓기 `STACK_MIN 3`·`STACK_GAP 10` |
| 폭 | `floor = max(nodeW, ceil(가장 긴 단어 폭 + 30))`, `cap = ceil(min(nodeMaxW×1.5, max(floor, nodeMaxW)))`, `natural = ceil(max(라벨 폭, sublabel 폭)+30)`, `width = min(cap, max(floor, natural))`. 줄 수가 같게 유지되는 가장 좁은 폭(4px 단위)으로 줄인다(쌓기 항목은 제외). 높이 = `ceil(24 + 근거 머리(18, 근거가 있는 노드) + 줄 수×17 + (sublabel 있으면 4+줄×14))` |
| 말단 쌓기(down만) | 한 부모의 **연속한** 말단 자식 3개 이상 → 들여쓴 목록 하나. 척추 오프셋 = 그 목록이 부모의 유일한 자식 그룹이면 22, 아니면 12, 들여쓰기 = 오프셋+16. 목록은 하나의 폭·행 높이를 공유, 행 간격 10 |
| 띠 | 세대마다 띠 하나(가장 큰 노드의 깊이 축 크기), 같은 세대 노드는 같은 깊이 크기. 띠 시작 = down `64`/right `32`에서 `크기+깊이 간격`씩 누적 |
| 가로축 배치 | 말단부터 `span`(자식 그룹 합 + 간격과 노드 크기의 최댓값)을 재귀로 구해 순서대로 놓고 부모를 첫·마지막 자식 부착점의 중점에 둔다(가운데 자식이 24px 안이면 그 자식 위로 맞춤). 접힘 여부와 무관하게 좌표 고정. 좌표는 반올림 |
| 간선 | down: `[부모 바닥 중앙 → midY → 자식 top 중앙]`(`midY = 자식 띠 시작 − gapY/2`, 중심 차이 2px 미만이면 직선), 쌓기 항목은 척추를 따라 왼쪽에서 진입. right: `[부모 오른쪽 중앙 → midX → 자식 왼쪽 중앙]` |
| viewBox | 자동: 폭 `max(320, ceil(최대 x+폭 + 32 + (right면 11.5)))`, 높이 `max(240, ceil(최대 y+높이 + 32 + (down이면 11.5)))`. 저자 viewBox는 노드가 `viewBox−16` 안에 안 들면 `layout/constraint` |

**진단**: 구조(`Tree structure validation failed`, 묶음 code `tree/structure`): `tree/duplicate-id`, `tree/missing-parent`, `tree/root-count`(루트가 정확히 1개가 아님), `tree/cycle`. 레이아웃: `layout/constraint`(저자 viewBox 넘침).

#### G. timeline (깊이 수준 B)

| 항목 | 값 |
|---|---|
| 상수 | `margin 28`, `top 52`, `axisH 60`, `laneLabelW = lanes 있으면 ceil(max(88, textUnits×13×0.6×1.06+24))` 없으면 0, `axisWidth = layout.width ‖ 960`, `edgePad 72`, `breakW 60`, `laneGap 10`, `lanePad 14`, `stemGap 16`, `rowGap 8`, `cardMaxW 200`, `cardPadX 10`, `cardAccent 12`, 제목 글자 12.5·줄 15, 시간 글자 10.5, `minTickPx 84`, `SEGMENT_FLOOR 28` |
| 입력 | 시각은 오프셋 포함 ISO 8601. 달력 날짜 유효성(2월 30일 거부)을 오프셋과 별도로 확인. 표시 시간대 `meta.timezone ‖ "UTC"`(IANA, 아니면 거부). 이벤트는 `t` 오름차순(동률은 입력 순), 레인이 없으면 가상 레인 `__all`(라벨 없음) |
| 휴지기 | 서로 다른 시각의 인접 간격 중 `길이 > 8×중앙값 && 길이 > 0.1×전체 폭`인 것을 긴 순으로 최대 8개 후보(`layout.breaks:"none"`이면 없음). 후보마다 라벨 `≈ <근사 기간>`, 폭 `max(60, ceil(textUnits×10.5×0.6+18))`. 고정 폭 합(`144 + 28` 시작, 후보마다 `폭+28`)에 `minTickPx`를 더해도 `axisWidth` 안이면 채택 |
| 척도 | `drawable = axisWidth − 144 − Σ휴지기 폭 − 28×구간 수`, `scale = drawable / 선형 시간 합`. 구간 안은 일정한 척도. 모든 시각이 같으면 구간 수로 균등 |
| 눈금 | 후보 간격 `[1,2,5,10,15,30초, 1,2,5,10,15,30분, 1,2,3,6,12시간, 1,2,7일]` 중 `간격×scale ≥ 84`인 첫 값(없으면 7일). 표시 시간대의 벽시계 정시에 놓고(DST로 겹치거나 없는 시각 처리 포함), 눈금이 없는 짧은 구간은 시작점을 눈금으로 쓴다 |
| 카드 | 폭 `ceil(min(200, max(제목 폭, 시간 폭) + 14 + 10))`, 높이 `9+12+줄 수×15+7`. 카드는 이벤트 시각 x를 중심으로 하되 축 영역 `[axisX0+4, axisX1−4−폭]`으로 자른다. 레인마다 카드를 선 위·아래 두 쪽에 행으로 쌓는다: 각 쪽에서 이전 카드와 10px 이상 떨어지는 첫 행(없으면 새 행)을 구해 더 안쪽(작은 행 번호)인 쪽, 동률은 아래. 선 y = `레인 y + 14 + (위쪽 높이 합 + 16, 없으면 10)`, 레인 높이 `max(56, …)` |
| viewBox | 저자 값 없음. `폭 = ceil(axisX1 + 28)`(`axisX1 = 28 + laneLabelW + axisWidth`), `높이 = ceil(마지막 레인 바닥 + 28 + (범례 있으면 34+추가))`. 범례는 `kind`가 2종 이상일 때만 |

**진단**(`timeline/input` 묶음): `timeline/duplicate-id`, `timeline/duplicate-lane-id`, `timeline/unknown-lane`(레인이 있는데 이벤트의 레인이 미정의·누락), `timeline/invalid-timestamp`, `timeline/invalid-timezone`. 레이아웃 진단 없음(카드는 항상 쌓는다).

**시간·기간 서식**(C-37, 관측은 T-28·T-29). 입력은 밀리초 정수 `ms`(`Date.parse`)이고, 시각은 표시 시간대(`meta.timezone ‖ "UTC"`)의 24시간제 벽시계로, 기간은 일·시·분·초로 바꾼다.

| 함수 | 변환 | 쓰이는 곳 |
|---|---|---|
| `clockLabel(ms,{seconds,date})` | `[MM-DD ]HH:mm[:ss[.mmm]]`. `date`면 앞에 `MM-DD `, `seconds`면 `:ss`, 밀리초가 0이 아니면 `.mmm`(3자리 0채움)이 `:ss` 뒤에 붙는다 | 카드 시각: `seconds = showSeconds`(어느 이벤트든 UTC 기준 초·밀리초가 0이 아님), `date = multiDay`(첫·마지막 이벤트가 표시 시간대에서 다른 날). 눈금 라벨: `seconds = tickSeconds`(간격 1분 미만 눈금이 있음), `date = multiDay && 이전 라벨과 MM-DD가 다름`. 노드 맥락(passport): `seconds:true, date:true`에 공백과 `offsetLabel` |
| `offsetLabel(ms)` | 그 시각의 표시 시간대 오프셋을 분으로 반올림해 `UTC+HH:MM` / `UTC-HH:MM` | 노드 맥락, 축 설명(첫 이벤트 시각의 오프셋) |
| `durationLabel(ms)` | 단위 `d`(86400000)·`h`·`min`·`s`를 큰 쪽부터 보며 값이 0이 아닌 단위를 `"<n> <단위>"`로 모으고 2개가 모이면 멈춘다(그 아래 단위는 버림). 모인 게 없으면 `0 s` | 휴지기 `aria-label`(`timeline.break` 문구에 `{duration}`로 들어감) |
| `approximateDuration(ms)` | 가장 큰 단위 `major`(값 ≥ 1)를 고른다. `ms < 1000`이면 `0 s`. `major`가 `s`면 `round(ms/1000) s`. 아니면 다음 작은 단위 `minor`로 `whole = floor(ms/major)`, `rest = round((ms − whole×major)/minor)`, `rest×minor ≥ major`이면 `whole+1`·`rest 0`. `rest`가 0이면 `"<whole> <major>"`, 아니면 `"<whole> <major> <rest> <minor>"` | 휴지기 칩 라벨 `"≈ " + 결과`(폭 하한 60에 반영되는 그 라벨) |

축 설명 줄은 `<timeline.axis 문구>: <구역>[ · <timeline.compressed 문구>]`이고 구역 = UTC면 `UTC`, 아니면 `<IANA 이름> (<offsetLabel(첫 이벤트)>)`에 단일일이면 ` · YYYY-MM-DD`(`multiDay`이면 날짜 생략). 눈금 라벨은 폭 `textUnits×10.5×0.6/2+5` 구간이 이미 놓인 라벨과 겹치면 숨긴다. 문구 본문(`Time`, `Axis break: … without events omitted` 등)은 로케일 카탈로그 키 `timeline.axis`·`timeline.break`·`timeline.compressed`·`timeline.evidence.*`이고 영어 관측은 T-28.

#### H. waterfall (깊이 수준 B)

| 항목 | 값 |
|---|---|
| 상수 | `margin 28`, `top 52`, `axisH 36`, `rowH 25`, `barH 14`, `indent 18`, 이름 글자 12.5·시간 11, `axisWidth = layout.width ‖ 760`, `columnGap 28`, `minTickPx 80`, `NAME_DOT 14`, `LABEL_GAP 7` |
| 입력 | `end` 또는 `duration` 하나(둘 다면 일치해야 함, 허용 오차 1e-9), 둘 다 없으면 `status:"incomplete"`여야 함(열린 막대는 기록된 마지막 시각까지, 라벨 `incomplete, ≥ N ms`). 파생 끝이 비유한이면 거부 |
| 행 | 루트들을 시작 시각(동률은 입력 순) 순으로, 각 span 다음에 그 자식들을 깊이 우선으로. 이름 열 폭 `labelW = ceil(max(140, 깊이×18 + 14 + textUnits×12.5×0.6×1.04))`, `axisX0 = 28 + labelW + 28`, `axisX1 = axisX0 + axisWidth` |
| 척도 | `scale = axisWidth / wall`(`wall = 전체 끝 − 최소 시작`, 0이면 척도 0), `x = round((axisX0 + (t−t0)×scale)×100)/100`, 막대 폭 `max(2, x1−x0)`. 비유한 척도는 `waterfall/invalid-timing` |
| 눈금 | `target = 80/axisWidth×wall`, 간격 = `{1,2,2.5,5}×10ⁿ` 중 `≥ target`인 최소. 눈금은 간격의 배수 시각. 끝점 라벨은 양끝에서 `margin` 안으로 밀어 넣고, 겹치는 중간 라벨은 숨김 |
| viewBox | 저자 값 없음. `폭 = ceil(axisX1 + max(24, 가장 오른쪽 막대 끝 + 7 + 라벨 폭 − axisX1) + 28)`, 행 바닥 = `rowsTop + 행 수×25 + 8`, `높이 = ceil(행 바닥 + 28 + (범례 있으면 34+추가))`. 범례: 서비스가 2개 이상이면 서비스 항목(5색 순환, 같은 색은 한 항목으로 합침) + 쓰인 상태(`error`, `cancelled`, `incomplete`) |

**진단**(`waterfall/input` 묶음): `waterfall/duplicate-id`, `waterfall/invalid-timing`(끝<시작, end·duration 불일치, 끝 정보 없는데 incomplete 아님, 비유한 범위), `waterfall/missing-parent`, `waterfall/cycle`. 레이아웃 진단 없음.

**수·기간 서식**(C-38, 관측은 T-30). 단위 `unit`(`meta.unit`, 기본 `ms`)은 `us`만 `µs`로 바꿔 쓴다(`unitLabel`).

| 함수 | 변환 |
|---|---|
| `number(v)` | `0 < |v| < 0.01`이면 `|v| < 1e-6`은 `Number(v.toPrecision(3)).toString()`(예 `1e-7`), 아니면 `toLocaleString('en-US',{maximumSignificantDigits:3})`(예 `0.0099`). 그 밖은 `round(v×100)/100`을 `toLocaleString('en-US',{maximumFractionDigits:2})`로(천 단위 쉼표, 소수 2자리까지, 끝 0은 생략). 값이 `MAX_VALUE/100`보다 크면 반올림하지 않는다 |
| `formatDuration(v)` | `number(v) + " " + unitLabel` (막대 오른쪽 라벨, 총 시간, 공유율 문구의 총 시간) |
| `percent(v)` | `wall`이 0이면 `100%`. 아니면 `share = v/wall×100`을 `share ≥ 10`이면 정수로, 아니면 소수 1자리로 반올림해 `%`를 붙인다 |
| `timeNumber(t)` | `number(t)`가 원값과 `timeResolution/100`(= `min(눈금 간격, 0보다 긴 span의 duration들)/100`) 이내로 같으면 그것, 아니면 `toPrecision(digits)`로 다시 쓴다(`digits = min(17, max(1, floor(log10|t|) − floor(log10(timeResolution)) + 2))`, 0이면 1). 축 눈금 라벨 `"<timeNumber> <unit>"`, 헤더 범위 `"<t0> → <t1> <unit>"`, 행 문구 `"<시작>–<끝|…> <unit>"`에 쓰인다 |

열린 막대의 오른쪽 라벨은 i18n `waterfall.incomplete`에 `formatDuration`을 넣은 것(영어 관측 `incomplete, ≥ 80 ms`), 행의 접근성 문구는 `"<시작>–<끝> <unit> · <라벨> · <waterfall.share 문구(percent, total)>"`, 헤더는 `waterfall.wall` 문구와 범위 문자열이다.

#### I. 공유 기하 함수 (이 문서에서 쓰는 부분만)

| 함수 | 의미 |
|---|---|
| `anchor(rect, side)` | `left`=(x, cy), `right`=(x+w, cy), `top`=(cx, y), `bottom`=(cx, y+h), 그 밖은 right |
| `legacyDefaultFromSide/ToSide` | `to.cx<from.cx`면 출발 left/도착 right, `>`면 right/left, 같으면 `to.cy>from.cy`로 bottom/top. architecture만 지배 축 추론을 쓰고 나머지 타입은 이 가로 우선 규칙 |
| `automaticPortSpread` | 위 dataflow 표의 포트 규칙. 정렬 키 = 상대 중심(수직 변이면 cy, 수평 변이면 cx), 동률은 `id|from|to|label` 사전순. `gutter 16` |
| `alignAutomaticFacingPorts` | 마주 보는 두 변(좌우 또는 상하)에서 포트 축 차이가 16 미만이고 명시 지오메트리가 없으면, 퍼뜨린 포트가 하나뿐일 때 그 반대편 끝점을 같은 축으로 당겨 직선으로 만든다(모서리 여유와 `accept` 통과 시) |
| `automaticPortRhythmBridge` | 같은 방향 변이고 포트 축 차이가 16 미만이면 24px 스텁(공간이 모자라면 최소 8)을 둔 바깥 채널(±16) 우회 후보를 돌려준다 |
| `labelPoint` | rendering R-32와 같다(`labelAt` → 2점 `[(x0+x1)/2+dx, y0−10+dy]` → 3점 이상 `labelSegment` 중점) |

#### J. erd·class가 `createRouter`에 넘기는 옵션과 효과

라우터 본문(변 쌍 후보 순서, 포트 퍼뜨림, 격자 탐색, 개선 스윕, 결정성)은 [rendering-architecture-routing.md](rendering-architecture-routing.md)의 R/C-ID가 그대로 적용되고, 일반 관계선(trunk·레인·버스가 아닌 것)의 좌표는 그 규칙에서 나온다. 아래는 이 두 렌더러가 기본값에서 바꾼 옵션이 그 규칙의 어느 지점을 바꾸는지다(옵션 기본값: routing 1.3 B).

| 옵션 | erd | class | 바뀌는 지점 |
|---|---|---|---|
| `sideFor` | `legacyDefaultFromSide/ToSide`(가로 우선, 두 엔티티가 있으면 항상 값을 줌) | 1.3 D의 `sideFor`(항상 값을 줌) | routing R-05의 "추론 변". 값이 항상 있어 R-07 팬아웃 변은 쓰이지 않는다 |
| `maxPortSpacing` | 24 | 26 | routing R-05의 포트 간격 `min(14, (변−32)/(n−1))`에서 14를 이 값으로 바꾼다: `min(24 또는 26, (변−32)/(n−1))` (T-09: 간격 24) |
| `preferredCandidates` | `[...trunk 후보, ...레인 후보]` | 없음 | routing R-09 ①. 각 후보는 `[시작, ...후보, 끝]`이 끝점 변 방향·끝점 컴포넌트 비관통·컴포넌트 여유 2px·`routeMeetsCompositionFloors`·해결 경로와 비충돌(`routeConflictsWithResolved`)을 모두 통과할 때만 채택, 아니면 건너뛰고 ②로 간다. 선택된 경로의 안쪽 점이 어떤 선호 후보와 같은 연결은 개선 스윕(routing R-14)에서 제외된다(routing R-14의 "`typeOwned`는 항상 빈 집합"은 architecture 한정) |
| `compositionFloors` | false | 기본 true | routing R-12의 `routeMeetsCompositionFloors`에서 리듬 검사(구간 8 미만·안쪽 16 미만)를 뺀다 |
| `minimumTerminalSegmentPx` | 14 | 기본 0 | 같은 술어에 "점 3개 이상 경로의 첫·끝 구간 맨해튼 길이 ≥ 값"을 더한다(직선 2점은 면제, `compositionFloors`와 무관). 후보 수락·격자 결과 수락·스윕의 `routeIsClear` 모두에 걸린다 |
| `crossingFreeGridFirst` | true | true | routing R-10의 일반 격자 탐색 **앞에** 한 단계를 끼운다. 해결된 경로 중 끝점을 공유하지 않는 것이 하나라도 있을 때만, 갭 `[10, 0]` 각각에 대해 그 경로 전체를 교차 불허 벽(`avoidedSegments`, `allowAvoidedCrossings:false`)으로 두고 R-10과 같은 인자로 탐색한다. 결과가 끝점 컴포넌트 비관통·컴포넌트 여유 2px·해결 경로와 비충돌·비겹침·`routeMeetsCompositionFloors`·`spacedRouteIsClean(갭)`을 모두 만족하면 즉시 채택한다. 못 찾으면 R-10(교차 허용) 탐색으로 간다. 탐색 한 번마다 `gridSearchCount`에 1을 더해 64회 예산을 같이 쓴다 |
| `componentGapPx` | 10 | 10 | 격자 탐색 갭 목록이 `[10, 0]`이 된다(위 단계와 routing R-10 단계 둘 다). 갭 10이면 끝점이 아닌 컴포넌트를 사방 10px 키운 장애물로 먼저 탐색(격자의 `clearance 2`가 더해져 실제로는 13px 떨어짐)하고, 수락되지 않으면 갭 0으로 다시 한다. 갭 > 0의 결과는 `spacedRouteIsClean`(첫·끝 구간 ≥ 16 그리고 리듬 문제 없음. `compositionFloors`가 false여도 적용)도 통과해야 한다 |
| `preferReadableRoutes` | true | true | 개선 스윕 ①~⑤ 켬(routing R-14) |
| `distinctAutomaticPorts` | 기본 false | 첫 시도 false, 버스 롤백이 한 번이라도 있으면 true(1.3 D) | true면 routing R-06·R-09 ⑥·R-12의 끝점 공유 경로 규칙과 포트 간격 확장이 켜진다 |

넘기지 않는 옵션(기본값): `frames []`(경계 프레임이 없으므로 테두리 따라달리기 규칙이 없음), `labelRectFor null`(라우팅 중 라벨 예약과 스윕 ④ 없음. 라벨은 라우팅이 끝난 뒤 `placeAutomaticLabels`가 옮긴다), `readabilityBottomMargin 0`(스윕 ⑥ 없음), `interiorSegmentPx 16`, `microSegmentPx 8`. `meta.quality_profile`·`--quality`는 라우터로 가지 않는다(routing R-26). 두 렌더러의 `pathFor`는 라우터 결과에 trunk·버스 경로를 덮어쓴 것이다(trunk·버스는 1.3 C·D).

#### K. SVG 마크업의 구조

각 타입 렌더러의 `renderSvg`와 요소 함수가 만드는 문자열이 기준이고 C-32~C-35·C-39가 그 코드다(`<style>` 블록의 선택자와 색 변수 포함). 구현자가 먼저 맞춰야 하는 구조만 적는다. 공통: 루트 `<svg viewBox="0 0 W H" …>` 다음에 `svgAccessibleText`, `renderDefinitions(추가 defs)`, `<!-- Background Grid -->` 격자 사각형이 오고(rendering.md C-03·C-09), 노드 그룹은 `focusNodeAttrs`·`focusNodeTitle`, 연결선은 `focusEdgeAttrs`(rendering.md C-03)를 쓴다. 범례는 공유 `renderLegend`(rendering.md C-06)에 타입별 `renderSwatch`를 넘긴 것이다. 노드 글자 위치는 공유 `nodeLabelLayout`(C-40)이 정한다.

| 타입 | 루트에 타입이 더하는 속성(순서) | 본문 순서 |
|---|---|---|
| dataflow | `viewBox`, [`data-reader-fit="intrinsic-height"` (meta.viewBox 없을 때)], `svgRootAttrs`, `data-motion-choreography="stream"` | 스테이지(프레임 `rect[data-graph-role=structural-frame]`+머리글 `text`) → 흐름 경로(자동 교차는 `g[data-graph-role=automatic-crossover]`에 밑선+경로) → 노드 → 흐름 라벨 → 범례 |
| lifecycle | `data-reader-fit="intrinsic-height" data-lifecycle-layout="main-path-v3"`, `svgRootAttrs`, `data-motion-choreography="walk"` | 복합 단계 프레임(`rect[data-lifecycle-frame]`) → 전이 경로(전이마다 `g[data-graph-role=automatic-crossover]`) → 합류점(`circle[data-lifecycle-junction]`) → 상태 → 전이 라벨 → 범례 |
| erd | `svgRootAttrs`, `data-erd-ui="cards"`, [`data-reader-fit="intrinsic-height"`, `data-reader-min-text="7.5"` (meta.viewBox 없을 때)] | defs(카디널리티 마커) + `<style>` → 도메인 띠 → trunk 경로(`data-er-trunk`) → 관계 경로 → 엔티티 → 관계 라벨 → 범례 |
| class | `svgRootAttrs`, `data-class-ui=""`, [intrinsic-height, `data-reader-min-text="7.5"` (meta.viewBox 없을 때)] | defs(UML 마커) + `<style>` → 관계 경로 → 타입 → 관계 라벨 → 범례 |
| sequence | `data-sequence-column-fit="<모드>"`, [`data-reader-fit="width-first"` (meta.viewBox 없을 때)], `svgRootAttrs`, `data-motion-choreography="sequence"` | 구간 프레임 → 생명선 → 활성화 → 메시지 → 구간 라벨 → 참가자 → 범례 |
| tree | `svgRootAttrs`, `data-tree-ui="" data-tree-direction="<방향>"`, [intrinsic-height, `data-reader-min-text="7.5"` (meta.viewBox 없을 때)] | `<style>`(`tree-hue-*`) → 간선 → 노드 → 접기 토글 → "모두 펼치기" 버튼(`g[data-tree-expand-all]`, 폭 `ceil(textUnits×10.5×0.6+24)`·높이 24, `(margin, 18)`) |
| timeline | `svgRootAttrs`, `data-motion-choreography="sweep" data-timeline-ui="" data-reader-fit="intrinsic-height" data-reader-min-text="7.5"`(항상) | 헤더(증거 배지+축 설명) → 레인 → 시간축(눈금, 구간선, 휴지기 `g[data-timeline-break]`) → 줄기 `line[data-timeline-stem]` → 후광 `circle r 7.5` → 핀 `circle r 6.5` → 이벤트 카드 → 범례(kind 2종 이상일 때만) |
| waterfall | `svgRootAttrs`, `data-motion-choreography="replay" data-waterfall-ui="" data-waterfall-unit="<unit>" data-reader-fit="width-first" data-reader-min-text="7.5"`(항상) | `<style>` → 헤더(증거 배지+총 시간) → 시간축 → 부모·자식 안내선 → 행(`g`: `data-waterfall-start/end/duration/depth/status[/service]`) → 범례 |

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | dataflow 노드 측정 | 1.3 A 표: `cx=100+215×stage`, `y=rowYs[row]+yOffset`, 기본 112×58, 스테이지 프레임 폭 168 | 실행 확인(T-01 좌표) |
| R-02 | dataflow viewBox | 자동 폭 `max(480, 내용 오른쪽+24)`, 높이 720. showcase 자동이면 높이 `max(360, 내용 바닥+24+74)` | 실행 확인(638×720, 638×512) |
| R-03 | dataflow 프리셋 라우터와 포트 | 변·포트 간격(`min(18,(변−32)/(n−1))`)·`routeVia` 표 그대로. 둥글리지 않는 꺾은선 | 실행 확인(T-01) / 코드 확인(채널 route) |
| R-04 | dataflow showcase 후처리 7단계 | 1.3 A 목록. 고정 핀이 있는 흐름·노드는 옮기지 않는다. 후보 비용 `길이+굽힘×48+교차×160` | 코드 확인(단계·상수·`gridDetour` 인자, `repairLabelRoutes` 본문은 C-36 → R-42) / 실행 확인(T-26: 격자 우회 1건) |
| R-05 | dataflow 진단 | `node-above-area`(y<104), `node-below-area`, `unknown-endpoint`는 전용 code, 나머지는 `layout/constraint`. 메시지 앞머리 `Data-flow layout validation failed` | 실행 확인(above-area, unknown-endpoint, 잘못된 행) / 코드 확인(나머지) |
| R-06 | dataflow 재시도 | 첫 시도가 레이아웃 오류면 `rebalancePorts=true`로 1회 재시도. 재시도 불가·실패면 첫 진단을 던진다 | 코드 확인 |
| R-07 | lifecycle 분류 | 행 = mainPath 0, 나머지 BFS 거리, 연결 없음 1. 전이 종류 spine/arc/same/between. 괄호는 서명이 같은 묶음이 정확히 1개일 때만 | 코드 확인 / 실행 확인(T-06 괄호) |
| R-08 | lifecycle 상태 크기 | 폭 140..220(식은 1.3 B), 높이 64(같은 행 병렬 전이가 3개 이상이면 그 행만 커짐) | 코드 확인 / 실행 확인(140×64) |
| R-09 | lifecycle 간격 라운드 | 최대 5라운드, 라운드마다 `partner`·`even` 후보 중 라벨이 다 놓이고 `routeCost`가 최소인 것. 간격 증가량 +28/+28/+14/+6, 척추 간격은 가독 폭 예산을 넘으면 고정 | 코드 확인 |
| R-10 | lifecycle 배치·포트·트랙·경로 | 1.3 B 3번 그대로. 선은 반지름 12로 둥글림 | 코드 확인 / 실행 확인(T-06 좌표) |
| R-11 | lifecycle 라벨 | 모드 4종, 후보와 허용 조건은 1.3 B 4번. 전부 실패하면 첫 후보에 두고 미배치로 기록 | 코드 확인 |
| R-12 | lifecycle 캔버스 | 폭 `max(640, 내용 오른쪽+56)`, 높이 `내용 바닥 + (범례가 있으면 78+추가, 없으면 32)` | 실행 확인(678×348) |
| R-13 | lifecycle 진단 | 구조: `duplicate-state`, `unknown-main-path-state`, `repeated-main-path-state`, `unknown-endpoint`, `main-path-gap`, `state-text-too-long`. 배치 중: `crowded-side-transitions`(같은 이웃 쌍 6개 이상). 배치 후: `too-wide`, `label-unplaced`. 구조 오류는 배치 전에, 나머지는 viewBox 계산 후에 던진다 | 실행 확인(`main-path-gap`, `duplicate-state`, `crowded-side-transitions`, `too-wide`) / 코드 확인(나머지) |
| R-14 | erd 엔티티 크기·격자·viewBox | 1.3 C 표. 자동 viewBox 폭 `ceil(최대 x+24)`, 높이 `…+24+34+범례` | 실행 확인(T-09, T-10) |
| R-15 | erd 라벨 요구 간격 | 위 조건(viewBox·pos·route 없음)에서만 인접 열 간격을 라벨 폭+56 이상으로 늘린다 | 코드 확인 |
| R-16 | erd 도메인 띠 | 꽉 찬 직사각형만 띠를 그리고, 못 그리는 태그·off-canvas 캡션·다른 엔티티를 덮는 띠는 `erd/domain-not-drawn`(사유 5종) | 실행 확인(`scattered`, `no-grid`) / 코드 확인(나머지 3종) |
| R-17 | erd 라우터 호출·레인 | 1.3 C의 옵션으로 `createRouter` 호출, 같은 통로 관계는 레인 오프셋 `(i−(n−1)/2)×12` | 코드 확인(옵션·레인, 옵션 효과는 R-41) / 실행 확인(일반 관계선 좌표 T-22~T-25) |
| R-18 | erd trunk | fan-in 우선, 오프셋 후보 `[16,22,12,28]`, 틈 ≤32면 이어 붙임, 32 초과면 분리. 관계 선은 trunk 구간을 뺀 조각 | 실행 확인(T-09) / 코드 확인(후보 오프셋 전체) |
| R-19 | erd 진단 | `header-text-capacity`, `domain-not-drawn`, `attribute-text-capacity`, `layout/marker-capacity`, 나머지 `layout/constraint`(자기 관계 포함) | 실행 확인(marker-capacity, header, 자기 관계, domain 2종) / 코드 확인(attribute) |
| R-20 | class 상자 크기·배치 | 1.3 D 표. 폭 `max(헤더, min(300, max(180, 멤버)))`, 같은 띠 안 세로 가운데, `col:1.5` 허용 | 실행 확인(T-13 `col 1.5`, 상자 34/44 높이) / 코드 확인 |
| R-21 | class 변 선택 | x 구간이 겹치거나 비겹침 일반화면 세로 변, 아니면 가로 우선 | 코드 확인 |
| R-22 | class 버스 | 자동 일반화 2개 이상이 (`to`,`kind`) 같고 간격 ≥40이며 다른 타입을 관통하지 않으면 `busY=round(바닥+간격/2)`의 공유 버스 | 실행 확인(T-13 좌표) |
| R-23 | class 버스 충돌 롤백 | 다른 경로와 충돌하는 버스 묶음은 통째로 취소하고 `distinctAutomaticPorts`로 라우터를 다시 만든다. 반복은 묶음이 줄어드는 만큼 | 코드 확인 |
| R-24 | class 진단 | `title-text-capacity`, `realization-target`, `inheritance-kind`, `inheritance-cycle`, `layout/marker-capacity`, 나머지 `layout/constraint` | 실행 확인(cycle, kind, realization-target) / 코드 확인(나머지) |
| R-25 | sequence 캔버스 폭 | 1.3 E 자동 폭 규칙 | 실행 확인(560, 920) |
| R-26 | sequence 열 기하 | spread: `상자=max(86,min(190,round((폭−124)/n)−24))`, fixed: 86/108. 참가자 중심 `leftX + i×gap` | 실행 확인(T-14 좌표) |
| R-27 | sequence 노트·높이 | 노트는 가장 넓은 간격 안에서 접힌다. 자동 높이 `max(327, 내용+65, 범례)` | 코드 확인 / 실행 확인(327) |
| R-28 | sequence 진단 | 라벨·sublabel overflow, unknown-endpoint, self-message-unsupported는 항상. note-canvas-limit·note-overlap·segment-message-border-run·segment-label-overlap은 showcase만 | 실행 확인(5종) |
| R-29 | sequence 폭 권고 | `finalize`가 통과한 `fixed` sequence에서 참가자 ≥4, 빈 오른쪽 폭 > 2×중앙 참가자 폭, 비율 > 0.25면 `layoutReviewRecommendation.action="inspect-sequence-width"` | 실행 확인(5명 fixed) / 코드 확인(조건) |
| R-30 | tree 구조 | 루트 1개, 부모 선언, 순환 없음. 위반은 `tree/structure` 묶음의 개별 code | 실행 확인(root-count, cycle) |
| R-31 | tree 크기·쌓기 | 폭 식, 말단 연속 3개 이상(down)은 들여쓴 목록 | 실행 확인(T-17 좌표) |
| R-32 | tree 배치·viewBox·간선 | 세대별 띠, 부모는 자식 중앙, 접힘 무관 고정, 자동 viewBox 식, 저자 viewBox는 `−16` 안 | 실행 확인(320×399, 404×314, 372×246) |
| R-33 | timeline 입력 | 오프셋 ISO, 달력 날짜 검증, IANA 시간대, 레인 정의 | 실행 확인(invalid-timestamp, invalid-timezone) / 코드 확인(나머지) |
| R-34 | timeline 휴지기·척도·눈금 | 1.3 G | 실행 확인(T-18 휴지기 1개, 좌표) |
| R-35 | timeline 카드·viewBox | 카드 쌓기 규칙, 폭 `28+laneLabelW+axisWidth+28` | 실행 확인(1016×286, 1104×393) |
| R-36 | waterfall 입력 | end/duration/incomplete 규칙, 부모·순환 | 실행 확인(invalid-timing, missing-parent, cycle) |
| R-37 | waterfall 행·척도·눈금 | 1.3 H | 실행 확인(T-19 좌표) |
| R-38 | waterfall viewBox | 자동 식 | 실행 확인(1121×208 등) |
| R-39 | 번들 예제 | 이 문서가 다룬 8개 타입의 번들 예제 16개가 모두 종료 0, viewBox는 T-20 | 실행 확인 |
| R-40 | 진단 code 매핑 | 문제 문장은 `throwDiagnosticProblems(prefix, problems, {code, subject, diagnostics})`로 던진다. 타입별 상세가 있는 문장은 그 code, 없으면 기본 code(erd·class·dataflow·lifecycle·sequence·tree는 `layout/constraint`, timeline·waterfall·tree 구조는 묶음 code). 공유 게이트의 code는 문장 앞에 `[composition/…]`으로 붙어 `layout/constraint`로 나온다(관측) | 실행 확인(`layout/constraint`+`[composition/label-route-clearance]` 문장) / 코드 확인 |
| R-41 | erd·class 라우터 옵션 | 1.3 J의 옵션 표대로 `createRouter`를 부른다. 일반 관계선 좌표는 rendering-architecture-routing.md의 R/C-ID에 이 옵션(포트 간격 상한 24·26, `crossingFreeGridFirst`, 갭 `[10,0]`, erd의 끝 구간 ≥14·리듬 검사 생략·선호 후보)을 적용해 정한다. 프로파일은 라우터에 가지 않는다 | 코드 확인(옵션 효과) / 실행 확인(T-22~T-25: 직선·한 번 꺾임·갭 13px 우회·교차 잔존) |
| R-42 | dataflow showcase 경로·라벨 수리 | `gridDetour`와 `repairLabelRoutes`의 인자·결과 반영은 1.3 A 3번·6번 (e)와 C-36. 후처리가 경로를 바꾸면(`proposal.labels !== resolvedLabelRects`) 경로 캐시·라벨 점·`viewBox[1]`(`heightForLabels`)·스테이지 프레임 높이를 다시 정하고, 후광 대상 집합(`resolvedCrossoverFlows`)을 자동 흐름끼리의 교차로 다시 만든다. standard 프로파일은 이 후처리가 없어 같은 입력이 `clean-flow/edge-through-node`로 실패한다 | 코드 확인(C-36) / 실행 확인(T-26: showcase만 우회 성공) |
| R-43 | timeline 시간·기간 서식 | 1.3 G 표: `clockLabel`, `offsetLabel`, `durationLabel`, `approximateDuration`과 축 설명 줄, 눈금 라벨 겹침 숨김 | 실행 확인(T-28·T-29) / 코드 확인(C-37) |
| R-44 | waterfall 수·기간 서식 | 1.3 H 표: `number`, `formatDuration`, `percent`, `timeNumber`, `us`→`µs` | 실행 확인(T-30) / 코드 확인(C-38) |
| R-45 | SVG 마크업 구조 | 1.3 K 표의 루트 속성·섹션 순서, 정확한 요소·클래스·`data-*`는 C-32~C-35·C-39. 노드 글자 위치는 C-40 | 코드 확인(C-ID 범위 전체를 읽음) / 실행 확인(8개 타입 루트 속성 이름·섹션 주석 순서가 1.3 K와 일치: [markup.txt](../../../artifacts/archify/spec-demos/rendering/other-types/markup.txt)) |
| R-46 | sequence·erd·class 라벨·마커 충돌 박스 | sequence: 메시지 라벨 박스·경로 박스·구간 라벨 박스(`legacySegmentLabelBox` → `segmentLabelBox`)와 그 진단은 C-41. erd: 카디널리티 글리프 `MARKER_GLYPH_WIDTH 24`·토 x 22·꼭짓점 x 8·원 x 3.5·높이 14, 충돌 박스 `cardinalityGlyphBox`(길이 24, 폭 20), 도메인 캡션 박스 `폭 textUnits(tag)×9×0.65+4`·높이 13은 C-42. class: `markerBox`(길이 `MARKER_REACH 20`, 폭 `MARKER_HALF 10`×2)는 C-43. 모두 shared `placeAutomaticLabels`의 `components`/`titles`로 넘겨 라벨이 피한다 | 코드 확인(C-41~C-43). 경계값 관측은 하지 않음(진단 code·조건은 R-24·R-28) |
| R-47 | dataflow `node-below-area` 수정안과 프로파일 | 수정안: (a) `height ≤ room`이면 `lower yOffset`(`room = (viewBox[1]−74) − 104`); (b) `cap = min(room, areaBottom−y) ≥ 36`이면 `reduce node height to at most cap`; (c) 높이 `R = y+height+74`가 `predictedFixedWidthOverflow({viewBoxWidth, viewBoxHeight:R, readerFit:null}) === null`이면 `raise meta.viewBox[1] to at least R and at most M`(`M = floor(w/1.55)`에서 같은 술어가 통과할 때까지 1씩 내린 값, `M ≤ R`이면 `to R`). 문구 3종과 뒤 문장 2종은 C-05. `--quality`(= `ARCHIFY_QUALITY_PROFILE`)가 `meta.quality_profile`보다 우선하고, 레이아웃 분기(`automaticShowcase`)와 공유 게이트(`qualityProfileForGate`가 환경 변수를 먼저 봄) 둘 다 이 값을 따른다 | 실행 확인(T-31·T-32) / 코드 확인(문구) |

- 불변식: (1) 같은 입력·같은 SHA·같은 환경이면 SVG는 같다. 전제: 시계·난수 없음(`추론`). 타입별 자동 배치는 입력 순서와 id 사전순만 타이브레이커로 쓴다(`추론`: 정렬 키를 읽은 범위에서 확인). (2) 렌더 진단 실패 시 출력 파일은 바뀌지 않는다(rendering R-04). (3) 저자 `pos`·`width`·`height`·`labelAt`·`via` 등 명시 지오메트리는 어느 자동 보정 단계도 옮기지 않는다(dataflow showcase 후처리, erd trunk, 라벨 재배치에서 확인).
- 미결정: **없음**. 이전 U-01~U-06은 모두 해소했다: U-01(erd·class의 `createRouter` 옵션과 일반 관계선 좌표)은 1.3 J·R-41·T-22~T-25와 rendering-architecture-routing.md, U-02(`shortestOrthogonalGridRoute` 사용과 `repairLabelRoutes`)는 1.3 A 3번·6번·R-42·C-36·T-26, U-03(SVG 마크업)은 1.3 K·R-45·C-32~C-35·C-39·C-40·T-27, U-04(시간·기간 서식)는 1.3 G·H·R-43·R-44·T-28~T-30, U-05(라벨·마커 박스)는 R-46·C-41~C-43, U-06(`node-below-area` 수정안·프로파일 영향)은 R-47·T-31·T-32. rendering.md M-03은 완전히 해소했다.
- 확인 한계: 설치본 `/Users/kkh/.claude/skills/archify`로 실행했다(rendering.md 기록상 레포 `archify/`와 바이트 동일). 레포 clone 안의 코드는 실행하지 않았다. 원본 테스트는 열지 않았다. 시각 품질(겹침·가독성)은 보지 않았다. `--layout-json`은 직접 렌더러 호출(erd·class·tree·timeline·waterfall)로 확인했고 공개 `validate --layout-json`은 이 타입들을 받지 않는다(rendering R-05, 이번에도 erd로 재확인: `--layout-json is currently supported for architecture and workflow diagrams only.`). dataflow에는 `--layout-json`이 없어 HTML의 `data-composition-points`에서 좌표를 읽었다. 아래는 코드로만 확인한 부분이다: (1) `repairLabelRoutes`가 제안을 채택하는 입력과 `wrapBlockedFlowLabels`·라벨 이동 후처리가 개입하는 입력은 만들지 못했다(C-36은 읽음, T-26은 격자 우회만 실행). (2) erd·class 개선 스윕이 어느 단계에서 경로를 바꿨는지는 단계별로 추적하지 않았다(T-22의 직선화, T-24·T-25의 교차 잔존은 결과 좌표만 관측). (3) R-46의 라벨·마커 박스 경계값은 관측하지 않았다. (4) 브랜드 마크(`renderBrandMark`, `brandMetadataFor`, `brandLabelFitWidth`)는 이 스펙의 범위 밖이다(기능 범위의 `brands` 제외). `brand`가 있는 노드의 마크업은 이 스펙만으로는 재현되지 않는다.

### 1.5 필수 코드 참조 [필수]
기준은 frontmatter SHA. 라이선스는 Apache-2.0(overview 1절). 경로는 `archify/renderers/` 기준(저장소 루트의 `archify/` 아래).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `dataflow/dataflow-compiler.mjs:62-146` `build`의 상수·자동 폭·`stageX`·`measureNode` | 상수와 노드 좌표, 자동 폭, showcase 자동 노드 폭 | R-01, R-02 |
| C-02 | `dataflow/dataflow-compiler.mjs:569-717` `routeVia`,`flowSides`,`pathFor` | 프리셋 라우터와 포트 적용, 중복점 제거 | R-03 |
| C-03 | `dataflow/dataflow-compiler.mjs:154-245,761-1006` | showcase 포트 재균형·노드 높이 확장·경로 수리·교차 해소·포트 재정렬 | R-04 |
| C-04 | `dataflow/dataflow-compiler.mjs:1008-1380` + `dataflow/label-capacity.mjs:1-81` | 라벨 크기·기본점·showcase 라벨 후처리 파이프라인, 두 줄 접기 | R-04 |
| C-05 | `dataflow/dataflow-compiler.mjs:250-562,1575-1605` `validateDataflow`,`attempt` | 진단 목록과 재시도 규칙 | R-05, R-06 |
| C-06 | `lifecycle/render-lifecycle.mjs:25-232` | 상수·상태 폭·분류·괄호·프레임 | R-07, R-08 |
| C-07 | `lifecycle/render-lifecycle.mjs:204-242` | 간격 라운드, `routeCost` | R-09 |
| C-08 | `lifecycle/render-lifecycle.mjs:244-491` `layout` | 척추·행·호·포트·트랙·경로 | R-10 |
| C-09 | `lifecycle/render-lifecycle.mjs:493-790` | 프레임 출구, `placeRow`, 호 수준, 포트 배분·스냅, 트랙 배정 | R-10 |
| C-10 | `lifecycle/render-lifecycle.mjs:792-853` `placeLabels` | 라벨 모드·후보·허용 조건 | R-11 |
| C-11 | `lifecycle/render-lifecycle.mjs:855-977` | 구조·레이아웃 진단, 범례 항목, viewBox | R-12, R-13 |
| C-12 | `erd/grid.mjs:1-150`, `erd/render-erd.mjs:60-83,134-200` | 기본 격자·띠 격자·엔티티 크기·라벨 요구 간격 | R-14, R-15 |
| C-13 | `erd/render-erd.mjs:202-322,1095-1151` | 도메인 띠 조건·상자·거부 사유 | R-16 |
| C-14 | `erd/render-erd.mjs:503-526,528-626` | 자동 viewBox, 라우터 옵션, 레인 | R-14, R-17 |
| C-15 | `erd/render-erd.mjs:628-931,1024-1042` | trunk 묶음·후보·그리기·레인 후보 | R-18 |
| C-16 | `erd/render-erd.mjs:1074-1357` `validateEr` | 진단 전체 | R-19 |
| C-17 | `class/render-class.mjs:62-260,282-300` | 상수·상자 크기·접기·배치·관계 표기 | R-20 |
| C-18 | `class/render-class.mjs:359-534` | 자동 viewBox, `sideFor`, 버스, 롤백 반복 | R-21~R-23 |
| C-19 | `class/render-class.mjs:536-566,619-819` | 라벨 기본점, 순환 검사, 진단 | R-24 |
| C-20 | `sequence/render-sequence.mjs:13-165` | 자동 폭·spread 기하·fixed | R-25, R-26 |
| C-21 | `sequence/render-sequence.mjs:167-337` | 노트 접기·자동 높이·캔버스 상수 | R-27 |
| C-22 | `sequence/render-sequence.mjs:554-930` `validateSequence` | 진단 | R-28 |
| C-23 | `archify/scripts/check-render-output.mjs:955-1032`, `archify/bin/finalize.mjs:700-708` | 폭 권고 조건과 영수증 필드 | R-29 |
| C-24 | `tree/render-tree.mjs:28-322` | 상수·구조 검증·접기·쌓기·폭·띠·배치 | R-30~R-32 |
| C-25 | `tree/render-tree.mjs:319-390` | viewBox·간선·캔버스 검사 | R-32 |
| C-26 | `timeline/render-timeline.mjs:34-66,136-295` | 상수·입력 정렬·휴지기·척도·눈금 | R-33, R-34 |
| C-27 | `timeline/render-timeline.mjs:297-391` | 카드·레인 쌓기·viewBox | R-35 |
| C-28 | `waterfall/render-waterfall.mjs:35-130` | 상수·타이밍 검증·행 | R-36 |
| C-29 | `waterfall/render-waterfall.mjs:160-270` | 척도·눈금·행 배치·viewBox | R-37, R-38 |
| C-30 | `shared/geometry.mjs:1517-1527,1543-1612,1615-1700,1703-1795,1800-1816,1868-1880` | `anchor`,`alignAutomaticFacingPorts`,`automaticPortRhythmBridge`,`automaticPortSpread`,`legacyDefault*`,`labelPoint` | R-03, R-04, R-21 |
| C-31 | `shared/desktop-readability.mjs:1-35`, `shared/text-fit.mjs:24-52` | 930px 투영, 최소 글자, 글자 폭 계수·패딩 | R-09, R-13, R-26 |
| C-32 | `dataflow/dataflow-compiler.mjs:1384-1575` | 스테이지 머리글(줄바꿈), 스테이지 프레임, 노드, 흐름 경로·라벨, 범례 카탈로그와 스와치, 루트 `renderSvg` | R-45 |
| C-33 | `lifecycle/render-lifecycle.mjs:988-1134` | 상태(최종·시작 마커·단계 번호), 전이 경로(교차 밑선), 라벨, 범례 스와치, 루트 | R-45 |
| C-34 | `erd/render-erd.mjs:86-135,282-332,1376-1588` | 키 배지 상수·`keyRoles`·배지, 도메인 띠 마크업, 엔티티 행, 관계 경로·라벨, 범례, 루트와 `<style>` | R-45 |
| C-35 | `class/render-class.mjs:282-345,898-1095` | `NOTATION`·`GLYPH`·마커 defs, 멤버 행, 타입, 관계 경로·라벨, 범례, 루트와 `<style>` | R-45 |
| C-36 | `dataflow/joint-label-routing.mjs:1-165` | `repairLabelRoutes`와 헬퍼 전부(후보 생성·정렬·16개 제한·32회 탐색 한도·격자 호출 인자·종료 조건). 호출부는 C-04의 `dataflow-compiler.mjs:1359-1382` | R-04, R-42 |
| C-37 | `timeline/render-timeline.mjs:112-134,138-182,291,398-495` | 시간대 보조 함수, `clockLabel`·`durationLabel`·`approximateDuration`, `tickSeconds`, 축·헤더·레인·이벤트 마크업 | R-43 |
| C-38 | `waterfall/render-waterfall.mjs:30-32,131-144,197-206,238-246,273-336` | 단위 라벨, `number`·`percent`·`timeNumber`, 축 라벨, 헤더·축·안내선·행 마크업 | R-44 |
| C-39 | `sequence/render-sequence.mjs:932-1105`, `tree/render-tree.mjs:405-573`, `timeline/render-timeline.mjs:377-576`, `waterfall/render-waterfall.mjs:338-413` | 4개 타입의 요소 함수·범례·루트 | R-45 |
| C-40 | `shared/text-fit.mjs:54-104` `nodeLabelLayout` | 노드 글자 x·행 y·장식 위치(아이콘 오른쪽으로 밀기, 장식 아래 행으로 내리기, 압축 배치) | R-45 |
| C-41 | `sequence/render-sequence.mjs:364-535` | `messageGeometry`·`messageLabelBox`·`messageRouteBox`, 구간 라벨 배치와 오류 위치 판정 | R-46 |
| C-42 | `erd/render-erd.mjs:333-430,951-1022` | 카디널리티 글리프 상수와 기하, 충돌 박스 `cardinalityGlyphBox`, 라벨 배치 호출 | R-46 |
| C-43 | `class/render-class.mjs:570-613` | `markerBox`와 라벨 배치 호출 | R-46 |

### 1.6 수락 사례 [필수]
출처: 모두 실행 관찰이다(설치본 `archify render`, 필요한 곳은 직접 렌더러 `--layout-json`). 입력 [in/](../../../artifacts/archify/spec-demos/rendering/other-types/in/)(`gen.py`가 생성), 스크립트 [run.sh](../../../artifacts/archify/spec-demos/rendering/other-types/run.sh)·[observe.sh](../../../artifacts/archify/spec-demos/rendering/other-types/observe.sh)·[extract.py](../../../artifacts/archify/spec-demos/rendering/other-types/extract.py), 결과 [summary.txt](../../../artifacts/archify/spec-demos/rendering/other-types/summary.txt)·[points.txt](../../../artifacts/archify/spec-demos/rendering/other-types/points.txt)·[observed.txt](../../../artifacts/archify/spec-demos/rendering/other-types/observed.txt). 출력 HTML은 용량 때문에 삭제했고 `python3 -I gen.py && sh run.sh`로 재생성된다. T-22~T-32는 같은 폴더의 추가 스크립트다: 일반 관계선 [gen-routes.py](../../../artifacts/archify/spec-demos/rendering/other-types/gen-routes.py)·[observe-routes.sh](../../../artifacts/archify/spec-demos/rendering/other-types/observe-routes.sh)(결과 [routes.txt](../../../artifacts/archify/spec-demos/rendering/other-types/routes.txt), 입력은 `in/`에 `erd.r*`·`cl.r*`·`df.r1.*`로 추가됨), 시간·수 서식 [time-formats.py](../../../artifacts/archify/spec-demos/rendering/other-types/time-formats.py)(결과 [time-formats.txt](../../../artifacts/archify/spec-demos/rendering/other-types/time-formats.txt)), U-06 [u06.py](../../../artifacts/archify/spec-demos/rendering/other-types/u06.py)(결과 [u06.txt](../../../artifacts/archify/spec-demos/rendering/other-types/u06.txt)), 마크업 [markup-observe.py](../../../artifacts/archify/spec-demos/rendering/other-types/markup-observe.py). 모두 설치본을 쓰고 HTML은 만든 즉시 지운다. 입력 이름을 괄호로 표기한다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 R-02 R-03 | (`df.std`) 스테이지 3(In/Mid/Out), 노드 a(0,행0) b(1,행1) c(2,행0) d(2,행2), 흐름 a→b, b→c, b→d, a→c, standard | `viewBox 0 0 638 720`(530+84+24). 경로 `a→b 156,166;207.5,166;207.5,271;259,271`, `b→c 371,262;422.5,262;422.5,166;474,166`, `b→d 371,280;422.5,280;422.5,385;474,385`, `a→c 156,148;474,148`(a의 오른쪽 포트 2개가 148/166으로 ±9 퍼짐, c의 왼쪽 포트도 a→c가 148, b→c가 166이라 a→c는 두 끝 y가 같아 직선, b의 오른쪽 포트 262/280) |
| T-02 | R-02 R-04 | (`df.show`) T-01 입력에 `quality_profile:"showcase"` | `viewBox 0 0 638 512`(노드 d 바닥 414+24+74), 경로는 T-01과 같음(교차·충돌이 없어 후처리가 아무것도 바꾸지 않음) |
| T-03 | R-05 | (`df.unknown`) 흐름의 `to`를 `zzz` | 종료 1, `[dataflow/unknown-endpoint]`, 수정안 노드 id 제안 |
| T-04 | R-05 | (`df.above`) 노드 b에 `yOffset -150` | 종료 1, `[dataflow/node-above-area] … keep y at or above 104`, 이어서 `layout/constraint` 라벨-노드 겹침 문장 |
| T-05 | R-05 | (`df.badrow`) 노드 b의 `row: 9` | 종료 1, 전용 code 없이 `[layout/constraint]` 두 문장(invalid row 9 — valid rows are 0..4, non-finite coordinates) |
| T-06 | R-07 R-08 R-10 R-12 | (`lc.basic`) mainPath a,b,c, 상태 e·d 추가, 전이 a→b "submit", b→c "ok", b→d "no", a→e "park", e→a "resume" | `viewBox 0 0 678 348`. 척추 `a→b 196,60;270,60`(간격 74 = 라벨 폭 48+26), `b→c 410,60;482,60`(간격 72), `b→d 340,92;340,184`, `a→e 113,92;113,184`, `e→a 139,184;139,92`(행 0 y28..92, 행 1 y184 = 92+34+58) |
| T-07 | R-07 R-10 | (`lc.bracket`) a→d, b→d 가 같은 라벨 "abort"(a,b는 연속 mainPath) | 두 전이가 `232,102;232,184` 한 경로를 공유(프레임 바닥 102, 프레임 출구 x 232), `viewBox 0 0 677 348` |
| T-08 | R-13 | `lc.gap`(mainPath b→c 전이 없음), `lc.dup`(상태 id 중복), `lc.crowded`(같은 이웃 d–e 6전이), `lc.wide`(상태 12개, 긴 라벨) | 각각 종료 1: `[lifecycle/main-path-gap]`, `[lifecycle/duplicate-state]`, `[lifecycle/crowded-side-transitions] 6 transitions between … at most five stay legible`, `[lifecycle/too-wide] The lifecycle is 4402px wide; at 10px text it stays readable on a desktop only up to 1550px` |
| T-09 | R-14 R-17 R-18 | (`erd.trunk`) 엔티티 p(행1,열1), c1·c2·c3(열0, 행0·1·2) 각 속성 6개(높이 156), 관계 c1→p, c2→p, c3→p | `viewBox 0 0 592 654`. 엔티티 x32/y40·240·440, p x328(gapX 56)·y240. p 왼쪽 포트 294/318/342(간격 24). 경로 `c1→p 272,118;312,118;312,294;328,294`, `c2→p 272,318;328,318`, `c3→p 272,518;312,518;312,342;328,342`. trunk 2개 `312,118;312,294`, `312,342;312,518`(trunk x = 328−16, 두 조각 사이 틈 48>32라 이어지지 않음) |
| T-10 | R-19 | (`erd.fan`) T-09와 같되 속성 1개(높이 56) | 종료 1, `[layout/marker-capacity] Entity "p" shares its left side with 3 relationship ends: their ports would sit 12px apart, under the 14px a cardinality glyph is tall` |
| T-11 | R-16 | (`erd.band`) a,b(`sales`, 행0 열0·1), c(`ops`, 행1 열0), 관계 a→c, b→a "owns" | `viewBox 0 0 625 254`. 띠 sales `x20 y22 w593 h82`(= 32−12, 40−18, 56+18+8), ops `x20 y122 w264 h82`. 관계 `a→c 152,96;152,140`, `b→a 361,68;272,68`(라벨 "owns"가 열 간격을 56→89로 키움: `ceil(32.3+56)`) |
| T-12 | R-16 R-19 | `erd.L`(a,b,c 같은 태그가 L자 3셀, z 다른 셀), `erd.nogrid`(태그 멤버 a가 `pos`), `erd.self`(a→a), `erd.hdr`(제목 긴 엔티티 `width 100`) | 종료 1 각각 `[erd/domain-not-drawn]`(`scattered`), `[erd/domain-not-drawn] … "a" have no grid cells`(`no-grid`), `[layout/constraint] Relationship 0 connects entity "a" to itself`, `[erd/header-text-capacity]` |
| T-13 | R-20 R-22 | (`cl.bus`) interface `base`(행0 열1), class x·y·z(행1 열0·1·2), x·y·z→base realization | `viewBox 0 0 852 260`. base x340 y40 w180 h44, x·y·z y168 h34. 버스 `x→base 122,168;122,126;430,126;430,84`, `y→base 430,168;430,84`(cx 같음 → 직선), `z→base 738,168;738,126;430,126;430,84`(busY = 84+84/2 = 126). (`cl.half`) 열 0·2·반칸 1.5 → `viewBox 0 0 672 250`, m→p 경로 `359,174;196,174;196,74` |
| T-14 | R-24 | `cl.cycle`(p↔q inheritance), `cl.kind`(class→interface inheritance), `cl.real`(class→class realization) | 종료 1 각각 `[class/inheritance-cycle]`(+같은 셀 쌍의 `layout/marker-capacity`), `[class/inheritance-kind]`, `[class/realization-target]` |
| T-15 | R-25 R-26 | (`sq.spread3`) 참가자 3(A,B,C), 메시지 2 / (`sq.fixed3`) 같은 입력 + `column_fit:"fixed"` | spread3: `viewBox 0 0 560 327`, 상자 x 62·230.5·399 폭 121(gap 168.5). fixed3: `0 0 920 327`, 상자 x 19·127·235 폭 86(gap 108) |
| T-16 | R-28 | `sq.longlabel`(fixed, 34자 라벨, viewBox [480,480]), `sq.self`, `sq.notelimit`(showcase, 노트 5줄, y 397), `sq.noteoverlap`(showcase, 같은 간격 y 180·200), `sq.borderrun`(showcase, 구간 `from`=메시지 y 180) | 종료 1: `[sequence/participant-label-overflow] … (~231px) is wider than component "a" (86px)`, `[sequence/self-message-unsupported]`, `[sequence/note-canvas-limit] … ends at y=463, below the canvas content limit y=435 … Fix: set /meta/viewBox/1 to 561`, `[sequence/note-overlap] … move "next" … y=268 … Fix: set /messages/1/y to 268`(+ `layout/constraint` 간격 28 미만·`[composition/label-route-clearance]`), `[sequence/segment-message-border-run] … Fix: set /segments/0/from to at least 184 …`(+`[composition/container-border-run]`) |
| T-17 | R-29 | (`sq.fixed5`) 참가자 5(`P a..e`), 메시지 1(a→e), fixed / (`sq.spread5`) 같은 입력 spread. `finalize sequence … --json` | fixed5: 영수증 `ok:true`, `layoutReviewRecommendation.evidence = {measured:true, columnFit:"fixed", participantCount:5, occupiedRight:537, canvasWidth:920, emptyRightPx:383, emptyRightRatio:0.416, typicalParticipantWidth:86, reviewSuggested:true}`. spread5: 권고 없음 |
| T-18 | R-31 R-32 R-30 | (`tr.stack`) 루트 + 말단 4 / (`tr.right`) 같은 입력 `direction:right` / (`tr.two`) 말단 2 / `tr.roots`(루트 2), `tr.cycle` | stack: `viewBox 0 0 320 399`, 말단 x70 y161·212·263·314 폭 140 높이 41(들여쓰기 38, 행 간격 41+10), 루트 x32 y64. right: `0 0 404 314`. two: `0 0 372 246`. 오류: `[tree/root-count] … 2 nodes have no parent`, `[tree/cycle]` |
| T-19 | R-33 R-34 R-35 | (`tl.break`) 이벤트 5(10:00, 10:05, 10:10 같은 날, 4일 뒤 2개) / (`tl.lanes`) 레인 2·이벤트 3 / `tl.badts`(2월 30일), `tl.tz`(`Not/AZone`) | break: `viewBox 0 0 1016 286`, 휴지기 1개(`x 594.67..654.67`, 길이 345600000ms), 구간 `x0 114..580.67`·`668.67..902`, 척도 46.667px/분, 눈금 간격 2분, 카드 폭 94 높이 43. lanes: `0 0 1104 393`(= 28+88+960+28). 오류: `[timeline/invalid-timestamp]`, `[timeline/invalid-timezone]` |
| T-20 | R-36 R-37 R-38 | (`wf.inc`) root 0~100, 자식 start 20 `incomplete` / `wf.bad`(root에 end·duration 불일치, 자식 끝 없음·부모 없음) / `wf.cycle` | inc: `viewBox 0 0 1121 208`, 축 `x 196..956`(28+140+28), 7.6px/ms, 자식 막대 `x 348..956` 라벨 `incomplete, ≥ 80 ms`, 행 y 88·113. bad: `[waterfall/invalid-timing]`×2, `[waterfall/missing-parent]`. cycle: `[waterfall/cycle]` |
| T-21 | R-39 | 번들 예제 16개: `orders.erd`, `subscription-billing.erd`, `payments.class`, `payment-processors.class`, `agent-run.lifecycle`, `deployment-release.lifecycle`, `async-job-roundtrip.sequence`, `cache-miss-request.sequence`, `product-analytics.dataflow`, `event-stream.dataflow`, `payment-platform.tree`, `archify-repository.tree`, `payment-incident.timeline`, `archify-dev-activity.timeline`, `checkout-request.waterfall`, `example-rebuild.waterfall` | 모두 종료 0, viewBox 순서대로 999×488, 1230×678, 993×430, 1640×918, 1152×500, 1284×680, 820×920, 1080×580, 1080×520, 1080×780, 1069×396, 1841×926, 1123×485, 1580×924, 1089×308, 1216×783 |
| T-22 | R-41 | (`erd.r1`) 엔티티 a(행0 열0)·b(행0 열1) 속성 1개씩(높이 56), a→b / (`erd.r2`) b가 속성 4개(높이 116) / (`erd.r4`) a(행0)·b(행1) 같은 열 | r1: `viewBox 0 0 592 154`, `272,68;328,68`. r2: `272,68;328,68`(두 중심 y가 30 다른데도 직선, 개선 스윕의 마주 보는 직선 단계로 추정(추론)). r4: `152,96;152,140`(세로 변) |
| T-23 | R-41 | (`erd.r3`) 같은 행에 a·m·c, 관계 a→c(m이 막음) / (`erd.r6`) 같은 입력에 라벨 "uses" | `viewBox 0 0 888 154`. `272,68;315,68;315,27;600,27;600,68;624,68`: 315 = m.x 328 − 갭 10 − clearance 2 − 1, 27 = m.y 40 − 13, 600 = c.x 624 − 끝 스텁 24. 위쪽 우회(동률인 아래 우회는 채택되지 않음). 라벨이 있어도 같은 경로 |
| T-24 | R-41 | (`erd.r5`) a(0,0) b(0,1) c(1,0) d(1,1), 관계 a→d, b→c | `a→d 272,68;300,68;300,168;328,168`, `b→c 448,96;448,118;152,118;152,140`. 두 선이 (300,118)에서 교차한 채 남는다(`crossingFreeGridFirst`가 켜져 있어도 교차 없는 경로가 항상 나오지는 않는다. 원인 단계는 추적하지 않음) |
| T-25 | R-41 | class 같은 형태: (`cl.r1`) 가로 인접 / (`cl.r2`) b가 속성 3개 / (`cl.r3`) 가운데가 막음 / (`cl.r4`) 같은 열 / (`cl.r5`) X 배치 | r1: `212,57;340,57`. r2: `212,92;340,92`(a가 띠 안에서 세로 가운데 정렬되어 cy가 같음). r3: `212,57;327,57;327,27;624,27;624,57;648,57`(327 = 340 − 13, 624 = 648 − 24). r4: `122,74;122,158`. r5: `a→d 212,57;276,57;276,175;340,175`, `b→c 430,74;430,116;122,116;122,158`(교차 잔존) |
| T-26 | R-04 R-42 | (`df.r1.show`) 스테이지 3, 같은 행에 a·b·c, 흐름 a→b "one", b→c "two", a→c "skip", showcase / (`df.r1.std`) 같은 입력 standard | show: 종료 0, `viewBox 0 0 638 360`, `a→c 156,166;244,166;244,113;450,113;450,148;474,148`(244 = b.x 259 − 노드 여유 12 − 2 − 1, 113 = b.y 128 − 15, 450 = c.x 474 − 스텁 24). std: 종료 1, `[clean-flow/edge-through-node] … crosses node "b"`와 라벨-노드 겹침 `layout/constraint` |
| T-27 | R-45 | (markup-observe.py) 8개 타입 최소 입력(`df.std`, `lc.basic`, `erd.band`, `cl.bus`, `sq.spread3`, `tr.stack`, `tl.break`, `wf.inc`)을 렌더해 루트 `<svg>` 속성 이름 순서와 본문 섹션 주석 순서를 읽음 | 1.3 K 표와 같다(예: timeline 루트 `viewBox, role, lang, aria-labelledby, data-animation, data-preset, data-quality-profile, data-quality-gates, data-motion-choreography, data-timeline-ui, data-reader-fit, data-reader-min-text`, 섹션 `Lanes → Time axis → stems → halo → Events → Legend`). `data-quality-gates`는 프로파일이 없을 때(advisory)의 값. [markup.txt](../../../artifacts/archify/spec-demos/rendering/other-types/markup.txt) |
| T-28 | R-43 | (time-formats.py) 이벤트 3개: 0, +1분, +1분+gap | 칩 라벨 / `aria-label`: gap 15h3s → `≈ 15 h` / `15 h 3 s`; 1d1h30m → `≈ 1 d 2 h` / `1 d 1 h`; 59m40s → `≈ 59 min 40 s` / `59 min 40 s`; 23h59m40s → `≈ 24 h`(올림 승격) / `23 h 59 min`; 10m → `≈ 10 min`; 2d → `≈ 2 d`; 3d12h → `≈ 3 d 12 h`; 45s는 휴지기 아님(중앙값 규칙) |
| T-29 | R-43 | 같은 스크립트: 시각 라벨 | `10:00`·`10:05`(분 단위 같은 날, 축 설명 `Time: UTC · 2026-10-01`), 초가 있으면 `10:00:30`, 밀리초가 있으면 `10:00:00.250`, 다중일 `10-01 22:00`·`10-02 02:00`(축 설명 `Time: UTC`, 눈금 `10-01 22:00`·`22:30`·…), `Asia/Seoul`이면 `19:00`(설명 `Asia/Seoul (UTC+09:00) · 2026-10-01`), `Asia/Kolkata` `15:30`(`UTC+05:30`), `America/New_York` 2026-03-08(DST 시작): 눈금 `01:00`·`01:30`·`03:00`(존재하지 않는 02시 건너뜀), 노드 맥락 `03-08 01:00:00 UTC-05:00`·`03-08 05:00:00 UTC-04:00` |
| T-30 | R-44 | 같은 스크립트: 루트 0~X, 자식 0~k | `100`/`40` → `100 ms`·`40 ms`·`100%`·`40%`; `100.456`/`33.333` → `100.46 ms`·`33.33 ms`·`33%`; `1234567.891`/`500000` → `1,234,567.89 ms`·`500,000 ms`·`41%`; `0.005` → `0.005 ms`; `1e-7` → `1e-7 ms`; 루트 `0.0123`·자식 `0.0099` → 총 시간과 루트 라벨 `0.01 ms`(`number`가 반올림), 자식 `0.0099 ms`·`80%`; 자식 12.6 → `13%`, 3.14 → `3.1%`; `unit:"us"` → `µs`; 행 문구 `0–40 ms · 40 ms · 40% of 100 ms wall-clock` |
| T-31 | R-47 | (u06.py A·B2·B3) 노드 b `yOffset 400`(자동 캔버스) / 같은 입력 `viewBox [1400,720]` / 노드 b `row 3, height 300` | 모두 종료 1 `[dataflow/node-below-area]`. 자동 캔버스: 수정안 `lower yOffset`만, 문구 `keep y within [104, 588] … Raising meta.viewBox[1] to 774 would fit the node, but the page then reaches at least ~2296px … compact the node instead`, `maximumViewBoxHeight 309`. 1400: 수정안 `lower yOffset`+`raise meta.viewBox[1] to at least 774 and at most 903 …`. 키 큰 노드: `lower yOffset`+`reduce node "b" height to at most 176`(= min(542, 646−470)) |
| T-32 | R-47 | (u06.py C·D) 건너뛰기 흐름 입력과 교차 입력에 프로파일 조합 | 건너뛰기: meta 없음 → 종료 1(`clean-flow/edge-through-node`), meta standard+`--quality showcase` → 성공(`638×360`), meta showcase+`--quality standard` → 종료 1, meta showcase → 성공, meta 없음+`--quality showcase` → 성공, 환경 변수 `ARCHIFY_QUALITY_PROFILE=showcase` → 성공. 교차: standard·meta 없음 → 종료 1(`layout/constraint`), showcase·standard+`--quality showcase` → 성공(`480×512`) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
읽은 범위: dataflow `dataflow-compiler.mjs` 1~1605행 전부(250~385 `validateDataflow` 앞부분과 `node-below-area`, 770~915 수리 패스, 1335~1575 라벨 후처리·마크업 포함), `label-capacity.mjs` 전체, `joint-label-routing.mjs` 1~165행 전부, `geometry.mjs`의 포트·변·라벨 함수, `desktop-readability.mjs` 전체. lifecycle `render-lifecycle.mjs` 1~1134행. erd `render-erd.mjs` 60~632, 805~1030, 1376~1588행과 `grid.mjs` 전체. class `render-class.mjs` 56~620, 898~1095행. sequence `render-sequence.mjs` 10~545, 554~930, 932~1105행. tree `render-tree.mjs` 28~397, 405~573행. timeline 34~495, 496~576행. waterfall 30~336, 338~413행. 라우터 쪽은 `routing.mjs`의 옵션 사용 지점(`crossingFreeGridFirst`·`componentGapPx`·`minimumTerminalSegmentPx`·`compositionFloors`·`preferredCandidates`·`typeOwned`·`readabilityBottomMargin`, 40~170, 405~440, 540~690, 1190~1215행)과 `route-quality.mjs`의 `accept` 처리(370~385, 495~520행). 나머지 라우터 본문은 rendering-architecture-routing.md가 읽었다. 열지 않음: 원본 테스트, 브랜드 마크 코드.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 R-02 | C-01, T-01 T-02 | 코드를 읽고 좌표·viewBox를 실행으로 대조(식과 일치) |
| R-03 | C-02 C-30, T-01 | 포트 148/166, midX 207.5가 식과 일치. `vertical-channel` 등 채널 route는 코드만 |
| R-04 | C-03 C-04 | 단계와 상수는 읽음. T-02는 후처리가 무변경인 경우, T-26은 격자 우회가 개입하는 경우. 교차 해소·라벨 공동 수리가 개입하는 입력은 실행하지 못했다(1.4 확인 한계 (1)) |
| R-05 R-06 | C-05, T-03~T-05 | 진단 code 실행 확인. 재시도 성공 경로는 실행하지 못함 |
| R-07~R-13 | C-06~C-11, T-06~T-08 | `lc.basic`·`lc.bracket` 좌표가 식(간격 74/72, 행 y 184, 프레임 바닥 102)과 일치. 호(arc)·루프·트랙 배정은 코드만 |
| R-14~R-19 | C-12~C-16, T-09~T-12 | trunk 좌표(312=328−16)·포트 간격 24·띠 상자가 식과 일치. 라우터 옵션 효과는 R-41(1.3 J) |
| R-20~R-24 | C-17~C-19, T-13 T-14 | 버스 y(126)·좌표 일치. 일반 관계선은 T-25 |
| R-25~R-28 | C-20~C-22, T-15 T-16 | spread3 상자 x(62, 230.5, 399)가 식과 일치. 한 사례(`sq.noteoverlap`)에서 공유 게이트 문장이 같이 나옴 |
| R-29 | C-23, T-17 | 5명 fixed 사례에서 `reviewSuggested:true` 실행 확인, 그 외 조건(참가자<4, 비율≤0.25)은 코드 |
| R-30~R-32 | C-24 C-25, T-18 | 좌표(70, 161, 51 간격, 399) 일치 |
| R-33~R-35 | C-26 C-27, T-19 | 휴지기 1개·척도 46.667 일치. 눈금·휴지기 라벨 서식은 R-43(T-28·T-29) |
| R-36~R-38 | C-28 C-29, T-20 | 축 x 196..956, 7.6px/ms 일치 |
| R-39 | T-21, [summary.txt](../../../artifacts/archify/spec-demos/rendering/other-types/summary.txt) | 16개 실행 확인 |
| R-40 | `render-*.mjs`의 `throwDiagnosticProblems` 호출, T-04 T-16 | rendering R-18과 일치. 타입별 접두어 문구는 위 C-ID |
| R-41 | C-14 `render-erd.mjs:552-590`·`render-class.mjs:455-470`, `architecture/routing.mjs:40-170,405-440,540-690,1190-1215`(옵션 사용 지점) | 옵션 값은 두 렌더러 호출부, 효과는 `routing.mjs` 사용 지점. 일반 관계선 좌표는 routes.txt. 개선 스윕 단계별 기여는 추적하지 않음 |
| R-42 | C-03 C-04 `dataflow-compiler.mjs:770-915,1359-1382`, C-36, T-26 | 코드를 읽고 `df.r1.show` HTML의 `data-composition-points`를 식(244 = 259−15, 113 = 128−15)과 대조. 라벨 공동 수리가 제안을 채택하는 입력은 못 만들었다 |
| R-43 R-44 | C-37 C-38, T-28~T-30, time-formats.txt | 코드를 읽고 입력을 바꿔 가며 출력 문자열을 정규식으로 추출해 변환표와 대조 |
| R-45 | C-32~C-35 C-39 C-40, T-27 | 마크업 코드와 `markup.txt`(루트 속성·섹션 순서)를 대조. 요소별 클래스·`data-*` 전체는 C-ID가 기준이고 실행으로 전수 대조하지 않음 |
| R-46 | C-41~C-43 | 코드만 읽음(경계값 미관측) |
| R-47 | C-05 `dataflow-compiler.mjs:286-380`, `desktop-readability.mjs:95-131`, `render-dataflow.mjs:17`, `geometry.mjs:1301-1306`, T-31 T-32, u06.txt | 수정안 분기를 입력 3종으로 실행 대조, 프로파일 조합 6+4종 실행 |
| 문서·구현 차이 | (0) rendering-architecture-routing.md R-14의 "`typeOwned`는 항상 빈 집합"은 architecture 한정이고, erd에서는 `preferredCandidates`와 같은 경로를 가진 연결이 스윕에서 제외되어 비어 있지 않다(1.3 J). (1) rendering.md R-42 "타임라인 높이 120px 미만이면 문제"는 `meta.viewBox` 최솟값(스키마 `[480,480]`, `schemas/sequence.schema.json`)이 막아 스키마 통과 입력으로는 도달하지 못한다(`layout/constraint`가 아니라 `schema/minimum`이 먼저 난다, `sq` 실행에서 `/meta/viewBox/1 must be >= 480` 확인). (2) rendering.md 표 H의 sequence 열 간격 "일정 간격"은 spread에서 `gap`이 폭에 따라 정해지는 값, fixed는 108 고정이라는 구분이 필요하다. (3) rendering.md R-43의 간격 증가식은 `spineGap`이 폭 예산 초과 시 고정된다는 조건이 빠져 있다. (4) rendering.md 표 H의 class "일반화 버스"는 멤버 2개 이상·간격 40 이상·비관통·충돌 롤백 조건이 있다. (5) `inspect-sequence-width`는 렌더러가 아니라 `check`/`finalize`의 권고라 rendering.md가 아니라 verification-gates 행의 소유다. | 코드와 실행으로 확인 |

### 2.2 코드 읽는 순서 [선택]
타입별 모듈 최상위(위에서 아래가 실행 순서; dataflow만 `compileDataflow` 안 `build`) → 측정 함수 → 배치 → 라우팅 → 라벨 → `validate*` → `renderSvg` → `writeDiagram`. erd·class는 `createRouter` 호출(`render-erd.mjs:552`, `render-class.mjs:455`) 직전의 옵션 주석을 먼저 읽으면 후보 구성 의도가 보인다. dataflow showcase 후처리는 `automaticShowcase` 조건 블록(761, 941, 1159, 1335, 1359행)만 따라가면 된다.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙 없음. 원본 코드를 복사하지 않았다.

## 적용 메모 [선택]
없음. 이 문서는 원본 동작만 기록한다.

## 미결정

없음. 이전 U-01~U-06은 1.4 미결정 줄에 해소 위치를 적었다. 남은 것은 1.4 확인 한계(후처리 일부의 채택 입력 미실행, 스윕 단계별 기여 미추적, 라벨·마커 박스 경계값 미관측, 브랜드 마크 범위 밖)뿐이다. 이 스펙 자체의 미결정이 비어 `status: ready`이고, 선행 [rendering.md](rendering.md)·[rendering-architecture-routing.md](rendering-architecture-routing.md)의 status는 메인이 확인한다.
