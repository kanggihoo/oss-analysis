> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Product launch videos

> What to say to turn a product URL, a script, or a brief into a launch or promo video — and when to reach for a site tour instead.

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

This is Level 1 of the Prompt Guide: a run of one-prompt rides, each handing a workflow a single ask and getting a finished video back. You don't need any technique yet — one sentence describing your product, aimed at the right workflow, is already enough for a first draft.

## Your first win

One prompt to [`/product-launch-video`](/prompting/overview), aimed at a live URL, is enough for a finished launch video — no technique required yet.

Verified, from the [examples](/prompting/examples) page — a 45-second launch from a live URL:

> /product-launch-video Make a 45-second 1920x1080 launch video for [https://linear.app](https://linear.app). Energetic but minimal, use the site's own palette and screenshots. Structure: hook stating the problem, 3 feature beats with UI captures and one-line captions, end card with logo + "Try it free". Female TTS voice, confident tone, subtle electronic BGM under -18dB.

<DocsVideo title="HyperFrames video: Example Product Launch" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-product-launch-v2.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

Read the [anatomy](/prompting/anatomy) of that skeleton — route, spec, structure, copy, voice, level — then swap in your own product.

## What this makes

A launch or promo that *sells*: SaaS promos, feature reveals, product demos, app and company launches. The [`/product-launch-video`](/prompting/overview) workflow captures the product's site (or takes a pasted script), reads its brand, writes a story, and builds it frame by frame.

**Route it right — the distinction is intent, not input:**

| You want… | Route |
| - | - |
| To market, launch, promote, or reveal a product (the default for any commercial URL) | `/product-launch-video` |
| A video *of* a general site — a portfolio / blog / docs / landing-page tour or showcase, not a sales pitch | `/product-launch-video` too — say *tour* or *showcase* in the brief (see the [website-to-video guide](/guides/product-launch-video)) |

Both route to the same workflow now; what changes is the brief. "Promo for our site" is a launch — sell it. A neutral walkthrough of a docs site is a tour — say so, and the workflow shows the site's own captured screens instead of pitching. Unsure → start at `/hyperframes` and let it route.

## The knobs that matter

What you can already steer from the prompt, before you've learned any technique. Set the ones you care about; leave the rest to the workflow's taste.

| Knob | What to say | Why it matters |
| - | - | - |
| **Capture vs no-capture** | Give a URL to capture the real site; give a script or brief for the no-capture path; give just a brand name to have the agent find the URL | Capture borrows the real palette and screenshots; no-capture invents visuals, so it needs your brand colors named |
| **Palette source** | "use the site's own palette" | The workflow remixes the captured brand tokens onto its frame preset — you get the product's real colors, not a generic theme |
| **Structure** | "hook stating the problem, N feature beats with captions, end card with CTA" | The workflow leads value-before-evidence; naming the beats keeps the hook and CTA from getting dropped |
| **Voice & tone** | "female TTS voice, confident" / "calm male voice" | Voice gender and tone are prompt words; the provider itself is a workflow decision — see the [skill](/prompting/overview) for provider mechanics |
| **BGM level** | "subtle electronic BGM under -18dB" (or "no BGM") | A stated ceiling keeps music under the voice; leave it off entirely for a teaser |
| **Length & destination** | "\~45 seconds", "9:16 for TikTok" | Sweet spot is 30-90s; destination sets the aspect (16:9 embed · 1:1 feed · 9:16 Shorts) |

<Tip>
  Duration and destination are the two cheapest, highest-leverage things to state. Everything else the workflow will choose well if you stay quiet — see [the specification dial](/prompting/specification-dial) for how much to delegate.
</Tip>

## Variants

<AccordionGroup>
  <Accordion title="20-second vertical teaser (9:16)">
    > /product-launch-video Make a \~20-second 1080x1920 teaser for [https://linear.app](https://linear.app). Super minimal, just the hook. Beat 1 (0-4s): the problem in one line, big type. Beat 2 (4-16s): two feature beats, one UI capture each with a three-word caption. Beat 3 (16-20s): logo + "Try it free" end card, then settle into a gentle idle. Use the site's own palette. Female TTS voice, confident; no BGM.

    A teaser trades feature coverage for pace — fewer beats, one idea each. Keep the destination (Shorts / TikTok → 9:16) and let the workflow scale the story to the shorter runtime.
  </Accordion>

  <Accordion title="Pasted script, no capture">
    > /product-launch-video Make a \~20-second 1920x1080 launch video from this script — use it verbatim: "Your CRM is three hours of busywork a day. AutoCRM logs every call, email, and meeting for you. 200 teams already switched. Try it free at autocrmhq.com." No site to capture — invent clean product-y visuals from the script. Male TTS voice, calm and confident; subtle BGM under -18dB.

    With no URL the workflow takes the no-capture path: no screenshots, no site palette to borrow, so name your brand colors and fonts if you have them (or the agent invents a palette). Verbatim scripts set the duration — figure roughly 130 spoken words per minute, so a 30-second video wants a 65–70 word script. Saying "use it verbatim" pre-answers the workflow's keep-or-restructure question.

    <DocsVideo title="HyperFrames video: Variant Launch Script" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/variant-launch-script-v2.mp4#t=0.1" loop />

    *Rendered from this prompt shape with a different, longer script (78 words, fictional dev-tool "Relay"), unedited — it ran 35.5s because the words set the length.*
  </Accordion>

  <Accordion title="Brand name only (agent finds the URL)">
    > /product-launch-video Make a \~45-second 1920x1080 launch video for Linear. Find the official site, capture it, and use its own palette and screenshots. Angle: speed as the whole pitch. End card with logo + "Try it free". Confident female TTS voice, subtle electronic BGM under -18dB.

    Given a name instead of a link, the workflow searches for the official URL, confirms it in one line, then captures — you get the site-grounded result without pasting the link yourself.
  </Accordion>

  <Accordion title="Site tour instead (same workflow, tour brief)">
    > /product-launch-video Make a 30-second 1920x1080 tour of [https://example.com](https://example.com) built from its own screenshots. Calm, editorial pace — show the homepage, two inner pages, and the footer. Full narration, warm male voice. This is a showcase, not a sales pitch.

    Reach for this when the goal is to *show the site*, not sell a product. It builds from captured screenshots and the site's brand assets. A launch or promo — even from the same URL — belongs to `/product-launch-video`.
  </Accordion>
</AccordionGroup>

## Common failure modes

**Hard-timing a verbatim script.** With supplied narration, the real TTS duration sets the length — a hard number forces the agent to cut or pad your words.

* ❌ `a 45-second launch video from this exact script: ...`
* ✅ `a ~45-second launch video from this script: ...`

**Overriding the designed structure.** The workflow builds hook → value → evidence → CTA for a reason; drop the hook and the promo never answers "why should I care?"

* ❌ `skip the intro, just list all six features back to back`
* ✅ `hook stating the problem, then 3 feature beats, then the CTA end card`

**Fighting the art-directed preset.** Each workflow adopts a frame preset and injects transitions; forcing a foreign theme yields a compromise, not your look (see [rules and anti-patterns](/prompting/rules-and-anti-patterns)).

* ❌ `/product-launch-video ... plain white, no transitions between scenes`
* ✅ pick the angle and tone, and let the preset carry the visual system

**Assuming the agent knows your assets.** On the no-capture path there's no site to read; an unnamed logo or color is invented.

* ❌ `use our brand colors`
* ✅ `brand colors #5E6AD2 on off-black; logo at assets/logo.svg`

*Next: [Explainers](/prompting/explainers) — no product, no site, just text turned into a faceless explainer.*


## Related topics

- [Create a product or website video](/guides/product-launch-video.md)
- [Verified example prompts](/prompting/examples.md)
- [Motion graphics](/prompting/motion-graphics.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.