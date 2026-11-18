> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Music videos and slideshows

> Two music- and slide-driven outputs that look alike in a brief but ship differently — a beat-synced MP4 versus a navigable deck — and how to route to the right one.

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

You've dressed footage and turned a PR into a story — now the driving input changes again: a track's own beat, or a deck of slides, sets the pace instead of a script.

## Your first win

One prompt to [`/music-to-video`](/prompting/overview), pointed at a track and some photos, is enough for a finished beat-synced video — no technique required yet.

The verified starting point: photos cut to a track, exported to a square MP4.

> /music-to-video 20-second 1080x1080 video from ./track.mp3 (pick the best 20 seconds of the track) and the 8 photos in ./shots/. Cut on the beat grid, one photo per bar, punch-in on downbeats, `whip-pan` transitions on phrase changes. End on the last photo with "SUMMER '26" in condensed caps. No TTS.

<DocsVideo title="HyperFrames video: Example Music Slideshow" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-music-slideshow-v2.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited.*

Every timing decision here is delegated to the track's own analysis — you describe the *treatment* ("one photo per bar", "punch-in on downbeats"), and the beat grid supplies the *times*.

## Two outputs that a brief blurs together

"Make a slideshow from these photos and this track" and "make a slideshow deck for my pitch" both say *slideshow*, but they produce different things and route to different workflows. Name the output you want up front.

| You want | Route | Output |
| - | - | - |
| Photos / clips cut to a music track, exported as a video | `/music-to-video` | A beat-synced **MP4** with audio |
| A presentation you click through — slides, reveals, speaker notes | `/slideshow` | A **navigable deck**, not an MP4 |

`/music-to-video` turns a **music track** — an audio file, a video to pull audio from, or a track generated from a mood brief — into a beat-synced video. The music drives all pacing; any photos or clips you supply are cut onto the same beat grid, and a complete video needs zero assets (typography carries it otherwise). There is no narration and no website capture.

`/slideshow` authors a HyperFrames deck — discrete slides with fragment reveals, hotspot branching, and a built-in presenter mode with speaker notes. Its output is the **running deck**, served with `hyperframes present`. Do not point `render` at a deck: it resolves only the first scene and emits a silently truncated MP4. If the user didn't explicitly ask for a slideshow, the skill confirms the deck route before authoring — that's a routing decision, not a style preference. One authoring detail worth knowing: fragment reveal times are absolute positions on the deck's master timeline, not per-slide offsets.

## The knobs that matter

What you can already steer from the prompt, before you've learned any technique.

**The beat grid.** `/music-to-video` analyzes the track once into energy phases, onsets, rolls, silences, hard stops, and phrases, then cuts at real musical changes. You steer *how* it cuts, not *when*: "one photo per bar" sets cut density, "punch-in on downbeats" adds the accent, "transitions on phrase changes" reserves the visible moves for structural boundaries. On genuinely rhythmic music the grid is trustworthy and cuts snap to the beat; on calm music the grid is a metronome the analyzer imposed, so the skill paces by phrase and energy instead of hard-cutting — say "let it flow, no hard cuts" if the track is ambient.

**Track section — describe, don't timestamp.** Ask for "the best 20 seconds" or "the verse into the hook" and let the analyzer choose boundaries that land on musical anchors. Hard timestamps ("use 0:32–0:52") cut mid-phrase and fight the grid.

**Asset supply.** Zero assets is valid — typography and templates carry a complete video. Any photos or clips you hand it are woven in *on the same beat grid* (beat-cut or Ken Burns), so more assets means more to cut between, not a different pacing model. Point at a directory ("the 8 photos in ./shots/") and name the end card.

**Deck structure (slideshow).** Fragments (reveal hold-points), hotspots + branch sequences (off-line detail slides), and presenter notes are the deck's structural knobs. Ask for them by name — "reveal the bullets as fragments", "branch to a detail slide from a hotspot", "add speaker notes" — and the island wiring follows.

## Variants

