---
sha: "5979991d5f0af542fbb02ba906bdba4de52b2b64"
created: 2026-10-20
updated: 2026-11-17
---

# hyperframes Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/heygen-com/hyperframes`
- **기준 SHA**: `5979991d` (2026-11-17), 버전 0.9.59 (`packages/cli/package.json`, `packages/core/package.json`). 이전 기준 `b7fa007`(0.8.181)에서 1,634 commit 진행(`git rev-list --count`).
- **작업트리 상태**: Clean
- **분석 목적**: 학습 (주요 기능 파악). 스펙을 어디에 쓸지는 미정
- **분석 대상 제품**: 모노레포 루트(npm `hyperframes` CLI + `packages/` 16개), 문서 사이트(`docs/`), 레지스트리(`registry/`), 스킬(`skills/`)
- **스펙 범위**: 2026-11-17 승인, feature map 행 1~8. 제외: 9~12·14~16(범위 밖, 미작성), 13(참고용 — 사용자 결정), 17·18(부속 — 기본 제외). `frame.md`는 참고용. 작성은 wave 1(행 1) → 2(행 2·6·7) → 3(행 3·4) → 4(행 5) → 5(행 8) 순
- **언어/규모**: TypeScript 모노레포(bun workspaces, Node ≥22, FFmpeg 필요), 추적 파일 10,350개(`git ls-files`). 아래 줄 수는 `b7fa007` 시점 값이라 재측정 전. 테스트 제외 TS 줄 수: cli 8.3만, studio 16.4만, core 5.5만, producer 4.0만, engine 3.2만. Apache-2.0(루트 `LICENSE` 확인, `packages/share/src/sources/contract/LICENSE-Unicode.txt`가 별도 존재).

---

## 2. 프로젝트 개요

HTML·CSS·미디어·"seek 가능한 애니메이션"을 **결정적(deterministic) MP4**로 렌더하는 프레임워크다. 사람은 CLI로, AI 코딩 에이전트는 스킬/플러그인으로 쓰는 것이 전제다. (출처: README "Write HTML. Render video. Built for agents.")

핵심 아이디어: 영상을 재생해서 녹화하지 않고, **프레임 번호 N → 시각 t = N/fps → 모든 애니메이션을 t로 seek → 한 프레임 캡처**를 반복한다. 벽시계·무시드 랜덤·렌더 중 fetch를 금지해 같은 입력이 같은 영상을 낸다. (출처: `docs/concepts/determinism.mdx`)

### Feature map

세밀도: 목적이 "학습(주요 기능 파악)"이라 렌더 핵심 경로(컴포지션 계약 → 런타임 seek → 캡처·인코딩 → 오케스트레이션)는 행을 나누고, 호스팅·분산·미디어 도구는 패밀리 한 행으로 묶었다. 이 표는 `5979991`에서 파일 목록·`export` 심볼·`cli.ts` 등록부를 대조해 만들었고, 본문 흐름은 열지 않았다. 그래서 검증 수준은 대부분 `코드 확인(진입점·심볼 존재)`이며 동작은 `추론`이다.

