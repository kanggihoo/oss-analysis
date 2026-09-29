# Codenotch Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/vinzdg/codenotch`
- **분석 Commit SHA**: `414ceaf6173d9988c01ed76d8e924cf0118e3755`
- **Commit 날짜/제목**: `2026-09-20 16:46:06 +0700` — "Codenotch 1.16.0 appcast"
- **분석 일자**: `2026-09-21`
- **작업트리 상태**: `Clean` (`git status --porcelain` 무출력)
- **분석 목적**: `학습 / 설계 참고` — 다수 외부 서비스 어댑터의 정규화, 폴링·백오프 전략, 실패를 정직하게 노출하는 상태 모델
- **License**: MIT © 2026 Vinz
- **원본 메타데이터**: [artifacts/codenotch/repo-metadata.txt](../../artifacts/codenotch/repo-metadata.txt)
- **규모**: Swift 5 / SwiftUI + AppKit, `Sources/` 187개 파일 38,444줄, `Tests/` 93개 파일 27,949줄 (테스트:소스 ≈ 0.73)
- **부가 포트**: `windows/`에 Rust + Tauri 2 포팅(30개 `.rs`). 이번 세션의 분석 범위는 macOS 본체(`Sources/`)로 한정 — `검증 수준: 미확인`

> 참고: shallow clone(`--depth 50`)이라 태그는 `v1.9.0`까지만 보이지만, HEAD 커밋 메시지는 1.16.0 appcast다.
> README 배지는 `platform-macOS 26+`, 본문은 "macOS 15 or later"라고 적혀 있어 서로 다르다. (`검증 수준: 코드 확인` — README 문자열)

---

## 2. 프로젝트 개요

Codenotch는 **화면 가장자리에 붙는 작은 검은 노치(notch)** 형태의 macOS 메뉴바급 앱이다.
Claude Code, Codex, Cursor, Copilot, GLM, Kimi, Kiro, Ollama, LM Studio 등
**Mac에 이미 설치된 코딩 도구들의 사용량 한도(limit window)를 한 화면에 링(ring)으로 모아 보여준다.**
동시에 "지금도 돌고 있는가 / 끝났는가 / 나를 기다리는가"라는 **세션 활동 상태**도 같은 링 안에서 표현한다.

이 프로젝트가 흥미로운 지점은 기능 자체보다 **"신뢰할 수 없는 외부 소스를 정직하게 다루는 방법"** 이다.
README가 스스로 "The honest caveat"라는 절을 두고 밝히듯,
**어떤 벤더도 "당신의 세션 한도가 N% 남았다"는 공개 API를 제공하지 않는다.**
그래서 모든 어댑터가 내부 엔드포인트·로컬 SQLite·CLI 출력·언어 서버 RPC·HTTP 캐시 파일 같은
**깨지기 쉬운 경로**를 읽는다. 이 제약을 코드가 어떻게 흡수하는지가 이 레포의 설계 핵심이다.

### 본 세션에서 코드로 확인한 설계 특징

1. **자격증명을 만들지 않고 "빌린다".**
   대부분의 provider는 이미 Mac에 있는 도구의 세션을 읽는다. 예외는 `WebSessionProvider`를 쓰는
   DeepSeek / QianwenAI / MiniMax뿐이며, 이들만 Codenotch 자체 `WKWebView` 안에서 명시적 로그인을 한다.
   (`검증 수준: 코드 확인` — `Sources/App/AppDelegate.swift:111-156`, `Sources/Providers/WebSessionProvider.swift`)

2. **신뢰도(`Fidelity`)를 타입으로 강제한다.**
   `enum Fidelity { official, derived, manual }`이고, `qualifier`가 official이 아닐 때 `~`를 붙인다.
   "추측한 숫자를 벤더가 발표한 것처럼 보이게 하지 않는다"는 규칙이 UI가 아니라 모델에 박혀 있다.
   (`검증 수준: 코드 확인` — `Sources/Model/UsageModel.swift:15-22`)

3. **실패가 숫자로 위장되지 않는다.**
   `ProviderStatus`는 `ok / stale(since:) / needsAuth / signedOutByOwner / accessDenied / unsupported / error`로 나뉘고,
   `UsageProviderError`는 `needsAuth`와 `accessDenied`와 `signedOutByOwner`를 **의도적으로 구분**한다.
   "로그인하세요"라는 안내가 이미 로그인한 사람을 엉뚱한 곳으로 보내지 않게 하려는 구분이다.
   (`검증 수준: 코드 확인` — `Sources/Model/UsageModel.swift:36-51`, `Sources/Providers/UsageProvider.swift:70-118`)

4. **헤드라인 창(window)을 provider가 "선언"한다.**
   `headlineID` / `weeklyID`가 없으면 링은 아무 숫자도 띄우지 않고 비운다.
   위치(첫 번째 window)로 고르면 응답에서 창 하나가 빠질 때 링이 모양을 유지한 채 조용히 주제를 바꾸기 때문이다.
   (`검증 수준: 코드 확인` — `ProviderSnapshot.headline` 주석)

