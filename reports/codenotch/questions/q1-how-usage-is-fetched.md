# Q1. Codex / Claude Code / Gemini 사용량을 실제로 어떻게 가져오는가?

- **상위 개요**: [overview.md](../overview.md)
- **기준 Commit SHA**: `414ceaf6173d9988c01ed76d8e924cf0118e3755`
- **작성일**: `2026-09-21`
- **관련 그림**: [system.html](../diagrams/system.html) (사용량 취득 경로), [flow.html](../diagrams/flow.html) (refresh 1회 패스)

---

## 짧은 결론

1. **벤더가 제공하는 "사용량 공개 API"는 없다.** 대신 각 어댑터가 **소유 앱이 자기 화면을 그릴 때 읽는 바로 그 경로**를
   똑같이 읽는다 — 내부 엔드포인트, CLI 표준출력, 로컬 SQLite, 언어서버 RPC, Chromium HTTP 캐시 파일.
2. **자격증명은 새로 만들지 않고 "빌린다."** Codenotch가 직접 로그인시키는 것은 WKWebView 3종(DeepSeek/QianwenAI/MiniMax)뿐이다.
3. **폴링은 맞지만 고정 주기가 아니다.** 바쁠 때 60초, 유휴 5분, 로컬 런타임 1초. window가 리셋되는 순간엔 주기를 무시하고 즉시 1회.
   429를 맞으면 60초에서 2배씩, 15분 상한으로 물러나고 그 deadline은 **디스크에 남아 재실행해도 지켜진다.**
4. **자동 인식은 "디렉터리 규약 + 자격증명 존재"의 2중 판정이다.** 규약만 믿으면 플러그인 디렉터리를 계정으로 오인한다.

---

## 1. 벤더 API가 따로 있는가? — 없다

README가 "The honest caveat" 절에서 직접 인정한다:

> No vendor publishes a clean "your session limit is N% used" API for any of these tools.
> Each adapter reads whatever the owning app itself reads from — an internal endpoint, a local
> database, a language server's own RPC — and those can change without notice.

`검증 수준: 코드 확인` — README.md:336-343

실제로 코드가 때리는 호스트를 전부 뽑아보면 **전부 벤더의 내부/비공개 엔드포인트**다:

| Provider | 엔드포인트 | 근거 |
|---|---|---|
| Claude Code | `https://api.anthropic.com/api/oauth/usage` (`anthropic-beta: oauth-2025-04-20` 헤더) | `ClaudeOAuthProvider.swift:34`, `:353` |
| Codex | `https://chatgpt.com/backend-api/wham/usage` | `CodexLocalProvider.swift:50` |
| Gemini (Antigravity) | `https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist`, `https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary` | `AntigravityProvider.swift:28-30` |
| Cursor | `https://cursor.com/api/usage-summary` | `CursorLocalProvider.swift:18` |
| GitHub Copilot | `https://api.github.com/copilot_internal/user` | `GitHubCopilotProvider.swift:9` |
| Kimi | `https://api.kimi.com/coding/v1/usages` | `KimiUsage.swift` |
| OpenCode | `https://opencode.ai/zen/go/v1/usage` | `OpenCodeProvider.swift` |
| Grok | `https://cli-chat-proxy.grok.com/v1/billing` | `GrokLocalProvider.swift` |

`검증 수준: 코드 확인` — `grep -rhoE 'https://[a-zA-Z0-9./_-]+' Sources/Providers/*.swift` 실행 결과 + 각 파일 확인.
**네트워크 실행은 하지 않았다** (macOS 전용 앱, 분석 환경은 Windows). 엔드포인트가 지금도 응답하는지는 `미확인`.

> `copilot_internal`, `backend-api/wham`, `v1internal` — 이름 자체가 비공개 표시다.
> 이 경로들이 예고 없이 깨질 수 있다는 것이 이 레포 설계의 전제다.

---

## 2. 사용량 취득의 5가지 방식

`Sources/Providers/`의 77개 파일은 결국 아래 다섯 가지 방식 중 하나로 자격증명이나 수치를 얻는다.
그림: [system.html](../diagrams/system.html) 왼쪽 열.

### (a) CLI 서브프로세스를 띄워 표준출력을 읽는다 — Claude Code

`claude` 바이너리를 직접 실행해 `/usage` 출력을 파싱한다.

