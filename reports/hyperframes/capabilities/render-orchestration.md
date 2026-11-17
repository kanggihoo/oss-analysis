---
sha: "5979991d5f0af542fbb02ba906bdba4de52b2b64"
created: 2026-11-17
updated: 2026-11-17
sources:
  - packages/producer/src/services/renderOrchestrator.ts
  - packages/producer/src/services/render/shared.ts
  - packages/producer/src/services/render/capturePlan.ts
  - packages/producer/src/services/render/captureCost.ts
  - packages/producer/src/services/render/segmentPlan.ts
  - packages/producer/src/services/render/segmentQueue.ts
  - packages/producer/src/services/render/segmentRecycle.ts
  - packages/producer/src/services/render/artifactTransaction.ts
  - packages/producer/src/services/render/renderDirOwner.ts
  - packages/producer/src/services/render/renderExecutionContext.ts
  - packages/producer/src/services/render/renderEventPublisher.ts
  - packages/producer/src/services/render/renderEtaGuard.ts
  - packages/producer/src/services/render/stallClock.ts
  - packages/producer/src/services/render/observability.ts
  - packages/producer/src/services/render/cleanup.ts
  - packages/producer/src/services/render/planValidation.ts
  - packages/producer/src/services/render/renderFormat.ts
  - packages/producer/src/services/render/hlsConfig.ts
  - packages/producer/src/services/render/deliveryEncoder.ts
  - packages/producer/src/services/render/chromaSubsampling.ts
  - packages/producer/src/services/render/pageNeverReady.ts
  - packages/producer/src/services/render/videoFrameCoverage.ts
  - packages/producer/src/services/render/stages/compileStage.ts
  - packages/producer/src/services/render/stages/probeStage.ts
  - packages/producer/src/services/render/stages/extractVideosStage.ts
  - packages/producer/src/services/render/stages/audioStage.ts
  - packages/producer/src/services/render/stages/captureStage.ts
  - packages/producer/src/services/render/stages/captureStreamingStage.ts
  - packages/producer/src/services/render/stages/captureSegmentedStage.ts
  - packages/producer/src/services/render/stages/captureHdrStage.ts
  - packages/producer/src/services/render/stages/encodeStage.ts
  - packages/producer/src/services/render/stages/assembleStage.ts
  - packages/producer/src/services/parallelCoordinator.ts
  - packages/producer/src/services/safeRenderErrorCode.ts
  - packages/producer/src/services/htmlCompiler.ts
  - packages/producer/src/services/fileServer.ts
  - packages/producer/src/renderRequest.ts
  - packages/producer/src/config.ts
  - packages/producer/src/server.ts
  - packages/producer/src/index.ts
  - packages/engine/src/services/parallelCoordinator.ts
  - packages/engine/src/config.ts
  - packages/core/src/fps.ts
  - packages/cli/src/commands/render.ts
  - packages/cli/src/commands/render/execute.ts
  - packages/cli/src/utils/renderCancellation.ts
  - docs/packages/producer.mdx
depends:
  - ./composition-contract.md
  - ./capture-encode-engine.md
  - ./audio-mix-fx.md
status: draft
---

# 로컬 렌더 파이프라인 (렌더 오케스트레이션)

> 렌더 요청(`RenderConfigInput`)을 받아 `createRenderJob`으로 `RenderJob`을 만들고, `executeRenderJob`이 컴파일, probe, 비디오 프레임 추출, 캡처(streaming, segmented, disk, HDR 중 하나), 오디오, 인코딩, 조립을 순서대로 돌려 `outputPath`에 산출물을 커밋하는 producer 오케스트레이터다. 워커 병렬, 재시도, 취소, 진행 이벤트, 경고 정책, 산출물 트랜잭션을 관리한다.

용어: 컴포지션은 영상 한 편 또는 한 장면을 설명하는 HTML 파일이고 바깥 요소에 `data-composition-id`가 있다. 이 문서의 "호출자"는 `createRenderJob`과 `executeRenderJob`을 부르는 쪽(CLI `render.ts`, producer `server.ts`, 외부 프로그램)이다. 컴파일 규칙은 [composition-contract.md](./composition-contract.md), 엔진 캡처·인코딩 API와 실패 계약은 [capture-encode-engine.md](./capture-encode-engine.md), 오디오 믹스는 [audio-mix-fx.md](./audio-mix-fx.md)가 소유하고 이 문서는 링크만 건다. 페이지 안쪽 seek 계약은 참고용으로 [runtime-seek.md](./runtime-seek.md)에 있다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 입력은 "30fps, `quality: "standard"`, `format: "mp4"`, 컴포지션 하나, 오디오 트랙과 비디오 요소 하나씩, 호출자가 abort 신호를 넘김"이다. 단계 순서는 R-05가 기준이다.

1. 호출자가 `createRenderJob(config)`로 `RenderJob`(status `queued`, progress 0)을 만든다. 이때는 아무것도 검증하지 않는다(R-01).
2. `executeRenderJob(job, projectDir, outputPath, onProgress?, signal?, assertRenderActive?)`가 형식 조합을 검증하고(R-03), work 디렉터리와 정리 순서를 정한 뒤(R-04) 파이프라인을 시작한다.
3. 컴파일 단계가 `compileForRender`를 불러 HTML을 만들고 `workDir/compiled`에 쓴다. probe 단계가 필요하면 Chrome을 띄워 길이와 미디어를 확정하고 `totalFrames`를 정한다(R-06~R-10).
4. 비디오 프레임 추출 단계가 FFmpeg로 프레임 이미지를 뽑는다. 이어서 오디오 단계가 시작되고, 오디오는 캡처 준비(GPU 확인, 캘리브레이션, 워커 수 결정, 캡처 경로 선택)와 동시에 돈다. 프레임 캡처를 시작하기 전에 오디오 결과를 기다린다(R-11~R-19).
5. 캡처 단계가 계획(`CapturePlan`)에 따라 streaming, segmented, disk, hdr_layered 중 하나로 프레임을 만들고, streaming과 segmented는 캡처와 동시에 인코딩한다. disk 경로만 캡처 뒤에 인코딩 단계를 따로 돈다(R-15~R-28).
6. 조립 단계가 오디오 길이를 영상 프레임 수에 맞춘 뒤 mux 또는 faststart 또는 HLS 패키징을 한다. 산출물은 sibling 스테이징 경로에 쓴다(R-29).
7. `ArtifactTransaction`이 스테이징 산출물을 검증하고(길이, 프레임 수, 크기) `outputPath`로 rename해 커밋한다. 상태는 `complete`가 되고 `outcome`은 `completed` 또는 `completed_with_warnings`다(R-30, R-31). 어느 단계에서든 예외나 취소가 나면 스테이징을 롤백하고 work 디렉터리를 지우고 오류를 호출자에게 던진다(R-32, R-37).

병렬인 구간은 두 곳이다. 오디오 단계와 캡처 준비가 겹치고, 캡처 단계 안에서 워커 여러 개가 프레임을 나눠 잡는다(R-13, R-20).

### 1.2 범위·통합 지점 [필수]

- 제공: (a) 렌더 요청과 `RenderJob`의 필드, 기본값, 거부 조건, (b) 단계 순서와 단계 사이로 넘기는 데이터, (c) 캡처 경로 선택 규칙(`forceScreenshot` 트리거 표 포함), (d) 워커 수 결정과 프레임 분배, 재시도와 복구 사다리, (e) 취소, 시간 예산(`maxRenderMs`), 정체(stall) 감지, (f) 진행 보고, (g) 경고 정책과 오류 타입 지도, (h) 산출물 형식별 분기와 트랜잭션, (i) CLI와 HTTP 서버가 오케스트레이터를 부르는 경계.
- 제외(이유):
  - 컴파일 규칙은 composition-contract, 엔진 캡처·인코딩 API와 실패 분류(`classifyCaptureFailure`)는 capture-encode-engine, 오디오 믹스와 true-peak 한도는 audio-mix-fx 소유라서 이 문서는 호출 위치와 결과 처리만 쓴다.
  - 분산 렌더(`packages/producer/src/services/distributed/*`, Lambda, Cloud Run)는 행 17이다. `renderRequest.ts`의 `distributedConfigFromRequest`와 CLI `--range`의 `renderSpan`이 같은 요청 계약을 쓴다는 사실만 R-44에 한 줄 쓴다. HeyGen 호스팅은 행 18이다.
  - HDR 캡처(`captureHdr*.ts`, `hdrMode.ts`), 셰이더 전환 레이어 합성, GIF 팔레트 인코딩(`gifEncodeArgs.ts`), drawElement worker-encode와 PSNR self-verify 내부, 모션 블러, static dedup은 개념 한 단락과 파일 위치만 쓴다(R-12, 1.2 끝).
  - CLI 명령 입구(옵션 파싱, lint, Docker, 배치, 텔레메트리)는 행 8이다. 이 문서는 오케스트레이터를 부르는 지점과 결과 처리만 쓴다(R-41).
- 외부 의존·선행 계약: 선행 스펙은 위 세 개다. 호출자가 제공해야 하는 것은 `projectDir`(컴포지션 프로젝트), `outputPath`(파일 또는 디렉터리), 선택적으로 `onProgress`, `AbortSignal`, `assertRenderActive`(commit 직전에 호출되는 생존 확인 콜백)다. 외부 프로그램은 Chrome(chrome-headless-shell), FFmpeg, ffprobe다.
- 소유 상태·부작용: `RenderJob` 객체(호출자와 공유하는 가변 객체), work 디렉터리(`captured-frames/`, `compiled/`, `video-only.*`, `audio-work/`, 세그먼트 디렉터리 등), `ArtifactTransaction`의 sibling 스테이징 디렉터리, file server, probe 세션과 캡처 세션, Chrome과 FFmpeg 자식 프로세스, 메모리 sampler, ETA guard 타이머. 최종 산출물은 `outputPath` 하나(HLS와 png-sequence는 디렉터리)다.
- 분리 제안: 이 행은 R-ID가 40개를 넘는다. 실패 복구(R-21~R-26)와 캡처 경로 선택(R-14~R-19)이 한 덩어리로 읽히므로 나중에 "캡처 경로 선택과 복구"를 따로 떼어도 서로 의존이 약하다. 이번 스펙은 핵심 경로를 모두 담았다.

### 1.3 인터페이스와 데이터 의미 [필수]

#### 1.3.1 공개 API (`@hyperframes/producer`의 `index.ts`가 내보내는 것)

| 연산·데이터 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `createRenderJob(config: RenderConfigInput)` | → `RenderJob` | 동기 함수. 검증하지 않는다. `fps`를 `Fps`로 바꾸고 `strictness` 기본값을 채워 `queued` 상태 객체를 만든다(R-01) |
| `executeRenderJob(job, projectDir, outputPath, progressSink?, abortSignal?, assertRenderActive?)` | → `Promise<void>` | 끝나면 `outputPath`에 산출물이 있다. 결과는 반환값이 아니고 `job`의 필드(`outputPath`, `outcome`, `warnings`, `perfSummary`, `duration`, `audioLoweredDb` 등)에 쓴다. 실패는 throw(R-37). `progressSink`는 `(job, message) => void 또는 Promise`다. `assertRenderActive`는 commit 직전에 부르는 `() => void`이고 던지면 렌더가 취소로 끝난다 |
| `applyRenderWarningPolicy(job, captureWarnings, log?)` | → void | 경고를 `job.warnings`에 합치고 정책에 걸리면 `RenderQualityError`를 던진다(R-38) |
| `RenderQualityError` | `Error` 하위, `warnings: RenderWarning[]` | 메시지는 `Render blocked by N correctness warning(s):` 뒤에 `- <code>: <redacted message>` 줄들이다 |
| `RenderCancelledError` | `Error` 하위, `reason: "user_cancelled" 또는 "timeout" 또는 "aborted"` | 기본 메시지 `render_cancelled`, 기본 reason `aborted`(R-32) |
| `RenderTooSlowError` | `Error` 하위, `code: "RENDER_TOO_SLOW"`, `owner: "user"`, `retryable: false`, `publicMetadata` | `index.ts`에서 내보내지 않는다. 서버가 `errorCode`로 전한다(R-33, R-43) |
| `resolveRenderDebugDir()` | → 경로 | debug work 디렉터리의 부모(`.debug`) |
| `createRenderRequest`, `parseRenderRequest`, `renderConfigFromRequest` | 요청 JSON ↔ `RenderConfig` | JSON 안전한 요청 계약. 검증은 이쪽에만 있다(R-02) |

타입은 `RenderStatus`(`queued`, `preprocessing`, `rendering`, `encoding`, `assembling`, `complete`, `failed`, `cancelled`), `RenderOutcome`(`completed`, `completed_with_warnings`, `failed`, `cancelled`), `RenderStrictness`(`strict`, `best-effort`)이고 C-01이 원본이다.

#### 1.3.2 `RenderConfigInput` 필드와 기본값이 채워지는 곳

`RenderConfigInput`은 `RenderConfig`에서 `fps`만 `number 또는 {num, den}`으로 넓힌 타입이다. 필수는 `fps`와 `quality`뿐이다. 기본값을 `createRenderJob`이 채우는 것은 `fps`(정규화)와 `strictness`뿐이고 나머지는 사용하는 단계가 읽을 때 채운다.

