> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# 검증된 예시 프롬프트

> 이 페이지의 영상을 만들 때 사용한 프롬프트와, 각 프롬프트와 함께 실행한 공통 모션 프리앰블입니다.

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

이 페이지는 새로운 강의가 아니라 레벨의 갤러리입니다. 방금 익힌 어휘와 함께 읽어 보십시오. 각 프롬프트에서 [6부 골격](/prompting/anatomy), [사양 다이얼](/prompting/specification-dial), 그리고 이에 대응하는 [단어 목록](/prompting/vocabulary)이나 [전체 시각 사양](/prompting/visual-specs)을 확인하면서 읽으면 골격의 각 부분이 어떻게 쓰였는지 보입니다.

아래의 모든 영상은 해당 프롬프트와 **다음 문단의 공통 프리앰블을 함께** 사용해 만들었습니다. 프리앰블을 먼저, 그다음 프롬프트를 복사하고, 문구·색상·입력값만 자신의 것으로 바꾸십시오. 프롬프트만 단독으로 붙여 넣으면 다른 영상이 나옵니다. 모션 문법이 각 프롬프트가 아니라 프리앰블에 들어 있기 때문입니다.

<Note>
  **공통 프리앰블 — 이 페이지의 모든 프롬프트 위에 붙여 넣으십시오.** 개별 프롬프트를 읽기 쉽게 유지하기 위해 [3단계 모션 문법](/prompting/motion)을 담고 있습니다. 모든 항목은 밀도 계약(디스플레이 크기의 초점 요소 하나, 독립된 신호에 맞춰 나타나는 보조 요소, 항상 보이는 크롬), 하나의 연속적이고 멈추지 않는 카메라 아래의 시차를 가진 3개 깊이 레이어, 연출되는 시간보다 짧은 간격으로 어긋나 나타나는 진입, 변형에만 적용되는 오버슈트, 그리고 정지된 마지막 프레임 대신 은은한 유휴 움직임을 요구합니다. 각 프롬프트가 개별적으로 명시하는 것은 그 영상의 **스펙터클 비트**입니다. 이는 적절한 위치에 배치된 단 하나의 과장된 순간입니다. 이 절은 중요합니다. 이름이 없는 폭발 효과는 빠지기 쉬운데, 카운트업의 컨페티가 기록되기 전에 실제로 그렇게 사라졌습니다.
</Note>

### 등록 블록과 워크플로 사용

