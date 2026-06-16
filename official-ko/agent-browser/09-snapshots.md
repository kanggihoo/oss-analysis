---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/09-snapshots.md
order: 9
title: "Snapshots"
---

# Snapshots

`snapshot` 명령은 요소 상호작용을 위한 refs가 포함된 간결한 접근성 트리를 반환합니다.

## 옵션

출력 크기를 줄이려면 필터링하세요.

```bash
agent-browser snapshot                    # Full accessibility tree
agent-browser snapshot -i                 # Interactive elements only (recommended)
agent-browser snapshot -c                 # Compact (remove empty elements)
agent-browser snapshot -d 3               # Limit depth to 3 levels
agent-browser snapshot -s "#main"         # Scope to CSS selector
agent-browser snapshot -i -c -d 5         # Combine options
```

<table>
  <thead>
    <tr><th>옵션</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>-i, --interactive</code></td><td>상호작용 가능한 요소만 포함(buttons, links, inputs)</td></tr>
    <tr><td><code>-u, --urls</code></td><td>link 요소의 href URL 포함</td></tr>
    <tr><td><code>-c, --compact</code></td><td>비어 있는 구조적 요소 제거</td></tr>
    <tr><td><code>-d, --depth</code></td><td>트리 깊이 제한</td></tr>
    <tr><td><code>-s, --selector</code></td><td>CSS selector로 범위 제한</td></tr>
  </tbody>
</table>

## 출력 형식

기본 텍스트 출력은 간결하며 AI에 적합합니다.

```bash
agent-browser snapshot -i
# Output:
# @e1 [heading] "Example Domain" [level=1]
# @e2 [button] "Submit"
# @e3 [input type="email"] placeholder="Email"
# @e4 [link] "Learn more"
```

## Refs 사용

snapshot의 refs는 명령에 직접 매핑됩니다.

```bash
agent-browser click @e2      # Click the Submit button
agent-browser fill @e3 "a@b.com"  # Fill the email input
agent-browser get text @e1        # Get heading text
```

## Ref 수명 주기

페이지가 변경되면 refs는 무효화됩니다. 탐색 또는 DOM 업데이트 후에는 항상 다시 snapshot을 가져오세요.

```bash
agent-browser click @e4      # Navigates to new page
agent-browser snapshot -i    # Get fresh refs
agent-browser click @e1      # Use new refs
```

## 주석이 달린 스크린샷

텍스트 snapshot과 함께 시각적 컨텍스트가 필요하면 `screenshot --annotate`를 사용해 상호작용 가능한 요소 위에 번호가 붙은 label을 오버레이하세요. 각 label `[N]`은 ref `@eN`에 매핑됩니다.

네이티브 모드에서 annotated screenshots는 현재 CDP 기반 브라우저 경로(Chromium/Lightpanda)에서 작동합니다. Safari/WebDriver backend는 아직 `--annotate`를 지원하지 않습니다.

```bash
agent-browser screenshot --annotate ./page.png
# -> Screenshot saved to ./page.png
#    [1] @e1 button "Submit"
#    [2] @e2 link "Home"
#    [3] @e3 textbox "Email"
agent-browser click @e2
```

Headless Chromium 스크린샷은 일관된 이미지 출력을 위해 네이티브 스크롤바를 숨깁니다.
네이티브 스크롤바를 표시하려면 실행할 때 `--hide-scrollbars false`를 전달하세요.

Annotated screenshots는 refs도 캐시하므로 즉시 요소와 상호작용할 수 있습니다. 텍스트 snapshot만으로 label이 없는 아이콘, canvas 콘텐츠 또는 시각적 layout 검증에 충분하지 않을 때 유용합니다.

## Iframes

Snapshots는 iframe 콘텐츠를 자동으로 감지하고 인라인으로 포함합니다. main frame의 각 `Iframe` 노드는 해석되며, 그 child 접근성 트리가 바로 아래에 포함됩니다. iframe 내부 요소에 할당된 refs는 frame 컨텍스트를 포함하므로 먼저 frame을 전환하지 않아도 상호작용이 작동합니다.

```bash
agent-browser snapshot -i
# @e1 [heading] "Checkout"
# @e2 [Iframe] "payment-frame"
#   @e3 [input] "Card number"
#   @e4 [button] "Pay"

agent-browser fill @e3 "4111111111111111"
agent-browser click @e4
```

iframe 중첩은 한 수준만 확장됩니다. 접근성 트리 접근을 차단하는 cross-origin iframe과 빈 iframe은 조용히 생략됩니다.

단일 iframe으로 snapshot 범위를 제한하려면 먼저 그 안으로 전환하세요.

```bash
agent-browser frame @e2
agent-browser snapshot -i       # Only elements inside that iframe
agent-browser frame main        # Return to main frame
```

## 모범 사례

1. 실행 가능한 요소로 출력을 줄이려면 `-i`를 사용하세요
2. 페이지 변경 후 업데이트된 refs를 얻으려면 다시 snapshot을 가져오세요
3. 특정 페이지 섹션에는 `-s`로 범위를 제한하세요
4. 복잡한 페이지에서는 `-d`로 깊이를 제한하세요
5. refs와 함께 시각적 컨텍스트가 필요할 때는 `screenshot --annotate`를 사용하세요

## JSON 출력

스크립트에서 프로그래밍 방식으로 파싱하려면 다음을 사용합니다.

```bash
agent-browser snapshot --json
# {"success":true,"data":{"snapshot":"...","refs":{"e1":{"role":"heading","name":"Title"},...}}}
```

참고: JSON은 텍스트 출력보다 더 많은 토큰을 사용합니다. 기본 텍스트 형식이 AI 에이전트에 권장됩니다.
