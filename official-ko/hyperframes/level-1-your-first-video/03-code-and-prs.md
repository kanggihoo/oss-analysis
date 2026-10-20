> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져옵니다.
> 더 살펴보기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾아보십시오.

# 코드 변경과 PR

> GitHub pull request를 코드 변경 설명 영상으로 바꾸려면 무엇을 말해야 하는지 — 변경 로그, 기능 공개, 수정, 리팩터링 안내.

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

두 번째 라이드입니다. 두 라이드 모두 페이지에 아직 아무것도 없는 상태에서 시작합니다. 이번에는 이미 존재하고 이미 사실인 것에서 시작합니다. 병합된 PR이 그것이고, diff 자체를 이야기로 만듭니다.

## 첫 번째 성과

[`/pr-to-video`](/prompting/overview)에 PR 링크를 가리키며 프롬프트 하나만 주면, 기법 없이도 완성된 코드 변경 설명 영상이 나옵니다.

[예시](/prompting/examples) 페이지에서 확인된 30초 기능 공개 영상입니다.

> /pr-to-video \[PR URL]에서 30초, 1920x1080 기능 공개 영상을 만들어주세요. diff가 아니라 사용자가 얻는 것으로 시작하세요. `code-diff` 블록으로 핵심 코드 변경을 한 비트에만 보여주세요. 버전 번호와 저장소 URL로 마무리하세요. 내레이션 없이, 대신 키네틱 자막을 쓰세요.

<DocsVideo title="HyperFrames video: Example Pr Video" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-pr-video-v2.mp4#t=0.1" loop />

*위 프롬프트로 렌더링했으며, 편집하지 않았습니다.*

## 무엇을 만드는가

GitHub pull request에서 만든 코드 변경 설명 영상입니다. [`/pr-to-video`](/prompting/overview) 워크플로는 `gh`로 PR을 읽습니다. diff, 커밋, 파일, 기여자를 읽은 뒤 이야기로 재구성하고, 코드 비트를 전용 diff 화면에 렌더링하면서 프레임 단위로 만듭니다.

입력은 **코드 변경**입니다. 웹사이트나 제품 페이지가 아닙니다. PR 링크(`https://github.com/owner/repo/pull/N`), `owner/repo#N` 참조, 또는 체크아웃된 저장소에서 "this PR"이라고 하는 것이 모두 작동합니다. 팔고 싶은 제품이라면 [`/product-launch-video`](/prompting/product-launch)를, PR이 없는 주제라면 [`/faceless-explainer`](/prompting/explainers)를 쓰십시오. 어느 쪽인지 모르겠다면 `/hyperframes`에서 시작하십시오.

## 중요한 조절 항목

기법을 하나도 배우기 전에, 프롬프트에서 이미 조절할 수 있는 것들입니다.

| 조절 항목 | 이렇게 말합니다 | 중요한 이유 |
| - | - | - |
| **영향 대 diff** | "diff가 아니라 사용자가 얻는 것부터" | 영상은 *변경*을 설명하며, diff를 소리 내어 읽지 않습니다. 영향으로 시작하면 코드보다 먼저 "왜 신경 써야 하나?"에 답합니다 |
| **hunk 개수** | "`code-diff` 비트는 하나만" / "hunk는 최대 두 개" | 코드 비트는 실제 hunk 2~4개를 각각 작고 읽기 쉬운 스니펫으로 보여줍니다. 파일 전체는 영상 크기에서는 읽을 수 없습니다 |
| **어떤 코드 블록** | 변경에는 `code-diff` · 리팩터링에는 `code-morph` · 새 코드에는 `code-typing` | 블록이 이야기와 맞아야 합니다. diff는 추가/삭제된 줄을 보여주고, morph는 한 모양이 다른 모양으로 바뀌는 것을 보여줍니다 |
| **관점** | "변경 로그" / "기능 공개" / "수정 설명" / "리팩터링 안내" | 이야기의 형태를 정합니다. 워크플로는 diff 순서대로 파일을 훑는 대신 PR을 그 형태로 재구성합니다 |
| **청중** | "개발자용"(기본) / "기술 혼합" / "비기술 이해관계자" | 내레이션이 가정하는 수준을 바꿉니다. 비기술 버전은 영향에 더 기대고 코드는 덜 씁니다 |
| **엔드 카드** | "버전 번호와 저장소 URL로 마무리" | 코드 설명 영상의 관례적인 마무리입니다. 무엇을 넣을지 말해서 실제 CTA가 되게 하고, 뒤늦은 생각이 되지 않게 하십시오 |
| **내레이션 대 자막** | "차분한 남성 내레이션" 또는 "내레이션 없이, 키네틱 자막" | 둘 다 지원됩니다. 자막만 쓰면 소셜용으로 무음 친화적이고, 내레이션은 더 긴 안내를 담습니다 |
| **길이** | 헤드라인 하나라면 "~30초", 큰 PR이라면 최대 "~3분" | 워크플로가 변경 크기를 읽고 등급을 추천합니다. 아주 큰 PR은 이야기의 상한이지, 채워야 할 하한이 아닙니다 |

<Tip>
  스타일은 워크플로의 따뜻한 에디토리얼 프리셋으로 고정되어 있으며, diff를 위해 만들어진 네이비 코드 화면을 씁니다. 코드 비트를 읽기 쉽게 만드는 것이 바로 이 부분입니다. 여기서는 테마를 고르지 않습니다. 관점, hunk, 내레이션을 고릅니다.
