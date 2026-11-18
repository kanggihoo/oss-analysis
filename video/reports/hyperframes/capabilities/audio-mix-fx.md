---
sha: "5979991d5f0af542fbb02ba906bdba4de52b2b64"
created: 2026-11-17
updated: 2026-11-17
sources:
  - packages/engine/src/services/audioMixer.ts
  - packages/engine/src/services/audioMixer.types.ts
  - packages/engine/src/services/audioFxRender.ts
  - packages/engine/src/services/audioFxWarmup.ts
  - packages/engine/src/services/audioVolumeEnvelope.ts
  - packages/engine/src/services/audioFailureDiagnostic.ts
  - packages/engine/src/services/aacEncode.ts
  - packages/engine/src/services/mediaHidden.ts
  - packages/engine/src/services/mediaTimelineWindow.ts
  - packages/engine/src/services/referenceResolver.ts
  - packages/engine/src/services/videoFrameExtractor.ts
  - packages/engine/src/utils/ffprobe.ts
  - packages/engine/src/utils/mediaPathSegment.ts
  - packages/engine/src/config.ts
  - packages/core/src/audioGain.ts
  - packages/core/src/audioFade.ts
  - packages/core/src/audioFx.ts
  - packages/core/src/audioAutomation.ts
  - packages/core/src/audioGroups.ts
  - packages/core/src/audioCarve.ts
  - packages/core/src/compiler/timingCompiler.ts
  - packages/studio/src/components/editor/carveOutput.ts
  - packages/studio/src/components/editor/useFxCarveNodes.ts
  - packages/producer/src/services/render/stages/assembleStage.ts
  - packages/core/src/audioLeveller.ts
  - packages/core/src/audibleVideo.ts
  - packages/core/src/audio/audioFxGraph.ts
  - packages/core/src/audio/audioFxTail.ts
  - packages/core/src/runtime/playbackRate.ts
  - packages/core/src/runtime/mediaVolumeEnvelope.ts
  - packages/core/src/runtime/audioFx.ts
  - packages/core/src/speedRamp.ts
  - packages/parsers/src/mediaDuration.ts
  - packages/producer/src/services/render/stages/audioStage.ts
  - packages/producer/src/services/render/stages/compileStage.ts
  - packages/producer/src/services/render/stages/probeStage.ts
  - packages/producer/src/services/render/stages/extractVideosStage.ts
  - packages/producer/src/services/render/audioDeliveryLimit.ts
  - packages/producer/src/services/render/audioPadTrim.ts
  - packages/producer/src/services/render/audioTruePeak.ts
  - packages/producer/src/services/render/encoderInterruption.ts
  - packages/producer/src/services/renderMediaCollector.ts
  - packages/producer/src/services/assetMediaType.ts
  - packages/producer/src/services/htmlCompiler.ts
  - packages/producer/src/services/renderOrchestrator.ts
  - packages/producer/src/services/distributed/plan.ts
  - packages/producer/src/services/audioMixer.ts
  - docs/reference/audio-effects.mdx
  - docs/reference/html-schema.mdx
depends:
  - ./composition-contract.md
status: ready
---

# 오디오 믹싱·효과

> 컴포지션 안의 `<audio>`와 소리가 있는 `<video>`를 입력으로 받아, 트랙마다 자르기·재생속도·효과·볼륨 곡선·페이드를 적용하고 서브믹스 그룹과 마스터 체인을 거쳐 하나의 AAC 파일(`audio.m4a`)로 합치는 렌더 오디오 단계를 설명한다.

## 1부. 동작 설명

용어를 먼저 정한다. **트랙**은 믹서가 다루는 오디오 하나(`AudioElement`, 준비 뒤에는 `AudioTrack`)다. **렌더 문서**는 `compileForRender`가 만든 인라인 HTML이다(선행 스펙의 1.1). **컴포지션**은 영상 한 편 또는 한 장면을 설명하는 HTML 파일이고 바깥 요소에 `data-composition-id`가 있다.

### 1.1 한눈에 보는 흐름 [필수]

1. **수집(producer, 컴파일 단계).** `collectRenderMedia`가 렌더 문서에서 `parseAudioElements`를 불러 `<audio>`와 소리 있는 `<video>`를 `AudioElement[]`로 만들고, `parseMasterFxChain`이 루트의 `data-fx-chain`을 읽는다. 로컬 경로가 프로젝트 밖이면 경고를 남기고 트랙을 뺀다(R-01~R-07).
2. **보정(producer, probe 단계).** 브라우저에서 media를 다시 읽어 `muted` 오디오를 빼고 src·타이밍·볼륨을 맞춘다. GSAP이 `volume`을 움직이면 타임라인을 최대 60Hz로 훑어 `volumeKeyframes`를 만든다. 파일에 소리가 있는 video는 `<id>-audio` 트랙으로 추가한다(R-08, R-09).
3. **호출(producer).** 오케스트레이터가 `runAudioStage`를 부른다. 길이는 `totalFrames × fps.den / fps.num`초다. 트랙이 0개면 ffmpeg를 부르지 않는다(R-10).
4. **트랙 준비(engine, 병렬).** 트랙마다 src 해석 → URL이면 다운로드 → 존재·문서 여부 검사 → (길이 미정이면 probe) → ffmpeg로 `mediaStart`부터 필요한 만큼 잘라 48kHz 스테레오 16bit WAV로 변환(재생속도, 루프 포함) → `data-fx-chain`이 있으면 headless Chrome에서 효과 적용 → 볼륨 곡선을 샘플에 곱해 넣는다(R-11~R-14, R-20~R-22).
5. **그룹 서브믹스(engine).** `data-audio-group` 멤버는 그룹별로 단위 이득으로 합쳐 float WAV 하나로 만들고, 그룹의 효과·볼륨 곡선을 적용해 길이 전체를 가진 트랙 하나로 바꾼다(R-23, R-24).
6. **최종 합산과 인코딩(engine).** 각 트랙을 `atrim → volume → afade → adelay`로 시간축에 놓고 `amix normalize=0`으로 단위 이득 합산해 float WAV(`master-sum.wav`)를 만든다. `audioGain`을 한 번 곱하고, 마스터 체인이 있으면 적용한 뒤 AAC 192k로 인코딩해 `workDir/audio.m4a`를 쓴다. 인코더에 넣은 float WAV는 `audio-source.wav`로 남긴다(R-15~R-18).
7. **전달 한도(producer).** `audio.m4a`의 true peak가 -1 dBFS를 넘으면 `audio-source.wav`에 `truepeak` 효과를 걸어 다시 인코딩하고, 그래도 넘으면 전체 볼륨을 일정량 낮춘다(R-19). 어느 단계든 오디오 실패가 있으면 `audio_processing_failed` 경고가 되고 렌더가 `RenderQualityError`로 멈춘다(R-27~R-32). 성공하면 결과 경로를 assemble 단계가 받는다(범위 밖, 1.2).

### 1.2 범위·통합 지점 [필수]

- 제공: 오디오 트랙 수집 규칙, 속성 기본값과 잘못된 값 처리, 트랙 준비·효과·볼륨 곡선·페이드, 서브믹스 그룹, 마스터 체인, 합산 규칙, true-peak 한도, 실패 분류와 렌더 실패 정책.
- 제외와 이유:
  - 브라우저 프리뷰 재생의 오디오 라우팅(`core/src/runtime/webAudio*.ts`, `levelTap.ts`, 프리뷰 쪽 `mediaVolumeEnvelope.ts` 사용부)은 요청 범위 밖이다. 렌더와 같은 규칙을 공유하는 지점은 아래 연결점으로 한 줄씩만 쓴다.
  - CLI 오디오 분석·정규화 명령(`commands/audio.ts`, `normalize-audio.ts`, `beats.ts`)은 요청 범위 밖이다.
  - 효과 17종(docs는 16종이라 쓴다, R-20)의 파라미터 범위와 worklet DSP 내부(`core/src/audio/audioFxWorklets.ts`, `audioFxGraph.ts`의 노드별 구현), EQ·컴프·리버브 수치는 개념 수준으로만 쓴다(R-20). 렌더 믹스의 경로(트랙 수집 → 합산 → 출력)와 실패 정책을 먼저 확정하기 위해서다. 분리 제안은 최종 보고에 적는다.
  - 보이스 카브·EQ 편집·leveller·preset 분석은 Studio가 작성 시점에 돌리는 분석이다. 렌더가 읽는 입력(생성된 `data-fx-chain`, `data-automation`)만 이 스펙에 있다(R-25).
  - `padOrTrimAudioToVideoFrameCount`(영상 프레임 수에 맞춘 길이 보정)와 mux, HLS 패키징은 assemble 단계이고 행 5다.
- 외부 의존·선행 계약: 선행 스펙 [컴포지션 계약·컴파일](composition-contract.md)이 `data-start` 참조 해석(R-04, R-05), `data-has-audio` 주입(R-08), `data-duration`·`data-end` 보정(R-09, R-12, R-13), legacy `data-layer`(R-11)를 정의한다. 이 스펙은 그 결과를 읽기만 한다. 호출자는 ffmpeg·ffprobe 실행 파일과 headless Chrome(효과 렌더용)을 제공해야 한다.
- 소유 상태·부작용: `workDir/audio` 아래 중간 WAV(`<id>-trimmed.wav`, `<id>-extracted.wav`, `<id>-fx.wav`, `group-<id>-<n>.wav`)와 `master-sum.wav`, `master-fx.wav`를 만들고 믹스가 끝나면 `workDir`을 지운다(실패 때도 지운다). 남기는 것은 `audio.m4a`와 호출자가 요청한 `audio-source.wav` 둘이다. 프로젝트 파일은 쓰지 않는다. URL 트랙은 `workDir`에 내려받는다.
- 프리뷰와의 연결점(각각 한 줄):
  - 효과 체인은 프리뷰와 렌더가 같은 파서(`parseAudioFxChain`)와 같은 Web Audio 그래프 빌더(`audioFxGraph.ts`)를 쓴다. 렌더는 같은 빌더를 headless Chrome의 `OfflineAudioContext`에서 돌린다(`core/src/runtime/audioFx.ts:9`, `engine/src/services/audioFxRender.ts:1-13`).
  - 읽을 수 없는 체인은 프리뷰에서 dry로 재생하고 렌더는 믹스 전체를 실패시킨다(`core/src/runtime/audioFx.ts:54`, `:71`).
  - `clampAudioGain`, `resolveAudioGroups`, `readAudioGroupVolume`, `readMasterFxChain`, `normaliseEnvelope`, `sampleAutomationLane`은 프리뷰와 렌더가 같은 함수를 공유한다(`core/src/audioGain.ts`, `audioGroups.ts`, `runtime/mediaVolumeEnvelope.ts`, `audioAutomation.ts`).
  - 다르게 동작하는 곳은 하나다. 렌더는 볼륨 곡선을 PCM 샘플에 미리 곱해 넣고(R-13), 프리뷰는 재생 중 gain으로 건다(docs `reference/audio-effects.mdx`의 "Preview and render" 표).

### 1.3 인터페이스와 데이터 의미 [필수]

속성 이름은 외부 계약이라 원문 그대로 쓴다. "잘못된 값"은 파싱 실패, 비유한수, 범위 밖을 말한다.

