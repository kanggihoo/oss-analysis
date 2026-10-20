> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Code changes and PRs

> What to say to turn a GitHub pull request into a code-change explainer — changelog, feature reveal, fix, or refactor walkthrough.

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

Two rides in, both built from nothing yet on the page. This one starts from something that already exists and is already true — a merged PR — and turns the diff itself into the story.

## Your first win

One prompt to [`/pr-to-video`](/prompting/overview), pointed at a PR link, is enough for a finished code-change explainer — no technique required yet.

Verified, from the [examples](/prompting/examples) page — a 30-second feature reveal:

> /pr-to-video Make a 30-second 1920x1080 feature-reveal video from \[PR URL]. Lead with what users get, not the diff; show the key code change with the `code-diff` block for one beat only; end on version number + repo URL. No narration, kinetic captions instead.

<DocsVideo title="HyperFrames video: Example Pr Video" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-pr-video-v2.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

## What this makes

A code-change explainer built from a GitHub pull request. The [`/pr-to-video`](/prompting/overview) workflow reads the PR through `gh` — the diff, commits, files, and contributors — reshapes it into a story, and builds it frame by frame, rendering code beats on a purpose-built diff surface.

The input is a **code change**, not a website or a product page. A PR link (`https://github.com/owner/repo/pull/N`), an `owner/repo#N` ref, or "this PR" in a checked-out repo all work. A product to sell → [`/product-launch-video`](/prompting/product-launch); a topic with no PR → [`/faceless-explainer`](/prompting/explainers). Unsure → start at `/hyperframes`.

## The knobs that matter

What you can already steer from the prompt, before you've learned any technique.

| Knob | What to say | Why it matters |
| - | - | - |
| **Impact vs diff** | "lead with what users get, not the diff" | The video explains the *change*, it doesn't read the diff aloud; opening on impact answers "why should I care?" before the code |
| **How many hunks** | "one `code-diff` beat only" / "at most two hunks" | Code beats feature 2-4 real hunks total, each a small legible snippet — a whole file is unreadable at video scale |
| **Which code block** | `code-diff` for a delta · `code-morph` for a refactor · `code-typing` for new code | The block matches the story: a diff shows added/removed lines, a morph shows one shape becoming another |
| **Angle** | "changelog" / "feature-reveal" / "fix-explainer" / "refactor-walkthrough" | Sets the story shape; the workflow reshapes the PR into it rather than walking files in diff order |
| **Audience** | "for developers" (default) / "mixed technical" / "non-technical stakeholders" | Shifts how much the narration assumes — a non-technical cut leans harder on impact and lighter on code |
| **End card** | "end on version number + repo URL" | The conventional close for a code explainer; state what goes on it so it's a real CTA, not an afterthought |
| **Narration vs captions** | "calm male narration" or "no narration, kinetic captions instead" | Both are supported; captions-only keeps it silent-friendly for social, narration carries a longer walkthrough |
| **Length** | "\~30s" for one headline, up to \~3 min for a large PR | The workflow reads the change size and recommends a tier — a huge PR is a ceiling on story, not a floor to fill |

<Tip>
  The style is fixed to the workflow's warm-editorial preset with a navy code surface built for diffs — it's what makes the code beats legible. You don't choose a theme here; you choose the angle, the hunks, and the narration.
</Tip>

## Variants

<AccordionGroup>
  <Accordion title="Changelog roundup">
    > /pr-to-video Make a \~40-second 1920x1080 changelog video from \[PR URL]. Changelog angle: open with the release line, then one beat per notable change — a short label and a one-line "what it does" each. Show at most two `code-diff` hunks across the whole video. End on version + repo URL. Calm male TTS narration, no captions.

    <DocsVideo title="HyperFrames video: Variant Pr Changelog" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/variant-pr-changelog.mp4#t=0.1" loop />

    *Rendered from this prompt with \[PR URL] = heygen-com/hyperframes#2092, unedited.*

    A changelog trades depth for breadth — many small changes, each a beat, rather than one change explored deeply. Keep code beats sparse so the pace stays fast. A PR doesn't carry its shipping version — the agent finds it from the release tag or the package manifest on main.
  </Accordion>

  <Accordion title="Fix explainer">
    > /pr-to-video Make a \~40-second 1920x1080 fix-explainer from \[PR URL], for developers. Fix angle: state the bug's symptom first, then the root cause, then the one-line fix on the `code-diff` block. End on version + repo URL. No narration, kinetic captions.

    A fix reads as symptom → cause → fix. Lead with what users saw break, not the stack trace — the diff is the payoff, not the opening.
  </Accordion>

  <Accordion title="Refactor walkthrough">
    > /pr-to-video Make a \~70-second 1920x1080 refactor-walkthrough from \[PR URL], for developers. Refactor angle: why the old shape hurt, then the new shape, showing the before/after with the `code-morph` block for the key file. End on version + repo URL. Calm male TTS narration.

    A refactor changes shape without changing behavior, so the story is *why* the new structure is better. `code-morph` animates one form transforming into another — the right block when the point is the transition, not a line-by-line delta.
  </Accordion>
</AccordionGroup>

## Common failure modes

**Forcing a theme over the preset.** The general rule is on [ride 1](/prompting/product-launch#common-failure-modes); the specific reason here is that the navy code surface is tuned for diff legibility, so a foreign theme costs you the one thing the workflow is good at.

* ❌ `/pr-to-video ... dark theme, neon accents`
* ✅ let the preset carry the look; spend your specificity on the angle and the code beats

**Asking for the whole diff.** A PR video explains the change; it doesn't recite every file. A full diff is unreadable at video scale.

* ❌ `walk through the entire diff, file by file`
* ✅ `feature the 2-3 key hunks, each a small legible snippet`

**Opening on the code.** The diff is the payoff, not the hook — lead with what the change means.

* ❌ `start with the diff, then explain what it does`
* ✅ `lead with what users get, then show the key hunk`

**Hard-timing a narrated cut.** As in [ride 1](/prompting/product-launch#common-failure-modes) — the spoken length sets the runtime, so state a range.

* ❌ `a 40-second narrated walkthrough`
* ✅ `a ~40-second narrated walkthrough`

The workflow this level rides is documented at [PR to video](/guides/pr-to-video) — what it takes as input, what it asks you before it builds, and what it returns.

*Next: [Captions and talking-head footage](/prompting/captions-and-talking-heads) — same one-prompt move, now dressing footage you already shot.*


## Related topics

- [Explainers](/prompting/explainers.md)
- [Code animations](/prompting/code-blocks.md)
- [Week in Merges](/catalog/blocks/week-in-merges.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.