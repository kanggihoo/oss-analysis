---
title: codenotch
created: 2026-09-21
updated: 2026-09-21
type: project
tags: [open-source, project, architecture, macos, swift, swiftui, adapter-pattern, usage-metering, developer-tools, desktop-app, evidence]
sources:
  - repos/codenotch/README.md
  - repos/codenotch/Sources/Providers/UsageProvider.swift
  - repos/codenotch/Sources/Model/UsageModel.swift
  - repos/codenotch/Sources/Model/UsageStore.swift
  - repos/codenotch/Sources/App/AppDelegate.swift
  - repos/codenotch/Sources/App/Runtime.swift
  - repos/codenotch/Sources/Sessions/ActivityCoordinator.swift
  - repos/codenotch/Sources/Sessions/SessionCompletionWatcher.swift
  - repos/codenotch/Sources/Notch/NotchPlacement.swift
  - repos/codenotch/Sources/Providers/ClaudeOAuthProvider.swift
  - repos/codenotch/Sources/Providers/ClaudeUsageCLI.swift
  - repos/codenotch/Sources/Providers/ClaudeProfile.swift
  - repos/codenotch/Sources/Providers/CodexProfile.swift
  - repos/codenotch/Sources/Providers/CodexLocalProvider.swift
  - repos/codenotch/Sources/Providers/AntigravityBridge.swift
  - repos/codenotch/Sources/Providers/AntigravityProvider.swift
  - repos/codenotch/Sources/Providers/CursorCredentials.swift
  - repos/codenotch/Sources/Providers/OllamaLocalProvider.swift
  - reports/codenotch/overview.md
  - reports/codenotch/questions/q1-how-usage-is-fetched.md
confidence: medium
---

# codenotch

`vinzdg/codenotch`. macOS 화면 가장자리에 붙는 작은 노치 UI로,
Mac에 이미 설치된 코딩 도구들(Claude Code, Codex, Cursor, Copilot, GLM, Kimi, Kiro, Ollama, LM Studio 등)의
**사용량 한도와 세션 활동 상태를 링 하나로 모아 보여주는 앱**.
Swift 5 / SwiftUI + AppKit, MIT, `Sources/` 187 파일 38,444줄 / `Tests/` 93 파일 27,949줄.
`windows/`에 Rust + Tauri 2 포트가 별도로 있다.

분석 기준: commit `414ceaf6173d9988c01ed76d8e924cf0118e3755` (2026-09-20, clean, shallow `--depth 50`).
상세 보고서·다이어그램: [reports/codenotch/overview.md](../../reports/codenotch/overview.md).

## 한 줄 요약

**공개 API가 존재하지 않는 20여 개 벤더의 사용량을, "추측을 사실처럼 보이지 않게 하는" 타입 체계로 흡수한 어댑터 레이어.**

## 문제의 성격

README가 "The honest caveat"라는 절을 따로 두고 인정하듯,
**어떤 벤더도 "세션 한도 N% 사용" 같은 공개 API를 내놓지 않는다.**
그래서 각 어댑터는 내부 엔드포인트, 로컬 SQLite, CLI 표준출력, 언어 서버 RPC,
Chromium HTTP 캐시 파일 같은 **예고 없이 깨질 수 있는 경로**를 읽는다.

이 레포에서 배울 것은 기능이 아니라 **그 불안정성을 코드 구조로 흡수하는 방법**이다.

## 사용량을 어떻게 가져오는가 (모두 `코드 확인` — 상세: [Q1 문서](../../reports/codenotch/questions/q1-how-usage-is-fetched.md))

**벤더가 주는 사용량 API는 없다.** 코드가 때리는 호스트는 전부 내부 경로다 —
`api.anthropic.com/api/oauth/usage`, `chatgpt.com/backend-api/wham/usage`,
`cloudcode-pa.googleapis.com/v1internal:*`, `api.github.com/copilot_internal/user`,
`cursor.com/api/usage-summary`. 이름(`internal`, `wham`, `v1internal`)이 곧 비공개 표시다.

