---
sha: "5979991d5f0af542fbb02ba906bdba4de52b2b64"
created: 2026-11-17
updated: 2026-11-17
sources:
  - packages/parsers/src/compositionContract.ts
  - packages/core/src/compositionContract.ts
  - packages/parsers/src/referenceResolver.ts
  - packages/parsers/src/subCompositionValidity.ts
  - packages/parsers/src/rewriteSubCompPaths.ts
  - packages/parsers/src/assets.ts
  - packages/parsers/src/assetPaths.ts
  - packages/parsers/src/mediaTiming.ts
  - packages/parsers/src/mediaDuration.ts
  - packages/parsers/src/htmlParser.ts
  - packages/core/src/compiler/htmlCompiler.ts
  - packages/core/src/compiler/timingCompiler.ts
  - packages/core/src/compiler/timingResolver.ts
  - packages/core/src/compiler/inlineSubCompositions.ts
  - packages/core/src/compiler/compositionAssembly.ts
  - packages/core/src/compiler/htmlBundler.ts
  - packages/core/src/compiler/staticGuard.ts
  - packages/core/src/compiler/compositionScoping.ts
  - packages/core/src/compiler/svgIdNamespacing.ts
  - packages/core/src/compiler/svgSelectorAliases.ts
  - packages/core/src/compiler/selectorIdTokens.ts
  - packages/core/src/compiler/rewriteSubCompPaths.ts
  - packages/core/src/compiler/subCompositionValidity.ts
  - packages/core/src/compiler/assetPaths.ts
  - packages/core/src/runtime/flattenedRoot.ts
  - packages/core/src/runtime/startResolver.ts
  - packages/core/src/runtime/startExpression.ts
  - packages/core/src/runtime/timeline.ts
  - packages/core/src/runtime/picker.ts
  - packages/core/src/runtime/compositionLoader.ts
  - packages/core/src/runtime/init.ts
  - packages/core/src/runtime/entry.ts
  - packages/core/src/sceneParts.ts
  - packages/core/src/runtime/playbackRate.ts
  - packages/producer/src/services/htmlCompiler.ts
  - packages/engine/src/services/audioMixer.ts
  - docs/concepts/data-attributes.mdx
  - docs/concepts/compositions.mdx
  - docs/reference/html-schema.mdx
depends: []
status: ready
---

# 컴포지션 계약·컴파일

> 컴포지션 HTML(`data-composition-id`, `data-start`, `data-duration`, `data-track-index`, `data-composition-src` 등 `data-*` 속성)을 입력으로 받아, 속성 값을 해석하고 서브 컴포지션을 호스트 안으로 인라인해서 렌더러와 브라우저 런타임이 읽을 수 있는 한 장의 HTML로 만든다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

컴파일 입구는 둘이다. 렌더는 producer의 `compileForRender`를 타고, 프리뷰·린트·`validate`·`layout`·inspector는 core의 `bundleToSingleHtml`을 탄다. 두 입구는 같은 `inlineSubCompositions`와 같은 `compileTimingAttrs`를 부른다(R-24, R-25, R-26).

렌더 경로(`compileForRender`)의 순서는 다음과 같다.

1. 진입 HTML 파일을 읽고, 파일이 `.html`이고 프로젝트 폴더 안에 있는지 확인한다(이 검사의 실패는 `Error` 두 종류이며 R-25에 적는다). `data-composition-src` 값을 정규화한다(R-17).
2. 사전 점검으로 `data-composition-src`가 가리키는 모든 파일(중첩 포함)이 쓸 수 있는 컴포지션인지 확인한다. 하나라도 안 되면 파일 목록을 모아 `EmptyCompositionError`를 던지고 컴파일을 시작하지 않는다(R-15, R-16).
3. 진입 HTML과 각 서브 컴포지션 파일에 `compileTimingAttrs`를 돌려 media 요소의 `id`, `data-start` 기본값, `data-end`, `data-has-audio`를 채운다. `data-duration`이 없는 video/audio는 ffprobe로 길이를 재서 채운다(R-08~R-13).
4. `inlineSubCompositions`가 각 호스트(`data-composition-src`가 있는 요소)에 서브 컴포지션 내용을 넣는다. 이때 CSS·script를 모으고 범위를 좁히며, 경로를 다시 쓰고, 속성을 정리한다(R-14, R-18~R-22).
5. 이후 외부 스크립트·폰트·원격 media 로컬화 같은 렌더 전용 후처리를 한다(이 스펙 범위 밖, 행 5).
6. 첫 번째 `[data-composition-id]` 요소에서 `data-width`·`data-height`·정적 길이를 읽어 결과와 함께 반환한다(R-25).

시작 시각이 `data-start="intro - 0.5"` 같은 참조인 요소는 이 컴파일에서 숫자로 바뀌지 않는다. 참조는 컴파일 뒤 소비자가 각자 해석한다(R-03, R-04). 브라우저 런타임(`core/src/runtime/startResolver.ts`), Node 쪽 정적 해석기(`parsers/src/referenceResolver.ts`), Studio·SDK 파서(`readClipTiming`)가 그 소비자다.

### 1.2 범위·통합 지점 [필수]

- 제공: 컴포지션 속성 계약(속성 이름, 의미, 기본값, 잘못된 값 처리), `data-start` 문법과 참조 해석 규칙, 컴파일 단계에서 추가하는 속성(`id`, `data-start`, `data-end`, `data-duration`, `data-has-audio`), 서브 컴포지션 인라인 규칙(내용 선택, 루트 평탄화, 경로 재작성, 중복 마운트 id, 중첩·순환 처리), 서브 컴포지션 사용 가능 판정.
- 제외:
  - 브라우저 런타임이 `data-start`를 다시 읽어 clip 가시성을 정하고 seek하는 부분은 행 2의 몫이다. 같은 속성을 쓰는 파일은 `packages/core/src/runtime/startResolver.ts`, `timeline.ts`, `init.ts`이다. 이 스펙은 해석 규칙의 차이만 R-04에 적는다.
  - 린트 규칙(`packages/lint`)은 행 7이다. `readClipTiming`이 내는 diagnostics를 린트가 규칙으로 바꿔 쓰지만 그 규칙은 다루지 않는다.
  - 렌더 전용 후처리(원격 media 다운로드, 폰트 임베드, GIF·HEIC 변환, `collectRenderMedia`)와 브라우저로 길이를 재는 `resolveCompositionDurations`는 행 5·6이다.
  - CSS 스코핑의 selector 변환 세부(`scopeSelector` 계열 60-170행)는 R-22의 개념 수준까지만 적었다. SVG id 네임스페이싱과 script wrapper는 R-27~R-29에 적었다.
- 외부 의존·선행 계약: 선행 스펙은 없다. 호출자가 파일 시스템(프로젝트 폴더), media 길이 측정기(core `compileHtml`은 `probeMediaDuration` callback, 렌더는 ffprobe)를 제공한다. DOM 구현은 Node에서 linkedom, 브라우저에서 기본 DOM이다.
- 소유 상태·부작용: 컴파일 함수는 입력 문자열을 바꾸지 않고 새 HTML 문자열을 반환한다(`compileTimingAttrs`, `inlineSubCompositions`는 전달받은 `document`를 제자리에서 바꾼다). 프로젝트 파일은 쓰지 않는다. 렌더 경로의 후처리는 `downloadDir`에 파일을 만들지만 이 스펙 범위 밖이다.

### 1.3 인터페이스와 데이터 의미 [필수]

속성 이름은 외부 계약이라 원문 그대로 쓴다. "소비자"는 값을 읽는 코드이다.

| 속성 | 값·기본값 | 의미·잘못된 값 처리 |
|---|---|---|
| `data-composition-id` | 문자열. 바깥 요소(루트)와 서브 컴포지션 루트에 둔다 | 컴포지션 식별자다. CSS 스코프(`[data-composition-id="<id>"]`), script 스코프, `window.__timelines[<id>]` 키, `data-start` 참조 대상(R-05)이 이 값을 쓴다. 같은 파일을 여러 호스트가 마운트하면 인스턴스마다 `<id>__hf<n>`이 된다(R-18). |
| `data-width`, `data-height` | 정수 px. 렌더 경로는 루트에서 `parseInt`하고 없으면 1080, 1920 | 컴포지션 프레임 크기. 호스트에 없으면 서브 컴포지션 루트 값을 호스트로 복사한다(R-14). |
| `data-start` | 비어 있으면 0. 문법은 R-01 | 시작 시각(초). 컴포지션 안 timeline 기준이다. 서브 컴포지션 안의 요소는 호스트 기준 로컬 시각이다. |
| `data-duration` | 0 이상 유한한 수(초) | 타임라인 슬롯 길이. 비었거나 숫자가 아니거나 음수이면 `invalid-duration`(R-06). |
| `data-end` | 컴파일러가 채우는 파생 속성 | 직접 쓰면 legacy로 본다(R-06). 컴파일러는 video/audio에만 쓴다(R-09). |
| `data-track-index` | 정수. 기본 0 | Studio 타임라인 행 표시용이다. 렌더에서는 읽지 않는다(R-11). |
| `data-layer` | 정수 | `data-track-index`의 legacy 입력. 읽기만 하고 쓰기에서는 지운다(R-07, R-23). 엔진 `audioMixer`는 오디오 layer로 별도로 읽는다. |
| `class="clip"` | | 컴파일러·parsers는 읽지 않는다(1.4 확인 한계). 가시성은 `data-start`로 정해지고 `.clip` 규칙은 레이아웃 용도다(docs). |
| `data-composition-src` | 프로젝트 루트 기준 상대 경로 | 서브 컴포지션 파일을 가리키는 호스트 표시. 인라인되면 호스트에서 지워지고 `data-composition-file`이 대신 들어간다(R-14). |
| `data-playback-start`, `data-media-start` | 0 이상 수(초). 앞의 것이 우선, 둘 다 무효이면 0 | source 안에서 시작할 위치. media와 서브 컴포지션 호스트(in-point)에 쓴다. |
| `data-hf-auto-start` | 빈 속성 | 컴파일러가 `data-start="0"`을 대신 넣었다는 표지(R-08). |

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `parseStartExpression(raw)` | string? → `{kind:"absolute", value}` / `{kind:"reference", refId, offset}` / null | 문법 해석만 한다. 참조를 풀지 않는다(R-01). |
| `readClipTiming(attrs, {resolveReferenceEnd?, defaultStart?})` | attribute reader → `{start, duration, end, trackIndex, durationSource, trackSource, diagnostics[]}` | 던지지 않고 diagnostics 배열에 코드를 쌓는다(R-02~R-07). Studio·SDK·린트·player가 쓴다. |
| `writeClipTiming(attrs, update)` | attribute writer → 새 timing | 쓰기는 canonical 속성만 만들고 `data-end`·`data-layer`를 지운다(R-23). 잘못된 값은 `ClipTimingWriteError`를 던진다. |
| `compileTimingAttrs(html)` | string → `{html, unresolved[]}` | 정적 컴파일. 순수 함수이고 DOM이 필요 없다(R-08~R-10). |
| `injectDurations`, `clampDurations` | html, `[{id, duration}]` → html | id가 같은 모든 여는 태그에 속성을 고쳐 쓴다(R-12, R-13). |
| `compileHtml(raw, projectDir, prober?)` | async → string | core의 정적+probe 컴파일. 프리뷰 번들러가 쓴다(R-13). |
| `inlineSubCompositions(document, hosts, options)` | → `{styles, scripts, scriptItems, externalLinks, variablesByComp, importMaps, moduleScripts, ...}` | 호스트 목록을 큐로 처리하고 document를 제자리에서 고친다(R-14~R-22). |
| `checkSubCompositionUsability(html, parseHtml)` | → `{ok, reason?, detail?}` | `reason`은 `empty` / `unparsable` / `no-content` / `no-composition-root`(R-15). |
| `bundleToSingleHtml(projectDir, options?)` | → string | 프리뷰·검사용 번들(R-24). |
| `compileForRender(projectDir, htmlPath, downloadDir, options)` | → `CompiledComposition` | 렌더용 컴파일(R-25). |