```
["--print", "--no-session-persistence", "--strict-mcp-config", "/usage"]
```

`검증 수준: 코드 확인` — `Sources/Providers/ClaudeUsageCLI.swift:54`

**왜 굳이 서브프로세스인가?** 주석이 이유를 명시한다 — Claude Code는 **토큰 회전마다 키체인 항목을 새로 만들고,
새 항목의 access list에는 이 앱이 없다.** 그래서 사용자가 "항상 허용"을 눌러도 한 시간쯤 뒤 다시 물어본다.
CLI에 물어보면 Claude Code가 이미 들고 있는 자격증명을 쓰므로 **이 앱은 키체인에 접근할 필요가 아예 없다.**
(`ClaudeUsageCLI.swift:5-15`)

플래그 하나하나가 부작용 회피다 (`:31-55`):
- `--print` — 워크스페이스 신뢰 다이얼로그를 건너뛴다
- `--no-session-persistence` — 폴링마다 transcript가 쌓이는 것을 막는다
- `--strict-mcp-config` (with no `--mcp-config`) — MCP 서버를 아예 안 띄운다.
  없으면 폴링마다 사용자가 설정한 MCP 서버 십수 개가 Node 프로세스로 뜬다고 주석이 적고 있다
- 작업 디렉터리는 **고정** — 매번 임시 디렉터리를 쓰면 `<config>/projects/` 아래 폴더가 시간당 12개씩 영구히 쌓였다
- 20초 타임아웃, 5분 스로틀 (`ClaudeOAuthProvider.cliRefreshInterval`)

### (b) macOS 로그인 키체인 — Claude(폴백), Cursor(agent), Antigravity

`kSecClassGenericPassword`로 읽는다. Claude의 서비스명은 `Claude Code-credentials`,
프로필별로는 `Claude Code-credentials-<~/.claude 경로 해시>`.

`검증 수준: 코드 확인` — `Sources/Providers/ClaudeProfile.swift:229`, `:247`, `Sources/Providers/KeychainItem.swift:46`

> 키체인 읽기는 승인 다이얼로그 뒤에서 **동기적으로 블록**된다. 이게 `UsageStore`의 deadline 설계 이유다 —
> [flow.html](../diagrams/flow.html) 참조.

### (c) 로컬 파일 · SQLite · HTTP 캐시 — Codex, Cursor, Grok, OpenCode, Command Code, GLM, Claude Desktop

읽기 전용으로 연다. 대표 경로:

