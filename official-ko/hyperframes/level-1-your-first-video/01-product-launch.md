> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져오십시오.
> 더 깊이 탐색하기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾으십시오.

# 제품 론칭 영상

> 제품 URL, 스크립트, 또는 브리프를 론칭 또는 프로모 영상으로 바꾸기 위해 무엇을 말할지 — 그리고 언제 사이트 투어를 택할지.

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

이것은 프롬프트 가이드의 레벨 1입니다: 워크플로에 단 하나의 요청을 주고 완성된 영상을 돌려받는 일회성 라이드 모음입니다. 아직 어떤 기법도 필요하지 않습니다 — 제품을 설명하는 한 문장을 올바른 워크플로에 겨냥해 쓰면 첫 초안으로 충분합니다.

## 첫 번째 성공

라이브 URL을 겨냥해 [`/product-launch-video`](/prompting/overview)에 프롬프트 하나를 주면, 기법 없이도 완성된 론칭 영상을 얻기에 충분합니다.

[예제](/prompting/examples) 페이지에서 검증된 내용 — 라이브 URL에서 만든 45초 론칭:

> /product-launch-video Make a 45-second 1920x1080 launch video for [https://linear.app](https://linear.app). Energetic but minimal, use the site's own palette and screenshots. Structure: hook stating the problem, 3 feature beats with UI captures and one-line captions, end card with logo + "Try it free". Female TTS voice, confident tone, subtle electronic BGM under -18dB.

<DocsVideo title="HyperFrames video: Example Product Launch" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/example-product-launch-v2.mp4#t=0.1" loop />

*위 프롬프트에서 렌더, 편집 없음.*

그 뼈대의 [해부](/prompting/anatomy)를 읽은 뒤, 자신의 제품으로 바꿔 넣으십시오 — 경로, 스펙, 구조, 문구, 목소리, 레벨.

## 이것이 만드는 것

판매하는 론칭 또는 프로모: SaaS 프로모, 기능 공개, 제품 데모, 앱 및 회사 론칭. [`/product-launch-video`](/prompting/overview) 워크플로는 제품의 사이트를 캡처하거나(또는 붙여넣은 스크립트를 받아), 브랜드를 읽고, 이야기를 쓰고, 프레임 단위로 만듭니다.

**올바르게 라우팅하십시오 — 구분은 입력이 아니라 의도입니다:**

| 원하는 것 | 라우트 |
| - | - |
| 제품을 마케팅, 론칭, 프로모션, 공개(상업적 URL의 기본값) | `/product-launch-video` |
| 일반 사이트의 영상 — 포트폴리오 / 블로그 / 문서 / 랜딩 페이지 투어 또는 쇼케이스, 판매 피치가 아닌 것 | `/product-launch-video`도 마찬가지 — 브리프에 *투어* 또는 *쇼케이스*라고 말하십시오 ([웹사이트 영상 가이드](/guides/product-launch-video) 참조) |

두 가지 모두 이제 같은 워크플로로 라우팅됩니다; 바뀌는 것은 브리프입니다. "우리 사이트 프로모"는 론칭입니다 — 판매하십시오. 문서 사이트의 중립적인 워크스루는 투어입니다 — 그렇다고 말하십시오. 그러면 워크플로는 피치하는 대신 사이트 자체의 캡처된 화면을 보여 줍니다. 불확실하면 `/hyperframes`에서 시작해 라우팅을 맡기십시오.

## 중요한 노브

어떤 기법도 배우기 전에 프롬프트에서 이미 조종할 수 있는 것입니다. 신경 쓰이는 것만 설정하고, 나머지는 워크플로의 취향에 맡기십시오.

| 노브 | 무엇을 말할지 | 중요한 이유 |
| - | - | - |
| **캡처 vs 비캡처** | 실제 사이트를 캡처하려면 URL을 주고; 비캡처 경로에는 스크립트나 브리프를 주고; 에이전트가 URL을 찾게 하려면 브랜드 이름만 주십시오 | 캡처는 실제 팔레트와 스크린샷을 빌려 쓰고; 비캡처는 비주얼을 지어내므로 브랜드 색을 이름으로 알려 주어야 합니다 |
| **팔레트 출처** | "use the site's own palette" | 워크플로는 캡처된 브랜드 토큰을 프레임 프리셋에 리믹스합니다 — 일반적인 테마가 아니라 제품의 실제 색을 얻습니다 |
| **구조** | "hook stating the problem, N feature beats with captions, end card with CTA" | 워크플로는 가치를 증거보다 먼저 보여 줍니다; 비트를 이름으로 지정하면 훅과 CTA가 빠지지 않습니다 |
| **목소리와 톤** | "female TTS voice, confident" / "calm male voice" | 목소리 성별과 톤은 프롬프트 단어입니다; 제공자 자체는 워크플로 결정입니다 — 제공자 메커니즘은 [스킬](/prompting/overview)을 참조하십시오 |
| **BGM 수준** | "subtle electronic BGM under -18dB" (또는 "no BGM") | 명시한 상한선이 음악을 목소리 아래로 유지합니다; 티저라면 완전히 끄십시오 |
| **길이와 목적지** | "~45 seconds", "9:16 for TikTok" | 최적 구간은 30–90초; 목적지가 종횡비를 정합니다 (16:9 임베드 · 1:1 피드 · 9:16 Shorts) |

<Tip>
  길이와 목적지는 말하기 가장 저렴하면서 효과가 큰 두 가지입니다. 나머지는 조용히 있으면 워크플로가 잘 고릅니다 — 얼마나 위임할지는 [명세 다이얼](/prompting/specification-dial)을 참조하십시오.
</Tip>

## 변형

<AccordionGroup>
  <Accordion title="20초 세로 티저 (9:16)">
    > /product-launch-video Make a \~20-second 1080x1920 teaser for [https://linear.app](https://linear.app). Super minimal, just the hook. Beat 1 (0-4s): the problem in one line, big type. Beat 2 (4-16s): two feature beats, one UI capture each with a three-word caption. Beat 3 (16-20s): logo + "Try it free" end card, then settle into a gentle idle. Use the site's own palette. Female TTS voice, confident; no BGM.

    티저는 기능 범위를 포기하고 속도를 얻습니다 — 비트는 적게, 아이디어는 하나씩. 목적지(Shorts / TikTok → 9:16)는 유지하고, 워크플로가 짧은 런타임에 맞춰 이야기를 조정하게 하십시오.
  </Accordion>

  <Accordion title="붙여넣은 스크립트, 캡처 없음">
    > /product-launch-video Make a \~20-second 1920x1080 launch video from this script — use it verbatim: "Your CRM is three hours of busywork a day. AutoCRM logs every call, email, and meeting for you. 200 teams already switched. Try it free at autocrmhq.com." No site to capture — invent clean product-y visuals from the script. Male TTS voice, calm and confident; subtle BGM under -18dB.

    URL이 없으면 워크플로는 비캡처 경로를 탑니다: 스크린샷도 없고, 빌릴 사이트 팔레트도 없으므로, 브랜드 색과 글꼴이 있다면 이름을 대십시오(아니면 에이전트가 팔레트를 지어냅니다). 그대로 쓴 스크립트는 길이를 정합니다 — 분당 약 130 단어로 계산하면, 30초 영상에는 65–70 단어 스크립트가 필요합니다. "use it verbatim"이라고 말하면 워크플로의 "유지할까 재구성할까" 질문에 미리 답하게 됩니다.

    <DocsVideo title="HyperFrames video: Variant Launch Script" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/variant-launch-script-v2.mp4#t=0.1" loop />

    *이 프롬프트 형태에서 다른, 더 긴 스크립트(78단어, 가상의 devtool "Relay")로 렌더, 편집 없음 — 단어들이 길이를 정했기 때문에 35.5초로 실행되었습니다.*
  </Accordion>

  <Accordion title="브랜드 이름만 (에이전트가 URL을 찾음)">
    > /product-launch-video Make a \~45-second 1920x1080 launch video for Linear. Find the official site, capture it, and use its own palette and screenshots. Angle: speed as the whole pitch. End card with logo + "Try it free". Confident female TTS voice, subtle electronic BGM under -18dB.

    링크 대신 이름을 주면, 워크플로가 공식 URL을 검색하고 한 줄로 확인한 뒤 캡처합니다 — 링크를 직접 붙여넣지 않아도 사이트에 근거한 결과를 얻습니다.
  </Accordion>

  <Accordion title="대신 사이트 투어 (같은 워크플로, 투어 브리프)">
    > /product-launch-video Make a 30-second 1920x1080 tour of [https://example.com](https://example.com) built from its own screenshots. Calm, editorial pace — show the homepage, two inner pages, and the footer. Full narration, warm male voice. This is a showcase, not a sales pitch.

    목표가 *사이트를 보여 주는 것*이지 제품을 파는 것이 아닐 때 이것을 택하십시오. 캡처된 스크린샷과 사이트의 브랜드 자산으로 만듭니다. 같은 URL이라도 론칭이나 프로모는 `/product-launch-video`에 속합니다.
  </Accordion>
</AccordionGroup>

## 흔한 실패 모드

**그대로 쓴 스크립트에 시간을 고정하기.** 실제 내레이션이 있으면 실제 TTS 길이가 길이를 정합니다 — 딱 떨어지는 숫자는 에이전트가 문구를 자르거나 채우게 만듭니다.

* ❌ `a 45-second launch video from this exact script: ...`
* ✅ `a ~45-second launch video from this script: ...`

**설계된 구조를 덮어쓰기.** 워크플로는 훅 → 가치 → 증거 → CTA를 이유가 있어 만듭니다; 훅을 빼면 프로모는 "왜 내가 신경 써야 하지?"에 답하지 못합니다.

* ❌ `skip the intro, just list all six features back to back`
* ✅ `hook stating the problem, then 3 feature beats, then the CTA end card`

**미리 설정된 아트 디렉션 프리셋과 싸우기.** 각 워크플로는 프레임 프리셋을 채택하고 전환을 주입합니다; 낯선 테마를 강요하면 당신의 룩이 아니라 타협이 나옵니다 ([규칙과 안티 패턴](/prompting/rules-and-anti-patterns) 참조).

* ❌ `/product-launch-video ... plain white, no transitions between scenes`
* ✅ 각도와 톤을 고르고, 시각 체계는 프리셋이 담당하게 하십시오

**에이전트가 자산을 안다고 가정하기.** 비캡처 경로에서는 읽을 사이트가 없습니다; 이름이 없는 로고나 색은 지어내집니다.

* ❌ `use our brand colors`
* ✅ `brand colors #5E6AD2 on off-black; logo at assets/logo.svg`

*다음: [설명 영상](/prompting/explainers) — 제품도, 사이트도 없이 텍스트만 얼굴 없는 설명 영상으로 바꿉니다.*


## 관련 주제

- [제품 또는 웹사이트 영상 만들기](/guides/product-launch-video.md)
- [검증된 예제 프롬프트](/prompting/examples.md)
- [모션 그래픽](/prompting/motion-graphics.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 빌드되고 호스팅됩니다.
