> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Transitions

> Map energy and mood to named shader and CSS transition blocks, and prompt them per seam.

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

[Motion](/prompting/motion)'s eight rules were written for what happens inside one scene. Rule 2's camera and rule 3's overlap apply *between* scenes too — a transition is that same grammar aimed at the cut itself, not a separate feature to bolt on afterward.

## What transitions do and when they trigger

A transition tells the viewer how two scenes relate — a crossfade says "this continues," a whip pan says "next point," a burn says "something changed." Most compositions with more than one scene want them: an *unmotivated* scene change reads as an accidental jump cut (see [rules and anti-patterns](/prompting/rules-and-anti-patterns)). A bare cut is legitimate when something else carries the continuity — a match cut on a shared shape, a beat grid, a prop that stays on screen — which is the alternatives table in [avoiding the slideshow](/prompting/motion#avoiding-the-slideshow). The skills add transitions by default, so prompts trigger this layer whenever you describe scene changes, crossfades, wipes, reveals, or a mood ("warm," "clinical," "glitchy") — or when you name a block directly.

Two families, both first-class:

* **[Shader transitions](/catalog/blocks/cross-warp-morph)** composite both scenes per-pixel on a WebGL canvas — they warp, dissolve, and morph in ways CSS cannot. Reach for these when the *handoff itself* is a moment (a hero reveal, a topic pivot with weight).
* **CSS transitions** animate the scene containers with opacity, transforms, clip-path, and filters. Simpler and lighter; reach for these for the 60–70% of ordinary scene changes where the content is just continuing.

Choose by the effect you want, not by which is easier. See also the transitions table in [vocabulary](/prompting/vocabulary).

<Note>
  The catalog pages linked here are standalone demos of each effect. In a real multi-scene build the agent wires the same effects through the `@hyperframes/shader-transitions` package (`HyperShader.init`) — you never need to say that; naming the transition is enough.
</Note>

## Energy → transition

Pick **one primary** transition for most scene changes, plus one or two accents for topic changes and the climax. Never use a different transition on every seam — that reads as chaos, not design.

| Energy | Shader primary | CSS primary | Feels like |
| - | - | - | - |
| **Calm** (wellness, brand story, luxury) | [`cross-warp-morph`](/catalog/blocks/cross-warp-morph), [`thermal-distortion`](/catalog/blocks/thermal-distortion) | [`transitions-blur`](/catalog/blocks/transitions-blur), [`transitions-dissolve`](/catalog/blocks/transitions-dissolve) | Soft, slow, drifting |
| **Medium** (corporate, SaaS, explainer) | [`whip-pan`](/catalog/blocks/whip-pan), [`cinematic-zoom`](/catalog/blocks/cinematic-zoom) | [`transitions-push`](/catalog/blocks/transitions-push), [`transitions-cover`](/catalog/blocks/transitions-cover) | Clean, directional, decisive |
| **High** (promos, sports, music, launch) | [`ridged-burn`](/catalog/blocks/ridged-burn), [`glitch`](/catalog/blocks/glitch), [`chromatic-radial-split`](/catalog/blocks/chromatic-radial-split) | [`transitions-scale`](/catalog/blocks/transitions-scale), [`transitions-destruction`](/catalog/blocks/transitions-destruction), [`transitions-light`](/catalog/blocks/transitions-light) | Fast, punchy, aggressive |

## Mood → transition

Energy sets tempo; mood sets meaning. Describe the brand feeling and the agent picks a matching block.

| Mood | Shader | CSS |
| - | - | - |
| **Warm / inviting** | [`light-leak`](/catalog/blocks/light-leak), [`thermal-distortion`](/catalog/blocks/thermal-distortion), [`cross-warp-morph`](/catalog/blocks/cross-warp-morph) | [`transitions-light`](/catalog/blocks/transitions-light), [`transitions-blur`](/catalog/blocks/transitions-blur) |
| **Cold / clinical** | [`gravitational-lens`](/catalog/blocks/gravitational-lens) | [`transitions-mechanical`](/catalog/blocks/transitions-mechanical), [`transitions-grid`](/catalog/blocks/transitions-grid) |
| **Editorial / magazine** | [`whip-pan`](/catalog/blocks/whip-pan) | [`transitions-push`](/catalog/blocks/transitions-push) |
| **Tech / futuristic** | [`glitch`](/catalog/blocks/glitch), [`chromatic-radial-split`](/catalog/blocks/chromatic-radial-split) | [`transitions-grid`](/catalog/blocks/transitions-grid) |
| **Tense / edgy** | [`ridged-burn`](/catalog/blocks/ridged-burn), [`glitch`](/catalog/blocks/glitch), [`domain-warp-dissolve`](/catalog/blocks/domain-warp-dissolve) | [`transitions-distortion`](/catalog/blocks/transitions-distortion) |
| **Playful / fun** | [`ripple-waves`](/catalog/blocks/ripple-waves), [`swirl-vortex`](/catalog/blocks/swirl-vortex) | [`transitions-3d`](/catalog/blocks/transitions-3d), [`transitions-radial`](/catalog/blocks/transitions-radial) |
| **Dramatic / cinematic** | [`cinematic-zoom`](/catalog/blocks/cinematic-zoom), [`gravitational-lens`](/catalog/blocks/gravitational-lens), [`domain-warp-dissolve`](/catalog/blocks/domain-warp-dissolve) | [`transitions-scale`](/catalog/blocks/transitions-scale) |
| **Premium / luxury** | [`cross-warp-morph`](/catalog/blocks/cross-warp-morph), [`thermal-distortion`](/catalog/blocks/thermal-distortion) | [`transitions-blur`](/catalog/blocks/transitions-blur), [`transitions-dissolve`](/catalog/blocks/transitions-dissolve) |
| **Retro / analog** | [`light-leak`](/catalog/blocks/light-leak) | [`transitions-light`](/catalog/blocks/transitions-light) |

Special-purpose seams: [`flash-through-white`](/catalog/blocks/flash-through-white) for a bright cut on an impact beat, [`sdf-iris`](/catalog/blocks/sdf-iris) for a clean iris reveal into a hero shot.

## Example prompts

Name the block and the seam — transitions are the one place where per-seam control usually beats letting the agent decide.

> /general-video Six-scene SaaS explainer. Use [`whip-pan`](/catalog/blocks/whip-pan) as the primary transition between related points, and one [`cinematic-zoom`](/catalog/blocks/cinematic-zoom) into the final pricing reveal. Medium energy, \~0.4s each.

<DocsVideo title="HyperFrames video: Validate Transitions" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-transitions.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited — whip-pan on four seams, cinematic-zoom into the pricing reveal.*

> Between beats 2 and 3, transition with [`swirl-vortex`](/catalog/blocks/swirl-vortex); keep every other seam on a plain blur crossfade.

> Warm transitions for this wellness brand — [`light-leak`](/catalog/blocks/light-leak) between scenes, nothing sharp or mechanical. Slow, 0.6–0.8s.

> Music promo, high energy. [`glitch`](/catalog/blocks/glitch) on the phrase changes, [`ridged-burn`](/catalog/blocks/ridged-burn) on the drop. Fast cuts, 0.15–0.25s.

## Knobs

* **Duration** follows energy: calm 0.5–0.8s, medium 0.3–0.5s, high 0.15–0.3s. Say a number to pin it.
* **Primary + accents.** One primary carries most seams; spend your boldest accent on the climax. State the split ("`whip-pan` throughout, one `ridged-burn` on the reveal").
* **Per-seam placement.** "on phrase changes," "between beats 2 and 3," "into the final scene" all bind a transition to a specific cut.
* **Blur intensity** (CSS blur crossfades): heavier (20–30px) for calm, light (3–6px) for high energy.
* **Easing presets:** `snappy`, `smooth`, `gentle`, `dramatic`, `instant`, `luxe` map to tuned duration/ease pairs.

## Failure modes

**Don't fade the outgoing scene out, then fade the next one in.** The renderer holds each scene's final state, so an explicit fade-out followed by an entrance renders as a jump cut with a dip in the middle — not a transition. The transition *is* the exit; both scenes hand off at the same instant.

* ❌ `fade scene 1 out, then fade scene 2 in`
* ✅ `cross-warp-morph from scene 1 to scene 2`

**Don't ask for a different transition on every seam.** A new effect at each cut reads as noise; consistency is what makes the one bold accent land.

* ❌ `use a different transition between each scene`
* ✅ `whip-pan as the primary, one glitch on the hero reveal`

**Don't leave "add transitions" unqualified when tone matters.** Bare requests get a sensible default; if the brand feeling is load-bearing, name the energy or mood (see [the specification dial](/prompting/specification-dial)).

* ❌ `add some transitions`
* ✅ `medium-energy editorial transitions — whip-pan primary`

**Don't invent transition names.** Only the blocks in the [shader](/catalog/blocks/cross-warp-morph) and CSS transition groups exist; a made-up name (`page-curl`, `star-iris`) sends the agent guessing at raw GLSL or an unsupported CSS effect.

* ❌ `add a page-curl transition`
* ✅ pick a real block, e.g. `sdf-iris` for an iris reveal

<Note>
  **Capstone thread** — the [Level 7 film](/prompting/capstone) allows itself exactly one shader seam: the camera pushes through an `sdf-iris` lens into the Surface region (cut from the film, below) with the timeline wire visible through the iris the whole way — a lens the journey passes through, not a cut.
</Note>

This is the clause in the [full capstone prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece — prompt language you can lift for your own video:

> SANCTIONED SEAM #1: the camera pushes through an **`sdf-iris` shader transition** — the iris opens ONTO the continuation of the same wire (the wire is visible through the iris throughout; this is a lens the journey passes through, not a cut).

<DocsVideo title="HyperFrames video: Capstone Region Surface" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-surface.mp4#t=0.1" loop />

*That clause, rendered — the region cut from the finished film.*

*Next: [Code animations](/prompting/code-blocks) — naming a block and pasting real code for walkthroughs, diffs, and terminal takes.*


## Related topics

- [Dissolve Transitions](/catalog/blocks/transitions-dissolve.md)
- [Distortion Transitions](/catalog/blocks/transitions-distortion.md)
- [Other Transitions](/catalog/blocks/transitions-other.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.