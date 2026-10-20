> ## 문서 인덱스
> 전체 문서 인덱스는 다음 주소에서 가져올 수 있습니다: https://hyperframes.heygen.com/llms.txt
> 더 살펴보기 전에 이 파일로 사용할 수 있는 모든 페이지를 먼저 찾아볼 수 있습니다.

# 디자인 시스템과 브랜드

> "온브랜드"라고 막연히 요청하는 대신, 브랜드의 기준이 되는 출처(디자인 명세, 사이트, 또는 Figma 파일)를 에이전트에게 알려 주고 프레임 구성은 맡기십시오.

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

지금까지는 한 번에 한 장면씩 다뤘습니다. 이 단계는 영상을 시스템으로 보는 이야기입니다. 장면 전체에 걸쳐 유지되는 디자인, 회귀 없이 이루어지는 편집, 그리고 배포 가능한 결과물입니다. 영상이 가진 가장 시스템적인 요소인 브랜드에서 시작합니다.

"온브랜드로 만들어 줘"는 요청하기에 가장 모호한 말입니다. 에이전트는 여러분의 브랜드가 *무엇인지* 알 방법이 없으므로 임의로 하나를 만들어 냅니다.

해결책은 바뀌지 않습니다. 에이전트에게 **브랜드 기준의 출처**를 주고, 프롬프트에서 그 출처를 이름으로 지정하십시오. 출처는 디자인 명세, 라이브 사이트, 또는 Figma 파일입니다. 아래 각 절은 그 방법 하나씩을 설명합니다.

## 설명 대신 명세를 가리킵니다

HyperFrames 프로젝트에는 디자인 명세 `frame.md`를 둘 수 있습니다. 그 프론트매터에는 기계가 읽을 수 있는 브랜드 정보가 들어 있습니다. 정확한 16진수 값, 글꼴 패밀리, 굵기 관계입니다. 프론트매터 아래의 본문에는 의도와 브랜드의 하지 말아야 할 것, 해야 할 것이 적힙니다.

명세가 있으면 이름을 지정하십시오.

> Use the palette and type from `frame.md`. Build a 15-second feature announcement.

* ❌ `make it feel on-brand and premium`
* ✅ `pull colors and fonts from frame.md; premium means generous spacing and one restrained accent`

이 방식이 잘 되는 이유: `온브랜드`는 에이전트가 짐작해야 하는 분위기입니다. 명세의 프론트매터는 규범적입니다. 에이전트는 여러분의 16진수 값과 글꼴 패밀리를 근사하지 않고 그대로 인용하고, 그다음 본문을 읽어 의도를 파악합니다.

브랜드 자료가 다른 곳에 있다면 첨부하십시오. PDF 브랜드 가이드, 스크린샷, 붙여 넣은 16진수 코드는 설명된 인상보다 훨씬 안정적으로 읽힙니다.

## 브랜드는 색과 글꼴에 대해서만 기준이고, 레이아웃에는 기준이 아닙니다

디자인 명세는 브랜드가 *어떻게 보이는지*를 말합니다. 영상 프레임을 *어떻게 구성할지*는 말하지 않습니다. 바꾸면 안 되는 것을 이름으로 지정하고, 나머지 구성은 에이전트에게 맡기십시오.

> Colors and fonts are locked to the brand — keep the exact hexes and the display/body pairing. Layout, spacing, and motion are yours to compose for video.

이 방식이 잘 되는 이유: 웹 규모의 브랜드 값은 영상에서 살아남지 못합니다. `0.06` 불투명도 그림자가 있는 `1px` 테두리는 H.264 압축 후에 보이지 않습니다. 웹용 본문 크기는 1080p 프레임에서 사라집니다.

그래서 명세를 두 부분으로 나눠 다루십시오.

* **엄격하게 유지** — 브랜드 색, 글꼴, 굵기 관계, 배경 선택. 브랜드가 밝은 캔버스라면 밝게 유지합니다.
* **매체에 맞게 키우기** — 타입 크기, 장식 요소의 불투명도, 테두리 두께.

웹 디자인 시스템에서 레이아웃을 지나치게 지정하면 이 방식과 충돌합니다. 팔레트와 타이포그래피만 고정하고, 프레임은 맡기십시오.

