> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Caption styles

> Map caption tone to named caption components, and prompt per-word emphasis for composed videos.

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

Your faceless explainer from Level 1 already asked for "embedded captions, keywords highlighted in the accent color" and got a sensible default. This chapter is the catalog behind that ask — the named components you can pin instead, by tone, so the highlight color and the animation are a decision, not a default.

## What caption styles do and when they trigger

Caption components are drop-in snippets that render animated on-screen text — one visual identity per component, animating per word or per line. Prompts trigger this layer when you ask for captions, subtitles, kinetic text, lyric-style words, or word-by-word titles inside a composition you're building. Describe the *energy* of the captions and the agent picks matching typography, size, and animation; name a component to lock the look.

<Note>
  These components are for **composed videos** — captions you author into a HyperFrames composition. To add captions to an existing **talking-head MP4**, use the [`/embedded-captions`](/prompting/captions-and-talking-heads) workflow instead: it carries its own catalog of caption identities built around subject matting and occlusion (the caption sits *behind* the speaker), which the composition snippets below don't do.
</Note>

## Tone → caption component

| Tone | Components |
| - | - |
| **Hype / high-energy social** | [`caption-kinetic-slam`](/catalog/components/caption-kinetic-slam), [`caption-highlight`](/catalog/components/caption-highlight), [`caption-particle-burst`](/catalog/components/caption-particle-burst), [`caption-emoji-pop`](/catalog/components/caption-emoji-pop) |
| **Clean / corporate** | [`caption-clip-wipe`](/catalog/components/caption-clip-wipe), [`caption-weight-shift`](/catalog/components/caption-weight-shift) |
| **Elegant / editorial** | [`caption-editorial-emphasis`](/catalog/components/caption-editorial-emphasis), [`caption-gradient-fill`](/catalog/components/caption-gradient-fill), [`caption-weight-shift`](/catalog/components/caption-weight-shift) |
| **Neon / nightlife / music** | [`caption-neon-glow`](/catalog/components/caption-neon-glow), [`caption-neon-accent`](/catalog/components/caption-neon-accent) |
| **Tech / cyber / glitch** | [`caption-glitch-rgb`](/catalog/components/caption-glitch-rgb), [`caption-matrix-decode`](/catalog/components/caption-matrix-decode) |
| **Karaoke / lyric / follow-along** | [`caption-pill-karaoke`](/catalog/components/caption-pill-karaoke), [`caption-highlight`](/catalog/components/caption-highlight) |
| **Textured / cinematic display type** | [`caption-texture`](/catalog/components/caption-texture), [`texture-mask-text`](/catalog/components/texture-mask-text) |
| **Depth / 3D layering** | [`caption-parallax-layers`](/catalog/components/caption-parallax-layers) |

## Text-effect components

Three [Text Effects](/catalog/components/morph-text) components do one focused job rather than caption a whole track:

| Component | Use when |
| - | - |
| [`caption-blend-difference`](/catalog/components/caption-blend-difference) | Text sits over busy or shifting footage and must stay legible — it auto-inverts per pixel against whatever is behind it. |
| [`morph-text`](/catalog/components/morph-text) | You want one spot to cycle through a short word list with a gooey morph ("fast / simple / yours"). |
| [`texture-mask-text`](/catalog/components/texture-mask-text) | A large display word filled with a physical texture (brick, rock, wood, metal, lava). |

## Example prompts

> /faceless-explainer 30-second vertical explainer. Add [`caption-highlight`](/catalog/components/caption-highlight) captions, TikTok-style — the visible line stays up, one word highlighted at a time.

<DocsVideo title="HyperFrames video: Validate Captions Catalog" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-captions-catalog.mp4#t=0.1" portrait loop />

*Rendered from the prompt above, unedited.*

<Note>
  Caption components ship as demos — a fixed word list, landscape sizing, an 8-second timeline. The agent re-authors the words and timings to your narration and re-sizes for your format; that's expected, not a workaround. If you want one full-screen word at a time (no visible line), that's [`caption-kinetic-slam`](/catalog/components/caption-kinetic-slam), not `caption-highlight`.
</Note>

> Hype captions with [`caption-kinetic-slam`](/catalog/components/caption-kinetic-slam): one full-screen word per beat, alternating slam-in direction.

<DocsVideo title="HyperFrames video: Caption Kinetic Slam" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/caption-kinetic-slam.mp4#t=0.1" loop />

*Rendered from the prompt above with an authored 24-word line, unedited.*

