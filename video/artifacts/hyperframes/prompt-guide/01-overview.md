> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Prompt Guide

> How to prompt AI agents to author HyperFrames videos — setup, the two prompt shapes, and the map of this guide.

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

<DocsVideo title="HyperFrames video: Capstone Timeline Default" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-timeline-default-v2.mp4#t=0.1" loop />

*By the end of this guide, you can build this with a prompt.*

HyperFrames is built for AI agents — compositions are plain HTML, the CLI is non-interactive, and the framework ships [skills](https://github.com/vercel-labs/skills) that teach agents the patterns docs alone don't cover. This guide shows how to prompt agents effectively once skills are installed — the vocabulary that changes output, the iteration patterns that save time, and the rules that prevent breakage.

<Note>
  **Before you prompt**, have three things in place: the skills installed (below), a scaffolded project (`npx hyperframes init my-video`), and the live preview running (`npx hyperframes preview`) so you can judge each render the moment it lands. Prompting without the preview open turns every iteration into a blind guess.
</Note>

## The level ladder

The guide is one arc, novice to advanced. Each level is what you can do once you've read it — read them in order, or jump straight to whichever gap matches where you are:

| Level | What you can do after it |
| - | - |
| **1 — [Your first video](/prompting/product-launch)** | Get a finished video from one prompt — the workflow fills the gaps (palette, pacing, structure) for you. |
| **2 — [Control](/prompting/anatomy)** | Name the parts yourself: route, spec, beats, copy, technique, negatives — the skeleton that removes the decisions agents get wrong. |
| **3 — [Life](/prompting/motion)** | Motion and transitions that read premium instead of like a slideshow. |
| **4 — [Substance](/prompting/code-blocks)** | Add real capabilities: code animation, data-viz, overlays, captions, generated artwork, VFX, 3D. |
| **5 — [Voice & sound](/prompting/media-and-audio)** | Narration, music, and any footage you supply, scored and mixed correctly. |
| **6 — [Scale](/prompting/design-systems)** | Design systems, variables, storyboards, editing, iterating, matching references, and export — a video as a system, not a one-off. |
| **7 — [Capstone](/prompting/capstone)** | Everything above, composed into one real prompt. Each chapter on the way up shows its own region of this film cut out in isolation; the capstone prompt is the glue that binds them into one continuous camera journey, rendered twice from one template. |

## One-time setup

Install the skills in your project (or globally for your agent):

```bash theme={null}
npx skills add heygen-com/hyperframes
```

The installer shows a picker. Select the **core skills** below — every project needs them. In Claude Code, restart the session after installing; the skills register as **slash commands**. Start at `/hyperframes`: it orients you to the whole surface and routes "make me a video" requests to the right workflow.

**Core skills — install all of these**

| Slash command | What it loads |
| - | - |
| `/hyperframes` | **Read first.** The entry skill — capability map + video router; sends "make me a video" intent to the right workflow |
| `/hyperframes-core` | Composition contract — HTML structure, `data-*` attributes, clips, tracks |
| `/hyperframes-animation` | All animation — motion rules, scene blueprints, transitions, and the runtime adapters (GSAP, Lottie, Three.js, Anime.js, CSS, WAAPI, TypeGPU) |
| `/hyperframes-creative` | Creative direction — design spec, palettes, typography, narration, beats |
| `/hyperframes-cli` | Dev-loop CLI — `init`, `lint`, `check`, `preview`, `render`, `doctor` |
| `/media-use` | Media OS — TTS voiceover (`tts`), `transcribe`, `remove-background`, plus BGM / SFX / image resolution (a host app's own music and sound tools come first) |
| `/hyperframes-registry` | Search the catalog before hand-building a look; install via `hyperframes add` |
| `/hyperframes-keyframes` | Seek-safe keyframe authoring across runtimes, plus `hyperframes keyframes` diagnostics |
| `/general-video` | The general authoring workflow — multi-scene pieces, reels, montages, remixes, and the home of **companion mode**; the fallback when no workflow below fits |

**Optional workflows — add the ones that match your inputs** (`/hyperframes` routes to whichever you've installed)

| Slash command | Input → output |
| - | - |
| `/product-launch-video` | Any website URL / brief / script → launch or promo video, or a site tour / showcase |
| `/faceless-explainer` | Arbitrary text (no URL, no footage) → faceless explainer — every visual invented (typography, diagrams, data-viz) |
| `/pr-to-video` | A GitHub PR → code-change explainer |
| `/embedded-captions` | An existing talking-head video → the same footage with captions / subtitles |
| `/talking-head-recut` | An existing talking-head video → footage packaged with transcript-synced graphic overlays (kinetic titles, lower-thirds, PiP) |
| `/motion-graphics` | A logo / stat / tweet / brief → a short (\~10s) unnarrated motion graphic (kinetic type, count-up, logo sting) — MP4 or transparent overlay |
| `/music-to-video` | A music track — a file, a video's audio, or one generated from a mood brief → beat-synced video (lyric / slideshow / kinetic promo); your images optional, cut on the beat |
| `/slideshow` | A deck outline or slides → navigable presentation with presenter mode (not a rendered MP4) |
| `/remotion-to-hyperframes` | Port an existing Remotion (React) composition to HyperFrames HTML |
| `/figma` | A Figma file / frame / URL → imported assets, brand tokens, and reconstructed motion |

<Tip>
  To skip the picker and install everything (core + every workflow) in one shot, run `npx hyperframes skills`. And start HyperFrames prompts with `/hyperframes` (or invoke the skill another way for non-Claude agents) — it loads the routing + composition context explicitly so the agent picks the right workflow and gets the rules right the first time.
</Tip>

## Claude Design

Claude Design uses a different setup. Download [`claude-design-hyperframes.md`](https://github.com/heygen-com/hyperframes/blob/main/docs/guides/claude-design-hyperframes.md) from GitHub (click the ↓ button), then **attach it to your chat** (don't paste the URL — file attachments produce better output):

```text theme={null}
Use the attached skill. 25-second LinkedIn video for my startup.

Problem: Sales teams waste 3 hours/day on manual CRM updates.
Solution: AutoCRM — AI that logs every call, email, and meeting.
Traction: 200+ teams, $1.2M ARR, 18% MoM growth.
CTA: autocrmhq.com
```

Claude Design produces a valid first draft (brand identity, scene content, animations, transitions). Download the ZIP and refine in any AI coding agent with `npx hyperframes preview` running. See the [Claude Design guide](/guides/design-tools) for the full workflow.

## The two prompt shapes

Most successful HyperFrames prompts fall into one of two shapes.

**Cold start — describe the video.** You tell the agent what you want from scratch — best for greenfield work where you already have the creative direction in your head.

> Using `/hyperframes`, create a 10-second product intro with a fade-in title over a dark background and subtle background music.

Cold-start prompts work best when you specify **duration** ("10 seconds", "5 scenes of 3s each"), **aspect ratio** ("16:9", "9:16 vertical" — defaults to 1920x1080 otherwise), **mood / style** ("minimal Swiss grid", "high-energy social"), and **key elements** (title, lower third, captions, music).

**Warm start — turn context into a video.** You give the agent something to work with — a URL, a doc, a CSV, a transcript — and ask it to synthesize that into a video. This is where HyperFrames shines because the agent does the research/summarization step *and* the production step in one flow.

> Take a look at this GitHub repo [https://github.com/heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) and explain its uses and architecture to me using `/hyperframes`.

> Turn this CSV into an animated bar chart race using `/hyperframes`.

Warm-start prompts produce richer, more grounded videos because the agent is writing about *something specific* instead of inventing copy.

The four prompts above illustrate shape, not results — every prompt in this guide that ships with an embedded render was run exactly as written, and the gallery of those lives in [Verified examples](/prompting/examples).

## The interview: what the agent asks first

Either shape starts a short interview before anything is built. This isn't the agent stalling — it's the intent layer turning "make me a video" into a confirmed brief, so the build never has to guess the things you'd have corrected afterward. The agent confirms the route, then asks that workflow's must-have questions (recommended answer first, so most are one-word confirmations). When the selected workflow supports both run shapes, it then closes with two questions that shape the run itself:

| Question | Your options |
| - | - |
| **Storyboard?** | `yes` — review the plan in chat, stills on a board (`boards/storyboard.html`), and the build pass by pass (recommended past a couple of scenes) · `no` — one finished video from the confirmed brief |
| **Automation or companion?** | `automation` — the matched workflow's pipeline executes the brief end to end · `companion` — build it together in `/general-video` with every HyperFrames capability on the table |

The two are independent — all four combinations are valid, and a companion run goes through the same review passes when you said yes to the storyboard. Four routes skip both questions because neither has anything to add: `/motion-graphics` (the piece is seconds long), `/slideshow` (the deliverable is a navigable deck, not a rendered video), and `/embedded-captions` and `/talking-head-recut` (the footage is untouched, so there's no storyboard to review).

In a hurry, skip the whole conversation by saying so:

> Just build it — don't ask me anything.

That locks `automation` with no storyboard wherever those apply, and every question the agent would have asked becomes a stated default in its heads-up instead.

Everything the interview settles is written to **`BRIEF.md`** in the project root — the brief is the artifact, not the chat. A later session (or a different agent) resumes from that file and asks nothing again; to change an answer, edit `BRIEF.md` rather than re-explaining yourself in the prompt.

## Recommended workflow

1. `npx hyperframes init my-video` — scaffold a project (skills install automatically)
2. Open the project in Claude Code (or Cursor / Codex)
3. Prompt with `/hyperframes` and one of the shapes above
4. `npx hyperframes preview` — watch in the browser as the agent edits
5. Iterate with small targeted prompts
6. `npx hyperframes lint && npx hyperframes check` — the gate: structure, runtime errors, layout collisions, motion, and contrast. Both must pass before you render
7. `npx hyperframes render --output final.mp4` when you're happy

`check` is the step people skip and regret. It runs the composition in a headless browser and reports what a still frame can't tell you — an element overflowing its region, two text blocks colliding, a runtime error that only fires mid-timeline, contrast below WCAG AA. It is fast and it is not optional: a render that took ten minutes will happily contain a defect `check` would have named in seconds.

## What a prompt buys you

Three prompts from this guide and their unedited renders — one workflow warm start, one registry-block piece, one dense freeform spec:

> /product-launch-video Make a 45-second 1920x1080 launch video for [https://linear.app](https://linear.app). Energetic but minimal, use the site's own palette and screenshots. Structure: hook stating the problem, 3 feature beats with UI captures and one-line captions, end card with logo + "Try it free". Female TTS voice, confident tone, subtle electronic BGM under -18dB.

<DocsVideo title="HyperFrames video: Example Product Launch" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-product-launch-v2.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

> /motion-graphics 6-second 1920x1080 video, dark navy background. Beat 1 (0-1s): label "ARR" fades up small, top-center. Beat 2 (1-4s): a giant number counts up to \$4.2M with an odometer roll, easing out as it lands. Beat 3 (4-6s): "+312% YoY" stamps in below in green, then everything settles into a gentle ambient idle. Use the `apple-money-count` registry block as base. No narration.

<DocsVideo title="HyperFrames video: Example Stat Countup" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-stat-countup.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

And at the far end of the [specification dial](/prompting/specification-dial), a full visual+motion spec one-shots a broadcast-style animated globe — see [Recreating something you saw](/prompting/recreating-references) for the spec:

<DocsVideo title="HyperFrames video: Recreate Globe Oneshot" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/recreate-globe-oneshot-v2.mp4#t=0.1" loop />

*One-shot render from the distilled spec, no iteration.*

## Explore the guide

<CardGroup cols={2}>
  <Card title="Prompt anatomy" href="/prompting/anatomy">The six-part skeleton every one-shot prompt shares</Card>
  <Card title="Verified examples" href="/prompting/examples">Copy-paste prompts, each one-shots a finished video</Card>
  <Card title="The specification dial" href="/prompting/specification-dial">How much to specify, and what density buys</Card>
  <Card title="Vocabulary" href="/prompting/vocabulary">Words that map to specific framework settings</Card>
  <Card title="Premium motion" href="/prompting/motion">The eight-rule grammar that keeps video from feeling cheap</Card>
  <Card title="Recreating references" href="/prompting/recreating-references">Match something you saw, from text alone</Card>
  <Card title="Capstone" href="/prompting/capstone">The film above, dissected frame by frame</Card>
</CardGroup>

*Next: [Your first video](/prompting/product-launch) — one URL, one prompt, a finished launch video.*


## Related topics

- [Product launch videos](/prompting/product-launch.md)
- [Changelog](/changelog.md)
- [Verified example prompts](/prompting/examples.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.