| 도구 | 경로 | 형식 |
|---|---|---|
| Codex | `~/.codex/auth.json` | JSON |
| Cursor (에디터) | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` | SQLite |
| Cursor (CLI) | `~/.cursor/cli-config.json` + 키체인 `cursor-access-token` | JSON + 키체인 |
| Grok | `~/.grok/auth.json` | JSON |
| OpenCode | `~/.local/share/opencode/auth.json` | JSON |
| Command Code | `~/.commandcode/auth.json` | JSON |
| GLM | Claude Code의 `~/.claude/settings.json`, ZCode, OpenCode 중 키를 가진 곳 | JSON |
| Claude Desktop | `~/Library/Application Support/Claude` 아래 Chromium HTTP 캐시 | 바이너리 + zstd |

`검증 수준: 코드 확인` — 각 `*Credentials.swift` 및 `grep` 결과

Cursor 주석이 이 방식의 제약을 잘 보여준다 (`CursorCredentials.swift:9-20`):
- SQLite를 **read-only로 열되 `immutable`로는 열지 않는다** — 실행 중인 에디터를 막지 않고,
  회전된 토큰을 stale 체크포인트에서 읽지 않기 위해
- 에디터와 CLI는 **같은 쿠키**를 쓴다: `WorkosCursorSessionToken={accountID}::{accessToken}`.
  에디터는 두 조각을 SQLite에 나눠 저장하고, CLI는 JWT를 키체인에, 계정 id를 JSON에 둔다.
  토큰만으로 된 쿠키나 Bearer 헤더는 401 — **쌍이 필요하다**

Claude Desktop 캐시는 별도로 특이하다: Chromium 앱이라 자기 패널이 그린 usage 응답이 HTTP 캐시 파일로 남는다.
그 바디가 `content-encoding: zstd`인데 macOS에 디코더가 없어서 **decode-only Zstandard를 벤더링**했다
(`Sources/Vendor/zstd`, BSD-3-Clause). 이 계정의 `/api/organizations/<id>/usage` 항목만 열고,
30분보다 오래된 스냅샷은 live로 치지 않는다. (`검증 수준: 코드 확인` — `ClaudeDesktopUsageCache.swift:340`, README:344-364)

### (d) 로컬 데몬 · 언어서버 — Gemini(Antigravity), Ollama, LM Studio

**이게 Gemini 이야기의 핵심이고, 가장 흥미로운 부분이다.**

Google은 Codenotch를 거절한다. `retrieveUserQuotaSummary`를 `cloudcode-pa`에 직접 때리면
개인 계정에는 403 *"You do not have a valid license of this product"* 가 돌아온다.
**API가 "누가 묻는가"를 판정하는데, Codenotch는 자기가 Antigravity라고 정직하게 주장할 수 없기 때문이다.**

주석이 이어서 말한다 — Antigravity 자신도 같은 문제를 같은 방법으로 푼다.
**Antigravity의 창도 Google을 직접 부르지 않는다.** 이 머신에서 도는 자기 언어서버를 부르고,
그 언어서버가 자격증명과 클라이언트 신원을 들고 대신 호출한다.

> "So this is not a workaround for a locked door; it is the door Antigravity itself uses.
> It works only while Antigravity is running, which is honest: the figure comes from Antigravity,
> so Antigravity has to be there."

`검증 수준: 코드 확인` — `Sources/Providers/AntigravityBridge.swift:1-17`

그 언어서버를 찾는 방법이 또 물리적이다 (`AntigravityBridge.swift:19-35`):
- **`ps`와 `lsof`를 spawn해서 포트를 찾는다.** 비싸서 한 번 찾으면 동작이 멈출 때까지 캐시한다
- 서버가 포트를 **두 개** 여는데 어느 쪽이 이 RPC를 서비스하는지 광고하지 않는다 → **둘 다 시도한다**
- CSRF 헤더 이름이 `x-codeium-csrf-token`이다 (Antigravity가 Codeium 스택 기반).
  주석: *"여섯 가지 그럴듯한 철자를 거절당한 끝에 바이너리에서 찾았다 — 서버는 어느 헤더를 원하는지 절대 말해주지 않고
  'missing CSRF token'만 반복한다"*

그리고 **쿼터가 아예 없으면 링을 만들지 않는다.** `:loadCodeAssist`는 어떤 플랜인지만 답하고 숫자를 주지 않는다.
그럴 땐 "측정되는 게 없다"고 정직하게 말한다 — `AntigravityProvider.swift:4-16`:

> "a confident 0% is worse than an admitted blank, especially in something people pay for."

Ollama / LM Studio는 더 단순하다 — 로컬 HTTP/WebSocket이다:
- Ollama: `GET <endpoint>/api/ps`, 타임아웃 3초 (`OllamaLocalProvider.swift:25-27`)
- LM Studio: SDK WebSocket(`lms ps`가 쓰는 그 채널) + `~/.lmstudio/server-logs` 파일.
  포트는 `~/.lmstudio/.internal/http-server-config.json`에서 읽는다 (`LMStudioLink.swift:1-12`)

### (e) 자체 WKWebView 세션 — DeepSeek, QianwenAI, MiniMax

유일하게 Codenotch가 **자기 세션을 만드는** 경로. 사용자가 앱 안 WKWebView에서 명시적으로 로그인하고,
그 세션 저장소는 Codenotch 것이다. **브라우저의 쿠키 저장소는 절대 읽지 않는다.**

`검증 수준: 코드 확인` — `Sources/Providers/WebSessionProvider.swift`, `Sites.swift`, README:112-120

그래서 `UsageProvider.signOut()`의 의미가 provider마다 다르다는 것이 프로토콜 주석에 명시돼 있다
(`UsageProvider.swift:23-32`): 빌린 자격증명은 버릴 게 없고(세션은 Claude Code/Cursor 것이다),
`WebSessionProvider`만 진짜 로그아웃이다.

---

## 3. 폴링 방식인가? — 맞다. 다만 주기가 상황에 따라 바뀐다

### 세 개의 타이머

`UsageStore` 생성자 기본값 (`Sources/Model/UsageStore.swift:145-153`):

| 값 | 기본값 | 의미 |
|---|---|---|
| `refreshInterval` | 60초 | 메인 틱 주기 |
| `localRefreshInterval` | 1초 | 로컬 런타임(Ollama/LM Studio) 전용 틱 |
| `idleRefreshInterval` | 5분 | 아무것도 안 돌 때 실제로 요청할 최소 간격 |
| `staleAfter` | 15분 | 이 시간 넘으면 리딩이 흐려짐 |
| `refreshDeadline` | 60초 | 한 패스를 기다려 줄 최대 시간 |

### 틱이 곧 요청은 아니다

```swift
static func shouldRefresh(isBusy: Bool, sinceLastAttempt: TimeInterval,
                          idleInterval: TimeInterval, resetDue: Bool = false) -> Bool {
    isBusy || resetDue || sinceLastAttempt >= idleInterval
}
```

`검증 수준: 코드 확인` — `Sources/Model/UsageStore.swift:331-337`

순수 함수라 시계 없이 테스트된다. 세 조건 중 하나라도 맞아야 요청이 나간다:
- **`isBusy`** — 세션 모니터가 "지금 뭔가 돌고 있다"고 말할 때. 주석: *"아무것도 안 도는데 세게 폴링하는 건,
  움직이지 않는 숫자를 다시 읽으려고 rate-limit 예산을 쓰는 것"*
- **`resetDue`** — `hasWindowRolledOver(...)`가 참일 때. 어떤 window의 `resetsAt`이 **직전 시도와 지금 사이**에
  들어 있으면 즉시 한 번 돈다. 이게 없으면 리셋 알림이 몇 분 늦게 떴다고 주석이 적고 있다 (`:318-329`)
- **유휴 간격 경과** — 5분

추가로 두 가지 이벤트가 즉시 refresh를 부른다 (`:239-272`):
- `NSWorkspace.didWakeNotification` — *"깨어나는 순간은 숫자가 반드시 틀려 있는 유일한 순간"*
- 언어 변경 알림 — window의 `label`은 파싱 시점에 결정되어 아카이브에 저장되므로, 다시 읽어야 언어가 바뀐다

### 429 백오프

```swift
static func backoff(forAttempt attempt: Int, retryAfter: TimeInterval?) -> TimeInterval {
    let floor: TimeInterval = 60
    let ceiling: TimeInterval = 15 * 60
    let doubled = floor * pow(2, Double(min(attempt, 4)))
    return min(ceiling, max(doubled, retryAfter ?? 0))
}
```

`검증 수준: 코드 확인` — `Sources/Providers/ClaudeOAuthProvider.swift:429-435`

**서버의 `Retry-After`는 "바닥을 올리는 용도"로만 쓴다.** Claude의 엔드포인트가 `Retry-After: 0`을 주는데
그걸 곧이곧대로 지키면 즉시 재시도 → 계속 rate limited이기 때문 (`:425-428`).
연속 429마다 2배(최대 4회 = 16분치이나 15분으로 캡).

그리고 이 deadline은 **아카이브에 저장된다**:

```swift
self.retryNoEarlierThan = archive.loadBackoffUntil(providerID: profile.id)   // init
archive.saveBackoffUntil(retryNoEarlierThan, providerID: id)                 // 429를 맞았을 때
```

`검증 수준: 코드 확인` — `CodexLocalProvider.swift:27`, `ClaudeOAuthProvider.swift:200-211`
주석: *"Recreating the provider or relaunching must not bypass the server's retry deadline."*
→ **앱을 껐다 켜서 페널티를 우회할 수 없다.**

### 소스별 별도 스로틀

Claude는 소스가 3개라 각각 다른 시계를 쓴다 (`ClaudeOAuthProvider.swift:105-112`):

| 소스 | 간격 | 이유 |
|---|---|---|
| Claude Desktop 캐시 | 재스캔 5분, 신선도 30분 | 파일 읽기라 가장 쌈. 30분 넘은 스냅샷은 live 취급 안 함 |
| `claude "/usage"` CLI | 5분 | 서브프로세스 비용 |
| 키체인 + 엔드포인트 | 스토어 틱 + 429 백오프 | 가장 비싸고, 유일하게 rate limit 대상 |

그리고 **CLI는 엔드포인트의 백오프를 공유하지 않는다** — 주석: *"그 deadline은 엔드포인트의 것이고,
CLI는 엔드포인트의 rate limit을 공유하지 않는다. 한쪽의 429가 다른 쪽이 채울 수 있는 링을 어둡게 할 이유가 없다."*
(`ClaudeOAuthProvider.swift:25-30`)

### 폴백 순서 (Claude 기준)

```swift
func fetchSnapshot() async throws -> ProviderSnapshot {
    if keychain.isRefused { throw UsageProviderError.accessDenied }     // Deny는 모든 소스가 존중
    if keychain.isAskingAgain { return try await fetchFromKeychain() }  // "다시 묻기"는 키체인으로 직행
    if let windows = await desktopWindows() { ... }                     // 1. Desktop 캐시 (공짜, 방해 없음)
    if let windows = await cliWindows() { ... }                         // 2. claude /usage
    return try await fetchFromKeychain()                                // 3. 키체인 + 엔드포인트
}
```

`검증 수준: 코드 확인` — `Sources/Providers/ClaudeOAuthProvider.swift` `fetchSnapshot()`

주목할 만한 두 가지:
- **Deny는 모든 소스에 전파된다.** Desktop 캐시와 CLI는 이 앱의 키체인 접근이 필요 없어서,
  사용자가 거절해도 링을 계속 채웠다 — 이슈 #98로 고쳐졌다
- **"Allow access…"를 눌렀으면 캐시/CLI를 건너뛰고 키체인으로 직행한다.**
  안 그러면 싼 소스가 refresh를 만족시켜서 사용자가 요청한 다이얼로그가 영영 안 뜬다

---

## 4. 어떻게 자동으로 인식하는가?

### 원칙: 파일시스템 규약 + 자격증명 존재의 2중 판정

Claude 프로필 탐색 (`Sources/Providers/ClaudeProfile.swift:33-77`):

```swift
static func discover(home:fileManager:hasCredential:) -> [ClaudeProfile] {
    // ~/ 를 훑어서 ".claude-<slug>" 이름을 찾고
    // 1차: Claude Code가 첫 실행에 쓰는 파일들이 있는가?
    // 2차: 그 디렉터리 이름으로 된 키체인 항목이 있는가?
    // 둘 다 통과한 것만 + 기본 ~/.claude 를 맨 앞에, 나머지는 slug 알파벳순
}
```

**왜 환경변수가 아니라 디렉터리 규약인가?**
주석이 명확하다 (`:6-16`): 앱이 **Finder에서 실행되므로 셸 alias의 `CLAUDE_CONFIG_DIR`가 이 앱에 도달하지 않는다.**
디렉터리가 그 프로필이 남긴 유일한 흔적이다.

**왜 2중 판정인가?** 1차(파일명)만으로는 플러그인을 거를 수 없다.
`claude-mem`은 `~/.claude-mem`에 상태를 두고 첫 실행 파일들을 전부 쓴다 — 파일명 규칙을 통과한다.
하지만 계정이 아니다. Claude Code가 거기에 로그인한 적이 없고 앞으로도 없다.
그러면 링에 뜰 수 있는 말은 *"Sign in to Claude Code in ~/.claude-mem"* — **따를 수 없는 조언**이다.
플러그인 이름 denylist는 다음 플러그인이 나오면 또 깨진다. **자격증명은 깨지지 않는다: 토큰 없으면 계정 아니고, 링도 없다.**

`검증 수준: 코드 확인` — `ClaudeProfile.swift:37-53`

> 세부: `hasCredential`은 토큰의 **유효성**을 보지 않는다. 만료된 토큰도 계정이 존재한다는 뜻이고,
> 그 경우 provider가 `credentialExpired`로 저하시켜 마지막 리딩을 나이와 함께 보여준다 (`:79-88`).

Codex도 동일한 패턴이다 (`CodexProfile.swift`):
- 규약: `~/.codex`, `~/.codex-<slug>`
- 1차 파일 판정: `auth.json`, `config.toml`, `sessions`, `history.jsonl`, `state_5.sqlite`, `sqlite/codex-dev.db` 중 하나라도
- 주석: *"Finder does not inherit a shell's CODEX_HOME."*

Antigravity도 `AntigravityProfile.discover()`로 같은 구조다.

### 탐색 시점: 런치 1회

```swift
private let claudeProfiles = ClaudeProfile.discover()
private let codexProfiles = CodexProfile.discover()
private let antigravityProfiles = AntigravityProfile.discover()
```

`검증 수준: 코드 확인` — `Sources/App/AppDelegate.swift:69-71` (stored property 초기화 = 런치 시 1회)

→ **프로필을 추가하면 재시작이 필요하다.** README도 그렇게 안내한다 (README:186-192).

주석이 이유도 적는다 (`ClaudeOAuthProvider.swift:85`): 매 60초 틱마다 수천 개 디렉터리 엔트리를 훑는 건 안 된다.

### 런타임/데몬은 "응답하는가"로 판정

로컬 런타임은 파일이 아니라 **포트가 답하는지**로 존재를 판정한다.
그리고 없으면 아예 링을 만들지 않는다:

```swift
nonisolated var isVisibleWhenAbsent: Bool { false }   // OllamaLocalProvider
```

`검증 수준: 코드 확인` — `Sources/Providers/OllamaLocalProvider.swift:10`,
프로토콜 기본값은 `true` (`UsageProvider.swift:58`, `:64`)

프로토콜 주석: *"대부분의 provider는 `true`라서 사용자가 sign-in 안내를 볼 수 있다.
로컬 데몬 provider는 `false`를 반환해서, 꺼져 있는 서비스가 노치에서 링 자리를 차지하지 않게 한다."*

Antigravity 언어서버는 한 단계 더 간다 — **한 번이라도 답한 적이 있으면**, 이후 실패는
"계정을 읽을 수 없음"이 아니라 "Antigravity가 닫혔거나 재시작됨"으로 해석한다.
포트가 매 실행마다 바뀌기 때문이다 (`AntigravityProvider.swift:36-41`).

### 그 외 자동 인식되는 것들

| 대상 | 판정 방법 | 근거 |
|---|---|---|
| Cursor 에디터 vs `cursor-agent` | `state.vscdb`에 `cachedEmail` 행이 있으면 에디터, 없으면 CLI config | `CursorCredentials.swift:44-46` |
| GLM 키 | Claude Code `settings.json` → ZCode → OpenCode 순으로 키를 가진 곳 | `GLMCredentials.swift` |
| GitHub Copilot 토큰 | GitHub CLI 세션(`gh auth login`) 또는 기존 환경변수 | `GitHubCopilotProvider.swift:2-3` |
| LM Studio 포트 | `~/.lmstudio/.internal/http-server-config.json` | `LMStudioLink.swift` |

---

## 5. 실행한 명령과 결과

```bash
git -C repos/codenotch log -1 --format='%H %ad %s'
# 414ceaf6173d9988c01ed76d8e924cf0118e3755  2026-09-20 16:46:06 +0700  Codenotch 1.16.0 appcast

