# Next Session Plan: Codenotch

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `414ceaf6173d9988c01ed76d8e924cf0118e3755`
- **작성/갱신 일자**: `2026-09-21` (2회차 갱신 — Q1 답변 후)

---

## 1. 이번 세션에서 확인한 범위

- [x] 코드 기준 기록 (`artifacts/codenotch/repo-metadata.txt`) — SHA, clean 여부, 모듈별 라인 수
- [x] `Sources/` 모듈 경계 파악 (App / Model / Providers / Sessions / Notch / Features / Settings / PhoneLink / DesignSystem / Vendor)
- [x] `UsageProvider` 프로토콜 및 `UsageProviderError` 전체 케이스 읽음
- [x] `ProviderSnapshot` / `LimitWindow` / `Fidelity` / `ProviderStatus` 데이터 모델 읽음
- [x] `UsageStore` 폴링 스케줄(`tick` → `shouldRefresh` → `refreshNow` → `armDeadline`) 읽음
- [x] `AppDelegate.applicationDidFinishLaunching` 배선 순서 읽음 (79–260행)
- [x] `ActivityCoordinator` 전체 읽음 (46줄)
- [x] archify 구조도 + 실행 흐름 + **사용량 취득 경로** 다이어그램 3종 생성·검증 (`diagrams/`)
- [x] **Q1 답변 완료** — [questions/q1-how-usage-is-fetched.md](./questions/q1-how-usage-is-fetched.md)
  - `ClaudeOAuthProvider.fetchSnapshot()` 3단 폴백 순서와 Deny/"다시 묻기" 분기
  - `ClaudeUsageCLI` 서브프로세스 인자 4개와 각각의 부작용 회피 이유
  - `AntigravityBridge` — Google 403을 피해 Antigravity 언어서버를 경유하는 이유와 `ps`/`lsof` 포트 탐색
  - `ClaudeProfile.discover()` / `CodexProfile.discover()` — 디렉터리 규약 + 자격증명 2중 판정
  - `ClaudeOAuthProvider.backoff(forAttempt:retryAfter:)` — 429 백오프 수식과 `UsageArchive` 영속 (**기존 Q3 해소**)
  - 20개 provider의 엔드포인트 전수 추출

## 아직 **읽지 않은** 곳 (중요)

- `Sources/Providers/` 77개 파일 중 읽은 것: `UsageProvider.swift`(전체), `ClaudeOAuthProvider.swift`(주요 함수),
  `ClaudeUsageCLI.swift`(상단), `ClaudeProfile.swift`/`CodexProfile.swift`(탐색 로직),
  `AntigravityProvider.swift`/`AntigravityBridge.swift`(상단), `CursorCredentials.swift`(상단),
  `CodexLocalProvider.swift`(상단), `GitHubCopilotProvider.swift`(상단), `OllamaLocalProvider.swift`, `LMStudioLink.swift`(상단).
  **응답 파싱부(`*Usage.swift` 계열 ~20개)는 전부 미확인.**
- `Sources/Notch/` 4,281줄, `Sources/Features/` 2,592줄, `Sources/Settings/` 5,638줄은 파일 목록만 확인.
- `Tests/` 93개 파일은 파일명·크기만 확인. 내용 미확인.
- `windows/` (Rust/Tauri 포트)는 파일 수만 셈.
- 빌드·테스트 미실행 — macOS 전용(`xcodegen` + `xcodebuild`)이고 현재 환경은 Windows다. **이 레포는 이 머신에서 `실행 확인` 수준에 도달할 수 없다.**

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [x] ~~Q1. 사용량 취득 경로 전반~~ → 답변 완료
- [x] ~~Q3. 429 백오프의 구현 위치와 디스크 영속~~ → Q1 문서 3절에서 해소
- [ ] Q1-a. 각 단계 실패가 `ProviderStatus`로 매핑되는 지점 (`fetch(retryingOnUnauthorized:)` 내부는 아직 미확인)
- [ ] Q1-b. `CredentialCache` — "키체인 항목의 수정 날짜"로 재읽기를 결정하는 구조
- [ ] Q1-c. `WebSessionProvider`가 WKWebView 세션으로 page-local 요청을 재생하는 방식
- [ ] Q2. 벤더별로 다른 응답이 `LimitWindow` 하나로 정규화되는 방식 (`usedFraction`이 optional인 이유)
- [ ] Q4. `AgentActivityMonitor` 프로토콜 계약과 9개 모니터가 `busy/idle/blocked`를 판정하는 서로 다른 근거
- [ ] Q5. "every adapter's response shape is pinned by tests"가 실제 테스트 코드에서 어떤 형태인지
- [ ] Q6. `NotchLayout`이 디자인 프레임 PNG에서 수치를 인용한다고 README가 말하는데, 그 대조가 코드/테스트로 어떻게 강제되는가
- [ ] Q7. `windows/` Rust 포트가 Swift 본체와 provider 목록·동작을 어떻게 맞추는가 (중복 구현인가, 별도 구현인가)

