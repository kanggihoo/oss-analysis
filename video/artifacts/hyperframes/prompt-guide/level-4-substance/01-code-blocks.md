> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Code animations

> Prompt code walkthroughs — typing, diffing, highlighting, scrolling — and pick a terminal or editor theme by name.

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

Your PR video from Level 1 named `code-diff` for a single beat and moved on. This chapter is the rest of that catalog: typing, diffing, highlighting, scrolling, and picking a terminal or editor theme by name — for the moments a walkthrough needs to slow down and let the code itself carry the scene.

Code is the one subject where the framework does the hard part for you. The [Code Animations](/catalog/blocks/code-typing) blocks handle syntax highlighting, caret tracking, diff coloring, and camera moves deterministically — you describe the *walkthrough*, name the block, and paste your snippet. This page is the vocabulary for doing that well; for turning a real pull request into a code-change video, see [Code and PRs](/prompting/code-and-prs).

Everything here follows the [one-shot skeleton](/prompting/anatomy): route, spec, beats, copy, technique, negatives. The "technique" slot is where you name the block, and the "copy" slot is where your code goes — quoted exactly, because unquoted code gets paraphrased into something that won't compile.

### Pick the motion by what the viewer should learn

Each Code Animations block answers a different "what is the viewer supposed to notice." Map the intent to the block:

| You want to show… | Name this block | Length |
| - | - | - |
| Code being written, character by character | [`code-typing`](/catalog/blocks/code-typing) | 5s |
| An edit — before → after, red/green | [`code-diff`](/catalog/blocks/code-diff) | 6s |
| One line as *the* line, everything else dim | [`code-highlight`](/catalog/blocks/code-highlight) | 5s |
| Walking a long file to a spot deep inside | [`code-scroll`](/catalog/blocks/code-scroll) | 6s |
| One snippet transforming into another | [`code-morph`](/catalog/blocks/code-morph) | 7s |
| Code on a rotating 3D slab (title-card feel) | [`code-3d-extrude`](/catalog/blocks/code-3d-extrude) | 8s |
| Code resolving out of a shader dissolve | [`code-shader-dissolve`](/catalog/blocks/code-shader-dissolve) | 7s |
| Code assembling from a particle swarm | [`code-particle-assemble`](/catalog/blocks/code-particle-assemble) | 8s |

The first four are the workhorses of a code *walkthrough* — they keep the code readable and the viewer oriented. Everything below them trades legibility for motion: they look great as an opener or a hero moment, but they trade legibility for motion, so don't ask them to carry an explanation.

<Tip>
  `code-morph` re-drives Shiki Magic Move as a paused GSAP timeline, and `code-diff` collapses removed lines and expands added lines. Both read "an edit happened" far more clearly than retyping the whole snippet with `code-typing` — reach for them when the story is *a change*, not *authoring from scratch*.
</Tip>

### Prompting a typing reveal

`code-typing` reveals code character by character with a caret that tracks the frontier — no CSS animation, so it seeks cleanly. Give it the exact code and a pace; the agent re-bakes the block's syntax tokens to your snippet.

> /motion-graphics 6-second 1920x1080 video. A dark editor types this snippet, character by character, caret tracking the frontier, then holds on the blinking cursor for the final second:
>
> ```
> export async function render(comp: Composition) {
>   await comp.seek(0);
>   return comp.capture();
> }
> ```
>
> Use the `code-typing` registry block. No narration, no image or media files.

<DocsVideo title="HyperFrames video: Validate Code Typing" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-code-typing.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

**Quote the code as a literal block.** Prose descriptions of code get paraphrased.

* ❌ `type out a function that seeks to zero and captures`
* ✅ paste the actual snippet in a fenced block — it renders verbatim

**Give the caret somewhere to rest.** Compositions hold their final state, so if you don't ask for a hold the last frame is a frozen full snippet — the [dead-motion tell](/prompting/motion).

* ❌ `types the code and ends`
* ✅ `types the code, then holds on the blinking cursor for the final second`

### Prompting a diff or a highlight

For "here's what changed," hand `code-diff` the before and after and let it color the delta. For "look at *this* line," give `code-highlight` the full context and name the target line.

> /motion-graphics 6-second 1920x1080 video. Show this edit to `api.ts` as a colored diff — the removed line collapses in red, the added line expands in green:
> removed: `const res = await fetch(url)`
> added: `const res = await fetch(url, { signal })`
> Use the `code-diff` registry block. No audio.

