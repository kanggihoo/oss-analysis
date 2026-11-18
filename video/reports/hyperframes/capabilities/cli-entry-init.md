---
sha: "5979991d5f0af542fbb02ba906bdba4de52b2b64"
created: 2026-11-17
updated: 2026-11-17
sources:
  - packages/cli/bin/hyperframes.mjs
  - packages/cli/package.json
  - packages/cli/src/cli.ts
  - packages/cli/src/help.ts
  - packages/cli/src/version.ts
  - packages/cli/src/runtimeVersion.ts
  - packages/cli/src/utils/defineCommand.ts
  - packages/cli/src/utils/commandResult.ts
  - packages/cli/src/utils/attendedTerminal.ts
  - packages/cli/src/utils/jsonError.ts
  - packages/cli/src/utils/projectShortcut.ts
  - packages/cli/src/utils/dotEnv.ts
  - packages/cli/src/utils/command-failure-tracking.ts
  - packages/cli/src/utils/reject-unknown-flags.ts
  - packages/cli/src/utils/reject-extra-positionals.ts
  - packages/cli/src/utils/commandUsageResolution.ts
  - packages/cli/src/utils/renderCancellation.ts
  - packages/cli/src/utils/renderLock.ts
  - packages/cli/src/utils/dockerRunArgs.ts
  - packages/cli/src/utils/audioLoweredWarning.ts
  - packages/cli/src/utils/project.ts
  - packages/cli/src/utils/projectConfig.ts
  - packages/cli/src/utils/copyDir.ts
  - packages/cli/src/utils/env.ts
  - packages/cli/src/utils/variables.ts
  - packages/cli/src/ui/prompts.ts
  - packages/cli/src/ui/renderResult.ts
  - packages/cli/src/ui/progress.ts
  - packages/cli/src/commands/render.ts
  - packages/cli/src/commands/render/plan.ts
  - packages/cli/src/commands/render/execute.ts
  - packages/cli/src/commands/render/present.ts
  - packages/cli/src/commands/render/renderSlot.ts
  - packages/cli/src/commands/batchRender.ts
  - packages/cli/src/commands/init.ts
  - packages/cli/src/commands/initMedia.ts
  - packages/cli/src/commands/doctor.ts
  - packages/cli/src/commands/info.ts
  - packages/cli/src/commands/docs.ts
  - packages/cli/src/commands/compositions.ts
  - packages/cli/src/commands/skills.ts
  - packages/cli/src/templates/blank/index.html
  - packages/cli/src/templates/from-file/index.html
  - packages/cli/src/templates/generators.ts
  - packages/cli/src/templates/remote.ts
  - packages/cli/src/templates/_shared/CLAUDE.md
  - packages/cli/src/docker/Dockerfile.render
  - packages/core/src/utils/renderOutputTimestamp.ts
depends:
  - render-orchestration.md
  - lint-check.md
status: draft
---

# CLI 명령 입구와 새 프로젝트 생성

> `npx hyperframes <cmd>`로 들어온 인자를 `cli.ts`가 명령 파일에 넘기고, `init`이 새 프로젝트 폴더를 만들며, `render`가 플래그를 모아 `executeRenderJob`까지 넘기는 입구 계약이다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

대표 흐름은 새 프로젝트를 만들어 렌더까지 가는 경로다.

1. 사용자가 `npx hyperframes init my-video`를 실행한다. `bin/hyperframes.mjs`가 Node 22 이상인지 확인하고 `dist/cli.js`(`cli.ts`)를 import한다(R-01).
2. `cli.ts`가 `--version`을 먼저 걸러내고, 작업 폴더의 `.env`에서 허용된 키만 읽고, 명령 이름 `init`으로 등록부를 조회해 `commands/init.js`를 처음 import한다. 알 수 없는 flag는 이 시점에 거절한다(R-03, R-04, R-05, R-15).
3. `init`이 대화형인지 무인인지 정하고, `blank`(또는 `--video`·`--audio`가 있으면 `from-file`, `--example`이 있으면 그 이름) 템플릿을 복사해 `index.html`, `meta.json`, `hyperframes.json`, `package.json`, `CLAUDE.md`, `AGENTS.md`를 만들고, 없는 코어 스킬을 설치한다(R-40~R-49).
4. 사용자가 프로젝트 폴더에서 `npx hyperframes render`를 실행한다. `render`의 `run`이 flag를 `RenderPlan`으로 굳힌다(R-16~R-21).
5. `executeRenderPlan`이 린트, 브라우저 확보, 해상도 preflight, 렌더 슬롯 순으로 문을 지난다. 린트 단계는 `--strict`일 때만 error에서 막는다(R-22~R-26).
6. `renderLocal`이 환경 점검과 인코더 선택을 하고 엔진 설정을 만든 뒤 `executeRenderJob`을 부른다. `--docker`는 같은 flag를 컨테이너 안의 `hyperframes render`에 넘기고, `--batch`는 행마다 이 경로를 반복한다(R-27~R-39).
7. 성공하면 출력 파일 경로와 크기를 출력하고 종료 코드 0, 실패하면 오류 상자와 종료 코드 1(또는 사용법 오류 2)로 끝난다. 모든 종료는 `cli.ts`의 `finalizeCli`를 거친다(R-10~R-13, R-33, R-34).

### 1.2 범위·통합 지점
- 제공: 명령 등록과 lazy import, 인자 검증, help·버전·알 수 없는 명령 처리, 종료 코드와 JSON 실패 규칙, 공통 전처리(`.env`, 업데이트 확인, telemetry, `preview` 빌드 게이트), `init`(새 프로젝트 폴더와 시작 파일, 스킬 설치 단계), `render`(flag 해석부터 `executeRenderJob` 호출과 결과 출력까지), 그리고 `doctor`·`info`·`docs`·`compositions`와 나머지 50개 명령의 소유 행 표.
- 제외: 오케스트레이터 내부 단계·재시도·취소(render-orchestration.md), 린트 규칙과 `--strict` 판정 규칙(lint-check.md R-16), Studio 서버(행 9), 편집 명령(행 10), 미디어 도구(행 15), 외부 가져오기(행 16), 분산·클라우드·인증·빌링(행 17·18), 스킬 설치 내부(행 14), registry 설치 내부(행 13). 표에서는 소유 행만 적는다.
- 외부 의존·선행 계약: [render-orchestration.md](render-orchestration.md)가 `executeRenderJob`의 입력·출력·오류 계약을, [lint-check.md](lint-check.md)가 `runRenderLint`가 쓰는 린트 판정을 정한다. citty(`^0.2.1`, 인자 파싱), `@clack/prompts` 래퍼(`ui/prompts.js`), Docker, ffmpeg·ffprobe, Chrome은 호출자 환경이 제공한다. citty는 `node_modules`에 설치돼 있지 않아 내부 동작은 읽지 못했다.
- 소유 상태·부작용: `process.argv`(help·폴더 단축·registry·measure 별칭 재작성), `process.env`(`.env` 허용 키, `plan.environment`, `HYPERFRAMES_FFMPEG_PATH`·`HYPERFRAMES_FFPROBE_PATH`·`PRODUCER_HEADLESS_SHELL_PATH`·`HYPERFRAMES_GSAP_VENDOR_DIR` 설정), 렌더 슬롯 lock 파일, batch의 `manifest.json`, `renders/` 출력 폴더, 프로젝트 기록(`recordRenderSuccess`, 최근 렌더 목록), telemetry 큐, `init`이 만드는 프로젝트 폴더와 전역 스킬 설치.

### 1.3 인터페이스와 데이터 의미
| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `hyperframes <command> [flags]` 최상위 | argv(string 목록) → 종료 코드(int)와 stdout·stderr | 명령 56개가 `commandLoaders`에 있다. 종료 코드는 0(성공), 1(runtime error), 2(usage error)가 기본이고 명령이 `failCommand(n)`·`finishCommand(n)`로 다른 값을 줄 수 있다. R-05, R-10 |
| `render [dir]` flag 전체 | `dir` positional(기본 현재 폴더), `--composition`/`-c`(string, 없거나 `.`이면 `index.html`), `--output`/`-o`(string, 기본 `renders/<project>_<YYYY-MM-DD>_<HH-MM-SS>.<ext>`), `--fps`/`-f`(string, 정수나 `30000/1001` 꼴 분수, 1-240, 없으면 루트 `data-fps`, 그것도 없으면 30), `--quality`/`-q`(string, `draft`·`looks`·`delivery`·`standard`·`high`, 기본 `looks`), `--format`(string, 기본 `mp4`, `mp4`·`webm`·`mov`·`gif`·`png-sequence`·`hls`), `--skill`(string, 슬러그가 아니면 무시), `--gif-loop`(string, 0-65535), `--hls-segment-seconds`(string, 1-60, 기본 4), `--video-frame-format`(string, 기본 `auto`, `jpg`·`png`), `--page-motion-blur`(string, `off`만 의미), `--workers`/`-w`(string, 숫자나 `auto`), `--docker`(boolean, false), `--hdr`(false), `--sdr`(false), `--crf`(string), `--video-bitrate`(string, 예 `10M`), `--start`(string, 초), `--end`(string, 초), `--keyframe-interval`, `--max-bitrate`, `--buffer-size`, `--prores-profile`(전달 flag 4개, `utils/deliveryFlags.ts`), `--vp9-cpu-used`(string, -8~8), `--chroma-subsampling`(string, 기본 `420`, `444`), `--gpu`(boolean, false), `--browser-gpu`(boolean, 기본 없음, `--no-browser-gpu` 가능), `--quiet`(false), `--lint-verbose`(false), `--debug`(false), `--best-effort`(boolean, 기본 true), `--wait`(boolean, 기본 true), `--strict`(false), `--strict-all`(false), `--max-concurrent-renders`(string, 1-10, 기본 2), `--variables`(string), `--variables-file`(string), `--strict-variables`(false), `--batch`(string), `--batch-concurrency`(string, 기본 1), `--batch-fail-fast`(false), `--json`(false), `--resolution`(string, 프리셋 이름), `--page-side-compositing`(boolean, 기본 true), `--browser-timeout`(string, 초), `--protocol-timeout`(string, ms), `--player-ready-timeout`(string, ms), `--resume`(false), `--keep-segments`(false), `--low-memory-mode`(boolean, 기본 없음), `--experimental-fast-capture`(boolean, 기본 없음), `--frames-cache-dir`(string) | 위 목록은 `render.ts:175-520`의 `args` 선언이다. 기본값이 `undefined`인 flag는 선언하지 않아야 환경변수 대체(`PRODUCER_*`)가 살아 있다. 값을 해석하는 규칙은 R-17~R-20 |
| `init [name]` flag 전체 | `name` positional(선택), `--example`/`-e`(string, 예 `warm-grain`·`swiss-grid`·`blank`), `--template`/`-t`(숨김 string, 지원 종료: 쓰면 `--example`을 쓰라는 안내와 종료 코드 2), `--video`/`-v`(string, mp4·webm·mov 경로), `-V`(숨김 `video-legacy`, 쓰면 `--video`를 쓰라는 안내와 종료 코드 2), `--audio`/`-a`(string, mp3·wav·m4a 경로), `--skip-transcribe`(boolean), `--keep-original`(boolean), `--model`(string, whisper 모델), `--language`(string), `--non-interactive`(boolean), `--agent`(숨김 boolean, `--non-interactive`와 같다), `--skip-skills`(boolean, `HYPERFRAMES_SKIP_SKILLS=1`로도 켠다), `--tailwind`(boolean), `--resolution`(string, `render`의 프리셋과 같은 이름·alias), `--skill`(string, slug) | `init.ts:769-860`의 `args` 선언이다. 기본값은 모두 선언하지 않고(`undefined`) 코드가 `=== true`로 읽는다. 잘못된 `--resolution`은 오류 문장과 종료 코드 2다(R-42) |
| 명령 종료 도우미 | `failCommand(exitCode=1, cause?, code?)`, `failUsage(exitCode=2)`, `finishCommand(exitCode=0)`, `setCommandExitCode(n)`, `requestCliExit(n)`, `scheduleCliExit(n)`(100ms 뒤 `requestCliExit`) | `failCommand`와 `failUsage`는 이미 출력한 실패를 `presented: true`로 던져 `cli.ts`가 메시지를 다시 쓰지 않게 한다. `finishCommand`는 조기 종료 신호(`CliResultSignal`)다. `setCommandExitCode`는 던지지 않고 결과만 남기고 0이 아닌 값이 먼저 있으면 0으로 덮지 않는다. 종료 코드 상수는 `USAGE_EXIT_CODE = 2` 하나다. R-10, R-12 |
| `defineCommand(def)` | citty 명령 정의 → 같은 정의(등록 표시됨) | 모든 등록 명령이 이 래퍼를 써야 하고, 등록 표시를 `WeakSet`에 남긴다. 표시가 없는 명령을 거절하는 검사는 소스 주석상 agent-mode contract test에 있다(테스트는 열지 않았다) |
| 무인 판정 | `isAttendedTerminal()`, `isUnattended()` | `isAttendedTerminal`은 CI가 아니고 stdin·stdout이 모두 TTY일 때 true다. `isUnattended`는 터미널이 아니거나 `HYPERFRAMES_AGENT=1`이거나 코딩 에이전트가 구동 중이면 true이고 이때 프롬프트를 띄우지 않는다. `init`이 모드를 정하는 데 쓴다(R-40) |
| `--json` 실패 envelope | `{ok: false, error: {code: string, message: string, hint?: string}}` | stdout에 한 줄. `--json`을 선언한 명령만 받는다. R-11 |
| `RenderPlan`(불변 객체) | `createRenderPlan` 반환값 | 프로젝트(`dir`, `name`, `indexPath`), `entryFile`, `renderTarget`, `fps`(분수), `quality`, `qualityPreset`, `format`, `outputPath`, `useDocker`, `useGpu`, `browserGpuMode`, `hdrMode`, `workers`, `range`, 인코더 값(`crf`, `videoBitrate`, `maxBitrate`, `bufferSize`, `keyframeIntervalSeconds`, `proresProfile`, `vp9CpuUsed`, `chromaSubsampling`), 타임아웃 3종, batch 값, `strictErrors`, `strictAll`, `quiet`, `effectiveQuiet`, `environment`(환경변수로 옮길 값) 등을 담는다. 단일 렌더에서 `renderOptionsFromPlan`이 `RenderOptions`로 옮기고 `exitAfterComplete: true`, `manageDeParallelRouterBreaker: true`를 더한다. batch 행은 `batchRowRenderOptions`가 `exitAfterComplete: false`, `throwOnError: true`, `skipFeedback: true`, `desktopHint: false`를 더한다. R-16~R-21 |
| `renderLocal` 입력·출력 | `(projectDir, outputPath, RenderOptions, cancellation?) → SingleRenderResult` | 결과는 `{renderTimeMs, durationMs?, outcome("completed"\|"completed_with_warnings"), warnings[{code, message}], motionBlur?, referenceBackground...}`다. docker 경로는 `{renderTimeMs}`만 돌려준다(R-36). `executeRenderJob`의 입력·출력은 [render-orchestration.md](render-orchestration.md) 1.3 |
| `init`이 만드는 폴더 | 대상 폴더 `<name>/` | 필수: `index.html`(템플릿 복사), `meta.json`, `hyperframes.json`, `package.json`, `CLAUDE.md`, `AGENTS.md`. 선택: 복사하거나 변환한 비디오·오디오 파일, `transcript.json`(전사 성공 때), 원격 example이면 registry가 설치한 파일(어떤 파일인지는 example마다 다르고 `installItem`을 읽지 않아 모른다). 내용은 R-45, `blank`의 `index.html`은 C-01 |

