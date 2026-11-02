---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - scripts/generate-viewer.mjs
  - viewer/template.source.html
  - viewer/README.md
  - viewer/focus.js
  - viewer/route-probe.js
  - viewer/semantic-lens.js
  - viewer/node-finder.js
  - viewer/intent-trace.js
  - viewer/motion-governor.js
  - viewer/viewer-camera.js
  - viewer/export.js
  - viewer/export-cleanup.js
  - viewer/reader-layout.js
  - viewer/node-outline.js
  - viewer/tree-branches.js
  - viewer/semantic-radar.js
  - viewer/guided-views.js
  - archify/references/viewer-runtime.md
  - archify/assets/template.html
  - archify/renderers/shared/utils.mjs
  - archify/renderers/shared/cli.mjs
  - test/repository-language-metadata.test.mjs
depends: [rendering.md]
status: ready            # 2026-11-02: 이 스펙 자체의 미결정 없음, 선행 스펙 ready
---

# 결과 뷰어 (HTML 안에서 도는 뷰어 런타임)

> 렌더러가 만든 HTML을 브라우저에서 열면, 이미 들어 있는 스크립트가 URL(쿼리·해시)과 키보드·포인터 입력을 받아 포커스·Reach·Route·Lens·검색·모션·발표 상태를 바꾸고, 현재 다이어그램을 이미지·SVG·WebM으로 내보낸다.

draft인 이유: 선행 스펙 `rendering.md`(렌더러가 SVG, `data-*` 속성, 슬롯을 채우는 쪽)의 status가 아직 `ready`가 아니었기 때문이다. 이 스펙의 미결정은 비어 있고, 1.3의 "렌더러가 뷰어에 약속하는 DOM 속성" 표는 [rendering-contracts.md](rendering-contracts.md) 1.3 A(쓰는 쪽·읽는 쪽 전수 표)와 대조해 맞췄다. 타입별로 어느 렌더러가 어떤 값을 쓰는지는 그 표가 상세 출처다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 개발자가 뷰어 조각(JS 14개, CSS 1개)과 셸 `template.source.html`을 고치고 `generate-viewer`를 돌리면, 마커 15개가 한 번씩 치환되어 단일 파일 `template.html`(787,334바이트)이 만들어진다(R-01). 렌더러는 이 파일의 슬롯만 채운다(R-02, 채우는 규칙은 rendering 소관).
2. 사용자가 완성된 HTML을 연다. `<head>`의 인라인 스크립트가 첫 그림 전에 `?theme=`·`?embed=1`·`?present=1`을 읽어 `<html>`의 `data-theme`·`data-embed`·`data-present`를 정한다(R-03).
3. 본문 끝의 스크립트가 `Archify.*` 모듈을 고정 순서로 한 번씩 초기화한다: preset → theme → exportMenu → motionGovernor → sourceEvidence → treeBranches → focus → intentTrace → readerLayout → viewerChromeLayout → view(camera) → radar → presentation → finder → outline → routeProbe → semanticLens → guide → 전역 keydown(R-06). 초기화 때 `focus`·`route`·`lens`가 URL 해시를 읽어 상태를 복원한다(R-04).
4. 입력(클릭·키·해시 변경)이 모듈 상태를 바꾸고, 바뀐 상태는 `<html>`/`<svg>`의 `data-*` 속성과 패널로 보인다(1.4). 상태 변경은 `history.replaceState`로 해시에 쓰이므로 히스토리 항목은 늘지 않는다(R-04).
5. 내보내기 메뉴(`E`)는 현재 SVG를 복제해 뷰어 상태를 지운 뒤 PNG/JPEG/WebP/SVG 3종/WebM으로 다운로드한다. Route·Reach가 활성이면 1200×630 Share Card도 낼 수 있다(R-20~R-25). 내보내기는 라이브 선택 상태를 바꾸지 않는다(R-25).

### 1.2 범위·통합 지점 [필수]
- 제공: 포커스(Passport)·상류/하류 Reach·두 노드 사이 Route·Semantic Lens·노드 검색(Finder)·Diagram Guide·줌/읽기 깊이·Live/Still 모션·발표 모드·내보내기·딥 링크(해시)·읽기 레일(노드 목록)·트리 접기.
- 제외:
  - 렌더러가 템플릿 슬롯과 `{{i18n:…}}`, SVG와 `data-*` 속성을 채우는 일(`rendering.md`). 여기서는 채워진 뒤의 HTML에서 도는 런타임만 다룬다.
  - `guided-views.js`의 "가이드 뷰"(`#view=` 해시, `?play=1`). 이 파일은 조립 대상이 아니며 기준 SHA의 `template.html`에 그 마크업·코드가 없다(R-29). 사용자에게 보이는 "가이드"는 `?`로 여는 Diagram Guide(R-08)다.
  - `compare architecture`가 만드는 delta HTML(별도 페이지 구조, 보조 명령 스펙 소관).
  - 호스팅·저장 서비스·모바일 제품 표면(`viewer-runtime.md`가 추가하지 말라고 명시).
- 외부 의존·선행 계약: 브라우저(DOM, `history.replaceState`, `localStorage`, Clipboard, `MediaRecorder`+`canvas.captureStream`). 렌더러가 약속하는 DOM 속성(1.3 표). 네트워크는 쓰지 않는다. 폰트는 템플릿에 임베드되어 있다.
- 소유 상태·부작용: 페이지 수명의 메모리 상태(`Archify.*` 클로저), `<html>`·`<svg>`의 `data-*` 속성, URL의 해시와 `present` 쿼리, `localStorage` 키 4개(R-28), 다운로드 파일과 클립보드. HTML 파일 자체는 바꾸지 않는다.

### 1.3 인터페이스와 데이터 의미 [필수]

**URL 입력**

