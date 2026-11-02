---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/scripts/check-render-output.mjs
  - archify/bin/archify.mjs
  - archify/bin/visual-check.mjs
  - archify/bin/finalize.mjs
  - archify/renderers/shared/geometry.mjs
  - archify/renderers/shared/desktop-readability.mjs
  - archify/renderers/shared/svg-path-analysis.mjs
  - archify/references/delivery-contract.md
depends: [delivery.md]
status: ready            # 2026-11-02: 이 스펙 자체의 미결정 없음, 선행 스펙 ready
---

# 자동 검증 게이트 (`check`, `browser-check`)

> 전달된 HTML 파일(과 그 옆의 provenance 파일)을 받아, 브라우저 없이 SVG를 정적으로 검사(`check`)하고 실제 Chrome 4개 뷰포트에서 넘침·글자 크기를 측정(`browser-check`)해 통과/실패(`browser-check`는 건너뜀 포함)와 진단을 돌려주는 두 게이트.

<!--
원본에서 확인한 범위: check-render-output.mjs 전체, archify.mjs의 provenance 판정과 두 명령, visual-check.mjs의 판정·Chrome 실행 경로, geometry.mjs와 desktop-readability.mjs에서 check가 부르는 함수.
읽지 않은 것: 뷰어 런타임(`Archify.*.whenStable` 등 template.html 안의 JS), explainer 전용 check/browser-check, 타입별 렌더러. 위 "경계"에서 제외로 명시.
스크립트·출력: ../../../artifacts/archify/spec-demos/verification-gates/ (이하 DEMO)
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

`check` (정적):
1. `archify check <html> [--json] [--require-provenance]` 인자를 검사한다(R-01).
2. provenance를 읽어 HTML 바이트의 SHA-256·바이트 수를 sidecar 기록과 대조한다. 불일치·잠금·미완료 등이면 정적 검사 없이 실패 영수증을 내고 종료 코드 1(R-02, R-03).
3. 통과하면 `scripts/check-render-output.mjs <html>`을 자식 프로세스로 실행해 그 JSON을 받는다(R-04).
4. 스크립트는 HTML 안의 `<svg>`가 정확히 하나일 때 SVG 문자열을 정규식으로 훑어 화살표 경로·라벨·프레임·글자 크기를 수집하고 검사 9개와 `composition` 보고서를 만든다(R-05~R-20).
5. CLI가 `provenance`, `deliveryReceiptId`를 덧붙이고, 검사 도중 파일이나 sidecar가 바뀌지 않았는지 다시 확인한 뒤 JSON을 출력한다. 종료 코드는 스크립트의 코드(R-04).

`browser-check` (브라우저):
1. `archify browser-check <html> [--json|--summary] [--require-provenance] [--out-dir <dir>]` 인자를 검사하고 provenance를 먼저 대조한다. 실패하면 Chrome을 띄우지 않고 실패 영수증을 파일로 남긴 뒤 종료 코드 1(R-24).
2. HTML 바이트를 임시 폴더에 복사하고 Chrome 실행 파일을 찾는다. 없으면 `skipped`, 종료 코드 2(R-25, R-26).
3. headless Chrome을 DevTools 파이프로 띄워 한 세션에서 라이트 4개 뷰포트(1440×900, 1600×1000, 1920×1080, 2048×1320)와 다크 2개(1440×900, 2048×1320)를 차례로 열고, 매번 모션 `still`·상세도 `read`로 맞춘 뒤 측정 스크립트를 실행한다(R-27, R-28).
4. 측정값으로 넘침·테마·글자 하한·뷰어 UI 간섭을 판정한다(R-29~R-32).
5. 영수증 `<stem>.browser-check.json`을 쓰고(스크린샷 없음) 통과 0 / 실패 1 로 종료한다(R-33, R-34).

두 게이트를 부르는 순서와 finalize 영수증은 finalize-orchestration 소관이다. 여기서는 `finalize`가 둘을 `requireProvenance: true`로 부른다는 경계만 안다(R-24).

### 1.2 범위·통합 지점 [필수]
- 제공: 전달된 HTML에 대한 정적 검사 9종과 composition 보고서, provenance 대조, Chrome 측정 판정, 영수증.
- 제외:
  - provenance 파일의 이름 규칙·작성·교체·잠금·복구. 이 스펙은 읽기만 한다(delivery.md 소관).
  - 진단 객체의 공통 모양(`code, severity, message, subject, evidence, supportedFixes`, input-validation 소관). 여기서는 gate별 code와 조건만 쓴다.
  - 렌더러 안의 배치 검증(`layout/*`, `composition/label-gap` 등. 노드 겹침은 거기서 잡히고 `check`는 보지 않는다. R-21, T-12).
  - finalize가 부르는 순서·영수증(finalize-orchestration 소관).
  - explainer HTML. `check`는 `explainer/check.mjs`로, `browser-check`는 `explainer/browser-check.mjs`와 다른 뷰포트 집합으로 넘긴다(R-06). 행 10 소관.
  - `visual-check`의 스크린샷 내용과 시각 검토. 이름·조건만 1.3에 적는다.
- 외부 의존·선행 계약:
  - 선행 delivery: HTML과 같은 폴더의 `<stem>.delivery.json`(이름은 delivery 규칙). 이 스펙이 읽는 필드는 1.3의 "provenance 필드" 표뿐이다.
  - Chrome/Chromium/Edge 실행 파일, 환경변수 `ARCHIFY_CHROME`, `ARCHIFY_CHROME_NO_SANDBOX`, `ARCHIFY_CHECK_MAX_BUFFER`.
  - 뷰어 런타임: HTML 안의 JS가 `html[data-theme]`, `data-reader-*` 속성, `Archify.layoutStability.whenStable()` 등을 제공한다고 가정한다(렌더링·뷰어 행 소관).
- 소유 상태·부작용: `check`는 stdout JSON만 낸다(파일 쓰기 없음). `browser-check`는 영수증 JSON 하나를 쓰고(실패·skipped도 씀), 임시 폴더 `archify-inspection-*`(HTML 사본)과 `archify-visual-check-profile-*`(Chrome 프로필)를 만들었다가 지운다. 대상 HTML과 provenance는 바꾸지 않는다.

### 1.3 인터페이스와 데이터 의미 [필수]

**CLI**

| 연산 | 입력 | 의미·제약 |
|---|---|---|
| `check <output.html> [--json] [--require-provenance]` | 위치 인자 정확히 1개. 옵션은 이 둘뿐 | 알 수 없는 `--옵션`, 위치 인자 0개·2개 이상은 사용법 출력 후 종료 코드 2. `--json`은 받기만 하고 효과가 없다(출력은 항상 pretty JSON) |
| `browser-check <output.html> [--json] [--summary] [--require-provenance] [--out-dir <dir>\|--out-dir=<dir>]` | 위치 인자 정확히 1개 | 알 수 없는 옵션·인자 개수 오류는 종료 코드 **1**(check는 2). `--out-dir` 값 없음도 종료 코드 2로 즉시 종료. `--json`이면 영수증 전체를, `--summary`면 `summarizeBrowserEvidence` 한 줄 JSON을, 둘 다 없으면 3줄 텍스트(통과/실패 줄, containment·captures·visualReview 줄, `receipt <경로>`)를 stdout에 낸다 |
| `visual-check` (같은 옵션) | 같음 | browser-check에 스크린샷을 더한 변형. 라이트·다크 × 1440×900·2048×1320 PNG 4장과 contact sheet HTML을 만든다(R-37) |
| `node scripts/check-render-output.mjs <html>` | 위치 인자 1개 | 인자 없으면 사용법을 stderr에 내고 종료 코드 2(`-h`/`--help`는 0). 파일을 못 읽으면 `{ok:false, checks:[{name:'file_readable', ok:false}]}` 후 종료 코드 1 |

**`--out-dir`**: 영수증을 둘 폴더. 생략하면 HTML과 같은 폴더. 값은 `resolveNativeOutputDirectory`로 검증하고(실패 시 진단 `output/native-path-syntax` 등과 종료 코드 1, 영수증 파일은 쓰지 않고 stdout/stderr에만 출력), 폴더가 없으면 만든다. HTML과 폴더가 다르면 영수증 `sidecars.directory`에 그 절대 경로가 들어간다.

**check 출력 JSON** (스크립트가 만들고 CLI가 덧붙임)

| 필드 | 의미 |
|---|---|
| `ok` | `checks`가 전부 `ok`이고 `composition.status !== 'fail'`이면 true. 이름 있는 검사가 모두 통과해도 `composition.status:'fail'`(예: `composition/desktop-readability` 오류)이면 false |
| `file` | 절대 경로 |
| `artifact` | `{sha256, bytes}` (스크립트가 읽은 바이트) |
| `checks[]` | `{name, ok, details[]}`. 이름·순서는 R-05 |
| `composition` | `{schemaVersion:1, profile, status:'pass'|'fail', summary:{errors, warnings}, metrics, suggestedLimits, routeReview, leadingSpace, [sequenceColumnSpace], [sequenceNoteBorders], desktopReadability, issues[]}`. `issues[]` 항목은 `{severity:'error'|'warning', code, ...증거}` |
| `diagnostics[]` | `svg_path_data`가 실패했을 때만. 경로 분석 오류 진단 |
| `provenance`, `deliveryReceiptId` | CLI가 추가. `provenance`는 `current`/`unknown`(sidecar 없음·플래그 없음), `deliveryReceiptId`는 sidecar의 `receiptId`(있을 때) |
| (실패 시) `error`, `diagnostic`, `diagnostics[]` | provenance 실패 영수증: `{schemaVersion:1, ok:false, command:'check', provenance:<status>, [deliveryReceiptId], artifact:{path}, error, file, diagnostic, diagnostics[]}` |

