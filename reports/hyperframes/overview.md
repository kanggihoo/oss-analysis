---
sha: "b7fa007bf3cfb03a62bbb5460009c7e628e3bb2d"
created: 2026-10-20
updated: 2026-10-20
---

# hyperframes Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/heygen-com/hyperframes`
- **기준 SHA**: `b7fa007b` (2026-10-20), 버전 0.8.181 (`packages/*/package.json`)
- **작업트리 상태**: Clean
- **분석 목적**: 학습 (주요 기능 파악)
- **언어/규모**: TypeScript 모노레포(bun workspaces, Node ≥22, FFmpeg 필요), 추적 파일 9,546개. 테스트 제외 TS 줄 수: cli 8.3만, studio 16.4만, core 5.5만, producer 4.0만, engine 3.2만. Apache-2.0.

---

## 2. 프로젝트 개요

HTML·CSS·미디어·"seek 가능한 애니메이션"을 **결정적(deterministic) MP4**로 렌더하는 프레임워크다. 사람은 CLI로, AI 코딩 에이전트는 스킬/플러그인으로 쓰는 것이 전제다. (출처: README "Write HTML. Render video. Built for agents.")

핵심 아이디어: 영상을 재생해서 녹화하지 않고, **프레임 번호 N → 시각 t = N/fps → 모든 애니메이션을 t로 seek → 한 프레임 캡처**를 반복한다. 벽시계·무시드 랜덤·렌더 중 fetch를 금지해 같은 입력이 같은 영상을 낸다. (출처: `docs/concepts/determinism.mdx`)

### 주요 기능

| 기능 | 설명 | 코드 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|
| HTML 컴포지션 | `data-start`/`data-duration`/`data-track-index`와 `class="clip"`으로 타임라인을 HTML에 선언. 트랙은 Studio 행일 뿐 z-order는 CSS | `docs/concepts/data-attributes.mdx`, `packages/core/src/runtime/clip*.ts`(`clipTree.ts`, `clipWindow.ts`) | 코드 확인(파일 존재·문서), 런타임 동작은 추론 |
| 결정적 프레임 렌더 | 프레임마다 seek 후 Chrome `HeadlessExperimental.beginFrame`으로 캡처, FFmpeg로 인코딩 | `packages/engine/src/services/frameCapture.ts`(`beginFrameCapture` 사용), `streamingEncoder.ts`(`spawn(getFfmpegBinary())`) | 코드 확인(호출 존재), 실행 미확인 |
| 프레임 어댑터 | GSAP·CSS·WAAPI·Anime.js·Lottie·Three.js·TypeGPU·D3·지도(Leaflet/Mapbox/MapLibre/Google) 애니메이션을 seek로 구동. 커스텀은 `FrameAdapter{getDurationFrames, seekFrame, destroy}` | `packages/core/src/runtime/adapters/*.ts`, `docs/concepts/frame-adapters.mdx` | 코드 확인(파일 목록) |
| 렌더 파이프라인 | compile → 프레임 캡처(워커 병렬, 재시도) → 인코딩 → 오디오 믹스. `createRenderJob`/`executeRenderJob` | `packages/producer/src/services/renderOrchestrator.ts`(5.3천 줄), `parallelCoordinator.ts`, `docs/packages/producer.mdx` | 코드 확인(구조), 흐름 세부는 추론 |
| 오디오 믹싱·효과 | 보이스 카브(음악 덕킹), EQ·컴프·리버브 등 효과 체인, 자동화 곡선, 서브믹스 버스(`<hf-audio-group>`) | `packages/core/src/audio*.ts`, `packages/engine/src/services/audioMixer.ts`, `audioFxRender.ts` | 코드 확인(파일 존재) |
| CLI | `init`/`preview`/`render`/`lint`/`check`/`snapshot`/`doctor`/`publish`/`add`/`catalog`/`tts`/`transcribe`/`remove-background`/`skills`/`cloud`/`lambda` 등 | `packages/cli/src/commands/*.ts`, `packages/cli/package.json` `bin` | 코드 확인 |
| Studio·Player | 웹 편집 UI(타임라인), 임베드용 웹 컴포넌트 `<hyperframes-player>` | `packages/studio`(16만 줄), `packages/player`, `packages/studio-server` | 추론(미열람) |
| 분산 렌더 | AWS Lambda·GCP Cloud Run 어댑터, HeyGen 호스팅 `cloud render` | `packages/aws-lambda`, `packages/gcp-cloud-run`, `packages/producer/src/distributed.ts`, `commands/cloud/`, `commands/lambda/` | 코드 확인(파일 존재), 실행 미확인 |
| 레지스트리·카탈로그 | 재사용 블록 210개, 컴포넌트 238개를 `hyperframes add`로 설치 | `registry/blocks/`, `registry/components/`, `commands/add.ts`, `catalog.ts` | 코드 확인(개수는 `ls | wc -l`) |
| 에이전트 스킬 21개 | `/hyperframes` 라우터 + 생성 워크플로(product-launch, faceless-explainer, pr-to-video, slideshow, remotion-to-hyperframes 등) + 도메인 스킬(core·animation·audio·registry·cli…). Claude Code 플러그인 마켓플레이스 제공 | `skills/*/`(21개 디렉터리), `.claude-plugin/{marketplace,plugin}.json` | 코드 확인(디렉터리), README 주장과 개수 일치 |
| 린트·검증 | 컴포지션 규칙 검사(`lint`), 렌더 전 `check`, 레이아웃·대비·모션 감사 | `packages/lint`, `packages/core/src/lint`, `commands/{lint,check,layout,contrast-*}.ts` | 코드 확인(파일 존재) |
| 변환·연동 | Remotion→HyperFrames 이식 스킬, Figma 임포트, SDK(헤드리스 편집 엔진) | `skills/remotion-to-hyperframes`, `packages/core/src/figma`, `packages/sdk` | 추론 |
| 렌더 모드 | Linux/Docker는 BeginFrame, 그 외는 스크린샷 fallback, 별도 drawElement 경로. 로컬은 폰트·Chrome 차이로 픽셀이 달라질 수 있어 `--docker` 권장 | `frameCapture.ts` 주석(1060, 1213행 부근), `drawElementService.ts`, `docs/concepts/determinism.mdx` | 코드 확인(주석 수준) |

