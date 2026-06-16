---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/17-debugging.md
order: 17
title: "Debugging"
---

# Debugging

자동화 중 브라우저 logs, page errors, JavaScript dialogs, Chrome DevTools traces, highlighted elements, live DevTools frontend를 inspect하려면 debugging commands를 사용하세요.

## Console and page errors

```bash
agent-browser console
agent-browser console --json
agent-browser console --clear

agent-browser errors
agent-browser errors --clear
```

<table>
  <thead>
    <tr><th>명령</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>console</code></td><td>브라우저 console messages 표시</td></tr>
    <tr><td><code>console --json</code></td><td>원시 CDP arguments가 포함된 구조화된 console output 표시</td></tr>
    <tr><td><code>console --clear</code></td><td>agent-browser가 캡처한 console log 지우기</td></tr>
    <tr><td><code>errors</code></td><td>캡처된 page errors와 uncaught JavaScript exceptions 표시</td></tr>
    <tr><td><code>errors --clear</code></td><td>캡처된 page error log 지우기</td></tr>
  </tbody>
</table>

자동화된 diagnostic script에서 object previews 또는 원시 CDP arguments가 중요할 때는 `console --json`을 사용하세요. agent가 페이지에 기록된 내용을 이해하기만 하면 될 때는 기본 text output을 사용하세요.

## JavaScript dialogs

```bash
agent-browser dialog status
agent-browser dialog accept
agent-browser dialog accept "prompt text"
agent-browser dialog dismiss
```

기본적으로 `alert`와 `beforeunload` dialogs는 agent를 차단하지 않도록 자동으로 수락됩니다. `confirm`과 `prompt` dialogs는 여전히 명시적 처리가 필요합니다. 자동 처리를 비활성화하려면 `--no-auto-dialog` 또는 `AGENT_BROWSER_NO_AUTO_DIALOG=1`을 사용하세요.

dialog가 대기 중이면 command responses에는 dialog type과 message가 포함된 `warning` field가 포함되므로 agents가 `dialog accept` 또는 `dialog dismiss`로 복구할 수 있습니다.

## DevTools and visual inspection

```bash
agent-browser highlight @e4
agent-browser highlight "#submit"
agent-browser inspect
```

`highlight`는 live page의 element에 주의를 끌도록 표시하며, headed로 실행하거나 streaming 또는 dashboard를 통해 session을 볼 때 유용합니다. `inspect`는 daemon이 agent-browser commands를 계속 받을 수 있는 상태에서 local proxy를 통해 active page의 Chrome DevTools를 엽니다.

## Chrome trace capture

```bash
agent-browser trace start

agent-browser open https://example.com
agent-browser click @e3

agent-browser trace stop ./trace.json
```

`trace start`는 Chrome DevTools trace를 시작합니다. `trace stop [path]`는 tracing을 끝내고 Chrome Trace Event JSON file을 저장합니다. path를 제공하지 않으면 agent-browser는 temp directory 아래에 자동 생성된 trace file을 씁니다.

curated performance categories와 event counts가 필요할 때는 [Profiler](/profiler)를 사용하세요. lower-level debugging을 위한 일반 Chrome trace가 필요할 때는 raw traces를 사용하세요.

## 관련 도구

<table>
  <thead>
    <tr><th>필요한 것</th><th>사용</th></tr>
  </thead>
  <tbody>
    <tr><td>Performance profile</td><td><a href="/profiler">Profiler</a></td></tr>
    <tr><td>저장된 video artifact</td><td><a href="/recording">Video Recording</a></td></tr>
    <tr><td>Live browser stream</td><td><a href="/streaming">Streaming</a></td></tr>
    <tr><td>Install and environment diagnosis</td><td><a href="/installation#doctor">Doctor</a></td></tr>
  </tbody>
</table>