<AccordionGroup>
  <Accordion title="Lyric video">
    > /music-to-video 30-second 1080x1920 lyric video from ./song.mp3 (pick the strongest 30-second section — a verse into the hook). Transcribe the vocals for word timing. Lines rise in one at a time on the beat, big condensed type on a dark grain background; the hook lands with each word punching in on its downbeat. Keyword in each line highlighted in acid green. No photos — typography only. No TTS.

    Word-level timing comes from transcribing the track (or from lyrics you paste, placed on the beat grid). No supplied assets needed — type is the whole video.
  </Accordion>

  <Accordion title="Kinetic promo from a mood brief (no track)">
    > /music-to-video 15-second 1080x1080 kinetic promo. No track supplied — generate one: driving synthwave, high energy. Cut hard on the beat: full-frame word cards ("FASTER", "SHARPER", "SHIP IT") slam in on downbeats, alternating black/white with inverted type, a glitch flash on each phrase change. End on the wordmark "NOVA" holding with a subtle ambient idle. No TTS.

    With no audio supplied, the track is generated from the mood you describe; the beat grid it produces still drives every cut. Fast, high-energy briefs suit this workflow best.
  </Accordion>

  <Accordion title="Presentation deck (slideshow)">
    > /slideshow Build a 5-slide pitch deck, 1920x1080. One idea per slide, each headline a complete-sentence claim (not a label), punchline first. Slide 2 reveals three pain points one at a time as fragments. Slide 3 shows bottom-up market math (accounts × ACV), not a bare "\$40B TAM". Add presenter notes to every slide, and a hotspot on slide 3 that branches to a "sizing methodology" detail slide. I'll present it with `hyperframes present`.

    This produces a clickable deck, not a video. Fragments are reveal hold-points inside a slide; the hotspot branches off the main line and returns on Back. Headlines follow the deck's hard rules — complete-sentence claims, one idea + one visual per slide, font no smaller than a 30pt equivalent.
  </Accordion>
</AccordionGroup>

## Failure modes

**Hard track timestamps.** The whole point of `/music-to-video` is that the track's structure sets the cuts. A literal time window ignores the analyzed beat grid and lands cuts mid-phrase.

* ❌ `use the section from 0:32 to 0:52`
* ✅ `pick the best 20 seconds of the track`

**Expecting an MP4 from `/slideshow`.** A deck is authored as several top-level scenes with no master-root composition, so `render` resolves only the first one and truncates. The supported outputs are the live `present` deck and per-slide snapshots.

* ❌ `/slideshow ... then render it to deck.mp4`
* ✅ `/slideshow ... I'll present it with hyperframes present` — or, if you actually need a rendered video, use `/music-to-video` (beat-synced) or `/general-video`.

**Wrong workflow for the output.** Photos set to music that you'll export and post is `/music-to-video`; a thing you click through live is `/slideshow`. Picking by the word "slideshow" alone builds the wrong deliverable.

<Tip>
  Both prompts here are unnarrated. `/music-to-video` has no TTS by design; if you want a spoken voice-over instead of a music bed, that's a different workflow (see the router in `/hyperframes`). For the six-part skeleton these prompts share, see [Prompt anatomy](/prompting/anatomy); for adjectives that map to eases and transitions, [Vocabulary](/prompting/vocabulary).
</Tip>

<Note>
  **Capstone thread** — the [Level 7 film](/prompting/capstone)'s Rhythm region cuts media cards onto a real analyzed beat grid from `hyperframes beats` — the film's only sanctioned hard cuts, every one on a detected beat while the camera keeps traveling (cut from the film, below).
</Note>

This is the clause in the [full capstone prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece — prompt language you can lift for your own video:

> **Rhythm (45–52s).** The wire becomes a waveform: **resolve the BGM first, run `hyperframes beats` on it, and drive this region on the detected grid** — the waveform pulses and compact media cards (a lyric line, a photo card, a chart flash) snap onto the wire on real analyzed beats while the camera keeps traveling; each snap gets a tick SFX. At least six beat-hits. SANCTIONED SEAM #2: the beat-hits may hard-cut card content ON the beat — the sanctioned exception, because the camera itself never stops moving through them.

<DocsVideo title="HyperFrames video: Capstone Region Rhythm" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-rhythm.mp4#t=0.1" loop />

*That clause, rendered — the region cut from the finished film.*

The workflow this level rides is documented at [Music to video](/guides/music-to-video) — what it takes as input, what it asks you before it builds, and what it returns.

*Next: [Motion graphics](/prompting/motion-graphics) — the shortest one yet, a single motion graphic where motion alone is the message.*


## Related topics

- [Create a music-driven video](/guides/music-to-video.md)
- [Captions and talking-head footage](/prompting/captions-and-talking-heads.md)
- [Capstone — every technique, one journey](/prompting/capstone.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.