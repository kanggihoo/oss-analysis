> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져오세요.
> 더 살펴보기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾으세요.

# 오버레이와 하단 자막(Lower Third)

> 이름이 붙은 하단 자막과 소셜 게시물 오버레이 블록을, 타이밍, 문구, 브랜드 톤과 함께 요청하세요.

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

Level 1의 founder-clip.mp4는 `/talking-head-recut`을 통해 이름이 붙은 하단 자막과 카드 오버레이를 받았습니다. 이 장은 반대 경우를 다룹니다. 처음부터 컴포지션을 만들면서 바로 넣을 수 있는, 이미 만들어진 하단 자막과 소셜 오버레이 블록입니다. 기존 영상은 필요 없습니다. 같은 어휘를 한 컷이 아니라 장면을 대상으로 쓰는 것입니다.

## 오버레이가 하는 일과 트리거되는 시점

오버레이는 영상이나 장면 위에 놓이는 타이밍 블록입니다. 화자 이름을 알려 주는 하단 자막, 방송 티커, 실제와 같은 소셜 미디어 카드가 여기에 속합니다. 각 블록은 타이밍이 있는 클립이므로, 특정 순간에 무언가를 *추가*해 달라고 요청하면 이 레이어가 작동합니다. 예를 들어 "add a lower third at 0:03 with the name and title", "show an animated tweet during the intro", "put a Spotify now-playing card in the corner"처럼 요청하세요. 시각, 문구, 톤을 주면 에이전트가 블록을 영상 위 트랙에 배치합니다.

두 가지 그룹이 있습니다.

* **[하단 자막](/catalog/blocks/lt-clean-bar)** — 인터뷰, 팟캐스트, 뉴스에서 화자를 식별하는 이름과 직함 표시입니다.
* **[소셜 오버레이](/catalog/blocks/x-post)** — 플랫폼 UI(게시물, 카드, 알림, 팔로우 유도)의 애니메이션 복제본입니다.

## 브랜드 톤 → 하단 자막

하단 자막은 **카드형**(텍스트 뒤에 채워진 도형이 있음)과 **카드 없음**(텍스트에 선이나 쓸어내리는 효과를 더함, 라이브 영상 위에 박스 없이 올라가도록 설계됨)으로 나뉩니다.

| 톤 | 블록 |
| - | - |
| **미니멀 / 깔끔함 / 기업용** | [`lt-clean-bar`](/catalog/blocks/lt-clean-bar), [`lt-soft-pill`](/catalog/blocks/lt-soft-pill) |
| **에너지 넘침 / 팟캐스트 / 강렬함** | [`lt-bold-block`](/catalog/blocks/lt-bold-block), [`lt-color-block`](/catalog/blocks/lt-color-block) |
| **영상 위의 카드 없는 형태**(인터뷰, 토킹 헤드) | [`lt-accent-underline`](/catalog/blocks/lt-accent-underline), [`lt-kicker-name`](/catalog/blocks/lt-kicker-name), [`lt-mask-reveal`](/catalog/blocks/lt-mask-reveal), [`lt-side-rule`](/catalog/blocks/lt-side-rule) |
| **밝은 영상 위의 카드** | [`lt-dark-card`](/catalog/blocks/lt-dark-card) |
| **방송 / 뉴스** | [`lower-third-bild`](/catalog/blocks/lower-third-bild), [`news-ticker`](/catalog/blocks/news-ticker) |
| **두 부분으로 나뉜 와이프(이름 + 역할)** | [`lt-stack-bars`](/catalog/blocks/lt-stack-bars) |

<Tip>
  라이브 영상 위에서는 **카드 없는** 하단 자막을 선호하세요. 이들은 텍스트에 그림자를 넣어 가독성을 확보하므로, 장면과 싸우는 박스가 필요 없습니다. 배경이 너무 복잡해 카드 없는 텍스트가 읽히지 않으면 **카드**([`lt-dark-card`](/catalog/blocks/lt-dark-card)의 차콜 색상, 밝은 장면용)를 쓰세요.
</Tip>

