> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Runtimes and 3D

> GSAP is the default and you rarely name it. Real 3D, existing animation files, and scene transitions each have a runtime worth pinning in the prompt.

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

Level 2's copy-paste examples include an isometric-cards prompt that asks to
"Build the scene in Three.js via the adapter." This chapter is why that line is
there. It's also the rest of the runtime map, for the cases where GSAP isn't the
right tool.

HyperFrames animates through the
[frame-adapter](/concepts/frame-adapters) pattern. Any runtime that can answer
"what should the screen look like at frame N?" plugs in and renders
deterministically. [GSAP](/guides/gsap-animation) is the default adapter and
covers most motion, so you rarely need to name it. The cases below are the ones
where the default can go wrong. There, the prompt should pick the runtime.

## Real 3D → Three.js via the adapter

This is the one pin to state every time. Ask for Three.js explicitly for
anything with genuine **depth, lighting, or a camera** — a rotating product, a
scene you move through, surfaces that catch light:

> Build the scene in **Three.js via the adapter**: a product model on a turntable, one key light and a soft fill, slow rotation.

* ❌ `isometric cards floating in CSS 3D with perspective`
* ✅ `build the isometric scene in Three.js via the adapter, with real depth and lighting`

<DocsVideo title="HyperFrames video: Example 3d Cards" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-3d-cards.mp4#t=0.1" loop />

*The Three.js version of the isometric-cards prompt — real shadows and lighting, one-shot.*

The engine rationale is simple. CSS `perspective` transforms skew flat planes.
There is no light source and no camera, only projected rectangles, so they read
flat the moment lighting or parallax matters.

Three.js is a first-party seek-safe runtime. The adapter publishes HyperFrames
time as `window.__hfThreeTime` and dispatches an `hf-seek` event on each seek, so
a real 3D scene renders frame-accurately like everything else.

Treat "real 3D" as "Three.js." This is a validated default, not a preference.
The exception is when you specifically want a flat, stylized fake-3D look.

Camera moves are part of the same rule. A drone orbit, a dolly, or a push-in
only exists where there's an actual camera:

<DocsVideo title="HyperFrames video: Camera Orbit" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/camera-orbit.mp4#t=0.1" loop />

*A seek-driven Three.js drone orbit. The camera sweeps a continuous arc, which CSS transforms cannot do.*

* ❌ `a drone-orbit camera move around the logo` with no runtime named — CSS has no camera to orbit
* ✅ `orbit the camera around the logo — Three.js via the adapter`

## Existing animation files → Lottie

You may already have a designed animation: an After Effects export, a `.json` or
`.lottie` file, an icon animation from a designer. Don't ask the agent to redraw
it. Point at the file and ask for Lottie:

> Play this Lottie file (`assets/loader.lottie`) centered, then fade to the title.

The Lottie adapter seeks the existing animation frame by frame, so the
designer's work renders exactly as authored. Asking the agent to recreate it in
GSAP throws away the source and lands somewhere approximate.

Characters work the same way. A mascot that walks in, stops and points is a
Lottie file with the acting in it; the agent builds the scene around it in GSAP:

> Use this character Lottie (`assets/mascot.json`): it walks in and points right at 5.2s. Bring the title card in on the point.

A short walk cycle with `loop: true` keeps cycling for the whole scene. The
[`lottie-character-walk`](/catalog/blocks/lottie-character-walk) block is a
working starting point.

## Simple UI and text motion → the default

Fades, slides, staggers, counters, kinetic type, hover-style reveals — the
everyday motion — is what GSAP does natively. It's already the default. Don't
name a runtime here. Describe the motion instead. See [Motion that reads
premium](/prompting/motion):

> The headline slides up per word, staggered 0.1s apart, easing out as it lands.

CSS keyframes and the Web Animations API are supported adapters too. Name them
only when you're bringing existing CSS `@keyframes` or WAAPI code you want kept
as-is. For a fresh ask, let the default handle it.

An SVG "line draws itself" effect (animated `strokeDasharray` /
`strokeDashoffset`) is also GSAP-default territory. See the appendix's [SVG
draw-on rows](/prompting/rules-and-anti-patterns#svg-draw-on) for two lint
gotchas worth knowing before you ask for one.

## Scene-to-scene → shader transitions

Motion *within* a scene is one thing. The handoff *between* scenes is another.
For a designed transition — a wipe, a glitch, a liquid dissolve — ask for a
shader transition at that specific moment:

> Hard-cut between the first three scenes; use a **shader transition** (glitch) into the final logo scene.

Name the moments. Shader transitions are for the two or three beats that deserve
them, not every cut. See [Transitions](/prompting/transitions) for the
vocabulary.

## Determinism surfaces in the prompt

Every runtime renders under the same [determinism](/concepts/determinism)
contract. The frame clock is `t = frame / fps`. There is **no wall clock, no live
network at render time, and no unseeded randomness**.

Two asks bump into this, so phrase them accordingly.

Live data can't be fetched at render time, because the render must be
reproducible:

* ❌ `fetch the current BTC price and count up to it`
* ✅ `count up to $67,400` with a fixed value baked in, or `read the target from a variable I pass at render time`

Unseeded randomness renders differently each frame and breaks reproducibility:

* ❌ `scatter 200 particles randomly`
* ✅ `scatter 200 particles from a seeded random layout` — say **seeded** and the positions stay stable across frames and re-renders

The rule of thumb: anything the video needs to *know* must be present before
rendering starts, baked in or passed as a
[variable](/prompting/variables-and-templating). Anything random must be seeded.

## The capstone thread

<Note>
  **Capstone thread** — the [Level 7 film](/prompting/capstone)'s Depth region is
  real Three.js through the frame adapter. The timeline wire coils around a rim-lit
  faceted form, and the protagonist chip threads the coil's loops and passes behind
  the form with true depth occlusion (cut from the film, below).
</Note>

This is the clause in the [full capstone
prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece. It's
prompt language you can lift for your own video:

> **Depth (52–56s).** The wire spirals off the flat plane into real 3D — a **Three.js scene via the frame adapter** (never CSS fake-3D): the camera descends following the wire as it coils around a rim-lit faceted form (ink material on charcoal), mono axis readouts landing on cue, then rises back to the plane with the wire leading the way out. The coil winds up out of the wire and collapses back onto it — its ends never float cut off in mid-air — and the protagonist chip joins the 3D scene for the crossing: it rides the wire straight through the coil's loops and passes behind the form with true depth occlusion, never floating over the geometry as a flat overlay.

<DocsVideo title="HyperFrames video: Capstone Region Depth" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-depth.mp4#t=0.1" loop />

*That clause, rendered — the region cut from the finished film.*

*Next: [Media and audio](/prompting/media-and-audio) — precise phrasing for
voiceover, music, sound, and assets, instead of motion and rendering.*

## Related topics

* [Frame adapters](/concepts/frame-adapters) — the seek-by-frame contract and the full list of supported runtimes
* [Deterministic Rendering](/concepts/determinism) — why no live data and no unseeded randomness
* [Motion that reads premium](/prompting/motion) — describing everyday GSAP motion so it doesn't read as cheap
* [Transitions](/prompting/transitions) — naming the scene-to-scene handoffs worth a shader transition
* [Animate with GSAP](/guides/gsap-animation) — the default adapter in detail


## Related topics

- [Capstone — every technique, one journey](/prompting/capstone.md)
- [VFX and liquid glass](/prompting/vfx-and-liquid-glass.md)
- [3D Transitions](/catalog/blocks/transitions-3d.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.