---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/renderers/architecture/routing.mjs
  - archify/renderers/architecture/render-architecture.mjs
  - archify/renderers/shared/geometry.mjs
  - archify/renderers/shared/route-quality.mjs
  - archify/renderers/shared/automatic-labels.mjs
  - archify/renderers/shared/spatial-grid.mjs
  - archify/renderers/shared/utils.mjs
depends: [rendering.md]
status: ready            # 2026-11-02: 이 스펙 자체의 미결정 없음, 선행 스펙 ready
---

# architecture 자동 라우팅 (포트 → 후보 경로 → 격자 탐색 → 개선 스윕 → 라벨 위치)

> 측정된 컴포넌트 상자와 `connections[]`를 받아, 연결마다 끝점 변·포트·직교 경로 좌표를 정하고(1차 계획 + 한 번의 개선 스윕), 연결 라벨의 예약·최종 위치까지 원본과 같은 좌표로 내는 규칙이다. 선행 [rendering.md](rendering.md)의 R-28·R-29·R-30·R-33과 미결정 M-01을 풀어 쓴 하위 스펙이다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. `render-architecture.mjs`가 컴포넌트를 측정하고 경계 프레임(`rawBoundaries`, 제목 확장 전)을 만든 뒤 `createRouter(components, arch.connections, routerOptions)`를 한 번 만든다(C-01). 옵션은 항상 같은 값이다(1.3 B).
2. 처음 `pathFor`/`connectionSides`가 불리면 `planRoutes`가 한 번 돈다(R-01). 끝점 컴포넌트가 둘 다 있는 연결만 계획한다. **명시 지오메트리(`via`, `route≠auto`, `channelX/Y`) 연결이 먼저**, 자동 연결은 두 중심의 맨해튼 거리 오름차순(동률은 입력 순)이다(R-02).
3. 연결 하나마다 `computePath`: 변 쌍 후보를 정렬해(R-04) 앞에서부터 `routeVia`로 경로를 만들고(R-08~R-12) 처음 "깨끗한" 것을 고른다(R-03). 끝점 포트는 같은 변에 몰린 연결끼리 미리 퍼뜨려 둔다(R-05, R-06). 고른 경로는 `resolvedRoutes`에 쌓이고, 라벨이 있으면 라벨 직사각형이 예약된다(R-13). 이후 연결은 이 경로·라벨을 장애물로 본다.
4. 후보가 모두 막히면 장애물 격자 최단 경로(굽힘 벌점 48)를 탐색한다. 탐색은 계획 전체에서 64번까지다(R-10, R-11).
5. 전체 계획이 끝나면 **개선 스윕**을 정해진 순서로 딱 한 번씩 돈다: 상호 연결 쌍 → 복잡한 경로 → 마주 보는 직선 → 라벨 때문에 막힌 경로 → 코너 포트 한 번 꺾기 → (자동 viewBox일 때) 아래 여백 24px 안의 교차 해소. 스윕은 격자 탐색을 쓰지 않고, 한 번에 연결 하나만 바꾸며, 수렴할 때까지 반복하지 않는다(R-14~R-21).
6. 결과 `{points, d}`가 `connection` 객체별로 캐시된다. 렌더러는 `points`로 SVG·라벨·viewBox·진단을 만든다(rendering.md R-23, R-31, R-32, R-35).
7. `meta.quality_profile==="showcase"`이면 그 뒤에 라벨만 한 번 더 재배치한다(R-23). 경로·캔버스는 바뀌지 않는다.

### 1.2 범위·통합 지점 [필수]
- 제공: architecture의 자동 라우팅 전부: 변 추론, 포트 퍼뜨림·정렬, 후보 생성 순서, 격자 최단 경로, 개선 스윕, 라벨 직사각형 예약, 라벨 최종 위치, 품질 프로파일 의존성.
- 제외: 명시 `via/route`의 해석(rendering.md R-27), 경로를 그리는 SVG 마크업(R-31), 레이아웃 진단 문장과 게이트(R-34, R-35, C-24), 경계 제목 배치(R-24), 컴포넌트 측정·경계 프레임 계산(C-10, C-11). 같은 `createRouter`·`shortestOrthogonalGridRoute`·`placeAutomaticLabels`를 쓰는 erd·class·dataflow·workflow의 호출 옵션과 후처리는 이 스펙이 아니다(2.3). 시각 품질(사람 눈 판단)은 확인하지 않았다.
- 외부 의존·선행 계약: [rendering.md](rendering.md)가 준 "검증을 통과한 diagram"과 측정된 상자 `Map<id, {id,x,y,width,height,cx,cy,…}>`(`cx=x+w/2`, `cy=y+h/2`), 경계 프레임 `{x,y,width,height,kind}`(R-22 공식). 글자 폭 `textUnits`(rendering.md C-26, 이 문서 C-22 뒤). 입력 스키마·진단 객체는 input-validation.md.
- 소유 상태·부작용: 라우터 인스턴스 안의 `pathCache`(연결 객체 → `{points,d}`), `selectedSides`(연결 → 최종 `{fromSide,toSide}`), `reservedLabels`, `planningMetrics`. 인스턴스는 상자나 연결이 바뀌면 새로 만든다. 파일·전역 상태는 건드리지 않는다.

### 1.3 인터페이스와 데이터 의미 [필수]

**A. 라우터**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `createRouter(components, connections, options)` | 상자 Map, 연결 배열(원본 객체 참조 유지), 옵션 → `{ports, pathFor, connectionSides, inferredSides, connectionEndpointSide, routingMetrics}` | 생성 시점에 `automaticPortSpread`를 한 번 계산한다(R-05). 경로는 첫 조회 때 한꺼번에 계획(`planRoutes`)하고 이후는 캐시. |
| `pathFor(conn)` | 연결 객체 → `{d, points}` | `points`는 자동 경로면 정규화(R-26), 명시면 그대로. 끝점이 없는 연결을 직접 부르면 계획에 없으므로 쓰지 않는다(렌더러는 거른다). |
| `connectionSides(conn)` | → `{fromSide, toSide}` | 스윕까지 끝난 최종 변. 계획 전이면 먼저 계획한다. |
| `connectionEndpointSide(conn, 'source'\|'target')` | → 변 | 저자가 `fromSide/toSide`를 `auto` 아닌 값으로 줬으면 그 값, 아니면 최종 변. |
| `inferredSides(conn)` | → 추론 변 | 계획을 일으키지 않는 추론만. |

**B. architecture가 넘기는 옵션(상수)**

| 옵션 | 값 | 효과 |
|---|---|---|
| `distinctAutomaticPorts` | `true` | 포트 점유 기반 재배정(R-06), 같은 끝점 공유 연결끼리도 통로 겹침·교차를 막음(R-12), 평행 채널 후보(R-09 ⑥), 포트 간격 확장 |
| `preferReadableRoutes` | `true` | 팬아웃 변 추론(R-07)과 개선 스윕(R-14) 켬 |
| `readabilityBottomMargin` | `meta.viewBox`가 있으면 0, 없으면 24 | R-21 |
| `frames` | 경계 프레임 `rawBoundaries`에 반지름(`security-group` 8, 그 외 12) | 격자 탐색의 테두리 회피, 경로의 테두리 따라달리기 금지(R-12) |
| `labelRectFor` | 라벨 있는 연결만 `reservedLabelRect(...)`(R-13), 없으면 `null` | 라벨 예약 |
| 그 밖 | 기본값: `interiorSegmentPx 16`, `microSegmentPx 8`, `compositionFloors true`, `componentGapPx 0`(격자 간격 목록 `[0]`), `minimumTerminalSegmentPx 0`, `crossingFreeGridFirst false`, `sideFor null`, `maxPortSpacing null`, `preferredCandidates null`(따라서 `typeOwned`는 항상 빈 집합) | |

**C. 상수·정의 표** (이 표에 없는 숫자는 C-ID 코드 안에 있다)