### 사용 방식 (코드 확인: README "How It Works"·"Quick Start", `skills/hyperframes-cli/SKILL.md`, `packages/cli/src/templates/blank/index.html`)

- 구성 3층: ① 렌더 엔진·CLI(npm `hyperframes`, 실제로 영상을 만드는 쪽) ② 에이전트 스킬 21개(엔진을 쓰는 법을 가르치는 지침) ③ 선택 사항인 데스크탑 앱·Studio(`hyperframes open`으로 인계, 앱 없으면 exit 1).
- 컴포지션은 순수 HTML + `data-*` 속성 + 애니메이션 라이브러리(blank 템플릿은 CDN GSAP 3.14.2, `paused: true` 타임라인을 `window.__timelines`에 등록). 타임라인 구동 방식이 일반 웹페이지와 다르다.
- 스킬 경로: 에이전트가 스킬 지침대로 `npx hyperframes init/lint/check/preview/render`를 실행한다. 별도 서버 불필요, Node 22+·FFmpeg 필요. `preview`는 렌더 전 확인용 로컬 Studio 서버다.

### 패키지 구성 (`packages/`)

`core`(컴포지션 계약·런타임·오디오·어댑터) · `engine`(Puppeteer+FFmpeg 캡처) · `producer`(렌더 오케스트레이션) · `cli` · `studio`/`studio-server` · `player` · `lint` · `parsers` · `sdk` · `shader-transitions`(WebGL 전환) · `aws-lambda` · `gcp-cloud-run` · `inspector`. 의존 순서는 루트 `package.json` `build` 스크립트(parsers·lint·studio-server → core → engine·producer·player·… → cli)로 확인.

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

미작성. 이번 요청은 clone·초기화·주요 기능 정리까지라 건너뜀. 다음 질문 때 그리기.

## 4. 질문과 조사 기록 (Questions)

없음.

## 5. 다음 작업 및 연계 링크

- **기능 스펙**: 없음
- 미확인: 실제 렌더 실행(`npx hyperframes init/render`), `renderOrchestrator` 단계별 흐름, 런타임의 seek 구현(`packages/core/src/runtime`), Studio 구조.
- 의존성 설치·빌드는 하지 않음(모노레포가 커서 실행 실험 시 9장 절차로 진행).
