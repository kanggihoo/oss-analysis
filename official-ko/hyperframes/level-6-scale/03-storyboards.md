> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져오세요.
> 더 살펴보기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾으세요.

# 스토리보드

> 여러 장면으로 이루어진 작업이라면 장면을 하나씩 프롬프트하지 마세요. 계획을 프롬프트하세요. 즉, 흐름(arc), 프레임별 비트, 그리고 빌드가 그 빈칸을 채울 때 따르는 페이싱 규칙을 적으세요.

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

[변수와 템플릿](/prompting/variables-and-templating)은 하나의 컴포지션을 여러 번 렌더링하며 재사용하는 방법을 다뤘습니다. 이 페이지는 규모의 다른 축, 즉 여러 장면으로 이루어진 하나의 영상을 다룹니다.

비트가 몇 개를 넘어가면, 빈 페이지에서 장면을 하나씩 묘사하는 방식은 느립니다. "그다음 프레임 2는 X를 보여 주고, 프레임 3은 Y를 보여 준다." 같은 식입니다. 또한 프레임들을 서로 묶어 주는 것이 없어서 점점 어긋나기도 합니다.

대신 **계획**을 한 번 프롬프트하세요. 전체를 관통하는 흐름, 각 프레임이 맡는 역할, 공개(reveal)의 속도를 정하는 규칙을 적습니다. 그다음 빌드가 프레임들을 이 계획에 맞춰 배치하도록 하세요.

이 서사 어휘는 작성 원칙이지, `STORYBOARD.md`에 추가로 필요한 스키마가 아닙니다. 워크플로가 여러분의 계획을 빌드가 쓰는 더 작고 기계가 읽을 수 있는 형태로 옮겨 줍니다.