| 이름 | 값 | 쓰임 |
|---|---|---|
| 끝점 스텁 `outwardStub` | 24px, 변 바깥 방향 | 변 인식 브리지(R-09), 격자 탐색 `endpointStubPx` |
| 최소 브리지/채널 | 16px (`minimumBridge`), 8px (`minimumStub`)×2=16 | R-09 ④⑤ |
| 라벨 여유 `LABEL_CLEARANCE` | 4px | 예약 라벨과 경로 사이 |
| 컴포넌트 통과 여유 | 2px (`routeClearsComponents` 기본) | R-12 |
| 코너 여유 `AUTOMATIC_PORT_CORNER_GUTTER` / `portHasCornerClearance` | 16px(상자 변 길이의 절반이 더 작으면 그 값) | 포트는 변 양 끝 16px 안쪽 |
| 선 굵기 `stroke(rel)` | `rel.width ‖ (variant==="emphasis" ? 1.8 : 1.5)` | 포트 간격 |
| `markerSpacing(l,r)`, `portSpacing(l,r)` | `3.5×(stroke(l)+stroke(r))`, `max(14, markerSpacing+3.5)` | R-05, R-06 |
| 비용 `readabilityCost` | 총 길이(맨해튼) + `(점 수−2)×48` + `교차한 경로 수×160` | R-15 이후 모든 비교 |
| 격자 탐색 인자 | `clearance 2, maximumObstacleCount 80, endpointStubPx 24, maximumGridNodes 4096, minimumAvoidedOverlapPx 8, routeSeparationPx 8, minimumSegmentPx 16, bendPenaltyPx 48`, `borderSegments=프레임 테두리` | R-10 |
| 격자 탐색 횟수 한도 | 계획 전체 64번(`maximumGridSearchCount`) | R-10 |
| 라벨 박스 | 폭 `max(30, textUnits×4.8+10)`, 높이 14, 기본 중심 `labelPoint`, `y = ly−10` | R-13, R-23 |
| 예약 라벨 비교 | 라벨 직사각형끼리 간격 2px 여유(`rectsOverlap(rect, other, 2)`) | 스윕의 `labelClears` |
| 스윕 범위 `bounds` | 계획 직후 모든 경로 점·컴포넌트·프레임·예약 라벨 직사각형의 외곽. 아래 여백 모드에서만 `bottom += 24` | `withinScene` |

**D. helper 색인** (원본 함수 → 이 문서의 C-ID. 표준 라이브러리 제외, 이 밖의 helper는 없다)

| 함수 | C-ID |
|---|---|
| `routeVia`, `computePath`, `candidateSidePairs`, `routeIsClear`, `crossingCount`, `readabilityCost`, `planRoutes`, `pathFor`, `improve*`, `relocatedLabelsFor`, `endpointSlotsClear`, `labelClears` | C-05, C-07~C-10 |
| `routeClears*`, `routeConflictsWithResolved`, `routeOverlapsResolved`, `collinearOverlapLength`, `orthogonalTouchOnResolvedInterior`, `routeMeetsCompositionFloors`, `spacedRouteIsClean`, `gridComponentObstacles`, `reservedLabelObstacles` | C-02, C-03 |
| `outwardStub`, `collinearBacktrack`, `sideAwareBridgeCandidates`, `alignFacingPorts`, `reciprocal`, `siblingCrossings` | C-04 |
| `rowFanOutSides`, `automaticEndpoint`, `connectionGeometry`, `routedForGeometry`, `inferredConnectionSides`, `hasAuthoredRouteGeometry`, `hasAuthoredLabelPlacement` | C-06 |
| `rectsOverlap`, `segmentIntersectsRect`, `segmentRectClearance(Within)`, `isFinitePoint`, 점-선분 거리, 교차 판정 | C-11 |
| `routeHonorsEndpointSides`, `endpointSideIssue`, `ENDPOINT_SIDE_RULES` | C-12 |
| `normalizeRoutePoints`, `collinearForward`, `properSegmentIntersection` | C-13 |
| `collectBorderRuns`, `frameBorderSegments`, `mergeBorderOverlaps`, `collinearAxisOverlap` | C-14 |
| `collectRouteRhythmIssues`, `segmentPosition` | C-15 |
| `anchor`, `portHasCornerClearance`, `alignAutomaticFacingPorts`, `automaticPortRhythmBridge` | C-16 |
| `automaticPortSpread`, `defaultFromSide/ToSide`, `chosenSide` | C-17 |
| `roundedPath`, `labelPoint` | C-18 |
| `shortestOrthogonalGridRoute`와 `MinHeap`, `moveOutward`, `expandedRect`, `pointBlocked`, `segmentBlocked`, `segmentConflictsWithAvoided`, `orthogonalTouchOnAvoidedInterior`, `pointOnAvoidedInterior`, `collinearOverlap`, `orthogonalLength`, `pointKey` | C-19, C-20 |
| `placeAutomaticLabels`, `reservedLabelRect`, `createSpatialGrid` | C-21 |
| `textUnits` | C-22 |

### 1.4 행동 규칙과 남은 질문 [필수]