| # | 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|---|
| 1 | 컴포지션 계약·컴파일 | 컴포지션(영상 한 편 또는 한 장면을 설명하는 HTML 파일. 바깥 요소에 `data-composition-id`)의 계약을 다룬다. HTML + `data-start`/`data-duration`/`data-track-index`/`class="clip"`을 파싱하고, 서브 컴포지션 인라인·경로 재작성·타이밍 해석(`data-start="intro - 0.5"`처럼 다른 클립 id 참조 포함)을 거쳐 렌더 가능한 HTML로 만든다. 렌더·캡처는 포함하지 않음 | `packages/producer/src/services/htmlCompiler.ts` `compileForRender`(렌더 경로의 실제 컴파일러, 2207행), `packages/core/src/compiler/htmlBundler.ts` `bundleToSingleHtml`(프리뷰·린트·validate·layout·inspector 입구), `timingCompiler.ts`, `inlineSubCompositions.ts`, `compositionAssembly.ts`, `packages/parsers/src/compositionContract.ts`·`referenceResolver.ts`, `docs/concepts/data-attributes.mdx`. `core/compiler/timingResolver.ts`는 파일 주석에 "NOT YET WIRED"이고 `resolveTimings`는 re-export뿐이라 이 행에서 제외 | 없음 | 핵심 | [composition-contract](capabilities/composition-contract.md) · ready | 코드 확인(파일 존재), 동작 추론 |
| 2 | 런타임·타임라인 seek | 페이지 안에서 `window.__timelines`·클립 창(clipWindow)·미디어 클럭을 t로 seek하는 브라우저 런타임. 부모(Studio·렌더러)가 `postMessage`(`hf-parent` control: play·pause·seek 등)로 제어하고, 프리뷰 재생과 렌더 캡처가 같은 런타임을 쓴다(`runtime/README.md` 확인, `init.ts` 본문 미열람) | `packages/core/src/runtime/entry.ts`, `init.ts`(6.9천 줄), `timeline.ts`, `clipTree.ts`, `clipWindow.ts`, `protocol.ts` | 1 | 핵심 | [runtime-seek](capabilities/runtime-seek.md) · ready | 코드 확인(파일 존재), 동작 추론 |
| 3 | 런타임 어댑터 패밀리 | 애니메이션 방식(GSAP·CSS·WAAPI·Anime.js·Lottie·Three.js·TypeGPU·D3·Leaflet·Mapbox·MapLibre·Google Maps)마다 "t초 상태로 정지"시키는 방법이 달라서, 방식별로 `discover`·`seek({time})`·`pause`를 구현한 변환 코드. 2번 런타임이 호출한다. `frame-source` 어댑터(`runtime/frameSources.ts`, `adapters/` 폴더 밖에 있지만 13개 어댑터 중 하나이고 공개 등록 API `window.__hyperframes.registerFrameSource`를 가진다)와 `video-texture-compat.ts`(어댑터가 아니라 GPU 업로드 패치)를 포함한다. 직접 만든 호스트용 공개 인터페이스 `FrameAdapter`(`getDurationFrames`·`seekFrame`·`destroy`, 문서상 experimental v0)는 이 런타임 어댑터와 다른 타입이며 `core/src/runtime`이 참조하지 않는다. 2번과 합칠지는 본문을 읽고 정한다 | `packages/core/src/runtime/types.ts` `RuntimeDeterministicAdapter`(412행), `packages/core/src/runtime/adapters/*.ts`, `packages/core/src/adapters/types.ts` `FrameAdapter`, `docs/concepts/frame-adapters.mdx` | 2 | 핵심 | [runtime-adapters](capabilities/runtime-adapters.md) · draft | 코드 확인(두 타입 정의·분리), 어댑터 공통 규칙 미확인 |
| 4 | 프레임 캡처·인코딩 엔진 | URL/HTML을 Chrome(Puppeteer)으로 열어 프레임마다 seek 후 캡처(BeginFrame, screenshot fallback, drawElement 경로)하고 FFmpeg로 인코딩. 비디오 프레임 추출·HDR 포함 | `packages/engine/src/services/frameCapture.ts`(6.3천 줄), `browserManager.ts`, `streamingEncoder.ts`, `chunkEncoder.ts`, `videoFrameExtractor.ts`, `drawElementService.ts`, `hdrCapture.ts`, 캡처 페이지 주입 스크립트 `packages/producer/src/services/fileServer.ts`(`HF_EARLY_STUB`, `RENDER_CAPTURE_MODE_SHIM`, `VIRTUAL_TIME_SHIM`, `buildRenderModeScript`, `HF_BRIDGE_SCRIPT`)와 `packages/producer/stubs/hf-early-stub.ts`. producer의 `frameCapture.ts`·`browserManager.ts`·`chunkEncoder.ts`는 engine re-export, `fileServer.ts`는 engine(217줄)과 producer(1005줄)가 서로 다른 구현이고 렌더는 producer 것을 쓴다 | 2 | 핵심 | [capture-encode-engine](capabilities/capture-encode-engine.md) · draft | 코드 확인(파일·호출 존재), 실행 미확인 |
| 5 | 렌더 오케스트레이션 | 컴파일 → probe → 비디오 추출 → 캡처(스트리밍/세그먼트/HDR) → 오디오 → 인코딩 → 조립 단계를 돌리고 워커 병렬·재시도·취소·진행 이벤트를 관리. 로컬 렌더 파이프라인 | `packages/producer/src/services/renderOrchestrator.ts` `createRenderJob`(1596행)·`executeRenderJob`(3072행), `render/stages/*`, `parallelCoordinator.ts`, `packages/producer/src/server.ts` | 1, 4, 6 | 핵심 | [render-orchestration](capabilities/render-orchestration.md) · draft | 코드 확인(심볼·단계 파일), 흐름 추론 |
| 6 | 오디오 믹싱·효과 | 클립 오디오 믹스, 페이드·게인·볼륨 곡선, 보이스 카브(덕킹), EQ·컴프·리버브 효과 체인, 서브믹스 그룹, 렌더 믹스의 true-peak 한도. 렌더는 Studio가 작성 시점에 만든 `data-fx-chain`·`data-automation`만 읽고 카브·leveller 분석 알고리즘은 렌더에 없다(스펙 R-25). 렌더에 LUFS 정규화는 없고 CLI `normalize-audio`의 몫 | `packages/core/src/audio*.ts`(`audioFx.ts`, `audioCarve.ts`, `audioGroups.ts`), `packages/engine/src/services/audioMixer.ts`, `audioFxRender.ts`, `packages/producer/src/services/render/stages/audioStage.ts` | 1 | 핵심 | [audio-mix-fx](capabilities/audio-mix-fx.md) · ready | 코드 확인(파일 존재), 동작 추론 |
| 7 | 린트·검증 | 컴포지션 규칙 검사(규칙 파일 14종: core·composition·gsap·media·captions·shaders 등), 렌더 차단 판정. 렌더를 막는 호출은 producer가 아니라 CLI `commands/render/execute.ts`의 `runRenderLint`이고, producer는 `POST /lint` 서비스·worker만 제공한다. `lint`·`check`·`validate`가 린트 결과를 쓰고 `layout`·contrast 감사는 브라우저 측정이라 린트 결과를 쓰지 않는다 | `packages/lint/src/hyperframeLinter.ts` `lintHyperframeHtml`, `project.ts` `lintProject`, `shouldBlockRender.ts`, `rules/*.ts`, `packages/cli/src/commands/{lint,check,validate,layout,contrast-*}.ts` | 1 | 핵심 | [lint-check](capabilities/lint-check.md) · draft | 코드 확인(심볼 위치), 규칙 내용 미확인 |
| 8 | CLI 명령 입구·새 프로젝트 생성 | `npx hyperframes <cmd>`로 `cli.ts`가 명령 56개(`cli.ts:143-204` 등록부, 키를 세어 확인)를 해당 명령 파일로 넘긴다(lazy import). `init`은 새 프로젝트 폴더와 시작 파일을 만든다(`--example`·`--resolution`·`--video` 옵션). `render`(plan→execute), `doctor`, `info`, `docs` 등 | `packages/cli/src/cli.ts`(145~202행 등록부), `commands/{init,render}.ts`, `commands/render/{plan,execute}.ts`(둘 다 오케스트레이터를 직접 부르지 않는다. 실제 호출은 `execute.ts:148`이 `plan.useDocker ? renderDocker : renderLocal`로 고른 `renderLocal`(`render.ts`가 주입)을 거쳐 `commands/render.ts:1012-1260`의 `executeLocalRender`가 한다), `templates/` | 5, 7 | 핵심 | [cli-entry-init](capabilities/cli-entry-init.md) · draft | 코드 확인(등록부 대조) |
| 9 | Studio·preview | `hyperframes preview`가 띄우는 컴포지션을 편집하는 로컬 웹 UI(타임라인·미리보기·파일·썸네일·waveform·히스토리 API). studio는 React 앱, studio-server는 Hono API | `packages/studio/src/App.tsx`, `packages/studio-server/src/createStudioApi.ts`, `routes/*.ts`, `packages/cli/src/commands/preview.ts` | 2, 10 | 핵심 | `capabilities/studio-preview.md` · 미작성 | 코드 확인(파일 존재), 동작 미확인 |
| 10 | 편집 엔진·인스펙터 | 컴포지션을 헤드리스로 편집(문서 mutate, history, persist queue)하고 렌더된 페이지를 검사(인스펙터). README 기준 용도는 편집 전에 지정 요소(`selector`·`hfId`)의 원본 HTML/CSS/GSAP 위치·맥락을 찾아 주는 것(`POST /inspect`, 모호하면 후보 반환, seek·캡처·렌더 안 함). Studio·에이전트가 공유하는지는 미확인 | `packages/sdk/src/session.ts`, `engine/mutate.ts`, `history.ts`, `packages/inspector/src/service.ts`, `packages/core/src/editing/`, `runtime/editing*.ts` | 1, 2 | 핵심 | `capabilities/editing-engine.md` · 미작성 | 코드 확인(파일 존재), 추론 |
| 11 | Player·slideshow·present | 결과물이 MP4가 아닌 쪽. `<hyperframes-player>`는 컴포지션을 웹페이지에 끼워 재생·seek하는 웹 컴포넌트, 슬라이드쇼는 JSON(`application/hyperframes-slideshow+json`)으로 슬라이드 순서·노트를 정한 컴포지션, `hyperframes present`는 그 덱을 로컬 서버로 띄워 발표자 모드로 여는 명령(청중 동기화 언급) | `packages/player/src/hyperframes-player.ts`(`customElements.define`, 1682행), `packages/core/src/slideshow/index.ts`, `commands/present.ts`, `skills/slideshow/` | 2 | 핵심 | `capabilities/player-slideshow.md` · 미작성 | 코드 확인(정의 위치), 동작 추론 |
| 12 | 색보정·VFX·셰이더 전환 | 컬러 그레이딩(LUT·곡선·bake), fractal noise·displacement 등 VFX 프래그먼트, WebGL 셰이더 전환 패키지 | `packages/core/src/colorGrading*.ts`, `colorLuts.ts`, `vfx.ts`, `vfx/*.frag.ts`, `packages/shader-transitions`, `commands/grade-compare.ts` | 2, 4 | 핵심 | `capabilities/grade-vfx-shaders.md` · 미작성 | 코드 확인(파일 존재), 추론 |
| 13 | 레지스트리·카탈로그 (참고용, 스펙 제외) | 미리 만든 영상 효과 소스 모음(전환·오버레이·제목·차트·지도·3D 등)인 블록 210개·컴포넌트 239개·예제 9개. `catalog --query`로 로컬 검색, `add <name>`으로 프로젝트에 소스 복사(복사본은 일반 소스라 수정 가능). 콘텐츠 모음이라 원본 소스가 곧 문서이므로 스펙으로 옮기지 않는다(사용자 결정 2026-11-17). block과 component의 정확한 차이는 미확인 | `registry/registry.json`, `registry/{blocks,components,examples}/`, `commands/{add,catalog}.ts`, `packages/cli/src/registry/` | 1 | 핵심 | 스펙 안 씀(참고용) | 코드 확인(디렉터리 개수), 설치 흐름 미확인 |
| 14 | 에이전트 스킬·플러그인 | 스킬 9개(hyperframes, hyperframes-cli, hyperframes-registry, media-use, slideshow, figma, remotion-to-hyperframes, reverse-any-video, style-sampling), Claude Code·Gemini·MCP 플러그인 매니페스트, `skills` 명령. 스킬이 읽는 디자인 입력 `frame.md`(브랜드 색·폰트 등을 영상 프레임 기준으로 쓴 규칙 파일, 프리셋 13개 `skills/hyperframes/assets/frame-presets/*/FRAME.md`, README "Frame.md" 절, `docs/prompting/design-systems.mdx`)는 엔진이 아니라 에이전트가 참고하는 문서라 참고용으로만 둔다(사용자 결정 2026-11-17) | `skills/*/SKILL.md`, `plugin.json`, `gemini-extension.json`, `server.json`, `skills-manifest.json`, `commands/skills.ts` | 8 | 핵심 | `capabilities/agent-skills.md` · 미작성 | 코드 확인(디렉터리·description) |
| 15 | 미디어 생성·분석 도구 (패밀리) | `media-use`(음악·이미지·보이스·아바타 생성), `tts`, `transcribe`(whisper·parakeet·sherpa), `remove-background`, `beats`, `measure`(curve·cuts·face·look 등 11종), `media-treatment`, `normalize-audio`. 외부 모델·HeyGen API 의존이 큼 | `packages/cli/src/commands/{media-use,tts,transcribe,remove-background,beats,measure}.ts`, `src/{tts,whisper,background-removal,media-use,measure}/` | 8 | 핵심 | `capabilities/media-tools.md` · 미작성 | 코드 확인(등록부), 개별 구현 미탐색 |
| 16 | 외부 소스 가져오기 (패밀리) | `figma`(asset·component·tokens·download), `reverse`(영상→프로젝트), `capture video`, Remotion 이식 스킬 | `packages/core/src/figma/`, `commands/{figma,reverse,capture}.ts`, `commands/figma/*.ts`, `skills/{figma,reverse-any-video,remotion-to-hyperframes}/` | 1, 14 | 핵심 | `capabilities/import-sources.md` · 미작성 | 코드 확인(파일 존재), 추론 |
| 17 | 분산 렌더 (Lambda·Cloud Run·k8s) | 렌더를 plan → chunk 렌더 → 조립으로 쪼개 AWS Lambda, GCP Cloud Run + Workflows에서 실행. 배포용 CDK·Terraform·예제 포함 | `packages/producer/src/distributed.ts`(`assembleV2`·`renderChunkV2`), `services/distributed/*.ts`, `packages/aws-lambda/src/handler.ts`, `packages/gcp-cloud-run/src/server.ts`, `commands/{lambda,cloudrun}.ts`, `examples/` | 5 | 부속 | `capabilities/distributed-render.md` · 미작성 | 코드 확인(파일·export), 흐름 미확인 |
| 18 | HeyGen 호스팅 연동 | `auth` 로그인, `cloud render/get/list/delete`, `publish`·`share`(리뷰 버전 업로드·공유 상태)·`billing`·`usage` | `packages/cli/src/commands/{auth,cloud,publish,share,billing,usage}.ts`, `commands/cloud/*.ts`, `packages/share/src/index.mjs`, `reviewClient.mjs` | 5 | 부속 | `capabilities/heygen-hosting.md` · 미작성 | 코드 확인(파일 존재), 서버 측 범위 밖 |