**provenance 필드** (읽는 쪽 계약. 쓰는 규칙은 delivery.md): `schemaVersion`=1, `command`='deliver', `receiptId`(UUID v4 형식), `status`('current'|'failed'), `input`·`output`(절대 경로 문자열), 그리고 `status:'current'`이면 `type`(지원 타입 집합 안), `specification`·`artifact` 각각 `{sha256: 64자리 소문자 hex, bytes: 0 이상 정수}`, `status:'failed'`이면 `stage`(문자열). 대조에 쓰는 해시는 `artifact`뿐이다. `specification` 해시는 형식만 검증하고 비교하지 않는다.

**browser-check 영수증 JSON** (`<stem>.browser-check.json`)

| 필드 | 의미 |
|---|---|
| `schemaVersion`:1, `command`:'browser-check', `evidenceKind`:'automated-browser' | 고정 |
| `ok`, `status` | `status`는 'pass'/'fail'/'skipped'. `ok`는 pass일 때만 true |
| `visualReview` | browser-check는 항상 'not-requested'(visual-check는 'pending') |
| `provenance`, `deliveryReceiptId` | provenance 상태와 sidecar 영수증 ID(해당할 때) |
| `artifact` | `{path, sha256, bytes}` |
| `state` | `{detail:'read', motion:'still'}` 고정 |
| `chrome` | `{status:'available'\|'unavailable'\|'not-checked', executable}` |
| `diagnostics[]` | 진단(R-29~R-32, R-26, R-36) |
| `containment` | `{status, policy:'fit-or-reader-declared-readable-vertical-scroll', viewports[]}` 라이트 4개 관측치 |
| `themeStates` | `{status, viewports[]}` 6개 관측치 각각 `{width,height,requestedTheme,resolvedTheme,ok}` |
| `readability` | `{status, minimumProjectedNodeTextPx:6, viewports[]}` 라이트 4개 관측치의 사본 |
| `viewerChrome` | `{status, viewports[]}` 라이트 4개 관측치의 사본 |
| `captures` | browser-check는 `{status:'not-requested', screenshots:[], contactSheet:null}` |
| `sidecars` | `{[directory], receipt:<파일명>, files:[]}` |
| `error` | 실패·skipped의 한 줄 사유 |

관측치 하나(`viewports[]` 원소)의 필드: `width, height, theme, innerWidth, innerHeight, scrollWidth, scrollHeight, overflowX, overflowY, verticalScrollAccepted, overflowDisposition('contained'|'readable-vertical-scroll'|'unexpected-overflow'), readerLayout, readerOverflow, readerFit, [diagramType, documentScrollUnclipped], ok, readerWidth, diagramWidth, pageComposition, viewBoxWidth, [workflowLanes], minimumProjectedNodeTextPx, minimumProjectedNonEdgeTextPx, minimumProjectedEdgeTextPx, minimumProjectedNodeText, minimumProjectedNodeTextDetail, minimumProjectedNodeTextOwner, minimumRequiredNodeTextPx:6, readabilityOk, hasLegend, hasNavigationDock, legendDockIntersectionArea, dockStageIntersectionArea, dockStageGap, requiredDockStageGap, viewerChromeStageOk, viewerChromeReserve, viewerChromeActive, viewerChromeOk, resolvedTheme`.

**영수증 파일 이름**: `<HTML 파일명에서 .html을 뗀 stem>.browser-check.json`을 `--out-dir`(또는 HTML 폴더)에 둔다. stem이 너무 길거나 대소문자·정규화 충돌 가능성이 있으면 해시로 줄이는 규칙(delivery와 공유하는 `boundedSidecarStem`)을 따른다. visual-check는 `<stem>.visual-check.json`, `.visual-check.html`, `.visual-check.<W>x<H>.<theme>.png`.

**Chrome 탐색 순서** (`findChrome`; 실행 가능 여부는 `X_OK`, Windows는 존재 여부)
1. 환경변수 `ARCHIFY_CHROME`가 설정돼 있으면(빈 문자열 포함) 그 값만 쓴다. 실행할 수 없으면 다른 브라우저로 넘어가지 않고 "없음"이다.
2. macOS: `/Applications/Google Chrome.app/.../Google Chrome` → `/Applications/Chromium.app/.../Chromium` → `/Applications/Microsoft Edge.app/.../Microsoft Edge` → PATH의 `microsoft-edge`, `microsoft-edge-stable`.
3. Linux: PATH의 `google-chrome`, `google-chrome-stable`, `chromium`, `chromium-browser` → `microsoft-edge`, `microsoft-edge-stable`.
4. Windows: `%ProgramFiles%`, `%ProgramFiles(x86)%`, `%LocalAppData%` 아래 Chrome·Chromium 고정 경로 → PATH의 `chrome`, `google-chrome`, `google-chrome-stable`, `chromium`, `chromium-browser` → Edge 고정 경로(`%ProgramFiles(x86)%`, `%ProgramFiles%`, `%LocalAppData%` 순) → PATH의 `msedge`.

### 1.4 행동 규칙과 남은 질문 [필수]

**공통: CLI·provenance**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `check`의 인자 | 1.3 CLI 표대로: 옵션은 `--json`, `--require-provenance`뿐, 위치 인자 정확히 1개. 위반하면 stderr에 메시지·종료 코드 2. `browser-check`는 같은 위반에 종료 코드 1 | 실행 확인 (T-15) |
| R-02 | provenance 대조 순서(`check`·`browser-check` 공통). 1) `<stem>.delivery-pending.json`(및 호환 이름)이 있다 → `delivery/provenance-failed`(status `failed`, `evidence.pendingJournal`). 2) delivery 잠금 파일이 있다 → `delivery/provenance-locked`(status `locked`). 3) sidecar 후보(기본 이름, raw-head 이름, 확장자 호환 이름 순)가 하나도 없다 → `--require-provenance`가 없으면 통과(status `unknown`), 있으면 `delivery/provenance-required`(`evidence:{required:true, found:false}`). 4) sidecar를 안정한 일반 파일(하드링크 1개)로 못 읽거나 JSON·스키마(1.3)가 어긋난다 → `delivery/provenance-invalid`(하드링크는 `delivery/provenance-hardlink-unsupported`). 5) sidecar의 `output`이 검사 중인 HTML과 같은 파일인지 판정할 수 없다 → `delivery/provenance-output-indeterminate`, 같은 파일이 아니다 → `delivery/provenance-invalid`(사유 "recorded delivery output does not identify this artifact"). 6) sidecar `status:'failed'` → `delivery/provenance-failed`(`evidence:{stage, deliveryReceiptId}`). 7) HTML의 SHA-256 또는 바이트 수가 `artifact`와 다르다 → `delivery/provenance-mismatch`(`evidence:{expectedSha256, actualSha256, expectedBytes, actualBytes}`). 8) 모두 같다 → status `current` | 앞 단계에서 걸리면 이후는 보지 않는다. 앞의 HTML 자체 읽기: HTML이 안정한 일반 파일이 아니거나 읽을 수 없다 → `input/artifact-unreadable`, 하드링크 → `output/target-hardlinked`. 검사 도중 HTML 바인딩이 바뀌면 `delivery/provenance-mismatch`(사유 "changed while ... inspected") | 코드 확인 전체. 1)·2)·4)~6)의 분기는 실행하지 않음. 3), 7), `input/artifact-unreadable`은 실행 확인 (T-02, T-04, T-18) |
| R-03 | 대조가 실패(위 어느 code든) | 이 게이트는 아래 정적/브라우저 단계로 가지 않는다. 종료 코드 1. `check`는 stdout에 provenance 실패 영수증(1.3)을 낸다. sidecar가 있으면 `--require-provenance` 없이도 검증한다(없을 때만 플래그가 의미를 가진다) | 실행 확인 (T-02, T-04) |
| R-04 | `check`가 대조를 통과 | 스크립트를 `child_process.spawnSync`(stdout pipe, 버퍼 상한 기본 64MiB, 환경변수 `ARCHIFY_CHECK_MAX_BUFFER`로 변경)로 실행한다. 버퍼 초과로 중단되면 판정 없이 `artifact/check-output-limit` 진단과 종료 코드 1. 자식이 JSON이 아닌 stdout을 내면 그대로 출력한다. JSON이면: provenance `current`인데 `(type==='explainer') !== (receipt.family==='explainer')`이면 `ok=false`와 진단 `delivery/artifact-family-mismatch`를 덧붙이고 종료 코드 1. 그다음 sidecar·HTML이 도중에 바뀌지 않았는지 다시 확인해 바뀌었으면 `delivery/provenance-mismatch` 실패 영수증과 종료 코드 1. 통과하면 `provenance`, `deliveryReceiptId`를 덧붙여 출력. 종료 코드는 자식의 코드(0/1). 자식의 stderr는 그대로 전달 | 코드 확인. 정상 경로만 실행 확인 (T-01) |
| R-06 | HTML이 explainer(`data-archify-artifact="explainer"` 또는 `archify-explainer-prepared` 스크립트) | 스크립트가 아래 R-05~R-20을 건너뛰고 `explainer/check.mjs`의 `checkExplainerHtml` 결과를 출력(`ok`면 0, 아니면 1). `browser-check`도 explainer는 `EXPLAINER_VIEWPORTS`와 explainer 판정을 쓴다 | 코드 확인 (내용은 범위 밖) |

