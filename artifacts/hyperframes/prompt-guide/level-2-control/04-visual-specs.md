> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# High-fidelity looks

> Write a visual spec that names, places, colors, and times every element, so words alone carry a specific look.

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

This is the [specification dial](/prompting/specification-dial)'s third setting,
pushed all the way. Not a word from the [vocabulary](/prompting/vocabulary)
list. Every element of a scene, written out like a designer's spec.

Words alone can carry a specific look, but only when the prompt reads like a
spec. Every element named, positioned, colored, and timed.

## A loose description, then a spec

A loose description leaves the agent room to guess: "dark night scene, mountain,
glowing ring, title fades in." Here is the same scene written as a spec.

> 8-second 1920x1080 title card. Scene, back to front: #0a0e2a night sky with faint grain; an orange radial glow (#ff6a2b core \~150px, falling off to transparent by \~430px) igniting at the mountain peak's right shoulder from 2s, positioned so its upper falloff reaches the wordmark's baseline; over it a huge concentric ring system (5 rings, 1px strokes at 8% white opacity, innermost ring glowing #4a5fd9) centered 40% from the top; a low-poly mountain (6-8 dark navy facets, #141a3d–#1e2650) filling the lower third with its apex left of center, a white road S-curving up its face with a soft glow; thin horizontal cloud streaks (white, 6% opacity) drifting right at two heights; a man's silhouette, pure black, \~90px tall, bottom-right, fading in at 2.5s. At 3.5s "SHOWREEL" — thin geometric sans, \~140px, 0.35em tracking, white at 90% — fades in per letter across the ring center, the glow bleeding up through the letterforms above the peak. Slow 4% push-in across the full 8s. No audio.

<DocsVideo title="HyperFrames video: Spec Showreel" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/spec-showreel.mp4#t=0.1" loop />

*Rendered from the spec above, unedited.*

<Note>
  Two clauses in this spec were **corrected by building it.**

  The first draft listed the scene "back to front," then put the rings before a
  glow it had described as sitting *behind* the rings.

  It also sized that glow at "\~300px." Too small: it can't physically reach the
  wordmark it is supposed to bleed through, given the ring center and mountain
  positions the same sentence pins down.

  Neither error is visible on the page. Both are obvious the moment someone
  renders it. That is the argument for the [validation
  rule](/prompting/iterating#the-gates-cant-tell-you-its-good) this guide runs
  on. A spec dense enough to be useful is dense enough to be internally
  inconsistent, and only a render finds out.
</Note>

## What a spec can't carry

Every element above is a primitive the agent can build directly. Two honest
limits:

* **Organic illustration** — drawn characters, painterly texture. Words
  underdetermine a drawing. Steer to geometric shape language instead ("flat
  rounded-geometric figure, circle head, no facial features"), or generate the
  artwork. See [When to generate artwork](/prompting/generated-artwork).
* **Photographic and live-action content** must be supplied as files. Mention
  the paths explicitly.

## The density contract

A spec tells the builder what each element *is*. A density contract tells it how
full every frame must be.

The [Level 7 film](/prompting/capstone) states the contract once and every
region obeys it. This is the clause in the [full capstone
prompt](/prompting/capstone#the-prompt-word-for-word) that buys it:

> Density: every region fills three roles — one focal element at display scale, at least two supporting elements on their own cues, and the chrome/wire. Asymmetric compositions; display type \~a tenth of frame width; three depth layers with parallax between them \[…]

That's the whole formula, and it's reusable in any prompt: **one focal element,
at least two supporting, plus persistent chrome.** Compose asymmetrically — 60/40,
never one element centered in emptiness. Size display type at roughly a tenth of
the frame width. Use at least three depth layers so parallax can sell the space.

Supporting elements land on their own cues. A frame that fills all three roles
at t=0 is a poster, not a scene.

Ask for the contract explicitly when a build keeps coming back sparse. "Every
scene carries one focal element, two supporting elements on staggered cues, and
the persistent chrome" is a sentence a builder can be held to.

## Two more worked specs

The same density, applied to a product-UI piece and a typographic piece. Both
were one-shot from these exact words.

Where a builder had to make a judgment call on the first pass, the spec below
pins it. That's the editing loop these specs live by: build, see what the words
underdetermined, then tighten the words.

> 6-second 1920x1080. A frosted-glass command palette (640x84px, 20px radius, rgba(255,255,255,0.08) fill, 1px rgba(255,255,255,0.25) border, heavy backdrop blur) centered on a #0b0f1a field with two soft accent glows drifting slowly — #5b6cff upper-left, #22d3a5 lower-right, \~400px, 20% opacity. At 0.4s the palette scales in 0.96→1 settling with back.out(1.2). At 0.8s a grey placeholder "Search commands…" types on; at 2.2s it fades out over 0.2s and the query "render 4k" types in white. At 2.8s three result rows (56px tall, 12px gaps: icon square, label, shortcut chip) cascade in as a detached list below the fixed bar, staggered 0.12s, each rising 12px with back.out(1.4). At 4.2s a 10%-opacity #5b6cff fill sweeps left to right across the first row and its shortcut chip pulses once. Rows and glows keep a barely-visible drift to the end. No audio.

<DocsVideo title="HyperFrames video: Spec Command Palette" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/spec-command-palette.mp4#t=0.1" loop />

*Rendered from the spec above, unedited.*

> 7-second 1920x1080. Off-black #101014 field with fine static film grain at 4%. The word "PRECISION" in \~220px heavy condensed caps (a heavy system face condensed with scaleX 0.82), white, 0.02em tracking, centered: its letters assemble from alternating top/bottom 40px offsets with power3.out and a 0.05s stagger, starting 0.3s. At 1.8s a 2px hairline rule draws left-to-right beneath the word, 60% of its width, centered. At 2.4s a 40px tabular-mono counter fades in below and ticks 99.999 → 00.001 mm over 2.2s with expo.out deceleration. At 5.2s the whole lockup eases to 1.03 scale over 0.5s while the word cools from white to #d8d8de, then settles into a slow ±1% breathing idle to the end. No audio.

<DocsVideo title="HyperFrames video: Spec Precision Type" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/spec-precision-type.mp4#t=0.1" loop />

*Rendered from the spec above, unedited.*

*Next: [Verified example prompts](/prompting/examples) — the level's gallery,
read with the vocabulary you now have.*

## Related topics

* [The specification dial](/prompting/specification-dial) — the three settings this page sits at the top of
* [Vocabulary that changes output](/prompting/vocabulary) — the single words a full spec replaces
* [When to generate artwork](/prompting/generated-artwork) — for the looks words underdetermine
* [Iterating](/prompting/iterating) — the render-and-check loop a dense spec needs
* [Verified example prompts](/prompting/examples) — more prompts at this density


## Related topics

- [Vocabulary that changes output](/prompting/vocabulary.md)
- [Rendering and output](/prompting/rendering-and-output.md)
- [Anamorphic Streak Flare](/catalog/blocks/vfx-anamorphic-flare.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.