| 이름 | 형식 | 의미·제약 |
|---|---|---|
| `?theme=` | `light` \| `dark` | 첫 그림 전에 테마 지정. 그 밖의 값은 무시하고 `localStorage['archify-theme']`, 그것도 없으면 `prefers-color-scheme`. 어느 쪽도 light가 아니면 dark |
| `?embed=1` | `1` | `<html data-embed="true">`. Finder·Guide·Route 시작은 열리지 않고 `#relation=`은 적용하지 않는다 |
| `?present=1` | `1` | `<html data-present="true">`로 시작(발표 모드). 진입/종료 때 이 쿼리를 `replaceState`로 갱신 |
| `?openExport=1` | `1` | 로드 후 폰트와 프레임 2개를 기다려 내보내기 메뉴를 자동으로 연다(데모·캡처용). 폰트 API가 없으면 200ms 대기 |
| `#focus=<id>` | 노드 id(URL 인코딩) | 그 노드에 포커스(Passport) |
| `#focus=<id>&reach=upstream\|downstream` | | 포커스 + 해당 방향 Reach. `reach`가 그 두 값이 아니면 포커스만 |
| `#relation=<relationship-id>` | 관계 id | 컴파일된 관계 하나를 고정(pin) |
| `#route=<from>~<to>` | 노드 id 두 개를 `~`로 연결(각각 인코딩) | Route를 계산해 결과 상태로 연다. `~`로 나눈 조각이 2개가 아니거나 id가 없으면 무시. 도달 불가면 결과 상태가 되지 않는다 |
| `#lens=<kind>[~<kind>]` | 노드 종류 id | 없는 종류를 걸러내고 중복 제거 후 앞 2개만 사용. 유효한 것이 0개면 무시 |
| 해시 없음/해석 불가 | | `focus`·`route`·`lens` 모듈은 활성 상태가 있으면 해제한다 |
| 해시 쓰기 | | 포커스 `#focus=…`(+`&reach=…`), 관계 `#relation=…`, 경로 `#route=…`, 렌즈 `#lens=…`. 해제하면 해시를 비운다. 모두 `replaceState` |
| 복사 링크 | `location.href`(해시 제외) + `#` + 상태 문자열(`focus=…[&reach=…]`, `relation=…`, `route=a~b`, `lens=a~b`) | `<html data-reading-link-template="…{state}…">`가 있으면 `{state}`가 정확히 한 번 있는 http/https/file 절대 URL(≤4096자, 인증정보 없음)에서 `{state}`를 `encodeURIComponent(상태 문자열)`로 치환한다. 템플릿이 있으나 부적합하면 복사는 실패하고 클립보드를 건드리지 않는다. 속성이 없으면 독립 링크 |

**렌더러가 뷰어에 약속하는 DOM 속성** (뷰어가 읽는다. 채우는 쪽은 rendering)

| 요소 | 속성 | 뷰어가 쓰는 곳 |
|---|---|---|
| `.diagram-container` 직계 `<svg>` | `data-animation="trace"` | Live/Still 가능 여부와 WebM 녹화 가능 여부. 렌더러 공통 경로는 항상 이 값을 붙인다 |
| `<svg>` | `data-motion-choreography` (`relay` 기본, `stream`·`walk`·`sequence`·`sweep`·`replay`) | 모션 계획. 렌더러는 sequence·dataflow·lifecycle·timeline·waterfall만 붙이고 나머지 5개 타입은 속성이 없어 `relay`로 본다 |
| `<svg>` | `data-tree-ui`, `data-sequence-column-fit` | 트리 접기, 읽기 레이아웃 |
| `<svg>` | `data-reader-fit` | 읽기 레이아웃(`reader-layout.js`). 값 3개 중 `width-first`·`intrinsic-height`만 해석하고 `authored-height`(architecture + 저자 `meta.viewBox`)는 뷰어가 무시하는 **검사 전용 표시**다 |
| `<svg>` | `data-reader-min-text`(`7.5`), `data-reader-primary-text`(`14`) | 읽기 레이아웃의 글자 크기 기준(`reader-layout.js`). 속성이 없는 타입·`meta.viewBox` 조합이 있다(렌더러 쪽 조건은 rendering-contracts 1.3 A) |
| 노드·선·라벨 | `data-detail`(`context`·`fine`), `data-detail-anchor` | 세부 수준 `map`에서 둘 다, `read`에서 `fine`을 CSS가 숨기고, 포커스·호버 등 강조 중에는 숨김을 해제. 내보내기 정화가 두 속성을 제거(`viewer.css`, `reader-layout.js`, `export-cleanup.js`) |
| 범례 | `data-legend`·`data-legend-bridge`, `data-legend-semantic-kind`, `data-legend-kind`·`data-legend-label` | 범례 클릭이 Lens 종류 선택(`semantic-lens.js`), 내보내기 정화 |
| 경로 | `data-graph-role`(자동 교차 밑선 `automatic-crossover-underlay` 등) | 교차 밑선의 CSS·내보내기 처리(`viewer.css`, `export.js`) |
| 노드 | `data-node-id`, `data-node-label`, `data-node-kind`, `data-node-sublabel`, `data-node-context`, `data-node-tag`, `data-node-brand` | Finder 검색·Focus·Outline·Lens |
| 관계(선) | `data-edge-from`, `data-edge-to`, 선택 `data-edge-key`, `data-edge-label`, `data-edge-id`(같은 key를 가진 조각을 구분), `data-animate`(`node\|edge` + `--step`: 모션 순서) | Route·Reach·Relationship pin(같은 from/to/label은 키로 중복 제거, 자기 연결은 Route에서 제외) |
| `<script type="application/json">` | `id="archify-i18n-data"`(`{locale, messages}`), `id="archify-source-evidence-data"`(선택) | 문구 사전(`viewerText`), Passport의 소스 근거와 Finder 검색 |
| 텍스트 치환 | `{{i18n:viewer.*}}` | 렌더러가 로케일 문구로 치환(R-02) |

**상태 속성 (관찰 가능한 사후 상태)**

| 위치 | 속성 | 값 |
|---|---|---|
| `<html>` | `data-theme` | `light` \| `dark` |
| `<html>` | `data-preset` | `classic` \| `signal-flow` \| `blueprint` \| `editorial` (`S`가 순환, 첫 전이 classic→signal-flow) |
| `<html>` | `data-motion` | `live` \| `still` |
| `<html>` | `data-present`, `data-embed`, `data-guide-open` | `true` 또는 없음 |
| `.diagram-container` | `data-detail-level` | `map` \| `read` \| `full` |
| `<svg>` | `data-focus-active` | 포커스 노드 id(여럿이면 공백 구분) 또는 없음 |
| `<svg>` | `data-reach-active` | `upstream` \| `downstream` 또는 없음 |
| `<svg>` | `data-route-active` | `<from>~<to>`(Route 결과일 때만) 또는 없음 |
| `<svg>` | `data-lens-active` | 선택된 종류 id를 공백으로 연결 또는 없음 |
| `<html>` | `data-last-export-format`, `data-last-export-bytes`, `data-last-export-canonical`, `data-last-motion-bytes`, `data-last-export-error-format` | 마지막 내보내기 영수증(검증용 표지). 새 내보내기를 시작할 때 지워짐 |

**`Archify.*` 공개 면** (페이지 내부 계약. 같은 문서 안의 다른 모듈과 테스트가 부른다)

