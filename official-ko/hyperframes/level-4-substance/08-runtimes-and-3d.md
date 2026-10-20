> ## 문서 인덱스
> 전체 문서 인덱스는 다음 주소에서 가져올 수 있습니다: https://hyperframes.heygen.com/llms.txt
> 더 탐색하기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 먼저 찾아보십시오.

# 런타임과 3D

> GSAP가 기본값이라 보통 이름을 밝힐 필요가 없습니다. 실제 3D, 기존 애니메이션 파일,
> 장면 전환은 프롬프트에서 런타임을 명시할 가치가 있습니다.

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

Level 2의 복사-붙여넣기 예제에는 "Build the scene in Three.js via the adapter."라고 요청하는
아이소메트릭 카드 프롬프트가 있습니다. 이 장은 그 문장이 왜 들어 있는지 설명합니다.
또한 GSAP가 적합하지 않은 경우를 위한 나머지 런타임 지도이기도 합니다.

HyperFrames는 [frame-adapter](/concepts/frame-adapters) 패턴으로 애니메이션을 만듭니다.
"프레임 N에서 화면이 어떻게 보여야 하는가?"라는 질문에 답할 수 있는 런타임이라면 무엇이든
연결되어 결정론적으로 렌더링됩니다. [GSAP](/guides/gsap-animation)가 기본 어댑터이며
대부분의 모션을 담당하므로, 보통 이름을 밝힐 필요가 없습니다. 아래 경우들은 기본값이
잘못될 수 있는 상황입니다. 이때는 프롬프트에서 런타임을 지정해야 합니다.

## 실제 3D → 어댑터를 통한 Three.js

이것은 매번 명시해야 하는 유일한 지정 사항입니다. **깊이, 조명, 카메라**가 실제로 필요한 것에는
Three.js를 명시적으로 요청하십시오. 회전하는 제품, 여러분이 그 안을 통과하며 이동하는 장면,
빛을 받는 표면이 해당합니다:

> Build the scene in **Three.js via the adapter**: a product model on a turntable, one key light and a soft fill, slow rotation.

* ❌ `isometric cards floating in CSS 3D with perspective`
* ✅ `build the isometric scene in Three.js via the adapter, with real depth and lighting`

<DocsVideo title="HyperFrames video: Example 3d Cards" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-3d-cards.mp4#t=0.1" loop />

*아이소메트릭 카드 프롬프트의 Three.js 버전입니다. 실제 그림자와 조명이 있으며 한 번의 요청으로 만들었습니다.*

엔진을 이렇게 고르는 이유는 단순합니다. CSS `perspective` 변환은 평평한 면을 기울여 보이게 할 뿐입니다.
광원도 카메라도 없고 투영된 사각형만 있으므로, 조명이나 시차가 중요해지는 순간 평평하게 보입니다.

Three.js는 프레임 단위 seek에 안전한 1차 런타임입니다. 어댑터는 HyperFrames 시간을
`window.__hfThreeTime`으로 노출하고 각 seek마다 `hf-seek` 이벤트를 발생시키므로,
실제 3D 장면도 다른 요소와 마찬가지로 프레임 단위로 정확하게 렌더링됩니다.

"실제 3D"는 "Three.js"로 취급하십시오. 이것은 검증된 기본값이지 취향의 문제가 아닙니다.
예외는 평면적이고 양식화된 가짜 3D 느낌을 원할 때뿐입니다.

카메라 이동도 같은 규칙을 따릅니다. 드론 궤도, 달리(dolly), 푸시인은 실제 카메라가 있는 곳에서만 존재합니다:

<DocsVideo title="HyperFrames video: Camera Orbit" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/camera-orbit.mp4#t=0.1" loop />

*seek로 구동되는 Three.js 드론 궤도입니다. 카메라가 연속된 호를 그리며 도는데, 이것은 CSS 변환으로는 할 수 없습니다.*

* ❌ 런타임을 지정하지 않은 `a drone-orbit camera move around the logo` — CSS에는 궤도를 돌 카메라가 없습니다
* ✅ `orbit the camera around the logo — Three.js via the adapter`

## 기존 애니메이션 파일 → Lottie

이미 디자인된 애니메이션이 있을 수 있습니다. After Effects 내보내기, `.json` 또는 `.lottie` 파일,
디자이너가 만든 아이콘 애니메이션 등입니다. 에이전트에게 이것을 다시 그리라고 요청하지 마십시오.
파일을 가리키고 Lottie를 요청하십시오:

> Play this Lottie file (`assets/loader.lottie`) centered, then fade to the title.

Lottie 어댑터는 기존 애니메이션을 프레임 단위로 seek하므로, 디자이너의 작업물이 원래대로 정확히 렌더링됩니다.
이것을 GSAP로 다시 만들어 달라고 하면 원본을 버리게 되고 결과는 어딘가 비슷하기만 한 모습이 됩니다.

캐릭터도 같은 방식으로 다룹니다. 걸어 들어와 멈추고 가리키는 마스코트는 연기가 담긴 Lottie 파일이고,
에이전트는 그 주변 장면을 GSAP로 구성합니다:

> Use this character Lottie (`assets/mascot.json`): it walks in and points right at 5.2s. Bring the title card in on the point.

`loop: true`가 설정된 짧은 걷기 사이클은 장면 전체 동안 계속 반복됩니다.
[`lottie-character-walk`](/catalog/blocks/lottie-character-walk) 블록이 바로 쓸 수 있는 출발점입니다.

## 단순한 UI와 텍스트 모션 → 기본값

