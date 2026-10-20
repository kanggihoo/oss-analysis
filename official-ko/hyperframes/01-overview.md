> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져오십시오.
> 더 깊이 탐색하기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾으십시오.

# 프롬프트 가이드

> AI 에이전트에게 HyperFrames 영상을 작성하도록 프롬프트하는 방법 — 설정, 두 가지 프롬프트 형태, 그리고 이 가이드의 지도.

export const DocsVideo = ({src, poster, title, autoPlay = false, loop = false, portrait = false}) => {
  const videoRef = useRef(null);
  const playerRef = useRef(null);
  const hideTimerRef = useRef(null);
  const progressFrameRef = useRef(null);
  const [enhanced, setEnhanced] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const [muted, setMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [controlsVisible, setControlsVisible] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenSupported, setFullscreenSupported] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [scrubbing, setScrubbing] = useState(false);
  const [previewTime, setPreviewTime] = useState(0);
  const [previewPosition, setPreviewPosition] = useState(0);
  const formatTime = seconds => {
    if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
    const minutes = Math.floor(seconds / 60);
    const remaining = Math.floor(seconds % 60);
    return `${minutes}:${String(remaining).padStart(2, "0")}`;
  };
  const clearHideTimer = () => {
    if (hideTimerRef.current) {
      window.clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  };
  const revealControls = () => {
    setControlsVisible(true);
    clearHideTimer();
    hideTimerRef.current = window.setTimeout(() => setControlsVisible(false), 2200);
  };
  const togglePlayback = async () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused || video.ended) {
      if (video.ended) video.currentTime = 0;
      setWaiting(true);
      try {
        await video.play();
      } catch {
        setWaiting(false);
        setPlaying(false);
      }
    } else {
      video.pause();
      setControlsVisible(true);
    }
  };
  const toggleMute = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.muted && video.volume === 0) video.volume = 0.8;
    video.muted = !video.muted;
    setMuted(video.muted);
  };
  const seek = event => {
    const video = videoRef.current;
    if (!video) return;
    const nextTime = Number(event.target.value);
    video.currentTime = nextTime;
    setCurrentTime(nextTime);
  };
  const updateScrubPreview = (event, seekMainVideo = false) => {
    if (!duration) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    const nextTime = ratio * duration;
    setPreviewing(true);
    setPreviewTime(nextTime);
    setPreviewPosition(ratio * 100);
    if (seekMainVideo) {
      const video = videoRef.current;
      if (video) {
        video.currentTime = nextTime;
        setCurrentTime(nextTime);
      }
    }
  };
  const cyclePlaybackRate = () => {
    const video = videoRef.current;
    if (!video) return;
    const rates = [1, 1.25, 1.5, 2];
    const currentIndex = rates.indexOf(video.playbackRate);
    const nextRate = rates[(currentIndex + 1) % rates.length];
    video.playbackRate = nextRate;
    setPlaybackRate(nextRate);
  };
  const toggleFullscreen = async () => {
    const player = playerRef.current;
    const video = videoRef.current;
    if (!player || typeof document === "undefined") return;
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else if (player.requestFullscreen) {
        await player.requestFullscreen();
      } else if (video?.webkitEnterFullscreen) {
        video.webkitEnterFullscreen();
      }
    } catch {}
  };
  const handleKeyboard = event => {
    if (event.target !== event.currentTarget) return;
    const video = videoRef.current;
    if (!video) return;
    if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
      togglePlayback();
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      video.currentTime = Math.max(0, video.currentTime - 5);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      video.currentTime = Math.min(duration || video.duration || 0, video.currentTime + 5);
    } else if (event.key.toLowerCase() === "m") {
      event.preventDefault();
      toggleMute();
    } else if (event.key.toLowerCase() === "f") {
      event.preventDefault();
      toggleFullscreen();
    }
  };
  useEffect(() => {
    setEnhanced(true);
    setFullscreenSupported(Boolean(playerRef.current?.requestFullscreen || videoRef.current?.webkitEnterFullscreen));
    return () => {
      clearHideTimer();
    };
  }, []);
  useEffect(() => {
    if (typeof document === "undefined") return undefined;
    const syncFullscreen = () => setFullscreen(document.fullscreenElement === playerRef.current);
    document.addEventListener("fullscreenchange", syncFullscreen);
    return () => document.removeEventListener("fullscreenchange", syncFullscreen);
  }, []);
  useEffect(() => {
    clearHideTimer();
    if (!playing) return undefined;
    hideTimerRef.current = window.setTimeout(() => setControlsVisible(false), 2200);
    return clearHideTimer;
  }, [playing]);
  useEffect(() => {
    if (!playing) return undefined;
    const updateProgress = () => {
      const video = videoRef.current;
      if (video && !video.paused) setCurrentTime(video.currentTime);
      progressFrameRef.current = window.requestAnimationFrame(updateProgress);
    };
    progressFrameRef.current = window.requestAnimationFrame(updateProgress);
    return () => {
      if (progressFrameRef.current) window.cancelAnimationFrame(progressFrameRef.current);
      progressFrameRef.current = null;
    };
  }, [playing]);
  const progress = duration > 0 ? currentTime / duration * 100 : 0;
  const replaying = duration > 0 && currentTime >= duration - 0.15;
  return <div className="hf-docs-video-block" data-portrait={portrait ? "true" : "false"}>
      <div ref={playerRef} className="hf-docs-video" role="region" aria-label={title} tabIndex={0} onKeyDown={handleKeyboard} onPointerMove={revealControls} onPointerLeave={() => setControlsVisible(false)} onFocus={revealControls} onBlur={event => {
    if (!event.currentTarget.contains(event.relatedTarget)) setControlsVisible(false);
  }}>
        <video ref={videoRef} aria-label={title} src={src} poster={poster} autoPlay={autoPlay} loop={loop} playsInline preload="metadata" controls={!enhanced} onClick={togglePlayback} onDoubleClick={toggleFullscreen} onLoadedMetadata={event => {
    const nextDuration = event.currentTarget.duration || 0;
    setDuration(nextDuration);
    setMuted(event.currentTarget.muted);
  }} onDurationChange={event => setDuration(event.currentTarget.duration || 0)} onTimeUpdate={event => setCurrentTime(event.currentTarget.currentTime)} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onPlaying={() => setWaiting(false)} onWaiting={() => setWaiting(true)} onCanPlay={() => setWaiting(false)} onEnded={() => {
    setPlaying(false);
    setControlsVisible(true);
  }} onVolumeChange={event => setMuted(event.currentTarget.muted)} />

        {enhanced && <>
            {!playing && (currentTime <= 0.2 || replaying) && <button type="button" className="hf-docs-video-hero-play" onClick={togglePlayback} aria-label={replaying ? "Replay video" : "Play video"}>
                <span className="hf-docs-video-hero-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <path d="M8 5.5v13l10-6.5z" />
                  </svg>
                </span>
              </button>}

            {waiting && playing && <span className="hf-docs-video-spinner" aria-label="Loading" />}

            <div className="hf-docs-video-controls" data-visible={controlsVisible ? "true" : "false"}>
              <div className="hf-docs-video-scrub-preview" data-visible={previewing ? "true" : "false"} style={{
    "--hf-video-preview-x": `${previewPosition}%`
  }} aria-hidden="true">
                <span>{formatTime(previewTime)}</span>
              </div>

              <input className="hf-docs-video-progress" type="range" min="0" max={duration || 0} step="0.01" value={Math.min(currentTime, duration || 0)} aria-label="Video progress" aria-valuetext={`${formatTime(currentTime)} of ${formatTime(duration)}`} onChange={seek} onPointerEnter={updateScrubPreview} onPointerMove={event => updateScrubPreview(event, scrubbing || event.buttons === 1)} onPointerDown={event => {
    setScrubbing(true);
    event.currentTarget.setPointerCapture?.(event.pointerId);
    updateScrubPreview(event, true);
  }} onPointerUp={event => {
    setScrubbing(false);
    if (event.pointerType !== "mouse") setPreviewing(false);
  }} onPointerCancel={() => {
    setScrubbing(false);
    setPreviewing(false);
  }} onPointerLeave={() => {
    if (!scrubbing) setPreviewing(false);
  }} style={{
    "--hf-video-progress": `${progress}%`
  }} />

              <div className="hf-docs-video-control-row">
                <button type="button" className="hf-docs-video-control" onClick={togglePlayback} aria-label={playing ? "Pause video" : "Play video"}>
                  {playing ? <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M7 5h4v14H7zm6 0h4v14h-4z" />
                    </svg> : <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M8 5.5v13l10-6.5z" />
                    </svg>}
                </button>

                <button type="button" className="hf-docs-video-control" onClick={toggleMute} aria-label={muted ? "Unmute video" : "Mute video"}>
                  {muted ? <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M4 9v6h4l5 4V5L8 9zm11.5 1.1 1.4-1.4 1.6 1.6 1.6-1.6 1.4 1.4-1.6 1.6 1.6 1.6-1.4 1.4-1.6-1.6-1.6 1.6-1.4-1.4 1.6-1.6z" />
                    </svg> : <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M4 9v6h4l5 4V5L8 9zm11 1.2v3.6c1-.5 1.7-1.5 1.7-2.8S16 10.7 15 10.2zm0-4v2.1c2.2.6 3.7 2.5 3.7 4.7s-1.5 4.1-3.7 4.7v2.1c3.3-.7 5.7-3.5 5.7-6.8S18.3 6.9 15 6.2z" />
                    </svg>}
                </button>

                <span className="hf-docs-video-time" aria-hidden="true">
                  {formatTime(currentTime)} <span>/</span> {formatTime(duration)}
                </span>

                <span className="hf-docs-video-spacer" />

                <button type="button" className="hf-docs-video-rate" onClick={cyclePlaybackRate} aria-label={`Playback speed ${playbackRate} times`}>
                  {playbackRate}×
                </button>

                {fullscreenSupported && <button type="button" className="hf-docs-video-control" onClick={toggleFullscreen} aria-label={fullscreen ? "Exit fullscreen" : "Enter fullscreen"}>
                    {fullscreen ? <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M8 3H6v3H3v2h5zm8 0v5h5V6h-3V3zM3 16v2h3v3h2v-5zm13 0v5h2v-3h3v-2z" />
                      </svg> : <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M3 8h2V5h3V3H3zm13-5v2h3v3h2V3zM5 16H3v5h5v-2H5zm14 3h-3v2h5v-5h-2z" />
                      </svg>}
                  </button>}
              </div>
            </div>
          </>}
      </div>

    </div>;
};