## 사이트 고유의 팔레트와 글꼴을 사용합니다

명세는 없지만 브랜드가 이미 공개되어 있다면, 그 주소를 가리켜 에이전트가 추출하게 하십시오.

> Match this site's look — pull its palette and fonts — and make a 20-second launch clip: `https://…`

잘 알려진 브랜드라면 이름만 말해도 충분한 경우가 많습니다. 에이전트가 팔레트와 타이포그래피를 직접 조사합니다.

한 가지 주의할 점이 있습니다. 단일 페이지 앱의 홈페이지는 거의 빈 셸만 돌려주는 경우가 있습니다. 팔레트가 빈약하게 나오면 블로그, 보도자료, 문서 페이지를 가리키십시오.

이것도 같은 브랜드 기준 방식입니다. 파일 대신 *사이트*가 출처가 됩니다.

## Figma 프레임, 브랜드, 로고 가져오기

브랜드가 Figma에 있다면 직접 요청하십시오. 에이전트는 스크린샷을 눈대중으로 보지 않고 가져옵니다.

> Bring in the brand tokens from this Figma file, then build the intro: `https://figma.com/…`

> Import this Figma frame as the opening scene and this logo as an SVG: `<links>`

[Figma 가져오기](/guides/figma)는 각 가져오기를 출처 정보와 함께 로컬 파일로 고정합니다. 렌더링은 Figma를 호출하지 않으므로 결정적인 결과를 유지합니다. 브랜드 변수는 컴포지션 브랜드 토큰으로 들어옵니다.

요청을 표현할 때 알아둘 점이 두 가지 있습니다.

* **컴포넌트보다 토큰을 먼저 가져옵니다.** "브랜드 토큰을 먼저 가져온 다음 컴포넌트를 만들어 줘"라고 말하십시오. 그래야 가져온 컴포넌트 색이 중복 16진수 값을 굽는 대신 브랜드 변수에 연결됩니다.
* **스토리보드 프레임은 슬라이드가 아니라 상태입니다.** 장면 프레임 띠를 가리킨다면, 프레임 사이의 모션을 *재구성*해 달라고 요청하십시오. 한 요소가 네 위치에 있는 프레임은 넘겨 볼 정지 이미지 네 장이 아니라, 한 요소가 움직이는 장면입니다.

## 여러 편으로 이루어진 시리즈의 일관성 유지

시리즈는 출시 세트, 주간 클립, 지역별 컷처럼 여러 편으로 이루어집니다. 일관성은 매번 브랜드를 다시 설명하는 데서 오지 않고, **공유된 기준 출처**에서 옵니다.

> All four videos share `frame.md` for palette and type. Only the headline and the stat change per video.

변하지 않는 부분은 하나의 작성 명세나 하나의 Figma 토큰 세트에서 가져옵니다. 바뀌는 부분은 [변수](/prompting/variables-and-templating)가 됩니다.

`frame.md`가 바뀌면, 영향을 받는 컴포지션을 생성하거나 조립하는 워크플로 단계를 다시 실행하십시오. 그래야 작성된 HTML이 새 브랜드 값을 반영합니다.

이미 존재하는 컴포지션은 렌더링 시점에 스타일을 다시 입혀야 할 때가 있습니다. 이때는 공유 브랜드 토큰을 컴포지션 변수로 선언하십시오. 모든 스칼라 변수는 컴포지션 루트에 `--{id}` CSS 커스텀 속성으로 적용되므로, CSS의 `var(--id)`가 재정의 값을 따라갑니다.

여기서 디자인 시스템과 템플릿화가 만납니다. 브랜드는 공유되고, 콘텐츠는 매개변수화됩니다.

## 경로로 브랜드 에셋 제공하기

로고, 글꼴, 텍스처, 제품 사진은 입력입니다. 그리라고 요청하지 말고 경로를 주십시오.

> Logo at `assets/logo.svg`, brand font files in `assets/fonts/`, product shot at `assets/hero.png`. Use them; don't invent placeholders.

래스터 로고보다 SVG 로고를 쓰십시오. 크기를 자유롭게 바꿀 수 있고 애니메이션도 가능합니다.

