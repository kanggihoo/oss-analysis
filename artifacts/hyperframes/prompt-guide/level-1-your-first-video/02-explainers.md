> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Explainers

> What to say to turn an article, notes, or a topic into a faceless explainer — where every visual is invented, not captured.

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

The last page pointed a workflow at a website. This one drops the site. Your
text is the whole input. Every visual is invented, not captured.

## Your first win

Paste your text into one prompt to [`/faceless-explainer`](/prompting/overview).
That is enough for a finished explainer. No site, no footage, no design
decisions yet.

Verified, from the [examples](/prompting/examples) page — a \~60-second vertical
explainer from pasted text:

> /faceless-explainer Turn this into a \~60-second 1080x1920 vertical explainer: \[paste your text]. One idea per scene, big typography, diagrams over stock footage, brand color #FF5533 on off-black. Male TTS voice, calm. Embedded captions, keywords highlighted in the brand color.

<DocsVideo title="HyperFrames video: Example Explainer" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-explainer.mp4#t=0.1" portrait loop />

*Rendered from the prompt above, unedited.*

Note the `~`. When you supply a script, the runtime follows the spoken words. So
ask for *about* a minute, not exactly one. See the
[anatomy](/prompting/anatomy) for the rest of the skeleton.

## What this makes

A faceless explainer. Your text becomes a narrated video — an article, notes, a
topic, a brief. Every visual is invented per scene: typography, abstract
graphics, diagrams, data-viz.

The [`/faceless-explainer`](/prompting/overview) workflow does four things. It
picks a design system. It reshapes your text into a teaching story. It generates
its own TTS narration. Then it builds the video frame by frame.

**Faceless means there is nothing to capture.** No site, no footage, no asset
inventory. The visuals are designed downstream.

Pick a different workflow when you do have something to show:

* A product to sell → [`/product-launch-video`](/prompting/product-launch)
* A real site to show → [`/product-launch-video`](/prompting/product-launch)
  with a tour brief
* A GitHub PR → [`/pr-to-video`](/prompting/code-and-prs)
* Unsure → start at `/hyperframes`

## The knobs that matter

You can steer all of these from the prompt, before you have learned any
technique.

| Knob | What to say | Why it matters |
| - | - | - |
| **Verbatim vs summarized** | "use my wording verbatim" or "restructure it freely" | The workflow asks once. Verbatim keeps your voice but locks the word count. Summarized lets it cut and reorder for pace. |
| **Duration** | "\~60 seconds", never "60 seconds" | With a script, the narration sets the real length. A hard number forces the agent to trim or pad the words. |
| **Scene density** | "one idea per scene" | A faceless scene has one invented focal to animate. Two ideas leave nothing to build the motion around. It reads as a text dump. |
| **Angle** | "concept" / "how-to" / "listicle" / "story" | The angle decides the story shape. The workflow reshapes your text into it instead of reading your paragraphs in order. |
| **Caption style** | "embedded captions, keywords highlighted in the accent color" | Captions are burned in. Naming the highlight color ties them to your palette instead of a default pill. |
| **Palette** | "brand color #FF5533 on off-black" | There is no site to borrow from, so the preset supplies a full palette. A named accent and ground personalize it. |
| **Voice** | "male TTS voice, calm" / "warm female voice" | Gender and tone are prompt words. The provider is a workflow decision. |

<Tip>
  Scene density is the single biggest quality lever here. "One idea per scene"
  turns a dense paragraph into a paced sequence. The workflow reorders and
  compresses your text to hit it. That is what makes an explainer teach instead
  of recite.
</Tip>

## Variants

<AccordionGroup>
  <Accordion title="30-second landscape topic explainer (16:9)">
    > /faceless-explainer Make a \~30-second 1920x1080 explainer on how HTTPS keeps a request private, for a non-technical audience — the takeaway: your data is sealed before it leaves the browser. Concept angle: one idea per scene, big geometric type, a simple lock-and-key diagram as the centerpiece (swap the metaphor with the topic). Near-black ink on off-white with a deep-blue accent. Female TTS voice, warm and clear. Embedded captions, key terms highlighted in the accent color.

    Shorter runtime, landscape for YouTube or an embed. Fewer scenes means the
    topic has to compress. Naming the takeaway tells the workflow what to keep.

    <DocsVideo title="HyperFrames video: Variant Explainer Landscape" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/variant-explainer-landscape.mp4#t=0.1" loop />

    *Rendered from this prompt with the topic swapped to HTTP caching (cache diagram as the metaphor), unedited — 26s, because the narration sets the length.*
  </Accordion>

  <Accordion title="Listicle">
    > /faceless-explainer Make a \~45-second 1080x1920 listicle: "5 habits of fast-shipping teams". Listicle angle — one habit per scene, each with a big number and a one-line label, escalating energy toward #1. Off-black with a lime accent. Male TTS voice, upbeat. Embedded captions, the habit label highlighted each scene.

    The listicle angle gives each item its own scene. Every scene reuses the same
    number-and-label shape. The result reads as a countdown, not a wall of
    points.
  </Accordion>

  <Accordion title="How-to with diagrams">
    > /faceless-explainer Make a \~60-second 1920x1080 how-to on setting up a CI pipeline, for developers. How-to angle: one step per scene, each built around a simple node-and-arrow diagram that draws on as the narration explains it. Charcoal with a teal accent. Calm male TTS voice. Embedded captions, the step name highlighted.

    A how-to leans on diagrams as the load-bearing visual. Describe the diagram
    *shape* per step — "node-and-arrow", or "a pipeline that fills left to
    right". Let the workflow invent the specifics.
  </Accordion>
</AccordionGroup>

## Common failure modes

**"60 seconds" instead of "\~60 seconds".** Same rule as on the
[product launch page](/prompting/product-launch#common-failure-modes). It bites
harder here, because the script is the whole video. You cannot know a supplied
script's spoken duration until the TTS renders.

* ❌ `a 60-second explainer from this text: ...`
* ✅ `a ~60-second explainer from this text: ...`

**Cramming ideas into a scene.** Every faceless visual is invented around a
single focal. Overload the scene and there is no clear thing to animate.

* ❌ `explain all five caching layers in one scene`
* ✅ `one idea per scene — one caching layer at a time`

**Asking it to capture or pull real imagery.** There is no capture step. A
faceless explainer invents its visuals.

* ❌ `pull screenshots from the site and explain the feature`
* ✅ that's a site or product video — use
  [`/product-launch-video`](/prompting/product-launch)

**Leaving the look unspecified when you care.** There is no brand to read, so
the preset picks the palette. If you have colors, name them.

* ❌ `make it look on-brand`
* ✅ `brand color #FF5533 on off-black`

The workflow this level rides is documented at [Faceless explainer](/guides/faceless-explainer) — what it takes as input, what it asks you before it builds, and what it returns.

*Next: [Code changes and PRs](/prompting/code-and-prs) — point a workflow at a merged GitHub PR instead of a blank page.*


## Related topics

- [Create a faceless explainer](/guides/faceless-explainer.md)
- [Verified example prompts](/prompting/examples.md)
- [Code changes and PRs](/prompting/code-and-prs.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.