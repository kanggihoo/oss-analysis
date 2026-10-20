> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져오십시오.
> 더 깊이 탐색하기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾으십시오.

# 캡션 스타일

> 캡션 톤을 이름 붙은 캡션 컴포넌트에 매핑하고, 컴포즈된 영상에서 단어별 강조를 프롬프트하는 방법.

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

레벨 1의 설명 영상은 이미 "임베디드 캡션, 키워드는 강조 색으로 하이라이트"를 요청했고 합리적인 기본값을 받았습니다. 이 장은 그 요청 뒤에 있는 카탈로그입니다 — 톤에 따라 고정할 수 있는 이름 붙은 컴포넌트들이므로, 하이라이트 색과 애니메이션이 기본값이 아니라 결정이 됩니다.

## 캡션 스타일이 하는 일과 트리거 시점

캡션 컴포넌트는 화면 위 텍스트를 애니메이션으로 렌더하는 드롭인 스니펫입니다 — 컴포넌트마다 하나의 시각적 정체성이 있고, 단어 또는 줄 단위로 애니메이션됩니다. 만들고 있는 컴포지션 안에서 캡션, 자막, 키네틱 텍스트, 가사 스타일 단어, 또는 단어별 타이틀을 요청하면 이 계층이 작동합니다. 캡션의 *에너지*를 설명하면 에이전트가 맞는 타이포그래피, 크기, 애니메이션을 고르고, 컴포넌트 이름을 대면 외관이 고정됩니다.

<Note>
  이 컴포넌트들은 **컴포즈된 영상**용입니다 — HyperFrames 컴포지션에 저작하는 캡션입니다. 기존 **토킹헤드 MP4**에 캡션을 넣으려면, 대신 [`/embedded-captions`](/prompting/captions-and-talking-heads) 워크플로를 사용하십시오. 이 워크플로는 피사체 매팅과 오클루전(캡션이 발화자 *뒤에* 놓임)을 중심으로 만든 자체 캡션 정체성 카탈로그를 갖고 있으며, 아래의 컴포지션 스니펫은 이것을 하지 않습니다.
</Note>

## 톤 → 캡션 컴포넌트

| 톤 | 컴포넌트 |
| - | - |
| **하이프 / 고에너지 소셜** | [`caption-kinetic-slam`](/catalog/components/caption-kinetic-slam), [`caption-highlight`](/catalog/components/caption-highlight), [`caption-particle-burst`](/catalog/components/caption-particle-burst), [`caption-emoji-pop`](/catalog/components/caption-emoji-pop) |
| **깔끔함 / 기업용** | [`caption-clip-wipe`](/catalog/components/caption-clip-wipe), [`caption-weight-shift`](/catalog/components/caption-weight-shift) |
| **우아함 / 에디토리얼** | [`caption-editorial-emphasis`](/catalog/components/caption-editorial-emphasis), [`caption-gradient-fill`](/catalog/components/caption-gradient-fill), [`caption-weight-shift`](/catalog/components/caption-weight-shift) |
| **네온 / 나이트라이프 / 음악** | [`caption-neon-glow`](/catalog/components/caption-neon-glow), [`caption-neon-accent`](/catalog/components/caption-neon-accent) |
| **테크 / 사이버 / 글리치** | [`caption-glitch-rgb`](/catalog/components/caption-glitch-rgb), [`caption-matrix-decode`](/catalog/components/caption-matrix-decode) |
| **가라오케 / 가사 / 따라 읽기** | [`caption-pill-karaoke`](/catalog/components/caption-pill-karaoke), [`caption-highlight`](/catalog/components/caption-highlight) |
| **질감 있는 / 시네마틱 디스플레이 타입** | [`caption-texture`](/catalog/components/caption-texture), [`texture-mask-text`](/catalog/components/texture-mask-text) |
| **깊이 / 3D 레이어링** | [`caption-parallax-layers`](/catalog/components/caption-parallax-layers) |

## 텍스트 효과 컴포넌트

전체 트랙에 캡션을 다는 대신 하나의 집중된 역할을 하는 [텍스트 효과](/catalog/components/morph-text) 컴포넌트가 세 개 있습니다:

