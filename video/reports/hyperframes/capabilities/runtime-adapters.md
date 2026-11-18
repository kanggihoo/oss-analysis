---
sha: "5979991d5f0af542fbb02ba906bdba4de52b2b64"
created: 2026-11-17
updated: 2026-11-17
sources:
  - packages/core/src/runtime/types.ts
  - packages/core/src/runtime/init.ts
  - packages/core/src/runtime/state.ts
  - packages/core/src/runtime/entry.ts
  - packages/core/src/runtime/window.d.ts
  - packages/core/src/runtime/diagnostics.ts
  - packages/core/src/runtime/clipWindow.ts
  - packages/core/src/runtime/frameSources.ts
  - packages/core/src/runtime/adapters/_holdAnimationAt.ts
  - packages/core/src/runtime/adapters/_readiness.ts
  - packages/core/src/runtime/adapters/animejs.ts
  - packages/core/src/runtime/adapters/css.ts
  - packages/core/src/runtime/adapters/d3.ts
  - packages/core/src/runtime/adapters/google-maps.ts
  - packages/core/src/runtime/adapters/gsap.ts
  - packages/core/src/runtime/adapters/gsapAuthoredOrder.ts
  - packages/core/src/runtime/adapters/leaflet.ts
  - packages/core/src/runtime/adapters/lottie.ts
  - packages/core/src/runtime/adapters/mapbox.ts
  - packages/core/src/runtime/adapters/maplibre.ts
  - packages/core/src/runtime/adapters/seek-dispatch.ts
  - packages/core/src/runtime/adapters/three.ts
  - packages/core/src/runtime/adapters/typegpu.ts
  - packages/core/src/runtime/adapters/video-texture-compat.ts
  - packages/core/src/runtime/adapters/waapi.ts
  - packages/core/src/adapters/types.ts
  - packages/core/src/adapters/gsap.ts
  - packages/core/src/index.ts
  - docs/concepts/frame-adapters.mdx
  - docs/concepts/determinism.mdx
  - skills/hyperframes/references/runtimes.md
depends:
  - ./runtime-seek.md
status: draft
---

# 런타임 어댑터 패밀리

> 컴포지션이 쓰는 애니메이션 방식(GSAP, CSS, WAAPI, Anime.js, Lottie, Three.js, TypeGPU 등)마다 "시각 t의 상태로 정지"시키는 변환 코드를 `RuntimeDeterministicAdapter` 계약으로 묶고, 런타임이 이 어댑터 13개를 등록 순서대로 불러 seek와 ready 게이트를 처리하게 하는 기능이다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

어댑터가 언제 어떤 순서로 불리는지(`discover`, `seek`, `pause`, `play`, `revert`, `getReadyPromise`)는 [runtime-seek.md](./runtime-seek.md)의 R-08, R-09, R-20, R-21과 1.3.6이 다룬다. 이 스펙은 그 호출을 받는 쪽의 변환 규칙을 쓴다.

1. 런타임 init이 어댑터 13개를 고정 순서로 만든다(R-31). 외부에서 어댑터를 추가하는 공개 API는 없다(R-32).
2. `runAdapters("discover")`가 어댑터마다 `discover()`를 부르고 곧바로 같은 어댑터에 `seek({time, suppressEvents: true})`를 부른다(R-02). 각 어댑터는 자기 방식의 인스턴스(CSS 요소, WAAPI `Animation`, `window.__hfLottie` 배열 등)를 모은다.
3. `maybePublishRenderReady`가 어댑터 `getReadyPromise()`를 모아 하나라도 settle 전이면 `window.__renderReady`를 false로 둔다(R-06). 이 게이트로 Three.js 로더, 지도 `load`, D3 transition, frame source 준비를 기다린다.
4. seek 패스는 루트 timeline과 scene timeline을 먼저 맞추고, 이어서 어댑터를 등록 순서대로 `seek({time, suppressEvents, pageAnimations})`한다. 어댑터는 t를 자기 방식의 API로 바꾼다(R-09). CSS와 WAAPI는 `Animation.currentTime`, Anime.js는 `instance.seek(ms)`, Lottie는 `goToAndStop`, Three.js와 TypeGPU는 `window.__hf…Time` 전역과 `hf-seek` 이벤트다.
5. seek 패스 끝에서 `runAdapters("pause")`가 모든 어댑터를 멈춘다. 재생을 시작할 때만 `runAdapters("play")`를 부른다(R-13).
6. 렌더러는 `__hfWaitForSeekCompletion`으로 `hf-seek` 리스너와 frame source가 등록한 비동기 작업이 끝나길 기다린 뒤 화면을 캡처한다(R-25).

### 1.2 범위·통합 지점 [필수]

- 제공: 어댑터 인터페이스 `RuntimeDeterministicAdapter`의 멤버별 계약, 방식별 변환 규칙, 어댑터가 읽는 전역·등록 배열(`window.__hfLottie` 등), 등록 순서, 공개 인터페이스 `FrameAdapter`와의 관계.
- 제외(이유):
  - 어댑터가 불리는 순서와 시점(init, seek 패스, transport)은 [runtime-seek.md](./runtime-seek.md)다. 여기서는 그 호출을 받는 어댑터 쪽 동작만 쓴다.
  - `FrameAdapter`(`packages/core/src/adapters/`)의 구현 세부는 경계만 쓴다(R-35).
  - Studio와 편집 UI 코드는 행 10 몫이라 읽지 않았다. `settleChangedScenes`가 프리뷰의 scene 교체 때 `discover`를 부르는 위치만 R-02에 적는다.
  - `video-texture-compat.ts`는 `RuntimeDeterministicAdapter`가 아닌 GPU 업로드 패치라 R-34에 경계만 쓴다.
  - frame source의 등록 API(`window.__hyperframes.registerFrameSource`)와 `render` 콜백 작성법은 `docs/guides/frame-sources.md`가 다루는 별도 기능이라 열지 않았다. 어댑터로서의 동작만 R-28에 쓴다.
  - 어댑터가 읽는 외부 라이브러리(GSAP, lottie-web, Three.js, Mapbox 등)의 내부 동작은 열지 않았다. 해당 라이브러리 메서드를 어떤 인자로 부르는지만 쓴다.
- 외부 의존·선행 계약: 선행 스펙은 [runtime-seek.md](./runtime-seek.md)(호출 시점, ready 게이트, 예외 삼킴, 길이 floors). 컴포지션 작성자는 방식에 따라 전역을 채워야 한다. Lottie는 `window.__hfLottie`, Anime.js는 `window.__hfAnime`, D3는 `window.__hfD3`, 지도는 `window.__hfLeaflet`·`__hfMapbox`·`__hfMaplibre`·`__hfGoogleMaps`다. Three.js는 `window.THREE`, GSAP는 루트 timeline 등록(runtime-seek R-06)이다.
- 소유 상태·부작용: 어댑터 인스턴스는 런타임이 `state.deterministicAdapters`에 소유한다(teardown 때 비움, R-33). 어댑터별 상태는 클로저 안에 있다(CSS 요소 목록, WAAPI baseline, readiness promise, `hf-seek` 마지막 시각 등). 페이지에는 `window.__hfThreeTime`, `window.__hfTypegpuTime`, `animation-delay`·`animation-play-state` inline style(CSS fallback), `Element.prototype.animate` 래퍼(WAAPI), `window` 이벤트 `hf-seek`를 남긴다.

### 1.3 인터페이스와 데이터 의미 [필수]

#### 1.3.1 `RuntimeDeterministicAdapter`

타입 정의는 `types.ts:412-462`(C-01)다. 아래는 멤버별 계약이다.

| 멤버 | 입력·출력 | 의미·제약 |
|---|---|---|
| `name` | string(필수) | 식별자. 런타임이 이름으로 분기하는 것은 `"gsap"` 하나뿐이다(R-03). 이름은 중복 검사를 받지 않는다 |
| `discover()` | 없음 → void(필수) | 현재 DOM·전역에서 이 어댑터가 다룰 인스턴스를 (다시) 찾는다. 여러 번 불려도 안전해야 한다(R-05). 반환값은 쓰지 않는다 |
| `seek(ctx)` | `{time: number(초), suppressEvents?: boolean, pageAnimations?: () => Animation[]}` → void(필수) | 어댑터가 다루는 인스턴스를 시각 `time`의 상태로 정지시킨다. `time`은 어댑터마다 클램프하지 않은 원래 값이다. `pageAnimations`는 한 패스 안에서 `document.getAnimations()`를 한 번만 부르게 하는 공유 getter다(R-08) |
| `pause(ctx?)` | `{pageAnimations?}` → void(필수) | 인스턴스가 스스로 흘러가지 않게 멈춘다. 모든 seek 패스 끝과 재생 정지 때 불린다 |
| `play?()` | 없음 → void | 재생 시작 때만 불린다. 어댑터 13개 중 일부만 구현한다(1.3.3 표) |
| `revert?()` | 없음 → void | 런타임 teardown 때 한 번. 어댑터가 건 후크와 타이머를 정리한다(R-33) |
| `getReadyPromise?()` | 없음 → `PromiseLike<unknown>` 또는 null | 비동기 준비가 남았으면 promise, 없으면 null. 같은 대기에는 같은 promise를 돌려주는 것이 계약이다(R-06) |
| `getInferredDurationSeconds?()` | 없음 → number 또는 null | 이 어댑터가 발견한 애니메이션의 가장 늦은 끝(초). 유한한 양수만 컴포지션 길이 floor에 반영된다(R-07) |
| `getAnimationCycleEndSeconds?()` | 없음 → number 또는 null | 한 사이클 끝 시각. `__hf.animationEnd()` 계산에만 쓰인다(R-07) |

#### 1.3.2 정지(hold)의 공통 원리

