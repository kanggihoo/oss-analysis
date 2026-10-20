> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져오세요.
> 더 살펴보기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾으세요.

# 데이터와 지도

> 애니메이션 차트, 카운트업 통계, 지도를 프롬프트하세요. 지역을 강조하고, 흐름을 그리고, 버블 크기를 정할 수 있습니다. 또는 차트를 직접 그려서 완전한 통제권을 가질 수도 있습니다.

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

Level 3의 6장면짜리 SaaS 설명 영상은 `cinematic-zoom`으로 가격 공개 장면에 들어가며 끝났습니다. 실제 숫자가 할 수 있는 역할을 전환 효과가 대신한 것입니다. 이 장은 카메라 움직임만 주는 대신, 그 공개 장면에 실제 애니메이션 차트나 카운트업 통계를 넣는 방법을 다룹니다.

숫자와 지리는 "무슨 데이터인가"와 "어떻게 움직이는가"를 따로 결정해야 하는 두 가지 주제입니다. [Data](/catalog/blocks/data-chart) 블록은 값을 넣기만 하면 되는 다듬어진 차트나 지도를 줍니다. 카운트업 [쇼케이스](/catalog/blocks/apple-money-count) 블록은 주행계식 숫자 롤링과 화려한 연출 순간을 처리합니다. 여기의 모든 내용은 [단일 프롬프트 골격](/prompting/anatomy)에 그대로 끼워 넣습니다. 데이터는 "copy" 슬롯에, 블록 이름은 "technique"에 들어갑니다.

### 차트: 블록을 지정하거나 직접 그리기

차트를 얻는 방법은 두 가지이며, 선택의 기준은 통제권입니다.

* **[`data-chart`](/catalog/blocks/data-chart)를 지정하면** 만들어 둔 애니메이션 막대+선 차트를 얻습니다. 순차적으로 나타나는 공개 효과, 값 라벨, NYT 스타일 타이포그래피가 들어 있으며, 여기에 여러분의 숫자를 넣으면 됩니다. 빠르고 일관되며 디자인 결정이 필요 없습니다.
* **"hand-draw everything — no chart library"라고 말하면** 에이전트가 대신 인라인 SVG와 GSAP로 차트를 만듭니다. 블록의 세련됨은 포기하는 대신 모양, 움직임, 레이아웃을 완전히 통제할 수 있습니다. 예를 들어 애니메이션 도중 순위가 바뀌는 막대 레이스, 카운터에 맞춰 그려지는 호, 어떤 라이브러리에도 없는 레이아웃 같은 것들입니다.

데이터는 인라인으로 주거나 파일로 줄 수 있습니다. 작은 시리즈는 프롬프트에 바로 넣고, CSV는 빌드 시점에 참조되어 파싱됩니다(결정론적으로 유지하세요. [렌더링 시점 fetch](/concepts/determinism)는 안 됩니다).

> /motion-graphics 12-second 1920x1080 video. Title "Most-used languages" with the subtitle "share of respondents, 2026 survey". Turn this into an animated bar chart with a staggered reveal and value labels counting up on each bar, each label suffixed `%`:
>
> ```
> Python 41, TypeScript 33, Rust 19, Go 14, Java 9
> ```
>
> Use the `data-chart` registry block. No audio.

<DocsVideo title="HyperFrames video: Chart Languages" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/chart-languages.mp4#t=0.1" loop />

*위 프롬프트를 편집 없이 렌더링한 결과 — 다음 막대가 이미 자라고 있는 동안 라벨이 카운트업됩니다.*

> /motion-graphics 10-second 1920x1080 video, dark slate background. Title "Top languages 2026" top-left. Five horizontal bars (Python, TypeScript, Rust, Go, Java) grow from zero with staggered starts, overtaking each other twice mid-animation; each bar has a right-edge value label counting up to its final %. End state holds 2s, alive — the leader pulses once, timed to finish exactly on the last frame, never a frozen tail. Hand-author the marks (no chart library) and make them *look* hand-drawn: wobbly ink strokes, not clean rectangles. Say which two pairs overtake and when, or the reveal will land on a different number of crossings each run. No audio.

<DocsVideo title="HyperFrames video: Barrace Handdrawn" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/barrace-handdrawn.mp4#t=0.1" loop />

*위 프롬프트를 편집 없이 렌더링한 결과 — 직접 작성한 잉크 획, 차트 라이브러리 없음. 순위가 두 번 바뀝니다.*

