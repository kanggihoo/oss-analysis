> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Data and maps

> Prompt animated charts, count-up stats, and maps — highlight regions, draw flows, size bubbles — or hand-draw a chart for full control.

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

Level 3's six-scene SaaS explainer ended on a `cinematic-zoom` into a pricing reveal — a transition doing the work a real number could. This chapter is how to put an actual animated chart or count-up stat in that reveal instead of just a camera move.

Numbers and geography are the two subjects where "what data" and "how it moves" are separate decisions. The [Data](/catalog/blocks/data-chart) blocks give you a polished chart or map you feed values into; the count-up [showcase](/catalog/blocks/apple-money-count) blocks handle the odometer-and-flourish moment. Everything here plugs into the [one-shot skeleton](/prompting/anatomy) — the data goes in the "copy" slot, the block name in "technique."

### Charts: name the block, or hand-draw

There are two ways to get a chart, and the choice is about control:

* **Name [`data-chart`](/catalog/blocks/data-chart)** to get the built animated bar + line chart — staggered reveal, value labels, NYT-style typography — and feed it your numbers. Fast, consistent, no design decisions.
* **Say "hand-draw everything — no chart library"** to make the agent build the chart from inline SVG and GSAP instead. You give up the polish of the block for total control over shape, motion, and layout — a bar race that overtakes mid-animation, an arc that draws to match a counter, a layout no library ships.

Feed data inline or as a file. Small series go straight in the prompt; a CSV gets referenced and parsed at build time (keep it deterministic — no [render-time fetches](/concepts/determinism)).

> /motion-graphics 12-second 1920x1080 video. Title "Most-used languages" with the subtitle "share of respondents, 2026 survey". Turn this into an animated bar chart with a staggered reveal and value labels counting up on each bar, each label suffixed `%`:
>
> ```
> Python 41, TypeScript 33, Rust 19, Go 14, Java 9
> ```
>
> Use the `data-chart` registry block. No audio.

<DocsVideo title="HyperFrames video: Chart Languages" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/chart-languages.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited — labels count up while the next bar is already growing.*

> /motion-graphics 10-second 1920x1080 video, dark slate background. Title "Top languages 2026" top-left. Five horizontal bars (Python, TypeScript, Rust, Go, Java) grow from zero with staggered starts, overtaking each other twice mid-animation; each bar has a right-edge value label counting up to its final %. End state holds 2s, alive — the leader pulses once, timed to finish exactly on the last frame, never a frozen tail. Hand-author the marks (no chart library) and make them *look* hand-drawn: wobbly ink strokes, not clean rectangles. Say which two pairs overtake and when, or the reveal will land on a different number of crossings each run. No audio.

<DocsVideo title="HyperFrames video: Barrace Handdrawn" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/barrace-handdrawn.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited — hand-authored ink strokes, no chart library; ranks swap twice.*

**State the block *or* opt out of it — don't leave it implicit.** "Animate this data" without a decision drifts between a generic block and an improvised layout.

* ❌ `animate this CSV as a chart`
* ✅ `turn this CSV into an animated bar chart — use the data-chart registry block` **or** `…hand-draw everything, no chart library`

**Format numbers for the animation you asked for.** An odometer count-up needs fixed digit columns; a `$0 → $4.2M` range forces an awkward `$0.0M` start.

* ❌ `counts from $0 to $4.2M`
* ✅ `counts up to $4.2M`

### Count-up stats

For a single hero number, [`apple-money-count`](/catalog/blocks/apple-money-count) is the Apple-style finance counter — it rolls from \$0, flashes green, and bursts money icons with sound. Name it when you want that exact flourish; hand-draw when you want a bare number in your own type.

> /motion-graphics 6-second 1920x1080 video, dark navy background. Beat 1 (0-1s): label "ARR" fades up small, top-center. Beat 2 (1-4s): a giant number counts up to \$4.2M with an odometer roll, easing out as it lands. Beat 3 (4-6s): "+312% YoY" stamps in below in green, then settles into a gentle ambient idle. Use the `apple-money-count` registry block as base. No narration.

<DocsVideo title="HyperFrames video: Money Count" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/money-count.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

### Maps: match the ask to the map

Each map block answers a different geographic question. Say what the map is *for* and name the matching block:

| You want to… | Name this block | Length |
| - | - | - |
| Shade US states by a value (choropleth) | [`us-map`](/catalog/blocks/us-map) | 12s |
| Size US cities by a value (proportional bubbles) | [`us-map-bubble`](/catalog/blocks/us-map-bubble) | 12s |
| Draw connections between US cities (origin→dest) | [`us-map-flow`](/catalog/blocks/us-map-flow) | 12s |
| Show US states as an equal-weight hex grid | [`us-map-hex`](/catalog/blocks/us-map-hex) | 10s |
| Shade Spain by autonomous community | [`spain-map`](/catalog/blocks/spain-map) | 12s |
| Shade the world country by country | [`world-map`](/catalog/blocks/world-map) | 14s |