| 필드 | 기본값과 채우는 곳 | 의미·거부 |
|---|---|---|
| `fps` | `createRenderJob`이 `toFps`로 정규화 | 숫자 n은 `{num:n, den:1}`. 객체는 값 검사 없이 통과. 양의 정수 유리수 검증은 요청 경로(R-02)에만 있다 |
| `quality` | 기본값 없음(서버 입력은 `high`로 보정) | `draft`, `standard`, `high`. 인코더 preset과 CRF를 정한다 |
| `format` | 파이프라인이 `mp4`로 채움(`renderOrchestrator.ts:3178`) | `mp4`, `webm`, `mov`, `gif`, `png-sequence`, `hls`. 알파가 필요한 형식은 `webm`, `mov`, `png-sequence`, `gif`(C-14의 `outputNeedsAlpha`). `mp4`와 `hls`는 같은 불투명 H.264 파이프라인 |
| `strictness` | `createRenderJob`이 `best-effort` | `strict`면 어떤 경고든 렌더를 막는다(R-38) |
| `entryFile` | 파이프라인이 `index.html`로 채움 | `projectDir` 기준 상대 경로. 없으면 `Entry file not found`(R-07) |
| `workers` | 없으면 자동 | 있으면 1에서 24로 clamp(R-18) |
| `maxRenderMs` | 없음 또는 0이면 ETA guard 꺼짐 | R-33 |
| `producerConfig` | 없으면 실행 시 `resolveConfig()`(환경변수 읽음) | 있으면 환경변수를 읽지 않는다. 엔진 `EngineConfig` 전체 |
| `debug` | false | true면 work 디렉터리를 `.debug/<job.id>`에 두고 지우지 않으며 `render.log`와 `perf-summary.json`을 쓴다(R-04, R-40) |
| `crf` 또는 `videoBitrate` | 없음 | 둘 다 있으면 `crf`를 쓰고 warn(`renderOrchestrator.ts:4927-4935`) |
| `hdrMode` | 파이프라인이 `auto` | `force-sdr`는 HDR 검사를 건너뜀. `force-hdr`는 hls, chroma 444에서 거부(R-03) |
| `hlsSegmentSeconds` | 4(`DEFAULT_HLS_SEGMENT_SECONDS`) | hls에서만 읽음. 양의 정수가 아니면 거부 |
| `gifLoop` | 0(무한 반복) | gif에서만 읽음. 0에서 65535 정수가 아니면 encode 단계에서 던짐 |
| `keyframeIntervalSeconds`, `maxBitrate`, `bufferSize` | 없음 | mp4에서만 허용(R-03) |
| `proresProfile` | 없음(mov에서 4444) | mov에서만 허용 |
| `chromaSubsampling` | `420` | `444`는 mp4, SDR, 소프트웨어 인코더에서만 허용(R-03, R-12) |
| `videoFrameFormat` | `auto` | 소스 비디오 프레임 추출 형식(R-11) |
| `outputResolution`, `outputResolutionAspectAgnostic` | 없음 | `deviceScaleFactor`로 바뀐다. 정수 배율만 허용(R-07) |
| `variables`, `strictVariables` | 없음 | `window.__hfVariables`로 주입. `strictVariables`면 probe가 브라우저에서 검사(R-08) |
| `motionBlur`, `pageMotionBlur` | 없음 | `motionBlur`가 있으면 PNG 캡처를 강제하고 지원 경로가 제한된다. `RenderRequestOptions`에 `motionBlur`가 없어 요청 경로로는 못 넣는다(R-02) |
| `useGpu` | false | 인코더 GPU. hls, chroma 444와 충돌하면 거부 |
| `resumeSegments`, `keepSegments` | false | segmented 캡처 전용(R-17) |
| `allowOutsideProjectAssets`, `logger` | 요청 경로에서는 `allowOutsideProjectAssets === true`일 때만 true | 컴파일, 추출, file server가 읽음 |

#### 1.3.3 `RenderJob` 필드

| 필드 | 값과 쓰는 시점 | 의미 |
|---|---|---|
| `id` | `createRenderJob`이 `randomUUID()` | work 디렉터리 이름과 로그 상관 키 |
| `config` | 입력 복사본(`fps`, `strictness` 정규화) | 이후 읽기 전용으로 쓴다 |
| `status`, `currentStage`, `progress`, `stageProgress` | `updateJobStatus`가 갱신(R-36) | `progress`는 0에서 100 정수이고 줄어들지 않는다. `stageProgress`는 `{code, done?, total?}`이고 `code`는 `compile`, `extract_video`, `process_audio`, `start_browsers`, `capture`, `encode`, `assemble` |
| `createdAt`, `startedAt`, `completedAt` | 생성, 파이프라인 시작, 터미널 상태 | `completedAt`은 `failed`, `complete`, `cancelled`로 바뀔 때만 |
| `outcome` | 터미널 상태에서만 | `failed`, `cancelled`, 그 외 `warnings`가 비면 `completed`, 있으면 `completed_with_warnings` |
| `warnings` | 경고 정책이 채움(R-38) | `{code, message, details, stage: "capture-readiness"}` 목록 |
| `duration`, `totalFrames`, `framesRendered` | probe 결과, 캡처 진행(재시도마다 0으로 리셋) | 초 단위 길이와 프레임 수 |
| `outputPath` | commit 성공 뒤에만 | 실패와 취소에서는 비어 있다 |
| `error`, `failedStage`, `errorDetails` | 실패 시 한 번에 채움(R-37) | `errorDetails`는 `message`, `stack`, `elapsedMs`, `freeMemoryMB`, `browserConsoleTail`(끝 30줄), `perfStages`, `observability` 등 |
| `perfSummary`, `audioLoweredDb` | 성공 시 / true-peak 한도로 믹스가 낮아졌을 때 | R-40, R-13 |
| `strictVariablesChecked` | probe가 | 변수 검사를 했는지 |
| `reference_background` | `createRenderJob`이 `{kind: "unknown"}`으로 만들고, probe 세션이 읽은 값(`createReferenceBackgroundRecorder`)으로 덮음 | 컴포지션 루트와 페이지 배경의 초기 상태. `kind`는 `solid`(+`rgb`), `none`, `unsupported_non_solid`, `unknown` |

#### 1.3.4 단계별 입력, 출력, 넘기는 데이터

| 단계 | 입력 | 출력(다음 단계로 넘기는 것) |
|---|---|---|
| compile | `projectDir`, `entryFile`, `variables`, `cfg` | `compiled`(HTML, subCompositions, externalAssets, videos, audios, images, renderModeHints), `composition`(길이, 크기, 미디어 목록), `deviceScaleFactor`, `outputWidth/Height`, `forceScreenshot`, `deCompileGate`. `workDir/compiled/index.html`과 하위 파일을 디스크에 씀 |
| probe | 위 결과 | 갱신된 `compiled`와 `composition`(브라우저가 찾은 길이, 미디어), `fileServer`, `probeSession`(재사용 가능한 초기화된 Chrome 세션 또는 null), `duration`, `totalFrames`, `beginFrameStalled`, `strictVariablesChecked`. 브라우저가 필요 없으면 `fileServer`와 `probeSession`은 null |
| extract videos | `composition.videos`, `compiledDir` | `extractionResult`, `frameLookup`(시각 t에 붙일 프레임 표), `videoMetadataHints`, `videoReadinessSkipIds`, HDR 소스 정보, `failureToEnforce`. 프레임은 `compiled/__hyperframes_video_frames/<id>`로 symlink(실패하면 junction, 복사) |
| audio | `composition.audios`, `totalFrames`, `fps` | `audioOutputPath`, `deliverySourcePath`(PCM), `hasAudio`, `audioError`, `audioFailures`, `audioLoweredDb` |
| capture | `CapturePlan`, 인코더 옵션(`preset`, `effectiveQuality`), `fileServer`, `probeSession`, `frameLookup` | streaming과 segmented는 `video-only.<ext>`를 바로 완성, disk는 `workDir/captured-frames/frame_NNNNNN.{jpg,png}`, hdr_layered는 자기 경로. `workerCount`, `probeSession`, 브라우저 콘솔 tail |
| encode(disk 경로만) | `captured-frames`, `preset` | `video-only.<ext>`(png-sequence는 `outputPath`에 PNG를 복사하고 `audio.m4a` 사이드카, gif는 두 패스 팔레트 인코딩으로 스테이징 경로에 바로 씀) |
| assemble | `video-only`, 오디오, `format` | 스테이징 경로의 최종 파일 또는 HLS 디렉터리 |
| commit | 스테이징 경로 | `outputPath` |

progress 구간은 compile 5, extract 10에서 20, audio 20, start_browsers 25, capture 25에서 80(disk는 25에서 70), disk encode 75에서 90, assemble 90에서 99, complete 100이다(R-36).

#### 1.3.5 `forceScreenshot` 트리거 표

엔진 기본값은 software GPU라 `forceScreenshot`이 true로 올라가 BeginFrame을 안 쓴다(capture-encode-engine R-04). 아래는 producer 쪽에서 값을 true로 올리는 곳이다. 오케스트레이터는 컴파일 단계가 정한 값을 지역 변수 `captureForceScreenshot`으로 들고 다니고, 이후 변경은 이 지역 변수와 `CapturePlan`에서만 일어난다. `cfg`는 컴파일 단계가 한 번 쓴 뒤 고정이다(`cfg.forceScreenshot = ...` 쓰기는 `compileStage.ts:364` 한 곳과 videoLayer 경로 `renderOrchestrator.ts:3597`).

| 트리거 | 조건 | 결과 | 위치 |
|---|---|---|---|
| 알파 출력 | `format`이 `webm`, `mov`, `png-sequence`, `gif`이고 `cfg.useDrawElement`가 꺼져 있음 | true. drawElement가 켜져 있으면 알파만으로는 올리지 않음 | `compileStage.ts:361`, `renderFormat.ts:3-5` |
| 렌더 모드 hint | 컴파일된 `renderModeHints.recommendScreenshot`(이유 코드 `htmlInCanvas`, `captureMotionBlur`, `iframe`, `requestAnimationFrame`) 중 하나라도 있고 이미 true가 아님 | true, 이유 코드를 담은 warn 로그 | `shared.ts:237-250`, C-15 |
| low memory 모드 | `cfg.lowMemoryMode`(총 RAM이 임계값 이하이면 자동, `PRODUCER_LOW_MEMORY_MODE=false`로 해제) | true, 캘리브레이션 생략, `workers` 없으면 1로 고정. 분산 `plan()`에도 같은 규칙(`distributed/plan.ts:1360-1366`) | `renderOrchestrator.ts:3429-3439`, `captureCost.ts:171-176` |
| BeginFrame liveness 실패 | probe 세션이 BeginFrame으로 떴고 출력 없는 `beginFrame` 한 번이 30초(`PRODUCER_BEGINFRAME_PROBE_TIMEOUT_MS`) 안에 안 끝남 | probe 브라우저를 screenshot으로 다시 띄우고 `beginFrameStalled`로 전체 렌더를 screenshot으로 | `probeStage.ts:566-611`, `renderOrchestrator.ts:3547-3550` |
| 캘리브레이션 오류 | BeginFrame 캘리브레이션이 `HeadlessExperimental.beginFrame timed out`, `Runtime.callFunctionOn timed out`, `Runtime.evaluate timed out` 등에 걸림 | 캘리브레이션을 screenshot으로 재시도하고 true | `captureCost.ts:452-466`, `534-539` |
| 구체 GPU 모드 clamp | `browserGpuMode: "auto"`가 software로 판명 | `applyConcreteGpuScreenshotClamp`로 true(명시적 해제가 없을 때) | `renderOrchestrator.ts:3835-3843` |
| 페이지 쪽 합성 | 셰이더 전환 컴포지션에서 page-side compositing 사용 | plan의 `forceScreenshot`이 true | `capturePlan.ts:183`, `renderOrchestrator.ts:4690-4749` |
| HDR layered | `hdr_layered` plan | 항상 true | `capturePlan.ts:192-197`, `captureHdrStage.ts:199` |
| video layer passthrough | 한 개의 전체 캔버스 비디오를 ffmpeg가 합성하는 opt-in 경로가 채택됨 | `cfg.useDrawElement=false`, `cfg.forceScreenshot=true` | `renderOrchestrator.ts:3593-3603` |
| 전체 재렌더 | streaming 경로 실패가 R-24 조건에 해당(엔진 설정이 streaming을 끈 렌더는 처음부터 disk plan이라 대상이 아니다, R-16) | 새 plan의 `forceScreenshot`이 true. segmented는 drawElement 계열 실패나 capture 실패일 때, disk는 drawElement 실패일 때 | `capturePlan.ts:235`, `255`, `303`, `renderOrchestrator.ts:5342-5433` |
| 호출자 입력 | HTTP 본문의 `forceScreenshot`, `PRODUCER_FORCE_SCREENSHOT=true`, CLI `--resolution`(자동 override를 건너뜀) | 엔진 설정이 true 유지 | `server.ts:345`, `render.ts:1172-1183` |

로컬 Linux CLI는 `browserGpuMode: "auto"`일 때 `forceScreenshot: false`와 `beginFrameFirstFrameDeadlineMs: 20000`을 override해서 BeginFrame을 쓴다(R-41). programmatic 호출은 이 override가 없어서 기본이 screenshot이다.

#### 1.3.6 단계별 실패 지도

처리 열은 "복구"(재시도나 대체 경로로 계속), "중단"(렌더 실패), "경고"(`job.warnings`에 남고 계속)로 쓴다.

