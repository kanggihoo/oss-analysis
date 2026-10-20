> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져오세요.
> 더 살펴보기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾으세요.

# 미디어와 오디오

> 컴포지션에 필요한 보이스오버, 음악, 사운드, 자막, 컷아웃, 에셋을 미디어 파이프라인이 실행할 수 있는 표현으로 요청하세요.

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

영상의 움직임과 읽히는 흐름은 제대로 잡혔습니다. 이 단계에서는 영상에 목소리를 입힙니다.

HyperFrames는 미디어 *재생*을 담당합니다. 별도의 미디어 파이프라인이 그 밖의 모든 것을 처리합니다. 음성, 음악, 효과음, 이미지, 아이콘, 로고, 자막, 배경 제거가 여기에 속합니다. 여러분은 컴포지션에 무엇이 필요한지 설명하고, 에이전트가 각 요구를 고정된 로컬 파일로 변환합니다.

정밀함이 이 단계의 핵심입니다. 모호하게 요청하면 결과도 어긋납니다. 가장 자주 문제가 되는 두 요청은 "Add some music"과 "no sound"입니다. 파이프라인은 적힌 말 그대로 실행하기 때문입니다.

## 보이스오버 (TTS)

에이전트는 정해진 순서에 따라 음성 엔진을 고릅니다. HeyGen 계정이 설정되어 있으면 HeyGen Starfish가 먼저 쓰입니다. 그다음은 ElevenLabs 키가 설정되어 있을 때 ElevenLabs입니다. 둘 다 없으면 로컬 Kokoro 모델이 실행되며, 이 모델은 API 키가 필요 없습니다.

콘텐츠를 설명하고 에이전트가 어울리는 목소리를 고르게 하거나, 목소리·톤·속도를 직접 지정할 수 있습니다:

> Generate narration for this script with a professional female voice.

> Add TTS voiceover, British male voice, at 1.1× speed.

