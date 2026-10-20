> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져올 수 있습니다.
> 더 탐색하기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾아보세요.

# 모션 그래픽

> 짧고 디자인 중심의 작품으로, 모션 자체가 메시지입니다 — 키네틱 타입, 수치 강조, 로고 스팅 — 그리고 MP4와 투명 오버레이를 가르는 설정들.

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

다섯 번 라이드를 마쳤고, 입력도 다섯 가지였습니다 — 사이트, 평문, PR, 푸티지, 트랙. 이번 마지막은 내레이션과 에셋 입력을 아예 뺍니다. 모션만으로 메시지를 전하는 짧고 디자인 중심의 모션 그래픽입니다.

## 첫 번째 성과

[`/motion-graphics`](/prompting/overview)에 비트를 자세히 적은 프롬프트 하나만 주면, 아직 어떤 기법도 필요 없이 완성된 모션 그래픽을 얻을 수 있습니다.

표준 형태는 다음과 같습니다. 라우팅되고, 사양이 정해지고, 비트마다 타임스탬프가 붙고, 문구가 인용되고, 기법이 고정되고, 빈틈이 메워집니다.

> /motion-graphics Make an 8-second 1920x1080 video. Beat 1 (0-4s): dark macOS terminal types "npx skills add heygen-com/hyperframes" character by character, then hold on the blinking cursor. Beat 2 (4-5s): the terminal shatters into fragments. Beat 3 (5-8s): bold white kinetic text on black slams in word by word, snappy: "YOU JUST MADE THIS / WITH HYPERFRAMES." Adapt the `code-typing` and `vfx-shatter` registry blocks; hand-author the kinetic text. No narration, no image or media files.

<DocsVideo title="HyperFrames video: Validate Anatomy Terminal" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-anatomy-terminal.mp4#t=0.1" loop />

*위 프롬프트에서 렌더링했으며, 편집하지 않았습니다.*

## 모션 그래픽이란

모션 그래픽은 **모션이 메시지인** 짧고 디자인 중심의 작품입니다. 키네틱 타이포그래피, 수치 카운트업, 차트 히트, 로고 스팅, 하단 자막이나 소셜 오버레이, 애니메이션 지도, 트윗, 헤드라인이 여기에 해당합니다. 보통 10초 미만(최대 \~30초)이며, 내레이션이나 실사 피사체가 없고, MP4 또는 투명 오버레이로 렌더링됩니다.

`/motion-graphics`로 라우팅합니다. 워크플로는 설계상 자율적입니다. 명확화 질문은 많아야 하나이고, 그다음은 렌더까지 곧장 갑니다. 작품이 "모션이 메시지"라는 범위를 넘어서면 다른 워크플로를 쓰세요.

| 작품이... | 대신 라우팅 |
| - | - |
| 더 길거나, 다중 장면이거나, 내레이션이 있음 | `/general-video` |
| 웹사이트의 내레이션 영상 | `/product-launch-video` |
| 음성 해설이 있는 주제 설명 영상 | `/faceless-explainer` |
| 제품 프로모 / 런치 | `/product-launch-video` |
| 기존 푸티지의 자막 | `/embedded-captions` |

## 중요한 설정값들

기법을 배우기 전에도 프롬프트에서 이미 조정할 수 있는 것들입니다.

**길이.** 짧게 유지하세요. 모션 그래픽은 10초 미만이며, 최대 \~30초입니다. 2초짜리 아이디어를 8초로 늘이면 어떻게 애니메이션을 하든 느리게 느껴집니다. 작품에 정말 여러 장면이나 더 긴 러닝 타임이 필요하다면 그것은 모션 그래픽이 아니라 `/general-video`입니다.

**MP4 대 투명 오버레이.** 기본 출력은 MP4입니다. 투명 오버레이 — 다른 푸티지 위에 합성될 하단 자막, 콜아웃, 버그 — 를 요청하면 렌더는 알파가 있는 `webm` 또는 `mov`를 대상으로 합니다. 프레임의 일부가 *비어 있어야 하는* 경우에만 투명도가 의미를 가집니다. 전체 프레임 디자인(자체 배경을 가장자리까지 채운 구성)은 투명하게 만들 것이 없으므로, 그런 곳에 투명 WebM을 요청하면 불투명 파일이 나오거나 깨져 보이는 파일이 나옵니다. "transparent overlay, alpha channel"이라는 말은 다른 무엇인가 위에 놓이도록 설계된 작품에만 쓰세요.

**레지스트리 블록 대 자유 형식.** 블록 이름(`apple-money-count`, `x-post`, `data-chart`, `code-typing`, `us-map` / `world-map`)을 지정하면 에이전트는 재사용 우선으로 구성합니다. 블록을 설치하고, 제자리에서 맞춤화하고, 빈틈만 직접 작성합니다. 블록을 생략하면 설명에서 처음부터 만듭니다. 일회성 룩에는 괜찮지만, 고정하지 않은 세부 사항에서 드리프트가 더 많이 생깁니다. 블록 이름은 [카탈로그](/catalog/blocks/data-chart)에 나온 그대로 쓰세요.