페이드, 슬라이드, 스태거, 카운터, 키네틱 타입, 호버 스타일 리빌 같은 일상적인 모션은
GSAP가 기본으로 처리합니다. 이미 기본값입니다. 여기서 런타임 이름을 밝히지 마십시오.
대신 모션을 설명하십시오. [프리미엄처럼 읽히는 모션](/prompting/motion)을 참고하십시오:

> The headline slides up per word, staggered 0.1s apart, easing out as it lands.

CSS 키프레임과 Web Animations API도 지원되는 어댑터입니다. 기존 CSS `@keyframes`나 WAAPI 코드를
그대로 유지하고 싶을 때만 이름을 밝히십시오. 새로 요청하는 경우에는 기본값에 맡기십시오.

SVG "선이 스스로 그려지는" 효과(애니메이션되는 `strokeDasharray` / `strokeDashoffset`)도
GSAP 기본 영역입니다. 요청하기 전에 알아 둘 두 가지 린트 주의점은 부록의
[SVG draw-on 행](/prompting/rules-and-anti-patterns#svg-draw-on)을 참고하십시오.

## 장면 간 전환 → 셰이더 전환

장면 *안에서*의 모션과 장면 *사이*의 전환은 다른 문제입니다. 디자인된 전환(와이프, 글리치,
액체 디졸브)을 원한다면 그 특정 순간에 셰이더 전환을 요청하십시오:

> Hard-cut between the first three scenes; use a **shader transition** (glitch) into the final logo scene.

순간을 명시하십시오. 셰이더 전환은 모든 컷이 아니라, 그럴 만한 두세 개의 비트를 위한 것입니다.
어휘는 [전환](/prompting/transitions)을 참고하십시오.

## 결정론이 프롬프트에 드러나는 지점

모든 런타임은 같은 [결정론](/concepts/determinism) 계약 아래에서 렌더링됩니다.
프레임 시계는 `t = frame / fps`입니다. **벽시계 시간, 렌더링 시점의 실시간 네트워크,
시드 없는 난수는 없습니다.**

이 중 두 가지 요청이 이 규칙에 부딪히므로, 그에 맞게 표현하십시오.

라이브 데이터는 렌더링 시점에 가져올 수 없습니다. 렌더링이 재현 가능해야 하기 때문입니다:

* ❌ `fetch the current BTC price and count up to it`
* ✅ 고정된 값을 넣은 `count up to $67,400`, 또는 `read the target from a variable I pass at render time`

시드 없는 난수는 프레임마다 다르게 렌더링되어 재현성을 깨뜨립니다:

* ❌ `scatter 200 particles randomly`
* ✅ `scatter 200 particles from a seeded random layout` — **seeded**라고 말하면 프레임과 재렌더링 사이에서도 위치가 안정적으로 유지됩니다

대략적인 원칙은 이렇습니다. 영상이 *미리 알아야 하는* 것은 렌더링 시작 전에 존재해야 하며,
구워 넣거나 [변수](/prompting/variables-and-templating)로 넘기십시오. 난수가 필요한 것은 모두 시드를 지정하십시오.

## 캡스톤 스레드

<Note>
  **캡스톤 스레드** — [Level 7 영화](/prompting/capstone)의 Depth 영역은 frame adapter를 통한 실제 Three.js입니다.
  타임라인 와이어가 면이 있는 조명받은 형태 주위를 감고, 주인공 칩이 코일의 고리 사이를 지나
  뒤로 넘어가며 실제 깊이 가림(occlusion)을 보여 줍니다(아래는 영화에서 잘라낸 장면입니다).
</Note>

이 절을 만드는 것은 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)입니다.
여러분의 영상에 가져다 쓸 수 있는 프롬프트 문구입니다:

> **Depth (52–56s).** The wire spirals off the flat plane into real 3D — a **Three.js scene via the frame adapter** (never CSS fake-3D): the camera descends following the wire as it coils around a rim-lit faceted form (ink material on charcoal), mono axis readouts landing on cue, then rises back to the plane with the wire leading the way out. The coil winds up out of the wire and collapses back onto it — its ends never float cut off in mid-air — and the protagonist chip joins the 3D scene for the crossing: it rides the wire straight through the coil's loops and passes behind the form with true depth occlusion, never floating over the geometry as a flat overlay.

<DocsVideo title="HyperFrames video: Capstone Region Depth" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-depth.mp4#t=0.1" loop />

*이 절을 렌더링한 결과이며, 완성된 영화에서 해당 영역만 잘라낸 것입니다.*

*다음: [미디어와 오디오](/prompting/media-and-audio) — 모션과 렌더링 대신,
보이스오버, 음악, 사운드, 에셋을 위한 정밀한 표현을 다룹니다.*

## 관련 주제

* [프레임 어댑터](/concepts/frame-adapters) — 프레임 단위 seek 계약과 지원되는 모든 런타임 목록입니다
* [결정론적 렌더링](/concepts/determinism) — 라이브 데이터와 시드 없는 난수를 쓰지 않는 이유입니다
* [프리미엄처럼 읽히는 모션](/prompting/motion) — 일상적인 GSAP 모션을 싸구려처럼 보이지 않게 묘사하는 방법입니다
* [전환](/prompting/transitions) — 셰이더 전환을 줄 만한 장면 간 전환을 명명하는 방법입니다
* [GSAP로 애니메이션 만들기](/guides/gsap-animation) — 기본 어댑터를 자세히 다룹니다


## 관련 주제

- [캡스톤 — 모든 기법, 하나의 여정](/prompting/capstone.md)
- [VFX와 리퀴드 글래스](/prompting/vfx-and-liquid-glass.md)
- [3D 전환](/catalog/blocks/transitions-3d.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 만들어져 호스팅됩니다.
