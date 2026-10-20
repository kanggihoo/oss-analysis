> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져오세요.
> 더 살펴보기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾으세요.

# 본 것 재현하기

> 움직임을 전사하고, 절대 목표값으로 반복하고, 상수를 추출하며, 텍스트만으로 도달할 수 있는 한계를 파악하세요.

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

[반복 작업](/prompting/iterating)에서는 수정 루프 전반을 다뤘습니다. 이 페이지는 그 루프의 가장 어려운 시험입니다. 여러분이 만들어 낸 분위기가 아니라, 직접 본 특정 레퍼런스에 맞추는 작업입니다.

텍스트만으로도 레퍼런스의 약 90%까지는 도달할 수 있습니다. 여기에는 특정한 워크플로가 필요하고, 한계가 어디인지 알아야 합니다. 두 가지 모두 아래에서 설명합니다.

<Note>
  이 페이지의 퍼센트는 이 가이드의 재현 빌드를 프레임 단위로 비교한 관찰 결과입니다. 정확한 보장이 아니라 곡선의 모양으로 받아들이세요.
</Note>

## 구성뿐 아니라 움직임도 전사하기

레퍼런스를 프레임 단위로 보면서 다음을 적어 두세요.

* 정확한 길이
* 카메라의 경로
* 각 요소가 하는 일과 타임스탬프
* 등장 애니메이션이 겹치는 방식
* 어느 레이어가 블러 처리되어 있는지
* 샘플링한 색상

이렇게 작성한 프롬프트는 목표의 약 75%를 한 번에 만들어 냅니다. 구조와 움직임의 흐름은 맞지만, 렌더링 보정은 맞지 않습니다.

## 절대 목표값으로 반복하기

렌더를 레퍼런스 프레임과 프레임 단위로 비교하세요. 그다음 한 번에 한 축씩 고치고, 이미 맞는 부분은 고정하세요.

수정 사항은 상대적인 조정이 아니라 절대값으로 말하세요.

* ❌ `make dots 2x finer`
* ✅ `dot radius = 25% of row spacing`

상대적 수정은 진자처럼 흔들립니다. 너무 크다가, 너무 작다가, 다시 너무 커집니다. 수렴하기까지 몇 라운드는 예상하세요.

## 수렴한 값을 프롬프트에 다시 담기

반복 작업은 탐색입니다. 그 과정에서 찾은 상수는 재사용할 수 있습니다.

이 상수를 담은 프롬프트는 새로 만든 빌드에서 수렴된 품질의 약 **80–90%**를 한 번에 만들어 냅니다. 이산적인 사실(타이밍, 개수, HEX 값, 비율, 카메라 호)은 손실 없이 옮겨집니다. 연속적인 특성(글로우의 두드러짐이나 프레이밍의 느낌 같은 것)은 보정 메모 한두 개만큼 여전히 달라집니다.

수렴된 컴포지션 파일 자체가 픽셀 단위로 정확한 결과물입니다. 렌더는 결정론적이므로, 그 파일을 다시 렌더하면 결과가 재현됩니다.

다음은 방송 스타일의 애니메이션 지구본을 한 번에 만들어 내는 추출된 스펙입니다:

