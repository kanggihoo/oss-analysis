> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져오세요.
> 더 살펴보기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾으세요.

# 단일 프롬프트의 구조

> 경로, 사양, 비트, 문구, 기법, 금지 사항으로 이루어진 여섯 부분 골격입니다. 에이전트가 가장 자주 잘못 정하는 결정을 없애 줍니다.

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

Level 1 프롬프트가 통한 이유는 워크플로가 빈틈을 대신 채워 주었기 때문입니다. 팔레트, 페이싱, 구조를 말이죠. 이 장은 Level 2입니다. 골격은 여러분이 그 통제권을 직접 쥐는 방법입니다.

[복사-붙여넣기 예제](/prompting/examples)는 모두 하나의 골격을 공유합니다. 각 부분은 에이전트가 첫 시도에서 가장 자주 잘못 정하는 결정을 하나씩 없앱니다.

```text theme={null}
[route]      /motion-graphics
[spec]       8-second 1920x1080 video.
[beats]      Beat 1 (0-4s): ...  Beat 2 (4-5s): ...  Beat 3 (5-8s): ...
[copy]       the exact on-screen text, quoted
[technique]  Adapt the `code-typing` and `vfx-shatter` registry blocks.
[negatives]  No narration, no image or media files.
```

* 슬래시 명령으로 **경로(Route)**를 지정합니다. 알맞은 워크플로와 프레임워크 규칙을 불러옵니다.
* **사양(Spec)**: 길이와 해상도를 맨 앞에 적습니다. 기본값은 1920x1080, 30fps입니다.
* **비트(Beats)**에는 타임스탬프를 붙입니다. 페이싱 지시("그다음 깜박이는 커서에서 멈춘다")도 넣으세요. 말하지 않으면 에이전트는 숨 쉴 틈을 건너뜁니다.
* **문구(Copy)**는 정확히 따옴표로 묶고, 줄바꿈은 `/`로 표시합니다. 따옴표가 없으면 문구가 바뀌어 적힙니다.
* **기법(Technique)**: 레지스트리 블록은 [카탈로그](/catalog/blocks/data-chart)에 나온 이름 그대로 지정하세요. 이들은 그대로 끼우는 부품이 아니라 고쳐 쓰기 위한 출발점입니다. 블록에는 데모 콘텐츠가 들어 있고, 에이전트가 여러분의 비트에 맞게 다시 씁니다. 그러니 블록 이름을 지정하면 *기법*이 고정됩니다. 기본 선택이 실패할 수 있는 곳에서는 기법을 고정하세요([명세 다이얼](/prompting/specification-dial) 참고).
* **금지 사항(Negatives)**은 빈틈을 막습니다. "내레이션 없음"은 "무음"과 다릅니다. 소리를 전혀 원하지 않으면 "오디오 없음"이라고 말하세요. "외부 에셋 없음"처럼 모호한 표현은 피하세요(CDN으로 불러오는 런타임은 정상입니다. 의도가 그것이라면 "이미지나 미디어 파일 없음"이라고 말하세요).

조립하면 다음과 같습니다.

> /motion-graphics Make an 8-second 1920x1080 video. Beat 1 (0-4s): dark macOS terminal types "npx skills add heygen-com/hyperframes" character by character, then hold on the blinking cursor. Beat 2 (4-5s): the terminal shatters into fragments. Beat 3 (5-8s): bold white kinetic text on black slams in word by word, snappy: "YOU JUST MADE THIS / WITH HYPERFRAMES." Adapt the `code-typing` and `vfx-shatter` registry blocks; hand-author the kinetic text. No narration, no image or media files.

<DocsVideo title="HyperFrames video: Validate Anatomy Terminal" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-anatomy-terminal.mp4#t=0.1" loop />

*위 프롬프트를 편집 없이 렌더링한 결과.*