### 1.4 행동 규칙과 남은 질문 [필수]

**A. 속성 해석(`parsers/src/compositionContract.ts`)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `parseStartExpression`에 `data-start` 문자열 | 앞뒤 공백을 지운 뒤 순서대로 판정한다. ① 비어 있으면 null. ② `Number()`가 유한한 수이면 absolute(`1e3`, `0x10`, `+5`, `-3`도 absolute). ③ 전체가 `^[A-Za-z0-9_.:-]+$`이면 reference이고 offset 0이다. ④ 끝이 숫자(`\d+` 또는 `\d+.\d+`)이고 그 앞(공백 건너뜀)이 `+` 또는 `-`이며 그 앞부분(trim)이 ③ 패턴이면 reference이고 offset은 부호×크기이다. ⑤ 나머지는 null. ③이 ④보다 먼저라서 공백 없는 `intro-0.5`는 id가 `intro-0.5`인 참조 하나로 읽힌다(offset 참조가 되지 않는다). `intro - 0.5`, `intro -0.5`, `intro+0.5`는 offset 참조이다. | 코드 확인 |
| R-02 | `readClipTiming`에서 `data-start`가 없거나 공백이다 | `start`는 `defaultStart`이다. 옵션이 없으면 0이다(`defaultStart: null`을 주면 null). diagnostics는 없다. 값이 있는데 `parseStartExpression`이 null이면 `invalid-start`를 남기고 `start`는 null이다. | 코드 확인 |
| R-03 | absolute 값 | `start = max(0, value)`. 음수는 0으로 올린다(진단 없음). reference는 호출자가 준 `resolveReferenceEnd(refId)`가 유한한 수를 주면 `max(0, end + offset)`이다. 콜백이 없거나 null·NaN을 주면 `unresolved-start-reference`를 남기고 `start`는 null이다. 순환 처리는 이 함수에 없고 호출자가 한다(R-04). | 코드 확인 |
| R-06 | `readClipTiming`이 `data-duration`·`data-end`를 읽는다 | `data-duration`이 있으면 canonical이다. 값이 비었거나 NaN·무한이거나 음수이면 `invalid-duration`, `durationSource:"invalid"`, `duration`·`end`는 null. 정상이면 `end = start + duration`(`start`가 null이면 end도 null). 이때 `data-end`가 같이 있으면 `\|data-end − end\| ≤ 1e-9`일 때만 조용하고, 그 밖에는 `deprecated-end`와 `conflicting-end`를 남긴다(수로 못 읽는 `data-end`는 `deprecated-end`와 `invalid-end`). `data-duration`이 없고 `data-end`만 있으면 항상 `deprecated-end`를 남기고 `legacy-end`로 읽는다(`data-end < start`이면 `end-before-start`, duration·end null). 둘 다 없으면 `durationSource:"missing"`이다. | 코드 확인 |
| R-07 | `data-track-index`·`data-layer` | `data-track-index`는 `parseNumeric`한 값이 정수여야 한다. 아니면 `invalid-track-index`이고 `trackIndex`는 0이다. 둘 다 없으면 0, 출처 `default`. `data-track-index`가 없고 `data-layer`만 있으면 layer 값을 쓰고 `deprecated-layer`를 남긴다. 둘 다 있으면 track 값을 쓰고 `deprecated-layer`를 남기며, 두 값이 다르면 `conflicting-layer`도 남긴다. | 코드 확인 |

(R-04, R-05는 아래 B 절에 있다. ID는 한 번 붙이면 바꾸지 않으므로 순서가 건너뛴다.)

**B. `data-start` 참조 해석(소비자 세 곳)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-04 | reference 시작 시각을 푼다 | 의미는 "참조 대상의 시작 + 대상 길이 + offset"이다. 해석기는 세 곳이고 결과가 같지 않을 수 있다. **(a) 브라우저 런타임** `startResolver.ts`: 대상은 `resolveStartForElementInternal(target, 0)`으로 풀어서 대상 시작은 호스트 origin을 이미 포함한 루트 timeline 절대값이다. `fallback`은 참조 대상이 없을 때, 방문 중인 요소를 다시 만날 때(순환), `data-start`가 없거나 파싱되지 않는 요소일 때(상속한 호스트의 시작, 없으면 `fallback`) 쓴다(`startResolver.ts:140-143`, `149-151`). 대상 시작은 `resolveStartForElementInternal(target, 0)`이라 대상 쪽 fallback은 0이고 최상위 호출의 fallback은 호출자가 준 값이다. 순환 안쪽에서는 `0`이 고리를 끊는 값이고 offset은 누적된다. 계산된 값은 resolver 인스턴스의 `startCache`(WeakMap)에 저장되므로 순환 안쪽 값은 먼저 푼 요소에 따라 달라진다. 예: A="B + 1", B="A + 2"(둘 다 길이를 모름)에서 A를 먼저 `resolveStartForElement(A, 5)`로 풀면 B=2, A=3이다(5가 아니다). B를 먼저 풀면 A=1, B=3이고 이 값이 캐시에 남아 이후 A를 물어도 1이다(`startResolver.ts:46,134-170`). 결과는 `max(floor, 대상시작 + 대상길이 + offset)`이고 `floor = min(0, 호스트 offset)`이다(호스트 값은 이 floor로만 들어간다). 대상 길이 출처는 ① authored `data-duration` 또는 `data-end − start`, ② media 요소의 `duration`(재생속도·mediaStart 반영), ③ timed `<img>` 기본 길이, ④ 등록된 timeline 길이(`window.__timelines[<composition id>]`, GSAP) 순이고 모두 없으면 0이다. **(b) Node 정적 해석기** `referenceResolver.ts`의 `resolveReferencedStart`: 순환·대상 없음이면 0, 결과는 `max(0, 대상시작 + 대상길이 + offset)`이고 호스트 offset은 쓰지 않는다. 대상 길이는 `data-duration`(>0), 없으면 `data-end − 시작`(>0)뿐이고 media 자체 길이·timeline 길이는 모른다(그러면 길이 0). 이 길이 출처 차이가 (a)와 (b)가 어긋나는 가장 큰 원인이다. 컴파일이 media에 `data-duration`을 채우므로(R-12) media 대상은 (b)도 길이를 알게 되지만, `data-duration`이 없는 GSAP 컴포지션 대상은 (b)에서 길이 0이다(브라우저로 길이를 재서 주입하는 단계는 행 5). 쓰는 곳: 엔진 `audioMixer`, `videoFrameExtractor`, producer `renderMediaCollector`, CLI `timeline`·`compositions`. **(c) `readClipTiming` 호출자**(`htmlParser.parseHtml`, studio, sdk, studio-server, player): 호출자가 `resolveReferenceEnd`를 주고, 순환·미해석이면 `start`는 null이다. `parseHtml`은 `timing.start ?? 0`, `timing.duration ?? 5`로 대신 채운다. 세 곳 모두 순환을 에러로 막지 않는다. | 코드 확인 |
| R-05 | 참조 대상 찾기 | 런타임(a)과 정적 해석기(b)는 같은 순서로 찾는다. ① 참조하는 요소가 속한 컴포지션(가장 가까운 `[data-composition-id]` 조상. 요소가 컴포지션 루트 자신이면 그 부모 쪽 컴포지션) 안에서 `id`가 같고 같은 컴포지션 스코프인 요소. ② 문서 전체의 `getElementById(refId)`. ③ `data-composition-id`가 `refId`인 요소. 즉 docs의 "같은 컴포지션 안에서만"과 달리 구현은 못 찾으면 문서 전체로 넓힌다(2.1). (c)는 호출자마다 찾는 방식이 다르다. `htmlParser.parseHtml`은 컴포지션 스코프 없이 문서의 `[data-start]` 요소를 `id` 또는 `data-hf-id`로 찾는다. studio `timelineIframeHelpers.ts`는 `data-composition-id`도 id로 등록한다. sdk `session.ts`는 `resolveScoped`(스코프 조회), studio-server `previewAdapter.ts`는 `findById`를 쓴다. `data-start`가 없는 요소는 `[data-start]` 기반 조회(`parseHtml`, studio)에서 대상이 되지 못한다. | 코드 확인 |

**C. 정적 컴파일(`compileTimingAttrs`)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-08 | `compileTimingAttrs`가 `<video>`·`<audio>` 여는 태그를 만난다 | `id`가 없으면 `hf-video-<n>` 또는 `hf-audio-<n>`을 넣는다(n은 태그별로 0부터, 한 번의 호출 안에서 센다). `data-start` 값을 읽어 null이면 `data-start="0"`과 `data-hf-auto-start=""`를 넣는다. 읽기 함수(`getAttr`)는 `name="value"` 꼴 속성만 값으로 보기 때문에, 속성이 아예 없는 경우뿐 아니라 값 없는 bare `data-start`(`<video data-start>`)도 null이 되어 `data-start="0"`이 하나 더 주입된다(같은 속성이 두 번 생긴다). `data-start=""`(빈 값)는 값으로 읽히므로 주입하지 않는다. `<video>`에 `data-has-audio`가 없으면 `muted` 속성이 있으면 `"false"`, 없으면 `"true"`로 넣는다. `id`도 같은 방식이다. `getAttr`는 `name="value"` 꼴만 값으로 보므로 bare `id`와 빈 `id=""`는 모두 없는 것으로 취급해 새 `id`를 주입하고 `id` 속성이 중복된다. 닫히지 않은 태그는 건드리지 않는다. | 코드 확인 |
| R-09 | 같은 태그에 `data-end`가 없다 | `data-duration`이 유한한 수이고 `data-start`가 수이면 `data-end = String(start + duration)`을 넣는다. `data-start`가 참조이면(수가 아님) `data-end`를 넣지 않는다. `data-duration`이 없거나 수가 아니면 `unresolved`에 `{id, tagName, src, start(수 아니면 0), mediaStart, playbackRate}`를 넣는다. `data-end`가 이미 있으면 아무것도 하지 않는다. 음수 `data-duration`도 수라서 `data-end`가 start보다 작게 들어간다(R-06의 `invalid-duration`과 다르다). `unresolved.id`는 R-08에서 주입된 id일 수 있다(`id=""`·bare `id`이면 새 id가 들어가 `id` 속성이 중복된다). | 코드 확인 |
| R-10 | 같은 호출에서 `div`·`section` | `data-start`가 있고 `data-end`·`data-duration`이 둘 다 없고 `id`가 있으면 `unresolved`에 `{id, tagName:"div", start(수 아니면 0), compositionSrc?}`로 넣는다. 이 요소에는 어떤 속성도 쓰지 않는다. 즉 비-media 요소에는 `data-end`가 생기지 않는다. | 코드 확인 |
**D. `data-track-index`**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-11 | `data-track-index`를 렌더가 읽는가 | 렌더 경로(`producer/src`, `engine/src`, `core/src/runtime`의 재생·가시성 코드)는 `data-track-index`로 시각·겹침·z-order를 정하지 않는다. 읽는 곳은 ① 런타임 `timeline.ts`의 `parseAuthoredTrack`(Studio가 쓰는 clip manifest의 track), `picker.ts`(선택자), ② `htmlParser.getZIndex`(Studio 파서의 `zIndex` 값), ③ `readClipTiming`(진단 포함)이다. 예외로 `<img>`는 `data-start` 또는 `data-track-index` 중 하나만 있어도 "timed"로 취급되어 기본 길이를 받는다(`resolveTimedImageDurationSeconds`). legacy `data-layer`는 엔진 `audioMixer`가 오디오 `layer`로 읽는다. | 코드 확인 |