| 컴포넌트 | 사용할 때 |
| - | - |
| [`caption-blend-difference`](/catalog/components/caption-blend-difference) | 텍스트가 복잡하거나 계속 바뀌는 푸티지 위에 놓여 있어 반드시 읽혀야 할 때 — 뒤에 있는 것에 맞춰 픽셀 단위로 자동 반전됩니다. |
| [`morph-text`](/catalog/components/morph-text) | 한 자리에서 짧은 단어 목록("빠른 / 단순한 / 당신의")을 끈적한 모프로 순환시키고 싶을 때. |
| [`texture-mask-text`](/catalog/components/texture-mask-text) | 벽돌, 바위, 나무, 금속, 용암 같은 물리적 질감으로 채운 큰 디스플레이 단어. |

## 예제 프롬프트

> /faceless-explainer 30-second vertical explainer. Add [`caption-highlight`](/catalog/components/caption-highlight) captions, TikTok-style — the visible line stays up, one word highlighted at a time.

<DocsVideo title="HyperFrames video: Validate Captions Catalog" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-captions-catalog.mp4#t=0.1" portrait loop />

*위 프롬프트에서 렌더, 편집 없음.*

<Note>
  캡션 컴포넌트는 데모로 제공됩니다 — 고정된 단어 목록, 가로 크기, 8초 타임라인. 에이전트는 단어와 타이밍을 당신의 내레이션에 맞춰 다시 작성하고 포맷에 맞춰 크기를 조정합니다. 이는 예상된 동작이며 우회가 아닙니다. 한 번에 화면 가득 한 단어씩(보이는 줄 없이)을 원하면 그것은 `caption-highlight`가 아니라 [`caption-kinetic-slam`](/catalog/components/caption-kinetic-slam)입니다.
</Note>

> Hype captions with [`caption-kinetic-slam`](/catalog/components/caption-kinetic-slam): one full-screen word per beat, alternating slam-in direction.

<DocsVideo title="HyperFrames video: Caption Kinetic Slam" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/caption-kinetic-slam.mp4#t=0.1" loop />

*위 프롬프트에서 렌더, 24단어 줄을 직접 저작해 편집 없음.*

> Neon music-video captions using [`caption-neon-glow`](/catalog/components/caption-neon-glow). Make brand names larger with an accent color and highlight the numbers differently.

<DocsVideo title="HyperFrames video: Caption Neon Glow" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/caption-neon-glow.mp4#t=0.1" loop />

*위 프롬프트에서 렌더, 편집 없음 — 브랜드는 마젠타로 1.4배 크기로, 숫자는 기본 시안과 구별되는 앰버 색으로 렌더됩니다.*

> Fill the hero word "STONE" with [`texture-mask-text`](/catalog/components/texture-mask-text) using the rock texture.

## 조절 옵션

* **톤**은 타이포그래피, 크기, 애니메이션을 고릅니다 — 하이프(굵고, 72–96px, 스케일 팝)부터 스토리텔링(세리프, 44–56px, 느린 페이드)까지. [어휘](/prompting/vocabulary)의 캡션 톤 표를 참조하십시오.
* **단어별 강조.** "브랜드 이름은 강조 색으로 더 크게", "숫자는 다르게 하이라이트", "감정적인 키워드에 바운스 추가" 모두 동작합니다 — 여러 컴포넌트가 이것을 기준으로 동작합니다: [`caption-editorial-emphasis`](/catalog/components/caption-editorial-emphasis)는 강조 단어에 극적인 크기 대비를 적용하고, [`caption-particle-burst`](/catalog/components/caption-particle-burst)는 키워드에서 발사되며, 네온 컴포넌트는 키워드 강조 색을 지닙니다.
* **질감 변수.** [`caption-texture`](/catalog/components/caption-texture)는 용암, 대리석, 금속, 나무, 콘크리트, 바위를 제공합니다 — 원하는 것의 이름을 대십시오.
* **단어 목록.** [`morph-text`](/catalog/components/morph-text)는 편집 가능한 목록을 순환합니다; 단어를 순서대로 인용하십시오.
* **포맷.** 전체 화면 단일 단어 스타일([`caption-kinetic-slam`](/catalog/components/caption-kinetic-slam))과 TikTok 스타일 하이라이트([`caption-highlight`](/catalog/components/caption-highlight))는 세로 / 소셜 프레이밍을 위해 만들어졌습니다 — 크기와 세이프 영역이 맞도록 "vertical" 또는 "9:16"이라고 말하십시오.

