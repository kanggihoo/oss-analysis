> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Editing existing videos

> Direct the agent like an editor — trim, move, retime, swap, restyle — with the NLE verb you already know mapped to the prompt that lands it in one pass.

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

A [storyboard](/prompting/storyboards)'s frames still get edited, and so does everything else you build — a templated composition, a one-shot scene, all of it. Most HyperFrames time isn't the first render — it's the twenty edits after it. A composition is plain HTML with `data-*` timing attributes and a GSAP timeline, so every edit you'd make in a non-linear editor maps to a specific, inspectable change in the source. You don't re-specify the video; you name the edit the way you'd say it to a human editor, and the agent makes the smallest change that does it.

This page maps the editor verbs to the prompts that land them. The examples name elements from a typical composition — swap the noun ("the lower third", "scene 2") for whatever yours is called. Two habits from [Iterating](/prompting/iterating) apply to every one of them, so keep them in mind: **change one thing per render**, and **state targets as absolute values** ("scene 2 = 2 seconds", not "a bit shorter") so the agent lands it in a single pass instead of oscillating.

## The verb → edit map

Every timeline verb resolves to a `data-*` attribute or an inline style. This is what each one touches under the hood — useful to know because it's why absolute targets work and why some edits are cheap:

| You say | Editor verb | What the agent edits |
| - | - | - |
| "start scene 2 later / earlier" | Move | `data-start` |
| "put the captions on top of the video" | Restack | `data-track-index` + inline `z-index` |
| "end the logo sooner" | Trim (right) | `data-duration` |
| "skip the first second of the clip" | Trim (front, media only) | `data-media-start` |
| "make scene 2 two seconds long" | Retime | `data-duration` (and the GSAP timeline length) |
| "the audio bed is too loud" | Level | `data-volume` |

<Note>
  The mental model the Studio timeline uses: **move** changes when a clip *starts*, **right trim** changes when it *ends*, and **front trim** only exists for media clips — a `<video>` or `<audio>` can skip into its own content, but a GSAP-driven `<div>` can't start halfway through its animation. See [Studio timeline](/studio/timeline) for the full clip-type breakdown. One more surface the map can't show: retiming a scene that spans the whole composition also needs the root's `data-duration` bumped — the root governs total length, so a longer child never renders past it.
</Note>

## Trim, move, and restack

These are the pure-timing edits — no visual change, just when and where a layer lives on the timeline.

> Trim the intro so it ends at 0:03 instead of 0:05.

> Move the lower third to start at 0:06.

> The captions are rendering behind the video — put them on a higher track so they sit on top.

Bound moves by the composition's length — a 4-second clip moved to 0:08 in a 10-second video barely appears before the end. And absolute targets matter most here: "make the intro shorter" invites a guess; "the intro should end at 3.0s" is a single `data-duration` write with nothing to overshoot.

* ❌ `tighten up the opening`
* ✅ `intro clip duration = 3s; leave its animation and position alone` — one attribute, and the freeze clause stops a rebuild from drifting on axes you'd already settled

<DocsVideo title="HyperFrames video: Editing Before" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/editing-before.mp4#t=0.1" loop />

*Before — the untouched composition.*

<DocsVideo title="HyperFrames video: Editing After" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/editing-after.mp4#t=0.1" loop />

*After — four verbatim edits from this page (move, right-trim, retime, restyle-with-freeze); each touched exactly the attribute the verb map promises, gates green after every edit.*

## Split a scene

The Studio timeline exposes move and trim as drag gestures but does **not** yet offer split, slip, slide, ripple, or roll. You can still split by directing the agent, because it edits the HTML directly — a split is just one clip becoming two with adjusted `data-start` / `data-duration`:

> Split scene 2 at 0:04 so I can drop a transition between the two halves.

Name the exact cut point. The agent turns one clip into two adjacent clips; you then treat each half as its own layer.

## Retime a scene

Retiming starts with the scene's `data-duration`. If the motion should keep its original speed, the timeline can finish early and hold its final state while the scene continues. If the motion itself should slow down or spread across the longer scene, ask the agent to retime the affected tweens as well.