[어휘 목록](/prompting/vocabulary#text-to-speech-voices)의 표는 콘텐츠 유형을 Kokoro 목소리에 연결합니다. `af_heart`와 `af_nova`는 제품 데모에, `am_adam`과 `bf_emma`는 튜토리얼에, `af_sky`와 `am_michael`은 마케팅에 어울립니다. 이미 원하는 목소리를 알고 있으면 이름을 직접 지정하세요. 그렇지 않으면 원하는 낭독 느낌을 설명하고 에이전트가 고르게 하세요.

* ❌ `add a voice`
* ✅ `warm, unhurried female narration of the quoted script` — 전달 방식을 실제로 바꾸는 것은 톤과 속도입니다

### Gemini 보이스오버

내레이터의 전달 방식을 설명으로 직접 지시하고 싶을 때 Gemini를 고르세요. [Gemini 자격 증명](/guides/authentication#providers-used-by-agent-workflows)을 설정한 뒤 에이전트에게 요청합니다:

> Use Gemini 3.8 Flash TTS with the Kore voice to narrate this script. Make the
> delivery warm and unhurried. Use the media-use audio engine, transcribe the
> generated audio, and sync the captions and visual reveals to the spoken words.

공유 오디오 워크플로는 3.8 Flash 및 Flash-Lite TTS, 3.1 Flash TTS Preview, 2.5 Pro 및 Flash TTS Preview를 지원합니다. Gemini는 명시적으로 골랐을 때만 쓰이며, 위의 자동 제공자 순서를 대신하지 않습니다. 스크립트와 전달 지시는 분리해서 유지하세요. 헬퍼는 3.8에서는 구조화된 스타일 메타데이터를, 이전 모델에서는 전달 프롬프트를 사용합니다. 생성된 음성에 의도치 않은 지시가 섞이지 않았는지 검토하세요.

에이전트는 보이스오버를 로컬에 저장하고, 별도의 전사 과정을 거쳐 단어별 타이밍을 얻습니다. 최종 렌더 전에 이름, 숫자, 멈춤 구간을 오디오와 대조해 확인하세요. 새로 녹음한 내레이션에는 새 타이밍이 필요합니다.

## 배경 음악

음악은 대규모 카탈로그에서 분위기에 따라 고릅니다. 음악은 거의 항상 내레이션과 경쟁하기보다 내레이션 *아래에* 깔려야 합니다.

분위기 **와** 음량 목표를 함께 지정하세요. 파이프라인은 특정 레벨로 덕킹(ducking)과 노멀라이즈를 할 수 있으므로, 명시적인 목표를 주면 추측이 아니라 의도한 믹스가 나옵니다.

> Add subtle electronic BGM, kept under −18 dB so it stays beneath the voiceover.

> Upbeat tech-launch music bed at a low level, ducking under narration.

* ❌ `add background music` — 음성과 맞서는 최대 볼륨 트랙이 나옵니다
* ✅ `subtle background music, ducked ~12 dB under the voice` — 파이프라인이 실행할 수 있는 믹스 지시입니다

<Tip>
  명시한 음량 목표("−18 dB 아래", "음성 아래로 덕킹")가 음악이 작품을 받쳐 주는지, 아니면 작품을 묻어 버리는지를 가릅니다. 내레이션이 있을 때는 음악이 그 아래에 깔린다고 항상 말하세요.
</Tip>

## 효과음

효과음은 번들된 19개 파일 라이브러리와 카탈로그에서 고릅니다. 전환, 도장 찍듯 등장하는 요소, 충격 같은 특정 순간에 맞춰 지정하세요. 여기저기 뿌리지 마세요.

> Add a whoosh on each of the three scene transitions.

> Put a soft click on the button press at 0:04.

## 내레이션에 맞춰 리빌 속도 조절하기

영상에 음성이 생기면 음성이 시계 역할을 합니다. 화면 요소가 **말로 나오는 신호에 맞춰** 등장한다고 밝히세요. 통계 수치는 내레이터가 그 수치를 말할 때 나타나야 하고, 빌더가 눈대중으로 정한 독립된 시점에 나타나면 안 됩니다. 이 부분을 빠뜨리면 내레이션과 화면이 같은 파일을 공유하는 두 개의 평행한 트랙으로 어긋납니다.

> VO-paced reveals: each scene's elements land on their spoken cues; secondary elements keep resolving while the narrator is mid-thought; the scene is complete just as the narration moves on.

캡스톤 필름은 이 규칙을 모든 영역에 그대로 적용합니다. 그 Direction 블록은 다음과 같습니다:

> VO-paced reveals: each region's elements land on their spoken cues as the camera arrives; secondary elements keep resolving while the camera is present; the region is complete just as the camera accelerates away.

실무상 참고할 점이 두 가지 있습니다.

에이전트는 단어 타이밍을 별도로 준비하지 않아도 얻습니다. 내레이션은 단어별 타임스탬프와 함께 전사되며, 이는 [자막](#captions-and-transcription)에 쓰이는 것과 같은 방식입니다. 따라서 "말 신호에 맞춰"라는 지시는 실제로 실행 가능한 지시입니다.

그 반대 규칙도 똑같이 중요합니다. 내레이션은 화면을 기다리지 않습니다. 목소리를 애니메이션에 맞추지 말고, 카메라와 리빌을 목소리에 맞추세요.

## 자막과 전사

자막은 단어 단위 타임스탬프에서 나옵니다. 보이스오버를 생성하면 타이밍도 함께 나옵니다. 기존 영상에서는 전사가 타이밍을 만듭니다. Parakeet이 설치되어 있으면 Parakeet을 쓰고, 아니면 whisper가 처리합니다. 원본 영상에서 프로젝트를 스캐폴딩할 때는 그 오디오에서 바로 자막을 생성할 수도 있습니다.

> Transcribe the narration and add karaoke-style captions synced to it.

> Generate captions from `assets/interview.mp4` and style them hype, scale-pop.

자막의 *모양*은 별도의 어휘입니다. 톤, 크기, 단어별 강조가 여기에 속합니다. 스타일은 [자막 카탈로그](/prompting/captions-catalog)를 보세요. 이 페이지는 타이밍이 있는 텍스트를 만드는 방법을 다루고, 그 페이지는 그 텍스트를 꾸미는 방법을 다룹니다.

## 배경 제거 (투명 컷아웃)

`remove-background` 명령은 영상이나 이미지에서 피사체를 로컬에서 분리합니다. 결과로 투명한 WebM을 얻으며, 이를 `<video>`로 어떤 장면에든 넣을 수 있습니다.

> Remove the background from `assets/presenter.mp4` and float the subject over the scene.

주의할 점이 하나 있고, 이것은 결과를 좌우합니다. 기본 제공 모델(`u2net_human_seg`)은 **사람을 위해 만들어졌습니다**. 상반신이나 전신, 비교적 안정된 프레이밍, 피사체와 대비되는 배경에서 잘 동작합니다. **사람이 아닌 피사체**(제품, 동물, 사물)에서는 거의 빈 마스크를 반환합니다.

따라서 제품을 잘라내야 한다면 그렇게 말하세요. 에이전트는 사람 모델을 실행해 아무것도 얻지 못하는 대신 다른 도구로 연결해야 합니다.

* ❌ `remove the background from this product shot` 기본 명령을 쓰면 — 사람용 매팅 모델은 이 피사체를 인식하지 못합니다
* ✅ 사람이라면 `matte the presenter out of assets/talk.mp4`. 제품이라면 사람이 아닌 피사체라고 표시해서 다른 매트(matte)가 쓰이게 하세요.

[배경 제거 가이드](/guides/remove-background)는 사람 전용이라는 주의점, 피사체 뒤 텍스트를 위한 2레이어 플레이트, 사물과 머리카락처럼 세밀한 매트를 위한 대안을 다룹니다.

## 영상 안의 영상과 PIP

영상을 겹치는 작업은 합성 프롬프트입니다. 장면 위의 말하는 사람, 헤드라인 앞의 피사체, PIP 인셋 같은 경우가 여기에 속합니다. 에이전트가 프레임 정확도 규칙을 적용해 주지만, 원하는 레이아웃을 명시하면 도움이 됩니다.

> Put the transparent presenter cutout in the bottom-right, over the chart scene.

> Layer the headline *behind* the presenter so their silhouette occludes the text.

<Note>
  워크플로 스킬이 [배경 제거 가이드](/guides/remove-background#compositing-patterns-and-pitfalls)에 따라 자동으로 처리하는 두 가지 메커니즘입니다.

  * 화면에 드러나며 나타나는 컷아웃은 타이밍이 없는 `<div>` 안에 들어가며, 애니메이션되는 것은 *래퍼*입니다. HyperFrames가 클립 가시성을 관리하므로, 미디어 요소를 직접 애니메이션하면 클립 수명 주기와 충돌합니다.
  * 기본 영상과 컷아웃은 모두 `data-start="0"`에 마운트되어, 컷 지점에서 디코더가 동기 상태를 유지합니다.

  이 중 어느 것도 말할 필요가 거의 없습니다. 이것이 PiP 클립을 "늦게 마운트"하면 한 프레임 어긋날 수 있는 이유이기도 합니다.
</Note>

## 어떤 영상이든 가져오기

지정하기 전에 제공된 영상을 미리 변환할 필요는 없습니다.

일부 코덱은 브라우저에서 깔끔하게 재생되지 않습니다. 가장 흔한 경우는 HEVC(H.265)로, iPhone이나 화면 녹화 프로그램에서 바로 나옵니다. 프레임워크가 에셋을 검사하고, `.transcode-cache/` 아래에 캐시되는 제한된 H.264 프록시를 자동으로 만듭니다.

`preview`, `play`, Studio, 게시된 플레이어 페이지는 재생에 그 프록시를 씁니다. 렌더는 항상 원본 파일을 디코딩하므로 최종 화질이나 색감은 전혀 바뀌지 않습니다. `snapshot`도 FFmpeg로 원본에서 프레임을 읽으므로, `--proxy`를 주지 않으면 프록시를 만들지 않습니다.

`hyperframes lint`도 에셋을 info 수준(`hevc_preview_codec`)으로 표시하므로, 프록시가 사용 중인지 알 수 있습니다. 프록시는 선택 사항입니다. 명령마다 `--no-proxy`를 주거나, `hyperframes.json`에서 `media.autoProxy: false`로 프로젝트 전체에 설정할 수 있습니다.

같은 메커니즘이 알파 채널 소스에도 적용됩니다. ProRes 4444와 알파 WebM은 거부되는 대신 VP8 + Opus WebM 프록시를 받으므로, 까다로운 코덱의 투명 컷아웃도 장애물이 되지 않습니다.

이 때문에 요청 방식이 바뀌지는 않습니다. 다른 제공 에셋과 마찬가지로 경로로 영상을 지정하고, 그 영상으로 만들고 싶은 컴포지션을 설명하세요.

> Build a short picture-in-picture piece from `source-hevc.mp4` — inset it bottom-right over a full-bleed background scene, with a soft rounded border.

<DocsVideo title="HyperFrames video: Proxy Footage" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/proxy-footage.mp4#t=0.1" loop />

*위 프롬프트에서 편집 없이 렌더링했습니다. 원본 클립은 일반적인 H.265/HEVC 파일입니다. 렌더는 FFmpeg로 직접 디코딩했습니다. 미리보기는 자동 H.264 프록시를 사용했을 것입니다.*

프록시 생성, 캐싱, 적용 코덱 같은 메커니즘은 [렌더링 가이드](/guides/rendering#input-video-codecs)를 참고하세요.

## 제공 에셋 규칙

이미 가지고 있는 에셋이라면, 명시적인 경로가 모호함을 가장 많이 없앱니다. 에이전트는 설명만 주면 검색하지만, 경로는 *어느* 파일인지를 확정합니다.

* ❌ `use my logo`
* ✅ `use assets/logo.svg`

검색이 잘 되더라도 이 점은 중요합니다. 브랜드와 엔터티 에셋은 비슷한 것으로 대체된 파일이 아니라 *여러분의* 파일을 가리켜야 합니다.

제3자 로고는 별개의 경우입니다. 파이프라인은 공식 마크를 로고 캐스케이드에서 가져오며, 손으로 다시 그리지 않습니다. 그래서 "add the LinkedIn logo"는 괜찮습니다. "Add my company's logo"에는 경로가 필요합니다.

## "소리 없음"이 실제로 무엇을 뜻하는지 밝히기

가장 흔한 오디오 실수는 생각보다 적은 것을 뜻하는 부정문입니다. "No narration"은 보이스오버만 제거합니다. 음악이나 효과음을 **끄지는** 않습니다. 완전한 무음을 원한다면 그렇게 말하세요:

* ❌ `no narration` 완전히 무음인 영상을 원할 때 — 음악과 효과음은 여전히 추가될 수 있습니다
* ✅ `no audio at all` — 무음을 요청하는 명확한 방법입니다

이는 [구조](/prompting/anatomy)의 부정문 원칙과 같습니다. 엔진은 문자 그대로 실행하므로 간극을 명시적으로 메우세요.

## 캡스톤 흐름

<Note>
  **캡스톤 흐름** — [7단계 필름](/prompting/capstone)의 Material 영역은 이 장의 전체 파이프라인을 하나의 클립에 적용합니다. 생성된 영상 → HEVC 자동 프록시 → 장면 중간의 배경 제거 → 클립 자체 전사에서 얻은 단어 동기 자막이 이어지고, 클립의 오디오가 BGM을 덕킹합니다(아래 필름에서 잘라낸 부분).
</Note>

이것은 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)에서 이 작품을 완성하는 절입니다. 여러분의 영상에도 가져다 쓸 수 있는 프롬프트 표현입니다:

> \[…] a real talking-head clip (generate a short clip of a person speaking one neutral line via the media pipeline's avatar video generation \[…] **transcode it to HEVC `hvc1`** so the automatic proxy subsystem carries preview) sits as a clip on the wire. The order of operations IS the story: as the camera arrives and BEFORE the person speaks, the framework mattes the footage — **the background peels away via background removal** \[…] THEN they speak, and the main **keywords of their own line — derived from the clip's transcription — land word-synced** \[…] The clip's own audio ducks the BGM briefly; the VO resumes as the camera pulls away.

<DocsVideo title="HyperFrames video: Capstone Region Material" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-material.mp4#t=0.1" loop />

*이 절을 렌더링한 결과입니다. 완성된 필름에서 잘라낸 영역입니다.*

*다음: [오디오 효과와 믹싱](/prompting/audio-effects) — 방금 배치한 음성, 음악, 효과음을 함께 어울리게 만들기.*

## 관련 주제

* [어휘 목록](/prompting/vocabulary) — 음성 이름, 자막 톤, 오디오 반응 매핑
* [자막 카탈로그](/prompting/captions-catalog) — 이 페이지가 만든 타이밍 텍스트 꾸미기
* [배경 제거](/guides/remove-background) — 매팅 명령, 사람 전용 주의점, 대안
* [영상과 이미지 사용하기](/guides/video-components) — 설치형 오버레이, 자막, 효과


## 관련 주제

- [린트 규칙](/reference/lint-rules.md)
- [출력을 바꾸는 어휘](/prompting/vocabulary.md)
- [HyperFrames 프로젝트의 작동 방식](/concepts/index.md)


이 문서는 [Mintlify](https://mintlify.com)로 빌드되고 호스팅되는 개발자 문서 플랫폼에서 제공됩니다.
