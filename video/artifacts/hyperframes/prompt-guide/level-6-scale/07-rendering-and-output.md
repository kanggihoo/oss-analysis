> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Rendering and output

> What to say to get the right file out — quality tier, format, resolution, framerate, and cloud rendering — without over-speccing a render that slows to no benefit.

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

Everything before this point — including the frame-by-frame matching in [Recreating something you saw](/prompting/recreating-references) — shapes the composition. This page is about the *export*: the words that pick a quality tier, a container format, a resolution, and where the render runs. The defaults — MP4, 1920×1080, 30fps, `standard` quality — are deliberately good, so most of the skill here is knowing when *not* to ask for more. The mechanics live in the [Rendering guide](/guides/rendering); this page owns what to say.

## Quality tier

Say the tier by name and the agent selects the matching encode preset — you don't specify CRF or encoder speed:

| Say this | Tier | Best for |
| - | - | - |
| "draft" / "quick render" | `draft` | Fast iteration while you're still judging the cut |
| nothing, or "review render" | `standard` (default) | General use — visually lossless at 1080p |
| "final" / "high quality" | `high` | Delivery masters |

The tiers trade encode time for fidelity. `standard` (the default) is already visually lossless at 1080p — most people can't tell it from source — so reserve `high` for the master you'll actually hand off, and use `draft` freely while iterating.

* ❌ `render everything at high quality`
* ✅ `draft renders while we iterate, then one high-quality final` — you spend the slow encode once, on the cut you've already approved

## Format

MP4 is the default and the right answer for almost everything — it plays everywhere. Ask for a different container only when the delivery target needs one:

> Render this as a transparent WebM overlay.

> Export a MOV I can drop into Premiere with the background knocked out.

Transparency has a container hierarchy, and the tradeoffs are real:

| Ask for | You get | Watch out for |
| - | - | - |
| "transparent MOV" | ProRes 4444 with alpha | The editor-grade choice (Premiere, Final Cut, Resolve, After Effects). Files are large — expected for an editing intermediate. |
| "transparent WebM" | VP9 with alpha | Small, but **only browsers decode the alpha** — every video editor renders the transparent areas black. Browser playback only. |
| "PNG sequence" | Lossless RGBA frames | For compositing in After Effects / Nuke / Fusion. Largest of all. |

Transparency also only *means something* on a design that has empty space to see through. A lower third, a subscribe card, or a logo sting is mostly empty canvas — transparency lets it composite over other footage. A full-frame scene (edge-to-edge background, full-bleed video, a title card with its own backdrop) has nothing to be transparent; the request produces a file that looks identical to the opaque one but is larger and plays in fewer places.

* ❌ `render my full-screen product promo as a transparent WebM`
* ✅ `render the promo as MP4; export just the lower-third overlay as transparent WebM` — transparency belongs to the layer meant to sit *over* other footage, not the finished full-frame film

<DocsVideo title="HyperFrames video: Overlay Spotify Preview" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/overlay-spotify-preview.mp4#t=0.1" portrait loop />

*A transparent VP9 WebM overlay previewed over a checkerboard. To verify alpha from the CLI: VP9 stores it out-of-band, so look for ALPHA\_MODE=1 in ffprobe (a pix\_fmt-only check false-negatives) or extract it with ffmpeg alphaextract.*

