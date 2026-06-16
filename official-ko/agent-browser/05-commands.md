---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/05-commands.md
order: 5
title: "Commands"
---

# 명령

## 핵심

```bash
agent-browser open                    # Launch browser (no nav); stays on about:blank
agent-browser open <url>              # Launch + navigate (aliases: goto, navigate)
agent-browser click <sel>             # Click element (--new-tab to open in new tab)
agent-browser dblclick <sel>          # Double-click
agent-browser fill <sel> <text>       # Clear and fill
agent-browser type <sel> <text>       # Type into element
agent-browser press <key>             # Press key (Enter, Tab, Control+a) (alias: key)
agent-browser keyboard type <text>    # Type at current focus (no selector needed)
agent-browser keyboard inserttext <text>  # Insert text without key events
agent-browser keydown <key>           # Hold key down
agent-browser keyup <key>             # Release key
agent-browser hover <sel>             # Hover element
agent-browser focus <sel>             # Focus element
agent-browser select <sel> <val>      # Select dropdown option
agent-browser check <sel>             # Check checkbox
agent-browser uncheck <sel>           # Uncheck checkbox
agent-browser scroll <dir> [px]       # Scroll (up/down/left/right, --selector <sel>)
agent-browser scrollintoview <sel>    # Scroll element into view
agent-browser drag <src> <dst>        # Drag and drop
agent-browser upload <sel> <files>    # Upload files
agent-browser screenshot [path]       # Screenshot (--full for full page)
agent-browser screenshot --annotate   # Annotated screenshot with numbered element labels
agent-browser screenshot --screenshot-dir ./shots    # Save to custom directory
agent-browser screenshot --screenshot-format jpeg --screenshot-quality 80
agent-browser pdf <path>              # Save page as PDF
agent-browser snapshot                # Accessibility tree with refs
agent-browser eval <js>               # Run JavaScript
agent-browser connect <port|url>      # Connect to browser via CDP
agent-browser stream enable [--port <port>]  # Start runtime WebSocket streaming
agent-browser stream status           # Show runtime streaming state and bound port
agent-browser stream disable          # Stop runtime WebSocket streaming
agent-browser close                   # Close browser (aliases: quit, exit)
agent-browser close --all             # Close all active sessions
```

다른 요소가 대상의 클릭 지점을 덮고 있으면 클릭은 dispatch 전에 실패합니다. 오류에는 덮고 있는 요소의 이름이 표시됩니다. 예: `covered by <div#consent-banner>`. 해당 요소를 닫거나 상호작용한 뒤, 새 snapshot을 가져오고 원래 작업을 다시 시도하세요.

Headless Chromium 스크린샷은 일관된 이미지 출력을 위해 네이티브 스크롤바를 숨깁니다. 네이티브 스크롤바를 표시하려면 실행할 때 `--hide-scrollbars false`를 전달하세요.

## 정보 가져오기

```bash
agent-browser get text <sel>          # Get text content
agent-browser get html <sel>          # Get innerHTML
agent-browser get value <sel>         # Get input value
agent-browser get attr <sel> <attr>   # Get attribute
agent-browser get title               # Get page title
agent-browser get url                 # Get current URL
agent-browser get cdp-url             # Get CDP WebSocket URL
agent-browser get count <sel>         # Count matching elements
agent-browser get box <sel>           # Get bounding box
agent-browser get styles <sel>        # Get computed styles
```

## 상태 확인

```bash
agent-browser is visible <sel>        # Check if visible
agent-browser is enabled <sel>        # Check if enabled
agent-browser is checked <sel>        # Check if checked
```

## 요소 찾기

동작(`click`, `fill`, `type`, `hover`, `focus`, `check`, `uncheck`, `text`)과 함께 사용하는 semantic locator입니다.

```bash
agent-browser find role <role> <action> [value]
agent-browser find text <text> <action>
agent-browser find label <label> <action> [value]
agent-browser find placeholder <ph> <action> [value]
agent-browser find alt <text> <action>
agent-browser find title <text> <action>
agent-browser find testid <id> <action> [value]
agent-browser find first <sel> <action> [value]
agent-browser find last <sel> <action> [value]
agent-browser find nth <n> <sel> <action> [value]
```

옵션:

