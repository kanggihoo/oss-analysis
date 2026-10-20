> ## 문서 인덱스
> 전체 문서 인덱스는 다음 주소에서 가져올 수 있습니다: https://hyperframes.heygen.com/llms.txt
> 더 살펴보기 전에 이 파일로 사용할 수 있는 모든 페이지를 먼저 찾아볼 수 있습니다.

# 전환 효과

> 에너지와 분위기를 이름이 있는 셰이더 및 CSS 전환 블록에 대응시키고, 이음매마다 프롬프트로 지정합니다.

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

[모션](/prompting/motion)의 여덟 가지 규칙은 한 장면 안에서 일어나는 일을 기준으로 만들어졌습니다. 규칙 2의 카메라와 규칙 3의 겹침은 장면 *사이*에서도 적용됩니다. 전환 효과는 나중에 덧붙이는 별도 기능이 아니라, 같은 문법을 컷 자체에 적용한 것입니다.

## 전환 효과가 하는 일과 발동 시점

전환 효과는 두 장면이 어떤 관계인지 시청자에게 알려 줍니다. 크로스페이드는 "이어진다"를, 휩 팬은 "다음 요점"을, 번(burn)은 "무언가 바뀌었다"를 뜻합니다. 장면이 여러 개인 대부분의 합성 영상에는 전환 효과가 필요합니다. 근거 없이 바뀌는 장면은 의도하지 않은 점프 컷처럼 보이기 때문입니다([규칙과 안티패턴](/prompting/rules-and-anti-patterns) 참고). 다른 요소가 연속성을 담당할 때는 전환 없는 단순 컷도 정당합니다. 예를 들어 같은 도형을 이용한 매치 컷, 비트 그리드, 화면에 계속 남아 있는 소품이 이에 해당하며, 이는 [슬라이드쇼 피하기](/prompting/motion#avoiding-the-slideshow)의 대안 표에 정리되어 있습니다. 스킬은 기본으로 전환 효과를 추가하므로, 장면 변화, 크로스페이드, 와이프, 공개(reveal), 또는 "따뜻한", "냉철한", "글리치" 같은 분위기를 설명하거나 블록 이름을 직접 말하면 이 층이 작동합니다.

두 가지 계열이 모두 주요 기능입니다.

* **[셰이더 전환](/catalog/blocks/cross-warp-morph)**은 WebGL 캔버스에서 두 장면을 픽셀 단위로 합성합니다. CSS로는 불가능한 방식으로 워프, 디졸브, 모핑을 합니다. *전환 자체*가 하나의 순간일 때(히어로 공개, 무게감 있는 주제 전환) 사용합니다.
* **CSS 전환**은 장면 컨테이너에 불투명도, 변형, clip-path, 필터를 적용합니다. 더 단순하고 가볍습니다. 콘텐츠가 그대로 이어지는 일반적인 장면 변화의 60–70%에 사용합니다.

쉬운지가 아니라 원하는 효과로 고르십시오. [어휘](/prompting/vocabulary)의 전환 표도 함께 참고하십시오.

<Note>
  여기 연결된 카탈로그 페이지는 각 효과를 보여 주는 독립 데모입니다. 실제 다중 장면 빌드에서는 에이전트가 `@hyperframes/shader-transitions` 패키지(`HyperShader.init`)를 통해 같은 효과를 연결합니다. 이를 직접 말할 필요는 없습니다. 전환 이름만 말하면 충분합니다.
</Note>

## 에너지 → 전환

대부분의 장면 변화에는 **주 전환 하나**를 고르고, 주제가 바뀌는 곳이나 절정에는 한두 개의 강조 전환을 더합니다. 이음매마다 다른 전환을 쓰지 마십시오. 혼란스러워 보이고 디자인처럼 보이지 않습니다.

| 에너지 | 셰이더 주 전환 | CSS 주 전환 | 느낌 |
| - | - | - | - |
| **차분함** (웰니스, 브랜드 스토리, 럭셔리) | [`cross-warp-morph`](/catalog/blocks/cross-warp-morph), [`thermal-distortion`](/catalog/blocks/thermal-distortion) | [`transitions-blur`](/catalog/blocks/transitions-blur), [`transitions-dissolve`](/catalog/blocks/transitions-dissolve) | 부드럽고 느리며 흐르는 |
| **중간** (기업, SaaS, 설명 영상) | [`whip-pan`](/catalog/blocks/whip-pan), [`cinematic-zoom`](/catalog/blocks/cinematic-zoom) | [`transitions-push`](/catalog/blocks/transitions-push), [`transitions-cover`](/catalog/blocks/transitions-cover) | 깔끔하고 방향성이 있으며 단호한 |
| **높음** (프로모션, 스포츠, 음악, 출시) | [`ridged-burn`](/catalog/blocks/ridged-burn), [`glitch`](/catalog/blocks/glitch), [`chromatic-radial-split`](/catalog/blocks/chromatic-radial-split) | [`transitions-scale`](/catalog/blocks/transitions-scale), [`transitions-destruction`](/catalog/blocks/transitions-destruction), [`transitions-light`](/catalog/blocks/transitions-light) | 빠르고 강렬하며 공격적인 |

## 분위기 → 전환

에너지는 템포를 정하고, 분위기는 의미를 정합니다. 브랜드의 느낌을 설명하면 에이전트가 맞는 블록을 고릅니다.

| 분위기 | 셰이더 | CSS |
| - | - | - |
| **따뜻함 / 호감** | [`light-leak`](/catalog/blocks/light-leak), [`thermal-distortion`](/catalog/blocks/thermal-distortion), [`cross-warp-morph`](/catalog/blocks/cross-warp-morph) | [`transitions-light`](/catalog/blocks/transitions-light), [`transitions-blur`](/catalog/blocks/transitions-blur) |
| **차가움 / 냉철함** | [`gravitational-lens`](/catalog/blocks/gravitational-lens) | [`transitions-mechanical`](/catalog/blocks/transitions-mechanical), [`transitions-grid`](/catalog/blocks/transitions-grid) |
| **에디토리얼 / 매거진** | [`whip-pan`](/catalog/blocks/whip-pan) | [`transitions-push`](/catalog/blocks/transitions-push) |
| **테크 / 미래지향** | [`glitch`](/catalog/blocks/glitch), [`chromatic-radial-split`](/catalog/blocks/chromatic-radial-split) | [`transitions-grid`](/catalog/blocks/transitions-grid) |
| **긴장감 / 날카로움** | [`ridged-burn`](/catalog/blocks/ridged-burn), [`glitch`](/catalog/blocks/glitch), [`domain-warp-dissolve`](/catalog/blocks/domain-warp-dissolve) | [`transitions-distortion`](/catalog/blocks/transitions-distortion) |
| **장난스러움 / 재미** | [`ripple-waves`](/catalog/blocks/ripple-waves), [`swirl-vortex`](/catalog/blocks/swirl-vortex) | [`transitions-3d`](/catalog/blocks/transitions-3d), [`transitions-radial`](/catalog/blocks/transitions-radial) |
| **드라마틱 / 시네마틱** | [`cinematic-zoom`](/catalog/blocks/cinematic-zoom), [`gravitational-lens`](/catalog/blocks/gravitational-lens), [`domain-warp-dissolve`](/catalog/blocks/domain-warp-dissolve) | [`transitions-scale`](/catalog/blocks/transitions-scale) |
| **프리미엄 / 럭셔리** | [`cross-warp-morph`](/catalog/blocks/cross-warp-morph), [`thermal-distortion`](/catalog/blocks/thermal-distortion) | [`transitions-blur`](/catalog/blocks/transitions-blur), [`transitions-dissolve`](/catalog/blocks/transitions-dissolve) |
| **레트로 / 아날로그** | [`light-leak`](/catalog/blocks/light-leak) | [`transitions-light`](/catalog/blocks/transitions-light) |

특수 목적 이음매도 있습니다. 임팩트 비트에서 밝게 끊을 때는 [`flash-through-white`](/catalog/blocks/flash-through-white)를, 히어로 샷으로 깔끔하게 열 때는 [`sdf-iris`](/catalog/blocks/sdf-iris)를 씁니다.

## 예시 프롬프트

블록과 이음매를 함께 이름으로 지정하십시오. 전환 효과는 대개 에이전트에게 맡기는 것보다 이음매별로 직접 지정하는 것이 더 낫습니다.

> /general-video Six-scene SaaS explainer. Use [`whip-pan`](/catalog/blocks/whip-pan) as the primary transition between related points, and one [`cinematic-zoom`](/catalog/blocks/cinematic-zoom) into the final pricing reveal. Medium energy, \~0.4s each.

<DocsVideo title="HyperFrames video: Validate Transitions" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-transitions.mp4#t=0.1" loop />

*위 프롬프트로 렌더링했으며 편집하지 않았습니다. 네 이음매에 whip-pan을, 가격 공개 장면에 cinematic-zoom을 적용했습니다.*

> Between beats 2 and 3, transition with [`swirl-vortex`](/catalog/blocks/swirl-vortex); keep every other seam on a plain blur crossfade.

> Warm transitions for this wellness brand — [`light-leak`](/catalog/blocks/light-leak) between scenes, nothing sharp or mechanical. Slow, 0.6–0.8s.

> Music promo, high energy. [`glitch`](/catalog/blocks/glitch) on the phrase changes, [`ridged-burn`](/catalog/blocks/ridged-burn) on the drop. Fast cuts, 0.15–0.25s.

## 조정 항목

* **지속 시간**은 에너지를 따릅니다. 차분함 0.5–0.8초, 중간 0.3–0.5초, 높음 0.15–0.3초입니다. 숫자를 말하면 그 값으로 고정됩니다.
* **주 전환 + 강조 전환.** 주 전환 하나가 대부분의 이음매를 맡고, 가장 강한 강조 전환은 절정에 씁니다. 배분을 명시하십시오(예: "전체에 `whip-pan`, 공개 장면에 `ridged-burn` 하나").
* **이음매별 배치.** "음절이 바뀔 때", "비트 2와 3 사이", "마지막 장면으로 들어갈 때"처럼 말하면 전환을 특정 컷에 묶을 수 있습니다.
* **블러 강도**(CSS 블러 크로스페이드): 차분함에는 강하게(20–30px), 높은 에너지에는 가볍게(3–6px) 줍니다.
* **이징 프리셋:** `snappy`, `smooth`, `gentle`, `dramatic`, `instant`, `luxe`는 조정된 지속 시간/이징 쌍으로 매핑됩니다.

## 실패 유형

**나가는 장면을 페이드 아웃한 뒤 다음 장면을 페이드 인하지 마십시오.** 렌더러는 각 장면의 최종 상태를 유지하므로, 명시적인 페이드 아웃 뒤에 등장 애니메이션을 넣으면 중간이 꺼지는 점프 컷으로 렌더링됩니다. 전환이 되지 않습니다. 전환 자체가 퇴장이고, 두 장면은 같은 순간에 넘어갑니다.

* ❌ `fade scene 1 out, then fade scene 2 in`
* ✅ `cross-warp-morph from scene 1 to scene 2`

**이음매마다 다른 전환을 요청하지 마십시오.** 컷마다 새 효과가 나오면 잡음처럼 읽힙니다. 일관성이 있어야 하나뿐인 강한 강조가 살아납니다.

* ❌ `use a different transition between each scene`
* ✅ `whip-pan as the primary, one glitch on the hero reveal`

**톤이 중요하면 "전환 추가"를 한정 없이 요청하지 마십시오.** 근거 없는 요청에는 무난한 기본값이 나옵니다. 브랜드의 느낌이 핵심이라면 에너지나 분위기를 명시하십시오([명세 다이얼](/prompting/specification-dial) 참고).

* ❌ `add some transitions`
* ✅ `medium-energy editorial transitions — whip-pan primary`

**전환 이름을 지어내지 마십시오.** 존재하는 것은 [셰이더](/catalog/blocks/cross-warp-morph) 및 CSS 전환 그룹에 있는 블록뿐입니다. 없는 이름(`page-curl`, `star-iris`)을 쓰면 에이전트가 원시 GLSL이나 지원되지 않는 CSS 효과를 추측하게 됩니다.

* ❌ `add a page-curl transition`
* ✅ 실제 블록을 고릅니다. 예: 아이리스 공개에는 `sdf-iris`

<Note>
  **캡스톤 흐름** — [레벨 7 영화](/prompting/capstone)는 셰이더 이음매를 정확히 하나만 허용합니다. 카메라가 `sdf-iris` 렌즈를 통과해 Surface 영역으로 들어가며(아래 영화에서 잘라낸 장면), 아이리스 너머로 타임라인 와이어가 내내 보입니다. 이는 컷이 아니라, 여정이 통과하는 렌즈입니다.
</Note>

이 절은 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)에서 이 장면을 살려 주는 문장입니다. 여러분의 영상에도 그대로 가져다 쓸 수 있는 프롬프트 표현입니다.

> SANCTIONED SEAM #1: the camera pushes through an **`sdf-iris` shader transition** — the iris opens ONTO the continuation of the same wire (the wire is visible through the iris throughout; this is a lens the journey passes through, not a cut).

<DocsVideo title="HyperFrames video: Capstone Region Surface" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-surface.mp4#t=0.1" loop />

*위 문장을 렌더링한 결과입니다. 완성된 영화에서 잘라낸 영역입니다.*

*다음: [코드 애니메이션](/prompting/code-blocks) — 블록 이름을 지정하고 실제 코드를 붙여 워크스루, diff, 터미널 장면을 만드는 방법입니다.*


## 관련 주제

- [Dissolve Transitions](/catalog/blocks/transitions-dissolve.md)
- [Distortion Transitions](/catalog/blocks/transitions-distortion.md)
- [Other Transitions](/catalog/blocks/transitions-other.md)


이 문서는 개발자 문서 플랫폼인 [Mintlify](https://mintlify.com)로 만들어지고 호스팅됩니다.
