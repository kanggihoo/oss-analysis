---
sha: "5979991d5f0af542fbb02ba906bdba4de52b2b64"
created: 2026-11-17
updated: 2026-11-17
---

# Next Session Plan: hyperframes

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] 기준 SHA를 `b7fa007`(0.8.181)에서 `5979991`(0.9.59)로 올리고 feature map 18행을 다시 썼다(스킬 21→9개, 레지스트리 컴포넌트 239개, 패키지 16개).
- [x] 승인 범위 행 1~8의 기능 스펙 8개를 `draft`로 작성했다. 작성자가 쓰고, 행 1·2·4·5·6·7은 독립 검토자가 코드와 대조해 불일치를 고쳤다. 행 3·8은 메인 점검만 했다.
  - [composition-contract](./capabilities/composition-contract.md) (행 1), [runtime-seek](./capabilities/runtime-seek.md) (행 2), [runtime-adapters](./capabilities/runtime-adapters.md) (행 3), [capture-encode-engine](./capabilities/capture-encode-engine.md) (행 4), [render-orchestration](./capabilities/render-orchestration.md) (행 5), [audio-mix-fx](./capabilities/audio-mix-fx.md) (행 6), [lint-check](./capabilities/lint-check.md) (행 7), [cli-entry-init](./capabilities/cli-entry-init.md) (행 8)
- [x] 후속: 미결정 9개를 읽어서 닫았다(composition-contract U-01, runtime-seek U-02·U-03, capture-encode-engine U-01·U-02·U-04·U-05, audio-mix-fx U-02, lint-check U-02). 닫으면서 기존 서술 일부를 코드 기준으로 고쳤다(audio-mix-fx R-06 길이 미정 트랙, lint-check `distributed` 옵션, runtime-seek R-22 `styleClipsDueVisibleOnce`, capture-encode-engine R-08 병렬 워커 브라우저 풀 비공유).
- [x] 통합 검토: 8개 스펙의 `sha` 일치, 선행 순환 없음, R-ID 교차 링크 점검, 대표 흐름을 `overview.md`에 글로 이음. 공유 정의는 부분 대조만 했다.
- 렌더를 실제로 실행하지 않았다. 의존성 설치·빌드·테스트도 하지 않았다. 모든 스펙의 동작은 코드를 읽은 결과다.

---

- [x] `ready` 승격(2026-11-17): 미결정이 없고 선행도 `ready`인 스펙 3개를 독립 검토 후 `ready`로 올렸다. [composition-contract](./capabilities/composition-contract.md)(검토 2회), [audio-mix-fx](./capabilities/audio-mix-fx.md)(검토 2회), [runtime-seek](./capabilities/runtime-seek.md)(검토 3회). 각 스펙 2.4 검토 기록에 대조한 R-ID와 대조하지 않은 부분을 적었다. 나머지 5개는 `draft`다. runtime-adapters·capture-encode-engine·lint-check·cli-entry-init은 실행·외부 소스·범위 결정이 필요한 미결정이 남았고, render-orchestration은 미결정이 0이지만 선행 capture-encode-engine이 `draft`라 승격하지 못한다.

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

상세는 각 스펙의 "미결정" 표에 있다. 스펙이 `ready`가 되려면 이 항목들을 닫거나 1.2 "제외"로 이유와 함께 옮겨야 한다(워크플로 4장 4번).

| 스펙 | 미결정 | 성격 |
|---|---|---|
| composition-contract | 없음 (U-01 닫음, R-27~R-29 추가) | |
| runtime-seek | 없음 (U-02·U-03 닫음, R-40~R-46 추가) | |
| render-orchestration | 없음 | |
| audio-mix-fx | 없음 (U-02 닫음, R-35 추가) | |
| runtime-adapters | U-01 waapi 역방향 seek에서 추적에서 뺀 `Animation` 복원, U-02 `waitFor` reject 재대기 반복 | 브라우저 실행 필요 |
| capture-encode-engine | U-03 `protocolTimeout`의 실제 끊김(U-01·U-02·U-04·U-05 닫음, R-55~R-58 추가) | Puppeteer 소스·실행 필요 |
| lint-check | U-01 `LINT_RULE_COUNT` 실행값(코드 주석 86, 손으로 센 배열 항목 106) (U-02 닫음, 부록 A 규칙 카탈로그 136행) | 실행 필요 |
| cli-entry-init | U-01 인자 없이 실행했을 때 citty 출력(추론), U-02 소유 행이 없는 명령 14개 | 실행 필요 / 범위 결정 |

2026-11-17 후속 작업으로 "더 읽기만 하면 닫히는" 미결정 9개를 닫았다. 남은 6개는 실행·외부 소스가 필요하거나 범위 결정이다.