- `--name <name>`: accessible name으로 role 필터링
- `--exact`: 정확한 텍스트 일치를 요구

예시:

```bash
agent-browser find role button click --name "Submit"
agent-browser find label "Email" fill "test@test.com"
agent-browser find alt "Logo" click
agent-browser find first ".item" click
agent-browser find last ".item" text
agent-browser find nth 2 ".card" hover
```

## 대기

```bash
agent-browser wait <selector>         # Wait for element
agent-browser wait <ms>               # Wait for time
agent-browser wait --text "Welcome"   # Wait for text (substring match)
agent-browser wait --url "**/dash"    # Wait for URL pattern
agent-browser wait --load networkidle # Wait for load state
agent-browser wait --fn "condition"   # Wait for JS condition
agent-browser wait --download [path]  # Wait for download
agent-browser wait --fn "!document.body.innerText.includes('Loading...')"  # Wait for text to disappear
agent-browser wait "#spinner" --state hidden           # Wait for element to disappear
```

## 다운로드

```bash
agent-browser download <sel> <path>   # Click element to trigger download
agent-browser wait --download [path]  # Wait for any download to complete
```

기본 다운로드 디렉터리를 설정하려면 `--download-path <dir>`(또는 `AGENT_BROWSER_DOWNLOAD_PATH` 환경 변수)를 사용하세요. 설정하지 않으면 다운로드는 브라우저가 닫힐 때 삭제되는 임시 디렉터리로 저장됩니다.

업로드, 다운로드, 로컬 파일, 스크린샷, PDF, 클립보드 워크플로는 [Files & Clipboard](/files)를 참조하세요.

## 마우스

```bash
agent-browser mouse move <x> <y>      # Move mouse
agent-browser mouse down [button]     # Press button
agent-browser mouse up [button]       # Release button
agent-browser mouse wheel <dy> [dx]   # Scroll wheel
```

## 클립보드

```bash
agent-browser clipboard read                      # Read text from clipboard
agent-browser clipboard write "Hello, World!"     # Write text to clipboard
agent-browser clipboard copy                      # Copy current selection (Ctrl+C)
agent-browser clipboard paste                     # Paste from clipboard (Ctrl+V)
```

클립보드, 업로드, 다운로드, 로컬 파일, 스크린샷, PDF 워크플로는 [Files & Clipboard](/files)를 참조하세요.

## 설정

```bash
agent-browser set viewport <w> <h> [scale]  # Set viewport size (scale for retina, e.g. 2)
agent-browser set device <name>       # Emulate device ("iPhone 14")
agent-browser set geo <lat> <lng>     # Set geolocation
agent-browser set offline [on|off]    # Toggle offline mode
agent-browser set headers <json>      # Extra HTTP headers
agent-browser set credentials <u> <p> # HTTP basic auth
agent-browser set media [dark|light]  # Emulate color scheme (persists for session)
```

모든 명령에서 지속되는 dark/light 모드에는 `--color-scheme`을 사용하세요.

```bash
agent-browser --color-scheme dark open https://example.com
```

## Cookies & storage

```bash
agent-browser cookies                 # Get all cookies
agent-browser cookies set <name> <val> # Set cookie
agent-browser cookies clear           # Clear cookies

agent-browser storage local           # Get all localStorage
agent-browser storage local <key>     # Get specific key
agent-browser storage local set <k> <v>  # Set value
agent-browser storage local clear     # Clear all

agent-browser storage session         # Same for sessionStorage
```

## 네트워크

```bash
agent-browser network route <url>              # Intercept requests
agent-browser network route <url> --abort      # Block requests
agent-browser network route <url> --body <json>  # Mock response
agent-browser network route '*' --abort --resource-type script  # Block scripts only
agent-browser network unroute [url]            # Remove routes
agent-browser network requests                 # View tracked requests
agent-browser network requests --clear         # Clear request log
agent-browser network requests --filter <pat>  # Filter by URL pattern
agent-browser network requests --type xhr,fetch  # Filter by resource type
agent-browser network requests --method POST   # Filter by HTTP method
agent-browser network requests --status 2xx    # Filter by status (200, 2xx, 400-499)
agent-browser network request <requestId>      # View full request/response detail
agent-browser network har start                # Start HAR recording
agent-browser network har stop [output.har]    # Stop and save HAR (temp path if omitted)
```

