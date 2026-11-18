> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Captions and talking-head footage

> Two ways to dress an existing talking-head clip — readable captions or designed graphic overlays — both leaving the footage itself untouched.

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

The first two rides built a video from nothing and the third built one from a diff. This one starts from footage you already have — a talking-head clip — and adds a layer on top without touching the shot itself.

## Your first win

One prompt to [`/embedded-captions`](/prompting/overview), pointed at an existing clip, is enough for a finished captioned video — no technique required yet.

Captions route by **identity**, not by mode. You pick one look from the catalog; the engine behind it is a lookup detail you never have to name. The default is a clean verbatim rail — `anchor` — with the occasional peak word composited behind the subject.

> /embedded-captions Add captions to ./interview\.mp4. Use the `anchor` identity — clean verbatim rail carrying the spoken words, readable lower-third. Promote the single hardest-hitting word to an embed behind the speaker; highlight one key word in each rail line. Keep the source aspect ratio. Footage stays untouched.

<DocsVideo title="HyperFrames video: Captions Anchor Rail" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/captions-anchor-rail-v2.mp4#t=0.1" loop />

*Rendered from the prompt above on generated avatar footage, unedited — one earned embed behind the speaker, everything else on the rail.*

The rail carries most of the text; an **embed** is the scarce, earned peak — one big word matted behind the subject at the climax, never every line. Embedding the whole transcript is the most common mistake this skill guards against.

## Two things you can add to a talking head

Both workflows take an existing talking-head / interview / podcast clip and add a layer on top. Neither edits the footage — no trims, no recolor, no reframe, no reorder. The clip plays untouched underneath; you're choosing what rides on top of it.

| You want | Route | What it adds |
| - | - | - |
| The spoken words as readable text | `/embedded-captions` | Captions / subtitles — a rail, with earned climax embeds |
| Designed on-screen graphics synced to the talk | `/talking-head-recut` | Overlay cards — titles, lower-thirds, data callouts, quotes, PiP |

If the words themselves need to read, you want captions. If you want a produced look — kinetic titles, a stat callout, a pull-quote card, the speaker shrunk into a corner while a chart fills the frame — you want overlay cards. When it's genuinely both, caption first, then package; they're siblings, not substitutes.

`/embedded-captions` runs locally end to end — it transcribes and mattes the subject itself, no API key — and needs a **single-subject clip**. Multi-speaker clips or hard cuts get split per shot or refused, because the matte is one person.

## Base prompt — overlay cards

> /talking-head-recut Package ./founder-clip.mp4 with designed graphic overlay cards synced to the transcript. 9:16 portrait, warm-paper style. Open with a fullscreen kicker + title hook, drop a lower-third when she names the company, a data callout card counting up the "200+ teams / \$1.2M ARR" stat, and a pull-quote card for the strongest line. Speaker stays full-bleed under the cards; shrink her into a corner PiP while the data card holds. The clip plays untouched underneath.

You describe the *cards* — their content, timing, and how the speaker shares the canvas with them (full-bleed, split, PiP, or glass overlay). The skill designs and writes each card; there's no fixed archetype list, so the overlays follow what the transcript actually says.

## The knobs that matter

What you can already steer from the prompt, before you've learned any technique.

**Identity and tone (captions).** One identity picks the entire look — surface, palette, motion, climax behavior. Route by content: explainer / interview / must-read words → a rail-carrying identity, with `anchor` the conservative default where every word has to read; poetic / social / cinematic → a column-flow identity by register (`editorial`, `cream`, `loud`, `neon`); "炸 / 特效 / VFX" → a themed identity (`ordnance`, `terminal`, `stomp`). Unsure → `anchor`: the words read and the scene stays safe. Don't ask for "Standard vs Cinematic vs Theme" — those are engine names; name the identity.

**Verbatim rail vs climax embed.** The rail is the default and carries most of the text. An embed is a promotion — one peak word matted behind the subject, scarce and spaced (roughly one per beat, never two co-visible, at most one apex). Tell the skill *which* lines earn the embed; leave the rest on the rail.

**Style, layout, and canvas (recut).** Pick a style group (warm-paper / clinical / experimental), a layout (split / stack / pip / overlay), and a canvas ratio; the video frame follows from layout × style. The recommended ratio matches the source, but you choose — 16:9 for desktop / YouTube, 9:16 for Reels / Shorts, 4:5 for feed.

