> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져옵니다.
> 더 살펴보기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾아보십시오.

# 변수와 템플릿화

> 바뀌어야 할 부분을 이름 있는 슬롯으로 만들도록 요청한 다음,
> 같은 composition을 다른 값으로 다시 렌더링하십시오. 레코드 하나당 결과물 하나가 나옵니다.

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

[디자인 시스템](/prompting/design-systems)은 영상에서 렌더링마다
절대 바뀌지 않아야 하는 부분, 즉 브랜드를 다뤘습니다. 이 페이지는
바뀌어야 하는 부분을 다룹니다. 고객마다 카드 하나, 분기마다 수치 하나,
수신자마다 이름 하나입니다.

composition을 재사용할 것이 확실하다면 프롬프트에서 그렇다고 말하십시오.
바뀌는 부분을 이름으로 지정하십시오. 에이전트는 이것을 선언된
[변수](/concepts/variables)로 바꿉니다. 타입이 있고 이름표가 붙은 슬롯이며,
HTML에 하드코딩하지 않고 렌더링 시점에 채워집니다.

요청하는 문장은 간단합니다. 슬롯을 지정하십시오.

> 6초짜리 타이틀 카드를 만드십시오. **이름**, **로고**, **강조 색상**을 변수로 만들고,
> 나머지는 모두 고정하십시오.

<DocsVideo title="HyperFrames video: Validate Variables Default" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-variables-default.mp4#t=0.1" loop />

*기본 변수 값입니다.*

<DocsVideo title="HyperFrames video: Validate Variables Variant" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-variables-variant.mp4#t=0.1" loop />

*같은 composition을 `--variables` 재정의로 다시 렌더링한 결과입니다.
이름, 로고, 강조 색상이 다르며 프롬프트를 다시 쓰지 않았습니다.*

에이전트는 composition 루트에 `data-composition-variables`를 선언하고,
각 슬롯에 맞는 타입을 붙입니다. 이름은 `string`입니다. 강조 색은 `color`입니다.
로고는 `image`이며, 일반 URL도 유효한 값입니다. 일반 `<img>` 로고에는
타이밍 속성이 필요 없습니다. `<video>`와 `<audio>` 변수만
[변수](/concepts/variables)에서 설명하는 미디어 연결 방식이 필요합니다.
하나의 composition에 여러 값을 채웁니다.

## 각 슬롯의 타입을 말하십시오

변수 타입은 일곱 가지입니다. `string`, `number`, `color`, `boolean`, `enum`,
`font`, `image`입니다. 각 타입은 렌더링 시점에 다르게 검증됩니다.
[Studio](/packages/studio)에서 `boolean`, `enum`, `color`, `number`는 각각 전용
컨트롤을 가지고, `string`, `font`, `image`는 일반 텍스트 입력을 씁니다.

JSON은 직접 쓸 필요가 없습니다. 하지만 프롬프트에서 타입을 밝히면 추측할 여지가 사라집니다.

> 변수: `plan` (enum: Free / Pro / Enterprise), `price` (number, `$`로 표시),
> `featured` (boolean, 리본을 켜고 끔), `headline` (text).

* ❌ `plan과 price를 편집 가능하게 해줘`
* ✅ `plan은 enum입니다(Free / Pro / Enterprise). price는 달러 단위의 number입니다`

엔진의 근거는 이렇습니다. 선언된 옵션이 있는 `enum`은 렌더링 시점에 그 목록과
대조되므로 `enum-out-of-range`가 잡힙니다. `number`에는 `min`, `max`, `step`,
`unit` 라벨을 붙일 수 있고, 이것이 Studio에 단순한 텍스트 상자 대신 실제
슬라이더를 줍니다. "편집 가능"이라고만 말하면 타입을 고르는 일이 에이전트에게
넘어갑니다. 그러면 잘못된 타입의 값은 훨씬 나중에 드러납니다.

## 템플릿으로 만들고 레코드마다 렌더링하기

바뀌는 부분이 변수가 되면, 같은 소스를 데이터 행마다 한 번씩 렌더링할 수 있습니다.
이것은 영상마다 복사해서 붙여넣는 루프가 아니라 실제 일괄 모드입니다.
composition은 한 번 작성하고, 값 집합의 목록을 넣습니다.

> `name`과 `title` 변수가 있는 템플릿으로 만든 다음, 내 데이터의 행마다 영상을
> 하나씩 렌더링하십시오. 출력은 `renders/{name}.mp4`로 하십시오.