"변" = `left|right|top|bottom`. "경로" = 점 배열 `[start, …, end]`(좌표 `[x,y]`). 규칙의 세부 분기는 괄호 안 C-ID 코드가 기준이다.

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 첫 `pathFor`/`connectionSides` 호출 | `planRoutes`가 한 번 실행되고(재진입 가드 `routesPlanning`) 이후 호출은 캐시를 돌려준다. 계획 대상은 `from`·`to` 컴포넌트가 모두 있는 연결. 자기 연결(`from===to`)도 대상이다(R-27 사례). | 코드 확인(C-08, C-10) / 실행 확인(T-14) |
| R-02 | 계획 순서 | `[…명시 지오메트리 연결(입력 순), …자동 연결]`. 자동은 `|to.cx−from.cx|+|to.cy−from.cy|` 오름차순, 동률은 입력 인덱스. 명시 = `via` 있음, `route`가 있고 `auto` 아님, `channelX/Y` 정의됨. `labelAt/labelDx/…`는 자동 연결로 계획된다(스윕만 제외). 시작할 때 `reservedLabels=[]`. | 코드 확인(C-08) |
| R-03 | 자동 연결 하나(`computePath`) | `candidateSidePairs`를 순서대로 돌며 각 쌍으로 `connectionGeometry`→`routedForGeometry`(=`routeVia`)를 만들고 `routeIsClear`인 첫 쌍을 고른다. 하나도 없으면 첫 쌍의 결과(폴백)를 쓴다. 먼저 예약 라벨을 장애물로 보고(`honourReservedLabels=true`) 한 번 고르고, 예약 라벨이 있고 결과가 없거나 길면 R-13의 규칙으로 예약을 무시한 결과와 비교한다. 선택은 `pathCache`·`selectedSides`에 기록. 명시 연결은 추론 변으로 `routedForGeometry`를 한 번만 한다(후보 탐색 없음). `routeIsClear` = 포트 `crowded` 아님 ∧ 점 2개 이상 ∧ `routeHonorsEndpointSides` ∧ `routeClearsEndpointComponents` ∧ `routeClearsComponents` ∧ `routeMeetsCompositionFloors` ∧ ¬`routeOverlapsResolved`(교차는 허용). | 코드 확인(C-07, C-03) / 실행 확인(T-12) |
| R-04 | 변 쌍 후보 | 추론 변(`inferredConnectionSides`) 우선. `from` 옵션 = 저자가 `auto` 아닌 값을 줬으면 그 하나, 아니면 `[추론, …['right','bottom','left','top']에서 추론 제외]`, `to`도 같다. 모든 조합을 만들어 (a) 추론에서 벗어난 끝 수(0/1/2) 오름차순, (b) 같으면 두 포트 사이 맨해튼 거리 오름차순(포트는 그 쌍으로 `connectionGeometry`를 호출해 얻음), (c) 같으면 생성 순서(안정 정렬)로 정렬한다. | 코드 확인(C-07) / 실행 확인(T-02: 동률에서 `(right,top)`이 `(bottom,left)`보다 앞) |
| R-05 | 변 추론·퍼뜨림 초기 계산 | 변은 `chosenSide(저자값, 추론)`. 추론 = `sideFor` 없음(null) → 팬아웃 규칙(R-07) → `defaultFromSide/ToSide`(C-17: `dx≠0 ∧ |dx|≥|dy|`이면 좌우, 아니면 `dy>0`이면 from=bottom/to=top, 아니면 from=top/to=bottom; 두 중심이 같으면 from=top, to=bottom). 퍼뜨림 대상 = `via`·`channelX/Y`·`labelAt` 없고 `route`가 없거나 `auto`인 연결. `(컴포넌트 id, 변)` 그룹마다 끝점(from/to 양쪽)이 2개 이상이면 상대 쪽 중심(변이 좌우면 `cy`, 상하면 `cx`) 오름차순, 동률은 `id\0from\0to\0label` 사전순으로 정렬하고, 변 중앙 기준 `(i−(n−1)/2)×spacing`만큼 변을 따라 이동. `spacing = min(14, (변 길이−32)/(n−1))`(`≤0`이면 그 그룹은 퍼뜨리지 않음). 인접 쌍 간격 `max(14, portSpacing(i,i+1))`의 합이 `변 길이−32` 이하이고 14 초과 간격이 하나라도 있으면 중심 대칭으로 그 간격 누적 배치(`spacingFor`, `markerSpacing>14`일 때만 `portSpacing`, 아니면 14). | 코드 확인(C-17, C-06) / 실행 확인(T-05, T-10, T-11) |
| R-06 | 끝점 포트 결정 `connectionGeometry`(`distinctAutomaticPorts`) | 변이 추론 변과 같으면 R-05의 퍼뜨린 포트가 우선 후보, 아니면 변 중앙 `anchor`. `via/route/channel/labelAt`이 있는 연결이면 그대로. 아니면 같은 컴포넌트·같은 변에 이미 놓인 다른 자동 연결 끝점(이미 경로가 있으면 그 점, 없으면 퍼뜨린 점 또는 중앙)을 점유로 보고, 후보 `[선호값, …점유값±portSpacing]`을 `|선호와의 거리|`, 그다음 `|상대 컴포넌트 중심(추론 변이 아닌 변이면) 또는 선호값 쪽과의 거리|`, 그다음 값 오름차순으로 정렬해 코너 여유를 만족하고 모든 점유와 `portSpacing` 이상 떨어진 첫 값을 쓴다. 없으면 선호 포트를 쓰되 `crowded=true`(그 쌍은 `routeIsClear` 불가). 마지막으로 `alignAutomaticFacingPorts`(R-09 앞)를 통과시킨다. | 코드 확인(C-06, C-16) |
| R-07 | 팬아웃 변(`rowFanOutSides`, `preferReadableRoutes`) | 연결의 한쪽 컴포넌트 `node`와 상대 `other`에 대해(from 쪽 먼저, 안 되면 to 쪽): `other`가 `node`의 위/아래에 완전히 떨어져 있고, `node`→`other`의 기본 변이 위/아래 변이 아니며, (a) `other`와 같은 줄(중심 y 차 <1)에 있는 다른 이웃 중 기본 변이 위/아래 변(아래이면 `bottom`, 위이면 `top`)인 것이 있고, (b) `other`와 같은 줄이면서 기본 변이 `other`와 같은 이웃(자기 포함) 중 하나라도 `node`와의 가로 틈에 다른 상자가 걸려 있으면, `node` 쪽 끝이 그 수직 변(상대 쪽은 반대 변)을 쓴다. 아니면 `null`(기본 추론). 이웃 목록은 연결의 양쪽 컴포넌트 모두에 대해 만든다. | 코드 확인(C-06) |
| R-08 | `routeVia`(자동) 입력 | `conn.via`가 있으면 그것, `route`가 `straight/orthogonal-h/orthogonal-v`면 rendering.md R-27의 점, 아니면 R-09의 자동. "수락" = R-12의 조건. 후보 `candidate`는 중간 점만이고 실제 경로는 `[start,…candidate,end]`. | 코드 확인(C-05) |
| R-09 | 자동 후보 생성 순서(`routeVia`) | 첫 수락 후보를 즉시 돌려준다. ① `preferredCandidates`(architecture는 없음). ② `|Δx|<4 ∨ |Δy|<4`이면 직선 `[]`(변 방향·끝점·컴포넌트·바닥·교차 모두 통과해야). ③ `automaticPortRhythmBridge`의 첫 후보(C-16, `accept`는 끝점·컴포넌트·바닥·교차 없음). ④ 두 포트가 상하(좌우)로 나란한 변이고 `|Δx|<16`(`|Δy|<16`)이면 바깥 채널 `[[채널x,sy],[채널x,ey]]`, 채널 = `max(sx,ex)+16`, `min−16` 순(좌우 쪽은 y 대칭). ⑤ `horizontalFirst=[[midX,sy],[midX,ey]]`, `verticalFirst=[[sx,midY],[ex,midY]]` 중 끝 변 방향을 지키는 것(`sideSafe`)과 `sideAwareBridgeCandidates`(C-04, 길이 짧은 순)를 `nearParallelPorts`(양쪽 상하이고 `|Δx|<16`, 또는 좌우이고 `|Δy|<16`)이면 `sideAware→sideSafe`, 아니면 `sideSafe→sideAware` 순으로 이어 붙여 각각 끝점·컴포넌트·바닥·교차 없음·(`distinctAutomaticPorts`)통로 겹침 없음·형제 교차 없음을 검사한다. 통과한 첫 후보가 라벨이 없거나 `labelRectFor`가 직사각형을 주면 확정, 아니면 `firstFeasible`로만 기억하고 계속 본다. 끝까지 확정이 없으면 `firstFeasible`을 쓴다. ⑥ `distinctAutomaticPorts`이면 중점에서 16px씩 벌린 평행 채널(x는 `mid±16k`, 허용 구간 `[min+24, max−24]`, 후보는 `+`쪽부터 번갈아, x 채널 후 y 채널)로 수직·수평 두 꺾임을 시도(통로 겹침·형제 교차 없음 포함). ⑦ 격자 탐색(R-10). ⑧ 폴백(R-11). 수락 검사 목록은 단계마다 조금 다르다(②③④는 통로 겹침 검사가 없고 ④는 끝점 컴포넌트 검사도 없다. C-05가 기준). | 코드 확인(C-05) / 실행 확인(T-01~T-06) |
| R-10 | 격자 탐색 호출 | 스윕 중(`allowGridSearch=false`)에는 하지 않고 폴백 후보(R-11 식)를 바로 돌려준다. 계획 중 `gridSearchCount≥64`이면 두 카운터(`gridBudgetExhaustedCount`, `conflictFallbackCount`)를 올리고 같은 폴백 후보. 아니면 갭 목록 `[0]`에 대해 한 번씩 `shortestOrthogonalGridRoute`를 호출(`gridSearchCount+1`). 장애물 = 모든 컴포넌트(끝점 포함) + 예약 라벨(2px 여유가 되도록 키움, 예약 무시 모드면 없음). `avoidedSegments` = `distinctAutomaticPorts`이고 끝점을 공유하며 둘 다 `via/route/channel/labelAt` 없는 해결 경로의 구간. `allowAvoidedCrossings=true`, `borderSegments=프레임 테두리`. 결과가 (끝점 컴포넌트 비관통 ∧ 컴포넌트 여유 ∧ 통로 비겹침 ∧ 리듬·테두리 바닥)이면 채택(교차는 허용, `crossoverRoutedCount`만 증가), 그렇지 않으면 ⑧. 채택 점은 `points.slice(1,-1)`. `crossingFreeGridFirst`는 꺼져 있어 쓰이지 않는다. | 코드 확인(C-05, C-19~C-20) / 실행 확인(T-06) |
| R-11 | 폴백 ⑧ | `conflictFallbackCount+1` 후 `sideSafe[0] ?? sideAware[0] ?? horizontalFirst`를 돌려준다(검증이 이후 진단으로 보고). 자기 연결도 이 경로로 떨어진다. | 코드 확인(C-05) / 실행 확인(T-14) |
| R-12 | 수락 술어 | `routeHonorsEndpointSides`: 정규화한 첫(마지막) 구간이 `from`(`to`) 변에서 바깥(안)쪽 축 방향으로만 나가야(수직 성분 0, 부호 일치). `routeClearsEndpointComponents`: 첫 구간 제외 구간은 `from` 상자와, 마지막 구간 제외 구간은 `to` 상자와 닿지 않음(여유 0). `routeClearsComponents(conn, points, 2)`: 끝점이 아닌 모든 컴포넌트와 2px 여유로 안 닿고, (`honourReservedLabels`이면) 다른 연결의 예약 라벨과 4px 여유로 안 닿음. `routeMeetsCompositionFloors`: (`minimumTerminalSegmentPx=0`이라 끝 구간 규칙 없음) `collectRouteRhythmIssues`(구간 길이 `<8`이면 micro, 안쪽 구간 `<16`이면 short-interior; 끝 구간은 8만) 없음 ∧ 프레임이 있으면 `collectBorderRuns` 없음(프레임 테두리와 같은 선 위로 달리지 않음). `routeConflictsWithResolved`: 끝점을 공유하지 않는 해결 경로와 진짜 교차 ∨ 직교 접촉(해결 경로의 안쪽 점에 닿음) ∨ 8px 이상 같은 선 겹침. `routeOverlapsResolved`: 8px 이상 같은 선 겹침(끝점 공유 경로는 `distinctAutomaticPorts`이고 둘 다 `via/route/channel/labelAt` 없을 때만 포함). `siblingCrossings`: 쌍방(reciprocal)이 아닌 경로만 대상 `crossingCount`. `crossingCount`: 경로 수 단위(진짜 교차 한 번이라도 있으면 1). | 코드 확인(C-03, C-11~C-15) |
| R-13 | 라벨 예약 | 연결에 `label`이 있으면 경로가 정해질 때마다 `reservedLabelRect`: 라벨 박스(기본 위치 `labelPoint`)를 `placeAutomaticLabels`에 `fallbackRing=false`·`viewBox=[∞,∞]`로 넣어(자기 라벨 `relationIndex −1`, 이미 예약된 라벨 `−2`, 경로는 자기 경로 `−1` + 이미 해결된 경로들) 첫 라벨의 결과 직사각형을 얻고, 그것이 컴포넌트와 `−2`(2px 넘게) 겹치면 `null`, 아니면 그 직사각형(경로·라벨과 겹쳐도 유지됨)을 `reservedLabels`에 저장한다. 따라서 "라벨 위치를 통과하는 후보"(R-09 ⑤)는 사실상 "라벨이 컴포넌트와 2px 넘게 겹치지 않는 후보"다. 예약 라벨은 이후 연결의 경로 장애물(4px)이고 격자 장애물이다. 예약이 있고 첫 선택(`honourReservedLabels=true`)이 실패하면 예약 무시로 다시 고르고, 성공했어도 길이가 `직접거리×1.25+64`를 넘으면 예약 무시 결과 `plain`을 만들어 `길이(plain)×1.25+64 < 길이(chosen)`일 때만 plain으로 교체한다(직접거리 = 선택된 경로 양끝 맨해튼). | 코드 확인(C-01, C-07, C-21) |
| R-14 | 개선 스윕 개요 (`preferReadableRoutes`) | 1차 계획 직후 한 번, 다음 순서로 각 단계가 `resolvedRoutes`를 계획 순서로 한 바퀴씩 돈다(R-02 순서, 앞서 바뀐 경로·변·라벨을 뒤 연결이 본다). 스윕 동안 `allowGridSearch=false`. ① `improveReciprocalPairs` ② `improveComplexRoutes(false)` ③ 마주 보는 직선(R-18) ④ 라벨 재배치(R-19) ⑤ 코너 포트 꺾기(R-20) ⑥ `readabilityBottomMargin>0`이면 `bounds.bottom += 24` 후 `improveComplexRoutes(true)`. 각 단계는 한 번만 실행되고 수렴 반복이 없다(종료 = 마지막 단계 끝). 새 경로가 `withinScene`(모든 점이 `bounds` 안, 경계 포함)이어야 한다. 한 번에 연결 하나만 바꾼다. 스윕이 건드리지 않는 연결: 명시 지오메트리, `labelAt/labelDx/labelDy/labelSegment` 중 하나라도 있는 연결, `typeOwned`(항상 빈 집합), ①에서 이미 바뀐 쌍(`jointlyImproved`). | 코드 확인(C-08~C-10) / 실행 확인(T-02, T-03, T-13) |
| R-15 | 비교 비용 | `readabilityCost = 맨해튼 길이 + max(0, 점 수−2)×48 + crossingCount×160`. 새 후보는 비용이 **엄격히 작을** 때만 채택, 같은 비용이면 먼저 나온 후보를 유지한다(후보 순서 = R-04 변 쌍 순서, 각 쌍의 슬롯 순서). `crossingCount`는 경로 단위이고 끝점 공유 경로는 `distinctAutomaticPorts`이고 양쪽 다 `via/route/channel/labelAt`이 없을 때만 센다. | 코드 확인(C-07) |
| R-16 | ① `improveReciprocalPairs` | 서로 반대 방향 연결 쌍(`from/to` 뒤바뀜, 둘 다 자동·비고정 변·라벨 위치 고정 없음)마다 한 번. 추론 변이 정확히 `(right,left)+(left,right)` 또는 `(bottom,top)+(top,bottom)` 형태이고 둘 중 하나라도 꺾인 경로(점 3개 이상)여야 한다. 두 연결의 지오메트리가 `crowded`가 아니면, 각 포트 좌표(`start`, `end`의 해당 축 값, 중복 제거) 조합마다 두 연결을 같은 축 값의 직선 `[start,end]`로 바꾼 후보쌍을 만들어 모두 `withinScene`, 포트 슬롯 간격(`endpointSlotsClear`), 코너 여유, `routeIsClear`(서로를 장애물로), 라벨 `labelClears`(예약 라벨을 두 연결 것만 빼고 유지)를 통과하고 두 비용 합이 현재보다 엄격히 작으면 최소를 채택한다. 채택하면 두 연결은 이후 모든 단계에서 제외. | 코드 확인(C-08) |
| R-17 | ② `improveComplexRoutes(onlyCrossings)` | 연결마다: 교차 수(`crossingsBefore`), 현재 라벨 직사각형, `labelBlocked = 라벨 있음 ∧ 라벨 직사각형 없음`. `!labelBlocked ∧ 교차 0 ∧ (onlyCrossings ∨ 점 수≤4)`이면 건너뛴다. 그 외에는 `candidateSidePairs` 전부(`connectionGeometry`→`routedForGeometry`, 새 지오메트리로 R-09의 격자 없는 후보)에 대해 `withinScene ∧ routeIsClear`이고 (onlyCrossings이면 교차가 줄어야) 비용이 더 낮으며 라벨이 `labelClears`이면 최소 비용 후보를 채택한다(`labelBlocked`이면 기준 비용 ∞). onlyCrossings에서는 추가로 `endpointSlotsClear`와 라벨이 컴포넌트와 −2 겹침 없음. 채택하면 라벨 예약도 새 직사각형으로 교체. | 코드 확인(C-09) / 실행 확인(T-13) |
| R-18 | ③ 마주 보는 직선 | 점 4개 이상, 자동, 라벨 위치 고정 없음, ①에서 제외 안 됨인 연결 중 두 상자가 한 축에서 완전히 떨어져 마주 보면(`from.x+w ≤ to.x`→`right,left`, 그 반대→`left,right`, `from.y+h ≤ to.y`→`bottom,top`, 그 반대→`top,bottom`, 위에서부터 첫 일치) 직선을 시도한다. 마주 보는 두 변의 겹치는 구간 `[max(origin)+16, min(origin+size)−16]`가 비어 있지 않고 저자 변이 있으면 같아야 한다. 차선 값 후보 = `{start축값, end축값, 둘의 중점, 구간 중점}`을 구간으로 clamp한 집합(이 순서). 첫 번째로 `withinScene ∧ endpointSlotsClear ∧ routeIsClear ∧ 교차 수가 늘지 않음 ∧ 라벨 labelClears`인 차선이 점 2개 경로가 된다. 변은 마주 보는 쌍으로 바뀐다. | 코드 확인(C-10) / 실행 확인(T-03) |
| R-19 | ④ 라벨 때문에 막힌 경로 재선택 | `labelRectFor`가 있고 다른 예약 라벨이 있는 경우만. 점이 4개 이하이면서 교차 0이면 건너뜀. 각 변 쌍을 `honourReservedLabels=false`로 `routeIsClear` 확인, 비용이 더 낮고 `withinScene`이며 교차가 늘지 않고 `endpointSlotsClear`이면, 새 경로가 가로지르는 예약 라벨이 **정확히 하나**이고 그 소유 연결이 자동·라벨 고정 없음일 때 그 라벨을 옮겨 두 라벨(소유 라벨 새 위치, 이 연결 라벨)이 모두 `labelClears`이고 컴포넌트와 −2 겹침 없으면 후보로 인정한다. 최소 비용 채택. | 코드 확인(C-09, C-10) |
| R-20 | ⑤ 코너 포트 꺾기 | 점 4개 이상, 자동, 라벨 위치 고정 없음인 연결마다, `candidateSidePairs` 중 한쪽은 좌우, 한쪽은 상하인 쌍만, 그 지오메트리의 두 포트마다 슬롯 `{선호 좌표, 변 시작+inset, 변 끝−inset}`(`inset = min(16, 변 길이/2)`, 코너 여유 통과분만, 중복 제거)을 만들어 모든 슬롯 쌍에 대해 한 번 꺾는 경로 `[start, corner, end]`(`corner = 시작 변이 좌우이면 [end.x,start.y]`, 아니면 `[start.x,end.y]`; 정규화 후 점이 정확히 3개)를 평가한다. `비용 < 현재 최소 ∧ withinScene ∧ endpointSlotsClear ∧ routeIsClear(끝점으로 새 포트 사용) ∧ 교차 수가 늘지 않음 ∧ 라벨 labelClears ∧ 라벨 컴포넌트 −2 겹침 없음`이면 채택 후보. 기준 비용은 현재 경로의 비용. | 코드 확인(C-10) / 실행 확인(T-02, T-08, T-11) |
| R-21 | ⑥ 아래 여백 | `meta.viewBox`가 없을 때(`readabilityBottomMargin=24`)만, ①~⑤ 뒤에 `bounds.bottom += 24` 하고 `improveComplexRoutes(true)`를 돈다. 아직 교차가 있는 연결만 대상이고, 교차가 줄어드는 후보만 채택하므로 장면 아래 24px 안쪽 통로로 우회할 수 있다. `meta.viewBox`가 있으면 단계 자체를 건너뛴다. | 실행 확인(T-13) / 코드 확인(C-10) |
| R-22 | 최종 점 | 자동 경로는 `normalizeRoutePoints`(연속 중복 제거, 직선 위 점 제거, 뒤로 꺾는 점은 유지)를 거친 점 배열, 명시 경로는 정규화하지 않는다. `d = roundedPath(points, 8)`. 스윕이 만든 경로도 같은 규칙의 `{points,d}`이다. | 코드 확인(C-06, C-13, C-18) |
| R-23 | 라벨 최종 위치(`meta.quality_profile==="showcase"`만) | 자동 viewBox 계산 뒤, 기본 위치(`labelPoint`)의 라벨 박스 목록으로 `placeAutomaticLabels({keepFallbackNearRoute:true, gridSweep:false, fallbackRing:true, viewBox, placementBottom})`을 한 번 호출한다. `placementBottom = 범례 있음 ? (viewBox[1]−16)−32−범례 extraHeight : viewBox[1]`. 알고리즘은 C-21 그대로이다(R-24). 결과 좌표는 `resolvedLabelPoints`에 저장돼 라벨 박스·진단·`--layout-json`의 라벨이 쓴다. 캔버스·경로는 안 바뀐다. 그 외 프로파일은 기본 위치 유지. | 코드 확인(C-01, C-21) / 실행 확인(T-15) |
| R-24 | `placeAutomaticLabels` 규칙 | 고정(`labelAt/labelDx/labelDy/labelSegment` 중 하나라도 있음)이 아닌 라벨만 처리한다. 라벨 하나의 `needsPlacement` = viewBox 밖 ∨ 컴포넌트와 −2 겹침 ∨ 제목과 겹침 ∨ 다른 라벨과 겹침(간격 0) ∨ 다른 연결 선분과의 거리 `<4`. 필요하면 `clear`(안쪽·`placementBottom` 위·장애물 2px·라벨 2px·다른 선 4px 이상)를 만족하는 첫 후보로 옮긴다. 후보 순서: (1) 각 자기 선분(순서대로)의 `0.5,0.25,0.75,0.125,0.875` 위치(양끝에서 8px 이상): 가로 선분(길이≥폭+4)이면 `[x,y−10],[x,y+20],[x,y−18],[x,y+28]`, 세로 선분(길이≥높이+16)이면 `[x−폭/2−6,y+3],[x+폭/2+6,y+3],[x−폭/2−14,y+3],[x+폭/2+14,y+3]`. (2) 슬라이딩 후보(장애물 가장자리를 따라). (3) `fallbackRing`이면 현재 점과 자기 선분 중점을 기준으로 14개 링 오프셋, `keepFallbackNearRoute`이면 높이×2 안에서 자기 선분에 가까운 것만. 못 찾으면 원래 위치 유지(진단이 보고). 최대 `labels.length`번의 패스, 패스에서 한 개도 안 움직이면 중단, 움직인 뒤에는 아직 `needsPlacement`인 것만 재시도. | 코드 확인(C-21) / 실행 확인(T-15) |
| R-25 | 격자 최단 경로 | C-19~C-20 그대로. 요점만: 격자 좌표 = 끝 스텁·점·(장애물을 2px 키운 직사각형의 `x−1`, `x+w+1`, `y−1`, `y+h+1`)·피해야 할 선분 끝점(세로/가로선분이면 `±8` 포함)·프레임 테두리 `±8`. 좌표를 오름차순 정렬하고, 1차 시도는 첫 값·끝 스텁 좌표·직전 *정렬된* 값과 `minimumSegmentPx`(16) 이상 떨어진 값만 남긴다. 격자점은 장애물 안·(교차 비허용일 때) 피할 선분 안쪽 점이 아니면 노드. 두 노드 사이 직선이 장애물에 막히거나 피할 선분과 8px 이상 겹치거나 프레임 테두리와 겹치면 간선 없음. 상태 = (노드, 들어온 방향), 같은 방향이면 길이만, 방향이 바뀌면 `+48`, 되돌아가기 금지, 도착 노드에서 끝 방향이 `toSide`와 다르면 `+48`. 1차에 경로가 없으면(호출자가 거절해도 같다. architecture는 `accept`를 주지 않는다) 프레임 테두리 `±16` 좌표를 더하고 `fillGaps` 방식(직전 *유지된* 값과 16 이상 + 끝 스텁 좌표와 16 이상 떨어진 값만 남김)으로 한 번 더 시도한다(총 노드 예산 4096 공유, 노드 수가 남은 예산을 넘으면 즉시 실패). 동률은 노드 삽입 순서와 `MinHeap` 구현으로만 정해지므로 코드를 그대로 옮겨야 한다. 결과는 `[start, …격자점, end]`를 정규화한 것. | 코드 확인(C-19~C-20) / 실행 확인(T-06) |
| R-26 | 품질 프로파일·viewBox 의존성 | 경로 좌표를 바꾸는 것은 ① `meta.viewBox` 유무(R-21) ② 경계 프레임 모양(프레임 위쪽 여백이 `meta.quality_profile`이 있으면 `max(pad,22,24)`, 없으면 `max(pad,22)`라 격자 탐색의 테두리 회피 좌표만 달라질 수 있음)뿐이다. `--quality`/`ARCHIFY_QUALITY_PROFILE`와 `meta.quality_profile` 값(`standard` vs `showcase`)은 라우터에 전달되지 않는다. 라벨은 `showcase`만 R-23이 움직인다. | 코드 확인(C-01) / 실행 확인(T-16) |
| R-27 | 자기 연결·끝점 없는 연결 | 끝점이 없는 연결은 계획에서 빠진다(점 없음, 라벨 없음). `from===to`는 추론 변이 `(top, bottom)`이다. 경로의 첫·끝 구간이 자기 상자에 닿으므로 `routeClearsEndpointComponents`가 어떤 후보·격자 결과에서도 실패해 폴백 `sideAware[0]`(바깥 채널 `max(sx,ex)+16`)이 쓰이고, 스윕도 바꾸지 못한다(`routeIsClear` 실패). | 실행 확인(T-14) / 코드 확인(C-05, C-17) |
| R-28 | 결정성 | 라우팅·라벨·스윕에 난수·시계가 없다. 같은 입력이면 같은 점을 낸다. 동률 해소는 모두 입력 순, 변 순서 `['right','bottom','left','top']`, Map 삽입 순서, 안정 정렬, `MinHeap` 구조로 결정된다. | 추론(시간·난수 호출을 이 범위에서 전수 grep으로 확인한 것은 아님) / 실행 확인(같은 입력 반복 실행에서 동일) |