취득 방식은 다섯 가지뿐이다:

| 방식 | 대표 | 특징 |
|---|---|---|
| CLI 서브프로세스 | `claude --print --no-session-persistence --strict-mcp-config /usage` | 이 앱의 키체인 접근이 아예 불필요해진다 |
| 로그인 키체인 | `Claude Code-credentials` | 동기 블록 → `UsageStore` deadline 설계의 원인 |
| 파일 · SQLite · HTTP 캐시 | `~/.codex/auth.json`, Cursor `state.vscdb`, Claude Desktop Chromium 캐시 | 읽기 전용. zstd 디코더를 벤더링해야 했던 이유 |
| 로컬 데몬 · 언어서버 | Antigravity LS, Ollama `api/ps`, LM Studio SDK 소켓 | 클라이언트 신원 문제를 우회하는 유일한 길 |
| 자체 WKWebView 세션 | DeepSeek · QianwenAI · MiniMax | 유일하게 Codenotch가 세션을 만드는 경로 |

**훔칠 만한 패턴 — 클라이언트 신원 벽은 "소유 앱의 로컬 서버"로 넘는다.**
Google의 `retrieveUserQuotaSummary`는 개인 계정에 403 *"valid license가 없다"*를 준다.
API가 *누가 묻는지*를 판정하는데 Codenotch는 자기가 Antigravity라고 주장할 수 없기 때문이다.
그래서 Antigravity가 이 머신에서 돌리는 **언어서버**를 부른다 — Antigravity 자신의 창도 그렇게 한다.
포트는 `ps`/`lsof`를 spawn해 찾고, 서버가 두 포트를 열되 어느 쪽인지 광고하지 않아 **둘 다 시도한다**.
CSRF 헤더 `x-codeium-csrf-token`은 여섯 번 틀린 끝에 바이너리에서 찾았다고 주석이 적고 있다.
(`AntigravityBridge.swift:1-35`)

**자동 인식 = 디렉터리 규약 + 자격증명 존재의 2중 판정.**
앱이 Finder에서 실행되므로 셸 alias의 `CLAUDE_CONFIG_DIR` / `CODEX_HOME`이 도달하지 않는다.
그래서 `~/.claude-<slug>` · `~/.codex-<slug>` 규약을 훑는다. 그런데 규약만으로는 부족하다 —
플러그인 `claude-mem`이 `~/.claude-mem`에 첫 실행 파일들을 전부 쓰기 때문에 파일명 판정을 통과한다.
2차로 **그 디렉터리 이름으로 된 키체인 항목이 있는가**를 묻는다. 토큰 없으면 계정 아니고, 링도 없다.
플러그인 이름 denylist는 다음 플러그인에서 깨지지만 이 판정은 안 깨진다. (`ClaudeProfile.swift:33-90`)
탐색은 **런치 시 1회**이므로 프로필 추가에는 재시작이 필요하다 (`AppDelegate.swift:69-71`).
로컬 런타임은 포트 응답으로 판정하고, 없으면 `isVisibleWhenAbsent = false`로 링 자체를 만들지 않는다.

**폴링 주기는 상황에 따라 바뀐다.** 바쁠 때 60초 / 유휴 5분 / 로컬 런타임 1초,
window의 `resetsAt`이 직전 시도와 지금 사이를 지나면 즉시 1회, wake·언어 변경 시에도 즉시.
429는 `min(15분, max(60 * 2^min(n,4), Retry-After))` — 서버의 `Retry-After: 0`은 바닥을 올리는 용도로만 쓴다.
이 deadline은 `UsageArchive`에 저장되어 **앱을 껐다 켜도 우회되지 않는다.**
(`ClaudeOAuthProvider.swift:429-435`, `CodexLocalProvider.swift:27`)