#### 명령 계열 표 (이 스펙이 직접 다루지 않는 명령 50개와 개념 수준 표시)

소유 행은 `overview.md` 2절 feature map 행 번호다. 소유 행이 없는 명령은 "미배정"이고(U-02), 한 줄 동작은 `meta.description`이나 `help.ts` 설명을 옮긴 것이다. 진입 파일은 모두 `packages/cli/src/commands/` 아래다.

| 계열 | 명령 | 한 줄 동작 | 소유 행 | 진입 파일 |
|---|---|---|---|---|
| 시작·이 스펙 | `init` | 새 composition 프로젝트를 만든다 | 8(이 스펙) | `init.ts` |
| 시작·이 스펙 | `render` | 컴포지션을 MP4·WebM·MOV·GIF·HLS·PNG 시퀀스로 렌더한다 | 8(이 스펙), 오케스트레이터는 5 | `render.ts`, `render/` |
| 점검·정보 | `doctor`, `info`, `docs`, `compositions` | 환경 점검, 프로젝트 메타데이터, 터미널 문서, 컴포지션 목록 | 8(이 스펙, R-51~R-54) | `doctor.ts`, `info.ts`, `docs.ts`, `compositions.ts` |
| 린트·검증 | `lint`, `check`, `validate`, `layout` | 규칙 검사, lint·런타임·layout을 묶은 게이트, headless Chrome 검증(deprecated, `check`를 쓰라고 안내), layout 점검 | 7([lint-check.md](lint-check.md)) | `lint.ts`, `check.ts`, `validate.ts`, `layout.ts` |
| 미리보기·덱 | `preview`, `play`, `present` | Studio 미리보기 서버, 가벼운 브라우저 플레이어, 슬라이드쇼 발표자 모드 | `preview` 9(범위 밖, 전처리 게이트만 R-55), `play`·`present` 11(범위 밖) | `preview.ts`, `play.ts`, `present.ts` |
| 편집·검사 | `timeline`, `history`, `inspect`, `keyframes` | 트랙·클립 출력과 편집, 변경 이력 조회·되돌림, 렌더된 레이아웃 검사, keyframe 진단 | `timeline`·`history` 10(범위 밖, 추정), `inspect`·`keyframes` 미배정 | `timeline.ts`, `history.ts`, `inspect.ts`, `keyframes.ts` |
| 시각 확인 | `snapshot`, `compare`, `diff`, `grade-compare` | 핵심 프레임 PNG, 변형 비교 시트, 원본 영상 대비 점수, 색보정 비교 | `grade-compare` 12(범위 밖), 나머지 미배정 | `snapshot.ts`, `compare.ts`, `diff.ts`, `grade-compare.ts` |
| 레지스트리 | `add`, `catalog`, `templates` | 블록·컴포넌트 설치, 목록 검색, 스타일 템플릿 가져오기 | `add`·`catalog` 13(참고용), `templates` 미배정 | `add.ts`, `catalog.ts`, `templates.ts` |
| 미디어 도구 | `media-use`, `tts`, `transcribe`, `remove-background`, `beats`, `audio`, `normalize-audio`, `measure`, `media-treatment`, `models` | 미디어 생성·전사·배경 제거·박자·음량·측정·처리, 온디바이스 모델 관리 | 15(범위 밖, `audio`·`models`는 추정) | `media-use.ts`, `tts.ts`, `transcribe.ts`, `remove-background.ts`, `beats.ts`, `audio.ts`, `normalize-audio.ts`, `measure.ts`, `media-treatment.ts`, `models.ts` |
| 외부 가져오기 | `capture`, `figma`, `reverse` | 웹사이트 캡처, Figma 가져오기, 영상에서 프로젝트 복원 | 16(범위 밖) | `capture.ts`, `figma.ts`, `reverse.ts` |
| 분산·클라우드·계정 | `lambda`, `cloudrun`, `cloud`, `auth`, `share`, `publish`, `billing`, `usage` | AWS Lambda·Cloud Run 분산 렌더, HeyGen 클라우드 렌더, 로그인, 리뷰 공유, 소스 게시, 플랜·사용량 | `lambda`·`cloudrun` 17(범위 밖), 나머지 18(범위 밖) | `lambda.ts`, `cloudrun.ts`, `cloud.ts`, `auth.ts`, `share.ts`, `publish.ts`, `billing.ts`, `usage.ts` |
| 스킬·텔레메트리 | `skills`, `events` | 에이전트 스킬 설치, 스킬 사용 이벤트 전송 | `skills` 14(범위 밖), `events` 14로 추정 | `skills.ts`, `events.ts` |
| 도구·유지보수 | `benchmark`, `browser`, `clean`, `upgrade`, `update`, `feedback`, `telemetry` | 렌더 속도 비교, Chrome 관리, 디스크 정리, CLI·스킬 업데이트, 피드백, telemetry 설정 | `benchmark`는 5와 8 경계(오케스트레이터를 직접 호출, R-46), 나머지 미배정 | `benchmark.ts`, `browser.ts`, `clean.ts`, `upgrade.ts`, `update.ts`, `feedback.ts`, `telemetry.ts` |
| 데스크톱 앱 | `open`, `catch-up` | 프로젝트를 데스크톱 앱에서 열기, 앱에서 한 작업 요약 | 미배정(데스크톱 앱은 feature map에 행이 없다) | `open.ts`, `catch-up.ts` |

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `hyperframes.mjs`(package.json `bin.hyperframes`)가 시작한다 | `process.versions.node`의 major가 22 미만이면 `HyperFrames requires Node.js >= 22 (current: <version>). Switch Node versions and retry.`를 stderr에 쓰고, 인자에 `--json`이 있으면 stdout에 `{"ok":false,"error":{"code":"node_version_unsupported","message":...}}`를 더해 쓰며 `process.exitCode = 1`로 끝난다. `dist/cli.js`는 읽지 않는다. 충족하면 compile cache를 켜고, 첫 인자가 `check`이면 warm check 경로를 먼저 시도하고 아니면 `dist/cli.js`를 import한다. 환경변수 `HYPERFRAMES_PLUGIN_CWD`가 있으면 그 폴더로 `chdir`하고 `PWD`를 맞춘 뒤 환경변수를 지운다 | 코드 확인 |
| R-02 | `cli.ts` 시작, 첫 인자가 `help` | `process.argv`에서 `help`를 지우고 나머지 뒤에 `--help`를 붙여 다시 읽는다. `hyperframes help render`는 `hyperframes render --help`와 같다 | 코드 확인 |
| R-03 | 첫 인자가 `--version`이나 `-V`이거나, 첫 인자가 없고 인자 어딘가에 `--version`이나 `-V`가 있다 | `VERSION`(빌드 때 주입한 `__CLI_VERSION__`, 주입이 없으면 `0.0.0-dev`)을 stdout에 쓰고 `process.exit(0)`한다. telemetry와 업데이트 확인을 시작하기 전이다. `hyperframes render --version`은 이 경로가 아니다 | 코드 확인 |
| R-04 | 명령 조회 전 | 작업 폴더의 `.env`를 읽되 `PROJECT_ENV_KEYS`(API 키류, 모델 이름, telemetry 끄기 변수 16개)만 `process.env`에 적용하고 나머지 키는 무시하며 무시한 키 이름을 stderr에 경고한다. 명령이 `capture`이고 `HYPERFRAMES_NO_CAPTURE_DOTENV=1`이면 읽지 않는다 | 코드 확인 |
| R-05 | 명령 등록부 `commandLoaders` | 명령 56개를 `이름 → () => import("./commands/<이름>.js")`로 등록한다. 모듈은 해당 명령이 불릴 때 처음 import한다. `media-treatment`만 default가 아닌 `mediaTreatmentCommand` export를 쓰고, `preview`는 import 앞에서 `assertStudioWorkspaceBuilt()`를 먼저 기다린다. 각 로더는 `trackCommandFailures`로 감싸 알 수 없는 flag 거부와 여분 positional 검사를 얹는다 | 코드 확인 |
| R-06 | 첫 non-flag 인자(`--` 앞)가 등록되지 않은 이름이고 현재 폴더에 그 이름의 디렉터리가 있다 | `open <그 인자> ...`로 바꿔 쓴다. 등록된 명령 이름이 같은 이름의 폴더보다 우선한다. 인자가 `registry`이면 `catalog`로 바꾸고 뒤따르는 `search` 한 단어는 지운다. `measure`의 첫 인자가 op 이름이 아니고 파일로 존재하면 `measure probe <file>`로 바꾸고 안내 문장을 stderr에 쓴다 | 코드 확인 |
| R-07 | 알 수 없는 최상위 명령 `hyperframes <word>`(`-`로 시작하지 않고, R-06 폴더 규칙에도 걸리지 않음) | `Unknown command: <word>`, 가장 가까운 이름 제안이나 `commandRedirect` 안내, `Run 'hyperframes --help' to list every command.`를 stderr에 쓰고 `CliUsageError(code: "unknown_command")`로 종료 코드 2로 끝난다. citty가 모든 명령을 로드하며 alias를 찾는 일을 피하려고 `runCommand` 앞에서 거른다 | 코드 확인 |
| R-08 | 인자가 없다 | `rejectUnknownTopLevelCommand`가 통과시키고, 최상위 명령에 `run`이 없어서 citty가 `E_NO_COMMAND`를 던진다고 코드가 가정한다. `cli.ts`는 이 코드를 usage error(종료 코드 2)로 분류하고 citty 오류의 메시지를 stderr에 쓴다. citty 오류는 `CliUsageError`가 아니어서 `executeCli`의 사용법 출력 분기를 타지 않으므로 root help는 따로 나오지 않는다. citty 쪽 던지는 조건은 설치본이 없어 읽지 못했다 | 추론 |
| R-09 | `--help`나 `-h`가 인자 어디든 있다 | 명령은 실행하지 않는다. telemetry와 업데이트 확인과 앱 기록 안내도 시작하지 않는다. 이름을 따라 내려가며 해석한 명령의 help를 stdout에 쓰고 종료 코드 0이다. 최상위는 `help.ts`의 `GROUPS` 7개 묶음 목록, 하위 명령은 citty `renderUsage`에 `_examples.ts` 예시를 덧붙인다. 알 수 없는 하위 명령 이름이면 R-07과 같은 오류를 낸다. 단 그 그룹 명령이 positional을 받으면(예: `timeline <dir>`) 오류 대신 그 명령의 help를 쓴다 | 코드 확인 |
| R-10 | 명령이 실행 중 던진 값을 `executeCli`가 받는다 | 종료 코드는 `CliResultSignal`이면 그 값, `CliUsageError`·`CliRuntimeError`이면 각자의 `result.exitCode`(기본 2와 1), citty 파싱 오류(`EARG`, `E_UNKNOWN_COMMAND`, `E_NO_COMMAND`)이면 2, 그 밖의 오류이면 1이다. `CliResultSignal`이 아니면 telemetry에 command failure를 기록하고, 출력하지 않은 usage error이면 hint가 없을 때 사용법을, 이미 출력하지 않은 오류이면 메시지를 stderr에 쓴다. `setCommandResult`로 명령이 남긴 `pendingResult`가 0이 아니면 그것이 최종 결과가 된다 | 코드 확인 |
| R-11 | 명령 인자에 `--json`이 있는 실행이 0이 아닌 종료 코드로 끝났고 stdout에 아무것도 쓰지 않았다 | stdout에 `{"ok":false,"error":{"code","message","hint?"}}` 한 줄을 쓴다. `code`는 typed error의 `code`, 없으면 usage 오류 `usage_error`와 그 밖 `runtime_error`다. message는 오류 자신의 문장, 없으면 cause, 명령이 `recordFailure`로 남긴 것, 마지막으로 stderr 끝 1000자(색 제거) 순이다. 명령이 이미 stdout에 쓴 실행은 덧붙이지 않는다. `--json`은 전역 flag가 아니고 `json` arg를 선언한 명령만 받는다 | 코드 확인 |
| R-12 | 종료 처리 `finalizeCli` | `isRenderSucceeded()`가 true이면 결과가 실패여도 종료 코드를 0으로 고친다(산출물이 검증되고 저장된 뒤의 후처리 예외를 성공으로 둔다). 종료 코드가 0이면 `markCommandDelivered()`를 부른다. `render`가 0이 아닌 코드로 끝났는데 오류 상자도 JSON 실패도 보이지 않았으면 `The command ended with code N without saying why`와 실패가 처음 설정된 stack 한 줄을 낸다. usage error가 아니면 업데이트 안내, 고정 버전 안내, skills 갱신 안내, 데스크톱 앱 기록 안내를 stderr에 쓰고(`--json`이면 앞의 둘은 생략) `process.exitCode`를 정한다 | 코드 확인 |
| R-13 | 처리되지 않은 예외나 거부, stdout/stderr의 `EPIPE` | `EPIPE`이면 렌더 산출물이 이미 확정(`isRunDelivered`)된 실행은 종료 코드 0, 아니면 1로 즉시 끝난다. `uncaughtException`은 산출물이 확정된 뒤이면 stderr에 `Late uncaughtException ...`만 남기고 0으로 끝나고, 아니면 오류 상자 `The command stopped on an unexpected error`를 쓰고 1로 끝난다. `unhandledRejection`은 확정 뒤에는 기록만 하고, 아니면 `process.exitCode = 1`을 두고 오류 상자를 쓴다 | 코드 확인 |
| R-14 | `--help`가 아니고 `cli.ts`가 명령 이름을 정한 뒤(등록되지 않은 이름은 `unknown`) | telemetry(`trackCommand`, 첫 실행 안내, 명령 횟수)를 시작한다. `telemetry`, `events`, `usage`와 `unknown`은 제외한다. 업데이트 확인(캐시된 결과로 안내, 백그라운드 설치, 백그라운드 점검 프로세스)은 `upgrade`, `update`, `events`, `telemetry`, `skills`, `usage`가 아니면(`unknown` 포함) 시작하고, `--json`이면 업데이트 안내와 자동 설치 보고는 하지 않는다. 앱 기록 안내는 `unknown`, `catch-up`, `events`, `telemetry` 밖에서만 읽는다 | 코드 확인 |
| R-15 | 알 수 없는 flag, 선언보다 많은 positional | 명령 본문 앞에서 `Unknown flag: <flag>`(`--help`·`-h`·`--version`·`-v`는 항상 허용, `--no-<flag>`와 camelCase·kebab 두 표기와 alias 허용, `--` 이후는 검사하지 않음)를 `CliUsageError(code: "unknown_flag")`로, 값이 있는 string·enum flag 뒤에 다른 flag가 오면 `Missing value for --<flag>`를 종료 코드 2로 거절한다. `check`는 `--frame-check`를 값 없이 받으면 `--frame-check=`로 바꾼다. 여분 positional은 `Unexpected extra argument(s) for hyperframes <path>`와 `Usage:` 줄을 쓰고 종료 코드 2이며, 자유 문장을 받는 명령은 남는 단어를 합친다 | 코드 확인 |
| R-16 | `render` 실행이 `createRenderPlan(args)`에 들어간다 | 프로젝트 폴더(`dir`, 기본 `.`)를 해석한다. 폴더가 없거나 파일이면 오류 상자를 낸 뒤 종료 코드 1이고, `--composition`이 없는데 `index.html`이 없으면 `No composition found in <dir>`와 `Run npx hyperframes init ...` 안내 후 종료 코드 1이다. 이어서 아래를 이 순서로 검증하고 잘못된 값마다 `errorBox(제목, 설명)` 뒤 `failUsage()`(종료 코드 2)로 끝난다. `--page-motion-blur`(`off`만 허용), fps, quality, format, `--gif-loop`, `--hls-segment-seconds`, `--chroma-subsampling`, `--video-frame-format`, `--resolution`, 충돌 검사들, workers, `--protocol-timeout`, `--player-ready-timeout`, `--max-concurrent-renders`, batch flag 조합, `--browser-gpu`와 `--docker` 충돌, `--crf`·`--video-bitrate`, `--vp9-cpu-used`, 전달 flag, `--start`·`--end`. 검증이 모두 끝나면 `Object.freeze`한 `RenderPlan`을 반환한다. 이 단계는 브라우저도 오케스트레이터도 부르지 않는다 | 코드 확인 |
| R-17 | 해석 규칙(단일 값) | `--quality`는 `draft`→`draft`, `standard`→`standard`, `high`→`high`, `looks`→`standard`+crf 16, `delivery`→`high`로 바꾼다. `--format`이 `gif`이고 fps가 30을 넘으면 fps를 30으로 내리고 `gifFpsCapped`를 켠다. `--gif-loop`가 없으면 gif에서만 0(무한)이다. `--hls-segment-seconds`는 hls에서만 쓰고 없으면 4다. `--workers auto`나 미지정은 `workers`를 `undefined`로 둔다. `--protocol-timeout`과 `--player-ready-timeout`은 1000 이상 정수(ms)다. `--max-concurrent-renders`는 1~10 정수로 `PRODUCER_MAX_CONCURRENT_RENDERS`에 싣는다 | 코드 확인 |
| R-18 | flag 조합 거절 | `--resolution`은 이름이나 alias가 프리셋에 없으면 거절하고 `--hdr`와 같이 쓰면 거절한다. `--hdr`와 `--sdr` 동시 사용, `--format hls`에서 `--hdr`나 `--gpu`, `--chroma-subsampling 444`에서 mp4가 아니거나 `--gpu`나 `--hdr`, `--crf`와 `--video-bitrate` 동시 사용, mov에서 `--crf`나 `--video-bitrate`, mov가 아닌데 `--prores-profile`, mp4가 아닌데 `--keyframe-interval`·`--max-bitrate`·`--buffer-size`, `--docker`와 `--browser-gpu`(true)를 같이 쓰면 거절한다. 거절은 모두 종료 코드 2다 | 코드 확인 |
| R-19 | `--start`·`--end` | 둘 중 하나라도 있으면 초 단위 0 이상의 유한한 수로 읽는다(`--start` 기본 0). `--end`가 `--start` 이하이면 거절한다. 형식이 mp4가 아니거나, fps가 24·25·30·60 중 정수가 아니거나, `--hdr`이면 거절한다(`--sdr`는 검사하지 않고 `--hdr` flag만 본다). 통과하면 `RenderRange{startSeconds, endSeconds?}`를 plan에 싣는다 | 코드 확인 |
| R-20 | 출력 경로와 환경 | `--output`이 있으면 `resolve(output)`, 없으면 `<project>/renders/<프로젝트 폴더 이름>_<YYYY-MM-DD>_<HH-MM-SS><확장자>`다. 확장자는 mp4 `.mp4`, webm `.webm`, mov `.mov`, gif `.gif`, png-sequence와 hls는 없음(폴더 출력)이다. batch용 템플릿은 `--output`을 그대로 쓰거나 `..._<timestamp>_{index}<확장자>`다. plan은 `--page-side-compositing=false`일 때 `HF_PAGE_SIDE_COMPOSITING=false`, `--low-memory-mode` 값(`PRODUCER_LOW_MEMORY_MODE`), `--experimental-fast-capture` 값(`PRODUCER_EXPERIMENTAL_FAST_CAPTURE`), `--frames-cache-dir`(`HYPERFRAMES_EXTRACT_CACHE_DIR`, 절대 경로로 풀이하고 비활성 alias는 그대로)를 `plan.environment`에 모으고 `applyRenderEnvironment`가 `process.env`에 쓴다 | 코드 확인 |
| R-21 | `browserGpuMode`와 린트 엄격도, 합성 | `resolveBrowserGpuForCli`는 `--docker`이면 `"software"`, `--browser-gpu`이면 `"hardware"`, `--no-browser-gpu`이면 `"software"`, 둘 다 없으면 `PRODUCER_BROWSER_GPU_MODE`가 `hardware`·`software`·`auto`일 때 그 값, 아니면 `"auto"`다. `strictAll`은 `--strict-all`, `strictErrors`는 `--strict`나 `--strict-all`이다. `hdrMode`는 `--sdr`이면 `force-sdr`, `--hdr`이면 `force-hdr`, 아니면 `auto`다. `--sdr`가 `--hdr`보다 먼저 보이지만 둘은 R-18로 동시에 쓸 수 없다. `effectiveQuiet`은 `--quiet`이거나 `--json`이다 | 코드 확인 |
| R-22 | `render`의 `run`이 시작한다 | 순서는 `createRenderPlan`(R-16) → `--docker`가 아니면 취소 범위(`createRenderCancellationScope`: 시그널 핸들러와 부모 프로세스 생존 확인 타이머) 생성 → `seedProjectAuthoringSkill`(`--skill`이 유효 slug일 때 프로젝트에 기록) → `presentRenderPlan` → `executeRenderPlan`이다. `executeRenderPlan` 안의 순서는 취소 확인 → `applyRenderEnvironment` → 단일 렌더이면 출력 폴더 생성(`makeOutputFolder`) → `--batch`이면 batch 입력 준비 → 단일 렌더이면 `--variables`·`--variables-file` 해석 → 린트(`runRenderLint`) → `--docker`가 아니면 디스크 여유 확인과 브라우저 확보 → 해상도 preflight(`--resolution`일 때만) → 렌더 슬롯 획득 → 단일 또는 batch 실행 → 슬롯 해제다. 취소 확인은 각 단계 사이에 들어 있다 | 코드 확인 |
| R-23 | 린트 단계 | `runRenderLint`는 `lintProject`를 돌리고(취소 범위가 있으면 별도 자식 프로세스) error와 warning이 모두 0이면 조용히 지나간다. 규칙(`--strict`·`--strict-all`, `blank_root_with_standalone_composition`이 `--strict` 없이도 막는 예외)은 lint-check.md R-16이 정한다. 막으면 `Cannot render: N error(s), M warning(s). <첫 finding code>: <message> Run hyperframes lint for details.`(예외는 `Cannot render: the default index.html entry is blank.`)를 오류 상자로 쓰고 `CliRuntimeError(presented)`로 종료 코드 1이다. 막지 않으면 요약(또는 `--lint-verbose`면 전체 목록)과 `Continuing render despite lint issues. Use --strict to block errors.`(`--strict`이면 `...lint warnings. Use --strict-all to block warnings.`)를 출력하고 계속한다. `effectiveQuiet`이면 출력만 생략한다 | 코드 확인 |
| R-24 | 브라우저 준비와 디스크 | `--docker`가 아니면 먼저 `tmpdir()`와 출력 폴더의 디스크 여유를 확인한다. 부족하면 오류 상자와 함께 종료 코드 1이다. 이어서 `ensureBrowser({preferManagedChrome: true})`를 부른다(`effectiveQuiet`이 아니면 `Checking browser...` spinner와 다운로드 진행률). 브라우저를 구하지 못하면(취소가 아닐 때) `Chrome not found`와 `Run: npx hyperframes browser ensure`를 쓰고 `failCommand(1, undefined, "chrome_not_found")`로 종료 코드 1이다. `--docker`는 이 단계를 건너뛰고 `browserPath`가 `undefined`다 | 코드 확인 |
| R-25 | 해상도 preflight | `--resolution`이 있을 때만 `renderTarget` HTML을 읽어 `checkRenderResolutionPreflight`를 부른다(알파 요구는 webm·mov·png-sequence, HDR 요구는 `hdrMode === "force-hdr"`). 문제가 있으면 `trackRenderPreflightRejected`를 기록하고 `Output resolution incompatible` 오류 상자와 종료 코드 1이다. 파일을 읽지 못하는 예외는 삼키고 넘어가 파이프라인이 알린다 | 코드 확인 |
| R-26 | 렌더 슬롯 | `acquireRenderSlot`이 사용자 계정당 로컬 렌더 하나만 허용하는 lock을 얻는다. 다른 렌더가 잡고 있으면 기본(`--wait`)은 `Waiting for another render to finish (...)`를 stderr에 쓰고 기다린다. `--no-wait`이면 `Another render is running for this user account` 오류 상자와 함께 `failCommand(1, error, "render_locked")`다. lock 파일을 쓸 수 없거나 stale lock을 깨지 못하거나 폴더가 거부되면 `The render slot cannot be taken`으로 종료 코드 1이다. `HYPERFRAMES_RENDER_LOCK`가 `off`·`0`·`false`이면 lock을 쓰지 않고 나란히 실행한다(`utils/renderLock.ts:57-60`). 슬롯은 `--docker`에서도 얻는다 | 코드 확인 |
| R-27 | 단일 로컬 렌더 `renderLocal` → `executeLocalRender`의 준비 | `renderLocal`은 `execute.ts`의 `RenderExecutionDependencies.renderLocal`로 주입된 `render.ts`의 함수다(`render/execute.ts`가 오케스트레이터를 직접 부르지 않는다). 준비 순서는 출력 경로를 프로젝트 기록에 등록(`registerRenderOutputOrWarn`) → 결과 비교용 `captureArtifactRevision` → 이전 렌더가 남긴 고아 브라우저 프로세스 정리(`killOrphanedProcessesForRender`, 정리한 개수가 있으면 경고) → 환경 점검 `runEnvironmentChecks`(프로젝트, 디스크 `tmpdir()`와 출력 폴더, 브라우저, Windows UNC 경로, ffmpeg·ffprobe 경로와 버전). 점검이 하나라도 실패하면 각 항목을 오류 상자로 쓰고 `failCommand(1, undefined, 마지막 실패의 code)`로 종료 코드 1이다. 경고(warn) 항목은 `quiet`가 아니면 stderr에 쓴다 | 코드 확인 |
| R-28 | mp4·hls의 H.264 인코더 선택 | `ffmpegPath`가 있고 format이 mp4나 hls이면 `detectH264EncoderModeForRender`로 인코더를 고른다. `--gpu`는 hls에서 무시된다(`gpuRequested = options.gpu && !isHls`). libx264가 없고 forced SDR이거나 hls이거나 libx265도 없으면 `... H.264 encoder unavailable` 오류 상자와 종료 코드 1이다. 그 밖의 탐지 실패는 경고만 쓰고 실제 인코딩이 진짜 오류를 알리게 둔다. libx264가 없어서 GPU로 대체하면 `gpu: true`로 바꾸고 경고한다. `--gpu`를 요청했는데 쓸 수 있는 GPU 인코더가 없으면 libx264로 인코딩한다고 경고한다 | 코드 확인 |
| R-29 | 오케스트레이터 입력 만들기와 엔진 설정 override | `producer.resolveConfig({browserGpuMode: options.browserGpuMode ?? "software", ...})`로 엔진 설정을 만든다. `??` 오른쪽은 CLI에서는 도달하지 않는다(`plan.ts`가 항상 `"auto"`·`"hardware"`·`"software"` 중 하나를 준다). `browserGpuMode === "auto"`이고 `--resolution`이 없고 `PRODUCER_FORCE_SCREENSHOT !== "true"`이면 `forceScreenshot: false`와 `beginFrameFirstFrameDeadlineMs: 20000`(`BEGIN_FRAME_FIRST_FRAME_DEADLINE_MS`)을 더한다. `--browser-timeout`, `--protocol-timeout`, `--player-ready-timeout`, `--vp9-cpu-used`는 값이 있을 때만 설정에 더한다. 이어 `producer.createRenderRequest({projectDir, outputPath, engineConfig, options})`로 요청을 만든다. 옵션은 fps, quality, format, gifLoop, hlsSegmentSeconds, workers, `useGpu`, hdrMode, crf, videoBitrate, 전달 flag 4개, videoFrameFormat, chromaSubsampling, pageMotionBlur, variables, entryFile, outputResolution(과 aspect 무관 여부), debug, resumeSegments, keepSegments, `strictness`(`--no-best-effort`이면 `"strict"`, 아니면 `"best-effort"`)다. `maxRenderMs`와 `strictVariables`는 싣지 않는다 | 코드 확인 |
| R-30 | 범위 없는 단일 렌더 실행 | 요청을 `renderConfigFromRequest(request, {logger, allowOutsideProjectAssets})`와 `createRenderJob`으로 job으로 바꾸고 `executeRenderJob(job, projectDir, outputPath, onProgress, cancellation.signal, cancellation.checkAncestors)`를 `await`한다. `quiet`가 아니면 `onProgress`가 진행률 막대(`renderProgress`)를 stdout에 쓴다. 오케스트레이터 내부 단계·재시도·취소·오류 계약은 [render-orchestration.md](render-orchestration.md) R-03, R-37, R-41, R-43을 따른다 | 코드 확인 |
| R-31 | `--start`·`--end`가 있는 렌더 | `executeRenderJob`을 부르지 않는다. `distributedConfigFromRequest`와 `renderSpan(projectDir, config, range, outputPath, {allowOutsideProjectAssets})`를 부른다. 성공하면 `outcome: "completed"`, `warnings: []`로 돌려주고 `perfSummary`·`audio_lowered`·텔레메트리 결과 지표는 만들지 않는다. 이 경로의 내부(`packages/producer/src/services/distributed/renderSpan.ts`)는 이 스펙 범위 밖이고 feature map 행 17(분산 렌더)이 소유한다 | 코드 확인 |
| R-32 | 렌더가 throw했을 때(`handleRenderError`) | 로컬 단일 렌더 오류는 telemetry 이벤트를 남기고(`trackRenderError`) 최근 렌더 목록에 실패로 기록한 뒤, batch(`throwOnError`)이면 `new Error(message)`를 다시 던진다. 아니면 Chrome 실행 실패로 분류되면 `Render failed — Chrome could not launch`(또는 Windows `chrome-headless-shell crashed at launch`)와 해결 안내, 그 밖에는 `Render failed` 오류 상자(컨테이너 안이 아니면 `Try --docker for containerized rendering` hint)를 쓰고 `failCommand()`로 종료 코드 1이다. 오류 메시지는 여러 줄이면 줄마다 terminal 제어 문자를 제거해 쓴다. 호출자가 받는 오류와 `job.error`의 차이는 render-orchestration.md R-37을 따른다 | 코드 확인 |
| R-33 | 렌더가 throw 없이 끝났다 | 곧바로 `markRenderSucceeded()`(embedded가 아닐 때)를 부른다. 이후 후처리 예외는 R-12·R-13으로 종료 코드에 영향을 주지 못한다. 이어서 프로젝트에 성공을 기록(`recordRenderSuccess`, 경고가 있으면 `completed_with_warnings`), 경고 목록을 `[code] message`로 stderr에 쓰고, `job.audioLoweredDb`가 있으면 `audio_lowered` 경고(`audioLoweredWarning`)를 CLI가 만들어 더한다. 이어 지표 telemetry, 완료 요약(`printRenderComplete`), webm 알파 손실 경고, feedback 안내 판정(`maybePromptRenderFeedback`, 표시 조건은 읽지 않았고 batch는 생략)를 부르고, 마지막에 `scheduleCliExit()`로 100ms 뒤 프로세스 종료를 요청한다. 반환값은 `{renderTimeMs, durationMs, outcome, warnings, motionBlur?, ...referenceBackground}`다. 후처리 단계는 각자 try로 감싸 실패가 렌더 결과를 바꾸지 않는다 | 코드 확인 |
| R-34 | 결과 출력 | 사람용 출력은 `quiet`가 아닐 때만 쓴다. 시작에 `◆  Rendering <name> → <output>`과 `<fps>fps · <quality> · <workers>` 줄(해상도·hls·GPU 줄은 해당할 때만), 진행 막대, 끝에 `◇  <outputPath>`와 `<파일 크기> · <소요 시간 ...>`, 파이프라인 요약, 데스크톱 앱 안내 줄이다. stdout이 TTY가 아니거나 `HYPERFRAMES_STDOUT_IS_TTY=1`이면 기계용 `@hf-progress {...}` 줄(진행 중)과 `@hf-result {"version":1,"operation":"render",...}` 한 줄(성공 때, 배경 또는 motion blur 정보가 있을 때만)을 stdout에 쓴다. `--json`은 단일 렌더에서 사람용 출력과 진행 표시를 끄고(`effectiveQuiet`) 성공 때는 JSON 문서를 쓰지 않는다. 실패 때만 R-11의 오류 envelope를 stdout에 쓴다 | 코드 확인 |
| R-35 | 취소 | `--docker`가 아닌 렌더는 SIGINT·SIGTERM·SIGHUP(환경변수 `HYPERFRAMES_RENDER_DETACHED=1`이면 SIGHUP 제외)을 받거나 조상 프로세스가 사라지면 취소 신호가 서고, 오케스트레이터에는 `cancellation.signal`로 전해진다. 취소 후 `run`의 catch가 `Render cancelled: <reason>`을 stderr에 쓰고 `recordFailure`한 뒤 `requestCliExit(1)`을 부른다. `--docker` 렌더는 취소 범위가 없다 | 코드 확인 |
| R-36 | `--docker` 렌더(`renderDocker`) | 로컬 준비 단계(R-24의 브라우저 확보, R-27의 환경 점검, R-28의 인코더 선택)는 호스트에서 하지 않는다. `docker image inspect`로 이미지 `hyperframes-render:<VERSION>`(개발 모드는 `latest`, arm64는 접미사 포함)을 확인하고 없으면 `Dockerfile.render`로 빌드한다. 이미지 빌드 실패는 오류 상자와 종료 코드 1이다. arm64 호스트에서 `--gpu`는 오류 상자 후 종료 코드 1이다. `docker run --rm --shm-size=2g -v <project>:/project:ro -v <outputDir>:/output <image> /project --output /output/<파일> --fps ... --quality ... --format ...`로 컨테이너를 띄운다. 컨테이너 안에서는 `hf-render` 스크립트가 `hyperframes render "$@"`를 다시 실행하므로 린트, 환경 점검, 오케스트레이터는 컨테이너 안의 로컬 경로에서 돈다. 호스트 쪽 린트·해상도 preflight·렌더 슬롯은 `executeRenderPlan`에서 이미 지나간 뒤다. 컨테이너가 종료 코드 0이면 `markRenderSucceeded()`·`recordRenderSuccess`·`printRenderComplete`(렌더 시간만, 영상 길이 없음)를 거쳐 `{renderTimeMs}`만 돌려준다. 0이 아니면 `DockerRenderExitError`가 `handleRenderError(... "Check Docker is running: docker info")`로 가서 R-32와 같은 `Render failed` 오류 상자와 종료 코드 1이다 | 코드 확인 |
| R-37 | `--docker`가 컨테이너로 넘기는 값 | `buildDockerRunArgs`가 컨테이너 CLI에 `--output`, `--fps`, `--quality`, `--format`을 항상 넘기고, 값이 있을 때 `--gif-loop`, `--hls-segment-seconds`, `--workers`, `--crf`, `--vp9-cpu-used`, `--video-bitrate`, `--prores-profile`, `--start`·`--end`, `--keyframe-interval`, `--max-bitrate`, `--buffer-size`, `--video-frame-format`(`auto`가 아닐 때), `--chroma-subsampling 444`, `--page-motion-blur`, `--quiet`, `--debug`, `--no-best-effort`, `--gpu`, `--hdr`·`--sdr`, `--variables <JSON>`, `--composition`, `--resolution`, `--no-page-side-compositing`, `--experimental-fast-capture`, `--browser-timeout`(초), `--protocol-timeout`, `--player-ready-timeout`을 붙인다. `--browser-gpu`가 아니면 항상 `--no-browser-gpu`를 붙인다. 넘기지 않는 flag는 `--resume`, `--keep-segments`, `--strict`·`--strict-all`, `--lint-verbose`, `--frames-cache-dir`, `--low-memory-mode`, `--max-concurrent-renders`, `--skill`, `--wait`, `--json`, `--variables-file`(호스트가 읽어 `--variables`로 바꿈)이고, 그 값들이 만드는 `plan.environment`는 호스트 프로세스 환경에만 써지며 `docker run -e`에는 네트워크 허용 환경변수 목록(`FORWARDED_RENDER_NETWORK_ENV`)만 실린다. `RenderOptions.pageSideCompositing`·`experimentalFastCapture`는 `--docker`일 때만 옵션으로 싣는다(로컬은 환경변수 경로) | 코드 확인 |
| R-38 | `--batch <file>` 입력 준비 | `--batch`가 있으면 `--variables`·`--variables-file`과 함께 쓸 수 없고(R-16), `--batch-concurrency`와 `--batch-fail-fast`는 `--batch` 없이 쓸 수 없다. 모두 `failUsage` 종료 코드 2다. `prepareBatchRender`는 린트보다 먼저 파일을 읽어 JSON 배열(또는 `{"rows":[...]}`)인지, 비어 있지 않은지, 행이 객체인지 검사하고, 행마다 출력 템플릿의 `{index}`와 `{<변수 이름>}`를 채워 경로를 만든다(값이 없거나 string·number·boolean이 아니면 거절). 출력이 템플릿 폴더 밖이거나 서로 겹치거나 `manifest.json`이 입력 파일과 같아지면 거절한다. 변수는 행마다 프로젝트 스키마로 검사하고 `--strict-variables`이면 불일치가 오류다. 입력 오류는 `exitBatchRenderInputError`가 오류 상자와 `failCommand()`(종료 코드 1)로 끝낸다 | 코드 확인 |
| R-39 | batch 실행 | 렌더 슬롯 안에서 `runBatchRender`가 행 전체를 `pending`으로 둔 `manifest.json`(공통 출력 폴더)을 쓰고, 동시에 `--batch-concurrency`(기본 1)개까지 행을 돌린다. 행마다 상태를 `running` → `completed`·`failed`로 manifest에 원자적으로 다시 쓰고, 각 행은 단일 렌더와 같은 `renderLocal`이나 `renderDocker`를 `throwOnError`, `skipFeedback`, `exitAfterComplete: false`로 부른다. 행 실패는 다른 행을 멈추지 않는다. `--batch-fail-fast`이면 첫 실패 뒤 새 행을 시작하지 않고 `pending` 행을 `skipped`(`Skipped after --batch-fail-fast.`)로 바꾼다. 하나라도 `failed`이면 `setCommandExitCode(1)`이다. `--json`이면 끝에 `{"type":"batch-complete","manifestPath","total","completed","failed","skipped","rows"}` 한 줄을 stdout에 쓴다. 배치의 린트·브라우저·해상도 preflight·슬롯은 한 번만 거친다 | 코드 확인 |
| R-40 | `init` 시작, 모드 결정 | `--template`이나 `-V`가 있으면 새 이름을 알리는 안내를 stderr에 쓰고 종료 코드 2다. `--resolution` 값이 프리셋이 아니면 `Invalid --resolution: "<값>". Use one of: ...`을 stderr에 쓰고 종료 코드 2다. 모드는 `nonInteractive = --non-interactive \|\| --agent`, `interactive = !nonInteractive && !isUnattended()`다. 터미널이 아니거나 CI이거나 코딩 에이전트가 돌리거나 `HYPERFRAMES_AGENT=1`이면 `isUnattended()`가 true라 flag 없이도 비대화 모드로 간다. `--skip-skills`는 flag나 `HYPERFRAMES_SKIP_SKILLS=1`일 때 켜진다 | 코드 확인 |
| R-41 | 템플릿 선택 `resolveScaffoldTemplateId(--example, --video나 --audio가 있는가)` | `--example`이 `agent`이면 `blank`로 본다. `--example`이 있고 `blank`가 아니면 그 이름이다. 없고 `--video`나 `--audio`가 있으면 `from-file`, 그 밖에는 `blank`다. 비대화 모드는 항상 이 함수로 정한다. 대화 모드는 `--example`이나 `--video`·`--audio`가 있을 때만 이 함수로 정하고, 아니면 목록에서 고르게 한다(R-44) | 코드 확인 |
| R-42 | 비대화 모드의 순서와 검증 | 이름은 `name` 없으면 `my-video`, 대상 폴더는 `resolve(name)`이다. ① 폴더 이름 한 마디가 255(Linux는 UTF-8 바이트, 그 밖은 문자 수)를 넘으면 메시지 후 종료 코드 1. ② 대상 폴더에 `hyperframes.json`과 이미 같은 파일인 원본 미디어(`--video`·`--audio`로 준 파일이 폴더 안에 있는 경우)를 뺀 항목이 하나라도 있으면 `Directory already exists and is not empty: <name>`와 종료 코드 1. ③ `--video`와 `--audio` 동시 사용은 `Cannot use --video and --audio together`와 종료 코드 2. ④ 파일이 없으면 `Video file not found: ...`나 `Audio file not found: ...`와 종료 코드 1. 이 검증이 모두 끝난 뒤에야 `mkdirSync(destDir, {recursive: true})`를 한다. 그래서 위 실패는 빈 폴더를 남기지 않는다 | 코드 확인 |
| R-43 | 비대화 모드의 미디어 처리와 scaffold | `--video`이면 R-47의 비디오 처리를 하고 `Video: <w>x<h>, <초>s`를 출력한다. `--audio`이면 파일을 폴더로 복사(이미 같은 파일이면 생략)하고 길이를 읽는다. 원본이 있고 `--skip-transcribe`가 아니면 whisper를 확보해 전사하고(`Transcribed: N words`), 실패하면 `Transcription skipped: <이유>`만 출력하고 계속한다. 이어 `scaffoldProject`(R-45)를 부른다. 실패하면 `Failed to scaffold example "<id>": <이유>`와 `Use --example blank for offline use.`를 쓰고 종료 코드 1이다. 폴더는 이미 만들어졌으므로 정리하지 않는다(부분 생성물이 남을 수 있다). 성공하면 `finishScaffold`가 telemetry를 기록하고 `transcript.json`이 있으면 자막 HTML을 갱신한다. 마지막에 `Created <name>/`과 점으로 시작하지 않는 항목 목록, 스킬 단계(R-48), 시작 안내 6단계를 출력하고 종료 코드 0이다 | 코드 확인 |
| R-44 | 대화 모드의 질문 순서 | 배너와 `Create a new HyperFrames project` 뒤에 ① 이름(positional이 있으면 생략, 기본 `my-video`) ② 폴더가 비어 있지 않으면 `Overwrite?`(기본 아니오, 취소나 아니오이면 `Setup cancelled.`와 종료 코드 0) ③ `--video`면 코덱이 웹 비호환일 때 `Transcode to H.264 MP4 ...?`(예·아니오) ④ 원본(`--video`·`--audio`)이 있으면 `Generate captions from audio?`(기본 예) ⑤ `--example`·`--video`·`--audio`가 모두 없을 때만 `Pick an example`(`blank`가 기본, 번들 `blank`와 registry의 example 목록, 원격 항목은 `(download)` 표시) 순이다. 질문 취소(Ctrl+C)는 `Setup cancelled.`와 종료 코드 0이다. 마지막에 `Opening studio preview...`를 쓰고 `preview <destDir>`를 실행한다. 대화 모드는 `--video`와 `--audio`를 같이 받아도 오류 없이 `--video`만 쓰고(`if (videoFlag) ... else if (audioFlag)`), `--skip-transcribe`를 읽지 않고 질문으로 묻는다 | 코드 확인 |
| R-45 | `scaffoldProject`(두 모드 공통)가 만드는 것 | 순서는 대상 폴더 생성 → 템플릿 복사 → 미디어 자리표시자 치환(R-46) → `--tailwind`이면 모든 HTML에 Tailwind 스크립트 삽입 → 캔버스 크기 치환 → `meta.json` → `hyperframes.json`(없을 때만) → `package.json`(없을 때만) → 공유 파일 복사다. 템플릿은 `src/templates/<id>/index.html`(dev) 또는 `dist/templates/<id>`(배포), 개발 모드는 repo 루트 `registry/examples/<id>`에도 있으면 그 디렉터리를 `copyDirSync`로 복사한다. 없으면 `fetchRemoteTemplate`이 registry에서 내려받고(의존 항목 먼저 설치, 호환성 경고는 stderr), 설치 뒤 `index.html`이 없으면 오류를 던진다. `meta.json`은 `{id, name, createdAt}`이고 `id`와 `name`은 입력한 `name` 그대로다. `hyperframes.json`은 `DEFAULT_PROJECT_CONFIG`(registry URL, paths: `compositions`, `compositions/components`, `assets`, `media.autoProxy: true`)이고 `--skill`이 유효 slug이면 `authoringSkill`을 더한다. `package.json`은 `{name, private: true, type: "module", scripts}`로 `dev`는 `preview`, `check`, `render`, `publish`를 `npx --yes hyperframes@<VERSION> <명령>`으로 부르고(개발 빌드는 버전 없이 `hyperframes`) 이미 있으면 건드리지 않는다. `_shared/CLAUDE.md`와 `AGENTS.md`(두 파일은 같은 내용)를 항상 덮어쓰며 복사한다 | 코드 확인 |
| R-46 | 미디어 자리표시자와 변형 | `--video`이면 `__VIDEO_SRC__`를 비디오 파일 이름(URL 인코딩, `#`·`?`는 퍼센트 인코딩)으로 바꾸고 `<video>`의 `muted`·`data-has-audio`를 지운 뒤 소리가 있으면 `data-has-audio="true"`, 없으면 `muted`를 붙인다. `__AUDIO_SRC__` 슬롯은 지운다. `--audio`이면 `<video>` 슬롯을 지우고 `__AUDIO_SRC__`를 오디오 파일 이름으로 바꾼다. 둘 다 없으면 세 슬롯을 모두 지운다. `__VIDEO_DURATION__`은 원본 길이(소수 둘째 자리까지 반올림)로, 길이를 모르면 `10`으로 바꾼다. `--resolution`이 있으면 해당 프리셋 크기로, 없고 `from-file`이면 클립 모양(짧은 변 1080, 비율 유지, 짝수 반올림)으로 `data-width`·`data-height`, body·`html` CSS 크기, `viewport` meta를 모든 HTML에서 정규식으로 바꾼다(클립이 16:9 1920x1080이면 그대로 둔다). `<html data-resolution="<프리셋>">`는 프리셋 이름으로 바꿀 때만 넣거나 고친다. `--tailwind`이면 `@tailwindcss/browser@4.2.4` 스크립트(고정 버전, integrity 해시 포함)와 `window.__tailwindReady` promise를 `</head>` 앞(없으면 앞쪽)에 한 번만 넣는다. 외부 `.css` 안의 크기는 바꾸지 않는다 | 코드 확인 |
| R-47 | 비디오 처리 `handleVideoFile` | `ffprobe`로 길이·크기·fps·오디오 유무·코덱을 읽는다. 없으면 `1920x1080, 5s, 30fps`, 오디오 있음, `h264`로 가정하고 경고한다. 코덱이 `h264`·`vp8`·`vp9`·`av1`이 아니고 `--keep-original`이 아니며 ffmpeg가 있으면 비대화 모드는 자동으로, 대화 모드는 질문 후 H.264(crf 18, aac 192k) MP4로 변환한다. 이름은 `<stem>.mp4`가 비어 있으면 그것, 아니면 `<stem>.h264.mp4`, `<stem>.h264-2.mp4` 순으로 빈 이름을 고른다. 변환이 실패하면 원본을 복사한다. ffmpeg가 없으면 원본을 복사하고 설치 안내를 쓴다. 웹 호환 코덱이거나 `--keep-original`이면 그대로 복사한다 | 코드 확인 |
| R-48 | 스킬 설치 단계 | `--skip-skills`나 `HYPERFRAMES_SKIP_SKILLS=1`이 아니면 scaffold 뒤에 `updateSkills({onlyMissing: true, cwd: destDir})`를 부른다. 없는 코어 스킬만 설치하고 이미 설치된 스킬은 건드리지 않는다. GitHub에 닿지 못하면 `Skills freshness unverified (offline?)`를 쓴다. 호출이 throw해도 `AI coding skills install skipped: <이유>`만 쓰고 `init`은 성공으로 끝난다. skip이면 시작 안내에 `npx hyperframes skills update`를 쓰는 문구가 나온다. 설치 위치·대상 에이전트 결정은 행 14가 소유하고 읽지 않았다 | 코드 확인 |
| R-49 | 이미 존재하는 폴더와 부분 생성물 | 기존 폴더가 비어 있지 않을 때 비대화 모드는 거절(R-42), 대화 모드는 사용자가 덮어쓰기를 허용해야 계속한다. 허용해도 폴더를 비우지 않는다. 템플릿 복사는 같은 이름의 파일만 덮어쓰고 나머지 기존 파일은 남는다. scaffold 도중(템플릿 복사·원격 다운로드·치환) 실패하면 이미 만든 폴더와 복사된 파일을 지우지 않는다. 검증 실패(R-42의 ①~④)는 폴더를 만들기 전이라 아무것도 남지 않는다. 비디오·오디오 복사 뒤 scaffold가 실패해도 복사한 미디어는 남는다 | 코드 확인 |
| R-50 | 등록 명령 56개 중 이 스펙이 직접 다루지 않는 50개 | 이름, 한 줄 동작(`meta.description`이나 `help.ts`의 설명 문자열), 소유 행, 진입 파일을 1.3의 "명령 계열 표"에 둔다. 동작 문장은 선언된 설명 문자열이고 각 명령의 구현은 소유 행 스펙이 다룬다. 소유 행이 feature map에 없는 명령은 "미배정"으로 표시한다. 이 스펙이 개념 수준으로 직접 다루는 것은 `init`, `render`와 R-51~R-54의 네 명령이다 | 코드 확인 |
| R-51 | `doctor [--json]` | `runEnvironmentChecks({includeBrowser: true})`와 별도 점검(Version, CLI binary, Node.js, CPU, Memory, Disk, Frames cache, Archive extractor, Settings lock, Linux만 `/dev/shm`, Environment, whisper-cpp, TTS(Kokoro), BGM(MusicGen), 선택 패키지들, FFmpeg·브라우저 등 환경 점검 결과, Docker 설치와 실행 여부)를 순서대로 돌려 `✓`·`✗`와 hint를 출력한다. `--json`은 redact한 보고서를 stdout에 쓰고 끝난다. 점검이 하나 실패해도 종료 코드는 0이다. 종료 코드로 건강 상태를 알리지 않는 이유는 소스 주석이 "새 버전이 나오면 `checkVersion`이 실패해 CI가 깨지기 때문"이라고 적었다 | 코드 확인 |
| R-52 | `info [dir] [--json] [--media]` | `resolveProject(dir)`로 프로젝트를 정하고 `index.html`을 파싱해 해상도(루트 `data-width`·`data-height`, 없으면 `data-resolution` 프리셋 크기), 길이, 요소 수, 트랙 수(고유 `zIndex` 개수), 요소 종류별 개수, 폴더 총 크기를 출력한다. `--media`이면 렌더가 듣는 클립 목록을 더한다. `index.html`이 없으면 R-16과 같이 오류 상자 후 종료 코드 1이다. `--json`은 `withMeta({...})` 객체를 stdout에 쓴다 | 코드 확인 |
| R-53 | `docs [topic]` | 인자가 없으면 주제 목록을 쓰고 종료 코드 0이다. 모르는 주제는 `Unknown topic: <topic>`과 목록을 stderr에 쓰고 종료 코드 2다. 알면 `docsDir()` 아래 해당 마크다운 파일을 터미널용으로 렌더링해 쓴다. 파일이 없으면 `Doc file not found: <경로>`와 종료 코드 1이다 | 코드 확인 |
| R-54 | `compositions [dir] [--json]` | `index.html`의 컴포지션을 `parseCompositions`로 찾아 `id`, 길이(초), 너비·높이, 요소 수, 서브 컴포지션이면 원본 파일을 표로 쓴다. 없으면 `no compositions found`를 쓰고 종료 코드 0이다. `--json`은 비어 있어도 `withMeta({compositions})`를 stdout에 쓴다. `index.html`이 없으면 R-16과 같이 종료 코드 1이다 | 코드 확인 |
| R-55 | `preview`의 공통 전처리 게이트 | `preview` 로더는 `assertStudioWorkspaceBuilt()`를 먼저 기다린다. 개발 모드(`import.meta.url` 경로가 `.ts`로 끝날 때)가 아니면 아무것도 하지 않는다. 개발 모드이면 레포 루트의 studio 워크스페이스 빌드가 최신인지 `checkStudioWorkspaceBuild`로 검사하고 문제가 있으면 안내를 stderr에 쓴 뒤 `CliRuntimeError("Studio workspace build check failed", {exitCode: 1, presented: true})`로 종료 코드 1이다. 빌드된 배포 패키지에서는 게이트가 작동하지 않는다 | 코드 확인 |
| R-56 | 무인 실행(`isUnattended()`)에서 명령이 `ui/prompts.js`의 `confirm`·`select`·`text`·`password`를 부른다 | `CliUsageError("This command asks a question, and this run cannot answer a prompt.", code: "prompt_unavailable", hint: "Pass the answer as a flag; ...")`를 던져 종료 코드 2다(`--json`이면 R-11의 envelope에 이 code가 실린다). `spinner()`는 무인이면 시작·종료 문구를 stderr에 한 줄씩 쓰는 선 출력으로 바뀐다. 확인이 필요한 명령이 `confirmationRequired(command, hint)`를 부르면 `code: "confirmation_required"`로 같은 종류의 오류다. 이 모듈이 `@clack/prompts`를 import하는 유일한 파일이라는 점은 주석이 lint 규칙으로 강제한다고 적었다(lint 규칙 파일은 열지 않았다) | 코드 확인 |

- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-08 | 인자 없이 `hyperframes`만 실행하면 stderr에 무엇이 나오는가 | root help를 보여 줄지, citty 기본 오류 문장만 둘지 정해야 한다 | citty 0.2.x 설치본(`packages/cli/package.json:62`의 `^0.2.1`)의 `runCommand`를 읽거나 `node packages/cli/dist/cli.js`를 인자 없이 실행해 stderr를 본다 |
| U-02 | R-50 | 소유 행이 feature map에 없는 명령(`snapshot`, `inspect`, `keyframes`, `compare`, `diff`, `clean`, `browser`, `upgrade`, `update`, `feedback`, `telemetry`, `open`, `catch-up`, `templates` 등)을 어느 행에 둘 것인가 | 구현자가 이 명령들을 누가 소유하는지 모르면 다음 스펙에 빠진다. 이 스펙의 표는 "미배정"으로 둔다 | 메인이 feature map을 보정하거나 각 명령 구현을 열어 소유를 정한다 |

### 1.5 필수 코드 참조
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `packages/cli/src/templates/blank/index.html:1-61` | `blank` 템플릿 전체다. `<html>`, viewport meta `width=1920, height=1080`, GSAP 3.15.0 CDN 스크립트, CSS 변수 3개(`--ground`, `--ink`, `--font-display`), 루트 `#root`에 `data-composition-id="main"`·`data-start="0"`·`data-duration="10"`·`data-width="1920"`·`data-height="1080"`, 자식 `<h1 id="title" class="clip" data-start="0" data-duration="10" data-track-index="0">Title</h1>`, `gsap.timeline({paused: true})`를 `window.__timelines["main"]`에 등록하고 `tl.seek(0)`을 부른다. 애니메이션은 없다 | R-45 |
| C-02 | `packages/cli/src/commands/initMedia.ts:1-72` `patchMediaPlaceholders` | 자리표시자 `__VIDEO_SRC__`·`__AUDIO_SRC__`·`__VIDEO_DURATION__` 치환 규칙 전체(R-46의 글보다 정확한 정규식) | R-46 |
| C-03 | `packages/cli/src/commands/init.ts:358-404` `toPackageName`, `buildPackageScripts`, `writeDefaultPackageJson` | 프로젝트 이름에서 `package.json`의 `name`을 만드는 정규화와 `scripts` 4개 | R-45 |
| C-04 | `packages/cli/src/commands/init.ts:206-214`, `601-660` `clipFrame`, `applyCanvasSize` | 클립 모양에서 캔버스 크기를 정하는 식과 HTML 안 크기 치환 정규식 | R-46 |
| C-05 | `packages/cli/src/commands/init.ts:69-74` `resolveScaffoldTemplateId` | 템플릿 id 결정 3분기 | R-41 |
| C-06 | `packages/cli/src/commands/init.ts:288-324` `holdsFilesBesideProjectConfigOrSources`, `MEDIA_THE_SCAFFOLD_NEVER_WRITES` | 폴더가 "비어 있지 않다"의 판정(`hyperframes.json`과 같은 파일인 원본 미디어는 제외하는 부분) | R-42, R-49 |
| C-07 | `packages/cli/src/commands/render/plan.ts:43-49`, `63-71`, `706-716` | 품질 별칭 표, 확장자 표, `resolveBrowserGpuForCli` | R-17, R-20, R-21 |