<Note>
  A transparent render also depends on the composition leaving `html` / `body` backgrounds unset — the transparency comes through only where nothing is painted. The workflow skills handle this; see the [Rendering guide](/guides/rendering#transparent-video) if you're hand-authoring an overlay.
</Note>

## Resolution and framerate

1920×1080 at 30fps is the default. Both cost real time when you raise them, and both are frequently asked for out of habit rather than need.

**4K** is a render-time flag — the composition stays at its authored size and Chrome supersamples it to 3840×2160. That buys crisp text, SVG, and CSS at any scale, but it does *nothing* for content already locked to a pixel grid: a 1080p `<video>`, a fixed-size `<canvas>`, or a sub-4K image gain no detail from it. And it isn't free — a 4K render is roughly **4× slower per frame** and produces a **3–5× larger file**. Ask for it when the delivery surface genuinely needs it (a 4K display, a client spec), not reflexively.

> Render this at 4K for the trade-show display.

**Framerate** follows the same logic: 60fps doubles the frames the engine captures and encodes. It's worth it for fast motion graphics destined for a high-refresh screen; it's wasted on a talking-head clip or a slow title sequence.

* ❌ `render in 4K 60fps` for a clip headed to Instagram — the platform will transcode it down anyway, and you paid the slow render for nothing
* ✅ say nothing for social; name `4K` (or `60fps`) only when the target actually resolves it

<Warning>
  A few 4K constraints will stop a render before it starts (all grounded in the [4K guide](/guides/4k-rendering#constraints)): the target orientation must match the composition's aspect ratio, the scale must be a whole number (1080p → 4K is exactly 2×), and **4K cannot be combined with HDR** in one pass. If you need both, render HDR at composition resolution and upscale separately.
</Warning>

## HDR

HDR output is **HDR10 MP4** (H.265 10-bit, BT.2020) and it is *source-driven* — the render only goes HDR when your composition actually references HDR media (video tagged BT.2020 with PQ or HLG transfer, or a 16-bit PNG). Text, gradients, and GSAP animation are not HDR sources; a composition made entirely of them has nothing to render in HDR.

> This composition has an HDR drone clip — render it as HDR10.

By default HDR is auto-detected, so with a real HDR source in the project you often need to say nothing. Force it explicitly only to override the probe:

* "force HDR" → forces the HDR path even without a detected HDR source
* "force SDR" → forces standard range even when HDR sources are present

HDR is **MP4 only** (a transparent MOV/WebM request falls back to SDR) and it is **not available on Lambda** (distributed rendering is SDR-only). See the [HDR guide](/guides/hdr) for source requirements and verification.

## Where the render runs

Local rendering is the default and the right choice for the whole iteration loop. Reach for cloud rendering only when a single machine is the bottleneck:

> Render this on Lambda.

That routes to HyperFrames' AWS Lambda path, which fans the render across many parallel workers. It's the right call for renders that are **too long or too large for one host** — multi-minute videos, 4K masters, or large parallel batches — and it needs AWS credentials configured first. For dev-loop iteration, stay on local `render`; the round-trip is faster than any cloud dispatch. Lambda is SDR-only (no HDR) and bills by compute time; the [AWS Lambda guide](/deploy/aws-lambda) covers setup, cost shape, and the conservative concurrency default.

* ❌ `set up Lambda so I can preview edits faster` — cloud dispatch adds latency to a fast local loop
* ✅ `render the final 3-minute 4K cut on Lambda` — the workload that actually justifies fanning out

Lambda is not the only remote target. **HeyGen-hosted cloud rendering** ([guide](/deploy/cloud)) takes the infrastructure off your hands entirely — no AWS account to configure — and **Google Cloud Run** ([guide](/deploy/gcp-cloud-run)) is the option when your stack already lives on GCP. Name the one you want ("render this on Cloud Run"); the routing is explicit, never inferred.

## Preview before you commit the slow render

The cheapest way to avoid a wasted `high`/4K/HDR render is to judge the frame first. The habit the workflow skills follow:

1. Keep `preview` running and scrub the timeline — same runtime as the render, so what you see is what you get.
2. Iterate with `draft` renders when you need a real file to check.
3. Only when the cut is locked, ask for the final tier / resolution / format.

* ❌ `render the final 4K HDR master` on a cut you haven't watched end to end
* ✅ `draft render so I can check timing` → approve → `now the 4K final`

<Tip>
  Rendering is user-gated by design — the agent pauses at preview and renders only when you approve. Use that pause to lock the cut before you pay for the expensive export.
</Tip>

## Related

<CardGroup cols={2}>
  <Card title="Iterating" href="/prompting/iterating">Small targeted edits between renders, not re-specification</Card>
  <Card title="Rules and anti-patterns" href="/prompting/rules-and-anti-patterns">Why over-speccing resolution and framerate backfires</Card>
  <Card title="Rendering guide" href="/guides/rendering">Formats, quality presets, workers — the mechanics</Card>
  <Card title="AWS Lambda" href="/deploy/aws-lambda">Cloud rendering setup and cost</Card>
</CardGroup>

<Note>
  **Capstone thread** — the [Level 7 film](/prompting/capstone) ends on this chapter's core promise: the protagonist chip snaps into a render slot and seeded confetti holds every piece for exactly two frames — deterministic, identical on every render (cut from the film, below). Its Everywhere region names the real cloud render targets: Lambda and Cloud Run.
</Note>

This is the clause in the [full capstone prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece — prompt language you can lift for your own video:

> A **seeded confetti burst** fires — mulberry32, **seed 42, each piece holding position for exactly two frames before stepping** (stop-motion feel) — and the VO lands the honest punchline: identical on every render, because determinism is the whole point.

<DocsVideo title="HyperFrames video: Capstone Region Render" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-render.mp4#t=0.1" loop />

*That clause, rendered — the seeded confetti, identical on every render of this composition.*

*Next: [Porting from Remotion](/prompting/remotion-migration) — bringing an existing Remotion project into everything you now know.*


## Related topics

- [Vocabulary that changes output](/prompting/vocabulary.md)
- [Recreating something you saw](/prompting/recreating-references.md)
- [Overlays and lower thirds](/prompting/overlays-and-lower-thirds.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.