<AccordionGroup>
  <Accordion title="Stat count-up">
    > /motion-graphics 6-second 1920x1080 video, dark navy background. Beat 1 (0-1s): label "ARR" fades up small, top-center. Beat 2 (1-4s): a giant number counts up to \$4.2M with an odometer roll, easing out as it lands. Beat 3 (4-6s): "+312% YoY" stamps in below in green, then everything settles into a gentle ambient idle (subtle breathing scale, slow particle drift). Use the `apple-money-count` registry block as base. No narration. **Spectacle beat:** On the land at 4s, a burst of \~60 paper money notes erupts from behind the numeral and flutters down, seeded so every render is identical, settled by 5.5s — the one exaggeration.

    <DocsVideo title="HyperFrames video: Example Stat Countup" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-stat-countup.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Animated social post">
    > /motion-graphics 7-second 1080x1350 vertical video. A real tweet card (handle @hyperframes, text "we render video from HTML now. no timeline UI. just code.") slides up over a soft animated gradient, likes counter ticks 0→1.2K, then the card tilts in 3D and a highlight sweeps the second sentence. Hold on the card at the end with a subtle ambient idle (slow breathing scale). Use the `x-post` and `vfx-liquid-background` registry blocks. No narration, no image or media files. **Spectacle beat:** When the like count lands, the heart pops to 1.6× with a radial burst of \~24 seeded particles and settles — one moment, nothing else exaggerated.

    <DocsVideo title="HyperFrames video: Example Tweet" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-tweet.mp4#t=0.1" portrait loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Map route">
    > /motion-graphics 8-second 1920x1080 video. Dark world map, a glowing arc animates from San Francisco to Tokyo over 3s, destination pin drops with a pulse, then camera zooms into Tokyo and the label "LATENCY: 89ms" types on. Use the `nyc-paris-flight` registry block as the base pattern, restyle to teal on charcoal. No narration. **Spectacle beat:** The destination pin's landing fires a triple concentric shockwave that expands past the label and fades, with a brief chromatic split on the pin.

    <DocsVideo title="HyperFrames video: Example Map Route" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-map-route.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Logo sting with shader transition">
    > /motion-graphics 5-second 1920x1080 logo sting. Beat 1 (0-2s): the word "ACME" assembles from scattered particles. Beat 2 (2-3s): full-frame `swirl-vortex` shader transition. Beat 3 (3-5s): logo lockup + tagline "Ship faster." settles on white and holds with a subtle ambient idle. Use `code-particle-assemble` for the assembly. **Spectacle beat:** The particle assembly IS the spectacle — \~1200 seeded particles converging with visible motion trails, and a single bloom flash on the frame the wordmark completes.

    <DocsVideo title="HyperFrames video: Example Logo Sting" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-logo-sting.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Product launch from a URL">
    > /product-launch-video Make a 45-second 1920x1080 launch video for [https://linear.app](https://linear.app). Energetic but minimal, use the site's own palette and screenshots. Structure: hook stating the problem, 3 feature beats with UI captures and one-line captions, end card with logo + "Try it free". Female TTS voice, confident tone, subtle electronic BGM under -18dB. **Spectacle beat:** One exaggerated moment: the end card's logo lands with a bloom flash and a fast light-sweep across the wordmark. Feature beats stay restrained.

    <DocsVideo title="HyperFrames video: Example Product Launch" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-product-launch-v2.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Explainer from pasted text">
    > /faceless-explainer Turn this into a \~60-second 1080x1920 vertical explainer: \[paste your text]. One idea per scene, big typography, diagrams over stock footage, brand color #FF5533 on off-black. Male TTS voice, calm. Embedded captions, keywords highlighted in the brand color. **Spectacle beat:** One exaggerated moment: the final CTA's key phrase slams in at 1.5× with a chromatic split that resolves in 0.2s. Every other scene stays typographically calm.

    대본을 그대로 쓰는 경우 최종 길이는 나레이션을 따릅니다. 정확히 60초가 아니라 "\~60 seconds"처럼 요청하십시오.

    <DocsVideo title="HyperFrames video: Example Explainer" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-explainer-v2.mp4#t=0.1" portrait loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="GitHub PR reveal">
    > /pr-to-video Make a 30-second 1920x1080 feature-reveal video from \[PR URL]. Lead with what users get, not the diff; show the key code change with the `code-diff` block for one beat only; end on version number + repo URL. No narration, kinetic captions instead. **Spectacle beat:** The added line in the diff ignites — a green light-sweep travels its length and the line blooms as the camera settles on it.

    <DocsVideo title="HyperFrames video: Example Pr Video" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-pr-video-v2.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Beat-synced slideshow">
    > /music-to-video 20-second 1080x1080 video. Resolve a dark, driving electronic track and cut to its analyzed beat grid — one image per bar, punch-in on downbeats, whip-pan transitions on phrase changes. Generate the eight images rather than using stock: brutalist concrete details as high-contrast monochrome abstracts, one consistent visual language across all eight, each carrying a single cyan light thread. Chrome: a `PLATE 0N/08` counter. End card "CAST IN PLACE" in condensed caps over a hard-edged opaque scrim, with the sub-line "EIGHT SURFACES · ONE HUNDRED BPM". No TTS. **Spectacle beat:** On the loudest downbeat, one image punches to 1.25× with an RGB channel split that snaps back on the next beat. The other cuts stay clean.

    <DocsVideo title="HyperFrames video: Example Music Slideshow" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-music-slideshow-v2.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>
</AccordionGroup>

### 자유 형식 — 블록 없이 손으로 만든 HTML/CSS/SVG/GSAP

<AccordionGroup>
  <Accordion title="Kinetic quote">
    > 12-second 1920x1080 video, off-white background. The quote "Simplicity is the ultimate sophistication" builds word by word in massive black serif type, each word snapping in with a slight overshoot; "sophistication" lands last in italic with a hand-drawn underline drawing on. Attribution "— Leonardo da Vinci" fades in small, bottom-right, at 9s. Settle into a barely-visible ambient idle to the end. No audio. **Spectacle beat:** The final word lands 1.4× oversized with an ink-bleed bloom before settling to its true size — the sentence's payoff.

    <DocsVideo title="HyperFrames video: Example Kinetic Quote" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-kinetic-quote-v2.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Countdown title card">
    > 6-second 1920x1080 video. Numbers 3, 2, 1 each fill the frame for one second — each number wipes in with a diagonal mask and its background alternates black/white with inverted text. At 3s the frame slams to "LAUNCH DAY" in condensed caps with a screen-shake, holds with a subtle grain flicker. No audio. **Spectacle beat:** The frame snap at 3s is the moment — a hard white flash frame and a 1.5° rotation kick settling in 0.25s.

    <DocsVideo title="HyperFrames video: Example Countdown" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-countdown.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Bar chart race">
    > 10-second 1920x1080 video, dark slate background. Title "Top languages 2026" top-left. Five horizontal bars (Python, TypeScript, Rust, Go, Java) grow from zero with staggered starts, overtaking each other twice mid-animation; each bar has a right-edge value label counting up to its final %. End state holds 2s with the leader pulsing once. Hand-draw everything — no chart library. No audio. **Spectacle beat:** The leader's single end pulse is the moment — a +16px overshoot and a bright cap flare, returning to rest exactly on the last frame.

    <DocsVideo title="HyperFrames video: Example Bar Race" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-bar-race.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Before / after split">
    > 8-second 1920x1080 video. Vertical split: left half labeled "BEFORE" shows a cluttered mock UI (grey, 12 overlapping windows drawn in CSS), right half "AFTER" shows one clean card. Both halves settle within the first second. A vertical divider line sweeps left to right at 4s, wiping the clutter into the clean state across the full frame. End on "One tool." centered. No audio. **Spectacle beat:** The divider's wipe is the moment — a bright scan-line travels the split with a bloom as it crosses, and the AFTER half resolves behind it.

    <DocsVideo title="HyperFrames video: Example Before After" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-before-after.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Loader → reveal">
    > 7-second 1920x1080 video, black background. A thin white progress ring draws from 0° to 360° over 4s while a percentage counter (0→100) ticks in the center in mono type, matching the arc exactly. Ring and counter fade out fully by 4.2s; at 4.2s the ring bursts outward into short radial dashes and "READY." stamps into the center, then holds with a subtle ambient idle (slow breathing scale). No audio. **Spectacle beat:** The ring's completion at 100% detonates — it flashes white, expands past frame, and the reveal rides that expansion out.

    <DocsVideo title="HyperFrames video: Example Loader Ready" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-loader-ready.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="3D cards (Three.js)">
    > 9-second 1920x1080 video, light warm cream background. Build the scene in Three.js via the adapter: three rounded card meshes labeled "Design", "Build", "Ship" lie flat on the ground plane, camera at a fixed 3/4 isometric angle, soft directional light + ambient so the cards cast soft shadows. One at a time each card lifts and straightens upright to face the viewer center-frame while the other two slide apart and dim; then it returns. Finish with all three standing upright in a row by 8.5s, hold with a subtle ambient idle. All easing power3.inOut. No audio. **Spectacle beat:** As the cards rise into their stack, a single specular sweep rakes across all three faces in sequence, catching each edge.

    <DocsVideo title="HyperFrames video: Example 3d Cards" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-3d-cards.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="SVG line-draw logo reveal">
    > 6-second 1920x1080 video, deep green background. A minimal mountain-range logo draws on as an SVG stroke over 2.5s, then the stroke fills with cream, the wordmark "NORTHTRAIL" letterspaces in beneath it, and a thin rule expands from center. Hold the last 1.5s with a subtle ambient idle. No audio. **Spectacle beat:** The stroke's completion is the moment — the drawn path flares once along its whole length, then the fill floods from that flare.

    <DocsVideo title="HyperFrames video: Example Svg Logo" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-svg-logo.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Word-swap headline">
    > 8-second 1920x1080 video, white background. Static sentence "Make it \_\_\_." in huge black type stays centered while the blank cycles through "faster", "simpler", "yours" — each swap flips vertically like a split-flap board, 1.5s apart, with a slight blur on motion. Final word "yours." lands in orange and the period pops. No audio. **Spectacle beat:** The last swap lands hardest — that word arrives 1.3× behind a motion-blur streak that resolves as it settles.

    <DocsVideo title="HyperFrames video: Example Word Swap" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-word-swap.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Stat tile dashboard">
    > 10-second 1920x1080 video, near-black background. Four stat tiles slide up in a 2x2 grid, staggered: "99.99% uptime", "42ms p50", "18M req/day", "0 incidents". Each tile's number counts or decrements to its value with its own easing; sparklines draw underneath in teal. At 8s the grid scales back and "Built to hold." fades in above. No audio. **Spectacle beat:** When the fourth tile lands, all four numerals flare in unison for three frames — one synchronized accent, then back to restrained idles.

    <DocsVideo title="HyperFrames video: Example Data Ticker" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-data-ticker.mp4#t=0.1" loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>

  <Accordion title="Vertical social hook">
    > 9-second 1080x1920 vertical video, charcoal background. Social-style hook: "nobody talks about this" types on center in bold white, then each following phrase replaces it on a hard cut every 1.5s — "it's not your code", "it's your prompts", "here's the fix" — with yellow highlight bars behind key words, alternating tilt. Last phrase holds with an arrow-down bounce. No audio. **Spectacle beat:** The final phrase is the payoff — it slams in at 1.35× with a three-frame shake and a chromatic split that resolves fast.

    <DocsVideo title="HyperFrames video: Example Vertical Hook" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-vertical-hook.mp4#t=0.1" portrait loop />

    *위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*
  </Accordion>
</AccordionGroup>

*다음: [읽기 쉬운 프로덕션 모션](/prompting/motion) — 3단계: 이 동작들이 평범하지 않고 전문적으로 보이는 이유를 설명하는 문법 규칙입니다.*


## 관련 주제

- [고충실도 룩](/prompting/visual-specs.md)
- [오버레이와 하단 자막](/prompting/overlays-and-lower-thirds.md)
- [자막 스타일](/prompting/captions-catalog.md)


이 문서는 [Mintlify](https://mintlify.com)로 빌드되고 호스팅됩니다. Mintlify는 개발자 문서 플랫폼입니다.