5. **틱(tick)은 요청이 아니다.**
   `UsageStore.shouldRefresh(isBusy:sinceLastAttempt:idleInterval:resetDue:)`는 순수 함수이고,
   아무것도 안 돌 때는 5분 idle 간격까지 기다린다. 단, 어떤 window의 `resetsAt`이
   직전 시도와 현재 사이에 있으면 즉시 한 번 돈다(알림이 늦지 않도록).
   (`검증 수준: 코드 확인` — `Sources/Model/UsageStore.swift:296-337`)

6. **데드라인은 취소가 아니다.**
   Claude fetch 바닥에는 동기 `SecItemCopyMatching`이 있어 `Task.cancel()`이 닿지 않는다.
   그래서 데드라인은 "스토어가 기다리기를 그만두는 것"만 하고, 늦게 도착한 응답은
   provider별 `generations` 카운터로 버린다.
   (`검증 수준: 코드 확인` — `UsageStore.refreshDeadline` 주석과 `armDeadline()/abandon()`)

7. **노치는 1차원 "stack space"에서만 계산된다.**
   `along`(스택 길이 방향) / `across`(베젤에서 안쪽으로)만 쓰고,
   실제 화면 좌표로 되돌리는 곳은 `NotchPlacement` 한 군데뿐이다. 네 방향 가장자리를 같은 코드로 처리하기 위한 분리다.
   (`검증 수준: 코드 확인` — `Sources/Notch/NotchPlacement.swift:3-12`)

8. **"끝났다"는 상태가 아니라 전이(transition)다.**
   `SessionCompletionWatcher`는 직전 상태를 들고 있다가 `busy → idle/blocked` **교차**만 보고한다.
   AppKit 의존이 없는 순수 struct로 만들어 테스트가 직접 구동할 수 있게 했다.
   (`검증 수준: 코드 확인` — `Sources/Sessions/SessionCompletionWatcher.swift:1-25`)

9. **테스트 실행 자체가 부작용이 되지 않게 막는다.**
   `Runtime.isUnderTest`는 유닛 번들이 앱 자신에 호스팅되므로 테스트 실행이 곧 "실행 중인 Codenotch"라는 점을 다룬다.
   이 가드가 없을 때 `make test` 한 번이 실제 usage 엔드포인트를 때리고 노치 패널 40개를 화면에 띄웠다고 주석이 적고 있다.
   (`검증 수준: 코드 확인` — `Sources/App/Runtime.swift`)

> 코드 주석의 밀도가 매우 높고, 대부분이 **"왜 이렇게 했는가 / 이렇게 안 하면 어떤 버그가 났는가"** 를 적고 있다.
> 이 레포는 주석이 설계 결정 기록(ADR에 가까운 것) 역할을 한다. 다만 그 서술은 **저자의 주장**이며,
> 본 문서에서 "코드 확인"으로 표시한 것은 *해당 코드와 주석이 그 위치에 실제로 존재한다*는 뜻이다.
> 주석이 말하는 과거 버그 재현 여부는 `미확인`이다.

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | `Sources/` 모듈 경계와 AppDelegate의 배선 |
| 대표 실행 흐름 | [flow.json](./diagrams/flow.json) | [flow.html](./diagrams/flow.html) | usage refresh 1회 패스(틱 → fetch → 발행 → 저하) |
| 사용량 취득 경로 | [system.json](./diagrams/system.json) | [system.html](./diagrams/system.html) | 자격증명 원천 5종 → 어댑터 → 벤더 엔드포인트 → 노치 |

**산출물 검증 상태** (archify `deliver` + `visual-check`):

- `structure.html` — validate/deliver 9/9 통과, errors 0 / warnings 0, repository evidence 10건 검증(SHA `414ceaf…`에 실제 존재하는 경로임을 archify가 확인). `visual-check` 1440×900 / 1600×1000 / 1920×1080 / 2048×1320 (light·dark) 전부 통과.
- `flow.html` — validate/deliver 9/9 통과, errors 0 / warnings 0, `visual-check` 동일 4개 뷰포트 통과.
- `system.html` — validate/deliver 9/9 통과, errors 0 / warnings 0, repository evidence 10건 검증. `visual-check` 동일 4개 뷰포트(light·dark) 통과. 2048×1320 light 스크린샷 직접 확인 (`실행 확인`).
  > 한국어로 작성한 다이어그램이다. archify의 `meta.locale`은 `en`/`zh-CN`만 지원하므로 **뷰어 UI와 `<html lang>`은 영어로 폴백**된다. 작성한 내용(노드·라벨·카드)은 한국어 그대로다.
- 시각적 검토: 세 그림 모두 2048×1320 light 스크린샷을 직접 확인함 (`실행 확인`). 그 외 뷰포트는 자동 측정치만 확인 (`미확인`).

### 그림 읽는 가이드