## 용도 → 소셜 오버레이

각 소셜 오버레이는 편집 가능한 자리 표시자 콘텐츠를 가진 독립적인 애니메이션 카드입니다.

| 원하는 것 | 블록 |
| - | - |
| 참여 지표가 있는 애니메이션 트윗 / X 게시물 | [`x-post`](/catalog/blocks/x-post) |
| 추천 수와 댓글이 있는 Reddit 게시물 카드 | [`reddit-post`](/catalog/blocks/reddit-post) |
| 앨범 아트와 진행 바가 있는 Spotify 재생 중 카드 | [`spotify-card`](/catalog/blocks/spotify-card) |
| macOS 알림 배너 | [`macos-notification`](/catalog/blocks/macos-notification) |
| Instagram 팔로우 유도 | [`instagram-follow`](/catalog/blocks/instagram-follow) |
| TikTok 팔로우 유도 | [`tiktok-follow`](/catalog/blocks/tiktok-follow) |
| YouTube 구독 하단 자막 | [`yt-lower-third`](/catalog/blocks/yt-lower-third) |

## 예시 프롬프트

편집 가능한 문구는 정확히 인용하세요. 따옴표 없는 이름과 직함은 바뀌어 표현됩니다([anatomy](/prompting/anatomy) 참고).

> Add a lower third at 0:03 for 5 seconds, on a track above the footage, with [`lt-clean-bar`](/catalog/blocks/lt-clean-bar). Name: "Dana Ríos". Title: "Head of Design".

<DocsVideo title="HyperFrames video: Validate Lower Third" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/validate-lower-third.mp4#t=0.1" loop />

*위 프롬프트로 대체 영상 위에 렌더링했으며, 편집하지 않았습니다.*

<Note>
  하단 자막에는 블록 자체의 타임라인 길이 이상을 주세요(대부분 설계된 퇴장 애니메이션을 포함해 약 5초입니다). 더 짧은 구간이면 정착 후 빠져나가는 애니메이션이 재생되기 전에 블록이 강제로 잘립니다.
</Note>

> Podcast clip. Bring in [`lt-bold-block`](/catalog/blocks/lt-bold-block) when the guest starts talking, holding 5 seconds — name "MARCUS LEE", tag "GUEST" — brand accent #FF5A1F.

> During the intro, show an [`x-post`](/catalog/blocks/x-post) card with the quote "we shipped it in a weekend" and 12.4K likes, then slide it out before the demo.

<DocsVideo title="HyperFrames video: Overlay Xpost" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/overlay-xpost.mp4#t=0.1" loop />

*위 프롬프트로 대체 장면 위에 렌더링했으며, 편집하지 않았습니다. 카드에 내장된 좋아요 탭 동작으로 12.4K → 12.5K가 올라갑니다.*

> /motion-graphics Transparent overlay only — a [`spotify-card`](/catalog/blocks/spotify-card) now-playing widget animating in, bottom-left. Export as transparent WebM so I can drop it over footage in my editor.

<DocsVideo title="HyperFrames video: Overlay Spotify Preview" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/overlay-spotify-preview.mp4#t=0.1" portrait loop />

*체커보드 위에 미리보기한 투명 WebM의 MP4 버전입니다. 전달된 파일에는 실제 VP9 알파가 들어 있습니다(ALPHA\_MODE와 alphaextract로 확인).*

## 조절 항목

* **타이밍.** "at 0:03", "for 4 seconds", "slide it out before the demo"는 블록의 시작과 길이를 정합니다. 오버레이는 타이밍이 있는 클립이므로 둘 다 필요합니다.
* **문구.** 이름, 직함, 핸들, 헤드라인, 지표, 티커 텍스트 등 편집 가능한 모든 항목을 인용하세요. 블록에는 교체해야 할 자리 표시자 콘텐츠가 들어 있습니다.
* **트랙 배치.** 오버레이는 영상 *위* 트랙에 놓여야 위에 합성됩니다. 기존 클립 위에 겹치는 경우에는 "over the footage"라고 말하세요.
* **브랜드 강조색.** HEX 값이나 브랜드 색상을 주세요. 대부분의 하단 자막에는 강조 막대, 탭, 또는 블록이 있어서 이 색을 받습니다.
* **카드형 또는 카드 없음.** 중요할 때 명시하거나, 톤 표에 맡기세요.
* **투명 출력.** 외부 NLE에서 쓰려면 오버레이를 단독으로 투명 WebM으로 렌더하세요. [렌더링과 출력](/prompting/rendering-and-output)을 참고하세요.