| 객체 | 메서드 |
|---|---|
| `focus` | `set(id, opts)`, `setMany`, `clear`, `copyLink`, `reach(direction, opts)`, `clearReach`, `reachabilitySnapshot`, `inspectRelationship(ById)`, `reposition`, `relationship`, `reachability`, `active` |
| `routeProbe` | `toggle`, `begin`, `choose`, `clear`, `escape`, `active`(`idle`/`source`/`target`/`result`), `exportSnapshot`, 저니 제어 |
| `semanticLens` | `toggle`, `open`, `close`, `clear`, `isOpen`, `active`, `clearPreview` |
| `finder` | `open`, `close`, `toggle`, `select(id)`, `isOpen`, `context`, `count` |
| `guide` | `open`, `close`, `toggle`, `execute(action)`, `isOpen`, `facts` |
| `view` | `zoomIn`, `zoomOut`, `reset`, `reveal(ids, opts)`, `sync` |
| `presentation` | `enter`, `exit`, `toggle`, `active` |
| `exportMenu` | `open`, `close`, `isOpen`, `run(format)`, `shareCard`, `downloadRouteShareCard`, `downloadReachShareCard`, `syncRouteShare`, `syncReachShare` |
| `motion` / `motionGovernor` | `canRecord`, `recordWebm` / `capable`, `pause`, `resume`, `toggle`, `setMode`, `mode`, `claim`, `release`, `suspend`, `isPaused`, `owner` |
| 그 밖 | `radar`, `outline`, `intentTrace`, `treeBranches`, `sourceEvidence`, `readerLayout`, `viewerChromeLayout`, `theme`, `preset`, `flowTokens`, `waitForStableLayout`, `layoutStability` |

**내보내기 포맷** (R-20~R-24)

| 메뉴 항목 | 파일 | 형식·제한 |
|---|---|---|
| Copy diagram | 클립보드 | PNG. `ClipboardItem`을 못 만들면 항목 비활성 |
| PNG | `<base>.png` | 배율은 4,3,2,1 중 `폭×배율×높이×배율 ≤ 16×1024×1024`인 최대값. 1배도 초과면 그 면적에 맞춰 축소 |
| JPEG | `<base>.jpeg` | 품질 0.95, 현재 테마 배경색으로 채움. 브라우저가 인코딩 못 하면 항목 비활성 |
| WebP | `<base>.webp` | 품질 0.95, 배경색 채움. 지원 판정은 `canvas.toDataURL`의 MIME 확인 |
| SVG (auto) | `<base>.svg` | 라이트·다크 변수를 둘 다 담고 `prefers-color-scheme`로 선택 |
| SVG light / dark | `<base>-light.svg` / `<base>-dark.svg` | 두 테마 변수를 담되 `prefers-color-scheme` 분기는 없음 |
| WebM | `<base>.webm` | 기본 6초(최소 250ms), 30fps, 가로 `min(1, 1280/viewBox폭)` 배율, `MediaRecorder` 6 Mbps. MIME 우선순위 `video/webm;codecs=vp9` → `vp8` → `video/webm`. svg `data-animation="trace"`와 `MediaRecorder`·`captureStream`이 없으면 비활성 |
| Route Share Card | `<base>-route-share-card.png` | 1200×630 PNG, 다운로드 전용. Route 결과가 없으면 거부 |
| Reach Share Card | `<base>-<upstream\|downstream>-reach-share-card.png` | 1200×630 PNG, 다운로드 전용. Reach가 없으면 거부 |