**정적 검사 (`check-render-output.mjs`)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-05 | 검사 목록과 순서 | `<svg ...>...</svg>`가 정확히 하나일 때: `single_svg`, `finite_svg`, `orthogonal_arrows`, `label_route_clearance`, `relationship_crossings`, `relationship_corridors`, `container_border_runs`, `route_rhythm`, `legend_clearance` 순으로 9개, 그 뒤 경로 분석 오류가 있으면 `svg_path_data` 1개 추가(항상 실패). 하나가 아니면(0개 또는 2개 이상) `single_svg`(실패, 상세 `found N <svg> block(s)`)만 나온다. 검사 `details[]`가 빈 배열이면 해당 검사는 `ok`. 타입에 따라 검사 개수가 달라지지 않는다(10개 타입 예제 모두 9개) | 실행 확인 (T-01, T-11, `05-all-types`) |
| R-07 | `finite_svg` | `<svg>` 안 숫자형 속성(`NUMERIC_ATTRS` 목록과 `fecolormatrix values`, `fepointlight z`, `fespotlight z`) 값에 단어 `NaN`·`undefined`·`Infinity`(숫자 문자참조 `&#78;` 등은 먼저 디코드)가 있으면 실패, 상세는 `<태그> <속성>="<값>"`. `foreignObject`, `desc`, `title` 안쪽과 비숫자 속성(`data-*`, `aria-label` 등)은 보지 않는다. 항상 오류(profile 무관) | 코드 확인 + 실행 확인 (T-10) |
| R-08 | 어떤 경로가 "관계 화살표"인가 | `<!-- Legend -->` 앞 SVG 조각에서 `<path>`·`<line>` 중 `class`에 `a-default`·`a-emphasis`·`a-security`·`a-dashed`가 있고 `marker-end` 속성이 있는 것. `data-edge-from`·`data-edge-to`(또는 `data-composition-edge-from/to`)가 없는 화살표는 직각 검사와 범례 검사만 받고 나머지 관계 검사(교차·회랑·테두리·리듬·라벨)에서는 제외. 경로 `d`는 `M L H V Q Z`(대소문자)만 지원: 그 밖의 명령은 `artifact/svg-path-unsupported`, 문법 오류는 `artifact/svg-path-malformed`(둘 다 `svg_path_data` 실패와 `diagnostics[]`, 항상 오류). `Q`는 8등분 표본 선분이 `segments`(교차·범례용)에 들어가고, 제어점이 시작·끝과 일직선(외적 ≤1e-9)일 때만 `straightSegments`(직각·테두리·리듬용)에도 들어간다 | 코드 확인 |
| R-09 | `orthogonal_arrows` | 화살표의 직선 구간(`straightSegments`) 중 `|Δx|>0.01` 그리고 `|Δy|>0.01`인 것이 하나라도 있으면 실패(허용 개수 0, 허용 오차 0.01 SVG 단위). 예외: `data-composition-route="straight"`이고 `data-edge-from`·`-to`가 있으며 선분이 1개이고 `<line>`이거나 `d`가 정확히 `M x y L x y` 형식(공백만 허용)인 직접 직선. 곡선(`Q` 비직선)은 대상 아님. 항상 오류(profile 무관) | 코드 확인 + 실행 확인 (T-05) |
| R-10 | `relationship_crossings` / `composition/proper-crossing` | 서로 다른 두 관계(`data-edge-from/to` 있음)의 선분 쌍이 엄격하게 교차(양 선분에서 서로 반대 부호, 부호 판정 임계 1e-9. 끝점 접촉·T자는 교차 아님)하면 교차 1건(쌍당 1건). 기본은 `segments`를 쓰고 `data-layout-contract="readable-v2"`이면 화면에 보이는 경로의 직진 병합 선분을 쓴다. 끝점(노드)을 공유하는 쌍은 제외하되, 예외로 포함: readable-v2이거나, 양쪽이 `independentPorts`(halo 검증 통과 + `data-composition-independent="true"`)이거나, 양쪽이 `data-composition-routing="workflow-v2-auto"`. 이 속성들을 만드는 타입은 한정돼 있다: halo(`data-composition-crossover="halo"` + 밑선)는 architecture·dataflow·lifecycle의 자동 라우트만, `data-composition-independent`는 architecture(`labelAt`이 없을 때)·lifecycle만(dataflow는 halo만 있고 독립 포트 표지가 없다), `workflow-v2-auto`와 `readable-v2`는 workflow v2만([rendering-contracts.md](rendering-contracts.md) R-08, D-07). 나머지 타입은 끝점 공유 쌍이 항상 제외된다. 양쪽 모두 halo 검증(아래)을 통과하면 오류가 아니라 `metrics.resolvedCrossovers`와 `routeReview.crossings`로만 기록. 허용 개수: showcase 0건, 그 외 profile은 경고만. halo 검증: `data-composition-crossover="halo"`, 바로 앞 형제(사이에 공백만)가 `data-graph-role="automatic-crossover-underlay"` 경로이고 `d` 동일·`fill="none"`·`stroke="var(--mask)"`·`pointer-events="none"`·underlay `stroke-width ≥ 경로 stroke-width + 3` | 코드 확인 + 실행 확인 (T-06) |
| R-11 | `relationship_corridors` = `composition/ambiguous-corridor` + `composition/arrowhead-collision` | (a) 두 관계의 축 평행 선분이 같은 축 위(허용 오차 1e-4)에서 겹친 길이가 8px 이상(`overlap+1e-4 < 8`이면 제외)이면 쌍당 가장 긴 1건. 끝점 공유 쌍은 `includeSharedEndpoints`(readable-v2, 또는 양쪽 independentPorts)일 때만 대상이고, 아니어도 양쪽이 `workflow-v2-auto`이며 진행 방향이 반대(내적<0)면 대상. 같은 `data-composition-junction` 값을 가진 쌍은 수평 겹침·같은 도착 노드·공유 출발 첫 선분이면 면제. readable-v2는 겹침 24px 이하·variant·stroke-width·role 같음·같은 방향으로 출발/도착 끝점이 일치하는 짧은 trunk를 면제. (b) 화살촉 충돌: readable-v2이거나 `independentPorts`인 관계의 마지막 구간만. 같은 도착 노드·같은 축·같은 방향에서 끝점 좌표가 교차 축으로 일치(1e-4)하고 축 방향 거리가 `반폭(좌)+반폭(우) − 1e-4` 미만이면 충돌. 반폭 = 3.5 × (stroke-width 또는 기본 1.5, emphasis는 1.8). 같은 junction의 병합 도착은 면제. 허용: showcase 0건, 그 외 경고 | 코드 확인. 경계값 실행 없음. `independentPorts`·halo를 만드는 타입 한정은 rendering-contracts R-08(코드 확인) |
| R-12 | `container_border_runs` / `composition/container-border-run` | 관계의 직선 구간이 프레임 테두리와 같은 직선 위에서 겹친 길이(1e-4 초과)가 있으면 프레임·변마다 1건(겹친 구간 병합, 길이 합 `overlapLength`). 프레임 = `data-composition-frame-kind`가 있는 `rect`(변은 모서리 반지름 `rx`만큼 안쪽으로 줄임)·`path`·`line`. 허용 길이 0. 이 검사만 profile이 아니라 `data-quality-gates`로 갈린다: 속성이 `advisory`가 아니면 오류, `advisory`면 경고 | 코드 확인 |
| R-13 | `route_rhythm` / `composition/micro-segment`, `composition/short-interior-segment` | 관계 경로(직진 병합 정규화 후)의 선분 길이는 맨해튼 길이 `|dx|+|dy|`. 길이 > 1e-4인 선분 중 8 미만(`length < 8 − 1e-4`)이면 위치 무관 `micro-segment`, 8 이상 16 미만이고 첫·마지막 선분(스텁)이 아닌 **중간** 선분이면 `short-interior-segment`. 시작·끝 스텁은 8 이상이면 짧아도 허용. 허용 0건. showcase 오류, 그 외 경고 | 코드 확인 |
| R-14 | `label_route_clearance` / `composition/label-route-clearance` | 라벨 = `data-edge-key|id|from`이 있는 `<g>` 안의 `class`에 `c-mask`가 있는 첫 `<rect>`(소유 관계는 key → 포함 관계 → id+from+to 순으로 찾음, 못 찾으면 무시). 라벨 사각형과 **다른** 관계 경로 선분의 최소 거리(교차하면 0, 같은 관계는 제외)가 임계 미만(`거리 + 1e-4 < 임계`)이면 라벨·관계 쌍마다 1건(가장 가까운 선분). 임계: `data-quality-profile="showcase"`이면 4px, 그 외(속성 없음 포함) 2px. 프로파일은 SVG 루트 속성만 본다(R-19). 경계는 정확히 임계값이면 통과. 오류는 showcase만, 아니면 경고 | 코드 확인 + 실행 확인 (T-07) |
| R-15 | `composition/label-canvas-containment` (이름 있는 검사 없음, `composition.issues`와 `composition.status`로만 반영) | 라벨 사각형이 `viewBox`(최소 x·y 원점 포함)를 0.5px 초과해 벗어나면 변마다 `overflowPx`를 적어 1건. showcase 오류, 그 외 경고. 음수 크기 사각형은 무시 | 코드 확인 |
| R-16 | `legend_clearance` | SVG 안 `<!-- Legend -->` 주석 이후 조각의 모든 `<rect>`와 `<text>` 상자(2px 패딩)에 모든 화살표의 `segments`가 닿으면(끝점이 안에 있거나 변과 교차) 1건. 글자 상자: 폭 = `max(글자크기, textUnits(문자열)×글자크기×0.62)`, `text-anchor`로 정렬, 위 = `y − 글자크기`, 아래 = `y + 0.25×글자크기`, 글자 크기 기본 10. 주석이 없으면 통과(상세 `no legend marker found`). 항상 오류(profile 무관) | 코드 확인 |
| R-17 | `composition/desktop-readability` (이름 있는 검사 없음) | 의미 있는 글자(`data-node-label`, `data-boundary-label`, `data-detail="context"` 소유자가 있는 글, 단 `data-detail="fine"` 제외)의 `font-size`를 모아 **투영 글자 크기 = font-size × min(1, 가용폭 / viewBox 너비)**를 구하고, 최소값이 6(`MIN_PROJECTED_NODE_TEXT_PX`) 미만이면 최소 글자 1건. 가용폭 = 기본 930(=960−30, `legacy-930`). 단 `<meta name="archify-reader-contract" content="declared-wide-v1">`가 정확히 1개이고 SVG가 `data-reader-fit`=`intrinsic-height`/`width-first`, `data-reader-min-text`>0, 의미 글자 ≥1, font-size 파싱 가능, viewBox 가로/세로 비 ≥ 1.55이면 `declared-wide` 예산: `목표 = max(6, min-text)`, `요구배율 = min(1, 목표/최소 글자)`, `희망폭 = max(960, viewBox너비×요구배율 + 30)`, `뷰포트상한 = 1440−64 = 1376`, `실폭 = min(희망폭, min(1920, 뷰포트상한))`, `가용폭 = 실폭 − 30`. font-size가 숫자가 아니거나 ≤0인 의미 글자가 있으면 declared 예산은 쓰지 않는다. 이슈는 가장 작은 글자 하나. 오류는 showcase만, 아니면 경고. 이 계산은 1440×900 한 가지 가정이고 **브라우저 판정(R-30)과 다른 계산**이다 | 코드 확인 + 실행 확인 (legacy-930 경로, T-08, T-09). declared-wide 경로는 코드 확인만 |
| R-18 | `composition/viewport-height` (이름 있는 검사 없음) | 예측: `data-reader-fit`이 `intrinsic-height`/`width-first`가 아니고, `authored-height`+`architecture`도 아니고, viewBox 비 < 1.55일 때, SVG 높이 = `round((1440−64−30) × vBH/vBW)`, 쪽 높이 = 그 값 + 126(12+39+75)이 900을 넘으면 1건(`overflowPx = 쪽높이 − 900`). 오류 승격은 코드에서 `false`로 고정이라 **항상 경고**. 브라우저 게이트가 같은 입력에서 실패한다는 예고 | 코드 확인 + 실행 확인 (T-13) |
| R-19 | 오류·경고와 profile | `profile` = `<svg data-quality-profile>`(없으면 `standard`). **루트 속성만 보고 환경 변수 `ARCHIFY_QUALITY_PROFILE`·`meta.quality_profile`은 보지 않는다.** 렌더러가 `--quality`만으로 루트를 showcase로 만들었지만 본문은 standard 경로인 산출물(architecture·sequence는 본문이 `meta.quality_profile`만 본다)도 이 검사는 showcase 기준으로 판정하므로, 렌더러 본문 게이트와의 불일치를 이 검사가 잡지 못한다([rendering-contracts.md](rendering-contracts.md) R-03, [rendering.md](rendering.md) 1.3 I). 오류 수 = containerBorderRuns(`data-quality-gates≠advisory`일 때) + (showcase일 때) 교차 + 회랑·화살촉 + 라벨 여유 + 라벨 캔버스 + 리듬 + 데스크톱 가독성(있으면 1). `composition.status`는 오류 수>0이면 `fail`. 이름 있는 검사는 showcase에서만 `ok:false`가 될 수 있다(`single_svg`·`finite_svg`·`orthogonal_arrows`·`legend_clearance`·`svg_path_data`는 profile 무관). 같은 위반이 standard에서는 `composition.issues`에 `severity:'warning'`으로만 남고 `ok:true`·종료 코드 0 | 실행 확인 (T-06) |
| R-20 | 타입별 차이 | 임계값·검사 목록은 타입(`data-diagram-type`)으로 갈리지 않는다. 입력 SVG의 속성이 동작을 바꾼다: `data-quality-profile`, `data-quality-gates`, `data-layout-contract="readable-v2"`, `data-composition-*`, `data-reader-fit`, `data-reader-min-text`, `data-diagram-type`(**architecture + 저자 `meta.viewBox`일 때만** 렌더러가 쓴다. R-18의 architecture 예외와 R-21 `crowdedSides` 증거용이고, 자동 viewBox인 architecture는 이 속성이 없는 대신 `data-reader-primary-text="14"`가 같은 증거 역할을 한다), 메타 `archify-reader-contract`. `data-edge-role`(workflow v2만 쓴다)은 검사가 읽어 객체에 담지만 판정·증거에 쓰이지 않는다. 화살표(`a-*` + `marker-end`)가 없는 타입(트리·타임라인 등)은 관계 검사가 모두 빈 입력으로 통과 | 코드 확인 + 실행 확인 (`05-all-types`: 10개 타입 모두 9개 검사). 훅을 쓰는 타입은 [rendering-contracts.md](rendering-contracts.md) 1.3 A·D-06 |
| R-21 | 판정에 영향 없는 증거 | `composition.metrics`(`maxBends`, `routesOverSuggestedBends`(굽힘 2 초과), `maxStretch`·`routesOverSuggestedStretch`(비율 1.35 초과), `minSegmentPx`, `shortSegmentCount`(16 미만), `microSegmentCount`(8 미만) 등), `suggestedLimits {bendsPerRelationship:2, stretch:1.35, segmentPx:16, microSegmentPx:8}`, `routeReview`(해소된 교차, 우회 경로, `crowdedSides`: architecture 또는 `data-reader-primary-text="14"`에서 한 변이 향하는 관계 수 n>1일 때 변 길이 < `32+14(n−1)`), `leadingSpace`(위쪽 빈 공간 > 2×중앙 노드 높이 and 비율 > 0.2면 `reviewSuggested`), `sequenceColumnSpace`(R-38), `sequenceNoteBorders`는 오류·경고 개수에 들어가지 않는다. 노드 겹침 검사는 `check`에 없다 | 코드 확인 + 실행 확인 (T-12) |
| R-38 | `composition.sequenceColumnSpace`와 `finalize`의 `inspect-sequence-width` 권고 | `check`가 SVG 루트 `data-sequence-column-fit`이 `fixed`·`spread`일 때 `sequenceColumnSpace`를 만든다. 측정 불가(루트·요소 `transform`, 노드 수와 노드 사각형 수 불일치, 관계 경로 없는 의미 화살표, `dx` 있는 글자, 비유한 값)면 `{measured:false, reviewSuggested:false, columnFit}`. 측정하면 `occupiedRight` = 노드 오른쪽 끝·관계 경로 점 x·`c-mask` 라벨판 오른쪽 끝·글자 상자 오른쪽 끝의 최댓값, `emptyRightPx = max(0, viewBox 왼쪽+폭 − occupiedRight)`, `emptyRightRatio = emptyRightPx/viewBox 폭`, `typicalParticipantWidth` = 노드 폭을 정렬한 `[floor(n/2)]`번째 값. **`reviewSuggested` = `columnFit==='fixed'` ∧ 참가자 4명 이상 ∧ `emptyRightPx > 2×typicalParticipantWidth` ∧ `emptyRightRatio > 0.25`**. `spread`는 항상 false. 오류·경고가 아니고 `ok`·종료 코드에 영향이 없다. `finalize`는 영수증이 `ok`이고 `type==='sequence'`이며 `reviewSuggested`일 때 영수증에 `layoutReviewRecommendation{action:"inspect-sequence-width", evidence, reason, repair}`를 싣는다. 렌더러는 이 권고를 만들지 않는다 | 코드 확인(`check-render-output.mjs:958-1033` `collectSequenceColumnSpace`, `bin/finalize.mjs:700-709`) / 실행 확인(5명 fixed 사례: `emptyRightPx 383`, `ratio 0.416`, `typicalParticipantWidth 86`, `reviewSuggested:true`, spread 같은 입력은 권고 없음. [rendering-other-types.md](rendering-other-types.md) T-17, R-29) |

