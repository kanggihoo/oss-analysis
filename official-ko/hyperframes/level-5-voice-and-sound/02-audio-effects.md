> ## 문서 색인
> 전체 문서 색인은 https://hyperframes.heygen.com/llms.txt 에서 가져오세요.
> 더 살펴보기 전에 이 파일을 사용해 사용 가능한 모든 페이지를 찾으세요.

# 오디오 효과와 믹싱

> 필터가 아니라 증상으로 믹스를 요청하세요. 음악이 내레이션에 길을 비키게 하고, 목소리를 깨끗하게 만들고, 정직한 답이 없는 요청이 무엇인지 아는 것입니다.

지난 장은 영상에 목소리를 주었습니다. 이번 장은 그 목소리와 주변의 모든 소리를
*잘 들리게* 만듭니다.

오디오 작업에서 프롬프트는 특정한 방식으로 잘못됩니다. 기계의 이름을 대고 싶은
유혹이 생기기 때문입니다. "80 Hz에 Q 0.7로 하이패스를 추가하라"는 실제로 가능한
지시입니다. 하지만 그런 요청은 그것을 낳은 요청보다 나쁩니다. 문제가 무엇인지
확인되기도 전에 해결책에 미리 묶어 두기 때문입니다. 믹스는 각 트랙에 붙은 효과로
저장됩니다. 필터, 다이내믹스, 음색, 공간감, 그리고 시간에 따라 이들을 움직이는
엔벨로프입니다. 에이전트가 그 도구 상자에서 꺼내 씁니다. 여러분의 일은 증상을
정확히 묘사하는 것입니다.

## 무엇을 추가할지가 아니라 어떻게 들리는지 말하기

랙의 모든 효과는 어떤 불만에 답하기 위해 존재합니다. 그 불만을 말하세요.

```text theme={null}
The narration sounds muffled, like it's behind cardboard. Fix it.
```

```text theme={null}
The voice sounds amateur — clean it up but don't make it sound processed.
```

```text theme={null}
There's a hum under the interview audio the whole way through.
```

각각은 특정하고 작은 변화로 이어집니다. 250 Hz 컷, `voice-clean` 체인, 목소리 아래의
하이패스 같은 것입니다. 어느 것인지 알 필요는 없습니다. 그리고 잘못된 메커니즘을
이름 붙이면, 잘못된 메커니즘이 확신에 찬 채로 적용됩니다.

이것은 화면 작업보다 더 중요합니다. **여러분은 믹스를 들을 수 있지만 에이전트는
들을 수 없기 때문입니다.** 소리를 묘사하는 프롬프트는 증거입니다. 필터의 이름을
대는 프롬프트는 증거의 옷을 입은 추측입니다.

## 이름을 알아 둘 가치가 있는 요청 하나

내레이션 아래의 음악은 가장 흔한 오디오 문제이며, 습관적인 해결책은 틀렸습니다.

음악 트랙 전체를 낮추는 덕킹(ducking)은 효과가 있지만, 보이스오버 내내 음악의
존재감을 모두 잃게 합니다. 누군가 말하는 동안 음악은 힘을 잃습니다. 하지만 목소리에는
전체 스펙트럼이 필요하지 않습니다. 실제로 차지하는 몇 개의 대역만 필요합니다. 음악에서
그 대역만 빼내는 것을 **카브(carve)**라고 부르며, 저음과 고음은 그대로 남깁니다. 그래서
목소리는 알아들을 수 있게 남고, 바탕은 여전히 음악입니다.

이 용어로 요청하세요.

```text theme={null}
Put the music under the narration properly — carve it so the voice stays clear
without the track going limp.
```

```text theme={null}
The music is fighting the voiceover. Make room for the voice in the music
rather than just turning the music down.
```

결과를 판단할 수 있도록 알아 둘 두 가지가 있습니다.

* **말을 따라갑니다.** 침묵 구간에서는 음악을 건드리지 않고, 큰 소리 구간에서는 최대
  깊이까지 파고듭니다. 모든 쉼 구간에서 고정된 낮춤을 유지하는 방식이 아닙니다.
* **카브는 음악 쪽에 있으며**, 공간을 내주는 목소리를 이름으로 지정합니다. 누군가
  목소리 트랙을 카브했다고 말한다면, 그것은 취향의 결정이 아니라 버그입니다.

결과가 나왔는데 음악이 단순히 작아진 것이 아니라 *속이 빈* 것처럼 들린다면, 정확히 그
단어로 말하세요. 깊이가 너무 깊다는 뜻이며, 소리로 분명히 알 수 있는 유일한 실패
모드입니다.

```text theme={null}
Too far — the music sounds notched now. Back it off.
```

## 깊이를 더 요구하기 전에 레벨을 요청하기

카브로는 단순히 목소리보다 큰 음악을 고칠 수 없습니다. 내레이션이 묻혀 있을 때 유용한
지시는 스펙트럼이 아니라 **레벨**에 관한 것입니다.

```text theme={null}
Check the actual loudness of the voiceover against the music before touching
the carve — the voice may just be quieter than the bed.
```

