> ## 문서 인덱스
> 전체 문서 인덱스는 다음 주소에서 가져올 수 있습니다: https://hyperframes.heygen.com/llms.txt
> 더 살펴보기 전에 이 파일로 사용할 수 있는 모든 페이지를 먼저 찾아볼 수 있습니다.

# Remotion에서 포팅하기

> 기존 Remotion(React) 컴포지션의 소스를 HyperFrames HTML로 옮기려면 무엇을 요청해야 하는지, 그리고 에이전트가 거부할 것이 무엇인지 설명합니다.

이 장은 레벨 6의 마지막 장이자 캡스톤 레벨 직전의 마지막 장입니다. 기존 Remotion 프로젝트를 지금까지 배운 모든 내용, 즉 브랜드 시스템, 변수, 편집, 반복 작업, 참조 맞추기, 내보내기와 연결합니다.

## 무엇을 만드는가

새 영상이 아니라 **번역**입니다. [`/remotion-to-hyperframes`](/prompting/overview) 워크플로는 기존 Remotion(React) 컴포지션의 소스를 읽고, 이를 HyperFrames HTML로 다시 씁니다. 프레임, 타이밍, 시각적 결과가 같아야 하며, React의 프레임 콜백 모델 대신 GSAP에서 실행됩니다.

이것은 제작 워크플로가 아니라 마이그레이션입니다. 기존 Remotion 소스를 포팅, 변환, 마이그레이션, 번역해 달라는 명시적인 요청에만 작동합니다. 비슷해 보이지만 이에 해당하지 않는 경우가 두 가지 있습니다.

