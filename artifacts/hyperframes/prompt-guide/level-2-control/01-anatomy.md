> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Anatomy of a one-shot prompt

> The six-part skeleton — route, spec, beats, copy, technique, negatives — that removes the decisions agents most often get wrong.

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

Your Level 1 prompts worked because the workflow filled the gaps for you — the palette, the pacing, the structure. This is Level 2: the skeleton is how you take that control yourself.

The [copy-paste examples](/prompting/examples) share one skeleton. Each part removes a decision agents most often get wrong on a first try:

```text theme={null}
[route]      /motion-graphics
[spec]       8-second 1920x1080 video.
[beats]      Beat 1 (0-4s): ...  Beat 2 (4-5s): ...  Beat 3 (5-8s): ...
[copy]       the exact on-screen text, quoted
[technique]  Adapt the `code-typing` and `vfx-shatter` registry blocks.
[negatives]  No narration, no image or media files.
```

* **Route** with a slash command — it loads the right workflow and the framework rules.
* **Spec** duration and resolution up front. Defaults are 1920x1080 at 30fps.
* **Beats** get timestamps. Include pacing instructions ("then hold on the blinking cursor") — agents skip breathing room unless told.
* **Copy** is quoted exactly, with `/` for line breaks. Unquoted copy gets paraphrased.
* **Technique**: name registry blocks exactly as they appear in the [catalog](/catalog/blocks/data-chart) — they're adapted starting points, not drop-ins (blocks ship with demo content the agent rewrites to your beat, so naming one pins the *technique*). Pin a technique wherever the default choice can fail (see [the specification dial](/prompting/specification-dial)).
* **Negatives** close the gaps: "no narration" is not "silent" — if you want no sound at all, say "no audio". Avoid ambiguous phrases like "no external assets" (CDN-loaded runtimes are normal; say "no image or media files" if that's what you mean).

Assembled:

> /motion-graphics Make an 8-second 1920x1080 video. Beat 1 (0-4s): dark macOS terminal types "npx skills add heygen-com/hyperframes" character by character, then hold on the blinking cursor. Beat 2 (4-5s): the terminal shatters into fragments. Beat 3 (5-8s): bold white kinetic text on black slams in word by word, snappy: "YOU JUST MADE THIS / WITH HYPERFRAMES." Adapt the `code-typing` and `vfx-shatter` registry blocks; hand-author the kinetic text. No narration, no image or media files.

<DocsVideo title="HyperFrames video: Validate Anatomy Terminal" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-anatomy-terminal.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

<Note>
  The skeleton isn't just prompting style — the framework enforces a version of it on itself. Since the composition-structure mandate (`0aaac7aa3`, PR #2599), a `hyperframes feedback` report on a visual defect requires a `COMPOSITION_STRUCTURE:` block — element census, attribute presence, timeline shape — auto-filled from the composition's own HTML; the CLI soft-warns (never blocks) when it's missing. Same idea as the six parts above: name the shape explicitly, and both you and the framework reason about it faster.
</Note>

## The beat formula

The skeleton above structures the *ask*. Inside each beat, describe the *content* with the same five slots every time:

```text theme={null}
[element]   what's on screen        a giant number · the tweet card · "SHOWREEL"
[motion]    what it does            counts up with an odometer roll · slides up · fades in per letter
[layout]    where it sits           top-center · filling the lower half · bottom-right
[style]     how it looks            dark navy, green accent · 8-bit pixel · thin geometric sans
[timing]    when, inside the beat   at 1s · over 3s, easing out as it lands · staggered 0.1s apart
```

One sentence per element, slots in any order: *"a giant number **(element)** counts up to \$4.2M with an odometer roll **(motion)**, easing out as it lands **(timing)**, centered **(layout)** in green on dark navy **(style)**."* Elements you don't describe, the agent designs — which is fine when you trust its taste and a drift risk when you don't (see [the specification dial](/prompting/specification-dial)).

<Tip>
  Beat-timestamped prompting — `Beat 2 (4-5s): ...` — is HyperFrames' native language. Diffusion video models bolt time segmentation on top of a single clip; here every beat maps directly to a timed clip in the composition, so per-beat descriptions translate losslessly. Use timestamps liberally.
</Tip>

## Common rewrites

The fixes that come up most, as before/after pairs — each exists because of how the engine actually behaves:

**Freezing the hold.** Compositions hold their final state, so a literal "hold" renders a frozen frame — the single biggest cheap-motion tell.

* ❌ `then everything holds motionless to the end`
* ✅ `then everything settles into a gentle ambient idle (breathing scale, slow drift)`

**A duration with no tail.** The subtler version of the same mistake: state a runtime longer than the beats you describe and the leftover seconds become a dead hold by default. Validating this guide's chart example turned up a 12-second ask carrying about five seconds of described content — the builder had to invent the remaining seven. Either shorten the ask to the content, or say what the tail does.

* ❌ `12-second video. [five seconds of beats]`
* ✅ `12-second video. [beats] … then hold ~5s on the finished chart with the leader pulsing once and a slow ambient drift`

**Simultaneity collisions.** Two things "at 4s" overlap for a few frames; the renderer does exactly what you wrote.

* ❌ `at 4s the counter fades out and READY stamps in`
* ✅ `the counter fades out fully by 4.2s; at 4.2s READY stamps in`

**Vague negatives.** "No external assets" is ambiguous — CDN-loaded runtimes are normal infrastructure.

* ❌ `no external assets`
* ✅ `no image or media files`

**Prose where copy belongs.** Unquoted text gets paraphrased; quoted text renders verbatim.

* ❌ `show a tagline about shipping faster`
* ✅ `tagline: "Ship faster."`

**Format-blind numbers.** An odometer needs fixed digit columns — "counts $0 → $4.2M" forces an awkward "\$0.0M" start.

* ❌ `counts from $0 to $4.2M`
* ✅ `counts up to $4.2M`

## The framework's own vocabulary

The skeleton above is how you ask. This is what the agent writes, and it's worth recognizing on sight — when you read a composition, review a diff, or get a lint error, these four are the load-bearing pieces:

| In the file | What it means |
| - | - |
| `class="clip"` | Marks a timed section. The framework owns its visibility — never animate a clip's own opacity or `display` to hide it. |
| `data-start` / `data-duration` / `data-track-index` | When the clip begins, how long it runs, and which track it sits on. Two clips on the same track index must not overlap in time. |
| `window.__timelines["<id>"]` | Every GSAP-driven composition registers exactly one paused timeline here, built synchronously at load. The renderer seeks that timeline frame by frame — which is why nothing may depend on wall-clock time or unseeded randomness. Other adapters, including Lottie, CSS animations, and WAAPI, register through their own seekable runtime contracts. |
| Footage with sound | `<video playsinline data-has-audio="true">` — the sound stays on the clip |
| Music / voiceover | separate `<audio>` |

You rarely write these by hand, but naming them in a prompt is legitimate and sometimes necessary — "put the captions on their own track index," "keep it one composition file, one timeline" — and it's the vocabulary every error message uses. The full contract lives in the `/hyperframes-core` skill; the [appendix](/prompting/rules-and-anti-patterns) carries the rules that most often bite.

<Note>
  **Capstone thread** — the [Level 7 film](/prompting/capstone) makes this table its scenery. In the Mount region the timeline wire splits into three track lanes and clip chips seat onto them, tagging themselves with the very attributes above — the framework's own vocabulary, staged as a set. And the whole prompt is this chapter's skeleton at maximum scale: route, spec, beats (its nine regions), copy quoted exactly, technique pinned per region, and a hard negative list.
</Note>

This is the clause in the [full capstone prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece — prompt language you can lift for your own video:

> **Mount (7–14s).** Traveling along the wire: it splits into three parallel track lanes; clip chips slide in along the direction of travel and seat onto the lanes on their spoken cues (audio track chip, video track chip, our protagonist chip among them). Small mono labels (`data-start`, `data-track-index`) tag themselves onto chips as the camera passes. The lanes merge back to one wire as the camera accelerates out.

<DocsVideo title="HyperFrames video: Capstone Region Mount" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-mount.mp4#t=0.1" loop />

*That clause, rendered — the region cut from the finished film.*

*Next: [The specification dial](/prompting/specification-dial) — how much of the skeleton to fill in, and when density stops being optional.*


## Related topics

- [VFX and liquid glass](/prompting/vfx-and-liquid-glass.md)
- [Storyboards](/prompting/storyboards.md)
- [Code animations](/prompting/code-blocks.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.