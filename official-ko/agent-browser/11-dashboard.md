---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/11-dashboard.md
order: 11
title: "Observability Dashboard"
---

# Observability Dashboard

live browser viewport와 command activity feed를 보여 주는 로컬 웹 dashboard로 agent-browser sessions를 실시간으로 모니터링합니다.

## 사용법

dashboard는 바이너리에 번들되어 있으며 별도 설치가 필요 없습니다. 서버를 시작하고 아무 session이나 여세요.

```bash
agent-browser dashboard start
agent-browser open example.com
```

그런 다음 브라우저에서 `http://localhost:4848` 또는 `https://dashboard.agent-browser.localhost` 같은 프록시/포워딩된 dashboard URL을 열어 live dashboard를 확인하세요.

모든 sessions는 자동으로 dashboard로 stream됩니다. 추가 flags는 필요 없습니다. 브라우저는 dashboard origin에 머무르며 서버가 session별 tabs, status, stream traffic을 내부적으로 프록시하므로 session ports를 노출할 필요가 없습니다.

### 사용자 지정 stream port

기본적으로 각 session은 WebSocket stream server를 OS가 할당한 port에 바인딩합니다. 특정 port를 사용하려면 `AGENT_BROWSER_STREAM_PORT` 환경 변수를 설정하세요.

```bash
AGENT_BROWSER_STREAM_PORT=9223 agent-browser open example.com
```

실행 중인 session에서 runtime commands를 사용해 streaming을 제어할 수도 있습니다.

```bash
agent-browser stream enable --port 9223
agent-browser stream status
agent-browser stream disable
```

## Dashboard 기능

dashboard는 세 영역으로 구성된 single-page web app입니다.

<table>
  <thead>
    <tr>
      <th>영역</th>
      <th>설명</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Live viewport</strong></td>
      <td>브라우저의 실시간 JPEG frames를 canvas 요소에 렌더링</td>
    </tr>
    <tr>
      <td><strong>Activity feed</strong></td>
      <td>commands, results, console messages를 시간순 stream으로 표시하며 세부 정보를 펼칠 수 있음</td>
    </tr>
    <tr>
      <td><strong>Session creation</strong></td>
      <td>dashboard에서 local engines(Chrome, Lightpanda) 또는 cloud providers(AgentCore, Browserbase, Browserless, Browser Use, Kernel)로 새 sessions 생성</td>
    </tr>
    <tr>
      <td><strong>Status bar</strong></td>
      <td>연결 상태, viewport dimensions, WebSocket endpoint</td>
    </tr>
  </tbody>
</table>

## WebSocket protocol

dashboard는 [Streaming](/streaming)에서 사용하는 것과 같은 WebSocket endpoint에 연결하며, observability를 위한 추가 message types를 사용합니다.

### Command events

command 실행이 시작될 때 전송됩니다.

```json
{
  "type": "command",
  "action": "click",
  "id": "r123",
  "params": { "selector": "@e5" },
  "timestamp": 1711367000000
}
```

### Result events

command가 완료될 때 전송됩니다.

```json
{
  "type": "result",
  "id": "r123",
  "action": "click",
  "success": true,
  "data": {},
  "duration_ms": 45,
  "timestamp": 1711367000045
}
```

### Console events

브라우저가 console에 log를 남길 때 전송됩니다.

```json
{
  "type": "console",
  "level": "log",
  "text": "Page loaded",
  "args": [{"type": "string", "value": "Page loaded"}],
  "timestamp": 1711367000100
}
```

`args` 배열에는 프로그래밍 방식 접근을 위한 원시 CDP `Runtime.consoleAPICalled` arguments가 포함됩니다. Object arguments에는 preview data가 포함됩니다(예: `"Object"` 대신 `{userId: "abc", count: 42}`).

이는 [Streaming](/streaming) 페이지에 문서화된 기존 `frame`, `status`, `error` message types에 추가됩니다.

## 아키텍처

dashboard는 plain HTML, CSS, JS를 생성하는 Next.js static export(`output: 'export'`)입니다. monorepo의 `packages/dashboard/`에 있으며 다음으로 빌드됩니다.

```bash
pnpm build:dashboard
```

dashboard는 compile time에 `rust-embed`를 사용해 CLI 바이너리에 embedded됩니다. Plain HTTP requests는 embedded dashboard assets와 same-origin API routes를 제공합니다. Session-specific tabs, status, stream WebSocket traffic은 dashboard server를 통해 loopback-only session ports로 프록시됩니다.

## AI Chat

dashboard에는 [Vercel AI Gateway](https://vercel.com/docs/ai-gateway)로 구동되는 선택적 AI chat panel이 포함되어 있습니다. 활성화되면 오른쪽 pane에서 Activity, Console, Network, Storage, Extensions와 함께 **Chat** tab이 나타납니다.

### 설정

Chat tab은 항상 표시됩니다. 응답을 활성화하려면 API key를 설정하세요.

```bash
agent-browser dashboard start
```

선택적으로 gateway URL 또는 model을 재정의하세요.

```bash
```

### 작동 방식

Rust server는 dashboard의 chat requests를 Vercel AI Gateway로 프록시하고 Vercel AI SDK의 UI Message Stream protocol을 사용해 응답을 다시 stream합니다. dashboard frontend는 `DefaultChatTransport`와 함께 `@ai-sdk/react`의 `useChat`을 사용합니다.

<table>
  <thead>
    <tr><th>변수</th><th>설명</th><th>기본값</th></tr>
  </thead>
  <tbody>
    <tr><td><code>AI_GATEWAY_URL</code></td><td>Vercel AI Gateway base URL입니다.</td><td><code>https://ai-gateway.vercel.sh</code></td></tr>
    <tr><td><code>AI_GATEWAY_API_KEY</code></td><td>AI Gateway용 API key입니다. AI chat responses를 활성화하려면 필요합니다.</td><td>(none)</td></tr>
    <tr><td><code>AI_GATEWAY_MODEL</code></td><td>chat requests의 기본 AI model입니다.</td><td><code>anthropic/claude-sonnet-4.6</code></td></tr>
  </tbody>
</table>