| 속성·요소 | 값과 기본값 | 의미와 잘못된 값 처리 |
|---|---|---|
| `<audio id src>` | `id`(렌더 문서는 `data-hf-render-id` 우선)와 src(`src` 속성, 없으면 `<source src>`)가 모두 필요 | 둘 중 하나라도 없으면 트랙이 아니다. 경고 없이 제외한다(R-01) |
| `<video id data-has-audio="true">` | `muted` 속성이 없을 때만 | 트랙 id는 `<id>-audio`, `type:"video"`다(R-02) |
| `data-start` | 숫자 또는 참조. 없거나 빈 값이면 0 | 참조 해석은 선행 스펙 R-04, R-05 |
| `data-end`, `data-duration` | `Number()`로 읽히는 유한수 | `data-end`가 유한수면 그 값이 `end`다. 아니면 `data-duration > 0`일 때 `start + duration`. 둘 다 아니면 `end = 0`이고 길이 미정이다(R-04) |
| `data-media-start`, `data-playback-start` | 0 이상 수(초). 기본 0 | `data-playback-start`를 먼저 보고, 무효·음수이면 `data-media-start`, 그것도 무효이면 0(R-03) |
| `data-playback-rate` | 0.1~10. 기본 1 | 양수로 읽히면 [0.1, 10]으로 자른다. 아니면 요소의 기본 속도(없으면 1). `data-automation`에 `rate` lane이 있으면 lane이 우선한다(R-03) |
| `loop` | 속성 존재 여부 | 있으면 `loop:true`. 소스 길이를 넘는 구간은 처음 구간(in-point 이후)을 반복해 채운다(R-11) |
| `data-volume` | `parseFloat`. 없거나 빈 문자열이면 1 | 숫자가 아니면 이후 `clampAudioGain`이 1로 바꾼다. 범위는 0~3.981(+12 dB). `"0"`은 무음이다(R-03) |
| `data-fade-in`, `data-fade-out` | 초. 기본 없음 | `parseFloat` 결과가 유한 양수가 아니면 없는 것으로 본다. 합이 클립 길이를 넘으면 같은 비율로 줄인다(R-14) |
| `data-fx-chain` | JSON `{version:1, nodes:[...]}` | `<audio>`, `<video>`, `<hf-audio-group>`, 루트(마스터). 읽을 수 없으면 렌더 실패(R-20, R-28) |
| `data-automation` | JSON `{version:1, lanes:[...]}` | `<audio>`, `<video>`, `<hf-audio-group>`. 읽을 수 없으면 렌더 실패. 루트의 것은 마스터 automation으로 읽지 않는다(R-21, R-28) |
| `data-audio-group` | 그룹 id 문자열 | `<audio>`와 소리 있는 `<video>`만 멤버가 된다. 빈 문자열이면 그룹 없음(R-23) |
| `<hf-audio-group id>` | `data-label`, `data-volume`(기본 1), `data-hidden`, `data-fx-chain`, `data-automation` | 그룹 버스 설정이다. 요소가 없어도 멤버만 있으면 그룹은 성립한다(R-23) |
| `data-hidden` | 속성 존재 여부 | 자기 자신, 조상, 속한 그룹 요소 중 하나에 있으면 트랙을 믹스에서 뺀다(R-01) |
| `data-layer` | 정수 | `AudioElement.layer`로 읽기만 한다. 믹스는 쓰지 않는다(R-05) |
| `data-fx-carve` | JSON | 렌더가 읽지 않는다(R-25) |
| 환경변수 `PRODUCER_AUDIO_GAIN` | 숫자, 기본 1 | 최종 합산에 한 번 곱하는 마스터 이득(`EngineConfig.audioGain`). 0 미만은 설정 검사에서 거부된다(R-15) |
| 환경변수 `FFMPEG_PROCESS_TIMEOUT_MS` | 기본 300000 ms | ffmpeg 하위 프로세스의 무진행 제한 시간(R-27) |

| 연산·데이터 | 입력·출력 | 의미·제약 |
|---|---|---|
| `parseAudioElements(html)` | string → `AudioElement[]` | 순수 함수. 파일을 읽지 않는다. 문서 순서(audio 먼저, 그다음 video)로 반환한다 |
| `parseMasterFxChain(html)` | string → string? | 루트(`[data-composition-id]` 중 조상에 컴포지션이 없는 첫 요소)의 `data-fx-chain` 원문 |
| `processCompositionAudio(elements, baseDir, workDir, outputPath, totalDuration, signal?, config?, compiledDir?)` | → `MixResult` | 믹스 전체를 실행한다. 실패는 대부분 `success:false`와 `failures[]`로 돌려주고, 효과 렌더 실패(`AudioFxRenderError`)만 reject한다(R-28) |
| `runAudioStage(input)` | → `AudioStageResult` | producer가 mixer를 감싼다. `audioOutputPath`는 항상 `workDir/audio.m4a`이고 `hasAudio`는 믹스 성공 여부다 |
| `applyAudioFxChain(inputWav, chain, outputWav, options)` | → `{path, envelopeBaked}` | 효과를 headless Chrome에서 적용한다. 켜진 노드가 없으면 `inputWav`를 그대로 돌려준다 |
| `MixResult`, `AudioProcessingFailure` | 타입 C-17 | `failures[]` 항목은 `stage`, `reason`, `owner`(`user`/`system`), `retryable`, `elementId?`, `detail`(2000자 제한, URL과 절대 경로는 가린다) |

### 1.4 행동 규칙과 남은 질문 [필수]

**A. 입력 수집**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `parseAudioElements`가 `audio[id]` 요소를 본다 | 다음 중 하나면 그 요소는 트랙이 아니다. 경고는 없다. ① 파서 선택자가 `audio[id]`라서 `id` 속성이 없는 요소는 `data-hf-render-id`만 있어도 트랙이 아니다(트랙 id는 렌더 id가 있으면 그것, 없으면 `id`). src가 없는 요소도 제외한다. ② 자기 또는 조상에 `data-hidden`이 있다. ③ 속한 `<hf-audio-group>`에 `data-hidden`이 있다(그룹 안 멤버에는 표시가 없어도 전부 빠진다). ④ `data-duration`이 0 이하로 읽힌다(음수 포함), 또는 `data-end`가 읽히고 그 값이 해석된 `start` 이하다. 이 제외는 볼륨을 0으로 두는 것이 아니고 트랙을 믹서에서 빼는 것이다. | 코드 확인 |
| R-02 | `video[id][data-has-audio="true"]` 요소 | `isAudibleVideoElement`(`muted` 속성이 없고 `data-has-audio`가 없거나 `"true"`)를 통과하면 R-01의 나머지 조건을 같은 방식으로 적용해 `<id>-audio`, `type:"video"` 트랙이 된다. 선택자가 `data-has-audio="true"`를 요구하므로 이 파서에 속성이 없는 video를 직접 넣으면 트랙이 아니다. 렌더 경로에서는 `compileTimingAttrs`가 `muted`가 없는 video에 `"true"`를 넣어 준다(선행 스펙 R-08). | 코드 확인 |
| R-03 | 속성 읽기 기본값과 잘못된 값 | 1.3 표를 따른다. 핵심은 세 가지다. `mediaStart`는 `data-playback-start`가 먼저이고(문서 `html-schema.mdx:134`와 다르다, 2.1), 값은 `Number()`로 읽히는 0 이상이어야 한다(`"2s"`는 무효). `data-volume`은 `parseFloat`이라 `"2x"`는 2다. 볼륨은 항상 `clampAudioGain`을 거쳐 0~3.981이 된다. | 코드 확인 |
| R-04 | 시작·끝 시각 | `start`는 `data-start`가 있으면 선행 스펙 R-04(b)의 Node 정적 해석기(`resolveReferencedStart`)로 구하고, 없으면 0이다. `end`는 R-01·1.3 표의 순서(`data-end` 유한수 → `start + data-duration` → 0)다. `end - start ≤ 0`이면 길이 미정이고 준비 단계에서 소스 끝까지 재생한다(R-12). | 코드 확인 |
| R-05 | `data-layer` | `AudioElement.layer`에 저장하지만 믹서·producer 오디오 코드에서 읽는 곳을 찾지 못했다. 겹치는 트랙의 순서나 우선순위에 쓰이지 않고 합산은 모든 트랙을 같은 가중치로 더한다(선행 스펙 R-11). | 코드 확인(검색 범위는 2.1) |
| R-06 | `collectRenderMedia`가 `parseAudioElements` 결과를 렌더 문서의 호스트 창(서브 컴포지션 호스트의 시작·길이·in-point)에 올린다 | 각 트랙의 `start`, `end`를 루트 timeline 기준으로 바꾸고, 호스트 in-point가 앞부분을 자르면 `mediaStart`와 `playbackRate`(lane일 때)도 바꾼다(R-35). 호스트 창은 `collectHostWindows`가 렌더 문서의 `video, audio, img[src]`마다 한 번 계산해 id(렌더 id, 없으면 `id`)로 모아 둔다. 조회 키는 트랙 id이고 video의 `<id>-audio`는 접미사를 떼어 video 요소의 창을 쓴다. 같은 author id가 둘 이상이면 먼저 나온 요소의 창만 쓰고, 렌더 id가 있는 요소는 같은 id를 덮어쓴다(`:143`). 창이 없는 id는 루트 창(offset 0, 한계 없음, local basis)이다. 창은 요소의 조상 중 `[data-composition-id], [data-composition-src], [data-composition-file]`인 호스트를 루트부터 차례로 접어 만든다(C-18). 각 호스트의 시작은 media와 같은 `resolveReferencedStart`로 풀어 `data-start="hook"` 같은 참조도 읽고, 끝은 런타임과 같은 `resolveAuthoredTimingWindow`로 구한다(`data-duration`이 0보다 크면 `start + duration`, 아니면 `data-end`가 `start`보다 클 때 그 값, 둘 다 아니면 끝없음). `toAbsoluteWindow`는 `start`와 `end`에 호스트 origin(offset)을 더하고(basis가 `global`이면 더하지 않는다), 호스트 끝 한계(limit)로 `end`를 자르며(루트 호스트, 즉 첫 번째 호스트이면서 `data-composition-src`·`data-composition-file`이 없는 호스트의 끝은 limit에 넣지 않는다. 루트 끝은 렌더 길이이고 자르면 clip fade-out이 움직이기 때문이며 `:108`, `:119-121`이다. 그래서 루트의 `data-duration`은 트랙을 자르지 않는다. 반면 서브 컴포지션 호스트나 루트가 아닌 인라인 호스트의 끝은 limit이 된다. in-point가 0보다 큰 호스트는 루트여도 slot을 만들고, 그 루트의 slot 끝은 `Infinity`다. `:111-113`), in-point 호스트의 slot 안에 남는 구간을 `played`로 구한다(C-18). 트랙의 `data-end`가 없어 `end === 0`이면 `placeAudio`가 `Infinity`로 바꿔 넣고, 결과 `end`가 유한수이면 그 값을, 아니면(바깥에 한계도 slot 끝도 없을 때) 0을 돌려준다. 즉 길이 미정 트랙도 한계가 있는 서브 컴포지션 호스트 안에서는 호스트 끝에서 잘린 유한한 `end`를 받는다. 다음 경우에는 트랙을 빼고 `droppedMediaIds`에 id를 넣어 probe 단계가 다시 추가하지 못하게 한다. ① 절대 `start`가 limit 이상이다. ② 잘라 낸 구간 `played`가 비는데(`played.end === played.start`) 원래 절대 구간은 길이가 있었다(`absolute.end > absolute.start`). 길이 0인 구간(`end === start`)은 빠지지 않는다. `data-hidden`인 video의 소리는 이 단계가 아니고 R-01의 `memberGroupHidden`/`isHidden`이 정한다. | 코드 확인 |
| R-07 | 컴파일 직후 `dropMediaOutsideProject`와 `preflightCompositionAssetMediaTypes`가 `composition.audios`를 본다 | ① 로컬 src가 프로젝트·compiled·downloads 폴더 밖이거나 비공개 경로이면(`allowOutsideProjectAssets`가 없을 때) `log.warn`을 남기고 그 트랙을 목록에서 뺀다. 렌더는 계속된다. ② 로컬 파일이 있고 probe가 되는데 `<audio>`로 선언된 파일에 디코드 가능한 오디오 스트림이 없으면 `AssetMediaTypeMismatchError`를 던져 렌더가 시작 전에 멈춘다. 파일이 없거나 probe가 안 되는 경우는 이 검사가 건드리지 않고 R-27로 간다. ③ 이 사전 검사(`notMediaReferences`, `assetMediaType.ts:136-145`)의 텍스트 문서(HTML·XML·JSON) 거부(`isNotMediaPayload`)는 `<video>` 참조에만 적용되고, `<img>` 참조에는 SVG가 아닌 markup·JSON을 거부하는 별도 검사(`isNotImagePayload`)가 걸린다. 오류는 `NotMediaPayloadError`다(`AssetMediaTypeMismatchError`보다 먼저 던진다). 오디오 트랙의 문서 src는 믹서가 트랙 단위로 거부한다(R-27). 다만 HLS playlist가 폴더 밖을 가리키는지 보는 `playlistLeavesItsFolder`는 audio 참조에도 적용되어 해당하면 같은 `NotMediaPayloadError`다. ②의 검사는 video가 만든 `<id>-audio` 트랙도 `audio` 참조로 포함한다(R-34). | 코드 확인 |

