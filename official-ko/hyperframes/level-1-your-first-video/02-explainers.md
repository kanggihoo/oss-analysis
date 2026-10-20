> ## Documentation Index
> 전체 문서 색인은 다음 주소에서 가져올 수 있습니다: https://hyperframes.heygen.com/llms.txt
> 다른 페이지를 살펴보기 전에 이 파일로 사용 가능한 모든 페이지를 찾아보세요.

# 설명 영상(Explainers)

> 기사, 메모, 또는 주제를 얼굴 없는 설명 영상으로 바꾸려면 무엇을 말해야 하는지 — 모든 시각 요소는 캡처가 아니라 새로 만들어집니다.

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

지난 페이지는 워크플로를 웹사이트에 향하게 했습니다. 이번 페이지는 사이트를 뺍니다. 입력은 텍스트뿐입니다. 모든 시각 요소는 캡처가 아니라 새로 만들어집니다.

## 첫 번째 성과

텍스트를 [`/faceless-explainer`](/prompting/overview) 프롬프트 하나에 붙여넣으세요. 그것으로 완성된 설명 영상을 얻기에 충분합니다. 사이트도, 영상 소스도, 디자인 결정도 필요 없습니다.

[예시](/prompting/examples) 페이지에서 검증된 내용입니다. 붙여넣은 텍스트로 만든 약 \~60초짜리 세로형 설명 영상입니다.

> /faceless-explainer Turn this into a \~60-second 1080x1920 vertical explainer: \[paste your text]. One idea per scene, big typography, diagrams over stock footage, brand color #FF5533 on off-black. Male TTS voice, calm. Embedded captions, keywords highlighted in the brand color.

<DocsVideo title="HyperFrames video: Example Explainer" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-explainer.mp4#t=0.1" portrait loop />

*위 프롬프트에서 렌더링한 결과물, 편집하지 않음.*

`~`에 주목하세요. 스크립트를 제공하면 런타임은 말해지는 단어를 따릅니다. 그러니 정확히 1분이 아니라 *약* 1분을 요청하세요. 나머지 골격은 [구조](/prompting/anatomy)를 보세요.

## 무엇을 만드는가

페이스리스 설명 영상입니다. 여러분의 텍스트가 내레이션이 있는 영상이 됩니다. 기사, 메모, 주제, 브리프 무엇이든 가능합니다. 모든 시각 요소는 장면마다 새로 만들어집니다. 타이포그래피, 추상 그래픽, 다이어그램, 데이터 시각화입니다.

[`/faceless-explainer`](/prompting/overview) 워크플로는 네 가지 일을 합니다. 디자인 시스템을 고르고, 텍스트를 교육용 이야기로 재구성하고, 자체 TTS 내레이션을 생성하고, 그다음 프레임 단위로 영상을 빌드합니다.

**페이스리스는 캡처할 것이 없다는 뜻입니다.** 사이트도, 영상도, 자산 목록도 없습니다. 시각 요소는 하류 단계에서 디자인됩니다.

보여줄 것이 있을 때는 다른 워크플로를 고르세요.

* 판매할 제품 → [`/product-launch-video`](/prompting/product-launch)
* 보여줄 실제 사이트 → 투어 브리프와 함께 [`/product-launch-video`](/prompting/product-launch)
* GitHub PR → [`/pr-to-video`](/prompting/code-and-prs)
* 잘 모르겠다면 → `/hyperframes`에서 시작

## 중요한 설정 항목

프롬프트에서 이 모든 것을 조절할 수 있습니다. 어떤 기법도 배우기 전에 말이죠.

| 설정 항목 | 무엇을 말할지 | 중요한 이유 |
| - | - | - |
| **원문 그대로 vs 요약** | "use my wording verbatim" 또는 "restructure it freely" | 워크플로는 한 번 묻습니다. 원문 그대로는 여러분의 목소리를 지키지만 단어 수를 고정합니다. 요약은 속도를 위해 잘라내고 재배열할 수 있습니다. |
| **길이** | "\~60 seconds", "60 seconds"가 아님 | 스크립트가 있으면 내레이션이 실제 길이를 정합니다. 정해진 숫자를 주면 에이전트가 단어를 잘라내거나 채워야 합니다. |
| **장면 밀도** | "one idea per scene" | 페이스리스 장면에는 애니메이션할 새로 만든 초점이 하나 있습니다. 아이디어가 둘이면 그 주변에 움직임을 만들 것이 없습니다. 텍스트 덩어리로 읽힙니다. |
| **관점** | "concept" / "how-to" / "listicle" / "story" | 관점이 이야기의 형태를 결정합니다. 워크플로는 여러분의 문단을 순서대로 읽는 대신 그 형태로 재구성합니다. |
| **캡션 스타일** | "embedded captions, keywords highlighted in the accent color" | 캡션은 영상에 구워 넣습니다. 강조 색을 이름으로 지정하면 기본 필에 맡기는 대신 팔레트에 맞춰집니다. |
| **팔레트** | "brand color #FF5533 on off-black" | 빌려올 사이트가 없으므로 프리셋이 전체 팔레트를 제공합니다. 이름 있는 강조색과 바탕색이 이를 개인화합니다. |
| **음성** | "male TTS voice, calm" / "warm female voice" | 성별과 톤은 프롬프트 단어입니다. 제공자는 워크플로의 결정입니다. |

