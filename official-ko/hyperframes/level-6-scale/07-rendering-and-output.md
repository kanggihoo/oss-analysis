> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져오세요.
> 더 살펴보기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾으세요.

# 렌더링과 출력

> 올바른 파일을 내보내려면 무엇을 말해야 하는지 알아봅니다. 품질 등급, 형식, 해상도, 프레임레이트, 클라우드 렌더링을 다루며, 효과가 없는데 렌더를 과하게 지정해 느려지는 일을 피하는 방법도 함께 설명합니다.

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

[이전에 본 것 재현하기](/prompting/recreating-references)에서 다룬 프레임 단위 매칭을 포함해, 지금까지의 모든 내용은 컴포지션을 만듭니다. 이 페이지는 *내보내기*에 관한 내용입니다. 즉 품질 등급, 컨테이너 형식, 해상도, 렌더를 실행할 위치를 고르는 말입니다. 기본값인 MP4, 1920×1080, 30fps, `standard` 품질은 의도적으로 좋게 설정되어 있으므로, 이 단계의 핵심은 더 요청하지 않아야 할 때를 아는 것입니다. 세부 메커니즘은 [렌더링 가이드](/guides/rendering)에 있고, 이 페이지는 무엇을 말해야 하는지를 다룹니다.

## 품질 등급

등급 이름을 말하면 에이전트가 맞는 인코딩 프리셋을 고릅니다. CRF나 인코더 속도를 직접 지정할 필요가 없습니다:

| 이렇게 말하면 | 등급 | 적합한 용도 |
| - | - | - |
| "draft" / "quick render" | `draft` | 컷을 아직 판단하는 중일 때의 빠른 반복 작업 |
| 아무 말 없음, 또는 "review render" | `standard` (기본값) | 일반적인 용도. 1080p에서 시각적으로 무손실 |
| "final" / "high quality" | `high` | 납품용 마스터 |

등급은 인코딩 시간과 충실도를 맞바꿉니다. 기본값인 `standard`는 1080p에서 이미 시각적으로 무손실이어서 대부분의 사람은 원본과 구별하지 못합니다. 따라서 `high`는 실제로 넘길 마스터에만 아껴 쓰고, `draft`는 작업하는 동안 자유롭게 쓰세요.

* ❌ `render everything at high quality`
* ✅ `draft renders while we iterate, then one high-quality final` — 이미 승인한 컷에 대해 느린 인코딩을 한 번만 씁니다

## 형식

MP4가 기본값이며 거의 모든 경우에 맞는 선택입니다. 어디서나 재생되기 때문입니다. 납품 대상이 다른 컨테이너를 요구할 때만 다른 형식을 요청하세요:

> Render this as a transparent WebM overlay.

> Export a MOV I can drop into Premiere with the background knocked out.

투명도에는 컨테이너 위계가 있고, 그 트레이드오프는 실제로 존재합니다:

| 요청 | 결과 | 주의할 점 |
| - | - | - |
| "transparent MOV" | 알파가 있는 ProRes 4444 | 편집용 등급의 선택입니다(Premiere, Final Cut, Resolve, After Effects). 파일이 큽니다. 편집용 중간 파일이라면 예상된 결과입니다. |
| "transparent WebM" | 알파가 있는 VP9 | 작지만, **브라우저만 알파를 디코딩합니다**. 모든 영상 편집기는 투명 영역을 검은색으로 렌더링합니다. 브라우저 재생 전용입니다. |
| "PNG sequence" | 무손실 RGBA 프레임 | After Effects / Nuke / Fusion에서 합성할 때 씁니다. 셋 중 가장 큽니다. |

투명도는 투과해서 볼 빈 공간이 있는 디자인에서만 *의미*가 있습니다. 하단 자막(lower third), 구독 카드, 로고 스팅은 대부분 빈 캔버스이므로, 투명도를 주면 다른 영상 위에 합성할 수 있습니다. 전체 화면 장면(가장자리까지 채운 배경, 전체 화면 영상, 자체 배경이 있는 타이틀 카드)은 투명하게 만들 것이 없습니다. 그런 요청은 불투명한 파일과 똑같아 보이지만 더 크고 재생될 수 있는 곳이 더 적은 파일을 만듭니다.

* ❌ `render my full-screen product promo as a transparent WebM`
* ✅ `render the promo as MP4; export just the lower-third overlay as transparent WebM` — 투명도는 다른 영상 *위에* 놓일 레이어에 주어야 하며, 완성된 전체 화면 필름에는 주지 않습니다

<DocsVideo title="HyperFrames video: Overlay Spotify Preview" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/overlay-spotify-preview.mp4#t=0.1" portrait loop />

*체커보드 위에 미리보기한 투명 VP9 WebM 오버레이입니다. CLI에서 알파를 확인하려면, VP9는 알파를 대역 외(out-of-band)로 저장하므로 ffprobe에서 ALPHA\_MODE=1을 찾거나 ffmpeg alphaextract로 알파를 추출하세요. pix\_fmt만 확인하면 잘못 음성으로 판단할 수 있습니다.*

