> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Verified example prompts

> Prompts that produced the videos on this page, plus the shared motion preamble each one was run with.

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

This is the level's gallery, not a new lesson — read these with the vocabulary you just picked up: the [six-part skeleton](/prompting/anatomy), the [specification dial](/prompting/specification-dial), and the [word list](/prompting/vocabulary) or [full visual spec](/prompting/visual-specs) it maps to. Spot the skeleton parts in each prompt below as you read it.

Every video below was produced by the prompt beneath it **plus the shared
preamble in the next paragraph**. Copy both — the preamble first, then the
prompt — and swap the copy, colors and inputs for your own. Pasting a prompt
on its own gives you a different video, because the motion grammar lives in
the preamble rather than in each one.

<Note>
  **The shared preamble — paste this above any prompt on this page.** It carries the [Level 3 motion grammar](/prompting/motion) so the individual prompts stay readable. Every one asks for the density contract (one focal element at display scale, supporting elements on their own cues, permanent chrome), three depth layers with parallax under one continuous non-settling camera, entrances staggered at offsets shorter than the animations they offset, overshoot on transforms only, and an ambient idle instead of a frozen final frame. What each prompt *does* state individually is its **spectacle beat** — the single exaggerated moment, placed where the piece earns it. That clause is load-bearing: an unnamed burst gets dropped, which is exactly what happened to the count-up's confetti before it was written down.
</Note>

### With registry blocks and workflows