`<base>` = 문서 `<title>`에서 끝의 ` Architecture Diagram`/` Architecture`/` Diagram`을 떼고, 영숫자·`_`·`-` 이외 연속 문자를 `-`로 바꾸고 소문자로, 양끝 `-` 제거(빈 값이면 `diagram`).

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 조립: `template.source.html`의 마커 15개(`VIEWER_CSS` 1개 + JS 14개)를 각각 정확히 한 번 치환 | 결과는 `archify/assets/template.html`과 바이트 동일. 마커가 0번이거나 2번 이상 나오거나 조각이 비었거나 허용되지 않은 다른 마커를 품으면 오류. `EXPORT_CLEANUP`만 `export.js` 안에 중첩되며 `EXPORT`를 먼저 펼친 뒤 펼침. CSS만 각 줄에 4칸 들여쓰기(빈 줄 제외)하고 마커 줄 뒤 개행 1개를 지움. `String.replace` 치환 패턴(`$&`)을 피하려 문자열 분할로 이어붙임. `--check`는 파일을 쓰지 않고 불일치 시 오류 | 실행 확인(독립 재구현으로 바이트 동일 확인, 레포의 생성기는 실행하지 않음) |
| R-02 | 렌더러 `applyTemplate`가 템플릿을 채움 | 템플릿은 HTML 주석 마커 6개(`SOURCE_EVIDENCE_DATA`, `I18N_DATA`, `SVG_SLOT_START/END`, `CARDS_SLOT_START/END`), 자리표시 문자열 4개(`<html lang="en" data-theme="dark" data-preset="[VISUAL PRESET]">`, `<title>[PROJECT NAME] Architecture Diagram</title>`, `<h1>[PROJECT NAME] Architecture</h1>`, 부제 `<p class="subtitle">[Subtitle description]</p>`), `{{i18n:…}}` 문구 키를 가진다. SVG·카드 슬롯, 부제, 자리표시 중 하나라도 없으면 렌더가 오류. `SOURCE_EVIDENCE_DATA`는 근거 데이터가 있을 때만 필수. 이 스펙은 슬롯 이름과 위치만 정하고 채우는 규칙은 rendering | 코드 확인 |
| R-03 | 쿼리 `theme`·`embed`·`present`·`openExport` | 1.3 표대로. 테마는 쿼리 → `localStorage['archify-theme']` → 시스템 선호 → dark 순. 관찰: `?theme=light`→`data-theme=light`, `?present=1`→`data-present=true`, `?embed=1`→`data-embed=true` | 실행 확인(theme·present·embed), 코드 확인(openExport) |
| R-04 | 해시 `#focus`·`#route`·`#lens`·`#relation`을 로드하거나 `hashchange` | `#focus=api`→`data-focus-active=api`; `…&reach=downstream`→`data-reach-active=downstream`; `#route=users~worker`(데모)→`data-route-active=users~worker`, 경로 단계 `users:0 cdn:1 lb:2 api:3 queue:4 worker:5`; `#lens=backend~database`→`data-lens-active="backend database"`. 로드 후 `location.hash`를 바꿔도 동기화됨(`#focus=db`, `#route=…`). 알 수 없는 id(`#focus=nope`, `#route=users~nope`, `#relation=nope`)는 상태를 만들지 않음. 방향이 맞지 않는 경로(`#route=worker~users`)는 만들지 않음 | 실행 확인 |
| R-05 | 해시에 두 종류가 함께 있음 | 한 종류만 남는다. 관찰: `#focus=api&route=users~worker`→Route만 활성(포커스 속성 없음), `#lens=backend&focus=api`→Lens만 활성(포커스 속성 없음). 해시로 Route를 적용하면 활성 포커스는 해제됨 | 실행 확인(최종 상태만. 어느 모듈이 어떤 순서로 해제하는지는 추론) |
| R-06 | 전역 keydown. 무시: `meta`/`ctrl`/`alt` 눌림, `shift`+방향/Home/End, 이미 `defaultPrevented`, 대상이 `INPUT`/`TEXTAREA`/contentEditable. Preset 메뉴가 열려 있으면 `S`·`Escape` 외 키는 먼저 Preset을 닫음 | `?`=Guide 토글, `/`=Finder 열기, `T`=테마 토글, `S`=시각 스타일 순환, `E`=내보내기 메뉴 열기(이미 열려 있으면 무동작), `F`=발표 토글, `M`=Radar 토글, `L`=Lens 토글, `R`=Route 시작/해제(노드로 포커스 이동), `+`·`=`=확대, `-`=축소, `0`=보기 초기화. 대소문자 구분 없음. 관찰: `?`→guide 열림, 다시 `?`→닫힘, `t`→light, `s`→signal-flow, `/`→finder 열림, `l`→lens 패널 열림, `m`→radar 열림·닫힘, `r`→route `source`, `e`→메뉴 열림, `f`→`data-present=true`+`?present=1` | 실행 확인 |
| R-07 | `Escape` | 전역 핸들러 우선순위: Preset 메뉴 열림 → Lens 패널 열림 → Lens 활성 → Guide 열림 → Radar 열림 → Route 활성 → Intent Trace 활성 → Focus 활성 → 발표 중. 한 번에 하나만 처리. Finder 패널·내보내기 메뉴는 자체 keydown에서 먼저 처리(Escape가 닫고 트리거로 포커스 복귀). 관찰(발표+포커스+Reach 상태에서): 1회차 포커스 해제, 2회차 변화 없음, 3회차 발표 종료(`data-present`와 `?present=1` 제거). 2회차는 포커스 해제 뒤 DOM 포커스가 노드로 돌아가 생긴 Intent 미리보기를 해제한 것으로 보인다(`intentTrace.active()`가 `api`→`null`) | 실행 확인(순서), 코드 확인(전체 우선순위). 2회차 해석은 추론 |
| R-08 | Guide 열기(`?` 또는 버튼) / 닫기(`?`, `Escape`, 닫기 버튼, 바깥 클릭) | 열면 `data-guide-open=true`, 열려 있던 내보내기 메뉴·Finder·Radar·Lens를 닫고 진행 중인 Route Journey를 일시정지, 첫 액션 버튼에 포커스. 자동으로 열리지 않음. 패널 안에서 단축키(`/ r m l f e t s 0 + = -`)는 해당 동작을 실행하고 패널을 닫으며, 방향키·Home/End는 액션 사이를 이동(순환). 액션 id: `find route map lens present export theme preset reset zoom-in zoom-out`. 닫을 때 열기 전 포커스 요소로 복귀(없으면 트리거). `embed`에서는 열리지 않음 | 실행 확인(열기·닫기), 코드 확인(나머지) |
| R-09 | 줌 `+`/`-`/`0`, 버튼 | 단계 0.25, 범위 0.25~3(0.25 배수로 반올림). `data-detail-level`: 의미 모드(semantic)면 `full`, 아니면 배율 ≥1.75 `full`, ≥1 `read`, 그 미만 `map`. 관찰: 초기 `read`, `+`×3→`full`, `0`→`read`, `-`×2→`map` | 실행 확인 |
| R-10 | Finder 입력 | 검색 문자열 = `id label type sublabel context tag 소스근거(path label line endLine) 노드 텍스트`를 소문자로 이은 것 + brand 소문자. 질의는 trim·소문자 후 부분 문자열 포함 필터(빈 질의는 전체). 상태줄 "N of M …". 입력창에서 `Enter`=첫 결과 선택, `ArrowDown`=결과로 이동, 결과 안에서 ↑↓(순환)/Home/End. 선택하면 보기를 초기화하고 그 노드에 포커스(토글 없이)+reveal 후 패널 닫힘. Route 모드에서는 같은 패널이 시작/도착 선택기가 되어 후보를 제한. 관찰: `cac`→`cache`만, 빈 질의→10개, `redis`(sublabel/텍스트)→`cache`, `Enter`→`#focus=cache` | 실행 확인(검색·`Enter`), 코드 확인(Route 문맥) |
| R-11 | 노드 클릭, 포커스된 노드에서 `Enter`/`Space`, `Focus.set`, 해시 | 그 노드가 포커스되고 Passport(상류/하류 사실, 소스 근거, 복사 링크, 닫기)가 열린다. 같은 노드를 다시 고르거나 빈 곳을 클릭하면 해제. 해시 `#focus=<id>`가 쓰이고 해제하면 해시가 비워짐. 포커스가 있으면 Intent Trace는 막힘 | 실행 확인(해시·속성), 코드 확인(Passport 내용) |
| R-12 | Passport의 Upstream/Downstream 버튼, 해시 `reach` | 컴파일된 관계(`data-edge-key` 우선, 없으면 `from\0to\0label`, 중복 키 제거)를 방향대로 BFS해 `nodeIds`(발견 순), `edgeKeys`(양 끝이 모두 도달 집합 안인 관계), `maxDepth`를 구한다. 버튼의 개수는 도달 노드 수에서 원점을 뺀 값. 해시는 `#focus=<id>&reach=<dir>`. 관찰: `api` 하류→`data-reach-active=downstream`, `data-reach-match` 요소 12개(노드·관계 합), 원점 표지 1개 | 실행 확인 |
| R-13 | Route: `R`/Guide `route`/버튼 → 출발 선택 → 도착 선택 | 상태 `idle → source → target → result`. `source`에서 노드를 고르면(클릭·Enter/Space·Finder) `target`이 되고, 그 노드에서 도달 가능한 노드에 `data-route-candidate`. 이미 단일 포커스가 있으면 출발로 자동 선택. `target`에서 고르면 방향 있는 관계만 따라 BFS 최단 경로(홉 수 최소, 같은 홉이면 DOM 순서로 먼저 발견한 선행)를 계산해 `result`가 되고 노드·관계에 `data-route-step`=0..n, `data-route-active=<from>~<to>`, 해시 `#route=…`, 경로 패널(복사 링크, Route Journey 이전/재생/다음/전체). 기하에서 경로를 추정하지 않는다. 관찰: users→worker는 6노드 경로, `R`→`route=source` | 실행 확인 |
| R-14 | Route 오류 경로 | 도착이 출발과 같으면 패널 `data-state=error`("다른 목적지")로 `target`에 머무르고, 도달 불가면 `error`("도달 불가")로 `target`에 머무름. 둘 다 `false` 반환·경로 없음. `Escape`: 저니 재생 중이면 일시정지 → 저니 선택 중이면 개요로 → 아니면 Route 해제(보기 초기화, 해시 비움) | 코드 확인(해시로 연 도달 불가는 R-04에서 실행 확인) |
| R-15 | Lens(`L`/버튼/해시/범례 클릭) | 노드 종류를 최대 2개 선택(3번째 버튼은 비활성). 선택하면 `data-lens-active="a b"`, 해시 `#lens=a~b`, 복사 링크 지원. 해제하면 해시 비움. 패널이 열려 있으면 `Escape`가 닫고, 닫힌 채 활성이면 `Escape`가 해제 | 실행 확인(해시·속성·패널 열림), 코드 확인(2개 제한 UI) |
| R-16 | Relationship pin(`#relation=<id>`) | 유일한 컴파일 관계를 고정(원래 선 유지). 출발·도착·라벨·id 메타가 충돌하면 거부(fail closed). `embed`에서는 적용하지 않고 해제 | 코드 확인(없는 id는 R-04에서 실행 확인) |
| R-17 | Intent Trace | 정밀 포인터(`(hover:hover) and (pointer:fine)`)에서 노드 위 `pointerover`(터치 제외) 90ms 뒤(감소 모션이면 0ms) 한 홉 이웃 미리보기. 키보드 포커스(`focusin`)도 같은 미리보기. 막힘: embed, Guide 열림, 패닝 중, Lens 활성, 관계 미리보기, Route 활성, Focus 활성. 확정은 클릭(R-11) | 코드 확인. 키보드 포커스 미리보기는 R-07 관찰로 실행 확인 |
| R-18 | Live/Still 버튼 | 저장값이 없는 새 방문자는 Still(`data-motion=still`). 버튼을 누르면 `live`가 되고 `localStorage['archify-motion']='live'`, 다시 누르면 `still`이 되고 키가 삭제된다(`removeItem`). 저장값이 `live`일 때만 시작이 Live. 시스템 감소 모션이면 버튼이 비활성이고 항상 Still. 문서 숨김·인쇄·embed·시맨틱 소유자(route/lens/relationship/intent/focus/legend) 활성 중에는 흐름이 멈추고 해제되면 재개. 유효 정지 = 독자 정지 OR 감소 모션 OR 중지 요청 존재. 유효 정지로 들어가면 Route 저니도 경과 시간을 보존한 채 일시정지 | 실행 확인(버튼·저장값), 코드 확인(나머지 소유 규칙) |
| R-19 | 발표(`F`/버튼/`?present=1`) | `data-present=true`, URL에 `present=1`(종료하면 제거), 스크롤을 맨 위로, 보기 자동 초기화 후 동기화. 종료하면 이전 스크롤 위치 복원. 저작된 도형은 바꾸지 않는다 | 실행 확인(진입·종료·쿼리), 코드 확인(스크롤) |
| R-20 | 내보내기 PNG/JPEG/WebP 실행 | 메뉴를 닫고(트리거로 포커스) 이전 영수증을 지운 뒤 래스터화해 `download`. 데모 산출물(viewBox 1184×742)의 PNG는 4736×2968(4배, 14.06Mpx ≤ 16Mpx). MIME과 시그니처: `image/png`(`89504e47…`), `image/jpeg`(`ffd8ff`), `image/webp`(`RIFF…WEBP`). 파일명 `sample-web-app.<ext>` | 실행 확인(PNG 크기·시그니처·이름, JPEG/WebP 시그니처), 코드 확인(배율 규칙·품질 0.95·배경 채움) |
| R-21 | 내보내기 SVG 3종 | `serializeSvg(1, {theme})`로 직렬화해 `image/svg+xml;charset=utf-8`로 다운로드. 파일명은 auto `<base>.svg`, `<base>-light.svg`, `<base>-dark.svg`. auto만 `prefers-color-scheme`를 포함하고, 세 파일 모두 라이트/다크 변수를 포함. 임베드 폰트 CSS(`archify-fonts`)와 소프트웨어 고지 메타를 함께 담는 경로가 있다 | 실행 확인(MIME·이름·prefers 유무), 코드 확인(폰트·고지) |
| R-22 | 내보내기 WebM | `canRecord()`(svg `data-animation="trace"` + `MediaRecorder` + 지원 MIME + `captureStream`)일 때만. 6초 동안 30fps로 캔버스를 녹화: 선명한 정적 SVG 배경 위에, 실제 관계 기하를 따라 시간에 따라 변하는 신호 장면을 프레임마다 그림(CSS 애니메이션을 캡처하지 않음). 결과 `video/webm;codecs=vp9`, 파일명 `<base>.webm`, 완료 토스트. 실패 시 WebM 항목을 비활성화하고 토스트(다른 형식의 실패는 `alert`) | 실행 확인(데모에서 vp9, 시그니처 `1a45dfa3`, 약 1.0~1.2MB. 영상 길이는 측정하지 않음), 코드 확인(실패 처리) |
| R-23 | Share Card | Route 결과가 있으면 Route Share Card, Reach가 있으면 Reach Share Card 항목이 보이고 활성(`hidden`/`disabled` 해제). 1200×630 PNG, 다운로드 전용, 영수증에 `canonical=false`. 스냅샷이 없거나 낡았으면 거부. Reach 카드는 이미 계산된 도달 집합을 쓰며 탐색을 다시 하지 않는다. 용어는 "authored reachability"(영향·폭발 반경이 아님) | 실행 확인(두 카드 모두 1200×630 PNG와 이름), 코드 확인(거부 조건) |
| R-24 | 내보내기 메뉴 조작·오류 | 트리거나 `E`로 열고 ↑/↓(순환)·Home/End 이동, `Escape`는 닫고 트리거로 포커스, `Tab`·바깥 클릭은 포커스 강제 없이 닫음. 지원하지 않는 형식 문자열(`gif`)은 시작 전에 거부("Not supported by this browser"). 다운로드 URL은 1000ms 뒤 해제. 클립보드 복사는 `ClipboardItem`을 Promise로 구성해 사용자 제스처 안에 두고, 동기 거부는 Blob 폴백, 비동기 쓰기 거부는 폴백 없음 | 실행 확인(`gif` 거부, `e`로 열기·`Escape`로 닫기), 코드 확인(나머지) |
| R-25 | 내보내기 정화(clean) | 복제 SVG에서 뷰어 상태를 제거: 포커스·Reach·Route·Lens 속성과 강조, 흐름 오버레이, Intent 오버레이, 카메라 변환, 임시 UI. 관찰: 포커스+하류 Reach가 켜진 상태에서 SVG 내보내기→복제본의 루트 `data-focus-active`·`data-reach-active`, `[data-reach-match]`·`[data-ambient-flow-overlay]` 요소가 0개(라이브는 12개·54개), `data-node-id` 10개·`data-edge-from` 15개는 그대로. 내보낸 뒤에도 라이브의 포커스·Reach 유지. Share Card만 자체 정적 표지(`data-share-route-*`/`data-share-reach-*`)를 씀 | 실행 확인(SVG 한 경우), 코드 확인(정화 항목 전체). 래스터·WebM의 동일 정화는 미확인 |
| R-26 | 읽기 레일·Outline·Radar·트리 | 뷰포트 ≥1280px에서 폭 288px 요약 레일이 노드 목록(Outline, 맥락별 그룹, 호버=Intent 미리보기, 선택=Finder 경로로 포커스)을 보인다. 기본 레일이 주 텍스트를 12px 미만으로 줄이면 접힌 채 시작. 레일 접힘·위치는 `localStorage`에 기억. Radar(`M`)는 의미 경계와 현재 뷰포트를 그리며 도형의 원본이 아니다. 트리 다이어그램(`data-tree-ui`)만 접기/펼치기를 가지며, 숨은 노드를 Finder/Outline/링크로 고르면 조상을 펼치고 내보내기는 항상 전체 트리 | 코드 확인(주석·상수 수준). 레이아웃 수치·실제 모양은 미확인 |
| R-27 | `data-reading-link-template` | R-04 복사 링크 규칙 그대로(상태 문자열은 `focus=…`, `relation=…`, `route=a~b`, `lens=a~b`) | 코드 확인 |
| R-28 | `localStorage` | 키 4개: `archify-theme`(`light`/`dark`), `archify-motion`(`live`만 저장), `archify-rail-collapsed`, `archify-rail-placement`. 모든 접근은 try/catch이며 접근 실패해도 페이지는 메모리 상태로 동작 | 코드 확인(theme·motion은 R-03·R-18에서 실행 확인) |
| R-29 | 가이드 뷰(`guided-views.js`) | 조립되지 않는다. `template.html`에 `guided-view` 문자열이 0건이고 `#view=d1`은 아무 상태도 만들지 않는다 | 실행 확인(조립 재현, 해시 무시), 추론(2026-09-25 `fca0dc2f`("no guided views")로 제거된 기능의 잔여 파일이라는 해석) |