**브라우저 게이트 (`browser-check`)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-22 | 확장자 | HTML이 아니면(`.html`/`.htm` 아님) 실행 오류(`viewer/browser-check-input`)로 종료 코드 1 | 코드 확인 |
| R-23 | `--out-dir` | 1.3대로. 영수증만 이 폴더에 쓴다. 폴더가 새로 생길 수 있다 | 실행 확인 (T-14, T-16) |
| R-24 | provenance (`browser-check`) | R-02의 대조를 Chrome보다 먼저 한다. 실패하면 Chrome을 부르지 않고 `{schemaVersion:1, ok:false, command, evidenceKind, status:'fail', visualReview:'not-requested', provenance, [deliveryReceiptId], artifact:{path,[sha256,bytes]}, error, diagnostics[], containment:{status:'fail',...}, captures:{status:'not-requested',...}, sidecars}` 영수증을 파일로 남기고 종료 코드 1. 측정 전·후에 HTML 바이트와 sidecar를 다시 확인해, 바뀌었으면 같은 code(`delivery/provenance-mismatch`)로 실패. `finalize`는 이 함수를 `requireProvenance: true`로 부른다 | 실행 확인 (T-03), 재확인 경로는 코드 확인 |
| R-25 | Chrome 탐색 | 1.3 순서. `chromePath` 옵션이 주어지면 탐색을 건너뜀(finalize 내부 용도) | 코드 확인. macOS의 Chrome 발견은 실행 확인 |
| R-26 | Chrome 없음 | `status:'skipped'`, `ok:false`, 모든 하위 판정 `skipped`, 진단 `viewer/chrome-unavailable`(`severity:'warning'`), `error`="No supported browser found. Install Chrome/Chromium (or Microsoft Edge), or set ARCHIFY_CHROME to its executable path.". 영수증은 쓴다. 종료 코드 **2**. 유효하지 않은 `ARCHIFY_CHROME` 값도 같다 | 실행 확인 (T-14) |
| R-27 | Chrome 실행 | `--headless=new --remote-debugging-pipe --disable-gpu --hide-scrollbars --disable-background-networking --disable-component-update --disable-default-apps --disable-sync --metrics-recording-only --no-first-run --no-default-browser-check --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-renderer-backgrounding --force-device-scale-factor=1 --user-data-dir=<임시 프로필> about:blank`. root 사용자이거나 `ARCHIFY_CHROME_NO_SANDBOX=1`이면 `--no-sandbox` 추가. stdio는 `[ignore, ignore, pipe(stderr), pipe(fd3: Chrome으로 쓰기), pipe(fd4: Chrome에서 읽기)]`, 메시지는 JSON + NUL 구분. 첫 `Target.getTargets` 대기는 90000ms(`viewer/chrome-startup-timeout`), 이후 CDP 요청 기본 15000ms, `Page.loadEventFired` 대기 15000ms, 스크린샷 20000ms, 초과하면 `ERR_CHROME_CDP_TIMEOUT`. 종료는 SIGTERM 후 1500ms 안에 안 죽으면 SIGKILL(또 1500ms), 그래도 안 죽으면 `viewer/temp-cleanup-incomplete`. 브라우저 인스턴스 1개를 모든 뷰포트에 재사용하고 뷰포트마다 `Emulation.setDeviceMetricsOverride{width,height,deviceScaleFactor:1,mobile:false}` 후 `file://<임시 HTML 사본>?theme=<light|dark>`로 이동한다. Chrome이 여는 파일은 원본 경로가 아니라 `os.tmpdir()/archify-inspection-*/artifact-snapshot.html` 사본이다(바이트 동일 확인) | 코드 확인. 실제 실행은 실행 확인 (T-01) |
| R-28 | 측정 절차 | 순서: 라이트 4개(1440×900, 1600×1000, 1920×1080, 2048×1320) → 다크 2개(1440×900, 2048×1320, 즉 라이트 목록의 처음·끝). 매 뷰포트에서 로드 후 `<html data-motion="still">`, `.diagram-container[data-detail-level="read"]`로 설정하고, 글꼴 준비 후 `Archify.layoutStability.whenStable()`(없으면 `readerLayout`·`viewerChromeLayout`의 `whenStable` 체인, 그것도 없으면 `requestAnimationFrame` 두 번)을 기다린 다음 측정 스크립트를 실행한다. 측정이 `scrollWidth/scrollHeight`를 숫자로 못 주면 실행 오류 | 코드 확인 + 실행 확인 (T-01) |
| R-29 | 넘침(containment) 판정(뷰포트 6개 각각) | `overflowX = scrollWidth > innerWidth`, `overflowY = scrollHeight > innerHeight`. `scrollWidth = ceil(documentElement.scrollWidth)`, `scrollHeight = max(innerHeight, ceil(documentElement.scrollHeight − (html[data-reader-rail="bottom"]이면 .reader-rail 높이)))`. 세로 스크롤 허용(`verticalScrollAccepted`)은 `overflowY && !overflowX && 글자 하한 통과 && 최소 글자 수치 유한`이고 둘 중 하나: (a) `data-reader-layout="adaptive"` and `data-reader-overflow="authored"` and `svg[data-reader-fit]`이 `intrinsic-height`/`width-first`, (b) `svg[data-reader-fit]="authored-height"` and `svg[data-diagram-type]="architecture"` and `documentScrollUnclipped`. `authoredClipped` = (b)의 선언이 있는데 `documentScrollUnclipped`가 아님. `ok = !authoredClipped && !overflowX && (!overflowY || verticalScrollAccepted)`. 실패 진단: `viewer/diagram-clipped`(authoredClipped), 아니면 `viewer/viewport-overflow`(증거: 넘침 수치·`pageComposition`·`supportedFixes`에 줄일 SVG·viewBox 높이 계산). 가로 넘침은 어떤 경우에도 실패 | 코드 확인 + 실행 확인 (T-13: 세로 넘침 실패, T-01: contained) |
| R-30 | 글자 하한 판정 | 측정 대상: SVG 안 `text[data-node-label], text[data-boundary-label], text[data-detail="context"], g[data-detail="context"] text`. `data-detail="fine"`(자신·조상)은 제외. 소유 판별: 엣지(`[data-edge-from][data-edge-to]` 조상) 안이면 `edge`, 노드 조상이면 `node`, `data-node-label`이면 `primary`, `data-boundary-label`이면 `boundary`. 엣지·노드 소유자가 없는 context 글은 제외. `font-size` 속성이 숫자가 아니면 제외. **투영 글자 크기 = font-size × min(1, svg.getBoundingClientRect().width / viewBox.width)**(실제 렌더 폭 사용, 정적 검사의 930이 아님). 전체 최소값(엣지 라벨 포함)이 6 미만이면 그 뷰포트의 `readabilityOk=false`(6이면 통과, 대상 글이 없으면 통과). `readability.status`는 **라이트 4개 뷰포트**의 `readabilityOk`만 본다(다크 2개는 containment에만 영향이 없고 readability에는 들어가지 않는다). 실패 진단 `viewer/projected-text-readability`는 라이트 뷰포트마다 1건. 세로 스크롤 허용 판정에도 이 하한이 들어간다(R-29) | 코드 확인 + 실행 확인 (T-09: 5.9 실패, 6 통과) |
| R-31 | 뷰어 UI 간섭(`viewerChrome`) | `legendDockIntersectionArea ≤ 0.5` 이어야 하고, 내비게이션 Dock이 있으면 `dockStageGap`이 유한하고 `dockStageIntersectionArea ≤ 0.5` 이며 `dockStageGap ≥ 요구 간격 − 1`(요구 간격 = 뷰어가 보고한 `viewerChromeRequiredGap`, 없으면 0). 실패 진단: `viewer/chrome-legend-clearance`, `viewer/chrome-stage-clearance`. 뷰포트 6개 모두 대상 | 코드 확인 |
| R-32 | 테마 | `html[data-theme]`가 요청한 테마(light/dark)와 같아야 한다. 아니면 `viewer/theme-state`(요청·실제 테마 증거). 뷰포트 6개 모두 대상 | 코드 확인 |
| R-33 | 총 판정·종료 코드 | `ok = containment && themeStates && readability && viewerChrome`(모두 pass). `status`는 pass/fail. 종료 코드 pass 0, fail 1, skipped 2. 영수증 게시(원자 교체)가 실패하면 판정이 통과여도 `fail`·종료 코드 1이고 `viewer/evidence-write` 등 진단이 붙는다 | 실행 확인 (T-01, T-13, T-14) |
| R-34 | 영수증 쓰기 | 통과·실패·skipped 모두 `<stem>.browser-check.json`을 쓴다(원자 교체; 임시 `.archify-visual-check-*` 폴더를 거침). 사용자 확인 없이 스크린샷·contact sheet는 만들지 않는다(browser-check는 `captures.status:'not-requested'`) | 실행 확인 (T-01) |
| R-35 | 기존 영수증과의 소유권 | 같은 경로에 영수증이 이미 있으면 그 파일이 이 명령이 만든 것이고 **그 영수증이 기록한 `artifact.sha256·bytes`가 지금 HTML 바이트와 같아야** 덮어쓴다. 다르면 `viewer/evidence-path-conflict`(`evidence.reason.code:'ownership-artifact-mismatch'` 등 `ownership-*`)와 종료 코드 1로 실패하고 기존 파일은 그대로다. 해결: 파일을 치우거나 다른 `--out-dir`. 즉 HTML을 바꿔 다시 전달한 뒤 같은 경로로 `browser-check`를 다시 돌리면 새 영수증이 막힌다. 같은 바이트로 다시 돌리는 것은 문제 없음 | 실행 확인 (T-16). 기록 파일 이름 불일치 등 다른 `ownership-*` 사유는 코드 확인 |
| R-36 | 런타임 오류 | Chrome 실행·CDP·측정 중 예외는 `skipped`로 바꾸지 않고 `fail`(종료 코드 1): `viewer/browser-check-runtime`(startup 타임아웃은 `viewer/chrome-startup-timeout`, 정리 실패는 `viewer/temp-cleanup-incomplete`). 입력 읽기·영수증 폴더 준비 실패는 `viewer/browser-check-input`, 임시 사본 실패는 `viewer/artifact-snapshot`, 영수증 폴더 정체 불명은 `viewer/sidecar-directory-identity` | 코드 확인 |
| R-37 | capture(스크린샷) 옵션 | `browser-check`에는 없다. `visual-check`만: 라이트·다크 × (1440×900, 2048×1320) PNG 4장(`...visual-check.<W>x<H>.<theme>.png`)과 `.visual-check.html`을 `--out-dir`/HTML 폴더에 쓰고 영수증 `visualReview:'pending'`. 판정 규칙은 browser-check와 같다 | 실행 확인 (T-17) |