| 단계·상황 | 처리 | 호출자가 받는 것 | R-ID |
|---|---|---|---|
| 실행 전 형식 조합 오류(hls와 `force-hdr`, hls와 `useGpu`, 444와 mp4 외 형식 등) | 중단. work 디렉터리도 만들지 않음 | 일반 `Error`. `job`은 `queued`로 남고 `error`도 비어 있음 | R-03 |
| 진입 파일 없음, 프로젝트 밖 경로, 해상도 배율 오류 | 중단 | 일반 `Error`, `job.status="failed"` | R-07 |
| probe 세션 초기화 실패 | transient 오류면 1회 재시도(총 2번 시도), 아니면 중단 | 원 오류 | R-08 |
| BeginFrame liveness 실패 | 복구(screenshot으로 전환) | 없음, 경고 로그만 | R-08 |
| 길이 0 | 중단 | `Error("Composition duration is 0, so this would produce a black video.")` | R-09 |
| 길이나 프레임 수가 범위 밖(최대 24시간) | 중단 | `PlanValidationError`(`code: "DISTRIBUTED_DURATION_OUT_OF_RANGE"`) | R-09 |
| 비디오 소스 추출 실패 | 기본 `enforce`면 중단(체크포인트 기록 뒤), `observe`는 로그만, `off`는 무시. 호스트 장애(encoder 중단, 디스크 가득)는 모드와 무관하게 중단 | `VideoExtractionStageError`(`VIDEO_EXTRACTION_FAILED` 또는 `VIDEO_SOURCE_UNRENDERABLE`), `EncoderInterruptedError`, `ENOSPC` 오류 | R-11 |
| 비디오 프레임 coverage 0.95 미만 | 중단(인코딩 전) | `VideoFrameCoverageError` | R-11 |
| 오디오 믹스 실패 | 중단(캡처 시작 전). `strictness`와 무관 | `RenderQualityError`(`audio_processing_failed`) | R-13, R-38 |
| 오디오 전달 한도(true-peak) 단계 실패, 오디오 FFmpeg 외부 중단 | 중단(캡처 시작 전). 경고 경로를 거치지 않음 | 일반 `Error`(`Audio true-peak limit failed`, `Audio true-peak check failed`) 또는 `EncoderInterruptedError` | R-13 |
| 워커가 일부 프레임을 못 만듦(disk) | 복구(워커 절반으로 재시도) | 없음, warn 로그. 못 고치면 `Capture completed but N frame(s) are missing` | R-21 |
| transient 브라우저 종료(`Target closed`, `Page crashed`) | 복구, 같은 워커 수로 1회 | 없음. 두 번째는 중단 | R-21, R-22 |
| stall(진행 없음) | disk: 워커 절반으로 재시도. streaming: 최대 3회 이어받기 뒤 전체 screenshot 재렌더. 한도 초과는 중단 | `RenderStageStalledError`(`RENDER_STAGE_STALLED`), `ParallelCaptureStallError`, `SequentialCaptureStallError` | R-23, R-24, R-34 |
| drawElement self-verify 또는 capture 오류 | 복구(프레임이나 세그먼트를 지우고 screenshot으로 전체 재렌더) | 없음 | R-25 |
| 메모리 부족(OOM) | 복구 시도는 1 워커 streaming 경로로. 그래도 실패하면 중단 | 안내 문구가 붙은 오류 | R-24 |
| streaming encoder 시작 실패 | 복구(disk 경로로) | 없음 | R-23 |
| streaming encoder가 프레임 2 이후 사망 | 복구(전체 screenshot 재렌더 1회) | 없음 | R-24 |
| `external_interruption`(호스트 수명주기가 FFmpeg를 끊음) | 중단. 재시도하지 않음 | `EncoderInterruptedError`(`ENCODER_INTERRUPTED`) | R-24 |
| 경고 `sub_timeline_script_failure`, `vfx_failure`, `audio_processing_failed` | 중단. `strictness`와 무관 | `RenderQualityError` | R-38, R-39 |
| 그 밖의 캡처 경고(`media_readiness_timeout` 등) | `best-effort`는 경고로 남고 계속, `strict`는 중단 | 경고는 `job.warnings`, 중단이면 `RenderQualityError` | R-38 |
| `maxRenderMs`의 두 배를 넘길 ETA | 중단 | `RenderTooSlowError`(`RENDER_TOO_SLOW`) | R-33 |
| 캘리브레이션과 캡처가 모두 `Runtime.evaluate` 시간 초과, 프레임 0개 | 중단 | `PageNeverReadyError`(`PAGE_NEVER_READY`) | R-35 |
| 취소 | 정리 후 `cancelled` | `RenderCancelledError` | R-32 |
| 산출물 검증 실패(잘림, 크기 불일치, 빈 파일) | 중단. 기존 `outputPath`는 그대로 | 일반 `Error`(`Render artifact ...`) | R-30 |

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `createRenderJob(config)` 호출 | 검증 없이 `RenderJob`을 돌려준다. `id`는 `randomUUID()`, `config`는 입력의 얕은 복사에 `fps: toFps(config.fps)`(숫자 n이면 `{num:n, den:1}`, 객체는 값 검사 없이 그대로)와 `strictness: config.strictness ?? "best-effort"`를 덮은 것이다. `status: "queued"`, `progress: 0`, `currentStage: "Queued"`, `createdAt: new Date()`, `warnings: []`, `reference_background: {kind: "unknown"}`(`referenceBackgroundResult(undefined)`)다. 다른 기본값(`format`, `entryFile`, `workers`, `producerConfig`)은 여기서 채우지 않고 실행 시점에 채운다 | 코드 확인 |
| R-02 | 요청 경로(`createRenderRequest` → `renderConfigFromRequest`) | `createRenderRequest`가 요청을 만든 뒤 직렬화와 파싱으로 검증한다. `version`은 1, `projectDir`와 `outputPath`는 비어 있지 않은 문자열, `fps`는 양의 정수 `num`과 `den`, `quality`는 3값 중 하나, `format`은 6값 중 하나, `workers`는 정수 1 이상, `hlsSegmentSeconds`는 정수 1 이상, `maxRenderMs`와 `crf`, `gifLoop`는 0 이상 정수, `engineConfig`는 스냅샷 검증을 통과해야 한다. `format`은 요청에서 필수이고(`RenderConfig`에서는 선택), `keyframeIntervalSeconds`는 정수가 아닌 양수 검사이고, `variables`는 평범한 객체, `strictVariables`는 boolean이어야 한다. `createRenderRequest`는 `engineConfig`가 없으면 `resolveConfig(engineOverrides)`로 채운다. 어기면 `Render request <field> ...` 메시지의 `Error`를 던진다. `renderConfigFromRequest`는 `engineConfig`를 `producerConfig`로 옮기고 `allowOutsideProjectAssets`는 호출자가 `true`를 준 때만 true로 둔다. `RenderRequestOptions`에 `motionBlur`가 없어서 `motionBlur`는 이 경로로 설정할 수 없다. `createRenderJob`은 이 검증을 다시 하지 않고, 직접 부르는 호출자(studio, benchmark 등, R-46)는 이 검증을 거치지 않는다 | 코드 확인 |
| R-03 | `executeRenderJob` 시작 | work 디렉터리를 만들기 전에 `validateHlsRenderConfig`, `validateDeliveryEncoderConfig`, `validateChromaSubsamplingConfig`를 이 순서로 부른다. hls는 `hlsSegmentSeconds`가 양의 정수가 아니거나 `hdrMode: "force-hdr"`이거나 `useGpu: true`이면 거부, `proresProfile`은 mov에서만, `keyframeIntervalSeconds`와 `maxBitrate`와 `bufferSize`는 mp4에서만(hls에서 `keyframeIntervalSeconds`는 따로 거부), `chromaSubsampling: "444"`는 mp4, SDR, `useGpu` 없음에서만 허용한다. 위반은 일반 `Error`를 던지며 `job.status`는 `queued`, `job.error`는 비어 있고 `onProgress`도 불리지 않는다. 이후 단계에서 나는 오류는 `failed`로 기록된다(R-37). 같은 이유로 `outputPath` 부모의 `mkdirSync`, `createRenderWorkDir`, `new RenderExecutionContext`, 파이프라인 진입 직후의 `new ArtifactTransaction`(`renderOrchestrator.ts:3195`)이 권한이나 디스크 문제로 던져도 `job`은 `queued`로 남는다. `failed` 기록은 `3264`의 `try` 안에서 나는 오류부터다. 자동 HDR 탐지가 HDR 소스를 찾은 뒤의 444 거부(`assertChromaSubsamplingSdr`)는 파이프라인 안에서 일어난다 | 코드 확인 |
| R-04 | work 디렉터리와 정리 | `outputPath`의 부모가 없으면 만든다. `debug`면 work는 `<producer 루트>/.debug/<job.id>`(`PRODUCER_RENDERS_DIR`이 있으면 그 상위의 `.debug`)이고 지우지 않는다. 아니면 `createRenderWorkDir`가 win32와 darwin에서는 `<tmpdir>/hf-render-*`, 그 밖에서는 `<outputPath 부모>/work-<job.id>-*`를 만들고, 그 전에 `outputDir`와 `prefix`의 부모(win32와 darwin에서는 `tmpdir()`) 둘 다를 훑어 소유 프로세스가 죽은 이전 렌더 디렉터리를 best-effort로 지운다. `backup`(`TRANSACTION_BACKUP`)을 가진 디렉터리는 복구 대상이라 건드리지 않는다. `RenderExecutionContext`가 정리 함수를 등록 역순(LIFO)으로 정확히 한 번 실행한다(ETA guard 중지, 메모리 sampler 중지, probe 세션 닫기, file server 닫기, 스테이징 롤백, work 디렉터리 삭제 순). 정리 함수가 던져도 debug 로그만 남기고 렌더 결과를 바꾸지 않는다. `KEEP_TEMP=1`이고 `job.status`가 `complete`일 때만 work를 보존한다. `deadlineAtMs` 옵션은 컨텍스트에 있지만 `executeRenderJob`은 넘기지 않아 쓰이지 않는다 | 코드 확인 |
| R-05 | 단계 순서 | 순서는 compile, probe, extract videos, HDR 판정, audio 시작, file server(probe가 안 띄웠으면), GPU 모드 확인, 캘리브레이션(조건부), 워커 수 결정, 캡처 plan 결정, audio 대기, 캡처(+disk면 encode), probe 세션과 file server 닫기, assemble(png-sequence와 gif 제외), 산출물 검증, commit이다. 단계마다 `observeRenderStage`로 감싸 시작, 종료, 실패를 기록한다. status는 `queued`, `preprocessing`(compile 5%, extract 10%, audio 20%), `rendering`(25%부터), `encoding`(disk 경로), `assembling`(90%), `complete`(100%)로 바뀐다 | 코드 확인 |
| R-06 | compile 단계 | `resolveEntryHtmlPath`가 진입 파일을 읽는다(프로젝트 밖이면 오류. `<template>` 진입이면 `index.html`에서 독립 진입을 뽑아 `workDir/standalone-entry.html`에 씀). `compileForRender`(composition-contract R-25)를 부른 뒤 `workDir/compiled`에 `index.html`, 서브 컴포지션, 프로젝트 밖 asset 복사본(디렉터리 밖으로 나가는 경로는 건너뜀)을 쓰고 `debug`면 `summary.json`도 쓴다. drawElement를 켜 둔 상태에서 CSS 3D(`3d`), 조상의 background-image(`ancestor_background_image`), 셰이더 전환(`shader_transitions`), chroma 444(`chroma_444`)가 있으면 `cfg.useDrawElement`를 끄고 이유를 `deCompileGate`에 남긴다. 셰이더 전환 gate는 `PRODUCER_EXPERIMENTAL_FAST_CAPTURE`가 `true`가 아닐 때만 작동한다. drawElement가 꺼졌고 `resolveConfig`가 drawElement 때문에 자동으로 끈 표시(`pageSideCompositingAutoDisabled`)가 있으면 `cfg.enablePageSideCompositing`을 true로 되돌린다(R-10의 입력). 그 뒤 `forceScreenshot`을 알파와 render mode hint로 한 번 확정해 `cfg.forceScreenshot`에 쓰고 반환한다(1.3.5). 프로젝트 밖 미디어는 `dropMediaOutsideProject`로 떨구고 미디어 타입을 사전 점검한다 | 코드 확인 |
| R-07 | compile 단계의 입력 오류 | 진입 파일이 없으면 `Entry file not found: <path>`, 프로젝트 밖이면 `Entry file "<rel>" leads outside the project folder`, `<template>` 진입인데 `index.html`이 없거나 `data-composition-src`로 마운트되지 않으면 해당 `Error`를 던진다. `outputResolution`은 `resolveDeviceScaleFactor`가 정수 배율, 같은 종횡비, HDR과 알파 비호환을 검사하고 어기면 `Error`를 던진다. 종횡비 무관 별칭(`1080p`, `hd`, `4k`, `uhd`)은 컴포지션 방향에 맞는 사전 설정으로 바꾼다. 이 오류들은 재시도 없이 `failed`로 끝난다 | 코드 확인 |
| R-08 | probe 단계 | 브라우저는 `cfg.videoLayerPassthrough`, 큰 비디오 박스 측정, 또는 `probeRequiresBrowser`(변수 검사 필요, 길이 0 이하, 미해결 서브 컴포지션, 자동 시작 비디오, 스크립트 오디오 볼륨, 변수 바인딩 미디어, 런타임 삽입 미디어 중 하나)일 때만 띄운다. 띄우면 file server와 probe `CaptureSession`을 만든다. 세션 생성이나 초기화가 실패하면 `isTransientBrowserError`일 때 한 번 더 시도하고(최대 2회) 아니면 던진다. 세션이 BeginFrame으로 떴으면 `probeBeginFrameLiveness`를 30초 한도로 돌려 실패하면 screenshot 세션으로 다시 띄우고 `beginFrameStalled`를 true로 한다. 길이는 컴파일의 `staticDuration`이 0 이하일 때만 브라우저에서 읽는다. 미해결 서브 컴포지션은 `resolveCompositionDurations`와 `recompileWithResolutions`로 풀고 `discoverMediaFromBrowser`로 동적 미디어를 `composition`에 합친다. 불필요하면 브라우저를 띄우지 않고 `fileServer`와 `probeSession`은 null이다 | 코드 확인 |
| R-09 | 길이와 프레임 수 | `totalFrames = durationToFrameCount(duration, fps)`이고 `raw = duration × fps`가 가장 가까운 정수와 1e-3 이내면 그 정수, 아니면 `ceil(raw)`다. `duration <= 0`이면 진단(GSAP 미로드, `window.__timelines` 비어 있음, 브라우저 오류 줄)을 붙인 `Composition duration is 0, so this would produce a black video.` 오류를 던진다. 이어서 `validateRenderDuration`이 길이, fps, `totalFrames`가 유한 양수 안전 정수이고 `totalFrames <= ceil(86400 × fps)`인지 검사하고 어기면 `PlanValidationError`(`code: "DISTRIBUTED_DURATION_OUT_OF_RANGE"`)를 던진다 | 코드 확인 |
| R-10 | file server 조립 | 오케스트레이터는 `createFileServer({projectDir, compiledDir: workDir/compiled, port: 0, preHeadScripts: [VIRTUAL_TIME_SHIM], fps, allowOutsideProjectAssets})`를 부른다. probe가 만든 서버가 있으면 재사용한다. `HF_EARLY_STUB`, `RENDER_CAPTURE_MODE_SHIM`, `buildRenderModeScript`, `HF_BRIDGE_SCRIPT`는 `createFileServer`가 직접 끼운다(capture-encode-engine R-01이 소유). 셰이더 전환을 page-side compositing으로 처리하는 렌더(`cfg.enablePageSideCompositing`이거나 gif이고, `hasShaderTransitions`이고, HDR 없음, 형식이 mp4, gif, hls)만 `addPreHeadScript(HF_PAGE_SIDE_COMPOSITING_STUB)`를 더 호출한다. 이때 probe 세션이 있으면 pre-head 스크립트를 로드하려고 닫는다. 이어서 `pageInstallsShaderCompositor`가 임시 세션을 띄워 컴포지션의 shader-transitions 빌드가 이 브라우저에서 합성기(`__hf-page-side-compositor` 캔버스)를 설치하는지 시험한다. 시험이 false이면 page-side를 끄고 Node 쪽 layered 경로로 간다(R-12). 시험이 던지면(abort 제외) page-side 값을 유지한 채 warn만 남기고 캡처 단계가 자기 세션으로 이어간다. 시험이 true이면 `forceScreenshot`을 true로 올린다. 서버는 캡처가 끝난 뒤(assemble 전)에 닫고 실패 경로에서도 정리 함수가 닫는다 | 코드 확인 |
| R-11 | 비디오 프레임 추출 단계와 coverage gate | 타임라인 끝 뒤에서 시작하는 비디오는 목록에서 뺀다. `hdrMode`가 `force-sdr`가 아니면 원본 색 공간을 먼저 probe한다. `extractAllVideoFrames`(engine)로 프레임을 뽑고 실패한 소스는 `errors`에 담긴다. 호스트 장애(`external_interruption`, `disk_full`)는 정책과 무관하게 즉시 던진다. 그 밖의 소스 실패는 `HF_VIDEO_EXTRACTION_FAILURE_MODE`가 `enforce`(기본)이면 `failureToEnforce`로 돌려주고 오케스트레이터가 체크포인트를 남긴 뒤 던진다. `observe`는 로그만, `off`는 무시한다. `HF_VIDEO_EXTRACTION_MAX_RETRIES=1`이고 모드가 `off`가 아니면 transient 실패를 한 번 재시도한다(기본 0. HDR 색 공간 probe와 deferred 추출에도 같은 값을 쓴다, `renderOrchestrator.ts:3987`). 이어서 클립별 캡처 대비 기대 프레임 비율(coverage)이 `HF_VIDEO_COVERAGE_THRESHOLD`(기본 0.95, 0 이하면 끔) 미만이면 `VideoFrameCoverageError`를 던진다. 비디오 자체의 오디오는 `appendAutoDetectedVideoAudio`가 `composition.audios`에 더한다. 프레임 디렉터리는 `compiled/__hyperframes_video_frames/<id>`로 연결된다 | 코드 확인 |
| R-12 | HDR 판정(개념) | 추출 결과와 이미지 색 공간으로 `resolveEffectiveHdrMode`가 유효 HDR 여부를 정한다. 네이티브 HDR 소스가 있으면 `hasHdrContent`이고 plan이 `hdr_layered`가 된다. 이 경로는 Node 쪽에서 레이어를 합성하며 자기 캡처와 인코딩을 한다(`captureHdr*.ts`). HDR에서 `outputResolution`과 chroma 444는 거부된다. layered 판정은 `shouldUseLayeredComposite`(`hdrCompositor.ts:458`)가 `HDR 콘텐츠이거나 (셰이더 전환이고 png-sequence가 아님)`으로 하고, 호출부(`renderOrchestrator.ts:4750-4756`)는 셰이더 전환 인자로 `hasShaderTransitions && !isGif`를 넘긴다. 그래서 page-side 합성을 못 쓰는 셰이더 전환 렌더(R-10의 시험이 false이거나 page-side를 안 쓰는 설정)는 webm, mov, mp4, hls에서만 SDR이어도 layered 경로가 된다. png-sequence는 layered가 아니고 page-side도 지원하지 않아 셰이더 블렌드 경로가 없다. gif는 layered 대상에서 빠지므로 page-side 시험이 false이면 셰이더 블렌드 경로가 없다. 이 문서는 내부를 쓰지 않는다 | 코드 확인 |
| R-13 | 오디오 단계의 위치와 실패 | 비디오 추출과 HDR 판정 뒤에 `runAudioStage`를 시작하고 약속(`pendingAudio`)을 들고 있는다. 이후 file server, GPU 모드 확인, 캘리브레이션, 워커 수, 캡처 plan 결정이 오디오와 겹쳐 돈다. 캡처 stage를 부르기 직전에 오디오를 기다리고(5초마다 진행 이벤트), 결과로 `hasAudio`, 경로, `audioLoweredDb`를 얻는다. `audioLoweredDb`가 있으면 `job.audioLoweredDb`에 쓰고 info 로그만 남기며 `audio_lowered` 경고는 만들지 않는다(CLI가 만든다, R-41). `audioError`가 있으면 `audio_processing_failed` 경고(audio-mix-fx R-30)를 정책에 넣어 `RenderQualityError`로 캡처 전에 끝낸다. 그 사이에 다른 단계가 실패해도 `catch`가 오디오 약속을 기다린 뒤에 오류를 처리한다. 오디오 stage가 reject하는 경로도 있다. 전달 한도 단계(`limitDeliveryPeaks`, `constrainAacTruePeak`)가 실패하면 stage가 `Audio true-peak limit failed` 또는 `Audio true-peak check failed`를 던지고(audio-mix-fx R-31), 오디오 FFmpeg가 외부 중단되면 `EncoderInterruptedError`를 던진다(`assertAudioNotInterrupted`). 이 경로는 `audioError` 경고를 거치지 않고 `await`에서 일반 `Error` 또는 `EncoderInterruptedError`로 렌더를 끝낸다(`RenderQualityError`가 아님). 믹서가 `AudioFxRenderError`로 reject하면 stage가 잡아 `audioError`로 바꾸므로 위 경고 경로를 탄다. 오디오 믹스 내용은 audio-mix-fx가 소유한다 | 코드 확인 |
| R-14 | `forceScreenshot` 결정 | 값의 결정 지점은 1.3.5 표의 행들이다. 컴파일 단계가 `cfg`에 쓴 뒤 오케스트레이터는 `cfg`를 다시 쓰지 않고(video layer 예외) 지역 변수와 불변 `CapturePlan`으로만 옮긴다. 한 번 true가 된 값을 되돌리는 곳은 없다. disk 경로(R-21, R-22)와 HDR 경로는 BeginFrame 실패를 screenshot으로 낮추는 전체 재렌더를 하지 않는다(BeginFrame 실패의 전체 재렌더는 streaming 경로에만 있다, R-24) | 코드 확인 |
| R-15 | 캡처 경로(plan) 선택 | `createCapturePlan`이 순서대로 정한다. `useLayeredComposite`이면 `hdr_layered`, 아니면 `useSegmentedCapture`이면 `sdr_segmented`, 아니면 `useStreamingEncode`이면 `sdr_streaming`, 아니면 `sdr_disk`다. `forceParallelStream`은 streaming에서만 유지된다. `useLayeredComposite`는 page-side compositing을 쓰지 않고 HDR 콘텐츠이거나, 셰이더 전환이 있고 형식이 gif와 png-sequence가 아닐 때다(R-12). drawElement를 기본으로 켜 둔 렌더는 단일 워커 streaming이거나 검증된 병렬 streaming일 때만 켜 둔 채로 가고, 그 밖의 경로(disk, 검증 없는 다중 워커)는 `PRODUCER_EXPERIMENTAL_FAST_CAPTURE=true`가 아니면 `cfg.useDrawElement`를 끈다(`shouldClampDefaultDrawElement`). 멀티 워커이고 drawElement가 꺼졌고 streaming이 가능하고 layered가 아닌 mp4, hls(`outputUsesH264Pipeline`. mov는 포함되지 않는다)는 interleaved 병렬 streaming(`shouldStreamParallelCapture`)으로 간다. 스위치 `HF_CAPTURE_PARALLEL_STREAM`은 비어 있으면 병렬 모드가 BeginFrame(Linux, headless shell, screenshot 강제 없음, supersampling 없음)일 때만 켜지고, `false`, `0`, `off`, `no`이면 꺼지고, 그 밖의 값이면 screenshot 모드에서도 켜진다(`isCaptureParallelStreamRouterEnabled`). 멀티 워커 screenshot은 기본으로 disk 경로다 | 코드 확인 |
| R-16 | streaming 사용 여부 | `explainStreamingEncodeGate`가 순서대로 정한다. `enableStreamingEncode`가 꺼졌으면 `disabled_by_config`, 형식이 `png-sequence`나 `gif`면 `format_excluded`, 길이가 유한 양수가 아니면 `invalid_duration`, 길이 상한 옵션(`streamingEncodeDurationCapEnabled`, 기본 꺼짐, 켜면 240초 초과)이 켜졌고 low memory가 아니면 `duration_cap`, `forceParallelStream` 또는 `HF_DE_PARALLEL_STREAM=true`이면 `parallel_forced`(켬), 워커 1이면 켬, 워커 2 이상이면 `multi_worker`(끔)다. 결과로 로그 `streaming-encode gate`에 이유가 남는다. `enableStreamingEncode`가 false가 되는 경우는 환경변수나 override로 끈 때와, `resolveConfig`가 win32, software GPU 강제, `workers === 1`, (길이를 알면 120초 초과)가 겹칠 때 자동으로 끈 때다(`shouldAutoDisableStreamingEncodeOnWin32Compound`, 명시적 설정이 있으면 그쪽이 이긴다). 이때 게이트는 `disabled_by_config`이고 plan은 처음부터 disk다 | 코드 확인 |
| R-17 | segmented 캡처 선택과 구성 | `shouldSegmentCapture`는 기본으로 꺼져 있다(`HF_SEGMENTED_MIN_SECONDS` 기본이 무한대). `HF_SEGMENTED_CAPTURE=false`(또는 0, off, no)면 항상 끔, streaming이 불가하거나 layered(HDR, 셰이더 전환) 경로면 끔, 형식이 mp4와 mov가 아니면 끔, `HF_SEGMENTED_CAPTURE=true`면 켬, 아니면 길이가 `HF_SEGMENTED_MIN_SECONDS` 이상일 때 켠다. 켜지면 `planSegments(totalFrames, segmentFrames)`가 `[start, end)` 조각으로 나눈다(`segmentFrames`는 `HF_SEGMENT_FRAMES`, 기본 3000, 최소 30). 각 세그먼트를 닫힌 GOP로 자기 encoder에 흘려 쓰고 마지막에 concat copy한다. 세그먼트는 `projectDir/renders/.hf-segments/<planHash>`(work 디렉터리 밖)에 쌓고 `manifest`에 완료 인덱스를 기록한다. `resumeSegments`일 때만 같은 `planHash`의 기록을 이어 받고, 아니면 디렉터리를 지우고 시작한다. 성공 뒤 `keepSegments`가 아니면 지우고, 실패나 취소에서는 `--resume`을 위해 남는다. `HF_SEGMENTED_MIN_SECONDS`는 0 이상 유한 수만 유효하고 그 밖의 값이나 빈 값은 무한대(꺼짐)로 돌아가며, 0이면 길이와 무관하게 켜진다 | 코드 확인 |
| R-18 | 워커 수 결정 | 순서대로 적용한다. 컴포지션이 html-in-canvas(`htmlInCanvas` hint)면 1. low memory이고 `workers`가 없으면 1. `workers`가 있으면 `max(1, min(24, workers))`. 자동이면 `computeWorkerSizing`이 `min(cpu-2 또는 cgroup 한도, 총 메모리의 절반을 1536MB로 나눈 값, floor(totalFrames/30))`을 기본으로 하고, `totalFrames < 60`이면 1, `totalFrames >= minParallelFrames(120)`이면 최소 2, 상한은 `max(6, min(16, floor(cpu/8)))`(`concurrency`가 숫자면 그 값)이다. 큰 렌더(1000프레임 이상 또는 비용 가중 프레임이 `max(120, 333)` 이상)는 `floor(cpu / (2.5 × 비용 배수))`로 더 줄이고 마지막으로 V8 힙 한도(`(heap−1024MB)/320MB`)로 자른다. 비용 배수는 정적 추정과 캘리브레이션 측정의 조합이다. 변형이 둘 있다. Apple GPU disk 캡처(darwin, hardware GPU, layered 아님, 병렬 streaming 아님)는 힙 128MB/워커, 코어 1.75/워커(`coresPerWorker`가 기본값일 때), 자동 상한 `max(기본 상한, 8)`을 쓰고, Electron 또는 `HYPERFRAMES_CLIENT`가 `desktop/`으로 시작하는 데스크톱 앱은 힙 640MB/워커를 쓴다. 그 뒤 video layer면 1로 덮고, resolve된 워커 수가 2 이상일 때만 drawElement 병렬 router가 적격이면 3(`ROUTER_WORKER_COUNT`), 단일 워커 inversion이 적격이면 1로 고정한다(R-45) | 코드 확인 |
| R-19 | 캘리브레이션 | `workers`가 없고, `totalFrames >= 60`이고, html-in-canvas가 아니고, low memory가 아니고, drawElement inversion과 router가 적격이 아닐 때만 돈다. 별도 Chrome을 띄워 프레임 0, 25%, 50%, 75%, 마지막 중 중복을 뺀 최대 5장을 캡처해 시간을 잰다. p95를 600ms로 나눈 값(1 이상, 최대 8)이 비용 배수다. 중앙값(`medianMs`)은 ETA 사전 점검(R-33)에 쓴다. BeginFrame 캘리브레이션이 위 오류(1.3.5)로 실패하면 screenshot으로 한 번 다시 하고 `forceScreenshot`을 true로 한다. 그것도 실패하거나 다른 오류로 실패하면 배수 8의 보수적 추정을 쓰고 렌더는 계속한다. 캘리브레이션 세션의 프로토콜 timeout은 30초로 줄인다 | 코드 확인 |
| R-20 | 프레임 분배와 병렬 풀 | `distributeFrames`는 프레임을 `ceil(N/워커)` 연속 구간으로, `distributeFramesInterleaved`는 워커 i가 i, i+N, i+2N, ...을 맡게 나눈다. 병렬 streaming은 interleaved(router가 켜졌을 때)나 연속 구간으로 나누고 `createFrameReorderBuffer`로 프레임을 순서대로 encoder에 쓴다. 각 워커는 자기 브라우저 세션을 갖는다. 풀이 실패하면 첫 풀-치명 실패(`cancelled`가 아닌 streaming 실패, disk에서는 `isFatalCaptureFailure`)가 `onWorkerFailure`를 먼저 부르고 그 뒤 나머지 워커를 abort한다(첫 실패가 abort 이유를 소유). 풀은 `[Parallel] Capture failed: ...` 메시지의 `CaptureFailure`(종류는 대표 워커 실패의 종류)를 던진다. disk 경로에서 `transient_browser`와 `protocol_timeout` 실패는 풀-치명이 아니어서(`isFatalCaptureFailure`는 `cancelled`, `transient_browser`, `protocol_timeout`을 제외) 다른 워커가 계속되고 비는 프레임은 R-21이 다시 잡는다. `executeWorkerTask`는 자체 재시도 없이 한 번 시도하고 `catch`에서 실패를 분류해 `onFailure`를 부른 뒤 `failure`를 담은 결과를 돌려준다. 풀은 모든 워커가 끝난 뒤 오류가 하나라도 있으면 전체를 `[Parallel] Capture failed`로 던진다. 다중 워커 streaming에서 drawElement를 쓰면 워커 단계별 deadline(`HF_DE_PARALLEL_PHASE_TIMEOUT_MS`, 기본 30초, `0`이면 끔)이 걸리고, worker 0이 첫 세션 검증(`verifyFirstSession`)을 끝낼 때까지 다른 워커가 기다린다. 워커가 끝나면 `mergeWorkerFrames`가 프레임 파일을 `captured-frames`로 rename(실패하면 copy)한다 | 코드 확인 |
| R-21 | disk 병렬 캡처의 재시도 사다리 | `executeDiskCaptureWithAdaptiveRetry`가 시도마다 `capture-attempt-N`을 쓰고 빠진 프레임 범위를 `captured-frames`에서 다시 센다. 재시도는 워커가 2 이상일 때만 허용된다. (1) `cancelled`는 즉시 다시 던진다. drawElement 검증 또는 capture 오류도 다시 던진다(R-25). (2) 빠진 프레임이 없으면 성공. (3) 진행이 있었고(남은 프레임이 이번 시도의 목표보다 적음) 워커가 2 이상이면 워커를 절반(`floor(n/2)`, 최소 1)으로 줄여 빠진 범위만 다시 한다. 진행이 없으면 "구조적으로 깨진 컴포지션"으로 보고 `Capture completed but N frame(s) are missing`을 던진다. (4) 진행이 없어도 `Network.enable timed out` 또는 `Navigation timeout`이면 워커 절반으로 재시도(워커 1이면 `protocol_timeout`에 한해 1회). (5) `transient_browser`는 같은 워커 수로 1회(`MAX_TRANSIENT_CAPTURE_RETRIES`) 재시도하고 진행 여부를 묻지 않는다. (6) 그 밖에는 stall 또는 `transient_browser`, `protocol_timeout`(`isRecoverableParallelCaptureError`)이면서 진행이 있고 워커가 2 이상일 때 절반으로 재시도하고 아니면 던진다. 재시도마다 dedup perf를 새로 모은다 | 코드 확인 |
| R-22 | disk 순차 캡처와 디스크 공간 | 워커 1이면 같은 프로세스에서 순차 캡처한다. `transient_browser` 실패 시 첫 빠진 프레임부터 새 세션으로 1회 이어 받고, 그 밖의 오류는 브라우저 콘솔을 붙여 던진다. 렌더 시작 때 디스크를 미리 거부하지 않는다. 캡처 중 첫 10프레임을 쓴 뒤 측정한 프레임당 바이트로 남은 용량을 투영해 필요량이 여유의 90%를 넘으면 `diskCaptureShortfallError`를 던진다(`captureStage.ts:298`, `"measured"` 기준에서만). 안내 문구는 `--workers 1`로 streaming 사용, 디스크 확보이고 오류는 코드 없는 일반 `Error`다. 추정 함수 `estimateDiskCaptureBytes`(JPEG는 원시 RGBA를 quality 80 이하에서 1/8, 80 초과에서 1/4로 나누고 PNG는 나누지 않음)와 `inspectDiskCaptureHeadroom`(추정이 여유의 90% 이하이면 가능)은 streaming 실패 뒤 disk로 내려가도 되는지 판정에만 쓰인다(`renderOrchestrator.ts:5430`) | 코드 확인 |
| R-23 | streaming 경로의 내부 복구 | encoder를 먼저 띄운다. 실패하고 abort가 아니면 `{success:false}`를 돌려주고 오케스트레이터가 plan을 `streaming_unavailable`로 바꿔 disk 경로로 간다(이때 default drawElement는 끈다). 캡처 중 워커 풀이나 순차 루프가 stall(`ParallelCaptureStallError`, `SequentialCaptureStallError`)로 멈추면, 그 사이에 새로 써진 프레임이 있고 abort가 아닐 때 첫 미작성 프레임부터 새 워커로 이어 받는다. 이어받기는 최대 3회(`STALL_RESUMES_BEFORE_FALLBACK`)이고 그 뒤나 진전이 없으면 던진다. encoder 쓰기 실패는 reorder buffer를 abort해 대기 중인 워커를 깨운다. streaming 단계의 stall 한도는 `HF_DE_STALL_MS`(옛 이름 `HF_DE_PARALLEL_STALL_MS`), 기본 60초다. 세션 초기화 단계의 stall 한도는 `SESSION_INIT_STALL_MS` 300초다(`captureStreamingStage.ts:102`). BeginFrame으로 아직 프레임을 못 그렸을 때는 `beginFrameFirstFrameDeadlineMs`가 있으면 그 값과 stall 한도 중 작은 값을 쓴다. 이 값은 엔진과 programmatic 기본에는 없고 로컬 CLI(auto)만 20초로 설정한다 | 코드 확인 |
| R-24 | streaming 실패 뒤 전체 재렌더 | `runCaptureStreamingStage`가 던지면 `shouldRetryViaPinnedFallback`이 판정한다. 취소(`RenderCancelledError` 또는 signal abort)와 `EncoderInterruptedError`는 재시도하지 않는다. drawElement 검증 또는 capture 오류, BeginFrame으로 캡처하던 시도의 모든 실패(`isBeginFrameCapture`: plan이 screenshot 강제가 아니고 drawElement가 아니고 병렬 모드가 beginframe), drawElement renderer stall, 순차 stall, 병렬 stall, 프레임 2 이후의 encoder 사망(`Streaming encoder exited before frame N was written`에서 N이 2 이상), `transient_browser` 오류는 항상 재시도한다. 그 밖의 오류는 drawElement 단일 워커 inversion이나 병렬 router로 고정된 렌더(`deWorkerInversion === "inverted"` 또는 `deParallelRouter === "routed"`)일 때만 재시도한다. 재시도하면 `replanAfterFailure`가 `forceScreenshot: true`인 새 plan을 만든다. default 라우팅이면 같은 종류에서 `workerCount`를 유지하되(OOM이거나 interleaved 병렬 streaming이었으면 1) streaming으로, inversion이나 router 라우팅이면 미리 계산한 fallback(원래 워커 수의 screenshot, disk 또는 streaming)으로 간다. OOM이면 `memoryExhaustionFallback`을 쓴다. 남아 있는 probe 세션은 닫고 재시도 plan이 streaming이면 다시 실행하고 disk면 R-21 경로로 간다. 재시도는 한 번뿐이고 두 번째 실패는 그대로 던진다 | 코드 확인 |
| R-25 | drawElement 검증 실패와 disk, segmented 경로 | disk 병렬 경로에서 drawElement 검증 또는 capture 오류가 나면(취소 제외) `captured-frames`를 비우고 `cfg.useDrawElement`를 끄고 probe 세션을 닫은 뒤 screenshot disk plan으로 한 번 다시 돈다. 손상된 프레임이 완전한 파일로 남아 있어 누락 검사가 성공으로 오인하기 때문이다. segmented 경로는 drawElement 검증, capture 오류, drawElement renderer stall이면 세그먼트 디렉터리를 지우고 완료 기록을 비운 뒤 screenshot으로 segmented를 한 번 다시 한다. 다른 segmented 실패는 재시도 없이 던진다. segmented에서 첫 세그먼트의 encoder가 못 뜨고 워커가 1이면 `streaming_unavailable`로 일반 streaming으로 내려간다 | 코드 확인 |
| R-26 | segmented 내부 복구 | 세그먼트는 `createSegmentQueue`에서 하나씩 꺼내 워커가 처리한다. 브라우저 target 손실(`target closed`, `detached frame`, `session closed`)이면 그 세그먼트 파일을 지우고 세션을 새로 열어 한 번 다시 캡처한다(abort면 던짐). 같은 이유가 아닌 오류는 던진다. 워커는 `HF_SEGMENT_BROWSER_RECYCLE`(기본 3)개 세그먼트마다 브라우저를 새로 연다(0이면 끔) | 코드 확인 |
| R-27 | `protocolTimeout` 스케일 | 첫 브라우저를 띄우기 전에 `scaleProtocolTimeoutForComposition(cfg.protocolTimeout, {outputWidth, outputHeight})`로 키운다. 값은 올리기만 하고 최대 1,800,000ms다(`config.ts:589`, capture-encode-engine R-18). 올라가면 `cfg.protocolTimeout`을 바꾸고 로그를 남긴다. probe 브라우저가 단일 워커 캡처에 재사용되므로 probe 전에 적용한다 | 코드 확인 |
| R-28 | disk 경로의 encode 단계 | streaming과 segmented가 아닌 경로에서만 돈다. 형식별로 갈린다. `png-sequence`는 `captured-frames`의 PNG를 `outputPath` 디렉터리에 `frame_NNNNNN.png`로 복사하고 오디오가 있으면 `audio.m4a`를 같이 둔다(PNG가 0개면 오류). `gif`는 두 패스 팔레트로 스테이징 파일에 쓴다. mp4, webm, mov, hls의 중간 산출물은 `encodeFramesFromDir` 또는 청크 인코딩(`enableChunkedEncode`) 결과 `video-only.<ext>`(hls는 `.mp4`)다. 멀티 워커 JPEG H.264 SDR이고 워커가 CPU 수보다 적고 `enableChunkedEncode`가 꺼져 있고 png-sequence와 gif가 아니면 캡처하면서 인코더에 프레임을 먹이는 `encodeWhileCapturing`을 켜서 interleaved로 분배한다(drawElement일 때는 안 씀) | 코드 확인 |
| R-29 | assemble 단계 | `png-sequence`와 `gif`는 건너뛴다. 오디오가 있으면 `padOrTrimAudioToVideoFrameCount`로 오디오 길이를 영상 프레임 수에 맞춘 사이드카를 만들고(내부는 audio-mix-fx가 assemble 소관으로 제외한 부분이라 이 스펙은 호출 위치만 쓴다. 결과의 `audioLoweredDb`는 `job`에 기록하며 의미는 audio-mix-fx R-19), hls면 `packageHls`(`-c copy`로 MPEG-TS 분할, `master.m3u8`, `video.m3u8`, 오디오 있으면 `audio.m3u8`), 아니면 `muxVideoWithAudio`로 mux한다. 오디오가 없으면 hls는 영상만 패키징, 그 외는 `applyFaststart`로 `moov` 앞당기기를 한다. 각 외부 호출이 `success: false`이면 `Audio duration normalization failed`, `Audio muxing failed`, `Faststart failed`, `HLS packaging failed` 형태로 던진다(FFmpeg 외부 중단이면 `EncoderInterruptedError`). 이 단계의 출력 위치는 `outputPath`가 아닌 스테이징 경로다 | 코드 확인 |
| R-30 | 산출물 트랜잭션 | `ArtifactTransaction`은 파이프라인 시작 시 만들어지고 `outputPath`의 형제 경로 `.<stem>.hf-transaction-*` 디렉터리(소유자 파일 포함)에 스테이징 경로를 둔다. 종류는 png-sequence와 hls가 `directory`, 그 외 `file`이다. `validate`는 파일이 비어 있지 않은지 확인하고, 기대값(`buildArtifactExpectation`, gif는 기대값 없음)이 있으면 ffprobe로 길이가 기대보다 `1/fps`초(fps가 없으면 0.02초) 넘게 짧으면 `Render artifact is truncated`, 프레임 수가 1프레임 넘게 모자라면 같은 오류, 크기가 안 맞으면(홀수 변은 +1 허용) `wrong size` 오류를 던진다. 길이 probe가 0이거나 실패하면 통과시키지 않고 던진다. ffprobe가 프레임 수를 못 주는 출력(webm, hls에서 흔함)은 프레임 수 검사를 건너뛰고 debug 이벤트 `artifact_frame_count_unavailable`만 남기며 길이와 크기 검사는 계속한다. png-sequence는 최상위 `frame_N.png` 개수를 기대 프레임 수와 `max(1, ceil(0.2%))` 허용으로 비교하고 hls는 `master.m3u8` 존재와 `video.m3u8` 길이를 본다. `commit`은 먼저 기대값 없이 `validate()`를 다시 해(비어 있지 않은 파일 또는 디렉터리 확인) 그 뒤 파일이면 스테이징에서 `outputPath`로 한 번의 rename(기존 파일을 원자적으로 대체), 디렉터리이고 대상이 없으면 rename, 대상이 있으면 대상을 백업으로 옮긴 뒤 rename하고 실패하면 백업을 복구한다(원자적 가시성은 없음). `rollback`은 스테이징을 지우고 백업이 있고 대상이 비어 있으면 되돌린다. 커밋 전까지 기존 `outputPath`는 건드리지 않는다 | 코드 확인 |
| R-31 | 정상 종료 | validate 뒤에 `perfSummary`를 `job`에 쓰고, `commitArtifactTransaction`이 `assertRenderActive`와 취소 검사를 한 번 더 하고 commit한다. 성공하면 `job.outputPath = outputPath`, `status: "complete"`, progress 100, `outcome`은 `warnings`가 비면 `completed`이고 아니면 `completed_with_warnings`다. 이벤트 큐를 flush하고 정리 함수가 실행된다. 반환값은 없다 | 코드 확인 |
| R-32 | 취소 | `AbortSignal`(및 `assertRenderActive`)이 중단 신호를 준다. 오케스트레이터는 단계 경계와 긴 작업 사이에서 `assertNotAborted`로 확인하고 `RenderCancelledError("render_cancelled")`(reason 기본 `aborted`)를 던진다. 신호는 컴파일 네트워크 요청, 추출, 오디오, 캡처 워커 풀, FFmpeg에 전달된다. `catch`는 `tooSlow`가 아니고 오류가 `RenderCancelledError`이거나 신호가 aborted이면 `job.error`를 쓰고 `status: "cancelled"`, `outcome: "cancelled"`로 바꾸고 `RenderCancelledError`를 던진다(다른 종류 오류가 신호 때문에 났으면 새 `RenderCancelledError("render_cancelled")`로 바꿈). `failed`로 기록하지 않는다. 정리 함수가 스테이징을 롤백하고 work 디렉터리를 지우므로 부분 산출물은 `outputPath`에 남지 않고 기존 파일도 그대로다. `reason: "timeout"`과 `deadlineAtMs`는 현재 producer와 cli에서 아무도 쓰지 않는다. 취소로 브라우저가 닫혀 나는 `Target closed`는 재시도 판정에서 `cancelled`로 먼저 걸러진다 | 코드 확인 |
| R-33 | `maxRenderMs` 시간 예산 | 값이 양수일 때만 켠다. (1) 캘리브레이션 뒤, 캡처 전에 `checkCalibratedRenderEta`가 `경과 + totalFrames × (중앙값ms / 워커 수)`가 `2 × maxRenderMs`를 넘으면 `RenderTooSlowError`를 던진다(캘리브레이션을 안 했으면 이 검사는 건너뜀). (2) 캡처 중 5초마다 `job.framesRendered`를 보고, 캡처 시간 60초와 3프레임 이상이 쌓이면 측정 속도로 ETA를 계산해 같은 기준을 넘으면 오류를 일으킨다(프레임 수가 줄거나 0이면 표본을 다시 시작, 프레임이 모두 끝나면 감시 종료). 오류는 내부 `tooSlow` AbortController를 abort해 실행 신호를 끊고 `catch`가 이를 실패로 처리해(취소 분기를 타지 않음) 그대로 던진다. 오류는 `code: "RENDER_TOO_SLOW"`, `owner: "user"`, `retryable: false`, `publicMetadata`(`stage`, `framesCompleted`, `totalFrames`, `msPerFrame`, `etaMs`, `maxRenderMs`)를 가진다. CLI는 `maxRenderMs`를 요청에 싣지 않고 서버 본문만 싣는다(R-41, R-42) | 코드 확인 |
| R-34 | stall(진행 없음) 감시 | disk와 HDR 캡처 단계는 `observeRenderStage`의 stall 규칙(`frameStallRule`)을 쓴다. 규칙은 `job.framesRendered`를 5초마다 본다. 진행이 없는 한도는 `HF_DE_STALL_MS`(기본 60초), 시도의 첫 진행 전 한도는 `max(300초, min(900초, probe 브라우저 기동 시간 × 2), 일반 한도)`, 프레임이 모두 도착한 뒤 마무리 한도는 300초다. 한도를 넘으면 현재 시도의 abort 신호를 abort해 단계가 재시도하거나 정리하게 한 번 더 창을 주고, 살아 있는 시도가 없으면 `RenderStageStalledError`(`code: "RENDER_STAGE_STALLED"`, `kind: protocol_timeout`로 분류, `retryable: false`)로 단계를 실패시킨다. 정지한 프로세스는 `createStallClock`이 "기대 간격 + 15초"보다 긴 공백을 침묵 시간에서 빼 준다. 정지 감시는 static dedup의 확인 스크린샷도 진행으로 센다. streaming과 segmented 단계는 규칙 대신 자기 watchdog(R-23)을 쓴다 | 코드 확인 |
| R-35 | 페이지가 끝내 준비되지 않음 | 캘리브레이션이 `Runtime.evaluate` 시간 초과로 끝났고, 캡처된 프레임이 0이고, 최종 오류도 `Runtime.evaluate` 시간 초과면 오류를 `PageNeverReadyError`(`code: "PAGE_NEVER_READY"`, `owner: "user"`, `retryable: false`)로 바꿔서 던진다 | 코드 확인 |
| R-36 | 진행 보고 | `updateJobStatus`가 `job.status`, `currentStage`, `stageProgress`를 쓰고 `progress`를 0에서 100으로 자르고 반올림한 뒤 이전보다 작아지지 않게(`max`) 쓴다. `failed`, `complete`, `cancelled`면 `completedAt`과 `outcome`도 쓴다. 이 세 호출은 `stageProgress` 인자를 넘기지 않으므로 `job.stageProgress`는 undefined가 된다. 그 뒤 `onProgress(job, stage)`를 부른다. 프레임 진행(`capture`, `extract_video`, `encode`, `assemble`)은 첫 보고, 마지막 보고, 그 사이 250ms 간격으로만 콜백을 부르고 같은 stage와 progress 조합은 연속으로 두 번 보내지 않는다(`job` 객체는 매번 갱신). 호출자에게는 `RenderExecutionContext.events`가 `job`의 스냅샷(경고 복제 포함)을 만들어 순서대로 하나씩 전달한다. 싱크가 던지거나 거부하면 warn 로그로 삼키고 렌더를 멈추지 않는다. 종료 때 `flush`가 최대 10초 기다리고 못 비우면 경고 로그만 남긴다. 워커 시동 중에는 `Starting browsers (n/N ready)`가 `start_browsers` 코드로 나간다. 구간은 1.3.4 끝 단락이다 | 코드 확인 |
| R-37 | 실패 발행과 호출자가 받는 오류 | 파이프라인의 예외는 `catch`가 모은다. 먼저 오디오 약속을 기다린다. 이어서 오류를 `tooSlowError`, `pageNeverReady`, 아니면 원 오류 순으로 고르고, 스크립트 실패 경고가 있고 오류가 아직 `RenderQualityError`나 `RenderCancelledError`가 아니면 `RenderQualityError`로 바꾼다(`surfaceScriptFailure`). 취소가 아니면 OOM 안내, protocol timeout과 navigation timeout 설정 안내를 붙인 메시지를 만들고 `publishRenderFailure`가 `job.error`, `job.failedStage`(`currentStage`), `job.errorDetails`를 채운 뒤 `status: "failed"`, progress는 유지, 메시지 `Failed: <error>`로 이벤트를 낸다. 호출자에게 던지는 값은 안내 문구를 붙이기 전의 오류 객체(위 우선순위로 고른 것)이고 `job.error`에는 안내 문구가 붙은 문자열이 들어간다. `executeRenderJob`이 던지는 형은 `RenderCancelledError`, `RenderQualityError`, `RenderTooSlowError`, `PageNeverReadyError`, `VideoExtractionStageError`, `VideoFrameCoverageError`, `PlanValidationError`, `EncoderInterruptedError`, `CaptureFailure`(엔진), 일반 `Error`다 | 코드 확인 |
| R-38 | 경고 정책(`applyRenderWarningPolicy`) | 입력 경고를 `{...경고, stage: "capture-readiness"}`로 복제해 `job.warnings`에 합치되 `code`와 `details` JSON이 같은 것은 한 번만 넣는다. 합친 뒤 목록이 비면 끝낸다. 하나라도 있으면 로그를 남기고 `strictness`가 `strict`이거나 목록에 `audio_processing_failed`, `sub_timeline_script_failure`, `vfx_failure` 중 하나가 있으면 `job.warnings` 전체로 `RenderQualityError`를 던진다. 그 외 `best-effort`에서는 경고가 남고 렌더가 계속되며 최종 `outcome`이 `completed_with_warnings`가 된다. 호출 지점은 셋이다. 오디오 실패(캡처 전), 워커 세션 init 중 script 실패 hook(R-39), 캡처 뒤의 일괄 처리(layered 경고와 각 워커의 `perf.warnings`). 경고의 코드와 의미는 capture-encode-engine R-50이 소유한다 | 코드 확인 |
| R-39 | script 실패 hook | 엔진은 `CaptureOptions.onSubTimelineScriptFailure`를 `initializeSession` 도중 동기 호출한다(capture-encode-engine R-12). 워커 세션용 옵션(`buildWorkerCaptureOptions`, 즉 streaming, segmented, disk, HDR 캡처)은 이 hook에 `applyRenderWarningPolicy`를 연결(`withScriptFailureStop`)해서 script 실패 경고가 쌓이는 즉시 `RenderQualityError`가 init을 중단시킨다. 캘리브레이션 세션 옵션(`buildPrepCaptureOptions`)은 hook이 일반 `Error("a composition script failed, so this preparation session stops")`를 던진다. probe 세션은 hook이 없다. probe 세션을 재사용하는 단일 워커 렌더는 probe에 hook이 없어 init에서 중단되지 않는다. 이 경우 script 실패는 캡처가 모두 끝난 뒤 `applyRenderWarningPolicy`(`renderOrchestrator.ts:5721-5725`)에서야 `RenderQualityError`가 된다. 어느 경우든 오케스트레이터 `catch`가 `surfaceScriptFailure`로 `RenderQualityError`를 호출자에게 낸다 | 코드 확인 |
| R-40 | 성능 요약과 관측 | 성공하면 `buildRenderPerfSummary`가 `job.perfSummary`를 만든다(워커 수, 단계별 ms, 캘리브레이션, 캡처 시도 목록, dedup, drawElement 라우팅 필드, HDR 진단, 메모리 최고치, `tmpPeakBytes`, 관측 요약). `debug`면 `perf-summary.json`을 work에 쓰고 산출물 사본을 둔다. 각 단계는 `RenderObservabilityRecorder`가 시작, 체크포인트, 하트비트, 오류를 기록한다. 실패하면 `errorDetails`에 단계별 시간과 관측 요약, 브라우저 콘솔 끝 30줄이 들어간다. 이 기록은 렌더 결과를 바꾸지 않는다 | 코드 확인 |
| R-41 | CLI 호출 경계 | 로컬 렌더는 `executeRenderPlan`이 lint, 브라우저 준비, 해상도 사전 점검, 렌더 슬롯 획득을 마치고 `renderLocal` → `executeLocalRender`를 부른다. 거기서 `resolveConfig({browserGpuMode: options.browserGpuMode ?? "software", ...})`로 엔진 설정을 만들고 `browserGpuMode === "auto"`이고 `--resolution`이 없고 `PRODUCER_FORCE_SCREENSHOT`이 `true`가 아니면 `forceScreenshot: false`와 `beginFrameFirstFrameDeadlineMs: 20000`을 더한다. `createRenderRequest`와 `renderConfigFromRequest`로 `RenderConfig`를 만들고 `createRenderJob`, `executeRenderJob(job, projectDir, outputPath, onProgress, cancellation.signal, cancellation.checkAncestors)`를 부른다(`strictness`는 `--best-effort` 해제 시 `strict`). 취소 scope는 SIGINT 등 신호와 부모 프로세스 소멸을 abort 신호로 바꾸고 `checkAncestors`가 commit 직전의 `assertRenderActive`다. 오류는 `handleRenderError`가 `job.failedStage`와 함께 텔레메트리와 오류 상자로 처리하고 프로세스를 실패 종료한다. 성공하면 `job.outcome`, `job.warnings`(콘솔에 `[code] message`), `job.audioLoweredDb`(CLI가 `audio_lowered` 경고를 만듦), `job.perfSummary`를 읽는다. CLI 요청에는 `maxRenderMs`와 `strictVariables`가 실리지 않는다. 입구 전체는 행 8이다 | 코드 확인 |
| R-42 | HTTP 서버 호출 경계 | `POST /render`는 JSON 본문을 검사해 `createRenderRequest`로 job을 만들고(실패는 400) 렌더 슬롯(`PRODUCER_MAX_CONCURRENT_RENDERS`, 기본 2)을 얻은 뒤 abort 신호 없이 `executeRenderJob`을 부른다. 성공은 `{success:true, requestId, outputPath, outputToken, outputUrl, fileSize, durationMs, reference_background, videoDurationSeconds, outcome, warnings, perf, strictVariablesChecked(값이 있을 때)}`, 어떤 오류든 500과 `{success:false, error, errorCode?, errorOwner?, retryable?, errorMetadata?, stage, durationMs, errorDetails}`다. `POST /render/stream`은 SSE로 `queued`(슬롯이 없을 때 대기 위치), `progress`(30초 keepalive 포함), `complete`(위와 같은 필드에서 `durationMs`를 빼고 `type`, `producerVersion`을 더한 것), `cancelled`(`RenderCancelledError`), `error`를 보내고 요청 연결 종료를 `RenderCancelledError("request_aborted")`로 abort한다. 서버 본문의 `format`은 mp4, webm, mov만 받는다(그 밖은 `mp4`로 처리). `maxRenderMs`, `strictness`, `outputResolution`, `forceScreenshot` 등은 본문에서 받는다. 입출력 형태까지가 이 문서 범위다 | 코드 확인 |
| R-43 | 오류 코드 전달 | 서버는 오류 객체의 `code`가 허용 목록(`ASSET_MEDIA_TYPE_MISMATCH`, `HEIF_IMAGE_CONVERSION_FAILED`, `HEIF_TOOL_UNAVAILABLE`, `NOT_MEDIA_PAYLOAD`, `INVALID_VIDEO_METADATA`, `VIDEO_SOURCE_UNRENDERABLE`, `VIDEO_EXTRACTION_FAILED`, `ENCODER_INTERRUPTED`, `RENDER_TOO_SLOW`, `RENDER_STAGE_STALLED`, `PAGE_NEVER_READY`, `VARIABLES_INVALID`)에 있을 때만 `errorCode`로 싣고 메시지에서 코드를 유추하지 않는다. `owner`(user 또는 system)와 `retryable`(boolean), `publicMetadata`(평범한 객체)는 형이 맞을 때만 함께 싣는다. `RenderQualityError`, `RenderCancelledError`, `PlanValidationError`는 허용 목록에 없어 `errorCode` 없이 메시지만 간다 | 코드 확인 |
| R-44 | 분산 렌더 경계 | 같은 `RenderRequest`에서 `distributedConfigFromRequest`가 분산 설정을 만든다(gif, hls, `force-hdr`, chroma 444는 거부). CLI `--range`는 `executeRenderJob` 대신 `renderSpan`을 부른다. 분산 plan과 chunk 실행은 이 문서의 범위 밖이다 | 코드 확인 |
| R-45 | drawElement 워커 수 고정(router, inversion) | 병렬 router는 기본 켜짐(`HF_DE_PARALLEL_ROUTER=false`로 끔)이고 다음이 모두 참일 때 적격이다. `workers` 미지정, 자동으로 resolve한 워커 수가 2 이상, `cfg.useDrawElement`, compile gate 없음, `forceScreenshot` 없음, 형식이 mp4 또는 hls, `totalFrames >= HF_DE_PARALLEL_MIN_FRAMES`(기본 700, 0 이하면 끔), layered 또는 셰이더 전환 아님, 배율 1, probe 세션이 drawElement gate를 통과(screenshot 프레임을 남기지 않음), `PRODUCER_EXPERIMENTAL_FAST_CAPTURE`와 `HF_DE_PARALLEL_STREAM` 미설정, 병렬 streaming이 가능, 총 RAM이 `HF_DE_PARALLEL_MIN_MEM_MB`(기본 24576, 0 이하면 끔) 이상. 적격이면 probe 세션을 추가로 띄워 gate를 확인하고, 통과하면 워커를 3으로 고정하고 캘리브레이션을 건너뛴다. 단일 워커 inversion은 `HF_DE_SINGLE_MIN_FRAMES`가 기본 0이라 기본으로 꺼져 있고, 양수로 켜면 `totalFrames`가 그 값 이상이고 워커 수가 2 이상이고 비슷한 조건(단일 워커 streaming 가능, layered 아님, 배율 1, probe gate 통과, opt-in 없음)에서 워커를 1로 고정한다. 둘 다 `CapturePlan`의 `routing`에 실패 시 fallback 대상을 담는다(R-24) | 코드 확인 |
| R-46 | 오케스트레이터를 직접 부르는 그 밖의 호출자 | studio(`studioServer.ts:702-745`)는 `createRenderRequest` 검증 없이 `createRenderJob({fps, quality, format, gifLoop?, outputResolution, entryFile?, variables?, 인코더 옵션, useGpu?, pageMotionBlur?, allowOutsideProjectAssets, renderBodyScripts?})`로 job을 만들고 렌더 락을 얻은 뒤 `executeRenderJob(job, project.dir, outputPath, onProgress, abortSignal)`을 `assertRenderActive` 없이 부른다. `renderBodyScripts`는 `RenderConfig`에 필드가 없고 producer와 engine에서 읽는 곳이 없어 오케스트레이터에는 영향이 없다. benchmark(`cli/src/commands/benchmark.ts:131-137`)는 `createRenderJob({fps, quality, workers, allowOutsideProjectAssets})`와 `executeRenderJob(job, project.dir, outputPath)`만 부른다(진행, 취소 없음). 이 호출자들은 R-02의 검증을 거치지 않고 R-03의 사전 검증과 R-37의 오류 계약을 그대로 받는다 | 코드 확인 |

