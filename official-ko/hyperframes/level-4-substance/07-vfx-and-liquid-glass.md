> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져옵니다.
> 더 살펴보기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾아보십시오.

# VFX와 liquid glass

> 디바이스 목업, liquid-glass UI, shatter/portal/magnetic 순간, 그리고 앰비언트 마감을 프롬프트로 요청하고, 어떤 효과에 canvas 파이프라인이 필요한지 알아봅니다.

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

Level 1의 모션 그래픽 터미널 작품은 이미 이 중 하나를 지정했습니다. 터미널이 부서지는 장면의 `vfx-shatter`입니다. 이 장은 카탈로그에서 그 화려한 쪽의 나머지 부분을 다룹니다. 3D 디바이스 목업, 반투명 유리 질감의 Apple 스타일 UI, 그리고 HTML이 산산이 부서지거나 포털로 빨려 들어가는 영화적인 순간이 여기에 해당합니다. 두 그룹이 주된 역할을 합니다. [HTML-in-Canvas](/catalog/blocks/vfx-iphone-device) 블록(실제 WebGL, 라이브 HTML을 GPU 텍스처로 렌더링)과 [Effects](/catalog/components/vignette) 컴포넌트(가벼운 CSS 마감)입니다. 어느 쪽이 어느 쪽인지 아는 것이 제대로 렌더링되는 효과와 예상 밖으로 어긋나는 효과를 가릅니다. 이 모든 것은 "technique" 단계에서 [one-shot 골격](/prompting/anatomy)에 들어갑니다.

### 디바이스 목업

제품 UI를 실제 휴대폰이나 노트북 안에 넣으려면 [`vfx-iphone-device`](/catalog/blocks/vfx-iphone-device)를 지정하십시오. 실제 GLTF iPhone 15 Pro Max와 MacBook Pro 모델에 라이브 HTML-in-Canvas 화면 콘텐츠, 제품 리뷰 카메라 연출, 360° 턴테이블이 포함됩니다. 디바이스 자체가 아니라 스타일이 적용된 iOS/macOS *환경*(홈 화면, 데스크톱, 독)이 필요하다면 아래의 liquid-glass 시스템 블록을 사용하십시오.

> /product-launch-video 15초 1920x1080 영상. 우리 대시보드 UI가 실제 iPhone 15 Pro Max 화면에 나오고, 제품 리뷰 조명 아래에서 천천히 턴테이블로 돕니다. 그다음 MacBook Pro가 옆에서 슬라이드로 들어와 같은 UI를 더 넓게 보여줍니다. `vfx-iphone-device` 레지스트리 블록을 사용하십시오. 내레이션은 없습니다.

<DocsVideo title="HyperFrames video: Validate Device Mockup" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-device-mockup.mp4#t=0.1" loop />

*위 프롬프트(블록의 데모 UI가 화면에 표시된 상태)로 렌더링했으며, 편집하지 않았습니다.*

**디바이스와 그 화면에 무엇이 나올지를 함께 요청하십시오.** 블록은 라이브 HTML을 화면에 렌더링하지만 자체 데모 UI를 함께 제공합니다. 여러분의 UI를 설명하거나(스크린샷이나 경로를 가리키거나) 해야 에이전트가 데모 대신 블록의 화면 콘텐츠를 교체합니다.

* ❌ `내 앱을 iPhone에 보여줘` (블록에 내장된 데모 UI가 나옵니다)
* ✅ `우리 대시보드 UI(assets/ui/의 스크린샷)를 iPhone 15 Pro Max 화면에 넣고, 턴테이블로 회전`

### Liquid-glass UI 처리

liquid-glass 블록은 오로라 셰이더 배경 위에 떠 있는 Apple 스타일의 반투명 유리 UI입니다. 원하는 표면에 따라 고르십시오.

| 원하는 것 | 지정할 블록 | 길이 |
| - | - | - |
| 3D iPhone 위의 전체 iOS 26 홈 화면 | [`ios26-liquid-glass`](/catalog/blocks/ios26-liquid-glass) | 15초 |
| 3D MacBook 위의 macOS Tahoe 데스크톱 | [`macos-tahoe-liquid-glass`](/catalog/blocks/macos-tahoe-liquid-glass) | 15초 |
| 유리 알림 카드 | [`liquid-glass-notification`](/catalog/blocks/liquid-glass-notification) | 8초 |
| 유리 통계 카드, 패널, 알약 모양 칩 | [`liquid-glass-widgets`](/catalog/blocks/liquid-glass-widgets) | 8초 |