기계가 생성한 음성은 마스터링된 음악 트랙보다 훨씬 낮게 도착하는 경우가 흔합니다. 그
차이는 취향이 아니라 산술이며, 아무리 카브해도 메울 수 없습니다. 먼저 측정을 요청하면
한 번의 추측이 숫자가 됩니다.

## 함께 속한 것들을 묶기

내레이션 클립 다섯 개에는 효과 세트 하나, 페이더 하나, 뮤트 하나가 필요합니다. 편집하면서
서로 어긋나는 복사본 다섯 개가 아닙니다. 이렇게 말하세요.

```text theme={null}
Group all the narration clips as one voiceover group, then carve the music
against that group.
```

이 표현은 추가 절을 붙일 가치가 있습니다. 개별 클립을 가리키는 카브는 그 클립을 하나하나
모두 나열해야 하며, 클립을 하나 더 추가하기 전까지만 맞습니다. 여섯 번째 클립은 카브가
인식하지 못한 채 재생되고, 음악은 그 아래에서 소리 없이 낮춰지지 않습니다. *그룹*을
가리키는 카브는 실행될 때 그 그룹에 있는 것을 무엇이든 잡아냅니다.

효과음도 두 개를 넘으면 그룹으로 묶으세요. 모두를 한 번에 낮출 수 있는 한 곳은, 다시
손볼 일이 없을 정밀한 개별 레벨보다 더 가치가 있습니다.

## 정적인 설정으로 충분하지 않을 때 움직임 요청하기

영상 길이에 따라 변해야 하는 것은 모두 엔벨로프이며, 시간에 따른 모양을 묘사해서
요청합니다.

```text theme={null}
Fade the music out over the last three seconds.
```

```text theme={null}
Bring the ambience up while the wide shot is on screen, then pull it back
under the interview.
```

기억해 둘 단서가 하나 있습니다. 일부 효과는 시간에 따라 전혀 움직일 수 없습니다. 컴프레서,
리미터, 게이트, 비트크러시, 피치 시프트는 노브 하나하나가 아니라 통째로 설정됩니다. 장면이
쌓이면서 조여지는 컴프레서를 요청하면, 정직한 답은 그 앞에서 움직이는 레벨 단계입니다.
이런 효과에 엔벨로프를 조용히 써 넣는 에이전트는 아무 작용도 하지 않는 것을 쓴 것입니다.
그러니 요청한 변경이 들리는 효과가 전혀 없다면, 그것을 가장 먼저 의심하세요.

## 정직한 답이 없는 세 가지 요청

빈틈을 이름 붙여 말하는 것이, 가장 가까운 프리셋을 받아들이고 그것이 요청한 것이라고
부르는 것보다 더 유용합니다.

**디에싱(de-essing).** 날카로운 `s` 소리에는 도구 상자의 무엇보다 빠른 검출기가
필요합니다. 가장 가까운 해결책은 5–9 kHz 대역의 좁은 컷입니다. 그 목소리가 쉭쉭거리는
지점을 찾기 위해 훑어 찾습니다. 항상 켜져 있으므로, 모든 단어에서 약간의 공기감을
잃습니다. 그 거래는 보통 가치가 있습니다. 다만 그것이 거래라는 점을 알고 요청하세요.

```text theme={null}
The s sounds are spitting. I know there's no real de-esser — put a narrow cut
where this voice actually sibilates and tell me what it cost.
```

**잡음 제거.** 게이트는 구절 사이의 틈을 닫습니다. 하지만 단어 *아래에* 깔린 쉬익거림은
사용할 수 있는 어떤 것으로도 건드릴 수 없습니다. 들리는 쉬익거림이 있는 소스는 더 나은
소스가 필요하며, 그렇게 말해 주는 에이전트는 게으른 것이 아니라 정확한 것입니다.

**한 목소리를 다른 목소리에 맞추기.** 매치 커브 도구는 없습니다. 두 테이크는 EQ로 손으로
가깝게 맞출 수 있습니다. 유도된 커브와 달리 예측 가능하지만, 그것은 손작업이므로 그렇게
요청할 가치가 있습니다.

## 전체 믹스를 마지막에 한 번 묘사하기

개별 수정은 쌓이지만, 아무도 전체로서 판단하지 않은 무언가가 됩니다. 마지막에 하는 지시
하나가 추가 조정 세 번보다 가치가 있습니다.

```text theme={null}
Render an audio-only pass and check the mix end to end: voice clear through
the loudest musical moment, effects where the action is, nothing surprising
at the open, and the music finishing on purpose rather than at the file edge.
```

오디오 문제는 화면이 주의를 빼앗지 않을 때 더 쉽게 알아챌 수 있습니다. 보지 않고 한 번
들어 보면, 프롬프트를 스무 번 주고받아도 놓칠 것들을 잡아냅니다.

*다음: [디자인 시스템과 브랜드](/prompting/design-systems) — 분위기를 묘사하는 대신
에이전트가 브랜드의 진실의 원천을 가리키게 하기.*


## 관련 주제

- [오디오 효과 구현](/reference/audio-effects.md)
- [미디어와 오디오](/prompting/media-and-audio.md)
- [오디오 믹스하고 효과 적용하기](/studio/audio-effects.md)


이 문서는 개발자 문서 플랫폼 [Mintlify](https://mintlify.com)로 만들어지고 호스팅됩니다.