런타임은 시각 t를 초 단위 숫자로 모든 어댑터에 똑같이 준다. 어댑터는 방식별 API가 받는 단위와 시작점으로 바꿔 인스턴스를 그 시각에 놓고 멈춘다. "정지"는 인스턴스가 스스로 시간을 진행하지 않게 하는 것이다. 어댑터마다 이 일을 하는 API가 아래처럼 다르다.

| 어댑터 | 시각 t를 넣는 곳 | 단위·기준점 | 정지 방법 |
|---|---|---|---|
| gsap | `timeline.totalTime(t, suppressEvents)`(없으면 `timeline.seek`) | 초, 루트 timeline 0 | `timeline.pause()` |
| css | 살아 있는 `CSSAnimation.currentTime`, 없으면 inline `animation-delay` | ms, 요소가 속한 clip(`[data-start]`)의 시작 시각 기준 | `Animation.pause()`, 없으면 `animation-play-state: paused` |
| waapi | `Animation.currentTime` | ms, 처음 발견한 시각(baseline) 기준 | `Animation.pause()` |
| animejs | `instance.seek(ms)` | ms, 인스턴스 0 | `instance.pause()` |
| lottie | lottie-web `goToAndStop(value, isFrame)`, dotLottie `setFrame`·`setCurrentRawFrameValue`·`seek(%)` | 컴포지션(`[data-composition-id]`) 시작 기준 초 → 프레임 또는 ms | `anim.pause()` |
| three | `window.__hfThreeTime = t`, `hf-seek` 이벤트 | 초, 페이지 0 | 컴포지션 코드의 `hf-seek` 리스너가 그린다 |
| typegpu | `window.__hfTypegpuTime = t`, `hf-seek` 이벤트 | 초, 페이지 0 | 위와 같다. 정지 중 250ms 하트비트(R-27) |
| frame-source | `source.render(sourceTime, signal)` | 초, 소스 시작 + 재생 속도 반영 | 비동기. `registerSeekCompletion`으로 렌더러가 기다린다 |
| d3, leaflet, mapbox, maplibre, google-maps | 없음(seek는 빈 함수) | 해당 없음 | 해당 없음. ready 게이트만 맡는다(R-29) |

#### 1.3.3 어댑터별 구현 멤버와 발견·의존

`discover`가 무엇을 찾는지와 어떤 전역·라이브러리에 기대는지가 어댑터마다 다르다. 표의 "ready"는 `getReadyPromise`, "길이"는 `getInferredDurationSeconds`와 `getAnimationCycleEndSeconds`를 뜻한다.

| 순서 | name | 발견 대상 | 의존하는 전역·API | `play` | `revert` | ready | 길이 |
|---|---|---|---|---|---|---|---|
| 1 | `frame-source` | `registerFrameSource`로 등록되고 DOM에 연결된 소스 | `window.__hyperframes.registerFrameSource`, `MutationObserver` | 없음 | 있음 | 있음 | 없음 |
| 2 | `waapi` | `document.getAnimations()` 스냅샷과 `Element.animate` 호출 | WAAPI, `Element.prototype.animate` 래핑 | 없음 | 있음 | 없음 | `getInferredDurationSeconds`만 |
| 3 | `css` | computed `animation-name`이 none이 아닌 모든 HTML 요소 | CSS animation, `getComputedStyle`, `getAnimations` | 있음 | 있음 | 없음 | 둘 다 |
| 4 | `animejs` | `window.__hfAnime` 배열(v3는 `anime.running`도 병합) | `window.anime`(v3 한정), 작성자의 `push` | 있음 | 빈 함수 | 없음 | 없음 |
| 5 | `lottie` | `window.__hfLottie` 배열 + `window.lottie.getRegisteredAnimations()` | lottie-web, dotLottie 인스턴스 | 없음 | 빈 함수 | 없음 | 둘 다 |
| 6 | `three` | `window.THREE.DefaultLoadingManager` | `window.THREE` 전역 | 있음 | 있음 | 있음 | 없음 |
| 7 | `mapbox` | `window.__hfMapbox` 배열 | Mapbox GL 지도 객체(`loaded()`, `on("load")`) | 빈 함수 | 빈 함수 | 있음 | 없음 |
| 8 | `leaflet` | `window.__hfLeaflet` 배열 | Leaflet 지도 객체(`whenReady`) | 빈 함수 | 빈 함수 | 있음 | 없음 |
| 9 | `google-maps` | `window.__hfGoogleMaps` 배열 | Google Maps 객체(`addListener("tilesloaded")`) | 빈 함수 | 빈 함수 | 있음 | 없음 |
| 10 | `maplibre` | `window.__hfMaplibre` 배열 | MapLibre 지도 객체(`loaded()`, `on("load")`) | 빈 함수 | 빈 함수 | 있음 | 없음 |
| 11 | `d3` | `window.__hfD3` 배열 | D3 transition 객체(`end()`) | 빈 함수 | 빈 함수 | 있음 | 없음 |
| 12 | `typegpu` | 없음(빈 `discover`) | 컴포지션의 `hf-seek` 리스너, `data-requires-webgpu` | 있음 | 있음 | 없음 | 없음 |
| 13 | `gsap` | 없음(빈 `discover`) | 런타임이 넘기는 `state.capturedTimeline` | 없음 | 없음 | 없음 | 없음 |

#### 1.3.4 `hf-seek` 이벤트

Three.js와 TypeGPU 어댑터가 공유하는 `window` CustomEvent다. `detail`은 `{time: number(초), waitUntil(promise): void}`다. 컴포지션 코드가 리스너에서 `e.detail.time`으로 한 프레임을 그리고, 같은 호출 스택 안에서 `e.detail.waitUntil(promise)`로 GPU 작업 완료 promise를 넘기면 렌더러가 그 promise를 기다린다. 리스너가 이벤트 처리가 끝난 뒤에 `waitUntil`을 부르면 오류를 던진다(R-25).

#### 1.3.5 등록 순서와 `FrameAdapter`와의 관계

등록 순서는 1.3.3 표의 "순서" 열이다(R-31). 공개 인터페이스 `FrameAdapter`는 `RuntimeDeterministicAdapter`와 다른 타입이고 런타임이 참조하지 않는다. 관계는 R-35에 쓴다.

### 1.4 행동 규칙과 남은 질문 [필수]