**B. probe 단계 보정과 video 소리**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-08 | probe 단계가 브라우저 DOM의 media를 `discoverMediaFromBrowser`로 읽는다 | `muted`인 `<audio>`(속성 또는 `.muted` 프로퍼티)는 `composition.audios`에서 제거된다. `muted` video는 `videos[].hasAudio`만 꺼지고 `audios`에서는 태그가 audio이고 `id`가 같은 항목만 지우므로, `.muted`만 스크립트로 건 video의 `<id>-audio` 트랙(정적 파싱에서 이미 만들어진 것)은 믹스에 남는다. 이미 있는 트랙은 src가 달라졌으면 바꾸고, `end`는 브라우저 값 `projectedEnd`와 비교해 정한다(`projectedEnd`가 0 이하이면 기존 값, src가 바뀌었고 길이가 추정값이면 `projectedEnd`, 기존 `end`가 0 이하이면 `projectedEnd`, 그 밖에는 둘 중 작은 값). 루프 여부를 브라우저 값으로 덮고, 브라우저 `volume > 0`이고 다르면 `volume`을 브라우저 값으로 바꾼다. 또 `adoptRuntimeMediaTiming`이 기존 트랙(audio, video의 `-audio`)에 브라우저 타이밍을 덮는다. 속도는 기존 트랙의 `playbackRate`가 상수(숫자)일 때만 바뀐다. 이미 lane인 트랙은 수집 단계가 앞자르기를 반영해 두었으므로 건드리지 않는다. 브라우저 속도가 상수이면 그 값을 그대로 받고, lane이면 이미 앞자르기된 소비량 `consumed = max(0, entry.mediaStart - authored)`를 `timeAtSourceTime`으로 `head`로 바꾼 뒤 `mediaStart += sourceTimeAt(lane, head) - consumed`로 보정하고 `playbackRate = shiftRateLane(lane, head)`를 적용한다(`probeStage.ts:262-271`). 그다음 브라우저 `mediaStart`가 0보다 크고 저작 값과 다르면 그 차이만큼 `mediaStart`를 옮긴다. DOM에는 있으나 정적 파싱에 없던 `<audio>`는 `layer:0`, `type:"audio"`로 새로 추가한다(`compiled.droppedMediaIds`에 있는 것은 제외). 이어서 `composition.audios`가 있으면 GSAP 루트 timeline을 `min(60, max(1, fps))`Hz로 seek해 각 클립의 `el.volume`을 읽고(`data-volume`이 시드, 범위 0~3.981), 값이 바뀐 지점만 남긴 `volumeKeyframes`를 만든다. 정적 `data-volume`과 모두 같으면 keyframe을 만들지 않는다. | 코드 확인 |
| R-09 | `appendAutoDetectedVideoAudio` | 렌더가 추출한 video 중 파일에 오디오 스트림이 있고(`metadata.hasAudio`), 요소가 `hasAudio`이며 숨김이 아니고, 같은 `src`의 오디오 트랙이 아직 없으면 `{id:"<id>-audio", layer:0, volume:1.0, type:"video", start/end/mediaStart/playbackRate/loop는 video 값}` 트랙을 추가한다. 이 경로의 트랙은 `data-volume`, 페이드, `fxChain`, `automation`, 그룹을 가지지 않는다. | 코드 확인 |

**C. 트랙 준비와 볼륨**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-10 | `runAudioStage` 호출 | `audios.length === 0`이면 `processCompositionAudio`를 부르지 않고 `hasAudio:false`, 오류 없이 돌려준다. 이때 `masterFxChain`은 읽지도 검증하지도 않아 마스터 체인만 있는 컴포지션은 오디오 단계가 건너뛰어진다. 있으면 믹서를 부르고 `duration = totalFrames * fps.den / fps.num`을 그대로 `totalDuration`으로 준다. `hasAudio`는 믹서의 `success`이고, 실패하면 `audioError`(믹서의 `error` 문자열)와 `audioFailures`를 채운다. 믹서가 `AudioFxRenderError`로 reject하면 stage가 잡아 `hasAudio:false`, `audioError`, 합성한 `internal` 실패 한 건(`owner:"system"`, `retryable:false`)으로 바꾼다. 취소(abort)는 이 변환 전에 `assertNotAborted()`로 원래 모양대로 던진다. | 코드 확인 |
| R-11 | 트랙 준비(`extractAudioSegment`) | ffmpeg로 `mediaStart`부터 `sourceTimeAt(rate, 길이)`초를 읽어 `pcm_s16le`, 48000Hz WAV를 쓴다. 모노는 `pan=stereo\|FL=FL+FC\|FR=FR+FC`(3 dB 손실 없이 양쪽에 복제), 그 밖에는 `-ac 2`다. 상수 속도는 `atempo`(0.5~2 단계로 나눈 피치 유지 체인), `rate` lane은 0.25초 조각(최대 240조각)마다 평균 속도로 `atempo`를 걸어 이어 붙인다. 입력 seek가 안전하지 않은 파일(스트림 시작 시각이 다른 경우)은 `atrim`으로 시간 기준 자른다. 루프는 소스 구간이 필요한 길이보다 짧고 길이를 알 때만 한 주기 WAV를 만들어 `-stream_loop -1`로 반복한다. 준비 동시 실행은 로컬 `max(2, floor(CPU/2))`개, URL은 16개로 제한한다. 모든 중간 파일은 `mediaIdPathSegment(id)`로 안전화한 이름을 쓴다. | 코드 확인 |
| R-12 | 트랙 하나의 준비 순서 | ① src 해석(`resolveProjectRelativeSrc`, 브라우저 URL 의미 그대로). ② `urlByAbsentLocalPath`에 있으면 원격 URL을 직접 읽고(사이드카 있으면 사용), 아니면 `assetRoots` 밖·비공개 경로 거부. ③ http(s) src는 `workDir`로 내려받는다. ④ 파일 존재 확인. ⑤ 텍스트 문서 여부 확인. ⑥ `end - start ≤ 0`이면 `console.warn("... length is unknown ...")`을 남기고 ffprobe로 소스 길이를 재서 `end`를 `start + (소스길이 - mediaStart)/속도`로 정한다(결과가 0 이하이면 소스 전체 길이). ⑦ video는 `<id>-extracted.wav`, audio는 `<id>-trimmed.wav`를 만든다. ⑧ 효과 체인(R-20), ⑨ 볼륨 곡선 굽기(R-13). 어느 단계든 실패하면 `failures`에 쌓고 그 트랙만 멈춘다(R-27). | 코드 확인 |
| R-13 | 볼륨 곡선 결정과 적용 | 곡선 출처는 `data-automation`의 `volume` lane(우선)과 probe의 GSAP 샘플(`volumeKeyframes`)이고, lane이 있으면 probe 값은 쓰지 않는다. `gainBeforeFx`는 체인에 켜진 노드(`enabledAudioFxNodes`)가 1개 이상일 때 참이다(노드가 전부 `enabled:false`이면 거짓). lane 키프레임 값은 `gainedVolume(v, data-volume, gainBeforeFx)`다. `gainBeforeFx`가 거짓이면 `clamp(data-volume × lane)`이고, 참이면 `data-volume`이 효과 앞에서 따로 곱해지므로 키프레임에는 `clamp(g·lane)/g`만 담는다(곱이 3.981을 넘는 구간의 몫만 남는다). 시각은 클립 로컬 `t`에 `start`를 더한 컴포지션 초이고, 굽은 구간은 초당 30점(최대 4096점)으로 펴서 선형 보간이 곡선을 펴지 않게 한다. `data-volume`이 적용되는 곳은 셋이다. ⓐ `gainBeforeFx`이면 `inputGain = clipGain(data-volume, tweened)`가 효과 앞에서 샘플에 곱해진다(lane이 있어도 마찬가지다. lane 없이 GSAP 키프레임만 있는 `tweened`이면 `inputGain`은 1이고 GSAP 값이 절댓값이다). ⓑ 체인이 없거나 전부 꺼져 있고 lane이 있으면 `data-volume`은 키프레임 값에 이미 곱해져 있다. ⓒ 곡선이 없으면 `data-volume`은 믹스 필터의 `volume`에 남는다. 믹스에서 트랙 `volume`은 곡선을 구웠거나(`bakedEnvelope`) `gainBeforeFx && !tweened`이면 1.0이고 아니면 `data-volume`이다. 곡선을 굽는 경로는 셋이다. ① 켜진 체인 노드가 있으면 효과 렌더 중 float 샘플에 곱한다(`envelopeBaked:true`, ±1로 자르기 전). ② 체인이 없거나 노드가 전부 꺼져 있으면 `applyAudioFxChain`이 `envelopeBaked:false`로 바로 돌아오므로 `applyVolumeEnvelopeToWav`가 WAV의 16bit PCM 또는 32bit float 샘플에 곱해 덮어쓴다(16bit는 -32768~32767로 자른다). ③ WAV 형식이 맞지 않아 ②가 `false`를 돌려주면 ffmpeg `volume=<if(lt(t,...))식>:eval=frame` 표현식으로 믹스 단계에서 적용한다(키프레임은 선형 단순화를 거쳐 최대 32점). | 코드 확인 |
| R-14 | 페이드 | `data-fade-in`/`data-fade-out`(초)은 믹스 필터에서 `volume` 다음에 `afade`(선형)로 붙는다. 클립 길이는 `end - start`이고 fade-out은 `st = 길이 - fadeOut`에서 시작한다. 두 페이드의 합이 길이보다 길면 같은 비율로 줄여 클립 안에서 만나게 한다. 페이드는 효과 체인과 볼륨 곡선 뒤에 걸리고, 믹서가 쓰는 길이는 FX tail을 포함하지 않는 `end`다. | 코드 확인 |

