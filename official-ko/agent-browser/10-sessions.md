---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/10-sessions.md
order: 10
title: "Sessions"
---

# Sessions

여러 개의 격리된 브라우저 인스턴스를 실행합니다.

```bash
# Different sessions
agent-browser --session agent1 open site-a.com
agent-browser --session agent2 open site-b.com

# Or via environment variable
AGENT_BROWSER_SESSION=agent1 agent-browser click "#btn"

# List active sessions
agent-browser session list
# Output:
# Active sessions:
# -> default
#    agent1

# Show current session
agent-browser session
```

## 세션 격리

각 세션은 자체적으로 다음을 가집니다.

- 브라우저 인스턴스
- Cookies 및 storage
- 탐색 기록
- 인증 상태

## Chrome profile 재사용

기존 로그인 상태를 재사용하는 가장 간단한 방법은 Chrome profile 이름을 `--profile`에 전달하는 것입니다. agent-browser는 profile을 임시 디렉터리로 복사한 뒤(read-only snapshot), 기존 cookies와 sessions가 있는 상태로 Chrome을 실행합니다.

```bash
# List available Chrome profiles
agent-browser profiles

# Reuse your default Chrome profile's login state
agent-browser --profile Default open https://gmail.com

# Use a named profile (by display name or directory name)
agent-browser --profile "Work" open https://app.example.com

# Or via environment variable
AGENT_BROWSER_PROFILE=Default agent-browser open https://gmail.com
```

<table>
  <thead>
    <tr><th>세부 정보</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td>지원 브라우저</td><td>Chrome, Chrome Canary, Chromium, Brave</td></tr>
    <tr><td>복사되는 항목</td><td>Cookies, local storage, extensions state(속도를 위해 cache dirs 제외)</td></tr>
    <tr><td>원본 profile</td><td>절대 수정되지 않음(read-only snapshot)</td></tr>
    <tr><td>정리</td><td>브라우저가 닫히면 임시 복사본 삭제</td></tr>
    <tr><td>Windows 참고</td><td>Chrome이 실행 중이면 <code>--profile &lt;name&gt;</code>을 사용하기 전에 Chrome을 닫으세요</td></tr>
  </tbody>
</table>

## 지속 profile

브라우저 재시작 사이에 상태를 유지하는 사용자 지정 profile 디렉터리를 사용하려면 `--profile`에 경로를 전달하세요.

```bash
# Use a persistent profile directory
agent-browser --profile ~/.myapp-profile open myapp.com

# Login once, then reuse the authenticated session
agent-browser --profile ~/.myapp-profile open myapp.com/dashboard

# Or via environment variable
AGENT_BROWSER_PROFILE=~/.myapp-profile agent-browser open myapp.com
```

profile 디렉터리는 다음을 저장합니다.

- Cookies 및 localStorage
- IndexedDB 데이터
- Service workers
- Browser cache
- Login sessions

## 브라우저에서 auth 가져오기

이미 Chrome에서 사이트에 로그인되어 있다면 해당 auth state를 가져와 agent-browser에서 재사용할 수 있습니다. 로그인 flow, OAuth, SSO 또는 2FA를 우회하는 가장 빠른 방법입니다.

**Step 1:** 원격 디버깅으로 Chrome을 시작합니다.

```bash
# macOS
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222
```

이 Chrome 창에서 대상 사이트에 로그인하세요.

`--remote-debugging-port`는 localhost에서 전체 브라우저 제어를 노출합니다. 모든 로컬 프로세스가 연결할 수 있습니다. 신뢰할 수 있는 머신에서만 사용하고, 작업이 끝나면 Chrome을 닫으세요.

**Step 2:** 연결하고 인증된 상태를 저장합니다.

```bash
agent-browser --auto-connect state save ./my-auth.json
```

**Step 3:** 이후 세션에서 저장된 auth를 사용합니다.

```bash
# Load auth at launch
agent-browser --state ./my-auth.json open https://app.example.com/dashboard

# Or load into an existing session
agent-browser state load ./my-auth.json
agent-browser open https://app.example.com/dashboard
```

가져온 auth가 재시작 사이에 자동으로 유지되도록 `--session-name`과 결합하세요.