- 불변식: (1) 자동 경로의 모든 구간은 수평 또는 수직이다(격자·후보 모두 직교). 폴백 후보(`sideSafe/sideAware/horizontalFirst`)도 직교다. (2) 자동 경로의 첫(마지막) 구간은 `routeIsClear`를 통과한 경우 끝점 변에서 바깥(안)쪽 직각이다. 폴백은 이를 보장하지 않는다(진단이 보고). (3) 스윕이 채택한 경로는 `withinScene`이며 끝점을 공유하지 않는 이미 해결된 경로와 한 연결씩 비교해 교차 수가 늘지 않는다(①은 비용 합만 비교).
- 미결정: **없음**. 이 문서가 다루는 원본 경로(`routing.mjs` 전체, `geometry.mjs`·`route-quality.mjs`·`automatic-labels.mjs`의 라우팅 관련 함수, 렌더러 호출부)는 모두 읽었다. 선행 [rendering.md](rendering.md)가 `draft`(M-02~M-06)라 이 스펙의 `status`는 `draft`이다.
- 확인 한계: (1) 격자 탐색 예산(장애물 80, 노드 4096, 64회)이 소진되는 입력, 프레임 테두리 따라달리기 금지가 경로를 바꾸는 입력, 라벨 예약이 1차 경로를 바꾸는 입력, ④ 라벨 재배치가 채택되는 입력은 직접 만들지 못해 코드로만 확인했다. (2) 설치본(`~/.claude/skills/archify`, `routing.mjs`가 레포와 바이트 동일)으로 실행했고 레포 clone 안의 코드는 실행하지 않았다. (3) 개선 스윕 이전 상태는 `labelDx:0`(스윕 제외, 포트 퍼뜨림은 유지)을 붙인 `-greedy` 변형으로 관찰했다. 이 변형은 라벨 위치 고정 때문에 `reciprocal` 쌍 보정·`jointlyImproved`가 빠지므로 스윕 효과의 정확한 분리 실험은 아니다. (4) 라우터는 시각 품질(사람 눈)을 보지 않는다.