**계약과 호출**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 어댑터 객체를 정의한다 | 필수 멤버는 `name`, `discover`, `seek`, `pause`이고 나머지(`play`, `revert`, `getReadyPromise`, `getInferredDurationSeconds`, `getAnimationCycleEndSeconds`)는 선택이다. 런타임은 선택 멤버를 `typeof … === "function"`으로 확인한 뒤에만 부른다(`play`, `revert`, `getReadyPromise`, 길이 hook 모두). 이 타입은 `@hyperframes/core`의 공개 export에 없다 | 코드 확인 |
| R-02 | `runAdapters("discover", time)`가 불린다 | 등록 순서대로 각 어댑터에 `discover()`를 부르고, 같은 어댑터에 곧바로 `seek({time, suppressEvents: true})`를 부른다(`pageAnimations` 없음). `discover`와 `seek`는 각각 따로 try/catch라서 `discover`가 던져도 같은 어댑터의 `seek`는 불린다. 이 호출은 `gsap` 어댑터를 건너뛰지 않는다(R-14). `runAdapters("discover")`를 부르는 위치는 네 곳이다. ① init의 `runAdapters("discover")`(시각 0, `init.ts:5486`), ② 루트 timeline 바인딩 직후(`5493`), ③ `maybePublishRenderReady`가 마운트와 timeline 빌드 대기 검사를 통과할 때마다(`5580`), ④ `settleChangedScenes`가 scene을 새 DOM으로 교체한 뒤 timeline을 다시 바인딩하고 나서(`4572`). ④는 프리뷰에서 `window.__hfSwapScenes`(scene manifest meta가 있는 프리뷰만 설치)나 scene 지연 마운트(`mountScene`)가 부른다. 렌더 경로에는 이 호출이 없다(검색 범위는 2.1 R-02) | 코드 확인 |
| R-03 | seek, pause, play 경로가 어댑터를 부른다 | `seek`는 `seekRootChildrenAndAdapters`가 루트·scene timeline 처리 뒤에 등록 순서대로 부른다. 이때 `name === "gsap"`이고 `tl`(`state.capturedTimeline`)이 있으면 그 어댑터만 건너뛴다. 같은 규칙이 `player`의 `onDeterministicSeek`(`init.ts:5404-5417`)에도 있다. `pause`는 `runAdapters("pause")`가 모든 어댑터에 부르고 `gsap`도 건너뛰지 않는다(루트 timeline `pause()`가 불린다). `play`는 `transport.play()`가 `runAdapters("play")`로 부르고, `play`가 없는 어댑터는 건너뛴다. 캡처 motion blur도 같은 `seekRootChildrenAndAdapters`로 어댑터를 다시 seek한다(`init.ts:4220-4237`). 그래서 한 프레임에 같은 시각의 `seek`가 여러 번 올 수 있다 | 코드 확인 |
| R-04 | 어댑터 메서드가 던진다 | `discover`·`seek`·`pause`·`play`·`revert`는 어댑터별 try/catch가 `swallow(label, err)`로 삼킨다. 다른 어댑터는 계속 불린다. `getReadyPromise`가 던져도 삼키고, 그 어댑터는 이번 평가에서 대기 대상이 아니다. 길이 hook이 던지면 삼키고 그 어댑터를 floor에서 뺀다. `swallow`는 `window.__hf.onSwallowed` 핸들러가 있으면 부르고, `__hfDebug` 또는 `__HYPERFRAMES_DEBUG`가 켜져 있을 때만 `console.debug`를 남긴다. 기본 설정에서는 사용자에게 보이는 신호가 없다. 어댑터 내부에서 하는 per-인스턴스 try/catch(Anime.js, Lottie, CSS 등)도 같은 `swallow`로 간다 | 코드 확인 |
| R-05 | `discover`가 같은 입력으로 여러 번 불린다 | 어댑터마다 중복 없이 상태를 갱신한다. css는 기존 inline style을 복원한 뒤 요소를 다시 스캔하고 이전 `Animation` 핸들을 이어 받는다. waapi는 이미 추적한 `Animation`에 baseline을 다시 만들지 않는다. animejs와 lottie는 `Set`으로 중복을 걸러 `window.__hfAnime`·`__hfLottie`에 없는 것만 추가한다. three는 이미 감싼 `DefaultLoadingManager`를 다시 감싸지 않는다. frame-source는 `owned` 집합으로 이미 등록한 소스를 다시 등록하지 않는다. gsap, typegpu, 지도·D3는 `discover`가 빈 함수다 | 코드 확인(13개 전부의 `discover` 본문을 읽음) |
| R-06 | `getReadyPromise`가 `__renderReady`에 반영된다 | `maybePublishRenderReady`가 `runAdapters("discover")` 뒤에 `isAdapterReadinessSettled()`를 평가한다. 이 함수는 모든 어댑터의 `getReadyPromise()`를 모아 null이 아닌 것의 목록을 만든다. 목록이 비면 settled다. 목록의 원소(promise 객체)가 직전 평가와 같으면 직전 settled 값을 돌려주고, 달라지면 `settled=false`로 두고 `Promise.all`(원소 하나면 그 promise)에 `then`을 단다. resolve와 reject 모두 settled가 되고 `maybePublishRenderReady`를 다시 부른다. reject는 `swallow("runtime.init.adapterReady")`로 삼킨다. settled가 아닌 동안 `__renderReady`는 false다. 런타임 쪽 타임아웃은 없다. 같은 대기에 대해 매번 새 promise를 돌려주면 목록 비교가 매번 달라져 대기가 끝나도 settled가 되지 않는다(init.ts:356-359의 주석). 그래서 같은 promise를 반복해 돌려주는 것이 계약이다. 타임아웃과 렌더러 쪽 대기 한도는 [runtime-seek.md](./runtime-seek.md) R-35를 따른다 | 코드 확인 |
| R-07 | 길이 hook이 불린다 | `resolveAdapterDurationFloorSeconds`가 모든 어댑터의 hook을 순서대로 부르고(`oneCycle`이면 `getAnimationCycleEndSeconds`, 아니면 `getInferredDurationSeconds`), 유한한 양수의 최댓값을 구해 `MIN_VALID_TIMELINE_DURATION_SECONDS`보다 크면 돌려준다. 결과는 컴포지션 길이 floor 중 하나다([runtime-seek.md](./runtime-seek.md) R-29). hook은 캐시 없이 호출마다 어댑터 상태를 읽는다. 구현하는 어댑터는 css(둘 다), waapi(`getInferredDurationSeconds`만), lottie(둘 다)다. 무한 반복 애니메이션은 css·waapi에서 `endTime`이 Infinity라 건너뛴다(그 컴포지션은 `data-duration`을 직접 써야 한다는 타입 주석). `types.ts`의 주석은 `getInferredDurationSeconds`가 `discover`와 같은 주기로 불린다고 쓰지만 구현은 길이 floor를 계산할 때 부른다(2.1) | 코드 확인 |
| R-08 | seek 패스와 pause가 `pageAnimations`를 넘긴다 | `pageAnimationsForOnePass()`가 `document.getAnimations()`를 처음 읽을 때 한 번 부르고 결과를 그 패스의 모든 어댑터가 공유한다. 같은 getter가 seek 패스의 `seek`와 이어지는 `runAdapters("pause", 0, pageAnimations)`에 전달된다. css와 waapi가 이 getter를 쓴다. `discover` 직후의 부트스트랩 `seek`와 `play`는 getter 없이 불려 각자 `document.getAnimations()`를 읽는다. 결과 목록은 프레임마다 새로 읽는다 | 코드 확인 |

**정지(hold)의 공통 규칙**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-09 | 어댑터 `seek({time})`가 불린다 | gsap, waapi, animejs, lottie, three, typegpu는 `Math.max(0, Number(time) \|\| 0)`로 time을 정리한다(NaN, 음수는 0). css는 `Number(time) \|\| 0`에서 clip 시작을 뺀 값을 `max(0, …)`로 막고, frame-source도 시작을 뺀 값에만 `max(0, …)`를 쓴다. 이후 1.3.2 표대로 방식별 API에 t를 넣는다. 런타임은 gsap 어댑터를 빼고 이 시각을 클램프하지 않은 원래 값으로 준다(루트 timeline만 `totalDuration` 끝으로 클램프된다, [runtime-seek.md](./runtime-seek.md) R-22) | 코드 확인 |
| R-10 | css 또는 waapi가 `Animation` 하나를 시각 ms에 놓는다 | `holdAnimationAt`이 먼저 `pause()`를 부르고 그 뒤 `currentTime = ms`를 쓴다. 주석의 이유는 대기 중인 pause가 다음 프레임의 시각이 아닌 seek 시각을 붙잡게 하려는 것이다. `pause()`가 던지면 `pauseFailed`를 기록하고 `currentTime`을 쓴 뒤 `pause()`를 한 번 더 부른다. 각 호출의 예외는 `swallow`다 | 코드 확인 |
| R-11 | 같은 시각 t로 `seek`가 다시 온다 | 어댑터마다 다르다. css, waapi, animejs, lottie는 같은 값을 다시 써서 같은 상태가 된다. three와 typegpu는 `dispatchSeekEvent`가 마지막 시각과 정확히 같은 float이면 `hf-seek` 이벤트를 다시 보내지 않고 전역 `__hf…Time`만 다시 쓴다(R-25). gsap의 `seekGsapTimeline`은 같은 시각이고 이미 한 번 그려졌으면 `totalTime(t)`만 다시 부르고 false를 돌려주며, 한 번도 그려진 적이 없으면 tween을 다시 렌더하고 true를 돌려준다(R-16). frame-source는 같은 소스 시각을 다시 `render`한다 | 코드 확인 |
| R-12 | `suppressEvents`가 어댑터에 전달된다 | `ctx.suppressEvents`를 읽는 어댑터는 `gsap`뿐이다(`totalTime(t, suppress)`). css, waapi, animejs, lottie, three, typegpu, frame-source는 이 값을 읽지 않고 이벤트를 막는 코드도 없다. discover의 부트스트랩 seek는 `suppressEvents: true`를 주지만 `gsap` 외에는 영향이 없다. Anime.js나 lottie-web 자체 콜백이 `seek` 중 실행되는지는 해당 라이브러리 동작이라 확인하지 않았다 | 코드 확인(전달·미사용), 미확인(라이브러리 쪽 콜백) |
| R-13 | 재생 중과 seek의 차이, 렌더와 프리뷰의 차이 | `play()`가 있는 어댑터는 재생 시작 때 한 번만 불린다. css는 inline `animation-delay`·`animation-play-state`를 복원하고 살아 있는 `CSSAnimation`에 `play()`를 부른다. animejs는 `instance.play()`다. three와 typegpu는 `forcedTime = null`로 비우고 typegpu는 하트비트를 멈춘다. waapi, lottie, gsap, frame-source에는 `play`가 없다. 재생 중 프레임 갱신은 transport가 같은 seek 경로를 매 tick 돌리는 것이다([runtime-seek.md](./runtime-seek.md) R-31). 렌더와 프리뷰의 차이를 어댑터가 직접 아는 곳은 없다. 같은 `ctx`가 가고, `renderFps`는 어댑터가 아닌 `seekGsapTimeline`에만 전달된다(R-15). 런타임 `isRenderMode` 분기는 어댑터에 없다 | 코드 확인(전달 경로), 추론(재생 중 tick이 어댑터를 매번 seek하는 점은 runtime-seek 스펙을 따름) |