**E. media 길이 보정**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-12 | `injectDurations(html, [{id,duration}])` | `id`가 같은 모든 여는 태그에 대해 `data-duration`이 수가 아니면 `String(duration)`으로 쓰고, `data-end`가 없고 `data-start`가 수이면 `start + duration`을 넣는다. 참조 `data-start`에는 `data-end`를 넣지 않는다. | 코드 확인 |
| R-13 | 길이 보정 두 단계. core `compileHtml`(프리뷰 번들러)과 producer `compileHtmlFile`(렌더)은 구조가 같고 세부가 다르다 | **공통**: ① `unresolved`의 video/audio(`src` 있음)를 측정해 `data-duration`·`data-end`를 넣는다(R-12). ② 이미 `data-duration > 0`인 non-loop media 중 audio만, 선언 길이가 `maxDuration + 0.05`를 넘으면 `data-duration`을 `maxDuration`으로 줄이고 `data-end`를 다시 쓴다. video는 선언 길이가 더 길어도 줄이지 않고 마지막 프레임을 유지한다. **core `compileHtml`**: probe callback이 없으면 정적 컴파일만 한다. 파일 길이 측정값이 0 이하이면 두 단계 모두 그 요소를 건너뛴다. 1단계 길이는 `파일길이 − mediaStart`이고 이 값이 0 이하이면(`mediaStart ≥ 파일길이`) `파일길이`로 대신한다(`htmlCompiler.ts:60-61`). `playbackRate`는 쓰지 않는다. ②의 `maxDuration`은 `파일길이 − mediaStart`이고 0 이하이면 그 요소는 줄이지 않는다(`maxDuration > 0` 검사, `:91`). **producer**: 측정은 `resolveMediaDuration`이 하고(ffprobe, 원격 `http(s)` src는 `downloadDir`에 내려받음) 길이와 ②의 `maxDuration` 둘 다 `resolveNaturalMediaTimelineDurationFromValues(파일길이, mediaStart, playbackRate)`이다(재생속도 반영). 이 함수는 `max(0, 파일길이 − mediaStart) / rate`를 돌려주므로(`mediaDuration.ts:70-73`, `playbackRate.ts:92-102`) `mediaStart ≥ 파일길이`이면 `null`이 아니라 0이다. producer는 `Number.isFinite`만 보고 건너뛰지 않아(`htmlCompiler.ts:758-760`) 1단계에서 `data-duration="0"`이 들어가고(core는 이때 `파일길이`로 대신한다), 2단계에서는 `maxDuration=0`이라 audio의 선언 길이가 0.05초를 넘으면 `data-duration`이 0으로 줄어든다(`:792-797`). video는 줄이지 않는다. 파일이 없거나 asset root 밖·private 경로이거나 다운로드 실패이면 `null`이라 건너뛴다. audio는 측정이 실패해도 건너뛰고(텍스트 문서이면 warn 후 요소를 렌더에서 뺀다), video는 측정·검증 실패를 던진다. 2단계에서 `hiddenVideoIds`(숨은 video)와 loop·src 없는 요소는 제외한다. `data-var-src`가 있는 video/audio 중 정적 컴파일 결과 `unresolved`에 든 것에는 `data-hf-inferred-duration=""`를 붙인다(`markInferredVariableMediaDurations`). 표시는 `injectDurations` 이전의 `unresolved` 기준이라 probe로 길이를 결국 채운 요소에도 붙는다(`:762-764`). producer는 audio를 줄이면 warn을 남긴다. | 코드 확인 |