git -C repos/codenotch status --porcelain
# (무출력 — clean)

grep -rhoE 'https://[a-zA-Z0-9./_-]+' Sources/Providers/*.swift | sort | uniq -c | sort -rn
# 40개 호스트 — 위 표의 근거
```

archify 산출물 (`deliver` + `visual-check`):

```
system.html   : 9/9 checks, 0 errors / 0 warnings, repository evidence 10건 검증
                spec sha256 59dba423…  artifact sha256 6c6bce83…
visual-check  : 1440x900 / 1600x1000 / 1920x1080 / 2048x1320 (light·dark) 전부 통과
```

**빌드·테스트는 실행하지 않았다.** macOS 전용(`xcodegen` + `xcodebuild`)이고 분석 환경이 Windows다.
따라서 이 문서의 검증 수준 상한은 `코드 확인`이며, 네트워크 동작·실제 파싱 결과는 `미확인`이다.

---

## 6. 남은 질문

- [ ] 각 provider의 응답 파싱이 `LimitWindow`로 정규화되는 구체적 규칙 (Q2로 이관)
- [ ] `WebSessionProvider`가 WKWebView 세션으로 page-local 요청을 재생하는 방식
- [ ] `CredentialCache`가 "키체인 항목의 수정 날짜"로 재읽기를 결정하는 구조 —
      주석은 "수정 날짜는 자격증명과 달리 승인 프롬프트 뒤에 있지 않다"고 말한다. 코드 미확인
- [ ] Codex의 `wham/profiles/me`와 `wham/rate-limit-reset-credits`가 언제 추가로 호출되는가
- [ ] 세션 모니터 9종이 `isBusy`를 판정하는 근거 (Q4)