탐색 전 라우팅, 요청 필터, HAR 내보내기, SSR/no-JavaScript 디버깅은 [Network](/network)를 참조하세요.

## Tabs & frames

```bash
agent-browser tab                              # List tabs (each row shows tabId and label)
agent-browser tab new [url]                    # New tab
agent-browser tab new --label docs [url]       # New tab with a user-assigned label
agent-browser tab <t<N>|label>                 # Switch to a tab by id or label
agent-browser tab close [t<N>|label]           # Close a tab (defaults to active)
agent-browser window new                       # Open new browser window
agent-browser frame <sel>                      # Switch to iframe by CSS selector
agent-browser frame @e3                        # Switch to iframe by element ref
agent-browser frame main                       # Back to main frame
```

### 안정적인 tab id와 label

Tab id는 `t1`, `t2`, `t3` 형식의 안정적인 문자열입니다. 세션 안에서 절대 재사용되지 않으므로, 다른 탭이 열리거나 닫혀도 `t2`는 계속 같은 탭을 가리킵니다. `t` 접두사는 `@e1` 요소 ref 규칙을 반영하며 위치 기반 정수와 서로 바꿔 쓸 수 없습니다. `agent-browser tab 2`는 안내 메시지와 함께 오류를 발생시키므로 `t2`를 사용하세요.

탭 생성 시 기억하기 쉬운 label(`docs`, `app`, `admin`)을 지정하고 id를 받는 모든 곳에서 사용할 수도 있습니다.

```bash
agent-browser tab new --label docs https://docs.example.com
agent-browser tab docs          # switch to the docs tab
agent-browser snapshot          # populate refs for docs
agent-browser click @e3         # click uses docs's refs
agent-browser tab close docs    # close by label
```

Label은 자동 생성되지 않으며 탐색 시 다시 작성되지 않습니다. 탭 이름을 `docs`로 지정한 에이전트는 탭이 닫힐 때까지 그 이름을 유지합니다. Label은 세션 안에서 고유합니다. 기존 label로 두 번째 탭을 만들면 오류가 발생합니다.

Refs(`@e1` 등)는 snapshot이 실행될 때 활성화되어 있던 탭으로 범위가 제한되므로, 먼저 탭을 전환한 뒤 snapshot을 가져오고 상호작용하세요.

```bash
agent-browser tab docs          # switch first
agent-browser snapshot          # refs for docs
agent-browser click @e3         # uses docs's refs
```

### Iframe 지원

Iframe은 snapshot 중 자동으로 감지됩니다. `Iframe` 노드는 해석되며 해당 콘텐츠는 snapshot 출력에서 iframe 요소 아래에 인라인으로 포함됩니다. iframe 내부 요소에 할당된 ref는 frame 컨텍스트를 포함하므로, 수동으로 frame을 전환하지 않아도 `click`, `fill` 및 기타 상호작용이 작동합니다.

```bash
agent-browser snapshot -i
# @e3 [Iframe] "payment-frame"
#   @e4 [input] "Card number"
#   @e5 [button] "Pay"

# Interact directly using refs — no frame switch needed
agent-browser fill @e4 "4111111111111111"
agent-browser click @e5

# Or switch frame context for scoped snapshots
agent-browser frame @e3
agent-browser snapshot -i             # Only elements inside that iframe
agent-browser frame main              # Return to main frame
```

`frame` 명령은 요소 ref(`@e3`), CSS selector(`"#my-iframe"`), 또는 frame 이름/URL을 받습니다.

## Dialogs

```bash
agent-browser dialog accept [text]    # Accept dialog (with optional prompt text)
agent-browser dialog dismiss          # Dismiss dialog
agent-browser dialog status           # Check if a dialog is currently open
```

기본적으로 `alert`와 `beforeunload` dialog는 에이전트를 차단하지 않도록 자동으로 수락됩니다. `confirm`과 `prompt` dialog는 여전히 명시적으로 처리해야 합니다. 자동 처리를 비활성화하려면 `--no-auto-dialog`(또는 `AGENT_BROWSER_NO_AUTO_DIALOG=1`)를 사용하세요.

JavaScript dialog(`alert`, `confirm`, `prompt`)가 대기 중이면 모든 명령 응답에는 dialog 유형과 메시지가 포함된 `warning` 필드가 포함됩니다.