**D. 시간축 배치와 합산, 출력**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-15 | 최종 합산(`mixAudioTracksFlat`, 트랙 96개 이하) | 트랙마다 `[i:a]atrim=0:<길이+tail>,<volume>,<afade>,adelay=<round(start×1000)>\|<같은 값>`을 건다(C-04). 합산은 `amix=inputs=N:duration=longest:dropout_transition=0:normalize=0`이라 단위 이득으로 더하며 트랙이 끝나도 남은 트랙이 커지지 않는다. 합산 뒤 `volume=audioGain`을 한 번 곱하고 `apad, asetpts=N/SR/TB, atrim=0:totalDuration`으로 정확히 영상 길이에 맞춘다. 출력은 `pcm_f32le`, 48000Hz WAV이고 `-t totalDuration`이다. `amix`에 `normalize` 옵션이 없는 ffmpeg(stderr에 `normalize`와 option not found 계열 문구)에서는 모든 트랙을 앞에서 `totalDuration`까지 패딩하고 `volume=audioGain×N`으로 보정하는 그래프로 한 번 다시 돌린다. 필터 그래프는 argv 길이 제한을 피하려 파일(`-filter_complex_script`)로 전달하고, 그 옵션이 없다고 ffmpeg가 말하면 `-/filter_complex`로 한 번 더 돌린다. | 코드 확인 |
| R-16 | 트랙이 `MAX_MIX_INPUTS = 96`개를 넘는다 | 96개씩 조각으로 단위 이득 합산해 float WAV를 만들고 앞 결과와 이어 합산한다(조각 합산은 그룹 서브믹스와 같은 함수 `mixGroupMembersFlat`). 마지막에 합친 하나를 입력으로 R-15를 돌린다. 트랙 수 상한은 없다. | 코드 확인 |
| R-17 | 트랙 준비는 병렬이고 합산은 순서가 있다 | 준비 결과는 `elements` 배열의 원래 순서로 모은다. 그 가운데 그룹이 없는 트랙이 문서 순서대로 평면 목록에 먼저 들어가고, 그룹 서브믹스 트랙은 그룹 루프에서 그 뒤에(첫 멤버가 나온 그룹 순서로) 붙는다. 따라서 최종 합산의 입력 순서는 문서 순서 전체가 아니다. 부동소수점 합이 입력 순서에 따라 달라지기 때문에 이 순서를 고정한다. | 코드 확인 |
| R-18 | 마스터 체인과 인코딩(`mixThroughFloatSum`) | 합산 float WAV에 마스터 체인이 있으면 `applyAudioFxChain(..., trackId:"master")`를 한 번 적용한다(automation과 `tailSeconds` 계산은 넘기지 않는다). 이어서 `encodeAac`가 AAC 192kbps, 48kHz로 `workDir/audio.m4a`를 쓴다(구간 수는 `floor(길이/60)`을 1~8로 자른 값이고 구간을 병렬 인코딩해 ADTS 프레임을 이어 붙인다). 파일명 `audio.m4a`는 MP4 계열 컨테이너가 AAC priming을 edit list로 기록하기 위해서다. 채널은 준비 단계가 모든 트랙을 `-ac 2` 또는 `pan=stereo`로 맞추고(`audioMixer.ts:175-176`), 합산은 `-ar 48000`만, `encodeAac`는 `aresample=48000`만 지정하고 `-ac`가 없으므로 스테레오가 유지된다. `supportsSettsDuration()`이 false인 ffmpeg(setts에 `duration` 옵션이 없는 5.0 미만)에서는 구간 분할 없이 한 번에 AAC 인코딩한다. `keepEncoderInputAt`이 주어지면 인코더에 넣은 WAV를 그 경로로 옮겨 둔다(producer는 `workDir/audio-source.wav`). | 코드 확인 |
| R-19 | 전달 true-peak 한도(`guardDeliveryPeaks`, 믹스 성공 후) | ① `limitDeliveryPeaks`: `audio-source.wav`가 없으면 이 단계를 건너뛰고 `success:true`다. 있으면 `audio.m4a`의 true peak(ffmpeg `ebur128=peak=true`)이 -1 dBFS 이하면 아무것도 하지 않는다. 넘으면 `audio-source.wav`에 `truepeak` 효과(ceiling -1 dBTP에서 시작)를 걸어 다시 AAC 인코딩하고 다시 잰다. 아직 넘으면 ceiling을 넘은 만큼과 0.05 dB(`PASS_HEADROOM_DB`)를 더 낮춰(최저 -3 dBTP) 최대 3번 되풀이하고 마지막 성공 결과를 `audio-source.wav`로 되돌려 둔다. ② `constrainAacTruePeak`: 그래도 -1 dBFS를 넘으면 `volume=-xdB` 전체 컷으로 최대 3번 재인코딩한다. 컷이 걸렸으면 `audioLoweredDb`를 돌려주고, 오케스트레이터(`recordLimiterAttenuation`)는 `job.audioLoweredDb`와 info 로그만 남긴다. `audio_lowered` 경고 문구는 CLI `packages/cli/src/utils/audioLoweredWarning.ts`가 만든다(범위 밖). 3번 뒤에도 넘으면 실패한다(R-31). | 코드 확인 |

**E. 효과 체인, automation, 그룹, 카브**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | `data-fx-chain` 입력 계약과 실행 방식 | `{version:1, nodes:[{type, id?, enabled?, params?, ...}]}`이고 `version`이 1이 아니거나 `nodes`가 배열이 아니거나 `type`이 레지스트리 `HF_AUDIO_FX`의 17종(gain, peaking, lowshelf, highshelf, highpass, lowpass, compressor, limiter, truepeak, gate, saturate, bitcrush, pitchshift, delay, chorus, phaser, reverb)에 없으면 `AudioFxChainError`다(알 수 없는 노드를 건너뛰지 않는다). `enabled:false`인 노드는 신호 경로에서 빠지고 켜진 노드가 하나도 없으면 효과 단계는 입력 WAV를 그대로 쓴다. 파라미터는 읽을 때 범위 안으로 자른다. 효과는 ffmpeg 필터가 아니고, 코어의 Web Audio 그래프 빌더를 headless Chrome의 `OfflineAudioContext`에서 돌리는 자체 구현이다(리버브 임펄스는 파라미터 시드 PRNG라 결정적). 입력이 512MiB를 넘으면 300초 창으로 나눠 렌더하고(pre-roll 10초 이상, 체인 기억 길이에 맞춰 최대 300초), 2GiB를 넘고 automation이 있으면 거부한다. 효과 파라미터 수치와 worklet 내부는 이 스펙에서 개념 수준으로만 다룬다(1.2 제외). | 코드 확인(효과 id), 파라미터 수치는 미확인 |
| R-21 | `data-automation` 입력 계약 | `{version:1, lanes:[{target, points:[{t, v, curve?, viaX?, viaY?}]}]}`. `target`은 `volume`, `rate`, `fx.<nodeId>.<param>`, `fx.preset.<presetId>`만 인정하고 그 밖은 `AudioAutomationError`(읽을 수 없는 target은 throw)다. lane당 최대 512점, 시각순 정렬, 같은 `t`는 뒤 것이 이긴다. `t`나 `v`가 수로 읽히지 않는 점은 버리고(숫자 문자열은 수로 받는다), `t`는 0 이상으로, `volume`·`rate`의 `v`는 해당 범위로 자른다. `resolveAutomation`이 체인에 없는 노드·파라미터의 lane을 조용히 버린다(오타난 `nodeId`는 효과 없음). 시계는 클립에 달린 lane이면 클립 시작이 0, 그룹에 달린 lane이면 컴포지션 시각이다. 곡선은 첫 점 이전은 첫 값, 마지막 점 이후는 마지막 값을 유지한다. `volume` lane은 `data-volume`과 곱해지고 곱이 3.981에서 막힌다. | 코드 확인 |
| R-22 | FX tail | 체인에 reverb, delay, chorus, pitchshift가 있고 해당 mix/wet이 0보다 크면 `chainTailSeconds`(노드별 tail의 합, 최대 5초)가 `tailSeconds`가 된다. 믹스에서 그 트랙은 `end - start + tailSeconds`까지 통과하고, 합산 뒤 `atrim=0:totalDuration`이 영상 끝을 넘는 부분을 자른다. 효과가 없는 트랙은 `end`에서 잘린다. 페이드와 `adelay`는 이 길이 기준으로 걸린다. | 코드 확인 |
| R-23 | 서브믹스 그룹의 멤버와 제외 | `data-audio-group`을 가진 `<audio>`와 소리 있는 `<video>`(`muted`나 `data-has-audio="false"`가 아님)가 `id`를 가지면 멤버다. 그룹 키는 렌더 문서의 `data-hf-group-render-id`가 있으면 그것, 없으면 속성 값이다. 그룹 요소는 태그가 `<hf-audio-group>`인 것만 인정한다(같은 id의 `<div>`나 `<audio>`는 버스가 아니다). 요소가 없으면 라벨은 id, 볼륨 1, 체인·automation 없이 평면 합으로 취급한다. 그룹 요소의 `data-hidden`은 모든 멤버를 트랙에서 뺀다(R-01). 그룹은 중첩되지 않고 한 클립은 하나의 그룹만 가진다. | 코드 확인 |
| R-24 | 그룹 서브믹스 처리 | 멤버는 트랙으로 각자 준비(자기 효과·볼륨 곡선 포함)된 뒤 `mixGroupMembers`가 단위 이득으로 합쳐 float WAV(`group-<안전화한id>-<순번>.wav`)를 만든다. 그룹 id는 `[A-Za-z0-9_-]` 밖의 문자를 `_`로 바꾸고 순번을 붙여 `workDir` 밖으로 나가지 못한다. 합산 이득은 `normalize=0`이면 보정 없음, 없는 ffmpeg에서는 그룹 자신의 멤버 수 N으로만 보정한다. 이어서 그룹 `data-automation`(시계 0, 길이 `totalDuration`, 이득은 그룹 `data-volume`)과 그룹 `data-fx-chain`을 같은 경로로 적용하되 `inputGain`은 없다. 즉 멤버의 `data-volume`은 멤버 단계에서 효과 앞에 걸리고(R-13), 그룹 `data-volume`은 그룹 효과 뒤, 곡선을 구웠으면 곡선 값 안에, 아니면 최종 믹스의 `volume`으로 걸린다. 결과를 `start 0, end totalDuration` 트랙(곡선을 구웠으면 `volume 1`, 굽지 못했으면 그룹 `volume`과 lane 키프레임을 실어 믹스의 volume 표현식이 처리)으로 바꿔 평면 트랙 목록에 더한다. 이후 합산은 그룹이 있는지 모른다. 그룹의 FX tail은 `end`가 영상 길이라 별도 계산 없이 영상 끝에서 잘린다. | 코드 확인 |
| R-25 | 보이스 카브(음악 덕킹) | 렌더 경로에는 카브 분석도 덕킹 코드도 없다. 카브는 Studio가 보이스 파일을 분석해 생성한 결과(음악 쪽 클립의 `data-fx-chain`에 `fromCarve:true`인 `peaking` 노드들과, 레벨을 낮추는 `data-automation` lane)만 렌더가 읽는다. 렌더는 그것을 일반 효과 체인과 automation으로 처리한다. `data-fx-carve`(설정 속성)는 렌더가 읽지 않는다. 카브의 `strength`는 `carveProfile`이 `maxCutDb 2+16s`, 대역 수 1~6, `duckDb 24s` 등으로 풀지만 이는 Studio 분석에서만 쓰인다. | 코드 확인(검색 범위는 2.1) |
| R-26 | 마스터 버스 | 루트 컴포지션(조상에 `[data-composition-id]`가 없는 첫 요소)의 `data-fx-chain`만 마스터 체인이다. 서브 컴포지션 루트의 것은 읽지 않는다. 마스터 automation은 없다. 합산 float WAV에 R-18대로 한 번 적용한다. 체인이 JSON이 아니거나 알 수 없는 type이면 서브믹스 전에 `stage:"mix"`, `reason:"internal"`, `owner:"user"`, `elementId:"master"` 실패로 믹스를 멈춘다. | 코드 확인 |