네 개의 `liquid-glass-*` 패널 블록은 오로라 셰이더 무대를 공유하므로 하나의 장면으로 자연스럽게 합칠 수 있습니다. `ios26-liquid-glass`와 `macos-tahoe-liquid-glass`는 완전한 디바이스 환경이어서 보통 단독으로 사용합니다.

> /motion-graphics 8초 1920x1080 영상. 프로스트 글라스 알림 카드가 떠다니며 들어와 오로라 셰이더 배경 위에 쌓이고, 각각 가짜 알림("Build passed", "Deploy live", "0 incidents")을 보여줍니다. 실제 반투명 효과가 필요합니다. 각 카드를 통해 오로라가 보여야 합니다. 흰색 텍스트가 오로라에서 가장 밝은 부분 대비 3:1 이상을 유지할 만큼 유리를 흐리게 처리하십시오. 오디오는 없습니다.

<DocsVideo title="HyperFrames video: Glass Notify" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/glass-notify.mp4#t=0.1" loop />

*위 프롬프트로 렌더링했으며, 편집하지 않았습니다. Three.js 오로라 위의 CSS `backdrop-filter` 유리입니다.*

<Warning>
  **`liquid-glass-notification` 블록은 GPU가 필요하며, GPU가 없으면 조용히 실패합니다.** `stability: experimental`로 표시되어 있고 `webgpu` 태그가 붙어 있습니다. 프로스트 표면이 `drawElementImage`로 그려지고, 굴절은 WebGPU 렌더러가 계산하기 때문입니다. 이 장을 검증하는 동안 `navigator.gpu.requestAdapter()`는 시도한 모든 headless 및 headful Chrome에서 `null`을 반환했습니다(`--enable-unsafe-webgpu`, `--use-angle=metal`, 하드웨어 GPU 모드를 모두 시도). 블록의 초기화는 그냥 빠져나갑니다. 실패는 오류로 드러나지 않습니다. **카드가 하나도 보이지 않고** 텍스트만 배경 위에 떠 있게 됩니다.

  따라서 재현 가능한 렌더링이 필요하다면 프롬프트에서 *효과*를 요청하십시오. "실제 반투명, 카드 뒤 배경이 보이도록"처럼 말하고, 에이전트가 어디서나 렌더링되는 CSS `backdrop-filter`로 만들게 하십시오. 위의 영상이 바로 그 결과입니다. WebGPU 블록은 렌더링 환경에서 작동하는 어댑터를 확인했고, CSS로는 할 수 없는 굴절, 정반사, 색수차가 특별히 필요할 때만 사용하십시오.
</Warning>

**"Liquid glass"는 설명한 필터가 아니라 블록을 뜻합니다.** 이것들은 완전한 WebGL 무대입니다. "div에 유리 같은 블러"를 요청하면 CSS `backdrop-filter`가 나오며, 이 질감은 나오지 않습니다.

* ❌ `내 텍스트 위에 liquid glass 효과를 추가해줘`
* ✅ `통계 카드에는 liquid-glass-widgets 레지스트리 블록을 사용해줘`

### Shatter, portal, magnetic, 커서 순간

`vfx-*` 블록은 하나하나가 독립적인 영화적 순간입니다. 영상 전체가 아니라 전환이나 공개 장면에 쓰십시오.

| 순간 | 지정할 블록 | 길이 |
| - | - | - |
| HTML이 유리 조각으로 부서짐 | [`vfx-shatter`](/catalog/blocks/vfx-shatter) | 12초 |
| 볼류메트릭 빛과 함께 차원이 깨짐 | [`vfx-portal`](/catalog/blocks/vfx-portal) | 10초 |
| 자기장 입자 시각화 | [`vfx-magnetic`](/catalog/blocks/vfx-magnetic) | 15초 |
| 유기적인 액체 표면 위에 떠 있는 HTML | [`vfx-liquid-background`](/catalog/blocks/vfx-liquid-background) | 12초 |
| 색수차 그림자 광선이 있는 극적인 텍스트 공개 | [`vfx-text-cursor`](/catalog/blocks/vfx-text-cursor) | 8초 |

