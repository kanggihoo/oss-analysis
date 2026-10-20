> ## Documentation Index
> 전체 문서 색인은 다음 주소에서 가져올 수 있습니다: https://hyperframes.heygen.com/llms.txt
> 다른 페이지를 살펴보기 전에 이 파일로 사용 가능한 모든 페이지를 찾아보세요.

# 색상 보정(Color grading)과 필름 효과

> 고정된 순서의 파이프라인으로 미디어를 보정합니다. 톤 작업, 색조 키, 인쇄 및 아날로그 처리를 다루며, 같은 처리라도 원본 소스가 페이로드보다 중요한 이유를 설명합니다.

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

이 장까지는 이미지를 만드는 과정이었습니다. 이번 장은 이미지가 *어떤 매체로 촬영된 것처럼 보이게 할지*를 바꿉니다. 보정은 마지막에 덧붙이는 장식이 아니라 매체에 대한 주장입니다. 이것은 테이프에서 나온 영상이고, 인쇄물이고, 진공관 화면이고, 특정 필름을 넣은 카메라로 찍은 영상이라는 주장입니다. 시청자는 그 주장을 즉시 읽어내며, 여러분이 의도했든 아니든 그렇게 읽습니다.

보정은 단일 `<img>` 또는 `<video>`에 `data-color-grading` 페이로드를 통해 붙습니다. 텍스트, 카드, 자막에는 절대 영향을 주지 않고, 보정이 붙은 미디어 요소의 픽셀만 바꿉니다. 전체 규격은 [Color Grading 가이드](/guides/color-grading)에 있으며, 이 장은 무엇을 *요청해야 하는지*와 이 프롬프트들이 잘못되는 세 가지 경우를 다룹니다.

## 소스에는 잃을 것이 있어야 합니다

이 실패는 시간을 가장 많이 잡아먹지만 프롬프트에서는 보이지 않습니다. 여기 나오는 처리는 모두 무언가를 *제거*하는 방식으로 작동하므로, 장면에 제거될 대상이 있어야 합니다.

이 페이지를 만들면서 얻은 예시 세 가지입니다. 셋 모두 기술적으로는 실행되었지만 눈에 띄는 것은 아무것도 가르치지 못했습니다.

| 처리 | 잘못된 소스 | 아무것도 보이지 않은 이유 |
| - | - | - |
| 색조 키(Hue key) — 한 색만 유지 | 주방의 토킹 헤드 | 피부가 곧 빨간 대역입니다. 빨간색을 키잉하자 얼굴이 남았고, 픽셀의 6%만 움직였습니다. |
| 2색 인쇄(Two-ink press) | 흰 종이 위의 검은 글자 | 이미 두 가지 색입니다. 줄일 것이 없습니다. |
| Kuwahara — 회화풍 | 초점이 흐린 사무실 | 가장자리를 보존하는 평활화 필터는 보존할 가장자리가 있어야 합니다. |

세 가지 모두 페이로드가 아니라 영상을 바꿔서 해결했습니다. 그래서 프롬프트에서 피사체를 지정하되, 효과가 사용하는 속성의 관점에서 지정하세요. *"색이 밀도 높고 가장자리가 밀도 높은 피사체를 고르세요"*, *"배경은 중립 회색이 아니라 색을 담고 있어야 합니다"*처럼 말입니다.

## 파이프라인 순서는 고정되어 있습니다

섹션은 작성 방식과 관계없이 정해진 순서대로 적용됩니다.

```text theme={null}
adjust → wheels → curves → hueCurves → secondaries → lut → details → effects
```

이것은 겉보기 문제가 아닙니다. `adjust`에 있는 전역 `saturation: -0.9`는 `secondaries`보다 *먼저* 실행됩니다. 그러므로 한 색을 지키려고 하는 색조 기준 선택 영역은 이미 채도가 빠진 색을 발견하고, 되살릴 것이 없게 됩니다. 한 색을 채도 저하 속에서도 살리고 싶다면, 전체 채도를 낮춘 뒤 다시 칠하는 대신 `hueCurves`에서 그 색을 키잉하세요.

