> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Overlays and lower thirds

> Prompt named lower-third and social-post overlay blocks with timing, copy, and brand tone.

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

Level 1's founder-clip.mp4 got named lower-thirds and card overlays through `/talking-head-recut`, which designs bespoke cards synced to that specific transcript. This chapter is the reverse case: ready-made lower-third and social-overlay blocks you drop into a composition you're building from scratch, no existing footage required — the same vocabulary, pointed at a scene instead of a shot.

## What overlays do and when they trigger

Overlays are timed blocks that sit on top of your footage or scene — a lower third that names a speaker, a broadcast ticker, or a replica social-media card. Because each is a timed clip, prompts trigger this layer when you ask to *add* something *at* a moment: "add a lower third at 0:03 with the name and title," "show an animated tweet during the intro," "put a Spotify now-playing card in the corner." Give the timestamp, the copy, and the tone; the agent places the block on a track above the footage.

Two groups:

* **[Lower thirds](/catalog/blocks/lt-clean-bar)** — name/title identifiers for speakers, interviews, podcasts, and news.
* **[Social overlays](/catalog/blocks/x-post)** — animated replicas of platform UI (posts, cards, notifications, follow prompts).

## Brand tone → lower third

Lower thirds split into **cards** (a filled shape behind the text) and **cardless** (text with a rule or sweep, designed to overlay live footage without boxing it in).

| Tone | Blocks |
| - | - |
| **Minimal / clean / corporate** | [`lt-clean-bar`](/catalog/blocks/lt-clean-bar), [`lt-soft-pill`](/catalog/blocks/lt-soft-pill) |
| **High-energy / podcast / bold** | [`lt-bold-block`](/catalog/blocks/lt-bold-block), [`lt-color-block`](/catalog/blocks/lt-color-block) |
| **Cardless over footage** (interview, talking head) | [`lt-accent-underline`](/catalog/blocks/lt-accent-underline), [`lt-kicker-name`](/catalog/blocks/lt-kicker-name), [`lt-mask-reveal`](/catalog/blocks/lt-mask-reveal), [`lt-side-rule`](/catalog/blocks/lt-side-rule) |
| **Card over bright footage** | [`lt-dark-card`](/catalog/blocks/lt-dark-card) |
| **Broadcast / news** | [`lower-third-bild`](/catalog/blocks/lower-third-bild), [`news-ticker`](/catalog/blocks/news-ticker) |
| **Two-part wipe (name + role)** | [`lt-stack-bars`](/catalog/blocks/lt-stack-bars) |

<Tip>
  Over live footage, prefer a **cardless** lower third — they're text-shadowed for legibility without a box that fights the shot. Use a **card** ([`lt-dark-card`](/catalog/blocks/lt-dark-card) charcoal for bright scenes) when the background is too busy for cardless text to read.
</Tip>

## Use → social overlay

Each social overlay is a self-contained animated card with editable placeholder content.

| You want | Block |
| - | - |
| An animated tweet / X post with engagement metrics | [`x-post`](/catalog/blocks/x-post) |
| A Reddit post card with upvotes and comments | [`reddit-post`](/catalog/blocks/reddit-post) |
| A Spotify now-playing card with album art and progress | [`spotify-card`](/catalog/blocks/spotify-card) |
| A macOS notification banner | [`macos-notification`](/catalog/blocks/macos-notification) |
| An Instagram follow prompt | [`instagram-follow`](/catalog/blocks/instagram-follow) |
| A TikTok follow prompt | [`tiktok-follow`](/catalog/blocks/tiktok-follow) |
| A YouTube subscribe lower third | [`yt-lower-third`](/catalog/blocks/yt-lower-third) |

## Example prompts

Quote the exact copy — unquoted names and titles get paraphrased (see [anatomy](/prompting/anatomy)).

> Add a lower third at 0:03 for 5 seconds, on a track above the footage, with [`lt-clean-bar`](/catalog/blocks/lt-clean-bar). Name: "Dana Ríos". Title: "Head of Design".

<DocsVideo title="HyperFrames video: Validate Lower Third" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-lower-third.mp4#t=0.1" loop />

*Rendered from the prompt above over stand-in footage, unedited.*

<Note>
  Give a lower third at least the block's own timeline length (most run \~5 seconds including their designed exit) — a shorter window hard-cuts the block before its settle-out animation plays.
