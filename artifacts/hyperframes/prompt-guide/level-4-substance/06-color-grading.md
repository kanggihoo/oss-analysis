> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Color grading and film effects

> Grade media with a fixed-order pipeline — tonal work, hue keys, print and analogue treatments — and know why the source matters more than the payload.

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

Every chapter so far has built the image. This one changes what the image appears to have been *recorded on*. A grade is not decoration applied at the end; it is a claim about the medium — that this came off tape, or a press, or a tube, or a camera with a particular stock in it. Viewers read that claim instantly and they read it whether or not you meant it.

Grading attaches to a single `<img>` or `<video>` through a `data-color-grading` payload. It never touches your text, your cards, or your captions — only the pixels of the media element it is on. The full contract lives in the [Color Grading guide](/guides/color-grading); this chapter is about what to *ask for*, and about the three ways these prompts go wrong.

## The source has to have something to lose

This is the failure that costs the most time, and it is invisible in the prompt. Every one of these treatments works by *removing* something, so the shot must contain the thing being removed.

Three worked examples from building this page, each of which produced a demo that technically executed and visibly taught nothing:

| Treatment | Wrong source | Why it showed nothing |
| - | - | - |
| Hue key — hold one color | Talking head in a kitchen | Skin **is** the red band. Keying red kept the face; 6% of pixels moved. |
| Two-ink press | Black type on white paper | Already two-tone. Nothing to collapse. |
| Kuwahara — painterly | Soft-focus office | An edge-preserving smoother needs edges to preserve. |

Fixing all three meant changing the footage, not the payload. So specify the subject in the prompt, and specify it in terms of the property the effect consumes: *"pick a subject with dense color and dense edges"*, *"the surround has to carry color, not be neutral grey"*.

## The pipeline order is fixed

Sections apply in a set order regardless of how you write them:

```text theme={null}
adjust → wheels → curves → hueCurves → secondaries → lut → details → effects
```

This is not cosmetic. A global `saturation: -0.9` in `adjust` runs *before* `secondaries`, so a hue-keyed selection that tries to hold one color back finds it already desaturated and has nothing to restore. If you want one color to survive a drain, key it in `hueCurves` rather than draining globally and painting it back.

## Grading qualifies by value, never by position

