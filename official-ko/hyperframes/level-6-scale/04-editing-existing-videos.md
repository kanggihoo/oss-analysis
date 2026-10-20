> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져옵니다.
> 더 살펴보기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾아보십시오.

# 기존 영상 편집하기

> 편집자처럼 에이전트를 지시하십시오. 자르기, 옮기기, 타이밍 바꾸기, 교체, 스타일 변경을 하면 됩니다. 이미 아는 NLE 동사를 한 번에 적용되는 프롬프트에 대응시켰습니다.

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

[스토리보드](/prompting/storyboards)의 프레임도 편집하고, 여러분이 만드는 다른 모든 것도 편집합니다. 템플릿화된 composition, one-shot 장면, 모든 것이 해당합니다. HyperFrames 시간의 대부분은 첫 렌더링이 아니라 그 뒤의 스무 번의 편집입니다. composition은 `data-*` 타이밍 속성과 GSAP 타임라인이 있는 순수 HTML이므로, 비선형 편집기에서 하는 모든 편집은 소스의 구체적이고 검사 가능한 변경에 대응합니다. 영상을 다시 명세할 필요는 없습니다. 사람 편집자에게 말하듯 편집을 이름 붙이면, 에이전트가 그것을 해내는 가장 작은 변경을 만듭니다.

이 페이지는 편집기 동사를 그것을 한 번에 적용하는 프롬프트에 대응시킵니다. 예시는 일반적인 composition의 요소 이름을 사용합니다. 여러분의 composition에 맞게 명사("하단 자막", "장면 2")를 바꿔 쓰십시오. [반복 작업](/prompting/iterating)의 두 가지 습관이 모든 예시에 적용되므로 기억해 두십시오. **렌더링마다 한 가지만 바꾸십시오**. 그리고 목표를 **절대값**으로 말하십시오("장면 2 = 2초", "조금 짧게"가 아니라). 그래야 에이전트가 진동하지 않고 한 번에 맞춥니다.

## 동사 → 편집 대응표

모든 타임라인 동사는 `data-*` 속성이나 인라인 스타일로 대응합니다. 각 동사가 내부에서 무엇을 건드리는지 아는 것이 유용합니다. 절대 목표가 효과가 있고 일부 편집이 저렴한 이유가 이것입니다.

| 이렇게 말합니다 | 편집기 동사 | 에이전트가 편집하는 것 |
| - | - | - |
| "장면 2를 더 늦게 / 더 일찍 시작" | Move | `data-start` |
| "자막을 영상 위에 올려줘" | Restack | `data-track-index` + 인라인 `z-index` |
| "로고를 더 빨리 끝내줘" | Trim (오른쪽) | `data-duration` |
| "클립의 첫 1초를 건너뛰어줘" | Trim (앞쪽, 미디어 전용) | `data-media-start` |
| "장면 2를 2초 길이로 만들어줘" | Retime | `data-duration` (그리고 GSAP 타임라인 길이) |
| "오디오 배경이 너무 커" | Level | `data-volume` |

<Note>
  Studio 타임라인이 사용하는 멘탈 모델은 이렇습니다. **move**는 클립이 *언제 시작하는지*를 바꾸고, **오른쪽 trim**은 *언제 끝나는지*를 바꿉니다. **앞쪽 trim**은 미디어 클립에만 존재합니다. `<video>`나 `<audio>`는 자신의 내용 안으로 건너뛸 수 있지만, GSAP으로 구동되는 `<div>`는 애니메이션 중간에서 시작할 수 없습니다. 클립 유형별 전체 설명은 [Studio 타임라인](/studio/timeline)을 보십시오. 대응표가 보여주지 못하는 표면이 하나 더 있습니다. 전체 composition에 걸치는 장면의 타이밍을 바꾸려면 루트의 `data-duration`도 함께 키워야 합니다. 루트가 전체 길이를 결정하므로, 더 긴 하위 요소는 그 길이를 넘어 렌더링되지 않습니다.
</Note>

## 자르기, 옮기기, restack

이것들은 순수한 타이밍 편집입니다. 시각적 변화는 없고, 레이어가 타임라인에서 언제, 어디에 놓이는지만 바꿉니다.

> 인트로가 0:05가 아니라 0:03에서 끝나도록 자르십시오.

> 하단 자막이 0:06에 시작하도록 옮기십시오.

> 자막이 영상 뒤에 렌더링되고 있습니다. 더 높은 트랙으로 옮겨서 영상 위에 올려주십시오.

