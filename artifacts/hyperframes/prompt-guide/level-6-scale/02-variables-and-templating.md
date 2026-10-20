> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Variables and templating

> Ask for the parts that should change to become named slots, then re-render the same composition with different values — one output per record.

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

[Design systems](/prompting/design-systems) covered the parts of a video that
should *never* change per render — the brand. This page covers the parts that
should. A card per customer. A stat per quarter. A name per recipient.

When you know a composition will be reused, say so in the prompt. Name the parts
that change. The agent turns them into declared
[variables](/concepts/variables) — typed, labeled slots filled at render time
instead of hardcoded into the HTML.

The trigger phrase is simple. Call out the slots:

> Build a 6-second title card. Make the **name**, the **logo**, and the **accent color** variables; everything else stays fixed.

<DocsVideo title="HyperFrames video: Validate Variables Default" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-variables-default.mp4#t=0.1" loop />

*Default variable values.*

<DocsVideo title="HyperFrames video: Validate Variables Variant" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-variables-variant.mp4#t=0.1" loop />

*The same composition re-rendered with `--variables` overrides — different name, logo, and accent, zero re-prompting.*

The agent declares `data-composition-variables` on the composition root, with
the right type for each slot. The name is a `string`. The accent is a `color`.
The logo is an `image`, and a plain URL is a valid value for it. A plain `<img>`
logo needs no timing attributes. Only `<video>` and `<audio>` variables involve
the media wiring described in [variables](/concepts/variables). One composition,
many fills.

## Say what type each slot is

There are seven variable types: `string`, `number`, `color`, `boolean`, `enum`,
`font`, and `image`. Each one validates differently at render time. In
[Studio](/packages/studio), `boolean`, `enum`, `color`, and `number` each get
their own control, while `string`, `font`, and `image` use a plain text input.

You don't write the JSON yourself. But naming the type in the prompt removes a
guess:

> Variables: `plan` (enum: Free / Pro / Enterprise), `price` (number, shown as `$`), `featured` (boolean — toggles the ribbon), `headline` (text).

* ❌ `make the plan and price editable`
* ✅ `plan is an enum (Free / Pro / Enterprise); price is a number in dollars`

The engine rationale: an `enum` with declared options is checked against that
list at render time, so `enum-out-of-range` gets caught. A `number` can carry
`min`, `max`, `step`, and a `unit` label, which is what gives Studio a real
slider instead of a bare text box. Say "editable" and you leave the agent to
pick a type. A mistyped value then surfaces much later.

## Template, then render one per record

Once the varying parts are variables, the same source renders once per data row.
This is a real batch mode, not a copy-paste-per-video loop. You author the
composition once and feed it a list of value sets:

> Build this as a template with `name` and `title` variables, then render one video per row of my data — output to `renders/{name}.mp4`.

