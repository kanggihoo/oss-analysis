> ## Documentation Index
> 전체 문서 색인은 다음 주소에서 가져올 수 있습니다: https://hyperframes.heygen.com/llms.txt
> 다른 페이지를 살펴보기 전에 이 파일로 사용 가능한 모든 페이지를 찾아보세요.

# 뮤직 비디오와 슬라이드쇼

> 음악과 슬라이드가 주도하는 두 가지 결과물입니다. 브리프에서는 비슷해 보이지만 결과물은 다릅니다. 하나는 비트에 맞춰 만든 MP4이고, 다른 하나는 탐색할 수 있는 덱입니다. 어느 쪽으로 보낼지 정하는 방법을 설명합니다.

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

영상을 꾸몄고 PR을 이야기로 바꿨습니다. 이제 구동 입력이 다시 바뀝니다. 트랙 자체의 비트나 슬라이드 덱이 스크립트 대신 속도를 정합니다.

## 첫 번째 성과

[`/music-to-video`](/prompting/overview)에 트랙과 사진 몇 장을 가리키는 프롬프트 하나면, 비트에 맞춘 완성 영상을 얻기에 충분합니다. 아직 어떤 기법도 필요하지 않습니다.

검증된 출발점은 사진을 트랙에 맞춰 자르고 정사각형 MP4로 내보내는 것입니다.

> /music-to-video 20-second 1080x1080 video from ./track.mp3 (pick the best 20 seconds of the track) and the 8 photos in ./shots/. Cut on the beat grid, one photo per bar, punch-in on downbeats, `whip-pan` transitions on phrase changes. End on the last photo with "SUMMER '26" in condensed caps. No TTS.

<DocsVideo title="HyperFrames video: Example Music Slideshow" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-music-slideshow-v2.mp4#t=0.1" loop />

*위 프롬프트에서 렌더링한 결과물, 편집하지 않음.*

여기서 모든 타이밍 결정은 트랙 자체의 분석에 위임됩니다. 여러분은 *처리 방식*("마디마다 사진 한 장", "다운비트에서 펀치 인")을 설명하고, 비트 그리드가 *시간*을 제공합니다.

## 브리프에서 자주 뒤섞이는 두 가지 결과물

"이 사진들과 이 트랙으로 슬라이드쇼를 만들어 줘"와 "발표용 슬라이드 덱을 만들어 줘"는 둘 다 *슬라이드쇼*라고 말하지만, 서로 다른 것을 만들고 서로 다른 워크플로로 보냅니다. 원하는 결과물을 처음에 분명히 말하세요.

| 원하는 것 | 경로 | 결과물 |
| - | - | - |
| 음악 트랙에 맞춰 자른 사진/클립, 영상으로 내보내기 | `/music-to-video` | 오디오가 포함된 비트 동기화 **MP4** |
| 클릭하며 넘기는 프레젠테이션 — 슬라이드, 공개 효과, 발표자 노트 | `/slideshow` | MP4가 아닌 **탐색 가능한 덱** |

`/music-to-video`는 **음악 트랙** — 오디오 파일, 오디오를 가져올 영상, 또는 분위기 브리프에서 생성된 트랙 — 을 비트에 맞춘 영상으로 바꿉니다. 음악이 모든 속도를 주도하고, 여러분이 제공한 사진이나 클립은 같은 비트 그리드 위에 잘려 들어갑니다. 완전한 영상은 자산이 전혀 없어도 만들 수 있습니다(그 경우 타이포그래피가 전부를 담당합니다). 내레이션과 웹사이트 캡처는 없습니다.

`/slideshow`는 HyperFrames 덱을 작성합니다. 조각(fragment) 공개, 핫스팟 분기, 발표자 노트가 있는 내장 발표자 모드가 포함된 개별 슬라이드들입니다. 결과물은 `hyperframes present`로 제공되는 **실행 중인 덱**입니다. 덱에 `render`를 쓰지 마세요. 첫 번째 장면만 처리하고 조용히 잘린 MP4를 내보냅니다. 사용자가 슬라이드쇼를 명시적으로 요청하지 않았다면, 스킬은 작성 전에 덱 경로를 확인합니다. 이것은 스타일 선호가 아니라 라우팅 결정이기 때문입니다. 알아둘 만한 작성 세부 사항이 하나 있습니다. 조각 공개 시간은 슬라이드별 오프셋이 아니라 덱 마스터 타임라인의 절대 위치라는 점입니다.

## 중요한 설정 항목

