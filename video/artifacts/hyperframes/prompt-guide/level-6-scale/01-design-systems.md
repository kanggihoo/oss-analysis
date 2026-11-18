> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Design systems and brand

> Point the agent at a source of brand truth — a design spec, a site, or a Figma file — instead of asking for 'on-brand', and let it compose the frame.

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

Everything so far was one scene at a time. This level is about videos as systems. Design that persists across scenes. Edits that don't regress. Output that ships. It starts with the most systemic thing a video has: its brand.

"Make it on-brand" is the vaguest thing you can ask. The agent has no way to know what your brand *is*, so it invents one.

The fix never changes. Give the agent a **source of brand truth**, and name it in the prompt. That source is a design spec, a live site, or a Figma file. Every section below is one way to do it.

## Point at a spec, don't describe a vibe

A HyperFrames project can carry a design spec: `frame.md`. Its frontmatter holds the machine-readable brand — exact hex values, font families, weight relationships. The prose below the frontmatter carries intent and the brand's Do's and Don'ts.

When a spec exists, name it:

> Use the palette and type from `frame.md`. Build a 15-second feature announcement.

* ❌ `make it feel on-brand and premium`
* ✅ `pull colors and fonts from frame.md; premium means generous spacing and one restrained accent`

Why this works: `on-brand` is a mood the agent has to guess at. A spec's frontmatter is normative. The agent quotes your hex and font family verbatim instead of approximating, then reads the prose for intent.

If your brand lives somewhere else, attach it. A PDF brand guide, a screenshot, or pasted hex codes all read more reliably than a described impression.

## Brand is truth for color and type — not for layout

A design spec says what the brand *looks like*. It does **not** say how to compose a video frame. Name what's sacred and let the agent stage the rest:

> Colors and fonts are locked to the brand — keep the exact hexes and the display/body pairing. Layout, spacing, and motion are yours to compose for video.

Why this works: web-scale brand values don't survive video. A `1px` border with a `0.06`-opacity shadow is invisible after H.264 compression. A web body size vanishes on a 1080p frame.

So treat the spec in two halves:

* **Strict** — brand colors, fonts, weight relationships, and the background choice. If the brand is a light canvas, keep it light.
* **Scaled up for the medium** — type sizes, decorative opacity, border weight.

Over-specifying layout from a web design system fights this. Pin the palette and typography. Delegate the frame.

## Use the site's own palette and fonts

When there's no spec but the brand is out there, point at it and let the agent extract:

> Match this site's look — pull its palette and fonts — and make a 20-second launch clip: `https://…`

For a well-known brand, naming it is often enough. The agent researches the palette and typography itself.

One caveat is worth stating. A single-page-app homepage often returns a near-empty shell. If the palette comes back thin, point the agent at a blog, press, or docs page instead.

This is the same brand-truth move. The *site* is the source instead of a file.

## Bringing in a Figma frame, brand, or logo

If the brand lives in Figma, ask for it directly. The agent imports it rather than eyeballing a screenshot:

> Bring in the brand tokens from this Figma file, then build the intro: `https://figma.com/…`

> Import this Figma frame as the opening scene and this logo as an SVG: `<links>`

[Figma import](/guides/figma) freezes each import as a local file with recorded provenance. Renders never call Figma, so they stay deterministic. Brand variables come in as composition brand tokens.

Two things are worth knowing when you phrase the ask:

* **Import tokens before components.** Say "brand tokens first, then the components." That's what lets imported component colors link to your brand variables instead of baking in duplicate hexes.
* **Storyboard frames are states, not slides.** If you point at a strip of scene frames, ask the agent to *reconstruct the motion between them*. A frame showing an element at four positions is one element animating, not four stills to flip through.

## Keeping a multi-video series consistent

A series is a launch set, a weekly clip, or a per-region cut. Consistency comes from a **shared source of truth**, not from re-describing the brand each time:

> All four videos share `frame.md` for palette and type. Only the headline and the stat change per video.

The constant parts come from that one authoring spec, or from one set of imported Figma tokens. The parts that vary become [variables](/prompting/variables-and-templating).

When `frame.md` changes, rerun the workflow steps that generate or assemble the affected compositions. That's how the authored HTML picks up the new brand value.

Some compositions already exist and have to re-skin at render time. Declare the shared brand tokens as composition variables instead. Every scalar variable is applied as a `--{id}` CSS custom property on the composition root, so `var(--id)` in your CSS follows the override.

This is where design systems and templating meet. The brand is shared. The content is parameterized.

## Supplying brand assets by path

Logos, fonts, textures, and product shots are inputs. Hand the agent the path — don't ask it to draw them:

> Logo at `assets/logo.svg`, brand font files in `assets/fonts/`, product shot at `assets/hero.png`. Use them; don't invent placeholders.

Prefer an SVG logo over a raster one. It scales and it animates.

State the paths explicitly. That way the agent wires up the real assets instead of generating stand-ins. It also keeps the render deterministic, because every asset is present locally before the render starts.

## Supply inputs a workflow accepts — don't fight its preset

Each creation workflow comes with a designed look — `/product-launch-video`, `/faceless-explainer`, and the rest. Feed that look your brand inputs. Don't override its composition after the fact.

* ❌ `run /product-launch-video, then restyle every scene to my colors afterward`
* ✅ `run /product-launch-video with my palette, fonts, and logo as inputs up front`

Why this works: a workflow's preset is a coherent, tested system. Its colors, spacing, motion, and component treatments hang together. Supply your brand inputs at the start and it applies your palette and type *within* that system.

Restyling scene by scene afterward pulls threads out of a design that was balanced as a whole. You spend more effort fighting the preset than handing it a spec would have cost.

## Related

<CardGroup cols={2}>
  <Card title="Figma Import" icon="figma" href="/guides/figma">
    Import brand tokens, assets, components, and motion from a Figma file.
  </Card>

  <Card title="Variables and templating" icon="sliders" href="/prompting/variables-and-templating">
    Turn brand tokens into variables that re-skin a whole series from one value.
  </Card>

  <Card title="The specification dial" icon="gauge" href="/prompting/specification-dial">
    How pinning exact hexes and type direction removes drift.
  </Card>

  <Card title="Claude Design" icon="message" href="/guides/design-tools">
    Attach a brand guide or screenshot to seed a first draft from your look.
  </Card>
</CardGroup>

<Note>
  **Capstone thread** — the entire [Level 7 film](/prompting/capstone) obeys a supplied `frame.md`: the real HyperFrames brand. The closing lockup is where the system shows most. ABC Solar Display carries the display type, and the mint→cyan CTA gradient makes its single sanctioned appearance (cut from the film, below).
</Note>

This is the clause in the [full capstone prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece. It's prompt language you can lift for your own video:

> **Design system: the provided `frame.md` is the single source of brand truth — read it first and obey it exactly.** It is the real HyperFrames brand (by HeyGen), dark-first: flat near-black ground \[…] **mint `#3CE6AC` used sparingly as the single accent — mint means go / primary / active**. The mint→cyan gradient (`#3CE6AC → #00E3FF`) appears in exactly one place in the whole film: the final CTA lockup.

<DocsVideo title="HyperFrames video: Capstone Region Render" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-render.mp4#t=0.1" loop />

*That clause paying off, rendered. The closing lockup is where the brand file's display face and its one sanctioned gradient finally appear together.*

*Next: [Variables and templating](/prompting/variables-and-templating) — turn the brand tokens that repeat across a series into named slots you fill per render.*


## Related topics

- [Capstone — every technique, one journey](/prompting/capstone.md)
- [Audio effects and mixing](/prompting/audio-effects.md)
- [Variables and templating](/prompting/variables-and-templating.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.