### 1.5 필수 코드 참조 [필수]
기준은 frontmatter SHA. 라이선스 Apache-2.0(overview 1절). 줄 범위는 이 SHA의 `archify/` 아래 경로.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `renderers/architecture/render-architecture.mjs:99`, `110-140`, `163-172`, `357-376`, `454-475` | 프로파일 플래그, 경계 프레임 `boundaryRect`(위쪽 여백), 라벨 박스 `connectionLabelBoxAt`, 라우터 옵션 `routerOptions`와 `createRouter` 호출, `showcase` 라벨 재배치 호출 | R-01, R-13, R-23, R-26 |
| C-02 | `renderers/architecture/routing.mjs:75-161` | 옵션 기본값, 상태(`reservedLabels`, `honourReservedLabels`, `allowGridSearch`), `planningMetrics`(한도 64) | R-01, R-10 |
| C-03 | `renderers/architecture/routing.mjs:98-138`, `164-305` | 예약 라벨 장애물, 낮은 바닥(`routeMeetsCompositionFloors`), 컴포넌트·해결 경로 충돌·겹침 술어, 격자 갭 | R-03, R-12 |
| C-04 | `renderers/architecture/routing.mjs:307-394` | `outwardStub`, `sideAwareBridgeCandidates`, `alignFacingPorts`, `reciprocal`, `siblingCrossings` | R-09 |
| C-05 | `renderers/architecture/routing.mjs:396-687` `routeVia` | 후보 생성 순서·수락 조건·격자 호출·폴백 | R-08~R-11 |
| C-06 | `renderers/architecture/routing.mjs:689-891` | 이웃 목록·`rowFanOutSides`, 선 굵기·포트 간격, `automaticPorts`, 추론 변, `automaticEndpoint`, `connectionGeometry`, `routedForGeometry`, `cachePath` | R-05~R-07, R-22 |
| C-07 | `renderers/architecture/routing.mjs:893-1007` | `SIDE_ORDER`, `candidateSidePairs`, `routeIsClear`, `crossingCount`, `readabilityCost`, `computePath` | R-03, R-04, R-13, R-15 |
| C-08 | `renderers/architecture/routing.mjs:1009-1192` | `planRoutes` 앞부분(계획 순서·라벨 예약), 스윕 준비(`bounds`, `withinScene`, `endpointSlotsClear`, `labelClears`), `improveReciprocalPairs` | R-02, R-14, R-16 |
| C-09 | `renderers/architecture/routing.mjs:1193-1281` | `followsPreferredCorridor`, `relocatedLabelsFor`, `improveComplexRoutes` | R-17, R-19 |
| C-10 | `renderers/architecture/routing.mjs:1282-1469` | 스윕 단계 순서(R-14), 마주 보는 직선, 라벨 재배치 루프, 코너 포트 꺾기, 아래 여백, 꼬리·반환 | R-14, R-18~R-21 |
| C-11 | `renderers/shared/geometry.mjs:16-18`, `26-99`, `1373-1390`, `1480-1515` | `isFinitePoint`, `rectsOverlap`, `segmentIntersectsRect`, `segmentRectClearance(Within)`, 점-선분 거리, 선분 교차 판정 | R-12, R-24 |
| C-12 | `renderers/shared/geometry.mjs:318-380` | 끝점 변 방향 규칙 | R-12 |
| C-13 | `renderers/shared/geometry.mjs:1327-1371`, `1392-1395`, `1461-1478` | `normalizeRoutePoints`, `collinearForward`, `properSegmentIntersection` | R-12, R-22 |
| C-14 | `renderers/shared/geometry.mjs:918-960`, `1397-1459` | 프레임 테두리 구간, 테두리 따라달리기 검출 | R-12 |
| C-15 | `renderers/shared/geometry.mjs:1070-1104`, `1316-1320` | 구간 길이 하한(micro 8·interior 16) | R-12 |
| C-16 | `renderers/shared/geometry.mjs:1517-1698` | `anchor`, `portHasCornerClearance`, `alignAutomaticFacingPorts`, `automaticPortRhythmBridge` | R-06, R-09 |
| C-17 | `renderers/shared/geometry.mjs:1703-1795`, `1814-1816` | `automaticPortSpread`, `defaultFromSide/ToSide`, `chosenSide` | R-05 |
| C-18 | `renderers/shared/geometry.mjs:1839-1880` | `roundedPath`, `labelPoint` | R-13, R-22 |
| C-19 | `renderers/shared/route-quality.mjs:10-24`, `34-72`, `104-117`, `174-259` | 상수·`MinHeap`·바깥 이동·확장 직사각형·막힘·피할 선분 술어 | R-25 |
| C-20 | `renderers/shared/route-quality.mjs:26-32`, `73-82`, `261-535` | `shortestOrthogonalGridRoute` 본문, `collinearOverlap`, `orthogonalLength`, `pointKey` | R-10, R-25 |
| C-21 | `renderers/shared/automatic-labels.mjs:1-290`, `renderers/shared/spatial-grid.mjs:1-70` | `placeAutomaticLabels`, `reservedLabelRect`, 공간 격자(셀 120, 질의는 상위 집합 반환) | R-13, R-23, R-24 |
| C-22 | `renderers/shared/utils.mjs:203-260` | `textUnits`(전각 2, 변이 선택자 처리) | R-13, R-24 |

