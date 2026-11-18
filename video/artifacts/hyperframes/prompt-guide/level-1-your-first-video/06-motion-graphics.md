> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Motion graphics

> Short, design-led pieces where motion is the message — kinetic type, a stat hit, a logo sting — and the knobs that decide MP4 versus transparent overlay.

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

Five rides in, five different inputs — a site, plain text, a PR, footage, a track. This last one drops narration and asset input altogether: a short, design-led motion graphic where motion alone carries the message.

## Your first win

One prompt to [`/motion-graphics`](/prompting/overview), with the beats spelled out, is enough for a finished motion graphic — no technique required yet.

The canonical shape: routed, spec'd, beat-timestamped, copy quoted, technique pinned, gaps closed.

> /motion-graphics Make an 8-second 1920x1080 video. Beat 1 (0-4s): dark macOS terminal types "npx skills add heygen-com/hyperframes" character by character, then hold on the blinking cursor. Beat 2 (4-5s): the terminal shatters into fragments. Beat 3 (5-8s): bold white kinetic text on black slams in word by word, snappy: "YOU JUST MADE THIS / WITH HYPERFRAMES." Adapt the `code-typing` and `vfx-shatter` registry blocks; hand-author the kinetic text. No narration, no image or media files.

<DocsVideo title="HyperFrames video: Validate Anatomy Terminal" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-anatomy-terminal.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

## What a motion graphic is

A motion graphic is a short, design-led piece where **motion is the message** — kinetic typography, a stat count-up, a chart hit, a logo sting, a lower-third or social overlay, an animated map, tweet, or headline. It's usually under 10 seconds (up to \~30s), has no narration and no live-action subject, and renders to an MP4 or a transparent overlay.

Route with `/motion-graphics`. The workflow is autonomous by design — at most one clarifying question, then straight through to render. Reach for a different workflow when the piece grows past what "motion is the message" covers:

| If the piece is… | Route instead |
| - | - |
| Longer, multi-scene, or narrated | `/general-video` |
| A narrated video of a website | `/product-launch-video` |
| A topic explainer with a voice-over | `/faceless-explainer` |
| A product promo / launch | `/product-launch-video` |
| Captions on existing footage | `/embedded-captions` |

## The knobs that matter

What you can already steer from the prompt, before you've learned any technique.

**Duration.** Keep it short — motion graphics live under 10 seconds, up to \~30. A 2-second idea stretched to 8 feels slow no matter how it's animated; if the piece genuinely needs multiple scenes or a longer runtime, it's a `/general-video`, not a motion graphic.

**MP4 vs transparent overlay.** The default output is an MP4. Ask for a transparent overlay — a lower-third, a callout, a bug meant to composite over other footage — and the render targets `webm` or `mov` with alpha. Transparency only makes sense when part of the frame is *meant* to be empty. A full-frame design (its own background, edge-to-edge composition) has nothing to be transparent, so asking for a transparent WebM there produces either an opaque file or a broken-looking one. Say "transparent overlay, alpha channel" only for pieces designed to sit on top of something else.

**Registry blocks vs freeform.** Naming a block (`apple-money-count`, `x-post`, `data-chart`, `code-typing`, `us-map` / `world-map`) makes the agent compose reuse-first: install the block, customize in place, hand-author only the gaps. Omit the block and it hand-builds from your description — fine for one-off looks, more drift on the details you didn't pin. Name blocks exactly as they appear in the [catalog](/catalog/blocks/data-chart).

**Easing and motion feel.** The words you use for *how* motion feels — "snappy", "bouncy", "settles with overshoot" — map to specific eases. Spend them; they're cheap precision. See [Vocabulary](/prompting/vocabulary) for the adjective-to-ease table and [Premium motion](/prompting/motion) for the grammar that keeps a piece from reading cheap (nothing fully stops, action overlaps, the camera acts).

## Variants

Each reuses a registry block, so the agent composes rather than hand-building from scratch.

<AccordionGroup>
  <Accordion title="Stat count-up">
    > /motion-graphics 6-second 1920x1080 video, dark navy background. Beat 1 (0-1s): label "ARR" fades up small, top-center. Beat 2 (1-4s): a giant number counts up to \$4.2M with an odometer roll, easing out as it lands. Beat 3 (4-6s): "+312% YoY" stamps in below in green, then everything settles into a gentle ambient idle (subtle breathing scale, slow particle drift). Use the `apple-money-count` registry block as base. No narration.
  </Accordion>

  <Accordion title="Logo sting">
    > /motion-graphics 5-second 1920x1080 logo sting. Beat 1 (0-2s): the word "ACME" assembles from scattered particles. Beat 2 (2-3s): full-frame `swirl-vortex` shader transition. Beat 3 (3-5s): logo lockup + tagline "Ship faster." settles on white, then holds with a subtle ambient idle (slow breathing scale). Use `code-particle-assemble` for the assembly.
  </Accordion>

  <Accordion title="Animated tweet">
    > /motion-graphics 7-second 1080x1350 vertical video. A real tweet card (handle @hyperframes, text "we render video from HTML now. no timeline UI. just code.") slides up over a soft animated gradient, likes counter ticks 0→1.2K, then the card tilts in 3D and a highlight sweeps the second sentence. Settle into a gentle ambient idle on the card at the end. Use the `x-post` and `vfx-liquid-background` registry blocks. No narration, no image or media files.
  </Accordion>

  <Accordion title="Map route">
    > /motion-graphics 8-second 1920x1080 video. Dark world map, a glowing arc animates from San Francisco to Tokyo over 3s, destination pin drops with a pulse, then camera zooms into Tokyo and the label "LATENCY: 89ms" types on. Use the `nyc-paris-flight` registry block as the base pattern, restyle to teal on charcoal. No narration.
  </Accordion>
</AccordionGroup>

## Failure modes

**Transparent output on a full-frame design.** Alpha is for overlay elements, not for pieces that fill the frame. A design with its own background has no transparent region to export.

* ❌ `an 8s full-screen stat count-up on dark navy — export as a transparent WebM`
* ✅ `an 8s stat count-up on dark navy, MP4` — or, for a bug to composite over footage: `just the count-up chip, no background, transparent overlay (webm)`

**Narration on a motion-is-the-message piece.** Motion graphics are unnarrated by definition — the visual carries it. A voice-over means a different workflow.

* ❌ `/motion-graphics a 10s logo sting with a voice-over reading the tagline`
* ✅ `/motion-graphics a 10s logo sting, no narration` — for a spoken track, use `/faceless-explainer` or `/general-video`.

**Stretching a short idea long.** Runtime is a knob, and past \~30s a single motion beat runs out of things to do.

* ❌ `a 45-second kinetic-type piece of one headline`
* ✅ `an 8-second kinetic-type piece of one headline` — or promote it to a multi-scene `/general-video`.

<Tip>
  For the six-part skeleton and the per-beat content formula these prompts share, see [Prompt anatomy](/prompting/anatomy); for the full set of run-verified examples, [Verified examples](/prompting/examples). Unsure whether your ask is a motion graphic at all? Start at the router in `/hyperframes`.
</Tip>

The workflow this level rides is documented at [Motion graphics](/guides/motion-graphics) — what it takes as input, what it asks you before it builds, and what it returns.

*Next: [Prompt anatomy](/prompting/anatomy) — you've been riding workflows through six one-prompt inputs; Level 2 opens the prompt itself.*


## Related topics

- [Create a motion graphic](/guides/motion-graphics.md)
- [Make your first video](/quickstart.md)
- [30 Days of HyperFrames](/thirty-days.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.