</Note>

> Podcast clip. Bring in [`lt-bold-block`](/catalog/blocks/lt-bold-block) when the guest starts talking, holding 5 seconds — name "MARCUS LEE", tag "GUEST" — brand accent #FF5A1F.

> During the intro, show an [`x-post`](/catalog/blocks/x-post) card with the quote "we shipped it in a weekend" and 12.4K likes, then slide it out before the demo.

<DocsVideo title="HyperFrames video: Overlay Xpost" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/overlay-xpost.mp4#t=0.1" loop />

*Rendered from the prompt above over stand-in scenes, unedited — the card's built-in like-tap ticks 12.4K → 12.5K.*

> /motion-graphics Transparent overlay only — a [`spotify-card`](/catalog/blocks/spotify-card) now-playing widget animating in, bottom-left. Export as transparent WebM so I can drop it over footage in my editor.

<DocsVideo title="HyperFrames video: Overlay Spotify Preview" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/overlay-spotify-preview.mp4#t=0.1" portrait loop />

*MP4 preview of the transparent WebM over a checkerboard — the delivered file carries real VP9 alpha (verified via ALPHA\_MODE + alphaextract).*

## Knobs

* **Timing.** "at 0:03," "for 4 seconds," "slide it out before the demo" set the block's start and duration — an overlay is a timed clip, so it needs both.
* **Copy.** Quote every editable field: name, title, handle, headline, metrics, ticker text. The blocks ship with placeholder content you replace.
* **Track placement.** Overlays go on a track *above* the footage so they composite on top; say "over the footage" if you're layering onto an existing clip.
* **Brand accent.** Give a hex or brand color — most lower thirds carry an accent bar, tab, or block that takes it.
* **Card vs cardless.** State it when it matters, or let the tone table decide.
* **Transparent output.** For use in an external NLE, render the overlay on its own as a transparent WebM — see [rendering and output](/prompting/rendering-and-output).

## Failure modes

**Don't leave the copy unquoted.** Unquoted names and titles get paraphrased; quoted text renders verbatim.

* ❌ `add a lower third with the speaker's name and role`
* ✅ `lt-clean-bar — name: "Dana Ríos", title: "Head of Design"`

**Don't omit the timestamp.** An overlay is a timed clip; without a start (and ideally a duration) the agent has to guess when it appears and how long it holds.

* ❌ `put a lower third somewhere in the intro`
* ✅ `lower third at 0:03, holding 4 seconds`

**Don't let the overlay render behind the footage.** It has to sit on a track above the clip, or the video covers it.

* ❌ `add the tweet card to the video` (ambiguous layering)
* ✅ `x-post card on a track above the footage, top-right`

**Don't over-spec real account data.** These are stylized replicas with editable placeholders — provide the copy you want shown, not a live URL to scrape.

* ❌ `pull my actual Spotify page`
* ✅ `spotify-card: track "Midnight City", artist "M83"`

**Don't invent overlay names.** Only the blocks in the [Social Overlays](/catalog/blocks/x-post) and [Lower Thirds](/catalog/blocks/lt-clean-bar) groups exist.

* ❌ `add a linkedin-post overlay`
* ✅ pick a real block, or describe the card and let the agent build a custom one in a freeform composition

<Note>
  **Capstone thread** — the [Level 7 film](/prompting/capstone)'s Material region docks a designed lower-third chip that renders *behind* the matted-out subject (cut from the film, below).
</Note>

This is the clause in the [full capstone prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece — prompt language you can lift for your own video:

> \[…] as the camera arrives and BEFORE the person speaks, the framework mattes the footage — **the background peels away via background removal**, sliding off along the travel direction and leaving the cutout standing alone on the brand ground. \[…] A designed lower-third chip renders behind the subject.

<DocsVideo title="HyperFrames video: Capstone Region Material" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-material.mp4#t=0.1" loop />

*That clause, rendered — the region cut from the finished film.*

*Next: [Caption styles](/prompting/captions-catalog) — the same timed-block pattern, tuned to on-screen text instead of name cards and social replicas.*


## Related topics

- [Capstone — every technique, one journey](/prompting/capstone.md)
- [Data and maps](/prompting/data-and-maps.md)
- [Lower Third — Accent Underline](/catalog/blocks/lt-accent-underline.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.