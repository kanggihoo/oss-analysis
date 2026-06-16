---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/12-diffing.md
order: 12
title: "Diffing"
---

# Diffing

페이지 상태를 비교해 변경 사항을 감지합니다. 접근성 트리 snapshots를 통한 구조적 비교, pixel comparison을 통한 시각적 비교, 또는 두 URL 간 비교가 가능합니다.

<DiffDemo />

## 명령

<table>
  <thead>
    <tr><th>명령</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>diff snapshot</code></td><td>현재 snapshot을 session의 마지막 snapshot과 비교</td></tr>
    <tr><td><code>diff snapshot --baseline &lt;file&gt;</code></td><td>현재 snapshot을 저장된 파일과 비교</td></tr>
    <tr><td><code>diff screenshot --baseline &lt;file&gt;</code></td><td>baseline 이미지와 visual pixel diff 수행</td></tr>
    <tr><td><code>diff url &lt;url1&gt; &lt;url2&gt;</code></td><td>두 페이지 비교(snapshot + 선택적 screenshot)</td></tr>
  </tbody>
</table>

## Snapshot diff

line-level text diff를 사용해 두 시점 사이의 접근성 트리를 비교합니다.

```bash
# Compare against the last snapshot taken in this session
agent-browser diff snapshot

# Compare against a saved baseline file
agent-browser diff snapshot --baseline before.txt

# Scope to a specific part of the page
agent-browser diff snapshot --selector "#main" --compact
```

`--baseline`이 없으면 명령은 현재 session에서 가장 최근에 가져온 snapshot과 자동으로 비교합니다. 이는 agent가 어떤 action이 의도한 효과를 냈는지 검증할 때의 주된 사용 사례입니다.

### 옵션

<table>
  <thead>
    <tr><th>Flag</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>-b, --baseline &lt;file&gt;</code></td><td>비교할 저장된 snapshot 파일 경로</td></tr>
    <tr><td><code>-s, --selector &lt;sel&gt;</code></td><td>현재 snapshot의 범위를 CSS selector 또는 @ref로 제한</td></tr>
    <tr><td><code>-c, --compact</code></td><td>compact snapshot 형식 사용</td></tr>
    <tr><td><code>-d, --depth &lt;n&gt;</code></td><td>snapshot 트리 깊이 제한</td></tr>
  </tbody>
</table>

### 출력

diff는 unified diff 형식과 유사하게 추가된 줄에는 `+`, 제거된 줄에는 `-`를 사용합니다. 요약 줄에는 additions, removals, unchanged lines 수가 표시됩니다.

```
- button "Submit" [ref=e2]
+ button "Submit" [ref=e2] [disabled]
  3 additions, 2 removals, 41 unchanged
```

## Screenshot diff

현재 페이지 screenshot을 baseline 이미지와 pixel 수준에서 비교합니다. 변경된 pixels가 빨간색으로 강조된 diff image를 생성합니다.

```bash
# Basic visual diff
agent-browser diff screenshot --baseline before.png

# Save diff image to a specific path
agent-browser diff screenshot --baseline before.png --output diff.png

# Adjust threshold and scope to element
agent-browser diff screenshot --baseline before.png --threshold 0.2 --selector "#hero"
```

### 옵션

<table>
  <thead>
    <tr><th>Flag</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>-b, --baseline &lt;file&gt;</code></td><td>비교할 baseline PNG/JPEG 이미지(필수)</td></tr>
    <tr><td><code>-o, --output &lt;file&gt;</code></td><td>생성된 diff image의 경로(기본값: temp dir)</td></tr>
    <tr><td><code>-t, --threshold &lt;0-1&gt;</code></td><td>Color distance threshold(기본값: 0.1). 높을수록 더 관대함</td></tr>
    <tr><td><code>-s, --selector &lt;sel&gt;</code></td><td>현재 screenshot의 범위를 element로 제한</td></tr>
    <tr><td><code>--full</code></td><td>full-page screenshot 촬영</td></tr>
  </tbody>
</table>

### 출력

diff image 경로, 다른 pixels 수, mismatch percentage를 보고합니다. diff image는 변경되지 않은 pixels를 어둡게 표시하고 변경된 pixels를 빨간색으로 표시합니다.

baseline 이미지와 현재 이미지의 크기가 다르면 명령은 pixel comparison을 시도하지 않고 dimension mismatch를 보고합니다.

## URL diff

두 페이지를 순서대로 탐색하고 결과를 diff해 비교합니다.

```bash
# Compare two URLs (snapshot diff)
agent-browser diff url https://staging.example.com https://prod.example.com

# Include visual comparison
agent-browser diff url https://v1.example.com https://v2.example.com --screenshot

# Full-page screenshot comparison
agent-browser diff url https://v1.example.com https://v2.example.com --screenshot --full
```

명령은 첫 번째 URL로 이동해 상태를 캡처한 다음, 두 번째 URL로 이동해 다시 캡처합니다. Snapshot diff는 항상 포함됩니다. Screenshot diff에는 `--screenshot` flag가 필요합니다.

완료 후 브라우저는 두 번째 URL에 머뭅니다.

### 옵션

<table>
  <thead>
    <tr><th>Flag</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>--screenshot</code></td><td>visual screenshot comparison도 수행</td></tr>
    <tr><td><code>--full</code></td><td>full-page screenshots 사용</td></tr>
    <tr><td><code>--wait-until &lt;strategy&gt;</code></td><td>Navigation wait strategy: <code>load</code>, <code>domcontentloaded</code>, <code>networkidle</code>(기본값: <code>load</code>)</td></tr>
    <tr><td><code>-s, --selector &lt;sel&gt;</code></td><td>snapshots 범위를 CSS selector 또는 @ref로 제한</td></tr>
    <tr><td><code>-c, --compact</code></td><td>compact snapshot 형식 사용</td></tr>
    <tr><td><code>-d, --depth &lt;n&gt;</code></td><td>snapshot 트리 깊이 제한</td></tr>
  </tbody>
</table>

## 사용 사례

### Agent actions 검증

가장 일반적인 사용 사례는 action(click, fill, submit)이 예상대로 페이지를 변경했는지 확인하는 것입니다.

```bash
agent-browser snapshot -i          # Take interactive-only snapshot (baseline)
agent-browser fill @e3 "test@example.com"
agent-browser diff snapshot        # Compare current snapshot to the baseline
```

### 변경 사항 모니터링

업데이트를 감지하기 위해 페이지를 저장된 baseline과 주기적으로 비교합니다.

```bash
# Save baseline
agent-browser open https://example.com && agent-browser snapshot > baseline.txt

# Later, check for changes
agent-browser open https://example.com && agent-browser diff snapshot --baseline baseline.txt
```

### Visual regression testing

deploy 전후의 screenshots를 비교해 의도하지 않은 시각적 변경을 포착합니다.

```bash
agent-browser open https://staging.example.com && agent-browser screenshot baseline.png
# ... deploy happens ...
agent-browser open https://staging.example.com && agent-browser diff screenshot --baseline baseline.png
```

### 환경 비교

staging과 production을 diff해 동등성을 검증합니다.

```bash
agent-browser diff url https://staging.example.com https://prod.example.com --screenshot
```
