> ## 문서 인덱스
> 전체 문서 인덱스는 다음 주소에서 가져올 수 있습니다: https://hyperframes.heygen.com/llms.txt
> 더 탐색하기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 먼저 찾아보십시오.

# 코드 애니메이션

> 타이핑, 디프, 하이라이트, 스크롤로 코드 워크스루를 프롬프트하고 이름으로 터미널이나 에디터 테마를 고릅니다.

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

Level 1의 PR 영상에서 `code-diff`라는 이름으로 잠깐 다뤘던 내용을 이 장에서 이어갑니다. 타이핑, 디프, 하이라이트, 스크롤, 그리고 이름으로 터미널이나 에디터 테마를 고르는 방법을 다룹니다. 워크스루에서 속도를 늦추고 코드 자체가 장면을 끌고 가야 할 때 쓰는 카탈로그입니다.

코드는 프레임워크가 어려운 부분을 대신 처리해 주는 대표적인 주제입니다. [Code Animations](/catalog/blocks/code-typing) 블록이 구문 강조, 캐럿 추적, 디프 색상, 카메라 이동을 결정론적으로 처리합니다. 여러분은 *워크스루*를 설명하고 블록 이름을 지정한 뒤 스니펫을 붙여 넣으면 됩니다. 이 페이지는 그것을 잘하기 위한 어휘집입니다. 실제 풀 리퀘스트를 코드 변경 영상으로 만드는 방법은 [코드와 PR](/prompting/code-and-prs)을 참고하십시오.

여기의 모든 내용은 [one-shot 골격](/prompting/anatomy)을 따릅니다: 경로, 스펙, 비트, 문구, 기법, 제약. "technique" 슬롯에는 블록 이름을 쓰고, "copy" 슬롯에는 코드를 넣습니다. 코드는 그대로 인용해야 합니다. 인용하지 않으면 paraphrase되어 컴파일되지 않는 코드가 되기 때문입니다.

### 시청자가 무엇을 알아야 하는지에 따라 모션 고르기

각 Code Animations 블록은 "시청자가 무엇을 알아채야 하는가"에 대해 서로 다른 답을 줍니다. 의도에 맞는 블록을 고르십시오:

| 보여 주려는 것 | 이 블록의 이름 | 길이 |
| - | - | - |
| 코드가 한 글자씩 작성되는 모습 | [`code-typing`](/catalog/blocks/code-typing) | 5초 |
| 수정 — 이전 → 이후, 빨강/초록 | [`code-diff`](/catalog/blocks/code-diff) | 6초 |
| 한 줄을 *핵심* 줄로, 나머지는 흐리게 | [`code-highlight`](/catalog/blocks/code-highlight) | 5초 |
| 긴 파일을 내려가 깊은 곳의 한 지점까지 이동 | [`code-scroll`](/catalog/blocks/code-scroll) | 6초 |
| 한 스니펫이 다른 스니펫으로 변하는 모습 | [`code-morph`](/catalog/blocks/code-morph) | 7초 |
| 회전하는 3D 슬랩 위의 코드 (타이틀 카드 느낌) | [`code-3d-extrude`](/catalog/blocks/code-3d-extrude) | 8초 |
| 셰이더 디졸브에서 드러나는 코드 | [`code-shader-dissolve`](/catalog/blocks/code-shader-dissolve) | 7초 |
| 파티클 군집에서 조립되는 코드 | [`code-particle-assemble`](/catalog/blocks/code-particle-assemble) | 8초 |

앞의 네 가지는 코드 *워크스루*의 주력 블록입니다. 코드를 읽기 쉽게 유지하고 시청자가 길을 잃지 않게 합니다. 그 아래 블록들은 가독성을 모션과 맞바꿉니다. 오프닝이나 히어로 장면으로는 멋지지만, 설명을 맡기기에는 적합하지 않습니다.

<Tip>
  `code-morph`는 Shiki Magic Move를 일시정지된 GSAP 타임라인으로 다시 구동하고, `code-diff`는 삭제된 줄을 접고 추가된 줄을 펼칩니다. 두 블록 모두 `code-typing`으로 스니펫 전체를 다시 타이핑하는 것보다 "수정이 일어났다"는 것을 훨씬 분명하게 전달합니다. 이야기가 *변경*이라면 이 블록을 쓰고, *처음부터 작성*하는 것이라면 `code-typing`을 쓰십시오.
</Tip>

### 타이핑 리빌 프롬프트하기