**GSAP**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-14 | `gsap` 어댑터가 불린다 | `createGsapAdapter({getTimeline})`는 `state.capturedTimeline`만 안다. `discover`는 빈 함수다. `seek`는 timeline이 null이면 아무것도 안 하고, 있으면 `timeline.pause()` 후 `totalTime(safeTime, suppressEvents)`를 부르고 `rerenderGsapTimelineAt(…, safeTime)`로 같은 시각을 다시 그린다(`totalTime`이 없으면 `timeline.seek`). `pause`는 `timeline.pause()`다. 런타임의 seek 패스는 이 어댑터를 건너뛰므로(R-03) 이 `seek`가 실제로 도는 경로는 `runAdapters("discover")`의 부트스트랩 seek(R-02)다. 이때는 `totalDuration` 클램프(runtime-seek R-22 ④)와 건너뛴 프레임 replay가 없고 `suppressEvents`는 true다 | 코드 확인 |
| R-15 | 루트·scene timeline을 `seekGsapTimeline(timeline, t, suppressEvents, structure, renderFps)`로 seek한다 | `renderFps`가 있으면 먼저 `framesSkippedSinceLastSeek`가 돌려준 시각들(먼 과거부터)에 `totalTime`으로 차례로 거친 뒤 t에 도착한다. `lastRenderSeek`(timeline별 마지막 seek 시각, WeakMap)와 비교해 건너뛴 프레임 수를 센다. 첫 seek면 `floor(t × fps)`, 아니면 `ceil((t − last) × fps) − 1`이다. 건너뛴 프레임이 1 미만이면 replay가 없다. 건너뛴 프레임 중에서 같은 target의 같은 속성을 쓰는 tween 쌍이 겹치는 구간(`overlapSpansOf`)에 걸리는 프레임만 replay한다. `renderFps`는 fps가 유효한 producer 렌더와 `__HF_REPLAY_SKIPPED_FRAMES`가 켜진 캡처 경로에서 정해진다([runtime-seek.md](./runtime-seek.md) R-23 (d)). 프리뷰는 `renderFps`가 없어 replay가 없다 | 코드 확인 |
| R-16 | t에 도착한 뒤 같은 시각 상태를 authored 순서에 맞춘다 | `landOn`이 `totalTime(t, suppress)` 뒤에 `settleOverlapsEndedBetween`으로 이전 위치에서 t 사이에 끝난 겹침을 정산한다(겹침 중 나중 것이 `set`이고 앞선 tween이 그 사이에 끝났으면 `later start − 1e-4`로 되돌아갔다 t로 다시 간다). t가 직전 위치보다 앞이고 `structure`가 있으면 `reapplyStepsInAuthoredOrder`가 t 시각의 길이 0 step과 timeline을 각자 `render(0, true, true)`로 다시 적용한다. 직전과 같은 시각이면서 한 번도 그려진 적 없으면(`gsapNeverRendered`) `rerenderGsapTimelineAt`을 부르고 true를 돌려준다. `structure`는 `renderCaptureSeekStarted`가 true면 undefined다(`init.ts:5629-5636`) | 코드 확인 |
| R-17 | `rerenderGsapTimelineAt(timeline, t, structure?)`가 같은 시각을 다시 그린다 | t 바로 아래(t가 0.001 이상이면 `t − 0.001`, 아니면 `t + 0.001`)로 `totalTime(…, true)`한 뒤 t에서 시작하는 keyframes·`_startAt` tween을 `primeTweensStartingAt`으로 먼저 렌더하고 `totalTime(t, true)`로 도착해 같은 시각 step이 authored 순서로 적용되게 한다. t 이후에 시작하는 child는 `_ts = 0`으로 잠시 멈추고 부모의 `_dur`·`_tDur`·`_end`·`_dirty`를 끝나면 복원한다. 근처 landing mark(`ratio`, `_zTime`, `_act`)도 복원해 이벤트가 중복 발화하지 않게 한다. 이 함수는 GSAP 내부 필드(`_ts`, `_start`, `_dur`, `_hfAuthored` 등)를 직접 읽고 쓴다 | 코드 확인(동작), 추론(각 내부 필드 복원이 필요한 GSAP 쪽 이유) |
| R-18 | authored order가 기록된다 | `installFlatGsapTransforms`(`entry.ts` 부트 시점, `window.gsap`가 할당될 때)가 `stampAuthoredOrder`로 GSAP `core.Timeline.prototype`의 `to`, `from`, `fromTo`, `set`을 감싼다. 감싼 함수가 추가한 child(`_recent`)에 `_hfAuthored`(전역 증가 번호)를 처음 한 번 붙인다. `authoredOrderOf(tween, owner)`가 owner까지 부모를 거슬러 올라가며 가장 가까운 번호를 돌려준다. 런타임이 로드되기 전에 만든 timeline은 번호가 없어 `undefined`이고, 이 경우 `writtenBefore`가 false라 순서 판정이 없다. 번호는 같은 시각의 `set`이 앞선 tween의 초기 상태인지 덮어쓰기인지를 가른다(`laterIsSet`) | 코드 확인 |

**CSS와 WAAPI**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-19 | css `discover`와 `seek`(살아 있는 `CSSAnimation`이 있을 때) | `discover`는 먼저 기존 entry의 inline 변경을 복원하고(작성자의 값으로 돌림) `document.querySelectorAll("*")`의 HTML 요소 중 computed `animationName`이 비어 있거나 none이 아닌 것을 entry로 만든다. entry는 inline `animation-delay`·`animation-play-state` 원본, 한 사이클 길이(delay + duration의 최댓값), 이름별 delay 목록, 이전 `Animation` 핸들을 가진다. `seek`는 `pageAnimations`에서 `CSSAnimation`이고 `pseudoElement`가 아닌 것만 요소별로 모으고(entries가 비면 스캔하지 않음), 이전 핸들 중 `idle`이 아닌 것을 유지한다. 연결된 entry마다 `localTimeMs = max(0, t − 시작) × 1000`을 구해 핸들 각각을 `holdAnimationAt`으로 놓는다. 시작 시각은 `el.closest("[data-start]") ?? el`을 `resolveStartForElement`로 푼 값이다. `animationDelay` 같은 CSS 값은 `currentTime`이 delay 구간을 포함해서 읽으므로 delay 보정을 따로 하지 않는다 | 코드 확인 |
| R-20 | css가 살아 있는 `CSSAnimation`을 못 찾는다(`getAnimations`는 `display: none`이거나 숨겨진 clip의 애니메이션을 돌려주지 않음) | entry의 핸들이 비어 있으면 inline에 `animation-play-state: paused`와 `animation-delay: (원래 delay − localTime)초`(`toFixed(3)`)를 이름별로 써서 같은 자세를 만든다. 다음 `seek`에서 핸들을 찾으면 inline을 먼저 복원하고(`animationDelay !== baseDelay`일 때) 핸들 경로로 돌아간다. `pause`는 살아 있는 애니메이션이 있는 entry만 `pause()`하고 inline을 복원한다. 레이아웃·계산 비용 때문에 한 패스 안에서 `playState` 읽기를 모두 쓰기 앞에 둔다(코드 주석). `display: none`을 해제하는 코드는 어댑터에 없다 | 코드 확인 |
| R-21 | waapi가 `Animation`을 추적하고 seek한다 | baseline은 `{compositionTimeMs, animationTimeMs}`이고 처음 본 시각에 한 번 정한다. `seek`는 `localMs = animationTimeMs + max(0, t − compositionTimeMs)`를 `holdAnimationAt`으로 쓴다. 첫 `discover` 전(`didDiscover` false)에 본 `running`·`finished` 상태의 작성자 `Animation`(재생 속도 1, document timeline, CSS가 만든 것이 아님)은 baseline을 0으로 고정하고(composition 시각 0에서 시작한 것으로 본다), `discover` 이후 처음 본 것은 그 애니메이션의 현재 `currentTime`을 기준으로 하되 현재 컴포지션 시각 이상이면 컴포지션 시각만큼 뺀다. `discover`가 `Element.prototype.animate`를 래핑해 이후 만들어지는 `Animation`을 `lastSeekTimeMs` 시각에 바로 추적한다. 빈 `discover` 뒤에는 추적 중인 것이 하나도 없으면 프레임마다의 `document.getAnimations()` 스캔을 건너뛴다(성능 주석). `finish`·`cancel` 이벤트가 오면 추적에서 뺀다. `idle`인 브라우저 생성 CSS 애니메이션도 뺀다 | 코드 확인 |
| R-22 | css와 waapi가 같은 `CSSAnimation`을 모두 만진다 | waapi의 `document.getAnimations()` 스냅샷은 브라우저가 만든 `CSSAnimation`과 `CSSTransition`도 추적하고 같은 `seek`에서 `holdAnimationAt`을 부른다. 등록 순서가 waapi(2번), css(3번)이므로 `CSSAnimation`에는 css 어댑터가 나중에 쓴 값이 남는다. `CSSTransition`은 css 어댑터가 다루지 않아 waapi만 만진다 | 코드 확인(두 어댑터 모두 같은 객체에 `currentTime`을 쓰고 순서가 이렇다), 추론(그래서 css 값이 이긴다는 결과) |

**Anime.js, Lottie**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-23 | animejs `discover`·`seek`·`pause`·`play` | `seek`는 `window.__hfAnime`의 모든 인스턴스에 `instance.seek(ms)`(ms = max(0, t) × 1000)를 부르고 인스턴스별 예외를 삼킨다. `pause`는 `instance.pause()`, `play`는 `instance.play()`다. `discover`는 `window.anime.running` 배열이 있을 때만(v3 방식) 그 인스턴스를 `__hfAnime`에 병합한다. anime.js v4는 `running`을 내보내지 않아 `discover`가 아무것도 찾지 못하므로, 작성자가 모든 인스턴스를 `window.__hfAnime`에 직접 `push`하지 않으면 seek 대상이 아니다(파일 주석). `revert`는 비어 있고 배열을 비우지 않는다(인스턴스는 작성자 소유) | 코드 확인 |
| R-24 | lottie `discover`·`seek`·`pause` | `discover`는 `window.lottie.getRegisteredAnimations()`의 결과를 `window.__hfLottie`에 병합한다(lottie-web 한정이고, dotLottie는 작성자가 `push`해야 한다). `seek`는 인스턴스마다 `time = max(0, 페이지 시각 − 컴포지션 시작)`을 구한다. 컴포지션 시작은 인스턴스 `wrapper`(dotLottie는 `canvas`)의 가장 가까운 `[data-composition-id]`를 `resolveStartForElement`로 푼 값이고, 조상이 없으면 0이다. lottie-web은 `loop === true`이면 `frame = time × frameRate`를 `wrapFrame(frame, totalFrames)`로 감아 `goToAndStop(frame, true)`, 루프가 아니고 `frame ≥ totalFrames`면 `goToAndStop(totalFrames − 1, true)`, 그 외는 `goToAndStop(time × 1000, false)`다. dotLottie는 `setFrame`, `setCurrentRawFrameValue`, `seek(percentage)` 중 인스턴스가 가진 첫 번째로 seek하고 `duration`·`totalFrames`가 유한한 양수가 아니면 그 인스턴스를 건너뛴다. `pause`는 두 종류 모두 `pause()`다. 아직 로드되지 않아 `totalFrames`가 0이면 길이 hook은 null을 돌려준다(이후 `discover` 주기에 다시 읽힌다) | 코드 확인 |

