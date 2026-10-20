> ## Documentation Index
> Fetch the complete documentation index at: https://hyperframes.heygen.com/llms.txt
> Use this file to discover all available pages before exploring further.

# 고충실도 룩

> 모든 요소의 이름, 위치, 색, 시간을 적은 시각 사양을 작성해, 단어만으로도 특정한 룩이 전달되게 합니다.

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

이것은 [사양 다이얼](/prompting/specification-dial)의 세 번째 설정을
끝까지 밀어붙인 것입니다. [어휘](/prompting/vocabulary) 목록에 있는
단어가 아닙니다. 장면의 모든 요소를 디자이너의 사양서처럼 적은 것입니다.

단어만으로도 특정한 룩을 전달할 수 있지만, 프롬프트가 사양서처럼 읽힐 때만
가능합니다. 모든 요소가 이름 붙고, 위치가 정해지고, 색이 지정되고, 시간이
정해져 있어야 합니다.

## 느슨한 설명과 사양서

느슨한 설명은 에이전트가 추측할 여지를 남깁니다. "dark night scene, mountain,
glowing ring, title fades in." 같은 문장이 그렇습니다. 같은 장면을 사양서로
적으면 다음과 같습니다.

> 8-second 1920x1080 title card. Scene, back to front: #0a0e2a night sky with faint grain; an orange radial glow (#ff6a2b core \~150px, falling off to transparent by \~430px) igniting at the mountain peak's right shoulder from 2s, positioned so its upper falloff reaches the wordmark's baseline; over it a huge concentric ring system (5 rings, 1px strokes at 8% white opacity, innermost ring glowing #4a5fd9) centered 40% from the top; a low-poly mountain (6-8 dark navy facets, #141a3d–#1e2650) filling the lower third with its apex left of center, a white road S-curving up its face with a soft glow; thin horizontal cloud streaks (white, 6% opacity) drifting right at two heights; a man's silhouette, pure black, \~90px tall, bottom-right, fading in at 2.5s. At 3.5s "SHOWREEL" — thin geometric sans, \~140px, 0.35em tracking, white at 90% — fades in per letter across the ring center, the glow bleeding up through the letterforms above the peak. Slow 4% push-in across the full 8s. No audio.

<DocsVideo title="HyperFrames video: Spec Showreel" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/spec-showreel.mp4#t=0.1" loop />

*위 사양으로 렌더링했으며, 편집하지 않았습니다.*

<Note>
  이 사양에서 두 절은 **실제로 만들어 보면서 수정되었습니다.**

  첫 번째 초안은 장면을 "back to front"로 나열했는데, 그 뒤에 링을 배치했고
  정작 링 *뒤에* 있다고 설명한 글로우를 나중에 적었습니다.

  또한 글로우 크기를 "\~300px"로 잡았습니다. 너무 작았습니다. 같은 문장이 고정한
  링 중심과 산의 위치를 고려하면, 글로우가 통과해서 번져야 할 워드마크에
  물리적으로 닿을 수 없습니다.

  두 오류 모두 페이지에서는 보이지 않습니다. 누군가 렌더링하는 순간 분명해집니다.
  이것이 이 가이드가 따르는 [검증 규칙](/prompting/iterating#the-gates-cant-tell-you-its-good)의
  근거입니다. 쓸모 있을 만큼 촘촘한 사양은 내부적으로 모순되기도 쉽고, 그것을
  찾아내는 것은 렌더링뿐입니다.
</Note>

## 사양이 담지 못하는 것

위의 모든 요소는 에이전트가 직접 만들 수 있는 기본 요소입니다. 솔직한 한계는
두 가지입니다.

* **유기적 일러스트레이션** — 그려진 캐릭터, 회화적 질감. 단어로는 그림을
  충분히 결정할 수 없습니다. "flat rounded-geometric figure, circle head, no facial features"처럼
  기하학적 형태 언어로 유도하거나, 아트워크를 생성하십시오. [아트워크를 생성해야 할 때](/prompting/generated-artwork)를
  참고하십시오.
* **사진과 실사 촬영 콘텐츠**는 파일로 제공해야 합니다. 경로를 명시적으로 언급하십시오.

## 밀도 계약

사양은 빌더에게 각 요소가 *무엇인지* 알려 줍니다. 밀도 계약은 모든 프레임이
얼마나 채워져야 하는지 알려 줍니다.

[7단계 필름](/prompting/capstone)은 계약을 한 번 명시하고, 모든 영역이 이를
따릅니다. 이는 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)에서
그 계약을 확보하는 문장입니다.

> Density: every region fills three roles — one focal element at display scale, at least two supporting elements on their own cues, and the chrome/wire. Asymmetric compositions; display type \~a tenth of frame width; three depth layers with parallax between them \[…]