### 1.6 수락 사례
출처: 모두 구현에서 도출

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | Node 20에서 `hyperframes render --json` | stderr에 `HyperFrames requires Node.js >= 22 (current: 20.x.y)...`, stdout에 `{"ok":false,"error":{"code":"node_version_unsupported",...}}`, 종료 코드 1. `dist/cli.js`는 로드되지 않는다 |
| T-02 | R-03 | `hyperframes --version`, `hyperframes -V`, `hyperframes render --version` | 앞의 둘은 `VERSION` 한 줄을 stdout에 쓰고 종료 코드 0이다. 셋째는 빠른 경로가 아니다(첫 인자가 `render`). 이후는 `render` 명령 경로이고 citty가 `--version`을 어떻게 다루는지는 읽지 못했다 |
| T-03 | R-07, R-10 | `hyperframes rendr` (현재 폴더에 `rendr` 디렉터리 없음) | stderr에 `Unknown command: rendr`, 제안 줄(`Did you mean 'hyperframes render'?` 꼴), `Run 'hyperframes --help' to list every command.`, 종료 코드 2. 해당 명령 모듈은 import되지 않는다 |
| T-04 | R-06 | 현재 폴더에 `my-video/` 디렉터리가 있고 `hyperframes my-video` | `hyperframes open my-video`로 바뀌어 실행된다. 같은 이름의 등록 명령(예: 폴더 `render`)이 있으면 명령이 실행되고 폴더는 열리지 않는다 |
| T-05 | R-15 | `hyperframes render --out x.mp4` | `Unknown flag: --out`, hint `Did you mean --output?`, 종료 코드 2. 기본 출력 경로로 렌더되지 않는다 |
| T-06 | R-11 | `hyperframes render --json --fps 999`(index.html 있음) | 사람용 출력 없이 오류 상자 문구가 stderr에 있고, stdout에 `{"ok":false,"error":{"code":"usage_error","message":...}}` 한 줄, 종료 코드 2 |
| T-07 | R-12 | `render`가 파일을 저장하고 `markRenderSucceeded()`를 부른 뒤 `printRenderComplete`에서 예외가 난다 | 후처리 예외는 삼켜지고(`runPostRenderStep`), 종료 코드는 0이다. 이후 uncaught 예외가 나도 `Late uncaughtException`만 stderr에 쓰고 0이다 |
| T-08 | R-18 | `hyperframes render --crf 18 --video-bitrate 10M` | `Conflicting encoder settings: Use either --crf or --video-bitrate, not both.` 오류 상자, 종료 코드 2. 린트·브라우저는 시작하지 않는다 |
| T-09 | R-19 | `hyperframes render --start 5 --end 3` / `--start 2 --format webm` | 앞은 `Invalid range`, 뒤는 `A range renders what chunked renders can`와 `--start/--end render MP4 only, not webm.`, 모두 종료 코드 2 |
| T-10 | R-20, R-17 | 프로젝트 `promo`에서 `hyperframes render --quality looks --format gif --fps 60`(2026-11-17 10:00:00) | `fps`는 30으로 내려가고 `GIF output is capped at 30fps.` 안내가 나온다. 출력은 `<project>/renders/promo_2026-11-17_10-00-00.gif`, gif-loop는 0이다. `crf`는 16이다 |
| T-11 | R-23 | `index.html` 루트가 비어 있고 서브 컴포지션 파일만 있는 프로젝트에서 `hyperframes render` | `blank_root_with_standalone_composition` 때문에 `--strict` 없이도 `Cannot render: the default index.html entry is blank.`, 종료 코드 1 |
| T-12 | R-26 | 다른 렌더가 lock을 잡은 상태에서 `hyperframes render --no-wait` | `Another render is running for this user account`, 종료 코드 1. `--no-wait` 없이 실행하면 `Waiting for another render to finish (...)`를 stderr에 쓰고 기다린 뒤 시작한다 |
| T-13 | R-29 | 로컬 Linux에서 `--docker`, `--resolution`, `--no-browser-gpu` 없이 렌더 | `browserGpuMode`는 `"auto"`이므로 엔진 설정에 `forceScreenshot: false`와 `beginFrameFirstFrameDeadlineMs: 20000`이 더해진다. `--resolution 4k`를 주거나 `PRODUCER_FORCE_SCREENSHOT=true`이면 더해지지 않는다 |
| T-14 | R-39 | `--batch rows.json --batch-fail-fast`에서 두 번째 행이 실패(행 3개, 동시성 1) | 첫 행 `completed`, 둘째 `failed`, 셋째 `skipped`(`Skipped after --batch-fail-fast.`). `manifest.json`에 `completed: 1, failed: 1, skipped: 1`. 종료 코드 1 |
| T-15 | R-42, R-49 | 비어 있지 않은 폴더 `demo/`에서 `hyperframes init demo --non-interactive` | `Directory already exists and is not empty: demo`, 종료 코드 1, 폴더 내용은 그대로다 |
| T-16 | R-42 | `hyperframes init x --non-interactive --video missing.mp4` | `Video file not found: missing.mp4`, 종료 코드 1, 폴더 `x/`는 만들어지지 않는다 |
| T-17 | R-41, R-45, R-46 | 빈 곳에서 `hyperframes init my-video --non-interactive --skip-skills` | `my-video/`에 `index.html`(C-01과 같되 `__*` 자리표시자 없음), `meta.json`({id:"my-video", name:"my-video", createdAt}), `hyperframes.json`, `package.json`(`name:"my-video"`, scripts 4개), `CLAUDE.md`, `AGENTS.md`가 생기고 종료 코드 0이다. 스킬 설치는 하지 않는다 |
| T-18 | R-46 | `init clip --video a.mp4 --resolution portrait`(a.mp4는 h264, 소리 있음) | 템플릿 `from-file`, 비디오는 폴더로 복사되고 `<video src="a.mp4" data-has-audio="true">`, `data-width="1080"`, `data-height="1920"`, `<html data-resolution="portrait">`다. `__AUDIO_SRC__` 슬롯은 지워진다 |
| T-19 | R-44 | 터미널에서 `hyperframes init`(flag 없음) | 이름 질문 → (빈 폴더이면 덮어쓰기 질문 생략) → 예제 선택 → 생성 → 스킬 단계 → `Opening studio preview...`로 `preview`가 실행된다. CI나 에이전트 안에서는 같은 명령이 비대화 모드로 `my-video/`를 만든다(R-40) |
| T-20 | R-56 | `CI=1`에서 코드 경로가 `clack.confirm`을 부른다 | `prompt_unavailable` usage 오류, 종료 코드 2 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | `packages/cli/bin/hyperframes.mjs:1-27`, `packages/cli/package.json:28-31`, `107-109`, `src/runtimeVersion.ts:1-12` | `bin` 파일과 `runtimeVersionError`를 읽었다. 실행은 하지 않았다. warm check(`warmCheckClient`)의 내부는 열지 않았다 |
| R-02 | `src/cli.ts:55-59` | 코드 확인 |
| R-03 | `src/cli.ts:60-69`, `src/version.ts:1-5` | 코드 확인. `__CLI_VERSION__`을 주입하는 위치(`tsup.config.ts`)는 열지 않았다. 번들에서 주입한다는 것은 선언 이름으로만 안다 |
| R-04 | `src/cli.ts:71-77`, `src/utils/dotEnv.ts:5-23`, `115-132` | 코드 확인. `applyDotEnv`가 이미 설정된 환경변수를 덮는지는 읽지 않았다 |
| R-05 | `src/cli.ts:144-203`, `126-138`, `226-228`, `src/utils/command-failure-tracking.ts:15-80` | 코드 확인. 개수는 `awk 'NR>=144&&NR<=203' src/cli.ts \| grep -oE '^  ("[a-z-]+"\|[a-z]+): '`로 56개를 세고 `comm`으로 이름 집합을 비교했다. help `GROUPS`에 없는 등록 명령은 `events`, `figma`, `layout`, `media-use`, `play`, `usage` 6개다(help 목록 `src/help.ts:19-170`에 이 이름이 없음을 `grep`으로 확인). 문서(작업 지시)의 "약 55개"는 56개로 고친다 |
| R-06 | `src/cli.ts:204-224`, `src/utils/projectShortcut.ts:1-59` | 코드 확인 |
| R-07 | `src/cli.ts:599-639`, `648-657`, `src/utils/didYouMean.ts`(함수 이름만 확인, 본문 미열람), `src/utils/commandResult.ts:11-30` | 코드 확인. 제안 문구를 고르는 `closestMatch`·`commandRedirect` 내부는 열지 않았다 |
| R-08 | `src/cli.ts:230-237`, `665-683`, `685-720`. citty는 `node_modules`에 없다(`ls node_modules/citty` 결과 없음) | 추론. `E_NO_COMMAND` 처리 줄은 읽었지만 citty가 인자 없는 실행에서 그 코드를 던지는지는 확인하지 못했다. U-01 |
| R-09 | `src/cli.ts:122`, `229-240`, `632-646`, `src/help.ts:19-248`, `src/utils/commandUsageResolution.ts:19-42` | 코드 확인. `_examples.ts`의 예시 내용은 열지 않았다 |
| R-10 | `src/cli.ts:665-722`, `src/utils/commandResult.ts:1-110` | 코드 확인 |
| R-11 | `src/cli.ts:693-719`, `src/utils/jsonError.ts:90-165`, `src/utils/reject-unknown-flags.ts:10-14` | 코드 확인. "`--json`은 전역 flag가 아니다"는 `reject-unknown-flags.ts` 주석과 `ALWAYS_KNOWN` 집합으로 확인했고 각 명령이 `json` arg를 선언하는지는 `render`, `doctor`, `info`, `compositions`만 열어 확인했다 |
| R-12 | `src/cli.ts:365-398`, `423-430`, `utils/render-success-state.ts`(함수 이름만) | 코드 확인. `markRenderSucceeded()` 호출 위치는 `render.ts:966`(docker), `1283`(로컬), `1381`(범위 렌더)이고 R-31, R-33, R-36이 다룬다 |
| R-13 | `src/cli.ts:14-31`, `430-452`, `498-516`, `553-590` | 코드 확인 |
| R-14 | `src/cli.ts:260-361` | 코드 확인. 업데이트 확인·telemetry 모듈 내부(`telemetry/index.ts`, `utils/updateCheck.ts`, `utils/autoUpdate.ts`)는 열지 않았다. 게이트 조건만 쓴다 |
| R-15 | `src/utils/command-failure-tracking.ts:36-80`, `src/utils/reject-unknown-flags.ts:10-14`, `116-130`, `215-245`, `src/utils/reject-extra-positionals.ts:66-103` | 코드 확인. `ACCEPTS_EXTRA_POSITIONALS`와 `JOINS_EXTRA_POSITIONALS`에 든 명령 이름 목록은 열지 않았다 |
| R-16 | `render/plan.ts:324-634`, `utils/project.ts:32-89` | 코드 확인. 단계 순서는 `createRenderPlan` 본문을 위에서 아래로 읽은 순서다. `resolveCompositionEntryArg`·`resolveDefaultFpsArg`·`parseFps`·`normalizeResolutionFlag`·`parseDeliveryFlags`의 내부 규칙은 열지 않았다(이름과 호출 위치만) |
| R-17 | `render/plan.ts:43-49`, `325-327`, `341-353`, `377-398`, `458-480`, `503-520` | 코드 확인. `parseGifLoopArg`, `parseHlsSegmentSecondsArg` 내부(범위 0-65535, 1-60은 flag 설명 근거)는 열지 않았다 |
| R-18 | `render/plan.ts:405-455`, `298-323`, `555-566`, `568-631` | 코드 확인 |
| R-19 | `render/plan.ts:221-267`, `633` | 코드 확인. `DISTRIBUTED_FPS`(24·25·30·60)는 정의를 열지 않고 `--end` flag 설명(`render.ts:253-255`)으로 안다 |
| R-20 | `render/plan.ts:63-71`, `484-501`, `545-553`, `696-698` | 코드 확인. 타임스탬프는 `packages/core/src/utils/renderOutputTimestamp.ts:2-7`이 로컬 시각으로 `YYYY-MM-DD_HH-MM-SS`를 만든다 |
| R-21 | `render/plan.ts:555-558`, `706-716`, `636-694` | 코드 확인 |
| R-22 | `render.ts:492-523`, `render/execute.ts:70-120` | 코드 확인. `seedProjectAuthoringSkill`의 내부는 열지 않았다 |
| R-23 | `render/execute.ts:53-69`, `284-359`. 규칙은 lint-check.md R-16 | 코드 확인 |
| R-24 | `render/execute.ts:232-282`, `browser/manager.ts`·`browser/preflight.ts`는 열지 않았다 | 코드 확인. 디스크 기준치와 `ensureBrowser` 내부는 열지 않았다 |
| R-25 | `render/execute.ts:361-383`, `render.ts:687-715` | 코드 확인. `checkRenderResolutionPreflight`가 정하는 비호환 규칙(해상도 배수 등)은 열지 않았다 |
| R-26 | `render/renderSlot.ts:1-55`, `utils/renderLock.ts:57-60` | 코드 확인. lock 파일 위치·소유 판단은 열지 않았다 |
| R-27 | `render.ts:1027-1085`, `852-860`(`registerRenderOutputOrWarn`의 이름만 확인), `render/execute.ts:20-40` | 코드 확인. `runEnvironmentChecks`, `captureArtifactRevision`, `killOrphanedProcessesForRender`의 내부는 열지 않았다 |
| R-28 | `render.ts:1086-1153` | 코드 확인. `detectH264EncoderModeForRender` 내부는 열지 않았다 |
| R-29 | `render.ts:1154-1230`, `714`(`BEGIN_FRAME_FIRST_FRAME_DEADLINE_MS = 20_000`), `render/plan.ts:706-716`. capture-encode-engine.md R-03·R-04와 같은 사실이다 | 코드 확인. `createRenderRequest`의 입력 검증은 producer 쪽이며 render-orchestration.md R-41, R-46이 다룬다. `maxRenderMs`·`strictVariables`가 요청에 없음은 위 `options` 객체에 키가 없음으로 확인했다 |
| R-30 | `render.ts:1231-1260` | 코드 확인 |
| R-31 | `render.ts:1217-1232`(분기), `1348-1400` | 코드 확인. `renderSpan` 내부는 열지 않았다 |
| R-32 | `render.ts:1923-1985`, `1907-1922`, `1892-1905` | 코드 확인. 감지 함수 `sandboxDeniedRemediation` 등 내부는 열지 않았다 |
| R-33 | `render.ts:1261-1346`, `utils/audioLoweredWarning.ts:1-12`, `utils/commandResult.ts:149-186`. audio-mix-fx.md R-19와 같은 사실이다 | 코드 확인. `recordRenderSuccess`, `trackRenderMetrics`, `maybePromptRenderFeedback` 내부는 열지 않았다 |
| R-34 | `render/present.ts:11-83`, `render.ts:2152-2205`, `ui/renderResult.ts:14-25`, `ui/progress.ts:6-26` | 코드 확인. "단일 렌더 `--json` 성공 때 JSON이 없다"는 `effectiveQuiet`이 true라 `printRenderComplete`와 `onProgress`가 모두 꺼지고 `renderMachineResult(result, quiet)`도 `quiet`이면 돌아가는 것을 코드로 따라 얻었다. 실행은 하지 않았다 |
| R-35 | `render.ts:492-523`, `utils/renderCancellation.ts:37-40`, `98-155` | 코드 확인. Windows에서 SIGHUP·조상 프로세스 탐지(`processAncestorSnapshot`)의 동작은 열지 않았다 |
| R-36 | `render.ts:716-1011`, `utils/dockerRunArgs.ts:129-170`, `docker/Dockerfile.render:48`, `76-85` | 코드 확인. `describeDockerBuildFailure`와 `createStderrTail` 내부, Docker 이미지 안의 `hyperframes` 설치 방식은 열지 않았다 |
| R-37 | `utils/dockerRunArgs.ts:30-64`, `111-124`, `129-230`, `render/execute.ts:171-228` | 코드 확인. "넘기지 않는 flag"는 `buildDockerRunArgs` 인자 목록 전체(129-230)를 읽고 그 flag 이름이 없음을 확인했고, `grep -n "resume\|keep-segments\|frames-cache\|low-memory\|strict\|wait\|lint\|skill\|json" utils/dockerRunArgs.ts`도 주석 두 줄(111, 189)만 나왔다. `FORWARDED_RENDER_NETWORK_ENV`의 변수 이름 목록은 읽지 않았다 |
| R-38 | `render/plan.ts:515-543`, `render/execute.ts:75-96`, `batchRender.ts:89-340`, `474-480` | 코드 확인. `checkOutputsInsideTemplateFolder`·`checkOutputCollisions`·`validateBatchVariables` 내부 규칙은 이름과 오류 제목만 확인했다 |
| R-39 | `batchRender.ts:354-472`, `render/execute.ts:386-461` | 코드 확인 |
| R-40 | `commands/init.ts:769-904`, `utils/attendedTerminal.ts:13-26` | 코드 확인. `isAgentDriven()`(`telemetry/agent_runtime.ts`)가 어떤 환경을 에이전트로 보는지는 열지 않았다 |