> Make scene 2 run 4 seconds instead of 2.5 — keep the animation, just give it more room.

* ❌ `stretch scene 2` — ambiguous whether you mean slower motion or a longer hold
* ✅ `scene 2 duration = 4s, same motion, add the extra time as a hold at the end`

<Warning>
  Render duration comes from `data-duration`, not GSAP timeline length. Do not pad a timeline with an empty `tl.set({}, {}, <seconds>)` sentinel. If a scene still ends early, check the scene and composition timing attributes in [Data attributes](/concepts/data-attributes).
</Warning>

## Make it snappier (retiming *feel*, not just duration)

"Snappier," "punchier," "more relaxed" are pacing words, and they map to concrete easing and timing choices — [Vocabulary](/prompting/vocabulary) has the full table. The agent reads "snappy" as a decisive ease (`power4.out`) and tighter durations, "dreamy" as slow symmetrical motion, and so on.

> Make scene 2 snappier — quicker entrances, harder cuts.

> The reveal feels robotic; give it a bouncy overshoot.

Change one scene's feel per render so you can attribute what helped. If a scene keeps missing, strip it to the minimal version (subject + its motion only), confirm it reads, then re-layer.

## Adjust a keyframe

Individual animation properties are editable — the value, the ease, the timing of any tween. You can direct these by prompt, or edit them yourself in the Studio Design Panel; either way they resolve to the same GSAP code.

> The title slides in from too far — change its entrance to travel 40px, not 200.

> Give the add-to-cart item an arc instead of a straight diagonal, like it's being tossed into the cart.

State the property target absolutely (`Move X = 40`, `arc curviness ≈ 1.5`). [Animation and keyframes](/studio/animation) covers what's editable, motion paths, and gesture recording.

<Tip>
  For an element-specific edit, the Design Panel's clipboard icon copies structured context — the element's id, position, size, and current animation — ready to paste into your prompt. It gives the agent exact spatial context instead of a vague "the title."
</Tip>

## Swap an asset

Replacing a video, image, logo, or audio track is a source-swap. The one rule: **name the path.** The agent will search for "my logo," but a path skips the search and removes the ambiguity of which file you mean.

> Replace the background music with `assets/track.mp3`.

> Swap the hero image for `assets/product-v2.png` and keep its animation.

* ❌ `use the new logo`
* ✅ `swap the logo for assets/logo-2025.svg`

## Change copy

On-screen text is edited verbatim when you quote it. Unquoted text gets paraphrased — the agent treats a description as an instruction to write copy, not to place it exactly.

> Change the headline to "Ship faster." — exact text, keep the styling.

* ❌ `update the title to say something about speed`
* ✅ `title copy: "Ship faster."`

## Restyle one element

Visual tweaks — color, size, weight, position of a single element — are where the "freeze the rest" clause earns its keep. Without it, a restyle prompt can trigger a rebuild that drifts on layout or motion you'd already approved.

> Make the CTA button 20% larger and switch it to the accent color — don't touch anything else.

* ❌ `make the CTA pop more`
* ✅ `CTA background = accent color, font-size = 1.2× current; framing and motion are right, leave them`

## Related

<CardGroup cols={2}>
  <Card title="Iterating" href="/prompting/iterating">One variable per edit, absolute targets, freeze what works</Card>
  <Card title="Vocabulary" href="/prompting/vocabulary">Pacing and easing words that retime the *feel* of a scene</Card>
  <Card title="Studio timeline" href="/studio/timeline">Move, trim, split, and navigate clips</Card>
  <Card title="Data attributes" href="/concepts/data-attributes">The `data-*` timing contract</Card>
</CardGroup>

*Next: [Iterating](/prompting/iterating) — the discipline behind every edit on this page: one variable per render, absolute targets, freeze what works.*


## Related topics

- [Iterating](/prompting/iterating.md)
- [Storyboards](/prompting/storyboards.md)
- [Finish and share a video](/guides/export-and-share.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.