`code-typing`은 캐럿이 진행 지점을 따라가며 코드를 한 글자씩 드러냅니다. CSS 애니메이션을 쓰지 않으므로 특정 시점으로 깔끔하게 이동(seek)할 수 있습니다. 정확한 코드와 속도를 주면 에이전트가 블록의 구문 토큰을 여러분의 스니펫에 맞게 다시 만듭니다.

> /motion-graphics 6-second 1920x1080 video. A dark editor types this snippet, character by character, caret tracking the frontier, then holds on the blinking cursor for the final second:
>
> ```
> export async function render(comp: Composition) {
>   await comp.seek(0);
>   return comp.capture();
> }
> ```
>
> Use the `code-typing` registry block. No narration, no image or media files.

<DocsVideo title="HyperFrames video: Validate Code Typing" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-code-typing.mp4#t=0.1" loop />

*위 프롬프트에서 렌더링했으며, 편집하지 않았습니다.*

**코드는 리터럴 블록으로 인용하십시오.** 코드를 산문으로 설명하면 paraphrase됩니다.

* ❌ `type out a function that seeks to zero and captures`
* ✅ 실제 스니펫을 펜스 블록에 넣으십시오 — 그대로 렌더링됩니다

**캐럿이 머물 자리를 주십시오.** 컴포지션은 마지막 상태를 유지하므로, 정지 구간을 요청하지 않으면 마지막 프레임은 전체 스니펫이 굳은 화면이 됩니다. 이것이 [정지된 모션의 신호](/prompting/motion)입니다.

* ❌ `types the code and ends`
* ✅ `types the code, then holds on the blinking cursor for the final second`

### 디프나 하이라이트 프롬프트하기

"무엇이 바뀌었는지 보여 주기"에는 `code-diff`에 수정 전과 후를 넘기고, 변경분의 색을 맡기십시오. "이 줄을 보라"에는 `code-highlight`에 전체 문맥을 주고 대상 줄을 지정하십시오.

> /motion-graphics 6-second 1920x1080 video. Show this edit to `api.ts` as a colored diff — the removed line collapses in red, the added line expands in green:
> removed: `const res = await fetch(url)`
> added: `const res = await fetch(url, { signal })`
> Use the `code-diff` registry block. No audio.

<DocsVideo title="HyperFrames video: Validate Code Diff" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-code-diff.mp4#t=0.1" loop />

*위 프롬프트에서 렌더링했으며, 편집하지 않았습니다.*

> /motion-graphics 5-second 1920x1080 video. Show a 12-line config file; a highlight band sweeps to line 7 (`timeout: 30_000`) while the surrounding lines dim. Hold with line 7 lit and the cursor blinking. Use the `code-highlight` registry block. No audio.

<DocsVideo title="HyperFrames video: Validate Code Highlight" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-code-highlight.mp4#t=0.1" loop />

*위 프롬프트에서 렌더링했으며, 편집하지 않았습니다. 에이전트가 그럴듯한 주변 설정 줄을 만들어 넣으므로, 정확한 파일이 중요하다면 12줄 전체를 붙여 넣으십시오.*

**대상 줄을 모호하지 않게 지정하십시오.** 이 블록은 한 줄을 제외한 주변 문맥을 흐리게 처리하므로, 어느 줄인지 알려 줘야 합니다.

* ❌ `highlight the important line`
* ✅ `highlight line 7 (timeout: 30_000)`

### 스크롤 진행 프롬프트하기

`code-scroll`은 긴 파일을 따라 카메라를 내려 목표 줄을 가운데로 가져오고 그 줄을 스포트라이트합니다. 장난감 같은 짧은 스니펫이 아니라 실제 모듈을 둘러보는 데 쓰는 블록입니다.

> /motion-graphics 6-second 1920x1080 video. Scroll a \~60-line source file so line 44 (`return dedupeFrames(frames)`) arrives at center and gets spotlighted; ease the scroll and let it settle without snapping. Use the `code-scroll` registry block. No audio.

<DocsVideo title="HyperFrames video: Code Scroll" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/code-scroll.mp4#t=0.1" loop />

*위 프롬프트에서 렌더링했으며, 편집하지 않았습니다.*

**스크롤이 튀지 않고 이징되어 안정되게 요청하십시오.** 선형으로 움직이다 갑자기 멈추는 스크롤은 기계적으로 읽힙니다.