| R-41 | C-05, `commands/init.ts:906-908`, `1203-1220` | 코드 확인 |

| R-42 | `commands/init.ts:905-948`, `297-324`, `340-356` | 코드 확인. `MEDIA_THE_SCAFFOLD_NEVER_WRITES` 확장자 목록은 C-06에 가깝다(코드 위치만) |

| R-43 | `commands/init.ts:949-1070`, `469-485` | 코드 확인. `whisper/manager.ts`·`whisper/transcribe.ts`·`whisper/normalize.ts`(자막 HTML 갱신) 내부는 열지 않았다. 전사 기능의 소유 행은 15다 |

| R-44 | `commands/init.ts:1073-1279`, `templates/generators.ts:15-49` | 코드 확인. 대화 모드를 실제 터미널에서 실행하지는 않았다. registry 목록을 못 불러올 때(오프라인)의 동작은 `listRegistryItems`를 열지 않아 모른다 |

| R-45 | `commands/init.ts:260-300`, `358-404`, `661-730`, `utils/copyDir.ts:1-14`, `utils/projectConfig.ts:86-97`, `templates/remote.ts:47-69`, `templates/_shared/` | 코드 확인. `cmp CLAUDE.md AGENTS.md`로 두 파일이 같음을 확인했다. registry 설치기(`registry/installer.ts`)와 `resolveItemWithDependencies`는 열지 않았다. `_shared/*.md` 본문은 첫 20행만 읽었다 |