- 불변식: 해시·쿼리 외의 상태(포커스·Route·Lens 선택 등)는 페이지 메모리에만 있고 새로고침 때 해시로만 복원된다. 내보내기는 포커스·Reach 라이브 상태를 바꾸지 않는다(R-25). 저작된 기하는 어떤 뷰어 기능도 바꾸지 않는다(`viewer-runtime.md`의 요구, 코드 주석에도 반복).
- 미결정: 없음.
- 확인 한계: 실행 확인은 headless Chrome 156(macOS)에서 합성 키 입력과 `Runtime.evaluate`로, 데모 산출물 하나(architecture, 노드 10·관계 15)에만 했다. 포인터 호버, 드래그 패닝, 터치, 모바일, 실제 클립보드 복사, 인쇄, Safari·Firefox, `?openExport=1`, WebM 영상 길이·화질, 시각 검토는 미확인. Radar·Relationship pin·Route Journey 재생·트리 접기·레일 접기는 코드로만 읽었다(R-16, R-26).

### 1.5 필수 코드 참조 [필수]
라이선스 Apache-2.0이므로 인용은 허용된다(overview 1절). 글보다 코드가 짧고 정확한 규칙만 가져온다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `scripts/generate-viewer.mjs:14-85` `fragments`, `generateViewer` | 마커↔파일 표(15개, CSS만 들여쓰기 4), 마커 한 번 분할, 중첩 `EXPORT_CLEANUP` 검증, 마커 줄 개행 제거, `--check` 비교 | R-01 |
| C-02 | `archify/renderers/shared/utils.mjs:130-148,150-199` `SVG_SLOT_RE`·`CARDS_SLOT_RE`·`TEMPLATE_PLACEHOLDERS`·`applyTemplate` | 슬롯 정규식(들여쓰기 포함)과 자리표시 4개, 누락 시 오류 | R-02 |
| C-03 | `viewer/template.source.html:12-23,1348-1437` | 쿼리 파싱, 전역 단축키 핸들러와 Escape 우선순위 | R-03, R-06, R-07 |
| C-04 | `viewer/focus.js:72-121` `computeReachability` | Reach BFS와 `edgeKeys`·`maxDepth` 정의 | R-12 |
| C-05 | `viewer/focus.js:1562-1583`, `viewer/route-probe.js:911-926`, `viewer/semantic-lens.js:535-550` | 세 `syncFromHash`의 파싱·검증(Route `split('~')` 길이 2, Lens 필터와 `slice(0,2)`) | R-04, R-05 |
| C-06 | `viewer/route-probe.js:265-325` `outgoingByNode`·`shortestDirectedPath` | Route 그래프 구성(자기 연결·미존재 노드 제외)과 BFS 최단 경로 | R-13 |
| C-07 | `viewer/viewer-camera.js:10-11,91-96,289-293` | 줌 범위 0.25~3, 0.25 단위 반올림, 읽기 깊이 임계(1.75, 1) | R-09 |
| C-08 | `viewer/node-finder.js:61-82,133-141` | Finder 검색 문자열 구성과 필터 | R-10 |
| C-09 | `viewer/motion-governor.js:515-523,671` | 저장 규칙(`live`만 저장, 정지는 삭제), 시작 상태 | R-18 |
| C-10 | `viewer/template.source.html:701-710` `readerLink` | 복사 링크 템플릿 검증 | R-04, R-27 |
| C-11 | `viewer/export.js:14-42,453-460` | 상수(배율 4, 6000ms, 30fps, 1200×630), 파일명 규칙, `pickSafeScale`와 16Mpx 상한 | R-20~R-23 |
| C-12 | `viewer/export.js:774-811,1100-1110` | WebM MIME 후보·`canRecordMotion`·옵션 기본값·배율, 형식 지원 판정 | R-20, R-22 |
| C-13 | `viewer/export.js:1208-1245,1262-1290` `runExport`, Share Card 이름 | 형식 문자열 화이트리스트, SVG/WebM/래스터 분기, 파일명 접미사 | R-21, R-23, R-24 |

