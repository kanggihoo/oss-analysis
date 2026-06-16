---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/03-quick-start.md
order: 3
title: "Quick Start"
---

# 빠른 시작

## 핵심 워크플로

모든 브라우저 자동화는 이 패턴을 따릅니다.

```bash
# 1. Navigate
agent-browser open example.com

# 2. Snapshot to get element refs
agent-browser snapshot -i
# Output:
# @e1 [heading] "Example Domain"
# @e2 [link] "More information..."

# 3. Interact using refs
agent-browser click @e2

# 4. Re-snapshot after page changes
agent-browser snapshot -i
```

## 일반적인 명령

```bash
agent-browser open example.com
agent-browser snapshot -i                # Get interactive elements with refs
agent-browser click @e2                  # Click by ref
agent-browser fill @e3 "test@example.com" # Fill input by ref
agent-browser get text @e1               # Get text content
agent-browser screenshot                 # Save to temp directory
agent-browser screenshot page.png        # Save to specific path
agent-browser close
```

## 기존 selector

CSS selector와 semantic locator도 지원됩니다.

```bash
agent-browser click "#submit"
agent-browser fill "#email" "test@example.com"
agent-browser find role button click --name "Submit"
```

## Headed 모드

디버깅을 위해 브라우저 창을 표시합니다.

```bash
agent-browser open example.com --headed
```

## 콘텐츠 대기

```bash
agent-browser wait @e1                   # Wait for element
agent-browser wait --load networkidle    # Wait for network idle
agent-browser wait --url "**/dashboard"  # Wait for URL pattern
agent-browser wait 2000                  # Wait milliseconds
```

## 명령 체이닝

단일 셸 호출에서 `&&`로 명령을 체이닝합니다. 브라우저는 백그라운드 데몬을 통해 유지되므로 체이닝은 안전하고 효율적입니다.

```bash
# Open, wait, and snapshot in one call
agent-browser open example.com && agent-browser wait --load networkidle && agent-browser snapshot -i

# Chain multiple interactions
agent-browser fill @e1 "user@example.com" && agent-browser fill @e2 "pass" && agent-browser click @e3

# Navigate and capture
agent-browser open example.com && agent-browser wait --load networkidle && agent-browser screenshot page.png
```

중간 출력이 필요하지 않을 때는 `&&`를 사용하세요. 먼저 출력을 파싱해야 할 때는 명령을 따로 실행하세요(예: 상호작용 전에 ref를 찾기 위한 snapshot).

## JSON 출력

스크립트에서 프로그래밍 방식으로 파싱하려면 다음을 사용합니다.

```bash
agent-browser snapshot --json
agent-browser get text @e1 --json
```

참고: 기본 텍스트 출력은 더 간결하며 AI 에이전트에 권장됩니다.