- 불변식: provenance 불일치는 항상 브라우저·정적 검사 전에 실패한다. `check`와 `browser-check`는 대상 HTML과 sidecar를 수정하지 않는다. 같은 HTML 바이트·같은 sidecar·같은 Chrome이면 판정 입력은 같다(정적 검사는 결정적, 브라우저 측정은 렌더 환경 의존).
- 미결정: 없음(이 스펙 범위의 임계값은 모두 읽음). 선행 `delivery.md`가 아직 없어 `status: draft`.
- 확인 한계: ① 뷰어 JS(`Archify.layoutStability` 등)와 `html[data-theme]`를 정하는 뷰어 코드는 읽지 않았다(측정 입력의 출처). `data-reader-*`·`data-composition-*`를 렌더러가 타입별로 쓰는 조건은 [rendering-contracts.md](rendering-contracts.md) 1.3 A가 읽었다. ② R-02의 pending·lock·hardlink·invalid·output-indeterminate 분기와 R-17의 declared-wide 예산, R-31의 Dock 판정은 읽기만 하고 실행하지 못했다(실패를 만드는 입력을 만들지 못함). ③ Windows·Linux의 Chrome 탐색은 코드만 읽었다.

### 1.5 필수 코드 참조 [필수]
<!-- 라이선스(Apache-2.0)상 인용 가능. 아래는 위치만. -->

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `archify/renderers/shared/desktop-readability.mjs:1-132` | 상수(6, 960, 30, 1.55, 1920, 64), `projectedNodeTextPx`, `declaredWideReadabilityBudget`, `DESKTOP_FIXED_VERTICAL_CHROME_PX`, `predictedFixedWidthOverflow` | R-17, R-18, R-30 |
| C-02 | `archify/scripts/check-render-output.mjs:21-52,111-452` | 인자·종료 코드, 검사 순서, profile별 오류/경고 계산, `ok` 식 | R-05, R-19 |
| C-03 | `check-render-output.mjs:454-537` `collectArrows` | 관계 화살표 선택 조건, `authoredStraight`, halo 검증, `independentPorts` | R-08, R-09, R-10 |
| C-04 | `check-render-output.mjs:737-767,1325-1345` | 교차 검출(끝점 공유 예외, `properSegmentIntersection`) | R-10 |
| C-05 | `archify/renderers/shared/geometry.mjs:730-860,1440-1458` | 회랑 겹침(8px), 짧은 trunk 면제, 화살촉 충돌, `collinearAxisOverlap` | R-11 |
| C-06 | `geometry.mjs:918-960,1397-1438` | 테두리 겹침, 프레임 변 계산(반지름), 구간 병합 | R-12 |
| C-07 | `geometry.mjs:1006-1105,1316-1320,1351-1395` | 경로 정규화, 예산 지표(16/8/2/1.35), 리듬 이슈(`composition/micro-segment`, `short-interior-segment`) | R-13, R-21 |
| C-08 | `geometry.mjs:62-100,206-270` | 라벨-경로 거리, `collectLabelRouteClearance`(임계 비교 `+0.0001 >= threshold`) | R-14 |
| C-09 | `geometry.mjs:1221-1262` | 라벨 캔버스 넘침(0.5px) | R-15 |
| C-10 | `check-render-output.mjs:1131-1193,1319-1323` | 범례 상자, 글자 상자·폭 추정, 충돌 판정 | R-16 |
| C-11 | `check-render-output.mjs:1210-1317` `collectDesktopReadability` | 의미 글자 수집·declared-wide 적격·증거 필드 | R-17 |
| C-12 | `check-render-output.mjs:1403-1430`, `91-109` | `finite_svg` 대상 속성 목록 | R-07 |
| C-13 | `archify/renderers/shared/svg-path-analysis.mjs:1-135` | 지원 명령 `M L H V Q Z`, 오류 code, `Q` 처리 | R-08 |
| C-14 | `archify/bin/archify.mjs:1904-2185` `inspectDeliveryProvenance`, `invalidProvenance` | provenance 판정 순서와 code | R-02 |
| C-15 | `archify.mjs:5420-5535` `inspectArtifactDeliveryProvenance`, `5537-5580` `verifyDeliveryUnchanged`·`provenanceFailureReceipt` | HTML 읽기 오류 code, 재확인, 실패 영수증 모양 | R-02~R-04, R-24 |
| C-16 | `archify.mjs:5581-5661` `commandCheck` | check 인자·실행·후처리 | R-01, R-04 |
| C-17 | `archify.mjs:5663-5836` `executeBrowserEvidence`, `commandBrowserEvidence` | browser-check 인자·출력 형식·종료 코드·실패 영수증 | R-01, R-23, R-24, R-33 |
| C-18 | `archify/bin/visual-check.mjs:37-59` | 뷰포트 4개, 캡처 2개, 테마, 종료 코드 `{pass:0, fail:1, skipped:2}`, 시작 타임아웃 90000 | R-27, R-28, R-33 |
| C-19 | `visual-check.mjs:1317-1402` `findChrome`, `1523-1550` `chromeVisualBrowserArgs` | 탐색 순서, Chrome 인자 | R-25, R-27 |
| C-20 | `visual-check.mjs:1659-1873` `inspect` | 상태 설정·대기·측정 스크립트(글자·넘침·Dock 지표) | R-28, R-30, R-31 |
| C-21 | `visual-check.mjs:1942-2032` `observation` | 넘침·세로 스크롤 허용·글자·Dock 판정 식 | R-29~R-31 |
| C-22 | `visual-check.mjs:2168-2277` `observationDiagnostics` | 진단 code와 증거 | R-29~R-32 |
| C-23 | `visual-check.mjs:2279-2310`, `2444-2767` `baseReceipt`, `runBrowserEvidence` | 영수증 기본 모양, 실행·skipped·실패 경로, 총 판정 | R-24~R-26, R-33~R-36 |
| C-24 | `visual-check.mjs:193-236`, `613-812` | 영수증 파일 이름, 기존 영수증 소유권 검사 | R-34, R-35 |
| C-25 | `check-render-output.mjs:958-1033` `collectSequenceColumnSpace`, `archify/bin/finalize.mjs:700-709` | 측정 조건·`reviewSuggested` 식, `finalize` 권고 | R-38 |