**structure.html — 가로 한 줄이 주 경로다.**
1. `Coding tools on the Mac` → `Providers` → `Model / UsageStore` → `Notch / NotchFleet` → `Features`.
   왼쪽 끝은 Mac에 이미 있는 CLI·에디터·로컬 데몬이고, 빨간 점선은 "빌린 자격증명"이라는 뜻이다.
2. 아래쪽 가지 둘은 **주 경로가 아니다**. `Sessions`는 숫자가 아니라 `isBusy`만 스토어에 준다(폴링 주기 결정).
   `UsageArchive`는 마지막 성공 리딩을 launch 너머로 보존한다.
3. 위쪽의 `App / AppDelegate`가 전부를 조립하고, `Settings / Preferences`가 순서·연결 여부를 스토어에 밀어 넣는다.
4. 미확인 영역: `PhoneLink`는 소스에서 `isAvailable = false`로 꺼져 있다. 실제 동작 경로는 이번 세션에서 확인하지 않았다.
   `Features` 내부(링 렌더링, tooltip 레이아웃 산식)도 아직 열지 않았다.

**system.html — 왼쪽 열 다섯 개가 "사용량을 어디서 얻는가"의 전부다.**
1. CLI 서브프로세스 / 키체인 / 파일·SQLite·HTTP 캐시 / 로컬 데몬·언어서버 / 자체 WKWebView — 이 다섯 가지뿐이다.
2. 가운데 위 `프로필 자동 탐색`이 계정 개수를 정하고, 그 수만큼 어댑터 actor가 만들어진다.
3. 오른쪽 위 `벤더 내부 엔드포인트`로 가는 빨간 점선이 유일한 외부 호출이고, 전부 비공개 경로다.
4. 아래 카드 3장이 세 가지 질문(벤더 API / 폴링 / 자동 인식)의 요약이다.

**flow.html — 세로로 세 구간(Decide / Fetch / Publish·degrade)이다.**
1. 상단 `Decide`: 타이머 틱이 곧바로 요청이 되지 않는다. `isBusy()`를 물어보고 `shouldRefresh()`를 통과해야 한다.
2. 중간 `Fetch`: `UsageProvider`는 actor이고, 빨간 점선이 벤더 소스(키체인·CLI·HTTP)를 읽는 구간이다.
   성공하면 `ProviderSnapshot`, 실패하면 `UsageProviderError`가 같은 자리로 돌아온다.
3. 하단 `Publish · degrade`: 보라 점선 `deadline fires`가 **취소가 아니라 포기**라는 점이 이 그림의 핵심이다.
   마지막 좋은 리딩을 남기고 `ProviderStatus`만 바꾼 뒤 노치로 발행한다.
4. 429 백오프(60초 → 2배 → 15분 상한, 디스크 영속)는 이 그림에 없다 —
   스토어가 아니라 **provider 안에** 있기 때문이다. `ClaudeOAuthProvider.backoff(forAttempt:retryAfter:)` 참조.
   자세한 경로는 [Q1 문서](./questions/q1-how-usage-is-fetched.md#3-폴링-방식인가--맞다-다만-주기가-상황에-따라-바뀐다)에 있다.

---

## 4. 핵심 질문 및 세부 답변 목록 (Questions)

- [Q1: 사용량을 실제로 어떻게 가져오는가?](./questions/q1-how-usage-is-fetched.md) — *벤더 공개 API는 없다. 소유 앱이 읽는 경로(내부 엔드포인트·CLI 출력·SQLite·언어서버 RPC·HTTP 캐시)를 그대로 읽고, 상황에 따라 주기가 바뀌는 폴링으로 돌리며, 디렉터리 규약 + 자격증명 존재의 2중 판정으로 계정을 자동 인식한다.*

아직 답하지 않은 질문:
2. **Q2. 20개 가까운 provider가 제각각인 벤더 응답을 `LimitWindow` 하나로 정규화한다. 어떤 필드가 "공통분모"로 뽑혔고, 왜 `usedFraction`이 optional인가?**
   → `remaining`만 주는 Perplexity, `used`만 세는 Cursor, 금액으로 계량되는 DeepSeek을 한 모델이 어떻게 담는지.
4. **Q4. 세션 모니터들은 각 CLI의 무엇을 읽어 `busy / idle / blocked`를 판정하는가? (Claude transcript, Codex, Cursor, Ollama relay가 모두 다르다)**
   → `Sources/Sessions/`의 9개 모니터가 공유하는 `AgentActivityMonitor` 계약이 무엇인지.
5. **Q5. 테스트 27,949줄은 무엇을 고정(pin)하고 있는가? "every adapter's response shape is pinned by tests"라는 주장이 실제로 어떤 형태인가?**
   → 외부 의존이 깨지기 쉬운 프로젝트의 테스트 전략 사례로서의 가치.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **축적된 위키 지식**: [wiki/projects/codenotch.md](../../wiki/projects/codenotch.md)