## 실패 모드

**문구를 따옴표 없이 쓰지 마세요.** 따옴표 없는 이름과 직함은 바뀌어 표현됩니다. 따옴표로 묶인 텍스트는 그대로 렌더됩니다.

* ❌ `add a lower third with the speaker's name and role`
* ✅ `lt-clean-bar — name: "Dana Ríos", title: "Head of Design"`

**시각을 빼먹지 마세요.** 오버레이는 타이밍이 있는 클립입니다. 시작 시점(그리고 가능하면 길이)이 없으면 에이전트가 언제 나타나고 얼마나 머물지 추측해야 합니다.

* ❌ `put a lower third somewhere in the intro`
* ✅ `lower third at 0:03, holding 4 seconds`

**오버레이를 영상 뒤에 렌더되게 두지 마세요.** 클립 위의 트랙에 있어야 합니다. 그렇지 않으면 영상이 가립니다.

* ❌ `add the tweet card to the video` (레이어가 모호함)
* ✅ `x-post card on a track above the footage, top-right`

**실제 계정 데이터를 과하게 지정하지 마세요.** 이것들은 편집 가능한 자리 표시자가 들어간 양식화된 복제본입니다. 스크랩할 실시간 URL이 아니라, 보여 줄 문구를 제공하세요.

* ❌ `pull my actual Spotify page`
* ✅ `spotify-card: track "Midnight City", artist "M83"`

**오버레이 이름을 지어내지 마세요.** [소셜 오버레이](/catalog/blocks/x-post)와 [하단 자막](/catalog/blocks/lt-clean-bar) 그룹에 있는 블록만 존재합니다.

* ❌ `add a linkedin-post overlay`
* ✅ 실제 블록을 고르거나, 자유형 컴포지션에서 에이전트가 맞춤 블록을 만들도록 카드를 설명하세요

<Note>
  **캡스톤 흐름** — [7단계 필름](/prompting/capstone)의 Material 영역은 설계된 하단 자막 칩을 도킹하는데, 이 칩은 외곽선이 잘려 나간 피사체 *뒤에* 렌더됩니다(아래 필름에서 잘라낸 부분).
</Note>

이것은 [전체 캡스톤 프롬프트](/prompting/capstone#the-prompt-word-for-word)에서 이 작품을 완성하는 절입니다. 여러분의 영상에도 가져다 쓸 수 있는 프롬프트 표현입니다:

> \[…] as the camera arrives and BEFORE the person speaks, the framework mattes the footage — **the background peels away via background removal**, sliding off along the travel direction and leaving the cutout standing alone on the brand ground. \[…] A designed lower-third chip renders behind the subject.

<DocsVideo title="HyperFrames video: Capstone Region Material" src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/capstone-region-material.mp4#t=0.1" loop />

*이 절을 렌더링한 결과입니다. 완성된 필름에서 잘라낸 영역입니다.*

*다음: [캡션 스타일](/prompting/captions-catalog) — 같은 타이밍 블록 패턴을, 이름 카드와 소셜 복제본 대신 화면 텍스트에 맞춰 조정한 것입니다.*


## 관련 주제

- [캡스톤 — 하나의 여정에 담긴 모든 기법](/prompting/capstone.md)
- [데이터와 지도](/prompting/data-and-maps.md)
- [하단 자막 — 액센트 언더라인](/catalog/blocks/lt-accent-underline.md)


이 문서는 [Mintlify](https://mintlify.com)로 빌드되고 호스팅되는 개발자 문서 플랫폼에서 제공됩니다.