### 1.6 수락 사례 [필수]
출처: 모두 **원본 실행 관찰**(설치본 `~/.claude/skills/archify`, 레포 `archify/`와 `diff -rq` 차이 없음 확인, 2026-11-02). 입력은 `archify/examples/*.json`을 DEMO `inputs/`에 복사한 것. 스크립트·출력은 DEMO 아래: [`01-baseline.sh`](../../../artifacts/archify/spec-demos/verification-gates/01-baseline.sh), [`02-tamper-check.py`](../../../artifacts/archify/spec-demos/verification-gates/02-tamper-check.py), [`03-label-clearance-boundary.py`](../../../artifacts/archify/spec-demos/verification-gates/03-label-clearance-boundary.py)(출력 `out/03-...out.txt`), [`04-provenance-and-browser.sh`](../../../artifacts/archify/spec-demos/verification-gates/04-provenance-and-browser.sh)(출력 `out/04-...out.txt`), [`05-all-types.sh`](../../../artifacts/archify/spec-demos/verification-gates/05-all-types.sh)(출력 `out/05-all-types.out.txt`), [`06-browser-extra.sh`](../../../artifacts/archify/spec-demos/verification-gates/06-browser-extra.sh)(출력 `out/06-...out.txt`). "아키텍처 샘플" = `brand-aware-delivery.architecture.json`을 `deliver architecture ... --json`한 HTML(857101바이트, viewBox 1120×640, `data-quality-profile="showcase"`, `data-reader-fit="authored-height"`).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-04, R-05, R-27, R-28, R-33, R-34 | 아키텍처 샘플을 deliver한 직후 `check <html> --require-provenance`, `browser-check <html> --json --require-provenance` | check: 종료 0, `ok:true`, `provenance:"current"`, `checks` 9개 이름 순서대로 모두 `ok:true`, `composition.summary {errors:0,warnings:0}`, `metrics.minProjectedNodeTextPx` 6.642857…(엣지 라벨 8 × 930/1120). browser-check: 종료 0, `status:"pass"`, `provenance:"current"`, 라이트 4개 뷰포트 `overflowDisposition:"contained"`, `themeStates.viewports` 6개(라이트 4+다크 2), `minimumProjectedNodeTextPx` 8, `captures.status:"not-requested"`, 영수증 `<stem>.browser-check.json` 생성 |
| T-02 | R-02, R-03 | T-01의 HTML 끝에 `\n` 1바이트 추가(857101→857102). `check <html> --require-provenance`, 그리고 플래그 없이 `check <html>` | 둘 다 종료 1, `ok:false`, `provenance:"mismatch"`, 진단 `delivery/provenance-mismatch`, `evidence.expectedBytes 857101`·`actualBytes 857102`와 두 sha256. 정적 `checks` 없음(스크립트 실행 안 함) |
| T-03 | R-24 | T-02와 같은 상태에서 `browser-check <html> --json --require-provenance` | 종료 1, `status:"fail"`, `provenance:"mismatch"`, 진단 `delivery/provenance-mismatch`, Chrome 미실행(`chrome` 필드 없음). `<stem>.browser-check.json` 실패 영수증이 HTML 옆에 생성 |
| T-04 | R-02, R-03 | HTML은 원본, `.delivery.json`을 치움. `check <html>`; `check <html> --require-provenance`; `browser-check <html> --json --require-provenance` | 첫째: 종료 0, `provenance:"unknown"`, 정적 검사 통과. 둘째·셋째: 종료 1, `delivery/provenance-required`(`evidence:{required:true,found:false}`) |
| T-05 | R-09 | 아키텍처 샘플에서 `brief-to-claude` 화살표(marker-end 경로)의 `d`를 `M 176 294 L 220 294`→`M 176 294 L 220 300`으로 바꾼 사본, 샘플 sidecar 없음, `check <사본>` | 종료 1, 실패한 검사는 `orthogonal_arrows` 하나(`details`: `path 1 segment 1: expected an orthogonal segment ...`), `composition.issues` 없음 |
| T-06 | R-10, R-14, R-19 | `github-to-container` 화살표를 `M 200 250 L 200 340`(수직선, 다른 관계 `brief-to-claude`의 라벨·경로를 가로지름)으로 바꾸고 halo 속성 제거한 사본. 같은 사본을 `data-quality-profile`만 `standard`로 바꿔 두 번 | showcase: 종료 1, 실패 검사 `label_route_clearance`(라벨 `brief` 0px < 4px), `relationship_crossings`(교차점 [200,294]), `composition.summary.errors:2`. standard: 종료 0, `ok:true`, 같은 두 code가 `severity:"warning"`, `summary {errors:0, warnings:2}` |
| T-07 | R-14 | 위 사본의 수직선 x를 라벨 사각형 오른쪽 끝(215)+간격으로 옮겨 간격 1.9/2/3.9/4/4.1px, profile 2종 (`03-...out.txt`) | `label-route-clearance` 이슈: showcase는 1.9·2·3.9에서 error(clearance 값, threshold 4), 4·4.1에서 없음. standard는 1.9에서 warning(threshold 2), 2 이상에서 없음. (교차 오류는 별개라 showcase 종료 코드는 모두 1) |
| T-08 | R-17, R-19 | 아키텍처 샘플에서 `Claude` 노드 라벨 `font-size`를 11→7.2 / 7.3으로 바꾼 사본, `check <사본>` | 7.2: 종료 1, `checks`는 전부 `ok:true`인데 `ok:false`, `composition.status:"fail"`, 이슈 `composition/desktop-readability`(severity error, `projectedFontPx` 5.979, `minimumProjectedFontPx` 6, `budgetBasis:"legacy-930"`). 7.3: 종료 0 |
| T-09 | R-17, R-30 | 노드 라벨 font-size 5.9 / 6 / 7.2 사본에 `check`와 `browser-check`(Chrome) 모두 실행 (`06-...out.txt`) | check: 5.9→투영 4.899, 6→4.982, 7.2→5.979 모두 실패(종료 1), 7.3→통과. browser-check: 5.9→종료 1, 라이트 4개 뷰포트마다 `viewer/projected-text-readability`(`detail:"primary"`, 5.9), `readability.status:"fail"`. 6→종료 0 통과, 7.2→종료 0 통과(렌더 폭 1306px ≥ viewBox 1120이라 배율 1) |
| T-10 | R-07 | 샘플의 `Claude` 노드 `rect`의 `x="220"`을 `x="NaN"`으로 바꾼 사본 | 종료 1, 실패 검사 `finite_svg`, `details`에 `rect x="NaN"` |
| T-11 | R-05 | 샘플 `</body>` 앞에 `<svg viewBox="0 0 1 1"></svg>` 추가 | 종료 1, `checks`에 `single_svg`(실패, `found 2 <svg> block(s)`)만 있고 나머지 검사 없음 |
| T-12 | R-21 | 샘플에서 `GitHub` 노드의 `rect` x를 402→250으로 옮겨 `Claude` 노드와 겹치게 한 사본 | 종료 0, `ok:true`. `check`는 노드 겹침을 보지 않는다(렌더러의 `layout/component-overlap` 소관) |
| T-13 | R-18, R-29 | `release-delivery.workflow.json`(workflow), `product-analytics.dataflow.json` 계열(`event-stream.dataflow.json`)을 deliver 후 `check`, `browser-check` | 둘 다 check 종료 0(`composition/viewport-height` 경고 1건, `summary {errors:0, warnings:1}`)인데 browser-check는 종료 1: workflow는 `viewer/viewport-overflow` 6건(라이트 4+다크 2, 1440×900에서 `scrollHeight 1967 > innerHeight 900`, `readerFit:null`, `overflowDisposition:"unexpected-overflow"`). 같은 위반이 `agent-tool-call.workflow.json`·다른 7개 타입에서는 없고 browser-check 통과 (`05-all-types.out.txt`) |
| T-14 | R-23, R-26 | `ARCHIFY_CHROME=/nonexistent/chrome browser-check <html> --json --out-dir <dir>` | 종료 2, `status:"skipped"`, `chrome:{status:"unavailable"}`, 진단 `viewer/chrome-unavailable`(severity warning), `<dir>/<stem>.browser-check.json` 생성 |
| T-15 | R-01 | `check`(인자 없음), `check a.html b.html`, `check x.html --bogus`, `browser-check x.html --bogus`, `browser-check`(인자 없음), `check x.html --json`(파일 없음) | 종료 코드 2, 2, 2, **1**, **1**, 1 |
| T-16 | R-35 | 같은 출력 경로로 deliver→browser-check(통과) 후 입력 제목을 바꿔 다시 deliver(HTML 바이트 변경)하고 `browser-check ... --require-provenance`; 같은 상태에서 `--out-dir`을 새 폴더로; `finalize` 두 번(입력 다르게, 같은 출력) | 첫 `browser-check`: 종료 1, 진단 `viewer/evidence-path-conflict`(`evidence.reason.code:"ownership-artifact-mismatch"`)이고 기존 영수증 유지. 새 `--out-dir`: 통과. `finalize` 두 번째: 종료 1, `failedStage:"browser-check"`, 같은 진단(게이트 `validate`·`deliver`·`check`는 pass) |
| T-17 | R-37 | `visual-check <html> --json --out-dir <dir>` | 종료 0, `<dir>`에 `<stem>.visual-check.json`, `.visual-check.html`, `.visual-check.1440x900.{light,dark}.png`, `.visual-check.2048x1320.{light,dark}.png` |
| T-18 | R-02 | 존재하지 않는 HTML 경로로 `check`, `browser-check --json` | check: 종료 1, `provenance:"unknown"`, `error`에 "Could not read the HTML artifact"(`input/artifact-unreadable`). browser-check: 종료 1, `input/artifact-unreadable`에 `viewer/evidence-path-conflict`(`artifact-unreadable`)가 덧붙음(영수증을 쓸 수 없음) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
문서와 구현의 차이는 아래 표 끝에 모았다. 경로는 모두 `archify/...` 기준 SHA `a406594`의 줄 번호.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-16 `archify.mjs:5581-5592`(`knownOptions`, `fail(usage())`), `archify.mjs:2227` `fail`(기본 코드 2), C-17 `:5747-5751`(`fail(..., 1)`) | 코드 읽기, T-15 실행 |
| R-02, R-03 | C-14, C-15. 판정 순서는 `archify.mjs:1904-2179`. `specification`은 `identityValid`로 형식만 검사(`:2048,2058`)하고 대조에 쓰이지 않음 | 코드 읽기. 3)·7)·읽기 오류는 T-02, T-04, T-18 실행 |
| R-04 | C-16. 버퍼 `archify.mjs:2257,2281-2288`, `checkerOutputLimitDiagnostics :2290` | 코드 읽기. 버퍼 초과·family 불일치는 실행하지 못함 |
| R-05 | C-02 `check-render-output.mjs:115-445`(`addCheck` 호출 순서). 타입별 검사 수는 `05-all-types` | 실행 (T-01, T-11, 10개 타입) |
| R-06 | `check-render-output.mjs:44-48`, `explainer/check.mjs`의 `isExplainerHtml`, `visual-check.mjs:2468-2471` | 이름·분기만 읽음. explainer 내용은 읽지 않음 |
| R-07 | C-12 | 코드 읽기, T-10 |
| R-08 | C-03, C-13 | 코드 읽기. 지원 명령 밖 경로(`A` 등)는 실행하지 않음 |
| R-09 | `check-render-output.mjs:139-144,1122-1129`, C-03 | 코드 읽기, T-05. 0.01은 코드 상수 |
| R-10 | C-04, C-03, `render-architecture.mjs:1066`, `render-lifecycle.mjs:1048`·`dataflow-compiler.mjs:1472`의 `data-composition-*` 쓰기 | 코드 읽기, T-06. halo 해소 경로는 실행 안 함. 속성을 쓰는 타입은 grep으로 확인(rendering-contracts R-08) |
| R-11 | C-05 | 코드 읽기. 8px·24px·3.5×폭 경계는 실행 안 함 |
| R-12 | C-06 | 코드 읽기. 실행 안 함 |
| R-13 | C-07 | 코드 읽기. 실행 안 함 |
| R-14 | C-08, `check-render-output.mjs:190-200,671-716` | 코드 읽기, T-07 경계 실행 |
| R-15 | C-09, `check-render-output.mjs:204-207` | 코드 읽기. 실행 안 함 |
| R-16 | C-10, `check-render-output.mjs:431-442` | 코드 읽기. 실행 안 함 |
| R-17 | C-01, C-11, `check-render-output.mjs:129-130` | 코드 읽기, T-08·T-09 실행. 가용폭 930은 `DESKTOP_READER_DIAGRAM_WIDTH`(960−30) |
| R-18 | C-01 `:88-132`, `check-render-output.mjs:132-137,215,382-390` | 코드 읽기, T-13 실행 |
| R-19 | `check-render-output.mjs:122-124,190,208-231,447` | 코드 읽기, T-06·T-08 |
| R-20 | `check-render-output.mjs:122-124,169,184-188,522`, 전체에서 `data-diagram-type`·`readerFit`·`data-edge-role` 참조 위치, `render-architecture.mjs:1143`(`data-diagram-type`을 쓰는 유일한 곳) | 코드 읽기 + 10개 타입 실행 |
| R-21 | `check-render-output.mjs:79,254-282,824-848,904-953,958-1033` | 코드 읽기 |
| R-38 | C-25, `check-render-output.mjs:188,281`(`composition`에 포함), `finalize.mjs:700-709` | 코드 확인 + 실행 확인은 rendering-other-types T-17(`finalize sequence`). 참가자 3명 이하·비율 0.25 이하 경계는 코드만 |
| R-22 | `visual-check.mjs:2457`(확장자), `archify.mjs:5693-5742`(`viewer/browser-check-input`) | 코드 읽기 |
| R-23 | `archify.mjs:2376-2394` `extractOutDirArgs`, `5755-5783` | 코드 읽기, T-14·T-16 |
| R-24 | C-15, C-17 `:5663-5742`, `finalize` 호출 `archify.mjs:5952-5954`, `visual-check.mjs:2535`(측정 전 재확인), `:2646`(측정 후 재확인) | 코드 읽기, T-03 실행 |
| R-25, R-26 | C-19, C-23 `visual-check.mjs:2545-2585` | 코드 읽기, T-14 실행 |
| R-27 | C-19, `visual-check.mjs:59,1469,1498,1576-1650,1880` | 코드 읽기. 타임아웃 초과 실행 안 함 |
| R-28 | C-18, C-20 `visual-check.mjs:1659-1700`, `2589-2640` | 코드 읽기, T-01 |
| R-29~R-32 | C-20, C-21, C-22 | 코드 읽기, T-01·T-09·T-13 실행. R-31·R-32 실패는 실행 안 함 |
| R-33 | C-18 `:49`, C-23 `visual-check.mjs:2640-2721` | 코드 읽기, T-01·T-13·T-14 |
| R-34 | C-24 `visual-check.mjs:193-236`, C-23 | 코드 읽기, T-01 |
| R-35 | C-24 `visual-check.mjs:613-812`(`ownership-artifact-mismatch`는 `:710-720`) | 코드 읽기, T-16 실행(`browser-check`·`finalize`) |
| R-36 | C-23 `visual-check.mjs:2723-2767` | 코드 읽기 |
| R-37 | `visual-check.mjs:44-58,2468-2470`, `archify.mjs:5744-5751` | T-17 실행 |
| T-01~T-18 | DEMO 스크립트·출력(1.6) | 실행 기록 |