프롬프트에서 이미 조절할 수 있는 것들입니다. 어떤 기법도 배우기 전에 말이죠.

**비트 그리드.** `/music-to-video`는 트랙을 한 번 분석해서 에너지 구간, 온셋, 롤, 무음, 급정지, 프레이즈로 나누고, 실제 음악적 변화에서 자릅니다. 여러분이 조절하는 것은 *언제*가 아니라 *어떻게* 자르는지입니다. "마디마다 사진 한 장"은 컷의 밀도를 정하고, "다운비트에서 펀치 인"은 강조를 더하며, "프레이즈 변화에서 전환"은 눈에 띄는 움직임을 구조적 경계를 위해 남겨 둡니다. 리듬감이 확실한 음악에서는 그리드를 믿을 수 있고 컷이 비트에 딱 맞습니다. 차분한 음악에서는 그리드가 분석기가 강요한 메트로놈일 뿐이므로, 스킬은 하드 컷 대신 프레이즈와 에너지에 맞춰 흐르게 합니다. 트랙이 앰비언트라면 "let it flow, no hard cuts"(흐르게 하고, 하드 컷은 없게)라고 말하세요.

**트랙 구간 — 타임스탬프 대신 설명하기.** "가장 좋은 20초" 또는 "벌스에서 훅까지"를 요청하고, 분석기가 음악적 기준점에 맞는 경계를 고르게 하세요. 정확한 타임스탬프("0:32–0:52 사용")는 프레이즈 중간에서 잘리고 그리드와 충돌합니다.

**자산 제공.** 자산 0개도 유효합니다. 타이포그래피와 템플릿이 완전한 영상을 담당합니다. 제공하는 사진이나 클립은 *같은 비트 그리드*에 맞춰 (비트 컷 또는 켄 번즈로) 엮여 들어갑니다. 따라서 자산이 많다는 것은 다른 페이싱 모델이 아니라 자를 것이 더 많다는 뜻입니다. 디렉터리를 가리키고("./shots/의 사진 8장"), 엔드 카드를 지정하세요.

**덱 구조 (슬라이드쇼).** 조각(공개 정지 지점), 핫스팟 + 분기 시퀀스(본 흐름에서 벗어난 상세 슬라이드), 발표자 노트가 덱의 구조적 설정 항목입니다. 이름으로 요청하세요. "bullets를 조각으로 공개해 줘", "핫스팟에서 상세 슬라이드로 분기해 줘", "발표자 노트를 추가해 줘"처럼 말하면 연결은 자동으로 따라옵니다.

## 변형

<AccordionGroup>
  <Accordion title="가사 영상">
    > /music-to-video 30-second 1080x1920 lyric video from ./song.mp3 (pick the strongest 30-second section — a verse into the hook). Transcribe the vocals for word timing. Lines rise in one at a time on the beat, big condensed type on a dark grain background; the hook lands with each word punching in on its downbeat. Keyword in each line highlighted in acid green. No photos — typography only. No TTS.

    단어 단위 타이밍은 트랙을 전사하거나(또는 비트 그리드에 맞춰 놓은 가사를 붙여넣어) 얻습니다. 필요한 자산은 없습니다. 타이포그래피가 영상 전체입니다.
  </Accordion>

  <Accordion title="분위기 브리프에서 만든 키네틱 프로모(트랙 없음)">
    > /music-to-video 15-second 1080x1080 kinetic promo. No track supplied — generate one: driving synthwave, high energy. Cut hard on the beat: full-frame word cards ("FASTER", "SHARPER", "SHIP IT") slam in on downbeats, alternating black/white with inverted type, a glitch flash on each phrase change. End on the wordmark "NOVA" holding with a subtle ambient idle. No TTS.

    오디오가 제공되지 않으면 트랙은 설명한 분위기에서 생성되며, 그것이 만든 비트 그리드가 모든 컷을 구동합니다. 빠르고 에너지 넘치는 브리프가 이 워크플로에 가장 잘 맞습니다.
  </Accordion>

  <Accordion title="발표 덱(슬라이드쇼)">
    > /slideshow Build a 5-slide pitch deck, 1920x1080. One idea per slide, each headline a complete-sentence claim (not a label), punchline first. Slide 2 reveals three pain points one at a time as fragments. Slide 3 shows bottom-up market math (accounts × ACV), not a bare "\$40B TAM". Add presenter notes to every slide, and a hotspot on slide 3 that branches to a "sizing methodology" detail slide. I'll present it with `hyperframes present`.

    이것은 영상이 아니라 클릭할 수 있는 덱을 만듭니다. 조각은 슬라이드 안의 공개 정지 지점이고, 핫스팟은 본 흐름에서 갈라져 나와 Back으로 돌아옵니다. 제목은 덱의 엄격한 규칙을 따릅니다. 완전한 문장의 주장이어야 하고, 슬라이드당 아이디어 하나와 시각 요소 하나이며, 글자 크기는 최소 30pt 상당이어야 합니다.
  </Accordion>
