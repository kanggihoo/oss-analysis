---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/14-cdp-mode.md
order: 14
title: "CDP Mode"
---

# CDP Mode

Chrome DevTools Protocol을 통해 기존 브라우저에 연결합니다.

```bash
# Start Chrome with: google-chrome --remote-debugging-port=9222

# Connect once, then run commands without --cdp
agent-browser connect 9222
agent-browser snapshot
agent-browser tab
agent-browser close

# Or pass --cdp on each command
agent-browser --cdp 9222 snapshot
```

## Remote WebSocket URLs

WebSocket URL을 통해 원격 브라우저 서비스에 연결합니다.

```bash
# Connect to remote browser service
agent-browser --cdp "wss://browser-service.com/cdp?token=..." snapshot

# Works with any CDP-compatible service
agent-browser --cdp "ws://localhost:9222/devtools/browser/abc123" open example.com
```

`--cdp` flag는 다음 중 하나를 받습니다.

- `http://localhost:{port}`를 통한 로컬 연결용 port number(예: `9222`)
- 원격 브라우저 서비스용 전체 WebSocket URL(예: `wss://...` 또는 `ws://...`)

## Auto-Connect

port를 지정하지 않고 실행 중인 Chrome 인스턴스를 자동으로 찾아 연결하려면 `--auto-connect`를 사용하세요.

```bash
# Auto-discover running Chrome with remote debugging
agent-browser --auto-connect open example.com
agent-browser --auto-connect snapshot

# Or via environment variable
AGENT_BROWSER_AUTO_CONNECT=1 agent-browser snapshot
```

Auto-connect는 다음 방식으로 Chrome을 찾습니다.

1. 기본 user data directory에서 Chrome의 `DevToolsActivePort` 파일 읽기
2. 일반적인 debugging ports(9222, 9229) probing으로 fallback
3. HTTP 기반 discovery(`/json/version`, `/json/list`)가 실패하면 direct WebSocket connection으로 fallback

다음과 같은 경우 유용합니다.

- Chrome 144+에서 `chrome://inspect/#remote-debugging`을 통해 remote debugging이 활성화된 경우(동적 port 사용)
- 기존 브라우저에 zero-configuration으로 연결하고 싶은 경우
- Chrome이 사용하는 port를 추적하고 싶지 않은 경우

## Color scheme

CDP로 연결할 때 지속적인 preference를 설정하려면 `--color-scheme`을 사용하세요.

```bash
agent-browser --cdp 9222 --color-scheme dark open https://example.com
agent-browser --cdp 9222 snapshot  # stays in dark mode
```

또는 config나 환경 변수를 통해 전역으로 설정하세요.

```bash
AGENT_BROWSER_COLOR_SCHEME=dark agent-browser --cdp 9222 open https://example.com
```

## 사용 사례

다음을 제어할 수 있습니다.

- Electron apps
- remote debugging이 활성화된 Chrome/Chromium
- WebView2 applications
- 원격 브라우저 서비스(WebSocket URL을 통해)
- CDP endpoint를 노출하는 모든 브라우저

## 전역 옵션

<table>
  <thead>
    <tr><th>옵션</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>--session &lt;name&gt;</code></td><td>격리된 session 사용</td></tr>
    <tr><td><code>--profile &lt;path&gt;</code></td><td>지속 browser profile directory</td></tr>
    <tr><td><code>-p &lt;provider&gt;</code></td><td>Browser provider(<code>browserbase</code>, <code>browseruse</code>, <code>kernel</code>, <code>browserless</code>, <code>agentcore</code> 또는 구성된 <code>browser.provider</code> plugin)</td></tr>
    <tr><td><code>--headers &lt;json&gt;</code></td><td>origin으로 범위가 제한된 HTTP headers</td></tr>
    <tr><td><code>--executable-path</code></td><td>사용자 지정 browser executable</td></tr>
    <tr><td><code>--args &lt;args&gt;</code></td><td>Browser launch args(쉼표로 구분)</td></tr>
    <tr><td><code>--user-agent &lt;ua&gt;</code></td><td>사용자 지정 User-Agent string</td></tr>
    <tr><td><code>--proxy &lt;url&gt;</code></td><td>Proxy server URL</td></tr>
    <tr><td><code>--proxy-bypass &lt;hosts&gt;</code></td><td>proxy를 우회할 hosts</td></tr>
    <tr><td><code>--json</code></td><td>scripts용 JSON output</td></tr>
    <tr><td><code>--name, -n</code></td><td>Locator name filter</td></tr>
    <tr><td><code>--exact</code></td><td>정확한 text match</td></tr>
    <tr><td><code>--headed</code></td><td>브라우저 창 표시</td></tr>
    <tr><td><code>{"--cdp <port|url>"}</code></td><td>CDP connection(port 또는 WebSocket URL)</td></tr>
    <tr><td><code>--auto-connect</code></td><td>실행 중인 Chrome을 자동으로 찾고 연결</td></tr>
    <tr><td><code>--color-scheme &lt;scheme&gt;</code></td><td>지속 color scheme(<code>dark</code>, <code>light</code>, <code>no-preference</code>)</td></tr>
    <tr><td><code>--debug</code></td><td>Debug output</td></tr>
  </tbody>
</table>

## Cloud providers

로컬 브라우저를 실행하는 대신 cloud browser provider 또는 구성된 `browser.provider` plugin에 연결하려면 `-p` flag를 사용하세요.

```bash
agent-browser -p browserbase open https://example.com
```

각 built-in provider의 설정과 구성은 [Providers](/providers/browser-use) 섹션을 참조하세요: [Browser Use](/providers/browser-use), [Browserbase](/providers/browserbase), [Browserless](/providers/browserless), [Kernel](/providers/kernel), [AgentCore](/providers/agentcore).