<Note>
  골격은 단순한 프롬프트 작성 스타일이 아닙니다. 프레임워크 자체도 그 일부를 스스로에게 강제합니다. 컴포지션 구조 의무(`0aaac7aa3`, PR #2599) 이후, 시각적 결함에 대한 `hyperframes feedback` 보고서에는 `COMPOSITION_STRUCTURE:` 블록이 필요합니다. 요소 목록, 속성 존재 여부, 타임라인 형태를 담으며, 컴포지션 자체의 HTML에서 자동으로 채워집니다. 이 블록이 없으면 CLI가 경고만 하고(차단하지는 않음) 넘어갑니다. 위의 여섯 부분과 같은 생각입니다. 형태를 명시적으로 말하면 여러분과 프레임워크가 모두 더 빠르게 추론합니다.
</Note>

## 비트 공식

위의 골격은 *요청*의 구조를 잡습니다. 각 비트 안에서는 매번 같은 다섯 슬롯으로 *내용*을 묘사하세요.

```text theme={null}
[element]   what's on screen        a giant number · the tweet card · "SHOWREEL"
[motion]    what it does            counts up with an odometer roll · slides up · fades in per letter
[layout]    where it sits           top-center · filling the lower half · bottom-right
[style]     how it looks            dark navy, green accent · 8-bit pixel · thin geometric sans
[timing]    when, inside the beat   at 1s · over 3s, easing out as it lands · staggered 0.1s apart
```

요소마다 문장 하나, 슬롯 순서는 아무거나 상관없습니다: *"거대한 숫자 **(요소)**가 주행계식 롤링으로 \$4.2M까지 올라가고 **(움직임)**, 착지하면서 속도가 줄어들며 **(타이밍)**, 짙은 남색 바탕에 초록색으로 가운데 **(레이아웃)** 정렬되어 있다 **(스타일)**."* 묘사하지 않은 요소는 에이전트가 설계합니다. 에이전트의 취향을 믿을 수 있다면 괜찮지만, 믿지 못하면 흐름이 어긋날 위험이 있습니다([명세 다이얼](/prompting/specification-dial) 참고).

<Tip>
  비트 타임스탬프 프롬프트(`Beat 2 (4-5s): ...`)는 HyperFrames의 기본 언어입니다. 확산(diffusion) 영상 모델은 하나의 클립 위에 시간 분할을 덧붙입니다. 여기서는 모든 비트가 컴포지션의 타임드 클립에 직접 대응하므로, 비트별 묘사가 손실 없이 옮겨집니다. 타임스탬프를 넉넉히 쓰세요.
</Tip>

## 자주 하는 고쳐 쓰기

가장 자주 나오는 수정을 전/후 쌍으로 정리했습니다. 각각은 엔진이 실제로 작동하는 방식 때문에 존재합니다.

**유지(hold)가 굳는 문제.** 컴포지션은 마지막 상태를 유지하므로, 말 그대로 "hold"라고 쓰면 굳은 프레임이 렌더링됩니다. 싸구려 움직임이 드러나는 가장 큰 신호입니다.

* ❌ `then everything holds motionless to the end`
* ✅ `then everything settles into a gentle ambient idle (breathing scale, slow drift)`

**꼬리 없는 길이.** 같은 실수의 더 미묘한 버전입니다. 묘사한 비트보다 긴 런타임을 적으면, 남는 초는 기본적으로 죽은 유지 구간이 됩니다. 이 가이드의 차트 예제를 검증하다 보니, 12초짜리 요청에 묘사된 내용은 약 5초뿐이었습니다. 빌더는 나머지 7초를 지어내야 했습니다. 요청을 내용 길이에 맞게 줄이거나, 꼬리 구간에서 무엇이 일어나는지 말하세요.

* ❌ `12-second video. [five seconds of beats]`
* ✅ `12-second video. [beats] … then hold ~5s on the finished chart with the leader pulsing once and a slow ambient drift`

**동시성 충돌.** "4초에"로 지정된 두 가지가 몇 프레임 겹칩니다. 렌더러는 적힌 그대로 정확히 실행합니다.

* ❌ `at 4s the counter fades out and READY stamps in`
* ✅ `the counter fades out fully by 4.2s; at 4.2s READY stamps in`

**모호한 금지 사항.** "외부 에셋 없음"은 모호합니다. CDN으로 불러오는 런타임은 정상적인 기반 요소입니다.

* ❌ `no external assets`
* ✅ `no image or media files`

**문구가 들어가야 할 자리에 산문을 쓴 경우.** 따옴표가 없는 텍스트는 바뀌어 적히고, 따옴표로 묶은 텍스트는 그대로 렌더링됩니다.

* ❌ `show a tagline about shipping faster`
* ✅ `tagline: "Ship faster."`

**형식을 무시한 숫자.** 주행계에는 고정된 자릿수 열이 필요합니다. "counts $0 → $4.2M"이라고 쓰면 어색한 "\$0.0M" 시작을 강요합니다.

* ❌ `counts from $0 to $4.2M`
* ✅ `counts up to $4.2M`

## 프레임워크 고유의 어휘

위의 골격은 여러분이 요청하는 방식입니다. 이것은 에이전트가 쓰는 내용이며 한눈에 알아볼 가치가 있습니다. 컴포지션을 읽거나, 디프를 검토하거나, 린트 오류를 받았을 때 이 네 가지가 핵심 부품입니다.

| 파일 안의 모습 | 의미 |
| - | - |
| `class="clip"` | 시간이 정해진 구간을 표시합니다. 가시성은 프레임워크가 관리합니다. 숨기려고 클립 자체의 opacity나 `display`를 애니메이션하지 마세요. |
| `data-start` / `data-duration` / `data-track-index` | 클립이 언제 시작하는지, 얼마나 재생되는지, 어느 트랙에 있는지. 같은 트랙 인덱스의 두 클립은 시간이 겹치면 안 됩니다. |
| `window.__timelines["<id>"]` | GSAP로 구동되는 모든 컴포지션은 여기에 일시정지된 타임라인을 정확히 하나 등록하며, 로드 시 동기적으로 만들어집니다. 렌더러는 이 타임라인을 프레임 단위로 탐색합니다. 그래서 벽시계 시간이나 시드가 없는 난수에 의존하면 안 됩니다. Lottie, CSS 애니메이션, WAAPI를 포함한 다른 어댑터는 각자의 탐색 가능한 런타임 계약을 통해 등록합니다. |
| 소리가 있는 영상 | `<video playsinline data-has-audio="true">` — 소리가 클립에 그대로 남습니다 |
| 음악 / 보이스오버 | 별도의 `<audio>` |

이것들을 손으로 직접 쓸 일은 드물지만, 프롬프트에서 이름을 부르는 것은 정당하고 때로는 필요합니다. "자막은 별도의 트랙 인덱스에 두라", "컴포지션 파일은 하나, 타임라인도 하나로 유지하라" 같은 식입니다. 또한 모든 오류 메시지가 쓰는 어휘이기도 합니다. 전체 계약은 `/hyperframes-core` 스킬에 있고, [부록](/prompting/rules-and-anti-patterns)에는 가장 자주 문제가 되는 규칙이 정리되어 있습니다.

<Note>
  **캡스톤 흐름** — [Level 7 영상](/prompting/capstone)은 이 표를 배경으로 삼습니다. Mount 영역에서는 타임라인 와이어가 세 개의 트랙 레인으로 갈라지고, 클립 칩이 그 레인에 자리 잡으며, 위에 나온 바로 그 속성을 스스로 달고 있습니다. 프레임워크 고유의 어휘가 한 세트로 연출되는 셈입니다. 프롬프트 전체도 이 장의 골격을 최대 규모로 적용한 것입니다. 경로, 사양, 비트(아홉 개 영역), 정확히 따옴표로 묶은 문구, 영역별로 고정된 기법, 그리고 엄격한 금지 목록입니다.
</Note>

이 절은 작품을 완성시키는 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)의 한 구절입니다. 여러분의 영상에 가져다 쓸 수 있는 프롬프트 문장입니다.

> **Mount (7–14s).** Traveling along the wire: it splits into three parallel track lanes; clip chips slide in along the direction of travel and seat onto the lanes on their spoken cues (audio track chip, video track chip, our protagonist chip among them). Small mono labels (`data-start`, `data-track-index`) tag themselves onto chips as the camera passes. The lanes merge back to one wire as the camera accelerates out.

<DocsVideo title="HyperFrames video: Capstone Region Mount" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-mount.mp4#t=0.1" loop />

*이 절을 렌더링한 결과 — 완성된 영상에서 잘라낸 영역입니다.*

*다음: [명세 다이얼](/prompting/specification-dial) — 골격을 얼마나 채울지, 그리고 언제 밀도가 선택 사항이 아니게 되는지.*


## 관련 주제

- [VFX와 리퀴드 글래스](/prompting/vfx-and-liquid-glass.md)
- [스토리보드](/prompting/storyboards.md)
- [코드 애니메이션](/prompting/code-blocks.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 만들어지고 호스팅됩니다.