경로를 명시하면 에이전트가 대체 이미지를 만들지 않고 실제 에셋을 연결합니다. 또한 렌더링이 시작되기 전에 모든 에셋이 로컬에 있으므로 렌더링도 결정적으로 유지됩니다.

## 워크플로가 받는 입력을 제공하고, 프리셋과 싸우지 마십시오

각 제작 워크플로에는 설계된 룩이 함께 들어 있습니다. 예를 들어 `/product-launch-video`, `/faceless-explainer`가 있습니다. 그 룩에 브랜드 입력을 주고, 나중에 컴포지션을 덮어쓰지 마십시오.

* ❌ `run /product-launch-video, then restyle every scene to my colors afterward`
* ✅ `run /product-launch-video with my palette, fonts, and logo as inputs up front`

이 방식이 잘 되는 이유: 워크플로의 프리셋은 일관되고 검증된 시스템입니다. 색, 간격, 모션, 컴포넌트 처리가 서로 맞물려 있습니다. 시작할 때 브랜드 입력을 주면, 에이전트는 그 시스템 *안에서* 팔레트와 타입을 적용합니다.

나중에 장면마다 다시 스타일을 입히면, 전체로 균형 잡힌 디자인에서 실을 뽑아내는 셈입니다. 처음부터 명세를 건네는 것보다 프리셋과 싸우는 데 노력이 더 듭니다.

## 관련 문서

<CardGroup cols={2}>
  <Card title="Figma Import" icon="figma" href="/guides/figma">
    Figma 파일에서 브랜드 토큰, 에셋, 컴포넌트, 모션을 가져옵니다.
  </Card>

  <Card title="Variables and templating" icon="sliders" href="/prompting/variables-and-templating">
    브랜드 토큰을 변수로 바꿔, 하나의 값으로 시리즈 전체의 스타일을 다시 입힙니다.
  </Card>

  <Card title="The specification dial" icon="gauge" href="/prompting/specification-dial">
    정확한 16진수 값과 타입 방향을 고정하면 편차가 줄어드는 방법입니다.
  </Card>

  <Card title="Claude Design" icon="message" href="/guides/design-tools">
    브랜드 가이드나 스크린샷을 첨부해 내 룩을 바탕으로 첫 초안을 만듭니다.
  </Card>
</CardGroup>

<Note>
  **캡스톤 흐름** — [레벨 7 영화](/prompting/capstone) 전체가 제공된 `frame.md`, 즉 실제 HyperFrames 브랜드(HeyGen 제작)를 따릅니다. 마무리 로크업에서 시스템이 가장 잘 드러납니다. ABC Solar Display가 디스플레이 타입을 담당하고, 민트에서 시안으로 이어지는 CTA 그라데이션이 단 한 번 등장합니다(아래 영화에서 잘라낸 장면).
</Note>

이 절은 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)에서 이 장면을 살려 주는 문장입니다. 여러분의 영상에도 그대로 가져다 쓸 수 있는 프롬프트 표현입니다.

> **Design system: the provided `frame.md` is the single source of brand truth — read it first and obey it exactly.** It is the real HyperFrames brand (by HeyGen), dark-first: flat near-black ground \[…] **mint `#3CE6AC` used sparingly as the single accent — mint means go / primary / active**. The mint→cyan gradient (`#3CE6AC → #00E3FF`) appears in exactly one place in the whole film: the final CTA lockup.

<DocsVideo title="HyperFrames video: Capstone Region Render" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-render.mp4#t=0.1" loop />

*위 문장이 실제로 작동한 결과입니다. 마무리 로크업에서 브랜드 파일의 디스플레이 서체와 단 하나뿐인 그라데이션이 함께 나타납니다.*

*다음: [변수와 템플릿화](/prompting/variables-and-templating) — 시리즈 전체에서 반복되는 브랜드 토큰을 렌더링할 때마다 채우는 이름 있는 슬롯으로 바꿉니다.*


## 관련 주제

- [Capstone — every technique, one journey](/prompting/capstone.md)
- [Audio effects and mixing](/prompting/audio-effects.md)
- [Variables and templating](/prompting/variables-and-templating.md)


이 문서는 개발자 문서 플랫폼인 [Mintlify](https://mintlify.com)로 만들어지고 호스팅됩니다.