</AccordionGroup>

## 실패 모드

**하드 트랙 타임스탬프.** `/music-to-video`의 핵심은 트랙의 구조가 컷을 정한다는 것입니다. 문자 그대로의 시간 구간은 분석된 비트 그리드를 무시하고 컷을 프레이즈 중간에 떨어뜨립니다.

* ❌ `use the section from 0:32 to 0:52`
* ✅ `pick the best 20 seconds of the track`

**`/slideshow`에서 MP4를 기대하기.** 덱은 마스터 루트 구성 없이 여러 개의 최상위 장면으로 작성되므로, `render`는 첫 번째 장면만 처리하고 잘라 버립니다. 지원되는 결과물은 라이브 `present` 덱과 슬라이드별 스냅샷입니다.

* ❌ `/slideshow ... then render it to deck.mp4`
* ✅ `/slideshow ... I'll present it with hyperframes present` — 또는 실제로 렌더링된 영상이 필요하다면 `/music-to-video`(비트 동기화) 또는 `/general-video`를 사용하세요.

**결과물에 맞지 않는 워크플로.** 음악에 맞춘 사진을 내보내 게시할 것이라면 `/music-to-video`이고, 라이브로 클릭하며 넘길 것이라면 `/slideshow`입니다. "슬라이드쇼"라는 단어만으로 고르면 잘못된 결과물을 만듭니다.

<Tip>
  여기 두 프롬프트는 모두 내레이션이 없습니다. `/music-to-video`는 설계상 TTS가 없습니다. 배경 음악 대신 음성 해설을 원한다면 그것은 다른 워크플로입니다(`/hyperframes`의 라우터를 참고하세요). 이 프롬프트들이 공유하는 여섯 부분 골격은 [프롬프트 구조](/prompting/anatomy)를, 이징과 전환에 대응하는 형용사는 [어휘](/prompting/vocabulary)를 보세요.
</Tip>

<Note>
  **캡스톤 흐름** — [Level 7 영화](/prompting/capstone)의 Rhythm 구간은 `hyperframes beats`에서 얻은 실제 분석된 비트 그리드 위에 미디어 카드를 자릅니다. 이것이 영화에서 허용된 유일한 하드 컷이며, 모두 감지된 비트 위에 있고 카메라는 계속 이동합니다(영화에서 발췌한 컷).
</Note>

이것은 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)에서 작품을 만들어 주는 조항입니다. 여러분의 영상에 그대로 가져다 쓸 수 있는 프롬프트 언어입니다.

> **Rhythm (45–52s).** The wire becomes a waveform: **resolve the BGM first, run `hyperframes beats` on it, and drive this region on the detected grid** — the waveform pulses and compact media cards (a lyric line, a photo card, a chart flash) snap onto the wire on real analyzed beats while the camera keeps traveling; each snap gets a tick SFX. At least six beat-hits. SANCTIONED SEAM #2: the beat-hits may hard-cut card content ON the beat — the sanctioned exception, because the camera itself never stops moving through them.

<DocsVideo title="HyperFrames video: Capstone Region Rhythm" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-rhythm.mp4#t=0.1" loop />

*그 조항을 렌더링한 결과 — 완성된 영화에서 잘라낸 구간.*

이 레벨이 활용하는 워크플로는 [음악으로 영상 만들기](/guides/music-to-video)에 문서화되어 있습니다. 무엇을 입력으로 받는지, 빌드 전에 무엇을 묻는지, 무엇을 반환하는지 설명합니다.

*다음: [모션 그래픽](/prompting/motion-graphics) — 가장 짧은 다음 장으로, 모션 자체가 메시지인 단일 모션 그래픽입니다.*


## 관련 주제

- [음악 기반 영상 만들기](/guides/music-to-video.md)
- [캡션과 토킹 헤드 영상](/prompting/captions-and-talking-heads.md)
- [캡스톤 — 모든 기법, 하나의 여정](/prompting/capstone.md)


이 문서는 [Mintlify](https://mintlify.com), 개발자 문서 플랫폼으로 빌드되고 호스팅됩니다.