## Streaming

```bash
agent-browser stream enable           # Start runtime WebSocket streaming on an auto-selected port
agent-browser stream enable --port 9223  # Bind a specific localhost port
agent-browser stream status           # Show enabled state, port, browser connection, screencasting
agent-browser stream disable          # Stop runtime streaming and remove the .stream metadata file
```

Streaming은 모든 세션에서 자동으로 활성화됩니다. 상태를 확인하거나, 특정 포트에서 다시 활성화하거나, streaming을 비활성화하려면 이 명령들을 사용하세요.

Streaming은 파일 기반 녹화와 별개입니다. 저장된 WebM artifact가 필요할 때는 [Video Recording](/recording)을 사용하세요.

## Debug

```bash
agent-browser trace start             # Start trace
agent-browser trace stop [path]       # Stop and save trace
agent-browser profiler start          # Start Chrome DevTools profiling
agent-browser profiler stop [path]    # Stop and save profile (.json)
agent-browser record start <path>     # Start video recording (WebM)
agent-browser record stop             # Stop and save video
agent-browser record restart <path>   # Stop current and start new recording
agent-browser console                 # View console messages
agent-browser console --json          # JSON output with raw CDP args
agent-browser console --clear         # Clear console log
agent-browser errors                  # View page errors
agent-browser errors --clear          # Clear error log
agent-browser highlight <sel>         # Highlight element
agent-browser inspect                 # Open Chrome DevTools for the active page
```

콘솔, 오류, dialog, trace, highlight, DevTools 워크플로는 [Debugging](/debugging)을 참조하세요. `record` 워크플로는 [Video Recording](/recording)을, 성능 profile은 [Profiler](/profiler)를 참조하세요.

## Auth vault

```bash
agent-browser auth save <name> [opts]    # Save auth profile
agent-browser auth login <name>          # Login using saved credentials
agent-browser auth login <name> --credential-provider <plugin> [--item <ref>] [--url <url>]
                                          # Resolve credentials from plugin
agent-browser auth login <name> --username-selector <s> --password-selector <s> [--submit-selector <s>]
                                          # Override selectors for one login
agent-browser auth list                  # List saved profiles (names and URLs only)
agent-browser auth show <name>           # Show profile metadata (no passwords)
agent-browser auth delete <name>         # Delete a saved profile
agent-browser plugin add <ref>           # Add a plugin from npm or GitHub
agent-browser plugin list                # List configured plugins
agent-browser plugin show <name>         # Show one configured plugin
agent-browser plugin run <name> <type> --payload <json>
                                          # Run an arbitrary plugin request
```

저장 옵션:

- `--url <url>`: 로그인 페이지 URL(필수)
- `--username <user>`: 사용자 이름(필수)
- `--password <pass>`: 비밀번호(`--password-stdin`이 없으면 필수)
- `--password-stdin`: stdin에서 비밀번호 읽기(셸 히스토리 노출을 피하기 위해 권장)
- `--username-selector <sel>`: 사용자 이름 필드용 사용자 지정 CSS selector
- `--password-selector <sel>`: 비밀번호 필드용 사용자 지정 CSS selector
- `--submit-selector <sel>`: 제출 버튼용 사용자 지정 CSS selector

`auth login`은 `load`로 탐색한 다음 상호작용하기 전에 사용자 이름/비밀번호/제출 selector가 나타날 때까지 기다립니다. 이렇게 하면 초기 페이지 로드 후 필드가 렌더링되는 SPA 로그인 페이지에서 신뢰성이 향상됩니다.

Plugin 로그인 옵션:

- `--credential-provider <plugin>`: 구성된 plugin에서 자격 증명 해석
- `--item <ref>`: provider별 vault item 참조
- `--url <url>`: 로그인 URL 재정의
- `--username-selector <sel>`: 이 로그인에 대한 selector 재정의
- `--password-selector <sel>`: 이 로그인에 대한 selector 재정의
- `--submit-selector <sel>`: 이 로그인에 대한 selector 재정의

Credential provider plugin은 `agent-browser.plugin.v1` stdio JSON protocol을 통해 out-of-process로 실행됩니다. 이 plugin은 한 번의 로그인을 위해 자격 증명을 데몬에 반환하며 agent-browser는 해당 자격 증명을 로컬에 저장하지 않습니다.

