---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/23-ios.md
order: 23
title: "iOS Simulator"
---

# iOS Simulator

실제 Mobile Safari를 iOS Simulator에서 제어해 진정한 mobile web testing을 수행합니다. native automation에는 XCUITest와 함께 Appium을 사용합니다.

## 요구 사항

- Xcode가 설치된 macOS
- iOS Simulator runtimes(Xcode를 통해 다운로드)
- XCUITest driver가 있는 Appium

## 설정

```bash
# Install Appium globally
npm install -g appium

# Install the XCUITest driver for iOS
appium driver install xcuitest
```

## 사용 가능한 devices 나열

시스템에서 사용 가능한 모든 iOS simulators를 확인합니다.

```bash
agent-browser device list

# Output:
# Available iOS Simulators:
#
#   ○ iPhone 16 Pro (iOS 18.0)
#     F21EEC0D-7618-419F-811B-33AF27A8B2FD
#   ○ iPhone 16 Pro Max (iOS 18.0)
#     50402807-C9B8-4D37-9F13-2E00E782C744
#   ○ iPad Pro 13-inch (M4) (iOS 18.0)
#     3A6C6436-B909-4593-866D-91D1062BB070
#   ...
```

## 기본 사용법

iOS mode를 활성화하려면 `-p ios` flag를 사용하세요. workflow는 desktop과 동일합니다.

```bash
# Launch Safari on iPhone 16 Pro
agent-browser -p ios --device "iPhone 16 Pro" open https://example.com

# Get snapshot with refs (same as desktop)
agent-browser -p ios snapshot -i

# Interact using refs
agent-browser -p ios tap @e1
agent-browser -p ios fill @e2 "text"

# Take screenshot
agent-browser -p ios screenshot mobile.png

# Close session (shuts down simulator)
agent-browser -p ios close
```

## Mobile-specific commands

```bash
# Swipe gestures
agent-browser -p ios swipe up
agent-browser -p ios swipe down
agent-browser -p ios swipe left
agent-browser -p ios swipe right

# Swipe with distance (pixels)
agent-browser -p ios swipe up 500

# Tap (alias for click, semantically clearer for touch)
agent-browser -p ios tap @e1
```

## 환경 변수

환경 변수로 iOS mode를 구성합니다.

```bash

# Now all commands use iOS
agent-browser open https://example.com
agent-browser snapshot -i
agent-browser tap @e1
```

<table>
  <thead>
    <tr><th>변수</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>AGENT_BROWSER_PROVIDER</code></td><td>iOS mode를 활성화하려면 <code>ios</code>로 설정</td></tr>
    <tr><td><code>AGENT_BROWSER_IOS_DEVICE</code></td><td>Device name(예: "iPhone 16 Pro")</td></tr>
    <tr><td><code>AGENT_BROWSER_IOS_UDID</code></td><td>Device UDID(device name의 대안)</td></tr>
  </tbody>
</table>

## 지원되는 devices

Xcode에서 사용 가능한 모든 iOS Simulators가 지원됩니다. 예:

- 모든 iPhone models(iPhone 15, 16, 17, SE 등)
- 모든 iPad models(iPad Pro, iPad Air, iPad mini 등)
- 여러 iOS versions(17.x, 18.x 등)

**Real devices**도 USB connection을 통해 지원됩니다(아래 참조).

## Real device support

Appium은 USB로 연결된 실제 iOS devices에서 Safari를 제어할 수 있습니다. 이를 위해서는 추가 일회성 설정이 필요합니다.

### 1. device UDID 가져오기

```bash
# List connected devices
xcrun xctrace list devices

# Or via system profiler
system_profiler SPUSBDataType | grep -A 5 "iPhone\|iPad"
```

### 2. WebDriverAgent 서명(일회성)

WebDriverAgent는 실제 devices에서 실행되려면 Apple Developer certificate로 서명되어야 합니다.

```bash
# Open the WebDriverAgent Xcode project
cd ~/.appium/node_modules/appium-xcuitest-driver/node_modules/appium-webdriveragent
open WebDriverAgent.xcodeproj
```

Xcode에서:

1. `WebDriverAgentRunner` target 선택
2. Signing & Capabilities로 이동
3. Team 선택(Apple Developer account 필요, free tier도 작동)
4. Xcode가 signing을 자동으로 관리하도록 허용

### 3. agent-browser와 함께 사용

```bash
# Connect device via USB, then use the UDID
agent-browser -p ios --device "<DEVICE_UDID>" open https://example.com

# Or use the device name if unique
agent-browser -p ios --device "John's iPhone" open https://example.com
```

### Real device 참고 사항

- 첫 실행은 WebDriverAgent를 device에 설치합니다(device에서 Trust prompt가 필요할 수 있음)
- Device는 unlock되어 있고 USB로 연결되어 있어야 합니다
- Simulator보다 초기 연결이 약간 느립니다
- 실제 Safari performance와 behavior를 대상으로 테스트합니다
- 처음 설치할 때 Settings → General → VPN & Device Management로 이동해 developer certificate를 신뢰하세요

## Performance notes

- **First launch:** simulator를 boot하고 Appium을 시작하는 데 30-60초가 걸립니다
- **Subsequent commands:** 빠릅니다(simulator가 계속 실행됨)
- **Close command:** simulator와 Appium server를 종료합니다

## Desktop과의 차이점

<table>
  <thead>
    <tr><th>Feature</th><th>Desktop</th><th>iOS</th></tr>
  </thead>
  <tbody>
    <tr><td>Browser</td><td>Chrome, Lightpanda</td><td>Safari only</td></tr>
    <tr><td>Tabs</td><td>Supported</td><td>Single tab only</td></tr>
    <tr><td>PDF export</td><td>Supported</td><td>Not supported</td></tr>
    <tr><td>Screencast</td><td>Supported</td><td>Not supported</td></tr>
    <tr><td>Swipe gestures</td><td>Not native</td><td>Native support</td></tr>
  </tbody>
</table>

## Troubleshooting

### Appium을 찾을 수 없음

```bash
# Make sure Appium is installed globally
npm install -g appium
appium driver install xcuitest

# Verify installation
appium --version
```

### 사용 가능한 simulators 없음

Xcode를 열고 **Settings → Platforms**에서 iOS Simulator runtimes를 다운로드하세요.

### Simulator가 boot되지 않음

Xcode 또는 Simulator app에서 simulator를 수동으로 boot해 작동을 확인한 다음 agent-browser로 다시 시도하세요.