- 불변식: 이 파이프라인에서 호출자가 볼 수 있는 `job.progress`는 줄어들지 않는다. `outputPath`는 commit이 성공한 때만 바뀌고 실패나 취소에서는 호출 전 상태 그대로다(스테이징과 work 디렉터리는 성공, 실패, 취소 모두에서 정리 함수가 지운다. 예외는 `debug`와 `KEEP_TEMP=1`(R-04)과 segmented 캡처의 `projectDir/renders/.hf-segments/<planHash>`로, 이 디렉터리는 실패와 취소 뒤에도 `--resume`을 위해 남는다(R-17)). 전제는 정리 함수가 던지지 않고 프로세스가 강제 종료되지 않는 것이다. 강제 종료 시 남은 `.hf-transaction-*`와 work 디렉터리는 다음 렌더의 `createRenderWorkDir`가 소유 프로세스가 죽은 것을 확인해 지운다.
- 미결정: 없음. 처음 U-01(drawElement 적격 조건)은 R-45, U-02(워커 내부 재시도)는 R-20, U-03(디스크 부족 오류)은 R-22로 근거를 옮겨 닫았다.

- 확인 한계: 렌더를 실행하지 않았다. Chrome, FFmpeg가 필요한 동작(BeginFrame 실제 사용 여부, drawElement 선택, 재시도 사다리가 실제로 타는 경로)은 코드 읽기로만 확인했다. 엔진 `usableCpuCount`와 cgroup 한도 함수, `scaleProtocolTimeoutForComposition` 본문, `shouldUseLayeredComposite` 본문, 호스트 수명주기 신호 처리 세부는 열지 않았다.