</Tip>

## 변형

<AccordionGroup>
  <Accordion title="변경 로그 요약">
    > /pr-to-video \[PR URL]에서 약 40초, 1920x1080 변경 로그 영상을 만들어주세요. 변경 로그 관점: 릴리스 줄로 시작한 뒤, 주요 변경마다 비트 하나씩. 각각 짧은 라벨과 "무엇을 하는지" 한 줄. 영상 전체에 `code-diff` hunk는 최대 두 개만 보여주세요. 버전과 저장소 URL로 마무리. 차분한 남성 TTS 내레이션, 자막 없음.

    <DocsVideo title="HyperFrames video: Variant Pr Changelog" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/variant-pr-changelog.mp4#t=0.1" loop />

    *\[PR URL] = heygen-com/hyperframes#2092로 이 프롬프트에서 렌더링했으며, 편집하지 않았습니다.*

    변경 로그는 깊이를 넓이와 맞바꿉니다. 하나의 변경을 깊이 파고드는 대신, 많은 작은 변경을 각각 비트 하나로 다룹니다. 속도를 빠르게 유지하도록 코드 비트는 드물게 두십시오. PR에는 배포 버전이 적혀 있지 않으므로, 에이전트는 main의 릴리스 태그나 패키지 매니페스트에서 버전을 찾습니다.
  </Accordion>

  <Accordion title="수정 설명">
    > /pr-to-video \[PR URL]에서 약 40초, 1920x1080 수정 설명 영상을 개발자용으로 만들어주세요. 수정 관점: 먼저 버그의 증상을 말하고, 그다음 근본 원인, 그다음 `code-diff` 블록에서 한 줄짜리 수정. 버전과 저장소 URL로 마무리. 내레이션 없이, 키네틱 자막.

    수정은 증상 → 원인 → 해결의 흐름으로 읽힙니다. 사용자가 본 고장으로 시작하고, 스택 트레이스로 시작하지 마십시오. diff는 시작이 아니라 보상입니다.
  </Accordion>

  <Accordion title="리팩터링 안내">
    > /pr-to-video \[PR URL]에서 약 70초, 1920x1080 리팩터링 안내 영상을 개발자용으로 만들어주세요. 리팩터링 관점: 예전 구조가 왜 불편했는지, 그다음 새 구조, 핵심 파일의 전후 비교는 `code-morph` 블록으로 보여주세요. 버전과 저장소 URL로 마무리. 차분한 남성 TTS 내레이션.

    리팩터링은 동작은 그대로 두고 모양만 바꿉니다. 그래서 이야기는 새 구조가 *왜* 더 나은지입니다. `code-morph`는 한 형태가 다른 형태로 바뀌는 과정을 애니메이션으로 보여줍니다. 요점이 줄 단위 차이가 아니라 전환일 때 맞는 블록입니다.
  </Accordion>
</AccordionGroup>

## 흔한 실패 유형

**프리셋 위에 테마를 강제로 씌우기.** 일반 규칙은 [라이드 1](/prompting/product-launch#common-failure-modes)에 있습니다. 여기서 구체적인 이유는, 네이비 코드 화면이 diff 가독성에 맞게 조율되어 있어서 다른 테마를 쓰면 워크플로가 가장 잘하는 한 가지를 잃기 때문입니다.

* ❌ `/pr-to-video ... 어두운 테마, 네온 강조색`
* ✅ 프리셋이 룩을 맡게 하고, 구체성은 관점과 코드 비트에 쓰십시오

**diff 전체를 요청하기.** PR 영상은 변경을 설명하며, 모든 파일을 읊지 않습니다. 전체 diff는 영상 크기에서는 읽을 수 없습니다.

* ❌ `diff 전체를 파일 단위로 훑어줘`
* ✅ `핵심 hunk 2~3개만, 각각 작고 읽기 쉬운 스니펫으로`

**코드로 시작하기.** diff는 훅이 아니라 보상입니다. 변경이 무엇을 뜻하는지로 시작하십시오.

* ❌ `diff로 시작하고 그다음 무엇을 하는지 설명`
* ✅ `사용자가 얻는 것으로 시작한 뒤 핵심 hunk를 보여주기`

**내레이션 컷에 고정 시간 지정하기.** [라이드 1](/prompting/product-launch#common-failure-modes)과 같습니다. 말하는 길이가 런타임을 정하므로 범위로 말하십시오.

* ❌ `40초짜리 내레이션 안내`
* ✅ `약 40초짜리 내레이션 안내`

이 레벨이 따르는 워크플로는 [PR에서 영상으로](/guides/pr-to-video)에 문서화되어 있습니다. 입력으로 무엇을 받는지, 만들기 전에 무엇을 묻는지, 무엇을 돌려주는지 설명합니다.

*다음: [자막과 토킹 헤드 영상](/prompting/captions-and-talking-heads). 같은 한 번의 프롬프트 방식을, 이번에는 이미 찍어 둔 영상을 꾸미는 데 씁니다.*


## 관련 주제

- [설명 영상](/prompting/explainers.md)
- [코드 애니메이션](/prompting/code-blocks.md)
- [Week in Merges](/catalog/blocks/week-in-merges.md)


이 문서는 개발자 문서 플랫폼인 [Mintlify](https://mintlify.com)로 작성되고 호스팅됩니다.
