---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/20-files.md
order: 20
title: "Files & Clipboard"
---

# Files & Clipboard

agent-browser는 files를 upload하고, downloads를 capture하고, `file://` URLs를 통해 local files를 읽고, PDFs와 screenshots를 쓰고, browser clipboard와 상호작용할 수 있습니다.

## Files upload

```bash
agent-browser snapshot -i
agent-browser upload @e4 ./invoice.pdf
agent-browser upload @e4 ./front.png ./back.png
```

selector는 file input으로 해석되어야 합니다. multi-file inputs에는 여러 file paths를 사용할 수 있습니다.

## Downloads

```bash
agent-browser download @e5 ./report.csv
agent-browser wait --download ./archive.zip --timeout 30000
```

특정 element가 download를 trigger할 때는 `download`를 사용하세요. 다른 action이 download를 시작하고 완료를 기다려야 할 때는 `wait --download`를 사용하세요.

브라우저가 시작한 downloads의 기본 download directory를 설정합니다.

```bash
agent-browser --download-path ./downloads open https://app.example.com
```

`--download-path`가 없으면 downloads는 브라우저가 닫힐 때 정리되는 temporary directory로 이동합니다.

## Screenshots and PDFs

```bash
agent-browser screenshot ./page.png
agent-browser screenshot --full ./page-full.png
agent-browser screenshot --screenshot-format jpeg --screenshot-quality 80 ./page.jpg
agent-browser pdf ./page.pdf
```

Screenshot defaults는 다음으로도 구성할 수 있습니다.

<table>
  <thead>
    <tr><th>설정</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>--screenshot-dir</code> / <code>AGENT_BROWSER_SCREENSHOT_DIR</code></td><td>기본 screenshot output directory</td></tr>
    <tr><td><code>--screenshot-format</code> / <code>AGENT_BROWSER_SCREENSHOT_FORMAT</code></td><td><code>png</code> 또는 <code>jpeg</code></td></tr>
    <tr><td><code>--screenshot-quality</code> / <code>AGENT_BROWSER_SCREENSHOT_QUALITY</code></td><td>0부터 100까지의 JPEG quality</td></tr>
  </tbody>
</table>

## Local files

```bash
agent-browser --allow-file-access open file:///Users/me/report.pdf
agent-browser --allow-file-access open file:///path/to/page.html
agent-browser screenshot ./local-file.png
```

`--allow-file-access`는 Chromium 전용입니다. 이 옵션은 `file://` pages가 `fetch`와 XHR 같은 browser APIs를 통해 다른 local files를 로드하고 접근할 수 있게 합니다.

## Clipboard

```bash
agent-browser clipboard read
agent-browser clipboard write "Hello, world"
agent-browser clipboard copy
agent-browser clipboard paste
```

`copy`와 `paste`는 현재 selection 또는 focused element에 대한 platform keyboard shortcuts를 simulate합니다. clipboard text를 직접 설정하려면 `write`를 사용하세요.