**공유 계약** (여러 기능이 같이 쓰는 데이터·프로토콜. 코드로 확인한 것만)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| 컴포지션 파일·속성 계약 | 1, 2, 7, 9, 10 | `packages/core/src/compositionContract.ts`, `packages/parsers/src/compositionContract.ts`, `docs/concepts/data-attributes.mdx` | 행 1에 포함 · 미작성 | 코드 확인(파일 존재) |
| 렌더 요청·설정(`RenderConfigInput`) | 5, 8, 17, 18 | `packages/producer/src/renderRequest.ts`, `config.ts` | 행 5에 포함 · 미작성 | 코드 확인(파일 존재), 필드 미확인 |
| 런타임 메시지 프로토콜 | 2, 9, 10, 11 | `packages/core/src/runtime/protocol.ts`, `bridge.ts` | 행 2에 포함([runtime-seek](capabilities/runtime-seek.md) R-11~R-19) · draft | 코드 확인(파일 존재) |

**대조한 범위와 미탐색 영역**
- 대조: `packages/*` 16개 패키지 목록과 각 `package.json` description, `packages/cli/src/cli.ts` 명령 등록부 전체, `skills/*/SKILL.md` description 9개, `registry/` 디렉터리 개수, `docs/concepts`·`docs/packages` 파일 목록. 각 행의 `export` 심볼은 `grep`으로 위치만 확인했다.
- 문서와 구현의 차이: README의 "all 9 published skills"는 `skills/`의 9개 디렉터리와 일치한다. `hyperframes-registry` SKILL.md의 "About 450 ready-made blocks and components"는 디렉터리 210 + 239 = 449개와 맞는다.
- 미탐색(본문 미열람): `packages/studio`의 컴포넌트·hooks·webmcp, `core/src/runtime`의 개별 파일, 린트 규칙 내용, `claude-design`·`catch-up`·`events`·`telemetry`·`feedback`·`history`·`compare`·`diff`·`timeline` 명령, `packages/sdk-playground`, `docs/` 가이드·`prompting`·`workflows`, `plans/`·`releases/`·`updates/`·`themes/`. 이 중 `compare`·`diff`·`history`·`timeline` 명령은 행 7~10 어디에 넣을지 아직 정하지 않았다.
- 소유 행이 없는 명령(2026-11-17, 행 8 작성자가 등록부 56개를 표로 분류): 검증·시각 점검 `snapshot`·`compare`·`diff`·`inspect`·`keyframes`(행 7과 10 사이 경계로 보임. `snapshot`은 `lintProject`를 부름), 데스크톱 앱 연동 `open`·`catch-up`, 설치 유지보수 `upgrade`·`update`·`clean`·`browser`·`feedback`·`telemetry`·`templates`. 필요하면 새 행 후보로 올린다. 현재 승인 범위(행 1~8)에는 포함하지 않는다.
- 경계 메모(2026-11-17, 행 2 작성자 제안): 렌더 페이지의 `__hf.seek`·`__hf.duration`과 렌더 모드 플래그(`__HF_EXPORT_RENDER_SEEK_CONFIG` 등)는 core 런타임이 아니라 producer `fileServer.ts`의 `buildRenderModeScript`와 `HF_BRIDGE_SCRIPT`가 만든다. 소유는 행 4로 정했다(2026-11-17): 엔진이 캡처 페이지에 기대하는 계약(`__hf.seek`, `pollHfReady`, 렌더 모드 플래그)이라서 행 4가 쓰고, 행 5는 링크만 한다. 행 2 스펙에는 입구만 C-19로 있다.
- 행 수 18이라 20행 점검선 안이다. 행 9(Studio)는 `packages/studio` 1,032개 파일이라 본문을 열면 더 나눌 수 있다.

