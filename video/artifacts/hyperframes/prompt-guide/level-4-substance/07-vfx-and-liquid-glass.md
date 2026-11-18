> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# VFX and liquid glass

> Prompt device mockups, liquid-glass UI, shatter/portal/magnetic moments, and ambient polish — and know which effects need the canvas pipeline.

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

Your motion-graphics terminal piece from Level 1 already named one of these — `vfx-shatter`, for the beat where the terminal breaks apart. This chapter is the rest of that showy end of the catalog: 3D device mockups, frosted-glass Apple UI, and cinematic moments where HTML shatters or gets sucked through a portal. Two groups do the work — the [HTML-in-Canvas](/catalog/blocks/vfx-iphone-device) blocks (real WebGL, live HTML rendered as GPU textures) and the [Effects](/catalog/components/vignette) components (lightweight CSS polish). Knowing which is which is the difference between an effect that renders and one that surprises you. All of it slots into the [one-shot skeleton](/prompting/anatomy) at the "technique" step.

### Device mockups

To put your product UI inside a real phone or laptop, name [`vfx-iphone-device`](/catalog/blocks/vfx-iphone-device) — real GLTF iPhone 15 Pro Max and MacBook Pro models with live HTML-in-Canvas screen content, a product-review camera choreography, and a 360° turntable. For a styled iOS/macOS *environment* (home screen, desktop, dock) rather than a bare device, reach for the liquid-glass system blocks below.

> /product-launch-video 15-second 1920x1080 video. Our dashboard UI lives on the screen of a real iPhone 15 Pro Max that turntables slowly under product-review lighting, then a MacBook Pro slides in beside it showing the same UI wider. Use the `vfx-iphone-device` registry block. No narration.

<DocsVideo title="HyperFrames video: Validate Device Mockup" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-device-mockup.mp4#t=0.1" loop />