다른 plugin 기능도 같은 protocol을 사용합니다.

- `browser.provider`: `--provider <name>`과 함께 plugin을 사용해 CDP WebSocket URL 반환
- `launch.mutate`: Chrome 시작 전에 로컬 launch args, extensions, init scripts 추가
- `command.run`: `agent-browser plugin run`을 통해 임의의 namespaced 요청 실행

`plugin run`은 `command.run` 및 사용자 지정 기능을 위한 것입니다. 핵심 기능과 protocol 요청 유형은 전용 명령 경로를 사용합니다.

```bash
echo "pass" | agent-browser auth save github --url https://github.com/login --username user --password-stdin
agent-browser auth login github
agent-browser plugin add agent-browser-plugin-vault --name vault
agent-browser auth login my-app --credential-provider vault --item "My App"
agent-browser --provider cloud-browser open https://example.com
agent-browser plugin run captcha captcha.solve --payload '{"siteKey":"...","url":"https://example.com"}'
agent-browser auth list
```

## Confirmation

`--confirm-actions`가 설정되면 특정 작업 범주는 즉시 실행되지 않고 `confirmation_required` 응답을 반환합니다. 작업을 승인하거나 거부하려면 `confirm` 또는 `deny`를 사용하세요.

```bash
agent-browser confirm <confirmation-id>  # Approve a pending action
agent-browser deny <confirmation-id>     # Deny a pending action
```

대기 중인 confirmation은 60초 후 자동으로 deny됩니다.

```bash
agent-browser --confirm-actions eval,download eval "document.title"
# Returns confirmation_required with ID
agent-browser confirm c_8f3a1234
```

## 상태 관리

```bash
agent-browser state save <path>       # Save auth state to file
agent-browser state load <path>       # Load auth state from file
agent-browser state list              # List saved state files
agent-browser state show <file>       # Show state summary
agent-browser state rename <old> <new> # Rename state file
agent-browser state clear [name]      # Clear states for session name
agent-browser state clear --all       # Clear all saved states
agent-browser state clean --older-than <days>  # Delete old states
```

## 세션

```bash
agent-browser session                 # Show current session name
agent-browser session list            # List active sessions
```

## Chrome profiles

```bash
agent-browser profiles               # List available Chrome profiles
agent-browser profiles --json        # List profiles as JSON
agent-browser --profile Default open https://gmail.com  # Reuse a profile's login state
```

## Dashboard

```bash
agent-browser dashboard [start]       # Start the dashboard server (default port: 4848)
agent-browser dashboard start --port <n>  # Start on a specific port
agent-browser dashboard stop          # Stop the dashboard server
```

`http://localhost:4848` 또는 `https://dashboard.agent-browser.localhost` 같은 프록시/포워딩된 dashboard URL을 통해 dashboard를 여세요. 브라우저는 dashboard origin에 머무릅니다. 세션별 탭, 상태, stream 트래픽은 내부적으로 프록시되므로 세션 포트를 노출할 필요가 없습니다.

## Doctor

설치 상태를 진단하고, 오래된 데몬 파일을 자동 정리하며, 선택적으로 일반적인 문제를 복구합니다.

```bash
agent-browser doctor                     # Full diagnosis (env, Chrome, daemons, config, providers, network, launch test)
agent-browser doctor --offline --quick   # Local-only, fastest
agent-browser doctor --fix               # Also run destructive repairs (reinstall Chrome, purge old state, ...)
agent-browser doctor --json              # Structured JSON output for agents
```