### 1.5 필수 코드 참조 [필수]

라이선스는 overview 1절을 따른다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `packages/producer/src/services/renderOrchestrator.ts:355-366`, `790-841` `RenderStatus`, `RenderOutcome`, `RenderStageCode`, `RenderStageProgress`, `RenderJob`, `ProgressCallback` | 상태, 결과, 진행 코드 목록과 `RenderJob` 필드 | R-01, R-31, R-36, R-37 |
| C-02 | `packages/producer/src/services/renderOrchestrator.ts:1594-1611` `createRenderJob` | job 생성(검증 없음) | R-01 |
| C-03 | `packages/producer/src/services/renderOrchestrator.ts:843-939` `RenderQualityError`, `applyRenderWarningPolicy`, script 실패 hook들, `RenderCancelledError` | 경고 정책과 오류 클래스 | R-32, R-38, R-39 |
| C-04 | `packages/producer/src/services/render/shared.ts:261-431` `updateJobStatus`, `reportFrameProgress`, `reportExtractProgress`, `reportEncodeProgress`, `reportAssembleProgress` | progress 단조 증가, 250ms 간격, 구간 | R-36 |
| C-05 | `packages/producer/src/services/render/capturePlan.ts:179-309` `createCapturePlan`, `replanAfterFailure` | plan 종류 선택과 실패 뒤 전이 | R-15, R-24, R-25 |
| C-06 | `packages/producer/src/services/renderOrchestrator.ts:1643-1687` `explainStreamingEncodeGate`, `2869-2906` `shouldSegmentCapture`, `packages/producer/src/services/render/segmentPlan.ts:13-44` | streaming과 segmented 선택, 세그먼트 분할 | R-16, R-17 |
| C-07 | `packages/engine/src/services/parallelCoordinator.ts:152-187`, `335-454` `computeWorkerSizing`, `packages/producer/src/services/render/captureCost.ts:51-65`, `142-266` | 워커 수 계산과 캘리브레이션 배수 | R-18, R-19 |
| C-08 | `packages/engine/src/services/parallelCoordinator.ts:464-516`, `1072-1155` | 프레임 분배, 풀-치명 실패 판정, 첫 실패 abort | R-20 |
| C-09 | `packages/producer/src/services/renderOrchestrator.ts:1184-1237`, `1329-1592` | disk 병렬 재시도 사다리 | R-21 |
| C-10 | `packages/producer/src/services/renderOrchestrator.ts:2632-2735` `shouldRetryViaPinnedFallback`와 stall, encoder 사망 판별 | streaming 전체 재렌더 조건 | R-24 |
| C-11 | `packages/producer/src/services/render/artifactTransaction.ts:88-140`, `187-263`, `281-511` | 산출물 검증 기준과 commit, rollback | R-30 |
| C-12 | `packages/producer/src/services/render/renderEtaGuard.ts:1-124` | ETA 계산과 guard | R-33 |
| C-13 | `packages/producer/src/services/render/observability.ts:609-700`, `stallClock.ts:1-26`, `packages/producer/src/services/renderOrchestrator.ts:1243-1274` | stall 규칙 | R-34 |
| C-14 | `packages/producer/src/services/render/renderFormat.ts:1-20` | 형식별 알파와 H.264 파이프라인 구분 | R-15, R-28 |
| C-15 | `packages/producer/src/services/htmlCompiler.ts:402-472` `detectRenderModeHints` | screenshot 권장 이유 코드 4개 | R-06, 1.3.5 |
| C-16 | `packages/producer/src/services/render/stages/probeStage.ts:124-132`, `352-370` | `totalFrames` 계산과 probe 필요 조건 | R-08, R-09 |
| C-17 | `packages/producer/src/services/safeRenderErrorCode.ts:1-24` | 허용 오류 코드 목록 | R-43 |
| C-18 | `packages/producer/src/services/render/planValidation.ts:75-78`, `145-173` `validateRenderDuration` | 길이 범위 검증 | R-09 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출. 실제 렌더를 실행한 것이 아니다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | `createRenderJob({fps: 30, quality: "standard", format: "mp4"})` | `job.config.fps`는 `{num:30, den:1}`, `job.config.strictness`는 `"best-effort"`, `status`는 `queued`, `progress`는 0, `warnings`는 `[]` |
| T-02 | R-03 | `format: "hls"`, `useGpu: true`인 job으로 `executeRenderJob` | work 디렉터리 생성 없이 `[Render] format "hls" does not support GPU encoding...` `Error`를 던진다. `job.status`는 `queued`, `job.error`는 undefined, `onProgress` 호출 0회 |
| T-03 | R-38 | 캡처가 `media_readiness_timeout` 경고만 남기고 끝남. `strictness: "best-effort"` | 렌더가 성공하고 `job.outcome === "completed_with_warnings"`, `job.warnings[0].stage === "capture-readiness"`. 같은 입력에 `strictness: "strict"`이면 `RenderQualityError`가 던져지고 `status`는 `failed` |
| T-04 | R-39, R-38 | 컴포지션 스크립트 로드가 실패해 워커 세션 init 중 `sub_timeline_script_failure` 경고가 생김. `best-effort` | 워커 세션이 init하는 경로(다중 워커, probe를 재사용하지 않는 렌더)에서는 init 중에 `RenderQualityError`가 던져져 프레임을 잡기 전에 렌더가 `failed`로 끝난다. probe 세션을 재사용하는 단일 워커 렌더는 probe에 hook이 없어 캡처가 모두 끝난 뒤 정책(`5721-5725`)에서 `RenderQualityError`로 `failed`가 된다 |
| T-05 | R-32, R-04, R-30 | 캡처 도중 호출자가 `AbortController.abort()`. 이미 `outputPath`에 이전 렌더의 파일이 있음 | `RenderCancelledError`가 던져지고 `job.status === "cancelled"`, `job.outcome === "cancelled"`. 이전 `outputPath` 파일은 그대로이고 스테이징과 work 디렉터리는 없다 |
| T-06 | R-21 | 3 워커 disk 캡처, 워커 하나가 `Target closed`로 죽어 400프레임이 비고 나머지는 계속 진행됨 | 같은 워커 수(3)로 빠진 범위만 1회 다시 잡는다(`reason: "transient-retry"`). 그 재시도도 `Target closed`로 실패하고 진행이 있었으면 워커를 1로 줄여(`floor(3/2)`) 한 번 더 한다 |
| T-07 | R-24, R-14 | 로컬 Linux CLI(`browserGpuMode: auto`), 단일 워커 streaming, BeginFrame 첫 프레임이 20초 안에 안 그려짐 | `SequentialCaptureStallError`(또는 병렬이면 `ParallelCaptureStallError`)로 실패하고 `shouldRetryViaPinnedFallback`이 참(BeginFrame 캡처). `forceScreenshot: true` plan으로 전체를 한 번 다시 렌더한다 |
| T-08 | R-33, R-19 | `maxRenderMs: 60000`, `workers` 없음, 2000프레임, 캘리브레이션 중앙값 400ms, 워커 1 | 경과를 무시해도 ETA ≈ 800000ms가 120000ms를 넘어 캡처 전에 `RenderTooSlowError`(`render too slow: stage capture_calibration, 0/2000 frames, 400 ms/frame, ...`, `code: RENDER_TOO_SLOW`)가 던져진다. `status`는 `failed` |
| T-09 | R-30 | 10초, 30fps 산출물을 ffprobe가 9.9초로 보고 | 부족분 0.1초가 허용 `1/30 ≈ 0.033`초를 넘어 `Render artifact is truncated`를 던진다. 기존 `outputPath`는 그대로 |
| T-10 | R-11 | 비디오 소스 하나가 디코드 불가. 기본 설정 | 추출 체크포인트 기록 뒤 `VideoExtractionStageError`(`code`는 재시도 불가면 `VIDEO_SOURCE_UNRENDERABLE`)가 던져진다. `HF_VIDEO_EXTRACTION_FAILURE_MODE=observe`면 로그만 남기고 계속한다 |
| T-11 | R-13 | 오디오 mix가 실패(`audioError` 있음). `best-effort` | 프레임 캡처 전에 `RenderQualityError`(`audio_processing_failed`)가 던져진다. 영상만 있는 산출물로 끝나지 않는다 |
| T-12 | R-42 | `/render/stream`에 요청한 클라이언트가 중간에 연결을 끊음 | 서버가 `RenderCancelledError("request_aborted")`로 abort하고 렌더는 취소로 끝나며 SSE에는 `cancelled` 이벤트를 쓴다(연결이 이미 끊겼으면 전달은 못 한다) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-02, `packages/core/src/fps.ts:7-14` `toFps` | `toFps`는 숫자면 `{num, den:1}`을 만들고 객체는 그대로 돌려준다(검사 없음)를 읽었다. `engine/src/services/referenceBackground.ts:25-36`에서 `referenceBackgroundResult`가 `solid`(rgb), `none`, `unsupported_non_solid`만 그대로 받고 그 밖은 `{kind: "unknown"}`으로 만듦을 읽었다. 문서 차이: `docs/packages/producer.mdx`의 Reference background 절은 완료된 job이 `reference_background`를 노출한다고 쓰지만 구현은 `createRenderJob` 시점부터 `unknown`으로 필드를 둔다. T-01은 이 필드를 단언하지 않아 기대값이 깨지지 않는다 |
| R-02 | `packages/producer/src/renderRequest.ts:99-297`, `271-284`, 검색: `motionBlur`, `createRenderJob(` | `motionBlur`가 `RenderRequestOptions`에 없음은 `packages/producer/src`와 `packages/cli/src`(테스트 제외)에서 `motionBlur`를 검색해 요청 옵션 정의에 없고 `job.config.motionBlur`를 읽는 곳(`renderOrchestrator.ts:3629`, `3849`, `3872`, `4848`, `probeStage.ts:472`)만 있음을 확인했다. `createRenderJob(` 호출 검색(`grep -rn "createRenderJob(" --include=*.ts --include=*.tsx --include=*.mjs packages/*/src`, 테스트 제외)에서 요청 경로를 거치지 않는 호출자 `cli/src/server/studioServer.ts:702`, `cli/src/commands/benchmark.ts:131`, `producer/src/benchmark.ts:214`, `producer/src/regression-harness.ts:1169`, `producer/src/services/distributed/shared.ts:481`을 찾았고 이들이 `motionBlur`를 넘기는지는 열어 보지 않았다 |
| R-03 | `renderOrchestrator.ts:3082-3099`, `3195-3202`, `3264`, `hlsConfig.ts:36-69`, `deliveryEncoder.ts:46-65`, `chromaSubsampling.ts:16-57`, `3172` | 검증기 세 개의 호출이 `try` 시작(`3110`)과 `RenderExecutionContext` 생성(`3094`) 앞에 있음을 읽었다. 이 위치에서 던지면 `updateJobStatus`가 불리지 않는다는 것은 코드 구조로 확인했고 실행하지 않았다 |
| R-04 | `renderOrchestrator.ts:3085-3108`, `1188-1196`, `3055-3060`, `3247-3262`, `4507-4519`, `render/renderDirOwner.ts:145-156`, `render/renderExecutionContext.ts:41-111` | `deadlineAtMs`가 쓰이지 않음은 `grep -rn deadlineAtMs --include=*.ts --include=*.mjs --include=*.js */src`(packages 하위, SHA 5979991)로 확인했다. `producer`에서는 `renderExecutionContext.ts`에 정의만 있고 호출하는 곳이 없다. `engine`의 `deadlineAtMs`는 ChildProcess 옵션으로 별개다. `renderDirOwner.ts:98-155`(`isAbandoned`, `listAbandonedRenderDirs`, `createRenderWorkDir`)에서 확인했다. 소유 기록을 쓰는 `pidScope`와 `ownerState` 세부는 열지 않았다 |
| R-05 | `renderOrchestrator.ts:3312-3335`, `3478-3528`, `3608-3678`, `3720-3772`, `3786-3843`, `4296-4506`, `4826-4866`, `4937-4971`, `5740-5780`, `5880-5886` | 호출 순서를 줄 순서로 읽었다. `status` 문자열은 `updateJobStatus` 호출에서 확인했다 |
| R-06 | `render/stages/compileStage.ts:174-214`, `235-439`(셰이더 gate와 page-side 복원은 `339-360`), `render/shared.ts:159-221` | 코드 확인. 컴파일 안쪽은 composition-contract가 소유하므로 열지 않았다 |
| R-07 | `render/stages/compileStage.ts:150-167`, `174-209`, `render/shared.ts:126-151`, `renderOrchestrator.ts:3305-3309` | 코드 확인. `checkOutputResolutionCompatibility`의 세부 조건은 core 몫이라 열지 않았다 |
| R-08 | C-16, `render/stages/probeStage.ts:387-611`, `619-660` | 코드 확인. `discoverMediaFromBrowser`와 미디어 합치기(`661-880`)는 이름만 확인했다 |
| R-09 | C-16, C-18, `render/stages/probeStage.ts:900-950`, `renderOrchestrator.ts:3520-3528` | 코드 확인 |
| R-10 | `renderOrchestrator.ts:3786-3809`, `4690-4749`, `5736-5738`, `compileStage.ts:340-358`, `probeStage.ts:458-465`, `services/fileServer.ts:798-876`, `985-990` | 주입 스크립트 조립은 `fileServer.ts:813-820`에서 읽었다. 스크립트 내용은 capture-encode-engine 소유 |
| R-11 | `render/stages/extractVideosStage.ts:204-226`, `274-295`, `378-392`, `422-640`, `render/videoFrameCoverage.ts:88-134`, `236-258`, `renderOrchestrator.ts:3680-3718`, `render/shared.ts:717-749` | 코드 확인. HDR 사전 probe(`461-584`)와 `appendAutoDetectedVideoAudio` 본문은 이름과 위치만 확인했다 |
| R-12 | `renderOrchestrator.ts:3720-3741`, `4001-4018`, `4750-4757`, `render/capturePlan.ts:191-198`, `packages/producer/src/services/hdrCompositor.ts:458-464` | 개념만 확인했다. `captureHdr*.ts`와 `resolveEffectiveHdrMode` 본문은 읽지 않았다 |
| R-13 | `renderOrchestrator.ts:3743-3772`, `render/stages/audioStage.ts:90-101`, `146-170`, `4937-4971`, `5887-5888`, `render/stages/audioStage.ts:195-290`, `render/stages/assembleStage.ts:61-69`, audio-mix-fx R-10, R-30 | 코드 확인. `recordLimiterAttenuation`은 `assembleStage.ts`에 정의되고 오케스트레이터(`4940`)와 assemble 단계(`129`)가 부른다. `audioLoweredDb`의 의미는 audio-mix-fx R-19이다. `audio_lowered` 경고 생성은 `packages/cli/src/utils/audioLoweredWarning.ts`와 `render.ts:1301`이다(검색: `audio_lowered`, `audioLoweredDb`, packages 하위) |
| R-14 | 1.3.5 표의 위치들. `renderOrchestrator.ts:3349`, `3405`, `3547-3550`, `3835-3843`, `5342-5433`, `5612-5625`, `render/capturePlan.ts:183`, `235`, `255`, `303` | 부재 주장("disk와 HDR 경로에 BeginFrame 실패를 screenshot으로 낮추는 전체 재렌더가 없다")의 검색: `grep -rn forceScreenshot --include=*.ts packages/producer/src`(테스트 제외). 쓰기 지점은 위 표의 곳뿐이다. disk 경로의 `catch`(`5613-5625`)는 drawElement 오류만 처리한다. 읽지 않은 `distributed/*`는 제외했다. 구현의 stale 주석: `captureCost.ts:528-533`의 주석은 `shouldFallbackToScreenshotAfterCalibrationError`를 시퀀서가 disk 캡처 재시도 루프에서도 부른다고 쓰지만 `grep -rn shouldFallbackToScreenshotAfterCalibrationError packages/producer/src`(테스트 제외)의 호출은 `captureCost.ts:453` 한 곳뿐이다. 코드 쪽이 사실이다 |
| R-15 | C-05, C-14, `renderOrchestrator.ts:2801-2813`, `2828-2849`(코드 주석은 "mp4/mov"라고 쓰지만 판정은 `outputUsesH264Pipeline`이라 mov를 포함하지 않는다. 구현이 사실), `2923-2973`, `4526-4635`, `4750-4757` | 코드 확인. 로그 `streaming-encode gate` 후의 plan 생성만 읽었다 |
| R-16 | C-06, `packages/engine/src/config.ts:608-660`, `1109` | 코드 확인. `streamingEncodeMaxDurationSeconds` 기본 240초는 capture-encode-engine 1.3.3 표. win32 복합 자동 비활성화 조건은 `shouldAutoDisableStreamingEncodeOnWin32Compound`(`640-664`)를 읽었고 호출부(`1109`)의 인자 구성은 열지 않았다 |
| R-17 | C-06, `renderOrchestrator.ts:5048-5110`, `2874-2879`, `render/segmentPlan.ts:1-44`, `render/segmentManifest.ts:88-90` | 코드 확인. 기본이 꺼진 근거는 `DEFAULT_SEGMENTED_MIN_SECONDS = Number.POSITIVE_INFINITY`(`2872`). `computeSegmentPlanHash`, `readSegmentManifest`, `concat` 본문은 열지 않았다 |
| R-18 | C-07, `renderOrchestrator.ts:3417-3439`, `4395-4455` | 코드 확인. `usableCpuCount`와 `getCgroupCpuLimit` 본문은 열지 않았다. 숫자 상수는 `parallelCoordinator.ts:152-195`(Apple disk와 desktop 변형 포함)와 `config.ts:294-297`(`coresPerWorker` 2.5, `minParallelFrames` 120, `largeRenderThreshold` 1000) |
| R-19 | C-07, `renderOrchestrator.ts:4296-4373`, `render/captureCost.ts:368-520`, `534-539` | 코드 확인 |
| R-20 | C-08, `packages/engine/src/services/parallelCoordinator.ts:1157-1304`, `render/stages/captureStreamingStage.ts:813-866` | 코드 확인. `executeWorkerTask`는 `parallelCoordinator.ts:893-1040`, `resolveParallelWorkerTimeoutMs`는 `594-600`, `isFatalCaptureFailure`는 `captureFailure.ts:219-221`에서 읽었다. producer의 `services/parallelCoordinator.ts`는 14줄 re-export다(`calculateOptimalWorkers`, `distributeFrames`, `executeParallelCapture`, `mergeWorkerFrames`, `getSystemResources`와 타입). 검색: `grep -rn "function executeParallelCapture\|function distributeFrames" --include=*.ts */src`로 구현은 engine 한 곳. 오케스트레이터는 re-export를 거치지 않고 `@hyperframes/engine`에서 직접 import한다(`renderOrchestrator.ts:88-93`). |
| R-21 | C-09, `render/stages/captureStage.ts:145-150`, `370-440` | 코드 확인 |
| R-22 | `render/stages/captureStage.ts:153-206`, `242-301`, `449-582`, `renderOrchestrator.ts:5430` | 코드 확인. `diskCaptureShortfallError`와 `inspectDiskCaptureHeadroom`의 호출처를 `grep -rn "diskCaptureShortfallError(\|inspectDiskCaptureHeadroom(" packages/producer/src`(테스트 제외)로 찾아 위 둘뿐임을 확인했다 |
| R-23 | `render/stages/captureStreamingStage.ts:100`, `126-170`, `726-745`, `782-866`, `990-1040`, `1210-1225`, `renderOrchestrator.ts:5499-5538`, `cli/src/commands/render.ts:714`, `1181` | 코드 확인. 20초 한도가 CLI만의 값임은 `grep -rni "beginFrameFirstFrame" packages/*/src`와 `grep -rni "FIRST_FRAME_DEADLINE" packages/*/src`(테스트 제외)로 확인했다. 정의는 `engine/src/config.ts`의 선택 필드이고 값을 넣는 곳은 `render.ts:1181`뿐이다. 따라서 사용자가 알려준 "20초"는 CLI auto 경로에만 해당한다 |
| R-24 | C-10, C-05, `renderOrchestrator.ts:5340-5488`, `1204-1210` | 코드 확인. 사용자가 알려준 `renderOrchestrator.ts:5405-5420`은 같은 `catch` 안의 로그 메시지와 체크포인트 문구이고 실제 판정은 `5358-5376`(`shouldRetryViaPinnedFallback`), plan 전이는 `5426-5433`과 `capturePlan.ts:244-309`다. 판정 조건 중 `isTransientCaptureError`는 `isTransientBrowserError`(engine, capture-encode-engine R-48)에 의존한다 |
| R-25 | `renderOrchestrator.ts:5168-5232`, `5610-5679`, `5257-5274`, `render/capturePlan.ts:220-261` | 코드 확인 |
| R-26 | `render/stages/captureSegmentedStage.ts:504-586`, `render/segmentRecycle.ts:1-32`, `render/segmentQueue.ts:1-22` | 코드 확인. 세그먼트 병렬 워커 수가 2 이상일 때의 분배와 concat 세부는 열지 않았다 |
| R-27 | `renderOrchestrator.ts:3441-3464`, capture-encode-engine R-18 | 코드 확인. `scaleProtocolTimeoutForComposition` 본문은 열지 않았다(위 스펙이 `config.ts:589`로 소유) |
| R-28 | `renderOrchestrator.ts:5540-5707`, `render/stages/encodeStage.ts:299-314`, `453-540`, `render/renderFormat.ts`, `renderOrchestrator.ts:4666-4683` | 코드 확인. gif 팔레트 인자(`gifEncodeArgs.ts`), 청크 인코딩 내부, `encodeWhileCapturing` 내부는 열지 않았다 |
| R-29 | C-14, `render/stages/assembleStage.ts:84-193`, `renderOrchestrator.ts:5740-5769` | 코드 확인. `padOrTrimAudioToVideoFrameCount`(`audioPadTrim.ts`) 내부는 audio-mix-fx가 assemble 소관으로 남긴 것인데 이 스펙도 열지 않았다. `packageHls` 내부는 capture-encode-engine 소유 |
| R-30 | C-11, `artifactTransaction.ts:388-404`, `424-430`, `docs/packages/producer.mdx:109-120`, `renderOrchestrator.ts:3195-3202`, `5771-5780`, `render/renderDirOwner.ts:145-156` | 코드 확인. `defaultArtifactDurationProbe`(ffprobe 호출)의 실행은 확인하지 않았다 |
| R-31 | `renderOrchestrator.ts:5782-5886` | 코드 확인 |
| R-32 | `renderOrchestrator.ts:929-939`, `3264-3272`, `5887-5902`, `render/renderExecutionContext.ts:82-84`, `server.ts:1000-1002`, `cli/src/utils/renderCancellation.ts:108-160` | "timeout reason을 만드는 곳이 없다"의 검색: `grep -rn "RenderCancelledError(" --include=*.ts --include=*.mjs --include=*.js */src`(테스트 제외). 생성 지점은 `server.ts:1001`, `distributed/renderSpan.ts:49`(`user_cancelled`), `renderOrchestrator.ts:3267`, `5901`뿐이다. 동적 생성이나 `studio`, `player` 같은 다른 소비자는 찾지 않았다 |
| R-33 | C-12, `renderOrchestrator.ts:3149-3154`, `4499-4519`, `5894-5902`, `server.ts:351` | 코드 확인. `RenderTooSlowError`가 `index.ts`에서 내보내지지 않음은 `grep -rn RenderTooSlowError --include=*.ts */src`(테스트 제외)에서 export가 정의 파일뿐인 것으로 확인했다. CLI가 `maxRenderMs`와 `strictVariables`를 요청에 안 싣는 것은 `packages/cli/src`(테스트 제외)에서 `maxRenderMs`를 찾지 못했고 `strictVariables`는 `render/plan.ts:690`, `execute.ts:88`, `156`(검사와 배치)에만 있어 `render.ts`의 `createRenderRequest` 옵션(`1195-1223`)에 없음으로 확인했다. Docker 경로나 다른 진입(studio 서버 등)은 보지 않았다 |
| R-34 | C-13, `renderOrchestrator.ts:1243-1274`, `5031`, `5608`, `render/shared.ts:439-448`, `render/stages/captureStreamingStage.ts:100`, `1015-1030` | 코드 확인. 한도 숫자는 `1243-1247`(300000, 2배 계수, 900000)과 `captureStreamingStage.ts:100`(60000) |
| R-35 | `render/pageNeverReady.ts:1-32`, `renderOrchestrator.ts:5889-5894`, `render/captureCost.ts` `isEvaluateTimeout` | 코드 확인 |
| R-36 | C-04, `render/renderEventPublisher.ts:1-72`, `render/renderExecutionContext.ts:52-111`, `render/stages/captureStage.ts:391-408`, `captureStreamingStage.ts:619`, `648`, `981` | 코드 확인. 진행 구간 숫자는 호출 인자(`25 + 비율 × 45` disk, `× 55` streaming, segmented, HDR 순차)에서 읽었다 |
| R-37 | `renderOrchestrator.ts:5887-6038`, `render/renderEventPublisher.ts:56-72`, `render/cleanup.ts:1-40`, `3267` | 코드 확인. `cleanup.ts`는 이름과 달리 정리 로직이 아니고 `errorDetails` 빌더다 |
| R-38 | C-03, `renderOrchestrator.ts:4953-4971`, `5721-5725`, `3937` | 코드 확인. 경고 코드의 의미는 capture-encode-engine R-50 |
| R-39 | C-03(`906-927`), `renderOrchestrator.ts:3936-3937`, `4338`, `5020`, `5145`, `5321`, `probeStage.ts:473-493` | 코드 확인. probe 옵션에 hook이 없음은 `probeStage.ts:473-493`의 `captureOpts` 필드 목록으로 확인했다 |
| R-40 | `renderOrchestrator.ts:5782-5870`, `render/perfSummary.ts`(이름만) | `buildRenderPerfSummary`와 `RenderObservabilityRecorder` 내부는 열지 않았다 |
| R-41 | `cli/src/commands/render.ts:1154-1260`, `1261-1346`, `1923-1977`, `cli/src/commands/render/execute.ts:70-151`, `cli/src/utils/renderCancellation.ts:108-160` | 코드 확인. 사용자가 알려준 `render.ts:1172-1183`을 확인했다. `plan.ts`와 `execute.ts` 자체는 오케스트레이터를 부르지 않고 `renderLocal`(`render.ts:1012-1024`)을 거친다 |
| R-42 | `server.ts:158-184`, `341-372`, `880-974`, `976-1065`, `748-794`, `208-218`, `813-826` | 코드 확인. 라우트 등록은 `1214-1219`. 인증과 CORS, `confineRequests` 정책은 읽지 않았다 |
| R-43 | C-17, `server.ts:158-184`, `render/renderEtaGuard.ts:21-39`, `render/pageNeverReady.ts:6-21`, `render/stages/extractVideosStage.ts:238-272` | 코드 확인 |
| R-44 | `renderRequest.ts:299-360`, `cli/src/commands/render.ts:1225-1238`, `1348-1380` | 한 줄만 확인했다 |
| R-45 | `renderOrchestrator.ts:2297-2380`, `2481-2560`, `4105-4244`, `4395-4455` | 코드 확인. 적격 조건은 `shouldPreferParallelDrawElement`(`2494-2548`)를 읽었고 `HF_DE_PARALLEL_MIN_FRAMES`, `HF_DE_PARALLEL_MIN_MEM_MB`, `HF_DE_PARALLEL_ROUTER`의 기본값은 `4139-4180`에서 확인했다. inversion은 `resolveDeSingleMinFrames`(`2306-2310`)의 기본 0과 `shouldPreferSingleWorkerDrawElement`(`2327-2376`)를 읽었다. probe 세션을 추가로 띄우는 gate 확인(`4182-4244`)은 흐름만 읽었다 |
| R-46 | `cli/src/server/studioServer.ts:689-745`, `cli/src/commands/benchmark.ts:125-140`, `renderOrchestrator.ts:1594-1611` | 코드 확인. `renderBodyScripts`가 읽히지 않음은 `grep -rn renderBodyScripts --include=*.ts packages/producer/src packages/engine/src`(테스트 제외) 결과가 없음으로 확인했다. 생성 쪽(`cli/src/server/*`의 `createStudioManualEditsRenderBodyScript`)은 열지 않았다. 호출자 목록의 검색은 R-02 행 참조 |
| T-01 | R-01 | 구현에서 도출 |
| T-02 | R-03 | 구현에서 도출 |
| T-03 | R-38 | 구현에서 도출 |
| T-04 | R-39 | 구현에서 도출 |
| T-05 | R-32 | 구현에서 도출 |
| T-06 | R-21 | 구현에서 도출(`captureAttempts` 기록의 `reason` 값은 `renderOrchestrator.ts:1376`) |
| T-07 | R-24 | 구현에서 도출 |
| T-08 | R-33 | 구현에서 도출. 계산식은 `render/renderEtaGuard.ts:46-50`, `66` |
| T-09 | R-30 | 구현에서 도출. 계산식은 `artifactTransaction.ts:187-191`, `216-223` |
| T-10 | R-11 | 구현에서 도출 |
| T-11 | R-13 | 구현에서 도출 |
| T-12 | R-42 | 구현에서 도출 |