<DocsVideo title="HyperFrames video: Validate Code Diff" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-code-diff.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

> /motion-graphics 5-second 1920x1080 video. Show a 12-line config file; a highlight band sweeps to line 7 (`timeout: 30_000`) while the surrounding lines dim. Hold with line 7 lit and the cursor blinking. Use the `code-highlight` registry block. No audio.

<DocsVideo title="HyperFrames video: Validate Code Highlight" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-code-highlight.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited — the agent authors plausible surrounding config lines; paste all 12 if the exact file matters.*

**Name the target line unambiguously.** The block dims context around one line — tell it which.

* ❌ `highlight the important line`
* ✅ `highlight line 7 (timeout: 30_000)`

### Prompting a scroll-through

`code-scroll` moves the camera down a long file to bring a target line to center and spotlights it — the block for walking real modules, not toy snippets.

> /motion-graphics 6-second 1920x1080 video. Scroll a \~60-line source file so line 44 (`return dedupeFrames(frames)`) arrives at center and gets spotlighted; ease the scroll and let it settle without snapping. Use the `code-scroll` registry block. No audio.

<DocsVideo title="HyperFrames video: Code Scroll" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/code-scroll.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

**Ask the scroll to ease and settle, not snap.** A linear scroll that stops dead reads mechanical.

* ❌ `scroll straight to the line`
* ✅ `ease the scroll and let it settle` — pair with the [motion grammar](/prompting/motion)

### Choosing a theme by name

| Profile | Block | Profile | Block |
| - | - | - | - |

**VS Code workbench themes** — full editor chrome (activity bar, sidebar, tabs, terminal, status bar). Say "monokai" or "visual studio dark":

| Say this | Block | Say this | Block |
| - | - | - | - |

<DocsVideo title="HyperFrames video: Terminal Ocean" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/terminal-ocean.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

**Match the theme to the surface you're claiming to show.** A terminal command in a VS Code editor chrome reads wrong; a source file in Terminal.app reads wrong.

* ❌ `monokai theme typing a shell command`
* ✅ `apple terminal homebrew profile typing a shell command`

<Tip>
  Ambiguity resolves to the closest named block. "Dark theme" is under-specified — the agent picks one of a dozen dark variants and you may not get the one you pictured. Say the theme name. This is the [specification dial](/prompting/specification-dial) applied to code: name the block when the default choice can miss.
</Tip>

### Pairing with a pull request

When the code you're animating comes from a real PR, don't hand-write the beats — the [`/pr-to-video`](/prompting/code-and-prs) workflow reads the diff and composes `code-diff`, `code-highlight`, and `code-scroll` around the actual changed hunks. Use the blocks on this page directly when you're illustrating a concept; route through the PR workflow when you're narrating a specific change set.

### Where to go next

* [Anatomy of a one-shot prompt](/prompting/anatomy) — the skeleton every prompt above uses.
* [Copy-paste examples](/prompting/examples) — full prompts you can adapt.
* [Code and PRs](/prompting/code-and-prs) — turning a GitHub PR into a code-change video.
* [Motion that reads premium](/prompting/motion) — the hold-and-settle rules the code blocks still need from you.

<Note>
  **Capstone thread** — the [Level 7 film](/prompting/capstone) opens with this chapter's technique: real HyperFrames markup typed character by character, and the typed line's baseline literally grows into the timeline wire the rest of the film travels (cut from the film, below).
</Note>

This is the clause in the [full capstone prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece — prompt language you can lift for your own video:

> **Type (0–7s).** Black-on-charcoal close-up: a cursor types real HyperFrames markup character by character — `<div class="clip" data-start="0" data-duration="4">` and a `gsap.timeline({ paused: true })` line. As the typed line completes, the text's baseline extends and becomes **the wire** — the underline literally grows into the timeline and the camera begins its dolly along it. The typed div folds into a compact clip chip (persistent element 3) that drops onto the wire. Kinetic display type states "WRITE HTML." as the travel begins.

<DocsVideo title="HyperFrames video: Capstone Region Type" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-type.mp4#t=0.1" loop />

*That clause, rendered — the region cut from the finished film.*

*Next: [Data and maps](/prompting/data-and-maps) — the same named-block, quoted-copy pattern, for charts, stats, and maps instead of code.*


## Related topics

- [Changelog](/changelog.md)
- [Prompt Guide](/prompting/overview.md)
- [Transitions](/prompting/transitions.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.