| R-46 | C-02, C-04, `commands/init.ts:99-102`, `427-466`, `597-660` | 코드 확인. `matchHtmlBodyCssWidthFirst` 등 `@hyperframes/parsers` 함수 내부와 `CANVAS_DIMENSIONS` 값은 열지 않았다 |

| R-47 | `commands/init.ts:85-97`, `124-258`, `486-596` | 코드 확인. `probeVideo` 앞 약 70줄(회전·fps 계산)은 대략만 읽었다 |

| R-48 | `commands/init.ts:732-768`, `commands/skills.ts:336-352` | 코드 확인. `updateSkills` 본문(`checkSkills`, 설치, `presenceOnly` 판정)은 앞 50줄만 읽었다. 소유 행은 14 |

| R-49 | `commands/init.ts:661-730`, `905-948`, `utils/copyDir.ts:5-14` | 코드 확인. "지우지 않는다"는 부재 주장이다. 검색: `grep -n "rmSync\|unlinkSync\|rmdirSync\|rm(\|rimraf\|cleanup" commands/init.ts commands/initMedia.ts templates/remote.ts utils/copyDir.ts`가 결과 없음이었다. 놓쳤을 가능성은 `registry/installer.ts`의 `installItem`이 실패 때 자기가 쓴 파일을 지우는 경우이고, 그 파일은 열지 않았다 |