**문서와 구현의 차이·확인 사항**
- 6px 하한: `delivery-contract.md:416-490` 문서는 숫자를 직접 쓰지 않고 overview·q2는 "6px(문서 기준)"이라 적었다. 코드는 `MIN_PROJECTED_NODE_TEXT_PX = 6`(`desktop-readability.mjs:5`)이고 브라우저·정적 검사가 같은 상수를 쓴다. 단 두 게이트의 **계산 입력은 다르다**: 정적 검사는 가용폭을 930(또는 declared-wide 계산)으로 가정하고, 브라우저는 실제 렌더 폭(1440 뷰포트에서 1306px 등)으로 계산한다(T-09: 7.2는 정적 실패·브라우저 통과). 정적 검사가 더 보수적이다. 문서에는 이 차이가 없다.
- 문서 "지정한 테마가 다르게 해석되면 실패"·"라이트 4개, 다크 양 끝"은 코드와 같다(`CAPTURE_VIEWPORTS` = `VISUAL_CHECK_VIEWPORTS`의 처음·끝). q2의 "라이트 4개 뷰포트 전부, 다크는 양 끝"도 같다. 단 q2의 "READ/Still 상태까지 본다"는 측정 전에 상태를 **설정**(`data-motion="still"`, `data-detail-level="read"`)할 뿐 다른 상태 비교는 하지 않는다.
- 문서 "browser-check ... Edge"는 같다. 문서는 `ARCHIFY_CHROME`가 잘못된 경로여도 대체하지 않는다고 하며 코드도 같다(`findChrome`의 `hasOwnProperty`).
- 문서 `delivery-contract.md`는 provenance 실패 시 "브라우저 검사 전에 실패하고 실패 영수증을 남긴다"고 하며 실행으로 확인했다(T-03). 영수증을 쓸 수 없는 경우(이전 영수증과 소유권 충돌, T-16)는 문서에 없고, 이때 진단은 `viewer/evidence-path-conflict`가 추가된다.
- `check --json`은 문서(명령 사용법 표 `archify.mjs:2202`)에 있으나 효과가 없다(R-01).
- 이전 q2 §2.5 "check --require-provenance... 어긋나면 브라우저를 열기 전에 실패"는 맞다. 다만 sidecar가 있으면 `--require-provenance` 없이도 같은 검증이 실행되고, 플래그는 sidecar가 **없을 때**만 실패 여부를 바꾼다(R-02, T-02, T-04). `--require-provenance` 없이 sidecar가 없으면 정적 검사만 하고 통과한다.
- q2 §2.4의 검사 이름 목록은 9개 중 `label_route_clearance`, `finite_svg`, `single_svg`는 맞고, 이름 없이 `composition.issues`로만 나오는 판정(`desktop-readability`, `label-canvas-containment`, `viewport-height`)이 있다는 점이 빠져 있었다(R-15, R-17, R-18).

### 2.2 코드 읽는 순서 [선택]
1. `archify.mjs` `commandCheck`(5581) → `inspectArtifactDeliveryProvenance`(5420) → `inspectDeliveryProvenance`(1904): provenance 판정.
2. `check-render-output.mjs:111-452`(흐름·severity) → `collectArrows`(454) → geometry 함수들(교차 737, 회랑·테두리·리듬·라벨은 geometry.mjs).
3. `archify.mjs` `executeBrowserEvidence`(5663) → `visual-check.mjs` `runBrowserEvidence`(2444) → `ChromeVisualBrowser.inspect`(1659) → `observation`(1942) → `observationDiagnostics`(2168).

구현 전략: 정적 검사는 SVG를 DOM 없이 정규식 토큰(`SVG_TAG_TOKEN`)으로 파싱하고, 같은 경로 분석 결과를 `pathAnalyses` 맵으로 캐시한다. 브라우저 쪽은 측정 JS를 한 문자열로 Chrome에 보내 값을 받고 판정은 Node에서 한다. 영수증은 임시 폴더에서 만든 뒤 원자 교체한다.

### 2.3 비교·재사용 출처 [선택]
없음.

## 적용 메모 [선택]
없음(재구현 계획 없음).
