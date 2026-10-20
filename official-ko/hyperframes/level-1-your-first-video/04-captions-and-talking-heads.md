> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# 캡션과 토킹 헤드 영상

> 기존 토킹 헤드 클립을 꾸미는 두 가지 방법입니다. 읽기 쉬운 캡션이나 디자인된 그래픽 오버레이를 추가하며, 두 방법 모두 영상 자체는 건드리지 않습니다.

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

앞의 두 실습은 아무것도 없는 상태에서 영상을 만들었고, 세 번째는 diff에서 영상을 만들었습니다. 이번에는 이미 가지고 있는 영상, 즉 토킹 헤드 클립에서 시작합니다. 촬영 장면 자체를 건드리지 않고 그 위에 레이어를 하나 더 얹습니다.

## 첫 번째 성과

[`/embedded-captions`](/prompting/overview)에 기존 클립을 가리키는 프롬프트 하나를 주면, 아직 어떤 기법도 필요 없이 완성된 캡션 영상을 얻을 수 있습니다.

캡션은 모드가 아니라 **아이덴티티(identity)**로 라우팅됩니다. 카탈로그에서 룩 하나를 고르면 되고, 그 뒤에서 동작하는 엔진은 굳이 이름을 댈 필요가 없는 세부 사항입니다. 기본값은 깔끔한 축어(verbatim) 레일인 `anchor`이며, 가끔 가장 강한 단어 하나를 피사체 뒤에 합성합니다.

> /embedded-captions Add captions to ./interview\.mp4. Use the `anchor` identity — clean verbatim rail carrying the spoken words, readable lower-third. Promote the single hardest-hitting word to an embed behind the speaker; highlight one key word in each rail line. Keep the source aspect ratio. Footage stays untouched.

<DocsVideo title="HyperFrames video: Captions Anchor Rail" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/captions-anchor-rail-v2.mp4#t=0.1" loop />

*위 프롬프트를 생성된 아바타 영상에 적용해 렌더링했으며, 편집하지 않았습니다. 화자 뒤에 강조 임베드가 하나 있고, 나머지는 모두 레일에 있습니다.*

대부분의 텍스트는 레일이 담당하고, **임베드**는 드물고 얻어야 하는 절정 단어입니다. 클라이맥스에서 화자 뒤에 매트로 합성된 큰 단어 하나가 그것입니다. 모든 줄을 임베드로 만드는 것이 이 스킬이 막으려는 가장 흔한 실수입니다. 전체 대본을 임베드하는 것이 바로 그 실수입니다.

## 토킹 헤드에 추가할 수 있는 두 가지

두 워크플로 모두 기존 토킹 헤드, 인터뷰, 팟캐스트 클립을 받아 그 위에 레이어를 얹습니다. 어느 쪽도 영상을 편집하지 않습니다. 자르기, 색보정, 리프레임, 순서 변경 모두 하지 않습니다. 클립은 그 아래에서 그대로 재생되고, 여러분은 그 위에 무엇을 얹을지만 고릅니다.

| 원하는 것 | 경로 | 추가되는 것 |
| - | - | - |
| 말한 내용을 읽을 수 있는 텍스트로 | `/embedded-captions` | 캡션/자막 — 레일과 절정 임베드 |
| 대화에 맞춰 동기화된 디자인 그래픽 | `/talking-head-recut` | 오버레이 카드 — 제목, 하단 자막, 데이터 콜아웃, 인용문, PiP |

말한 단어 자체를 읽혀야 한다면 캡션이 필요합니다. 키네틱 타이틀, 수치 강조, 인용문 카드, 차트가 화면을 채우는 동안 화자를 구석으로 줄이는 것처럼 완성된 룩을 원한다면 오버레이 카드가 필요합니다. 둘 다 필요하다면 캡션을 먼저 넣고 나서 패키징하십시오. 두 방식은 서로 대체재가 아니라 형제 관계입니다.

`/embedded-captions`는 처음부터 끝까지 로컬에서 실행됩니다. 직접 전사하고 피사체를 매트로 분리하며, API 키가 필요 없습니다. 다만 **단일 피사체 클립**이 필요합니다. 여러 화자이거나 하드 컷이 있는 클립은 샷별로 나뉘거나 거부됩니다. 매트는 한 사람을 기준으로 하기 때문입니다.

## 기본 프롬프트 — 오버레이 카드