```bash
agent-browser --session-name myapp state load ./my-auth.json
# From now on, state auto-saves/restores for "myapp"
```

State files에는 session tokens가 plaintext로 포함됩니다. `.gitignore`에 추가하고 더 이상 필요하지 않으면 삭제하세요. 저장 시 암호화는 아래 [State encryption](#state-encryption)을 참조하세요.

## 세션 지속성

브라우저 재시작 사이에 cookies와 localStorage를 자동으로 저장하고 복원하려면 `--session-name`을 사용하세요.

```bash
# Auto-save/load state for "twitter" session
agent-browser --session-name twitter open twitter.com

# Login once, then state persists automatically
agent-browser --session-name twitter click "#login"

# Or via environment variable
agent-browser open twitter.com
```

State files는 `~/.agent-browser/sessions/`에 저장되며 daemon 시작 시 자동으로 로드됩니다.

### Session name 규칙

Session name은 영숫자, hyphen, underscore만 포함해야 합니다.

```bash
# Valid session names
agent-browser --session-name my-project open example.com
agent-browser --session-name test_session_v2 open example.com

# Invalid (will be rejected)
agent-browser --session-name "../bad" open example.com    # path traversal
agent-browser --session-name "my session" open example.com # spaces
agent-browser --session-name "foo/bar" open example.com    # slashes
```

## State encryption

AES-256-GCM을 사용해 저장된 state files(cookies, localStorage)를 암호화합니다.

```bash
# Generate a 256-bit key (64 hex characters)
openssl rand -hex 32

# Set the encryption key

# State files are now encrypted automatically
agent-browser --session-name secure-session open example.com

# List states shows encryption status
agent-browser state list
```

## State auto-expiration

누적을 방지하기 위해 오래된 state files를 자동으로 삭제합니다.

```bash
# Set expiration (default: 30 days)

# Manually clean old states
agent-browser state clean --older-than 7
```

## State management 명령

```bash
# List all saved states
agent-browser state list

# Show state summary (cookies, origins, domains)
agent-browser state show my-session-default.json

# Rename a state file
agent-browser state rename old-name new-name

# Clear states for a specific session name
agent-browser state clear my-session

# Clear all saved states
agent-browser state clear --all

# Manual save/load (for custom paths)
agent-browser state save ./backup.json
agent-browser state load ./backup.json
```

## 인증된 세션

특정 origin에 HTTP headers를 설정하려면 `--headers`를 사용하세요.

```bash
# Headers scoped to api.example.com only
agent-browser open api.example.com --headers '{"Authorization": "Bearer <token>"}'

# Requests to api.example.com include the auth header
agent-browser snapshot -i --json
agent-browser click @e2

# Navigate to another domain - headers NOT sent
agent-browser open other-site.com
```

유용한 용도:

- **로그인 flow 건너뛰기** - headers로 인증
- **사용자 전환** - 세션별 다른 auth tokens
- **API 테스트** - 보호된 endpoints 접근
- **보안** - Headers는 origin으로 범위가 제한되며 유출되지 않음

## 여러 origins

```bash
agent-browser open api.example.com --headers '{"Authorization": "Bearer token1"}'
agent-browser open api.acme.com --headers '{"Authorization": "Bearer token2"}'
```

## 전역 headers

모든 domains에 headers를 적용하려면 다음을 사용합니다.

```bash
agent-browser set headers '{"X-Custom-Header": "value"}'
```

## 환경 변수

<table>
  <thead>
    <tr><th>변수</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>AGENT_BROWSER_SESSION</code></td><td>브라우저 session ID(기본값: "default")</td></tr>
    <tr><td><code>AGENT_BROWSER_SESSION_NAME</code></td><td>state 자동 저장/로드 지속성 이름</td></tr>
    <tr><td><code>AGENT_BROWSER_ENCRYPTION_KEY</code></td><td>AES-256-GCM 암호화를 위한 64자 hex 키</td></tr>
    <tr><td><code>AGENT_BROWSER_STATE_EXPIRE_DAYS</code></td><td>N일보다 오래된 states 자동 삭제(기본값: 30)</td></tr>
  </tbody>
</table>