<AccordionGroup>
  <Accordion title="Stat count-up">
    > /motion-graphics 6-second 1920x1080 video, dark navy background. Beat 1 (0-1s): label "ARR" fades up small, top-center. Beat 2 (1-4s): a giant number counts up to \$4.2M with an odometer roll, easing out as it lands. Beat 3 (4-6s): "+312% YoY" stamps in below in green, then everything settles into a gentle ambient idle (subtle breathing scale, slow particle drift). Use the `apple-money-count` registry block as base. No narration. **Spectacle beat:** On the land at 4s, a burst of \~60 paper money notes erupts from behind the numeral and flutters down, seeded so every render is identical, settled by 5.5s — the one exaggeration.

    <DocsVideo title="HyperFrames video: Example Stat Countup" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-stat-countup.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Animated social post">
    > /motion-graphics 7-second 1080x1350 vertical video. A real tweet card (handle @hyperframes, text "we render video from HTML now. no timeline UI. just code.") slides up over a soft animated gradient, likes counter ticks 0→1.2K, then the card tilts in 3D and a highlight sweeps the second sentence. Hold on the card at the end with a subtle ambient idle (slow breathing scale). Use the `x-post` and `vfx-liquid-background` registry blocks. No narration, no image or media files. **Spectacle beat:** When the like count lands, the heart pops to 1.6× with a radial burst of \~24 seeded particles and settles — one moment, nothing else exaggerated.

    <DocsVideo title="HyperFrames video: Example Tweet" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-tweet.mp4#t=0.1" portrait loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Map route">
    > /motion-graphics 8-second 1920x1080 video. Dark world map, a glowing arc animates from San Francisco to Tokyo over 3s, destination pin drops with a pulse, then camera zooms into Tokyo and the label "LATENCY: 89ms" types on. Use the `nyc-paris-flight` registry block as the base pattern, restyle to teal on charcoal. No narration. **Spectacle beat:** The destination pin's landing fires a triple concentric shockwave that expands past the label and fades, with a brief chromatic split on the pin.

    <DocsVideo title="HyperFrames video: Example Map Route" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-map-route.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Logo sting with shader transition">
    > /motion-graphics 5-second 1920x1080 logo sting. Beat 1 (0-2s): the word "ACME" assembles from scattered particles. Beat 2 (2-3s): full-frame `swirl-vortex` shader transition. Beat 3 (3-5s): logo lockup + tagline "Ship faster." settles on white and holds with a subtle ambient idle. Use `code-particle-assemble` for the assembly. **Spectacle beat:** The particle assembly IS the spectacle — \~1200 seeded particles converging with visible motion trails, and a single bloom flash on the frame the wordmark completes.

    <DocsVideo title="HyperFrames video: Example Logo Sting" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-logo-sting.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Product launch from a URL">
    > /product-launch-video Make a 45-second 1920x1080 launch video for [https://linear.app](https://linear.app). Energetic but minimal, use the site's own palette and screenshots. Structure: hook stating the problem, 3 feature beats with UI captures and one-line captions, end card with logo + "Try it free". Female TTS voice, confident tone, subtle electronic BGM under -18dB. **Spectacle beat:** One exaggerated moment: the end card's logo lands with a bloom flash and a fast light-sweep across the wordmark. Feature beats stay restrained.

    <DocsVideo title="HyperFrames video: Example Product Launch" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-product-launch-v2.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Explainer from pasted text">
    > /faceless-explainer Turn this into a \~60-second 1080x1920 vertical explainer: \[paste your text]. One idea per scene, big typography, diagrams over stock footage, brand color #FF5533 on off-black. Male TTS voice, calm. Embedded captions, keywords highlighted in the brand color. **Spectacle beat:** One exaggerated moment: the final CTA's key phrase slams in at 1.5× with a chromatic split that resolves in 0.2s. Every other scene stays typographically calm.

    With a verbatim script, final duration follows the narration — ask for "\~60 seconds", not exactly 60.

    <DocsVideo title="HyperFrames video: Example Explainer" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-explainer-v2.mp4#t=0.1" portrait loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="GitHub PR reveal">
    > /pr-to-video Make a 30-second 1920x1080 feature-reveal video from \[PR URL]. Lead with what users get, not the diff; show the key code change with the `code-diff` block for one beat only; end on version number + repo URL. No narration, kinetic captions instead. **Spectacle beat:** The added line in the diff ignites — a green light-sweep travels its length and the line blooms as the camera settles on it.

    <DocsVideo title="HyperFrames video: Example Pr Video" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-pr-video-v2.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Beat-synced slideshow">
    > /music-to-video 20-second 1080x1080 video. Resolve a dark, driving electronic track and cut to its analyzed beat grid — one image per bar, punch-in on downbeats, whip-pan transitions on phrase changes. Generate the eight images rather than using stock: brutalist concrete details as high-contrast monochrome abstracts, one consistent visual language across all eight, each carrying a single cyan light thread. Chrome: a `PLATE 0N/08` counter. End card "CAST IN PLACE" in condensed caps over a hard-edged opaque scrim, with the sub-line "EIGHT SURFACES · ONE HUNDRED BPM". No TTS. **Spectacle beat:** On the loudest downbeat, one image punches to 1.25× with an RGB channel split that snaps back on the next beat. The other cuts stay clean.

    <DocsVideo title="HyperFrames video: Example Music Slideshow" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-music-slideshow-v2.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>
</AccordionGroup>

### Freeform — no blocks, hand-built HTML/CSS/SVG/GSAP

<AccordionGroup>
  <Accordion title="Kinetic quote">
    > 12-second 1920x1080 video, off-white background. The quote "Simplicity is the ultimate sophistication" builds word by word in massive black serif type, each word snapping in with a slight overshoot; "sophistication" lands last in italic with a hand-drawn underline drawing on. Attribution "— Leonardo da Vinci" fades in small, bottom-right, at 9s. Settle into a barely-visible ambient idle to the end. No audio. **Spectacle beat:** The final word lands 1.4× oversized with an ink-bleed bloom before settling to its true size — the sentence's payoff.

    <DocsVideo title="HyperFrames video: Example Kinetic Quote" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-kinetic-quote-v2.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Countdown title card">
    > 6-second 1920x1080 video. Numbers 3, 2, 1 each fill the frame for one second — each number wipes in with a diagonal mask and its background alternates black/white with inverted text. At 3s the frame slams to "LAUNCH DAY" in condensed caps with a screen-shake, holds with a subtle grain flicker. No audio. **Spectacle beat:** The frame snap at 3s is the moment — a hard white flash frame and a 1.5° rotation kick settling in 0.25s.

    <DocsVideo title="HyperFrames video: Example Countdown" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-countdown.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Bar chart race">
    > 10-second 1920x1080 video, dark slate background. Title "Top languages 2026" top-left. Five horizontal bars (Python, TypeScript, Rust, Go, Java) grow from zero with staggered starts, overtaking each other twice mid-animation; each bar has a right-edge value label counting up to its final %. End state holds 2s with the leader pulsing once. Hand-draw everything — no chart library. No audio. **Spectacle beat:** The leader's single end pulse is the moment — a +16px overshoot and a bright cap flare, returning to rest exactly on the last frame.

    <DocsVideo title="HyperFrames video: Example Bar Race" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-bar-race.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Before / after split">
    > 8-second 1920x1080 video. Vertical split: left half labeled "BEFORE" shows a cluttered mock UI (grey, 12 overlapping windows drawn in CSS), right half "AFTER" shows one clean card. Both halves settle within the first second. A vertical divider line sweeps left to right at 4s, wiping the clutter into the clean state across the full frame. End on "One tool." centered. No audio. **Spectacle beat:** The divider's wipe is the moment — a bright scan-line travels the split with a bloom as it crosses, and the AFTER half resolves behind it.

    <DocsVideo title="HyperFrames video: Example Before After" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-before-after.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Loader → reveal">
    > 7-second 1920x1080 video, black background. A thin white progress ring draws from 0° to 360° over 4s while a percentage counter (0→100) ticks in the center in mono type, matching the arc exactly. Ring and counter fade out fully by 4.2s; at 4.2s the ring bursts outward into short radial dashes and "READY." stamps into the center, then holds with a subtle ambient idle (slow breathing scale). No audio. **Spectacle beat:** The ring's completion at 100% detonates — it flashes white, expands past frame, and the reveal rides that expansion out.

    <DocsVideo title="HyperFrames video: Example Loader Ready" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-loader-ready.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="3D cards (Three.js)">
    > 9-second 1920x1080 video, light warm cream background. Build the scene in Three.js via the adapter: three rounded card meshes labeled "Design", "Build", "Ship" lie flat on the ground plane, camera at a fixed 3/4 isometric angle, soft directional light + ambient so the cards cast soft shadows. One at a time each card lifts and straightens upright to face the viewer center-frame while the other two slide apart and dim; then it returns. Finish with all three standing upright in a row by 8.5s, hold with a subtle ambient idle. All easing power3.inOut. No audio. **Spectacle beat:** As the cards rise into their stack, a single specular sweep rakes across all three faces in sequence, catching each edge.

    <DocsVideo title="HyperFrames video: Example 3d Cards" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-3d-cards.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="SVG line-draw logo reveal">
    > 6-second 1920x1080 video, deep green background. A minimal mountain-range logo draws on as an SVG stroke over 2.5s, then the stroke fills with cream, the wordmark "NORTHTRAIL" letterspaces in beneath it, and a thin rule expands from center. Hold the last 1.5s with a subtle ambient idle. No audio. **Spectacle beat:** The stroke's completion is the moment — the drawn path flares once along its whole length, then the fill floods from that flare.

    <DocsVideo title="HyperFrames video: Example Svg Logo" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-svg-logo.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Word-swap headline">
    > 8-second 1920x1080 video, white background. Static sentence "Make it \_\_\_." in huge black type stays centered while the blank cycles through "faster", "simpler", "yours" — each swap flips vertically like a split-flap board, 1.5s apart, with a slight blur on motion. Final word "yours." lands in orange and the period pops. No audio. **Spectacle beat:** The last swap lands hardest — that word arrives 1.3× behind a motion-blur streak that resolves as it settles.

    <DocsVideo title="HyperFrames video: Example Word Swap" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-word-swap.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Stat tile dashboard">
    > 10-second 1920x1080 video, near-black background. Four stat tiles slide up in a 2x2 grid, staggered: "99.99% uptime", "42ms p50", "18M req/day", "0 incidents". Each tile's number counts or decrements to its value with its own easing; sparklines draw underneath in teal. At 8s the grid scales back and "Built to hold." fades in above. No audio. **Spectacle beat:** When the fourth tile lands, all four numerals flare in unison for three frames — one synchronized accent, then back to restrained idles.

    <DocsVideo title="HyperFrames video: Example Data Ticker" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-data-ticker.mp4#t=0.1" loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>

  <Accordion title="Vertical social hook">
    > 9-second 1080x1920 vertical video, charcoal background. Social-style hook: "nobody talks about this" types on center in bold white, then each following phrase replaces it on a hard cut every 1.5s — "it's not your code", "it's your prompts", "here's the fix" — with yellow highlight bars behind key words, alternating tilt. Last phrase holds with an arrow-down bounce. No audio. **Spectacle beat:** The final phrase is the payoff — it slams in at 1.35× with a three-frame shake and a chromatic split that resolves fast.

    <DocsVideo title="HyperFrames video: Example Vertical Hook" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-vertical-hook.mp4#t=0.1" portrait loop />

    *Rendered from the prompt above, unedited.*
  </Accordion>
</AccordionGroup>

*Next: [Motion that reads premium](/prompting/motion) — Level 3: the grammar rules behind why these moves read as professional instead of generic.*


## Related topics

- [High-fidelity looks](/prompting/visual-specs.md)
- [Overlays and lower thirds](/prompting/overlays-and-lower-thirds.md)
- [Caption styles](/prompting/captions-catalog.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.