### 1.6 수락 사례 [필수]
출처: 모두 실행 관찰이다. 설치본 `archify validate architecture <in> --layout-json`의 `connections[].points`와 `labels`를 기대값으로 둔다. 입력·출력·재실행: [spec-demos/rendering/routing/](../../../artifacts/archify/spec-demos/rendering/routing/)(`python3 -I gen.py && sh run.sh`, 요약 [summary.txt](../../../artifacts/archify/spec-demos/rendering/routing/summary.txt), 프로파일 비교 [summary-profiles.txt](../../../artifacts/archify/spec-demos/rendering/routing/summary-profiles.txt)). 입력은 `in/<이름>.architecture.json`, 컴포넌트는 `pos`만 주면 120×60, `type:backend`, `meta.viewBox` 없음. 좌표는 `x1,y1;x2,y2;…`. "-greedy"는 같은 입력의 모든 연결에 `labelDx:0`을 붙인 변형으로 개선 스윕이 건너뛰므로 1차 계획 결과다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-09 ② | `r01-facing`: `a(40,40)`, `b(240,40)`, 연결 `a→b` | `160,70;240,70` (직선, `|Δy|<4`) |
| T-02 | R-04 R-09 R-14 R-20 | `r02-offset-h`: `a(40,40)`, `b(240,100)`, `a→b` | greedy: `160,70;200,70;200,130;240,130`(수평 먼저 두 꺾임, midX=200). 최종: `160,84;256,84;256,100`. 코너 꺾기가 비용 `112+48=160`으로 `236`(=140+2×48)보다 낮고, `(right,top)`과 `(bottom,left)`가 같은 거리(170)라 앞선 `(right,top)`이 먼저 평가돼 같은 비용 `(bottom,left)`는 채택되지 않는다 |
| T-03 | R-18 | `r03-vertical-dogleg`: `a(40,40)`, `b(60,200)`, `a→b` | greedy: `100,100;100,150;120,150;120,200`(수직 먼저, 수평 먼저 후보는 변 방향 위반). 최종: `100,100;100,200`(마주 보는 직선, 구간 `[76,144]`, 첫 차선 = start x 100) |
| T-04 | R-06 | `r04-vertical-snap`: `a(40,40)`, `b(50,200)` | greedy도 최종도 `100,100;100,200`. 두 x가 10px 차(<16)라 `alignAutomaticFacingPorts`가 끝점 x를 start x로 맞춘다 |
| T-05 | R-05 R-07 R-20 | `r05-fanout`: `h(200,40)`; `x(40,220)`,`y(200,220)`,`z(360,220)`; `h→x`,`h→y`,`h→z` | greedy: `h→x 246,100;246,160;100,160;100,220`, `h→y 260,100;260,220`, `h→z 274,100;274,160;420,160;420,220`(h 아래변 3개 포트 `cx±14`, 상대 `cx` 오름차순). 최종: `h→x 200,84;144,84;144,220`, `h→y` 그대로, `h→z 320,84;376,84;376,220` |
| T-06 | R-10 R-25 | `r06-blocked-grid`: `a(40,100)`, `m(240,100)`, `c(440,100)`, 연결 `a→c`(`m`이 가로 막음) | `160,130;237,130;237,163;416,163;416,130;440,130`. 237=`m.x−2−1`, 163=`m.y+60+2+1`. `184`에서 내려가는 동률 경로(길이·굽힘 같음)가 있지만 원본은 `237`을 고른다 — 재구현이 동률을 다르게 풀면 이 사례가 실패한다 |
| T-07 | R-05 | `r07-reciprocal-aligned`: `a(40,40)`, `b(240,40)`, `a→b`, `b→a` | `a→b 160,63;240,63`, `b→a 240,77;160,77`(그룹 키 `\0a\0b\0` < `\0b\0a\0`이라 `a→b`가 위쪽 포트 −7) |
| T-08 | R-16 R-20 | `r08-reciprocal-offset`: `a(40,40)`, `b(240,70)`, `a→b`, `b→a` | greedy: `a→b 160,63;200,63;200,93;240,93`, `b→a 240,107;184,107;184,77;160,77`. 최종: `a→b 160,56;256,56;256,70`, `b→a 240,114;144,114;144,100`(직선 차선은 포트 코너 여유 때문에 불가, 코너 꺾기로 개선) |
| T-09 | R-04 | `r09-explicit-sides`: `a(40,40)`, `b(240,200)`, `a→b fromSide:bottom, toSide:top` | `100,100;100,150;300,150;300,200`(저자 변 하나만 후보, 스윕이 못 바꿈) |
| T-10 | R-05 | `r17-port-order`: `h(40,120)`; `u(300,20)`, `m(300,130)`, `d(300,240)`; `h→d`,`h→u`,`h→m` | greedy: `h→u 160,136;230,136;230,50;300,50`, `h→m 160,150;300,150`, `h→d 160,164;230,164;230,270;300,270`(오른쪽 포트가 대상 `cy` 오름차순 `−14,0,+14`). 최종: `h→u 144,120;144,64;300,64`, `h→m` 같음, `h→d 144,180;144,256;300,256` |
| T-11 | R-05 | `r15-port-width`: `h(200,40)`; `x(100,220)`, `y(300,220)`; `h→x width:6`, `h→y width:6` | greedy: `h→x 237.25,100;…`, `h→y 282.75,100;…`(간격 `max(14,3.5×12+3.5)=45.5`, 중심 대칭 ±22.75). 최종: `h→x 237.25,100;237.25,236;220,236`, `h→y 282.75,100;282.75,236;300,236` |
| T-12 | R-03 R-12 | `r12-crossing`: `a(40,40)`, `b(240,200)`, `c(240,40)`, `d(40,200)`, `a→b`, `c→d` | greedy `c→d`: `300,100;300,197;184,197;184,230;160,230`(추론 변 `(left,right)`가 아닌 `(bottom,right)` 쌍으로 계획됨. 추론 쌍이 통과하지 못한 이유는 단계별로 추적하지 않았다). 최종 `a→b 160,70;200,70;200,230;240,230`, `c→d 300,100;300,150;100,150;100,200`(교차 하나는 남음) |
| T-13 | R-21 | `r14-bottom-margin`: `a(440,170)`, `b(640,170)`, `c(240,300)`, `d(40,300)`; `a→c`,`b→a`,`b→d`. 같은 입력 `meta.viewBox [800,400]` 변형 `…-fixedvb` | 자동 viewBox: `b→d 700,230;700,384;100,384;100,360`(384 = 장면 아래 360+24, `a→c`와의 교차 회피), viewBox 800×452. 고정 viewBox: `b→d 700,230;700,265;100,265;100,300`(교차 남음), `a→c 440,200;300,200;300,300`는 둘 다 같음 |
| T-14 | R-01 R-11 R-27 | `r16-self-and-unknown`: `a(40,40)`, `b(240,40)`; 연결 `a→a`, `a→zzz`, `a→b` | `a→a 100,40;100,16;116,16;116,124;100,124;100,100`(폴백 `sideAware[0]`, 채널 x=`100+16`), `a→b 160,70;240,70`, `a→zzz`는 점 없음(진단 `architecture/unknown-endpoint`로 종료 1) |
| T-15 | R-23 R-24 | `l02-reciprocal-labels`: `a(40,40)`, `b(280,40)`, `a→b label:"request"`, `b→a label:"response"`. `meta.quality_profile` 없음 / `showcase` | 없음: `response` 박스 `x196 y57`(기본 위치, `labelAt [220,67]`). showcase: `request`는 그대로 `x198 y43`, `response`는 `labelAt [220,97]`, 박스 `x196 y87`(기본 위치가 다른 선과 4px 안이라 후보 `(220,67)` 다음 `(220,97)` 채택). 경로 `a→b 160,63;280,63`, `b→a 280,77;160,77`은 둘 다 같음 |
| T-16 | R-26 | 번들 예제 architecture 5개(`brand-aware-delivery`, `checkout-platform.base/.head`, `production-deployment`, `web-app`)에 `meta.quality_profile`을 없음/`standard`/`showcase`로 바꿔 실행 | 15회 모두 종료 0, 5개 예제에서 `points`·`labels`·`viewBox`가 프로파일 사이에 모두 같음 |
| T-17 | R-24 | `l01-label-gap`: `a(40,40)`, `b(200,40)`(틈 40px), `a→b label:"LONGLABELTEXT"`(폭 72). 없음/`standard`/`showcase` | 경로 `160,70;200,70`, 라벨 `x144 y50`이 어느 프로파일에서도 그대로(후보가 모두 컴포넌트와 겹침). 진단: 없음·`standard`는 `layout/constraint`(라벨-컴포넌트 겹침), `showcase`는 `composition/label-gap` |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
읽은 범위: `routing.mjs` 1~1469 전부, `route-quality.mjs` 1~535(탐색 본문과 helper; 536 이후 `cleanRouteDetourProblems`는 검증 게이트라 rendering.md C-25 소관), `automatic-labels.mjs` 전부, `spatial-grid.mjs` 전부, `geometry.mjs`의 위 C-11~C-18 범위, `render-architecture.mjs` 140~172·355~476, `utils.mjs` 203~260. 문서(rendering.md)와 구현의 차이는 아래 표 끝과 "문서·구현 차이"에 둔다.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-08 `planRoutes` 1011-1016,1454-1455, C-10 `pathFor` 1457-1461 | 코드 읽음. 자기 연결은 T-14 |
| R-02 | C-08 1014-1029 | 코드 읽음 |
| R-03 | C-07 `computePath` 959-1007, `routeIsClear` 922-929 | 코드 읽음, T-12 |
| R-04 | C-07 `candidateSidePairs` 893-920 | 코드 읽음. 동률 `(right,top)` 우선은 T-02 관찰과 안정 정렬로 일치 확인 |
| R-05 | C-17 `automaticPortSpread` 1703-1775, `defaultFromSide/ToSide` 1783-1795, C-06 745-752 | 코드 읽음, T-05 T-07 T-10 T-11 |
| R-06 | C-06 `automaticEndpoint` 807-841, `connectionGeometry` 843-867, C-16 `alignAutomaticFacingPorts` 1543-1601 | 코드 읽음, T-04 |
| R-07 | C-06 `rowFanOutSides` 701-729 | 코드 읽음. 이 분기가 결과를 바꾸는 입력은 만들지 못함(T-05의 greedy는 R-07 없이도 같은 값) |
| R-08~R-09 | C-05 396-550 | 코드 읽음, T-01~T-06 |
| R-10~R-11 | C-05 552-687, C-02 151, C-19~C-20 | 코드 읽음, T-06 T-14. 예산 소진은 미실행 |
| R-12 | C-03, C-11~C-15 | 코드 읽음. `routeClearsEndpointComponents`는 여유 0, 나머지 2/4 |
| R-13 | C-01 357-376, C-21 277-290, C-07 990-1004 | 코드 읽음. 예약이 경로를 바꾸는 입력은 못 만듦 |
| R-14 | C-08 1043-1055, C-10 1282-1448 | 코드 읽음, T-02 T-03 T-13 |
| R-15 | C-07 950-957 | 코드 읽음, T-02 계산 |
| R-16 | C-08 1088-1192 | 코드 읽음. 채택되는 입력은 미관찰(T-08은 후보가 거절돼 다른 단계가 개선) |
| R-17 | C-09 1235-1281 | 코드 읽음, T-13 |
| R-18 | C-10 1290-1337 | 코드 읽음, T-03 |
| R-19 | C-09 1212-1234, C-10 1341-1380 | 코드 읽음. 미관찰 |
| R-20 | C-10 1386-1438 | 코드 읽음, T-02 T-05 T-08 T-10 T-11 |
| R-21 | C-10 1442-1445, C-01 363 | 코드 읽음, T-13 |
| R-22 | C-06 869-885, C-13, C-18 | 코드 읽음 |
| R-23~R-24 | C-01 454-475, C-21 | 코드 읽음, T-15 T-17 |
| R-25 | C-19~C-20 | 코드 읽음, T-06(좌표 237·163) |
| R-26 | C-01 99, 357-376, 457; `render-architecture.mjs:99` | 코드 읽음, T-16 |
| R-27 | C-05, C-17 | 코드 읽음, T-14 |
| R-28 | 범위 내 `Math.random`·`Date` 없음(코드 읽음) | 추론 |
| T-01~T-17 | [gen.py](../../../artifacts/archify/spec-demos/rendering/routing/gen.py), [run.sh](../../../artifacts/archify/spec-demos/rendering/routing/run.sh), [profile-compare.py](../../../artifacts/archify/spec-demos/rendering/routing/profile-compare.py) | 설치본 실행. 좌표는 관찰값 |