**GPU 어댑터와 `hf-seek`**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-25 | `dispatchSeekEvent(t)`와 seek 완료 barrier | `dispatchSeekEvent`는 직전 시각과 정확히 같은 float이면(초기값 −1) 아무것도 안 하고, 다르면 `hf-seek` CustomEvent를 `window`로 보낸다. `forceDispatchSeekEvent`는 같은 시각이어도 보낸다. `detail.waitUntil(p)`는 이벤트를 보내는 동안(`accepting`)에만 받고, 그 뒤에 부르면 오류를 던진다. 넘겨진 promise가 있으면 `Promise.all`을 `registerSeekCompletion(…, "hf-seek")`로 barrier에 올린다. `dispatchEvent` 자체가 던지면 삼킨다. barrier 대기는 `waitForSeekCompletion`이 맡고(보류 중 completion이 모두 settle할 때까지 반복, 처음 reject된 이유를 던지고, 한도를 넘으면 `SeekNotSettledError`, 상세는 runtime-seek R-22), `SeekHold` 종류는 `video-frame`, `hf-seek`, `frame-source`, `scene-window`, `motion-blur`, `vfx`, `image-decode`다 | 코드 확인 |
| R-26 | three 어댑터 | `seek`는 시각을 `window.__hfThreeTime`에 쓰고 `dispatchSeekEvent`를 부른다. 클로저의 `forcedTime`·`lastForcedTime`은 `seek`, `pause`, `play`, `revert` 안에서만 바뀌고 같은 파일의 다른 코드가 읽지 않는다. `discover`는 `window.THREE.DefaultLoadingManager`(`itemsLoaded`·`itemsTotal`이 숫자일 때)를 잡아 `onStart`를 감싸고 아직 로딩 중이면 `onLoad`를 감싸 대기 promise를 만든다. 사용자의 기존 `onStart`·`onLoad`는 먼저 부르고 끝나면 `onLoad`를 원래 값으로 되돌린다. `getReadyPromise`는 THREE가 없거나 큐가 비었으면(`itemsTotal <= itemsLoaded`) null, 아니면 같은 대기 promise를 돌려준다 | 코드 확인 |
| R-27 | typegpu 어댑터 | `seek`는 `window.__hfTypegpuTime`에 쓰고 `dispatchSeekEvent`를 부른다(three와 같은 이벤트, R-25가 중복을 막는다). `pause`는 `forcedTime`이 null이면 마지막 시각으로 채우고 `startPresentHeartbeat`를 시작한다. 하트비트는 문서에 `[data-composition-id][data-requires-webgpu]` 요소가 있을 때만 켜지고, `wallSetInterval` 250ms(`TYPEGPU_PRESENT_HEARTBEAT_MS`)마다 `forcedTime`이 있고 seek barrier가 활성이 아니면 `__hfTypegpuTime`을 다시 쓰고 `forceDispatchSeekEvent`를 보낸다. `play`와 `revert`가 하트비트를 멈춘다. `pause`는 렌더에서도 seek 패스마다 불리므로 하트비트는 렌더 중에도 켜진다. 하트비트의 목적(정지 중에도 WebGPU 캔버스를 계속 present)은 이름에서 추론한 것이다 | 코드 확인(동작), 추론(목적) |

**frame source, 지도·D3**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-28 | frame-source 어댑터 | 모듈 전역 `sources` 맵에 `registerFrameSource`가 등록한 소스를 어댑터가 요소가 DOM에 연결돼 있으면 `owned`에 담고(연결이 끊긴 소스는 `dispose`), 처음 담을 때 소스의 `ready`를 `registerSeekCompletion(…, "frame-source")`에 올린다. `seek`는 소스마다 clip 창(`isClipOnScreenAt(time, start, end, fps, 컴포지션 길이)`)에 들어 있을 때만 `sourceTime = readMediaStart(el) + sourceTimeAt(속도 사양, max(0, time − start))`를 `source.seek`에 주고 그 promise도 barrier에 올린다. `source.seek`는 마지막 요청만 남기는 직렬 큐(`pending`, `work`)이고 `sourceRange`가 있으면 `start + clamp(time, 0, duration − 1/fps)`로 바꾼다. `getReadyPromise`는 소스가 없으면 null, 있으면 모든 `source.ready`를 `Promise.all`한 것(소스 집합이 같으면 같은 promise)이다. `MutationObserver`가 DOM 제거를 감시하고 `revert`가 모든 소스를 `dispose`한다. `pause`는 빈 함수다 | 코드 확인 |
| R-29 | 지도·D3 어댑터(`createReadinessAdapter`) | `getInstances()`가 `window.__hf…` 배열(배열이 아니면 빈 목록)을 읽는다. `discover`, `seek`, `pause`, `play`, `revert`는 모두 빈 함수다. `getReadyPromise`는 인스턴스가 없거나 모두 settled면 null, 아니면 아직 settled가 아닌 인스턴스에 `waitFor`를 걸어 `Promise.allSettled`로 묶은 promise 하나를 만들고 끝나면 `pendingPromise`를 null로 돌린다. 대기 중에는 같은 promise를 돌려준다. `waitFor`가 fulfilled된 인스턴스만 `settled` 집합에 들어간다. rejected된 인스턴스는 다음 평가에서 다시 `waitFor`를 건다. `waitFor`가 동기로 던지면 `getReadyPromise` 전체가 던지고 런타임이 삼킨다(R-04) | 코드 확인 |
| R-30 | 방식별 대기 조건 | mapbox와 maplibre는 `map.loaded()`가 true면 즉시, 아니면 `map.on("load", resolve)`까지 기다린다(주석: style과 source가 준비된 때이고 타일 단위 `idle`은 아니다). leaflet은 `map.whenReady(resolve)`다. google-maps는 `map.addListener("tilesloaded", …)`가 불릴 때까지 기다리고 그때 리스너를 제거한다. d3는 `transition.end()` promise를 기다린다. 런타임에 타임아웃이 없어서(R-06) 이벤트가 오지 않으면 `__renderReady`가 false로 남는다. google-maps는 이미 `tilesloaded`가 지나간 지도를 `__hfGoogleMaps`에 넣으면 이벤트가 다시 오지 않을 수 있다(`loaded()` 같은 즉시 확인 분기가 없음, 라이브러리 재발화 여부는 미확인). `skills/hyperframes/references/runtimes.md`는 차트·지도는 라이브러리 자체 전환 대신 GSAP tween의 `onUpdate`로 구동하라고 안내한다 | 코드 확인(대기 조건), 미확인(Leaflet·Google Maps의 재발화·즉시 호출 동작) |

**등록, teardown, 경계**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-31 | init이 어댑터를 만든다 | `state.deterministicAdapters`에 이 순서로 담긴다: `frame-source`, `waapi`, `css`, `animejs`, `lottie`, `three`, `mapbox`, `leaflet`, `google-maps`, `maplibre`, `d3`, `typegpu`, `gsap`(C-02). 의존 주입은 frame-source(`resolveStartForElement`, `resolveDurationForElement`, `getSafeTimelineDurationSeconds`, `canonicalFps`), css와 lottie(`resolveStartForElement`), gsap(`getTimeline`)이다. 모든 `seek`·`pause`·`play`·`discover`는 이 순서로 불리고 `gsap`이 마지막이다. 어댑터를 만든 직후 `patchVideoTextureCompat`, `patchWebGLVideoTextureCompat`, `patchCanvasVideoFrameCompat`, `patchExternalVideoTextureCompat`을 부른다(R-34) | 코드 확인 |
| R-32 | 새 어댑터를 추가하려는 호출자가 있다 | 어댑터를 런타임에 넣는 공개 등록 API는 없다. 어댑터는 `init.ts`에서만 만들고 `state.deterministicAdapters`에서만 읽는다. 새 어댑터를 추가하는 방법은 ① `runtime/adapters/`에 `RuntimeDeterministicAdapter`를 돌려주는 팩토리를 만들고 ② `init.ts` import 구역(`68-88`)에 import하고 ③ `5436-5459`의 배열에서 원하는 순서에 끼우고(`gsap` 앞) ④ 작성자가 채울 전역이 있으면 `window.d.ts`에 타입을 더하고 ⑤ 런타임 IIFE를 다시 빌드하는 것이다. 단 frame source 소스는 `window.__hyperframes.registerFrameSource`로 등록할 수 있다(이것은 `frame-source` 어댑터가 다루는 소스를 등록하는 API이고 어댑터 자체를 추가하지 않는다) | 코드 확인(없다는 주장은 2.1에 검색 범위) |
| R-33 | teardown이 어댑터를 정리한다 | teardown이 `state.deterministicAdapters`의 `revert`를 순서대로 부르고(없는 어댑터는 건너뜀, 예외는 삼킴) 배열을 비운다. `revert`가 하는 일은 css(entries 비움), waapi(추적·baseline 초기화와 `Element.prototype.animate` 원복), three와 typegpu(상태 초기화, typegpu는 하트비트 중지), frame-source(`MutationObserver` 해제와 소스 `dispose`)이고, animejs와 lottie는 작성자 소유 인스턴스라 비우지 않으며, 지도·D3는 빈 함수, gsap은 `revert`가 없다 | 코드 확인 |
| R-34 | `video-texture-compat.ts`의 패치 | `RuntimeDeterministicAdapter`가 아니다. `drawImage`, `GPUQueue.copyExternalImageToTexture`, `importExternalTexture`, WebGL `texImage2D`·`texSubImage2D`의 prototype을 한 번만 덮어(`__hfVideoPatched` 표식) `<video>`가 인자로 오면 렌더러가 넣은 `__render_frame__` `<img>`(없으면 정지 프레임)로 바꿔 준다. 렌더에서 video 위에 GPU 효과를 그리는 컴포지션이 `hf-seek` 리스너 안에서 video를 텍스처로 올릴 때 쓰인다. `window.__hfReseekGpu(t)`가 `__hfThreeTime`·`__hfTypegpuTime`을 t로 쓰고 `forceDispatchSeekEvent(t)`로 한 번 더 그리게 한다(엔진이 video 프레임을 주입한 뒤 호출) | 코드 확인(패치 대상·`__hfReseekGpu`), 추론(렌더 중 호출 시점은 주석 기준) |
| R-35 | `FrameAdapter`와 `RuntimeDeterministicAdapter`의 관계 | 서로 다른 타입이다. `FrameAdapter`는 `packages/core/src/adapters/types.ts`의 공개 인터페이스(`id`, `init?`, `getDurationFrames`, `seekFrame(frame)`, `destroy?`)이고 `@hyperframes/core`가 `createGSAPFrameAdapter`와 함께 export한다(experimental v0). 직접 만든 호스트가 호출하는 계약이며 프레임 정수와 비동기를 쓴다. `RuntimeDeterministicAdapter`는 브라우저 안 런타임 IIFE가 내부에서만 쓰는 계약이고 초 단위 시각과 동기 `seek`를 쓰며 공개 export에 없다. `core/src/runtime`, engine, producer, player, studio, cli의 비테스트 코드는 `FrameAdapter`를 참조하지 않는다. 렌더 경로는 렌더러가 `__hf.seek`를 호출하고 런타임이 `RuntimeDeterministicAdapter`를 부르는 것이다. `docs/concepts/frame-adapters.mdx`와 `determinism.mdx`는 이 둘을 구분하지 않고 "frame adapter가 `seekFrame`을 받는다"로 렌더를 설명한다(2.1) | 코드 확인(타입 정의·export·검색 범위 안의 참조 없음), 추론(문서가 호스트용 계약을 렌더 설명에 가져온 이유) |