---

## 3. 다음에 볼 파일 및 함수 (Next Entry Points)

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `Sources/Providers/ClaudeOAuthProvider.swift` | `fetch(retryingOnUnauthorized:)` | HTTP 응답 → `ProviderStatus` 매핑 (Q1-a) |
| `Sources/Providers/CredentialCache.swift` | 수정 날짜 기반 재읽기 | 키체인 프롬프트를 피하는 캐시 무효화 (Q1-b) |
| `Sources/Providers/ClaudeDesktopUsageCache.swift` | 캐시 엔트리 탐색 | Chromium HTTP 캐시를 org id로 좁히는 방식 + zstd 디코드 경계 |
| `Sources/Providers/CursorLocalProvider.swift` · `CursorUsage.swift` | 응답 파싱 | `used`만 세는 벤더가 `LimitWindow`에 담기는 형태 (Q2) |
| `Sources/Model/UsageStore.swift` | `refresh()` · `beginRefresh()` · `publish()` · `abandon()` (415–510행) | generation 카운터로 늦은 응답을 버리는 실제 코드 |
| `Sources/Sessions/AgentActivityMonitor.swift` | 프로토콜 정의 | 9개 모니터의 공통 계약 (Q4) |
| `Sources/Sessions/ClaudeSessionMonitor.swift` · `ClaudeTranscript.swift` | transcript 파싱 | busy/blocked 판정 근거 |
| `Tests/UsageResponseTests.swift` (49.7K) · `ClaudeOAuthProviderTests.swift` (36.2K) | 픽스처 구조 | 응답 shape 고정 방식 (Q5) |
| `Tests/UsageRefreshDeadlineTests.swift` | 데드라인 시나리오 | 포기(abandon) 동작의 테스트 표현 |

---

## 4. 참고 사항 및 후속 제안

- **플랫폼 제약**: macOS 전용 앱이라 현재 Windows 환경에서 `make test` / `make run`이 불가능하다.
  따라서 이 레포에 대한 검증 수준의 상한은 `코드 확인`이다. 문서에 `실행 확인`을 쓰지 말 것.
- **shallow clone**: `--depth 50`이라 `git log`가 50커밋까지만 보인다. 히스토리 기반 질문(왜 이렇게 바뀌었나)을
  하려면 `git fetch --unshallow` 필요. 클론이 느렸으므로 실제로 필요할 때만 할 것.
- **주석이 1차 사료**: 이 레포는 주석에 "이렇게 안 했을 때 난 버그"가 구체적으로 적혀 있다.
  분석 효율이 매우 높지만, **저자의 주장**이므로 코드 위치 확인과 주장 자체를 구분해 기록할 것.
- **`TASKS.md`가 102KB**: 구현 히스토리가 통째로 들어 있다. Q1~Q7 대부분의 배경 설명이 여기에 있을 가능성이 크다.
  단, 이는 저자 서술이므로 `추론`/`미확인`으로 취급하고 코드로 교차검증할 것.
- **다음 세션 추천 순서**: Q2 → Q4 → Q5. Q1이 "어디서 가져오는가"를 끝냈으니, 다음은 "가져온 것을 어떻게 한 모델로 만드는가"(Q2)가 자연스럽다.
