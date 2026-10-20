> ## 문서 인덱스
> 전체 문서 인덱스는 다음 주소에서 가져올 수 있습니다: https://hyperframes.heygen.com/llms.txt
> 더 탐색하기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 먼저 찾아보십시오.

# 아트워크를 생성해야 할 때

> UI, 타이포그래피, 기하, 3D에는 코드로 그린 그래픽이 낫습니다. 일러스트 중심의 히어로 아트는 이미지 모델에서 가져와 레이어로 애니메이션합니다.

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

Level 1의 음악 슬라이드쇼는 실제 사진을 비트에 맞춰 잘랐습니다.
다룰 실제 아트가 있었던 셈입니다. 이 장은 반대의 경우를 다룹니다.
아직 사진이나 캡처로 존재하지 않는 히어로 캐릭터, 회화풍 장면, 조형적 오브젝트가 필요한 경우입니다.

## 코드로 잘 그리는 것, 그렇지 않은 것

코드로 그린 HTML, CSS, SVG는 매체가 본래 맞는 곳에서 뛰어납니다.
UI 목업, 타이포그래피, 기하학적 도형, 차트, 픽셀 아트, Three.js를 통한 3D가 여기에 해당합니다.

**일러스트 중심**의 히어로 아트는 예외입니다. 캐릭터, 회화풍 장면, 조형적 오브젝트는
손으로 그린 SVG가 가장 못하는 영역입니다. 프롬프트를 아무리 잘 써도 클립아트 수준에서 벗어나지 못합니다.

## 하이브리드: 아트는 생성하고, 코드로 움직이기

정지 이미지 아트는 이미지 모델에 요청하고, 움직임은 코드로 주십시오:

> Generate the hero artwork as an image (via the media-use skill's image generation), then animate it with code. Anything that must move independently — eyelids, light beams, drawing lines — stays a code layer on top of the static art.

생성된 이미지는 하나의 평평한 레이어입니다. 독립적으로 움직여야 하는 모든 것은
그 위에 코드 레이어로 남겨 둡니다.

## 이 방식이 작동하게 하는 세 가지 규칙

1. **단색의 대비되는 배경에서 생성하십시오.** 마젠타가 잘 맞습니다. 주제가
   깔끔하게 키아웃(key out)됩니다. 밝은 주제를 밝은 배경에 두면
   조용히 지워집니다.
2. **평평한 벡터풍 아트는 크로마 키(`ffmpeg colorkey`)로 키잉하십시오.** AI 배경 제거는 쓰지 마십시오.
   `remove-background`는 사람 분할용 매팅 모델을 쓰므로 사진과 사람에 맞게 튜닝되어 있습니다.
   평평한 아트는 신뢰성 있게 처리하지 못하며, 주제 대신 배경을 남기기도 합니다.
   `remove-background`는 사진에만 쓰십시오.
3. **생성 프롬프트에 절제 조항을 넣으십시오** — "minimal, lots of negative space"(최소한으로, 여백을 많이).
   이미지 모델은 기본적으로 프레임을 가득 채웁니다. 바쁘게 생성된 질감은
   나쁜 벡터 아트만큼 싸구려로 보입니다.

## 차이, 나란히 보기

같은 브리프를 두 방식으로 만들었습니다. 따뜻한 그라데이션 스웨터를 입고 팔짱을 낀 네 사람,
플랫 일러스트 스타일입니다. 애니메이션 비트와 조명, 분위기, 그레이딩 같은 제작 레이어는 같습니다.
달라지는 변수는 인물의 출처뿐입니다.

<DocsVideo title="HyperFrames video: Artwork Hand Drawn" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/artwork-hand-drawn.mp4#t=0.1" loop />

*손으로 그린 SVG 인물입니다. 깔끔하지만 비율과 제스처가 클립아트처럼 읽힙니다.*

<DocsVideo title="HyperFrames video: Artwork Generated" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/artwork-generated.mp4#t=0.1" loop />

*생성된 일러스트를 레이어로 나눠 애니메이션한 결과입니다. 실제 해부학적 비율과 편집 디자인풍 음영이 있습니다.
아트를 투명도로 키잉했기 때문에, 움직이는 선이 인물 뒤를 지나갑니다.*

<Note>
  **캡스톤 스레드** — [Level 7 영화](/prompting/capstone)의 Surface 영역은 생성된 아트워크 위에 있습니다.
  뮤럴은 팔레트 중립으로 생성된 뒤, 컴포지션의 두 변수로부터 CSS가 실시간으로 듀오톤 처리합니다.
  따라서 `--variables` 렌더링에서는 래스터 이미지조차 다시 입혀집니다. 이 영역은 아래 영화에서 잘라낸 것입니다.
</Note>

이 절을 만드는 것은 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)에 있습니다.
여러분의 영상에 가져다 쓸 수 있는 프롬프트 문구입니다:

> \[…] over a **generated-artwork backdrop** — a flat abstract mural evoking motion trails, generated **palette-neutral (grayscale) and duotoned live by CSS** from the two variables so it re-skins with everything else. **The mural is a full-frame, screen-fixed backdrop: it never moves on screen — the widening iris circle alone reveals it already in place at full frame \[…] and it exits by fading out.**

<DocsVideo title="HyperFrames video: Capstone Region Surface" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-surface.mp4#t=0.1" loop />

*이 절을 렌더링한 결과이며, 완성된 영화에서 해당 영역만 잘라낸 것입니다.*

*다음: [색보정과 필름 효과](/prompting/color-grading) — 톤 작업, 색상 키, 인쇄물과 아날로그 룩,
그리고 페이로드보다 소스가 중요한 이유처럼 미디어 자체를 다룹니다.*


## 관련 주제

- [고품질 룩](/prompting/visual-specs.md)
- [캡스톤 — 모든 기법, 하나의 여정](/prompting/capstone.md)
- [캡션 스타일](/prompting/captions-catalog.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 만들어져 호스팅됩니다.