**F. 서브 컴포지션 인라인**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-14 | 호스트 하나를 처리한다(`inlineSubCompositions`의 큐 항목) | 호스트 `data-composition-src` 값으로 HTML을 얻고 사용 가능 판정(R-15)을 통과하면 내용을 호스트 안에 넣는다. 이어서 호스트에서 `data-composition-src`를 지우고 `data-composition-file="<src>"`를 넣는다. 서브 컴포지션 루트가 `data-timeline-locked`·`data-no-timeline`을 가졌으면 호스트로 복사한다. 루트의 `data-width`·`data-height`는 호스트에 없을 때만 각각 복사한다. 호스트가 이미 가진 `data-start`·`data-duration`·`data-track-index`는 그대로이다. producer는 공용 인라이너가 끝난 뒤 처음 찾은 호스트(초기 `hosts` 목록, 중첩 호스트는 제외)에 한해, `data-width`·`data-height`가 둘 다 있으면 `style`에 `width:<w>px`, `height:<h>px`를 더한다. 이미 있는지는 style 문자열에 `width`·`height` 부분 문자열이 들어 있는지로만 보므로 `max-width` 같은 속성이 있어도 해당 항목을 건너뛴다. | 코드 확인 |
| R-15 | 서브 컴포지션 파일 판정 | 내용 선택: `<template>`이 있으면 `[data-composition-id]`를 가진 첫 template(없으면 첫 template)의 innerHTML, 없으면 `<body>` innerHTML, 둘 다 없고 `<html>`도 없으면 파일 전체(bare fragment). 판정 순서: 비었거나 공백뿐 → `empty`, `documentElement` 없음 → `unparsable`, 선택한 내용이 공백 → `no-content`, 내용 파싱 실패 → `unparsable`, 내용 안에 `[data-composition-id]` 요소가 없음 → `no-composition-root`. | 코드 확인 |
| R-16 | 판정 실패 시 처리 경로별 | 인라이너(프리뷰·번들러, 렌더의 후단 인라인)는 던지지 않고 `onMissingComposition(src, detail)`을 부른다. 번들러와 producer는 `console.warn("Skipping sub-composition ...")`을 남기고 그 호스트를 건너뛴다. 건너뛴 호스트는 바뀌지 않고 `data-composition-src`를 그대로 가진 채 남는다. 렌더는 인라인 전에 R-17의 사전 점검이 먼저 던지므로 이 경로는 사전 점검 이후 파일이 바뀐 경우에만 탄다. | 코드 확인 |
| R-17 | `compileForRender` 사전 점검 `assertSubCompositionsUsable` | 모든 호스트(재귀)를 점검해 문제를 모은 뒤 한 번에 `EmptyCompositionError`(`code:"EMPTY_COMPOSITION"`, 메시지 첫 줄 `N composition file(s) referenced by data-composition-src cannot be rendered:`와 `  - <src>: <detail>` 줄)를 던진다. detail 값: `it is outside the project folder`, `it is outside the project in a private location`, `it is git metadata, an env file or a private tool record`, `it is not an .html file, so it is refused`, `the file does not exist`, `it is a folder, not an HTML file`, R-15의 detail 문구. `__UPPER__` 꼴 placeholder 등 미해결 템플릿 토큰(`isUnresolvedAssetPlaceholder`)은 건너뛴다. 이미 방문한 파일(순환)은 조용히 건너뛴다. 중첩 점검에서도 `projectDir`는 바꾸지 않는다(경로는 항상 프로젝트 루트 기준). 점검 전에 `data-composition-src`의 `%xx`와 앞 `/`를 프로젝트 상대 경로로 정규화한다. | 코드 확인 |
| R-18 | 같은 컴포지션 id의 runtime id 부여(번들러와 producer가 다르다) | **번들러**(`assignBundledRuntimeCompositionIds`): 대상 호스트는 `data-composition-src`가 있는 요소와, `<template id="<id>-template">`가 문서에 있는 `data-composition-id` 요소이다. id별 호스트 수를 세고(템플릿 호스트는 자식 유무와 무관하게 센다), 같은 id를 가진 마운트가 둘 이상이면 문서 순서대로 `<id>__hf1`, `<id>__hf2`, ...를 `data-composition-id`에 쓰고 원래 값을 `data-hf-original-composition-id`에 보관한다. id 부여는 `data-composition-src` 호스트이거나 자식이 0개인 템플릿 호스트에만 일어난다. 페이지 루트(문서의 첫 `[data-composition-id]`)와 같은 id를 가진 호스트가 있으면 `countPageRoot`가 그것을 반복으로 세므로, 호스트가 하나뿐이어도 `__hf1`이 붙을 수 있다. 중복이 아니면 `data-composition-id`는 그대로이고 `data-hf-original-composition-id`는 지운다. **producer**: 초기 호스트는 `[data-composition-src]` 요소뿐이고 위 번들러 함수로 같은 규칙을 적용한다(템플릿 호스트 규칙은 번들러에서만 쓰인다). 인라인 중 새로 발견된 중첩 호스트는 `ProducerHostIdentityMap`이 처음 조회될 때 부여하는데, 단일 인스턴스여도 항상 `<id>__hf<n>`(n은 1부터, 같은 이름이 이미 있으면 올림)이고 `data-hf-original-composition-id`를 단다. 호스트에 `data-composition-id`가 없으면(anonymous) 아무 id도 부여하지 않고 루트의 id가 스코프가 된다. CSS 스코프 선택자와 `__hfVariablesByComp` 키는 runtime id를 쓴다. | 코드 확인 |
| R-19 | 평탄화: 인라인할 때 서브 컴포지션 루트 | `flattenInnerRoot`가 주어진 경로(번들러와 producer 모두 `prepareFlattenedInnerRoot`)이면 루트를 복제해 `data-composition-id`, `data-composition-file`, `data-start`, `data-duration`, `data-end`, `data-track-index`, `data-track`, `data-composition-src`, `data-hf-authored-duration`, `data-hf-authored-end`를 지우고, 루트의 `id`는 `data-hf-authored-id`로 옮기며, `data-hf-inner-root="true"`를 달고, `style`에 `width:<data-width>px;height:<data-height>px`(없으면 `100%`)를 더한 뒤 `host.innerHTML = 복제본.outerHTML`로 넣는다. 서브 컴포지션 루트가 갖고 있던 시간 속성은 사라지고 시간은 호스트가 정한다. 호스트가 anonymous(자기 `data-composition-id` 없음)이면 평탄화한 루트에 스코프 id를 `data-composition-id`로 되돌려 둔다. `flattenInnerRoot` 없이 호출하면 호스트에 id가 있을 때 루트의 `innerHTML`만, 없을 때 `outerHTML`을 넣고 `data-hf-authored-id`를 호스트에 단다. 루트를 못 찾으면(호스트가 지목한 id의 루트가 내용에 없음) body innerHTML(없으면 documentElement.outerHTML)을 넣는다. | 코드 확인 |
| R-20 | 경로 재작성 `rewriteAssetPath(compSrc, path, assetExists?)` | `src`·`href`·`srcset`(그리고 `rewriteInlineStyles`가 켜지면 inline `style`과 hoist한 CSS의 `url()`)에 적용한다. 바꾸지 않는 값: 비었거나 `http(s)://`, `//`, `data:`, `#`, `/`로 시작, 2글자 이상 scheme(`isNonRelativeUrl`), `compSrc`의 디렉터리가 없거나 `.`, `/`로 시작하는 경로. 그 밖의 상대 경로는 `compSrc`의 디렉터리 기준으로 합친 프로젝트 루트 상대 경로(`sibling`)를 만든다. `../`로 시작(또는 `..`)하면 항상 `sibling`으로 바꾼다. 그냥 상대 경로(`assets/a.png`)는 `assetExists(sibling)`이 참일 때만 바꾼다(형제 파일 규약과 프로젝트 루트 규약을 파일 시스템으로 구분). `assetExists`가 없으면 그냥 상대 경로는 그대로이다. 합치기는 `posix.resolve("/", ...)`로 하므로 `..`가 프로젝트 루트 위로 올라가도 오류 없이 루트에서 잘려 루트 직하 경로가 된다(예: `compositions/a.html`의 `../../x.png`는 `x.png`). 결과는 POSIX 구분자이다. `splitUrlSuffix`로 `?`·`#` 접미사를 뗀 경로를 `decodeWellFormedEscapes`로 해독해 합친 뒤 `encodeUrlPath`로 다시 인코딩하고 접미사를 붙인다(`rewriteSubCompPaths.ts:78-88`. 이 세 함수는 열지 않았다). 서브 컴포지션 경로 재작성의 속성은 `PATH_ATTRS`(`assetPaths.ts:20`)의 `src`·`href` 둘과 `srcset`(`rewriteSrcsetUrls`)뿐이다. `poster`와 `xlink:href`는 이 단계에서 재작성하지 않는다. R-24의 asset inliner(`htmlBundler.ts:240`, `1481`)는 `src`·`href`·`poster`·`xlink:href`를 읽는다. `<head>`의 `<link href>`, `<script src>`도 같은 규칙을 쓴다. | 코드 확인 |
| R-21 | 중첩·순환 | 한 호스트를 인라인한 직후 그 안의 `[data-composition-src]` 호스트를 찾아 큐 뒤에 넣는다. 조상 `src` 문자열 목록(`ancestry`)에 같은 `src`가 있으면 `circular composition reference`로, 조상 수가 20 이상이면 `nesting depth exceeded`로 건너뛰고 `onMissingComposition`(경고)만 부른다. 예외는 없다. 비교는 문자열 그대로라서 `./a.html`과 `a.html`은 다른 `src`이다(이때 순환은 깊이 20에서 멈춘다. 추론). 렌더의 `parseSubCompositions`·`assertSubCompositionsUsable`은 방문한 파일 경로(해석된 경로)를 쓰고 반복을 말없이 건너뛴다. | 코드 확인(순환 판정 방식의 결과는 추론) |
| R-22 | 호스트가 모은 asset 처리 | 서브 컴포지션의 `<style>`은 경로를 바꾼 뒤 `[data-composition-id="<runtime id>"]` 범위로 좁혀 모은다. 실행 가능한 `<script>`는 컴포지션 스코프 wrapper와 error boundary로 감싸 모은다(`importmap`, `type=module`은 별도 목록). `<link rel=stylesheet\|preconnect>`는 루트 문서로 hoist한다. 이 asset은 서브 컴포지션 안에서 지운다. 호출자가 head·body에 넣는다. 모든 인스턴스 인라인이 끝난 뒤 충돌하는 SVG id만 네임스페이스를 붙인다. 개념 수준 세부(코드 확인): ① CSS는 postcss로 파싱해 rule의 selector마다 `scope + " " + selector`로 바꾼다. 대상은 global at-rule(`@keyframes`·`@-webkit-keyframes`·`@font-face`) 안이 아니고 다른 rule 안에 중첩되지도 않은 rule이며, `@media`·`@supports` 안의 rule은 포함된다(`forEachScopedRule`, `compositionScoping.ts:172-199`, `227-233`). `@keyframes`·`@font-face` 안의 rule과, rule 안에 중첩된 rule은 건드리지 않는다. 파싱이 실패하면 빈 문자열을 반환한다. 서브 컴포지션 인라인에서는 `scopeRootSelectors`가 켜져 있어 맨 `html`·`body`·`:root` selector가 호스트가 아닌 컴포지션 박스(`scope:not(:has([data-hf-inner-root])), scope > [data-hf-inner-root]`)로 바뀐다(`body.dark` 같은 복합 selector는 일반 스코핑). 컴포지션 id 속성 selector(`[data-composition-id="X"]`)만 있으면 같은 컴포지션 박스 selector, 뒤에 다른 selector가 붙으면 `scope`로 치환하고, 루트 요소에 대한 `[data-start]`·`[data-duration]` 속성 selector는 떼어낸다. 원래 루트 `#id`는 `[data-hf-authored-id="id"]`로 바뀐다. 같은 파일이 여러 번 마운트되면 placeholder scope로 한 번만 변환한 템플릿을 재사용한다. ② script는 즉시 실행 함수로 감싸 `window.__hyperframes`를 컴포지션 범위 객체(`getVariables`, `assetUrl` 등)로 바꿔 끼우고, 예외는 `errorLabel`과 함께 잡는다. ③ SVG id는 문서 전체에서 충돌하는 id 중 `url(#id)`·`href`로 네이티브하게 참조되는 것만 이름을 바꾸고(원래 이름은 `data-hf-authored-id`에 남김), 해당 인스턴스의 `<style>` 텍스트에도 같은 치환을 적용한다. 바뀐 id 이름 규칙·충돌 판정은 R-27, selector 변환 도구와 브라우저 별칭 Proxy는 R-28, script wrapper 전체와 변수 표 방출은 R-29에 적었다. | 코드 확인 |
| R-27 | 모든 인스턴스 인라인이 끝난 뒤 `namespaceCollidingSvgIds(document, scopes, finalizedIds?)`가 SVG id를 개명한다(`scopes`는 호출자마다 구성이 같다. 인라인된 호스트마다 하나(namespace는 runtime id, 없으면 호스트 id, 그것도 없으면 루트 선언 id), 최상위 문서 하나(`root: documentElement`, namespace 빈 문자열, `referenceTarget:"document"`, 호스트와 clip은 `exclude`, `cssTexts`는 루트 `<style>`), `sceneClipRoots`가 고른 clip마다 하나(namespace `clip-<순번>`). `sceneClipRoots`는 컴포지션 호스트 밖에서 `<svg>`를 가진 최상위 timed clip, 즉 `[data-start]`가 있고 `data-composition-id`·`data-composition-src`가 없으며 같은 종류의 조상이 없고 가장 가까운 `[data-composition-id]` 조상 안에 있는 요소를 고른다) | **범위 판정**: scope의 `namespace`가 빈 문자열이면 개명 후보는 없고 id는 얼어 있지만 참조 수리는 여전히 한다(아래 상속 항목). 호스트 scope의 namespace는 `runtimeCompId \|\| scopeCompId`이고 `scopeCompId = plan.authoredCompositionId`(`compositionId \|\| declaredCompositionId`, 즉 호스트 id, 없으면 서브 컴포지션 루트가 선언한 id. `inlineSubCompositions.ts:510`, `compositionAssembly.ts:244`)라서 id 없는 호스트도 값이 있다. 빈 문자열이 되는 것은 최상위 문서 scope와, 호스트 id도 루트 선언 id도 없는 비정상 경우뿐이다(후자는 R-15의 `no-composition-root` 판정에서 걸러진다고 추론). 최상위 문서의 id는 개명되지 않고 인스턴스 쪽이 비키는 구조이다. 그 밖에는 `scope.root` 아래(중첩 호스트 `exclude` 하위 제외)의 `svg [id], svg[id]` 요소 중, 같은 scope 안의 attribute 값이나 추출된 `<style>` 텍스트(`cssTexts`)가 `url(#id)` 또는 `href`·`xlink:href="#id"`로 가리키는 id만 개명 후보(renamable)이다. GSAP `tl.to("#x")` 같은 JS만의 참조와 런타임에 스크립트가 주입하는 참조는 세지 않는다(그래서 두 인스턴스가 JS로만 쓰는 같은 id는 개명되지 않고 둘 다 남는다. 코드 주석이 의도된 잔여로 적었다). `finalizedIds`에 이미 든 요소는 후보에서 빼서 다음 호출이 다시 개명하지 않는다. **충돌 판정**: 문서 전체 `[id]`를 문서 순서로 센다(최상위 문서가 직접 가진 id도 포함하고, 이미 개명된 요소는 원래 id로도 등록한다). 요소가 둘 이상인 id가 충돌이다. 충돌 id의 keeper는 문서 순서상 첫 번째 non-renamable 요소이고, 그런 요소가 없으면 첫 요소이다. keeper가 아니면서 현재 id가 같은 renamable 요소가 속한 scope마다 개명 대상이 된다. 새 id는 scope와 id 쌍마다 한 번만 만든다(`planRenames`). 그래서 한 scope 안에 같은 id를 가진 renamable 요소가 둘 이상이면 `applyRenames`가 모두 같은 새 id로 바꾸어 scope 안 중복 id는 그대로 남는다. **새 이름**: 새 id는 `<namespace의 [^a-zA-Z0-9_-]를 -로 바꾼 값>--<원래 id>`이고 문서에 이미 있거나 이번에 만든 id와 겹치면 `-2`, `-3`... 접미사를 붙인다(C-17). **적용**: 개명한 요소는 `data-hf-authored-id`에 원래 id를 남기고(이미 있으면 유지), 변경 내역을 `data-hf-svg-reference-aliases` 속성(상수 `SVG_REFERENCE_ALIASES_ATTR`)에 `{name, localName, namespaceURI, before, after}` JSON 배열로 기록한다(`id` 변경과 `href`·`url()` 값 변경 모두. `xlink:href`는 직렬화된 SVG에서 XLink 네임스페이스로 복원한다). 같은 scope 안 모든 요소의 `href`류(`#id`)와 `url(#id)` 값(inline `style` 포함)도 새 id로 고친다. scope마다 old→new 맵을 돌려주고, 맵에는 다른 scope에서 개명된 문서 첫 정의를 가리키는 상속 항목(그 scope가 같은 id의 로컬 정의가 없을 때)과 로컬 개명 항목이 들어간다. `referenceTarget:"document"` scope는 로컬 정의를 보지 않아 문서 순서상 첫 정의를 따라간다. 호출자는 인라이너(`inlineSubCompositions.ts:800-841`)와 브라우저 런타임의 `namespaceMountedSvgIds`(`compositionLoader.ts:903-949`, 런타임에 마운트한 컴포지션용이고 `finalizedIds`를 공유)이다. 호출자가 이 맵을 `rewriteSvgIdReferencesInCss`로 해당 인스턴스의 `<style>` 텍스트에 적용한다: 규칙 selector의 `#old`는 `:is(#old, #new)`로, 선언 값과 at-rule 인자의 `url(#old)`는 `url(#new)`로 바뀌고, 파싱 실패하면 원문을 그대로 돌려준다. | 코드 확인 |
| R-28 | 개명된 SVG id와 속성 값이 있는 문서에서 선택자가 쓰인다(컴파일 때 CSS, 런타임에 `querySelector`) | `selectorIdTokens.ts`는 selector 문자열 변환 도구이다. `replaceSelectorIdTokens(selector, candidateIds, resolveReplacement)`는 따옴표 안과 attribute 대괄호 안(`markUnguardedOffsets`의 정규식 구간)이 아닌 곳의 `#id` 토큰만 대상으로 하고, CSS 식별자 규칙으로 `\.`·`\HEX ` escape를 해독한 값이 후보에 있을 때만 바꾼다(그래서 `#clip2`는 `#clip`으로 오인되지 않고 `#fx\.1`은 id `fx.1`과 맞는다). `escapeCssIdentifier`는 `CSS.escape`와 같은 알고리즘(Node에 `CSS` 전역이 없어 직접 구현)이다. `parseAttributeSelector`·`replaceSelectorAttributeTokens`는 `[name op value flag]` 꼴(`=`, `~=`, `\|=`, `^=`, `$=`, `*=`, 선택적 `i`/`s` flag, namespace prefix)을 해석한다. `svgSelectorAliases.ts`의 `rewriteSvgSelectors(selector, ids, references, namespaces?)`가 이를 써서 개명 전 이름도 계속 맞게 만든다. ① `#old` → `:is(#old, #new)`(`references`의 `id` 기록이 있으면 같은 방식으로 합친다). ② attribute selector `[href="#a"]`는 `references`에서 이름(prefix 규칙 포함)이 같고 `before` 값이 연산자 조건으로 맞는 항목마다 `[name="<after>"]` 대안을 추가해 `:is(원래, 대안...)`로 묶는다. attribute selector의 namespace는 `none`(prefix 없음), `any`(`*\|attr`), `named`(`ns\|attr`) 셋이다. `namespaces`(CSSOM의 `@namespace` 표)를 주면(브라우저의 CSSOM 수리) `named`만, 안 주면 `none`·`any`와 id 토큰만 바꾼다(`svgSelectorAliases.ts:47-49`, `67`). `none`은 `namespaceURI`가 null인 기록과, `any`는 URI와 무관하게 `localName`이 같은 기록과 맞춘다(`:50-56`). `rewrite`는 selector에 `#`도 `[`도 없으면 즉시 원문을 돌려준다(`:191-192`). 브라우저에서는 `refreshSvgSelectorAliases`/`ensureSvgSelectorAliases`가 문서의 `data-hf-svg-reference-aliases`(잘못된 JSON은 무시)와 `[data-hf-authored-id][id]`를 읽어 별칭 표를 만들고, 개명이 하나라도 있으면(`ids`나 `references`가 비어 있지 않을 때) `Element.prototype.querySelector`·`querySelectorAll`을 Proxy로 감싸 인자를 `rewrite`한다(id 별칭은 `:is(#authored, [data-hf-authored-id="authored"])`). 문서에 `<style>`로 남은 prefix attribute selector는 라이브 CSSOM(`@namespace` 규칙이 있는 시트)에서만 고친다. 호출처는 런타임 `init.ts`(4778, 4821행), `entry.ts`(87), `compositionLoader.ts`(949), 그리고 `getSvgSelectorAliasesScript()`로 인라인한 script(`compositionScoping.ts:453`)이다. | 코드 확인 |
| R-29 | `wrapScopedCompositionScript(source, compositionId, errorLabel?, scopeSelectorOverride?, timelineCompositionId?, authoredRootId?, compositionSrc?)`가 서브 컴포지션 인라인 script 하나를 감싼다(인라이너·번들러·브라우저 런타임 `compositionLoader.ts`가 같은 함수를 부른다. `compositionId`는 plan의 `scriptCompositionId`, `timelineCompositionId`는 runtime id) | 반환 문자열은 즉시 실행 함수이고 안에서 순서대로 ① SVG selector 별칭 설치 script(R-28)를 별도 즉시 실행 함수로 실행한다(authored script의 strict mode 밖이고, `window.__hfSvgSelectorAliases`가 이미 있으면 다시 설치하지 않는다). ② 값을 `jsonScriptLiteral`(`JSON.stringify`한 값에서 모든 `<`를 6글자 문자열 `\u003c`로 바꾼 JS 리터럴. `compositionScoping.ts:397-399`)로 넣는다. 그래서 id·label·경로에 `</script>`가 있어도 element가 닫히지 않는다. authored source도 `</script`를 `<\/script`로 바꾼다. ③ 범위 selector `__hfRootSelector`는 `scopeSelectorOverride`(runtime scope)이거나 `[data-composition-id="<id>"]`이다. `compositionId`가 비면 빈 값이라 스코핑을 하지 않는다. ④ `document`, `gsap`, `window`, `__hyperframes`를 같은 이름의 지역 인자로 바꿔 끼운다(`.call(window, ...)`). 바꾼 `document`(Proxy)는 `querySelector`·`querySelectorAll`·`getElementById`만 가로채 결과를 호스트 루트 안 노드로 제한하고(루트가 없으면 전체 문서) 나머지는 원본에 bind한다. selector는 `__hfNormalizeSelector`로 먼저 고친다. 루트 selector 뒤나 앞에 붙은 `[data-start=…]`·`[data-duration=…]` 속성 selector를 떼고, `timelineCompositionId`가 다르면 runtime id 루트 selector도 범위 selector로 바꾸며, SVG 별칭 `rewrite`(원래 루트 `id`는 `[data-hf-authored-id="<id>"]`로)를 적용한다. `getElementById`는 문서 전체에서 찾은 요소가 이 루트 안에 있으면 그것, 아니면 루트 자신(`id` 또는 `data-hf-authored-id` 일치)과 루트 아래의 `data-hf-authored-id`, `#id`, `[id=…]` 순으로 찾는다. ⑤ `window`도 Proxy이다. `window.__timelines`는 레지스트리 Proxy를 돌려준다. `compositionId`와 runtime id가 다르면 `__timelines[<authored id>]` 읽기는 `__timelines[<runtime id>]`로 가고(없을 때만 authored 값), 쓰기는 runtime id에 쓰며 authored id 키에 다른 마운트가 이미 값을 갖고 있지 않을 때만 authored id에도 같은 timeline을 쓴다. `window.__hyperframes`는 아래 ⑥의 scoped 객체이다. `window`의 함수 프로퍼티는 `prototype`이 없는 것(내장 메서드)만 `window`에 bind하고 class·생성자는 그대로 둔다(static 보존). `window.__timelines = <proxy>` 되돌려 쓰기는 무시한다. ⑥ scoped `__hyperframes`는 기본 객체에 `assetUrl(path)`(`compositionSrc`가 있으면 그 파일 기준, 없으면 `document.baseURI` 기준 절대 URL)와 `getVariables()`(`window.__hfVariablesByComp[<runtime id>]`의 복사본, 없으면 `{}`)를 얹은 것이다. 기본 객체가 없으면 그대로 없다. ⑦ `gsap`도 Proxy이다. `timeline()`이 돌려준 timeline의 `to`·`from`·`fromTo`·`set`과 gsap 자신의 같은 네 메서드, `utils.toArray`, `utils.selector`가 첫 인자 selector 문자열(또는 문자열 배열)을 범위 안 요소 목록으로 바꿔 넘긴다. 일치하는 요소가 없으면 빈 배열이고 문자열화하면 원래 selector가 되도록 해서 GSAP 경고 문구를 유지한다. 요소를 이미 넘겼으면 그대로 둔다. ⑧ 실행: `window.__hfScriptState`가 함수이면 `start`·`finish`를 `compositionSrc`(없으면 `"index.html"`)와 함께 부르고, 예외는 `console.error(errorLabel, compositionId, err)`로 잡아 다음 script를 막지 않는다. authored 코드는 `/*hf-authored-begin*/ ... /*hf-authored-end*/` 주석 표지 안에 들어간다. ⑨ 문서에 `meta[name="hf-scene-parts"]`가 있을 때(최초 한 번 `window.__hfSceneAnimations`를 `{}`로 정하고, 없으면 `null`)만 script 실행 전후의 `gsap.globalTimeline` 자식 차이를 runtime id별로 `__hfSceneAnimations`에 기록하고, 실행 중에는 `autoRemoveChildren`을 끈다. 끝난 단일 tween은 timeline에서 제거한다. 기록은 scene swap이 되돌리는 데 쓴다. 관련 export: `scopedModulePrelude(timelineCompositionId, compositionSrc?)`는 `type=module` script 앞에 붙이는 문자열로, 모듈 최상위 `const __hyperframes`(scoped 객체)를 만들고 빈 source로 만든 wrapper를 이어 붙인다. `wrapInlineScriptWithErrorBoundary(source, label)`는 `data-composition-id`가 없을 때 쓰며 `Function(<source>).call(window)`를 try/catch로 감쌀 뿐 스코핑은 없다. `buildVariablesByCompScript`·`emitVariablesByCompScript`는 `window.__hfVariablesByComp = Object.assign({}, 기존, <표>)`를 `<head>` 끝에 `<script>`로 방출한다(없거나 빈 표이면 방출하지 않음). 읽는 쪽(`getVariables`)과 같은 파일에 두어 번들러와 렌더 컴파일러가 같은 빌더를 쓰게 했다(주석이 과거 렌더에서 변수가 빈 값이 된 사고를 이유로 든다). | 코드 확인(생성된 문자열을 브라우저에서 실행하지는 않았다) |