### 2.2 코드 읽는 순서 [선택]

1. `renderOrchestrator.ts:3072-3124` `executeRenderJob`(껍데기)과 `3126-3262`(자원, 정리 등록)를 읽는다.
2. `3312-3772`로 compile, probe, extract, audio 시작까지 따라간다. 단계 안쪽은 `render/stages/*.ts`를 필요할 때 연다.
3. `4296-4866`에서 캘리브레이션, 워커 수, 캡처 plan을 정한다. 이 구간은 telemetry 코드가 많아서 `capturePlan.ts`와 `captureCost.ts`를 먼저 읽고 돌아오면 쉽다.
4. `4937-5707`이 캡처 분기(hdr_layered, segmented, streaming, disk)와 각 복구다.
5. `5721-6038`이 조립, 검증, commit과 실패 경로다.

파일 구조는 `renderOrchestrator.ts`(순서, 자원, 복구)와 `render/stages/*`(단계 함수)와 `render/*.ts`(순수 판정, 정책, 트랜잭션)로 나뉜다. 단계 함수들은 `renderOrchestrator.ts`를 import하지 않으려고 `render/shared.ts`에 공용 타입과 진행 보고 함수를 둔다.

### 2.4 검토 기록 [필수, ready 스펙]

`draft` 스펙이라 해당 없음. 메인 세션의 원본 대조 점검 뒤 채운다.

## 적용 메모 [선택]

없음.