<Note>
  "스토리보드"는 에이전트가 [시작 인터뷰](/prompting/overview#the-interview-what-the-agent-asks-first)에서 묻는 질문이기도 합니다. 거기서 예라고 답하면 계획(채팅에서), 정지 이미지(`boards/storyboard.html`의 보드), 그리고 빌드를 모두 단계별로 함께 검토하게 됩니다. 그 답은 검토 과정을 바꿀 뿐 경로를 바꾸지는 않습니다. 어느 쪽이든 이 페이지가 가르치는 계획이 빌드의 기준이 됩니다.
</Note>

## 장면이 아니라 계획을 프롬프트하기

스토리보드는 개별 프레임 위에 놓이는 짧고 구조화된 문서입니다. 세 가지를 담습니다.

* 흐름 하나
* 모든 프레임이 물려받는 연출 블록 하나
* 핵심 순간마다 붙는 가벼운 프레임별 명세(전체 묘사가 아닙니다)

워크플로는 계획을 읽고, 그에 맞춰 각 프레임의 HTML 하위 컴포지션을 만듭니다. 영상의 *형태*를 정확히 말하면, 프레임들은 이미 페이싱, 팔레트, 결실이 서로 맞는 상태로 나옵니다. 프레임마다 그것을 다시 말할 필요가 없습니다.

방법은 장면 하나가 아니라 흐름에 이름을 붙이고 스토리보드를 요청하는 것입니다.

> Storyboard a 3-frame piece: hook → substance → landing, silent, \~15 seconds, with a callback that pays off the opening motif.

아래 내용은 "스토리보드"라는 느슨한 말을 빌드가 한 번에 실행할 수 있는 계획으로 바꿔 주는 어휘입니다.

## 영상의 형태를 한 번만 정하기

어떤 프레임보다 먼저, 모든 프레임이 평가받을 네 가지를 정하세요.

* **메시지(Message)** — 영상 전체가 증명해야 할 한 문장짜리 주장입니다. 어떤 프레임이 이를 뒷받침하지 않으면, 메시지가 아니라 그 프레임을 잘라냅니다.
* **흐름(Arc)** — 비트의 순서를 평이하게 적습니다. `Hook → Substance → Landing`, 또는 `Hook → Problem → Solution → Proof → CTA`. 프레임들이 점점 고조되는 순서가 아니라 병렬 항목일 때는 "리스티클"처럼 형태를 나타내는 단어를 씁니다.
* **시청자(Audience)** — 누구를 위한 것인지 한 구절로 적습니다. 모든 프레임의 어조와 전문 용어 수준을 한꺼번에 맞춰 줍니다.
* **분위기(Mood)** — 음악이나 에너지를 나타내는 묘사 하나, 예를 들어 "긴장감 있는 신스 펄스가 따뜻하게 풀리는 느낌". 무음 작품이라도 모든 프레임의 페이싱이 여기에 맞아야 합니다.

이 네 가지는 맨 앞에서 한 번만 말하세요. 그러면 개별 프레임 프롬프트가 자기 어조를 다시 정당화할 필요가 없습니다.

## 연출 방향은 한 번 정하고 모든 프레임에 적용하기

스토리보드의 연출 블록은 모든 프레임이 굳이 다시 말하지 않아도 따르는 규칙들의 집합입니다. 명시해 둘 가치가 있는 규칙은 네 가지입니다.

**두 색 원칙.** 바탕색 하나와 잉크색 하나를 정하세요. 그다음 규칙을 분명히 말하세요. 강조를 위해 두 번째 색조를 주는 것은 없습니다. 더 큰 순간은 반전, 굵기, 크기, 밀도를 통해 더 크게 만듭니다.

* ❌ `use the brand colors, plus a highlight color for the important bits`
* ✅ `ground: deep navy; ink: warm white. Emphasis = invert, scale up, or go denser — never a third color.`

**VO 기준 공개(VO-paced reveals).** 규칙 자체는 [미디어와 오디오](/prompting/media-and-audio#pace-reveals-to-the-narration)에 있습니다. 스토리보드는 이 규칙을 프레임마다 *적용하는* 자리입니다. t=0에서는 내레이터가 말하는 내용만 화면에 있고, 각 부분은 말로 나오는 신호에 맞춰 등장합니다.

여기에 유지(hold) 동작을 함께 정하세요. 정지된 프레임이 완전히 가만히 있을지, 아니면 은은한 idle 움직임을 줄지 말하세요. 느린 드리프트나 "숨쉬기" 효과는 요청하지 마세요. 그것은 의도된 선택이 아니라 미완성으로 보입니다.

영상이 무음이라면 규칙의 틀은 유지하고 신호만 바꾸세요. 공개는 말로 나오는 절 대신 지정된 타임스탬프에 맞춥니다. 페이싱은 여전히 의도적이어야 합니다. 다만 맞춰 줄 VO가 없을 뿐입니다.

**숨 고르기 프레임 하나.** 영상 전체에서 숨 고르기 프레임을 정확히 하나만 지정하세요. 의도적으로 더 차분하고 정적인 비트, 또는 가장 길게 유지되는 읽기 구간입니다. 나머지 프레임은 계속 전개됩니다.

이렇게 지정하면 두 가지 실패를 막을 수 있습니다. 빌드가 시청자가 숨을 고르게 해야 할 그 한 프레임을 과하게 애니메이션하지 않고, 그 프레임에 맞춘다며 나머지 프레임을 덜 애니메이션하지도 않습니다.

**금지 목록(negative list).** 금지할 시각적 클리셰 목록을 한 번만 적습니다. 프레임마다 새로 만드는 목록이 아니라 항상 적용되는 필터입니다. 모든 프레임은 만들어지면서 이 목록에 대해 점검됩니다.

> no purple-blue AI gradients, no bokeh, no browser chrome, no drop-shadow cards, no infinite loops or randomness

*여러분의* 영상에 맞지 않는 클리셰로 바꾸세요. 핵심은 프레임이 어떤 클리셰로 흘러들기 전에 미리 이름을 붙여 두는 것입니다.

## 프레임마다 역할 주기

연출 블록이 공통된 모든 내용을 담당합니다. 따라서 각 프레임의 프롬프트에는 그 프레임만의 차이점만 적으면 됩니다.

```text theme={null}
[type]        the frame's category      hook · benefit_highlight · social_proof · cta
[persuasion]  the rhetorical device     before/after · numbered enumeration · counterexample · callback + distillation
[beat]        the emotional beat        recognition + tension · aha · resolve + inevitability
[focal]       the one thing the eye lands on
[roles]       what's foreground / supporting / background, assigned explicitly
```

`persuasion`과 `beat`는 절대 빼먹지 마세요. 없으면 프레임은 "통계를 보여 주는 장면"이 됩니다. 있으면 "통계를 증명하고, 그 통계가 *어떻게 와닿는지*를 보여 주는 장면"이 됩니다.

설득 장치와 비트가 지정된 프레임은 빌드가 모든 선택에 이유를 갖게 해 줍니다. 시각적 묘사만 있는 프레임은 이유를 주지 못합니다.

## 콜백(callback)

모티프는 일찍 도입하세요. 도형, 표식, 문구, 색 한 조각 같은 것입니다. 나중에 더 촘촘하거나 꽉 찬 모습으로 돌아오게 해서 의도된 보상을 만듭니다.

계획에는 두 부분을 모두 적으세요. 모티프를 어디에 심는지, 그리고 돌아올 때 어떻게 바뀌는지입니다.

> A single thin accent dot appears top-right in frame 1 at low weight. In the landing frame, that same dot expands and fills into the full logo lockup — same motif, now complete.

돌아오는 방식을 명확히 적으세요. 그렇지 않으면 다시 만드는 과정에서 초반 모티프를 그냥 일회성 질감으로 취급해도 됩니다. 콜백은 계획이 두 번째 등장이 비슷해 보이는 새 요소가 아니라 *같은* 요소라고 말할 때만 작동합니다.

## 예시: 무음 3프레임 스토리보드

<Tip>
  아래의 `storyboard-mini`는 의도적으로 작고 무음입니다. 프레임 3개, 약 \~15초, 내레이션 없음. 그래서 흐름, 연출 블록, 프레임별 역할, 숨 고르기 프레임 하나, 콜백 하나로 이루어진 전체 패턴을 저렴한 렌더 한 번으로 확인할 수 있습니다. 더 길고 내레이션이 있는 스토리보드를 쓰기 전에 이것부터 해 보세요.
</Tip>

> Storyboard a 3-frame, \~15-second, 1920x1080 piece. Silent — no narration, no VO track. Message: "Fernwell gives you back the hours other tools take." Arc: Hook → Substance → Landing. Audience: small-team operators evaluating a new tool. Mood: tense synth pulse resolving to warm.
>
> Direction for every frame: ground color deep navy `#0b1220`, ink color warm off-white `#f4efe6`. Nothing else gets a hue — emphasis is inversion, scale, or density only. Reveals stage on internal timestamps, since the piece is silent and there's no spoken cue. At each frame's t=0 only its first element is on screen. The rest arrive on the timestamps below. Holds stay fully still, no drift or breathing. No purple-blue AI gradients, no bokeh, no browser chrome, no drop-shadow cards, no infinite loops or randomness.
>
> Frame 1 — Hook (0.0–4.0s), type: hook, persuasion: counterexample, beat: recognition + tension, focal: the headline. At 0.0s: bold ink headline "Most tools slow you down." slams in, centered. At 1.5s: a single thin accent dot (ink color, small, low weight) fades in top-right — the motif, planted quietly. Hold from 3.0–4.0s.
>
> Frame 2 — Substance, **the breather** (4.0–10.0s), type: benefit\_highlight, persuasion: numbered enumeration, beat: aha, focal: the stat. This is the one deliberately calmer, more static frame in the piece. Everything else develops continuously. This one mostly holds. At 4.0s: the accent dot from frame 1 carries over, now larger, sitting quietly left-of-center. At 5.0s: a big stat "3.2 hrs / week" fades in beside it, no motion after it lands. Static hold 6.0–10.0s.
>
> Frame 3 — Landing (10.0–15.0s), type: cta, persuasion: callback + distillation, beat: resolve + inevitability, focal: the completed motif. At 10.0s: the accent dot from frames 1–2 expands and fills into the full Fernwell wordmark lockup — same motif, now complete, denser and larger. At 12.0s: tagline "Fernwell. Built for flow." stamps in below it. Hold 13.5–15.0s.

<DocsVideo title="HyperFrames video: Storyboard Mini" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/storyboard-mini.mp4#t=0.1" loop />

*위 프롬프트를 편집 없이 렌더링한 결과 — 오디오 트랙 없음, 요청한 그대로입니다.*

## 관련 문서

<CardGroup cols={2}>
  <Card title="단일 프롬프트의 구조" icon="list-ordered" href="/prompting/anatomy">
    한 비트가 쓰는 여섯 부분 골격입니다. 같은 원칙을 한 번에 한 프레임씩 적용합니다.
  </Card>

  <Card title="본 것을 다시 만들기" icon="film" href="/prompting/recreating-references">
    움직임을 프레임 단위로 옮겨 적기. 스토리보드의 프레임별 타임스탬프에 필요한 것과 같은 엄밀함입니다.
  </Card>

  <Card title="디자인 시스템과 브랜드" icon="palette" href="/prompting/design-systems">
    스토리보드의 연출 블록이 가져오는 두 색 원칙과 브랜드 토큰입니다.
  </Card>

  <Card title="HyperFrames 프로젝트의 작동 방식" icon="route" href="/concepts">
    제작 산출물인 `STORYBOARD.md` — 이 장의 계획이 `BRIEF.md` 다음 단계에서 들어가는 곳입니다.
  </Card>
</CardGroup>

<Note>
  **캡스톤 흐름** — [Level 7 영상](/prompting/capstone)은 이 장의 콜백 장치를 전체 길이에 걸쳐 늘립니다. 오프닝에서 입력된 `<div class="clip">` 칩은 모든 영역을 거치며 와이어를 따라 이동합니다. 마지막에는 보상으로 렌더 슬롯에 딱 맞게 들어갑니다(아래 영상에서 잘라낸 부분).
</Note>

이 절은 작품을 완성시키는 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)의 한 구절입니다. 여러분의 영상에 그대로 가져다 쓸 수 있는 프롬프트 문장입니다.

> **The clip card** — the `<div class="clip">` typed in the opening travels the whole journey: it slides onto the wire as a clip chip after being typed, rides ahead of the camera between regions (handing itself off — visible leaving one region and arriving in the next), and is the thing that finally renders at the end. It is the protagonist.

<DocsVideo title="HyperFrames video: Capstone Region Render" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-render.mp4#t=0.1" loop />

*이 절이 결실을 맺는 장면을 렌더링한 것 — 와이어 위에서 꼬박 1분을 보낸 뒤 주인공 칩이 렌더 슬롯에 도착합니다.*

*다음: [기존 영상 편집](/prompting/editing-existing-videos) — 스토리보드를 쓰든 안 쓰든, 첫 렌더를 그 뒤의 스무 번의 편집으로 바꿔 주는 편집 동사들입니다.*


## 관련 주제

- [제품 업데이트](/product-updates.md)
- [Figma 연동](/guides/figma.md)
- [예제](/examples.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 만들어지고 호스팅됩니다.