- 불변식: 모든 어댑터 호출(R-04)은 한 어댑터의 예외로 다른 어댑터가 멈추지 않는다. `discover`는 같은 환경에서 여러 번 불려도 인스턴스를 중복으로 등록하지 않는다(R-05의 13개 확인).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-21 | waapi가 `finish` 이벤트로 추적에서 뺀 `Animation`을, 이후 t가 그 애니메이션의 시작보다 앞으로 돌아가는 seek(역방향·scrub)에서 되돌리는가. `holdAnimationAt`이 `pause` 상태로 `currentTime`을 끝 이후로 쓸 때 `finish` 이벤트가 실제로 발화하는지가 브라우저 동작에 달려 있다 | 재구현이 `finish`에서 추적을 빼면 되감기 가능한 시킹이 깨질 수 있어 그대로 따라 할지 정해야 한다 | 브라우저에서 paused `Animation`의 `currentTime`을 끝 이후로 쓸 때 `finish` 이벤트 발화를 확인한다. 또는 `waapi.test.ts`의 "drops finished lazy-tracked animations" 사례(265행 부근)를 연다 |
| U-02 | R-29 | `waitFor`가 rejected되는 인스턴스(예: interrupt된 D3 transition의 `end()`)는 `settled`에 들어가지 않고 다음 평가에서 다시 `waitFor`를 건다. reject된 promise가 settle될 때마다 `maybePublishRenderReady`가 다시 불리므로, 같은 인스턴스가 계속 reject되면 평가가 반복되는지, 그 사이 `__renderReady`가 true가 되는지 | reject하는 인스턴스가 있는 컴포지션에서 ready가 영영 안 오거나 반복 평가로 페이지가 느려질 수 있다 | `_readiness.ts` 단위 테스트가 없다(`d3.test.ts`에는 reject 사례가 없다). reject하는 `end()`를 가진 가짜 transition으로 `maybePublishRenderReady` 반복 횟수를 세어 본다 |

- 확인 한계: 어댑터가 호출하는 외부 라이브러리(GSAP, lottie-web, Three.js, Mapbox, Leaflet, Google Maps, D3, Anime.js)의 내부 동작은 열지 않았다. 브라우저에서 실행하지 않았다. `rerenderGsapTimelineAt`이 읽고 쓰는 GSAP 내부 필드(`_ts`, `_start`, `_dur`, `_zTime`, `_act` 등)의 의미는 GSAP 소스를 열지 않아 코드 읽기만으로 확인했다.

### 1.5 필수 코드 참조 [필수]