C-ID 범위 안의 내부 helper는 1.3으로 풀었다: `viewerText`/`viewerCount`(`archify-i18n-data`의 `messages` 조회), `nodesById`/`edges`(DOM의 `data-node-id`, `data-edge-from/to` 질의), `serializeSvg`(1.3 내보내기 표의 테마 변형), `renderShareCard`(1200×630 카드), `Archify.view.reveal`(해당 노드가 보이도록 카메라 이동, 세부 수치는 R-26과 같이 미확인).

### 1.6 수락 사례 [필수]
출처: 원본 실행 관찰(headless Chrome으로 `archify demo` 산출물 `demo.html`을 연 기록). T-08만 조립 재현. 재구현 검증은 아님.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-04, R-11 | `demo.html#focus=api` 로드 | `<svg data-focus-active="api">`. `#focus=nope`이면 속성 없음 |
| T-02 | R-04, R-12 | `#focus=api&reach=downstream` / `&reach=upstream` | 각각 `data-reach-active="downstream"` / `"upstream"` |
| T-03 | R-04, R-13 | `#route=users~worker` | `data-route-active="users~worker"`, 단계 `users:0 cdn:1 lb:2 api:3 queue:4 worker:5`. `#route=worker~users`와 `#route=users~nope`은 속성 없음 |
| T-04 | R-04, R-15 | `#lens=backend~database` / `#lens=backend~database~cloud` | 둘 다 `data-lens-active="backend database"` |
| T-05 | R-05 | `#focus=api&route=users~worker` / `#lens=backend&focus=api` | 각각 Route만 / Lens만 활성(포커스 속성 없음) |
| T-06 | R-03 | `?present=1`, `?theme=light`, `?embed=1#focus=api` | 각각 `data-present=true`, `data-theme=light`, `data-embed=true`이고 마지막은 `data-focus-active=api`도 있음 |
| T-07 | R-06, R-09, R-10 | `?`, `t`, `s`, `+`×3, `0`, `-`×2, `/`, 질의 `cac`, `Enter` | guide 열림→닫힘, theme light, preset signal-flow, detail full→read→map, finder 열림, 결과 `cache` 1개(상태줄 "1 of 10 nodes"), `Enter` 후 해시 `#focus=cache` |
| T-08 | R-01, R-29 | 레포의 `viewer/*`를 규칙대로 합친 결과를 `template.html`과 비교 | 787,334바이트 동일, 남은 JS/CSS 마커 없음, `guided-views.js`는 쓰이지 않음 |
| T-09 | R-07, R-19 | `f`로 발표 진입 후 `#focus=api&reach=downstream` 상태에서 Escape 3회 | 1회 포커스·해시 해제(`present` 유지), 2회 변화 없음, 3회 `data-present` 제거와 `?present=1` 삭제 |
| T-10 | R-18 | 저장값 없는 새 프로필에서 모션 버튼 2회 | 1회: `data-motion=live`·`archify-motion=live`, 2회: `still`·키 삭제 |
| T-11 | R-20, R-21, R-22 | `Archify.exportMenu.run('png'/'jpeg'/'webp'/'svg'/'svg-light'/'svg-dark'/'webm')` | 파일명 `sample-web-app{.png,.jpeg,.webp,.svg,-light.svg,-dark.svg,.webm}`, PNG 4736×2968, WebM `video/webm;codecs=vp9`. auto SVG만 `prefers-color-scheme` 포함 |
| T-12 | R-23 | Route 결과가 있는 상태, `api` 하류 Reach 상태에서 각 카드 다운로드 | `…-route-share-card.png`, `…-downstream-reach-share-card.png`, 둘 다 1200×630 PNG |
| T-13 | R-25 | `api` 포커스+하류 Reach 상태에서 `run('svg-dark')` | 내보낸 SVG의 `[data-reach-match]` 0개, `[data-ambient-flow-overlay]` 0개, 루트에 `data-focus-active`·`data-reach-active` 없음. 라이브의 포커스·Reach는 유지 |
| T-14 | R-24 | `run('gif')` | 시작 전에 거부, 다운로드 없음 |