*Rendered from the prompt above (the block's demo UI on screen), unedited.*

**Ask for the device *and* what's on its screen.** The block renders live HTML into the screen but ships with its own demo UI — describing your UI (or pointing at screenshots/paths) is what makes the agent replace the block's screen content instead of shipping the demo.

* ❌ `show my app on an iPhone` (you'll get the block's built-in demo UI)
* ✅ `our dashboard UI (screenshots in assets/ui/) on the screen of the iPhone 15 Pro Max, turntabling`

### Liquid-glass UI treatments

The liquid-glass blocks are frosted-glass Apple-style UI floating over an aurora shader background. Pick by the surface you want:

| You want… | Name this block | Length |
| - | - | - |
| A full iOS 26 home screen on a 3D iPhone | [`ios26-liquid-glass`](/catalog/blocks/ios26-liquid-glass) | 15s |
| A macOS Tahoe desktop on a 3D MacBook | [`macos-tahoe-liquid-glass`](/catalog/blocks/macos-tahoe-liquid-glass) | 15s |
| Glass notification cards | [`liquid-glass-notification`](/catalog/blocks/liquid-glass-notification) | 8s |
| Glass stat cards, panels, pill chips | [`liquid-glass-widgets`](/catalog/blocks/liquid-glass-widgets) | 8s |

The four `liquid-glass-*` panel blocks share the aurora-shader stage, so they compose cleanly into one scene; `ios26-liquid-glass` and `macos-tahoe-liquid-glass` are complete device environments and generally stand alone.

> /motion-graphics 8-second 1920x1080 video. Frosted glass notification cards drift in and stack over an aurora shader background, each reading a fake alert ("Build passed", "Deploy live", "0 incidents"). Real translucency — the aurora must be visible through each card. Smoke the glass enough to keep white text above 3:1 against the brightest part of the aurora. No audio.

<DocsVideo title="HyperFrames video: Glass Notify" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/glass-notify.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited — CSS `backdrop-filter` glass over a Three.js aurora.*

<Warning>
  **The `liquid-glass-notification` block needs a GPU and fails quietly without one.** It is marked `stability: experimental` and tagged `webgpu` because its frosted surface is painted through `drawElementImage` with refraction computed by a WebGPU renderer. Validating this chapter, `navigator.gpu.requestAdapter()` returned `null` in every headless and headful Chrome tried — with `--enable-unsafe-webgpu`, `--use-angle=metal`, and hardware GPU mode — and the block's init simply bails. The failure mode is not an error: you get **no cards at all**, just the text floating on the background.

  So for a render you need to be able to reproduce, ask for the *effect* — "real translucency, the background visible through the card" — and let the agent build it with CSS `backdrop-filter`, which renders anywhere. That's what the video above is. Reach for the WebGPU block only when you have confirmed a working adapter in your render environment and you specifically want refraction, specular, and chromatic aberration, which CSS cannot do.
</Warning>

**"Liquid glass" means the block, not a filter you're describing.** These are complete WebGL stages; asking for "a glassy blur on my div" gets you a CSS `backdrop-filter`, not this look.

* ❌ `add a liquid glass effect over my text`
* ✅ `use the liquid-glass-widgets registry block for the stat cards`

### Shatter, portal, magnetic, and cursor moments

The `vfx-*` blocks are single cinematic beats — spend them on a transition or a reveal, not a whole video:

| The moment | Name this block | Length |
| - | - | - |
| HTML shatters into glass fragments | [`vfx-shatter`](/catalog/blocks/vfx-shatter) | 12s |
| A dimension breach with volumetric light | [`vfx-portal`](/catalog/blocks/vfx-portal) | 10s |
| A magnetic-field particle visualization | [`vfx-magnetic`](/catalog/blocks/vfx-magnetic) | 15s |
| HTML floating over an organic liquid surface | [`vfx-liquid-background`](/catalog/blocks/vfx-liquid-background) | 12s |
| A dramatic text reveal with chromatic shadow rays | [`vfx-text-cursor`](/catalog/blocks/vfx-text-cursor) | 8s |

> /motion-graphics 8-second 1920x1080 video. Beat 1 (0-4s): a landing-page hero holds under directional light. Beat 2 (4-6s): the whole page shatters into glass fragments that scatter. Beat 3 (6-8s): bold white text slams in on black. Use the `vfx-shatter` registry block; the final beat reads "HTML IS VIDEO". No narration, no image or media files.

<DocsVideo title="HyperFrames video: Vfx Shatter" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/vfx-shatter.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

**Name the exact effect — "explode," "break," "burst" don't map.** Each block is a specific simulation.

* ❌ `make the UI explode`
* ✅ `the page shatters into glass fragments` → `vfx-shatter`, or `gets pulled through a portal` → `vfx-portal`

### Ambient polish

The [Effects](/catalog/components/vignette) components are lightweight, pure-CSS finishing passes you layer *on top* of a finished scene — grain, vignette, a light sweep, a subtle push:

| Say this | Component |
| - | - |
| Film grain / texture | [`grain-overlay`](/catalog/components/grain-overlay) |
| Darkened cinematic edges | [`vignette`](/catalog/components/vignette) |
| A light sweep across text | [`shimmer-sweep`](/catalog/components/shimmer-sweep) |
| Slow push-in on a card | [`parallax-zoom`](/catalog/components/parallax-zoom) |
| Card pulls back to reveal siblings | [`parallax-unzoom`](/catalog/components/parallax-unzoom) |
| Screen dissolves into a grid | [`grid-pixelate-wipe`](/catalog/components/grid-pixelate-wipe) |

These are the ambient layer of the [motion grammar](/prompting/motion): grain and a slow `parallax-zoom` keep a "held" beat alive instead of freezing. Never write "holds motionless" — a still final second is the biggest cheap-motion tell; let a grain overlay and a 2% push carry the hold.

> /motion-graphics 6-second 1920x1080 video. A wordmark logo — "HYPERFRAMES" in platinum on near-black — settles center-frame, then holds — but keep it alive with a film grain overlay and a slow 3% push-in, plus one shimmer sweep across the wordmark at 4s. Use the `grain-overlay`, `parallax-zoom`, and `shimmer-sweep` registry components. No audio.

<DocsVideo title="HyperFrames video: Logo Polish" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/logo-polish-v2.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited — the "hold" stays alive on grain, a 3% push, and one shimmer pass.*

**Reach for grain over a literal freeze.** The engine holds the final state exactly as written.

* ❌ `logo appears and holds still to the end`
* ✅ `logo settles, then a grain overlay and slow push keep the hold breathing` (see [ambient idle](/prompting/motion))

### When an effect needs the canvas pipeline

The distinction that trips people up: the **HTML-in-Canvas blocks are not CSS**. The device mockups, liquid-glass stages, and `vfx-*` blocks render live DOM into WebGL textures via the experimental `drawElementImage` API — which needs a Chrome flag. The [HTML-in-Canvas guide](/guides/html-in-canvas) documents the real behavior:

* **Rendering enables CanvasDrawElement automatically** (`--enable-features=CanvasDrawElement`), including inside Docker. That is enough for CanvasDrawElement-only blocks. Liquid-glass blocks that combine it with WebGPU still need a compatible browser such as Brave or Chrome Canary configured through `PRODUCER_HEADLESS_SHELL_PATH`; the bundled headless shell cannot run that combination.
* **Live preview in the Studio needs the flag turned on manually** (`chrome://flags/#canvas-draw-element` → *Enabled* → restart). Without it, these blocks fall back rather than showing the effect in preview.
* The blocks **feature-detect and degrade gracefully**, so a browser without the flag won't crash — it just won't show the WebGL treatment.

The Effects components above have none of this — they're plain CSS and animate everywhere, preview included. So if you need something visible in Studio preview today with zero setup, prefer the CSS Effects; the HTML-in-Canvas group is where the flag caveat lives.

<Warning>
  Don't promise a stakeholder a live Studio preview of a liquid-glass or device block without confirming the Chrome flag is enabled on that machine — the rendered MP4 is unaffected, but the in-browser preview may fall back. See the [HTML-in-Canvas guide](/guides/html-in-canvas).
</Warning>

### Where to go next

* [Anatomy of a one-shot prompt](/prompting/anatomy) — the skeleton, and quoting on-screen copy.
* [Motion that reads premium](/prompting/motion) — the ambient-idle rule these polish layers serve.
* [Copy-paste examples](/prompting/examples) — a `vfx-liquid-background` social-card prompt to adapt.
* [HTML-in-Canvas guide](/guides/html-in-canvas) — how `drawElementImage` works and the flag details.

<Note>
  **Capstone thread** — the [Level 7 film](/prompting/capstone)'s Surface region floats its inspector panels on the brand's glass tokens — translucent white over real backdrop blur, the mural visibly smearing through each panel (cut from the film, below).
</Note>

This is the clause in the [full capstone prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece — prompt language you can lift for your own video:

> Inside: frosted-glass inspector panels (real translucency — blur over what's behind; the product's Studio design language) hover above the wire carrying live values (`ease: power3.out`, a color token, an fps readout) \[…] Glass surfaces use the file's `--glass-*` tokens with real backdrop blur.

<DocsVideo title="HyperFrames video: Capstone Region Surface" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-surface.mp4#t=0.1" loop />

*That clause, rendered — the region cut from the finished film.*

*Next: [Runtimes and 3D](/prompting/runtimes-and-3d) — picking GSAP, Three.js, or Lottie by what the moment actually needs, including the real depth these effects render on.*


## Related topics

- [Liquid Glass](/catalog/blocks/vfx-liquid-glass.md)
- [Color grading and film effects](/prompting/color-grading.md)
- [Capstone — every technique, one journey](/prompting/capstone.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.