The US map encodings combine — asking to "shade states *and* draw flows between two cities" gets you one composition: the agent merges the blocks at source onto a shared projection so arcs land exactly on the choropleth's states.

> /motion-graphics 12-second 1920x1080 video. A US choropleth shades states by adoption rate with staggered reveals and a gradient legend, then connection arcs draw between San Francisco, Austin, and New York. Use the `us-map` and `us-map-flow` registry blocks. No audio.

<DocsVideo title="HyperFrames video: Validate Us Map Flows" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-us-map-flows.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

<Note>
  The map blocks fetch their geo data from a CDN at runtime, which violates the deterministic-render rules — the agent bakes the projected geometry into the composition instead. You never need to ask for this; it's part of building the map correctly.
</Note>

**Pick the encoding, don't just say "map."** Choropleth (color), bubble (size), hex (equal weight), and flow (arcs) tell different stories from the same data.

* ❌ `put California's number on a US map`
* ✅ `size each city as a proportional bubble` → `us-map-bubble`, or `shade each state by value` → `us-map`

**Name the region's block.** The choropleths are region-specific with baked-in projections (`spain-map` is D3 conic conformal, `world-map` is Natural Earth) — there's no generic "any country" map.

* ❌ `a map of Spain's regions` (leaves the projection and geography to chance)
* ✅ `use the spain-map registry block`

### Routes and flights

For a point-to-point journey — a route drawing across a map with a landing beat — [`nyc-paris-flight`](/catalog/blocks/nyc-paris-flight) is the Apple-style flight animation: a plane flies New York → Paris with a marker circle, landing pop, and sound effects. Use it as the base and re-point the endpoints in your prompt.

> /motion-graphics 6-second 1920x1080 video. A realistic map with a plane flying between two cities, a marker circle at the origin, and a landing pop at the destination. Use the `nyc-paris-flight` registry block as base — the route runs New York (JFK) → Paris (CDG), labelled at both ends. Keep the block's own title card and route ticks. End on the settled map, not on the block's white-out hand-off frame. No audio.

<DocsVideo title="HyperFrames video: Flight Route" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/flight-route.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

**A route is a flow with a vehicle, not a static arc.** If you want the drawn arc without the plane and sound, that's `us-map-flow`; if you want the journey performance, that's `nyc-paris-flight`.

* ❌ `draw a line from NYC to Paris` (ambiguous between arc-only and full flight)
* ✅ `a plane flies the route with a landing pop` → `nyc-paris-flight`

### Where to go next

* [Anatomy of a one-shot prompt](/prompting/anatomy) — the skeleton, and why odometers need fixed digit columns.
* [Copy-paste examples](/prompting/examples) — bar-chart race and stat-tile prompts to adapt.
* [Generated artwork](/prompting/generated-artwork) — where hand-drawn HTML/CSS/SVG shines, and where it doesn't.
* [The specification dial](/prompting/specification-dial) — deciding when to name a block versus hand-draw.

<Note>
  **Capstone thread** — the [Level 7 film](/prompting/capstone)'s Measure and Everywhere regions are this chapter end to end: `data-chart` bars rise from the timeline wire while the hero count lands, then the same wire becomes a great-circle arc over the `world-map` block's real cloud render regions (cut from the film, below).
</Note>

This is the clause in the [full capstone prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece — prompt language you can lift for your own video:

> **Measure (14–21s).** The wire becomes a chart baseline (same line, same thickness — no cut): adapt the **`data-chart` registry block** — six labeled bars rise from the wire itself on spoken cues while a hero numeral counts up beside them in huge tabular mono: **50+ CATALOG BLOCKS** (the real registry count) \[…]
>
> **Everywhere (21–28s).** The wire arcs and the ground falls away: adapt the **`world-map` registry block** — the dotted world map scrolls beneath while the wire becomes a great-circle route arcing across it. Real render infrastructure, truthfully labeled: pulses light up at AWS and Google Cloud regions (US-EAST-1 · EU-WEST-1 · AP-SOUTH-1) with a "CLOUD RENDER · LAMBDA + CLOUD RUN" kicker \[…]

<DocsVideo title="HyperFrames video: Capstone Region Data Map" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-data-map.mp4#t=0.1" loop />

*That clause, rendered — the region cut from the finished film.*

*Next: [Overlays and lower thirds](/prompting/overlays-and-lower-thirds) — naming timed blocks that sit above your footage or scene, instead of ones that render the scene itself.*


## Related topics

- [World Map](/catalog/blocks/world-map.md)
- [Spain Map](/catalog/blocks/spain-map.md)
- [US Map](/catalog/blocks/us-map.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.