> /motion-graphics 8초 1920x1080 영상. 1번 비트(0-4초): 랜딩 페이지 히어로가 방향성 조명 아래 유지됩니다. 2번 비트(4-6초): 페이지 전체가 유리 조각으로 부서져 흩어집니다. 3번 비트(6-8초): 굵은 흰색 텍스트가 검은 배경에 쾅 하고 들어옵니다. `vfx-shatter` 레지스트리 블록을 사용하십시오. 마지막 비트에는 "HTML IS VIDEO"라고 적힙니다. 내레이션은 없으며, 이미지나 미디어 파일도 쓰지 않습니다.

<DocsVideo title="HyperFrames video: Vfx Shatter" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/vfx-shatter.mp4#t=0.1" loop />

*위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*

**"explode," "break," "burst"처럼 두루뭉술하게 말하지 말고 정확한 효과 이름을 쓰십시오.** 각 블록은 특정한 시뮬레이션입니다.

* ❌ `UI를 폭발시켜줘`
* ✅ `페이지가 유리 조각으로 부서진다` → `vfx-shatter`, 또는 `포털로 빨려 들어간다` → `vfx-portal`

### 앰비언트 마감

[Effects](/catalog/components/vignette) 컴포넌트는 완성된 장면 *위에* 겹쳐 쓰는 가벼운 순수 CSS 마감 처리입니다. 그레인, 비네트, 빛 스윕, 미묘한 푸시 등이 있습니다.

| 이렇게 말하십시오 | 컴포넌트 |
| - | - |
| 필름 그레인 / 질감 | [`grain-overlay`](/catalog/components/grain-overlay) |
| 어두운 영화적 가장자리 | [`vignette`](/catalog/components/vignette) |
| 텍스트를 가로지르는 빛 스윕 | [`shimmer-sweep`](/catalog/components/shimmer-sweep) |
| 카드에 천천히 밀고 들어가는 줌 | [`parallax-zoom`](/catalog/components/parallax-zoom) |
| 카드가 물러나며 형제 카드를 드러냄 | [`parallax-unzoom`](/catalog/components/parallax-unzoom) |
| 화면이 그리드로 흩어짐 | [`grid-pixelate-wipe`](/catalog/components/grid-pixelate-wipe) |

이것들은 [모션 문법](/prompting/motion)의 앰비언트 계층입니다. 그레인과 느린 `parallax-zoom`은 "정지된" 비트가 얼어붙지 않고 살아 있게 합니다. "움직임 없이 멈춘다"라고 쓰지 마십시오. 완전히 정지한 마지막 1초는 값싼 모션의 가장 큰 흔적입니다. 그레인 오버레이와 2% 푸시가 그 정지를 지탱하게 하십시오.

> /motion-graphics 6초 1920x1080 영상. 워드마크 로고인 "HYPERFRAMES"가 거의 검은 바탕에 플래티넘 색으로 화면 중앙에 자리 잡고 멈춥니다. 다만 필름 그레인 오버레이와 3% 느린 푸시인을 더해 살아 있게 하고, 4초에 워드마크를 가로지르는 shimmer 스윕을 한 번 넣습니다. `grain-overlay`, `parallax-zoom`, `shimmer-sweep` 레지스트리 컴포넌트를 사용하십시오. 오디오는 없습니다.

<DocsVideo title="HyperFrames video: Logo Polish" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/logo-polish-v2.mp4#t=0.1" loop />

*위 프롬프트로 렌더링했으며, 편집하지 않았습니다. "정지" 상태는 그레인, 3% 푸시, shimmer 한 번으로 살아 있습니다.*

**문자 그대로의 정지 대신 그레인을 쓰십시오.** 엔진은 작성된 최종 상태를 정확히 그대로 유지합니다.

* ❌ `로고가 나타나 끝까지 가만히 멈춰 있다`
* ✅ `로고가 자리 잡고, 그다음 그레인 오버레이와 느린 푸시로 정지 상태를 살아 있게 유지` ([앰비언트 아이들](/prompting/motion) 참고)

### 효과에 canvas 파이프라인이 필요한 경우

사람들이 헷갈리는 구분은 이것입니다. **HTML-in-Canvas 블록은 CSS가 아닙니다.** 디바이스 목업, liquid-glass 무대, `vfx-*` 블록은 실험적인 `drawElementImage` API를 통해 라이브 DOM을 WebGL 텍스처로 렌더링하며, 이 API에는 Chrome 플래그가 필요합니다. [HTML-in-Canvas 가이드](/guides/html-in-canvas)가 실제 동작을 설명합니다.