이동은 composition의 길이에 맞춰 제한됩니다. 10초짜리 영상에서 4초짜리 클립을 0:08로 옮기면 끝나기 전에 거의 보이지 않습니다. 절대 목표는 여기서 가장 중요합니다. "인트로를 짧게 해줘"는 추측을 부르지만, "인트로는 3.0초에서 끝나야 함"은 `data-duration`을 한 번 쓰는 일이며 넘칠 여지가 없습니다.

* ❌ `오프닝을 조이세요`
* ✅ `인트로 클립 길이 = 3초. 애니메이션과 위치는 그대로 두기` — 속성 하나이며, 고정 조항 덕분에 재구성이 이미 정한 축에서 벗어나지 않습니다.

<DocsVideo title="HyperFrames video: Editing Before" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/editing-before.mp4#t=0.1" loop />

*편집 전 — 손대지 않은 composition입니다.*

<DocsVideo title="HyperFrames video: Editing After" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/editing-after.mp4#t=0.1" loop />

*편집 후 — 이 페이지의 편집 네 가지를 그대로 적용한 결과입니다(move, 오른쪽 trim, retime, 고정 조항이 있는 스타일 변경). 각각 대응표가 약속한 속성만 정확히 건드렸고, 매 편집 후 게이트는 모두 통과했습니다.*

## 장면 나누기

Studio 타임라인은 move와 trim을 드래그 제스처로 제공하지만, split, slip, slide, ripple, roll은 아직 제공하지 않습니다. 그래도 에이전트에게 지시하면 나눌 수 있습니다. 에이전트가 HTML을 직접 편집하기 때문입니다. 나누기는 클립 하나가 `data-start` / `data-duration`이 조정된 두 클립이 되는 것입니다.

> 장면 2를 0:04에서 나눠서 두 부분 사이에 전환을 넣을 수 있게 해주세요.

정확한 자를 지점을 이름으로 말하십시오. 에이전트가 클립 하나를 인접한 클립 두 개로 바꿉니다. 그러면 각 절반을 독립된 레이어로 다룰 수 있습니다.

## 장면 타이밍 바꾸기

타이밍 변경은 장면의 `data-duration`에서 시작합니다. 움직임이 원래 속도를 유지해야 한다면, 타임라인은 일찍 끝나고 장면이 계속되는 동안 마지막 상태를 유지할 수 있습니다. 움직임 자체가 느려지거나 더 긴 장면에 걸쳐 펼쳐져야 한다면, 영향을 받는 트윈도 함께 다시 타이밍을 맞추도록 에이전트에게 요청하십시오.

> 장면 2를 2.5초가 아니라 4초로 만들어주세요. 애니메이션은 그대로 두고, 여유만 더 주세요.

* ❌ `장면 2를 늘려줘` — 움직임을 느리게 하라는 것인지, 정지 시간을 늘리라는 것인지 모호합니다
* ✅ `장면 2 길이 = 4초, 움직임은 같게, 추가 시간은 끝에 정지 구간으로 추가`

<Warning>
  렌더링 길이는 GSAP 타임라인의 길이가 아니라 `data-duration`에서 옵니다. 빈 `tl.set({}, {}, <seconds>)` 센티널로 타임라인을 채우지 마십시오. 장면이 여전히 일찍 끝난다면, [데이터 속성](/concepts/data-attributes)에서 장면과 composition의 타이밍 속성을 확인하십시오.
</Warning>

## 더 빠르게 만들기(길이가 아니라 *느낌*을 바꾸기)

"더 빠르게", "더 탄력 있게", "더 여유 있게"는 속도를 나타내는 말이며, 구체적인 이징과 타이밍 선택으로 대응됩니다. 전체 표는 [어휘](/prompting/vocabulary)에 있습니다. 에이전트는 "빠른"을 단호한 이징(`power4.out`)과 더 짧은 길이로 읽고, "꿈같은"을 느리고 대칭적인 움직임으로 읽습니다.

> 장면 2를 더 빠르게 해주세요. 입장은 더 빨리, 컷은 더 강하게.

> 공개 장면이 기계적으로 느껴집니다. 통통 튀는 오버슈트를 주세요.

렌더링마다 장면 하나의 느낌만 바꾸면 무엇이 효과가 있었는지 구별할 수 있습니다. 어떤 장면이 계속 실패한다면, 최소 버전(주체와 그 움직임만)으로 줄여서 읽히는지 확인한 다음 다시 레이어를 쌓으십시오.