라이선스가 인용을 허용하는지는 overview 1절을 따른다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `packages/core/src/runtime/types.ts:412-462` `RuntimeDeterministicAdapter` | 어댑터 인터페이스와 각 선택 hook의 계약(주석 포함) | R-01, R-06, R-07 |
| C-02 | `packages/core/src/runtime/init.ts:5436-5463` 어댑터 배열과 패치 호출 | 등록 순서, 의존 주입, 어댑터 생성 직후 호출되는 GPU 패치 | R-31, R-34 |
| C-03 | `packages/core/src/runtime/init.ts:4114-4137` `runAdapters` | `discover`·`pause`·`play` 호출, `discover`마다 따라오는 `seek`, 어댑터별 try/catch | R-02, R-03, R-04 |
| C-04 | `packages/core/src/runtime/init.ts:360-394`, `4149-4169` | readiness 수집과 promise 집합 비교 로직(`createSettledTracker`, `isAdapterReadinessSettled`) | R-06 |
| C-05 | `packages/core/src/runtime/init.ts:5839-5914` `seekRootChildrenAndAdapters` | 어댑터 seek 순회에서 `gsap` 어댑터를 건너뛰는 조건과 `pageAnimations` 생성 | R-03, R-08, R-09 |
| C-06 | `packages/core/src/runtime/adapters/_holdAnimationAt.ts:1-29` `holdAnimationAt` | `pause` 후 `currentTime`, pause 실패 재시도 | R-10 |
| C-07 | `packages/core/src/runtime/adapters/_readiness.ts:1-36` `createReadinessAdapter` | 지도·D3 어댑터 공통 ready 게이트 | R-29 |
| C-08 | `packages/core/src/runtime/adapters/css.ts:146-234` | css 어댑터의 `discover`, `seek`, `pause`, `play`, fallback delay 계산 | R-19, R-20 |
| C-09 | `packages/core/src/runtime/adapters/waapi.ts:44-97`, `158-243` | waapi baseline 계산, 추적, `animate` 래핑, seek | R-21 |
| C-10 | `packages/core/src/runtime/adapters/lottie.ts:48-112`, `182-185` `wrapFrame` | lottie-web과 dotLottie seek 분기, 루프 감기 | R-24 |
| C-11 | `packages/core/src/runtime/adapters/seek-dispatch.ts:42-107`, `146-194` | `hf-seek` 디스패치, dedup, `waitUntil`, `waitForSeekCompletion` | R-25 |
| C-12 | `packages/core/src/runtime/adapters/gsap.ts:270-332` `framesSkippedSinceLastSeek`, `landOn`, `seekGsapTimeline` | 건너뛴 프레임 replay 선택, 도착 후 정산, 역방향 step 재적용 | R-15, R-16 |
| C-13 | `packages/core/src/runtime/adapters/gsap.ts:12-67` `rerenderGsapTimelineAt`, `renderOntoInAuthoredOrder` | 같은 시각 다시 그리기와 상태 복원 | R-17 |
| C-14 | `packages/core/src/runtime/adapters/gsapAuthoredOrder.ts:13-40` | `to/from/fromTo/set` 후킹과 `_hfAuthored` 번호 | R-18 |
| C-15 | `packages/core/src/runtime/adapters/typegpu.ts:74-127` | typegpu의 seek, pause, play, 하트비트 | R-27 |
| C-16 | `packages/core/src/runtime/frameSources.ts:22-165` | `registerFrameSource`와 `frame-source` 어댑터 | R-28 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출. 테스트 파일은 열지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02, R-04 | 어댑터 A의 `discover`가 던진다. `runAdapters("discover", 2)`를 부른다 | A의 `discover`는 `swallow`로 삼켜지고 A의 `seek({time: 2, suppressEvents: true})`가 이어서 불린다. 다음 어댑터들도 정상으로 불린다 |
| T-02 | R-19, R-20 | `start 1s`인 clip 안 요소에 `animation: fade 2s`(delay 0)가 있고 요소가 `display: none`이라 `getAnimations`에 없다. t = 1.5로 seek한다 | 요소에 `animation-play-state: paused`, `animation-delay: -0.5s`가 inline으로 써진다. 보이게 된 뒤 같은 t로 다시 seek하면 inline을 복원하고 `CSSAnimation.currentTime = 500`ms로 놓는다 |
| T-03 | R-21 | `discover` 뒤 컴포지션 시각 2s에 작성자가 `el.animate(…)`로 `Animation`을 만든다(`currentTime` 0). t = 3으로 seek한다 | baseline은 `{compositionTimeMs: 2000, animationTimeMs: 0}`이고 `currentTime`은 1000ms로 놓인다 |
| T-04 | R-24 | lottie-web 인스턴스(`totalFrames` 60, `frameRate` 30, `loop: true`)가 `start 1s`인 컴포지션 안에 있다. t = 4.5로 seek한다 | `time = 3.5`, 프레임 105가 `wrapFrame(105, 60) = 45`로 감겨 `goToAndStop(45, true)`다. `loop`가 false이면 `frame ≥ totalFrames`라 `goToAndStop(59, true)`다 |
| T-05 | R-25, R-26, R-27 | three와 typegpu 어댑터가 모두 등록돼 있다. 같은 프레임에 `seek({time: 5})`가 두 어댑터에 온다 | `window.__hfThreeTime`과 `__hfTypegpuTime`이 모두 5로 써지고 `hf-seek`는 한 번만 발화한다. 이후 t = 5로 한 번 더 seek해도 이벤트는 발화하지 않는다. `window.__hfReseekGpu(5)`는 같은 시각이어도 발화한다 |
| T-06 | R-06, R-29, R-30 | Mapbox 지도가 `window.__hfMapbox`에 등록돼 있고 `loaded()`가 false다. `maybePublishRenderReady`를 부른다 | `__renderReady`는 false다. 지도가 `load`를 보내면 promise가 settle되어 `maybePublishRenderReady`가 다시 불리고 다음 `getReadyPromise()`는 null이라 `__renderReady`가 true가 된다 |
| T-07 | R-06 | 어댑터 `getReadyPromise`가 reject된 promise를 돌려준다 | settled로 처리되어 `swallow("runtime.init.adapterReady")`로 기록되고 `__renderReady` 게이트는 통과한다. 다른 어댑터가 대기 중이면 그 어댑터를 기다린다 |
| T-08 | R-23 | anime.js v4 인스턴스를 `window.__hfAnime`에 넣지 않고 `autoplay: false`로 만들었다. t = 1로 seek한다 | 어떤 어댑터도 이 인스턴스를 seek하지 않는다. `__hfAnime`에 push한 인스턴스는 `instance.seek(1000)`이 불린다 |
| T-09 | R-03, R-14 | 루트 timeline이 바인딩돼 있다. seek 패스와 `runAdapters("pause")`가 지난다 | seek 패스에서 gsap 어댑터는 건너뛴다. pause에서는 gsap 어댑터의 `pause`가 루트 timeline의 `pause()`를 부른다. 루트 바인딩 직후의 `runAdapters("discover", currentTime)`에서는 gsap 어댑터의 `seek`가 루트에 `totalTime(currentTime, true)`와 `rerenderGsapTimelineAt`을 부른다 |
| T-10 | R-22, R-31 | 요소에 CSS `animation`이 있다. 같은 시각 t로 seek한다 | waapi가 먼저 같은 `CSSAnimation`을 baseline 기준 시각에, css가 이어서 `max(0, t − 시작)` 시각에 놓는다. css가 나중이라 최종 `currentTime`은 css 값이다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01, `packages/core/src/runtime/init.ts:1386-1404` `resolveAdapterDurationFloorSeconds`, `packages/core/src/index.ts:2` | 선택 멤버 확인 방식은 init의 `typeof … === "function"` 검사. "공개 export에 없다"는 `rg -n "RuntimeDeterministicAdapter" packages --glob '*.ts'`에서 `packages/core/src/index.ts`에 없는 것으로 확인했다(index.ts는 `PlaybackHeldBy`·`RuntimeTimelineClipIdentity`만 runtime/types에서 내보냄). 동적 export나 `export *`는 `rg -n "export \*" packages/core/src/index.ts`로 확인하지 않았다 |
| R-02 | C-03, `packages/core/src/runtime/init.ts:5486`, `5493`, `5580`, `4572`, `4537-4582` `settleChangedScenes`, `4603` `swapScenes`, `4815-4831` `mountScene`, `4935-4936` | 호출 위치 검색: `rg -n 'runAdapters\("discover"' packages/core/src/runtime --glob '!*.test.ts'`가 네 줄(`4572`, `5486`, `5493`, `5580`)이다. `4572`는 [runtime-seek.md](./runtime-seek.md) 1.3.6 표와 R-08에도 적혀 있는 호출 위치다(이 스펙 작성 중 행 2 스펙에서 빠진 것을 찾아 행 2가 반영했다). `settleChangedScenes`는 `swapScenes`(`4795`)와 `mountScene`(`4831`)에서만 불리고, `swapScenes`는 scene manifest meta가 있을 때만 `window.__hfSwapScenes`로 노출된다. 사용처는 `packages/studio/src/player/sceneSwap.ts`가 `__hfSwapScenes`를 참조하는 것까지만 확인했다(Studio 쪽 호출 조건은 행 10). 렌더 경로에 이 호출이 없다는 것은 producer·engine에서 `__hfSwapScenes`를 검색한 결과(없음)에 기댄 추론이다. `rg -n "__hfSwapScenes" packages --glob '*.ts'`가 studio와 core뿐이었다 |
| R-03 | C-05, `packages/core/src/runtime/init.ts:4114-4137`, `5404-5417`, `4220-4237` `initMotionBlur`, `4527-4535` `joinPlayback`, `5262-5272` | `adapter.name === "gsap"` 검사는 `5406`(`onDeterministicSeek`)과 `5907`(seek 순회, 줄 `adapter.name === "gsap" && tl`) 두 곳뿐이다. `runAdapters`(discover·pause·play)에는 이름 검사가 없다. `rg -n '"gsap"' packages/core/src/runtime/init.ts`로 확인했다. "렌더 경로에 없다"는 R-02와 같은 한계 |
| R-04 | C-03, `packages/core/src/runtime/init.ts:4149-4169`, `5404-5417`, `5906-5912`, `1386-1404`, `6821-6831`, `packages/core/src/runtime/diagnostics.ts:74-95` `swallow` | 각 호출 지점의 try/catch를 읽었다. `swallow`는 `onSwallowed` 핸들러와 debug 플래그 외에 사용자에게 보이는 출력이 없다 |
| R-05 | `packages/core/src/runtime/adapters/css.ts:148-166`, `waapi.ts:160-164`, `animejs.ts:54-74`, `lottie.ts:24-46`, `three.ts:63-80`, `frameSources.ts:124-126`, `_readiness.ts:16`, `typegpu.ts:99-101`, `gsap.ts:629` | 13개 어댑터의 `discover` 본문을 모두 읽었다. 전칭 주장이라 범위는 `packages/core/src/runtime/adapters/*.ts`와 `frameSources.ts`다. 새 어댑터는 이 목록에 없다. 같은 환경에서 여러 번 불렀을 때의 부작용은 코드로만 확인했고 실행하지 않았다 |
| R-06 | C-04, `packages/core/src/runtime/init.ts:356-394`, `4149-4169`, `5564-5590`, `packages/core/src/runtime/types.ts:423-441` | `createSettledTracker`의 `samePromiseSet` 비교와 settled 처리를 읽었다. "런타임 쪽 타임아웃 없음"은 `rg -n "adapterReady\|isAdapterReadinessSettled" packages/core/src/runtime --glob '!*.test.ts'`로 호출처가 `maybePublishRenderReady` 하나인 것과 타이머가 없는 것을 확인했다. 렌더러 쪽 한도는 runtime-seek R-35 |
| R-07 | `packages/core/src/runtime/init.ts:1386-1404`, `1669`, `3814-3829`, `packages/core/src/runtime/types.ts:442-461`, `css.ts:167-190`, `waapi.ts:231-242`, `lottie.ts:137-175` | 길이 hook 구현 검색: `rg -n "getInferredDurationSeconds\|getAnimationCycleEndSeconds" packages/core/src/runtime --glob '!*.test.ts'`. `types.ts:456-457`의 "discover와 같은 주기" 주석은 구현과 다르다. 호출은 `1669`(길이 floors)와 `3819`(`__hf.animationEnd`) 쪽이다(문서·구현 차이) |
| R-08 | `packages/core/src/runtime/init.ts:515-518` `pageAnimationsForOnePass`, `5905`, `5356`, `5024`, `css.ts:30-43`, `waapi.ts:30-37`, `173` | `pageAnimations`를 읽는 어댑터는 `rg -n "pageAnimations" packages/core/src/runtime/adapters --glob '!*.test.ts'`로 css와 waapi 둘뿐인 것을 확인했다 |
| R-09 | `css.ts:192`, `waapi.ts:166`, `animejs.ts:77`, `lottie.ts:49`, `three.ts:96`, `typegpu.ts:104`, `gsap.ts:634`, C-05 | 각 어댑터 `seek` 첫 줄을 읽었다. css(`css.ts:192`)와 frame-source(`frameSources.ts:128-146`)는 정리 방식이 달라 R-09에 나눠 적었다 |
| R-10 | C-06 | 코드 확인 |
| R-11 | C-11 `seek-dispatch.ts:88-107`, C-12 `gsap.ts:319-331`, `frameSources.ts:128-146`, `css.ts:191-212` | 코드 확인. gsap은 같은 시각 재호출 시 GSAP가 `totalTime(같은 값)`에 변화를 일으키는지는 열지 않았다 |
| R-12 | `rg -n "suppressEvents" packages/core/src/runtime/adapters --glob '!*.test.ts'`의 결과 | 이 검색에서 `suppressEvents`를 읽는 어댑터 구현은 `gsap.ts`뿐이다(타입 선언과 gsap 헬퍼 인자 제외). 검색어는 `suppressEvents`와 `suppress`로 했고 동의어(`silent`, `noEvents`)도 `rg -n "silent\|noEvents" packages/core/src/runtime/adapters`에서 없다. 라이브러리 쪽 콜백은 열지 않았다 |
| R-13 | `css.ts:223-229`, `animejs.ts:109-123`, `three.ts:106-108`, `typegpu.ts:117-120`, `init.ts:5269`, `4530`, `5419`, `627-628`(`renderFps` 정의), `5648`, `5883`(`seekGsapTimeline`에 `renderFps` 전달) | `play` 구현 검색: `rg -n "play:" packages/core/src/runtime/adapters packages/core/src/runtime/frameSources.ts`에서 css, animejs, three, typegpu, `_readiness`(빈 함수)다. 재생 중 tick이 어댑터를 매번 seek한다는 점은 [runtime-seek.md](./runtime-seek.md) R-31을 따르며 여기서 다시 읽지 않았다 |
| R-14 | `gsap.ts:626-656`, `init.ts:5486-5493`, `5580`, `4572`, `4114-4137` | 부트스트랩 seek에 이름 검사가 없는 것을 `runAdapters`에서 읽었다. 이 호출 때 `capturedTimeline`이 이미 바인딩돼 있다는 것은 `5493`(바인딩 직후), `5580`(마운트 뒤 반복 평가), `4572`(재바인딩 뒤)에 한한다. `5486`은 대개 바인딩 전이라 `getTimeline()`이 null일 수 있다(추론). [runtime-seek.md](./runtime-seek.md) R-09("건너뛴다")는 seek 패스 한정으로 읽어야 한다 |
| R-15 | C-12 `gsap.ts:270-288`, `302-332`, `init.ts:627-628` | 코드 확인. 식은 손으로 확인했다: 첫 seek면 `floor(t × fps + 1e-6)`, 이후는 `ceil((t − last) × fps − 1e-6) − 1`이다 |
| R-16 | C-12 `gsap.ts:253-268`, `290-300`, `74-85`, `init.ts:5629-5636` | 코드 확인. `structure` 키의 `version`은 `compositionTimingRevision:child 수`이다 |
| R-17 | C-13 | 코드 확인. 내부 필드 복원의 GSAP 쪽 이유는 GSAP 소스를 열지 않은 추론이다 |
| R-18 | C-14, `packages/core/src/runtime/init.ts:478-490` `installFlatGsapTransforms`, `entry.ts:50` | 코드 확인. `_hfAuthored`는 `rg -nw "_hfAuthored" packages/core/src --glob '!*.test.ts'`로 `gsapAuthoredOrder.ts`에서만 쓰이는 것을 확인했다 |
| R-19 | C-08 `css.ts:30-43`, `45-49`, `58-74`, `100-109`, `146-212` | 코드 확인 |
| R-20 | C-08 `css.ts:191-221` | 코드 확인. "`display: none` clip에서 `getAnimations`가 비는 것"은 파일 주석("no live CSSAnimation (no WAAPI, a hidden clip)", `css.ts:58`, `206`)이 근거이고 브라우저 동작은 실행하지 않았다 |
| R-21 | C-09 | 코드 확인. `finish` 이벤트 처리의 실제 효과는 U-01 |
| R-22 | `waapi.ts:5-7`, `30-37`, `56-63`, `175-191`, `css.ts:30-43`, `191-212`, `init.ts:5437-5459` | 두 어댑터가 같은 `Animation`에 `currentTime`을 쓰는 것과 등록 순서는 코드 확인이다. 마지막 쓰기가 이긴다는 결론은 `Animation.currentTime` setter가 즉시 반영된다는 브라우저 동작에 기댄 추론이다 |
| R-23 | `animejs.ts:4-129` | 코드 확인. `anime.running`이 v4에서 없다는 말은 파일 주석 기준이다. `skills/hyperframes/references/runtimes.md:23`도 `__hfAnime` push를 안내한다 |
| R-24 | C-10 | 코드 확인 |
| R-25 | C-11, `packages/core/src/runtime/init.ts:5466-5471` | 코드 확인. `waitUntil` 호출 시점 제한은 `seek-dispatch.ts:47-52`다. 리스너 안에서 던진 오류가 `dispatchEvent` 밖으로 나가는지(브라우저는 window error로 보고)는 열지 않았다 |
| R-26 | `packages/core/src/runtime/adapters/three.ts:18-128` `createThreeAdapter` | `forcedTime`이 읽히지 않는 것은 `rg -n "forcedTime" packages/core/src/runtime/adapters/three.ts`로 확인했다(쓰기만 있음). 같은 이름을 다른 파일에서 읽는 일은 클로저 변수라 불가능하다 |
| R-27 | C-15, `packages/core/src/runtime/wallClock.ts`(`wallSetInterval`이 실제 시계를 쓴다는 것은 파일명·함수명 기준이고 본문은 열지 않았다) | 코드 확인. 렌더 중 하트비트가 도는 것은 `runAdapters("pause")`가 seek 패스마다 불리는 것(R-03)에서 유도했다. 목적은 이름과 주석에서 추론했다 |
| R-28 | C-16, `packages/core/src/runtime/entry.ts:18`, `35`, `69`, `packages/core/src/runtime/clipWindow.ts:29-38` | 코드 확인. `docs/guides/frame-sources.md`는 열지 않았다 |
| R-29 | C-07, `d3.ts`, `leaflet.ts`, `mapbox.ts`, `maplibre.ts`, `google-maps.ts` 전체 | 코드 확인. "빈 함수" 주장은 `rg -n "seek: \(\) => \{\}" packages/core/src/runtime/adapters/_readiness.ts`로 확인했다 |
| R-30 | `mapbox.ts:9-25`, `maplibre.ts:9-25`, `leaflet.ts:9-16`, `google-maps.ts:9-22`, `d3.ts:7-17`, `skills/hyperframes/references/runtimes.md:26` | 코드 확인. 라이브러리의 이벤트 발화 규칙은 열지 않았다. Leaflet `whenReady`가 이미 준비된 지도에 즉시 콜백하는지, Google `tilesloaded`가 한 번만 발화하는지는 미확인이다 |
| R-31 | C-02 | 코드 확인. 어댑터 13개는 배열 리터럴의 항목 수다 |
| R-32 | C-02, `packages/core/src/runtime/state.ts:8`, `100`, `packages/core/src/runtime/entry.ts:35`, `69` | 없다 주장의 검색: `rg -n "deterministicAdapters" packages --glob '*.ts'`는 `state.ts`, `init.ts`, 테스트뿐이다. `rg -ni "registerAdapter\|registerDeterministicAdapter\|addDeterministicAdapter\|__hfAdapters\|adapters\.push\|customAdapter" packages docs skills`는 `packages/core/src/runtime/frameSources.test.ts:24`의 테스트 지역 변수 `adapters.push(runtime)`뿐이다. 검색 범위는 `packages/*/src`, `docs`, `skills`다. `registry/`, `.agents/`, 동적 대입(`state` 접근을 다른 이름으로 하는 코드)과 빌드 산출물은 보지 않았다 |
| R-33 | `packages/core/src/runtime/init.ts:6821-6831`, `css.ts:231-233`, `waapi.ts:206-230`, `three.ts:108-111`, `typegpu.ts:122-126`, `frameSources.ts:159-163`, `animejs.ts:125-127`, `lottie.ts:132-135` | 코드 확인 |
| R-34 | `packages/core/src/runtime/adapters/video-texture-compat.ts:1-156`(앞 60행과 함수 시그니처·prototype 대입만 읽음), `init.ts:5460-5471` | 패치 대상 목록은 `rg -n "prototype\." video-texture-compat.ts` 결과다. `texImage2D`·`texSubImage2D` 본문과 `getPausedVideoFrame`은 열지 않았다 |
| R-35 | `packages/core/src/adapters/types.ts:1-15`, `gsap.ts:1-60`, `packages/core/src/index.ts:365-368`, `docs/concepts/frame-adapters.mdx:6-93`, `docs/concepts/determinism.mdx:38-62`, `docs/packages/core.mdx:171` | 없다 주장의 검색: `rg -n "FrameAdapter\|createGSAPFrameAdapter\|FrameAdapterContext" packages/core/src/runtime packages/engine/src packages/producer/src packages/player/src packages/studio/src packages/cli/src --glob '!*.test.ts'`가 결과 없음이다. 저장소 전체에서 이 이름이 있는 비테스트 파일은 `packages/core/src/adapters/*`, `packages/core/src/index.ts`, `packages/core/README.md`, `docs/concepts/frame-adapters.mdx`, `docs/packages/core.mdx`뿐이었다. `packages/*/src` 밖의 `.agents/`·`registry/` 같은 디렉터리와 사용자 프로젝트에서 쓰는 코드는 보지 않았다. 문서 차이: `frame-adapters.mdx:13`은 GSAP·CSS·Anime.js·Lottie·Three.js·Web Animations·TypeGPU를 "frame adapter가 seek한다"로 쓰고, `determinism.mdx:42-45`는 렌더의 Seek 단계를 `seekFrame(frame)`로 설명한다. 구현에서는 렌더러가 `__hf.seek`를 부르고 런타임의 `RuntimeDeterministicAdapter`가 이를 처리한다. D3·Leaflet·Mapbox·MapLibre·Google Maps·frame source 어댑터는 문서에 없다 |
| T-01 ~ T-10 | 각 사례의 R-ID 행 | 구현에서 도출한 손계산이다. T-02: `delay − localTime = 0 − 0.5`. T-03: `normalizeInitialAnimationTimeMs(0, 2000) = 0`, `0 + (3000 − 2000)`. T-04: `3.5 × 30 = 105`, `105 % 60 = 45`. 브라우저에서 실행하지 않았다 |