## 핵심 설계 결정 (모두 `코드 확인`)

1. **신뢰도를 타입으로 강제한다.**
   `enum Fidelity { official, derived, manual }`. `qualifier`가 official이 아니면 `~`를 붙인다
   (`Sources/Model/UsageModel.swift:15`). 어떤 어댑터도 파생값을 벤더 공표값처럼 렌더링할 수 없다.

2. **실패를 숫자로 위장하지 않는다.**
   `ProviderStatus`: `ok / stale(since:) / needsAuth / signedOutByOwner / accessDenied / unsupported / error`.
   `UsageProviderError`는 `needsAuth`(아무도 로그인한 적 없음)와 `signedOutByOwner`(로그인했었는데 소유 앱이 비움)와
   `accessDenied`(macOS가 거부)를 **의도적으로 분리**한다. 이 구분이 "마지막 리딩을 살릴지"를 결정한다.

3. **자격증명을 만들지 않고 빌린다.**
   대부분의 provider는 이미 Mac에 있는 도구의 세션을 읽는다.
   자체 세션을 만드는 것은 `WebSessionProvider`(DeepSeek / QianwenAI / MiniMax)뿐이고,
   그래서 `signOut()` / `presentSignIn()`이 provider마다 의미가 다르다는 점이 프로토콜 주석에 명시되어 있다.

4. **헤드라인 창을 "선언"하게 한다.**
   `ProviderSnapshot.headlineID` / `weeklyID`. 선언된 window가 응답에 없으면 **링을 비운다.**
   위치(첫 번째 window)로 고르면 창 하나가 빠질 때 링이 모양을 유지한 채 조용히 주제를 바꾸기 때문.
   → 훔칠 만한 패턴: *파생 UI가 가리키는 대상을 데이터가 명시하게 하고, 못 찾으면 대체하지 말고 비운다.*

5. **틱은 요청이 아니다.**
   `UsageStore.shouldRefresh(isBusy:sinceLastAttempt:idleInterval:resetDue:)`는 **순수 함수**로 뽑혀 있다.
   유휴 시 5분, 바쁠 때 60초. 단 어떤 window의 `resetsAt`이 직전 시도와 현재 사이를 지났으면 즉시 한 번 돈다.
   → 훔칠 만한 패턴: *스케줄 결정을 시계·스토어 없이 테스트할 수 있는 순수 함수로 분리.*

6. **데드라인은 취소가 아니라 포기다.**
   fetch 바닥의 동기 `SecItemCopyMatching`은 `Task.cancel()`이 닿지 않는다(키체인 승인 다이얼로그 대기).
   그래서 데드라인은 **스토어가 기다리기를 그만두는 것**만 하고, 늦게 온 응답은 provider별 `generations` 카운터로 버린다.
   → 훔칠 만한 패턴: *취소 불가능한 blocking 호출을 감싸는 대신, 호출자의 대기를 끊고 결과를 세대 번호로 무효화한다.*

7. **활동(activity)과 사용량(usage)을 분리한다.**
   세션 모니터가 스토어에 주는 유일한 입력은 `isBusy`이고, 그건 **폴링 주기**만 바꾼다.
   `ActivityCoordinator`(46줄)는 모니터의 수명만 관리한다.

8. **"끝났다"는 상태가 아니라 전이다.**
   `SessionCompletionWatcher`는 직전 상태를 들고 `busy → idle/blocked` **교차**만 보고한다.
   AppKit 의존 없는 순수 struct라 테스트가 직접 구동한다.

9. **노치 기하는 1차원 stack space에서만 계산한다.**
   `along`(스택 방향) / `across`(베젤에서 안쪽). 실제 화면 좌표로 되돌리는 곳은 `NotchPlacement` 한 군데뿐.
   네 방향 가장자리 + 하드웨어 노치를 같은 레이아웃 코드로 처리하기 위한 분리.