에이전트는 composition을 작성한 다음 [일괄 렌더링](/concepts/variables#batch-renders)을
실행합니다. 일괄 입력은 JSON 배열입니다. 각 행은 하나의 변수 값 집합이며,
행마다 출력 파일이 하나씩 나옵니다. 출력 경로의 `{key}` 자리표시자는 그 행의 값으로 채워집니다.

소스가 CSV라면 그렇게 말하십시오. 에이전트가 일괄 처리에 필요한 행 배열로 변환합니다.

"선언되지 않았거나 타입이 잘못된 값이 있으면 실패" 조건을 추가하면
`--strict-variables`로 렌더링됩니다. 그러면 열 이름의 오타가 기본값을 조용히
렌더링하는 대신 실행을 멈춥니다.

모든 결과물이 하나의 composition을 공유합니다. 따라서 디자인을 한 번 고치면
다음 렌더링에서 모든 결과물에 반영됩니다. 수백 개의 거의 같은 파일을 편집할 필요가 없습니다.

## 개인화 요청

규모가 큰 개인화 영상도 같은 패턴입니다. 값 집합만 여러분의 데이터에서 옵니다.

> 새 가입자마다 이름으로 인사하고 회사 로고를 보여주는 10초짜리 환영 클립입니다.
> `{ firstName, logoUrl }` 레코드 목록을 제공하겠습니다.

`firstName`은 `string`입니다. `logoUrl`은 composition이 `<img src>`에 연결하는 이미지 슬롯입니다.

에셋은 인라인 데이터가 아니라 **URL 참조**로 넘기십시오. URL 형태의 값은 로컬 렌더러와
분산 [Lambda 렌더링](/deploy/templates-on-lambda) 모두에서 깔끔하게 전달됩니다.

CLI가 아니라 여러분 자신의 제품 UI나 에이전트 뒤에서 이것을 연결하고 싶다면,
[`@hyperframes/sdk`](/packages/sdk)가 기본 템플릿을 열고 인스턴스마다 희소한 재정의
집합을 겹쳐 적용합니다. 그러면 호스트는 레코드마다 차이분만 저장합니다.

## 미리 선언하고, 값을 굳히지 마십시오

가장 흔한 실수는 값이 이미 고정된 완성 영상을 설명한 다음, 나중에
"재사용 가능하게 해달라"고 요청하는 것입니다.

* ❌ `"Acme — Pro plan — $49"라고 적힌 카드를 만들어줘. 나중에 다른 회사도 필요할 거야.`
* ✅ `plan 카드를 만들어줘. 변수: company (text), plan (enum), price (number, $). 기본값으로 "Acme / Pro / 49"를 보여줘.`

엔진의 근거는 이렇습니다. 변수는 스크립트가 라이브 DOM에 적용하는 런타임 값입니다.
값은 선언된 기본값이 먼저, 그다음 인스턴스별 재정의, 그다음 CLI 순으로 결정됩니다.

처음부터 선언하면 재사용 가능한 구조가 첫 렌더링부터 존재합니다. 기본값도 값 집합
하나일 뿐입니다. 마크업에 `"Acme — Pro — $49"`를 굳혀 넣으면 슬롯이 없는
composition이 됩니다. 그러면 재사용하려면 변형마다 하드코딩된 텍스트를 다시 편집해야 합니다.
변수가 존재하는 이유가 바로 그것을 피하는 것입니다.

## 템플릿이 실제로 다시 스타일링되는지 증명하기

다시 스타일링되지 않는 템플릿은 가진 모든 게이트를 통과할 수 있습니다.
`lint`와 `check`는 구조를 검증합니다. `--strict-variables`는 선언되지 않았거나
타입이 잘못된 키를 잡습니다. 그러나 전달한 값이 DOM에 실제로 도달했는지는 어느 것도 알려주지 못합니다.

실패는 성공처럼 보입니다. 렌더링이 완료되고 깔끔하게 종료되며,
**기본값과 픽셀 단위로 동일합니다**.

그래서 차등 방식으로 테스트하십시오. 두 번 렌더링하고 비교합니다.

```bash theme={null}
hyperframes render --output default.mp4
hyperframes render --variables '{"ground":"#0d1420","ink":"#c8ff3d"}' --strict-variables --output reskin.mp4
```

두 파일이 같다면 재정의가 기대한 속성에 도달하지 못한 것입니다. 세 가지를 확인하십시오.
변수 ID가 선언되어 있는가? 렌더링 명령이 그 정확한 ID를 사용하는가?
눈에 보이는 속성이 실제로 CSS 커스텀 속성이나 변수 값에 바인딩되어 있는가?

렌더링 시점의 `--variables` 재정의는 변수 ID 기준으로 전역입니다. 컴파일러는
일치하는 재정의를 루트와 `data-composition-src`로 가져온 하위 composition의
CSS 커스텀 속성에 적용합니다. `data-variable-values`는 두 마운트가 서로 다른 값을
갖도록 하는 여전히 인스턴스별 방법입니다.

하위 composition 안의 범위 지정된 JavaScript는 자신의 인스턴스별 변수 테이블을 읽습니다.
따라서 그 스크립트가 CSS 대신 `getVariables()`를 호출한다면, 마운트 지점에서 값을 전달하십시오.

[캡스톤](/prompting/capstone)은 단순함을 위해 변수를 루트 파일 하나에 둡니다.
템플릿이 반드시 그래야 하는 것은 아닙니다. 공유되는 CSS 바인딩 ID가 일관되게
선언되어 있다면 하위 composition도 작동합니다. 인스턴스별 입력이나 JavaScript가
읽는 입력에는 마운트 지점 값을 사용하십시오. 정확한 변수 문장은 이 페이지 하단에 인용되어 있습니다.

## 변수가 될 수 없는 것

몇몇 입력은 컴파일 시점에 한 번만 읽히며, 어떤 변수로도 바꿀 수 없습니다.

* composition **크기**(`data-width` / `data-height`)
* 루트 composition의 **전체 길이**
* **프레임 레이트**
* **출력 형식, 코덱, 품질**

그래서 다음은 읽히는 것과 다르게 작동합니다.

* ❌ `각 렌더링마다 길이가 다르도록 영상 길이를 변수로 만들어줘`
* ✅ `대상 길이마다 composition을 하나씩 작성하십시오`. 또는 *클립의* 길이를 바꾸는 것입니다.
  이것은 라이브 DOM에서 다시 읽힙니다.

출력마다 전체 길이가 달라야 한다면, 그것은 변수가 아니라 렌더링마다 다른 루트
`data-duration`입니다. 전체 목록과 그 뒤의 컴파일 시점 대 라이브 DOM 규칙은
[변수될 수 없는 것](/concepts/variables#what-cant-be-a-variable)을 보십시오.

<Note>
  작성된 CSS 커스텀 속성은 같은 이름의 변수보다 항상 우선합니다. composition이 이미
  손으로 쓴 테마 토큰으로 `:root { --accent: ... }`를 정의하고 있다고 해봅시다.
  `accent`라는 변수는 이것을 절대 덮어쓰지 않으며, 작성된 값이 유지됩니다.
  렌더링 시점의 `--variables` 재정의는 둘 모두보다 여전히 우선합니다. 따라서 렌더링마다
  작성된 값을 재정의해야 할 때는 같은 이름의 선언된 변수가 아니라 `--variables`를 쓰십시오.
</Note>

## 관련

<CardGroup cols={2}>
  <Card title="변수 (개념)" icon="sliders" href="/concepts/variables">
    동작 원리: 타입 선언, 인스턴스별 재정의, 일괄 렌더링, 우선순위.
  </Card>

  <Card title="@hyperframes/sdk" icon="code" href="/packages/sdk">
    여러분 자신의 제품 UI나 에이전트 뒤의 템플릿 + 희소 재정의 편집.
  </Card>

  <Card title="명세의 다이얼" icon="gauge" href="/prompting/specification-dial">
    얼마나 명세할지, 그리고 타입을 이름으로 밝히는 것이 왜 저렴한 정밀성인지.
  </Card>

  <Card title="디자인 시스템과 브랜드" icon="palette" href="/prompting/design-systems">
    브랜드 토큰을 변수로 두고 한 값으로 재사용마다 다시 스타일링.
  </Card>
</CardGroup>

<Note>
  **캡스톤 흐름**: [Level 7 영상](/prompting/capstone)은 작동하는 템플릿입니다.
  단일 파일 composition 하나, 변수 범위 하나입니다. 두 번째 렌더링은 `--variables`
  플래그 하나뿐입니다. 네이비 바탕, 아시드 그린 잉크이며, 생성된 벽화를 포함한
  모든 영역이 다시 스타일링됩니다. 두 전체 렌더링 결과는 캡스톤 페이지에 삽입되어 있습니다.
</Note>

이것은 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)에서
이 작품을 완성하는 문장입니다. 여러분의 영상에도 그대로 가져다 쓸 수 있는 프롬프트 언어입니다.

> **변수:** `ground`(기본값 `#0a0a0a`)와 `ink`(기본값 `#3CE6AC`)를 단일 루트 파일의
> composition 변수로 노출하고, 모든 곳에서 CSS 커스텀 속성으로 바인딩하십시오(듀오톤 벽화 포함).
> 그래서 `--variables` 호출 하나로 전체 여정을 다시 스타일링할 수 있습니다.
> 두 번 렌더링합니다. 기본 브랜드 팔레트와, `{"ground":"#0d1420","ink":"#c8ff3d"}`를 사용한
> 두 번째 전체 렌더링입니다.
>
> **아키텍처 제약(기술):** 단일 composition 파일입니다. `index.html` 하나, 변수 범위 하나입니다.
> \[…] `data-composition-src` 하위 파일은 없습니다.

*다음: [스토리보드](/prompting/storyboards). 여러 장면으로 된 작업에는 장면을 하나씩
요청하지 말고, 프레임별 빌드가 채워 넣을 계획을 요청하십시오.*


## 관련 주제

- [캡스톤 — 하나의 여정에 담긴 모든 기법](/prompting/capstone.md)
- [디자인 시스템과 브랜드](/prompting/design-systems.md)
- [스토리보드](/prompting/storyboards.md)


이 문서는 개발자 문서 플랫폼인 [Mintlify](https://mintlify.com)로 작성되고 호스팅됩니다.