### 2.2 코드 읽는 순서 [선택]

1. `types.ts:412-462`로 계약을 읽는다. 2. `init.ts:4114-4169`(`runAdapters`, readiness)와 `5436-5493`(등록, 첫 discover)으로 호출 쪽을 본다. 3. 가장 단순한 `animejs.ts`(51~129)로 "전역 배열을 읽어 `seek`"하는 기본형을 익힌다. 4. 지도·D3는 `_readiness.ts`와 `mapbox.ts` 한 개만 읽는다. 5. `css.ts`와 `waapi.ts`는 `_holdAnimationAt.ts`와 함께 읽는다. 6. `three.ts`와 `typegpu.ts`는 `seek-dispatch.ts`와 함께 읽는다. 7. `gsap.ts`는 마지막에 `createGsapAdapter`(`626-656`)를 먼저 보고 `seekGsapTimeline`(`302-332`)으로 간다. 나머지(`rerenderGsapTimelineAt`, authored order)는 필요할 때만 본다.

### 2.3 비교·재사용 출처 [선택]

다른 레포의 같은 기능 스펙은 없다. `FrameAdapter` 쪽은 R-35에 경계만 있다.

### 2.4 검토 기록 [필수, ready 스펙]

status가 `draft`라 아직 없다. 작성자는 모든 R-ID의 코드를 직접 읽었다. 메인 세션의 원본 대조 점검과 필요하면 독립 검토가 남아 있다.

## 적용 메모 [선택]

없음.