**F. 실패 처리**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-27 | 트랙 준비 중 개별 실패 | 사례마다 `failures`에 한 건을 쌓고 그 트랙의 준비만 멈춘다(다른 트랙은 계속 준비). ① 로컬 경로가 asset root 밖·비공개: `source/source_not_found`, `owner:user`. ② 파일 없음: `source/source_not_found`, `owner:user`. ③ 텍스트 문서(HTML·XML·JSON): `source/invalid_media`, `owner:user`. ④ URL 다운로드 실패: `download/download_failed`. HTTP 400·401·403·404·405·410·422, invalid URL, HTTPS 아님, 사설 주소, `UrlDownloadError`의 `http_not_found`·`http_rejected`·`invalid_payload`·`cancelled`는 `owner:user`, 그 밖은 `system`이고 `retryable`은 `UrlDownloadError.retryable`(그 외는 `!invalidSource`). ⑤ 길이 미정 트랙의 ffprobe 실패: `probe`(오디오 스트림 없음 등 `invalid_media`, 취소 `cancelled`, ffprobe 없음 `ffmpeg_unavailable`, 시간 초과 `ffmpeg_timeout`, 그 밖 `probe_failed`). ⑥ ffmpeg 준비·추출 실패: `extract`(video) 또는 `prepare`(audio), `invalid_media`(`owner:user`, stderr에 invalid data·moov atom not found 등), `ffmpeg_unsupported`(옵션 미지원), `ffmpeg_timeout`(무진행 `inactivity`, `retryable`), `ffmpeg_unavailable`(spawn 실패), `external_interruption`(`retryable`), `cancelled`, 그 밖 `ffmpeg_failed`. URL을 읽다 `invalid_media`나 `ffmpeg_failed`가 나면 `download_failed`, `system`, `retryable`로 바꾼다. ⑦ 그 밖의 예외: `internal/internal`, `owner:system`. 일부 트랙만 실패했어도 나머지를 섞은 부분 믹스를 만들지 않는다. 준비가 모두 끝난 뒤 `failures`가 하나라도 있으면 `bail()`이 `workDir`을 지우고 `success:false`, `tracksProcessed`, `error`("Audio processing failed: <detail들>", 2000자 제한), `failures`를 돌려준다. | 코드 확인 |
| R-28 | 효과·automation 오류 | 체인·automation JSON이 읽히지 않거나 알 수 없는 노드 type이면(`AudioFxChainError`, `AudioAutomationError`) 그 트랙의 `internal` 실패가 되어 R-27의 전체 실패로 이어진다(그룹 체인은 `stage:"mix"`, `internal`, `owner:system`, `elementId:<그룹 id>`). 반대로 효과를 렌더하다 나는 오류(`AudioFxRenderError`: 입력 WAV 없음·형식 미지원, 출력 샘플 없음, 브라우저 실행 실패, 취소, 2GiB 초과 automation)는 즉시 던진다. 형제 트랙의 ffmpeg를 취소하고 `workDir`을 지운 뒤 `processCompositionAudio`가 reject한다. dry 신호로 대체하지 않는다. 입력 WAV가 비어 있으면(트림이 소스 끝을 넘은 경우) 효과를 건너뛰고 입력을 그대로 쓴다. | 코드 확인 |
| R-29 | 믹스 단계의 재시도와 성능 저하 | 합산 ffmpeg 실패 시 ① `normalize` 미지원이면 R-15의 보정 그래프로 재시도한다. ② 곡선이 ffmpeg 표현식으로 남은 트랙이 있고 실패했으면 곡선 없이(기본 볼륨으로) 한 번 더 시도한다. 취소·`external_interruption` 검사는 경로마다 다르다. 평면 경로(`mixAudioTracksFlat`)는 ①②를 모두 `external_interruption`이 아니고 취소가 아닐 때만 재시도한다. 그룹 경로(`mixGroupMembersFlat`)는 ①에 어떤 검사도 없고 ②만 `!signal?.aborted`를 본다. 재시도가 성공하면 `success:true`로 돌려주고 `error`에 "Volume automation exceeded this ffmpeg build's expression limits; rendered at base volume"(그룹이면 그룹 id를 더한 문구)을 남긴다. 이 `error`는 성공 결과의 부가 정보라서 producer가 쓰지 않는다. `runAudioStage`는 `!hasAudio`일 때만 `audioError`를 만들므로(`audioStage.ts:264`) 이 degrade는 경고나 실패 없이 조용히 넘어가고 해당 트랙은 기본 볼륨(페이드는 유지)으로 렌더된다. 재시도 뒤에도 실패하면 `stage:"mix"` 실패(`success:false`)다. | 코드 확인 |
| R-30 | stage 결과를 받은 오케스트레이터 | `audioResult.audioError`가 있으면 `audio_processing_failed` 경고(메시지 "Audio mix failed; output would be video-only: ...", `details`에 `audioFailures`(최대 16건, 민감 필드 제거), `failureReasons`, `failureStages`, `failureOwner`(하나라도 `system`이면 `system`), `retryable`(모두 retryable일 때만 true))를 `applyRenderWarningPolicy`에 넣는다. 이 코드는 `strictness`와 상관없이 `audio_processing_failed`가 있으면 `RenderQualityError`를 던진다. 즉 오디오 실패는 영상만 있는 출력으로 계속되지 않고 렌더를 실패시킨다. 그 앞에서 `external_interruption` 실패가 있으면 `EncoderInterruptedError`(`retryable`)를 던진다. 분산 렌더 `plan.ts`도 같은 정책 함수를 쓴다. | 코드 확인 |
| R-31 | 전달 한도 단계의 실패 | ① `limitDeliveryPeaks`: `truepeak` 효과 렌더가 실패하면(취소 제외) 경고(`[audio] true-peak limit failed, the whole-mix cut applies`)를 남기고 이 단계만 건너뛴다. 재인코딩이 실패하면 오류를 돌려주고 stage가 `Audio true-peak limit failed`로 던진다. ② `constrainAacTruePeak`: 측정값이 비유한이면, 재인코딩이 실패하면, 3번 뒤에도 -1 dBFS를 넘으면 실패이고 stage가 `Audio true-peak check failed`로 던진다. 둘 다 `encoderFailureError`(외부 중단이면 `EncoderInterruptedError`)다. 단 `limitDeliveryPeaks`의 첫 `measure`와 마지막 `rename`은 try 밖이라(`audioDeliveryLimit.ts:50`, `:70`) 그 예외는 `encoderFailureError`를 거치지 않고 일반 `Error`로 전파된다. 즉 이 단계의 실패는 R-30의 경고 경로가 아니고 렌더를 바로 실패시킨다. | 코드 확인 |
| R-32 | 취소 | `AbortSignal`이 서면 대기 중인 트랙은 `cancelled` 실패(`owner:user`, `retryable:false`)를 남기고 실행 중인 ffmpeg는 중단한다. 합산 중 취소이면 `stage:"cancelled"`, `error:"Audio mix cancelled"`다. 한 트랙의 효과 오류는 내부 컨트롤러로 형제 작업을 취소한다. | 코드 확인 |
| R-33 | 개수·길이 한계 | 트랙 개수와 트랙 길이에 걸린 명시적 상한은 없다. 96개 초과는 조각 합산(R-16), 512MiB 초과 효과 입력은 창 렌더(R-20)로 처리한다. 모든 트랙은 영상 길이(`totalDuration`)에서 잘린다. `audioDeliveryLimit`이라는 이름은 길이 제한이 아니고 true-peak 한도(R-19)다. 렌더 믹스 밖에서는 클라우드 offload가 audio 파일당 1.5GB(`.wav`, `.mp3`)를 넘는 업로드를 거부하는 상한이 있으나(`packages/cli/src/cloud/offload.ts:67`, `:79-80`) 이 스펙의 범위 밖이다. | 코드 확인(부재 주장, 검색 범위는 2.1) |
| R-34 | 오디오 스트림이 없는 video(`muted` 없음, `data-has-audio` 없음) | 컴파일이 `data-has-audio="true"`를 넣고(선행 스펙 R-08), `collectRenderMedia`가 `<id>-audio` 트랙을 `composition.audios`에 넣고, `preflightCompositionAssetMediaTypes`가 `audios` 전체를 `expected:"audio"`로 검사해 `hasAudioStream`이 없는 파일을 mismatch로 모아 `AssetMediaTypeMismatchError`를 던진다. 따라서 렌더가 시작 전에 실패한다. 소리 없는 video는 `muted`로 선언해야 하고 문서는 린트 규칙 `video_missing_muted`를 말한다. | 코드 확인 |
| R-35 | `startAtPlayed`가 R-06의 `toAbsoluteWindow` 결과 `played`를 받는다(호스트 in-point `data-playback-start`/`data-media-start`가 0보다 큰 서브 컴포지션 안의 트랙) | `head = played.start - clip.start`(`clip.start`는 절대 `start`)가 0 이하이면 트랙은 그대로다. 0보다 크면 ① `loop` 트랙은 `start`만 `played.start`로 옮기고 `mediaStart`와 `playbackRate`는 바꾸지 않는다(루프가 `mediaStart`에서 도는 탓에 앞을 자른 만큼의 위상 차이가 남는다고 코드 주석이 인정한다). ② 그 밖의 트랙은 `start = played.start`, `mediaStart += sourceTimeAt(rate, head)`, `playbackRate = shiftRateLane(rate, head)`가 된다. `rate`는 `normalizeRateSpec(clip.playbackRate)`라 상수는 0.1~10으로 자른 값이고 lane은 그대로다. 상수 속도면 `mediaStart`가 `head × 속도`만큼 늘고 속도는 변하지 않는다. lane이면 `mediaStart`가 lane의 적분(head 구간에 소비되는 소스 시간)만큼 늘고, lane은 `head` 시점부터 시작하도록 앞이 잘리며 점의 시각이 `head`만큼 당겨진다(C-18). `end`는 `toAbsoluteWindow`가 이미 `played.end`로 정해 둔 값이고 이 함수가 바꾸지 않는다. 최종 믹스의 `adelay`는 이 `start`로 걸리므로 호스트 in-point가 자른 구간은 소리가 나지 않는다. 호스트 in-point가 0이면 slot이 만들어지지 않아 `played`는 `absolute`와 같고 이 함수는 항상 그대로 돌려준다. | 코드 확인 |

- 불변식: `parseAudioElements`와 `buildVolumeExpression`, `buildAtempoFilter`는 같은 입력이면 같은 출력이다(순수 함수). 같은 입력 파일·같은 순서의 트랙이면 합산 순서가 고정이라 합산 입력 순서에 따른 부동소수점 차이는 없다. 불변식이 깨지는 곳: 효과 렌더(headless Chrome)와 ffmpeg 버전에 따라 샘플 값이 달라질 수 있다(실행하지 않아 미확인).
- 미결정: 남은 항목이 없다. 소리 없는 video의 사전 검사 실패(R-34), 스크립트 mute video(R-08), 서브 컴포지션 호스트 창 계산(R-06, R-35)은 코드로 확인해 닫았다.

- 확인 한계: ffmpeg, ffprobe, headless Chrome을 실행하지 않았다. 필터 그래프 문자열과 분기를 코드를 따라 계산했다. 효과 16종의 파라미터와 worklet DSP, Studio 카브·leveller 분석 알고리즘은 열지 않았다. 호스트 창 계산은 코드를 읽어 확인했지만 실제 컴포지션으로 실행하지는 않았다(T-14는 손계산이고, 인라인된 렌더 문서에서 호스트에 `data-composition-src`가 유지되는지는 `htmlCompiler.ts:1128`의 호스트 조회까지만 확인했다). 외부 시스템(ffmpeg `amix`, `afade`, `atempo`, `ebur128`)의 정확한 수치 동작은 ffmpeg 문서를 확인하지 않았다(코드의 주석이 설명하는 의도를 따랐고 수치는 `미확인`).

### 1.5 필수 코드 참조 [필수]