* **렌더링은 CanvasDrawElement를 자동으로 켭니다**(`--enable-features=CanvasDrawElement`). Docker 안에서도 마찬가지입니다. CanvasDrawElement만 쓰는 블록에는 이것으로 충분합니다. 이것을 WebGPU와 함께 쓰는 liquid-glass 블록은 여전히 `PRODUCER_HEADLESS_SHELL_PATH`로 설정한 Brave나 Chrome Canary 같은 호환 브라우저가 필요합니다. 번들된 headless shell은 이 조합을 실행할 수 없습니다.
* **Studio의 라이브 미리보기는 플래그를 수동으로 켜야 합니다**(`chrome://flags/#canvas-draw-element` → *Enabled* → 재시작). 플래그가 없으면 이 블록들은 효과를 보여주는 대신 대체 표시로 떨어집니다.
* 블록은 **기능을 감지하고 우아하게 기능을 낮춥니다**. 따라서 플래그가 없는 브라우저에서도 크래시는 나지 않고, WebGL 처리만 보이지 않습니다.

위의 Effects 컴포넌트에는 이런 제약이 없습니다. 순수 CSS이므로 미리보기를 포함해 어디서나 애니메이션됩니다. 그래서 오늘 설정 없이 Studio 미리보기에서 보여야 하는 것이 있다면 CSS Effects를 우선 쓰십시오. 플래그 문제가 있는 것은 HTML-in-Canvas 그룹입니다.

<Warning>
  플래그가 해당 컴퓨터에서 켜져 있는지 확인하지 않은 채 이해관계자에게 liquid-glass나 디바이스 블록의 라이브 Studio 미리보기를 약속하지 마십시오. 렌더링된 MP4에는 영향이 없지만, 브라우저 안의 미리보기는 대체 표시로 떨어질 수 있습니다. [HTML-in-Canvas 가이드](/guides/html-in-canvas)를 보십시오.
</Warning>

### 다음으로 갈 곳

* [one-shot 프롬프트의 구조](/prompting/anatomy): 골격과 화면상 문구 인용법.
* [고급스럽게 읽히는 모션](/prompting/motion): 이 마감 계층이 따르는 앰비언트 아이들 규칙.
* [복사해서 쓰는 예시](/prompting/examples): 각색할 수 있는 `vfx-liquid-background` 소셜 카드 프롬프트.
* [HTML-in-Canvas 가이드](/guides/html-in-canvas): `drawElementImage`의 동작 방식과 플래그 세부사항.

<Note>
  **캡스톤 흐름**: [Level 7 영상](/prompting/capstone)의 Surface 영역은 검사 패널을 브랜드의 유리 토큰 위에 띄웁니다. 실제 배경 블러 위의 반투명 흰색이며, 각 패널을 통해 벽화가 눈에 보이게 번져 보입니다(영상에서 잘라낸 장면, 아래 참고).
</Note>

이것은 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)에서 이 작품을 완성하는 문장입니다. 여러분의 영상에도 그대로 가져다 쓸 수 있는 프롬프트 언어입니다.

> 내부: 프로스트 유리 검사 패널(실제 반투명 — 뒤에 있는 것 위의 블러, 제품의 Studio 디자인 언어)이 라이브 값(`ease: power3.out`, 색상 토큰, fps 표시)을 담은 와이어 위에 떠 있습니다 \[…] 유리 표면은 파일의 `--glass-*` 토큰을 사용하며 실제 backdrop 블러를 적용합니다.

<DocsVideo title="HyperFrames video: Capstone Region Surface" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-surface.mp4#t=0.1" loop />

*이 문장을 렌더링한 결과이며, 완성된 영상에서 해당 영역을 잘라낸 것입니다.*

*다음: [런타임과 3D](/prompting/runtimes-and-3d). 순간이 실제로 필요로 하는 것에 따라 GSAP, Three.js, Lottie를 고르는 방법이며, 이 효과들이 렌더링되는 실제 깊이도 다룹니다.*


## 관련 주제

- [Liquid Glass](/catalog/blocks/vfx-liquid-glass.md)
- [색보정과 필름 효과](/prompting/color-grading.md)
- [캡스톤 — 하나의 여정에 담긴 모든 기법](/prompting/capstone.md)


이 문서는 개발자 문서 플랫폼인 [Mintlify](https://mintlify.com)로 작성되고 호스팅됩니다.