## 보정은 위치가 아니라 값으로 선택합니다

선택 영역은 색상(hue), 채도(saturation), 휘도(luma)를 기준으로 합니다. 마스크, 도형, 추적 영역은 없고, 공간적으로 변하는 유일한 조절인 `vignette`는 프레임 중앙에 고정되어 있습니다. 프레임의 *일부*만 처리하려면 그 부분을 별도 레이어로 분리한 다음 그 레이어를 보정하세요. 작성 예시가 포함된 이 패턴은 [프레임 일부로 보정 제한하기](/reference/color-grading#limit-a-grade-to-part-of-the-frame)에 있습니다.

***

## 피사체와 배경 분리하기

보정이 할 수 있는 가장 유용한 일은 룩을 만드는 것이 아닙니다. 한 부분은 보호하면서 다른 부분은 처리하는 것입니다. 이를 위해서는 매트(matte)가 필요하고, 따라서 두 개의 레이어가 필요합니다.

### 배경은 보정하고, 얼굴은 보호하기

> 토킹 헤드 클립을 가져와 피사체와 방을 분리하세요. 사람은 사진처럼 그대로 두세요. 살결을 살짝 부드럽게 하는 처리와 약 3분의 1스톱 정도의 노출 추가만 하고, 피부에 효과처럼 보이는 것은 넣지 마세요. 대신 뒤의 방을 보정하세요. 4초에 걸쳐 하프톤 스크린을 올려서 공간이 작은 색 점들로 분해되게 하고, 창문이 밝아지도록 절제된 블룸을 함께 쌓아 올리세요. 두 효과 모두 0에서 시작해서 장면이 보정 없이 시작하게 하세요.

<DocsVideo title="HyperFrames video: Grade Matte Separation B0ef8e73" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-matte-separation-b0ef8e73.mp4#t=0.1" loop />

*방은 하프톤 스크린과 블룸을 받고, 피사체는 살결 부드러움 처리와 3분의 1스톱만 받습니다.*

주의할 점이 두 가지 있습니다. 배경 판(plate)으로는 피사체를 지운 판이 아니라 **원본 클립**을 쓰세요. 지운 판은 피사체가 있던 자리의 구멍이라서, 그 위에 페더링된 컷아웃을 올리면 어두운 테두리가 생깁니다. 그리고 컷아웃이 프리멀티플라이드 알파(premultiplied alpha)로 제공되면, 브라우저는 이를 스트레이트 알파로 합성해서 가장자리 픽셀을 두 번 곱하고 검은 윤곽선을 만듭니다. 이 경우 원본과 매트를 사용해 `ffmpeg alphamerge`로 다시 만드세요.

### 얼굴만 모자이크하기

> 판에서 피사체를 매트로 분리한 다음, 얼굴만 가리세요. 나머지 몸과 뒤의 방은 완전히 건드리지 마세요. 픽셀화(pixelation)는 장면 전체에서 약 절반 강도로 고정하세요. 램프도, 페이드 인도 없이요. 움직이면서 켜지는 가림은 효과로 읽히고, 그냥 켜져 있는 가림은 정책으로 읽힙니다. 가림 영역은 이목구비에 딱 맞추지 말고 넉넉하게 잡아서 헤어라인, 귀, 턱선까지 포함하세요.

<DocsVideo title="HyperFrames video: Grade Redaction Engaging Ec781f26" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-redaction-engaging-ec781f26.mp4#t=0.1" loop />

*얼굴은 픽셀화되고, 몸과 방은 그대로입니다. 이 영역은 페이로드 설정이 아니라 세 번째 레이어의 `clip-path`입니다.*

영역은 *세 번째* 레이어에 있는 `clip-path`에서 나옵니다. 이 레이어는 보정이 적용된 컷아웃의 두 번째 복사본이고, 보정되지 않은 복사본 위에 쌓입니다. 보정된 레이어가 곧 컷아웃이므로, 타원이 머리 바깥으로 넘쳐도 방은 건드리지 않습니다. 실루엣 바깥에는 칠할 것이 없기 때문입니다. 빠듯하게 말고 넉넉하게 잡으세요.

고정된 클립은 피사체가 거의 움직이지 않는 영상에서만 유지됩니다. 의존하기 전에 측정하세요. 여기서는 클립 전체에서 머리가 5.5px 움직였습니다. 실제로 움직임이 있는 영상은 HyperFrames 밖에서 만든 추적 매트가 필요합니다.

***

## 일부러 그림을 망가뜨리기

### 픽셀화, 디더링, 블룸

이미지를 해체하는 방법은 세 가지이고, 각각 다른 의미를 전달합니다. 픽셀화는 *가림(redaction)*으로 읽힙니다. 디더링은 *디스플레이가 고장 난 것*으로 읽힙니다. 블룸은 *빛이 센서를 압도한 것*으로 읽힙니다.

> 4초에 걸쳐 그림을 화면이 깨진 것처럼 열화시키세요. 디더링을 깨끗한 상태에서 중간 패턴 크기 0.85까지 올려서, 연속된 톤이 이산적인 양자화 레벨로 쪼개지게 하세요. 필터가 적용된 것이 아니라 디스플레이가 고장 난 것처럼 읽혀야 합니다.

<DocsVideo title="HyperFrames video: Grade Signal Loss Babe88ef" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-signal-loss-babe88ef.mp4#t=0.1" loop />

*깨끗한 상태에서 0.85까지 올라가는 디더링. 연속된 톤이 이산적인 레벨로 쪼개집니다.*

> 4초에 걸쳐 하이라이트를 날려 버리세요. 블룸을 0에서 3까지 올리세요. 취향 있는 하이라이트 보정을 훨씬 넘어서는 값입니다. 넓은 반경에서 빛이 창문 밖으로 번져 나가 프레임을 점점 삼키게 하세요. 은은한 광택이 아니라 범위의 끝을 보고 싶습니다.

<DocsVideo title="HyperFrames video: Grade Bloom Out 11531968" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-bloom-out-11531968.mp4#t=0.1" loop />

*하이라이트 보정을 훨씬 넘어 3까지 올린 블룸. 빛이 프레임을 삼킬 때까지 올라갑니다.*

<Warning>
  블룸은 계측 장비를 속이는 유일한 조절입니다. 강하게 주면 날아간 것처럼 보이지만, 측정상으로는 보정하지 않은 원본보다 *덜* 클리핑된 것으로 나옵니다. 이 번짐은 빛이 퍼지는 헐레이션(halation)이지 클리핑이 아니기 때문입니다. 어떤 클리핑 지표도 이를 잡아내지 못합니다. 블룸은 반드시 1:1로 판단하고, 썸네일로 판단하지 마세요.
</Warning>

### 뭉개지지 않는 회화풍

> 4초에 걸쳐 장면을 뭉개지 않고 그림으로 바꾸세요. Kuwahara 필터를 0에서 최대까지 램프하세요. 반경은 중간, 가장자리가 선명하게 남도록 선명도는 꽤 높게, 채도는 조금 낮춰서 필터가 아니라 붓질처럼 읽히게 하세요. 경계는 분명하게 유지되고, 평평한 영역은 붓 자국으로 매끄러워집니다. 색이 밀도 높고 가장자리가 밀도 높은 피사체를 고르세요. 평평한 피부나 초점이 흐린 배경에는 보존할 것이 없습니다.

<DocsVideo title="HyperFrames video: Grade Painterly Ffd5c0f9" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-painterly-ffd5c0f9-v2.mp4#t=0.1" loop />

*보존할 가장자리가 충분한 피사체에 풀 강도로 적용한 Kuwahara.*

***

## 인쇄와 색

### 두 가지 잉크

> 포스터를 두 가지 잉크로만 인쇄하세요. 거의 검은 네이비와 따뜻한 크림색을 중간 도트 크기로, 2색 인쇄기로 찍은 것처럼 하세요. 모든 색이 이 두 가지 색으로 모입니다. 4초에 걸쳐 원본 포스터에서 점점 올리고, 바로 전환하지 마세요. 이름 있는 팔레트 대신 정확한 헥스 값을 주세요.

<DocsVideo title="HyperFrames video: Grade Two Ink Press 3c5662f1" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-two-ink-press-3c5662f1-v2.mp4#t=0.1" loop />

*열 개의 색상 계열이 세 개로 모입니다. 밀도 높은 글자는 2색 축소의 가장 까다로운 시험입니다.*

글자는 2색 축소의 가장 가혹한 시험입니다. 작고 빽빽한 본문은 도트 스크린을 견디거나 얼룩으로 뭉개지는데, 그 차이는 한눈에 보입니다. 페이로드는 명시적인 헥스 배열을 받으며, 이름 있는 팔레트 id는 거부된다는 점에 유의하세요.

### 한 색만 남기고 나머지는 빼기

> 청록색 배경 위의 빨간 사과 한 개입니다. 사과의 색은 유지하고 나머지는 모두 빼세요. 빨강 바깥에서는 색상으로 키잉하고 어디서나 채도를 낮춰서, 배경은 완전히 중립 회색이 되고 사과는 원래 채도 그대로 남게 하세요. 사과를 되살리는 전역 채도 저하 대신 색조-채도 곡선을 쓰세요. 전역 채도는 파이프라인에서 먼저 실행되므로, 키가 사과를 보기도 전에 사과를 없애 버립니다. 대역의 가장자리는 넉넉하게 두어서 사과의 그늘진 쪽이 회색으로 잘리지 않게 하세요.

<DocsVideo title="HyperFrames video: Grade Brand Spotlight 5ebe45bf" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-brand-spotlight-5ebe45bf.mp4#t=0.1" loop />

*배경은 중립 회색으로 빠지고, 사과는 채도를 정확히 유지합니다.*

피사체에 대해 세 가지가 참이어야 합니다. 각각이 이 장면의 이전 시도를 망쳤습니다. 첫째, **무생물**이어야 합니다. 보정은 대역 바깥의 모든 것을 탈색시키므로, 사람에게 적용하면 회색빛의 죽은 듯한 얼굴이 됩니다. 둘째, **단일** 피사체여야 합니다. 여러 과일이 섞인 정물은 색으로 가득하지만, 절반의 항목이 대역 바깥에 있어서 회색으로 빠지므로 한 가지 색을 의도적으로 지킨 것이 아니라 필터가 오작동하는 것처럼 보입니다. 셋째, 배경이 색을 **담고** 있어야 합니다. 중립 회색 배경 앞에서는 보정이 회색을 회색으로 탈색시킬 뿐이라서 아무 일도 일어나지 않습니다.

***

## 아날로그: 세 가지 서로 다른 고장

"옛날 느낌으로 만들어 줘"는 세 가지 별개의 처리이며, 섞으면 시대가 흐려집니다.

| 처리 | 고장 나는 부분 | 특징 |
| - | - | - |
| **테이프** | 전송 장치 | 굴러가는 수평 물결, 트래킹 오류, 드롭아웃 |
| **브라운관** | 디스플레이 유리 | 배럴 곡률, 주사선, 형광체 번짐, 수렴 오류 |
| **카메라** | 캡처 | 그레인, 대비 뭉개짐, RGB 분리, 비네트 |

굴러가는 물결은 `tapeTracking`과 `tapeDamage`입니다. 정적 인터레이스는 `scanlines`인데, 이는 다른 것입니다. 카메라나 브라운관에 넣을 때 물결을 함께 끌고 오지 않도록 따로 쓰세요.

### 테이프

> 낡은 VHS 테이프처럼 만들어 주세요. 하나의 아티팩트가 아니라 여러 개를 겹치세요. 트래킹 오류가 있는 강한 테이프 손상, 약간의 노이즈, 중간 테이프 속도, 주사선, 눈에 띄는 크로마 번짐을 넣으세요. 이 중 하나만으로는 필터로 읽히지만, 함께 있으면 신호가 고장 난 것으로 읽힙니다.

<DocsVideo title="HyperFrames video: Grade Tape Degradation 6050228f" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-tape-degradation-6050228f.mp4#t=0.1" loop />

*여섯 가지 테이프 아티팩트가 동시에 나타납니다. 그중 하나만으로도 필터로 읽힙니다.*

### 브라운관

> 이것이 낡은 CRT 텔레비전에서 표시되는 것처럼 만들어 주세요. 낡은 테이프에서 나온 것처럼 만들지 마세요. 배럴 곡률로 기하를 휘게 해서 직선이 굽고 모서리가 안으로 당겨지게 하세요. 꽤 촘촘한 간격으로 주사선을 깔고, 형광체 번짐과 가장자리에 눈에 보이는 RGB 프린지가 생길 만큼 충분한 색수차를 넣으세요. 번짐과 주사선은 범위의 위쪽 근처에 두고 싶습니다. 번짐은 0.9에서도 은은합니다. 곡률과 색수차는 예외인데, 둘 다 강하게 읽히므로 곡률은 절반 정도로 유지하고 색수차는 적당하게 두세요. 그렇지 않으면 브라운관이 어안 렌즈 장난감이 됩니다. 기하뿐 아니라 톤도 보정하세요. 그림자와 검정을 뭉개고, 하이라이트와 흰색을 밝히고, 채도를 살짝 올리고, 절제된 블룸을 더하세요. CRT에는 진짜 검정이 없고 위쪽 끝이 헐레이션되기 때문입니다. 그레인과 비네트를 더하세요. 테스트 카드나 완전히 곧은 선이 있는 것을 쓰세요. 곡률은 유기적인 피사체에서는 보이지 않습니다.

<DocsVideo title="HyperFrames video: Grade Crt Broadcast B64dc1a8" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-crt-broadcast-b64dc1a8.mp4#t=0.1" loop />

*기하는 휘고, 주사선이 그 위에 깔리고, 톤은 뭉개졌습니다. 깨끗한 디지털 이미지 위에 덧씌운 필터가 아니라 브라운관입니다.*

톤 작업도 기하만큼 중요한 역할을 합니다. 그림자 뭉개짐과 헐레이션되는 상단이 없으면, 곡률과 주사선은 깨끗한 디지털 이미지 위에 덧씌운 필터로 읽힙니다.

피사체를 장면에 합성한다면 보정하기 **전에** 하세요. CRT는 표시되는 화면 전체를 휘게 하므로, 두 레이어를 따로 보정하면 배경은 휘어 보이는데 피사체는 직선으로 남아 브라운관의 굽은 가장자리 밖으로 흘러나옵니다. 레이어는 하나, 휨도 하나입니다. 위의 매트 분리 규칙과는 반대이고, 이유도 반대입니다.

### 카메라

> 클립에 캠코더 보정을 주세요. 그림자와 검정을 뭉개고, 하이라이트와 흰색을 밝히고, 채도를 살짝 낮추고, 절제된 블룸, 노이즈용 필름 그레인, 비네트, 인터레이스 선, 가장자리의 약간의 RGB 분리를 더하세요. 뭉개진 대비와 절제된 색이 실제 소비자용 테이프의 모습이었습니다. 뭉개지고 쨍한 것은 현대적인 필터로 읽힙니다. 분리에는 색수차를 쓰세요. 채널을 어긋나게 하기 때문입니다. 크로마 번짐은 다른 것으로, 가장자리 프린지가 아니라 번진 얼룩입니다. 인터레이스는 정적으로 유지하세요. 테이프 트래킹이나 테이프 손상은 넣지 마세요. 둘 다 굴러가는 수평 물결을 만들어서 카메라가 아니라 고장 난 데크처럼 읽히게 하기 때문입니다.

<DocsVideo title="HyperFrames video: Grade Camcorder Overlay 18e80485" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/grade-camcorder-overlay-18e80485.mp4#t=0.1" loop />

*영상은 열화되지만 HUD는 그렇지 않습니다. HUD는 미디어 캔버스 위에 합성된 오버레이입니다.*

이 장면의 HUD는 보정의 일부가 아닙니다. 미디어 캔버스 *위에* 합성된, 실제 HTML, CSS, 일시 정지된 GSAP 타임라인으로 이루어진 [`camcorder-hud`](/catalog) 레지스트리 블록입니다. 보정은 이를 전혀 건드리지 않으며, 이것이 바로 원하는 바입니다. 타임스탬프를 원본 픽셀에 구워 넣으면 함께 열화되고, 오버레이에 두면 영상이 밑에서 무너지는 동안에도 선명하고 편집 가능하며 타임라인으로 구동되는 상태로 남습니다.

## 보정을 애니메이션하기

CSS 커스텀 프로퍼티를 노출하고 직접 트윈할 수 있는 속성은 아홉 개입니다. `ascii`, `bloom`, `blur`, `dither`, `exposure`, `intensity`, `kuwahara`, `lut`, `pixelate`입니다. 장면이 보정 없이 시작하고 모든 중간값이 렌더링되도록 항등값에서 시작하세요.

클라이언트에게 램프를 약속하기 전에 알아둘 두 가지 주의점이 있습니다.

* **`--hf-color-grading-intensity`는 기본 보정만 조절합니다** — `adjust`, `wheels`, `curves`, `hueCurves`, `secondaries`와 LUT입니다. `details`와 `effects`는 이 혼합 바깥에 있으며, 어느 쪽도 조절하지 않습니다. 일부는 샘플링된 미디어를 그 전에 다듬고, 일부는 그 후에 실행되기 때문입니다. 그래서 그레인, 하프톤, 블룸, 테이프와 CRT 계열은 램프되지 않습니다. 이것을 마스터 다이얼로 취급하지 말고 특정 효과를 직접 쓰세요.
* **그 밖의 모든 것에는 커스텀 프로퍼티가 없습니다.** 그중 일부는 타임라인에서 `data-color-grading` 페이로드를 다시 써서 여전히 애니메이션할 수 있고, 일부는 불가능합니다. 어느 것이 어느 쪽인지에 대한 검증된 목록은 가이드의 [보정 애니메이션하기](/reference/color-grading#animate-a-supported-property)에 있으므로, 한 곳에서만 관리하면 됩니다. 램프를 약속하기 전에 애니메이션하려는 효과를 측정하고, 움직이지 않으면 정적 처리로 되돌리세요.

## 다음 단계

* [Color Grading 가이드](/guides/color-grading) — 전체 규격, 모든 키와 범위
* [카탈로그: 오버레이와 효과](/catalog) — HUD, 플래시, 빛 누출, 프리즈 프레임 장식
* [VFX와 리퀴드 글라스](/prompting/vfx-and-liquid-glass) — 카탈로그의 캔버스 파이프라인 쪽

*다음: [VFX와 리퀴드 글라스](/prompting/vfx-and-liquid-glass) — 같은 보정 어휘를 캔버스 파이프라인으로 확장합니다.*


## 관련 주제

- [이미지와 영상 색상 보정하기](/guides/color-grading.md)
- [변경 로그](/changelog.md)
- [아트워크를 생성할 때](/prompting/generated-artwork.md)


이 문서는 [Mintlify](https://mintlify.com), 개발자 문서 플랫폼으로 빌드되고 호스팅됩니다.