## 실패 모드

**모든 단어에 무거운 효과를 겹치지 마십시오.** 캡션 컴포넌트는 이미 단어 단위로 애니메이션합니다. 그 위에 또 다른 강조를 쌓으면 경쟁하여 읽기 어려워집니다. 키워드만 강조하십시오.

* ❌ `make every word explode with particles`
* ✅ `caption-particle-burst, firing only on the keywords`

**한 섹션에서 캡션 스타일을 섞지 마십시오.** 구성(또는 섹션)마다 하나의 정체성은 디자인된 것처럼 읽히고, 두 개의 경쟁하는 스타일은 실수처럼 읽힙니다.

* ❌ `use caption-neon-glow and caption-matrix-decode together`
* ✅ 하나를 고르십시오; 명확한 섹션 경계에서만 스타일을 바꾸십시오

**토킹헤드 푸티지에는 이것을 쓰지 마십시오.** 이것들은 컴포지션 스니펫이지 매팅/오클루전 파이프라인이 아닙니다 — 건드리지 않은 MP4 위에 놓으면 캡션은 발화자 *앞에* 놓이고, 뒤에 놓이는 일은 없습니다. (아래 캡스톤 스레드는 `caption-kinetic-slam`이 피사체 *뒤에서* 읽히는 모습을 보여 주는데, 이는 모순이 아닙니다: 그 컴포지션은 먼저 푸티지 자체를 매팅하므로 컷아웃이 타입이 아래로 지나갈 수 있는 별도의 레이어가 됩니다. 제한은 스니펫 자체에 관한 것이지 기법에 관한 것이 아닙니다.)

* ❌ `/hyperframes add caption-highlight to my interview.mp4`
* ✅ `/embedded-captions` (참조: [캡션과 토킹헤드](/prompting/captions-and-talking-heads))

**차분한 콘텐츠에 과격한 스타일을 맞추지 마십시오.** 고에너지 캡션을 기업 설명 영상에 쓰면 톤과 충돌합니다; 톤 표가 정체성을 고르게 하십시오.

* ❌ `glitchy RGB captions` (웰니스 브랜드 작품에서)
* ✅ `clean captions with caption-clip-wipe`

**캡션 이름을 지어내지 마십시오.** [캡션](/catalog/components/caption-highlight)과 [텍스트 효과](/catalog/components/morph-text) 그룹의 컴포넌트만 존재합니다.

* ❌ `add typewriter-bounce captions`
* ✅ 톤을 설명하거나("튜토리얼, 모노스페이스, 타자기") 실제 컴포넌트 이름을 대십시오

<Note>
  **캡스톤 스레드** — [레벨 7 필름](/prompting/capstone)의 Material 영역에서, 클립 자체 트랜스크립션의 단어 동기화된 키워드가 매팅된 발화자 뒤에서 거대한 디스플레이 타입으로 슬램되어 들어옵니다 — 실제 단어 타이밍을 따르는 장면 연출로서의 캡션입니다(필름에서 잘라 냄, 아래).
</Note>

이것은 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)에서 작품을 만들어 내는 절입니다 — 자신의 영상에 가져다 쓸 수 있는 프롬프트 문장:

> THEN they speak, and the main **keywords of their own line — derived from the clip's transcription — land word-synced as huge display text BEHIND the cutout**, each keyword slamming in on its spoken moment with the subject's silhouette occluding it (the two-layer text-behind-subject plate); style the keyword type by adapting a bold **catalog caption component** (`caption-kinetic-slam` or similar) at display scale.

<DocsVideo title="HyperFrames video: Capstone Region Material" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-material.mp4#t=0.1" loop />

*그 절을 렌더한 것 — 완성된 필름에서 잘라 낸 영역.*

*다음: [아트워크를 생성할 때](/prompting/generated-artwork) — 손으로 그린 HTML/CSS/SVG가 이기는 곳과 생성된 이미지가 이기는 곳.*


## 관련 주제

- [카메라 추적 캡션](/catalog/components/caption-camera-follow.md)
- [하이라이트](/catalog/components/caption-highlight.md)
- [필 카라오케](/catalog/components/caption-pill-karaoke.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 빌드되고 호스팅됩니다.