- [ ] 어댑터 13개의 `discover`가 모두 멱등이라는 주장(runtime-adapters R-05)은 표본 대조를 하지 않았다.
- [ ] `render-orchestration` 선행 3개와 `cli-entry-init`의 공유 정의(경고 정책, `protocolTimeout`, 캡처 경로 기본값) 전수 대조는 안 했다.

---

## 3. 기능 스펙 후보

feature map에 행은 있지만 승인 범위(행 1~8) 밖이라 스펙을 쓰지 않았다. 행 13(레지스트리)과 `frame.md`는 사용자 결정으로 참고용이라 스펙 후보가 아니다.

| 기능 | 근거 | 상태 |
|---|---|---|
| 행 9 Studio·preview, 행 10 편집 엔진·인스펙터, 행 11 Player·slideshow·present, 행 12 색보정·VFX·셰이더 | feature map 행, 진입점은 overview 2절 | 범위 밖. 학습 목적이 확장되면 승인 |
| 행 14~16 스킬·미디어 도구·외부 가져오기 | 같음 | 범위 밖 |
| 행 17 분산 렌더, 행 18 HeyGen 호스팅 | 같음(부속) | 기본 제외 |
| 소유 행이 없는 명령군(검증·시각 점검 `snapshot`·`compare`·`diff`·`inspect`·`keyframes`, 데스크톱 앱 연동 `open`·`catch-up`, 설치 유지보수 7개) | cli-entry-init R-50, overview 2절 메모 | 새 행 후보. 행 7·10 사이 경계로 보임 |
| 캡처 경로 선택·복구(`forceScreenshot` 트리거, plan 전이, 재시도 사다리) | render-orchestration 작성자 분리 제안 | 보류 |
| frame source 등록·`render` 콜백 작성 | runtime-adapters 작성자 제안, `docs/guides/frame-sources.md` | 보류 |

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

다음에 쓸 기능 스펙은 사용자 결정 뒤에 정한다. 후보 순서는 학습 목적상 행 9(Studio)와 행 10(편집 엔진)이다.

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `packages/core/src/runtime/init.ts` | `applySeek`, `maybePublishRenderReady` | 행 2 미결정 U-02·U-03을 닫을 때 |
| `packages/lint/src/hyperframeLinter.ts` | `LINT_RULE_COUNT` | 규칙 개수 실행 확인(의존성 설치 필요, 실행 허용 대기) |
| `packages/studio/src/App.tsx`, `packages/studio-server/src/createStudioApi.ts` | | 행 9 범위 승인 시 |
| `packages/cli/src/commands/{snapshot,compare,diff,inspect,keyframes}.ts` | | 소유 행 없는 명령군을 새 행으로 올릴 때 |

### 막힌 경로

| 시도 | 결과 | 재개 조건 |
|---|---|---|
| 행 8 첫 작성자 서브에이전트 | 600초 동안 진행이 없어 중단, 파일 없음 | 스켈레톤을 먼저 저장하고 영역마다 쓰는 방식으로 재시도해 성공(이후 큰 스펙도 같은 방식 권장) |
| `LINT_RULE_COUNT` 값, 렌더 실행, 브라우저 동작 확인 | 의존성 설치·빌드·실행을 하지 않음 | 사용자가 실행을 허용하면(워크플로 9장) |

---

## 5. 참고 사항 및 후속 제안

- 8개 스펙은 모두 `draft`다. `ready`로 올리는 조건은 미결정 해소와 선행 스펙 `ready`다. 미결정을 범위 제한으로 닫을지 이어서 읽을지는 사용자 결정 대기다(handoff.md).
- 구조도(archify)는 아직 안 그렸다. overview 3절은 미작성이다.
- 작성 중 반복된 사고: 작성자가 수정하다가 1.4(4칸) 행을 근거 문장(3칸)으로 덮어쓰거나, backtick 안 `|`를 이스케이프하지 않아 표가 깨졌다. 표 칸 수는 backtick 안 `|`도 칸 구분으로 세는 스크립트로 점검했다(메인의 점검 스크립트에 섹션 키 버그가 한 번 있어 행 6·7을 다시 점검했다).
- 지시문의 "알려진 사실"에 메인의 오류가 있었다(`5405-5420`은 로그 문구, 알파 트리거 조건, 20초 값의 출처 등). 작성자가 코드로 바로잡았으니 다음에 지시문을 쓸 때도 줄 번호와 조건은 코드로 먼저 확인한다.
- 문서와 구현이 다른 대표 사례: `determinism.mdx`의 "BeginFrame이 픽셀을 가져온다"(로컬 Linux CLI는 맞고 programmatic 기본은 screenshot), `frame-adapters.mdx`가 렌더 Seek을 `FrameAdapter.seekFrame`으로 설명(실제는 `RuntimeDeterministicAdapter`), README의 control 액션 7개(구현 26개), `audio-effects.mdx`의 true-peak -3 dBTP(구현은 -1에서 시작해 최대 3패스).
