---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/15-streaming.md
order: 15
title: "Streaming"
---

# Streaming

live preview 또는 사람이 AI 에이전트와 함께 지켜보고 상호작용할 수 있는 "pair browsing"을 위해 WebSocket으로 브라우저 viewport를 stream합니다.

## Streaming

모든 session은 OS가 할당한 port에서 WebSocket stream server를 자동으로 시작합니다. 서버는 viewport frames를 stream하고 input events(mouse, keyboard, touch)를 받습니다.

특정 port에 바인딩하려면 `AGENT_BROWSER_STREAM_PORT`를 설정하세요.

```bash
AGENT_BROWSER_STREAM_PORT=9223 agent-browser open example.com
```

runtime에서 streaming을 관리할 수도 있습니다.

```bash
agent-browser stream status            # Show streaming state and bound port
agent-browser stream enable --port 9223  # Re-enable on a specific port
agent-browser stream disable           # Stop streaming for the session
```

`stream status`는 enabled state, active port, browser connection state, 그리고 screencasting이 활성 상태인지 여부를 반환합니다. `stream disable`은 서버를 종료하고 session의 `.stream` metadata file을 제거합니다.

live WebSocket stream 대신 저장된 WebM artifact가 필요할 때는 [Video Recording](/recording)을 사용하세요.

## Runtime status response

`agent-browser stream status --json`은 다음과 같은 데이터를 반환합니다.

```json
{
  "enabled": true,
  "port": 9223,
  "connected": true,
  "screencasting": true
}
```

`connected`는 daemon에 현재 browser가 attached되어 있는지 보고합니다. `screencasting`은 stream server를 위해 frames가 활발히 생성되고 있는지 보고합니다.

## screencast commands와의 관계

`stream enable`은 WebSocket server를 만들고 session에서 계속 사용할 수 있게 유지합니다. 그러면 WebSocket clients가 live frame delivery를 자동으로 trigger합니다.

lower-level `screencast_start` 및 `screencast_stop` commands는 여전히 명시적인 CDP screencasts를 직접 제어합니다. WebSocket runtime server 없이 screencast를 원할 때 사용하세요.

## WebSocket protocol

frames를 받고 input을 보내려면 `ws://localhost:9223`에 연결하세요.

### Frame messages

서버는 base64로 인코딩된 images가 포함된 frame messages를 보냅니다.

```json
{
  "type": "frame",
  "data": "<base64-encoded-jpeg>",
  "metadata": {
    "deviceWidth": 1280,
    "deviceHeight": 720,
    "pageScaleFactor": 1,
    "offsetTop": 0,
    "scrollOffsetX": 0,
    "scrollOffsetY": 0
  }
}
```

### Status messages

Connection 및 screencast status:

```json
{
  "type": "status",
  "connected": true,
  "screencasting": true,
  "viewportWidth": 1280,
  "viewportHeight": 720
}
```

## Input injection

브라우저를 원격으로 제어하려면 input events를 보내세요.

### Mouse events

```json
// Click
{
  "type": "input_mouse",
  "eventType": "mousePressed",
  "x": 100,
  "y": 200,
  "button": "left",
  "clickCount": 1
}

// Release
{
  "type": "input_mouse",
  "eventType": "mouseReleased",
  "x": 100,
  "y": 200,
  "button": "left"
}

// Move
{
  "type": "input_mouse",
  "eventType": "mouseMoved",
  "x": 150,
  "y": 250
}

// Scroll
{
  "type": "input_mouse",
  "eventType": "mouseWheel",
  "x": 100,
  "y": 200,
  "deltaX": 0,
  "deltaY": 100
}
```

### Keyboard events

```json
// Key down
{
  "type": "input_keyboard",
  "eventType": "keyDown",
  "key": "Enter",
  "code": "Enter"
}

// Key up
{
  "type": "input_keyboard",
  "eventType": "keyUp",
  "key": "Enter",
  "code": "Enter"
}

// Type character
{
  "type": "input_keyboard",
  "eventType": "char",
  "text": "a"
}

// With modifiers (1=Alt, 2=Ctrl, 4=Meta, 8=Shift)
{
  "type": "input_keyboard",
  "eventType": "keyDown",
  "key": "c",
  "code": "KeyC",
  "modifiers": 2
}
```

### Touch events

```json
// Touch start
{
  "type": "input_touch",
  "eventType": "touchStart",
  "touchPoints": [{ "x": 100, "y": 200 }]
}

// Touch move
{
  "type": "input_touch",
  "eventType": "touchMove",
  "touchPoints": [{ "x": 150, "y": 250 }]
}

// Touch end
{
  "type": "input_touch",
  "eventType": "touchEnd",
  "touchPoints": []
}

// Multi-touch (pinch zoom)
{
  "type": "input_touch",
  "eventType": "touchStart",
  "touchPoints": [
    { "x": 100, "y": 200, "id": 0 },
    { "x": 200, "y": 200, "id": 1 }
  ]
}
```

## Programmatic API

고급 사용을 위해 TypeScript API로 streaming을 직접 제어합니다.

```typescript

const browser = new BrowserManager();
await browser.launch({ headless: true });
await browser.navigate('https://example.com');

// Start screencast with callback
await browser.startScreencast((frame) => {
  console.log('Frame:', frame.metadata.deviceWidth, 'x', frame.metadata.deviceHeight);
  // frame.data is base64-encoded image
}, {
  format: 'jpeg',  // or 'png'
  quality: 80,     // 0-100, jpeg only
  maxWidth: 1280,
  maxHeight: 720,
  everyNthFrame: 1
});

// Inject mouse event
await browser.injectMouseEvent({
  type: 'mousePressed',
  x: 100,
  y: 200,
  button: 'left',
  clickCount: 1
});

// Inject keyboard event
await browser.injectKeyboardEvent({
  type: 'keyDown',
  key: 'Enter',
  code: 'Enter'
});

// Inject touch event
await browser.injectTouchEvent({
  type: 'touchStart',
  touchPoints: [{ x: 100, y: 200 }]
});

// Check if screencasting
console.log('Active:', browser.isScreencasting());

// Stop screencast
await browser.stopScreencast();
```

## 사용 사례

- **Pair browsing** - 사람이 AI agent를 실시간으로 지켜보고 지원
- **Remote preview** - 별도 UI에서 브라우저 출력 보기
- **Recording** - video 생성을 위해 frames 캡처
- **Mobile testing** - mobile emulation을 위해 touch events 주입
- **Accessibility testing** - automated tests 중 수동 상호작용