**Keyword highlighting.** On the caption rail, a punch word can carry an inline `emphasis` — an accent-color or active-word pop — without leaving the rail. Ask for "highlight the key word in each line" and it stays readable.

## Variants

<AccordionGroup>
  <Accordion title="Cinematic caption embed (mood over verbatim)">
    > /embedded-captions Cinematic captions on ./poem.mp4 — no rail, hero typography composited behind the speaker, words accumulating as a column. Use the `editorial` identity (lowercase-italic hero). One apex word per thought, air between them. 4:5. Never grade the footage.

    Column-flow identities drop the rail and make everything embed-style — reach for them on poetic / social / "cinematic" asks where mood beats strict readability, never on an explainer where the words must read.
  </Accordion>

  <Accordion title="Bright-scene captions">
    > /embedded-captions Add verbatim captions to ./outdoor-vlog.mp4. It's a bright daylight scene, so use the `ink` identity — near-black type printed onto the surface — not a light-on-bright look that washes out. Keep it a readable rail. 16:9.

    Screen-blend cream looks wash out over bright backdrops (luminance > \~180); `ink` is built for bright surfaces. Match the identity to the scene rather than asking the engine to recolor a look.
  </Accordion>

  <Accordion title="VFX-grade themed captions">
    > /embedded-captions Bring the energy on ./hype-clip.mp4 — I want the captions to hit hard. Use the `ordnance` identity: a stamped verbatim rail with a detonation apex. Rail carries the verbatim; the payoff line is the setpiece. 9:16.

    Themed identities (`ordnance`, `terminal`, `stomp`, `neonsign`, `stardust`, …) are the answer to "make it explode / 特效 / like AE did it". Theme mode is the one place a register-gated reaction beat may touch the frame — applied after the matte composite so subject, text, and plate move as one — but the a-roll is still never graded.
  </Accordion>

  <Accordion title="Landscape data recut">
    > /talking-head-recut Recut ./analyst-interview\.mp4 as a 16:9 explainer with a clinical style. Split layout: speaker on the right, data cards on the left. Cards for each claim — a count-up for the headline number, a swiss-grid comparison for the two options, a terminal-style callout for the technical bit. Auto-pace the card count for a 5-minute clip. Footage untouched.

    Layout (split / stack / pip / overlay) sets how speaker and cards share the canvas; card count auto-infers from duration and information density, with a floor of five so even a short clip has rhythm.
  </Accordion>
</AccordionGroup>

## Failure modes

**Asking for footage edits.** Both skills add a layer and leave the a-roll exactly as shot. Trimming, speeding up, recoloring, reframing, or reordering is NLE editing and out of scope — captions and cards are the only additions.

* ❌ `add captions and trim the dead air at the start, and warm up the color to match my brand`
* ✅ `add captions; leave the footage untouched` — do the trim / grade in an editor first, then bring the finished clip here.

**Embedding every word.** On a talking head the rail is the verbatim default; matting every caption behind the subject buries the words and spends the climax on nothing.

* ❌ `composite every caption behind the speaker for a cinematic look` (on an explainer)
* ✅ `verbatim rail; promote only the two payoff lines to an embed`

**Multi-subject clips.** The caption matte is one person; two speakers or hard cuts flicker or get refused.

* ❌ `caption this two-person podcast in one pass`
* ✅ `split the clip per shot / per speaker first, then caption each` — or use a single-subject cut.

<Tip>
  For the beat-timestamped skeleton these prompts share, see [Prompt anatomy](/prompting/anatomy); for adjectives that map to motion and emphasis settings, [Vocabulary](/prompting/vocabulary). To build a video from scratch instead of dressing existing footage, start at the router in `/hyperframes`.
</Tip>

The workflow this level rides is documented at [Captions and talking head](/guides/captions-and-recuts) — what it takes as input, what it asks you before it builds, and what it returns.

*Next: [Music videos and slideshows](/prompting/music-and-slideshows) — swap footage for a soundtrack, or slides, and let the beat or the deck set the pace.*


## Related topics

- [Add an avatar presenter](/guides/avatar-presenter.md)
- [Code changes and PRs](/prompting/code-and-prs.md)
- [Add captions or repackage talking-head footage](/guides/captions-and-recuts.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.