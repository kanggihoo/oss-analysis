---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/16-recording.md
order: 16
title: "Video Recording"
---

# Video Recording

디버깅, CI 증거, 제품 walkthrough 또는 repro report를 위해 브라우저 자동화를 WebM video로 캡처하려면 `record`를 사용하세요.

## 기본 워크플로

```bash
agent-browser open https://example.com
agent-browser record start ./demo.webm
agent-browser snapshot -i
agent-browser click @e1

agent-browser record stop
```

session을 실행한 후 `record start`는 즉시 navigation할 수도 있습니다.

```bash
agent-browser open
agent-browser record start ./demo.webm https://example.com
```

URL을 제공하지 않으면 현재 페이지에서 recording이 시작됩니다. recording context는 active session의 cookies를 복사합니다.

## 명령

<table>
  <thead>
    <tr><th>명령</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>record start &lt;path.webm&gt; [url]</code></td><td>WebM 파일로 recording 시작</td></tr>
    <tr><td><code>record stop</code></td><td>active recording을 중지하고 파일 저장</td></tr>
    <tr><td><code>record restart &lt;path.webm&gt; [url]</code></td><td>현재 recording을 중지하고 즉시 다른 recording 시작</td></tr>
  </tbody>
</table>

## CI 증거

```bash
#!/bin/bash
set -e

cleanup() {
  agent-browser record stop 2>/dev/null || true
  agent-browser close 2>/dev/null || true
}
trap cleanup EXIT

agent-browser open https://app.example.com/login
agent-browser record start "./artifacts/login-flow.webm"
agent-browser snapshot -i
agent-browser fill @e1 "demo@example.com"
agent-browser fill @e2 "password"
agent-browser click @e3
agent-browser wait --url "**/dashboard"
```

브라우저 실패를 텍스트 출력만으로 진단하기 어려울 때 recordings를 CI artifacts로 보관하세요.

## 사람이 읽기 쉬운 demos

사람이 볼 video라면 짧은 waits를 추가하세요.

```bash
agent-browser open https://shop.example.com
agent-browser record start ./checkout.webm
agent-browser wait 500
agent-browser click @e4
agent-browser wait 500
agent-browser screenshot ./screenshots/cart.png
agent-browser record stop
```

Screenshots와 videos는 함께 사용하기 좋습니다. screenshots는 정확한 still states를 캡처하고, video는 timing, transitions, unexpected overlays를 보여 줍니다.

## 출력 형식

<table>
  <thead>
    <tr><th>속성</th><th>값</th></tr>
  </thead>
  <tbody>
    <tr><td>Container</td><td>WebM</td></tr>
    <tr><td>일반 extension</td><td><code>.webm</code></td></tr>
    <tr><td>Viewport</td><td>active browser viewport settings 사용</td></tr>
    <tr><td>State</td><td>active session의 cookies 복사</td></tr>
  </tbody>
</table>

## 제한 사항

- Recording은 automation에 overhead를 추가합니다.
- 긴 recordings는 상당한 disk space를 사용할 수 있습니다.
- 파일을 flush해야 한다면 session을 닫기 전에 `record stop`을 사용하세요.
- 일부 제한된 headless environments에는 codec 또는 GPU 제한이 있을 수 있습니다.