> Neon music-video captions using [`caption-neon-glow`](/catalog/components/caption-neon-glow). Make brand names larger with an accent color and highlight the numbers differently.

<DocsVideo title="HyperFrames video: Caption Neon Glow" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/caption-neon-glow.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited — the brand renders 1.4x in magenta, numbers in amber, distinct from the default cyan.*

> Fill the hero word "STONE" with [`texture-mask-text`](/catalog/components/texture-mask-text) using the rock texture.

## Knobs

* **Tone** picks typography, size, and animation — Hype (heavy, 72–96px, scale-pop) through Storytelling (serif, 44–56px, slow fade). See the caption-tone table in [vocabulary](/prompting/vocabulary).
* **Per-word emphasis.** "Make brand names larger with accent color," "highlight numbers differently," "add bounce to emotional keywords" all work — several components key off this: [`caption-editorial-emphasis`](/catalog/components/caption-editorial-emphasis) drives a dramatic size contrast on emphasis words, [`caption-particle-burst`](/catalog/components/caption-particle-burst) fires on keywords, and the neon components carry keyword accent colors.
* **Texture variable.** [`caption-texture`](/catalog/components/caption-texture) ships lava, marble, metal, wood, concrete, and rock — name the one you want.
* **Word list.** [`morph-text`](/catalog/components/morph-text) cycles an editable list; quote the words in order.
* **Format.** Full-screen single-word styles ([`caption-kinetic-slam`](/catalog/components/caption-kinetic-slam)) and TikTok-style highlights ([`caption-highlight`](/catalog/components/caption-highlight)) are built for vertical / social framing — say "vertical" or "9:16" so sizing and safe areas match.

## Failure modes

**Don't stack a heavy effect on every word.** Caption components already animate per word; layering another emphasis on top of that competes and turns illegible. Emphasize only the keywords.

* ❌ `make every word explode with particles`
* ✅ `caption-particle-burst, firing only on the keywords`

**Don't mix caption styles in one section.** One identity per composition (or per section) reads as designed; two competing styles read as a mistake.

* ❌ `use caption-neon-glow and caption-matrix-decode together`
* ✅ pick one; switch styles only across a clear section break

**Don't reach for these on talking-head footage.** These are composition snippets, not the matting/occlusion pipeline — dropped onto an untouched MP4, a caption sits in front of the speaker, never behind. (The capstone thread below shows `caption-kinetic-slam` reading *behind* a subject, which is not a contradiction: that composition mattes the footage itself first, so the cutout is a separate layer the type can pass under. The limitation is about the snippet alone, not the technique.)

* ❌ `/hyperframes add caption-highlight to my interview.mp4`
* ✅ `/embedded-captions` (see [captions and talking heads](/prompting/captions-and-talking-heads))

**Don't match a hype style to calm content.** A high-energy caption on a corporate explainer fights the tone; let the tone table pick the identity.

* ❌ `glitchy RGB captions` (on a wellness brand piece)
* ✅ `clean captions with caption-clip-wipe`

**Don't invent caption names.** Only the components in the [Captions](/catalog/components/caption-highlight) and [Text Effects](/catalog/components/morph-text) groups exist.

* ❌ `add typewriter-bounce captions`
* ✅ describe the tone ("tutorial, monospace, typewriter") or name a real component

<Note>
  **Capstone thread** — in the [Level 7 film](/prompting/capstone)'s Material region, word-synced keywords from the clip's own transcription slam in as display type behind the matted-out speaker — captions as scenography, on real word timings (cut from the film, below).
</Note>

This is the clause in the [full capstone prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece — prompt language you can lift for your own video:

> THEN they speak, and the main **keywords of their own line — derived from the clip's transcription — land word-synced as huge display text BEHIND the cutout**, each keyword slamming in on its spoken moment with the subject's silhouette occluding it (the two-layer text-behind-subject plate); style the keyword type by adapting a bold **catalog caption component** (`caption-kinetic-slam` or similar) at display scale.

<DocsVideo title="HyperFrames video: Capstone Region Material" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-material.mp4#t=0.1" loop />

*That clause, rendered — the region cut from the finished film.*

*Next: [When to generate artwork](/prompting/generated-artwork) — where hand-drawn HTML/CSS/SVG wins, and where a generated image beats it.*


## Related topics

- [Camera Follow Captions](/catalog/components/caption-camera-follow.md)
- [Highlight](/catalog/components/caption-highlight.md)
- [Pill Karaoke](/catalog/components/caption-pill-karaoke.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.