Selections key on hue, saturation, and luma. There are no masks, shapes, or tracked regions, and the one spatially-varying control — `vignette` — is locked to the frame centre. To treat *part* of a frame you split that part into its own layer and grade the layer. That pattern, with worked markup, is in [Limiting a Grade to Part of the Frame](/reference/color-grading#limit-a-grade-to-part-of-the-frame).

***

## Separating subject from background

The most useful thing grading does is not a look. It is protecting one part of the frame while treating another — which requires a matte, and therefore two layers.

### Grade the room, protect the face

> Take the talking-head clip and separate the subject from the room. Leave the person photographic — a gentle skin-softening pass and about a third of a stop of extra exposure, nothing that reads as an effect on skin. Grade the room behind them instead: across the four seconds bring up a halftone screen so the space resolves into small colored dots, and let a restrained bloom build alongside it so the windows lift. Both start at zero so the shot opens ungraded.

<DocsVideo title="HyperFrames video: Grade Matte Separation B0ef8e73" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-matte-separation-b0ef8e73.mp4#t=0.1" loop />

*The room takes the halftone screen and the bloom; the subject takes nothing but a skin-soft pass and a third of a stop.*

Two traps here. Use the **original clip** as the background plate, not a subject-removed plate — that plate is a hole where the subject was, and a feathered cutout over it gives a dark rim. And if your cutout ships premultiplied alpha, the browser composites it as straight, multiplying edge pixels twice and producing a black outline; rebuild it with `ffmpeg alphamerge` from the original plus its matte.

### Redact only the face

> Matte the subject off the plate, then redact just their face — the rest of them and the room behind both stay completely untouched. Hold pixelation constant at about half strength for the whole shot: no ramp, no fade-up. A redaction that animates on reads as an effect; one that is simply on reads as policy. Size the redaction generously so it takes in the hairline, ears and jaw rather than sitting tight on the features.

<DocsVideo title="HyperFrames video: Grade Redaction Engaging Ec781f26" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-redaction-engaging-ec781f26.mp4#t=0.1" loop />

*Face pixelated, body and room untouched — the region is a `clip-path` on a third layer, not a payload setting.*

The region comes from a `clip-path` on a *third* layer — a second copy of the cutout carrying the grade, stacked over an ungraded copy. Because the graded layer **is** the cutout, the ellipse can overshoot the head without touching the room; there is nothing outside the silhouette to paint. Size it generously rather than tightly.

A fixed clip only holds for footage where the subject barely moves. Measure before relying on it — here the head travelled 5.5px across the whole clip. Anything with real movement needs a tracked matte produced outside HyperFrames.

***

## Destroying the picture on purpose

### Pixelate, dither, bloom

Three ways to take the image apart, each saying something different. Pixelation reads as *redaction*. Dither reads as a *display failing*. Bloom reads as *light overwhelming the sensor*.

> Degrade the picture into a screen over four seconds. Ramp dithering from clean up to 0.85 at mid pattern size, so continuous tone breaks into discrete quantised levels. It should read as a display failing, not as a filter being applied.

<DocsVideo title="HyperFrames video: Grade Signal Loss Babe88ef" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-signal-loss-babe88ef.mp4#t=0.1" loop />

*Dither ramping from clean to 0.85 — continuous tone breaking into discrete levels.*

> Blow the highlights out over four seconds. Ramp bloom from nothing all the way to 3 — well past a tasteful highlight lift — on a wide radius, so light spills out of the windows and progressively swallows the frame. I want to see the top of the range, not a subtle glow.

<DocsVideo title="HyperFrames video: Grade Bloom Out 11531968" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-bloom-out-11531968.mp4#t=0.1" loop />

*Bloom driven to 3, well past a highlight lift, until the light swallows the frame.*

<Warning>
  Bloom is the one control that will fool your instruments. Pushed hard it looks blown out while measuring as *less* clipped than the ungraded source — the haze is halation spreading light, not clipping. No clipping metric catches it. Judge bloom at 1:1, never from a thumbnail.
</Warning>

### Painterly, without mush

> Turn the shot into a painting over four seconds without turning it to mush. Ramp a Kuwahara filter from nothing to full — mid radius, fairly high sharpness so edges stay crisp, and pull the saturation back a little so it reads as brushwork rather than as a filter. Boundaries stay defined while flat areas smooth into strokes. Pick a subject with dense color and dense edges; the effect has nothing to preserve on flat skin or a soft-focus background.

<DocsVideo title="HyperFrames video: Grade Painterly Ffd5c0f9" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-painterly-ffd5c0f9-v2.mp4#t=0.1" loop />

*Kuwahara at full strength, on a subject with enough edges to be worth preserving.*

***

## Print and color

### Two inks

> Take the poster and print it in two inks only: a near-black navy and a warm cream, at mid dot size, like a two-color press run. Everything collapses to those two colors. Bring it up across the four seconds from the untouched poster rather than cutting straight to it. Give it the exact hex values rather than a named palette.

<DocsVideo title="HyperFrames video: Grade Two Ink Press 3c5662f1" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-two-ink-press-3c5662f1-v2.mp4#t=0.1" loop />

*Ten hue families collapsing to three. Dense type is the harshest test of a two-ink reduction.*

Type is the harshest test of a two-ink reduction — dense small copy either survives the dot screen or turns to mud, and you can see which at a glance. Note the payload takes an explicit hex array; a named palette id is rejected.

### Hold one color, drain the rest

> A single red apple on a teal backdrop. Hold the apple's color and drain everything else — key off hue and collapse saturation everywhere outside the reds, so the backdrop goes fully neutral grey while the apple stays exactly as saturated as it was. Use a hue-vs-saturation curve rather than a global desaturation with the apple keyed back in: global saturation runs first in the pipeline and would kill the apple before the key ever sees it. Keep a generous skirt on the band so the apple's shadowed side doesn't clip grey.

<DocsVideo title="HyperFrames video: Grade Brand Spotlight 5ebe45bf" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-brand-spotlight-5ebe45bf.mp4#t=0.1" loop />

*The backdrop drains to neutral grey; the apple holds its saturation exactly.*

Three things have to be true of the subject, and each one killed an earlier attempt at this shot. It must be **inanimate** — the grade desaturates everything outside the band, and on a person that means a grey, corpse-like face. It must be a **single** subject — a still life of mixed produce is full of color, but half the items fall outside the band and grey out, so it reads as a filter misfiring rather than one color deliberately held. And the surround must **carry** color: against a neutral grey backdrop the grade would desaturate grey to grey and do nothing at all.

***

## Analogue: three different failures

"Make it look old" is three separate treatments, and mixing them muddles the period.

| Treatment | What is failing | Signature |
| - | - | - |
| **Tape** | The transport | Rolling horizontal wave, tracking error, dropout |
| **Tube** | The display glass | Barrel curvature, scanlines, phosphor bleed, convergence error |
| **Camera** | The capture | Grain, crushed contrast, RGB split, vignette |

The rolling wave is `tapeTracking` and `tapeDamage`. Static interlacing is `scanlines` — a different thing, and it belongs on a camera or a tube without dragging the wave along with it.

### Tape

> Make it look like a worn VHS tape. Not one artefact — layer them: strong tape damage with tracking error, a little noise, mid tape speed, scanlines, and noticeable chroma bleed. Any one of these alone reads as a filter; together they read as a failing signal.

<DocsVideo title="HyperFrames video: Grade Tape Degradation 6050228f" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-tape-degradation-6050228f.mp4#t=0.1" loop />

*Six tape artefacts at once — any one of them alone reads as a filter.*

### Tube

> Make this look like it is being displayed on an old CRT television, not like it came off a worn tape. Bow the geometry with barrel curvature so the straight lines curve and the corners pull inward, lay scanlines across it at a fairly fine pitch, add phosphor bleed and enough chromatic aberration to give visible RGB fringing at the edges. Bleed and scanlines want to sit near the top of their range — bleed is subtle even at 0.9. Curvature and chromatic aberration are the exceptions: both read strongly, so hold curvature around half and keep the aberration modest, or the tube turns into a fisheye novelty. Grade the tone as well as the geometry: crush the shadows and blacks, lift the highlights and whites, nudge saturation up, and add a restrained bloom — a CRT has no true black and lets its top end halate. Add grain and a vignette. Use a test card or something with dead-straight lines: curvature is invisible on organic subject matter.

<DocsVideo title="HyperFrames video: Grade Crt Broadcast B64dc1a8" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-crt-broadcast-b64dc1a8.mp4#t=0.1" loop />

*Geometry bowed, scanlines laid over it, tone crushed — a tube rather than a filter on a clean image.*

The tonal work is doing as much as the geometry. Without crushed shadows and a halating top end, curvature and scanlines read as a filter laid over a clean digital image.

If you composite a subject into the shot, do it **before** grading. A CRT warps the whole displayed picture; grading two layers separately bows the background while the subject stays rectilinear and spills past the tube's curved edge. One layer, one warp — the opposite of the matte-separation rule above, and for the opposite reason.

### Camera

> Take the clip and give it a camcorder grade: crush the shadows and blacks, lift the highlights and whites, pull the saturation back slightly, and add a restrained bloom, film grain for noise, a vignette, interlacing lines, and a little RGB splitting at the edges. Crushed contrast with muted color is what consumer tape actually looked like — crushed and punchy reads as a modern filter. For the split use chromatic aberration, which offsets the channels; chroma bleed is a different thing, a smear rather than a fringe. Keep the interlacing static — no tape tracking and no tape damage, because those produce a rolling horizontal wave that reads as a broken deck rather than as a camera.

<DocsVideo title="HyperFrames video: Grade Camcorder Overlay 18e80485" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-camcorder-overlay-18e80485.mp4#t=0.1" loop />

*The footage degrades; the HUD does not. It is an overlay, composed above the media canvas.*

The HUD in that shot is not part of the grade. It is a [`camcorder-hud`](/catalog) registry block — real HTML, CSS, and a paused GSAP timeline composed *above* the media canvas. Grading never touches it, which is exactly what you want: burn a timestamp into the source pixels and it degrades with them; put it in an overlay and it stays crisp, editable, and timeline-driven while the footage falls apart underneath.

## Animating a grade

Nine properties expose a CSS custom property and tween directly — `ascii`, `bloom`, `blur`, `dither`, `exposure`, `intensity`, `kuwahara`, `lut`, `pixelate`. Start them at identity so the shot opens ungraded and every intermediate value renders.

Two caveats worth knowing before you promise a client a ramp:

* **`--hf-color-grading-intensity` scales the primary grade only** — `adjust`, `wheels`, `curves`, `hueCurves`, `secondaries` and the LUT. `details` and `effects` sit outside that mix and it scales neither: some shape the sampled media before it, others run after it. So it will not ramp grain, halftone, bloom, or the tape and CRT families. Reach for the specific effect instead of treating it as a master dial.
* **Everything else has no custom property.** Some of those can still be animated by rewriting the `data-color-grading` payload from the timeline, and some cannot — the verified list of which is which lives in the guide's [Animating a Grade](/reference/color-grading#animate-a-supported-property), so it only has to be maintained in one place. Measure the effect you intend to animate before you promise a ramp, and fall back to a static treatment if it does not move.

## Next steps

* [Color Grading guide](/guides/color-grading) — the full contract, every key and bound
* [Catalog: overlays and effects](/catalog) — HUD, flash, light leak, freeze-frame dressing
* [VFX and liquid glass](/prompting/vfx-and-liquid-glass) — the canvas-pipeline end of the catalog

*Next: [VFX and liquid glass](/prompting/vfx-and-liquid-glass) — the same grading vocabulary pushed into the canvas pipeline.*


## Related topics

- [Color grade images and footage](/guides/color-grading.md)
- [Changelog](/changelog.md)
- [When to generate artwork](/prompting/generated-artwork.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.