### 통합 검토: 대표 흐름 (2026-11-17, 행 1~8 스펙 기준)

입력은 `index.html` 하나와 `npx hyperframes render` 명령이다. 컴포지션 루트에 `data-composition-id`가 있고, GSAP으로 움직이는 clip에 `data-start="0"`, `data-duration="3"`이 있으며 `<audio data-start=...>` 하나가 있다고 하자. 로컬 Linux에서 mp4를 만드는 경로를 따라간다. 각 단계의 세부 규칙은 R-ID가 가리키는 스펙에 있다.

1. **CLI 입구(행 8)**: `cli.ts`가 등록부에서 `render`를 lazy import로 불러 실행한다. 렌더 직전에 `runRenderLint`가 돌고(기본은 lint error가 있어도 계속, `--strict`일 때 막음, [lint-check](capabilities/lint-check.md) R-16), 브라우저 준비·해상도 점검·슬롯 획득을 마친 뒤 `executeLocalRender`가 `executeRenderJob`을 부른다([render-orchestration](capabilities/render-orchestration.md) R-41).
2. **컴파일(행 1)**: 오케스트레이터가 `executeRenderJob` 시작에서 사전 검증을 한 뒤([render-orchestration](capabilities/render-orchestration.md) R-03) `compileForRender`로 컴포지션을 컴파일한다. 이때 `data-start` 같은 속성이 규칙대로 읽혀 타이밍이 정해지고 서브 컴포지션이 인라인된다([composition-contract](capabilities/composition-contract.md) R-01, R-25).
3. **캡처 경로 선택(행 4)**: 로컬 Linux CLI는 `browserGpuMode: "auto"`와 `forceScreenshot: false`로 BeginFrame을 쓴다. 엔진·producer를 코드로 직접 부르면 기본이 screenshot이다([capture-encode-engine](capabilities/capture-encode-engine.md) R-04).
4. **페이지 준비(행 2·4)**: 엔진이 Chrome으로 페이지를 열고 `pollHfReady`로 기다린다([capture-encode-engine](capabilities/capture-encode-engine.md) R-11). 페이지 안 런타임은 어댑터 promise와 timeline 빌드가 모두 끝나야 `__renderReady`를 올린다([runtime-seek](capabilities/runtime-seek.md) R-08).
5. **프레임 한 장(행 2·3·4)**: 프레임 N마다 시각 t = N/fps를 정하고 엔진이 `__hf.seek`를 부른다([runtime-seek](capabilities/runtime-seek.md) R-21). 런타임이 등록 순서대로 어댑터를 불러 GSAP 같은 애니메이션을 그 시각에 정지시킨다. 어댑터 예외는 삼켜진다([runtime-adapters](capabilities/runtime-adapters.md) R-04). 엔진은 seek가 남긴 비동기 작업이 끝나길 기다린 뒤 캡처하고([capture-encode-engine](capabilities/capture-encode-engine.md) R-18) 프레임을 인코더로 넘긴다.
6. **오디오(행 6)**: `audios`가 비어 있으면 믹스를 건너뛰고, 믹스가 실패하면 `audio_processing_failed`로 렌더가 `RenderQualityError`로 끝난다([audio-mix-fx](capabilities/audio-mix-fx.md) R-10, R-30).
7. **조립과 종료(행 5·8)**: 오케스트레이터가 인코딩한 비디오와 오디오를 조립해 산출물을 commit한다. 실패는 호출자가 받는 오류와 `job.error`가 다르게 전달된다([render-orchestration](capabilities/render-orchestration.md) R-37). CLI는 산출물이 검증된 뒤 후처리 예외가 나도 종료 코드를 0으로 고친다([cli-entry-init](capabilities/cli-entry-init.md) R-12).