<Accordion title="Worked example: the hologram globe (full distilled spec)">
  > 1.8초, 1920x1080 영상. 어댑터를 통한 Three.js(시크 기반, rAF 없음). 하나의 연속된 샷. 마지막 프레임에서도 모든 요소가 여전히 움직입니다.
  >
  > **FIELD**
  >
  > * 청보라색 배경, 위에서 아래로 linear #2a24a8 → #12105e, 가운데에 부드러운 방사형 밝기
  > * 흐릿한 세로 청록색 빛줄기(#5ee0e8, 불투명도 약 10%, 간격 약 340px)가 조각 전체에 걸쳐 왼쪽으로 70px 흘러감
  > * 깊은 모서리 비네팅
  > * 소프트 라이트 필름 그레인, 약 6%(시드 노이즈)
  >
  > **GLOBE**
  >
  > * 로열 블루 구체(#4348f2), 왼쪽 위에서 비추며 0.58 환경광 바닥
  > * 넓고 은은한 새틴 띠(#6470ff, 매우 넓은 감쇠, 약 30% 혼합)가 위쪽 곡선을 쓸고 지나감
  > * 강한 청록색 림 라이트 선(#5ee8f0)이 윗가장자리만 따라감
  > * 대륙은 두 개의 레이어로 표현:
  >   * (a) 표면 바로 아래에 있는, 매우 흐려진 어두운 파란색 실루엣(#3439c2, 불투명도 80%). 부드러운 그림자 모양으로 읽힙니다.
  >   * (b) 표면 바로 위의 도트 매트릭스. 등면적 격자(위도 행 0.9°, 위도가 높아질수록 경도 간격이 넓어짐)
  > * 점 반지름 = 행 간격의 24–28%. 점 사이에 뚜렷한 파란 틈이 있으며, 적도 쪽으로 갈수록 약간 커짐. 점 불투명도 85%
  > * 두 가지 색상 집단: 북쪽은 청록색 아쿠아 #5ee0e8, 위도 약 32°부터 남쪽은 봄 초록 #7ce97a. 시드 기반으로 점마다 ±30% 밝기 차이
  > * 시점 공간의 오른쪽 아래 그림자 영역에서는 점이 40%로 어두워짐
  > * 대륙은 보이는 반구의 약 30–35%를 덮는 뚜렷한 점선 육지로 읽히며, 나머지는 로열 블루 바다가 대부분
  >
  > **CAMERA**
  >
  > * 극도로 가까이에서 시작: 구체의 곡선이 화면 전체를 채우고, 수평선은 위 모서리 밖으로 나감
  > * 이어서 하나의 연속된 뒤로 빼기 + 크레인 이동(fov 52°→40°)
  > * 돔이 아래 절반을 가장자리에서 가장자리까지 채우며 끝남. 실루엣이 양쪽 프레임 가장자리에 닿고, 수평선은 약 45%
  > * 1.8초를 렌더하면서 2.0초 구간에 대해 ease power1.inOut을 계산하므로, 움직임은 화면에서 끝까지 안정되지 않음
  > * 지구본은 수직축을 기준으로 28° 회전(linear). 대륙은 오른쪽에서 왼쪽으로 계속 흘러가며 멈추지 않음
  >
  > **ORBS** — 세 개의 깊이 평면에 걸친 12개. 상단 반구에 월드 고정, 줄기가 수직을 유지하도록 함
  >
  > * 0.45초→1.15초에 걸쳐 엇갈린 시작으로 튀어나옴(간격 0.06–0.13초)
  > * 각각 0.44–0.56초 동안 back.out 오버슛으로 상승(오브마다 1.7–2.6 변화), 이후 위상이 어긋난 사인 곡선으로 ±8px씩 영원히 흔들림
  > * **중간 레이어 5개**(마무리 프레이밍에서 약 90–110px): 부드러운 민트색 본체 #a7ecc4, 왼쪽 아래의 짙은 녹색 그림자 #3f9b5e, 오른쪽 위의 연한 림 #d6ffe8, 흰색 코어 없음
  >   * 각각은 지름의 약 3.5배인 부드러운 가산(additive) 블룸 스프라이트로 감싸며, 이 텍스처는 가운데가 비어 있고 오브 가장자리 바로 바깥에서 약 35%로 정점을 찍음. 불투명 오브 위의 밝은 코어 글로우는 민트를 라임색으로 날려 버림
  >   * 반지름의 약 4.2배인 얇고 부드러운 헤일로 링(불투명도 60%)을 더하며, 항상 오브 자체보다 약하게 두고 5% 크기의 느린 맥동을 줌
  > * **배경 4개** — 약 30px, 선명하고, 더 조밀한 블룸
  > * **전경 근거리 렌즈 보케 3개** — 약 160–190px, 카메라를 따라가는 조밀한 민트색 방사형 그라데이션 스프라이트. 중앙 왼쪽 / 가운데 아래 / 오른쪽 위에 놓이며, 불투명도 약 70%, 좌우로 ±30px 흘러감, 줄기 없음
  > * **줄기** — 2–3px 가산 청록색 원기둥이 표면에서 투명하게 사라짐
  > * 캔버스로 생성한 스프라이트 텍스처는 sRGB로 설정하세요. 그렇지 않으면 민트색이 창백하게 씻겨 나갑니다
  >
  > **CAPTION** — "Across 82 Countries"
  >
  > * Inter 300, 34px, 자간 0.06em, 흰색 90%, 위에서 12% 지점 가운데 정렬
  > * 왼쪽에서 오른쪽으로 글자별 페이드인, t=1.0초에 시작해 약 1.45초에 완료
  > * 이후 6px 위로 천천히 떠오르며, 마지막 프레임에서도 여전히 감속 중
  >
  > 오디오 없음.

  <DocsVideo title="HyperFrames video: Recreate Globe Oneshot" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/recreate-globe-oneshot.mp4#t=0.1" loop />

  *새로 만든 빌드에서 이 정확한 스펙으로 만든 한 번에 렌더한 결과입니다. 반복 작업은 없습니다.*
</Accordion>

## 텍스트만으로 가능한 한계 파악하기

텍스트는 셀 수 있는 이산적인 것들을 손실 없이 담습니다. 하지만 블룸의 감쇠, 재질감, 광학적 색 혼합 같은 연속적인 지각 특성은 충분히 규정하지 못합니다.

마지막 10%는 텍스트로는 좁혀지지 않고, 대신 진동합니다. 픽셀 단위의 정확함이 필요하다면 컴포지션 파일을 보관하세요.

## 관련 링크

<CardGroup cols={2}>
  <Card title="Iterating" href="/prompting/iterating">이 페이지가 한계까지 밀어붙이는 수정 루프</Card>
  <Card title="High-fidelity looks" href="/prompting/visual-specs">재현에 필요한 스펙 밀도를 작성하기</Card>
  <Card title="Runtimes and 3D" href="/prompting/runtimes-and-3d">worked example이 쓰는 어댑터</Card>
  <Card title="Capstone" href="/prompting/capstone">하나의 필름으로 합쳐진 모든 기법</Card>
</CardGroup>

*다음: [렌더링과 출력](/prompting/rendering-and-output) — 컷이 확정된 뒤, 올바른 내보내기를 고르는 말.*


## 관련 주제

- [렌더링과 출력](/prompting/rendering-and-output.md)
- [반복 작업](/prompting/iterating.md)
- [프롬프트 가이드](/prompting/overview.md)


이 문서는 [Mintlify](https://mintlify.com)로 빌드되고 호스팅되는 개발자 문서 플랫폼에서 제공됩니다.