**블록을 쓸지 말지를 분명히 하세요. 암묵적으로 두지 마세요.** 결정 없이 "이 데이터를 애니메이션으로 만들어 줘"라고만 하면, 일반 블록과 즉흥적인 레이아웃 사이에서 결과가 흔들립니다.

* ❌ `animate this CSV as a chart`
* ✅ `turn this CSV into an animated bar chart — use the data-chart registry block` **또는** `…hand-draw everything, no chart library`

**요청한 애니메이션에 맞게 숫자 형식을 정하세요.** 주행계식 카운트업에는 고정된 자릿수 열이 필요합니다. `$0 → $4.2M` 같은 범위는 어색한 `$0.0M` 시작을 강요합니다.

* ❌ `counts from $0 to $4.2M`
* ✅ `counts up to $4.2M`

### 카운트업 통계

단 하나의 대표 숫자에는 [`apple-money-count`](/catalog/blocks/apple-money-count)가 Apple 스타일의 금융 카운터입니다. \$0에서 롤링하고, 초록색으로 번쩍이며, 소리와 함께 돈 아이콘이 터집니다. 그 정확한 화려한 연출을 원하면 이름으로 지정하고, 여러분의 서체로 맨 숫자만 원하면 직접 그리세요.

> /motion-graphics 6-second 1920x1080 video, dark navy background. Beat 1 (0-1s): label "ARR" fades up small, top-center. Beat 2 (1-4s): a giant number counts up to \$4.2M with an odometer roll, easing out as it lands. Beat 3 (4-6s): "+312% YoY" stamps in below in green, then settles into a gentle ambient idle. Use the `apple-money-count` registry block as base. No narration.

<DocsVideo title="HyperFrames video: Money Count" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/money-count.mp4#t=0.1" loop />

*위 프롬프트를 편집 없이 렌더링한 결과.*

### 지도: 요청을 지도에 맞추기

지도 블록마다 답하는 지리적 질문이 다릅니다. 지도가 *무엇을 위한* 것인지 말하고, 맞는 블록을 지정하세요.

| 원하는 것… | 이 블록 이름 | 길이 |
| - | - | - |
| 미국 주를 값에 따라 음영 처리(코로플레스) | [`us-map`](/catalog/blocks/us-map) | 12s |
| 미국 도시를 값에 따라 크기 조절(비례 버블) | [`us-map-bubble`](/catalog/blocks/us-map-bubble) | 12s |
| 미국 도시 사이의 연결선 그리기(출발지→도착지) | [`us-map-flow`](/catalog/blocks/us-map-flow) | 12s |
| 미국 주를 같은 가중치의 육각형 격자로 표시 | [`us-map-hex`](/catalog/blocks/us-map-hex) | 10s |
| 스페인을 자치 지방별로 음영 처리 | [`spain-map`](/catalog/blocks/spain-map) | 12s |
| 세계 지도를 국가별로 음영 처리 | [`world-map`](/catalog/blocks/world-map) | 14s |

미국 지도의 표현 방식은 조합할 수 있습니다. "주를 음영 처리*하고* 두 도시 사이에 흐름을 그려 달라"고 하면 하나의 컴포지션이 나옵니다. 에이전트가 소스 단계에서 블록들을 공통 투영법으로 합쳐, 호(arc)가 코로플레스의 주 위에 정확히 떨어지게 합니다.

> /motion-graphics 12-second 1920x1080 video. A US choropleth shades states by adoption rate with staggered reveals and a gradient legend, then connection arcs draw between San Francisco, Austin, and New York. Use the `us-map` and `us-map-flow` registry blocks. No audio.

<DocsVideo title="HyperFrames video: Validate Us Map Flows" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-us-map-flows.mp4#t=0.1" loop />

*위 프롬프트를 편집 없이 렌더링한 결과.*

<Note>
  지도 블록은 실행 시점에 지리 데이터를 CDN에서 가져오는데, 이는 결정론적 렌더링 규칙을 어깁니다. 그래서 에이전트는 투영된 기하 데이터를 대신 컴포지션에 구워 넣습니다. 이것을 따로 요청할 필요는 없습니다. 지도를 올바르게 만드는 과정의 일부이기 때문입니다.
</Note>

**그냥 "지도"라고만 하지 말고 표현 방식을 고르세요.** 코로플레스(색), 버블(크기), 육각형(동일 가중치), 흐름(호)은 같은 데이터로도 서로 다른 이야기를 전합니다.

* ❌ `put California's number on a US map`
* ✅ `size each city as a proportional bubble` → `us-map-bubble`, 또는 `shade each state by value` → `us-map`