재현 기록: [deeplink.log](../../../artifacts/archify/spec-demos/viewer/deeplink.log), [cdp-run.log](../../../artifacts/archify/spec-demos/viewer/cdp-run.log), [cdp-run.json](../../../artifacts/archify/spec-demos/viewer/cdp-run.json), [assemble-check.out](../../../artifacts/archify/spec-demos/viewer/assemble-check.out). 스크립트: [deeplink.sh](../../../artifacts/archify/spec-demos/viewer/deeplink.sh), [cdp-run.mjs](../../../artifacts/archify/spec-demos/viewer/cdp-run.mjs), [assemble-check.mjs](../../../artifacts/archify/spec-demos/viewer/assemble-check.mjs). 입력: [demo.html](../../../artifacts/archify/spec-demos/viewer/demo.html)(`archify demo` 산출물 사본).

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
repo@a4065941f12be7967436261d9934784e381d423c 기준.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01, T-08 | C-01, `viewer/README.md:23-45`(조립 설명), 독립 재구현 [assemble-check.mjs](../../../artifacts/archify/spec-demos/viewer/assemble-check.mjs) | 재구현이 만든 787,334바이트가 `archify/assets/template.html`과 같음. 레포의 `generate-viewer.mjs`는 실행하지 않았다(clone 코드 실행 금지) |
| R-02 | C-02, `viewer/template.source.html:170,287-292,439,614,655`(마커 위치), `archify/renderers/shared/cli.mjs:363`(`data-animation="trace"`) | 코드 확인. 렌더러가 채우는 값은 rendering 소관. 1.3 속성 표의 `data-detail*`·`data-reader-*`·`data-legend*`·`data-graph-role`·`data-edge-id`·`data-animate` 행은 [rendering-contracts.md](rendering-contracts.md) R-04~R-07 근거(뷰어 참조 파일을 `grep`으로 재확인: `viewer/reader-layout.js`·`viewer.css`·`export-cleanup.js`·`export.js`·`semantic-lens.js`·`focus.js`·`route-probe.js`·`motion-governor.js`)로 쓴다. 분기 하나하나는 읽지 않았다(grep 수준) |
| R-03 | C-03(`12-23`), `viewer/template.source.html:876-892`(theme 모듈), `viewer/export.js:1404-1418` | theme·present·embed는 [deeplink.log](../../../artifacts/archify/spec-demos/viewer/deeplink.log)로 실행 확인 |
| R-04, R-05, T-01~T-05 | C-05, `viewer/focus.js:152,228,816,1308,1384`, `viewer/route-probe.js:186-190,888-899`, `viewer/semantic-lens.js:321-327,520-530`, [deeplink.log](../../../artifacts/archify/spec-demos/viewer/deeplink.log), [cdp-run.log](../../../artifacts/archify/spec-demos/viewer/cdp-run.log) | headless Chrome으로 URL을 열어 DOM 속성을 읽음. 결합 해시에서 모듈 간 해제 순서는 미검증 |
| R-06, T-07 | C-03(`1348-1437`) | 합성 키 입력(`Input.dispatchKeyEvent`)으로 확인. 단축키 목록은 코드 주석과 일치 |
| R-07, T-09 | C-03, `viewer/intent-trace.js:163-195` | 3회차 종료는 실행 관찰. 2회차가 Intent 해제라는 점은 `intent` 필드 관찰에서의 해석 |
| R-08 | `viewer/template.source.html:1180-1345` `Archify.guide` | 열기·닫기는 실행 확인. 액션 id 표와 키 매핑 `actionForKey`는 코드 확인 |
| R-09, T-07 | C-07, `viewer/viewer-camera.js:604-605` | 실행 확인 |
| R-10 | C-08, `viewer/node-finder.js:196-240` | 실행 확인(검색·`Enter`), Route 문맥은 코드 확인 |
| R-11 | `viewer/focus.js:1316-1395,1395-1420`, `viewer/template.source.html:495-540`(Passport 마크업) | 해시·속성은 실행 확인, Passport 내용은 코드 확인 |
| R-12 | C-04, `viewer/focus.js:173-215` | `api` 하류/상류 실행 확인 |
| R-13, R-14 | C-06, `viewer/route-probe.js:694-800` | 해시 경로는 실행 확인. 오류 상태는 코드 확인 |
| R-15 | `viewer/semantic-lens.js:300-330,460-480,520-550` | 해시·속성·패널 열림 실행 확인 |
| R-16 | `viewer/focus.js:820` `inspectRelationshipById`, `viewer/focus.js:1562-1583`, `archify/references/viewer-runtime.md:16-17` | 코드·문서 확인 |
| R-17 | `viewer/intent-trace.js:20-50,160-195` | 코드 확인 |
| R-18 | C-09, `viewer/motion-governor.js:7,20,516-540`, `viewer/README.md:817-888` | 실행 확인(버튼·저장). 문서와 구현 일치 |
| R-19 | `viewer/template.source.html:1090-1135` `Archify.presentation` | 실행 확인 |
| R-20~R-24, T-11, T-12, T-14 | C-11, C-12, C-13, `viewer/export.js:561-600,637-760,1066-1090,1262-1300`, [cdp-run.log](../../../artifacts/archify/spec-demos/viewer/cdp-run.log) | `download` 앵커 클릭을 가로채 Blob의 MIME·크기·시그니처·PNG 크기를 읽음. 레포 코드가 아닌 산출물 안의 런타임을 실행 |
| R-25, T-13 | `viewer/export-cleanup.js`, `viewer/README.md:889-925`, [cdp-run.log](../../../artifacts/archify/spec-demos/viewer/cdp-run.log) | 내보낸 SVG를 `DOMParser`로 파싱해 속성·요소 수를 라이브 DOM과 비교. 래스터·WebM은 미확인 |
| R-26 | `viewer/reader-layout.js:40-70`, `viewer/node-outline.js:1-20`, `viewer/tree-branches.js:1-25`, `viewer/semantic-radar.js:1-30`, `viewer/README.md:566-816` | 코드 확인(주석·상수 수준) |
| R-27 | C-10, `viewer/focus.js:1395-1402`, `viewer/route-probe.js:888-900`, `viewer/semantic-lens.js:520-530` | 코드 확인 |
| R-28 | `viewer/template.source.html:876-892`, `viewer/motion-governor.js:515-523`, `viewer/reader-layout.js:50-62` | 코드 확인 |
| R-29, T-08 | `scripts/generate-viewer.mjs:14-30`(목록에 없음), `test/repository-language-metadata.test.mjs:50`(파일명만 열거), `git show fca0dc2f`(제목 `feat(viewer)!: … no guided views`) | 조립 재현과 `#view=d1` 무시는 실행 확인. 제거 이유 해석은 커밋 제목 기반 추론 |

