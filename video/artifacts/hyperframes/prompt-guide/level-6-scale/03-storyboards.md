> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Storyboards

> For multi-scene work, don't prompt the scenes one by one — prompt the plan: the arc, the per-frame beats, and the pacing rule the build follows to fill them in.

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

[Variables and templating](/prompting/variables-and-templating) was about reusing one composition across many renders. This page is the other axis of scale: one film with many scenes.

Past a handful of beats, describing each scene from a blank page is the slow way. "Then frame 2 shows X, then frame 3 shows Y." It also drifts, because nothing ties the frames to each other.

Prompt the **plan** once instead — the throughline, the job each frame does, the rule that paces reveals. Then let the build put frames against it.

This narrative vocabulary is a writing discipline, not extra `STORYBOARD.md` schema. The workflow translates your plan into the smaller machine-readable shape the build consumes.

<Note>
  "Storyboard" is also a question the agent asks in the [opening interview](/prompting/overview#the-interview-what-the-agent-asks-first). Say yes there and the plan (in chat), the stills (a board at `boards/storyboard.html`), and the build all get reviewed with you pass by pass. That answer changes the review process, not the route. Either way, the plan this page teaches is what the build works from.
</Note>

## Prompt the plan, not the scenes

A storyboard is a short, structured document that sits above the individual frames. It holds three things:

* one arc
* one direction block that every frame inherits
* a light per-frame spec — not a full description — for each key moment

The workflow reads the plan and builds each frame's HTML sub-composition against it. Be precise about the *shape* of the film, and the frames come out already agreeing with each other on pacing, palette, and payoff. You never restate any of that per frame.

The trigger is naming the arc and asking for a storyboard rather than a single scene:

> Storyboard a 3-frame piece: hook → substance → landing, silent, \~15 seconds, with a callback that pays off the opening motif.

Everything below is the vocabulary that turns "storyboard" from a loose word into a plan the build can execute in one pass.

## State the film's shape once

Before any frame, fix four things that every frame will be judged against:

* **Message** — the one-sentence thesis the whole film has to prove. If a frame doesn't serve it, cut the frame, not the message.
* **Arc** — the beat sequence, named plainly. `Hook → Substance → Landing`, or `Hook → Problem → Solution → Proof → CTA`. Use a shape word like "listicle" when the frames are parallel entries rather than a rising sequence.
* **Audience** — who it's for, in a phrase. It calibrates tone and jargon for every frame at once.
* **Mood** — one music or energy descriptor, like "tense synth pulse, resolving to warm". Every frame's pacing should agree with it, even in a silent piece.

Say these four once, up front. Then no individual frame prompt has to re-justify its tone.

## Set the direction once, apply it to every frame

A storyboard's direction block is the set of rules every frame obeys without restating them. Four are worth naming explicitly.

**Two-color discipline.** Name a ground color and one ink color. Then say the rule out loud: nothing ever gets a second hue for emphasis. A bigger moment gets bigger through inversion, weight, scale, or density.

* ❌ `use the brand colors, plus a highlight color for the important bits`
* ✅ `ground: deep navy; ink: warm white. Emphasis = invert, scale up, or go denser — never a third color.`

**VO-paced reveals.** The rule itself lives in [Media and audio](/prompting/media-and-audio#pace-reveals-to-the-narration). A storyboard is where you *apply* it per frame. At t=0, only what the narrator is saying is on screen, and each part arrives on its spoken cue.

Pair it with a hold behavior. Say whether a held frame stays fully still or gets a subtle idle. Never ask for a slow drift or "breathing" — that reads as unfinished, not as a choice.

If the piece is silent, keep the rule's shape and swap the trigger. Reveals land on named timestamps instead of spoken clauses. The pacing still has to be deliberate. There's just no VO to key it to.

**One breather.** Across the whole film, name exactly one frame as the breather. It's the deliberately calmer, more static beat, or the longest held read. Every other frame keeps developing continuously.

Naming it prevents two failures. The build won't over-animate the one frame that's supposed to let the audience exhale, and it won't under-animate the rest to match it.

**The negative list.** One list of banned visual clichés, stated once. It's a standing filter, not a fresh list per frame. Every frame gets checked against it as it's built:

> no purple-blue AI gradients, no bokeh, no browser chrome, no drop-shadow cards, no infinite loops or randomness

Swap in whatever clichés are wrong for *your* film. The point is naming them before a frame drifts into one.

## Give each frame a job

The direction block covers everything shared. So each frame's own prompt only needs to say what's different about it:

```text theme={null}
[type]        the frame's category      hook · benefit_highlight · social_proof · cta
[persuasion]  the rhetorical device     before/after · numbered enumeration · counterexample · callback + distillation
[beat]        the emotional beat        recognition + tension · aha · resolve + inevitability
[focal]       the one thing the eye lands on
[roles]       what's foreground / supporting / background, assigned explicitly
```

Never skip `persuasion` and `beat`. Without them, a frame is "a scene that shows the stat." With them, it becomes "a scene that proves the stat, and here's how it *feels* to land."

A frame with a named persuasion device and beat gives the build a reason for every choice. A frame with only a visual description gives it none.

## The callback

Introduce a motif early: a shape, a mark, a phrase, a piece of color. Have it return later, denser or fuller, as a deliberate payoff.

Say both halves in the plan — where the motif is planted, and how it changes when it returns.

> A single thin accent dot appears top-right in frame 1 at low weight. In the landing frame, that same dot expands and fills into the full logo lockup — same motif, now complete.

State the return explicitly. Otherwise a rebuild is free to treat the early motif as throwaway texture. The callback only works if the plan says the second appearance is the *same* element, not a new one that resembles it.

## Worked example: a silent 3-frame storyboard

<Tip>
  `storyboard-mini` below is deliberately small and silent: three frames, \~15 seconds, no narration. That makes the whole pattern checkable in one cheap render — arc, direction block, per-frame job, one breather, one callback. Do this before you write a longer, narrated storyboard.
</Tip>

> Storyboard a 3-frame, \~15-second, 1920x1080 piece. Silent — no narration, no VO track. Message: "Fernwell gives you back the hours other tools take." Arc: Hook → Substance → Landing. Audience: small-team operators evaluating a new tool. Mood: tense synth pulse resolving to warm.
>
> Direction for every frame: ground color deep navy `#0b1220`, ink color warm off-white `#f4efe6`. Nothing else gets a hue — emphasis is inversion, scale, or density only. Reveals stage on internal timestamps, since the piece is silent and there's no spoken cue. At each frame's t=0 only its first element is on screen. The rest arrive on the timestamps below. Holds stay fully still, no drift or breathing. No purple-blue AI gradients, no bokeh, no browser chrome, no drop-shadow cards, no infinite loops or randomness.
>
> Frame 1 — Hook (0.0–4.0s), type: hook, persuasion: counterexample, beat: recognition + tension, focal: the headline. At 0.0s: bold ink headline "Most tools slow you down." slams in, centered. At 1.5s: a single thin accent dot (ink color, small, low weight) fades in top-right — the motif, planted quietly. Hold from 3.0–4.0s.
>
> Frame 2 — Substance, **the breather** (4.0–10.0s), type: benefit\_highlight, persuasion: numbered enumeration, beat: aha, focal: the stat. This is the one deliberately calmer, more static frame in the piece. Everything else develops continuously. This one mostly holds. At 4.0s: the accent dot from frame 1 carries over, now larger, sitting quietly left-of-center. At 5.0s: a big stat "3.2 hrs / week" fades in beside it, no motion after it lands. Static hold 6.0–10.0s.
>
> Frame 3 — Landing (10.0–15.0s), type: cta, persuasion: callback + distillation, beat: resolve + inevitability, focal: the completed motif. At 10.0s: the accent dot from frames 1–2 expands and fills into the full Fernwell wordmark lockup — same motif, now complete, denser and larger. At 12.0s: tagline "Fernwell. Built for flow." stamps in below it. Hold 13.5–15.0s.

<DocsVideo title="HyperFrames video: Storyboard Mini" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/storyboard-mini.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited — no audio track, exactly as asked.*

## Related

<CardGroup cols={2}>
  <Card title="Anatomy of a one-shot prompt" icon="list-ordered" href="/prompting/anatomy">
    The six-part skeleton a single beat uses — the same discipline, one frame at a time.
  </Card>

  <Card title="Recreating something you saw" icon="film" href="/prompting/recreating-references">
    Transcribing motion frame by frame — the same rigor a storyboard's per-frame timestamps need.
  </Card>

  <Card title="Design systems and brand" icon="palette" href="/prompting/design-systems">
    The two-color discipline and brand tokens a storyboard's direction block draws from.
  </Card>

  <Card title="How a HyperFrames project works" icon="route" href="/concepts">
    `STORYBOARD.md` as a production artifact — where this chapter's plans land, downstream of `BRIEF.md`.
  </Card>
</CardGroup>

<Note>
  **Capstone thread** — the [Level 7 film](/prompting/capstone) stretches this chapter's callback device across its whole runtime. The `<div class="clip">` chip typed in the opening rides the wire through every region. It finally snaps into the render slot as the payoff (cut from the film, below).
</Note>

This is the clause in the [full capstone prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece. It's prompt language you can lift for your own video:

> **The clip card** — the `<div class="clip">` typed in the opening travels the whole journey: it slides onto the wire as a clip chip after being typed, rides ahead of the camera between regions (handing itself off — visible leaving one region and arriving in the next), and is the thing that finally renders at the end. It is the protagonist.

<DocsVideo title="HyperFrames video: Capstone Region Render" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-render.mp4#t=0.1" loop />

*That clause paying off, rendered — the protagonist chip arriving at the render slot after a full minute on the wire.*

*Next: [Editing existing videos](/prompting/editing-existing-videos) — the editor verbs that turn a first render, storyboard or not, into the twenty edits after it.*


## Related topics

- [Product updates](/product-updates.md)
- [Figma integration](/guides/figma.md)
- [Examples](/examples.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.