> /talking-head-recut Package ./founder-clip.mp4 with designed graphic overlay cards synced to the transcript. 9:16 portrait, warm-paper style. Open with a fullscreen kicker + title hook, drop a lower-third when she names the company, a data callout card counting up the "200+ teams / \$1.2M ARR" stat, and a pull-quote card for the strongest line. Speaker stays full-bleed under the cards; shrink her into a corner PiP while the data card holds. The clip plays untouched underneath.

여기서는 *카드*를 설명합니다. 카드의 내용, 타이밍, 그리고 화자가 캔버스를 카드와 어떻게 나눠 쓸지(풀블리드, 분할, PiP, 유리 오버레이)를 적습니다. 스킬이 각 카드를 설계하고 작성합니다. 고정된 아키텍처 목록은 없으므로, 오버레이는 전사문이 실제로 말하는 내용을 따라갑니다.

## 조절 가능한 핵심 옵션

기법을 배우기 전에도 프롬프트만으로 조절할 수 있는 것들입니다.

**아이덴티티와 톤(캡션).** 아이덴티티 하나가 전체 룩을 결정합니다. 표면, 팔레트, 모션, 클라이맥스 동작까지 포함합니다. 내용에 따라 라우팅하십시오. 설명형/인터뷰/반드시 읽혀야 하는 단어 → 레일을 운반하는 아이덴티티이며, 모든 단어가 읽혀야 할 때는 보수적인 기본값인 `anchor`를 씁니다. 시적/소셜/시네마틱 → 분위기에 맞는 열 흐름 아이덴티티(`editorial`, `cream`, `loud`, `neon`). "炸 / 특효 / VFX" → 테마 아이덴티티(`ordnance`, `terminal`, `stomp`). 잘 모르겠으면 `anchor`를 쓰십시오. 단어는 읽히고 장면은 안전하게 유지됩니다. "Standard vs Cinematic vs Theme"을 요청하지 마십시오. 그것들은 엔진 이름입니다. 아이덴티티를 이름으로 지정하십시오.

**축어 레일 대 절정 임베드.** 레일이 기본이며 대부분의 텍스트를 담습니다. 임베드는 승격입니다. 피사체 뒤에 매트로 합성된 절정 단어 하나이며, 드물고 간격을 두고 배치됩니다(대략 비트당 하나, 동시에 두 개가 보이지 않으며, 정점은 최대 하나). 스킬에게 *어떤* 줄이 임베드를 얻을 자격이 있는지 알려 주고, 나머지는 레일에 두십시오.

**스타일, 레이아웃, 캔버스(recut).** 스타일 그룹(warm-paper / clinical / experimental), 레이아웃(split / stack / pip / overlay), 캔버스 비율을 고르면 레이아웃과 스타일의 조합으로 영상 프레임이 정해집니다. 권장 비율은 원본과 맞지만 선택은 여러분의 몫입니다. 데스크톱/YouTube는 16:9, Reels/Shorts는 9:16, 피드는 4:5를 씁니다.

**키워드 강조.** 캡션 레일에서 강조 단어에 인라인 `emphasis`를 붙일 수 있습니다. 레일을 벗어나지 않고 강조색이나 활성 단어 팝 효과를 줍니다. "highlight the key word in each line"이라고 요청하면 가독성을 유지한 채 강조됩니다.

## 변형