* ❌ `scroll straight to the line`
* ✅ `ease the scroll and let it settle` — [모션 문법](/prompting/motion)과 함께 쓰십시오

### 이름으로 테마 고르기

| 프로필 | 블록 | 프로필 | 블록 |
| - | - | - | - |

**VS Code 워크벤치 테마** — 에디터 전체 크롬(액티비티 바, 사이드바, 탭, 터미널, 상태 바)을 보여 줍니다. "monokai" 또는 "visual studio dark"라고 말하십시오:

| 이렇게 말하기 | 블록 | 이렇게 말하기 | 블록 |
| - | - | - | - |

<DocsVideo title="HyperFrames video: Terminal Ocean" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/terminal-ocean.mp4#t=0.1" loop />

*위 프롬프트에서 렌더링했으며, 편집하지 않았습니다.*

**테마를 보여 주려는 화면에 맞추십시오.** VS Code 에디터 크롬에 터미널 명령이 있으면 어색하게 보이고, Terminal.app에 소스 파일이 있으면 역시 어색합니다.

* ❌ `monokai theme typing a shell command`
* ✅ `apple terminal homebrew profile typing a shell command`

<Tip>
  모호한 표현은 가장 가까운 이름 있는 블록으로 해석됩니다. "Dark theme"은 지나치게 불분명합니다. 에이전트는 열두 가지 어두운 변형 중 하나를 고르므로, 떠올린 것과 다른 결과가 나올 수 있습니다. 테마 이름을 말하십시오. 이것은 코드에 적용한 [세부 수준 조절 다이얼](/prompting/specification-dial)입니다. 기본 선택이 빗나갈 수 있을 때는 블록 이름을 지정하십시오.
</Tip>

### 풀 리퀘스트와 함께 쓰기

애니메이션하려는 코드가 실제 PR에서 왔다면 비트를 손으로 쓰지 마십시오. [`/pr-to-video`](/prompting/code-and-prs) 워크플로가 디프를 읽고, 실제로 바뀐 hunk 주변에 `code-diff`, `code-highlight`, `code-scroll`을 구성합니다. 개념을 설명하는 중이라면 이 페이지의 블록을 직접 쓰고, 특정 변경 묶음을 내레이션하는 중이라면 PR 워크플로를 거치십시오.

### 다음으로 갈 곳

* [one-shot 프롬프트의 구조](/prompting/anatomy) — 위의 모든 프롬프트가 쓰는 골격입니다.
* [복사해서 쓰는 예제](/prompting/examples) — 각색할 수 있는 완전한 프롬프트입니다.
* [코드와 PR](/prompting/code-and-prs) — GitHub PR을 코드 변경 영상으로 바꾸는 방법입니다.
* [프리미엄처럼 읽히는 모션](/prompting/motion) — 코드 블록에도 필요한 정지와 안착 규칙입니다.

<Note>
  **캡스톤 스레드** — [Level 7 영화](/prompting/capstone)는 이 장의 기법으로 시작합니다. 실제 HyperFrames 마크업을 한 글자씩 타이핑하고, 타이핑된 줄의 기준선이 영화의 나머지 부분이 따라가는 타임라인 와이어로 자라납니다(아래는 영화에서 잘라낸 장면입니다).
</Note>

이 장면을 만드는 절은 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)에 있습니다. 여러분의 영상에 그대로 가져다 쓸 수 있는 프롬프트 문구입니다:

> **Type (0–7s).** Black-on-charcoal close-up: a cursor types real HyperFrames markup character by character — `<div class="clip" data-start="0" data-duration="4">` and a `gsap.timeline({ paused: true })` line. As the typed line completes, the text's baseline extends and becomes **the wire** — the underline literally grows into the timeline and the camera begins its dolly along it. The typed div folds into a compact clip chip (persistent element 3) that drops onto the wire. Kinetic display type states "WRITE HTML." as the travel begins.

<DocsVideo title="HyperFrames video: Capstone Region Type" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-type.mp4#t=0.1" loop />

*이 절을 렌더링한 결과이며, 완성된 영화에서 해당 영역만 잘라낸 것입니다.*

*다음: [데이터와 지도](/prompting/data-and-maps) — 코드 대신 차트, 통계, 지도를 다루는, 같은 "이름 있는 블록 + 인용된 문구" 패턴입니다.*


## 관련 주제

- [변경 이력](/changelog.md)
- [프롬프트 가이드](/prompting/overview.md)
- [트랜지션](/prompting/transitions.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 만들어져 호스팅됩니다.