**문서·구현 차이**(구현을 사실로 썼다): rendering.md R-28은 "한 노드 아래 한 줄로 늘어선 이웃은 같은 수직 변으로 팬아웃"이라 했으나 실제는 형제가 같은 쪽 기본 변을 쓰고 가로 통로가 막힐 때만이다(R-07). R-30은 "라벨 예약이 우회를 직선×1.25+64보다 길게 만들면 예약을 무시한 라우트를 택한다"인데 실제는 예약 무시 결과 길이에 ×1.25+64를 곱해도 선택 길이보다 짧을 때만 교체한다(R-13). R-29 ⑤의 "라벨 위치도 통과하는 후보 우선"은 실제로는 라벨 직사각형이 컴포넌트와 겹치지 않는 후보 우선이다(R-13). R-30의 "개선 스윕"은 한 단계가 아니라 여섯 단계이며 모두 한 번씩이다(R-14).

### 2.2 코드 읽는 순서 [선택]
`render-architecture.mjs` 357-376(옵션) → `routing.mjs` `planRoutes`(1011) → `computePath`(959) → `candidateSidePairs`(894) → `connectionGeometry`(843)·`automaticPortSpread` → `routeVia`(396) → `shortestOrthogonalGridRoute` → 스윕(1043-1448) → `automatic-labels.mjs`. 원본 전략: 경로는 생성 시 한 번 계획해 캐시, 점 수가 많거나 교차·라벨 막힘이 있는 연결만 비교(예산을 거기에 쓴다는 주석), 격자 탐색은 1차 계획에서만.

### 2.3 비교·재사용 출처 [선택]
같은 `createRouter`를 `class`(`render-class.mjs:456`)와 `erd`(`render-erd.mjs:552`)가 다른 옵션으로 호출하고, `shortestOrthogonalGridRoute`는 dataflow·workflow가, `placeAutomaticLabels`는 dataflow·class·erd가 쓴다. 이 스펙의 C-02~C-21은 그 타입들의 선 좌표(rendering.md M-03)를 재현하는 데도 필요하지만, 옵션 값(`preferredCandidates`, `sideFor`, `crossingFreeGridFirst`, `componentGapPx`, `compositionFloors`, `minimumTerminalSegmentPx`, `maxPortSpacing`)과 후처리는 해당 타입 스펙에서 따로 정해야 한다(여기서는 읽지 않음). 원본 코드를 복사하지 않았다.

## 미결정

이 스펙 자체의 미결정은 없다. `status: draft`인 이유는 선행 [rendering.md](rendering.md)가 `draft`(M-02~M-06 미해결)이기 때문이다(워크플로 4장 4번). 확인 한계는 1.4에 적었다.