**G. 쓰기 규칙과 입구별 파이프라인**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-23 | `writeClipTiming(attrs, update)` | `start`는 수, `ReferenceExpression`, 또는 `parseStartExpression`이 받아들이는 문자열로 쓴다. 참조는 `<refId>` (offset 0) 또는 `<refId> +\|- <절댓값>` 꼴로 직렬화한다. `duration`은 유한한 0 이상이어야 하고 `null`이면 속성을 지운다. `trackIndex`는 유한한 정수이다. 위반하면 `ClipTimingWriteError(code: invalid-start \| invalid-duration \| invalid-track-index)`를 던진다. 쓴 뒤 `data-end`와 `data-layer`를 지운다. 예외: `data-duration`이 없고 `data-end`만 있으며 읽은 duration이 null(참조 start 때문)이고 이번 update에 duration이 없으면 `data-end`를 지우지 않는다. | 코드 확인 |
| R-24 | `bundleToSingleHtml(projectDir, {entryFile?})` 입구(프리뷰·린트·`validate`·`layout`·inspector) | 진입 파일이 `<template>`만 있는 scene이면 `index.html`이 그것을 마운트하는 모양으로 감싸고, 아니면 그대로 읽는다. 순서: `compileHtml` → `validateHyperframeHtmlContract`(린트 error를 모아 `console.warn("[StaticGuard] ...")`만 하고 번들은 계속한다, `staticGuard:false`이거나 mountedShell이면 생략) → 런타임 interceptor 주입 → 진입 파일이 하위 폴더에 있으면 상대 경로를 프로젝트 루트 기준으로 다시 씀 → 로컬 stylesheet(`<link rel=stylesheet>`)를 `<style>`로 인라인 → `inlineSubCompositions` → 서브 컴포지션 variables·script·link 정리 → `<template id="<id>-template">`와 자식 없는 `data-composition-id="<id>"` 호스트의 인라인 마운트(템플릿 element는 제거) → 로컬 `script[src]`를 인라인 → variables 스타일·모듈 script 방출 → `enforceCompositionPixelSizing`(컴포지션별 `data-width`·`data-height`가 양수이면 `[data-composition-id="id"] { ... }` 블록 안의 `width:100%`, `height:100%`를 px로 바꿈) → `autoHealMissingCompositionIds`(style·script 텍스트가 `data-composition-id="X"`를 참조하는데 그 id의 요소가 없을 때 처리. 세부는 읽지 않음) → head style·body script 병합 → 폰트 로드 뒤로 script 지연 → 텍스트 자산(`src`·`href`·`poster`·`xlink:href`, `srcset`, CSS `url()`, 색보정 LUT)을 data URL로 인라인(`inlineAssets:false`이면 생략) → `assignMediaRenderIds`. 파일은 읽을 뿐 쓰지 않는다. 프로젝트 밖·private 경로는 `isSafePath`로 막는다. 진입 파일이 위 mountedShell(template-only scene)이면 `sourceDir`이 `dirname(진입 파일)`이 아니라 `projectDir`가 되어 `rebaseEntryAuthoredAssetPaths`가 일어나지 않고(`resolve(sourceDir) !== resolve(projectDir)`일 때만 실행) StaticGuard도 건너뛴다(`!mountedShell`, `htmlBundler.ts:1141`). 옵션 `stampHfIds`가 켜지면 번들러가 읽는 진입·서브 컴포지션 HTML에 먼저 `ensureHfIds`(`@hyperframes/parsers/hf-ids`, 내용은 열지 않음)를 적용한다(`:1137`). 옵션 `sceneParts`(프리뷰 전용)가 켜지면 인라이너에 `tagScenes`를 켜서 scene의 host·style·script에 `data-hf-scene`를 달고, 루트 script 텍스트를 따로 모으고, `@font-face`를 hoist한다(`:1181`, `1229`, `1505`). 두 옵션은 호출자가 고른다. | 순서와 위 단계의 동작은 코드 확인. `autoHealMissingCompositionIds`·`coalesceHeadStylesAndBodyScripts`·`createAssetInliner`의 세부는 미확인 |
| R-25 | `compileForRender` 입력 검사·전처리·반환 | 진입 파일이 프로젝트 안에 있으면서 asset root 밖으로 나가면 `Error("Entry file <path> leads outside the project folder")`, 확장자가 `.html`·`.htm`이 아니면 `Error("Entry file <path> is not an .html file, so it is refused")`를 던진다. 통과하면 진입 HTML을 읽고 다음 전처리를 한 뒤 사전 점검(R-17)으로 간다. ① `rebaseDirectEntryAssetPaths`: 진입 파일이 프로젝트 하위 폴더에 있으면(`index.html`이 아니면) 그 경로를 `compSrc`처럼 보고 R-20 규칙으로 `src`·`href`·`srcset`·inline `style`·`<style>`의 경로를 프로젝트 루트 기준으로 바꾼다. ② `rewriteUnresolvableGsapToCdn`: 로컬에서 못 찾는 GSAP 로드를 CDN으로 바꾼다(세부 미확인). ③ `normalizeCompositionSrcs`(R-17). ④ `bindVariableMediaSources`: `data-var-src`가 있는 video/audio에서(`data-variable-values` 호스트 아래는 제외) 선언된 변수 기본값 위에 `options.variables`를 얹어 계산한 값으로 `src`를 바꾼다. 또 `compileHtmlFile`은 media 길이 보정 뒤 `<video>`·`<img>`·`<audio>`의 `crossorigin` 속성을 모두 제거한다(렌더는 영상 프레임을 이미지로 주입하고 오디오는 FFmpeg로 따로 처리하므로 브라우저 CORS가 필요 없다는 코드 주석). 반환: `html`(인라인 완료), `subCompositions`(src → 컴파일된 HTML), `videos`·`audios`·`images`(인라인된 문서에서 `collectRenderMedia`가 읽음), `unresolvedCompositions`(R-10의 `div` 항목), `variablesByComp`, `externalAssets`, `width`, `height`, `staticDuration`, 렌더 힌트. `width`·`height`는 문서에서 첫 `[data-composition-id]` 요소의 `data-width`·`data-height`를 `parseInt`하고 없으면 1080×1920이다. `staticDuration`은 같은 요소의 `data-duration`, 없으면 `data-composition-duration`, 둘 다 없으면 0이다(런타임에 GSAP 길이로 정해질 수 있다). 인라인 때 `assignMediaRenderIds`가 media 요소에 문서 단위로 유일한 render id를 붙인다(요소 `id`는 컴포지션 파일 안에서만 유일하다). | 코드 확인(`rewriteUnresolvableGsapToCdn` 세부만 미확인) |
| R-26 | 두 입구의 관계와 이름이 겹치는 파일 | 호출 경로 기준으로 중복 구현이 아니다. `core/src/compositionContract.ts`, `core/src/mediaTiming.ts`, `core/src/compiler/rewriteSubCompPaths.ts`, `subCompositionValidity.ts`, `assetPaths.ts`, `srcset.ts`는 `@hyperframes/parsers`를 다시 내보내는 얇은 파일이고, 구현은 `packages/parsers/src/`에 한 벌만 있다. `compiler/timingResolver.ts`는 `data-start` 참조와 무관한 TTS 단어 기준 탄성 타이밍이고 이 SHA에서 컴포지션 컴파일 경로가 부르지 않는다. 진짜 중복에 가까운 것은 producer `htmlCompiler.ts`의 `compileHtmlFile`(media 길이 보정)로, 정적 단계는 core `compileTimingAttrs`를 그대로 쓰고 ffprobe 단계만 따로 구현한 것이다. producer의 `inlineSubCompositions`는 core 공용 `inlineSubCompositions`를 감싼 wrapper이다. | 코드 확인 |