**통합 검토 결과**: (1) `sha`는 8개 스펙 모두 `5979991d`로 같고 모두 `draft`이며, feature map·`index.md`와 `check.py`로 상태를 맞췄다. (2) 선행 순환은 없다(`cli-entry-init` → `render-orchestration` → `capture-encode-engine` → `runtime-seek` → `composition-contract`, `render-orchestration` → `audio-mix-fx`, `lint-check` → `composition-contract`). (3) 스펙끼리 건 R-ID 교차 링크는 정규식 점검에서 깨진 것이 없었다. (4) 공유 정의 점검은 독립 검토가 부분으로 했다. `RenderQualityError` 정책, `protocolTimeout` 확대(최대 1,800,000ms), `onSubTimelineScriptFailure` hook 연결, 캡처 경로 기본값 서술이 행 4·5·6 스펙에서 서로 같은지 확인했다. 전수 대조는 하지 않았다. (5) 위 흐름은 코드를 읽어 이은 것이고 렌더를 실제로 실행하지 않았다.

### 사용 방식 (코드 확인: README "How It Works"·"Quick Start", `skills/hyperframes-cli/SKILL.md`, `packages/cli/src/templates/blank/index.html`)

- 구성 3층: ① 렌더 엔진·CLI(npm `hyperframes`, 실제로 영상을 만드는 쪽) ② 에이전트 스킬(`b7fa007` 기준 21개, 현재 published 9개. 엔진을 쓰는 법을 가르치는 지침) ③ 선택 사항인 데스크탑 앱·Studio(`hyperframes open`으로 인계, 앱 없으면 exit 1).
- 컴포지션은 순수 HTML + `data-*` 속성 + 애니메이션 라이브러리(blank 템플릿은 CDN GSAP 3.14.2, `paused: true` 타임라인을 `window.__timelines`에 등록). 타임라인 구동 방식이 일반 웹페이지와 다르다.
- 스킬 경로: 에이전트가 스킬 지침대로 `npx hyperframes init/lint/check/preview/render`를 실행한다. 별도 서버 불필요, Node 22+·FFmpeg 필요. `preview`는 렌더 전 확인용 로컬 Studio 서버다.

