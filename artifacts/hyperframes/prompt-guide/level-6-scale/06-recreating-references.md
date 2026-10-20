> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Recreating something you saw

> Transcribe motion, iterate with absolute targets, distill the constants — and know where the text-only ceiling is.

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

[Iterating](/prompting/iterating) covered the correction loop in general. This page is its hardest test: matching a specific reference you watched, rather than a look you're inventing.

From text alone, you can reach roughly 90% of a reference. That takes a specific workflow, and it takes knowing where the ceiling is. Both are below.

<Note>
  The percentages on this page are observed results from this guide's own recreation builds, judged frame against frame. Treat them as the shape of the curve, not a guarantee.
</Note>

## Transcribe motion, not just composition

Watch the reference frame by frame. Write down:

* the exact duration
* the camera's path
* what each element does, with timestamps
* how entrances overlap
* which layers are blurred
* sampled colors

A prompt built this way one-shots about 75% of the target. Structure and the motion arc land. Rendering calibration doesn't.

## Iterate with absolute targets

Compare your render against the reference frame by frame. Then correct one axis at a time, freezing everything that already matches.

State each correction as an absolute value, not a relative nudge:

* ❌ `make dots 2x finer`
* ✅ `dot radius = 25% of row spacing`

Relative corrections pendulum — too big, then too small, then too big again. Expect a handful of rounds to converge.

## Distill the converged values back into the prompt

Iteration is a search. The constants it finds are reusable.

A prompt carrying them one-shots \~80–90% of the converged quality on a fresh build. The discrete facts transfer losslessly: timings, counts, hexes, ratios, camera arcs. Continuous qualities still vary by a calibration note or two, like glow prominence or how the framing feels.

The converged composition file itself is the pixel-exact artifact. Renders are deterministic, so re-rendering that file reproduces the result.

Here is a distilled spec that one-shots a broadcast-style animated globe:

<Accordion title="Worked example: the hologram globe (full distilled spec)">
  > 1.8-second 1920x1080 video, Three.js via the adapter (seek-driven, no rAF). One continuous shot. Every element is still moving on the final frame.
  >
  > **FIELD**
  >
  > * blue-violet background, linear #2a24a8 → #12105e top-to-bottom, with a soft radial lift at center
  > * faint blurred vertical cyan light-streaks (#5ee0e8 at \~10% opacity, \~340px spacing) drifting 70px left across the piece
  > * deep corner vignette
  > * soft-light film grain at \~6% (seeded noise)
  >
  > **GLOBE**
  >
  > * royal-blue sphere (#4348f2), lit from upper-left with a 0.58 ambient floor
  > * a broad subtle satin band (#6470ff, very wide falloff, \~30% mix) sweeping the upper curve
  > * a strong cyan rim-light line (#5ee8f0) tracing only the top edge
  > * continents in TWO layers:
  >   * (a) a heavily-blurred darker-blue silhouette (#3439c2, 80% opacity) just under the surface, reading as a soft shadow shape
  >   * (b) a dot-matrix just above the surface on an equal-area grid (0.9° latitude rows, longitude step widening with latitude)
  > * dot radius = 24–28% of row spacing — clear blue gaps between dots — growing slightly toward the equator, 85% dot opacity
  > * two color populations: cyan-aqua #5ee0e8 north, spring-green #7ce97a from latitude \~32° southward, with seeded ±30% per-dot brightness variance
  > * dots dimmed to 40% in the view-space lower-right shadow zone
  > * continents read as distinct dotted landmasses covering \~30–35% of the visible hemisphere, with royal-blue ocean dominating the rest
  >
  > **CAMERA**
  >
  > * open EXTREMELY close: the sphere's curve fills the entire frame, horizon exiting the upper corners
  > * then one continuous pull-back + crane (fov 52°→40°)
  > * end with the dome filling the lower half edge-to-edge, its silhouette touching both frame edges, horizon at \~45%
  > * ease power1.inOut computed over a 2.0s window while rendering 1.8s, so the move never settles on-screen
  > * the globe rotates 28° about its vertical axis, linear, continents drifting right-to-left, never stopping
  >
  > **ORBS** — 12 across three depth planes, world-anchored on the upper hemisphere so stems stay vertical
  >
  > * popping at staggered starts 0.45s→1.15s (0.06–0.13s apart)
  > * each rising 0.44–0.56s with back.out overshoot (vary 1.7–2.6 per orb), then bobbing ±8px on phase-offset sines forever
  > * **5 midground** (\~90–110px at end framing): soft mint body #a7ecc4, a darker-green under-shade #3f9b5e at lower-left, a pale rim #d6ffe8 top-right, no white core
  >   * each wrapped in a soft additive bloom sprite \~3.5x its diameter, whose texture is HOLLOW-centered, peaking \~35% just outside the orb edge. A bright-cored additive glow over the opaque orb blows the mint to lime.
  >   * plus a thin soft halo ring \~4.2x radius at 60% opacity, always subtler than the orb itself, with a slow 5% scale pulse
  > * **4 background** — \~30px, sharp, tighter bloom
  > * **3 foreground near-lens bokeh** — \~160–190px, dense mint radial-gradient sprites riding the camera at center-left / lower-center / upper-right, \~70% opacity, drifting ±30px laterally, no stems
  > * **stems** — 2–3px additive cyan cylinders fading to transparent at the surface
  > * tag canvas-generated sprite textures sRGB, or the mints wash out pale
  >
  > **CAPTION** — "Across 82 Countries"
  >
  > * Inter 300, 34px, 0.06em tracking, white at 90%, top-center 12% from the top
  > * left-to-right per-letter fade starting t=1.0s, completing \~1.45s
  > * then a slow 6px upward drift, still easing at the final frame
  >
  > No audio.

  <DocsVideo title="HyperFrames video: Recreate Globe Oneshot" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/recreate-globe-oneshot.mp4#t=0.1" loop />

  *The one-shot render produced by this exact spec on a fresh build — no iteration.*
</Accordion>

## Know where the text-only ceiling is

Words carry discrete, countable things losslessly. They underdetermine continuous perceptual qualities: bloom falloff, material feel, optical color mixing.

That last 10% doesn't close from text. It oscillates instead. If pixel-exact matters, keep the composition file.

## Related

<CardGroup cols={2}>
  <Card title="Iterating" href="/prompting/iterating">The correction loop this page pushes to its limit</Card>
  <Card title="High-fidelity looks" href="/prompting/visual-specs">Writing the spec density a recreation needs</Card>
  <Card title="Runtimes and 3D" href="/prompting/runtimes-and-3d">The adapter the worked example uses</Card>
  <Card title="Capstone" href="/prompting/capstone">Every technique composed into one film</Card>
</CardGroup>

*Next: [Rendering and output](/prompting/rendering-and-output) — once the cut is locked, the words that pick the right export.*


## Related topics

- [Rendering and output](/prompting/rendering-and-output.md)
- [Iterating](/prompting/iterating.md)
- [Prompt Guide](/prompting/overview.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.