- 불변식: `parseStartExpression`은 같은 문자열이면 항상 같은 결과를 낸다(순수 함수). `compileTimingAttrs`는 같은 입력 HTML이면 같은 출력과 같은 `unresolved`를 낸다(시각·난수를 쓰지 않는다). `inlineSubCompositions`는 서브 컴포지션 파일을 읽지 않고 `resolveHtml` 결과만 쓴다. 불변식이 깨지는 곳: media 길이 측정은 파일 시스템과 ffprobe 결과에 의존한다.
- 미결정: 없음. 이전 U-01(SVG id 규칙, wrapper 뒷부분, selector 도구)은 R-27~R-29로 닫았다. 코드를 읽은 결과이고 브라우저 실행은 하지 않았다(확인 한계).

- 확인 한계: 브라우저에서 컴파일 결과를 실행해 보지 않았다. 의존성 설치·빌드·테스트 실행도 하지 않았다. 런타임(`startResolver.ts`)의 결과는 코드를 읽은 것이고 실행하지 않았다. `.clip` CSS 규칙이 어디서 주입되는지는 찾지 않았다(`class="clip"` 의미는 docs 기준이다).

### 1.5 필수 코드 참조 [필수]

라이선스는 Apache-2.0(overview 1절)이고 인용을 허용한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `packages/parsers/src/compositionContract.ts:103-171` `parseNumeric`, `REFERENCE_ID_PATTERN`, `findMagnitudeStart`, `parseReferenceOffset`, `parseStartExpression` | `data-start` 문법. 순서(수 → id 패턴 → offset 참조)가 결과를 정한다 | R-01 |
| C-02 | `packages/parsers/src/compositionContract.ts:182-202`, `218-360` `resolveStart`, `diagnoseDerivedEnd`, `readCanonicalDuration`, `readLegacyEnd`, `readDuration`, `readTrackValue`, `readTrack` | start·duration·end·track 읽기와 diagnostics 코드 | R-02, R-03, R-06, R-07 |
| C-03 | `packages/parsers/src/compositionContract.ts:361-372` `readClipTiming` | 위 읽기 함수의 합성 순서 | R-02~R-07 |
| C-04 | `packages/parsers/src/compositionContract.ts:374-476` `serializeStart`, `writeDuration`, `writeTrack`, `writeClipTiming` | 쓰기 규칙과 오류 코드 | R-23 |
| C-05 | `packages/parsers/src/referenceResolver.ts:18-98` `compositionScopeOf`, `findReferenceTargetEl`, `resolveReferencedStart`, `resolveReferencedDuration` | Node 정적 참조 해석, 대상 찾기 순서, 순환 시 0 | R-04, R-05 |
| C-06 | `packages/core/src/runtime/startResolver.ts:54-69`, `138-170` `findReferenceTarget`, `computeStart`, `resolveStartForElementInternal` | 런타임 참조 해석(참조 부분만. in-point·host 규칙은 행 2) | R-04, R-05 |
| C-07 | `packages/core/src/compiler/timingCompiler.ts:159-218`, `230-271` `withDefaultTimingAttrs`, `compileTag`, `compileTimingAttrs` | media 기본 속성, `data-end` 계산, `unresolved` 수집 | R-08, R-09, R-10 |
| C-08 | `packages/core/src/compiler/timingCompiler.ts:280-361`, `66-91` `injectDurations`, `extractResolvedMedia`, `clampDurations`, `MEDIA_DURATION_CLAMP_EPSILON_SECONDS`, `shouldClampResolvedMediaDuration` | 길이 주입과 audio 길이 보정 | R-12, R-13 |
| C-09 | `packages/core/src/compiler/htmlCompiler.ts:36-101` `compileHtml`, `clampProbedMedia` | core 정적+probe 컴파일 | R-13 |
| C-10 | `packages/parsers/src/subCompositionValidity.ts:39-159` `resolveSubCompositionContent`, `checkSubCompositionUsability` | 내용 선택과 사용 가능 판정 | R-15 |
| C-11 | `packages/parsers/src/rewriteSubCompPaths.ts:38-163` `needsRewrite`, `rewriteAssetPath`, `rewriteAssetPaths`, `rewriteInlineStyleAssetUrls`, `rewriteCssAssetUrls` | 경로 재작성. 사용하는 `isNonRelativeUrl`은 `parsers/src/assetPaths.ts:22-37`, `splitUrlSuffix`·`decodeWellFormedEscapes`·`encodeUrlPath`는 `parsers/src/utils/urlPath.ts`(아래 확인 한계) | R-20 |
| C-12 | `packages/core/src/compiler/compositionAssembly.ts:100`, `222-264`, `289-311` `MAX_SUB_COMPOSITION_DEPTH`, `planCompositionAssembly`, `enumerateNestedCompositionHosts` | 루트 선택, id 규칙, 중첩 순환·깊이 | R-18, R-19, R-21, R-22 |
| C-13 | `packages/core/src/runtime/flattenedRoot.ts:8-32` `FLATTENED_INNER_ROOT_STRIP_ATTRS`, `markFlattenedInnerRoot`, 그리고 `packages/core/src/compiler/htmlBundler.ts:631-642` `prepareFlattenedInnerRoot` | 루트 평탄화 | R-19 |
| C-14 | `packages/core/src/compiler/htmlBundler.ts:533-535`, `553-629` `uniqueCompositionId`, `getBundledTrackedCompositionHosts`, `assignBundledRuntimeCompositionIds` | 중복 마운트 runtime id | R-18 |
| C-15 | `packages/core/src/compiler/inlineSubCompositions.ts:384-799` `inlineSubCompositions` | 호스트 큐 처리 전체 흐름(위 R-14~R-22의 원본) | R-14~R-22 |
| C-16 | `packages/producer/src/services/htmlCompiler.ts:254-264`, `303-389` `normalizeCompositionSrcs`, `assertSubCompositionsUsable`, `EmptyCompositionError`(235-250) | 렌더 사전 점검과 오류 포맷 | R-17 |
| C-17 | `packages/core/src/compiler/svgIdNamespacing.ts:36-38`, `308-347`, `436-471` `sanitizeNamespaceSegment`, `mintNamespacedId`, `collisionScopes`, `planRenames`, `namespaceCollidingSvgIds` | SVG id 새 이름 규칙, keeper 선택, 충돌 판정 | R-27 |
| C-18 | `packages/core/src/compiler/selectorIdTokens.ts:195-232`, `255-262`, `322-350` 및 `svgSelectorAliases.ts:21-92`, `95-136`, `148-257` `replaceSelectorIdTokens`, `escapeCssAttributeValue`, `parseAttributeSelector`, `replaceSelectorAttributeTokens`, `rewriteSvgSelectors`, `readSvgReferenceAliases`, `installSvgSelectorAliases` | selector 토큰 치환과 개명 별칭 표, 브라우저 `querySelector` 패치 | R-28 |
| C-19 | `packages/core/src/compiler/compositionScoping.ts:397-475`, `476-766`, `768-807` `jsonScriptLiteral`, `SCOPED_HYPERFRAMES_EXPRESSION`, `scopedModulePrelude`, `wrapScopedCompositionScript`(앞부분 429-475, 뒷부분 476-766), `wrapInlineScriptWithErrorBoundary`, `buildVariablesByCompScript`, `emitVariablesByCompScript` | script wrapper의 Proxy 구성(document·window·gsap)과 변수 표 방출 | R-29 |