**문서와 구현의 차이·발견** (구현을 사실로 썼다)
- `viewer-runtime.md`는 "Every rendered diagram enables reader-controlled Live/Still"이라 쓰고, 구현은 svg `data-animation="trace"`가 있을 때만 모션 컨트롤이 켜진다(`motion-governor.js:20`). 렌더러 공통 경로가 항상 `trace`를 붙이므로(`cli.mjs:363`) 결과는 같다. `meta.animation: "none"`을 넣어도 렌더러는 이 입력을 읽지 않고 `trace`를 항상 붙인다(무효. 10개 타입 × 3조건 SVG 해시 동일, [rendering-contracts.md](rendering-contracts.md) R-01). 그래서 입력으로 Live/Still을 끌 수 없다.
- `template.source.html`의 전역 단축키 주석은 "Escape → clear temporary trace/focus/view first, then exit presentation"이고, 발표 모드 주석은 "Escape first clears an active focus, then exits the stage"다. 실제로는 포커스 해제 뒤 Intent 미리보기가 한 번 더 끼어 Escape가 3번 필요했다(R-07).
- 작업 요청과 feature map은 "가이드 뷰"를 이 기능의 경계로 적지만 `guided-views.js`는 조립되지 않는 잔여 소스다(R-29). `viewer/README.md`의 파일 목록에도 이 파일이 없다.
- `viewer/README.md` Export 절 일부(WebM 자원 수명 표)는 중국어로 쓰여 있다. 영어 본문과 동작은 일치한다.

### 2.2 코드 읽는 순서 [선택]
1. `viewer/README.md`(모듈 책임·초기화 순서) → `scripts/generate-viewer.mjs`(15줄짜리 표가 조립 규칙의 전부).
2. `viewer/template.source.html`: 셸 마크업(툴바 170-260, 다이어그램 컨테이너 286-295, Passport 495-540, 내비게이션 598-602) → 전역 모듈(`Archify` 객체 668, `viewerText` 690, `readerLink` 701, theme 876, presentation 1090, guide 1180, 단축키 1348).
3. 상태 모듈은 `focus.js`(선택·관계·Reach) → `route-probe.js`(Route) → `semantic-lens.js` → `node-finder.js` 순. 그 뒤에 모션(`motion-governor.js`)과 카메라(`viewer-camera.js`).
4. `export.js`는 마지막에: 상수와 파일명 → `serializeSvg` → `rasterize` → `recordWebm` → `runExport`와 Share Card.
5. 구현 전략: 상태는 `<svg>`의 `data-*` 속성으로 표현하고 CSS(`viewer.css`)가 그 속성을 보고 그린다. 저작된 기하·SVG 요소는 바꾸지 않고, 모션은 같은 경로를 따르는 별도 오버레이 `<path>`(관계마다 하나)를 둔다. `README`가 "Moving CSS can change export output even when the live page looks similar"라고 경고한다.