The agent authors the composition, then runs a
[batch render](/concepts/variables#batch-renders). The batch input is a JSON
array. Each row is one set of variable values, and each row produces one output
file. `{key}` placeholders in the output path get filled from that row.

If your source is a CSV, say so. The agent converts it to the row array the
batch expects.

Add "fail on any undeclared or mistyped value" and it renders with
`--strict-variables`. A typo in a column name then stops the run instead of
silently rendering the default.

Everything shares one composition. So a design fix propagates to every output on
the next render. You are not editing a hundred near-duplicate files.

## Personalization asks

Personalized-at-scale videos are the same pattern, with the value set coming
from your data:

> A 10-second welcome clip that greets each new signup by first name and shows their company logo. I'll supply a list of `{ firstName, logoUrl }` records.

`firstName` is a `string`. `logoUrl` is the image slot your composition binds to
an `<img src>`.

Pass assets as **URL references, not inlined data**. URL-shaped values travel
cleanly through both the local renderer and distributed
[Lambda renders](/deploy/templates-on-lambda).

Wiring this behind your own product UI or an agent instead of the CLI? The
[`@hyperframes/sdk`](/packages/sdk) opens a base template and layers a sparse
override set per instance. The host then stores only each record's delta.

## Declare up front — don't bake values in

The most common miss is describing the finished video with the values already
fixed, then asking to "make it reusable" afterward:

* ❌ `Make a card that says "Acme — Pro plan — $49". Later I'll want other companies too.`
* ✅ `Make a plan card. Variables: company (text), plan (enum), price (number, $). Show "Acme / Pro / 49" as the default.`

The engine rationale: variables are runtime values a script applies to the live
DOM. They resolve from declared defaults first, then per-instance overrides,
then the CLI.

Declare them up front and the reusable structure exists from the first render.
The default is then just one more value set. Bake `"Acme — Pro — $49"` into the
markup and you get a composition with no slots. Reuse then means an edit pass
over hardcoded text for every variant. That is exactly what variables exist to
avoid.

## Prove the template actually re-skins

A template that never re-skins can pass every gate you have. `lint` and `check`
verify structure. `--strict-variables` catches an undeclared or mistyped key.
Neither can tell you whether the values you passed ever reached the DOM.

The failure looks like success. The render completes, exits clean, and is
**pixel-identical to the default**.

So test it differentially. Render twice and compare:

```bash theme={null}
hyperframes render --output default.mp4
hyperframes render --variables '{"ground":"#0d1420","ink":"#c8ff3d"}' --strict-variables --output reskin.mp4
```

Two identical files mean the override never reached the property you expected.
Check three things. Is the variable ID declared? Does the render command use
that exact ID? Is the visible property actually bound to its CSS custom property
or variable value?

Render-time `--variables` overrides are global by variable ID. The compiler
applies a matching override to CSS custom properties on the root and on
sub-compositions pulled in with `data-composition-src`. `data-variable-values`
is still the per-instance way to give two mounts different values.

Scoped JavaScript inside a sub-composition reads its own per-instance variable
table. So forward values at the mount point when that script calls
`getVariables()` instead of reading CSS.

The [capstone](/prompting/capstone) keeps its variables on one root file for
simplicity, not because templates require one file. Sub-compositions work as
long as shared CSS-bound IDs are declared consistently. Use mount-point values
for instance-specific or JavaScript-read inputs. Its exact variable clause is
quoted at the bottom of this page.

## What can't be a variable

A few inputs are read once at compile time, and no variable can move them:

* composition **dimensions** (`data-width` / `data-height`)
* the **root composition's total duration**
* **frame rate**
* **output format, codec, or quality**

So this doesn't do what it reads like:

* ❌ `make the video length a variable so each render can be a different duration`
* ✅ `author one composition per target length` — or vary a *clip's* duration,
  which is re-read from the live DOM

If total length must differ per output, that is a different root `data-duration`
per render, not a variable. See
[what can't be a variable](/concepts/variables#what-cant-be-a-variable) for the
full list and the compile-time-vs-live-DOM rule behind it.

<Note>
  An authored CSS custom property always wins over a same-named variable. Say
  your composition already defines its own `:root { --accent: ... }` as a
  hand-written theme token. A variable called `accent` never overwrites it — the
  authored value stands. A render-time `--variables` override still wins over
  both. So when you need to override an authored value per render, use
  `--variables`, not a same-named declared variable.
</Note>

## Related

<CardGroup cols={2}>
  <Card title="Variables (concept)" icon="sliders" href="/concepts/variables">
    The mechanics: declaring types, per-instance overrides, batch renders, precedence.
  </Card>

  <Card title="@hyperframes/sdk" icon="code" href="/packages/sdk">
    Template + sparse-override editing behind your own product UI or agent.
  </Card>

  <Card title="The specification dial" icon="gauge" href="/prompting/specification-dial">
    How much to specify — and why naming the type is cheap precision.
  </Card>

  <Card title="Design systems and brand" icon="palette" href="/prompting/design-systems">
    Brand tokens as variables that re-skin every reuse from one value.
  </Card>
</CardGroup>

<Note>
  **Capstone thread** — the [Level 7 film](/prompting/capstone) is a working
  template. One single-file composition, one variable scope. Its second render is
  nothing but one `--variables` flag: navy ground, acid-green ink, every region
  re-skinned including the generated mural. Both full renders are embedded on the
  capstone page.
</Note>

This is the clause in the [full capstone prompt](/prompting/capstone#the-prompt-word-for-word)
that buys the piece — prompt language you can lift for your own video:

> **Variables:** expose `ground` (default `#0a0a0a`) and `ink` (default `#3CE6AC`) as composition variables on the single root file, bound via CSS custom properties everywhere (including the duotoned mural), so one `--variables` call re-skins the entire journey. It will be rendered twice: the default brand palette, and a second full render with `{"ground":"#0d1420","ink":"#c8ff3d"}`.
>
> **Architecture constraint (technical):** single composition file — one `index.html`, one variable scope. \[…] No `data-composition-src` sub-files.

*Next: [Storyboards](/prompting/storyboards) — for multi-scene work, prompt the plan a frame-by-frame build fills in, not the scenes one by one.*


## Related topics

- [Capstone — every technique, one journey](/prompting/capstone.md)
- [Design systems and brand](/prompting/design-systems.md)
- [Storyboards](/prompting/storyboards.md)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.