- 확인 한계(C-11): `splitUrlSuffix`, `decodeWellFormedEscapes`, `encodeUrlPath`(`parsers/src/utils/urlPath.ts`)와 `parsers/src/cssUrlScans.ts`의 `cssUrlMatches`는 열지 않았다. 재구현자는 이름 그대로 "쿼리·해시 접미사 분리", "퍼센트 이스케이프 해독", "경로 재인코딩"으로 읽되 세부는 확인이 필요하다. 필요하면 U-ID로 승격한다.

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출. 원본 테스트 파일은 열지 않았다. 실행은 하지 않았고 코드 경로를 따라 기대값을 계산했다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | `parseStartExpression` 입력 `"intro - 0.5"`, `"intro+0.5"`, `"intro"`, `"intro-0.5"`, `"1e3"`, `"-3"`, `"a + 1 + 2"`, `""` | reference(intro, −0.5), reference(intro, +0.5), reference(intro, 0), reference(refId `intro-0.5`, 0), absolute 1000, absolute −3, null, null |
| T-02 | R-03 | `readClipTiming`에 `data-start="-3" data-duration="2"` | `start=0`, `end=2`, diagnostics 없음 |
| T-03 | R-03, R-04 | `<video id="intro" data-start="0" data-duration="4">`와 `<section id="result" data-start="intro - 0.5" data-duration="3">`. `readClipTiming(result, {resolveReferenceEnd: id => id==="intro" ? 4 : null})` | `start=3.5`, `end=6.5`. 콜백이 없으면 `start=null`, `unresolved-start-reference` |
| T-04 | R-04 | A의 `data-start="B + 1"`, B의 `data-start="A + 2"`(둘 다 `data-duration` 없음, 같은 컴포지션). 전제: 새 resolver에서 A를 먼저 푼다 | 런타임 `resolveStartForElement(A, 5)`는 B=2, A=3이다(5가 아니다). B를 먼저 풀면 A=1, B=3이다(R-04의 `startCache`). 정적 `resolveReferencedStart(doc, A, ...)`도 B=2, A=3이다(순환 고리에서 0). `parseHtml`/`readClipTiming` 경로는 두 요소 모두 `start`가 null이라 0으로 채운다. 어느 경로도 예외를 던지지 않는다 |
| T-05 | R-06 | `data-start="1" data-duration="2" data-end="9"` | `end=3`, `deprecated-end`와 `conflicting-end`. `data-end="3"`이면 diagnostics 없음 |
| T-06 | R-07 | `data-track-index="1.5"`, `data-layer="2"` | `trackIndex=0`(출처 `invalid`). diagnostics는 `invalid-track-index`, `deprecated-layer`, `conflicting-layer` 순서이다. layer 2가 무효 처리된 track 값 0과 다르기 때문이다 |
| T-07 | R-08, R-09 | `<video src="a.mp4" muted></video>`를 `compileTimingAttrs`에 입력 | `id="hf-video-0"`, `data-start="0"`, `data-hf-auto-start=""`, `data-has-audio="false"`가 들어가고, `data-duration`이 없어 `unresolved`에 `{id:"hf-video-0", tagName:"video", src:"a.mp4", start:0, ...}` 한 건 |
| T-08 | R-09, R-10 | `<audio id="m" data-start="intro" data-duration="5">`와 `<div id="s" data-start="0">` | audio에는 `data-end`가 안 생기고 `unresolved`에도 없다. div는 `unresolved`에 `{id:"s", tagName:"div", start:0}`로 들어가고 속성은 바뀌지 않는다 |
| T-09 | R-13 | audio `data-duration="10"`, 파일 길이 6초, `data-playback-start` 없음, prober 주입 | `data-duration="6"`, `data-end`는 `start + 6`. 같은 값의 video이면 그대로 10 |
| T-10 | R-15, R-17 | `index.html`에 `data-composition-src="compositions/a.html"`가 있고 `a.html`이 빈 파일 | 렌더: 컴파일 시작 전에 `EmptyCompositionError`, 메시지에 `  - compositions/a.html: the file is empty (0 bytes or whitespace-only)`. 프리뷰 번들: 던지지 않고 `[Bundler] Skipping sub-composition "compositions/a.html": the file is empty ...` warn |
| T-11 | R-20 | `compositions/scene.html` 안의 `<img src="../assets/logo.png">`와 `<link href="_shared.css">`(파일 `compositions/_shared.css` 존재) 및 `<img src="assets/x.png">`(프로젝트 루트 `assets/x.png`만 존재), `assetExists` 주어짐 | `src="assets/logo.png"`, `href="compositions/_shared.css"`, `src="assets/x.png"`(`compositions/assets/x.png`가 없으므로 그대로) |
| T-12 | R-18, R-19 | 호스트 둘이 같은 `card.html`(루트 `data-composition-id="card"`)을 마운트하고 호스트에 id가 없다 | 호스트에 id가 없으면 R-18의 id 부여가 일어나지 않고, 평탄화한 루트에 `data-composition-id="card"`가 되돌려진다. 호스트 둘이 모두 `data-composition-id="card"`를 가지면 `card__hf1`, `card__hf2`가 되고 `data-hf-original-composition-id="card"`가 붙는다 |
| T-13 | R-21 | `a.html`이 `data-composition-src="a.html"`를 자기 안에 가진다 | 첫 인라인 후 중첩 호스트 `src="a.html"`이 조상 목록에 있어 `circular composition reference`로 건너뛰고 경고만 낸다. 렌더 사전 점검은 오류 없이 통과한다(순환 파일 반복은 조용히 건너뜀) |
| T-14 | R-25 | 루트 `<div data-composition-id="root">`에 `data-width`가 없고 `data-duration="12"` | `width=1080`, `height=1920`, `staticDuration=12` |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repo@5979991 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 | 코드를 따라 손으로 계산. `Number()` 의미(`1e3`, `0x10`, 공백 허용)는 JS 표준 동작이라 별도로 실행하지 않음. 문법 설명 주석(`compositionContract.ts:151-155`)과 docs는 `clip-id +/- offset`만 말하고 공백 없는 `intro-0.5`가 id가 되는 점은 쓰지 않았다. 구현을 사실로 썼다 |
| R-02, R-03 | C-02, C-03 `resolveStart` 182-202 | 코드 확인 |
| R-04 | C-05, C-06, `parsers/src/htmlParser.ts:205-232`, `core/src/runtime/startResolver.ts:96-110`(`resolveDurationForElement`) | 세 해석기를 비교했다. (a)와 (b)의 차이는 코드 비교로 확인했고, 실제 렌더에서 두 값이 어긋나는 사례는 실행해 보지 않았다. T-04의 값은 코드를 따라 손으로 계산했다(메인 검토자도 같은 값을 확인). 컴파일이 media 길이를 `data-duration`으로 채워 (b)도 길이를 알게 된다는 설명은 추론이다 |
| R-05 | C-05 `findReferenceTargetEl`, C-06 `findReferenceTarget`, `studio/src/player/lib/timelineIframeHelpers.ts:338-349`, `sdk/src/session.ts:405-428`, `studio-server/src/helpers/previewAdapter.ts:140-160` | docs(`data-attributes.mdx`, `html-schema.mdx`의 "같은 composition 안")와 구현이 다르다. 구현은 같은 컴포지션 안을 먼저 보고 못 찾으면 문서 전체 `id`, `data-composition-id` 순으로 넓힌다. docs의 "참조 대상은 길이를 알아야 한다"도 엄밀하지 않다. 길이를 모르면 에러 없이 길이 0으로 계산한다(R-04). docs의 "순환은 금지"를 코드로 막는 곳은 찾지 못했다. 검색: `grep -rn "visiting" --include=*.ts --include=*.tsx --exclude=*.test.ts packages`(SHA 5979991)에서 start 참조를 다루는 순환 방어는 `startResolver.ts:47,162`, `referenceResolver.ts:48-52`, `htmlParser.ts:211-215`(id 집합), `sdk/src/session.ts:410-426`, `studio-server/.../previewAdapter.ts:142-155`, `studio/.../timelineIframeHelpers.ts:357-364`였고 모두 에러 없이 값을 0·null·fallback으로 돌린다(그 밖의 `visiting`은 media 목록, 레지스트리 의존 해석 등 무관). 서브 컴포지션 파일 순환은 별개 규칙이다(R-21, `lint/src/project.ts:1005`의 `visited`). 린트가 start 참조를 규칙으로 검사하는지는 행 7이며 `grep "unresolved-start-reference\|invalid-start" lint/src`에서는 결과가 없었고, 린트는 `readClipTiming`을 `rules/composition.ts:89`, `rules/structure.ts:182,210,213`에서 직접 부른다. 다른 어휘로 쓴 규칙은 놓쳤을 수 있다 |
| R-06 | C-02 `diagnoseDerivedEnd` 235-260, `readCanonicalDuration`, `readLegacyEnd`, `readDuration` | 코드 확인. 반면 `compileTag`는 음수 `data-duration`을 수로 받는다(`parseStrictFiniteTimingNumber`는 `parseNumeric`이고 음수를 거르지 않음) |
| R-07 | C-02 `readTrack` 329-359, `readTrackValue` 315-327 | 코드 확인 |
| R-08~R-10 | C-07 | 코드 확인. 파일 머리 주석(`timingCompiler.ts:6-9`)은 "모든 timed element가 `data-end`를 갖는다"고 쓰지만 구현은 video/audio만 쓴다(R-10). 구현을 사실로 썼다 |
| R-11 | `core/src/runtime/timeline.ts:146-153`(`parseAuthoredTrack`), `:429`(`CLIP_NODES`), `:697-700` 주석("Track index is display-only; render never reads it"), `core/src/runtime/picker.ts:239-240`, `core/src/runtime/playbackRate.ts:74-80`(`resolveTimedImageDurationSeconds`), `parsers/src/htmlParser.ts:91-100`(`getZIndex`), `engine/src/services/audioMixer.ts:626,641`, docs `data-attributes.mdx:20-22,29-33`, `html-schema.mdx:100-103` | 부재 주장. 검색: `grep -rn "track-index\|trackIndex\|data-layer" --include=*.ts --exclude=*.test.ts core/src/runtime producer/src engine/src`(SHA 5979991). 위 파일들이 전부였고 `producer/src`·`engine/src`에서 `data-track-index`는 읽히지 않았다. 놓칠 수 있는 곳: 변수로 속성 이름을 조립하는 동적 접근, `packages/player`·`studio`·`sdk`(편집·재생 쪽이라 렌더 경로에서 의도적으로 제외), `runtime/init.ts`가 6.9천 줄이라 `data-track` 별칭 사용처까지는 전부 읽지 않았다. 따라서 "렌더가 `data-track-index`를 무시한다"는 docs 주장은 코드로 확인되었고 단 하나의 예외(`<img>`의 timed 판정, R-11)를 docs가 적지 않는다 |
| R-12 | C-08 `injectDurations` 280-304 | 코드 확인. id가 같은 태그는 모두 바뀐다(`replaceIdTags`는 첫 번째에서 멈추지 않음) |
| R-13 | C-08, C-09, `producer/src/services/htmlCompiler.ts:569-704`(`resolveMediaDuration`, video 실패 throw는 `:683-684`), `:704-719`(`markInferredVariableMediaDurations`), `:721-846`(`compileHtmlFile`, 2단계 `:774-797`) | 코드 확인. core는 `playbackRate`를 쓰지 않고 producer는 쓴다. 이 차이가 프리뷰와 렌더의 media 길이에 영향을 주는지는 실행해 보지 않았다 |
| R-14 | C-15 `inlineSubCompositions.ts:711-731`, `765-777`; producer `htmlCompiler.ts:1118-1260`(host 크기 style 반복문은 공용 인라이너 호출 뒤, 초기 `hosts`만 대상) | 코드 확인 |
| R-15, R-16 | C-10, `inlineSubCompositions.ts:457-499` | 코드 확인. 프리뷰 번들러는 의도적으로 관대하다(파일 헤더 주석 `subCompositionValidity.ts:1-37`) |
| R-17 | C-16 | 코드 확인. 사전 점검은 `compileForRender`가 `rawHtml`에 대해 호출한다(`htmlCompiler.ts:2232`). 오류 문구는 코드에서 그대로 옮겼다 |
| R-18 | C-14, `core/src/compiler/compositionAssembly.ts:312-319`(`countPageRoot`), `htmlBundler.ts:553-571`, `:585-629`, producer `htmlCompiler.ts:991-1038`(`ProducerHostIdentityMap`), `:1126-1128`(초기 호스트 선택) | 코드 확인. `countPageRoot` 효과는 코드를 따라 계산했고 실행하지 않았다 |
| R-19 | C-13, `inlineSubCompositions.ts:733-764` | 코드 확인 |
| R-20 | C-11 | 코드 확인. `resolve("/", ...)`로 루트 위 `..`가 잘리는 동작은 POSIX `path.resolve` 의미로 추론했다(실행 없음). 보조 함수는 열지 않았다(1.5 확인 한계) |
| R-21 | C-12, `inlineSubCompositions.ts:765-777`, producer `htmlCompiler.ts:338-340`(사전 점검의 순환 skip), `:849-946`(`parseSubCompositions`, `visited` 집합) | 부재 주장("예외를 던지지 않는다")은 위 두 파일의 `throw` 없음과 `onMissingComposition` 경로로 확인. 검색 범위는 `core/src/compiler`와 `producer/src/services/htmlCompiler.ts`. 문자열 비교의 결과는 추론이다 |
| R-22 | C-15의 호출 구조, `core/src/compiler/compositionScoping.ts:60-170`(selector 스코핑, `:105` html·body·:root 치환), `:166`(`GLOBAL_AT_RULES` = keyframes·-webkit-keyframes·font-face), `:219-222`(postcss 파싱), `:314`(파싱 실패 시 빈 문자열) | 위 줄을 직접 읽어 확인(메인 재확인 2026-11-17: postcss·GLOBAL_AT_RULES·html/body/:root·파싱 실패 빈 문자열). SVG id와 wrapper 세부는 R-27~R-29의 근거 행 참고. `scopeSelector` 계열 내부 분기(60-170행)는 개념 수준만 확인했다 |
| R-27 | C-17, `core/src/compiler/svgIdNamespacing.ts:1-538` 전체, 호출부 `inlineSubCompositions.ts:772-841`(scope 구성, CSS 재작성), `core/src/runtime/compositionLoader.ts:895-949`(`namespaceMountedSvgIds`) | 파일 전체를 읽었다. 테스트 파일은 열지 않았고 이름 검색도 하지 않았다. 새 id 형식의 예(`card--clip`, 충돌하면 `card--clip-2`)는 코드를 따라 계산했고 실행하지 않았다. `svgIdNamespacing.ts:140-146`의 `namespace` 주석은 빈 namespace를 anonymous 호스트라고 설명하지만 호출 코드(`inlineSubCompositions.ts:510`, `784`)에서 anonymous 호스트의 namespace는 루트 선언 id이다. 빈 문자열은 최상위 문서 scope에만 확실히 쓰이므로 구현을 사실로 썼다. producer는 `namespaceCollidingSvgIds`를 직접 부르지 않고 공용 인라이너를 거친다(검색: `grep -rn namespaceCollidingSvgIds --include=*.ts --exclude=*.test.ts packages`, SHA 5979991, 호출처는 `inlineSubCompositions.ts`와 `compositionLoader.ts` 두 곳). 번들러가 `<template id="<id>-template">` 호스트를 펼치는 자체 경로(`htmlBundler.ts:1335-1402`)는 이 함수를 부르지 않는다(그 마운트의 SVG id는 브라우저 `compositionLoader`가 처리하는지까지는 확인하지 못했다). 즉 컴파일 단계의 id 개명은 `inlineSubCompositions`가 처리한 호스트에만 일어난다 |
| R-28 | C-18, 호출처 검색: `grep -rn "selectorIdTokens\|svgSelectorAliases\|refreshSvgSelectorAliases" --include=*.ts --exclude=*.test.ts packages`(SHA 5979991) | `selectorIdTokens.ts` 195-350행(id 토큰 치환, attribute selector 해석)과 `svgSelectorAliases.ts` 전체를 읽었다. `selectorIdTokens.ts` 1-194행(CSS 식별자 해독·`CSS.escape` 구현)은 주석과 함수 이름까지만 읽었다. wrapper에 인라인되는 `generated/svg-selector-aliases-inline.ts`는 이 파일을 번들한 문자열이고 열지 않았다(`packages/core/scripts/build-svg-selector-aliases.ts`가 생성하고 `stubs/svg-selector-aliases-entry.ts`가 `ensureSvgSelectorAliases()`를 부른다). 브라우저 동작은 실행하지 않았다 |
| R-29 | C-19, 호출부 `inlineSubCompositions.ts:645-675`, `htmlBundler.ts:1039-1066`, `compositionLoader.ts:636-655`, `compositionAssembly.ts:245-246`(`scriptCompositionId`·`authoredRootId`), `packages/core/src/sceneParts.ts:5`(`SCENE_PARTS_META = "hf-scene-parts"`) | `compositionScoping.ts` 397-807행을 읽었다. 호출부 인자는 3곳이 같지 않다. 번들러가 `<template>` 호스트를 자체 경로로 펼칠 때(`htmlBundler.ts:1361`, `1398`의 `hoistCompositionScripts`)는 `compositionSrc`를 넘기지 않아 그 경로에서는 `assetUrl`이 `document.baseURI` 기준이고 `__hfScriptState`의 이름은 `"index.html"`이 된다. 인라이너(렌더·프리뷰의 `inlineSubCompositions`)는 `src`를 넘기고, 브라우저 런타임은 `params.compositionUrl?.href`를 넘긴다. 이 wrapper를 실행해 본 적은 없고 문자열 템플릿을 읽은 결과이다("예외는 잡아 다음 script를 막지 않는다" 같은 동작은 코드 구조 기준) |
| R-23 | C-04 | 코드 확인 |
| R-24 | `core/src/compiler/htmlBundler.ts:1071-1210`, `1291-1465`, `1476-1545`(후반 단계), `:644-678`(`enforceCompositionPixelSizing`), `staticGuard.ts:1-45`, `cli/src/server/studioServer.ts:565-570`(프리뷰), `cli/src/commands/{validate,layout,compare,grade-compare,motionShot}.ts`, `inspector/src/service.ts:196` | 입구별 호출은 `grep -rn "bundleToSingleHtml(" --include=*.ts --exclude=*.test.ts packages`(SHA 5979991)로 찾았다. 후반 단계는 줄을 훑어 순서와 동작을 적었고 `autoHealMissingCompositionIds` 이후 보조 함수 내부는 열지 않았다 인라인 템플릿 컴포지션(`<template id="<id>-template">` + 빈 `data-composition-id` 호스트)은 렌더 경로 컴파일(`compileForRender`)이 펼치지 않고 브라우저 런타임이 마운트한다. 근거와 호출 조건은 [runtime-seek.md](./runtime-seek.md) R-10과 2.1(`init.ts:1204-1222`, `compositionLoader.ts`의 `mountInlineTemplateCompositions`, 메인 재확인 2026-11-17) |
| R-25 | `producer/src/services/htmlCompiler.ts:2207-2514`, 전처리 `:2147-2200`(`rebaseDirectEntryAssetPaths`, `bindVariableMediaSources`), `:2220-2224`, crossorigin 제거 `:819-834`; 호출처 `producer/src/services/render/stages/compileStage.ts`(주석에 `compileForRender` 실행 명시) | 코드 확인. 단계 5의 후처리는 범위 밖이라 이름만 적었다. `rewriteUnresolvableGsapToCdn` 세부는 열지 않았다 |
| R-26 | `core/src/compositionContract.ts:1`, `core/src/mediaTiming.ts:1-2`, `core/src/compiler/{rewriteSubCompPaths,subCompositionValidity,assetPaths,srcset}.ts`, `core/src/compiler/timingResolver.ts:1-25`, `core/src/compiler/index.ts:1-12` | 부재 주장("중복 구현이 아니다", "컴포지션 컴파일 경로가 부르지 않는다"). 검색: `grep -rn "resolveTimings\|timingResolver" --include=*.ts packages`(SHA 5979991). 결과는 `core/src/compiler/index.ts`·`core/src/index.ts` 재내보내기, 테스트, 그리고 `core/src/runtime/init.ts`의 `timingResolverFor`였다. `init.ts` 쪽은 이름이 같은 로컬 변수이고(`createRuntimeStartTimeResolver`의 래퍼) `resolveTimings`를 부르지 않았다. `timingResolver.ts` 자체 주석도 "NOT YET WIRED"라고 쓴다. feature map이 이 파일을 "타이밍 해석"의 진입점으로 적었으나 `data-start` 참조 해석과 관련이 없다. 동적 import·문자열 조립 호출은 놓쳤을 수 있다 |
| 문서 차이 | `docs/reference/html-schema.mdx:99`, `:82-91`; `producer/src/services/htmlCompiler.ts:2488-2492` | `html-schema.mdx:99`는 DOM·서브 컴포지션 clip의 `data-duration`을 필수(Yes)로 쓰지만 구현에는 필수 검사가 없다. `compileTimingAttrs`는 길이 없는 media와 `div`·`section`을 `unresolved`에 모으고(R-09, R-10), 런타임은 길이를 못 구하면 0으로 계산한다(R-04). 루트 `data-duration` 설명(`:82-91`)은 "명시한 값이 렌더 길이"라고 하는데, `compileForRender.staticDuration`은 `data-duration` 다음에 `data-composition-duration`도 fallback으로 읽는다(R-25). `html-schema.mdx`에는 이 속성 설명이 없고 catalog 예제(`docs/catalog/components/*.mdx`)에서만 쓰인다(검색: `grep -rn data-composition-duration docs`). 구현을 사실로 썼다 |
| T-01~T-14 | 각 R-ID 근거 | 모두 코드를 읽고 손으로 계산한 기대값이다. 실행하지 않았다. T-06의 `conflicting-layer`는 `parseNumeric(rawLayer)=2`가 `canonical.trackIndex=0`과 다르므로 남는다 |

