> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Media and audio

> Ask for the voiceover, music, sound, captions, cutouts, and assets a composition needs, in phrasing the media pipeline acts on.

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

Your video moves and reads right. This level gives it a voice.

HyperFrames owns media *playback*. A sibling media pipeline resolves everything
else: voice, music, sound effects, images, icons, logos, captions, and
background removal. You describe what the composition needs. The agent resolves
each need to a frozen local file.

Precision is the whole craft here. Vague asks come back wrong. "Add some music"
and "no sound" are the two that bite most often, because the pipeline does
exactly what the words say.

## Voiceover (TTS)

The agent picks a voice engine in a fixed order. HeyGen Starfish goes first if
your HeyGen account is configured. ElevenLabs is next if that key is set.
Otherwise the local Kokoro model runs, and it needs no API key.

Describe the content and let the agent pick a fitting voice. Or name the voice,
tone, and speed yourself:

> Generate narration for this script with a professional female voice.

> Add TTS voiceover, British male voice, at 1.1× speed.

The [Vocabulary](/prompting/vocabulary#text-to-speech-voices) table maps content
types to Kokoro voices. `af_heart` and `af_nova` suit a product demo. `am_adam`
and `bf_emma` suit a tutorial. `af_sky` and `am_michael` suit marketing. Name a
voice directly if you already know it. Otherwise describe the read and let the
agent choose.

* ❌ `add a voice`
* ✅ `warm, unhurried female narration of the quoted script` — tone and pace are what actually change the delivery

### Gemini voiceover

Choose Gemini when you want to direct a narrator's delivery with a description.
Configure [Gemini credentials](/guides/authentication#providers-used-by-agent-workflows),
then ask your agent:

> Use Gemini 3.8 Flash TTS with the Kore voice to narrate this script. Make the
> delivery warm and unhurried. Use the media-use audio engine, transcribe the
> generated audio, and sync the captions and visual reveals to the spoken words.

The shared audio workflow supports 3.8 Flash and Flash-Lite TTS,
3.1 Flash TTS Preview, and 2.5 Pro and Flash TTS Preview. Gemini is an explicit choice; it does not replace
the automatic provider order above. Keep the script separate from delivery
instructions. The helper uses structured style metadata for 3.8 and a delivery
prompt for older models; review the generated speech for accidental directions.

The agent saves the voiceover locally and obtains word timings through a
separate transcription pass. Check names, numbers, and pauses against the
audio before the final render. A new narration take needs new timings.

## Background music

Music resolves from a large catalog by mood. It should almost always sit *under*
the narration rather than compete with it.

Give the mood **and** a loudness target. The pipeline can duck and normalize to
a level, so an explicit target lands a mix instead of a guess.

> Add subtle electronic BGM, kept under −18 dB so it stays beneath the voiceover.

> Upbeat tech-launch music bed at a low level, ducking under narration.

* ❌ `add background music` — you'll get a full-volume track fighting the VO
* ✅ `subtle background music, ducked ~12 dB under the voice` — a mix instruction the pipeline can execute

<Tip>
  A stated loudness target ("under −18 dB," "ducked under the voice") is the
  difference between music that supports the piece and music that buries it.
  When there's narration, always say the bed goes under it.
</Tip>

## Sound effects

SFX resolve from a bundled 19-file library plus the catalog. Cue them to
specific moments — a transition, a stamp-in, an impact. Don't sprinkle them.

> Add a whoosh on each of the three scene transitions.

> Put a soft click on the button press at 0:04.

## Pace reveals to the narration

Once a video has a voice, the voice is the clock. Say that on-screen elements
land **on their spoken cues**. The stat appears as the narrator says it, not at
some independent time the builder eyeballed. Skip this and narration and visuals
drift into two parallel tracks that happen to share a file.

> VO-paced reveals: each scene's elements land on their spoken cues; secondary elements keep resolving while the narrator is mid-thought; the scene is complete just as the narration moves on.

The capstone film applies exactly this rule to every region. Its Direction block
reads:

> VO-paced reveals: each region's elements land on their spoken cues as the camera arrives; secondary elements keep resolving while the camera is present; the region is complete just as the camera accelerates away.

Two practical notes.

The agent gets word timings for free. Narration is transcribed with per-word
timestamps — the same machinery behind
[captions](#captions-and-transcription). So "on its spoken cue" is a real,
executable instruction.

The inverse rule matters just as much. The narration never waits for the
visuals. Pace the camera and the reveals to the voice, not the voice to the
animation.

## Captions and transcription

Captions come from word-level timestamps. Generate a voiceover and the timing
comes with it. For existing footage, transcription produces the timing: Parakeet
runs when it's installed, and whisper handles it otherwise. Scaffolding a
project from a source video can generate captions from its audio directly.

> Transcribe the narration and add karaoke-style captions synced to it.

> Generate captions from `assets/interview.mp4` and style them hype, scale-pop.

Caption *look* is its own vocabulary — tone, size, per-word emphasis. See the
[Captions catalog](/prompting/captions-catalog) for the styles. This page is
about producing the timed text. That page is about styling it.

## Background removal (transparent cutouts)

The `remove-background` command mattes a subject out of a video or image
locally. You get back a transparent WebM you can drop into any scene as a
`<video>`.

> Remove the background from `assets/presenter.mp4` and float the subject over the scene.

One caveat is load-bearing. The built-in model (`u2net_human_seg`) is
**purpose-built for people**: head-and-shoulders or full-body, reasonably stable
framing, a background that contrasts with the subject. On **non-human subjects**
— products, animals, objects — it returns a mostly-empty mask.

So if you need to cut out a product, say so. The agent should route to a
different tool instead of running the person model and getting nothing.

* ❌ `remove the background from this product shot` with the built-in command — the human-matting model can't see it
* ✅ `matte the presenter out of assets/talk.mp4` for a person. For a product, flag that it's a non-human subject so a different matter is used.

The [Remove background guide](/guides/remove-background) covers the person-only
caveat, the two-layer plate for text-behind-subject, and alternatives for
objects and hair-fine mattes.

## Video-in-video and picture-in-picture

Layering footage is a compositing prompt: a talking head over a scene, a subject
in front of a headline, a PiP inset. The agent applies the frame-accuracy rules
for you. Naming the layout you want still helps.

> Put the transparent presenter cutout in the bottom-right, over the chart scene.

> Layer the headline *behind* the presenter so their silhouette occludes the text.

<Note>
  Two mechanics the workflow skills handle automatically, from the [Remove
  background guide](/guides/remove-background#compositing-patterns-and-pitfalls):

  * A cutout that reveals into view goes inside a non-timed `<div>`, and the
    *wrapper* is what gets animated. HyperFrames owns clip visibility, so
    animating the media element directly fights the clip lifecycle.
  * The base video and the cutout both mount at `data-start="0"`, so their
    decoders stay in sync at the cut.

  You rarely need to say either one. They're why "late-mounting" a PiP clip can
  land a frame off.
</Note>

## Bring any footage

You don't need to pre-convert supplied footage before naming it in a prompt.

Some codecs don't play back cleanly in a browser. HEVC (H.265) is the common
case, straight off an iPhone or a screen recorder. The framework probes the
asset and builds a bounded H.264 proxy automatically, cached under
`.transcode-cache/`.

`preview`, `play`, Studio, and published player pages use that proxy for
playback. A render always decodes the original file, so nothing about final
quality or color is touched. `snapshot` also reads frames from the original with
FFmpeg, so it makes no proxy unless you pass `--proxy`.

`hyperframes lint` also flags the asset at info level (`hevc_preview_codec`) so
you know a proxy is in play. Proxying is optional. Pass `--no-proxy` per
command, or set `media.autoProxy: false` in `hyperframes.json` project-wide.

The same mechanism covers alpha-channel sources. ProRes 4444 and alpha WebM get
a VP8 + Opus WebM proxy instead of being refused, so a transparent cutout in a
hostile codec isn't a blocker either.

None of this changes how you phrase the ask. Name the footage by path like any
other supplied asset, and describe the composition you want built from it.

> Build a short picture-in-picture piece from `source-hevc.mp4` — inset it bottom-right over a full-bleed background scene, with a soft rounded border.

<DocsVideo title="HyperFrames video: Proxy Footage" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/proxy-footage.mp4#t=0.1" loop />

*Rendered from the prompt above, unedited. The source clip is a plain H.265/HEVC
file. The render decoded it directly via FFmpeg. Preview would have used the
automatic H.264 proxy.*

See the [Rendering guide](/guides/rendering#input-video-codecs) for the
mechanics — proxy generation, caching, and which codecs it covers.

## The supplied-assets rule

For any asset you already have, an explicit path removes the most ambiguity. The
agent will search when you only describe an asset. A path settles *which* file.

* ❌ `use my logo`
* ✅ `use assets/logo.svg`

This matters even when a search would have worked. Brand and entity assets
should point at *your* file, not a resolved lookalike.

Third-party logos are a separate case. The pipeline pulls official marks from a
logo cascade and never redraws them by hand. So "add the LinkedIn logo" is fine.
"Add my company's logo" needs a path.

## Say what "no sound" actually means

The most common audio mistake is a negative that means less than you think. "No
narration" removes the voiceover. It does **not** silence music or sound
effects. If you want genuine silence, say so:

* ❌ `no narration` when you mean a completely silent video — music and SFX can still be added
* ✅ `no audio at all` — the unambiguous way to ask for silence

This mirrors the negatives discipline in [Anatomy](/prompting/anatomy). Close
the gap explicitly, because the engine acts on the literal words.

## The capstone thread

<Note>
  **Capstone thread** — the [Level 7 film](/prompting/capstone)'s Material region
  runs this chapter's entire pipeline on one clip: generated footage → HEVC
  auto-proxy → background removal mid-scene → word-synced captions from the clip's
  own transcription, with the clip's audio ducking the BGM (cut from the film,
  below).
</Note>

This is the clause in the [full capstone
prompt](/prompting/capstone#the-prompt-word-for-word) that buys the piece. It's
prompt language you can lift for your own video:

> \[…] a real talking-head clip (generate a short clip of a person speaking one neutral line via the media pipeline's avatar video generation \[…] **transcode it to HEVC `hvc1`** so the automatic proxy subsystem carries preview) sits as a clip on the wire. The order of operations IS the story: as the camera arrives and BEFORE the person speaks, the framework mattes the footage — **the background peels away via background removal** \[…] THEN they speak, and the main **keywords of their own line — derived from the clip's transcription — land word-synced** \[…] The clip's own audio ducks the BGM briefly; the VO resumes as the camera pulls away.

<DocsVideo title="HyperFrames video: Capstone Region Material" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-material.mp4#t=0.1" loop />

*That clause, rendered — the region cut from the finished film.*

*Next: [Audio effects and mixing](/prompting/audio-effects) — making the voice,
music, and effects you just placed sit together.*

## Related topics

* [Vocabulary](/prompting/vocabulary) — voice names, caption tones, and audio-reactive mappings
* [Captions catalog](/prompting/captions-catalog) — styling the timed text this page produces
* [Remove a background](/guides/remove-background) — the matting command, its person-only caveat, and alternatives
* [Use images and video](/guides/video-components) — installable overlays, captions, and effects


## Related topics

- [Lint rules](/reference/lint-rules.md)
- [Vocabulary that changes output](/prompting/vocabulary.md)
- [How a HyperFrames project works](/concepts/index.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.