라이선스는 Apache-2.0(overview 1절)이고 인용을 허용한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `packages/engine/src/services/audioMixer.ts:111-130` `formatFilterNumber`, `buildAtempoFilter` | 상수 속도를 0.5~2 단계 `atempo` 체인으로 나누는 알고리즘 | R-11 |
| C-02 | `packages/engine/src/services/audioMixer.ts:133-190`, `:233` `RAMP_SLICE_SECONDS`, `buildRampFilterComplex`, `preparedAudioOutputArgs`, `STEREO_CHANNEL_FILTER` | `rate` lane을 조각별 평균 속도로 굽는 그래프, 모노·스테레오 채널 처리 | R-11 |
| C-03 | `packages/engine/src/services/audioMixer.ts:219-342` `MAX_VOLUME_SEGMENTS`, `VOLUME_SIMPLIFY_EPSILON`, `simplifyVolumeKeyframes`, `buildVolumeExpression` | ffmpeg 표현식 경로의 키프레임 단순화와 `volume=...:eval=frame` 식 생성 | R-13 |
| C-04 | `packages/engine/src/services/audioMixer.ts:345-375` `buildFadeFilters`, `buildTrackInputFilter` | 트랙 필터 한 줄(`atrim, volume, afade, adelay, 선택적 apad`) | R-14, R-15, R-22 |
| C-05 | `packages/engine/src/services/audioMixer.ts:951-967` `buildFilterComplex` (안쪽 함수) | 최종 합산 그래프와 `audioGain` 곱, 보정 그래프 | R-15 |
| C-06 | `packages/engine/src/services/audioMixer.ts:1143-1157` `runOnce` 앞부분 | 그룹 서브믹스 그래프와 그룹 자신의 N 보정 | R-24 |
| C-07 | `packages/engine/src/services/audioMixer.ts:529-567` `volumeLaneKeyframes`, `packages/core/src/audioAutomation.ts:179-225` `volumeSegmentSampleCount`, `isBentSegment`, `gainedVolume`, `gainedVolumePoints` | `volume` lane을 PCM 굽기용 키프레임으로 바꾸고 이득 곱과 +12 dB 한도를 처리 | R-13 |
| C-08 | `packages/core/src/audioGain.ts:8-39` `MAX_AUDIO_GAIN_DB`, `MAX_AUDIO_GAIN`, `clampAudioGain`, `gainTimesLane`, `clipGain` | 볼륨 범위(0~3.981)와 잘못된 값 처리 | R-03, R-13 |
| C-09 | `packages/core/src/audioFade.ts:23-45` `readFadeSeconds`, `readElementFades`, `clampFadesToDuration` | 페이드 속성 읽기와 클립 안에서 만나게 줄이는 규칙 | R-03, R-14 |
| C-10 | `packages/core/src/runtime/mediaVolumeEnvelope.ts:29-62` `normaliseEnvelope`, `packages/engine/src/services/audioVolumeEnvelope.ts:75-199` `parseWavLayout`, `createEnvelopeWalker`, `scaleSamples`, `applyVolumeEnvelopeToWav` | 키프레임 정규화와 PCM 샘플에 곡선을 곱하는 굽기(16bit PCM과 32bit float) | R-13 |
| C-11 | `packages/core/src/audibleVideo.ts:1-16` `isAudibleVideoElement` | video가 소리 트랙인 조건 | R-02 |
| C-12 | `packages/parsers/src/mediaDuration.ts:11-23`, `:25-40`, `packages/core/src/runtime/playbackRate.ts:29-40`, `packages/core/src/speedRamp.ts:128-134` | `mediaStart`, 재생속도(clamp), `rate` lane 선택 | R-03 |
| C-13 | `packages/core/src/audio/audioFxTail.ts:28-135` | tail 길이 공식(delay, reverb, chorus, pitchshift)과 5초 상한 | R-22 |
| C-14 | `packages/core/src/audioGroups.ts:46-50`, `:118-181`, `:231-234` `readAudioGroupVolume`, `isMemberGroupHidden`, `resolveMasterBusElement`, `readMasterFxChain`, `resolveAudioGroups`, `isGroupableMember`, `packages/engine/src/services/mediaHidden.ts:1-35` | 그룹 멤버십, 키, hidden 규칙, 마스터 요소 선택 | R-01, R-23, R-26 |
| C-15 | `packages/producer/src/services/render/audioDeliveryLimit.ts:1-110`, `packages/producer/src/services/render/audioPadTrim.ts:51-53`, `:387-540` `limitDeliveryPeaks`, `constrainAacTruePeak`, `enforceAacTruePeak` | true-peak 한도 반복과 전체 컷 | R-19, R-31 |
| C-16 | `packages/engine/src/services/audioMixer.ts:400-516` `boundedDetail`, `probeFailure`, `downloadFailure`, `ffmpegFailure` | 실패 분류(`stage`, `reason`, `owner`, `retryable`) 규칙과 2000자·경로 가리기 | R-27 |
| C-17 | `packages/engine/src/services/audioMixer.types.ts:1-117` | `AudioElement`, `AudioTrack`, `AudioFailureStage/Reason`, `AudioProcessingFailure`, `MixResult` 타입 | R-10, R-27 |
| C-18 | `packages/producer/src/services/renderMediaCollector.ts:45-53`, `:93-128`, `:168-207`, `:269-277` `resolveHostEnd`, `resolveHostWindow`, `isRootComposition`, `toAbsoluteWindow`, `startAtPlayed`, `placeAudio`, `packages/parsers/src/mediaTiming.ts:7-20`, `:54-81` `readMediaStartBasis`, `resolveAbsoluteMediaStartSeconds`, `hostInPointSeconds`, `compositionOriginSeconds`, `cutToHostSlots`, `packages/core/src/speedRamp.ts:16-28`, `:101-109` `shiftRateLane`, `sourceTimeAt` | 호스트 chain을 접어 `{offset, limit, slots}`를 만들고, 트랙의 절대 구간과 `played`를 구하고, in-point만큼 앞을 자른 `mediaStart`·`playbackRate`를 정하는 알고리즘 | R-06, R-35 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출. 원본 테스트 본문은 열지 않았다(`audioMixer.*.test.ts` 파일명과 사례 이름만 보고 동작 범위를 가늠했다). 실행하지 않았고 코드 경로를 따라 기대값을 계산했다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03, R-15 | `<audio id="a" src="x.mp3" data-start="2" data-duration="5" data-volume="0.5" data-fade-in="1">`, 볼륨 곡선·효과 없음, `normalize` 지원 ffmpeg | `AudioElement{start:2, end:7, mediaStart:0, volume:0.5, fadeIn:1, loop:false, layer:0}`. 믹스 필터에 `[0:a]atrim=0:5,volume=0.5,afade=t=in:st=0:d=1,adelay=2000\|2000[a0]` 가 들어간다 |
| T-02 | R-14 | 위와 같고 `data-duration="4"`, `data-fade-in="3"`, `data-fade-out="3"` | 합 6이 길이 4를 넘어 각각 2로 줄어 `afade=t=in:st=0:d=2,afade=t=out:st=2:d=2` |
| T-03 | R-03 | `data-volume="abc"`, `data-volume="0"`, `data-volume="9"` | 각각 `volume=1`(NaN이 `clampAudioGain`에서 1), 무음(`volume=0`), `volume=3.981072`(+12 dB로 제한) |
| T-04 | R-02 | `<video id="v" muted data-has-audio="true">`, `<video id="w" data-has-audio="false">`, `<video id="u" data-has-audio="true">`, `<video id="t">`(속성 없음)를 `parseAudioElements`에 직접 입력 | `u`만 `u-audio`(`type:"video"`) 트랙이다. `v`는 `muted`, `w`는 선언값 때문에 제외된다. `t`는 선택자가 `data-has-audio="true"`를 요구해 트랙이 아니다(렌더 경로에서는 컴파일이 `t`에 `"true"`를 넣어 트랙이 된다) |
| T-05 | R-27, R-30 | 오디오 2개, 하나는 `src`가 가리키는 파일이 없다 | 다른 트랙은 준비되지만 믹스는 하지 않는다. `MixResult{success:false, failures:[{stage:"source", reason:"source_not_found", owner:"user", elementId}]}`, `workDir` 삭제. stage는 `hasAudio:false`, `audioError`를 돌려주고 오케스트레이터가 `audio_processing_failed` 경고 후 `RenderQualityError`를 던진다. `strictness`가 `best-effort`여도 같다 |
| T-06 | R-16 | 평면 트랙 100개 | 96개와 4개 조각으로 합산한 float WAV 둘을 이어 합산한 하나를 입력으로 R-15 그래프를 돌린다. 개수 상한 오류는 없다 |
| T-07 | R-23, R-24 | `<hf-audio-group id="bed" data-volume="0.5">`와 `a`, `b` 멤버(`data-audio-group="bed"`), 체인·automation 없음 | `a`, `b`가 각자 트랙으로 준비된 뒤 단위 이득으로 합쳐져 `group-bed-0.wav`가 되고, 평면 목록에는 `{id:"bed", start:0, end:totalDuration, volume:0.5}` 트랙 하나만 남는다 |
| T-08 | R-01, R-23 | 위 그룹 요소에 `data-hidden`을 추가 | 멤버 `a`, `b`는 자기 `data-hidden`이 없어도 `parseAudioElements`에서 제외된다. 그룹 트랙도 생기지 않는다 |
| T-09 | R-28 | `<audio data-fx-chain="{bad">` | `AudioFxChainError`가 트랙의 `internal/internal` 실패로 잡혀 R-27의 전체 실패가 된다(reject가 아니다). `version:2` 같은 알 수 없는 version도 같다 |
| T-10 | R-28 | 정상 체인인데 headless Chrome이 뜨지 않는다 | `AudioFxRenderError`가 던져져 `processCompositionAudio`가 reject하고, stage가 `hasAudio:false`, 합성 `internal` 실패로 바꾼다. 결과는 R-30과 같이 렌더 실패다. dry 오디오로 대체하지 않는다 |
| T-11 | R-29 | 곡선이 ffmpeg 표현식으로 남은 트랙(예: WAV 형식 문제로 굽기가 `false`인 경우)이 있고 최종 합산 ffmpeg가 그래프 초기화에서 실패 | 곡선 없이 다시 돌려 성공하면 `success:true`, `error`에 "rendered at base volume" 문구가 남지만 producer는 이를 버리므로 렌더는 경고 없이 계속된다. 정상 경로에서는 키프레임이 `simplifyVolumeKeyframes`로 32점 이하가 되고 보통 WAV로 구워져 이 경로에 오지 않는다 |
| T-12 | R-19 | 합산 AAC의 true peak가 -0.4 dBFS | `audio-source.wav`에 ceiling -1 dBTP `truepeak` 효과를 걸어 재인코딩하고 다시 잰다. 남으면 최대 3패스까지 ceiling을 낮추고(최저 -3), 그래도 남으면 전체 컷(`volume=-xdB`)을 건다. 컷이 걸리면 `audioLoweredDb`가 기록된다. 3번 뒤에도 넘으면 렌더 실패(`Audio true-peak check failed`) |
| T-13 | R-22 | 효과 체인에 reverb `size 0.7`, `wet 0.35`, 클립 `data-duration="4"` | `tailSeconds = 0.6 + 0.7×2.6 = 2.42`. 믹스 필터는 `atrim=0:6.42`, 영상이 이 구간보다 짧으면 최종 `atrim`이 영상 끝에서 자른다 |
| T-14 | R-06, R-35 | 루트 아래 `<div data-composition-src="a.html" data-start="10" data-duration="20" data-playback-start="4">` 안에 `<audio id="m" data-start="2" data-duration="10" data-playback-start="1">`(속도·loop 없음, basis 기본 local) | 호스트 start 10, end 30, in-point 4다. 전제로 호스트에 `data-composition-src`가 남아 있다고 본다(렌더 문서의 호스트 조회가 이 속성을 쓴다, `htmlCompiler.ts:1128`. 인라인된 실제 문서로는 미확인). 호스트는 파일 호스트라 루트 예외가 아니므로 limit 30, slot `{10,30}`, offset `10-4=6`이다. 절대 구간은 `{8,18}`이고 `played`는 `{10,18}`, 반환은 `start 8, end 18`이다. `startAtPlayed`에서 `head = 10-8 = 2`이므로 최종 트랙은 `start 10, end 18, mediaStart 1+2×1=3, playbackRate 1`이다. 같은 트랙의 `data-start="25"`이면 절대 시작 31이 limit 30 이상이라 트랙이 빠지고 `droppedMediaIds`에 들어간다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repo@5979991 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `packages/engine/src/services/audioMixer.ts:665-673` `parseAudioElements`(audio 루프), `:606-614`, C-14, `packages/engine/src/services/mediaTimelineWindow.ts:1-17` `isKnownInactiveTimelineWindow` | 코드 확인. 제외 조건에 경고 호출이 없음을 줄을 읽어 확인했다. 선택자 `audio[id]`는 `audioMixer.ts:665`다 |
| R-02 | `audioMixer.ts:675-682`(video 루프), C-11, 선행 스펙 R-08 | 코드 확인. 선택자 `video[id][data-has-audio="true"]`가 속성 없음을 걸러낸다(T-04) |
| R-03 | `audioMixer.ts:619-657` `build`, C-08, C-09, C-12 | 코드 확인. docs `reference/html-schema.mdx:134`는 "믹서는 `data-media-start`만 읽는다"고 쓰지만 `readMediaOffsetSeconds`(`parsers/src/mediaDuration.ts:19-23`)는 `data-playback-start`를 먼저 읽는다. 믹서는 `readMediaStart`(`core/src/runtime/playbackRate.ts:38-40`)를 써서 구현이 사실이다. 같은 줄의 "playback-start만 쓴 video는 화면은 잘리고 소리는 안 잘린다"는 이 SHA의 믹서에는 해당하지 않는다. CLI `validate`는 `data-media-start`와 `data-playback-start`를 둘 다 읽어(`packages/cli/src/commands/validate.ts:245-246`) 문서의 "validate는 media-start만"과도 다르다. `snapshot`은 열지 않았다 |
| R-04 | `audioMixer.ts:595-605` `resolveStart`, `resolveEnd`, `packages/engine/src/services/referenceResolver.ts:1-2`(parsers 재내보내기), 선행 스펙 R-04, R-05 | 코드 확인. `data-start`가 참조이면 Node 정적 해석기(선행 R-04(b))다 |
| R-05 | 검색(SHA 5979991): `grep -rn "\.layer" packages/engine/src packages/producer/src --include=*.ts`(테스트 제외)는 `renderOrchestrator.ts:5313`(`videoLayer.layer`, video 합성 층이고 오디오와 무관)만 낸다. `grep -n "layer" packages/engine/src/services/audio*.ts packages/producer/src/services/render/audio*.ts packages/producer/src/services/render/stages/audioStage.ts`는 `audioMixer.ts:618`(주석), `:626`, `:641`(읽기·대입), `audioMixer.types.ts:17`(필드 선언)뿐이다 | 코드 확인(부재 주장). 범위는 engine·producer `src`다. `studio`, `cli`, `sdk` 등 다른 패키지에서 `AudioElement.layer`를 쓰는지, 동적 접근(`el["layer"]`)은 보지 않았다 |
| R-06 | `packages/producer/src/services/renderMediaCollector.ts:226-277` `collectRenderMedia`, `placeAudio` | 코드 확인. 호출부 검색 `grep -rn "collectHostWindows\|toAbsoluteWindow\|startAtPlayed" packages --include=*.ts`(테스트 제외)는 `renderMediaCollector.ts` 한 파일(정의 `:134`, `:168`, `:191`, 호출 `:227`, `:239`, `:245`, `:251`, `:273`, `:276`)에서만 나온다. 세 함수는 모듈 내부 함수이고 export하지 않는다. 호스트 chain 접기는 `:93-117`, 보조 함수는 `parsers/src/mediaTiming.ts`, `core/src/speedRamp.ts:16-28`, `:101-109`, `core/src/runtime/authoredTiming.ts:27-53`(`resolveAuthoredTimingWindow`)에서 읽었다. 호스트 끝 계산이 런타임과 같은 함수라는 점은 코드 주석(`:42-43`, `:89-91`)과 호출을 보고 확인했고 런타임 쪽 호출부(`sceneWindow` 등)는 이번에 다시 열지 않았다. `resolveReferencedStart`의 참조 해석 본문과 `normalizePlaybackRate`의 0.1~10 자르기(`playbackRateBounds`)는 열지 않았고 상수는 `speedRamp.ts`가 가져오는 `MIN_PLAYBACK_RATE`, `MAX_PLAYBACK_RATE`(`parsers/src/mediaDuration.ts:26-27`)로만 확인했다. 이전 R-06 서술의 "길이 미정은 창 안에서도 0으로 되돌린다"는 한계가 있는 호스트 안에서는 맞지 않아(`:275`는 유한한 `end`를 그대로 쓴다) 고쳤다 |
| R-35 | `renderMediaCollector.ts:190-207` `startAtPlayed`, `:178-187` `played` 계산, C-18 | 코드 확인. `loop` 분기의 한계는 `:197-198` 주석에 있다. 속도 lane 앞자르기(`shiftRateLane`)의 shaped 구간 재표본(16등분)은 읽었으나 수치 사례는 계산하지 않았다. T-14는 손계산이며 실행하지 않았다 |
| R-07 | `packages/producer/src/services/assetMediaType.ts:100-131` `dropMediaOutsideProject`, `:156-228` `preflightCompositionAssetMediaTypes`, `:52-70`(`mediaProfileMatchesElementType`), `packages/producer/src/services/render/stages/compileStage.ts:387-399`(호출) | 코드 확인. `probeStage.ts:863-880`에서도 같은 두 함수를 부른다. 텍스트 문서 거부는 `assetMediaType.ts:134-145`(`notMediaReferences`, video는 `isNotMediaPayload`, img는 `isNotImagePayload`, playlist 이탈은 모든 참조)과 `:222`(`NotMediaPayloadError`), 소리 없는 video 파생 트랙은 `renderMediaCollector.ts:259-263`과 `assetMediaType.ts:165-168`, `:205-212`로 확인했다 |
| R-08 | `packages/producer/src/services/htmlCompiler.ts:2547-2686` `discoverMediaFromBrowser`, `:2689-2853` `discoverAudioVolumeAutomationFromTimeline`, `packages/producer/src/services/render/stages/probeStage.ts:660-835`, `:988-1006` `pruneMutedBrowserMedia` | 코드 확인. 60Hz 상한과 변화점 압축은 `htmlCompiler.ts:2697`, `:2780-2810`에서 읽었다. `adoptRuntimeMediaTiming`은 `probeStage.ts:251-278`(lane 분기 `:262-271`), 호출 `:696-760`. 스크립트 mute video는 `:988-1006`의 `pruneMutedBrowserMedia`가 audio 태그만 지우는 것을 읽어 확인했다 |
| R-09 | `packages/producer/src/services/render/stages/extractVideosStage.ts:643-668`, `:728-755` `appendVideoAudioFromProbe` | 코드 확인. 같은 `src`의 오디오가 이미 있으면 추가하지 않는 `existingAudioSrcs` 조건을 읽었다 |
| R-10 | `packages/producer/src/services/audioMixer.ts:1-11`(engine 재내보내기), `packages/producer/src/services/render/stages/audioStage.ts:103-144`, `:172-290`, `packages/producer/src/services/renderOrchestrator.ts:3748-3772`(호출), `:4937-4940`(결과 소비), `packages/producer/src/services/distributed/plan.ts:1470-1490`(`mixPlanAudio`) | 코드 확인. 같은 이름 파일 점검: `packages/producer/src/services/audioMixer.ts`는 `@hyperframes/engine`의 `parseAudioElements`, `processCompositionAudio`와 타입을 다시 내보내는 11줄 파일이고, `packages/core/src` 바로 아래(`ls`에서 `audioMixer`를 찾은 결과)에는 `audioMixer` 이름 파일이 없다. 믹서 구현은 engine에 한 벌이다. 오케스트레이터는 stage를 await하지 않고 시작해(`pendingAudio = audioStage.catch(...)`) 이후 `audioWait.wait(audioStage)`로 캡처 루프 시작 전에 결과를 받는다. 이 순서의 상세는 행 5 몫이다 |
| R-11 | C-01, C-02, `audioMixer.ts:692-854` `extractAudioSegment`, `:215-217`(동시성) | 코드 확인. `ffmpegSeekSeconds`와 `latestStreamLeadSeconds`의 의미는 열지 않았다. 입력 seek 판단 조건(`inputSeek`)은 줄 781-783에서 읽었다 |
| R-12 | `audioMixer.ts:1475-1766`, 특히 `:1492-1594` | 코드 확인. `resolveProjectRelativeSrc`(`videoFrameExtractor.ts`)의 경로 변환은 열지 않았다 |
| R-13 | `audioMixer.ts:1659-1732`(`gainBeforeFx`는 `:1668`, 키프레임 이득은 `:1669-1677`, `inputGain`은 `:1703`, 트랙 `volume`은 `:1727`), `audioAutomation.ts:189-193`, `audioFxRender.ts:540`(켜진 노드가 없으면 `envelopeBaked:false`), `audioVolumeEnvelope.ts:144`(16bit 자르기), C-03, C-07, C-10, `packages/engine/src/services/audioFxRender.ts:324-341`(`applyEnvelopeToPlanes`, `applyInputGain`), `:527-600` | 코드 확인. docs(`reference/audio-effects.mdx`)의 "On a clip, `data-volume` is applied ahead of its effects"와 일치한다 |
| R-14 | C-04, C-09 | 코드 확인. `afade`의 실제 곡선(선형)은 ffmpeg 기본값이라는 지식에 의존하고 `afade` 문서는 확인하지 않았다. docs `html-schema.mdx:137`이 "Linear"라고 쓴다 |
| R-15 | `audioMixer.ts:926-1089` `mixAudioTracksFlat`, C-04, C-05 | 코드 확인. `amix`의 실제 가중치(`normalize=0` 단위 합)는 코드 주석과 docs(`audio-effects.mdx`의 "Tracks add up")에 근거하고 ffmpeg는 실행하지 않았다 |
| R-16 | `audioMixer.ts:1233-1359` | 코드 확인. 테스트 이름 `audioMixer.manyTracks.test.ts`("200 clips")는 파일명 수준으로만 봤다 |
| R-17 | `audioMixer.ts:1768-1787`, `:1927`(그룹 트랙을 평면 목록 뒤에 push) | 코드 확인 |
| R-18 | `audioMixer.ts:1365-1422` `mixThroughFloatSum`, `packages/engine/src/services/aacEncode.ts:1-137` | 코드 확인. `audioMixer.ts:175-176`(준비 단계 채널), `:999-1000`(합산 `-ar`), `aacEncode.ts:89`, `:108-110`, `:126`(`aresample`, 한 번 인코딩 분기) |
| R-19 | C-15, `packages/producer/src/services/render/stages/audioStage.ts:146-170`, `packages/producer/src/services/render/audioTruePeak.ts:1-60`(측정 방식) | 코드 확인. docs `audio-effects.mdx:150-153`은 "통과한 믹스에 `truepeak` -3 dBTP를 건다"고 쓰지만 구현은 -1 dBTP에서 시작해 최대 3패스에 걸쳐 -3 dBTP까지 낮춘다(`audioDeliveryLimit.ts:12-18`, `:60-72`). 구현이 사실이다. `assembleStage.ts:99-135`의 `padOrTrimAudioToVideoFrameCount`가 이후에도 `sourcePath`로 true-peak 보정을 한다(행 5). 또 docs `:150-153`은 -3 dBTP 뒤 "전체 믹스를 한 번 낮춘다"고 쓰지만 구현의 전체 컷은 최대 3회 재인코딩이다(`audioPadTrim.ts:51-53`, `:480-515`). `audio_lowered` 경고는 `cli/src/utils/audioLoweredWarning.ts:1-12`가 만들고 오케스트레이터는 `assembleStage.ts:61-69`에서 기록만 한다 |
| R-20 | `packages/core/src/audioFx.ts:17-30`, `:871-990`(`HfAudioFxNode`, `parseAudioFxChain`, `enabledAudioFxNodes`), `:148-816`(`HF_AUDIO_FX` 정의의 `id: "..."` 열거), `packages/engine/src/services/audioFxRender.ts:1-13`, `:343-376`, `:527-640`, `packages/core/src/audio/audioFxGraph.ts:1-60` | 코드 확인. `grep -c '^    id: "' packages/core/src/audioFx.ts`가 17이고 id 17개를 `:150-760`에서 확인했다. docs `reference/audio-effects.mdx`는 "Sixteen effects"라 쓰지만 같은 문서의 표(filter 5, dynamics 5, nonlinear 2, time 5)도 17개다. 구현을 사실로 썼다. 파라미터 수치는 열지 않았다 |
| R-21 | `packages/core/src/audioAutomation.ts:18-130`, `:362-393`(`cleanPoint`, `normalizePoints`), `:400-480` | 코드 확인. `parseAudioFxNode`(`audioFx.ts:1018-1046`)가 알 수 없는 type을 throw하고 `params`를 범위로 자르는 것을 읽었다. 시계 설명은 docs `audio-effects.mdx`("Two clocks")와 그룹 처리 코드(`audioMixer.ts:1878-1893`)로 대조했다 |
| R-22 | C-13, `audioMixer.ts:1691-1708` | 코드 확인 |
| R-23 | C-14, `audioMixer.ts:608-614`, `:1770-1787` | 코드 확인. `audioGroups.ts:64-72`의 주석("Audio only in v1, a data-audio-group on a `<video>` is ignored")과 `:8-9`("nothing here routes or sums audio yet")는 구현과 다르다. 구현은 소리 있는 video를 멤버로 받고(`isGroupableMember`), 서브믹스는 engine이 한다. docs `audio-effects.mdx:200-210`이 구현과 같다. 구현이 사실이다 |
| R-24 | `audioMixer.ts:1122-1230` `mixGroupMembersFlat`, `:1846-1959`, C-06 | 코드 확인. 그룹 경로에 `inputGain` 인자가 없음은 `:1899-1909`, 트랙 `volume`은 `:1927-1939`에서 읽었다. 그룹 이득 법칙(`plans/spikes/amix-nesting-spike.sh`로 +2.499 dB 측정)은 코드 주석이 가리키는 스크립트라 열지 않았다 |
| R-25 | `packages/core/src/audioCarve.ts:1-120`, `:236-262`, `:686-767`, `packages/studio/src/components/editor/useFxCarveNodes.ts:18-20`, `:130-132`, `packages/studio/src/components/editor/carveOutput.ts:1-54`, `docs/reference/audio-effects.mdx`("data-fx-carve" 절) | 코드 확인. 부재 주장("렌더에 카브 경로 없음"): `grep -rln "carve" --include=*.ts --include=*.tsx packages`(테스트 제외, SHA 5979991)는 `core`(10), `engine`(1), `lint`(1), `studio`(40) 파일을 낸다. `engine`의 1건은 `videoFrameExtractor.ts:400`의 무관한 주석이고 `producer`에는 없다. `data-fx-carve` 속성 이름은 `core/src/audioCarve.ts`, `lint/src/rules/media.ts`, studio, 그리고 CLI 스크립트 `skills/media-use/audio/scripts/carve.mjs`에서 나온다. `carve.mjs`는 열지 않았다(docs가 말하는 CLI 분석 도구이고 렌더 경로 밖). 놓칠 수 있는 곳: 이름을 합성해 만든 속성 접근, `*.mjs`·`*.js` 소스(위 검색은 `.ts`/`.tsx`만) |
| R-26 | C-14, `audioMixer.ts:574-576`, `:1818-1836` | 코드 확인 |
| R-27 | C-16, `audioMixer.ts:1475-1587`, `:1789-1814`, `packages/producer/src/services/assetMediaType.ts:100-131` | 코드 확인. 사례 이름은 `audioMixer.test.ts`("fails the audio result instead of silently mixing after one track preparation fails"), `audioMixer.undecodableTrack.test.ts`, `audioMixer.urlRead.test.ts`("fails the track when the read is cut mid-span, instead of padding it with silence")로 범위만 가늠했다 |
| R-28 | `audioMixer.ts:1659-1666`, `:1735-1766`, `:1856-1958`, `audioFxRender.ts:527-640`, `packages/core/src/audioFx.ts:952-973`, `audioAutomation.ts:445-480` | 코드 확인. 그룹 체인의 `parseAudioFxChain`이 `mixGroupMembers` 성공 뒤에 호출되므로 서브믹스를 마친 다음 실패한다. 사례 이름: `audioMixer.grouping.test.ts`("reports an unparseable group fx-chain as a failure instead of throwing") |
| R-29 | `audioMixer.ts:1019-1049`, `:1203-1223`, `audioStage.ts:257-265` | 코드 확인. 그룹 경로는 ① 재시도(`:1205`)에 검사가 없고 ②(`:1217`)만 `!signal?.aborted`를 보며 `external_interruption`은 두 곳 모두 보지 않는다. 평면 경로(`:1021-1025`, `:1038-1043`)는 둘 다 `external_interruption`과 abort를 본다. 이 차이의 의도는 확인하지 않았다 |
| R-30 | `packages/producer/src/services/renderOrchestrator.ts:855-900` `applyRenderWarningPolicy`, `:4937-4977`, `packages/producer/src/services/distributed/plan.ts:401-430`, `packages/producer/src/services/render/stages/audioStage.ts:90-101`, `packages/producer/src/services/render/encoderInterruption.ts:1-38` | 코드 확인. 린트 규칙 `audio_attribute_unreadable`은 열지 않았다(docs 인용) |
| R-31 | `packages/producer/src/services/render/stages/audioStage.ts:146-170`, `packages/producer/src/services/render/audioDeliveryLimit.ts:76-110`, `audioPadTrim.ts:462-540` | 코드 확인 |
| R-32 | `audioMixer.ts:1468-1490`, `:826-840`, `:1051-1068` | 코드 확인 |
| R-33 | 검색: `grep -rniE "too (long\|many)\|max.*(tracks\|audio\|clips)\|MAX_AUDIO\|audio.*limit" packages/engine/src/services/audio*.ts packages/producer/src/services/render/audio*.ts packages/producer/src/services/render/stages/audioStage.ts packages/core/src/audio*.ts`(테스트 제외, SHA 5979991). 상한 관련 이름은 `MAX_MIX_INPUTS`(96, 조각 합산), `MAX_AUTOMATION_POINTS`(512, lane당), `MAX_FX_TAIL_SECONDS`(5), `MAX_VOLUME_SEGMENTS`(32), 스트리밍 창 한계뿐이다 | 코드 확인(부재 주장). 위 검색은 렌더 믹스 경로 한정이다. 클라우드 offload의 audio 1.5GB 상한을 `cli/src/cloud/offload.ts:67`, `:79-80`에서 확인했고 범위 밖으로 명시했다. 놓칠 수 있는 곳: `engine/src/config.ts`의 일반 제한값, 서버 쪽 제한 |
| R-34 | `packages/producer/src/services/renderMediaCollector.ts:259-263`, `packages/producer/src/services/assetMediaType.ts:52-70`, `:156-228`, `packages/core/src/compiler/timingCompiler.ts`(선행 스펙 R-08), `docs/reference/html-schema.mdx:144` | 코드 확인. 정적으로 경로를 따라 확정했다(실행은 하지 않았다). `compileTimingAttrs`는 오디오 스트림 유무를 보지 않고 `muted`만 본다(선행 스펙 R-08). 소리 없는 video의 렌더 실패 여부는 이 근거로 확정했다 |
| T-11 | R-29 재시도 경로(`audioMixer.ts:1036-1049`)와 `simplifyVolumeKeyframes`(`:246-290`) | 코드를 읽고 계산했다. 전제를 "표현식으로 남은 트랙"으로 한정한다 |
| T-01~T-13 | 각 R-ID 근거 | 모두 코드를 읽고 손으로 계산했다. 실행하지 않았다. T-01의 필터 문자열은 `buildTrackInputFilter`(C-04)의 `padToDuration=false` 분기를, T-13의 수치는 `reverbRoomSeconds`(`audioFxTail.ts:69-71`)를 따랐다 |