**이징과 모션의 느낌.** *어떻게* 움직이는지 묘사하는 단어들 — "snappy", "bouncy", "settles with overshoot" — 은 특정 이징에 대응합니다. 아끼지 말고 쓰세요. 형용사와 이징의 대응표는 [어휘](/prompting/vocabulary)를, 작품이 싸구려로 읽히지 않게 하는 문법(무엇도 완전히 멈추지 않음, 동작이 겹침, 카메라가 연기함)은 [프리미엄 모션](/prompting/motion)을 참고하세요.

## 변형

각각은 레지스트리 블록을 재사용하므로, 에이전트가 처음부터 직접 만들지 않고 구성합니다.

<AccordionGroup>
  <Accordion title="Stat count-up">
    > /motion-graphics 6-second 1920x1080 video, dark navy background. Beat 1 (0-1s): label "ARR" fades up small, top-center. Beat 2 (1-4s): a giant number counts up to \$4.2M with an odometer roll, easing out as it lands. Beat 3 (4-6s): "+312% YoY" stamps in below in green, then everything settles into a gentle ambient idle (subtle breathing scale, slow particle drift). Use the `apple-money-count` registry block as base. No narration.
  </Accordion>

  <Accordion title="Logo sting">
    > /motion-graphics 5-second 1920x1080 logo sting. Beat 1 (0-2s): the word "ACME" assembles from scattered particles. Beat 2 (2-3s): full-frame `swirl-vortex` shader transition. Beat 3 (3-5s): logo lockup + tagline "Ship faster." settles on white, then holds with a subtle ambient idle (slow breathing scale). Use `code-particle-assemble` for the assembly.
  </Accordion>

  <Accordion title="Animated tweet">
    > /motion-graphics 7-second 1080x1350 vertical video. A real tweet card (handle @hyperframes, text "we render video from HTML now. no timeline UI. just code.") slides up over a soft animated gradient, likes counter ticks 0→1.2K, then the card tilts in 3D and a highlight sweeps the second sentence. Settle into a gentle ambient idle on the card at the end. Use the `x-post` and `vfx-liquid-background` registry blocks. No narration, no image or media files.
  </Accordion>

  <Accordion title="Map route">
    > /motion-graphics 8-second 1920x1080 video. Dark world map, a glowing arc animates from San Francisco to Tokyo over 3s, destination pin drops with a pulse, then camera zooms into Tokyo and the label "LATENCY: 89ms" types on. Use the `nyc-paris-flight` registry block as the base pattern, restyle to teal on charcoal. No narration.
  </Accordion>
</AccordionGroup>

## 실패 모드

**전체 프레임 디자인에서 투명 출력.** 알파는 전체 프레임을 채우는 작품이 아니라 오버레이 요소를 위한 것입니다. 자체 배경이 있는 디자인에는 내보낼 투명 영역이 없습니다.

* ❌ `an 8s full-screen stat count-up on dark navy — export as a transparent WebM`
* ✅ `an 8s stat count-up on dark navy, MP4` — 또는 푸티지 위에 합성될 버그라면: `just the count-up chip, no background, transparent overlay (webm)`

**모션이 메시지인 작품에 내레이션.** 모션 그래픽은 정의상 내레이션이 없습니다. 시각 요소가 메시지를 전합니다. 음성 해설은 다른 워크플로를 뜻합니다.

* ❌ `/motion-graphics a 10s logo sting with a voice-over reading the tagline`
* ✅ `/motion-graphics a 10s logo sting, no narration` — 음성 트랙이 필요하면 `/faceless-explainer` 또는 `/general-video`를 쓰세요.

**짧은 아이디어를 길게 늘이기.** 러닝 타임은 조정 가능한 설정이지만, \~30초를 넘으면 단일 모션 비트는 할 일이 떨어집니다.

* ❌ `a 45-second kinetic-type piece of one headline`
* ✅ `an 8-second kinetic-type piece of one headline` — 또는 다중 장면 `/general-video`로 승격하세요.

<Tip>
  여섯 부분으로 된 골격과 이 프롬프트들이 공유하는 비트별 내용 공식은 [프롬프트 해부](/prompting/anatomy)를, 실제로 실행해 검증된 예시 전체는 [검증된 예시](/prompting/examples)를 보세요. 요청이 모션 그래픽인지 확신이 없다면 `/hyperframes`의 라우터에서 시작하세요.
</Tip>

이 레벨이 따르는 워크플로는 [모션 그래픽](/guides/motion-graphics)에 문서화되어 있습니다 — 무엇을 입력으로 받는지, 빌드 전에 무엇을 묻는지, 무엇을 돌려주는지.

*다음: [프롬프트 해부](/prompting/anatomy) — 여섯 가지 하나짜리 프롬프트 입력을 통해 워크플로를 타 왔습니다. 레벨 2에서는 프롬프트 자체를 엽니다.*

## 관련 주제

- [모션 그래픽 만들기](/guides/motion-graphics.md)
- [첫 영상 만들기](/quickstart.md)
- [HyperFrames 30일](/thirty-days.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 빌드되어 호스팅됩니다.