* "내 Remotion 영상과 비슷한 것을 만들어 줘"처럼 실제 소스를 마이그레이션해 달라는 요청이 없는 경우 → 새로 만드는 작업이므로 [`/general-video`](/prompting/overview#one-time-setup)를 씁니다.
* After Effects, Framer Motion, 순수 React/CSS 같은 Remotion이 아닌 소스 → 번역할 Remotion 소스가 없으므로 네이티브로 다시 만듭니다.

변환 방향은 한쪽뿐입니다. Remotion이나 다른 프레임워크로 되돌리는 내보내기는 없습니다.

## 기본 프롬프트

> /remotion-to-hyperframes Port the composition at `src/HeroReveal.tsx` (Remotion project root: `.`) to HyperFrames. Keep the same duration, fps, and dimensions. Write `TRANSLATION_NOTES.md` for anything that doesn't translate cleanly.

프로젝트에 `<Composition>`이 여러 개 등록되어 있을 때는 "내 Remotion 프로젝트"라고만 말하지 말고 정확한 파일을 지정하십시오. 어떤 컴포지션인지 밝혀야 합니다.

## 번역되지 않는 것과 그것이 맞는 이유

스킬은 번역 전에 소스를 린트합니다. HyperFrames의 탐색 기반 모델이 결정적으로 표현할 수 없는 패턴을 만나면, 근사하지 않고 **거부**합니다.

* **상태에 따른 애니메이션** — `useState`, `useReducer`, 실제 의존성이 있는 `useEffect`/`useLayoutEffect`. HyperFrames는 임의의 프레임으로 탐색하고 매번 같은 픽셀을 기대하는데, 자신의 이력에 반응하는 상태 기계는 이를 보장할 수 없습니다. 스킬은 "보기에는 맞지만 프레임 단위로 정확하지 않은" 번역을 조용히 만들어 내는 대신, 런타임 상호운용 패턴을 권장합니다.
* **서드파티 React UI 키트** — MUI, Chakra, Mantine, antd, shadcn, Radix, NextUI. 이들을 옮길 HTML/CSS/GSAP 대응물이 없습니다.
* **`@remotion/lambda` 배포 설정** — 차단 요소는 아닙니다. 애니메이션이 아니라 배포 설정이므로 제외되며, 컴포지션의 나머지 부분은 계속 번역됩니다.

소스가 차단 요소에 걸리면, 에이전트는 억지로 밀고 나가지 않고 멈추고 상호운용 권장안을 설명합니다. 이것은 실패가 아니라 올바른 동작입니다. 차단 요소를 "그냥 대충 근사해 줘"라고 밀어붙이지 마십시오. 이 워크플로의 핵심은 검증되고 측정된 번역이지, 최선의 추측이 아닙니다.

## 검증은 선택 사항이 아닙니다

모든 번역은 렌더링된 프레임에서 SSIM(구조적 유사도)으로 Remotion 원본과 비교해 채점되며, 눈대중으로 판단하지 않습니다. 까다로운 포팅이라면 검사를 명시적으로 요청하십시오.

> After translating, render both the Remotion original and the HyperFrames version and report the SSIM diff.

미리보기에서 "보기에 맞는" 번역도 검증된 기준선보다 상당히 낮은 점수가 나올 수 있습니다. 이 워크플로가 잡아내도록 설계된 차이가 바로 이것입니다.

## 중요한 조정 항목

| 항목 | 이렇게 말하십시오 | 이유 |
| - | - | - |
| **정확한 소스 파일** | "the composition at `src/HeroReveal.tsx`" | Remotion 프로젝트는 `<Composition>`을 여러 개 등록할 수 있으므로, 의도한 것을 이름으로 지정하십시오 |
| **정확한 타이밍 유지** | "keep the same duration, fps, and dimensions" | 기본값이지만, 에이전트가 값을 반올림하거나 크기를 바꾸지 않도록 명시하십시오 |
| **누락 기록** | "write `TRANSLATION_NOTES.md` for anything that doesn't translate cleanly" | 근사된 글꼴, 생략된 볼륨 램프, 대체된 표현은 조용히 넘어가지 않고 기록됩니다 |
| **검증** | "report the SSIM diff against the original" | 충실도 검사를 나중에 생각나는 선택 사항이 아니라 결과물의 일부로 만듭니다 |

## 흔한 실패 유형

**Remotion을 영감으로 삼아 새로 만들어 달라고 요청하는 경우.** 번역할 실제 Remotion 소스가 없다면 이 워크플로가 아니라 일반 제작입니다.

* ❌ `/remotion-to-hyperframes make something like my Remotion intro`
* ✅ `/general-video make an intro like this: [description]` — Remotion 소스가 없고, 마이그레이션도 없습니다

**린트 차단 요소를 밀어붙이라고 요청하는 경우.** `useState` 기반 컴포지션은 "일단 번역하고 최선을 다하라"는 상황이 아니라 다른 문제(런타임 상호운용)입니다. 억지로 번역하면 그럴듯해 보이지만 프레임 단위로 정확하지 않은 결과가 나옵니다.

* ❌ `just convert it, don't worry about the state stuff`
* ✅ 에이전트가 상호운용 패턴을 권장하게 한 뒤, 여러분의 경우에 맞는지 판단합니다

**까다로운 포팅에서 검증을 건너뛰는 경우.** 눈으로 보는 확인으로는 프레임 단위 SSIM 비교에서만 드러나는 타이밍과 이징의 미세한 차이를 놓칩니다.

* ❌ *(검증 요청 없음 — "보기에 맞는다"는 이유로 수락)*
* ✅ `render both and report the SSIM diff`

*다음: [캡스톤](/prompting/capstone) — 하나의 프롬프트, 하나의 영화, 이 가이드의 모든 기법을 프레임 단위로 분석합니다.*


## 관련 주제

- [Rendering and output](/prompting/rendering-and-output.md)
- [Changelog](/changelog.md)
- [HyperFrames or Remotion?](/guides/hyperframes-vs-remotion.md)


이 문서는 개발자 문서 플랫폼인 [Mintlify](https://mintlify.com)로 만들어지고 호스팅됩니다.
