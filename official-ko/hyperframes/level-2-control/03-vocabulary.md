> ## 문서 인덱스
> 전체 문서 인덱스는 다음 주소에서 가져올 수 있습니다: https://hyperframes.heygen.com/llms.txt
> 더 탐색하기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 먼저 찾아보십시오.

# 출력을 바꾸는 어휘

> 스킬이 특정 프레임워크 설정으로 매핑하는 자연어 형용사 — 이징, 캡션, 전환, 오디오, 음성.

[세부 수준 조절 다이얼](/prompting/specification-dial)에서 *얼마나* 구체적으로 지정할지를 알아봤습니다. 이 페이지는 저비용 정밀 설정을 위한 단어 목록입니다. 말하는 데 비용이 들지 않으면서도 실제로 모호함을 줄여 주는 스타일 토큰입니다. 스킬은 자연어 형용사를 특정 프레임워크 설정으로 매핑합니다. 올바른 단어를 쓰면 기술적인 세부 사항을 지정하지 않아도 원하는 결과를 얻을 수 있습니다.

## 모션과 이징

모션이 *어떤 느낌*이어야 하는지 설명하면 에이전트가 맞는 GSAP 이즈를 고릅니다:

| 이렇게 말하기 | 에이전트가 쓰는 값 | 느낌 |
| - | - | - |
| smooth | `power2.out` | 자연스러운 감속 |
| snappy | `power4.out` | 빠르고 단호함 |
| bouncy | `back.out` | 넘쳤다가 자리를 잡음 |
| springy | `elastic.out` | 진동하며 자리를 잡음 |
| dramatic | `expo.out` | 빠르게 시작해 길게 미끄러짐 |
| dreamy | `sine.inOut` | 느리고 대칭적임 |

**시간 약칭:** fast(0.2초) = 에너지, medium(0.4초) = 전문적, slow(0.6초) = 고급스러움, very slow(1–2초) = 영화적.

단어별 렌더링 결과입니다. 동작은 같고 이즈만 바뀝니다:

<div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", margin: "1.25rem 0" }}>
  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/ease-power2-out.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="smooth preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      smooth <code>power2.out</code>
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/ease-power4-out.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="snappy preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      snappy <code>power4.out</code>
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/ease-back-out.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="bouncy preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      bouncy <code>back.out</code>
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/ease-elastic-out.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="springy preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      springy <code>elastic.out</code>
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/ease-expo-out.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="dramatic preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      dramatic <code>expo.out</code>
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/ease-sine-inout.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="dreamy preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      dreamy <code>sine.inOut</code>
    </figcaption>
  </figure>
</div>

## 카메라 용어

컴포지션에는 실제 카메라가 없지만, 카메라 용어는 장면 변환(또는 Three.js 장면에서는 실제 카메라 이동)으로 직접 옮겨집니다:

| 이렇게 말하기 | 에이전트가 만드는 것 |
| - | - |
| slow push-in | 장면 전체를 4–8% 확대, 완만한 이즈 |
| pull back / widen | 축소, 보통 요소 진입과 함께 사용 |
| pan across | 장면 레이어의 수평 이동 |
| drone orbit | 지속적인 카메라 궤도 회전 (Three.js 장면) |
| crane down/up | 세로 카메라 이동과 시선 지점 이동을 결합 |
| whip to | 빠르게 흐려지며 다음 프레이밍으로 슬라이드 |
| parallax | 깊이감을 위해 레이어가 서로 다른 속도로 이동 |

같은 장면에 각 카메라 용어를 적용한 결과입니다:

<div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", margin: "1.25rem 0" }}>
  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/camera-push-in.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="slow push-in preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      slow push-in
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/camera-pull-back.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="pull back preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      pull back
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/camera-pan.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="pan across preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      pan across
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/camera-crane.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="crane down/up preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      crane down/up
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/camera-whip.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="whip to preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      whip to
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/camera-parallax.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="parallax preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      parallax
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/camera-orbit.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="drone orbit preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      drone orbit
    </figcaption>
  </figure>
</div>

## 깊이 용어

| 이렇게 말하기 | 에이전트가 만드는 것 |
| - | - |
| near-lens / foreground bokeh | 카메라 가까이에서 흐릿하게 블러 처리된 큰 요소가 떠다님 |
| depth planes | 서로 다른 속도로 움직이는 2–3개의 레이어 |
| out-of-focus background | 블러 처리되고 더 느리게 움직이는 뒤쪽 레이어 |
| shallow depth of field | 주제는 선명하게, 나머지는 흐리게 |

## 리듬 용어

| 이렇게 말하기 | 에이전트가 만드는 것 |
| - | - |
| punchy cuts | 아이디어당 1.5–4초, 하드 컷, 겹치는 등장 |
| cinematic holds | 주변 idle 모션이 있는 더 긴 비트 |
| beat-synced | 음악의 비트 그리드에 맞춘 컷과 강조 |
| breathing room | 다음 비트가 시작되기 전 잠시 멈춘 순간 |
| ambient idle | 유지 구간 동안 1–2% 호흡 스케일 + 느린 드리프트 |

## 캡션 톤

*전체 장: [캡션 스타일](/prompting/captions-catalog).*

캡션의 *에너지*를 설명하면 에이전트가 맞는 타이포그래피, 크기, 애니메이션을 고릅니다:

| 톤 | 타이포그래피 | 애니메이션 | 크기 범위 |
| - | - | - | - |
| Hype | 굵은 굵기의 폰트 | 스케일 팝 | 72–96px |
| Corporate | 깔끔한 산세리프 | 페이드 + 슬라이드 | 56–72px |
| Tutorial | 모노스페이스 | 타이프라이터 | 48–64px |
| Storytelling | 세리프 | 느린 페이드 | 44–56px |
| Social | 둥글고 장난스러운 서체 | 바운스 | 56–80px |

```
"Hype-style captions with scale-pop"
"Calm, elegant subtitles with slow fades"
"Karaoke-style word highlighting"
```

단어 단위 스타일링도 가능합니다:

```
"Make brand names larger with accent color"
"Add bounce to emotional keywords"
"Highlight numbers differently"
```

## 전환

*전체 장: [전환](/prompting/transitions).*

여러 장면으로 이루어진 컴포지션이라면 모두 전환 효과에서 이득을 봅니다. 에너지 수준을 설명하세요:

| 에너지 | CSS 옵션 | 셰이더 옵션 |
| - | - | - |
| Calm | 블러 크로스페이드 | 크로스 워프 모프 |
| Medium | 푸시 슬라이드 | 휩 팬 |
| High | 줌 스루 | 글리치, 릿지드 번 |

또는 분위기로 설명하세요:

```
"Warm transitions for this wellness brand"
"Cold, clinical transitions for tech"
"Playful bouncy transitions"
"Dramatic zoom for the reveal"
```

## 오디오 반응형 애니메이션

*전체 장: [미디어와 오디오](/prompting/media-and-audio).*

오디오 주파수 대역을 시각 속성에 매핑합니다. 에이전트는 다음 기본값을 사용합니다:

| 오디오 대역 | 매핑 대상 | 시각 효과 |
| - | - | - |
| Bass | `scale` | 비트에 맞춘 펄스 |
| Treble | `glow` | 반짝임 강도 |
| Amplitude | `opacity` | 호흡 효과 |
| Mids | `shape` | 모핑 |

```
"Make the text pulse with the beat"
"Add bass-driven scale to the logo"
"Create glow that responds to treble"
```

<Tip>
  텍스트에는 오디오 반응 효과를 은은하게 유지하세요(강도 3–6%). 배경에는 더 크게 주세요(10–30%).
</Tip>

## 마커 하이라이트

텍스트를 위한 손으로 그린 듯한 강조 효과입니다:

| 모드 | 효과 | 적합한 용도 |
| - | - | - |
| `highlight` | 마커 스윕 | 핵심 문구 |
| `circle` | 손으로 그린 타원 | 단일 단어 |
| `burst` | 방사형 선 | 하이프 순간 |
| `scribble` | 거친 낙서 선 | 취소선 긋기 |
| `sketchout` | 사각형 윤곽선 | 콜아웃 |

```
"Add a marker highlight sweep on 'revolutionary'"
"Circle this keyword with hand-drawn effect"
"Add burst lines around 'AMAZING'"
```

같은 문장에 다섯 가지 모드를 적용한 결과입니다:

<div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", margin: "1.25rem 0" }}>
  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/marker-highlight.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="highlight preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      highlight
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/marker-circle.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="circle preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      circle
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/marker-burst.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="burst preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      burst
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/marker-scribble.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="scribble preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      scribble
    </figcaption>
  </figure>

  <figure style={{ margin: 0 }}>
    <video src="https://static.heygen.ai/hyperframes-oss/docs/images/prompting/marker-sketchout.mp4#t=0.1" autoPlay muted loop playsInline preload="metadata" aria-label="sketchout preview" style={{ display: "block", width: "100%", borderRadius: "10px", background: "#000" }} />

    <figcaption style={{ marginTop: "0.4rem", fontSize: "0.8125rem", opacity: 0.75 }}>
      sketchout
    </figcaption>
  </figure>
</div>

## 텍스트 음성 변환(TTS) 음성

TTS는 Kokoro를 통해 로컬에서 실행됩니다(API 키 필요 없음). 콘텐츠를 설명하면 에이전트가 음성을 고르고, 직접 음성을 지정할 수도 있습니다:

| 콘텐츠 유형 | 권장 음성 |
| - | - |
| 제품 데모 | `af_heart`, `af_nova` |
| 튜토리얼 | `am_adam`, `bf_emma` |
| 마케팅 | `af_sky`, `am_michael` |

```
"Generate narration for this script"
"Create voiceover with a professional female voice"
"Add TTS with British male voice at 1.1x speed"
```

## 렌더링 품질

*전체 장: [렌더링과 출력](/prompting/rendering-and-output).*

| 품질 | 용도 |
| - | - |
| `draft` | 빠른 반복 작업 |
| `standard` | 검토와 피드백 |
| `high` | 최종 납품 |

```
"Quick draft render"
"Render at high quality"
"Export as transparent WebM"
```

*다음: [고품질 룩](/prompting/visual-specs) — 단어 하나를 넘어 전체 룩을 담는 완전한 비주얼 스펙을 다룹니다.*


## 관련 주제

- [고품질 룩](/prompting/visual-specs.md)
- [프롬프트 가이드](/prompting/overview.md)
- [세부 수준 조절 다이얼](/prompting/specification-dial.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 만들어져 호스팅됩니다.