<Note>
  투명 렌더는 컴포지션의 `html` / `body` 배경을 설정하지 않은 상태에 의존합니다. 그래야 아무것도 칠해지지 않은 곳에서만 투명도가 나타납니다. 워크플로 스킬이 이를 처리하며, 오버레이를 직접 작성하는 경우에는 [렌더링 가이드](/guides/rendering#transparent-video)를 보세요.
</Note>

## 해상도와 프레임레이트

기본값은 1920×1080, 30fps입니다. 둘 다 올리면 실제 시간이 듭니다. 그런데 둘 다 필요해서가 아니라 습관적으로 요청하는 경우가 많습니다.

**4K**는 렌더 시점 플래그입니다. 컴포지션은 작성한 크기를 유지하고, Chrome이 3840×2160으로 슈퍼샘플링합니다. 그 결과 어떤 배율에서도 텍스트, SVG, CSS가 선명해지지만, 이미 픽셀 격자에 고정된 콘텐츠에는 아무 효과가 없습니다. 1080p `<video>`, 고정 크기 `<canvas>`, 4K보다 작은 이미지는 이 설정으로 디테일이 늘지 않습니다. 또한 공짜가 아닙니다. 4K 렌더는 프레임당 약 **4배** 느리고, 파일은 **3–5배** 큽니다. 납품 화면이 실제로 필요로 할 때(4K 디스플레이, 클라이언트 사양)에만 요청하고, 습관적으로 요청하지 마세요.

> Render this at 4K for the trade-show display.

**프레임레이트**도 같은 논리를 따릅니다. 60fps는 엔진이 캡처하고 인코딩하는 프레임을 두 배로 늘립니다. 고주사율 화면을 위한 빠른 모션 그래픽에는 가치가 있지만, 토킹 헤드 클립이나 느린 타이틀 시퀀스에는 낭비입니다.

* ❌ 인스타그램용 클립에 `render in 4K 60fps` — 플랫폼이 어차피 다운스케일해서, 느린 렌더 비용만 치르게 됩니다
* ✅ 소셜용이라면 아무 말도 하지 않습니다. 대상이 실제로 해상도나 `60fps`를 활용할 때만 `4K`(또는 `60fps`)를 말하세요

<Warning>
  4K 제약 중 일부는 렌더가 시작되기도 전에 멈추게 합니다([4K 가이드](/guides/4k-rendering#constraints)에 근거가 있습니다). 대상 방향이 컴포지션의 종횡비와 맞아야 하고, 배율은 정수여야 하며(1080p → 4K는 정확히 2배), **4K는 한 번의 패스에서 HDR과 함께 쓸 수 없습니다**. 둘 다 필요하다면 HDR은 컴포지션 해상도로 렌더하고, 업스케일은 따로 하세요.
</Warning>

## HDR

HDR 출력은 **HDR10 MP4**(H.265 10비트, BT.2020)이며, *소스 기반*입니다. 컴포지션이 실제로 HDR 미디어를 참조할 때만 HDR로 렌더됩니다. 여기서 HDR 미디어란 PQ 또는 HLG 전달 함수를 가진 BT.2020 태그 영상이나 16비트 PNG를 말합니다. 텍스트, 그라데이션, GSAP 애니메이션은 HDR 소스가 아닙니다. 이것만으로 구성된 컴포지션은 HDR로 렌더할 것이 없습니다.

> This composition has an HDR drone clip — render it as HDR10.

기본적으로 HDR은 자동 감지되므로, 프로젝트에 실제 HDR 소스가 있다면 아무 말도 하지 않아도 되는 경우가 많습니다. 프로브 결과를 무시하고 싶을 때만 명시적으로 지정하세요:

* "force HDR" → 감지된 HDR 소스가 없어도 HDR 경로를 강제합니다
* "force SDR" → HDR 소스가 있어도 표준 범위를 강제합니다

HDR은 **MP4에서만** 가능하며(투명 MOV/WebM 요청은 SDR로 대체됩니다), **Lambda에서는 사용할 수 없습니다**(분산 렌더링은 SDR 전용입니다). 소스 요구 사항과 검증 방법은 [HDR 가이드](/guides/hdr)를 보세요.

## 렌더를 실행할 위치

로컬 렌더링은 기본값이며, 전체 반복 작업 루프에 맞는 선택입니다. 단일 머신이 병목일 때만 클라우드 렌더링을 쓰세요:

> Render this on Lambda.

이 요청은 HyperFrames의 AWS Lambda 경로로 연결되며, 렌더를 여러 병렬 워커에 나눕니다. 한 호스트에 비해 **너무 길거나 너무 큰** 렌더에 맞습니다. 예를 들어 수 분짜리 영상, 4K 마스터, 대규모 병렬 배치가 여기에 해당합니다. 먼저 AWS 자격 증명을 설정해야 합니다. 개발 루프에서 반복 작업을 할 때는 로컬 `render`를 쓰세요. 왕복 시간이 어떤 클라우드 디스패치보다도 빠릅니다. Lambda는 SDR 전용(HDR 불가)이며 컴퓨팅 시간에 따라 과금됩니다. 설정, 비용 구조, 보수적인 동시성 기본값은 [AWS Lambda 가이드](/deploy/aws-lambda)에서 다룹니다.

* ❌ `set up Lambda so I can preview edits faster` — 빠른 로컬 루프에 클라우드 디스패치는 지연만 더합니다
* ✅ `render the final 3-minute 4K cut on Lambda` — 여러 대로 나눌 가치가 실제로 있는 작업입니다

Lambda만 원격 대상은 아닙니다. **HeyGen 호스팅 클라우드 렌더링**([가이드](/deploy/cloud))은 인프라를 완전히 넘겨줍니다. AWS 계정을 설정할 필요가 없습니다. **Google Cloud Run**([가이드](/deploy/gcp-cloud-run))은 스택이 이미 GCP에 있을 때 쓰는 선택지입니다. 원하는 대상을 이름으로 말하세요("render this on Cloud Run"). 라우팅은 추론하지 않고 명시적으로 이루어집니다.

## 느린 렌더를 하기 전에 미리보기

잘못 걸린 `high`/4K/HDR 렌더를 피하는 가장 저렴한 방법은 프레임을 먼저 판단하는 것입니다. 워크플로 스킬이 따르는 습관은 다음과 같습니다:

1. `preview`를 실행한 채로 타임라인을 훑어봅니다. 렌더와 같은 런타임이므로, 보는 것이 곧 얻는 것입니다.
2. 실제 파일이 필요하면 `draft` 렌더로 반복합니다.
3. 컷이 확정되었을 때만 최종 등급, 해상도, 형식을 요청합니다.

* ❌ 끝까지 보지 않은 컷에 대해 `render the final 4K HDR master`
* ✅ `draft render so I can check timing` → 승인 → `now the 4K final`

<Tip>
  렌더는 설계상 사용자가 승인해야 진행됩니다. 에이전트는 미리보기에서 멈추고, 여러분이 승인할 때만 렌더합니다. 이 멈춤을 이용해 비싼 내보내기를 하기 전에 컷을 확정하세요.
</Tip>

## 관련 링크

<CardGroup cols={2}>
  <Card title="Iterating" href="/prompting/iterating">렌더 사이의 작은 목표 편집이며, 재지정이 아닙니다</Card>
  <Card title="Rules and anti-patterns" href="/prompting/rules-and-anti-patterns">해상도와 프레임레이트를 과하게 지정하면 왜 역효과가 나는지</Card>
  <Card title="Rendering guide" href="/guides/rendering">형식, 품질 프리셋, 워커 — 메커니즘</Card>
  <Card title="AWS Lambda" href="/deploy/aws-lambda">클라우드 렌더링 설정과 비용</Card>
</CardGroup>

<Note>
  **캡스톤 흐름** — [7단계 필름](/prompting/capstone)은 이 장의 핵심 약속으로 끝납니다. 주인공 칩이 렌더 슬롯에 스냅되고, 시드 기반 컨페티가 각 조각을 정확히 두 프레임 동안 붙잡습니다. 결정론적이며, 렌더할 때마다 동일합니다(아래 필름에서 잘라낸 부분). 그 Everywhere 영역은 실제 클라우드 렌더 대상인 Lambda와 Cloud Run을 명시합니다.
</Note>

이것은 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)에서 이 작품을 완성하는 절입니다. 여러분의 영상에도 가져다 쓸 수 있는 프롬프트 표현입니다:

> A **seeded confetti burst** fires — mulberry32, **seed 42, each piece holding position for exactly two frames before stepping** (stop-motion feel) — and the VO lands the honest punchline: identical on every render, because determinism is the whole point.

<DocsVideo title="HyperFrames video: Capstone Region Render" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-render.mp4#t=0.1" loop />

*이 절을 렌더링한 결과입니다. 시드 기반 컨페티이며, 이 컴포지션의 렌더마다 동일합니다.*

*다음: [Remotion에서 옮기기](/prompting/remotion-migration) — 기존 Remotion 프로젝트를 지금까지 배운 모든 내용에 맞게 가져오기.*


## 관련 주제

- [출력을 바꾸는 어휘](/prompting/vocabulary.md)
- [본 것 재현하기](/prompting/recreating-references.md)
- [오버레이와 하단 자막](/prompting/overlays-and-lower-thirds.md)


이 문서는 [Mintlify](https://mintlify.com)로 빌드되고 호스팅되는 개발자 문서 플랫폼에서 제공됩니다.