### 패키지 구성 (`packages/`)

`share`·`sdk-playground`가 새로 보인다. `core`(컴포지션 계약·런타임·오디오·어댑터) · `engine`(Puppeteer+FFmpeg 캡처) · `producer`(렌더 오케스트레이션) · `cli` · `studio`/`studio-server` · `player` · `lint` · `parsers` · `sdk` · `shader-transitions`(WebGL 전환) · `aws-lambda` · `gcp-cloud-run` · `inspector`. 의존 순서는 루트 `package.json` `build` 스크립트(parsers·lint·studio-server → core → engine·producer·player·… → cli)로 확인.

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

미작성. 이번 요청은 clone·초기화·주요 기능 정리까지라 건너뜀. 다음 질문 때 그리기.

## 4. 질문과 조사 기록 (Questions)

없음.

## 5. 다음 작업 및 연계 링크

- **기능 스펙**: 없음(feature map 18행 중 승인 범위 1~8 작성 중)
- 미확인: 실제 렌더 실행(`npx hyperframes init/render`), `renderOrchestrator` 단계별 흐름, 런타임의 seek 구현(`packages/core/src/runtime`), Studio 구조.
- 의존성 설치·빌드는 하지 않음(모노레포가 커서 실행 실험 시 9장 절차로 진행).