<DocsVideo title="HyperFrames video: Capstone Timeline Default" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-timeline-default-v2.mp4#t=0.1" loop />

*이 가이드를 끝내면 프롬프트만으로 이것을 만들 수 있습니다.*

HyperFrames는 AI 에이전트를 위해 만들어졌습니다. 컴포지션은 일반 HTML이고, CLI는 비대화형이며, 프레임워크는 문서만으로는 다루지 않는 패턴을 에이전트에게 가르치는 [스킬](https://github.com/vercel-labs/skills)을 함께 제공합니다. 이 가이드는 스킬을 설치한 뒤 에이전트에게 효과적으로 프롬프트하는 방법을 보여 줍니다. 결과물을 바꾸는 어휘, 시간을 아끼는 반복 패턴, 그리고 깨짐을 막는 규칙을 다룹니다.

<Note>
  **프롬프트를 쓰기 전에**, 세 가지를 준비하십시오: 아래에서 설명하는 스킬 설치, 스캐폴딩된 프로젝트(`npx hyperframes init my-video`), 그리고 각 렌더가 나오는 순간 판단할 수 있도록 라이브 미리보기(`npx hyperframes preview`)를 실행해 두는 것입니다. 미리보기를 열지 않고 프롬프트하면 모든 반복이 눈먼 추측이 됩니다.
</Note>

## 레벨 사다리

이 가이드는 초급에서 고급까지 하나의 흐름입니다. 각 레벨은 읽고 나면 할 수 있는 일입니다. 순서대로 읽거나, 자신이 막힌 지점에 맞는 레벨로 바로 가십시오:

| 레벨 | 읽고 나면 할 수 있는 일 |
| - | - |
| **1 — [첫 번째 영상](/prompting/product-launch)** | 프롬프트 하나로 완성된 영상을 얻습니다 — 워크플로가 빈칸(팔레트, 페이싱, 구조)을 대신 채워 줍니다. |
| **2 — [제어](/prompting/anatomy)** | 부품에 직접 이름을 붙입니다: 라우트, 스펙, 비트, 문구, 기법, 네거티브 — 에이전트가 틀리는 결정을 없애는 뼈대입니다. |
| **3 — [생동감](/prompting/motion)** | 슬라이드쇼처럼 보이지 않고 프리미엄처럼 읽히는 모션과 전환. |
| **4 — [실질](/prompting/code-blocks)** | 실제 기능 추가: 코드 애니메이션, 데이터 시각화, 오버레이, 캡션, 생성 아트워크, VFX, 3D. |
| **5 — [음성과 사운드](/prompting/media-and-audio)** | 내레이션, 음악, 그리고 직접 제공한 모든 푸티지를 올바르게 스코어링하고 믹싱. |
| **6 — [규모](/prompting/design-systems)** | 디자인 시스템, 변수, 스토리보드, 편집, 반복, 참조 맞추기, 내보내기 — 일회성 작업이 아니라 시스템으로서의 영상. |
| **7 — [캡스톤](/prompting/capstone)** | 위의 모든 것을 하나의 실제 프롬프트로 구성. 올라가는 각 챕터는 이 필름에서 자기 영역만 떼어 단독으로 보여 줍니다. 캡스톤 프롬프트는 이것들을 하나의 연속된 카메라 여정으로 묶는 접착제이며, 하나의 템플릿에서 두 번 렌더됩니다. |

## 1회 설정

프로젝트에(또는 에이전트 전역으로) 스킬을 설치하십시오:

```bash theme={null}
npx skills add heygen-com/hyperframes
```

설치 프로그램은 선택 화면을 보여 줍니다. 아래의 **핵심 스킬**을 선택하십시오 — 모든 프로젝트에 필요합니다. Claude Code에서는 설치 후 세션을 재시작하십시오. 스킬은 **슬래시 명령**으로 등록됩니다. `/hyperframes`에서 시작하십시오: 전체 표면을 안내하고 "영상 만들어 줘" 요청을 올바른 워크플로로 보냅니다.

**핵심 스킬 — 이것들을 모두 설치하십시오**

| 슬래시 명령 | 로드하는 내용 |
| - | - |
| `/hyperframes` | **먼저 읽으십시오.** 진입 스킬 — 기능 지도 + 영상 라우터; "영상 만들어 줘" 의도를 올바른 워크플로로 보냄 |
| `/hyperframes-core` | 컴포지션 계약 — HTML 구조, `data-*` 속성, 클립, 트랙 |
| `/hyperframes-animation` | 모든 애니메이션 — 모션 규칙, 장면 청사진, 전환, 그리고 런타임 어댑터(GSAP, Lottie, Three.js, Anime.js, CSS, WAAPI, TypeGPU) |
| `/hyperframes-creative` | 크리에이티브 디렉션 — 디자인 스펙, 팔레트, 타이포그래피, 내레이션, 비트 |
| `/hyperframes-cli` | 개발 루프 CLI — `init`, `lint`, `check`, `preview`, `render`, `doctor` |
| `/media-use` | 미디어 OS — TTS 보이스오버(`tts`), `transcribe`, `remove-background`, 그리고 BGM / SFX / 이미지 해석(호스트 앱 자체의 음악·사운드 도구가 먼저) |
| `/hyperframes-registry` | 직접 만들기 전에 카탈로그 검색; `hyperframes add`로 설치 |
| `/hyperframes-keyframes` | 런타임 전반에 걸친 seek-safe 키프레임 작성, 그리고 `hyperframes keyframes` 진단 |
| `/general-video` | 일반 작성 워크플로 — 다중 장면 작품, 릴스, 몽타주, 리믹스, 그리고 **컴패니언 모드**의 본거지; 아래 워크플로 중 맞는 것이 없을 때의 대체 수단 |

**선택 워크플로 — 입력에 맞는 것을 추가하십시오** (`/hyperframes`는 설치된 것 중 해당하는 워크플로로 라우팅합니다)

| 슬래시 명령 | 입력 → 출력 |
| - | - |
| `/product-launch-video` | 임의의 웹사이트 URL / 브리프 / 스크립트 → 론칭 또는 프로모 영상, 또는 사이트 투어/쇼케이스 |
| `/faceless-explainer` | 임의의 텍스트(URL 없음, 푸티지 없음) → 얼굴 없는 설명 영상 — 모든 비주얼을 새로 만듦(타이포그래피, 다이어그램, 데이터 시각화) |
| `/pr-to-video` | GitHub PR → 코드 변경 설명 영상 |
| `/embedded-captions` | 기존 토킹헤드 영상 → 같은 푸티지에 캡션/자막 |
| `/talking-head-recut` | 기존 토킹헤드 영상 → 트랜스크립트에 동기화된 그래픽 오버레이(키네틱 타이틀, 로어서드, PiP)를 얹은 푸티지 |
| `/motion-graphics` | 로고 / 수치 / 트윗 / 브리프 → 짧은(~10초) 무내레이션 모션 그래픽(키네틱 타입, 카운트업, 로고 스팅) — MP4 또는 투명 오버레이 |
| `/music-to-video` | 음악 트랙 — 파일, 영상의 오디오, 또는 분위기 브리프로 생성한 것 → 비트 동기화 영상(가사 / 슬라이드쇼 / 키네틱 프로모); 이미지는 선택 사항이며 비트에 맞춰 편집 |
| `/slideshow` | 덱 아웃라인 또는 슬라이드 → 발표자 모드가 있는 탐색 가능한 프레젠테이션(렌더된 MP4가 아님) |
| `/remotion-to-hyperframes` | 기존 Remotion(React) 컴포지션을 HyperFrames HTML로 이식 |
| `/figma` | Figma 파일 / 프레임 / URL → 가져온 에셋, 브랜드 토큰, 재구성된 모션 |

<Tip>
  선택기를 건너뛰고 모든 것(핵심 + 모든 워크플로)을 한 번에 설치하려면 `npx hyperframes skills`를 실행하십시오. 그리고 HyperFrames 프롬프트는 `/hyperframes`로 시작하십시오(Claude가 아닌 에이전트에서는 다른 방식으로 스킬을 호출하십시오) — 라우팅과 컴포지션 맥락을 명시적으로 로드하므로 에이전트가 올바른 워크플로를 고르고 규칙을 처음부터 제대로 지킵니다.
</Tip>

## Claude Design

Claude Design은 다른 설정을 사용합니다. GitHub에서 [`claude-design-hyperframes.md`](https://github.com/heygen-com/hyperframes/blob/main/docs/guides/claude-design-hyperframes.md)를 다운로드하고(↓ 버튼 클릭), **채팅에 첨부하십시오**(URL을 붙여넣지 마십시오 — 파일 첨부가 더 나은 결과를 만듭니다):

```text theme={null}
Use the attached skill. 25-second LinkedIn video for my startup.

Problem: Sales teams waste 3 hours/day on manual CRM updates.
Solution: AutoCRM — AI that logs every call, email, and meeting.
Traction: 200+ teams, $1.2M ARR, 18% MoM growth.
CTA: autocrmhq.com
```

Claude Design은 유효한 첫 초안(브랜드 아이덴티티, 장면 콘텐츠, 애니메이션, 전환)을 만듭니다. ZIP을 다운로드한 뒤 `npx hyperframes preview`가 실행 중인 상태에서 아무 AI 코딩 에이전트로 다듬으십시오. 전체 워크플로는 [Claude Design 가이드](/guides/design-tools)를 참조하십시오.

## 두 가지 프롬프트 형태

대부분의 성공적인 HyperFrames 프롬프트는 두 가지 형태 중 하나에 속합니다.

**콜드 스타트 — 영상을 묘사하기.** 처음부터 원하는 것을 에이전트에게 말합니다 — 크리에이티브 방향이 이미 머릿속에 있는 신규 작업에 가장 적합합니다.

> Using `/hyperframes`, create a 10-second product intro with a fade-in title over a dark background and subtle background music.

콜드 스타트 프롬프트는 **길이**("10초", "3초씩 5개 장면"), **종횡비**("16:9", "9:16 세로" — 지정하지 않으면 1920x1080이 기본), **분위기 / 스타일**("미니멀한 스위스 그리드", "에너지 넘치는 소셜"), 그리고 **핵심 요소**(타이틀, 로어서드, 캡션, 음악)를 명시할 때 가장 잘 동작합니다.

**웜 스타트 — 맥락을 영상으로 바꾸기.** 에이전트에게 작업할 무언가 — URL, 문서, CSV, 트랜스크립트 — 를 주고 그것을 영상으로 종합하라고 요청합니다. 여기서 HyperFrames가 빛납니다. 에이전트가 리서치/요약 단계와 제작 단계를 한 흐름에서 함께 수행하기 때문입니다.

> Take a look at this GitHub repo [https://github.com/heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) and explain its uses and architecture to me using `/hyperframes`.

> Turn this CSV into an animated bar chart race using `/hyperframes`.

웜 스타트 프롬프트는 에이전트가 문구를 지어내는 대신 *특정한 무언가*에 대해 쓰기 때문에 더 풍부하고 근거 있는 영상을 만듭니다.

위의 네 가지 프롬프트는 형태를 보여 줄 뿐 결과를 보여 주지 않습니다 — 이 가이드에서 렌더 결과가 함께 실린 모든 프롬프트는 적힌 그대로 실행된 것이며, 그 갤러리는 [검증된 예제](/prompting/examples)에 있습니다.

## 인터뷰: 에이전트가 먼저 묻는 것

두 형태 모두 아무것도 만들기 전에 짧은 인터뷰로 시작합니다. 에이전트가 멈춘 것이 아닙니다 — 의도 계층이 "영상 만들어 줘"를 확정된 브리프로 바꾸어, 빌드가 나중에 고쳐야 할 것들을 추측하지 않도록 하는 것입니다. 에이전트는 라우트를 확인한 뒤, 해당 워크플로의 필수 질문을 묻습니다(추천 답변이 먼저 나오므로 대부분은 한 단어 확인입니다). 선택된 워크플로가 두 실행 방식을 모두 지원하면, 실행 자체를 정하는 두 가지 질문으로 마무리합니다:

| 질문 | 선택지 |
| - | - |
| **스토리보드?** | `yes` — 채팅에서 계획 검토, 스틸이 담긴 보드(`boards/storyboard.html`), 그리고 패스별 빌드(장면이 두어 개를 넘으면 권장) · `no` — 확정된 브리프로 완성된 영상 한 편 |
| **자동화 또는 컴패니언?** | `automation` — 해당 워크플로의 파이프라인이 브리프를 처음부터 끝까지 실행 · `companion` — `/general-video`에서 모든 HyperFrames 기능을 테이블에 올려놓고 함께 빌드 |

두 질문은 독립적입니다 — 네 가지 조합이 모두 유효하며, 스토리보드에 yes라고 했다면 컴패니언 실행도 같은 검토 패스를 거칩니다. 두 질문을 모두 건너뛰는 경로가 네 개 있는데, 둘 다 덧붙일 것이 없기 때문입니다: `/motion-graphics`(작품이 수 초 길이), `/slideshow`(결과물은 렌더된 영상이 아니라 탐색 가능한 덱), 그리고 `/embedded-captions`와 `/talking-head-recut`(푸티지를 건드리지 않으므로 검토할 스토리보드가 없음).

급할 때는 이렇게 말하면 전체 대화를 건너뛸 수 있습니다:

> Just build it — don't ask me anything.

그러면 해당되는 곳에서는 `automation`과 스토리보드 없음이 잠기고, 에이전트가 물었을 모든 질문은 시작 알림에 명시된 기본값으로 대체됩니다.

인터뷰로 정해진 모든 내용은 프로젝트 루트의 **`BRIEF.md`**에 기록됩니다 — 채팅이 아니라 브리프가 산출물입니다. 나중의 세션(또는 다른 에이전트)은 그 파일에서 재개하며 다시 묻지 않습니다. 답을 바꾸려면 프롬프트에서 다시 설명하기보다 `BRIEF.md`를 편집하십시오.

## 권장 워크플로

1. `npx hyperframes init my-video` — 프로젝트 스캐폴딩(스킬은 자동 설치)
2. 프로젝트를 Claude Code(또는 Cursor / Codex)에서 열기
3. `/hyperframes`와 위 형태 중 하나로 프롬프트
4. `npx hyperframes preview` — 에이전트가 편집하는 동안 브라우저에서 확인
5. 작고 목표가 분명한 프롬프트로 반복
6. `npx hyperframes lint && npx hyperframes check` — 관문: 구조, 런타임 오류, 레이아웃 충돌, 모션, 대비. 렌더 전에 둘 다 통과해야 합니다
7. 만족하면 `npx hyperframes render --output final.mp4`

`check`는 사람들이 건너뛰고 나중에 후회하는 단계입니다. 헤드리스 브라우저에서 컴포지션을 실행하고, 정지 프레임이 알려 줄 수 없는 것을 보고합니다 — 요소가 영역을 넘침, 두 텍스트 블록이 충돌, 타임라인 중간에서만 발생하는 런타임 오류, WCAG AA 미만의 대비. 빠르며 선택 사항이 아닙니다: 10분 걸린 렌더에도 `check`가 몇 초 만에 짚어 냈을 결함이 얼마든지 들어 있을 수 있습니다.

## 프롬프트가 주는 것

이 가이드의 프롬프트 세 개와 편집하지 않은 렌더 결과 — 웜 스타트 워크플로 하나, 레지스트리 블록 작품 하나, 밀도 높은 자유 형식 스펙 하나:

> /product-launch-video Make a 45-second 1920x1080 launch video for [https://linear.app](https://linear.app). Energetic but minimal, use the site's own palette and screenshots. Structure: hook stating the problem, 3 feature beats with UI captures and one-line captions, end card with logo + "Try it free". Female TTS voice, confident tone, subtle electronic BGM under -18dB.

<DocsVideo title="HyperFrames video: Example Product Launch" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-product-launch-v2.mp4#t=0.1" loop />

*위 프롬프트에서 렌더, 편집 없음.*

> /motion-graphics 6-second 1920x1080 video, dark navy background. Beat 1 (0-1s): label "ARR" fades up small, top-center. Beat 2 (1-4s): a giant number counts up to \$4.2M with an odometer roll, easing out as it lands. Beat 3 (4-6s): "+312% YoY" stamps in below in green, then everything settles into a gentle ambient idle. Use the `apple-money-count` registry block as base. No narration.

<DocsVideo title="HyperFrames video: Example Stat Countup" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-stat-countup.mp4#t=0.1" loop />

*위 프롬프트에서 렌더, 편집 없음.*

그리고 [명세 다이얼](/prompting/specification-dial)의 먼 끝에서, 전체 비주얼+모션 스펙은 방송풍 애니메이션 지구본을 한 번에 만들어 냅니다 — 스펙은 [보았던 것 재현하기](/prompting/recreating-references)를 참조하십시오:

<DocsVideo title="HyperFrames video: Recreate Globe Oneshot" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/recreate-globe-oneshot-v2.mp4#t=0.1" loop />

*증류된 스펙에서 나온 원샷 렌더, 반복 없음.*

## 가이드 탐색

<CardGroup cols={2}>
  <Card title="프롬프트 해부" href="/prompting/anatomy">모든 원샷 프롬프트가 공유하는 여섯 부분 뼈대</Card>
  <Card title="검증된 예제" href="/prompting/examples">복사해서 붙여넣는 프롬프트, 각각 완성된 영상 한 편을 원샷으로 만듦</Card>
  <Card title="명세 다이얼" href="/prompting/specification-dial">얼마나 명시할지, 그리고 밀도가 무엇을 사는지</Card>
  <Card title="어휘" href="/prompting/vocabulary">특정 프레임워크 설정에 대응하는 단어</Card>
  <Card title="프리미엄 모션" href="/prompting/motion">영상이 싸구려처럼 느껴지지 않게 하는 여덟 가지 규칙 문법</Card>
  <Card title="참조 재현하기" href="/prompting/recreating-references">본 것을 텍스트만으로 맞추기</Card>
  <Card title="캡스톤" href="/prompting/capstone">위의 필름을 프레임 단위로 해부</Card>
</CardGroup>

*다음: [첫 번째 영상](/prompting/product-launch) — URL 하나, 프롬프트 하나, 완성된 론칭 영상.*


## 관련 주제

- [제품 론칭 영상](/prompting/product-launch.md)
- [변경 로그](/changelog.md)
- [검증된 예제 프롬프트](/prompting/examples.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 빌드되고 호스팅됩니다.