<AccordionGroup>
  <Accordion title="Cinematic caption embed (mood over verbatim)">
    > /embedded-captions Cinematic captions on ./poem.mp4 — no rail, hero typography composited behind the speaker, words accumulating as a column. Use the `editorial` identity (lowercase-italic hero). One apex word per thought, air between them. 4:5. Never grade the footage.

    열 흐름 아이덴티티는 레일을 없애고 모든 것을 임베드 스타일로 만듭니다. 가독성보다 분위기가 중요한 시적/소셜/"시네마틱" 요청에 쓰십시오. 단어가 정확히 읽혀야 하는 설명형 영상에는 쓰지 마십시오.
  </Accordion>

  <Accordion title="Bright-scene captions">
    > /embedded-captions Add verbatim captions to ./outdoor-vlog.mp4. It's a bright daylight scene, so use the `ink` identity — near-black type printed onto the surface — not a light-on-bright look that washes out. Keep it a readable rail. 16:9.

    스크린 블렌드 방식의 크림 룩은 밝은 배경(휘도 약 180 초과)에서 바랩니다. `ink`는 밝은 표면을 위해 만들어졌습니다. 엔진에게 룩의 색을 바꾸라고 요청하지 말고, 아이덴티티를 장면에 맞추십시오.
  </Accordion>

  <Accordion title="VFX-grade themed captions">
    > /embedded-captions Bring the energy on ./hype-clip.mp4 — I want the captions to hit hard. Use the `ordnance` identity: a stamped verbatim rail with a detonation apex. Rail carries the verbatim; the payoff line is the setpiece. 9:16.

    테마 아이덴티티(`ordnance`, `terminal`, `stomp`, `neonsign`, `stardust`, …)는 "폭발하게 만들어 줘 / 특효 / AE로 만든 것처럼"이라는 요청에 대한 답입니다. 테마 모드는 레지스터에 따라 반응하는 비트가 프레임에 닿을 수 있는 유일한 곳입니다. 매트 합성 이후에 적용되어 피사체, 텍스트, 플레이트가 하나로 움직입니다. 그래도 A-roll은 결코 색보정되지 않습니다.
  </Accordion>

  <Accordion title="Landscape data recut">
    > /talking-head-recut Recut ./analyst-interview\.mp4 as a 16:9 explainer with a clinical style. Split layout: speaker on the right, data cards on the left. Cards for each claim — a count-up for the headline number, a swiss-grid comparison for the two options, a terminal-style callout for the technical bit. Auto-pace the card count for a 5-minute clip. Footage untouched.

    레이아웃(split / stack / pip / overlay)은 화자와 카드가 캔버스를 어떻게 나눌지 정합니다. 카드 개수는 길이와 정보 밀도에서 자동으로 추론되며, 짧은 클립에도 리듬이 생기도록 최소 5장입니다.
  </Accordion>
</AccordionGroup>

## 실패 사례

**영상 편집을 요청하기.** 두 스킬 모두 레이어만 추가하고 A-roll은 촬영된 그대로 둡니다. 자르기, 빠르게 하기, 색 바꾸기, 리프레임, 순서 바꾸기는 NLE 편집이며 범위 밖입니다. 캡션과 카드만이 추가 가능한 요소입니다.

* ❌ `add captions and trim the dead air at the start, and warm up the color to match my brand`
* ✅ `add captions; leave the footage untouched` — 자르기/보정은 먼저 편집기에서 하고, 완성된 클립을 여기로 가져오십시오.

**모든 단어를 임베드하기.** 토킹 헤드에서는 레일이 축어 기본값입니다. 모든 캡션을 피사체 뒤에 매트로 합성하면 단어가 묻히고, 절정이 아무것도 아닌 곳에 쓰입니다.

* ❌ `composite every caption behind the speaker for a cinematic look` (설명형 영상에서)
* ✅ `verbatim rail; promote only the two payoff lines to an embed`

**여러 피사체 클립.** 캡션 매트는 한 사람을 기준으로 합니다. 두 명의 화자나 하드 컷이 있으면 깜빡이거나 거부됩니다.

* ❌ `caption this two-person podcast in one pass`
* ✅ `split the clip per shot / per speaker first, then caption each` — 또는 단일 피사체 컷을 사용하십시오.

<Tip>
  이 프롬프트들이 공유하는 비트 타임스탬프 골격은 [프롬프트 해부](/prompting/anatomy)를 참고하십시오. 모션과 강조 설정에 대응하는 형용사는 [어휘](/prompting/vocabulary)를 참고하십시오. 기존 영상을 꾸미는 대신 처음부터 영상을 만들려면 `/hyperframes`의 라우터에서 시작하십시오.
</Tip>

이 레벨이 다루는 워크플로는 [캡션과 토킹 헤드](/guides/captions-and-recuts)에 정리되어 있습니다. 입력으로 무엇을 받고, 빌드 전에 무엇을 묻고, 무엇을 반환하는지 설명합니다.

*다음: [뮤직비디오와 슬라이드쇼](/prompting/music-and-slideshows) — 영상 대신 사운드트랙이나 슬라이드를 넣고, 비트나 덱이 속도를 정하게 하십시오.*


## 관련 주제

- [아바타 프레젠터 추가하기](/guides/avatar-presenter.md)
- [코드 변경과 PR](/prompting/code-and-prs.md)
- [토킹 헤드 영상에 캡션을 추가하거나 다시 패키징하기](/guides/captions-and-recuts.md)


이 문서는 [Mintlify](https://mintlify.com)로 빌드되고 호스팅됩니다. Mintlify는 개발자 문서 플랫폼입니다.