이것이 공식 전체이며, 어떤 프롬프트에도 재사용할 수 있습니다. **초점 요소 하나,
최소 두 개의 보조 요소, 그리고 항상 보이는 크롬.** 구성은 비대칭으로 하십시오.
60/40 비율이 좋고, 빈 공간 한가운데 요소 하나만 두지 마십시오. 디스플레이 타입은
프레임 너비의 대략 10분의 1 크기로 잡으십시오. 시차로 공간감을 살릴 수 있도록
깊이 레이어는 최소 세 개를 쓰십시오.

보조 요소는 각자의 신호에 맞춰 등장해야 합니다. 세 역할을 모두 t=0에서 채운
프레임은 장면이 아니라 포스터입니다.

빌드 결과가 계속 희박하게 나온다면 계약을 명시적으로 요청하십시오. "Every scene
carries one focal element, two supporting elements on staggered cues, and the
persistent chrome"은 빌더가 그대로 지키도록 요구할 수 있는 문장입니다.

## 두 가지 추가 작업 사양 예시

같은 밀도를 제품 UI 작업과 타이포그래피 작업에 적용했습니다. 두 예시 모두 이
정확한 문장에서 한 번에 만들어졌습니다.

빌더가 첫 번째 패스에서 판단을 내려야 했던 곳은, 아래 사양이 그 판단을 고정합니다.
이것이 이 사양들이 따르는 편집 루프입니다. 만들고, 단어가 무엇을 충분히 결정하지
못했는지 보고, 그다음 단어를 조입니다.

> 6-second 1920x1080. A frosted-glass command palette (640x84px, 20px radius, rgba(255,255,255,0.08) fill, 1px rgba(255,255,255,0.25) border, heavy backdrop blur) centered on a #0b0f1a field with two soft accent glows drifting slowly — #5b6cff upper-left, #22d3a5 lower-right, \~400px, 20% opacity. At 0.4s the palette scales in 0.96→1 settling with back.out(1.2). At 0.8s a grey placeholder "Search commands…" types on; at 2.2s it fades out over 0.2s and the query "render 4k" types in white. At 2.8s three result rows (56px tall, 12px gaps: icon square, label, shortcut chip) cascade in as a detached list below the fixed bar, staggered 0.12s, each rising 12px with back.out(1.4). At 4.2s a 10%-opacity #5b6cff fill sweeps left to right across the first row and its shortcut chip pulses once. Rows and glows keep a barely-visible drift to the end. No audio.

<DocsVideo title="HyperFrames video: Spec Command Palette" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/spec-command-palette.mp4#t=0.1" loop />

*위 사양으로 렌더링했으며, 편집하지 않았습니다.*

> 7-second 1920x1080. Off-black #101014 field with fine static film grain at 4%. The word "PRECISION" in \~220px heavy condensed caps (a heavy system face condensed with scaleX 0.82), white, 0.02em tracking, centered: its letters assemble from alternating top/bottom 40px offsets with power3.out and a 0.05s stagger, starting 0.3s. At 1.8s a 2px hairline rule draws left-to-right beneath the word, 60% of its width, centered. At 2.4s a 40px tabular-mono counter fades in below and ticks 99.999 → 00.001 mm over 2.2s with expo.out deceleration. At 5.2s the whole lockup eases to 1.03 scale over 0.5s while the word cools from white to #d8d8de, then settles into a slow ±1% breathing idle to the end. No audio.

<DocsVideo title="HyperFrames video: Spec Precision Type" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/spec-precision-type.mp4#t=0.1" loop />

*위 사양으로 렌더링했으며, 편집하지 않았습니다.*

*다음: [검증된 예시 프롬프트](/prompting/examples) — 레벨의 갤러리이며, 이제
익힌 어휘와 함께 읽습니다.*

## 관련 주제

* [사양 다이얼](/prompting/specification-dial) — 이 페이지가 맨 위에 자리한 세 가지 설정
* [출력을 바꾸는 어휘](/prompting/vocabulary) — 완전한 사양이 대체하는 단일 단어들
* [아트워크 생성 시점](/prompting/generated-artwork) — 단어가 충분히 결정하지 못하는 룩을 위해
* [반복 작업](/prompting/iterating) — 촘촘한 사양이 필요로 하는 렌더 후 확인 루프
* [검증된 예시 프롬프트](/prompting/examples) — 이 밀도의 프롬프트를 더 보려면


## 관련 주제

- [출력을 바꾸는 어휘](/prompting/vocabulary.md)
- [렌더링과 출력](/prompting/rendering-and-output.md)
- [Anamorphic Streak Flare](/catalog/blocks/vfx-anamorphic-flare.md)


이 문서는 [Mintlify](https://mintlify.com)로 빌드되고 호스팅됩니다. Mintlify는 개발자 문서 플랫폼입니다.