| R-50 | `src/cli.ts:144-203`, `src/help.ts:19-170`, 각 `commands/<name>.ts`의 `meta`(소수만 열고 나머지는 `grep -m1 -A3 "meta: {"`로 설명 문자열만 읽었다) | 코드 확인(등록과 설명 문자열). 소유 행 열은 feature map 행 표(`overview.md` 33-50행)와 명령 이름·설명으로 맞춘 추정이다. 소유 행 판단은 `추론`이고 U-02에 둔다 |
| R-51 | `commands/doctor.ts:406-504` | 코드 확인. 각 `check*` 함수 내부는 열지 않았다 |
| R-52 | `commands/info.ts:60-137` | 코드 확인. `heardClips`, `totalSize`, `durationFromRoot` 내부는 열지 않았다 |
| R-53 | `commands/docs.ts:100-156` | 코드 확인. `TOPICS`의 주제 목록과 `docsDir()` 위치는 열지 않았다 |
| R-54 | `commands/compositions.ts:20-60`, `170-229` | 코드 확인. `parseCompositions` 본문 중간은 열지 않았다 |
| R-55 | `src/cli.ts:122-138`, `src/utils/env.ts:5-14` | 코드 확인. `workspaceBuildCheck.ts` 내부는 열지 않았다 |
| R-56 | `ui/prompts.ts:12-70`, `utils/attendedTerminal.ts:13-26` | 코드 확인. 어떤 명령이 `confirmationRequired`를 부르는지는 검색하지 않았다 |
| T-01~T-20 | 구현에서 도출. 각 사례는 관련 R-ID의 근거 줄을 코드로 따라가 기대값을 적었고 실행하지는 않았다. T-03의 제안 문구(`Did you mean ...`)는 `didYouMean.ts` 내부를 읽지 않아 꼴만 적었고, T-10의 시각은 로컬 시각이다 | 대체한 의존 없음. 검증하지 않는 것: 실제 Chrome·ffmpeg·Docker 실행과 telemetry 전송 |