### 2.2 코드 읽는 순서 [선택]

1. 속성 계약부터: `parsers/src/compositionContract.ts`(`parseStartExpression` → `readClipTiming`). 나머지 파일은 모두 이 읽기 결과나 같은 문법을 쓴다.
2. 정적 컴파일: `core/src/compiler/timingCompiler.ts`의 `compileTimingAttrs`, `core/src/compiler/htmlCompiler.ts`의 `compileHtml`.
3. 서브 컴포지션: `core/src/compiler/compositionAssembly.ts`(결정 규칙) → `inlineSubCompositions.ts`(큐 루프, 384행부터) → `parsers/src/subCompositionValidity.ts`, `rewriteSubCompPaths.ts`.
4. 입구: 렌더 `producer/src/services/htmlCompiler.ts`의 `compileForRender`(2207행), 프리뷰 `core/src/compiler/htmlBundler.ts`의 `bundleProject`(1100행).
5. 참조 해석은 소비자 쪽: `parsers/src/referenceResolver.ts`, `core/src/runtime/startResolver.ts`(행 2).

### 2.3 비교·재사용 출처 [선택]

없음. 다른 레포의 같은 기능 스펙은 만들지 않았다.

### 2.4 검토 기록 [필수, ready 스펙]

- 방식: 독립 검토 2회와 메인 점검. 2026-11-17.
  - 1차 독립 검토(읽기 전용 서브에이전트): R-01~R-26과 T-01~T-14 전체를 원본 코드와 대조했다. 불일치(R-04 순환 의미, R-13 producer 분리, R-18 번들러·producer 분리, T-04)와 누락(R-25 전처리 등)은 작성자가 반영했다. 이 과정에서 1.4 행이 근거 문장으로 덮어써진 사고가 있어 복원했다.
  - 2차 독립 검토(별도 서브에이전트, 1차 이후 바뀐 부분 중심): R-04, R-05, R-08~R-10, R-12~R-14, R-18, R-20, R-22, R-24, R-25, R-27~R-29와 T-04, T-12, T-14를 대조했고 표본으로 R-01, R-03, R-17, R-21을 확인했다. 선행·후행 링크(runtime-seek, audio-mix-fx, lint-check, render-orchestration)의 R-ID 번호와 의미가 맞는지도 봤다. 서술 오류 4건(R-27 namespace 문장, R-29 `<` 오기, R-04 `fallback` 조건, R-13 `mediaStart` 이상일 때 producer 동작)과 보강 사항은 작성자가 반영했다.
  - 메인 점검: 표 칸 수와 R-ID 집합 일치를 스크립트로 확인했고, R-04(`startResolver.ts:138-146`), R-27(`inlineSubCompositions.ts:510`, `svgIdNamespacing.ts:322` keeper), R-29(`compositionScoping.ts:397-399`)와 `check.py`를 확인했다.
- 대조한 R-ID: R-01~R-29 전부(R-01~R-26은 1차, R-04·R-05·R-08~R-10·R-12~R-14·R-18·R-20·R-22·R-24·R-25·R-27~R-29는 2차). 결과는 일치 또는 불일치 후 수정이다.
- 대조하지 않은 부분: 2차 검토 후 작성자가 추가한 보강 문장(R-04 호출 순서 의존, R-13 core와 producer의 0 길이 처리, R-20 `poster`·`xlink:href` 제외, R-22 `@media` 안 rule, R-24 mountedShell, R-28 attribute selector의 any, R-27 같은 scope 안 중복)은 작성자가 코드를 다시 열어 반영했고 별도 검토자는 재대조하지 않았다. `ensureHfIds`와 `urlPath` 보조 함수의 내용은 열지 않았다. 브라우저에서 wrapper와 별칭 Proxy를 실행해 보지 않았다.
- 재구현: 미수행.

## 적용 메모 [선택]

없음. 이 스펙은 원본 동작만 쓴다.