모든 검사를 통과하면 종료 코드는 `0`입니다(경고는 괜찮습니다). 실패한 검사가 있으면 `1`입니다. 전체 검사 목록은 [Installation page](/installation#doctor)를 참조하세요.

## Chat

자연어를 사용해 AI로 브라우저를 제어합니다. `chat` 명령은 지시를 agent-browser 명령으로 변환하고, 이를 실행한 뒤 AI 응답을 스트리밍합니다. `AI_GATEWAY_API_KEY`가 설정되어 있어야 합니다.

```bash
agent-browser chat "open google.com and search for cats"     # Single-shot instruction
agent-browser chat                                           # Interactive REPL (type quit to exit)
echo "summarize this page" | agent-browser chat              # Piped input
agent-browser -q chat "summarize this page"                  # Quiet: text only, no tool calls shown
agent-browser -v chat "fill in the login form"               # Verbose: show commands and their output
agent-browser --model openai/gpt-4o chat "take a screenshot" # Override the default AI model
agent-browser --json chat "open example.com"                 # Structured JSON output
```

Chat 전용 옵션:

```bash
--model <name>           # AI model (or AI_GATEWAY_MODEL env, default: anthropic/claude-sonnet-4.6)
-v, --verbose            # Show tool commands and their raw output
-q, --quiet              # Show only the AI text response (hide tool calls)
```

## 탐색

```bash
agent-browser back                    # Go back
agent-browser forward                 # Go forward
agent-browser reload                  # Reload page
agent-browser pushstate <url>         # SPA client-side nav; auto-detects window.next.router.push,
                                      # falls back to history.pushState + popstate
```

## 탐색 전 설정

일부 흐름에서는 첫 탐색 *전에* routes, cookies 또는 init scripts를 구성해야 합니다(SSR 디버그, 보호된 origin의 인증 등). URL 없이 `open`을 실행하면 브라우저를 실행하지만 `about:blank`에 머물러 상태를 준비할 수 있는 여지를 남깁니다. `batch`는 이를 하나의 CLI 호출로 만듭니다.

```bash
agent-browser batch \
  '["open"]' \
  '["network","route","*","--abort","--resource-type","script"]' \
  '["cookies","set","--curl","cookies.curl","--domain","localhost"]' \
  '["navigate","http://localhost:3000/target"]'
```

## React / Web Vitals

React 명령은 실행 시 `--enable react-devtools`가 필요합니다(페이지 JS가 실행되기 전에 React DevTools hook을 설치합니다). `vitals`와 `pushstate`는 모든 사이트에서 작동합니다.

```bash
agent-browser open --enable react-devtools <url>   # Launch with React hook installed
agent-browser react tree                           # Full component tree
agent-browser react inspect <fiberId>              # Inspect one component
agent-browser react renders start                  # Begin fiber render recording
agent-browser react renders stop [--json]          # Stop + print profile
agent-browser react suspense [--only-dynamic] [--json]  # Suspense boundaries + classifier
                                                         # --only-dynamic hides the "static" list
agent-browser vitals [url] [--json]                # LCP/CLS/TTFB/FCP/INP + hydration
```

모든 React 앱(Next.js, Remix, Vite+React, CRA, TanStack Start, React Native Web 등)에서 작동합니다. `vitals`와 `pushstate`는 프레임워크에 독립적입니다.

전체 명령 세부 정보와 예시는 [React & Web Vitals](/react)를 참조하세요.

## Init scripts

```bash
agent-browser open --init-script <path>           # Register before first navigation (repeatable)
agent-browser addinitscript <js>                  # Register at runtime (returns identifier)
agent-browser removeinitscript <identifier>       # Remove a previously registered init script
```

실행 시점 scripts, runtime scripts, 내장 React DevTools, extensions는 [Init Scripts & Extensions](/init-scripts)를 참조하세요.

## 전역 옵션

```bash
--session <name>         # Isolated browser session
--session-name <name>    # Auto-save/restore session state (cookies, localStorage)
--profile <path>         # Persistent browser profile directory
--state <path>           # Load storage state from JSON file
--headers <json>         # HTTP headers scoped to URL's origin
--executable-path <path> # Custom browser executable
--extension <path>       # Load browser extension (repeatable)
--init-script <path>     # Register a page init script before first navigation (repeatable)
--enable <feature>       # Built-in init scripts: react-devtools (repeatable or comma-list)
--args <args>            # Browser launch args (comma separated)
--user-agent <ua>        # Custom User-Agent string
--proxy <url>            # Proxy server URL
--proxy-bypass <hosts>   # Hosts to bypass proxy
--ignore-https-errors    # Ignore HTTPS certificate errors
--allow-file-access      # Allow file:// URLs to access local files (Chromium only)
--hide-scrollbars <bool> # Hide native scrollbars in headless Chromium screenshots
-p, --provider <name>    # Browser provider or configured provider plugin
--device <name>          # iOS device name (e.g., "iPhone 15 Pro")
--json                   # JSON output (for scripts)
--annotate               # Annotated screenshot with numbered element labels
--screenshot-dir <path>   # Default screenshot output directory (or AGENT_BROWSER_SCREENSHOT_DIR)
--screenshot-quality <n>  # JPEG quality 0-100 (or AGENT_BROWSER_SCREENSHOT_QUALITY)
--screenshot-format <fmt> # Format: png (default), jpeg (or AGENT_BROWSER_SCREENSHOT_FORMAT)
--headed                 # Show browser window (not headless)
--cdp <port|url>         # Connect via Chrome DevTools Protocol (port or WebSocket URL)
--auto-connect           # Auto-discover and connect to running Chrome
--color-scheme <scheme>  # Color scheme: dark, light, no-preference
--download-path <path>   # Default download directory
--content-boundaries     # Wrap page output in boundary markers for LLM safety
--max-output <chars>     # Truncate page output to N characters
--allowed-domains <list> # Comma-separated allowed domain patterns
--action-policy <path>   # Path to action policy JSON file
--confirm-actions <list> # Action categories requiring confirmation
--confirm-interactive    # Interactive confirmation prompts (auto-denies if stdin is not a TTY)
--engine <name>          # Browser engine: chrome (default), lightpanda
--idle-timeout <time>    # Auto-shutdown daemon after inactivity (10s, 3m, 1h, or ms)
--no-auto-dialog         # Disable auto-accept for alert and beforeunload dialogs
--model <name>           # AI model for chat (or AI_GATEWAY_MODEL env)
-v, --verbose            # Show tool commands and their raw output (chat)
-q, --quiet              # Show only AI text responses (chat)
--config <path>          # Use a custom config file
--debug                  # Debug output
```

구성 파일과 환경 변수는 [Configuration](/configuration)을 참조하세요. 프록시 서버, 우회, 자격 증명 설정은 [Proxy](/proxy)를 참조하세요.

## Batch 실행

단일 호출에서 여러 명령을 실행합니다. 명령은 따옴표로 감싼 인자로 전달하거나 stdin을 통해 JSON으로 pipe할 수 있습니다.

```bash
# Argument mode: each quoted argument is a full command
agent-browser batch "open https://example.com" "snapshot -i" "screenshot"

# With --bail to stop on first error
agent-browser batch --bail "open https://example.com" "click @e1" "screenshot"

# Stdin mode: pipe commands as JSON
echo '[
  ["open", "https://example.com"],
  ["snapshot", "-i"],
  ["click", "@e1"],
  ["screenshot", "result.png"]
]' | agent-browser batch --json
```

<table>
  <thead>
    <tr><th>옵션</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>--bail</code></td><td>첫 번째 오류에서 중지(기본값: 모든 명령 계속 실행)</td></tr>
    <tr><td><code>--json</code></td><td>결과를 JSON 배열로 출력</td></tr>
  </tbody>
</table>

## 명령 체이닝

단일 셸 호출에서 `&&`로 명령을 체이닝합니다. 브라우저는 백그라운드 데몬을 통해 유지되므로 체이닝이 자연스럽게 작동하며 별도 호출보다 효율적입니다.

```bash
agent-browser open example.com && agent-browser wait --load networkidle && agent-browser snapshot -i
agent-browser fill @e1 "user@example.com" && agent-browser fill @e2 "pass" && agent-browser click @e3
agent-browser open example.com && agent-browser wait --load networkidle && agent-browser screenshot page.png
```

중간 출력을 읽을 필요가 없을 때는 `&&`를 사용하세요. 먼저 출력을 파싱해야 할 때는 명령을 따로 실행하세요(예: ref를 찾기 위해 snapshot을 가져온 뒤 해당 ref와 상호작용).

## 로컬 파일

`file://` URL을 사용해 로컬 파일(PDF, HTML)을 엽니다.

```bash
agent-browser --allow-file-access open file:///path/to/document.pdf
agent-browser --allow-file-access open file:///path/to/page.html
agent-browser screenshot output.png
```

`--allow-file-access` 플래그는 JavaScript가 다른 로컬 파일에 접근할 수 있게 합니다. Chromium 전용입니다.

로컬 파일, 업로드, 다운로드, 스크린샷, PDF, 클립보드 워크플로는 [Files & Clipboard](/files)를 참조하세요.