**지역의 블록을 지정하세요.** 코로플레스는 지역별로 고정된 투영법을 가집니다(`spain-map`은 D3 conic conformal, `world-map`은 Natural Earth입니다). "아무 국가"나 그릴 수 있는 일반 지도는 없습니다.

* ❌ `a map of Spain's regions` (투영법과 지리를 우연에 맡깁니다)
* ✅ `use the spain-map registry block`

### 경로와 비행

지점에서 지점으로 가는 여정, 즉 지도 위에 그려지며 착륙 비트로 끝나는 경로에는 [`nyc-paris-flight`](/catalog/blocks/nyc-paris-flight)가 Apple 스타일의 비행 애니메이션입니다. 비행기가 뉴욕 → 파리로 날아가며, 마커 원, 착륙 팝, 효과음이 나옵니다. 이를 기반으로 쓰고, 프롬프트에서 시작점과 끝점을 다시 지정하세요.

> /motion-graphics 6-second 1920x1080 video. A realistic map with a plane flying between two cities, a marker circle at the origin, and a landing pop at the destination. Use the `nyc-paris-flight` registry block as base — the route runs New York (JFK) → Paris (CDG), labelled at both ends. Keep the block's own title card and route ticks. End on the settled map, not on the block's white-out hand-off frame. No audio.

<DocsVideo title="HyperFrames video: Flight Route" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/flight-route.mp4#t=0.1" loop />

*위 프롬프트를 편집 없이 렌더링한 결과.*

**경로는 정적인 호가 아니라 이동수단이 있는 흐름입니다.** 비행기와 소리 없이 그려진 호만 원하면 `us-map-flow`이고, 여정 연출까지 원하면 `nyc-paris-flight`입니다.

* ❌ `draw a line from NYC to Paris` (호만 그릴지 전체 비행을 그릴지 모호합니다)
* ✅ `a plane flies the route with a landing pop` → `nyc-paris-flight`

### 다음으로 볼 곳

* [단일 프롬프트의 구조](/prompting/anatomy) — 골격과, 주행계에 고정 자릿수 열이 필요한 이유.
* [복사-붙여넣기 예제](/prompting/examples) — 가져다 고칠 수 있는 막대 차트 레이스와 통계 타일 프롬프트.
* [생성된 아트워크](/prompting/generated-artwork) — 직접 그린 HTML/CSS/SVG가 빛나는 곳과 그렇지 않은 곳.
* [명세 다이얼](/prompting/specification-dial) — 블록을 지정할지 직접 그릴지 결정하기.

<Note>
  **캡스톤 흐름** — [Level 7 영상](/prompting/capstone)의 Measure와 Everywhere 영역은 이 장을 처음부터 끝까지 그대로 보여 줍니다. 대표 숫자가 자리 잡는 동안 `data-chart` 막대가 타임라인 와이어에서 솟아오르고, 이어서 같은 와이어가 `world-map` 블록의 실제 클라우드 렌더 영역 위에 대원(great-circle) 호가 됩니다(아래 영상에서 잘라낸 부분).
</Note>

이 절은 작품을 완성시키는 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)의 한 구절입니다. 여러분의 영상에 가져다 쓸 수 있는 프롬프트 문장입니다.

> **Measure (14–21s).** The wire becomes a chart baseline (same line, same thickness — no cut): adapt the **`data-chart` registry block** — six labeled bars rise from the wire itself on spoken cues while a hero numeral counts up beside them in huge tabular mono: **50+ CATALOG BLOCKS** (the real registry count) \[…]
>
> **Everywhere (21–28s).** The wire arcs and the ground falls away: adapt the **`world-map` registry block** — the dotted world map scrolls beneath while the wire becomes a great-circle route arcing across it. Real render infrastructure, truthfully labeled: pulses light up at AWS and Google Cloud regions (US-EAST-1 · EU-WEST-1 · AP-SOUTH-1) with a "CLOUD RENDER · LAMBDA + CLOUD RUN" kicker \[…]

<DocsVideo title="HyperFrames video: Capstone Region Data Map" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-data-map.mp4#t=0.1" loop />

*이 절을 렌더링한 결과 — 완성된 영상에서 잘라낸 영역입니다.*

*다음: [오버레이와 하단 자막](/prompting/overlays-and-lower-thirds) — 장면 자체를 렌더링하는 블록이 아니라, 영상이나 장면 위에 얹히는 시간 블록을 지정하는 방법.*


## 관련 주제

- [세계 지도](/catalog/blocks/world-map.md)
- [스페인 지도](/catalog/blocks/spain-map.md)
- [미국 지도](/catalog/blocks/us-map.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 만들어지고 호스팅됩니다.