### 2.2 코드 읽는 순서 [선택]

1. `packages/producer/src/services/render/stages/audioStage.ts`(`runAudioStageScoped` → `mixAudioForDelivery`)로 호출 경계와 출력을 먼저 본다.
2. `packages/engine/src/services/audioMixer.ts`를 `parseAudioElements`(582행) → `processCompositionAudio`(1424행, 트랙 준비 루프 1475행, 그룹 1846행, 합산 1961행) → `mixAudioTracksFlat`(926행) → `mixThroughFloatSum`(1365행) 순으로 읽는다. 필터 문자열은 C-01~C-06이다.
3. 효과가 필요해지면 `packages/engine/src/services/audioFxRender.ts`의 `applyAudioFxChain`(527행)과 `packages/core/src/audio/audioFxGraph.ts`, `packages/core/src/audioFx.ts`의 레지스트리를 본다.
4. 실패 분류는 `audioMixer.ts:400-516`, 렌더 정책은 `packages/producer/src/services/renderOrchestrator.ts:855-900`과 `:4937-4977`이다.

### 2.3 비교·재사용 출처 [선택]

없음. 같은 기능을 다른 레포에서 스펙으로 만들지 않았다.

### 2.4 검토 기록 [필수, ready 스펙]

- 방식: 독립 검토 2회와 메인 점검. 2026-11-17.
  - 1차 독립 검토(읽기 전용 서브에이전트): R-01~R-34와 T-01~T-13 전체를 원본 코드와 대조했다. 불일치(R-13 `data-volume` 적용 순서, R-19 `audio_lowered` 경고 소유자, R-24, R-29 재시도 검사 차이, R-07, R-18, R-08, R-17, R-01, R-33, T-11 등)와 누락은 작성자가 16건을 반영했다.
  - 2차 독립 검토(별도 서브에이전트, 1차 이후 바뀐 부분 중심): R-06, R-35, C-18, T-14(호스트 창 계산 손계산)와 R-01, R-03, R-07, R-08, R-10, R-13, R-17~R-19, R-24, R-29, R-31, R-33, R-34를 대조했다. 표본으로 R-02, R-04, R-05, R-22, R-26, R-30도 확인했다. 선행·후행 링크의 R-ID 번호와 의미도 맞췄다. 불일치한 R-ID와 T-ID는 없었고, R-06 루트 호스트 예외·in-point 호스트의 slot·R-07 ③ `<img>` 거부 규칙·R-08 lane 분기·T-14 전제 등 보강은 작성자가 반영했다.
  - 메인 점검: 표 칸 수와 R-ID 집합 일치를 스크립트로 확인했고, R-05(`audioMixer.ts:626`), R-06(`renderMediaCollector.ts:93-208`, `isRootComposition`), R-30(`renderOrchestrator.ts:855-904`), true-peak 다중 패스(`audioDeliveryLimit.ts`)와 `check.py`를 확인했다.
- 대조한 R-ID: 1차에서 R-01~R-34 전체, 2차에서 R-01, R-03, R-06~R-08, R-10, R-13, R-17~R-19, R-24, R-29, R-31, R-33~R-35. 결과는 일치 또는 불일치 후 수정이다.
- 대조하지 않았거나 판단 불가로 남은 R-ID: R-09, R-11, R-12, R-20, R-21, R-27, R-28, R-32는 1차에서 호출 경로와 `bail()`까지만 확인했고 `downloadFailure`·`probeFailure`·`ffmpegFailure` 분류 세부와 `parseAudioFxChain`·`parseAutomation` 검사 본문은 별도 검토자가 재대조하지 않았다. 효과 파라미터 수치와 worklet DSP 내부는 개념 수준이다. `normalizePlaybackRate`의 0.1~10 자르기 본문은 상수와 주석까지만 읽었다.
- 재구현: 미수행.

## 적용 메모 [선택]

없음. 이 스펙은 원본 동작만 쓴다.