10. **테스트 실행이 부작용이 되지 않게 막는다.**
    `Runtime.isUnderTest`. 유닛 번들이 앱 자신에 호스팅되므로 테스트 실행이 곧 "실행 중인 Codenotch"다.
    가드 없을 때 `make test` 한 번이 실제 usage 엔드포인트를 때리고 노치 패널 40개를 화면에 띄웠다고 주석에 적혀 있다.

## 모듈 규모 (라인 수)

| 모듈 | 줄 | 역할 |
|---|---|---|
| `Sources/Providers` | 15,446 | 어댑터 77파일. 앱의 40% |
| `Sources/Settings` | 5,638 | 환경설정·순서·외형 |
| `Sources/Notch` | 4,281 | 패널·기하·배치 |
| `Sources/Sessions` | 4,045 | 활동 모니터 9종 + 완료 감지 |
| `Sources/Model` | 2,610 | UsageStore / 데이터 모델 |
| `Sources/Features` | 2,592 | 링·tooltip·pace |
| `Sources/App` | 1,853 | 배선·메뉴바·업데이터 |
| `Sources/PhoneLink` | 1,679 | LAN 페어링 서버 (`isAvailable = false`로 꺼져 있음) |

**Providers가 전체의 40%라는 사실 자체가 이 프로젝트의 정의다** — 앱의 본질이 UI가 아니라 어댑터라는 뜻.

## Taste Notes

- **주석이 설계 결정 기록(ADR) 역할을 한다.** 대부분의 주석이 "왜 이렇게 했는가 / 이렇게 안 했을 때 난 버그"를
  구체적으로 적는다. 분석 효율이 매우 높다. 다만 **저자의 주장**이므로 코드 존재 확인과 주장 검증을 분리해야 한다.
- **테스트:소스 비율 0.73.** 외부 의존이 깨지기 쉬운 프로젝트가 신뢰를 유지하는 방식으로,
  "모든 어댑터의 응답 shape를 테스트로 고정"한다고 README가 주장한다. (아직 `미확인`)
- **정직함을 기능으로 취급한다.** `Percent.halves()`가 0.3% 사용을 "0%"로 반올림하지 않고 "0.3% Used · 99.7% left"로
  내는 이유를 주석이 길게 설명한다. 숫자 표현 규칙 자체가 제품 결정으로 다뤄진다.
- **비교 메모**: [[tokscale-data-flow-pipeline]]와 소재가 겹친다 — 둘 다 코딩 에이전트의 사용량을 읽는다.
  다만 Tokscale은 **로컬 로그 ETL**(이미 디스크에 있는 것을 집계)이고, Codenotch는 **라이브 벤더 조회**
  (남은 한도를 지금 물어본다)다. 전자는 사후 분석, 후자는 실시간 계기판. (`추론` — Tokscale 쪽 재확인 필요)

## 아직 확인하지 않은 것

- 각 provider의 **응답 파싱부**(`*Usage.swift` 계열 ~20개)는 전부 미확인 — `LimitWindow` 정규화 규칙이 여기 있다.
- `fetch(retryingOnUnauthorized:)` 내부의 HTTP 응답 → `ProviderStatus` 매핑.
- `CredentialCache` — "키체인 항목의 수정 날짜"로 재읽기를 결정한다는 주장의 구현.
- `Sources/Notch` / `Features` / `Settings` 내부 전부.
- `Tests/` 내용 전부. "응답 shape 고정"이 실제로 어떤 형태인지.
- `windows/` Rust 포트가 Swift 본체와 어떻게 동기화되는지.
- **실행 검증 전무.** macOS 전용(`xcodegen` + `xcodebuild`)이고 분석 환경이 Windows라
  이 레포의 검증 수준 상한은 `코드 확인`이다.

관련: [[evidence-backed-analysis]] · [[open-source-analysis-judgment-model]] · [[workspace-boundaries]]