<Tip>
  장면 밀도는 여기서 품질을 가장 크게 좌우하는 요소입니다. "One idea per scene"은 빽빽한 문단을 리듬 있는 순서로 바꿉니다. 워크플로는 이를 맞추기 위해 텍스트를 재배열하고 압축합니다. 그래서 설명 영상이 낭독이 아니라 가르침이 됩니다.
</Tip>

## 변형

<AccordionGroup>
  <Accordion title="30초 가로형 주제 설명 영상 (16:9)">
    > /faceless-explainer Make a \~30-second 1920x1080 explainer on how HTTPS keeps a request private, for a non-technical audience — the takeaway: your data is sealed before it leaves the browser. Concept angle: one idea per scene, big geometric type, a simple lock-and-key diagram as the centerpiece (swap the metaphor with the topic). Near-black ink on off-white with a deep-blue accent. Female TTS voice, warm and clear. Embedded captions, key terms highlighted in the accent color.

    더 짧은 런타임, 유튜브나 임베드를 위한 가로형입니다. 장면이 적으면 주제를 압축해야 합니다. 핵심 메시지를 이름으로 말하면 워크플로가 무엇을 남길지 알게 됩니다.

    <DocsVideo title="HyperFrames video: Variant Explainer Landscape" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/variant-explainer-landscape.mp4#t=0.1" loop />

    *주제를 HTTP 캐싱으로 바꾸고(캐시 다이어그램을 비유로 사용) 이 프롬프트에서 렌더링한 결과물, 편집하지 않음 — 내레이션이 길이를 정하므로 26초입니다.*
  </Accordion>

  <Accordion title="리스티클">
    > /faceless-explainer Make a \~45-second 1080x1920 listicle: "5 habits of fast-shipping teams". Listicle angle — one habit per scene, each with a big number and a one-line label, escalating energy toward #1. Off-black with a lime accent. Male TTS voice, upbeat. Embedded captions, the habit label highlighted each scene.

    리스티클 관점은 각 항목에 자신만의 장면을 줍니다. 모든 장면이 같은 숫자와 라벨 형태를 재사용합니다. 결과는 점 목록의 벽이 아니라 카운트다운으로 읽힙니다.
  </Accordion>

  <Accordion title="다이어그램이 있는 how-to">
    > /faceless-explainer Make a \~60-second 1920x1080 how-to on setting up a CI pipeline, for developers. How-to angle: one step per scene, each built around a simple node-and-arrow diagram that draws on as the narration explains it. Charcoal with a teal accent. Calm male TTS voice. Embedded captions, the step name highlighted.

    how-to는 다이어그램을 핵심 시각 요소로 삼습니다. 단계마다 다이어그램의 *형태*를 설명하세요. "node-and-arrow"(노드와 화살표), 또는 "왼쪽에서 오른쪽으로 차오르는 파이프라인"처럼 말입니다. 구체적인 내용은 워크플로가 만들게 하세요.
  </Accordion>
</AccordionGroup>

## 흔한 실패 모드

**"60 seconds" 대신 "\~60 seconds".** [제품 출시 페이지](/prompting/product-launch#common-failure-modes)와 같은 규칙입니다. 여기서는 스크립트 전체가 영상이므로 더 크게 작용합니다. 제공된 스크립트의 말해지는 길이는 TTS가 렌더링되기 전에는 알 수 없습니다.

* ❌ `a 60-second explainer from this text: ...`
* ✅ `a ~60-second explainer from this text: ...`

**장면에 아이디어를 쑤셔 넣기.** 모든 페이스리스 시각 요소는 하나의 초점을 중심으로 만들어집니다. 장면이 과부하되면 애니메이션할 분명한 대상이 없습니다.

* ❌ `explain all five caching layers in one scene`
* ✅ `one idea per scene — one caching layer at a time`

**실제 이미지를 캡처하거나 가져오라고 요청하기.** 캡처 단계는 없습니다. 페이스리스 설명 영상은 시각 요소를 만들어 냅니다.

* ❌ `pull screenshots from the site and explain the feature`
* ✅ 사이트나 제품 영상이라면 [`/product-launch-video`](/prompting/product-launch)를 사용하세요

**중요하게 여기는데 룩을 지정하지 않기.** 읽어 올 브랜드가 없으므로 프리셋이 팔레트를 고릅니다. 색이 있다면 이름을 말하세요.

* ❌ `make it look on-brand`
* ✅ `brand color #FF5533 on off-black`

이 레벨이 활용하는 워크플로는 [페이스리스 설명 영상](/guides/faceless-explainer)에 문서화되어 있습니다. 무엇을 입력으로 받는지, 빌드 전에 무엇을 묻는지, 무엇을 반환하는지 설명합니다.

*다음: [코드 변경과 PR](/prompting/code-and-prs) — 빈 페이지 대신 병합된 GitHub PR을 워크플로에 가리키기.*


## 관련 주제

- [페이스리스 설명 영상 만들기](/guides/faceless-explainer.md)
- [검증된 예시 프롬프트](/prompting/examples.md)
- [코드 변경과 PR](/prompting/code-and-prs.md)


이 문서는 [Mintlify](https://mintlify.com), 개발자 문서 플랫폼으로 빌드되고 호스팅됩니다.