## 키프레임 조정하기

개별 애니메이션 속성은 편집할 수 있습니다. 어떤 트윈의 값, 이징, 타이밍도 가능합니다. 이것을 프롬프트로 지시하거나, Studio Design Panel에서 직접 편집할 수 있습니다. 어느 쪽이든 같은 GSAP 코드로 귀결됩니다.

> 제목이 너무 멀리서 들어옵니다. 입장을 200px가 아니라 40px만 이동하도록 바꿔주세요.

> 장바구니 담기 항목에 곧장 대각선이 아니라 호를 그리게 해주세요. 장바구니에 던져 넣는 것처럼요.

속성 목표는 절대값으로 말하십시오(`Move X = 40`, `호의 곡률 ≈ 1.5`). [애니메이션과 키프레임](/studio/animation)은 편집 가능한 항목, 모션 경로, 제스처 녹화를 다룹니다.

<Tip>
  요소별 편집에는 Design Panel의 클립보드 아이콘이 구조화된 맥락(요소의 id, 위치, 크기, 현재 애니메이션)을 복사하며, 프롬프트에 붙여넣을 준비가 되어 있습니다. "제목" 같은 모호한 말 대신 에이전트에게 정확한 공간 맥락을 줍니다.
</Tip>

## 에셋 교체하기

영상, 이미지, 로고, 오디오 트랙을 바꾸는 것은 소스 교체입니다. 규칙은 하나입니다. **경로를 이름으로 말하십시오.** 에이전트는 "내 로고"를 검색하지만, 경로는 검색을 건너뛰게 하고 어느 파일을 뜻하는지의 모호함을 없앱니다.

> 배경 음악을 `assets/track.mp3`로 바꿔주세요.

> 히어로 이미지를 `assets/product-v2.png`로 교체하고 애니메이션은 유지해주세요.

* ❌ `새 로고를 써줘`
* ✅ `로고를 assets/logo-2025.svg로 교체`

## 문구 바꾸기

화면상의 텍스트는 인용하면 그대로 편집됩니다. 인용하지 않은 텍스트는 바꿔 쓰입니다. 에이전트는 설명을 정확히 배치하라는 지시가 아니라, 문구를 새로 쓰라는 지시로 받아들이기 때문입니다.

> 헤드라인을 "Ship faster."로 바꿔주세요. 문구는 정확히 그대로, 스타일도 유지.

* ❌ `속도에 관한 제목으로 바꿔줘`
* ✅ `제목 문구: "Ship faster."`

## 요소 하나의 스타일 바꾸기

색, 크기, 굵기, 요소 하나의 위치 같은 시각적 조정에는 "나머지는 고정" 조항이 힘을 발휘합니다. 이 조항이 없으면 스타일 프롬프트가 이미 승인된 레이아웃이나 움직임에서 벗어나는 재구성을 일으킬 수 있습니다.

> CTA 버튼을 20% 키우고 강조 색으로 바꿔주세요. 그 밖에는 아무것도 건드리지 마세요.

* ❌ `CTA를 더 돋보이게 해줘`
* ✅ `CTA 배경 = 강조 색, font-size = 현재의 1.2배. 구도와 움직임은 맞으니 그대로 두기`

## 관련

<CardGroup cols={2}>
  <Card title="반복 작업" href="/prompting/iterating">편집마다 변수 하나, 절대 목표, 잘 된 것은 고정</Card>
  <Card title="어휘" href="/prompting/vocabulary">장면의 *느낌*을 바꾸는 속도와 이징 단어</Card>
  <Card title="Studio 타임라인" href="/studio/timeline">클립 이동, 자르기, 나누기, 탐색</Card>
  <Card title="데이터 속성" href="/concepts/data-attributes">`data-*` 타이밍 계약</Card>
</CardGroup>

*다음: [반복 작업](/prompting/iterating). 이 페이지의 모든 편집 뒤에 있는 원칙입니다. 렌더링마다 변수 하나, 절대 목표, 잘 된 것은 고정.*


## 관련 주제

- [반복 작업](/prompting/iterating.md)
- [스토리보드](/prompting/storyboards.md)
- [영상 마무리 및 공유](/guides/export-and-share.md)


이 문서는 개발자 문서 플랫폼인 [Mintlify](https://mintlify.com)로 작성되고 호스팅됩니다.
